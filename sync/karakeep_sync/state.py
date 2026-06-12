from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path

DEFAULT_STATE_PATH = Path("~/apps/karakeep/sync/sync-state.json").expanduser()


@dataclass
class BookmarkState:
    updated: str   # ISO 8601
    repo: str      # "common" | "company"
    imported: bool


def load_state(path: Path = DEFAULT_STATE_PATH) -> dict[str, BookmarkState]:
    if not path.exists():
        return {}
    with open(path) as f:
        raw = json.load(f)
    return {k: BookmarkState(**v) for k, v in raw.items()}


def save_state(state: dict[str, BookmarkState], path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({k: asdict(v) for k, v in state.items()}, f, indent=2)
