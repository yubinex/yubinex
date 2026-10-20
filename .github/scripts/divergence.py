#!/usr/bin/env python3
"""Animated nixie divergence meter (CSS only). Reuses glyph paths from the static meter."""
import random, re, sys

src = open(sys.argv[1]).read()
out_path = sys.argv[2]
defs_glyphs = re.search(r'<defs><path id="d0".*?</defs>', src, re.S).group(0)
head_defs = re.search(r'<defs>\n<linearGradient.*?</defs>', src, re.S).group(0)
# per-digit x offset relative to tube x, from the static file
off = {}
for m in re.finditer(r'<rect x="(\d+)" y="14" width="46".*?(?=<rect x="\d+" y="18")', src, re.S):
    tx = int(m.group(1))
    for d, x in re.findall(r'href="#d(\d)" class="lit" transform="translate\(([\d.]+) 81', m.group(0)):
        off[int(d)] = round(float(x) - tx, 2)
assert len(off) == 10, off
S = "scale(0.03228 -0.03228)"
TUBES = [14, 74, 128, 182, 236, 290, 344]
MAIN, ALTS = "1048596", ["0571024", "0337187"]
P = 24.0  # full period: two ~12 s halves, each with one world-line shift
rnd = random.Random(1048596)

# timeline per tube: list of (start, end, digit)
tl = [[] for _ in TUBES]
def scramble(t0, lock, step, final, until):
    for i in range(7):
        t = t0
        lt = lock(i)
        while t < lt:
            tl[i].append((t, min(t + step, lt), rnd.randrange(10)))
            t += step
        tl[i].append((lt, until, int(final[i])))
scramble(0.0, lambda i: 0.35 + i * 0.27, 0.08, MAIN, 7.8)
scramble(7.8, lambda i: 8.15 + i * 0.05, 0.06, ALTS[0], 9.5)
scramble(9.5, lambda i: 9.85 + i * 0.05, 0.06, MAIN, 19.8)
scramble(19.8, lambda i: 20.15 + i * 0.05, 0.06, ALTS[1], 21.5)
scramble(21.5, lambda i: 21.85 + i * 0.05, 0.06, MAIN, P)

pc = lambda t: f"{t / P * 100:.3f}".rstrip("0").rstrip(".") + "%"  # noqa: E731
css = [
    ".gh{fill:none;stroke:#2e2824;stroke-width:34;opacity:.55}",
    ".lit{fill:none;stroke:#ff9d4d;stroke-width:49.57;stroke-linejoin:round}",
    ".core{fill:none;stroke:#ffe2bf;stroke-width:22.31;opacity:.85}",
    ".dg{opacity:0}",
    # warm cathode glow breathing; shifts dim the whole display briefly
    "@keyframes br{0%,100%{opacity:.75}50%{opacity:1}}.wm{animation:br 3.2s ease-in-out infinite}",
]
# global flicker during world-line shifts
fk = []
for a in (7.8, 9.5, 19.8, 21.5):
    fk += [f"{pc(a)}{{opacity:1}}", f"{pc(a+0.05)}{{opacity:.35}}", f"{pc(a+0.12)}{{opacity:1}}",
           f"{pc(a+0.2)}{{opacity:.5}}", f"{pc(a+0.3)}{{opacity:1}}"]
css.append("@keyframes sh{0%,100%{opacity:1}" + "".join(fk) + f"}}.sh{{animation:sh {P}s steps(1,end) infinite}}")

o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 404 112" width="404" height="112" role="img" aria-label="Divergence 1.048596">',
     head_defs, defs_glyphs, "<style>@@CSS@@</style>",
     '<rect x="0.5" y="0.5" width="403" height="111" rx="12" fill="#0b0a09" stroke="#2a2522"/>']
kid = 0
for i, tx in enumerate(TUBES):
    o.append("<g>")
    o.append(f'<rect x="{tx}" y="14" width="46" height="84" rx="14" fill="url(#glass)" stroke="#3a322d" stroke-width="1"/>')
    o.append(f'<rect x="{tx+5}" y="22" width="36" height="68" rx="8" fill="url(#mesh)" opacity=".6"/>')
    # stacked cathodes, like a real nixie
    for d in (1, 7, 4, 3, 0, 6, 9, 2, 5, 8):
        o.append(f'<use href="#d{d}" class="gh" transform="translate({tx+off[d]:.2f} 81) {S}"/>')
    o.append(f'<rect class="wm" style="animation-delay:-{rnd.uniform(0,3):.2f}s" x="{tx}" y="14" width="46" height="84" rx="14" fill="url(#warm)"/>')
    # small per-tube cathode flicker
    fa = rnd.uniform(3, 7)
    css.append(f"@keyframes f{i}{{0%,{fa:.1f}%,{fa+0.6:.1f}%,100%{{opacity:1}}{fa+0.2:.1f}%{{opacity:.6}}{fa+0.4:.1f}%{{opacity:.9}}}}"
               f".f{i}{{animation:f{i} {rnd.uniform(5,9):.1f}s infinite}}")
    o.append(f'<g class="sh"><g class="f{i}" filter="url(#glow)">')
    by_d = {}
    for a, b, d in tl[i]:
        if b > a:
            by_d.setdefault(d, []).append((a, b))
    for d, iv in sorted(by_d.items()):
        # merge touching intervals
        iv.sort()
        m = [list(iv[0])]
        for a, b in iv[1:]:
            if a <= m[-1][1] + 1e-6:
                m[-1][1] = max(m[-1][1], b)
            else:
                m.append([a, b])
        kf = ["0%{opacity:0}"]
        for a, b in m:
            kf.append(f"{pc(a)}{{opacity:1}}")
            if b < P - 1e-6:
                kf.append(f"{pc(b)}{{opacity:0}}")
        if m[0][0] == 0:
            kf[0] = "0%{opacity:1}"
        k = f"k{kid}"; kid += 1
        css.append(f"@keyframes {k}{{{''.join(kf[0:1] + [x for x in kf[1:] if not x.startswith('0%')])}}}.{k}{{animation:{k} {P}s steps(1,end) infinite}}")
        t = f"translate({tx+off[d]:.2f} 81) {S}"
        o.append(f'<g class="dg {k}"><use href="#d{d}" class="lit" transform="{t}"/><use href="#d{d}" class="core" transform="{t}"/></g>')
    o.append("</g></g>")
    o.append(f'<rect x="{tx+4}" y="18" width="5.5" height="76" rx="2" fill="#ffffff" opacity=".05"/>')
    o.append("</g>")
    if i == 0:
        o.append('<g class="sh" filter="url(#glow)"><circle cx="67.00" cy="78.50" r="2.8" fill="#ff9d4d"/><circle cx="67.00" cy="78.50" r="1.2" fill="#ffe2bf"/></g>')
o.append("</svg>")
svg = "\n".join(o).replace("@@CSS@@", "".join(css))
open(out_path, "w").write(svg)
print(f"wrote {out_path} ({len(svg)//1024} KB)")
