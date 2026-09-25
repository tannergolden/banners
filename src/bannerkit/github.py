# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A small GitHub client on urllib: GraphQL, retries and a cost meter.

Trophies' client, cut to what a banner asks: nothing here knows about
banners. It exists so the measuring module can say what it wants in one
line, and so a test can substitute a fake with the same two methods.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

GRAPHQL = "https://api.github.com/graphql"
UA = "tannergolden-banners"


class ApiError(RuntimeError):
    pass


class GitHub:
    """`gql(query, **variables)` and `paged(...)`, with retries on 5xx and secondary limits."""

    def __init__(self, token: str | None = None, retries: int = 4, quiet: bool = False):
        self.token = token or os.environ.get("BANNERS_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        if not self.token:
            raise ApiError("no token: set GITHUB_TOKEN (the workflow does) or BANNERS_TOKEN")
        self.retries = retries
        self.quiet = quiet
        self.calls = 0
        self.points = 0  # GraphQL rate-limit cost, summed from each response
        self.last_errors: list[str] = []  # per-field errors of the last reply

    # -- transport -------------------------------------------------------------
    def _request(self, url: str, body: bytes) -> object:
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", UA)
        req.add_header("Content-Type", "application/json")
        delay = 2.0
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - a fixed https endpoint
                    self.calls += 1
                    raw = resp.read()
                    return json.loads(raw) if raw else None
            except urllib.error.HTTPError as exc:
                self.calls += 1
                retry_after = exc.headers.get("Retry-After")
                limited = exc.code in (403, 429) and (retry_after or "rate limit" in (exc.reason or "").lower())
                if exc.code == 401:
                    raise ApiError(f"GitHub refused the token (401) for {url}")
                if not (exc.code >= 500 or limited) or attempt == self.retries:
                    detail = exc.read().decode("utf-8", "replace")[:300]
                    raise ApiError(f"GitHub answered {exc.code} for {url}: {detail}")
                wait = float(retry_after) if retry_after else delay
                self._log(f"retrying after {exc.code} in {wait:.0f}s")
                time.sleep(wait)
                delay *= 2
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == self.retries:
                    raise ApiError(f"network failure for {url}: {exc}")
                time.sleep(delay)
                delay *= 2
        raise ApiError("unreachable")

    def _log(self, msg: str) -> None:
        if not self.quiet:
            print(f"::debug::{msg}" if os.environ.get("GITHUB_ACTIONS") else f"  {msg}", file=sys.stderr)

    def _warn(self, msg: str) -> None:
        """A line the run log shows without debug logging switched on."""
        if not self.quiet:
            print(f"::warning::{msg}" if os.environ.get("GITHUB_ACTIONS") else f"  {msg}", file=sys.stderr)

    # -- the calls -----------------------------------------------------------------
    def gql(self, query: str, **variables) -> dict:
        body = json.dumps({"query": query, "variables": variables}).encode()
        data = self._request(GRAPHQL, body)
        if not isinstance(data, dict):
            raise ApiError("GraphQL returned no body")
        cost = ((data.get("data") or {}).get("rateLimit") or {}).get("cost")
        if cost:
            self.points += cost
        errors = data.get("errors")
        if errors and not data.get("data"):
            raise ApiError("GraphQL: " + "; ".join(e.get("message", "?") for e in errors))
        # The path names the field, which is what a scope error hides.
        self.last_errors = [e.get("message", "?") + (f" (at {'.'.join(str(x) for x in e['path'])})" if e.get("path") else "")
                            for e in errors or []]
        for msg in self.last_errors:
            # Partial data with per-field errors (a private field, a missing
            # scope): keep what came back and say, visibly, what did not.
            self._warn("GraphQL partial: " + msg)
        return data["data"]

    def paged(self, query: str, path: tuple, page_size: int = 100, limit: int = 10, **variables) -> list:
        """Walk a GraphQL connection at `path` (keys into the response) until it ends or `limit` pages."""
        nodes: list = []
        after = None
        for _ in range(limit):
            data = self.gql(query, first=page_size, after=after, **variables)
            conn = data
            for key in path:
                conn = (conn or {}).get(key)
            if not conn:
                break
            nodes.extend(n for n in conn.get("nodes", []) if n)
            info = conn.get("pageInfo") or {}
            if not info.get("hasNextPage"):
                break
            after = info.get("endCursor")
        return nodes
