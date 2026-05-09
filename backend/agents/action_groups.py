import os
import json
import boto3
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Demo: mock-data jos oikeita integraatioita ei vielä ole
USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "True") == "True"

dynamodb = boto3.resource("dynamodb")
suppliers_table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SUPPLIERS", "pientuottajat-suppliers"))


def get_deliveries(supplier_id: str, event: dict, context) -> dict:
    """Action: hae toimittajan viimeisimmät toimitukset."""
    if USE_MOCK_DATA:
        return {
            "deliveries": [
                {"id": "DEL-001", "date": "2026-05-07", "store": "Prisma Tikkurila", "status": "Vastaanotettu", "items": 24, "value_eur": 312.50},
                {"id": "DEL-002", "date": "2026-05-05", "store": "S-market Kerava", "status": "Reklamaatio", "items": 12, "value_eur": 156.00},
                {"id": "DEL-003", "date": "2026-05-02", "store": "Prisma Tikkurila", "status": "Laskutettu", "items": 30, "value_eur": 390.00},
            ]
        }
    # TODO: Oikea integraatio Confluent Kafkaan / WMS


def get_reclamations(supplier_id: str, event: dict, context) -> dict:
    """Action: hae avoimet reklamaatiot."""
    if USE_MOCK_DATA:
        return {
            "reclamations": [
                {
                    "id": "REC-042",
                    "delivery_id": "DEL-002",
                    "date": "2026-05-06",
                    "store": "S-market Kerava",
                    "reason": "Pakkausvaurio — 3 kpl",
                    "status": "Avoin",
                    "resolution_deadline": "2026-05-13",
                }
            ]
        }
    # TODO: SAP BTP OData -integraatio


def get_sales_by_store(supplier_id: str, event: dict, context) -> dict:
    """Action: hae myyntidata alueosuuskaupoittain."""
    month = event.get("month", datetime.now().strftime("%Y-%m"))
    if USE_MOCK_DATA:
        return {
            "month": month,
            "sales": [
                {"store": "Prisma Tikkurila", "units_sold": 156, "revenue_eur": 2028.00},
                {"store": "S-market Kerava", "units_sold": 89, "revenue_eur": 1157.00},
                {"store": "Sale Järvenpää", "units_sold": 34, "revenue_eur": 442.00},
            ],
            "total_revenue_eur": 3627.00,
        }
    # TODO: Snowflake connector


def get_shelf_availability(supplier_id: str, event: dict, context) -> dict:
    """Action: hae hyllysaatavuustilanne."""
    if USE_MOCK_DATA:
        return {
            "timestamp": datetime.now().isoformat(),
            "alerts": [
                {"store": "Sale Järvenpää", "product": "Luomuhillot 400g", "shelf_fill_pct": 15, "status": "KRIITTINEN"},
            ],
            "all_ok": [
                {"store": "Prisma Tikkurila", "status": "OK"},
                {"store": "S-market Kerava", "status": "OK"},
            ],
        }
    # TODO: Snowflake hyllysaatavuusdata


def update_preferences(supplier_id: str, event: dict, context) -> dict:
    """Action: päivitä toimittajan hälytyspreferenssit."""
    preferences = event.get("preferences", {})
    suppliers_table.update_item(
        Key={"supplier_id": supplier_id},
        UpdateExpression="SET preferences = :p",
        ExpressionAttributeValues={":p": preferences},
    )
    return {"status": "ok", "message": "Hälytyspreferenssit päivitetty."}


# Action Group dispatcher
ACTIONS = {
    "getDeliveries": get_deliveries,
    "getReclamations": get_reclamations,
    "getSalesByStore": get_sales_by_store,
    "getShelfAvailability": get_shelf_availability,
    "updatePreferences": update_preferences,
}


def lambda_handler(event: dict, context) -> dict:
    """Bedrock Agent Action Group Lambda handler."""
    logger.info(f"Bedrock action event: {json.dumps(event)}")

    action_group = event.get("actionGroup", "")
    api_path = event.get("apiPath", "")
    http_method = event.get("httpMethod", "GET")
    parameters = event.get("parameters", [])
    request_body = event.get("requestBody", {})

    # Hae supplier_id session-attribuuteista
    session_attrs = event.get("sessionAttributes", {})
    supplier_id = session_attrs.get("supplier_id", "unknown")

    # Parsitaan parametrit
    params = {p["name"]: p["value"] for p in parameters} if parameters else {}

    # Yhdistetään request body parametreihin
    body_content = request_body.get("content", {}).get("application/json", {}).get("properties", [])
    for prop in body_content:
        params[prop["name"]] = prop["value"]

    # Dispatching
    action_name = api_path.strip("/").replace("-", "_")
    # Etsi action camelCase nimellä
    handler_fn = None
    for key, fn in ACTIONS.items():
        if key.lower() == action_name.lower() or f"/{key.lower()}" == api_path.lower():
            handler_fn = fn
            break

    if not handler_fn:
        result = {"error": f"Tuntematon toiminto: {api_path}"}
        status_code = 400
    else:
        try:
            result = handler_fn(supplier_id, params, context)
            status_code = 200
        except Exception as e:
            logger.error(f"Action error: {e}")
            result = {"error": str(e)}
            status_code = 500

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "apiPath": api_path,
            "httpMethod": http_method,
            "httpStatusCode": status_code,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(result, ensure_ascii=False)
                }
            },
        },
    }
