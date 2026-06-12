from karakeep_sync.karakeep import Bookmark
from karakeep_sync.markdown import bookmark_to_md, md_to_bookmark, bookmark_filename


BM = Bookmark(
    id="abc123",
    url="https://example.com/article",
    title="Example Article",
    tags=["topic/python", "area/work"],
    created="2024-01-01T00:00:00+09:00",
    updated="2024-01-02T00:00:00+09:00",
    note="my note here",
)


def test_bookmark_filename():
    assert bookmark_filename(BM) == "abc123.md"


def test_bookmark_to_md_contains_frontmatter():
    md = bookmark_to_md(BM)
    assert "id: abc123" in md
    assert "url: https://example.com/article" in md
    assert "topic/python" in md
    assert "my note here" in md
    assert md.startswith("---\n")


def test_md_to_bookmark_roundtrip():
    md = bookmark_to_md(BM)
    result = md_to_bookmark(md)
    assert result.id == BM.id
    assert result.url == BM.url
    assert result.title == BM.title
    assert result.tags == BM.tags
    assert result.note == BM.note
    assert result.updated == BM.updated


def test_md_to_bookmark_no_note():
    bm_no_note = Bookmark(
        id="xyz", url="https://x.com", title="X",
        tags=[], created="2024-01-01T00:00:00Z",
        updated="2024-01-01T00:00:00Z", note=""
    )
    md = bookmark_to_md(bm_no_note)
    result = md_to_bookmark(md)
    assert result.note == ""
