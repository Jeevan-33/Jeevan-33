"""Generate profile SVGs (stats card + animated F1 race track) from the GitHub GraphQL API."""
import datetime as dt, html, json, os, urllib.request

USER = os.environ.get("GH_USER", "Jeevan-33")
TOKEN = os.environ["GH_TOKEN"]
QUERY = """query($u:String!){user(login:$u){
 followers{totalCount}
 publicRepos: repositories(ownerAffiliations:OWNER, privacy:PUBLIC){totalCount}
 repositories(ownerAffiliations:OWNER, isFork:false, first:100){nodes{stargazerCount
  languages(first:10, orderBy:{field:SIZE, direction:DESC}){edges{size node{name color}}}}}
 contributionsCollection{totalCommitContributions totalPullRequestContributions totalIssueContributions
  contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": QUERY, "variables": {"u": USER}}).encode(),
    headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-graph"},
)
u = json.load(urllib.request.urlopen(req))["data"]["user"]
cc = u["contributionsCollection"]
cal = cc["contributionCalendar"]
today = dt.date.today().isoformat()
days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
days = [d for d in days if d[0] <= today]

longest = cur = 0
for _, c in days:
    cur = cur + 1 if c else 0
    longest = max(longest, cur)
cur = 0
for d, c in reversed(days):
    if c:
        cur += 1
    elif cur or d != today:
        break

FONT = 'font-family="Segoe UI,Arial,sans-serif"'

# ---------- animated F1 race track ----------
last = days[-30:]
recent = sum(c for _, c in last)
lap = max(5.0, 14.0 - recent * 0.25)          # more activity -> faster laps
kmh = min(350, 120 + recent * 6)

SEGS = [  # closed circuit as cubic beziers: (p0, c1, c2, p1)
    ((120, 200), (120, 130), (190, 95), (280, 110)),
    ((280, 110), (370, 125), (410, 200), (490, 150)),
    ((490, 150), (570, 100), (650, 60), (700, 115)),
    ((700, 115), (750, 170), (740, 235), (640, 245)),
    ((640, 245), (540, 255), (300, 245), (220, 245)),
    ((220, 245), (140, 245), (120, 235), (120, 200)),
]
d = f"M{SEGS[0][0][0]},{SEGS[0][0][1]} " + " ".join(
    f"C{a[0]},{a[1]} {b[0]},{b[1]} {c[0]},{c[1]}" for _, a, b, c in SEGS) + " Z"


def bez(seg, t):
    p0, c1, c2, p1 = seg
    m = 1 - t
    return tuple(m**3 * p0[i] + 3 * m * m * t * c1[i] + 3 * m * t * t * c2[i] + t**3 * p1[i] for i in range(2))


samples = [bez(s, k / 60) for s in SEGS for k in range(60)]
cum = [0.0]
for a, b in zip(samples, samples[1:] + samples[:1]):
    cum.append(cum[-1] + ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5)
total = cum[-1]


def at(frac):
    target, i = frac * total, 0
    while i < len(samples) - 1 and cum[i + 1] < target:
        i += 1
    return samples[i]


marks = ""
for i, (day, c) in enumerate(last):
    x, y = at((i + 0.5) / len(last))
    if c:
        marks += (f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#f2c811" stroke="#fff" stroke-width="1.5">'
                  f'<animate attributeName="r" values="6;8;6" dur="1.4s" begin="{(i % 7) * 0.2:.1f}s" repeatCount="indefinite"/></circle>'
                  f'<text x="{x:.1f}" y="{y+3:.1f}" text-anchor="middle" font-size="8" font-weight="700" fill="#0d1117">{c}</text>'
                  f'<title>{day}: {c} contribution(s)</title></g>')
    else:
        marks += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="#484f58"><title>{day}: none</title></circle>'

car = """<g transform="scale(1.25)">
<rect x="-12" y="-9" width="8" height="4" rx="1" fill="#111"/><rect x="-12" y="5" width="8" height="4" rx="1" fill="#111"/>
<rect x="8" y="-9" width="7" height="4" rx="1" fill="#111"/><rect x="8" y="5" width="7" height="4" rx="1" fill="#111"/>
<rect x="-19" y="-7" width="4" height="14" fill="#22d3ee"/><rect x="15" y="-7" width="4" height="14" fill="#22d3ee"/>
<polygon points="-16,-3.5 4,-3.5 18,-1 18,1 4,3.5 -16,3.5" fill="#2f81f7"/>
<circle cx="-3" cy="0" r="2.6" fill="#fff"/></g>"""
smoke = "".join(
    f'<circle r="{5-k}" fill="#8b949e" opacity="{0.45-k*0.1:.2f}"><animateMotion dur="{lap:.1f}s" begin="-{(k+1)*0.14:.2f}s" repeatCount="indefinite" path="{d}"/></circle>'
    for k in range(4))
hud = [(cal["totalContributions"], "POINTS (year)"), (cur, "STREAK"), (longest, "BEST STREAK"),
       (f"{kmh}", "KM/H"), (f"{lap:.1f}s", "LAP TIME")]
hud_svg = "".join(
    f'<text x="{80+i*160}" y="28" text-anchor="middle" font-size="22" font-weight="700" fill="#2f81f7">{v}</text>'
    f'<text x="{80+i*160}" y="45" text-anchor="middle" font-size="10" letter-spacing="1" fill="#8b949e">{l}</text>'
    for i, (v, l) in enumerate(hud))
W, H = 800, 310
with open("assets/race-track.svg", "w", encoding="utf-8") as f:
    f.write(f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" {FONT}>
<rect width="{W}" height="{H}" rx="8" fill="#0d1117" stroke="#21262d"/>{hud_svg}
<path d="{d}" fill="none" stroke="#f85149" stroke-width="32" stroke-linejoin="round"/>
<path d="{d}" fill="none" stroke="#fff" stroke-width="32" stroke-dasharray="10 10" stroke-linejoin="round"/>
<path d="{d}" fill="none" stroke="#21262d" stroke-width="26" stroke-linejoin="round"/>
<path d="{d}" fill="none" stroke="#484f58" stroke-width="1.5" stroke-dasharray="8 10"/>
<rect x="107" y="197" width="26" height="5" fill="#fff"/><rect x="107" y="197" width="26" height="5" fill="none" stroke="#0d1117" stroke-dasharray="3 3"/>
{marks}{smoke}
<g><animateMotion dur="{lap:.1f}s" repeatCount="indefinite" rotate="auto" path="{d}"/>
<g><animateTransform attributeName="transform" type="rotate" values="0;16;0;-16;0" dur="{lap/6:.2f}s" repeatCount="indefinite"/>{car}</g></g>
<g font-size="10" fill="#8b949e"><circle cx="30" cy="292" r="5" fill="#f2c811"/><text x="40" y="296">checkpoint with commits (coin)</text>
<circle cx="230" cy="292" r="2.5" fill="#484f58"/><text x="240" y="296">no activity that day</text>
<text x="770" y="296" text-anchor="end">last 30 days · faster laps with more commits · updated {today}</text></g></svg>""")

# ---------- stats card ----------
repos = u["repositories"]["nodes"]
stars = sum(r["stargazerCount"] for r in repos)
langs = {}
for r in repos:
    for e in r["languages"]["edges"]:
        n = e["node"]
        langs.setdefault(n["name"], [0, n["color"] or "#8b949e"])[0] += e["size"]
tot = sum(v[0] for v in langs.values()) or 1
top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]
rows = [("Public repos", u["publicRepos"]["totalCount"]), ("Followers", u["followers"]["totalCount"]),
        ("Stars earned", stars), ("Contributions (year)", cal["totalContributions"]), ("Commits (year)", cc["totalCommitContributions"]),
        ("Pull requests", cc["totalPullRequestContributions"]), ("Issues", cc["totalIssueContributions"])]
left = "".join(
    f'<text x="30" y="{80+i*28}" fill="#c9d1d9">{k}</text>'
    f'<text x="270" y="{80+i*28}" text-anchor="end" font-weight="700" fill="#2f81f7">{v}</text>'
    for i, (k, v) in enumerate(rows))
x, bar = 360, ""
for n, (s, c) in top:
    w = 410 * s / tot
    bar += f'<rect x="{x:.1f}" y="62" width="{w:.1f}" height="8" fill="{c}"/>'
    x += w
leg = "".join(
    f'<circle cx="{360+(i%2)*210}" cy="{98+(i//2)*26}" r="5" fill="{c}"/>'
    f'<text x="{372+(i%2)*210}" y="{102+(i//2)*26}" fill="#c9d1d9">{html.escape(n)} {s/tot*100:.1f}%</text>'
    for i, (n, (s, c)) in enumerate(top))
with open("assets/github-stats.svg", "w", encoding="utf-8") as f:
    f.write(f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="285" viewBox="0 0 800 285" {FONT} font-size="13">
<rect width="800" height="285" rx="8" fill="#0d1117" stroke="#21262d"/>
<text x="30" y="40" font-size="17" font-weight="600" fill="#2f81f7">{USER}'s GitHub Stats</text>
<text x="360" y="40" font-size="17" font-weight="600" fill="#2f81f7">Most Used Languages</text>
{left}<rect x="360" y="62" width="410" height="8" rx="4" fill="#21262d"/>{bar}{leg}
<text x="770" y="272" text-anchor="end" font-size="10" fill="#6e7681">updated {today}</text></svg>""")
print("ok", rows, cur, longest)
