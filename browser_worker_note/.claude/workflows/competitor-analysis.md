---
description: 競合分析の共通ディスパッチャー。プラットフォーム別ワークフローに振り分ける
---

# /competitor-analysis ワークフロー

競合アカウントの発見・登録・分析・NG判定を実行する。
**X と note はテーブル・ワークフロー共に分離済み。** 必ずプラットフォームを指定すること。

## 使い方

```
/competitor-analysis <platform> <サブコマンド> [オプション]
```

| platform | ワークフロー |
|----------|-------------|
| `x` | → `competitor-analysis-x.md` |
| `note` | → `competitor-analysis-note.md` |

### サブコマンド（共通）

| コマンド | 説明 |
|---------|------|
| `scan` | 新規アカウント発見→分類→登録 |
| `update` | 既存ベンチマークの投稿メトリクス更新 |
| `report` | タイプ別集計・勝ちパターン確認 |
| `ng-check <テキスト>` | NG判定チェックリストに該当しないか確認 |
| `map` | コンテンツ構造対照表の更新（C×P×Tマッピング） |

### X 固有サブコマンド

| コマンド | 説明 |
|---------|------|
| `news` | 朝トレンド巡回→投稿候補抽出（3層構造） |

例:
```
/competitor-analysis x scan
/competitor-analysis note scan
/competitor-analysis x news
/competitor-analysis note ng-check "Notion AIを使ったら業務が半分になった話"
```

---

## 共通: 6タイプ分類基準

| type | 判定基準 |
|------|---------|
| benchmark | 専門性あり + 具体的実演 + 自分でやった証拠（スクショ/数値） |
| ng | 煽り/誇張/中身スカスカ/情報商材誘導 |
| news | AIプロバイダー公式 or ニュースキュレーター |
| growth | 0→1フェーズの成長実績データあり |
| visual | 図解/インフォグラフィック品質が高い |
| engagement | 初期拡散/コミュニティ構築の戦術が具体的 |

---

## 共通: NG判定チェックリスト

以下に **1つでも該当 → NG**:

### 基本NG（X / note 共通）
- [ ] 自分で実行していない情報をまとめているだけ
- [ ] ○選リストで項目数が価値の中心
- [ ] 具体的な画面スクショ・数値データがない
- [ ] 読者が読んだ後に再現できるステップがない
- [ ] 「すごい」「革命」「損する」等の感情操作ワード多用
- [ ] 「月○万」「時給○万」の収益煽り
- [ ] 「9割が知らない」「知らないと損」FOMO煽り

### X 追加NG
- [ ] 無料配布→いいね/リプ/フォロー条件→情報商材誘導
- [ ] PDF配布で「保存版」を煽るがリスト羅列のみ

### note 追加NG
- [ ] AI量産×有料記事の副業煽りファネル
- [ ] 「note×AIで稼ぐ」がメインテーマ（AI活用ではなくマネタイズが目的）
- [ ] LINE誘導・メルマガ誘導で情報商材に接続
- [ ] 「コピペOK」「誰でも」「スキルゼロで不労所得」等のFOMO煽り
- [ ] 有料記事の中身がプロンプトテンプレート集だけ

---

## 共通: ng-check コマンド

投稿テキストを渡すと以下をチェック:

1. **NGワードスキャン** — `quality-standards.md` の驚き屋・AI臭プリフライトチェック
2. **構造チェック** — NG層の構造パターンに該当しないか
   - X: C2×P5×T1 = 試してない情報リスト
   - note: C2×P5×T1 + 有料記事テンプレ集
3. **ベンチマーク比較** — 同テーマのベンチマーク投稿と比較して具体性・専門性が劣っていないか

---

## 共通: DB操作リファレンス

```bash
# アカウント登録
python scripts/competitor_analytics.py add-account -p <x|note> \
  --handle <handle> --name "<名前>" --category "<カテゴリ>" \
  --type <benchmark|ng|news|growth|visual|engagement> \
  --fork-direction "<フォーク方向>" --note "<メモ>"

# NG登録
python scripts/competitor_analytics.py add-account -p <x|note> \
  --handle <handle> --name "<名前>" --category "NG:<サブカテゴリ>" \
  --type ng --ng-reason "<NG理由>"

# 一覧
python scripts/competitor_analytics.py accounts -p <x|note>
python scripts/competitor_analytics.py accounts -p <x|note> --type benchmark

# レポート
python scripts/competitor_analytics.py report -p <x|note>
python scripts/competitor_analytics.py report -p <x|note> --ranking
python scripts/competitor_analytics.py report -p <x|note> --patterns
```

---

## 参照ファイル

| ファイル | 内容 |
|---------|------|
| `competitor-analysis-x.md` | X固有ワークフロー |
| `competitor-analysis-note.md` | note固有ワークフロー |
| `scripts/competitor_analytics.py` | 競合DB管理CLI（X/noteテーブル分離済み） |
| `knowledge/data/competitor_benchmark.db` | 競合SQLiteデータベース |
| `.agent/skills/god-writing/quality-standards.md` | 品質基準・NGワードリスト |
