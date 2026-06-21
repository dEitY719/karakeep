# sync/tests/test_karakeep.py
import json
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


# --- 회귀 방지: write API 스키마 (#14) ---

def test_create_bookmark_sends_type_link(httpx_mock: HTTPXMock):
    """link 북마크는 type 필드가 필수 — 누락 시 Karakeep 이 400 을 준다."""
    httpx_mock.add_response(
        method="POST", url=f"{BASE}/api/v1/bookmarks",
        json={"id": "n1", "title": "New", "tags": [],
              "createdAt": "2024-01-03T00:00:00.000Z",
              "content": {"url": "https://new.com"}},
    )
    client = KarakeepClient(BASE, KEY)
    client.create_bookmark(Bookmark(id="", url="https://new.com", title="New",
                                    tags=[], created="", updated=""))
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["type"] == "link"
    assert body["url"] == "https://new.com"


def test_add_tags_uses_tagname_schema(httpx_mock: HTTPXMock):
    """올바른 태그 attach 스키마는 {"tags":[{"tagName":..}]} (과거 {"name":..} 는 400)."""
    httpx_mock.add_response(
        method="POST", url=f"{BASE}/api/v1/bookmarks/abc/tags", json={"attached": []},
    )
    client = KarakeepClient(BASE, KEY)
    client.add_tags("abc", ["topic/python", "area/work"])
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body == {"tags": [{"tagName": "topic/python"}, {"tagName": "area/work"}]}


def test_add_tags_empty_is_noop(httpx_mock: HTTPXMock):
    client = KarakeepClient(BASE, KEY)
    client.add_tags("abc", [])
    assert httpx_mock.get_requests() == []


# --- 리스트(폴더) 멤버십 → frontmatter (#A) ---

LISTS_RESPONSE = {
    "lists": [
        {"id": "us", "name": "미국 주식 사이트", "parentId": None},
        {"id": "ipo", "name": "11 IPO·SPAC", "parentId": "us"},
        {"id": "ai", "name": "AI 도구", "parentId": None},
    ]
}


def test_build_list_paths_resolves_nested():
    from karakeep_sync.karakeep import BookmarkList, build_list_paths
    lists = [
        BookmarkList("us", "미국 주식 사이트", None),
        BookmarkList("ipo", "11 IPO·SPAC", "us"),
        BookmarkList("ai", "AI 도구", None),
    ]
    paths = build_list_paths(lists)
    assert paths["us"] == "미국 주식 사이트"
    assert paths["ipo"] == "미국 주식 사이트/11 IPO·SPAC"
    assert paths["ai"] == "AI 도구"


def test_get_all_lists(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="GET", url=f"{BASE}/api/v1/lists", json=LISTS_RESPONSE)
    client = KarakeepClient(BASE, KEY)
    lists = client.get_all_lists()
    assert {l.id for l in lists} == {"us", "ipo", "ai"}
    ipo = next(l for l in lists if l.id == "ipo")
    assert ipo.name == "11 IPO·SPAC"
    assert ipo.parent_id == "us"


def test_bookmark_in_excluded_list_matches_top_level():
    from karakeep_sync.karakeep import bookmark_in_excluded_list
    # 정확히 일치
    assert bookmark_in_excluded_list(["Company"], ["Company"]) is True
    # 하위 폴더(Company/...)도 제외 대상
    assert bookmark_in_excluded_list(["Company/사내포털"], ["Company"]) is True
    # 무관한 리스트는 통과
    assert bookmark_in_excluded_list(["미국 주식 사이트/11 IPO·SPAC"], ["Company"]) is False
    # 리스트 없음 → 통과
    assert bookmark_in_excluded_list([], ["Company"]) is False
    # 제외 목록이 비면 무조건 통과
    assert bookmark_in_excluded_list(["Company"], []) is False
    # "Companyabc" 같은 접두사 오탐 방지
    assert bookmark_in_excluded_list(["Companywide"], ["Company"]) is False


def test_get_bookmark_list_paths(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="GET", url=f"{BASE}/api/v1/lists", json=LISTS_RESPONSE)
    httpx_mock.add_response(
        method="GET", url=f"{BASE}/api/v1/lists/us/bookmarks",
        json={"bookmarks": []},
    )
    httpx_mock.add_response(
        method="GET", url=f"{BASE}/api/v1/lists/ipo/bookmarks",
        json={"bookmarks": [{"id": "bm1"}]},
    )
    httpx_mock.add_response(
        method="GET", url=f"{BASE}/api/v1/lists/ai/bookmarks",
        json={"bookmarks": [{"id": "bm1"}, {"id": "bm2"}]},
    )
    client = KarakeepClient(BASE, KEY)
    paths = client.get_bookmark_list_paths()
    assert paths["bm1"] == ["AI 도구", "미국 주식 사이트/11 IPO·SPAC"]  # sorted
    assert paths["bm2"] == ["AI 도구"]
