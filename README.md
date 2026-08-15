# 死ぬまでカウントダウン X自動投稿ボット

GitHub Actions が毎日2回、X (@アカウント) に自動投稿する。

- **朝8時 (JST)**: アプリと同じ「今日の名言」＋著者（肩書き）＋英語原文（文字数に収まる時のみ）
- **夜9時 (JST)**: 奇数日は Tips、偶数日と日曜はアプリ紹介（ストアリンク付き）

## セットアップ（1回だけ）

1. X でアプリ用アカウントを作成する
2. https://developer.x.com にそのアカウントでログイン → Free プランで App を作成
3. App の権限を **Read and write** に変更（User authentication settings で App permissions を設定）
4. Keys and tokens で以下4つを発行し、**このリポジトリの Settings → Secrets and variables → Actions** に登録:
   - `X_API_KEY`（API Key）
   - `X_API_SECRET`（API Key Secret）
   - `X_ACCESS_TOKEN`（Access Token）
   - `X_ACCESS_SECRET`（Access Token Secret）
   - ※ Access Token は権限変更**後**に発行（Read and write と表示されていること）
5. Actions タブ → 「X auto post」→ Run workflow → dry=true で本文だけ確認 → dry=false で試し投稿

## 運用

- 名言データは `quotes.json`（アプリと同じ100個＋Tips8個、出典検証済み）
- 投稿ロジックは `bot.py`。日替わりの選び方はアプリの表示と同期している
- X Free プランの上限は月500投稿。1日2投稿=月60なので余裕
- 止めたいときは Actions タブでワークフローを Disable
