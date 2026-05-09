import os
import json
import boto3
import logging
import urllib.request
import urllib.error

logger = logging.getLogger()
logger.setLevel(logging.INFO)

WHATSAPP_TOKEN = os.environ["WHATSAPP_TOKEN"]
WHATSAPP_PHONE_NUMBER_ID = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
WHATSAPP_VERIFY_TOKEN = os.environ["WHATSAPP_VERIFY_TOKEN"]
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "eu-west-1"))
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "eu-west-1"))
suppliers_table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SUPPLIERS", "pientuottajat-suppliers"))
conversations_table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_CONVERSATIONS", "pientuottajat-conversations"))

SYSTEM_PROMPT = """Olet pientuottaja-assistentti joka auttaa suomalaisia pieniä elintarviketoimittajia seuraamaan
toimituksiaan, laskutustaan, reklamaatioitaan ja hyllysaatavuuttaan alueosuuskaupoissa.

Olet ystävällinen, selkeä ja proaktiivinen. Käytä aina suomea. Vastaa lyhyesti ja selkeästi.
Älä käytä markdown-muotoilua (ei *, #, **) — WhatsApp näyttää tekstin sellaisenaan.

Voit hakea toimittajan: toimitukset, reklamaatiot, myyntidata alueosuuskaupoittain, hyllysaatavuuden.
Voit myös päivittää hänen hälytyspreferenssinsä."""

USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "True") == "True"


def get_mock_context() -> str:
    return """
TOIMITTAJAN TIEDOT (demo-data):
Viimeisimmät toimitukset:
- DEL-001: 7.5.2026, Prisma Tikkurila, Vastaanotettu, 24 kpl, 312,50 e
- DEL-002: 5.5.2026, S-market Kerava, REKLAMAATIO, 12 kpl, 156,00 e
- DEL-003: 2.5.2026, Prisma Tikkurila, Laskutettu, 30 kpl, 390,00 e

Avoimet reklamaatiot:
- REC-042: Toimitus DEL-002, S-market Kerava, Syy: Pakkausvaurio 3 kpl, Avoin, maaraika 13.5.2026

Myynti toukokuu 2026:
- Prisma Tikkurila: 156 kpl, 2028 e
- S-market Kerava: 89 kpl, 1157 e
- Sale Jarvenpaaa: 34 kpl, 442 e
- Yhteensa: 3627 e

Hyllysaatavuus:
- Sale Jarvenpaaa / Luomuhillot 400g: KRIITTINEN, tayttaste 15%
- Prisma Tikkurila: OK
- S-market Kerava: OK
"""


def get_conversation_history(session_id: str) -> list:
    try:
        resp = conversations_table.get_item(Key={"session_id": session_id})
        return resp.get("Item", {}).get("messages", [])
    except Exception:
        return []


def save_conversation_history(session_id: str, messages: list):
    import time
    try:
        conversations_table.put_item(Item={
            "session_id": session_id,
            "messages": messages[-20:],
            "ttl": int(time.time()) + 86400 * 7,
        })
    except Exception as e:
        logger.warning(f"Conversation save failed: {e}")


def invoke_bedrock(session_id: str, user_message: str) -> str:
    history = get_conversation_history(session_id)
    context = get_mock_context() if USE_MOCK_DATA else ""

    user_content = f"{user_message}\n\n[Jarjestelma data]\n{context}" if context else user_message
    messages = history + [{"role": "user", "content": user_content}]

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 512,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }

    try:
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        reply = result["content"][0]["text"]

        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        save_conversation_history(session_id, history)
        return reply
    except Exception as e:
        logger.error(f"Bedrock error: {e}")
        return "Tekninen ongelma. Yrita hetken kuluttua uudelleen."


def send_whatsapp_message(to: str, text: str):
    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as e:
        logger.error(f"WhatsApp send error {e.code}: {e.read().decode()}")


def get_or_create_supplier(wa_number: str, display_name: str) -> dict:
    supplier_id = f"wa_{wa_number}"
    resp = suppliers_table.get_item(Key={"supplier_id": supplier_id})
    if "Item" not in resp:
        item = {
            "supplier_id": supplier_id,
            "channel": "whatsapp",
            "channel_user_id": wa_number,
            "display_name": display_name,
            "preferences": {
                "monthly_report_day": 1,
                "alert_on_reclamation": True,
                "alert_on_shelf_shortage": True,
            },
        }
        suppliers_table.put_item(Item=item)
        return item
    return resp["Item"]


def lambda_handler(event: dict, context) -> dict:
    logger.info(f"Event: {json.dumps(event)}")

    # WhatsApp webhook-vahvistus (GET — Meta kutsuu tata kerran setupissa)
    params = event.get("queryStringParameters") or {}
    if params.get("hub.mode") == "subscribe":
        if params.get("hub.verify_token") == WHATSAPP_VERIFY_TOKEN:
            return {"statusCode": 200, "body": params.get("hub.challenge", "")}
        return {"statusCode": 403, "body": "Forbidden"}

    # Saapuva viesti (POST)
    body = json.loads(event.get("body", "{}"))
    entry = body.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    value = changes.get("value", {})
    messages = value.get("messages", [])

    if not messages:
        return {"statusCode": 200, "body": "ok"}

    msg = messages[0]
    if msg.get("type") != "text":
        return {"statusCode": 200, "body": "ok"}

    wa_number = msg["from"]
    text = msg["text"]["body"]
    contacts = value.get("contacts", [{}])
    display_name = contacts[0].get("profile", {}).get("name", wa_number)

    supplier = get_or_create_supplier(wa_number, display_name)
    session_id = f"wa-{wa_number}-session"

    if text.strip().lower() in ["hei", "moi", "aloita", "start"]:
        reply = (
            f"Hei {display_name}! Olen pientuottaja-assistenttisi.\n\n"
            "Voit kysyä minulta:\n"
            "- Viimeisimmät toimitukseni\n"
            "- Avoimet reklamaatiot\n"
            "- Kuukauden myynti myymalakohtaisesti\n"
            "- Hyllysaatavuustilanne\n\n"
            "Voit myos pyytaa automaattisia halytyksia, esim:\n"
            "\"Halyta minulle aina reklamaatioista\""
        )
    else:
        reply = invoke_bedrock(session_id, text)

    send_whatsapp_message(wa_number, reply)
    return {"statusCode": 200, "body": "ok"}
