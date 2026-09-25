# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Example measurements, for the preview page, `preview` mode and the tests.

The numbers are made up, and the subjects are trophies' own samples,
octo-dev and octo-dev/toolkit, so the two kits preview the same account.
Each is shaped exactly like what `measure` returns, which the tests hold
it to.
"""
from __future__ import annotations

REPOSITORY = {
    "mode": "repository", "subject": "octo-dev/toolkit", "today": "2026-09-25",
    "repository": {
        "full": "octo-dev/toolkit", "name": "toolkit", "owner": "octo-dev", "org": False,
        "description": "A small, sharp set of command-line tools for working with structured logs.",
        "homepage": "https://toolkit.octo.dev", "created": "2019-03-14", "archived": False, "private": False,
        "stars": 1284, "forks": 96, "watchers": 41, "issues": 23, "pulls": 4, "issuesOn": True,
        "language": "Python", "license": "MIT", "release": "v2.4.0", "released": "2026-09-02", "releases": 31,
        "topics": ["cli", "logs", "python"], "branch": "main", "updated": "2026-09-23",
    },
    "notes": [], "api": {"calls": 0, "points": 0},
}

PROFILE = {
    "mode": "profile", "subject": "octo-dev", "today": "2026-09-25",
    "profile": {
        "login": "octo-dev", "name": "Octo Dev", "bio": "Builds small tools for big logs. Maintainer of toolkit.",
        "company": "", "location": "Lisbon, Portugal", "website": "https://octo.dev", "twitter": "",
        "created": "2018-05-02", "followers": 88, "following": 61, "repositories": 34, "stars": 312,
        "contributions": 1864, "language": "Python",
        "status": {"emoji": "\U0001F6E0\ufe0f", "message": "Shipping toolkit 2.5"},
    },
    "repository": {
        "full": "octo-dev/octo-dev", "name": "octo-dev", "owner": "octo-dev", "org": False,
        "description": "", "homepage": "", "created": "2020-07-10", "archived": False, "private": False,
        "stars": 3, "forks": 0, "watchers": 1, "issues": 0, "pulls": 0, "issuesOn": True,
        "language": "", "license": "MIT", "release": "", "released": "", "releases": 0,
        "topics": [], "branch": "main", "updated": "2026-09-20",
    },
    "notes": [], "api": {"calls": 0, "points": 0},
}

SAMPLES = {"repository": REPOSITORY, "profile": PROFILE}
