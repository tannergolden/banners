# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The lock: `.github/banners.lock.json`.

Every value on a banner is measured again on every run; the lock only
keeps `last`, the measurement the committed banners were drawn from. That
is what lets `check` redraw them offline and compare, byte for byte,
without a token and without the numbers moving underneath it. Deleting it
loses nothing but that.

It is written when a drawing changed, and once a week besides: a real
commit, which keeps GitHub from switching off the schedule after sixty
quiet days in a repository nobody is pushing to.
"""
from __future__ import annotations

import datetime as dt
import json

LAST_KEYS = ("mode", "subject", "today", "repository", "profile")
SNAPSHOT_DAYS = 7


def load(path) -> dict:
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    return {"version": 1, "last": None, "snapshot": None}


def save(path, lock: dict) -> bool:
    """Write the lock; returns True when the file changed."""
    text = json.dumps(lock, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def remember(lock: dict, measurement: dict) -> None:
    """Keep what `plan` needs to draw these banners again, and nothing that changes from run to run on its own."""
    lock["last"] = {k: measurement[k] for k in LAST_KEYS if k in measurement}


def last(lock: dict):
    """The measurement the committed banners were drawn from, or None."""
    return lock.get("last")


def snapshot_due(lock: dict, today: dt.date) -> bool:
    stamp = lock.get("snapshot")
    return stamp is None or (today - dt.date.fromisoformat(stamp)).days >= SNAPSHOT_DAYS


def mark_snapshot(lock: dict, today: dt.date) -> None:
    lock["snapshot"] = today.isoformat()
