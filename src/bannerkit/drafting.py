# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Drafting: what every banner here is drawn with.

A banner is a sheet from a set of drawings, the header the first sheet of
the set and the footer the second. This module holds what every sheet
shares: the print's colours, the paper with its grain, grid, border and
zone marks, dimensions, numbered notes, a title block's cells, and the
plotter that draws the linework in as the page opens.

Line weights follow a drawing's: the border heaviest, then the title
block's frame, then its rules and the dimensions, and the grid finest.
"""
from __future__ import annotations

import math

from .canvas import Canvas, c
from .draw import clip_rect, grain
from .text import cap_height, f1, fit, flow, fx, width

# A print is the colour a drawing is reproduced in: its lines and lettering
# on white paper by day, and by night the sheet those lines are printed on.
# The family runs the spectrum, red to pink, then the two the trade named
# first after the blueprint: the brownprint (Van Dyke) and the blackprint
# (black-line). Every colour is a palette token.
#
# By day a print's lines take `line` and its lettering `ink`, dark enough
# to read on white. By night the sheet is `sheet`, lettered in `night`:
# white on the deep sheets, black on the two bright ones, yellow and
# orange, which white could not be read on.
PRINTS = {
    "redprint": dict(label="Redprint", line="cherry", ink="maroon", sheet="cherry"),
    "orangeprint": dict(label="Orangeprint", line="tangerine", ink="brick", sheet="tangerine", night="black"),
    "yellowprint": dict(label="Yellowprint", line="mustard", ink="charcoal", sheet="mustard", night="black"),
    "greenprint": dict(label="Greenprint", line="forest", ink="forest", sheet="forest"),
    "tealprint": dict(label="Tealprint", line="teal", ink="ocean", sheet="ocean"),
    "blueprint": dict(label="Blueprint", line="cobalt", ink="navy", sheet="navy"),
    "indigoprint": dict(label="Indigoprint", line="iris", ink="indigo", sheet="indigo"),
    "purpleprint": dict(label="Purpleprint", line="plum", ink="amethyst", sheet="amethyst"),
    "pinkprint": dict(label="Pinkprint", line="magenta", ink="ruby", sheet="ruby"),
    "brownprint": dict(label="Brownprint", line="brown", ink="brown", sheet="brown"),
    "blackprint": dict(label="Blackprint", line="charcoal", ink="black", sheet="charcoal"),
}
DEFAULT_PRINT = "blueprint"
# The rainbow, in order. A banner in `rainbowprint` is drawn in one of these
# and moves to the next each time an update redraws it.
SPECTRUM = ("redprint", "orangeprint", "yellowprint", "greenprint", "tealprint", "blueprint", "indigoprint",
            "purpleprint", "pinkprint")
RAINBOW = "rainbowprint"


def colours(tone: str, th: dict) -> dict:
    """A print in a theme: `line` for linework, `ink` for lettering, `paper`, and `edge`, the day sheet's outline."""
    p = PRINTS.get(tone) or PRINTS[SPECTRUM[0] if tone == RAINBOW else DEFAULT_PRINT]
    dark = th["dark"]
    night = p.get("night", "white")
    return {"line": night if dark else p["line"], "ink": night if dark else p["ink"],
            "paper": p["sheet"] if dark else "white", "edge": p["line"], "dark": dark}


def hair(col: dict, opacity: float = .8) -> str:
    return f'stroke="{c(col["line"])}" stroke-opacity="{fx(opacity)}"'


# --- the sheet ---------------------------------------------------------------------------

def sheet(cv: Canvas, col: dict, *, W: float, H: float, border: float, zones: int, top: float = 0,
          rx: float = 6, plain: tuple = ()) -> None:
    """The paper: grain, a grid of 10 and 50 pixels inside the border, and zone marks between the border and the edge.

    Drawn once the content is measured, so the sheet is as tall as its
    content needs, and before the content, so it lies underneath. `plain`
    names regions, (x, y, w, h), the grid leaves out: a title block's cells
    are printed on plain paper, where small lettering reads cleanly.
    """
    h = H - top
    dark = col["dark"]
    cv.add(f'<rect y="{f1(top)}" width="{W}" height="{f1(h)}" rx="{rx}" fill="{c(col["paper"])}"'
           + ("" if dark else f' stroke="{c(col["edge"])}" stroke-opacity=".35"') + "/>")
    if not dark:
        # A print by day is never quite white: the faintest wash of its own line colour.
        cv.add(f'<rect y="{f1(top)}" width="{W}" height="{f1(h)}" rx="{rx}" fill="{c(col["edge"])}" fill-opacity=".03"/>')
    # The paper's tooth: trophies' grain, lighter on a print than on brass.
    paper = clip_rect(cv, 0, top, W, h, rx)
    cv.add(f'<rect y="{f1(top)}" width="{W}" height="{f1(h)}" clip-path="url(#{paper})" '
           f'filter="url(#{grain(cv, .06 if dark else .035, dark)})"/>')
    minor, major = cv.uid("p"), cv.uid("p")
    so = (.075, .16) if dark else (.07, .14)
    cv.defs.append(f'<pattern id="{minor}" width="10" height="10" patternUnits="userSpaceOnUse">'
                   f'<path d="M10 .5H.5V10" fill="none" {hair(col, so[0])}/></pattern>'
                   f'<pattern id="{major}" width="50" height="50" patternUnits="userSpaceOnUse">'
                   f'<path d="M50 .5H.5V50" fill="none" {hair(col, so[1])}/></pattern>')
    if plain:
        rects = [(border, top + border, W - 2 * border, h - 2 * border), *plain]
        inside = cv.uid("c")
        cv.defs.append(f'<clipPath id="{inside}"><path clip-rule="evenodd" d="'
                       + "".join(f"M{f1(x)} {f1(y)}h{f1(w)}v{f1(hh)}h{f1(-w)}z" for x, y, w, hh in rects)
                       + '"/></clipPath>')
    else:
        inside = clip_rect(cv, border, top + border, W - 2 * border, h - 2 * border)
    cv.add(f'<g clip-path="url(#{inside})"><rect y="{f1(top)}" width="{W}" height="{f1(h)}" fill="url(#{minor})"/>'
           f'<rect y="{f1(top)}" width="{W}" height="{f1(h)}" fill="url(#{major})"/></g>')
    cv.add(f'<rect x="{f1(border + .8)}" y="{f1(top + border + .8)}" width="{f1(W - 2 * border - 1.6)}" '
           f'height="{f1(h - 2 * border - 1.6)}" fill="none" {hair(col, .9)} stroke-width="1.6"/>')
    # Zone marks, as a drawing has: numbers along the top and foot, letters down the sides.
    step = (W - 2 * border) / zones
    ticks, marks = [], []
    for i in range(zones):
        x = border + step * i
        if i:
            ticks.append(f"M{f1(x)} {f1(top)}V{f1(top + border)}M{f1(x)} {f1(H - border)}V{f1(H)}")
        marks += [(x + step / 2, top + border - 3.2, str(zones - i)), (x + step / 2, H - 3.4, str(zones - i))]
    rows = 3 if h > 150 else 2
    seg = (h - 2 * border) / rows
    for i, letter in enumerate("ABC"[:rows]):
        y = top + border + seg * i + seg / 2 + 2.5
        marks += [(border / 2, y, letter), (W - border / 2, y, letter)]
    cv.add(f'<path d="{"".join(ticks)}" {hair(col, .6)}/>',
           cv.L.scatter(marks, face="meta", size=7, fill=c(col["ink"]), opacity=.6))


def centre_line(cv: Canvas, col: dict, *, x0: float, x1: float, y: float) -> None:
    """A long-dash, short-dash line: the divider above a footer, where a drawing marks an axis."""
    cv.add(f'<path d="M{f1(x0)} {f1(y)}H{f1(x1)}" stroke="{c(col["edge"] if not col["dark"] else "gray")}" '
           f'stroke-opacity=".6" stroke-dasharray="8 4 2 4"/>')


# --- linework ------------------------------------------------------------------------------

def arrowhead(x: float, y: float, sgn: int, col: dict, vertical: bool = False) -> str:
    """A filled arrowhead with its tip at (x, y), pointing along the axis toward `sgn`."""
    if vertical:
        return f'<path d="M{f1(x)} {f1(y)}l-2.6 {f1(-sgn * 7)}h5.2z" fill="{c(col["line"])}"/>'
    return f'<path d="M{f1(x)} {f1(y)}l{f1(-sgn * 7)} -2.6v5.2z" fill="{c(col["line"])}"/>'


def dimension(cv: Canvas, col: dict, *, left: float, right: float, y: float, near: float,
              label: str | None = None) -> list:
    """A horizontal dimension over a span: extension lines up from `near`, arrows, the measured width between them."""
    draws = [(10, f'<path d="M{f1(x)} {f1(near)}V{f1(y - 5)}" {hair(col)}/>') for x in (left, right)]
    text = f"{round(right - left)}" if label is None else label
    lw = width(text, "meta", 10.5, .6) + 10
    mid = (left + right) / 2
    draws.append(((right - left) / 2, f'<path d="M{f1(left)} {f1(y)}H{f1(mid - lw / 2)}M{f1(mid + lw / 2)} {f1(y)}'
                                      f'H{f1(right)}" {hair(col)}/>'))
    cv.add(arrowhead(left, y, -1, col), arrowhead(right, y, 1, col))
    cv.add(cv.L.text(text, face="meta", size=10.5, x=mid, y=y + cap_height("meta", 10.5) / 2, anchor="middle", ls=.6,
                     fill=c(col["ink"]), opacity=.85))
    return draws


def vdimension(cv: Canvas, col: dict, *, top: float, bottom: float, x: float, near: float,
               label: str | None = None) -> list:
    """A vertical dimension over a height: extension lines out from `near`, the measure set along the line."""
    draws = [(10, f'<path d="M{f1(near)} {f1(y)}H{f1(x - 5)}" {hair(col)}/>') for y in (top, bottom)]
    text = f"{round(bottom - top)}" if label is None else label
    lh = width(text, "meta", 10.5, .6) + 10
    mid = (top + bottom) / 2
    draws.append(((bottom - top) / 2, f'<path d="M{f1(x)} {f1(top)}V{f1(mid - lh / 2)}M{f1(x)} {f1(mid + lh / 2)}'
                                      f'V{f1(bottom)}" {hair(col)}/>'))
    cv.add(arrowhead(x, top, -1, col, vertical=True), arrowhead(x, bottom, 1, col, vertical=True))
    cv.add(f'<g transform="rotate(-90 {f1(x)} {f1(mid)})">'
           + cv.L.text(text, face="meta", size=10.5, x=x, y=mid + cap_height("meta", 10.5) / 2, anchor="middle",
                       ls=.6, fill=c(col["ink"]), opacity=.85) + "</g>")
    return draws


def note(cv: Canvas, col: dict, flow_, *, x: float, text: str, size: float, room: float, number: str = "1",
         centre: float | None = None) -> list:
    """A numbered general note: the number in a bubble, the note in capitals beside it. Returns the bubble to draw in.

    With `centre`, the bubble and the note's widest line are centred on it
    as one, and any further line hangs under the first.
    """
    r = size * .82
    _, lines = flow(text.upper(), "meta", size, size, room - 2 * r - 10, size * .14, rows=3)
    if centre is not None:
        x = centre - (2 * r + 9 + max(width(line, "meta", size, size * .14) for line in lines)) / 2
    base = flow_.line(size, caps=True)
    cx = x + r
    cy = base - cap_height("meta", size) / 2
    cv.add(cv.L.text(number, face="meta", size=size * .85, x=cx, y=base - .6, anchor="middle", fill=c(col["ink"])))
    for i, line in enumerate(lines):
        if i:
            flow_.gap(size * .55)
        y = base if i == 0 else flow_.line(size, caps=True)
        cv.add(cv.L.text(line, face="meta", size=size, x=x + 2 * r + 9, y=y, ls=size * .14, fill=c(col["ink"]),
                         opacity=.82))
    return [(2 * math.pi * r, f'<circle cx="{f1(cx)}" cy="{f1(cy)}" r="{f1(r)}" fill="none" {hair(col)}/>')]


def frame(col: dict, *, x: float, y: float, w: float, h: float) -> tuple:
    """A title block's outer frame, heavier than the rules inside it: (length, markup) for the plotter."""
    return (2 * (w + h), f'<rect x="{f1(x)}" y="{f1(y)}" width="{f1(w)}" height="{f1(h)}" fill="none" '
                         f'{hair(col, .85)} stroke-width="1.2"/>')


def cell(cv: Canvas, col: dict, *, x: float, y: float, w: float, h: float, label: str, value: str = "",
         size: float = 12.5, align: str = "start", label_size: float = 7) -> None:
    """One cell of a title block: its label small in the top corner, its value set on the cell's foot."""
    ink = c(col["ink"])
    cv.add(cv.L.text(label, face="meta", size=label_size, x=x + 7, y=y + 11, ls=1.1, fill=ink, opacity=.6))
    if value:
        vs = fit(value, "meta", w - 14, size, 8.5)
        vx, anchor = (x + w - 7, "end") if align == "end" else (x + 7, "start")
        cv.add(cv.L.text(value, face="meta", size=vs, x=vx, y=y + h - 8, anchor=anchor, fill=ink))


def rule(col: dict, d: str) -> str:
    """A title block's inner rules: finer than its frame."""
    return f'<path d="{d}" {hair(col, .55)} stroke-width=".8"/>'


# --- the schedule --------------------------------------------------------------------------

LABEL = 7  # the size a cell's label is lettered at
PAD = 7  # a cell's inner margin, each side


def _natural(label: str, value: str, size: float) -> float:
    return max(width(label, "meta", LABEL, 1.1), width(value, "meta", size)) + 2 * PAD + 4


def schedule_rows(cells: list, size: float, w: float, most: int) -> list[list[int]]:
    """Which cells share a row: the fewest rows, of as even a count as can be, in which every cell fits.

    A drawing's schedule reads left to right and top to bottom, so the order
    is kept; only where a row ends is chosen. A cell too wide for any row
    takes one of its own, and its value is set smaller to fit.
    """
    nat = [_natural(label, value, size) for label, value in cells]
    n = len(nat)
    for r in range(max(1, -(-n // most)), n + 1):
        base, extra = divmod(n, r)
        groups, i = [], 0
        for k in range(r):
            step = base + (1 if k < extra else 0)
            groups.append(list(range(i, i + step)))
            i += step
        if all(sum(nat[j] for j in g) <= w for g in groups):
            return groups
    return [[j] for j in range(n)]


def schedule_height(cells: list, size: float, w: float, most: int, row: float) -> float:
    return len(schedule_rows(cells, size, w, most)) * row if cells else 0.0


def schedule(cv: Canvas, col: dict, cells: list, *, x: float, y: float, w: float, size: float, row: float,
             most: int, draws: list) -> float:
    """The figures, ruled as a drawing's schedule along the foot of the sheet: each a small label over its value.

    It runs the width it is given, from border to border, so the sheet's own
    border closes it at the sides and the foot; only its top edge and the
    rules between cells are drawn here. A row's spare width is shared out
    evenly, so a long value keeps the room it needs and short ones space out.
    Returns the height it took.
    """
    if not cells:
        return 0.0
    rows = schedule_rows(cells, size, w, most)
    nat = [_natural(label, value, size) for label, value in cells]
    draws.append((w, f'<path d="M{f1(x)} {f1(y)}H{f1(x + w)}" {hair(col, .85)} stroke-width="1.2"/>'))
    rules = []
    for r, group in enumerate(rows):
        top = y + r * row
        if r:
            rules.append(f"M{f1(x)} {f1(top)}H{f1(x + w)}")
        spare = (w - sum(nat[j] for j in group)) / len(group)
        xx = x
        for k, j in enumerate(group):
            cw = nat[j] + spare if k < len(group) - 1 else x + w - xx
            if k:
                rules.append(f"M{f1(xx)} {f1(top)}V{f1(top + row)}")
            label, value = cells[j]
            cell(cv, col, x=xx, y=top, w=cw, h=row, label=label, value=value, size=size)
            xx += cw
    if rules:
        cv.add(rule(col, "".join(rules)))
    return len(rows) * row


def plot(cv: Canvas, draws: list, *, animate: bool, dur: float = 1.4) -> None:
    """Draw the linework in, the way a plotter would, as the page opens. Complete without SMIL."""
    for length, markup in draws:
        if animate:
            n = f1(length + 2)
            tag = markup[1:markup.index(" ")]
            markup = markup.replace("/>", f' stroke-dasharray="{n} {n}" stroke-dashoffset="0">'
                                    f'<animate attributeName="stroke-dashoffset" values="{n};{n};0" keyTimes="0;.25;1" '
                                    f'dur="{fx(dur, 2)}s" calcMode="spline" keySplines="0 0 1 1;.3 0 .2 1" '
                                    f'fill="freeze"/></{tag}>', 1)
        cv.add(markup)
