#!/bin/bash
# setup_bedrock_agent.sh — Luo Amazon Bedrock Agent kaikilla action groupeilla
# Aja CDK-deployn jälkeen: ./setup_bedrock_agent.sh <ActionGroupsLambdaArn>
set -e

LAMBDA_ARN="${1:?Anna ActionGroupsLambdaArn parametrina}"
REGION="${AWS_DEFAULT_REGION:-eu-west-1}"
AGENT_NAME="pientuottajat-agent"

echo "Luodaan Bedrock Agent..."

# IAM Role
ROLE_ARN=$(aws iam create-role \
  --role-name "AmazonBedrockExecutionRoleForAgents_pientuottajat" \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"bedrock.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
  --query "Role.Arn" --output text 2>/dev/null || \
  aws iam get-role --role-name "AmazonBedrockExecutionRoleForAgents_pientuottajat" --query "Role.Arn" --output text)

aws iam attach-role-policy --role-name "AmazonBedrockExecutionRoleForAgents_pientuottajat" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonBedrockFullAccess" 2>/dev/null || true

echo "  IAM Role: $ROLE_ARN"
sleep 5  # IAM propagation

# Bedrock Agent
AGENT_ID=$(aws bedrock-agent create-agent \
  --agent-name "$AGENT_NAME" \
  --agent-resource-role-arn "$ROLE_ARN" \
  --foundation-model "anthropic.claude-3-haiku-20240307-v1:0" \
  --instruction "$(cat <<'INSTR'
Olet pientuottaja-assistentti SOK:n alueosuuskauppojen pientoimittajille.

Tehtavasi: auta toimittajia seuraamaan toimituksia, tilityksia, reklamaatioita ja hyllysaatavuutta.
Ole proaktiivinen — mainitse avoimet reklamaatiot ja kriittiset hyllypuutteet automaattisesti.
Toimittaja voi luoda reklamaatioita ja vastata asiakkaan kyselyihin sinun kauttasi.
Kayta aina suomea. Vastaa lyhyesti. Ei markdown-muotoilua.
INSTR
)" \
  --region "$REGION" \
  --query "agent.agentId" --output text)

echo "  Agent ID: $AGENT_ID"

# OpenAPI schema
SCHEMA=$(cat <<'SCHEMA'
{
  "openapi": "3.0.0",
  "info": {"title": "Pientuottajat API", "version": "1.0"},
  "paths": {
    "/getDeliveries": {
      "get": {
        "operationId": "getDeliveries",
        "summary": "Hae toimittajan toimitukset",
        "parameters": [
          {"name": "store",  "in": "query", "schema": {"type": "string"}, "description": "Myymalan nimi suodatukseen"},
          {"name": "status", "in": "query", "schema": {"type": "string"}, "description": "Tila: Vastaanotettu, Laskutettu, Reklamaatio, Tilitetty"}
        ],
        "responses": {"200": {"description": "Toimitukset"}}
      }
    },
    "/getSettlements": {
      "get": {
        "operationId": "getSettlements",
        "summary": "Hae tilitykset ja maksujen status",
        "parameters": [
          {"name": "period", "in": "query", "schema": {"type": "string"}, "description": "Jakso esim. huhtikuu"}
        ],
        "responses": {"200": {"description": "Tilitysdata"}}
      }
    },
    "/getReclamations": {
      "get": {
        "operationId": "getReclamations",
        "summary": "Hae avoimet reklamaatiot",
        "parameters": [
          {"name": "status", "in": "query", "schema": {"type": "string"}, "description": "Tila: avoin, kasitelty"}
        ],
        "responses": {"200": {"description": "Reklamaatiot"}}
      }
    },
    "/submitReclamation": {
      "post": {
        "operationId": "submitReclamation",
        "summary": "Luo uusi reklamaatio toimittajan puolelta",
        "requestBody": {
          "required": true,
          "content": {"application/json": {"schema": {
            "type": "object",
            "required": ["delivery_id", "reason"],
            "properties": {
              "delivery_id":  {"type": "string", "description": "Toimituksen ID esim. DEL-002"},
              "reason":       {"type": "string", "description": "Reklamaation syy lyhyesti"},
              "description":  {"type": "string", "description": "Tarkempi kuvaus"}
            }
          }}}
        },
        "responses": {"200": {"description": "Reklamaation kuittaus"}}
      }
    },
    "/respondToReclamation": {
      "post": {
        "operationId": "respondToReclamation",
        "summary": "Vastaa avoimeen reklamaatioon",
        "requestBody": {
          "required": true,
          "content": {"application/json": {"schema": {
            "type": "object",
            "required": ["reclamation_id", "comment"],
            "properties": {
              "reclamation_id": {"type": "string"},
              "comment":        {"type": "string", "description": "Toimittajan vastine"}
            }
          }}}
        },
        "responses": {"200": {"description": "Kuittaus"}}
      }
    },
    "/getShelfAvailability": {
      "get": {
        "operationId": "getShelfAvailability",
        "summary": "Hae hyllysaatavuustilanne myymaloittain",
        "parameters": [
          {"name": "store", "in": "query", "schema": {"type": "string"}}
        ],
        "responses": {"200": {"description": "Hyllysaatavuusdata"}}
      }
    },
    "/updateAlertPreferences": {
      "post": {
        "operationId": "updateAlertPreferences",
        "summary": "Paivita toimittajan halytysasetukset",
        "requestBody": {
          "required": true,
          "content": {"application/json": {"schema": {
            "type": "object",
            "properties": {
              "alert_on_reclamation":    {"type": "boolean"},
              "alert_on_shelf_shortage": {"type": "boolean"},
              "alert_on_payment":        {"type": "boolean"},
              "weekly_summary":          {"type": "boolean"},
              "monthly_report_day":      {"type": "integer", "description": "Kuukausiraportin paiva 1-28"}
            }
          }}}
        },
        "responses": {"200": {"description": "Paivitetyt asetukset"}}
      }
    },
    "/getSurveyQuestions": {
      "get": {
        "operationId": "getSurveyQuestions",
        "summary": "Hae asiakkaan lahettamat odottavat kyselyt",
        "responses": {"200": {"description": "Avoimet kyselyt"}}
      }
    },
    "/submitSurveyResponse": {
      "post": {
        "operationId": "submitSurveyResponse",
        "summary": "Vastaa kyselyyn",
        "requestBody": {
          "required": true,
          "content": {"application/json": {"schema": {
            "type": "object",
            "required": ["survey_id", "answer"],
            "properties": {
              "survey_id": {"type": "string"},
              "answer":    {"type": "string"},
              "comment":   {"type": "string"}
            }
          }}}
        },
        "responses": {"200": {"description": "Vastauksen kuittaus"}}
      }
    }
  }
}
SCHEMA
)

# Action Group
aws bedrock-agent create-agent-action-group \
  --agent-id "$AGENT_ID" \
  --agent-version "DRAFT" \
  --action-group-name "SupplierDataActions" \
  --action-group-executor "lambda={lambdaArn=$LAMBDA_ARN}" \
  --api-schema "$(echo "$SCHEMA" | python3 -c 'import json,sys; print(json.dumps({"payload": sys.stdin.read()}))')" \
  --region "$REGION" 2>/dev/null || \
aws bedrock-agent create-agent-action-group \
  --agent-id "$AGENT_ID" \
  --agent-version "DRAFT" \
  --action-group-name "SupplierDataActions" \
  --action-group-executor "lambda={lambdaArn=$LAMBDA_ARN}" \
  --api-schema "s3={s3BucketName=PLACEHOLDER,s3ObjectKey=openapi.json}" \
  --region "$REGION" || true

# Prepare & alias
echo "Valmistellaan agenttia..."
aws bedrock-agent prepare-agent --agent-id "$AGENT_ID" --region "$REGION" > /dev/null
sleep 15

ALIAS_ID=$(aws bedrock-agent create-agent-alias \
  --agent-id "$AGENT_ID" \
  --agent-alias-name "demo" \
  --region "$REGION" \
  --query "agentAlias.agentAliasId" --output text)

echo ""
echo "✅ Bedrock Agent valmis!"
echo ""
echo "Paivita Lambda ympäristömuuttujat:"
echo "  aws lambda update-function-configuration \\"
echo "    --function-name pientuottajat-webhook \\"
echo "    --environment 'Variables={BEDROCK_AGENT_ID=$AGENT_ID,BEDROCK_AGENT_ALIAS_ID=$ALIAS_ID,WHATSAPP_TOKEN=$WHATSAPP_TOKEN,WHATSAPP_PHONE_NUMBER_ID=$WHATSAPP_PHONE_NUMBER_ID,WHATSAPP_VERIFY_TOKEN=$WHATSAPP_VERIFY_TOKEN,DYNAMODB_TABLE_SUPPLIERS=pientuottajat-suppliers,DYNAMODB_TABLE_CONVERSATIONS=pientuottajat-conversations,USE_MOCK_DATA=True}'"
