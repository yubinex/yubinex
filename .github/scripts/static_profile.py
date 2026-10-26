"""One static lab dossier. Refresh public data at build time, never in the browser."""
import argparse
from collections import Counter, defaultdict
import datetime as dt
from html import escape
import json
import os
from pathlib import Path
import textwrap
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".github/profile-data.json"
TOOLS = ("Git", "GitHub", "Linux")
PALETTES = {
    "dark": ("#101312", "#191d19", "#ece6d5", "#b5b6a3", "#3c4437", "#ffb35c"),
    "light": ("#f4efdf", "#eae3cf", "#292e24", "#626650", "#c3bca5", "#944309"),
}
NAV = (
    ("site", "ENTER THE LAB", "PERSONAL WEBSITE", "https://yubinex.github.io/yubinex-web/"),
    ("repos", "EXPERIMENT INDEX", "PUBLIC REPOSITORIES", "https://github.com/yubinex?tab=repositories"),
    ("activity", "OBSERVATION LOG", "GITHUB ACTIVITY", "https://github.com/yubinex?tab=overview"),
)


def language_inventory(repos):
    counts = Counter(r["language"] for r in repos
                     if r.get("private") is False and not r.get("fork") and r.get("language"))
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:6]


def collect():
    from sg_data import API, _get, calendar, streaks
    user = "yubinex"
    token = os.environ.get("GITHUB_TOKEN")
    profile = json.loads(_get(f"{API}/users/{user}", token))
    repos = json.loads(_get(f"{API}/users/{user}/repos?per_page=100&type=owner&sort=pushed", token))
    own = [r for r in repos if r.get("private") is False and not r.get("fork")]
    cells = calendar(user, token)
    if not cells:
        raise RuntimeError("Empty contribution calendar; keeping the last good snapshot")
    longest, current = streaks(cells)
    projects = [dict(name=r["name"], description=r.get("description") or "Public experiment.",
                     language=r.get("language") or "Source", stars=r.get("stargazers_count", 0))
                for r in own if r["name"] not in (user, "profile-readme-test")][:3]
    return dict(user=user, created=profile["created_at"][:7].replace("-", " / "),
                public_repos=profile["public_repos"], followers=profile["followers"],
                stars=sum(r.get("stargazers_count", 0) for r in own),
                cells=cells, total=sum(c["count"] for c in cells),
                active_days=sum(c["count"] > 0 for c in cells),
                longest_streak=longest, current_streak=current, projects=projects,
                languages=language_inventory(own),
                generated=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))


def short(value, limit):
    return value if len(value) <= limit else value[:limit - 1].rstrip() + "…"


def contribution_worldlines(cells):
    grouped = defaultdict(list)
    for cell in cells:
        grouped[cell["x"]].append(cell)
    weeks = [dict(week=week, count=sum(c["count"] for c in days),
                  date=min(c["date"] for c in days))
             for week, days in sorted(grouped.items())]
    maximum = max((w["count"] for w in weeks), default=0)
    scale = max(20, ((maximum + 19) // 20) * 20)
    months = defaultdict(list)
    for i, week in enumerate(weeks):
        week["x"] = 92 + (i + .5) * 730 / max(1, len(weeks))
        week["month"] = week["date"][:7]
        months[week["month"]].append(week)
    for month in months.values():
        root = sum(w["x"] for w in month) / len(month)
        for week in month:
            x = week["x"]
            rise = week["count"] / scale * 110
            week.update(root=root, y=833 - rise)
            week["path"] = (f'M{root:.2f} 833C{root:.2f} {833-rise*.45:.2f} '
                            f'{x:.2f} {833-rise*.75:.2f} {x:.2f} {833-rise:.2f}')
    return weeks, months, maximum, scale


def render(theme, data=None):
    d = data if data is not None else json.loads(DATA.read_text())
    bg, panel, ink, muted, rule, amber = PALETTES[theme]
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="880" height="1650" viewBox="0 0 880 1650" role="img" aria-labelledby="title desc">',
        '<title id="title">Future Gadget Laboratory / yubinex personnel dossier</title>',
        '<desc id="desc">One static lab file: member information, real weekly GitHub contributions drawn as world-line branches, public experiments and a language and tools inventory. A text version follows in the README.</desc>',
        f'<rect width="880" height="1650" rx="8" fill="{bg}"/>',
        f'<rect x="10" y="10" width="860" height="1630" rx="4" fill="none" stroke="{rule}"/>',
    ]

    def text(x, y, value, size=17, color=ink, extra=""):
        out.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="monospace" font-size="{size}" {extra}>{escape(str(value))}</text>')

    def path(value, color=rule, width=1, extra=""):
        out.append(f'<path d="{value}" fill="none" stroke="{color}" stroke-width="{width}" {extra}/>')

    def rect(x, y, w, h, color=panel, extra=""):
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" {extra}/>')

    def section(y, number, title, note):
        rect(36, y - 23, 34, 30, amber)
        text(53, y - 2, number, 16, bg, 'text-anchor="middle" font-weight="700"')
        text(84, y, title, 18, amber, 'letter-spacing="1"')
        path(f"M36 {y + 18}H844")
        text(36, y + 46, note, 15, muted)

    # Printed dossier furniture: static registration marks and a case-file rail.
    for x, sign in ((22, 1), (858, -1)):
        for y, v in ((22, 1), (1628, -1)):
            path(f"M{x} {y + v * 12}V{y}H{x + sign * 12}", amber)
    text(36, 48, "FUTURE GADGET LABORATORY", 18, amber, 'letter-spacing="2"')
    text(844, 47, "FILE / YBX-001", 14, muted, 'text-anchor="end"')
    path("M36 66H844")
    text(36, 99, "PERSONNEL DOSSIER", 15, muted, 'letter-spacing="3"')
    text(36, 159, "yubinex", 58, ink, 'font-weight="700"')
    text(38, 196, "Hi. Welcome to the lab.", 19)
    text(38, 230, "STATUS / observing", 15, amber)
    text(38, 258, "WORLD LINE / stable", 15, muted)

    rect(464, 88, 380, 182, panel, f'rx="6" stroke="{rule}"')
    text(484, 116, "DIVERGENCE METER", 14, muted, 'letter-spacing="1"')
    for i, digit in enumerate("1048596"):
        x = 484 + i * 49
        rect(x, 131, 42, 88, bg, f'rx="17" stroke="{rule}"')
        # Solid, offset letter strokes suggest warm cathodes without SVG blur.
        text(x + 21, 189, digit, 43, amber, 'text-anchor="middle" stroke-width="3" stroke="' + amber + '" opacity=".12"')
        text(x + 21, 189, digit, 43, amber, 'text-anchor="middle"')
        path(f"M{x + 11} 207H{x + 31}", muted)
    out.append(f'<circle cx="529" cy="198" r="2" fill="{amber}"/>')
    text(484, 248, "1.048596 / STEINS GATE", 14, amber)
    path("M36 292H844")
    text(36, 318, "$ ./labmem --observe yubinex", 16, muted)
    text(844, 318, "ACCESS GRANTED", 14, amber, 'text-anchor="end"')

    section(368, "01", "LAB MEMBER FILE", "Public signals. One observer behind the experiments.")
    for x, value, label in ((36, d["public_repos"], "PUBLIC REPOS"), (246, d["stars"], "REPO STARS"),
                            (456, d["followers"], "FOLLOWERS"), (666, d["total"], "CONTRIBUTIONS")):
        text(x, 466, value, 36, ink)
        text(x, 494, label, 14, muted)
    text(36, 534, f'MEMBER SINCE / {d["created"]}', 16)
    text(456, 534, f'STREAK / {d["longest_streak"]}d best · {d["current_streak"]}d now', 16)

    section(594, "02", "WORLD LINE OBSERVATION", "Your contribution history / weekly branches, monthly convergence")
    weeks, months, maximum, scale = contribution_worldlines(d["cells"])
    out.append('<g id="worldline-map" stroke-linecap="round" stroke-linejoin="round">')
    out.append(f'<defs><linearGradient id="field-wash" x1="0" y1="1" x2="0" y2="0"><stop stop-color="{amber}" stop-opacity=".08"/><stop offset="1" stop-color="{amber}" stop-opacity="0"/></linearGradient></defs>')
    rect(36, 660, 808, 220, bg, f'rx="5" stroke="{rule}"')
    rect(37, 661, 806, 218, "url(#field-wash)", 'rx="4"')
    text(58, 688, "CONTRIBUTIONS / WEEK", 13, muted, 'letter-spacing="1"')
    if d["cells"]:
        dates = sorted(c["date"] for c in d["cells"])
        period = " — ".join(dt.date.fromisoformat(date).strftime("%b %Y").upper()
                            for date in (dates[0], dates[-1]))
        text(822, 688, period, 13, muted, 'text-anchor="end"')
    for count in (0, scale // 2, scale):
        y = 833 - count / scale * 110
        path(f"M84 {y}H822", rule, .8, 'stroke-dasharray="2 6"')
        text(72, y + 4, count, 12, muted, 'text-anchor="end"')
    path("M92 833H822", muted, .8, 'opacity=".45"')
    # Real weeks fan out from the convergence point for their starting month.
    active = [w for w in weeks if w["count"]]
    if active:
        path(" ".join(w["path"] for w in active), amber, 1.1,
             'id="worldline-branches" opacity=".65"')
    for i, (month, members) in enumerate(months.items()):
        root = members[0]["root"]
        out.append(f'<circle cx="{root:.2f}" cy="833" r="2.5" fill="{bg}" stroke="{muted}" stroke-width=".8"/>')
        # Avoid squeezing a label into the first partial month.
        if i > 0 or len(months) <= 3:
            label = dt.date.fromisoformat(month + "-01").strftime("%b").upper()
            text(root, 860, label, 12, muted, 'text-anchor="middle"')
    tips = []
    for week in weeks:
        x, y = week["x"], week["y"]
        if week["count"]:
            tips.append(f'M{x+1.8:.2f} {y:.2f}a1.8 1.8 0 1 0 -3.6 0a1.8 1.8 0 1 0 3.6 0')
    if tips:
        path(" ".join(tips), amber, .8, 'id="weekly-endpoints"')
    if maximum:
        peak = next(w for w in weeks if w["count"] == maximum)
        path(peak["path"], amber, 7, 'opacity=".06"')
        path(peak["path"], amber, 1.9, 'id="peak-week"')
        out.append(f'<circle cx="{peak["x"]:.2f}" cy="{peak["y"]:.2f}" r="4" fill="{bg}" stroke="{amber}" stroke-width="1.2"/>')
        text(min(peak["x"] + 10, 798), peak["y"] - 8, maximum, 12, amber)
    if not weeks:
        text(457, 783, "NO CONTRIBUTION DATA", 16, muted, 'text-anchor="middle"')
    out.append("</g>")
    text(36, 911, f'ACTIVITY / {d["total"]} contributions · {d["active_days"]} active days', 17)
    text(36, 939, f'Each branch = one week · height = contributions · peak {maximum}/week', 15, muted)

    out.append('<g transform="translate(0 80)">')
    section(909, "03", "CURRENT EXPERIMENTS", "Most recently pushed public projects. Lab notebooks, not finished answers.")
    for i, repo in enumerate(d["projects"][:3]):
        y = 998 + i * 88
        text(36, y, short(repo["name"], 42), 20, ink, 'font-weight="700"')
        text(844, y, short(repo["language"], 16), 14, amber, 'text-anchor="end"')
        lines = textwrap.wrap(repo["description"], width=78)
        for j, line in enumerate(lines[:2]):
            if j == 1 and len(lines) > 2:
                line = short(line + " …", 78)
            text(36, y + 27 + j * 21, line, 16, muted)
    if not d["projects"]:
        text(36, 998, "No public projects in this snapshot.", 18)

    section(1300, "04", "LAB EQUIPMENT", "Language inventory / primary language of public, non-fork repositories")
    for i, (language, count) in enumerate(d["languages"][:6]):
        x, y = 36 + (i % 2) * 420, 1380 + (i // 2) * 30
        text(x, y, ">", 17, amber)
        text(x + 24, y, short(language, 20), 17)
        text(x + 380, y, f'{count} repo' + ('s' if count != 1 else ''), 14, muted, 'text-anchor="end"')
    if not d["languages"]:
        text(36, 1380, "No language metadata in this snapshot.", 17, muted)
    text(36, 1480, "TOOLS /", 15, amber)
    text(156, 1480, " · ".join(TOOLS), 17)
    path("M36 1510H844")
    text(36, 1538, f'SYNC / {d["generated"]}', 13, muted)
    text(844, 1538, "El Psy Kongroo.", 16, amber, 'text-anchor="end"')
    out.append("</g></svg>")
    return "\n".join(out) + "\n"


def render_nav(theme, key):
    bg, _, ink, muted, rule, amber = PALETTES[theme]
    index, item = next((i, item) for i, item in enumerate(NAV, 1) if item[0] == key)
    _, title, subtitle, _ = item
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="270" height="68" viewBox="0 0 270 68" role="img" aria-labelledby="title">
<title id="title">{escape(title)} / {escape(subtitle)}</title>
<rect x=".5" y=".5" width="269" height="67" rx="4" fill="{bg}" stroke="{rule}"/>
<path d="M1 16V1H16" fill="none" stroke="{amber}"/>
<text x="16" y="23" fill="{muted}" font-family="monospace" font-size="10" letter-spacing="1">0{index} / {escape(subtitle)}</text>
<text x="16" y="48" fill="{ink}" font-family="monospace" font-size="14" letter-spacing=".5">{escape(title)}</text>
<path d="M239 43H251M245 37L251 43L245 49" fill="none" stroke="{amber}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
'''


def render_readme(d):
    _, months, maximum, _ = contribution_worldlines(d["cells"])
    month_lines = "\n".join(f'| `{month}` | `{sum(w["count"] for w in members)}` |'
                            for month, members in months.items())
    project_lines = "\n".join(
        f'- [`{r["name"]}`](https://github.com/yubinex/{quote(r["name"])}) — {escape(r["description"])}'
        for r in d["projects"])
    language_lines = "\n".join(f'{language:<22} {count:>3} public repos'
                               for language, count in d["languages"]) or "No language metadata in this snapshot."
    navigation = "\n".join(f'''  <a href="{escape(url, quote=True)}">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="./assets/lab-nav-{key}-dark.svg" />
      <source media="(prefers-color-scheme: light)" srcset="./assets/lab-nav-{key}-light.svg" />
      <img src="./assets/lab-nav-{key}-light.svg" width="270" height="68" alt="{title} — {subtitle}" />
    </picture>
  </a>''' for key, title, subtitle, url in NAV)
    return f'''<!-- Generated by .github/scripts/static_profile.py from .github/profile-data.json. -->
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/lab-dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset="./assets/lab-light.svg" />
    <img src="./assets/lab-light.svg" width="880" alt="yubinex — Future Gadget Laboratory personnel dossier. Member file, data-driven contribution world lines, current experiments and lab equipment. Expand the text version below for all content and project links." />
  </picture>
</p>

<p align="center">
{navigation}
</p>

<details>
<summary><samp>[ FILE / TEXT MODE ] — open lab record &amp; project links</samp></summary>

## `FUTURE GADGET LABORATORY // TEXT ARCHIVE`

```text
OPERATOR      yubinex
STATUS        observing
WORLD LINE    stable
DIVERGENCE    1.048596 / decorative meter
```

### `01 / LAB MEMBER FILE`

```text
MEMBER SINCE  {d["created"]}
PUBLIC REPOS  {d["public_repos"]}
REPO STARS    {d["stars"]} / public, non-fork repositories
FOLLOWERS     {d["followers"]}
```

### `02 / WORLD LINE OBSERVATION`

```text
CONTRIBUTIONS {d["total"]} / calendar snapshot
ACTIVE DAYS   {d["active_days"]}
BEST STREAK   {d["longest_streak"]} days
NOW           {d["current_streak"]} days
PEAK WEEK     {maximum} contributions
```
Read left to right. Each branch is one week of real GitHub contributions, and its
endpoint height follows the numbered contribution scale. Weeks converge into
monthly bundles, grouped by the first date in each calendar week. Zero-contribution
weeks have zero height. The brightest branch marks a peak week: **{maximum} contributions**.
These are GitHub contribution-calendar counts, not commit-only counts: contributions
can also include pull requests, issues, and other GitHub activity.

| `MONTH / WEEK START` | `CONTRIBUTIONS` |
| :--- | ---: |
{month_lines}

### `03 / CURRENT EXPERIMENTS`

Most recently pushed public, non-fork projects (excluding profile repositories):

{project_lines}

### `04 / LAB EQUIPMENT`

Top languages by number of public, non-fork repositories using each as their primary language. This is an inventory, not a proficiency ranking or a code-volume breakdown.

```text
LANGUAGE INVENTORY
{language_lines}

TOOLS / ENVIRONMENT
{" · ".join(TOOLS)}
```

<samp>SYNC / {d["generated"]}</samp>

<samp>END OF RECORD / El Psy Kongroo.</samp>

</details>
'''


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch a fresh public GitHub snapshot")
    args = parser.parse_args()
    data = collect() if args.refresh else json.loads(DATA.read_text())
    if args.refresh:
        DATA.write_text(json.dumps(data, indent=2) + "\n")
    for theme in ("dark", "light"):
        (ROOT / "assets" / f"lab-{theme}.svg").write_text(render(theme, data))
        for key, *_ in NAV:
            (ROOT / "assets" / f"lab-nav-{key}-{theme}.svg").write_text(render_nav(theme, key))
    (ROOT / "README.md").write_text(render_readme(data))
