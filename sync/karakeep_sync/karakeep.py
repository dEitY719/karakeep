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
        resp = httpx.get(f"{self._base}/api/v1/bookmarks", headers=self._headers)
        resp.raise_for_status()
        return [self._parse(item) for item in resp.json()["bookmarks"]]

    def create_bookmark(self, bm: Bookmark) -> Bookmark:
        payload = {"url": bm.url, "title": bm.title, "note": bm.note}
        resp = httpx.post(
            f"{self._base}/api/v1/bookmarks", json=payload, headers=self._headers
        )
        resp.raise_for_status()
        return self._parse(resp.json())

    def update_bookmark(self, bookmark_id: str, bm: Bookmark) -> None:
        payload = {"title": bm.title, "note": bm.note}
        resp = httpx.patch(
            f"{self._base}/api/v1/bookmarks/{bookmark_id}",
            json=payload,
            headers=self._headers,
        )
        resp.raise_for_status()

    def _parse(self, item: dict) -> Bookmark:
        return Bookmark(
            id=item["id"],
            url=item["url"],
            title=item.get("title") or "",
            tags=[t["name"] for t in item.get("tags", [])],
            created=item["createdAt"],
            updated=item["updatedAt"],
            note=item.get("note") or "",
        )
