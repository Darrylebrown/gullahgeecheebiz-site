#!/usr/bin/env python3
"""
Gullah Geechee Biz — Buffer Queue Engine
Large-capacity job queue with priority, rate limiting, preloading,
and a web dashboard. Sits between cron triggers and workflow execution.
"""

import json, os, sys, time, threading, queue, sqlite3, subprocess, re
from queue import Empty as QueueEmpty
from pathlib import Path
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

HOME = Path.home()
ENGINE_DIR = HOME / "gullahgeecheebiz-site" / "ggb-engine"
BUFFER_DIR = HOME / ".hermes" / "buffer"
BUFFER_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = BUFFER_DIR / "buffer.db"
DASHBOARD_PORT = 8769

# ─── Database ───────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    # Jobs table
    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            workflow TEXT NOT NULL,
            priority INTEGER DEFAULT 5,
            status TEXT DEFAULT 'queued',
            context TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            scheduled_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            result TEXT,
            error TEXT,
            progress INTEGER DEFAULT 0,
            progress_total INTEGER DEFAULT 100,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            batch_id TEXT,
            parent_job_id INTEGER
        )
    """)
    
    # Batches table
    c.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            total_jobs INTEGER DEFAULT 0,
            completed_jobs INTEGER DEFAULT 0,
            status TEXT DEFAULT 'queued',
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
    """)
    
    # Schedule table (preloaded jobs)
    c.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            workflow TEXT NOT NULL,
            cron TEXT NOT NULL,
            context TEXT DEFAULT '{}',
            priority INTEGER DEFAULT 5,
            enabled INTEGER DEFAULT 1,
            last_run TEXT,
            next_run TEXT
        )
    """)
    
    # Rate limits
    c.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            window_start TEXT NOT NULL,
            window_end TEXT NOT NULL,
            jobs_run INTEGER DEFAULT 0,
            max_jobs INTEGER DEFAULT 10
        )
    """)
    
    conn.commit()
    conn.close()

# ─── Job Queue ─────────────────────────────────────────────────────────────────

class JobQueue:
    """Thread-safe priority job queue with database persistence."""
    
    def __init__(self):
        self._queue = queue.PriorityQueue()
        self._running = {}
        self._lock = threading.Lock()
        self._paused = False
        self._rate_limit = 10  # max jobs per minute
        self._rate_window = []
    
    def enqueue(self, name, workflow, context=None, priority=5, scheduled_at=None, batch_id=None, parent_id=None):
        """Add a job to the queue."""
        job = {
            "name": name,
            "workflow": workflow,
            "context": json.dumps(context or {}),
            "priority": priority,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "scheduled_at": scheduled_at,
            "batch_id": batch_id,
            "parent_job_id": parent_id,
            "max_retries": 3,
            "retry_count": 0
        }
        
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""
            INSERT INTO jobs (name, workflow, priority, status, context, created_at, scheduled_at, batch_id, parent_job_id)
            VALUES (?, ?, ?, 'queued', ?, ?, ?, ?, ?)
        """, (name, workflow, priority, job["context"], job["created_at"], scheduled_at, batch_id, parent_id))
        job_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # Add to in-memory queue (negative priority = higher priority runs first)
        self._queue.put((priority, job_id, job))
        
        return job_id
    
    def enqueue_batch(self, name, jobs):
        """Add a batch of jobs."""
        batch_id = f"batch-{int(time.time())}"
        
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("INSERT INTO batches (id, name, total_jobs, status, created_at) VALUES (?, ?, ?, 'queued', ?)",
                  (batch_id, name, len(jobs), datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        job_ids = []
        for job in jobs:
            jid = self.enqueue(
                name=job.get("name", "unnamed"),
                workflow=job.get("workflow", ""),
                context=job.get("context"),
                priority=job.get("priority", 5),
                scheduled_at=job.get("scheduled_at"),
                batch_id=batch_id
            )
            job_ids.append(jid)
        
        return batch_id, job_ids
    
    def preload(self, name, workflow, context=None, cron="0 6 * * *", priority=5):
        """Preload a recurring job schedule."""
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""
            INSERT INTO schedules (name, workflow, cron, context, priority, enabled, next_run)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        """, (name, workflow, cron, json.dumps(context or {}), priority, _next_cron(cron)))
        sid = c.lastrowid
        conn.commit()
        conn.close()
        return sid
    
    def dequeue(self):
        """Get the next available job."""
        if self._paused:
            return None
        
        # Check rate limit
        now = time.time()
        self._rate_window = [t for t in self._rate_window if t > now - 60]
        if len(self._rate_window) >= self._rate_limit:
            return None
        
        try:
            priority, job_id, job = self._queue.get_nowait()
            
            # Check if scheduled
            if job.get("scheduled_at"):
                scheduled = datetime.fromisoformat(job["scheduled_at"])
                if scheduled > datetime.now():
                    # Put it back
                    self._queue.put((priority, job_id, job))
                    return None
            
            self._rate_window.append(now)
            
            with self._lock:
                self._running[job_id] = job
            
            return job_id, job
            
        except QueueEmpty:
            return None
    
    def complete(self, job_id, result=None, error=None):
        """Mark a job as completed."""
        with self._lock:
            self._running.pop(job_id, None)
        
        status = "completed" if not error else "failed"
        
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""
            UPDATE jobs SET status=?, completed_at=?, result=?, error=?, progress=100
            WHERE id=?
        """, (status, datetime.now().isoformat(), json.dumps(result) if result else None, error, job_id))
        
        # Update batch progress
        c.execute("SELECT batch_id FROM jobs WHERE id=?", (job_id,))
        row = c.fetchone()
        if row and row[0]:
            c.execute("""
                UPDATE batches SET completed_jobs = (
                    SELECT COUNT(*) FROM jobs WHERE batch_id=? AND status IN ('completed', 'failed')
                ), status = CASE 
                    WHEN completed_jobs = total_jobs THEN 'completed'
                    ELSE 'running'
                END WHERE id=?
            """, (row[0], row[0]))
        
        conn.commit()
        conn.close()
    
    def update_progress(self, job_id, progress, total=100):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("UPDATE jobs SET progress=?, progress_total=? WHERE id=?", (progress, total, job_id))
        conn.commit()
        conn.close()
    
    def retry(self, job_id):
        """Retry a failed job."""
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT name, workflow, context, priority, max_retries, retry_count, batch_id, parent_job_id FROM jobs WHERE id=?", (job_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return None
        
        name, workflow, context, priority, max_retries, retry_count, batch_id, parent_id = row
        
        if retry_count >= max_retries:
            return None
        
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""
            INSERT INTO jobs (name, workflow, priority, status, context, created_at, batch_id, parent_job_id, retry_count)
            VALUES (?, ?, ?, 'queued', ?, ?, ?, ?, ?)
        """, (name, workflow, priority, context, datetime.now().isoformat(), batch_id, parent_id, retry_count + 1))
        new_id = c.lastrowid
        conn.commit()
        conn.close()
        
        self._queue.put((priority, new_id, {"name": name, "workflow": workflow}))
        return new_id
    
    def pause(self):
        self._paused = True
    
    def resume(self):
        self._paused = False
    
    def status(self):
        return {
            "queued": self._queue.qsize(),
            "running": len(self._running),
            "paused": self._paused,
            "rate_limit": self._rate_limit,
            "rate_window_60s": len(self._rate_window)
        }
    
    def get_stats(self):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM jobs")
        total = c.fetchone()[0]
        
        c.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
        by_status = {row[0]: row[1] for row in c.fetchall()}
        
        c.execute("SELECT COUNT(*) FROM jobs WHERE created_at > ?", 
                  ((datetime.now() - timedelta(hours=24)).isoformat(),))
        last_24h = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM batches")
        batches = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM schedules WHERE enabled=1")
        schedules = c.fetchone()[0]
        
        conn.close()
        
        return {
            "total_jobs": total,
            "by_status": by_status,
            "last_24h": last_24h,
            "batches": batches,
            "active_schedules": schedules
        }

# ─── Worker ────────────────────────────────────────────────────────────────────

class BufferWorker(threading.Thread):
    """Background worker that processes jobs from the queue."""
    
    def __init__(self, queue, worker_id=1):
        super().__init__(daemon=True)
        self.queue = queue
        self.worker_id = worker_id
        self.running = True
    
    def run(self):
        while self.running:
            try:
                job = self.queue.dequeue()
                if job:
                    job_id, job_info = job
                    self._execute(job_id, job_info)
                else:
                    time.sleep(1)
            except Exception as e:
                print(f"  ⚠️ Worker {self.worker_id} error: {e}")
                time.sleep(5)
    
    def _execute(self, job_id, job_info):
        workflow = job_info.get("workflow", "")
        name = job_info.get("name", workflow)
        
        print(f"\n  🔄 Worker {self.worker_id}: {name}")
        
        # Update status
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("UPDATE jobs SET status='running', started_at=? WHERE id=?", 
                  (datetime.now().isoformat(), job_id))
        conn.commit()
        conn.close()
        
        # Run the workflow
        engine_script = ENGINE_DIR / "engine.py"
        if engine_script.exists() and workflow:
            try:
                result = subprocess.run(
                    ["python3", str(engine_script), "run", workflow],
                    capture_output=True, text=True, timeout=600
                )
                
                if result.returncode == 0:
                    self.queue.complete(job_id, result={"stdout": result.stdout[-500:]})
                    print(f"  ✅ Worker {self.worker_id}: {name} completed")
                else:
                    error = result.stderr[-500:] if result.stderr else "Unknown error"
                    self.queue.complete(job_id, error=error)
                    
                    # Auto-retry
                    new_id = self.queue.retry(job_id)
                    if new_id:
                        print(f"  🔄 Worker {self.worker_id}: {name} retrying ({new_id})")
                    else:
                        print(f"  ❌ Worker {self.worker_id}: {name} failed, max retries reached")
            
            except subprocess.TimeoutExpired:
                self.queue.complete(job_id, error="Timeout after 600s")
                print(f"  ⏰ Worker {self.worker_id}: {name} timed out")
        else:
            # No workflow engine - run as shell command
            try:
                result = subprocess.run(
                    workflow, shell=True, capture_output=True, text=True, timeout=600
                )
                if result.returncode == 0:
                    self.queue.complete(job_id, result={"stdout": result.stdout[-500:]})
                else:
                    self.queue.complete(job_id, error=result.stderr[-500:])
            except Exception as e:
                self.queue.complete(job_id, error=str(e))

# ─── Schedule Checker ──────────────────────────────────────────────────────────

def _next_cron(cron_expr):
    """Simple cron parser - returns next run time."""
    parts = cron_expr.split()
    if len(parts) != 5:
        return datetime.now().isoformat()
    
    minute, hour, day, month, weekday = parts
    
    now = datetime.now()
    # Very simple: if hour matches, run now
    if hour != "*":
        try:
            h = int(hour)
            if now.hour >= h:
                next_time = now.replace(hour=h, minute=0, second=0) + timedelta(days=1)
            else:
                next_time = now.replace(hour=h, minute=0, second=0)
            return next_time.isoformat()
        except:
            pass
    
    return (now + timedelta(hours=1)).isoformat()

def schedule_checker(queue):
    """Background thread that checks for scheduled jobs."""
    while True:
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            
            now = datetime.now().isoformat()
            c.execute("""
                SELECT id, name, workflow, context, priority, cron FROM schedules
                WHERE enabled=1 AND next_run <= ?
            """, (now,))
            
            for row in c.fetchall():
                sid, name, workflow, context, priority, cron = row
                
                # Enqueue the job
                ctx = json.loads(context) if context else {}
                queue.enqueue(name, workflow, ctx, priority)
                
                # Update next run
                next_run = _next_cron(cron)
                c.execute("UPDATE schedules SET last_run=?, next_run=? WHERE id=?",
                         (now, next_run, sid))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"  ⚠️ Schedule checker: {e}")
        
        time.sleep(30)

# ─── Dashboard Server ─────────────────────────────────────────────────────────

class DashboardHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        
        if path == "/" or path == "/dashboard":
            self._render_dashboard()
        elif path == "/api/status":
            self._json(200, queue.status())
        elif path == "/api/stats":
            self._json(200, queue.get_stats())
        elif path == "/api/jobs":
            status_filter = params.get("status", [None])[0]
            self._json(200, self._get_jobs(status_filter))
        elif path == "/api/batches":
            self._json(200, self._get_batches())
        elif path == "/api/schedules":
            self._json(200, self._get_schedules())
        elif path == "/api/pause":
            queue.pause()
            self._json(200, {"status": "paused"})
        elif path == "/api/resume":
            queue.resume()
            self._json(200, {"status": "resumed"})
        elif path == "/api/retry":
            job_id = params.get("id", [None])[0]
            if job_id:
                new_id = queue.retry(int(job_id))
                self._json(200, {"retried": True, "new_job_id": new_id})
            else:
                self._json(400, {"error": "No job ID provided"})
        else:
            self._json(404, {"error": "Not found"})
    
    def _get_jobs(self, status_filter=None):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        
        if status_filter:
            c.execute("""
                SELECT id, name, workflow, priority, status, created_at, started_at, completed_at, 
                       progress, progress_total, retry_count, error, batch_id
                FROM jobs WHERE status=? ORDER BY created_at DESC LIMIT 50
            """, (status_filter,))
        else:
            c.execute("""
                SELECT id, name, workflow, priority, status, created_at, started_at, completed_at,
                       progress, progress_total, retry_count, error, batch_id
                FROM jobs ORDER BY created_at DESC LIMIT 50
            """)
        
        jobs = []
        for row in c.fetchall():
            jobs.append({
                "id": row[0], "name": row[1], "workflow": row[2], "priority": row[3],
                "status": row[4], "created_at": row[5], "started_at": row[6],
                "completed_at": row[7], "progress": row[8], "progress_total": row[9],
                "retry_count": row[10], "error": (row[11] or "")[:100], "batch_id": row[12]
            })
        
        conn.close()
        return jobs
    
    def _get_batches(self):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT id, name, total_jobs, completed_jobs, status, created_at FROM batches ORDER BY created_at DESC LIMIT 20")
        batches = [{"id": r[0], "name": r[1], "total": r[2], "completed": r[3], "status": r[4], "created_at": r[5]} for r in c.fetchall()]
        conn.close()
        return batches
    
    def _get_schedules(self):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT id, name, workflow, cron, priority, enabled, last_run, next_run FROM schedules ORDER BY next_run")
        schedules = [{"id": r[0], "name": r[1], "workflow": r[2], "cron": r[3], "priority": r[4], 
                      "enabled": bool(r[5]), "last_run": r[6], "next_run": r[7]} for r in c.fetchall()]
        conn.close()
        return schedules
    
    def _render_dashboard(self):
        stats = queue.get_stats()
        qstatus = queue.status()
        jobs = self._get_jobs()
        batches = self._get_batches()
        schedules = self._get_schedules()
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GGB Buffer Queue</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a14;color:#f0ede5;line-height:1.6;padding:30px 20px}}
.container{{max-width:1200px;margin:0 auto}}
h1{{font-family:Georgia,serif;color:#d4af37;font-size:1.8em;margin-bottom:5px}}
.subtitle{{color:#888;margin-bottom:25px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:25px}}
.card{{background:#111122;border-radius:10px;padding:18px;text-align:center;border:1px solid #1a1a2e}}
.card .num{{font-size:1.8em;font-weight:bold;color:#d4af37}}
.card .label{{color:#888;font-size:0.8em;margin-top:3px}}
.controls{{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}}
.btn{{background:#d4af37;color:#0a0a14;padding:8px 16px;border-radius:20px;border:none;cursor:pointer;font-weight:bold;font-size:0.85em}}
.btn:hover{{background:#e8c84a}}
.btn-outline{{background:transparent;color:#d4af37;border:1px solid #d4af37}}
.btn-danger{{background:#c0392b;color:white}}
.section{{margin-bottom:25px}}
.section h2{{color:#d4af37;font-size:1.1em;margin-bottom:8px;border-bottom:1px solid #1a1a2e;padding-bottom:6px}}
table{{width:100%;border-collapse:collapse;font-size:0.85em}}
th{{text-align:left;color:#888;padding:6px 8px;border-bottom:1px solid #333;font-weight:normal}}
td{{padding:6px 8px;border-bottom:1px solid #1a1a2e}}
.status-queued{{color:#f39c12}}
.status-running{{color:#3498db}}
.status-completed{{color:#27ae60}}
.status-failed{{color:#e74c3c}}
.bar{{height:4px;background:#1a1a2e;border-radius:2px;margin-top:3px}}
.bar-fill{{height:100%;background:#d4af37;border-radius:2px;transition:width 0.3s}}
.footer{{margin-top:30px;color:#555;font-size:0.75em;text-align:center}}
</style>
</head>
<body>
<div class="container">
<h1>📦 GGB Buffer Queue</h1>
<p class="subtitle">Job queue, rate limiter, and schedule engine</p>

<div class="grid">
<div class="card"><div class="num">{stats['total_jobs']}</div><div class="label">Total Jobs</div></div>
<div class="card"><div class="num">{stats['by_status'].get('queued', 0)}</div><div class="label">Queued</div></div>
<div class="card"><div class="num">{stats['by_status'].get('running', 0)}</div><div class="label">Running</div></div>
<div class="card"><div class="num">{stats['by_status'].get('completed', 0)}</div><div class="label">Completed</div></div>
<div class="card"><div class="num">{stats['by_status'].get('failed', 0)}</div><div class="label">Failed</div></div>
<div class="card"><div class="num">{stats['last_24h']}</div><div class="label">Last 24h</div></div>
<div class="card"><div class="num">{stats['batches']}</div><div class="label">Batches</div></div>
<div class="card"><div class="num">{stats['active_schedules']}</div><div class="label">Schedules</div></div>
</div>

<div class="controls">
<button class="btn" onclick="enqueue()">+ Add Job</button>
<button class="btn" onclick="preload()">+ Add Schedule</button>
<button class="btn {'btn-outline' if not qstatus['paused'] else 'btn-danger'}" onclick="togglePause()">
  {'⏸ Pause' if not qstatus['paused'] else '▶ Resume'}
</button>
<button class="btn btn-outline" onclick="window.location.reload()">Refresh</button>
</div>

<div class="section">
<h2>Queue Status</h2>
<table>
<tr><td>Queued</td><td>{qstatus['queued']}</td><td>Running</td><td>{qstatus['running']}</td>
<td>Rate (60s)</td><td>{qstatus['rate_window_60s']}/{qstatus['rate_limit']}</td>
<td>Paused</td><td>{'Yes' if qstatus['paused'] else 'No'}</td></tr>
</table>
</div>

<div class="section">
<h2>Recent Jobs</h2>
<table>
<tr><th>ID</th><th>Name</th><th>Workflow</th><th>Status</th><th>Progress</th><th>Created</th><th>Actions</th></tr>
"""
        for j in jobs[:15]:
            status_class = f"status-{j['status']}"
            bar_width = int((j['progress'] / max(j['progress_total'], 1)) * 100)
            html += f"""<tr>
<td style="color:#555">{j['id']}</td>
<td>{j['name'][:30]}</td>
<td style="color:#888">{j['workflow'][:20]}</td>
<td class="{status_class}">{j['status']}</td>
<td><div class="bar"><div class="bar-fill" style="width:{bar_width}%"></div></div></td>
<td style="color:#555;font-size:0.8em">{j['created_at'][:16]}</td>
<td>{'<button class="btn btn-outline" style="padding:2px 8px;font-size:0.75em" onclick="retry(' + str(j['id']) + ')">↻</button>' if j['status'] == 'failed' else ''}</td>
</tr>"""
        
        html += """</table></div>

<div class="section">
<h2>Batches</h2>
<table><tr><th>ID</th><th>Name</th><th>Progress</th><th>Status</th><th>Created</th></tr>
"""
        for b in batches[:10]:
            pct = int((b['completed'] / max(b['total'], 1)) * 100) if b['total'] > 0 else 0
            html += f"""<tr>
<td style="color:#555">{b['id'][:20]}</td>
<td>{b['name'][:30]}</td>
<td>{b['completed']}/{b['total']} ({pct}%)</td>
<td>{b['status']}</td>
<td style="color:#555;font-size:0.8em">{b['created_at'][:16]}</td>
</tr>"""
        
        html += """</table></div>

<div class="section">
<h2>Schedules</h2>
<table><tr><th>Name</th><th>Workflow</th><th>Cron</th><th>Next Run</th><th>Last Run</th><th>Enabled</th></tr>
"""
        for s in schedules[:10]:
            html += f"""<tr>
<td>{s['name'][:30]}</td>
<td style="color:#888">{s['workflow'][:20]}</td>
<td style="color:#555">{s['cron']}</td>
<td style="font-size:0.8em">{s['next_run'][:16] if s['next_run'] else '-'}</td>
<td style="font-size:0.8em;color:#555">{s['last_run'][:16] if s['last_run'] else '-'}</td>
<td>{'✅' if s['enabled'] else '❌'}</td>
</tr>"""
        
        html += """</table></div>

<div class="footer">
GGB Buffer Queue · Port 8769 · SQLite backend · {count} workers
</div>
</div>

<script>
async function togglePause() {{
    const resp = await fetch('/api/status');
    const data = await resp.json();
    const endpoint = data.paused ? '/api/resume' : '/api/pause';
    await fetch(endpoint);
    window.location.reload();
}}
async function retry(id) {{
    await fetch('/api/retry?id=' + id);
    window.location.reload();
}}
async function enqueue() {{
    const name = prompt('Job name:');
    const workflow = prompt('Workflow name or shell command:');
    if (name && workflow) {{
        await fetch('/api/enqueue?name=' + encodeURIComponent(name) + '&workflow=' + encodeURIComponent(workflow));
        window.location.reload();
    }}
}}
async function preload() {{
    const name = prompt('Schedule name:');
    const workflow = prompt('Workflow name:');
    const cron = prompt('Cron expression (e.g. 0 6 * * *):', '0 6 * * *');
    if (name && workflow && cron) {{
        await fetch('/api/preload?name=' + encodeURIComponent(name) + '&workflow=' + encodeURIComponent(workflow) + '&cron=' + encodeURIComponent(cron));
        window.location.reload();
    }}
}}
</script>
</body>
</html>"""
        
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

queue = JobQueue()
workers = []

def start():
    global workers
    
    init_db()
    
    # Start workers (4 by default)
    num_workers = 4
    for i in range(num_workers):
        w = BufferWorker(queue, i + 1)
        w.start()
        workers.append(w)
    
    # Start schedule checker
    t = threading.Thread(target=schedule_checker, args=(queue,), daemon=True)
    t.start()
    
    # Start dashboard
    server = HTTPServer(("0.0.0.0", DASHBOARD_PORT), DashboardHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    
    print(f"\n{'='*50}")
    print(f"📦 GGB Buffer Queue")
    print(f"{'='*50}")
    print(f"   Workers: {num_workers}")
    print(f"   Dashboard: http://localhost:{DASHBOARD_PORT}")
    print(f"   Database: {DB_PATH}")
    print(f"   Rate limit: {queue._rate_limit} jobs/minute")
    print(f"{'='*50}\n")
    
    # Preload default schedules
    queue.preload("SEO Audit", "seo-audit-daily", cron="0 6 * * *")
    queue.preload("Distribution AM", "distribution-overseer-am", cron="0 9 * * *")
    queue.preload("Ad Generator", "ad-generator-every-4h", cron="0 */6 * * *")
    queue.preload("Fable Prompts", "fable-prompts-every-6h", cron="15 */6 * * *")
    queue.preload("Traffic Check", "traffic-check-every-4h", cron="45 */6 * * *")
    queue.preload("Manus Factory", "manus-factory-weekly", cron="0 8 * * 1")
    
    print(f"   Preloaded {6} default schedules")
    print(f"   Ready for jobs\n")
    
    # Keep alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    start()
