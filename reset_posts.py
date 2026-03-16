#!/usr/bin/env python3
"""
Remove todas as postagens do SQLite (posts.db) e atualiza index.html
com a seção do blog vazia e dados resetados.
"""
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "posts.db"
INDEX_PATH = BASE / "index.html"

DATA_START = '<script id="posts-data" type="application/json">'
DATA_END = '</script>'

def update_index_empty() -> None:
    text = INDEX_PATH.read_text(encoding="utf-8")

    # Limpa a seção blog visual se houver algo (geralmente gerado pelo JS, mas por segurança)
    # Mas o principal é limpar o JSON
    start_idx = text.find(DATA_START)
    if start_idx != -1:
        start_content = start_idx + len(DATA_START)
        end_idx = text.find(DATA_END, start_content)
        if end_idx != -1:
            text = text[:start_content] + "[]" + text[end_idx:]

    INDEX_PATH.write_text(text, encoding="utf-8")

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
    print("OK: index.html atualizada com dados vazios.")

if __name__ == "__main__":
    main()
