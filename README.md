# affiliate-blog

SNSのアルゴリズムに依存しない、完全自動のアフィリエイトブログ。GitHub Actionsが毎日1記事を自動生成し、GitHub Pagesで公開する。

## 仕組み

1. GitHub Actions(日次cron, JST朝7時)が `scripts/run_daily.py` を実行
2. 楽天ランキングAPIで商品候補を取得 → 薬機法NGワード・既出商品を除外
3. Gemini APIでSEOブログ記事を生成
4. Amazon検索リンク(アソシエイトタグ付き)を併記
5. Markdown原稿を `content/posts/` に保存し、`docs/` 配下に静的HTMLを生成
6. 変更をmainにpush → GitHub Pagesが自動配信

**一度公開した記事HTML(`docs/posts/<slug>/index.html`)には、バッチは二度と書き込まない。** 手直しが必要な記事は、GitHub上で直接そのファイルを編集すればよい。

## ローカルでの動作確認

```
pip install -r requirements.txt
python scripts/run_daily.py --dry-run   # ファイル書き込みなしで試す
python scripts/run_daily.py             # 実際に記事を1本生成
python -m http.server --directory docs 8000
```

## 現在の運用ジャンル

`config/genres.yaml` に「家電」のみ設定(検証用ダミー)。本番の10ジャンルは仕組みの動作確認後に別途決定する。
