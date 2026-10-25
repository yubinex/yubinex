#!/usr/bin/env python3
"""Steins;Gate-themed profile panels built from public GitHub data.

Usage: sg_graph.py --style worldlines|labfile|phonewave|steiner --user yubinex
                   --out-dark a.svg --out-light b.svg [--data cached.json]
Standard library only. Shares glyphs/palette with contrib_graph.py (same folder).
"""
import argparse, json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contrib_graph  # noqa: E402
from contrib_graph import PAL, DIGITS, glow_filter, digit_defs, number, svg_open  # noqa: E402
import sg_data  # noqa: E402
from raster_svg import png_data  # noqa: E402

MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono','Liberation Mono',monospace"
EXTRA = {
    "dark": dict(panel="#0b0a09", panel_s="#2a2420", dimtext="#8a7a6a", faint="#3a302a", grid="#1f1a17", hi="#ffd59a"),
    "light": dict(panel="#fbf8f4", panel_s="#e2d8ce", dimtext="#8a6f58", faint="#e6d9cc", grid="#efe6dc", hi="#a84a0a"),
}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, fill, size=11, anchor="start", weight="normal", extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-family="{MONO}" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{weight}" {extra}>{esc(s)}</text>')


def roll(value, x_right, y_base, h, pal, start=0.2, steps=9, seed=1):
    """Divergence-meter style number: random values flash, then the real one stays."""
    r = random.Random(seed)
    n_int = len(value.split(".")[0])
    out = []
    for i in range(steps + 1):
        last = i == steps
        v = value if last else ("%0*.6f" % (n_int + 7, r.uniform(0, 10 ** n_int - 0.01)))
        anim = (f'<set attributeName="opacity" to="1" begin="{start+i*0.08:.2f}s" fill="freeze"/>' if last else
                f'<set attributeName="opacity" to="1" begin="{start+i*0.08:.2f}s" dur="0.08s"/>')
        out.append(f'<g opacity="0">{number(v, x_right, y_base, h, pal)}{anim}</g>')
    return "".join(out)


def frame(W, H, pal, ex, title, right=""):
    return (f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="10" fill="{ex["panel"]}" stroke="{ex["panel_s"]}"/>'
            + text(18, 22, title, ex["dimtext"], 10, extra='letter-spacing="2"')
            + (text(W - 18, 22, right, ex["dimtext"], 10, "end", extra='letter-spacing="1"') if right else ""))


# ------------------------------------------------------------------ 1. attractor field / world lines
def worldlines(d, theme):
    pal, ex = PAL[theme], EXTRA[theme]
    W, H = 880, 270
    cells = d["cells"]
    weeks = max(c["x"] for c in cells) + 1
    wk = [0] * weeks
    for c in cells:
        wk[c["x"]] += c["count"]
    x0, x1, y0 = 40, W - 40, 196
    step = (x1 - x0) / (weeks - 1)
    X = lambda i: x0 + i * step  # noqa: E731
    D = 6.0  # main line draw time
    T = lambda x: 0.6 + (x - x0) / (x1 - x0) * D  # noqa: E731
    mx = max(wk) or 1
    css = [".dr{stroke-dasharray:1;stroke-dashoffset:1;animation:dr 1s ease-out forwards}",
           "@keyframes dr{to{stroke-dashoffset:0}}",
           ".pop{opacity:0;animation:pop .5s ease-out forwards}@keyframes pop{0%{opacity:0}40%{opacity:1}60%{opacity:.4}100%{opacity:1}}",
           ".fl{animation:fl 6s infinite}@keyframes fl{0%,92%,100%{opacity:1}94%{opacity:.5}96%{opacity:1}}"]
    o = [svg_open(W, H, "World line attractor field built from contributions"), "<defs>", glow_filter("gl", pal, 1.4, 3.6),
         digit_defs(), "</defs>"]
    o.append(frame(W, H, pal, ex, "ATTRACTOR FIELD  //  WORLD LINE OBSERVATION"))
    # attractor field guide lines
    for k, yy in enumerate((y0 - 105, y0 - 70, y0 - 35)):
        o.append(f'<line x1="{x0}" y1="{yy}" x2="{x1}" y2="{yy}" stroke="{ex["grid"]}" stroke-width="1" stroke-dasharray="2 6"/>')
    o.append(f'<line x1="{x0}" y1="{y0+30}" x2="{x1}" y2="{y0+30}" stroke="{ex["grid"]}" stroke-width="1"/>')
    for lab, yy in (("β", y0 - 105), ("α", y0)):
        o.append(text(x0 - 16, yy + 4, lab, ex["dimtext"], 11, "middle"))
    # month ticks
    months = {}
    for c in cells:
        m = c["date"][:7]
        months.setdefault(m, c["x"])
    names = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
    for m, xw in sorted(months.items())[1:]:
        xx = X(xw)
        o.append(f'<line x1="{xx:.1f}" y1="{y0+26}" x2="{xx:.1f}" y2="{y0+34}" stroke="{ex["faint"]}"/>')
        o.append(text(xx + 3, y0 + 46, names[int(m[5:]) - 1], ex["dimtext"], 9))
    # branches: every active week splits off the main line and converges back
    top = sorted(range(weeks), key=lambda i: -wk[i])[:4]
    g = ['<g filter="url(#gl)">']
    for i, v in enumerate(wk):
        if not v:
            continue
        h = 12 + (v / mx) ** 0.6 * 104
        xs = min(X(i), x1 - step * 3.2)
        xe = xs + step * 3.2
        xp = xs + step * 1.1
        lw = 0.8 + (v / mx) * 1.4
        dly = T(xs)
        path = f"M{xs:.1f} {y0} C{xs+step*0.5:.1f} {y0} {xp-step*0.4:.1f} {y0-h:.1f} {xp:.1f} {y0-h:.1f} S{xe-step*0.6:.1f} {y0} {xe:.1f} {y0}"
        g.append(f'<path class="dr" pathLength="1" style="animation-delay:{dly:.2f}s;animation-duration:{0.6+h/120:.2f}s" d="{path}" fill="none" '
                 f'stroke="{pal["lv"][3] if v < mx*0.5 else pal["line"]}" stroke-width="{lw:.2f}" stroke-linecap="round" opacity="{0.55+0.45*v/mx:.2f}"/>')
        r = 1.6 + (v / mx) * 2.6
        g.append(f'<g class="pop" style="animation-delay:{dly+0.35:.2f}s"><circle cx="{xp:.1f}" cy="{y0-h:.1f}" r="{r:.1f}" fill="{pal["lv"][4]}"/>'
                 f'<circle cx="{xp:.1f}" cy="{y0-h:.1f}" r="{r*0.45:.1f}" fill="{pal["core"]}"/></g>')
        # commit-heavy days split again off the branch peak
        heavy = sorted([c for c in cells if c["x"] == i and c["count"] >= 8], key=lambda c: -c["count"])[:2]
        for j, c in enumerate(heavy):
            hx, hy = xp + step * (0.9 + j * 0.5), y0 - h - 10 - (c["count"] ** 0.5) * 3
            sp = f"M{xp:.1f} {y0-h:.1f} Q{xp+step*0.3:.1f} {y0-h-2:.1f} {hx:.1f} {hy:.1f}"
            g.append(f'<path class="dr" pathLength="1" style="animation-delay:{dly+0.5:.2f}s;animation-duration:.5s" d="{sp}" fill="none" '
                     f'stroke="{pal["line"]}" stroke-width=".8" opacity=".8"/>')
            g.append(f'<circle class="pop" style="animation-delay:{dly+0.9:.2f}s" cx="{hx:.1f}" cy="{hy:.1f}" r="1.6" fill="{pal["core"]}"/>')
        if i in top:
            g.append(f'<g class="pop" style="animation-delay:{dly+0.5:.2f}s">'
                     + text(xp, y0 - h - 9, str(v), pal["text"], 9, "middle") + "</g>")
    # main world line on top
    g.append(f'<path class="dr" pathLength="1" style="animation-duration:{D}s;animation-timing-function:linear;animation-delay:.6s" '
             f'd="M{x0} {y0} L{x1} {y0}" stroke="{pal["line"]}" stroke-width="1.6" fill="none"/>')
    # Preserve the vector draw-in, then swap its settled appearance for a 2x PNG.
    # Even isolated SVG filter groups can be rerasterized on every dot update.
    settled = (svg_open(W, H, "Settled world lines") + '<defs>'
               + glow_filter("gl", pal, 1.4, 3.6) + '</defs>' + "".join(g) + '</g></svg>')
    backdrop = png_data(settled, W * 2, H * 2)
    g.append('<set attributeName="display" to="none" begin="8s" fill="freeze"/></g>')
    g.append(f'<image x="0" y="0" width="{W}" height="{H}" href="{backdrop}" opacity="0">'
             '<set attributeName="opacity" to="1" begin="8s" fill="freeze"/></image>')
    # The moving dot must not invalidate the blur of the entire branch graph.
    g.append('<g filter="url(#gl)">')
    # 15 updates/second retains the tracer without requesting full-rate SVG paints.
    points = ";".join(f"{i / 75:.6f}" for i in range(76))
    g.append(f'<circle r="2.6" fill="{pal["core"]}" opacity="0"><set attributeName="opacity" to="1" begin="{0.6+D:.1f}s"/>'
             f'<animateMotion dur="5s" begin="{0.6+D:.1f}s" repeatCount="indefinite" '
             f'calcMode="discrete" keyPoints="{points}" keyTimes="{points}" path="M{x0} {y0} L{x1} {y0}"/></circle>')
    g.append("</g>")
    o += g
    # readout: fraction of observed days with activity
    ratio = d["active_days"] / max(1, len(cells))
    o.append(roll(f"{ratio:.6f}", W - 20, 50, 16, pal, start=0.3, seed=11))
    o.append(text(W - 22, 66, f"divergence = {d['active_days']} of {len(cells)} days active", ex["dimtext"], 9, "end"))
    o.append(text(18, 44, f"{d['total']} contributions  ·  longest streak {d['longest_streak']}d  ·  best day {d['best_day']['count']} ({d['best_day']['date']})",
                  ex["dimtext"], 10))
    o.append(text(W / 2, H - 12, "each branch is one week, diverging by its contributions and converging back into the main world line",
                  ex["dimtext"], 9, "middle"))
    o.insert(3, "<style>" + "".join(css) + "</style>")
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ 2. lab member file (CRT terminal)
LAB_MEM_NO = "042"


def lab_mem_no(d):
    return LAB_MEM_NO


def labfile(d, theme):
    pal, ex = PAL[theme], EXTRA[theme]
    W, H = 880, 244
    peak = max(range(24), key=lambda h: d["push_hours"][h])
    fs, cw = 13, 7.85  # font size, approx monospace advance
    stamp_c = pal["red"]
    css = [".crt{animation:crt 7s steps(1,end) infinite}@keyframes crt{0%,96%,100%{opacity:1}97%{opacity:.86}98%{opacity:1}}",
           ".cur{animation:bl 1s steps(1) infinite}@keyframes bl{50%{opacity:0}}",
           ".scan{animation:sc 6s steps(72,end) infinite}@keyframes sc{from{transform:translateY(-40px)}to{transform:translateY(%dpx)}}" % (H + 40),
           ".st{opacity:0;transform-box:fill-box;transform-origin:center;animation:st .35s cubic-bezier(.2,1.6,.4,1) forwards}"
           "@keyframes st{0%{opacity:0;transform:rotate(-9deg) scale(1.6)}100%{opacity:.85;transform:rotate(-9deg) scale(1)}}",
           ".fi{opacity:0;animation:fi .4s ease-out forwards}@keyframes fi{to{opacity:1}}"]
    o = [svg_open(W, H, f"Lab member file: {d['user']}"), "<defs>", glow_filter("gl", pal, 0.7, 2.4), digit_defs(),
         '<pattern id="sl" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity=".28"/></pattern>',
         f'<radialGradient id="vg" cx=".5" cy=".5" r=".75"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="{.55 if theme=="dark" else .04}"/></radialGradient>',
         f'<linearGradient id="sb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{pal["line"]}" stop-opacity="0"/><stop offset=".5" stop-color="{pal["line"]}" stop-opacity=".07"/><stop offset="1" stop-color="{pal["line"]}" stop-opacity="0"/></linearGradient>']
    # ---- right column: typed key/value lines
    X0, X1 = 284, 586
    L1, L2 = 14, 11
    lines = []  # (y, [(x, str, color)])
    lines.append((76, [(X0, f"$ ./labmem --observe {d['user']}", ex["dimtext"])]))
    rows = [("PUBLIC REPOS", d["public_repos"], "STARS", d["stars"]),
            ("FOLLOWERS", d["followers"], "FOLLOWING", d["following"]),
            ("CONTRIBUTIONS", f"{d['total']} / yr", "STREAK", f"{d['longest_streak']}d max \u00b7 {d['current_streak']}d now"),
            ("COMMITS", f"{d['commits_year']} / yr", "PEAK HOUR", f"{peak:02d}:00")]
    y = 104
    for a_, b_, c_, e_ in rows:
        lines.append((y, [(X0, f"{a_:<{L1}}", ex["dimtext"]), (X0 + L1 * cw, str(b_), pal["text"]),
                          (X1, f"{c_:<{L2}}", ex["dimtext"]), (X1 + L2 * cw, str(e_), pal["text"])]))
        y += 21
    div_y = y - 8
    y += 14
    exp = d.get("experiment")
    if exp:
        room = int((W - 28 - (X0 + L1 * cw)) / cw)
        name = exp["name"]
        rest = exp.get("description") or ""
        rest = (" \u2014 " + rest) if rest else ""
        if len(name) + len(rest) > room:
            rest = rest[: max(0, room - len(name) - 1)].rstrip() + "\u2026"
        lines.append((y, [(X0, f"{'EXPERIMENT':<{L1}}", ex["dimtext"]), (X0 + L1 * cw, name, ex["hi"]),
                          (X0 + (L1 + len(name)) * cw, rest, ex["dimtext"])]))
        y += 21
    status = "observing. world line stable"
    lines.append((y, [(X0, f"{'STATUS':<{L1}}", ex["dimtext"]), (X0 + L1 * cw, status, pal["text"])]))
    clips, body, t = [], [], 0.6
    for li, (yy, parts) in enumerate(lines):
        right = max(x + len(s_) * cw for x, s_, _ in parts)
        n = max(1, int((right - X0) / cw))
        dur = max(0.2, n * 0.008)
        vals = ";".join(f"{X0 - 4 + (right - X0 + 8) * k / 12:.0f}" for k in range(13))
        clips.append(f'<clipPath id="c{li}"><rect x="0" y="{yy-fs}" width="0" height="{fs+6}">'
                     f'<animate attributeName="width" values="{vals}" dur="{dur:.2f}s" begin="{t:.2f}s" fill="freeze" calcMode="discrete"/></rect></clipPath>')
        g = [f'<g clip-path="url(#c{li})">']
        for x, s_, col in parts:
            g.append(text(x, yy, s_, col, fs, extra='xml:space="preserve"'))
        g.append("</g>")
        body += g
        t += dur + (0.3 if li == 0 else 0.1)
    cx = X0 + L1 * cw + len(status) * cw + 4
    cursor = (f'<rect class="cur" x="{cx:.1f}" y="{lines[-1][0]-fs+2}" width="{cw:.1f}" height="{fs}" fill="{pal["line"]}" opacity="0">'
                f'<set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/></rect>')
    o += clips + ["</defs>"]
    o.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="{ex["panel"]}" stroke="{ex["panel_s"]}"/>')
    o.append('<g class="crt">')
    # ---- header strip
    o.append(f'<path d="M1 13a12 12 0 0 1 12-12h{W-26}a12 12 0 0 1 12 12v27H1z" fill="{pal["line"]}" opacity="{.08 if theme=="dark" else .1}"/>')
    o.append(f'<line x1="1" y1="40" x2="{W-1}" y2="40" stroke="{pal["line"]}" stroke-opacity=".35"/>')
    o.append(text(24, 25, "FUTURE GADGET LABORATORY", pal["text"], 11, weight="bold", extra='letter-spacing="3" filter="url(#gl)"'))
    o.append(text(W - 24, 25, "PERSONNEL DOSSIER  //  WORLD LINE 1.048596", ex["dimtext"], 10, "end", extra='letter-spacing="2"'))
    # ---- left column: identity
    o.append(text(24, 68, "LAB MEM", ex["dimtext"], 10, extra='letter-spacing="3"'))
    o.append(f'<g class="fi" style="animation-delay:.25s">' + text(24, 112, "No.", pal["text"], 15, weight="bold")
             + number(lab_mem_no(d), 158, 114, 38, pal) + "</g>")
    o.append(text(24, 146, "OPERATOR", ex["dimtext"], 10, extra='letter-spacing="3"'))
    o.append(f'<g class="fi" style="animation-delay:.45s">' + text(24, 170, d["user"], ex["hi"], 20, weight="bold", extra='filter="url(#gl)"') + "</g>")
    o.append(text(24, 196, "MEMBER SINCE", ex["dimtext"], 10, extra='letter-spacing="3"'))
    o.append(text(24, 214, d["created_at"][:7].replace("-", " / "), pal["text"], fs))
    # dividers
    o.append(f'<line x1="258" y1="58" x2="258" y2="{H-24}" stroke="{ex["faint"]}"/>')
    o.append(f'<line x1="{X0}" y1="{div_y}" x2="{W-24}" y2="{div_y}" stroke="{ex["faint"]}" stroke-dasharray="3 4"/>')
    o.append('<g filter="url(#gl)">' + "".join(body) + "</g>")
    o.append('<g filter="url(#gl)">' + cursor + "</g>")
    o.append(text(W - 24, H - 12, f"sync {d['generated']}", ex["faint"] if theme == "dark" else ex["dimtext"], 9, "end"))
    o.append("</g>")
    # ---- classification stamp
    sx, sy = W - 136, 56
    o.append(f'<g class="st" style="animation-delay:{t+0.2:.2f}s">'
             f'<rect x="{sx}" y="{sy}" width="112" height="28" rx="3" fill="none" stroke="{stamp_c}" stroke-width="2"/>'
             f'<rect x="{sx+3}" y="{sy+3}" width="106" height="22" rx="2" fill="none" stroke="{stamp_c}" stroke-width=".8"/>'
             + text(sx + 56, sy + 19, "CLASSIFIED", stamp_c, 13, "middle", weight="bold", extra='letter-spacing="2.5"') + "</g>")
    o.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="12" fill="url(#sl)" opacity="{1 if theme=="dark" else .1}"/>')
    o.append(f'<rect class="scan" x="1" y="0" width="{W-2}" height="40" fill="url(#sb)"/>')
    o.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="12" fill="url(#vg)"/>')
    o.insert(3, "<style>" + "".join(css) + "</style>")
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ 3. phone microwave (language dials)
def phonewave(d, theme):
    pal, ex = PAL[theme], EXTRA[theme]
    W, H = 880, 250
    langs = d["languages"][:5]
    tot = sum(v for _, v in d["languages"]) or 1
    n = len(langs)
    o = [svg_open(W, H, "Language breakdown dials"), "<defs>", glow_filter("gl", pal, 1.0, 3.0), digit_defs(), "</defs>"]
    o.append(frame(W, H, pal, ex, "PHONE MICROWAVE (NAME SUBJECT TO CHANGE)", f"LANGUAGES BY BYTES  ·  {len(d['repos'])} REPOS"))
    css = [".jit{animation:jit 2.6s ease-in-out infinite}@keyframes jit{0%,100%{transform:rotate(0)}50%{transform:rotate(1.2deg)}}"]
    span, a0 = 240, -120
    cw = (W - 40) / n
    for i, (name, v) in enumerate(langs):
        pct = v / tot * 100
        cx, cy, R = 20 + cw * i + cw / 2, 120, 62
        g = []
        # scale ticks
        for k in range(0, 51):
            a = math.radians(a0 + span * k / 50 - 90)
            r1 = R - (9 if k % 10 == 0 else 5)
            col = ex["faint"] if theme == "dark" else ex["panel_s"]
            if k % 10 == 0:
                col = ex["dimtext"]
            g.append(f'<line x1="{cx+R*math.cos(a):.1f}" y1="{cy+R*math.sin(a):.1f}" x2="{cx+r1*math.cos(a):.1f}" y2="{cy+r1*math.sin(a):.1f}" stroke="{col}" stroke-width="{1.2 if k%10==0 else .8}"/>')
        # lit arc up to value
        ang = a0 + span * pct / 100
        def pt(deg, r):
            a = math.radians(deg - 90)
            return cx + r * math.cos(a), cy + r * math.sin(a)
        sx, sy = pt(a0, R + 6)
        ex_, ey = pt(ang, R + 6)
        large = 1 if span * pct / 100 > 180 else 0
        arc = f"M{sx:.1f} {sy:.1f} A{R+6} {R+6} 0 {large} 1 {ex_:.1f} {ey:.1f}"
        dl = 0.4 + i * 0.25
        g.append(f'<path d="{arc}" fill="none" stroke="{pal["line"]}" stroke-width="3" stroke-linecap="round" pathLength="1" '
                 f'stroke-dasharray="1" stroke-dashoffset="1" filter="url(#gl)">'
                 f'<animate attributeName="stroke-dashoffset" from="1" to="0" begin="{dl:.2f}s" dur="1.3s" fill="freeze" calcMode="spline" keySplines=".2 .8 .2 1" keyTimes="0;1"/></path>')
        # needle
        g.append(f'<g transform="translate({cx:.1f} {cy:.1f})"><g class="jit" style="animation-delay:{dl+1.4:.2f}s"><g transform="rotate({a0})">'
                 f'<line x1="0" y1="8" x2="0" y2="{-(R-12)}" stroke="{pal["line"]}" stroke-width="5" stroke-linecap="round" opacity=".25"/>'
                 f'<line x1="0" y1="8" x2="0" y2="{-(R-12)}" stroke="{pal["core"] if theme == "dark" else ex["hi"]}" stroke-width="1.6" stroke-linecap="round"/>'
                 f'<animateTransform attributeName="transform" type="rotate" values="{a0};{ang+6:.1f};{ang-2:.1f};{ang:.1f}" keyTimes="0;.6;.85;1" '
                 f'begin="{dl:.2f}s" dur="1.6s" fill="freeze" calcMode="spline" keySplines=".3 0 .2 1;.4 0 .6 1;.4 0 .6 1"/>'
                 f'</g></g><circle r="5" fill="{ex["panel"]}" stroke="{pal["line"]}" stroke-width="1.4"/><circle r="1.8" fill="{pal["line"]}"/></g>')
        o += g
        o.append(roll(f"{pct:.1f}", cx + (26 if pct >= 10 else 20), cy + 52, 16, pal, start=dl, steps=7, seed=i))
        o.append(text(cx, cy + 76, name.upper(), ex["dimtext"], 10, "middle", extra='letter-spacing="1.5"'))
    o.insert(3, "<style>" + "".join(css) + "</style>")
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ 4. reading steiner (commit clock)
def steiner(d, theme):
    pal, ex = PAL[theme], EXTRA[theme]
    W, H = 880, 284
    hrs, wds = d["push_hours"], d["push_weekdays"]
    mh, mw = max(hrs) or 1, max(wds) or 1
    peak = max(range(24), key=lambda h: hrs[h])
    tot = sum(hrs)
    o = [svg_open(W, H, "Commit clock by hour of day"), "<defs>", glow_filter("gl", pal, 1.1, 3.2), digit_defs(), "</defs>"]
    o.append(frame(W, H, pal, ex, "READING STEINER  //  WHEN THE OPERATOR COMMITS", f"{tot} COMMITS  ·  LAST 365 DAYS  ·  EUROPE/BERLIN"))
    css = [".bar{transform-box:fill-box;transform-origin:50% 100%;transform:scaleY(0);animation:gr .9s cubic-bezier(.2,.8,.2,1) forwards}",
           "@keyframes gr{to{transform:scaleY(1)}}",
           ".hb{transform-box:fill-box;transform-origin:0 50%;transform:scaleX(0);animation:gx .9s cubic-bezier(.2,.8,.2,1) forwards}@keyframes gx{to{transform:scaleX(1)}}"]
    cx, cy, R0, R1 = 210, 160, 42, 92
    # face
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{R1+8}" fill="none" stroke="{ex["faint"]}"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{R0-6}" fill="none" stroke="{ex["faint"]}"/>')
    g = ['<g filter="url(#gl)">']
    for h in range(24):
        a = math.radians(h / 24 * 360 - 90)
        L = (hrs[h] / mh) * (R1 - R0)
        # bar as rotated rect growing outward
        dl = 0.5 + ((peak - h) % 24) * 0.03
        col = pal["line"] if h == peak else pal["lv"][3 if hrs[h] > mh * 0.4 else 2]
        if L > 0.5:
            g.append(f'<g transform="translate({cx} {cy}) rotate({h/24*360:.1f})"><rect class="bar" style="animation-delay:{dl:.2f}s" '
                     f'x="-4.2" y="{-(R0+L):.1f}" width="8.4" height="{L:.1f}" rx="2" fill="{col}"/></g>')
        tx, ty = cx + (R1 + 20) * math.cos(a), cy + (R1 + 20) * math.sin(a) + 3
        if h % 3 == 0:
            o.append(text(tx, ty, f"{h:02d}", ex["dimtext"], 9, "middle"))
        else:
            o.append(f'<circle cx="{cx+(R1+8)*math.cos(a):.1f}" cy="{cy+(R1+8)*math.sin(a):.1f}" r=".9" fill="{ex["dimtext"]}"/>')
    g.append("</g>")
    o += g
    # time-leap hand: spins backwards twice, settles on the peak hour
    ang = peak / 24 * 360
    o.append(f'<g transform="translate({cx} {cy})"><g><line x1="0" y1="0" x2="0" y2="{-(R1+4)}" stroke="{pal["line"]}" stroke-width="5" opacity=".22"/><line x1="0" y1="0" x2="0" y2="{-(R1+4)}" stroke="{pal["core"] if theme == "dark" else ex["hi"]}" stroke-width="1.4"/>'
             f'<animateTransform attributeName="transform" type="rotate" values="0;-720;{ang-360-8:.1f};{ang-360:.1f}" keyTimes="0;.55;.85;1" dur="2.6s" begin=".3s" fill="freeze" '
             f'calcMode="spline" keySplines=".5 0 .5 1;.3 0 .3 1;.4 0 .6 1"/></g><circle r="3" fill="{pal["line"]}"/></g>')
    o.append(roll(f"{peak:02d}.00", cx + 28, cy + 8, 20, pal, start=0.4, seed=3))
    o.append(text(cx, cy + 26, "PEAK HOUR", ex["dimtext"], 8, "middle", extra='letter-spacing="2"'))
    # weekday bars
    names = "MON TUE WED THU FRI SAT SUN".split()
    bx, by, bw = 420, 76, 330
    o.append(text(bx, by - 14, "BY WEEKDAY", ex["dimtext"], 9, extra='letter-spacing="2"'))
    g = ['<g filter="url(#gl)">']
    for i, v in enumerate(wds):
        yy = by + i * 24
        o.append(text(bx, yy + 9, names[i], ex["dimtext"], 10))
        o.append(f'<rect x="{bx+40}" y="{yy}" width="{bw}" height="10" rx="2" fill="{ex["grid"]}"/>')
        if v:
            g.append(f'<rect class="hb" style="animation-delay:{1.0+i*0.12:.2f}s" x="{bx+40}" y="{yy}" width="{bw*v/mw:.1f}" height="10" rx="2" '
                     f'fill="{pal["line"] if v == mw else pal["lv"][3]}"/>')
        o.append(text(bx + 40 + bw + 10, yy + 9, str(v), pal["text"], 10))
    g.append("</g>")
    o += g
    night = sum(hrs[h] for h in (22, 23, 0, 1, 2, 3, 4, 5))
    o.append(text(bx, by + 7 * 24 + 18, f"{night * 100 // max(1, tot)}% of commits between 22:00 and 06:00", ex["dimtext"], 10))
    o.insert(3, "<style>" + "".join(css) + "</style>")
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ 5. d-mail glitch, framed like the other panels
def dmail(d, theme):
    pal, ex = PAL[theme], EXTRA[theme]
    inner = contrib_graph.dmail(d["cells"], pal)
    head, body = inner.split(">", 1)
    iw = int(head.split('width="')[1].split('"')[0])
    ih = int(head.split('height="')[1].split('"')[0])
    body = body.rsplit("</svg>", 1)[0]
    W = 880
    H = ih + 30
    ox = (W - iw) / 2
    o = [svg_open(W, H, "Contribution graph, world line shift"),
         frame(W, H, pal, ex, "D-MAIL  //  WORLD LINE SHIFT"),
         text(18, H - 10, f"{d['total']} contributions in the last year", ex["dimtext"], 9),
         f'<svg x="{ox:.1f}" y="22" width="{iw}" height="{ih}" viewBox="0 0 {iw} {ih}">{body}</svg>',
         "</svg>"]
    return "\n".join(o)


# ------------------------------------------------------------------ 6. title with a d-mail glitch on the name
def title(d, theme, name=None):
    pal, ex = PAL[theme], EXTRA[theme]
    name = name or d.get("user", "yubinex")
    W, H, T = 600, 64, 9.0
    fs, y = 30, 42
    lead = "Hi, I'm "
    alt = "".join({"u": "µ", "i": "!", "e": "3", "b": "8", "n": "П", "y": "¥", "x": "×"}.get(ch, ch) for ch in name)
    lead_c = "#e6edf3" if theme == "dark" else "#1f2328"
    name_c = pal["line"] if theme == "dark" else pal["text"]
    rnd = random.Random(1048596)

    def line(gid, nm, glow=True, show_lead=False, show_name=True):
        return (f'<g id="{gid}"><text x="{W/2}" y="{y}" text-anchor="middle" font-family="{MONO}" font-size="{fs}" font-weight="700">'
                f'<tspan fill="{lead_c if show_lead else "transparent"}">{esc(lead)}</tspan>'
                f'<tspan fill="{name_c if show_name else "transparent"}"{" filter=\"url(#gl)\"" if glow else ""}>{esc(nm)}</tspan></text></g>')
    # timeline in % of T: small twitch, then the real world-line shift
    a1, b1 = 31.0, 32.6
    a2, b2 = 72.0, 79.0
    s1, s2 = 74.6, 76.6  # alternate world line shown
    css = [
        f"@keyframes bs{{0%,{s1-0.01}%{{opacity:1}}{s1}%,{s2-0.01}%{{opacity:0}}{s2}%,100%{{opacity:1}}}}",
        f"@keyframes as{{0%,{s1-0.01}%{{opacity:0}}{s1}%,{s2-0.01}%{{opacity:1}}{s2}%,100%{{opacity:0}}}}",
        f".bs{{animation:bs {T}s steps(1,end) infinite}}.as{{opacity:0;animation:as {T}s steps(1,end) infinite}}",
    ]
    o = [svg_open(W, H, f"Hi, I'm {name}"), "<defs>", glow_filter("gl", pal, 0.8, 2.4) if theme == "dark" else
         f'<filter id="gl"><feOffset/></filter>',
         line("t", name), line("ta", alt), line("tr", name, False), line("tar", alt, False)]
    nb = 6
    top, bot = y - fs * 0.85, y + fs * 0.3
    bh = (bot - top) / nb
    for i in range(nb):
        o.append(f'<clipPath id="c{i}"><rect x="0" y="{top + i*bh:.1f}" width="{W}" height="{bh+0.6:.1f}"/></clipPath>')
    o.append(f'<filter id="red"><feFlood flood-color="{pal["red"]}"/><feComposite in2="SourceAlpha" operator="in"/></filter>')
    o.append(f'<filter id="cy"><feFlood flood-color="{"#5ad1ff" if theme == "dark" else "#1a7fb0"}"/><feComposite in2="SourceAlpha" operator="in"/></filter>')
    o.append("</defs>")
    o.append(line("lead", name, False, True, False).replace('<g id="lead">', '<g>'))
    o.append('<use href="#t" class="bs"/><use href="#ta" class="as"/>')

    def slices(src, a, b, k0, amp):
        parts = []
        for i in range(nb):
            kf = [f"0%,{a-0.01:.2f}%{{opacity:0;transform:translateX(0)}}"]
            for f in range(6):
                t = a + (b - a) * f / 6
                dx = rnd.choice([0, -1, 1, 1]) * rnd.uniform(2, amp)
                kf.append(f"{t:.2f}%{{opacity:1;transform:translateX({dx:.1f}px)}}")
            kf.append(f"{b:.2f}%,100%{{opacity:0;transform:translateX(0)}}")
            k = f"{k0}{i}"
            css.append(f"@keyframes {k}{{{''.join(kf)}}}.{k}{{opacity:0;animation:{k} {T}s steps(1,end) infinite}}")
            parts.append(f'<g clip-path="url(#c{i})"><use href="#{src}" class="{k}"/></g>')
        return parts

    def split(src, a, b, k, fid, dx, op):
        css.append(f"@keyframes {k}{{0%,{a-0.01:.2f}%{{opacity:0}}{a:.2f}%{{opacity:{op};transform:translate({dx}px,-1px)}}"
                   f"{(a+b)/2:.2f}%{{opacity:{op*0.7:.2f};transform:translate({-dx*1.3:.1f}px,1px)}}{b:.2f}%,100%{{opacity:0}}}}"
                   f".{k}{{opacity:0;animation:{k} {T}s steps(1,end) infinite}}")
        return f'<use href="#{src}" class="{k}" filter="url(#{fid})"/>'
    # mask the base during slice frames so the strips read as displaced, not doubled
    o += slices("t", a1, b1, "p", 6)
    o += slices("t", a2, s1, "q", 22) + slices("ta", s1, s2, "r", 14) + slices("t", s2, b2, "s", 18)
    o.append(split("tr", a1, b1, "k1", "red", 2, .6))
    o.append(split("tr", a2, s1, "k2", "red", 4, .55))
    o.append(split("tar", s1, s2, "k3", "red", 3, .5))
    o.append(split("tr", s2, b2, "k4", "cy", 3, .35))
    css.append(f"@keyframes sc{{0%,{a2:.2f}%{{opacity:0;transform:translateY(0)}}{a2+0.1:.2f}%{{opacity:.8}}"
               f"{b2:.2f}%{{opacity:0;transform:translateY({bot-top+6:.0f}px)}}100%{{opacity:0}}}}.sc{{opacity:0;animation:sc {T}s linear infinite}}")
    o.append(f'<rect class="sc" x="40" y="{top-3:.1f}" width="{W-80}" height="1.2" fill="{pal["line"]}"/>')
    o.insert(3, "<style>" + "".join(css) + "</style>")
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ 7. recent activity as incoming d-mails
def feed(d, theme):
    pal, ex = PAL[theme], EXTRA[theme]
    items = (d.get("feed") or [])[:6]
    W, row, top = 880, 40, 46
    H = top + row * max(1, len(items)) + 30
    rnd = random.Random(571024)
    body_c = "#c9d1d9" if theme == "dark" else "#3d444d"
    css = [
        ".mi{opacity:0;animation:mi .9s steps(1,end) forwards}",
        "@keyframes mi{0%{opacity:0}10%{opacity:1;transform:translateX(-6px)}20%{opacity:.2}30%{opacity:1;transform:translateX(4px)}"
        "45%{opacity:.6;transform:translateX(-2px)}60%,100%{opacity:1;transform:translateX(0)}}",
        ".rs{opacity:0;animation:rs .9s steps(1,end) forwards}",
        "@keyframes rs{0%{opacity:0}10%{opacity:.7;transform:translate(3px,-1px)}30%{opacity:.5;transform:translate(-4px,1px)}45%{opacity:.3}60%,100%{opacity:0}}",
        ".nw{opacity:0;animation:nw 1.8s ease-out forwards}@keyframes nw{0%{opacity:0}20%{opacity:1}100%{opacity:.0}}",
        ".cur{animation:cb 1.1s steps(1,end) infinite}@keyframes cb{0%{opacity:1}50%{opacity:0}}",
        # an old message twitches now and then
        ".tw{animation:tw 9s steps(1,end) infinite}@keyframes tw{0%,93%,100%{transform:translateX(0);opacity:1}94%{transform:translateX(5px);opacity:.6}95%{transform:translateX(-3px)}96%{transform:translateX(0);opacity:1}}",
    ]
    o = [svg_open(W, H, "Recent activity as incoming D-Mails"), "<defs>", glow_filter("gl", pal, 0.6, 1.8),
         f'<filter id="red"><feFlood flood-color="{pal["red"]}"/><feComposite in2="SourceAlpha" operator="in"/></filter></defs>']
    o.append(frame(W, H, pal, ex, "D-MAIL INBOX  //  INCOMING", f"{len(items)} RECEIVED  \u00b7  LATEST FIRST"))
    o.append(f'<line x1="18" y1="32" x2="{W-18}" y2="32" stroke="{ex["panel_s"]}"/>')
    for i, it in enumerate(items):
        y = top + i * row
        dl = 0.4 + i * 0.45
        g = []
        # envelope icon
        ix, iy = 22, y + 2
        g.append(f'<rect x="{ix}" y="{iy}" width="18" height="12" rx="1.5" fill="none" stroke="{pal["line"]}" stroke-width="1.2"/>'
                 f'<path d="M{ix} {iy+1}L{ix+9} {iy+7}L{ix+18} {iy+1}" fill="none" stroke="{pal["line"]}" stroke-width="1.2"/>')
        g.append(text(52, y + 12, f"D-MAIL RECEIVED  //  {it['time']}", pal["text"], 10, extra='letter-spacing="1.5"'))
        g.append(text(W - 18, y + 12, it["head"], ex["dimtext"], 10, "end"))
        body = it.get("body") or it["head"]
        g.append(text(52, y + 29, f"\u201c{body}\u201d" if it.get("body") else body, body_c, 12))
        inner = "".join(g)
        o.append(f'<g class="tw" style="animation-delay:{3 + i * 1.7:.1f}s">'
                 f'<g class="rs" style="animation-delay:{dl:.2f}s" filter="url(#red)">{inner}</g>'
                 f'<g class="mi" style="animation-delay:{dl:.2f}s">{inner}</g></g>')
        if i == 0:
            o.append(f'<g class="nw" style="animation-delay:{dl+0.5:.2f}s">' + text(W - 18, y + 29, "NEW", pal["line"], 9, "end", extra='letter-spacing="2"') + "</g>")
        if i < len(items) - 1:
            o.append(f'<line x1="52" y1="{y+row-5}" x2="{W-18}" y2="{y+row-5}" stroke="{ex["grid"]}" stroke-dasharray="2 5"/>')
    if not items:
        o.append(text(52, top + 16, "no D-Mails on this world line yet", ex["dimtext"], 12))
    end = 0.4 + len(items) * 0.45 + 0.6
    o.append(f'<g class="mi" style="animation-delay:{end:.2f}s">' + text(18, H - 12, "awaiting next D-Mail", ex["dimtext"], 9)
             + f'<rect class="cur" x="{18 + 21*5.45:.1f}" y="{H-20}" width="5" height="10" fill="{pal["line"]}"/></g>')
    o.append(text(W - 18, H - 12, f"times {d.get('tz', 'Europe/Berlin')}", ex["dimtext"], 9, "end"))
    o.insert(3, "<style>" + "".join(css) + "</style>")
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ 8. future gadget list (repos)
STAR = "M0 -5.2L1.5 -1.7L5.3 -1.6L2.4 0.8L3.3 4.5L0 2.5L-3.3 4.5L-2.4 0.8L-5.3 -1.6L-1.5 -1.7Z"


def gadget_list(d, theme):
    pal, ex = PAL[theme], EXTRA[theme]
    items = (d.get("gadgets") or [])[:6]
    W, cols, cw_, ch_, gx, gy, top = 880, 2, 412, 92, 16, 14, 46
    nrows = max(1, (len(items) + 1) // 2)
    H = top + nrows * ch_ + (nrows - 1) * gy + 18
    css = [
        ".gi{opacity:0;animation:gi .8s steps(1,end) forwards}",
        "@keyframes gi{0%{opacity:0}12%{opacity:1;transform:translateX(-5px)}22%{opacity:.25}34%{opacity:1;transform:translateX(3px)}"
        "50%{opacity:.7;transform:translateX(0)}60%,100%{opacity:1;transform:translateX(0)}}",
        ".ac{animation:ac 2.4s ease-in-out infinite}@keyframes ac{0%,100%{opacity:1}50%{opacity:.45}}",
    ]
    o = [svg_open(W, H, "Future gadget list: selected repositories"), "<defs>", glow_filter("gl", pal, 0.6, 1.8), "</defs>"]
    o.append(frame(W, H, pal, ex, "FUTURE GADGET LIST", "(NAMES SUBJECT TO CHANGE)"))
    o.append(f'<line x1="18" y1="32" x2="{W-18}" y2="32" stroke="{ex["panel_s"]}"/>')
    body_c = "#c9d1d9" if theme == "dark" else "#3d444d"
    card_bg = "#120f0d" if theme == "dark" else "#ffffff"
    for i, g in enumerate(items):
        cx = 18 + (i % cols) * (cw_ + gx)
        cy = top + (i // cols) * (ch_ + gy)
        dl = 0.35 + i * 0.3
        active = g.get("age", 999) <= 30
        tag = "ACTIVE" if active else "DORMANT"
        tag_c = pal["line"] if active else ex["dimtext"]
        p = [f'<rect x="{cx}" y="{cy}" width="{cw_}" height="{ch_}" rx="8" fill="{card_bg}" stroke="{ex["panel_s"]}"/>',
             f'<rect x="{cx}" y="{cy+10}" width="2.5" height="{ch_-20}" rx="1" fill="{pal["line"]}" opacity="{.9 if active else .35}"/>',
             text(cx + 16, cy + 20, f"FUTURE GADGET No.{i+1:02d}" + ("  \u00b7  PINNED" if g.get("pinned") else ""), pal["text"], 9, extra='letter-spacing="2"')]
        tw = len(tag) * 6.2 + 14
        p.append(f'<g{" class=\"ac\"" if active else ""}><rect x="{cx+cw_-14-tw:.1f}" y="{cy+9}" width="{tw:.1f}" height="15" rx="7.5" fill="none" stroke="{tag_c}"/>'
                 + text(cx + cw_ - 14 - tw / 2, cy + 20, tag, tag_c, 9, "middle", extra='letter-spacing="1.5"') + "</g>")
        p.append(text(cx + 16, cy + 42, g["name"], ex["hi"], 15, weight="bold", extra='filter="url(#gl)"' if theme == "dark" else ""))
        desc = g.get("description") or "no description on this world line"
        lim = 58
        if len(desc) > lim:
            desc = desc[: lim - 1].rstrip() + "\u2026"
        p.append(text(cx + 16, cy + 60, desc, body_c, 11))
        fx = cx + 16
        meta_y = cy + 80
        if g.get("language"):
            p.append(f'<circle cx="{fx+4}" cy="{meta_y-4}" r="4" fill="{pal["line"]}"/>')
            p.append(text(fx + 13, meta_y, g["language"], ex["dimtext"], 10))
            fx += 13 + len(g["language"]) * 6.1 + 18
        p.append(f'<path d="{STAR}" transform="translate({fx+5} {meta_y-4})" fill="none" stroke="{pal["line"]}" stroke-width="1.1" stroke-linejoin="round"/>')
        p.append(text(fx + 14, meta_y, str(g.get("stars", 0)), ex["dimtext"], 10))
        p.append(text(cx + cw_ - 14, meta_y, f"last push {g.get('pushed', '')}", ex["dimtext"], 10, "end"))
        o.append(f'<g class="gi" style="animation-delay:{dl:.2f}s">' + "".join(p) + "</g>")
    if not items:
        o.append(text(W / 2, top + 40, "no gadgets registered on this world line", ex["dimtext"], 12, "middle"))
    o.insert(3, "<style>" + "".join(css) + "</style>")
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ 9. registered lab equipment (tech stack)
def _icon(kind, x, y, c, bg):
    """16x16 line icons drawn around (x, y) top-left."""
    sw = 'fill="none" stroke="%s" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"' % c
    if kind == "C":
        return (f'<path d="M{x+8} {y} L{x+15} {y+4} L{x+15} {y+12} L{x+8} {y+16} L{x+1} {y+12} L{x+1} {y+4} Z" {sw}/>'
                f'<path d="M{x+10.8} {y+5.6} A3.6 3.6 0 1 0 {x+10.8} {y+10.4}" {sw}/>')
    if kind == "Python":
        return (f'<path d="M{x+8} {y+7} H{x+4} Q{x+1} {y+7} {x+1} {y+10} V{x+0 and y+11} Q{x+1} {y+14} {x+4} {y+14} H{x+6} V{y+11} Q{x+6} {y+9} {x+8} {y+9} H{x+11} Q{x+13} {y+9} {x+13} {y+7} V{y+3} Q{x+13} {y+1} {x+10} {y+1} H{x+7} Q{x+4} {y+1} {x+4} {y+3} V{y+5}" {sw}/>'
                f'<path d="M{x+8} {y+9} H{x+12} Q{x+15} {y+9} {x+15} {y+6}" {sw} opacity=".0"/>'
                f'<path d="M{x+12} {y+9} V{y+13} Q{x+12} {y+15} {x+9} {y+15} H{x+7}" {sw}/>'
                f'<circle cx="{x+7}" cy="{y+3.6}" r=".9" fill="{c}"/><circle cx="{x+9.5}" cy="{y+12.6}" r=".9" fill="{c}"/>')
    if kind == "Bash":
        return (f'<rect x="{x+.5}" y="{y+1.5}" width="15" height="13" rx="2" {sw}/>'
                f'<path d="M{x+3.5} {y+6} L{x+6} {y+8.2} L{x+3.5} {y+10.4}" {sw}/><path d="M{x+8} {y+11} H{x+12}" {sw}/>')
    if kind in ("JavaScript", "TypeScript"):
        lab = "JS" if kind == "JavaScript" else "TS"
        return (f'<rect x="{x+.5}" y="{y+.5}" width="15" height="15" rx="2" fill="{c}"/>'
                f'<text x="{x+14}" y="{y+13.6}" fill="{bg}" font-family="{MONO}" font-size="7.5" font-weight="700" text-anchor="end">{lab}</text>')
    if kind in ("HTML", "CSS"):
        inner = (f'<path d="M{x+6} {y+5} L{x+4} {y+8} L{x+6} {y+11} M{x+10} {y+5} L{x+12} {y+8} L{x+10} {y+11}" {sw}/>' if kind == "HTML" else
                 f'<path d="M{x+7} {y+4.5} Q{x+5} {y+4.5} {x+5.5} {y+6.5} Q{x+6} {y+8} {x+4.5} {y+8} Q{x+6} {y+8} {x+5.5} {y+9.5} Q{x+5} {y+11.5} {x+7} {y+11.5}'
                 f' M{x+9} {y+4.5} Q{x+11} {y+4.5} {x+10.5} {y+6.5} Q{x+10} {y+8} {x+11.5} {y+8} Q{x+10} {y+8} {x+10.5} {y+9.5} Q{x+11} {y+11.5} {x+9} {y+11.5}" {sw}/>')
        return f'<path d="M{x+1} {y} H{x+15} L{x+13.6} {y+13.4} L{x+8} {y+16} L{x+2.4} {y+13.4} Z" {sw}/>' + inner
    if kind == "React":
        e = "".join(f'<ellipse cx="{x+8}" cy="{y+8}" rx="7.6" ry="2.9" transform="rotate({a} {x+8} {y+8})" {sw.replace("1.4", "1.1")}/>' for a in (0, 60, 120))
        return e + f'<circle cx="{x+8}" cy="{y+8}" r="1.5" fill="{c}"/>'
    return ""


STACK = ["C", "Python", "Bash", "JavaScript", "TypeScript", "HTML", "CSS", "React"]


def stack(d, theme):
    pal, ex = PAL[theme], EXTRA[theme]
    pad, gap, H = 18, 8, 78
    widths = [12 + 16 + 8 + len(n) * 6.9 + 12 for n in STACK]
    W = int(pad * 2 + sum(widths) + gap * (len(STACK) - 1))
    css = [".on{opacity:0;animation:on .6s steps(1,end) forwards}",
           "@keyframes on{0%{opacity:0}20%{opacity:.8}35%{opacity:.15}55%{opacity:1}70%{opacity:.5}85%,100%{opacity:1}}",
           ".fl{animation:fl 8s infinite}@keyframes fl{0%,94%,100%{opacity:1}95%{opacity:.55}96.5%{opacity:1}}"]
    o = [svg_open(W, H, "Tech stack: " + ", ".join(STACK)), "<defs>", glow_filter("gl", pal, 0.5, 1.6), "</defs>"]
    o.append(frame(W, H, pal, ex, "REGISTERED LAB EQUIPMENT", f"{len(STACK):02d} UNITS"))
    chip_bg = "#120f0d" if theme == "dark" else "#ffffff"
    x = pad
    for i, (n, w) in enumerate(zip(STACK, widths)):
        y = 34
        c = pal["line"] if theme == "dark" else pal["text"]
        g = [f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="30" rx="6" fill="{chip_bg}" stroke="{ex["panel_s"]}"/>',
             f'<g filter="url(#gl)">{_icon(n, round(x + 12, 1), y + 7, c, chip_bg)}</g>',
             text(x + 36, y + 19.5, n, ex["hi"] if theme == "dark" else ex["hi"], 11.5)]
        o.append(f'<g class="on" style="animation-delay:{0.25 + i * 0.13:.2f}s"><g class="fl" style="animation-delay:{i * 0.9:.1f}s">' + "".join(g) + "</g></g>")
        x += w + gap
    o.insert(3, "<style>" + "".join(css) + "</style>")
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ 10. footer
def footer(d, theme):
    pal, ex = PAL[theme], EXTRA[theme]
    W, H = 600, 40
    msg = "El Psy Kongroo."
    fs, cw = 13, 7.85
    tw = len(msg) * cw
    x0 = W / 2 - tw / 2
    c = pal["line"] if theme == "dark" else pal["text"]
    css = [".fl{animation:fl 9s infinite}@keyframes fl{0%,95%,100%{opacity:1}96%{opacity:.5}97%{opacity:1}98%{opacity:.75}}",
           ".cur{opacity:0;animation:cu 1s steps(1) 2.1s 3 forwards}@keyframes cu{0%{opacity:1}50%{opacity:0}100%{opacity:0}}",
           ".ln{stroke-dasharray:1;stroke-dashoffset:1;animation:ln .8s ease-out .2s forwards}@keyframes ln{to{stroke-dashoffset:0}}"]
    steps = len(msg)
    vals = ";".join(f"{tw*k/steps:.1f}" for k in range(steps + 1))
    o = [svg_open(W, H, msg), "<defs>", glow_filter("gl", pal, 0.6, 2.0),
         f'<clipPath id="ty"><rect x="{x0-2:.1f}" y="0" width="0" height="{H}"><animate attributeName="width" values="{vals}" '
         f'dur="{steps*0.07:.2f}s" begin=".6s" fill="freeze" calcMode="discrete"/></rect></clipPath></defs>']
    gap = 18
    o.append(f'<path class="ln" pathLength="1" d="M{x0-gap:.1f} 17 L60 17" stroke="{ex["panel_s"]}" fill="none"/>')
    o.append(f'<path class="ln" pathLength="1" d="M{x0+tw+gap+6:.1f} 17 L{W-60} 17" stroke="{ex["panel_s"]}" fill="none"/>')
    o.append(f'<g class="fl" clip-path="url(#ty)">' + text(x0, 21.5, msg, c, fs, extra=('filter="url(#gl)" ' if theme == "dark" else "") + 'font-style="italic"') + "</g>")
    o.append(f'<rect class="cur" x="{x0+tw+3:.1f}" y="{21.5-fs+2}" width="6" height="{fs-1}" fill="{c}"/>')
    o.append(text(W / 2, 36, "transmission end  //  world line 1.048596", ex["dimtext"], 8, "middle",
                  extra='letter-spacing="1.5" opacity=".55"'))
    o.insert(3, "<style>" + "".join(css) + "</style>")
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ 11. observation monitor around the OP GIF
GIF_PATH = "assets/op.gif"


def monitor(d, theme):
    import base64, struct
    pal, ex = PAL[theme], EXTRA[theme]
    raw = open(GIF_PATH, "rb").read()
    if raw[:6] not in (b"GIF87a", b"GIF89a"):
        raise SystemExit(f"{GIF_PATH} is not a GIF")
    gw, gh = struct.unpack("<HH", raw[6:10])
    SW = 400
    SH = round(SW * gh / gw)
    pad, hd, ft = 12, 24, 24
    W, H = SW + pad * 2, SH + pad * 2 + hd + ft
    sx, sy = pad, pad + hd
    bezel = "#0b0a09" if theme == "dark" else "#1a1613"
    dim = "#8a7a6a"
    amber = pal["line"] if theme == "dark" else "#ffb35c"
    red = "#ff4d3a"
    css = [".rec{animation:rec 1.2s steps(1) infinite}@keyframes rec{50%{opacity:.15}}",
           ".rl{animation:rl 7s steps(84,end) infinite}@keyframes rl{from{transform:translateY(-60px)}to{transform:translateY(%dpx)}}" % (SH + 60),
           ".fk{opacity:0;animation:fk 6s steps(1,end) infinite}@keyframes fk{0%,93%,100%{opacity:0}94%{opacity:.08}95%{opacity:0}96.5%{opacity:.05}}"]
    b64 = base64.b64encode(raw).decode()
    o = [svg_open(W, H, "Observation feed"), "<defs>",
         f'<clipPath id="scr"><rect x="{sx}" y="{sy}" width="{SW}" height="{SH}" rx="10"/></clipPath>',
         '<pattern id="sl" width="3" height="3" patternUnits="userSpaceOnUse"><rect width="3" height="1" fill="#000" opacity=".22"/></pattern>',
         f'<radialGradient id="vg" cx=".5" cy=".5" r=".72"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".6"/></radialGradient>',
         f'<radialGradient id="gls" cx=".3" cy=".15" r=".7"><stop offset="0" stop-color="#fff" stop-opacity=".09"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/></radialGradient>',
         f'<linearGradient id="tint" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff9d4d" stop-opacity=".05"/><stop offset="1" stop-color="#ff9d4d" stop-opacity=".09"/></linearGradient>',
         f'<linearGradient id="rb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".05"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>',
         "</defs>"]
    o.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="{bezel}" stroke="{ex["panel_s"] if theme == "dark" else "#3a322d"}"/>')
    # header
    o.append(f'<circle class="rec" cx="{pad+5}" cy="{pad+hd/2-1}" r="4" fill="{red}"/>')
    o.append(text(pad + 15, pad + hd / 2 + 2.5, "REC  //  OBSERVATION FEED", amber, 10, extra='letter-spacing="2"'))
    o.append(text(W - pad, pad + hd / 2 + 2.5, "CAM-02  \u00b7  FUTURE GADGET LAB", dim, 9, "end", extra='letter-spacing="1.5"'))
    # screen
    o.append(f'<rect x="{sx-1}" y="{sy-1}" width="{SW+2}" height="{SH+2}" rx="11" fill="#000"/>')
    o.append(f'<g clip-path="url(#scr)">')
    o.append(f'<image x="{sx}" y="{sy}" width="{SW}" height="{SH}" preserveAspectRatio="xMidYMid slice" href="data:image/gif;base64,{b64}"/>')
    o.append(f'<rect x="{sx}" y="{sy}" width="{SW}" height="{SH}" fill="url(#tint)"/>')
    o.append(f'<rect x="{sx}" y="{sy}" width="{SW}" height="{SH}" fill="url(#sl)"/>')
    o.append(f'<rect class="rl" x="{sx}" y="{sy}" width="{SW}" height="50" fill="url(#rb)"/>')
    o.append(f'<rect class="fk" x="{sx}" y="{sy}" width="{SW}" height="{SH}" fill="#fff"/>')
    o.append(f'<rect x="{sx}" y="{sy}" width="{SW}" height="{SH}" fill="url(#vg)"/>')
    o.append(f'<rect x="{sx}" y="{sy}" width="{SW}" height="{SH}" fill="url(#gls)"/>')
    # corner brackets
    L = 12
    for cx, cy, dx, dy in ((sx + 8, sy + 8, 1, 1), (sx + SW - 8, sy + 8, -1, 1), (sx + 8, sy + SH - 8, 1, -1), (sx + SW - 8, sy + SH - 8, -1, -1)):
        o.append(f'<path d="M{cx} {cy+dy*L} V{cy} H{cx+dx*L}" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1.2"/>')
    o.append("</g>")
    o.append(f'<rect x="{sx}" y="{sy}" width="{SW}" height="{SH}" rx="10" fill="none" stroke="#000" stroke-opacity=".8" stroke-width="2"/>')
    # footer
    fy = sy + SH + ft / 2 + 4
    o.append(text(pad, fy, "2010-07-28  11:56", dim, 9, extra='letter-spacing="1.5"'))
    o.append(text(W - pad, fy, "WORLD LINE 1.048596", amber, 9, "end", extra='letter-spacing="1.5"'))
    o.insert(3, "<style>" + "".join(css) + "</style>")
    o.append("</svg>")
    return "\n".join(o)


STYLES = {"title": title, "feed": feed, "footer": footer, "monitor": monitor, "gadgets": gadget_list, "stack": stack, "worldlines": worldlines, "dmail": dmail, "labfile": labfile, "phonewave": phonewave, "steiner": steiner}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", choices=STYLES, required=True)
    ap.add_argument("--user", default="yubinex")
    ap.add_argument("--data", help="use cached data json instead of fetching")
    ap.add_argument("--save-data", help="write the fetched data to this file")
    ap.add_argument("--out-dark", required=True)
    ap.add_argument("--out-light", required=True)
    ap.add_argument("--gif", default=GIF_PATH, help="GIF embedded by the monitor style")
    a = ap.parse_args()
    globals()["GIF_PATH"] = a.gif
    if a.data:
        d = json.load(open(a.data))
    elif a.style == "monitor":
        d = {}
    else:
        d = sg_data.collect(a.user, os.environ.get("GITHUB_TOKEN"))
    d.setdefault("user", a.user)
    if a.save_data:
        json.dump(d, open(a.save_data, "w"))
    for theme, path in (("dark", a.out_dark), ("light", a.out_light)):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        svg = STYLES[a.style](d, theme)
        open(path, "w").write(svg)
        print(f"wrote {path} ({len(svg)//1024} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
