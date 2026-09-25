# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Example measurements, for the gallery, the preview page, `preview` mode and the tests.

Both are snapshots of real subjects on 2026-09-25, the kit's author and
this repository, not made-up numbers.

- REPOSITORY is tannergolden/banners exactly as the kit measured it that
  night (🪧 Own Banners, run 36155309538), before v1.1.0 was cut.
- PROFILE is the account tannergolden as GitHub's REST API reports it, and
  its profile repository likewise. Two things only GraphQL can say, the
  contributions in the last year and the status, were not read; each is
  None, and a value that was not read is left off the drawing rather than
  drawn as zero.

Each is otherwise shaped exactly like what `measure` returns, which the
tests hold it to.
"""
from __future__ import annotations

REPOSITORY = {
    "mode": "repository", "subject": "tannergolden/banners", "today": "2026-09-25",
    "repository": {
        "full": "tannergolden/banners", "name": "banners", "owner": "tannergolden", "org": False,
        "description": "Blueprint headers and footers a README draws for itself. Measured nightly, never fetched, "
                       "so they are up for as long as GitHub is.",
        "homepage": "", "created": "2026-09-25", "archived": False, "private": False,
        "stars": 0, "forks": 0, "watchers": 0, "issues": 0, "pulls": 0, "issuesOn": True,
        "discussionsOn": False, "workflows": 16,
        "language": "Python", "license": "MIT", "release": "v1.0.0", "released": "2026-09-25", "releases": 1,
        "topics": [], "branch": "Development", "updated": "2026-09-25",
    },
    "notes": [], "api": {"calls": 0, "points": 0},
}

PROFILE = {
    "mode": "profile", "subject": "tannergolden", "today": "2026-09-25",
    "profile": {
        "login": "tannergolden", "name": "Tanner Golden",
        "bio": "Infrastructure for AI research. Reproducibility, supply-chain hygiene, and CI that fails for the "
               "right reasons.",
        "company": "", "location": "United States", "website": "www.tannergolden.com", "twitter": "tannergolden",
        "created": "2016-12-20", "followers": 14, "following": 5, "repositories": 7, "stars": 0,
        "contributions": None, "language": "Python",
        "status": {"message": None},
    },
    "repository": {
        "full": "tannergolden/tannergolden", "name": "tannergolden", "owner": "tannergolden", "org": False,
        "description": "My GitHub profile README. AI research and systems engineering, with a bias toward "
                       "reproducibility, hardened CI/CD, and standards a machine enforces.",
        "homepage": "", "created": "2026-07-25", "archived": False, "private": False,
        "stars": 0, "forks": 0, "watchers": 0, "issues": 0, "pulls": 0, "issuesOn": False,
        "discussionsOn": False, "workflows": 5,
        "language": "Python", "license": "MIT", "release": "", "released": "", "releases": 0,
        "topics": ["engineering-standards", "github-profile", "profile-metrics", "profile-readme"],
        "branch": "Development", "updated": "2026-09-24",
    },
    "notes": [], "api": {"calls": 0, "points": 0},
}

SAMPLES = {"repository": REPOSITORY, "profile": PROFILE}
