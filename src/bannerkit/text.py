# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-FileCopyrightText: 2020 The Cinzel Project Authors (Cinzel outlines)
# SPDX-FileCopyrightText: 2017 The Barlow Project Authors (Barlow Condensed outlines)
# SPDX-License-Identifier: MIT
"""Outlined lettering, so a banner looks the same on every device.

A README image cannot load a web font, and the viewer's system font differs
by platform, so every letter is drawn as a path. The outlines are trophies'
`fonts/glyphs.json`, verbatim, plus `fonts/glyphs-extra.json` for the
characters a header or footer needs and a trophy never did: the space, `@`,
brackets, quotes. `src/extract-glyphs.py` made the supplement from the same
three fonts and proved it reproduces every glyph trophies already had.

Three faces, named the way trophies names them:

  serif   Cinzel Bold: titles, engraving, anything that should feel struck
  meta    Barlow Condensed SemiBold: prose, captions, the terminal line
  num     Barlow Condensed Bold: the heavier cut, for a title that shouts

Each SVG embeds only the glyphs it uses, once, and places them with `<use>`.
Nothing is set as `<text>`: every letter on a banner is a path.
"""
from __future__ import annotations

import itertools
import json

FILES = ("glyphs.json", "glyphs-extra.json")

# Glyph ids are the face's letter and the code point: `m64` is Barlow's `@`.
# None of these letters is a hex digit, which is what lets the lint tell a
# reference like `#m64` from a colour like `#ABCDEF`.
PREFIX = {"serif": "s", "num": "n", "meta": "m"}

# What an unknown character advances by, in ems. It is drawn as nothing; the
# kit reports it rather than guessing a shape.
UNKNOWN_EM = 0.5

_FONTS: dict | None = None


def fonts_dir():
    from pathlib import Path

    return Path(__file__).resolve().parents[1] / "fonts"


def use(*tables: dict) -> dict:
    """Merge glyph tables, earlier first, and make them the ones every run uses.

    The kit reads its two files from disk; the preview page, which has no
    disk, hands the same two tables in here instead.
    """
    global _FONTS
    merged: dict = {}
    for table in tables:
        for face, data in table.items():
            into = merged.setdefault(face, {"upem": data["upem"], "cap": data["cap"], "g": {}})
            for ch, glyph in data["g"].items():
                into["g"].setdefault(ch, glyph)
    _FONTS = merged
    return merged


def fonts() -> dict:
    """Both files, merged per face. The supplement never overrides a glyph."""
    if _FONTS is None:
        use(*(json.loads((fonts_dir() / name).read_text(encoding="utf-8")) for name in FILES))
    return _FONTS


def _key(font: dict, ch: str) -> str | None:
    """The glyph for a character, or its uppercase, or None."""
    g = font["g"]
    if ch in g:
        return ch
    up = ch.upper()
    return up if up in g else None


def missing(text: str, face: str = "meta") -> str:
    """The characters of `text` this face cannot draw, in order, once each."""
    font = fonts()[face]
    seen = []
    for ch in text:
        if _key(font, ch) is None and ch not in seen:
            seen.append(ch)
    return "".join(seen)


def advances(text: str, face: str = "meta", size: float = 12, ls: float = 0) -> list[float]:
    """Each character's advance in pixels, letter-spacing included except after the last."""
    font = fonts()[face]
    sc = size / font["upem"]
    out = []
    for i, ch in enumerate(text):
        key = _key(font, ch)
        adv = font["g"][key][1] * sc if key else UNKNOWN_EM * size
        out.append(adv + (ls if i < len(text) - 1 else 0))
    return out


def width(text: str, face: str = "meta", size: float = 12, ls: float = 0) -> float:
    """Advance width of `text` at `size`, with letter-spacing `ls` between glyphs."""
    return sum(advances(text, face, size, ls))


def cap_height(face: str, size: float) -> float:
    font = fonts()[face]
    return font["cap"] * size / font["upem"]


def fx(v: float, places: int = 3) -> str:
    """`v` to at most `places` decimals, trailing zeros dropped, by rounding an integer.

    Not a format spec, on purpose. A spec like `.4f` rounds the exact binary
    value, and the two Pythons this kit runs on (CPython, and Brython in the
    preview page) disagree on a near tie at the last place. Both round an
    integer the same way, so the same banner comes out byte for byte.
    """
    n = round(v * 10 ** places)
    digits = str(abs(n)).rjust(places + 1, "0")
    head, tail = digits[:-places], digits[-places:].rstrip("0")
    return ("-" if n < 0 else "") + head + ("." + tail if tail else "")


def f1(n: float) -> str:
    """One decimal, no trailing zero: the number format every coordinate uses."""
    return fx(n, 1)


def fit(text: str, face: str, max_w: float, size: float, floor: float, ls: float = 0) -> float:
    """The largest size, in half-pixel steps from `size` down to `floor`, at which `text` fits."""
    while size > floor and width(text, face, size, ls) > max_w:
        size -= 0.5
    return size


def wrap(text: str, face: str, size: float, max_w: float, ls: float = 0, rows: int = 3) -> list[str] | None:
    """The fewest lines that fit, then the evenest split of that many; None if `rows` is not enough.

    Evenest, not greedy, for the reason the masthead gives: greedy wrapping
    fills the first line and leaves the last holding one word, which reads
    as a mistake rather than as a wrapped line.
    """
    words = text.split()
    if not words:
        return []
    for count in range(1, min(rows, len(words)) + 1):
        best = None
        for cuts in itertools.combinations(range(1, len(words)), count - 1):
            bounds = (0, *cuts, len(words))
            lines = [" ".join(words[a:b]) for a, b in zip(bounds, bounds[1:])]
            widest = max(width(line, face, size, ls) for line in lines)
            if widest <= max_w and (best is None or widest < best[0]):
                best = (widest, lines)
        if best:
            return best[1]
    return None


def flow(text: str, face: str, size: float, floor: float, max_w: float, ls: float = 0,
         rows: int = 3) -> tuple[float, list[str]]:
    """Wrap into at most `rows` lines, shrinking toward `floor` only if it must."""
    while True:
        lines = wrap(text, face, size, max_w, ls, rows)
        if lines is not None:
            return size, lines
        if size <= floor:
            # Nothing fits: take more lines rather than overflow the plate.
            return size, wrap(text, face, size, max_w, ls, 12) or [text]
        size = max(floor, size - 0.5)


class Lettering:
    """Collects the glyphs one SVG uses, so `defs()` can embed each once."""

    def __init__(self) -> None:
        self.used: set[tuple[str, str]] = set()
        # The smallest type this image sets. The breakpoint a phone switches
        # at is derived from it, so it is measured here rather than guessed.
        self.smallest: float = 1e9

    def text(self, s: str, *, face: str = "meta", size: float = 12, x: float = 0, y: float = 0,
             anchor: str = "start", ls: float = 0, fill: str | None, opacity: float | None = None,
             oblique: float = 0, attrs: str = "") -> str:
        """A run of outlined glyphs with its baseline at `y`.

        `oblique` slants the run by that many degrees, for the one place a
        README would use italics: the motto. Neither font here has an italic,
        and a slanted roman is what the eye expects from a caption anyway.
        """
        if not s:
            return ""
        font = fonts()[face]
        sc = size / font["upem"]
        w = width(s, face, size, ls)
        x0 = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
        self.smallest = min(self.smallest, size)
        adv = 0.0
        uses = []
        for ch in s:
            key = _key(font, ch)
            if key and key != " ":
                self.used.add((face, key))
                uses.append(f'<use href="#{PREFIX[face]}{ord(key)}" x="{round(adv)}"/>')
            adv += (font["g"][key][1] if key else font["upem"] * UNKNOWN_EM) + ls / sc
        skew = f" skewX({f1(-oblique)})" if oblique else ""
        op = f' fill-opacity="{fx(opacity)}"' if opacity is not None else ""
        paint = f' fill="{fill}"' if fill else ""
        return (f'<g transform="translate({f1(x0)} {f1(y)}){skew} scale({fx(sc, 5)} {fx(-sc, 5)})"'
                f'{paint}{op}{attrs}>' + "".join(uses) + "</g>")

    def scatter(self, items: list[tuple[float, float, str]], *, face: str = "meta", size: float = 12, fill: str,
                opacity: float | None = None) -> str:
        """Short labels set anywhere, each centred on its (x, y) baseline point, as one group of glyphs.

        A drawing's zone marks are a score of one-character labels; a group
        each would cost more than their outlines, so they share one.
        """
        font = fonts()[face]
        sc = size / font["upem"]
        self.smallest = min(self.smallest, size)
        uses = []
        for x, y, text in items:
            adv = (x - width(text, face, size) / 2) / sc
            for ch in text:
                key = _key(font, ch)
                if key and key != " ":
                    self.used.add((face, key))
                    uses.append(f'<use href="#{PREFIX[face]}{ord(key)}" x="{round(adv)}" y="{round(-y / sc)}"/>')
                adv += font["g"][key][1] if key else font["upem"] * UNKNOWN_EM
        op = f' fill-opacity="{fx(opacity)}"' if opacity is not None else ""
        return f'<g transform="scale({fx(sc, 5)} {fx(-sc, 5)})" fill="{fill}"{op}>' + "".join(uses) + "</g>"

    def defs(self) -> str:
        out = []
        for face, ch in sorted(self.used, key=lambda k: (k[0], ord(k[1]))):
            out.append(f'<path id="{PREFIX[face]}{ord(ch)}" d="{fonts()[face]["g"][ch][0]}"/>')
        return "".join(out)
