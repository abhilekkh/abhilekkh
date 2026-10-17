"""Render an animated "Sakura Ninja" SVG from a user's GitHub contribution calendar.

A chibi ninja dashes across the graph at night; every day with contributions
blooms into cherry-blossom pink as the ninja passes, while petals drift down.

Usage: GITHUB_TOKEN=... python scripts/sakura.py <username> <output.svg>
Stdlib only, so it runs on a bare GitHub Actions runner.
"""

import json
import os
import random
import sys
import urllib.request

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount weekday } }
      }
    }
  }
}
"""

CELL, GAP = 11, 3
STEP = CELL + GAP
PAD_X, GRID_TOP = 24, 118
CYCLE = 20.0  # seconds for one full loop
RUN = 13.0  # seconds the ninja takes to cross the screen

EMPTY = "#2a2440"
BLOOM = ["#2a2440", "#7a2f5e", "#b8457f", "#ef6fa8", "#ffc4dd"]


def fetch_calendar(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def levels(weeks):
    """Bucket counts into 0-4 using quartiles of the non-zero days, like GitHub does."""
    counts = sorted(d["contributionCount"] for w in weeks for d in w["contributionDays"] if d["contributionCount"])
    if not counts:
        return lambda c: 0
    q = [counts[int(len(counts) * f)] for f in (0.25, 0.5, 0.75)]

    def level(c):
        if c == 0:
            return 0
        return 1 + sum(c > t for t in q)

    return level


def ninja():
    """Chibi ninja, origin at its feet, facing right."""
    return """
  <g class="bob">
    <path class="scarf" d="M-4,-25 C-14,-27 -20,-22 -28,-25 M-4,-23 C-12,-21 -18,-17 -25,-18" stroke="#ff5c9a" stroke-width="3" fill="none" stroke-linecap="round"/>
    <g class="legA"><rect x="-4" y="-9" width="4" height="9" rx="2" fill="#1b1430"/></g>
    <g class="legB"><rect x="1" y="-9" width="4" height="9" rx="2" fill="#1b1430"/></g>
    <rect x="-7" y="-17" width="14" height="10" rx="4" fill="#3b2f63"/>
    <circle cx="0" cy="-25" r="10" fill="#3b2f63"/>
    <rect x="-8" y="-28" width="17" height="6" rx="3" fill="#ffe3cf"/>
    <circle cx="2" cy="-25" r="1.6" fill="#1b1430"/>
    <circle cx="6.5" cy="-25" r="1.6" fill="#1b1430"/>
    <path d="M-10,-31 L10,-31" stroke="#ff5c9a" stroke-width="3" stroke-linecap="round"/>
    <circle cx="10" cy="-12" r="2.4" fill="#ffe3cf"/>
  </g>"""


def petal(rng, width, height):
    x = rng.uniform(0, width)
    drift = rng.uniform(-80, 40)
    dur = rng.uniform(7, 13)
    delay = -rng.uniform(0, dur)
    scale = rng.uniform(0.6, 1.2)
    return (
        f'<g transform="translate({x:.0f},-12)"><g class="petal" style="--dx:{drift:.0f}px;--dy:{height + 24}px;'
        f'animation-duration:{dur:.1f}s;animation-delay:{delay:.1f}s">'
        f'<path transform="scale({scale:.2f})" d="M0,0 C4,-5 9,-1 6,4 C4,8 -1,8 -3,4 C-5,0 -3,-3 0,0Z" fill="#ffb7d2" opacity=".85"/>'
        f"</g></g>"
    )


def render(login, cal):
    weeks = cal["weeks"]
    width = PAD_X * 2 + len(weeks) * STEP - GAP
    height = GRID_TOP + 7 * STEP + 34
    level = levels(weeks)
    run_dist = width + 80
    rng = random.Random(login)

    def pass_time(x):
        return RUN * (x + 40) / run_dist

    cells = []
    for wi, week in enumerate(weeks):
        x = PAD_X + wi * STEP
        delay = pass_time(x + CELL / 2)
        for day in week["contributionDays"]:
            y = GRID_TOP + day["weekday"] * STEP
            lv = level(day["contributionCount"])
            cls = f' class="b{lv}" style="animation-delay:{delay:.2f}s"' if lv else ""
            cells.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{EMPTY}"{cls}/>')

    stars = "".join(
        f'<circle cx="{rng.uniform(0, width):.0f}" cy="{rng.uniform(6, GRID_TOP - 30):.0f}" r="{rng.uniform(.5, 1.3):.1f}" '
        f'fill="#fff" class="star" style="animation-delay:{-rng.uniform(0, 4):.1f}s"/>'
        for _ in range(40)
    )
    petals = "".join(petal(rng, width, height) for _ in range(22))

    bloom_css = "\n".join(
        f".b{i}{{animation:bloom{i} {CYCLE}s linear infinite backwards}}"
        f"@keyframes bloom{i}{{0%{{fill:{EMPTY}}}2%{{fill:#fff}}5%,82%{{fill:{BLOOM[i]}}}92%,100%{{fill:{EMPTY}}}}}"
        for i in range(1, 5)
    )
    run_pct = RUN / CYCLE * 100
    ground_y = GRID_TOP - 6

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>
{bloom_css}
.runner{{animation:run {CYCLE}s linear infinite}}
@keyframes run{{0%{{transform:translate(-40px,{ground_y}px)}}{run_pct:.1f}%,100%{{transform:translate({width + 40}px,{ground_y}px)}}}}
.bob{{animation:bob .32s ease-in-out infinite alternate}}
@keyframes bob{{to{{transform:translateY(-2px)}}}}
.legA{{transform-origin:-2px -9px;animation:leg .32s ease-in-out infinite alternate}}
.legB{{transform-origin:3px -9px;animation:leg .32s ease-in-out infinite alternate-reverse}}
@keyframes leg{{from{{transform:rotate(-35deg)}}to{{transform:rotate(35deg)}}}}
.scarf{{animation:flap .25s ease-in-out infinite alternate}}
@keyframes flap{{to{{transform:translateY(2px)}}}}
.petal{{animation-name:fall;animation-timing-function:linear;animation-iteration-count:infinite}}
@keyframes fall{{from{{transform:translate(0,0) rotate(0)}}to{{transform:translate(var(--dx),var(--dy)) rotate(540deg)}}}}
.star{{animation:twinkle 4s ease-in-out infinite}}
@keyframes twinkle{{50%{{opacity:.2}}}}
text{{font-family:'Segoe UI','Hiragino Sans','Noto Sans JP',sans-serif}}
</style>
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#140f26"/><stop offset="1" stop-color="#241a3d"/>
  </linearGradient>
  <radialGradient id="glow"><stop offset="0" stop-color="#ffe8f2" stop-opacity=".35"/><stop offset="1" stop-color="#ffe8f2" stop-opacity="0"/></radialGradient>
</defs>
<rect width="{width}" height="{height}" rx="14" fill="url(#sky)"/>
{stars}
<circle cx="{width - 70}" cy="38" r="48" fill="url(#glow)"/>
<circle cx="{width - 70}" cy="38" r="22" fill="#fff1f6"/>
<text x="{PAD_X}" y="34" fill="#ffc4dd" font-size="18" font-weight="700">桜 Sakura Ninja</text>
<text x="{PAD_X}" y="56" fill="#b9a7d9" font-size="12">{cal["totalContributions"]} contributions in the last year · @{login}</text>
{"".join(cells)}
{petals}
<g class="runner"><g transform="scale(1.25)">{ninja()}
</g></g>
<text x="{width - PAD_X}" y="{height - 12}" fill="#7d6aa6" font-size="10" text-anchor="end">頑張って! ✿</text>
</svg>
"""


def main():
    login, out = sys.argv[1], sys.argv[2]
    cal = fetch_calendar(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(login, cal))
    print(f"wrote {out} ({cal['totalContributions']} contributions)")


if __name__ == "__main__":
    main()
