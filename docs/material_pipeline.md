# Background & Thumbnail Pipeline

## 素材取得
- テーマが決まったら `keyword = genre + hook` で動画/画像検索。
- Pexels API から 1080p ループ動画を取得し、`assets/cache/` に保存。
- 背景が不足する場合は Stable Diffusion API にキーワードを渡して生成。

## テンプレ連動
- テーマテンプレ (`configs/themes/*.yaml`) に `thumbnail_keywords` と配色を定義。
- サムネイル生成スクリプトはこの設定を参照し、驚きコピーや色を自動配置。

## TODO
- [ ] Pexels/Pixabay クライアントとキャッシュの実装。
- [ ] AI 画像生成ラッパー（Stable Diffusion API）。
- [ ] Pillow でのサムネイル描画テンプレ。
