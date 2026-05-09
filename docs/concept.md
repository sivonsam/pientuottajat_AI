# Pientuottajat AI — Konsepti & Etenemissuunnitelma

> **Tila:** Konseptivaihe — ei vielä toiminnallista toteutusta  
> **Tavoite:** Esitellä asiakkaalle konsepti, arvolupaus ja konkreettiset seuraavat askeleet

---

## Miksi tämä?

Kaupan alueosuuskauppojen pientoimittajat ovat usein pieniä paikallisia yrityksiä, joilla on:
- Rajoitetut IT-resurssit ja -taidot
- Ei omaa toiminnanohjausjärjestelmää
- Tarve saada tieto toimituksista, reklamaatioista ja tilityksissä **sinne missä he jo ovat** — WhatsAppiin

Samaan aikaan kaupan henkilöstöllä ei ole helppoa keinoa:
- Tavoittaa toimittajia nopeasti (manuaaliset sähköpostit, puhelut)
- Kerätä tietoa toimittajakunnalta (kapasiteetti, laatu, hinnat)
- Muistuttaa eräpäivistä tai reagoida hyllypuutteisiin proaktiivisesti

---

## Ratkaisu yhdellä lauseella

> **Pientuottaja saa tutun WhatsApp-viestin kaupan AI-assistentilta — ja voi kysyä, raportoida ja reagoida ilman yhtään uutta järjestelmää.**

---

## Sidosryhmät

| Rooli | Tarve | Kanava |
|---|---|---|
| Pientoimittaja | Toimitukset, tilitykset, reklamaatiot, hyllysaatavuus | WhatsApp (ensisijainen) / Web-portaali |
| Kaupan ostaja / hankintapäällikkö | Kyselyt, muistutukset, tiedotteet toimittajille | n8n-pohjainen ops-työkalu |
| Myymäläpäällikkö | Hyllytilanne, toimitusstatus | n8n-raportti / WhatsApp |
| Alueosuuskaupan johto | Kokonaiskuva toimittajakunnasta | Dashboard (myöhempi vaihe) |

---

## Käyttäjäpolut

### Toimittajan polku (WhatsApp)
```
Toimittaja kirjoittaa:  "Mikä on toimitukseni DEL-002 tilanne?"
AI-agentti vastaa:      "Toimitus DEL-002 on vastaanotettu Prisma Tikkurilassa
                         7.5. — lasku lähetetty. Avoimia reklamaatioita ei ole."

Toimittaja kirjoittaa:  "Kirjaa reklamaatio, DEL-005 pakkaus vaurioitunut"
AI-agentti vastaa:      "Reklamaatio REC-089 kirjattu toimitukselle DEL-005.
                         Saat vahvistuksen 1-2 arkipäivässä."

Kauppa lähettää:        "Pystytkö toimittamaan 20% enemmän luomuhilloja
                         heinäkuussa? Vastaa: Kyllä / Ei / Osittain"
Toimittaja vastaa:      "Kyllä"
```

### Kaupan henkilöstön polku (n8n / ops-työkalu)
```
1. Kirjaudu n8n-pohjaiseen ops-portaaliin (selain)
2. Valitse: "Lähetä kysely" / "Muistutus" / "Tiedote"
3. Valitse kohderyhmä: kaikki / alue / yksittäinen toimittaja
4. Kirjoita viesti tai valitse malli
5. Lähetä → toimittajat saavat WhatsApp-viestin
6. Seuraa vastauksia ops-portaalissa
```

---

## Teknologiavalinnat — miksi nämä?

### Toimittajakanava: WhatsApp Business API
- **Miksi:** 95%+ suomalaisista pk-yrittäjistä käyttää WhatsAppia päivittäin
- Ei vaadi toimittajalta uutta sovellusta tai tunnuksia
- Meta Cloud API — rekisteröinti omalla SIM-kortilla (yrityksen numero)

### Web-portaali: Next.js
- Toimittaja voi myös kirjautua selaimella jos haluaa isomman näkymän
- SOK Tech Radar: ADOPT
- Rakennetaan myöhemmin — WhatsApp riittää demoon

### AI-agentti: Amazon Bedrock Agent (Claude)
- **Miksi agenttisuus eikä pelkkä chatbot:**  
  Agentti päättää itse mitä dataa hakee — toimittaja kirjoittaa vapaasti suomea,  
  agentti ymmärtää kontekstin ja kutsuu oikeita toimintoja (tool-use)
- Muistaa keskusteluhistorian session ajan
- Skaalautuu ilman koodimuutoksia kun uusia toimintoja lisätään

### Kassadata & toimitusdata: Manuaalinen JSON (demossa)
- Ei integraatioita demovaiheessa — data syötetään manuaalisesti DynamoDB:hen tai JSON-tiedostoon
- Vastaukset toimittajien kysymyksiin perustuvat tähän käsin ylläpidettävään dataan
- Pilottivaiheessa: oikea integraatio SAP BTP:hen tai WMS:ään

### Kaupan ops-työkalu: n8n (open source)
- **Miksi n8n eikä oma koodi:**
  - Visuaalinen workflow-builder — kaupan henkilöstö voi itse rakentaa työnkulkuja
  - Open source, self-hosted AWS:ssä (ECS tai EC2)
  - Natiiviintegraatio WhatsApp Business API:in
  - Valmiit nodet: ajastus, ehtologiikka, HTTP-kutsut, sähköposti
  - Toimittajaryhmät, muistutukset, kyselyt ilman koodausta
- **Vaihtoehdot:** n8n (suositeltu) / Retool / Appsmith / Tooljet

### Kafka-korvike: AWS SQS + DynamoDB
- Confluent Kafka on liian raskas demo+pilottivaiheeseen
- SQS riittää event-pohjaiseen viestinvälitykseen
- DynamoDB toimii yksinkertaisena tapahtumavarastona
- Kafka lisätään vasta tuotantovaiheessa jos tapahtumavolyymi vaatii

---

## Arkkitehtuuri — Demo + Pilotti (yhdistetty vaihe)

```
Pientoimittaja
  │
  ├── WhatsApp Business API
  └── Web Portal (Next.js) — myöhemmin
       │
       ▼
  AWS API Gateway
       │
       ▼
  Amazon Bedrock Agent (Claude Haiku → Sonnet pilotissa)
       │ tool-use
       ▼
  Action Groups Lambda (Python)
  ├── getDeliveries        ← manuaalidata DynamoDB
  ├── getSettlements       ← manuaalidata DynamoDB
  ├── getReclamations      ← manuaalidata DynamoDB
  ├── submitReclamation    ← kirjaa DynamoDB:hen
  ├── getShelfAvailability ← manuaalidata DynamoDB
  └── getSurveyQuestions   ← kyselyt DynamoDB:stä

Kaupan henkilöstö
  │
  └── n8n (open source, self-hosted AWS)
       ├── Workflow: Lähetä kysely → WhatsApp → kerää vastaukset
       ├── Workflow: Muistutus eräpäivästä → valituille toimittajille
       ├── Workflow: Hyllypuutehälytys → toimittajalle
       └── Workflow: Kuukausiraportti → kaikille automaattisesti
            │
            └── SQS → Event Processor Lambda → WhatsApp
```

---

## Seuraavat askeleet (ehdotus)

### Askel 1 — Sidosryhmähaastattelut (viikot 1-2)
- [ ] Valitse 3-5 pientoimittajaa pilottiin (eri IT-taitotasot)
- [ ] Valitse kaupan edustajat: ostaja + myymäläpäällikkö + IT
- [ ] Haastattele tarpeet — transcript päällä → AI tiivistää vaatimukset
- [ ] Validoi käyttäjäpolut tässä dokumentissa

### Askel 2 — Konseptin validointi (viikko 2-3)
- [ ] Esittele tämä konseptidokumentti + mockup asiakkaalle
- [ ] Sovi pilottimyymälät (1-3 alueosuuskauppaa)
- [ ] Sovi pilottitoimittajat (5-10 pientoimittajaa)
- [ ] Päätä kassadatan syöttötapa: manuaalinen Excel-lataus vai kevyt integraatio

### Askel 3 — Tekninen setup (viikot 3-4)
- [ ] AWS-tili + Bedrock Haiku käyttöönotto (eu-west-1)
- [ ] WhatsApp Business API rekisteröinti (yrityksen numero)
- [ ] n8n asennus AWS ECS:lle (tai lokaali testi)
- [ ] Bedrock Agent luonti + action groups
- [ ] Ensimmäinen toimittaja mukaan testaukseen

### Askel 4 — Pilotti (kuukaudet 1-3)
- [ ] Onboarding: 5-10 toimittajaa WhatsAppiin
- [ ] Manuaalidata: toimitukset, tilitykset, reklamaatiot syötetty
- [ ] Kaupan henkilöstö käyttää n8n:ää kyselyihin ja muistutuksiin
- [ ] Kerää palaute → iteroi

### Askel 5 — Tuotanto (kuukausi 4+)
- [ ] Oikeat integraatiot (SAP BTP, WMS)
- [ ] Web-portaali toimittajille (Next.js)
- [ ] Laajennus muihin alueosuuskauppoihin

---

## Avoimet kysymykset asiakkaalle

1. **Kassadata:** Miten toimitustiedot saadaan järjestelmästä? SAP BTP OData, CSV-vienti, vai manuaalinen syöttö?
2. **Toimittajat:** Onko toimittajarekisteri olemassa? Kuinka monta pilottitoimittajaa?
3. **Kaupan liiitto:** Onko Kaupan Liitto mukana pilotissa vai myöhemmin?
4. **GDPR:** Kenellä on vastuu toimittajadatan käsittelystä?
5. **WhatsApp:** Onko yrityksellä jo Meta Business Manager -tili?

---

*Päivitetty: 2026-05-09 | Tila: Konsepti — ei vielä teknistä toteutusta*
