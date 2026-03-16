"""
統合ダッシュボード生成

使い方:
  python scripts/dashboard.py generate --month 2026-03 --open

設計: knowledge/sites/common/dashboard-design.md
設定: config/platforms.yaml
"""

from __future__ import annotations

import argparse
import json
import statistics
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

import sqlite3

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "platforms.yaml"
DASHBOARD_DIR = ROOT / "knowledge" / "logs" / "dashboard"
X_DB_PATH = ROOT / "knowledge" / "data" / "x_posts.db"
COMP_DB_PATH = ROOT / "knowledge" / "data" / "competitor_benchmark.db"
WEEKLY_DIR = ROOT / "knowledge" / "logs" / "x" / "weekly"

# パターン定義（x_report.py と同一）
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

PILLAR_NAMES = ["やってみた実演", "埋もれた一次情報のフォーク", "制作の裏側公開"]

CONTENT_TYPE_NAMES: dict[str, str] = {
    "C1": "ツール紹介", "C2": "ノウハウ", "C3": "ニュース", "C4": "体験",
    "C5": "用語", "C6": "比較", "C7": "オピニオン", "C8": "トレンド分析",
}

# スコア算出（x_report.py と同一ロジック）
VOLUME_WEIGHTS = {"replies": 10, "bookmarks": 8, "retweets": 3, "likes": 1}
VOLUME_QUALITY_RATIO = (0.6, 0.4)


def _calc_volume(m: dict) -> float:
    return sum(m.get(k, 0) * w for k, w in VOLUME_WEIGHTS.items())


def _calc_quality(m: dict) -> float:
    imp = m.get("impressions", 0)
    eng = m.get("engagements", 0)
    return (eng / imp * 100) if imp > 0 else 0.0


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return values
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def _get_x_conn() -> sqlite3.Connection | None:
    if not X_DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(X_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _get_comp_conn() -> sqlite3.Connection | None:
    if not COMP_DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(COMP_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


# =========================================================================
# データ収集
# =========================================================================
def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    """sqlite3.Row のリストを plain dict に変換"""
    return [dict(r) for r in rows]


def collect_x_data(month: str) -> dict:
    conn = _get_x_conn()
    if not conn:
        return dict(
            month=month, total_posts=0, total_all_posts=0,
            total_impressions=0, total_engagements=0, total_replies=0,
            total_bookmarks=0, total_retweets=0, total_likes=0,
            avg_engagement_rate=0, pattern_summary=[], pillar_dist={},
            pillar_perf={}, diff_count={"初心者": 0, "中級": 0, "上級": 0},
            heatmap_data=[], image_type_summary=[], issues=[], timeline=[],
            weekly_reports=[],
        )

    try:
        # 月別 / 全件を取得
        month_rows = _rows_to_dicts(conn.execute(
            "SELECT * FROM posts WHERE substr(date, 1, 7) = ? ORDER BY date, time", (month,)
        ).fetchall())
        all_rows = _rows_to_dicts(conn.execute(
            "SELECT * FROM posts ORDER BY date, time"
        ).fetchall())
    finally:
        conn.close()

    # -- スコア算出 --
    volumes = [_calc_volume(r) for r in month_rows]
    qualities = [_calc_quality(r) for r in month_rows]
    norm_v = _normalize(volumes)
    norm_q = _normalize(qualities)
    vr, qr = VOLUME_QUALITY_RATIO
    composites = [vr * nv + qr * nq for nv, nq in zip(norm_v, norm_q)]

    for r, vol, qual, comp in zip(month_rows, volumes, qualities, composites):
        r["_volume"] = round(vol, 1)
        r["_quality"] = round(qual, 2)
        r["_composite"] = round(comp, 4)
        r["_er"] = round(qual, 2)  # quality = ER%

    # -- KPI 集計 --
    total_imp = sum(r.get("impressions", 0) for r in month_rows)
    total_eng = sum(r.get("engagements", 0) for r in month_rows)
    total_rep = sum(r.get("replies", 0) for r in month_rows)
    total_bkm = sum(r.get("bookmarks", 0) for r in month_rows)
    total_rt = sum(r.get("retweets", 0) for r in month_rows)
    total_likes = sum(r.get("likes", 0) for r in month_rows)
    ers = [r["_er"] for r in month_rows if r["_er"] > 0]
    avg_er = statistics.mean(ers) if ers else 0.0

    # -- パターン別 --
    pattern_data: dict[str, list[float]] = {}
    for r in month_rows:
        pat = r.get("pattern", "unknown") or "unknown"
        pattern_data.setdefault(pat, []).append(r["_composite"])
    pattern_summary = [
        {"pattern": pat, "count": len(sc), "avg_score": round(statistics.mean(sc), 4),
         "rank": PATTERN_CONFIG.get(pat, {}).get("rank", "?")}
        for pat, sc in sorted(pattern_data.items())
    ] if pattern_data else []

    # -- 柱別 --
    pillar_counts: dict[str, int] = {p: 0 for p in PILLAR_NAMES}
    pillar_scores: dict[str, list[float]] = {}
    for r in month_rows:
        pil = r.get("pillar", "不明") or "不明"
        if pil in pillar_counts:
            pillar_counts[pil] += 1
        pillar_scores.setdefault(pil, []).append(r["_composite"])
    total_pil = sum(pillar_counts.values()) or 1
    pillar_dist = {p: {"count": c, "ratio": round(c / total_pil, 2)} for p, c in pillar_counts.items()}
    pillar_perf = {pil: round(statistics.mean(scs), 4) if scs else 0.0 for pil, scs in pillar_scores.items()}

    # -- 難易度別 --
    diff_count: dict[str, int] = {"初心者": 0, "中級": 0, "上級": 0}
    for r in month_rows:
        d = PATTERN_CONFIG.get(r.get("pattern", ""), {}).get("difficulty", "中級")
        diff_count[d] = diff_count.get(d, 0) + 1

    # -- ヒートマップ --
    heatmap_data = [{"day": r.get("day", "?"), "time": r.get("time", "?"),
                     "er": r["_er"], "imp": r.get("impressions", 0),
                     "rep": r.get("replies", 0)} for r in month_rows]

    # -- 画像タイプ別 --
    image_type_data: dict[str, list[float]] = {}
    for r in month_rows:
        itype = r.get("image_type", "none") or "none"
        image_type_data.setdefault(itype, []).append(r["_composite"])
    image_type_summary = [
        {"type": itype, "count": len(sc), "avg_score": round(statistics.mean(sc), 4)}
        for itype, sc in sorted(image_type_data.items())
    ] if image_type_data else []

    # -- タイムライン（全件） --
    all_volumes = [_calc_volume(r) for r in all_rows]
    all_qualities = [_calc_quality(r) for r in all_rows]
    all_norm_v = _normalize(all_volumes)
    all_norm_q = _normalize(all_qualities)
    all_composites = [vr * nv + qr * nq for nv, nq in zip(all_norm_v, all_norm_q)]

    timeline = [
        {"date": r.get("date", ""), "day": r.get("day", "?"), "pattern": r.get("pattern", "?"),
         "pillar": r.get("pillar", "?"), "status": r.get("status", "?"), "topic": r.get("topic", ""),
         "impressions": r.get("impressions", 0),
         "engagement_rate": round(_calc_quality(r), 2),
         "likes": r.get("likes", 0), "replies": r.get("replies", 0),
         "retweets": r.get("retweets", 0), "bookmarks": r.get("bookmarks", 0),
         "composite_score": round(cs, 4),
         "image_type": r.get("image_type", ""), "image_issues": "",
         "content_type": r.get("content_type", ""), "source": r.get("source", ""),
         "char_count": r.get("char_count", 0),
         "post_text": (r.get("post_text", "") or "")[:80],
         "detail_clicks": r.get("detail_clicks", 0),
         "profile_visits": r.get("profile_visits", 0),
         "link_clicks": r.get("link_clicks", 0),
         "time_slot": r.get("time_slot", ""),
         "note_linked": "有" if r.get("note_url", "") else "無"}
        for r, cs in zip(all_rows, all_composites)
    ]

    # -- C種別（コンテンツタイプ）集計 --
    ct_data: dict[str, list[dict]] = {}
    for r in month_rows:
        ct = r.get("content_type", "") or "不明"
        ct_data.setdefault(ct, []).append(r)
    content_type_summary = [
        {"type": ct, "label": CONTENT_TYPE_NAMES.get(ct, ct), "count": len(rows),
         "avg_score": round(statistics.mean([r["_composite"] for r in rows]), 4) if rows else 0,
         "avg_er": round(statistics.mean([r["_er"] for r in rows if r["_er"] > 0]), 2) if any(r["_er"] > 0 for r in rows) else 0,
         "avg_imp": round(statistics.mean([r.get("impressions", 0) for r in rows]), 1)}
        for ct, rows in sorted(ct_data.items())
    ]

    # -- ネタ元（ソース）集計 --
    src_data: dict[str, list[dict]] = {}
    for r in month_rows:
        src = r.get("source", "") or "不明"
        src_data.setdefault(src, []).append(r)
    source_summary = [
        {"source": src, "count": len(rows),
         "avg_score": round(statistics.mean([r["_composite"] for r in rows]), 4) if rows else 0,
         "avg_er": round(statistics.mean([r["_er"] for r in rows if r["_er"] > 0]), 2) if any(r["_er"] > 0 for r in rows) else 0}
        for src, rows in sorted(src_data.items())
    ]

    # -- 投稿枠（time_slot）集計 --
    ts_data: dict[str, list[dict]] = {}
    for r in month_rows:
        ts = r.get("time_slot", "") or "不明"
        ts_data.setdefault(ts, []).append(r)
    time_slot_summary = [
        {"slot": ts, "count": len(rows),
         "avg_er": round(statistics.mean([r["_er"] for r in rows if r["_er"] > 0]), 2) if any(r["_er"] > 0 for r in rows) else 0,
         "avg_imp": round(statistics.mean([r.get("impressions", 0) for r in rows]), 1)}
        for ts, rows in sorted(ts_data.items())
    ]

    # -- クロス分析（C種別×パターン） --
    cross_data: dict[str, list[dict]] = {}
    for r in month_rows:
        ct = r.get("content_type", "") or "不明"
        pat = r.get("pattern", "") or "不明"
        key = f"{ct}×{pat}"
        cross_data.setdefault(key, []).append(r)
    cross_summary = sorted([
        {"combo": k, "ct": k.split("×")[0], "pattern": k.split("×")[1],
         "count": len(rows),
         "avg_score": round(statistics.mean([r["_composite"] for r in rows]), 4),
         "avg_er": round(statistics.mean([r["_er"] for r in rows if r["_er"] > 0]), 2) if any(r["_er"] > 0 for r in rows) else 0,
         "avg_imp": round(statistics.mean([r.get("impressions", 0) for r in rows]), 1)}
        for k, rows in cross_data.items()
    ], key=lambda x: x["avg_score"], reverse=True)

    # -- 改善分析（ワースト + 示唆） --
    sorted_by_score = sorted(month_rows, key=lambda r: r["_composite"])
    worst_posts = [
        {"date": r.get("date", ""), "topic": (r.get("topic", "") or "")[:30],
         "pattern": r.get("pattern", ""), "content_type": r.get("content_type", ""),
         "impressions": r.get("impressions", 0),
         "er": round(r["_er"], 2), "score": round(r["_composite"], 4),
         "time_slot": r.get("time_slot", ""), "image_type": r.get("image_type", "")}
        for r in sorted_by_score[:5]
    ]
    # C種別の偏りチェック
    used_cts = set(r.get("content_type", "") for r in month_rows if r.get("content_type"))
    all_cts = set(CONTENT_TYPE_NAMES.keys())
    unused_cts = [{"type": ct, "label": CONTENT_TYPE_NAMES[ct]} for ct in sorted(all_cts - used_cts)]
    # 偏り警告
    ct_counts = {}
    for r in month_rows:
        ct = r.get("content_type", "") or "不明"
        ct_counts[ct] = ct_counts.get(ct, 0) + 1
    total_n = len(month_rows)
    skew_warnings = []
    for ct, cnt in ct_counts.items():
        ratio = cnt / total_n if total_n > 0 else 0
        if ratio >= 0.4:
            label = CONTENT_TYPE_NAMES.get(ct, ct)
            skew_warnings.append(f"{ct}（{label}）が全体の{ratio:.0%}を占めています。他のC種別を試しましょう")

    # -- note連動分析 --
    linked = [r for r in month_rows if r.get("note_url", "")]
    unlinked = [r for r in month_rows if not r.get("note_url", "")]
    def _avg_or_zero(lst, key):
        vals = [r.get(key, 0) for r in lst]
        return round(statistics.mean(vals), 1) if vals else 0
    note_link_analysis = {
        "linked": {"count": len(linked), "avg_imp": _avg_or_zero(linked, "impressions"),
                   "avg_profile": _avg_or_zero(linked, "profile_visits"),
                   "avg_link_clicks": _avg_or_zero(linked, "link_clicks")},
        "unlinked": {"count": len(unlinked), "avg_imp": _avg_or_zero(unlinked, "impressions"),
                     "avg_profile": _avg_or_zero(unlinked, "profile_visits"),
                     "avg_link_clicks": _avg_or_zero(unlinked, "link_clicks")},
    }

    # -- 週次レポート（YAMLのまま — 週次集計は蓄積型のため） --
    weekly_reports = []
    if WEEKLY_DIR.exists():
        for f in sorted(WEEKLY_DIR.glob("*.yaml")):
            with open(f, encoding="utf-8") as fh:
                wr = yaml.safe_load(fh)
                if wr:
                    weekly_reports.append(wr)

    return dict(
        month=month, total_posts=len(month_rows), total_all_posts=len(all_rows),
        total_impressions=total_imp, total_engagements=total_eng, total_replies=total_rep,
        total_bookmarks=total_bkm, total_retweets=total_rt, total_likes=total_likes,
        avg_engagement_rate=round(avg_er, 2), pattern_summary=pattern_summary,
        pillar_dist=pillar_dist, pillar_perf=pillar_perf, diff_count=diff_count,
        heatmap_data=heatmap_data, image_type_summary=image_type_summary,
        issues=[], timeline=timeline, weekly_reports=weekly_reports,
        content_type_summary=content_type_summary, source_summary=source_summary,
        time_slot_summary=time_slot_summary, note_link_analysis=note_link_analysis,
        cross_summary=cross_summary, worst_posts=worst_posts,
        unused_cts=unused_cts, skew_warnings=skew_warnings,
    )


def collect_note_data(month: str) -> dict:
    return dict(month=month, total_posts=0, total_pv=0, total_likes=0, total_comments=0, articles=[])


def collect_trend_data() -> dict:
    rd = ROOT / "knowledge" / "logs" / "x" / "research"
    trends, ideas = [], []
    if (rd / "trend").exists():
        for f in sorted((rd / "trend").glob("*.yaml")):
            with open(f, encoding="utf-8") as fh:
                d = yaml.safe_load(fh)
                if d: trends.append(d)
    if (rd / "ideas.yaml").exists():
        with open(rd / "ideas.yaml", encoding="utf-8") as fh:
            d = yaml.safe_load(fh)
            ideas = d.get("ideas", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
    return {"trend_reports": trends, "ideas": ideas}


def collect_competitive_data(config: dict) -> dict:
    """competitor_benchmark.db から競合データを取得"""
    empty = {"accounts": [], "type_summary": [], "top_posts": [], "total_accounts": 0,
             "rules": [], "note_accounts": [], "note_type_summary": []}
    if not COMP_DB_PATH.exists():
        return empty

    conn = _get_comp_conn()
    cur = conn.cursor()

    # X アカウント種別サマリー
    cur.execute("SELECT account_type, COUNT(*) as cnt FROM x_accounts WHERE is_active=1 GROUP BY account_type ORDER BY cnt DESC")
    type_summary = [{"type": r[0], "count": r[1]} for r in cur.fetchall()]
    total_accounts = sum(t["count"] for t in type_summary)

    # X アカウント一覧（followers 追加）
    cur.execute("""
        SELECT handle, name, category, account_type, fork_direction, ng_reason, followers
        FROM x_accounts WHERE is_active=1
        ORDER BY account_type, handle
    """)
    accounts = [{"handle": r[0], "name": r[1], "category": r[2],
                 "type": r[3], "fork_direction": r[4], "ng_reason": r[5], "followers": r[6]}
                for r in cur.fetchall()]

    # トップパフォーマンス投稿（followers 追加）
    cur.execute("""
        SELECT p.handle, a.name, a.followers, p.date, p.topic, p.content_pattern,
               p.views, p.likes, p.retweets, p.replies, p.bookmarks
        FROM x_posts p JOIN x_accounts a ON p.handle = a.handle
        WHERE a.account_type = 'benchmark'
        ORDER BY p.views DESC LIMIT 10
    """)
    top_posts = [{"handle": r[0], "name": r[1], "followers": r[2], "date": r[3],
                  "topic": r[4], "pattern": r[5], "views": r[6], "likes": r[7],
                  "retweets": r[8], "replies": r[9], "bookmarks": r[10]}
                 for r in cur.fetchall()]

    # note アカウント種別サマリー
    cur.execute("SELECT account_type, COUNT(*) as cnt FROM note_accounts WHERE is_active=1 GROUP BY account_type ORDER BY cnt DESC")
    note_type_summary = [{"type": r[0], "count": r[1]} for r in cur.fetchall()]

    # note アカウント一覧
    cur.execute("""
        SELECT handle, name, category, account_type, fork_direction, ng_reason, cpt_score
        FROM note_accounts WHERE is_active=1
        ORDER BY account_type, handle
    """)
    note_accounts = [{"handle": r[0], "name": r[1], "category": r[2],
                      "type": r[3], "fork_direction": r[4], "ng_reason": r[5], "cpt_score": r[6]}
                     for r in cur.fetchall()]

    # 運用ルール / KPI 目標値
    cur.execute("SELECT rule_id, category, description, value FROM rules WHERE enabled=1")
    rules = [{"id": r[0], "category": r[1], "description": r[2], "value": r[3]}
             for r in cur.fetchall()]

    conn.close()
    return {"accounts": accounts, "type_summary": type_summary,
            "top_posts": top_posts, "total_accounts": total_accounts,
            "rules": rules, "note_accounts": note_accounts,
            "note_type_summary": note_type_summary}


def collect_algorithm_data(x_data: dict) -> dict:
    weekly_ers = []
    for wr in x_data.get("weekly_reports", []):
        s = wr.get("summary", {})
        weekly_ers.append({"week": wr.get("week", "?"), "avg_er": s.get("avg_engagement_rate", 0),
                           "avg_score": s.get("avg_composite_score", 0), "total_imp": s.get("total_impressions", 0)})
    return {"weekly_ers": weekly_ers}


def collect_system_data() -> dict:
    sd = ROOT / "knowledge" / "logs" / "system"
    task_logs, error_logs = [], []
    for sub, lst in [("tasks", task_logs), ("errors", error_logs)]:
        if (sd / sub).exists():
            for f in sorted((sd / sub).glob("*.yaml")):
                with open(f, encoding="utf-8") as fh:
                    d = yaml.safe_load(fh)
                    if d: lst.append(d)
    return {"task_logs": task_logs, "error_logs": error_logs}


# =========================================================================
# HTML 構築
# =========================================================================
def build_html(month: str, x_data: dict, note_data: dict, comp_data: dict,
               trend_data: dict, algo_data: dict, sys_data: dict, config: dict) -> str:
    cdn = config.get("dashboard", {}).get("chart_cdn", "https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js")
    tenants = config.get("tenants", {})
    tenant_name = tenants.get("default", {}).get("name", "Delvework for SNS")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Delvework for SNS — {month}</title>
<script src="{cdn}"></script>
<style>{_css()}</style>
</head>
<body>

{_header(month, tenant_name, tenants)}

<div class="layout">
  {_sidebar_integrated(trend_data, algo_data, sys_data)}
  {_sidebar_x(x_data)}
  {_sidebar_note(comp_data)}

  <main class="content">
    {_pages_integrated(month, x_data, note_data, comp_data, trend_data, algo_data, sys_data)}
    {_pages_x(x_data)}
    {_pages_note(note_data, comp_data)}
  </main>
</div>

<script>
{_js_all(x_data, algo_data, trend_data, config)}
</script>
</body>
</html>"""


# =========================================================================
# CSS
# =========================================================================
def _css() -> str:
    return """
:root {
  /* 森テーマ: ヘッダー=深緑の葉, サイド=幹, 背景=芝生, カード=ガーデニング */
  --bg: #c8d8a8; --bg2: #bdd19e; --surface: #f0e4d0; --surface2: #e8daC2;
  --surface3: #ddd0b4; --border: #c8b898; --border2: #b8a880;
  --text: #2e3a1e; --text2: #4a5438; --muted: #7a8068;
  --accent: #4a7a3a; --accent2: #3d6830; --accent-bg: rgba(74,122,58,0.1);
  --green: #4a8c3a; --yellow: #b89a2a; --red: #b85a3a; --blue: #4a7a9e;
  --pink: #c07a7a; --teal: #4a9a80; --orange: #c08a40; --purple: #8a6ea0; --cyan: #4a9494;
  /* 構造別カラー */
  --header-bg: #1e3a1e; --header-text: #d0e8c0;
  --sidebar-bg: #5c3d1e; --sidebar-text: #f0e6d0;
  --header-h: 52px; --sidebar-w: 220px;
}
* { margin:0; padding:0; box-sizing:border-box; }
html,body { height:100%; overflow:hidden; }
body { background:var(--bg); color:var(--text); font-family:'Segoe UI','Noto Sans JP',system-ui,sans-serif; font-size:13px; }

/* ===== ヘッダー ===== */
.header {
  height:var(--header-h); background:var(--header-bg); border-bottom:1px solid #153015;
  display:flex; align-items:center; padding:0 20px; position:fixed; top:0; left:0; right:0; z-index:200;
}
.header-brand { font-weight:800; font-size:1rem; margin-right:32px; letter-spacing:-0.02em; color:#fff; }
.header-tabs { display:flex; gap:2px; }
.header-tab {
  background:none; border:none; color:rgba(255,255,255,0.7); font-size:0.8rem; font-weight:500;
  padding:6px 16px; cursor:pointer; border-radius:6px; transition:all 0.15s;
}
.header-tab:hover { background:rgba(255,255,255,0.1); color:#fff; }
.header-tab.active { background:rgba(255,255,255,0.15); color:#fff; font-weight:700; }
.header-right { margin-left:auto; display:flex; align-items:center; gap:12px; }
.account-select {
  background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.2); color:#fff;
  padding:5px 12px; border-radius:6px; font-size:0.78rem; cursor:pointer; outline:none;
}
.account-select:focus { border-color:rgba(255,255,255,0.4); }
.header-meta { color:rgba(255,255,255,0.7); font-size:0.72rem; }

/* ===== レイアウト ===== */
.layout { display:flex; margin-top:var(--header-h); height:calc(100vh - var(--header-h)); }

/* ===== サイドバー ===== */
.sidebar {
  width:var(--sidebar-w); background:var(--sidebar-bg); border-right:1px solid #4a2e14;
  overflow-y:auto; flex-shrink:0; display:none; /* JS で active を付与 */
}
.sidebar.active { display:flex; flex-direction:column; }
.sidebar-section { padding:16px 0 8px; }
.sidebar-label { color:#b8a888; font-size:0.65rem; text-transform:uppercase; letter-spacing:0.1em; padding:0 16px 6px; font-weight:700; }
.side-item {
  display:flex; align-items:center; gap:8px; padding:7px 16px; cursor:pointer;
  color:var(--sidebar-text); font-size:0.8rem; transition:all 0.12s; border-left:3px solid transparent;
}
.side-item:hover { background:rgba(255,255,255,0.06); color:#fff; }
.side-item.active { background:rgba(74,122,58,0.2); color:#a0d890; border-left-color:#4a7a3a; font-weight:600; }
.side-icon { font-size:0.85rem; width:16px; text-align:center; flex-shrink:0; opacity:0.7; }
.side-badge { margin-left:auto; background:#4a7a3a; color:#fff; font-size:0.6rem; padding:1px 6px; border-radius:8px; font-weight:700; }

.sidebar-footer { margin-top:auto; padding:12px 16px; border-top:1px solid #4a2e14; }
.sidebar-footer span { color:#b8a888; font-size:0.68rem; line-height:1.6; }

/* ===== コンテンツ ===== */
.content { flex:1; overflow-y:auto; background:var(--bg2); }
.page { display:none; }
.page.active { display:block; }
.page-head { padding:20px 28px 14px; border-bottom:1px solid var(--border); background:var(--surface); position:sticky; top:0; z-index:50; }
.page-head h2 { font-size:1.05rem; font-weight:700; }
.page-head p { color:var(--muted); font-size:0.75rem; margin-top:2px; }
.page-body { padding:20px 28px 40px; }

/* ===== KPI ===== */
.kpi-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(145px,1fr)); gap:10px; margin-bottom:20px; }
.kpi { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:14px; }
.kpi-label { color:var(--muted); font-size:0.68rem; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:3px; }
.kpi-val { font-size:1.4rem; font-weight:700; line-height:1.2; }
.kpi-sub { color:var(--muted); font-size:0.68rem; margin-top:3px; }

/* ===== セクション ===== */
.sec { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:18px; margin-bottom:16px; }
.sec-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid var(--border); }
.sec-head h3 { font-size:0.88rem; font-weight:600; }
.sec-tag { color:var(--muted); font-size:0.7rem; background:var(--surface2); padding:2px 8px; border-radius:5px; }

/* ===== チャート ===== */
.ch-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:16px; }
.ch-grid3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; margin-bottom:16px; }
.ch-box { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:14px; }
.ch-box h4 { font-size:0.78rem; color:var(--muted); margin-bottom:8px; font-weight:500; }
canvas { max-height:260px; }

/* ===== テーブル ===== */
.tw { overflow-x:auto; }
table { width:100%; border-collapse:collapse; font-size:0.78rem; }
th { text-align:left; color:var(--muted); font-weight:600; padding:7px 8px; border-bottom:2px solid var(--border); position:sticky; top:0; background:var(--surface); cursor:pointer; user-select:none; white-space:nowrap; }
th:hover { color:var(--text); }
th .sa { font-size:0.6rem; margin-left:2px; opacity:0.4; }
td { padding:6px 8px; border-bottom:1px solid var(--border); }
tr:hover td { background:rgba(74,122,58,0.06); }

.bdg { display:inline-block; padding:1px 7px; border-radius:5px; font-size:0.68rem; font-weight:600; }
.bdg-posted { background:rgba(34,197,94,0.1); color:var(--green); }
.bdg-scheduled { background:rgba(234,179,8,0.1); color:var(--yellow); }
.bdg-draft { background:rgba(124,128,154,0.1); color:var(--muted); }
.bdg-s { background:rgba(239,68,68,0.1); color:var(--red); }
.bdg-a { background:rgba(234,179,8,0.1); color:var(--yellow); }
.bdg-b { background:rgba(34,197,94,0.1); color:var(--green); }
.bdg-c { background:rgba(124,128,154,0.1); color:var(--muted); }

/* ===== 空状態 ===== */
.empty { text-align:center; padding:32px 16px; }
.empty-icon { font-size:1.6rem; margin-bottom:8px; opacity:0.25; }
.empty-title { color:var(--text2); font-size:0.88rem; font-weight:600; margin-bottom:4px; }
.empty-desc { color:var(--muted); font-size:0.76rem; max-width:380px; margin:0 auto; line-height:1.5; }
.empty-cmd { background:var(--surface2); color:var(--cyan); font-size:0.72rem; padding:6px 12px; border-radius:5px; display:inline-block; margin-top:8px; font-family:monospace; }

/* ===== PF カード ===== */
.pf-card { display:flex; align-items:center; gap:14px; padding:14px; background:var(--surface2); border:1px solid var(--border); border-radius:8px; margin-bottom:10px; }
.pf-icon { width:40px; height:40px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:1.1rem; flex-shrink:0; }
.pf-stats { display:flex; gap:18px; flex-wrap:wrap; margin-top:4px; }
.pf-st-l { color:var(--muted); font-size:0.66rem; text-transform:uppercase; }
.pf-st-v { font-size:1rem; font-weight:700; }

/* ===== カード系 ===== */
.item-card { background:var(--surface2); border:1px solid var(--border); border-radius:7px; padding:11px 13px; margin-bottom:7px; }
.item-title { font-weight:600; font-size:0.82rem; margin-bottom:3px; }
.item-meta { color:var(--muted); font-size:0.7rem; }
.item-tag { font-size:0.68rem; padding:1px 6px; border-radius:3px; background:var(--surface); margin-right:4px; }
.issue-item { padding:7px 11px; border-left:3px solid var(--yellow); margin-bottom:5px; background:rgba(234,179,8,0.03); border-radius:0 5px 5px 0; font-size:0.8rem; }
.issue-id { font-weight:700; margin-right:6px; color:var(--yellow); }

@media (max-width:1100px) { .ch-grid,.ch-grid3 { grid-template-columns:1fr; } }
@media (max-width:768px) { :root { --sidebar-w:180px; } .kpi-row { grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); } }
"""


# =========================================================================
# ヘッダー
# =========================================================================
def _header(month: str, tenant_name: str, tenants: dict) -> str:
    tenant_options = ""
    for tid, t in tenants.items():
        sel = " selected" if tid == "default" else ""
        tenant_options += f'<option value="{tid}"{sel}>{t.get("name", tid)}</option>'

    return f"""
<header class="header">
  <div class="header-brand">Delvework for SNS</div>
  <div class="header-tabs">
    <button class="header-tab active" data-platform="integrated">統合</button>
    <button class="header-tab" data-platform="x">X</button>
    <button class="header-tab" data-platform="note">note</button>
  </div>
  <div class="header-right">
    <select class="account-select" id="tenant-select">{tenant_options}</select>
    <span class="header-meta">{month} | <span id="gen-time"></span></span>
  </div>
</header>"""


# =========================================================================
# サイドバー（媒体別に3本）
# =========================================================================
def _sidebar_integrated(trend_data: dict, algo_data: dict, sys_data: dict) -> str:
    idea_n = len(trend_data.get("ideas", []))
    weekly_n = len(algo_data.get("weekly_ers", []))
    return f"""
<aside class="sidebar active" id="sidebar-integrated">
  <div class="sidebar-section">
    <div class="sidebar-label">概況</div>
    <div class="side-item active" data-page="i-summary"><span class="side-icon">&#9632;</span>サマリー</div>
  </div>
  <div class="sidebar-section">
    <div class="sidebar-label">分析</div>
    <div class="side-item" data-page="i-competitive"><span class="side-icon">&#9733;</span>競合分析</div>
    <div class="side-item" data-page="i-trend"><span class="side-icon">&#9650;</span>トレンド観測{f'<span class="side-badge">{idea_n}</span>' if idea_n else ''}</div>
  </div>
  <div class="sidebar-section">
    <div class="sidebar-label">運用</div>
    <div class="side-item" data-page="i-algorithm"><span class="side-icon">&#9881;</span>アルゴリズム監視{f'<span class="side-badge">{weekly_n}w</span>' if weekly_n else ''}</div>
    <div class="side-item" data-page="i-system"><span class="side-icon">&#9998;</span>システム管理</div>
  </div>
  <div class="sidebar-footer"><span>統合ダッシュボード<br>全プラットフォーム横断</span></div>
</aside>"""


def _sidebar_x(x_data: dict) -> str:
    n = x_data["total_posts"]
    issues = len(x_data.get("issues", []))
    return f"""
<aside class="sidebar" id="sidebar-x">
  <div class="sidebar-section">
    <div class="sidebar-label">分析</div>
    <div class="side-item active" data-page="x-overview"><span class="side-icon">&#9632;</span>概況{f'<span class="side-badge">{n}</span>' if n else ''}</div>
    <div class="side-item" data-page="x-patterns"><span class="side-icon">&#9830;</span>パターン分析</div>
    <div class="side-item" data-page="x-content-type"><span class="side-icon">&#9670;</span>コンテンツ種別</div>
    <div class="side-item" data-page="x-pillars"><span class="side-icon">&#9878;</span>柱バランス</div>
    <div class="side-item" data-page="x-timeslot"><span class="side-icon">&#9200;</span>曜日×時間帯</div>
    <div class="side-item" data-page="x-images"><span class="side-icon">&#9635;</span>画像分析{f'<span class="side-badge">{issues}</span>' if issues else ''}</div>
    <div class="side-item" data-page="x-note-link"><span class="side-icon">&#9741;</span>note連動</div>
    <div class="side-item" data-page="x-cross"><span class="side-icon">&#9851;</span>クロス分析</div>
    <div class="side-item" data-page="x-improve"><span class="side-icon">&#9888;</span>改善分析</div>
  </div>
  <div class="sidebar-section">
    <div class="sidebar-label">データ</div>
    <div class="side-item" data-page="x-posts"><span class="side-icon">&#9776;</span>投稿一覧</div>
  </div>
  <div class="sidebar-footer"><span>X（旧Twitter）<br>投稿パフォーマンス分析</span></div>
</aside>"""


def _sidebar_note(comp_data: dict) -> str:
    note_n = sum(t["count"] for t in comp_data.get("note_type_summary", []))
    return f"""
<aside class="sidebar" id="sidebar-note">
  <div class="sidebar-section">
    <div class="sidebar-label">分析</div>
    <div class="side-item active" data-page="n-overview"><span class="side-icon">&#9632;</span>概況</div>
    <div class="side-item" data-page="n-articles"><span class="side-icon">&#9776;</span>競合アカウント{f'<span class="side-badge">{note_n}</span>' if note_n else ''}</div>
    <div class="side-item" data-page="n-categories"><span class="side-icon">&#9830;</span>カテゴリ別</div>
    <div class="side-item" data-page="n-trends"><span class="side-icon">&#9650;</span>PV推移</div>
  </div>
  <div class="sidebar-footer"><span>note<br>記事パフォーマンス分析</span></div>
</aside>"""


# =========================================================================
# ページ群: 統合
# =========================================================================
def _pages_integrated(month, x_data, note_data, comp_data, trend_data, algo_data, sys_data) -> str:
    return (_pg_i_summary(month, x_data, note_data, comp_data) +
            _pg_i_competitive(comp_data) +
            _pg_i_trend(trend_data) +
            _pg_i_algorithm(algo_data) +
            _pg_i_system(sys_data))


def _pg_i_summary(month, x, n, cd) -> str:
    total_p = x["total_posts"] + n["total_posts"]
    total_r = x["total_impressions"] + n["total_pv"]
    posted = sum(1 for t in x["timeline"] if t["status"] == "posted")
    sched = sum(1 for t in x["timeline"] if t["status"] == "scheduled")

    # 目標 vs 実績（rules テーブルから）
    rules = {r["id"]: r for r in cd.get("rules", [])}
    # 運用日数（月の投稿期間）
    dates = set(t["date"] for t in x["timeline"] if t["date"].startswith(month))
    days_active = len(dates) or 1
    weeks_active = max(days_active / 7, 1)

    goal_posts = int(rules.get("growth_daily_posts", {}).get("value", 0))
    goal_replies = int(rules.get("growth_daily_replies", {}).get("value", 0))
    goal_qrt = int(rules.get("growth_quote_rt_per_week", {}).get("value", 0))
    actual_posts_day = round(x["total_posts"] / days_active, 1) if x["total_posts"] else 0
    actual_replies_day = round(x["total_replies"] / days_active, 1) if x["total_replies"] else 0
    actual_rt_week = round(x["total_retweets"] / weeks_active, 1) if x["total_retweets"] else 0

    def _goal_color(actual, goal):
        if goal == 0: return "var(--muted)"
        ratio = actual / goal
        if ratio >= 0.8: return "var(--green)"
        if ratio >= 0.5: return "var(--yellow)"
        return "var(--red)"

    goals_html = ""
    if goal_posts or goal_replies or goal_qrt:
        goals_html = f"""
    <div class="sec"><div class="sec-head"><h3>目標 vs 実績</h3><span class="sec-tag">rules テーブル</span></div>
      <div class="kpi-row">
        <div class="kpi"><div class="kpi-label">日次投稿</div><div class="kpi-val" style="color:{_goal_color(actual_posts_day, goal_posts)}">{actual_posts_day}</div><div class="kpi-sub">目標 {goal_posts}/日</div></div>
        <div class="kpi"><div class="kpi-label">日次リプライ</div><div class="kpi-val" style="color:{_goal_color(actual_replies_day, goal_replies)}">{actual_replies_day}</div><div class="kpi-sub">目標 {goal_replies}/日</div></div>
        <div class="kpi"><div class="kpi-label">週次RT</div><div class="kpi-val" style="color:{_goal_color(actual_rt_week, goal_qrt)}">{actual_rt_week}</div><div class="kpi-sub">目標 {goal_qrt}/週</div></div>
      </div>
    </div>"""

    return f"""
<div class="page active" id="page-i-summary">
  <div class="page-head"><h2>サマリー</h2><p>{month} — 全プラットフォーム横断のパフォーマンス概況</p></div>
  <div class="page-body">
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">総投稿数</div><div class="kpi-val" style="color:var(--accent)">{total_p}</div></div>
      <div class="kpi"><div class="kpi-label">総リーチ</div><div class="kpi-val">{total_r:,}</div></div>
      <div class="kpi"><div class="kpi-label">投稿済</div><div class="kpi-val" style="color:var(--green)">{posted}</div></div>
      <div class="kpi"><div class="kpi-label">予約</div><div class="kpi-val" style="color:var(--yellow)">{sched}</div></div>
    </div>{goals_html}
    <div class="sec"><div class="sec-head"><h3>プラットフォーム別</h3><span class="sec-tag">{month}</span></div>
      <div class="pf-card">
        <div class="pf-icon" style="background:rgba(29,161,242,0.1);color:#1da1f2">X</div>
        <div><div style="font-weight:600;margin-bottom:5px">X（旧Twitter）</div>
          <div class="pf-stats">
            <div><div class="pf-st-l">投稿</div><div class="pf-st-v">{x["total_posts"]}</div></div>
            <div><div class="pf-st-l">インプレッション</div><div class="pf-st-v">{x["total_impressions"]:,}</div></div>
            <div><div class="pf-st-l">ER</div><div class="pf-st-v" style="color:var(--green)">{x["avg_engagement_rate"]}%</div></div>
            <div><div class="pf-st-l">リプライ</div><div class="pf-st-v" style="color:var(--blue)">{x["total_replies"]}</div></div>
            <div><div class="pf-st-l">いいね</div><div class="pf-st-v" style="color:var(--pink)">{x["total_likes"]}</div></div>
          </div>
        </div>
      </div>
      <div class="pf-card">
        <div class="pf-icon" style="background:rgba(45,204,112,0.1);color:#2dcc70">N</div>
        <div><div style="font-weight:600;margin-bottom:5px">note</div>
          <div class="pf-stats">
            <div><div class="pf-st-l">記事</div><div class="pf-st-v">{n["total_posts"]}</div></div>
            <div><div class="pf-st-l">PV</div><div class="pf-st-v">{n["total_pv"]:,}</div></div>
            <div><div class="pf-st-l">スキ</div><div class="pf-st-v">{n["total_likes"]}</div></div>
          </div>
        </div>
      </div>
    </div>
    <div class="ch-grid">
      <div class="ch-box"><h4>プラットフォーム別投稿数</h4><canvas id="c-sum-posts"></canvas></div>
      <div class="ch-box"><h4>プラットフォーム別リーチ</h4><canvas id="c-sum-reach"></canvas></div>
    </div>
  </div>
</div>"""


def _pg_i_competitive(cd) -> str:
    type_sum = cd.get("type_summary", [])
    accounts = cd.get("accounts", [])
    top_posts = cd.get("top_posts", [])
    total = cd.get("total_accounts", 0)
    note_accts = cd.get("note_accounts", [])
    note_ts = cd.get("note_type_summary", [])
    has_data = bool(type_sum)

    # X種別 + note種別 合算サマリーカード
    type_colors = {"benchmark": "var(--green)", "ng": "var(--red)", "news": "var(--blue)",
                   "engagement": "var(--yellow)", "growth": "var(--teal)", "visual": "var(--purple)"}
    type_cards = ""
    for t in type_sum:
        c = type_colors.get(t["type"], "var(--muted)")
        type_cards += f'<div class="kpi"><div class="kpi-label">X {t["type"]}</div><div class="kpi-val" style="color:{c}">{t["count"]}</div></div>'
    for t in note_ts:
        c = type_colors.get(t["type"], "var(--muted)")
        type_cards += f'<div class="kpi"><div class="kpi-label">note {t["type"]}</div><div class="kpi-val" style="color:{c}">{t["count"]}</div></div>'

    # X ベンチマークアカウント一覧（followers追加）
    bench_rows = ""
    for a in accounts:
        if a["type"] == "benchmark":
            fw = f'{a["followers"]:,}' if a.get("followers") else "-"
            bench_rows += f'<tr><td>@{a["handle"]}</td><td>{a["name"]}</td><td>{a["category"]}</td><td style="text-align:right">{fw}</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{a["fork_direction"]}">{a["fork_direction"]}</td></tr>'

    # X NGアカウント一覧
    ng_rows = ""
    for a in accounts:
        if a["type"] == "ng":
            ng_rows += f'<tr><td>@{a["handle"]}</td><td>{a["name"]}</td><td>{a["category"]}</td><td style="color:var(--red)">{a["ng_reason"]}</td></tr>'

    # X トップ投稿（followers追加）
    post_rows = ""
    for p in top_posts:
        fw = f'{p["followers"]:,}' if p.get("followers") else "-"
        post_rows += f'<tr><td>@{p["handle"]}</td><td>{fw}</td><td>{p["date"]}</td><td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{p["topic"]}">{p["topic"]}</td><td>{p["views"]:,}</td><td>{p["likes"]:,}</td><td>{p["retweets"]}</td><td>{p["bookmarks"]}</td></tr>'

    # note ベンチマーク / NG / ニュース
    note_bench_rows = ""
    for a in note_accts:
        if a["type"] == "benchmark":
            note_bench_rows += f'<tr><td>{a["handle"]}</td><td>{a["name"]}</td><td>{a["category"]}</td><td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{a["fork_direction"]}">{a["fork_direction"]}</td><td>{a.get("cpt_score","")}</td></tr>'
    note_ng_rows = ""
    for a in note_accts:
        if a["type"] == "ng":
            note_ng_rows += f'<tr><td>{a["handle"]}</td><td>{a["name"]}</td><td>{a["category"]}</td><td style="color:var(--red)">{a["ng_reason"]}</td></tr>'
    note_news_rows = ""
    for a in note_accts:
        if a["type"] == "news":
            note_news_rows += f'<tr><td>{a["handle"]}</td><td>{a["name"]}</td><td>{a["category"]}</td></tr>'

    if not has_data:
        return f"""
<div class="page" id="page-i-competitive">
  <div class="page-head"><h2>競合分析</h2><p>競合アカウントの追跡・ベンチマーク比較</p></div>
  <div class="page-body">
    <div class="empty"><div class="empty-icon">&#9733;</div><div class="empty-title">競合データ未収集</div>
    <div class="empty-desc">competitor_analytics.py でデータを収集してください。</div>
    <div class="empty-cmd">python scripts/competitor_analytics.py collect -p x</div></div>
  </div>
</div>"""

    note_total = sum(t["count"] for t in note_ts)
    return f"""
<div class="page" id="page-i-competitive">
  <div class="page-head"><h2>競合分析</h2><p>X {total}件 + note {note_total}件 追跡中</p></div>
  <div class="page-body">
    <div class="kpi-row">{type_cards}</div>
    <div class="sec"><div class="sec-head"><h3>X ベンチマーク</h3><span class="sec-tag">{sum(1 for a in accounts if a["type"]=="benchmark")}件</span></div>
      <div class="tw"><table><thead><tr><th>ハンドル</th><th>名前</th><th>カテゴリ</th><th>フォロワー</th><th>フォーク方向</th></tr></thead><tbody>{bench_rows}</tbody></table></div>
    </div>
    <div class="sec"><div class="sec-head"><h3>X NG分析</h3><span class="sec-tag">{sum(1 for a in accounts if a["type"]=="ng")}件</span></div>
      <div class="tw"><table><thead><tr><th>ハンドル</th><th>名前</th><th>カテゴリ</th><th>NG理由</th></tr></thead><tbody>{ng_rows}</tbody></table></div>
    </div>
    <div class="sec"><div class="sec-head"><h3>X トップ投稿</h3><span class="sec-tag">{len(top_posts)}件</span></div>
      <div class="tw"><table><thead><tr><th>ハンドル</th><th>フォロワー</th><th>日付</th><th>トピック</th><th>Views</th><th>Likes</th><th>RT</th><th>BM</th></tr></thead><tbody>{post_rows}</tbody></table></div>
    </div>
    <div class="sec"><div class="sec-head"><h3>note ベンチマーク</h3><span class="sec-tag">{sum(1 for a in note_accts if a["type"]=="benchmark")}件</span></div>
      <div class="tw"><table><thead><tr><th>アカウント</th><th>名前</th><th>カテゴリ</th><th>フォーク方向</th><th>C×P×T</th></tr></thead><tbody>{note_bench_rows}</tbody></table></div>
    </div>
    <div class="sec"><div class="sec-head"><h3>note NG分析</h3><span class="sec-tag">{sum(1 for a in note_accts if a["type"]=="ng")}件</span></div>
      <div class="tw"><table><thead><tr><th>アカウント</th><th>名前</th><th>カテゴリ</th><th>NG理由</th></tr></thead><tbody>{note_ng_rows}</tbody></table></div>
    </div>
    {f'<div class="sec"><div class="sec-head"><h3>note ニュース</h3><span class="sec-tag">{sum(1 for a in note_accts if a["type"]=="news")}件</span></div><div class="tw"><table><thead><tr><th>アカウント</th><th>名前</th><th>カテゴリ</th></tr></thead><tbody>{note_news_rows}</tbody></table></div></div>' if note_news_rows else ''}
  </div>
</div>"""


def _pg_i_trend(td) -> str:
    trends = td.get("trend_reports", [])
    ideas = td.get("ideas", [])

    t_cards = ""
    for t in trends[-5:]:
        topic = t.get("topic", t.get("query", t.get("title", "?")))
        t_cards += f'<div class="item-card"><div class="item-title">{topic}</div><div class="item-meta"><span class="item-tag">{t.get("period","?")}</span><span class="item-tag">{str(t.get("collected_at",t.get("date","?")))[:10]}</span></div></div>'
    if not t_cards:
        t_cards = """<div class="empty"><div class="empty-icon">&#9650;</div><div class="empty-title">トレンドデータ未収集</div>
<div class="empty-cmd">python scripts/x_search.py topic "AI活用" --period 7d</div></div>"""

    i_cards = ""
    for idea in ideas[:10]:
        if isinstance(idea, dict):
            st = idea.get("status", "new")
            st_color = "var(--green)" if st == "new" else "var(--muted)"
            i_cards += f'<div class="item-card"><div class="item-title">{idea.get("topic",idea.get("title","?"))}</div><div class="item-meta"><span style="color:{st_color}">{st}</span>{" | " + idea.get("source","") if idea.get("source") else ""}</div></div>'
    if not i_cards:
        i_cards = """<div class="empty"><div class="empty-icon">&#128161;</div><div class="empty-title">アイデアストック空</div>
<div class="empty-desc">リサーチで見つかったネタ候補が ideas.yaml に蓄積されます。</div></div>"""

    return f"""
<div class="page" id="page-i-trend">
  <div class="page-head"><h2>トレンド観測</h2><p>ジャンル全体の話題・フォーマット動向とネタ候補</p></div>
  <div class="page-body">
    <div class="sec"><div class="sec-head"><h3>トレンドレポート</h3><span class="sec-tag">{len(trends)}件</span></div>{t_cards}</div>
    <div class="sec"><div class="sec-head"><h3>アイデアストック</h3><span class="sec-tag">{len(ideas)}件</span></div>{i_cards}</div>
  </div>
</div>"""


def _pg_i_algorithm(ad) -> str:
    wk = ad.get("weekly_ers", [])
    rows = ""
    for w in wk:
        rows += f'<tr><td>{w["week"]}</td><td>{w["avg_er"]}%</td><td>{w["avg_score"]}</td><td>{w["total_imp"]:,}</td></tr>'

    chart_or_empty = '<canvas id="c-algo-er" style="max-height:280px"></canvas>' if wk else ""
    table_or_empty = f'<div class="tw"><table><thead><tr><th>週</th><th>平均 ER</th><th>平均スコア</th><th>総IMP</th></tr></thead><tbody>{rows}</tbody></table></div>' if rows else ""

    if not wk:
        chart_or_empty = """<div class="empty"><div class="empty-icon">&#128200;</div><div class="empty-title">週次データ未蓄積</div>
<div class="empty-desc">週次レポートを蓄積すると ER 推移と異常検知が表示されます。</div>
<div class="empty-cmd">python scripts/x_report.py weekly</div></div>"""

    return f"""
<div class="page" id="page-i-algorithm">
  <div class="page-head"><h2>アルゴリズム監視</h2><p>エンゲージメント率の推移・異常検知・仕様変更の追跡</p></div>
  <div class="page-body">
    <div class="sec"><div class="sec-head"><h3>ER 推移</h3><span class="sec-tag">週次</span></div>{chart_or_empty}</div>
    {f'<div class="sec"><div class="sec-head"><h3>週次データ</h3><span class="sec-tag">{len(wk)}週</span></div>{table_or_empty}</div>' if wk else ''}
    <div class="sec"><div class="sec-head"><h3>異常検知アラート</h3><span class="sec-tag">自動</span></div>
      <div class="empty"><div class="empty-icon">&#9888;</div><div class="empty-title">異常なし</div>
      <div class="empty-desc">12週分蓄積後、移動平均±2σ逸脱を自動検知。</div></div>
    </div>
    <div class="sec"><div class="sec-head"><h3>仕様変更ログ</h3><span class="sec-tag">手動</span></div>
      <div class="empty"><div class="empty-icon">&#128221;</div><div class="empty-title">記録なし</div>
      <div class="empty-desc">knowledge/logs/x/algorithm/ に記録。</div></div>
    </div>
  </div>
</div>"""


def _pg_i_system(sd) -> str:
    tl = sd.get("task_logs", [])
    el = sd.get("error_logs", [])
    t_rows = ""
    for log in tl[-3:]:
        for e in log.get("executions", [])[-10:]:
            sc = "bdg-posted" if e.get("status") == "success" else "bdg-s"
            t_rows += f'<tr><td>{e.get("task","?")}</td><td>{str(e.get("timestamp","?"))[:19]}</td><td><span class="bdg {sc}">{e.get("status","?")}</span></td><td>{e.get("duration_sec",0)}秒</td></tr>'

    tasks_html = f'<div class="tw"><table><thead><tr><th>タスク</th><th>日時</th><th>状態</th><th>所要時間</th></tr></thead><tbody>{t_rows}</tbody></table></div>' if t_rows else """<div class="empty"><div class="empty-icon">&#128203;</div><div class="empty-title">タスクログ未記録</div><div class="empty-desc">knowledge/logs/system/tasks/ にログが蓄積されると表示されます。</div></div>"""

    errors_html = ""
    if el:
        for e in el[-5:]:
            errors_html += f'<div class="issue-item"><span class="issue-id">{e.get("timestamp",e.get("date","?"))}</span>{e.get("error",e.get("message","?"))}</div>'
    else:
        errors_html = '<div class="empty"><div class="empty-icon">&#10003;</div><div class="empty-title">エラーなし</div></div>'

    return f"""
<div class="page" id="page-i-system">
  <div class="page-head"><h2>システム管理</h2><p>タスク実行・エラー・ナレッジ更新の追跡</p></div>
  <div class="page-body">
    <div class="sec"><div class="sec-head"><h3>タスク実行ログ</h3></div>{tasks_html}</div>
    <div class="sec"><div class="sec-head"><h3>エラーログ</h3></div>{errors_html}</div>
    <div class="sec"><div class="sec-head"><h3>ナレッジ更新履歴</h3><span class="sec-tag">Git 連動</span></div>
      <div class="empty"><div class="empty-icon">&#128218;</div><div class="empty-title">将来実装</div><div class="empty-desc">git log -- knowledge/ から自動取得予定。</div></div>
    </div>
  </div>
</div>"""


# =========================================================================
# ページ群: X
# =========================================================================
def _pages_x(d) -> str:
    return (_pg_x_overview(d) + _pg_x_patterns(d) + _pg_x_content_type(d) +
            _pg_x_pillars(d) + _pg_x_timeslot(d) + _pg_x_images(d) +
            _pg_x_note_link(d) + _pg_x_cross(d) + _pg_x_improve(d) +
            _pg_x_posts(d))


def _pg_x_overview(d) -> str:
    return f"""
<div class="page" id="page-x-overview">
  <div class="page-head"><h2>X 概況</h2><p>{d["month"]} — 主要 KPI とハイライト</p></div>
  <div class="page-body">
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">投稿数</div><div class="kpi-val" style="color:var(--accent)">{d["total_posts"]}</div><div class="kpi-sub">当月</div></div>
      <div class="kpi"><div class="kpi-label">インプレッション</div><div class="kpi-val">{d["total_impressions"]:,}</div></div>
      <div class="kpi"><div class="kpi-label">エンゲージメント</div><div class="kpi-val">{d["total_engagements"]:,}</div></div>
      <div class="kpi"><div class="kpi-label">平均 ER</div><div class="kpi-val" style="color:var(--green)">{d["avg_engagement_rate"]}%</div></div>
      <div class="kpi"><div class="kpi-label">リプライ</div><div class="kpi-val" style="color:var(--blue)">{d["total_replies"]}</div></div>
      <div class="kpi"><div class="kpi-label">ブックマーク</div><div class="kpi-val">{d["total_bookmarks"]}</div></div>
      <div class="kpi"><div class="kpi-label">RT</div><div class="kpi-val">{d["total_retweets"]}</div></div>
      <div class="kpi"><div class="kpi-label">いいね</div><div class="kpi-val" style="color:var(--pink)">{d["total_likes"]}</div></div>
    </div>
    <div class="ch-grid">
      <div class="ch-box"><h4>パターン別スコア</h4><canvas id="c-xo-pattern"></canvas></div>
      <div class="ch-box"><h4>3本柱バランス</h4><canvas id="c-xo-pillar"></canvas></div>
    </div>
  </div>
</div>"""


def _pg_x_patterns(d) -> str:
    rows = ""
    for p in d["pattern_summary"]:
        rc = {"S":"bdg-s","A":"bdg-a","B":"bdg-b"}.get(p["rank"],"bdg-c")
        rows += f'<tr><td>{p["pattern"]}</td><td><span class="bdg {rc}">{p["rank"]}</span></td><td>{p["count"]}</td><td>{p["avg_score"]}</td></tr>'
    return f"""
<div class="page" id="page-x-patterns">
  <div class="page-head"><h2>パターン分析</h2><p>10パターンの効果比較</p></div>
  <div class="page-body">
    <div class="ch-box" style="margin-bottom:16px"><h4>パターン別スコア（棒: スコア / 線: 使用回数）</h4><canvas id="c-xp-bar"></canvas></div>
    <div class="sec"><div class="sec-head"><h3>パターン一覧</h3><span class="sec-tag">{len(d["pattern_summary"])}種</span></div>
      <div class="tw"><table><thead><tr><th>パターン</th><th>ランク</th><th>使用回数</th><th>平均スコア</th></tr></thead><tbody>{rows}</tbody></table></div>
    </div>
  </div>
</div>"""


def _pg_x_content_type(d) -> str:
    cts = d.get("content_type_summary", [])
    srcs = d.get("source_summary", [])

    ct_rows = ""
    for ct in cts:
        ct_rows += f'<tr><td>{ct["type"]}</td><td>{ct["label"]}</td><td>{ct["count"]}</td><td>{ct["avg_score"]}</td><td>{ct["avg_er"]}%</td><td>{ct["avg_imp"]:,.0f}</td></tr>'
    src_rows = ""
    for s in srcs:
        src_rows += f'<tr><td>{s["source"]}</td><td>{s["count"]}</td><td>{s["avg_score"]}</td><td>{s["avg_er"]}%</td></tr>'

    best_ct = max(cts, key=lambda c: c["avg_score"]) if cts else {"type": "-", "label": "-", "avg_score": 0}

    return f"""
<div class="page" id="page-x-content-type">
  <div class="page-head"><h2>コンテンツ種別</h2><p>C軸（記事の種類）とネタ元ごとのパフォーマンス</p></div>
  <div class="page-body">
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">C種別数</div><div class="kpi-val" style="color:var(--accent)">{len(cts)}</div></div>
      <div class="kpi"><div class="kpi-label">最高スコア</div><div class="kpi-val" style="color:var(--green)">{best_ct["type"]}</div><div class="kpi-sub">{best_ct["label"]} ({best_ct["avg_score"]})</div></div>
      <div class="kpi"><div class="kpi-label">ネタ元数</div><div class="kpi-val">{len(srcs)}</div></div>
    </div>
    <div class="ch-grid">
      <div class="ch-box"><h4>C種別スコア（棒: スコア / 線: 回数）</h4><canvas id="c-xct-bar"></canvas></div>
      <div class="ch-box"><h4>ネタ元別スコア</h4><canvas id="c-xsrc-bar"></canvas></div>
    </div>
    <div class="sec"><div class="sec-head"><h3>C種別一覧</h3><span class="sec-tag">{len(cts)}種</span></div>
      <div class="tw"><table><thead><tr><th>種別</th><th>名称</th><th>投稿数</th><th>平均スコア</th><th>平均ER</th><th>平均IMP</th></tr></thead><tbody>{ct_rows}</tbody></table></div>
    </div>
    <div class="sec"><div class="sec-head"><h3>ネタ元一覧</h3><span class="sec-tag">{len(srcs)}種</span></div>
      <div class="tw"><table><thead><tr><th>ネタ元</th><th>投稿数</th><th>平均スコア</th><th>平均ER</th></tr></thead><tbody>{src_rows}</tbody></table></div>
    </div>
  </div>
</div>"""


def _pg_x_note_link(d) -> str:
    nla = d.get("note_link_analysis", {})
    linked = nla.get("linked", {})
    unlinked = nla.get("unlinked", {})

    # note連動投稿一覧
    note_posts = [t for t in d.get("timeline", []) if t.get("note_linked") == "有"]
    np_rows = ""
    for t in note_posts:
        np_rows += f'<tr><td>{t["date"]}</td><td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{t["topic"]}</td><td>{t["impressions"]:,}</td><td>{t["profile_visits"]}</td><td>{t["link_clicks"]}</td><td>{t["engagement_rate"]}%</td></tr>'

    return f"""
<div class="page" id="page-x-note-link">
  <div class="page-head"><h2>note連動</h2><p>note記事と連動した投稿のパフォーマンス分析</p></div>
  <div class="page-body">
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">連動投稿数</div><div class="kpi-val" style="color:var(--accent)">{linked.get("count", 0)}</div></div>
      <div class="kpi"><div class="kpi-label">非連動投稿数</div><div class="kpi-val">{unlinked.get("count", 0)}</div></div>
      <div class="kpi"><div class="kpi-label">連動時 平均IMP</div><div class="kpi-val" style="color:var(--green)">{linked.get("avg_imp", 0):,.0f}</div></div>
      <div class="kpi"><div class="kpi-label">非連動 平均IMP</div><div class="kpi-val">{unlinked.get("avg_imp", 0):,.0f}</div></div>
    </div>
    <div class="ch-box" style="margin-bottom:16px"><h4>note連動 有無別パフォーマンス比較</h4><canvas id="c-xnl-bar"></canvas></div>
    <div class="sec"><div class="sec-head"><h3>note連動投稿一覧</h3><span class="sec-tag">{linked.get("count", 0)}件</span></div>
      <div class="tw"><table><thead><tr><th>日付</th><th>トピック</th><th>IMP</th><th>プロフ遷移</th><th>リンクClick</th><th>ER</th></tr></thead><tbody>{np_rows if np_rows else '<tr><td colspan="6" class="empty" style="padding:16px">連動投稿なし</td></tr>'}</tbody></table></div>
    </div>
    <div class="sec"><div class="sec-head"><h3>プロフィール遷移の比較</h3></div>
      <div class="kpi-row">
        <div class="kpi"><div class="kpi-label">連動時 プロフ遷移</div><div class="kpi-val" style="color:var(--blue)">{linked.get("avg_profile", 0)}</div></div>
        <div class="kpi"><div class="kpi-label">非連動 プロフ遷移</div><div class="kpi-val">{unlinked.get("avg_profile", 0)}</div></div>
        <div class="kpi"><div class="kpi-label">連動時 リンクClick</div><div class="kpi-val" style="color:var(--teal)">{linked.get("avg_link_clicks", 0)}</div></div>
        <div class="kpi"><div class="kpi-label">非連動 リンクClick</div><div class="kpi-val">{unlinked.get("avg_link_clicks", 0)}</div></div>
      </div>
    </div>
  </div>
</div>"""


def _pg_x_cross(d) -> str:
    """クロス分析: C種別×パターンの組み合わせ別パフォーマンス"""
    cross = d.get("cross_summary", [])
    cross_rows = ""
    for c in cross:
        ct_label = CONTENT_TYPE_NAMES.get(c["ct"], c["ct"])
        score_color = "var(--green)" if c["avg_score"] > 0.5 else "var(--red)" if c["avg_score"] < 0.2 else "var(--text)"
        cross_rows += (
            f'<tr><td>{c["ct"]}</td><td>{ct_label}</td><td>{c["pattern"]}</td>'
            f'<td>{c["count"]}</td><td style="color:{score_color};font-weight:600">{c["avg_score"]}</td>'
            f'<td>{c["avg_er"]}%</td><td>{c["avg_imp"]:,.0f}</td></tr>'
        )
    best = cross[0] if cross else {"combo": "-", "avg_score": 0}
    worst = cross[-1] if cross else {"combo": "-", "avg_score": 0}
    return f"""
<div class="page" id="page-x-cross">
  <div class="page-head"><h2>クロス分析</h2><p>C種別×パターンの組み合わせ別パフォーマンス — どの掛け算が効くか</p></div>
  <div class="page-body">
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">組み合わせ数</div><div class="kpi-val" style="color:var(--accent)">{len(cross)}</div></div>
      <div class="kpi"><div class="kpi-label">最強の組み合わせ</div><div class="kpi-val" style="color:var(--green);font-size:1rem">{best["combo"]}</div><div class="kpi-sub">スコア {best["avg_score"]}</div></div>
      <div class="kpi"><div class="kpi-label">改善候補</div><div class="kpi-val" style="color:var(--red);font-size:1rem">{worst["combo"]}</div><div class="kpi-sub">スコア {worst["avg_score"]}</div></div>
    </div>
    <div class="ch-box" style="margin-bottom:16px"><h4>組み合わせ別スコア</h4><canvas id="c-xcross-bar"></canvas></div>
    <div class="sec"><div class="sec-head"><h3>C種別×パターン一覧</h3><span class="sec-tag">{len(cross)}組</span></div>
      <div class="tw"><table><thead><tr><th>C種別</th><th>名称</th><th>パターン</th><th>投稿数</th><th>平均スコア</th><th>平均ER</th><th>平均IMP</th></tr></thead><tbody>{cross_rows}</tbody></table></div>
    </div>
  </div>
</div>"""


def _pg_x_improve(d) -> str:
    """改善分析: ワースト投稿 + 偏り警告 + 未使用C種別"""
    worst = d.get("worst_posts", [])
    unused = d.get("unused_cts", [])
    warnings = d.get("skew_warnings", [])

    worst_rows = ""
    for w in worst:
        er_color = "var(--green)" if w["er"] > 5 else "var(--red)" if w["er"] == 0 else "var(--text)"
        worst_rows += (
            f'<tr><td>{w["date"]}</td><td>{w["content_type"]}</td><td>{w["pattern"]}</td>'
            f'<td style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{w["topic"]}</td>'
            f'<td>{w["impressions"]:,}</td><td style="color:{er_color}">{w["er"]}%</td>'
            f'<td style="font-weight:600">{w["score"]}</td><td>{w["time_slot"]}</td><td>{w["image_type"]}</td></tr>'
        )

    # 警告カード
    warn_html = ""
    for w in warnings:
        warn_html += f'<div style="background:rgba(184,90,58,0.08);border:1px solid var(--red);border-radius:6px;padding:10px 14px;margin-bottom:8px;font-size:0.82rem;color:var(--red)">⚠ {w}</div>'

    # 未使用C種別
    unused_html = ""
    if unused:
        tags = " ".join(f'<span style="display:inline-block;background:var(--surface2);border:1px solid var(--border);border-radius:4px;padding:3px 10px;margin:3px;font-size:0.78rem">{u["type"]}（{u["label"]}）</span>' for u in unused)
        unused_html = f"""
    <div class="sec"><div class="sec-head"><h3>未使用のC種別</h3><span class="sec-tag">{len(unused)}種</span></div>
      <p style="color:var(--muted);font-size:0.78rem;margin-bottom:8px">まだ試していないコンテンツ種別。新しい切り口として検討できます。</p>
      <div>{tags}</div>
    </div>"""

    return f"""
<div class="page" id="page-x-improve">
  <div class="page-head"><h2>改善分析</h2><p>低パフォーマンス投稿の特定と次のアクション</p></div>
  <div class="page-body">
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">ER=0%の投稿</div><div class="kpi-val" style="color:var(--red)">{sum(1 for w in worst if w["er"] == 0)}</div><div class="kpi-sub">改善余地あり</div></div>
      <div class="kpi"><div class="kpi-label">未使用C種別</div><div class="kpi-val" style="color:var(--blue)">{len(unused)}</div><div class="kpi-sub">/ {len(CONTENT_TYPE_NAMES)}種中</div></div>
      <div class="kpi"><div class="kpi-label">偏り警告</div><div class="kpi-val" style="color:{"var(--red)" if warnings else "var(--green)"}">{len(warnings)}</div></div>
    </div>
    {"".join(warn_html) if warn_html else ""}
    <div class="sec"><div class="sec-head"><h3>スコア下位5投稿</h3><span class="sec-tag">要分析</span></div>
      <div class="tw"><table><thead><tr><th>日付</th><th>C種別</th><th>パターン</th><th>トピック</th><th>IMP</th><th>ER</th><th>スコア</th><th>枠</th><th>画像</th></tr></thead><tbody>{worst_rows}</tbody></table></div>
    </div>
    {unused_html}
  </div>
</div>"""


def _pg_x_pillars(d) -> str:
    rows = ""
    for pil, info in d["pillar_dist"].items():
        sc = d["pillar_perf"].get(pil, 0)
        rows += f'<tr><td>{pil}</td><td>{info["count"]}</td><td>{info["ratio"]:.0%}</td><td>{sc}</td></tr>'
    return f"""
<div class="page" id="page-x-pillars">
  <div class="page-head"><h2>柱バランス</h2><p>3本柱の投稿数比率とスコア</p></div>
  <div class="page-body">
    <div class="ch-grid">
      <div class="ch-box"><h4>3本柱バランス（投稿数）</h4><canvas id="c-xpil-donut"></canvas></div>
      <div class="ch-box"><h4>柱別平均スコア</h4><canvas id="c-xpil-bar"></canvas></div>
    </div>
    <div class="ch-box" style="margin-bottom:16px"><h4>難易度分布</h4><canvas id="c-xpil-diff"></canvas></div>
    <div class="sec"><div class="sec-head"><h3>柱別データ</h3></div>
      <div class="tw"><table><thead><tr><th>柱</th><th>投稿数</th><th>比率</th><th>平均スコア</th></tr></thead><tbody>{rows}</tbody></table></div>
    </div>
  </div>
</div>"""


def _pg_x_timeslot(d) -> str:
    tss = d.get("time_slot_summary", [])
    ts_rows = ""
    for ts in tss:
        ts_rows += f'<tr><td>{ts["slot"]}</td><td>{ts["count"]}</td><td>{ts["avg_er"]}%</td><td>{ts["avg_imp"]:,.0f}</td></tr>'
    return f"""
<div class="page" id="page-x-timeslot">
  <div class="page-head"><h2>曜日×時間帯</h2><p>エンゲージメントのタイミング分析</p></div>
  <div class="page-body">
    <div class="sec"><div class="sec-head"><h3>ヒートマップ</h3><span class="sec-tag">ER%</span></div><div id="x-heatmap"></div></div>
    <div class="ch-box" style="margin-bottom:16px"><h4>投稿枠別 平均ER</h4><canvas id="c-xts-slot"></canvas></div>
    <div class="sec"><div class="sec-head"><h3>投稿枠別データ</h3><span class="sec-tag">{len(tss)}枠</span></div>
      <div class="tw"><table><thead><tr><th>枠</th><th>投稿数</th><th>平均ER</th><th>平均IMP</th></tr></thead><tbody>{ts_rows}</tbody></table></div>
    </div>
  </div>
</div>"""


def _pg_x_images(d) -> str:
    rows = ""
    for t in d["image_type_summary"]:
        rows += f'<tr><td>{t["type"]}</td><td>{t["count"]}</td><td>{t["avg_score"]}</td></tr>'
    issue_html = ""
    for i in d["issues"]:
        issue_html += f'<div class="issue-item"><span class="issue-id">{i["post_id"]}</span>{i["issue"]}</div>'
    if not issue_html:
        issue_html = '<div class="empty"><div class="empty-icon">&#10003;</div><div class="empty-title">問題なし</div></div>'
    return f"""
<div class="page" id="page-x-images">
  <div class="page-head"><h2>画像分析</h2><p>画像タイプ別スコアと品質問題</p></div>
  <div class="page-body">
    <div class="ch-box" style="margin-bottom:16px"><h4>画像タイプ別スコア</h4><canvas id="c-ximg-bar"></canvas></div>
    <div class="sec"><div class="sec-head"><h3>画像タイプ一覧</h3><span class="sec-tag">{len(d["image_type_summary"])}種</span></div>
      <div class="tw"><table><thead><tr><th>タイプ</th><th>使用回数</th><th>平均スコア</th></tr></thead><tbody>{rows}</tbody></table></div>
    </div>
    <div class="sec"><div class="sec-head"><h3>画像品質問題</h3><span class="sec-tag">{len(d["issues"])}件</span></div>{issue_html}</div>
  </div>
</div>"""


def _pg_x_posts(d) -> str:
    return f"""
<div class="page" id="page-x-posts">
  <div class="page-head"><h2>投稿一覧</h2><p>全投稿のソート可能テーブル</p></div>
  <div class="page-body">
    <div class="sec">
      <div class="tw">
        <table id="x-tbl">
          <thead><tr>
            <th data-sort="str">日付<span class="sa"></span></th>
            <th data-sort="str">枠<span class="sa"></span></th>
            <th data-sort="str">C種別<span class="sa"></span></th>
            <th data-sort="str">パターン<span class="sa"></span></th>
            <th data-sort="str">ランク<span class="sa"></span></th>
            <th data-sort="str">柱<span class="sa"></span></th>
            <th data-sort="str">トピック<span class="sa"></span></th>
            <th data-sort="str">状態<span class="sa"></span></th>
            <th data-sort="num">IMP<span class="sa"></span></th>
            <th data-sort="num">ER%<span class="sa"></span></th>
            <th data-sort="num">いいね<span class="sa"></span></th>
            <th data-sort="num">リプ<span class="sa"></span></th>
            <th data-sort="num">RT<span class="sa"></span></th>
            <th data-sort="num">BM<span class="sa"></span></th>
            <th data-sort="num">スコア<span class="sa"></span></th>
            <th data-sort="str">画像<span class="sa"></span></th>
            <th data-sort="str">ネタ元<span class="sa"></span></th>
            <th data-sort="num">文字数<span class="sa"></span></th>
            <th data-sort="str">note<span class="sa"></span></th>
            <th data-sort="str">本文<span class="sa"></span></th>
          </tr></thead>
          <tbody id="x-tbl-body"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>"""


# =========================================================================
# ページ群: note
# =========================================================================
def _pages_note(d, comp_data) -> str:
    note_accts = comp_data.get("note_accounts", [])
    note_ts = comp_data.get("note_type_summary", [])

    # note競合の種別KPI
    note_kpi = ""
    type_colors = {"benchmark": "var(--green)", "ng": "var(--red)", "news": "var(--blue)"}
    for t in note_ts:
        c = type_colors.get(t["type"], "var(--muted)")
        note_kpi += f'<div class="kpi"><div class="kpi-label">競合 {t["type"]}</div><div class="kpi-val" style="color:{c}">{t["count"]}</div></div>'

    # 競合テーブル
    bench_rows = ""
    for a in note_accts:
        if a["type"] == "benchmark":
            bench_rows += f'<tr><td>{a["handle"]}</td><td>{a["name"]}</td><td>{a["category"]}</td><td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{a["fork_direction"]}">{a["fork_direction"]}</td><td>{a.get("cpt_score","")}</td></tr>'
    ng_rows = ""
    for a in note_accts:
        if a["type"] == "ng":
            ng_rows += f'<tr><td>{a["handle"]}</td><td>{a["name"]}</td><td>{a["category"]}</td><td style="color:var(--red)">{a["ng_reason"]}</td></tr>'
    news_rows = ""
    for a in note_accts:
        if a["type"] == "news":
            news_rows += f'<tr><td>{a["handle"]}</td><td>{a["name"]}</td><td>{a["category"]}</td></tr>'

    return f"""
<div class="page" id="page-n-overview">
  <div class="page-head"><h2>note 概況</h2><p>{d["month"]} — 記事パフォーマンス + 競合概況</p></div>
  <div class="page-body">
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">記事数</div><div class="kpi-val" style="color:var(--accent)">{d["total_posts"]}</div></div>
      <div class="kpi"><div class="kpi-label">PV</div><div class="kpi-val">{d["total_pv"]:,}</div></div>
      <div class="kpi"><div class="kpi-label">スキ</div><div class="kpi-val" style="color:var(--green)">{d["total_likes"]}</div></div>
      <div class="kpi"><div class="kpi-label">コメント</div><div class="kpi-val" style="color:var(--blue)">{d["total_comments"]}</div></div>
      {note_kpi}
    </div>
    <div class="empty"><div class="empty-icon">&#128221;</div><div class="empty-title">自記事データ未収集</div>
    <div class="empty-desc">note_analytics.py 構築後にデータを収集してください。</div></div>
  </div>
</div>
<div class="page" id="page-n-articles">
  <div class="page-head"><h2>競合アカウント</h2><p>note 競合 {len(note_accts)}件の追跡状況</p></div>
  <div class="page-body">
    <div class="sec"><div class="sec-head"><h3>ベンチマーク</h3><span class="sec-tag">{sum(1 for a in note_accts if a["type"]=="benchmark")}件</span></div>
      <div class="tw"><table><thead><tr><th>アカウント</th><th>名前</th><th>カテゴリ</th><th>フォーク方向</th><th>C×P×T</th></tr></thead><tbody>{bench_rows if bench_rows else '<tr><td colspan="5" class="empty" style="padding:12px">データなし</td></tr>'}</tbody></table></div>
    </div>
    <div class="sec"><div class="sec-head"><h3>NG分析</h3><span class="sec-tag">{sum(1 for a in note_accts if a["type"]=="ng")}件</span></div>
      <div class="tw"><table><thead><tr><th>アカウント</th><th>名前</th><th>カテゴリ</th><th>NG理由</th></tr></thead><tbody>{ng_rows if ng_rows else '<tr><td colspan="4" class="empty" style="padding:12px">データなし</td></tr>'}</tbody></table></div>
    </div>
    {f'<div class="sec"><div class="sec-head"><h3>ニュース</h3><span class="sec-tag">{sum(1 for a in note_accts if a["type"]=="news")}件</span></div><div class="tw"><table><thead><tr><th>アカウント</th><th>名前</th><th>カテゴリ</th></tr></thead><tbody>{news_rows}</tbody></table></div></div>' if news_rows else ''}
  </div>
</div>
<div class="page" id="page-n-categories">
  <div class="page-head"><h2>カテゴリ別</h2><p>記事カテゴリごとの PV 比較</p></div>
  <div class="page-body"><div class="empty"><div class="empty-icon">&#9830;</div><div class="empty-title">データ蓄積後に表示</div></div></div>
</div>
<div class="page" id="page-n-trends">
  <div class="page-head"><h2>PV 推移</h2><p>記事公開後の PV 変化</p></div>
  <div class="page-body"><div class="empty"><div class="empty-icon">&#9650;</div><div class="empty-title">データ蓄積後に表示</div></div></div>
</div>"""


# =========================================================================
# JavaScript
# =========================================================================
def _js_all(x_data, algo_data, trend_data, config) -> str:
    # JSON
    pil_l = _j(list(x_data["pillar_dist"].keys())) if x_data["pillar_dist"] else "[]"
    pil_c = _j([v["count"] for v in x_data["pillar_dist"].values()]) if x_data["pillar_dist"] else "[]"
    pil_s = _j(list(x_data["pillar_perf"].values())) if x_data["pillar_perf"] else "[]"
    pat_l = _j([p["pattern"] for p in x_data["pattern_summary"]])
    pat_s = _j([p["avg_score"] for p in x_data["pattern_summary"]])
    pat_c = _j([p["count"] for p in x_data["pattern_summary"]])
    dif_l = _j(list(x_data["diff_count"].keys()))
    dif_v = _j(list(x_data["diff_count"].values()))
    img_l = _j([t["type"] for t in x_data["image_type_summary"]])
    img_s = _j([t["avg_score"] for t in x_data["image_type_summary"]])
    img_c = _j([t["count"] for t in x_data["image_type_summary"]])
    hm = _j(x_data["heatmap_data"])
    tl = _j(x_data["timeline"])
    rank_map = _j({p: PATTERN_CONFIG[p]["rank"] for p in PATTERN_CONFIG})
    wk_w = _j([w["week"] for w in algo_data.get("weekly_ers", [])])
    wk_e = _j([w["avg_er"] for w in algo_data.get("weekly_ers", [])])
    sp = _j([x_data["total_posts"], 0])
    sr = _j([x_data["total_impressions"], 0])

    # 新規: C種別 / ネタ元 / 枠別 / note連動
    ct_l = _j([c["label"] for c in x_data.get("content_type_summary", [])])
    ct_s = _j([c["avg_score"] for c in x_data.get("content_type_summary", [])])
    ct_c = _j([c["count"] for c in x_data.get("content_type_summary", [])])
    src_l = _j([s["source"] for s in x_data.get("source_summary", [])])
    src_s = _j([s["avg_score"] for s in x_data.get("source_summary", [])])
    src_c = _j([s["count"] for s in x_data.get("source_summary", [])])
    ts_l = _j([t["slot"] for t in x_data.get("time_slot_summary", [])])
    ts_er = _j([t["avg_er"] for t in x_data.get("time_slot_summary", [])])
    ts_c = _j([t["count"] for t in x_data.get("time_slot_summary", [])])
    # クロス分析
    cross = x_data.get("cross_summary", [])
    cross_l = _j([c["combo"] for c in cross])
    cross_s = _j([c["avg_score"] for c in cross])
    cross_c = _j([c["count"] for c in cross])

    nla = x_data.get("note_link_analysis", {})
    nl_labels = _j(["連動あり", "連動なし"])
    nl_imp = _j([nla.get("linked", {}).get("avg_imp", 0), nla.get("unlinked", {}).get("avg_imp", 0)])
    nl_prof = _j([nla.get("linked", {}).get("avg_profile", 0), nla.get("unlinked", {}).get("avg_profile", 0)])
    nl_link = _j([nla.get("linked", {}).get("avg_link_clicks", 0), nla.get("unlinked", {}).get("avg_link_clicks", 0)])

    return f"""
document.getElementById('gen-time').textContent = new Date().toLocaleString('ja-JP');

// ===== ナビゲーション =====
const platforms = ['integrated','x','note'];
const sidebarFirstPage = {{ integrated:'i-summary', x:'x-overview', note:'n-overview' }};

document.querySelectorAll('.header-tab').forEach(btn => {{
  btn.addEventListener('click', () => {{
    const pf = btn.dataset.platform;
    // ヘッダータブ
    document.querySelectorAll('.header-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    // サイドバー切替
    document.querySelectorAll('.sidebar').forEach(s => s.classList.remove('active'));
    document.getElementById('sidebar-' + pf).classList.add('active');
    // 最初のページ表示
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + sidebarFirstPage[pf]).classList.add('active');
    // サイドバーのアクティブ
    document.getElementById('sidebar-' + pf).querySelectorAll('.side-item').forEach((s,i) => {{
      s.classList.toggle('active', i === 0);
    }});
  }});
}});

document.querySelectorAll('.side-item').forEach(item => {{
  item.addEventListener('click', () => {{
    const sidebar = item.closest('.sidebar');
    sidebar.querySelectorAll('.side-item').forEach(s => s.classList.remove('active'));
    item.classList.add('active');
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + item.dataset.page).classList.add('active');
  }});
}});

// ===== チャート共通 =====
const C = ['#6366f1','#22c55e','#eab308','#ef4444','#3b82f6','#ec4899','#14b8a6','#f97316','#8b5cf6','#06b6d4'];
const bO = {{ responsive:true, maintainAspectRatio:true, plugins:{{ legend:{{ labels:{{ color:'#7c809a', font:{{ size:10 }} }} }} }} }};
const nL = {{ responsive:true, maintainAspectRatio:true, plugins:{{ legend:{{ display:false }} }} }};
const scX = {{ ticks:{{ color:'#7c809a', font:{{ size:9 }} }}, grid:{{ display:false }} }};
const scY = {{ ticks:{{ color:'#7c809a' }}, grid:{{ color:'#252839' }} }};
const scY2 = {{ position:'right', ticks:{{ color:'#22c55e' }}, grid:{{ display:false }} }};

function mkBar(id, labels, datasets, opts) {{
  const el = document.getElementById(id);
  if (el && labels.length) new Chart(el, {{ type:'bar', data:{{ labels, datasets }}, options:opts }});
}}
function mkDonut(id, labels, data, colors) {{
  const el = document.getElementById(id);
  if (el && labels.length) new Chart(el, {{ type:'doughnut', data:{{ labels, datasets:[{{ data, backgroundColor:colors, borderWidth:0 }}] }}, options:{{ ...bO, cutout:'55%' }} }});
}}

// ===== サマリー =====
mkBar('c-sum-posts', ['X','note'], [{{ label:'投稿数', data:{sp}, backgroundColor:['#1da1f2cc','#2dcc70cc'], borderRadius:6 }}], {{ ...nL, scales:{{ x:scX, y:scY }} }});
mkBar('c-sum-reach', ['X','note'], [{{ label:'リーチ', data:{sr}, backgroundColor:['#1da1f2cc','#2dcc70cc'], borderRadius:6 }}], {{ ...nL, scales:{{ x:scX, y:scY }} }});

// ===== X 概況 =====
mkBar('c-xo-pattern', {pat_l}, [
  {{ label:'スコア', data:{pat_s}, backgroundColor:'#6366f1cc', borderRadius:4, yAxisID:'y' }},
  {{ label:'回数', data:{pat_c}, backgroundColor:'#22c55e44', borderRadius:4, yAxisID:'y1' }}
], {{ ...bO, scales:{{ x:{{ ...scX, ticks:{{ ...scX.ticks, maxRotation:45 }} }}, y:scY, y1:scY2 }} }});
mkDonut('c-xo-pillar', {pil_l}, {pil_c}, C.slice(0,3));

// ===== X パターン =====
mkBar('c-xp-bar', {pat_l}, [
  {{ label:'スコア', data:{pat_s}, backgroundColor:'#6366f1cc', borderRadius:4, yAxisID:'y' }},
  {{ label:'回数', data:{pat_c}, backgroundColor:'#22c55e44', borderRadius:4, yAxisID:'y1' }}
], {{ ...bO, scales:{{ x:{{ ...scX, ticks:{{ ...scX.ticks, maxRotation:45 }} }}, y:{{ ...scY, title:{{ display:true, text:'スコア', color:'#7c809a' }} }}, y1:{{ ...scY2, title:{{ display:true, text:'回数', color:'#22c55e' }} }} }} }});

// ===== X 柱 =====
mkDonut('c-xpil-donut', {pil_l}, {pil_c}, C.slice(0,3));
mkBar('c-xpil-bar', {pil_l}, [{{ label:'平均スコア', data:{pil_s}, backgroundColor:C.slice(0,3).map(c=>c+'cc'), borderRadius:6 }}], {{ ...nL, indexAxis:'y', scales:{{ x:scY, y:{{ ...scX, ticks:{{ ...scX.ticks, font:{{ size:9 }} }} }} }} }});
mkDonut('c-xpil-diff', {dif_l}, {dif_v}, ['#22c55e','#eab308','#ef4444']);

// ===== X 画像 =====
mkBar('c-ximg-bar', {img_l}, [
  {{ label:'スコア', data:{img_s}, backgroundColor:'#ec4899cc', borderRadius:4, yAxisID:'y' }},
  {{ label:'回数', data:{img_c}, backgroundColor:'#14b8a644', borderRadius:4, yAxisID:'y1' }}
], {{ ...bO, scales:{{ x:scX, y:scY, y1:{{ ...scY2, ticks:{{ color:'#14b8a6' }} }} }} }});

// ===== X コンテンツ種別 =====
mkBar('c-xct-bar', {ct_l}, [
  {{ label:'スコア', data:{ct_s}, backgroundColor:'#8b5cf6cc', borderRadius:4, yAxisID:'y' }},
  {{ label:'回数', data:{ct_c}, backgroundColor:'#06b6d444', borderRadius:4, yAxisID:'y1' }}
], {{ ...bO, scales:{{ x:{{ ...scX, ticks:{{ ...scX.ticks, maxRotation:45 }} }}, y:scY, y1:scY2 }} }});
mkBar('c-xsrc-bar', {src_l}, [
  {{ label:'スコア', data:{src_s}, backgroundColor:'#f97316cc', borderRadius:4, yAxisID:'y' }},
  {{ label:'回数', data:{src_c}, backgroundColor:'#22c55e44', borderRadius:4, yAxisID:'y1' }}
], {{ ...bO, scales:{{ x:{{ ...scX, ticks:{{ ...scX.ticks, maxRotation:45 }} }}, y:scY, y1:scY2 }} }});

// ===== X 投稿枠別 =====
mkBar('c-xts-slot', {ts_l}, [
  {{ label:'平均ER%', data:{ts_er}, backgroundColor:C.slice(0,{ts_l}.length).map(c=>c+'cc'), borderRadius:6 }}
], {{ ...nL, scales:{{ x:scX, y:{{ ...scY, title:{{ display:true, text:'ER%', color:'#7c809a' }} }} }} }});

// ===== X note連動 =====
mkBar('c-xnl-bar', {nl_labels}, [
  {{ label:'平均IMP', data:{nl_imp}, backgroundColor:['#22c55ecc','#7c809acc'], borderRadius:6, yAxisID:'y' }},
  {{ label:'プロフ遷移', data:{nl_prof}, backgroundColor:['#3b82f6cc','#7c809a88'], borderRadius:6, yAxisID:'y1' }}
], {{ ...bO, scales:{{ x:scX, y:scY, y1:scY2 }} }});

// ===== X クロス分析 =====
mkBar('c-xcross-bar', {cross_l}, [
  {{ label:'スコア', data:{cross_s}, backgroundColor:C.concat(C).slice(0,{cross_l}.length).map(c=>c+'cc'), borderRadius:4, yAxisID:'y' }},
  {{ label:'回数', data:{cross_c}, backgroundColor:C.concat(C).slice(0,{cross_l}.length).map(c=>c+'33'), borderRadius:4, yAxisID:'y1' }}
], {{ ...bO, scales:{{ x:{{ ...scX, ticks:{{ ...scX.ticks, maxRotation:60 }} }}, y:scY, y1:scY2 }} }});

// ===== アルゴリズム ER 推移 =====
(function() {{
  const el = document.getElementById('c-algo-er');
  const weeks = {wk_w};
  const ers = {wk_e};
  if (el && weeks.length) {{
    new Chart(el, {{
      type:'line',
      data:{{ labels:weeks, datasets:[{{ label:'平均 ER%', data:ers, borderColor:'#6366f1', backgroundColor:'rgba(99,102,241,0.08)', fill:true, tension:0.3, pointRadius:4, pointBackgroundColor:'#6366f1' }}] }},
      options:{{ ...bO, scales:{{ x:scX, y:{{ ...scY, title:{{ display:true, text:'ER%', color:'#7c809a' }} }} }} }}
    }});
  }}
}})();

// ===== X ヒートマップ =====
(function() {{
  const c = document.getElementById('x-heatmap');
  if (!c) return;
  const data = {hm};
  if (!data.length) {{ c.innerHTML = '<div class="empty"><div class="empty-desc">データなし</div></div>'; return; }}
  const days = ['月','火','水','木','金','土','日'];
  const g = {{}};
  data.forEach(d => {{ if(!g[d.day]) g[d.day]=[]; g[d.day].push(d); }});
  let h = '<table><thead><tr><th>曜日</th><th>時間帯</th><th>ER%</th><th>IMP</th><th>リプ</th></tr></thead><tbody>';
  days.forEach(day => {{
    if (!g[day]) return;
    g[day].forEach(d => {{
      const i = Math.min(d.er / 10, 1);
      const bg = `rgba(99,102,241,${{(i * 0.5 + 0.06).toFixed(2)}})`;
      h += `<tr><td style="font-weight:600">${{day}}</td><td>${{d.time}}</td><td style="background:${{bg}};border-radius:4px;text-align:center;font-weight:700">${{d.er}}%</td><td>${{d.imp.toLocaleString()}}</td><td>${{d.rep}}</td></tr>`;
    }});
  }});
  h += '</tbody></table>';
  c.innerHTML = h;
}})();

// ===== X 投稿テーブル =====
(function() {{
  const tbody = document.getElementById('x-tbl-body');
  if (!tbody) return;
  const data = {tl};
  const rm = {rank_map};
  data.forEach(t => {{
    const bc = t.status==='posted'?'bdg-posted':t.status==='scheduled'?'bdg-scheduled':'bdg-draft';
    const rk = rm[t.pattern]||'?';
    const rc = rk==='S'?'bdg-s':rk==='A'?'bdg-a':rk==='B'?'bdg-b':'bdg-c';
    const row = document.createElement('tr');
    row.innerHTML =
      `<td>${{t.date}}</td><td>${{t.time_slot||''}}</td><td>${{t.content_type||''}}</td><td>${{t.pattern}}</td>` +
      `<td><span class="bdg ${{rc}}">${{rk}}</span></td><td>${{t.pillar}}</td>` +
      `<td style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${{t.topic}}">${{t.topic}}</td>` +
      `<td><span class="bdg ${{bc}}">${{t.status}}</span></td>` +
      `<td>${{t.impressions.toLocaleString()}}</td><td>${{t.engagement_rate}}%</td>` +
      `<td>${{t.likes}}</td><td>${{t.replies}}</td><td>${{t.retweets}}</td><td>${{t.bookmarks}}</td>` +
      `<td style="font-weight:600">${{t.composite_score}}</td><td>${{t.image_type}}</td>` +
      `<td>${{t.source||''}}</td><td>${{t.char_count||0}}</td><td>${{t.note_linked||''}}</td>` +
      `<td style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:0.7rem" title="${{(t.post_text||'').replace(/"/g,'&quot;')}}">${{t.post_text||''}}</td>`;
    tbody.appendChild(row);
  }});
  if (!data.length) tbody.innerHTML = '<tr><td colspan="20" class="empty" style="padding:16px">投稿データなし</td></tr>';
}})();

// ===== テーブルソート =====
document.querySelectorAll('th[data-sort]').forEach(th => {{
  th.addEventListener('click', () => {{
    const tbl = th.closest('table'), tbody = tbl.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const idx = Array.from(th.parentNode.children).indexOf(th);
    const type = th.dataset.sort, asc = th.dataset.dir !== 'asc';
    th.dataset.dir = asc ? 'asc' : 'desc';
    th.parentNode.querySelectorAll('th').forEach(h => {{ if(h!==th) {{ h.dataset.dir=''; const s=h.querySelector('.sa'); if(s) s.textContent=''; }} }});
    const sa = th.querySelector('.sa'); if(sa) sa.textContent = asc ? ' ▲' : ' ▼';
    rows.sort((a,b) => {{
      let va = a.children[idx]?.textContent.trim()||'', vb = b.children[idx]?.textContent.trim()||'';
      if (type==='num') {{ va=parseFloat(va.replace(/[,%]/g,''))||0; vb=parseFloat(vb.replace(/[,%]/g,''))||0; }}
      return va<vb ? (asc?-1:1) : va>vb ? (asc?1:-1) : 0;
    }});
    rows.forEach(r => tbody.appendChild(r));
  }});
}});
"""


# =========================================================================
# メイン
# =========================================================================
def generate_dashboard(month=None, open_browser=False) -> Path:
    from system_logger import log_task

    month = month or datetime.now().strftime("%Y-%m")

    with log_task("dashboard-generate") as task:
        config = load_config()
        x_data = collect_x_data(month)
        note_data = collect_note_data(month)
        comp_data = collect_competitive_data(config)
        trend_data = collect_trend_data()
        algo_data = collect_algorithm_data(x_data)
        sys_data = collect_system_data()

        html = build_html(month, x_data, note_data, comp_data, trend_data, algo_data, sys_data, config)

        DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
        out = DASHBOARD_DIR / f"{month}.html"
        out.write_text(html, encoding="utf-8")
        print(f"ダッシュボード生成: {out}")

        task.note(f"X投稿{x_data['total_posts']}件, note記事{note_data['total_posts']}件")

    if open_browser:
        webbrowser.open(str(out))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="統合ダッシュボード生成")
    sub = parser.add_subparsers(dest="command")
    gen = sub.add_parser("generate", help="ダッシュボード生成")
    gen.add_argument("--month", help="対象月 (YYYY-MM)", default=None)
    gen.add_argument("--open", action="store_true", help="生成後にブラウザで開く")
    args = parser.parse_args()
    if args.command == "generate":
        generate_dashboard(args.month, args.open)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
