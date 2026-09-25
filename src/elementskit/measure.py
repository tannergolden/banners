# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Measure a repository for its elements: from git for most, from GitHub for what only GitHub knows.

Each function returns the dict the matching element draws from, so a data
file names an element and leaves the numbers to this. What git cannot say,
a placard's description or whether CI passed, is read from the API with a
token, and everything measured is kept in the lock so `check` can redraw
without one.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import urllib.request
from collections import Counter
from pathlib import Path


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout


def when(d: dt.date, year: bool = False) -> str:
    return d.strftime("%d %b %Y" if year else "%d %b").lstrip("0").upper()


# --- from git -----------------------------------------------------------------------------------

KINDS = {"yml": "YAML", "yaml": "YAML", "md": "MARKDOWN", "py": "PYTHON", "sh": "SHELL", "rs": "RUST", "go": "GO",
         "ts": "TYPESCRIPT", "tsx": "TYPESCRIPT", "js": "JAVASCRIPT", "toml": "TOML", "json": "JSON",
         "html": "HTML", "css": "CSS", "svg": "SVG", "tf": "HCL"}


def tree(root: Path, ref: str = "HEAD", *, rooms: int = 6, closet: int = 3, hide: tuple = ()) -> dict:
    """The plan's rooms: the top-level folders by file count, the root as the lobby, small folders as closets."""
    files = git(root, "ls-tree", "-r", "--name-only", ref).split("\n")
    files = [f for f in files if f and not any(f == h or f.startswith(h + "/") for h in hide)]
    top: dict[str, list[str]] = {}
    lobby: list[str] = []
    for f in files:
        head, _, rest = f.partition("/")
        (top.setdefault(head, []) if rest else lobby).append(rest if rest else head)
    order = sorted(top, key=lambda k: (-len(top[k]), k))
    out_rooms, closets = [], []
    for k in order:
        members = top[k]
        if len(members) <= closet or len(out_rooms) >= rooms:
            closets.append({"label": k.upper() + "/", "count": len(members)})
            continue
        subs: Counter = Counter()
        loose: list[str] = []
        for m in members:
            h, _, r = m.partition("/")
            if r:
                subs[h + "/"] += 1
            else:
                loose.append(h)
        lines = [[name, str(n)] for name, n in sorted(subs.items(), key=lambda kv: (-kv[1], kv[0]))]
        lines += [[name, ""] for name in sorted(loose)]
        out_rooms.append({"key": re.sub(r"[^a-z0-9]+", "-", k.lower()).strip("-") or "room", "label": k.upper() + "/",
                          "count": len(members), "lines": lines})
    visible = sorted(f for f in lobby if not f.startswith("."))
    dots = [f for f in lobby if f.startswith(".")]
    return {"total": len(files), "rooms": out_rooms,
            "lobby": {"count": len(lobby), "lines": [[f, ""] for f in visible[:6]],
                      "far": ([f"+{len(dots)} DOTFILES"] if dots else []) + [f"+{len(visible) - 6} MORE"] * (len(visible) > 6)},
            "closets": closets}


def histogram(root: Path, ref: str = "HEAD", *, weeks: int = 10, today: dt.date | None = None) -> dict:
    """Commits per ISO week for the last `weeks`, ending with the week of `today`."""
    today = today or dt.date.today()
    counts = Counter(git(root, "log", ref, "--format=%ad", "--date=format:%G-%V").split())
    iso = today.isocalendar()
    first = dt.date.fromisocalendar(iso[0], iso[1], 1) - dt.timedelta(weeks=weeks - 1)
    bars = []
    for i in range(weeks):
        d = first + dt.timedelta(weeks=i)
        y, w, _ = d.isocalendar()
        bars.append([when(d), counts.get(f"{y}-{w:02d}", 0)])
    return {"label": "COMMITS PER WEEK", "sum": f"IN {weeks} WEEKS".replace("10", "TEN"), "bars": bars}


def materials(root: Path, ref: str = "HEAD", *, parts: int = 4) -> dict:
    """Tracked bytes by file type, the biggest kinds named and the rest as OTHER."""
    sizes: Counter = Counter()
    for row in git(root, "ls-tree", "-r", "-l", ref).splitlines():
        meta, name = row.split("\t", 1)
        size = int(meta.split()[3])
        base = name.rsplit("/", 1)[-1]
        ext = base.rsplit(".", 1)[-1].lower() if "." in base[1:] else ""
        sizes[KINDS.get(ext, "OTHER")] += size
    named = [(k, v) for k, v in sizes.most_common() if k != "OTHER"][:parts]
    other = sum(sizes.values()) - sum(v for _, v in named)
    total = sum(sizes.values())
    return {"label": "TRACKED BYTES BY FILE TYPE", "parts": [[k, v] for k, v in named] + [["OTHER", other]],
            "total": f"{total / 1e6:.1f} MB" if total >= 1e6 else f"{round(total / 1000)} KB"}


def days_since_release(root: Path, today: dt.date | None = None) -> dict | None:
    """The dial: days since the newest version tag, or None when there is no tag."""
    today = today or dt.date.today()
    rows = [r.split() for r in git(root, "tag", "--sort=-creatordate", "--format=%(refname:short) %(creatordate:short)").splitlines()]
    rows = [(t, d) for t, d in rows if re.fullmatch(r"v?\d+\.\d+\.\d+", t)]
    if not rows:
        return None
    tag, date = rows[0]
    days = (today - dt.date.fromisoformat(date)).days
    span = 30 if days <= 30 else 90 if days <= 90 else 365
    return {"label": "DAYS SINCE THE LAST RELEASE", "value": days, "span": span, "major": span // 3,
            "minor": max(1, span // 6), "sub": f"{tag.upper()}  ·  {when(dt.date.fromisoformat(date))}"}


def count(root: Path, ref: str, pattern: str) -> int:
    """Tracked files matching a glob, as a counter's value: `*` stays within one folder, `**` crosses them."""
    rx = "".join(".*" if part == "**" else "[^/]*" if part == "*" else re.escape(part)
                 for part in re.split(r"(\*\*|\*)", pattern))
    return sum(1 for f in git(root, "ls-tree", "-r", "--name-only", ref).split() if re.fullmatch(rx, f))


def roster(root: Path, ref: str = "HEAD", *, most: int = 4, bots: bool = True) -> dict:
    """Authors and co-authors by commit count, with each one's first and last."""
    rows = git(root, "log", ref, "--date=short",
               "--format=%ad|%an|%ae|%(trailers:key=Co-Authored-By,valueonly,separator=%x1f)").splitlines()
    people: dict[str, dict] = {}

    def seen(key: str, name: str, date: str, how: str):
        p = people.setdefault(key, {"name": name, "n": 0, "first": date, "last": date, "how": how})
        p["n"] += 1
        p["first"], p["last"] = min(p["first"], date), max(p["last"], date)

    for row in rows:
        date, name, email, trailers = row.split("|", 3)
        seen(email.lower(), name, date, "AUTHORED")
        for t in filter(None, trailers.split("\x1f")):
            m = re.match(r"\s*(.*?)\s*<([^>]+)>", t)
            if m:
                seen(m.group(2).lower(), m.group(1), date, "CO-AUTHORED")
    out = []
    for email, p in sorted(people.items(), key=lambda kv: -kv[1]["n"]):
        bot = "[bot]" in p["name"] or "[bot]" in email
        if bot and not bots:
            continue
        handle = re.sub(r"^\d+\+", "", email.split("@")[0]) if "users.noreply.github.com" in email else ""
        words = p["name"].replace("[bot]", "").split()
        entry = {"name": p["name"].upper(), "handle": f"@{handle.upper()}" if handle else p["how"], "n": p["n"],
                 "first": when(dt.date.fromisoformat(p["first"]), True),
                 "last": when(dt.date.fromisoformat(p["last"]))}
        if bot:
            entry["icon"] = "package"
        else:
            entry["initials"] = "".join(w[0] for w in words[:2]).upper()
        out.append(entry)
    total = len(rows)
    return {"caption": f"{total:,} COMMITS FROM {len(out)} CONTRIBUTORS", "people": out[:most]}


def milestones(root: Path, *, notable: dict | None = None, planned: list | None = None) -> dict:
    """Every version tag on the line: minors as dots, `notable` ones (tag: [notes]) as diamonds with their notes."""
    rows = [r.split() for r in git(root, "tag", "--sort=creatordate", "--format=%(refname:short) %(creatordate:short)").splitlines()]
    notable = notable or {}
    events = []
    for tag, date in rows:
        if not re.fullmatch(r"v?\d+\.\d+\.\d+", tag):
            continue
        major = tag.endswith(".0") or tag in notable
        e = {"date": date, "tag": tag.upper(), "major": major}
        if tag in notable:
            e["above"] = notable[tag]
        if tag.endswith(".0.0"):
            e["big"] = True
        events.append(e)
    for p in planned or []:
        events.append(dict(p, next=True))
    n = sum(1 for e in events if not e.get("next"))
    return {"caption": f"{n} RELEASES SINCE {when(dt.date.fromisoformat(rows[0][1]), True)}" if rows else "", "events": events}


def checks(root: Path, ref: str = "HEAD", *, ci: str | None = None, head: str | None = None) -> dict:
    """The conformance checks a checkout can answer, plus CI's verdict when the caller knows it."""
    files = set(git(root, "ls-tree", "-r", "--name-only", ref).split())
    uses = pinned = 0
    for f in files:
        if f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml")):
            for m in re.finditer(r"^\s*-?\s*uses:\s*([^\s#]+)", git(root, "show", f"{ref}:{f}"), re.M):
                uses += 1
                # A local path is the commit itself, and a docker image carries its own digest or tag.
                pinned += m.group(1).startswith(("./", "docker://")) or \
                    bool(re.search(r"@(v\d+(\.\d+)*|[0-9a-f]{40})$", m.group(1)))
    subjects = git(root, "log", ref, "--format=%s").splitlines()
    conv = sum(1 for s in subjects if re.match(r"^(feat|fix|docs|chore|ci|test|refactor|style|perf|build|revert)(\([^)]+\))?!?: ", s))
    lic = next((f for f in ("LICENSE", "LICENSE.md", "LICENSE.txt") if f in files), None)
    sec = next((f for f in ("SECURITY.md", ".github/SECURITY.md") if f in files), None)
    sha = head or git(root, "rev-parse", "--short", ref).strip()
    # Each row carries its own verdict, so the certificate marks a check that is not met as not met.
    out = []
    if ci:
        out.append([f"CI passes on {ci}", f"Checks at {sha}", True])
    out += [["Licensed", lic or "no LICENSE", bool(lic)], ["Security policy", sec or "none", bool(sec)],
            ["Actions pinned to a tag or a commit", f"{pinned} of {uses} uses:", pinned == uses],
            ["Conventional commits", f"{conv:,} of {len(subjects):,} subjects", conv == len(subjects)]]
    passed = all(row[2] for row in out)
    return {"commit": sha, "checks": out, "passed": passed}


# --- from GitHub ---------------------------------------------------------------------------------

def api(path: str, token: str) -> dict:
    """One GET against api.github.com, with the token the action was given."""
    req = urllib.request.Request(f"https://api.github.com{path}", headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "tannergolden-elements"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def placard(full: str, token: str) -> dict:
    """A repository's card: its description, language and latest release, from the API."""
    owner, name = full.split("/", 1)
    repo = api(f"/repos/{full}", token)
    try:
        release = api(f"/repos/{full}/releases/latest", token)["tag_name"]
    except Exception:
        release = "none"
    return {"owner": owner, "name": name, "desc": repo.get("description") or "", "link": repo["html_url"],
            "cells": [["Language", (repo.get("language") or "").upper()], ["Release", release.upper()],
                      ["Stars", f"{repo.get('stargazers_count', 0):,}"]]}


def ci_status(full: str, ref: str, token: str) -> str | None:
    """'passing' or 'failing' for the newest completed check suite on `ref`, or None when there is none."""
    runs = api(f"/repos/{full}/actions/runs?head_sha={ref}&per_page=20", token).get("workflow_runs", [])
    done = [r for r in runs if r.get("status") == "completed"]
    if not done:
        return None
    return "passing" if all(r.get("conclusion") == "success" for r in done) else "failing"
