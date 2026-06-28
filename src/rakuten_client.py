import os
import time
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

RANKING_ENDPOINT = "https://openapi.rakuten.co.jp/ichibaranking/api/IchibaItem/Ranking/20220601"
SEARCH_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"

# 薬機法に触れやすい効果効能・症状訴求キーワード(商品名・キャッチコピーに含まれる商品はピックアップ対象から除外する)
RISKY_KEYWORDS = [
    "効果", "効能", "改善", "治る", "治療", "完治", "即効性",
    "妊娠線", "アトピー", "湿疹", "かぶれ", "アレルギー",
    "育毛", "発毛", "薄毛", "サプリ", "医薬部外品",
    "美白", "シミ", "しわ", "ニキビ", "痩せる", "ダイエット",
    "免疫力", "ホルモン", "便秘解消", "アンチエイジング", "デトックス",
    "抗炎症", "殺菌", "消毒",
]

# 楽天APIは2026年の新仕様でリクエスト間隔1.5秒以上を推奨(超過すると429エラー)
_MIN_INTERVAL_SEC = 1.5
_last_request_at = 0.0


def _throttle() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < _MIN_INTERVAL_SEC:
        time.sleep(_MIN_INTERVAL_SEC - elapsed)
    _last_request_at = time.monotonic()


def _credentials() -> tuple[str, str, str, str]:
    app_id = os.getenv("RAKUTEN_APP_ID", "")
    access_key = os.getenv("RAKUTEN_ACCESS_KEY", "")
    affiliate_id = os.getenv("RAKUTEN_AFFILIATE_ID", "")
    referer = os.getenv("RAKUTEN_REFERER", "")
    if not app_id:
        raise ValueError("RAKUTEN_APP_ID が .env に設定されていません。")
    if not access_key:
        raise ValueError(
            "RAKUTEN_ACCESS_KEY が .env に設定されていません。"
            "楽天ウェブサービスの管理画面でアプリを確認し、'pk_'で始まるアクセスキーを.envに追加してください(2026年の新仕様でapplicationIdとは別に必須)。"
        )
    if not referer:
        raise ValueError(
            "RAKUTEN_REFERER が .env に設定されていません。"
            "アプリ登録時に設定したサイトURL(Referer/Origin)を.envに追加してください(2026年の新仕様で必須)。"
        )
    return app_id, access_key, affiliate_id, referer


def _request_headers(referer: str) -> dict:
    parsed = urlparse(referer)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return {"Referer": referer, "Origin": origin}


def _to_item(raw: dict) -> dict:
    item = raw.get("Item", raw)
    image_urls = item.get("mediumImageUrls", [])
    image_url = ""
    if image_urls:
        image_url = image_urls[0].get("imageUrl", "") if isinstance(image_urls[0], dict) else image_urls[0]
    # 楽天APIのitemCodeは既に"shopCode:商品固有コード"の形式で返ってくる
    item_code = item.get("itemCode", "")
    return {
        "name": item.get("itemName", ""),
        "price": int(item.get("itemPrice") or 0),
        "url": item.get("affiliateUrl") or item.get("itemUrl", ""),
        "image_url": image_url,
        "catch_copy": item.get("catchcopy", ""),
        "rank": item.get("rank"),
        "review_average": item.get("reviewAverage"),
        "review_count": item.get("reviewCount"),
        # 重複公開防止用の安定キー。商品名の表記揺れに影響されない一意な識別子。
        "item_code": f"rakuten:{item_code}" if item_code else "",
    }


def is_risky_item(item: dict) -> bool:
    """商品名・キャッチコピーに薬機法上の効果効能・症状訴求キーワードを含むか判定する。"""
    text = f"{item.get('name', '')} {item.get('catch_copy', '')}"
    return any(keyword in text for keyword in RISKY_KEYWORDS)


def filter_risky_items(items: list[dict]) -> tuple[list[dict], int]:
    """薬機法に触れる可能性のある商品を除外する。戻り値: (安全な商品一覧, 除外件数)"""
    safe_items = [item for item in items if not is_risky_item(item)]
    return safe_items, len(items) - len(safe_items)


def get_ranking(genre_id: int, page: int = 1) -> list[dict]:
    """指定ジャンルの売れ筋ランキング(リアルタイム)を取得する。"""
    app_id, access_key, affiliate_id, referer = _credentials()
    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "genreId": genre_id,
        "period": "realtime",
        "page": page,
        "format": "json",
    }
    if affiliate_id:
        params["affiliateId"] = affiliate_id

    _throttle()
    resp = requests.get(RANKING_ENDPOINT, params=params, headers=_request_headers(referer), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return [_to_item(raw) for raw in data.get("Items", [])]


def search_items(keyword: str, genre_id: int | None = None, hits: int = 10) -> list[dict]:
    """キーワードで商品を検索する(トレンド調査結果から具体商品を探す用途)。"""
    app_id, access_key, affiliate_id, referer = _credentials()
    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "keyword": keyword,
        "hits": hits,
        "sort": "-reviewCount",
        "format": "json",
    }
    if genre_id:
        params["genreId"] = genre_id
    if affiliate_id:
        params["affiliateId"] = affiliate_id

    _throttle()
    resp = requests.get(SEARCH_ENDPOINT, params=params, headers=_request_headers(referer), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return [_to_item(raw) for raw in data.get("Items", [])]


def get_ranking_pages(genre_id: int, pages: int = 3) -> list[dict]:
    """複数ページ分のランキングをまとめて取得する(候補プールを広げて、フィルタ後の枯渇を防ぐ)。"""
    items: list[dict] = []
    for page in range(1, pages + 1):
        items.extend(get_ranking(genre_id, page=page))
    return items


if __name__ == "__main__":
    items = get_ranking(genre_id=100533)
    for it in items[:5]:
        print(it["rank"], it["name"][:40], it["price"], "円", it["item_code"])
