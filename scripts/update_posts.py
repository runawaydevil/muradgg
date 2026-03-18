#!/usr/bin/env python3
"""
Lê arquivos .txt e .md em in/, persiste no SQLite (posts.db) e exporta posts.json.
O JavaScript carrega posts.json dinamicamente - o HTML permanece limpo.

Primeira linha = título; resto = corpo (Markdown). Linhas são preservadas como estão.

Recursos:
- Exportação para JSON (posts carregados dinamicamente via JS)
- Tempo de leitura estimado
- Geração de sitemap.xml e feed.xml
- Meta tags SEO
- Datas exibidas no fuso America/Sao_Paulo
"""
import sqlite3
import markdown
import re
import unicodedata
import math
import json
from html import escape
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
IN_DIR = ROOT / "files" / "in"
IN_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = ROOT / "files" / "posts.db"
INDEX_PATH = ROOT / "index.html"
RSS_PATH = ROOT / "feed.xml"
SITEMAP_PATH = ROOT / "sitemap.xml"
POSTS_JSON_PATH = ROOT / "files" / "posts.json"

SEO_START = "<!-- SEO_META -->"
SEO_END = "<!-- /SEO_META -->"

# Configurações
POSTS_PER_PAGE = 10
WORDS_PER_MINUTE = 200
BASE_URL = "https://murad.gg"
SITE_TITLE = "murad.gg"
SITE_DESCRIPTION = "Blog pessoal de murad - tecnologia, programação e pensamentos"
DISPLAY_TZ = "America/Sao_Paulo"


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)


_EXPECTED_COLUMNS = [
    ("title", "TEXT NOT NULL DEFAULT ''"),
    ("body", "TEXT NOT NULL DEFAULT ''"),
    ("created_at", "TEXT NOT NULL DEFAULT ''"),
]


def migrate_schema(conn: sqlite3.Connection) -> None:
    """Adiciona colunas que faltam na tabela posts."""
    cur = conn.execute("PRAGMA table_info(posts)")
    existing = {row[1] for row in cur.fetchall()}
    for name, spec in _EXPECTED_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE posts ADD COLUMN {name} {spec}")
    conn.commit()


def read_post_file(path: Path) -> tuple[str, str] | None:
    """Lê .txt ou .md: primeira linha = título, resto = corpo (linhas preservadas)."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    lines = text.strip().split("\n")
    if not lines:
        return None
    title = lines[0].strip()
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    return (title, body)


def upsert_from_in(conn: sqlite3.Connection) -> None:
    """Insere ou atualiza posts a partir de .txt e .md em in/."""
    if not IN_DIR.is_dir():
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    paths = sorted(IN_DIR.glob("*.txt")) + sorted(IN_DIR.glob("*.md"))
    for path in paths:
        parsed = read_post_file(path)
        if not parsed:
            continue
        title, body = parsed
        cur = conn.execute(
            "SELECT id, created_at FROM posts WHERE title = ?", (title,)
        )
        row = cur.fetchone()
        if row:
            conn.execute(
                "UPDATE posts SET body = ? WHERE id = ?",
                (body, row[0]),
            )
        else:
            conn.execute(
                "INSERT INTO posts (title, body, created_at) VALUES (?, ?, ?)",
                (title, body, now),
            )
    conn.commit()


def delete_sources_after_ingest() -> None:
    """Remove os .txt e .md em in/ após ingestão no DB."""
    if not IN_DIR.is_dir():
        return
    for path in list(IN_DIR.glob("*.txt")) + list(IN_DIR.glob("*.md")):
        try:
            path.unlink()
        except OSError:
            pass


def get_posts(conn: sqlite3.Connection) -> list[tuple[str, str, str]]:
    cur = conn.execute(
        "SELECT title, body, created_at FROM posts ORDER BY created_at DESC"
    )
    return cur.fetchall()


def calculate_reading_time(text: str) -> int:
    """Calcula tempo de leitura em minutos (~200 palavras/minuto)."""
    clean_text = re.sub(r'[#*`\[\](){}|<>]', '', text)
    clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', clean_text)
    clean_text = re.sub(r'\[.*?\]\(.*?\)', '', clean_text)
    words = len(clean_text.split())
    return max(1, math.ceil(words / WORDS_PER_MINUTE))


def format_date(iso: str) -> str:
    """Formata data ISO UTC para YYYY-MM-DD no fuso DISPLAY_TZ."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        local_dt = dt.astimezone(ZoneInfo(DISPLAY_TZ))
        return local_dt.strftime("%Y-%m-%d")
    except Exception:
        return iso


def slugify(value: str) -> str:
    value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)


def export_posts_json(posts: list[tuple[str, str, str]]) -> None:
    """Exporta posts para JSON - o JavaScript carrega dinamicamente."""
    posts_data = []

    for title, body, created_at in posts:
        html_body = markdown.markdown(
            body,
            extensions=['fenced_code', 'codehilite', 'tables']
        )
        posts_data.append({
            "slug": slugify(title),
            "title": title,
            "body": body,
            "html": html_body,
            "date": format_date(created_at),
            "created_at": created_at,
            "reading_time": calculate_reading_time(body)
        })

    json_content = {
        "config": {
            "posts_per_page": POSTS_PER_PAGE,
            "site_title": SITE_TITLE,
            "base_url": BASE_URL
        },
        "posts": posts_data
    }
    POSTS_JSON_PATH.write_text(
        json.dumps(json_content, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def generate_rss(posts: list[tuple[str, str, str]]) -> None:
    """Gera um arquivo RSS 2.0."""
    items = []
    for title, body, created_at in posts:
        slug = slugify(title)
        safe_title = escape(title)
        html_body = markdown.markdown(body, extensions=['fenced_code', 'codehilite', 'tables'])
        safe_body = escape(html_body)
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S %z")
        except Exception:
            pub_date = created_at
        items.append(f"""    <item>
      <title>{safe_title}</title>
      <link>{BASE_URL}#{slug}</link>
      <description>{safe_body}</description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="false">{slug}-{created_at}</guid>
    </item>""")
    items_block = "\n".join(items)
    rss_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>{SITE_TITLE}</title>
  <link>{BASE_URL}</link>
  <description>{SITE_DESCRIPTION}</description>
  <language>pt-br</language>
{items_block}
</channel>
</rss>"""
    RSS_PATH.write_text(rss_content, encoding="utf-8")


def generate_sitemap(posts: list[tuple[str, str, str]]) -> None:
    """Gera um arquivo sitemap.xml para SEO."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [f"""  <url>
    <loc>{BASE_URL}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>"""]
    for title, _, created_at in posts:
        slug = slugify(title)
        date_str = format_date(created_at)
        urls.append(f"""  <url>
    <loc>{BASE_URL}#{slug}</loc>
    <lastmod>{date_str}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>""")
    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""
    SITEMAP_PATH.write_text(sitemap_content, encoding="utf-8")


def generate_seo_meta(posts: list[tuple[str, str, str]]) -> str:
    """Gera meta tags SEO para o <head>."""
    if posts:
        _, latest_body, _ = posts[0]
        description = latest_body[:160].replace('\n', ' ').strip()
        if len(latest_body) > 160:
            description += "..."
    else:
        description = SITE_DESCRIPTION
    safe_description = escape(description)
    return f"""
  <!-- SEO Meta Tags -->
  <meta name="description" content="{safe_description}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{BASE_URL}">

  <!-- Open Graph / Facebook -->
  <meta property="og:type" content="website">
  <meta property="og:url" content="{BASE_URL}">
  <meta property="og:title" content="{SITE_TITLE}">
  <meta property="og:description" content="{safe_description}">
  <meta property="og:site_name" content="{SITE_TITLE}">
  <meta property="og:locale" content="pt_BR">

  <!-- Twitter -->
  <meta name="twitter:card" content="summary">
  <meta name="twitter:url" content="{BASE_URL}">
  <meta name="twitter:title" content="{SITE_TITLE}">
  <meta name="twitter:description" content="{safe_description}">
  """


def update_seo_meta(seo_meta: str) -> None:
    """Atualiza apenas as meta tags SEO no index.html."""
    text = INDEX_PATH.read_text(encoding="utf-8")
    seo_start = text.find(SEO_START)
    seo_end = text.find(SEO_END)
    if seo_start != -1 and seo_end != -1 and seo_end > seo_start:
        seo_after_end = seo_end + len(SEO_END)
        new_text = (
            text[:seo_start]
            + SEO_START
            + "\n"
            + seo_meta
            + "\n"
            + SEO_END
            + text[seo_after_end:]
        )
        INDEX_PATH.write_text(new_text, encoding="utf-8")


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_table(conn)
        migrate_schema(conn)
        upsert_from_in(conn)
        posts = get_posts(conn)
        export_posts_json(posts)
        seo_meta = generate_seo_meta(posts)
        update_seo_meta(seo_meta)
        generate_rss(posts)
        generate_sitemap(posts)
        delete_sources_after_ingest()
        print(f"OK: {len(posts)} post(s) exportados para posts.json, feed.xml e sitemap.xml")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
