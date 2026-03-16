"""
note記事アナリティクス — SQLite管理CLI

使い方:
  # DB初期化（初回のみ）
  python scripts/note_analytics.py init

  # 記事登録
  python scripts/note_analytics.py add --article-id naad9e3279dfe --date 2026-03-16 \
      --title "Notion AIの中身は..." --content-type C3 --treatment 対比 \
      --chars 2500 --images 4 --thumb-style blackboard \
      --hashtags "#NotionAI #AI活用" --url "https://note.com/akatu_unison/n/naad9e3279dfe" \
      --draft "knowledge/drafts/note_notion-ai-claude.md"

  # メトリクス更新
  python scripts/note_analytics.py update --article-id naad9e3279dfe \
      --views 15 --likes 3 --comments 0

  # 記事詳細
  python scripts/note_analytics.py show --article-id naad9e3279dfe

  # レポート
  python scripts/note_analytics.py report                       # 全期間サマリ
  python scripts/note_analytics.py report --days 7              # 直近7日
  python scripts/note_analytics.py report --by content          # コンテンツタイプ別
  python scripts/note_analytics.py report --by treatment        # T軸別
  python scripts/note_analytics.py report --by thumbnail        # サムネスタイル別
  python scripts/note_analytics.py report --by day              # 曜日別
  python scripts/note_analytics.py report --ranking             # PV順ランキング
  python scripts/note_analytics.py report --monthly             # 月別サマリ
  python scripts/note_analytics.py report --monthly 2026-03     # 特定月の詳細
  python scripts/note_analytics.py report --yearly              # 年別サマリ
  python scripts/note_analytics.py report --yearly 2026         # 特定年の詳細

  # 一覧
  python scripts/note_analytics.py list                         # 全件
  python scripts/note_analytics.py list --days 7                # 直近7日

データ:
  knowledge/data/note_articles.db
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Windows UTF-8 output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "knowledge" / "data" / "note_articles.db"

DAY_MAP = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS articles (
    article_id      TEXT PRIMARY KEY,
    date            TEXT NOT NULL,
    day             TEXT NOT NULL,
    title           TEXT NOT NULL DEFAULT '',
    content_type    TEXT NOT NULL DEFAULT '',
    treatment       TEXT NOT NULL DEFAULT '',
    char_count      INTEGER NOT NULL DEFAULT 0,
    image_count     INTEGER NOT NULL DEFAULT 0,
    thumbnail_style TEXT NOT NULL DEFAULT '',
    hashtags        TEXT NOT NULL DEFAULT '',
    article_url     TEXT NOT NULL DEFAULT '',
    draft_file      TEXT NOT NULL DEFAULT '',
    views           INTEGER NOT NULL DEFAULT 0,
    likes           INTEGER NOT NULL DEFAULT 0,
    comments        INTEGER NOT NULL DEFAULT 0,
    measured_at     TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS rules (
    rule_id     TEXT PRIMARY KEY,
    category    TEXT NOT NULL,
    description TEXT NOT NULL,
    value       TEXT NOT NULL,
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 初期ルール（init時に投入）
DEFAULT_RULES = [
    ("max_publish_per_day", "publish", "1日あたりの最大公開記事数", "1"),
    ("metrics_update_window_days", "update", "メトリクス更新ウィンドウ（日数）", "7"),
]

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date);
CREATE INDEX IF NOT EXISTS idx_articles_content_type ON articles(content_type);
CREATE INDEX IF NOT EXISTS idx_articles_treatment ON articles(treatment);
CREATE INDEX IF NOT EXISTS idx_articles_thumbnail_style ON articles(thumbnail_style);
"""

# 既存DBへの列追加（ALTER TABLE）
# 新しいカラムを追加する場合はここに追記する
MIGRATIONS: list[str] = [
    # 例: "ALTER TABLE articles ADD COLUMN pillar TEXT NOT NULL DEFAULT ''",
]


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(CREATE_TABLE)
    # マイグレーション（既存テーブルに列追加）
    for sql in MIGRATIONS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # duplicate column = already migrated
    # インデックス作成（マイグレーション後）
    conn.executescript(CREATE_INDEX)
    # デフォルトルール投入
    for rule_id, category, desc, value in DEFAULT_RULES:
        conn.execute(
            "INSERT OR IGNORE INTO rules (rule_id, category, description, value) VALUES (?, ?, ?, ?)",
            (rule_id, category, desc, value),
        )
    conn.commit()


def get_rule(conn: sqlite3.Connection, rule_id: str) -> str | None:
    row = conn.execute(
        "SELECT value FROM rules WHERE rule_id = ? AND enabled = 1", (rule_id,)
    ).fetchone()
    return row["value"] if row else None


def check_publish_limit(conn: sqlite3.Connection, date: str) -> None:
    limit = get_rule(conn, "max_publish_per_day")
    if not limit:
        return
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM articles WHERE date = ?", (date,)
    ).fetchone()["cnt"]
    if count >= int(limit):
        print(f"⚠ WARNING: {date} already has {count} article(s) (limit: {limit}/day)")
        print("  Rule: max_publish_per_day. Use 'rules' command to change.")


def check_update_window(conn: sqlite3.Connection, article_id: str) -> None:
    window = get_rule(conn, "metrics_update_window_days")
    if not window:
        return
    row = conn.execute(
        "SELECT date, title FROM articles WHERE article_id = ?", (article_id,)
    ).fetchone()
    if not row:
        return
    pub_date = datetime.strptime(row["date"], "%Y-%m-%d")
    days_since = (datetime.now() - pub_date).days
    if days_since > int(window):
        print(f"⚠ WARNING: '{row['title']}' is {days_since} days old (window: {window} days)")
        print("  Metrics are past the update window. Consider using report --monthly for summary.")


# ── add ──────────────────────────────────────────────────────────────────

def add_article(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    day = args.day
    if not day and args.date:
        dt = datetime.strptime(args.date, "%Y-%m-%d")
        day = DAY_MAP[dt.weekday()]

    check_publish_limit(conn, args.date)

    conn.execute(
        """INSERT OR REPLACE INTO articles
           (article_id, date, day, title, content_type, treatment,
            char_count, image_count, thumbnail_style, hashtags,
            article_url, draft_file)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            args.article_id, args.date, day,
            args.title or "", args.content_type or "", args.treatment or "",
            args.chars or 0, args.images or 0, args.thumb_style or "",
            args.hashtags or "", args.url or "", args.draft or "",
        ),
    )
    conn.commit()
    print(f"Added: {args.article_id} ({args.date} {args.title})")


# ── update ───────────────────────────────────────────────────────────────

def update_metrics(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    check_update_window(conn, args.article_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute(
        """UPDATE articles SET
           views = ?, likes = ?, comments = ?, measured_at = ?
           WHERE article_id = ?""",
        (
            args.views or 0, args.likes or 0, args.comments or 0,
            now, args.article_id,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT title FROM articles WHERE article_id = ?", (args.article_id,)).fetchone()
    title = row["title"] if row else "?"
    print(f"Updated: {args.article_id} ({title}) views={args.views} likes={args.likes} comments={args.comments}")


# ── show ─────────────────────────────────────────────────────────────────

def show_article(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    r = conn.execute("SELECT * FROM articles WHERE article_id = ?", (args.article_id,)).fetchone()
    if not r:
        print(f"Article not found: {args.article_id}")
        return

    like_rate = (r["likes"] / r["views"] * 100) if r["views"] > 0 else 0.0

    print("=" * 60)
    print(f"  Article Detail: {r['title']}")
    print("=" * 60)
    print(f"  ID:             {r['article_id']}")
    print(f"  URL:            {r['article_url']}")
    print(f"  Date:           {r['date']} ({r['day']})")
    print("-" * 60)
    print(f"  Content Type:   {r['content_type']}")
    print(f"  Treatment:      {r['treatment']}")
    print(f"  Characters:     {r['char_count']}")
    print(f"  Images:         {r['image_count']}")
    print(f"  Thumbnail:      {r['thumbnail_style']}")
    print(f"  Hashtags:       {r['hashtags']}")
    if r["draft_file"]:
        print(f"  Draft File:     {r['draft_file']}")
    print("-" * 60)
    print(f"  Views:          {r['views']}")
    print(f"  Likes:          {r['likes']} ({like_rate:.1f}%)")
    print(f"  Comments:       {r['comments']}")
    print(f"  Measured At:    {r['measured_at']}")
    print("=" * 60)


# ── list ─────────────────────────────────────────────────────────────────

def list_articles(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    query = "SELECT * FROM articles"
    params: list[Any] = []
    if args.days:
        since = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        query += " WHERE date >= ?"
        params.append(since)
    query += " ORDER BY date DESC"

    rows = conn.execute(query, params).fetchall()
    if not rows:
        print("No articles found.")
        return

    print(f"{'ID':<18} {'Date':>10} {'Day':>2} {'Type':<6} {'Views':>5} {'Likes':>5} {'Title'}")
    print("-" * 90)
    for r in rows:
        print(
            f"{r['article_id']:<18} {r['date']:>10} {r['day']:>2} "
            f"{r['content_type']:<6} {r['views']:>5} {r['likes']:>5} {r['title']}"
        )
    print(f"\nTotal: {len(rows)} articles")


# ── report ───────────────────────────────────────────────────────────────

def report(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    where = ""
    params: list[Any] = []
    if args.days:
        since = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        where = "WHERE date >= ?"
        params.append(since)

    if args.ranking:
        _report_ranking(conn, where, params)
    elif args.monthly is not None:
        _report_monthly(conn, args.monthly)
    elif args.yearly is not None:
        _report_yearly(conn, args.yearly)
    elif args.by:
        _report_by(conn, args.by, where, params)
    else:
        _report_summary(conn, where, params)


def _report_summary(conn: sqlite3.Connection, where: str, params: list[Any]) -> None:
    row = conn.execute(
        f"""SELECT
            COUNT(*) as cnt,
            SUM(views) as total_views,
            AVG(views) as avg_views,
            SUM(likes) as total_likes,
            AVG(likes) as avg_likes,
            SUM(comments) as total_comments,
            AVG(char_count) as avg_chars,
            AVG(image_count) as avg_images,
            MIN(date) as first_date,
            MAX(date) as last_date,
            COUNT(DISTINCT date) as active_days
        FROM articles {where}""",
        params,
    ).fetchone()

    if not row or row["cnt"] == 0:
        print("No data.")
        return

    days = row["active_days"]
    articles_per_day = row["cnt"] / days if days > 0 else 0
    like_rate = row["total_likes"] / row["total_views"] * 100 if row["total_views"] > 0 else 0

    print("=" * 55)
    print(f"  note Analytics Summary ({row['first_date']} ~ {row['last_date']})")
    print("=" * 55)
    print(f"  Articles:       {row['cnt']} ({days} days, {articles_per_day:.1f}/day)")
    print(f"  Views:          {row['total_views']} (avg {row['avg_views']:.1f}/article)")
    print(f"  Likes:          {row['total_likes']} (avg {row['avg_likes']:.1f}/article)")
    print(f"  Comments:       {row['total_comments']}")
    print(f"  Like Rate:      {like_rate:.2f}%")
    print(f"  Avg Chars:      {row['avg_chars']:.0f}")
    print(f"  Avg Images:     {row['avg_images']:.1f}")
    print("=" * 55)

    # Top 3
    top3 = conn.execute(
        f"SELECT title, views, likes FROM articles {where} ORDER BY views DESC LIMIT 3",
        params,
    ).fetchall()
    if top3:
        print("\n  Top 3:")
        for i, t in enumerate(top3, 1):
            print(f"    {i}. {t['title']} (views={t['views']} likes={t['likes']})")


def _report_by(conn: sqlite3.Connection, by: str, where: str, params: list[Any]) -> None:
    col_map = {
        "content": "content_type",
        "treatment": "treatment",
        "thumbnail": "thumbnail_style",
        "day": "day",
    }
    col = col_map.get(by)
    if not col:
        print(f"Unknown grouping: {by}. Use: {', '.join(col_map.keys())}")
        return

    rows = conn.execute(
        f"""SELECT
            {col} as grp,
            COUNT(*) as cnt,
            ROUND(AVG(views), 1) as avg_views,
            ROUND(AVG(likes), 1) as avg_likes,
            SUM(views) as total_views,
            SUM(likes) as total_likes,
            SUM(comments) as total_comments,
            MAX(views) as max_views,
            ROUND(AVG(char_count), 0) as avg_chars
        FROM articles {where}
        GROUP BY {col}
        ORDER BY avg_views DESC""",
        params,
    ).fetchall()

    if not rows:
        print("No data.")
        return

    label = by.upper()
    print(f"\n{'':>2} {label:<20} {'N':>3} {'AvgPV':>6} {'AvgLk':>6} {'MaxPV':>6} {'TotPV':>6} {'TotLk':>6} {'Cmt':>4} {'AvgCh':>6}")
    print("-" * 85)
    for r in rows:
        grp = r["grp"] if r["grp"] else "(empty)"
        print(
            f"  {grp:<20} {r['cnt']:>3} {r['avg_views']:>6.1f} {r['avg_likes']:>6.1f} "
            f"{r['max_views']:>6} {r['total_views']:>6} {r['total_likes']:>6} "
            f"{r['total_comments']:>4} {r['avg_chars']:>6.0f}"
        )


def _report_ranking(conn: sqlite3.Connection, where: str, params: list[Any]) -> None:
    rows = conn.execute(
        f"""SELECT article_id, date, day, title, content_type, treatment,
                   thumbnail_style, char_count, views, likes, comments
            FROM articles {where}
            ORDER BY views DESC""",
        params,
    ).fetchall()

    if not rows:
        print("No data.")
        return

    print(f"\n{'#':>3} {'Date':>10} {'Day':>2} {'Type':<6} {'T軸':<10} {'PV':>4} {'Lk':>3} {'Cmt':>3} {'Chars':>5} {'Title'}")
    print("-" * 95)
    for i, r in enumerate(rows, 1):
        print(
            f"{i:>3} {r['date']:>10} {r['day']:>2} "
            f"{r['content_type']:<6} {r['treatment']:<10} "
            f"{r['views']:>4} {r['likes']:>3} {r['comments']:>3} "
            f"{r['char_count']:>5} {r['title']}"
        )


def _report_monthly(conn: sqlite3.Connection, month: str) -> None:
    if month:
        # 特定月の詳細
        rows = conn.execute(
            """SELECT
                date, COUNT(*) as cnt,
                SUM(views) as pv, SUM(likes) as lk, SUM(comments) as cmt
            FROM articles
            WHERE substr(date, 1, 7) = ?
            GROUP BY date
            ORDER BY date""",
            (month,),
        ).fetchall()

        if not rows:
            print(f"No data for {month}.")
            return

        totals = conn.execute(
            """SELECT COUNT(*) as cnt, SUM(views) as pv, SUM(likes) as lk,
                      AVG(views) as avg_pv, AVG(likes) as avg_lk,
                      SUM(comments) as cmt, AVG(char_count) as avg_chars
            FROM articles WHERE substr(date, 1, 7) = ?""",
            (month,),
        ).fetchone()

        like_rate = totals["lk"] / totals["pv"] * 100 if totals["pv"] > 0 else 0

        print(f"\n{'=' * 55}")
        print(f"  Monthly Detail: {month}")
        print(f"{'=' * 55}")
        print(f"  Articles: {totals['cnt']} | PV: {totals['pv']} (avg {totals['avg_pv']:.1f}) | Likes: {totals['lk']} (avg {totals['avg_lk']:.1f})")
        print(f"  Comments: {totals['cmt']} | Like Rate: {like_rate:.2f}% | Avg Chars: {totals['avg_chars']:.0f}")

        print(f"\n  {'Date':>10} {'Day':>3} {'N':>3} {'PV':>5} {'Likes':>5} {'Cmt':>4}")
        print(f"  {'-' * 40}")
        for r in rows:
            dt = datetime.strptime(r["date"], "%Y-%m-%d")
            day = DAY_MAP[dt.weekday()]
            print(
                f"  {r['date']:>10} {day:>3} {r['cnt']:>3} "
                f"{r['pv']:>5} {r['lk']:>5} {r['cmt']:>4}"
            )

        # コンテンツタイプ別内訳
        types = conn.execute(
            """SELECT content_type, COUNT(*) as cnt, ROUND(AVG(views),1) as avg_pv,
                      SUM(likes) as lk
            FROM articles WHERE substr(date, 1, 7) = ?
            GROUP BY content_type ORDER BY avg_pv DESC""",
            (month,),
        ).fetchall()
        if types:
            print(f"\n  Content Type Breakdown:")
            for t in types:
                nm = t["content_type"] or "(empty)"
                print(f"    {nm:<12} x{t['cnt']} avg_pv={t['avg_pv']} likes={t['lk']}")

        # T軸別内訳
        treatments = conn.execute(
            """SELECT treatment, COUNT(*) as cnt, ROUND(AVG(views),1) as avg_pv
            FROM articles WHERE substr(date, 1, 7) = ?
            GROUP BY treatment ORDER BY avg_pv DESC""",
            (month,),
        ).fetchall()
        if treatments:
            print(f"\n  Treatment Breakdown:")
            for t in treatments:
                nm = t["treatment"] or "(empty)"
                print(f"    {nm:<12} x{t['cnt']} avg_pv={t['avg_pv']}")

    else:
        # 月別サマリ一覧
        rows = conn.execute(
            """SELECT
                substr(date, 1, 7) as month,
                COUNT(*) as cnt,
                SUM(views) as total_pv,
                ROUND(AVG(views), 1) as avg_pv,
                SUM(likes) as total_lk,
                ROUND(AVG(likes), 1) as avg_lk,
                SUM(comments) as cmt,
                COUNT(DISTINCT date) as active_days
            FROM articles
            GROUP BY substr(date, 1, 7)
            ORDER BY month""",
        ).fetchall()

        if not rows:
            print("No data.")
            return

        print(f"\n  {'Month':>7} {'N':>4} {'Days':>4} {'N/Day':>5} {'TotPV':>6} {'AvgPV':>6} {'TotLk':>6} {'AvgLk':>6} {'Cmt':>4} {'Rate':>6}")
        print(f"  {'-' * 70}")
        for r in rows:
            n_per_day = r["cnt"] / r["active_days"] if r["active_days"] > 0 else 0
            rate = r["total_lk"] / r["total_pv"] * 100 if r["total_pv"] > 0 else 0
            print(
                f"  {r['month']:>7} {r['cnt']:>4} {r['active_days']:>4} {n_per_day:>5.1f} "
                f"{r['total_pv']:>6} {r['avg_pv']:>6.1f} {r['total_lk']:>6} {r['avg_lk']:>6.1f} "
                f"{r['cmt']:>4} {rate:>5.1f}%"
            )


def _report_yearly(conn: sqlite3.Connection, year: str) -> None:
    if year:
        # 特定年の月別内訳
        rows = conn.execute(
            """SELECT
                substr(date, 1, 7) as month,
                COUNT(*) as cnt,
                SUM(views) as total_pv,
                ROUND(AVG(views), 1) as avg_pv,
                SUM(likes) as total_lk,
                ROUND(AVG(likes), 1) as avg_lk,
                SUM(comments) as cmt,
                COUNT(DISTINCT date) as active_days
            FROM articles
            WHERE substr(date, 1, 4) = ?
            GROUP BY substr(date, 1, 7)
            ORDER BY month""",
            (year,),
        ).fetchall()

        if not rows:
            print(f"No data for {year}.")
            return

        totals = conn.execute(
            """SELECT COUNT(*) as cnt, SUM(views) as pv, SUM(likes) as lk,
                      AVG(views) as avg_pv, AVG(likes) as avg_lk,
                      SUM(comments) as cmt, COUNT(DISTINCT date) as days
            FROM articles WHERE substr(date, 1, 4) = ?""",
            (year,),
        ).fetchone()

        rate = totals["lk"] / totals["pv"] * 100 if totals["pv"] > 0 else 0

        print(f"\n{'=' * 55}")
        print(f"  Yearly Detail: {year}")
        print(f"{'=' * 55}")
        print(f"  Articles: {totals['cnt']} | Days: {totals['days']} | PV: {totals['pv']} (avg {totals['avg_pv']:.1f})")
        print(f"  Likes: {totals['lk']} (avg {totals['avg_lk']:.1f}) | Rate: {rate:.2f}%")
        print(f"  Comments: {totals['cmt']}")

        print(f"\n  {'Month':>7} {'N':>4} {'Days':>4} {'TotPV':>6} {'AvgPV':>6} {'TotLk':>6} {'AvgLk':>6} {'Cmt':>4} {'Rate':>6}")
        print(f"  {'-' * 60}")
        for r in rows:
            r_rate = r["total_lk"] / r["total_pv"] * 100 if r["total_pv"] > 0 else 0
            print(
                f"  {r['month']:>7} {r['cnt']:>4} {r['active_days']:>4} "
                f"{r['total_pv']:>6} {r['avg_pv']:>6.1f} {r['total_lk']:>6} {r['avg_lk']:>6.1f} "
                f"{r['cmt']:>4} {r_rate:>5.1f}%"
            )

        # 年間コンテンツタイプランキング
        types = conn.execute(
            """SELECT content_type, COUNT(*) as cnt, ROUND(AVG(views),1) as avg_pv,
                      SUM(likes) as lk, SUM(views) as tot_pv
            FROM articles WHERE substr(date, 1, 4) = ?
            GROUP BY content_type ORDER BY avg_pv DESC""",
            (year,),
        ).fetchall()
        if types:
            print(f"\n  Content Type Ranking ({year}):")
            for t in types:
                nm = t["content_type"] or "(empty)"
                print(f"    {nm:<12} x{t['cnt']} avg_pv={t['avg_pv']} tot_pv={t['tot_pv']} likes={t['lk']}")

    else:
        # 年別サマリ一覧
        rows = conn.execute(
            """SELECT
                substr(date, 1, 4) as year,
                COUNT(*) as cnt,
                SUM(views) as total_pv,
                ROUND(AVG(views), 1) as avg_pv,
                SUM(likes) as total_lk,
                ROUND(AVG(likes), 1) as avg_lk,
                SUM(comments) as cmt,
                COUNT(DISTINCT date) as active_days,
                COUNT(DISTINCT substr(date, 1, 7)) as active_months
            FROM articles
            GROUP BY substr(date, 1, 4)
            ORDER BY year""",
        ).fetchall()

        if not rows:
            print("No data.")
            return

        print(f"\n  {'Year':>4} {'N':>5} {'Months':>6} {'Days':>5} {'TotPV':>7} {'AvgPV':>6} {'TotLk':>6} {'AvgLk':>6} {'Cmt':>4} {'Rate':>6}")
        print(f"  {'-' * 70}")
        for r in rows:
            rate = r["total_lk"] / r["total_pv"] * 100 if r["total_pv"] > 0 else 0
            print(
                f"  {r['year']:>4} {r['cnt']:>5} {r['active_months']:>6} {r['active_days']:>5} "
                f"{r['total_pv']:>7} {r['avg_pv']:>6.1f} {r['total_lk']:>6} {r['avg_lk']:>6.1f} "
                f"{r['cmt']:>4} {rate:>5.1f}%"
            )


# ── rules ────────────────────────────────────────────────────────────────

def manage_rules(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    if args.set:
        parts = args.set.split("=", 1)
        if len(parts) != 2:
            print("Format: --set rule_id=value")
            return
        rule_id, value = parts
        row = conn.execute("SELECT * FROM rules WHERE rule_id = ?", (rule_id,)).fetchone()
        if not row:
            print(f"Rule not found: {rule_id}")
            return
        conn.execute("UPDATE rules SET value = ? WHERE rule_id = ?", (value, rule_id))
        conn.commit()
        print(f"Updated: {rule_id} = {value}")
    elif args.toggle:
        row = conn.execute("SELECT enabled FROM rules WHERE rule_id = ?", (args.toggle,)).fetchone()
        if not row:
            print(f"Rule not found: {args.toggle}")
            return
        new_val = 0 if row["enabled"] else 1
        conn.execute("UPDATE rules SET enabled = ? WHERE rule_id = ?", (new_val, args.toggle))
        conn.commit()
        print(f"{'Enabled' if new_val else 'Disabled'}: {args.toggle}")
    else:
        rows = conn.execute("SELECT * FROM rules ORDER BY category, rule_id").fetchall()
        if not rows:
            print("No rules defined.")
            return
        print(f"\n  {'ID':<30} {'Cat':<10} {'Value':>6} {'On':>3} Description")
        print(f"  {'-' * 80}")
        for r in rows:
            on = "✓" if r["enabled"] else "✗"
            print(f"  {r['rule_id']:<30} {r['category']:<10} {r['value']:>6} {on:>3} {r['description']}")


# ── stock ────────────────────────────────────────────────────────────────

DRAFTS_DIR = ROOT / "knowledge" / "drafts"

STATUS_ORDER = {"校正済み": 0, "検証済み": 1, "下書き": 2, "投稿済み": 3}


def _parse_draft_status(path: Path) -> str:
    """下書きファイルからステータスを読み取る。"""
    try:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("- **ステータス**:"):
                raw = line.split(":", 1)[1].strip()
                # 括弧付き補足を除去: "下書き（Codexレビュー反映済み・エディタ未同期）" → "下書き"
                for s in STATUS_ORDER:
                    if raw.startswith(s):
                        return s
                return raw
    except Exception:
        pass
    return "不明"


def stock_check(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    target = args.days if args.days else 4

    # 公開済み article_id を取得（下書きの投稿済み判定用）
    published_drafts: set[str] = set()
    for row in conn.execute("SELECT draft_file FROM articles WHERE article_url != ''").fetchall():
        if row["draft_file"]:
            published_drafts.add(row["draft_file"])

    drafts: list[dict[str, str]] = []
    for f in sorted(DRAFTS_DIR.glob("note_*.md")):
        rel = f"knowledge/drafts/{f.name}"
        status = _parse_draft_status(f)
        # 公開済みの下書きを投稿済みに補正
        if rel in published_drafts and status != "投稿済み":
            status = "投稿済み"
        drafts.append({"file": f.name, "status": status})

    # ステータス別集計
    counts: dict[str, int] = {}
    for d in drafts:
        counts[d["status"]] = counts.get(d["status"], 0) + 1

    ready = counts.get("校正済み", 0)
    verified = counts.get("検証済み", 0)
    draft_count = counts.get("下書き", 0)
    posted = counts.get("投稿済み", 0)
    shortage = max(0, target - ready)

    print("=" * 55)
    print(f"  note Draft Stock (target: {target} days)")
    print("=" * 55)
    print(f"  校正済み（公開可能）:  {ready} {'✅' if ready >= target else '⚠️'}")
    print(f"  検証済み（校正待ち）:  {verified}")
    print(f"  下書き（検証待ち）:    {draft_count}")
    print(f"  投稿済み:              {posted}")
    print("-" * 55)
    print(f"  ストック充足率:        {ready}/{target} ({ready * 100 // target if target > 0 else 0}%)")
    if shortage > 0:
        print(f"  不足:                  {shortage}本 → 作成が必要")
    else:
        print(f"  状態:                  充足 ✅")
    print("=" * 55)

    # 個別ファイル一覧
    if drafts:
        print(f"\n  {'File':<45} {'Status'}")
        print(f"  {'-' * 60}")
        for d in sorted(drafts, key=lambda x: STATUS_ORDER.get(x["status"], 9)):
            mark = "✅" if d["status"] == "校正済み" else "📝" if d["status"] in ("下書き", "検証済み") else "📤"
            print(f"  {d['file']:<45} {mark} {d['status']}")


# ── CLI ──────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="note Analytics CLI")
    sub = parser.add_subparsers(dest="command")

    # init
    sub.add_parser("init", help="Initialize database")

    # add
    p_add = sub.add_parser("add", help="Add an article")
    p_add.add_argument("--article-id", required=True)
    p_add.add_argument("--date", required=True)
    p_add.add_argument("--day", default="")
    p_add.add_argument("--title", default="")
    p_add.add_argument("--content-type", default="")
    p_add.add_argument("--treatment", default="")
    p_add.add_argument("--chars", type=int, default=0)
    p_add.add_argument("--images", type=int, default=0)
    p_add.add_argument("--thumb-style", default="")
    p_add.add_argument("--hashtags", default="")
    p_add.add_argument("--url", default="")
    p_add.add_argument("--draft", default="")

    # update
    p_upd = sub.add_parser("update", help="Update metrics")
    p_upd.add_argument("--article-id", required=True)
    p_upd.add_argument("--views", type=int, default=0)
    p_upd.add_argument("--likes", type=int, default=0)
    p_upd.add_argument("--comments", type=int, default=0)

    # show
    p_show = sub.add_parser("show", help="Show article detail")
    p_show.add_argument("--article-id", required=True)

    # list
    p_list = sub.add_parser("list", help="List articles")
    p_list.add_argument("--days", type=int, default=0)

    # report
    p_rep = sub.add_parser("report", help="Generate report")
    p_rep.add_argument("--days", type=int, default=0)
    p_rep.add_argument("--by", choices=["content", "treatment", "thumbnail", "day"])
    p_rep.add_argument("--ranking", action="store_true")
    p_rep.add_argument("--monthly", nargs="?", const="", default=None,
                       help="Monthly summary (optionally specify YYYY-MM)")
    p_rep.add_argument("--yearly", nargs="?", const="", default=None,
                       help="Yearly summary (optionally specify YYYY)")

    # stock
    p_stock = sub.add_parser("stock", help="Check draft stock status")
    p_stock.add_argument("--days", type=int, default=4,
                         help="Target stock days (default: 4)")

    # rules
    p_rules = sub.add_parser("rules", help="Manage rules")
    p_rules.add_argument("--set", default="", help="Set rule value (rule_id=value)")
    p_rules.add_argument("--toggle", default="", help="Toggle rule enabled/disabled")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    conn = get_conn()
    init_db(conn)

    commands = {
        "init": lambda c, a: print("DB ready."),
        "add": add_article,
        "update": update_metrics,
        "show": show_article,
        "list": list_articles,
        "report": report,
        "stock": stock_check,
        "rules": manage_rules,
    }

    try:
        commands[args.command](conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
