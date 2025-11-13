# Auto Explainer Video Generator — TODO

## High Priority (Week 1)
- [ ] Define pydantic models for config/script YAML (`src/models.py`).
- [ ] Implement VOICEVOX API client with retry + caching (`src/audio/voicevox_client.py`).
- [ ] Prototype `generate_video.py` that loads YAML and sequentially calls VOICEVOX (音声だけ生成して work/audio に保存）。

## Medium Priority
- [ ] Timeline builder: compute section durations based on WAV lengths + pause settings.
- [ ] FFmpeg command template for背景+テロップ+ウォーターマーク。
- [ ] SRT generator and metadata writer。
- [ ] Batch renderer CLI (`scripts/batch_render.py`) が glob で複数 YAML を処理。

## Low Priority / Future
- [ ] Ken Burns 風ズームのプリセット作成。
- [ ] マルチ音声エンジン対応（COEIROINK 等）。
- [ ] GUI や web フロントの検討。

## Notes
- 進行中のタスクは Git issue / branch と紐付けて更新。
- 完了した項目は日付付きで別セクションへ移す予定。
