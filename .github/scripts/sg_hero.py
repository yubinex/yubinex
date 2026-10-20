#!/usr/bin/env python3
"""Compose the hero row (divergence meter + title on the left, observation monitor on the right)
into ONE SVG so it scales as a unit. Each part keeps its own CSS animation; ids, classes and
keyframes are namespaced so the merged styles cannot collide.

Usage: sg_hero.py --meter m.svg --title t.svg --monitor mon.svg --out hero.svg
"""
import argparse, re

W, H = 880, 300


def namespace(svg, p):
    ids = set(re.findall(r'\bid="([^"]+)"', svg))
    classes = set()
    for c in re.findall(r'\bclass="([^"]+)"', svg):
        classes.update(c.split())
    kfs = set(re.findall(r"@keyframes\s+([\w-]+)", svg))

    def anim(decl):  # rename keyframe names inside animation / animation-name values
        return re.sub(r"(animation(?:-name)?\s*:\s*)([^;}\"]+)",
                      lambda m: m[1] + re.sub(r"[A-Za-z_][\w-]*",
                                              lambda t: p + t[0] if t[0] in kfs else t[0], m[2]), decl)

    def css(block):
        block = re.sub(r"@keyframes\s+([\w-]+)", lambda m: "@keyframes " + p + m[1], block)
        block = re.sub(r"\.([A-Za-z_][\w-]*)", lambda m: "." + p + m[1] if m[1] in classes else m[0], block)
        block = re.sub(r"#([A-Za-z_][\w-]*)(?![\w-])", lambda m: "#" + p + m[1] if m[1] in ids else m[0], block)
        return anim(block)

    svg = re.sub(r"<style>(.*?)</style>", lambda m: "<style>" + css(m[1]) + "</style>", svg, flags=re.S)
    svg = re.sub(r'\bstyle="([^"]*)"', lambda m: 'style="' + anim(m[1]) + '"', svg)
    svg = re.sub(r'\bid="([^"]+)"', lambda m: f'id="{p}{m[1]}"', svg)
    svg = re.sub(r"url\(#([\w-]+)\)", lambda m: f"url(#{p}{m[1]})" if m[1] in ids else m[0], svg)
    svg = re.sub(r'((?:xlink:)?href)="#([\w-]+)"', lambda m: f'{m[1]}="#{p}{m[2]}"' if m[2] in ids else m[0], svg)
    svg = re.sub(r'\bclass="([^"]+)"', lambda m: 'class="' + " ".join(p + c for c in m[1].split()) + '"', svg)
    return svg


def inner(svg):
    m = re.search(r"<svg\b[^>]*>", svg)
    vb = re.search(r'viewBox="([^"]+)"', m[0])[1]
    body = svg[m.end():svg.rindex("</svg>")]
    return vb, body


def place(svg, p, x, y, w):
    vb, body = inner(namespace(svg, p))
    vw, vh = [float(v) for v in vb.split()[2:]]
    h = w * vh / vw
    return f'<svg x="{x:g}" y="{y:g}" width="{w:g}" height="{h:.2f}" viewBox="{vb}" overflow="visible">{body}</svg>', h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meter", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--monitor", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    meter, title, mon = (open(f).read() for f in (a.meter, a.title, a.monitor))
    # right column: monitor at native size, vertically centred
    mv = [float(v) for v in inner(mon)[0].split()[2:]]
    mx, my = W - mv[0] - 2, (H - mv[1]) / 2
    right, _ = place(mon, "mo-", mx, my, mv[0])
    # left column: meter above title, centred in the space left of the monitor
    col = mx - 16
    mw, tw, gap = 380, 430, 22
    mh = mw * 112 / 404
    tvb = [float(v) for v in inner(title)[0].split()[2:]]
    th = tw * tvb[1] / tvb[0]
    top = (H - (mh + gap + th)) / 2
    left_m, _ = place(meter, "dv-", (col - mw) / 2, top, mw)
    left_t, _ = place(title, "ti-", (col - tw) / 2, top + mh + gap, tw)
    out = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'role="img" aria-label="Divergence 1.048596. Hi, I\'m yubinex. Observation feed.">\n'
           f"{left_m}\n{left_t}\n{right}\n</svg>\n")
    open(a.out, "w").write(out)
    print(f"wrote {a.out} ({len(out) // 1024} KB)")


if __name__ == "__main__":
    main()
