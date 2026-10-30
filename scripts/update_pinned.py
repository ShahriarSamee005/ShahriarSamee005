#!/usr/bin/env python3
"""Render Featured Projects from GitHub pinned repositories as custom SVG cards.

Each pinned repo becomes assets/projects/<slug>.svg with: a monogram app-icon
(in the repo's top-language colour), name, description, language tag pills, a
language-percentage list, a donut ring for the top language, stars and "updated".
The README block is rewritten with one linked card image per repo, in pin order.

CI:       python scripts/update_pinned.py           (needs GH_TOKEN/GITHUB_TOKEN)
Preview:  python scripts/update_pinned.py --mock      (sample data, no network)
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USERNAME = "ShahriarSamee005"
README = Path("README.md")
CARD_DIR = Path("assets/projects")
ICONS_SRC = Path("assets/projects/icons")
START = "<!-- PINNED:START -->"
END = "<!-- PINNED:END -->"
MAX_PINS = 6

BG = "#0B1A2E"
BORDER = "#17334F"
CYAN = "#4DB8FF"
WHITE = "#E6F3FF"
MUTED = "#7FA6C9"
MONO = "'JetBrains Mono','DejaVu Sans Mono','Courier New',monospace"
W, H = 440, 176

QUERY = """
query($login:String!){
  user(login:$login){
    pinnedItems(first:6, types:REPOSITORY){
      nodes{ ... on Repository{
        name url description stargazerCount pushedAt
        languages(first:5, orderBy:{field:SIZE, direction:DESC}){
          totalSize edges{ size node{ name color } }
        }
      }}
    }
  }
}
"""


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fetch():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Missing GH_TOKEN/GITHUB_TOKEN.")
    data = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=data,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "pinned-cards"})
    res = json.load(urllib.request.urlopen(req, timeout=30))
    if res.get("errors"):
        raise SystemExit(f"GraphQL error: {res['errors']}")
    user = res["data"]["user"]
    if not user:
        raise SystemExit(f"User '{USERNAME}' not found.")
    out = []
    for n in user["pinnedItems"]["nodes"][:MAX_PINS]:
        langs = []
        total = n["languages"]["totalSize"] or 1
        for e in n["languages"]["edges"]:
            langs.append((e["node"]["name"], e["node"]["color"] or "#4DB8FF",
                          round(e["size"] * 100 / total)))
        out.append({"name": n["name"], "url": n["url"],
                    "desc": n["description"] or "No description provided.",
                    "stars": n["stargazerCount"], "pushed": n["pushedAt"], "langs": langs})
    return out


def mock():
    def r(name, desc, stars, days, langs):
        return {"name": name, "url": f"https://github.com/{USERNAME}/{name}", "desc": desc,
                "stars": stars,
                "pushed": f"2026-{10 - days // 30:02d}-15T00:00:00Z", "langs": langs}
    return [
        r("ChronoPlan", "Hourly retrospective time logging with AI coaching.", 2, 25,
          [("Dart", "#00B4AB", 61), ("HTML", "#e34c26", 24), ("C++", "#f34b7d", 7)]),
        r("BeyondSilence", "Sign-language recognition and communication aid.", 0, 90,
          [("Dart", "#00B4AB", 72), ("C++", "#f34b7d", 18), ("CMake", "#064F8C", 10)]),
        r("CodexHackathon", "Hackathon project built in 36 hours.", 1, 200,
          [("Python", "#3572A5", 88), ("Jupyter", "#DA5B0B", 12)]),
        r("Explaniarmus", "Explainable-AI demo for model predictions.", 1, 300,
          [("Dart", "#00B4AB", 55), ("C++", "#f34b7d", 25), ("CMake", "#064F8C", 20)]),
        r("Digital-Delta-Hackfusion", "Team hackathon build.", 0, 120,
          [("Dart", "#00B4AB", 80), ("C++", "#f34b7d", 12), ("CMake", "#064F8C", 8)]),
        r("work_sleep_repeat", "Pixel-art room status for a shared account.", 1, 150,
          [("Dart", "#00B4AB", 90), ("Swift", "#F05138", 10)]),
    ]


def ago(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return ""
    days = (datetime.now(timezone.utc) - dt).days
    if days < 1:
        return "updated today"
    if days < 30:
        return f"updated {days}d ago"
    if days < 365:
        return f"updated {days // 30}mo ago"
    return f"updated {days // 365}y ago"


def pill(x, y, text, color):
    w = 16 + len(text) * 7.2
    return (f'<rect x="{x}" y="{y}" width="{w:.0f}" height="20" rx="10" fill="{color}" fill-opacity="0.14" stroke="{color}" stroke-opacity="0.6"/>'
            f'<text x="{x + w/2:.0f}" y="{y+14}" text-anchor="middle" font-family="{MONO}" font-size="10" fill="{WHITE}">{esc(text)}</text>'), w + 8


def donut(cx, cy, r, pct, color):
    import math
    C = 2 * math.pi * r
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#13273E" stroke-width="6"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="6" '
            f'stroke-linecap="round" stroke-dasharray="{C*pct/100:.1f} {C:.1f}" '
            f'transform="rotate(-90 {cx} {cy})"/>'
            f'<text x="{cx}" y="{cy+5}" text-anchor="middle" font-family="{MONO}" font-size="14" '
            f'font-weight="700" fill="{WHITE}">{pct}%</text>')


def wrap(text, width_chars, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len((cur + " " + w).strip()) <= width_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    # ellipsize if text was truncated
    joined = " ".join(lines)
    if len(joined) < len(text.strip()) and lines:
        last = lines[-1]
        lines[-1] = (last[:width_chars - 1].rstrip() + "…")
    return lines[:max_lines]


def icon_markup(name, color, mono):
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    f = ICONS_SRC / f"{key}.png"
    if f.exists():
        b64 = base64.b64encode(f.read_bytes()).decode()
        defs = ('<defs><clipPath id="tile"><rect x="18" y="40" width="44" height="44" rx="11"/>'
                '</clipPath></defs>')
        img = (f'<image x="18" y="40" width="44" height="44" clip-path="url(#tile)" '
               f'preserveAspectRatio="xMidYMid slice" href="data:image/png;base64,{b64}"/>'
               f'<rect x="18" y="40" width="44" height="44" rx="11" fill="none" '
               f'stroke="{color}" stroke-opacity="0.7"/>')
        return img, defs
    tile = (f'<rect x="18" y="40" width="44" height="44" rx="11" fill="{color}" fill-opacity="0.16" '
            f'stroke="{color}" stroke-opacity="0.7"/>'
            f'<text x="40" y="70" text-anchor="middle" font-family="{MONO}" font-size="22" '
            f'font-weight="700" fill="{WHITE}">{esc(mono)}</text>')
    return tile, ""


def card_svg(repo: dict) -> str:
    langs = repo["langs"] or [("Code", CYAN, 100)]
    top_name, top_color, top_pct = langs[0]
    mono = repo["name"][0].upper()
    icon_block, defs = icon_markup(repo["name"], top_color, mono)

    name = repo["name"]
    name_fs = 17 if len(name) <= 16 else 14 if len(name) <= 22 else 12
    if len(name) > 24:
        name = name[:23] + "…"

    desc_lines = wrap(repo["desc"], 26, 2)

    # language tag pills (names), up to 3, left column
    px, pills = 70, []
    for lname, color, _ in langs[:3]:
        s, dw = pill(px, 116, lname, color)
        pills.append(s)
        px += dw

    # language percentage list (right column), up to 3
    rows = []
    for i, (lname, color, pct) in enumerate(langs[:3]):
        y = 56 + i * 19
        rows.append(f'<circle cx="262" cy="{y-4}" r="4" fill="{color}"/>'
                    f'<text x="274" y="{y}" font-family="{MONO}" font-size="11" fill="{MUTED}">{esc(lname)} {pct}%</text>')

    desc_svg = "".join(
        f'<text x="70" y="{80 + i*17}" font-family="{MONO}" font-size="11.5" fill="{MUTED}">{esc(line)}</text>'
        for i, line in enumerate(desc_lines))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(repo['name'])}">
  {defs}
  <rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{BG}"/>
  <rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="none" stroke="{BORDER}" stroke-width="1.5"/>
  <circle cx="22" cy="20" r="3" fill="{CYAN}"/>
  <text x="34" y="24" font-family="{MONO}" font-size="11" fill="{MUTED}">{esc(USERNAME)}/{esc(repo['name'])}</text>
  {icon_block}
  <text x="70" y="57" font-family="{MONO}" font-size="{name_fs}" font-weight="700" fill="{WHITE}">{esc(name)}<tspan fill="{CYAN}">_</tspan></text>
  {desc_svg}
  {''.join(rows)}
  {donut(402, 68, 26, top_pct, top_color)}
  {''.join(pills)}
  <text x="70" y="154" font-family="{MONO}" font-size="11" fill="{MUTED}">&#9733; {repo['stars']} &#160;&#160;·&#160;&#160; {ago(repo['pushed'])}</text>
</svg>
'''


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "-", name)


def build_block(repos):
    if not repos:
        return ('<div align="center"><sub>No pinned repositories found. '
                'Pin repositories on your profile and this section updates automatically.</sub></div>')
    cells = []
    for repo in repos:
        rel = f"./assets/projects/{slug(repo['name'])}.svg"
        cells.append(f'<a href="{esc(repo["url"])}"><img src="{rel}" width="100%" alt="{esc(repo["name"])}"/></a>')
    rows = []
    for i in range(0, len(cells), 2):
        pair = cells[i:i + 2]
        tds = "".join(f'<td width="50%">{c}</td>' for c in pair)
        if len(pair) == 1:
            tds += '<td width="50%"></td>'
        rows.append(f"<tr>{tds}</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def main():
    repos = mock() if ("--mock" in sys.argv or "--placeholder" in sys.argv) else fetch()
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    # clear stale cards
    for f in CARD_DIR.glob("*.svg"):
        f.unlink()
    for repo in repos:
        (CARD_DIR / f"{slug(repo['name'])}.svg").write_text(card_svg(repo), encoding="utf-8")

    content = README.read_text(encoding="utf-8")
    block = f"{START}\n{build_block(repos)}\n{END}"
    updated = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, content, count=1, flags=re.S)
    README.write_text(updated, encoding="utf-8")
    print(f"Wrote {len(repos)} project cards.")


if __name__ == "__main__":
    main()
