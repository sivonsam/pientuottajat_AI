#!/bin/bash
# setup_bedrock_agent.sh — Luo Amazon Bedrock Agent AWS Consolessa tai CLI:llä
# AJA VASTA kun CDK-deploy on tehty ja ActionGroupsLambdaArn on tiedossa

set -e

LAMBDA_ARN="${1:-PLACEHOLDER_ARN}"
REGION="${AWS_DEFAULT_REGION:-eu-west-1}"
AGENT_NAME="pientuottajat-agent"

echo "🤖 Luodaan Amazon Bedrock Agent..."

# 1. Luo IAM role Bedrock Agentille
TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "bedrock.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}'

ROLE_ARN=$(aws iam create-role \
  --role-name "AmazonBedrockExecutionRoleForAgents_pientuottajat" \
  --assume-role-policy-document "$TRUST_POLICY" \
  --query "Role.Arn" --output text 2>/dev/null || \
  aws iam get-role --role-name "AmazonBedrockExecutionRoleForAgents_pientuottajat" --query "Role.Arn" --output text)

aws iam attach-role-policy \
  --role-name "AmazonBedrockExecutionRoleForAgents_pientuottajat" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonBedrockFullAccess" 2>/dev/null || true

echo "  IAM Role: $ROLE_ARN"

# 2. Luo Bedrock Agent
AGENT_ID=$(aws bedrock-agent create-agent \
  --agent-name "$AGENT_NAME" \
  --agent-resource-role-arn "$ROLE_ARN" \
  --foundation-model "anthropic.claude-3-5-sonnet-20241022-v2:0" \
  --instruction "$(cat <<'INSTRUCTION'
Olet pientuottaja-assistentti joka auttaa suomalaisia pieniä elintarviketoimittajia seuraamaan toimituksiaan, laskutustaan, reklamaatioitaan ja hyllysaatavuuttaan alueosuuskaupoissa.

Olet ystävällinen, selkeä ja proaktiivinen. Käytä aina suomea. Vastaa lyhyesti ja selkeästi — käyttäjillä voi olla rajoitettu digitaalinen osaaminen.

Voit tehdä seuraavia toimintoja:
- Hakea viimeisimmät toimitukset
- Hakea avoimet reklamaatiot  
- Hakea myyntidatan alueosuuskaupoittain
- Tarkistaa hyllysaatavuuden
- Päivittää käyttäjän hälytyspreferenssit

Kun käyttäjä pyytää sinua ilmoittamaan automaattisesti jostakin (esim. "hälytä minulle aina reklamaatioista"), päivitä hänen hälytyspreferenssinsä action groupin kautta.
INSTRUCTION
)" \
  --region "$REGION" \
  --query "agent.agentId" --output text)

echo "  Agent ID: $AGENT_ID"

# 3. Luo Action Group
aws bedrock-agent create-agent-action-group \
  --agent-id "$AGENT_ID" \
  --agent-version "DRAFT" \
  --action-group-name "SupplierDataActions" \
  --action-group-executor "lambda={lambdaArn=$LAMBDA_ARN}" \
  --api-schema "$(cat <<'SCHEMA'
{
  "openapi": "3.0.0",
  "info": {"title": "Supplier Data API", "version": "1.0"},
  "paths": {
    "/getDeliveries": {
      "get": {"operationId": "getDeliveries", "summary": "Hae toimittajan toimitukset", "responses": {"200": {"description": "Toimitusdata"}}}
    },
    "/getReclamations": {
      "get": {"operationId": "getReclamations", "summary": "Hae avoimet reklamaatiot", "responses": {"200": {"description": "Reklamaatiodata"}}}
    },
    "/getSalesByStore": {
      "get": {
        "operationId": "getSalesByStore",
        "summary": "Hae myynti myymäläkohtaisesti",
        "parameters": [{"name": "month", "in": "query", "schema": {"type": "string"}, "description": "Kuukausi muodossa YYYY-MM"}],
        "responses": {"200": {"description": "Myyntidata"}}
      }
    },
    "/getShelfAvailability": {
      "get": {"operationId": "getShelfAvailability", "summary": "Hae hyllysaatavuustilanne", "responses": {"200": {"description": "Hyllysaatavuusdata"}}}
    }
  }
}
SCHEMA
)" \
  --region "$REGION"

# 4. Valmistele ja luo alias
aws bedrock-agent prepare-agent --agent-id "$AGENT_ID" --region "$REGION"

sleep 10

ALIAS_ID=$(aws bedrock-agent create-agent-alias \
  --agent-id "$AGENT_ID" \
  --agent-alias-name "demo" \
  --region "$REGION" \
  --query "agentAlias.agentAliasId" --output text)

echo ""
echo "✅ Bedrock Agent luotu!"
echo "   BEDROCK_AGENT_ID=$AGENT_ID"
echo "   BEDROCK_AGENT_ALIAS_ID=$ALIAS_ID"
echo ""
echo "Lisää nämä Lambda-ympäristömuuttujiin:"
echo "  aws lambda update-function-configuration \\"
echo "    --function-name pientuottajat-webhook \\"
echo "    --environment 'Variables={BEDROCK_AGENT_ID=$AGENT_ID,BEDROCK_AGENT_ALIAS_ID=$ALIAS_ID,USE_MOCK_DATA=True,DYNAMODB_TABLE_SUPPLIERS=pientuottajat-suppliers}'"
