#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Iterable, List, Optional

import yaml
try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
except ImportError:  # pragma: no cover
    Image = ImageDraw = ImageFont = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
try:
    from scripts._importlib_metadata_compat import ensure_importlib_metadata_compat  # type: ignore
except Exception:  # pragma: no cover - fallback if import fails
    ensure_importlib_metadata_compat = None  # type: ignore

if ensure_importlib_metadata_compat:
    ensure_importlib_metadata_compat()
try:
    from scripts.fetch_trend_ideas_llm import fetch_trend_ideas_via_llm  # type: ignore
except Exception:
    fetch_trend_ideas_via_llm = None

TOPIC_HISTORY_DEFAULT = PROJECT_ROOT / "work" / "topic_history.json"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", text).strip("-").lower()
    return slug or "keyword"


def normalize_keyword_text(value: str | None) -> str:
    return (value or "").strip().lower()


def parse_timestamp(value: str | None) -> Optional[datetime.datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        return None


def prune_topic_history(entries: List[dict], window_days: int) -> List[dict]:
    if window_days <= 0:
        return entries
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=window_days)
    filtered: List[dict] = []
    for entry in entries:
        ts = parse_timestamp(entry.get("ts"))
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)
        if ts and ts >= cutoff:
            filtered.append(entry)
    return filtered


def load_topic_history(path: Path, window_days: int) -> tuple[List[dict], set]:
    entries: List[dict] = []
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                entries = [entry for entry in data if isinstance(entry, dict)]
        except json.JSONDecodeError:
            print(f"[WARN] topic history {path} が壊れているためリセットします。")
    entries = prune_topic_history(entries, window_days)
    lookup = {normalize_keyword_text(entry.get("keyword")) for entry in entries if entry.get("keyword")}
    return entries, lookup


def save_topic_history(path: Path, entries: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def record_topic_history(
    path: Path,
    entries: List[dict],
    lookup: set,
    keywords: List[str],
    window_days: int,
) -> tuple[List[dict], set]:
    if not keywords:
        return entries, lookup
    now_iso = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    for kw in keywords:
        norm = normalize_keyword_text(kw)
        if not norm:
            continue
        entries.append({"keyword": kw, "ts": now_iso})
        lookup.add(norm)
    entries = prune_topic_history(entries, window_days)
    save_topic_history(path, entries)
    return entries, lookup


def run_script_generation(
    keyword: str,
    brief_template: str,
    theme_id: str,
    sections: int,
    output_dir: Path,
    brief_override: Optional[str] = None,
    extra_keyword: Optional[str] = None,
) -> Optional[Path]:
    """Invoke generate_script_from_brief.py to produce a Script YAML for the keyword."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    effective_kw = f"{extra_keyword} {keyword}".strip() if extra_keyword else keyword
    slug = slugify(effective_kw)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{slug}_{ts}.yaml"

    brief = brief_override or brief_template.format(keyword=effective_kw)
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "generate_script_from_brief.py"),
        "--brief",
        brief,
        "--theme-id",
        theme_id,
        "--sections",
        str(sections),
        "--output",
        str(output_path),
    ]
    print(f"[INFO] Generating script for '{keyword}' -> {output_path}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"[ERROR] Script generation failed for '{keyword}'. 詳細は上記ログを確認してください。")
        return None
    return output_path


def override_short_mode(script_path: Path, short_mode: str) -> None:
    """Force-set video.short_mode on the generated script if specified."""
    if short_mode == "inherit":
        return
    try:
        data = yaml.safe_load(script_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return
        video_cfg = data.get("video")
        if not isinstance(video_cfg, dict):
            video_cfg = {}
            data["video"] = video_cfg
        video_cfg["short_mode"] = short_mode
        script_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    except Exception as err:
        print(f"[WARN] short_mode の上書きに失敗しました: {err}")


def run_video_generation(script_path: Path, config_path: Optional[Path], adjust_tickers: bool = False) -> Optional[Path]:
    """Invoke generate_video.py for the given script."""
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "generate_video.py"),
        "--script",
        str(script_path),
    ]
    if adjust_tickers:
        cmd.append("--adjust-tickers")
    if config_path:
        cmd += ["--config", str(config_path)]
    print(f"[INFO] Generating video for {script_path}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"[ERROR] Video generation failed for {script_path}. 詳細は上記ログを確認してください。")
        return None

    # Best-effort: list newest mp4 under outputs/rendered
    rendered_dir = PROJECT_ROOT / "outputs" / "rendered"
    if not rendered_dir.exists():
        return None
    mp4s = sorted(rendered_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    return mp4s[0] if mp4s else None


def clear_audio_cache(work_dir: Path) -> None:
    """Remove cached audio to avoid reuse across runs."""
    targets = [work_dir / "audio", work_dir / "video", work_dir / "tmp"]
    for target in targets:
        if target.exists():
            try:
                shutil.rmtree(target)
                print(f"[INFO] Cleared cache: {target}")
            except Exception as err:
                print(f"[WARN] Failed to clear cache {target}: {err}")


PRIVACY_CHOICES = {"private", "unlisted", "public"}
THUMBNAIL_FONT_CANDIDATES = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]
THUMBNAIL_SIZE = (1280, 720)
THUMBNAIL_BG = "#0e121b"
THUMBNAIL_STROKE = "#050910"
THUMBNAIL_FILL = "#FFD166"


def _load_thumbnail_font(size: int):
    if not ImageFont:
        return None
    for candidate in THUMBNAIL_FONT_CANDIDATES:
        if not candidate:
            continue
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    try:
        return ImageFont.truetype("ArialUnicode.ttf", size)
    except OSError:
        return ImageFont.load_default()


def generate_thumbnail_from_title(title: str) -> Optional[Path]:
    if not Image or not title:
        return None
    try:
        img = Image.new("RGB", THUMBNAIL_SIZE, THUMBNAIL_BG)
        draw = ImageDraw.Draw(img)
        font = _load_thumbnail_font(96)
        if not font:
            return None
        lines = textwrap.wrap(title.strip(), width=10) or [title.strip()]
        bbox = font.getbbox("あ")
        line_height = (bbox[3] - bbox[1]) + 10
        total_height = len(lines) * line_height
        y = max(40, (THUMBNAIL_SIZE[1] - total_height) // 2)
        for line in lines:
            if not line:
                continue
            text_bbox = draw.textbbox((0, 0), line, font=font, stroke_width=6)
            line_width = text_bbox[2] - text_bbox[0]
            x = max(40, (THUMBNAIL_SIZE[0] - line_width) // 2)
            draw.text(
                (x, y),
                line,
                font=font,
                fill=THUMBNAIL_FILL,
                stroke_width=6,
                stroke_fill=THUMBNAIL_STROKE,
            )
            y += line_height
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            img.save(tmp.name, format="PNG")
            return Path(tmp.name)
    except Exception as err:
        print(f"[WARN] Failed to generate thumbnail: {err}")
        return None


def extract_upload_metadata(script_path: Path) -> tuple[Optional[str], Optional[str], List[str]]:
    """Read upload_prep (title/desc/tags) from a generated script, if present."""
    try:
        with open(script_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        upload = data.get("upload_prep") or {}
        title = upload.get("title")
        desc = upload.get("desc")
        tags = upload.get("tags")
        tag_list = [t for t in tags if isinstance(t, str)] if isinstance(tags, list) else []
        return (
            title if isinstance(title, str) and title.strip() else None,
            desc if isinstance(desc, str) and desc.strip() else None,
            tag_list,
        )
    except Exception as err:
        print(f"[WARN] Failed to parse upload_prep from {script_path}: {err}")
        return None, None, []


def build_brief_from_keywords(keywords: List[str]) -> str:
    """Mimic the UI brief instructions using all trend keywords."""
    cleaned = [kw.strip() for kw in keywords if isinstance(kw, str) and kw.strip()]
    if not cleaned:
        return ""
    joined = " / ".join(cleaned[:20])
    lines = [
        f"キーワード候補: {joined}",
        "これらの中で重複・類似をまとめ、最も良い切り口を選んで構成してください。",
        "形式はランキング/解説/暴露など最適なものをAIが判断してください。",
        "イントロでフック→本編複数セクション→アウトロ/CTAの流れで。中間セクション数は内容に合わせて決めてください。",
        "視聴者が惹きつけられる切り口と、信頼性のある根拠を入れてください。",
    ]
    return "\n".join(lines)


def normalize_llm_topics(data: dict) -> List[dict]:
    topics: List[dict] = []
    seen = set()

    def add_topic(keyword, brief=None, related=None, fragments=None):
        kw = (keyword or "").strip()
        if not kw:
            return
        norm = normalize_keyword_text(kw)
        if norm in seen:
            return
        seen.add(norm)
        topic = {
            "keyword": kw,
            "brief": (brief or "").strip(),
            "related_keywords": related if isinstance(related, list) else [],
        }
        if fragments and isinstance(fragments, list):
            seeds = [frag.strip() for frag in fragments if isinstance(frag, str) and frag.strip()]
            if seeds:
                topic["seed_fragments"] = seeds
        topics.append(topic)

    ideas = data.get("ideas") if isinstance(data, dict) else []
    if isinstance(ideas, list):
        for item in ideas:
            if not isinstance(item, dict):
                continue
            related = item.get("related_keywords") if isinstance(item.get("related_keywords"), list) else []
            add_topic(
                item.get("keyword") or item.get("title"),
                item.get("brief"),
                related,
                item.get("seed_phrases"),
            )

    briefs = data.get("briefs")
    if isinstance(briefs, list):
        for entry in briefs:
            if not isinstance(entry, dict):
                continue
            related = entry.get("keywords") if isinstance(entry.get("keywords"), list) else None
            add_topic(
                entry.get("keyword"),
                entry.get("brief"),
                related,
                entry.get("seed_phrases"),
            )

    keywords = data.get("keywords")
    if isinstance(keywords, list):
        for kw in keywords:
            add_topic(kw)

    return topics


def fetch_llm_topics(args) -> List[dict]:
    if not fetch_trend_ideas_via_llm:
        print("[ERROR] --source llm は利用できません。scripts/fetch_trend_ideas_llm.py を確認してください。")
        return []
    try:
        data = fetch_trend_ideas_via_llm(
            max_ideas=args.max_keywords,
            language=args.language,
            category=args.llm_category,
            extra_keyword=args.extra_keyword,
        )
    except Exception as err:
        print(f"[ERROR] LLMからトピックを取得できませんでした: {err}")
        return []
    if not isinstance(data, dict):
        print("[WARN] LLM結果が不正です。")
        return []
    return normalize_llm_topics(data)


def maybe_upload_to_youtube(
    video_path: Path,
    title: str,
    description: str,
    tags: Iterable[str],
    client_secrets: Optional[Path],
    credentials_path: Optional[Path],
    privacy_status: str = "private",
    thumbnail_text: Optional[str] = None,
) -> bool:
    """Upload video to YouTube if dependencies and credentials are present."""
    if not client_secrets:
        print("[INFO] YouTube upload skipped: --youtube-client-secrets not provided.")
        return False
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import google.oauth2.credentials
        import pickle
    except ImportError:
        print("[WARN] youtube upload skipped: google-api-python-client/google-auth not installed.")
        return False

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    if credentials_path and credentials_path.exists():
        try:
            with open(credentials_path, "rb") as token:
                creds = pickle.load(token)
        except Exception:
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
            creds = flow.run_console()
        if credentials_path:
            credentials_path.parent.mkdir(parents=True, exist_ok=True)
            with open(credentials_path, "wb") as token:
                pickle.dump(creds, token)

    youtube = build("youtube", "v3", credentials=creds)
    privacy = (privacy_status or "private").lower()
    if privacy not in PRIVACY_CHOICES:
        privacy = "private"
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": list(tags),
            "categoryId": "22",  # People & Blogs
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    print(f"[INFO] Uploading {video_path} to YouTube...")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"[INFO] Upload progress: {pct}%")
    video_id = response.get("id")
    print(f"[INFO] Upload completed: https://youtube.com/watch?v={video_id}")
    thumb_path = None
    if thumbnail_text:
        thumb_path = generate_thumbnail_from_title(thumbnail_text)
    if thumb_path:
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumb_path)),
            ).execute()
            print(f"[INFO] Thumbnail uploaded from {thumb_path}")
        except Exception as err:
            print(f"[WARN] Failed to upload thumbnail: {err}")
        finally:
            try:
                thumb_path.unlink()
            except OSError:
                pass
    return True


def run_once(args: argparse.Namespace) -> None:
    tasks: list[dict] = []
    history_entries, history_lookup = load_topic_history(args.history_file, args.history_days)

    def is_duplicate(keyword: str) -> bool:
        return normalize_keyword_text(keyword) in history_lookup

    topics = fetch_llm_topics(args)
    if not topics:
        print("[WARN] LLM からトピックが取得できませんでした。")
        return
    selected_topic = None
    for topic in topics:
        if not topic.get("keyword"):
            continue
        if is_duplicate(topic["keyword"]):
            continue
        selected_topic = topic
        break
    if not selected_topic:
        selected_topic = topics[0]
    if selected_topic:
        kw = selected_topic["keyword"]
        if selected_topic.get("brief"):
            brief = selected_topic["brief"]
        elif selected_topic.get("related_keywords"):
            brief = build_brief_from_keywords([kw, *selected_topic.get("related_keywords", [])])
        else:
            brief = args.brief_template.format(keyword=kw)
        fragments = selected_topic.get("seed_fragments") or []
        if fragments:
            fragment_text = "\n元フレーズ案 (短い断言で記述):\n" + "\n".join(f"- {frag}" for frag in fragments)
            brief = f"{brief}\n\n{fragment_text}"
        tasks.append({"keyword": kw, "brief": brief, "theme_id": args.theme_id, "extra_kw": args.extra_keyword})

    output_script_dir = PROJECT_ROOT / "scripts" / "generated" / "auto_trend"
    # Clear audio/cache before each cycle if requested
    if args.clear_cache:
        clear_audio_cache(PROJECT_ROOT / "work")

    if tasks:
        keywords_to_record = [
            (f"{task.get('extra_kw')} {task['keyword']}".strip() if task.get("extra_kw") else task["keyword"])
            for task in tasks
            if task.get("keyword")
        ]
        history_entries, history_lookup = record_topic_history(
            args.history_file, history_entries, history_lookup, keywords_to_record, args.history_days
        )

    for item in tasks:
        kw = item["keyword"]
        brief = item["brief"]
        theme_id = item["theme_id"]
        script_path = run_script_generation(
            keyword=kw,
            brief_template=args.brief_template,
            theme_id=theme_id,
            sections=args.sections,
            output_dir=output_script_dir,
            brief_override=brief,
            extra_keyword=item.get("extra_kw"),
        )
        if not script_path:
            continue
        override_short_mode(script_path, args.short_mode)
        video_path = run_video_generation(
            script_path,
            args.config,
            adjust_tickers=args.adjust_tickers,
        )
        if not video_path:
            continue
        try:
            rendered_script_path = video_path.with_suffix(".yaml")
            shutil.copy2(script_path, rendered_script_path)
            print(f"[INFO] Saved script snapshot: {rendered_script_path}")
        except Exception as err:
            print(f"[WARN] Failed to archive script next to video: {err}")

        if args.youtube_client_secrets:
            meta_title, meta_desc, meta_tags = extract_upload_metadata(script_path)
            title = meta_title or f"{kw} トレンド解説"
            desc = meta_desc or f"{kw} に関する自動生成動画です。作成日時: {datetime.datetime.now():%Y-%m-%d %H:%M}"
            tags = meta_tags or [kw, "トレンド", "自動生成"]
            try:
                maybe_upload_to_youtube(
                    video_path=video_path,
                    title=title,
                    description=desc,
                    tags=tags,
                    client_secrets=args.youtube_client_secrets,
                    credentials_path=args.youtube_credentials,
                    privacy_status=args.youtube_privacy,
                    thumbnail_text=title,
                )
            except Exception as err:
                print(f"[WARN] YouTube upload skipped/failed but処理を継続します: {err}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate scripts/videos directly from AI-generated monthly topics (optionally upload to YouTube)."
    )
    parser.add_argument(
        "--short-mode",
        choices=["off", "auto", "short", "inherit"],
        default="auto",
        help="video.short_mode を上書きする（auto: 60秒以下で縦長, inherit: 生成結果そのまま）",
    )
    parser.add_argument(
        "--max-keywords",
        type=int,
        default=10,
        help="LLM に要求するトピック数。履歴で重複除外した後、1件を採用します。",
    )
    parser.add_argument("--language", default="ja", help="LLMソース時の言語ヒント (default: ja)")
    parser.add_argument("--llm-category", default=None, help="LLMソース時のカテゴリを固定したい場合に指定（任意）")
    parser.add_argument(
        "--extra-keyword",
        default=None,
        help="任意の追加キーワード（20文字以内推奨）。ブリーフ生成時に先頭へ付与。",
    )
    parser.add_argument(
        "--brief-template",
        default=(
            "「{keyword}」について解説してください。導入(intro)でフックを入れ、"
            "本編は複数セクションに分けて要点を解説し、最後(outro)でまとめとCTAを入れてください。"
            "セクション数は内容に合わせてAIが決めて構いません。"
        ),
        help="Template for AI brief. '{keyword}' will be replaced with the trend keyword.",
    )
    parser.add_argument("--theme-id", default="lifehack_surprise", help="Theme ID under configs/themes/.")
    parser.add_argument("--sections", type=int, default=5, help="Number of sections per script.")
    parser.add_argument("--config", type=Path, help="Optional config YAML/JSON for generate_video.py.")
    parser.add_argument(
        "--adjust-tickers",
        action="store_true",
        default=True,
        help="テロップ幅を自動調整してから動画生成する（generate_video.py --adjust-tickers を付与）",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=0,
        help="If >0, repeat the cycle every N minutes (until --max-runs is reached or interrupted).",
    )
    parser.add_argument("--max-runs", type=int, default=0, help="If >0, stop after this many cycles when looping.")
    parser.add_argument("--youtube-client-secrets", type=Path, help="client_secrets.json for YouTube upload (optional).")
    parser.add_argument(
        "--youtube-credentials",
        type=Path,
        help="Path to store OAuth credentials for YouTube upload (optional but recommended when uploading).",
    )
    parser.add_argument(
        "--youtube-privacy",
        choices=["private", "unlisted", "public"],
        default="private",
        help="Upload privacyStatus when sending to YouTube (default: private).",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear work/audio and related caches before each cycle.",
    )
    parser.add_argument(
        "--history-file",
        type=Path,
        default=TOPIC_HISTORY_DEFAULT,
        help="キーワード重複管理の履歴ファイルパス (default: work/topic_history.json)。",
    )
    parser.add_argument(
        "--history-days",
        type=int,
        default=30,
        help="履歴に保持する日数。0 を指定すると重複除外しません。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    # 自動実行では必ずテロップ調整を有効化する
    args.adjust_tickers = True
    runs = 0
    while True:
        runs += 1
        print(f"[INFO] === Auto trend cycle #{runs} ===")
        run_once(args)
        if args.interval_minutes <= 0:
            break
        if args.max_runs and runs >= args.max_runs:
            break
        time.sleep(args.interval_minutes * 60)


if __name__ == "__main__":
    main()
