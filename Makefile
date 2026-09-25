# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
#
# The kit is stdlib-only Python, so every target below runs on a bare
# `python3` with nothing installed. `make preview` fetches Brython once, pinned
# by checksum, into .cache/; `make schema` fetches GitHub's GraphQL schema
# once, from npm, into the same place.

PYTHON ?= python3
KIT    := $(PYTHON) src/banner-kit.py
ELEMENTS := $(PYTHON) src/elements-kit.py
SCHEMA := .cache/schema/package/schema.json

.DEFAULT_GOAL := help
.PHONY: help preview sample gallery lint check test schema draw glyphs elements clean-preview

## help: List the available targets
help:
	@echo "Banners - the Banner Kit, and the Elements Kit beside it"
	@echo
	@grep -E '^## ' $(MAKEFILE_LIST) | sed -e 's/## /  /' -e 's/:/\t-/' | column -t -s $$'\t'

## preview: Build preview/preview.html, every design drawn by the kit (no network after the first run)
preview:
	@$(KIT) page --out preview/preview.html

## sample: Draw the sample repository and profile into preview/, the way a run would (no network)
sample:
	@$(KIT) preview --root preview/repository --mode repository --today 2026-09-25
	@$(KIT) preview --root preview/profile --mode profile --today 2026-09-25

## gallery: Redraw the README's gallery into assets/gallery/ from the samples
gallery:
	@$(KIT) gallery

## lint: Draw every design for every sample in every print and lint every file
lint:
	@$(KIT) lint

## check: CI gate - every file lints, every query is well formed, the gallery, this README's banners and its elements and the driftmark specimen are current, a sample root re-checks clean
check: lint
	@$(PYTHON) tests/gql_check.py
	@$(KIT) gallery --check
	@if $(PYTHON) -c "import json,sys; sys.exit(0 if json.load(open('.github/banners.lock.json')).get('last') else 1)" 2>/dev/null; then $(KIT) check --root . ; fi
	@rm -rf preview/check && mkdir -p preview/check
	@$(KIT) preview --root preview/check --mode repository >/dev/null
	@$(KIT) check --root preview/check --mode repository
	@rm -rf preview/check
	@$(ELEMENTS) check --root examples/driftmark
	@if [ -f .github/elements.lock.json ]; then $(ELEMENTS) check --root . ; fi

## test: Everything CI runs - the gate plus the unit tests
test: check
	@$(PYTHON) -m unittest discover -s tests -p 'test_*.py'
	@$(PYTHON) -m unittest discover -s .github/scripts -p 'test_*.py'

## schema: Check every GraphQL query against GitHub's published schema (@octokit/graphql-schema)
schema:
	@test -f $(SCHEMA) || (mkdir -p .cache/schema && cd .cache/schema && npm pack @octokit/graphql-schema --silent >/dev/null && tar xzf octokit-graphql-schema-*.tgz)
	@GITHUB_GRAPHQL_SCHEMA=$(SCHEMA) $(PYTHON) tests/gql_check.py

## elements: Redraw this README's own elements from git, the way a run would (no network)
elements:
	@$(ELEMENTS) run --root .

## draw: Draw every design's files for the samples into preview/files/
draw:
	@$(KIT) draw --out preview/files

## glyphs: Re-extract the glyph supplement and prove it matches trophies' outlines (needs fonttools, skia-pathops)
glyphs:
	@$(PYTHON) src/extract-glyphs.py --cache .cache/fonts

## clean-preview: Remove the built preview
clean-preview:
	@rm -rf preview
