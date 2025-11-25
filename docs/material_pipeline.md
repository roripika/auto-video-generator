# Background & Thumbnail Pipeline

## 素材取得
- テーマが決まったら `keyword = genre + hook` で動画/画像検索。
- Pexels API から 1080p ループ動画を取得し、`assets/cache/` に保存。
- 背景が不足する場合は Stable Diffusion API にキーワードを渡して生成。

## テンプレ連動
- テーマテンプレ (`configs/themes/*.yaml`) に `thumbnail_keywords` と配色を定義。
- サムネイル生成スクリプトはこの設定を参照し、驚きコピーや色を自動配置。

## TODO
- [x] Pexels/Pixabay クライアントとキャッシュの実装。
- [x] AI 画像生成ラッパー（Stable Diffusion API）。
- [x] Pillow でのサムネイル描画テンプレ。

## 実装状況 (2024-11)
- `src/assets/clients.py`: Pexels/Pixabay 用の検索クライアント。API Key は `PEXELS_API_KEY` / `PIXABAY_API_KEY` を参照し、未設定なら自動スキップ。
- `src/assets/cache.py`: `assets/cache/<keyword>/provider_kind_id.ext` にバイナリ、同名 `.json` にライセンス/著者/取得日時を記録。
- `src/assets/pipeline.py`: `AssetFetcher` が検索→ダウンロード→キャッシュ保存を統合。素材が無い場合は Stable Diffusion フォールバックに対応。
- `src/assets/generators.py`: Stability AI ラッパー。`STABILITY_API_KEY` があれば `generate_image()` で PNG とメタ情報を返す。
- `src/assets/thumbnail.py`: Pillow ベースの `ThumbnailRenderer`。テーマに定義した色・フォントに沿ってテキスト/バッジ/CTA を描画。
- `scripts/fetch_assets.py`: CLI から `python scripts/fetch_assets.py --keyword "ライフハック 驚き"` のように実行し、画像/動画をキャッシュに保存。
- `scripts/generate_thumbnail.py`: `python scripts/generate_thumbnail.py --headline "知らないと損"` でテーマ連動のサムネ PNG を生成。

## 環境変数
| 変数 | 用途 |
| --- | --- |
| `PEXELS_API_KEY` | 背景動画 / 画像検索（Pexels） |
| `PIXABAY_API_KEY` | 背景動画 / 画像検索（Pixabay） |
| `STABILITY_API_KEY` | Stable Diffusion 生成フォールバック |

キーが未設定の場合は対応するサービスをスキップし、利用可能なサービスだけで処理する。

## テーマのサムネイル設定
`configs/themes/*.yaml` に `thumbnail` セクションを追加すると、以下のプロパティでスタイルを制御できる。

| キー | 内容 |
| --- | --- |
| `background_color` | 背景の基調色（グラデーションのベース） |
| `overlay_opacity` | 背景画像に被せる暗幕の強さ (0.0 - 1.0) |
| `primary_color` | 見出しやCTAボタンのメインカラー |
| `accent_color` | バッジや副見出しカラー |
| `stroke_color` / `stroke_width` | テキストの縁取り設定 |
| `font_heading` / `font_subheading` | 任意のフォントパス。未指定時は DejaVu フォントを利用 |
