了解です。
Codex（VSCodeのAgent）にそのまま渡せる「開発ガイド／仕様書」っぽいドキュメントを書きます。
このまま `AGENT_GUIDE.md` か `docs/llm_trend_pipeline.md` みたいなファイル名で置けばOKな想定です。

---

````markdown
# auto-video-generator 用 LLMトレンド連携仕様書（Googleトレンド代替）

## 目的

`auto-video-generator` において、従来想定していた Google トレンド連携の代わりに、

- LLM（例: Gemini / OpenAI / Claude）から
- 「直近約30日で話題になったトピック」をベースにした
- 雑学・解説系 YouTube 動画向けのネタ候補（トレンドアイデア）を
- JSON または YAML 形式で取得し、
- そのデータを既存のスクリプト生成・動画生成パイプラインに流し込む

という自動化フローを構築する。

## 方針概要

1. LLM に対して「雑学動画向きのトレンドネタを 50〜100 件返してほしい」というプロンプトを送る。
2. LLM からは **JSON 形式** でネタリストを受け取る。
3. その JSON から優先度 (`priority_score`) が高いアイデアを選別する。
4. 各アイデアの `brief` をもとに、既存の `generate_script_from_brief.py` を呼び出して台本 YAML を生成する。
5. 必要に応じて `title` や `thumbnail` 情報もサムネ生成・YouTube アップロードに利用する。
6. 将来的に cron 等で定期実行し、一定間隔で自動投稿できるようにする。

※ Google トレンド API / RSS は利用しない。  
※ LLM 呼び出しは、既存の `ai_settings.json` / 環境変数の仕組みに可能な限り乗る。

---

## 仕様 1: LLM レスポンスの JSON スキーマ

LLM には「**この形の JSON だけを返して**」とプロンプトで指示する。  
Codex が扱う前提の JSON スキーマは以下の通り。

```json
{
  "generated_at": "2025-12-09T18:30:00+09:00",
  "language": "ja",
  "time_range": "last_30_days",
  "ideas": [
    {
      "id": "20251209-001",
      "keyword": "ミャクミャク",
      "category": "ネット流行語",
      "region": "JP",
      "title": "大阪万博キャラ『ミャクミャク』が炎上した本当の理由3選",
      "brief": "2025年SNS流行語大賞の年間大賞にも選ばれた大阪万博公式キャラクター『ミャクミャク』。かわいい・怖い・気持ち悪いと評価が割れた理由は何だったのか？デザイン案の変遷、名前の由来、SNSでの炎上ポイントを、子どもにも分かるように解説する雑学動画。",
      "thumbnail": {
        "headline": "ミャクミャク炎上の裏側",
        "subhead": "大阪万博キャラに何が？"
      },
      "tags": ["雑学", "ネット文化", "大阪万博", "2025年トレンド"],
      "suggested_theme_id": "trivia_social",
      "priority_score": 0.96,
      "estimated_lifespan_days": 90,
      "nsfw": false
    }
  ]
}
````

### 各フィールドの意味

* `generated_at`:

  * LLM がネタリストを生成した日時（日本時間）
  * ISO8601形式（例: `"2025-12-09T18:30:00+09:00"`）

* `language`:

  * `"ja"` 固定でよい（日本語向け動画チャンネル前提）

* `time_range`:

  * `"last_30_days"` など、トレンドの参照レンジ（文字列でOK）

* `ideas`: トレンドネタの配列

  * `id`:

    * 一意なID（例: `YYYYMMDD-001`）
    * ファイル名やログに使う

  * `keyword`:

    * トレンドの元になっているキーワード・流行語・話題名（短め）

  * `category`:

    * `"ネット流行語"`, `"アニメ"`, `"ゲーム"`, `"テック"`, `"ライフハック"`, `"社会"` など
    * 絞り込みやプレイリスト分けに使える

  * `region`:

    * `"JP"`, `"Global"` など

  * `title`:

    * YouTube動画用タイトル案
    * 全角 30〜40 文字程度を想定（ただし厳密制約は不要）

  * `brief`:

    * `generate_script_from_brief.py` に渡すブリーフ文字列
    * 動画全体の趣旨・切り口が分かるように、日本語で数行程度書かれている

  * `thumbnail`:

    * `headline`: サムネ用の大見出し（短め、全角 15 文字目安）
    * `subhead`: サムネ用の小見出し（全角 20 文字目安）

  * `tags`:

    * YouTubeタグやチャンネル内分類用のキーワード配列

  * `suggested_theme_id`:

    * `generate_script_from_brief.py` の `--theme-id` に渡せる文字列
    * 例: `"trivia_social"`, `"trivia_ranking"`, `"trivia_culture"` など
    * 未指定の場合は、パイプライン側のデフォルトテーマを使ってよい

  * `priority_score`:

    * 0.0〜1.0 の数値
    * 「バズりそう度」「今のトレンド度」が高いほど 1.0 に近づける
    * パイプライン側で上位 N 件だけ選別するために利用

  * `estimated_lifespan_days`:

    * そのネタが「旬であり続けそうな」期間（日数）の目安
    * 長く使えそうなネタを後回し、短命ネタを優先して消化するなどの判断材料

  * `nsfw`:

    * センシティブな内容かどうか（基本的には `false` にしてもらう想定）

---

## 仕様 2: LLM へのプロンプト（例）

Codex が LLM に投げるときに使うプロンプト例。
※ここでは「テキストとして渡す仕様」を定めるだけで、実装は別途。

````text
あなたは YouTube 雑学・解説動画チャンネル向けの企画編集者AIです。

目的:
- 直近約30日間に日本および世界で話題になったトピックやネットトレンドを参考に、
  YouTube向けの雑学・解説動画のネタ候補を最大100件提案してください。
- ネタは「ゴシップ過多」「誹謗中傷」「露骨な政治対立」「過度にセンシティブな性的コンテンツ」は避けてください。

出力フォーマット:
- 以下の JSON だけを出力してください。説明文やコメントは一切書かないでください。
- コードブロック（```）も使わないでください。

スキーマ:
{ 上記の JSON スキーマをそのまま貼る }

制約:
- ideas は 50〜100件程度返してください。
- keyword には、2025年の「ネット流行語」「SNSトレンド」などで話題になったワードを優先的に含めてください。ただし説明は一般視聴者向けにわかりやすくしてください。
- priority_score が高いものほど、最近よく話題になっている／動画映えしそうなテーマにしてください。
- nsfw が true のものは基本的に作らない前提なので、原則すべて false にしてください。
````

Codex 実装側では、LLMのレスポンスを **そのまま JSON としてパース** する。

---

## 仕様 3: リポジトリへの変更方針

ターゲットリポジトリ:
`https://github.com/roripika/auto-video-generator`

### 3-1. 新規スクリプト（例）

#### ファイル案1: `scripts/fetch_trend_ideas_llm.py`

役割:

* LLM を呼び出して、上記スキーマの JSON を取得する。
* レスポンスを `data/trend_ideas_<timestamp>.json` として保存する。
* 標準出力に簡単なサマリ（件数など）を出す。

想定インターフェイス:

```bash
python scripts/fetch_trend_ideas_llm.py \
  --output data/trend_ideas_20251209.json \
  --max-ideas 100 \
  --language ja
```

コマンドライン引数:

* `--output`: 出力する JSON ファイルパス
* `--max-ideas`: 必要なアイデア数（LLMへのヒントとして使用。レスポンス件数チェックも行う）
* `--language`: `"ja"` 固定でよいが、将来の拡張用に残しておく

主な処理:

1. LLM にプロンプトを送信
2. レスポンス文字列を JSON としてパース
3. スキーマの基本要素が揃っているか軽くバリデーション
4. 必要なら `ideas` の長さを `max-ideas` にトリミング
5. `--output` で指定されたパスに JSON を保存

※ LLM 呼び出し部分は、リポジトリ内の既存「AI呼び出しラッパ」があればそれを利用する（`ai_settings.json`等に基づいてクライアントを切り替える）。

---

#### ファイル案2: `scripts/auto_trend_pipeline.py` の拡張

`auto_trend_pipeline.py` が既に存在する場合:

* `--source` オプションを追加し、`"llm"` を選べるようにする。

  * 例: `--source google_trends` / `--source llm` など
* `--source llm` の場合:

  1. `fetch_trend_ideas_llm.py` を内部的に呼び出すか、
     もしくは同等の処理を同じファイル内で直接実装する。
  2. JSON を読み取り、`ideas` を `priority_score` 降順でソート。
  3. 上位 N 件（`--max-keywords` 相当）を採用。

想定コマンド例:

```bash
python scripts/auto_trend_pipeline.py \
  --source llm \
  --max-keywords 5 \
  --theme-id trivia_social \
  --sections 5
```

`auto_trend_pipeline.py` 側の擬似処理フロー:

1. LLMからトレンドアイデアJSON取得
2. JSONロード → `ideas` を `priority_score` 降順でソート
3. 上位 `max_keywords` 件についてループ:

   * `brief` を一時ファイルに書き出す（例: `work/brief.txt`）
   * `suggested_theme_id` があればそれを、なければ `--theme-id` の値を使用
   * `generate_script_from_brief.py` を subprocess で呼び出し、YAML台本生成
   * 続けて、既存の動画生成・音声合成・サムネ生成・YouTubeアップロードのフローを実行（すでにあるスクリプトの呼び出し規約に従う）

---

## 仕様 4: 優先度とフィルタリングロジック

Codex に実装してほしいポイント:

* `priority_score` が高い順に採用する。
* `nsfw == true` のアイデアは一律スキップする。
* `estimated_lifespan_days` が著しく短い（例: 3日未満）ものは、
  自動運用の場合は優先度が高くても後回しにするか、ログに警告を出す。
* カテゴリやタグにより、チャンネル方針に合わないジャンル（例: ホラー、陰謀論など）があれば、
  あらかじめブラックリスト化して除外できるとベター。

---

## 仕様 5: YAML での利用案（必要なら）

JSON ではなく YAML を使う場合、上記スキーマをそのまま YAML に変換して保存し、

* `pyyaml`（既に依存があればそれ）でロード
* Python 内では同じ dict 構造として扱う

だけで済む。

例（短縮版）:

```yaml
generated_at: "2025-12-09T18:30:00+09:00"
language: "ja"
time_range: "last_30_days"
ideas:
  - id: "20251209-001"
    keyword: "ミャクミャク"
    category: "ネット流行語"
    region: "JP"
    title: "大阪万博キャラ『ミャクミャク』が炎上した本当の理由3選"
    brief: >
      2025年SNS流行語大賞の年間大賞にも選ばれた大阪万博公式キャラクター『ミャクミャク』。
      かわいい・怖い・気持ち悪いと評価が割れた理由は何だったのか？
    thumbnail:
      headline: "ミャクミャク炎上の裏側"
      subhead: "大阪万博キャラに何が？"
    tags: ["雑学", "ネット文化", "大阪万博", "2025年トレンド"]
    suggested_theme_id: "trivia_social"
    priority_score: 0.96
    estimated_lifespan_days: 90
    nsfw: false
```

---

## Codex への依頼メッセージ例

このドキュメントを読んだ Codex に対して、具体的にやってほしいことを指示するときの例:

> * この仕様書に従って、
>
>   * `scripts/fetch_trend_ideas_llm.py` を新規作成し、
>   * `scripts/auto_trend_pipeline.py` に `--source llm` モードを追加してください。
> * LLM呼び出し部分は、現在の `ai_settings.json` と環境変数の構成に合わせて実装してください。
> * レスポンスJSONは上記スキーマに沿っている前提で、最低限のエラーハンドリング（JSONパース失敗・ideasが空など）も入れてください。

---

以上。
このファイルをリポジトリ内に置いておけば、Codex に

> 「AGENT_GUIDE.md を読んで、この仕様どおりに LLM トレンドパイプラインを実装して」

とお願いするだけで、ある程度狙いどおりのコードが出てくる想定です。

```
::contentReference[oaicite:0]{index=0}
```

## 追加要件: 定期実行タスク管理 (UI)

トレンド→台本生成→動画生成→YouTubeアップロードまでを、UIからスケジュール実行できるようにする。要件の骨子は以下。

- 新規「定期実行タスク管理」画面を追加。タスク一覧、追加、削除、手動実行、有効/無効トグルを持つ。
- タスク設定項目:
  - トレンドソース: `LLM` または `YouTube mostPopular`
  - テーマ: `freeform_prompt` 固定
  - セクション: intro / outro は必須、中間セクション数はAIに任せる旨をブリーフに自動で付与
  - max-keywords（1回で処理する件数）、実行インターバル（分/時間）
  - 自動YouTubeアップロード: ON/OFF を選択
- 実行フロー:
  - UI設定 → メインプロセスがタスクを永続化（例: settings/schedule.json）し、タイマーで `auto_trend_pipeline.py` を起動
  - `--source {llm|youtube}` を指定し、`--theme-id freeform_prompt` で実行
  - `--max-keywords` のデフォルトは 10 件（取得上限として使い、AIが優先度順に採用）
  - 成功/失敗ログを `logs/scheduler/` に保存。リトライは不要だがエラーは記録。
- UI要件:
  - 複数タスクをリスト表示
  - タスク追加ボタン / 削除ボタン
  - 各タスクの最終実行結果とログへの導線を表示
