#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Banner Kit: the command line the action runs, and the one you run locally.

  python3 src/banner-kit.py run --root . [--mode auto|profile|repository] [--subject octo-dev]
      measure over GitHub's API, draw, write the README blocks and the lock
  python3 src/banner-kit.py measure --mode ... --subject ... > measurement.json
      measure only, print the JSON
  python3 src/banner-kit.py render --root . [--from measurement.json]
      redraw a saved measurement (else the lock's, else the sample), no network
  python3 src/banner-kit.py check --root . [--from measurement.json]
      fail if the committed banners or README blocks differ from a fresh drawing, no network
  python3 src/banner-kit.py preview --root preview/repository [--mode repository|profile]
      draw the built-in sample measurement into a folder, for a look
  python3 src/banner-kit.py page --out preview/preview.html
      every design, drawn by the kit, in one self-contained page (make preview)
  python3 src/banner-kit.py lint
      draw every design for every sample in every print and lint every file (make lint)
  python3 src/banner-kit.py gallery [--check]
      draw the README's gallery into assets/gallery/, or fail if it is stale (make gallery)
  python3 src/banner-kit.py draw --out preview/files
      draw every design's files for the samples into a folder

Stdlib only. GITHUB_TOKEN (or BANNERS_TOKEN) is read from the environment
for anything that talks to GitHub; nothing else touches the network, and
`page` fetches only Brython, once, pinned by checksum.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bannerkit import config, lock, plan, readme, sample  # noqa: E402
from bannerkit.compose import CompositionError, compose  # noqa: E402
from bannerkit.content import Footer, Header  # noqa: E402
from bannerkit.designs import DESIGNS, check as lint_files, render  # noqa: E402
from bannerkit.drafting import PRINTS, RAINBOW, SPECTRUM  # noqa: E402

LOCK = Path(".github") / "banners.lock.json"
DRAWN = re.compile(r"^(header|footer|link)-[a-z0-9-]+\.svg$")


def _today(args) -> str:
    return args.today or dt.datetime.now(dt.timezone.utc).date().isoformat()


def _cfg(args) -> dict:
    root = Path(args.root)
    cfg = config.load(root / (args.config or ".github/banners.yml"))
    for key in ("mode", "subject", "header", "footer", "theme", "out"):
        v = getattr(args, key, None)
        if v:
            cfg[key] = v
    return config.validate(cfg)


def _write(root: Path, p: dict) -> list[str]:
    """Write the planned files that differ, and remove drawn files the plan no longer has. Returns what changed."""
    changed = []
    for rel, svg in p["files"].items():
        path = root / rel
        if not path.exists() or path.read_text(encoding="utf-8") != svg:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(svg, encoding="utf-8")
            changed.append(rel)
    out = root / p["out"]
    if out.is_dir():
        for path in sorted(out.iterdir()):
            rel = (Path(p["out"]) / path.name).as_posix()
            if DRAWN.match(path.name) and rel not in p["files"]:
                path.unlink()
                changed.append(rel)
    return changed


def _stale(root: Path, p: dict, cfg: dict) -> list[str]:
    """Every way the committed banners differ from a fresh drawing of the same measurement."""
    stale = []
    for rel, svg in p["files"].items():
        path = root / rel
        if not path.exists():
            stale.append(f"{rel} (missing)")
        elif path.read_text(encoding="utf-8") != svg:
            stale.append(f"{rel} (differs)")
    out = root / p["out"]
    if out.is_dir():
        for path in sorted(out.iterdir()):
            rel = (Path(p["out"]) / path.name).as_posix()
            if DRAWN.match(path.name) and rel not in p["files"]:
                stale.append(f"{rel} (no longer drawn)")
    if cfg["readme"] == "manage":
        path = root / cfg["readme_path"]
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for kind in readme.KINDS:
            found, wanted = readme.current(text, kind), p["blocks"].get(kind)
            if wanted is not None and found is None:
                stale.append(f"{cfg['readme_path']} ({kind} markers missing)")
            elif wanted is not None and found != wanted:
                stale.append(f"{cfg['readme_path']} ({kind} block differs)")
            elif wanted is None and found is not None:
                stale.append(f"{cfg['readme_path']} ({kind} block no longer drawn)")
    return stale


def _rainbow(cfg: dict, state: dict) -> str | None:
    """The print a rainbowprint is drawn in now: the lock's, else the first colour. None for any other theme."""
    if cfg["theme"] != RAINBOW:
        return None
    current = state.get("rainbow")
    return current if current in SPECTRUM else SPECTRUM[0]


def _drawn(cfg: dict, shade: str | None) -> dict:
    """The config with a rainbowprint resolved to the print it is drawn in."""
    return dict(cfg, theme=shade) if shade else cfg


def _before(lk: dict | None, cfg: dict):
    """What the committed banners showed, for the commit message to compare with; None on a first run."""
    last = lock.last(lk) if lk else None
    if not last:
        return None
    try:
        return plan.facts(plan.plan(last, cfg))
    except (CompositionError, KeyError, TypeError):
        return None


def finish(m: dict, cfg: dict, root: Path, *, use_lock: bool, commit_file: str = "", advance: bool = False) -> int:
    lock_path = root / LOCK
    state = lock.load(lock_path)
    lk = state if (use_lock and cfg["lock"]) else None
    shade = _rainbow(cfg, state)
    before = _before(lk, _drawn(cfg, shade))
    p = plan.plan(m, _drawn(cfg, shade))
    if shade and advance and state.get("rainbow") in SPECTRUM and _stale(root, p, cfg):
        # An update: rainbowprint draws each one in the next colour of the spectrum.
        shade = SPECTRUM[(SPECTRUM.index(shade) + 1) % len(SPECTRUM)]
        p = plan.plan(m, _drawn(cfg, shade))
    print(plan.describe(p))
    for note in p["notes"]:
        print(f"note: {note}")
    changed = _write(root, p)
    if cfg["readme"] == "manage" and readme.apply(root / cfg["readme_path"], p["blocks"]):
        changed.append(cfg["readme_path"])
    if lk is not None:
        # A quiet day writes nothing. The lock is rewritten when a drawing
        # changed, and once a week besides, which keeps the schedule alive.
        today = dt.date.fromisoformat(m["today"])
        due = lock.snapshot_due(lk, today)
        if changed or due or not lock_path.exists():
            lock.remember(lk, m)
            if shade:
                lk["rainbow"] = shade
            if due:
                lock.mark_snapshot(lk, today)
            if lock.save(lock_path, lk):
                changed.append(LOCK.as_posix())
    print(f"{len(changed)} files changed" if changed else "nothing changed")
    if commit_file and changed:
        msg = plan.commit_message(p, before, changed, os.environ.get("GITHUB_RUN_ID", ""), rainbow=bool(shade))
        Path(commit_file).write_text(msg, encoding="utf-8")
        print(msg.splitlines()[0])
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### Banners\n\n{plan.describe(p)}\n\n{len(changed)} files changed\n")
            for note in p["notes"]:
                fh.write(f"\n- {note}")
            fh.write("\n")
    return 0


def _measure(args, cfg: dict) -> dict:
    from bannerkit import measure
    from bannerkit.github import GitHub

    return measure.measure(GitHub(), cfg["mode"], cfg["subject"], os.environ.get("GITHUB_REPOSITORY", ""),
                           today=_today(args))


def cmd_run(args) -> int:
    cfg = _cfg(args)
    m = _measure(args, cfg)
    if args.save:
        Path(args.save).write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return finish(m, cfg, Path(args.root), use_lock=True, commit_file=args.commit_file, advance=True)


def cmd_measure(args) -> int:
    print(json.dumps(_measure(args, _cfg(args)), indent=1, ensure_ascii=False))
    return 0


def _sample(cfg: dict) -> dict:
    mode = "profile" if cfg["mode"] == "profile" else "repository"
    return json.loads(json.dumps(sample.SAMPLES[mode]))


def _remembered(args, cfg: dict, root: Path):
    """A measurement: the file named, else the lock's."""
    if args.source:
        return json.loads(Path(args.source).read_text(encoding="utf-8"))
    path = root / LOCK
    return lock.last(lock.load(path)) if path.exists() else None


def cmd_render(args) -> int:
    root = Path(args.root)
    cfg = _cfg(args)
    m = _remembered(args, cfg, root) or _sample(cfg)
    return finish(m, cfg, root, use_lock=False)


def cmd_check(args) -> int:
    """Are the committed banners what the kit draws from the measurement they were drawn from?

    Reads the lock's remembered measurement (or --from), replans, and
    compares with the files on disk and the README blocks. No token, no
    network, and the numbers cannot move underneath it: a stale result
    means a hand-edited file, a missing one, a block that drifted, or a
    config changed without a run."""
    root = Path(args.root)
    cfg = _cfg(args)
    m = _remembered(args, cfg, root)
    if m is None:
        print("check needs a measurement: run the kit once with the lock on, or pass --from m.json")
        return 2
    p = plan.plan(m, _drawn(cfg, _rainbow(cfg, lock.load(root / LOCK))))
    stale = _stale(root, p, cfg)
    if stale:
        print("stale: " + ", ".join(stale))
        return 1
    print(f"{len(p['files'])} files and the README blocks current")
    return 0


def cmd_preview(args) -> int:
    """The sample measurement, drawn into a folder the way a run would, and remembered so the folder checks."""
    root = Path(args.root)
    cfg = _cfg(args)
    m = _sample(cfg)
    if args.today:
        m["today"] = args.today
    code = finish(m, cfg, root, use_lock=False)
    lk = {"version": 1, "last": None, "snapshot": None}
    lock.remember(lk, m)
    if cfg["theme"] == RAINBOW:
        lk["rainbow"] = SPECTRUM[0]
    lock.save(root / LOCK, lk)
    return code


def cmd_page(args) -> int:
    from bannerkit import preview

    emblems = Path(args.emblems_kit) if args.emblems_kit else None
    stats = preview.build(Path(args.out), Path(args.cache), emblems)
    print(f"{args.out}: {stats['bytes'] / 1e6:.2f} MB, {stats['files']} pre-rendered files in {stats['sets']} sets")
    return 0


def contents() -> dict:
    """Every content the kit is linted with: each sample, composed, and the kit's own lines."""
    out = {"kit": (Header(), Footer())}
    for key, m in sample.SAMPLES.items():
        h, f, _ = compose(m, config.validate({}))
        out[key] = (h, f)
    return out


def cmd_lint(args) -> int:
    failed = 0
    for name, (h, f) in contents().items():
        for code, design in DESIGNS.items():
            largest, problems = 0, {}
            for tone in PRINTS:
                content = (h if design.kind == "header" else f).with_(tone=tone)
                files = render(design, content)
                problems.update(lint_files(design, files))
                largest = max(largest, *(len(svg.encode("utf-8")) for svg in files.values()))
            print(f"{name:<10} {code} {design.name:<12} {len(PRINTS)} prints, largest {largest / 1000:.1f} KB"
                  + ("" if not problems else f"  PROBLEMS: {problems}"))
            failed += bool(problems)
    return 1 if failed else 0


# The README's gallery: every design once, a profile once, and every theme
# once, each a real file the kit draws from a sample measurement. `gallery`
# writes them; `gallery --check` fails when one is stale, which `make check`
# runs, so the README can never show a drawing the kit no longer makes.
GALLERY = [
    ("h1-sheet", "H1", "repository", {"header": "sheet"}),
    ("h2-section", "H2", "repository", {}),
    ("h3-strip", "H3", "repository", {"header": "strip"}),
    ("h2-profile", "H2", "profile", {}),
    ("f1-title-block", "F1", "repository", {"closing": "Drawn at both ends. Fetched at neither."}),
    ("f2-scale-bar", "F2", "repository", {"closing": "Drawn at both ends. Fetched at neither."}),
]
GALLERY_OUT = "assets/gallery"


def gallery_files() -> dict[str, str]:
    """Every gallery file by name. A design is drawn by day and by night; a theme, as its night sheet only."""
    out = {}
    for name, code, subject, given in GALLERY:
        h, f, _ = compose(sample.SAMPLES[subject], config.validate(given))
        files = render(DESIGNS[code], h if DESIGNS[code].kind == "header" else f, {"day", "dark"})
        for file, svg in files.items():
            out[f"{name}-{file.rsplit('-', 1)[1]}"] = svg
    for tone in PRINTS:
        _, f, _ = compose(sample.REPOSITORY, config.validate({"theme": tone, "closing": f"theme: {tone}"}))
        out[f"theme-{tone}.svg"] = render(DESIGNS["F2"], f, {"dark"})["footer-dark.svg"]
    return out


def cmd_gallery(args) -> int:
    root = Path(args.root)
    out = root / GALLERY_OUT
    files = gallery_files()
    stale = [n for n, svg in files.items() if not (out / n).exists() or (out / n).read_text(encoding="utf-8") != svg]
    extra = sorted(p.name for p in out.glob("*.svg") if p.name not in files) if out.is_dir() else []
    if args.check:
        if stale or extra:
            print(f"{GALLERY_OUT} is stale ({', '.join(stale + extra)}): run make gallery")
            return 1
        print(f"{len(files)} gallery files current")
        return 0
    out.mkdir(parents=True, exist_ok=True)
    for name in stale:
        (out / name).write_text(files[name], encoding="utf-8")
    for name in extra:
        (out / name).unlink()
    print(f"{GALLERY_OUT}: {len(stale)} drawn, {len(extra)} removed, {len(files)} in all")
    return 0


def cmd_draw(args) -> int:
    out = Path(args.out)
    for name, (h, f) in contents().items():
        for code, design in DESIGNS.items():
            folder = out / name / f"{code}-{design.slug}"
            folder.mkdir(parents=True, exist_ok=True)
            for file, svg in render(design, h if design.kind == "header" else f).items():
                (folder / file).write_text(svg, encoding="utf-8")
    print(f"drew every design into {out}/")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="banner-kit", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--root", default=".", help="repository root (default: .)")
        sp.add_argument("--config", default="", help="config path relative to root (default: .github/banners.yml)")
        sp.add_argument("--mode", choices=sorted(config.CHOICES["mode"]))
        sp.add_argument("--subject", default="", help="a login, or owner/name in repository mode")
        sp.add_argument("--header", choices=sorted(config.CHOICES["header"]))
        sp.add_argument("--footer", choices=sorted(c for c in config.CHOICES["footer"] if c))
        sp.add_argument("--theme", choices=[*PRINTS, RAINBOW])
        sp.add_argument("--out", default="")
        sp.add_argument("--today", default="", help="YYYY-MM-DD, for reproducible runs")

    sp = sub.add_parser("run", help="measure, draw, write")
    common(sp)
    sp.add_argument("--save", default="", help="also save the measurement JSON here")
    sp.add_argument("--commit-file", default="", help="write a Conventional Commit message here when something changed")
    common(sub.add_parser("measure", help="measure only, print JSON"))
    sp = sub.add_parser("render", help="redraw a saved measurement")
    common(sp)
    sp.add_argument("--from", dest="source", default="", help="measurement JSON (default: the lock's, else the sample)")
    sp = sub.add_parser("check", help="verify the committed banners against their measurement")
    common(sp)
    sp.add_argument("--from", dest="source", default="")
    common(sub.add_parser("preview", help="draw the sample measurement into a folder"))
    sp = sub.add_parser("page", help="build the preview page")
    sp.add_argument("--out", default="preview/preview.html")
    sp.add_argument("--cache", default=".cache")
    sp.add_argument("--emblems-kit", default="", help="emblems' src/badge-kit.py, to draw the mock README's badges")
    sub.add_parser("lint", help="draw and lint every design")
    sp = sub.add_parser("gallery", help="draw the README's gallery into assets/gallery/")
    sp.add_argument("--root", default=".")
    sp.add_argument("--check", action="store_true", help="fail if a committed gallery file is stale, write nothing")
    sp = sub.add_parser("draw", help="draw every design's files into a folder")
    sp.add_argument("--out", default="preview/files")
    args = ap.parse_args(argv)
    commands = {"run": cmd_run, "measure": cmd_measure, "render": cmd_render, "check": cmd_check,
                "preview": cmd_preview, "page": cmd_page, "lint": cmd_lint, "gallery": cmd_gallery,
                "draw": cmd_draw}
    try:
        return commands[args.cmd](args)
    except (config.ConfigError, CompositionError) as exc:
        print(f"::error::{exc}" if os.environ.get("GITHUB_ACTIONS") else f"config: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
