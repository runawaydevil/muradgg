#!/usr/bin/env python3
"""
Lê arquivos .txt em in/, persiste no SQLite (posts.db) e atualiza a seção blog em index.html.
Primeira linha do .txt = título; resto = corpo do post.
"""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
IN_DIR = BASE / "in"
DB_PATH = BASE / "posts.db"
INDEX_PATH = BASE / "index.html"

BLOG_START = "<!-- BLOG_CONTENT -->"
BLOG_END = "<!-- /BLOG_CONTENT -->"
POSTS_PER_PAGE = 15


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


def escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return iso


def _pagination_script() -> str:
    return r"""
<script>
(function() {
  var PER_PAGE = 15;
  var blog = document.getElementById('blog');
  if (!blog) return;
  var posts = blog.querySelectorAll('.blog-post');
  if (posts.length <= PER_PAGE) return;
  var totalPages = Math.ceil(posts.length / PER_PAGE);
  var currentPage = 1;
  function showPage(page) {
    currentPage = page;
    var start = (page - 1) * PER_PAGE;
    var end = start + PER_PAGE;
    for (var i = 0; i < posts.length; i++) {
      posts[i].style.display = (i >= start && i < end) ? '' : 'none';
    }
    prevLink.className = page <= 1 ? 'blog-pagination-disabled' : '';
    nextLink.className = page >= totalPages ? 'blog-pagination-disabled' : '';
    prevLink.style.pointerEvents = page <= 1 ? 'none' : '';
    nextLink.style.pointerEvents = page >= totalPages ? 'none' : '';
    info.textContent = 'P\u00e1gina ' + page + ' de ' + totalPages;
  }
  var nav = document.createElement('nav');
  nav.className = 'blog-pagination';
  nav.setAttribute('aria-label', 'Navega\u00e7\u00e3o do blog');
  var prevLink = document.createElement('a');
  prevLink.href = '#';
  prevLink.textContent = 'Anterior';
  prevLink.addEventListener('click', function(e) {
    e.preventDefault();
    if (currentPage > 1) showPage(currentPage - 1);
  });
  var info = document.createElement('span');
  info.className = 'blog-pagination-info';
  var nextLink = document.createElement('a');
  nextLink.href = '#';
  nextLink.textContent = 'Pr\u00f3xima';
  nextLink.addEventListener('click', function(e) {
    e.preventDefault();
    if (currentPage < totalPages) showPage(currentPage + 1);
  });
  nav.appendChild(prevLink);
  nav.appendChild(info);
  nav.appendChild(nextLink);
  blog.appendChild(nav);
  showPage(1);
})();
</script>"""


def render_blog_html(posts: list[tuple[str, str, str]]) -> str:
    if not posts:
        return '<section id="blog" class="blog"></section>'
    parts = ['<section id="blog" class="blog">', '<div id="blog-posts-list">']
    for title, body, created_at in posts:
        safe_title = escape(title)
        safe_body = escape(body)
        date_str = format_date(created_at)
        parts.append(
            f'  <article class="blog-post">'
            f'<h2>{safe_title}</h2>'
            f'<p class="blog-date">{date_str}</p>'
            f'<div class="blog-body">{safe_body}</div>'
            f"</article>"
        )
    parts.append("</div>")
    if len(posts) > POSTS_PER_PAGE:
        parts.append(_pagination_script())
    parts.append("</section>")
    return "\n".join(parts)


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
        delete_txt_after_ingest()
        print(f"OK: {len(posts)} post(s) em index.html")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
