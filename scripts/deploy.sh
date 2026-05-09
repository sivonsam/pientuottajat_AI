#!/bin/bash
# deploy.sh — Pientuottajat AI demo-ympäristön deployaus AWS:ään
set -e

echo "🚀 Pientuottajat AI — Demo Deploy"
echo "=================================="

# 1. Tarkista AWS credentials
echo "✅ Tarkistetaan AWS credentials..."
aws sts get-caller-identity --query "Account" --output text || {
  echo "❌ AWS credentials puuttuu. Aja: aws configure"
  exit 1
}

# 2. Asenna Python-riippuvuudet Lambda Layeria varten
echo "📦 Asennetaan Python-riippuvuudet Lambda Layeriin..."
mkdir -p backend/layers/python/python
pip install -r backend/requirements.txt -t backend/layers/python/python/ --quiet

# 3. Asenna CDK-riippuvuudet
echo "📦 Asennetaan CDK-riippuvuudet..."
cd infrastructure/cdk && npm install --silent && cd ../..

# 4. Bootstrap CDK (jos ei vielä tehty)
echo "🔧 CDK Bootstrap..."
cd infrastructure/cdk && npx cdk bootstrap --quiet 2>/dev/null || true && cd ../..

# 5. Deploy
echo "☁️  Deploytaan AWS:ään..."
cd infrastructure/cdk && npx cdk deploy --all --require-approval never --outputs-file ../../cdk-outputs.json && cd ../..

# 6. Lue outputs
echo ""
echo "✅ Deploy valmis! Outputit:"
cat cdk-outputs.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for stack, outputs in data.items():
    for key, val in outputs.items():
        print(f'  {key}: {val}')
"

# 7. Aseta Telegram webhook (jos TELEGRAM_BOT_TOKEN on asetettu)
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
  WEBHOOK_URL=$(cat cdk-outputs.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for stack, outputs in data.items():
    if 'TelegramWebhookUrl' in outputs:
        print(outputs['TelegramWebhookUrl'])
")
  echo ""
  echo "📡 Asetetaan Telegram webhook: $WEBHOOK_URL"
  curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=${WEBHOOK_URL}" | python3 -c "import json,sys; r=json.load(sys.stdin); print('  ✅ Webhook asetettu!' if r.get('ok') else f'  ❌ {r}')"
else
  echo ""
  echo "⚠️  Aseta TELEGRAM_BOT_TOKEN ympäristömuuttujaan ja aja webhook manuaalisesti:"
  echo "   curl https://api.telegram.org/bot\$TOKEN/setWebhook?url=WEBHOOK_URL"
fi

echo ""
echo "🎉 Pientuottajat AI on käynnissä!"
echo "   Avaa Telegram ja etsi bottisi käyttäjätunnuksella."
