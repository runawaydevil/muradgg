#!/usr/bin/env python3
"""
Remove todas as postagens do SQLite (posts.db) e atualiza index.html
com a seção do blog vazia.
"""
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "posts.db"
INDEX_PATH = BASE / "index.html"

BLOG_START = "<!-- BLOG_CONTENT -->"
BLOG_END = "<!-- /BLOG_CONTENT -->"


def update_index_empty() -> None:
    text = INDEX_PATH.read_text(encoding="utf-8")
    start_idx = text.find(BLOG_START)
    end_idx = text.find(BLOG_END)
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return
    after_end = end_idx + len(BLOG_END)
    empty_section = '<section id="blog" class="blog"></section>'
    new_text = (
        text[:start_idx]
        + BLOG_START
        + "\n"
        + empty_section
        + "\n"
        + BLOG_END
        + text[after_end:]
    )
    INDEX_PATH.write_text(new_text, encoding="utf-8")


def main() -> None:
    if not DB_PATH.exists():
        print("OK: posts.db não existe, nada a resetar.")
        update_index_empty()
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM posts")
        conn.commit()
        print("OK: Todas as postagens removidas do SQLite.")
    finally:
        conn.close()
    update_index_empty()
    print("OK: index.html atualizada com blog vazio.")


if __name__ == "__main__":
    main()
