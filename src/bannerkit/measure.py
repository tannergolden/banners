# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Measure what a banner says: the repository its README lives in, and in profile mode the person too.

Everything comes out of `measure(gh, ...)` as one plain dict, the
measurement, which is all `compose` needs to write a header and a footer.
It is kept in the lock file, so a committed banner can be redrawn and
checked later without a token and without the numbers moving underneath.

Two modes, the way trophies has them:

  repository   the repository: its name, description, release, stars,
               forks, open issues, language, licence, and when it last
               changed
  profile      a person, for the README GitHub shows on their profile:
               name, bio, followers, public repositories and the stars
               they earned, contributions in the last year, their main
               language; plus the profile repository's own licence and
               last change, for the footer

`auto` picks profile for the repository named after its owner, which is
the one whose README a profile shows, and repository mode everywhere else.

"When it last changed" is the last commit on the default branch that a
person made. A commit a workflow pushed (its committer is a bot) or a
refresh commit of this kit (its scope is `chore(banners)`) does not count,
or every refresh would move the date it draws and so cause the next one.
The GraphQL is written out in full, so a reader can see exactly what is
asked.
"""
from __future__ import annotations

import html
import re
from collections import Counter

REPOSITORY = """
query($owner:String!,$name:String!){ rateLimit{cost}
  repository(owner:$owner,name:$name){ nameWithOwner name description homepageUrl createdAt isArchived isPrivate
    hasIssuesEnabled owner{ login __typename }
    stargazerCount forkCount watchers{totalCount}
    openIssues: issues(states:OPEN){totalCount} openPulls: pullRequests(states:OPEN){totalCount}
    primaryLanguage{ name } licenseInfo{ spdxId name }
    latestRelease{ tagName publishedAt }
    releases{totalCount}
    repositoryTopics(first:20){ nodes{ topic{ name } } }
    defaultBranchRef{ name } } }"""

HISTORY = """
query($owner:String!,$name:String!,$first:Int!,$after:String){ rateLimit{cost}
  repository(owner:$owner,name:$name){ defaultBranchRef{ target{ ... on Commit{
    history(first:$first,after:$after){ pageInfo{hasNextPage endCursor}
      nodes{ committedDate messageHeadline committer{ name email } } } } } } } }"""

USER = """
query($login:String!){ rateLimit{cost}
  user(login:$login){ login name bio company location websiteUrl twitterUsername createdAt
    followers{totalCount} following{totalCount}
    publicRepos: repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC){totalCount}
    status{ emojiHTML message }
    contributionsCollection{ contributionCalendar{ totalContributions } } } }"""

REPOS = """
query($login:String!,$first:Int!,$after:String){ rateLimit{cost}
  user(login:$login){ repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:$first,after:$after,
      orderBy:{field:STARGAZERS,direction:DESC}){
    pageInfo{hasNextPage endCursor}
    nodes{ stargazerCount primaryLanguage{ name } } } } }"""

# This kit's own refresh commits, and trophies', which run beside it.
REFRESH = re.compile(r"^chore\((banners|trophies)\):")
HISTORY_PAGES = 5

# The one character a status emoji is, out of the HTML GitHub renders it as.
_EMOJI_TAG = re.compile(r"<g-emoji[^>]*>(.*?)</g-emoji>", re.S)


def day(stamp: str | None) -> str:
    """An ISO timestamp's date, in UTC, as GitHub stores it; empty for none."""
    return (stamp or "")[:10]


def automated(node: dict) -> bool:
    """A commit no person made: a refresh of this kit or trophies, or anything a bot committed."""
    if REFRESH.match(node.get("messageHeadline") or ""):
        return True
    who = node.get("committer") or {}
    name, email = (who.get("name") or ""), (who.get("email") or "")
    return name.endswith("[bot]") or email.endswith("[bot]@users.noreply.github.com")


def last_change(gh, owner: str, name: str, notes: list) -> str:
    """The date of the newest default-branch commit a person made, reading back at most a few pages."""
    after = None
    for _ in range(HISTORY_PAGES):
        data = gh.gql(HISTORY, owner=owner, name=name, first=100, after=after)
        target = ((((data or {}).get("repository") or {}).get("defaultBranchRef") or {}).get("target") or {})
        history = target.get("history") or {}
        for node in history.get("nodes") or []:
            if node and not automated(node):
                return day(node.get("committedDate"))
        info = history.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            break
        after = info.get("endCursor")
    notes.append(f"no commit by a person in the last {HISTORY_PAGES * 100} on {owner}/{name}'s default branch; "
                 "the date is left off")
    return ""


def repository(gh, owner: str, name: str, notes: list) -> dict:
    r = gh.gql(REPOSITORY, owner=owner, name=name).get("repository")
    if not r:
        why = "; ".join(getattr(gh, "last_errors", []) or []) or "not found, or not readable with this token"
        raise RuntimeError(f"cannot read repository {owner}/{name}: {why}")
    licence = (r.get("licenseInfo") or {}).get("spdxId") or ""
    release = r.get("latestRelease") or {}
    return {
        "full": r["nameWithOwner"], "name": r["name"], "owner": (r.get("owner") or {}).get("login") or owner,
        "org": (r.get("owner") or {}).get("__typename") == "Organization",
        "description": r.get("description") or "", "homepage": r.get("homepageUrl") or "",
        "created": day(r.get("createdAt")), "archived": bool(r.get("isArchived")), "private": bool(r.get("isPrivate")),
        "stars": r.get("stargazerCount") or 0, "forks": r.get("forkCount") or 0,
        "watchers": ((r.get("watchers") or {}).get("totalCount")) or 0,
        "issues": ((r.get("openIssues") or {}).get("totalCount")) or 0,
        "pulls": ((r.get("openPulls") or {}).get("totalCount")) or 0,
        "issuesOn": bool(r.get("hasIssuesEnabled")),
        "language": (r.get("primaryLanguage") or {}).get("name") or "",
        # NOASSERTION is GitHub saying it found a licence file it cannot name.
        "license": "" if licence in ("", "NOASSERTION") else licence,
        "release": release.get("tagName") or "", "released": day(release.get("publishedAt")),
        "releases": ((r.get("releases") or {}).get("totalCount")) or 0,
        "topics": [((n or {}).get("topic") or {}).get("name") for n in ((r.get("repositoryTopics") or {}).get("nodes") or [])
                   if ((n or {}).get("topic") or {}).get("name")],
        "branch": (r.get("defaultBranchRef") or {}).get("name") or "",
        "updated": last_change(gh, owner, name, notes) if r.get("defaultBranchRef") else "",
    }


def status_emoji(emoji_html: str | None) -> str:
    """The character a status emoji is. A custom GitHub emoji is an image, not a character, and gives none."""
    found = _EMOJI_TAG.search(emoji_html or "")
    text = html.unescape(found.group(1)).strip() if found else ""
    return "" if "<" in text else text


def profile(gh, login: str, notes: list) -> dict:
    u = gh.gql(USER, login=login).get("user")
    if not u:
        why = "; ".join(getattr(gh, "last_errors", []) or []) or "no such user"
        raise RuntimeError(f"cannot read user {login}: {why} (profile mode measures a person, not an organization)")
    repos = gh.paged(REPOS, ("user", "repositories"), login=login)
    languages = Counter((r.get("primaryLanguage") or {}).get("name") for r in repos if r.get("primaryLanguage"))
    # The language most of their repositories are written in; a tie goes to the one whose repositories have more stars.
    stars_in = Counter()
    for r in repos:
        if r.get("primaryLanguage"):
            stars_in[r["primaryLanguage"]["name"]] += r.get("stargazerCount") or 0
    top = sorted(languages, key=lambda k: (-languages[k], -stars_in[k], k))
    status = u.get("status") or {}
    site = u.get("websiteUrl") or ""
    return {
        "login": u["login"], "name": u.get("name") or "", "bio": u.get("bio") or "",
        "company": u.get("company") or "", "location": u.get("location") or "", "website": site,
        "twitter": u.get("twitterUsername") or "", "created": day(u.get("createdAt")),
        "followers": ((u.get("followers") or {}).get("totalCount")) or 0,
        "following": ((u.get("following") or {}).get("totalCount")) or 0,
        "repositories": ((u.get("publicRepos") or {}).get("totalCount")) or 0,
        "stars": sum(r.get("stargazerCount") or 0 for r in repos),
        "contributions": ((((u.get("contributionsCollection") or {}).get("contributionCalendar")) or {})
                          .get("totalContributions")) or 0,
        "language": top[0] if top else "",
        "status": {"emoji": status_emoji(status.get("emojiHTML")), "message": (status.get("message") or "").strip()},
    }


def resolve(mode: str, subject: str, here: str) -> tuple[str, str, str]:
    """(mode, the subject, the repository whose README carries the banners) from the config and the environment.

    `here` is the repository the workflow runs in, `owner/name`. In auto
    mode the one named after its owner is a profile repository.
    """
    owner, _, name = here.partition("/")
    if mode == "auto":
        if subject:
            mode = "repository" if "/" in subject else "profile"
        else:
            mode = "profile" if owner and name and owner.lower() == name.lower() else "repository"
    if mode == "repository":
        full = subject or here
        if "/" not in full:
            raise SystemExit("repository mode needs subject: owner/name (or GITHUB_REPOSITORY)")
        return mode, full, here or full
    login = subject or owner
    if not login:
        raise SystemExit("profile mode needs subject: a login (or GITHUB_REPOSITORY)")
    return mode, login, here or f"{login}/{login}"


def measure(gh, mode: str, subject: str, here: str, *, today: str) -> dict:
    """The measurement: the mode, its subject, the README's repository, and in profile mode the person."""
    notes: list[str] = []
    mode, subject, readme_repo = resolve(mode, subject, here)
    result: dict = {"mode": mode, "subject": subject, "today": today}
    if mode == "profile":
        result["profile"] = profile(gh, subject, notes)
    target = subject if mode == "repository" else readme_repo
    owner, _, name = target.partition("/")
    try:
        result["repository"] = repository(gh, owner, name, notes)
    except RuntimeError as exc:
        if mode == "repository":
            raise
        # A profile measured from somewhere other than its own repository still has a header.
        notes.append(f"{exc}; the footer's licence and date are left off")
        result["repository"] = None
    result["notes"] = notes
    result["api"] = {"calls": gh.calls, "points": gh.points}
    return result
