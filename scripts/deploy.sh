#!/bin/bash
# deploy.sh — Pientuottajat AI demo-ympäristön deployaus AWS:ään
set -e

echo "Pientuottajat AI — Demo Deploy"
echo "================================="

# 1. Tarkista AWS credentials
echo "Tarkistetaan AWS credentials..."
aws sts get-caller-identity --query "Account" --output text || {
  echo "AWS credentials puuttuu. Aja: aws configure"
  exit 1
}

# 2. Tarkista pakolliset ympäristömuuttujat
: "${WHATSAPP_TOKEN:?Aseta WHATSAPP_TOKEN ympäristömuuttuja}"
: "${WHATSAPP_PHONE_NUMBER_ID:?Aseta WHATSAPP_PHONE_NUMBER_ID ympäristömuuttuja}"
: "${WHATSAPP_VERIFY_TOKEN:?Aseta WHATSAPP_VERIFY_TOKEN ympäristömuuttuja}"

# 3. Asenna Python-riippuvuudet (ei enää tarvita python-telegram-bot)
echo "Asennetaan Python-riippuvuudet Lambda Layeriin..."
mkdir -p backend/layers/python/python
pip install -r backend/requirements.txt -t backend/layers/python/python/ --quiet

# 4. Asenna CDK
echo "Asennetaan CDK-riippuvuudet..."
cd infrastructure/cdk && npm install --silent && cd ../..

# 5. Bootstrap & deploy
echo "CDK Bootstrap..."
cd infrastructure/cdk && npx cdk bootstrap --quiet 2>/dev/null || true

echo "Deploytaan AWS:ään..."
WHATSAPP_TOKEN=$WHATSAPP_TOKEN \
WHATSAPP_PHONE_NUMBER_ID=$WHATSAPP_PHONE_NUMBER_ID \
WHATSAPP_VERIFY_TOKEN=$WHATSAPP_VERIFY_TOKEN \
npx cdk deploy --all --require-approval never --outputs-file ../../cdk-outputs.json
cd ../..

# 6. Outputit
echo ""
echo "Deploy valmis! Outputit:"
WEBHOOK_URL=$(python3 -c "
import json
data = json.load(open('cdk-outputs.json'))
for stack, outputs in data.items():
    for key, val in outputs.items():
        print(f'  {key}: {val}')
    if 'WhatsAppWebhookUrl' in outputs:
        print(outputs['WhatsAppWebhookUrl'], end='')
" 2>/dev/null | tail -1)

echo ""
echo "=== SEURAAVA ASKEL: Aseta WhatsApp webhook Meta-konsolissa ==="
echo "1. Mene: https://developers.facebook.com/apps/"
echo "2. WhatsApp -> Configuration -> Webhook"
echo "3. Callback URL: $(python3 -c "import json; d=json.load(open('cdk-outputs.json')); [print(v) for s,o in d.items() for k,v in o.items() if 'Webhook' in k]" 2>/dev/null)"
echo "4. Verify Token: $WHATSAPP_VERIFY_TOKEN"
echo "5. Tilaa: messages"
