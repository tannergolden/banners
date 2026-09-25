# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""One SVG in progress, and the lint every finished one has to pass.

A banner ends up as an `<img>` in a README, which is a strict place to live:
GitHub serves the file with a policy that runs no script and fetches
nothing, and a viewer's theme decides which of two files it sees. So every
file is self-contained, and `lint()` checks the things that would break it
quietly: a script, a `foreignObject`, an external reference, a colour that is
not an emblems token, a missing title or description, a dash the standards
ban, a reference to an id that does not exist, and a file grown too large.
"""
from __future__ import annotations

import re
from html import escape

from . import KIT_VERSION
from .palette import HEXES, hexof
from .text import Lettering

# The two themes GitHub paints behind a README, as ink roles. Every role is a
# palette token, so a design never reaches for a colour of its own.
#
#   ink     body text        strong  titles          muted  secondary text
#   faint   captions, rules  hair    hairlines       paper  a plate's own ground
DAY = {"name": "day", "dark": False, "ink": "charcoal", "strong": "black", "muted": "slate",
       "faint": "gray", "hair": "ash", "paper": "white"}
DARK = {"name": "dark", "dark": True, "ink": "white", "strong": "white", "muted": "ash",
        "faint": "gray", "hair": "charcoal", "paper": "black"}
THEMES = {"day": DAY, "dark": DARK}


def c(token: str) -> str:
    """A palette token as the hex a file carries."""
    return hexof(token)


class Canvas:
    """Shared machinery for one image: ids, defs, style, lettering, and the root element."""

    def __init__(self, w: float, h: float, *, title: str, desc: str, stamp: str) -> None:
        self.w, self.h = w, h
        self.title, self.desc, self.stamp = title, desc, stamp
        self.L = Lettering()
        self.defs: list[str] = []
        self.css: list[str] = []
        self.body: list[str] = []
        self._ids = 0

    def uid(self, base: str = "") -> str:
        """A fresh id. It starts with `k`, so no id can read as a colour to the lint."""
        self._ids += 1
        return f"k{base}{self._ids}"

    def add(self, *markup: str) -> None:
        self.body.extend(m for m in markup if m)

    def svg(self) -> str:
        w, h = round(self.w), round(self.h)
        css = "".join(self.css)
        glyphs = self.L.defs()
        defs = "".join(self.defs) + glyphs
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d"><title id="t">{escape(self.title)}</title>'
            f'<desc id="d">{escape(self.desc)}</desc><!--banner-kit v{KIT_VERSION} {self.stamp}-->'
            + (f"<defs>{defs}</defs>" if defs else "")
            + (f"<style>{css}</style>" if css else "")
            + "".join(self.body) + "</svg>\n"
        )


# --- the lint -----------------------------------------------------------------------

_BANNED = ("<script", "foreignobject", "<image", "@import", "<iframe", "<object", "<embed", "javascript:")
_EXTERNAL = re.compile(r'(?:href|src)\s*=\s*["\'](?!#)|url\(\s*["\']?(?!#)', re.I)
_HEX = re.compile(r"#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})(?![0-9A-Za-z_-])")
_PAINT = re.compile(r'(?<![\w-])(fill|stroke|stop-color|flood-color|lighting-color|color)\s*(?:=\s*"|:\s*)([^";}]+)')
_ID = re.compile(r'\bid="([^"]+)"')
_REF = re.compile(r'(?:href="#|url\(#)([^")]+)')
_TEXT = re.compile(r"<text\b([^>]*)>")
_DASHES = ("\u2013", "\u2014", "\u2015", "&#x2013;", "&#x2014;", "&#x2015;")

# Budgets, in bytes. A README page loads every one of these on every view, so
# a banner is held to the size of the masthead that inspired half of them.
# The masthead's animated file is 35 KB and trophies' level card 26 KB. A
# banner with ordinary content lands between 20 and 35 KB; these caps leave
# room for the longest titles in the family, whose outlines are most of it.
BUDGET = {"motion": 48_000, "still": 48_000, "narrow": 48_000, "link": 12_000}


# What re.I lets stand for each letter a case-blind needle is made of: its
# capital, and for s the long s too.
_CASES = {"h": "hH", "r": "rR", "e": "eE", "f": "fF", "s": "sS\u017f", "c": "cC", "u": "uU", "l": "lL"}


def _spellings(word: str) -> list[str]:
    """Every way `word` can be written for a pattern that ignores case."""
    out = [""]
    for ch in word:
        out = [head + alt for head in out for alt in _CASES.get(ch, ch)]
    return out


def _stop(text: str, i: int, stops: str) -> int:
    """The offset just past the first of `stops` at or after `i`, or the end of `text`."""
    found = [j for j in (text.find(ch, i) for ch in stops) if j >= 0]
    return min(found) + 1 if found else len(text)


def _matches(pattern: re.Pattern, text: str, starts: tuple[str, ...], window, fold: bool = False) -> list:
    """What `pattern.finditer(text)` finds, tried only where a match can begin, on only the text it can reach.

    Every pattern the lint uses begins with a literal, one of `starts`, and
    ends at or before a character `window(i, start)` finds, so matching the
    slice between them, with one character before it for a lookbehind, finds
    the same matches, in the same order. It matters in the preview page,
    where `re` is pure Python and pays for the whole string on every call:
    a second a file becomes a few milliseconds. With `fold`, a start is
    looked for in every spelling a case-blind pattern accepts.
    """
    spots = []
    for start in starts:
        for spelling in (_spellings(start) if fold else (start,)):
            i = text.find(spelling)
            while i >= 0:
                spots.append((i, start))
                i = text.find(spelling, i + 1)
    found, end = [], 0
    for i, start in sorted(spots):
        if i < end:
            continue
        lo = max(0, i - 1)
        m = pattern.match(text[lo:window(i, start)], i - lo)
        if m:
            found.append(m)
            end = lo + m.end()
    return found


def lint(svg: str, *, budget: int, text_ok: bool = False) -> list[str]:
    """Everything wrong with `svg` as a README image, or an empty list.

    No `<text>` is allowed: every letter is a path. `text_ok` would admit it,
    for a design set in a font, and no design here is.
    """
    problems = []
    low = svg.lower()
    for word in _BANNED:
        if word in low:
            problems.append(f"contains {word}")
    # After href or src: a quote and the one character the lookahead reads. After url(: the one it reads.
    if _matches(_EXTERNAL, svg, ("href", "src", "url("),
                lambda i, n: i + 5 if n == "url(" else min(len(svg), _stop(svg, i + len(n), "\"'") + 1), fold=True):
        problems.append("references something outside the file")
    if 'role="img"' not in svg:
        problems.append('no role="img"')
    title = re.search(r'<title id="t">([^<]*)</title>', svg)
    desc = re.search(r'<desc id="d">([^<]*)</desc>', svg)
    if not title or not title.group(1).strip():
        problems.append("no title")
    if not desc or not desc.group(1).strip():
        problems.append("no description")
    for hexc in (m.group(1) for m in _matches(_HEX, svg, ("#",), lambda i, n: i + 8)):
        full = hexc if len(hexc) == 6 else "".join(ch * 2 for ch in hexc)
        if f"#{full.upper()}" not in HEXES:
            problems.append(f"#{hexc} is not an emblems token")
    # A paint's value ends at the first of " ; } after it, which is the second after the name when an = opens it.
    paints = _matches(_PAINT, svg, ("fill", "stroke", "stop-color", "flood-color", "lighting-color", "color"),
                      lambda i, n: _stop(svg, _stop(svg, i + len(n), '";}'), '";}'))
    for prop, value in (m.groups() for m in paints):
        value = value.strip()
        if value == "none" or value.startswith("url(#") or value.upper() in HEXES:
            continue
        if prop == "fill" and value in ("freeze", "remove"):
            continue   # SMIL's own `fill`, which says what an animation leaves behind, not a colour
        problems.append(f"{prop} {value!r} is not a token")
    ids = [m.group(1) for m in _matches(_ID, svg, ('id="',), lambda i, n: _stop(svg, i + 4, '"'))]
    if len(ids) != len(set(ids)):
        problems.append("duplicate ids")
    for i in ids:
        if re.fullmatch(r"[0-9a-fA-F]{3}|[0-9a-fA-F]{6}", i):
            problems.append(f"id {i!r} reads as a colour")
    # First seen, first reported: a set's order differs from one Python to the next.
    refs = dict.fromkeys(m.group(1) for m in _matches(_REF, svg, ('href="#', "url(#"), lambda i, n: _stop(svg, i + len(n), '")')))
    for ref in refs:
        if ref not in ids:
            problems.append(f"#{ref} is referenced but never defined")
    texts = [m.group(1) for m in _matches(_TEXT, svg, ("<text",), lambda i, n: _stop(svg, i + 5, ">"))]
    if not text_ok and texts:
        problems.append("text not drawn as paths")
    if any(d in svg for d in _DASHES):
        problems.append("an en or em dash")
    size = len(svg.encode("utf-8"))
    if size > budget:
        problems.append(f"{size:,} bytes, over the {budget:,} budget")
    return problems
