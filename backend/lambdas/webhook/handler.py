import os
import json
import boto3
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
BEDROCK_AGENT_ID = os.environ["BEDROCK_AGENT_ID"]
BEDROCK_AGENT_ALIAS_ID = os.environ["BEDROCK_AGENT_ALIAS_ID"]

bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=os.environ.get("AWS_REGION", "eu-west-1"))
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "eu-west-1"))
suppliers_table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SUPPLIERS", "pientuottajat-suppliers"))


def get_or_create_supplier(telegram_user_id: str, username: str) -> dict:
    """Hae tai luo toimittajaprofiili DynamoDB:stä."""
    response = suppliers_table.get_item(Key={"supplier_id": f"tg_{telegram_user_id}"})
    if "Item" not in response:
        item = {
            "supplier_id": f"tg_{telegram_user_id}",
            "channel": "telegram",
            "channel_user_id": telegram_user_id,
            "username": username,
            "preferences": {
                "monthly_report_day": 1,
                "alert_on_reclamation": True,
                "alert_on_shelf_shortage": True,
            },
        }
        suppliers_table.put_item(Item=item)
        return item
    return response["Item"]


def invoke_bedrock_agent(supplier_id: str, session_id: str, message: str) -> str:
    """Lähetä viesti Bedrock Agentille ja palauta vastaus."""
    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=BEDROCK_AGENT_ID,
            agentAliasId=BEDROCK_AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=message,
            sessionState={
                "sessionAttributes": {"supplier_id": supplier_id},
            },
        )
        completion = ""
        for event in response.get("completion", []):
            chunk = event.get("chunk", {})
            if "bytes" in chunk:
                completion += chunk["bytes"].decode("utf-8")
        return completion or "Pahoittelen, en saanut vastausta. Yritä hetken kuluttua uudelleen."
    except Exception as e:
        logger.error(f"Bedrock Agent error: {e}")
        return "Tekninen ongelma. Ota yhteyttä tukeen."


def lambda_handler(event: dict, context) -> dict:
    """Lambda entry point — käsittelee Telegram webhook -kutsut."""
    logger.info(f"Event: {json.dumps(event)}")

    body = json.loads(event.get("body", "{}"))
    if "message" not in body:
        return {"statusCode": 200, "body": "ok"}

    message = body["message"]
    chat_id = str(message["chat"]["id"])
    user = message.get("from", {})
    user_id = str(user.get("id", chat_id))
    username = user.get("username", user.get("first_name", "Toimittaja"))
    text = message.get("text", "")

    supplier = get_or_create_supplier(user_id, username)
    session_id = f"tg-{chat_id}-session"

    if text.startswith("/start"):
        reply = (
            f"👋 Hei {username}! Olen pientuottaja-assistenttisi.\n\n"
            "Voit kysyä minulta esimerkiksi:\n"
            "• Viimeisimmät toimitukseni\n"
            "• Avoimet reklamaatiot\n"
            "• Kuukauden myynti alueosuuskaupoittain\n"
            "• Hyllysaatavuustilanne\n\n"
            "Voit myös asettaa automaattihälytyksiä, esim:\n"
            "_\"Hälytä minulle aina kun toimituksissani on poikkeama\"_"
        )
    else:
        reply = invoke_bedrock_agent(supplier["supplier_id"], session_id, text)

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        bot.send_message(chat_id=chat_id, text=reply, parse_mode="Markdown")
    )

    return {"statusCode": 200, "body": "ok"}
