"""Generoi Pientuottajat AI arkkitehtuurikaavio PNG-muodossa."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(22, 14))
ax.set_xlim(0, 22)
ax.set_ylim(0, 14)
ax.axis("off")
fig.patch.set_facecolor("#F8F9FA")

# ── Värit ───────────────────────────────────────────────────────────────────
C_DEMO   = "#2E7D32"   # tumma vihreä
C_PILOTTI= "#E65100"   # oranssi
C_TUOT   = "#1565C0"   # tumma sininen
C_WA     = "#25D366"   # WhatsApp vihreä
C_AWS    = "#FF9900"   # AWS oranssi
C_ARROW  = "#546E7A"
C_BG_D   = "#E8F5E9"
C_BG_P   = "#FFF3E0"
C_BG_T   = "#E3F2FD"
C_BOX    = "#FFFFFF"

def box(ax, x, y, w, h, label, sublabel="", bg=C_BOX, border="#90A4AE", fontsize=8.5):
    rect = FancyBboxPatch((x, y), w, h,
        boxstyle="round,pad=0.08", linewidth=1.2,
        edgecolor=border, facecolor=bg, zorder=3)
    ax.add_patch(rect)
    if sublabel:
        ax.text(x+w/2, y+h*0.62, label, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", zorder=4, color="#212121")
        ax.text(x+w/2, y+h*0.25, sublabel, ha="center", va="center",
                fontsize=7, zorder=4, color="#546E7A")
    else:
        ax.text(x+w/2, y+h/2, label, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", zorder=4, color="#212121")

def cluster(ax, x, y, w, h, title, color, bg):
    rect = FancyBboxPatch((x, y), w, h,
        boxstyle="round,pad=0.15", linewidth=2,
        edgecolor=color, facecolor=bg, zorder=1, alpha=0.5)
    ax.add_patch(rect)
    ax.text(x+0.15, y+h-0.02, title, ha="left", va="top",
            fontsize=10, fontweight="bold", color=color, zorder=2)

def arrow(ax, x1, y1, x2, y2, color=C_ARROW, style="->", lw=1.5, label=""):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                        connectionstyle="arc3,rad=0.0"))
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx+0.1, my, label, fontsize=6.5, color=color, va="center")

def migration_arrow(ax, x1, y1, x2, y2, label, color):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=2.5,
                        linestyle="dashed", connectionstyle="arc3,rad=0.0"))
    ax.text((x1+x2)/2, (y1+y2)/2+0.2, label, ha="center",
            fontsize=8, fontweight="bold", color=color,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor=color, alpha=0.9))

# ═══════════════════════════════════════════════════════════════════════════
# OTSIKKO
# ═══════════════════════════════════════════════════════════════════════════
ax.text(11, 13.5, "Pientuottajat AI — Arkkitehtuuri & Migraatiopolku",
        ha="center", va="top", fontsize=16, fontweight="bold", color="#212121")
ax.text(11, 13.1, "SOK Tech Radar -linjattu   |   AWS   |   WhatsApp Business API   |   Amazon Bedrock",
        ha="center", va="top", fontsize=9, color="#546E7A")

# ═══════════════════════════════════════════════════════════════════════════
# VAIHE 1: DEMO
# ═══════════════════════════════════════════════════════════════════════════
cluster(ax, 0.3, 5.5, 6.8, 7.0, "VAIHE 1 — DEMO  (~0–5 €/kk, oma luottokortti)", C_DEMO, C_BG_D)

# Toimittaja
box(ax, 0.6, 11.2, 2.0, 0.9, "Pientoimittaja", "eri IT-taidot", bg="#E8EAF6", border="#3949AB")
# WhatsApp
box(ax, 0.6, 9.9, 2.0, 0.9, "WhatsApp", "Business Cloud API", bg=C_WA, border="#1B9448", fontsize=8)
# API Gateway
box(ax, 3.2, 9.9, 1.8, 0.9, "API Gateway", "1M req/kk\nilmaiseksi", bg=C_BOX, border=C_AWS)
# Webhook Lambda
box(ax, 3.2, 8.6, 1.8, 0.9, "Lambda\nWebhook", "Python 3.12", bg=C_BOX, border=C_AWS)
# Bedrock Haiku
box(ax, 3.2, 7.3, 1.8, 0.9, "Bedrock\nClaude Haiku", "~$0.001/viesti\n10x halvempi", bg="#FFF8E1", border="#F57F17")
# DynamoDB
box(ax, 0.6, 7.3, 2.0, 0.9, "DynamoDB", "Profiilit\nKeskusteluhistoria\n(25 GB ilm.)", bg=C_BOX, border=C_AWS)
# EventBridge
box(ax, 0.6, 6.0, 2.0, 0.9, "EventBridge\nScheduler", "Kuukausiraportti\nilmainen taso", bg=C_BOX, border=C_AWS)
# Notifier Lambda
box(ax, 3.2, 6.0, 1.8, 0.9, "Lambda\nNotifier", "Proaktiiviset\nhälytykset", bg=C_BOX, border=C_AWS)
# S3
box(ax, 3.2, 5.7, 1.8, 0.7, "S3 Raportit", "5 GB ilmaiseksi", bg=C_BOX, border=C_AWS, fontsize=7.5)

# Yhteydet demo
arrow(ax, 1.6, 11.2, 1.6, 10.8)          # toimittaja → WA
arrow(ax, 2.6, 10.35, 3.2, 10.35)        # WA → APIgw
arrow(ax, 4.1, 9.9, 4.1, 9.5)            # apigw → webhook
arrow(ax, 4.1, 8.6, 4.1, 8.2)            # webhook → bedrock
arrow(ax, 3.2, 7.75, 2.6, 7.75)          # bedrock → DDB
arrow(ax, 1.6, 9.9, 1.6, 8.2, label="")  # WA ← notifier (proaktiivinen)
arrow(ax, 3.2, 6.45, 2.6, 6.45)          # notifier ← EventBridge
arrow(ax, 0.6+1.0, 6.0, 3.2, 6.45, color=C_DEMO)  # EB → notifier
arrow(ax, 4.1, 6.0, 4.1, 5.7)            # notifier → S3

# ═══════════════════════════════════════════════════════════════════════════
# VAIHE 2: PILOTTI
# ═══════════════════════════════════════════════════════════════════════════
cluster(ax, 7.5, 5.5, 7.0, 7.0, "VAIHE 2 — PILOTTI  (~50–300 €/kk, 1–3 alueosuuskauppaa)", C_PILOTTI, C_BG_P)

box(ax, 7.8, 11.2, 2.2, 0.9, "WhatsApp +\nWeb Portal", "Next.js (SOK ADOPT)", bg=C_BOX, border=C_PILOTTI)
box(ax, 10.4, 11.2, 1.8, 0.9, "API Gateway", "+WAF", bg=C_BOX, border=C_AWS)
box(ax, 10.4, 9.9, 1.8, 0.9, "Lambda\nWebhook", "Python", bg=C_BOX, border=C_AWS)
box(ax, 10.4, 8.6, 1.8, 0.9, "Bedrock Agent\nClaude Sonnet", "Action Groups", bg="#FFF8E1", border="#F57F17")
box(ax, 7.8, 9.9, 2.0, 0.9, "DynamoDB\nMulti-tenant", "tenant_id\npartition", bg=C_BOX, border=C_AWS)
box(ax, 7.8, 8.6, 2.0, 0.9, "Confluent Kafka", "Toimituseventit\nReklamaatiot\n(SOK TRIAL)", bg=C_BOX, border=C_PILOTTI)
box(ax, 7.8, 7.3, 2.0, 0.9, "SQS FIFO", "Hälytysjono\n(SOK ADOPT)", bg=C_BOX, border=C_AWS)
box(ax, 10.4, 7.3, 1.8, 0.9, "SAP BTP\nOData", "Kassadata\nLaskutus", bg=C_BOX, border="#7B1FA2")
box(ax, 7.8, 6.0, 2.0, 0.9, "Monetisointi", "Free / Pro 49€/kk\n/ Enterprise", bg="#FCE4EC", border="#C62828")
box(ax, 10.4, 6.0, 1.8, 0.9, "QuickSight\nRaportit", "Toimittajat\n+ Kauppa", bg=C_BOX, border=C_AWS)

arrow(ax, 9.0, 11.65, 10.4, 11.65)
arrow(ax, 11.3, 11.2, 11.3, 10.8)
arrow(ax, 11.3, 9.9, 11.3, 9.5)
arrow(ax, 10.4, 9.05, 9.8, 9.05)
arrow(ax, 8.8, 8.6, 8.8, 8.2)
arrow(ax, 8.8, 7.3, 8.8, 6.9)
arrow(ax, 10.4, 7.75, 9.8, 7.75)
arrow(ax, 11.3, 7.3, 11.3, 6.9)

# ═══════════════════════════════════════════════════════════════════════════
# VAIHE 3: TUOTANTO
# ═══════════════════════════════════════════════════════════════════════════
cluster(ax, 14.9, 5.5, 6.8, 7.0, "VAIHE 3 — TUOTANTO  (SOK Tech Radar ADOPT, kaikki alueet)", C_TUOT, C_BG_T)

box(ax, 15.2, 11.2, 2.2, 0.9, "WhatsApp + Web\n+ API (3rd party)", "Multi-channel", bg=C_BOX, border=C_TUOT)
box(ax, 17.8, 11.2, 1.8, 0.9, "CloudFront\n+ WAF", "SOK ADOPT", bg=C_BOX, border=C_AWS)
box(ax, 17.8, 9.9, 1.8, 0.9, "ECS Fargate\nAgentit", "Long-running\nSOK ADOPT", bg=C_BOX, border=C_AWS)
box(ax, 15.2, 9.9, 2.2, 0.9, "Multi-Agent\nBedrock Orchestration", "Claude 3.5 Sonnet", bg="#FFF8E1", border="#F57F17")
box(ax, 15.2, 8.6, 2.2, 0.9, "Confluent Kafka\n+ Snowflake", "SOK TRIAL\nDatasharing", bg=C_BOX, border=C_TUOT)
box(ax, 17.8, 8.6, 1.8, 0.9, "Aurora\nServerless v2", "Analytiikka\nSOK ADOPT", bg=C_BOX, border=C_AWS)
box(ax, 15.2, 7.3, 2.2, 0.9, "ElasticSearch", "Haku & suodatus\nSOK ADOPT", bg=C_BOX, border=C_AWS)
box(ax, 17.8, 7.3, 1.8, 0.9, "X-Ray + Splunk", "Observability\nSOK ADOPT", bg=C_BOX, border=C_AWS)
box(ax, 15.2, 6.0, 2.2, 0.9, "QuickSight\n+ Survey Lambda", "Kaupan Liitto\nnäkymä + kyselyt", bg=C_BOX, border=C_TUOT)
box(ax, 17.8, 6.0, 1.8, 0.9, "Stripe /\nAWS Marketplace", "SaaS-laskutus\nMonetised", bg="#FCE4EC", border="#C62828")

arrow(ax, 17.4, 11.65, 17.8, 11.65)
arrow(ax, 18.7, 11.2, 18.7, 10.8)
arrow(ax, 17.8, 10.35, 17.4, 10.35)
arrow(ax, 16.3, 9.9, 16.3, 9.5)
arrow(ax, 17.4, 9.05, 17.8, 9.05)
arrow(ax, 16.3, 8.6, 16.3, 8.2)
arrow(ax, 18.7, 8.6, 18.7, 8.2)

# ═══════════════════════════════════════════════════════════════════════════
# MIGRAATIOPILIA
# ═══════════════════════════════════════════════════════════════════════════
migration_arrow(ax, 7.1, 9.0, 7.5, 9.0, "Viikko 1–2\nAsiakkaan hyväksyntä\n→ Pilotti", C_PILOTTI)
migration_arrow(ax, 14.5, 9.0, 14.9, 9.0, "Kk 2–6\nToimittajien\nonboarding → Tuotanto", C_TUOT)

# ═══════════════════════════════════════════════════════════════════════════
# LEGENDA
# ═══════════════════════════════════════════════════════════════════════════
legend_items = [
    (C_DEMO,    "Vaihe 1: Demo (Free Tier / ~$1-2 Bedrock-kulu)"),
    (C_PILOTTI, "Vaihe 2: Pilotti (asiakaslaskutus alkaa, oikeat integraatiot)"),
    (C_TUOT,    "Vaihe 3: Tuotanto (SOK Tech Radar ADOPT, full scale)"),
    ("#F57F17",  "Amazon Bedrock (AI-ydin)"),
    ("#C62828",  "Monetisointi (SaaS-tiers: Free / Pro 49€ / Enterprise)"),
]
for i, (c, lbl) in enumerate(legend_items):
    ax.add_patch(mpatches.Rectangle((0.4, 4.7 - i*0.4), 0.4, 0.28, color=c, zorder=5))
    ax.text(0.95, 4.84 - i*0.4, lbl, va="center", fontsize=8, color="#212121")

ax.text(0.4, 5.1, "Legenda:", fontsize=9, fontweight="bold", color="#212121")

# ── Tallennus ───────────────────────────────────────────────────────────────
out = "docs/diagrams/architecture.png"
plt.tight_layout(pad=0.5)
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"Kaavio tallennettu: {out}")
