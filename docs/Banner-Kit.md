<!--
title: '🪧 BANNER KIT'
description: 'The specification for the banner generator: the designs, the themes, the two modes, what is measured, the files it writes, the lock, and the contract every consumer relies on.'
tags: [banners, specification, svg, automation, readme-header]
category: docs
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🪧 BANNER KIT

<a name="top"></a>

**The specification: what a run measures, what it draws, and what it promises.**

_Drafted, never fetched._

</div>

---

## 🎯 Intent

A banner here is a **committed SVG**: a README's header or footer, drawn as a
sheet from a set of engineering drawings, from a measurement the action took
over GitHub's API. That removes any third-party dependency from the README,
removes any rate-limit risk at view time, and keeps what the header says true
without anyone editing it: the name, the description and the figures are read
from GitHub on every run and redrawn when they move.

The kit is one Python package with no dependencies, driven by one command:

| Module                                             | Job                                                                                   |
| :------------------------------------------------- | :------------------------------------------------------------------------------------ |
| `github.py`, `measure.py`                          | Measurement: the API client and both modes.                                           |
| `compose.py`                                       | A measurement and a config, as the header and footer's words and figures.             |
| `headers.py`, `footers.py`, `drafting.py`          | Drawing: three headers, two footers, and the sheet, dimensions and prints they share. |
| `canvas.py`, `text.py`, `draw.py`, `palette.py`    | The SVG canvas and its lint, outlined lettering, shared shapes, emblems' tokens.      |
| `plan.py`, `readme.py`, `lock.py`, `config.py`     | The plan of files, the README blocks, the lock, the config, and the commit message.   |
| `snippets.py`, `designs.py`, `layout.py`           | The `<picture>` markup, the design registry and its variants, layout helpers.         |
| `live.py`, `preview.py`, `page/`                   | The preview page, which runs this same package in the browser.                        |
| `banner-kit.py`                                    | The command line the action runs.                                                     |

---

## 🧱 The Set

A README gets two sheets from one set of drawings: a header at the top and a
footer at the foot, in the same print.

| Design       | Code | Kind   | Moves | Pairs with |
| :----------- | :--- | :----- | :---- | :--------- |
| Section      | H2   | header | yes   | F1         |
| Sheet        | H1   | header | yes   | F1         |
| Strip        | H3   | header | yes   | F2         |
| Title block  | F1   | footer | no    | H1, H2     |
| Scale bar    | F2   | footer | no    | H3         |

**H2 Section is the default**: a config that names no header gets it, over its
F1 Title block. H2 draws the title as a cut solid, outlined and hatched at 45
degrees, dimensioned both ways. H1 is a cover sheet with the title centred and
dimensioned. H3 is the sheet at a smaller scale. Along the foot of every
header runs its **schedule**: the project or the account, then the figures,
each a small label over its value, ruled from border to border.

### Files

Everything lands under `assets/banners/` (configurable as `out`):

| File                                             | When                                 |
| :----------------------------------------------- | :----------------------------------- |
| `header-day.svg`, `header-dark.svg`              | Always: 830 px wide                  |
| `header-still-day.svg`, `header-still-dark.svg`  | A design that moves: reduced motion  |
| `header-narrow-day.svg`, `header-narrow-dark.svg` | A phone: 360 px wide, always still  |
| `footer-*.svg`                                    | The same, for the footer, never still |
| `link-<label>-day.svg`, `link-<label>-dark.svg`  | One pair per link in the links row   |

An image in a README carries one link at most, the one around it, so the
footer as a whole is the way back to the top and each link under it is its
own small image. Rendering **prunes**: a `header-*`, `footer-*` or `link-*`
file the plan no longer names is deleted.

### Drawing rules

Every file is checked by the kit's lint before it is written, and a finding
fails the run:

- No script, no `foreignObject`, and no reference to anything outside the
  file: no font, image or stylesheet is fetched.
- Every colour is one of emblems' 64 tokens; a colour that is not is a bug.
- Lettering is drawn as paths from Barlow Condensed, so no reader needs a font
  installed, and no viewer's font draws anything. No header carries an
  emoji: an emoji a description or bio opens with is left off the tagline.
- `role="img"`, a `<title>` and a `<desc>`, and alt text built from exactly
  what the image shows.
- No en or em dash, and no file over 48 KB (12 KB for a link).
- A file that moves is complete without SMIL: every animated attribute keeps
  its resting value, so a viewer that does not animate sees the drawing whole.

Output is **deterministic**: the same measurement and config give
byte-identical files, which is what `check` relies on. Every file carries a
`banner-kit` version stamp.

---

## 🎨 Themes

`theme` picks the print the whole set is drawn in: its lines and lettering on
white paper by day, and its sheet by night.

| Theme         | By day: lines, lettering | By night: sheet, lettering |
| :------------ | :----------------------- | :------------------------- |
| `redprint`    | cherry, maroon           | cherry, white              |
| `orangeprint` | tangerine, brick         | tangerine, black           |
| `yellowprint` | mustard, charcoal        | mustard, black             |
| `greenprint`  | forest, forest           | forest, white              |
| `tealprint`   | teal, ocean              | ocean, white               |
| `blueprint`   | cobalt, navy             | navy, white                |
| `indigoprint` | iris, indigo             | indigo, white              |
| `purpleprint` | plum, amethyst           | amethyst, white            |
| `pinkprint`   | magenta, ruby            | ruby, white                |
| `brownprint`  | brown, brown             | brown, white               |
| `blackprint`  | charcoal, black          | charcoal, white            |

`blueprint` is the default. The first nine are the spectrum, red to pink;
`brownprint` and `blackprint` are the Van Dyke and black-line prints of the
same trade. Yellow and orange are lettered in black by night, since white
cannot be read on them.

**`rainbowprint`** draws each update in the next colour of the spectrum. The
lock remembers which colour the committed banners are in; a run that redraws
them, because something they show moved, takes the next one, and a quiet day
keeps the colour it has. After `pinkprint` it comes round to `redprint`.
`check` and `render` use the lock's colour, so a rainbow is checked like any
other print. It needs `lock: true`.

---

## 📏 Measurement

Two modes, the way trophies has them. `auto`, the default, reads a profile in
the repository named after its owner, whose README is the profile, and a
repository everywhere else.

### Repository mode

The repository whose README carries the banners: its name, description,
homepage, creation date, stars, forks, watchers, open issues, open pull
requests, primary language, licence (its SPDX id; one GitHub cannot name is
left off), latest release and its date, topics, whether its issues and
discussions are on and how many workflow files it has (for the link
buttons), and **the last change**.

### Profile mode

The person: name, bio, company, location, website, the year they joined,
followers, following, public repositories they own (forks excluded), the
stars those repositories earned, contributions in the last year as GitHub
counts them, their main language (the one most of their repositories are
written in, a tie going to the one with more stars) and their status
message. The profile repository is measured too, for the footer's
licence and last change.

### The last change

The date of the newest commit on the default branch that **a person** made.
A commit whose committer is a bot, or whose subject opens with
`chore(banners):` or `chore(trophies):`, does not count, so a refresh never
moves the date it draws and never causes the next one. Up to 500 commits are
read back.

### The queries

Four GraphQL documents, written out in full in `measure.py`:
`REPOSITORY`, `HISTORY`, `USER` and `REPOS`. `tests/gql_check.py` checks them
structurally on every run of the tests, and against GitHub's published schema
(the `@octokit/graphql-schema` package) with `make schema`. A run costs a
handful of calls: one or two for the repository, one per 100 commits read
back, and in profile mode one for the person and one per 100 repositories.
`GITHUB_TOKEN` reads all of it.

---

## ✍️ Composition

What a banner says comes from one of two places. A field the config leaves
empty is **read from GitHub**; a field it sets **wins**; a field listed under
`hide` is **not drawn**, and not spoken in the alt text either.

| Field         | From GitHub, when the config is empty                                   |
| :------------ | :---------------------------------------------------------------------- |
| `title`       | The repository's name, or the person's name (their login if the letters cannot draw it) |
| `tagline`     | The repository's description, or the bio                                |
| `motto`       | Nothing, or in profile mode the status message: the sheet's one note    |
| `figures`     | The mode's defaults, below                                              |
| footer        | The handle, the licence and the last change; the closing phrase is the config's |
| `links`       | The first four pages a developer reaches for, below                     |

**Link buttons.** The row under the footer holds up to four buttons, each its
own small image with its own link. A config that names links gets those, in
its order, four at most. One that names none gets the first four of these
the repository has:

| Mode       | In order, the first four there                                                                  |
| :--------- | :---------------------------------------------------------------------------------------------- |
| repository | Issues (when on), Pull Requests, Releases (when there is one), Actions (when it has a workflow), Discussions (when on), Contributors |
| profile    | Website (when the person has one), Repositories, Projects, Packages, Stars                      |

A repository's page with nothing on it is never a button. Every default URL
is absolute, since a README is also read where a relative link would resolve
against the wrong page.

**Figures.** Each is a label over a value; one GitHub has no value for is left
out. Counts are lettered in full to 99,999, then as `128k` and `1.2M`.

| Mode         | Default figures, in order                                                   | Also available                        |
| :----------- | :-------------------------------------------------------------------------- | :------------------------------------ |
| `repository` | project, release, stars, forks, issues, language, license                   | watchers, pulls, updated, created, site |
| `profile`    | account, followers, repositories, stars, contributions, language, since     | following, location, company, site    |

**Drawable text.** Lettering is outlined from a fixed set of letters: every
letter of Latin-1 and Latin Extended-A, the digits and common marks. Measured
text is made drawable first: a dash the standards ban becomes a hyphen, a
GitHub `:shortcode:` is dropped, and a character no face holds is left out,
with a note in the run's summary. Text is clipped at a word: 40 characters
for a title, 160 for a tagline, 80 for a note.

---

## ⚙️ The Config

`.github/banners.yml`. Every key is optional and validated; an unknown key or
value fails the run with the key named. [`examples/banners.yml`](../examples/banners.yml)
lists every key at its default.

| Key           | Default          | Meaning                                                                           |
| :------------ | :--------------- | :-------------------------------------------------------------------------------- |
| `mode`        | `auto`           | `auto`, `profile` or `repository`.                                                |
| `subject`     | this repository  | A login, or `owner/name`. Empty means this repository, or its owner.              |
| `header`      | `section`        | `section`, `sheet`, `strip` or `none`.                                            |
| `footer`      | the header's pair | `title-block`, `scale-bar` or `none`.                                            |
| `theme`       | `blueprint`      | Any print above, or `rainbowprint`.                                               |
| `title`       | from GitHub      | The title, set fully capped.                                                      |
| `tagline`     | from GitHub      | The line under the title.                                                         |
| `motto`       | none             | The sheet's one general note, in capitals.                                        |
| `description` | none             | A longer line under the note.                                                     |
| `figures`     | the mode's       | Which figures, in order.                                                          |
| `closing`     | none             | The footer's closing phrase.                                                      |
| `top`         | `Back to Top`    | The words on the footer's way back up. The footer links to the top either way.    |
| `links`       | from GitHub      | Up to four buttons: a map of label to URL, or a list of `Label \| URL` lines.     |
| `hide`        | `[]`             | Fields not drawn: any of the header's and footer's fields.                        |
| `readme`      | `manage`         | Write the README blocks, or `none`.                                               |
| `readme_path` | `README.md`      | The file that holds them.                                                         |
| `out`         | `assets/banners` | Where the SVGs are written.                                                       |
| `lock`        | `true`           | Keep `.github/banners.lock.json`.                                                 |

The list of fields that are not drawn is `hide`, not `off`: YAML reads a bare
`off` as `false`. The kit reads the file with PyYAML when it happens to be
installed and with its own reader for this flat shape when it is not, and the
two agree on every documented form.

---

## 🔒 The Lock

`.github/banners.lock.json`, when `lock: true`:

```json
{
  "version": 1,
  "last": { "mode": "repository", "subject": "octo-dev/toolkit", "today": "2026-09-25", "repository": { "…": "…" } },
  "rainbow": "tealprint",
  "snapshot": "2026-09-25"
}
```

- `last` is the measurement the committed banners were drawn from. `check`
  replans against it and `render` redraws from it, without a token.
- `rainbow` is the colour a `rainbowprint` is drawn in now.
- `snapshot` is the last weekly write.

The lock is written when a drawing changed, and when seven days have passed
since the last snapshot. That weekly write is a real commit, which keeps
GitHub from switching the schedule off after sixty days without one.
Deleting the lock loses nothing but those three.

---

## 📝 The README Blocks

With `readme: manage`, the run owns what sits between
`<!-- banners:header:start -->` and `<!-- banners:header:end -->`, and
between the footer's pair of markers. The first run puts the header block at
the top of the README and the footer block at its foot; every later run
rewrites only what is between the markers, so they can be moved anywhere.
A block whose design is set to `none` is taken out again, markers and all.

The header block holds the `<a name="top">` anchor the footer links back to,
and one `<picture>`: the narrow file below 585 px, the still file under
reduced motion, the dark file in a dark theme, the day file otherwise. A
tagline or motto the drawing leaves out is written under it as Markdown, so
hiding it from the image does not drop it from the page.

The whole footer image is a link to `#top`, always: hiding `top` takes the
words "Back to Top" off the drawing, not the way back. With `header: none`
the header block is still written, holding the anchor and nothing else, so
the footer has a top to go back to. The link is written as one HTML block,
`<a href="#top">` on a line of its own and no blank line before `</a>`.
Written on one line with `<picture>`, Markdown would close the link before
the image, and GitHub would link the image to its own SVG instead.

---

## 🧭 The Command Line

```bash
python3 src/banner-kit.py run      --root . [--mode …] [--subject …] [--save m.json] [--commit-file msg.txt]
python3 src/banner-kit.py measure  --mode … --subject … > m.json
python3 src/banner-kit.py render   --root . [--from m.json]
python3 src/banner-kit.py check    --root . [--from m.json]
python3 src/banner-kit.py preview  --root out/ [--mode repository|profile]
python3 src/banner-kit.py page     --out preview/preview.html
python3 src/banner-kit.py gallery  [--check]
python3 src/banner-kit.py lint
```

Every subcommand that touches a repository takes `--root`, `--config`,
`--mode`, `--subject`, `--header`, `--footer`, `--theme`, `--out` and
`--today YYYY-MM-DD`, which fixes the date for reproducible runs. The action
calls `run` with `--commit-file`, which writes the Conventional Commit for the
run when something changed; `preview` draws the built-in sample measurement
with no network and is what the tests use.

`check` is the consumer's gate. It reads the measurement the lock remembered
(or `--from`), replans, and compares with the files on disk and the README
blocks: no token, no network, and nothing can move underneath it. It exits 0
when the banners are exactly what the kit draws from that measurement, 1
naming what is stale (a hand-edited file, a missing one, a drifted block, a
config changed without a run), and 2 when there is no measurement to check.
The workflow exposes it as `check: true` and the action as `mode: check`.

`page` builds the preview page: every design, drawn by this same package
running in the browser under Brython, checked byte for byte against the kit
before it draws live. It fetches Brython once, pinned by checksum.

---

## 🤝 The Contract

What a consumer pinned to `v1` can rely on:

1. The stub is the only file in their repository with behavior in it, and it
   has none: a schedule and a `uses:`.
2. With no config at all, the README gets H2 Section over F1 Title block, in
   blueprint, every word and figure read from GitHub.
3. The output folder mirrors the plan; nothing else under `out` is touched.
4. The README is edited only between the markers.
5. Commits are authored by the kit's author (the workflow's `author` input)
   and committed by `github-actions[bot]`, as Conventional Commits with the
   `banners` scope, and each one is unique to the run: the subject names what
   moved and the body carries what the banners show, the date and the run.
   The measurement sets those commits aside, so a refresh never moves the
   last change it draws.
6. A quiet day writes nothing, except the weekly lock snapshot.
7. `check` never needs a token: committed banners can be verified against
   the measurement their lock remembers, in pull-request CI, by anyone.

---

## 🏷️ Releases

Tags come in two kinds: `vX.Y.Z` is immutable and fixed, for anyone who wants
exactness; `v1` is moving, re-pointed at each release in the line, the pin
every stub uses and the reason a fix reaches every README without anyone
editing a workflow. The reusable workflow fetches the kit at the same ref it
was called at (`kit-ref`, `v1` by default), so a stub at `@v1` runs the
released kit; this repository's own banners pass its commit, so a change is
exercised by the tree that carries it before it is released.

A version is cut by dispatching **🏷️ Cut Release** with `vX.Y.Z`. That stub
calls `tannergolden/standards/.github/workflows/release.yml@v1`, called and
never copied: it refuses a commit that is not on the default branch and a
version that does not move forward, proves the files a consumer resolves at
the tag exist and that `make check` passes, tags the version, force-moves the
major, publishes the release with generated notes, and prunes the pages the
release superseded. A change that alters what a banner looks like for
unchanged input bumps `KIT_VERSION`, so every README redraws on its next run;
a change that removes an input, a mode, a design or a theme is breaking and
belongs in a new major line.

---

<div align="center">

[↑ Back to Top](#top)

</div>
