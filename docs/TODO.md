# Auto Explainer Video Generator — TODO

## High Priority (Week 1)
- [x] Define pydantic models for config/script YAML (`src/models.py`).
- [x] Implement VOICEVOX API client with retry + caching (`src/audio/voicevox_client.py`).
- [x] Prototype `generate_audio.py` that loads YAML and sequentially calls VOICEVOX (音声だけ生成して work/audio に保存）。

## Medium Priority
- [x] Timeline builder: compute section durations based on WAV lengths + pause settings (`src/timeline.py`).
- [ ] FFmpeg command template for背景+テロップ+ウォーターマーク。
- [ ] SRT generator and metadata writer。
- [ ] Batch renderer CLI (`scripts/batch_render.py`) が glob で複数 YAML を処理。
- [ ] Mac 向け `Setup.command` / `RunVoicevoxGUI.command` のような環境整備スクリプトを用意し、依存ツール (VOICEVOX, FFmpeg) の導入手順を自動化する。
- [ ] 台本(YAML)の入力・編集・セクション調整を行える UI 画面を設計・実装し、CLI だけでなくブラウザから台本を編集できるようにする。
- [ ] 自然文や箇条書きから YAML 台本を AI で自動生成するユーティリティ（CLI or UI）を実装し、手動整備の負荷を減らす。

## Low Priority / Future
- [ ] Ken Burns 風ズームのプリセット作成。
- [ ] マルチ音声エンジン対応（COEIROINK 等）。
- [ ] GUI や web フロントの検討。

## Notes
- 進行中のタスクは Git issue / branch と紐付けて更新。
- 完了した項目は日付付きで別セクションへ移す予定。
