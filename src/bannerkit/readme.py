# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The README's two blocks: the header between `<!-- banners:header:start -->` and its end marker, the footer likewise.

The kit owns only what sits between the markers. The first run puts the
header block at the top of the README and the footer block at its foot;
every later run rewrites what is between them and nothing else, so the
README's own sections are never touched. A block whose design is set to
`none` is taken out again, markers and all.
"""
from __future__ import annotations

KINDS = ("header", "footer")


def markers(kind: str) -> tuple[str, str]:
    return f"<!-- banners:{kind}:start -->", f"<!-- banners:{kind}:end -->"


def block(kind: str, snippet: str) -> str:
    start, end = markers(kind)
    return f"{start}\n{snippet.rstrip()}\n{end}"


def current(text: str, kind: str) -> str | None:
    """The block of that kind as it stands in `text`, markers included, or None."""
    start, end = markers(kind)
    if start not in text or end not in text:
        return None
    a = text.index(start)
    b = text.index(end, a) + len(end)
    return text[a:b]


def place(text: str, blocks: dict) -> str:
    """`text` with each block written in place, placed on the first run, or taken out when it is no longer wanted."""
    for kind in KINDS:
        found = current(text, kind)
        wanted = blocks.get(kind)
        if found is not None and wanted is not None:
            text = text.replace(found, wanted, 1)
        elif found is not None:
            a = text.index(found)
            b = a + len(found)
            while b < len(text) and text[b] == "\n" and b - (a + len(found)) < 2:
                b += 1
            before, after = text[:a], text[b:]
            # A block at the foot takes the blank line above it along.
            text = before.rstrip("\n") + "\n" if not after.strip() and before.strip() else before + after
        elif wanted is not None:
            if kind == "header":
                text = wanted + "\n\n" + text.lstrip("\n") if text.strip() else wanted + "\n"
            else:
                text = text.rstrip("\n") + ("\n\n" if text.strip() else "") + wanted + "\n"
    return text


def apply(path, blocks: dict) -> bool:
    """Write the blocks into the README at `path`. Returns True if the file changed."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    new = place(text, blocks)
    if new == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    return True
