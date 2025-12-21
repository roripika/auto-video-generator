#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_DIR = PROJECT_ROOT / "settings"
SCHEDULE_FILE = SETTINGS_DIR / "schedule.json"
AI_SETTINGS_FILE = SETTINGS_DIR / "ai_settings.json"
AUTO_TREND_SCRIPT = PROJECT_ROOT / "scripts" / "auto_trend_pipeline.py"
SCHED_LOG_DIR = PROJECT_ROOT / "logs" / "scheduler"


def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"[WARN] Failed to parse JSON: {path}")
        return None


def load_ai_settings() -> dict:
    data = load_json(AI_SETTINGS_FILE)
    return data if isinstance(data, dict) else {}


def load_schedule() -> List[dict]:
    data = load_json(SCHEDULE_FILE)
    return [item for item in data or [] if isinstance(item, dict)]


def get_latest_log_time(task_id: str) -> Optional[dt.datetime]:
    if not SCHED_LOG_DIR.exists():
        return None
    best = None
    for file in SCHED_LOG_DIR.glob(f"{task_id}-*.log"):
        try:
            mtime = dt.datetime.fromtimestamp(file.stat().st_mtime, tz=dt.timezone.utc)
        except OSError:
            continue
        if not best or mtime > best:
            best = mtime
    return best


def clamp_int(value, default: int, minimum: int = 1) -> int:
    try:
        parsed = int(value)
        return parsed if parsed >= minimum else minimum
    except (ValueError, TypeError):
        return default


@dataclass
class TaskState:
    task: dict
    next_run: dt.datetime


def compute_next_run(task: dict, last_run: Optional[dt.datetime]) -> dt.datetime:
    now = dt.datetime.now(dt.timezone.utc)
    interval_minutes = clamp_int(task.get("interval_minutes"), 1440)
    interval = dt.timedelta(minutes=interval_minutes)
    if last_run:
        due = last_run + interval
        return due if due > now else now
    offset_minutes = task.get("start_offset_minutes")
    try:
        offset = int(offset_minutes)
        if offset < 0:
            offset = 0
    except (TypeError, ValueError):
        offset = interval_minutes
    return now + dt.timedelta(minutes=offset)


def build_task_command(task: dict, ai_settings: dict) -> List[str]:
    args = [
        sys.executable,
        str(AUTO_TREND_SCRIPT),
        "--max-keywords",
        str(clamp_int(task.get("max_keywords"), 10)),
        "--theme-id",
        "freeform_prompt",
    ]
    # LLM カテゴリ/追加キーワードが設定されていれば引き渡す
    category = task.get("category")
    if isinstance(category, str) and category.strip():
        args += ["--llm-category", category]
    extra_kw = task.get("extra_keyword")
    if isinstance(extra_kw, str) and extra_kw.strip():
        args += ["--extra-keyword", extra_kw]
    if task.get("clear_cache", True):
        args.append("--clear-cache")
    if task.get("auto_upload", True):
        client_path = ai_settings.get("youtubeClientSecretsPath")
        creds_path = ai_settings.get("youtubeCredentialsPath")
        privacy = ai_settings.get("youtubePrivacyStatus")
        if client_path:
            args += ["--youtube-client-secrets", str(Path(client_path).expanduser())]
        if creds_path:
            args += ["--youtube-credentials", str(Path(creds_path).expanduser())]
        if privacy:
            args += ["--youtube-privacy", privacy]
    return args


def run_task(task: dict, ai_settings: dict) -> Path:
    SCHED_LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.utcnow().isoformat(timespec="seconds").replace(":", "-")
    log_path = SCHED_LOG_DIR / f"{task.get('id', 'task')}-{timestamp}.log"
    cmd = build_task_command(task, ai_settings)
    print(f"[INFO] Running task {task.get('id')} -> {' '.join(cmd)}")
    with log_path.open("w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(cmd, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert proc.stdout is not None
        for line in proc.stdout:
            log_file.write(line)
            log_file.flush()
            print(line.rstrip())
        proc.wait()
    print(f"[INFO] Task {task.get('id')} finished with exit code {proc.returncode}. Log: {log_path}")
    return log_path


def refresh_states(states: Dict[str, TaskState], ai_settings: dict) -> Dict[str, TaskState]:
    schedule = load_schedule()
    new_states: Dict[str, TaskState] = {}
    for task in schedule:
        if task.get("enabled") is False:
            continue
        task_id = task.get("id")
        if not task_id:
            continue
        last_run = get_latest_log_time(task_id)
        if task_id in states:
            st = states[task_id]
            if st.task != task:
                next_run = compute_next_run(task, last_run)
                new_states[task_id] = TaskState(task=task, next_run=next_run)
            else:
                new_states[task_id] = st
        else:
            next_run = compute_next_run(task, last_run)
            new_states[task_id] = TaskState(task=task, next_run=next_run)
    return new_states


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run saved scheduler tasks without launching the desktop app. Keep this script running."
    )
    parser.add_argument("--poll-seconds", type=int, default=60, help="Polling interval for reloading tasks.")
    parser.add_argument("--run-once", action="store_true", help="Run any due tasks once then exit.")
    args = parser.parse_args()

    ai_settings = load_ai_settings()
    states: Dict[str, TaskState] = {}
    executed_once = False
    try:
        while True:
            states = refresh_states(states, ai_settings)
            now = dt.datetime.now(dt.timezone.utc)
            ran_this_cycle = False
            for task_id, st in list(states.items()):
                if now >= st.next_run:
                    run_task(st.task, ai_settings)
                    st.next_run = compute_next_run(st.task, dt.datetime.now(dt.timezone.utc))
                    ran_this_cycle = True
                    executed_once = True
            if args.run_once and executed_once:
                break
            time.sleep(max(5, args.poll_seconds))
    except KeyboardInterrupt:
        print("[INFO] Scheduler daemon stopped by user.")


if __name__ == "__main__":
    main()
