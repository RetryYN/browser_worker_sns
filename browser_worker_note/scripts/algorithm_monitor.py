"""
アルゴリズム変動監視

使い方:
  # 異常検知チェック（週次データ蓄積後）
  python scripts/algorithm_monitor.py check

  # 仕様変更の記録
  python scripts/algorithm_monitor.py log-change --description "リプライの重み変更" --source "https://..."

  # ベースライン表示
  python scripts/algorithm_monitor.py baseline

設計: knowledge/sites/common/dashboard-design.md §4
設定: config/platforms.yaml §algorithm_monitor
"""

from __future__ import annotations

import argparse
import statistics
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "platforms.yaml"
WEEKLY_DIR = ROOT / "knowledge" / "logs" / "x" / "weekly"
ALGO_DIR = ROOT / "knowledge" / "logs" / "x" / "algorithm"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


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
# 週次データ収集
# =========================================================================
def collect_weekly_data() -> list[dict]:
    """週次レポートから ER と IMP を時系列で取得。"""
    if not WEEKLY_DIR.exists():
        return []
    data = []
    for f in sorted(WEEKLY_DIR.glob("*.yaml")):
        with open(f, encoding="utf-8") as fh:
            wr = yaml.safe_load(fh)
            if wr and "summary" in wr:
                s = wr["summary"]
                data.append({
                    "week": wr.get("week", "?"),
                    "avg_er": s.get("avg_engagement_rate", 0),
                    "avg_score": s.get("avg_composite_score", 0),
                    "total_imp": s.get("total_impressions", 0),
                    "total_rep": s.get("total_replies", 0),
                })
    return data


# =========================================================================
# ベースライン算出
# =========================================================================
def calculate_baseline(weekly_data: list[dict], window_weeks: int = 12) -> dict:
    """移動平均とσを算出してベースラインを返す。"""
    if not weekly_data:
        return {"status": "データ不足", "window_weeks": window_weeks}

    # 直近 window_weeks 分
    recent = weekly_data[-window_weeks:]

    ers = [w["avg_er"] for w in recent]
    imps = [w["total_imp"] for w in recent]

    er_mean = statistics.mean(ers) if ers else 0.0
    er_std = statistics.stdev(ers) if len(ers) > 1 else 0.0
    imp_mean = statistics.mean(imps) if imps else 0.0
    imp_std = statistics.stdev(imps) if len(imps) > 1 else 0.0

    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d"),
        "window_weeks": window_weeks,
        "actual_weeks": len(recent),
        "engagement_rate_mean": round(er_mean, 3),
        "engagement_rate_std": round(er_std, 3),
        "impressions_mean": round(imp_mean, 1),
        "impressions_std": round(imp_std, 1),
    }


# =========================================================================
# 異常検知
# =========================================================================
def detect_anomalies(weekly_data: list[dict], baseline: dict, threshold_sigma: float = 2.0) -> list[dict]:
    """直近の週次データで ER が baseline ± threshold_sigma * σ を逸脱していないかチェック。"""
    anomalies = []

    er_mean = baseline.get("engagement_rate_mean", 0)
    er_std = baseline.get("engagement_rate_std", 0)

    if er_std == 0:
        return anomalies  # σ=0 なら検知不可

    upper = er_mean + threshold_sigma * er_std
    lower = er_mean - threshold_sigma * er_std

    for w in weekly_data[-4:]:  # 直近4週をチェック
        er = w["avg_er"]
        if er > upper or er < lower:
            deviation = (er - er_mean) / er_std if er_std else 0
            anomalies.append({
                "week": w["week"],
                "metric": "engagement_rate",
                "expected": round(er_mean, 3),
                "actual": er,
                "deviation_sigma": round(deviation, 2),
                "direction": "上昇" if er > upper else "下降",
                "cause": "",  # 手動記入
            })

    return anomalies


# =========================================================================
# チェック実行
# =========================================================================
def run_check() -> dict:
    """異常検知を実行して結果を表示・記録。"""
    from system_logger import log_task

    config = load_config()
    algo_cfg = config.get("algorithm_monitor", {})
    window = algo_cfg.get("baseline_window_weeks", 12)
    threshold = algo_cfg.get("anomaly_threshold_sigma", 2.0)

    with log_task("algorithm-monitor-check") as task:
        weekly_data = collect_weekly_data()

        if len(weekly_data) < 3:
            print(f"\n週次データ不足: {len(weekly_data)}週（最低3週必要）")
            task.note(f"データ不足: {len(weekly_data)}週")
            return {"status": "データ不足", "weeks": len(weekly_data)}

        baseline = calculate_baseline(weekly_data, window)
        anomalies = detect_anomalies(weekly_data, baseline, threshold)

        # 月次ログに記録
        now = datetime.now()
        month = now.strftime("%Y-%m")
        log_path = ALGO_DIR / f"{month}.yaml"

        existing = _load_yaml(log_path) or {
            "platform": "x",
            "month": month,
            "anomalies": [],
            "spec_changes": [],
            "baseline": {},
        }

        existing["baseline"] = baseline
        # 新しい異常のみ追加（重複チェック）
        existing_weeks = {a["week"] for a in existing.get("anomalies", [])}
        for a in anomalies:
            if a["week"] not in existing_weeks:
                existing["anomalies"].append(a)

        _save_yaml(log_path, existing)

        # 表示
        print(f"\n{'='*50}")
        print(f"アルゴリズム監視チェック: {month}")
        print(f"{'='*50}")
        print(f"週次データ: {len(weekly_data)}週（ベースライン窓: {baseline['actual_weeks']}週）")
        print(f"ER 平均: {baseline['engagement_rate_mean']}% ± {baseline['engagement_rate_std']}%")
        print(f"閾値: ±{threshold}σ → [{round(baseline['engagement_rate_mean'] - threshold * baseline['engagement_rate_std'], 2)}%, {round(baseline['engagement_rate_mean'] + threshold * baseline['engagement_rate_std'], 2)}%]")
        print()

        if anomalies:
            print(f"⚠ 異常検知: {len(anomalies)}件")
            for a in anomalies:
                print(f"  {a['week']}: ER={a['actual']}% (期待値{a['expected']}%, {a['deviation_sigma']}σ {a['direction']})")
            task.note(f"異常検知: {len(anomalies)}件")
        else:
            print("✓ 異常なし")
            task.note("異常なし")

        print(f"{'='*50}\n")
        return {"baseline": baseline, "anomalies": anomalies}


# =========================================================================
# 仕様変更記録
# =========================================================================
def log_spec_change(description: str, source: str = "", impact: str = "medium") -> None:
    """プラットフォーム仕様変更を記録。"""
    now = datetime.now()
    month = now.strftime("%Y-%m")
    log_path = ALGO_DIR / f"{month}.yaml"

    existing = _load_yaml(log_path) or {
        "platform": "x",
        "month": month,
        "anomalies": [],
        "spec_changes": [],
        "baseline": {},
    }

    existing["spec_changes"].append({
        "date": now.strftime("%Y-%m-%d"),
        "description": description,
        "source": source,
        "impact": impact,
        "action_taken": "",
    })

    _save_yaml(log_path, existing)
    print(f"仕様変更を記録: {description}")


# =========================================================================
# ベースライン表示
# =========================================================================
def show_baseline() -> None:
    """現在のベースラインを表示。"""
    weekly_data = collect_weekly_data()
    if not weekly_data:
        print("週次データなし")
        return

    config = load_config()
    window = config.get("algorithm_monitor", {}).get("baseline_window_weeks", 12)
    baseline = calculate_baseline(weekly_data, window)

    print(f"\n{'='*50}")
    print("アルゴリズム監視ベースライン")
    print(f"{'='*50}")
    print(f"更新日: {baseline.get('updated_at', '?')}")
    print(f"ウィンドウ: {baseline.get('window_weeks', '?')}週（実データ: {baseline.get('actual_weeks', '?')}週）")
    print(f"ER 平均: {baseline.get('engagement_rate_mean', 0)}%")
    print(f"ER 標準偏差: {baseline.get('engagement_rate_std', 0)}%")
    print(f"IMP 平均: {baseline.get('impressions_mean', 0)}")
    print(f"IMP 標準偏差: {baseline.get('impressions_std', 0)}")
    print(f"{'='*50}\n")


# =========================================================================
# CLI
# =========================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="アルゴリズム変動監視")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="異常検知チェック")

    lc = sub.add_parser("log-change", help="仕様変更の記録")
    lc.add_argument("--description", required=True, help="変更内容")
    lc.add_argument("--source", default="", help="情報ソース URL")
    lc.add_argument("--impact", choices=["high", "medium", "low"], default="medium", help="影響度")

    sub.add_parser("baseline", help="ベースライン表示")

    args = parser.parse_args()

    if args.command == "check":
        run_check()
    elif args.command == "log-change":
        log_spec_change(args.description, args.source, args.impact)
    elif args.command == "baseline":
        show_baseline()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
