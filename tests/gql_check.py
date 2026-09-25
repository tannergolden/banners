# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Validate every GraphQL document the kit sends, against GitHub's schema.

GitHub's GraphQL endpoint is where a typo in a field name is found, one
run at a time. This checks the documents first: braces balance, every
selected field exists on its parent type, every argument is one the field
takes, and every variable is declared. The schema comes from the
`@octokit/graphql-schema` npm package (its `schema.json`), pointed at by
GITHUB_GRAPHQL_SCHEMA; without it only the structural checks run.

    npm pack @octokit/graphql-schema && tar xzf octokit-graphql-schema-*.tgz
    GITHUB_GRAPHQL_SCHEMA=package/schema.json python3 tests/gql_check.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

TOKEN = re.compile(r"\.\.\.|[A-Za-z_][A-Za-z0-9_]*|\$[A-Za-z_][A-Za-z0-9_]*|[{}():\[\]!,=]|\"(?:[^\"\\]|\\.)*\"|-?\d+(?:\.\d+)?")


def documents() -> dict:
    from bannerkit import measure

    out = {}
    for name in dir(measure):
        v = getattr(measure, name)
        if isinstance(v, str) and re.match(r"\s*query\b", v):
            out[f"measure.{name}"] = v
    return out


class Schema:
    def __init__(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        s = data.get("data", data)["__schema"]
        self.types = {t["name"]: t for t in s["types"]}
        self.query = s["queryType"]["name"]

    @staticmethod
    def unwrap(t):
        while t.get("ofType"):
            t = t["ofType"]
        return t["name"]

    def field(self, type_name: str, field: str):
        t = self.types.get(type_name) or {}
        for f in t.get("fields") or []:
            if f["name"] == field:
                return f
        return None

    def possible(self, type_name: str) -> list:
        t = self.types.get(type_name) or {}
        return [p["name"] for p in t.get("possibleTypes") or []]


def parse(doc: str) -> list:
    return TOKEN.findall(doc)


def check(name: str, doc: str, schema: Schema | None) -> list:
    problems = []
    depth = 0
    for ch in doc:
        depth += ch == "{"
        depth -= ch == "}"
        if depth < 0:
            break
    if depth != 0:
        problems.append(f"{name}: braces unbalanced ({depth:+d})")
        return problems
    toks = parse(doc)
    declared = set()
    used = set()
    i = 0
    # variables
    if toks[0] == "query":
        i = 1
        if toks[i] == "(":
            j = toks.index(")", i)
            declared = {t for t in toks[i:j] if t.startswith("$")}
            i = j + 1
    if not schema:
        used = {t for t in toks[i:] if t.startswith("$")}
        problems += [f"{name}: variable {v} used but not declared" for v in used - declared]
        return problems

    def walk(pos: int, parent: str) -> int:
        """pos is at '{'; returns the position after the matching '}'."""
        assert toks[pos] == "{", (name, pos, toks[pos])
        pos += 1
        while toks[pos] != "}":
            t = toks[pos]
            if t == "...":
                # ... on Type { ... }
                assert toks[pos + 1] == "on"
                sub = toks[pos + 2]
                if sub not in schema.possible(parent) and sub != parent:
                    problems.append(f"{name}: '... on {sub}' is not a possible type of {parent}")
                pos = walk(pos + 3, sub)
                continue
            fname = t
            pos += 1
            if toks[pos] == ":":  # alias
                fname = toks[pos + 1]
                pos += 2
            if fname == "__typename":
                f = {"type": {"name": "String"}, "args": []}
            else:
                f = schema.field(parent, fname)
            if f is None:
                problems.append(f"{name}: {parent} has no field '{fname}'")
                f = {"type": {"name": "?"}, "args": []}
            if toks[pos] == "(":
                j = pos + 1
                argnames = {a["name"] for a in f.get("args") or []}
                nest = 0  # inside an object literal such as orderBy:{field:..., direction:...}
                while toks[j] != ")":
                    if toks[j] == "{":
                        nest += 1
                    elif toks[j] == "}":
                        nest -= 1
                    elif nest == 0 and toks[j + 1] == ":" and not toks[j].startswith("$"):
                        if f["type"]["name"] != "?" and toks[j] not in argnames:
                            problems.append(f"{name}: {parent}.{fname} takes no argument '{toks[j]}'")
                    if toks[j].startswith("$"):
                        used.add(toks[j])
                    j += 1
                pos = j + 1
            if toks[pos] == "{":
                pos = walk(pos, schema.unwrap(f["type"]))
        return pos + 1

    walk(i, schema.query)
    problems += [f"{name}: variable {v} used but not declared" for v in used - declared]
    return problems


def main() -> int:
    path = os.environ.get("GITHUB_GRAPHQL_SCHEMA")
    schema = Schema(Path(path)) if path and Path(path).exists() else None
    problems = []
    docs = documents()
    for name, doc in docs.items():
        problems += check(name, doc, schema)
    mode = "against the schema" if schema else "structurally (no schema)"
    if problems:
        print(f"{len(problems)} problems in {len(docs)} documents, checked {mode}:\n  " + "\n  ".join(problems))
        return 1
    print(f"{len(docs)} GraphQL documents valid, checked {mode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
