"""
X Search スクリプト — xAI API (Grok + X Search) で X の定性分析を行い、結果を YAML に保存する

使い方:
  # 競合分析 — 特定アカウントの投稿テーマ・傾向を要約
  python scripts/x_search.py competitor @handle1 @handle2 --period 30d

  # トレンド検索 — ジャンルキーワードで話題を探す
  python scripts/x_search.py trend "AI 業務効率化" --period 7d

  # トピック調査 — 投稿ネタの反応・切り口を事前調査
  python scripts/x_search.py topic "Claude Codeで議事録"

  # ベンチマーク — platforms.yaml の競合5アカウントを一括分析
  python scripts/x_search.py benchmark --period 30d

  # フリー検索 — 任意のプロンプトで X 検索
  python scripts/x_search.py search "プロンプトエンジニアリング 初心者"

出力:
  - YAML: knowledge/logs/x/research/<type>/YYYY-MM-DD_<slug>.yaml
  - ネタ候補: knowledge/logs/x/research/ideas.yaml に追記
  - コンソール: 要約を表示
"""

import argparse
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Windows cp932 でのUnicodeEncodeError回避
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx
import yaml
from dotenv import load_dotenv

# ── プロジェクト設定 ──────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_KEY = os.getenv("XAI_API_KEY", "")
BASE_URL = "https://api.x.ai/v1"
MODEL = "grok-4-1-fast"  # X Search ツールは grok-4 ファミリーのみ対応

RESEARCH_DIR = ROOT / "knowledge" / "logs" / "x" / "research"
IDEAS_FILE = RESEARCH_DIR / "ideas.yaml"

# platforms.yaml から競合アカウントを読む
def _load_competitive_accounts() -> list[dict]:
    cfg_path = ROOT / "config" / "platforms.yaml"
    if not cfg_path.exists():
        return []
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    accounts = cfg.get("platforms", {}).get("x", {}).get("competitive", {}).get("accounts", [])
    return accounts if isinstance(accounts, list) else []


# ── API 呼び出し ──────────────────────────────────────

def _call_x_search(
    prompt: str,
    *,
    handles: list[str] | None = None,
    excluded_handles: list[str] | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict:
    """xAI Responses API + X Search ツールを呼び出す"""
    if not API_KEY:
        print("ERROR: XAI_API_KEY が設定されていません (.env を確認)")
        sys.exit(1)

    x_search_params: dict = {}
    if handles:
        x_search_params["allowed_x_handles"] = [h.lstrip("@") for h in handles]
    if excluded_handles:
        x_search_params["excluded_x_handles"] = [h.lstrip("@") for h in excluded_handles]
    if from_date:
        x_search_params["from_date"] = from_date
    if to_date:
        x_search_params["to_date"] = to_date

    tool_def: dict = {"type": "x_search"}
    if x_search_params:
        tool_def["x_search"] = x_search_params

    payload = {
        "model": MODEL,
        "tools": [tool_def],
        "input": prompt,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    with httpx.Client(timeout=120) as client:
        resp = client.post(f"{BASE_URL}/responses", json=payload, headers=headers)

    if resp.status_code != 200:
        print(f"ERROR: API returned {resp.status_code}")
        print(resp.text[:500])
        sys.exit(1)

    return resp.json()


def _extract_response(raw: dict) -> tuple[str, list[str]]:
    """API レスポンスからテキストと引用URLを抽出"""
    text = ""
    citations: list[str] = []

    # Responses API 形式
    output = raw.get("output", [])
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict):
                if item.get("type") == "message":
                    content = item.get("content", [])
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "output_text":
                            text += block.get("text", "")
                            for ann in block.get("annotations", []):
                                if ann.get("type") == "url_citation":
                                    url = ann.get("url", "")
                                    if url and url not in citations:
                                        citations.append(url)

    # output_text がトップレベルにある場合
    if not text and "output_text" in raw:
        text = raw["output_text"]

    # テキストからURLを抽出（fallback）
    if not citations and text:
        urls = re.findall(r'https?://x\.com/\S+', text)
        citations = list(dict.fromkeys(urls))

    return text.strip(), citations


# ── 期間パース ────────────────────────────────────────

def _parse_period(period_str: str) -> tuple[str, str]:
    """'7d', '30d', '3m' → (from_date, to_date) ISO形式"""
    today = datetime.now()
    to_date = today.strftime("%Y-%m-%d")

    match = re.match(r"(\d+)([dm])", period_str)
    if not match:
        # デフォルト30日
        from_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        return from_date, to_date

    num, unit = int(match.group(1)), match.group(2)
    if unit == "d":
        delta = timedelta(days=num)
    else:  # m
        delta = timedelta(days=num * 30)

    from_date = (today - delta).strftime("%Y-%m-%d")
    return from_date, to_date


# ── 保存 ──────────────────────────────────────────────

def _slugify(text: str, max_len: int = 40) -> str:
    """ファイル名用スラッグ生成"""
    slug = re.sub(r'[^\w\s-]', '', text)
    slug = re.sub(r'[\s_]+', '-', slug).strip('-')
    return slug[:max_len] or "query"


def _save_result(subdir: str, slug: str, data: dict) -> Path:
    """結果をYAMLに保存"""
    out_dir = RESEARCH_DIR / subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{today}_{slug}.yaml"
    out_path = out_dir / filename

    # 同名ファイルがあれば連番
    if out_path.exists():
        for i in range(2, 100):
            out_path = out_dir / f"{today}_{slug}_{i}.yaml"
            if not out_path.exists():
                break

    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return out_path


def _save_ideas(ideas: list[dict]) -> None:
    """ネタ候補を ideas.yaml に追記"""
    if not ideas:
        return

    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    existing: list[dict] = []
    if IDEAS_FILE.exists():
        with open(IDEAS_FILE, encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, list):
                existing = loaded

    existing.extend(ideas)

    with open(IDEAS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(existing, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


# ── サブコマンド ──────────────────────────────────────

def cmd_competitor(args: argparse.Namespace) -> None:
    """競合アカウントの投稿テーマ・傾向を分析"""
    handles = args.handles
    from_date, to_date = _parse_period(args.period)

    handle_list = ", ".join(f"@{h.lstrip('@')}" for h in handles)
    prompt = f"""以下のXアカウントの最近の投稿を分析してください: {handle_list}

分析項目:
1. 主な投稿テーマ（3-5個）
2. 投稿フォーマットの傾向（テキストのみ/画像付き/スレッド等）
3. エンゲージメントが高い投稿の特徴
4. 投稿頻度の印象
5. 注目すべき投稿（URL付きで最大3件）
6. 自分のアカウント運営に活かせるヒント

日本語で回答してください。"""

    print(f"[competitor] {handle_list} を分析中 ({from_date} ~ {to_date})...")
    raw = _call_x_search(prompt, handles=handles, from_date=from_date, to_date=to_date)
    text, citations = _extract_response(raw)

    result = {
        "type": "competitor",
        "handles": [h.lstrip("@") for h in handles],
        "period": {"from": from_date, "to": to_date},
        "analyzed_at": datetime.now().isoformat(),
        "summary": text,
        "citations": citations,
    }

    slug = _slugify("-".join(h.lstrip("@") for h in handles[:3]))
    path = _save_result("competitor", slug, result)

    print(f"\n{'='*60}")
    print(text[:2000] if text else "(応答なし)")
    if citations:
        print(f"\n引用: {len(citations)}件")
    print(f"{'='*60}")
    print(f"保存: {path.relative_to(ROOT)}")


def cmd_trend(args: argparse.Namespace) -> None:
    """ジャンルのキーワードでトレンドを検索"""
    keyword = args.keyword
    from_date, to_date = _parse_period(args.period)

    prompt = f"""Xで「{keyword}」に関する最近の話題を調べてください。

以下の形式で日本語で回答してください:
1. 盛り上がっているトピック（3-5個、それぞれ簡潔に説明）
2. よく使われているフォーマット・切り口
3. エンゲージメントが高い投稿の共通点
4. 注目すべき投稿（URL付きで最大5件）
5. コンテンツのネタになりそうなアイデア（3個、具体的に）"""

    print(f"[trend] 「{keyword}」のトレンドを検索中 ({from_date} ~ {to_date})...")
    raw = _call_x_search(prompt, from_date=from_date, to_date=to_date)
    text, citations = _extract_response(raw)

    # ネタ候補を抽出して保存
    ideas = [{
        "source": "trend",
        "query": keyword,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "status": "new",
        "raw_ideas": _extract_ideas_from_text(text),
    }]

    result = {
        "type": "trend",
        "keyword": keyword,
        "period": {"from": from_date, "to": to_date},
        "analyzed_at": datetime.now().isoformat(),
        "summary": text,
        "citations": citations,
        "ideas_extracted": ideas[0]["raw_ideas"],
    }

    slug = _slugify(keyword)
    path = _save_result("trend", slug, result)
    _save_ideas(ideas)

    print(f"\n{'='*60}")
    print(text[:2000] if text else "(応答なし)")
    if citations:
        print(f"\n引用: {len(citations)}件")
    print(f"{'='*60}")
    print(f"保存: {path.relative_to(ROOT)}")
    print(f"ネタ候補: {IDEAS_FILE.relative_to(ROOT)} に追記")


def cmd_topic(args: argparse.Namespace) -> None:
    """投稿ネタの反応・切り口を事前調査"""
    topic = args.topic
    from_date, to_date = _parse_period(args.period)

    prompt = f"""Xで「{topic}」について投稿する前のリサーチです。

以下を調べて日本語で回答してください:
1. このトピックに関する既存の投稿の反応（良い/悪い）
2. どんな切り口・表現が刺さっているか
3. 避けるべき表現やアプローチ
4. 差別化できるポイント（まだ誰も言っていない角度）
5. 参考になる投稿（URL付きで最大3件）
6. おすすめの投稿案（140字以内で2パターン）"""

    print(f"[topic] 「{topic}」のトピック調査中 ({from_date} ~ {to_date})...")
    raw = _call_x_search(prompt, from_date=from_date, to_date=to_date)
    text, citations = _extract_response(raw)

    ideas = [{
        "source": "topic",
        "query": topic,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "status": "new",
        "raw_ideas": _extract_ideas_from_text(text),
    }]

    result = {
        "type": "topic",
        "topic": topic,
        "period": {"from": from_date, "to": to_date},
        "analyzed_at": datetime.now().isoformat(),
        "summary": text,
        "citations": citations,
        "ideas_extracted": ideas[0]["raw_ideas"],
    }

    slug = _slugify(topic)
    path = _save_result("topic", slug, result)
    _save_ideas(ideas)

    print(f"\n{'='*60}")
    print(text[:2000] if text else "(応答なし)")
    if citations:
        print(f"\n引用: {len(citations)}件")
    print(f"{'='*60}")
    print(f"保存: {path.relative_to(ROOT)}")
    print(f"ネタ候補: {IDEAS_FILE.relative_to(ROOT)} に追記")


def cmd_benchmark(args: argparse.Namespace) -> None:
    """platforms.yaml の競合アカウントを一括分析してベンチマーク"""
    accounts = _load_competitive_accounts()
    if not accounts:
        print("ERROR: config/platforms.yaml に競合アカウントが未設定です")
        print("  competitive.accounts にアカウントを追加してください")
        sys.exit(1)

    handles = [a["id"] for a in accounts if isinstance(a, dict) and "id" in a]
    if not handles:
        print("ERROR: 有効なアカウントIDがありません")
        sys.exit(1)

    from_date, to_date = _parse_period(args.period)
    handle_list = ", ".join(f"@{h}" for h in handles)

    prompt = f"""以下のXアカウントを比較分析してベンチマークレポートを作成してください: {handle_list}

分析項目（日本語で回答）:
1. 各アカウントの概要（フォロワー規模感・ジャンル・特徴）
2. 投稿頻度の比較
3. コンテンツの傾向比較（テーマ・フォーマット・トーン）
4. エンゲージメントが高いアカウントの共通特徴
5. 各アカウントの強み・弱み
6. ジャンル全体のトレンド
7. 自アカウント改善のための具体的なアクション（3つ）"""

    print(f"[benchmark] {len(handles)} アカウントのベンチマーク分析中...")
    raw = _call_x_search(prompt, handles=handles, from_date=from_date, to_date=to_date)
    text, citations = _extract_response(raw)

    result = {
        "type": "benchmark",
        "accounts": handles,
        "period": {"from": from_date, "to": to_date},
        "analyzed_at": datetime.now().isoformat(),
        "summary": text,
        "citations": citations,
    }

    slug = datetime.now().strftime("%Y-%m")
    path = _save_result("benchmark", slug, result)

    print(f"\n{'='*60}")
    print(text[:3000] if text else "(応答なし)")
    if citations:
        print(f"\n引用: {len(citations)}件")
    print(f"{'='*60}")
    print(f"保存: {path.relative_to(ROOT)}")


def cmd_search(args: argparse.Namespace) -> None:
    """フリー検索"""
    query = args.query
    from_date, to_date = _parse_period(args.period)

    prompt = f"""Xで以下について検索して、結果を日本語で要約してください: {query}

以下の形式で回答してください:
1. 検索結果の概要
2. 主要な投稿・意見（URL付きで最大5件）
3. 全体的な傾向やセンチメント
4. コンテンツに活かせるポイント"""

    print(f"[search] 「{query}」を検索中 ({from_date} ~ {to_date})...")
    raw = _call_x_search(prompt, from_date=from_date, to_date=to_date)
    text, citations = _extract_response(raw)

    result = {
        "type": "search",
        "query": query,
        "period": {"from": from_date, "to": to_date},
        "analyzed_at": datetime.now().isoformat(),
        "summary": text,
        "citations": citations,
    }

    slug = _slugify(query)
    path = _save_result("search", slug, result)

    print(f"\n{'='*60}")
    print(text[:2000] if text else "(応答なし)")
    if citations:
        print(f"\n引用: {len(citations)}件")
    print(f"{'='*60}")
    print(f"保存: {path.relative_to(ROOT)}")


# ── ユーティリティ ────────────────────────────────────

def _extract_ideas_from_text(text: str) -> list[str]:
    """Grok の回答からネタ候補を抽出（ヒューリスティック）"""
    ideas: list[str] = []
    lines = text.split("\n")
    in_idea_section = False

    for line in lines:
        stripped = line.strip()
        # 「ネタ」「アイデア」「案」を含むヘッダーを検出
        if re.search(r'(ネタ|アイデア|案|おすすめ|提案)', stripped) and len(stripped) < 50:
            in_idea_section = True
            continue
        # 次のヘッダーでセクション終了
        if in_idea_section and re.match(r'^[#\d]+[.）]', stripped) and not re.match(r'^[\d]+[.）]', stripped):
            in_idea_section = False
        # 箇条書きを抽出
        if in_idea_section and re.match(r'^[-・●▸▹*]\s|^\d+[.）]\s', stripped):
            idea = re.sub(r'^[-・●▸▹*]\s|^\d+[.）]\s', '', stripped).strip()
            if idea and len(idea) > 5:
                ideas.append(idea)

    # セクションが見つからなかった場合、「ネタ」を含む行の次の箇条書きを拾う
    if not ideas:
        for i, line in enumerate(lines):
            if re.search(r'(ネタ|アイデア)', line):
                for j in range(i + 1, min(i + 10, len(lines))):
                    stripped = lines[j].strip()
                    if re.match(r'^[-・●▸▹*]\s|^\d+[.）]\s', stripped):
                        idea = re.sub(r'^[-・●▸▹*]\s|^\d+[.）]\s', '', stripped).strip()
                        if idea and len(idea) > 5:
                            ideas.append(idea)

    return ideas


# ── CLI ───────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="X Search — xAI API で X の定性分析を行い YAML に保存",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
サブコマンド:
  competitor  競合アカウントの投稿テーマ・傾向を分析
  trend       ジャンルキーワードでトレンドを検索
  topic       投稿ネタの反応・切り口を事前調査
  benchmark   platforms.yaml の競合アカウントを一括分析
  search      フリー検索

例:
  python scripts/x_search.py competitor @handle1 @handle2 --period 30d
  python scripts/x_search.py trend "AI 業務効率化" --period 7d
  python scripts/x_search.py topic "Claude Codeで議事録"
  python scripts/x_search.py benchmark
  python scripts/x_search.py search "プロンプトエンジニアリング"
""")

    sub = parser.add_subparsers(dest="command", required=True)

    # competitor
    p_comp = sub.add_parser("competitor", help="競合アカウント分析")
    p_comp.add_argument("handles", nargs="+", help="分析対象の X ハンドル（@付き可）")
    p_comp.add_argument("--period", default="30d", help="分析期間（7d/30d/3m）デフォルト: 30d")

    # trend
    p_trend = sub.add_parser("trend", help="トレンド検索")
    p_trend.add_argument("keyword", help="検索キーワード")
    p_trend.add_argument("--period", default="7d", help="検索期間 デフォルト: 7d")

    # topic
    p_topic = sub.add_parser("topic", help="トピック事前調査")
    p_topic.add_argument("topic", help="調査するトピック")
    p_topic.add_argument("--period", default="30d", help="検索期間 デフォルト: 30d")

    # benchmark
    p_bench = sub.add_parser("benchmark", help="競合ベンチマーク（platforms.yaml のアカウント使用）")
    p_bench.add_argument("--period", default="30d", help="分析期間 デフォルト: 30d")

    # search
    p_search = sub.add_parser("search", help="フリー検索")
    p_search.add_argument("query", help="検索クエリ")
    p_search.add_argument("--period", default="7d", help="検索期間 デフォルト: 7d")

    args = parser.parse_args()

    dispatch = {
        "competitor": cmd_competitor,
        "trend": cmd_trend,
        "topic": cmd_topic,
        "benchmark": cmd_benchmark,
        "search": cmd_search,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    main()
