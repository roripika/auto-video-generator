# Media Asset Pipeline & Thumbnail Automation

## 1. 素材収集
- テーマとランキング項目からキーワードを生成し、Pexels/Pixabay API で背景動画・画像を取得。
- 併せて Stable Diffusion などの生成AIでオリジナル素材を生成するオプションを用意。
- 取得した素材は `assets/cache/<keyword>` に保存し、ライセンス情報を JSON に記録。

## 2. 素材整形
- 画像は ffmpeg の `zoompan` や Ken Burns プリセットで動きを付ける。
- 動画は `-stream_loop` で尺を揃え、音声はミュート。
- ロゴ／アイコン／ランキング番号などのオーバーレイ用素材を準備し、テロップと一緒に描画。

## 3. サムネイル自動生成
- テンプレ構造: 背景 + 大見出し + 副見出し + アイコン/スタンプ。
- テーマテンプレから `thumbnail_keywords` を読み出し、Pillow などで固定レイアウトを描画。
- 出力先: `outputs/rendered/<project>/<timestamp>/thumb.png`。

## 4. ワークフロー
1. テーマ入力→キーワード生成。
2. 素材検索→キャッシュ保存。
3. ffmpeg で背景／テロップ合成。
4. Pillow でサムネを生成。

## 5. TODO
- [ ] 素材検索クライアント（Pexels/Pixabay API + AI生成オプション）。
- [ ] キャッシュとメタ情報管理。
- [ ] サムネイル描画スクリプト。
- [ ] テンプレごとの配色・フォント設定ファイル。
