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

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "platforms.yaml"
DASHBOARD_DIR = ROOT / "knowledge" / "logs" / "dashboard"

from x_report import (
    PATTERN_CONFIG,
    PILLAR_NAMES,
    POSTS_DIR,
    WEEKLY_DIR,
    MONTHLY_DIR,
    calc_composite_scores,
    calc_volume_score,
    calc_quality_score,
    load_posts,
    load_monthly,
    _count_pillars,
)


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


# =========================================================================
# データ収集
# =========================================================================
def collect_x_data(month: str) -> dict:
    posts = load_posts(POSTS_DIR, year_month=month)
    all_posts = load_posts(POSTS_DIR)

    if posts:
        composites = calc_composite_scores(posts)
        for p, cs in zip(posts, composites):
            p.setdefault("scores", {})
            p["scores"]["volume_score"] = round(calc_volume_score(p["metrics"]), 1)
            p["scores"]["quality_score"] = round(calc_quality_score(p["metrics"]), 2)
            p["scores"]["composite_score"] = round(cs, 4)
    else:
        composites = []

    total_imp = sum(p["metrics"].get("impressions", 0) for p in posts)
    total_eng = sum(p["metrics"].get("engagements", 0) for p in posts)
    total_rep = sum(p["metrics"].get("replies", 0) for p in posts)
    total_bkm = sum(p["metrics"].get("bookmarks", 0) for p in posts)
    total_rt = sum(p["metrics"].get("retweets", 0) for p in posts)
    total_likes = sum(p["metrics"].get("likes", 0) for p in posts)
    avg_er = statistics.mean([p["metrics"].get("engagement_rate", 0) for p in posts]) if posts else 0.0

    pattern_data: dict[str, list[float]] = {}
    for p in posts:
        pat = p.get("pattern", "unknown")
        pattern_data.setdefault(pat, []).append(p.get("scores", {}).get("composite_score", 0))
    pattern_summary = [
        {"pattern": pat, "count": len(sc), "avg_score": round(statistics.mean(sc), 4),
         "rank": PATTERN_CONFIG.get(pat, {}).get("rank", "?")}
        for pat, sc in sorted(pattern_data.items())
    ] if pattern_data else []

    pillar_dist = _count_pillars(posts) if posts else {}
    pillar_scores: dict[str, list[float]] = {}
    for p in posts:
        pil = p.get("pillar", "不明")
        pillar_scores.setdefault(pil, []).append(p.get("scores", {}).get("composite_score", 0))
    pillar_perf = {pil: round(statistics.mean(scs), 4) if scs else 0.0 for pil, scs in pillar_scores.items()}

    diff_count: dict[str, int] = {"初心者": 0, "中級": 0, "上級": 0}
    for p in posts:
        d = p.get("difficulty", PATTERN_CONFIG.get(p.get("pattern", ""), {}).get("difficulty", "中級"))
        diff_count[d] = diff_count.get(d, 0) + 1

    heatmap_data = [{"day": p.get("day", "?"), "time": p.get("time", "?"),
                     "er": p["metrics"].get("engagement_rate", 0),
                     "imp": p["metrics"].get("impressions", 0),
                     "rep": p["metrics"].get("replies", 0)} for p in posts]

    image_type_data: dict[str, list[float]] = {}
    for p in posts:
        itype = p.get("image_type", "none")
        image_type_data.setdefault(itype, []).append(p.get("scores", {}).get("composite_score", 0))
    image_type_summary = [
        {"type": itype, "count": len(sc), "avg_score": round(statistics.mean(sc), 4)}
        for itype, sc in sorted(image_type_data.items())
    ] if image_type_data else []

    issues = [{"post_id": p.get("post_id", "?"), "issue": p.get("image_issues", "")}
              for p in all_posts if p.get("image_issues")]

    timeline = [
        {"date": str(p.get("date", "")), "day": p.get("day", "?"), "pattern": p.get("pattern", "?"),
         "pillar": p.get("pillar", "?"), "status": p.get("status", "?"), "topic": p.get("topic", ""),
         "impressions": p.get("metrics", {}).get("impressions", 0),
         "engagement_rate": p.get("metrics", {}).get("engagement_rate", 0),
         "likes": p.get("metrics", {}).get("likes", 0), "replies": p.get("metrics", {}).get("replies", 0),
         "retweets": p.get("metrics", {}).get("retweets", 0), "bookmarks": p.get("metrics", {}).get("bookmarks", 0),
         "composite_score": p.get("scores", {}).get("composite_score", 0),
         "image_type": p.get("image_type", ""), "image_issues": p.get("image_issues", "")}
        for p in all_posts
    ]

    weekly_reports = []
    if WEEKLY_DIR.exists():
        for f in sorted(WEEKLY_DIR.glob("*.yaml")):
            with open(f, encoding="utf-8") as fh:
                wr = yaml.safe_load(fh)
                if wr:
                    weekly_reports.append(wr)

    return dict(
        month=month, total_posts=len(posts), total_all_posts=len(all_posts),
        total_impressions=total_imp, total_engagements=total_eng, total_replies=total_rep,
        total_bookmarks=total_bkm, total_retweets=total_rt, total_likes=total_likes,
        avg_engagement_rate=round(avg_er, 2), pattern_summary=pattern_summary,
        pillar_dist=pillar_dist, pillar_perf=pillar_perf, diff_count=diff_count,
        heatmap_data=heatmap_data, image_type_summary=image_type_summary,
        issues=issues, timeline=timeline, weekly_reports=weekly_reports,
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
    rd = ROOT / "knowledge" / "logs" / "x" / "research"
    comp, bench = [], []
    for sub, lst in [("competitor", comp), ("benchmark", bench)]:
        if (rd / sub).exists():
            for f in sorted((rd / sub).glob("*.yaml")):
                with open(f, encoding="utf-8") as fh:
                    d = yaml.safe_load(fh)
                    if d: lst.append(d)
    accts = config.get("platforms", {}).get("x", {}).get("competitive", {}).get("accounts", [])
    return {"accounts": accts if isinstance(accts, list) else [], "competitor_reports": comp, "benchmark_reports": bench}


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
    tenant_name = tenants.get("default", {}).get("name", "Delvework")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Delvework Dashboard — {month}</title>
<script src="{cdn}"></script>
<style>{_css()}</style>
</head>
<body>

{_header(month, tenant_name, tenants)}

<div class="layout">
  {_sidebar_integrated(trend_data, algo_data, sys_data)}
  {_sidebar_x(x_data)}
  {_sidebar_note()}

  <main class="content">
    {_pages_integrated(month, x_data, note_data, comp_data, trend_data, algo_data, sys_data)}
    {_pages_x(x_data)}
    {_pages_note(note_data)}
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
  --bg: #08090d; --bg2: #0d0f15; --surface: #12141c; --surface2: #181b26;
  --surface3: #1e2130; --border: #252839; --border2: #333658;
  --text: #eaeaf0; --text2: #c8c8d0; --muted: #7c809a;
  --accent: #6366f1; --accent2: #818cf8; --accent-bg: rgba(99,102,241,0.08);
  --green: #22c55e; --yellow: #eab308; --red: #ef4444; --blue: #3b82f6;
  --pink: #ec4899; --teal: #14b8a6; --orange: #f97316; --purple: #8b5cf6; --cyan: #06b6d4;
  --header-h: 52px; --sidebar-w: 220px;
}
* { margin:0; padding:0; box-sizing:border-box; }
html,body { height:100%; overflow:hidden; }
body { background:var(--bg); color:var(--text); font-family:'Segoe UI','Noto Sans JP',system-ui,sans-serif; font-size:13px; }

/* ===== ヘッダー ===== */
.header {
  height:var(--header-h); background:var(--surface); border-bottom:1px solid var(--border);
  display:flex; align-items:center; padding:0 20px; position:fixed; top:0; left:0; right:0; z-index:200;
}
.header-brand { font-weight:800; font-size:1rem; margin-right:32px; letter-spacing:-0.02em; color:var(--accent2); }
.header-tabs { display:flex; gap:2px; }
.header-tab {
  background:none; border:none; color:var(--muted); font-size:0.8rem; font-weight:500;
  padding:6px 16px; cursor:pointer; border-radius:6px; transition:all 0.15s;
}
.header-tab:hover { background:var(--surface2); color:var(--text2); }
.header-tab.active { background:var(--accent-bg); color:var(--accent2); font-weight:700; }
.header-right { margin-left:auto; display:flex; align-items:center; gap:12px; }
.account-select {
  background:var(--surface2); border:1px solid var(--border); color:var(--text2);
  padding:5px 12px; border-radius:6px; font-size:0.78rem; cursor:pointer; outline:none;
}
.account-select:focus { border-color:var(--accent); }
.header-meta { color:var(--muted); font-size:0.72rem; }

/* ===== レイアウト ===== */
.layout { display:flex; margin-top:var(--header-h); height:calc(100vh - var(--header-h)); }

/* ===== サイドバー ===== */
.sidebar {
  width:var(--sidebar-w); background:var(--surface); border-right:1px solid var(--border);
  overflow-y:auto; flex-shrink:0; display:none; /* JS で active を付与 */
}
.sidebar.active { display:flex; flex-direction:column; }
.sidebar-section { padding:16px 0 8px; }
.sidebar-label { color:var(--muted); font-size:0.65rem; text-transform:uppercase; letter-spacing:0.1em; padding:0 16px 6px; font-weight:700; }
.side-item {
  display:flex; align-items:center; gap:8px; padding:7px 16px; cursor:pointer;
  color:var(--text2); font-size:0.8rem; transition:all 0.12s; border-left:3px solid transparent;
}
.side-item:hover { background:var(--surface2); color:var(--text); }
.side-item.active { background:var(--accent-bg); color:var(--accent2); border-left-color:var(--accent); font-weight:600; }
.side-icon { font-size:0.85rem; width:16px; text-align:center; flex-shrink:0; opacity:0.7; }
.side-badge { margin-left:auto; background:var(--accent); color:#fff; font-size:0.6rem; padding:1px 6px; border-radius:8px; font-weight:700; }

.sidebar-footer { margin-top:auto; padding:12px 16px; border-top:1px solid var(--border); }
.sidebar-footer span { color:var(--muted); font-size:0.68rem; line-height:1.6; }

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
tr:hover td { background:rgba(99,102,241,0.03); }

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
  <div class="header-brand">Delvework</div>
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
    <div class="side-item" data-page="x-pillars"><span class="side-icon">&#9878;</span>柱バランス</div>
    <div class="side-item" data-page="x-timeslot"><span class="side-icon">&#9200;</span>曜日×時間帯</div>
    <div class="side-item" data-page="x-images"><span class="side-icon">&#9635;</span>画像分析{f'<span class="side-badge">{issues}</span>' if issues else ''}</div>
  </div>
  <div class="sidebar-section">
    <div class="sidebar-label">データ</div>
    <div class="side-item" data-page="x-posts"><span class="side-icon">&#9776;</span>投稿一覧</div>
  </div>
  <div class="sidebar-footer"><span>X（旧Twitter）<br>投稿パフォーマンス分析</span></div>
</aside>"""


def _sidebar_note() -> str:
    return """
<aside class="sidebar" id="sidebar-note">
  <div class="sidebar-section">
    <div class="sidebar-label">分析</div>
    <div class="side-item active" data-page="n-overview"><span class="side-icon">&#9632;</span>概況</div>
    <div class="side-item" data-page="n-articles"><span class="side-icon">&#9776;</span>記事一覧</div>
    <div class="side-item" data-page="n-categories"><span class="side-icon">&#9830;</span>カテゴリ別</div>
    <div class="side-item" data-page="n-trends"><span class="side-icon">&#9650;</span>PV推移</div>
  </div>
  <div class="sidebar-footer"><span>note<br>記事パフォーマンス分析</span></div>
</aside>"""


# =========================================================================
# ページ群: 統合
# =========================================================================
def _pages_integrated(month, x_data, note_data, comp_data, trend_data, algo_data, sys_data) -> str:
    return (_pg_i_summary(month, x_data, note_data) +
            _pg_i_competitive(comp_data) +
            _pg_i_trend(trend_data) +
            _pg_i_algorithm(algo_data) +
            _pg_i_system(sys_data))


def _pg_i_summary(month, x, n) -> str:
    total_p = x["total_posts"] + n["total_posts"]
    total_r = x["total_impressions"] + n["total_pv"]
    posted = sum(1 for t in x["timeline"] if t["status"] == "posted")
    sched = sum(1 for t in x["timeline"] if t["status"] == "scheduled")
    return f"""
<div class="page active" id="page-i-summary">
  <div class="page-head"><h2>サマリー</h2><p>{month} — 全プラットフォーム横断のパフォーマンス概況</p></div>
  <div class="page-body">
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">総投稿数</div><div class="kpi-val" style="color:var(--accent)">{total_p}</div></div>
      <div class="kpi"><div class="kpi-label">総リーチ</div><div class="kpi-val">{total_r:,}</div></div>
      <div class="kpi"><div class="kpi-label">投稿済</div><div class="kpi-val" style="color:var(--green)">{posted}</div></div>
      <div class="kpi"><div class="kpi-label">予約</div><div class="kpi-val" style="color:var(--yellow)">{sched}</div></div>
    </div>
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
    comp = cd.get("competitor_reports", [])
    bench = cd.get("benchmark_reports", [])
    has_data = bool(comp or bench)

    cards = ""
    for r in comp[-5:]:
        cards += f'<div class="item-card"><div class="item-title">{r.get("query", r.get("title","競合分析"))}</div><div class="item-meta"><span class="item-tag">期間: {r.get("period","?")}</span></div></div>'
    for b in bench[-3:]:
        cards += f'<div class="item-card"><div class="item-title">{b.get("query", b.get("title","ベンチマーク"))}</div><div class="item-meta"><span class="item-tag">期間: {b.get("period","?")}</span></div></div>'

    if not has_data:
        cards = """<div class="empty"><div class="empty-icon">&#9733;</div><div class="empty-title">競合データ未収集</div>
<div class="empty-desc">X Search を使った競合分析が利用可能です。</div>
<div class="empty-cmd">python scripts/x_search.py competitor --period 14d</div><br>
<div class="empty-cmd">python scripts/x_search.py benchmark --period 30d</div></div>"""

    return f"""
<div class="page" id="page-i-competitive">
  <div class="page-head"><h2>競合分析</h2><p>競合アカウントの追跡・ベンチマーク比較</p></div>
  <div class="page-body">
    <div class="sec"><div class="sec-head"><h3>競合 / ベンチマークレポート</h3><span class="sec-tag">{len(comp)+len(bench)}件</span></div>{cards}</div>
    <div class="sec"><div class="sec-head"><h3>設定状況</h3></div>
      <div class="item-meta" style="padding:8px">追跡アカウント: {len(cd.get("accounts",[]))}件 — config/platforms.yaml の competitive.accounts で管理</div>
    </div>
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
    return _pg_x_overview(d) + _pg_x_patterns(d) + _pg_x_pillars(d) + _pg_x_timeslot(d) + _pg_x_images(d) + _pg_x_posts(d)


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
    return f"""
<div class="page" id="page-x-timeslot">
  <div class="page-head"><h2>曜日×時間帯</h2><p>エンゲージメントのタイミング分析</p></div>
  <div class="page-body">
    <div class="sec"><div class="sec-head"><h3>ヒートマップ</h3><span class="sec-tag">ER%</span></div><div id="x-heatmap"></div></div>
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
            <th data-sort="str">曜日<span class="sa"></span></th>
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
def _pages_note(d) -> str:
    return f"""
<div class="page" id="page-n-overview">
  <div class="page-head"><h2>note 概況</h2><p>{d["month"]} — 記事パフォーマンス</p></div>
  <div class="page-body">
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">記事数</div><div class="kpi-val" style="color:var(--accent)">{d["total_posts"]}</div></div>
      <div class="kpi"><div class="kpi-label">PV</div><div class="kpi-val">{d["total_pv"]:,}</div></div>
      <div class="kpi"><div class="kpi-label">スキ</div><div class="kpi-val" style="color:var(--green)">{d["total_likes"]}</div></div>
      <div class="kpi"><div class="kpi-label">コメント</div><div class="kpi-val" style="color:var(--blue)">{d["total_comments"]}</div></div>
    </div>
    <div class="empty"><div class="empty-icon">&#128221;</div><div class="empty-title">記事データ未収集</div>
    <div class="empty-desc">note-dashboard-report タスクを実行してデータを収集してください。</div></div>
  </div>
</div>
<div class="page" id="page-n-articles">
  <div class="page-head"><h2>記事一覧</h2><p>全記事の PV・スキ・コメント</p></div>
  <div class="page-body"><div class="empty"><div class="empty-icon">&#9776;</div><div class="empty-title">データ蓄積後に表示</div></div></div>
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
      `<td>${{t.date}}</td><td>${{t.day}}</td><td>${{t.pattern}}</td>` +
      `<td><span class="bdg ${{rc}}">${{rk}}</span></td><td>${{t.pillar}}</td>` +
      `<td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${{t.topic}}">${{t.topic}}</td>` +
      `<td><span class="bdg ${{bc}}">${{t.status}}</span></td>` +
      `<td>${{t.impressions.toLocaleString()}}</td><td>${{t.engagement_rate}}%</td>` +
      `<td>${{t.likes}}</td><td>${{t.replies}}</td><td>${{t.retweets}}</td><td>${{t.bookmarks}}</td>` +
      `<td style="font-weight:600">${{t.composite_score}}</td><td>${{t.image_type}}</td>`;
    tbody.appendChild(row);
  }});
  if (!data.length) tbody.innerHTML = '<tr><td colspan="15" class="empty" style="padding:16px">投稿データなし</td></tr>';
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
