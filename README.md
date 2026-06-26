# 沖縄釣果ダイジェスト

沖縄本島の釣り好き向けに、毎日「天気・風・波・潮見・釣果情報・狙いやすい魚種・おすすめ時間帯・注意点」をまとめる静的サイトです。

無料運用しやすいように、HTML/CSSとPythonの小さなビルドスクリプトだけで構成しています。記事はMarkdownで追加できます。

GitHub Actionsで毎朝5時に記事を自動生成し、GitHub Pagesへ公開できる構成です。

## 起動方法

まず記事を自動生成し、HTMLを生成します。

```powershell
cd C:\Users\user\Documents\Codex\2026-06-26\ok\outputs\okinawa-choka-digest-site
python scripts/generate_daily_post.py
python build.py
```

生成後、以下のファイルをブラウザで開きます。

```text
site\index.html
```

この環境で `python` が使えない場合は、Codex同梱Pythonなど任意のPython 3.10以上で `build.py` を実行してください。

## 記事の追加方法

`content/posts` にMarkdownファイルを追加します。

例:

```text
content/posts/2026-06-27.md
```

ファイル先頭のメタ情報を書き換えます。

```markdown
---
title: 沖縄釣果ダイジェスト｜2026/6/27
date: 2026-06-27
weather: 晴れ
wind: やや強い風
wave: 2m
tide: 中潮
rating: 3
areas: 北部,中部,南部
fish: タマン,ミーバイ,チヌ
---
```

本文を書いたあと、もう一度ビルドします。

```powershell
python build.py
```

## GitHub Pagesへの公開方法

GitHub Pagesで公開する場合:

1. GitHubで新しいリポジトリを作成
2. このプロジェクトの中身をアップロード
3. リポジトリの `Settings > Pages` を開く
4. `Build and deployment` のSourceを `GitHub Actions` にする
5. `Actions` タブで `Daily site build` を手動実行、または翌朝5時の自動実行を待つ

ワークフローは以下です。

```text
.github/workflows/daily-pages.yml
```

スケジュールは毎朝5時（JST）です。

```yaml
cron: "0 20 * * *"
```

GitHub ActionsのcronはUTCなので、`20:00 UTC` が日本時間の翌朝 `05:00 JST` になります。

## 自動生成される内容

`scripts/generate_daily_post.py` が以下を行います。

- Open-Meteoから那覇周辺の天気・風・雨を取得
- Open-Meteo Marine APIから波を取得
- 気象庁の那覇潮位表から満潮・干潮を取得
- 潮回り名は月齢をもとに算出
- 直近釣果のサンプルまたはGitHub Variablesの値を反映
- `content/posts/YYYY-MM-DD.md` を生成
- Markdown内にX投稿用テキストを保存

直近釣果を変えたい場合は、GitHubリポジトリのVariablesに以下を設定できます。

```text
CATCH_MANUAL_SUMMARY=うるま市・与勝周辺：タマン好調|読谷周辺：タマン50cmクラス|港内：ミーバイ、チヌ、ハタ類
```

## X投稿について

最初はXへ自動投稿しません。`content/posts/YYYY-MM-DD.md` には `X投稿用テキスト` を保存しますが、Webページには表示しません。

将来的にX APIを使う場合は、GitHub Secretsに以下を設定し、`scripts/post_to_x_future.py` を実装・ワークフローへ追加します。

```text
X_API_KEY
X_API_SECRET
X_ACCESS_TOKEN
X_ACCESS_TOKEN_SECRET
```

X APIは有料または従量課金になる可能性があるため、最初は本文生成だけにしています。

## 今後自動化する場合の拡張ポイント

- 釣果情報のRSS/公開ページを要約してMarkdownへ反映
- アイキャッチ画像を自動生成して `site/assets` に保存
- Google Analyticsタグを `build.py` の共通HTML生成処理に追加
- OGP画像とSEO用メタタグを記事ごとに生成

## 構成

```text
content/posts/      毎日のMarkdown記事
src/pages/          固定ページのMarkdown
assets/             画像など
scripts/            毎日記事生成・将来拡張用スクリプト
.github/workflows/  GitHub Actions設定
build.py            静的HTML生成スクリプト
site/               生成される公開用サイト
```
