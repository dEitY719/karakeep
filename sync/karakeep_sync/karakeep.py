from __future__ import annotations
from dataclasses import dataclass
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
