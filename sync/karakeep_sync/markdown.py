from __future__ import annotations
import re
import yaml
from karakeep_sync.karakeep import Bookmark


def bookmark_filename(bm: Bookmark) -> str:
    return f"{bm.id}.md"


def bookmark_to_md(bm: Bookmark) -> str:
    frontmatter = {
        "id": bm.id,
        "url": bm.url,
        "title": bm.title,
        "tags": bm.tags,
        "created": bm.created,
        "updated": bm.updated,
        "source": "karakeep",
    }
    fm = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False).strip()
    body = bm.note.strip()
    if body:
        return f"---\n{fm}\n---\n\n{body}\n"
    return f"---\n{fm}\n---\n"


def md_to_bookmark(content: str) -> Bookmark:
    match = re.match(r"^---\n(.*?)\n---\n?(.*)?$", content, re.DOTALL)
    if not match:
        raise ValueError("Invalid Markdown: missing frontmatter")
    fm = yaml.safe_load(match.group(1))
    note = (match.group(2) or "").strip()
    return Bookmark(
        id=str(fm["id"]),
        url=fm["url"],
        title=fm.get("title") or "",
        tags=fm.get("tags") or [],
        created=str(fm["created"]),
        updated=str(fm["updated"]),
        note=note,
    )
