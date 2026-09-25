# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A GitHub client that answers from a table: the same two methods, no network."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bannerkit import measure  # noqa: E402
from bannerkit.github import GitHub  # noqa: E402


class FakeGitHub(GitHub):
    """Answers each query from `answers`, keyed by the query text; a callable answer gets the variables."""

    def __init__(self, answers: dict):  # noqa: super().__init__ would want a token
        self.answers = answers
        self.calls = 0
        self.points = 0
        self.last_errors = []
        self.asked = []

    def gql(self, query: str, **variables) -> dict:
        self.calls += 1
        self.asked.append((query, variables))
        answer = self.answers[query]
        return answer(**variables) if callable(answer) else answer


def commit(day: str, headline: str, committer: str = "Octo Dev", email: str = "octo@users.noreply.github.com") -> dict:
    return {"committedDate": f"{day}T12:00:00Z", "messageHeadline": headline,
            "committer": {"name": committer, "email": email}}


BOT = ("github-actions[bot]", "41898282+github-actions[bot]@users.noreply.github.com")


def repository_answer(**overrides) -> dict:
    r = {
        "nameWithOwner": "octo-dev/toolkit", "name": "toolkit",
        "description": "\U0001F9F0 A small, sharp set of command-line tools for working with structured logs.",
        "homepageUrl": "https://toolkit.octo.dev", "createdAt": "2019-03-14T09:00:00Z", "isArchived": False,
        "isPrivate": False, "hasIssuesEnabled": True, "owner": {"login": "octo-dev", "__typename": "User"},
        "stargazerCount": 1284, "forkCount": 96, "watchers": {"totalCount": 41},
        "openIssues": {"totalCount": 23}, "openPulls": {"totalCount": 4},
        "primaryLanguage": {"name": "Python"}, "licenseInfo": {"spdxId": "MIT", "name": "MIT License"},
        "latestRelease": {"tagName": "v2.4.0", "publishedAt": "2026-09-02T10:00:00Z"},
        "releases": {"totalCount": 31},
        "repositoryTopics": {"nodes": [{"topic": {"name": "cli"}}, {"topic": {"name": "logs"}}, {"topic": {"name": "python"}}]},
        "defaultBranchRef": {"name": "main"},
    }
    r.update(overrides)
    return {"rateLimit": {"cost": 1}, "repository": r}


def history_answer(pages: list[list[dict]]):
    """A HISTORY answer that pages through `pages`, 100 at a time as the real one would."""
    def answer(owner, name, first, after=None):
        i = int(after or 0)
        return {"repository": {"defaultBranchRef": {"target": {"history": {
            "pageInfo": {"hasNextPage": i + 1 < len(pages), "endCursor": str(i + 1)},
            "nodes": pages[i]}}}}}
    return answer


def user_answer(**overrides) -> dict:
    u = {
        "login": "octo-dev", "name": "Octo Dev", "bio": "Builds small tools for big logs. Maintainer of toolkit.",
        "company": "", "location": "Lisbon, Portugal", "websiteUrl": "https://octo.dev", "twitterUsername": None,
        "createdAt": "2018-05-02T08:00:00Z", "followers": {"totalCount": 88}, "following": {"totalCount": 61},
        "publicRepos": {"totalCount": 34},
        "status": {"message": "Shipping toolkit 2.5"},
        "contributionsCollection": {"contributionCalendar": {"totalContributions": 1864}},
    }
    u.update(overrides)
    return {"rateLimit": {"cost": 1}, "user": u}


def repos_answer(nodes: list[dict]):
    def answer(login, first, after=None):
        i = int(after or 0)
        chunk = nodes[i * first:(i + 1) * first]
        return {"user": {"repositories": {"pageInfo": {"hasNextPage": (i + 1) * first < len(nodes), "endCursor": str(i + 1)},
                                          "nodes": chunk}}}
    return answer


def repository_client(pages=None, **overrides) -> FakeGitHub:
    pages = pages or [[commit("2026-09-25", "chore(banners): \U0001FAA7 redraw with 1,284 stars", *BOT),
                       commit("2026-09-24", "chore(trophies): \U0001F3C6 refresh the case", *BOT),
                       commit("2026-09-23", "feat: add the tail command")]]
    return FakeGitHub({measure.REPOSITORY: repository_answer(**overrides), measure.HISTORY: history_answer(pages)})


def profile_client() -> FakeGitHub:
    repos = [{"stargazerCount": 200, "primaryLanguage": {"name": "Python"}},
             {"stargazerCount": 90, "primaryLanguage": {"name": "Go"}},
             {"stargazerCount": 12, "primaryLanguage": {"name": "Go"}},
             {"stargazerCount": 10, "primaryLanguage": {"name": "Python"}},
             {"stargazerCount": 0, "primaryLanguage": None}]
    readme = repository_answer(nameWithOwner="octo-dev/octo-dev", name="octo-dev", description="", homepageUrl="",
                               stargazerCount=3, forkCount=0, primaryLanguage=None, latestRelease=None,
                               releases={"totalCount": 0}, repositoryTopics={"nodes": []})
    return FakeGitHub({measure.USER: user_answer(), measure.REPOS: repos_answer(repos), measure.REPOSITORY: readme,
                       measure.HISTORY: history_answer([[commit("2026-09-20", "docs: say hello")]])})
