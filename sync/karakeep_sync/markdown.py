from __future__ import annotations
import re
import yaml
from karakeep_sync.karakeep import Bookmark


def bookmark_filename(bm: Bookmark) -> str:
    return f"{bm.id}.md"


def slugify_tag(tag: str) -> str:
    """Obsidian 태그로 쓸 수 있게 정규화한다.

    Obsidian 태그는 공백을 허용하지 않으므로 AI 가 만든 'Design Patterns' 같은
    태그는 깨져 보인다. 소문자화하고 영숫자(유니코드, 한글 포함)·'/' 외의
    문자를 하이픈으로 바꾼다. '/' 는 Obsidian 계층 태그라 보존한다.
    """
    s = tag.strip().lower()
    s = re.sub(r"[^\w/]+", "-", s, flags=re.UNICODE)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


def bookmark_to_md(bm: Bookmark) -> str:
    frontmatter = {
        "id": bm.id,
        "url": bm.url,
        "title": bm.title,
        "tags": [s for t in bm.tags if (s := slugify_tag(t))],
        "created": bm.created,
        "updated": bm.updated,
        "source": "karakeep",
    }
    # 리스트 멤버십은 full path 그대로 보존한다 (Obsidian Properties/Dataview 로 필터링).
    # 태그와 달리 slugify 하지 않는다 — 한글 경로·공백·'/' 계층을 사람이 읽는 그대로 둔다.
    if bm.lists:
        frontmatter["lists"] = list(bm.lists)
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
        lists=fm.get("lists") or [],
    )
