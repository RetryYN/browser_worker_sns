# Pipeline Map

ワークフロー・スクリプト・データの接続を可視化する。

---

## 全体パイプライン

```mermaid
graph TB
    subgraph INPUT["🔍 ネタ収集"]
        RS["/research"]
        WS["Web検索 / x_search.py"]
        ES["external-sources.md<br/>巡回先50+"]
    end

    subgraph QUEUE["📋 ネタ帳"]
        XQ["x-content-queue.md<br/>Inbox → Ready"]
        NQ["note-content-queue.md<br/>Inbox → Ready"]
        RL["research logs<br/>knowledge/logs/research/"]
    end

    subgraph X_FLOW["🐦 X系"]
        XB["/x-batch<br/>3日分12枠充足"]
        XP["/x-post<br/>単発投稿"]
        TS["/trend-sokuhou<br/>速報割り込み"]
        XR["/x-reply<br/>1日10リプ"]
    end

    subgraph NOTE_FLOW["📝 note系"]
        NB["/note-batch<br/>4日分ストック充足"]
        GC["/generate-content<br/>Phase 1-2: 企画→執筆"]
        GCN["generate-content-note<br/>Phase 2.5-3.5: 検証→校正"]
    end

    subgraph DATA["💾 データ"]
        XDB[("x_posts.db")]
        NDB[("note_articles.db")]
        CDB[("competitor_benchmark.db")]
        DASH["dashboard.py<br/>→ dashboard.html"]
    end

    subgraph OUTPUT["📤 公開"]
        XSITE["X 投稿/予約"]
        NSITE["note 記事公開"]
    end

    RS --> WS & ES
    WS --> RL
    ES --> RL
    RL -->|X向き| XQ
    RL -->|note向き| NQ

    XQ -->|Ready| XP
    XB -->|③ストック充足| XP
    XP --> XSITE
    TS --> XSITE
    XR -->|リプ投稿| XSITE
    WS -->|検索| XR
    XSITE --> XDB

    NQ -->|Ready| GC
    NB -->|③ストック充足| GC
    GC -->|下書き| GCN
    GCN -->|校正済み| NB
    NB -->|③-A 公開| NSITE
    NSITE --> NDB

    XDB --> DASH
    NDB --> DASH
    CDB -->|差別化チェック| XP
    XDB -->|queue-sync| XQ
```

---

## コマンド別フロー

### /x-batch（X日常運用）

```mermaid
graph LR
    subgraph PHASE1["① データ取得"]
        S1["stock --days 3<br/>空き枠把握"]
        S2["予約→投稿<br/>遷移確認"]
        S3["メトリクス収集<br/>imp/eng/likes..."]
        S4["queue-sync<br/>DB→queue.md"]
    end

    subgraph PHASE2["② レポート確認"]
        D1["dashboard generate"]
        D2["改善シグナル読取<br/>ER=0% / 偏り / クロス"]
        D3["report --days 14"]
        D4["空きスロット設計"]
        D5["★ ユーザー確認"]
    end

    subgraph PHASE3["③ ストック充足"]
        P1["テーマ確定<br/>queue → ideas → 生成"]
        P2["本文生成<br/>140字以内"]
        P3["画像生成<br/>generate_image.py"]
        P4["予約投稿<br/>ブラウザ操作"]
        P5["DB登録<br/>x_analytics.py add"]
        P6["★ ユーザー承認"]
    end

    S1 --> S2 --> S3 --> S4
    S4 --> D1 --> D2 --> D3 --> D4 --> D5
    D5 -->|承認| P1 --> P2 --> P3 --> P4 --> P6
    P6 -->|承認| P5
    P5 -->|次の投稿| P1
```

### /note-batch（note日常運用）

```mermaid
graph LR
    subgraph PHASE1["① データ取得"]
        N1["stock<br/>下書きストック確認"]
        N2["メトリクス収集<br/>views/likes/comments"]
        N3["ステータス同期<br/>投稿済み判定"]
    end

    subgraph PHASE2["② レポート確認"]
        ND1["dashboard generate"]
        ND2["report --days 14"]
        ND3["ネタ帳確認<br/>note-content-queue.md"]
        ND4["作成計画"]
        ND5["★ ユーザー確認"]
    end

    subgraph PHASE3["③ ストック充足"]
        direction TB
        subgraph PUB["A. 今日の1記事公開"]
            PA1["校正済み下書き選択"]
            PA2["Phase 4: note公開"]
            PA3["★ ユーザー承認"]
        end
        subgraph DRAFT["B. 下書き作成（4日分まで）"]
            PB1["/research<br/>Web検索→ネタ帳"]
            PB2["/generate-content<br/>Phase 1-2: 企画→執筆"]
            PB3["Phase 2.5-3.5<br/>検証→校正"]
            PB4["ネタ帳更新<br/>Ready → Used"]
        end
    end

    N1 --> N2 --> N3
    N3 --> ND1 --> ND2 --> ND3 --> ND4 --> ND5
    ND5 -->|承認| PA1 --> PA2 --> PA3
    PA3 --> PB1 --> PB2 --> PB3 --> PB4
    PB4 -->|次の記事| PB1
```

---

## データフロー

```mermaid
graph TB
    subgraph SCRIPTS["⚙️ スクリプト"]
        XA["x_analytics.py<br/>stock / add / update<br/>queue-sync / report"]
        NA["note_analytics.py<br/>stock / add / update<br/>report"]
        DA["dashboard.py<br/>generate"]
        CA["competitor_analytics.py<br/>report"]
        GI["generate_image.py<br/>thumbnail / diagram<br/>quiz-choice / quiz-ba"]
        XS["x_search.py<br/>trend / topic / search"]
    end

    subgraph DB["🗄️ データベース"]
        XDB[("x_posts.db<br/>30カラム / 14行")]
        NDB[("note_articles.db<br/>17カラム / 5行")]
        CDB[("competitor_benchmark.db<br/>x:73 / note:28")]
    end

    subgraph FILES["📁 ファイル"]
        XCQ["x-content-queue.md"]
        NCQ["note-content-queue.md"]
        DRAFTS["knowledge/drafts/<br/>note_*.md"]
        IMAGES["knowledge/data/images/<br/>thumbnail / diagram / source"]
        HTML["dashboard.html"]
        RLOG["research logs<br/>YYYY-MM-DD.md"]
    end

    XA -->|read/write| XDB
    XA -->|queue-sync| XCQ
    NA -->|read/write| NDB
    NA -->|stock scan| DRAFTS
    DA -->|read| XDB & NDB & CDB
    DA -->|write| HTML
    CA -->|read| CDB
    GI -->|write| IMAGES
    XS -->|write| RLOG

    XDB -.->|sync| XCQ
    NDB -.->|対応| DRAFTS
```

---

## 記事ライフサイクル（note）

```mermaid
stateDiagram-v2
    [*] --> ネタ収集: /research
    ネタ収集 --> Inbox: note-content-queue.md
    Inbox --> Ready: 検証済み
    Ready --> 下書き: /generate-content Phase 1-2
    下書き --> 検証済み: Phase 2.5（ファクトチェック・画像）
    検証済み --> 校正済み: Phase 3-3.5（校正・文字数）
    校正済み --> 投稿済み: Phase 4（note公開）
    投稿済み --> [*]

    note left of 校正済み
        ストック = この状態の件数
        目標: 4件
    end note
```

---

## X投稿ライフサイクル

```mermaid
stateDiagram-v2
    [*] --> ネタ収集: /research
    ネタ収集 --> Inbox: x-content-queue.md
    Inbox --> Ready: 検証済み
    Ready --> テーマ確定: /x-post or /x-batch
    テーマ確定 --> 本文生成: 140字以内
    本文生成 --> 画像生成: generate_image.py
    画像生成 --> 予約投稿: ブラウザ操作
    予約投稿 --> scheduled: x_analytics.py add
    scheduled --> posted: 予約日時到達

    note left of scheduled
        ストック = この状態の件数
        目標: 12枠（3日×4枠）
    end note
```

---

## 参照一覧

| カテゴリ | ファイル | 役割 |
|---------|---------|------|
| **ワークフロー** | `.claude/workflows/x-batch.md` | X日常バッチ |
| | `.claude/workflows/note-batch.md` | note日常バッチ |
| | `.claude/workflows/x-post.md` | X単発投稿 |
| | `.claude/workflows/research.md` | ネタ収集 |
| | `.claude/workflows/generate-content.md` | 記事生成（共通） |
| | `.claude/workflows/generate-content-note.md` | note固有（検証→公開） |
| | `.claude/workflows/x-reply.md` | Xアウトリーチリプ |
| | `.claude/workflows/trend-sokuhou.md` | トレンド速報 |
| **スクリプト** | `scripts/x_analytics.py` | X投稿DB管理 |
| | `scripts/note_analytics.py` | note記事DB管理 |
| | `scripts/dashboard.py` | ダッシュボード生成 |
| | `scripts/competitor_analytics.py` | 競合分析 |
| | `scripts/generate_image.py` | 画像生成 |
| | `scripts/x_search.py` | X検索 |
| **データ** | `knowledge/data/x_posts.db` | X投稿メトリクス |
| | `knowledge/data/note_articles.db` | note記事メトリクス |
| | `knowledge/data/competitor_benchmark.db` | 競合データ |
| **キュー** | `knowledge/x-content-queue.md` | Xネタ帳 |
| | `knowledge/note-content-queue.md` | noteネタ帳 |
| **下書き** | `knowledge/drafts/note_*.md` | note記事下書き |
| **戦略** | `knowledge/account-concept.md` | ペルソナ・トーン |
| | `knowledge/content-types.md` | C×P×T定義 |
| | `knowledge/sites/x/posting-strategy.md` | X配置ルール |
| | `knowledge/sites/x/reply-strategy.md` | Xリプ戦略 |
