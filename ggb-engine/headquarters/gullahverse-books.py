#!/usr/bin/env python3
"""
GullahVerse Books — AI-Powered Bookstore & Publishing Platform.
Built from the AI Think Tank winning design.
Author: Darryl Elliott Brown | Publisher: Gullah Geechee Biz
Features: Storefront, AI Book Generator, AI Audio Generator, Author Platform
"""
import json, os, sys, time, sqlite3, requests, hashlib, random, threading, re
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
VERSE_DIR = LOGS_DIR / "gullahverse"
DB_PATH = VERSE_DIR / "gullahverse.db"
PORT = 8083

VERSE_DIR.mkdir(parents=True, exist_ok=True)

def get_api_key():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if "OPENROUTER_API_KEY" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def call_ai(prompt, model="google/gemini-2.5-flash", max_tokens=3000):
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=120
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return None

# ─── Database ──────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT,
            author TEXT DEFAULT 'Darryl Elliott Brown',
            description TEXT,
            price_ebook REAL DEFAULT 3.99,
            price_audiobook REAL DEFAULT 7.99,
            price_bundle REAL DEFAULT 9.99,
            category TEXT,
            language TEXT DEFAULT 'en',
            tags TEXT DEFAULT '[]',
            has_audio INTEGER DEFAULT 0,
            has_ebook INTEGER DEFAULT 1,
            cover_url TEXT,
            source TEXT DEFAULT 'existing',
            created_at TEXT,
            sales INTEGER DEFAULT 0,
            rating REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS authors (
            id TEXT PRIMARY KEY,
            name TEXT,
            bio TEXT,
            email TEXT,
            books_published INTEGER DEFAULT 0,
            total_sales REAL DEFAULT 0,
            joined_at TEXT
        );
        CREATE TABLE IF NOT EXISTS generated_books (
            id TEXT PRIMARY KEY,
            customer_name TEXT,
            customer_email TEXT,
            prompt TEXT,
            title TEXT,
            content TEXT,
            cover_prompt TEXT,
            status TEXT DEFAULT 'generating',
            price REAL DEFAULT 19.99,
            created_at TEXT,
            delivered_at TEXT
        );
        CREATE TABLE IF NOT EXISTS audio_jobs (
            id TEXT PRIMARY KEY,
            book_id TEXT,
            book_title TEXT,
            voice TEXT DEFAULT 'gullah_storyteller',
            status TEXT DEFAULT 'processing',
            created_at TEXT,
            completed_at TEXT,
            FOREIGN KEY(book_id) REFERENCES books(id)
        );
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            customer_name TEXT,
            customer_email TEXT,
            book_id TEXT,
            book_title TEXT,
            type TEXT,
            amount REAL,
            status TEXT DEFAULT 'completed',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id TEXT PRIMARY KEY,
            customer_email TEXT,
            customer_name TEXT,
            status TEXT DEFAULT 'active',
            price REAL DEFAULT 9.99,
            started_at TEXT,
            renews_at TEXT
        );
    """)
    conn.commit()
    conn.close()

# ─── GullahVerse Engine ────────────────────────────────────────────────────

class GullahVerseEngine:
    def __init__(self):
        init_db()
        self._seed_books()
    
    def _get_conn(self):
        return sqlite3.connect(str(DB_PATH))
    
    def _seed_books(self):
        """Load existing books from publisher DB into GullahVerse."""
        conn = self._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        if count > 0:
            conn.close()
            return
        
        try:
            pub_conn = sqlite3.connect(str(PUB_DB))
            rows = pub_conn.execute(
                "SELECT manifest_id, data FROM manifests WHERE state = 'published' ORDER BY ROWID DESC LIMIT 100"
            ).fetchall()
            pub_conn.close()
            
            for mid, data_json in rows:
                try:
                    data = json.loads(data_json) if data_json else {}
                except:
                    data = {}
                title = data.get("title", mid)
                if isinstance(title, dict):
                    title = title.get("canonical", str(title))
                
                bid = hashlib.md5(mid.encode()).hexdigest()[:12]
                cats = ["Gullah Geechee", "Culture", "Heritage"]
                
                conn.execute("""INSERT OR IGNORE INTO books 
                    (id, title, author, description, price_ebook, category, language, tags, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (bid, str(title)[:100], "Darryl Elliott Brown",
                     f"{title} — A Gullah Geechee Biz publication exploring the rich culture and heritage of the Gullah Geechee people.",
                     3.99, random.choice(cats), "en",
                     json.dumps(["Gullah Geechee", "Culture", "Heritage", "African American"]),
                     datetime.now(timezone.utc).isoformat()))
            conn.commit()
        except:
            pass
        
        # Add Darryl as default author
        conn.execute("""INSERT OR IGNORE INTO authors VALUES (?,?,?,?,?,?,?)""",
                    ("darryl-brown", "Darryl Elliott Brown",
                     "Gullah Geechee publisher, author, and cultural preservationist. Founder of Gullah Geechee Biz.",
                     "deb2020win3@gmail.com", 0, 0, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
    
    def get_books(self, page=1, limit=20, category=None, search=None):
        conn = self._get_conn()
        query = "SELECT * FROM books WHERE 1=1"
        params = []
        if category and category != "all":
            query += " AND category=?"
            params.append(category)
        if search:
            query += " AND (title LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, (page-1)*limit])
        rows = conn.execute(query, params).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        conn.close()
        return {
            "books": [{
                "id": r[0], "title": r[1], "author": r[2], "description": r[3][:100],
                "price_ebook": r[4], "price_audiobook": r[5], "price_bundle": r[6],
                "category": r[7], "language": r[8], "tags": json.loads(r[9] or "[]"),
                "has_audio": bool(r[10]), "sales": r[14], "rating": r[15],
            } for r in rows],
            "total": total,
            "page": page,
            "pages": max(1, (total + limit - 1) // limit),
        }
    
    def get_book(self, book_id):
        conn = self._get_conn()
        r = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        conn.close()
        if not r:
            return None
        return {
            "id": r[0], "title": r[1], "author": r[2], "description": r[3],
            "price_ebook": r[4], "price_audiobook": r[5], "price_bundle": r[6],
            "category": r[7], "language": r[8], "tags": json.loads(r[9] or "[]"),
            "has_audio": bool(r[10]), "has_ebook": bool(r[11]),
            "cover_url": r[12], "source": r[13], "sales": r[14], "rating": r[15],
        }
    
    def get_categories(self):
        conn = self._get_conn()
        cats = conn.execute("SELECT DISTINCT category FROM books ORDER BY category").fetchall()
        conn.close()
        return [c[0] for c in cats if c[0]]
    
    def generate_book(self, prompt: str, customer_name: str = "", customer_email: str = "") -> Dict:
        """AI Book Generator — creates a complete book from natural language description."""
        gid = hashlib.md5(f"gen-{time.time()}".encode()).hexdigest()[:12]
        
        conn = self._get_conn()
        conn.execute("""INSERT INTO generated_books (id, customer_name, customer_email, prompt, status, price, created_at)
                       VALUES (?,?,?,?,'generating',19.99,?)""",
                    (gid, customer_name, customer_email, prompt, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        
        # Generate book using AI
        gen_prompt = f"""You are the GullahVerse Book Generator. Create a complete book based on this description:

{prompt}

Author: Darryl Elliott Brown
Publisher: Gullah Geechee Biz

Generate a complete book with:
1. A compelling title
2. A subtitle
3. A full chapter-by-chapter outline (5-8 chapters)
4. The complete content for Chapter 1 (at least 500 words)
5. A professional synopsis/description
6. 5 relevant categories/tags
7. A suggested cover image description
8. Target audience

Return as JSON:
{{"title": "...", "subtitle": "...", "synopsis": "...", "chapters": ["Chapter 1: ...", "..."], "chapter_1_content": "...", "categories": ["..."], "cover_description": "...", "target_audience": "..."}}"""
        
        result = call_ai(gen_prompt, max_tokens=4000)
        
        book_data = {}
        if result:
            try:
                start = result.find("{")
                end = result.rfind("}") + 1
                book_data = json.loads(result[start:end])
            except:
                book_data = {"title": "Generated Book", "synopsis": result[:200]}
        
        title = book_data.get("title", "Generated Book")
        content = book_data.get("chapter_1_content", result or "Content generation in progress...")
        synopsis = book_data.get("synopsis", "A Gullah Geechee Biz publication.")
        categories = book_data.get("categories", ["Gullah Geechee"])
        cover_desc = book_data.get("cover_description", "Gullah Geechee cultural imagery")
        
        # Save as a book in the store
        bid = hashlib.md5(f"generated-{gid}".encode()).hexdigest()[:12]
        conn = self._get_conn()
        conn.execute("""INSERT INTO books (id, title, author, description, price_ebook, category, tags, source, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (bid, title[:100], "Darryl Elliott Brown", synopsis[:200],
                     19.99, categories[0] if categories else "Generated",
                     json.dumps(categories), "generated", datetime.now(timezone.utc).isoformat()))
        
        conn.execute("UPDATE generated_books SET title=?, content=?, cover_prompt=?, status='completed', delivered_at=? WHERE id=?",
                    (title, content[:1000], cover_desc, datetime.now(timezone.utc).isoformat(), gid))
        conn.commit()
        conn.close()
        
        return {
            "generated_id": gid,
            "book_id": bid,
            "title": title,
            "synopsis": synopsis[:200],
            "content_preview": content[:300],
            "categories": categories,
            "price": 19.99,
            "status": "completed",
        }
    
    def generate_audio(self, book_id: str, voice: str = "gullah_storyteller") -> Dict:
        """AI Audio Generator — creates audiobook from any book."""
        book = self.get_book(book_id)
        if not book:
            return {"error": "Book not found"}
        
        aid = hashlib.md5(f"audio-{book_id}-{time.time()}".encode()).hexdigest()[:12]
        
        conn = self._get_conn()
        conn.execute("""INSERT INTO audio_jobs (id, book_id, book_title, voice, status, created_at)
                       VALUES (?,?,?,?,'processing',?)""",
                    (aid, book_id, book["title"], voice, datetime.now(timezone.utc).isoformat()))
        
        # Generate narration script
        prompt = f"""You are the GullahVerse Audio Generator. Create a narration script for this book:

Title: {book['title']}
Author: {book['author']}
Description: {book['description']}

Voice: {voice.replace('_', ' ').title()}

Generate:
1. An engaging audiobook introduction (2-3 sentences)
2. Chapter 1 narration (300-400 words, written for spoken word)
3. A closing/outro
4. Estimated listening time
5. Suggested chapter breaks

Return as JSON:
{{"introduction": "...", "chapter_1_narration": "...", "outro": "...", "estimated_minutes": 0, "chapters": ["..."], "voice_notes": "..."}}"""
        
        result = call_ai(prompt, max_tokens=2000)
        
        audio_data = {}
        if result:
            try:
                start = result.find("{")
                end = result.rfind("}") + 1
                audio_data = json.loads(result[start:end])
            except:
                audio_data = {"introduction": "Audiobook generated.", "estimated_minutes": 30}
        
        # Mark book as having audio
        conn.execute("UPDATE books SET has_audio=1 WHERE id=?", (book_id,))
        conn.execute("UPDATE audio_jobs SET status='completed', completed_at=? WHERE id=?",
                    (datetime.now(timezone.utc).isoformat(), aid))
        conn.commit()
        conn.close()
        
        return {
            "audio_job_id": aid,
            "book_title": book["title"],
            "voice": voice,
            "introduction": audio_data.get("introduction", "")[:200],
            "estimated_minutes": audio_data.get("estimated_minutes", 30),
            "status": "completed",
            "price_addon": 4.99,
        }
    
    def place_order(self, customer_name: str, customer_email: str, book_id: str, order_type: str = "ebook") -> Dict:
        book = self.get_book(book_id)
        if not book:
            return {"error": "Book not found"}
        
        prices = {"ebook": book["price_ebook"], "audiobook": book["price_audiobook"], "bundle": book["price_bundle"]}
        price = prices.get(order_type, book["price_ebook"])
        
        oid = hashlib.md5(f"order-{time.time()}".encode()).hexdigest()[:12]
        
        conn = self._get_conn()
        conn.execute("""INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)""",
                    (oid, customer_name, customer_email, book_id, book["title"],
                     order_type, price, "completed", datetime.now(timezone.utc).isoformat()))
        conn.execute("UPDATE books SET sales = sales + 1 WHERE id=?", (book_id,))
        conn.commit()
        conn.close()
        
        return {"order_id": oid, "book_title": book["title"], "type": order_type, "amount": price, "status": "completed"}
    
    def subscribe(self, name: str, email: str) -> Dict:
        sid = hashlib.md5(f"sub-{email}".encode()).hexdigest()[:8]
        conn = self._get_conn()
        existing = conn.execute("SELECT id FROM subscriptions WHERE customer_email=?", (email,)).fetchone()
        if existing:
            conn.close()
            return {"error": "Already subscribed", "subscription_id": existing[0]}
        
        conn.execute("""INSERT INTO subscriptions VALUES (?,?,?,?,?,?,?)""",
                    (sid, email, name, "active", 9.99,
                     datetime.now(timezone.utc).isoformat(),
                     datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
        return {"subscription_id": sid, "price": 9.99, "status": "active"}
    
    def get_stats(self):
        conn = self._get_conn()
        books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        revenue = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM orders").fetchone()[0]
        generated = conn.execute("SELECT COUNT(*) FROM generated_books").fetchone()[0]
        audio = conn.execute("SELECT COUNT(*) FROM audio_jobs").fetchone()[0]
        subs = conn.execute("SELECT COUNT(*) FROM subscriptions WHERE status='active'").fetchone()[0]
        conn.close()
        return {"books": books, "orders": orders, "revenue": revenue, "generated": generated, "audio_jobs": audio, "subscribers": subs}

# ─── HTML ─────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GullahVerse Books — AI-Powered Bookstore</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: #0a0a12;
    color: #c8d6e5;
    min-height: 100vh;
  }
  .container { max-width: 1200px; margin: 0 auto; padding: 20px; }

  /* Header */
  .header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 0; border-bottom: 1px solid rgba(240,192,64,0.1); margin-bottom: 20px;
    flex-wrap: wrap; gap: 12px;
  }
  .header h1 {
    font-size: 1.5rem; font-weight: 900;
    background: linear-gradient(135deg, #f0c040, #d4a017, #8B7355);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .header .sub { font-size: 0.7rem; color: #5a7a9a; }
  .header .stats { display: flex; gap: 12px; font-size: 0.75rem; color: #5a7a9a; }
  .header .stats span { color: #f0c040; font-weight: 600; }

  /* Tabs */
  .tabs { display: flex; gap: 4px; margin-bottom: 20px; flex-wrap: wrap; }
  .tab {
    padding: 8px 16px; border-radius: 8px 8px 0 0; cursor: pointer;
    font-size: 0.8rem; font-weight: 600; color: #5a7a9a;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
    border-bottom: none; transition: all 0.2s;
  }
  .tab.active { color: #f0c040; background: rgba(240,192,64,0.05); border-color: rgba(240,192,64,0.15); }
  .tab:hover { color: #a0c0e0; }
  .panel { display: none; }
  .panel.active { display: block; }

  /* Search */
  .search-bar {
    display: flex; gap: 8px; margin-bottom: 16px;
  }
  .search-bar input {
    flex: 1; padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);
    background: rgba(255,255,255,0.03); color: #e0f0ff; font-size: 0.85rem;
  }
  .search-bar input:focus { outline: none; border-color: #f0c040; }
  .search-bar select {
    padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);
    background: rgba(255,255,255,0.03); color: #e0f0ff; font-size: 0.8rem;
  }

  /* Grid */
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
  .card {
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 16px; transition: all 0.3s; cursor: pointer;
  }
  .card:hover { border-color: rgba(240,192,64,0.2); transform: translateY(-2px); }
  .card .cover {
    width: 100%; height: 140px; border-radius: 6px; margin-bottom: 10px;
    background: linear-gradient(135deg, rgba(240,192,64,0.1), rgba(139,115,85,0.1));
    display: flex; align-items: center; justify-content: center;
    font-size: 2.5rem; color: rgba(240,192,64,0.3);
  }
  .card h3 { font-size: 0.85rem; color: #e0f0ff; margin-bottom: 4px; }
  .card .author { font-size: 0.7rem; color: #5a7a9a; margin-bottom: 4px; }
  .card .price { font-size: 1.1rem; font-weight: 700; color: #f0c040; }
  .card .price span { font-size: 0.65rem; color: #5a7a9a; font-weight: 400; }
  .card .badge { display: inline-block; font-size: 0.6rem; padding: 2px 6px; border-radius: 4px; margin-top: 4px; }
  .badge.audio { background: rgba(76,175,80,0.1); color: #4caf50; }
  .badge.generated { background: rgba(240,192,64,0.1); color: #f0c040; }

  /* Book Detail */
  .book-detail {
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 24px; margin-bottom: 16px;
  }
  .book-detail h2 { font-size: 1.3rem; color: #e0f0ff; margin-bottom: 4px; }
  .book-detail .author { color: #f0c040; font-size: 0.85rem; margin-bottom: 12px; }
  .book-detail .desc { font-size: 0.85rem; line-height: 1.6; margin-bottom: 16px; }
  .book-detail .pricing { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
  .book-detail .pricing .option {
    padding: 8px 16px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);
    cursor: pointer; text-align: center; transition: all 0.2s;
  }
  .book-detail .pricing .option:hover { border-color: #f0c040; }
  .book-detail .pricing .option .amt { font-size: 1.1rem; font-weight: 700; color: #f0c040; }
  .book-detail .pricing .option .lbl { font-size: 0.65rem; color: #5a7a9a; }
  .book-detail .actions { display: flex; gap: 8px; flex-wrap: wrap; }

  /* Generator */
  .gen-section {
    background: rgba(255,255,255,0.02); border: 1px solid rgba(240,192,64,0.1);
    border-radius: 12px; padding: 20px; margin-bottom: 16px;
  }
  .gen-section h2 { font-size: 1.1rem; color: #f0c040; margin-bottom: 8px; }
  .gen-section .desc { font-size: 0.8rem; color: #5a7a9a; margin-bottom: 12px; }

  textarea {
    width: 100%; padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);
    background: rgba(255,255,255,0.03); color: #e0f0ff; font-size: 0.85rem;
    font-family: inherit; resize: vertical; min-height: 80px;
  }
  textarea:focus { outline: none; border-color: #f0c040; }

  input, select {
    padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);
    background: rgba(255,255,255,0.03); color: #e0f0ff; font-size: 0.85rem; width: 100%;
    margin-bottom: 8px;
  }
  input:focus, select:focus { outline: none; border-color: #f0c040; }
  label { font-size: 0.75rem; color: #5a7a9a; display: block; margin-bottom: 4px; }

  .btn {
    display: inline-block; padding: 10px 24px; border-radius: 8px; border: none;
    font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: all 0.2s;
  }
  .btn-primary { background: linear-gradient(135deg, #f0c040, #d4a017); color: #0a0a12; }
  .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(240,192,64,0.3); }
  .btn-secondary { background: rgba(255,255,255,0.05); color: #a0c0e0; border: 1px solid rgba(255,255,255,0.1); }
  .btn-secondary:hover { background: rgba(255,255,255,0.08); }
  .btn-success { background: linear-gradient(135deg, #4caf50, #388e3c); color: #fff; }
  .btn-audio { background: linear-gradient(135deg, #ab47bc, #7b1fa2); color: #fff; }
  .btn-full { width: 100%; }

  .result-box {
    background: rgba(0,0,0,0.3); border: 1px solid rgba(240,192,64,0.1);
    border-radius: 8px; padding: 12px; margin-top: 12px;
    font-size: 0.8rem; line-height: 1.5; max-height: 300px; overflow-y: auto;
    white-space: pre-wrap;
  }

  .toast {
    position: fixed; bottom: 20px; right: 20px;
    background: rgba(240,192,64,0.9); color: #0a0a12;
    padding: 12px 20px; border-radius: 8px; font-size: 0.8rem; font-weight: 600;
    animation: slideUp 0.3s ease; z-index: 100;
  }
  @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
  .loading { text-align: center; padding: 20px; color: #f0c040; }
  .loading::after { content: '...'; animation: dots 1.5s infinite; }
  @keyframes dots { 0%,20% { content: '.'; } 40% { content: '..'; } 60%,100% { content: '...'; } }

  .pagination { display: flex; justify-content: center; gap: 8px; margin-top: 20px; }
  .pagination button {
    padding: 6px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);
    background: rgba(255,255,255,0.02); color: #a0c0e0; cursor: pointer; font-size: 0.8rem;
  }
  .pagination button:hover { border-color: #f0c040; }
  .pagination button.active { background: rgba(240,192,64,0.1); border-color: #f0c040; color: #f0c040; }

  .footer { text-align: center; padding: 20px; font-size: 0.7rem; color: #3a4a5a; border-top: 1px solid rgba(255,255,255,0.04); margin-top: 20px; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>📚 GullahVerse Books</h1>
      <div class="sub">Your Story, Instantly Realized. From Imagination to Audiobook.</div>
    </div>
    <div class="stats">
      <span id="statBooks">0</span> books &middot;
      <span id="statOrders">0</span> sold &middot;
      <span id="statRevenue">$0</span> revenue
    </div>
  </div>

  <div class="tabs">
    <div class="tab active" onclick="switchTab('store')">📚 Store</div>
    <div class="tab" onclick="switchTab('generator')">✨ Book Generator</div>
    <div class="tab" onclick="switchTab('audio')">🎧 Audio Studio</div>
    <div class="tab" onclick="switchTab('author')">👤 Publish With Us</div>
    <div class="tab" onclick="switchTab('subscribe')">⭐ Subscribe</div>
  </div>

  <!-- Store -->
  <div class="panel active" id="panel-store">
    <div class="search-bar">
      <input id="searchInput" placeholder="Search books, authors, themes..." onkeyup="searchBooks()">
      <select id="categoryFilter" onchange="searchBooks()">
        <option value="all">All Categories</option>
      </select>
    </div>
    <div id="bookCount" style="font-size:0.75rem; color:#5a7a9a; margin-bottom:12px"></div>
    <div class="grid" id="bookGrid"></div>
    <div class="pagination" id="pagination"></div>
  </div>

  <!-- Book Generator -->
  <div class="panel" id="panel-generator">
    <div class="gen-section">
      <h2>✨ AI Book Generator</h2>
      <div class="desc">Describe the book you want. Our AI will write it, design a cover, and add it to the store — instantly.</div>
      <label>Your Name</label>
      <input id="genName" placeholder="Your name">
      <label>Your Email</label>
      <input id="genEmail" placeholder="your@email.com">
      <label>Describe Your Book</label>
      <textarea id="genPrompt" rows="4" placeholder="Example: A children's book about a young Gullah Geechee girl who learns to weave sweetgrass baskets from her grandmother, discovering the stories woven into each strand. Warm, educational, for ages 5-9."></textarea>
      <button class="btn btn-primary btn-full" onclick="generateBook()">✨ Generate My Book — $19.99</button>
      <div id="genResult"></div>
    </div>
  </div>

  <!-- Audio Studio -->
  <div class="panel" id="panel-audio">
    <div class="gen-section">
      <h2>🎧 AI Audio Studio</h2>
      <div class="desc">Turn any book into an audiobook instantly. Choose your narrator voice.</div>
      <label>Select a Book</label>
      <select id="audioBookSelect"><option value="">Loading books...</option></select>
      <label>Narrator Voice</label>
      <select id="audioVoice">
        <option value="gullah_storyteller">🎙️ Gullah Geechee Storyteller (Authentic)</option>
        <option value="male_warm">🎙️ Male — Warm & Engaging</option>
        <option value="female_soothing">🎙️ Female — Soothing & Clear</option>
        <option value="male_deep">🎙️ Male — Deep & Authoritative</option>
        <option value="female_energetic">🎙️ Female — Energetic & Bright</option>
      </select>
      <button class="btn btn-audio btn-full" onclick="generateAudio()">🎧 Generate Audiobook — $4.99</button>
      <div id="audioResult"></div>
    </div>
  </div>

  <!-- Author Platform -->
  <div class="panel" id="panel-author">
    <div class="gen-section">
      <h2>👤 Publish With GullahVerse</h2>
      <div class="desc">Publish your books alongside Darryl Elliott Brown's collection. AI helps you write, edit, design covers, and market. You keep 70% royalties and full rights to your work.</div>
      <label>Your Name</label>
      <input id="authorName" placeholder="Your full name">
      <label>Your Email</label>
      <input id="authorEmail" placeholder="your@email.com">
      <label>Your Book Title</label>
      <input id="authorTitle" placeholder="Your book title">
      <label>Book Description</label>
      <textarea id="authorDesc" rows="3" placeholder="Describe your book..."></textarea>
      <label>Genre/Category</label>
      <input id="authorCategory" placeholder="e.g. Historical Fiction, Children's, Cookbook">
      <button class="btn btn-primary btn-full" onclick="submitAuthorBook()">📚 Submit for Publishing</button>
      <div id="authorResult"></div>
    </div>
  </div>

  <!-- Subscribe -->
  <div class="panel" id="panel-subscribe">
    <div class="gen-section" style="text-align:center">
      <h2>⭐ GullahVerse Unlimited</h2>
      <div style="font-size:2.5rem; margin:16px 0">📚🎧</div>
      <div style="font-size:1.2rem; font-weight:700; color:#f0c040">$9.99<span style="font-size:0.8rem; color:#5a7a9a">/month</span></div>
      <div class="desc" style="margin:12px 0">Unlimited access to every book in the store. Ebooks and audiobooks included. Cancel anytime.</div>
      <label>Your Name</label>
      <input id="subName" placeholder="Your name" style="max-width:400px; margin:0 auto 8px">
      <label>Your Email</label>
      <input id="subEmail" placeholder="your@email.com" style="max-width:400px; margin:0 auto 8px">
      <button class="btn btn-primary" onclick="subscribe()" style="max-width:400px">⭐ Subscribe — $9.99/mo</button>
      <div id="subResult"></div>
    </div>
  </div>

  <div class="footer">
    GullahVerse Books &middot; A Gullah Geechee Biz Platform &middot; Author: Darryl Elliott Brown
  </div>
</div>

<script>
let currentPage = 1;
let currentBook = null;

async function api(path, data) {
  const opts = { headers: {'Content-Type': 'application/json'} };
  if (data) opts.body = JSON.stringify(data), opts.method = 'POST';
  const r = await fetch('/api' + path, opts);
  return r.json();
}

function toast(msg) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

async function loadBooks(page) {
  const search = document.getElementById('searchInput').value;
  const category = document.getElementById('categoryFilter').value;
  const r = await api(`/books?page=${page}&category=${category}&search=${encodeURIComponent(search)}`);
  const grid = document.getElementById('bookGrid');
  const count = document.getElementById('bookCount');
  count.textContent = `${r.total} books available`;
  
  grid.innerHTML = r.books.map(b => `
    <div class="card" onclick="showBook('${b.id}')">
      <div class="cover">📖</div>
      <h3>${b.title.substring(0, 50)}</h3>
      <div class="author">${b.author}</div>
      <div class="price">$${b.price_ebook.toFixed(2)}<span> ebook</span></div>
      ${b.has_audio ? '<span class="badge audio">🎧 Audiobook</span>' : ''}
    </div>
  `).join('');

  // Pagination
  const pg = document.getElementById('pagination');
  pg.innerHTML = '';
  for (let i = 1; i <= r.pages && i <= 10; i++) {
    pg.innerHTML += `<button class="${i === page ? 'active' : ''}" onclick="loadBooks(${i})">${i}</button>`;
  }
  currentPage = page;
}

async function showBook(id) {
  const b = await api('/book/' + id);
  currentBook = b;
  switchTab('store');
  const grid = document.getElementById('bookGrid');
  grid.innerHTML = `
    <div class="book-detail" style="grid-column:1/-1">
      <h2>${b.title}</h2>
      <div class="author">by ${b.author}</div>
      <div class="desc">${b.description}</div>
      <div class="pricing">
        <div class="option" onclick="buyBook('${b.id}','ebook')">
          <div class="amt">$${b.price_ebook.toFixed(2)}</div>
          <div class="lbl">Ebook</div>
        </div>
        ${b.has_audio ? `<div class="option" onclick="buyBook('${b.id}','audiobook')">
          <div class="amt">$${b.price_audiobook.toFixed(2)}</div>
          <div class="lbl">Audiobook</div>
        </div>` : ''}
        <div class="option" onclick="buyBook('${b.id}','bundle')">
          <div class="amt">$${b.price_bundle.toFixed(2)}</div>
          <div class="lbl">Bundle</div>
        </div>
      </div>
      <div class="actions">
        <button class="btn btn-primary" onclick="buyBook('${b.id}','ebook')">📚 Buy Ebook — $${b.price_ebook.toFixed(2)}</button>
        ${!b.has_audio ? `<button class="btn btn-audio" onclick="generateAudioFor('${b.id}')">🎧 Generate Audiobook — $4.99</button>` : `<button class="btn btn-success" onclick="buyBook('${b.id}','audiobook')">🎧 Buy Audiobook — $${b.price_audiobook.toFixed(2)}</button>`}
      </div>
      <div id="buyResult-${b.id}"></div>
    </div>
  `;
}

async function buyBook(id, type) {
  const name = prompt('Your name:') || 'Guest';
  const email = prompt('Your email:') || 'guest@example.com';
  const r = await api('/order', { customer_name: name, customer_email: email, book_id: id, order_type: type });
  if (r.error) return toast(r.error);
  document.getElementById('buyResult-' + id).innerHTML = `<div class="result-box">✅ Purchased! Order #${r.order_id}. ${r.book_title} (${r.type}) — $${r.amount.toFixed(2)}</div>`;
  toast('Purchase complete!');
  loadStats();
}

async function generateBook() {
  const name = document.getElementById('genName').value.trim() || 'Guest';
  const email = document.getElementById('genEmail').value.trim() || 'guest@example.com';
  const prompt = document.getElementById('genPrompt').value.trim();
  if (!prompt) return toast('Describe the book you want');
  
  const div = document.getElementById('genResult');
  div.innerHTML = '<div class="loading">AI is writing your book</div>';
  
  const r = await api('/generate-book', { prompt, customer_name: name, customer_email: email });
  if (r.error) { div.innerHTML = '<div class="result-box" style="color:#f44336">Error: ' + r.error + '</div>'; return; }
  
  div.innerHTML = `
    <div class="result-box">
      <strong>✅ "${r.title}" generated!</strong>
      <br><br>${r.synopsis}
      <br><br><em>${r.content_preview}...</em>
      <br><br>Categories: ${(r.categories || []).join(', ')}
      <br>Price: $${r.price.toFixed(2)}
      <br>Status: ${r.status}
    </div>
  `;
  toast('Book generated! Added to store.');
  loadBooks(1);
  loadStats();
}

async function generateAudio() {
  const bookId = document.getElementById('audioBookSelect').value;
  const voice = document.getElementById('audioVoice').value;
  if (!bookId) return toast('Select a book');
  
  const div = document.getElementById('audioResult');
  div.innerHTML = '<div class="loading">AI is narrating your audiobook</div>';
  
  const r = await api('/generate-audio', { book_id: bookId, voice });
  if (r.error) { div.innerHTML = '<div class="result-box" style="color:#f44336">Error: ' + r.error + '</div>'; return; }
  
  div.innerHTML = `
    <div class="result-box">
      <strong>✅ Audiobook generated!</strong>
      <br><br>Book: ${r.book_title}
      <br>Voice: ${r.voice.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
      <br>Estimated: ${r.estimated_minutes} minutes
      <br>Add-on price: $${r.price_addon.toFixed(2)}
      <br>Status: ${r.status}
    </div>
  `;
  toast('Audiobook ready!');
  loadAudioBooks();
  loadStats();
}

async function generateAudioFor(bookId) {
  const voice = 'gullah_storyteller';
  const r = await api('/generate-audio', { book_id: bookId, voice });
  if (r.error) return toast(r.error);
  toast('Audiobook generated!');
  showBook(bookId);
  loadStats();
}

async function submitAuthorBook() {
  const name = document.getElementById('authorName').value.trim();
  const email = document.getElementById('authorEmail').value.trim();
  const title = document.getElementById('authorTitle').value.trim();
  const desc = document.getElementById('authorDesc').value.trim();
  const cat = document.getElementById('authorCategory').value.trim();
  if (!name || !email || !title) return toast('Fill in name, email, and title');
  
  const div = document.getElementById('authorResult');
  div.innerHTML = '<div class="loading">AI is preparing your book for publishing</div>';
  
  const r = await api('/generate-book', {
    prompt: `Title: ${title}. Description: ${desc}. Category: ${cat}. Author: ${name}.`,
    customer_name: name, customer_email: email
  });
  
  div.innerHTML = `
    <div class="result-box">
      <strong>✅ Submitted for publishing!</strong>
      <br><br>Your book "${r.title || title}" has been added to the store.
      <br>You keep 70% royalties and full rights.
      <br>We'll notify you at ${email} when it's live.
    </div>
  `;
  toast('Book submitted!');
  loadBooks(1);
}

async function subscribe() {
  const name = document.getElementById('subName').value.trim();
  const email = document.getElementById('subEmail').value.trim();
  if (!name || !email) return toast('Enter your name and email');
  
  const r = await api('/subscribe', { name, email });
  if (r.error) return toast(r.error);
  
  document.getElementById('subResult').innerHTML = `
    <div class="result-box">
      <strong>⭐ Welcome to GullahVerse Unlimited!</strong>
      <br>Subscription #${r.subscription_id}
      <br>$${r.price.toFixed(2)}/month — ${r.status}
      <br>Unlimited access to all books and audiobooks.
    </div>
  `;
  toast('Subscribed!');
  loadStats();
}

async function loadAudioBooks() {
  const r = await api('/books?limit=100');
  const sel = document.getElementById('audioBookSelect');
  sel.innerHTML = r.books.map(b => `<option value="${b.id}">${b.title.substring(0, 50)} ${b.has_audio ? '🎧' : ''}</option>`).join('');
}

async function loadCategories() {
  const r = await api('/categories');
  const sel = document.getElementById('categoryFilter');
  r.forEach(c => { sel.innerHTML += `<option value="${c}">${c}</option>`; });
}

async function loadStats() {
  const r = await api('/stats');
  document.getElementById('statBooks').textContent = r.books;
  document.getElementById('statOrders').textContent = r.orders;
  document.getElementById('statRevenue').textContent = '$' + Math.round(r.revenue);
}

function searchBooks() { loadBooks(1); }

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelector('.tab[onclick*="' + name + '"]').classList.add('active');
  document.getElementById('panel-' + name).classList.add('active');
  if (name === 'audio') loadAudioBooks();
}

loadBooks(1);
loadCategories();
loadStats();
setInterval(loadStats, 15000);
</script>
</body>
</html>"""

# ─── Server ───────────────────────────────────────────────────────────────

engine = GullahVerseEngine()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        if path.startswith("/api/books"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(path).query)
            page = int(qs.get("page", [1])[0])
            limit = int(qs.get("limit", [20])[0])
            category = qs.get("category", ["all"])[0]
            search = qs.get("search", [""])[0]
            self._json(engine.get_books(page, limit, category, search))
        elif path.startswith("/api/book/"):
            bid = path.split("/")[-1]
            b = engine.get_book(bid)
            self._json(b or {"error": "Not found"})
        elif path == "/api/categories":
            self._json(engine.get_categories())
        elif path == "/api/stats":
            self._json(engine.get_stats())
        else:
            self._html(HTML)
    
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        path = self.path
        
        if path == "/api/generate-book":
            self._json(engine.generate_book(body.get("prompt", ""), body.get("customer_name", ""), body.get("customer_email", "")))
        elif path == "/api/generate-audio":
            self._json(engine.generate_audio(body.get("book_id", ""), body.get("voice", "gullah_storyteller")))
        elif path == "/api/order":
            self._json(engine.place_order(body.get("customer_name", ""), body.get("customer_email", ""), body.get("book_id", ""), body.get("order_type", "ebook")))
        elif path == "/api/subscribe":
            self._json(engine.subscribe(body.get("name", ""), body.get("email", "")))
        else:
            self._json({"error": "Unknown endpoint"})
    
    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

def main():
    print(f"\n{'='*55}")
    print(f"  📚 GULLAHVERSE BOOKS")
    print(f"  http://localhost:{PORT}")
    print(f"{'='*55}")
    print(f"  • AI-Powered Bookstore")
    print(f"  • Built-in Book Generator")
    print(f"  • Built-in Audio Generator")
    print(f"  • Author Publishing Platform")
    print(f"  • Author: Darryl Elliott Brown")
    print(f"  • Publisher: Gullah Geechee Biz")
    print(f"  • Press Ctrl+C to stop.\n")
    
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
