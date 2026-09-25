#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Blueprint elements a README draws for itself: the kit's command line.

    python3 src/elements-kit.py measure    # measure the repository into .github/elements.lock.json
    python3 src/elements-kit.py render     # draw every element into assets/elements/ and fill the README's blocks
    python3 src/elements-kit.py check      # fail when a file or a block has drifted from the data
    python3 src/elements-kit.py snippets   # print each element's block, to paste where it should go

A README names where an element goes with a pair of markers,
`<!-- elements:ID:start -->` and its end; `render` writes the <picture>
between them and touches nothing else. An element the README has no
markers for is drawn and reported, so nothing is silently skipped.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from elementskit import elements as E  # noqa: E402
from elementskit import measure as M  # noqa: E402

_STAMP = re.compile(r"<!--banner-kit v\w+ elements v(\w+) ")


def workspace() -> Path:
    ws = os.environ.get("GITHUB_WORKSPACE", "")
    return Path(ws) if ws and Path(ws).is_dir() else Path.cwd()


# --- the data file and the lock ------------------------------------------------------------------

def load_data(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore
    except ImportError as e:
        raise SystemExit(f"{path.name} is YAML and PyYAML is not installed; write elements.json instead") from e
    return yaml.safe_load(text) or {}


def load_lock(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"measured": {}}


REQUIRED = {
    "schematic": ("boxes", "wires"), "instruments": ("histogram", "dial", "materials", "counters"),
    "plan": ("rooms",), "milestones": ("events",), "roster": ("people",), "certificate": ("checks", "ring_top", "ring_bottom", "name"),
    "placard": ("owner", "name", "desc", "cells"), "seal": ("ring_top", "ring_bottom", "name"),
}


def validate(data: dict, lock: dict) -> list[str]:
    """What the data file gets wrong, said precisely: an unknown kind, a field an element cannot draw without,
    a wire to a box that is not there, an id that is not a file name."""
    errors = []
    if not isinstance(data.get("elements"), dict) or not data["elements"]:
        return ["no `elements:` map in the data file"]
    if data.get("print", "blueprint") not in E.PRINTS:
        errors.append(f"unknown print {data.get('print')!r} (one of {', '.join(E.PRINTS)})")
    for eid, d in merged(data, lock).items():
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", eid):
            errors.append(f"{eid}: an element's id must be kebab-case")
        kind = d.get("kind")
        if kind not in E.KINDS:
            errors.append(f"{eid}: unknown kind {kind!r} (one of {', '.join(E.KINDS)})")
            continue
        missing = [f for f in REQUIRED[kind] if f not in d]
        if missing:
            hint = " (run `elements-kit.py measure` first)" if "measure" in data["elements"][eid] else ""
            errors.append(f"{eid}: a {kind} needs {', '.join(missing)}{hint}")
            continue
        if kind == "schematic":
            for w in d["wires"]:
                for k in w[:2]:
                    if k not in d["boxes"]:
                        errors.append(f"{eid}: wire {w[0]} -> {w[1]} names a box that is not there: {k}")
            for k, box in d["boxes"].items():
                if box.get("icon") and box["icon"] not in E.ICONS:
                    errors.append(f"{eid}: box {k} names an icon that is not in the set: {box['icon']}")
        if kind == "placard" and d.get("icon") and d["icon"] not in E.ICONS:
            errors.append(f"{eid}: icon {d['icon']!r} is not in the set")
        if kind == "roster" and any(p.get("icon") and p["icon"] not in E.ICONS for p in d["people"]):
            errors.append(f"{eid}: a person names an icon that is not in the set")
    return errors


def merged(data: dict, lock: dict) -> dict:
    """Each element's data: what the file says, filled in with what was measured for it."""
    out = {}
    for eid, spec in data["elements"].items():
        d = dict(lock["measured"].get(eid, {}))
        own = {k: v for k, v in spec.items() if k != "measure"}
        if spec.get("kind") == "plan" and "rooms" in d and "rooms" in own:
            # A room the file names by key adds to the measured one (a note, a label) rather than replacing
            # the plan; a room the file describes in full, with its count, is added beside the measured ones.
            rooms = [dict(r) for r in d["rooms"]]
            by = {r.get("key"): r for r in rooms}
            for r in own.pop("rooms"):
                if r.get("key") in by:
                    by[r["key"]].update(r)
                elif "count" in r:
                    rooms.append(dict(r))
            d["rooms"] = rooms
        d.update(own)
        d.setdefault("subject", data.get("subject", ""))
        if data.get("today"):
            d.setdefault("today", str(data["today"]))
        out[eid] = d
    return out


def run_measure(root: Path, data: dict, lock: dict, token: str | None) -> dict:
    """Fill each element's `measure:` request from git, and from GitHub where a token allows."""
    today = dt.date.fromisoformat(str(data["today"])) if data.get("today") else dt.date.today()
    ref = data.get("ref", "HEAD")
    subject = data.get("subject", "")
    for eid, spec in data["elements"].items():
        req = spec.get("measure")
        if req is None:
            continue   # `measure: {}` asks for the defaults; no key at all asks for nothing
        kind, out = spec["kind"], {}
        if kind == "plan":
            out = M.tree(root, ref, hide=tuple(req.get("hide", ())) if isinstance(req, dict) else ())
        elif kind == "instruments":
            req = req if isinstance(req, dict) else {}
            out["histogram"] = M.histogram(root, ref, weeks=req.get("weeks", 10), today=today)
            out["materials"] = M.materials(root, ref)
            out["dial"] = M.days_since_release(root, today) or {"label": "DAYS SINCE THE LAST RELEASE", "value": 0,
                                                                  "span": 30, "sub": "NO RELEASE YET"}
            out["counters"] = [[k.upper(), M.count(root, ref, v)] for k, v in req.get("count", {}).items()][:3]
            out["caption"] = f"MEASURED {M.when(today, True)}"
        elif kind == "roster":
            req = req if isinstance(req, dict) else {}
            out = M.roster(root, ref, most=req.get("most", 4), bots=req.get("bots", True))
            for p in out["people"]:
                for match, fields in req.get("rename", {}).items():
                    if match.upper() in p["name"]:
                        p.update({k: str(v) for k, v in fields.items()})
        elif kind == "milestones":
            req = req if isinstance(req, dict) else {}
            out = M.milestones(root, notable=req.get("notable"), planned=req.get("planned"))
            out["today"] = str(today)
        elif kind == "certificate":
            req = req if isinstance(req, dict) else {}
            ci = req.get("ci")
            if ci and token and subject:
                status = M.ci_status(subject, ref, token)
                ci = ci if status == "passing" else None
            out = M.checks(root, ref, ci=ci)
            out.pop("passed", None)
        elif kind == "placard":
            full = req if isinstance(req, str) else req.get("repo", "")
            if token and full:
                out = M.placard(full, token)
            elif full not in ("", None) and eid not in lock["measured"]:
                print(f"::warning::{eid}: a placard needs a token to read {full}; drawn from the data file only")
        if out:
            lock["measured"][eid] = out
    lock["today"] = str(today)
    return lock


# --- files and blocks ----------------------------------------------------------------------------

def file_name(eid: str, variant: str, theme: str) -> str:
    v = "" if variant in ("wide", "half") else f"-{variant}"
    return f"{eid}{v}-{theme}.svg"


def render_all(data: dict, lock: dict) -> dict[str, str]:
    """{basename: svg} for every element, every variant, both themes."""
    tone = data.get("print", "blueprint")
    files = {}
    for eid, d in merged(data, lock).items():
        kind = d["kind"]
        for variant in E.variants(kind, d):
            for theme in ("day", "dark"):
                files[file_name(eid, variant, theme)] = E.draw(kind, d, tone, theme, variant)
    return files


def block(eid: str, d: dict, rel: str) -> str:
    """The <picture> a README embeds: the phone's file, the still one for no motion, the dark one, then the day one."""
    kind = d["kind"]
    vs = E.variants(kind, d)
    src = lambda v, t: f"{rel}/{file_name(eid, v, t)}"
    lines = ["<picture>"]
    if "narrow" in vs:
        lines.append(f'  <source media="(max-width: 585px) and (prefers-color-scheme: dark)" srcset="{src("narrow", "dark")}">')
        lines.append(f'  <source media="(max-width: 585px)" srcset="{src("narrow", "day")}">')
    if "still" in vs:
        lines.append(f'  <source media="(prefers-reduced-motion: reduce) and (prefers-color-scheme: dark)" srcset="{src("still", "dark")}">')
        lines.append(f'  <source media="(prefers-reduced-motion: reduce)" srcset="{src("still", "day")}">')
    main = "half" if "half" in vs else "wide"
    lines.append(f'  <source media="(prefers-color-scheme: dark)" srcset="{src(main, "dark")}">')
    lines.append(f'  <img alt="{escape(E.alt(kind, d))}" src="{src(main, "day")}">')
    lines.append("</picture>")
    pic = "\n".join(lines)
    if d.get("link"):
        pic = f'<a href="{escape(str(d["link"]))}">\n{pic}\n</a>'
    return f"<!-- elements:{eid}:start -->\n{pic}\n<!-- elements:{eid}:end -->"


def place(text: str, blocks: dict[str, str]) -> tuple[str, list[str]]:
    """Write each block between its markers. Returns the new text and the ids the README has no markers for."""
    missing = []
    for eid, wanted in blocks.items():
        start, end = f"<!-- elements:{eid}:start -->", f"<!-- elements:{eid}:end -->"
        if start in text and end in text:
            a = text.index(start)
            b = text.index(end, a) + len(end)
            text = text[:a] + wanted + text[b:]
        else:
            missing.append(eid)
    return text, missing


# --- init -----------------------------------------------------------------------------------------

STARTER = """\
# The blueprint elements this README draws for itself.
#
#   elements-kit.py measure   reads git (and GitHub, given a token) into .github/elements.lock.json
#   elements-kit.py render    draws every element into assets/elements/ and writes each one's
#                    <picture> between its markers in README.md
#   elements-kit.py check     fails CI when a file or a block has drifted from this data
#
# Anything you write here wins over what was measured, so give any element a
# `title:`, a `caption:` or a `desc:` of your own. `measure: {{}}` asks for the
# defaults; leave `measure:` out to draw an element from this file alone.

print: {print}
subject: {subject}

elements:
  vitals:
    kind: instruments
    measure:
      count: {{tests: "tests/**", workflows: ".github/workflows/*"}}

  layout:
    kind: plan
    measure: {{}}

  history:
    kind: milestones
    measure:
      # tag: [a note or two] calls a release out with a diamond; the rest are dots.
      notable: {{}}

  contributors:
    kind: roster
    size: half
    measure: {{}}

  conformance:
    kind: certificate
    size: half
    name: {name}
    ring_top: {ring_top}
    ring_bottom: MEASURED FROM THE CHECKOUT
    measure: {{}}

  # A schematic and a placard are written by hand. The driftmark specimen in the
  # kit shows every field each one takes.
"""


def origin(root: Path) -> str:
    """owner/name from the checkout's origin, or '' when there is none."""
    try:
        url = M.git(root, "config", "--get", "remote.origin.url").strip()
    except Exception:
        return ""
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else ""


def init(root: Path, data_path: Path, readme: Path) -> int:
    """A starter data file and the README's markers, so the first `measure` and `render` have somewhere to go."""
    subject = origin(root) or "owner/name"
    name = subject.split("/")[-1]
    if data_path.exists():
        print(f"{data_path.name} is already there; leaving it as it is.")
    else:
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_text(STARTER.format(print="blueprint", subject=subject, name=name.upper(),
                                            ring_top=f"{name.upper()}  ·  CONFORMANCE"), encoding="utf-8")
        print(f"Wrote {data_path.relative_to(root) if data_path.is_relative_to(root) else data_path}.")
    data = load_data(data_path)
    text = readme.read_text(encoding="utf-8") if readme.exists() else f"# {name}\n"
    missing = [eid for eid in data["elements"] if f"<!-- elements:{eid}:start -->" not in text]
    if missing:
        blocks = "\n\n".join(f"<!-- elements:{eid}:start -->\n<!-- elements:{eid}:end -->" for eid in missing)
        text = text.rstrip("\n") + ("\n\n" if text.strip() else "") + \
            "<!-- Each pair of markers below is where one element is drawn. Move a pair anywhere in the page. -->\n" \
            + blocks + "\n"
        readme.write_text(text, encoding="utf-8")
        print(f"Added markers to {readme.name} for: {', '.join(missing)}.")
    else:
        print(f"{readme.name} already has every marker.")
    print("Next: `elements-kit.py measure`, then `elements-kit.py render`, then commit what they wrote.")
    return 0


# --- the command line -----------------------------------------------------------------------------

GITMOJI = "\U0001F4D0"   # the triangular ruler: chore(elements) commits carry it, as banners carry the placard


def _series(items: list[str]) -> str:
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1] if items else ""


def commit_message(subject: str, today: str, *, first: bool, drawn: list[str], pruned: list[str],
                   blocks: int, readme: str) -> str:
    """A Conventional Commit for a run: what was drawn, for whom, and why the files are committed."""
    import textwrap
    head = f"chore(elements): {GITMOJI} "
    who = subject or "this repository"
    if first:
        title = head + f"draw the elements for {who}"
    else:
        title = head + "redraw " + _series(drawn)
        if len(title) > 72:
            title = head + f"redraw {len(drawn)} elements for {who}"
    lines = [f"Measured {who} on {today}."]
    if first:
        lines.append(f"The first run: the data file, the markers in {readme} and every file are new.")
    elif drawn:
        lines.append(f"Redrawn: {_series(drawn)}.")
    if blocks:
        lines.append(f"{blocks} block{'s' if blocks != 1 else ''} rewritten in {readme}.")
    if pruned:
        lines.append(f"Pruned {_series(pruned)}: no element writes them now.")
    body = textwrap.fill(" ".join(lines), 72)
    why = textwrap.fill("The elements are committed SVGs, so the page renders them with no request at view time. "
                        "This refresh is the kit's own commit and counts as a chore.", 72)
    return f"{title}\n\n{body}\n\n{why}\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="The body of a README, drawn for itself.")
    ap.add_argument("command", choices=("run", "init", "measure", "render", "check", "snippets"),
                    help="run is init (when there is no data file), measure and render, in one")
    ap.add_argument("--root", type=Path, default=None)
    ap.add_argument("--data", type=Path, default=None, help="default .github/elements.yml (or .json)")
    ap.add_argument("--out", type=Path, default=None, help="default assets/elements")
    ap.add_argument("--readme", type=Path, default=None, help="default README.md")
    ap.add_argument("--lock", type=Path, default=None, help="default .github/elements.lock.json")
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN") or None)
    ap.add_argument("--commit-file", type=Path, default=None,
                    help="run only: where the commit message for what changed is written; absent when nothing did")
    args = ap.parse_args(argv)
    root = (args.root or workspace()).resolve()
    data_path = args.data or next((root / ".github" / n for n in ("elements.yml", "elements.yaml", "elements.json")
                                   if (root / ".github" / n).exists()), root / ".github" / "elements.yml")
    out = args.out or root / "assets" / "elements"
    readme = args.readme or root / "README.md"
    lock_path = args.lock or root / ".github" / "elements.lock.json"
    if args.command == "init":
        return init(root, data_path, readme)
    bootstrapped = False
    if args.command == "run" and not data_path.exists():
        init(root, data_path, readme)
        bootstrapped = True
    if not data_path.exists():
        print(f"::error::no {data_path.relative_to(root) if data_path.is_relative_to(root) else data_path}")
        return 1
    data = load_data(data_path)
    lock = load_lock(lock_path)
    lock_before = json.loads(json.dumps(lock))

    if args.command in ("measure", "run"):
        lock = run_measure(root, data, lock, args.token)
        if args.command == "measure":
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text(json.dumps(lock, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Measured {len(lock['measured'])} element(s) into {lock_path.name}.")
            return 0

    problems = validate(data, lock)
    if problems:
        for e in problems:
            print(f"::error::{data_path.name}: {e}", file=sys.stderr)
        return 1
    E.WARNINGS.clear()
    files = render_all(data, lock)
    for w in sorted(set(E.WARNINGS)):
        print(f"::warning::{w}; drawn as '?'")
    try:
        rel = out.resolve().relative_to(readme.resolve().parent).as_posix()
    except ValueError:
        rel = out.as_posix()
    elements = merged(data, lock)
    blocks = {eid: block(eid, d, rel) for eid, d in elements.items()}
    owner = {file_name(eid, v, t): eid for eid, d in elements.items() for v in E.variants(d["kind"], d) for t in ("day", "dark")}

    if args.command == "snippets":
        for b in blocks.values():
            print(b + "\n")
        return 0

    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    new_text, missing = place(text, blocks)
    on_disk = {p.name for p in out.glob("*.svg")} if out.is_dir() else set()
    orphans = sorted(on_disk - set(files))

    if args.command == "check":
        stale, regen = [], []
        for name, svg in files.items():
            current = (out / name).read_text(encoding="utf-8") if (out / name).exists() else ""
            if current == svg:
                continue
            m = _STAMP.search(current)
            (regen if current and m and m.group(1) != E.KIT_VERSION else stale).append(name)
        stale += [f"{o} (orphaned)" for o in orphans]
        if new_text != text:
            stale.append(f"{readme.name} blocks")
        if stale:
            print(f"::error::{len(stale)} out of date: {', '.join(stale)}. Run 'elements-kit.py render'.", file=sys.stderr)
            return 1
        if regen:
            print(f"::notice::{len(regen)} file(s) drawn by another kit version; the next render re-stamps them.")
        if missing:
            print(f"::notice::no markers in {readme.name} for: {', '.join(missing)}")
        print(f"Elements check passed: {len(files)} file(s) and {readme.name} are current.")
        return 0

    first = not on_disk
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, svg in files.items():
        if not (out / name).exists() or (out / name).read_text(encoding="utf-8") != svg:
            (out / name).write_text(svg, encoding="utf-8")
            written.append(name)
    for o in orphans:
        (out / o).unlink()
        print(f"Pruned {o} (no element writes it).")
    if new_text != text:
        readme.write_text(new_text, encoding="utf-8")
    rewritten = sum(1 for eid, b in blocks.items() if eid not in missing and b not in text)
    if missing:
        print(f"::notice::{readme.name} has no markers for: {', '.join(missing)}. 'elements-kit.py snippets' prints them.")
    print(f"Rendered {len(files)} file(s) into {out.relative_to(root) if out.is_relative_to(root) else out} "
          f"and wrote {len(blocks) - len(missing)} block(s) in {readme.name}.")

    if args.command == "run":
        # A day on which nothing moved writes nothing: the lock keeps its date, and no message is left.
        moved = {k: v for k, v in lock.items() if k != "today"} != {k: v for k, v in lock_before.items() if k != "today"}
        changed = bool(written or orphans or new_text != text or moved or bootstrapped)
        if changed or not lock_path.exists():
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text(json.dumps(lock, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        if args.commit_file:
            if changed:
                drawn = sorted({owner[n] for n in written}, key=list(elements).index)
                args.commit_file.write_text(commit_message(
                    data.get("subject", ""), lock.get("today", ""), first=first or bootstrapped, drawn=drawn,
                    pruned=orphans, blocks=rewritten, readme=readme.name), encoding="utf-8")
            elif args.commit_file.exists():
                args.commit_file.unlink()
        print("Something moved; a commit is due." if changed else "Nothing moved since the last run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
