# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Layout helpers the designs share: a vertical cursor and the title run.

Sizes are CSS pixels at the size the file declares. A wide file is 830 px,
the width of a README column on a desktop; a narrow one is 360 px, a phone's
viewport, which GitHub scales to its roughly 330 px column.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .canvas import Canvas, c
from .content import Header
from .text import width

WIDE, NARROW = 830, 360


@dataclass(frozen=True)
class Design:
    """One direction: its code (H1..H3, F1..F2), its name, and the function that draws it.

    `draw(content, theme, wide, motion)` returns the SVG. A footer also has
    `chip(label, theme, tone)`, the small linked image its links row is made of.
    `text_ok` would admit `<text>`; no design here needs it.
    """
    code: str
    slug: str
    name: str
    blurb: str
    animates: bool
    pairs: tuple
    draw: Callable
    kind: str = "header"
    text_ok: bool = False
    chip: Callable | None = None

# How far below the baseline mixed-case text reaches, and how far above it
# the tallest letters stand, in ems. Barlow puts its capitals at .70.
DESCENT = .22
ASCENT = .74


class Flow:
    """A top-to-bottom cursor. `line()` returns the baseline for a line of `size` and moves past it."""

    def __init__(self, y: float) -> None:
        self.y = y

    def line(self, size: float, caps: bool = False, lead: float = 1.0) -> float:
        base = self.y + size * (.70 if caps else ASCENT)
        self.y = base + (0 if caps else size * DESCENT) + size * (lead - 1)
        return base

    def gap(self, px: float) -> None:
        self.y += px


def title_width(h: Header, face: str, size: float, ls_em: float) -> float:
    """How wide the capped title is set at `size`."""
    return width(h.caps, face, size, size * ls_em) if h.caps else 0


def fit_title(h: Header, face: str, size: float, floor: float, max_w: float, ls_em: float) -> float:
    while size > floor:
        if title_width(h, face, size, ls_em) <= max_w:
            break
        size -= 1
    return size


def title_lines(h: Header, face: str, size: float, floor: float, max_w: float, ls_em: float) -> tuple[float, list[str]]:
    """The capped title at the largest size that fits: on one line while it can, else balanced over two.

    One line wins while it can be set at no less than six tenths of the
    design's size; below that a two-line title set larger reads better than
    one line set small.
    """
    one = fit_title(h, face, size, floor, max_w, ls_em)
    words = h.caps.split()
    if (title_width(h, face, one, ls_em) <= max_w and one >= size * .6) or len(words) < 2:
        return one, [h.caps]
    best = None
    for cut in range(1, len(words)):
        lines = [" ".join(words[:cut]), " ".join(words[cut:])]
        s = size
        while s > floor * .8:
            w1 = width(lines[0], face, s, s * ls_em)
            w2 = width(lines[1], face, s, s * ls_em)
            if max(w1, w2) <= max_w:
                break
            s -= 1
        balance = abs(width(lines[0], face, s) - width(lines[1], face, s))
        if best is None or (s, -balance) > (best[0], -best[2]):
            best = (s, lines, balance)
    if best and best[0] > one:
        return best[0], best[1]
    return one, [h.caps]


def title_block(cv: Canvas, h: Header, lines: list[str], *, face: str, size: float, ls_em: float, flow: "Flow",
                fill: str, cx: float | None = None, x: float | None = None, lead: float = 1.12,
                attrs: str = "") -> tuple[float, float, float]:
    """Draw the title's lines down `flow`; returns (left, right, top of the first line)."""
    left_all, right_all, top = 1e9, -1e9, flow.y
    for i, line in enumerate(lines):
        base = flow.line(size, caps=True)
        if i == 0:
            top = base - size * .70
            part = h.with_(title=line) if len(lines) > 1 else h
            l, r = title_run(cv, part, face=face, size=size, ls_em=ls_em, baseline=base, fill=fill, cx=cx, x=x,
                             attrs=attrs)
        else:
            tw = width(line, face, size, size * ls_em)
            l = cx - tw / 2 if cx is not None else x
            r = l + tw
            cv.add(cv.L.text(line, face=face, size=size, x=l, y=base, ls=size * ls_em, fill=c(fill), attrs=attrs))
        left_all, right_all = min(left_all, l), max(right_all, r)
        if i < len(lines) - 1:
            flow.gap(size * (lead - 1) + size * .22)
    return left_all, right_all, top


def title_run(cv: Canvas, h: Header, *, face: str, size: float, ls_em: float, baseline: float, fill: str,
              cx: float | None = None, x: float | None = None, attrs: str = "") -> tuple[float, float]:
    """The capped title, centred on `cx` or starting at `x`. Returns its extent."""
    tw = title_width(h, face, size, ls_em)
    left = cx - tw / 2 if cx is not None else x
    if tw:
        cv.add(cv.L.text(h.caps, face=face, size=size, x=left, y=baseline, ls=size * ls_em,
                         fill=c(fill), attrs=attrs))
    return left, left + tw


