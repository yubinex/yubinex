"""Guard the assets actually loaded by the README, not the legacy experiments."""
from pathlib import Path
import copy
import json
import re
import unittest
import xml.etree.ElementTree as ET

from static_profile import DATA, NAV, contribution_worldlines, language_inventory, render, render_nav, render_readme

ROOT = Path(__file__).resolve().parents[2]


class StaticProfileTests(unittest.TestCase):
    def test_artwork_is_reproducible_and_inexpensive(self):
        for theme in ("dark", "light"):
            with self.subTest(theme=theme):
                asset = ROOT / "assets" / f"lab-{theme}.svg"
                source = asset.read_text()
                self.assertEqual(source, render(theme))
                self.assertLess(asset.stat().st_size, 24_000)
                tree = ET.fromstring(source)
                self.assertEqual(tree.get("viewBox"), "0 0 880 1650")
                self.assertLess(len(list(tree.iter())), 240)
                forbidden = {"filter", "image", "script", "style", "foreignObject", "set"}
                for node in tree.iter():
                    tag = node.tag.rsplit("}", 1)[-1]
                    self.assertNotIn(tag, forbidden)
                    self.assertFalse(tag.startswith("animate"))
                    self.assertFalse(any(k.startswith("on") or k.endswith("href") for k in node.attrib))
                self.assertNotIn("data:", source)

    def test_readme_loads_one_dossier_and_three_static_controls(self):
        source = (ROOT / "README.md").read_text()
        dossier = source.split("</p>", 1)[0]
        self.assertNotIn("<a ", dossier)
        self.assertEqual(source.count('<a href="https://yubinex.github.io/yubinex-web/">'), 1)
        self.assertEqual(source.count("<picture>"), 4)
        self.assertEqual(source.count("<img "), 4)
        images = re.findall(r'(?:src|srcset)="([^"]+)"', source)
        self.assertEqual(len(images), 12)
        expected = {f"lab-{theme}.svg" for theme in ("dark", "light")}
        expected.update(f"lab-nav-{key}-{theme}.svg" for key, *_ in NAV for theme in ("dark", "light"))
        for url in images:
            name = url.split("/assets/")[1].split("?")[0]
            self.assertIn(name, expected)
            self.assertTrue((ROOT / "assets" / name).is_file())
        self.assertNotRegex(source, r'!\[|<script|<iframe|\.gif|<video')

    def test_footer_controls_are_small_static_and_theme_matched(self):
        readme = (ROOT / "README.md").read_text()
        for theme in ("dark", "light"):
            for key, title, _, url in NAV:
                source = (ROOT / "assets" / f"lab-nav-{key}-{theme}.svg").read_text()
                self.assertEqual(source, render_nav(theme, key))
                self.assertLess(len(source.encode()), 1800)
                tree = ET.fromstring(source)
                self.assertEqual(tree.get("viewBox"), "0 0 270 68")
                for node in tree.iter():
                    tag = node.tag.rsplit("}", 1)[-1]
                    self.assertIn(tag, {"svg", "title", "rect", "path", "text"})
                    self.assertFalse(any(k.startswith("on") or k.endswith("href") for k in node.attrib))
                self.assertIn(title, source)
                self.assertIn(url, readme)
        self.assertIn("<summary><samp>[ FILE / TEXT MODE ]", readme)
        self.assertIn("```text\nOPERATOR", readme)

    def test_transcript_matches_snapshot_and_all_sections_exist(self):
        data = json.loads(DATA.read_text())
        self.assertEqual((ROOT / "README.md").read_text(), render_readme(data))
        tree = ET.fromstring(render("dark", data))
        labels = [n.text for n in tree.iter() if n.tag.endswith("}text")]
        for section in ("LAB MEMBER FILE", "WORLD LINE OBSERVATION", "CURRENT EXPERIMENTS", "LAB EQUIPMENT"):
            self.assertIn(section, labels)
        self.assertNotIn("D-MAIL INBOX", labels)
        for repo in data["projects"]:
            self.assertIn(repo["name"], render_readme(data))

    def test_empty_activity_and_special_characters(self):
        data = copy.deepcopy(json.loads(DATA.read_text()))
        data.update(cells=[], languages=[], projects=[])
        ET.fromstring(render("light", data))
        self.assertIn("No language metadata", render_readme(data))
        data["projects"] = [dict(name="lab", language="C++", description='A <lab> & "test"')]
        source = render("dark", data)
        ET.fromstring(source)
        self.assertIn("A &lt;lab&gt; &amp; &quot;test&quot;", source)

    def test_inventory_counts_only_public_nonfork_primary_languages(self):
        repos = [dict(private=False, fork=False, language=language)
                 for language in ("Python", "Python", "QML", "JavaScript", None)]
        repos += [dict(private=True, fork=False, language="Secret"),
                  dict(private=False, fork=True, language="Forked")]
        self.assertEqual(language_inventory(repos), [("Python", 2), ("JavaScript", 1), ("QML", 1)])

    def test_worldline_geometry_encodes_actual_weekly_contributions(self):
        data = copy.deepcopy(json.loads(DATA.read_text()))
        data["cells"] = [dict(x=x, date=date, count=count) for x, date, count in (
            (0, "2026-01-01", 10), (0, "2026-01-02", 10),
            (1, "2026-01-08", 0), (2, "2026-02-01", 40))]
        weeks, months, maximum, scale = contribution_worldlines(data["cells"])
        self.assertEqual([w["count"] for w in weeks], [20, 0, 40])
        self.assertEqual(sum(w["count"] for w in weeks), 60)
        self.assertEqual(maximum, 40)
        self.assertEqual(scale, 40)
        self.assertAlmostEqual(833 - weeks[2]["y"], 2 * (833 - weeks[0]["y"]))
        self.assertEqual(weeks[1]["y"], 833)
        self.assertEqual(weeks[0]["root"], weeks[1]["root"])
        self.assertNotEqual(weeks[0]["root"], weeks[2]["root"])
        self.assertEqual(list(months), ["2026-01", "2026-02"])
        tree = ET.fromstring(render("dark", data))
        diagram = next(n for n in tree.iter() if n.get("id") == "worldline-map")
        labels = [n.text for n in diagram.iter() if n.tag.endswith("}text")]
        self.assertIn("JAN", labels)
        self.assertIn("FEB", labels)
        branches = next(n for n in diagram.iter() if n.get("id") == "worldline-branches")
        self.assertEqual(branches.get("d"), " ".join(w["path"] for w in weeks if w["count"]))
        peak = next(n for n in diagram.iter() if n.get("id") == "peak-week")
        self.assertEqual(peak.get("d"), weeks[2]["path"])
        data.update(cells=[], total=0, active_days=0)
        empty_tree = ET.fromstring(render("dark", data))
        empty_diagram = next(n for n in empty_tree.iter() if n.get("id") == "worldline-map")
        self.assertNotEqual(ET.tostring(diagram), ET.tostring(empty_diagram))
        self.assertIn("not commit-only counts", render_readme(data))

    def test_full_year_of_activity_stays_within_payload_budget(self):
        data = copy.deepcopy(json.loads(DATA.read_text()))
        for cell in data["cells"]:
            cell["count"] = 1
        source = render("dark", data)
        self.assertLess(len(source.encode()), 24_000)
        self.assertLess(len(list(ET.fromstring(source).iter())), 240)


if __name__ == "__main__":
    unittest.main()
