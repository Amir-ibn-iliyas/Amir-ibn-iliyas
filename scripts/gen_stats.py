#!/usr/bin/env python3
"""
Generates stats.svg and langs.svg from the GitHub GraphQL API.

No third-party services, so nothing can 503 on you. Runs in Actions with the
built-in GITHUB_TOKEN and commits the rendered SVGs back into the repo.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

USER = os.environ.get("GH_USER") or sys.exit("GH_USER not set")
TOKEN = os.environ.get("GH_TOKEN") or sys.exit("GH_TOKEN not set")

# ---- palette (matches hero-banner.svg) -------------------------------------
BG, BAR, LINE = "#090E1A", "#0D1424", "#1C2740"
RED, BLUE, AMBER = "#E62429", "#1B72BE", "#F0A202"
WHITE, MUTED, DIM = "#FFFFFF", "#9DB0CB", "#4E5D78"
MONO = "'SF Mono','DejaVu Sans Mono',Consolas,'Courier New',monospace"

QUERY = """
query($login:String!) {
  user(login:$login) {
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar { totalContributions }
    }
    repositories(first:100, ownerAffiliations:OWNER, isFork:false,
                 orderBy:{field:STARGAZERS, direction:DESC}) {
      totalCount
      nodes {
        stargazerCount
        languages(first:12, orderBy:{field:SIZE, direction:DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "profile-stats",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        payload = json.load(r)
    if "errors" in payload:
        sys.exit("GraphQL error: " + json.dumps(payload["errors"]))
    return payload["data"]["user"]


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def shell(width, height, title, inner):
    """Terminal window chrome shared by both cards."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{esc(title)}">
<defs>
  <style>
    .m{{font-family:{MONO};font-size:13px}}
    .lb{{fill:{MUTED}}} .vl{{fill:{WHITE};font-weight:bold}} .dm{{fill:{DIM}}}
    .ps{{fill:{RED};font-weight:bold}} .cm{{fill:#E8EEF7}}
    .cur{{fill:{RED};animation:bl 1.05s steps(1) infinite}}
    @keyframes bl{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
    .grow{{animation:gw 1.1s cubic-bezier(.2,.8,.3,1) forwards;transform-origin:left center}}
    @keyframes gw{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
    @media (prefers-reduced-motion:reduce){{.cur{{animation:none}}.grow{{animation:none}}}}
  </style>
  <clipPath id="round"><rect width="{width}" height="{height}" rx="12"/></clipPath>
</defs>
<g clip-path="url(#round)">
  <rect width="{width}" height="{height}" fill="{BG}"/>
  <rect width="{width}" height="38" fill="{BAR}"/>
  <line x1="0" y1="38" x2="{width}" y2="38" stroke="{LINE}"/>
  <circle cx="20" cy="19" r="5" fill="{RED}"/><circle cx="38" cy="19" r="5" fill="{AMBER}"/><circle cx="56" cy="19" r="5" fill="{BLUE}"/>
  <text class="m" x="{width/2}" y="24" text-anchor="middle" fill="{DIM}" font-size="11">{esc(title)}</text>
{inner}
  <rect y="{height-32}" width="{width}" height="32" fill="#0A1120"/>
  <line x1="0" y1="{height-32}" x2="{width}" y2="{height-32}" stroke="{LINE}"/>
  <rect x="0" y="{height-32}" width="4" height="32" fill="{RED}"/>
  <text class="m" x="22" y="{height-12}" fill="{DIM}" font-size="10.5">{esc(USER)}</text>
  <text class="m" x="{width-20}" y="{height-12}" text-anchor="end" fill="{DIM}" font-size="10.5">updated {stamp}</text>
</g>
</svg>
'''


def fmt(n):
    return f"{n:,}"


def build_stats(u, path):
    c = u["contributionsCollection"]
    repos = u["repositories"]
    stars = sum(r["stargazerCount"] for r in repos["nodes"])
    rows = [
        ("total contributions", c["contributionCalendar"]["totalContributions"], "past year"),
        ("commits", c["totalCommitContributions"], "past year"),
        ("pull requests", c["totalPullRequestContributions"], ""),
        ("code reviews", c["totalPullRequestReviewContributions"], ""),
        ("issues opened", c["totalIssueContributions"], ""),
        ("public repositories", repos["totalCount"], ""),
        ("stars earned", stars, ""),
        ("followers", u["followers"]["totalCount"], ""),
    ]
    w, h = 520, 330
    out = [f'  <text class="m" x="22" y="70"><tspan class="ps">❯</tspan>'
           f'<tspan class="cm" dx="10">gh stats --user {esc(USER)}</tspan></text>']
    y = 100
    for label, value, note in rows:
        out.append(f'  <text class="m" x="26" y="{y}" fill="{MUTED}">{esc(label)}</text>')
        if note:
            out.append(f'  <text class="m" x="{w-26}" y="{y}" text-anchor="end" fill="{DIM}" font-size="10.5">{esc(note)}</text>')
            out.append(f'  <text class="m" x="{w-96}" y="{y}" text-anchor="end" font-weight="bold" fill="{WHITE}">{fmt(value)}</text>')
        else:
            out.append(f'  <text class="m" x="{w-26}" y="{y}" text-anchor="end" font-weight="bold" fill="{WHITE}">{fmt(value)}</text>')
        y += 26
    out.append(f'  <text class="m" x="22" y="{y+8}"><tspan class="ps">❯</tspan></text>')
    out.append(f'  <rect class="cur" x="40" y="{y-5}" width="9" height="15"/>')
    open(path, "w", encoding="utf-8").write(shell(w, h, f"{USER} — gh stats", "\n".join(out)))


def build_langs(u, path, top=6):
    totals, colors = {}, {}
    for repo in u["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]
            colors[name] = edge["node"]["color"] or BLUE
    if not totals:
        totals, colors = {"No data": 1}, {"No data": DIM}
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:top]
    grand = sum(v for _, v in ranked) or 1

    w, h = 520, 330
    bar_x, bar_w, bar_y = 26, w - 52, 92
    out = [f'  <text class="m" x="22" y="70"><tspan class="ps">❯</tspan>'
           f'<tspan class="cm" dx="10">gh langs --top {top}</tspan></text>',
           f'  <clipPath id="barclip"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="16" rx="8"/></clipPath>',
           '  <g clip-path="url(#barclip)">']
    x = bar_x
    for i, (name, size) in enumerate(ranked):
        seg = bar_w * size / grand
        out.append(f'    <rect class="grow" x="{x:.1f}" y="{bar_y}" width="{seg:.1f}" height="16" '
                   f'fill="{colors[name]}" style="animation-delay:{i*0.09:.2f}s"/>')
        x += seg
    out.append('  </g>')

    y = 146
    for name, size in ranked:
        pct = 100 * size / grand
        out.append(f'  <circle cx="32" cy="{y-4}" r="5" fill="{colors[name]}"/>')
        out.append(f'  <text class="m" x="48" y="{y}" fill="{MUTED}">{esc(name)}</text>')
        out.append(f'  <text class="m" x="{w-26}" y="{y}" text-anchor="end" fill="{WHITE}" font-weight="bold">{pct:.1f}%</text>')
        y += 26
    out.append(f'  <text class="m" x="22" y="{y+8}"><tspan class="ps">❯</tspan></text>')
    out.append(f'  <rect class="cur" x="40" y="{y-5}" width="9" height="15"/>')
    open(path, "w", encoding="utf-8").write(shell(w, h, f"{USER} — gh langs", "\n".join(out)))


if __name__ == "__main__":
    user = fetch()
    build_stats(user, "stats.svg")
    build_langs(user, "langs.svg")
    print("wrote stats.svg and langs.svg")
