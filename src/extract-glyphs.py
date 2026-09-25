#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Where `fonts/glyphs-extra.json` comes from, and the proof that it matches.

The kit draws every letter as a path. The outlines it starts from are
trophies' `fonts/glyphs.json`, copied here byte for byte, which holds only
the characters a trophy needs: no `@`, no brackets, no `!`, no space. A
footer that says "Built with love by @tannergolden" needs more than that, so
the characters it lacks are drawn from the same three fonts, the same way,
into a supplement that sits beside it and never overrides it.

"The same way" is checked, not claimed. Before this writes anything it
re-extracts every glyph `glyphs.json` already holds and requires each one to
come out byte-identical, advance included. If a font file, a tool version or
the recipe below ever drifts, the proof fails and nothing is written.

The recipe, found by reproducing trophies' file rather than guessed:

  serif  Cinzel 700, the static instance Google Fonts serves (v26), with
         overlapping contours merged, which is what makes an `A` one outline
  num    Barlow Condensed Bold, from google/fonts
  meta   Barlow Condensed SemiBold, from google/fonts

Every coordinate is rounded half to even, Python's own `round`, and the path
is written by fontTools' SVGPathPen, whose compact syntax (a lineto after a
moveto drops its `L`) is the one `glyphs.json` uses.

This is a development tool, not part of the kit: it needs fontTools and
skia-pathops, which the kit never does.

  pip install fonttools skia-pathops
  python3 src/extract-glyphs.py            # fetch, prove, write
  python3 src/extract-glyphs.py --check    # prove, and fail if the file on disk differs
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import urllib.request
from pathlib import Path

FONTS = Path(__file__).resolve().parent / "fonts"
BASE = FONTS / "glyphs.json"
EXTRA = FONTS / "glyphs-extra.json"

# Pinned by content, so a font that changes upstream stops the run instead of
# quietly changing a letter.
SOURCES = {
    "serif": ("https://fonts.gstatic.com/s/cinzel/v26/8vIU7ww63mVu7gtR-kwKxNvkNOjw-jHgTYk.woff",
              "1bb7ec5b84ee97a9eae36528d5bae3bfeddf035c19842fc1740ce44c09fac4ad", True),
    "num": ("https://raw.githubusercontent.com/google/fonts/main/ofl/barlowcondensed/BarlowCondensed-Bold.ttf",
            "e476562ec9c1e16cf16475895b511f08c804f438cc9a9f80a44ea50a0eeb5b65", False),
    "meta": ("https://raw.githubusercontent.com/google/fonts/main/ofl/barlowcondensed/BarlowCondensed-SemiBold.ttf",
             "7b619d14bc2327509a9ef32b0890f709626f7ecc9ff61191c2a4314c5499d2d9", False),
}

# What every face gains: printable ASCII, and the typographic marks a line of
# prose reaches for. No dashes beyond the hyphen, on purpose: the standards
# ban the en and em dash in everything a repository writes, and a glyph that
# is not here cannot be drawn by accident. Arrows and hearts are absent from
# both fonts; the kit draws those with emblems' `arrow` and `heart` icons.
WANTED = "".join(chr(c) for c in range(32, 127)) + "©®™°•…‘’“”×·‹›«»"

# What the two Barlow faces gain beyond that: every letter of Latin-1 and
# Latin Extended-A, because a banner is filled from GitHub, and a name, a
# bio or a description arrives as its owner wrote it. A title that reads
# "Jos" for "Jos\u00e9" is a wrong title. Cinzel is left as it was: no design
# letters measured text in it.
LATIN = "".join(chr(c) for c in (*range(0xC0, 0x100), *range(0x100, 0x180)) if c not in (0xD7, 0xF7)) + "\u00a1\u00bf"
FACE_WANTS = {"serif": WANTED, "num": WANTED + LATIN, "meta": WANTED + LATIN}


def fetch(url: str, sha: str, cache: Path | None) -> bytes:
    local = cache / url.rsplit("/", 1)[-1] if cache else None
    if local and local.exists():
        data = local.read_bytes()
    else:
        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - pinned https sources
            data = response.read()
        if local:
            local.write_bytes(data)
    got = hashlib.sha256(data).hexdigest()
    if got != sha:
        raise SystemExit(f"{url}\n  sha256 {got}\n  wanted {sha}\nThe font changed upstream; nothing was written.")
    return data


def outlines(data: bytes, merge: bool):
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.ttLib import TTFont

    font = TTFont(io.BytesIO(data))
    if merge:
        from fontTools.ttLib.removeOverlaps import removeOverlaps

        removeOverlaps(font)
    glyphs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]

    def glyph(ch: str):
        name = cmap.get(ord(ch))
        if name is None:
            return None
        pen = SVGPathPen(glyphs, ntos=lambda v: str(round(v)))
        glyphs[name].draw(pen)
        return [pen.getCommands(), hmtx[name][0]]

    return glyph, font["head"].unitsPerEm


def build(cache: Path | None) -> dict:
    base = json.loads(BASE.read_text(encoding="utf-8"))
    extra: dict = {}
    for face, (url, sha, merge) in SOURCES.items():
        glyph, upem = outlines(fetch(url, sha, cache), merge)
        have = base[face]["g"]
        if upem != base[face]["upem"]:
            raise SystemExit(f"{face}: {upem} units per em, glyphs.json says {base[face]['upem']}")
        drift = [ch for ch, want in have.items() if glyph(ch) != want]
        if drift:
            raise SystemExit(f"{face}: {len(drift)} of {len(have)} glyphs no longer reproduce "
                             f"({''.join(drift[:12])}); nothing was written.")
        added, absent = {}, []
        for ch in FACE_WANTS[face]:
            if ch in have:
                continue
            got = glyph(ch)
            if got is None:
                absent.append(ch)
            else:
                added[ch] = got
        extra[face] = {"upem": upem, "cap": base[face]["cap"], "g": added}
        print(f"{face}: {len(have)} reproduced exactly, {len(added)} added"
              + (f", not in the font: {''.join(absent)!r}" if absent else ""), file=sys.stderr)
    return extra


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if glyphs-extra.json differs from a fresh extraction")
    ap.add_argument("--cache", type=Path, help="a directory to keep the downloaded fonts in")
    args = ap.parse_args(argv)
    if args.cache:
        args.cache.mkdir(parents=True, exist_ok=True)
    text = json.dumps(build(args.cache), ensure_ascii=False, separators=(",", ":")) + "\n"
    if args.check:
        if EXTRA.read_text(encoding="utf-8") != text:
            print("glyphs-extra.json is stale: run src/extract-glyphs.py", file=sys.stderr)
            return 1
        return 0
    EXTRA.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
