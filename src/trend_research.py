import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

SYSTEM_PROMPT = """あなたはアフィリエイトブログ向けのSEOキーワード・トレンドリサーチャーです。
Google検索を使って、指定ジャンルの中で「需要はあるが競合記事が少なそうな、ニッチな切り口」を調査します。"""


def _get_client() -> genai.Client | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def research_trend(genre_hint: str) -> str:
    """Google検索連携のGeminiで、いま話題になっている商品・検索ニーズを調査する。失敗時は空文字を返す(ベストエフォート)。"""
    client = _get_client()
    if client is None:
        return ""

    prompt = f"""いま「{genre_hint}」のジャンルで、ブログ記事として需要がありそうな
ニッチな切り口・検索ニーズを教えてください。

以下の観点で調査してください:
1. 直近で話題になっている具体的な商品名・カテゴリ
2. どんな悩み・目的で検索されそうか(例:「一人暮らし向け」「コンパクト」等の絞り込み軸)
3. 競合記事が少なそうな切り口

簡潔にマークダウンの箇条書きでまとめてください。"""

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                max_output_tokens=2048,
                http_options=types.HttpOptions(timeout=120_000),
            ),
        )
        return response.text or ""
    except Exception:
        # ベストエフォート機能のため、失敗しても記事生成自体は続行させる
        return ""


if __name__ == "__main__":
    print(research_trend("家電"))
