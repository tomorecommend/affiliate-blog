import os
import re
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

ASIN_PATTERNS = [
    r"/dp/([A-Z0-9]{10})",
    r"/gp/product/([A-Z0-9]{10})",
    r"/ASIN/([A-Z0-9]{10})",
    r"[?&]ASIN=([A-Z0-9]{10})",
]


def extract_asin(url_or_asin: str) -> str | None:
    """AmazonのURLからASINを抜き出す。すでにASINそのものが渡された場合はそのまま返す。"""
    text = url_or_asin.strip()
    if re.fullmatch(r"[A-Z0-9]{10}", text):
        return text
    for pattern in ASIN_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def build_associate_link(url_or_asin: str) -> str:
    """ASIN/URLからAmazonアソシエイトリンクを生成する(ASINが既知の場合用。今回のブログ自動化では未使用)。"""
    tag = os.getenv("AMAZON_ASSOCIATE_TAG", "")
    if not tag:
        raise ValueError("AMAZON_ASSOCIATE_TAG が .env に設定されていません。")

    asin = extract_asin(url_or_asin)
    if not asin:
        raise ValueError(
            "URLからASINを取得できませんでした。短縮URL(amzn.to等)の場合は、"
            "商品ページを開いて表示されるURL(amazon.co.jp/dp/...)を貼り直してください。"
        )
    return f"https://www.amazon.co.jp/dp/{asin}?tag={tag}"


def build_search_link(keyword: str) -> str:
    """商品名やキーワードから、Amazon検索結果ページへのアソシエイトリンクを生成する。

    Amazon PA-API(商品情報取得用の公式API)は新規ブログだと180日以内に
    3件以上の売上がないとアクセス権を剥奪されるため、本プロジェクトではPA-APIを使わず、
    キーワード検索結果へのリンク(Amazonアソシエイト規約上認められた方式)で代替する。
    """
    tag = os.getenv("AMAZON_ASSOCIATE_TAG", "")
    if not tag:
        raise ValueError("AMAZON_ASSOCIATE_TAG が .env に設定されていません。")
    return f"https://www.amazon.co.jp/s?k={quote(keyword)}&tag={tag}"


if __name__ == "__main__":
    print(build_search_link("電気ケトル 一人暮らし"))
