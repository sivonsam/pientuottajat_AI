# Arkkitehtuuridokumentaatio

## Migraatiopolku & Kustannusarvio

```
🟢 DEMO          🟡 PILOTTI              🔵 TUOTANTO
Viikko 1-2  →   Kuukausi 1-3       →   Kuukausi 4+
~0-5 €/kk       ~50-300 €/kk           Asiakkaan rahoittama
Omat AWS        Ensimmäiset max        SaaS-monetisointi
henkilökohtaiset  3 alueosuuskauppaa   kaikki alueet
```

## Vaihe 1 — Demo (kustannustehokas, omat AWS-tunnukset)

**Kustannusoptimointipäätökset:**
- **Claude 3 Haiku** Sonnetin sijaan → ~10x halvempi per token
- **EventBridge Scheduler** Step Functionsin sijaan → ilmainen taso kattaa
- **Mock data** kaikkiin integraatioihin → nolla integraatiokustannuksia
- **DynamoDB On-Demand** → AWS Free Tier kattaa (25 GB, 25 WCU/RCU)
- **Lambda** → 1M kutsua/kk ilmaiseksi
- **API Gateway** → 1M kutsua/kk ilmaiseksi
- **S3** → 5 GB ilmaiseksi

**Ainoa todellinen kulu demossa:** Bedrock Haiku -tokenikustannus
- Haiku: $0.00025/1K input tokens, $0.00125/1K output tokens
- 1000 viestiä demossa ≈ ~$0.50-2.00 yhteensä

**Demo sisältää:**
- ✅ Telegram-botti (ilmainen API, nopea käynnistää)
- ✅ Lambda + DynamoDB + API Gateway
- ✅ Bedrock (Claude Haiku) AI-vastaukset
- ✅ Proaktiiviset hälytykset (mock-data pohjainen)
- ✅ Kuukausiraportti ajoitus (EventBridge)

**Demo EI sisällä (tulossa myöhemmin):**
- ❌ WhatsApp (vaatii Meta Business -hyväksynnän)
- ❌ Oikeat Kafka/Snowflake/SAP -integraatiot
- ❌ Web-portaali
- ❌ Laskutusintegraatio

## Vaihe 2 — Pilotti (monetisointi alkaa)

**Monetisointimalli:**
| Tier | Hinta | Sisältää |
|---|---|---|
| Free | 0 €/kk | 1 myymälä, peruskyselyt, Telegram |
| Pro | 49 €/kk | kaikki myymälät, raportit, hälytykset, kaikki kanavat |
| Enterprise | Neuvoteltava | API-integraatiot, white-label, Kaupan Liitto -näkymä |

**Kaupan Liitto -monetisointi:**
- Aggregoitu anonymisoitu data → benchmarking-raportti
- API-avain sidosryhmäraportointiin

## Vaihe 3 — Tuotanto (SOK Tech Radar -linjattu)

| Komponentti | Teknologia | SOK Radar |
|---|---|---|
| IaC | AWS CDK (TypeScript) | ADOPT |
| Backend | Python 3.12 | ADOPT |
| Frontend | Next.js | ADOPT |
| Tietokanta | DynamoDB + Aurora Serverless v2 | ADOPT/TRIAL |
| Viestijono | SQS + SNS | ADOPT |
| Streaming | Confluent Kafka | TRIAL |
| Kontainerointi | ECS Fargate | ADOPT |
| Observability | X-Ray + Splunk | ADOPT |
| Haku | ElasticSearch | ADOPT |
| AI | Bedrock Agents (Claude 3.5 Sonnet) | — |
| Raportointi | QuickSight | — |

## Raportointi & Kyselyt

**Toimittajille:**
- Kuukausiraportti → automaattinen viesti kanavaan + PDF S3:een
- Ad-hoc kyselyt Bedrock Agentin kautta

**Kaupan toimijalle (alueosuuskaupat):**
- QuickSight dashboard → toimittajien suorituskyky, reklamaatiotrendit
- Aggregoitu hyllysaatavuus alueosuuskaupoittain

**Kaupan Liitto:**
- Anonymisoitu aggregoitu näkymä → toimialabenchmarking
- API-integraatio heidän omiin järjestelmiinsä

**Toimittajakyselyt:**
- Survey Lambda → lähettää kyselyn Telegramiin/WhatsAppiin
- Vastaukset tallennetaan DynamoDB:hen → Aurora → QuickSight

## Turvallisuus & Tietosuoja

- Kaikki liikenne HTTPS/TLS
- Webhook token -vahvistus (Telegram secret token)
- AWS IAM least privilege, Secrets Manager API-avaimille
- Toimittajakohtainen data eristetty (tenant_id partition key)
- GDPR: ainoastaan toimitus- ja tuotedata, ei henkilötietoja
- Tuotannossa: AWS PrivateLink Kafka-yhteyksiin
