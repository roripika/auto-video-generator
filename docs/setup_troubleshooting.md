# Setup & Troubleshooting Guide

このメモは「ワンクリックで動かしたいが、環境依存で止まりやすい」という状況を想定して、初心者がつまずきやすいポイントと確認コマンドをまとめたものです。macOS（Apple Silicon）を前提にしています。

## 1. 事前チェックリスト

1. **Xcode Command Line Tools**: すでに `xcode-select --install` 済みか確認。未導入ならダイアログに従ってインストール。
2. **Homebrew**: `brew -v` が通るか確認。未導入なら公式手順（https://brew.sh/）どおりに `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` を実行。
3. **必須ツール**: `brew install pyenv python@3.11 p7zip ffmpeg` を実行しておくと `Setup.command` の処理が短くなります。
4. **レポジトリの配置**: 半角英数字のみのパス（例: `~/auto-video-generator`）にクローンする。全角スペースや日本語を含めると VOICEVOX/FFmpeg が失敗しやすいです。

## 2. Setup.command の挙動

`Setup.command` は以下の順番で処理します。

1. Homebrew の self-update（必要な場合）。
2. `pyenv install 3.10.15` を試す（OpenSSL 3.x 連携ビルド）。
3. 失敗した場合は Homebrew の `python@3.11` にフォールバックし、`.venv` を再構築。
4. `pip install -r requirements.txt`、VOICEVOX Engine の自動ダウンロード＆展開。

### 2.1 pyenv ビルドが失敗する場合

- `BUILD FAILED (OS X 26.1 using python-build 2.6.x)` のようなエラーは OpenSSL 周りで発生します。以下を試してから再実行してください。

```bash
brew install openssl@3 ca-certificates
export CPPFLAGS="-I$(brew --prefix openssl@3)/include"
export LDFLAGS="-L$(brew --prefix openssl@3)/lib"
pyenv install 3.10.15
```

- それでも失敗する場合は pyenv を諦め、Homebrew の Python を使います（次項）。

## 3. Homebrew Python で `.venv` を作り直す

`Setup.command` が自動でやってくれますが、手動で再現したい場合は次の手順です。

```bash
cd ~/auto-video-generator
rm -rf .venv
PYTHON_BIN="$(brew --prefix python@3.11)/bin/python3.11"
"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> ℹ️ `python3.11 -m pip --version` と `python -c "import ssl; print(ssl.OPENSSL_VERSION)"` を実行し、`OpenSSL 3.x` が表示されれば OK です。LibreSSL が表示される場合は設定が反映されていません。

## 4. LLM 応答が途中で切れる場合

- 2025-11-25 の更新で `scripts/generate_script_from_brief.py` の `--max-tokens` 既定値を **6000** に拡張し、OpenAI の `finish_reason == "length"` を検出した場合は明示的にエラーを表示するようになりました。
- CLI やデスクトップアプリで「LLM response was truncated because max_tokens was too small」というエラーが出たら、以下のように `--max-tokens 8000` などを指定して再実行してください。

```bash
source .venv/bin/activate
python scripts/generate_script_from_brief.py \
  --brief "最新の家事時間短縮ガジェットを5つ紹介して" \
  --max-tokens 8000 \
  --stdout
```

- `logs/llm_errors/invalid_llm_response_*.txt` にエラー時の生レスポンスが保存されます。トラブル報告の際はこのファイルを共有すると原因が特定しやすいです。

## 5. 典型的なエラーログと対処

| 症状 | 対処 |
| ---- | ---- |
| `pyenv install` で `clang: error: linker command failed` | Xcode Command Line Tools と Homebrew の `openssl@3` を再インストール後、`CPPFLAGS`/`LDFLAGS` を設定して再実行。 |
| `/opt/homebrew/bin/python3` が見つからない | Intel Mac の場合は `/usr/local/opt/python@3.11` になる。`brew --prefix python@3.11` で実パスを取得。 |
| `.command` ファイルが実行できない（アクセス権） | `chmod +x Setup.command Start_DesktopApp.command Uninstall.command` を実行。Gatekeeper にブロックされた場合は「システム設定 > プライバシーとセキュリティ」で許可。 |
| Electron アプリで「LLM レスポンス解析に失敗」 | `.venv/bin/python` が LibreSSL を指していないか確認。`Start_DesktopApp.command` 実行前に `source .venv/bin/activate` して `python -c "import ssl; print(ssl.OPENSSL_VERSION)"` を確認。 |

## 6. 追加で収集しておきたい情報

- `-<timestamp>.log` ファイル（リポジトリ直下）: Setup/Uninstall コマンドの標準出力ログ。
- `logs/llm_errors/*.txt`: LLM 応答の生データ。
- `tools/voicevox_engine/setup.log`: VOICEVOX のセットアップ状況。

これらを毎回 Git にコミットする必要はありませんが、問題再現時に添付すると切り分けが大幅に楽になります。
