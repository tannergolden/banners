# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Config, lock, README blocks and the command line, end to end without a network."""
from __future__ import annotations

import copy
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bannerkit import config, plan, readme, sample  # noqa: E402
from bannerkit.drafting import PRINTS  # noqa: E402
from bannerkit.palette import PALETTE  # noqa: E402

spec = importlib.util.spec_from_file_location("banner_kit", ROOT / "src" / "banner-kit.py")
kit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kit)


# What a runner sets that the kit reads: the run id goes into the commit
# message, and the step summary would take the test's own report.
RUNNER = ("GITHUB_ACTIONS", "GITHUB_RUN_ID", "GITHUB_STEP_SUMMARY", "GITHUB_REPOSITORY")


def run(argv: list[str], measurement: dict | None = None) -> tuple[int, str]:
    """The command line, with `measurement` standing in for GitHub, as it runs off a runner."""
    if measurement is not None:
        kit._measure = lambda args, cfg: copy.deepcopy(measurement) | ({"today": args.today} if args.today else {})
    out = io.StringIO()
    env = {k: v for k, v in os.environ.items() if k not in RUNNER}
    with mock.patch.dict(os.environ, env, clear=True), redirect_stdout(out), redirect_stderr(io.StringIO()):
        code = kit.main(argv)
    return code, out.getvalue()


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "README.md").write_text("# Toolkit\n\nWhat it does.\n", encoding="utf-8")
        self.msg = self.root.parent / f"{self.root.name}-commit.txt"

    def tearDown(self):
        self.tmp.cleanup()
        self.msg.unlink(missing_ok=True)

    def first(self):
        return run(["run", "--root", str(self.root), "--today", "2026-09-25", "--commit-file", str(self.msg)],
                   sample.REPOSITORY)

    def test_first_run_draws_everything_and_places_both_blocks(self):
        code, out = self.first()
        self.assertEqual(code, 0)
        text = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("<!-- banners:header:start -->"))
        self.assertIn("# Toolkit\n\nWhat it does.\n\n<!-- banners:footer:start -->", text)
        self.assertTrue(text.rstrip().endswith("<!-- banners:footer:end -->"))
        drawn = sorted(p.name for p in (self.root / "assets" / "banners").iterdir())
        # Six header files, four footer files, and a day and a dark button for each of the four links.
        self.assertEqual(len(drawn), 18)
        lock = json.loads((self.root / ".github" / "banners.lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["last"]["subject"], "octo-dev/toolkit")
        self.assertEqual(lock["snapshot"], "2026-09-25")
        msg = self.msg.read_text(encoding="utf-8")
        self.assertTrue(msg.startswith("chore(banners): \U0001FAA7 draw the banners for octo-dev/toolkit\n\n"))
        self.assertIn("1,284 stars", msg.replace("\n", " "))

    def test_an_empty_config_draws_the_section_and_reads_everything_from_github(self):
        (self.root / ".github").mkdir()
        (self.root / ".github" / "banners.yml").write_text("# nothing to set\n", encoding="utf-8")
        self.assertEqual(config.load(self.root / ".github" / "banners.yml"), config.validate({}))
        code, out = self.first()
        self.assertEqual(code, 0)
        self.assertIn("H2 Section and F1 Title block in blueprint", out)
        header = (self.root / "assets" / "banners" / "header-day.svg").read_text(encoding="utf-8")
        footer = (self.root / "assets" / "banners" / "footer-day.svg").read_text(encoding="utf-8")
        self.assertIn("<!--banner-kit v1 H2 day-->", header)
        self.assertIn("<!--banner-kit v1 F1 day-->", footer)
        repo = sample.REPOSITORY["repository"]
        self.assertIn(f'<title id="t">{repo["name"]}</title>', header)
        self.assertIn(repo["description"], header)
        self.assertIn("Stars: 1,284.", header)
        self.assertIn(f"Last updated {'September 23, 2026'}.", footer)

    def test_a_quiet_day_writes_nothing(self):
        self.first()
        self.msg.unlink()
        code, out = run(["run", "--root", str(self.root), "--today", "2026-09-26", "--commit-file", str(self.msg)],
                        sample.REPOSITORY)
        self.assertEqual(code, 0)
        self.assertIn("nothing changed", out)
        self.assertFalse(self.msg.exists())

    def test_a_week_on_the_lock_is_written_to_keep_the_schedule_alive(self):
        self.first()
        _, out = run(["run", "--root", str(self.root), "--today", "2026-10-02"], sample.REPOSITORY)
        self.assertIn("1 files changed", out)
        lock = json.loads((self.root / ".github" / "banners.lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["snapshot"], "2026-10-02")

    def test_a_moved_figure_is_redrawn_and_named_in_the_commit(self):
        self.first()
        m = copy.deepcopy(sample.REPOSITORY)
        m["repository"]["stars"] = 1285
        m["repository"]["release"] = "v2.4.1"
        _, out = run(["run", "--root", str(self.root), "--today", "2026-09-26", "--commit-file", str(self.msg)], m)
        msg = self.msg.read_text(encoding="utf-8")
        self.assertEqual(msg.splitlines()[0], "chore(banners): \U0001FAA7 redraw with release v2.4.1 and 1,285 stars")
        self.assertIn("release v2.4.1 (was v2.4.0)", msg.replace("\n", " "))
        self.assertIn("header-day.svg", " ".join(out.split()) + "header-day.svg")

    def test_check_passes_on_what_run_wrote_and_fails_on_a_hand_edit(self):
        self.first()
        self.assertEqual(run(["check", "--root", str(self.root)])[0], 0)
        svg = self.root / "assets" / "banners" / "header-day.svg"
        svg.write_text(svg.read_text(encoding="utf-8").replace("1,284", "9,999"), encoding="utf-8")
        code, out = run(["check", "--root", str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn("header-day.svg (differs)", out)

    def test_check_fails_on_a_drifted_block_and_a_changed_config(self):
        self.first()
        path = self.root / "README.md"
        path.write_text(path.read_text(encoding="utf-8").replace("Back to Top", "Up"), encoding="utf-8")
        self.assertIn("footer block differs", run(["check", "--root", str(self.root)])[1])
        self.first()
        (self.root / ".github" / "banners.yml").write_text("theme: brownprint\n", encoding="utf-8")
        code, out = run(["check", "--root", str(self.root)])
        self.assertEqual(code, 1)

    def test_a_design_set_to_none_takes_its_files_and_block_away(self):
        self.first()
        (self.root / ".github" / "banners.yml").write_text("footer: none\n", encoding="utf-8")
        run(["run", "--root", str(self.root), "--today", "2026-09-26"], sample.REPOSITORY)
        names = [p.name for p in (self.root / "assets" / "banners").iterdir()]
        self.assertFalse([n for n in names if n.startswith(("footer-", "link-"))])
        text = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("banners:footer", text)
        self.assertEqual(run(["check", "--root", str(self.root)])[0], 0)

    def test_a_bad_config_fails_with_the_key_named(self):
        (self.root / ".github").mkdir()
        (self.root / ".github" / "banners.yml").write_text("figures: [followers]\n", encoding="utf-8")
        code, _ = run(["run", "--root", str(self.root), "--today", "2026-09-25"], sample.REPOSITORY)
        self.assertEqual(code, 2)


class Rainbow(unittest.TestCase):
    """rainbowprint: each update is drawn in the next colour of the spectrum, and a quiet day keeps its colour."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".github").mkdir()
        (self.root / ".github" / "banners.yml").write_text("theme: rainbowprint\n", encoding="utf-8")
        self.msg = self.root.parent / f"{self.root.name}-commit.txt"

    def tearDown(self):
        self.tmp.cleanup()
        self.msg.unlink(missing_ok=True)

    def run_on(self, day: str, stars: int) -> str:
        m = copy.deepcopy(sample.REPOSITORY)
        m["repository"]["stars"] = stars
        self.msg.unlink(missing_ok=True)
        run(["run", "--root", str(self.root), "--today", day, "--commit-file", str(self.msg)], m)
        self.assertEqual(run(["check", "--root", str(self.root)])[0], 0)
        return json.loads((self.root / ".github" / "banners.lock.json").read_text(encoding="utf-8"))["rainbow"]

    def drawn_in(self, token: str) -> bool:
        return PALETTE[token] in (self.root / "assets" / "banners" / "header-day.svg").read_text(encoding="utf-8")

    def test_each_update_takes_the_next_colour_and_a_quiet_day_keeps_it(self):
        self.assertEqual(self.run_on("2026-09-25", 1284), "redprint")
        self.assertTrue(self.drawn_in(PRINTS["redprint"]["line"]))
        self.assertIn("colour 1 of 9; the next update will be the orangeprint", self.msg.read_text(encoding="utf-8").replace("\n", " "))
        self.assertEqual(self.run_on("2026-09-26", 1284), "redprint")
        self.assertFalse(self.msg.exists())
        self.assertEqual(self.run_on("2026-09-27", 1285), "orangeprint")
        self.assertTrue(self.drawn_in(PRINTS["orangeprint"]["line"]))
        self.assertFalse(self.drawn_in(PRINTS["redprint"]["line"]))

    def test_the_spectrum_wraps_round(self):
        self.run_on("2026-09-25", 1284)
        path = self.root / ".github" / "banners.lock.json"
        lk = json.loads(path.read_text(encoding="utf-8"))
        lk["rainbow"] = "pinkprint"
        path.write_text(json.dumps(lk), encoding="utf-8")
        run(["render", "--root", str(self.root)])
        self.assertEqual(self.run_on("2026-09-26", 1300), "redprint")

    def test_a_weekly_snapshot_is_not_an_update(self):
        self.run_on("2026-09-25", 1284)
        self.assertEqual(self.run_on("2026-10-02", 1284), "redprint")

    def test_the_rainbow_needs_the_lock(self):
        with self.assertRaises(config.ConfigError):
            config.validate({"theme": "rainbowprint", "lock": False})


class Preview(unittest.TestCase):
    def test_a_preview_root_checks_like_a_real_one(self):
        for mode in ("repository", "profile"):
            with tempfile.TemporaryDirectory() as tmp:
                self.assertEqual(run(["preview", "--root", tmp, "--mode", mode])[0], 0)
                self.assertEqual(run(["check", "--root", tmp, "--mode", mode])[0], 0)


class Blocks(unittest.TestCase):
    def test_place_is_idempotent_and_keeps_the_readme(self):
        blocks = {"header": readme.block("header", "H"), "footer": readme.block("footer", "F")}
        once = readme.place("# Title\n\nBody.\n", blocks)
        self.assertEqual(readme.place(once, blocks), once)
        self.assertIn("# Title\n\nBody.\n", once)
        self.assertEqual(readme.place(once, {}), "# Title\n\nBody.\n")

    def test_an_empty_readme_gets_just_the_blocks(self):
        blocks = {"header": readme.block("header", "H"), "footer": readme.block("footer", "F")}
        text = readme.place("", blocks)
        self.assertEqual(text, blocks["header"] + "\n\n" + blocks["footer"] + "\n")


class TopLink(unittest.TestCase):
    """The footer is always the way back to the top of the README."""

    def blocks(self, **given) -> dict:
        return plan.plan(copy.deepcopy(sample.REPOSITORY), config.validate(given), draw=False)["blocks"]

    def assertLinksTheImage(self, footer: str):
        # The link opens on a line of its own and nothing inside it is blank,
        # so Markdown reads it as one HTML block, with the image inside it.
        start = footer.index('<a href="#top">\n<picture>\n')
        body = footer[start:footer.index("</picture>\n</a>", start)]
        self.assertNotIn("\n\n", body)
        self.assertIn('src="assets/banners/footer-day.svg"', body)

    def test_the_whole_footer_links_to_the_anchor_in_the_header(self):
        blocks = self.blocks()
        self.assertLinksTheImage(blocks["footer"])
        self.assertIn('<a name="top"></a>', blocks["header"])

    def test_hiding_the_words_keeps_the_way_back(self):
        self.assertLinksTheImage(self.blocks(hide=["top"])["footer"])

    def test_with_no_header_the_top_is_still_there(self):
        blocks = self.blocks(header="none")
        self.assertLinksTheImage(blocks["footer"])
        self.assertIn('<a name="top"></a>', blocks["header"])
        self.assertNotIn("<picture>", blocks["header"])

    def test_with_no_footer_nothing_is_added(self):
        self.assertEqual(self.blocks(header="none", footer="none"), {})


class Config(unittest.TestCase):
    def test_the_starter_file_is_the_defaults(self):
        self.assertEqual(config.load(ROOT / "examples" / "banners.yml"), config.validate({}))

    def test_unknown_keys_and_values_fail_loudly(self):
        for given in ({"colour": "navy"}, {"theme": "navy"}, {"theme": "rainbowprint", "lock": False}, {"hide": ["repo"]}, {"figures": ["nope"]},
                      {"links": ["no bar"]}, {"lock": "yes please"}):
            with self.assertRaises(config.ConfigError):
                config.validate(given)

    def test_a_validated_config_validates_again_unchanged(self):
        cfg = config.validate({"links": {"Docs": "docs/"}, "hide": ["motto"], "theme": "tealprint"})
        self.assertEqual(config.validate(cfg), cfg)

    def test_dump_round_trips(self):
        cfg = config.validate({"theme": "purpleprint", "title": "It's #1: logs", "figures": ["stars"], "hide": ["motto"],
                               "links": {"Docs": "docs/"}})
        self.assertEqual(config.validate(config.parse_yaml(config.dump(cfg))), cfg)


if __name__ == "__main__":
    unittest.main()
