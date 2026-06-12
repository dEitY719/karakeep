import json
from pathlib import Path
from karakeep_sync.state import load_state, save_state, BookmarkState


def test_load_empty_state(tmp_path):
    assert load_state(tmp_path / "state.json") == {}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    original = {
        "abc123": BookmarkState(updated="2024-01-01T00:00:00+09:00", repo="common", imported=False),
        "xyz789": BookmarkState(updated="2024-01-02T00:00:00+09:00", repo="company", imported=True),
    }
    save_state(original, path)
    loaded = load_state(path)
    assert loaded == original


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "state.json"
    save_state({}, path)
    assert path.exists()
