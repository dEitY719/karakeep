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


def test_create_bookmark_attaches_tags(httpx_mock: HTTPXMock):
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
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE}/api/v1/bookmarks/new001/tags",
        json={},
    )
    client = KarakeepClient(BASE, KEY)
    bm = Bookmark(id="", url="https://new.com", title="New",
                  tags=["topic/python"], created="", updated="", note="")
    created = client.create_bookmark(bm)
    assert created.id == "new001"


def test_get_all_bookmarks_paginates(httpx_mock: HTTPXMock):
    # First page
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE}/api/v1/bookmarks",
        json={
            "bookmarks": [BOOKMARK_RESPONSE["bookmarks"][0]],
            "nextCursor": "cursor_abc",
        },
    )
    # Second page
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE}/api/v1/bookmarks?cursor=cursor_abc",
        json={
            "bookmarks": [{
                **BOOKMARK_RESPONSE["bookmarks"][0],
                "id": "def456",
                "url": "https://example2.com",
            }],
        },
    )
    client = KarakeepClient(BASE, KEY)
    bookmarks = client.get_all_bookmarks()
    assert len(bookmarks) == 2
    assert bookmarks[0].id == "abc123"
    assert bookmarks[1].id == "def456"
