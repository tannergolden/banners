# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every element, every variant, every theme and print: well formed, within budget, deterministic, and the
kit's command line doing what it says: render, check drift, prune, fill blocks, measure into a lock."""
from __future__ import annotations

import contextlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
import xml.dom.minidom as minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from elementskit import elements as E  # noqa: E402
from elementskit import layout as L  # noqa: E402
from elementskit import measure as M  # noqa: E402
from bannerkit.canvas import lint  # noqa: E402

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("elements_kit", ROOT / "src" / "elements-kit.py")
K = importlib.util.module_from_spec(spec)
spec.loader.exec_module(K)

SPECIMEN = ROOT / "examples" / "driftmark"
DATA = K.load_data(SPECIMEN / ".github" / "elements.yml")
LOCK = {"measured": {}}
DASHES = ("–", "—", "―")


def run(argv) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = K.main(argv)
    return code, buf.getvalue()


class EveryFile(unittest.TestCase):
    """The specimen's every element in every variant, theme and print."""

    def test_every_variant_and_theme_is_well_formed_within_budget_and_deterministic(self):
        for eid, d in K.merged(DATA, LOCK).items():
            kind = d["kind"]
            for variant in E.variants(kind, d):
                for theme in ("day", "dark"):
                    svg = E.draw(kind, d, "blueprint", theme, variant)
                    minidom.parseString(svg)
                    self.assertEqual(svg, E.draw(kind, d, "blueprint", theme, variant), (eid, variant, theme))
                    self.assertIn('role="img"', svg)
                    self.assertIn("<title", svg)
                    self.assertNotIn("<text", svg, "lettering must be paths")
                    self.assertEqual(lint(svg, budget=E.BUDGET[E.KINDS[kind][2]]), [], (eid, variant, theme))
                    for ch in DASHES:
                        self.assertNotIn(ch, svg)

    def test_every_print_draws_every_element(self):
        for tone in E.PRINTS:
            for eid, d in K.merged(DATA, LOCK).items():
                svg = E.draw(d["kind"], d, tone, "day", "wide")
                self.assertEqual(lint(svg, budget=E.BUDGET[E.KINDS[d["kind"]][2]]), [], (eid, tone))

    def test_narrow_files_are_phone_wide_and_wide_files_page_wide(self):
        for eid, d in K.merged(DATA, LOCK).items():
            kind = d["kind"]
            vs = E.variants(kind, d)
            for variant in vs:
                w = int(re.search(r'width="(\d+)"', E.draw(kind, d, "blueprint", "day", variant)).group(1))
                if variant == "narrow":
                    self.assertLessEqual(w, 404, (eid, variant))
                elif variant in ("wide", "still") and kind not in ("placard", "seal"):
                    self.assertEqual(w, 830, (eid, variant))

    def test_night_lettering_follows_the_print(self):
        d = K.merged(DATA, LOCK)["how-it-runs"]
        self.assertIn("#000000", E.draw("schematic", d, "orangeprint", "dark", "wide"))
        self.assertNotIn("#000000", E.draw("schematic", d, "blueprint", "dark", "wide"))


class Elements(unittest.TestCase):
    """Behaviours the drawings promise."""

    def test_a_character_no_face_has_is_spelled_plainly_or_marked(self):
        E.WARNINGS.clear()
        # The mono face has an ellipsis; it has no arrow and no accented e, which get their plain spellings.
        self.assertEqual(E.plain("done \u2026 \u2192 next \u00e9", "mono"), "done \u2026 -> next e")
        self.assertEqual(E.WARNINGS, [])
        self.assertEqual(E.plain("\u6f22", "mono"), "?")
        self.assertTrue(E.WARNINGS)

    def test_counters_show_every_digit(self):
        d = dict(K.merged(DATA, LOCK)["vitals"], counters=[["TESTS", 2241], ["A", 7], ["B", 12345]])
        svg = E.draw("instruments", d, "blueprint", "day", "wide")
        # Four digits get four cells; a five-digit count is shown in thousands.
        self.assertEqual(len(re.findall(r'<rect x="\d+" y="252" width="18" height="28" rx="2"', svg)), 4 + 3 + 3)
        self.assertEqual(lint(svg, budget=E.BUDGET["sheet"]), [])

    def test_plan_puts_the_lobby_on_the_bottom_wall_and_reaches_every_room(self):
        d = K.merged(DATA, LOCK)["layout"]
        for narrow in (False, True):
            x0, y0, x1 = (24, 84, 336) if narrow else (48, 86, 782)
            rooms, spec, ph = E._plan_rooms(d, narrow, x0, y0, x1)
            lobby = next(r for r in rooms if r.key == "lobby")
            self.assertAlmostEqual(lobby.y + lobby.h, y0 + ph, delta=1)
            doors = L.doors(rooms)
            self.assertEqual(len(doors), len(rooms) - 1, "a spanning tree of doors")
            # No two rooms overlap, and together they fill the plan.
            area = sum(r.w * r.h for r in rooms)
            self.assertAlmostEqual(area, (x1 - x0) * ph, delta=4 * len(rooms))

    def test_schematic_wires_never_cross_a_box(self):
        d = K.merged(DATA, LOCK)["how-it-runs"]
        keys = list(d["boxes"])
        boxes = [L.Box(k) for k in keys]
        edges = [(a, b) for a, b, *_ in d["wires"]]
        L.snake(boxes, edges, left=46, top=118, width=738, per_row=3, box_w=224, box_h=52, gap_x=72, gap_y=64)
        by = {b.key: b for b in boxes}
        for a, b, *_ in d["wires"]:
            pts = L.route(by[a], by[b], 72, boxes)
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                self.assertFalse(L._crosses(x0, y0, x1, y1, boxes, (a, b)), (a, b, pts))

    def test_a_plan_with_one_room_and_a_schematic_with_a_cycle_still_draw(self):
        one = {"kind": "plan", "subject": "x/y", "total": 3,
               "rooms": [{"key": "src", "label": "SRC/", "count": 2, "lines": [["a.py", ""], ["b.py", ""]]}],
               "lobby": {"count": 1, "lines": [["README.md", ""]]}}
        many = {"kind": "plan", "subject": "x/y", "total": 900,
                "rooms": [{"key": f"r{i}", "label": f"ROOM-{i}/", "count": 10 + 40 * i,
                           "lines": [[f"file-{j}.py", j] for j in range(9)]} for i in range(8)],
                "lobby": {"count": 3, "lines": [["README.md", ""]]},
                "closets": [{"label": f"C{i}/", "count": i + 1} for i in range(6)]}
        cyc = {"kind": "schematic", "subject": "x/y",
               "boxes": {"a": {"title": "A", "path": "a"}, "b": {"title": "B", "path": "b"}, "c": {"title": "C", "path": "c"}},
               "wires": [["a", "b", "ONE"], ["b", "c", "TWO"], ["c", "a", "BACK"]]}
        for kind, d in (("plan", one), ("plan", many), ("schematic", cyc)):
            for variant in ("wide", "narrow"):
                svg = E.draw(kind, d, "blueprint", "day", variant)   # draw lints and budgets, and raises if either fails
                minidom.parseString(svg)
        for narrow in (False, True):
            x0, y0, x1 = (24, 84, 336) if narrow else (48, 86, 782)
            rooms, _, _ = E._plan_rooms(one, narrow, x0, y0, x1)
            self.assertEqual({r.key for r in rooms}, {"src", "lobby"})
            self.assertEqual(len(L.doors(rooms)), 1)
        self.assertEqual(L.layers(["a", "b", "c"], [("a", "b"), ("b", "c"), ("c", "a")]), {"a": 0, "b": 1, "c": 2})

    def test_timeline_cuts_only_a_quiet_stretch_and_keeps_the_scale_monotonic(self):
        import datetime as dt
        s = L.timeline(dt.date(2026, 7, 22), dt.date(2026, 10, 8),
                       [dt.date(2026, 7, 25), dt.date(2026, 7, 27), dt.date(2026, 9, 24)], 46, 784)
        self.assertEqual(len(s.breaks), 1)
        xs = [s.x(dt.date(2026, 7, 22) + dt.timedelta(days=i)) for i in range(0, 78, 3)]
        self.assertEqual(xs, sorted(xs))
        self.assertLess(s.x(dt.date(2026, 7, 27)) - s.x(dt.date(2026, 7, 25)), 80)
        dates = [E._date(e["date"]) for e in DATA["elements"]["history"]["events"]]
        s2 = L.timeline(dt.date(2025, 3, 1), dt.date(2026, 12, 15), dates, 46, 784)
        self.assertEqual(s2.breaks, [], "fourteen releases over eighteen months leave nothing quiet enough to cut")
        s3 = L.timeline(dt.date(2025, 3, 1), dt.date(2026, 12, 15), [dt.date(2025, 4, 2), dt.date(2026, 9, 18)], 46, 784)
        self.assertEqual(len(s3.breaks), 1, "two marks seventeen months apart do")
        inside = s3.x(dt.date(2026, 1, 1))
        self.assertTrue(s3.breaks[0][0] <= inside <= s3.breaks[0][1], "a date in the cut lands on the break")

    def test_alt_text_comes_from_the_data(self):
        d = K.merged(DATA, LOCK)["how-it-runs"]
        self.assertTrue(E.alt("schematic", d).startswith("Schematic of driftmark"))
        self.assertEqual(E.alt("seal", {"alt": "The seal"}), "The seal")

    def test_a_ring_shrinks_to_fit_its_arc(self):
        d = dict(K.merged(DATA, LOCK)["conformance"], ring_top="A VERY MUCH LONGER RING OF LETTERING THAN THE ARC HAS ROOM FOR")
        svg = E.draw("certificate", d, "blueprint", "day", "wide")
        self.assertEqual(lint(svg, budget=E.BUDGET["sheet"]), [])


class Cli(unittest.TestCase):
    """render, check, snippets and measure, on a copy of the specimen."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        shutil.copytree(SPECIMEN, self.root, ignore=shutil.ignore_patterns("assets", "*.html", "*.png"))
        (self.root / "assets").mkdir()
        self.out = self.root / "assets" / "elements"
        self.readme = self.root / "README.md"

    def tearDown(self):
        self.tmp.cleanup()

    def kit(self, *args):
        return run([*args, "--root", str(self.root)])

    def test_render_then_check_passes(self):
        code, out = self.kit("render")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(list(self.out.glob("*.svg"))), 30)
        self.assertEqual(self.kit("check")[0], 0)

    def test_render_is_idempotent(self):
        self.kit("render")
        before = {p.name: p.read_bytes() for p in self.out.glob("*.svg")}
        text = self.readme.read_text()
        self.kit("render")
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.out.glob("*.svg")})
        self.assertEqual(text, self.readme.read_text())

    def test_check_names_a_stale_file_an_orphan_and_a_stale_block(self):
        self.kit("render")
        (self.out / "survey-day.svg").write_text("<svg/>")
        code, out = self.kit("check")
        self.assertEqual(code, 1)
        self.assertIn("survey-day.svg", out)
        self.kit("render")
        (self.out / "gone.svg").write_text("<svg/>")
        code, out = self.kit("check")
        self.assertEqual(code, 1)
        self.assertIn("gone.svg (orphaned)", out)
        self.kit("render")
        self.assertFalse((self.out / "gone.svg").exists(), "render prunes what no element writes")
        text = self.readme.read_text()
        a = text.index("<!-- elements:vitals:start -->")
        self.readme.write_text(text[:a] + "<!-- elements:vitals:start -->\nstale\n" + text[text.index("<!-- elements:vitals:end -->"):])
        code, out = self.kit("check")
        self.assertEqual(code, 1)
        self.assertIn("README.md blocks", out)

    def test_another_kit_version_is_a_notice_not_a_failure(self):
        self.kit("render")
        p = self.out / "history-day.svg"
        p.write_text(p.read_text().replace(f"elements v{E.KIT_VERSION} ", "elements v0 "))
        code, out = self.kit("check")
        self.assertEqual(code, 0, out)
        self.assertIn("another kit version", out)

    def test_blocks_carry_every_variant_in_githubs_order(self):
        self.kit("render")
        text = self.readme.read_text()
        block = text[text.index("<!-- elements:how-it-runs:start -->"):text.index("<!-- elements:how-it-runs:end -->")]
        order = [m.group(1) for m in re.finditer(r'(?:srcset|src)="assets/elements/([^"]+)"', block)]
        self.assertEqual(order, ["how-it-runs-narrow-dark.svg", "how-it-runs-narrow-day.svg",
                                 "how-it-runs-dark.svg", "how-it-runs-day.svg"])
        half = text[text.index("<!-- elements:contributors:start -->"):text.index("<!-- elements:contributors:end -->")]
        self.assertNotIn("narrow", half, "a half-page element is one size")
        card = text[text.index("<!-- elements:action:start -->"):text.index("<!-- elements:action:end -->")]
        self.assertIn('<a href="https://github.com/driftmark/action">', card)

    def test_snippets_prints_a_block_per_element_and_writes_nothing(self):
        code, out = self.kit("snippets")
        self.assertEqual(code, 0)
        self.assertEqual(out.count("<!-- elements:"), 22)
        self.assertFalse(self.out.exists())

    def test_a_missing_marker_is_reported_not_silently_skipped(self):
        text = self.readme.read_text()
        a = text.index("<!-- elements:vitals:start -->")
        b = text.index("<!-- elements:vitals:end -->") + len("<!-- elements:vitals:end -->")
        self.readme.write_text(text[:a] + text[b:])
        code, out = self.kit("render")
        self.assertEqual(code, 0)
        self.assertIn("has no markers for: vitals", out)
        self.assertTrue((self.out / "vitals-day.svg").exists(), "the file is still drawn")

    def test_bad_data_fails_with_a_precise_message(self):
        data = self.root / ".github" / "elements.yml"
        text = data.read_text().replace("      - [collector, alerts, PAST THE THRESHOLD]", "      - [collector, alarms, PAST THE THRESHOLD]")
        data.write_text(text)
        code, out = self.kit("render")
        self.assertEqual(code, 1)
        self.assertIn("names a box that is not there: alarms", out)
        data.write_text(data.read_text().replace("kind: roster", "kind: rooster"))
        code, out = self.kit("render")
        self.assertIn("unknown kind 'rooster'", out)

    def test_json_data_needs_no_yaml(self):
        data = K.load_data(self.root / ".github" / "elements.yml")
        (self.root / ".github" / "elements.yml").unlink()
        (self.root / ".github" / "elements.json").write_text(json.dumps(data, default=str))
        saved = sys.modules.get("yaml")
        sys.modules["yaml"] = None
        try:
            code, out = self.kit("render")
        finally:
            if saved is None:
                del sys.modules["yaml"]
            else:
                sys.modules["yaml"] = saved
        self.assertEqual(code, 0, out)

    def test_a_print_in_the_data_file_recolours_everything(self):
        data = self.root / ".github" / "elements.yml"
        data.write_text(data.read_text().replace("print: blueprint", "print: redprint"))
        self.kit("render")
        for p in self.out.glob("*-day.svg"):
            self.assertNotIn("#2F66C6", p.read_text(), p.name)


def bare(root: Path) -> None:
    """This checkout copied to `root` without its own elements, the way a repository looks before its first run."""
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns("assets", "__pycache__", ".cache", "preview", "node_modules"))
    for p in (root / ".github" / "elements.yml", root / ".github" / "elements.lock.json"):
        if p.exists():
            p.unlink()


class Measured(unittest.TestCase):
    """The measuring path, end to end, on a real checkout: this one."""

    def test_init_then_measure_then_render_on_a_bare_checkout(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            bare(root)
            (root / "README.md").write_text("# banners\n\nA line about it.\n")
            code, out = run(["init", "--root", str(root)])
            self.assertEqual(code, 0, out)
            self.assertIn("Wrote .github/elements.yml", out)
            self.assertIn("Added markers to README.md for: vitals, layout, history, contributors, conformance", out)
            data = (root / ".github" / "elements.yml").read_text()
            self.assertIn("subject: tannergolden/banners", data)
            self.assertIn("name: BANNERS", data)
            code, out = run(["init", "--root", str(root)])
            self.assertEqual(code, 0)
            self.assertIn("already there", out)
            self.assertIn("already has every marker", out)
            self.assertEqual(run(["measure", "--root", str(root)])[0], 0)
            code, out = run(["render", "--root", str(root)])
            self.assertEqual(code, 0, out)
            self.assertEqual(run(["check", "--root", str(root)])[0], 0)
            readme = (root / "README.md").read_text()
            self.assertTrue(readme.startswith("# banners\n\nA line about it.\n"), "what was there is kept")
            self.assertEqual(readme.count("<picture>"), 5)
            self.assertNotIn("kit.py", readme)

    def test_run_bootstraps_a_bare_checkout_and_is_quiet_the_second_time(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            bare(root)
            (root / "README.md").write_text("# banners\n")
            msg = Path(td) / "commit.txt"
            code, out = run(["run", "--root", str(root), "--commit-file", str(msg)])
            self.assertEqual(code, 0, out)
            self.assertIn("Wrote .github/elements.yml", out)
            self.assertIn("Something moved", out)
            text = msg.read_text()
            self.assertTrue(text.startswith("chore(elements): \U0001F4D0 draw the elements for tannergolden/banners\n\n"), text)
            self.assertIn("The first run", text)
            self.assertTrue((root / ".github" / "elements.lock.json").exists())
            self.assertEqual(run(["check", "--root", str(root)])[0], 0)
            code, out = run(["run", "--root", str(root), "--commit-file", str(msg)])
            self.assertEqual(code, 0, out)
            self.assertIn("Nothing moved", out)
            self.assertFalse(msg.exists(), "no message when there is nothing to commit")
            # A README block someone deleted by hand comes back, and the commit names the element.
            readme = (root / "README.md").read_text()
            a, b = readme.index("<!-- elements:layout:start -->") + len("<!-- elements:layout:start -->"), readme.index("<!-- elements:layout:end -->")
            (root / "README.md").write_text(readme[:a] + "\n" + readme[b:])
            (root / "assets" / "elements" / "layout-day.svg").unlink()
            code, out = run(["run", "--root", str(root), "--commit-file", str(msg)])
            self.assertEqual(code, 0, out)
            text = msg.read_text()
            self.assertTrue(text.startswith("chore(elements): \U0001F4D0 redraw layout\n"), text)
            self.assertIn("1 block rewritten in README.md", " ".join(text.split()))

    def test_measure_then_render_then_check(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            bare(root)
            (root / "assets").mkdir(exist_ok=True)
            (root / ".github").mkdir(exist_ok=True)
            (root / ".github" / "elements.json").write_text(json.dumps({
                "print": "greenprint", "subject": "tannergolden/banners", "today": "2026-09-25",
                "elements": {
                    "layout": {"kind": "plan", "measure": {}, "entrance": "ENTRANCE  ·  README.MD"},
                    "vitals": {"kind": "instruments", "measure": {"count": {"workflows": ".github/workflows/*.yml",
                                                                              "tests": "tests/test_*.py",
                                                                              "docs": "docs/*.md"}}},
                    "people": {"kind": "roster", "measure": {"rename": {"claude": {"name": "CLAUDE", "handle": "CO-AUTHOR", "initials": "C"}}}},
                    "history": {"kind": "milestones", "measure": {"notable": {"v1.0.0": ["FIRST RELEASE"]}}},
                    "conformance": {"kind": "certificate", "measure": {}, "ring_top": "CONFORMS TO TANNERGOLDEN/STANDARDS",
                                    "ring_bottom": "V1  ·  VERIFIED 25 SEP 2026", "name": "BANNERS"},
                }}))
            (root / "README.md").write_text("# banners\n\n" + "\n\n".join(
                f"<!-- elements:{eid}:start -->\n<!-- elements:{eid}:end -->"
                for eid in ("layout", "vitals", "people", "history", "conformance")) + "\n")
            code, out = run(["render", "--root", str(root)])
            self.assertEqual(code, 1, "measured fields are missing until measure runs")
            self.assertIn("run `elements-kit.py measure` first", out)
            code, out = run(["measure", "--root", str(root)])
            self.assertEqual(code, 0, out)
            lock = json.loads((root / ".github" / "elements.lock.json").read_text())
            tracked = M.git(ROOT, "ls-tree", "-r", "--name-only", "HEAD").split()
            self.assertEqual(lock["measured"]["layout"]["total"], len(tracked))
            code, out = run(["render", "--root", str(root)])
            self.assertEqual(code, 0, out)
            self.assertEqual(run(["check", "--root", str(root)])[0], 0)
            svg = (root / "assets" / "elements" / "layout-day.svg").read_text()
            self.assertIn("#22773E", svg, "drawn in the greenprint")
            self.assertEqual(lint(svg, budget=E.BUDGET["sheet"]), [])
            # The lock is enough: a second machine with no git history renders the same bytes.
            shutil.rmtree(root / ".git")
            before = {p.name: p.read_bytes() for p in (root / "assets" / "elements").glob("*.svg")}
            self.assertEqual(run(["render", "--root", str(root)])[0], 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in (root / "assets" / "elements").glob("*.svg")})

    def test_a_counter_glob_stays_in_its_folder_unless_told_to_cross(self):
        one = M.count(ROOT, "HEAD", ".github/workflows/*.yml")
        every = M.count(ROOT, "HEAD", ".github/**.yml")
        self.assertGreater(one, 0)
        self.assertGreater(every, one, "the data file and the workflows both end in .yml")
        self.assertEqual(M.count(ROOT, "HEAD", "src/fonts/*.json"), 3)
        self.assertEqual(M.count(ROOT, "HEAD", "*.py"), 0, "no Python at the root: * does not reach into src/")

    def test_a_check_that_is_not_met_is_drawn_as_not_met(self):
        rows = M.checks(ROOT, "HEAD")["checks"]
        self.assertTrue(all(len(r) == 3 and isinstance(r[2], bool) for r in rows))
        d = {"checks": [["Licensed", "LICENSE", True], ["Security policy", "none", False], ["By hand", "a claim"]],
             "ring_top": "RING", "ring_bottom": "V1", "name": "X", "subject": "x/y"}
        svg = E.draw("certificate", d, "blueprint", "day", "wide")
        self.assertIn("not met: Security policy", svg)
        self.assertEqual(lint(svg, budget=E.BUDGET["sheet"]), [])

    def test_a_policy_the_owner_serves_for_every_repository_meets_the_check(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            M.git(root, "init", "-q")
            (root / "LICENSE").write_text("MIT\n")
            M.git(root, "add", "LICENSE")
            M.git(root, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "feat: 🎉 begin")
            bare_rows = {r[0]: r for r in M.checks(root)["checks"]}
            self.assertEqual(bare_rows["Security policy"][1:], ["none", False])
            rows = {r[0]: r for r in M.checks(root, inherited_policy="owner/.github/SECURITY.md")["checks"]}
            self.assertEqual(rows["Security policy"][1:], ["owner/.github/SECURITY.md", True])

    def test_measurements_have_the_shapes_the_elements_want(self):
        root = ROOT
        t = M.tree(root)
        self.assertTrue(all({"key", "label", "count", "lines"} <= set(r) for r in t["rooms"]))
        h = M.histogram(root, weeks=6)
        self.assertEqual(len(h["bars"]), 6)
        m = M.materials(root)
        self.assertEqual(m["parts"][-1][0], "OTHER")
        r = M.roster(root)
        self.assertTrue(all({"name", "n", "first", "last"} <= set(p) for p in r["people"]))
        c = M.checks(root)
        self.assertEqual(len(c["checks"]), 4)
        self.assertIn("of", c["checks"][2][1])


if __name__ == "__main__":
    unittest.main()
