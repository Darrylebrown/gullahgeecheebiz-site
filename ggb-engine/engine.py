#!/usr/bin/env python3
"""
Gullah Geechee Biz — Workflow Engine
Zero dependencies. No APIs. No cloud. Just Python.
Runs locally, chains steps, logs everything.
"""

import json, os, sys, time, subprocess, traceback
from datetime import datetime
from pathlib import Path

HOME = Path(__file__).resolve().parent.parent.parent  # gullahgeecheebiz-site/
ENGINE_DIR = Path(__file__).resolve().parent  # ggb-engine/
WORKFLOWS_DIR = ENGINE_DIR / "workflows"
LOGS_DIR = ENGINE_DIR / "logs"
STATE_DIR = ENGINE_DIR / "state"

for d in [ENGINE_DIR, WORKFLOWS_DIR, LOGS_DIR, STATE_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ─── Step Types ───────────────────────────────────────────────────────────────

def step_python(step, context):
    """Run a Python expression or script."""
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
    """Run a shell command."""
    cmd = step.get("command", "")
    if not cmd:
        return {"error": "No command provided"}
    
    # Substitute context variables
    cmd = _substitute(cmd, context)
    
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=step.get("timeout", 300)
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {step.get('timeout', 300)}s"}
    except Exception as e:
        return {"error": str(e)}


def _substitute(text, context):
    """Replace {{var}} and {{var.key}} with context values."""
    import re
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


def step_write_file(step, context):
    """Write content to a file."""
    path = step.get("path", "")
    content = step.get("content", "")
    
    path = _substitute(path, context)
    content = _substitute(content, context)
    
    path = str(HOME / path) if not path.startswith("/") else path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    try:
        with open(path, "w") as f:
            f.write(content)
        return {"result": f"Written to {path}", "path": path}
    except Exception as e:
        return {"error": str(e)}


def step_read_file(step, context):
    """Read a file into context."""
    path = step.get("path", "")
    var_name = step.get("var", "file_content")
    
    path = str(HOME / path) if not path.startswith("/") else path
    
    try:
        with open(path) as f:
            content = f.read()
        context[var_name] = content
        return {"result": f"Read {len(content)} chars from {path}"}
    except Exception as e:
        return {"error": str(e)}


def step_condition(step, context):
    """Evaluate a condition and return which branch to take."""
    condition = step.get("if", "")
    try:
        result = eval(condition, {"context": context})
        branch = "then" if result else "else"
        return {"result": result, "branch": branch}
    except Exception as e:
        return {"error": str(e), "branch": "else"}


def step_loop(step, context):
    """Loop over items and run child steps for each."""
    items = step.get("items", [])
    var_name = step.get("var", "item")
    child_steps = step.get("steps", [])
    
    results = []
    for item in items:
        context[var_name] = item
        for child in child_steps:
            r = run_step(child, context)
            results.append(r)
            if r.get("error"):
                return {"error": f"Loop failed at item {item}", "results": results}
    
    return {"results": results, "count": len(items)}


def step_sleep(step, context):
    """Wait for a duration."""
    seconds = step.get("seconds", 1)
    time.sleep(seconds)
    return {"result": f"Slept {seconds}s"}


def step_log(step, context):
    """Log a message."""
    message = step.get("message", "")
    message = _substitute(message, context)
    print(f"[LOG] {message}")
    return {"result": message}


# ─── Step Router ──────────────────────────────────────────────────────────────

STEP_HANDLERS = {
    "python": step_python,
    "shell": step_shell,
    "write_file": step_write_file,
    "read_file": step_read_file,
    "condition": step_condition,
    "loop": step_loop,
    "sleep": step_sleep,
    "log": step_log,
}


def run_step(step, context):
    """Run a single step and return its result."""
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


# ─── Workflow Runner ──────────────────────────────────────────────────────────

def run_workflow(workflow, context=None):
    """Run a full workflow definition."""
    if context is None:
        context = {}
    
    name = workflow.get("name", "unnamed")
    steps = workflow.get("steps", [])
    max_retries = workflow.get("max_retries", 0)
    
    print(f"\n{'='*50}")
    print(f"🏗  Workflow: {name}")
    print(f"📅 {datetime.now().isoformat()}")
    print(f"📊 Steps: {len(steps)}")
    print(f"{'='*50}\n")
    
    results = []
    overall_start = time.time()
    failed = False
    
    for i, step in enumerate(steps):
        step_name = step.get("name", f"step_{i}")
        
        # Retry logic
        for attempt in range(max_retries + 1):
            result = run_step(step, context)
            results.append(result)
            
            if result.get("error"):
                if attempt < max_retries:
                    wait = step.get("retry_delay", 5)
                    print(f"  ↻ Retry {attempt+1}/{max_retries} in {wait}s...")
                    time.sleep(wait)
                else:
                    failed = True
                    if step.get("on_failure") == "continue":
                        print(f"  ⚠ Continuing despite failure")
                        failed = False
                        break
            else:
                # Store result in context
                if step.get("store"):
                    store_key = step["store"]
                    store_val = step.get("store_field", "result")
                    context[store_key] = result.get(store_val, result)
                break
        
        if failed and step.get("on_failure") != "continue":
            break
    
    overall_elapsed = time.time() - overall_start
    
    # Summary
    passed = sum(1 for r in results if not r.get("error"))
    total = len(results)
    
    print(f"\n{'='*50}")
    print(f"📋 Workflow Complete: {name}")
    print(f"⏱  {overall_elapsed:.1f}s total")
    print(f"✅ {passed}/{total} steps passed")
    if failed:
        print(f"❌ Workflow FAILED")
    else:
        print(f"✅ Workflow SUCCEEDED")
    print(f"{'='*50}\n")
    
    return {
        "name": name,
        "success": not failed,
        "elapsed": overall_elapsed,
        "passed": passed,
        "total": total,
        "results": results,
        "context": context
    }


# ─── Workflow File Management ─────────────────────────────────────────────────

def load_workflow(name):
    """Load a workflow from a JSON file."""
    path = WORKFLOWS_DIR / f"{name}.json"
    if not path.exists():
        print(f"Workflow not found: {name}")
        print(f"Available: {', '.join(list_workflows())}")
        return None
    with open(path) as f:
        return json.load(f)


def list_workflows():
    """List all available workflows."""
    return [p.stem for p in WORKFLOWS_DIR.glob("*.json")]


def save_workflow(workflow):
    """Save a workflow definition."""
    name = workflow.get("name", "unnamed")
    path = WORKFLOWS_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(workflow, f, indent=2)
    print(f"Saved workflow: {name} ({path})")
    return path


def log_run(name, result):
    """Log a workflow run to a file."""
    log_file = LOGS_DIR / f"{name}.log"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "success": result["success"],
        "elapsed": result["elapsed"],
        "passed": result["passed"],
        "total": result["total"]
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Workflow Engine")
    parser.add_argument("command", nargs="?", default="list",
                        help="run <name> | list | create <name>")
    parser.add_argument("arg", nargs="?", help="Workflow name or JSON")
    
    args = parser.parse_args()
    
    if args.command == "list":
        workflows = list_workflows()
        if workflows:
            print("Available workflows:")
            for w in workflows:
                print(f"  • {w}")
        else:
            print("No workflows yet. Create one with: python3 engine.py create <name>")
    
    elif args.command == "run":
        name = args.arg
        if not name:
            print("Usage: python3 engine.py run <workflow_name>")
            return
        workflow = load_workflow(name)
        if workflow:
            result = run_workflow(workflow)
            log_run(name, result)
    
    elif args.command == "create":
        name = args.arg or "new-workflow"
        workflow = {
            "name": name,
            "description": "Auto-generated workflow",
            "max_retries": 1,
            "steps": [
                {"name": "start", "type": "log", "message": f"Starting {name}"},
                {"name": "done", "type": "log", "message": "Workflow complete"}
            ]
        }
        save_workflow(workflow)
    
    else:
        # Try running as workflow name
        workflow = load_workflow(args.command)
        if workflow:
            result = run_workflow(workflow)
            log_run(args.command, result)


if __name__ == "__main__":
    main()
