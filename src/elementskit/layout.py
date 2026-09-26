# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Layout the kit computes, so a data file never carries a coordinate.

shared wall. A schematic layers its boxes along the wires and snakes the
layers across the sheet, routing every wire orthogonally. A time line cuts
the quiet stretches out of the calendar so the busy ones have room.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


# --- a schematic's boxes and wires ------------------------------------------------------------

@dataclass
class Box:
    key: str
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0
    layer: int = 0

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


def layers(keys: list[str], edges: list[tuple[str, str]]) -> dict[str, int]:
    """Each box's layer: the longest path from a source to it, with any cycle broken where it closes."""
    out = {k: 0 for k in keys}
    succ = {k: [] for k in keys}
    for a, b in edges:
        if a in succ and b in out:
            succ[a].append(b)
    state: dict[str, int] = {}

    def visit(k: str, depth: int) -> None:
        if state.get(k) == 1:
            return   # a cycle: the edge that closes it is left where the layers already put it
        out[k] = max(out[k], depth)
        state[k] = 1
        for n in succ[k]:
            visit(n, depth + 1)
        state[k] = 2

    for k in keys:
        if not any(k == b for _, b in edges):
            visit(k, 0)
    for k in keys:
        if k not in state:
            visit(k, 0)
    return out


def snake(boxes: list[Box], edges: list[tuple[str, str]], *, left: float, top: float, width: float,
          per_row: int, box_w: float, box_h: float, gap_x: float, gap_y: float, stack_gap: float = 22) -> float:
    """Place layers along a boustrophedon: left to right, then back, each layer one cell, stacked when shared.

    With `per_row` of 1 it is a column, which is what a phone gets. Returns
    the height the placement took.
    """
    lay = layers([b.key for b in boxes], edges)
    for b in boxes:
        b.layer = lay[b.key]
    by_layer: dict[int, list[Box]] = {}
    for b in boxes:
        by_layer.setdefault(b.layer, []).append(b)
    cols = min(per_row, len(by_layer)) or 1
    cell_w = (width - (cols - 1) * gap_x) / cols
    bw = min(box_w, cell_w)
    y = top
    row_h = 0.0
    for i, layer in enumerate(sorted(by_layer)):
        row, col = divmod(i, cols)
        if row % 2:
            col = cols - 1 - col
        if col == (0 if row % 2 == 0 else cols - 1) and i:
            y += row_h + gap_y
            row_h = 0.0
        x = left + col * (cell_w + gap_x) + (cell_w - bw) / 2
        yy = y
        for b in by_layer[layer]:
            b.x, b.y, b.w, b.h = x, yy, bw, box_h
            yy += box_h + stack_gap
        row_h = max(row_h, yy - stack_gap - y)
    return y + row_h - top


def _crosses(x0, y0, x1, y1, boxes: list, skip: tuple) -> bool:
    """Whether the straight run from (x0, y0) to (x1, y1) passes through a box it does not start or end in."""
    for b in boxes:
        if b.key in skip:
            continue
        if x0 == x1 and b.x < x0 < b.x + b.w and max(y0, y1) > b.y and min(y0, y1) < b.y + b.h:
            return True
        if y0 == y1 and b.y < y0 < b.y + b.h and max(x0, x1) > b.x and min(x0, x1) < b.x + b.w:
            return True
    return False


def route(a: Box, b: Box, gap_x: float, boxes: list | None = None, lane: float = 0) -> list[tuple[float, float]]:
    """An orthogonal wire from a to b: straight when the two line up and nothing is in the way, else an L or a Z.

    `lane` shifts the wire's channel run, so wires sharing a channel run
    side by side; `boxes` are what a run must not pass through.
    """
    boxes = boxes or []
    skip = (a.key, b.key)
    if abs(a.cy - b.cy) < 1 and (b.x >= a.x + a.w or a.x >= b.x + b.w):
        pts = [(a.x + a.w, a.cy), (b.x, b.cy)] if b.x > a.x else [(a.x, a.cy), (b.x + b.w, b.cy)]
        if not _crosses(*pts[0], *pts[1], boxes, skip):
            return pts
    if abs(a.cx - b.cx) < 1:
        pts = [(a.cx, a.y + a.h), (b.cx, b.y)] if b.y > a.y else [(a.cx, a.y), (b.cx, b.y + b.h)]
        if not _crosses(*pts[0], *pts[1], boxes, skip):
            return pts
        # Down the channel beside the column, past whatever sits between.
        ch = a.x + a.w + gap_x / 2 + lane
        return [(a.x + a.w, a.cy), (ch, a.cy), (ch, b.cy), (b.x + b.w, b.cy)]
    if b.x >= a.x + a.w or a.x >= b.x + b.w:
        if b.x > a.x:
            ch = a.x + a.w + gap_x / 2 + lane
            return [(a.x + a.w, a.cy), (ch, a.cy), (ch, b.cy), (b.x, b.cy)]
        ch = a.x - gap_x / 2 + lane
        return [(a.x, a.cy), (ch, a.cy), (ch, b.cy), (b.x + b.w, b.cy)]
    if b.y > a.y:
        mid = a.y + a.h + (b.y - a.y - a.h) / 2 + lane
        return [(a.cx, a.y + a.h), (a.cx, mid), (b.cx, mid), (b.cx, b.y)]
    mid = b.y + b.h + (a.y - b.y - b.h) / 2 + lane
    return [(a.cx, a.y), (a.cx, mid), (b.cx, mid), (b.cx, b.y + b.h)]


# --- a time line's breaks ----------------------------------------------------------------------

@dataclass
class Scale:
    """Dates to x, with the quiet stretches cut out."""
    segments: list[tuple[dt.date, dt.date, float, float]] = field(default_factory=list)
    breaks: list[tuple[float, float, int]] = field(default_factory=list)

    def x(self, d: dt.date) -> float:
        """The x of a date: along its stretch, or across the break a cut stretch became."""
        for i, (d0, d1, x0, x1) in enumerate(self.segments):
            if d0 <= d <= d1:
                span = (d1 - d0).days or 1
                return x0 + (x1 - x0) * (d - d0).days / span
            if d < d0:
                if i == 0:
                    return x0
                p0, p1 = self.segments[i - 1][1], d0
                bx0, bx1 = self.segments[i - 1][3], x0
                return bx0 + (bx1 - bx0) * (d - p0).days / max((p1 - p0).days, 1)
        return self.segments[-1][3]


def timeline(start: dt.date, end: dt.date, anchors: list[dt.date], x0: float, x1: float, *,
             quiet: int | None = None, cut: float = 44, margin: int | None = None) -> Scale:
    """Lay the calendar from x0 to x1, cutting every stretch longer than `quiet` days that holds no anchor.

    Quiet means nothing happened for three tenths of the whole span, and
    at least a month, unless the caller says otherwise. A cut stretch
    keeps `margin` days on each side, so a mark never sits right at a
    break, and is drawn `cut` pixels wide, room for the break symbol and
    the length it stands for.
    """
    total = (end - start).days
    if quiet is None:
        quiet = max(30, round(total * .3))
    if margin is None:
        margin = max(2, round(total * .02))
    marks = sorted({start, end, *anchors})
    kept: list[tuple[dt.date, dt.date]] = []
    gaps: list[tuple[dt.date, dt.date]] = []
    cur = start
    for a, b in zip(marks, marks[1:]):
        if (b - a).days > quiet + 2 * margin:
            kept.append((cur, a + dt.timedelta(days=margin)))
            gaps.append((a + dt.timedelta(days=margin), b - dt.timedelta(days=margin)))
            cur = b - dt.timedelta(days=margin)
    kept.append((cur, end))
    days = sum((b - a).days for a, b in kept)
    room = (x1 - x0) - cut * len(gaps)
    scale = Scale()
    x = x0
    for i, (a, b) in enumerate(kept):
        w = room * (b - a).days / days
        scale.segments.append((a, b, x, x + w))
        x += w
        if i < len(gaps):
            scale.breaks.append((x, x + cut, (gaps[i][1] - gaps[i][0]).days))
            x += cut
    return scale
