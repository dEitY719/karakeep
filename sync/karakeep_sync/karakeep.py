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
        payload = {"url": bm.url, "title": bm.title, "note": bm.note}
        resp = httpx.post(
            f"{self._base}/api/v1/bookmarks", json=payload, headers=self._headers
        )
        resp.raise_for_status()
        created = self._parse(resp.json())
        for tag in bm.tags:
            self._attach_tag(created.id, tag)
        return created

    def _attach_tag(self, bookmark_id: str, tag_name: str) -> None:
        resp = httpx.post(
            f"{self._base}/api/v1/bookmarks/{bookmark_id}/tags",
            json={"name": tag_name},
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
        for tag in bm.tags:
            self._attach_tag(bookmark_id, tag)

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
