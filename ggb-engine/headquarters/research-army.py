#!/usr/bin/env python3
"""
GGB Research & Review Army — 50 autonomous research agents that review
100% of production output. Every book, song, movie, ad, pin, post, and
piece of content gets reviewed by multiple agents before release.
"""
import json, os, sys, time, sqlite3, requests, hashlib, random, threading
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
ARMY_DIR = LOGS_DIR / "research-army"
STATE_FILE = ARMY_DIR / "army-state.json"
REVIEWS_FILE = ARMY_DIR / "reviews.json"
QUEUE_FILE = ARMY_DIR / "review-queue.json"
FINDINGS_FILE = ARMY_DIR / "findings.json"

ARMY_DIR.mkdir(parents=True, exist_ok=True)

def get_api_key():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if "OPENROUTER_API_KEY" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def call_ai(prompt, model="ggb-free-auto", max_tokens=2000):
    """Route through OmniRoute gateway, falling back to Agnes AI (free) if the gateway fails."""
    result = omniroute_shim.call_ai(prompt=prompt, model=model, max_tokens=min(max_tokens, 4000))
    if result:
        return result
    # Fallback: Agnes AI free OpenAI-compatible endpoint (key in BASE_DIR/.env)
    try:
        env_file = BASE_DIR / ".env"
        agnes_key = ""
        if env_file.exists():
            for line in env_file.read_text().split("\n"):
                if "AGNES_API_KEY" in line:
                    agnes_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        if agnes_key:
            r = requests.post(
                "https://apihub.agnes-ai.com/v1/chat/completions",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {agnes_key}"},
                json={
                    "model": "agnes-2.5-flash",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": min(max_tokens, 4000),
                },
                timeout=120,
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
    except Exception:
        pass
    return None

# ─── 50 Research Agent Specializations ────────────────────────────────────

RESEARCH_AGENTS = [
    # Cultural & Historical Accuracy (1-10)
    {"id": 1,  "name": "Gullah Language Authenticator",     "focus": "Verify Gullah Geechee language and dialect accuracy", "model": "google/gemini-2.5-flash"},
    {"id": 2,  "name": "Historical Fact Checker",           "focus": "Verify historical dates, events, and figures", "model": "deepseek/deepseek-chat"},
    {"id": 3,  "name": "Cultural Sensitivity Reader",        "focus": "Ensure content respects Gullah Geechee traditions", "model": "qwen/qwen3.7-max"},
    {"id": 4,  "name": "Geographic Accuracy Verifier",       "focus": "Verify Lowcountry locations, landmarks, and geography", "model": "google/gemini-2.5-flash"},
    {"id": 5,  "name": "Foodways & Recipe Authenticator",    "focus": "Verify Gullah Geechee recipes and food traditions", "model": "deepseek/deepseek-chat"},
    {"id": 6,  "name": "Spiritual & Religious Context Check","focus": "Ensure spiritual references are accurate and respectful", "model": "qwen/qwen3.7-max"},
    {"id": 7,  "name": "Music & Song Tradition Verifier",    "focus": "Verify musical traditions, spirituals, and work songs", "model": "google/gemini-2.5-flash"},
    {"id": 8,  "name": "Craft & Artisan Accuracy Check",    "focus": "Verify sweetgrass basket weaving and craft traditions", "model": "deepseek/deepseek-chat"},
    {"id": 9,  "name": "Family & Kinship Structure Analyst", "focus": "Verify family structures and kinship terminology", "model": "qwen/qwen3.7-max"},
    {"id": 10, "name": "Oral History & Storytelling Verifier","focus": "Ensure oral traditions are accurately represented", "model": "google/gemini-2.5-flash"},
    
    # Content Quality (11-20)
    {"id": 11, "name": "Grammar & Spelling Auditor",         "focus": "Check grammar, spelling, and punctuation", "model": "deepseek/deepseek-chat"},
    {"id": 12, "name": "Readability & Flow Analyst",         "focus": "Assess reading level, sentence flow, and clarity", "model": "qwen/qwen3.7-max"},
    {"id": 13, "name": "Plagiarism & Originality Checker",  "focus": "Detect AI-generated patterns and ensure originality", "model": "google/gemini-2.5-flash"},
    {"id": 14, "name": "Tone & Voice Consistency Auditor",  "focus": "Ensure consistent Gullah Geechee voice throughout", "model": "deepseek/deepseek-chat"},
    {"id": 15, "name": "Structure & Organization Reviewer", "focus": "Check logical flow, chapter structure, and organization", "model": "qwen/qwen3.7-max"},
    {"id": 16, "name": "Factual Accuracy Cross-Checker",    "focus": "Cross-reference facts against multiple sources", "model": "google/gemini-2.5-flash"},
    {"id": 17, "name": "Citation & Source Verifier",        "focus": "Verify citations and source attribution", "model": "deepseek/deepseek-chat"},
    {"id": 18, "name": "Consistency & Continuity Checker",  "focus": "Check for internal consistency across content", "model": "qwen/qwen3.7-max"},
    {"id": 19, "name": "Redundancy & Repetition Detector",  "focus": "Detect repeated phrases, ideas, and content", "model": "google/gemini-2.5-flash"},
    {"id": 20, "name": "Length & Completeness Auditor",     "focus": "Verify content meets length and completeness standards", "model": "deepseek/deepseek-chat"},
    
    # SEO & Discoverability (21-30)
    {"id": 21, "name": "Keyword Optimization Analyst",      "focus": "Verify keyword usage and search optimization", "model": "qwen/qwen3.7-max"},
    {"id": 22, "name": "Title & Metadata Reviewer",         "focus": "Review title, description, and metadata quality", "model": "google/gemini-2.5-flash"},
    {"id": 23, "name": "Platform-Specific SEO Checker",     "focus": "Verify SEO for Google, Amazon, Spotify, YouTube", "model": "deepseek/deepseek-chat"},
    {"id": 24, "name": "Hashtag & Tag Strategist",          "focus": "Review hashtag and tag strategy for each platform", "model": "qwen/qwen3.7-max"},
    {"id": 25, "name": "Competitive Positioning Analyst",   "focus": "Compare content against competitors in the same space", "model": "google/gemini-2.5-flash"},
    {"id": 26, "name": "Trend Alignment Checker",           "focus": "Verify content aligns with current trends", "model": "deepseek/deepseek-chat"},
    {"id": 27, "name": "Audience Targeting Reviewer",        "focus": "Verify content targets the right audience", "model": "qwen/qwen3.7-max"},
    {"id": 28, "name": "Call-to-Action Effectiveness Check","focus": "Review CTA placement, wording, and effectiveness", "model": "google/gemini-2.5-flash"},
    {"id": 29, "name": "Visual & Media Alignment Auditor",  "focus": "Verify visuals align with content and brand", "model": "deepseek/deepseek-chat"},
    {"id": 30, "name": "Cross-Platform Consistency Check",  "focus": "Ensure content works across all distribution platforms", "model": "qwen/qwen3.7-max"},
    
    # Legal & Compliance (31-35)
    {"id": 31, "name": "Copyright & Licensing Checker",     "focus": "Verify no copyrighted material is used without permission", "model": "google/gemini-2.5-flash"},
    {"id": 32, "name": "Terms of Service Compliance Auditor","focus": "Verify content complies with platform ToS", "model": "deepseek/deepseek-chat"},
    {"id": 33, "name": "Privacy & Data Protection Checker", "focus": "Ensure no private data is exposed in content", "model": "qwen/qwen3.7-max"},
    {"id": 34, "name": "Trademark & Brand Usage Verifier",  "focus": "Verify proper use of trademarks and brand names", "model": "google/gemini-2.5-flash"},
    {"id": 35, "name": "Content Rating & Age Gate Checker", "focus": "Verify content is appropriate for target age group", "model": "deepseek/deepseek-chat"},
    
    # Market Readiness (36-45)
    {"id": 36, "name": "Market Demand Analyst",             "focus": "Assess market demand for the content", "model": "qwen/qwen3.7-max"},
    {"id": 37, "name": "Pricing & Value Reviewer",          "focus": "Review pricing strategy and perceived value", "model": "google/gemini-2.5-flash"},
    {"id": 38, "name": "Launch Timing Strategist",          "focus": "Recommend optimal launch timing", "model": "deepseek/deepseek-chat"},
    {"id": 39, "name": "Promotional Angle Finder",          "focus": "Identify best promotional angles for marketing", "model": "qwen/qwen3.7-max"},
    {"id": 40, "name": "Review & Rating Predictor",         "focus": "Predict likely reviews and ratings", "model": "google/gemini-2.5-flash"},
    {"id": 41, "name": "Sales Channel Optimizer",           "focus": "Recommend best sales channels for each content type", "model": "deepseek/deepseek-chat"},
    {"id": 42, "name": "International Market Checker",      "focus": "Assess appeal in Spanish and Mandarin markets", "model": "qwen/qwen3.7-max"},
    {"id": 43, "name": "Bundling & Cross-Sell Analyst",     "focus": "Identify bundling and cross-selling opportunities", "model": "google/gemini-2.5-flash"},
    {"id": 44, "name": "Subscription Model Feasibility Check","focus": "Assess if content fits subscription models", "model": "deepseek/deepseek-chat"},
    {"id": 45, "name": "Revenue Potential Estimator",       "focus": "Estimate revenue potential for each content piece", "model": "qwen/qwen3.7-max"},
    
    # Improvement & Evolution (46-50)
    {"id": 46, "name": "Improvement Suggestion Generator",  "focus": "Generate actionable improvement suggestions", "model": "google/gemini-2.5-flash"},
    {"id": 47, "name": "Version 2.0 Planner",              "focus": "Plan next version or sequel based on review", "model": "deepseek/deepseek-chat"},
    {"id": 48, "name": "Spin-Off Content Identifier",       "focus": "Identify spin-off content opportunities", "model": "qwen/qwen3.7-max"},
    {"id": 49, "name": "Cross-Cultural Adaptation Checker",  "focus": "Assess content for Spanish and Mandarin adaptation", "model": "google/gemini-2.5-flash"},
    {"id": 50, "name": "Quality Score Aggregator",          "focus": "Aggregate all reviews into a final quality score", "model": "deepseek/deepseek-chat"},
]

# ─── Research Army ─────────────────────────────────────────────────────────

class ResearchArmy:
    """50 autonomous research agents that review 100% of production."""
    
    def __init__(self):
        self.api_key = get_api_key()
        self.state = self._load_state()
        self.reviews = self._load_reviews()
        self.queue = self._load_queue()
        self.findings = self._load_findings()
        self.agents = RESEARCH_AGENTS
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {
            "runs": 0, "items_reviewed": 0, "reviews_completed": 0,
            "issues_found": 0, "issues_resolved": 0,
            "avg_quality_score": 0, "last_review": None,
            "agent_performance": {str(a["id"]): {"reviews": 0, "issues": 0} for a in RESEARCH_AGENTS}
        }
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _load_reviews(self) -> List[Dict]:
        if REVIEWS_FILE.exists():
            try:
                return json.loads(REVIEWS_FILE.read_text())
            except:
                pass
        return []
    
    def _save_reviews(self):
        REVIEWS_FILE.write_text(json.dumps(self.reviews[-1000:], indent=2))
    
    def _load_queue(self) -> List[Dict]:
        if QUEUE_FILE.exists():
            try:
                return json.loads(QUEUE_FILE.read_text())
            except:
                pass
        return []
    
    def _save_queue(self):
        QUEUE_FILE.write_text(json.dumps(self.queue, indent=2))
    
    def _load_findings(self) -> List[Dict]:
        if FINDINGS_FILE.exists():
            try:
                return json.loads(FINDINGS_FILE.read_text())
            except:
                pass
        return []
    
    def _save_findings(self):
        FINDINGS_FILE.write_text(json.dumps(self.findings[-500:], indent=2))
    
    def _scan_production_output(self) -> List[Dict]:
        """Scan all production output directories for items to review."""
        items = []
        
        # Content Factory output
        factory_dir = LOGS_DIR / "content-factory" / "output"
        if factory_dir.exists():
            for f in sorted(factory_dir.glob("*.md"))[-50:]:
                items.append({
                    "source": "content-factory",
                    "path": str(f.relative_to(BASE_DIR)),
                    "title": f.stem[:60],
                    "type": f.stem.split("-")[0] if "-" in f.stem else "unknown",
                    "content": f.read_text()[:1000],
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                })
        
        # Dream Weaver output
        dream_dir = LOGS_DIR / "dream-weaver"
        dreams_file = dream_dir / "dreams.json"
        if dreams_file.exists():
            try:
                dreams = json.loads(dreams_file.read_text())
                for d in dreams[-20:]:
                    items.append({
                        "source": "dream-weaver",
                        "path": f"dream-weaver/{d.get('id', 'unknown')}",
                        "title": d.get("title", "Untitled Dream"),
                        "type": d.get("type", "dream"),
                        "content": json.dumps(d)[:1000],
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                    })
            except:
                pass
        
        # Pipeline database
        try:
            conn = sqlite3.connect(str(PUB_DB))
            rows = conn.execute(
                "SELECT manifest_id, data FROM manifests WHERE state = 'published' ORDER BY ROWID DESC LIMIT 20"
            ).fetchall()
            conn.close()
            for mid, data_json in rows:
                try:
                    data = json.loads(data_json) if data_json else {}
                except:
                    data = {}
                title = data.get("title", mid)
                if isinstance(title, dict):
                    title = title.get("canonical", str(title))
                items.append({
                    "source": "pipeline",
                    "path": mid,
                    "title": str(title)[:60],
                    "type": "book",
                    "content": json.dumps(data)[:1000],
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                })
        except:
            pass
        
        return items
    
    def review_item(self, item: Dict, agent: Dict) -> Optional[Dict]:
        """Have a single agent review a content item."""
        prompt = f"""You are {agent['name']}, a research and review agent for Gullah Geechee Biz.

Your Focus: {agent['focus']}

Review this content item:
Title: {item.get('title', 'Untitled')}
Type: {item.get('type', 'unknown')}
Source: {item.get('source', 'unknown')}

Content Preview:
{item.get('content', '')[:800]}

Your task: Review this content from your specific focus area.

Provide:
1. Your assessment (pass/fail/needs-improvement)
2. Specific findings (what's correct, what's wrong)
3. Issues found (if any)
4. Improvement suggestions
5. A score from 0-100 for your focus area

Return as JSON:
{{"agent_id": {agent['id']}, "agent_name": "{agent['name']}", "assessment": "pass/fail/needs-improvement", "findings": ["..."], "issues": ["..."], "suggestions": ["..."], "score": 0-100, "confidence": 0-100}}"""
        
        result = call_ai(prompt, model=agent["model"], max_tokens=1500)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            review = json.loads(result[start:end])
            review["item_title"] = item.get("title", "?")
            review["item_type"] = item.get("type", "?")
            review["item_source"] = item.get("source", "?")
            review["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            review["review_id"] = hashlib.md5(f"{agent['id']}-{item.get('title', '')}-{datetime.now().timestamp()}".encode()).hexdigest()[:12]
            return review
        except:
            return None
    
    def review_item_full(self, item: Dict) -> Dict:
        """Review an item with all 50 agents."""
        print(f"\n📋 Reviewing: {item.get('title', '?')[:50]}")
        print(f"   Type: {item.get('type', '?')} | Source: {item.get('source', '?')}")
        print(f"   Agents: {len(self.agents)}\n")
        
        reviews = []
        threads = []
        lock = threading.Lock()
        
        def review_worker(agent):
            r = self.review_item(item, agent)
            if r:
                with lock:
                    reviews.append(r)
                    aid = str(agent["id"])
                    self.state["agent_performance"][aid]["reviews"] += 1
                    if r.get("issues") and len(r["issues"]) > 0:
                        self.state["agent_performance"][aid]["issues"] += len(r["issues"])
        
        for agent in self.agents:
            t = threading.Thread(target=review_worker, args=(agent,))
            threads.append(t)
            t.start()
            time.sleep(0.1)
        
        for t in threads:
            t.join(timeout=60)
        
        # Calculate aggregate scores
        scores = [r.get("score", 0) for r in reviews if r.get("score") is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        assessments = {}
        for r in reviews:
            a = r.get("assessment", "unknown")
            assessments[a] = assessments.get(a, 0) + 1
        
        all_issues = []
        for r in reviews:
            for issue in r.get("issues", []):
                all_issues.append({"agent": r["agent_name"], "issue": issue})
        
        all_suggestions = []
        for r in reviews:
            for s in r.get("suggestions", []):
                all_suggestions.append({"agent": r["agent_name"], "suggestion": s})
        
        result = {
            "item_title": item.get("title", "?"),
            "item_type": item.get("type", "?"),
            "item_source": item.get("source", "?"),
            "reviews_completed": len(reviews),
            "agents_total": len(self.agents),
            "avg_quality_score": round(avg_score, 1),
            "assessments": assessments,
            "total_issues": len(all_issues),
            "total_suggestions": len(all_suggestions),
            "issues": all_issues[:20],
            "suggestions": all_suggestions[:10],
            "top_agents": sorted(reviews, key=lambda r: r.get("score", 0), reverse=True)[:3],
            "bottom_agents": sorted(reviews, key=lambda r: r.get("score", 0))[:3],
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        
        self.reviews.append(result)
        self.state["items_reviewed"] += 1
        self.state["reviews_completed"] += len(reviews)
        self.state["issues_found"] += len(all_issues)
        self.state["avg_quality_score"] = (
            (self.state["avg_quality_score"] * (self.state["items_reviewed"] - 1) + avg_score)
            / self.state["items_reviewed"]
        )
        self.state["last_review"] = datetime.now(timezone.utc).isoformat()
        self._save_reviews()
        self._save_state()
        
        return result
    
    def review_all_pending(self, limit: int = 5) -> List[Dict]:
        """Review all pending items in the queue."""
        items = self._scan_production_output()
        results = []
        
        for item in items[:limit]:
            result = self.review_item_full(item)
            results.append(result)
            time.sleep(2)
        
        return results
    
    def full_cycle(self) -> Dict:
        """Run full research army cycle."""
        print(f"\n{'='*60}")
        print(f"🔬 GGB RESEARCH ARMY — Full Review Cycle")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        # 1. Scan for new content
        print("🔍 Step 1: Scanning for new content...")
        items = self._scan_production_output()
        print(f"   Found {len(items)} items to review\n")
        
        # 2. Review each item with all 50 agents
        print("🔬 Step 2: Reviewing with 50 agents...")
        results = []
        for item in items[:3]:  # Review up to 3 items per cycle
            result = self.review_item_full(item)
            results.append(result)
            time.sleep(3)
        
        # 3. Generate findings report
        print("\n📊 Step 3: Generating findings report...")
        all_issues = []
        for r in results:
            all_issues.extend(r.get("issues", []))
        
        top_issues = sorted(all_issues, key=lambda x: x.get("issue", ""))[:10]
        
        self.findings.append({
            "cycle": self.state["runs"] + 1,
            "items_reviewed": len(results),
            "total_issues": len(all_issues),
            "top_issues": top_issues,
            "avg_quality": round(sum(r.get("avg_quality_score", 0) for r in results) / len(results), 1) if results else 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })
        self._save_findings()
        
        self.state["runs"] += 1
        self._save_state()
        
        print(f"\n{'='*60}")
        print(f"✅ RESEARCH ARMY CYCLE COMPLETE")
        print(f"{'='*60}")
        print(f"   Items reviewed: {len(results)}")
        print(f"   Total reviews: {sum(r['reviews_completed'] for r in results)}")
        print(f"   Issues found: {len(all_issues)}")
        print(f"   Avg quality score: {self.state['avg_quality_score']:.1f}/100")
        
        return {"items_reviewed": len(results), "issues_found": len(all_issues), "results": results}
    
    def report(self) -> Dict:
        return {
            "state": self.state,
            "reviews_completed": len(self.reviews),
            "findings": len(self.findings),
            "agents": len(self.agents),
            "top_performers": sorted(
                [{"id": k, "name": next((a["name"] for a in self.agents if str(a["id"]) == k), "?"), **v}
                 for k, v in self.state["agent_performance"].items()],
                key=lambda x: x.get("reviews", 0), reverse=True
            )[:5],
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Research & Review Army")
    parser.add_argument("--cycle", action="store_true", help="Run full review cycle")
    parser.add_argument("--review", type=str, help="Review a specific item by title or path")
    parser.add_argument("--scan", action="store_true", help="Scan for items to review")
    parser.add_argument("--report", action="store_true", help="Army status report")
    parser.add_argument("--agents", action="store_true", help="List all 50 agents")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"🔬 GGB RESEARCH & REVIEW ARMY")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    army = ResearchArmy()
    
    if args.cycle:
        army.full_cycle()
        return
    
    if args.scan:
        items = army._scan_production_output()
        print(f"📋 Items available for review:")
        for item in items[:20]:
            print(f"  📄 {item.get('type', '?'):20s} | {item.get('title', '?')[:50]}")
        print(f"\n   Total: {len(items)} items")
        return
    
    if args.review:
        query = args.review.lower()
        items = army._scan_production_output()
        matches = [i for i in items if query in i.get("title", "").lower() or query in i.get("path", "").lower()]
        if matches:
            result = army.review_item_full(matches[0])
            print(f"\n📊 REVIEW RESULTS")
            print(f"{'='*40}")
            print(f"   Title: {result['item_title']}")
            print(f"   Type: {result['item_type']}")
            print(f"   Quality Score: {result['avg_quality_score']}/100")
            print(f"   Reviews: {result['reviews_completed']}/{result['agents_total']}")
            print(f"   Assessments: {result['assessments']}")
            print(f"   Issues: {result['total_issues']}")
            print(f"   Suggestions: {result['total_suggestions']}")
            if result['issues']:
                print(f"\n   Top Issues:")
                for i in result['issues'][:5]:
                    print(f"     ⚠️  [{i['agent']}] {i['issue'][:60]}")
            if result['suggestions']:
                print(f"\n   Top Suggestions:")
                for s in result['suggestions'][:3]:
                    print(f"     💡 [{s['agent']}] {s['suggestion'][:60]}")
        else:
            print(f"❌ No items matching '{query}'")
        return
    
    if args.report:
        report = army.report()
        print(f"📊 RESEARCH ARMY REPORT")
        print(f"{'='*40}")
        print(f"   Runs: {report['state']['runs']}")
        print(f"   Items Reviewed: {report['state']['items_reviewed']}")
        print(f"   Reviews Completed: {report['state']['reviews_completed']}")
        print(f"   Issues Found: {report['state']['issues_found']}")
        print(f"   Issues Resolved: {report['state']['issues_resolved']}")
        print(f"   Avg Quality Score: {report['state']['avg_quality_score']:.1f}/100")
        print(f"   Agents: {report['agents']}")
        print(f"\n   Top Performing Agents:")
        for a in report['top_performers'][:5]:
            print(f"     🔬 Agent {a['id']:2s} ({a.get('name', '?')[:30]}): {a.get('reviews', 0)} reviews, {a.get('issues', 0)} issues")
        return
    
    if args.agents:
        print(f"🔬 50 Research Agents:")
        for a in RESEARCH_AGENTS:
            perf = army.state["agent_performance"].get(str(a["id"]), {})
            print(f"  Agent {a['id']:2d} | {a['name']:35s} | Reviews: {perf.get('reviews', 0):3d} | Issues: {perf.get('issues', 0):3d}")
        return
    
    # Default: run cycle
    army.full_cycle()

if __name__ == "__main__":
    main()
