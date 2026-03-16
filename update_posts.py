#!/usr/bin/env python3
"""
Lê arquivos .txt em in/, persiste no SQLite (posts.db) e atualiza os dados em index.html.
Suporta Markdown no corpo do post.
"""
import sqlite3
import json
import markdown
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
IN_DIR = BASE / "in"
DB_PATH = BASE / "posts.db"
INDEX_PATH = BASE / "index.html"

DATA_START = '<script id="posts-data" type="application/json">'
DATA_END = '</script>'

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
            "SELECT id FROM posts WHERE title = ?", (title,)
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
    if not IN_DIR.is_dir():
        return
    for path in IN_DIR.glob("*.txt"):
        try:
            path.unlink()
        except OSError:
            pass

def format_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return iso

def get_posts_json(conn: sqlite3.Connection) -> str:
    cur = conn.execute(
        "SELECT id, title, body, created_at FROM posts ORDER BY created_at DESC"
    )
    rows = cur.fetchall()
    posts = []
    md = markdown.Markdown(extensions=['extra', 'nl2br'])
    for row in rows:
        posts.append({
            "id": row[0],
            "title": row[1],
            "body": md.convert(row[2]),
            "date": format_date(row[3])
        })
    return json.dumps(posts, ensure_ascii=False)

def update_index(json_data: str) -> None:
    text = INDEX_PATH.read_text(encoding="utf-8")
    start_idx = text.find(DATA_START)
    if start_idx == -1:
        # Tenta fallback se o ID mudou ou algo assim
        raise SystemExit(f"Marcador {DATA_START} não encontrado em index.html")

    start_content = start_idx + len(DATA_START)
    end_idx = text.find(DATA_END, start_content)

    if end_idx == -1:
        raise SystemExit(f"Marcador {DATA_END} não encontrado após o início dos dados.")

    new_text = text[:start_content] + json_data + text[end_idx:]
    INDEX_PATH.write_text(new_text, encoding="utf-8")

def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_table(conn)
        upsert_from_in(conn)
        json_data = get_posts_json(conn)
        update_index(json_data)
        delete_txt_after_ingest()
        # Conta posts para o log
        count = len(json.loads(json_data))
        print(f"OK: {count} post(s) processados e index.html atualizado.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
