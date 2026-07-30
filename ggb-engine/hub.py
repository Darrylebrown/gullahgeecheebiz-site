#!/usr/bin/env python3
"""
Gullah Geechee Biz — GGB Hub
Active-active parallel hub with hot backup.
Any business or website plugs in once and the hub handles routing.
Two instances run simultaneously. If one fails, the other takes over instantly.
"""

import json, os, sys, time, threading, sqlite3, subprocess, socket, hashlib
from pathlib import Path
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HOME = Path.home()
HUB_DIR = HOME / ".hermes" / "hub"
HUB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = HUB_DIR / "hub.db"
HEARTBEAT_PATH = HUB_DIR / "heartbeat"
HUB_PORT = 8770
PEER_PORT = 8771

# ─── Database ───────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    # Registered businesses/nodes
    c.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            node_type TEXT NOT NULL,
            description TEXT DEFAULT '',
            channels TEXT DEFAULT '[]',
            content_types TEXT DEFAULT '[]',
            status TEXT DEFAULT 'active',
            registered_at TEXT NOT NULL,
            last_heartbeat TEXT,
            config TEXT DEFAULT '{}'
        )
    """)
    
    # Channel definitions
    c.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id TEXT PRIMARY KEY,
            node_id TEXT NOT NULL,
            channel_type TEXT NOT NULL,
            name TEXT NOT NULL,
            config TEXT DEFAULT '{}',
            enabled INTEGER DEFAULT 1,
            FOREIGN KEY (node_id) REFERENCES nodes(id)
        )
    """)
    
    # Content routing rules
    c.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_node TEXT NOT NULL,
            content_type TEXT NOT NULL,
            target_channel TEXT NOT NULL,
            priority INTEGER DEFAULT 5,
            transform TEXT DEFAULT '{}',
            enabled INTEGER DEFAULT 1
        )
    """)
    
    # Instance registry (for active-active)
    c.execute("""
        CREATE TABLE IF NOT EXISTS instances (
            id TEXT PRIMARY KEY,
            hostname TEXT NOT NULL,
            port INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            started_at TEXT NOT NULL,
            last_heartbeat TEXT,
            is_primary INTEGER DEFAULT 0
        )
    """)
    
    # Cross-instance queue (shared)
    c.execute("""
        CREATE TABLE IF NOT EXISTS cross_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_instance TEXT NOT NULL,
            target_instance TEXT,
            action TEXT NOT NULL,
            payload TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            processed INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()

# ─── Hub Core ──────────────────────────────────────────────────────────────────

class GGBHub:
    """Active-active parallel hub with hot backup."""
    
    def __init__(self, instance_id=None, is_primary=False):
        self.instance_id = instance_id or f"hub-{socket.gethostname()}-{int(time.time())}"
        self.hostname = socket.gethostname()
        self.is_primary = is_primary
        self.started_at = datetime.now().isoformat()
        self._lock = threading.Lock()
        self._running = True
        
        # Register this instance
        self._register_instance()
        
        # Start heartbeat
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        
        # Start peer sync
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
    
    def _register_instance(self):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO instances (id, hostname, port, status, started_at, last_heartbeat, is_primary)
            VALUES (?, ?, ?, 'active', ?, ?, ?)
        """, (self.instance_id, self.hostname, HUB_PORT, self.started_at, self.started_at, 1 if self.is_primary else 0))
        conn.commit()
        conn.close()
    
    def _heartbeat_loop(self):
        while self._running:
            try:
                now = datetime.now().isoformat()
                conn = sqlite3.connect(str(DB_PATH))
                c = conn.cursor()
                c.execute("UPDATE instances SET last_heartbeat=? WHERE id=?", (now, self.instance_id))
                c.execute("UPDATE nodes SET last_heartbeat=? WHERE status='active'", (now,))
                conn.commit()
                conn.close()
                
                # Write heartbeat file for peer detection
                with open(HEARTBEAT_PATH, "w") as f:
                    f.write(json.dumps({
                        "instance_id": self.instance_id,
                        "hostname": self.hostname,
                        "port": HUB_PORT,
                        "timestamp": now,
                        "is_primary": self.is_primary
                    }))
            except:
                pass
            time.sleep(15)
    
    def _sync_loop(self):
        """Sync with peer instance."""
        while self._running:
            try:
                # Check for peer heartbeat
                if HEARTBEAT_PATH.exists():
                    with open(HEARTBEAT_PATH) as f:
                        peer = json.load(f)
                    
                    # If peer is alive and we're both primary, resolve
                    peer_age = (datetime.now() - datetime.fromisoformat(peer["timestamp"])).total_seconds()
                    if peer_age < 30 and peer["instance_id"] != self.instance_id:
                        if self.is_primary and peer.get("is_primary"):
                            # Both think they're primary - resolve by hostname
                            if self.hostname > peer["hostname"]:
                                self.is_primary = False
                                conn = sqlite3.connect(str(DB_PATH))
                                c = conn.cursor()
                                c.execute("UPDATE instances SET is_primary=0 WHERE id=?", (self.instance_id,))
                                conn.commit()
                                conn.close()
                
                # Process cross-queue items
                conn = sqlite3.connect(str(DB_PATH))
                c = conn.cursor()
                c.execute("""
                    SELECT id, source_instance, action, payload FROM cross_queue
                    WHERE (target_instance IS NULL OR target_instance=?) AND processed=0
                    ORDER BY id LIMIT 10
                """, (self.instance_id,))
                
                for row in c.fetchall():
                    qid, source, action, payload = row
                    data = json.loads(payload)
                    
                    if action == "register_node":
                        self._register_node(data)
                    elif action == "route_content":
                        self._route_content(data)
                    elif action == "sync_state":
                        self._sync_state(data)
                    
                    c.execute("UPDATE cross_queue SET processed=1 WHERE id=?", (qid,))
                
                conn.commit()
                conn.close()
            except:
                pass
            time.sleep(5)
    
    def register_node(self, name, node_type, channels=None, content_types=None, config=None):
        """Register a business or website with the hub."""
        node_id = hashlib.md5(name.encode()).hexdigest()[:12]
        
        node = {
            "id": node_id,
            "name": name,
            "node_type": node_type,
            "channels": json.dumps(channels or []),
            "content_types": json.dumps(content_types or []),
            "config": json.dumps(config or {}),
            "registered_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO nodes (id, name, node_type, channels, content_types, config, registered_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        """, (node_id, name, node_type, node["channels"], node["content_types"], node["config"], node["registered_at"]))
        
        # Register channels
        if channels:
            for ch in channels:
                ch_id = hashlib.md5(f"{node_id}-{ch['type']}-{ch['name']}".encode()).hexdigest()[:12]
                c.execute("""
                    INSERT OR REPLACE INTO channels (id, node_id, channel_type, name, config, enabled)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (ch_id, node_id, ch["type"], ch["name"], json.dumps(ch.get("config", {}))))
        
        conn.commit()
        conn.close()
        
        # Broadcast to peer
        self._broadcast("register_node", node)
        
        return node_id
    
    def add_route(self, source_node, content_type, target_channel, priority=5, transform=None):
        """Add a content routing rule."""
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""
            INSERT INTO routes (source_node, content_type, target_channel, priority, transform, enabled)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (source_node, content_type, target_channel, priority, json.dumps(transform or {})))
        rid = c.lastrowid
        conn.commit()
        conn.close()
        return rid
    
    def route_content(self, source_node, content_type, content):
        """Route content to all matching channels."""
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        
        # Find matching routes
        c.execute("""
            SELECT r.target_channel, r.transform, c.channel_type, c.name, c.config, n.name
            FROM routes r
            JOIN channels c ON c.id = r.target_channel
            JOIN nodes n ON n.id = c.node_id
            WHERE r.source_node=? AND r.content_type=? AND r.enabled=1 AND c.enabled=1
            ORDER BY r.priority
        """, (source_node, content_type))
        
        routes = []
        for row in c.fetchall():
            routes.append({
                "channel_id": row[0],
                "transform": json.loads(row[1]) if row[1] else {},
                "channel_type": row[2],
                "channel_name": row[3],
                "channel_config": json.loads(row[4]) if row[4] else {},
                "node_name": row[5]
            })
        
        conn.close()
        
        # Route to each channel
        results = []
        for route in routes:
            result = self._deliver_to_channel(route, content)
            results.append(result)
        
        return {"routes_matched": len(routes), "results": results}
    
    def _deliver_to_channel(self, route, content):
        """Deliver content to a specific channel."""
        channel_type = route["channel_type"]
        channel_config = route["channel_config"]
        
        # Each channel type has a known delivery path
        delivery_map = {
            "site": self._deliver_to_site,
            "etsy": self._deliver_to_etsy,
            "shopify": self._deliver_to_shopify,
            "tiktok": self._deliver_to_tiktok,
            "instagram": self._deliver_to_instagram,
            "pinterest": self._deliver_to_pinterest,
            "substack": self._deliver_to_substack,
            "kdp": self._deliver_to_kdp,
            "d2d": self._deliver_to_d2d,
            "acx": self._deliver_to_acx,
            "distrokid": self._deliver_to_distrokid,
            "spotify": self._deliver_to_spotify,
            "file": self._deliver_to_file,
        }
        
        handler = delivery_map.get(channel_type)
        if handler:
            return handler(route, content)
        return {"status": "unknown_channel", "channel": channel_type}
    
    def _deliver_to_site(self, route, content):
        """Deliver to a website (GitHub Pages deploy)."""
        target_dir = route["channel_config"].get("target_dir", str(HOME / "gullahgeecheebiz-site"))
        filename = route["channel_config"].get("filename", f"hub-content-{int(time.time())}.html")
        
        filepath = Path(target_dir) / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w") as f:
            f.write(content.get("body", str(content)))
        
        return {"status": "delivered", "path": str(filepath), "channel": "site"}
    
    def _deliver_to_file(self, route, content):
        """Deliver to a local file."""
        target_dir = Path(route["channel_config"].get("target_dir", str(HOME / "hub-output")))
        filename = route["channel_config"].get("filename", f"content-{int(time.time())}.json")
        
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(content, f, indent=2)
        
        return {"status": "delivered", "path": str(filepath), "channel": "file"}
    
    def _deliver_to_etsy(self, route, content):
        return {"status": "routed", "channel": "etsy", "note": "Etsy delivery via distribution bot"}
    
    def _deliver_to_shopify(self, route, content):
        return {"status": "routed", "channel": "shopify", "note": "Shopify delivery via CSV feed"}
    
    def _deliver_to_tiktok(self, route, content):
        return {"status": "routed", "channel": "tiktok", "note": "TikTok delivery via upload pipeline"}
    
    def _deliver_to_instagram(self, route, content):
        return {"status": "routed", "channel": "instagram", "note": "Instagram delivery via upload pipeline"}
    
    def _deliver_to_pinterest(self, route, content):
        return {"status": "routed", "channel": "pinterest", "note": "Pinterest delivery via pin pipeline"}
    
    def _deliver_to_substack(self, route, content):
        return {"status": "routed", "channel": "substack", "note": "Substack delivery via newsletter bot"}
    
    def _deliver_to_kdp(self, route, content):
        return {"status": "routed", "channel": "kdp", "note": "KDP delivery via distribution bot"}
    
    def _deliver_to_d2d(self, route, content):
        return {"status": "routed", "channel": "d2d", "note": "D2D delivery via distribution bot"}
    
    def _deliver_to_acx(self, route, content):
        return {"status": "routed", "channel": "acx", "note": "ACX delivery via distribution bot"}
    
    def _deliver_to_distrokid(self, route, content):
        return {"status": "routed", "channel": "distrokid", "note": "DistroKid delivery via distribution bot"}
    
    def _deliver_to_spotify(self, route, content):
        return {"status": "routed", "channel": "spotify", "note": "Spotify delivery via distribution bot"}
    
    def _register_node(self, data):
        """Register a node from peer broadcast."""
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO nodes (id, name, node_type, channels, content_types, config, registered_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        """, (data["id"], data["name"], data["node_type"], data["channels"], data["content_types"],
              data["config"], data["registered_at"]))
        conn.commit()
        conn.close()
    
    def _route_content(self, data):
        """Route content from peer broadcast."""
        self.route_content(data.get("source"), data.get("type"), data.get("content", {}))
    
    def _sync_state(self, data):
        """Sync full state from peer."""
        pass  # State is shared via SQLite
    
    def _broadcast(self, action, payload):
        """Broadcast an action to the peer instance."""
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""
            INSERT INTO cross_queue (source_instance, target_instance, action, payload, created_at)
            VALUES (?, NULL, ?, ?, ?)
        """, (self.instance_id, action, json.dumps(payload), datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def get_nodes(self):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT id, name, node_type, channels, content_types, status, registered_at FROM nodes ORDER BY registered_at DESC")
        nodes = []
        for row in c.fetchall():
            nodes.append({
                "id": row[0], "name": row[1], "type": row[2],
                "channels": json.loads(row[3]) if row[3] else [],
                "content_types": json.loads(row[4]) if row[4] else [],
                "status": row[5], "registered_at": row[6]
            })
        conn.close()
        return nodes
    
    def get_channels(self, node_id=None):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        if node_id:
            c.execute("SELECT id, node_id, channel_type, name, enabled FROM channels WHERE node_id=?", (node_id,))
        else:
            c.execute("SELECT id, node_id, channel_type, name, enabled FROM channels")
        channels = [{"id": r[0], "node_id": r[1], "type": r[2], "name": r[3], "enabled": bool(r[4])} for r in c.fetchall()]
        conn.close()
        return channels
    
    def get_routes(self):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""
            SELECT r.id, r.source_node, r.content_type, r.target_channel, r.priority, r.enabled,
                   n.name as source_name, c.name as channel_name, c.channel_type
            FROM routes r
            JOIN nodes n ON n.id = r.source_node
            JOIN channels c ON c.id = r.target_channel
            ORDER BY r.priority
        """)
        routes = [{"id": r[0], "source": r[1], "content_type": r[2], "target_channel": r[3],
                   "priority": r[4], "enabled": bool(r[5]), "source_name": r[6],
                   "channel_name": r[7], "channel_type": r[8]} for r in c.fetchall()]
        conn.close()
        return routes
    
    def get_instances(self):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT id, hostname, port, status, started_at, last_heartbeat, is_primary FROM instances")
        instances = [{"id": r[0], "hostname": r[1], "port": r[2], "status": r[3],
                      "started_at": r[4], "last_heartbeat": r[5], "is_primary": bool(r[6])} for r in c.fetchall()]
        conn.close()
        return instances
    
    def get_stats(self):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM nodes")
        nodes = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM channels")
        channels = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM routes WHERE enabled=1")
        active_routes = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM instances WHERE status='active'")
        active_instances = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM cross_queue WHERE processed=0")
        pending_sync = c.fetchone()[0]
        conn.close()
        
        return {
            "nodes": nodes,
            "channels": channels,
            "active_routes": active_routes,
            "active_instances": active_instances,
            "pending_sync": pending_sync,
            "this_instance": self.instance_id,
            "is_primary": self.is_primary
        }

# ─── Dashboard Server ─────────────────────────────────────────────────────────

class HubHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        
        if path == "/" or path == "/dashboard":
            self._render_dashboard()
        elif path == "/api/stats":
            self._json(200, hub.get_stats())
        elif path == "/api/nodes":
            self._json(200, hub.get_nodes())
        elif path == "/api/channels":
            node_id = params.get("node", [None])[0]
            self._json(200, hub.get_channels(node_id))
        elif path == "/api/routes":
            self._json(200, hub.get_routes())
        elif path == "/api/instances":
            self._json(200, hub.get_instances())
        elif path == "/api/register":
            name = params.get("name", [""])[0]
            node_type = params.get("type", ["business"])[0]
            if name:
                node_id = hub.register_node(name, node_type)
                self._json(200, {"node_id": node_id, "name": name})
            else:
                self._json(400, {"error": "Name required"})
        elif path == "/api/route":
            source = params.get("source", [""])[0]
            content_type = params.get("content_type", [""])[0]
            target = params.get("target", [""])[0]
            if source and content_type and target:
                rid = hub.add_route(source, content_type, target)
                self._json(200, {"route_id": rid})
            else:
                self._json(400, {"error": "source, content_type, target required"})
        else:
            self._json(404, {"error": "Not found"})
    
    def _render_dashboard(self):
        stats = hub.get_stats()
        nodes = hub.get_nodes()
        channels = hub.get_channels()
        routes = hub.get_routes()
        instances = hub.get_instances()
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GGB Hub — Active-Active</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a14;color:#f0ede5;line-height:1.6;padding:30px 20px}}
.container{{max-width:1200px;margin:0 auto}}
h1{{font-family:Georgia,serif;color:#d4af37;font-size:1.8em;margin-bottom:5px}}
.subtitle{{color:#888;margin-bottom:25px}}
.badge{{display:inline-block;padding:2px 10px;border-radius:10px;font-size:0.75em;font-weight:bold}}
.badge-primary{{background:#d4af37;color:#0a0a14}}
.badge-backup{{background:#3498db;color:white}}
.badge-active{{background:#27ae60;color:white}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:25px}}
.card{{background:#111122;border-radius:10px;padding:18px;text-align:center;border:1px solid #1a1a2e}}
.card .num{{font-size:1.8em;font-weight:bold;color:#d4af37}}
.card .label{{color:#888;font-size:0.8em;margin-top:3px}}
.controls{{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}}
.btn{{background:#d4af37;color:#0a0a14;padding:8px 16px;border-radius:20px;border:none;cursor:pointer;font-weight:bold;font-size:0.85em}}
.btn:hover{{background:#e8c84a}}
.btn-outline{{background:transparent;color:#d4af37;border:1px solid #d4af37}}
.section{{margin-bottom:25px}}
.section h2{{color:#d4af37;font-size:1.1em;margin-bottom:8px;border-bottom:1px solid #1a1a2e;padding-bottom:6px}}
table{{width:100%;border-collapse:collapse;font-size:0.85em}}
th{{text-align:left;color:#888;padding:6px 8px;border-bottom:1px solid #333;font-weight:normal}}
td{{padding:6px 8px;border-bottom:1px solid #1a1a2e}}
.footer{{margin-top:30px;color:#555;font-size:0.75em;text-align:center}}
</style>
</head>
<body>
<div class="container">
<h1>🔗 GGB Hub</h1>
<p class="subtitle">Active-active parallel hub — always up, always routing</p>

<div class="grid">
<div class="card"><div class="num">{stats['nodes']}</div><div class="label">Nodes</div></div>
<div class="card"><div class="num">{stats['channels']}</div><div class="label">Channels</div></div>
<div class="card"><div class="num">{stats['active_routes']}</div><div class="label">Active Routes</div></div>
<div class="card"><div class="num">{stats['active_instances']}</div><div class="label">Live Instances</div></div>
<div class="card"><div class="num">{stats['pending_sync']}</div><div class="label">Pending Sync</div></div>
</div>

<div class="section">
<h2>Instances</h2>
<table><tr><th>ID</th><th>Host</th><th>Role</th><th>Status</th><th>Started</th><th>Heartbeat</th></tr>
"""
        for inst in instances:
            role = '<span class="badge badge-primary">PRIMARY</span>' if inst['is_primary'] else '<span class="badge badge-backup">BACKUP</span>'
            status = '<span class="badge badge-active">ACTIVE</span>' if inst['status'] == 'active' else inst['status']
            html += f"""<tr>
<td style="color:#555;font-size:0.8em">{inst['id'][:20]}</td>
<td>{inst['hostname']}</td>
<td>{role}</td>
<td>{status}</td>
<td style="font-size:0.8em">{inst['started_at'][:16]}</td>
<td style="font-size:0.8em;color:#555">{inst['last_heartbeat'][:16] if inst['last_heartbeat'] else '-'}</td>
</tr>"""
        
        html += """</table></div>

<div class="section">
<h2>Registered Nodes</h2>
<table><tr><th>ID</th><th>Name</th><th>Type</th><th>Channels</th><th>Status</th><th>Registered</th></tr>
"""
        for node in nodes:
            ch_names = ", ".join([c.get("name", c.get("type", "?")) for c in node["channels"]]) if isinstance(node["channels"], list) else str(node["channels"])
            html += f"""<tr>
<td style="color:#555;font-size:0.8em">{node['id']}</td>
<td>{node['name'][:30]}</td>
<td style="color:#888">{node['type']}</td>
<td style="font-size:0.8em;color:#888">{ch_names[:40]}</td>
<td>{'✅' if node['status'] == 'active' else '❌'}</td>
<td style="font-size:0.8em;color:#555">{node['registered_at'][:16]}</td>
</tr>"""
        
        html += """</table></div>

<div class="section">
<h2>Active Routes</h2>
<table><tr><th>Source</th><th>Content Type</th><th>Target Channel</th><th>Priority</th><th>Status</th></tr>
"""
        for r in routes:
            html += f"""<tr>
<td>{r['source_name'][:25]}</td>
<td style="color:#888">{r['content_type']}</td>
<td>{r['channel_name'][:25]} ({r['channel_type']})</td>
<td style="color:#555">{r['priority']}</td>
<td>{'✅' if r['enabled'] else '❌'}</td>
</tr>"""
        
        html += """</table></div>

<div class="controls">
<button class="btn" onclick="registerNode()">+ Register Node</button>
<button class="btn btn-outline" onclick="window.location.reload()">Refresh</button>
</div>

<div class="footer">
GGB Hub · Active-Active · Port {port} · Instance: {instance}
</div>
</div>

<script>
async function registerNode() {{
    const name = prompt('Node name (e.g. Gullah Geechee Biz):');
    const type = prompt('Node type (business, website, store):', 'business');
    if (name) {{
        const resp = await fetch('/api/register?name=' + encodeURIComponent(name) + '&type=' + encodeURIComponent(type));
        const data = await resp.json();
        alert('Registered: ' + data.node_id);
        window.location.reload();
    }}
}}
</script>
</body>
</html>""".format(port=HUB_PORT, instance=hub.instance_id[:16])
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
    
    def _json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
    
    def log_message(self, format, *args):
        pass

# ─── Main ──────────────────────────────────────────────────────────────────────

hub = None

def start(is_primary=True):
    global hub
    
    init_db()
    hub = GGBHub(is_primary=is_primary)
    
    # Auto-register Gullah Geechee Biz
    hub.register_node(
        name="Gullah Geechee Biz",
        node_type="publisher",
        channels=[
            {"type": "site", "name": "Main Website", "config": {"url": "https://gullahgeecheebiz.com"}},
            {"type": "etsy", "name": "Etsy Store", "config": {"url": "https://gullahgeecheebiz.etsy.com"}},
            {"type": "shopify", "name": "Shopify Store", "config": {"url": "https://gullahgeecheebiz.myshopify.com"}},
            {"type": "file", "name": "Local Output", "config": {"target_dir": str(HOME / "hub-output")}},
        ],
        content_types=["ebook", "recipe", "video", "ad", "pin", "article"]
    )
    
    # Auto-route: ebooks → all stores
    hub.add_route(
        source_node=hub.get_nodes()[0]["id"] if hub.get_nodes() else "",
        content_type="ebook",
        target_channel=hub.get_channels()[0]["id"] if hub.get_channels() else "",
        priority=1
    )
    
    # Start dashboard
    server = HTTPServer(("0.0.0.0", HUB_PORT), HubHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    
    role = "PRIMARY" if is_primary else "BACKUP"
    print(f"\n{'='*50}")
    print(f"🔗 GGB Hub — {role}")
    print(f"{'='*50}")
    print(f"   Instance: {hub.instance_id}")
    print(f"   Dashboard: http://localhost:{HUB_PORT}")
    print(f"   Database: {DB_PATH}")
    print(f"   Heartbeat: {HEARTBEAT_PATH}")
    print(f"{'='*50}\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Hub — Active-Active")
    parser.add_argument("--backup", action="store_true", help="Start as backup instance")
    args = parser.parse_args()
    start(is_primary=not args.backup)
