---
description: ネタ調査から記事化・投稿候補の引き渡しまでを行うリサーチワークフロー
---

# /research ワークフロー

ネタの収集、分類、実演可否判断、検証、キュー登録、`/run-task` への引き渡しまでを担当する。

## 使い方

```
/research [任意のフォーカス]
```

例:
- `/research Claude Code`
- `/research AI画像生成のネタを3本`
- `/research X向けの参加型ネタを探す`

---

## このワークフローの責務

- 外部ソースからネタ候補を集める
- `update / compare / howto / trend / real` に分類する
- 実演できるか判定する
- 必要な事実確認をする
- リサーチログを更新する
- X向けなら `knowledge/x-content-queue.md` を更新する
- note/X に流すための handoff を作る

**やらないこと**
- その場で投稿・公開まではしない
- 課金・削除・設定変更はしない
- 実演のためだけに危険操作をしない

---

## 起動時に必ず読むファイル

1. `knowledge/account-concept.md` — ペルソナ・ポジショニング
2. `knowledge/external-sources.md` — 巡回先ソース一覧
3. `knowledge/content-types.md` — C×P選択基準
4. `.agent/skills/god-writing/quality-standards.md` — テーマ選定の原則
5. `knowledge/sites/x/posting-strategy.md` — 配置ルール
6. `knowledge/x-content-queue.md` — キュー状況
7. `config/policies.yaml` — 禁止事項
8. 当日ログ `knowledge/logs/research/YYYY-MM-DD.md`（なければ `_template.md` を複製して作成）

---

## 実行手順

### 1. スコープ確認

ユーザーの指示から以下を決める。

- 対象媒体: `note / x / both`
- 優先トピック: 例 `Claude`, `ChatGPT`, `AI比較`
- 本数目安: 指定がなければ **3候補**
- 緊急度: `速報系` か `ストック系` か

指定が曖昧なら、以下をデフォルトにする。

```yaml
target: both
count: 3
priority: balanced
```

### 2. 当日ログ準備

1. `knowledge/logs/research/_template.md` を読む
2. 当日ログ `knowledge/logs/research/YYYY-MM-DD.md` がなければ作成する
3. すでに同日ログがあれば追記モードで使う

### 3. 候補収集

#### 3-1. X Search によるトレンド収集（推奨）

フォーカスが指定されている場合、まず X Search で X 上のリアルタイムな話題を収集する。

```bash
# トレンド検索
python scripts/x_search.py trend "<フォーカスキーワード>" --period 7d

# 特定トピックの事前調査
python scripts/x_search.py topic "<候補テーマ>" --period 30d
```

- 結果は `knowledge/logs/x/research/trend/` に YAML 保存される
- ネタ候補は `knowledge/logs/x/research/ideas.yaml` に自動蓄積される
- 蓄積済みの ideas.yaml も確認し、未使用のネタがあればそこから拾う

#### 3-2. auto_fetch ソース

`knowledge/external-sources.md` の `auto_fetch: yes` を優先して確認する。

収集項目:
- タイトル
- URL
- 公開日
- ソースカテゴリ

#### 3-3. auto_fetch: no ソース

RSS 非対応サイトはブラウザで巡回する。

手順:
1. `browser_navigate`
2. `browser_snapshot`
3. 見出し一覧を取得
4. 最新ログとの差分を見る
5. 新着だけを候補に追加

### 4. 一次ふるい

各候補を以下で落とす。

- 明らかな二次転載のみ
- 既に同趣旨で直近対応済み
- 実読価値が薄い細かな UI 文言変更
- 安全に検証できない課金・削除・設定変更系

### 5. 情報の5軸分類

一次ふるいを通過した候補ごとに、情報を5つのベクトルで分類する。この分類が記事の切り口（T軸）と価値の源泉を決める。

```yaml
info_vectors:
  semantic: "この情報は何を意味するか（一文で）"
  awareness: "高/中/低 — ターゲット層がどれくらい知っているか"
  discovery: "調べて初めてわかった事実（なければ空）"
  forgotten: "かつて知られていたが忘れられている事実（なければ空）"
  psychological: "読者がこの情報に触れたときの感情（驚き/不安/期待/etc.）"
```

**分類例:**
```yaml
# 候補: Notion AIのモデル選定
info_vectors:
  semantic: "AIツールの裏で動くモデルは選択・切替の時代に入った"
  awareness: 低
  discovery: "OpenAIからAnthropicに主要モデルを切り替えていた"
  forgotten: "GPT-3は2020年から存在したが開発者しか使えなかった"
  psychological: "え、そうだったの？ → 他のツールも裏が違う？"
```

**5軸 → 記事価値の判定:**
- awareness 低 + discovery あり → **高価値**（読者の常識を覆せる）
- awareness 高 + discovery なし → **低価値**（周知の事実の繰り返し）
- forgotten あり → **中〜高価値**（歴史の掘り起こしで独自性）
- psychological が強い → **高価値**（感情が動く＝シェアされやすい）

**5軸 → T軸（加工方法）の推奨:**

`content-types.md` の「T の選び方（5軸ベクトルから）」を正本とする。

#### エンベディングによる類似度分析（将来拡張）

5軸分類を GPT の embedding API でベクトル化し、以下に活用できる:
- **ネタ被り検出**: 過去記事の5軸ベクトルとのコサイン類似度で重複を検出
- **切り口の新規性判定**: 類似度が高いネタでも T軸が違えば価値あり
- **記事クラスタリング**: 似た記事が固まりすぎていないかバランスチェック

実装時は `scripts/embed_vectors.py` 等でバッチ処理し、結果を `knowledge/logs/research/embeddings.jsonl` に蓄積する想定。

### 6. ネタタイプ判定

| タイプ | 判定基準 | 推奨 content-type |
|---|---|---|
| `update` | 新機能、仕様変更、リリース | `C3 × P4` または `C3 × P8` |
| `compare` | 複数AI・複数ツールの比較 | `C6 × P3` または `C6 × P8` |
| `howto` | 手順、ノウハウ、再現方法 | `C2 × P2` または `C2 × P6` |
| `trend` | 市場動向、数値、業界解説 | `C8 × P4` または `C8 × P1` |
| `real` | 実体験、あるある、運用知見 | `C4 × P6` または `C4 × P8` |

### 7. 実演判定

以下5項目を `OK / NG` で判定する。

1. ブラウザで到達可能か
2. 操作が再現可能か
3. スクショに意味があるか
4. 安全に実行可能か
5. ログイン済みセッションで到達可能か

判定ルール:
- `OK 5/5`: 実演あり
- `OK 3-4/5`: 部分実演
- `OK 0-2/5`: テキストのみ

### 8. 検証

検証対象:
- 機能
- 料金
- 数値
- 日付
- 比較軸

手順:
1. 記事化・投稿化に使う事実を抽出
2. 一次ソースを特定
3. 必要ならブラウザまたは WebSearch/WebFetch 相当で再確認
4. 未確認事項は留保表現前提で記録

### 9. 媒体ごとの落とし先を決める

#### note 向き

- 情報量が多い
- 実演や比較の説明が必要
- `content-types.md` の骨格に落とし込みやすい

#### X 向き

- 初速が命
- 画像付きで一撃で伝わる
- `posting-strategy.md` の型に当てやすい

#### both 向き

- note: 詳細版
- X: 予告版、クイズ版、図解版、4枚版

### 10. ログ更新

当日ログに各候補を追記する。

必須項目:
- タイトル
- ソースURL
- ソースカテゴリ
- ネタタイプ
- トピック
- 5軸分類（`info_vectors` YAML）
- 推奨T（加工方法）
- 実演判定
- 検証状態
- 推奨 `C × P × T`
- ミサキ刺さり度
- 一言要約

### 11. X キュー更新

X向き、または both 向きの候補は `knowledge/x-content-queue.md` に追記・更新する。

管理状態:
- `inbox`
- `ready`
- `scheduled`
- `posted`
- `dropped`

### 12. handoff 生成

候補ごとに以下を出力する。

#### note handoff

```yaml
theme: "ネタタイトル"
source_url: "一次ソースURL"
content_type: "C3 × P4 × T7"
treatment: "対比（常識仮説 vs 事実のギャップ）"
info_vectors:
  semantic: "..."
  awareness: "低"
  discovery: "..."
  forgotten: ""
  psychological: "..."
topic_main: "Claude"
topic_sub: "AIニュース, Claude Code"
research_brief: "この記事で押さえるべき論点"
verification_log: "knowledge/logs/research/YYYY-MM-DD.md"
tags: "Claude, AIニュース, Claude Code"
```

#### X handoff

```yaml
theme: "ネタタイトル"
pattern: "quiz-senshuken / xgrid-4koma / tsukaiwake-chart / trend-sokuhou"
image_type: "quiz-choice / diagram / thumbnail / none"
source_url: "一次ソースURL"
fact_notes: "X本文で盛りすぎないための事実メモ"
verification_log: "knowledge/logs/research/YYYY-MM-DD.md"
```

#### 推奨コマンド

```text
# note 記事
/run-task note-article-publish theme: ... source_url: ... content_type: ... topic_main: ... topic_sub: ... research_brief: ... verification_log: ...

# X 投稿（軽量版 — 推奨）
/x-post <テーマ> schedule: YYYY-MM-DD HH:mm image: <image_type>

# X 投稿（/run-task 正式フロー）
/run-task x-idea-post-publish theme: ... pattern: ... image_type: ... source_url: ... fact_notes: ... schedule_at: ...
```

---

## 出力フォーマット

最終出力は以下の3部構成にする。

### 1. 今日の候補

3件前後。優先度順。

### 2. 推奨アクション

- note に回す候補
- X に回す候補
- 見送る候補

### 3. handoff

そのまま `/run-task` に渡せる形で提示する。

---

## 運用ルール

- 同じ日付のログは新規作成せず追記する
- research ログの本文は事実と判断を分けて書く
- 検証未完了のネタを「確定ネタ」として queue に入れない
- X向け queue に入れる時は `posting-strategy.md` の10型を必ず1つ紐付ける
- 実演スクショがある場合は保存先も handoff に残す
- note 記事化時は `note-article-publish` に research 情報を引き継ぐ
