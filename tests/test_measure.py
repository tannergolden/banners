# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The measurement: what is read from GitHub, and how it is read, against a fake client."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fake import BOT, commit, profile_client, repository_client  # noqa: E402

from bannerkit import measure, sample  # noqa: E402


def shape(value):
    """A value's shape: the keys of every dict, all the way down, and the type of everything else."""
    if isinstance(value, dict):
        return {k: shape(v) for k, v in value.items()}
    if isinstance(value, list):
        return "list"
    return type(value).__name__


class Repository(unittest.TestCase):
    def test_reads_what_the_header_and_footer_show(self):
        m = measure.measure(repository_client(), "repository", "octo-dev/toolkit", "octo-dev/toolkit", today="2026-09-25")
        r = m["repository"]
        self.assertEqual((m["mode"], m["subject"]), ("repository", "octo-dev/toolkit"))
        self.assertEqual((r["stars"], r["forks"], r["issues"], r["release"], r["license"], r["language"]),
                         (1284, 96, 23, "v2.4.0", "MIT", "Python"))
        self.assertEqual((r["created"], r["released"], r["topics"]), ("2019-03-14", "2026-09-02", ["cli", "logs", "python"]))

    def test_last_change_skips_refreshes_and_bot_commits(self):
        m = measure.measure(repository_client(), "repository", "", "octo-dev/toolkit", today="2026-09-25")
        self.assertEqual(m["repository"]["updated"], "2026-09-23")

    def test_last_change_reads_back_across_pages(self):
        pages = [[commit("2026-09-25", "chore: format", *BOT)] * 100, [commit("2026-08-01", "fix: a person's fix")]]
        gh = repository_client(pages)
        m = measure.measure(gh, "repository", "", "octo-dev/toolkit", today="2026-09-25")
        self.assertEqual(m["repository"]["updated"], "2026-08-01")
        self.assertEqual(sum(1 for q, _ in gh.asked if q is measure.HISTORY), 2)

    def test_a_refresh_by_a_person_still_does_not_count(self):
        pages = [[commit("2026-09-25", "chore(banners): \U0001FAA7 redraw"), commit("2026-09-01", "feat: real")]]
        m = measure.measure(repository_client(pages), "repository", "", "octo-dev/toolkit", today="2026-09-25")
        self.assertEqual(m["repository"]["updated"], "2026-09-01")

    def test_no_person_in_reach_leaves_the_date_off_and_says_so(self):
        pages = [[commit("2026-09-25", "chore: bump", *BOT)]]
        m = measure.measure(repository_client(pages), "repository", "", "octo-dev/toolkit", today="2026-09-25")
        self.assertEqual(m["repository"]["updated"], "")
        self.assertTrue(any("no commit by a person" in n for n in m["notes"]))

    def test_workflows_and_discussions_are_measured_for_the_link_buttons(self):
        m = measure.measure(repository_client(), "repository", "", "octo-dev/toolkit", today="2026-09-25")
        # Two workflow files; the README beside them is not one.
        self.assertEqual((m["repository"]["workflows"], m["repository"]["discussionsOn"]), (2, False))
        m = measure.measure(repository_client(workflows=None), "repository", "", "octo-dev/toolkit", today="2026-09-25")
        self.assertEqual(m["repository"]["workflows"], 0)

    def test_an_unnamed_licence_is_left_off(self):
        gh = repository_client(licenseInfo={"spdxId": "NOASSERTION", "name": "Other"})
        m = measure.measure(gh, "repository", "", "octo-dev/toolkit", today="2026-09-25")
        self.assertEqual(m["repository"]["license"], "")

    def test_the_sample_has_the_shape_of_a_measurement(self):
        m = measure.measure(repository_client(), "repository", "", "octo-dev/toolkit", today="2026-09-25")
        self.assertEqual(shape(m["repository"]), shape(sample.REPOSITORY["repository"]))
        self.assertEqual(set(m) - {"api"}, set(sample.REPOSITORY) - {"api"})


class Profile(unittest.TestCase):
    def test_reads_the_person_and_their_profile_repository(self):
        m = measure.measure(profile_client(), "auto", "", "octo-dev/octo-dev", today="2026-09-25")
        p = m["profile"]
        self.assertEqual((m["mode"], m["subject"]), ("profile", "octo-dev"))
        self.assertEqual((p["followers"], p["repositories"], p["stars"], p["contributions"]), (88, 34, 312, 1864))
        self.assertEqual((p["created"], p["website"]), ("2018-05-02", "https://octo.dev"))
        self.assertEqual(m["repository"]["full"], "octo-dev/octo-dev")
        self.assertEqual(m["repository"]["updated"], "2026-09-20")

    def test_top_language_is_the_most_repositories_then_the_most_stars(self):
        m = measure.measure(profile_client(), "profile", "octo-dev", "octo-dev/octo-dev", today="2026-09-25")
        # Python and Go have two repositories each; Python's have 210 stars to Go's 102.
        self.assertEqual(m["profile"]["language"], "Python")

    def test_the_status_is_its_message(self):
        m = measure.measure(profile_client(), "profile", "octo-dev", "octo-dev/octo-dev", today="2026-09-25")
        self.assertEqual(m["profile"]["status"], {"message": "Shipping toolkit 2.5"})

    def test_the_sample_has_the_shape_of_a_measurement(self):
        m = measure.measure(profile_client(), "profile", "octo-dev", "octo-dev/octo-dev", today="2026-09-25")
        self.assertEqual(shape(m["profile"]), shape(sample.PROFILE["profile"]))
        self.assertEqual(shape(m["repository"]), shape(sample.PROFILE["repository"]))


class Resolve(unittest.TestCase):
    def test_auto_reads_a_profile_only_in_the_repository_named_after_its_owner(self):
        self.assertEqual(measure.resolve("auto", "", "octo-dev/octo-dev"), ("profile", "octo-dev", "octo-dev/octo-dev"))
        self.assertEqual(measure.resolve("auto", "", "Octo-Dev/octo-dev")[0], "profile")
        self.assertEqual(measure.resolve("auto", "", "octo-dev/toolkit"),
                         ("repository", "octo-dev/toolkit", "octo-dev/toolkit"))

    def test_a_subject_decides_auto_by_its_shape(self):
        self.assertEqual(measure.resolve("auto", "someone", "octo-dev/toolkit")[:2], ("profile", "someone"))
        self.assertEqual(measure.resolve("auto", "a/b", "octo-dev/octo-dev")[:2], ("repository", "a/b"))

    def test_repository_mode_needs_a_repository(self):
        with self.assertRaises(SystemExit):
            measure.resolve("repository", "", "")


class Automated(unittest.TestCase):
    def test_what_counts_as_no_person(self):
        self.assertTrue(measure.automated(commit("2026-01-01", "anything", *BOT)))
        self.assertTrue(measure.automated(commit("2026-01-01", "chore(trophies): x")))
        self.assertTrue(measure.automated(commit("2026-01-01", "x", "renovate[bot]", "renovate@example.com")))
        self.assertFalse(measure.automated(commit("2026-01-01", "chore(deps): bump", "GitHub", "noreply@github.com")))
        self.assertFalse(measure.automated(commit("2026-01-01", "chore(bannersx): not ours")))


if __name__ == "__main__":
    unittest.main()
