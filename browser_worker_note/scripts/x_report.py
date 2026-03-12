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

PILLAR_NAMES = ["やってみた実演", "埋もれた一次情報のフォーク", "制作の裏側公開"]

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
# 柱別集計
# ---------------------------------------------------------------------------
def _count_pillars(posts: list[dict]) -> dict[str, dict]:
    """3本柱の投稿数・比率を集計"""
    counts: dict[str, int] = {p: 0 for p in PILLAR_NAMES}
    for post in posts:
        pillar = post.get("pillar", "")
        if pillar in counts:
            counts[pillar] += 1
    total = sum(counts.values()) or 1
    return {
        p: {"count": c, "ratio": round(c / total, 2)}
        for p, c in counts.items()
    }


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

    # 柱別分布
    pillar_dist = _count_pillars(week_posts)

    # 画像品質問題の集計
    image_issues = [
        {"post_id": p.get("post_id", "?"), "issue": p["image_issues"]}
        for p in week_posts
        if p.get("image_issues")
    ]

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
                "pillar": p.get("pillar", "不明"),
                "day": p.get("day", "?"),
                "composite_score": round(p["scores"]["composite_score"], 4),
                "engagement_rate": round(p["metrics"].get("engagement_rate", 0), 2),
            }
            for p in week_posts
        ],
        "pillar_balance": pillar_dist,
        "timeslot_performance": ts_perf,
        "best_post": best.get("post_id", "?"),
        "worst_post": worst.get("post_id", "?"),
        "image_issues": image_issues,
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
        print(f"  {pu['day']} {pu['pattern']} [{pu['pillar']}]: composite={pu['composite_score']:.4f}, ER={pu['engagement_rate']}%")
    print()
    print("--- 柱別バランス ---")
    for pil, info in pillar_dist.items():
        print(f"  {pil}: {info['count']}件 ({info['ratio']:.0%})")
    if image_issues:
        print()
        print("--- 画像品質問題 ---")
        for issue in image_issues:
            print(f"  {issue['post_id']}: {issue['issue']}")
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

    # 柱別分布
    pillar_dist = _count_pillars(posts)

    # 柱別スコア平均
    pillar_scores: dict[str, list[float]] = {}
    for p, cs in zip(posts, composites):
        pil = p.get("pillar", "不明")
        pillar_scores.setdefault(pil, []).append(cs)
    pillar_perf = {
        pil: round(statistics.mean(scs), 4) if scs else 0.0
        for pil, scs in pillar_scores.items()
    }

    # 画像品質問題の集計
    image_issues_monthly = [
        {"post_id": p.get("post_id", "?"), "issue": p["image_issues"]}
        for p in posts
        if p.get("image_issues")
    ]

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
        "pillar_balance": pillar_dist,
        "pillar_performance": pillar_perf,
        "difficulty_balance": diff_balance,
        "timeslot_monthly": ts_result,
        "top3": top3,
        "worst3": worst3,
        "image_issues": image_issues_monthly,
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

    print("--- 柱別バランス ---")
    for pil, info in pillar_dist.items():
        score = pillar_perf.get(pil, 0.0)
        print(f"  {pil}: {info['count']}件 ({info['ratio']:.0%}) score={score:.4f}")
    print()

    print("--- 難易度バランス ---")
    for d, info in diff_balance.items():
        status = "OK" if abs(info["ratio"] - info["target"]) < 0.15 else "要調整"
        print(f"  {d}: {info['count']}件 ({info['ratio']:.0%}) 目標{info['target']:.0%} [{status}]")

    if image_issues_monthly:
        print()
        print("--- 画像品質問題 ---")
        for issue in image_issues_monthly:
            print(f"  {issue['post_id']}: {issue['issue']}")
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
# ダッシュボード HTML 生成
# ---------------------------------------------------------------------------
DASHBOARD_DIR = ROOT / "knowledge" / "logs" / "x" / "dashboard"


def _json_dumps(obj: Any) -> str:
    """JSON 文字列化（テンプレート埋め込み用）"""
    import json
    return json.dumps(obj, ensure_ascii=False)


def generate_dashboard(target_month: str | None = None) -> Path:
    """投稿データからスタンドアロン HTML ダッシュボードを生成"""
    import json

    month = target_month or datetime.now().strftime("%Y-%m")
    posts = load_posts(POSTS_DIR, year_month=month)
    all_posts = load_posts(POSTS_DIR)  # 全期間（タイムライン用）

    # スコア算出
    if posts:
        composites = calc_composite_scores(posts)
        for p, cs in zip(posts, composites):
            p.setdefault("scores", {})
            p["scores"]["volume_score"] = round(calc_volume_score(p["metrics"]), 1)
            p["scores"]["quality_score"] = round(calc_quality_score(p["metrics"]), 2)
            p["scores"]["composite_score"] = round(cs, 4)

    # 集計データ
    pillar_dist = _count_pillars(posts) if posts else {}
    total_imp = sum(p["metrics"].get("impressions", 0) for p in posts)
    total_eng = sum(p["metrics"].get("engagements", 0) for p in posts)
    total_rep = sum(p["metrics"].get("replies", 0) for p in posts)
    total_bkm = sum(p["metrics"].get("bookmarks", 0) for p in posts)
    avg_er = (
        statistics.mean([p["metrics"].get("engagement_rate", 0) for p in posts])
        if posts else 0.0
    )

    # パターン別
    pattern_data: dict[str, list[float]] = {}
    for p in posts:
        pat = p.get("pattern", "unknown")
        pattern_data.setdefault(pat, []).append(
            p.get("scores", {}).get("composite_score", 0)
        )
    pattern_summary = [
        {"pattern": pat, "count": len(scores), "avg_score": round(statistics.mean(scores), 4)}
        for pat, scores in sorted(pattern_data.items())
    ] if pattern_data else []

    # 難易度
    diff_count: dict[str, int] = {"初心者": 0, "中級": 0, "上級": 0}
    for p in posts:
        d = p.get("difficulty", "中級")
        diff_count[d] = diff_count.get(d, 0) + 1

    # 投稿タイムライン（全期間）
    timeline = [
        {
            "date": str(p.get("date", "")),
            "day": p.get("day", "?"),
            "pattern": p.get("pattern", "?"),
            "pillar": p.get("pillar", "?"),
            "status": p.get("status", "?"),
            "topic": p.get("topic", ""),
            "impressions": p.get("metrics", {}).get("impressions", 0),
            "engagement_rate": p.get("metrics", {}).get("engagement_rate", 0),
            "likes": p.get("metrics", {}).get("likes", 0),
            "replies": p.get("metrics", {}).get("replies", 0),
            "retweets": p.get("metrics", {}).get("retweets", 0),
            "bookmarks": p.get("metrics", {}).get("bookmarks", 0),
            "image_issues": p.get("image_issues", ""),
        }
        for p in all_posts
    ]

    # 画像品質問題
    issues = [
        {"post_id": p.get("post_id", "?"), "issue": p.get("image_issues", "")}
        for p in all_posts
        if p.get("image_issues")
    ]

    html = _build_dashboard_html(
        month=month,
        total_posts=len(posts),
        total_imp=total_imp,
        total_eng=total_eng,
        total_rep=total_rep,
        total_bkm=total_bkm,
        avg_er=round(avg_er, 2),
        pillar_dist=pillar_dist,
        pattern_summary=pattern_summary,
        diff_count=diff_count,
        timeline=timeline,
        issues=issues,
    )

    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DASHBOARD_DIR / f"{month}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"ダッシュボード生成: {out_path}")
    return out_path


def _build_dashboard_html(
    *,
    month: str,
    total_posts: int,
    total_imp: int,
    total_eng: int,
    total_rep: int,
    total_bkm: int,
    avg_er: float,
    pillar_dist: dict,
    pattern_summary: list,
    diff_count: dict,
    timeline: list,
    issues: list,
) -> str:
    import json

    pillar_labels = json.dumps(list(pillar_dist.keys()), ensure_ascii=False)
    pillar_counts = json.dumps([v["count"] for v in pillar_dist.values()])

    pattern_labels = json.dumps([p["pattern"] for p in pattern_summary], ensure_ascii=False)
    pattern_scores = json.dumps([p["avg_score"] for p in pattern_summary])
    pattern_counts_data = json.dumps([p["count"] for p in pattern_summary])

    diff_labels = json.dumps(list(diff_count.keys()), ensure_ascii=False)
    diff_values = json.dumps(list(diff_count.values()))

    timeline_json = json.dumps(timeline, ensure_ascii=False)
    issues_json = json.dumps(issues, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>X Report Dashboard — {month}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0f1117; --surface: #1a1d27; --border: #2a2d3a;
    --text: #e4e4e7; --muted: #9ca3af; --accent: #6366f1;
    --green: #22c55e; --yellow: #eab308; --red: #ef4444; --blue: #3b82f6;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, 'Segoe UI', sans-serif; padding: 24px; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 8px; }}
  .subtitle {{ color: var(--muted); margin-bottom: 24px; font-size: 0.9rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }}
  .card-label {{ color: var(--muted); font-size: 0.8rem; margin-bottom: 4px; }}
  .card-value {{ font-size: 1.8rem; font-weight: 700; }}
  .card-value.accent {{ color: var(--accent); }}
  .card-value.green {{ color: var(--green); }}
  .card-value.blue {{ color: var(--blue); }}
  .section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
  .section h2 {{ font-size: 1.1rem; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }}
  .chart-row {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 24px; }}
  .chart-box {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }}
  .chart-box h3 {{ font-size: 0.9rem; color: var(--muted); margin-bottom: 12px; }}
  canvas {{ max-height: 250px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  th {{ text-align: left; color: var(--muted); font-weight: 600; padding: 8px 12px; border-bottom: 1px solid var(--border); }}
  td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); }}
  tr:hover td {{ background: rgba(99,102,241,0.05); }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }}
  .badge-posted {{ background: rgba(34,197,94,0.15); color: var(--green); }}
  .badge-scheduled {{ background: rgba(234,179,8,0.15); color: var(--yellow); }}
  .badge-draft {{ background: rgba(156,163,175,0.15); color: var(--muted); }}
  .issue-item {{ padding: 8px 12px; border-left: 3px solid var(--yellow); margin-bottom: 8px; background: rgba(234,179,8,0.05); border-radius: 0 6px 6px 0; }}
  .issue-id {{ font-weight: 600; margin-right: 8px; }}
  .empty {{ color: var(--muted); font-style: italic; padding: 16px; text-align: center; }}
  @media (max-width: 900px) {{ .chart-row {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>

<h1>X Report Dashboard</h1>
<p class="subtitle">{month} | 生成: <span id="gen-time"></span></p>

<!-- KPIs -->
<div class="grid">
  <div class="card"><div class="card-label">投稿数</div><div class="card-value accent">{total_posts}</div></div>
  <div class="card"><div class="card-label">インプレッション</div><div class="card-value">{total_imp:,}</div></div>
  <div class="card"><div class="card-label">エンゲージメント</div><div class="card-value">{total_eng:,}</div></div>
  <div class="card"><div class="card-label">平均 ER</div><div class="card-value green">{avg_er}%</div></div>
  <div class="card"><div class="card-label">リプライ</div><div class="card-value blue">{total_rep}</div></div>
  <div class="card"><div class="card-label">ブックマーク</div><div class="card-value">{total_bkm}</div></div>
</div>

<!-- Charts -->
<div class="chart-row">
  <div class="chart-box">
    <h3>3本柱バランス</h3>
    <canvas id="pillarChart"></canvas>
  </div>
  <div class="chart-box">
    <h3>パターン別スコア</h3>
    <canvas id="patternChart"></canvas>
  </div>
  <div class="chart-box">
    <h3>難易度分布</h3>
    <canvas id="diffChart"></canvas>
  </div>
</div>

<!-- Timeline -->
<div class="section">
  <h2>投稿タイムライン</h2>
  <table>
    <thead><tr><th>日付</th><th>曜日</th><th>パターン</th><th>柱</th><th>トピック</th><th>状態</th><th>IMP</th><th>ER%</th><th>Like</th><th>Rep</th><th>RT</th><th>BM</th></tr></thead>
    <tbody id="timeline-body"></tbody>
  </table>
</div>

<!-- Image Issues -->
<div class="section">
  <h2>画像品質問題</h2>
  <div id="issues-container"></div>
</div>

<script>
document.getElementById('gen-time').textContent = new Date().toLocaleString('ja-JP');

// --- Charts ---
const chartColors = ['#6366f1','#22c55e','#eab308','#ef4444','#3b82f6','#ec4899','#14b8a6','#f97316','#8b5cf6','#06b6d4'];
const chartOpts = {{ responsive: true, plugins: {{ legend: {{ labels: {{ color: '#9ca3af', font: {{ size: 11 }} }} }} }} }};

new Chart(document.getElementById('pillarChart'), {{
  type: 'doughnut',
  data: {{
    labels: {pillar_labels},
    datasets: [{{ data: {pillar_counts}, backgroundColor: chartColors.slice(0,3), borderWidth: 0 }}]
  }},
  options: {{ ...chartOpts, cutout: '55%' }}
}});

new Chart(document.getElementById('patternChart'), {{
  type: 'bar',
  data: {{
    labels: {pattern_labels},
    datasets: [
      {{ label: 'Avg Score', data: {pattern_scores}, backgroundColor: '#6366f1cc', borderRadius: 4, yAxisID: 'y' }},
      {{ label: '使用回数', data: {pattern_counts_data}, backgroundColor: '#22c55e55', borderRadius: 4, yAxisID: 'y1' }}
    ]
  }},
  options: {{
    ...chartOpts,
    scales: {{
      x: {{ ticks: {{ color: '#9ca3af', font: {{ size: 9 }} }}, grid: {{ display: false }} }},
      y: {{ position: 'left', ticks: {{ color: '#9ca3af' }}, grid: {{ color: '#2a2d3a' }} }},
      y1: {{ position: 'right', ticks: {{ color: '#22c55e' }}, grid: {{ display: false }} }}
    }}
  }}
}});

new Chart(document.getElementById('diffChart'), {{
  type: 'doughnut',
  data: {{
    labels: {diff_labels},
    datasets: [{{ data: {diff_values}, backgroundColor: ['#22c55e','#eab308','#ef4444'], borderWidth: 0 }}]
  }},
  options: {{ ...chartOpts, cutout: '55%' }}
}});

// --- Timeline ---
const timeline = {timeline_json};
const tbody = document.getElementById('timeline-body');
timeline.forEach(t => {{
  const badgeClass = t.status === 'posted' ? 'badge-posted' : t.status === 'scheduled' ? 'badge-scheduled' : 'badge-draft';
  const row = document.createElement('tr');
  row.innerHTML = `<td>${{t.date}}</td><td>${{t.day}}</td><td>${{t.pattern}}</td><td>${{t.pillar}}</td>` +
    `<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${{t.topic}}</td>` +
    `<td><span class="badge ${{badgeClass}}">${{t.status}}</span></td>` +
    `<td>${{t.impressions.toLocaleString()}}</td><td>${{t.engagement_rate}}%</td>` +
    `<td>${{t.likes}}</td><td>${{t.replies}}</td><td>${{t.retweets}}</td><td>${{t.bookmarks}}</td>`;
  tbody.appendChild(row);
}});
if (!timeline.length) tbody.innerHTML = '<tr><td colspan="12" class="empty">投稿データなし</td></tr>';

// --- Issues ---
const issues = {issues_json};
const ic = document.getElementById('issues-container');
if (issues.length) {{
  issues.forEach(i => {{
    const div = document.createElement('div');
    div.className = 'issue-item';
    div.innerHTML = `<span class="issue-id">${{i.post_id}}</span>${{i.issue}}`;
    ic.appendChild(div);
  }});
}} else {{
  ic.innerHTML = '<div class="empty">問題なし</div>';
}}
</script>
</body>
</html>"""


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

    d = sub.add_parser("dashboard", help="HTML ダッシュボード生成")
    d.add_argument("--month", help="対象月 (YYYY-MM)", default=None)
    d.add_argument("--open", action="store_true", help="生成後にブラウザで開く")

    args = parser.parse_args()

    if args.command == "weekly":
        from system_logger import log_task
        with log_task("x-report-weekly") as task:
            date = datetime.strptime(args.date, "%Y-%m-%d") if args.date else None
            result = weekly_check(date)
            if not result:
                task.note("投稿データなし")
            else:
                task.note(f"投稿数: {len(result.get('patterns_used', []))}")
    elif args.command == "monthly":
        from system_logger import log_task
        with log_task("x-report-monthly") as task:
            result = monthly_check(args.month)
            if not result:
                task.note("投稿データなし")
            else:
                task.note(f"投稿数: {result.get('total_posts', 0)}")
    elif args.command == "score":
        score_single(args.file)
    elif args.command == "dashboard":
        out = generate_dashboard(args.month)
        if args.open:
            import webbrowser
            webbrowser.open(str(out))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
