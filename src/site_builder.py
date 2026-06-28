import markdown as md
import yaml
from jinja2 import Environment, FileSystemLoader

from .config import BASE_URL, CONTENT_DIR, GA_MEASUREMENT_ID, SITE_DIR, SITE_NAME, SITE_ORIGIN, SITE_POSTS_DIR, TEMPLATES_DIR

_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
_env.globals["ga_measurement_id"] = GA_MEASUREMENT_ID


def _parse_post(md_path) -> dict:
    """frontmatter(YAML) + Markdown本文の形式で保存された記事ファイルを読み込む。"""
    text = md_path.read_text(encoding="utf-8")
    _, frontmatter_text, body_text = text.split("---", 2)
    meta = yaml.safe_load(frontmatter_text)
    meta["body_html"] = md.markdown(body_text.strip(), extensions=["extra"])
    meta["source_path"] = md_path
    return meta


def load_all_posts() -> list[dict]:
    posts = [_parse_post(p) for p in sorted(CONTENT_DIR.glob("*.md"))]
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def build_site() -> dict:
    """content/posts/*.md から site/ 配下の静的HTMLを生成する。

    重要な制約: 一度生成済みの個別記事HTML(site/posts/<slug>/index.html)は
    絶対に再生成・上書きしない。ユーザーがGitHub上で直接記事を手直しすることがあるため。
    一覧ページ(index.html)とsitemap.xmlは「索引」であり個別記事ではないため、
    毎回全件から再生成してよい。
    """
    posts = load_all_posts()

    new_posts: list[str] = []
    for post in posts:
        post_dir = SITE_POSTS_DIR / post["slug"]
        out_path = post_dir / "index.html"
        if out_path.exists():
            continue  # 既存の個別記事には二度と書き込まない
        post_dir.mkdir(parents=True, exist_ok=True)
        html = _env.get_template("post.html").render(post=post, base_url=BASE_URL, site_name=SITE_NAME)
        out_path.write_text(html, encoding="utf-8")
        new_posts.append(post["slug"])

    index_html = _env.get_template("index.html").render(posts=posts, base_url=BASE_URL, site_name=SITE_NAME)
    (SITE_DIR / "index.html").write_text(index_html, encoding="utf-8")

    _write_sitemap(posts)
    _ensure_nojekyll()

    return {"new_posts": new_posts, "total_posts": len(posts)}


def _write_sitemap(posts: list[dict]) -> None:
    base = f"{SITE_ORIGIN}{BASE_URL}"
    urls = [f"{base}/"] + [f"{base}/posts/{p['slug']}/" for p in posts]
    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n'
    (SITE_DIR / "sitemap.xml").write_text(xml, encoding="utf-8")


def _ensure_nojekyll() -> None:
    nojekyll = SITE_DIR / ".nojekyll"
    if not nojekyll.exists():
        nojekyll.write_text("", encoding="utf-8")
