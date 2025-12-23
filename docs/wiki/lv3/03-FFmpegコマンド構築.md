# 🎬 FFmpegコマンド構築 (Lv3 詳細仕様)

## ✨ TL;DR
- YAML 台本 + タイムライン + 素材ファイル一覧から FFmpeg complex filter string を生成。
- 6 種類のフィルタ（drawtext, zoompan, sidechaincompress, concat, scale, pad）を組合せ。
- `src/render/ffmpeg_runner.py` の `build_ffmpeg_command()` 関数。
- 出力例：`-filter_complex "[0:v]scale=1080:1920[v1];[v1][1:v]overlay[out]"` 等。
- 実装ファイル：[src/render/ffmpeg_runner.py](../../../src/render/ffmpeg_runner.py) 行 200-400。

## 📚 用語・前提
- **complex filter**: 複数入力・複数出力を組合せるFFmpegフィルタチェーン。
- **drawtext**: テキスト（テロップ）を画像上に描画。
- **zoompan**: ズーム・パンアニメーション。
- **sidechaincompress**: オーディオ圧縮（BGM ダッキング）。
- **concat**: 複数の音声・映像を連結。
- **pad/scale**: フレームサイズ調整（ショート=1080x1920, 通常=1920x1080）。

## 🧭 背景
- FFmpeg CLI は長大なコマンド文字列が必要。タイムライン・テロップ・BGM・背景等の制御が複雑。
- Python で構造化して生成することで、保守性・再利用性・テスト容易性を確保。
- `--dry-run` オプションで FFmpeg コマンド確認可能。

## 🏗️ 実装詳細

### メイン関数：build_ffmpeg_command()（行 200-260）

#### 関数シグネチャ
```python
def build_ffmpeg_command(
    yaml_script: ScriptModel,
    timeline: Timeline,
    audio_dir: Path,
    output_mp4: Path,
    short_mode: bool = False,
    dry_run: bool = False
) -> Dict[str, Union[str, List[str]]]:
    """
    YAML 台本とタイムラインから FFmpeg complex filter + 入出力を構築。
    
    戻り値：
    {
        "inputs": ["-i", "video1.mp4", "-i", "audio.wav", ...],
        "filters": "-filter_complex [...complex filter string...]",
        "outputs": ["-c:v", "libx264", "-c:a", "aac", "-y", str(output_mp4)]
    }
    """
```

### 処理フロー

#### 1. 入力ファイル一覧生成（行 265-310）
```python
inputs = []
input_map = {}  # {file_path: input_index}
index = 0

# 背景画像
for section in yaml_script.sections:
    bg_file = Path(section.background_image_path)
    if bg_file not in input_map:
        inputs.extend(["-i", str(bg_file)])
        input_map[bg_file] = index
        index += 1

# BGM ファイル
if yaml_script.bgm_file:
    bgm_file = Path(yaml_script.bgm_file)
    inputs.extend(["-i", str(bgm_file)])
    input_map[bgm_file] = index
    index += 1

# 各セクションの音声ファイル
for section_timeline in timeline.sections:
    if section_timeline.audio_path:
        audio_file = section_timeline.audio_path
        if audio_file not in input_map:
            inputs.extend(["-i", str(audio_file)])
            input_map[audio_file] = index
            index += 1
```

#### 2. Filter Chain 構築（行 315-370）
```python
filters = []

# ビデオフィルタ群
video_filters = []

# Step 1: 背景画像スケール + パッド
for section_idx, section in enumerate(yaml_script.sections):
    bg_idx = input_map[Path(section.background_image_path)]
    
    if short_mode:
        # ショート（1080x1920）
        size = "1080x1920"
    else:
        # 通常（1920x1080）
        size = "1920x1080"
    
    # scale: 背景画像を target size に。
    video_filters.append(f"[{bg_idx}]scale={size}[bg{section_idx}]")

# Step 2: テロップ描画（drawtext）
for section_idx, section_timeline in enumerate(timeline.sections):
    # テロップの位置・サイズ・色は config から。
    text = section_timeline.on_screen_text
    
    # パラメータ
    x = "x=100"
    y = "y=1700" if short_mode else "y=1000"
    fontsize = "64" if short_mode else "80"
    fontfile = f"'{_resolve_font_path(section.font_name)}'"
    
    # drawtext フィルタ
    drawtext_filter = (
        f"[bg{section_idx}]"
        f"drawtext="
        f"text='{text}':"
        f"fontfile={fontfile}:"
        f"fontsize={fontsize}:"
        f"{x}:{y}:"
        f"fontcolor=white"
        f"[text{section_idx}]"
    )
    video_filters.append(drawtext_filter)

# Step 3: Zoom/Pan エフェクト
for section_idx, section in enumerate(yaml_script.sections):
    if hasattr(section, 'enable_zoom') and section.enable_zoom:
        zoom_filter = (
            f"[text{section_idx}]"
            f"zoompan=z='1.0+0.001*t':d=1:x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2)"
            f"[zoom{section_idx}]"
        )
        video_filters.append(zoom_filter)
    else:
        video_filters.append(f"[text{section_idx}]copy[zoom{section_idx}]")

# Step 4: 全セクション連結（concat）
concat_inputs = "".join([f"[zoom{i}]" for i in range(len(timeline.sections))])
concat_filter = f"{concat_inputs}concat=n={len(timeline.sections)}:v=1:a=0[video]"
video_filters.append(concat_filter)

filter_str = ";".join(video_filters)
```

#### 3. オーディオフィルタ（BGM ダッキング）（行 375-400）
```python
# 各セクション音声を時間軸で配置
audio_filters = []

# BGM
bgm_idx = input_map[Path(yaml_script.bgm_file)]
audio_filters.append(f"[{bgm_idx}]atrim=0:{timeline.total_duration}[bgm_main]")

# セクション音声を concat
narration_parts = []
for section_timeline in timeline.sections:
    if section_timeline.audio_path:
        audio_idx = input_map[section_timeline.audio_path]
        audio_filters.append(
            f"[{audio_idx}]atrim=0:{section_timeline.duration_sec}[sec{section_timeline.index}]"
        )
        narration_parts.append(f"[sec{section_timeline.index}]")

narration_str = "".join(narration_parts)
audio_filters.append(f"{narration_str}concat=n={len(timeline.sections)}:a=1:v=0[narration]")

# ダッキング（BGM を 0.7 倍に圧縮）
audio_filters.append("[bgm_main]volume=0.7[bgm_ducked]")

# BGM + Narration ミックス
audio_filters.append("[bgm_ducked][narration]amix=inputs=2:duration=longest[audio]")

audio_filter_str = ";".join(audio_filters)
```

#### 4. 入出力オプション（行 405-420）
```python
outputs = []

# ビデオコーデック
outputs.extend(["-c:v", "libx264"])
outputs.extend(["-preset", "medium"])  # fast/medium/slow

# オーディオコーデック
outputs.extend(["-c:a", "aac"])
outputs.extend(["-b:a", "128k"])

# 出力ファイル
outputs.extend(["-y", str(output_mp4)])

return {
    "inputs": inputs,
    "filters": f"-filter_complex '{filter_str};{audio_filter_str}'",
    "outputs": outputs
}
```

### ヘルパー関数

#### drawtext フォント解決（行 425-440）
```python
def _resolve_font_path(font_name: str) -> str:
    """
    font_name （例："Noto Sans JP"）から実パスを取得。
    フォント存在確認・文字化けチェック。
    """
    # cf. Lv3-01 フォント解決システム
    from render.ffmpeg_runner import _resolve_font_path
    return _resolve_font_path(font_name)
```

#### コマンド文字列への変換（行 445-470）
```python
def command_dict_to_list(cmd_dict: Dict) -> List[str]:
    """
    コマンド辞書を FFmpeg CLI 引数リストに変換。
    """
    cmd = ["ffmpeg"]
    cmd.extend(cmd_dict["inputs"])
    cmd.append(cmd_dict["filters"])
    cmd.extend(cmd_dict["outputs"])
    return cmd
```

#### Dry-Run（行 475-485）
```python
def print_ffmpeg_command(cmd_dict: Dict, dry_run: bool = False):
    """コマンドを表示（-y オプション除去）。"""
    cmd = command_dict_to_list(cmd_dict)
    
    # -y（上書き確認なし）を -n（上書き禁止）に置換
    if dry_run:
        cmd = ["-n" if c == "-y" else c for c in cmd]
    
    print(" ".join(cmd))
```

## 🔧 運用・デバッグ

### CLI でコマンド確認
```bash
python scripts/generate_video.py \
  --config configs/config.yaml \
  --script inputs/scripts_yaml/test.yaml \
  --dry-run
```

### FFmpeg コマンド実行例
```bash
ffmpeg \
  -i background1.jpg \
  -i background2.jpg \
  -i bgm.mp3 \
  -i narration1.wav \
  -i narration2.wav \
  -filter_complex \
    "[0]scale=1920:1080[bg0];" \
    "[bg0]drawtext=text='第1位':fontfile='/System/Library/Fonts/HiraKakuProN-W4.otf':fontsize=80:x=100:y=1000:fontcolor=white[text0];" \
    "[text0]copy[zoom0];" \
    "[1]scale=1920:1080[bg1];" \
    "[bg1]drawtext=text='第2位':...[text1];" \
    "[text1]copy[zoom1];" \
    "[zoom0][zoom1]concat=n=2:v=1:a=0[video];" \
    "[2]atrim=0:145.5[bgm_main];" \
    "[3]atrim=0:28.5[sec0];" \
    "[4]atrim=0:32.2[sec1];" \
    "[sec0][sec1]concat=n=2:a=1:v=0[narration];" \
    "[bgm_main]volume=0.7[bgm_ducked];" \
    "[bgm_ducked][narration]amix=inputs=2:duration=longest[audio]" \
  -map "[video]" \
  -map "[audio]" \
  -c:v libx264 \
  -preset medium \
  -c:a aac \
  -b:a 128k \
  -y output.mp4
```

### よくあるエラー

| エラー | 原因 | 対策 |
|------|------|------|
| `Unknown encoder 'libx264'` | FFmpeg ビルドに H.264 未含 | `brew install ffmpeg --with-x264` |
| `Too many connections` | 入力ファイルが多すぎて フォーク制限 | セクション数を減らす、または FFmpeg 設定を調整 |
| `fontfile not found` | フォントパス間違い | `_resolve_font_path()` ログで確認 |
| `concat demuxer error` | 音声フォーマット非互換 | 全音声を 16kHz/mono で統一 |

## 🔗 参考
- **実装ファイル**: [src/render/ffmpeg_runner.py](../../../src/render/ffmpeg_runner.py)
- **タイムライン**: [src/timeline.py](../../../src/timeline.py)（Lv3-02）
- **フォント解決**: [src/render/ffmpeg_runner.py#L43](../../../src/render/ffmpeg_runner.py#L43)（Lv3-01）
- **使用箇所**: [scripts/generate_video.py](../../../scripts/generate_video.py), [desktop-app/src/main/video-renderer.js](../../../desktop-app/src/main/video-renderer.js)
- **テスト**: [tests/test_ffmpeg_effects.py](../../../tests/test_ffmpeg_effects.py)
- **FFmpeg ドキュメント**: https://ffmpeg.org/ffmpeg-filters.html

## ✅ まとめ
- `build_ffmpeg_command()` で YAML + Timeline から complex filter string を生成。
- 背景→テロップ→Zoom/Pan→concat で映像、BGM→セクション音声→amix でオーディオ。
- フォント・タイムスタンプ・素材ファイルパスを正確に参照。
- `--dry-run` で確認後、実際の FFmpeg 実行。
- エラーハンドリング：入力チェック、コーデック確認、ファイル存在確認。

## 🚀 次のアクション
- 大規模セクション（100+）での filter string 最適化。
- GPU アクセラレーション（libx264_videotoolbox 等）対応。
- 複雑な Zoom/Pan シーケンスの自動生成。

## 🗓️ 追記/更新ログ
- 2025-12-23: 初版。Lv3 詳細仕様として作成。
