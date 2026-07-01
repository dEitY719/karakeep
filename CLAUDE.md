# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is **not** the upstream Karakeep app. It is a personal bookmark-sync pipeline around a
self-hosted Karakeep instance:

```
Karakeep (capture/UI)  ⇄  Markdown ({id}.md)  ⇄  Git repos inside the Obsidian vault
                          via REST API                (GitHub = common, GHES = company)
```

The heart is the `karakeep-sync` Python CLI in `sync/`. The repo also ships operational shell
scripts (`scripts/`) and design docs (`docs/`). The repo itself holds **no bookmark data** — data
lives in the running Karakeep instance's `DATA_DIR` (docker volume) and the bookmarks materialize as
Markdown inside the user's Obsidian vault, which are themselves separate git repos.

## Commands

All Python work happens in `sync/` (managed by mise + uv):

```bash
cd sync
uv sync                       # create .venv + install deps (incl. dev group)
mise run test                 # = uv run pytest  (full suite)
uv run pytest tests/test_cli.py::test_name   # single test
uv run karakeep-sync <cmd>    # run the CLI (= mise run run)
```

`karakeep-sync` subcommands: `push` (Karakeep→git), `pull` (git→Karakeep), `auto` (pull+push, used
by cron), `status` (count pending), `init` (clone repos + register `*/30 * * * *` cron), and
`import-chrome FILE` (Chrome HTML/JSON → Karakeep; defaults to dry-run, needs `--commit`).

Operational scripts (run from repo root): `scripts/bootstrap.sh` (idempotent new-PC setup),
`scripts/check.sh` (diagnose what's missing), `scripts/vault-sync.sh` (sync the whole Obsidian
vault), `scripts/llm-wiki-deploy.sh`. Docker (`docker compose up -d`) is only for `external` mode.

## Architecture — the two concepts that explain everything

### 1. The three PC modes (`~/.dotfiles-setup-mode`)

A single file `~/.dotfiles-setup-mode` holds `external` | `internal` | `home`, and this value
changes behavior across `config.py`, the CLI, and every shell script. Read `config.py:load_config`
to see the rules:

- **external** — *hosts* the Karakeep docker container; pushes/pulls the public (`common`) repo.
- **home** — sync client against the shared instance (`KARAKEEP_URL`); pushes/pulls `common`.
- **internal** (`is_work=True`) — sync client; `common` repo becomes **pull-only** (push disabled),
  and the `company` repo (GHES) is the only writable target. The `company` repo entry is dropped
  from config entirely unless mode is `internal`.

Topology SSOT: `docs/architecture/system/pc-environment.md`. Mode differences table: `README.md`.

### 2. The Company confidentiality guardrail (§4.3) — the critical invariant

Bookmarks in designated `company_lists` (default top-level list `Company`) are **confidential** and
must reach *only* a GHES repo, never the public GitHub repo. This is enforced in `cli.py` by
`_is_confidential` / `_repo_accepts_bookmark`, independent of per-repo `exclude_lists` (multi-layer
defense, so a missing config line cannot leak). Two directions:

- confidential bookmark → blocked from any non-`is_company` repo;
- `is_company` repo → accepts *only* confidential bookmarks (keeps public links out of company git).

`push` and `status` share this exact routing predicate, so "pending" counts never include bookmarks
that no repo would accept. When a PC has no company target, confidential bookmarks are **withheld
with a warning**, not silently dropped. When changing routing/filter logic, keep `push` and `status`
in sync and preserve this guardrail.

## Sync mechanics worth knowing

- **Identity is the URL.** Bookmarks dedup by `url.rstrip("/")`. Each bookmark is one
  `{id}.md` file with YAML frontmatter (`markdown.py`).
- **List membership is preserved as full paths** in the `lists:` frontmatter field and is **not**
  slugified (Korean/spaces/`/` hierarchy kept human-readable); only `tags` are slugified for
  Obsidian. Karakeep Lists are folder-like and nested (parent paths joined with `/`).
- **`sync-state.json`** (per bookmark: `updated`, `repo`, `imported`) prevents re-export loops —
  `imported:true` bookmarks are never pushed back, and unchanged timestamps are skipped unless
  `push --force` (used to backfill `lists:` membership).
- **`.env` auto-injection**: the CLI loads repo-root `.env` via `setdefault` (shell env wins over
  `.env`); cron and `check.sh` instead `source` it directly. `${VAR}` in `config.yaml` is expanded
  by `config.py:_expand`, which **raises** on any unresolved variable rather than failing silently.

## Inspecting live bookmark data (this repo has none)

This checkout contains only code. The running Karakeep instance's SQLite DB lives in its
deployment's `DATA_DIR` (docker volume). On the `external`-mode host that is the Karakeep
deployment checkout's `data/` dir — e.g. `/home/bwyoon/para/project/karakeep/data/db.db`
(`/home/bwyoon/para/project/karakeep-review-2` is a code-only review worktree with no data).

To answer "what Lists / bookmarks exist?", query that DB directly — do **not** guess from code.
The `sqlite3` CLI is **not installed** on this host; use Python's stdlib `sqlite3` instead:

```bash
python3 -c "import sqlite3; c=sqlite3.connect('/home/bwyoon/para/project/karakeep/data/db.db'); \
  [print(r) for r in c.execute('SELECT id,name,parentId,type FROM bookmarkLists ORDER BY parentId')]"
# membership: bookmarksInLists(bookmarkId, listId); bookmark rows in the bookmarks table.
```

### Classifying a new bookmark into a List

Karakeep is operated **List-based** (folders), not free tags. Hard rule: the **`Company`** List
(and its children) is the confidential boundary — its bookmarks go only to GHES `80-Company/`,
never public GitHub. So never put public/personal links in `Company`. For a general dev resource
that isn't language-specific, the catch-all dev List is `개발·SW엔지니어링` (vs. language-specific
`Python` / `C++`, or `AI 도구`). A bookmark in a non-`Company` List flows out to
`30-Resource/Bookmarks` and surfaces in Obsidian via its `lists:` frontmatter property.

### Creating Lists / adding bookmarks (write path via REST)

`karakeep.py`'s `KarakeepClient` is **read/sync-only** (no `create_list` / `add-to-list`). To
create folders or attach bookmarks, call the Karakeep REST API directly — base URL is `.env`'s
`NEXTAUTH_URL` (not `config.yaml`'s localhost), List creation needs an `icon`, and you dedup by
`url.rstrip("/")` before writing. The full proven curl recipe lives in
**`docs/claude/karakeep-rest-write-path.md`**.

## Module map (`sync/karakeep_sync/`)

`cli.py` (commands + routing/guardrail), `karakeep.py` (REST client + list-path resolution),
`markdown.py` (bookmark↔md, tag slugify), `config.py` (mode-aware load + `${VAR}` expansion),
`chrome_import.py` (Chrome bookmarks → Karakeep, folder→tags), `git_ops.py`, `state.py`.

## Gotchas

- `vault-sync.sh` syncs the **whole** Obsidian vault and is separate from `karakeep-sync`, which
  only manages the bookmark folders. Don't conflate them.
- The `30_Resources/llm-wiki/` path (underscore) is the LLM-wiki and is unrelated to the
  `30-Resource/Bookmarks` (hyphen) Karakeep submodule — see README "llm-wiki 연동".
- Docs are written in Korean; match that when editing `docs/` and `README.md`.
