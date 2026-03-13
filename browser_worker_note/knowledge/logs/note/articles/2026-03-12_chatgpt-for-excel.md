# note-article-publish: ChatGPT for Excel — 2026-03-12

## 実行結果: 成功
## フェーズ: ①初回（note記事投稿の初回）

## パラメータ
- theme: ChatGPT for Excel（日本語で指示するだけでExcel関数を作れるアドイン）
- content_type: C1×P6（ツール紹介×Before/After）
- tags: #ChatGPT, #AI活用, #Excel, #業務効率化
- topic_main: ChatGPT
- topic_sub: AI活用
- source_url: https://openai.com/index/chatgpt-for-excel/

## 公開情報
- 記事URL: https://note.com/akatu_unison/n/n4baac79c5368
- エディタURL: https://editor.note.com/notes/n4baac79c5368/edit/
- 公開日時: 2026-03-12 20:45
- 文字数: 3,143文字
- 画像数: 5枚

## 画像一覧
| # | 種類 | ファイル |
|---|------|---------|
| 1 | アイキャッチ | note_thumbnail_*.jpg（サムネイル） |
| 2 | 4コマ漫画 | note_comic_untitled_2026-03-12.jpg |
| 3 | Before/After図解 | note_diagram_untitled_2026-03-12.jpg |
| 4 | ChatGPTスクショ | note_screenshot_chatgpt-excel-sumif_2026-03-12.png (1140×590 クロップ済) |
| 5 | Claude Office日本語スクショ | スクリーンショット 2026-03-12 203242.png（ユーザー提供） |

## 記事構成

### H2見出し
1. 【Excel関数ググり勢へ】数式を日本語で作れる時代が来るらしい
2. VLOOKUPを調べて、コピペして、またググる
3. 日本語で聞くだけで数式が作れる。ChatGPT for Excelの3つの機能
4. 「関数なに使えばいいかわからない」がなくなる働き方
5. 日本で使えるのはいつ？
6. 日本提供を待たずに今日からできるExcel × AI活用法

### H3見出し
- 1. 自然言語で数式作成
- 2. エラー自動修正
- 3. データ分析・シナリオ作成
- ステップ1〜3（今日からできる活用法）
- もう一歩先へ：Claude for Excel

### 太字（11箇所）
- 日本語で指示するだけでExcelの数式を作れるアドイン
- ただし日本は未提供
- 15分
- Excelの中でAIに指示できるアドイン
- 関数名を知らなくて大丈夫
- 「このエラーを直して」と伝えるだけ
- 数式の精度は87%
- 「調べる時間」が消える
- 同じことは今日からできます
- 無料プランでも使えます
- 15分から1分以下へ

### 参考リンク
- ChatGPT in Excel and Google Sheets — OpenAI（ChatGPTセクション下）
- Claude for Excel — Anthropic（Claudeセクション下）

## 公開設定
- 記事タイプ: 無料
- マガジン: あとで読む（チェック済み）
- クリエイターページに表示: ON
- AI学習対価還元: ON
- コメント受付: ON
- スキ画像: chatgpt emoji.png（セッション中に設定）

## 実行ルート
```
1. editor.note.com/notes/<id>/edit/ で記事編集
2. アイキャッチ画像アップ
3. タイトル入力
4. 本文入力（browser_type + browser_evaluate でDOM操作）
5. 4コマ挿入（メニュー→画像→file_upload）
6. Before/After図解挿入
7. ChatGPTスクショ差し替え（削除→再挿入→クロップ版アップ）
8. 目次挿入（メニュー→目次）
9. 太字挿入（browser_evaluate: innerHTML.replace + <strong>）
10. 埋め込みテスト（OpenAI URL → 失敗 → テキストリンクに変更）
11. Claude for Excelセクション追加（browser_evaluate: insertAdjacentHTML）
12. 参考リンク再配置（browser_evaluate: DOM操作で移動）
13. 「公開に進む」クリック → publish画面
14. ハッシュタグ4つ追加（combobox slowly入力→選択）
15. 「投稿する」クリック
16. スキ設定（chatgpt emoji.png アップ→「これで設定！」）
17. 公開記事確認（noteトップ + 記事ページ）
```

## 短縮メモ
- 本文入力はDOMの一括操作（browser_evaluate）が最速。browser_type の繰り返しより効率的
- 太字は本文入力後にまとめてバッチ処理する（11箇所を1回のevaluateで）
- 目次は見出し確定後に挿入（見出し変更すると再生成が必要）
- ハッシュタグはslowly: trueが安定。fastだとドロップダウンが追いつかない

## 学び
- ProseMirror のDOM操作パターンが確立。innerHTML操作 + input event dispatchで安定動作
- 埋め込みはoEmbed対応サービスのみ。事前判定は難しいので、失敗時はテキストリンクにフォールバック
- スキ設定の画像アップは hidden input の親要素をクリック
- 参考リンクは最後にまとめるより関連セクション下に配置するほうが読者体験が良い（ユーザーフィードバック）
