#!/usr/bin/env python3
"""
Lê arquivos .txt em in/, persiste no SQLite (posts.db) e atualiza a seção blog em index.html.
Primeira linha do .txt = título; resto = corpo do post.
"""
import sqlite3
import markdown
import re
import unicodedata
from html import escape
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
IN_DIR = BASE / "in"
DB_PATH = BASE / "posts.db"
INDEX_PATH = BASE / "index.html"
RSS_PATH = BASE / "feed.xml"

BLOG_START = "<!-- BLOG_CONTENT -->"
BLOG_END = "<!-- /BLOG_CONTENT -->"


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)


def read_txt(path: Path) -> tuple[str, str] | None:
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
    if not IN_DIR.is_dir():
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for path in sorted(IN_DIR.glob("*.txt")):
        parsed = read_txt(path)
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


def delete_txt_after_ingest() -> None:
    """Remove os .txt em in/ após ingestão no DB (evita reingerir na próxima execução)."""
    if not IN_DIR.is_dir():
        return
    for path in IN_DIR.glob("*.txt"):
        try:
            path.unlink()
        except OSError:
            pass


def get_posts(conn: sqlite3.Connection) -> list[tuple[str, str, str]]:
    cur = conn.execute(
        "SELECT title, body, created_at FROM posts ORDER BY created_at DESC"
    )
    return cur.fetchall()




def format_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
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


def _routing_script() -> str:
    return r"""
<script>
(function() {
  function route() {
    var hash = window.location.hash.substring(1);
    var blogList = document.getElementById('blog-list');
    var postsContainer = document.getElementById('blog-posts-container');
    var posts = document.querySelectorAll('.blog-post');

    if (!hash) {
      if (blogList) blogList.style.display = 'block';
      if (postsContainer) postsContainer.style.display = 'none';
      for (var i = 0; i < posts.length; i++) {
        posts[i].style.display = 'none';
      }
    } else {
      if (blogList) blogList.style.display = 'none';
      if (postsContainer) postsContainer.style.display = 'block';
      var found = false;
      for (var i = 0; i < posts.length; i++) {
        if (posts[i].id === hash) {
          posts[i].style.display = 'block';
          found = true;
        } else {
          posts[i].style.display = 'none';
        }
      }
      if (!found && blogList) {
        window.location.hash = '';
      }
    }
    window.scrollTo(0, 0);
  }
  window.addEventListener('hashchange', route);
  window.addEventListener('load', route);
})();
</script>"""




def render_blog_html(posts: list[tuple[str, str, str]]) -> str:
    if not posts:
        return '<section id="blog" class="blog"></section>'
    parts = ['<section id="blog" class="blog">']

    # List view
    parts.append('  <div id="blog-list">')
    for title, _, created_at in posts:
        slug = slugify(title)
        safe_title = escape(title)
        date_str = format_date(created_at)
        parts.append(f'    <div class="blog-list-item"><span class="blog-list-date">{date_str}</span> <a href="#{slug}">{safe_title}</a></div>')
    parts.append('  </div>')

    # Post view
    parts.append('  <div id="blog-posts-container" style="display:none;">')
    for title, body, created_at in posts:
        slug = slugify(title)
        safe_title = escape(title)
        html_body = markdown.markdown(body, extensions=['fenced_code', 'codehilite', 'tables'])
        date_str = format_date(created_at)
        parts.append(
            f'    <article class="blog-post" id="{slug}" style="display:none;">'
            f'      <div class="blog-nav"><a href="#">&lt;-- Voltar</a></div>'
            f'      <h2>{safe_title}</h2>'
            f'      <p class="blog-date">{date_str}</p>'
            f'      <div class="blog-body">{html_body}</div>'
            f'    </article>'
        )
    parts.append('  </div>')

    parts.append(_routing_script())
    parts.append("</section>")
    return "\n".join(parts)


def generate_rss(posts: list[tuple[str, str, str]]) -> None:
    """Gera um arquivo RSS 2.0 básico."""
    items = []
    # Usamos o domínio murad.gg como base (ajuste conforme necessário)
    base_url = "https://murad.gg"

    for title, body, created_at in posts:
        slug = slugify(title)
        safe_title = escape(title)
        html_body = markdown.markdown(body, extensions=['fenced_code', 'codehilite', 'tables'])
        safe_body = escape(html_body)
        # Formata data para o padrão RSS (RFC 822)
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S %z")
        except Exception:
            pub_date = created_at

        items.append(f"""    <item>
      <title>{safe_title}</title>
      <link>{base_url}#{slug}</link>
      <description>{safe_body}</description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="false">{title}-{created_at}</guid>
    </item>""")

    rss_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>murad.gg</title>
  <link>{base_url}</link>
  <description>Blog pessoal de murad</description>
  <language>pt-br</language>
{"\n".join(items)}
</channel>
</rss>"""
    RSS_PATH.write_text(rss_content, encoding="utf-8")


def update_index(html_content: str) -> None:
    text = INDEX_PATH.read_text(encoding="utf-8")
    start_idx = text.find(BLOG_START)
    end_idx = text.find(BLOG_END)
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        raise SystemExit("Marcadores BLOG_CONTENT não encontrados em index.html")
    after_end = end_idx + len(BLOG_END)
    new_text = (
        text[:start_idx]
        + BLOG_START
        + "\n"
        + html_content
        + "\n"
        + BLOG_END
        + text[after_end:]
    )
    INDEX_PATH.write_text(new_text, encoding="utf-8")


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_table(conn)
        upsert_from_in(conn)
        posts = get_posts(conn)
        html = render_blog_html(posts)
        update_index(html)
        generate_rss(posts)
        delete_txt_after_ingest()
        print(f"OK: {len(posts)} post(s) em index.html e feed.xml")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
