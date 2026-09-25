# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Composing: a measurement and a config, as the header and the footer, and the text made drawable."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bannerkit import compose as c, config, plan, sample  # noqa: E402
from bannerkit.text import missing  # noqa: E402


def composed(m, **given):
    return c.compose(m, config.validate(given))


class Defaults(unittest.TestCase):
    def test_a_repository_reads_itself(self):
        h, f, notes = composed(sample.REPOSITORY)
        self.assertEqual((h.title, h.tagline, h.motto), ("toolkit", sample.REPOSITORY["repository"]["description"], ""))
        self.assertEqual([label for label, _ in h.figures],
                         ["PROJECT", "RELEASE", "STARS", "FORKS", "OPEN ISSUES", "LANGUAGE", "LICENSE"])
        self.assertEqual(dict(h.figures)["STARS"], "1,284")
        self.assertEqual((f.handle, f.license, f.updated), ("@octo-dev", "MIT", "2026-09-23"))
        self.assertEqual(f.links, (("Website", "https://toolkit.octo.dev"),
                                   ("Releases", "https://github.com/octo-dev/toolkit/releases"),
                                   ("Issues", "https://github.com/octo-dev/toolkit/issues")))
        self.assertEqual(notes, [])

    def test_a_profile_reads_the_person(self):
        h, f, _ = composed(sample.PROFILE)
        self.assertEqual((h.title, h.motto), ("Octo Dev", "Shipping toolkit 2.5"))
        self.assertEqual(h.figures[0], ("ACCOUNT", "@octo-dev"))
        self.assertEqual(dict(h.figures)["CONTRIBUTIONS, LAST YEAR"], "1,864")
        self.assertEqual(dict(h.figures)["MEMBER SINCE"], "2018")
        self.assertEqual([label for label, _ in f.links], ["Website"])

    def test_a_figure_github_does_not_have_is_left_out(self):
        m = copy.deepcopy(sample.REPOSITORY)
        m["repository"]["release"] = ""
        m["repository"]["language"] = ""
        h, _, _ = composed(m)
        self.assertNotIn("RELEASE", dict(h.figures))
        self.assertNotIn("LANGUAGE", dict(h.figures))


class Config(unittest.TestCase):
    def test_the_config_wins_where_it_speaks(self):
        h, f, _ = composed(sample.REPOSITORY, title="Toolkit Pro", tagline="Logs, tamed.",
                           motto="Drawn, never fetched.", closing="Thanks for reading.", theme="brownprint")
        self.assertEqual((h.title, h.tagline, h.motto, h.tone), ("Toolkit Pro", "Logs, tamed.", "Drawn, never fetched.",
                                                                 "brownprint"))
        self.assertEqual((f.closing, f.tone), ("Thanks for reading.", "brownprint"))

    def test_figures_are_the_ones_named_in_that_order(self):
        h, _, _ = composed(sample.REPOSITORY, figures=["license", "stars", "updated", "site"])
        self.assertEqual(h.figures, (("LICENSE", "MIT"), ("STARS", "1,284"), ("UPDATED", "2026-09-23"),
                                     ("SITE", "toolkit.octo.dev")))

    def test_a_figure_of_the_other_mode_fails_with_its_name(self):
        with self.assertRaises(c.CompositionError) as err:
            composed(sample.REPOSITORY, figures=["followers"])
        self.assertIn("followers", str(err.exception))

    def test_hidden_fields_are_neither_drawn_nor_spoken(self):
        h, f, _ = composed(sample.REPOSITORY, hide=["tagline", "figures", "license", "links"])
        self.assertFalse(h.on("tagline") or h.on("figures") or f.on("license") or f.on("links"))
        self.assertNotIn("Stars", h.alt())
        self.assertNotIn("MIT", f.spoken())

    def test_links_from_the_config_replace_the_defaults(self):
        _, f, _ = composed(sample.REPOSITORY, links={"Docs": "docs/", "Changelog": "CHANGELOG.md"})
        self.assertEqual(f.links, (("Docs", "docs/"), ("Changelog", "CHANGELOG.md")))


class Drawable(unittest.TestCase):
    def test_banned_dashes_become_hyphens_and_shortcodes_go(self):
        notes = []
        text = c.drawable("Engineer \u2014 builds :rocket: tools \u2013 fast", notes=notes)
        self.assertEqual(text, "Engineer - builds tools - fast")
        self.assertEqual(notes, [])
        self.assertFalse(any(ch in text for ch in "\u2013\u2014"))

    def test_a_character_no_face_holds_is_left_out_with_a_note(self):
        notes = []
        self.assertEqual(c.drawable("Logs \u2603 tamed", notes=notes, what="tagline"), "Logs tamed")
        self.assertTrue(notes and "tagline" in notes[0])

    def test_accented_names_draw_whole(self):
        for name in ("Jos\u00e9 Valim", "Zo\u00eb M\u00fcller", "\u0141ukasz Dvo\u0159\u00e1k"):
            self.assertEqual(missing(name.upper(), "num"), "")
            self.assertEqual(c.drawable(name, "num"), name)

    def test_a_name_the_letters_cannot_draw_falls_back_to_the_login(self):
        m = copy.deepcopy(sample.PROFILE)
        m["profile"]["name"] = "\u5f35\u5049"
        h, _, _ = composed(m)
        self.assertEqual(h.title, "octo-dev")

    def test_an_opening_emoji_is_taken_off_the_tagline_quietly(self):
        m = copy.deepcopy(sample.REPOSITORY)
        m["repository"]["description"] = "\U0001F9F0 Tools for logs."
        h, _, notes = composed(m)
        self.assertEqual(h.tagline, "Tools for logs.")
        self.assertEqual(notes, [])
        self.assertEqual(c.split_emoji("\u5f35\u5049 x"), ("", "\u5f35\u5049 x"))

    def test_no_header_draws_an_emoji(self):
        m = copy.deepcopy(sample.PROFILE)
        m["profile"]["bio"] = "\U0001F9F0 Builds small tools for big logs."
        for header in ("sheet", "section", "strip"):
            files = plan.plan(m, config.validate({"header": header}))["files"]
            for name, svg in files.items():
                if "header" in name:
                    self.assertNotIn("<text", svg, name)
                    self.assertNotIn("1F9F0", svg.upper(), name)

    def test_no_footer_draws_a_separator_line(self):
        for footer in ("title-block", "scale-bar"):
            files = plan.plan(sample.REPOSITORY, config.validate({"footer": footer}))["files"]
            for name, svg in files.items():
                if "footer" in name:
                    self.assertNotIn("stroke-dasharray", svg, name)

    def test_a_config_written_for_1_0_still_runs(self):
        # 1.0's starter file carried `emoji: ''` and listed both under `hide`; they are read and set aside.
        self.assertEqual(config.validate({"emoji": "\U0001FAB5", "hide": ["emoji", "divider", "motto"]}),
                         config.validate({"hide": ["motto"]}))

    def test_long_text_is_clipped_at_a_word(self):
        m = copy.deepcopy(sample.REPOSITORY)
        m["repository"]["description"] = "word " * 80
        h, _, _ = composed(m)
        self.assertLessEqual(len(h.tagline), c.LIMITS["tagline"])
        self.assertTrue(h.tagline.endswith("word\u2026"))


class Counts(unittest.TestCase):
    def test_counts_as_a_drawing_letters_them(self):
        self.assertEqual([c.count(n) for n in (0, 1, 1284, 99999, 100000, 128400, 999499, 999500, 1250000, 12300000)],
                         ["0", "1", "1,284", "99,999", "100k", "128k", "999k", "1.0M", "1.2M", "12M"])

    def test_host(self):
        self.assertEqual(c.host("https://www.octo.dev/"), "octo.dev")
        self.assertEqual(c.host("octo.dev/blog"), "octo.dev/blog")


if __name__ == "__main__":
    unittest.main()
