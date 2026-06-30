# Creating Lists / adding bookmarks (write path via REST)

> Extracted from `CLAUDE.md` for progressive disclosure. The root `CLAUDE.md`
> points here; the operational recipe lives in this file.

`karakeep.py`'s `KarakeepClient` is **read/sync-only** — it has no `create_list` or
`add-to-list` method. To create folders or attach bookmarks (e.g. building a new List tree),
call the Karakeep REST API directly. Two things bite you, both learned the hard way:

- **Base URL = `.env`'s `NEXTAUTH_URL`** (e.g. `https://karakeep.tail7f8427.ts.net`), *not*
  `config.yaml`'s `http://localhost:3001`. Both reach the same instance from the `external` host,
  but `NEXTAUTH_URL` is the canonical address to use for ad-hoc API calls. Auth is
  `Authorization: Bearer $KARAKEEP_API_KEY` (from `.env`).
- **List creation requires an `icon`** (an emoji); `name` alone is accepted but every existing
  List carries one. Nest by passing `parentId`.

Proven recipe (`set -a && source .env && set +a` first; `BASE=$NEXTAUTH_URL`, `H="Authorization: Bearer $KARAKEEP_API_KEY"`):

```bash
# create a (nested) List → returns JSON with .id
curl -s -X POST -H "$H" -H "Content-Type: application/json" \
  -d '{"name":"github","icon":"🐙"}' "$BASE/api/v1/lists"                 # top-level
curl -s -X POST -H "$H" -H "Content-Type: application/json" \
  -d '{"name":"repository","icon":"📦","parentId":"<github_id>"}' "$BASE/api/v1/lists"  # child

# create a link bookmark (type:"link" is required) → returns .id
curl -s -X POST -H "$H" -H "Content-Type: application/json" \
  -d '{"type":"link","url":"https://github.com/owner/repo","title":"owner/repo"}' "$BASE/api/v1/bookmarks"

# attach bookmark to a List (idempotent; empty body on success)
curl -s -X PUT -H "$H" "$BASE/api/v1/lists/<list_id>/bookmarks/<bookmark_id>"
```

Before creating a bookmark, dedup by `url.rstrip("/")` against `GET /api/v1/bookmarks` (URL is
identity). After writing, verify via `GET /api/v1/lists/<id>/bookmarks`. Membership materializes
into `lists:` frontmatter on the next `karakeep-sync push`.
