# sync/tests/test_karakeep.py
import pytest
import httpx
from pytest_httpx import HTTPXMock
from karakeep_sync.karakeep import KarakeepClient, Bookmark

BASE = "http://localhost:3000"
KEY = "test-api-key"

BOOKMARK_RESPONSE = {
    "bookmarks": [
        {
            "id": "abc123",
            "url": "https://example.com",
            "title": "Example",
            "note": "my note",
            "tags": [{"name": "topic/python"}, {"name": "area/work"}],
            "createdAt": "2024-01-01T00:00:00.000Z",
            "updatedAt": "2024-01-02T00:00:00.000Z",
        }
    ]
}


def test_get_all_bookmarks(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE}/api/v1/bookmarks",
        json=BOOKMARK_RESPONSE,
    )
    client = KarakeepClient(BASE, KEY)
    bookmarks = client.get_all_bookmarks()

    assert len(bookmarks) == 1
    bm = bookmarks[0]
    assert bm.id == "abc123"
    assert bm.url == "https://example.com"
    assert bm.tags == ["topic/python", "area/work"]
    assert bm.note == "my note"


def test_create_bookmark(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE}/api/v1/bookmarks",
        json={
            "id": "new001",
            "url": "https://new.com",
            "title": "New",
            "note": "",
            "tags": [],
            "createdAt": "2024-01-03T00:00:00.000Z",
            "updatedAt": "2024-01-03T00:00:00.000Z",
        },
    )
    client = KarakeepClient(BASE, KEY)
    bm = Bookmark(id="", url="https://new.com", title="New",
                  tags=[], created="", updated="", note="")
    created = client.create_bookmark(bm)
    assert created.id == "new001"


def test_update_bookmark(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="PATCH", url=f"{BASE}/api/v1/bookmarks/abc123", json={})
    client = KarakeepClient(BASE, KEY)
    bm = Bookmark(id="abc123", url="https://example.com", title="Updated",
                  tags=[], created="", updated="", note="new note")
    client.update_bookmark("abc123", bm)  # should not raise
