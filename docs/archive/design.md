# Auto Explainer Video Generator — Architecture

最終更新: 2025-12-20

## 1. System Overview
- CLI ツールが YAML/JSON 台本 + 設定を読み込み、各工程（素材補完→音声生成→タイムライン計算→映像合成→SRT/メタ書き出し）を順番に実行する。
- Python 3.10+ をコアとし、外部コンポーネントとして VOICEVOX Web API と FFmpeg を利用。
- `scripts/` 配下に CLI 群（`generate_video.py`, `batch_render.py`, `generate_audio.py`, `generate_script_from_brief.py` など）を配置、`src/` に共通モジュールを集約。
- Electron デスクトップアプリ（`desktop-app/`）と Stepdocs 自動記録（`stepdocs/`）で UI 操作の再現とガイド生成を補助。

## 2. Module Breakdown
1. **Script I/O (`src/script_io.py`)**
   - 台本/設定のロード（YAML/JSON）と pydantic モデルへの変換。`ScriptModel`/`ConfigModel` 検証。
2. **LLM Script Generation (`src/script_generation/`)**
   - `generator.py`: ブリーフから台本ペイロードを生成。
   - `llm.py`: プロバイダ非依存クライアントと `generate_and_validate()`（厳密JSON＋救済＋リトライ）。
   - `prompt_templates.py` / `response_validator.py` / `schemas.py` / `logging_utils.py`: JSON専用テンプレ、パース救済、簡易スキーマ、最小ログ化。
3. **Assets Pipeline (`src/assets/`)**
   - `pipeline.py`: Pexels/Pixabay 検索・ダウンロード・キャッシュ管理。
   - `clients.py` / `generators.py` / `types.py`: APIクライアントと生成系ユーティリティ。
4. **Audio Engine (`src/audio/voicevox_client.py`)**
   - VOICEVOX API ラッパー、音声合成、WAV保存。
5. **Timeline (`src/timeline.py`)**
   - セクションごとの開始/終了時刻計算。音声長がない場合はテキスト長から推定。
6. **Renderer (`src/render/ffmpeg_runner.py`)**
   - 背景のループ/ズームパン、テロップ描画、BGMダッキングを含む FFmpeg コマンド生成。
7. **Outputs (`src/outputs.py`)**
   - SRT, メタ JSON の書き出し、サムネイル抽出。
8. **CLI Orchestration (`scripts/`)**
   - `generate_video.py`: 素材補完→音声→タイムライン→レンダ→出力の一括実行。`ensure_background_assets()` / `ensure_bgm_track()` を備える。
   - `generate_script_from_brief.py`: LLM で台本生成。
   - `fetch_trend_ideas_llm.py`: トレンド案の収集（厳密JSONラッパー経由）。
9. **Desktop App & Stepdocs**
   - Electron（`desktop-app/src`）の UI 操作を Stepdocs（`stepdocs/`）で自動記録し、ガイド Markdown（`docs/stepdocs/基本操作ガイド_自動生成.md`）を生成。

## 3. Execution Flow
1. Config + Script 読み込み → モデル変換（`src/script_io.py`）。
2. 素材補完: 背景/セクション素材の自動取得（`ensure_background_assets`）。BGM のローカル候補探索（`ensure_bgm_track`）。
3. 音声生成: sections の narration を順次 WAV 化（`src/audio/voicevox_client.py`）。
4. タイムライン計算: 音声長/テキストから各セクションの秒数を確定（`src/timeline.py`）。
5. FFmpeg 合成: 背景／テロップ／BGM／ダッキングを一括実行（`src/render/ffmpeg_runner.py`）。
6. 出力: SRT + metadata + thumbnail を出力（`src/outputs.py`）。

## 4. Data Contracts
- `ScriptModel`: `project`, `title`, `video`, `voice`, `text_style`, `bgm?`, `watermark?`, `credits?`, `sections[]`, `output`, `upload_prep?`。
- `Section`: `id`, `on_screen_text`, `on_screen_segments[]?`, `text_layout?`, `overlays[]?`, `narration`, `duration_hint_sec?`, `bg?`, `bg_keyword?`, `hook?`, `evidence?`, `demo?`, `bridge?`, `cta?`, `effects[]?`。
- `SectionTimeline`: `{ id, index, start_sec, duration_sec, on_screen_text, narration, audio_path? }`。

## 5. External Dependencies
- **VOICEVOX**: `audio_query`, `synthesis` API。タイムアウト/リトライを `ConfigModel` で制御。
- **FFmpeg**: version >= 6.0。`zoompan`, `drawtext`, `sidechaincompress` 使用。
- **Pexels/Pixabay**: 背景素材検索用 API キー（環境変数または `settings/ai_settings.json`）。

## 6. Risks & Open Questions
- 素材不足時のフォールバック（デフォルト背景/フォント）とライセンス表記の一貫性。
- 複数音声エンジン対応の抽象化。
- Mac/Win でのフォントパス差異対応。
- LLM 出力の逸脱時救済のテレメトリ（失敗ログの自動要因分析）。

## 7. Next Architecture Steps
- `generate_and_validate` のスキーマ拡充と運用設定化（リトライ/バックオフ）。
- 素材取得のキーワードサニタイズ強化（Pixabay/Pexels 400回避）。
- Stepdocs のシナリオ拡充と UI ガイドの定期再生成。
