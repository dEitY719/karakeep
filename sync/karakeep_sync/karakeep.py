from __future__ import annotations
from dataclasses import dataclass, field
import httpx


@dataclass
class Bookmark:
    id: str
    url: str
    title: str
    tags: list[str]
    created: str
    updated: str
    note: str = ""
    # Karakeep 리스트(폴더) 멤버십을 full path 로 담는다 (예: "미국 주식 사이트/11 IPO·SPAC").
    # 단방향(Karakeep → Obsidian frontmatter)으로만 쓰며 pull 시 Karakeep 으로 되돌리지 않는다.
    lists: list[str] = field(default_factory=list)


@dataclass
class BookmarkList:
    id: str
    name: str
    parent_id: str | None


def build_list_paths(lists: list[BookmarkList]) -> dict[str, str]:
    """리스트 id → full path(부모/자식) 를 만든다.

    중첩 리스트는 부모 이름을 '/' 로 이어 사람이 읽는 경로로 만든다 — Obsidian
    frontmatter 에 그대로 노출해 Dataview/Properties 로 필터링하기 위함이다.
    """
    by_id = {l.id: l for l in lists}

    def resolve(lid: str) -> str:
        node = by_id[lid]
        if node.parent_id and node.parent_id in by_id:
            return f"{resolve(node.parent_id)}/{node.name}"
        return node.name

    return {l.id: resolve(l.id) for l in lists}


def bookmark_in_any_list(bm_lists: list[str], list_names: list[str]) -> bool:
    """북마크가 주어진 top-level 리스트 중 하나에 속하는지 판단한다.

    repo export 의 포함(include)/제외(exclude) 라우팅에 공통으로 쓴다. 리스트
    경로는 full path("Company/사내포털")이므로 최상위 이름만 비교한다 — 하위 폴더도
    함께 매칭되고, "Companywide" 같은 접두사 오탐은 막는다.
    """
    if not list_names:
        return False
    return any(path.split("/", 1)[0] in list_names for path in bm_lists)


class KarakeepClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def get_all_bookmarks(self) -> list[Bookmark]:
        results = []
        cursor: str | None = None
        while True:
            params = {"cursor": cursor} if cursor else {}
            resp = httpx.get(
                f"{self._base}/api/v1/bookmarks",
                headers=self._headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            results.extend(self._parse(item) for item in data["bookmarks"])
            cursor = data.get("nextCursor")
            if not cursor:
                break
        return results

    def create_bookmark(self, bm: Bookmark) -> Bookmark:
        # Karakeep link 북마크는 `type` 필드가 필수다 — 없으면 400 Bad Request.
        payload: dict = {"type": "link", "url": bm.url, "title": bm.title}
        if bm.note:
            payload["note"] = bm.note
        resp = httpx.post(
            f"{self._base}/api/v1/bookmarks", json=payload, headers=self._headers
        )
        resp.raise_for_status()
        created = self._parse(resp.json())
        self.add_tags(created.id, bm.tags)
        return created

    def add_tags(self, bookmark_id: str, tags: list[str]) -> None:
        """북마크에 태그를 붙인다 (배치·멱등).

        올바른 스키마는 ``{"tags": [{"tagName": ...}]}`` 이다. 과거 구현은
        ``{"name": ...}`` 를 보내 400 을 받았다 — write 경로가 실제로 호출된 적이
        없어 드러나지 않았던 잠복 버그.
        """
        if not tags:
            return
        resp = httpx.post(
            f"{self._base}/api/v1/bookmarks/{bookmark_id}/tags",
            json={"tags": [{"tagName": t} for t in tags]},
            headers=self._headers,
        )
        resp.raise_for_status()

    def update_bookmark(self, bookmark_id: str, bm: Bookmark) -> None:
        payload = {"title": bm.title, "note": bm.note}
        resp = httpx.patch(
            f"{self._base}/api/v1/bookmarks/{bookmark_id}",
            json=payload,
            headers=self._headers,
        )
        resp.raise_for_status()
        self.add_tags(bookmark_id, bm.tags)

    def get_all_lists(self) -> list[BookmarkList]:
        resp = httpx.get(f"{self._base}/api/v1/lists", headers=self._headers)
        resp.raise_for_status()
        return [
            BookmarkList(id=l["id"], name=l["name"], parent_id=l.get("parentId"))
            for l in resp.json()["lists"]
        ]

    def _list_bookmark_ids(self, list_id: str) -> list[str]:
        ids: list[str] = []
        cursor: str | None = None
        while True:
            params = {"cursor": cursor} if cursor else {}
            resp = httpx.get(
                f"{self._base}/api/v1/lists/{list_id}/bookmarks",
                headers=self._headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            ids.extend(item["id"] for item in data["bookmarks"])
            cursor = data.get("nextCursor")
            if not cursor:
                break
        return ids

    def get_bookmark_list_paths(self) -> dict[str, list[str]]:
        """북마크 id → 소속 리스트 full path 목록(정렬)을 만든다.

        리스트 단위로 멤버를 조회(~리스트 수 만큼 호출)해 N+1 을 피한다.
        """
        lists = self.get_all_lists()
        paths = build_list_paths(lists)
        out: dict[str, list[str]] = {}
        for lst in lists:
            for bid in self._list_bookmark_ids(lst.id):
                out.setdefault(bid, []).append(paths[lst.id])
        for bid in out:
            out[bid].sort()
        return out

    def _parse(self, item: dict) -> Bookmark:
        # URL/title 은 link 타입의 경우 content 안에 중첩되어 온다.
        content = item.get("content") or {}
        return Bookmark(
            id=item["id"],
            url=content.get("url") or item.get("url") or "",
            title=item.get("title") or content.get("title") or "",
            tags=[t["name"] for t in item.get("tags", [])],
            created=item["createdAt"],
            updated=item.get("modifiedAt") or item.get("updatedAt") or item["createdAt"],
            note=item.get("note") or "",
        )
