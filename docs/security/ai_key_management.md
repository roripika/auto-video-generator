# API キー管理と秘匿化手順（Auto Video Generator）

この文書は、リポジトリ内に誤って含まれた API キーやログに含まれる機密情報を安全に扱うための手順を示します。特に今回のように `settings/ai_settings.json` に平文のキーが存在する場合に行うべき手順をまとめます。

**重要**: 既に公開リポジトリや他者と共有した鍵は直ちにサービス側でローテーション（再発行／無効化）してください。鍵の流出を前提に対応してください。

---

## 目的
- API キーや認証情報をリポジトリから除去し、ローカル環境や安全なシークレット管理へ移行する。
- 既存のログやファイルに残るキーを赤出しして記録を残すが、公開用には伏せる。
- 開発者が安全にアプリを動かせる手順を提供する。

---

## 推奨ワークフロー（概要）
1. 即時対応: 影響を受ける API キーをサービス側でローテーション（再発行）する。
2. リポジトリ上の平文キーを削除（`settings/ai_settings.json` のキーを空にするか、削除する）。
3. キーはローカルの `.env`、`~/.config/...` または OS のキーチェーンに移す。
4. `.gitignore` を更新して `.env` やローカルのシークレットファイルを除外する。
5. 既にコミット履歴に含まれている場合は、必要に応じて git の履歴書き換え（`git filter-repo` 等）を検討する。リモートに公開されている場合はキーのローテーションを優先する。
6. ログの redacted コピーを作成して監査用に保存する（元ログは保管期間を設けて安全に削除/アーカイブする）。

---

## ファイル構成（現在の例）
- `settings/ai_settings.json` : 現在キーが平文で入っているファイル。
- `logs/llm_requests.log` : LLM へ送ったリクエストのログ（API の URL が残ることがある）。
- `docs/stepdocs/replay_network.log` : Playwright/Electron のネットワーク/コンソールログ。

---

## 具体手順

### A. 鍵のローテーション（必須）
- 例: Google/Gemini, OpenAI, Pexels, Pixabay, YouTube など
- 各サービスのコンソールで対象キーを無効化（revoke）し、新しいキーを発行してください。
- その後、新しいキーを安全に保存して次の手順で扱います。

### B. `settings/ai_settings.json` から鍵を除去する（ローカル）
- 手動でエディタを開き `providers` 配下や `youtubeApiKey` 等の値を空文字 `""` に置き換えて保存します。
- 自動で実施する場合（ローカルで実行）:

```bash
# バックアップ
cp settings/ai_settings.json settings/ai_settings.json.bak
# jq がある場合、キーを空にする例
jq '.providers.openai.apiKey = "" | .providers.gemini.apiKey = "" | .providers.anthropic.apiKey = "" | .youtubeApiKey = "" | .pexelsApiKey = "" | .pixabayApiKey = ""' settings/ai_settings.json > settings/ai_settings.clean.json && mv settings/ai_settings.clean.json settings/ai_settings.json
```

> 注意: 上のコマンドはローカルでの編集です。バックアップがあることを確認してから実行してください。

### C. 鍵を安全に管理する方法（推奨）
1. `.env` ファイル（ローカルのみ）
   - プロジェクトルートに `.env` を作り、鍵を設定します（例）:

```text
OPENAI_API_KEY=sk-xxxxx
GEMINI_API_KEY=AIzaSy...
PEXELS_API_KEY=...
YOUTUBE_API_KEY=...
```

   - `.gitignore` に `.env` を追加してコミットしないようにする。
   - 実行時に `export $(cat .env | xargs)` するか、`direnv`/`dotenv` を使う。

2. macOS キーチェーン / Secret Manager
   - CI や共有環境では GitHub Secrets / GitLab CI Secret / macOS キーチェーン を利用してください。

3. launchd / systemd 環境変数
   - サービス起動時に環境変数を注入する方法も検討してください（運用向け）。

### D. アプリ側の設定（既存コードの確認）
- `desktop-app/src/main.js` では `buildEnv()` が利用され、環境変数（`PEXELS_API_KEY` 等）をプロセス環境に注入して Python スクリプトを起動します。
- したがって、`settings/ai_settings.json` からキーを除去しても、ローカル環境変数（または `.env` 経由）に設定すればアプリは動きます。

### E. ログの赤字化（redact）
- 既に行ったように、ログ中の `key=...`, `sk-...`, `AIza...`, `Authorization: Bearer ...` などは置換して redacted ファイルを作成してください。

```bash
# 例: 既存の llm_requests.log を redacted にコピーする
sed -E 's/(key=)[^&[:space:]]+/\1REDACTED/g; s/(sk-[A-Za-z0-9_\-]+)/REDACTED_SK/g; s/(AIza[ A-Za-z0-9_\-]+)/REDACTED_GOOGLEKEY/g; s/(Authorization: Bearer )[^[:space:]]+/\1REDACTED/g' logs/llm_requests.log > logs/llm_requests.redacted.log
```

- redacted ファイルを問題調査用に保存し、公開用のログは redacted を使ってください。

### F. 既にコミット済みの鍵がある場合（公開リポジトリ等）
- 可能なら早急に該当キーを失効させて再発行してください。
- `git filter-repo` や `bfg-repo-cleaner` を使って履歴からキーを除去できますが、履歴書き換えは慎重に行ってください（共同開発者と調整が必要）。

```bash
# 参考: BFG で文字列を置換（注意して使用）
# bfg --replace-text passwords.txt
```

---

## 例：ローカルでの実践手順（簡易）
1. サービス側でキーをローテーション（コンソールで新しいキー発行）。
2. プロジェクトに `.env` を作成して新しいキーを保存。
3. `settings/ai_settings.json` のキーを空にする（手動または jq）。
4. `.gitignore` に `.env` を追加し、 `git rm --cached settings/ai_settings.json` を必要に応じて実行してコミットから削除する。

```bash
# 仮のコマンド例
echo "OPENAI_API_KEY=sk-NEW" > .env
git add .env
# settings を編集してコミット
git add settings/ai_settings.json
git commit -m "Remove API keys from settings and use .env"
```

---

## 付録：今回作成した redacted ファイル
- `logs/llm_requests.redacted.log`
- `docs/stepdocs/replay_network.redacted.log`

これらは証跡用として保管されています。

---

必要であれば、私が `settings/ai_settings.json` を自動でクリーンアップするパッチ（API キーを空にする）を作成し、`.env` を使う README を追加します。続けますか？
