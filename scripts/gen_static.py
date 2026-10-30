#!/usr/bin/env python3
"""Generate the static decorative SVGs (glowing social buttons + research chips).
Run once locally; the SVGs are committed to assets/ and never change at runtime.
"""
from pathlib import Path

ASSETS = Path("assets")
(ASSETS / "social").mkdir(parents=True, exist_ok=True)

BG = "#0A1A2E"
BORDER = "#4DB8FF"
TEXT = "#E6F3FF"
FONT = "'JetBrains Mono','DejaVu Sans Mono','Courier New',monospace"


def button(label: str) -> str:
    w = 40 + len(label) * 11
    h = 46
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">
  <defs>
    <filter id="g" x="-40%" y="-80%" width="180%" height="260%">
      <feGaussianBlur stdDeviation="2.5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect x="3" y="3" width="{w-6}" height="{h-6}" rx="13" fill="{BG}"/>
  <rect x="3" y="3" width="{w-6}" height="{h-6}" rx="13" fill="none" stroke="{BORDER}" stroke-width="1.6" filter="url(#g)" opacity="0.95"/>
  <circle cx="20" cy="{h//2}" r="3" fill="{BORDER}" filter="url(#g)"/>
  <text x="{(w+14)//2+4}" y="{h//2+5}" text-anchor="middle" font-family="{FONT}" font-size="15" font-weight="700" letter-spacing="1.5" fill="{TEXT}">{label}</text>
</svg>
'''


for name, label in [
    ("github", "GITHUB"),
    ("linkedin", "LINKEDIN"),
    ("portfolio", "PORTFOLIO"),
    ("email", "EMAIL"),
    ("scholar", "SCHOLAR"),
]:
    (ASSETS / "social" / f"{name}.svg").write_text(button(label), encoding="utf-8")


# ---- research interest chips (one wide SVG, glowing pills) ----
def chips(items, per_row=4, cw=252, ch=52, pad=14):
    rows = (len(items) + per_row - 1) // per_row
    width = per_row * cw + pad
    height = rows * ch + pad
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Research interests">',
           '<defs><filter id="g" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="2.3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>']
    for i, text in enumerate(items):
        r, c = divmod(i, per_row)
        x = pad + c * cw
        y = pad // 2 + r * ch
        pw = cw - 16
        out.append(f'<rect x="{x}" y="{y}" width="{pw}" height="{ch-16}" rx="18" fill="{BG}"/>')
        out.append(f'<rect x="{x}" y="{y}" width="{pw}" height="{ch-16}" rx="18" fill="none" stroke="{BORDER}" stroke-width="1.4" filter="url(#g)" opacity="0.9"/>')
        out.append(f'<text x="{x+pw//2}" y="{y+(ch-16)//2+5}" text-anchor="middle" font-family="{FONT}" font-size="14" font-weight="600" fill="{TEXT}">{text}</text>')
    out.append('</svg>')
    return "\n".join(out)


interests = [
    "Computer Vision", "Deep Learning", "Explainable AI", "Object Detection",
    "Multimodal Learning", "Interpretable AI", "Human-Centered AI", "Data-Limited AI",
]
(ASSETS / "research.svg").write_text(chips(interests), encoding="utf-8")

print("Generated:", [p.name for p in (ASSETS / "social").iterdir()], "+ research.svg")
