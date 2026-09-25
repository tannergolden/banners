# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""`.github/banners.yml`: the consumer's choices, with defaults for all of them.

An empty text field means "read it from GitHub": the title is the
repository's name or the person's, the tagline its description or their
bio. Setting one keeps it; listing a field under `hide` leaves it out of
the drawing. So a consumer who writes nothing at all gets banners that read
their repository or profile and keep reading it as it changes.

Stdlib only, like the rest of the kit: PyYAML is used when it happens to be
installed and a small reader for the flat, two-level YAML this file needs
substitutes when it is not. Every key is validated; an unknown key or value
fails the run with the key named rather than being ignored. The one
exception is a retired key: `emoji`, which the headers no longer draw, is
read and set aside, as is `emoji` under `hide`, so a config written for an
earlier version keeps working.
"""
from __future__ import annotations

import re

from .compose import FIGURES
from .content import FOOTER_FIELDS, HEADER_FIELDS
from .drafting import DEFAULT_PRINT, PRINTS, RAINBOW

DEFAULTS = {
    "mode": "auto",            # auto | profile | repository; auto reads a profile in the repository named after its owner
    "subject": "",             # a login, or owner/name; empty means this repository, or its owner
    "header": "section",       # section | sheet | strip | none; section is what a config that says nothing gets
    "footer": "",              # title-block | scale-bar | none; empty means the one made for the header
    "theme": DEFAULT_PRINT,    # the print the set is drawn in: blueprint, redprint, ... or rainbowprint
    "title": "",               # empty: the repository's name, or the person's name
    "tagline": "",             # empty: the repository's description, or the bio
    "motto": "",               # the sheet's one general note; empty: none, or in profile mode the status message
    "description": "",         # a longer line under the note; empty: none
    "figures": [],             # which figures, in order; empty means the mode's defaults
    "closing": "",             # the footer's closing phrase; empty: none
    "top": "Back to Top",      # the footer's way back up
    "links": [],               # the row of links under the footer; empty: the website, releases and issues
    "hide": [],                # fields that are not drawn (not `off`, which YAML reads as false)
    "readme": "manage",        # manage the blocks between the markers | none
    "readme_path": "README.md",
    "out": "assets/banners",   # where the SVGs are written
    "lock": True,              # keep .github/banners.lock.json, so `check` can redraw without a token
}
CHOICES = {
    "mode": {"auto", "profile", "repository"},
    "header": {"sheet", "section", "strip", "none"},
    "footer": {"", "title-block", "scale-bar", "none"},
    "theme": set(PRINTS) | {RAINBOW},
    "readme": {"manage", "none"},
}
# Keys an earlier version read and this one sets aside, rather than fail a config written for it.
RETIRED = frozenset({"emoji"})
TEXT = ("subject", "title", "tagline", "motto", "description", "closing", "top", "readme_path", "out")


class ConfigError(ValueError):
    pass


_ESCAPE = re.compile(r'\\(U[0-9a-fA-F]{8}|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)')
_SIMPLE = {"n": "\n", "t": "\t", "0": "\0", '"': '"', "\\": "\\", "/": "/", " ": " "}


def _unescape(body: str) -> str:
    """A double-quoted YAML scalar's escapes: the ones a config would carry, emoji included."""
    def one(m):
        e = m.group(1)
        if e[0] in "Uux" and len(e) > 1:
            return chr(int(e[1:], 16))
        return _SIMPLE.get(e, "\\" + e)
    return _ESCAPE.sub(one, body)


def _parse_scalar(s: str):
    s = s.strip()
    if s.startswith("'") and s.endswith("'") and len(s) >= 2:
        return s[1:-1].replace("''", "'")
    if s.startswith('"') and s.endswith('"') and len(s) >= 2:
        return _unescape(s[1:-1])
    low = s.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("", "null", "~"):
        return None
    try:
        return int(s)
    except ValueError:
        return s


def _parse_inline(s: str):
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [_parse_scalar(x) for x in inner.split(",")] if inner else []
    if s.startswith("{") and s.endswith("}"):
        out = {}
        for pair in s[1:-1].split(","):
            if pair.strip():
                k, _, v = pair.partition(":")
                out[_parse_scalar(k)] = _parse_scalar(v)
        return out
    return _parse_scalar(s)


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(ch)
        elif ch == "#" and (i == 0 or line[i - 1].isspace()):
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def parse_yaml(text: str) -> dict:
    """Enough YAML for this file: `key: scalar`, inline lists and maps, and block lists or maps one level deep."""
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ImportError:
        pass
    data: dict = {}
    key = None
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        body = line.strip()
        if indent == 0:
            k, sep, v = body.partition(":")
            if not sep:
                raise ConfigError(f"cannot read line: {raw!r}")
            key = k.strip()
            data[key] = _parse_inline(v) if v.strip() else None
        elif key is not None:
            if body.startswith("- "):
                if not isinstance(data.get(key), list):
                    data[key] = []
                data[key].append(_parse_inline(body[2:]))
            else:
                k, sep, v = body.partition(":")
                if not sep:
                    raise ConfigError(f"cannot read line: {raw!r}")
                if not isinstance(data.get(key), dict):
                    data[key] = {}
                data[key][_parse_scalar(k)] = _parse_scalar(v)
    return data


def _links(value) -> list:
    """`links` as [[label, url], ...], from a map of label to URL or a list of "Label | URL" lines."""
    if isinstance(value, dict):
        pairs = list(value.items())
    elif isinstance(value, list):
        pairs = []
        for item in value:
            if isinstance(item, dict) and len(item) == 1:
                pairs += list(item.items())
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                pairs.append(tuple(item))
            elif isinstance(item, str) and "|" in item:
                label, _, url = item.partition("|")
                pairs.append((label, url))
            else:
                raise ConfigError(f"links: cannot read {item!r}; write Label | URL, or a map of label: URL")
    else:
        raise ConfigError("links: expected a map of label: URL, or a list of Label | URL")
    out = [[str(label).strip(), str(url).strip()] for label, url in pairs]
    bad = [label for label, url in out if not label or not url]
    if bad:
        raise ConfigError(f"links: every link needs a label and a URL ({bad!r})")
    return out


def validate(given: dict, where: str = "the config") -> dict:
    """The full config: defaults under what was given, every key and value checked."""
    cfg = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULTS.items()}
    for k, v in (given or {}).items():
        k = str(k).replace("-", "_")
        if k in RETIRED:
            continue
        if k not in DEFAULTS:
            raise ConfigError(f"unknown key in {where}: {k}")
        if v is not None:
            cfg[k] = v
    for k in TEXT:
        cfg[k] = "" if cfg[k] is None else str(cfg[k])
    for k, allowed in CHOICES.items():
        if cfg[k] not in allowed:
            raise ConfigError(f"{k}: {cfg[k]!r} is not one of {sorted(a for a in allowed if a)}")
    for k in ("figures", "hide"):
        if isinstance(cfg[k], str):
            cfg[k] = [cfg[k]]
        if not isinstance(cfg[k], list):
            raise ConfigError(f"{k}: expected a list")
        cfg[k] = [str(x) for x in cfg[k] if k != "hide" or str(x) not in RETIRED]
    known = {key for keys in FIGURES.values() for key in keys}
    for k in cfg["figures"]:
        if k not in known:
            raise ConfigError(f"figures: {k!r} is not a figure ({', '.join(sorted(known))})")
    fields = set(HEADER_FIELDS) | set(FOOTER_FIELDS)
    for k in cfg["hide"]:
        if k not in fields:
            raise ConfigError(f"hide: {k!r} is not a field ({', '.join(sorted(fields))})")
    cfg["links"] = _links(cfg["links"]) if cfg["links"] else []
    if not isinstance(cfg["lock"], bool):
        raise ConfigError("lock: expected true or false")
    if cfg["theme"] == RAINBOW and not cfg["lock"]:
        raise ConfigError("theme: rainbowprint remembers its colour in the lock; set lock: true")
    return cfg


def load(path) -> dict:
    """The config at `path`, or the defaults when there is no file."""
    if path is not None and path.exists():
        return validate(parse_yaml(path.read_text(encoding="utf-8")), str(path))
    return validate({})


def _yaml(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(_yaml(v) for v in value) + "]"
    text = str(value)
    plain = text and not text[0] in "[]{}&*!|>'\"%@`#,?:-~ " and ": " not in text and " #" not in text \
        and text.lower() not in ("true", "false", "yes", "no", "on", "off", "null", "~") and not text.isdigit()
    return text if plain else "'" + text.replace("'", "''") + "'"


def dump(cfg: dict) -> str:
    """The config as the file a consumer would write: only what differs from the defaults, in their order."""
    lines = []
    for k, default in DEFAULTS.items():
        v = cfg.get(k, default)
        if v == default or (k == "footer" and not v):
            continue
        if k == "links":
            lines.append("links:")
            lines += [f"  {_yaml(label)}: {_yaml(url)}" for label, url in v]
        else:
            lines.append(f"{k}: {_yaml(v)}")
    return "\n".join(lines) + ("\n" if lines else "")
