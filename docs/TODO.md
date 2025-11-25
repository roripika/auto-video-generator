# Auto Explainer Video Generator — TODO

## High Priority (Week 1)
- [x] Define pydantic models for config/script YAML (`src/models.py`).
- [x] Implement VOICEVOX API client with retry + caching (`src/audio/voicevox_client.py`).
- [x] Prototype `generate_audio.py` that loads YAML and sequentially calls VOICEVOX (音声だけ生成して work/audio に保存）。

## Medium Priority
- [x] Timeline builder: compute section durations based on WAV lengths + pause settings (`src/timeline.py`).
- [x] FFmpeg command template for背景+テロップ+ウォーターマーク (`src/render/ffmpeg_runner.py`)。
- [x] SRT generator and metadata writer (`src/outputs.py`)。
- [x] Batch renderer CLI (`scripts/batch_render.py`) が glob で複数 YAML を処理。
- [x] Mac 向け `Setup.command` / `RunVoicevoxGUI.command` のような環境整備スクリプトを用意し、依存ツール (VOICEVOX, FFmpeg) の導入手順を自動化する。
- [x] 台本(YAML)の入力・編集・セクション調整を行えるデスクトップ（Electron ベース）UI を設計・実装し、CLI だけでなくウインドウアプリから編集できるようにする。
- [x] 自然文や箇条書きから YAML 台本を AI で自動生成するユーティリティ（CLI or UI）を実装し、手動整備の負荷を減らす (`scripts/generate_script_from_brief.py`)。
- [x] テーマ／ジャンル／ランキング項目数を管理する「企画テンプレート」モジュールを実装し、動画ごとに切り口・ターゲット・CTA を保存できるようにする (`src/themes.py`, `configs/themes/`).
- [x] 科学的根拠・ブリッジ文・CTA を差し込む台本テンプレ機能を YAML スキーマ／AI プロンプトに追加し、ライフハック構成（フック→根拠→実演）を自動化する (`src/models.py`, `docs/script_template_spec.md`).
- [x] フリー素材サイト検索や AI 画像生成を含む「背景／アイコン素材取得パイプライン」を設計・実装する。
- [x] サムネイル自動生成スクリプトを追加し、驚きを与えるコピーやランキング要素をテンプレ化する。

## Low Priority / Future
- [ ] Ken Burns 風ズームのプリセット作成。
- [ ] マルチ音声エンジン対応（COEIROINK 等）。※ペンディング
- [ ] GUI や web フロントの検討。
- [ ] **自動トレンド→動画→YouTube投稿パイプライン**: Google Trends 定期監視→トレンドワードからアイデア生成→AI台本→動画生成→YouTubeアップロードまでのフル自動ジョブを設計・実装する（Scheduler/キュー、API鍵管理、失敗リトライ、アップロードスクリプト含む）。

## Next Phase (Automation & QA)
- [x] `scripts/generate_video.py` で ScriptModel → VOICEVOX → Timeline → FFmpeg → SRT/metadata を一括実行する orchestrator を実装し、`scripts/batch_render.py` がこの CLI を呼ぶだけで完パケを書き出せるようにする。
- [x] `src/render/ffmpeg_runner.py` を拡張し、BGM トラック（ループ＋ducking）、`watermark` オーバーレイ、`credits` の描画/フェードアウトを ScriptModel の設定値から自動反映できるようにする。
- [x] テーマ ID やセクションのキーワードから `AssetFetcher` を呼び出して背景素材を自動選定し、キャッシュメタ情報を `metadata.json` に同梱するパイプライン（背景未指定時のフォールバック）を追加する。
- [x] `upload_prep`（title/tags/desc）を `outputs/upload/` に書き出すエクスポータを実装し、YouTube への手動アップロードがコピペで済む形に整える（CTA/ハッシュタグのテンプレも差し込み）。
- [ ] `desktop-app` に AI フック（自然文→YAML、ブリッジ文自動生成、Monaco diff ビュー）を実装し、セクションのドラッグ並べ替えと連動して `script_editor_spec.md` の要件を満たす。
- [x] pytest ベースの最小テストスイートを用意し、`src/timeline.py`, `src/outputs.py`, `src/assets/pipeline.py` など副作用の少ないモジュールから順に回帰テストを整備する（サンプル YAML/ダミー WAV を fixtures 化）。
- [ ] **UI統合ロードマップ（現状/残タスクを整理）**
  - [x] LLM パネル: デスクトップアプリから自然文ブリーフ→`scripts/generate_script_from_brief.py` を IPC 呼び出し（renderer/main 実装済み）。
  - [x] 背景素材 UI: キーワード入力→AssetFetcher 実行→結果リストから背景に適用（renderer/main 実装済み）。
  - [x] テキストスタイル UI: フォント/サイズ/色/ストローク/位置/アニメーションを編集して ScriptModel に反映（renderer 実装済み）。
  - [x] 音声生成＋タイムライン: VOICEVOX 合成を UI から実行し、`describe_timeline` で尺要約を表示（renderer/main 実装済み、波形プレビューは未対応）。
  - [x] 動画生成 UI: `scripts/generate_video.py` を IPC で起動し、ログと生成ファイルのオープンボタンを提供（renderer/main 実装済み）。
  - [x] BGM/YouTube 設定共有: デスクトップアプリの設定画面に YouTube API Key / BGM ディレクトリを追加し、CLI (`scripts/generate_video.py`) からも `settings/ai_settings.json` を読み込んで共通設定を再利用できるようにした（2025-11-22）。
  - [x] スクリプト保存ダイアログ: タイトル/プロジェクト名を既定ファイル名として提案し、保存時の手入力を省略できるようにした（2025-11-22）。
  - [x] 保存操作の分離: メイン画面に「保存（上書き）」と「別名で保存」ボタンを分離し、2回目以降でも新しい保存先をダイアログから選べるようにした（2025-11-22）。
  - [ ] ハイライト再生: キーワード検索で該当文言をハイライトし、その音声を即時再生する UI を追加。
  - [ ] 内部プレビュー: 生成動画/SRT をアプリ内で再生・確認するビュー（もしくは簡易プレイヤー埋め込み）を追加。
  - [ ] タイムライン強化: WAV 波形/セクション単位の尺調整 UI、pause 可視化などを追加。
  - [ ] 背景素材検索の別ウインドウ化: FullHDノート環境でメイン＋サブが並ぶ 900x700 目安のウインドウを新設し、プレビュー＋「全体/セクションに適用」ボタンを備える。
  - [ ] **BGM 設定 UI**: 設定画面に BGM ファイル選択＋音量(dB)＋ナレーション時の ducking(dB)スライダーを追加し、YAML の `bgm` を編集・保存できるようにする。ライセンス表記が必要な場合は `credits.text` に追記する UX を提示。
  - [ ] **AI台本でBGM候補も生成**: プロンプトに BGM（ジャンル/ムード/ファイル案）、音量(dB)、ducking(dB)、ライセンスメモを書かせ、生成結果をYAML `bgm`に反映する。

## Notes
- 進行中のタスクは Git issue / branch と紐付けて更新。
- 完了した項目は日付付きで別セクションへ移す予定。
