#!/usr/bin/env python3
"""Steins;Gate-style contribution graph generator.

Usage: contrib_graph.py --style worldlines|nixie|dmail --user yubinex --out-dark a.svg --out-light b.svg
Data: GitHub GraphQL (needs GITHUB_TOKEN) with the public contributions page as fallback,
or --calendar file.json (list of {"x","y","level","date"}).
Only the Python standard library is used.
"""
import argparse, json, math, os, random, re, sys, urllib.request

DIGITS = {"0": ["M651 1360Q495 1360 416.5 1206.5Q338 1053 338 745Q338 438 416.5 284.5Q495 131 651 131Q808 131 886.5 284.5Q965 438 965 745Q965 1053 886.5 1206.5Q808 1360 651 1360ZM651 1520Q902 1520 1034.5 1321.5Q1167 1123 1167 745Q1167 368 1034.5 169.5Q902 -29 651 -29Q400 -29 267.5 169.5Q135 368 135 745Q135 1123 267.5 1321.5Q400 1520 651 1520Z", [135, -29, 1167, 1520]], "1": ["M254 170H584V1309L225 1237V1421L582 1493H784V170H1114V0H254Z", [225, 0, 1114, 1493]], "2": ["M393 170H1098V0H150V170Q265 289 463.5 489.5Q662 690 713 748Q810 857 848.5 932.5Q887 1008 887 1081Q887 1200 803.5 1275.0Q720 1350 586 1350Q491 1350 385.5 1317.0Q280 1284 160 1217V1421Q282 1470 388.0 1495.0Q494 1520 582 1520Q814 1520 952.0 1404.0Q1090 1288 1090 1094Q1090 1002 1055.5 919.5Q1021 837 930 725Q905 696 771.0 557.5Q637 419 393 170Z", [150, 0, 1098, 1520]], "3": ["M831 805Q976 774 1057.5 676.0Q1139 578 1139 434Q1139 213 987.0 92.0Q835 -29 555 -29Q461 -29 361.5 -10.5Q262 8 156 45V240Q240 191 340.0 166.0Q440 141 549 141Q739 141 838.5 216.0Q938 291 938 434Q938 566 845.5 640.5Q753 715 588 715H414V881H596Q745 881 824.0 940.5Q903 1000 903 1112Q903 1227 821.5 1288.5Q740 1350 588 1350Q505 1350 410.0 1332.0Q315 1314 201 1276V1456Q316 1488 416.5 1504.0Q517 1520 606 1520Q836 1520 970.0 1415.5Q1104 1311 1104 1133Q1104 1009 1033.0 923.5Q962 838 831 805Z", [156, -29, 1139, 1520]], "4": ["M774 1317 264 520H774ZM721 1493H975V520H1188V352H975V0H774V352H100V547Z", [100, 0, 1188, 1493]], "5": ["M221 1493H1014V1323H406V957Q450 972 494.0 979.5Q538 987 582 987Q832 987 978.0 850.0Q1124 713 1124 479Q1124 238 974.0 104.5Q824 -29 551 -29Q457 -29 359.5 -13.0Q262 3 158 35V238Q248 189 344.0 165.0Q440 141 547 141Q720 141 821.0 232.0Q922 323 922 479Q922 635 821.0 726.0Q720 817 547 817Q466 817 385.5 799.0Q305 781 221 743Z", [158, -29, 1124, 1493]], "6": ["M676 827Q540 827 460.5 734.0Q381 641 381 479Q381 318 460.5 224.5Q540 131 676 131Q812 131 891.5 224.5Q971 318 971 479Q971 641 891.5 734.0Q812 827 676 827ZM1077 1460V1276Q1001 1312 923.5 1331.0Q846 1350 770 1350Q570 1350 464.5 1215.0Q359 1080 344 807Q403 894 492.0 940.5Q581 987 688 987Q913 987 1043.5 850.5Q1174 714 1174 479Q1174 249 1038.0 110.0Q902 -29 676 -29Q417 -29 280.0 169.5Q143 368 143 745Q143 1099 311.0 1309.5Q479 1520 762 1520Q838 1520 915.5 1505.0Q993 1490 1077 1460Z", [143, -29, 1174, 1520]], "7": ["M168 1493H1128V1407L586 0H375L885 1323H168Z", [168, 0, 1128, 1493]], "8": ["M651 709Q507 709 424.5 632.0Q342 555 342 420Q342 285 424.5 208.0Q507 131 651 131Q795 131 878.0 208.5Q961 286 961 420Q961 555 878.5 632.0Q796 709 651 709ZM449 795Q319 827 246.5 916.0Q174 1005 174 1133Q174 1312 301.5 1416.0Q429 1520 651 1520Q874 1520 1001.0 1416.0Q1128 1312 1128 1133Q1128 1005 1055.5 916.0Q983 827 854 795Q1000 761 1081.5 662.0Q1163 563 1163 420Q1163 203 1030.5 87.0Q898 -29 651 -29Q404 -29 271.5 87.0Q139 203 139 420Q139 563 221.0 662.0Q303 761 449 795ZM375 1114Q375 998 447.5 933.0Q520 868 651 868Q781 868 854.5 933.0Q928 998 928 1114Q928 1230 854.5 1295.0Q781 1360 651 1360Q520 1360 447.5 1295.0Q375 1230 375 1114Z", [139, -29, 1163, 1520]], "9": ["M225 31V215Q301 179 379.0 160.0Q457 141 532 141Q732 141 837.5 275.5Q943 410 958 684Q900 598 811.0 552.0Q722 506 614 506Q390 506 259.5 641.5Q129 777 129 1012Q129 1242 265.0 1381.0Q401 1520 627 1520Q886 1520 1022.5 1321.5Q1159 1123 1159 745Q1159 392 991.5 181.5Q824 -29 541 -29Q465 -29 387.0 -14.0Q309 1 225 31ZM627 664Q763 664 842.5 757.0Q922 850 922 1012Q922 1173 842.5 1266.5Q763 1360 627 1360Q491 1360 411.5 1266.5Q332 1173 332 1012Q332 850 411.5 757.0Q491 664 627 664Z", [129, -29, 1159, 1520]]}  # DejaVu Sans digit outlines (font units, y up)

PAL = {
    "dark": dict(empty="#161b22", dim="#2a2420", lv=["#161b22", "#3b2614", "#6e3f15", "#b8641c", "#ff9d4d"],
                 line="#ffb35c", core="#ffe2bf", glass="#100d0b", glass_s="#342b25", text="#ff9d4d",
                 red="#ff3b30", glow=1.0),
    "light": dict(empty="#ebedf0", dim="#ddd5ce", lv=["#ebedf0", "#fde0bf", "#fbbf7c", "#f08c3c", "#c9600f"],
                  line="#d9731a", core="#fff1df", glass="#f4efea", glass_s="#d9cfc6", text="#c9600f",
                  red="#e5372b", glow=0.45),
}
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


# ---------------------------------------------------------------- data
def fetch_graphql(user, token):
    q = ("query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{"
         "weeks{contributionDays{date weekday contributionLevel}}}}}}")
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": q, "variables": {"login": user}}).encode(),
                                 headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                                          "User-Agent": "contrib-graph"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [dict(x=x, y=d["weekday"], date=d["date"], level=LEVELS[d["contributionLevel"]])
            for x, w in enumerate(weeks) for d in w["contributionDays"]]


def fetch_public(user):
    req = urllib.request.Request(f"https://github.com/users/{user}/contributions",
                                 headers={"User-Agent": "Mozilla/5.0 contrib-graph"})
    html = urllib.request.urlopen(req, timeout=30).read().decode()
    cells = re.findall(r'data-date="([\d-]+)" id="contribution-day-component-(\d+)-(\d+)" data-level="(\d)"', html)
    if not cells:
        raise RuntimeError("could not parse public contributions page")
    return [dict(x=int(w), y=int(wd), date=dt, level=int(lv)) for dt, wd, w, lv in cells]


def load(args):
    if args.calendar:
        return json.load(open(args.calendar))
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        try:
            return fetch_graphql(args.user, token)
        except Exception as e:  # noqa: BLE001
            print(f"GraphQL failed ({e}), falling back to public page", file=sys.stderr)
    return fetch_public(args.user)


# ---------------------------------------------------------------- helpers
P = 16          # cell pitch
C = 12          # cell size
M = 16          # margin
TOP = 30        # room for the corner number


def glow_filter(fid, pal, a=2.0, b=5.0):
    g = pal["glow"]
    return (f'<filter id="{fid}" x="-50%" y="-50%" width="200%" height="200%">'
            f'<feGaussianBlur in="SourceGraphic" stdDeviation="{b*g:.2f}" result="b2"/>'
            f'<feGaussianBlur in="SourceGraphic" stdDeviation="{a*g:.2f}" result="b1"/>'
            '<feMerge><feMergeNode in="b2"/><feMergeNode in="b1"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')


def digit_defs():
    return "".join(f'<path id="g{c}" d="{d}"/>' for c, (d, _) in DIGITS.items())


def number(value, x_right, y_base, h, pal, cls="", extra=""):
    """Right-aligned number drawn with stroked digit outlines (nixie wire look)."""
    s = h / 1493.0
    adv = 0.86 * h
    out, x = [], x_right - adv * len(value.replace(".", "")) - 0.3 * h
    for ch in value:
        if ch == ".":
            out.append(f'<circle cx="{x + 0.12*h:.2f}" cy="{y_base - 0.08*h:.2f}" r="{0.07*h:.2f}" fill="{pal["text"]}"/>')
            x += 0.3 * h
            continue
        d, bb = DIGITS[ch]
        gw = (bb[2] - bb[0]) * s
        tx = x + (adv - gw) / 2 - bb[0] * s
        out.append(f'<use href="#g{ch}" transform="translate({tx:.2f} {y_base:.2f}) scale({s:.5f} {-s:.5f})" '
                   f'fill="none" stroke="{pal["text"]}" stroke-width="{1.1/s:.1f}"/>')
        x += adv
    return f'<g class="{cls}" {extra} filter="url(#gl)">{"".join(out)}</g>'


def svg_open(w, h, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{label}">')


def size(cells, top):
    weeks = max(c["x"] for c in cells) + 1
    return weeks, M * 2 + weeks * P - (P - C), top + 7 * P - (P - C) + M


def cxy(c, top):
    return M + c["x"] * P + C / 2, top + c["y"] * P + C / 2


# ---------------------------------------------------------------- style: world lines
def worldlines(cells, pal):
    weeks, W, H = size(cells, TOP)
    T, D = 14.0, 7.0                      # loop length, draw duration
    act = sorted([c for c in cells if c["level"] > 0], key=lambda c: c["date"])
    mid = 3.0
    raw = []
    for wk in range(weeks):
        days = [c for c in cells if c["x"] == wk and c["level"] > 0]
        if days:
            wsum = sum(c["level"] for c in days)
            raw.append(sum(c["y"] * c["level"] for c in days) / wsum)
        else:
            raw.append(None)
    # inactive weeks drift back toward the middle; then smooth
    ys, prev = [], mid
    for v in raw:
        prev = v if v is not None else prev + (mid - prev) * 0.35
        ys.append(prev)
    ys = [sum(ys[max(0, i-1):i+2]) / len(ys[max(0, i-1):i+2]) for i in range(len(ys))]
    pts = [(M + i * P + C / 2, TOP + y * P + C / 2) for i, y in enumerate(ys)]
    x0, x1 = pts[0][0], pts[-1][0]

    def path(points):  # Catmull-Rom -> cubic bezier
        d = f"M{points[0][0]:.1f} {points[0][1]:.1f}"
        for i in range(len(points) - 1):
            p0 = points[i - 1] if i else points[i]
            p1, p2 = points[i], points[i + 1]
            p3 = points[i + 2] if i + 2 < len(points) else p2
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            d += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
        return d
    rnd = random.Random(48596)
    ghost = [(x, y + rnd.uniform(-9, 9)) for x, y in pts]
    ghost = [(x, sum(g[1] for g in ghost[max(0,i-1):i+2]) / len(ghost[max(0,i-1):i+2])) for i, (x, _) in enumerate(ghost)]
    css = [f".ln{{stroke-dasharray:1;stroke-dashoffset:1;animation:draw {T}s linear infinite}}",
           f"@keyframes draw{{0%{{stroke-dashoffset:1;opacity:1}}{D/T*100:.1f}%{{stroke-dashoffset:0;opacity:1}}"
           f"86%{{stroke-dashoffset:0;opacity:1}}95%{{stroke-dashoffset:0;opacity:0}}100%{{stroke-dashoffset:1;opacity:0}}}}",
           ".hd{animation:hd %ss linear infinite}" % T]
    out = [svg_open(W, H, "Contribution world line"), "<defs>", glow_filter("gl", pal), digit_defs(), "</defs>"]
    # all days as faint dots
    out.append('<g>')
    for c in cells:
        x, y = cxy(c, TOP)
        if c["level"]:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{1.6+0.5*c["level"]:.1f}" fill="{pal["lv"][c["level"]]}" opacity=".45"/>')
        else:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.3" fill="{pal["dim"]}"/>')
    out.append('</g>')
    out.append(f'<path d="{path(ghost)}" fill="none" stroke="{pal["line"]}" stroke-width=".7" opacity=".16"/>')
    out.append(f'<g filter="url(#gl)">')
    out.append(f'<path class="ln" pathLength="1" d="{path(pts)}" fill="none" stroke="{pal["line"]}" stroke-width="1.3" stroke-linecap="round"/>')
    for i, c in enumerate(act):
        x, y = cxy(c, TOP)
        on = (x - x0) / (x1 - x0) * D / T * 100
        k = f"k{i}"
        css.append(f"@keyframes {k}{{0%,{max(on-0.01,0):.2f}%{{opacity:0}}{on:.2f}%{{opacity:1}}"
                   f"{min(on+1.2,85):.2f}%{{opacity:.75}}86%{{opacity:.75}}95%,100%{{opacity:0}}}}"
                   f".{k}{{animation:{k} {T}s linear infinite}}")
        r = 2.2 + 0.7 * c["level"]
        out.append(f'<g class="{k}" opacity="0"><circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{pal["lv"][4]}"/>'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r*0.45:.1f}" fill="{pal["core"]}"/></g>')
    out.append('</g>')
    # corner number: rolls on load, settles
    rnd2 = random.Random(7)
    vals = ["%.6f" % rnd2.uniform(0, 1.2) for _ in range(9)] + ["1.048596"]
    for i, v in enumerate(vals):
        last = i == len(vals) - 1
        anim = (f'<set attributeName="opacity" to="1" begin="{0.2+i*0.09:.2f}s" fill="freeze"/>' if last else
                f'<set attributeName="opacity" to="1" begin="{0.2+i*0.09:.2f}s" dur="0.09s"/>')
        out.append(number(v, W - M, TOP - 12, 12, pal, extra='opacity="0"').replace("</g>", anim + "</g>", 1)
                   if False else _wrap(number(v, W - M, TOP - 12, 12, pal), anim))
    out.insert(3, "<style>" + "".join(css) + "</style>")
    out.append("</svg>")
    return "\n".join(out)


def _wrap(inner, anim):
    return f'<g opacity="0">{inner}{anim}</g>'


# ---------------------------------------------------------------- style: nixie cells
def nixie(cells, pal):
    weeks, W, H = size(cells, M)
    rnd = random.Random(1048596)
    css = [".on{opacity:0;animation:on .55s linear both}",
           "@keyframes on{0%{opacity:0}18%{opacity:.85}28%{opacity:.1}45%{opacity:1}58%{opacity:.35}72%,100%{opacity:1}}",
           "@keyframes fl{0%,90%,100%{opacity:1}92%{opacity:.45}93.5%{opacity:1}95%{opacity:.65}96%{opacity:1}}",
           ".gw{opacity:0;animation:gw 1.2s ease-out both}@keyframes gw{to{opacity:1}}"]
    out = [svg_open(W, H, "Contribution graph as nixie cells"), "<defs>", glow_filter("gl", pal, 1.6, 4.2),
           f'<linearGradient id="gls" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{pal["glass"]}" stop-opacity=".6"/>'
           f'<stop offset="1" stop-color="{pal["glass"]}"/></linearGradient>', "</defs>"]
    out.append("<g>")
    for c in cells:
        x, y = M + c["x"] * P, M + c["y"] * P
        out.append(f'<rect x="{x}" y="{y}" width="{C}" height="{C}" rx="3" fill="url(#gls)" stroke="{pal["glass_s"]}" stroke-width=".8"/>')
    out.append("</g>")
    # warm haze per active cell (no filter, cheap)
    lit = []
    for c in cells:
        if not c["level"]:
            continue
        x, y = M + c["x"] * P, M + c["y"] * P
        delay = 0.25 + c["x"] * 0.045 + c["y"] * 0.012
        style = f"animation-delay:{delay:.3f}s"
        if rnd.random() < 0.18:
            style = (f"animation:on .55s linear {delay:.3f}s both,fl {rnd.uniform(5,9):.1f}s linear "
                     f"{delay+1+rnd.uniform(0,4):.2f}s infinite")
        lv = c["level"]
        s = 4.2 + lv * 1.25          # filament size grows with level
        o = 0.45 + lv * 0.14
        lit.append(f'<g class="on" style="{style}"><rect x="{x+(C-s)/2-1:.2f}" y="{y+(C-s)/2-1:.2f}" width="{s+2:.2f}" height="{s+2:.2f}" rx="2" '
                   f'fill="{pal["lv"][max(lv,2)]}" opacity="{o*0.6:.2f}"/>'
                   f'<rect x="{x+(C-s)/2:.2f}" y="{y+(C-s)/2:.2f}" width="{s:.2f}" height="{s:.2f}" rx="1.4" fill="{pal["lv"][4]}" opacity="{o:.2f}"/>'
                   + (f'<rect x="{x+C/2-0.9:.2f}" y="{y+C/2-0.9:.2f}" width="1.8" height="1.8" rx=".9" fill="{pal["core"]}"/>' if lv >= 3 else "")
                   + "</g>")
    out.append('<g filter="url(#gl)">' + "".join(lit) + "</g>")
    out.insert(3, "<style>" + "".join(css) + "</style>")
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- style: d-mail glitch
def dmail(cells, pal):
    weeks, W, H = size(cells, TOP)
    T = 11.0
    rnd = random.Random(571024)
    # alternate world line: same activity, displaced
    taken, alt = set(), {}
    for c in sorted(cells, key=lambda c: c["date"]):
        if not c["level"]:
            continue
        for _ in range(6):
            nx = min(weeks - 1, max(0, c["x"] + rnd.choice([-2, -1, 0, 1, 1, 2])))
            ny = min(6, max(0, c["y"] + rnd.choice([-1, 0, 1])))
            if (nx, ny) not in taken:
                break
        taken.add((nx, ny))
        alt[(nx, ny)] = max(1, min(4, c["level"] + rnd.choice([-1, 0, 0, 1])))
    def grid(gid, levels, only_active=False):
        g = [f'<g id="{gid}">']
        for c in cells:
            lv = levels.get((c["x"], c["y"]), 0)
            if only_active and not lv:
                continue
            x, y = M + c["x"] * P, TOP + c["y"] * P
            g.append(f'<rect x="{x}" y="{y}" width="{C}" height="{C}" rx="2.5" fill="{pal["lv"][lv]}"/>')
        g.append("</g>")
        return "".join(g)
    real = {(c["x"], c["y"]): c["level"] for c in cells}
    # timeline (percent of T)
    g1a, g1b, g2a, g2b = 46, 53, 84, 91
    css = [
        f"@keyframes vr{{0%,{g1a-0.1}%{{opacity:1}}{g1a}%,{g2b-0.1}%{{opacity:0}}{g2b}%,100%{{opacity:1}}}}",
        f"@keyframes va{{0%,{g1b-0.1}%{{opacity:0}}{g1b}%,{g2a-0.1}%{{opacity:1}}{g2a}%,100%{{opacity:0}}}}",
        f".vr{{animation:vr {T}s steps(1,end) infinite}}.va{{opacity:0;animation:va {T}s steps(1,end) infinite}}",
    ]
    out = [svg_open(W, H, "Contribution graph, world line shift"), "<defs>", glow_filter("gl", pal, 1.2, 3.0), digit_defs(),
           grid("gr", real), grid("ga", alt), grid("grx", real, True), grid("gax", alt, True)]
    nb = 7
    bh = (7 * P) / nb
    for i in range(nb):
        out.append(f'<clipPath id="b{i}"><rect x="0" y="{TOP + i*bh - 1:.1f}" width="{W}" height="{bh + 1:.1f}"/></clipPath>')
    out.append(f'<filter id="red"><feFlood flood-color="{pal["red"]}"/><feComposite in2="SourceAlpha" operator="in"/></filter>')
    out.append("</defs>")
    out.append('<use href="#gr" class="vr"/><use href="#ga" class="va"/>')

    # glitch windows: slices of the outgoing grid first, then the incoming one
    def glitch(src, a, b, name):
        parts = []
        frames = 7
        for i in range(nb):
            kf = [f"0%,{a-0.01:.2f}%{{opacity:0;transform:translateX(0)}}"]
            for f in range(frames):
                t = a + (b - a) * f / frames
                dx = rnd.choice([0, 0, -1, 1]) * rnd.uniform(4, 26)
                kf.append(f"{t:.2f}%{{opacity:1;transform:translateX({dx:.1f}px)}}")
            kf.append(f"{b:.2f}%,100%{{opacity:0;transform:translateX(0)}}")
            k = f"{name}{i}"
            css.append(f"@keyframes {k}{{{''.join(kf)}}}.{k}{{opacity:0;animation:{k} {T}s steps(1,end) infinite}}")
            parts.append(f'<g clip-path="url(#b{i})"><use href="#{src}" class="{k}"/></g>')
        # red split copy
        k = f"{name}r"
        css.append(f"@keyframes {k}{{0%,{a-0.01:.2f}%{{opacity:0}}{a:.2f}%{{opacity:.5;transform:translate(3px,-1px)}}"
                   f"{(a+b)/2:.2f}%{{opacity:.3;transform:translate(-4px,1px)}}{b:.2f}%,100%{{opacity:0}}}}"
                   f".{k}{{opacity:0;animation:{k} {T}s steps(1,end) infinite}}")
        parts.append(f'<use href="#{src}x" class="{k}" filter="url(#red)"/>')
        return parts
    mid1, mid2 = (g1a + g1b) / 2, (g2a + g2b) / 2
    out += glitch("gr", g1a, mid1, "x") + glitch("ga", mid1, g1b, "y") + glitch("ga", g2a, mid2, "z") + glitch("gr", mid2, g2b, "w")
    # scan line flash
    for n, (a, b) in enumerate([(g1a, g1b), (g2a, g2b)]):
        k = f"sc{n}"
        css.append(f"@keyframes {k}{{0%,{a:.2f}%{{opacity:0;transform:translateY(0)}}{a+0.1:.2f}%{{opacity:.8}}"
                   f"{b:.2f}%{{opacity:0;transform:translateY({7*P}px)}}100%{{opacity:0}}}}"
                   f".{k}{{opacity:0;animation:{k} {T}s linear infinite}}")
        out.append(f'<rect class="{k}" x="{M}" y="{TOP-2}" width="{W-2*M}" height="1.2" fill="{pal["line"]}" filter="url(#gl)"/>')
    # divergence numbers
    css.append(f".nr{{animation:vr {T}s steps(1,end) infinite}}.na{{opacity:0;animation:va {T}s steps(1,end) infinite}}")
    css.append(f"@keyframes nf{{0%,{g1a}%{{opacity:0}}{g1a+1}%{{opacity:1}}{g1a+2.5}%{{opacity:0}}{g1a+4}%{{opacity:1}}{g1b}%,{g2a}%{{opacity:0}}"
               f"{g2a+1}%{{opacity:1}}{g2a+2.5}%{{opacity:0}}{g2a+4}%{{opacity:1}}{g2b}%,100%{{opacity:0}}}}.nf{{opacity:0;animation:nf {T}s steps(1,end) infinite}}")
    out.append(number("1.048596", W - M, TOP - 12, 12, pal, cls="nr"))
    out.append(number("0.571024", W - M, TOP - 12, 12, pal, cls="na"))
    out.append(number("0.000000", W - M, TOP - 12, 12, pal, cls="nf"))
    out.insert(3, "<style>" + "".join(css) + "</style>")
    out.append("</svg>")
    return "\n".join(out)


STYLES = {"worldlines": worldlines, "nixie": nixie, "dmail": dmail}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", choices=STYLES, required=True)
    ap.add_argument("--user", default="yubinex")
    ap.add_argument("--calendar")
    ap.add_argument("--out-dark", required=True)
    ap.add_argument("--out-light", required=True)
    a = ap.parse_args()
    cells = load(a)
    print(f"{len(cells)} days, {sum(1 for c in cells if c['level'])} active", file=sys.stderr)
    for theme, path in (("dark", a.out_dark), ("light", a.out_light)):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        open(path, "w").write(STYLES[a.style](cells, PAL[theme]))
        print(f"wrote {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
