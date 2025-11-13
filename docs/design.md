# Auto Explainer Video Generator — Architecture Draft

最終更新: 2025-11-12

## 1. System Overview
- CLI ツールが YAML 台本 + config を読み込み、各工程（音声生成→映像合成→SRT/メタ書き出し）を順番に実行する。
- Python 3.10+ をコアとし、外部コマンドとして VOICEVOX Web API と FFmpeg を呼び出す。
- `scripts/` 配下に CLI (`generate_video.py`, `batch_render.py`) を配置、`src/` に共通モジュールをまとめる。

## 2. Module Breakdown
1. **Script Loader (`src/scripts_loader.py`)**
   - YAML バリデーション (PyYAML + pydantic) とセクション整形。
2. **Audio Engine (`src/audio/voicevox_client.py`)**
   - VOICEVOX API wrapper、音声キャッシュ、無音挿入ヘルパー。
3. **Timeline Builder (`src/timeline.py`)**
   - セクションごとの開始/終了時刻、テキストイベント、BGM ダッキングトラックを計算。
4. **Renderer (`src/render/ffmpeg_runner.py`)**
   - 背景ソースのループ/拡大処理、テロップ描画、ウォーターマーク配置を行う FFmpeg コマンドを生成。
5. **Outputs (`src/outputs.py`)**
   - SRT, メタ JSON, サムネイル抽出、ログまとめ。
6. **CLI (`scripts/generate_video.py`)**
   - 上記モジュールを orchestration。

## 3. Execution Flow
1. Config + Script 読み込み → モデル変換。
2. 音声生成: sections の narration を順次 WAV 化し `work/audio/{idx}_{id}.wav` へ保存。
3. タイムライン計算: 各セクションの予定秒数（音声長 + 余白）を決定。
4. FFmpeg フィルタ構築: 背景／テロップ／BGM／サイドチェイン圧縮を一括実行。
5. 生成後: SRT + metadata + thumbnail を出力。

## 4. Data Contracts
- `ScriptModel`: project/title/video/voice/.../sections[].
- `SectionTimeline`: {id, duration_sec, narration_wav, on_screen_text, start_sec}.
- `RenderContext`: {video_size, font_paths, overlay_paths, bg_asset, bg_mode, credits}.

## 5. External Dependencies
- **VOICEVOX**: `audio_query`, `synthesis` API。タイムアウト/リトライ設定を `config` で受け取る。
- **FFmpeg**: version >= 6.0。`zoompan`, `drawtext`, `sidechaincompress` 使用。

## 6. Risks & Open Questions
- 素材不足時のフォールバック方針（デフォルト背景/フォント）。
- 複数音声エンジン対応の抽象化インターフェース。
- Mac/Win でのフォントパス相違への対処。

## 7. Next Architecture Steps
- pydantic モデル定義とサンプル YAML での検証。
- VOICEVOX クライアントの試験実装（1 セクション音声変換）。
- FFmpeg コマンドのテンプレート化（Jinja2 もしくは Python 組み立て）。
