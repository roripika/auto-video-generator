# Auto Explainer Video Generator

このリポジトリは、構造化された台本データから解説動画を自動生成するツールのベースです。台本作成 → ナレーション → ビジュアル → 編集というパイプラインを定義し、開発環境を整えることを初期目標にしています。

## リポジトリ構成

```
auto-video-generator/
├── docs/        # 仕様・調査メモ
├── src/         # アプリケーション本体ソース
├── scripts/     # CLI や補助スクリプト
└── README.md    # このファイル
```

## 今後の進め方

1. `docs/requirements.md` で要件とユースケースを具体化。
2. 台本 → 音声 → 映像 → 出力の各ステップをモジュール分割し、必要な外部サービスを整理。
3. ナレーション TTS、映像合成（FFmpeg）、サムネ生成などに使う技術スタックを決定。
4. CLI から YAML 台本を読み込み、VOICEVOX 音声と背景映像を合成する最小パイプラインを試作。

プロジェクトの成長に合わせて柔軟に更新してください。

## 参照ポリシー

- 外部プロジェクト（例: `voicevox-storycaster`）は **参照のみ** とし、得られた知見を本リポジトリへ落とし込む形で利用します。
- 外部リポジトリに直接コミットや PR を送ることは行いません。改修は必ず本リポジトリで独自実装します。

## セットアップ手順

### 1. 依存ライブラリのインストール
```
pip install pydantic PyYAML requests
```

### 2. ナレーション音声（WAV）の生成
```
python scripts/generate_audio.py --script path/to/script.yaml [--config configs/config.yaml]
```
YAML 台本を `ScriptModel` で読み込み、VOICEVOX API をセクションごとに呼び出して `work/audio/` 配下へ WAV を保存します。

### 3. macOS 向け補助スクリプト
- `Setup.command`: 仮想環境の作成、依存インストール、ffmpeg 導入をまとめて実行。
- `RunVoicevoxGUI.command`: インストール済み VOICEVOX GUI を起動します。
