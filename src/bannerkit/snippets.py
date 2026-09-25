# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The markup a README pastes: one `<picture>` per image.

THE ORDER OF THE SOURCES IS THE WHOLE THING, as the masthead found: a browser
takes the first `<source>` whose media matches, so the narrower conditions
come first. Width, then reduced motion, then the colour scheme, then the
`<img>`, which carries the alt text whichever source was chosen.

GitHub keeps `media` on a `<source>` whatever the query says; the masthead
checked `max-width` and the combined queries against the real renderer.
"""
from __future__ import annotations

import math
from html import escape

from .content import Footer, Header, sentence
from .designs import slug
from .layout import WIDE, Design

BASE = "assets/banners"

# The width below which a phone gets the narrow file. Derived, not picked:
# the wide layouts set their secondary lines at 15 px, and a reader should
# not have to read anything smaller than 10 px, so the wide file may shrink
# to two thirds of its width and no further. Past that is the narrow file.
READABLE = 10
SECONDARY = 15
GUTTERS = 32
BREAKPOINT = math.ceil(WIDE * READABLE / SECONDARY) + GUTTERS - 1


def picture(kind: str, design: Design, alt: str, base: str = BASE, indent: str = "") -> str:
    sources = [
        (f"(max-width: {BREAKPOINT}px) and (prefers-color-scheme: dark)", f"{kind}-narrow-dark"),
        (f"(max-width: {BREAKPOINT}px)", f"{kind}-narrow-day"),
    ]
    if design.animates:
        sources += [
            ("(prefers-reduced-motion: reduce) and (prefers-color-scheme: dark)", f"{kind}-still-dark"),
            ("(prefers-reduced-motion: reduce)", f"{kind}-still-day"),
        ]
    sources.append(("(prefers-color-scheme: dark)", f"{kind}-dark"))
    lines = [f"{indent}<picture>"]
    lines += [f'{indent}  <source media="{media}" srcset="{base}/{name}.svg">' for media, name in sources]
    lines.append(f'{indent}  <img alt="{escape(alt, quote=True)}" src="{base}/{kind}-day.svg">')
    lines.append(f"{indent}</picture>")
    return "\n".join(lines)


def header(design: Design, h: Header, *, markdown: bool = True, base: str = BASE) -> str:
    """The header block: centred, with the top anchor the footer links back to.

    With `markdown`, a field the image leaves out and the standards' header
    matrix asks for (the bold line, the italic tagline) is written under the
    image as Markdown, so switching it off in the drawing does not drop it
    from the page.
    """
    parts = ["<!-- markdownlint-disable MD041 -->", "", '<div align="center">', "", '<a name="top"></a>', "",
             picture("header", design, h.alt(), base)]
    if markdown:
        if h.tagline.strip() and not h.on("tagline"):
            parts += ["", f"**{sentence(h.tagline)}**"]
        if h.motto.strip() and not h.on("motto"):
            parts += ["", f"_{sentence(h.motto)}_"]
    parts += ["", "</div>"]
    return "\n".join(parts) + "\n"


def chip(label: str, url: str, base: str = BASE) -> str:
    name = slug(label)
    return (f'<a href="{escape(url, quote=True)}"><picture><source media="(prefers-color-scheme: dark)" '
            f'srcset="{base}/link-{name}-dark.svg"><img alt="{escape(label, quote=True)}" '
            f'src="{base}/link-{name}-day.svg"></picture></a>')


def footer(design: Design, ft: Footer, *, base: str = BASE) -> str:
    """The footer block. The image is the way back to the top; each link is its own image."""
    image = picture("footer", design, ft.spoken(), base)
    if ft.on("top"):
        image = '<a href="#top">' + image.replace("<picture>", "<picture>", 1) + "</a>"
    parts = ['<div align="center">', "", image]
    if ft.on("links") and ft.links:
        parts += ["", "\n".join(chip(label, url, base) for label, url in ft.links)]
    parts += ["", "</div>"]
    return "\n".join(parts) + "\n"
