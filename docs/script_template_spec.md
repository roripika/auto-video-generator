# Script Template Specification (ライフハック動画向け)

## Section structure
Each section in YAML should include the following fields (aligned with `src/models.Section`):

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
    on_screen_segments:
      - text: "第5位："
        style: { fontsize: 96, fill: "#FFE65A", stroke: { color: "#000000", width: 6 } }
      - text: "○○の神ワザ\n要点キーワード"
        style: { fontsize: 64, fill: "#FFFFFF", stroke: { color: "#000000", width: 6 } }
    text_layout: "hero_center"   # hero_center | hero_middle | lower_third | side_left | side_right
    narration: "…"
    effects:
      - blur
      - grayscale
    bg_keyword: "背景検索に使う短いキーワード（10〜30文字）"
    overlays:
      - file: "overlays/product.png"
        position: { x: "right-120", y: "center" }
        scale: 0.6
```

- `hook`: 問題提示・共感を引き出す一言。
- `evidence`: 根拠・データ・専門家コメント。
- `demo`: 実演・ビフォーアフター説明。
- `bridge`: 次の順位への繋ぎ。
- `cta`: セクション単位の行動喚起（任意）。
- `effects`: シーンごとに適用する画面効果（例: `blur`, `grayscale`, `vignette`, `contrast`, `zoom_in`, `zoom_out`, `zoom_pan_left`, `zoom_pan_right`）。複数指定可。
- `on_screen_segments`: テロップを強調語ごとに分割し、色・サイズ・フォント等を調整するための配列。
- `text_layout`: テロップ位置のテンプレ指定。ヒーロー中央/下部/左右などのレイアウトを選択。
- `bg_keyword`: 背景素材検索に使う短いキーワード。各セクションに1つ以上設定推奨。
- `overlays`: 画像の重ね合わせ（商品写真/図版等）。`file`/`position`/`scale`/`opacity` などを指定。

## AI prompt guidance
When generating scripts via AI, ensure the prompt explicitly instructs the model to fill these subfields. Example instruction snippet:

```
For each ranking item, output hook/evidence/demo/bridge/cta/bg_keyword as separate fields.
Use on_screen_segments to split highlighted text lines and set contrasting styles.
```

## CTA templates
- コメント誘導: "コメントでお気に入りのハックを教えてください！"
- 登録誘導: "次回のハックも見逃さないようチャンネル登録を！"

この仕様を YAML スキーマと AI プロンプトに反映し、台本の一貫性を保ちます。
