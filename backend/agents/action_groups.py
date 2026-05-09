"""
Bedrock Agent Action Groups — Pientuottajat AI

Tama Lambda toimii Bedrock Agentin Action Group -handlerina.
Agentin AI (Claude) paattaa itse mita toimintoja kutsutaan
perustuen toimittajan viestiin.

Toiminnot:
  getDeliveries          — viimeisimmat toimitukset (filtterit: jakso, myymala, status)
  getSettlements         — tilitykset ja maksujen status
  getReclamations        — avoimet reklamaatiot
  submitReclamation      — luo uusi reklamaatio toimittajan puolelta
  respondToReclamation   — vastaa reklamaatioon (liite, kommentti)
  getShelfAvailability   — hyllysaatavuus myymaloittain
  updateAlertPreferences — aseta mitka halytykset toimittaja haluaa
  getSurveyQuestions     — hae asiakkaan lahettamat kyselyt (odottaa vastausta)
  submitSurveyResponse   — vastaa kyselyyn
"""
import os
import json
import logging
import boto3
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

USE_MOCK = os.environ.get("USE_MOCK_DATA", "True") == "True"

dynamodb = boto3.resource("dynamodb")
suppliers_table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SUPPLIERS", "pientuottajat-suppliers"))
surveys_table   = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SURVEYS",   "pientuottajat-surveys"))


# ─────────────────────────────────────────────────────────────────────────────
# Mock data — korvautuu oikeilla integraatioilla pilottivaiheessa
# ─────────────────────────────────────────────────────────────────────────────

MOCK_DELIVERIES = [
    {"id": "DEL-001", "date": "2026-05-07", "store": "Prisma Tikkurila",  "status": "Vastaanotettu", "items": 24, "value_eur": 312.50, "products": ["Luomuhillo 400g x24"]},
    {"id": "DEL-002", "date": "2026-05-05", "store": "S-market Kerava",   "status": "Reklamaatio",   "items": 12, "value_eur": 156.00, "products": ["Luomuhillo 400g x12"]},
    {"id": "DEL-003", "date": "2026-05-02", "store": "Prisma Tikkurila",  "status": "Laskutettu",    "items": 30, "value_eur": 390.00, "products": ["Luomuhillo 400g x30"]},
    {"id": "DEL-004", "date": "2026-04-28", "store": "Sale Jarvenpaaa",   "status": "Tilitetty",     "items": 18, "value_eur": 234.00, "products": ["Luomuhillo 400g x18"]},
]

MOCK_SETTLEMENTS = [
    {"id": "TIL-2026-04", "period": "Huhtikuu 2026", "stores": ["Prisma Tikkurila","S-market Kerava","Sale Jarvenpaaa"],
     "gross_eur": 3627.00, "commission_eur": 181.35, "net_eur": 3445.65,
     "status": "Tilitetty", "payment_date": "2026-05-10", "reference": "REF20260410"},
    {"id": "TIL-2026-03", "period": "Maaliskuu 2026", "stores": ["Prisma Tikkurila","S-market Kerava"],
     "gross_eur": 2890.00, "commission_eur": 144.50, "net_eur": 2745.50,
     "status": "Tilitetty", "payment_date": "2026-04-10", "reference": "REF20260310"},
    {"id": "TIL-2026-05", "period": "Toukokuu 2026",  "stores": ["Prisma Tikkurila","S-market Kerava","Sale Jarvenpaaa"],
     "gross_eur": 1820.00, "commission_eur": 91.00,  "net_eur": 1729.00,
     "status": "Avoin — eraantymispaiva 10.6.2026", "payment_date": "2026-06-10", "reference": None},
]

MOCK_RECLAMATIONS = [
    {"id": "REC-042", "delivery_id": "DEL-002", "date": "2026-05-06",
     "store": "S-market Kerava", "reason": "Pakkausvaurio — 3 kpl",
     "status": "Avoin", "deadline": "2026-05-13",
     "compensation_eur": 39.00, "notes": "Toimittaja ei ole viela vastannut"},
]

MOCK_SHELF = [
    {"store": "Sale Jarvenpaaa",  "product": "Luomuhillo 400g", "fill_pct": 15, "level": "KRIITTINEN",  "last_delivery_days_ago": 7},
    {"store": "Prisma Tikkurila", "product": "Luomuhillo 400g", "fill_pct": 72, "level": "OK",          "last_delivery_days_ago": 2},
    {"store": "S-market Kerava",  "product": "Luomuhillo 400g", "fill_pct": 45, "level": "SEURAA",      "last_delivery_days_ago": 5},
]


# ─────────────────────────────────────────────────────────────────────────────
# Toiminnot
# ─────────────────────────────────────────────────────────────────────────────

def get_deliveries(supplier_id: str, params: dict) -> dict:
    if USE_MOCK:
        store_filter  = params.get("store", "").lower()
        status_filter = params.get("status", "").lower()
        results = MOCK_DELIVERIES
        if store_filter:
            results = [d for d in results if store_filter in d["store"].lower()]
        if status_filter:
            results = [d for d in results if status_filter in d["status"].lower()]
        return {"deliveries": results, "total": len(results)}
    # TODO: Confluent Kafka / WMS integraatio


def get_settlements(supplier_id: str, params: dict) -> dict:
    if USE_MOCK:
        period_filter = params.get("period", "").lower()
        results = MOCK_SETTLEMENTS
        if period_filter:
            results = [s for s in results if period_filter in s["period"].lower()]
        return {
            "settlements": results,
            "next_payment": {"amount_eur": 1729.00, "date": "2026-06-10", "period": "Toukokuu 2026"},
        }
    # TODO: SAP BTP OData integraatio


def get_reclamations(supplier_id: str, params: dict) -> dict:
    if USE_MOCK:
        status_filter = params.get("status", "avoin").lower()
        results = [r for r in MOCK_RECLAMATIONS if status_filter in r["status"].lower()]
        return {"reclamations": results, "open_count": len(results)}
    # TODO: SAP BTP / reklamaatiojarjestelma


def submit_reclamation(supplier_id: str, params: dict) -> dict:
    delivery_id = params.get("delivery_id", "")
    reason      = params.get("reason", "")
    description = params.get("description", "")
    if not delivery_id or not reason:
        return {"success": False, "error": "delivery_id ja reason vaaditaan"}
    rec_id = f"REC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    if USE_MOCK:
        return {
            "success": True,
            "reclamation_id": rec_id,
            "message": f"Reklamaatio {rec_id} kirjattu toimitukselle {delivery_id}. Saat vahvistuksen 1-2 arkipaivan kuluessa.",
            "delivery_id": delivery_id,
            "reason": reason,
        }
    # TODO: Kirjaa SAP BTP:hen


def respond_to_reclamation(supplier_id: str, params: dict) -> dict:
    rec_id  = params.get("reclamation_id", "")
    comment = params.get("comment", "")
    if not rec_id:
        return {"success": False, "error": "reclamation_id vaaditaan"}
    if USE_MOCK:
        return {
            "success": True,
            "message": f"Vastauksesi reklamaatioon {rec_id} on kirjattu. Kaupan ostaja kasittelee sen 2 arkipaivan kuluessa.",
        }


def get_shelf_availability(supplier_id: str, params: dict) -> dict:
    if USE_MOCK:
        store_filter = params.get("store", "").lower()
        results = MOCK_SHELF
        if store_filter:
            results = [s for s in results if store_filter in s["store"].lower()]
        critical = [s for s in results if s["level"] == "KRIITTINEN"]
        return {"stores": results, "critical_count": len(critical), "all_ok": len(critical) == 0}
    # TODO: Snowflake hyllysaatavuusdata


def update_alert_preferences(supplier_id: str, params: dict) -> dict:
    prefs = {
        "alert_on_reclamation":     params.get("alert_on_reclamation", True),
        "alert_on_shelf_shortage":  params.get("alert_on_shelf_shortage", True),
        "alert_on_payment":         params.get("alert_on_payment", True),
        "monthly_report_day":       int(params.get("monthly_report_day", 1)),
        "weekly_summary":           params.get("weekly_summary", False),
    }
    suppliers_table.update_item(
        Key={"supplier_id": supplier_id},
        UpdateExpression="SET preferences = :p, updated_at = :t",
        ExpressionAttributeValues={":p": prefs, ":t": datetime.now().isoformat()},
    )
    return {"success": True, "preferences": prefs,
            "message": "Halytysasetukset tallennettu. Voit muuttaa niita milloin tahansa."}


def get_survey_questions(supplier_id: str, params: dict) -> dict:
    try:
        resp = surveys_table.scan(
            FilterExpression="attribute_exists(supplier_id) AND supplier_id = :sid AND #st = :s",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={":sid": supplier_id, ":s": "pending"},
        )
        surveys = resp.get("Items", [])
    except Exception:
        surveys = []
    if USE_MOCK and not surveys:
        surveys = [{"id": "SURVEY-001", "question": "Pystytteko toimittamaan 20% enemman luomuhilloja heinakuussa 2026?",
                    "deadline": "2026-05-15", "from": "Hankintapaallikkoo, S-ryhmä", "options": ["Kylla","Ei","Osittain"]}]
    return {"pending_surveys": surveys, "count": len(surveys)}


def submit_survey_response(supplier_id: str, params: dict) -> dict:
    survey_id = params.get("survey_id", "")
    answer    = params.get("answer", "")
    comment   = params.get("comment", "")
    if not survey_id or not answer:
        return {"success": False, "error": "survey_id ja answer vaaditaan"}
    try:
        surveys_table.update_item(
            Key={"id": survey_id},
            UpdateExpression="SET responses.#sid = :r, #st = :s",
            ExpressionAttributeNames={"#sid": supplier_id, "#st": "status"},
            ExpressionAttributeValues={":r": {"answer": answer, "comment": comment, "ts": datetime.now().isoformat()}, ":s": "answered"},
        )
    except Exception:
        pass
    return {"success": True, "message": f"Vastauksesi '{answer}' on kirjattu kyselyyn. Kiitos!"}


# ─────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────────────────────────────────────

ACTIONS = {
    "/getDeliveries":          get_deliveries,
    "/getSettlements":         get_settlements,
    "/getReclamations":        get_reclamations,
    "/submitReclamation":      submit_reclamation,
    "/respondToReclamation":   respond_to_reclamation,
    "/getShelfAvailability":   get_shelf_availability,
    "/updateAlertPreferences": update_alert_preferences,
    "/getSurveyQuestions":     get_survey_questions,
    "/submitSurveyResponse":   submit_survey_response,
}


def lambda_handler(event: dict, context) -> dict:
    logger.info(f"Action group event: {json.dumps(event)}")

    action_group = event.get("actionGroup", "")
    api_path     = event.get("apiPath", "")
    http_method  = event.get("httpMethod", "GET")

    # Supplier ID session-attribuuteista (asetetaan webhook-handlerissa)
    session_attrs = event.get("sessionAttributes", {})
    supplier_id   = session_attrs.get("supplier_id", "demo_supplier")

    # Parametrit (GET query params tai POST body)
    params = {}
    for p in event.get("parameters", []):
        params[p["name"]] = p["value"]
    for prop in (event.get("requestBody", {}).get("content", {})
                 .get("application/json", {}).get("properties", [])):
        params[prop["name"]] = prop["value"]

    handler_fn = ACTIONS.get(api_path)
    if not handler_fn:
        result, status = {"error": f"Tuntematon toiminto: {api_path}"}, 400
    else:
        try:
            result, status = handler_fn(supplier_id, params), 200
        except Exception as e:
            logger.error(f"Action error in {api_path}: {e}")
            result, status = {"error": str(e)}, 500

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "apiPath": api_path,
            "httpMethod": http_method,
            "httpStatusCode": status,
            "responseBody": {"application/json": {"body": json.dumps(result, ensure_ascii=False)}},
        },
    }
