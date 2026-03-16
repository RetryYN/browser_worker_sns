# 下書き: Notion AIの中身は1つじゃない。知らずに3つのAIを使ってた

- **C×P×T**: C8（トレンド分析）× P4（逆三角形）× T7（対比）
- **Treatment**: 対比（「1つのAIが動いている」常識 vs 「3モデルがタスクで切り替わる」事実）
- **ステータス**: 校正済み
- **想定文字数**: 2,500〜3,000文字
- **ハッシュタグ**: #NotionAI #マルチモデル #AI活用 #Notion
- **タイトル文字数**: 31文字
- **リサーチログ**: knowledge/logs/research/2026-03-13.md

## 画像

| # | 種別 | ファイル | 挿入位置 | 検証 |
|---|------|---------|---------|------|
| 1 | サムネイル | `knowledge/data/images/note_thumbnail_blackboard_notion-ai-multimodel_2026-03-13.jpg` | 記事トップ | [x] |
| 2 | 図解（マルチモデル構造） | `knowledge/data/images/note_diagram_notion-ai-multimodel_2026-03-13.jpg` | H2「3つのAIを使い分けている」の下 | [x] |
| 3 | ソーススクショ | `knowledge/data/images/source_notion-ai-multimodel_01.png` | H2「1社に絞らない理由」の下 | [ ] |

---

Notion AIの中で、3つのAIモデルが動いています。GPT-5.2、Claude Opus 4.6、Gemini 3。タスクに応じて自動で切り替わる仕組みです。「Notion AIってChatGPTでしょ？」と思ってたなら、それはもう古い情報です。この流れ、Notionだけの話じゃありません。

---

## Notion AIは2022年11月に生まれていた。実はChatGPTより先

「Notion AIってChatGPTの後に出たツールでしょ？」

そう思っている人は多いはずです。でも調べてみたら逆でした。

Notion AI（当時の名前はNotion AI Writer）がローンチしたのは2022年11月。ChatGPTの公開は2022年11月30日です。Notion AIのほうが先です。

当時のNotion AIはOpenAIのモデルを使っていました。だから「中身はChatGPT」という印象が広まったのも無理はありません。ただ、それは2022年の話です。

2026年3月の今、Notion AIの中身は大きく変わっています。

## 2026年のNotion AIは、タスクごとに3つのAIを使い分けている

Notion 3.2のアップデートで、Notion AIは3つのモデルを搭載するようになりました（[Notion — リリースノート](https://www.notion.com/releases) / [Notion — AI機能の紹介](https://www.notion.com/ja/product/ai)）。

| モデル | 提供元 |
|--------|--------|
| GPT-5.2 | OpenAI |
| Claude Opus 4.6 | Anthropic |
| Gemini 3 | Google |

デフォルトは「Auto」モードです。ユーザーが何も選ばなくても、タスクの内容に応じてモデルが自動で切り替わります。

たとえば、ミーティングノートの要約を頼んだときと、文章の校正を頼んだとき。裏で動いているAIが違う可能性があります。

ユーザーがモデルを手動で選ぶこともできます。Notion AIのチャット画面にモデルピッカーが追加されていて、「この作業はClaudeでやりたい」と指定できます。

ただ、ほとんどの人はAutoのまま使っているはずです。つまり、知らないうちに3つのAIを使い分けていた、ということになります。

## 1社に絞らない理由は「得意分野が違うから」

「一番いいモデル1つに全部やらせればよくない？」

その疑問はもっともです。でも、AIモデルには得意・不得意があります。

Anthropicの事例ページでは、NotionがClaudeを採用した経緯が紹介されています（[Anthropic — Notion creates more intelligent workspaces with Claude AI](https://claude.com/customers/notion)）。ライティングやQ&Aといったコア機能で、Claudeの出力品質が評価されたとのことです。

Anthropicの事例ページには「プロンプトキャッシュでコスト90%削減」「レイテンシ85%改善」という数字が載っています。ただし、これはAnthropicのプロンプトキャッシュ技術の汎用的な数字です。Notion固有の成果として読むと誤解になります。自社有利な情報を載せるのは当然なので、そこは差し引いて読む必要があります。

では、なぜ3社並立なのか。理由は2つあります。

1つ目は、タスクによって最適なモデルが違うから。要約が得意なモデルと、文章生成が得意なモデルは違います。

2つ目は、1社依存のリスクです。AIモデルは半年で性能が大きく変わります。特定の1社に全て預けると、そのモデルの品質が落ちたとき、サービス全体が影響を受けます。

「最強のAI」を1つ探すより、タスクに合ったAIを選ぶ。Notionはその設計思想で動いています。

## Notion以外も中身は1つじゃない。ツールの選び方が変わる

この流れはNotionだけではありません。2026年3月時点で、主要なAIツールの裏側はこうなっています。

| ツール | 裏のモデル（2026年3月時点） |
|--------|--------------------------|
| Microsoft Copilot | GPT-4o中心。マルチモデル移行中 |
| Google Workspace | Gemini |
| Slack AI | Claude |
| Perplexity | 複数モデル（ユーザー選択可） |
| Notion AI | GPT-5.2 + Claude Opus 4.6 + Gemini 3 |

「Notion AIってChatGPTでしょ？」と聞かれたら、「3つのAIが入ってるよ」と答えられます。「Slack AIはChatGPTでしょ？」と聞かれたら、「Claude、Anthropicのやつだよ」と答えられます。

ツール名とモデル名はイコールじゃありません。

これからAIツールを選ぶとき、「ChatGPTかGeminiか」ではなく、「自分のタスクに合ったモデルが裏にいるかどうか」で判断するほうが合理的です。

自分が普段使っているAIツールの設定画面を開いてみてください。モデル選択の項目があるかもしれません。Notion AIならチャット画面のモデルピッカーを確認できます。裏で何が動いているか知るだけで、ツールの使い方が変わります。
