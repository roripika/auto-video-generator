**LLM プロンプト方針（厳密JSON出力）**

目的
- LLM による自動台本・アイデア生成で出力の信頼性を上げ、パースエラーや余計な説明文を排する。
- 生レスポンスの最小ログ化と、パース失敗時の生レスポンス保存ルールを明確にする。

方針（短く）
- モデルには「必ず有効な JSON のみを返す」旨をシステムメッセージで明示する。
- スキーマ（JSON Schema 風の簡易定義）を渡し、存在必須項目を指定して妥当性を担保する。
- 受け取ったレスポンスはまず `json.loads` → `yaml.safe_load` の順で試し、それでもダメなら文字列から JSON 部分を抽出して再試行する。
- 最終的にパースできなければ `logs/llm_errors/` に生レスポンスを保存し、最小限の診断ログを `logs/llm_requests.log` に追記する。

利用方法（実装済みファイル）
- 厳密テンプレート: `src/script_generation/prompt_templates.py`
- 救済/検証ユーティリティ: `src/script_generation/response_validator.py`
- スキーマ定義（簡易）: `src/script_generation/schemas.py`
- ログユーティリティ: `src/script_generation/logging_utils.py`
- ラッパー: `src/script_generation/llm.py::generate_and_validate()`

簡単なテンプレート例（運用）
- 呼び出し時はスキーマを渡す:

  - schema = {"type": "object", "required": ["sections"], "properties": {"sections": {"type": "array"}}}

  - messages = original_messages
  - result_json = generate_and_validate(client, messages, schema=schema, retries=2)

ログと鍵管理
- `logs/llm_requests.log` にはリクエストのメタ情報（endpoint, payload keys, timestamp, status）だけを残す。API キーや全パラメータは絶対に出力しない。
- 生レスポンスは `logs/llm_errors/invalid_llm_response_<timestamp>.txt` に保存する。調査時以外は閲覧しないこと。
- 開発環境では `settings/ai_settings.json` 内の平文 API キーをリポジトリから削除し、環境変数や `.env`（gitignored）へ移行することを必須にする。

運用上の注意
- モデルが時折余計な語を混ぜる（コードフェンスや説明）ケースがあるため、`generate_and_validate` は salvage 処理を行うが、必ず成功する保証はない。失敗時はプロンプトを厳格化して再実行または手動で検査すること。
- 生成物の重要度が高い場面（公開用タイトル/著作権情報など）は自動出力をそのまま公開せず、必ず人がレビューするワークフローを残す。

追加の改善案（今後）
- 保存した `logs/llm_errors/` を集計してパース失敗パターンを解析し、プロンプトのどの箇所が原因か自動で推定するスクリプト。
- モデルへ「必ず JSON のみ」と保証させるための追加プロンプトガード（出力先検知・構文チェックを促す文言の調整）。

お問い合わせ
- 仕様/テンプレートの変更は `docs/llm_prompting.md` を更新してください。
