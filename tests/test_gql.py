# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every GraphQL document the kit sends is well formed; against GitHub's
schema too when GITHUB_GRAPHQL_SCHEMA points at one (see gql_check.py)."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gql_check  # noqa: E402


class Documents(unittest.TestCase):
    def test_documents_are_valid(self):
        path = os.environ.get("GITHUB_GRAPHQL_SCHEMA")
        schema = gql_check.Schema(Path(path)) if path and Path(path).exists() else None
        docs = gql_check.documents()
        self.assertEqual(len(docs), 4)
        problems = []
        for name, doc in docs.items():
            problems += gql_check.check(name, doc, schema)
        self.assertEqual(problems, [])

    def test_checker_catches_an_unbalanced_brace(self):
        self.assertTrue(gql_check.check("x", "query{ viewer{ login }", None))

    def test_checker_catches_an_undeclared_variable(self):
        self.assertTrue(gql_check.check("x", "query($a:Int){ viewer{ f(first:$b) } }", None))


if __name__ == "__main__":
    unittest.main()
