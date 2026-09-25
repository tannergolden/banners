# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The headers: the first sheet of a set of drawings.

Each is a pure function of the header's content, a theme, a width and
whether it may move: the same input gives byte-identical output, which is
what lets a committed file be checked against a fresh render.

  H1 Sheet     a cover sheet: the title centred and dimensioned, the figures ruled along its foot
  H2 Section   the title drawn as a cut solid, outlined and hatched, dimensioned both ways; the default
  H3 Strip     the sheet at a smaller scale, for a short header

Across the foot of every sheet runs its schedule: the repository or the
account, then the figures GitHub gives for it, each a small label over its
value, redrawn whenever the measurement moves. The title stands alone on
its line: a header draws no emoji.

Motion follows the masthead's rules. A file that moves is still complete
without SMIL: every animated attribute carries its resting value, and the
animation overrides it. Nothing inside a file asks for reduced motion,
because that query never matches inside an `<img>`; the still file is a
separate file, chosen by the `<picture>`.
"""
from __future__ import annotations

from .canvas import Canvas, c
from .content import Header
from .drafting import colours, dimension, hair, note, plot, schedule, sheet, vdimension
from .layout import NARROW, WIDE, Flow, title_block, title_lines
from .text import f1, flow, fonts, fx, width


def _canvas(h: Header, code: str, th: dict, wide: bool, motion: bool) -> Canvas:
    stamp = f"{code} {th['name']}" + ("" if wide else " narrow") + ("" if motion else " still")
    return Canvas(WIDE if wide else NARROW, 0, title=h.spoken_title(), desc=h.spoken(), stamp=stamp)


def _lines(cv: Canvas, h: Header, col: dict, f: Flow, *, x0: float, room: float, wide: bool, draws: list,
           small: bool = False, centre: float | None = None) -> None:
    """What a sheet says under its title: the tagline, the motto as its one general note, the description.

    Set from `x0`, or centred on `centre` for a cover sheet.
    """
    x, anchor = (centre, "middle") if centre is not None else (x0, "start")
    if h.on("tagline"):
        top, floor = (16, 13) if small else (21, 15) if wide else (17, 15)
        size, lines = flow(h.get("tagline"), "meta", top, floor, room, rows=2 if wide else 3)
        for line in lines:
            cv.add(cv.L.text(line, face="meta", size=size, x=x, y=f.line(size, lead=1.08), anchor=anchor,
                             fill=c(col["ink"]), opacity=.94))
        f.gap(8 if small else 10)
    if h.on("motto"):
        draws += note(cv, col, f, x=x0, text=h.get("motto"), size=10.5 if (small or not wide) else 11.5, room=room,
                      centre=centre)
        f.gap(10 if small else 12)
    if h.on("description"):
        top = 12.5 if small else 14 if wide else 13
        size, lines = flow(h.get("description"), "meta", top, 12, room, rows=(1 if small else 2) if wide else 4)
        for line in lines:
            cv.add(cv.L.text(line, face="meta", size=size, x=x, y=f.line(size, lead=1.1), anchor=anchor,
                             fill=c(col["ink"]), opacity=.72))


def _foot(cv: Canvas, h: Header, col: dict, *, border: float, y: float, wide: bool, draws: list,
          small: bool = False) -> tuple[float, tuple]:
    """The schedule along the sheet's foot, from border to border, below `y`.

    Returns the sheet's height and the region the grid leaves out. Without
    figures the sheet simply ends a margin below its last line.
    """
    cells = list(h.shown_figures)
    if not cells:
        return y + ((20 if small else 30) if wide else 22) + border, ()
    top = y + ((14 if small else 22) if wide else 18)
    size = (12 if small else 14) if wide else 12.5
    row = (32 if small else 36) if wide else 34
    w = cv.w - 2 * border
    height = schedule(cv, col, cells, x=border, y=top, w=w, size=size, row=row, most=8 if wide else 3, draws=draws)
    return top + height + border, ((border, top, w, height),)


# --- H1 Sheet ------------------------------------------------------------------------------

def sheet_design(h: Header, th: dict, wide: bool = True, motion: bool = True) -> str:
    """A cover sheet. The title is centred and dimensioned with its own measured width, in pixels.

    Its colours are a print's: blue lines on white by day and a blueprint by
    night, or the sepia, black-line and coloured prints of the same trade.
    The motto is the sheet's one general note, and the figures are ruled
    along its foot. When the page opens, the dimensions and the rules are
    drawn in, the way a plotter would.
    """
    cv = _canvas(h, "H1", th, wide, motion)
    W = cv.w
    col = colours(h.tone, th)
    border = 12 if wide else 10
    x0 = 50 if wide else 26
    room = W - 2 * x0
    draws: list = []
    keep, cv.body = cv.body, []
    f = Flow(border + (40 if wide else 34))

    if h.caps:
        size, lines = title_lines(h, "num", 58 if wide else 36, 22 if wide else 18, room, .07)
        f.gap(22)
        left, right, top = title_block(cv, h, lines, face="num", size=size, ls_em=.07, flow=f, fill=col["ink"],
                                       cx=W / 2)
        draws += dimension(cv, col, left=left, right=right, y=top - 16, near=top - 5)
        f.gap(18 if wide else 14)
    _lines(cv, h, col, f, x0=x0, room=room, wide=wide, draws=draws, centre=W / 2)
    H, plain = _foot(cv, h, col, border=border, y=f.y, wide=wide, draws=draws)
    body, cv.body = cv.body, keep

    sheet(cv, col, W=W, H=H, border=border, zones=8 if wide else 4, plain=plain)
    plot(cv, draws, animate=motion and wide)
    cv.add(*body)
    cv.h = H
    return cv.svg()


# --- H2 Section ----------------------------------------------------------------------------

# Longer than any outline in the title face, in its own units (the @ runs to
# 5,432), so one dash draws any glyph whole.
DASH = 5500


def section(h: Header, th: dict, wide: bool = True, motion: bool = True) -> str:
    """The title drawn as a cut solid: outlined, hatched at 45 degrees the way a section is, dimensioned both ways.

    When the page opens a plotter draws every letter's outline at once, at
    one pen speed, so the narrow letters close first; the hatching follows.
    """
    cv = _canvas(h, "H2", th, wide, motion)
    W = cv.w
    col = colours(h.tone, th)
    animate = motion and wide
    border = 12 if wide else 10
    x0 = 74 if wide else 46
    room = W - x0 - (50 if wide else 26)
    draws: list = []
    keep, cv.body = cv.body, []
    f = Flow(border + (40 if wide else 34))

    if h.caps:
        size, lines = title_lines(h, "num", 64 if wide else 40, 24 if wide else 18, room, .06)
        sc = size / fonts()["num"]["upem"]
        ls = size * .06
        f.gap(24)
        runs = []
        for i, line in enumerate(lines):
            base = f.line(size, caps=True)
            runs.append((x0, base, line))
            if i < len(lines) - 1:
                f.gap(size * .22)
        # Each line is drawn once, then used twice: as the mask its hatching
        # shows through, and as the outline the plotter draws.
        ids = []
        for x, base, line in runs:
            rid = cv.uid("t")
            cv.defs.append(cv.L.text(line, face="num", size=size, x=x, y=base, ls=ls, fill=None)
                           .replace("<g ", f'<g id="{rid}" ', 1))
            ids.append(rid)
        cut_left = min(x for x, _, _ in runs)
        cut_right = max(x + width(line, "num", size, ls) for x, _, line in runs)
        bx, bxr = cut_left - 4, cut_right + 4
        by, byb = runs[0][1] - size * .78, runs[-1][1] + size * .25
        solid = cv.uid("m")
        cv.defs.append(f'<mask id="{solid}" maskUnits="userSpaceOnUse" x="{f1(bx)}" y="{f1(by)}" '
                       f'width="{f1(bxr - bx)}" height="{f1(byb - by)}">'
                       + "".join(f'<use href="#{rid}" fill="{c("white")}"/>' for rid in ids) + "</mask>")
        hatch = cv.uid("p")
        cv.defs.append(f'<pattern id="{hatch}" width="6" height="6" patternUnits="userSpaceOnUse" '
                       f'patternTransform="rotate(45)"><path d="M3 0V6" {hair(col, .7)} stroke-width="1.1"/></pattern>')
        rect = (f'<rect x="{f1(bx)}" y="{f1(by)}" width="{f1(bxr - bx)}" height="{f1(byb - by)}" '
                f'fill="url(#{hatch})" mask="url(#{solid})"')
        cv.add(rect + ('><animate attributeName="opacity" values="0;0;1" keyTimes="0;.72;1" dur="2.8s" '
                       'fill="freeze"/></rect>' if animate else "/>"))
        pen = f'stroke="{c(col["line"])}" stroke-width="{fx(1.5 / sc, 1)}" stroke-linejoin="round"'
        for rid in ids:
            if animate:
                cv.add(f'<use href="#{rid}" fill="none" {pen} stroke-dasharray="{DASH} {DASH}" stroke-dashoffset="0">'
                       f'<animate attributeName="stroke-dashoffset" values="{DASH};{DASH};0" keyTimes="0;.1;1" '
                       f'dur="2.4s" calcMode="spline" keySplines="0 0 1 1;.4 .1 .3 1" fill="freeze"/></use>')
            else:
                cv.add(f'<use href="#{rid}" fill="none" {pen}/>')
        draws += dimension(cv, col, left=cut_left, right=cut_right, y=by - 12, near=by - 1)
        first_top, first_base = runs[0][1] - size * .70, runs[0][1]
        if first_base - first_top >= 24:
            # Too short a height leaves no room for its own figure; a drafter would leave it off.
            draws += vdimension(cv, col, top=first_top, bottom=first_base, x=x0 - 22, near=x0 - 6)
        f.gap(12)
        cv.add(cv.L.text("SECTION A-A", face="meta", size=9, x=cut_left, y=f.line(9, caps=True), ls=1.8,
                         fill=c(col["ink"]), opacity=.7))
        f.gap(16 if wide else 12)
    _lines(cv, h, col, f, x0=x0, room=room, wide=wide, draws=draws)
    H, plain = _foot(cv, h, col, border=border, y=f.y, wide=wide, draws=draws)
    body, cv.body = cv.body, keep

    sheet(cv, col, W=W, H=H, border=border, zones=8 if wide else 4, plain=plain)
    plot(cv, draws, animate=animate)
    cv.add(*body)
    cv.h = H
    return cv.svg()


# --- H3 Strip ------------------------------------------------------------------------------

def strip(h: Header, th: dict, wide: bool = True, motion: bool = True) -> str:
    """The sheet at a smaller scale: the title dimensioned, a line or two under it, and a slimmer schedule."""
    cv = _canvas(h, "H3", th, wide, motion)
    W = cv.w
    col = colours(h.tone, th)
    border = 10 if wide else 9
    x0 = 40 if wide else 26
    room = W - 2 * x0
    draws: list = []
    keep, cv.body = cv.body, []
    f = Flow(border + 16)

    if h.caps:
        size, lines = title_lines(h, "num", 36 if wide else 30, 18 if wide else 16, room, .07)
        f.gap(20)
        left, right, top = title_block(cv, h, lines, face="num", size=size, ls_em=.07, flow=f, fill=col["ink"], x=x0)
        draws += dimension(cv, col, left=left, right=right, y=top - 13, near=top - 4)
        f.gap(12)
    _lines(cv, h, col, f, x0=x0, room=room, wide=wide, draws=draws, small=True)
    H, plain = _foot(cv, h, col, border=border, y=f.y, wide=wide, draws=draws, small=True)
    body, cv.body = cv.body, keep

    sheet(cv, col, W=W, H=H, border=border, zones=8 if wide else 4, plain=plain)
    plot(cv, draws, animate=motion and wide, dur=1.2)
    cv.add(*body)
    cv.h = H
    return cv.svg()
