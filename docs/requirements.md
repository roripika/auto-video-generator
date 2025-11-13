# Requirements Draft

## Goal
Automatically generate concise explainer videos from structured inputs (Markdown scripts, bullet lists, or API data) by chaining text processing, narration, and visual assembly.

## Functional highlights
- Input ingestion: accept Markdown, outline JSON, or prompt-based topics.
- Script enrichment: add hooks for glossary, call-to-action, or references.
- Narration: select a TTS voice, control pacing, inject pauses.
- Visuals: auto-generate slides or motion cards with titles, bullet points, and supporting imagery.
- Assembly: combine narration, background music, and visuals into MP4 output.
- Export presets: social square, vertical short, widescreen.

## Open questions
1. Which rendering engine to start with (ffmpeg overlays, Remotion, custom canvas)?
2. Do we need live-preview or is batch rendering sufficient for MVP?
3. How to manage licensed assets (music/fonts/backgrounds)?
4. Desired hosting/usage model (local CLI vs. web service).

Iterate on this document before locking down architecture.
