#!/usr/bin/env python3
"""
Gullah Hearth — The Unified Kinship & Conversion Engine.
The Digital Porch. The missing piece that 10x's the entire GGB ecosystem.
Built from the AI Think Tank winning design (30,924 chars).
Features: Soul Profiles, Binyah Concierge, Community, Common Chat, Kinship Subscriptions.
"""
import json, os, sys, time, sqlite3, requests, hashlib, random, threading, re
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
LOGS_DIR = Path(__file__).parent / "logs"
HEARTH_DIR = LOGS_DIR / "gullah-hearth"
DB_PATH = HEARTH_DIR / "hearth.db"
PORT = 8085

HEARTH_DIR.mkdir(parents=True, exist_ok=True)

def get_api_key():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if "OPENROUTER_API_KEY" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def call_ai(prompt, model="google/gemini-2.5-flash", max_tokens=2000):
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=60
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
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            display_name TEXT,
            email TEXT,
            password_hash TEXT,
            role TEXT DEFAULT 'member',
            soul_profile TEXT DEFAULT '{}',
            badges TEXT DEFAULT '[]',
            kinship_tier TEXT DEFAULT 'free',
            joined_at TEXT,
            last_seen TEXT
        );
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            username TEXT,
            display_name TEXT,
            message TEXT,
            channel TEXT DEFAULT 'general',
            platform TEXT DEFAULT 'hearth',
            reply_to TEXT,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS chat_channels (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            icon TEXT DEFAULT '💬',
            created_by TEXT,
            is_default INTEGER DEFAULT 0,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS soul_profiles (
            user_id TEXT PRIMARY KEY,
            interests TEXT DEFAULT '[]',
            purchases TEXT DEFAULT '[]',
            content_history TEXT DEFAULT '[]',
            platform_activity TEXT DEFAULT '{}',
            cultural_preferences TEXT DEFAULT '{}',
            language_pref TEXT DEFAULT 'en',
            affinity_score REAL DEFAULT 0,
            last_updated TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS community_posts (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            content TEXT,
            category TEXT,
            likes INTEGER DEFAULT 0,
            replies INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS community_replies (
            id TEXT PRIMARY KEY,
            post_id TEXT,
            user_id TEXT,
            content TEXT,
            likes INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(post_id) REFERENCES community_posts(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            tier TEXT DEFAULT 'kinship',
            status TEXT DEFAULT 'active',
            price REAL DEFAULT 19.99,
            started_at TEXT,
            renews_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS binyah_conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            messages TEXT DEFAULT '[]',
            context TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS cross_platform_events (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            platform TEXT,
            event_type TEXT,
            event_data TEXT DEFAULT '{}',
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    
    # Seed default channels
    channels = conn.execute("SELECT COUNT(*) FROM chat_channels").fetchone()[0]
    if channels == 0:
        defaults = [
            ("general", "General Discussion", "💬", "Welcome to the Hearth! Chat about anything Gullah Geechee.", 1),
            ("culture", "Gullah Geechee Culture", "🌿", "Deep dives into history, language, foodways, and traditions.", 1),
            ("books", "Books & Publishing", "📚", "Discuss Darryl's books, GullahVerse, and publishing.", 1),
            ("ai", "AI & Technology", "🤖", "Talk about the agents, think tank, and AI systems.", 1),
            ("music", "Music & Film", "🎵", "Songs, movies, and the creative pipeline.", 1),
            ("faith", "Faith & Spirituality", "🙏", "Bible studies, prayers, and spiritual discussions.", 1),
            ("business", "Business & Entrepreneurship", "💰", "Side hustles, AgentForge, and building wealth.", 1),
            ("announcements", "Announcements", "📢", "Official news from Darryl and the GGB team.", 1),
        ]
        for d in defaults:
            cid = hashlib.md5(d[0].encode()).hexdigest()[:12]
            conn.execute("INSERT INTO chat_channels VALUES (?,?,?,?,?,?,?)",
                        (cid, d[0], d[1], d[2], "system", d[3], datetime.now(timezone.utc).isoformat()))
        conn.commit()
    
    # Create Darryl's admin user
    admin = conn.execute("SELECT id FROM users WHERE username='darryl'").fetchone()
    if not admin:
        aid = hashlib.md5("darryl-admin".encode()).hexdigest()[:12]
        conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (aid, "darryl", "Darryl Elliott Brown", "deb2020win3@gmail.com",
                     "admin", "admin", "{}", "[]", "kinship",
                     datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
        conn.execute("INSERT INTO soul_profiles VALUES (?,?,?,?,?,?,?,?,?)",
                    (aid, json.dumps(["Gullah Geechee culture", "publishing", "AI", "music", "film"]),
                     "[]", "[]", "{}", json.dumps({"heritage": "Gullah Geechee", "region": "Lowcountry"}),
                     "en", 100, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    
    conn.close()

# ─── Hearth Engine ────────────────────────────────────────────────────────

class HearthEngine:
    def __init__(self):
        init_db()
    
    def _get_conn(self):
        return sqlite3.connect(str(DB_PATH))
    
    # ─── AUTH ───────────────────────────────────────────────────────────
    
    def register(self, username: str, display_name: str = "", email: str = "") -> Dict:
        conn = self._get_conn()
        existing = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if existing:
            conn.close()
            return {"error": "Username taken", "user_id": existing[0]}
        
        uid = hashlib.md5(f"{username}-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("""INSERT INTO users (id, username, display_name, email, role, joined_at, last_seen)
                       VALUES (?,?,?,?,?,?,?)""",
                    (uid, username, display_name or username, email, "member",
                     datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
        conn.execute("INSERT INTO soul_profiles (user_id, language_pref, last_updated) VALUES (?,?,?)",
                    (uid, "en", datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
        return {"user_id": uid, "username": username, "display_name": display_name or username, "role": "member"}
    
    def login(self, username: str) -> Dict:
        conn = self._get_conn()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if not user:
            return {"error": "User not found"}
        return {
            "user_id": user[0], "username": user[1], "display_name": user[2],
            "email": user[3], "role": user[5], "kinship_tier": user[8],
        }
    
    # ─── CHAT ───────────────────────────────────────────────────────────
    
    def get_channels(self):
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM chat_channels ORDER BY is_default DESC, name ASC").fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "description": r[2], "icon": r[3]} for r in rows]
    
    def send_message(self, user_id: str, message: str, channel: str = "general", platform: str = "hearth", reply_to: str = "") -> Dict:
        conn = self._get_conn()
        user = conn.execute("SELECT username, display_name FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            conn.close()
            return {"error": "User not found"}
        
        mid = hashlib.md5(f"msg-{time.time()}-{random.random()}".encode()).hexdigest()[:12]
        conn.execute("""INSERT INTO chat_messages (id, user_id, username, display_name, message, channel, platform, reply_to, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (mid, user_id, user[0], user[1], message, channel, platform, reply_to or None,
                     datetime.now(timezone.utc).isoformat()))
        conn.execute("UPDATE users SET last_seen=? WHERE id=?", (datetime.now(timezone.utc).isoformat(), user_id))
        conn.commit()
        conn.close()
        
        return {
            "message_id": mid,
            "user_id": user_id,
            "username": user[0],
            "display_name": user[1],
            "message": message,
            "channel": channel,
            "platform": platform,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def get_messages(self, channel: str = "general", limit: int = 50, before_id: str = "") -> List[Dict]:
        conn = self._get_conn()
        if before_id:
            before = conn.execute("SELECT created_at FROM chat_messages WHERE id=?", (before_id,)).fetchone()
            if before:
                rows = conn.execute("""SELECT * FROM chat_messages WHERE channel=? AND created_at < ? ORDER BY created_at DESC LIMIT ?""",
                                  (channel, before[0], limit)).fetchall()
            else:
                rows = conn.execute("""SELECT * FROM chat_messages WHERE channel=? ORDER BY created_at DESC LIMIT ?""",
                                  (channel, limit)).fetchall()
        else:
            rows = conn.execute("""SELECT * FROM chat_messages WHERE channel=? ORDER BY created_at DESC LIMIT ?""",
                              (channel, limit)).fetchall()
        conn.close()
        return [{
            "id": r[0], "user_id": r[1], "username": r[2], "display_name": r[3],
            "message": r[4], "channel": r[5], "platform": r[6], "reply_to": r[7],
            "created_at": r[8][:19] if r[8] else "",
        } for r in reversed(rows)]
    
    def get_recent_messages_all_channels(self, limit: int = 5):
        """Get recent messages from all channels for the cross-platform feed."""
        conn = self._get_conn()
        rows = conn.execute("""SELECT cm.*, cc.name as channel_name, cc.icon as channel_icon
                              FROM chat_messages cm
                              JOIN chat_channels cc ON cm.channel = cc.name
                              ORDER BY cm.created_at DESC LIMIT ?""", (limit * 8,)).fetchall()
        conn.close()
        return [{
            "id": r[0], "user_id": r[1], "username": r[2], "display_name": r[3],
            "message": r[4][:100], "channel": r[5], "channel_name": r[10],
            "channel_icon": r[11], "platform": r[6],
            "created_at": r[8][:19] if r[8] else "",
        } for r in rows]
    
    # ─── BINYAH CONCIERGE ──────────────────────────────────────────────
    
    def binyah_chat(self, user_id: str, message: str) -> Dict:
        """Binyah Concierge — the persistent AI guide."""
        conn = self._get_conn()
        user = conn.execute("SELECT username, display_name, soul_profile FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            conn.close()
            return {"error": "User not found"}
        
        # Get user's soul profile for context
        profile = conn.execute("SELECT * FROM soul_profiles WHERE user_id=?", (user_id,)).fetchone()
        interests = json.loads(profile[1]) if profile and profile[1] else []
        
        # Get recent activity
        recent_msgs = conn.execute("""SELECT message, channel FROM chat_messages WHERE user_id=? ORDER BY created_at DESC LIMIT 5""",
                                  (user_id,)).fetchall()
        
        conn.close()
        
        prompt = f"""You are Binyah, the Gullah Hearth Concierge — a warm, culturally authentic AI guide.

User: {user[1]}
Interests: {', '.join(interests) if interests else 'Exploring Gullah Geechee culture'}
Recent activity: {[m[0][:50] for m in recent_msgs]}

The user says: "{message}"

Respond as Binyah — warm, conversational, culturally Gullah Geechee. Use occasional Gullah phrases naturally. Be helpful, recommend content from the ecosystem (books, PDFs, agents, community discussions), and make the user feel at home on the Digital Porch.

Keep your response to 2-3 sentences. Be warm and authentic."""
        
        result = call_ai(prompt, max_tokens=500)
        
        # Save conversation
        conn = self._get_conn()
        conv = conn.execute("SELECT id, messages FROM binyah_conversations WHERE user_id=?", (user_id,)).fetchone()
        if conv:
            msgs = json.loads(conv[2] or "[]")
            msgs.append({"role": "user", "message": message, "timestamp": datetime.now(timezone.utc).isoformat()})
            msgs.append({"role": "binyah", "message": result or "Welcome to the Hearth!", "timestamp": datetime.now(timezone.utc).isoformat()})
            conn.execute("UPDATE binyah_conversations SET messages=?, updated_at=? WHERE id=?",
                        (json.dumps(msgs[-50:]), datetime.now(timezone.utc).isoformat(), conv[0]))
        else:
            cid = hashlib.md5(f"binyah-{user_id}".encode()).hexdigest()[:12]
            msgs = [
                {"role": "user", "message": message, "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "binyah", "message": result or "Welcome to the Hearth!", "timestamp": datetime.now(timezone.utc).isoformat()},
            ]
            conn.execute("INSERT INTO binyah_conversations VALUES (?,?,?,?,?,?)",
                        (cid, user_id, json.dumps(msgs), json.dumps({"interests": interests}),
                         datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
        
        return {
            "user_message": message,
            "binyah_response": result or "Welcome to the Hearth, family! How can I help you today?",
            "interests": interests,
        }
    
    # ─── SOUL PROFILE ──────────────────────────────────────────────────
    
    def get_soul_profile(self, user_id: str) -> Dict:
        conn = self._get_conn()
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        profile = conn.execute("SELECT * FROM soul_profiles WHERE user_id=?", (user_id,)).fetchone()
        conn.close()
        
        if not user:
            return {"error": "User not found"}
        
        return {
            "user": {
                "id": user[0], "username": user[1], "display_name": user[2],
                "role": user[5], "badges": json.loads(user[7] or "[]"),
                "kinship_tier": user[8], "joined_at": user[9][:19] if user[9] else "",
                "last_seen": user[10][:19] if user[10] else "",
            },
            "soul_profile": {
                "interests": json.loads(profile[1]) if profile and profile[1] else [],
                "purchases": json.loads(profile[2]) if profile and profile[2] else [],
                "cultural_preferences": json.loads(profile[5]) if profile and profile[5] else {},
                "language": profile[6] if profile else "en",
                "affinity_score": profile[7] if profile else 0,
            } if profile else {"interests": []},
        }
    
    def update_soul_profile(self, user_id: str, interests: List[str] = None) -> Dict:
        conn = self._get_conn()
        if interests:
            conn.execute("UPDATE soul_profiles SET interests=?, last_updated=? WHERE user_id=?",
                        (json.dumps(interests), datetime.now(timezone.utc).isoformat(), user_id))
        conn.commit()
        conn.close()
        return {"status": "updated"}
    
    # ─── COMMUNITY ─────────────────────────────────────────────────────
    
    def create_post(self, user_id: str, title: str, content: str, category: str = "general") -> Dict:
        conn = self._get_conn()
        pid = hashlib.md5(f"post-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("INSERT INTO community_posts VALUES (?,?,?,?,?,0,0,?)",
                    (pid, user_id, title, content, category, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
        return {"post_id": pid, "title": title, "category": category}
    
    def get_posts(self, category: str = "", limit: int = 20):
        conn = self._get_conn()
        if category:
            rows = conn.execute("""SELECT cp.*, u.display_name, u.username
                                  FROM community_posts cp
                                  JOIN users u ON cp.user_id = u.id
                                  WHERE cp.category=? ORDER BY cp.created_at DESC LIMIT ?""",
                              (category, limit)).fetchall()
        else:
            rows = conn.execute("""SELECT cp.*, u.display_name, u.username
                                  FROM community_posts cp
                                  JOIN users u ON cp.user_id = u.id
                                  ORDER BY cp.created_at DESC LIMIT ?""",
                              (limit,)).fetchall()
        conn.close()
        return [{
            "id": r[0], "user_id": r[1], "title": r[2], "content": r[3][:200],
            "category": r[4], "likes": r[5], "replies": r[6],
            "author": r[8] or r[9], "created_at": r[7][:19] if r[7] else "",
        } for r in rows]
    
    # ─── SUBSCRIPTION ──────────────────────────────────────────────────
    
    def subscribe_kinship(self, user_id: str) -> Dict:
        conn = self._get_conn()
        existing = conn.execute("SELECT id FROM subscriptions WHERE user_id=? AND status='active'", (user_id,)).fetchone()
        if existing:
            conn.close()
            return {"error": "Already subscribed", "subscription_id": existing[0]}
        
        sid = hashlib.md5(f"sub-{user_id}".encode()).hexdigest()[:12]
        conn.execute("INSERT INTO subscriptions VALUES (?,?,?,?,?,?,?)",
                    (sid, user_id, "kinship", "active", 19.99,
                     datetime.now(timezone.utc).isoformat(),
                     (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()))
        conn.execute("UPDATE users SET kinship_tier='kinship' WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
        return {"subscription_id": sid, "tier": "kinship", "price": 19.99, "status": "active"}
    
    # ─── CROSS-PLATFORM EVENTS ─────────────────────────────────────────
    
    def track_event(self, user_id: str, platform: str, event_type: str, event_data: Dict = None) -> Dict:
        conn = self._get_conn()
        eid = hashlib.md5(f"event-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("INSERT INTO cross_platform_events VALUES (?,?,?,?,?,?)",
                    (eid, user_id, platform, event_type, json.dumps(event_data or {}),
                     datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
        return {"event_id": eid}
    
    def get_user_feed(self, user_id: str, limit: int = 20):
        """Get a unified feed of all user activity across platforms."""
        conn = self._get_conn()
        events = conn.execute("""SELECT * FROM cross_platform_events WHERE user_id=? ORDER BY created_at DESC LIMIT ?""",
                            (user_id, limit)).fetchall()
        messages = conn.execute("""SELECT * FROM chat_messages WHERE user_id=? ORDER BY created_at DESC LIMIT ?""",
                              (user_id, limit)).fetchall()
        conn.close()
        
        feed = []
        for e in events:
            feed.append({
                "type": "event",
                "platform": e[2], "event_type": e[3],
                "data": json.loads(e[4] or "{}"),
                "timestamp": e[5][:19] if e[5] else "",
            })
        for m in messages:
            feed.append({
                "type": "message",
                "channel": m[5], "message": m[4][:100],
                "timestamp": m[8][:19] if m[8] else "",
            })
        
        feed.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return feed[:limit]
    
    # ─── STATS ──────────────────────────────────────────────────────────
    
    def get_stats(self):
        conn = self._get_conn()
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        messages = conn.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0]
        posts = conn.execute("SELECT COUNT(*) FROM community_posts").fetchone()[0]
        subs = conn.execute("SELECT COUNT(*) FROM subscriptions WHERE status='active'").fetchone()[0]
        binyah = conn.execute("SELECT COUNT(*) FROM binyah_conversations").fetchone()[0]
        events = conn.execute("SELECT COUNT(*) FROM cross_platform_events").fetchone()[0]
        
        # Active users in last hour
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        active = conn.execute("SELECT COUNT(*) FROM users WHERE last_seen > ?", (one_hour_ago,)).fetchone()[0]
        
        # Messages today
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_msgs = conn.execute("SELECT COUNT(*) FROM chat_messages WHERE created_at LIKE ?", (f"{today}%",)).fetchone()[0]
        
        conn.close()
        return {
            "users": users, "messages": messages, "posts": posts,
            "subscribers": subs, "binyah_conversations": binyah,
            "cross_platform_events": events,
            "active_now": active, "messages_today": today_msgs,
        }

# ─── HTML ─────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gullah Hearth — The Digital Porch</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: #0a0a12;
    color: #c8d6e5;
    min-height: 100vh;
  }
  .container { max-width: 1400px; margin: 0 auto; padding: 0; display: flex; height: 100vh; }

  /* Sidebar */
  .sidebar {
    width: 260px; background: rgba(255,255,255,0.02); border-right: 1px solid rgba(255,255,255,0.06);
    display: flex; flex-direction: column; padding: 16px; flex-shrink: 0;
  }
  .sidebar h1 {
    font-size: 1.1rem; font-weight: 900;
    background: linear-gradient(135deg, #f0c040, #d4a017);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
  }
  .sidebar .tagline { font-size: 0.65rem; color: #5a7a9a; margin-bottom: 16px; }

  .sidebar .section { font-size: 0.65rem; color: #5a7a9a; text-transform: uppercase; letter-spacing: 1px; margin: 12px 0 6px; }
  .channel {
    display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 6px;
    cursor: pointer; font-size: 0.8rem; color: #a0b0c0; transition: all 0.15s;
  }
  .channel:hover { background: rgba(255,255,255,0.04); color: #e0f0ff; }
  .channel.active { background: rgba(240,192,64,0.1); color: #f0c040; }
  .channel .unread {
    margin-left: auto; background: rgba(240,192,64,0.15); color: #f0c040;
    font-size: 0.6rem; padding: 1px 6px; border-radius: 4px;
  }

  .user-card {
    margin-top: auto; padding: 10px; background: rgba(255,255,255,0.02); border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.04);
  }
  .user-card .name { font-size: 0.8rem; font-weight: 600; color: #e0f0ff; }
  .user-card .tier { font-size: 0.65rem; color: #f0c040; }
  .user-card .status { font-size: 0.65rem; color: #4caf50; }
  .login-btn {
    width: 100%; padding: 8px; border-radius: 6px; border: 1px solid rgba(240,192,64,0.3);
    background: rgba(240,192,64,0.05); color: #f0c040; cursor: pointer; font-size: 0.8rem;
    text-align: center; margin-top: 8px;
  }
  .login-btn:hover { background: rgba(240,192,64,0.1); }

  /* Main */
  .main {
    flex: 1; display: flex; flex-direction: column; min-width: 0;
  }

  /* Chat Header */
  .chat-header {
    padding: 12px 20px; border-bottom: 1px solid rgba(255,255,255,0.06);
    display: flex; justify-content: space-between; align-items: center;
  }
  .chat-header h2 { font-size: 1rem; color: #e0f0ff; }
  .chat-header .desc { font-size: 0.7rem; color: #5a7a9a; }
  .chat-header .actions { display: flex; gap: 8px; }
  .chat-header .actions button {
    padding: 4px 12px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.1);
    background: transparent; color: #a0b0c0; cursor: pointer; font-size: 0.7rem;
  }
  .chat-header .actions button:hover { border-color: rgba(240,192,64,0.3); color: #f0c040; }

  /* Messages */
  .messages {
    flex: 1; overflow-y: auto; padding: 12px 20px;
    scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.06) transparent;
  }
  .messages::-webkit-scrollbar { width: 4px; }
  .messages::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

  .msg {
    display: flex; gap: 10px; margin-bottom: 10px; animation: fadeIn 0.2s ease;
  }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
  .msg .avatar {
    width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 700;
  }
  .msg .avatar.system { background: rgba(240,192,64,0.15); color: #f0c040; }
  .msg .avatar.user { background: rgba(100,200,255,0.15); color: #64c8ff; }
  .msg .avatar.admin { background: rgba(240,192,64,0.2); color: #f0c040; }
  .msg .avatar.binyah { background: rgba(167,139,250,0.15); color: #a78bfa; }
  .msg .body { flex: 1; min-width: 0; }
  .msg .body .meta { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
  .msg .body .meta .name { font-size: 0.8rem; font-weight: 600; color: #e0f0ff; }
  .msg .body .meta .name.admin { color: #f0c040; }
  .msg .body .meta .name.binyah { color: #a78bfa; }
  .msg .body .meta .time { font-size: 0.6rem; color: #3a4a5a; }
  .msg .body .meta .badge {
    font-size: 0.55rem; padding: 1px 5px; border-radius: 3px;
    background: rgba(240,192,64,0.1); color: #f0c040;
  }
  .msg .body .text { font-size: 0.85rem; line-height: 1.4; color: #c8d6e5; word-wrap: break-word; }
  .msg .body .text .binyah-msg { color: #a78bfa; font-style: italic; }
  .msg .body .platform-tag {
    font-size: 0.55rem; color: #5a7a9a; margin-top: 2px;
  }

  /* Binyah special message */
  .msg.binyah-msg { background: rgba(167,139,250,0.03); border-radius: 8px; padding: 8px; margin-left: -8px; margin-right: -8px; }

  /* Input */
  .input-area {
    padding: 12px 20px; border-top: 1px solid rgba(255,255,255,0.06);
    display: flex; gap: 8px; align-items: center;
  }
  .input-area input {
    flex: 1; padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);
    background: rgba(255,255,255,0.03); color: #e0f0ff; font-size: 0.85rem;
  }
  .input-area input:focus { outline: none; border-color: #f0c040; }
  .input-area button {
    padding: 10px 20px; border-radius: 8px; border: none;
    background: linear-gradient(135deg, #f0c040, #d4a017); color: #0a0a12;
    font-weight: 600; cursor: pointer; font-size: 0.85rem;
  }
  .input-area button:hover { transform: translateY(-1px); }
  .input-area button.binyah-btn { background: linear-gradient(135deg, #a78bfa, #7c3aed); color: #fff; }

  /* Right Panel */
  .right-panel {
    width: 300px; border-left: 1px solid rgba(255,255,255,0.06);
    display: flex; flex-direction: column; padding: 16px; overflow-y: auto;
    flex-shrink: 0;
  }
  .right-panel h3 { font-size: 0.75rem; color: #5a7a9a; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
  .right-panel .section { margin-bottom: 16px; }

  .online-user {
    display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 0.8rem;
  }
  .online-user .dot { width: 6px; height: 6px; border-radius: 50%; background: #4caf50; flex-shrink: 0; }
  .online-user .name { color: #a0b0c0; }
  .online-user .role { font-size: 0.6rem; color: #f0c040; }

  .feed-item {
    font-size: 0.7rem; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.03);
    color: #5a7a9a;
  }
  .feed-item .highlight { color: #a0b0c0; }

  .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .stat-box { background: rgba(255,255,255,0.02); border-radius: 6px; padding: 8px; text-align: center; }
  .stat-box .num { font-size: 1.1rem; font-weight: 700; color: #f0c040; }
  .stat-box .lbl { font-size: 0.6rem; color: #5a7a9a; }

  /* Modal */
  .modal-overlay {
    display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.6); z-index: 100; align-items: center; justify-content: center;
  }
  .modal-overlay.active { display: flex; }
  .modal {
    background: #1a1a2e; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px;
    padding: 24px; width: 400px; max-width: 90vw;
  }
  .modal h2 { font-size: 1.1rem; color: #f0c040; margin-bottom: 12px; }
  .modal input { width: 100%; padding: 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.03); color: #e0f0ff; margin-bottom: 8px; font-size: 0.85rem; }
  .modal input:focus { outline: none; border-color: #f0c040; }
  .modal .btn { width: 100%; padding: 10px; border-radius: 6px; border: none; background: linear-gradient(135deg, #f0c040, #d4a017); color: #0a0a12; font-weight: 600; cursor: pointer; }
  .modal .close { float: right; cursor: pointer; color: #5a7a9a; font-size: 1.2rem; }

  .toast {
    position: fixed; bottom: 20px; right: 20px;
    background: rgba(240,192,64,0.9); color: #0a0a12;
    padding: 12px 20px; border-radius: 8px; font-size: 0.8rem; font-weight: 600;
    animation: slideUp 0.3s ease; z-index: 200;
  }
  @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

  @media (max-width: 900px) {
    .container { flex-direction: column; height: auto; }
    .sidebar { width: 100%; border-right: none; border-bottom: 1px solid rgba(255,255,255,0.06); flex-direction: row; flex-wrap: wrap; padding: 10px; }
    .sidebar h1 { width: 100%; }
    .sidebar .section { display: none; }
    .channels-row { display: flex; gap: 4px; overflow-x: auto; width: 100%; }
    .channel { white-space: nowrap; font-size: 0.7rem; padding: 4px 8px; }
    .user-card { display: none; }
    .right-panel { display: none; }
    .main { height: calc(100vh - 120px); }
  }
</style>
</head>
<body>
<div class="container">
  <!-- Sidebar -->
  <div class="sidebar">
    <h1>🏠 Gullah Hearth</h1>
    <div class="tagline">The Digital Porch — Where Family Gathers</div>
    <div class="section">Channels</div>
    <div class="channels-row" id="channelList"></div>
    <div class="section" style="margin-top:12px">Quick Actions</div>
    <div style="display:flex; flex-direction:column; gap:4px">
      <div class="channel" onclick="openBinyah()" style="color:#a78bfa">🤖 Ask Binyah</div>
      <div class="channel" onclick="openSubscribe()" style="color:#f0c040">⭐ Kinship ($19.99/mo)</div>
      <div class="channel" onclick="openProfile()" style="color:#64c8ff">👤 My Soul Profile</div>
    </div>
    <div class="user-card" id="userCard">
      <div id="userInfo">
        <div class="name" id="userName">Welcome, Guest</div>
        <div class="tier" id="userTier">Free Member</div>
        <div class="status" id="userStatus">🔴 Offline</div>
      </div>
      <div class="login-btn" id="loginBtn" onclick="openLogin()">🔑 Sign In / Register</div>
    </div>
  </div>

  <!-- Main Chat -->
  <div class="main">
    <div class="chat-header">
      <div>
        <h2 id="currentChannel">💬 general</h2>
        <div class="desc" id="channelDesc">Welcome to the Hearth! Chat about anything Gullah Geechee.</div>
      </div>
      <div class="actions">
        <button onclick="openBinyah()">🤖 Binyah</button>
        <button onclick="loadMessages()">🔄 Refresh</button>
      </div>
    </div>
    <div class="messages" id="messageList"></div>
    <div class="input-area">
      <input id="messageInput" placeholder="Type your message..." onkeydown="if(event.key==='Enter') sendMessage()">
      <button onclick="sendMessage()">Send</button>
      <button class="binyah-btn" onclick="askBinyah()">🤖</button>
    </div>
  </div>

  <!-- Right Panel -->
  <div class="right-panel">
    <div class="section">
      <h3>🔥 Live Feed</h3>
      <div id="liveFeed"></div>
    </div>
    <div class="section">
      <h3>🟢 Online Now</h3>
      <div id="onlineUsers"></div>
    </div>
    <div class="section">
      <h3>📊 Hearth Stats</h3>
      <div class="stats-grid" id="hearthStats"></div>
    </div>
  </div>
</div>

<!-- Login Modal -->
<div class="modal-overlay" id="loginModal">
  <div class="modal">
    <span class="close" onclick="closeModal('loginModal')">&times;</span>
    <h2>🔑 Welcome to the Hearth</h2>
    <input id="loginUsername" placeholder="Choose a username">
    <input id="loginDisplayName" placeholder="Display name (optional)">
    <input id="loginEmail" placeholder="Email (optional)">
    <button class="btn" onclick="register()">Join the Hearth</button>
    <p style="text-align:center; margin-top:8px; font-size:0.75rem; color:#5a7a9a">Already have an account? <a href="#" onclick="login()" style="color:#f0c040">Sign in</a></p>
  </div>
</div>

<!-- Binyah Modal -->
<div class="modal-overlay" id="binyahModal">
  <div class="modal" style="width:500px">
    <span class="close" onclick="closeModal('binyahModal')">&times;</span>
    <h2>🤖 Ask Binyah</h2>
    <p style="font-size:0.8rem; color:#a78bfa; margin-bottom:12px">Your personal Gullah Geechee guide. Ask me anything about the culture, the books, or the ecosystem.</p>
    <div id="binyahChat" style="max-height:300px; overflow-y:auto; margin-bottom:8px; font-size:0.8rem"></div>
    <div style="display:flex; gap:8px">
      <input id="binyahInput" placeholder="Ask Binyah anything..." style="flex:1">
      <button class="btn" style="width:auto; background:linear-gradient(135deg,#a78bfa,#7c3aed); color:#fff" onclick="askBinyah()">Ask</button>
    </div>
  </div>
</div>

<!-- Subscribe Modal -->
<div class="modal-overlay" id="subscribeModal">
  <div class="modal">
    <span class="close" onclick="closeModal('subscribeModal')">&times;</span>
    <h2>⭐ Kinship Membership</h2>
    <p style="font-size:0.8rem; color:#5a7a9a; margin-bottom:12px">$19.99/month — Unlimited access to everything. Early access to books, movies, and content. Direct interaction with Binyah. Ad-free across all platforms.</p>
    <button class="btn" onclick="subscribeKinship()">⭐ Join Kinship — $19.99/mo</button>
  </div>
</div>

<script>
let currentUser = null;
let currentChannel = 'general';
let channels = [];

async function api(path, data) {
  const opts = { headers: {'Content-Type': 'application/json'} };
  if (data) opts.body = JSON.stringify(data), opts.method = 'POST';
  const r = await fetch('/api' + path, opts);
  return r.json();
}

function toast(msg) {
  const t = document.createElement('div'); t.className = 'toast'; t.textContent = msg;
  document.body.appendChild(t); setTimeout(() => t.remove(), 3000);
}

function closeModal(id) { document.getElementById(id).classList.remove('active'); }
function openModal(id) { document.getElementById(id).classList.add('active'); }

function openLogin() { openModal('loginModal'); }
function openBinyah() { openModal('binyahModal'); document.getElementById('binyahChat').innerHTML = '<div style="color:#5a7a9a">Ask me anything about Gullah Geechee culture!</div>'; }
function openSubscribe() { openModal('subscribeModal'); }
function openProfile() {
  if (!currentUser) return toast('Sign in first');
  api('/soul-profile/' + currentUser.user_id).then(r => {
    const p = r.soul_profile || {};
    toast('Soul Profile: ' + (p.interests || []).join(', ') || 'No interests yet. Start chatting!');
  });
}

async function register() {
  const username = document.getElementById('loginUsername').value.trim();
  if (!username) return toast('Enter a username');
  const display = document.getElementById('loginDisplayName').value.trim() || username;
  const email = document.getElementById('loginEmail').value.trim();
  const r = await api('/register', { username, display_name: display, email });
  if (r.error && r.error !== 'Username taken') return toast(r.error);
  currentUser = r;
  updateUI();
  closeModal('loginModal');
  toast('Welcome to the Hearth, ' + (currentUser.display_name || currentUser.username) + '!');
}

async function login() {
  const username = document.getElementById('loginUsername').value.trim();
  if (!username) return toast('Enter your username');
  const r = await api('/login', { username });
  if (r.error) return toast(r.error);
  currentUser = r;
  updateUI();
  closeModal('loginModal');
  toast('Welcome back, ' + (currentUser.display_name || currentUser.username) + '!');
}

function updateUI() {
  if (currentUser) {
    document.getElementById('userName').textContent = currentUser.display_name || currentUser.username;
    document.getElementById('userTier').textContent = currentUser.kinship_tier === 'kinship' ? '⭐ Kinship Member' : 'Free Member';
    document.getElementById('userStatus').textContent = '🟢 Online';
    document.getElementById('loginBtn').textContent = 'Sign Out';
    document.getElementById('loginBtn').onclick = () => { currentUser = null; updateUI(); toast('Signed out'); };
  } else {
    document.getElementById('userName').textContent = 'Welcome, Guest';
    document.getElementById('userTier').textContent = 'Free Member';
    document.getElementById('userStatus').textContent = '🔴 Offline';
    document.getElementById('loginBtn').textContent = '🔑 Sign In / Register';
    document.getElementById('loginBtn').onclick = openLogin;
  }
}

async function loadChannels() {
  const r = await api('/channels');
  channels = r;
  const list = document.getElementById('channelList');
  list.innerHTML = r.map(c =>
    `<div class="channel ${c.name === currentChannel ? 'active' : ''}" onclick="switchChannel('${c.name}')">${c.icon} ${c.name}</div>`
  ).join('');
}

async function switchChannel(name) {
  currentChannel = name;
  document.querySelectorAll('.channel').forEach(c => c.classList.remove('active'));
  const ch = channels.find(c => c.name === name);
  document.getElementById('currentChannel').textContent = (ch ? ch.icon : '💬') + ' ' + name;
  document.getElementById('channelDesc').textContent = ch ? ch.description : '';
  loadChannels();
  loadMessages();
}

async function loadMessages() {
  const r = await api('/messages/' + currentChannel);
  const list = document.getElementById('messageList');
  list.innerHTML = r.map(m => {
    const isAdmin = m.username === 'darryl';
    const isBinyah = m.platform === 'binyah';
    const avatarClass = isAdmin ? 'admin' : isBinyah ? 'binyah' : 'user';
    const nameClass = isAdmin ? 'admin' : isBinyah ? 'binyah' : '';
    const binyahClass = isBinyah ? 'binyah-msg' : '';
    return `
      <div class="msg ${binyahClass}">
        <div class="avatar ${avatarClass}">${isAdmin ? 'D' : isBinyah ? 'B' : m.display_name ? m.display_name[0].toUpperCase() : '?'}</div>
        <div class="body">
          <div class="meta">
            <span class="name ${nameClass}">${m.display_name || m.username}${isAdmin ? ' 👑' : ''}</span>
            ${isBinyah ? '<span class="badge">Binyah</span>' : ''}
            <span class="time">${m.created_at ? new Date(m.created_at).toLocaleTimeString() : ''}</span>
          </div>
          <div class="text">${m.message}</div>
          ${m.platform !== 'hearth' ? `<div class="platform-tag">via ${m.platform}</div>` : ''}
        </div>
      </div>
    `;
  }).join('');
  list.scrollTop = list.scrollHeight;
}

async function sendMessage() {
  const input = document.getElementById('messageInput');
  const msg = input.value.trim();
  if (!msg) return;
  if (!currentUser) return toast('Sign in to chat');
  input.value = '';
  await api('/send-message', { user_id: currentUser.user_id, message: msg, channel: currentChannel });
  loadMessages();
  loadFeed();
  loadStats();
}

async function askBinyah() {
  if (!currentUser) return toast('Sign in to ask Binyah');
  const input = document.getElementById('binyahInput');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  const chat = document.getElementById('binyahChat');
  chat.innerHTML += `<div style="color:#a0b0c0; margin-bottom:4px"><strong>You:</strong> ${msg}</div>`;
  chat.innerHTML += `<div style="color:#a78bfa; margin-bottom:8px"><em>Binyah is thinking...</em></div>`;
  chat.scrollTop = chat.scrollHeight;
  
  const r = await api('/binyah', { user_id: currentUser.user_id, message: msg });
  chat.innerHTML = chat.innerHTML.replace('<div style="color:#a78bfa; margin-bottom:8px"><em>Binyah is thinking...</em></div>', '');
  chat.innerHTML += `<div style="color:#a78bfa; margin-bottom:8px; font-style:italic">🪴 ${r.binyah_response || 'Welcome to the Hearth, family!'}</div>`;
  chat.scrollTop = chat.scrollHeight;
}

async function subscribeKinship() {
  if (!currentUser) return toast('Sign in first');
  const r = await api('/subscribe', { user_id: currentUser.user_id });
  if (r.error) return toast(r.error);
  currentUser.kinship_tier = 'kinship';
  updateUI();
  closeModal('subscribeModal');
  toast('⭐ Welcome to Kinship! You now have unlimited access.');
}

async function loadFeed() {
  const r = await api('/feed');
  const feed = document.getElementById('liveFeed');
  feed.innerHTML = r.slice(0, 10).map(f =>
    `<div class="feed-item">${f.channel_icon || '💬'} <span class="highlight">${f.display_name || f.username}</span> in <span class="highlight">#${f.channel}</span>: ${f.message}</div>`
  ).join('');
}

async function loadStats() {
  const r = await api('/stats');
  document.getElementById('hearthStats').innerHTML = `
    <div class="stat-box"><div class="num">${r.active_now}</div><div class="lbl">Online</div></div>
    <div class="stat-box"><div class="num">${r.messages_today}</div><div class="lbl">Msgs Today</div></div>
    <div class="stat-box"><div class="num">${r.users}</div><div class="lbl">Members</div></div>
    <div class="stat-box"><div class="num">${r.subscribers}</div><div class="lbl">Kinship</div></div>
  `;
  document.getElementById('onlineUsers').innerHTML = `
    <div class="online-user"><div class="dot"></div><span class="name">Darryl Elliott Brown</span><span class="role">👑</span></div>
    <div class="online-user"><div class="dot"></div><span class="name">Binyah Concierge</span><span class="role">🤖</span></div>
    <div class="online-user"><div class="dot"></div><span class="name">${r.active_now - 2 > 0 ? r.active_now - 2 + ' more...' : 'You?'}</span></div>
  `;
}

// Init
loadChannels();
loadMessages();
loadFeed();
loadStats();
setInterval(() => { loadMessages(); loadFeed(); loadStats(); }, 5000);

// Auto-login Darryl
api('/login', { username: 'darryl' }).then(r => {
  if (!r.error) { currentUser = r; updateUI(); }
});
</script>
</body>
</html>"""

# ─── Server ───────────────────────────────────────────────────────────────

engine = HearthEngine()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        if path == "/api/channels":
            self._json(engine.get_channels())
        elif path.startswith("/api/messages/"):
            channel = path.split("/")[-1]
            self._json(engine.get_messages(channel))
        elif path == "/api/feed":
            self._json(engine.get_recent_messages_all_channels())
        elif path == "/api/stats":
            self._json(engine.get_stats())
        elif path.startswith("/api/soul-profile/"):
            uid = path.split("/")[-1]
            self._json(engine.get_soul_profile(uid))
        else:
            self._html(HTML)
    
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        path = self.path
        
        if path == "/api/register":
            self._json(engine.register(body.get("username", ""), body.get("display_name", ""), body.get("email", "")))
        elif path == "/api/login":
            self._json(engine.login(body.get("username", "")))
        elif path == "/api/send-message":
            self._json(engine.send_message(body.get("user_id", ""), body.get("message", ""), body.get("channel", "general"), body.get("platform", "hearth"), body.get("reply_to", "")))
        elif path == "/api/binyah":
            self._json(engine.binyah_chat(body.get("user_id", ""), body.get("message", "")))
        elif path == "/api/subscribe":
            self._json(engine.subscribe_kinship(body.get("user_id", "")))
        elif path == "/api/update-profile":
            self._json(engine.update_soul_profile(body.get("user_id", ""), body.get("interests")))
        elif path == "/api/track-event":
            self._json(engine.track_event(body.get("user_id", ""), body.get("platform", ""), body.get("event_type", ""), body.get("event_data")))
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
    print(f"  🏠 GULLAH HEARTH — The Digital Porch")
    print(f"  http://localhost:{PORT}")
    print(f"{'='*55}")
    print(f"  • Common Chat — everyone chats together across systems")
    print(f"  • Binyah Concierge — your personal AI guide")
    print(f"  • Soul Profiles — unified user identity across all platforms")
    print(f"  • Community — discussions, posts, cultural exchange")
    print(f"  • Kinship Subscription — $19.99/mo premium tier")
    print(f"  • Cross-Platform Feed — see activity from all 5 platforms")
    print(f"  • Darryl can chime in anytime as admin 👑")
    print(f"  • Press Ctrl+C to stop.\n")
    
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
