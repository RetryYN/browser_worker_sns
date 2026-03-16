"""
競合コンテンツベンチマーク — SQLite管理CLI（X / note テーブル分離版）

使い方:
  python scripts/competitor_analytics.py init

  # ── X ──
  python scripts/competitor_analytics.py add-account -p x --handle masahirochaen \
      --name "茶圓 将裕" --category "AI×人事" --followers 15000 \
      --bio "AI活用コンサル" --note "毎日1-3件、画像4枚+ステップ形式"

  python scripts/competitor_analytics.py add -p x --handle masahirochaen \
      --post-id 2030530247926435845 --date 2026-03-08 \
      --text "Claudeで人事評価Excel作成" --format 画像付きステップ \
      --topic "AI×人事評価" --has-image 1 \
      --likes 639 --retweets 120 --replies 15 --bookmarks 200 --views 50000

  python scripts/competitor_analytics.py accounts -p x
  python scripts/competitor_analytics.py accounts -p x --type benchmark
  python scripts/competitor_analytics.py list -p x --days 30
  python scripts/competitor_analytics.py report -p x
  python scripts/competitor_analytics.py report -p x --ranking

  # ── note ──
  python scripts/competitor_analytics.py add-account -p note --handle fladdict \
      --name "深津貴之" --category "プロンプト技術" --cpt "C2×P2×T5" \
      --note "note CXO。AIプロンプト技術の第一人者"

  python scripts/competitor_analytics.py add -p note --handle fladdict \
      --article-id nabc123 --date 2026-03-10 --title "プロンプトの書き方" \
      --content-type "C2×P2" --treatment "実践" --chars 3000 \
      --views 500 --likes 30 --comments 5

  python scripts/competitor_analytics.py accounts -p note
  python scripts/competitor_analytics.py list -p note
  python scripts/competitor_analytics.py report -p note

  # ── 共通 ──
  python scripts/competitor_analytics.py update --post-id 2030530247926435845 \
      --likes 700 --retweets 130 --replies 18 --bookmarks 220 --views 55000
  python scripts/competitor_analytics.py show --post-id 2030530247926435845

  python scripts/competitor_analytics.py rules
  python scripts/competitor_analytics.py rules --set benchmark_interval_days=30

データ:
  knowledge/data/competitor_benchmark.db
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
DB_PATH = ROOT / "knowledge" / "data" / "competitor_benchmark.db"

DAY_MAP = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}

# ── テーブル定義 ────────────────────────────────────────

CREATE_TABLES = """
-- X アカウント
CREATE TABLE IF NOT EXISTS x_accounts (
    handle          TEXT PRIMARY KEY,
    name            TEXT DEFAULT '',
    category        TEXT DEFAULT '',
    bio             TEXT DEFAULT '',
    followers       INTEGER DEFAULT 0,
    following       INTEGER DEFAULT 0,
    note            TEXT DEFAULT '',
    account_type    TEXT DEFAULT 'benchmark',
    fork_direction  TEXT DEFAULT '',
    ng_reason       TEXT DEFAULT '',
    is_active       INTEGER DEFAULT 1,
    added_at        TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- X 投稿
CREATE TABLE IF NOT EXISTS x_posts (
    post_id         TEXT PRIMARY KEY,
    handle          TEXT NOT NULL,
    date            TEXT NOT NULL,
    day             TEXT NOT NULL DEFAULT '',
    text            TEXT DEFAULT '',
    format          TEXT DEFAULT '',
    topic           TEXT DEFAULT '',
    content_pattern TEXT DEFAULT '',
    has_image       INTEGER DEFAULT 0,
    has_video       INTEGER DEFAULT 0,
    is_thread       INTEGER DEFAULT 0,
    hashtags        TEXT DEFAULT '',
    post_url        TEXT DEFAULT '',
    likes           INTEGER DEFAULT 0,
    retweets        INTEGER DEFAULT 0,
    replies         INTEGER DEFAULT 0,
    bookmarks       INTEGER DEFAULT 0,
    views           INTEGER DEFAULT 0,
    eng_rate        REAL DEFAULT 0.0,
    measured_at     TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (handle) REFERENCES x_accounts(handle)
);

-- note アカウント
CREATE TABLE IF NOT EXISTS note_accounts (
    handle          TEXT PRIMARY KEY,
    name            TEXT DEFAULT '',
    category        TEXT DEFAULT '',
    bio             TEXT DEFAULT '',
    note            TEXT DEFAULT '',
    account_type    TEXT DEFAULT 'benchmark',
    fork_direction  TEXT DEFAULT '',
    ng_reason       TEXT DEFAULT '',
    cpt_score       TEXT DEFAULT '',
    is_active       INTEGER DEFAULT 1,
    added_at        TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- note 記事（競合）
CREATE TABLE IF NOT EXISTS note_posts (
    article_id      TEXT PRIMARY KEY,
    handle          TEXT NOT NULL,
    date            TEXT NOT NULL,
    day             TEXT NOT NULL DEFAULT '',
    title           TEXT DEFAULT '',
    content_type    TEXT DEFAULT '',
    treatment       TEXT DEFAULT '',
    char_count      INTEGER DEFAULT 0,
    has_image       INTEGER DEFAULT 0,
    hashtags        TEXT DEFAULT '',
    article_url     TEXT DEFAULT '',
    views           INTEGER DEFAULT 0,
    likes           INTEGER DEFAULT 0,
    comments        INTEGER DEFAULT 0,
    measured_at     TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (handle) REFERENCES note_accounts(handle)
);

-- ルール（共通）
CREATE TABLE IF NOT EXISTS rules (
    rule_id     TEXT PRIMARY KEY,
    category    TEXT NOT NULL,
    description TEXT NOT NULL,
    value       TEXT NOT NULL,
    enabled     INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_x_posts_handle ON x_posts(handle);
CREATE INDEX IF NOT EXISTS idx_x_posts_date ON x_posts(date);
CREATE INDEX IF NOT EXISTS idx_x_posts_topic ON x_posts(topic);
CREATE INDEX IF NOT EXISTS idx_x_posts_format ON x_posts(format);
CREATE INDEX IF NOT EXISTS idx_note_posts_handle ON note_posts(handle);
CREATE INDEX IF NOT EXISTS idx_note_posts_date ON note_posts(date);
"""

# ── マイグレーション ────────────────────────────────────
# 旧 accounts/posts テーブルから新テーブルへのデータ移行

MIGRATION_SQL = """
-- 旧 accounts → x_accounts に X データ移行
INSERT OR IGNORE INTO x_accounts
    (handle, name, category, bio, followers, following, note,
     account_type, fork_direction, ng_reason, is_active, added_at, updated_at)
SELECT handle, name, category, bio, followers, following, note,
       COALESCE(account_type, 'benchmark'),
       COALESCE(fork_direction, ''),
       COALESCE(ng_reason, ''),
       is_active, added_at, updated_at
FROM accounts
WHERE COALESCE(platform, 'x') = 'x';

-- 旧 accounts → note_accounts に note データ移行
INSERT OR IGNORE INTO note_accounts
    (handle, name, category, bio, note,
     account_type, fork_direction, ng_reason, is_active, added_at, updated_at)
SELECT handle, name, category, bio, note,
       COALESCE(account_type, 'benchmark'),
       COALESCE(fork_direction, ''),
       COALESCE(ng_reason, ''),
       is_active, added_at, updated_at
FROM accounts
WHERE platform = 'note';

-- 旧 posts → x_posts に移行
INSERT OR IGNORE INTO x_posts
    (post_id, handle, date, day, text, format, topic, content_pattern,
     has_image, has_video, is_thread, hashtags, post_url,
     likes, retweets, replies, bookmarks, views, eng_rate, measured_at, created_at)
SELECT post_id, handle, date, day, text, format, topic, content_pattern,
       has_image, has_video, is_thread, hashtags, post_url,
       likes, retweets, replies, bookmarks, views, eng_rate, measured_at, created_at
FROM posts;
"""

DEFAULT_RULES: list[tuple[str, str, str, str]] = [
    ("benchmark_interval_days", "benchmark", "ベンチマーク実施間隔（日数）", "30"),
    ("min_views_for_viral", "analysis", "バズ判定の最低views数", "10000"),
    ("min_likes_for_notable", "analysis", "注目判定の最低likes数", "100"),
    ("news_check_interval_hours", "news", "ニュースソース巡回間隔（時間）", "12"),
    ("morning_trend_post_time", "news", "朝トレンド投稿の目標時間帯", "07:00-09:00"),
    ("ng_check_before_publish", "quality", "公開前にNG判定チェックリストを実行", "1"),
    ("growth_daily_replies", "growth", "1日のリプライ目標数", "80"),
    ("growth_daily_posts", "growth", "1日の投稿目標数", "3"),
    ("growth_quote_rt_per_week", "growth", "週の引用RT目標数", "10"),
]


# ── DB接続 ──────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def init_db(conn: sqlite3.Connection) -> None:
    # 新テーブル作成
    conn.executescript(CREATE_TABLES)

    # 旧テーブルからの移行（旧 accounts テーブルが存在する場合のみ）
    if _table_exists(conn, "accounts"):
        try:
            conn.executescript(MIGRATION_SQL)
        except sqlite3.OperationalError:
            pass  # カラム不足などの場合はスキップ
        # 旧テーブルをリネーム（バックアップ）
        for old in ("accounts", "posts"):
            if _table_exists(conn, old):
                bak = f"_bak_{old}"
                if not _table_exists(conn, bak):
                    conn.execute(f"ALTER TABLE {old} RENAME TO {bak}")

    # デフォルトルール挿入
    for rule_id, cat, desc, val in DEFAULT_RULES:
        conn.execute(
            "INSERT OR IGNORE INTO rules (rule_id, category, description, value) VALUES (?,?,?,?)",
            (rule_id, cat, desc, val),
        )
    conn.commit()


# ── ヘルパー ──────────────────────────────────────────────

def _acct_table(platform: str) -> str:
    return "x_accounts" if platform == "x" else "note_accounts"


def _post_table(platform: str) -> str:
    return "x_posts" if platform == "x" else "note_posts"


def _require_platform(args: argparse.Namespace) -> str:
    p = getattr(args, "platform", None)
    if not p:
        print("  ✗ --platform (-p) x|note を指定してください")
        sys.exit(1)
    return p


# ── ルール ──────────────────────────────────────────────

def get_rule(conn: sqlite3.Connection, rule_id: str) -> str | None:
    row = conn.execute(
        "SELECT value FROM rules WHERE rule_id=? AND enabled=1", (rule_id,)
    ).fetchone()
    return row["value"] if row else None


def manage_rules(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    if args.set:
        parts = args.set.split("=", 1)
        if len(parts) == 2:
            rid, val = parts
            cur = conn.execute("UPDATE rules SET value=? WHERE rule_id=?", (val, rid))
            if cur.rowcount:
                conn.commit()
                print(f"  ✓ {rid} = {val}")
            else:
                print(f"  ✗ ルール '{rid}' が見つかりません")
        return
    if args.toggle:
        rid = args.toggle
        row = conn.execute("SELECT enabled FROM rules WHERE rule_id=?", (rid,)).fetchone()
        if row:
            new_val = 0 if row["enabled"] else 1
            conn.execute("UPDATE rules SET enabled=? WHERE rule_id=?", (new_val, rid))
            conn.commit()
            print(f"  ✓ {rid} → {'ON' if new_val else 'OFF'}")
        else:
            print(f"  ✗ ルール '{rid}' が見つかりません")
        return

    rows = conn.execute("SELECT * FROM rules ORDER BY category, rule_id").fetchall()
    print(f"  {'ID':<35} {'Cat':<12} {'Value':>8}  {'On':>3} Description")
    print(f"  {'-'*80}")
    for r in rows:
        on = "✓" if r["enabled"] else "✗"
        print(f"  {r['rule_id']:<35} {r['category']:<12} {r['value']:>8}  {on:>3} {r['description']}")


# ── アカウント管理 ──────────────────────────────────────

def add_account(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    platform = _require_platform(args)
    handle = args.handle.lstrip("@")
    acct_type = getattr(args, "type", "benchmark") or "benchmark"
    fork_dir = getattr(args, "fork_direction", "") or ""
    ng_reason = getattr(args, "ng_reason", "") or ""
    table = _acct_table(platform)

    if platform == "x":
        conn.execute(
            f"""INSERT OR REPLACE INTO {table}
               (handle, name, category, bio, followers, following, note,
                account_type, fork_direction, ng_reason, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?, datetime('now','localtime'))""",
            (handle, args.name, args.category, args.bio,
             args.followers, args.following, args.note, acct_type,
             fork_dir, ng_reason),
        )
    else:
        cpt = getattr(args, "cpt", "") or ""
        conn.execute(
            f"""INSERT OR REPLACE INTO {table}
               (handle, name, category, bio, note,
                account_type, fork_direction, ng_reason, cpt_score, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?, datetime('now','localtime'))""",
            (handle, args.name, args.category, args.bio,
             args.note, acct_type, fork_dir, ng_reason, cpt),
        )
    conn.commit()
    print(f"  ✓ @{handle} [{platform}] を登録/更新しました")


def list_accounts(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    platform = _require_platform(args)
    table = _acct_table(platform)
    acct_filter = getattr(args, "type", "") or ""

    conditions: list[str] = []
    params: list[Any] = []
    if acct_filter:
        conditions.append("account_type=?")
        params.append(acct_filter)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    if platform == "x":
        rows = conn.execute(
            f"SELECT * FROM {table} {where} ORDER BY followers DESC", params
        ).fetchall()
        if not rows:
            print("  アカウント未登録")
            return
        type_label = f" ({acct_filter})" if acct_filter else ""
        print(f"\n  ── X アカウント{type_label} ──\n")
        print(f"  {'Handle':<25} {'Name':<20} {'Category':<15} {'Followers':>10} {'Type':>10}")
        print(f"  {'-'*85}")
        for r in rows:
            print(f"  @{r['handle']:<24} {r['name']:<20} {r['category']:<15} {r['followers']:>10,} {r['account_type']:>10}")
    else:
        rows = conn.execute(
            f"SELECT * FROM {table} {where} ORDER BY handle", params
        ).fetchall()
        if not rows:
            print("  アカウント未登録")
            return
        type_label = f" ({acct_filter})" if acct_filter else ""
        print(f"\n  ── note アカウント{type_label} ──\n")
        print(f"  {'Handle':<25} {'Name':<20} {'Category':<15} {'C×P×T':<12} {'Type':>10}")
        print(f"  {'-'*87}")
        for r in rows:
            cpt = r["cpt_score"] if r["cpt_score"] else ""
            print(f"  @{r['handle']:<24} {r['name']:<20} {r['category']:<15} {cpt:<12} {r['account_type']:>10}")

    print(f"\n  計 {len(rows)} 件")

    # 投稿数集計
    post_table = _post_table(platform)
    rows2 = conn.execute(
        f"""SELECT a.handle, COUNT(p.rowid) as cnt,
           COALESCE(AVG(p.likes),0) as avg_likes,
           COALESCE(AVG(p.views),0) as avg_views,
           COALESCE(MAX(p.likes),0) as max_likes
           FROM {table} a LEFT JOIN {post_table} p ON a.handle=p.handle
           {where}
           GROUP BY a.handle ORDER BY avg_likes DESC""", params
    ).fetchall()
    if any(r["cnt"] > 0 for r in rows2):
        print(f"\n  {'Handle':<25} {'Posts':>6} {'AvgLikes':>10} {'AvgViews':>12} {'MaxLikes':>10}")
        print(f"  {'-'*70}")
        for r in rows2:
            if r["cnt"] > 0:
                print(f"  @{r['handle']:<24} {r['cnt']:>6} {r['avg_likes']:>10.0f} {r['avg_views']:>12.0f} {r['max_likes']:>10}")


# ── X 投稿管理 ────────────────────────────────────────────

def _calc_x_eng_rate(likes: int, retweets: int, replies: int, bookmarks: int, views: int) -> float:
    if views <= 0:
        return 0.0
    return (likes + retweets + replies + bookmarks) / views * 100


def add_x_post(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    handle = args.handle.lstrip("@")
    acct = conn.execute("SELECT handle FROM x_accounts WHERE handle=?", (handle,)).fetchone()
    if not acct:
        print(f"  ⚠ @{handle} は x_accounts に未登録です。先に add-account -p x してください。")

    day = args.day
    if not day and args.date:
        try:
            dt = datetime.strptime(args.date, "%Y-%m-%d")
            day = DAY_MAP.get(dt.weekday(), "")
        except ValueError:
            pass

    eng_rate = _calc_x_eng_rate(args.likes, args.retweets, args.replies, args.bookmarks, args.views)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn.execute(
        """INSERT OR REPLACE INTO x_posts
           (post_id, handle, date, day, text, format, topic, content_pattern,
            has_image, has_video, is_thread, hashtags, post_url,
            likes, retweets, replies, bookmarks, views, eng_rate, measured_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (args.post_id, handle, args.date, day, args.text, args.format,
         args.topic, args.content_pattern,
         args.has_image, args.has_video, args.is_thread, args.hashtags, args.url,
         args.likes, args.retweets, args.replies, args.bookmarks, args.views,
         eng_rate, now),
    )
    conn.commit()
    print(f"  ✓ x_post {args.post_id} (@{handle}) を登録しました (eng_rate={eng_rate:.2f}%)")


# ── note 記事管理 ──────────────────────────────────────────

def add_note_post(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    handle = args.handle.lstrip("@")
    acct = conn.execute("SELECT handle FROM note_accounts WHERE handle=?", (handle,)).fetchone()
    if not acct:
        print(f"  ⚠ @{handle} は note_accounts に未登録です。先に add-account -p note してください。")

    day = args.day
    if not day and args.date:
        try:
            dt = datetime.strptime(args.date, "%Y-%m-%d")
            day = DAY_MAP.get(dt.weekday(), "")
        except ValueError:
            pass

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute(
        """INSERT OR REPLACE INTO note_posts
           (article_id, handle, date, day, title, content_type, treatment,
            char_count, has_image, hashtags, article_url,
            views, likes, comments, measured_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (args.article_id, handle, args.date, day, args.title,
         args.content_type, args.treatment,
         args.chars, args.has_image, args.hashtags, args.url,
         args.views, args.likes, args.comments, now),
    )
    conn.commit()
    print(f"  ✓ note_post {args.article_id} (@{handle}) を登録しました")


# ── 投稿追加ディスパッチ ──────────────────────────────────

def add_post(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    platform = _require_platform(args)
    if platform == "x":
        add_x_post(conn, args)
    else:
        add_note_post(conn, args)


# ── メトリクス更新 ────────────────────────────────────────

def update_metrics(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    # X の post_id で検索
    post_id = getattr(args, "post_id", None)
    article_id = getattr(args, "article_id", None)

    if post_id:
        row = conn.execute("SELECT * FROM x_posts WHERE post_id=?", (post_id,)).fetchone()
        if not row:
            print(f"  ✗ x_posts に post_id={post_id} が見つかりません")
            return
        likes = args.likes if args.likes else row["likes"]
        retweets = args.retweets if args.retweets else row["retweets"]
        replies = args.replies if args.replies else row["replies"]
        bookmarks = args.bookmarks if args.bookmarks else row["bookmarks"]
        views = args.views if args.views else row["views"]
        eng_rate = _calc_x_eng_rate(likes, retweets, replies, bookmarks, views)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute(
            """UPDATE x_posts SET likes=?, retweets=?, replies=?, bookmarks=?, views=?,
               eng_rate=?, measured_at=? WHERE post_id=?""",
            (likes, retweets, replies, bookmarks, views, eng_rate, now, post_id),
        )
        conn.commit()
        print(f"  ✓ x_post {post_id} メトリクス更新 (eng_rate={eng_rate:.2f}%)")

    elif article_id:
        row = conn.execute("SELECT * FROM note_posts WHERE article_id=?", (article_id,)).fetchone()
        if not row:
            print(f"  ✗ note_posts に article_id={article_id} が見つかりません")
            return
        views = args.views if args.views else row["views"]
        likes = args.likes if args.likes else row["likes"]
        comments = args.comments if args.comments else row["comments"]
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute(
            """UPDATE note_posts SET views=?, likes=?, comments=?, measured_at=?
               WHERE article_id=?""",
            (views, likes, comments, now, article_id),
        )
        conn.commit()
        print(f"  ✓ note_post {article_id} メトリクス更新")
    else:
        print("  ✗ --post-id または --article-id を指定してください")


# ── 表示 ──────────────────────────────────────────────────

def show_post(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    post_id = getattr(args, "post_id", None)
    article_id = getattr(args, "article_id", None)

    row = None
    if post_id:
        row = conn.execute("SELECT * FROM x_posts WHERE post_id=?", (post_id,)).fetchone()
    elif article_id:
        row = conn.execute("SELECT * FROM note_posts WHERE article_id=?", (article_id,)).fetchone()

    if not row:
        print(f"  ✗ 見つかりません")
        return
    print()
    for key in row.keys():
        print(f"  {key:<18} {row[key]}")


def list_posts(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    platform = _require_platform(args)
    conditions: list[str] = []
    params: list[Any] = []

    if args.handle:
        conditions.append("handle=?")
        params.append(args.handle.lstrip("@"))
    if args.days:
        cutoff = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        conditions.append("date>=?")
        params.append(cutoff)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    if platform == "x":
        rows = conn.execute(
            f"SELECT * FROM x_posts {where} ORDER BY date DESC, likes DESC", params
        ).fetchall()
        if not rows:
            print("  投稿なし")
            return
        print(f"\n  ── X 投稿一覧 ──\n")
        print(f"  {'Date':<12} {'Handle':<20} {'Likes':>7} {'RT':>6} {'Views':>10} {'EngR':>6} {'Topic'}")
        print(f"  {'-'*80}")
        for r in rows:
            print(
                f"  {r['date']:<12} @{r['handle']:<19} {r['likes']:>7,} {r['retweets']:>6,} "
                f"{r['views']:>10,} {r['eng_rate']:>5.1f}% {r['topic'][:30]}"
            )
    else:
        rows = conn.execute(
            f"SELECT * FROM note_posts {where} ORDER BY date DESC, likes DESC", params
        ).fetchall()
        if not rows:
            print("  記事なし")
            return
        print(f"\n  ── note 記事一覧 ──\n")
        print(f"  {'Date':<12} {'Handle':<20} {'Likes':>6} {'Views':>8} {'Cmts':>5} {'C×P':<10} {'Title'}")
        print(f"  {'-'*80}")
        for r in rows:
            print(
                f"  {r['date']:<12} @{r['handle']:<19} {r['likes']:>6,} {r['views']:>8,} "
                f"{r['comments']:>5,} {r['content_type']:<10} {r['title'][:25]}"
            )

    print(f"\n  計 {len(rows)} 件")


# ── レポート ────────────────────────────────────────────

def _print_x_group_report(rows: list[sqlite3.Row], group_col: str) -> None:
    if not rows:
        print("  データなし")
        return
    print(f"  {group_col:<25} {'Posts':>6} {'AvgLikes':>10} {'AvgRT':>8} {'AvgViews':>12} {'AvgEng%':>8} {'MaxLikes':>10}")
    print(f"  {'-'*85}")
    for r in rows:
        print(
            f"  {str(r['grp']):<25} {r['cnt']:>6} {r['avg_likes']:>10.0f} "
            f"{r['avg_rt']:>8.0f} {r['avg_views']:>12.0f} {r['avg_eng']:>7.2f}% {r['max_likes']:>10}"
        )


def _print_note_group_report(rows: list[sqlite3.Row], group_col: str) -> None:
    if not rows:
        print("  データなし")
        return
    print(f"  {group_col:<25} {'Posts':>6} {'AvgLikes':>10} {'AvgViews':>10} {'AvgCmts':>8} {'MaxLikes':>10}")
    print(f"  {'-'*75}")
    for r in rows:
        print(
            f"  {str(r['grp']):<25} {r['cnt']:>6} {r['avg_likes']:>10.0f} "
            f"{r['avg_views']:>10.0f} {r['avg_cmts']:>8.0f} {r['max_likes']:>10}"
        )


def report(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    platform = _require_platform(args)

    if args.monthly is not None:
        _report_monthly(conn, platform, args.monthly)
        return

    if args.ranking:
        _report_ranking(conn, platform)
        return

    if args.patterns:
        _report_patterns(conn, platform)
        return

    if args.by:
        _report_by_group(conn, platform, args.by)
        return

    _report_summary(conn, platform)


def _report_summary(conn: sqlite3.Connection, platform: str) -> None:
    if platform == "x":
        row = conn.execute(
            """SELECT COUNT(*) as cnt, COUNT(DISTINCT handle) as accts,
               AVG(likes) as avg_likes, AVG(retweets) as avg_rt,
               AVG(views) as avg_views, AVG(eng_rate) as avg_eng,
               MAX(likes) as max_likes, MAX(views) as max_views,
               MIN(date) as first_date, MAX(date) as last_date
               FROM x_posts"""
        ).fetchone()
        if not row or row["cnt"] == 0:
            print("  データなし")
            return
        print(f"\n  ── X 競合ベンチマーク サマリ ──\n")
        print(f"  期間:       {row['first_date']} ~ {row['last_date']}")
        print(f"  アカウント: {row['accts']}")
        print(f"  投稿数:     {row['cnt']}")
        print(f"  平均Likes:  {row['avg_likes']:.0f}")
        print(f"  平均RT:     {row['avg_rt']:.0f}")
        print(f"  平均Views:  {row['avg_views']:.0f}")
        print(f"  平均Eng%:   {row['avg_eng']:.2f}%")
        print(f"  最大Likes:  {row['max_likes']}")
        print(f"  最大Views:  {row['max_views']}")

        # 自アカウントとの比較
        x_db = ROOT / "knowledge" / "data" / "x_posts.db"
        if x_db.exists():
            xconn = sqlite3.connect(str(x_db))
            xconn.row_factory = sqlite3.Row
            xrow = xconn.execute(
                """SELECT COUNT(*) as cnt, AVG(impressions) as avg_imp,
                   AVG(engagements) as avg_eng, AVG(likes) as avg_likes
                   FROM posts"""
            ).fetchone()
            xconn.close()
            if xrow and xrow["cnt"] > 0:
                print(f"\n  ── 自アカウント比較 ──")
                print(f"  自投稿数:     {xrow['cnt']}")
                print(f"  自平均Views:  {xrow['avg_imp']:.0f}")
                print(f"  自平均Likes:  {xrow['avg_likes']:.0f}")
                ratio = row["avg_likes"] / max(xrow["avg_likes"], 1)
                print(f"  Likes比率:    競合は自分の {ratio:.1f}倍")
    else:
        row = conn.execute(
            """SELECT COUNT(*) as cnt, COUNT(DISTINCT handle) as accts,
               AVG(likes) as avg_likes, AVG(views) as avg_views,
               AVG(comments) as avg_cmts,
               MAX(likes) as max_likes, MAX(views) as max_views,
               MIN(date) as first_date, MAX(date) as last_date
               FROM note_posts"""
        ).fetchone()
        if not row or row["cnt"] == 0:
            print("  データなし")
            return
        print(f"\n  ── note 競合ベンチマーク サマリ ──\n")
        print(f"  期間:       {row['first_date']} ~ {row['last_date']}")
        print(f"  アカウント: {row['accts']}")
        print(f"  記事数:     {row['cnt']}")
        print(f"  平均スキ:   {row['avg_likes']:.0f}")
        print(f"  平均PV:     {row['avg_views']:.0f}")
        print(f"  平均コメント: {row['avg_cmts']:.1f}")
        print(f"  最大スキ:   {row['max_likes']}")
        print(f"  最大PV:     {row['max_views']}")

        # 自アカウントとの比較
        note_db = ROOT / "knowledge" / "data" / "note_articles.db"
        if note_db.exists():
            nconn = sqlite3.connect(str(note_db))
            nconn.row_factory = sqlite3.Row
            nrow = nconn.execute(
                """SELECT COUNT(*) as cnt, AVG(views) as avg_views,
                   AVG(likes) as avg_likes
                   FROM articles"""
            ).fetchone()
            nconn.close()
            if nrow and nrow["cnt"] > 0:
                print(f"\n  ── 自アカウント比較 ──")
                print(f"  自記事数:     {nrow['cnt']}")
                print(f"  自平均PV:     {nrow['avg_views']:.0f}")
                print(f"  自平均スキ:   {nrow['avg_likes']:.0f}")
                ratio = row["avg_likes"] / max(nrow["avg_likes"], 1)
                print(f"  スキ比率:     競合は自分の {ratio:.1f}倍")


def _report_ranking(conn: sqlite3.Connection, platform: str) -> None:
    if platform == "x":
        rows = conn.execute(
            """SELECT p.*, a.name, a.category FROM x_posts p
               LEFT JOIN x_accounts a ON p.handle=a.handle
               ORDER BY p.likes DESC LIMIT 20"""
        ).fetchall()
        if not rows:
            print("  データなし")
            return
        print(f"\n  ── X エンゲージメント TOP 20 ──\n")
        print(f"  {'#':>3} {'Likes':>8} {'Views':>10} {'Eng%':>6} {'Handle':<20} {'Topic'}")
        print(f"  {'-'*70}")
        for i, r in enumerate(rows, 1):
            print(
                f"  {i:>3} {r['likes']:>8,} {r['views']:>10,} {r['eng_rate']:>5.1f}% "
                f"@{r['handle']:<19} {r['topic'][:30]}"
            )
    else:
        rows = conn.execute(
            """SELECT p.*, a.name, a.category FROM note_posts p
               LEFT JOIN note_accounts a ON p.handle=a.handle
               ORDER BY p.likes DESC LIMIT 20"""
        ).fetchall()
        if not rows:
            print("  データなし")
            return
        print(f"\n  ── note スキ TOP 20 ──\n")
        print(f"  {'#':>3} {'Likes':>6} {'Views':>8} {'Cmts':>5} {'Handle':<20} {'Title'}")
        print(f"  {'-'*70}")
        for i, r in enumerate(rows, 1):
            print(
                f"  {i:>3} {r['likes']:>6,} {r['views']:>8,} {r['comments']:>5,} "
                f"@{r['handle']:<19} {r['title'][:25]}"
            )


def _report_by_group(conn: sqlite3.Connection, platform: str, by: str) -> None:
    if platform == "x":
        col_map = {
            "account": "handle", "format": "format", "topic": "topic",
            "category": "a.category", "day": "day", "pattern": "content_pattern",
        }
        col = col_map.get(by, by)
        if by == "category":
            rows = conn.execute(
                f"""SELECT a.category as grp, COUNT(*) as cnt,
                    AVG(p.likes) as avg_likes, AVG(p.retweets) as avg_rt,
                    AVG(p.views) as avg_views, AVG(p.eng_rate) as avg_eng,
                    MAX(p.likes) as max_likes
                    FROM x_posts p JOIN x_accounts a ON p.handle=a.handle
                    GROUP BY a.category ORDER BY avg_likes DESC"""
            ).fetchall()
        else:
            rows = conn.execute(
                f"""SELECT {col} as grp, COUNT(*) as cnt,
                    AVG(likes) as avg_likes, AVG(retweets) as avg_rt,
                    AVG(views) as avg_views, AVG(eng_rate) as avg_eng,
                    MAX(likes) as max_likes
                    FROM x_posts GROUP BY {col} ORDER BY avg_likes DESC"""
            ).fetchall()
        print(f"\n  ── X {by} 別レポート ──\n")
        _print_x_group_report(rows, by.title())
    else:
        col_map = {
            "account": "handle", "content-type": "content_type",
            "treatment": "treatment", "category": "a.category", "day": "day",
        }
        col = col_map.get(by, by)
        if by == "category":
            rows = conn.execute(
                f"""SELECT a.category as grp, COUNT(*) as cnt,
                    AVG(p.likes) as avg_likes, AVG(p.views) as avg_views,
                    AVG(p.comments) as avg_cmts, MAX(p.likes) as max_likes
                    FROM note_posts p JOIN note_accounts a ON p.handle=a.handle
                    GROUP BY a.category ORDER BY avg_likes DESC"""
            ).fetchall()
        else:
            rows = conn.execute(
                f"""SELECT {col} as grp, COUNT(*) as cnt,
                    AVG(likes) as avg_likes, AVG(views) as avg_views,
                    AVG(comments) as avg_cmts, MAX(likes) as max_likes
                    FROM note_posts GROUP BY {col} ORDER BY avg_likes DESC"""
            ).fetchall()
        print(f"\n  ── note {by} 別レポート ──\n")
        _print_note_group_report(rows, by.title())


def _report_patterns(conn: sqlite3.Connection, platform: str) -> None:
    if platform == "x":
        print(f"\n  ── X 伸びてるパターン分析 ──\n")

        print("  [フォーマット別パフォーマンス]")
        rows = conn.execute(
            """SELECT format as grp, COUNT(*) as cnt,
               AVG(likes) as avg_likes, AVG(retweets) as avg_rt,
               AVG(views) as avg_views, AVG(eng_rate) as avg_eng,
               MAX(likes) as max_likes
               FROM x_posts WHERE format != '' GROUP BY format ORDER BY avg_likes DESC"""
        ).fetchall()
        _print_x_group_report(rows, "Format")

        print("\n  [メディア有無別]")
        rows = conn.execute(
            """SELECT CASE WHEN has_image=1 THEN '画像あり'
                      WHEN has_video=1 THEN '動画あり'
                      ELSE 'テキストのみ' END as grp,
               COUNT(*) as cnt,
               AVG(likes) as avg_likes, AVG(retweets) as avg_rt,
               AVG(views) as avg_views, AVG(eng_rate) as avg_eng,
               MAX(likes) as max_likes
               FROM x_posts GROUP BY grp ORDER BY avg_likes DESC"""
        ).fetchall()
        _print_x_group_report(rows, "Media")

        print("\n  [スレッド vs 単発]")
        rows = conn.execute(
            """SELECT CASE WHEN is_thread=1 THEN 'スレッド' ELSE '単発' END as grp,
               COUNT(*) as cnt,
               AVG(likes) as avg_likes, AVG(retweets) as avg_rt,
               AVG(views) as avg_views, AVG(eng_rate) as avg_eng,
               MAX(likes) as max_likes
               FROM x_posts GROUP BY grp ORDER BY avg_likes DESC"""
        ).fetchall()
        _print_x_group_report(rows, "Type")

        min_views = get_rule(conn, "min_views_for_viral")
        threshold = int(min_views) if min_views else 10000
        viral = conn.execute(
            """SELECT handle, post_id, date, topic, format, likes, views, eng_rate
               FROM x_posts WHERE views >= ? ORDER BY likes DESC LIMIT 10""",
            (threshold,)
        ).fetchall()
        if viral:
            print(f"\n  [バズ投稿 (views≥{threshold:,})]")
            print(f"  {'Handle':<20} {'Likes':>8} {'Views':>10} {'Eng%':>6} {'Topic'}")
            print(f"  {'-'*65}")
            for r in viral:
                print(f"  @{r['handle']:<19} {r['likes']:>8,} {r['views']:>10,} {r['eng_rate']:>5.1f}% {r['topic'][:30]}")
    else:
        print(f"\n  ── note 伸びてるパターン分析 ──\n")

        print("  [コンテンツタイプ別]")
        rows = conn.execute(
            """SELECT content_type as grp, COUNT(*) as cnt,
               AVG(likes) as avg_likes, AVG(views) as avg_views,
               AVG(comments) as avg_cmts, MAX(likes) as max_likes
               FROM note_posts WHERE content_type != '' GROUP BY content_type ORDER BY avg_likes DESC"""
        ).fetchall()
        _print_note_group_report(rows, "ContentType")

        print("\n  [加工方法(T軸)別]")
        rows = conn.execute(
            """SELECT treatment as grp, COUNT(*) as cnt,
               AVG(likes) as avg_likes, AVG(views) as avg_views,
               AVG(comments) as avg_cmts, MAX(likes) as max_likes
               FROM note_posts WHERE treatment != '' GROUP BY treatment ORDER BY avg_likes DESC"""
        ).fetchall()
        _print_note_group_report(rows, "Treatment")

        print("\n  [文字数帯別]")
        rows = conn.execute(
            """SELECT CASE
                  WHEN char_count < 1000 THEN '~1000字'
                  WHEN char_count < 2000 THEN '1000~2000字'
                  WHEN char_count < 3000 THEN '2000~3000字'
                  WHEN char_count < 5000 THEN '3000~5000字'
                  ELSE '5000字~' END as grp,
               COUNT(*) as cnt,
               AVG(likes) as avg_likes, AVG(views) as avg_views,
               AVG(comments) as avg_cmts, MAX(likes) as max_likes
               FROM note_posts WHERE char_count > 0 GROUP BY grp ORDER BY avg_likes DESC"""
        ).fetchall()
        _print_note_group_report(rows, "CharRange")


def _report_monthly(conn: sqlite3.Connection, platform: str, month: str) -> None:
    table = _post_table(platform)
    label = "X" if platform == "x" else "note"

    if platform == "x":
        if month:
            rows = conn.execute(
                f"""SELECT handle as grp, COUNT(*) as cnt,
                   AVG(likes) as avg_likes, AVG(retweets) as avg_rt,
                   AVG(views) as avg_views, AVG(eng_rate) as avg_eng,
                   MAX(likes) as max_likes
                   FROM {table} WHERE date LIKE ? GROUP BY handle ORDER BY avg_likes DESC""",
                (f"{month}%",)
            ).fetchall()
            print(f"\n  ── {label} {month} アカウント別 ──\n")
            _print_x_group_report(rows, "Handle")
        else:
            rows = conn.execute(
                f"""SELECT substr(date,1,7) as grp, COUNT(*) as cnt,
                   AVG(likes) as avg_likes, AVG(retweets) as avg_rt,
                   AVG(views) as avg_views, AVG(eng_rate) as avg_eng,
                   MAX(likes) as max_likes
                   FROM {table} GROUP BY grp ORDER BY grp DESC"""
            ).fetchall()
            print(f"\n  ── {label} 月別サマリ ──\n")
            _print_x_group_report(rows, "Month")
    else:
        if month:
            rows = conn.execute(
                f"""SELECT handle as grp, COUNT(*) as cnt,
                   AVG(likes) as avg_likes, AVG(views) as avg_views,
                   AVG(comments) as avg_cmts, MAX(likes) as max_likes
                   FROM {table} WHERE date LIKE ? GROUP BY handle ORDER BY avg_likes DESC""",
                (f"{month}%",)
            ).fetchall()
            print(f"\n  ── {label} {month} アカウント別 ──\n")
            _print_note_group_report(rows, "Handle")
        else:
            rows = conn.execute(
                f"""SELECT substr(date,1,7) as grp, COUNT(*) as cnt,
                   AVG(likes) as avg_likes, AVG(views) as avg_views,
                   AVG(comments) as avg_cmts, MAX(likes) as max_likes
                   FROM {table} GROUP BY grp ORDER BY grp DESC"""
            ).fetchall()
            print(f"\n  ── {label} 月別サマリ ──\n")
            _print_note_group_report(rows, "Month")


# ── CLI ───────────────────────────────────────────────

def _add_platform_arg(parser: argparse.ArgumentParser, required: bool = True) -> None:
    parser.add_argument("-p", "--platform", required=required, choices=["x", "note"],
                        help="プラットフォーム: x / note")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="競合コンテンツベンチマーク — SQLite管理CLI（X / note テーブル分離版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    sub.add_parser("init", help="Initialize database")

    # add-account
    p_acct = sub.add_parser("add-account", help="Add/update competitor account")
    _add_platform_arg(p_acct)
    p_acct.add_argument("--handle", required=True)
    p_acct.add_argument("--name", default="")
    p_acct.add_argument("--category", default="")
    p_acct.add_argument("--bio", default="")
    p_acct.add_argument("--note", default="")
    p_acct.add_argument("--type", default="benchmark",
                        choices=["benchmark", "ng", "news", "growth", "visual", "engagement"])
    p_acct.add_argument("--fork-direction", default="", dest="fork_direction")
    p_acct.add_argument("--ng-reason", default="", dest="ng_reason")
    # X 固有
    p_acct.add_argument("--followers", type=int, default=0)
    p_acct.add_argument("--following", type=int, default=0)
    # note 固有
    p_acct.add_argument("--cpt", default="", help="C×P×T スコア（note用）")

    # accounts
    p_accounts = sub.add_parser("accounts", help="List competitor accounts")
    _add_platform_arg(p_accounts)
    p_accounts.add_argument("--type", default="")

    # add (post/article)
    p_add = sub.add_parser("add", help="Add a competitor post/article")
    _add_platform_arg(p_add)
    p_add.add_argument("--handle", required=True)
    p_add.add_argument("--date", required=True)
    p_add.add_argument("--day", default="")
    p_add.add_argument("--has-image", type=int, default=0)
    p_add.add_argument("--hashtags", default="")
    p_add.add_argument("--url", default="")
    p_add.add_argument("--likes", type=int, default=0)
    p_add.add_argument("--views", type=int, default=0)
    # X 固有
    p_add.add_argument("--post-id", default="")
    p_add.add_argument("--text", default="")
    p_add.add_argument("--format", default="")
    p_add.add_argument("--topic", default="")
    p_add.add_argument("--content-pattern", default="")
    p_add.add_argument("--has-video", type=int, default=0)
    p_add.add_argument("--is-thread", type=int, default=0)
    p_add.add_argument("--retweets", type=int, default=0)
    p_add.add_argument("--replies", type=int, default=0)
    p_add.add_argument("--bookmarks", type=int, default=0)
    # note 固有
    p_add.add_argument("--article-id", default="")
    p_add.add_argument("--title", default="")
    p_add.add_argument("--content-type", default="")
    p_add.add_argument("--treatment", default="")
    p_add.add_argument("--chars", type=int, default=0)
    p_add.add_argument("--comments", type=int, default=0)

    # update
    p_upd = sub.add_parser("update", help="Update post/article metrics")
    p_upd.add_argument("--post-id", default="", help="X post ID")
    p_upd.add_argument("--article-id", default="", help="note article ID")
    p_upd.add_argument("--likes", type=int, default=0)
    p_upd.add_argument("--views", type=int, default=0)
    # X 固有
    p_upd.add_argument("--retweets", type=int, default=0)
    p_upd.add_argument("--replies", type=int, default=0)
    p_upd.add_argument("--bookmarks", type=int, default=0)
    # note 固有
    p_upd.add_argument("--comments", type=int, default=0)

    # show
    p_show = sub.add_parser("show", help="Show post/article detail")
    p_show.add_argument("--post-id", default="", help="X post ID")
    p_show.add_argument("--article-id", default="", help="note article ID")

    # list
    p_list = sub.add_parser("list", help="List posts/articles")
    _add_platform_arg(p_list)
    p_list.add_argument("--handle", default="")
    p_list.add_argument("--days", type=int, default=0)

    # report
    p_rep = sub.add_parser("report", help="Generate report")
    _add_platform_arg(p_rep)
    p_rep.add_argument("--by", choices=["account", "format", "topic", "category",
                                        "day", "pattern", "content-type", "treatment"])
    p_rep.add_argument("--ranking", action="store_true")
    p_rep.add_argument("--patterns", action="store_true")
    p_rep.add_argument("--monthly", nargs="?", const="", default=None)

    # rules
    p_rules = sub.add_parser("rules", help="Manage rules")
    p_rules.add_argument("--set", default="")
    p_rules.add_argument("--toggle", default="")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    conn = get_conn()
    init_db(conn)

    commands = {
        "init": lambda c, a: print("DB ready."),
        "add-account": add_account,
        "accounts": list_accounts,
        "add": add_post,
        "update": update_metrics,
        "show": show_post,
        "list": list_posts,
        "report": report,
        "rules": manage_rules,
    }

    try:
        commands[args.command](conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
