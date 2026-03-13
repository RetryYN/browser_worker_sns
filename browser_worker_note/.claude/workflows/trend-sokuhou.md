---
description: Xトレンドに乗る速報投稿を、スクショ比較画像付きで作成・予約するワークフロー
---

# /trend-sokuhou ワークフロー

トレンドを検出し、スクリーンショット比較画像を合成し、注意喚起・解説投稿を作成・予約する。

## 使い方

```
/trend-sokuhou <トレンドテーマ> [schedule: YYYY-MM-DD HH:mm]
```

例:
- `/trend-sokuhou Claude偽サイト注意喚起 schedule: 2026-03-13 15:00`
- `/trend-sokuhou Gemini新機能` ← 即時投稿

---

## 前提条件

- Xにログイン済みであること
- Playwright MCP が使用可能であること
- PIL（Pillow）が使用可能であること

---

## 起動時に読むファイル

1. `knowledge/sites/x/index.md` — 実証済みフロー・注意事項
2. `knowledge/sites/x/posting-strategy.md` — アルゴリズムスコア
3. `knowledge/account-concept.md` — ペルソナ・トーン
4. `knowledge/x-content-queue.md` — キュー状況
5. `.agent/skills/god-writing/quality-standards.md` — テーマ選定の原則・品質基準

---

## 実行フロー

### Phase 1: トレンド確認

1. Xホームの右サイドバー「本日のニュース」「速報」セクションでトレンドを確認
2. トレンドのポスト件数・経過時間を記録（半減期52分の判断材料）
3. トレンドテーマに合致するか判定

### Phase 2: スクリーンショット取得

1. `browser_navigate` で対象ページにアクセス（例: Google検索結果、公式サイト）
2. `browser_take_screenshot` でスクリーンショットを撮影
3. 比較対象がある場合は複数枚取得（例: 正規サイト vs 偽サイト）

### Phase 3: 比較画像合成（PIL）

`Bash` で Python スクリプトを実行し、比較画像を合成する。

#### 基本パターン: 2枚比較（横並び）

```python
from PIL import Image, ImageDraw, ImageFont

# 1. 画像読み込み・クロップ
img1 = Image.open("screenshot1.png")
img2 = Image.open("screenshot2.png")

# 対象領域をクロップ（必要に応じて）
img1_cropped = img1.crop((left, top, right, bottom))
img2_cropped = img2.crop((left, top, right, bottom))

# 2. キャンバス作成（推奨: 900x540 or 1024x1024）
canvas = Image.new('RGB', (900, 540), 'white')

# 3. 画像を配置
canvas.paste(img1_cropped.resize((420, 400)), (20, 80))
canvas.paste(img2_cropped.resize((420, 400)), (460, 80))

# 4. ラベル追加（緑OK / 赤NG）
draw = ImageDraw.Draw(canvas)
draw.rectangle([(20, 40), (200, 75)], fill='#22c55e')   # 緑
draw.text((30, 45), "✓ 正規サイト", fill='white')
draw.rectangle([(460, 40), (640, 75)], fill='#ef4444')   # 赤
draw.text((470, 45), "✗ 偽サイト", fill='white')

# 5. 保存
canvas.save("comparison.png")
```

#### 画像仕様

| 項目 | 値 |
|------|-----|
| 推奨サイズ | 900x540（横長）or 1024x1024（正方形） |
| フォーマット | PNG（スクショ比較）or JPEG（写真系） |
| ラベル色 | 緑(#22c55e)=OK/正規、赤(#ef4444)=NG/偽/注意 |
| フォント | ゴシック系。PIL デフォルトフォントで可 |

### Phase 4: 投稿テキスト作成

ルール:
- **140字以内**（無料プラン制限）
- URLは本文に入れない（アルゴリズム不利）
- ハッシュタグ最大1個
- トーン: 「AIめっちゃ使ってる先輩が隣で見せてくれる感じ」
- 驚き屋ムーブNG（「衝撃」「ヤバい」「神ツール」は使わない）
- 「ブクマ推奨」等の短縮CTA推奨

### Phase 5: X投稿（即時 or 予約）

`knowledge/sites/x/index.md` の実証済みフローに従う。

#### 予約投稿の場合

**重要: 時間→日付の順で設定する**（過去日時エラー回避）

```
1. navigate /compose/post
2. click "ポストを予約"
3. select_option "時" → 時を設定     ← 時間を先に
4. select_option "分" → 分を設定
5. select_option "日" → 日を設定     ← 日付は後
6. click "確認する"
7. type（slowly: true）→ 本文入力
8. click "画像や動画を追加" → file_upload
9. click "予約設定"
10. snapshot → alert で確認
```

#### URLカードプレビュー対策

本文にURL（claude.ai 等）が含まれると、Xが自動でカードプレビューを生成する。

- カードプレビューが表示された場合 → 「カードプレビューを削除」ボタンをクリック
- URLを本文に含めないのがベスト（アルゴリズムスコア的にも不利）

### Phase 6: 記録

1. `knowledge/x-content-queue.md` の Scheduled/Posted セクションに追加
2. 画像は `knowledge/data/images/` に保存（命名: `x_<テーマ>_<日付>.png`）

---

## タイミング判断

| 条件 | 判断 |
|------|------|
| トレンド投稿数 5,000+ | 即座に投稿。半減期52分以内が勝負 |
| トレンド投稿数 1,000-5,000 | 1-2時間以内に投稿 |
| トレンド投稿数 < 1,000 | 予約投稿でピーク時間帯に合わせる |
| トレンド経過 > 6時間 | 速報性は薄い。図解・解説で付加価値を出す |

---

## 実証済みの技術要素（2026-03-13 Claude偽サイトで検証）

- **PIL**: `Image.open` → `crop` → `new canvas` → `paste` + `ImageDraw.text` でラベル付き比較画像
- **X投稿**: URLカードプレビューが自動生成される → 「カードプレビューを削除」ボタンで除去
- **文字数**: 140字制限に注意。「ブクマ推奨」等で短縮
- **半減期**: 52分。速報性のある投稿にはスクショベースの画像が有効（生成AI画像より速い）

---

## エスカレーション

- 投稿確定の直前に**必ず人間に最終承認**を求める
- 注意喚起・セキュリティ系の投稿は特に慎重に（誤情報リスク）
