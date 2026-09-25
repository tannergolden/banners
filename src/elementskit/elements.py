# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The blueprint elements: eight drawings a README makes from its own repository.

Every element is drawn on the banners' paper, in one of its prints, lettered
in the same outlines, and comes in the variants a README needs: a wide file
for the page and a narrow one for a phone. A data file names what to draw; the
layout module places it; nothing here takes a coordinate from a consumer.

What every sheet shares, so the set reads as one drawing set:
  - a tag plate at the head, the element's name lettered on a solid block of
    the print, the way an emblems plate carries its value, then the subject
  - one caption style, small capitals letter-spaced, for every label
  - poché (section lining) wherever a drawing shows solid material
  - wire and dimension text set in a gap in the line, never floating
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

from bannerkit import text as T
from bannerkit.canvas import DARK, DAY, Canvas, c, lint
from bannerkit.drafting import PRINTS, arrowhead, cell, colours, dimension, hair, rule, sheet
from bannerkit.draw import icon
from bannerkit.palette import ICONS
from bannerkit.text import cap_height, f1, fit, flow, fx, width

from .layout import Box, Room, doors, route, snake, snap, squarify, timeline

KIT_VERSION = "1"
THEMES = {"day": DAY, "dark": DARK}
WIDE, NARROW, HALF, SEAL = 830, 360, 404, 180
# Bytes a file may weigh. A sheet carries a repository's own content, so it
# is allowed more than a banner; a card is a banner's link chip grown up.
BUDGET = {"sheet": 72_000, "card": 32_000}

# --- the mono face, registered beside banners' two ---------------------------------------------

_MONO = Path(__file__).resolve().parents[1] / "fonts" / "jetbrains-mono.json"


def _register_mono() -> None:
    if "mono" in T.fonts():
        return
    T.fonts()["mono"] = json.loads(_MONO.read_text(encoding="utf-8"))["mono"]
    T.PREFIX["mono"] = "j"


_register_mono()


def mono_advance(size: float) -> float:
    font = T.fonts()["mono"]
    return font["g"]["M"][1] * size / font["upem"]


# --- shared pieces ------------------------------------------------------------------------------

def geometry(variant: str) -> dict:
    narrow = variant == "narrow"
    return dict(W=NARROW if narrow else WIDE, B=10 if narrow else 12, zones=4 if narrow else 8, narrow=narrow)


def new(kind: str, variant: str, th: dict, tone: str, W: float, h: float, title: str, desc: str):
    cv = Canvas(W, h, title=title, desc=desc, stamp=f"elements v{KIT_VERSION} {kind} {variant} {th['name']}")
    return cv, colours(tone, th)


WARNINGS: list[str] = []
_PLAIN = {"\u2026": "...", "\u2192": "->", "\u2190": "<-", "\u2713": "v", "\u2714": "v", "\u2717": "x", "\u2718": "x",
          "\u2022": "*", "\u00d7": "x", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " ",
          "\u2013": "-", "\u2014": "-", "\u2015": "-", "\u2212": "-", "\u00b7": "\u00b7"}


def plain(s: str, face: str) -> str:
    """`s` as the face can letter it: known characters as they are, the rest as their nearest plain spelling."""
    import unicodedata
    out = []
    for ch in str(s):
        if ch in _PLAIN and T.missing(ch, face):
            ch = _PLAIN[ch]
        if ch and T.missing(ch, face):
            base = "".join(c_ for c_ in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c_))
            if base and not T.missing(base, face):
                ch = base
            else:
                WARNINGS.append(f"{face} cannot letter {ch!r}")
                ch = "?"
        out.append(ch)
    return "".join(out)


def say(cv, s, *, x, y, col, size=10, face="meta", anchor="start", ls=0.0, op=None, role="ink"):
    s = plain(s, face)
    cv.add(cv.L.text(s, face=face, size=size, x=x, y=y, anchor=anchor, ls=ls, fill=c(col[role]), opacity=op))


def caption(cv, col, s, *, x, y, anchor="start"):
    say(cv, s, x=x, y=y, col=col, size=8, anchor=anchor, ls=1.2, op=.66)


def bubble(cv, col, n, x: float, y: float, r: float = 6.5):
    n = str(n)
    cv.add(f'<circle cx="{f1(x)}" cy="{f1(y)}" r="{f1(r)}" fill="none" {hair(col, .85)}/>')
    say(cv, n, x=x, y=y + cap_height("meta", 8) / 2, col=col, size=8, anchor="middle")


def hatch(cv, col, angle: float, gap: float, sw: float = 1.0, op: float = .8) -> str:
    """Section lining: parallel lines at an angle, the draughtsman's way to show solid material."""
    pid = cv.uid("h")
    cv.defs.append(f'<pattern id="{pid}" width="{fx(gap)}" height="{fx(gap)}" patternUnits="userSpaceOnUse" '
                   f'patternTransform="rotate({fx(angle)})"><path d="M0 0V{fx(gap)}" '
                   f'stroke="{c(col["line"])}" stroke-width="{fx(sw)}" stroke-opacity="{fx(op)}"/></pattern>')
    return pid


def paper(col) -> str:
    return c(col["paper"])


def _open(col, d: str, op: float = .9, extra: str = "") -> str:
    return f'<path d="{d}" fill="none" {hair(col, op)}{extra}/>'


def plate(cv, col, text: str, x: float, y: float, *, h: float = 17, size: float = 9, pad: float = 7) -> float:
    """A tag: capitals on a solid block of the print, the emblems plate's value block. Returns its right edge."""
    w = width(text, "num", size, 1.3) + 2 * pad
    cv.add(f'<rect x="{f1(x)}" y="{f1(y)}" width="{f1(w)}" height="{f1(h)}" fill="{c(col["line"])}"/>')
    say(cv, text, x=x + pad, y=y + h / 2 + cap_height("num", size) / 2, col=col, size=size, face="num", ls=1.3,
        role="paper")
    return x + w


def title(cv, col, g: dict, tag: str, subject: str, right: str = "", *, x0: float | None = None,
          y: float = 26) -> float:
    """The head of a sheet: the tag plate, the subject after it, a note on the right, a rule under all three."""
    W, B = g["W"], g["B"]
    x = (B + 20 if not g["narrow"] else B + 14) if x0 is None else x0
    edge = plate(cv, col, tag, x, y)
    base = y + 17 / 2 + cap_height("num", 14) / 2
    room = W - B - 20 - (edge + 12) - (width(right, "meta", 8, 1.2) + 16 if right and not g["narrow"] else 0)
    size = fit(subject, "num", room, 14, 9, 1.2)
    say(cv, subject, x=edge + 12, y=base, col=col, size=size, face="num", ls=1.2)
    if right and not g["narrow"]:
        say(cv, right, x=W - B - 20, y=base - 1, col=col, size=8, anchor="end", ls=1.2, op=.72)
    cv.add(_open(col, f"M{B} {f1(y + 26)}H{W - B}", .55, ' stroke-width=".8"'))
    return y + 26


def notes(cv, col, items, *, x: float, y: float, right: float, size: float = 8) -> float:
    """Numbered notes in a row, wrapping to a new row when the sheet runs out. Returns the last baseline."""
    xx = x
    for num, text in items:
        num, text = str(num), str(text)
        w = 17 + width(text, "meta", size, 1)
        if xx + w > right and xx > x:
            xx, y = x, y + 14
        bubble(cv, col, num, xx + 6, y - 3.5)
        say(cv, text, x=xx + 17, y=y, col=col, size=size, ls=1, op=.82)
        xx += w + 22
    return y


def ring(cv, col, s: str, *, cx, cy, r, size, top: bool, ls=1.2):
    """Lettering set on a circle: along the top reading outward, along the foot reading inward."""
    font = T.fonts()["meta"]
    sc = size / font["upem"]
    total = width(s, "meta", size, ls)
    pos = -total / 2
    out = []
    for ch in s:
        key = T._key(font, ch)
        adv = font["g"][key][1] * sc if key else 0
        mid = pos + adv / 2
        pos += adv + ls
        if not key or key == " ":
            continue
        cv.L.used.add(("meta", key))
        deg = math.degrees(mid / r) if top else -math.degrees(mid / r)
        base = -r if top else r + cap_height("meta", size)
        out.append(f'<use href="#m{ord(key)}" transform="translate({f1(cx)} {f1(cy)}) rotate({fx(deg, 2)}) '
                   f'translate({fx(-adv / 2, 2)} {fx(base, 2)}) scale({fx(sc, 5)} {fx(-sc, 5)})"/>')
    cv.add(f'<g fill="{c(col["ink"])}">' + "".join(out) + "</g>")


# --- schematic ----------------------------------------------------------------------------------

def _wire(cv, col, pts: list, label: str | None, W: float, *, along: bool = False, placed: list | None = None,
          avoid: list | None = None) -> None:
    """A polyline with an arrowhead at its end, its label set in a gap in its longest run, as a dimension's is.

    On a vertical run the label is set across the wire in a gap; with `along`
    it is turned to run with it, for a wire in a channel with no room beside.
    `placed` collects the labels' boxes, and a label slides along its run
    until it is clear of every one before it and of every run in `avoid`,
    the other wires' segments, so no wire crosses through a word.
    """
    placed = placed if placed is not None else []
    avoid = avoid or []
    segs = list(zip(pts, pts[1:]))
    gap_seg = None
    if label:
        gap_seg = max(range(len(segs)), key=lambda i: abs(segs[i][1][0] - segs[i][0][0])
                      + abs(segs[i][1][1] - segs[i][0][1]))
    parts, line = [], c(col["line"])

    def clear(box):
        return all(box[2] < a - 4 or box[0] > b + 4 or box[3] < c_ - 4 or box[1] > d + 4
                   for a, c_, b, d in placed + avoid)

    def spot(x0, y0, x1, y1, tw, th):
        """Where along the run the label sits: the middle, else stepped toward either end until clear."""
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        run = max(abs(x1 - x0), abs(y1 - y0))
        for k in (0, 1, -1, 2, -2, 3, -3):
            t = .5 + k * .14
            if not 0.2 <= t <= 0.8 and k:
                continue
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            box = (px - tw / 2, py - th / 2, px + tw / 2, py + th / 2)
            inside = (min(x0, x1) - 1 <= box[0] and box[2] <= max(x0, x1) + 1) if y0 == y1 else \
                     (min(y0, y1) - 1 <= box[1] and box[3] <= max(y0, y1) + 1)
            if (clear(box) and (inside or k == 0)) or run < 30:
                placed.append(box)
                return px, py
        placed.append((mx - tw / 2, my - th / 2, mx + tw / 2, my + th / 2))
        return mx, my

    for i, ((x0, y0), (x1, y1)) in enumerate(segs):
        if i == gap_seg and y0 == y1:
            tw = width(label, "meta", 8, 1.1)
            px, _ = spot(x0, y0, x1, y1, tw + 12, 10)
            half = tw / 2 + 6
            sgn = 1 if x1 > x0 else -1
            parts.append(f"M{f1(x0)} {f1(y0)}H{f1(px - sgn * half)}M{f1(px + sgn * half)} {f1(y0)}H{f1(x1)}")
            say(cv, label, x=px, y=y0 + 3, col=col, size=8, anchor="middle", ls=1.1, op=.85)
        elif i == gap_seg and abs(y1 - y0) >= 36:
            sgn = 1 if y1 > y0 else -1
            tw = width(label, "meta", 8, 1.1)
            if x0 + tw / 2 > W - 16 or x0 - tw / 2 < 16:
                along = True   # no room across the wire this close to the edge: run with it
            if along:
                _, py = spot(x0, y0, x1, y1, 10, tw + 12)
                half = tw / 2 + 6
                parts.append(f"M{f1(x0)} {f1(y0)}V{f1(py - sgn * half)}M{f1(x0)} {f1(py + sgn * half)}V{f1(y1)}")
                cv.add(f'<g transform="rotate(-90 {f1(x0)} {f1(py)})">'
                       + cv.L.text(label, face="meta", size=8, x=x0, y=py + 3, anchor="middle", ls=1.1,
                                   fill=c(col["ink"]), opacity=.85) + "</g>")
            else:
                _, py = spot(x0, y0, x1, y1, tw, 12)
                parts.append(f"M{f1(x0)} {f1(y0)}V{f1(py - sgn * 7)}M{f1(x0)} {f1(py + sgn * 7)}V{f1(y1)}")
                say(cv, label, x=x0, y=py + 3, col=col, size=8, anchor="middle", ls=1.1, op=.85)
        else:
            parts.append(f"M{f1(x0)} {f1(y0)}L{f1(x1)} {f1(y1)}")
            if i == gap_seg:
                right = x0 < W * .68
                say(cv, label, x=x0 + (9 if right else -9), y=(y0 + y1) / 2 + 3, col=col, size=8,
                    anchor="start" if right else "end", ls=1.1, op=.85)
    cv.add(f'<path d="{"".join(parts)}" fill="none" stroke="{line}" stroke-width="1.2"/>')
    (x0, y0), (x1, y1) = segs[-1]
    vertical = x0 == x1
    cv.add(arrowhead(x1, y1, 1 if (y1 > y0 if vertical else x1 > x0) else -1, col, vertical=vertical))


def schematic(d: dict, tone: str, th: dict, variant: str = "wide") -> str:
    """Boxes and the wires between them, layered along the wires and snaked across the sheet.

    A phone gets one box to a row in wire order, with any wire that skips a
    row carried down a channel at the right.
    """
    g = geometry(variant)
    W, B, narrow = g["W"], g["B"], g["narrow"]
    keys = list(d["boxes"])
    edges = [(a, b) for a, b, *_ in d["wires"]]
    boxes = [Box(k) for k in keys]
    by = {b.key: b for b in boxes}
    bh = 52
    groups = d.get("groups", {})
    grouped = any(d["boxes"][k].get("in") for k in keys)
    wires: list[tuple] = []
    if narrow:
        left, top, bw, gap_y = B + 14, 78, 276, 44
        from .layout import layers as _layers
        lay = _layers(keys, edges)
        order = sorted(keys, key=lambda k: (lay[k], keys.index(k)))
        y = top
        prev_group = None
        for k in order:
            grp = d["boxes"][k].get("in")
            if grp and grp != prev_group:
                y += 26
            b = by[k]
            b.x, b.y, b.w, b.h = left, y, bw, bh
            y += bh + gap_y
            prev_group = grp
        placed = y - gap_y - top
        row = {k: i for i, k in enumerate(order)}
        channel = 0
        for a, b, *rest in d["wires"]:
            A, Bx = by[a], by[b]
            label = str(rest[0]) if rest else None
            if row[b] == row[a] + 1:
                wires.append(([(A.cx, A.y + A.h), (Bx.cx, Bx.y)], label, False))
            else:
                chx = left + bw + 10 + 8 * channel
                channel += 1
                wires.append(([(A.x + A.w, A.cy), (chx, A.cy), (chx, Bx.cy), (Bx.x + Bx.w, Bx.cy)], label, True))
    else:
        left, top = 46, 100
        gap_x, gap_y = 72, 64
        placed = snake(boxes, edges, left=left, top=top + (18 if grouped else 0), width=W - 2 * left,
                       per_row=3, box_w=224, box_h=bh, gap_x=gap_x, gap_y=gap_y)
        # Wires that would share a channel take lanes in it, 8 px apart, centred on the channel.
        first = {}
        for a, b, *rest in d["wires"]:
            pts = route(by[a], by[b], gap_x, boxes)
            key = None if len(pts) < 4 else (round(pts[1][0]) if pts[1][0] == pts[2][0] else ("y", round(pts[1][1])))
            first.setdefault(key, []).append((a, b, str(rest[0]) if rest else None))
        for key, group in first.items():
            n = len(group) if key is not None else 1
            for i, (a, b, label) in enumerate(group):
                lane = (i - (n - 1) / 2) * 8 if key is not None else 0
                wires.append((route(by[a], by[b], gap_x, boxes, lane), label, False))
    ns = d.get("notes", ())
    rows = 0
    if ns:
        rows = 1
        xx, right = left, W - B - 20
        for _, text in ns:
            w = 17 + width(str(text), "meta", 8, 1)
            if xx + w > right and xx > left:
                xx, rows = left, rows + 1
            xx += w + 22
    H = top + (0 if narrow else (18 if grouped else 0)) + placed + 34 + (rows * 14 if rows else 0) + B
    cv, col = new("schematic", variant, th, tone, W, H, d.get("title", "Schematic"), d.get("desc", ""))
    sheet(cv, col, W=W, H=H, border=B, zones=g["zones"])
    title(cv, col, g, "SCHEMATIC", d.get("subject", ""), d.get("caption", ""))
    line = c(col["line"])
    for gk, label in groups.items():
        members = [by[k] for k in keys if d["boxes"][k].get("in") == gk]
        if not members:
            continue
        x0, y0 = min(b.x for b in members) - 14, min(b.y for b in members) - 30
        x1, y1 = max(b.x + b.w for b in members) + 14, max(b.y + b.h for b in members) + 14
        if narrow:
            x0, x1 = max(x0, B + 4), min(x1, left + 276 + 6)
        cv.add(f'<rect x="{f1(x0)}" y="{f1(y0)}" width="{f1(x1 - x0)}" height="{f1(y1 - y0)}" rx="4" fill="none" '
               f'{hair(col, .8)} stroke-dasharray="7 4"/>')
        say(cv, label, x=(x0 + x1) / 2, y=y0 + 16, col=col, size=8, anchor="middle", ls=1.2, op=.75)
    for k in keys:
        b, spec = by[k], d["boxes"][k]
        cv.add(f'<rect x="{f1(b.x)}" y="{f1(b.y)}" width="{f1(b.w)}" height="{f1(b.h)}" rx="3" fill="{paper(col)}" '
               f'stroke="{line}" stroke-width="1.3"/>')
        cv.add(f'<rect x="{f1(b.x)}" y="{f1(b.y)}" width="34" height="{f1(b.h)}" fill="{line}" fill-opacity=".06"/>'
               + _open(col, f"M{f1(b.x + 34)} {f1(b.y)}V{f1(b.y + b.h)}", .45))
        cv.add(icon(spec.get("icon", "grid"), b.x + 8, b.y + (b.h - 18) / 2, 18, col["ink"], 1.8))
        say(cv, str(spec["title"]).upper(), x=b.x + 46, y=b.y + b.h / 2 - 3, col=col, size=11.5, face="num", ls=1)
        say(cv, spec.get("path", ""), x=b.x + 46, y=b.y + b.h / 2 + 12, col=col, size=9, face="mono", op=.75)
        if spec.get("note"):
            bubble(cv, col, spec["note"], b.x + b.w - 12, b.y + 12)
    taken = [(b.x, b.y, b.x + b.w, b.y + b.h) for b in boxes]
    runs = [[(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])) for a, b in zip(pts, pts[1:])]
            for pts, _, _ in wires]
    for i, (pts, label, along) in enumerate(wires):
        others = [seg for j, segs in enumerate(runs) if j != i for seg in segs]
        _wire(cv, col, pts, label, W, along=along, placed=taken, avoid=others)
    if ns:
        notes(cv, col, ns, x=left, y=H - B - 17 - (rows - 1) * 14, right=W - B - 20)
    return cv.svg()


# --- instruments --------------------------------------------------------------------------------

def _histogram(cv, col, hist, *, x0, x1, top, base, size_n=8.5):
    line = c(col["line"])
    peak = hist.get("peak") or max(10, math.ceil(max(v for _, v in hist["bars"]) / 10) * 10 + 5)
    ticks = hist.get("ticks") or [round(peak * k / 3) for k in range(4)]
    tk = []
    for v in ticks:
        yy = base - (base - top) * v / peak
        tk.append(f"M{x0 - 4} {f1(yy)}H{x1}")
        say(cv, str(v), x=x0 - 8, y=yy + 3, col=col, size=8, face="mono", anchor="end", op=.6)
    cv.add(_open(col, "".join(tk), .25), _open(col, f"M{x0} {top - 4}V{base}H{x1}"))
    hid = hatch(cv, col, 45, 4.5, 1.1)
    step = (x1 - x0) / len(hist["bars"])
    bw = step * .62
    for i, (label, v) in enumerate(hist["bars"]):
        label, v = str(label), int(v)
        cx = x0 + step * i + step / 2
        hh = (base - top) * v / peak
        if v:
            cv.add(f'<rect x="{f1(cx - bw / 2)}" y="{f1(base - hh)}" width="{f1(bw)}" height="{f1(hh)}" '
                   f'fill="url(#{hid})" stroke="{line}" stroke-width="1.1"/>')
        say(cv, str(v), x=cx, y=base - hh - 5, col=col, size=size_n, face="mono", anchor="middle",
            op=.9 if v else .45)
        say(cv, label, x=cx, y=base + 13, col=col, size=7 if step < 40 else 7.5, anchor="middle", ls=.5, op=.66)


def _dial(cv, col, dial, *, cx, cy, r):
    line = c(col["line"])
    span, tk = dial["span"], []
    for v in range(0, span + 1):
        a = math.pi * (1 - v / span)
        major = v % dial.get("major", 10) == 0
        inner = r - (11 if major else 7 if v % dial.get("minor", 5) == 0 else 4)
        tk.append(f"M{f1(cx + inner * math.cos(a))} {f1(cy - inner * math.sin(a))}"
                  f"L{f1(cx + r * math.cos(a))} {f1(cy - r * math.sin(a))}")
        if major:
            lr = r - 21
            say(cv, str(v), x=cx + lr * math.cos(a), y=cy - lr * math.sin(a) + 3, col=col, size=8.5, face="mono",
                anchor="middle", op=.7)
    cv.add(f'<path d="M{cx - r} {cy}A{r} {r} 0 0 1 {cx + r} {cy}" fill="none" stroke="{line}" '
           f'stroke-width="1.4"/>' + _open(col, "".join(tk)) + _open(col, f"M{cx - r - 6} {cy}H{cx + r + 6}", .5))
    value = min(dial["value"], span)
    a = math.pi * (1 - value / span)
    cv.add(f'<path d="M{cx} {cy}L{f1(cx + (r - 8) * math.cos(a))} {f1(cy - (r - 8) * math.sin(a))}" '
           f'stroke="{line}" stroke-width="2" stroke-linecap="round"/><circle cx="{cx}" cy="{cy}" r="4.5" '
           f'fill="{line}"/>')
    say(cv, str(dial["value"]), x=cx, y=cy - 22, col=col, size=26 if r > 70 else 22, face="num", anchor="middle")
    caption(cv, col, dial.get("sub", ""), x=cx, y=cy + 18, anchor="middle")


def _materials(cv, col, mat, *, x0, x1, y, h, label_size=8):
    line = c(col["line"])
    fills = [hatch(cv, col, 45, 4, 1), hatch(cv, col, -45, 4, 1), hatch(cv, col, 0, 3.2, 1.1),
             hatch(cv, col, 90, 5, .8), None]
    parts = mat["parts"][:5]
    total = sum(float(b) for _, b in parts) or 1
    xx = x0
    taken = {True: [], False: []}   # label spans placed above and below, so none lands on another
    for i, ((kind, size_b), fid) in enumerate(zip(parts, fills)):
        share = float(size_b) / total
        w = (x1 - x0) * share
        fill, op = (f"url(#{fid})", "") if fid else (line, ' fill-opacity=".12"')
        cv.add(f'<rect x="{f1(xx)}" y="{y}" width="{f1(w)}" height="{h}" fill="{fill}"{op} stroke="{line}" '
               f'stroke-width="1.1"/>')
        text = f"{kind} {round(share * 100)}%"
        tw = width(text, "meta", label_size, .8)
        lo, hi = xx + w / 2 - tw / 2, xx + w / 2 + tw / 2
        if lo < x0:
            lo, hi = x0, x0 + tw
        if hi > x1:
            lo, hi = x1 - tw, x1
        for up in (i % 2 == 0, i % 2 != 0):
            if all(hi < a - 6 or lo > b + 6 for a, b in taken[up]):
                taken[up].append((lo, hi))
                say(cv, text, x=lo, y=y - 7 if up else y + h + 13, col=col, size=label_size, ls=.8, op=.85)
                break
        xx += w
    dimension(cv, col, left=x0, right=x1, y=y + h + 30, near=y + h + 16, label=mat["total"])


def _counters(cv, col, counters, *, x, y, step=88, cell=18):
    line = c(col["line"])
    shown = []
    for label, value in counters[:3]:
        value = int(value)
        digits = f"{value:03d}" if value < 10000 else f"{round(value / 1000)}K"
        shown.append((label, value, digits))
    step = max(step, max(len(dg) for _, _, dg in shown) * (cell + 2) + 10)
    for i, (label, value, digits) in enumerate(shown):
        ox = x + i * step
        for k, ch in enumerate(digits):
            dx = ox + k * (cell + 2)
            cv.add(f'<rect x="{dx}" y="{y}" width="{cell}" height="28" rx="2" fill="none" stroke="{line}" '
                   f'stroke-width="1.1"/>' + _open(col, f"M{dx} {y + 6}H{dx + cell}M{dx} {y + 22}H{dx + cell}", .35))
            say(cv, ch, x=dx + cell / 2, y=y + 19, col=col, size=14, face="mono", anchor="middle",
                op=1 if value >= 10 ** (len(digits) - 1 - k) or k == len(digits) - 1 else .35)
        caption(cv, col, label, x=ox + (len(digits) * (cell + 2) - 2) / 2, y=y + 46, anchor="middle")


def instruments(d: dict, tone: str, th: dict, variant: str = "wide") -> str:
    """A histogram, a dial, a bar of materials and a row of counters: a project's vitals."""
    g = geometry(variant)
    W, B, narrow = g["W"], g["B"], g["narrow"]
    hist, dial, mat = d["histogram"], d["dial"], d["materials"]
    total = sum(v for _, v in hist["bars"])
    if narrow:
        H = 520
        cv, col = new("instruments", variant, th, tone, W, H, d.get("title", "Instruments"), d.get("desc", ""))
        sheet(cv, col, W=W, H=H, border=B, zones=4)
        title(cv, col, g, "INSTRUMENTS", d.get("subject", ""))
        x0, x1 = B + 14, W - B - 14
        caption(cv, col, hist["label"], x=x0, y=74)
        say(cv, f"{total:,}", x=x1, y=78, col=col, size=18, face="num", anchor="end")
        caption(cv, col, hist.get("sum", ""), x=x1, y=90, anchor="end")
        _histogram(cv, col, hist, x0=x0 + 22, x1=x1, top=100, base=160, size_n=7.5)
        cv.add(_open(col, f"M{B} 188H{W - B}", .55, ' stroke-width=".8"'))
        caption(cv, col, dial["label"], x=x0, y=210)
        _dial(cv, col, dial, cx=W / 2, cy=286, r=64)
        cv.add(_open(col, f"M{B} 312H{W - B}", .55, ' stroke-width=".8"'))
        caption(cv, col, mat["label"], x=x0, y=334)
        _materials(cv, col, mat, x0=x0, x1=x1, y=352, h=20, label_size=7.5)
        cv.add(_open(col, f"M{B} 418H{W - B}", .55, ' stroke-width=".8"'))
        caption(cv, col, "COUNTED", x=x0, y=440)
        _counters(cv, col, d["counters"], x=x0 + 4, y=452, step=104, cell=18)
        return cv.svg()
    H = 346
    cv, col = new("instruments", variant, th, tone, W, H, d.get("title", "Instruments"), d.get("desc", ""))
    sheet(cv, col, W=W, H=H, border=B, zones=8)
    title(cv, col, g, "INSTRUMENTS", d.get("subject", ""), d.get("caption", ""))
    cv.add(_open(col, f"M520 61V{H - B}M{B} 206H{W - B}", .55, ' stroke-width=".8"'))
    caption(cv, col, hist["label"], x=34, y=80)
    say(cv, f"{total:,}", x=500, y=84, col=col, size=20, face="num", anchor="end")
    caption(cv, col, hist.get("sum", ""), x=500, y=96, anchor="end")
    _histogram(cv, col, hist, x0=62, x1=500, top=104, base=178)
    caption(cv, col, dial["label"], x=546, y=80)
    _dial(cv, col, dial, cx=662, cy=176, r=82)
    caption(cv, col, mat["label"], x=34, y=230)
    _materials(cv, col, mat, x0=34, x1=500, y=262, h=24)
    caption(cv, col, "COUNTED", x=546, y=230)
    _counters(cv, col, d["counters"], x=546, y=252)
    return cv.svg()


# --- plan ---------------------------------------------------------------------------------------

WALL, OUTER = 6, 8   # wall thickness, in px: the poché is drawn this wide


def _plan_rooms(d: dict, narrow: bool, x0: float, y0: float, x1: float) -> tuple[list[Room], dict, float]:
    """Rooms weighted by the area their listing needs, packed as square as a few tries can make them.

    The rooms come biggest first and the lobby last, which puts the lobby on
    the plan's bottom wall, where its entrance goes. The lobby's weight and
    the closets' place are tried a few ways and the packing with the least
    stretched room is kept: a treemap's last item is otherwise a strip.
    """
    col_w = 150 if narrow else 170

    def need(lines: int, far: int = 0) -> float:
        return (44 + 14 * max(min(lines, 6), 1, far) + 10) * col_w

    ordered = sorted(d.get("rooms", ()), key=lambda r: -r["count"])
    lobby = d.get("lobby") or {"count": 0, "lines": []}
    spec = {r["key"]: r for r in ordered}
    spec["lobby"] = dict(lobby, key="lobby", label=lobby.get("label", "LOBBY"))
    closets = d.get("closets") or ()
    closet_w = (38 * math.ceil(len(closets) / 2) + 6) * 130 if closets else 0
    best = None
    for lobby_w in (need(len(lobby.get("lines", ())), len(lobby.get("far", ()))), need(4), need(3), need(6)):
        for closet_at in ((len(ordered), len(ordered) - 1, max(len(ordered) - 2, 0)) if closets else (None,)):
            rooms = [Room(r["key"], need(len(r.get("lines", ())))) for r in ordered]
            if closets:
                rooms.insert(closet_at, Room("closets", closet_w))
            rooms.append(Room("lobby", lobby_w))
            ph = max(248, round(sum(r.weight for r in rooms) * 1.08 / (x1 - x0) / 2) * 2)
            squarify(rooms, x0, y0, x1 - x0, ph)
            snap(rooms)
            worst = max(max(r.w / r.h, r.h / r.w) for r in rooms)
            lob = next(r for r in rooms if r.key == "lobby")
            if abs(lob.y + lob.h - (y0 + ph)) > 1:
                worst += 10   # the entrance wants the lobby on the bottom wall
            if best is None or worst < best[0]:
                best = (worst, rooms, ph)
    _, rooms, ph = best
    return rooms, spec, ph


def _room(cv, col, room: Room, spec: dict, narrow: bool) -> None:
    x, y, w, h = room.rect
    inset = 13
    label = str(spec["label"])
    ls_ = fit(label, "num", w - 2 * inset - 4, 11 if narrow else 12.5, 8, 1)
    say(cv, label, x=x + inset, y=y + 21, col=col, size=ls_, face="num", ls=1)
    n = spec["count"]
    count = f"{n} FILE{'S' if n != 1 else ''}"
    far = [str(f) for f in spec.get("far", ())]
    if width(label, "num", ls_, 1) + width(count, "meta", 7.5, 1.1) + 2 * inset + 12 <= w:
        say(cv, count, x=x + w - 12, y=y + 21, col=col, size=7.5, anchor="end", ls=1.1, op=.66)
    else:
        far = [count] + far
    cv.add(_open(col, f"M{f1(x + inset)} {f1(y + 27)}H{f1(x + w - 12)}", .3))
    lines = [(str(a), str(b)) for a, b in spec.get("lines", ())]
    fits = min(max(0, int((h - 41 - 6) // 14)), int(spec.get("most", 6)))
    if len(lines) > fits:
        lines = lines[:max(fits - 1, 0)] + ([("", f"+{len(spec['lines']) - max(fits - 1, 0)} MORE")] if fits else [])
    wide_enough = w >= 190
    if far and far[0] == count and not wide_enough and len(lines) < fits:
        lines.append(("", count))   # the header had no room for it, and there is no far column to take it
    yy = y + 41
    for i, (name, extra) in enumerate(lines):
        room = w - inset - 2 - 12 - (width(extra, "mono", 8) + 8 if extra else 0)
        chars = max(4, int(room / mono_advance(9)))
        if name:
            shown = name if len(name) <= chars else name[:chars - 1] + "~"
            say(cv, shown, x=x + inset + 2, y=yy, col=col, size=9, face="mono", op=.9)
        if extra and (name or not wide_enough or not far):
            say(cv, extra, x=x + w - 12, y=yy, col=col, size=8 if name else 7.5, face="mono" if name else "meta",
                anchor="end", op=.6, ls=0 if name else 1)
        for num, at in spec.get("notes", ()):
            if name and (at == i or (isinstance(at, str) and at in (name, extra))):
                bx = x + inset + 2 + width(shown, "mono", 9) + 10
                if bx + 8 < x + w - 12 - (width(extra, "mono", 8) + 6 if extra else 0):
                    bubble(cv, col, num, bx, yy - 3.2)
        yy += 14
    if wide_enough:
        for i, name in enumerate(far[:fits]):
            if i < len(lines) and lines[i][1] and lines[i][0]:
                continue   # the near column's own extra sits there
            say(cv, name, x=x + w - 12, y=y + 41 + 14 * i, col=col, size=9 if not name.endswith("FILES") else 7.5,
                face="mono" if not name.endswith("FILES") else "meta", anchor="end", op=.6,
                ls=1 if name.endswith("FILES") else 0)


def _closets(cv, col, room: Room, closets: list) -> None:
    x, y, w, h = room.rect
    cols = 2 if w >= 100 else 1
    cw, ch = w / cols, 38
    rows = max(1, int(h // ch))
    shown = closets[:cols * rows]
    for i, cl in enumerate(shown):
        r, cc = divmod(i, cols)
        cx, cy = x + cc * cw + cw / 2, y + r * ch
        if i:
            cv.add(_open(col, f"M{f1(x + cc * cw)} {f1(cy)}h{f1(cw)}" if cc == 0 else
                         f"M{f1(x + cc * cw)} {f1(cy)}v{f1(ch)}", .4))
        label = cl["label"]
        s = fit(label, "meta", cw - 8, 6.8, 5.5, .5)
        say(cv, label, x=cx, y=cy + 16, col=col, size=s, anchor="middle", ls=.5, op=.8)
        say(cv, str(cl["count"]), x=cx, y=cy + 29, col=col, size=8.5, face="mono", anchor="middle", op=.6)
    if len(closets) > len(shown):
        say(cv, f"+{len(closets) - len(shown)}", x=x + w - 6, y=y + h - 6, col=col, size=7, anchor="end", op=.6)


def plan(d: dict, tone: str, th: dict, variant: str = "wide") -> str:
    """The repository as a floor plan: rooms behind poché walls, doors, the lobby and its entrance."""
    g = geometry(variant)
    W, B, narrow = g["W"], g["B"], g["narrow"]
    if narrow:
        x0, y0, x1 = B + 14, 84, W - B - 14
    else:
        x0, y0, x1 = 48, 86, W - 48
    rooms, spec, ph = _plan_rooms(d, narrow, x0, y0, x1)
    y1 = y0 + ph
    ns = list(d.get("notes", ()))
    note_rows, xx = (1 if ns else 0), x0 + 48
    for _, text in ns:
        w = 17 + width(str(text), "meta", 8 if narrow else 8.5, 1)
        if xx + w > W - B - 12 and xx > x0 + 48:
            xx, note_rows = x0 + 48, note_rows + 1
        xx += w + 22
    H = y1 + 48 + 14 * max(note_rows, 1)
    cv, col = new("plan", variant, th, tone, W, H, d.get("title", "Plan"), d.get("desc", ""))
    sheet(cv, col, W=W, H=H, border=B, zones=g["zones"])
    title(cv, col, g, "PLAN", d.get("subject", ""), d.get("caption", ""))
    dimension(cv, col, left=x0, right=x1, y=y0 - 18, near=y0 - 5, label=f"{d['total']} TRACKED FILES")
    line = c(col["line"])
    poche = hatch(cv, col, 45, 3.4, 1.0, 1.0)

    def rect_path(x, y, w, h, o=0.0):
        return f"M{f1(x - o)} {f1(y - o)}h{f1(w + 2 * o)}v{f1(h + 2 * o)}h{f1(-w - 2 * o)}z"

    inner = "".join(rect_path(*r.rect) for r in rooms)
    cv.add(f'<path d="{inner}" fill="none" stroke="url(#{poche})" stroke-width="{WALL}"/>'
           + _open(col, "".join(rect_path(*r.rect, o) for r in rooms for o in (-WALL / 2, WALL / 2)), .95))
    cv.add(f'<path d="{rect_path(x0, y0, x1 - x0, ph)}" fill="none" stroke="url(#{poche})" stroke-width="{OUTER}"/>'
           + _open(col, "".join(rect_path(x0, y0, x1 - x0, ph, o) for o in (-OUTER / 2, OUTER / 2)), .95,
                   ' stroke-width="1.1"'))
    pc = paper(col)
    lobby = next(r for r in rooms if r.key == "lobby")
    ex_w = 24
    if abs(lobby.y + lobby.h - y1) < 1:
        entrance = (lobby.x + lobby.w / 2 - ex_w / 2, y1, True, ex_w, -1)
        arrow = ("bottom", lobby.x + lobby.w / 2)
    elif abs(lobby.x + lobby.w - x1) < 1:
        entrance = (x1, lobby.y + lobby.h / 2 - ex_w / 2, False, ex_w, -1)
        arrow = ("right", lobby.y + lobby.h / 2)
    elif abs(lobby.y - y0) < 1:
        entrance = (lobby.x + lobby.w / 2 - ex_w / 2, y0, True, ex_w, 1)
        arrow = ("top", lobby.x + lobby.w / 2)
    else:
        entrance = (x0, lobby.y + lobby.h / 2 - ex_w / 2, False, ex_w, 1)
        arrow = ("left", lobby.y + lobby.h / 2)
    for x, y, horizontal, w, swing in doors(rooms) + [entrance]:
        flag, t = (1 if swing > 0 else 0), OUTER + 2
        if horizontal:
            cv.add(f'<rect x="{f1(x)}" y="{f1(y - t / 2)}" width="{f1(w)}" height="{t}" fill="{pc}"/>',
                   _open(col, f"M{f1(x)} {f1(y)}v{f1(-w * swing)}M{f1(x)} {f1(y - w * swing)}"
                              f"a{f1(w)} {f1(w)} 0 0 {flag} {f1(w)} {f1(w * swing)}", .8))
        else:
            cv.add(f'<rect x="{f1(x - t / 2)}" y="{f1(y)}" width="{t}" height="{f1(w)}" fill="{pc}"/>',
                   _open(col, f"M{f1(x)} {f1(y)}h{f1(w * swing)}M{f1(x + w * swing)} {f1(y)}"
                              f"a{f1(w)} {f1(w)} 0 0 {flag} {f1(-w * swing)} {f1(w)}", .8))
    for r in rooms:
        if r.key == "closets":
            _closets(cv, col, r, d["closets"])
        else:
            _room(cv, col, r, spec[r.key], narrow)
    label = d.get("entrance", "ENTRANCE")
    side, at = arrow
    if side == "bottom":
        cv.add(_open(col, f"M{f1(at)} {y1 + 34}V{y1 + 13}"), arrowhead(at, y1 + 9, -1, col, vertical=True))
        say(cv, label, x=at + 10, y=y1 + 31, col=col, size=8.5, ls=1.2, op=.85,
            anchor="start" if at + 10 + width(label, "meta", 8.5, 1.2) < W - B - 10 else "end")
    elif side == "top":
        cv.add(_open(col, f"M{f1(at)} {y0 - 30}V{y0 - 13}"), arrowhead(at, y0 - 9, 1, col, vertical=True))
    else:
        xa = min(x1 + 12, W - B - 5) if side == "right" else max(x0 - 12, B + 5)
        cv.add(_open(col, f"M{f1(xa)} {f1(at - 20)}V{f1(at - 6)}"), arrowhead(xa, at - 3, 1, col, vertical=True))
    if side != "bottom":
        ns = [("", label)] + ns
    cv.add(icon("compass", x0 - 2, y1 + 14, 22, col["ink"], 1.6))
    say(cv, "N", x=x0 + 9, y=y1 + 46, col=col, size=8, anchor="middle", ls=1)
    items = [(n, t) for n, t in ns if n]
    plain = [t for n, t in ns if not n]
    yy = y1 + 39
    for t in plain:
        say(cv, t, x=x0 + 48, y=yy, col=col, size=8.5, ls=1.2, op=.85)
        yy += 14
    if items:
        notes(cv, col, items, x=x0 + 48, y=yy, right=W - B - 12, size=8.5 if not narrow else 8)
    return cv.svg()


# --- milestones ---------------------------------------------------------------------------------

def _date(s) -> dt.date:
    return s if isinstance(s, dt.date) else dt.date.fromisoformat(str(s))


def _when(d: dt.date, year: bool) -> str:
    return d.strftime("%d %b %Y" if year else "%d %b").lstrip("0").upper()


def milestones(d: dict, tone: str, th: dict, variant: str = "wide") -> str:
    """A project's history on a drafted time line: what shipped below, what it brought above."""
    g = geometry(variant)
    W, B, narrow = g["W"], g["B"], g["narrow"]
    events = sorted(d.get("events", ()), key=lambda e: _date(e["date"]))
    today = _date(d.get("today") or dt.date.today())
    if not events:
        events = [{"date": str(today), "tag": "NO RELEASE YET", "major": True}]
    start = _date(d["start"]) if d.get("start") else _date(events[0]["date"]) - dt.timedelta(days=14)
    end = _date(d["end"]) if d.get("end") else _date(max(str(events[-1]["date"]), str(today))) + dt.timedelta(days=21)
    line_hex = None
    if narrow:
        majors = [e for e in events if e.get("major", True) or e.get("made")]
        rows = [(e, 1 + len(e.get("above", ()))) for e in majors]
        H = 96 + sum(30 + 11 * (n - 1) for _, n in rows) + 20
        cv, col = new("milestones", variant, th, tone, W, H, d.get("title", "Milestones"), d.get("desc", ""))
        sheet(cv, col, W=W, H=H, border=B, zones=4)
        title(cv, col, g, "MILESTONES", d.get("subject", ""))
        line = c(col["line"])
        lx, y = B + 30, 82
        ty = y
        ys = []
        for e, n in rows:
            ys.append(y)
            y += 30 + 11 * (n - 1)
        cv.add(f'<path d="M{lx} {ty - 6}V{f1(ys[-1] + 6)}" stroke="{line}" stroke-width="2"/>')
        for (e, n), yy in zip(rows, ys):
            dashed = e.get("next")
            fill = paper(col) if dashed else line
            stroke = ' stroke-dasharray="2 2"' if dashed else ""
            if e.get("made"):
                cv.add(f'<circle cx="{lx}" cy="{f1(yy)}" r="5" fill="{paper(col)}" stroke="{line}" stroke-width="1.6"/>')
            else:
                cv.add(f'<path d="M{lx} {f1(yy - 6.5)}l6.5 6.5l-6.5 6.5l-6.5 -6.5z" fill="{fill}" stroke="{line}" '
                       f'stroke-width="1.2"{stroke}/>')
            say(cv, e["tag"], x=lx + 20, y=yy + 4, col=col, size=10.5, face="num", ls=.6)
            say(cv, e.get("when") or _when(_date(e["date"]), True), x=W - B - 14, y=yy + 4, col=col, size=7.5,
                anchor="end", ls=.8, op=.6)
            for i, text in enumerate(e.get("above", ())):
                say(cv, text, x=lx + 20, y=yy + 16 + 11 * i, col=col, size=8, ls=.9, op=.75)
        return cv.svg()

    H = d.get("H", 282)
    cv, col = new("milestones", variant, th, tone, W, H, d.get("title", "Milestones"), d.get("desc", ""))
    sheet(cv, col, W=W, H=H, border=B, zones=8)
    title(cv, col, g, "MILESTONES", d.get("subject", ""), d.get("caption", ""))
    line = c(col["line"])
    tx0, tx1, ty = 46, 784, 142
    anchors = [_date(e["date"]) for e in events] + [today]
    scale = timeline(start, end, anchors, tx0, tx1)
    X = scale.x
    tx = X(today)
    cv.add(f'<path d="M{tx0} {ty}H{f1(tx)}" stroke="{line}" stroke-width="2"/>'
           f'<path d="M{f1(tx)} {ty}H{tx1}" stroke="{line}" stroke-width="2" stroke-dasharray="6 5"/>')
    for bx0, bx1, days in scale.breaks:
        zx = (bx0 + bx1) / 2
        cv.add(f'<rect x="{f1(bx0 + 4)}" y="{ty - 12}" width="{f1(bx1 - bx0 - 8)}" height="24" fill="{paper(col)}"/>')
        cv.add(_open(col, f"M{f1(bx0 + 4)} {ty}H{f1(zx - 10)}l4 -9l6 18l6 -18l4 9H{f1(bx1 - 4)}", .9))
        say(cv, f"{days} DAYS", x=zx, y=ty + 22, col=col, size=7, anchor="middle", ls=1, op=.6)
    ticks = []
    for d0, d1, _, _ in scale.segments:
        m = dt.date(d0.year, d0.month, 1)
        while m <= d1:
            if m >= d0:
                x = X(m)
                big = m.month == 1
                ticks.append(f"M{f1(x)} {ty - (6 if big else 3)}V{ty + (6 if big else 3)}")
                if big or m.month in (4, 7, 10):
                    say(cv, m.strftime("%b %Y" if big else "%b").upper(), x=x, y=ty + 20, col=col, size=7.5,
                        anchor="middle", ls=.8, op=.85 if big else .6)
            m = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    cv.add(_open(col, "".join(ticks)))
    cv.add(_open(col, f"M{f1(tx)} {ty - 14}V{ty + 10}", .6, ' stroke-dasharray="2 2"'))
    # Marks within a few pixels of one another are spread apart, and a label that would land on the one
    # before it is lifted a level (above the line) or dropped one (below), so nothing prints on anything.
    xs = [X(_date(e["date"])) for e in events]
    clusters = []
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[j + 1] - xs[i] < 14 * (j + 1 - i):
            j += 1
        if j > i:
            mid = sum(xs[i:j + 1]) / (j + 1 - i)
            for k in range(i, j + 1):
                xs[k] = mid + (k - i - (j - i) / 2) * 24
            clusters.append((i, j))
        i = j + 1
    above_spans: list = []   # (x, w, lift, h) of every stack of notes placed above the line
    below_spans: list = []   # (x, w, drop, h) of every tag and date placed below it

    def level(spans, x, w, h, gap):
        """How far from the line a new span sits: clear of every span it overlaps sideways, by that span's height."""
        lift = 0
        for px, pw, plift, ph in spans:
            if abs(x - px) < (w + pw) / 2 + 6:
                lift = max(lift, plift + ph + gap)
        spans.append((x, w, lift, h))
        return lift

    # The notes of marks that were spread apart above sit side by side over the cluster rather than one
    # over another, each on a leader that bends from its own mark, the way a drafted callout does.
    at = {}   # event index -> (x of the stack, base lift)
    for i0, j0 in clusters:
        noted = [k for k in range(i0, j0 + 1) if events[k].get("above")]
        if len(noted) < 2:
            continue
        widths = [max(width(str(t), "meta", 8.5, .9) for t in events[k]["above"]) for k in noted]
        total = sum(widths) + 14 * (len(noted) - 1)
        left = min(max(sum(xs[i0:j0 + 1]) / (j0 + 1 - i0) - total / 2, tx0 + 4), tx1 - 4 - total)
        for k, w in zip(noted, widths):
            at[k] = (left + w / 2, 14)
            left += w + 14

    last_minor_x = -100
    for n, (e, x) in enumerate(zip(events, xs)):
        if e.get("made"):
            texts = [str(t) for t in e.get("above", [e["tag"]])]
            sx, base = at.get(n, (x, 0))
            lift = base + level(above_spans, sx, max(width(t, "meta", 10, .8) for t in texts), 13 * len(texts), 8)
            cv.add(f'<circle cx="{f1(x)}" cy="{ty}" r="5" fill="{paper(col)}" stroke="{line}" stroke-width="1.6"/>',
                   _open(col, f"M{f1(x)} {ty - 6}V{ty - 12 - lift}" if sx == x else
                         f"M{f1(x)} {ty - 6}V{ty - 11}L{f1(sx)} {f1(ty - 12 - lift)}", .8))
            for i, text in enumerate(reversed(texts)):
                say(cv, text, x=sx, y=ty - 16 - lift - 13 * i, col=col, size=10, anchor="middle", ls=.8)
            continue
        if not e.get("major", True):
            cv.add(f'<circle cx="{f1(x)}" cy="{ty}" r="3" fill="{line}"/>')
            if x - last_minor_x > 34:
                say(cv, e["tag"], x=x, y=ty + 31, col=col, size=7, anchor="middle", ls=.5, op=.5)
                last_minor_x = x
            continue
        dashed = e.get("next")
        stroke = ' stroke-dasharray="2 2"' if dashed else ""
        fill = paper(col) if dashed else line
        tag = str(e["tag"])
        drop = level(below_spans, x, width(tag, "num", 10.5 if e.get("big") else 9.5, .6), 22, 4)
        cv.add(_open(col, f"M{f1(x)} {ty + 7}V{ty + 28 + drop}", .5),
               f'<path d="M{f1(x)} {ty - 6.5}l6.5 6.5l-6.5 6.5l-6.5 -6.5z" fill="{fill}" stroke="{line}" '
               f'stroke-width="1.2"{stroke}/>')
        say(cv, tag, x=x, y=ty + 40 + drop, col=col, size=10.5 if e.get("big") else 9.5, face="num",
            anchor="middle", ls=.6)
        when = e.get("when") or _when(_date(e["date"]), _date(e["date"]).month == 1 or e is events[0])
        say(cv, when, x=x, y=ty + 52 + drop, col=col, size=7.5, anchor="middle", ls=.8, op=.6)
        if e.get("above"):
            texts = [str(t) for t in e["above"]]
            sx, base = at.get(n, (x, 0))
            lift = base + level(above_spans, sx, max(width(t, "meta", 8.5, .9) for t in texts), 12 * len(texts), 8)
            cv.add(_open(col, f"M{f1(x)} {ty - 9}V{ty - 18 - lift}" if sx == x else
                         f"M{f1(x)} {ty - 9}V{ty - 14}L{f1(sx)} {f1(ty - 18 - lift)}", .7))
            for i, text in enumerate(reversed(texts)):
                say(cv, text, x=sx, y=ty - 24 - lift - 12 * i, col=col, size=8.5, anchor="middle", ls=.9,
                    op=.9 if i == len(texts) - 1 else .75)
    ky = H - B - 16
    cv.add(f'<path d="M{B + 26} {ky - 8.5}l5.5 5.5l-5.5 5.5l-5.5 -5.5z" fill="{line}"/>')
    say(cv, "RELEASED", x=B + 36, y=ky, col=col, size=8, ls=1.2, op=.75)
    kx = B + 106
    if any(e.get("made") for e in events):
        cv.add(f'<circle cx="{kx - 3}" cy="{ky - 3}" r="4" fill="{paper(col)}" stroke="{line}" stroke-width="1.4"/>')
        say(cv, "CREATED", x=kx + 7, y=ky, col=col, size=8, ls=1.2, op=.75)
        kx += 70
    if any(not e.get("major", True) for e in events):
        cv.add(f'<circle cx="{kx - 3}" cy="{ky - 3}" r="3" fill="{line}"/>')
        say(cv, "PATCH", x=kx + 6, y=ky, col=col, size=8, ls=1.2, op=.75)
        kx += 64
    if any(e.get("next") for e in events):
        cv.add(f'<path d="M{kx} {ky - 8.5}l5.5 5.5l-5.5 5.5l-5.5 -5.5z" fill="{paper(col)}" stroke="{line}" '
               f'stroke-width="1.2" stroke-dasharray="2 2"/>')
        say(cv, "PLANNED", x=kx + 10, y=ky, col=col, size=8, ls=1.2, op=.75)
        kx += 74
    cv.add(_open(col, f"M{kx} {ky - 10}V{ky + 3}", .6, ' stroke-dasharray="2 2"'))
    say(cv, "TODAY", x=kx + 8, y=ky, col=col, size=8, ls=1.2, op=.75)
    return cv.svg()


# --- roster -------------------------------------------------------------------------------------

def _medallion(cv, col, p: dict, mx: float, my: float, r: float) -> None:
    line = c(col["line"])
    ticks = "".join(f"M{f1(mx + (r - 3.5) * math.cos(a))} {f1(my + (r - 3.5) * math.sin(a))}"
                    f"L{f1(mx + (r - 1.2) * math.cos(a))} {f1(my + (r - 1.2) * math.sin(a))}"
                    for a in (k * math.pi / 18 for k in range(36)))
    cv.add(f'<circle cx="{f1(mx)}" cy="{f1(my)}" r="{r}" fill="none" stroke="{line}" stroke-width="1.5"/>'
           f'<circle cx="{f1(mx)}" cy="{f1(my)}" r="{r - 6}" fill="none" {hair(col, .7)}/>' + _open(col, ticks, .6))
    if p.get("initials"):
        size = 15 * r / 26
        say(cv, p["initials"], x=mx, y=my + cap_height("num", size) / 2, col=col, size=size, face="num",
            anchor="middle", ls=.8)
    else:
        s = 18 * r / 26
        cv.add(icon(p.get("icon", "package"), mx - s / 2, my - s / 2, s, col["ink"], 1.8))


def roster(d: dict, tone: str, th: dict, variant: str = "wide") -> str:
    """The people who drew it, each in a medallion, with their count and their first and last."""
    people = d["people"]
    most = max(p["n"] for p in people)
    if variant != "wide":
        # Half a page: two to a row, the way the cards go, and what a phone gets.
        W, B = HALF, 10
        rows = math.ceil(len(people) / 2)
        H = 54 + rows * 74 + 6
        cv, col = new("roster", variant, th, tone, W, H, d.get("title", "Contributors"), d.get("desc", ""))
        sheet(cv, col, W=W, H=H, border=B, zones=4)
        title(cv, col, dict(W=W, B=B, narrow=True), "DRAWN BY", d.get("subject", ""))
        line = c(col["line"])
        fill = hatch(cv, col, 45, 3, 1, 1.0)
        colw = (W - 2 * B) / 2
        for i, p in enumerate(people):
            r, cc = divmod(i, 2)
            x, y = B + cc * colw, 62 + r * 74
            if cc:
                cv.add(_open(col, f"M{f1(x)} {y - 4}V{y + 66}", .4, ' stroke-width=".8"'))
            if r:
                cv.add(_open(col, f"M{f1(x + 8)} {y - 6}H{f1(x + colw - 8)}", .4, ' stroke-width=".8"'))
            _medallion(cv, col, p, x + 30, y + 30, 20)
            tx = x + 60
            say(cv, p["name"], x=tx, y=y + 20, col=col, size=fit(plain(p["name"], "num"), "num", colw - 68, 10.5, 7.5, .7),
                face="num", ls=.7)
            say(cv, p.get("handle", ""), x=tx, y=y + 31, col=col, size=7, ls=.9, op=.66)
            say(cv, f"{p['n']:,}", x=tx, y=y + 52, col=col, size=15, face="num")
            say(cv, "COMMITS", x=tx + width(f"{p['n']:,}", "num", 15) + 5, y=y + 51, col=col, size=6.5, ls=1, op=.7)
            room = colw - 74
            cv.add(f'<rect x="{f1(tx)}" y="{y + 57}" width="{f1(room)}" height="5" fill="none" {hair(col, .5)}/>'
                   f'<rect x="{f1(tx)}" y="{y + 57}" width="{f1(max(room * p["n"] / most, 2))}" height="5" '
                   f'fill="url(#{fill})" stroke="{line}" stroke-width="1"/>')
        return cv.svg()
    W, B = WIDE, 12
    H = 222
    cv, col = new("roster", variant, th, tone, W, H, d.get("title", "Contributors"), d.get("desc", ""))
    sheet(cv, col, W=W, H=H, border=B, zones=8)
    title(cv, col, geometry("wide"), "DRAWN BY", d.get("subject", ""), d.get("caption", ""))
    line = c(col["line"])
    colw = (W - 2 * B) / len(people)
    fill = hatch(cv, col, 45, 3, 1, 1.0)
    for i, p in enumerate(people):
        x = B + colw * i
        if i:
            cv.add(_open(col, f"M{f1(x)} 61V{H - B}", .55, ' stroke-width=".8"'))
        _medallion(cv, col, p, x + 42, 104, 26)
        tx = x + 80
        say(cv, p["name"], x=tx, y=91, col=col, size=fit(plain(p["name"], "num"), "num", colw - 86, 12, 8, .8),
            face="num", ls=.8)
        say(cv, p.get("handle", ""), x=tx, y=104, col=col, size=7.5, ls=1, op=.66)
        say(cv, f"{p['n']:,}", x=tx, y=132, col=col, size=20, face="num")
        say(cv, "COMMITS", x=tx + width(f"{p['n']:,}", "num", 20) + 6, y=131, col=col, size=7.5, ls=1, op=.7)
        room = colw - 94
        cv.add(f'<rect x="{f1(tx)}" y="139" width="{f1(room)}" height="7" fill="none" {hair(col, .5)}/>'
               f'<rect x="{f1(tx)}" y="139" width="{f1(max(room * p["n"] / most, 2))}" height="7" '
               f'fill="url(#{fill})" stroke="{line}" stroke-width="1"/>')
        top = H - B - 40
        cv.add(_open(col, f"M{f1(x)} {top}H{f1(x + colw)}", .55, ' stroke-width=".8"'))
        half = colw / 2
        cell(cv, col, x=x, y=top, w=half, h=40, label="FIRST", value=p["first"], size=11.5)
        cell(cv, col, x=x + half, y=top, w=half, h=40, label="LAST", value=p["last"], size=11.5)
        cv.add(rule(col, f"M{f1(x + half)} {top}V{H - B}"))
    return cv.svg()


# --- placard ------------------------------------------------------------------------------------

def placard(d: dict, tone: str, th: dict, variant: str = "wide") -> str:
    """A card that links to another repository: its name, its description, three facts."""
    PW, PH = HALF, 150
    cv, col = new("placard", variant, th, tone, PW, PH, f"{d['owner']}/{d['name']}", d["desc"])
    line, rx = c(col["line"]), 6
    cv.add(f'<rect width="{PW}" height="{PH}" rx="{rx}" fill="{paper(col)}"/>')
    if not col["dark"]:
        cv.add(f'<rect width="{PW}" height="{PH}" rx="{rx}" fill="{line}" fill-opacity=".03"/>')
    pid = cv.uid("p")
    cv.defs.append(f'<pattern id="{pid}" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M10 .5H.5V10" '
                   f'fill="none" {hair(col, .075 if col["dark"] else .07)}/></pattern>')
    cv.add(f'<rect width="{PW}" height="{PH}" rx="{rx}" fill="url(#{pid})"/>')
    cv.add(icon(d.get("icon", "book"), 16, 16, 16, col["ink"], 2))
    plate(cv, col, d["owner"].upper(), 40, 16, h=16, size=8.5, pad=6)
    say(cv, d["name"].upper(), x=16, y=58, col=col, size=fit(d["name"].upper(), "num", PW - 70, 22, 14, 1.4),
        face="num", ls=1.4)
    cv.add(f'<circle cx="{PW - 26}" cy="24" r="11" fill="{line}"/>'
           f'<g transform="rotate(-45 {PW - 26} 24)">' + icon("arrow", PW - 33, 17, 14, col["paper"], 2.2) + "</g>")
    s, lines = flow(d["desc"], "meta", 11.2, 10, PW - 32, rows=3)
    for i, ln in enumerate(lines):
        say(cv, ln, x=16, y=77 + i * 14, col=col, size=s, op=.88)
    top = PH - 32
    cv.add(f'<path d="M0 {top}H{PW}" {hair(col, .85)} stroke-width="1.2"/>')
    cells = list(d["cells"])[:3]
    cw = PW / len(cells)
    for i, (lab, val) in enumerate(cells):
        cell(cv, col, x=i * cw, y=top, w=cw, h=32, label=lab.upper(), value=str(val), size=11.5)
    cv.add(rule(col, "".join(f"M{f1(k * cw)} {top}V{PH}" for k in range(1, len(cells)))))
    cv.add(f'<rect x=".5" y=".5" width="{PW - 1}" height="{PH - 1}" rx="{rx - .5}" fill="none" stroke="{line}" '
           f'stroke-opacity=".9"/>')
    return cv.svg()


# --- seal and certificate -------------------------------------------------------------------------

def _seal(cv, col, cx, cy, d: dict, scale: float = 1.0):
    line = c(col["line"])
    cv.add(f'<g transform="translate({f1(cx)} {f1(cy)}) scale({fx(scale)}) translate({f1(-cx)} {f1(-cy)})">')
    cv.add(f'<circle cx="{cx}" cy="{cy}" r="82" fill="{paper(col)}" stroke="{line}" stroke-width="2"/>'
           f'<circle cx="{cx}" cy="{cy}" r="77" fill="none" {hair(col, .8)}/>'
           f'<circle cx="{cx}" cy="{cy}" r="55" fill="none" stroke="{line}" stroke-width="1.4"/>')
    for text, r, top_, ls_ in ((d["ring_top"], 62, True, 1), (d["ring_bottom"], 60, False, 1.4)):
        size = 8.6
        while size > 5.5 and width(plain(text, "meta"), "meta", size, ls_) > math.pi * r * .92:
            size -= .3
        ring(cv, col, plain(text, "meta"), cx=cx, cy=cy, r=r, size=size, top=top_, ls=ls_)
    for side in (-1, 1):
        cv.add(f'<circle cx="{cx + side * 66}" cy="{cy}" r="2.2" fill="{line}"/>')
    cv.add(icon("check-circle", cx - 17, cy - 36, 34, col["ink"], 1.8))
    say(cv, d["name"].upper(), x=cx, y=cy + 14, col=col, size=fit(d["name"].upper(), "num", 96, 15, 10, 1.4),
        face="num", anchor="middle", ls=1.4)
    say(cv, d.get("commit", "").upper(), x=cx, y=cy + 29, col=col, size=8.5, face="mono", anchor="middle", op=.7)
    cv.add("</g>")


def seal(d: dict, tone: str, th: dict, variant: str = "wide") -> str:
    cv, col = new("seal", variant, th, tone, SEAL, SEAL, d.get("title", "Seal"), d.get("desc", ""))
    _seal(cv, col, SEAL / 2, SEAL / 2, d)
    return cv.svg()


def certificate(d: dict, tone: str, th: dict, variant: str = "wide") -> str:
    checks = d["checks"]
    if variant != "wide":
        W, B = HALF, 10
        H = max(196, 66 + 29 * len(checks) + 14)
        cv, col = new("certificate", variant, th, tone, W, H, d.get("title", "Conformance"), d.get("desc", ""))
        sheet(cv, col, W=W, H=H, border=B, zones=4, plain=((B, B, 150, H - 2 * B),))
        cv.add(f'<path d="M{B + 150} {B}V{H - B}" {hair(col, .85)} stroke-width="1.2"/>')
        _seal(cv, col, B + 75, H / 2, d, scale=.74)
        x0 = B + 150
        plate(cv, col, "CONFORMANCE", x0 + 14, 24)
        cv.add(_open(col, f"M{x0} 50H{W - B}", .55, ' stroke-width=".8"'))
        y = 72
        for label, evidence in checks:
            label, evidence = str(label), str(evidence)
            cv.add(icon("check", x0 + 14, y - 10, 11, col["line"], 2.6))
            say(cv, label.upper(), x=x0 + 32, y=y, col=col, size=fit(label.upper(), "meta", W - B - 12 - (x0 + 32), 9.5, 7, .8),
                ls=.8)
            say(cv, evidence, x=x0 + 32, y=y + 11, col=col, size=7.5, face="mono", op=.65)
            y += 29
        return cv.svg()
    W, B = WIDE, 12
    H = max(212, 84 + 27 * len(checks))
    cv, col = new("certificate", variant, th, tone, W, H, d.get("title", "Conformance"), d.get("desc", ""))
    sheet(cv, col, W=W, H=H, border=B, zones=8, plain=((B, B, 196, H - 2 * B),))
    cv.add(f'<path d="M{B + 196} {B}V{H - B}" {hair(col, .85)} stroke-width="1.2"/>')
    _seal(cv, col, B + 98, H / 2, d)
    x0 = B + 196
    title(cv, col, dict(W=W, B=B, narrow=False), "CONFORMANCE", d.get("subject", ""), "EVIDENCE", x0=x0 + 20)
    y, rules = 78, []
    for label, evidence in checks:
        label, evidence = str(label), str(evidence)
        cv.add(icon("check", x0 + 22, y - 11, 13, col["line"], 2.6))
        say(cv, label.upper(), x=x0 + 44, y=y, col=col, size=11, ls=1)
        say(cv, evidence, x=W - B - 20, y=y, col=col, size=9.5, face="mono", anchor="end", op=.75)
        rules.append(f"M{x0 + 20} {y + 12}H{W - B - 20}")
        y += 27
    cv.add(_open(col, "".join(rules[:-1]), .3))
    return cv.svg()


# --- the registry -------------------------------------------------------------------------------

KINDS = {
    "schematic": (schematic, ("wide", "narrow"), "sheet"),
    "instruments": (instruments, ("wide", "narrow"), "sheet"),
    "plan": (plan, ("wide", "narrow"), "sheet"),
    "milestones": (milestones, ("wide", "narrow"), "sheet"),
    "roster": (roster, ("wide", "narrow"), "sheet"),
    "certificate": (certificate, ("wide", "narrow"), "sheet"),
    "placard": (placard, ("wide",), "card"),
    "seal": (seal, ("wide",), "card"),
}


def variants(kind: str, d: dict) -> tuple[str, ...]:
    """The files an element writes. `size: half` makes a roster or certificate one half-page file."""
    _, vs, _ = KINDS[kind]
    if d.get("size") == "half" and kind in ("roster", "certificate"):
        return ("half",)
    return vs


def describe(kind: str, d: dict) -> dict:
    """The data with a title and a description filled in from what it holds, when the file gave none."""
    d = dict(d)
    subject = d.get("subject") or "this repository"
    if kind == "schematic":
        d.setdefault("title", f"Schematic of {subject}")
        d.setdefault("desc", f"How {subject} runs: " + ", ".join(str(b.get("title", k)) for k, b in d.get("boxes", {}).items()) + ".")
    elif kind == "instruments":
        d.setdefault("title", f"Instruments for {subject}")
        d.setdefault("desc", f"Commits per week, days since the last release, tracked bytes by file type and counts for {subject}.")
    elif kind == "plan":
        d.setdefault("title", f"Plan of {subject}")
        d.setdefault("desc", f"{subject} as a floor plan: {d.get('total', 0)} tracked files in {len(d.get('rooms', ()))} rooms and a lobby.")
    elif kind == "milestones":
        n = sum(1 for e in d.get("events", ()) if not e.get("next") and not e.get("made"))
        d.setdefault("title", f"Milestones of {subject}")
        d.setdefault("desc", f"{n} releases of {subject} on a time line.")
    elif kind == "roster":
        d.setdefault("title", f"Contributors to {subject}")
        d.setdefault("desc", "; ".join(f"{p['name']}: {p['n']:,} commits" for p in d.get("people", ())) + ".")
    elif kind == "certificate":
        d.setdefault("title", f"Conformance of {subject}")
        d.setdefault("desc", f"{len(d.get('checks', ()))} checks on {subject}, each passing, with the evidence for it.")
    elif kind == "seal":
        d.setdefault("title", f"Seal: {subject}")
        d.setdefault("desc", f"{d.get('ring_top', '')}, {d.get('ring_bottom', '')}.")
    elif kind == "placard":
        d.setdefault("title", f"{d.get('owner', '')}/{d.get('name', '')}")
    return d


def draw(kind: str, d: dict, tone: str, theme: str, variant: str) -> str:
    """One finished file, checked against the banners lint and this kit's budget."""
    fn, _, klass = KINDS[kind]
    d = describe(kind, d)
    svg = fn(d, tone, THEMES[theme], "narrow" if variant == "half" else variant)
    problems = lint(svg, budget=BUDGET[klass])
    if problems:
        raise ValueError(f"{kind} {variant} {theme}: " + "; ".join(problems))
    return svg


def alt(kind: str, d: dict) -> str:
    """The accessible name: what the data file says, else the sheet's title and description."""
    if d.get("alt"):
        return d["alt"]
    d = describe(kind, d)
    parts = [d.get("title") or kind.capitalize(), d.get("desc", "")]
    return ". ".join(p.rstrip(".") for p in parts if p) + "."
