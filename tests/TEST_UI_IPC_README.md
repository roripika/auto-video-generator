# UI IPC ハンドラ と バックエンド API テストガイド

## 概要

このドキュメントは、Electron デスクトップアプリケーション UI のボタンごとの IPC 呼び出しと、バックエンド Python API のユニットテストについて説明します。

対象機能:
- **トレンド LLM 取得**: `trends:fetch-llm` IPC ハンドラと `fetch_trend_ideas_llm.py`
- **台本生成**: `scripts:generate-from-brief` IPC ハンドラと `src/script_generation/generator.py`
- **素材取得**: `assets:fetch` IPC ハンドラと `src/assets/pipeline.py`

---

## テスト構成

### [tests/test_ui_ipc_handlers.py](tests/test_ui_ipc_handlers.py)

#### テストクラス

| クラス | 対象 | テスト数 | 説明 |
|--------|------|--------|------|
| `TestFetchTrendIdeasViaLlm` | `scripts/fetch_trend_ideas_llm.py` | 6 | LLM トレンド取得の各種パターン（成功/失敗/検証） |
| `TestScriptGenerationFromBrief` | `src/script_generation/generator.py` | 2 | AI 台本生成のペイロード処理 |
| `TestLlmClientIntegration` | `src/script_generation/llm.py` | 3 | LLM クライアントの統合テスト（リトライ/検証） |
| `TestErrorHandling` | 全般 | 3 | エラーハンドリング・ロギング |
| `TestIpcPayloadValidation` | Main thread | 2 | IPC ペイロード構造の検証 |

**合計: 16 テストケース**

---

## 実行方法

### 環境セットアップ（初回のみ）

```bash
# 必須パッケージをインストール
/usr/local/bin/python3.11 -m pip install -q PyYAML pydantic requests Pillow pytest

# または Homebrew Python を使用
python3 -m pip install --user PyYAML pydantic requests Pillow pytest
```

### テスト実行

#### 全テスト実行

```bash
cd /Users/ooharayukio/auto-video-generator

# Python 3.11 を使用
/usr/local/bin/python3.11 -m pytest tests/test_ui_ipc_handlers.py -v

# または標準 python3
python3 -m pytest tests/test_ui_ipc_handlers.py -v
```

#### 特定クラスのみ実行

```bash
# トレンド取得テストのみ
python3 -m pytest tests/test_ui_ipc_handlers.py::TestFetchTrendIdeasViaLlm -v

# LLM 統合テスト
python3 -m pytest tests/test_ui_ipc_handlers.py::TestLlmClientIntegration -v

# エラーハンドリング
python3 -m pytest tests/test_ui_ipc_handlers.py::TestErrorHandling -v
```

#### 詳細出力オプション

```bash
# デバッグモード（スタックトレース表示）
python3 -m pytest tests/test_ui_ipc_handlers.py -xvs --tb=short

# シンプル出力（エラーのみ）
python3 -m pytest tests/test_ui_ipc_handlers.py -v --tb=no
```

---

## テスト項目詳細

### 1. トレンド LLM 取得（6テスト）

#### `test_fetch_trend_ideas_valid_response`
- **テスト内容**: LLM が有効な JSON レスポンスを返した場合
- **期待動作**: パース成功 → キーワード・アイデアが返却される
- **重要性**: ✅ 正常系の基本動作確認

#### `test_fetch_trend_ideas_invalid_json`
- **テスト内容**: LLM が無効な JSON を返した場合
- **期待動作**: JSONDecodeError 発生 → リトライまたはフォールバック
- **重要性**: ✅ エラーハンドリング必須

#### `test_fetch_trend_ideas_missing_ideas_field`
- **テスト内容**: LLM レスポンスに `ideas` フィールドがない
- **期待動作**: ValueError 発生 → リトライまたはフォールバック
- **重要性**: ✅ スキーマ検証

#### `test_parse_and_validate_with_max_ideas`
- **テスト内容**: max_ideas パラメータでアイデア数を制限
- **期待動作**: アイデア数が指定した上限以下に絞られる
- **重要性**: 📊 パフォーマンス制御

#### `test_parse_and_validate_filters_nsfw`
- **テスト内容**: NSFW フラグ付きアイデアを除外
- **期待動作**: `nsfw: true` のアイデアが結果に含まれない
- **重要性**: ⚠️ コンテンツフィルタリング

#### `test_build_messages_format`
- **テスト内容**: LLM へのメッセージ構築が正しい形式
- **期待動作**: role/content が正しく構成される
- **重要性**: 📝 プロンプト構造検証

### 2. 台本生成（2テスト）

#### `test_generate_script_valid_response`
- **テスト内容**: LLM が有効な台本ペイロードを返した場合
- **期待動作**: ScriptModel に変換できる
- **重要性**: ✅ 正常系確認

#### `test_generate_script_with_malformed_response`
- **テスト内容**: 不正な YAML/JSON レスポンス
- **期待動作**: エラーが適切に発生
- **重要性**: ✅ エラーハンドリング

### 3. LLM 統合（3テスト）

#### `test_generate_and_validate_with_valid_json`
- **テスト内容**: `generate_and_validate()` が有効 JSON を処理
- **期待動作**: JSON 文字列を返却
- **重要性**: ✅ ラッパー機能検証

#### `test_generate_and_validate_with_retry_on_failure`
- **テスト内容**: パース失敗時のリトライ処理
- **期待動作**: 指数バックオフで再試行 → 成功
- **重要性**: 🔄 リトライロジック

#### `test_generate_and_validate_fails_after_retries`
- **テスト内容**: 全リトライ失敗時
- **期待動作**: LLMError 発生
- **重要性**: ✅ エラー伝播確認

### 4. エラーハンドリング（3テスト）

#### `test_llm_api_error_handling`
- **テスト内容**: LLM API エラー（キーなし等）
- **期待動作**: LLMError 発生
- **重要性**: ⚠️ API エラー対応

#### `test_network_error_handling`
- **テスト内容**: ネットワークエラー
- **期待動作**: Exception 発生
- **重要性**: ⚠️ ネットワーク復帰性

#### `test_invalid_response_logging`
- **テスト内容**: 不正なレスポンスをログに保存
- **期待動作**: `logs/llm_errors/` に生レスポンス保存
- **重要性**: 📋 デバッグ情報収集

### 5. IPC ペイロード検証（2テスト）

#### `test_fetch_llm_trends_payload_structure`
- **テスト内容**: `trends:fetch-llm` の返却値構造
- **期待動作**: keywords/briefs フィールドが配列
- **重要性**: 🔌 IPC データ契約

#### `test_generate_script_payload_structure`
- **テスト内容**: `scripts:generate-from-brief` の入力構造
- **期待動作**: brief/sections/theme_id が期待形式
- **重要性**: 🔌 IPC データ契約

---

## トラブルシューティング

### テスト実行時の一般的なエラー

#### `ModuleNotFoundError: No module named 'yaml'`

```bash
# Homebrew Python 3.11 を使用してインストール
/usr/local/bin/python3.11 -m pip install PyYAML pydantic requests
```

#### `pytest: command not found`

```bash
# pytest をインストール
python3 -m pip install pytest
```

#### テスト中に生レスポンスが `logs/llm_errors/` に保存される

- **原因**: LLM レスポンスのパース失敗（正常な動作）
- **対応**: ログファイルの内容を確認して LLM プロンプト調整

#### `LLMError: API key not set`

- **原因**: 環境変数未設定
- **対応**: `OPENAI_API_KEY` 等を `.env` ファイルで設定

---

## CI/CD 統合

### GitHub Actions 例

```yaml
name: Test UI IPC Handlers

on: [push, pull_request]

jobs:
  test:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python -m pytest tests/test_ui_ipc_handlers.py -v
```

---

## 今後の拡張予定

- [ ] Mock HTTP クライアントを使用した YouTube API テスト
- [ ] Electron IPC リスナーの Jest テスト
- [ ] 統合テスト: UI ボタン → IPC → バックエンド → UI 更新
- [ ] パフォーマンスベンチマーク（LLM 呼び出し時間）
- [ ] 本番環境での E2E テスト

---

## 関連ファイル

- [src/script_generation/llm.py](src/script_generation/llm.py) - LLM クライアント
- [src/script_generation/generator.py](src/script_generation/generator.py) - 台本生成
- [scripts/fetch_trend_ideas_llm.py](scripts/fetch_trend_ideas_llm.py) - トレンド取得
- [desktop-app/src/main.js](desktop-app/src/main.js) - IPC ハンドラ定義
- [docs/llm_prompting.md](docs/llm_prompting.md) - LLM ポリシー

---

## 質問・フィードバック

テスト実行中に問題が発生した場合は、以下を確認してください：

1. Python バージョン: `python3 --version` （3.10 以上推奨）
2. 依存パッケージ: `pip list | grep -E "pytest|pydantic|PyYAML"`
3. ログファイル: `logs/llm_errors/` の内容
4. 環境変数: `echo $OPENAI_API_KEY` など

