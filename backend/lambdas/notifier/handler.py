import os
import json
import boto3
import logging
import urllib.request
import urllib.error
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")

dynamodb = boto3.resource("dynamodb")
suppliers_table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SUPPLIERS", "pientuottajat-suppliers"))


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


def notify_supplier(supplier: dict, message: str):
    channel = supplier.get("channel", "whatsapp")
    channel_user_id = supplier.get("channel_user_id")
    if channel == "whatsapp" and channel_user_id:
        send_whatsapp_message(channel_user_id, message)
    else:
        logger.warning(f"Tuntematon kanava tai puuttuva kayttajatunnus: {supplier}")


def get_all_suppliers() -> list:
    resp = suppliers_table.scan(ProjectionExpression="supplier_id, channel, channel_user_id, preferences")
    return resp.get("Items", [])


def lambda_handler(event: dict, context) -> dict:
    """
    Proaktiivinen notifier. Kaynnistyy:
    1. SQS-jonosta (Kafka-eventit: reklamaatio, hyllypuute)
    2. EventBridge Schedulerista (kuukausiraportti kaikille toimittajille)
    """
    logger.info(f"Notifier event: {json.dumps(event)}")

    for record in event.get("Records", []):
        body = json.loads(record.get("body", "{}"))
        event_type = body.get("event_type")

        # Broadcast kuukausiraportti kaikille toimittajille
        if event_type == "monthly_report" and body.get("broadcast"):
            month = datetime.now().strftime("%m/%Y")
            suppliers = get_all_suppliers()
            for supplier in suppliers:
                prefs = supplier.get("preferences", {})
                msg = (
                    f"Kuukausiraportti {month}\n\n"
                    f"Kokonaismyynti: 3 627 e (demo-data)\n"
                    f"- Prisma Tikkurila: 2 028 e\n"
                    f"- S-market Kerava: 1 157 e\n"
                    f"- Sale Jarvenpaaa: 442 e\n\n"
                    f"Kysy lisatietoja vastaamalla tahan viestiin!"
                )
                notify_supplier(supplier, msg)
            continue

        # Yksittaisen toimittajan halytys
        supplier_id = body.get("supplier_id")
        if not supplier_id:
            continue

        resp = suppliers_table.get_item(Key={"supplier_id": supplier_id})
        supplier = resp.get("Item")
        if not supplier:
            logger.warning(f"Toimittajaa ei loydy: {supplier_id}")
            continue

        prefs = supplier.get("preferences", {})

        if event_type == "reclamation" and prefs.get("alert_on_reclamation", True):
            store = body.get("store", "tuntematon myymala")
            reason = body.get("reason", "")
            msg = (
                f"REKLAMAATIO ILMOITETTU\n"
                f"Myymala: {store}\n"
                f"Syy: {reason}\n"
                f"Aika: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"Vastaa tahan viestiin lisatietoja varten."
            )
            notify_supplier(supplier, msg)

        elif event_type == "shelf_shortage" and prefs.get("alert_on_shelf_shortage", True):
            store = body.get("store", "tuntematon myymala")
            product = body.get("product", "")
            fill_pct = body.get("shelf_fill_pct", 0)
            msg = (
                f"HYLLYSAATAVUUSHÄLYTYS\n"
                f"Tuote: {product}\n"
                f"Myymala: {store}\n"
                f"Hyllytayttaste: {fill_pct}%\n"
                f"Aika: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            notify_supplier(supplier, msg)

    return {"statusCode": 200, "body": "ok"}
