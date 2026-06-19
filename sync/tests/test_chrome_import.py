# sync/tests/test_chrome_import.py
import json

from click.testing import CliRunner

from karakeep_sync import chrome_import as ci
from karakeep_sync.cli import cli
from karakeep_sync.karakeep import Bookmark

HTML = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<DL><p>
  <DT><H3 PERSONAL_TOOLBAR_FOLDER="true">북마크바</H3>
  <DL><p>
    <DT><A HREF="https://github.com">GitHub</A>
    <DT><H3>AI</H3>
    <DL><p>
      <DT><A HREF="https://claude.ai">Claude</A>
    </DL><p>
  </DL><p>
</DL><p>
"""

JSON = json.dumps({"roots": {"bookmark_bar": {"type": "folder", "name": "bar", "children": [
    {"type": "url", "name": "G", "url": "https://github.com"},
    {"type": "folder", "name": "AI", "children": [
        {"type": "url", "name": "C", "url": "https://claude.ai"}]}]}}})


def test_html_folder_mapping_and_toolbar_excluded():
    m = {e.url: e.folder for e in ci.parse_chrome_html(HTML)}
    assert m["https://github.com"] == ()      # 툴바 직속 → 태그 없음
    assert m["https://claude.ai"] == ("AI",)


def test_json_folder_mapping_and_root_excluded():
    m = {e.url: e.folder for e in ci.parse_chrome_json(JSON)}
    assert m["https://github.com"] == ()       # bookmark_bar 자체는 태그 아님
    assert m["https://claude.ai"] == ("AI",)


def test_auto_detect_format():
    assert ci.parse_chrome_bookmarks("{\"roots\":{}}") == []
    assert len(ci.parse_chrome_bookmarks(HTML)) == 2


def test_split_excluded_case_insensitive():
    entries = [ci.ChromeEntry("u1", "t", ("Company", "Sub")),
               ci.ChromeEntry("u2", "t", ("AI",))]
    kept, excluded = ci.split_excluded(entries, ("company",))
    assert [k.url for k in kept] == ["u2"]
    assert [x.url for x in excluded] == ["u1"]


class _FakeClient:
    def __init__(self, existing):
        self._existing = existing
        self.created = []
        self.tagged = {}

    def get_all_bookmarks(self):
        return self._existing

    def create_bookmark(self, bm):
        nid = f"new{len(self.created)}"
        self.created.append(bm.url)
        return Bookmark(id=nid, url=bm.url, title=bm.title, tags=[], created="", updated="")

    def add_tags(self, bid, tags):
        self.tagged[bid] = tags


def _entries():
    return [
        ci.ChromeEntry("https://exists.com", "E", ("AI",)),
        ci.ChromeEntry("https://new.com", "N", ("Dev", "Py")),
        ci.ChromeEntry("https://new.com/", "dup", ("Dev",)),  # 정규화 후 내부 중복
    ]


def test_import_entries_upsert_and_dedup():
    existing = [Bookmark(id="ex1", url="https://exists.com", title="", tags=[], created="", updated="")]
    fake = _FakeClient(existing)
    res = ci.import_entries(fake, _entries(), dry_run=False)

    assert res.todo == 2           # 내부 중복 1건 제거
    assert res.to_create == 1      # exists.com 은 기존 → 재사용
    assert res.created == 1
    assert fake.created == ["https://new.com"]
    assert fake.tagged["ex1"] == ["AI"]          # 기존 북마크에 폴더 태그 보강
    assert fake.tagged["new0"] == ["Dev", "Py"]


def test_import_entries_dry_run_writes_nothing():
    fake = _FakeClient([])
    res = ci.import_entries(fake, _entries(), dry_run=True)
    assert res.todo == 2 and res.to_create == 2
    assert fake.created == [] and fake.tagged == {}


def test_no_folder_tags_skips_tagging():
    fake = _FakeClient([])
    ci.import_entries(fake, _entries(), folder_tags=False, dry_run=False)
    assert fake.tagged == {}


def test_import_chrome_command_registered():
    out = CliRunner().invoke(cli, ["--help"]).output
    assert "import-chrome" in out
