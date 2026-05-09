"""Generoi Pientuottajat AI arkkitehtuurikaavio — agenttinen versio."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(24, 15))
ax.set_xlim(0, 24)
ax.set_ylim(0, 15)
ax.axis("off")
fig.patch.set_facecolor("#F0F4F8")

C_SUPPLIER = "#1B5E20"
C_CUSTOMER = "#0D47A1"
C_AGENT    = "#E65100"
C_AWS      = "#FF9900"
C_WA       = "#25D366"
C_SAP      = "#1976D2"
C_DATA     = "#4A148C"
C_EVENT    = "#880E4F"
C_BG_S     = "#E8F5E9"
C_BG_C     = "#E3F2FD"
C_BG_A     = "#FFF3E0"
C_BG_D     = "#F3E5F5"
WHITE      = "#FFFFFF"

def box(ax, x, y, w, h, label, sub="", bg=WHITE, border="#90A4AE", fs=8.5, bold=True):
    rect = FancyBboxPatch((x,y), w, h, boxstyle="round,pad=0.1",
        linewidth=1.5, edgecolor=border, facecolor=bg, zorder=3)
    ax.add_patch(rect)
    fw = "bold" if bold else "normal"
    if sub:
        ax.text(x+w/2, y+h*0.63, label, ha="center", va="center", fontsize=fs, fontweight=fw, zorder=4, color="#1A1A1A")
        ax.text(x+w/2, y+h*0.25, sub,   ha="center", va="center", fontsize=6.8, zorder=4, color="#546E7A")
    else:
        ax.text(x+w/2, y+h/2,    label, ha="center", va="center", fontsize=fs, fontweight=fw, zorder=4, color="#1A1A1A")

def cluster(ax, x, y, w, h, title, color, bg, alpha=0.35):
    rect = FancyBboxPatch((x,y), w, h, boxstyle="round,pad=0.2",
        linewidth=2.2, edgecolor=color, facecolor=bg, zorder=1, alpha=alpha)
    ax.add_patch(rect)
    ax.text(x+0.18, y+h-0.05, title, ha="left", va="top",
            fontsize=9.5, fontweight="bold", color=color, zorder=2)

def arr(ax, x1, y1, x2, y2, color="#546E7A", lw=1.6, label="", rad=0.0, style="->"):
    ax.annotate("", xy=(x2,y2), xytext=(x1,y1),
        arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                        connectionstyle=f"arc3,rad={rad}"))
    if label:
        ax.text((x1+x2)/2+0.05, (y1+y2)/2+0.15, label,
                fontsize=6.5, color=color, ha="center",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, pad=1))

def darr(ax, x1,y1,x2,y2, color, label=""):
    ax.annotate("", xy=(x2,y2), xytext=(x1,y1),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=2.2,
                        linestyle="dashed", connectionstyle="arc3,rad=0.0"))
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2+0.25, label, ha="center",
                fontsize=8, fontweight="bold", color=color,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=color, alpha=0.92))

# ═══════════════════════════════════════════════════════════════════════════
# OTSIKKO
# ═══════════════════════════════════════════════════════════════════════════
ax.text(12, 14.6, "Pientuottajat AI — Agenttinen arkkitehtuuri", ha="center", va="top",
        fontsize=17, fontweight="bold", color="#1A1A1A")
ax.text(12, 14.15,"Kaksisuuntainen: toimittaja chattaa agentin kanssa  |  kauppa laahettaa kyselyitä & muistutuksia proaktiivisesti",
        ha="center", va="top", fontsize=9, color="#546E7A")

# ═══════════════════════════════════════════════════════════════════════════
# VASEN: TOIMITTAJAN PUOLI
# ═══════════════════════════════════════════════════════════════════════════
cluster(ax, 0.2, 3.2, 5.0, 10.5, "TOIMITTAJAN PUOLI (pientoimittaja)", C_SUPPLIER, C_BG_S)

box(ax, 0.5,12.0,4.4,1.1,"Pientoimittaja","Eri IT-tasot, pk-yritys",bg="#C8E6C9",border=C_SUPPLIER,fs=10)
box(ax, 0.5,10.5,4.4,1.1,"WhatsApp Business","Tuttu kanava — ei uutta appia",bg=C_WA,border="#1B9448",fs=9.5)
box(ax, 0.5, 8.8,4.4,0.95,"Kysy toimituksistasi","\"Mika on DEL-002 tilanne?\"",bg=WHITE,border=C_SUPPLIER,fs=8.5,bold=False)
box(ax, 0.5, 7.7,4.4,0.95,"Kirjaa reklamaatio","\"Kirjaa reklamaatio DEL-002\"",bg=WHITE,border=C_SUPPLIER,fs=8.5,bold=False)
box(ax, 0.5, 6.6,4.4,0.95,"Kysy tilitystasi","\"Paljonko tilitysta on tulossa?\"",bg=WHITE,border=C_SUPPLIER,fs=8.5,bold=False)
box(ax, 0.5, 5.5,4.4,0.95,"Aseta halytykset","\"Halyta aina reklamaatioista\"",bg=WHITE,border=C_SUPPLIER,fs=8.5,bold=False)
box(ax, 0.5, 4.4,4.4,0.95,"Vastaa kyselyihin","\"Kylla, voin toimittaa enemman\"",bg=WHITE,border=C_SUPPLIER,fs=8.5,bold=False)
box(ax, 0.5, 3.4,4.4,0.75,"Vastaanota proaktiiviset ilmoitukset","Reklamaatiot, hyllypuutteet, erapaivat",bg="#F1F8E9",border=C_SUPPLIER,fs=7.5)

arr(ax, 2.7,12.0,2.7,11.6, C_SUPPLIER)
arr(ax, 2.7,10.5,2.7,9.75, C_SUPPLIER)
arr(ax, 4.94,10.0,5.5,10.0, C_SUPPLIER, label="HTTPS Webhook")

# ═══════════════════════════════════════════════════════════════════════════
# KESKIOSA: BEDROCK AGENT (AI-ydin)
# ═══════════════════════════════════════════════════════════════════════════
cluster(ax, 5.4, 2.0, 8.0, 12.0, "AWS — AGENTTINEN AI-YDIN", C_AGENT, C_BG_A)

box(ax, 5.7,12.4, 2.0,1.0,"API Gateway","GET+POST\n/webhook/whatsapp",bg=WHITE,border=C_AWS)
box(ax, 8.1,12.4, 2.0,1.0,"Lambda\nWebhook","Python 3.12",bg=WHITE,border=C_AWS)

# Bedrock Agent — paikka
box(ax, 5.7,10.2, 4.4,1.8,"Amazon Bedrock Agent\n(Claude 3 Haiku)",
    "Ymmaartaa kontekstin, paattaa itse mitka\ntoiminnot kutsutaan (tool-use), pitaa muistin",
    bg="#FFE0B2",border=C_AGENT,fs=9.5)

# Action Groups
box(ax, 5.7,8.4, 2.0,1.5,"Action Groups",
    "getDeliveries\ngetSettlements\ngetReclamations\nsubmitReclamation\nrespondToReclamation\ngetShelfAvailability\nupdateAlertPreferences\ngetSurveyQuestions\nsubmitSurveyResponse",
    bg=WHITE,border=C_AGENT,fs=7.0)
box(ax, 8.1,8.4, 2.0,1.5,"Lambda\nAction Handler","Python\nMock → oikeat\nintegraatiot",bg=WHITE,border=C_AWS,fs=8)

box(ax, 5.7,6.5, 2.0,1.5,"DynamoDB","Toimittajaprofiilit\nKeskusteluhistoria (TTL)\nHalytysasetukset\n(25 GB Free Tier)",bg=WHITE,border=C_DATA,fs=7.5)
box(ax, 8.1,6.5, 2.0,1.5,"SQS\nEvent Queue","Asynk. eventit\npientuottajat-events\n(Free Tier)",bg=WHITE,border=C_AWS,fs=7.5)

box(ax, 5.7,4.5, 2.0,1.6,"Event Processor\nLambda","Reklamaatiot\nHyllypuutteet\nErapaivat\nMitkä toimittajat?",bg=WHITE,border=C_EVENT,fs=7.5)
box(ax, 8.1,4.5, 2.0,1.6,"EventBridge\nScheduler","Kuukausiraportti\n1. pv klo 8:00\nKaikille toimittajille\n(ilmainen taso)",bg=WHITE,border=C_AWS,fs=7.5)

box(ax, 5.7,2.5, 2.0,1.6,"Surveys Table\nDynamoDB","Kaupan kyselyt\nVastaukset\nYhteenvedot",bg=WHITE,border=C_DATA,fs=7.5)
box(ax, 8.1,2.5, 2.0,1.6,"S3\nRaportit","PDF-raportit\nKuukausiyhteevedot\nKaupan Liitto",bg=WHITE,border=C_AWS,fs=7.5)

# Nuolet agent-osassa
arr(ax, 7.7,12.9, 8.1,12.9, C_AWS)
arr(ax, 9.1,12.4, 9.1,11.6, label="invoke_agent\ntai InvokeModel",color=C_AGENT)
arr(ax, 5.7+2.2,10.2, 5.7+2.2,9.9, C_AGENT, label="tool-use")
arr(ax, 7.7,9.15, 8.1,9.15, C_AGENT)
arr(ax, 6.7,8.4, 6.7,8.0, C_DATA)
arr(ax, 9.1,8.4, 9.1,8.0, C_AWS)
arr(ax, 9.1,6.5, 9.1,6.1, C_EVENT)
arr(ax, 8.1,5.25, 7.7,5.25, C_EVENT)
arr(ax, 8.1+1.0,4.5, 8.1+1.0,4.1, C_AWS)

# ═══════════════════════════════════════════════════════════════════════════
# OIKEA: KAUPAN PUOLI
# ═══════════════════════════════════════════════════════════════════════════
cluster(ax, 13.6, 3.2, 5.0, 10.5, "KAUPAN PUOLI (alueosuuskauppa)", C_CUSTOMER, C_BG_C)

box(ax, 13.9,12.0,4.4,1.1,"Kaupan henkilosto","Ostaja, hankintapaallikkoo,\nalueosuuskaupan johto",bg="#BBDEFB",border=C_CUSTOMER,fs=9.5)
box(ax, 13.9,10.5,4.4,1.1,"Customer Ops API","/customer/* + API Key\nAWS API Gateway",bg=WHITE,border=C_AWS,fs=8.5)
box(ax, 13.9, 8.8,4.4,0.95,"Laata kysely","\"Pystytkö toimittamaan\nenemmän heinäkuussa?\"",bg=WHITE,border=C_CUSTOMER,fs=8,bold=False)
box(ax, 13.9, 7.7,4.4,0.95,"Laheta muistutus","Erapaivat, toimituspyynnot,\nhyllypuutteet",bg=WHITE,border=C_CUSTOMER,fs=8,bold=False)
box(ax, 13.9, 6.6,4.4,0.95,"Broadcast kaikille","Tiedotteet kaikille\ntai valituille toimittajille",bg=WHITE,border=C_CUSTOMER,fs=8,bold=False)
box(ax, 13.9, 5.5,4.4,0.95,"Naa vastaukset","Kyselyiden tulokset,\nyhteenvedot",bg=WHITE,border=C_CUSTOMER,fs=8,bold=False)
box(ax, 13.9, 4.4,4.4,0.95,"QuickSight raportit","Toimittajien suorituskyky,\nreklamaatiotrendit (pilotti+)",bg="#E8EAF6",border=C_CUSTOMER,fs=7.5,bold=False)
box(ax, 13.9, 3.4,4.4,0.75,"Kaupan Liitto","Aggregoitu anonymisoitu\nnakymä (tuotanto)",bg="#F1F8E9",border=C_CUSTOMER,fs=7.5)

arr(ax, 16.1,12.0,16.1,11.6, C_CUSTOMER)
arr(ax, 13.9,10.95,13.4,10.05, C_CUSTOMER, label="POST /customer/*\n+ API Key")

# ═══════════════════════════════════════════════════════════════════════════
# INTEGRAATIOT (alempi osa)
# ═══════════════════════════════════════════════════════════════════════════
cluster(ax, 0.2, 0.1, 18.4, 2.1, "INTEGRAATIOT  (mock demossa → oikeat pilottivaiheessa)", "#37474F", "#ECEFF1")

box(ax, 0.5, 0.3, 3.0, 1.5, "Confluent Kafka","Toimituseventit\nReklamaatioeventit\n(SOK TRIAL)",bg=WHITE,border="#37474F",fs=7.5)
box(ax, 4.0, 0.3, 3.0, 1.5, "Snowflake","Myyntidata\nHyllysaatavuus\nDatasharing",bg=WHITE,border="#37474F",fs=7.5)
box(ax, 7.5, 0.3, 3.0, 1.5, "SAP BTP OData","Kassadata\nLaskutus\nTilitykset",bg=WHITE,border=C_SAP,fs=7.5)
box(ax, 11.0,0.3, 3.0, 1.5, "Vanhemmat\ntoimiala-\njarjestelmat","WMS, varasto\nREST / batch",bg=WHITE,border="#37474F",fs=7.5)
box(ax, 14.5,0.3, 4.0, 1.5, "Proaktiiviset tapahtumat\n(EventBridge Rules)","Paivittainen hyllytarkistus\nViikoittainen erapaivamuistutus\nMaaritettavat triggerit",bg="#FFF9C4",border="#F57F17",fs=7.5)

# Integraatio -> Agent nuolet
arr(ax, 2.0, 1.8, 6.7,2.5, "#37474F", lw=1.2, label="Kafka consumer")
arr(ax, 5.5, 1.8, 6.7,2.5, "#37474F", lw=1.2, label="Snowflake query")
arr(ax, 9.0, 1.8, 6.7,2.5, C_SAP,    lw=1.2, label="OData REST")

# ═══════════════════════════════════════════════════════════════════════════
# KAKSISUUNTAISET DATAVIRRAT
# ═══════════════════════════════════════════════════════════════════════════
# Toimittaja WA → API GW
arr(ax, 4.94,10.0, 5.7,12.9, C_SUPPLIER, lw=2, label="viesti")
# Agent → toimittaja (proaktiivinen)
arr(ax, 5.7,5.0, 4.94,10.35, C_EVENT, lw=2, rad=0.2, label="proaktiivinen\nhalytys")
# Customer ops → SQS
arr(ax, 13.4,10.0, 10.1,7.4, C_CUSTOMER, lw=2, label="event")
# Customer ops → Surveys
arr(ax, 13.4,9.5, 10.1,3.5, C_CUSTOMER, lw=1.5, rad=0.15, label="survey")

# ═══════════════════════════════════════════════════════════════════════════
# LEGENDA
# ═══════════════════════════════════════════════════════════════════════════
legend = [
    (C_SUPPLIER, "Toimittajan puoli — WhatsApp-keskustelu agentin kanssa"),
    (C_AGENT,    "AI-agenttikerros — Bedrock Agent (Claude), tool-use, muisti"),
    (C_CUSTOMER, "Kaupan puoli — kyselyt, muistutukset, broadcastit (API Key)"),
    (C_EVENT,    "Proaktiivinen notifikaatio — SQS-eventit + EventBridge scheduler"),
    ("#37474F",  "Integraatiot — Kafka, Snowflake, SAP BTP (mock → oikeat pilotissa)"),
]
for i, (c, lbl) in enumerate(legend):
    ax.add_patch(FancyBboxPatch((19.1, 11.5-i*0.6), 0.45, 0.35,
        boxstyle="round,pad=0.05", facecolor=c, zorder=5))
    ax.text(19.65, 11.67-i*0.6, lbl, va="center", fontsize=7.5, color="#212121")

ax.text(19.1, 12.0, "Legenda:", fontsize=9, fontweight="bold", color="#212121")

# Kustannuslaatikko
box(ax, 19.1, 7.5, 4.7, 3.8,
    "DEMO-kustannus\n(oma luottokortti)\n\n"
    "API Gateway:  ilmainen\n"
    "Lambda:       ilmainen\n"
    "DynamoDB:     ilmainen\n"
    "EventBridge:  ilmainen\n"
    "S3:           ilmainen\n"
    "Bedrock Haiku: ~$1-2/demo\n\n"
    "YHTEENSA: ~0-5 EUR/kk",
    bg="#E8F5E9", border=C_SUPPLIER, fs=8)

out = "docs/diagrams/architecture.png"
plt.tight_layout(pad=0.3)
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"Kaavio tallennettu: {out}")
