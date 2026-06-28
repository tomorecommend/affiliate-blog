import json

from google import genai
from google.genai import types

from .config import gemini_api_key

SYSTEM_PROMPT = """あなたはアフィリエイトブログのSEO記事ライターです。
楽天市場の商品データと、与えられたトレンド情報を踏まえて、検索ユーザーの悩みを解決する
信頼できる比較・レビュー記事を作成します。AI臭い大げさな煽り文句や、根拠のない断定は避けてください。

【最優先・絶対禁止(薬機法違反による検索ペナルティ・法的リスクを防ぐため)】
- 効果効能を保証・断定する表現は絶対に使わない(例:「治る」「改善する」「完治」「効果が出る」「即効性」「症状が消える」など)
- 化粧品・健康グッズ・育児用品などの医薬品でない商品に対して、医薬品的な効能効果(治療・予防・症状改善)を暗示する表現は使わない
- 「絶対に」「必ず」「100%」など、効果を断定・保証するような言い切り表現は商品の効能に関して使わない
- 上記に当たるか迷う場合は、「個人の感想」「使ってみた印象」のような体験談トーンに必ず言い換える

【記事構成のルール】
- title: 32文字前後。検索されそうな具体的なキーワードを含む
- slug: 英数小文字とハイフンのみのURLスラッグ(日本語不可)
- meta_description: 110〜120文字程度。記事の要約とクリックを誘う一文
- headings: 3〜5個のH2見出しと、それぞれの本文(Markdown形式、各300〜500文字程度)。
  比較・選び方・具体的な使用シーンなど、読者の意思決定に役立つ実用的な内容にする
- conclusion_markdown: まとめ。商品の総括と、購入を検討する読者への一言

【ステルスマーケティング対策】
- 記事の冒頭(最初のh2より前を想定したリード文は不要だが、conclusion以外の本文中に1か所)で、
  「本記事はアフィリエイトリンクを含みます」という趣旨の開示が自然に読めるよう、
  最初のheadingsの本文の中に一文入れる

【Amazon検索キーワードについて】
- 楽天の商品名はSEOキーワードが詰め込まれて長すぎるため、そのままAmazon検索には使えない。
- amazon_search_keywordには、ブランド名・型番・商品カテゴリだけで構成した
  10〜20文字程度の簡潔な検索キーワードを別途生成すること(例:「富士通 プラズィオン HDS-302R 脱臭機」)
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "32文字前後のSEOタイトル"},
        "slug": {"type": "string", "description": "英数小文字とハイフンのみのURLスラッグ"},
        "meta_description": {"type": "string", "description": "110〜120文字程度のメタディスクリプション"},
        "headings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "h2": {"type": "string"},
                    "body_markdown": {"type": "string"},
                },
                "required": ["h2", "body_markdown"],
            },
        },
        "conclusion_markdown": {"type": "string"},
        "amazon_search_keyword": {
            "type": "string",
            "description": "ブランド名・型番・カテゴリのみで構成した10〜20文字程度のAmazon検索用キーワード",
        },
    },
    "required": ["title", "slug", "meta_description", "headings", "conclusion_markdown", "amazon_search_keyword"],
}


def _get_client() -> genai.Client | None:
    api_key = gemini_api_key()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def generate_article(
    genre: str,
    product_name: str,
    product_price: int,
    product_catch_copy: str = "",
    trend_info: str = "",
) -> dict | None:
    """商品情報・ジャンル・トレンド情報を踏まえて、長文SEOブログ記事を構造化生成する。
    戻り値: {"title", "slug", "meta_description", "headings", "conclusion_markdown"} または失敗時None。"""
    client = _get_client()
    if client is None:
        return None

    user_message = f"""【ジャンル】
{genre}

【今回紹介する商品(楽天市場)】
商品名: {product_name}
価格: {product_price}円
キャッチコピー: {product_catch_copy or "(なし)"}

【話題性・トレンド情報】
{trend_info or "(なし)"}

上記の商品を中心に、検索ユーザーの悩みを解決するSEO記事を作成してください。"""

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=4096,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                http_options=types.HttpOptions(timeout=120_000),
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )
        return json.loads(response.text)
    except Exception:
        return None
