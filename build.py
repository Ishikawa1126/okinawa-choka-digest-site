from __future__ import annotations

import html
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).parent
CONTENT_DIR = ROOT / "content" / "posts"
PAGES_DIR = ROOT / "src" / "pages"
ASSETS_DIR = ROOT / "assets"
SITE_DIR = ROOT / "site"


def parse_markdown(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text

    _, frontmatter, body = text.split("---", 2)
    data: dict[str, str] = {}
    for line in frontmatter.strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data, body.strip()


def inline_markdown(value: str) -> str:
    value = html.escape(value)
    value = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", value)
    return value


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append(f"<p>{inline_markdown(' '.join(paragraph))}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            items = "".join(f"<li>{inline_markdown(item)}</li>" for item in list_items)
            blocks.append(f"<ul>{items}</ul>")
            list_items = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                blocks.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                in_code = False
            else:
                flush_paragraph()
                flush_list()
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        if stripped.startswith("## "):
            flush_paragraph()
            flush_list()
            blocks.append(f"<h2>{inline_markdown(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            flush_paragraph()
            flush_list()
            blocks.append(f"<h1>{inline_markdown(stripped[2:])}</h1>")
        elif stripped.startswith("- "):
            flush_paragraph()
            list_items.append(stripped[2:])
        else:
            flush_list()
            paragraph.append(stripped)

    flush_paragraph()
    flush_list()
    return "\n".join(blocks)


def remove_markdown_section(markdown: str, heading: str) -> str:
    pattern = rf"(?ms)^## {re.escape(heading)}\s*\n.*?(?=^## |\Z)"
    return re.sub(pattern, "", markdown).strip()


def section_cards_html(markdown: str, kind: str) -> str:
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in markdown.splitlines():
        if line.startswith("## "):
            if current_title:
                sections.append((current_title, current_lines))
            current_title = line[3:].strip()
            current_lines = []
        elif current_title:
            current_lines.append(line)

    if current_title:
        sections.append((current_title, current_lines))

    cards = []
    for index, (title, lines) in enumerate(sections, start=1):
        body = "\n".join(lines).strip()
        card_class = "info-card caution-card" if title in {"注意", "危険な魚と取り扱い", "沖縄の釣りで注意すべきこと"} else "info-card"
        label = "Safety" if title == "注意" else f"{kind} {index:02d}"
        cards.append(
            f"""
        <article class="{card_class}">
          <p class="panel-label">{html.escape(label)}</p>
          <h2>{html.escape(title)}</h2>
          {markdown_to_html(body)}
        </article>
"""
        )

    grid_class = "area-grid" if kind == "Area" else "fish-grid" if kind == "Fish" else "guide-grid"
    return f'<section class="card-grid {grid_class}">\n{"".join(cards)}      </section>'


def rating_marks(rating: str) -> str:
    try:
        value = max(0, min(5, int(rating)))
    except ValueError:
        value = 0
    return "★" * value + "☆" * (5 - value)


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def split_pipe(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def base_html(title: str, content: str, current: str = "", base_path: str = "") -> str:
    nav = [
        ("index.html", "トップ", "home"),
        ("areas.html", "エリア別", "areas"),
        ("fish.html", "魚種別", "fish"),
        ("beginner.html", "初心者ガイド", "beginner"),
    ]
    nav_html = "\n".join(
        f'<a class="{"active" if key == current else ""}" href="{base_path}{href}">{label}</a>'
        for href, label, key in nav
    )
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="毎朝5分で沖縄本島の釣り情報がわかるサイト">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{base_path}styles.css">
</head>
<body>
  <header class="site-header">
    <div class="header-inner">
      <a class="brand" href="{base_path}index.html">沖縄釣果ダイジェスト</a>
      <nav>{nav_html}</nav>
    </div>
  </header>
  {content}
  <footer class="site-footer">
    <p>安全第一で、最新の海況を確認して楽しみましょう。</p>
  </footer>
</body>
</html>
"""


def post_url(meta: dict[str, str]) -> str:
    return f"posts/{meta['date']}.html"


def render_home(posts: list[tuple[dict[str, str], str]]) -> str:
    latest, latest_body = posts[0]
    catches = split_pipe(latest.get("catch", ""))
    if not catches:
        catches = [
            "うるま市・与勝周辺：タマン好調",
            "読谷周辺：タマン50cmクラス",
            "港内：ミーバイ、チヌ、ハタ類",
        ]
    catch_items = "".join(
        f"<li>{html.escape(item)}</li>"
        for item in catches
    )
    fish_items = "".join(
        f"<li><span>{html.escape(item)}</span></li>"
        for item in split_csv(latest.get("fish", ""))
    )
    article_links = "\n".join(
        f'<li><a href="{post_url(meta)}">{html.escape(meta.get("title", meta["date"]))}</a></li>'
        for meta, _ in posts[:10]
    )

    content = f"""
  <main>
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">毎朝5分で沖縄本島の釣り情報がわかるサイト</p>
        <h1>沖縄釣果ダイジェスト</h1>
        <p>天気・風・波・潮見・釣果傾向・狙い目を、釣行前に見やすく整理します。</p>
      </div>
      <div class="hero-badge">
        <span>Today's Digest</span>
        <strong>{html.escape(latest.get("display_date", latest["date"]))}</strong>
      </div>
    </section>

    <section class="quick-strip" aria-label="今日の概要">
      <div>
        <span>おすすめ度</span>
        <strong>{rating_marks(latest.get("rating", "0"))}</strong>
      </div>
      <div>
        <span>潮回り</span>
        <strong>{html.escape(latest.get("tide", ""))}</strong>
      </div>
      <div>
        <span>波</span>
        <strong>{html.escape(latest.get("wave", ""))}</strong>
      </div>
      <div>
        <span>注目</span>
        <strong>{html.escape(split_csv(latest.get("fish", ""))[0] if split_csv(latest.get("fish", "")) else "釣果確認")}</strong>
      </div>
    </section>

    <section class="today-layout">
      <article class="main-card">
        <div class="section-title">
          <span>今日の釣り情報</span>
          <strong>{html.escape(latest.get("display_date", latest["date"]))}</strong>
        </div>
        <div class="alert"><span>本日の判断</span>{html.escape(latest.get("warning", ""))}</div>
        <div class="info-grid">
          <div><span>天気</span><strong>{html.escape(latest.get("weather", ""))}</strong></div>
          <div><span>風</span><strong>{html.escape(latest.get("wind", ""))}</strong></div>
          <div><span>波</span><strong>{html.escape(latest.get("wave", ""))}</strong></div>
        </div>
        <div class="info-grid">
          <div><span>潮</span><strong>{html.escape(latest.get("tide", ""))}</strong></div>
          <div><span>満潮</span><strong>{html.escape(latest.get("high_tide", ""))}</strong></div>
          <div><span>干潮</span><strong>{html.escape(latest.get("low_tide", ""))}</strong></div>
        </div>
      </article>

      <aside class="side-card">
        <p class="panel-label">Catch Trend</p>
        <h2>直近釣果</h2>
        <ul>{catch_items}</ul>
        <p class="panel-label">Target Fish</p>
        <h2>狙い目魚種</h2>
        <ul class="chips">{fish_items}</ul>
      </aside>
    </section>

    <section class="two-column">
      <article class="panel">
        <p class="panel-label">Best Time</p>
        <h2>おすすめ時間帯</h2>
        <div class="time-slots">
          <div><span>朝まずめ</span><strong>{html.escape(latest.get("morning_time", ""))}</strong></div>
          <div><span>夕まずめ</span><strong>{html.escape(latest.get("evening_time", ""))}</strong></div>
        </div>
      </article>
      <article class="panel caution-panel">
        <p class="panel-label">Safety</p>
        <h2>注意点</h2>
        <p>{html.escape(latest.get("warning", ""))}</p>
      </article>
    </section>

    <section class="article-list">
      <h2>最新記事一覧</h2>
      <ul>{article_links}</ul>
    </section>
  </main>
"""
    return base_html("沖縄釣果ダイジェスト", content, "home")


def render_post(meta: dict[str, str], body: str) -> str:
    public_body = remove_markdown_section(body, "X投稿用テキスト")
    content = f"""
  <main class="page">
    <article class="article">
      <p class="eyebrow">{html.escape(meta.get("display_date", meta["date"]))}</p>
      <h1>{html.escape(meta.get("title", ""))}</h1>
      <div class="post-summary">
        <div><span>海況</span><strong>{html.escape(meta.get("weather", ""))} / {html.escape(meta.get("wind", ""))} / {html.escape(meta.get("wave", ""))}</strong></div>
        <div><span>潮見</span><strong>{html.escape(meta.get("tide", ""))} 満潮 {html.escape(meta.get("high_tide", ""))} / 干潮 {html.escape(meta.get("low_tide", ""))}</strong></div>
      </div>
      {markdown_to_html(public_body)}
    </article>
  </main>
"""
    return base_html(meta.get("title", "記事"), content, base_path="../")


def render_page(path: Path, key: str) -> str:
    meta, body = parse_markdown(path)
    body_html = (
        section_cards_html(body, "Area")
        if key == "areas"
        else section_cards_html(body, "Fish")
        if key == "fish"
        else section_cards_html(body, "Guide")
        if key == "beginner"
        else markdown_to_html(body)
    )
    content = f"""
  <main class="page">
    <article class="article">
      <p class="eyebrow">{html.escape(meta.get("description", ""))}</p>
      <h1>{html.escape(meta.get("title", ""))}</h1>
      {body_html}
    </article>
  </main>
"""
    return base_html(meta.get("title", ""), content, key)


def write_styles() -> None:
    css = """* { box-sizing: border-box; }
:root {
  --ink: #0b2235;
  --muted: #617885;
  --navy: #051c31;
  --blue: #086b91;
  --teal: #00a6a6;
  --green: #0d8d72;
  --sand: #f3bf4f;
  --paper: #ffffff;
  --line: #d5e5e7;
  --soft: #f5fbfa;
  --shadow: 0 18px 46px rgba(4, 31, 48, .12);
}
body {
  margin: 0;
  font-family: "Meiryo", "Yu Gothic", system-ui, sans-serif;
  color: var(--ink);
  background:
    radial-gradient(circle at 12% 0%, rgba(0,166,166,.18), transparent 28rem),
    radial-gradient(circle at 88% 8%, rgba(8,107,145,.18), transparent 30rem),
    linear-gradient(180deg, #effafb 0, #f8fbf9 360px, #eef5f1 100%);
  line-height: 1.65;
  overflow-x: hidden;
}
a { color: #006f9b; text-underline-offset: 3px; }
.site-header {
  background: rgba(5, 28, 49, .94);
  backdrop-filter: blur(14px);
  color: white;
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 1px solid rgba(255,255,255,.12);
  box-shadow: 0 12px 34px rgba(2, 19, 34, .18);
}
.header-inner {
  width: min(1120px, calc(100% - 28px));
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 64px;
  padding: 10px 0;
}
.brand {
  color: white;
  text-decoration: none;
  font-weight: 800;
  font-size: clamp(1rem, 2.2vw, 1.18rem);
  letter-spacing: 0;
  white-space: nowrap;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 9px;
}
.brand::before {
  content: "";
  width: 11px;
  height: 28px;
  border-radius: 99px;
  background: linear-gradient(180deg, var(--sand), #39d3c1);
  box-shadow: 0 0 22px rgba(57,211,193,.45);
}
nav {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  flex: 1 1 auto;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}
nav::-webkit-scrollbar { display: none; }
nav a {
  color: rgba(255,255,255,.86);
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 999px;
  font-weight: 700;
  font-size: .9rem;
  line-height: 1;
  white-space: nowrap;
  flex: 0 0 auto;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.05);
}
nav a.active, nav a:hover {
  background: white;
  color: var(--navy);
}
main, .page {
  width: min(1120px, calc(100% - 28px));
  margin: 0 auto;
}
.hero {
  margin: 28px 0 18px;
  min-height: 455px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 26px;
  padding: clamp(24px, 5vw, 46px);
  border-radius: 8px;
  color: white;
  background:
    linear-gradient(90deg, rgba(3,18,33,.92), rgba(3,68,82,.46) 54%, rgba(3,18,33,.06)),
    linear-gradient(180deg, rgba(0,0,0,.02), rgba(3,18,33,.68)),
    url("assets/okinawa-hero-sea.png") center/cover;
  overflow: hidden;
  box-shadow: 0 28px 80px rgba(3, 34, 50, .28);
  position: relative;
  isolation: isolate;
}
.hero::before {
  content: "";
  position: absolute;
  inset: 18px;
  border: 1px solid rgba(255,255,255,.18);
  border-radius: 8px;
  pointer-events: none;
}
.hero::after {
  content: "";
  position: absolute;
  inset: auto 0 0;
  height: 8px;
  background: linear-gradient(90deg, var(--sand), #7ee7d3, #45b9d6);
}
.hero h1 {
  font-size: clamp(2.45rem, 5.8vw, 4.45rem);
  margin: 0 0 12px;
  line-height: 1.05;
  text-shadow: 0 4px 18px rgba(0,0,0,.32);
  word-break: keep-all;
  overflow-wrap: normal;
}
.hero p { max-width: 700px; font-size: 1.08rem; margin: 0; }
.hero-copy {
  max-width: 780px;
  position: relative;
  z-index: 1;
}
.hero-badge {
  align-self: start;
  background: rgba(255,255,255,.93);
  color: #073b67;
  border: 1px solid rgba(255,255,255,.7);
  border-radius: 8px;
  padding: 16px 18px;
  min-width: 205px;
  box-shadow: 0 10px 30px rgba(0,0,0,.18);
  position: relative;
  z-index: 1;
}
.hero-badge span {
  display: block;
  color: var(--teal);
  font-size: .78rem;
  font-weight: 800;
  text-transform: uppercase;
}
.hero-badge strong {
  display: block;
  font-size: 1.2rem;
}
.eyebrow {
  color: var(--teal);
  font-weight: 800;
  margin: 0 0 8px;
}
.hero .eyebrow {
  color: #93f4dd;
  text-shadow: 0 2px 12px rgba(0,0,0,.36);
}
.quick-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 0 0 22px;
}
.quick-strip div {
  background: rgba(255,255,255,.88);
  border: 1px solid rgba(5,28,49,.08);
  border-radius: 8px;
  padding: 15px 16px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
}
.quick-strip div::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: linear-gradient(180deg, var(--teal), var(--sand));
}
.quick-strip span,
.panel-label {
  display: block;
  color: var(--teal);
  font-size: .78rem;
  font-weight: 800;
  margin: 0 0 4px;
  text-transform: uppercase;
}
.quick-strip strong {
  display: block;
  font-size: 1.12rem;
  line-height: 1.35;
  overflow-wrap: anywhere;
}
.today-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.38fr) minmax(310px, .82fr);
  gap: 22px;
}
.main-card, .side-card, .panel, .article-list {
  background: rgba(255,255,255,.9);
  border: 1px solid rgba(5,28,49,.08);
  border-radius: 8px;
  padding: clamp(18px, 3vw, 26px);
  box-shadow: var(--shadow);
  backdrop-filter: blur(10px);
}
.section-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  font-size: 1.2rem;
  font-weight: 800;
}
.section-title strong {
  background: #061f35;
  color: white;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: .92rem;
  white-space: nowrap;
}
.alert {
  background: linear-gradient(90deg, #fff5d6, #fffdf5);
  border: 1px solid rgba(190,127,21,.28);
  border-left: 6px solid var(--sand);
  border-radius: 8px;
  padding: 14px 16px;
  font-weight: 700;
  margin: 16px 0;
}
.alert span {
  display: block;
  color: #8a5c05;
  font-size: .82rem;
  margin-bottom: 4px;
}
.info-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}
.info-grid div {
  background: linear-gradient(180deg, #f7fcff, #ffffff);
  border: 1px solid rgba(8,107,145,.12);
  border-radius: 8px;
  padding: 14px;
  min-height: 92px;
}
.info-grid span, .post-summary span {
  display: block;
  color: var(--muted);
  font-size: .9rem;
  margin-bottom: 5px;
}
.info-grid strong, .post-summary strong {
  display: block;
  font-size: 1.08rem;
  overflow-wrap: anywhere;
}
.side-card h2, .panel h2, .article-list h2 {
  margin: 0 0 12px;
  line-height: 1.25;
}
.side-card ul:not(.chips) {
  list-style: none;
  padding-left: 0;
  margin: 0 0 22px;
}
.side-card li {
  margin: 0 0 8px;
}
.side-card ul:not(.chips) li {
  border-left: 4px solid var(--teal);
  background: #f6fbff;
  border-radius: 8px;
  padding: 10px 12px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0;
}
.chips li {
  list-style: none;
}
.chips span {
  display: inline-flex;
  align-items: center;
  background: #e7f7f3;
  color: #07674f;
  border: 1px solid #b9ead7;
  border-radius: 999px;
  padding: 8px 12px;
  font-weight: 700;
}
.two-column {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  margin: 20px 0;
}
.time-slots {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.time-slots div {
  background: linear-gradient(180deg, #fffdf7, #f6fbff);
  border: 1px solid rgba(8,107,145,.13);
  border-radius: 8px;
  padding: 14px;
}
.time-slots span {
  color: #d76518;
  display: block;
  font-weight: 800;
}
.time-slots strong {
  display: block;
  font-size: 1.32rem;
  margin-top: 6px;
  overflow-wrap: anywhere;
}
.caution-panel {
  border-color: rgba(198,90,42,.28);
  background: #fffdfb;
}
.article-list { margin-bottom: 34px; }
.article-list ul {
  margin: 0;
  padding-left: 1.2rem;
}
.article-list li {
  margin: 8px 0;
}
.page { padding: 30px 0 50px; }
.article {
  background: transparent;
  border: 0;
  border-radius: 0;
  padding: 0;
  box-shadow: none;
}
.article h1 {
  font-size: clamp(2.25rem, 6vw, 3.8rem);
  margin: 0 0 18px;
  line-height: 1.08;
  letter-spacing: 0;
}
.article h2 {
  border-left: 6px solid var(--teal);
  padding-left: 10px;
  margin-top: 30px;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin-top: 24px;
}
.area-grid {
  grid-template-columns: 1fr;
}
.fish-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.guide-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.info-card {
  background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(247,252,251,.94));
  border: 1px solid rgba(5,28,49,.08);
  border-radius: 8px;
  padding: 20px;
  box-shadow: var(--shadow);
  position: relative;
  overflow: hidden;
}
.info-card::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 4px;
  background: linear-gradient(90deg, var(--teal), #4ac7dc, var(--sand));
}
.info-card h2 {
  border-left: 0;
  padding-left: 0;
  margin: 0 0 10px;
  font-size: 1.3rem;
  color: #071f33;
}
.info-card p {
  margin: 0 0 12px;
}
.info-card p:last-child {
  margin-bottom: 0;
}
.info-card ul {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
}
.info-card li {
  background: #f4fbff;
  border-left: 4px solid var(--teal);
  border-radius: 8px;
  margin: 8px 0;
  padding: 10px 12px;
}
.area-grid .info-card:not(.caution-card) {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 4px 22px;
  align-items: start;
}
.area-grid .info-card:not(.caution-card) .panel-label,
.area-grid .info-card:not(.caution-card) h2 {
  grid-column: 1;
}
.area-grid .info-card:not(.caution-card) > p:not(.panel-label),
.area-grid .info-card:not(.caution-card) > ul {
  grid-column: 2;
}
.area-grid .info-card:not(.caution-card) > p:not(.panel-label) {
  margin-top: 0;
}
.caution-card {
  border-color: rgba(198,90,42,.25);
  background: linear-gradient(180deg, #fffdfb, #fff7f2);
}
.caution-card::before {
  background: linear-gradient(90deg, #e7894f, var(--sand));
}
.caution-card .panel-label {
  color: #b35a1d;
}
.caution-card li {
  background: #fff7f2;
  border-left-color: #e7894f;
}
.post-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0;
}
.post-summary div {
  background: #f2fbff;
  border: 1px solid rgba(8,107,145,.13);
  border-radius: 8px;
  padding: 14px;
}
pre {
  max-width: 100%;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  background: #f6fbff;
  border: 1px solid #cfe8f4;
  border-radius: 8px;
  padding: 14px;
}
.site-footer {
  background: #051c31;
  color: white;
  padding: 24px;
  text-align: center;
}
@media (max-width: 980px) {
  .hero {
    grid-template-columns: 1fr;
  }
  .hero-badge {
    align-self: end;
    width: fit-content;
  }
  .quick-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 800px) {
  .header-inner, .section-title {
    align-items: flex-start;
    flex-direction: column;
  }
  .header-inner {
    gap: 8px;
    min-height: 0;
    padding: 10px 0 11px;
  }
  nav {
    width: 100%;
    justify-content: flex-start;
    padding-bottom: 1px;
  }
  nav a {
    font-size: .86rem;
    padding: 8px 11px;
  }
  .today-layout, .two-column, .post-summary {
    grid-template-columns: 1fr;
  }
  .card-grid,
  .fish-grid,
  .guide-grid {
    grid-template-columns: 1fr;
  }
  .area-grid .info-card:not(.caution-card) {
    display: block;
  }
  .info-grid {
    grid-template-columns: 1fr;
  }
  .hero {
    min-height: 340px;
    padding: 22px;
    background-position: center;
  }
  .hero h1 {
    font-size: clamp(2rem, 12vw, 3rem);
  }
  .hero-badge {
    width: 100%;
  }
  .quick-strip,
  .time-slots {
    grid-template-columns: 1fr;
  }
}
"""
    (SITE_DIR / "styles.css").write_text(css, encoding="utf-8")


def copy_assets() -> None:
    target = SITE_DIR / "assets"
    target.mkdir(parents=True, exist_ok=True)
    if ASSETS_DIR.exists():
        for path in ASSETS_DIR.glob("*"):
            if path.is_file():
                shutil.copyfile(path, target / path.name)


def build() -> None:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "posts").mkdir(exist_ok=True)
    (SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")
    copy_assets()
    write_styles()

    posts = []
    for path in sorted(CONTENT_DIR.glob("*.md"), reverse=True):
        meta, body = parse_markdown(path)
        if "date" not in meta:
            continue
        posts.append((meta, body))
        (SITE_DIR / post_url(meta)).write_text(render_post(meta, body), encoding="utf-8")

    if not posts:
        raise RuntimeError("No posts found in content/posts")

    (SITE_DIR / "index.html").write_text(render_home(posts), encoding="utf-8")
    (SITE_DIR / "areas.html").write_text(render_page(PAGES_DIR / "areas.md", "areas"), encoding="utf-8")
    (SITE_DIR / "fish.html").write_text(render_page(PAGES_DIR / "fish.md", "fish"), encoding="utf-8")
    (SITE_DIR / "beginner.html").write_text(render_page(PAGES_DIR / "beginner.md", "beginner"), encoding="utf-8")


if __name__ == "__main__":
    build()
    print(f"Built site: {SITE_DIR}")
