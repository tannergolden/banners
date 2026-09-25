# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""What a header and a footer carry, and the alt text that says it.

A header follows the standards' header matrix, less its emoji: a FULLY CAPPED
title, a bold one-line description (the tagline here), an italic principle
(the motto), and optionally a longer description. Under them runs a row of
figures, each a label and a value: the repository or the account, then what
GitHub says about it (the release, stars, forks, followers and so on).
`compose` fills all of it from a measurement; nothing here knows where the
values came from. A footer follows the footer composition: a closing
phrase, the way back to the top, and the attribution line.

Every field can be switched off. A field that is off is neither drawn nor
spoken: the alt text is built from exactly what the image shows.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

HEADER_FIELDS = ("title", "tagline", "motto", "description", "figures")
FOOTER_FIELDS = ("closing", "top", "built", "license", "updated", "links")

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December")


def long_date(iso: str) -> str:
    """`2026-09-25` as `September 25, 2026`, with no locale in the way."""
    try:
        y, m, d = (int(p) for p in iso.split("-"))
        return f"{MONTHS[m - 1]} {d}, {y}"
    except (ValueError, IndexError):
        return iso


def sentence(text: str) -> str:
    """A field as a sentence for alt text: trimmed, and ending in a stop."""
    text = text.strip()
    return text if not text or text[-1] in ".!?" else text + "."


@dataclass(frozen=True)
class Header:
    title: str = "Banners"
    tagline: str = "Headers and footers a README draws for itself."
    motto: str = "Drawn, never fetched."
    description: str = "Committed SVGs, drawn from one data file, with nothing requested when the page is read."
    # (LABEL, value) pairs, in the order they are drawn.
    figures: tuple = (("PROJECT", "tannergolden/banners"), ("RELEASE", "v1.0.0"), ("LANGUAGE", "Python"),
                      ("LICENSE", "MIT"))
    # The print it is drawn in: a key of `drafting.PRINTS`.
    tone: str = "blueprint"
    off: frozenset = field(default_factory=frozenset)

    def on(self, name: str) -> bool:
        if name == "figures":
            return name not in self.off and bool(self.figures)
        return name not in self.off and bool(str(getattr(self, name)).strip())

    def get(self, name: str) -> str:
        return str(getattr(self, name)).strip() if self.on(name) else ""

    def with_(self, **changes) -> "Header":
        return replace(self, **changes)

    @property
    def caps(self) -> str:
        """The title as the standards set a title: fully capped."""
        return self.get("title").upper()

    @property
    def shown_figures(self) -> tuple:
        return self.figures if self.on("figures") else ()

    def spoken_title(self) -> str:
        return self.get("title") or next((v for _, v in self.shown_figures), "") or "Header"

    def spoken(self) -> str:
        """Everything the image shows after its title, as sentences."""
        parts = [sentence(self.get(k)) for k in ("tagline", "motto", "description")]
        parts += [sentence(f"{label.capitalize()}: {value}") for label, value in self.shown_figures]
        return " ".join(p for p in parts if p) or self.spoken_title()

    def alt(self) -> str:
        head = self.spoken_title()
        rest = self.spoken()
        return head if rest == head else f"{head}: {rest}"


@dataclass(frozen=True)
class Footer:
    closing: str = "Drawn at both ends. Fetched at neither."
    top: str = "Back to Top"
    handle: str = "@tannergolden"
    license: str = "MIT"
    updated: str = "2026-09-25"
    links: tuple = (("Docs", "docs/Banner-Kit.md"), ("Issues", "https://github.com/tannergolden/banners/issues"),
                    ("Releases", "https://github.com/tannergolden/banners/releases"))
    built: bool = True
    # The print it is drawn in, the header's: a key of `drafting.PRINTS`.
    tone: str = "blueprint"
    off: frozenset = field(default_factory=frozenset)

    def on(self, name: str) -> bool:
        if name in self.off:
            return False
        value = getattr(self, name)
        return bool(value) if not isinstance(value, str) else bool(value.strip())

    def get(self, name: str) -> str:
        return str(getattr(self, name)).strip() if self.on(name) else ""

    def with_(self, **changes) -> "Footer":
        return replace(self, **changes)

    @property
    def date(self) -> str:
        return long_date(self.updated) if self.on("updated") else ""

    @property
    def license_line(self) -> str:
        return f"Distributed under the {self.license} License." if self.on("license") else ""

    @property
    def link_labels(self) -> list[str]:
        return [label for label, _ in self.links] if self.on("links") else []

    def spoken(self) -> str:
        parts = [sentence(self.get("closing")), sentence(self.get("top"))]
        if self.on("built"):
            parts.append(f"Built with love by {self.handle}.")
        parts.append(self.license_line)
        if self.date:
            parts.append(f"Last updated {self.date}.")
        return " ".join(p for p in parts if p) or "Footer"
