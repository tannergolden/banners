# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The footers: the foot of the same set of drawings, and the chips their links are made of.

A footer follows the standards' footer composition: a closing phrase, the
way back to the top, and the attribution line, here with the licence and a
date as options. Nothing is ruled above a footer: it starts at its own
border.

  F1 Title block   the foot of a sheet: notes, built by, licence, last change, the way up   (H1, H2)
  F2 Scale bar     a slim foot: a graphic scale, the closing lines, the way up        (H3)

An image in a README is one link at most, the one around it. So the footer
image as a whole is the "Back to Top" link, and each entry in the links row
is its own small image with its own link, drawn by `chip`.
"""
from __future__ import annotations

import math

from .canvas import Canvas, c
from .content import Footer
from .draw import solid, up_arrow
from .drafting import colours, hair, rule, sheet
from .layout import NARROW, WIDE
from .text import cap_height, f1, fit, flow, width


def _canvas(ft: Footer, code: str, th: dict, wide: bool, motion: bool) -> Canvas:
    stamp = f"{code} {th['name']}" + ("" if wide else " narrow") + ("" if motion else " still")
    title = ft.get("closing") or "Footer"
    return Canvas(WIDE if wide else NARROW, 0, title=title, desc=ft.spoken(), stamp=stamp)


def _heart(th: dict) -> str:
    return "rose" if th["dark"] else "crimson"


# --- F1 Title block ---------------------------------------------------------------------

def _cells(ft: Footer) -> list[tuple[str, str, str]]:
    """The title block's cells: who built it, under what licence, when it last changed, and the way back up."""
    cells = []
    if ft.on("built"):
        cells.append(("BUILT WITH  BY", ft.handle, "heart"))
    if ft.on("license"):
        cells.append(("LICENSE", ft.license, ""))
    if ft.on("updated"):
        cells.append(("UPDATED", ft.updated, ""))
    if ft.on("top"):
        cells.append(("RETURN TO", ft.get("top"), "up"))
    return cells


def _cell(cv: Canvas, col: dict, th: dict, *, x: float, y: float, w: float, h: float, label: str, value: str,
          mark: str, size: float) -> None:
    ink = c(col["ink"])
    if mark == "heart":
        lw = width("BUILT WITH ", "meta", 7, 1.1)
        cv.add(cv.L.text("BUILT WITH", face="meta", size=7, x=x + 8, y=y + 12, ls=1.1, fill=ink, opacity=.6),
               solid("heart", x + 8 + lw, y + 5.4, 7.5, _heart(th)),
               cv.L.text("BY", face="meta", size=7, x=x + 8 + lw + 10, y=y + 12, ls=1.1, fill=ink, opacity=.6))
    else:
        cv.add(cv.L.text(label, face="meta", size=7, x=x + 8, y=y + 12, ls=1.1, fill=ink, opacity=.6))
    vs = fit(value, "meta", w - 18 - (16 if mark == "up" else 0), size, 9)
    vx = x + 8
    if mark == "up":
        cv.add(up_arrow(vx, y + h - 21, 13, col["ink"], 2.6))
        vx += 16
    cv.add(cv.L.text(value, face="meta", size=vs, x=vx, y=y + h - 9, fill=ink))


def title_block(ft: Footer, th: dict, wide: bool = True, motion: bool = True) -> str:
    """The foot of the sheet: its notes, who built it, under what licence, when it last changed, and the way back up.

    The whole footer is the drawing's title block, one row ruled inside the
    sheet's border, in the print of the header above it: the closing phrase
    as the sheet's notes, then a cell for each thing the attribution line
    says. The date is the repository's last change a person made, measured
    with everything else, so the block moves only when the project does.
    """
    cv = _canvas(ft, "F1", th, wide, motion)
    W = cv.w
    col = colours(ft.tone, th)
    border = 12 if wide else 10
    cells = _cells(ft)
    left, right = border, W - border
    top = border
    ink = c(col["ink"])
    closing = ft.get("closing")
    if wide:
        note_w = (300 if cells else right - left) if closing else 0
        if closing:
            s, lines = flow(closing, "meta", 15, 12, note_w - 24, rows=2)
            rh = max(46.0, 22 + len(lines) * s * 1.25 + 4)
        else:
            rh = 46.0
        gx = left + note_w
        cw = (right - gx) / len(cells) if cells else 0
        H = top + rh + border
        sheet(cv, col, W=W, H=H, border=border, zones=8,
              plain=((gx, top, right - gx, rh),) if cells else ())
        if closing:
            cv.add(cv.L.text("NOTES", face="meta", size=7, x=left + 8, y=top + 12, ls=1.1, fill=ink, opacity=.6))
            yy = top + 12 + (rh - 12) / 2 - len(lines) * s * 1.25 / 2 + s * .95
            for line in lines:
                cv.add(cv.L.text(line, face="meta", size=s, x=left + 12, y=yy, fill=ink))
                yy += s * 1.25
            if cells:
                cv.add(f'<path d="M{f1(gx)} {f1(top)}V{f1(H - border)}" {hair(col, .85)} stroke-width="1.2"/>')
        for i, (label, value, mark) in enumerate(cells):
            x = gx + i * cw
            if i:
                cv.add(rule(col, f"M{f1(x)} {f1(top)}V{f1(top + rh)}"))
            _cell(cv, col, th, x=x, y=top, w=cw, h=rh, label=label, value=value, mark=mark, size=14)
    else:
        note_h = 0.0
        if closing:
            s_n, note_lines = flow(closing, "meta", 14, 12, right - left - 20, rows=3)
            note_h = 22 + len(note_lines) * s_n * 1.3 + 8
        rh = 36
        rows = math.ceil(len(cells) / 2)
        cw = (right - left) / 2
        H = top + note_h + rows * rh + border
        cells_top = top + note_h
        sheet(cv, col, W=W, H=H, border=border, zones=4,
              plain=((left, cells_top, right - left, rows * rh),) if cells else ())
        if closing:
            cv.add(cv.L.text("NOTES", face="meta", size=7, x=left + 8, y=top + 12, ls=1.1, fill=ink, opacity=.6))
            yy = top + 22 + s_n
            for line in note_lines:
                cv.add(cv.L.text(line, face="meta", size=s_n, x=left + 10, y=yy, fill=ink))
                yy += s_n * 1.3
            if cells:
                cv.add(f'<path d="M{f1(left)} {f1(cells_top)}H{f1(right)}" {hair(col, .85)} stroke-width="1.2"/>')
        for i, (label, value, mark) in enumerate(cells):
            r, k = divmod(i, 2)
            x = left + k * cw
            y = cells_top + r * rh
            last = i == len(cells) - 1 and k == 0
            w = right - left if last else cw
            if k:
                cv.add(rule(col, f"M{f1(x)} {f1(y)}V{f1(y + rh)}"))
            if r:
                cv.add(rule(col, f"M{f1(x)} {f1(y)}H{f1(x + w)}"))
            _cell(cv, col, th, x=x, y=y, w=w, h=rh, label=label, value=value, mark=mark, size=13)
    cv.h = H
    return cv.svg()


# --- F2 Scale bar ---------------------------------------------------------------------------

def _scale(cv: Canvas, col: dict, *, x: float, y: float) -> None:
    """A graphic scale a hundred pixels long, in five parts, alternately solid and open, figured every twenty."""
    ink = c(col["ink"])
    parts = []
    for i in range(5):
        fill = c(col["line"]) if i % 2 == 0 else "none"
        parts.append(f'<rect x="{f1(x + 20 * i)}" y="{f1(y)}" width="20" height="6" fill="{fill}" {hair(col, .9)}/>')
    cv.add(*parts)
    for i in range(6):
        cv.add(cv.L.text(str(20 * i), face="meta", size=7, x=x + 20 * i, y=y - 4, anchor="middle", fill=ink, opacity=.7))
    cv.add(cv.L.text("SCALE 1:1 \u00b7 PX", face="meta", size=7, x=x, y=y + 17, ls=1.2, fill=ink, opacity=.6))


def _attribution(cv: Canvas, ft: Footer, col: dict, th: dict, *, cx: float, y: float, size: float,
                 room: float) -> float:
    """"Built with (heart) by @handle", the licence and the date, centred on `cx`: on one line, or two when it must.

    Returns how far below `y` the last line's baseline sits.
    """
    ink = c(col["ink"])
    rest = " \u00b7 ".join(p for p in (f"{ft.license} License" if ft.on("license") else "", ft.get("updated")) if p)
    a, b = "Built with ", " by "
    hs = size * 1.02
    built_w = width(a, "meta", size) + hs + width(b, "meta", size) + width(ft.handle, "meta", size) if ft.on("built") else 0
    sep = width(" \u00b7 ", "meta", size)
    one = built_w + (sep if built_w and rest else 0) + width(rest, "meta", size)
    lines = [(built_w, rest)] if one <= room else [(built_w, ""), (0, rest)]
    dy = 0.0
    for n, (bw, text) in enumerate(lines):
        if not bw and not text:
            continue
        total = bw + (sep if bw and text else 0) + width(text, "meta", size)
        x = cx - total / 2
        if bw:
            cv.add(cv.L.text(a.strip(), face="meta", size=size, x=x, y=y + dy, fill=ink, opacity=.85),
                   solid("heart", x + width(a, "meta", size), y + dy - size * .8, hs, _heart(th)),
                   cv.L.text(b.strip(), face="meta", size=size, x=x + width(a, "meta", size) + hs + width(" ", "meta", size),
                             y=y + dy, fill=ink, opacity=.85),
                   cv.L.text(ft.handle, face="meta", size=size, x=x + width(a, "meta", size) + hs + width(b, "meta", size),
                             y=y + dy, fill=ink))
            x += bw
            if text:
                cv.add(cv.L.text("\u00b7", face="meta", size=size, x=x + sep / 2, y=y + dy, anchor="middle", fill=ink,
                                 opacity=.6))
                x += sep
        if text:
            cv.add(cv.L.text(text, face="meta", size=size, x=x, y=y + dy, fill=ink, opacity=.85))
        dy += size * 1.45
    return dy - size * 1.45


def scale_bar(ft: Footer, th: dict, wide: bool = True, motion: bool = True) -> str:
    """A slim foot for the strip: a graphic scale, the closing phrase over the attribution, and the way back up."""
    cv = _canvas(ft, "F2", th, wide, motion)
    W = cv.w
    col = colours(ft.tone, th)
    border = 10 if wide else 9
    ink = c(col["ink"])
    has_text = ft.on("closing") or ft.on("built") or ft.on("license") or ft.on("updated")
    if wide:
        # Compartments ruled on the sheet's own grid lines, which fall every fifty pixels from the left edge.
        side = 200 - border
        H = 2 * border + 66
        top = border
        mid = top + 33
        sheet(cv, col, W=W, H=H, border=border, zones=8,
              plain=((border, border, side, 66), (W - border - side, border, side, 66)))
        cv.add(f'<path d="M{f1(border + side + .5)} {f1(top)}V{f1(H - border)}M{f1(W - border - side + .5)} {f1(top)}'
               f'V{f1(H - border)}" {hair(col, .85)} stroke-width="1.2"/>')
        _scale(cv, col, x=border + (side - 100) / 2, y=mid - 3)
        cx = W / 2
        room = W - 2 * (border + side) - 32
        if ft.on("closing"):
            s = fit(ft.get("closing"), "meta", room, 16, 12)
            cv.add(cv.L.text(ft.get("closing"), face="meta", size=s, x=cx, y=mid - 2 if has_text else mid + 5,
                             anchor="middle", fill=ink))
        if ft.on("built") or ft.on("license") or ft.on("updated"):
            _attribution(cv, ft, col, th, cx=cx, y=mid + 17 if ft.on("closing") else mid + 4, size=11.5, room=room)
        if ft.on("top"):
            rx = W - border - side / 2
            text = ft.get("top")
            ts = fit(text, "meta", side - 44, 14, 10)
            total = 13 + 5 + width(text, "meta", ts)
            cv.add(cv.L.text("RETURN TO", face="meta", size=7, x=rx, y=mid - 10, anchor="middle", ls=1.2, fill=ink,
                             opacity=.6),
                   up_arrow(rx - total / 2, mid - 1, 13, col["ink"], 2.6),
                   cv.L.text(text, face="meta", size=ts, x=rx - total / 2 + 18, y=mid + 10, fill=ink))
    else:
        # A phone stacks it: the scale and the way up, then the closing lines under them.
        room = W - 2 * border - 24
        body = []
        if ft.on("closing"):
            s, lines = flow(ft.get("closing"), "meta", 15, 12, room, rows=3)
            body.append(("closing", s, lines))
        H = border + 48
        extra = 0.0
        for _, s, lines in body:
            extra += len(lines) * s * 1.25 + 6
        if ft.on("built") or ft.on("license") or ft.on("updated"):
            extra += 34
        H += extra + (14 if extra else 0) + border
        sheet(cv, col, W=W, H=H, border=border, zones=4, plain=((border, border, W - 2 * border, 44),))
        top = border
        cv.add(f'<path d="M{f1(border)} {f1(top + 44)}H{f1(W - border)}" {hair(col, .85)} stroke-width="1.2"/>')
        _scale(cv, col, x=border + 18, y=top + 19)
        if ft.on("top"):
            text = ft.get("top")
            ts = fit(text, "meta", 120, 13, 10)
            x = W - border - 14 - width(text, "meta", ts) - 18
            cv.add(up_arrow(x, top + 17, 12, col["ink"], 2.6),
                   cv.L.text(text, face="meta", size=ts, x=x + 17, y=top + 27, fill=ink))
        y = top + 44 + 14
        for _, s, lines in body:
            for line in lines:
                y += s
                cv.add(cv.L.text(line, face="meta", size=s, x=W / 2, y=y, anchor="middle", fill=ink))
                y += s * .25
            y += 6
        if ft.on("built") or ft.on("license") or ft.on("updated"):
            _attribution(cv, ft, col, th, cx=W / 2, y=y + 12, size=11.5, room=room)
    cv.h = H
    return cv.svg()


# --- the links row ------------------------------------------------------------------------

def chip(label: str, th: dict, tone: str = "") -> str:
    """One link in the row under a footer: its label in capitals on a small plate of the same print."""
    col = colours(tone, th)
    s = 11
    text = label.upper()
    w = width(text, "meta", s, 1.2) + 24
    cv = Canvas(w, 26, title=label, desc=f"Link: {label}", stamp=f"link {th['name']}")
    cv.add(f'<rect x=".5" y=".5" width="{f1(w - 1)}" height="25" rx="3" fill="{c(col["paper"])}" {hair(col, .7)}/>')
    cv.add(cv.L.text(text, face="meta", size=s, x=w / 2, y=13 + cap_height("meta", s) / 2, anchor="middle", ls=1.2,
                     fill=c(col["ink"])))
    return cv.svg()
