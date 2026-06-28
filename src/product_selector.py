from datetime import date

import yaml

from .config import GENRES_FILE
from .history_store import is_duplicate
from .rakuten_client import filter_risky_items, get_ranking_pages

# 候補が薬機法フィルタ・重複除外で枯渇しにくいよう、ランキングを複数ページ分取得する
RANKING_PAGES = 3


def load_genres() -> list[dict]:
    with open(GENRES_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("genres", [])


def pick_genre_for_today(genres: list[dict], today: date | None = None) -> dict:
    """ジャンルを日替わりでローテーション選定する。ジャンルが1件のみの今回の検証フェーズでは
    常にその1件を返す。将来ジャンル数が増えても変更不要な設計。"""
    if not genres:
        raise ValueError("config/genres.yaml に有効なジャンルが設定されていません。")
    today = today or date.today()
    index = today.toordinal() % len(genres)
    return genres[index]


def select_product(genre: dict, published: list[dict]) -> dict | None:
    """指定ジャンルの楽天ランキングから、薬機法NG・既出商品を除外したうえで
    最上位の商品を1件選ぶ。候補が0件の場合はNoneを返す(呼び出し側はスキップ扱いにする)。"""
    items = get_ranking_pages(genre["rakuten_genre_id"], pages=RANKING_PAGES)
    safe_items, _excluded_count = filter_risky_items(items)
    candidates = [item for item in safe_items if not is_duplicate(item.get("item_code", ""), published)]
    if not candidates:
        return None
    return candidates[0]
