"""
Event Processor Lambda — Pientuottajat AI

Kasittelee asiakkaan jarjestelmista tulevia eventteja
(Confluent Kafka → SQS) ja triggeroi proaktiiviset
WhatsApp-halytykset oikeille toimittajille.

Demo: SQS-viestit simuloivat Kafka-eventteja.
Tuotanto: Confluent Kafka consumer Lambda triggeraa taman.

Eventtityypit:
  reclamation_created   — kauppa loi reklamaation toimittajalle
  shelf_shortage        — hyllysaatavuus kriittinen
  payment_due           — tilityksen erapaiva lahestyy
  delivery_deviation    — toimituspoikkeama (vajaus, laatu)
  new_survey            — uusi kysely lahetetty (lahetetaan customer_ops:sta)
"""
import os
import json
import boto3
import logging
import urllib.request
import urllib.error
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

WHATSAPP_TOKEN           = os.environ["WHATSAPP_TOKEN"]
WHATSAPP_PHONE_NUMBER_ID = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
REGION                   = os.environ.get("AWS_REGION", "eu-west-1")

dynamodb        = boto3.resource("dynamodb", region_name=REGION)
suppliers_table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SUPPLIERS", "pientuottajat-suppliers"))


def send_whatsapp(to: str, text: str):
    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = json.dumps({"messaging_product": "whatsapp", "to": to,
                          "type": "text", "text": {"body": text}}).encode()
    req = urllib.request.Request(url, data=payload, method="POST",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as e:
        logger.error(f"WA error {e.code}: {e.read().decode()}")


def get_supplier(supplier_id: str) -> dict:
    resp = suppliers_table.get_item(Key={"supplier_id": supplier_id})
    return resp.get("Item", {})


def notify(supplier: dict, message: str):
    wa_id = supplier.get("channel_user_id")
    if wa_id:
        send_whatsapp(wa_id, message)
    else:
        logger.warning(f"Ei kanavaa toimittajalle: {supplier.get('supplier_id')}")


# ── Eventtikohtaiset viestit ─────────────────────────────────────────────────

def handle_reclamation_created(event_data: dict, supplier: dict):
    prefs = supplier.get("preferences", {})
    if not prefs.get("alert_on_reclamation", True):
        return
    notify(supplier,
        f"UUSI REKLAMAATIO\n"
        f"Reklamaatio {event_data.get('reclamation_id','')} on avattu\n"
        f"Toimitus: {event_data.get('delivery_id','')}\n"
        f"Myymala: {event_data.get('store','')}\n"
        f"Syy: {event_data.get('reason','')}\n"
        f"Vastausaika: {event_data.get('deadline','')}\n\n"
        f"Vastaa kirjoittamalla minulle tai kayma asiakasportaalissa."
    )


def handle_shelf_shortage(event_data: dict, supplier: dict):
    prefs = supplier.get("preferences", {})
    if not prefs.get("alert_on_shelf_shortage", True):
        return
    fill_pct = event_data.get("fill_pct", 0)
    notify(supplier,
        f"HYLLYSAATAVUUSHÄLYTYS\n"
        f"Myymala: {event_data.get('store','')}\n"
        f"Tuote: {event_data.get('product','')}\n"
        f"Hyllytayttaste: {fill_pct}%\n"
        f"Taso: {'KRIITTINEN' if fill_pct < 20 else 'MATALA'}\n"
        f"Edellinen toimitus: {event_data.get('last_delivery_days_ago','')} pv sitten\n\n"
        f"Suosittelemme pikatolmitusta."
    )


def handle_payment_due(event_data: dict, supplier: dict):
    prefs = supplier.get("preferences", {})
    if not prefs.get("alert_on_payment", True):
        return
    notify(supplier,
        f"MAKSUMUISTUTUS\n"
        f"Tilitysjakso: {event_data.get('period','')}\n"
        f"Summa: {event_data.get('amount_eur','')} e\n"
        f"Erapaiva: {event_data.get('due_date','')}\n"
        f"Viite: {event_data.get('reference','')}\n\n"
        f"Kysy lisatietoja vastaamalla tahan viestiin."
    )


def handle_delivery_deviation(event_data: dict, supplier: dict):
    notify(supplier,
        f"TOIMITUSPOIKKEAMA HAVAITTU\n"
        f"Toimitus: {event_data.get('delivery_id','')}\n"
        f"Myymala: {event_data.get('store','')}\n"
        f"Poikkeama: {event_data.get('deviation_type','')}\n"
        f"Yksityiskohdat: {event_data.get('details','')}\n\n"
        f"Ota yhteytta ostajaan tai kirjaa vastine minulle."
    )


# ── Broadcast EventBridge schedulerista (kuukausiraportti) ───────────────────

def handle_monthly_report(event_data: dict):
    month   = datetime.now().strftime("%m/%Y")
    resp    = suppliers_table.scan()
    for supplier in resp.get("Items", []):
        notify(supplier,
            f"KUUKAUSIRAPORTTI {month}\n\n"
            f"Kokonaismyynti: 3 627 e\n"
            f"- Prisma Tikkurila: 2 028 e\n"
            f"- S-market Kerava: 1 157 e\n"
            f"- Sale Jarvenpaaa: 442 e\n\n"
            f"Tilitys: 1 729 e, erapaiva 10.6.2026\n\n"
            f"Kysy lisatietoja vastaamalla tahan viestiin!"
        )


# ── Dispatcher ────────────────────────────────────────────────────────────────

HANDLERS = {
    "reclamation_created": handle_reclamation_created,
    "shelf_shortage":      handle_shelf_shortage,
    "payment_due":         handle_payment_due,
    "delivery_deviation":  handle_delivery_deviation,
}


def lambda_handler(event: dict, context) -> dict:
    logger.info(f"Event processor: {json.dumps(event)}")

    for record in event.get("Records", []):
        try:
            body       = json.loads(record.get("body", "{}"))
            event_type = body.get("event_type", "")
            supplier_id = body.get("supplier_id")

            # Broadcast (EventBridge scheduler)
            if event_type == "monthly_report":
                handle_monthly_report(body)
                continue

            if not supplier_id:
                logger.warning(f"Ei supplier_id eventille: {event_type}")
                continue

            supplier = get_supplier(supplier_id)
            if not supplier:
                logger.warning(f"Toimittajaa ei loydy: {supplier_id}")
                continue

            handler_fn = HANDLERS.get(event_type)
            if handler_fn:
                handler_fn(body, supplier)
            else:
                logger.warning(f"Tuntematon eventtitype: {event_type}")

        except Exception as e:
            logger.error(f"Event processing error: {e} — record: {record}")

    return {"statusCode": 200, "body": "ok"}
