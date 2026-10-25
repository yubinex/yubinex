#!/usr/bin/env python3
"""Rebuild cached 2x nixie tiles: python .github/scripts/nixie_tiles.py.

Requires rsvg-convert (librsvg2-bin) only when rebuilding. The meter generator
uses image_defs(), which needs only the standard library and cached PNGs.
"""
import argparse
import base64
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TILE_DIR = ROOT / "assets/nixie-digits"
# Tube-local coordinates, with generous transparent space for both glow lobes.
X, Y, W, H = -32, -32, 110, 176
SCALE = 2


def image_defs():
    images = []
    for digit in range(10):
        path = TILE_DIR / f"{digit}.png"
        if not path.is_file():
            raise SystemExit(f"Missing {path}; run .github/scripts/nixie_tiles.py")
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        images.append(f'<image id="tile{digit}" x="{X}" y="{Y}" width="{W}" height="{H}" href="data:image/png;base64,{data}"/>')
    return "<defs>" + "".join(images) + "</defs>"


def rebuild(source, output):
    src = source.read_text()
    glyphs = re.search(r'<defs><path id="d0".*?</defs>', src, re.S).group(0)
    head = re.search(r'<defs>\n<linearGradient.*?</defs>', src, re.S).group(0)
    offsets = {}
    for match in re.finditer(r'<rect x="(\d+)" y="14" width="46".*?(?=<rect x="\d+" y="18")', src, re.S):
        for digit, x in re.findall(r'href="#d(\d)" class="lit" transform="translate\(([\d.]+) 81', match.group(0)):
            offsets[int(digit)] = round(float(x) - int(match[1]), 2)
    if set(offsets) != set(range(10)):
        raise ValueError("Source must provide all ten glyph offsets")
    output.mkdir(parents=True, exist_ok=True)
    for digit in range(10):
        # Retain the original shared object bounding box: opacity-zero siblings
        # still contribute geometry, unlike display:none or omitted glyphs.
        states = []
        for d in range(10):
            transform = f"translate({offsets[d]:.2f} 81) scale(0.03228 -0.03228)"
            states.append(f'<g opacity="{int(d == digit)}"><use href="#d{d}" class="lit" transform="{transform}"/><use href="#d{d}" class="core" transform="{transform}"/></g>')
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="{X} {Y} {W} {H}">'
               + head + glyphs
               + '<style>.lit{fill:none;stroke:#ff9d4d;stroke-width:49.57;stroke-linejoin:round}.core{fill:none;stroke:#ffe2bf;stroke-width:22.31;opacity:.85}</style>'
               + '<g filter="url(#glow)">' + "".join(states) + '</g></svg>')
        subprocess.run(["rsvg-convert", "--width", str(W * SCALE), "--height", str(H * SCALE),
                        "--output", str(output / f"{digit}.png")], input=svg.encode(), check=True)
    print(f"Wrote ten {W * SCALE}x{H * SCALE} transparent tiles to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).with_name("divergence-src.svg"))
    parser.add_argument("--out", type=Path, default=TILE_DIR)
    args = parser.parse_args()
    rebuild(args.source, args.out)
