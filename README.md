# Auto Explainer Video Generator

This repository contains the groundwork for a new tool that automatically produces explainer-style videos from structured content. The initial milestones focus on defining requirements, planning the pipeline (script authoring → narration → visuals → editing), and setting up the development environment.

## Repository layout

```
auto-video-generator/
├── docs/        # Specifications, research notes, mockups
├── src/         # Application source code (to be populated)
├── scripts/     # Helper scripts for setup, builds, etc.
└── README.md    # Project overview
```

## Next steps

1. Draft high-level requirements in `docs/requirements.md`.
2. Outline the media-generation pipeline and required external services.
3. Decide on the tech stack for narration (TTS), motion graphics, and final compositing.
4. Prototype a minimal CLI that converts a markdown script into a narrated slideshow video.

Feel free to adapt this structure as the project evolves.

## Reference Policy

- 外部プロジェクト（例: `voicevox-storycaster`）は **参照のみ** とし、分析結果をこのリポジトリへ反映する形で活用します。
- これら外部リポジトリを直接編集したり PR を送ることは行いません。必要な変更は常に本リポジトリ内で独自実装してください。
