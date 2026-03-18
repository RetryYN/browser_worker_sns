"""
動的ダッシュボードサーバー

使い方:
  python scripts/dashboard_server.py
  → http://127.0.0.1:8000 でアクセス
  → ?month=2026-03 で月指定可
  → DB更新後にブラウザリロードで即反映
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# scripts/ ディレクトリを PATH に追加
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from dashboard import (
    build_html,
    collect_algorithm_data,
    collect_competitive_data,
    collect_note_data,
    collect_system_data,
    collect_trend_data,
    collect_x_data,
    load_config,
)

app = FastAPI(title="Delvework Dashboard")


@app.get("/", response_class=HTMLResponse)
def dashboard(month: str | None = None):
    month = month or datetime.now().strftime("%Y-%m")
    config = load_config()
    x_data = collect_x_data(month)
    note_data = collect_note_data(month)
    comp_data = collect_competitive_data(config)
    trend_data = collect_trend_data()
    algo_data = collect_algorithm_data(x_data)
    sys_data = collect_system_data()
    html = build_html(
        month, x_data, note_data, comp_data,
        trend_data, algo_data, sys_data, config,
    )
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn

    print("Dashboard: http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
