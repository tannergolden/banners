# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Builds `preview.html`: every design, drawn by the kit, in one self-contained page.

The page has to show what the kit will draw, so nothing in it is drawn by
hand. Two things put the kit's own output on the page:

  1. Pre-rendered sets. `make preview` renders every design, in every
     variant, for a handful of field and content presets, through the same
     `live.answer` the page calls. They are what the page opens with, and
     all it has in a viewer that will not run the live renderer.
  2. The kit itself, running in the page. Brython, a Python written in
     JavaScript, is inlined with the stdlib modules the kit imports and the
     kit's own source, so a toggle or an edited line is redrawn by the code
     that will draw the committed files. Before the page trusts it, it
     redraws the default set and compares it with the pre-rendered one,
     byte for byte.

Brython is fetched once from the npm registry, pinned by checksum, and kept
in a cache directory; nothing else is fetched, and the page fetches nothing.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import re
import tarfile
import urllib.request
from pathlib import Path

from . import KIT_VERSION, config, live, plan, sample
from .compose import DEFAULT_FIGURES, FIGURES
from .designs import DESIGNS
from .drafting import DEFAULT_PRINT, PRINTS, RAINBOW, SPECTRUM
from .palette import hexof
from .snippets import BREAKPOINT
from .text import FILES, PREFIX, fonts_dir

PAGE = Path(__file__).resolve().parent / "page"
KIT = Path(__file__).resolve().parent

BRYTHON_VERSION = "3.14.3"
BRYTHON_URL = f"https://registry.npmjs.org/brython/-/brython-{BRYTHON_VERSION}.tgz"
BRYTHON_SHA256 = "7b154153ce52253034f2fa737be401fa5106205b5333bcde39df4f2ddb87c372"

# The stdlib modules the kit imports under Brython: measured, not guessed, by
# running every design there and reading `__BRYTHON__.imported`, plus the one
# that list cannot see, the JavaScript SHA-256 `hashlib` loads by name for the
# terminal's typing rhythm. Brython's full library is 4.8 MB; these are about one.
BRYTHON_MODULES = (
    "crypto_js.rollups.sha256",
    "__future__", "_ast", "_codecs", "_collections", "_collections_abc", "_contextvars", "_frozen_importlib",
    "_functools", "_imp", "_importlib", "_io", "_io_classes", "_json", "_locale", "_operator", "_py_abc",
    "_py_warnings", "_random", "_suggestions", "_sys", "_thread", "_tokenize", "_typing", "_warnings", "_weakref",
    "_weakrefset", "abc", "annotationlib", "ast", "bisect", "browser", "browser.aio", "browser.html", "builtins",
    "codecs", "collections", "collections.abc", "copy", "copyreg", "dataclasses", "dis", "enum", "errno",
    "functools", "genericpath", "hashlib", "html", "html.entities", "importlib", "importlib._bootstrap",
    "importlib._bootstrap_external", "importlib.machinery", "inspect", "io", "itertools", "javascript", "json",
    "json.encoder", "keyword", "linecache", "marshal", "math", "operator", "os", "os.path", "posix", "posixpath",
    "python_re", "random", "re", "reprlib", "stat", "sys", "textwrap", "time", "token", "tokenize", "types", "typing",
    "warnings", "weakref",
)

# The kit's modules the page needs: everything but this builder.
PAGE_MODULES = ("__init__", "canvas", "compose", "config", "content", "designs", "draw", "drafting", "footers",
                "headers", "layout", "live", "palette", "plan", "readme", "snippets", "text")

# --- subjects: what the page can show even without the live renderer ---------------------

# The two sample measurements, made up, and trophies' own sample subjects.
SUBJECTS = {
    "repository": ("Repository", sample.REPOSITORY),
    "profile": ("Profile", sample.PROFILE),
}
# The stubs a consumer copies, shown on the page as they are in examples/.
STUBS = {"repository": "stub-repository.yml", "profile": "stub-profile.yml", "check": "stub-check.yml"}
EXAMPLES = KIT.parent.parent / "examples"


def request(subject: str, tone: str) -> dict:
    """What the page asks for a subject in a print, with every other choice left at its default."""
    return {"measurement": SUBJECTS[subject][1], "config": {"theme": tone}, "codes": list(DESIGNS),
            "markdown": True, "composed": True, "setup": True}


# --- Brython ------------------------------------------------------------------------------

def brython(cache: Path) -> tuple[str, str]:
    """The Brython runtime and the stdlib modules the kit needs, as two scripts."""
    cache.mkdir(parents=True, exist_ok=True)
    tgz = cache / f"brython-{BRYTHON_VERSION}.tgz"
    if not tgz.exists():
        with urllib.request.urlopen(BRYTHON_URL, timeout=120) as response:  # noqa: S310 - pinned https source
            tgz.write_bytes(response.read())
    data = tgz.read_bytes()
    got = hashlib.sha256(data).hexdigest()
    if got != BRYTHON_SHA256:
        raise SystemExit(f"{tgz}: sha256 {got}, wanted {BRYTHON_SHA256}")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        runtime = tar.extractfile("package/brython.min.js").read().decode("utf-8")
        stdlib = tar.extractfile("package/brython_stdlib.js").read().decode("utf-8")
    start = stdlib.index("var scripts = ") + len("var scripts = ")
    end = stdlib.rindex("__BRYTHON__.update_VFS(scripts)")
    scripts = json.loads(stdlib[start:end].rstrip().rstrip(";"))
    subset = {"$timestamp": scripts["$timestamp"]}
    subset.update({name: scripts[name] for name in BRYTHON_MODULES if name in scripts})
    vfs = "__BRYTHON__.use_VFS = true;\n__BRYTHON__.update_VFS(" + _js(subset) + ")\n"
    return runtime, vfs


def kit_vfs() -> str:
    mods = {}
    for stem in PAGE_MODULES:
        source = (KIT / f"{stem}.py").read_text(encoding="utf-8")
        name = "bannerkit" if stem == "__init__" else f"bannerkit.{stem}"
        mods[name] = [".py", source, []] + ([1] if stem == "__init__" else [])
    return "__BRYTHON__.update_VFS(" + _js(mods) + ")\n"


def _js(value) -> str:
    """JSON that is safe inside a <script>: every `<` escaped, so no tag can close it early."""
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.replace("<", "\\u003c")


# --- the pre-rendered sets --------------------------------------------------------------

GLYPH = re.compile(r'<path id="[smn]\d+" d="[^"]*"/>')


def strip(svg: str) -> list:
    """An SVG without its glyph outlines, and the ids to put back: the page holds each outline once."""
    found = list(GLYPH.finditer(svg))
    if not found:
        return [svg, ""]
    first, last = found[0].start(), found[-1].end()
    block = svg[first:last]
    if "".join(m.group(0) for m in found) != block:
        raise SystemExit("glyph outlines are not one run; the page could not put them back")
    ids = " ".join(re.match(r'<path id="([smn]\d+)"', m.group(0)).group(1) for m in found)
    return [svg[:first] + "\x00" + svg[last:], ids]


def restore(entry: list, table: dict) -> str:
    stripped, ids = entry
    if not ids:
        return stripped
    return stripped.replace("\x00", "".join(f'<path id="{i}" d="{table[i]}"/>' for i in ids.split()), 1)


def glyph_table() -> dict:
    from .text import fonts

    return {f"{PREFIX[face]}{ord(ch)}": data[0] for face, font in fonts().items() for ch, data in font["g"].items()}


def corpus() -> dict:
    """Every subject, in every print, with every design: what the page opens with and falls back to."""
    table = glyph_table()
    out: dict = {}
    for subject in SUBJECTS:
        for tone in PRINTS:
            answer = live.answer(request(subject, tone))
            for code, entry in answer.items():
                if code not in DESIGNS:
                    continue
                files = {}
                for name, svg in entry["files"].items():
                    packed = strip(svg)
                    if restore(packed, table) != svg:
                        raise SystemExit(f"{code} {name}: stripping the outlines is not reversible")
                    files[name] = packed
                entry["files"] = files
            out[f"{subject}|{tone}"] = answer
    return out


# --- the page -------------------------------------------------------------------------

def emblems_badges(kit: Path | None) -> dict:
    """The four header badges, drawn by emblems itself when a checkout is at hand."""
    if not kit or not kit.exists():
        return {}
    import importlib.util

    spec = importlib.util.spec_from_file_location("badge_kit", kit)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rows = (("status", "Status", "Active", "green", "pulse"), ("role", "Role", "Tool", "pink", "book"),
            ("context", "Context", "Banners", "purple", "layers"), ("license", "License", "MIT", "yellow", "scale"))
    return {name: {"svg": mod.render(label, message, "black", color, icon, "for-the-badge"), "alt": f"{label}: {message}"}
            for name, label, message, color, icon in rows}


# What a README gets from a config that says nothing: the header and the footer made for it.
DEFAULTS = plan.designs(config.validate({}))


def build(out: Path, cache: Path, emblems_kit: Path | None = None) -> dict:
    runtime, stdlib = brython(cache)
    base, extra = ((fonts_dir() / name).read_text(encoding="utf-8") for name in FILES)
    rendered = corpus()
    packed = base64.b64encode(gzip.compress(json.dumps(rendered, ensure_ascii=False, separators=(",", ":"))
                                            .encode("utf-8"), 9, mtime=0)).decode("ascii")
    data = {
        "kit": KIT_VERSION,
        "brython": BRYTHON_VERSION,
        "breakpoint": BREAKPOINT,
        "designs": [{"code": d.code, "slug": d.slug, "name": d.name, "blurb": d.blurb, "animates": d.animates,
                     "pairs": list(d.pairs), "kind": d.kind, "default": d in DEFAULTS} for d in DESIGNS.values()],
        "subjects": {key: {"label": label, "name": m["subject"], "mode": m["mode"], "measurement": m}
                     for key, (label, m) in SUBJECTS.items()},
        "figures": {mode: list(keys) for mode, keys in FIGURES.items()},
        "defaultFigures": {mode: list(keys) for mode, keys in DEFAULT_FIGURES.items()},
        "top": config.DEFAULTS["top"],
        "stubs": {key: (EXAMPLES / name).read_text(encoding="utf-8") for key, name in STUBS.items()},
        # Each print's swatch: its lines by day and its sheet by night.
        "tones": {k: {"label": v["label"], "band": hexof(v["line"]), "deep": hexof(v["sheet"])} for k, v in PRINTS.items()},
        "defaultTone": DEFAULT_PRINT,
        "spectrum": list(SPECTRUM),
        "rainbow": RAINBOW,
        "badges": emblems_badges(emblems_kit),
    }
    html = (PAGE / "page.html").read_text(encoding="utf-8")
    parts = {
        "/*@CSS@*/": (PAGE / "page.css").read_text(encoding="utf-8"),
        "/*@DATA@*/": _js(data),
        "/*@CORPUS@*/": _js(packed),
        "/*@FONTS@*/": _js([base, extra]),
        "/*@APP@*/": (PAGE / "page.js").read_text(encoding="utf-8"),
        "/*@BRYTHON@*/": runtime.replace("</script", "<\\/script"),
        "/*@STDLIB@*/": stdlib,
        "/*@KIT@*/": kit_vfs(),
        "#@BOOT@": (PAGE / "boot.py").read_text(encoding="utf-8"),
    }
    for marker in parts:
        if html.count(marker) != 1:
            raise SystemExit(f"page.html must hold {marker} exactly once")
    # One pass, so nothing inserted can be mistaken for a later marker.
    html = re.sub("|".join(re.escape(m) for m in parts), lambda m: parts[m.group(0)], html)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return {"bytes": len(html.encode("utf-8")), "sets": len(rendered),
            "files": sum(len(e["files"]) for a in rendered.values() for code, e in a.items() if code in DESIGNS)}
