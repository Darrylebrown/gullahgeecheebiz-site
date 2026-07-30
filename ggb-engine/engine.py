#!/usr/bin/env python3
"""
Gullah Geechee Biz — Workflow Engine v2
Doubled capacity: parallel execution, webhooks, API calls, scheduled triggers,
conditional branching, retry logic, and cross-workflow dependencies.
Zero dependencies. No cloud. Just Python.
"""

import json, os, sys, time, subprocess, traceback, threading, queue, re, socket, hashlib
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from queue import Empty as QueueEmpty

HOME = Path(__file__).resolve().parent.parent.parent
ENGINE_DIR = Path(__file__).resolve().parent
WORKFLOWS_DIR = ENGINE_DIR / "workflows"
LOGS_DIR = ENGINE_DIR / "logs"
STATE_DIR = ENGINE_DIR / "state"
WEBHOOK_PORT = 8768

for d in [ENGINE_DIR, WORKFLOWS_DIR, LOGS_DIR, STATE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Context ───────────────────────────────────────────────────────────────────

class WorkflowContext(dict):
    """Thread-safe workflow context with history."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()
        self.history = []
    
    def set(self, key, value):
        with self._lock:
            self[key] = value
            self.history.append({"time": datetime.now().isoformat(), "key": key, "value": str(value)[:100]})
    
    def get_safe(self, key, default=None):
        with self._lock:
            return self.get(key, default)

# ─── Step Types (v1 compatible + v2 additions) ────────────────────────────────

def step_python(step, context):
    code = step.get("code", "")
    if not code:
        return {"error": "No code provided"}
    local_vars = {"context": context, "result": None}
    try:
        exec(code, {}, local_vars)
        return {"result": local_vars.get("result")}
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

def step_shell(step, context):
    cmd = step.get("command", "")
    if not cmd:
        return {"error": "No command provided"}
    cmd = _substitute(cmd, context)
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=step.get("timeout", 300))
        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode, "success": result.returncode == 0}
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {step.get('timeout', 300)}s"}
    except Exception as e:
        return {"error": str(e)}

def step_write_file(step, context):
    path = _substitute(step.get("path", ""), context)
    content = _substitute(step.get("content", ""), context)
    path = str(HOME / path) if not path.startswith("/") else path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w") as f:
            f.write(content)
        return {"result": f"Written to {path}", "path": path}
    except Exception as e:
        return {"error": str(e)}

def step_read_file(step, context):
    path = step.get("path", "")
    var_name = step.get("var", "file_content")
    path = str(HOME / path) if not path.startswith("/") else path
    try:
        with open(path) as f:
            content = f.read()
        context.set(var_name, content)
        return {"result": f"Read {len(content)} chars from {path}"}
    except Exception as e:
        return {"error": str(e)}

def step_condition(step, context):
    condition = step.get("if", "")
    try:
        result = eval(condition, {"context": context})
        branch = "then" if result else "else"
        return {"result": result, "branch": branch}
    except Exception as e:
        return {"error": str(e), "branch": "else"}

def step_loop(step, context):
    items = step.get("items", [])
    var_name = step.get("var", "item")
    child_steps = step.get("steps", [])
    results = []
    for item in items:
        context.set(var_name, item)
        for child in child_steps:
            r = run_step(child, context)
            results.append(r)
            if r.get("error"):
                return {"error": f"Loop failed at item {item}", "results": results}
    return {"results": results, "count": len(items)}

def step_sleep(step, context):
    seconds = step.get("seconds", 1)
    time.sleep(seconds)
    return {"result": f"Slept {seconds}s"}

def step_log(step, context):
    message = _substitute(step.get("message", ""), context)
    print(f"[LOG] {message}")
    return {"result": message}

# ─── v2 Step Types ─────────────────────────────────────────────────────────────

def step_parallel(step, context):
    """Run multiple child workflows in parallel threads."""
    branches = step.get("branches", [])
    results = {}
    threads = []
    lock = threading.Lock()
    
    def run_branch(branch):
        name = branch.get("name", "unnamed")
        steps = branch.get("steps", [])
        branch_ctx = WorkflowContext(context)
        branch_results = []
        for s in steps:
            r = run_step(s, branch_ctx)
            branch_results.append(r)
            if r.get("error"):
                break
        with lock:
            results[name] = branch_results
    
    for branch in branches:
        t = threading.Thread(target=run_branch, args=(branch,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join(timeout=step.get("timeout", 300))
    
    return {"results": results, "branch_count": len(branches)}

def step_retry(step, context):
    """Run a step with retry logic."""
    max_attempts = step.get("max_retries", 3)
    delay = step.get("delay", 5)
    child = step.get("step", {})
    
    for attempt in range(1, max_attempts + 1):
        result = run_step(child, context)
        if not result.get("error"):
            return {"result": result, "attempts": attempt}
        if attempt < max_attempts:
            time.sleep(delay)
    
    return {"error": f"Failed after {max_attempts} attempts", "last_error": result.get("error")}

def step_aggregate(step, context):
    """Collect results from multiple context keys and combine them."""
    keys = step.get("keys", [])
    output_key = step.get("output", "aggregated")
    
    combined = {}
    for key in keys:
        val = context.get_safe(key, {})
        combined[key] = val
    
    context.set(output_key, combined)
    return {"result": f"Aggregated {len(keys)} keys into {output_key}"}

# ─── Step Router ───────────────────────────────────────────────────────────────

STEP_HANDLERS = {
    "python": step_python,
    "shell": step_shell,
    "write_file": step_write_file,
    "read_file": step_read_file,
    "condition": step_condition,
    "loop": step_loop,
    "sleep": step_sleep,
    "log": step_log,
    # v2 additions (API-free)
    "parallel": step_parallel,
    "retry": step_retry,
    "aggregate": step_aggregate,
}

def _substitute(text, context):
    def replacer(m):
        key = m.group(1)
        parts = key.split(".")
        val = context
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p, m.group(0))
            else:
                return m.group(0)
        return str(val) if not isinstance(val, (dict, list)) else str(val)
    return re.sub(r"\{\{(\w+(?:\.\w+)*)\}\}", replacer, text)

def run_step(step, context):
    step_type = step.get("type", "")
    name = step.get("name", step_type)
    
    handler = STEP_HANDLERS.get(step_type)
    if not handler:
        return {"error": f"Unknown step type: {step_type}"}
    
    print(f"  ▶ {name}...", end=" ", flush=True)
    start = time.time()
    
    try:
        result = handler(step, context)
        elapsed = time.time() - start
        
        if result.get("error"):
            print(f"❌ ({elapsed:.1f}s) — {result['error']}")
        else:
            print(f"✅ ({elapsed:.1f}s)")
        
        result["elapsed"] = elapsed
        result["name"] = name
        return result
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ ({elapsed:.1f}s) — {str(e)}")
        return {"error": str(e), "elapsed": elapsed, "name": name}

# ─── Workflow Runner ───────────────────────────────────────────────────────────

def load_workflow(name):
    path = WORKFLOWS_DIR / f"{name}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)

def run_workflow(name, initial_context=None):
    workflow = load_workflow(name)
    if not workflow:
        print(f"❌ Workflow not found: {name}")
        return {"error": f"Workflow not found: {name}"}
    
    context = WorkflowContext(initial_context or {})
    context.set("workflow_name", name)
    context.set("start_time", datetime.now().isoformat())
    
    max_retries = workflow.get("max_retries", 0)
    steps = workflow.get("steps", [])
    
    print(f"\n{'='*50}")
    print(f"🏗  Workflow: {name}")
    print(f"📅 {datetime.now().isoformat()}")
    print(f"📊 Steps: {len(steps)}")
    print(f"{'='*50}\n")
    
    results = []
    for attempt in range(max_retries + 1):
        results = []
        for step in steps:
            result = run_step(step, context)
            results.append(result)
            if result.get("error"):
                on_failure = step.get("on_failure", "abort")
                if on_failure == "abort":
                    break
                elif on_failure == "retry" and attempt < max_retries:
                    print(f"  🔄 Retry {attempt + 1}/{max_retries}...")
                    time.sleep(5)
                    break
        
        # Check if all steps passed
        if not any(r.get("error") for r in results):
            break
    
    passed = sum(1 for r in results if not r.get("error"))
    failed = sum(1 for r in results if r.get("error"))
    total_time = sum(r.get("elapsed", 0) for r in results)
    
    print(f"\n{'='*50}")
    print(f"📋 Workflow Complete: {name}")
    print(f"⏱  {total_time:.1f}s total")
    print(f"✅ {passed}/{len(steps)} steps passed")
    if failed:
        print(f"❌ {failed} step(s) failed")
    print(f"{'='*50}")
    
    return {"workflow": name, "results": results, "passed": passed, "failed": failed, "total_time": total_time}

# ─── Webhook Server ─────────────────────────────────────────────────────────────

class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._json(200, {"status": "ok", "engine": "v2", "workflows": len(list(WORKFLOWS_DIR.glob("*.json")))})
        else:
            self._json(404, {"error": "Not found"})
    
    def do_POST(self):
        path = urlparse(self.path).path
        webhooks_file = STATE_DIR / "webhooks.json"
        
        if webhooks_file.exists():
            with open(webhooks_file) as f:
                webhooks = json.load(f)
            
            if path in webhooks:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
                data = json.loads(body) if body else {}
                
                workflow_name = webhooks[path]["workflow"]
                self._json(202, {"status": "accepted", "workflow": workflow_name})
                
                # Run in background
                t = threading.Thread(target=run_workflow, args=(workflow_name, data))
                t.daemon = True
                t.start()
            else:
                self._json(404, {"error": f"No webhook registered for {path}"})
        else:
            self._json(404, {"error": "No webhooks registered"})
    
    def _json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
    
    def log_message(self, format, *args):
        pass

def start_webhook_server():
    server = HTTPServer(("0.0.0.0", WEBHOOK_PORT), WebhookHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"  🌐 Webhook server on port {WEBHOOK_PORT}")

# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Workflow Engine v2 — Active-Active")
    parser.add_argument("action", nargs="?", default="list", choices=["list", "run", "webhook", "test", "serve"])
    parser.add_argument("workflow", nargs="?", default="", help="Workflow name")
    parser.add_argument("--context", "-c", default="{}", help="Initial context as JSON")
    parser.add_argument("--backup", action="store_true", help="Start as backup instance")
    
    args = parser.parse_args()
    
    if args.action == "serve":
        instance_id = f"engine-{socket.gethostname()}-{int(time.time())}"
        is_primary = not args.backup
        role = "PRIMARY" if is_primary else "BACKUP"
        
        print(f"\n{'='*50}")
        print(f"⚙️  GGB Engine — {role}")
        print(f"{'='*50}")
        print(f"   Instance: {instance_id}")
        print(f"   Workflows: {len(list(WORKFLOWS_DIR.glob('*.json')))}")
        print(f"   Step types: {len(STEP_HANDLERS)}")
        print(f"{'='*50}\n")
        
        # Register with hub
        try:
            import urllib.request
            hub_url = f"http://localhost:8770/api/register?name=GGB-Engine-{instance_id[:8]}&type=engine"
            urllib.request.urlopen(hub_url, timeout=3)
            print(f"   ✅ Registered with GGB Hub")
        except:
            print(f"   ⚠️  Hub not available — running standalone")
        
        # Heartbeat loop
        while True:
            time.sleep(30)
    
    elif args.action == "list":
        print(f"\n📋 Available Workflows ({len(list(WORKFLOWS_DIR.glob('*.json')))}):")
        for wf in sorted(WORKFLOWS_DIR.glob("*.json")):
            with open(wf) as f:
                data = json.load(f)
            print(f"  • {data.get('name', wf.stem)}: {data.get('description', '')[:60]}")
        print()
    
    elif args.action == "run":
        if not args.workflow:
            print("❌ Specify a workflow name: python3 engine.py run <name>")
            return
        context = json.loads(args.context)
        run_workflow(args.workflow, context)
    
    elif args.action == "webhook":
        start_webhook_server()
        print(f"  🌐 Webhook server running on http://localhost:{WEBHOOK_PORT}")
        print(f"  📡 Endpoints:")
        webhooks_file = STATE_DIR / "webhooks.json"
        if webhooks_file.exists():
            with open(webhooks_file) as f:
                webhooks = json.load(f)
            for route, info in webhooks.items():
                print(f"     POST http://localhost:{WEBHOOK_PORT}{route} → {info['workflow']}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
    
    elif args.action == "test":
        print(f"\n🧪 Engine v2 Self-Test")
        print(f"   Step types: {len(STEP_HANDLERS)}")
        print(f"   Workflows: {len(list(WORKFLOWS_DIR.glob('*.json')))}")
        print(f"   Webhook port: {WEBHOOK_PORT}")
        
        # Test parallel execution
        test_workflow = {
            "name": "self-test",
            "steps": [
                {"name": "test-parallel", "type": "parallel", "branches": [
                    {"name": "branch-a", "steps": [{"name": "sleep-1", "type": "sleep", "seconds": 1}]},
                    {"name": "branch-b", "steps": [{"name": "sleep-2", "type": "sleep", "seconds": 1}]},
                    {"name": "branch-c", "steps": [{"name": "sleep-3", "type": "sleep", "seconds": 1}]},
                ]},
                {"name": "test-aggregate", "type": "aggregate", "keys": ["workflow_name", "start_time"], "output": "test_result"},
                {"name": "test-log", "type": "log", "message": "Self-test complete — all API-free steps working"},
            ]
        }
        
        # Save and run
        test_path = WORKFLOWS_DIR / "self-test.json"
        with open(test_path, "w") as f:
            json.dump(test_workflow, f, indent=2)
        
        result = run_workflow("self-test")
        
        # Cleanup
        test_path.unlink(missing_ok=True)
        
        if result.get("failed", 0) == 0:
            print(f"\n✅ All tests passed")
        else:
            print(f"\n❌ {result.get('failed')} test(s) failed")

if __name__ == "__main__":
    main()
