"""
WhatsApp Webhook Handler — Pientuottajat AI

Vastaanottaa toimittajan WhatsApp-viestit ja ohjaa ne
Amazon Bedrock Agentille (Claude), joka paattaa mitka
action groupit kutsutaan (getDeliveries, submitReclamation jne.).

Jos BEDROCK_AGENT_ID ei ole asetettu (ennen agent-setuppia),
kaytaa suoraa InvokeModel-kutsua (fallback).
"""
import os
import json
import boto3
import logging
import urllib.request
import urllib.error

logger = logging.getLogger()
logger.setLevel(logging.INFO)

WHATSAPP_TOKEN          = os.environ["WHATSAPP_TOKEN"]
WHATSAPP_PHONE_NUMBER_ID = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
WHATSAPP_VERIFY_TOKEN   = os.environ["WHATSAPP_VERIFY_TOKEN"]
BEDROCK_AGENT_ID        = os.environ.get("BEDROCK_AGENT_ID", "")
BEDROCK_AGENT_ALIAS_ID  = os.environ.get("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID")
BEDROCK_MODEL_ID        = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
REGION                  = os.environ.get("AWS_REGION", "eu-west-1")

bedrock_agent   = boto3.client("bedrock-agent-runtime", region_name=REGION)
bedrock_runtime = boto3.client("bedrock-runtime",       region_name=REGION)
dynamodb        = boto3.resource("dynamodb",            region_name=REGION)

suppliers_table    = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SUPPLIERS",    "pientuottajat-suppliers"))
conversations_table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_CONVERSATIONS","pientuottajat-conversations"))

SYSTEM_PROMPT = """Olet pientuottaja-assistentti SOK:n (S-ryhman) alueosuuskauppojen pientoimittajille.

Tehtavasi:
- Auta toimittajaa seuraamaan toimituksiaan, tilityksiaan, reklamaatioitaan ja hyllysaatavuuttaan
- Ole proaktiivinen: jos naet ongelmakohtia (esim. kriittinen hyllysaatavuus tai avoin reklamaatio), mainitse niista
- Toimittaja voi myos luoda reklamaatioita ja vastata asiakkaan kyselyihin sinun kauttasi

Kaytettavissa olevat toiminnot (kaytat niita automaattisesti tarpeen mukaan):
- getDeliveries: hae toimitukset
- getSettlements: hae tilitykset ja maksujen status
- getReclamations: hae reklamaatiot
- submitReclamation: luo uusi reklamaatio
- respondToReclamation: vastaa reklamaatioon
- getShelfAvailability: hyllysaatavuus myymaloittain
- updateAlertPreferences: aseta halytysasetukset
- getSurveyQuestions: hae asiakkaan lahettamat kyselyt
- submitSurveyResponse: vastaa kyselyyn

Tarkeat ohjeet:
- Kayta aina suomea
- Vastaa lyhyesti ja selkeasti — kaytat ovat pienyrittajia, ei it-ammattilaisia
- EI markdown-muotoilua (ei *, #) — WhatsApp nayttaa plain text
- Jos toimittaja pyytaa asettamaan halytykset, kayda preferenssit selkeasti lapi
- Mainitse aina avoimet reklamaatiot ja kriittiset hyllypuutteet automaattisesti kun naet niita datassa"""


def send_whatsapp(to: str, text: str):
    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = json.dumps({"messaging_product": "whatsapp", "to": to,
                          "type": "text", "text": {"body": text}}).encode()
    req = urllib.request.Request(url, data=payload, method="POST",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as e:
        logger.error(f"WhatsApp send error {e.code}: {e.read().decode()}")


def get_or_create_supplier(wa_number: str, display_name: str) -> dict:
    supplier_id = f"wa_{wa_number}"
    resp = suppliers_table.get_item(Key={"supplier_id": supplier_id})
    if "Item" not in resp:
        item = {
            "supplier_id": supplier_id, "channel": "whatsapp",
            "channel_user_id": wa_number, "display_name": display_name,
            "preferences": {"alert_on_reclamation": True, "alert_on_shelf_shortage": True,
                            "alert_on_payment": True, "monthly_report_day": 1, "weekly_summary": False},
        }
        suppliers_table.put_item(Item=item)
        return item
    return resp["Item"]


# ── Agenttinen kutsu: Bedrock Agent (suositeltava, tool-use + muisti) ────────

def invoke_agent(supplier_id: str, wa_number: str, message: str) -> str:
    """Kutsu Bedrock Agentia — agenti paattaa itse mita action groupeja kaytetaan."""
    session_id = f"wa-{wa_number}"  # Yksi sessio per toimittaja, Agent pitaa kontekstin
    try:
        response = bedrock_agent.invoke_agent(
            agentId=BEDROCK_AGENT_ID,
            agentAliasId=BEDROCK_AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=message,
            sessionState={
                "sessionAttributes": {"supplier_id": supplier_id, "channel": "whatsapp"},
            },
        )
        result = ""
        for event in response.get("completion", []):
            chunk = event.get("chunk", {})
            if "bytes" in chunk:
                result += chunk["bytes"].decode("utf-8")
        return result or "Pahoittelen, en saanut vastausta. Yrita uudelleen."
    except Exception as e:
        logger.error(f"Bedrock Agent error: {e}")
        return invoke_model_fallback(supplier_id, wa_number, message)


# ── Fallback: suora InvokeModel (ennen kuin Agent on luotu) ─────────────────

MOCK_CONTEXT = """
TOIMITTAJAN DATA (demo):
Toimitukset: DEL-001 Prisma Tikkurila OK 312.50e, DEL-002 S-market Kerava REKLAMAATIO 156e, DEL-003 Prisma Tikkurila Laskutettu 390e
Avoin reklamaatio: REC-042 / S-market Kerava / Pakkausvaurio 3kpl / Maararaika 13.5.2026
Tilitys toukokuu: 1729e, eraantymispaiva 10.6.2026
Hyllysaatavuus: Sale Jarvenpaaa KRIITTINEN 15%, Prisma OK 72%, S-market Kerava SEURAA 45%
Avoin kysely: SURVEY-001 "Pystytteko toimittamaan 20% enemman luomuhilloja heinakuussa?"
"""

def invoke_model_fallback(supplier_id: str, wa_number: str, message: str) -> str:
    """Fallback suoraan InvokeModel-kutsuun jos Agent ei viela ole luotu."""
    import time
    history = []
    try:
        resp = conversations_table.get_item(Key={"session_id": f"wa-{wa_number}"})
        history = resp.get("Item", {}).get("messages", [])[-10:]
    except Exception:
        pass

    messages = history + [{"role": "user", "content": f"{message}\n\n[DATA]\n{MOCK_CONTEXT}"}]
    body = {"anthropic_version": "bedrock-2023-05-31", "max_tokens": 600,
            "system": SYSTEM_PROMPT, "messages": messages}
    try:
        resp = bedrock_runtime.invoke_model(modelId=BEDROCK_MODEL_ID,
            body=json.dumps(body), contentType="application/json", accept="application/json")
        reply = json.loads(resp["body"].read())["content"][0]["text"]
        history.append({"role": "user",      "content": message})
        history.append({"role": "assistant",  "content": reply})
        conversations_table.put_item(Item={
            "session_id": f"wa-{wa_number}", "messages": history[-20:],
            "ttl": int(time.time()) + 86400 * 7,
        })
        return reply
    except Exception as e:
        logger.error(f"Fallback model error: {e}")
        return "Tekninen ongelma. Yrita hetken kuluttua uudelleen."


def lambda_handler(event: dict, context) -> dict:
    logger.info(f"Webhook event: {json.dumps(event)}")

    # Meta webhook -vahvistus (GET)
    params = event.get("queryStringParameters") or {}
    if params.get("hub.mode") == "subscribe":
        if params.get("hub.verify_token") == WHATSAPP_VERIFY_TOKEN:
            return {"statusCode": 200, "body": params.get("hub.challenge", "")}
        return {"statusCode": 403, "body": "Forbidden"}

    # Saapuva viesti (POST)
    body = json.loads(event.get("body", "{}"))
    try:
        value    = body["entry"][0]["changes"][0]["value"]
        messages = value.get("messages", [])
    except (KeyError, IndexError):
        return {"statusCode": 200, "body": "ok"}

    if not messages or messages[0].get("type") != "text":
        return {"statusCode": 200, "body": "ok"}

    msg          = messages[0]
    wa_number    = msg["from"]
    text         = msg["text"]["body"]
    display_name = (value.get("contacts") or [{}])[0].get("profile", {}).get("name", wa_number)

    supplier    = get_or_create_supplier(wa_number, display_name)
    supplier_id = supplier["supplier_id"]

    # Tervehdys
    if text.strip().lower() in ["hei", "moi", "aloita", "start", "hello"]:
        reply = (
            f"Hei {display_name}! Olen assistenttisi.\n\n"
            "Kysy minulta suoraan esim:\n"
            "- Mika on toimitukseni DEL-002 tilanne?\n"
            "- Kirjaa reklamaatio toimituksesta DEL-002\n"
            "- Paljonko tilitys on tulossa?\n"
            "- Onko hyllypuutteita?\n"
            "- Aseta minut saamaan halytys aina reklamaatioista\n"
            "- Onko minulle kyselyita?"
        )
    else:
        # Kayta Bedrock Agentia jos maaritelty, muuten fallback
        if BEDROCK_AGENT_ID:
            reply = invoke_agent(supplier_id, wa_number, text)
        else:
            reply = invoke_model_fallback(supplier_id, wa_number, text)

    send_whatsapp(wa_number, reply)
    return {"statusCode": 200, "body": "ok"}
