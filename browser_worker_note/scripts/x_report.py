"""
X投稿レポート & 入れ替えアルゴリズム

使い方:
  # 週間チェック（毎週金曜の投稿完了後）
  python scripts/x_report.py weekly

  # 月間チェック + 入れ替え判定（月末）
  python scripts/x_report.py monthly

  # 個別投稿のスコア算出（デバッグ用）
  python scripts/x_report.py score knowledge/logs/x/posts/2026-03-10_月.yaml

データ:
  knowledge/logs/x/posts/    個別レポート YAML
  knowledge/logs/x/weekly/   週間レポート YAML（出力先）
  knowledge/logs/x/monthly/  月間レポート YAML（出力先）

設計詳細: knowledge/sites/x/report-design.md
"""

from __future__ import annotations

import argparse
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# パス
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "knowledge" / "logs" / "x" / "posts"
WEEKLY_DIR = ROOT / "knowledge" / "logs" / "x" / "weekly"
MONTHLY_DIR = ROOT / "knowledge" / "logs" / "x" / "monthly"

# ---------------------------------------------------------------------------
# パターン定義
# ---------------------------------------------------------------------------
PATTERN_CONFIG: dict[str, dict[str, str]] = {
    "dotchi-taiketsu":   {"rank": "S", "difficulty": "初心者"},
    "sankagata-odai":    {"rank": "S", "difficulty": "初心者"},
    "quiz-senshuken":    {"rank": "S", "difficulty": "初心者"},
    "xgrid-4koma":       {"rank": "A", "difficulty": "初心者"},
    "prompt-ba":         {"rank": "A", "difficulty": "中級"},
    "tsukaiwake-chart":  {"rank": "A", "difficulty": "中級"},
    "aruaru-kakeai":     {"rank": "B", "difficulty": "初心者"},
    "dokuzetu-review":   {"rank": "B", "difficulty": "中級"},
    "gachi-thread":      {"rank": "C", "difficulty": "上級"},
    "trend-sokuhou":     {"rank": "C", "difficulty": "中級"},
}

DIFFICULTY_TARGETS = {"初心者": 0.50, "中級": 0.33, "上級": 0.17}

# ---------------------------------------------------------------------------
# スコア算出
# ---------------------------------------------------------------------------
VOLUME_WEIGHTS = {"replies": 10, "bookmarks": 8, "retweets": 3, "likes": 1}
VOLUME_QUALITY_RATIO = (0.6, 0.4)
BAYESIAN_K = 3  # 正則化パラメータ


def calc_volume_score(m: dict[str, int | float]) -> float:
    """volume_score = replies×10 + bookmarks×8 + retweets×3 + likes×1"""
    return sum(m.get(k, 0) * w for k, w in VOLUME_WEIGHTS.items())


def calc_quality_score(m: dict[str, int | float]) -> float:
    """quality_score = engagement_rate（%）"""
    return float(m.get("engagement_rate", 0.0))


def normalize_list(values: list[float]) -> list[float]:
    """min-max 正規化 → 0〜1"""
    if not values:
        return values
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def calc_composite_scores(posts: list[dict]) -> list[float]:
    """全投稿の composite_score を一括算出（正規化が必要なため）"""
    volumes = [calc_volume_score(p["metrics"]) for p in posts]
    qualities = [calc_quality_score(p["metrics"]) for p in posts]
    norm_v = normalize_list(volumes)
    norm_q = normalize_list(qualities)
    vr, qr = VOLUME_QUALITY_RATIO
    return [vr * nv + qr * nq for nv, nq in zip(norm_v, norm_q)]


# ---------------------------------------------------------------------------
# 外れ値キャップ（IQR法）
# ---------------------------------------------------------------------------
def cap_outliers(scores: list[float]) -> list[float]:
    """IQR 法で上限をクリップ"""
    if len(scores) < 4:
        return scores
    sorted_s = sorted(scores)
    n = len(sorted_s)
    q1 = sorted_s[n // 4]
    q3 = sorted_s[(3 * n) // 4]
    iqr = q3 - q1
    cap = q3 + 1.5 * iqr
    return [min(s, cap) for s in scores]


# ---------------------------------------------------------------------------
# 時間帯正規化
# ---------------------------------------------------------------------------
def timeslot_normalize(
    posts: list[dict], scores: list[float]
) -> list[float]:
    """曜日×時間帯のインプレッション差を補正"""
    slot_impressions: dict[str, list[float]] = {}
    for p in posts:
        slot = f"{p.get('day', '?')}_{p.get('time', '?')}"
        imp = p.get("metrics", {}).get("impressions", 0)
        slot_impressions.setdefault(slot, []).append(imp)

    slot_avg = {s: statistics.mean(v) for s, v in slot_impressions.items() if v}
    global_avg = statistics.mean(slot_avg.values()) if slot_avg else 1.0

    result = []
    for p, sc in zip(posts, scores):
        slot = f"{p.get('day', '?')}_{p.get('time', '?')}"
        factor = slot_avg.get(slot, global_avg) / global_avg if global_avg else 1.0
        result.append(sc / factor if factor else sc)
    return result


# ---------------------------------------------------------------------------
# ベイズ補正
# ---------------------------------------------------------------------------
def bayesian_adjust(
    pattern_scores: dict[str, list[float]], global_avg: float
) -> dict[str, float]:
    """サンプル数が少ないパターンを全体平均に寄せる"""
    adjusted = {}
    for pat, scores in pattern_scores.items():
        n = len(scores)
        if n == 0:
            adjusted[pat] = global_avg
        else:
            observed = statistics.mean(scores)
            adjusted[pat] = (n * observed + BAYESIAN_K * global_avg) / (n + BAYESIAN_K)
    return adjusted


# ---------------------------------------------------------------------------
# 3ヶ月ローリング窓
# ---------------------------------------------------------------------------
def rolling_average(
    current: dict[str, float],
    prev1: dict[str, float] | None,
    prev2: dict[str, float] | None,
) -> dict[str, float]:
    """加重移動平均: 当月0.5 + 前月0.3 + 前々月0.2"""
    result = {}
    all_patterns = set(current) | set(prev1 or {}) | set(prev2 or {})
    for pat in all_patterns:
        vals, weights = [], []
        if pat in current:
            vals.append(current[pat])
            weights.append(0.5)
        if prev1 and pat in prev1:
            vals.append(prev1[pat])
            weights.append(0.3)
        if prev2 and pat in prev2:
            vals.append(prev2[pat])
            weights.append(0.2)
        if vals:
            total_w = sum(weights)
            result[pat] = sum(v * w for v, w in zip(vals, weights)) / total_w
    return result


# ---------------------------------------------------------------------------
# パーセンタイルランク
# ---------------------------------------------------------------------------
def percentile_rank(scores: dict[str, float]) -> dict[str, float]:
    """0-100 のパーセンタイルに変換（高い=良い）"""
    if not scores:
        return {}
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    n = len(sorted_items)
    return {
        pat: round((1 - i / max(n - 1, 1)) * 100, 1)
        for i, (pat, _) in enumerate(sorted_items)
    }


# ---------------------------------------------------------------------------
# 判定
# ---------------------------------------------------------------------------
def judge_rotation(
    ranks: dict[str, float],
    usage_counts: dict[str, int],
    months_of_data: int,
    all_scores_std: float,
) -> dict[str, list[str]]:
    """promote / hold / demote / replace / experiment を判定"""
    STD_THRESHOLD = 0.05  # 横並び検出

    result: dict[str, list[str]] = {
        "promote": [], "hold": [], "demote": [],
        "replace": [], "experiment": [], "overrides": [],
    }

    # 横並び検出
    if all_scores_std < STD_THRESHOLD:
        result["hold"] = list(ranks.keys())
        result["overrides"].append("横並び検出: 全パターン hold、前月踏襲")
        return result

    for pat, rank in ranks.items():
        count = usage_counts.get(pat, 0)

        # 使用3回未満は experiment
        if count < 3:
            result["experiment"].append(pat)
            continue

        # パーセンタイル判定
        if rank >= 80:
            result["promote"].append(pat)
        elif rank >= 30:
            result["hold"].append(pat)
        elif rank >= 10:
            result["demote"].append(pat)
        else:
            # 3ヶ月未満なら replace を出さない
            if months_of_data < 3:
                result["hold"].append(pat)
                result["overrides"].append(
                    f"{pat}: データ{months_of_data}ヶ月のため replace→hold"
                )
            else:
                result["replace"].append(pat)

    return result


# ---------------------------------------------------------------------------
# トレンド補正
# ---------------------------------------------------------------------------
def apply_trend_correction(
    decision: dict[str, list[str]],
    current_ranks: dict[str, float],
    prev_ranks: dict[str, float] | None,
    prev2_ranks: dict[str, float] | None,
) -> dict[str, list[str]]:
    """2ヶ月連続上昇/下降で1段階補正"""
    if not prev_ranks or not prev2_ranks:
        return decision

    LEVELS = ["replace", "demote", "hold", "promote"]

    for pat in list(current_ranks.keys()):
        if pat not in prev_ranks or pat not in prev2_ranks:
            continue

        cur = current_ranks[pat]
        p1 = prev_ranks[pat]
        p2 = prev2_ranks[pat]

        # 現在のレベルを特定
        current_level = None
        for level in LEVELS:
            if pat in decision.get(level, []):
                current_level = level
                break
        if current_level is None or current_level not in LEVELS:
            continue

        idx = LEVELS.index(current_level)

        if cur > p1 > p2:  # 2ヶ月連続上昇
            new_idx = min(idx + 1, len(LEVELS) - 1)
            if new_idx != idx:
                decision[current_level].remove(pat)
                decision[LEVELS[new_idx]].append(pat)
                decision.setdefault("overrides", []).append(
                    f"{pat}: 2ヶ月連続上昇 → {current_level}→{LEVELS[new_idx]}"
                )

        elif cur < p1 < p2:  # 2ヶ月連続下降
            new_idx = max(idx - 1, 0)
            if new_idx != idx:
                decision[current_level].remove(pat)
                decision[LEVELS[new_idx]].append(pat)
                decision.setdefault("overrides", []).append(
                    f"{pat}: 2ヶ月連続下降 → {current_level}→{LEVELS[new_idx]}"
                )

    return decision


# ---------------------------------------------------------------------------
# 難易度バランスチェック
# ---------------------------------------------------------------------------
def check_difficulty_balance(
    decision: dict[str, list[str]],
) -> dict[str, list[str]]:
    """難易度制約が判定を上書き"""
    # 配置されるパターン（promote + hold）
    active = decision["promote"] + decision["hold"]

    diff_count: dict[str, int] = {"初心者": 0, "中級": 0, "上級": 0}
    for pat in active:
        cfg = PATTERN_CONFIG.get(pat, {})
        diff = cfg.get("difficulty", "中級")
        diff_count[diff] = diff_count.get(diff, 0) + 1

    total = sum(diff_count.values()) or 1

    # 初心者 < 40% → 最高スコアの初心者パターンを promote
    if diff_count["初心者"] / total < 0.40:
        # demote/experiment にいる初心者パターンを rescue
        for level in ["demote", "experiment"]:
            for pat in list(decision.get(level, [])):
                cfg = PATTERN_CONFIG.get(pat, {})
                if cfg.get("difficulty") == "初心者":
                    decision[level].remove(pat)
                    decision["hold"].append(pat)
                    decision.setdefault("overrides", []).append(
                        f"{pat}: 初心者不足のため {level}→hold"
                    )
                    break

    # 上級 == 0 → ガチ回を強制配置
    if diff_count["上級"] == 0 and "gachi-thread" not in active:
        if "gachi-thread" in decision.get("demote", []):
            decision["demote"].remove("gachi-thread")
        elif "gachi-thread" in decision.get("replace", []):
            decision["replace"].remove("gachi-thread")
        decision["hold"].append("gachi-thread")
        decision.setdefault("overrides", []).append(
            "gachi-thread: 上級0のため強制配置"
        )

    return decision


# ---------------------------------------------------------------------------
# YAML I/O
# ---------------------------------------------------------------------------
def load_posts(directory: Path, year_month: str | None = None) -> list[dict]:
    """個別レポート YAML を読み込み"""
    if not directory.exists():
        return []
    posts = []
    for f in sorted(directory.glob("*.yaml")):
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
            if data:
                if year_month and not str(data.get("date", "")).startswith(year_month):
                    continue
                posts.append(data)
    return posts


def load_monthly(directory: Path, month: str) -> dict | None:
    """月間レポートを読み込み"""
    f = directory / f"{month}.yaml"
    if f.exists():
        with open(f, encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    return None


def save_yaml(path: Path, data: dict) -> None:
    """YAML を保存"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"保存: {path}")


# ---------------------------------------------------------------------------
# 週間チェック
# ---------------------------------------------------------------------------
def weekly_check(target_date: datetime | None = None) -> dict:
    """週間レポートを生成（判定なし、データ蓄積と振り返り用）"""
    today = target_date or datetime.now()
    # ISO週番号
    iso_year, iso_week, _ = today.isocalendar()
    week_label = f"{iso_year}-W{iso_week:02d}"

    # 今週の月〜金の投稿を収集
    week_start = today - timedelta(days=today.weekday())  # 月曜
    week_end = week_start + timedelta(days=4)  # 金曜

    posts = load_posts(POSTS_DIR)
    week_posts = [
        p for p in posts
        if week_start.date() <= datetime.strptime(str(p["date"]), "%Y-%m-%d").date() <= week_end.date()
    ]

    if not week_posts:
        print(f"[週間] {week_label}: 投稿データなし")
        return {}

    # composite_score 算出
    composites = calc_composite_scores(week_posts)
    for p, cs in zip(week_posts, composites):
        p.setdefault("scores", {})
        p["scores"]["volume_score"] = round(calc_volume_score(p["metrics"]), 1)
        p["scores"]["quality_score"] = round(calc_quality_score(p["metrics"]), 2)
        p["scores"]["composite_score"] = round(cs, 4)

    # 集計
    total_imp = sum(p["metrics"].get("impressions", 0) for p in week_posts)
    total_eng = sum(p["metrics"].get("engagements", 0) for p in week_posts)
    total_rep = sum(p["metrics"].get("replies", 0) for p in week_posts)
    total_bkm = sum(p["metrics"].get("bookmarks", 0) for p in week_posts)
    avg_er = statistics.mean([p["metrics"].get("engagement_rate", 0) for p in week_posts])
    avg_cs = statistics.mean(composites)

    # ベスト/ワースト
    best = max(week_posts, key=lambda p: p["scores"]["composite_score"])
    worst = min(week_posts, key=lambda p: p["scores"]["composite_score"])

    # タイムスロット別
    ts_perf = {}
    for p in week_posts:
        slot = f"{p.get('day', '?')}_{p.get('time', '?')}"
        ts_perf[slot] = {
            "engagement_rate": round(p["metrics"].get("engagement_rate", 0), 2),
            "replies": p["metrics"].get("replies", 0),
            "impressions": p["metrics"].get("impressions", 0),
        }

    report = {
        "week": week_label,
        "period": f"{week_start.date()} ~ {week_end.date()}",
        "summary": {
            "total_impressions": total_imp,
            "total_engagements": total_eng,
            "avg_engagement_rate": round(avg_er, 2),
            "total_replies": total_rep,
            "total_bookmarks": total_bkm,
            "avg_composite_score": round(avg_cs, 4),
        },
        "patterns_used": [
            {
                "pattern": p.get("pattern", "unknown"),
                "day": p.get("day", "?"),
                "composite_score": round(p["scores"]["composite_score"], 4),
                "engagement_rate": round(p["metrics"].get("engagement_rate", 0), 2),
            }
            for p in week_posts
        ],
        "timeslot_performance": ts_perf,
        "best_post": best.get("post_id", "?"),
        "worst_post": worst.get("post_id", "?"),
        "wins": [],
        "improvements": [],
        "discoveries": [],
    }

    # 週間サマリー出力
    print(f"\n{'='*60}")
    print(f"週間チェック: {week_label}")
    print(f"{'='*60}")
    print(f"投稿数: {len(week_posts)}")
    print(f"平均エンゲージメント率: {avg_er:.2f}%")
    print(f"平均 composite_score: {avg_cs:.4f}")
    print(f"総リプライ: {total_rep}")
    print(f"総ブックマーク: {total_bkm}")
    print(f"ベスト: {best.get('post_id', '?')} (score={best['scores']['composite_score']:.4f})")
    print(f"ワースト: {worst.get('post_id', '?')} (score={worst['scores']['composite_score']:.4f})")
    print()
    for pu in report["patterns_used"]:
        print(f"  {pu['day']} {pu['pattern']}: composite={pu['composite_score']:.4f}, ER={pu['engagement_rate']}%")
    print(f"{'='*60}\n")

    save_yaml(WEEKLY_DIR / f"{week_label}.yaml", report)
    return report


# ---------------------------------------------------------------------------
# 月間チェック + 入れ替え判定
# ---------------------------------------------------------------------------
def monthly_check(target_month: str | None = None) -> dict:
    """月間レポート生成 + 入れ替えアルゴリズム実行"""
    month = target_month or datetime.now().strftime("%Y-%m")

    # --- データ収集 ---
    posts = load_posts(POSTS_DIR, year_month=month)
    if not posts:
        print(f"[月間] {month}: 投稿データなし")
        return {}

    # composite_score 算出
    composites = calc_composite_scores(posts)
    composites = cap_outliers(composites)  # バズキャップ
    composites = timeslot_normalize(posts, composites)  # 時間帯正規化

    for p, cs in zip(posts, composites):
        p.setdefault("scores", {})
        p["scores"]["volume_score"] = round(calc_volume_score(p["metrics"]), 1)
        p["scores"]["quality_score"] = round(calc_quality_score(p["metrics"]), 2)
        p["scores"]["composite_score"] = round(cs, 4)

    # --- パターン別集計 ---
    pattern_scores: dict[str, list[float]] = {}
    pattern_counts: dict[str, int] = {}
    for p, cs in zip(posts, composites):
        pat = p.get("pattern", "unknown")
        pattern_scores.setdefault(pat, []).append(cs)
        pattern_counts[pat] = pattern_counts.get(pat, 0) + 1

    global_avg = statistics.mean(composites) if composites else 0.0

    # --- ベイズ補正 ---
    adjusted_current = bayesian_adjust(pattern_scores, global_avg)

    # --- 3ヶ月ローリング ---
    prev1_month = (datetime.strptime(month + "-01", "%Y-%m-%d") - timedelta(days=15)).strftime("%Y-%m")
    prev2_month = (datetime.strptime(month + "-01", "%Y-%m-%d") - timedelta(days=45)).strftime("%Y-%m")

    prev1_report = load_monthly(MONTHLY_DIR, prev1_month)
    prev2_report = load_monthly(MONTHLY_DIR, prev2_month)

    prev1_scores = None
    prev2_scores = None
    months_of_data = 1
    if prev1_report and "pattern_adjusted_scores" in prev1_report:
        prev1_scores = prev1_report["pattern_adjusted_scores"]
        months_of_data = 2
    if prev2_report and "pattern_adjusted_scores" in prev2_report:
        prev2_scores = prev2_report["pattern_adjusted_scores"]
        months_of_data = 3

    rolling = rolling_average(adjusted_current, prev1_scores, prev2_scores)

    # --- パーセンタイルランク ---
    ranks = percentile_rank(rolling)

    # --- 3ヶ月合計の使用回数 ---
    total_usage: dict[str, int] = dict(pattern_counts)
    if prev1_report:
        for pp in prev1_report.get("pattern_performance", []):
            pat = pp["pattern"]
            total_usage[pat] = total_usage.get(pat, 0) + pp.get("times_used", 0)
    if prev2_report:
        for pp in prev2_report.get("pattern_performance", []):
            pat = pp["pattern"]
            total_usage[pat] = total_usage.get(pat, 0) + pp.get("times_used", 0)

    # --- 横並び検出用の標準偏差 ---
    all_std = statistics.stdev(rolling.values()) if len(rolling) > 1 else 0.0

    # --- 判定 ---
    decision = judge_rotation(ranks, total_usage, months_of_data, all_std)

    # --- トレンド補正 ---
    prev1_ranks_data = None
    prev2_ranks_data = None
    if prev1_report and "pattern_ranks" in prev1_report:
        prev1_ranks_data = prev1_report["pattern_ranks"]
    if prev2_report and "pattern_ranks" in prev2_report:
        prev2_ranks_data = prev2_report["pattern_ranks"]
    decision = apply_trend_correction(decision, ranks, prev1_ranks_data, prev2_ranks_data)

    # --- 難易度バランスチェック ---
    decision = check_difficulty_balance(decision)

    # --- 集計 ---
    total_imp = sum(p["metrics"].get("impressions", 0) for p in posts)
    total_eng = sum(p["metrics"].get("engagements", 0) for p in posts)
    total_rep = sum(p["metrics"].get("replies", 0) for p in posts)
    total_bkm = sum(p["metrics"].get("bookmarks", 0) for p in posts)
    total_rt = sum(p["metrics"].get("retweets", 0) for p in posts)
    avg_er = statistics.mean([p["metrics"].get("engagement_rate", 0) for p in posts])
    avg_cs = statistics.mean(composites)

    # パターン別
    pattern_perf = []
    for pat in sorted(set(p.get("pattern", "unknown") for p in posts)):
        pat_posts = [p for p in posts if p.get("pattern") == pat]
        pat_cs = [p["scores"]["composite_score"] for p in pat_posts]
        pat_er = [p["metrics"].get("engagement_rate", 0) for p in pat_posts]
        pattern_perf.append({
            "pattern": pat,
            "times_used": len(pat_posts),
            "avg_composite_score": round(statistics.mean(pat_cs), 4),
            "avg_engagement_rate": round(statistics.mean(pat_er), 2),
            "rank": round(ranks.get(pat, 0), 1),
            "decision": next(
                (k for k, v in decision.items() if pat in v and k != "overrides"),
                "unknown"
            ),
        })

    # 難易度バランス
    diff_count: dict[str, int] = {"初心者": 0, "中級": 0, "上級": 0}
    for p in posts:
        d = p.get("difficulty", PATTERN_CONFIG.get(p.get("pattern", ""), {}).get("difficulty", "中級"))
        diff_count[d] = diff_count.get(d, 0) + 1
    total = sum(diff_count.values()) or 1
    diff_balance = {
        d: {"count": c, "ratio": round(c / total, 2), "target": DIFFICULTY_TARGETS.get(d, 0)}
        for d, c in diff_count.items()
    }

    # タイムスロット
    ts_monthly: dict[str, dict] = {}
    for p in posts:
        slot = f"{p.get('day', '?')}_{p.get('time', '?')}"
        ts_monthly.setdefault(slot, {"ers": [], "reps": [], "imps": []})
        ts_monthly[slot]["ers"].append(p["metrics"].get("engagement_rate", 0))
        ts_monthly[slot]["reps"].append(p["metrics"].get("replies", 0))
        ts_monthly[slot]["imps"].append(p["metrics"].get("impressions", 0))
    ts_result = {
        s: {
            "avg_engagement_rate": round(statistics.mean(d["ers"]), 2),
            "avg_replies": round(statistics.mean(d["reps"]), 1),
            "avg_impressions": round(statistics.mean(d["imps"]), 1),
        }
        for s, d in ts_monthly.items()
    }

    # トップ3/ワースト3
    sorted_posts = sorted(posts, key=lambda p: p["scores"]["composite_score"], reverse=True)
    top3 = [p.get("post_id", "?") for p in sorted_posts[:3]]
    worst3 = [p.get("post_id", "?") for p in sorted_posts[-3:]]

    report = {
        "month": month,
        "total_posts": len(posts),
        "months_of_data": months_of_data,
        "summary": {
            "total_impressions": total_imp,
            "total_engagements": total_eng,
            "avg_engagement_rate": round(avg_er, 2),
            "total_replies": total_rep,
            "total_bookmarks": total_bkm,
            "total_retweets": total_rt,
            "avg_composite_score": round(avg_cs, 4),
        },
        "pattern_performance": pattern_perf,
        "pattern_adjusted_scores": {k: round(v, 4) for k, v in adjusted_current.items()},
        "pattern_ranks": {k: round(v, 1) for k, v in ranks.items()},
        "difficulty_balance": diff_balance,
        "timeslot_monthly": ts_result,
        "top3": top3,
        "worst3": worst3,
        "rotation_decision": decision,
    }

    # --- 出力 ---
    print(f"\n{'='*60}")
    print(f"月間チェック + 入れ替え判定: {month}")
    print(f"{'='*60}")
    print(f"投稿数: {len(posts)}  |  データ蓄積: {months_of_data}ヶ月")
    print(f"平均エンゲージメント率: {avg_er:.2f}%")
    print(f"平均 composite_score: {avg_cs:.4f}")
    print(f"総リプライ: {total_rep}  |  総ブックマーク: {total_bkm}")
    print()

    print("--- パターン別成績 ---")
    for pp in sorted(pattern_perf, key=lambda x: x["rank"], reverse=True):
        print(
            f"  {pp['pattern']:24s}  "
            f"使用{pp['times_used']}回  "
            f"score={pp['avg_composite_score']:.4f}  "
            f"ER={pp['avg_engagement_rate']}%  "
            f"rank={pp['rank']}  "
            f"→ {pp['decision']}"
        )
    print()

    print("--- 入れ替え判定 ---")
    for key in ["promote", "hold", "demote", "replace", "experiment"]:
        pats = decision.get(key, [])
        if pats:
            print(f"  {key:12s}: {', '.join(pats)}")
    if decision.get("overrides"):
        print("  --- 補正 ---")
        for o in decision["overrides"]:
            print(f"    {o}")
    print()

    print("--- 難易度バランス ---")
    for d, info in diff_balance.items():
        status = "OK" if abs(info["ratio"] - info["target"]) < 0.15 else "要調整"
        print(f"  {d}: {info['count']}件 ({info['ratio']:.0%}) 目標{info['target']:.0%} [{status}]")
    print(f"{'='*60}\n")

    save_yaml(MONTHLY_DIR / f"{month}.yaml", report)
    return report


# ---------------------------------------------------------------------------
# 単発スコア算出
# ---------------------------------------------------------------------------
def score_single(yaml_path: str) -> None:
    """1つの個別レポートのスコアを算出して表示"""
    p = Path(yaml_path)
    if not p.exists():
        print(f"ファイルが見つかりません: {p}")
        return
    with open(p, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not data or "metrics" not in data:
        print("metrics が含まれていません")
        return

    m = data["metrics"]
    vs = calc_volume_score(m)
    qs = calc_quality_score(m)
    print(f"volume_score:  {vs:.1f}  (replies×10={m.get('replies',0)*10}, bookmarks×8={m.get('bookmarks',0)*8}, RT×3={m.get('retweets',0)*3}, likes×1={m.get('likes',0)})")
    print(f"quality_score: {qs:.2f}%  (engagement_rate)")
    print(f"※ composite_score は月間の全投稿と一緒に正規化するため、単発では算出不可")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="X投稿レポート & 入れ替えアルゴリズム")
    sub = parser.add_subparsers(dest="command")

    w = sub.add_parser("weekly", help="週間チェック")
    w.add_argument("--date", help="対象日 (YYYY-MM-DD)", default=None)

    m = sub.add_parser("monthly", help="月間チェック + 入れ替え判定")
    m.add_argument("--month", help="対象月 (YYYY-MM)", default=None)

    s = sub.add_parser("score", help="単発スコア算出")
    s.add_argument("file", help="個別レポート YAML のパス")

    args = parser.parse_args()

    if args.command == "weekly":
        date = datetime.strptime(args.date, "%Y-%m-%d") if args.date else None
        weekly_check(date)
    elif args.command == "monthly":
        monthly_check(args.month)
    elif args.command == "score":
        score_single(args.file)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
