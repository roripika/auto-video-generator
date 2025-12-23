# Script Editing UI — Concept

## Goals
- Electron などを用いたウインドウ型アプリとして YAML エディタを提供し、ランキング構成・トーン・CTA を一体化する。
- テーマ／ジャンル設定、セクション調整、AI 自動生成のトリガーをひとまとめにする。

## Features
1. **Theme & Ranking panel**: ジャンル、切り口、アイテム数、CTA テンプレを入力。ライフハックの驚きワードもここで管理。
2. **Section list sidebar**: 順位・タイトルを表示し、ドラッグで並べ替え。
3. **Section form**: `hook / evidence / demo / bridge` といったサブフィールドに分割し、語尾・トーンのプリセットを適用。
4. **Preview pane**: タイムライン、想定総尺、CTA の確認。ランキングのサマリーカードを表示。
5. **YAML diff view**: 生成済み YAML と編集中差分を比較。
6. **AI hooks**: ボタン1つで「自然文→YAML 変換」「ブリッジ文自動生成」「サムネコピー案生成」を呼び出す。

## Tech stack (proposal)
- Electron + React (既存コンポーネントを流用)。
- State management via Zustand or Redux Toolkit.
- Monaco editor for raw YAML edits.
- IPC/ローカル API (`GET/PUT /scripts/{id}` 相当) で CLI モジュールと連携。

## Next steps
- Build wireframes (Figma or markdown sketches)。特にランキングエディタとプレビューを明確化。
- Define API contracts (`/scripts`, `/themes`, `/ai/generate-script`).
- Implement minimal editor with theme panel + section forms + diff view。

## Implementation snapshot (2024-11)
- `desktop-app/` に Electron ベースの最小 UI を追加。テーマ選択、新規 YAML 生成、セクション編集、YAML プレビュー、ファイル保存/読込が可能。
- まだ React/Monaco ではなく素の DOM 実装だが、`ScriptModel` とテーマテンプレをそのまま扱えるため CLI と互換性がある。
- 今後は AI 生成フック、ドラッグによる並べ替え、Monaco による diff 表示を統合する。
