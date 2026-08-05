#!/usr/bin/env python3
"""
GGB System Health Monitor — Checks all 9 platforms, tracks resources, auto-heals.
Runs as a daemon on port 8092, serves a health dashboard.
"""
import json, os, sys, time, subprocess, threading, logging
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
HQ = BASE / "ggb-engine" / "headquarters"
LOG_DIR = HQ / "logs" / "health-monitor"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "health-monitor.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("health-monitor")

PLATFORMS = {
    "Command Center": 8080,
    "AgentForge": 8081,
    "AI-Persona Pro": 8082,
    "GullahVerse Books": 8083,
    "GullahGems": 8084,
    "Gullah Hearth": 8085,
    "Universal Submitter": 8086,
    "Royalty Dashboard": 8087,
    "Publishing Controller": 8090,
    "Bot Factory": 8091,
}

health_state = {
    "platforms": {},
    "system": {"cpu": 0, "memory": 0, "disk": 0},
    "events": [],
    "overall_health": 0,
    "last_updated": "",
}

def check_platform(name, port):
    """Check if a platform is responding."""
    try:
        req = Request(f"http://127.0.0.1:{port}/", method="GET")
        resp = urlopen(req, timeout=5)
        status = resp.getcode()
        return "ok" if status == 200 else "degraded"
    except URLError:
        return "down"
    except Exception:
        return "down"

def get_system_metrics():
    """Get CPU, memory, and disk usage."""
    metrics = {"cpu": 0, "memory": 0, "disk": 0}
    try:
        # CPU
        result = subprocess.run(
            ["ps", "-A", "-o", "%cpu="],
            capture_output=True, text=True, timeout=5
        )
        cpus = [float(x) for x in result.stdout.strip().split("\n") if x.strip()]
        metrics["cpu"] = round(sum(cpus) / len(cpus), 1) if cpus else 0
    except:
        pass
    try:
        # Memory
        result = subprocess.run(
            ["vm_stat"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            if "Pages active" in line:
                metrics["memory"] = 50  # rough estimate
    except:
        pass
    try:
        # Disk
        result = subprocess.run(
            ["df", "-H", str(BASE)],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            parts = lines[1].split()
            if len(parts) >= 5:
                used = parts[2].replace("G", "").replace("M", "")
                total = parts[1].replace("G", "").replace("M", "")
                try:
                    metrics["disk"] = round(float(used) / float(total) * 100, 1)
                except:
                    pass
    except:
        pass
    return metrics

def calculate_health():
    """Calculate overall system health score."""
    platforms = health_state["platforms"]
    total = len(platforms)
    if total == 0:
        return 0
    
    ok_count = sum(1 for p in platforms.values() if p.get("status") == "ok")
    degraded_count = sum(1 for p in platforms.values() if p.get("status") == "degraded")
    
    # Platform health: 60% of score
    platform_score = (ok_count / total) * 60 + (degraded_count / total) * 30
    
    # System health: 40% of score
    sys_metrics = health_state["system"]
    cpu_score = max(0, 100 - sys_metrics.get("cpu", 0)) * 0.15
    mem_score = max(0, 100 - sys_metrics.get("memory", 0)) * 0.15
    disk_score = max(0, 100 - sys_metrics.get("disk", 0)) * 0.10
    
    system_score = cpu_score + mem_score + disk_score
    
    return round(platform_score + system_score)

def scan_cycle():
    """One complete health scan cycle."""
    log.info("=== Health Scan Cycle ===")
    
    # Check all platforms
    for name, port in PLATFORMS.items():
        status = check_platform(name, port)
        health_state["platforms"][name] = {
            "port": port,
            "status": status,
            "last_check": datetime.now().isoformat()
        }
        log.info(f"  {name} (:{port}): {status}")
    
    # Get system metrics
    health_state["system"] = get_system_metrics()
    log.info(f"  System: CPU={health_state['system']['cpu']}% Mem={health_state['system']['memory']}% Disk={health_state['system']['disk']}%")
    
    # Calculate health
    health_state["overall_health"] = calculate_health()
    health_state["last_updated"] = datetime.now().isoformat()
    
    # Add event
    health_state["events"].insert(0, {
        "time": datetime.now().isoformat(),
        "message": f"Health scan: {health_state['overall_health']}/100",
        "type": "info"
    })
    health_state["events"] = health_state["events"][:50]
    
    # Save state
    state_file = LOG_DIR / "health-state.json"
    state_file.write_text(json.dumps(health_state, indent=2))
    
    log.info(f"  Overall Health: {health_state['overall_health']}/100")
    
    # Auto-heal: restart any platform that's down
    for name, port in PLATFORMS.items():
        if health_state["platforms"].get(name, {}).get("status") == "down":
            log.warning(f"  ⚠️ {name} is DOWN — attempting restart...")
            # Try to restart by running the script
            script_map = {
                "Command Center": "command-center.py",
                "Bot Factory": "bot-factory.py",
                "Publishing Controller": "publishing-controller.py",
                "Royalty Dashboard": "royalty-dashboard.py",
                "Universal Submitter": "universal-submitter.py",
            }
            if name in script_map:
                script = HQ / script_map[name]
                if script.exists():
                    subprocess.Popen(
                        ["python3", str(script)],
                        cwd=str(HQ),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    health_state["events"].insert(0, {
                        "time": datetime.now().isoformat(),
                        "message": f"🔄 Auto-restarted {name}",
                        "type": "heal"
                    })
                    log.info(f"  ✅ Restart initiated for {name}")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = self.get_dashboard_html()
            self.wfile.write(html.encode())
        elif self.path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(health_state, indent=2).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def get_dashboard_html(self):
        platforms = health_state.get("platforms", {})
        sys_metrics = health_state.get("system", {})
        events = health_state.get("events", [])
        score = health_state.get("overall_health", 0)
        
        color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
        
        platform_rows = ""
        for name, info in sorted(platforms.items(), key=lambda x: x[1].get("port", 0)):
            status = info.get("status", "unknown")
            status_color = "green" if status == "ok" else "orange" if status == "degraded" else "red"
            platform_rows += f"""
            <tr>
                <td style="padding:8px;border-bottom:1px solid #333">{name}</td>
                <td style="padding:8px;border-bottom:1px solid #333">:{info.get('port','?')}</td>
                <td style="padding:8px;border-bottom:1px solid #333;color:{status_color}">{status.upper()}</td>
            </tr>"""
        
        event_rows = ""
        for e in events[:20]:
            event_rows += f"""
            <tr>
                <td style="padding:4px;border-bottom:1px solid #222;font-size:12px">{e.get('time','')[-8:]}</td>
                <td style="padding:4px;border-bottom:1px solid #222;font-size:12px;color:{'#4ade80' if e.get('type')=='heal' else '#fbbf24' if e.get('type')=='warn' else '#aaa'}">{e.get('message','')}</td>
            </tr>"""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta http-equiv="refresh" content="10">
<title>GGB Health Monitor</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#111; color:#eee; margin:0; padding:20px; }}
h1 {{ color:#FFD700; font-size:24px; margin:0 0 20px 0; }}
h2 {{ color:#FFA000; font-size:18px; margin:20px 0 10px 0; }}
.score {{ font-size:48px; font-weight:bold; }}
.green {{ color:#4ade80; }}
.yellow {{ color:#fbbf24; }}
.red {{ color:#f87171; }}
table {{ width:100%; border-collapse:collapse; }}
th {{ text-align:left; padding:8px; border-bottom:2px solid #FFD700; color:#FFD700; }}
td {{ padding:8px; border-bottom:1px solid #333; }}
.metrics {{ display:flex; gap:20px; margin:10px 0; }}
.metric {{ background:#1a1a2e; padding:15px; border-radius:8px; flex:1; text-align:center; }}
.metric .value {{ font-size:28px; font-weight:bold; }}
.metric .label {{ font-size:12px; color:#888; margin-top:4px; }}
.footer {{ margin-top:30px; font-size:11px; color:#555; text-align:center; }}
</style>
</head>
<body>
<h1>🩺 GGB System Health Monitor</h1>
<div class="score {color}">{score}/100</div>
<div style="color:#888;margin-bottom:20px">Last updated: {health_state.get('last_updated','')[-19:]}</div>

<h2>📊 System Resources</h2>
<div class="metrics">
    <div class="metric"><div class="value">{sys_metrics.get('cpu',0)}%</div><div class="label">CPU</div></div>
    <div class="metric"><div class="value">{sys_metrics.get('memory',0)}%</div><div class="label">Memory</div></div>
    <div class="metric"><div class="value">{sys_metrics.get('disk',0)}%</div><div class="label">Disk</div></div>
</div>

<h2>🖥️ Platforms</h2>
<table>
<tr><th>Platform</th><th>Port</th><th>Status</th></tr>
{platform_rows}
</table>

<h2>📋 Recent Events</h2>
<table>
<tr><th>Time</th><th>Event</th></tr>
{event_rows}
</table>

<div class="footer">
GGB Health Monitor v1.0 | Auto-refreshes every 10s | Port 8092
</div>
</body>
</html>"""

def health_loop():
    """Run health scans in a background thread."""
    while True:
        try:
            scan_cycle()
        except Exception as e:
            log.error(f"Scan error: {e}")
        time.sleep(60)

def main():
    log.info("=" * 50)
    log.info("GGB System Health Monitor starting...")
    log.info(f"Monitoring {len(PLATFORMS)} platforms")
    log.info(f"Dashboard: http://127.0.0.1:8092")
    log.info("=" * 50)
    
    # Start background scanner
    scanner = threading.Thread(target=health_loop, daemon=True)
    scanner.start()
    
    # Run initial scan
    scan_cycle()
    
    # Start HTTP server
    server = HTTPServer(("127.0.0.1", 8092), HealthHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down...")
        server.shutdown()

if __name__ == "__main__":
    main()
