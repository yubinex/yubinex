"""Regression checks: python3 -m unittest discover -s .github/scripts -p 'test_*.py'."""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

import sg_graph
from version_panels import version_panels

ROOT = Path(__file__).resolve().parents[2]
NS = {"s": "http://www.w3.org/2000/svg"}


class ProfileTests(unittest.TestCase):
    def test_branch_urls_and_content_invalidation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "assets").mkdir()
            for name in ("hero-dark.svg", "hero-light.svg"):
                (root / "assets" / name).write_text("<svg/>")
            readme = root / "README.md"
            readme.write_text(
                '<source srcset="https://github.com/yubinex/yubinex/raw/master/assets/hero-dark.svg?v=old">\n'
                '<img src="https://raw.githubusercontent.com/yubinex/yubinex/master/assets/hero-light.svg">'
            )
            ref = "perf/profile-performance"
            self.assertTrue(version_panels(root, ref))
            first = readme.read_text()
            self.assertEqual(first.count(f"/{ref}/assets/"), 2)
            self.assertNotIn("/master/", first)
            self.assertFalse(version_panels(root, ref))
            (root / "assets/hero-dark.svg").write_text("<svg>changed</svg>")
            self.assertTrue(version_panels(root, ref))
            self.assertEqual(first.splitlines()[1], readme.read_text().splitlines()[1])
            self.assertTrue(version_panels(root, "master"))
            self.assertNotIn(f"/{ref}/", readme.read_text())

    def test_meter_tiles_and_all_worldline_states(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "meter.svg"
            subprocess.run([sys.executable, str(ROOT / ".github/scripts/divergence.py"),
                            str(ROOT / ".github/scripts/divergence-src.svg"), str(output)], check=True)
            svg = output.read_text()
            root = ET.fromstring(svg)
            images = root.findall(".//s:image", NS)
            self.assertEqual(len(images), 10)
            self.assertTrue(all(i.get("href").startswith("data:image/png;base64,") for i in images))
            states = [g for g in root.findall(".//s:g", NS) if g.get("class", "").startswith("dg ")]
            self.assertEqual(len(states), 70)
            frames = {}
            for name, body in re.findall(r"@keyframes (k\d+)\{((?:[^{}]*\{[^{}]*\})+)\}", svg):
                frames[name] = [(float(t), int(v)) for t, v in re.findall(r"([\d.]+)%\{opacity:([01])\}", body)]
            for seconds, expected in [(6, "1048596"), (8.8, "0571024"), (12, "1048596"),
                                      (21, "0337187"), (23, "1048596")]:
                visible = []
                for g in states:
                    timeline = frames[g.get("class").split()[1]]
                    opacity = [v for t, v in timeline if t <= seconds / 24 * 100][-1]
                    if opacity:
                        visible.append(g.find("s:use", NS).get("href")[-1])
                self.assertEqual("".join(visible), expected)

    def test_graph_dot_has_its_own_filter_group(self):
        cells = [dict(x=x, y=0, date=f"2026-01-{1+x*7:02d}", count=1, level=1) for x in range(2)]
        data = dict(cells=cells, active_days=2, total=2, longest_streak=1, best_day=cells[0])
        for theme in ("dark", "light"):
            root = ET.fromstring(sg_graph.worldlines(data, theme))
            backdrop = root.find("s:image", NS)
            self.assertTrue(backdrop.get("href").startswith("data:image/png;base64,"))
            self.assertEqual(backdrop.find("s:set", NS).get("begin"), "8s")
            hidden = [g for g in root.findall("s:g", NS)
                      if g.find('s:set[@attributeName="display"]', NS) is not None]
            self.assertEqual(len(hidden), 1)
            self.assertEqual(hidden[0].find('s:set[@attributeName="display"]', NS).get("begin"), "8s")
            moving = [g for g in root.findall("s:g", NS) if g.find(".//s:animateMotion", NS) is not None]
            self.assertEqual(len(moving), 1)
            self.assertEqual(len(list(moving[0])), 1)
            motion = moving[0].find(".//s:animateMotion", NS)
            self.assertEqual(motion.get("calcMode"), "discrete")
            self.assertEqual(len(motion.get("keyTimes").split(";")), 76)

    def test_readme_cache_keys_match_branch_assets(self):
        text = (ROOT / "README.md").read_text()
        ref = os.environ.get("GITHUB_REF_NAME") or subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True
        ).strip() or "master"
        matches = re.findall(r'/' + re.escape(ref) + r'/assets/([\w-]+\.svg)\?v=([a-f0-9]{16})', text)
        self.assertEqual(len(matches), 15)
        for name, version in matches:
            self.assertEqual(hashlib.sha256((ROOT / "assets" / name).read_bytes()).hexdigest()[:16], version)


if __name__ == "__main__":
    unittest.main()
