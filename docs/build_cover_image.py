"""
Generate MatRes cover image for Devpost (1200x630px).
Run: python docs/build_cover_image.py
Output: docs/matres_cover.png
"""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1200, 630

# Colours
DARK_BG      = (13,  27,  42)
CARD_BG      = (21,  40,  62)
ACCENT_BLUE  = (66,  133, 244)
ACCENT_GREEN = (52,  168,  83)
ACCENT_RED   = (234,  67,  53)
ACCENT_YELL  = (251, 188,   4)
WHITE        = (255, 255, 255)
LIGHT_GREY   = (180, 180, 200)
MID_GREY     = (100, 110, 130)

img  = Image.new("RGB", (W, H), DARK_BG)
draw = ImageDraw.Draw(img)

# ── Helper: try system fonts, fall back to default ────────────────────────────
def font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/System/Library/Fonts/SFNSText.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

# ── Top accent bar ─────────────────────────────────────────────────────────────
draw.rectangle([0, 0, W, 8], fill=ACCENT_BLUE)

# ── Bottom accent bar ──────────────────────────────────────────────────────────
draw.rectangle([0, H-8, W, H], fill=ACCENT_BLUE)

# ── Left panel — title block ───────────────────────────────────────────────────
# Badge
badge_font = font(13)
draw.rounded_rectangle([40, 28, 340, 52], radius=4, fill=CARD_BG)
draw.text((55, 32), "Google for Startups AI Agents Challenge 2026",
          font=badge_font, fill=MID_GREY)

# MatRes title
draw.text((40, 72), "MatRes", font=font(110, bold=True), fill=WHITE)

# Accent underline
draw.rectangle([40, 195, 320, 202], fill=ACCENT_BLUE)

# Subtitle
draw.text((40, 218), "Materials Resilience Agent",
          font=font(30, bold=True), fill=ACCENT_BLUE)

# Description
draw.text((40, 268),
          "Supply risk analysis for EV battery",
          font=font(20), fill=LIGHT_GREY)
draw.text((40, 296),
          "engineering teams — under 90 seconds.",
          font=font(20), fill=LIGHT_GREY)

# ── Stat cards (bottom left) ──────────────────────────────────────────────────
stats = [
    (ACCENT_RED,   "4",      "Sub-agents"),
    (ACCENT_BLUE,  "90s",    "Full report"),
    (ACCENT_GREEN, "100%",   "Cited output"),
    (ACCENT_YELL,  "3",      "Demo scenarios"),
]
x = 40
for color, value, label in stats:
    draw.rounded_rectangle([x, 370, x+130, 460], radius=8, fill=CARD_BG)
    draw.rectangle([x, 370, x+130, 376], fill=color)
    vfont = font(32, bold=True)
    vw = draw.textlength(value, font=vfont)
    draw.text((x + (130-vw)//2, 385), value, font=vfont, fill=color)
    lw = draw.textlength(label, font=font(13))
    draw.text((x + (130-lw)//2, 430), label, font=font(13), fill=MID_GREY)
    x += 148

# ── Right panel — architecture visual ─────────────────────────────────────────
rx = 640
panel_w = W - rx - 30

# Panel background
draw.rounded_rectangle([rx, 28, rx+panel_w, H-28], radius=12, fill=CARD_BG)

# BOM input box
bw = 160
draw.rounded_rectangle([rx + (panel_w-bw)//2, 50,
                         rx + (panel_w-bw)//2 + bw, 90],
                        radius=6, fill=ACCENT_BLUE)
bom_text = "BOM JSON"
bw_t = draw.textlength(bom_text, font=font(15, bold=True))
draw.text((rx + (panel_w-bw_t)//2, 63), bom_text,
          font=font(15, bold=True), fill=WHITE)

# Arrow down
draw.polygon([
    (rx + panel_w//2 - 8, 94),
    (rx + panel_w//2 + 8, 94),
    (rx + panel_w//2,     110),
], fill=MID_GREY)

# Orchestrator box
draw.rounded_rectangle([rx+20, 114, rx+panel_w-20, 165],
                        radius=6, fill=(30, 55, 90))
draw.text((rx + 35, 122), "Root Orchestrator",
          font=font(14, bold=True), fill=WHITE)
draw.text((rx + 35, 143), "Google ADK  ·  Gemini 2.5 Pro",
          font=font(12), fill=ACCENT_BLUE)

# Arrow down
draw.polygon([
    (rx + panel_w//2 - 8, 168),
    (rx + panel_w//2 + 8, 168),
    (rx + panel_w//2,     182),
], fill=MID_GREY)

# 4 agent boxes
agents = [
    (ACCENT_RED,   "Supply\nRisk"),
    (ACCENT_YELL,  "Failure\nModes"),
    (ACCENT_GREEN, "Substitu-\ntions"),
    (ACCENT_BLUE,  "Qualifica-\ntion"),
]
aw = (panel_w - 50) // 4
ax = rx + 15
for color, label in agents:
    draw.rounded_rectangle([ax, 186, ax+aw, 262], radius=6, fill=CARD_BG)
    draw.rectangle([ax, 186, ax+aw, 192], fill=color)
    lines = label.split("\n")
    for i, line in enumerate(lines):
        lw = draw.textlength(line, font=font(12, bold=True))
        draw.text((ax + (aw-lw)//2, 204 + i*18), line,
                  font=font(12, bold=True), fill=color)
    ax += aw + 6

# Arrow down
draw.polygon([
    (rx + panel_w//2 - 8, 266),
    (rx + panel_w//2 + 8, 266),
    (rx + panel_w//2,     280),
], fill=MID_GREY)

# Risk Report box
draw.rounded_rectangle([rx+20, 284, rx+panel_w-20, 330],
                        radius=6, fill=(20, 50, 30))
rr_text = "RiskReport  ·  Composite Score"
rr_w = draw.textlength(rr_text, font=font(13, bold=True))
draw.text((rx + (panel_w - rr_w)//2, 299), rr_text,
          font=font(13, bold=True), fill=ACCENT_GREEN)

# Tech stack pills
pills = ["Gemini 2.5 Pro", "Google ADK", "MCP", "Cloud Run", "Vertex AI"]
px = rx + 18
py = 355
for pill in pills:
    pw = int(draw.textlength(pill, font=font(11))) + 18
    if px + pw > rx + panel_w - 10:
        px = rx + 18
        py += 30
    draw.rounded_rectangle([px, py, px+pw, py+22], radius=11, fill=(30,55,90))
    draw.text((px+9, py+4), pill, font=font(11), fill=ACCENT_BLUE)
    px += pw + 8

# Cloud Run footer in right panel
cr_text = "Live on Cloud Run · GCP us-central1"
cr_w = draw.textlength(cr_text, font=font(11))
draw.text((rx + (panel_w-cr_w)//2, H-55),
          cr_text, font=font(11), fill=MID_GREY)

# ── Save ──────────────────────────────────────────────────────────────────────
out = os.path.join(os.path.dirname(__file__), "matres_cover.png")
img.save(out, "PNG")
print(f"Saved: {out}  ({W}x{H}px)")
