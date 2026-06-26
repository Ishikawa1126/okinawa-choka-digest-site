# 沖縄釣果ダイジェスト

沖縄本島の釣り好き向けに、毎日「天気・風・波・海水温・潮見・釣果情報・狙いやすい魚種・おすすめ時間帯・注意点」をまとめる静的サイトです。

GitHub Actionsで毎朝記事を自動生成し、GitHub Pagesへ公開します。Xへの自動投稿はまだ行わず、将来使えるように記事Markdown内へX投稿用テキストだけ保存します。

公開サイト:

```text
https://ishikawa1126.github.io/okinawa-choka-digest-site/
```

## ローカルで確認する方法

```powershell
cd C:\Users\user\Documents\Codex\2026-06-26\ok\outputs\okinawa-choka-digest-site
python scripts/generate_daily_post.py
python build.py
```

生成後、以下をブラウザで開きます。

```text
site\index.html
```

## 毎朝の自動更新

GitHub Actionsのワークフローは以下です。

```text
.github/workflows/daily-pages.yml
```

現在は、GitHub Actionsの混雑を避けるため、毎朝2回実行します。

```yaml
cron: "7 20 * * *"   # 05:07 JST
cron: "22 20 * * *"  # 05:22 JST retry
```

GitHub ActionsのcronはUTC基準です。`20:07 UTC` が日本時間の翌朝 `05:07 JST` になります。

## 釣果情報の更新方法

釣果情報は、GitHubのRepository variablesに `CATCH_MANUAL_SUMMARY` を設定すると、毎朝の記事生成時に反映されます。

設定場所:

```text
GitHub repository
> Settings
> Secrets and variables
> Actions
> Variables
> New repository variable
```

Variable name:

```text
CATCH_MANUAL_SUMMARY
```

Variable valueの例:

```text
うるま市・与勝周辺：タマン好調|読谷周辺：タマン50cmクラス|港内：ミーバイ、チヌ、ハタ類
```

区切り文字は `|` です。次のように、1エリアごとに短く書くと見やすくなります。

```text
エリア名：魚種・傾向
```

例:

```text
本部港周辺：小型ガーラの回遊あり|読谷周辺：タマン50cmクラス|那覇港内：チヌ、ミーバイの情報あり
```

`CATCH_MANUAL_SUMMARY` が未設定、または空の場合は、サンプル釣果を使います。

```text
うるま市・与勝周辺：タマン好調
読谷周辺：タマン50cmクラス
港内：ミーバイ、チヌ、ハタ類
```

## 釣果情報を反映するタイミング

GitHubのVariableを変更しただけでは、すぐにサイトは更新されません。

反映方法は2つです。

1. 翌朝の自動生成を待つ
2. GitHubのActionsタブから `Daily site build` を手動実行する

手動実行する場合:

```text
GitHub repository
> Actions
> Daily site build
> Run workflow
```

## 自動取得している情報

`scripts/generate_daily_post.py` が以下を取得・生成します。

- Open-Meteoから天気、風、雨、気温を取得
- Open-Meteo Marine APIから波、海水温を取得
- 気象庁の那覇潮位表から満潮・干潮を取得
- 潮回り名は月齢をもとに算出
- 釣果情報は `CATCH_MANUAL_SUMMARY` またはデフォルト文を使用
- `content/posts/YYYY-MM-DD.md` を生成
- Markdown内にX投稿用テキストを保存

## 記事の追加・修正

記事は以下にMarkdownで保存されます。

```text
content/posts/YYYY-MM-DD.md
```

手動で修正したあと、以下でHTMLを再生成できます。

```powershell
python build.py
```

## GitHub Pagesへの公開設定

GitHub Pagesでは以下を設定します。

```text
Settings
> Pages
> Build and deployment
> Source: GitHub Actions
```

`main` ブランチにpushすると、自動でビルドとデプロイが走ります。

## X投稿について

現時点ではXへ自動投稿しません。

ただし、各記事Markdownには `X投稿用テキスト` を保存しています。Webページには表示しないようにしています。

将来X APIを使う場合は、GitHub Secretsに以下を設定し、投稿用スクリプトを追加します。

```text
X_API_KEY
X_API_SECRET
X_ACCESS_TOKEN
X_ACCESS_TOKEN_SECRET
```

## 構成

```text
content/posts/      毎日のMarkdown記事
src/pages/          エリア別・魚種別・初心者ガイドなどの固定ページ
assets/             画像素材
scripts/            毎日記事生成スクリプト
.github/workflows/  GitHub Actions設定
build.py            静的HTML生成スクリプト
site/               生成される公開用サイト
```
