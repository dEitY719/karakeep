"""Chrome 북마크(HTML 내보내기 / 원본 JSON) → Karakeep import.

- 입력 자동 감지: ``{`` 로 시작하면 Chrome 원본 JSON, 아니면 Netscape HTML.
- 폴더 경로를 태그로 매핑하되, 툴바 루트(bookmark_bar / PERSONAL_TOOLBAR_FOLDER)는 제외.
- 기존 북마크 URL 과 dedup 후 멱등 업서트(있으면 재사용 + 태그 보강, 없으면 생성).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from html.parser import HTMLParser

from karakeep_sync.karakeep import Bookmark, KarakeepClient


@dataclass
class ChromeEntry:
    url: str
    title: str
    folder: tuple[str, ...] = ()


@dataclass
class ImportResult:
    parsed: int = 0
    excluded: list[ChromeEntry] = field(default_factory=list)
    todo: int = 0           # dedup 후 대상 수
    to_create: int = 0      # 그중 신규 생성 대상
    created: int = 0
    tagged: int = 0
    failed: int = 0


# ---------- 파서: Chrome 원본 JSON ----------
def parse_chrome_json(text: str) -> list[ChromeEntry]:
    roots = json.loads(text).get("roots", {})
    out: list[ChromeEntry] = []

    def walk(node: dict, path: tuple[str, ...]) -> None:
        if node.get("type") == "url":
            url = node.get("url", "")
            if url.startswith(("http://", "https://")):
                out.append(ChromeEntry(url=url, title=node.get("name") or url, folder=path))
        elif node.get("type") == "folder" or "children" in node:
            name = node.get("name")
            newpath = path + (name,) if name else path
            for child in node.get("children", []):
                walk(child, newpath)

    # 최상위 roots(bookmark_bar/other/synced) 자체 이름은 태그에서 제외하고,
    # 그 하위 폴더부터 태그로 만든다 → 자식들을 path=() 로 시작.
    for key in ("bookmark_bar", "other", "synced"):
        if key in roots:
            for child in roots[key].get("children", []):
                walk(child, ())
    return out


# ---------- 파서: Chrome HTML 내보내기 (Netscape) ----------
class _NetscapeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.entries: list[ChromeEntry] = []
        self._stack: list[str] = []
        self._cur_href: str | None = None
        self._capture_h3 = False
        self._capture_a = False
        self._a_text = ""
        self._h3_text = ""
        self._last_h3 = ""
        self._pending_toolbar = False  # 직전 H3 가 PERSONAL_TOOLBAR_FOLDER 인가

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t == "h3":
            self._capture_h3 = True
            self._h3_text = ""
            # 툴바 루트(북마크바/Bookmarks bar 등)는 태그에서 제외한다.
            self._pending_toolbar = dict(attrs).get("personal_toolbar_folder") == "true"
        elif t == "a":
            self._cur_href = dict(attrs).get("href")
            self._capture_a = True
            self._a_text = ""
        elif t == "dl":
            # 폴더 한 단계 진입 — 직전 H3 가 폴더명. 툴바 루트면 빈 문자열로 푸시
            # (folder 튜플 만들 때 빈 문자열은 걸러져 태그에서 제외됨).
            name = "" if self._pending_toolbar else self._last_h3
            self._stack.append(name)
            self._pending_toolbar = False

    def handle_endtag(self, tag):
        t = tag.lower()
        if t == "h3":
            self._capture_h3 = False
            self._last_h3 = self._h3_text.strip()
        elif t == "a":
            if self._cur_href and self._cur_href.startswith(("http://", "https://")):
                folder = tuple(p for p in self._stack if p)
                self.entries.append(
                    ChromeEntry(url=self._cur_href, title=self._a_text.strip() or self._cur_href, folder=folder)
                )
            self._capture_a = False
            self._cur_href = None
        elif t == "dl" and self._stack:
            self._stack.pop()

    def handle_data(self, data):
        if self._capture_h3:
            self._h3_text += data
        elif self._capture_a:
            self._a_text += data


def parse_chrome_html(text: str) -> list[ChromeEntry]:
    p = _NetscapeParser()
    p.feed(text)
    return p.entries


def parse_chrome_bookmarks(text: str) -> list[ChromeEntry]:
    """입력 형식을 자동 감지해 파싱한다."""
    return parse_chrome_json(text) if text.lstrip().startswith("{") else parse_chrome_html(text)


# ---------- 제외 / import ----------
def split_excluded(
    entries: list[ChromeEntry], exclude_folders: tuple[str, ...]
) -> tuple[list[ChromeEntry], list[ChromeEntry]]:
    """폴더 경로 중 한 컴포넌트라도 exclude_folders 와 (대소문자 무시) 일치하면 제외."""
    excl = {x.lower() for x in exclude_folders}
    if not excl:
        return list(entries), []
    kept, excluded = [], []
    for e in entries:
        (excluded if any(p.lower() in excl for p in e.folder) else kept).append(e)
    return kept, excluded


def excluded_to_json(excluded: list[ChromeEntry]) -> str:
    return json.dumps(
        [{"url": e.url, "title": e.title, "folder": list(e.folder)} for e in excluded],
        ensure_ascii=False,
        indent=2,
    )


def import_entries(
    client: KarakeepClient,
    entries: list[ChromeEntry],
    *,
    folder_tags: bool = True,
    dry_run: bool = True,
    progress=None,
) -> ImportResult:
    """entries 를 Karakeep 에 멱등 업서트한다.

    dry_run=True 면 카운트만 계산하고 쓰기는 하지 않는다 (단, 기존 목록 조회는 함).
    progress(i, n) 콜백이 주어지면 매 항목마다 호출한다.
    """
    result = ImportResult(parsed=len(entries))
    existing_id = {b.url.rstrip("/"): b.id for b in client.get_all_bookmarks()}

    # 파일 내부 중복 제거 (첫 등장만)
    todo: list[ChromeEntry] = []
    seen: set[str] = set()
    for e in entries:
        key = e.url.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        todo.append(e)
        if key not in existing_id:
            result.to_create += 1
    result.todo = len(todo)

    if dry_run:
        return result

    for i, e in enumerate(todo, 1):
        tags = list(e.folder) if folder_tags else []
        key = e.url.rstrip("/")
        try:
            bid = existing_id.get(key)
            if bid is None:
                bm = Bookmark(id="", url=e.url, title=e.title, tags=[], created="", updated="")
                bid = client.create_bookmark(bm).id
                result.created += 1
            if tags:
                client.add_tags(bid, tags)
                result.tagged += 1
        except Exception:  # noqa: BLE001  — 한 건 실패가 전체를 막지 않도록
            result.failed += 1
        if progress:
            progress(i, len(todo))
    return result
