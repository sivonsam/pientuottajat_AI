"""Generoi Pientuottajat AI arkkitehtuurikaavio — vaiheistus + kustannusarviot."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

fig = plt.figure(figsize=(26, 17))
ax  = fig.add_subplot(111)
ax.set_xlim(0, 26)
ax.set_ylim(0, 17)
ax.axis("off")
fig.patch.set_facecolor("#F5F7FA")

# ── Väripaletti ──────────────────────────────────────────────────────────────
C_D  = "#2E7D32"   # Demo  — vihreä
C_P  = "#E65100"   # Pilotti — oranssi
C_T  = "#1565C0"   # Tuotanto — sininen
C_AW = "#FF9900"   # AWS oranssi
C_WA = "#25D366"   # WhatsApp
C_AG = "#BF360C"   # Agent
C_CU = "#283593"   # Customer side
W    = "#FFFFFF"
BG_D = "#E8F5E9"
BG_P = "#FFF3E0"
BG_T = "#E3F2FD"
GRAY = "#546E7A"

def box(ax, x, y, w, h, top, bot="", bg=W, bc="#90A4AE", fs=8, tfs=None, bfs=6.5):
    tfs = tfs or fs
    r = FancyBboxPatch((x,y), w, h, boxstyle="round,pad=0.09",
        lw=1.4, edgecolor=bc, facecolor=bg, zorder=3)
    ax.add_patch(r)
    if bot:
        ax.text(x+w/2, y+h*0.63, top, ha="center", va="center",
                fontsize=tfs, fontweight="bold", zorder=4, color="#1A1A1A")
        ax.text(x+w/2, y+h*0.23, bot, ha="center", va="center",
                fontsize=bfs, zorder=4, color=GRAY)
    else:
        ax.text(x+w/2, y+h/2, top, ha="center", va="center",
                fontsize=tfs, fontweight="bold", zorder=4, color="#1A1A1A")

def cluster(ax, x, y, w, h, title, color, bg, alpha=0.4):
    r = FancyBboxPatch((x,y), w, h, boxstyle="round,pad=0.18",
        lw=2.4, edgecolor=color, facecolor=bg, zorder=1, alpha=alpha)
    ax.add_patch(r)
    ax.text(x+0.2, y+h-0.08, title, ha="left", va="top",
            fontsize=10.5, fontweight="bold", color=color, zorder=2)

def header_badge(ax, x, y, w, h, text, color):
    r = FancyBboxPatch((x,y), w, h, boxstyle="round,pad=0.12",
        lw=0, facecolor=color, zorder=5, alpha=0.92)
    ax.add_patch(r)
    ax.text(x+w/2, y+h/2, text, ha="center", va="center",
            fontsize=9.5, fontweight="bold", color="white", zorder=6)

def arr(ax, x1,y1,x2,y2, color=GRAY, lw=1.5, label="", rad=0.0, dashed=False):
    ls = "dashed" if dashed else "solid"
    ax.annotate("", xy=(x2,y2), xytext=(x1,y1),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                        linestyle=ls, connectionstyle=f"arc3,rad={rad}"),
        zorder=4)
    if label:
        mx,my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx+0.05, my+0.14, label, fontsize=6.2, color=color, ha="center",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=0.8))

def phase_arrow(ax, x1,y1,x2,y2, label, color):
    ax.annotate("", xy=(x2,y2), xytext=(x1,y1),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=3.0,
                        linestyle="dashed", connectionstyle="arc3,rad=0.0"), zorder=6)
    ax.text((x1+x2)/2, (y1+y2)/2+0.28, label, ha="center", fontsize=8.5,
            fontweight="bold", color=color, zorder=7,
            bbox=dict(boxstyle="round,pad=0.28", fc="white", ec=color, lw=1.5, alpha=0.95))

# ═══════════════════════════════════════════════════════════════════════════
# PÄÄOTSIKKO
# ═══════════════════════════════════════════════════════════════════════════
ax.text(13, 16.65, "Pientuottajat AI", ha="center", va="top",
        fontsize=20, fontweight="bold", color="#1A1A1A")
ax.text(13, 16.15, "Proaktiivinen agenttinen ratkaisu kaupan pientoimittajille  |  AWS  |  WhatsApp Business API  |  Amazon Bedrock",
        ha="center", va="top", fontsize=9.5, color=GRAY)
ax.axhline(15.85, color="#CBD5E0", lw=1, xmin=0.01, xmax=0.99)

# ═══════════════════════════════════════════════════════════════════════════
# VAIHE 1 — DEMO
# ═══════════════════════════════════════════════════════════════════════════
cluster(ax, 0.3, 1.0, 7.8, 14.5, "VAIHE 1 — DEMO", C_D, BG_D)
header_badge(ax, 0.5,14.6, 3.2,0.7, "Vaihe 1: DEMO", C_D)
header_badge(ax, 3.9,14.6, 4.0,0.7, "Kesto: 1-2 viikkoa", "#388E3C")

# Kustannuslaatikko
box(ax, 0.5,13.0, 7.2,1.4,
    "Kustannusarvio: ~0-5 EUR/kk",
    "API Gateway + Lambda + DynamoDB + EventBridge: AWS Free Tier (0 EUR)\n"
    "Bedrock Claude Haiku: ~$0.001/viesti — 1000 viestiä demossa ~$1-2\n"
    "Rahoitus: henkilökohtainen AWS-tili / luottokortti",
    bg="#C8E6C9", bc=C_D, fs=9, bfs=7)

# Toimittajan puoli
box(ax, 0.5,11.5, 3.4,1.2,"Pientoimittaja","Pk-yritys, eri IT-taidot",bg="#A5D6A7",bc=C_D,fs=9)
box(ax, 0.5,10.1, 3.4,1.1,"WhatsApp Business","Ei uutta sovellusta\nMeta Cloud API",bg=C_WA,bc="#1B9448",fs=9)

# AWS palvelut
box(ax, 4.3,11.5, 3.3,1.2,"API Gateway","1M req/kk ilmaiseksi\n/webhook/whatsapp",bg=W,bc=C_AW,fs=8)
box(ax, 4.3,10.1, 3.3,1.1,"Lambda Webhook","Python 3.12\nVahvistus + routing",bg=W,bc=C_AW,fs=8)
box(ax, 0.5, 8.6, 3.4,1.2,"Bedrock Claude Haiku","Suora InvokeModel\n~$0.001/viesti, 10x halv.",bg="#FFE0B2",bc=C_AG,fs=8)
box(ax, 4.3, 8.6, 3.3,1.2,"DynamoDB On-Demand","Profiilit, historia, kyselyt\n25 GB ilmaiseksi",bg=W,bc=C_AW,fs=8)
box(ax, 0.5, 7.1, 3.4,1.2,"EventBridge Scheduler","Kuukausiraportti\n1. pv klo 8 — ilmainen taso",bg=W,bc=C_AW,fs=8)
box(ax, 4.3, 7.1, 3.3,1.2,"Lambda Notifier","Proaktiiviset hälytykset\nReklamaatiot, hyllypuutteet",bg=W,bc=C_AW,fs=8)
box(ax, 0.5, 5.6, 3.4,1.2,"S3 Raportit","PDF-raportit\n5 GB ilmaiseksi",bg=W,bc=C_AW,fs=8)
box(ax, 4.3, 5.6, 3.3,1.2,"SQS Event Queue","Hälytysjono\n1M viestia/kk ilm.",bg=W,bc=C_AW,fs=8)
box(ax, 0.5, 4.0, 7.2,1.2,"Mock Data (JSON)","Toimitukset | Tilitykset | Reklamaatiot | Hyllysaatavuus — ei oikeita integraatioita tässä vaiheessa",bg="#FFF9C4",bc="#F57F17",fs=8)

# Demo nuolet
arr(ax, 2.2,11.5,2.2,11.2, C_D)
arr(ax, 3.9,10.6,4.3,11.9, C_D, label="webhook")
arr(ax, 5.95,11.5,5.95,11.2, C_AW)
arr(ax, 5.95,10.1,5.95,9.8, C_AW)
arr(ax, 4.3,9.15,3.9,9.15, C_AG, label="Bedrock")
arr(ax, 2.2,8.6,2.2,8.3, C_AG)
arr(ax, 1.5,7.1,1.5,6.8, C_AW)
arr(ax, 5.95,7.1,5.95,6.8, C_AW)
arr(ax, 4.3,6.5,3.9,7.65, C_AW)
arr(ax, 2.2,5.6,2.2,5.3, C_AW)
arr(ax, 2.2,7.1,2.2,6.8, C_AW)
arr(ax, 2.2,10.1,2.2,9.8, C_D)

# ═══════════════════════════════════════════════════════════════════════════
# VAIHE 2 — PILOTTI
# ═══════════════════════════════════════════════════════════════════════════
cluster(ax, 8.5, 1.0, 8.5, 14.5, "VAIHE 2 — PILOTTI", C_P, BG_P)
header_badge(ax, 8.7,14.6, 3.5,0.7, "Vaihe 2: PILOTTI", C_P)
header_badge(ax, 12.4,14.6, 4.4,0.7, "Kesto: kuukausi 1-3", "#F57F17")

box(ax, 8.7,13.0, 8.1,1.4,
    "Kustannusarvio: ~50-300 EUR/kk",
    "Asiakaslaskutus alkaa | Free: 0 EUR | Pro: 49 EUR/kk | Enterprise: neuvoteltava\n"
    "Bedrock Agent + Sonnet: ~$0.01-0.05/viesti | Kafka consumer | SAP BTP kutsut\n"
    "Rahoitus: pilottisopimus asiakkaan kanssa — kauppa maksaa",
    bg="#FFE0B2", bc=C_P, fs=9, bfs=7)

# Kanavat
box(ax, 8.7,11.5, 3.8,1.2,"WhatsApp + Web Portal","Next.js (SOK ADOPT)\nMulti-channel",bg=W,bc=C_P,fs=8)
box(ax, 12.8,11.5, 3.8,1.2,"API Gateway + WAF","Toimittajat + Kauppa\nAPI Key kaupan puolelle",bg=W,bc=C_AW,fs=8)

# Agent core
box(ax, 8.7,10.0, 7.9,1.2,"Bedrock Agent — Claude 3 Sonnet — Action Groups (9 toimintoa)",
    "getDeliveries | getSettlements | getReclamations | submitReclamation | respondToReclamation\n"
    "getShelfAvailability | updateAlertPreferences | getSurveyQuestions | submitSurveyResponse",
    bg="#FFE0B2",bc=C_AG,fs=8.5,bfs=6.5)

# Data
box(ax, 8.7, 8.5, 3.8,1.2,"DynamoDB Multi-tenant","tenant_id partition\nProfiilit, sessiot, surveys",bg=W,bc=C_AW,fs=8)
box(ax, 12.8, 8.5, 3.8,1.2,"SQS + EventBridge","Event fan-out\nAjastetut raportit",bg=W,bc=C_AW,fs=8)

# Integraatiot
box(ax, 8.7, 7.0, 3.8,1.2,"Confluent Kafka","Toimituseventit\n(SOK TRIAL)",bg=W,bc=C_P,fs=8)
box(ax, 12.8, 7.0, 3.8,1.2,"SAP BTP OData","Kassadata\nLaskutus + tilitykset",bg=W,bc="#1976D2",fs=8)

# Kaupan puoli
box(ax, 8.7, 5.5, 7.9,1.2,"Customer Ops API — Kaupan henkilöstö (API Key)",
    "POST /customer/broadcast — joukkotiedote toimittajille\n"
    "POST /customer/survey — kysely toimittajille WA:n kautta\n"
    "POST /customer/reminder — erapaivat, toimituspyynnot, hyllypuutteet",
    bg="#E3F2FD",bc=C_CU,fs=8.5,bfs=6.5)

# Monetisointi
box(ax, 8.7, 4.0, 3.8,1.2,"Monetisointi","Free / Pro 49 EUR/kk\nEnterprise neuvoteltava",bg="#FCE4EC",bc="#C62828",fs=8)
box(ax, 12.8, 4.0, 3.8,1.2,"QuickSight Raportit","Toimittajien suorituskyky\nKaupan Liitto -näkymä",bg=W,bc=C_AW,fs=8)

# Pilotti nuolet
arr(ax, 10.6,11.5,10.6,11.2, C_P)
arr(ax, 12.7,10.55,12.7,11.2, C_AW)
arr(ax, 10.6,10.0,10.6,9.7, C_P)
arr(ax, 10.6,8.5,10.6,8.2, C_AW)
arr(ax, 12.7,8.5,12.7,8.2, C_AW)
arr(ax, 10.6,7.0,10.6,6.7, C_P)
arr(ax, 12.7,7.0,12.7,6.7, "#1976D2")

# ═══════════════════════════════════════════════════════════════════════════
# VAIHE 3 — TUOTANTO
# ═══════════════════════════════════════════════════════════════════════════
cluster(ax, 17.3, 1.0, 8.4, 14.5, "VAIHE 3 — TUOTANTO", C_T, BG_T)
header_badge(ax, 17.5,14.6, 3.7,0.7, "Vaihe 3: TUOTANTO", C_T)
header_badge(ax, 21.4,14.6, 4.1,0.7, "Kuukausi 4+", "#1565C0")

box(ax, 17.5,13.0, 8.0,1.4,
    "Kustannusarvio: asiakas rahoittaa — SaaS-malli tai projektitoimitussopimus",
    "AWS Well-Architected | ECS Fargate long-running agentit | Aurora Serverless v2 analytiikka\n"
    "ElasticSearch haku | X-Ray + Splunk observability | CloudFront + WAF — kaikki SOK Tech Radar ADOPT\n"
    "Kaupan Liitto: aggregoitu anonymisoitu benchmark-näkymä",
    bg="#BBDEFB", bc=C_T, fs=9, bfs=7)

# Kanavat
box(ax, 17.5,11.5, 3.8,1.2,"WhatsApp + Web + API","3rd party integraatiot\nMulti-channel SaaS",bg=W,bc=C_T,fs=8)
box(ax, 21.6,11.5, 3.8,1.2,"CloudFront + WAF","CDN + tietoturva\nSOK ADOPT",bg=W,bc=C_AW,fs=8)

# Multi-agent
box(ax, 17.5,10.0, 7.9,1.2,"Multi-Agent Orchestration — Bedrock Agents (Claude 3.5 Sonnet)",
    "Erikoistunut agentit: toimitus-agentti | reklamaatio-agentti | raportointi-agentti\n"
    "ECS Fargate long-running + Lambda event-driven (SOK ADOPT)",
    bg="#FFE0B2",bc=C_AG,fs=8.5,bfs=6.5)

# Data
box(ax, 17.5, 8.5, 3.8,1.2,"DynamoDB Global Tables","Multi-region\nHigh availability",bg=W,bc=C_AW,fs=8)
box(ax, 21.6, 8.5, 3.8,1.2,"Aurora Serverless v2","Analytiikka + raportointi\nSOK ADOPT",bg=W,bc=C_AW,fs=8)

# Integraatiot
box(ax, 17.5, 7.0, 3.8,1.2,"Confluent Kafka\n+ Snowflake","Full real-time events\nDatasharing (SOK TRIAL)",bg=W,bc=C_T,fs=8)
box(ax, 21.6, 7.0, 3.8,1.2,"ElasticSearch","Haku ja suodatus\nSOK ADOPT",bg=W,bc=C_T,fs=8)

# Raportointi
box(ax, 17.5, 5.5, 7.9,1.2,"Raportointi & Kyselyt — QuickSight + Survey Lambda",
    "Toimittajien suorituskyky | Reklamaatiotrendit | Hyllysaatavuus-benchmarking\n"
    "Kaupan Liitto: anonymisoitu aggregoitu toimialanäkymä | Toimittajakyselyt automaattisesti",
    bg="#E8EAF6",bc=C_CU,fs=8.5,bfs=6.5)

# Observability
box(ax, 17.5, 4.0, 3.8,1.2,"X-Ray + Splunk","Full observability\nSOK ADOPT",bg=W,bc=C_T,fs=8)
box(ax, 21.6, 4.0, 3.8,1.2,"Stripe / Marketplace","SaaS-laskutus\nMulti-tenant billing",bg="#FCE4EC",bc="#C62828",fs=8)

# Tuotanto nuolet
arr(ax, 19.4,11.5,19.4,11.2, C_T)
arr(ax, 21.5,11.9,21.6,11.9, C_AW)
arr(ax, 19.4,10.0,19.4,9.7, C_T)
arr(ax, 19.4,8.5,19.4,8.2, C_T)
arr(ax, 23.5,8.5,23.5,8.2, C_AW)
arr(ax, 19.4,7.0,19.4,6.7, C_T)
arr(ax, 23.5,7.0,23.5,6.7, C_T)

# ═══════════════════════════════════════════════════════════════════════════
# MIGRAATIOPILIA
# ═══════════════════════════════════════════════════════════════════════════
phase_arrow(ax, 8.1, 8.0, 8.5, 8.0, "Viikko 1-2\nAsiakas hyväksyy\nPilottisopimus", C_P)
phase_arrow(ax, 17.0, 8.0, 17.3, 8.0, "Kuukausi 2-6\nOnboarding\nOikeat integraatiot", C_T)

# ═══════════════════════════════════════════════════════════════════════════
# ALARIVI — YHTEENVETO
# ═══════════════════════════════════════════════════════════════════════════
ax.axhline(2.85, color="#CBD5E0", lw=1, xmin=0.01, xmax=0.99)
ax.text(13, 2.72, "SOK Tech Radar -linjaus:  ADOPT: AWS CDK | Lambda | DynamoDB | SQS | ECS Fargate | Aurora | ElasticSearch | X-Ray | Splunk | Terraform | Python | TypeScript | Next.js | Docker    TRIAL: Confluent Kafka | Aurora Serverless",
        ha="center", va="top", fontsize=7.5, color=GRAY)
ax.text(13, 2.32, "Monetisointi:  Free (1 myymälä, peruskyselyt) — Pro 49 EUR/kk (kaikki myymälät, raportit, hälytykset) — Enterprise (API-integraatiot, white-label, Kaupan Liitto)",
        ha="center", va="top", fontsize=7.5, color="#1A1A1A", fontweight="bold")
ax.text(13, 1.95, "Tietosuoja: GDPR-yhteensopiva | Ei henkilötietoja | Toimittajakohtainen data eristetty | AWS Secrets Manager | HTTPS/TLS kaikkialla",
        ha="center", va="top", fontsize=7.5, color=GRAY)

# Legenda
items = [
    (C_D, "Vaihe 1 DEMO — AWS Free Tier, ~0-5 EUR/kk (oma luottokortti)"),
    (C_P, "Vaihe 2 PILOTTI — Asiakaslaskutus, ~50-300 EUR/kk"),
    (C_T, "Vaihe 3 TUOTANTO — SaaS full scale, SOK Tech Radar ADOPT"),
    (C_AG,"Amazon Bedrock Agent — AI-ydin, tool-use, muisti"),
    ("#C62828","Monetisointi — Free / Pro 49 EUR / Enterprise"),
]
for i,(c,l) in enumerate(items):
    ax.add_patch(FancyBboxPatch((0.4, 2.52-i*0.38), 0.42, 0.26,
        boxstyle="round,pad=0.04", facecolor=c, zorder=5))
    ax.text(0.95, 2.65-i*0.38, l, va="center", fontsize=7.5, color="#1A1A1A")
ax.text(0.4, 2.88, "Legenda:", fontsize=8.5, fontweight="bold", color="#1A1A1A")

out = "docs/diagrams/architecture.png"
plt.tight_layout(pad=0.3)
plt.savefig(out, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"OK: {out}")
