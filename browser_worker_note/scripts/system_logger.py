"""
システムログ記録モジュール

タスク実行ログ・エラーログを knowledge/logs/system/ に記録する。
他のスクリプトから import して使う。

使い方:
  from system_logger import log_task, log_error

  # タスク実行ログ
  with log_task("x-post-publish") as task:
      # ... 処理 ...
      task.note("予約投稿完了")      # 任意のメモ

  # エラーログ（手動）
  log_error("x-post-publish", "ログインセッション切れ", details="再認証が必要")

  # CLI でログ確認
  python scripts/system_logger.py show --month 2026-03
  python scripts/system_logger.py show --errors
  python scripts/system_logger.py stats
"""

from __future__ import annotations

import argparse
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

import yaml

ROOT = Path(__file__).resolve().parent.parent
SYSTEM_DIR = ROOT / "knowledge" / "logs" / "system"
TASKS_DIR = SYSTEM_DIR / "tasks"
ERRORS_DIR = SYSTEM_DIR / "errors"


# =========================================================================
# タスク実行ログ
# =========================================================================
class TaskContext:
    """タスク実行のコンテキスト。with 文で使用。"""

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.start_time = datetime.now()
        self.start_ts = time.time()
        self.status = "success"
        self.error_msg = ""
        self.notes: list[str] = []
        self.retries = 0

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    def retry(self) -> None:
        self.retries += 1

    def fail(self, error: str) -> None:
        self.status = "failure"
        self.error_msg = error


@contextmanager
def log_task(task_name: str) -> Generator[TaskContext, None, None]:
    """タスク実行をログに記録するコンテキストマネージャ。"""
    ctx = TaskContext(task_name)
    try:
        yield ctx
    except Exception as e:
        ctx.status = "failure"
        ctx.error_msg = str(e)
        # エラーログにも記録
        log_error(task_name, str(e), details=traceback.format_exc())
        raise
    finally:
        duration = round(time.time() - ctx.start_ts, 1)
        _write_task_log(ctx, duration)


def _write_task_log(ctx: TaskContext, duration: float) -> None:
    """タスク実行ログを YAML に追記。"""
    month = ctx.start_time.strftime("%Y-%m")
    log_path = TASKS_DIR / f"{month}.yaml"

    TASKS_DIR.mkdir(parents=True, exist_ok=True)

    # 既存データ読み込み
    data = _load_yaml(log_path) or {
        "month": month,
        "executions": [],
        "summary": {
            "total_executions": 0,
            "success_count": 0,
            "failure_count": 0,
            "success_rate": 0.0,
            "avg_duration_sec": 0.0,
            "most_common_errors": [],
        },
    }

    # 実行記録追加
    entry = {
        "task": ctx.task_name,
        "timestamp": ctx.start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": ctx.status,
        "duration_sec": duration,
        "error": ctx.error_msg,
        "retries": ctx.retries,
        "notes": ctx.notes if ctx.notes else [],
    }
    data["executions"].append(entry)

    # サマリー更新
    execs = data["executions"]
    total = len(execs)
    success = sum(1 for e in execs if e["status"] == "success")
    failure = total - success
    durations = [e["duration_sec"] for e in execs]
    avg_dur = round(sum(durations) / len(durations), 1) if durations else 0.0

    # エラー頻度集計
    error_counts: dict[str, int] = {}
    for e in execs:
        if e.get("error"):
            # エラーメッセージの先頭50文字でグルーピング
            key = e["error"][:50]
            error_counts[key] = error_counts.get(key, 0) + 1
    common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    data["summary"] = {
        "total_executions": total,
        "success_count": success,
        "failure_count": failure,
        "success_rate": round(success / total * 100, 1) if total else 0.0,
        "avg_duration_sec": avg_dur,
        "most_common_errors": [{"error": e, "count": c} for e, c in common_errors],
    }

    _save_yaml(log_path, data)


# =========================================================================
# エラーログ
# =========================================================================
def log_error(task_name: str, error: str, *, details: str = "") -> None:
    """エラーを errors/ に記録。"""
    now = datetime.now()
    month = now.strftime("%Y-%m")
    log_path = ERRORS_DIR / f"{month}.yaml"

    ERRORS_DIR.mkdir(parents=True, exist_ok=True)

    data = _load_yaml(log_path) or {"month": month, "errors": []}

    data["errors"].append({
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "task": task_name,
        "error": error,
        "details": details[:500] if details else "",  # 長すぎるトレースバックを切る
    })

    _save_yaml(log_path, data)


# =========================================================================
# YAML I/O
# =========================================================================
def _load_yaml(path: Path) -> dict | None:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    return None


def _save_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


# =========================================================================
# CLI: ログ確認
# =========================================================================
def show_logs(month: str | None = None, errors_only: bool = False) -> None:
    """ログを表示。"""
    month = month or datetime.now().strftime("%Y-%m")

    if not errors_only:
        task_path = TASKS_DIR / f"{month}.yaml"
        if task_path.exists():
            data = _load_yaml(task_path)
            if data:
                s = data.get("summary", {})
                print(f"\n{'='*50}")
                print(f"タスク実行ログ: {month}")
                print(f"{'='*50}")
                print(f"実行回数: {s.get('total_executions', 0)}")
                print(f"成功: {s.get('success_count', 0)} / 失敗: {s.get('failure_count', 0)}")
                print(f"成功率: {s.get('success_rate', 0)}%")
                print(f"平均所要時間: {s.get('avg_duration_sec', 0)}秒")
                print()
                for e in data.get("executions", [])[-10:]:
                    status_mark = "OK" if e["status"] == "success" else "NG"
                    print(f"  {status_mark} {e['timestamp']} {e['task']} ({e['duration_sec']}秒) {e.get('error', '')}")
                    for n in e.get("notes", []):
                        print(f"    → {n}")
                print()
        else:
            print(f"\nタスクログなし: {month}")

    # エラー
    error_path = ERRORS_DIR / f"{month}.yaml"
    if error_path.exists():
        data = _load_yaml(error_path)
        if data:
            errors = data.get("errors", [])
            print(f"\n{'='*50}")
            print(f"エラーログ: {month} ({len(errors)}件)")
            print(f"{'='*50}")
            for e in errors[-10:]:
                print(f"  [{e['timestamp']}] {e['task']}: {e['error']}")
            print()
    else:
        if errors_only:
            print(f"\nエラーログなし: {month}")


def show_stats() -> None:
    """全期間の統計を表示。"""
    if not TASKS_DIR.exists():
        print("タスクログなし")
        return

    total_exec = 0
    total_success = 0
    task_counts: dict[str, int] = {}

    for f in sorted(TASKS_DIR.glob("*.yaml")):
        data = _load_yaml(f)
        if not data:
            continue
        for e in data.get("executions", []):
            total_exec += 1
            if e["status"] == "success":
                total_success += 1
            task_counts[e["task"]] = task_counts.get(e["task"], 0) + 1

    print(f"\n{'='*50}")
    print("システム統計（全期間）")
    print(f"{'='*50}")
    print(f"総実行回数: {total_exec}")
    print(f"成功率: {round(total_success / total_exec * 100, 1) if total_exec else 0}%")
    print(f"\nタスク別実行回数:")
    for task, count in sorted(task_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {task}: {count}回")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="システムログ管理")
    sub = parser.add_subparsers(dest="command")

    s = sub.add_parser("show", help="ログ表示")
    s.add_argument("--month", help="対象月 (YYYY-MM)", default=None)
    s.add_argument("--errors", action="store_true", help="エラーのみ表示")

    sub.add_parser("stats", help="全期間統計")

    args = parser.parse_args()

    if args.command == "show":
        show_logs(args.month, args.errors)
    elif args.command == "stats":
        show_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
