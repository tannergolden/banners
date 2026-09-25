# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""What the preview page asks the kit, answered by the kit itself.

The page runs this module under Brython, a Python written in JavaScript, so
a toggle or an edited line is redrawn by the same code that will draw the
committed files. `make preview` runs the same function under CPython to
pre-render the sets the page opens with, and the page checks the two agree
byte for byte before it trusts itself to draw live.

A request is a measurement and a config, exactly what a run has:

  {"measurement": {...},             what `measure` returned, or a sample
   "config": {"theme": "redprint", ...}, what .github/banners.yml would say
   "codes": ["H1", "F2"],            which designs; all when absent, none when empty
   "only": ["day", "narrow-day"],    which variants; all when absent
   "markdown": true,                 the header snippet's Markdown fallback
   "snippet": true, "lint": true,
   "composed": true,                 what each field came out as, for the page's placeholders
   "setup": true,                    the config file, the README blocks and the first commit
   "shade": "greenprint"}            which colour of a rainbowprint the setup is drawn in

and the answer maps each code to its files, its snippet and its problems.
"""
from __future__ import annotations

import json

from . import config, plan, snippets
from .compose import compose, every_figure
from .designs import DESIGNS, check, render
from .drafting import RAINBOW, SPECTRUM


def answer(request: dict) -> dict:
    m = request["measurement"]
    cfg = config.validate(request.get("config") or {})
    header, footer, notes = compose(m, cfg)
    only = set(request.get("only") or ())
    out: dict = {}
    codes = request.get("codes")
    for code in list(DESIGNS) if codes is None else codes:
        design = DESIGNS[code]
        content = header if design.kind == "header" else footer
        files = render(design, content, only)
        entry: dict = {"files": files}
        if request.get("snippet", True):
            entry["snippet"] = (snippets.header(design, header, markdown=request.get("markdown", True))
                                if design.kind == "header" else snippets.footer(design, footer))
            entry["alt"] = header.alt() if design.kind == "header" else footer.spoken()
        if request.get("lint", True):
            entry["problems"] = check(design, files)
        out[code] = entry
    if request.get("composed"):
        out["composed"] = {
            "header": {k: getattr(header, k) for k in ("emoji", "title", "tagline", "motto", "description")}
            | {"figures": [list(f) for f in header.figures]},
            "footer": {k: getattr(footer, k) for k in ("closing", "top", "handle", "license", "updated")}
            | {"links": [list(link) for link in footer.links]},
            "notes": notes,
            "available": [list(f) for f in every_figure(m["mode"], m)],
        }
    if request.get("setup"):
        # A rainbowprint is drawn in one colour of the spectrum at a time: the one the page is showing.
        rainbow = cfg["theme"] == RAINBOW
        shade = request.get("shade") if request.get("shade") in SPECTRUM else SPECTRUM[0]
        p = plan.plan(m, dict(cfg, theme=shade) if rainbow else cfg, draw=False)
        changed = sorted(p["files"]) + [cfg["readme_path"], ".github/banners.lock.json"]
        out["setup"] = {"config": config.dump(cfg), "summary": plan.describe(p), "blocks": p["blocks"],
                        "commit": plan.commit_message(p, None, changed, rainbow=rainbow)}
    return out


def answer_json(text: str) -> str:
    return json.dumps(answer(json.loads(text)), ensure_ascii=False, separators=(",", ":"))
