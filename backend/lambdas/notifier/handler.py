import os
import json
import boto3
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
dynamodb = boto3.resource("dynamodb")
suppliers_table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SUPPLIERS", "pientuottajat-suppliers"))


def send_telegram_message(chat_id: str, text: str):
    import urllib.request
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)


def notify_supplier(supplier: dict, message: str):
    """Lähetä proaktiivinen viesti toimittajalle hänen valitsemallaan kanavalla."""
    channel = supplier.get("channel", "telegram")
    channel_user_id = supplier.get("channel_user_id")

    if channel == "telegram" and channel_user_id:
        send_telegram_message(channel_user_id, message)
    else:
        logger.warning(f"Tuntematon kanava tai puuttuva käyttäjätunnus: {supplier}")


def lambda_handler(event: dict, context) -> dict:
    """
    Proaktiivinen notifier — käynnistyy:
    1. SQS-jonosta (Kafka-eventit: reklamaatio, hyllypuute)
    2. Step Functions -ajastuksesta (kuukausiraportti)
    """
    logger.info(f"Notifier event: {json.dumps(event)}")

    # SQS-viestit
    for record in event.get("Records", []):
        body = json.loads(record.get("body", "{}"))
        event_type = body.get("event_type")
        supplier_id = body.get("supplier_id")

        if not supplier_id:
            continue

        resp = suppliers_table.get_item(Key={"supplier_id": supplier_id})
        supplier = resp.get("Item")
        if not supplier:
            logger.warning(f"Toimittajaa ei löydy: {supplier_id}")
            continue

        prefs = supplier.get("preferences", {})

        if event_type == "reclamation" and prefs.get("alert_on_reclamation", True):
            store = body.get("store", "tuntematon myymälä")
            reason = body.get("reason", "")
            msg = (
                f"⚠️ *Reklamaatio ilmoitettu*\n"
                f"Myymälä: {store}\n"
                f"Syy: {reason}\n"
                f"Aika: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"Vastaa tähän viestiin tai kirjaudu portaaliin lisätietoja varten."
            )
            notify_supplier(supplier, msg)

        elif event_type == "shelf_shortage" and prefs.get("alert_on_shelf_shortage", True):
            store = body.get("store", "tuntematon myymälä")
            product = body.get("product", "")
            fill_pct = body.get("shelf_fill_pct", 0)
            msg = (
                f"📦 *Hyllysaatavuushälytys*\n"
                f"Tuote: {product}\n"
                f"Myymälä: {store}\n"
                f"Hyllytäyttöaste: {fill_pct}%\n"
                f"Aika: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            notify_supplier(supplier, msg)

        elif event_type == "monthly_report":
            month = body.get("month", datetime.now().strftime("%m/%Y"))
            revenue = body.get("total_revenue_eur", 0)
            msg = (
                f"📊 *Kuukausiraportti {month}*\n"
                f"Kokonaismyynti: {revenue:.2f} €\n\n"
                f"Kysy lisätietoja myymäläkohtaisesta myynnistä!"
            )
            notify_supplier(supplier, msg)

    return {"statusCode": 200, "body": "ok"}
