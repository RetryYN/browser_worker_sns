# リサーチフロー

ネタの収集 → 分類 → 実演判定 → 実演 → 検証 → 記事設計への引き渡し。

## 概要

```
[自動] cron: RSS/API巡回 → ネタ候補リスト蓄積
                                  ↓
[手動] /research 起動
        ├─ 1. ネタ候補リスト確認
        ├─ 2. RSS非対応サイトをPlaywright巡回
        ├─ 3. ネタタイプ判定
        ├─ 4. 実演判定
        │    ├─ OK → 実演フロー
        │    └─ NG → テキストのみで記事設計へ
        ├─ 5. 検証フロー
        └─ 6. 出力 → /run-task へ
```

---

## 1. ソース収集（自動 + 手動）

### 自動巡回（cron）

RSS/API がある公式ソースを定期取得し、ネタ候補リストに蓄積する。
取得だけ。判断はしない。

```
巡回先: knowledge/external-sources.md の auto_fetch: true のソース
出力先: knowledge/logs/research/YYYY-MM-DD.md
```

取得する情報:
- タイトル
- URL
- 公開日
- ソースカテゴリ（provider / trend / tech-blog）

### 手動巡回（/research 起動時）

RSS非対応サイトは Playwright MCP で巡回し、新着を確認する。

```
1. mcp__playwright__browser_navigate で対象サイトにアクセス
2. mcp__playwright__browser_snapshot で見出し一覧を取得
3. 前回巡回時（knowledge/logs/research/ の最新ログ）と差分を確認
4. 新着をネタ候補リストに追記
```

---

## 2. ネタタイプ判定

収集したネタを以下の5タイプに分類する。

| タイプ | 内容 | content-types.md との対応 | 実演相性 |
|--------|------|--------------------------|---------|
| **update** アップデート速報 | 公式の新機能・変更点 | C3 ニュース × P4 逆三角形 or P8 対話劇 | 高 |
| **compare** 比較検証 | 複数AIやツールの横並び検証 | C6 比較 × P3 並列比較 or P8 対話劇 | 高 |
| **howto** ノウハウ翻訳 | 技術ブログの実践知をノンエンジニア向けに | C2 ノウハウ × P2 ステップ or P6 Before/After | 中 |
| **trend** トレンド解説 | 業界動向・データの読み解き | C8 トレンド分析 × P4 逆三角形 or P1 PREP | 低 |
| **real** あるある・ネタ | 実体験ベースのAIあるある | C4 体験 × P8 対話劇 or P6 Before/After | 中 |

### 判定基準

```
一次ソースに新機能・バージョン情報がある → update
複数のツール/AIが比較対象になる         → compare
手順・やり方・Tipsが核                 → howto
数値・市場動向・将来予測が核            → trend
「使ってみたらこうだった」が核          → real
```

---

## 3. 実演判定

Claude Code（Playwright MCP）で実画面を見せられるかを判定する。

### 判定チェックリスト

| # | チェック項目 | OK | NG |
|---|------------|----|----|
| 1 | ブラウザでアクセス可能か | 公開ページ、無料ツール | 有料限定、モバイルアプリ専用 |
| 2 | 操作が再現可能か | プロンプト入力→出力確認 | アプリインストール必須 |
| 3 | スクショが意味をなすか | UI変更、出力結果、比較画面 | 内部アルゴリズム変更（見た目に出ない） |
| 4 | 安全に実行可能か | 読み取り・生成系 | 課金・削除・外部送信を伴う操作 |
| 5 | ログインウォールの中か | ログイン済みセッションで到達可能 | 新規登録・決済が必要 |

### 判定結果

```
全項目 OK        → 実演あり（スクショつき記事）
1-2項目 NG       → 部分実演（アクセス可能な部分だけスクショ + 残りはテキスト）
3項目以上 NG     → テキストのみ
```

---

## 4. 実演フロー

実演判定OKのネタに対して、実際にブラウザで操作してスクショを撮る。

### 手順

```
1. 事前準備
   - 操作対象のサイトナレッジを確認（knowledge/sites/）
   - 操作手順をプランニング

2. 操作 & 撮影
   - mcp__playwright__browser_navigate で対象にアクセス
   - 操作前のスクショを撮る（Before）
   - 実際の操作を実行（プロンプト入力、機能操作等）
   - 操作後のスクショを撮る（After）
   - 注目ポイントがあれば追加スクショ

3. 記録
   - スクショを knowledge/data/images/research/ に保存
   - 操作手順・結果をログに記録
   - 成功/失敗、予想との差異をメモ
```

### 撮影パターン

| パターン | 撮影内容 | 使い方 |
|---------|---------|--------|
| 新機能紹介 | 機能画面 → 操作 → 結果 | update 記事のエビデンス |
| 比較撮影 | AI-A の出力 → AI-B の出力 → 並べて比較 | compare 記事の素材 |
| 手順撮影 | ステップ1画面 → ステップ2画面 → … | howto 記事の図解 |
| Before/After | 改善前 → 操作 → 改善後 | real / howto 記事の変化 |

---

## 5. 検証フロー

記事に含まれる事実情報のファクトチェック。account-concept.md のファクトチェックポリシーに準拠。

### 手順

```
1. 事実抽出
   - 記事内の事実情報（機能、料金、数値、日付）を抽出

2. 一次ソース突合
   - 各事実に対して一次ソースを特定
   - WebSearch / WebFetch で最新情報を確認
   - ソースURL と確認日を記録

3. 判定
   - 確認できた → そのまま（ソース明示）
   - 確認できない → 留保表現に変更 or 削除
   - 古い情報 → 「執筆時点（YYYY年M月）」を明記

4. 掛け合いチェック
   - キャラの掛け合い内の「嘘」（特にGemini）にツッコミが入っているか確認

5. 記録
   - 検証結果をログに記録（knowledge/logs/research/）
```

### 検証レベル

| ネタタイプ | 検証レベル | 理由 |
|-----------|-----------|------|
| update | 高 — 公式ソースと全項目突合 | 誤情報が信頼を致命的に損なう |
| compare | 高 — 全比較軸で再検証 | 公平性が命 |
| howto | 中 — 手順の再現性を確認 | 動かない手順は価値ゼロ |
| trend | 中 — 数値・出典の確認 | 出典不明の数値は使わない |
| real | 低 — 体験ベースなので事実確認は軽め | 感想は検証不要。引用した事実のみ確認 |

---

## 6. 出力

リサーチ結果を記事設計に引き渡す。

### ネタ候補リストのフォーマット（knowledge/logs/research/YYYY-MM-DD.md）

```markdown
# リサーチログ YYYY-MM-DD

## 新着ネタ

### [ネタタイトル]
- **ソース**: [URL]
- **ソースカテゴリ**: provider / trend / tech-blog
- **ネタタイプ**: update / compare / howto / trend / real
- **トピック**: メイン: [トピック名] / サブ: [トピック名, ...]
- **実演判定**: OK / 部分OK / NG
- **実演メモ**: （実演OKの場合、何をどう撮るか）
- **検証状態**: 未検証 / 検証済み
- **content-types**: C? × P?（推奨の組み合わせ）
- **ミサキ刺さり度**: 高 / 中 / 低
- **一言**: （このネタの核心を1文で）
```

トピック一覧は `knowledge/sites/note/index.md` §トピック設計 を参照。

### /run-task への引き渡し

実演・検証が完了したネタは以下の情報を持って記事作成に進む:

```yaml
theme: "ネタタイトル"
source_url: "一次ソースURL"
neta_type: "update"
content_type: "C3 × P4"
topic_main: "Claude"
topic_sub: ["AIニュース", "Claude Code"]
hashtags: ["#Claude", "#AIニュース", "#ClaudeCode"]
demo_available: true
demo_screenshots:
  - "knowledge/data/images/research/screenshot-1.png"
  - "knowledge/data/images/research/screenshot-2.png"
verification_status: "verified"
verification_log: "knowledge/logs/research/YYYY-MM-DD.md"
```
