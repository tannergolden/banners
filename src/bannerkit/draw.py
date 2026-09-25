# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Drawing helpers every design shares: icons, the grain, a clip.

Everything takes palette tokens, never hex, so a design cannot reach for a
colour outside the family even by accident.
"""
from __future__ import annotations

from .canvas import Canvas, c
from .palette import ICONS
from .text import f1, fx


def icon(name: str, x: float, y: float, size: float, stroke: str, sw: float = 2, opacity: float | None = None,
         attrs: str = "") -> str:
    """An emblems icon, stroked, with its 24x24 box's top-left at (x, y)."""
    op = f' stroke-opacity="{fx(opacity)}"' if opacity is not None else ""
    return (f'<g transform="translate({f1(x)} {f1(y)}) scale({fx(size / 24, 4)})" fill="none" stroke="{c(stroke)}" '
            f'stroke-width="{fx(sw)}" stroke-linecap="round" stroke-linejoin="round"{op}{attrs}>{ICONS[name]}</g>')


def solid(name: str, x: float, y: float, size: float, fill: str, attrs: str = "") -> str:
    """An emblems icon filled rather than stroked: the heart that stands for the love in "built with"."""
    return (f'<g transform="translate({f1(x)} {f1(y)}) scale({fx(size / 24, 4)})" fill="{c(fill)}" stroke="{c(fill)}" '
            f'stroke-width="1.2" stroke-linejoin="round"{attrs}>{ICONS[name]}</g>')


def up_arrow(x: float, y: float, size: float, stroke: str, sw: float = 2.4) -> str:
    """Emblems' `arrow`, turned to point up: the arrow in "Back to Top"."""
    half = size / 2
    return (f'<g transform="rotate(-90 {f1(x + half)} {f1(y + half)})">'
            + icon("arrow", x, y, size, stroke, sw) + "</g>")


def grain(cv: Canvas, alpha: float, light: bool) -> str:
    """Trophies' grain: fractal noise at a low alpha, so a flat plate reads as a material."""
    fid = cv.uid("n")
    rgb = "1" if light else "0"
    cv.defs.append(
        f'<filter id="{fid}" x="0" y="0" width="100%" height="100%">'
        '<feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" stitchTiles="stitch"/>'
        f'<feColorMatrix values="0 0 0 0 {rgb} 0 0 0 0 {rgb} 0 0 0 0 {rgb} 0 0 0 {fx(alpha)} 0"/></filter>')
    return fid


def clip_rect(cv: Canvas, x, y, w, h, rx=0) -> str:
    cid = cv.uid("c")
    cv.defs.append(f'<clipPath id="{cid}"><rect x="{f1(x)}" y="{f1(y)}" width="{f1(w)}" height="{f1(h)}"'
                   + (f' rx="{f1(rx)}"' if rx else "") + "/></clipPath>")
    return cid


