import json
from datetime import datetime

from .config import PUBLISHED_FILE


def _read_raw() -> dict:
    if not PUBLISHED_FILE.exists():
        return {}
    try:
        with open(PUBLISHED_FILE, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def _write_raw(data: dict) -> None:
    PUBLISHED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PUBLISHED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_published() -> list[dict]:
    return _read_raw().get("published", [])


def is_duplicate(item_code: str, published: list[dict]) -> bool:
    if not item_code:
        return False
    return any(p.get("item_code") == item_code for p in published)


def add_published(entry: dict) -> None:
    """新しい公開記録を履歴に追記する(既存エントリは書き換えない)。"""
    data = _read_raw()
    items = data.get("published", [])
    items.append(entry)
    data["published"] = items
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _write_raw(data)
