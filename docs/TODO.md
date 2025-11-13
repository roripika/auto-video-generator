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
- [ ] 台本(YAML)の入力・編集・セクション調整を行えるデスクトップ（Electron ベース）UI を設計・実装し、CLI だけでなくウインドウアプリから編集できるようにする。
- [ ] 自然文や箇条書きから YAML 台本を AI で自動生成するユーティリティ（CLI or UI）を実装し、手動整備の負荷を減らす。
- [ ] テーマ／ジャンル／ランキング項目数を管理する「企画テンプレート」モジュールを実装し、動画ごとに切り口・ターゲット・CTA を保存できるようにする。
- [ ] 科学的根拠・ブリッジ文・CTA を差し込む台本テンプレ機能を YAML スキーマ／AI プロンプトに追加し、ライフハック構成（フック→根拠→実演）を自動化する。
- [ ] フリー素材サイト検索や AI 画像生成を含む「背景／アイコン素材取得パイプライン」を設計・実装する。
- [ ] サムネイル自動生成スクリプトを追加し、驚きを与えるコピーやランキング要素をテンプレ化する。

## Low Priority / Future
- [ ] Ken Burns 風ズームのプリセット作成。
- [ ] マルチ音声エンジン対応（COEIROINK 等）。
- [ ] GUI や web フロントの検討。

## Notes
- 進行中のタスクは Git issue / branch と紐付けて更新。
- 完了した項目は日付付きで別セクションへ移す予定。
