# Script Template Specification (ライフハック動画向け)

## Section structure
Each section in YAML should include the following fields:

```yaml
sections:
  - id: point1
    title: "第5位: ○○"
    hook: "いつも○○していませんか？"
    evidence: "○○研究所のデータによると…"
    demo: "実際に○○をやってみると…"
    bridge: "次はもっと意外な○○です"
    cta: "コメント欄で試した感想を教えてください"
    on_screen_text: "○○の神ワザ"
    narration: "…"
    effects:
      - blur
      - grayscale
```

- `hook`: 問題提示・共感を引き出す一言。
- `evidence`: 根拠・データ・専門家コメント。
- `demo`: 実演・ビフォーアフター説明。
- `bridge`: 次の順位への繋ぎ。
- `cta`: セクション単位の行動喚起（任意）。
- `effects`: シーンごとに適用する画面効果（例: `blur`, `grayscale`, `vignette`, `contrast`, `zoom_in`, `zoom_out`, `zoom_pan_left`, `zoom_pan_right`）。複数指定可。

## AI prompt guidance
When generating scripts via AI, ensure the prompt explicitly instructs the model to fill these subfields. Example instruction snippet:

```
For each ranking item, output hook/evidence/demo/bridge/cta as separate fields.
```

## CTA templates
- コメント誘導: "コメントでお気に入りのハックを教えてください！"
- 登録誘導: "次回のハックも見逃さないようチャンネル登録を！"

この仕様を YAML スキーマと AI プロンプトに反映し、台本の一貫性を保ちます。
