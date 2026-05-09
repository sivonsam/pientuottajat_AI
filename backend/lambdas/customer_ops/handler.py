"""
Customer Ops Lambda — Pientuottajat AI

Kaupan puolen (alueosuuskauppa, hankintapaallikkoo) rajapinta.
Mahdollistaa:
  - Kyselyiden (survey) lahettaminen kaikille tai valituille toimittajille
  - Muistutusten lahettaminen (erapaiva, toimitustarve)
  - Proaktiivisten halytysten triggeroiminen
  - Joukkotiedottaminen (broadcast)

API-avain vaaditaan (AWS API Gateway API Key).
"""
import os
import json
import boto3
import logging
import urllib.request
import urllib.error
from datetime import datetime
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

WHATSAPP_TOKEN           = os.environ["WHATSAPP_TOKEN"]
WHATSAPP_PHONE_NUMBER_ID = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
REGION                   = os.environ.get("AWS_REGION", "eu-west-1")

dynamodb        = boto3.resource("dynamodb", region_name=REGION)
suppliers_table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SUPPLIERS", "pientuottajat-suppliers"))
surveys_table   = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SURVEYS",   "pientuottajat-surveys"))
sqs             = boto3.client("sqs", region_name=REGION)
SQS_URL         = os.environ.get("SQS_NOTIFICATION_QUEUE_URL", "")


def send_whatsapp(to: str, text: str):
    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = json.dumps({"messaging_product": "whatsapp", "to": to,
                          "type": "text", "text": {"body": text}}).encode()
    req = urllib.request.Request(url, data=payload, method="POST",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
        return True
    except urllib.error.HTTPError as e:
        logger.error(f"WhatsApp error {e.code}: {e.read().decode()}")
        return False


def get_all_suppliers(store_filter: str = None) -> list:
    """Hae kaikki toimittajat, optionaalisesti myymalan mukaan suodatettuna."""
    resp = suppliers_table.scan()
    suppliers = resp.get("Items", [])
    if store_filter:
        suppliers = [s for s in suppliers if store_filter in s.get("stores", [])]
    return suppliers


# ── Operaatiot ────────────────────────────────────────────────────────────────

def broadcast(body: dict) -> dict:
    """Laheta viesti kaikille tai valituille toimittajille."""
    message         = body.get("message", "")
    supplier_ids    = body.get("supplier_ids")   # None = kaikki
    from_name       = body.get("from", "S-ryhma")

    if not message:
        return {"statusCode": 400, "body": {"error": "message vaaditaan"}}

    suppliers = get_all_suppliers()
    if supplier_ids:
        suppliers = [s for s in suppliers if s["supplier_id"] in supplier_ids]

    sent, failed = 0, 0
    text = f"Viesti: {from_name}\n\n{message}"
    for s in suppliers:
        wa_id = s.get("channel_user_id")
        if wa_id:
            if send_whatsapp(wa_id, text):
                sent += 1
            else:
                failed += 1

    return {"statusCode": 200, "body": {"sent": sent, "failed": failed, "total": len(suppliers)}}


def create_survey(body: dict) -> dict:
    """Luo kysely ja laheta toimittajille."""
    question     = body.get("question", "")
    options      = body.get("options", [])     # esim. ["Kylla","Ei","Osittain"]
    deadline     = body.get("deadline", "")
    from_name    = body.get("from", "S-ryhma Hankinta")
    supplier_ids = body.get("supplier_ids")    # None = kaikki

    if not question:
        return {"statusCode": 400, "body": {"error": "question vaaditaan"}}

    survey_id = f"SURVEY-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    survey = {
        "id": survey_id, "question": question, "options": options,
        "deadline": deadline, "from": from_name,
        "status": "pending", "responses": {},
        "created_at": datetime.now().isoformat(),
    }
    surveys_table.put_item(Item=survey)

    # Laheta kysely toimittajille WhatsAppilla
    suppliers = get_all_suppliers()
    if supplier_ids:
        suppliers = [s for s in suppliers if s["supplier_id"] in supplier_ids]

    options_text = "\n".join([f"  {i+1}. {o}" for i, o in enumerate(options)]) if options else ""
    deadline_text = f"\nVastausaika: {deadline}" if deadline else ""
    text = (
        f"Kysely: {from_name}\n\n"
        f"{question}\n"
        f"{options_text}"
        f"{deadline_text}\n\n"
        f"Vastaa kirjoittamalla minulle tai valitsemalla vaihtoehto numerolla."
    )
    sent = 0
    for s in suppliers:
        wa_id = s.get("channel_user_id")
        if wa_id and send_whatsapp(wa_id, text):
            sent += 1

    return {"statusCode": 200, "body": {"survey_id": survey_id, "sent": sent}}


def send_reminder(body: dict) -> dict:
    """Laheta muistutus yhdelle tai useammalle toimittajalle."""
    reminder_type  = body.get("type", "custom")   # due_date | delivery_needed | shelf_alert | custom
    supplier_ids   = body.get("supplier_ids", [])
    custom_message = body.get("message", "")
    from_name      = body.get("from", "S-ryhma")

    templates = {
        "due_date": lambda b: (
            f"Muistutus: {from_name}\n\n"
            f"Laskusi eraantymispaiva lahestyy: {b.get('due_date','')}\n"
            f"Summa: {b.get('amount_eur','')} e\n"
            f"Viite: {b.get('reference','')}"
        ),
        "delivery_needed": lambda b: (
            f"Toimituspyynto: {from_name}\n\n"
            f"Myymala {b.get('store','')} tarvitsee lisatoimituksen:\n"
            f"Tuote: {b.get('product','')}\n"
            f"Maara: {b.get('quantity','')}\n"
            f"Toivottu toimituspaiva: {b.get('delivery_date','')}"
        ),
        "shelf_alert": lambda b: (
            f"Hyllysaatavuushälytys: {from_name}\n\n"
            f"Myymala {b.get('store','')} hyllytayttaste {b.get('fill_pct','')}%\n"
            f"Tuote: {b.get('product','')}\n"
            f"Toimita pian!"
        ),
        "custom": lambda b: f"Viesti: {from_name}\n\n{custom_message}",
    }

    text = templates.get(reminder_type, templates["custom"])(body)

    suppliers = get_all_suppliers()
    if supplier_ids:
        suppliers = [s for s in suppliers if s["supplier_id"] in supplier_ids]

    sent = 0
    for s in suppliers:
        wa_id = s.get("channel_user_id")
        if wa_id and send_whatsapp(wa_id, text):
            sent += 1

    return {"statusCode": 200, "body": {"sent": sent, "type": reminder_type}}


def get_survey_results(body: dict) -> dict:
    """Hae kyselyn tulokset."""
    survey_id = body.get("survey_id", "")
    if not survey_id:
        return {"statusCode": 400, "body": {"error": "survey_id vaaditaan"}}
    resp = surveys_table.get_item(Key={"id": survey_id})
    survey = resp.get("Item", {})
    responses = survey.get("responses", {})
    summary = {}
    for _, r in responses.items():
        ans = r.get("answer", "muu")
        summary[ans] = summary.get(ans, 0) + 1
    return {"statusCode": 200, "body": {
        "survey_id": survey_id, "question": survey.get("question"),
        "total_responses": len(responses), "summary": summary,
        "responses": responses,
    }}


# ── Lambda handler ────────────────────────────────────────────────────────────

ROUTES = {
    ("POST", "/customer/broadcast"):      broadcast,
    ("POST", "/customer/survey"):         create_survey,
    ("POST", "/customer/reminder"):       send_reminder,
    ("GET",  "/customer/survey/results"): get_survey_results,
}

def lambda_handler(event: dict, context) -> dict:
    logger.info(f"Customer ops: {json.dumps(event)}")

    method   = event.get("httpMethod", "POST")
    path     = event.get("path", "")
    body_raw = event.get("body", "{}")
    body     = json.loads(body_raw) if isinstance(body_raw, str) else (body_raw or {})

    # Query params myos bodyyn (GET-kyselyille)
    body.update(event.get("queryStringParameters") or {})

    handler_fn = ROUTES.get((method, path))
    if not handler_fn:
        return {"statusCode": 404, "body": json.dumps({"error": f"Reittia ei loydy: {method} {path}"})}

    result = handler_fn(body)
    return {
        "statusCode": result["statusCode"],
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result["body"], ensure_ascii=False),
    }
