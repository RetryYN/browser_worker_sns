"""
X投稿アナリティクス — SQLite管理CLI

使い方:
  # DB初期化（初回のみ）
  python scripts/x_analytics.py init

  # 投稿登録
  python scripts/x_analytics.py add --post-id 2032... --date 2026-03-14 --time 12:00 \
      --pattern 図解 --pillar やってみた実演 --image-type diagram \
      --topic "AI4種使い分け" --text "本文..." --url "https://x.com/..." \
      --content-type C6 --source オリジナル --hashtags "#AI活用"

  # エンゲージメント更新
  python scripts/x_analytics.py update --post-id 2032... \
      --imp 78 --eng 6 --detail 3 --profile 1 --link 0 --likes 1

  # 投稿詳細
  python scripts/x_analytics.py show --post-id 2032...

  # レポート
  python scripts/x_analytics.py report                    # 全期間サマリ
  python scripts/x_analytics.py report --days 7           # 直近7日
  python scripts/x_analytics.py report --by pattern       # パターン別
  python scripts/x_analytics.py report --by time          # 時間帯別
  python scripts/x_analytics.py report --by image         # 画像種別
  python scripts/x_analytics.py report --by day           # 曜日別
  python scripts/x_analytics.py report --by slot          # 時間枠別（朝/昼/夕/夜）
  python scripts/x_analytics.py report --by source        # ソース別
  python scripts/x_analytics.py report --by content       # コンテンツタイプ別
  python scripts/x_analytics.py report --by pillar        # 柱別
  python scripts/x_analytics.py report --ranking          # imp順ランキング
  python scripts/x_analytics.py report --monthly          # 月別サマリ
  python scripts/x_analytics.py report --monthly 2026-03  # 特定月の詳細
  python scripts/x_analytics.py report --yearly           # 年別サマリ
  python scripts/x_analytics.py report --yearly 2026      # 特定年の詳細

  # 一覧
  python scripts/x_analytics.py list                      # 全件
  python scripts/x_analytics.py list --days 7             # 直近7日

  # YAML一括インポート
  python scripts/x_analytics.py import-yaml

  # ストック確認（今後N日分の空きスロット）
  python scripts/x_analytics.py stock                      # 3日分（デフォルト）
  python scripts/x_analytics.py stock --days 7             # 7日分

  # キュー同期（DBからx-content-queue.mdを再生成）
  python scripts/x_analytics.py queue-sync

  # リプライ管理
  python scripts/x_analytics.py reply-add --reply-id 2033... --date 2026-03-16 --time 23:00 \
      --target-user @star_02192018 --target-url "https://x.com/..." \
      --layer 就活生 --keyword "27卒 ChatGPT" --text "面接前に..." \
      --pattern 共感+実体験 --url "https://x.com/UaW6wnKW8c87193/status/..."
  python scripts/x_analytics.py reply-update --reply-id 2033... --imp 50 --likes 2 --reply-backs 1
  python scripts/x_analytics.py reply-list                 # 全件
  python scripts/x_analytics.py reply-list --days 7        # 直近7日
  python scripts/x_analytics.py reply-report               # サマリ
  python scripts/x_analytics.py reply-report --by layer    # 層別
  python scripts/x_analytics.py reply-report --by keyword  # キーワード別
  python scripts/x_analytics.py reply-report --by pattern  # パターン別
  python scripts/x_analytics.py reply-report --ranking     # imp順

  # 改善レポート（全チャネル横断）
  python scripts/x_analytics.py improve                    # 戦略改善レポート生成

データ:
  knowledge/data/x_posts.db
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

import yaml

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "knowledge" / "data" / "x_posts.db"
POSTS_DIR = ROOT / "knowledge" / "logs" / "x" / "posts"

DAY_MAP = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}

# 時間→枠マッピング
SLOT_MAP = {
    "07": "朝", "08": "朝", "09": "朝",
    "10": "昼", "11": "昼", "12": "昼", "13": "昼", "14": "昼", "15": "昼",
    "16": "夕", "17": "夕", "18": "夕", "19": "夕",
    "20": "夜", "21": "夜", "22": "夜", "23": "夜", "00": "夜", "01": "夜",
    "02": "夜", "03": "夜", "04": "夜", "05": "夜", "06": "夜",
}


def time_to_slot(t: str) -> str:
    hh = t.split(":")[0].zfill(2)
    return SLOT_MAP.get(hh, "不明")


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS posts (
    post_id         TEXT PRIMARY KEY,
    date            TEXT NOT NULL,
    day             TEXT NOT NULL,
    time            TEXT NOT NULL,
    time_slot       TEXT NOT NULL DEFAULT '',
    pattern         TEXT NOT NULL DEFAULT '',
    pattern_rank    TEXT NOT NULL DEFAULT '',
    pillar          TEXT NOT NULL DEFAULT '',
    content_type    TEXT NOT NULL DEFAULT '',
    image_type      TEXT NOT NULL DEFAULT 'none',
    topic           TEXT NOT NULL DEFAULT '',
    post_text       TEXT NOT NULL DEFAULT '',
    post_url        TEXT NOT NULL DEFAULT '',
    note_url        TEXT NOT NULL DEFAULT '',
    source          TEXT NOT NULL DEFAULT '',
    hashtags        TEXT NOT NULL DEFAULT '',
    char_count      INTEGER NOT NULL DEFAULT 0,
    impressions     INTEGER NOT NULL DEFAULT 0,
    engagements     INTEGER NOT NULL DEFAULT 0,
    detail_clicks   INTEGER NOT NULL DEFAULT 0,
    profile_visits  INTEGER NOT NULL DEFAULT 0,
    link_clicks     INTEGER NOT NULL DEFAULT 0,
    likes           INTEGER NOT NULL DEFAULT 0,
    retweets        INTEGER NOT NULL DEFAULT 0,
    replies         INTEGER NOT NULL DEFAULT 0,
    bookmarks       INTEGER NOT NULL DEFAULT 0,
    measured_at     TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS replies (
    reply_id            TEXT PRIMARY KEY,
    date                TEXT NOT NULL,
    day                 TEXT NOT NULL,
    time                TEXT NOT NULL,
    target_user         TEXT NOT NULL DEFAULT '',
    target_post_id      TEXT NOT NULL DEFAULT '',
    target_post_url     TEXT NOT NULL DEFAULT '',
    target_layer        TEXT NOT NULL DEFAULT '',
    keyword_used        TEXT NOT NULL DEFAULT '',
    reply_text          TEXT NOT NULL DEFAULT '',
    pattern_type        TEXT NOT NULL DEFAULT '',
    reply_url           TEXT NOT NULL DEFAULT '',
    impressions         INTEGER NOT NULL DEFAULT 0,
    likes               INTEGER NOT NULL DEFAULT 0,
    reply_backs         INTEGER NOT NULL DEFAULT 0,
    profile_visits      INTEGER NOT NULL DEFAULT 0,
    measured_at         TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
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
    ("metrics_update_window_days", "update", "メトリクス更新ウィンドウ（日数）", "3"),
    ("reply_metrics_window_days", "update", "リプライメトリクス更新ウィンドウ（日数）", "3"),
    ("reply_daily_target", "reply", "1日あたりリプライ目標件数", "10"),
]

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_posts_date ON posts(date);
CREATE INDEX IF NOT EXISTS idx_posts_pattern ON posts(pattern);
CREATE INDEX IF NOT EXISTS idx_posts_time_slot ON posts(time_slot);
CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source);
CREATE INDEX IF NOT EXISTS idx_posts_content_type ON posts(content_type);
CREATE INDEX IF NOT EXISTS idx_replies_date ON replies(date);
CREATE INDEX IF NOT EXISTS idx_replies_layer ON replies(target_layer);
CREATE INDEX IF NOT EXISTS idx_replies_keyword ON replies(keyword_used);
"""

# 既存DBへの列追加（ALTER TABLE）
MIGRATIONS = [
    "ALTER TABLE posts ADD COLUMN time_slot TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE posts ADD COLUMN content_type TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE posts ADD COLUMN source TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE posts ADD COLUMN hashtags TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE posts ADD COLUMN char_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE posts ADD COLUMN bookmarks INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE posts ADD COLUMN status TEXT NOT NULL DEFAULT 'posted'",
    "ALTER TABLE posts ADD COLUMN image_path TEXT NOT NULL DEFAULT ''",
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


def check_update_window(conn: sqlite3.Connection, post_id: str) -> None:
    window = get_rule(conn, "metrics_update_window_days")
    if not window:
        return
    row = conn.execute(
        "SELECT date, topic FROM posts WHERE post_id = ?", (post_id,)
    ).fetchone()
    if not row:
        return
    pub_date = datetime.strptime(row["date"], "%Y-%m-%d")
    days_since = (datetime.now() - pub_date).days
    if days_since > int(window):
        print(f"⚠ WARNING: '{row['topic']}' is {days_since} days old (window: {window} days)")
        print("  Metrics are past the update window. Consider using report --monthly for summary.")


# ── add ──────────────────────────────────────────────────────────────────

def add_post(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    day = args.day
    if not day and args.date:
        dt = datetime.strptime(args.date, "%Y-%m-%d")
        day = DAY_MAP[dt.weekday()]

    slot = args.slot or time_to_slot(args.time)
    text = args.text or ""
    char_count = len(text)

    status = args.status or ("scheduled" if not args.url else "posted")

    conn.execute(
        """INSERT OR REPLACE INTO posts
           (post_id, date, day, time, time_slot, pattern, pattern_rank, pillar,
            content_type, image_type, topic, post_text, post_url, note_url,
            source, hashtags, char_count, status, image_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            args.post_id, args.date, day, args.time, slot,
            args.pattern or "", args.pattern_rank or "", args.pillar or "",
            args.content_type or "", args.image_type or "none",
            args.topic or "", text, args.url or "", args.note_url or "",
            args.source or "", args.hashtags or "", char_count,
            status, args.image_path or "",
        ),
    )
    conn.commit()
    print(f"Added: {args.post_id} ({args.date} {args.time} [{slot}] {args.topic})")


# ── update ───────────────────────────────────────────────────────────────

def update_metrics(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    check_update_window(conn, args.post_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute(
        """UPDATE posts SET
           impressions = ?, engagements = ?, detail_clicks = ?,
           profile_visits = ?, link_clicks = ?, likes = ?,
           retweets = ?, replies = ?, bookmarks = ?, measured_at = ?
           WHERE post_id = ?""",
        (
            args.imp or 0, args.eng or 0, args.detail or 0,
            args.profile or 0, args.link or 0, args.likes or 0,
            args.retweets or 0, args.replies or 0, args.bookmarks or 0,
            now, args.post_id,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT topic FROM posts WHERE post_id = ?", (args.post_id,)).fetchone()
    topic = row["topic"] if row else "?"
    print(f"Updated: {args.post_id} ({topic}) imp={args.imp} eng={args.eng}")


# ── show ─────────────────────────────────────────────────────────────────

def show_post(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    r = conn.execute("SELECT * FROM posts WHERE post_id = ?", (args.post_id,)).fetchone()
    if not r:
        print(f"Post not found: {args.post_id}")
        return

    eng_rate = (r["engagements"] / r["impressions"] * 100) if r["impressions"] > 0 else 0.0

    print("=" * 60)
    print(f"  Post Detail: {r['topic']}")
    print("=" * 60)
    print(f"  ID:           {r['post_id']}")
    print(f"  URL:          {r['post_url']}")
    print(f"  Date:         {r['date']} ({r['day']}) {r['time']} [{r['time_slot']}]")
    print("-" * 60)
    print(f"  Pattern:      {r['pattern']} (rank: {r['pattern_rank']})")
    print(f"  Pillar:       {r['pillar']}")
    print(f"  Content Type: {r['content_type']}")
    print(f"  Source:        {r['source']}")
    print(f"  Image:        {r['image_type']}")
    print(f"  Hashtags:     {r['hashtags']}")
    if r["note_url"]:
        print(f"  Note URL:     {r['note_url']}")
    print("-" * 60)
    print(f"  Text ({r['char_count']} chars):")
    if r["post_text"]:
        for line in r["post_text"].split("\n"):
            print(f"    {line}")
    print("-" * 60)
    print(f"  Impressions:    {r['impressions']}")
    print(f"  Engagements:    {r['engagements']} ({eng_rate:.1f}%)")
    print(f"  Detail Clicks:  {r['detail_clicks']}")
    print(f"  Profile Visits: {r['profile_visits']}")
    print(f"  Link Clicks:    {r['link_clicks']}")
    print(f"  Likes:          {r['likes']}")
    print(f"  Retweets:       {r['retweets']}")
    print(f"  Replies:        {r['replies']}")
    print(f"  Bookmarks:      {r['bookmarks']}")
    print(f"  Measured At:    {r['measured_at']}")
    print("=" * 60)


# ── list ─────────────────────────────────────────────────────────────────

def list_posts(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    query = "SELECT * FROM posts"
    params: list[Any] = []
    if args.days:
        since = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        query += " WHERE date >= ?"
        params.append(since)
    query += " ORDER BY date DESC, time DESC"

    rows = conn.execute(query, params).fetchall()
    if not rows:
        print("No posts found.")
        return

    print(f"{'ID':>22} {'Date':>10} {'Time':>5} {'Slot':<3} {'Pattern':<16} {'Src':<8} {'Imp':>4} {'Eng':>4} {'Topic'}")
    print("-" * 110)
    for r in rows:
        print(
            f"{r['post_id']:>22} {r['date']:>10} {r['time']:>5} "
            f"{r['time_slot']:<3} {r['pattern']:<16} {r['source']:<8} "
            f"{r['impressions']:>4} {r['engagements']:>4} {r['topic']}"
        )
    print(f"\nTotal: {len(rows)} posts")


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
            SUM(impressions) as total_imp,
            AVG(impressions) as avg_imp,
            SUM(engagements) as total_eng,
            AVG(engagements) as avg_eng,
            SUM(detail_clicks) as total_detail,
            SUM(profile_visits) as total_profile,
            SUM(link_clicks) as total_link,
            SUM(likes) as total_likes,
            SUM(retweets) as total_rt,
            SUM(replies) as total_replies,
            SUM(bookmarks) as total_bm,
            MIN(date) as first_date,
            MAX(date) as last_date,
            COUNT(DISTINCT date) as active_days
        FROM posts {where}""",
        params,
    ).fetchone()

    if not row or row["cnt"] == 0:
        print("No data.")
        return

    days = row["active_days"]
    posts_per_day = row["cnt"] / days if days > 0 else 0

    print("=" * 55)
    print(f"  X Analytics Summary ({row['first_date']} ~ {row['last_date']})")
    print("=" * 55)
    print(f"  Posts:          {row['cnt']} ({days} days, {posts_per_day:.1f}/day)")
    print(f"  Impressions:    {row['total_imp']} (avg {row['avg_imp']:.1f}/post)")
    print(f"  Engagements:    {row['total_eng']} (avg {row['avg_eng']:.1f}/post)")
    print(f"  Detail Clicks:  {row['total_detail']}")
    print(f"  Profile Visits: {row['total_profile']}")
    print(f"  Link Clicks:    {row['total_link']}")
    print(f"  Likes:          {row['total_likes']}")
    print(f"  RTs:            {row['total_rt']}")
    print(f"  Replies:        {row['total_replies']}")
    print(f"  Bookmarks:      {row['total_bm']}")
    if row["total_imp"] > 0:
        rate = row["total_eng"] / row["total_imp"] * 100
        print(f"  Eng Rate:       {rate:.2f}%")
    print("=" * 55)

    # Top 3
    top3 = conn.execute(
        f"SELECT topic, impressions, engagements FROM posts {where} ORDER BY impressions DESC LIMIT 3",
        params,
    ).fetchall()
    if top3:
        print("\n  Top 3:")
        for i, t in enumerate(top3, 1):
            print(f"    {i}. {t['topic']} (imp={t['impressions']} eng={t['engagements']})")


def _report_by(conn: sqlite3.Connection, by: str, where: str, params: list[Any]) -> None:
    col_map = {
        "pattern": "pattern",
        "time": "time",
        "image": "image_type",
        "day": "day",
        "pillar": "pillar",
        "slot": "time_slot",
        "source": "source",
        "content": "content_type",
    }
    col = col_map.get(by)
    if not col:
        print(f"Unknown grouping: {by}. Use: {', '.join(col_map.keys())}")
        return

    rows = conn.execute(
        f"""SELECT
            {col} as grp,
            COUNT(*) as cnt,
            ROUND(AVG(impressions), 1) as avg_imp,
            ROUND(AVG(engagements), 1) as avg_eng,
            SUM(impressions) as total_imp,
            SUM(engagements) as total_eng,
            SUM(detail_clicks) as total_detail,
            SUM(profile_visits) as total_profile,
            SUM(link_clicks) as total_link,
            MAX(impressions) as max_imp
        FROM posts {where}
        GROUP BY {col}
        ORDER BY avg_imp DESC""",
        params,
    ).fetchall()

    if not rows:
        print("No data.")
        return

    label = by.upper()
    print(f"\n{'':>2} {label:<20} {'N':>3} {'AvgImp':>7} {'AvgEng':>7} {'MaxImp':>7} {'TotImp':>7} {'TotEng':>7} {'Det':>4} {'Prof':>4} {'Link':>4}")
    print("-" * 100)
    for r in rows:
        grp = r["grp"] if r["grp"] else "(empty)"
        print(
            f"  {grp:<20} {r['cnt']:>3} {r['avg_imp']:>7.1f} {r['avg_eng']:>7.1f} "
            f"{r['max_imp']:>7} {r['total_imp']:>7} {r['total_eng']:>7} "
            f"{r['total_detail']:>4} {r['total_profile']:>4} {r['total_link']:>4}"
        )


def _report_ranking(conn: sqlite3.Connection, where: str, params: list[Any]) -> None:
    rows = conn.execute(
        f"""SELECT post_id, date, time, time_slot, pattern, image_type, source, topic,
                   impressions, engagements, detail_clicks, profile_visits, link_clicks, likes
            FROM posts {where}
            ORDER BY impressions DESC""",
        params,
    ).fetchall()

    if not rows:
        print("No data.")
        return

    print(f"\n{'#':>3} {'Date':>10} {'Time':>5} {'Slot':<3} {'Pattern':<16} {'Img':<10} {'Imp':>4} {'Eng':>4} {'Det':>4} {'Prof':>4} {'Lk':>3} {'Topic'}")
    print("-" * 115)
    for i, r in enumerate(rows, 1):
        print(
            f"{i:>3} {r['date']:>10} {r['time']:>5} {r['time_slot']:<3} "
            f"{r['pattern']:<16} {r['image_type']:<10} "
            f"{r['impressions']:>4} {r['engagements']:>4} {r['detail_clicks']:>4} "
            f"{r['profile_visits']:>4} {r['likes']:>3} {r['topic']}"
        )


def _report_monthly(conn: sqlite3.Connection, month: str) -> None:
    if month:
        # 特定月の詳細
        rows = conn.execute(
            """SELECT
                date, COUNT(*) as cnt,
                SUM(impressions) as imp, SUM(engagements) as eng,
                SUM(likes) as lk, SUM(detail_clicks) as det,
                SUM(profile_visits) as prof
            FROM posts
            WHERE substr(date, 1, 7) = ?
            GROUP BY date
            ORDER BY date""",
            (month,),
        ).fetchall()

        if not rows:
            print(f"No data for {month}.")
            return

        totals = conn.execute(
            """SELECT COUNT(*) as cnt, SUM(impressions) as imp, SUM(engagements) as eng,
                      AVG(impressions) as avg_imp, AVG(engagements) as avg_eng,
                      SUM(likes) as lk, SUM(detail_clicks) as det,
                      SUM(profile_visits) as prof, SUM(link_clicks) as link,
                      SUM(bookmarks) as bm
            FROM posts WHERE substr(date, 1, 7) = ?""",
            (month,),
        ).fetchone()

        print(f"\n{'=' * 55}")
        print(f"  Monthly Detail: {month}")
        print(f"{'=' * 55}")
        print(f"  Posts: {totals['cnt']} | Imp: {totals['imp']} (avg {totals['avg_imp']:.1f}) | Eng: {totals['eng']} (avg {totals['avg_eng']:.1f})")
        print(f"  Likes: {totals['lk']} | Detail: {totals['det']} | Profile: {totals['prof']} | Link: {totals['link']} | BM: {totals['bm']}")
        if totals["imp"] > 0:
            print(f"  Eng Rate: {totals['eng'] / totals['imp'] * 100:.2f}%")

        print(f"\n  {'Date':>10} {'Day':>3} {'N':>3} {'Imp':>6} {'Eng':>5} {'Likes':>5} {'Det':>5} {'Prof':>5}")
        print(f"  {'-' * 50}")
        for r in rows:
            dt = datetime.strptime(r["date"], "%Y-%m-%d")
            day = DAY_MAP[dt.weekday()]
            print(
                f"  {r['date']:>10} {day:>3} {r['cnt']:>3} "
                f"{r['imp']:>6} {r['eng']:>5} {r['lk']:>5} {r['det']:>5} {r['prof']:>5}"
            )

        # パターン別内訳
        patterns = conn.execute(
            """SELECT pattern, COUNT(*) as cnt, ROUND(AVG(impressions),1) as avg_imp,
                      SUM(engagements) as eng
            FROM posts WHERE substr(date, 1, 7) = ?
            GROUP BY pattern ORDER BY avg_imp DESC""",
            (month,),
        ).fetchall()
        if patterns:
            print(f"\n  Pattern Breakdown:")
            for p in patterns:
                nm = p["pattern"] or "(empty)"
                print(f"    {nm:<20} x{p['cnt']} avg_imp={p['avg_imp']} eng={p['eng']}")

        # 時間枠別内訳
        slots = conn.execute(
            """SELECT time_slot, COUNT(*) as cnt, ROUND(AVG(impressions),1) as avg_imp
            FROM posts WHERE substr(date, 1, 7) = ?
            GROUP BY time_slot ORDER BY avg_imp DESC""",
            (month,),
        ).fetchall()
        if slots:
            print(f"\n  Time Slot Breakdown:")
            for s in slots:
                nm = s["time_slot"] or "(empty)"
                print(f"    {nm:<6} x{s['cnt']} avg_imp={s['avg_imp']}")

    else:
        # 月別サマリ一覧
        rows = conn.execute(
            """SELECT
                substr(date, 1, 7) as month,
                COUNT(*) as cnt,
                SUM(impressions) as total_imp,
                ROUND(AVG(impressions), 1) as avg_imp,
                SUM(engagements) as total_eng,
                ROUND(AVG(engagements), 1) as avg_eng,
                SUM(likes) as lk,
                SUM(detail_clicks) as det,
                SUM(profile_visits) as prof,
                SUM(link_clicks) as link,
                COUNT(DISTINCT date) as active_days
            FROM posts
            GROUP BY substr(date, 1, 7)
            ORDER BY month""",
        ).fetchall()

        if not rows:
            print("No data.")
            return

        print(f"\n  {'Month':>7} {'N':>4} {'Days':>4} {'N/Day':>5} {'TotImp':>7} {'AvgImp':>7} {'TotEng':>7} {'AvgEng':>7} {'Likes':>5} {'Det':>4} {'Prof':>4} {'Link':>4} {'Rate':>6}")
        print(f"  {'-' * 100}")
        for r in rows:
            n_per_day = r["cnt"] / r["active_days"] if r["active_days"] > 0 else 0
            rate = r["total_eng"] / r["total_imp"] * 100 if r["total_imp"] > 0 else 0
            print(
                f"  {r['month']:>7} {r['cnt']:>4} {r['active_days']:>4} {n_per_day:>5.1f} "
                f"{r['total_imp']:>7} {r['avg_imp']:>7.1f} {r['total_eng']:>7} {r['avg_eng']:>7.1f} "
                f"{r['lk']:>5} {r['det']:>4} {r['prof']:>4} {r['link']:>4} {rate:>5.1f}%"
            )


def _report_yearly(conn: sqlite3.Connection, year: str) -> None:
    if year:
        # 特定年の月別内訳
        rows = conn.execute(
            """SELECT
                substr(date, 1, 7) as month,
                COUNT(*) as cnt,
                SUM(impressions) as total_imp,
                ROUND(AVG(impressions), 1) as avg_imp,
                SUM(engagements) as total_eng,
                ROUND(AVG(engagements), 1) as avg_eng,
                SUM(likes) as lk,
                SUM(detail_clicks) as det,
                SUM(profile_visits) as prof,
                SUM(link_clicks) as link,
                COUNT(DISTINCT date) as active_days
            FROM posts
            WHERE substr(date, 1, 4) = ?
            GROUP BY substr(date, 1, 7)
            ORDER BY month""",
            (year,),
        ).fetchall()

        if not rows:
            print(f"No data for {year}.")
            return

        totals = conn.execute(
            """SELECT COUNT(*) as cnt, SUM(impressions) as imp, SUM(engagements) as eng,
                      AVG(impressions) as avg_imp, AVG(engagements) as avg_eng,
                      SUM(likes) as lk, SUM(detail_clicks) as det,
                      SUM(profile_visits) as prof, SUM(link_clicks) as link,
                      SUM(bookmarks) as bm, COUNT(DISTINCT date) as days
            FROM posts WHERE substr(date, 1, 4) = ?""",
            (year,),
        ).fetchone()

        rate = totals["eng"] / totals["imp"] * 100 if totals["imp"] > 0 else 0

        print(f"\n{'=' * 55}")
        print(f"  Yearly Detail: {year}")
        print(f"{'=' * 55}")
        print(f"  Posts: {totals['cnt']} | Days: {totals['days']} | Imp: {totals['imp']} (avg {totals['avg_imp']:.1f})")
        print(f"  Eng: {totals['eng']} (avg {totals['avg_eng']:.1f}) | Rate: {rate:.2f}%")
        print(f"  Likes: {totals['lk']} | Det: {totals['det']} | Prof: {totals['prof']} | Link: {totals['link']} | BM: {totals['bm']}")

        print(f"\n  {'Month':>7} {'N':>4} {'Days':>4} {'TotImp':>7} {'AvgImp':>7} {'TotEng':>7} {'AvgEng':>7} {'Likes':>5} {'Rate':>6}")
        print(f"  {'-' * 70}")
        for r in rows:
            r_rate = r["total_eng"] / r["total_imp"] * 100 if r["total_imp"] > 0 else 0
            print(
                f"  {r['month']:>7} {r['cnt']:>4} {r['active_days']:>4} "
                f"{r['total_imp']:>7} {r['avg_imp']:>7.1f} {r['total_eng']:>7} {r['avg_eng']:>7.1f} "
                f"{r['lk']:>5} {r_rate:>5.1f}%"
            )

        # 年間パターンランキング
        patterns = conn.execute(
            """SELECT pattern, COUNT(*) as cnt, ROUND(AVG(impressions),1) as avg_imp,
                      SUM(engagements) as eng, SUM(impressions) as tot_imp
            FROM posts WHERE substr(date, 1, 4) = ?
            GROUP BY pattern ORDER BY avg_imp DESC""",
            (year,),
        ).fetchall()
        if patterns:
            print(f"\n  Pattern Ranking ({year}):")
            for p in patterns:
                nm = p["pattern"] or "(empty)"
                print(f"    {nm:<20} x{p['cnt']} avg_imp={p['avg_imp']} tot_imp={p['tot_imp']} eng={p['eng']}")

    else:
        # 年別サマリ一覧
        rows = conn.execute(
            """SELECT
                substr(date, 1, 4) as year,
                COUNT(*) as cnt,
                SUM(impressions) as total_imp,
                ROUND(AVG(impressions), 1) as avg_imp,
                SUM(engagements) as total_eng,
                ROUND(AVG(engagements), 1) as avg_eng,
                SUM(likes) as lk,
                COUNT(DISTINCT date) as active_days,
                COUNT(DISTINCT substr(date, 1, 7)) as active_months
            FROM posts
            GROUP BY substr(date, 1, 4)
            ORDER BY year""",
        ).fetchall()

        if not rows:
            print("No data.")
            return

        print(f"\n  {'Year':>4} {'N':>5} {'Months':>6} {'Days':>5} {'TotImp':>8} {'AvgImp':>7} {'TotEng':>7} {'AvgEng':>7} {'Likes':>5} {'Rate':>6}")
        print(f"  {'-' * 80}")
        for r in rows:
            rate = r["total_eng"] / r["total_imp"] * 100 if r["total_imp"] > 0 else 0
            print(
                f"  {r['year']:>4} {r['cnt']:>5} {r['active_months']:>6} {r['active_days']:>5} "
                f"{r['total_imp']:>8} {r['avg_imp']:>7.1f} {r['total_eng']:>7} {r['avg_eng']:>7.1f} "
                f"{r['lk']:>5} {rate:>5.1f}%"
            )


# ── import-yaml ──────────────────────────────────────────────────────────

def import_yaml(conn: sqlite3.Connection, _args: argparse.Namespace) -> None:
    if not POSTS_DIR.exists():
        print(f"Posts directory not found: {POSTS_DIR}")
        return

    count = 0
    for f in sorted(POSTS_DIR.glob("*.yaml")):
        if f.name.startswith("_"):
            continue
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not data or not data.get("post_id"):
            continue

        metrics = data.get("metrics", {})
        t = data.get("time", "")
        slot = time_to_slot(t) if t else ""
        text = data.get("post_text", "")

        conn.execute(
            """INSERT OR REPLACE INTO posts
               (post_id, date, day, time, time_slot, pattern, pattern_rank, pillar,
                image_type, topic, post_text, post_url, char_count,
                impressions, engagements, detail_clicks, profile_visits,
                link_clicks, likes, retweets, replies, bookmarks)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(data.get("post_id", "")),
                data.get("date", ""),
                data.get("day", ""),
                t, slot,
                data.get("pattern", ""),
                data.get("pattern_rank", ""),
                data.get("pillar", ""),
                data.get("image_type", "none"),
                data.get("topic", ""),
                text,
                data.get("post_url", ""),
                len(text),
                metrics.get("impressions", 0),
                metrics.get("engagements", 0),
                metrics.get("detail_clicks", 0) if "detail_clicks" in metrics else 0,
                metrics.get("profile_clicks", 0),
                metrics.get("link_clicks", 0),
                metrics.get("likes", 0),
                metrics.get("retweets", 0),
                metrics.get("replies", 0),
                metrics.get("bookmarks", 0),
            ),
        )
        count += 1
        print(f"  Imported: {f.name}")

    conn.commit()
    print(f"\nImported {count} posts from YAML.")


# ── stock ────────────────────────────────────────────────────────────────

# 標準4枠
DAILY_SLOTS = [
    ("07:00", "朝"),
    ("12:00", "昼"),
    ("18:00", "夕"),
    ("22:00", "夜"),
]


def stock_check(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """今後N日分のスロット充足状況を表示する。"""
    days = args.days or 3
    today = datetime.now().date()

    # 今後N日分の予定投稿を取得
    start = today.strftime("%Y-%m-%d")
    end = (today + timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT date, time, time_slot, status, topic, pattern, image_type, post_id "
        "FROM posts WHERE date >= ? AND date < ? ORDER BY date, time",
        (start, end),
    ).fetchall()

    # 日付×スロットのマップを作成
    filled: dict[str, dict[str, dict]] = {}
    for r in rows:
        d = r["date"]
        slot = r["time_slot"] or time_to_slot(r["time"])
        if d not in filled:
            filled[d] = {}
        filled[d][slot] = {
            "topic": r["topic"],
            "pattern": r["pattern"],
            "status": r["status"] or "posted",
            "image": r["image_type"],
            "post_id": r["post_id"],
        }

    total_slots = 0
    filled_slots = 0
    empty_list: list[tuple[str, str, str]] = []

    print(f"\n{'=' * 65}")
    print(f"  Stock Check: {start} ~ {end} ({days} days)")
    print(f"{'=' * 65}")

    for i in range(days):
        d = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        dt = today + timedelta(days=i)
        day_name = DAY_MAP[dt.weekday()]
        print(f"\n  📅 {d} ({day_name})")

        for slot_time, slot_name in DAILY_SLOTS:
            total_slots += 1
            entry = filled.get(d, {}).get(slot_name)
            if entry:
                filled_slots += 1
                status_icon = "✅" if entry["status"] == "posted" else "🔜"
                print(f"    {slot_time} [{slot_name}] {status_icon} {entry['pattern']:<16} {entry['topic']}")
            else:
                empty_list.append((d, slot_time, slot_name))
                print(f"    {slot_time} [{slot_name}] ⬜ --- 空き ---")

    print(f"\n{'─' * 65}")
    print(f"  充足: {filled_slots}/{total_slots} ({filled_slots/total_slots*100:.0f}%)")
    print(f"  空き: {total_slots - filled_slots} スロット")

    if empty_list:
        print(f"\n  空きスロット一覧:")
        for d, t, s in empty_list:
            dt = datetime.strptime(d, "%Y-%m-%d")
            day_name = DAY_MAP[dt.weekday()]
            print(f"    {d} ({day_name}) {t} [{s}]")

    print(f"{'=' * 65}")


# ── queue-sync ──────────────────────────────────────────────────────────

QUEUE_PATH = ROOT / "knowledge" / "x-content-queue.md"


def queue_sync(conn: sqlite3.Connection, _args: argparse.Namespace) -> None:
    """DBの状態からx-content-queue.mdを再生成する。"""
    today = datetime.now().strftime("%Y-%m-%d")

    # Scheduled: 未来の投稿（statusがscheduled or 日付が未来でpost_urlが空）
    scheduled = conn.execute(
        "SELECT date, time, topic, pattern, image_type, image_path, status "
        "FROM posts WHERE (status = 'scheduled' OR (date >= ? AND post_url = '')) "
        "ORDER BY date, time",
        (today,),
    ).fetchall()

    # Posted: 投稿済み（直近14日、post_urlあり）
    since = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    posted = conn.execute(
        "SELECT date, time, topic, pattern, post_url, source, impressions "
        "FROM posts WHERE post_url != '' AND date >= ? "
        "ORDER BY date DESC, time DESC",
        (since,),
    ).fetchall()

    # Inbox: x-content-queue.md の inbox セクションは手動管理のため保持
    # 既存ファイルから inbox セクションを抽出
    inbox_lines: list[str] = []
    dropped_lines: list[str] = []
    if QUEUE_PATH.exists():
        section = ""
        with open(QUEUE_PATH, encoding="utf-8") as f:
            for line in f:
                if line.startswith("## Inbox"):
                    section = "inbox"
                    continue
                elif line.startswith("## Ready"):
                    section = ""
                    continue
                elif line.startswith("## Dropped"):
                    section = "dropped"
                    continue
                elif line.startswith("## "):
                    section = ""
                    continue
                if section == "inbox":
                    inbox_lines.append(line.rstrip())
                elif section == "dropped":
                    dropped_lines.append(line.rstrip())

    # 生成
    lines = [
        "# X Content Queue",
        "",
        "`x_analytics.py queue-sync` で DB から自動生成。Inbox / Dropped のみ手動管理。",
        "",
        "## Inbox",
        "",
    ]
    lines.extend(inbox_lines)

    lines.append("")
    lines.append("## Scheduled")
    lines.append("")
    if scheduled:
        lines.append("| Date | Time | Pattern | Image | Topic |")
        lines.append("|---|---|---|---|---|")
        for r in scheduled:
            img = r["image_path"].split("/")[-1] if r["image_path"] else r["image_type"]
            lines.append(f"| {r['date']} | {r['time']} | {r['pattern']} | {img} | {r['topic']} |")
    else:
        lines.append("（なし）")

    lines.append("")
    lines.append("## Posted (直近14日)")
    lines.append("")
    if posted:
        lines.append("| Date | Time | Pattern | Imp | Topic | URL |")
        lines.append("|---|---|---|---|---|---|")
        for r in posted:
            lines.append(
                f"| {r['date']} | {r['time']} | {r['pattern']} | "
                f"{r['impressions']} | {r['topic']} | {r['post_url']} |"
            )
    else:
        lines.append("（なし）")

    lines.append("")
    lines.append("## Dropped")
    lines.append("")
    lines.extend(dropped_lines)
    lines.append("")

    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Queue synced: {len(scheduled)} scheduled, {len(posted)} posted → {QUEUE_PATH.name}")


# ── reply-add ────────────────────────────────────────────────────────────

def add_reply(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    day = args.day
    if not day and args.date:
        dt = datetime.strptime(args.date, "%Y-%m-%d")
        day = DAY_MAP[dt.weekday()]

    # target_post_id をURLから抽出（末尾の数字部分）
    target_post_id = args.target_post_id or ""
    if not target_post_id and args.target_url:
        parts = args.target_url.rstrip("/").split("/")
        target_post_id = parts[-1] if parts else ""

    conn.execute(
        """INSERT OR REPLACE INTO replies
           (reply_id, date, day, time, target_user, target_post_id, target_post_url,
            target_layer, keyword_used, reply_text, pattern_type, reply_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            args.reply_id, args.date, day, args.time,
            args.target_user or "", target_post_id, args.target_url or "",
            args.layer or "", args.keyword or "",
            args.text or "", args.pattern or "", args.url or "",
        ),
    )
    conn.commit()
    print(f"Reply added: {args.reply_id} → {args.target_user} [{args.layer}]")


# ── reply-update ─────────────────────────────────────────────────────────

def update_reply(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    # ウィンドウチェック
    window = get_rule(conn, "reply_metrics_window_days")
    if window:
        row = conn.execute(
            "SELECT date, target_user FROM replies WHERE reply_id = ?", (args.reply_id,)
        ).fetchone()
        if row:
            pub_date = datetime.strptime(row["date"], "%Y-%m-%d")
            days_since = (datetime.now() - pub_date).days
            if days_since > int(window):
                print(f"⚠ WARNING: Reply to {row['target_user']} is {days_since} days old (window: {window} days)")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute(
        """UPDATE replies SET
           impressions = ?, likes = ?, reply_backs = ?,
           profile_visits = ?, measured_at = ?
           WHERE reply_id = ?""",
        (
            args.imp or 0, args.likes or 0, args.reply_backs or 0,
            args.profile or 0, now, args.reply_id,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT target_user FROM replies WHERE reply_id = ?", (args.reply_id,)).fetchone()
    user = row["target_user"] if row else "?"
    print(f"Updated reply: {args.reply_id} → {user} (imp={args.imp} likes={args.likes} backs={args.reply_backs})")


# ── reply-list ───────────────────────────────────────────────────────────

def list_replies(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    query = "SELECT * FROM replies"
    params: list[Any] = []
    if args.days:
        since = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        query += " WHERE date >= ?"
        params.append(since)
    query += " ORDER BY date DESC, time DESC"

    rows = conn.execute(query, params).fetchall()
    if not rows:
        print("No replies found.")
        return

    print(f"{'ID':>22} {'Date':>10} {'Time':>5} {'Layer':<6} {'Target':<20} {'Imp':>4} {'Lk':>3} {'Bk':>3} {'Pattern'}")
    print("-" * 100)
    for r in rows:
        print(
            f"{r['reply_id']:>22} {r['date']:>10} {r['time']:>5} "
            f"{r['target_layer']:<6} {r['target_user']:<20} "
            f"{r['impressions']:>4} {r['likes']:>3} {r['reply_backs']:>3} {r['pattern_type']}"
        )
    print(f"\nTotal: {len(rows)} replies")


# ── reply-report ─────────────────────────────────────────────────────────

def reply_report(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    where = ""
    params: list[Any] = []
    if args.days:
        since = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        where = "WHERE date >= ?"
        params.append(since)

    if args.ranking:
        _reply_ranking(conn, where, params)
    elif args.by:
        _reply_report_by(conn, args.by, where, params)
    else:
        _reply_summary(conn, where, params)


def _reply_summary(conn: sqlite3.Connection, where: str, params: list[Any]) -> None:
    row = conn.execute(
        f"""SELECT
            COUNT(*) as cnt,
            SUM(impressions) as total_imp,
            AVG(impressions) as avg_imp,
            SUM(likes) as total_likes,
            SUM(reply_backs) as total_backs,
            SUM(profile_visits) as total_profile,
            MIN(date) as first_date,
            MAX(date) as last_date,
            COUNT(DISTINCT date) as active_days
        FROM replies {where}""",
        params,
    ).fetchone()

    if not row or row["cnt"] == 0:
        print("No reply data.")
        return

    days = row["active_days"]
    per_day = row["cnt"] / days if days > 0 else 0

    print("=" * 55)
    print(f"  Reply Analytics Summary ({row['first_date']} ~ {row['last_date']})")
    print("=" * 55)
    print(f"  Replies:        {row['cnt']} ({days} days, {per_day:.1f}/day)")
    print(f"  Impressions:    {row['total_imp'] or 0} (avg {(row['avg_imp'] or 0):.1f})")
    print(f"  Likes:          {row['total_likes'] or 0}")
    print(f"  Reply Backs:    {row['total_backs'] or 0}")
    print(f"  Profile Visits: {row['total_profile'] or 0}")

    # 層別内訳
    layers = conn.execute(
        f"""SELECT target_layer, COUNT(*) as cnt,
                   SUM(impressions) as imp, SUM(likes) as lk, SUM(reply_backs) as bk
        FROM replies {where}
        GROUP BY target_layer ORDER BY cnt DESC""",
        params,
    ).fetchall()
    if layers:
        print(f"\n  Layer Breakdown:")
        for la in layers:
            nm = la["target_layer"] or "(empty)"
            print(f"    {nm:<10} x{la['cnt']} imp={la['imp'] or 0} likes={la['lk'] or 0} backs={la['bk'] or 0}")

    # 日別件数
    daily = conn.execute(
        f"SELECT date, COUNT(*) as cnt FROM replies {where} GROUP BY date ORDER BY date DESC LIMIT 7",
        params,
    ).fetchall()
    if daily:
        target = get_rule(conn, "reply_daily_target") or "10"
        print(f"\n  Daily (target: {target}/day):")
        for d in daily:
            bar = "█" * d["cnt"] + "░" * max(0, int(target) - d["cnt"])
            print(f"    {d['date']} {bar} {d['cnt']}")

    print("=" * 55)


def _reply_report_by(conn: sqlite3.Connection, by: str, where: str, params: list[Any]) -> None:
    col_map = {
        "layer": "target_layer",
        "keyword": "keyword_used",
        "pattern": "pattern_type",
        "user": "target_user",
    }
    col = col_map.get(by)
    if not col:
        print(f"Unknown grouping: {by}. Use: {', '.join(col_map.keys())}")
        return

    rows = conn.execute(
        f"""SELECT
            {col} as grp,
            COUNT(*) as cnt,
            ROUND(AVG(impressions), 1) as avg_imp,
            SUM(impressions) as total_imp,
            SUM(likes) as total_likes,
            SUM(reply_backs) as total_backs,
            SUM(profile_visits) as total_profile
        FROM replies {where}
        GROUP BY {col}
        ORDER BY total_imp DESC""",
        params,
    ).fetchall()

    if not rows:
        print("No data.")
        return

    label = by.upper()
    print(f"\n  {label:<20} {'N':>3} {'AvgImp':>7} {'TotImp':>7} {'Likes':>5} {'Backs':>5} {'Prof':>5}")
    print(f"  {'-' * 65}")
    for r in rows:
        grp = r["grp"] if r["grp"] else "(empty)"
        print(
            f"  {grp:<20} {r['cnt']:>3} {r['avg_imp']:>7.1f} "
            f"{r['total_imp']:>7} {r['total_likes']:>5} "
            f"{r['total_backs']:>5} {r['total_profile']:>5}"
        )


def _reply_ranking(conn: sqlite3.Connection, where: str, params: list[Any]) -> None:
    rows = conn.execute(
        f"""SELECT reply_id, date, target_user, target_layer, pattern_type,
                   reply_text, impressions, likes, reply_backs, profile_visits
        FROM replies {where}
        ORDER BY impressions DESC""",
        params,
    ).fetchall()

    if not rows:
        print("No data.")
        return

    print(f"\n{'#':>3} {'Date':>10} {'Target':<18} {'Layer':<6} {'Imp':>4} {'Lk':>3} {'Bk':>3} {'Prof':>4} Text")
    print("-" * 100)
    for i, r in enumerate(rows, 1):
        text = (r["reply_text"][:30] + "…") if len(r["reply_text"]) > 30 else r["reply_text"]
        print(
            f"{i:>3} {r['date']:>10} {r['target_user']:<18} {r['target_layer']:<6} "
            f"{r['impressions']:>4} {r['likes']:>3} {r['reply_backs']:>3} {r['profile_visits']:>4} {text}"
        )


# ── improve ──────────────────────────────────────────────────────────────

NOTE_DB_PATH = ROOT / "knowledge" / "data" / "note_articles.db"


def improve_report(conn: sqlite3.Connection, _args: argparse.Namespace) -> None:
    """全チャネル横断の改善レポートを生成する。"""
    print("=" * 65)
    print("  Improvement Report")
    print("=" * 65)

    # ── 1. 未計測アイテム ──
    print("\n── 未計測アイテム ──")

    # X投稿: measured_at が空 & 投稿から3日以上
    window = get_rule(conn, "metrics_update_window_days") or "3"
    cutoff = (datetime.now() - timedelta(days=int(window))).strftime("%Y-%m-%d")
    unmeasured_posts = conn.execute(
        "SELECT post_id, date, topic FROM posts WHERE measured_at = '' AND date <= ? ORDER BY date",
        (cutoff,),
    ).fetchall()
    if unmeasured_posts:
        print(f"\n  X投稿（{len(unmeasured_posts)}件、{window}日経過 & 未計測）:")
        for r in unmeasured_posts:
            print(f"    {r['date']} {r['topic']} [{r['post_id']}]")

    # リプライ: measured_at が空 & 3日以上
    reply_window = get_rule(conn, "reply_metrics_window_days") or "3"
    reply_cutoff = (datetime.now() - timedelta(days=int(reply_window))).strftime("%Y-%m-%d")
    unmeasured_replies = conn.execute(
        "SELECT reply_id, date, target_user, reply_text FROM replies WHERE measured_at = '' AND date <= ? ORDER BY date",
        (reply_cutoff,),
    ).fetchall()
    if unmeasured_replies:
        print(f"\n  リプライ（{len(unmeasured_replies)}件、{reply_window}日経過 & 未計測）:")
        for r in unmeasured_replies:
            text = (r["reply_text"][:25] + "…") if len(r["reply_text"]) > 25 else r["reply_text"]
            print(f"    {r['date']} → {r['target_user']} 「{text}」")

    # note記事
    if NOTE_DB_PATH.exists():
        note_conn = sqlite3.connect(str(NOTE_DB_PATH))
        note_conn.row_factory = sqlite3.Row
        unmeasured_notes = note_conn.execute(
            "SELECT article_id, date, title FROM articles WHERE measured_at = '' AND date <= ?",
            ((datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),),
        ).fetchall()
        if unmeasured_notes:
            print(f"\n  note記事（{len(unmeasured_notes)}件、7日経過 & 未計測）:")
            for r in unmeasured_notes:
                print(f"    {r['date']} {r['title']}")
        note_conn.close()

    if not unmeasured_posts and not unmeasured_replies:
        print("  なし（全て計測済み）")

    # ── 2. パフォーマンス分析 ──
    print("\n── パフォーマンス分析 ──")

    # X投稿: 計測済みのみ対象
    measured = conn.execute(
        "SELECT COUNT(*) as cnt FROM posts WHERE measured_at != ''"
    ).fetchone()
    if measured and measured["cnt"] >= 3:
        # Top/Bottom パターン
        top_pattern = conn.execute(
            """SELECT pattern, COUNT(*) as cnt, ROUND(AVG(impressions),1) as avg_imp
            FROM posts WHERE measured_at != '' AND pattern != ''
            GROUP BY pattern HAVING cnt >= 2
            ORDER BY avg_imp DESC LIMIT 3"""
        ).fetchall()
        if top_pattern:
            print("\n  X投稿 — 高パフォーマンス パターン:")
            for r in top_pattern:
                print(f"    {r['pattern']:<20} x{r['cnt']} avg_imp={r['avg_imp']}")

        bottom_pattern = conn.execute(
            """SELECT pattern, COUNT(*) as cnt, ROUND(AVG(impressions),1) as avg_imp
            FROM posts WHERE measured_at != '' AND pattern != ''
            GROUP BY pattern HAVING cnt >= 2
            ORDER BY avg_imp ASC LIMIT 3"""
        ).fetchall()
        if bottom_pattern:
            print("\n  X投稿 — 低パフォーマンス パターン:")
            for r in bottom_pattern:
                print(f"    {r['pattern']:<20} x{r['cnt']} avg_imp={r['avg_imp']}")

        # 時間帯
        top_slot = conn.execute(
            """SELECT time_slot, COUNT(*) as cnt, ROUND(AVG(impressions),1) as avg_imp
            FROM posts WHERE measured_at != '' AND time_slot != ''
            GROUP BY time_slot ORDER BY avg_imp DESC"""
        ).fetchall()
        if top_slot:
            print("\n  X投稿 — 時間帯別:")
            for r in top_slot:
                print(f"    {r['time_slot']:<6} x{r['cnt']} avg_imp={r['avg_imp']}")

    # リプライ: 計測済みのみ対象
    measured_replies = conn.execute(
        "SELECT COUNT(*) as cnt FROM replies WHERE measured_at != ''"
    ).fetchone()
    if measured_replies and measured_replies["cnt"] >= 3:
        top_layer = conn.execute(
            """SELECT target_layer, COUNT(*) as cnt,
                      ROUND(AVG(impressions),1) as avg_imp,
                      SUM(reply_backs) as backs
            FROM replies WHERE measured_at != ''
            GROUP BY target_layer ORDER BY avg_imp DESC"""
        ).fetchall()
        if top_layer:
            print("\n  リプライ — 層別パフォーマンス:")
            for r in top_layer:
                nm = r["target_layer"] or "(empty)"
                print(f"    {nm:<10} x{r['cnt']} avg_imp={r['avg_imp']} backs={r['backs'] or 0}")

        top_kw = conn.execute(
            """SELECT keyword_used, COUNT(*) as cnt,
                      ROUND(AVG(impressions),1) as avg_imp,
                      SUM(reply_backs) as backs
            FROM replies WHERE measured_at != '' AND keyword_used != ''
            GROUP BY keyword_used ORDER BY avg_imp DESC"""
        ).fetchall()
        if top_kw:
            print("\n  リプライ — キーワード別パフォーマンス:")
            for r in top_kw:
                print(f"    {r['keyword_used']:<20} x{r['cnt']} avg_imp={r['avg_imp']} backs={r['backs'] or 0}")

    # ── 3. 改善提案 ──
    print("\n── 改善アクション ──")
    actions: list[str] = []

    # 未計測があれば回収を提案
    total_unmeasured = len(unmeasured_posts) + len(unmeasured_replies)
    if total_unmeasured > 0:
        actions.append(f"メトリクス回収: {total_unmeasured}件の未計測アイテムがあります → ブラウザでアナリティクス取得")

    # リプライ日次目標チェック
    target = int(get_rule(conn, "reply_daily_target") or "10")
    today = datetime.now().strftime("%Y-%m-%d")
    today_replies = conn.execute(
        "SELECT COUNT(*) as cnt FROM replies WHERE date = ?", (today,)
    ).fetchone()
    today_cnt = today_replies["cnt"] if today_replies else 0
    if today_cnt < target:
        actions.append(f"リプライ: 本日 {today_cnt}/{target}件 → あと{target - today_cnt}件")

    # リプライでreply_backsが多いパターンがあればfew-shot昇格を提案
    if measured_replies and measured_replies["cnt"] >= 5:
        best_reply = conn.execute(
            """SELECT reply_text, target_user, reply_backs, impressions
            FROM replies WHERE measured_at != ''
            ORDER BY reply_backs DESC, impressions DESC LIMIT 1"""
        ).fetchone()
        if best_reply and (best_reply["reply_backs"] or 0) > 0:
            text = (best_reply["reply_text"][:30] + "…") if len(best_reply["reply_text"]) > 30 else best_reply["reply_text"]
            actions.append(f"Few-shot候補: 「{text}」(backs={best_reply['reply_backs']}) → reply-strategy.md に昇格検討")

    if not actions:
        actions.append("現時点で改善アクションなし（データ蓄積中）")

    for i, a in enumerate(actions, 1):
        print(f"  {i}. {a}")

    print(f"\n{'=' * 65}")


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


# ── CLI ──────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="X Analytics CLI")
    sub = parser.add_subparsers(dest="command")

    # init
    sub.add_parser("init", help="Initialize database")

    # add
    p_add = sub.add_parser("add", help="Add a post")
    p_add.add_argument("--post-id", required=True)
    p_add.add_argument("--date", required=True)
    p_add.add_argument("--time", required=True)
    p_add.add_argument("--day", default="")
    p_add.add_argument("--slot", default="")
    p_add.add_argument("--pattern", default="")
    p_add.add_argument("--pattern-rank", default="")
    p_add.add_argument("--pillar", default="")
    p_add.add_argument("--content-type", default="")
    p_add.add_argument("--image-type", default="none")
    p_add.add_argument("--topic", default="")
    p_add.add_argument("--text", default="")
    p_add.add_argument("--url", default="")
    p_add.add_argument("--note-url", default="")
    p_add.add_argument("--source", default="")
    p_add.add_argument("--hashtags", default="")
    p_add.add_argument("--status", default="", help="scheduled or posted (auto-detected from --url)")
    p_add.add_argument("--image-path", default="", help="Path to image file")

    # update
    p_upd = sub.add_parser("update", help="Update metrics")
    p_upd.add_argument("--post-id", required=True)
    p_upd.add_argument("--imp", type=int, default=0)
    p_upd.add_argument("--eng", type=int, default=0)
    p_upd.add_argument("--detail", type=int, default=0)
    p_upd.add_argument("--profile", type=int, default=0)
    p_upd.add_argument("--link", type=int, default=0)
    p_upd.add_argument("--likes", type=int, default=0)
    p_upd.add_argument("--retweets", type=int, default=0)
    p_upd.add_argument("--replies", type=int, default=0)
    p_upd.add_argument("--bookmarks", type=int, default=0)

    # show
    p_show = sub.add_parser("show", help="Show post detail")
    p_show.add_argument("--post-id", required=True)

    # list
    p_list = sub.add_parser("list", help="List posts")
    p_list.add_argument("--days", type=int, default=0)

    # report
    p_rep = sub.add_parser("report", help="Generate report")
    p_rep.add_argument("--days", type=int, default=0)
    p_rep.add_argument("--by", choices=[
        "pattern", "time", "image", "day", "pillar", "slot", "source", "content",
    ])
    p_rep.add_argument("--ranking", action="store_true")
    p_rep.add_argument("--monthly", nargs="?", const="", default=None,
                       help="Monthly summary (optionally specify YYYY-MM)")
    p_rep.add_argument("--yearly", nargs="?", const="", default=None,
                       help="Yearly summary (optionally specify YYYY)")

    # import-yaml
    sub.add_parser("import-yaml", help="Import from YAML logs")

    # stock
    p_stock = sub.add_parser("stock", help="Check scheduled stock for next N days")
    p_stock.add_argument("--days", type=int, default=3)

    # queue-sync
    sub.add_parser("queue-sync", help="Regenerate x-content-queue.md from DB")

    # reply-add
    p_radd = sub.add_parser("reply-add", help="Add a reply")
    p_radd.add_argument("--reply-id", required=True)
    p_radd.add_argument("--date", required=True)
    p_radd.add_argument("--time", required=True)
    p_radd.add_argument("--day", default="")
    p_radd.add_argument("--target-user", default="")
    p_radd.add_argument("--target-post-id", default="")
    p_radd.add_argument("--target-url", default="")
    p_radd.add_argument("--layer", default="")
    p_radd.add_argument("--keyword", default="")
    p_radd.add_argument("--text", default="")
    p_radd.add_argument("--pattern", default="")
    p_radd.add_argument("--url", default="")

    # reply-update
    p_rupd = sub.add_parser("reply-update", help="Update reply metrics")
    p_rupd.add_argument("--reply-id", required=True)
    p_rupd.add_argument("--imp", type=int, default=0)
    p_rupd.add_argument("--likes", type=int, default=0)
    p_rupd.add_argument("--reply-backs", type=int, default=0)
    p_rupd.add_argument("--profile", type=int, default=0)

    # reply-list
    p_rlist = sub.add_parser("reply-list", help="List replies")
    p_rlist.add_argument("--days", type=int, default=0)

    # reply-report
    p_rrep = sub.add_parser("reply-report", help="Reply report")
    p_rrep.add_argument("--days", type=int, default=0)
    p_rrep.add_argument("--by", choices=["layer", "keyword", "pattern", "user"])
    p_rrep.add_argument("--ranking", action="store_true")

    # improve
    sub.add_parser("improve", help="Cross-channel improvement report")

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
        "add": add_post,
        "update": update_metrics,
        "show": show_post,
        "list": list_posts,
        "report": report,
        "import-yaml": import_yaml,
        "stock": stock_check,
        "queue-sync": queue_sync,
        "reply-add": add_reply,
        "reply-update": update_reply,
        "reply-list": list_replies,
        "reply-report": reply_report,
        "improve": improve_report,
        "rules": manage_rules,
    }

    try:
        commands[args.command](conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
