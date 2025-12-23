# 自動解説動画ジェネレーター（VOICEVOX）要件定義_v1

最終更新: 2025-12-20 (JST)
作成目的: Codex(エージェント)が実装を進めやすいように、要件・仕様・入出力・設計方針を明確化する。

---
## 0. ゴール/非ゴール
- **ゴール**: テキスト台本(YAML/JSON)と定義済み素材を入力し、VOICEVOXナレーション + 背景映像/画像 + テロップ + BGM を自動合成したショート〜ロング解説動画(MP4)を大量生成できること。
- **非ゴール**: 高度なモーショングラフィックス、人物の口パク同期、AIアバター合成、GUIエディタの提供。

---
## 1. 想定ユースケース
- 社会/地域/テック解説のショート動画量産 (60–120秒)。
- 長尺の章立て解説 (5–10分、セクション分割)。
- 同一テーマの言い換えバリエーション出力。

---
## 2. 入出力定義
### 2.1 入力
1) **台本ファイル** (`scripts_yaml/*.yaml`)
- 構成、読み上げテキスト、画面テキスト、装飾(色/位置/フォント)、セクション長目安、BGM/SE指示。
2) **素材**
- 背景: ループ動画(MP4) or 画像(PNG/JPG)。
- BGM/SE: WAV/MP3(ライセンス明示)。
- フォント: TTF/OTF。
3) **設定** (`config.yaml`)
- 解像度・fps、音量バランス、テロップスタイル、VOICEVOXキャラ/話速/抑揚、クレジット表記、出力先など。

### 2.2 出力
- `outputs/rendered/<project>/<timestamp>/final.mp4`
- 付随: `final.srt`(字幕), `final.json`(メタ情報), `thumb.png`(サムネ候補)。

---
## 3. 依存コンポーネント/前提
- **VOICEVOX**: ローカルAPIが有効 (`http://localhost:50021`).
- **FFmpeg**: CLI 利用可能。
- **Python 3.10+**: orchestration スクリプト。主要ライブラリ: `PyYAML`, `pydub`(任意), `moviepy`(任意), `jinja2`(任意)。
- OS: macOS / Linux を想定 (Windows可)。

---
## 4. ディレクトリ構成 (推奨)
```
video_generator/
├─ scripts/                 # 実行スクリプト
├─ configs/
│   └─ config.yaml
├─ inputs/
│   ├─ scripts_yaml/        # 台本(YAML)
│   ├─ bg_materials/        # 背景(動画/画像)
│   ├─ bgm/
│   ├─ fonts/
│   └─ overlays/            # ロゴ/透かし等
├─ work/                    # 中間生成(WAV, 章ごとのMP4等)
└─ outputs/
    └─ rendered/
```

---
## 5. YAML台本スキーマ(初版)
```yaml
project: "aichi_it_analysis_01"
title: "愛知のイノベーションはどこにある？"
locale: "ja-JP"
video:
  width: 1920
  height: 1080
  fps: 30
  bg: "bg_materials/ai_loop01.mp4"   # 画像ならPNG
  bg_fit: "cover"                     # cover|contain|stretch
voice:
  engine: "voicevox"
  speaker_id: 1                        # 例: 青山龍星のID(実体に合わせる)
  speedScale: 1.05
  pitchScale: 0.0
  intonationScale: 1.1
  volumeScale: 1.0
  pause_msec: 250                      # セクション間ポーズ
text_style:
  font: "fonts/NotoSansJP-Regular.otf"
  fontsize: 54
  fill: "#FFFFFF"
  stroke: { color: "#000000", width: 3 }
  position: { x: "center", y: "bottom-160" }
  max_chars_per_line: 22
  lines: 3
bgm:
  file: "bgm/light_tech_60.mp3"
  volume_db: -16
  ducking_db: -6                        # ナレーション時にBGMを自動で下げる
watermark:
  file: "overlays/logo.png"
  position: { x: "right-40", y: "top+40" }
credits:
  enabled: true
  text: "VOICEVOX: 青山龍星"
  position: { x: "left+40", y: "bottom-40" }
sections:
  - id: intro
    on_screen_text: "愛知の産業×イノベーション"
    narration: "今回は、愛知県の産業集積とイノベーションの関係を見ていきます。"
    duration_hint_sec: 6
  - id: point1
    on_screen_text: "製造業の集積 ≠ IT給与の高さ"
    narration: "自動車を中心に大手が多い一方、IT給与は東京等より控えめというデータがあります。"
  - id: point2
    on_screen_text: "スタートアップは福岡型？"
    narration: "起業土壌や支援制度は地域で差があり、福岡はスタートアップ比率が高い傾向です。"
  - id: summary
    on_screen_text: "集積の強みをDXで拡張"
    narration: "製造×ITの横断で新価値を生む余地があり、愛知独自のイノベーションが鍵になります。"
output:
  filename: "aichi_innovation_v1.mp4"
  srt: true
  thumbnail_time_sec: 1.0
  upload_prep: { title: "愛知×イノベーションの現在地", tags: ["愛知","IT","スタートアップ"], desc: "データに基づく解説" }
```

---
## 6. 機能要件
1) **音声生成**
   - VOICEVOX Web API を使い、各 `sections[*].narration` から WAV を生成。
   - セクション毎に `work/audio/<idx>_<id>.wav` 保存。
   - エラー時はリトライ(指数バックオフ/最大3回)。
2) **BGMミキシング**
   - 全編にBGMを敷き、ナレーションの区間で自動ダッキング(ducking)。
3) **背景合成**
   - 背景が動画: ループ。画像: 指定秒数で静止 or ズームパン(ケンバーンズ)。
4) **テロップ描画**
   - `on_screen_text` をセクション時間に合わせて `drawtext` で表示。
   - 改行/禁則処理、テキスト長自動折返し。
5) **クレジット/ウォーターマーク**
   - 全編固定表示 or イントロ/アウトロのみ。
6) **字幕(SRT)**
   - 各セクションの開始/長さから SRT 自動生成(日本語)。
7) **出力/品質**
   - `libx264`、`yuv420p`、`crf`/`preset` を `config.yaml` で調整。
8) **バッチ生成**
   - 複数YAMLをキュー投入して連続レンダリング。

---
## 7. 非機能要件
- **性能**: 60–120秒動画を1–3分程度で生成(環境依存)。
- **再現性**: 同じYAML/素材/設定→同じ結果ファイル。
- **ログ**: JSONラインで工程ログ出力。失敗時のステップ/コマンド履歴を保存。
- **拡張性**: 将来的に音声エンジン差し替え(VOICEVOX→COEIROINK等)に対応。

---
## 8. VOICEVOX API I/F 仕様(実装用メモ)
- `POST /audio_query?text=...&speaker={id}` → JSON のクエリを取得。
- `POST /synthesis?speaker={id}` with 取得JSON → バイナリWAV。
- セクション間ポーズは、無音結合 or `pause_msec` で無音WAV生成。

---
## 9. FFmpeg 合成ポリシー(例)
- **基本**: 背景 + ナレーション + BGM + テロップ + 透かし を `filter_complex` 一発で出力。
- **テロップ**: `drawtext=fontfile=...:text='...':fontsize=...:fontcolor=...:x=...:y=...:borderw=...`
- **ダッキング**: `sidechaincompress` でBGMをナレーションに追従して減衰。
- **画像BGの場合**: `-loop 1 -t <sec>` + Ken Burns風に `scale,zoompan` を任意実装。

---
## 10. クリエイティブポリシー
- テキスト: 1画面 2–3行/最大22全角を推奨。強調語は【】や全角スペースでリズム付け。
- BGM: -16dBFS目安、ナレーション時は -6〜-10dB。
- 色: 青系/メタリック基調(技術系)。
- サムネ: 太字ゴシック、短い強いワード、人物/地図/アイコンを抽象化。

---
## 11. 権利・コンプライアンス
- **VOICEVOXキャラ別ライセンス**を事前確認: クレジット表記、事前申請の要否(例: 青山龍星)。
- BGM/SE/映像素材のライセンス明記・台帳化(出典URL/許諾形態/使用回/NG用途)。
- 機微なトピックの事実確認(情報ソース)と引用表記の運用。

---
## 12. CLI & 実行フロー(概略)
```
# 単体生成
python scripts/generate_video.py \
  --config configs/config.yaml \
  --script inputs/scripts_yaml/aichi_it_01.yaml \
  --out outputs/rendered/

# バッチ
python scripts/batch_render.py --glob "inputs/scripts_yaml/*.yaml"
```

**generate_video.py(想定役割)**
1) 設定/台本ロード → 2) VOICEVOX 音声生成 → 3) 各セクションMP4生成 → 4) 連結 → 5) SRT/サムネ → 6) メタJSON。

---
## 13. エラーハンドリング/リカバリ
- VOICEVOX応答なし: バックオフリトライ、fallbackでセクションをスキップ/警告。
- 素材欠落: プレースホルダ背景/音源へ自動切替。
- 文字が長すぎ: 自動折返し/縮小/スクロールのいずれか適用。

---
## 14. テスト観点
- 台本最小/最大(文字数/セクション数)。
- 画像/動画背景の双方。
- フォント未設定時のデフォルト挙動。
- ダッキングの聞感評価(-6/-8/-10dB)。
- 出力フォーマット(1080p, 720p, 9:16縦動画)。

---
## 15. 将来拡張
- Whisperで自動字幕生成(読み上げ→文字起こし→SRT整形)。
- AI画像/動画生成(パターン背景を自動生成/バリエーション化)。
- YouTube API連携(タイトル/説明/タグの自動投稿下書き)。
- A/Bテスト用にテロップ/BGM/構成の自動パラメトリック生成。

---
## 付録A: 最小YAML(ショート用)
```yaml
project: "short_demo"
video: { width: 1080, height: 1920, fps: 30, bg: "bg_materials/ai_loop02.mp4" }
voice: { engine: voicevox, speaker_id: 1, speedScale: 1.1 }
text_style: { font: "fonts/NotoSansJP-Bold.otf", fontsize: 64, fill: "#fff" }
sections:
  - { id: s1, on_screen_text: "愛知のITは弱い？", narration: "よく言われますが、データで見ると一概には言えません。" }
  - { id: s2, on_screen_text: "給与は?", narration: "東京よりは控えめの傾向。ただし職種と企業で差が出ます。" }
  - { id: s3, on_screen_text: "勝ち筋は?", narration: "製造×DXの交差領域がチャンスです。" }
output: { filename: "short_demo.mp4", srt: true }
```

---
## 付録B: スクリプト生成ワークフロー (実装済み)

### B.1. ブリーフから台本への自動生成
- CLI: `python scripts/generate_script_from_brief.py --brief "..." --theme lifehack --sections 5`
- 実装: `src/script_generation/generator.py::ScriptFromBriefGenerator.generate()`
- LLM ラッパー: `src/script_generation/llm.py::generate_and_validate()` で厳密JSON出力を強制。
- スキーマ: `src/script_generation/schemas.py::script_payload_schema()`
- 結果: `ScriptModel` インスタンスを YAML/JSON で出力。

### B.2. 厳密 JSON 出力ポリシー
- プロンプトテンプレート: `src/script_generation/prompt_templates.py::build_json_only_messages()`
- 救済/検証: `src/script_generation/response_validator.py::sanitize_and_validate()`
- ログ: `src/script_generation/logging_utils.py` で最小ログ化・生レスポンス保存。
- リトライ: 指数バックオフ（デフォルト1秒×回数）、最大3回まで自動再試行。

---
## 付録C: アセット自動補完 (実装済み)

### C.1. 背景素材の自動取得
- 関数: `scripts/generate_video.py::ensure_background_assets()`
- 処理: 背景未指定またはファイル非存在の場合、Pexels/Pixabay API で自動検索・ダウンロード。
- キーワードサニタイズ: 正規表現で ASCII/日本語のみを抽出し、50文字以下に制限（Pixabay 400エラー回避）。
- キャッシュ: `assets/cache/` 配下に保存、ライセンス情報を JSON に記録。

### C.2. BGM 自動補完
- 関数: `scripts/generate_video.py::ensure_bgm_track()`
- 処理: BGM 未指定の場合、ローカルキャッシュ `assets/bgm/` から候補を検索。見つからない場合はデフォルト・フォルバック。
- ボリュームダッキング: ナレーション時は BGM を自動減衰（デフォルト -6〜-10dB）。

---
## 付録D: Stepdocs UI ガイド自動生成 (実装済み)

### D.1. Electron 操作の自動記録
- エンジン: `stepdocs/record_electron.js` で Playwright を使用して UI 操作を自動化。
- JSON シナリオ: `stepdocs/scenarios/` に複数の操作フロー定義（01_script_editor.json ～ 09_history_reuse.json）。
- スクリーンショット + ステップ: 各操作ごとにスクリーンショットとアクション履歴を JSON で記録。

### D.2. Markdown ガイドの自動生成
- ビルドスクリプト: `stepdocs/build_stepdocs.js` で `docs/stepdocs/steps.json` と画像から Markdown を生成。
- 出力先: `docs/stepdocs/基本操作ガイド_自動生成.md`
- 重複排除: `tools/stepdocs/dedupe_screenshots.py` でハッシュベースの重複削除と参照更新。
- 更新ポリシー: シナリオ追加時に `record_electron.js` を再実行し、ガイドを定期再生成。

---
## 付録B: 品質チェックリスト(運用)
- [ ] ナレーションの不自然な間/読み間違いがない
- [ ] テロップの誤字/はみ出し/被りなし
- [ ] クレジット/ロゴ/素材ライセンス表記あり
- [ ] 音量バランス: ナレーション>-12dBFS, BGMダッキング-6〜-10dB
- [ ] サムネの可読性(小画面テスト)

---
以上。実装に着手する際は、この要件定義をIssue化し、優先度順にタスク分解してください。

