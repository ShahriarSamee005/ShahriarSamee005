#!/usr/bin/env python3
"""Generate a custom isometric 3D contribution chart as assets/contrib-3d.svg.

Why custom instead of a third-party service:
  - bar height is driven by contribution LEVEL (0-4), not raw count, so even a
    single-commit day shows a clearly tall bar (no "dead/flat" look);
  - streak/total numbers are computed here and are always correct;
  - it is committed into the repo, so it renders reliably (no flaky service).

Run in CI:   python scripts/gen_contrib.py          (needs GH_TOKEN/GITHUB_TOKEN)
Preview:     python scripts/gen_contrib.py --mock    (random data, no network)
"""
from __future__ import annotations

import json
import os
import random
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

USERNAME = "ShahriarSamee005"
OUT = Path("assets/contrib-3d.svg")

# geometry
TW, TH = 11, 6                      # tile half-width / half-height (isometric)
HEIGHTS = {0: 3, 1: 16, 2: 26, 3: 37, 4: 48}   # bar height per level
TOP = {0: "#0A2036", 1: "#10507F", 2: "#1689FF", 3: "#4DB8FF", 4: "#9BE4FF"}
LEFT = {0: "#071726", 1: "#0B3A5E", 2: "#0F62BD", 3: "#2E90D8", 4: "#5FB9EF"}
RIGHT = {0: "#05121E", 1: "#082B45", 2: "#0A4C93", 3: "#1E6FB0", 4: "#3F97C9"}
LEVELS = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]

QUERY = """
query($login:String!){
  user(login:$login){
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""


def fetch():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Missing GH_TOKEN/GITHUB_TOKEN.")
    data = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=data,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "contrib-3d"})
    cal = json.load(urllib.request.urlopen(req, timeout=30))["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = []
    for w in cal["weeks"]:
        for d in w["contributionDays"]:
            days.append((d["date"], d["contributionCount"], LEVELS.index(d["contributionLevel"])))
    return cal["totalContributions"], days


def mock():
    today = date.today()
    start = today - timedelta(days=371)
    start -= timedelta(days=(start.weekday() + 1) % 7)   # back to Sunday
    days = []
    total = 0
    for i in range((today - start).days + 1):
        d = start + timedelta(days=i)
        r = random.random()
        lvl = 0 if r < 0.45 else 1 if r < 0.7 else 2 if r < 0.88 else 3 if r < 0.97 else 4
        cnt = [0, 2, 5, 9, 16][lvl]
        total += cnt
        days.append((d.isoformat(), cnt, lvl))
    return total, days


def streaks(days):
    cur = longest = run = 0
    for _, cnt, _ in days:
        if cnt > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    # current streak: walk backfrom the end
    for _, cnt, _ in reversed(days):
        if cnt > 0:
            cur += 1
        else:
            break
    return cur, longest


def diamond(cx, cy, h):
    return f"{cx},{cy-TH-h} {cx+TW},{cy-h} {cx},{cy+TH-h} {cx-TW},{cy-h}"


def bar(cx, cy, lvl):
    h = HEIGHTS[lvl]
    s = [f'<polygon points="{cx-TW},{cy} {cx},{cy+TH} {cx},{cy+TH-h} {cx-TW},{cy-h}" fill="{LEFT[lvl]}"/>',
         f'<polygon points="{cx+TW},{cy} {cx},{cy+TH} {cx},{cy+TH-h} {cx+TW},{cy-h}" fill="{RIGHT[lvl]}"/>',
         f'<polygon points="{diamond(cx,cy,h)}" fill="{TOP[lvl]}"/>']
    return "".join(s)


def build(total, days, placeholder=False):
    # index days into (week, weekday)
    cells = []
    week = 0
    for i, (dstr, cnt, lvl) in enumerate(days):
        wd = datetime.fromisoformat(dstr).date().weekday()   # Mon=0..Sun=6
        wd = (wd + 1) % 7                                     # Sun=0..Sat=6
        if i > 0 and wd == 0:
            week += 1
        cells.append((week, wd, lvl))
    ncols = week + 1

    ox = 70
    oy = 110
    draw = []
    for col, row, lvl in sorted(cells, key=lambda c: (c[0] + c[1], c[0])):
        cx = ox + (col - row) * TW
        cy = oy + (col + row) * TH
        draw.append(bar(cx, cy, lvl))

    width = ox + (ncols - 1) * TW + 7 * TW + 40
    height = oy + (ncols + 6) * TH + 90
    cur, longest = streaks(days)
    if placeholder:
        total_s = cur_s = long_s = "—"
    else:
        total_s, cur_s, long_s = f"{total:,}", str(cur), str(longest)
    note = ('<text x="30" y="70" font-family="%s" font-size="11" fill="#7FA6C9">preview · run the workflow to load live data</text>' % MONO) if placeholder else ''

    def stat(x, big, small):
        return (f'<text x="{x}" y="{height-46}" font-family="{MONO}" font-size="26" font-weight="700" fill="#E6F3FF">{big}</text>'
                f'<text x="{x}" y="{height-24}" font-family="{MONO}" font-size="13" fill="#7FA6C9">{small}</text>')

    legend = "".join(
        f'<polygon points="{diamond(width-170+i*26, 60, 0)}" fill="{TOP[i]}"/>' for i in range(5))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="3D contribution graph">
  <rect width="{width}" height="{height}" rx="16" fill="#050B14"/>
  <rect x="1.5" y="1.5" width="{width-3}" height="{height-3}" rx="15" fill="none" stroke="#0B5FA5" stroke-width="2" opacity="0.8"/>
  <text x="30" y="46" font-family="{MONO}" font-size="18" font-weight="700" fill="#4DB8FF">CONTRIBUTION ACTIVITY</text>
  <text x="{width-182}" y="52" font-family="{MONO}" font-size="11" fill="#7FA6C9">less</text>
  <text x="{width-28}" y="52" font-family="{MONO}" font-size="11" fill="#7FA6C9">more</text>
  {note}
  {legend}
  {''.join(draw)}
  {stat(30, total_s, "TOTAL CONTRIBUTIONS")}
  {stat(230, cur_s, "CURRENT STREAK (DAYS)")}
  {stat(460, long_s, "LONGEST STREAK (DAYS)")}
</svg>
'''


MONO = "'JetBrains Mono','DejaVu Sans Mono','Courier New',monospace"

if __name__ == "__main__":
    ph = "--placeholder" in sys.argv
    total, days = (mock() if (ph or "--mock" in sys.argv) else fetch())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(total, days, placeholder=ph), encoding="utf-8")
    print(f"Wrote {OUT} (placeholder={ph}, {len(days)} days)")
