# Requirements Draft (v2)

## 1. Goal & Scope
- 雑学／ライフハック系の動画を、テーマ入力から完成動画までほぼ自動で生成する。
- テキスト台本は YAML を基準とし、ランキング形式や CTA など雑学動画特有の構造をテンプレ化する。
- 将来的には YouTube/Shorts/Vertical など複数フォーマットに対応。

## 2. Content Strategy Requirements
1. **テーマ選定テンプレ**: ユーザーが「ジャンル」「切り口」「ランキング項目数」を指定し、驚きを与えるネタ（損している習慣 etc.）を提示できるようにする。
2. **構成テンプレ**:
   - オープニング: 悩み提示＋メリット予告＋ダイジェスト。
   - 本編: ランキング形式（5〜7項目）、各項目は「フック→根拠→実演→ブリッジ」で構成。
   - エンディング: サマリー＋CTA（コメント/登録誘導）。
3. **スクリプトトーン**: テンション（明るい/淡々）、語尾、キャッチコピーのプリセットを保持し、テーマごとに切り替える。

## 3. Functional Highlights
- **Input ingestion**: Markdown / YAML / プロンプトを受け取り、自動でランキング台本を生成。
- **Script enrichment**:
  - 科学的根拠や専門家コメントの挿入。
  - ブリッジ文や CTA を自動生成。
  - 語尾/口調統一。
- **Narration**: VOICEVOX キャラクター選択、スピード・ピッチ調整、セクションごとのポーズ。
- **Visuals**:
  - 背景: 既存クリップ or 画像；必要に応じて AI 画像生成やフリー素材自動取得。
  - テロップ: ランキング番号、タイトル、ビフォーアフター文を描画。
  - サムネイル: 「知らないと損」「保存版」など驚きラベル付きテンプレ。
- **Assembly**: FFmpeg で背景 + BGM + ナレーション + テロップを統合。SRT/メタ JSON/サムネも同時生成。
- **Automation**:
  1. テーマ入力 → AI 台本生成。
  2. 素材収集 → 背景・アイコンの自動取得。
  3. 音声生成 → VOICEVOX API。
  4. 映像合成 → ffmpeg ランキングテンプレ。
  5. アウトプット → 複数レイアウトで MP4/SRT/サムネ。

## 4. Non-functional Considerations
- **再現性**: 同じテーマと設定で同じ結果が得られるシード管理。
- **ライセンス管理**: 素材の出典や利用条件をメタ情報に記録。
- **拡張性**: 音声エンジンや画像生成エンジンの差し替えができる構造。
- **ユーザーUX**: CLI + Web UI（スクリプト編集画面）で操作可能。

## 4.1. LLM & Script Generation Requirements
- **厳密JSON出力**: AI台本生成時は `generate_and_validate()` ラッパーで JSON のみを強制。YAML フォールバックと文字列抽出による救済処理を実装。
- **スキーマ検証**: `src/script_generation/schemas.py` で簡易スキーマ定義（`script_payload_schema`, `trend_ideas_schema`）を保持し、各 LLM 呼び出しで適用。
- **リトライ・バックオフ**: LLM 呼び出し失敗時は指数バックオフ（デフォルト 1秒×回数）で最大3回まで自動再試行。
- **最小ログ化・キー非出力**: `logs/llm_requests.log` には request/response のメタ情報（endpoint、status、timestamp）のみ。API キーや全ペイロードは記録しない。
- **生レスポンス保存**: パース失敗時は `logs/llm_errors/invalid_llm_response_<timestamp>.txt` に生レスポンスを保存。運用調査用のみ。
- **プロバイダ選択**: OpenAI/Anthropic/Gemini 対応。環境変数 (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`) または `settings/ai_settings.json` から設定取得（平文出力はしない）。

## 4.2. Logging & Security
- **キー管理**: 全 API キーを環境変数か `.env` ファイル（`.gitignore` 対象）に配置。リポジトリには絶対に平文を含めない。
- **ログ監査**: ログファイル `logs/llm_requests.log` と `logs/llm_errors/` を定期確認し、異常パターンを検出。
- **機微データ処理**: 生成物に著作権/個人情報が含まれる可能性がある場合は、自動出力をそのまま公開せず人によるレビュー必須とする。

## 4.3. Asset Pipeline & Stepdocs
- **自動素材取得**: `ensure_background_assets()` で Pexels/Pixabay API を呼び出し、不足素材を補完。キーワードをサニタイズし 429/400 エラー回避。
- **キャッシュ管理**: ダウンロード済み素材を `assets/cache/<keyword>/` に保存し、ライセンス情報を JSON に記録。
- **UI ガイド自動生成**: Electron デスクトップアプリの操作を Stepdocs（`stepdocs/`）で自動記録し、スクリーンショット + ステップを Markdown ガイドに変換。定期的に再生成して最新状態を保証。

## 5. Open Questions
1. 自動テーマ選定のアルゴリズム（トレンド API を利用するか）。
2. AI スクリプト生成時の安全対策・検閲ポリシー。
3. 素材取得のコスト管理（キャッシュやプリセット活用）。
4. 将来的なアップロード自動化（YouTube API 連携）が必要か。
