# Auto Explainer Video Generator

このリポジトリは、構造化された台本データから解説動画を自動生成するツールのベースです。台本作成 → ナレーション → ビジュアル → 編集というパイプラインを整備し、雑学／ライフハック向けのランキング動画を高速に量産できるようにすることを目標としています。

本 README は **GUI を触る初心者ユーザー向け** と **CLI/API を扱う開発者向け** の 2 章構成です。用途に合わせて該当セクションをご覧ください。

---

## 🎬 GUI ビギナー向けクイックスタート

最小限の手順で Electron デスクトップアプリを起動し、台本生成 → 素材選定 → 動画レンダリングまで行いたい方向けのガイドです。

1. **セットアップを実行**
   - macOS で `Setup.command`（内部では `setup.sh` を呼び出します）をダブルクリックするだけで OK。Homebrew が入っていれば、pyenv や `python@3.11`、FFmpeg、VOICEVOX Engine などを自動導入し `.venv` を再構築します。
   - 失敗した場合は `docs/setup_troubleshooting.md` を参照し、エラーのログファイルを確認してください。

2. **デスクトップアプリを起動**
   - `Start_DesktopApp.command` を実行すると GUI が立ち上がります。初回起動時は右上の **設定** で OpenAI Key、YouTube API Key、BGM ディレクトリなどを入力してください（`settings/ai_settings.json` に保存）。

3. **台本を AI 生成**
   - 画面左の「AI 台本生成」パネルにブリーフとセクション数を入力し、テーマを選んで「AIで生成」を押せば YAML 台本が読み込まれます。セクションリストをクリックするとテロップや CTA を GUI で編集できます。

4. **素材と BGM を選ぶ**
   - 「背景素材」パネルの検索か、`ライブラリから選ぶ` ボタンでローカルの BGM ディレクトリを参照できます。ドラッグ＆ドロップでセクション単位の背景を差し替えることも可能です。

5. **VOICEVOX 音声 / 動画を書き出す**
   - `VOICEVOX で音声生成` → `タイムライン更新` → `動画を書き出す` の順にクリックすると、`outputs/rendered/` に MP4 + SRT が生成されます。

> 🔍 *補足:* VOICEVOX Engine を個別に走らせたい場合は `Start_VoicevoxEngine.command` を起動してください。GUI からは自動で `http://localhost:50021` を参照します。

---

## 🧑‍💻 開発者／API ユーザー向け

CLI や API 統合を行う方向けに、環境構築からスクリプトベースのパイプラインまでをまとめています。

### 0. 参照ポリシー
- 外部プロジェクト（例: `voicevox-storycaster`）は **参照のみ** とし、得られた知見を本リポジトリへ取り込む方針です。
- 外部リポジトリに直接コミットや PR は送らず、改修は本リポジトリで独自実装します。

### 1. 依存ライブラリ
```
pip install pydantic PyYAML requests Pillow urllib3<2 pytest yt-dlp
```
macOS 標準 Python は LibreSSL 依存のため、OpenSSL 版 Python（pyenv の `3.10.15` など）で `.venv` を作成してください。`setup.sh`（または `Setup.command`）は Homebrew が使える環境であれば pyenv / gettext / ffmpeg / p7zip を導入し、pyenv Python で仮想環境を再構築、`requirements.txt` をインストールします。

> ✅ **Tip:** pyenv でのビルドに失敗した場合、自動的に Homebrew の `python@3.11` へフォールバックします。`source .venv/bin/activate && python -c "import ssl; print(ssl.OPENSSL_VERSION)"` で OpenSSL 3.x になっているか確認してください。

> 📘 **トラブルシュート:** うまく動かない場合は `docs/setup_troubleshooting.md` を参照。Homebrew の導入、`.venv` 再作成、ログの確認方法をまとめています。

### 2. AI 台本自動生成（LLM）
```
python scripts/generate_script_from_brief.py \
  --brief-file notes/idea.txt \
  --theme-id lifehack_surprise \
  --sections 5
```
- `OPENAI_API_KEY`（必要なら `OPENAI_MODEL`, `OPENAI_BASE_URL`）を環境変数で指定してください。
- `--brief` で直接テキストを渡すか、標準入力からパイプすることもできます。
- 生成結果は `scripts/generated/` 配下に ScriptModel 互換の YAML として保存されます。必要に応じて `desktop-app` や CLI へ受け渡してください。
- Electron デスクトップアプリ右上の **設定**（`settings/ai_settings.json` に保存）から API Key / プロバイダ / Base URL / モデルを入力しておくと、CLI でも自動で参照されます。
- サポートするプロバイダと環境変数  
  - OpenAI: `OPENAI_API_KEY`（任意で `OPENAI_MODEL`, `OPENAI_BASE_URL`）  
  - Anthropic Claude: `ANTHROPIC_API_KEY`（任意で `ANTHROPIC_MODEL`, `ANTHROPIC_BASE_URL`）  
  - Google Gemini: `GEMINI_API_KEY` または `GOOGLE_API_KEY`（任意で `GEMINI_MODEL`, `GEMINI_BASE_URL`, `GEMINI_MAX_OUTPUT_TOKENS`）
- BGM 自動取得を有効にしたい場合は設定画面で **YouTube API Key** と **BGM ディレクトリ** を入力すると `settings/ai_settings.json` に保存され、CLI (`scripts/generate_video.py`) も同じ値を読み込みます（環境変数 `YOUTUBE_API_KEY` / `BGM_DIRECTORY` でも上書き可能）。

### 3. VOICEVOX Engine のセットアップ
```
chmod +x scripts/setup_voicevox.sh
./scripts/setup_voicevox.sh
```
- 既定では `tools/voicevox_engine/` に VOICEVOX Engine を展開します。
- macOS では `Start_VoicevoxEngine.command` をダブルクリックするとローカル API (`http://localhost:50021`) が起動します。
- すでに VOICEVOX Engine/GUI をインストール済みの場合はこの手順を飛ばし、`ConfigModel.voicevox_endpoint` を実際のエンドポイントに合わせてください。

### 4. フルパイプライン（映像 + 音声 + SRT）
```
python scripts/generate_video.py \
  --script path/to/script.yaml \
  [--config configs/config.yaml] \
  [--skip-audio] [--force-audio] [--dry-run]
```
- ScriptModel を読み込み、VOICEVOX で WAV を生成し（`work/audio/*.wav`）、タイムライン計算 → FFmpeg 合成 → SRT/metadata 出力まで一括実行します。
- `--skip-audio`: 既存 WAV をそのまま利用したい場合に指定。`--force-audio`: 既存 WAV があっても再生成。
- `--dry-run`: FFmpeg コマンドのみ表示して実行をスキップ。パスや設定の確認に使えます。
- 出力先は `ConfigModel.outputs_dir`（既定: `outputs/rendered/`）。動画と同名で `.srt` / `.json` も生成されます。
- `video.bg` や各セクションの `bg_keyword` / `bg` がローカルファイルを指していない場合、Pexels/Pixabay から自動で素材をダウンロードして補完します。セクション固有の背景が見つかったものには個別に `section.bg` が書き込まれます。
- `bgm` が未設定、またはファイルが存在しない場合は `assets/bgm/` ディレクトリから自動で音源を選び、`bgm.file` にセットします。`YOUTUBE_API_KEY` を設定し `yt-dlp` をインストールしておくと、YouTube Audio Library（Data API）検索→自動ダウンロードで BGM を確保できます。ローカルの `assets/bgm/youtube/` にキャッシュされるため、次回以降はオフラインでも利用できます。特定の動画を指定したい場合は `YOUTUBE_FORCE_VIDEO=<videoId or URL>`（または `settings/ai_settings.json` / GUI 設定画面の「デフォルト BGM」欄で `youtubeForceVideo`）を設定すると、その動画を優先的にダウンロードします。
- キーワードからの検索にヒットしない場合でも、既定で「雑学 BGM」系のキーワードを付与して YouTube Audio Library を検索するため、雑学/解説動画向けの汎用 BGM が自動で補われます。
- ライセンス表記などを冒頭のウォーターマークで表示したい場合は YAML で `watermark.text`（任意で `duration_sec`, `font`, `fontsize`, `fill`, `stroke_color`, `stroke_width`）を設定してください。画像 `watermark.file` と併用すると、画像に加えてテキストも重ねて描画されます。

YouTube Audio Library から BGM を自動取得するには、Google Cloud Console で API キーを発行し `YOUTUBE_API_KEY` 環境変数を設定してください（例: `export YOUTUBE_API_KEY=xxxx`）。`yt-dlp` と FFmpeg が導入済みであれば、最初の実行時に `assets/bgm/youtube/` へ mp3 がダウンロードされます。

### 5. ナレーション音声のみ生成（デバッグ用途）
```
python scripts/generate_audio.py --script path/to/script.yaml [--config configs/config.yaml]
```
YAML 台本を `ScriptModel` で読み込み、VOICEVOX API をセクションごとに呼び出して `work/audio/` 配下へ WAV を保存します。

### 6. macOS 向け補助スクリプト
- `Setup.command`: 仮想環境の作成、依存インストール、ffmpeg 導入をまとめて実行。
- `Start_DesktopApp.command`: Electron 製の台本エディタを起動します（初回は自動で `npm install` を実行）。
- `Start_VoicevoxEngine.command`: `tools/voicevox_engine/` に展開した VOICEVOX Engine を起動します。

### 7. 素材取得パイプライン
1. `.env` などで以下のキーを設定（利用可能なサービスのみでも可）  
   - `PEXELS_API_KEY` / `PIXABAY_API_KEY`  
   - `STABILITY_API_KEY`（Stable Diffusion フォールバック用）
2. CLI から素材を取得  
   ```
   python scripts/fetch_assets.py --keyword "ライフハック 驚き" --kind video --max-results 3
   ```
   成功すると `assets/cache/<keyword>/` に動画/画像とライセンス JSON が保存されます。
3. 画像素材が足りない場合は `--kind image` または `--disable-ai` を切り替えて再実行してください。

### 8. サムネイル自動生成
```
python scripts/generate_thumbnail.py --theme-id lifehack_surprise --headline "知らないと損" --subhead "保存版ライフハック"
```
- テーマ YAML の `thumbnail` セクションで色やフォントを指定可能。
- `--background work/assets/cache/.../file.jpg` のように既存素材を合成することもできる。

### 9. デスクトップ台本エディタ（Electron, β版）
```
cd desktop-app
npm install
npm start
```
- テーマ選択 → 新規 YAML 生成、セクション単位の編集、ファイルの読み書きが GUI から可能。
- 右カラムの YAML プレビューで `ScriptModel` 互換のデータを即座に確認できる。
- 生成したファイルは `scripts/` 配下など任意の場所へ保存し、既存の CLI パイプラインに渡せる。
- ヘッダー右上の「設定」から OpenAI / Anthropic / Google Gemini の API Key やエンドポイントを登録できます（内容は `settings/ai_settings.json` に保存されます）。
- 「AI 台本生成」パネルからブリーフを入力して LLM 生成を実行し、「背景素材」パネルでキーワード検索→AssetFetcher（Pexels/Pixabay/AI フォールバック）を呼び出して `video.bg` を設定できます。
- 「テキストスタイル」パネルでフォント/色/位置/アニメーションを編集でき、「音声 & タイムライン」パネルから VOICEVOX 音声生成とタイムライン更新を UI から直接呼び出せます。
- 「BGM設定」パネルで BGM ファイル/URL、音量 (dB)、ナレーション時の ducking 量、ライセンス表記メモを入力すると、生成時に自動合成されます（UI からファイル選択も可能）。
- セクション編集フォームには「テロップセグメント」と「前景オーバーレイ」があり、行ごとのフォント/色/位置や商品画像などのレイヤーを GUI で細かく調整できます。

## 追加ドキュメント
- `docs/requirements.md`: 雑学動画に必要なコンテンツ要件（ランキング構成、CTA、素材取得フロー）を記載。
- `docs/script_editor_spec.md`: テーマ／ランキングエディタ UI のコンセプトや AI 連携フロー。
- `docs/TODO.md`: 実装タスク（AI 台本生成、素材パイプライン、サムネ自動化など）。
- `configs/themes/`: ランキング向けの企画テンプレート（例: `lifehack_surprise.yaml`）。`src/themes.py` から読み込めます。
