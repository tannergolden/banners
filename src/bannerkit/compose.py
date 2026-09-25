# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A measurement and a config, as the header and the footer the designs draw.

Every value on a banner comes from one of two places: what GitHub says
(the measurement) or what the config says. A field the config leaves
empty is filled from GitHub; a field it sets wins; a field it lists under
`hide` is not drawn at all. So a consumer who writes nothing gets a banner
that reads their repository or profile, and keeps reading it as it
changes, and one who writes a title keeps that title.

  title        the config's, else the repository's name, or the person's name
  tagline      the config's, else the repository's description, or the bio
  motto        the config's, else in profile mode the status message: the
               one general note on the sheet
  emoji        the config's, else the status emoji, else an emoji the
               description or bio opens with
  figures      the ones the config names, in its order, else the mode's
               defaults; one whose value GitHub does not have is left out
  footer       the handle, the licence and the last change, from GitHub;
               the closing phrase and the links row from the config

Text is drawn as outlines from a fixed set of letters, so measured text is
made drawable first: a dash the standards ban becomes a hyphen, a GitHub
`:shortcode:` is dropped, and a character no face holds is left out, with
a note saying so. The alt text is built from what is drawn.

This module is pure: it runs in the preview page, under Brython, too.
"""
from __future__ import annotations

import re

from .content import FOOTER_FIELDS, HEADER_FIELDS, Footer, Header
from .drafting import DEFAULT_PRINT
from .text import missing

# Every figure each mode can draw, in the order the page offers them, with its label.
FIGURES = {
    "repository": {
        "project": "PROJECT", "release": "RELEASE", "stars": "STARS", "forks": "FORKS", "watchers": "WATCHERS",
        "issues": "OPEN ISSUES", "pulls": "OPEN PULL REQUESTS", "language": "LANGUAGE", "license": "LICENSE",
        "updated": "UPDATED", "created": "CREATED", "site": "SITE",
    },
    "profile": {
        "account": "ACCOUNT", "followers": "FOLLOWERS", "following": "FOLLOWING", "repositories": "REPOSITORIES",
        "stars": "STARS EARNED", "contributions": "CONTRIBUTIONS, LAST YEAR", "language": "LANGUAGE",
        "since": "MEMBER SINCE", "location": "LOCATION", "company": "COMPANY", "site": "SITE",
    },
}
DEFAULT_FIGURES = {
    "repository": ("project", "release", "stars", "forks", "issues", "language", "license"),
    "profile": ("account", "followers", "repositories", "stars", "contributions", "language", "since"),
}
# Measured text is clipped here, at a word, before it is drawn.
LIMITS = {"title": 40, "tagline": 160, "motto": 80, "value": 40}
TOP = "Back to Top"

# Characters a measured line may carry that the letters do not: each is
# replaced by what a drafter would letter instead. Written as escapes, since
# the dashes themselves are banned from this repository.
_REPLACE = {
    "\u2014": " - ", "\u2013": "-", "\u2012": "-", "\u2010": "-", "\u2011": "-", "\u2212": "-",
    "\u00a0": " ", "\u2009": " ", "\u202f": " ", "\u2192": "->", "\u2190": "<-",
}
_SHORTCODE = re.compile(r":[a-z0-9_+-]+:")
_SPACES = re.compile(r"\s+")


class CompositionError(ValueError):
    """A config that names something this mode cannot draw."""


def count(n) -> str:
    """A count as a drawing letters it: 1,284 in full, then 128k, then 1.3M."""
    n = int(n or 0)
    if n < 100_000:
        return f"{n:,}"
    if n < 999_500:
        return f"{round(n / 1000)}k"
    m = n / 1_000_000
    return f"{m:.1f}M" if m < 9.95 else f"{round(m)}M"


def host(url: str) -> str:
    """A web address as it is read aloud: no scheme, no www, no trailing slash."""
    url = re.sub(r"^[a-z]+://", "", (url or "").strip(), flags=re.I)
    url = re.sub(r"^www\.", "", url, flags=re.I)
    return url.rstrip("/")


# What an emoji is made of: the pictographs, the symbols and dingbats, the
# regional indicators a flag is two of, and the joiners and selectors that
# bind a sequence together.
_EMOJI = ((0x1F000, 0x1FAFF), (0x2600, 0x27BF), (0x2300, 0x23FF), (0x2B00, 0x2BFF), (0xE0020, 0xE007F))
_BINDERS = (0x200D, 0xFE0F, 0x20E3)


def _emoji_char(ch: str) -> bool:
    c = ord(ch)
    return c in _BINDERS or any(a <= c <= b for a, b in _EMOJI)


def split_emoji(text: str) -> tuple[str, str]:
    """(an emoji the text opens with, the rest). "\U0001F3C6 Trophies for..." gives the cup and "Trophies for...".

    The first word counts when every character of it belongs to an emoji.
    It is split off at whitespace and read by iterating, never by index,
    because under Brython a string that arrived as JSON counts an emoji as
    two units when indexed and as one when iterated.
    """
    text = (text or "").strip()
    parts = text.split(None, 1)
    if not parts:
        return "", text
    chars = list(parts[0])
    if all(_emoji_char(ch) for ch in chars) and any(ord(ch) not in _BINDERS for ch in chars):
        return parts[0], parts[1].strip() if len(parts) > 1 else ""
    return "", text


def drawable(text: str, face: str = "meta", notes: list | None = None, what: str = "") -> str:
    """Text the letters can draw: banned dashes become hyphens, shortcodes and undrawable characters go."""
    out = "".join(_REPLACE.get(ch, ch) for ch in (text or ""))
    out = _SHORTCODE.sub("", out)
    lost = missing(out, face)
    if lost:
        out = "".join(ch for ch in out if ch not in lost)
        if notes is not None and lost.strip():
            notes.append(f"{what or 'a line'}: not drawn, no letter for {lost.strip()!r}")
    return _SPACES.sub(" ", out).strip()


def clip(text: str, limit: int) -> str:
    """At most `limit` characters, cut at a word, with an ellipsis when anything was cut."""
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(" ", 1)[0].rstrip(" ,.;:-")
    return cut + "\u2026"


def _value(mode: str, key: str, m: dict) -> str:
    repo = m.get("repository") or {}
    person = m.get("profile") or {}
    if mode == "repository":
        v = {
            "project": repo.get("full"), "release": repo.get("release"), "language": repo.get("language"),
            "license": repo.get("license"), "updated": repo.get("updated"), "created": (repo.get("created") or "")[:4],
            "site": host(repo.get("homepage") or ""),
        }.get(key)
        if key in ("stars", "forks", "watchers", "issues", "pulls"):
            v = count(repo.get(key)) if key in repo else ""
        return v or ""
    v = {
        "account": "@" + person["login"] if person.get("login") else "", "language": person.get("language"),
        "since": (person.get("created") or "")[:4], "location": person.get("location"), "company": person.get("company"),
        "site": host(person.get("website") or ""),
    }.get(key)
    if key in ("followers", "following", "repositories", "stars", "contributions"):
        v = count(person.get(key)) if key in person else ""
    return v or ""


def figures(mode: str, m: dict, wanted, notes: list) -> tuple:
    """The (LABEL, value) pairs a header draws: the config's keys, else the mode's defaults, each only if measured."""
    labels = FIGURES[mode]
    keys = list(wanted) if wanted else list(DEFAULT_FIGURES[mode])
    bad = [k for k in keys if k not in labels]
    if bad:
        raise CompositionError(f"figures: {', '.join(repr(k) for k in bad)} not a {mode} figure "
                               f"({', '.join(labels)})")
    out = []
    for k in keys:
        v = drawable(_value(mode, k, m), "meta", notes, f"figure {k}")
        if v:
            out.append((labels[k], clip(v, LIMITS["value"])))
    return tuple(out)


def every_figure(mode: str, m: dict) -> list[tuple[str, str, str]]:
    """(key, LABEL, value) for every figure this mode can draw, measured or not: what the preview page offers."""
    return [(k, label, clip(drawable(_value(mode, k, m), "meta"), LIMITS["value"])) for k, label in FIGURES[mode].items()]


def _pick(cfg: dict, key: str, measured: str) -> str:
    given = cfg.get(key)
    return str(given).strip() if given not in (None, "") else measured


def links(mode: str, m: dict) -> tuple:
    """The links row when the config names none: the website, and a repository's releases and issues."""
    repo = m.get("repository") or {}
    person = m.get("profile") or {}
    out = []
    site = (person.get("website") if mode == "profile" else repo.get("homepage")) or ""
    if site:
        out.append(("Website", site if re.match(r"^[a-z]+://", site, re.I) else "https://" + site))
    # Absolute, since a relative link resolves against whatever page shows
    # the README, which on a profile is not the repository.
    home = f"https://github.com/{repo.get('full')}" if repo.get("full") else ""
    if mode == "repository" and home:
        if repo.get("releases"):
            out.append(("Releases", f"{home}/releases"))
        if repo.get("issuesOn"):
            out.append(("Issues", f"{home}/issues"))
    return tuple(out)


def compose(m: dict, cfg: dict) -> tuple[Header, Footer, list[str]]:
    """The header and footer for a measurement under a config, and notes on anything left out."""
    notes: list[str] = []
    mode = m["mode"]
    repo = m.get("repository") or {}
    person = m.get("profile") or {}
    off = frozenset(cfg.get("hide") or ())
    tone = cfg.get("theme") or DEFAULT_PRINT

    if mode == "profile":
        name = drawable(person.get("name") or "", "num", notes, "name")
        # A name the letters can mostly not draw is better read as the login.
        title = name if name and len(name) >= .6 * len((person.get("name") or "").strip()) else person.get("login", "")
        told = person.get("bio") or ""
        status = person.get("status") or {}
        note = drawable(status.get("message") or "", "meta", notes, "status")
        opens = status.get("emoji") or ""
    else:
        title = repo.get("name") or ""
        told = repo.get("description") or ""
        note = ""
        opens = ""
    lead, told = split_emoji(told)
    emoji = _pick(cfg, "emoji", opens or lead)
    header = Header(
        emoji=emoji,
        title=clip(drawable(_pick(cfg, "title", title), "num", notes, "title"), LIMITS["title"]),
        tagline=clip(drawable(_pick(cfg, "tagline", told), "meta", notes, "tagline"), LIMITS["tagline"]),
        motto=clip(drawable(_pick(cfg, "motto", note), "meta", notes, "motto"), LIMITS["motto"]),
        description=drawable(_pick(cfg, "description", ""), "meta", notes, "description"),
        figures=figures(mode, m, cfg.get("figures"), notes),
        tone=tone,
        off=frozenset(k for k in off if k in HEADER_FIELDS),
    )
    given = cfg.get("links")
    footer = Footer(
        closing=drawable(_pick(cfg, "closing", ""), "meta", notes, "closing"),
        top=drawable(_pick(cfg, "top", TOP), "meta", notes, "top"),
        handle="@" + (person.get("login") if mode == "profile" else repo.get("owner") or ""),
        license=repo.get("license") or "",
        updated=repo.get("updated") or "",
        links=tuple((drawable(str(label), "meta"), str(url)) for label, url in given) if given else links(mode, m),
        tone=tone,
        off=frozenset(k for k in off if k in FOOTER_FIELDS),
    )
    return header, footer, notes
