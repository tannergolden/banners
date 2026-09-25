# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""What a run draws and writes, and the commit that records it.

`plan(measurement, config)` is the whole of a run that does not touch the
network or the disk: it composes the header and the footer, draws every
file, and writes the two README blocks. `run`, `render`, `check` and
`preview` all go through it, and so does the preview page, under Brython,
which is why it is pure.

The commit message says what the banners now show and what moved since
the last drawing, so no two refreshes read alike, the way trophies' do.
"""
from __future__ import annotations

import posixpath
import textwrap

from . import readme, snippets
from .compose import FIGURES, compose
from .designs import FOOTERS, HEADERS, names, render
from .drafting import SPECTRUM

HEADER_DESIGNS = {"sheet": "H1", "section": "H2", "strip": "H3"}
FOOTER_DESIGNS = {"title-block": "F1", "scale-bar": "F2"}
# The footer each header was drawn to sit above.
PAIRED = {"sheet": "title-block", "section": "title-block", "strip": "scale-bar"}
# The commit's gitmoji: a placard, which is what a banner is.
GITMOJI = "\U0001FAA7"

# How the commit message says each figure: (plural, singular).
PHRASES = {
    "project": ("project {}", None), "account": ("account {}", None), "release": ("release {}", None),
    "stars": ("{} stars", "{} star"), "forks": ("{} forks", "{} fork"), "watchers": ("{} watchers", "{} watcher"),
    "issues": ("{} open issues", "{} open issue"), "pulls": ("{} open pull requests", "{} open pull request"),
    "language": ("language {}", None), "license": ("license {}", None), "updated": ("the last change on {}", None),
    "created": ("created in {}", None), "site": ("site {}", None), "followers": ("{} followers", "{} follower"),
    "following": ("following {}", None), "repositories": ("{} repositories", "{} repository"),
    "earned": ("{} stars earned", "{} star earned"),
    "contributions": ("{} contributions in the last year", "{} contribution in the last year"),
    "since": ("member since {}", None), "location": ("location {}", None), "company": ("company {}", None),
}


def designs(cfg: dict) -> tuple:
    """The header and footer designs the config asks for; either may be None."""
    header = HEADERS[HEADER_DESIGNS[cfg["header"]]] if cfg["header"] != "none" else None
    key = cfg["footer"] or PAIRED.get(cfg["header"], "title-block")
    footer = FOOTERS[FOOTER_DESIGNS[key]] if key != "none" else None
    return header, footer


def plan(m: dict, cfg: dict, draw: bool = True) -> dict:
    """Everything a run writes for this measurement under this config: the files by path, and the README blocks.

    With `draw` false the files are named but not drawn, which is all a
    commit message or a summary needs.
    """
    header, footer, notes = compose(m, cfg)
    hd, fd = designs(cfg)
    out = cfg["out"].strip("/") or "."
    base = posixpath.relpath(out, posixpath.dirname(cfg["readme_path"]) or ".")
    files, blocks = {}, {}
    for design, content in ((hd, header), (fd, footer)):
        if design:
            drawn = render(design, content) if draw else {name: "" for name in names(design, content)}
            files.update({f"{out}/{name}": svg for name, svg in drawn.items()})
            snippet = (snippets.header(design, content, base=base) if design.kind == "header"
                       else snippets.footer(design, content, base=base))
            blocks[design.kind] = readme.block(design.kind, snippet)
    if fd and not hd:
        # The footer always links to the top of the README, so the top has to
        # be there even when no header is drawn.
        blocks["header"] = readme.block("header", snippets.anchor())
    return {"mode": m["mode"], "subject": m["subject"], "today": m.get("today", ""), "out": out, "theme": header.tone,
            "designs": [d for d in (hd, fd) if d], "header": header, "footer": footer, "files": files,
            "blocks": blocks, "notes": notes + list(m.get("notes") or ())}


def _phrase(mode: str, key: str, value: str) -> str:
    many, one = PHRASES["earned" if (mode, key) == ("profile", "stars") else key]
    return (one if one and value == "1" else many).format(value)


def facts(p: dict) -> dict:
    """What the banners show, as phrases, keyed so two runs can be compared."""
    mode = p["mode"]
    keys = {label: key for key, label in FIGURES[mode].items()}
    h, f = p["header"], p["footer"]
    shown = {}
    if any(d.kind == "header" for d in p["designs"]):
        for field, say in (("title", "the title {}"), ("tagline", "a new tagline"), ("motto", "a new note"),
                           ("description", "a new description")):
            if h.get(field):
                shown[field] = (h.caps if field == "title" else h.get(field), say.format(h.caps))
        for label, value in h.shown_figures:
            key = keys.get(label, label.lower())
            shown["figure:" + key] = (value, _phrase(mode, key, value))
    if any(d.kind == "footer" for d in p["designs"]):
        if f.on("license"):
            shown["footer:license"] = (f.license, _phrase(mode, "license", f.license))
        if f.on("updated"):
            shown["footer:updated"] = (f.updated, _phrase(mode, "updated", f.updated))
        if f.on("links") and f.links:
            labels = [label for label, _ in f.links]
            shown["footer:links"] = (", ".join(labels), "the buttons " + _series(labels))
    return shown


def changes(before: dict | None, now: dict) -> list[tuple[str, str]]:
    """(phrase now, what it was) for everything that moved, in the order the banners show it."""
    if before is None:
        return []
    out = []
    for key, (value, phrase) in now.items():
        was = before.get(key)
        if was is None or was[0] != value:
            out.append((phrase, was[0] if was else ""))
    return out


def describe(p: dict) -> str:
    """One line for the log and the action's `summary` output."""
    names = " and ".join(f"{d.code} {d.name}" for d in p["designs"]) or "no banners"
    figs = ", ".join(f"{label.lower()} {value}" for label, value in p["header"].shown_figures)
    return f"banners for {p['subject']} ({p['mode']}): {names} in {p['theme']}" + (f"; {figs}" if figs else "")


def _wrap(text: str) -> str:
    return textwrap.fill(text, 72, break_long_words=False, break_on_hyphens=False)


def _series(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def commit_message(p: dict, before: dict | None, changed: list[str], run: str = "", rainbow: bool = False) -> str:
    """A Conventional Commit for this run: what the banners now show, what moved, and why it is committed.

    With `rainbow`, the banners are a rainbowprint, and the body says which
    colour of the spectrum this drawing is and which the next update takes.
    """
    now = facts(p)
    moved = changes(before, now)
    head = f"chore(banners): {GITMOJI} "
    if before is None:
        subject = head + f"draw the banners for {p['subject']}"
    elif moved:
        subject = head + "redraw with " + _series([phrase for phrase, _ in moved[:2]])
        if len(subject) > 72:
            subject = head + "redraw with " + moved[0][0]
        if len(subject) > 72:
            subject = head + f"redraw the banners for {p['subject']}"
    else:
        subject = head + f"redraw the banners for {p['subject']}"
    where = f" in run {run}" if run else ""
    title = p["header"].caps
    figures = [phrase for key, (_, phrase) in now.items() if key.startswith("figure:")]
    first = f"Measured {p['subject']} on {p['today']}{where}."
    if title:
        first += f" The header reads {title}" + (f", with {_series(figures)}" if figures else "") + "."
    if "footer:updated" in now:
        first += f" The footer dates the last change {now['footer:updated'][0]}."
    if rainbow and p["theme"] in SPECTRUM:
        i = SPECTRUM.index(p["theme"])
        first += (f" As a rainbowprint, this drawing is the {p['theme']}, colour {i + 1} of {len(SPECTRUM)};"
                  f" the next update will be the {SPECTRUM[(i + 1) % len(SPECTRUM)]}.")
    paras = [_wrap(first)]
    if moved:
        paras.append(_wrap("Changed since the last drawing: "
                           + _series([phrase + (f" (was {was})" if was else "") for phrase, was in moved]) + "."))
    images = [c for c in changed if c.endswith(".svg")]
    others = [c for c in changed if not c.endswith(".svg")]
    what = (f"{len(images)} image{'s' if len(images) != 1 else ''}" if images else "") \
        + (" and " if images and others else "") + ", ".join(others)
    paras.append(_wrap(f"This run rewrote {what}. Nothing is fetched when the README is viewed, so every value "
                       "the banners show has to be committed. The kit recognises this commit by its scope and "
                       "never counts it as the repository's last change."))
    return subject + "\n\n" + "\n\n".join(paras) + "\n"
