# Pientuottajat AI — Proaktiivinen agenttinen ratkaisu

Ratkaisu kaupan alueosuuskauppojen pientoimittajille: helppokäyttöinen, proaktiivinen AI-agentti joka kommunikoi toimittajan haluamalla kanavalla (WhatsApp, Telegram, web) ja raportoi automaattisesti toimituksista, laskutuksesta, laadusta ja reklamaatioista.

## Arkkitehtuuri (hypoteesi — tarkentuu haastatteluiden myötä)

```
Pientoimittaja
    │
    ├── WhatsApp Business API
    ├── Telegram Bot
    └── Web Portal (Next.js)
         │
         ▼
    AWS API Gateway
         │
         ▼
    AWS Lambda (Webhook Handler)
         │
         ▼
    Amazon Bedrock Agent ←→ Action Groups (Lambda)
         │                        │
         │              ┌─────────┼──────────┐
         │              ▼         ▼          ▼
         │         DynamoDB   Confluent   SAP BTP
         │         (state)     Kafka     (kassadata)
         │                   (eventit)
         ▼
    AWS SQS → Lambda (Notifier) → WhatsApp/Telegram proaktiivinen viesti
```

## Projektin vaiheet

1. **Konseptointi** — Sidosryhmähaastattelut, tarpeiden kartoitus
2. **Kokeilu / Demo** — Toimiva E2E-demo (tämä repo)
3. **Toteutus** — Modulaarinen tuotantovalmis ratkaisu
4. **Operointi** — Jatkuva kehitys ja ylläpito

## Teknologiavalinnat (SOK Tech Radar -linjaus)

| Komponentti | Teknologia | SOK Radar |
|---|---|---|
| IaC | AWS CDK (TypeScript) | ADOPT |
| Backend lambdat | Python 3.12 | ADOPT |
| Frontend | Next.js | ADOPT |
| Tietokanta | AWS DynamoDB | ADOPT |
| Viestijono | AWS SQS | ADOPT |
| Orkestrointi | AWS Step Functions | ADOPT |
| AI-agentti | Amazon Bedrock Agents (Claude) | — |
| Streaming | Confluent Kafka | TRIAL |
| Observability | AWS X-Ray + Splunk | ADOPT |

## Hakemistorakenne

```
├── docs/               Arkkitehtuuridokumentaatio ja diagrammit
├── infrastructure/cdk  AWS CDK stack
├── backend/
│   ├── agents/         Bedrock Agent määrittelyt & action groups
│   └── lambdas/        Lambda funktiot
├── channels/
│   ├── whatsapp/       WhatsApp Business API integraatio
│   └── telegram/       Telegram Bot integraatio
├── frontend/portal     Next.js toimittajaportaali
└── scripts/            Deploy- ja hallintaskriptit
```

## Nopea aloitus (demo-ympäristö)

```bash
# 1. Asenna riippuvuudet
pip install -r backend/requirements.txt
cd infrastructure/cdk && npm install

# 2. Konfiguroi ympäristömuuttujat
cp .env.example .env
# Täytä AWS credentials, WhatsApp/Telegram API-avaimet

# 3. Deploy AWS:ään
cd infrastructure/cdk && npx cdk deploy --all

# 4. Käynnistä Telegram-botti paikallisesti testaamista varten
python channels/telegram/bot.py
```

## Arkkitehtuuridiagrammi

Katso `docs/diagrams/architecture.mmd` (Mermaid-formaatti).
