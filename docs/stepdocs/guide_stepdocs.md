# Stepdocs ガイド（自動生成）

このガイドは `stepdocs` のシナリオ実行結果（`steps.json` と `screenshots/`）をもとに自動生成されました。
目的は、初心者が `stepdocs` を使ってアプリの基本操作を再現できるようにすることです。

---

## 前提
- リポジトリをクローン済みであること。`auto-video-generator` のルートが存在。
- Node.js と npm がインストールされていること。
- `desktop-app` の依存は `npm install` により解決されている（Electron は開発環境により差異あり）。

## すぐに試せるコマンド
```bash
# stepdocs ディレクトリへ移動してシナリオを実行
cd stepdocs
node record_electron.js --scenario=scenarios/01_beginner_flow.json

# 再生ログとスクリーンショットは docs/stepdocs 以下に保存されます
# ネットワークログ: docs/stepdocs/replay_network.log
# スクリーンショット: docs/stepdocs/screenshots/
```

---

## 手順（スクリーンショット付き）
以下は `stepdocs/steps.json` の各ステップを分かりやすくしたものです。スクリーンショットは `docs/stepdocs/screenshots/` を参照してください。

### Step 1: アプリを開く
- 意図: アプリの UI を開く（ローカルの renderer を参照）。
- 実行方法: `Start_DesktopApp.command` を使うか、stepdocs のシナリオを再生します。
- スクリーンショット:

  ![step01](screenshots/step01.png)

### Step 2: テーマセレクト表示待ち
- 意図: 起動後にテーマ選択 UI が準備されるまで待機します。
- スクリーンショット:

  ![step02](screenshots/step02.png)

### Step 3: 台本タブへ移動
- 意図: 上部のタブで「台本編集」タブを選択します。
- 実行: `.tab-btn[data-tab="tab-script"]` をクリック。
- スクリーンショット:

  ![step03](screenshots/step03.png)

### Step 4: AI ブリーフ入力欄の表示待ち
- 意図: AI ブリーフ（台本生成用のテキスト）入力欄が表示されるのを待ちます。
- スクリーンショット:

  ![step04](screenshots/step03.png)

### Step 5: ブリーフ入力
- 意図: 例として「忙しい朝でもできる驚きの時短ライフハック...」というブリーフを入力します。
- スクリーンショット:

  ![step06](screenshots/step06.png)

### Step 6: セクション数の設定
- 意図: 台本のセクション（項目）数を設定します（例: 5）。
- スクリーンショット:

  ![step07](screenshots/step06.png)

### Step 7: ショート調整（任意）
- 意図: ショート動画向けの調整を有効にします。
- スクリーンショット:

  ![step08](screenshots/step06.png)

### Step 8: AI 生成の実行
- 実行: `AIで生成` ボタンをクリックします。外部 API が呼ばれる場合は事前に `settings/ai_settings.json` に API キーを設定するか、環境変数経由で設定してください。
- 次に、生成結果として `#sectionList li` が表示されるのを待ちます。

---

## 追加情報
- ネットワークログ: `docs/stepdocs/replay_network.log` にネットワークリクエストの履歴が出力されます（ローカルAPI 含む）。
- LLM 呼び出しログ: `logs/llm_requests.log` に Python 側から送信した LLM リクエストの記録があります（秘密情報は redacted してください）。

## トラブルシュート
- Playwright/ Electron が起動しない: Electron のバイナリアーキテクチャ（arm64/x64）や `ELECTRON_RUN_AS_NODE` が設定されていないか確認してください。
- API キー漏洩の懸念: `settings/ai_settings.json` にキーが含まれている場合、ローテーションして `.env` または OS シークレットに移行してください。手順は `docs/security/ai_key_management.md` を参照してください。

---

このガイドをベースに、より詳しい手順書（外部API 利用時の手順や CI での自動化）を作成可能です。どうしますか？
