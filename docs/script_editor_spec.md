# Script Editing UI — Concept

## Goals
- Provide a browser-based editor for YAML scripts (sections, voice, styles) with live preview.
- Allow users to import/export YAML, duplicate sections, adjust narration text, and preview estimated duration.

## Features
1. **Section list sidebar**: reorder, add, remove sections.
2. **Section form**: fields for `on_screen_text`, `narration`, duration hint.
3. **Preview pane**: render timeline summary + KPIs.
4. **YAML diff view**: show generated YAML compared to last saved version.
5. **Integration hooks**: button to call AI YAML generator (future task).

## Tech stack (proposal)
- React + Vite (reuse existing stack).
- State management via TanStack Query or Zustand.
- Monaco editor for raw YAML edits.
- API endpoints: `GET/PUT /scripts/{id}`.

## Next steps
- Build wireframes (Figma or markdown sketches).
- Define API contracts for saving drafts.
- Implement minimal editor with section list + forms.
