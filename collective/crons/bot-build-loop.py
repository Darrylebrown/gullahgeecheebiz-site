#!/usr/bin/env python3
"""
GGB Collective Build Loop — distributor bots from the approved blueprint.
Build → critique → repair → critique → final pass. No one signs off until satisfied.
"""
import json, os, sys, time, threading, urllib.request, urllib.error
from pathlib import Path

SITE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
HQ = SITE / "ggb-engine" / "headquarters"
OUT = HQ / "gauntlet-output" / "bot-build-loop"
OUT.mkdir(parents=True, exist_ok=True)

ENV = {}
for line in (SITE / ".env").read_text().splitlines():
    line = line.strip()
    if line and "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        ENV[k] = v.strip().strip('"').strip("'")

OR_KEY = ENV.get("OPENROUTER_API_KEY", "")
BASE = "https://openrouter.ai/api/v1/chat/completions"

MODELS = [
    "deepseek/deepseek-chat",
    "qwen/qwen3.8-max",
    "mistralai/mistral-large-2512",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "openrouter/free",
    "google/gemma-4-31b-it:free",
    "moonshotai/kimi-k3",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "openai/gpt-oss-20b:free",
]

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def query(model, prompt, max_tokens=4000):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(BASE, data=body, headers={
        "Authorization": f"Bearer {OR_KEY}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read())
        content = d["choices"][0]["message"]["content"]
        return content if content else ""
    except Exception as e:
        log(f"  {model}: {e}")
        return ""

def extract_code(text):
    """Extract Python code from markdown fences."""
    if not text:
        return ""
    if "```python" in text:
        parts = text.split("```python")
        if len(parts) > 1:
            code = parts[1].split("```")[0]
            return code.strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) > 1:
            code = parts[1].split("\n", 1)[-1].rsplit("```", 1)[0]
            return code.strip()
    return text.strip()

def compile_check(code):
    """Hard gate: does it compile?"""
    import py_compile, tempfile
    tmp = tempfile.mktemp(suffix=".py")
    try:
        with open(tmp, "w") as f:
            f.write(code)
        py_compile.compile(tmp, doraise=True)
        return True, ""
    except py_compile.PyCompileError as e:
        return False, str(e)[:300]
    finally:
        os.unlink(tmp)

def judge(model, code, context):
    """Critique the code. Returns (score, issues)."""
    prompt = f"""You are a senior code reviewer. Score this Python bot code 0-10 on:
1. Does it compile? (already verified: {"YES" if compile_check(code)[0] else "NO"})
2. Does it follow the blueprint structure?
3. Is it production-ready (error handling, logging, session management)?
4. Does it avoid mock/fake patterns?

Context: {context[:500]}

Code:
```python
{code[:3000]}
```

Respond in JSON: {{"score": N, "issues": ["issue1", "issue2"]}}"""
    out = query(model, prompt, max_tokens=500)
    if not out:
        return 0, ["no response from critic"]
    try:
        # Find JSON in response
        start = out.find("{")
        end = out.rfind("}") + 1
        d = json.loads(out[start:end])
        return d.get("score", 0), d.get("issues", [])
    except Exception:
        return 0, [f"parse failed: {out[:100]}"]

def main():
    log("══ COLLECTIVE BUILD LOOP — distributor bots ══")
    
    # Read the blueprint for context
    blueprint_path = HQ / "gauntlet-output" / "distribution-connectivity" / "FINAL-BLUEPRINT-20260809-204830.md"
    blueprint = blueprint_path.read_text()[:2000] if blueprint_path.exists() else ""
    
    # The browser-base.py we already built
    base_path = SITE / "collective" / "bots" / "core" / "browser-base.py"
    base_code = base_path.read_text()[:1500] if base_path.exists() else ""
    
    context = f"Blueprint: {blueprint}\n\nBase class: {base_code}"
    
    # ROUND 1: Each model builds a Gumroad bot (the P0 API bot)
    log("ROUND 1 — build gumroad-publisher-v4.py")
    build_prompt = f"""Build a production-ready Gumroad publisher bot in Python.

IMPORTANT: Do NOT use chain-of-thought reasoning — respond directly and immediately with the code.

Requirements:
- Use the Gumroad REST API v2 (https://api.gumroad.com/v2)
- Read GUMROAD_ACCESS_TOKEN from env
- Support: --verify (check connection), --publish <epub_path> (create product), --list (list products)
- Proper error handling, logging, retry logic
- No mock/fake patterns — real API calls only
- Follow the base class pattern from browser-base.py (log function, human_delay, etc.)
- This is an API bot, NOT a browser bot — use requests/urllib, not Playwright

Context: {context[:800]}

Output ONLY the complete Python file in a ```python block."""

    builds = {}
    for model in MODELS:
        log(f"  building with {model}...")
        out = query(model, build_prompt, max_tokens=4000)
        code = extract_code(out)
        if len(code) > 200:
            ok, err = compile_check(code)
            log(f"  {model}: {len(code)} chars, compile={'PASS' if ok else 'FAIL'}")
            builds[model] = code
        else:
            log(f"  {model}: too little output")
    
    if not builds:
        log("❌ No valid builds — aborting")
        return
    
    # ROUND 2: Critique each build
    log("ROUND 2 — collective critiques")
    scores = {}
    for model, code in builds.items():
        total = 0
        issues = []
        for critic in MODELS:
            s, iss = judge(critic, code, context)
            total += s
            issues.extend(iss)
        avg = total / len(MODELS)
        scores[model] = (avg, issues)
        log(f"  {model}: {avg:.1f}/10, issues: {issues[:3]}")
    
    # Pick winner
    winner = max(scores, key=lambda m: scores[m][0])
    best_code = builds[winner]
    log(f"WINNER: {winner} ({scores[winner][0]:.1f}/10)")
    
    # ROUND 3+: LOOP until satisfied (score >= 8) or max 5 repair cycles
    MAX_REPAIRS = 5
    for repair_cycle in range(1, MAX_REPAIRS + 1):
        if scores[winner][0] >= 8.0:
            log(f"✅ SATISFIED at {scores[winner][0]:.1f}/10 — no repair needed")
            break

        log(f"ROUND 3.{repair_cycle} — repair cycle (score {scores[winner][0]:.1f}/10)")
        repair_prompt = f"""Fix these issues in the code:
{chr(10).join(scores[winner][1][:5])}

Original code:
```python
{best_code[:3000]}
```

Output the COMPLETE fixed Python file in a ```python block."""
        fixed = extract_code(query(winner, repair_prompt, max_tokens=4000))
        if len(fixed) > 200 and compile_check(fixed)[0]:
            best_code = fixed
            log("  repair applied and compiles")
        else:
            log("  repair failed — keeping previous version")

        # Re-critique after repair — only count critics that actually responded
        log(f"ROUND 4.{repair_cycle} — re-critique after repair")
        new_scores = {}
        for model, code in {winner: best_code}.items():
            total = 0
            responded = 0
            issues = []
            for critic in MODELS:
                s, iss = judge(critic, code, context)
                if s > 0:  # only count real responses
                    total += s
                    responded += 1
                    issues.extend(iss)
            avg = total / responded if responded > 0 else 0
            new_scores[model] = (avg, issues)
            log(f"  {model}: {avg:.1f}/10 ({responded}/{len(MODELS)} critics responded), issues: {issues[:3]}")
        scores[winner] = new_scores[winner]

    # Final satisfaction check
    log("FINAL — satisfaction check")
    final_scores = []
    for critic in MODELS:
        s, iss = judge(critic, best_code, context)
        final_scores.append(s)
        log(f"  {critic}: {s}/10")

    avg_final = sum(final_scores) / len(final_scores)
    log(f"FINAL SCORE: {avg_final:.1f}/10")
    
    # Save the bot
    bot_path = SITE / "collective" / "bots" / "distributors" / "gumroad-publisher-v4.py"
    bot_path.write_text(best_code)
    log(f"✅ Saved: {bot_path}")
    
    # Save report
    report = {
        "winner": winner,
        "scores": {m: s[0] for m, s in scores.items()},
        "final_avg": avg_final,
        "issues_fixed": scores[winner][1][:5],
        "bot_path": str(bot_path),
    }
    (OUT / "build-report.json").write_text(json.dumps(report, indent=2))
    log("DONE")

if __name__ == "__main__":
    main()
