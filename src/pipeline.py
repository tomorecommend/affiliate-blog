import json
import re
import traceback
from datetime import date, datetime

import yaml

from . import site_builder
from .amazon_link import build_search_link
from .article_generator import generate_article
from .config import CONTENT_DIR, RUNS_DIR
from .history_store import add_published, load_published
from .product_selector import load_genres, pick_genre_for_today, select_product
from .trend_research import research_trend


def _slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9-]+", "-", text.lower()).strip("-")
    return text or "post"


def _write_run_log(status: str, detail: dict) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    today_str = date.today().isoformat()
    path = RUNS_DIR / f"{today_str}.json"
    payload = {"date": today_str, "status": status, "timestamp": datetime.now().isoformat(), **detail}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_post_markdown(slug: str, today_str: str, genre: str, product: dict, article: dict, amazon_link: str) -> None:
    body_parts = [f"## {h['h2']}\n\n{h['body_markdown']}" for h in article["headings"]]
    body_parts.append(f"## まとめ\n\n{article['conclusion_markdown']}")
    body = "\n\n".join(body_parts)

    frontmatter = {
        "title": article["title"],
        "slug": slug,
        "meta_description": article["meta_description"],
        "date": today_str,
        "genre": genre,
        "product_name": product["name"],
        "product_price": product["price"],
        "product_image": product.get("image_url", ""),
        "product_url": product.get("url", ""),
        "amazon_search_link": amazon_link,
        "item_code": product.get("item_code", ""),
    }
    front_yaml = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    content = f"---\n{front_yaml}---\n\n{body}\n"

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    post_path = CONTENT_DIR / f"{slug}.md"
    post_path.write_text(content, encoding="utf-8")


def run(dry_run: bool = False) -> dict:
    genres = load_genres()
    genre = pick_genre_for_today(genres)
    published = load_published()

    try:
        product = select_product(genre, published)
    except Exception as exc:
        # 楽天API側の一時的な障害(429/5xx/認証エラー等)。リトライ・通知はせず、その日はスキップする。
        _write_run_log("failed", {"reason": f"rakuten_api_error: {exc}", "genre": genre["name"]})
        return {"status": "failed", "reason": str(exc)}

    if product is None:
        _write_run_log("skipped", {"reason": "no_candidate", "genre": genre["name"]})
        return {"status": "skipped", "reason": "no_candidate", "genre": genre["name"]}

    trend_info = research_trend(genre["name"])  # ベストエフォート。失敗時は空文字が返るだけで続行する

    article = generate_article(
        genre=genre["name"],
        product_name=product["name"],
        product_price=product["price"],
        product_catch_copy=product.get("catch_copy", ""),
        trend_info=trend_info,
    )
    if article is None:
        _write_run_log("skipped", {"reason": "gemini_failed", "genre": genre["name"], "product": product["name"]})
        return {"status": "skipped", "reason": "gemini_failed"}

    amazon_link = build_search_link(article["amazon_search_keyword"])
    today_str = date.today().isoformat()
    slug = f"{today_str}-{_slugify(article['slug'])}"

    if dry_run:
        return {
            "status": "dry_run",
            "genre": genre["name"],
            "product": product["name"],
            "article_title": article["title"],
            "slug": slug,
        }

    _save_post_markdown(slug, today_str, genre["name"], product, article, amazon_link)
    add_published(
        {
            "date": today_str,
            "genre": genre["name"],
            "item_code": product.get("item_code", ""),
            "product_name": product["name"],
            "slug": slug,
            "post_path": f"content/posts/{slug}.md",
        }
    )

    build_result = site_builder.build_site()
    _write_run_log("success", {"genre": genre["name"], "product": product["name"], "slug": slug, **build_result})
    return {"status": "success", "slug": slug, **build_result}


if __name__ == "__main__":
    print(run())
