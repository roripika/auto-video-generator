# AutoVideoGenerator: 全体仕様

## TL;DR
- YAML台本からYouTube解説動画を自動生成するPythonパイプライン。
- LLMでトレンド台本生成→VOICEVOX音声合成→FFmpeg映像レンダ→YouTube自動投稿まで対応。
- ElectronデスクトップUIとCLIの両方で運用可能。文字化け対策のフォント解決機能を実装済み。
- short/通常を自動判定。テロップ幅は `--adjust-tickers` で事前調整。
- 既知課題: Pixabay 400頻発、ショート時のテロップはみ出し、YouTubeトークン期限切れ。

## 用語・前提
- **VOICEVOX**: 日本語音声合成エンジン。ローカルAPIサーバーとして動作 (localhost:50021)。
- **FFmpeg**: 映像・音声処理ツール。テロップ描画とBGMダッキングに使用。
- **Pexels/Pixabay**: 背景素材取得用の無料APIサービス。環境変数でキー管理。
- **LLM**: Claude/GPT等の大規模言語モデル。台本とトレンドアイデア生成に使用。
- **Electron**: デスクトップアプリフレームワーク。台本編集UIを提供。
- **short_mode**: `auto/off/short/inherit`。60秒以下で縦1080x1920に自動スイッチ (auto)。
- **adjust_tickers**: テロップ幅自動調整 (Pillowで文字幅計測、改行/縮小)。
- **YouTube OAuth**: `client_secrets*.json` と `~/.config/auto-video-generator/youtube_credentials.pickle`。

## 概要
### 何を解決するか
- YouTube向け解説動画の量産（トレンド追従・定時投稿）をコードベースで完全自動化。
- 企画→台本→音声→映像→投稿の全工程を手動操作なしで実行。

### なぜ今必要か
- トレンド動画は鮮度が命。人手の企画・編集では間に合わない。
- 同一フォーマットで量産する場合、手作業の限界コストが高い。
- ショート/通常を自動切替し、テロップは縦画面でもはみ出さないよう調整が必要。

### システムの構成
- **Pythonコア** (`src/`, `scripts/`): 台本処理、音声合成、映像レンダ、素材管理。
- **Electronアプリ** (`desktop-app/`): 台本編集、プレビュー、スケジュール管理UI。
- **外部依存**: VOICEVOX Engine (localhost:50021), FFmpeg, Pexels/Pixabay API, LLM API。

## 仕組み/手順
### 実行フロー（CLI）
1. **台本読込**: YAML/JSONを `src/script_io.py` でpydanticモデルに変換。
2. **素材補完**: 背景動画/画像を `src/assets/pipeline.py` がPexels/Pixabayから自動取得、キャッシュ (`assets/cache/`)。
3. **音声生成**: セクションごとのナレーションを `src/audio/voicevox_client.py` でWAV化 (`work/audio/`)。
4. **タイムライン計算**: 音声長からセクション開始/終了時刻を `src/timeline.py` で確定。
5. **映像合成**: `src/render/ffmpeg_runner.py` がFFmpegコマンド生成→実行。背景ループ/ズームパン、テロップ描画、BGMダッキング。
6. **出力**: SRT字幕、メタデータJSON、サムネイル画像を `src/outputs.py` で生成。

### 実行フロー（自動トレンド生成）
1. **トレンド収集**: `scripts/fetch_trend_ideas_llm.py` がLLMに問い合わせ、候補JSON生成。
2. **台本生成**: `scripts/generate_script_from_brief.py` がブリーフから台本YAML作成。
3. **動画生成**: `scripts/generate_video.py --adjust-tickers` で上記1-6を実行。
4. **YouTube投稿**: `scripts/youtube_upload.py` でOAuth認証→アップロード（任意）。
5. **スケジュール実行**: `scripts/scheduler_daemon.py` がcron的に上記を繰り返し。

### Electronアプリの役割
- **台本編集**: YAML手動編集、セクション単位の追加/削除/並替。
- **プレビュー**: 別ウィンドウで映像プレビュー+YAML同時表示。メイン編集エリアを拡大。
- **スケジューラーUI**: 定期実行の開始/停止、パラメータ設定（インターバル、最大キーワード数、カテゴリ、ショート指定）。
- **YouTube認証**: トークン管理、認証テスト、トークン削除。

### ショート動画対応
- `short_mode=auto` で60秒以下を自動検出し、解像度を1080x1920に切替。
- `--adjust-tickers` でテロップ幅を事前調整（Pillowで文字幅計測、改行/縮小）。
- 自動実行では `--adjust-tickers` を強制ON。

### 素材とキャッシュ
- 背景: `bg_keyword` をキーにPexels/Pixabay検索。失敗時はローカルデフォルトにフォールバック。
- BGM: YouTube Audio Library から自動取得（yt-dlp）。指定URLがあれば優先。`assets/bgm/` にキャッシュ。
- 履歴: `work/topic_history.json` で重複トピック除外。

## 実装ポイント
### モジュール構成
- **`src/script_io.py`**: YAML/JSONロード、pydantic検証。
- **`src/script_generation/`**: LLM台本生成。`generator.py` (ブリーフ→台本)、`llm.py` (プロバイダ抽象化+JSON修正ロジック)。
- **`src/assets/`**: 素材取得。`pipeline.py` (検索→ダウンロード→キャッシュ)、`clients.py` (Pexels/Pixabay API)。
- **`src/audio/voicevox_client.py`**: 音声合成APIラッパー。タイムアウト/リトライ対応。
- **`src/timeline.py`**: セクションの開始時刻・継続時間を計算。音声なしの場合はテキスト長から推定。
- **`src/render/ffmpeg_runner.py`**: FFmpegコマンド生成。**フォント名→システムフォントパス解決** (`_resolve_font_path()` 関数でfc-match呼出し、macOSはヒラギノにフォールバック)。
- **`src/outputs.py`**: SRT字幕、メタJSON、サムネイル出力。

### 主要CLI
| スクリプト | 役割 |
|---|---|
| `generate_video.py` | 台本→動画の全パイプライン実行 |
| `generate_script_from_brief.py` | LLMでYAML台本生成 |
| `fetch_trend_ideas_llm.py` | トレンドアイデアJSON取得 |
| `scheduler_daemon.py` | 定期実行デーモン |
| `youtube_upload.py` | YouTube自動投稿 |
| `batch_render.py` | 複数台本を一括レンダ |
| `adjust_tickers.py` | テロップ幅を事前調整 |
| `render_snapshot.py` | 1フレームPNGでテロップ確認 |

### 設定ファイル
- `configs/config.yaml`: FFmpegパス、VOICEVOX URL、作業ディレクトリ。
- `settings/ai_settings.json`: LLM APIキー、プロバイダ選択、温度パラメータ、素材APIキー。
- `settings/schedule.json`: スケジューラー設定（インターバル、最大件数、カテゴリ、ショート指定）。
- `configs/themes/<theme_id>/theme.yaml`: テーマ別の配色・フォント・サムネイル設定。
- `configs/text_layouts.yaml`: テロップ位置レイアウト定義 (`top_center`, `middle_center` 等)。

### データ構造
- **ScriptModel**: `project`, `title`, `video` (width/height/fps/bg), `voice` (engine/speaker_id), `sections[]`, `output`, `upload_prep?`。
- **Section**: `id`, `narration`, `on_screen_text`, `on_screen_segments[]` (スタイル指定)、`bg_keyword`, `effects[]`。
- **SectionTimeline**: `id`, `start_sec`, `duration_sec`, `audio_path`。

### テロップ調整の仕組み
- デフォルトフォント: Noto Sans JP / 64pt（未指定時に自動補完）。
- フォント解決: `_resolve_font_path()` がfc-matchでシステムフォントパスに変換。macOSは `/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc` にフォールバック。
- 幅調整: `scripts/adjust_tickers.py` がPillowで文字幅計測→改行/縮小。
- ショート対応: `_short_scale` で座標とフォントサイズを縮小。

### YouTube投稿の仕組み
- OAuth認証: `client_secrets.json` と `youtube_credentials.pickle` を使用。
- アップロード: `scripts/youtube_upload.py` が `upload_prep` の title/desc/tags を参照。
- サムネイル: タイトル入りPNGを自動生成して添付。
- トークン期限: 認証テスト失敗時はトークン削除→再認証が必要。

## 運用・落とし穴
### よくある失敗
1. **VOICEVOX未起動**: 音声生成で Connection refused → 事前に `Start_VoicevoxEngine.command` 実行。エンジン起動確認を先に行う。
2. **APIキー未設定**: Pexels/Pixabay/LLMキーが空だと素材取得/台本生成が失敗 → `.env` または `settings/ai_settings.json` で設定。
3. **フォント名を直接指定**: FFmpegがフォント名を認識できず文字化け → `_resolve_font_path()` で自動解決済み（macOSはヒラギノにフォールバック）。
4. **音声キャッシュ残存**: 同一台本を再生成すると古い音声を使い回す → `--clear-audio` で削除。
5. **YouTube OAuth期限切れ**: 初回認証から一定期間後に再認証必要 → UIの「認証テスト」で確認、失敗時は「トークン削除」→再認証。
6. **Pixabay 400エラー**: クエリが長い/日本語含有で失敗することが多い。Pexels優先やクエリ短縮が必要。
7. **テロップはみ出し**: 縦動画で長文だと依然リスク。`--adjust-tickers` ONで再生成し、`render_snapshot.py` で事前確認が推奨。
8. **映像が真っ黒**: 背景素材パスが間違っている → `ensure_background_assets()` で自動補完を有効化。
9. **テロップ位置ズレ**: `text_layout` 設定を確認 → `configs/text_layouts.yaml` で `top_center` 等を調整。
10. **BGMが大きすぎ**: `bgm.ducking.amount` を増やす（例: 0.7 → 0.85）。

### 推奨運用
- デスクトップアプリで台本を編集し、プレビューで確認。確定後にCLIでバッチレンダ。
- スケジューラーは夜間に1日分を一括生成。YouTube投稿は手動レビュー後に実行（自動投稿は任意）。
- 素材キャッシュは定期削除（容量節約）。`assets/cache/` を週次でクリーンアップ。
- LLMのトークン使用量を監視。月次で上限チェック。
- 同時実行数は低めに設定（アップロード制限/背景衝突回避）。

### デバッグ手順
1. `render_snapshot.py` でテロップレイアウト確認。
2. `--dry-run` でFFmpegコマンドを出力し、手動実行でエラー箇所を特定。
3. `--clear-audio` で音声キャッシュをクリアし、最新音声で再生成。
4. VOICEVOXログ (`tools/voicevox_engine/logs/`) を確認。

## 参考
- **内部ドキュメント**:
  - [design.md](design.md): アーキテクチャ詳細
  - [media_pipeline_spec.md](media_pipeline_spec.md): 素材取得・サムネイル生成
  - [script_template_spec.md](script_template_spec.md): YAML台本スキーマ
  - [llm_trend_pipeline.md](llm_trend_pipeline.md): LLMトレンド生成仕様
  - [deepwiki_generation_instruction.md](deepwiki_generation_instruction.md): ドキュメント生成指示書
- **外部リンク**:
  - VOICEVOX公式: https://voicevox.hiroshiba.jp/
  - Pexels API: https://www.pexels.com/api/
  - Pixabay API: https://pixabay.com/api/docs/

## 追記/更新ログ
- 2025-12-23: 全面改訂。フォント解決システム、プレビューウィンドウ、YouTube認証修正を反映。DeepWiki風フォーマットに統一。
- 設計書（現行正本）: `docs/設計書.md`
- テロップ調整: `scripts/adjust_tickers.py`, `src/render/ffmpeg_runner.py`
- 自動生成パイプライン: `scripts/auto_trend_pipeline.py`, `scripts/generate_video.py`, `scripts/generate_script_from_brief.py`
- プレビュー: `scripts/render_snapshot.py`
- YouTubeアップロード: `scripts/youtube_upload.py`
- 背景/BGMログ確認: `logs/scheduler/*.log`, `outputs/rendered/*.json`

## 追記/更新ログ
- 2025-12-23: DeepWikiスタイルで現状仕様を整理。テロップ調整とショート対応の要点を明文化。
