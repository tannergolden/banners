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
        self.assertEqual((h.title, h.tagline, h.motto), ("banners", sample.REPOSITORY["repository"]["description"], ""))
        self.assertEqual([label for label, _ in h.figures],
                         ["PROJECT", "RELEASE", "STARS", "FORKS", "OPEN ISSUES", "LANGUAGE", "LICENSE"])
        self.assertEqual((dict(h.figures)["STARS"], dict(h.figures)["RELEASE"]), ("0", "v1.0.0"))
        self.assertEqual((f.handle, f.license, f.updated), ("@tannergolden", "MIT", "2026-09-25"))
        self.assertEqual(f.links, (("Issues", "https://github.com/tannergolden/banners/issues"),
                                   ("Pull Requests", "https://github.com/tannergolden/banners/pulls"),
                                   ("Releases", "https://github.com/tannergolden/banners/releases"),
                                   ("Actions", "https://github.com/tannergolden/banners/actions")))
        self.assertEqual(notes, [])

    def test_a_profile_reads_the_person(self):
        h, f, _ = composed(sample.PROFILE)
        self.assertEqual((h.title, h.motto), ("Tanner Golden", ""))
        self.assertEqual(h.figures[0], ("ACCOUNT", "@tannergolden"))
        self.assertEqual(dict(h.figures)["MEMBER SINCE"], "2016")
        # The snapshot did not read the contributions, so they are left out rather than drawn as zero.
        self.assertEqual([label for label, _ in h.figures],
                         ["ACCOUNT", "FOLLOWERS", "REPOSITORIES", "STARS EARNED", "LANGUAGE", "MEMBER SINCE"])
        self.assertEqual(f.links, (("Website", "https://www.tannergolden.com"),
                                   ("Repositories", "https://github.com/tannergolden?tab=repositories"),
                                   ("Projects", "https://github.com/tannergolden?tab=projects"),
                                   ("Packages", "https://github.com/tannergolden?tab=packages")))

    def test_a_figure_github_does_not_have_is_left_out(self):
        m = copy.deepcopy(sample.REPOSITORY)
        m["repository"]["release"] = ""
        m["repository"]["language"] = ""
        h, _, _ = composed(m)
        self.assertNotIn("RELEASE", dict(h.figures))
        self.assertNotIn("LANGUAGE", dict(h.figures))


class Config(unittest.TestCase):
    def test_the_config_wins_where_it_speaks(self):
        h, f, _ = composed(sample.REPOSITORY, title="Banners Pro", tagline="Drawn at both ends.",
                           motto="Drawn, never fetched.", closing="Thanks for reading.", theme="brownprint")
        self.assertEqual((h.title, h.tagline, h.motto, h.tone), ("Banners Pro", "Drawn at both ends.", "Drawn, never fetched.",
                                                                 "brownprint"))
        self.assertEqual((f.closing, f.tone), ("Thanks for reading.", "brownprint"))

    def test_figures_are_the_ones_named_in_that_order(self):
        m = copy.deepcopy(sample.REPOSITORY)
        m["repository"]["homepage"] = "https://www.tannergolden.com/"
        h, _, _ = composed(m, figures=["license", "stars", "updated", "site"])
        self.assertEqual(h.figures, (("LICENSE", "MIT"), ("STARS", "0"), ("UPDATED", "2026-09-25"),
                                     ("SITE", "tannergolden.com")))

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
        self.assertEqual(h.title, "tannergolden")

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

    def test_a_person_with_no_website_gets_the_four_profile_tabs(self):
        m = copy.deepcopy(sample.PROFILE)
        m["profile"]["website"] = "tannergolden.com"
        _, f, _ = composed(m)
        self.assertEqual(f.links[0], ("Website", "https://tannergolden.com"))
        m["profile"]["website"] = ""
        _, f, _ = composed(m)
        self.assertEqual([label for label, _ in f.links], ["Repositories", "Projects", "Packages", "Stars"])

    def test_a_repository_page_with_nothing_on_it_is_never_a_button(self):
        m = copy.deepcopy(sample.REPOSITORY)
        m["repository"].update(issuesOn=False, releases=0, workflows=0, discussionsOn=True)
        _, f, _ = composed(m)
        self.assertEqual([label for label, _ in f.links], ["Pull Requests", "Discussions", "Contributors"])

    def test_the_config_names_up_to_four_buttons(self):
        four = {f"Link {i}": f"https://example.com/{i}" for i in range(4)}
        _, f, _ = composed(sample.REPOSITORY, links=four)
        self.assertEqual([label for label, _ in f.links], list(four))
        with self.assertRaisesRegex(config.ConfigError, "at most 4"):
            config.validate({"links": dict(four, Fifth="https://example.com/5")})

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
        self.assertEqual(c.host("https://www.tannergolden.com/"), "tannergolden.com")
        self.assertEqual(c.host("tannergolden.com/blog"), "tannergolden.com/blog")


if __name__ == "__main__":
    unittest.main()
