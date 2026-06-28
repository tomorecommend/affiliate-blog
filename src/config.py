import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT_DIR / "content" / "posts"
SITE_DIR = ROOT_DIR / "docs"
SITE_POSTS_DIR = SITE_DIR / "posts"
TEMPLATES_DIR = ROOT_DIR / "templates"
DATA_DIR = ROOT_DIR / "data"
RUNS_DIR = DATA_DIR / "runs"
PUBLISHED_FILE = DATA_DIR / "published.json"
GENRES_FILE = ROOT_DIR / "config" / "genres.yaml"

# GitHub Pagesでリポジトリ名のサブパス配信になるため、テンプレート内のリンクは
# 必ずこのBASE_URLを起点にする(将来カスタムドメイン化する際もここを変えるだけで済む)
BASE_URL = os.getenv("BASE_URL", "/affiliate-blog")

SITE_NAME = os.getenv("SITE_NAME", "ニッチ商品お得情報ブログ")


def gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "")


def amazon_associate_tag() -> str:
    return os.getenv("AMAZON_ASSOCIATE_TAG", "")
