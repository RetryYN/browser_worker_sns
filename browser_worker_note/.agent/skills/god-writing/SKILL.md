---
name: god-writing
description: God Writing — 全てのライティングスキルの上位原則。読者中心主義・目的従属・価値密度最大化・信頼構築優先・構造先行の5原則
triggers:
  - 記事を書く
  - 投稿文を作成する
  - コンテンツを生成する
  - generate_text
  - committee_review
dependencies: []
---

# God Writing — ライティング原則

**god-writing 配下の全スキル（21本）はこの原則に従属する。**
記事・投稿の生成前に必ず読み込むこと。

---

## 5つの原則

### 1. 読者中心主義（Reader-First）

文章の存在意義は読者にある。書き手の自己満足ではなく、読者の問題解決・欲求充足が最優先。

- 「読者は何を求めているか」を常に問う
- 専門用語は読者の理解レベルに合わせて変換する
- 情報の順序は読者の思考フローに沿わせる

### 2. 目的従属（Purpose-Driven）

全ての文章には明確な目的がある。一文一語が目的達成に貢献すること。

| Level | 目的の階層 | 例 |
|-------|-----------|-----|
| 1 | ビジネス目的 | 認知拡大 / フォロワー獲得 |
| 2 | コンテンツ目的 | 認知 / 理解 / 行動 |
| 3 | 文章目的 | クリック / 読了 / 共有 |
| 4 | 段落目的 | 注意 / 興味 / 納得 |
| 5 | 文目的 | 理解 / 感情 / 記憶 |

### 3. 価値密度最大化（Value Density）

限られた読者の時間と注意に対し、最大の価値を提供する。

```
価値密度 = 提供価値 ÷ 読者の消費コスト（時間 + 認知負荷）
```

- 冗長な表現の削除
- 重複情報の統合
- 本質的でない情報の排除

### 4. 信頼構築優先（Trust Building）

短期的な説得より長期的な信頼を重視。誇張・虚偽は厳禁。

| 要素 | 内容 |
|------|------|
| 正確性 | 事実に基づく記述 |
| 透明性 | メリット・デメリット両面の提示 |
| 一貫性 | 主張と行動の整合 |
| 誠実性 | 読者利益の優先 |

### 5. 構造先行（Structure First）

美しい文章より、明確な構造を優先。構造が内容を支える。

1. 全体の目的を定義
2. 必要な情報ブロックを洗い出し
3. 論理的順序で配置
4. 各ブロックの役割を明確化
5. 詳細を肉付け

---

## 3つの法則

### 80/20法則

20%の努力で80%の効果を得る箇所に集中する。

- タイトル・見出しに最大の注力
- 冒頭100文字に核心を凝縮
- CTAの設計に時間を投資

### 認知負荷最小化

読者の脳に負担をかけない。理解しやすさは最大の優しさ。

- 一文一義
- 既知 → 未知の順序
- 具体例による抽象概念の補強
- 視覚的な区切り

### 感情と論理の両輪

人は感情で動き、論理で正当化する。両方を満たす。

- 感情訴求 → 興味喚起・共感形成
- 論理訴求 → 納得・行動決定

---

## 執筆前チェックリスト

- [ ] この文章の目的は明確か
- [ ] 読者は誰か、その人のために書いているか
- [ ] 全ての文が目的に貢献しているか
- [ ] 価値密度は最大化されているか
- [ ] 信頼を損なう表現はないか
- [ ] 構造は論理的か

---

## 適用順序（メイン戦略 + サブエージェント実行）

```
メイン（戦略レイヤー）
  1. エンティティ生成 — 読者の心理・状況・期待を想定
  2. 読者価値の定義 — 記事を読んで得られる価値
  3. ブランド変容設計 — 読後にアカウントへのイメージがどう変わるか
  4. C×P選択 + スキル検索 — 演出・トーン・必要スキルを特定
  5. アウトライン作成 — 構造・見出し・各セクションの役割
  6. レギュレーション確認 — quality-standards + policies で調整
  7. ユーザー承認 — アウトラインの承認を得る
  ↓
サブエージェント（実行レイヤー）
  執筆Agent — アウトライン + スキルセットを受けて本文生成
  校正Agent — 品質判定 + 驚き屋チェック
```

詳細手順・プロンプトテンプレート → `.claude/workflows/generate-content.md`

---

## スキルローディング

### メインコンテキスト（常駐）

| スキル | 役割 |
|--------|------|
| **SKILL.md**（この文書） | 5原則 + 3法則 + ディスパッチ表 |
| **quality-standards.md** | 品質基準（Level 4以上必須） |
| `knowledge/content-types.md` | C×P選択 + 演出ガイド |
| `knowledge/account-concept.md` | ペルソナ・トーン・エンティティ生成 |

### リサーチAgent（`.claude/workflows/research.md` で定義）

| スキル | 役割 |
|--------|------|
| `knowledge/account-concept.md` | ペルソナ・ポジショニング |
| `knowledge/external-sources.md` | 巡回先ソース一覧 |
| `.claude/workflows/research.md` | リサーチフロー |

### 見出しAgent

| スキル | 役割 |
|--------|------|
| **headline-writing.md** | タイトル・H2の設計技法 |
| **benefit-writing.md** | 機能→ベネフィット変換 |
| `knowledge/account-concept.md` | ミサキ層の言葉・NGトーン |

### 執筆Agent

| 常に読む | 役割 |
|---------|------|
| **SKILL.md** | 5原則 + 3法則 |
| **quality-standards.md** | 品質基準 |
| **three-nots.md** | 3NOT突破策 |
| **reader-adaptation.md** | ミサキ層への読者適応 |
| **sentence-construction.md** | 一文一義・文長・リズム |
| **concise-writing.md** | 冗長削除・価値密度最大化 |
| `knowledge/content-types.md` | 演出ガイド |
| `knowledge/account-concept.md` | ペルソナ・トーン |

| C×P×媒体で追加 | 選択基準 |
|---------------|---------|
| C別スキル | 下表参照 |
| P別スキル | 下表参照 |
| 媒体別スキル | note → paragraph-design / X → social-copy |

### 校正Agent

| スキル | 役割 |
|--------|------|
| **quality-standards.md** | 品質基準（Level判定） |
| **proofreading.md** | 校正・推敲 |
| **emphasis-technique.md** | 強調箇所の最終調整 |
| `knowledge/account-concept.md` | 驚き屋ワードチェック用 |

### 特殊Agent（必要時のみ）

| スキル | 用途 |
|--------|------|
| tagline-creation.md | プロフィール・マガジン名作成時 |

---

## C×P別スキル選択表 + T軸OODA重心ガイド（執筆Agentが参照）

### T軸（加工方法）— OODA重心指示

T軸の定義は `knowledge/content-types.md` を正本とする。T軸はスキル追加ではなく、執筆Agentの**OODAループのどこに重心を置くか**を決める。

| T | 加工方法 | OODA重心 | 執筆Agentへの指示 |
|---|---------|---------|-----------------|
| T1 | 情報整理 | Observe | 事実を漏れなく拾い、構造化して並べる |
| T2 | 情報翻訳 | Orient | 読者の言葉に置き換える。専門用語を体験に変換 |
| T3 | 情報解釈 | Detect | 事実に「こう読める」を加える。一次解釈を前面に |
| T4 | 検証 | Detect+Interpret | 「本当？」を確かめた過程と結果を見せる |
| T5 | 実践 | Interpret | やった結果を読者の行動に翻訳する |
| T6 | 比較 | Orient+Detect | 同一基準で並べ、差分を際立たせる |
| T7 | 対比 | Orient→Detect | 常識仮説を立て、事実で覆す |

### 内容（C）別

| C | 内容 | 追加スキル |
|---|------|-----------|
| C1 | ツール紹介 | benefit-writing, trust-building, social-proof |
| C2 | ノウハウ | benefit-writing, urgency-creation |
| C3 | ニュース | headline-writing, hook-creation, trust-building |
| C4 | 体験 | storytelling, social-proof, trust-building |
| C5 | 用語 | emphasis-technique |
| C6 | 比較 | benefit-writing, objection-preemption |
| C7 | オピニオン | trust-building, objection-preemption, emphasis-technique |
| C8 | トレンド分析 | trust-building, urgency-creation, headline-writing |

### 構成パターン（P）別

| P | パターン | 追加スキル |
|---|---------|-----------|
| P1 | PREP | objection-preemption |
| P2 | ステップ | readability-optimization |
| P3 | 並列比較 | benefit-writing |
| P4 | 逆三角形 | headline-writing, hook-creation |
| P5 | リスト | readability-optimization |
| P6 | Before/After | desire-amplification, benefit-writing |
| P7 | Q&A | objection-preemption |
| P8 | 対話劇 | storytelling |
| P9 | ケーススタディ | storytelling, social-proof |
| P10 | Problem/Solution | desire-amplification, urgency-creation |

### 読み込み例

```
C3（ニュース）× P4（逆三角形）× T7（対比）× note記事 の場合:

執筆Agent が読むもの:
  常駐:  SKILL.md, quality-standards, three-nots,
         reader-adaptation, sentence-construction, concise-writing,
         content-types, account-concept
  C3:    headline-writing, hook-creation, trust-building
  P4:    headline-writing（重複→1回）, hook-creation（重複→1回）
  T7:    OODA重心 = Orient→Detect（常識仮説を立て、事実で覆す）
  note:  paragraph-design, readability-optimization

校正Agent が読むもの:
  quality-standards, proofreading, emphasis-technique, account-concept

→ T軸はスキル追加ではなく、OODAループの重心指示として機能する
→ メインコンテキストは2ファイルのみ。重いスキルはAgent内で完結
```
