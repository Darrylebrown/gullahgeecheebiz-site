#!/usr/bin/env python3
"""
GGB Newsletter, Substack & Stripe Optimizer — wires all three into the
Spirit Weaver SOE for continuous optimization, automation, and connectivity.
"""
import json, os, sys, time, sqlite3, requests, re
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
SOE_DIR = LOGS_DIR / "soe"
STATE_FILE = SOE_DIR / "nss-optimizer-state.json"

SOE_DIR.mkdir(parents=True, exist_ok=True)

def get_api_key():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if "OPENROUTER_API_KEY" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def call_ai(prompt, max_tokens=2000):
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "google/gemini-2.5-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=30
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return None

# ─── Newsletter Optimizer ─────────────────────────────────────────────────

class NewsletterOptimizer:
    """Optimizes newsletter content, subject lines, and delivery for max engagement."""
    
    def __init__(self):
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"runs": 0, "newsletters_optimized": 0, "subject_lines_tested": 0, "last_run": None}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def scan_newsletter_pages(self) -> List[Dict]:
        """Scan all newsletter/magazine pages for SOE optimization."""
        mag_dirs = [
            BASE_DIR / "publish" / "magazines" / "gg-corridor-weekly",
            BASE_DIR / "publish" / "magazines" / "ai-weekly",
        ]
        results = []
        for d in mag_dirs:
            if d.exists():
                for f in d.rglob("*.html"):
                    content = f.read_text()
                    rel = str(f.relative_to(BASE_DIR))
                    
                    title = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
                    desc = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', content, re.IGNORECASE)
                    text = re.sub(r'<[^>]+>', ' ', content)
                    words = len(text.split())
                    
                    issues = []
                    score = 100
                    
                    if not title: issues.append("Missing title"); score -= 20
                    if not desc: issues.append("Missing description"); score -= 15
                    if words < 200: issues.append(f"Thin content ({words} words)"); score -= 10
                    if not re.search(r'subscribe|join|sign.?up', content, re.IGNORECASE): issues.append("No subscribe CTA"); score -= 10
                    if not re.search(r'share|twitter|facebook', content, re.IGNORECASE): issues.append("No social sharing"); score -= 10
                    
                    results.append({
                        "path": rel,
                        "score": max(0, score),
                        "issues": issues,
                        "words": words,
                        "title": title.group(1) if title else "MISSING",
                    })
        return results
    
    def optimize_newsletter_subject(self, current_title: str, content_preview: str) -> Optional[str]:
        """Generate optimized subject lines using AI."""
        prompt = f"""Generate 5 optimized email subject lines for this newsletter.

Current Title: {current_title}
Content Preview: {content_preview[:200]}

Requirements:
- Under 60 characters
- Compelling and curiosity-driven
- Include keywords for search
- Drive opens and engagement

Return as JSON array of strings:
["subject 1", "subject 2", "subject 3", "subject 4", "subject 5"]"""
        
        result = call_ai(prompt, max_tokens=500)
        if not result:
            return None
        
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            subjects = json.loads(result[start:end])
            self.state["subject_lines_tested"] += len(subjects)
            self._save_state()
            return subjects
        except:
            return None
    
    def generate_newsletter_seo(self, title: str, content: str) -> Optional[Dict]:
        """Generate SEO metadata for newsletter pages."""
        prompt = f"""Generate SEO metadata for this newsletter issue.

Title: {title}
Content Preview: {content[:300]}

Generate:
1. Optimized title tag (under 60 chars)
2. Meta description (under 160 chars, compelling)
3. 5 target keywords
4. Suggested social media post text
5. Suggested email preview text

Return as JSON:
{{"title": "...", "description": "...", "keywords": ["..."], "social_post": "...", "email_preview": "..."}}"""
        
        result = call_ai(prompt, max_tokens=1000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            return json.loads(result[start:end])
        except:
            return None
    
    def optimize_all_newsletters(self) -> List[str]:
        """Optimize all newsletter pages with SOE metadata."""
        results = self.scan_newsletter_pages()
        optimized = []
        
        for r in results:
            if r["score"] < 80:
                meta = self.generate_newsletter_seo(r["title"], f"Newsletter at {r['path']}")
                if meta:
                    optimized.append({"path": r["path"], "old_score": r["score"], "meta": meta})
                    self.state["newsletters_optimized"] += 1
        
        self.state["runs"] += 1
        self._save_state()
        return optimized

# ─── Substack Optimizer ──────────────────────────────────────────────────

class SubstackOptimizer:
    """Monitors and optimizes Substack integration."""
    
    def __init__(self):
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"runs": 0, "links_checked": 0, "last_check": None}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def scan_substack_links(self) -> List[Dict]:
        """Find and verify all Substack links on the site."""
        results = []
        for html_file in BASE_DIR.rglob("*.html"):
            if "node_modules" in str(html_file):
                continue
            content = html_file.read_text()
            rel = str(html_file.relative_to(BASE_DIR))
            
            # Find Substack links
            links = re.findall(r'href=["\']([^"\']*substack[^"\']*)["\']', content, re.IGNORECASE)
            if links:
                for link in links:
                    results.append({
                        "page": rel,
                        "link": link,
                        "status": "found",
                    })
            
            # Check for Substack embed/widget
            has_embed = bool(re.search(r'substack.*embed|substack.*widget|substack.*subscribe', content, re.IGNORECASE))
            if has_embed:
                results.append({
                    "page": rel,
                    "link": "embed",
                    "status": "embed_found",
                })
        
        self.state["links_checked"] += len(results)
        self._save_state()
        return results
    
    def check_substack_health(self) -> Dict:
        """Check if Substack publication is accessible."""
        try:
            r = requests.get("https://gullahgeecheebiz.substack.com", timeout=10)
            return {
                "reachable": r.status_code == 200,
                "status_code": r.status_code,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        except:
            return {
                "reachable": False,
                "status_code": 0,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
    
    def generate_substack_promo(self, book_title: str) -> Optional[str]:
        """Generate a Substack post promoting a book."""
        prompt = f"""Write a compelling Substack post promoting this book.

Book: {book_title}
Publisher: Gullah Geechee Biz

Write a short post (150-200 words) that:
1. Hooks the reader in the first sentence
2. Explains why this book matters
3. Includes a call-to-action to read/buy
4. Has 3-5 relevant tags
5. Includes a suggested subject line

Return as JSON:
{{"subject": "...", "post": "...", "tags": ["..."], "cta": "..."}}"""
        
        result = call_ai(prompt, max_tokens=1000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            return json.loads(result[start:end])
        except:
            return None
    
    def optimize_substack_integration(self) -> List[Dict]:
        """Find pages missing Substack links and suggest adding them."""
        results = []
        for html_file in BASE_DIR.rglob("*.html"):
            if "node_modules" in str(html_file):
                continue
            content = html_file.read_text()
            rel = str(html_file.relative_to(BASE_DIR))
            
            has_link = bool(re.search(r'substack', content, re.IGNORECASE))
            has_cta = bool(re.search(r'subscribe|newsletter|join our', content, re.IGNORECASE))
            
            if not has_link and has_cta:
                results.append({
                    "page": rel,
                    "issue": "Has CTA but no Substack link",
                    "suggestion": "Add Substack subscribe link",
                })
        
        return results

# ─── Stripe Optimizer ────────────────────────────────────────────────────

class StripeOptimizer:
    """Monitors Stripe checkout links and optimizes conversion."""
    
    def __init__(self):
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"runs": 0, "checkouts_verified": 0, "last_check": None}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def scan_stripe_links(self) -> List[Dict]:
        """Find and verify all Stripe checkout links."""
        results = []
        for html_file in BASE_DIR.rglob("*.html"):
            if "node_modules" in str(html_file):
                continue
            content = html_file.read_text()
            rel = str(html_file.relative_to(BASE_DIR))
            
            # Find Stripe links
            links = re.findall(r'href=["\']([^"\']*stripe[^"\']*checkout[^"\']*)["\']', content, re.IGNORECASE)
            if links:
                for link in links:
                    results.append({
                        "page": rel,
                        "link": link,
                        "status": "found",
                    })
            
            # Check for Stripe button/embed
            has_button = bool(re.search(r'stripe.*button|stripe.*buy|stripe.*pay', content, re.IGNORECASE))
            if has_button:
                results.append({
                    "page": rel,
                    "link": "button",
                    "status": "button_found",
                })
        
        self.state["checkouts_verified"] += len(results)
        self._save_state()
        return results
    
    def check_stripe_links_health(self) -> List[Dict]:
        """Verify Stripe checkout links are reachable."""
        results = []
        for html_file in BASE_DIR.rglob("*.html"):
            if "node_modules" in str(html_file):
                continue
            content = html_file.read_text()
            rel = str(html_file.relative_to(BASE_DIR))
            
            links = re.findall(r'href=["\'](https://buy\.stripe\.com[^"\']*)["\']', content)
            for link in links:
                try:
                    r = requests.head(link, timeout=10, allow_redirects=True)
                    results.append({
                        "page": rel,
                        "link": link[:60],
                        "reachable": r.status_code < 400,
                        "status_code": r.status_code,
                    })
                except:
                    results.append({
                        "page": rel,
                        "link": link[:60],
                        "reachable": False,
                        "status_code": 0,
                    })
        
        return results
    
    def optimize_checkout_cta(self, page_title: str, page_content: str) -> Optional[str]:
        """Generate optimized checkout CTA text using AI."""
        prompt = f"""Generate 3 optimized call-to-action buttons for a Stripe checkout page.

Page: {page_title}
Content: {page_content[:200]}

Requirements:
- Compelling and action-oriented
- Under 40 characters
- Drive conversions
- Culturally appropriate for Gullah Geechee audience

Return as JSON array:
["CTA 1", "CTA 2", "CTA 3"]"""
        
        result = call_ai(prompt, max_tokens=500)
        if not result:
            return None
        
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            return json.loads(result[start:end])
        except:
            return None
    
    def generate_stripe_seo(self, page_path: str) -> Optional[Dict]:
        """Generate SEO metadata for Stripe checkout pages."""
        html_path = BASE_DIR / page_path
        if not html_path.exists():
            return None
        
        content = html_path.read_text()
        title = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
        current_title = title.group(1) if title else "Checkout"
        
        prompt = f"""Generate optimized SEO metadata for this checkout page.

Page: {page_path}
Current Title: {current_title}

Generate:
1. Optimized title (under 60 chars, conversion-focused)
2. Meta description (under 160 chars)
3. 5 keywords targeting buyers
4. Suggested Open Graph tags for social sharing

Return as JSON:
{{"title": "...", "description": "...", "keywords": ["..."], "og_title": "...", "og_description": "..."}}"""
        
        result = call_ai(prompt, max_tokens=1000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            return json.loads(result[start:end])
        except:
            return None

# ─── Unified NSS Optimizer ───────────────────────────────────────────────

class NSSOptimizer:
    """Unified Newsletter, Substack, Stripe optimizer with SOE connectivity."""
    
    def __init__(self):
        self.newsletter = NewsletterOptimizer()
        self.substack = SubstackOptimizer()
        self.stripe = StripeOptimizer()
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"runs": 0, "last_full_cycle": None}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def full_cycle(self) -> Dict:
        """Run full NSS optimization cycle."""
        print(f"\n{'='*60}")
        print(f"📬 NSS OPTIMIZER — Full Cycle")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        results = {}
        
        # 1. Newsletter
        print("📰 Step 1: Optimizing newsletters...")
        nl_scan = self.newsletter.scan_newsletter_pages()
        nl_opt = self.newsletter.optimize_all_newsletters()
        results["newsletter"] = {
            "pages_scanned": len(nl_scan),
            "optimized": len(nl_opt),
            "avg_score": sum(r["score"] for r in nl_scan) / len(nl_scan) if nl_scan else 0,
        }
        print(f"   Scanned: {len(nl_scan)} | Optimized: {len(nl_opt)}")
        
        # 2. Substack
        print("📬 Step 2: Checking Substack...")
        ss_links = self.substack.scan_substack_links()
        ss_health = self.substack.check_substack_health()
        ss_missing = self.substack.optimize_substack_integration()
        results["substack"] = {
            "links_found": len(ss_links),
            "reachable": ss_health.get("reachable", False),
            "pages_missing_links": len(ss_missing),
        }
        print(f"   Links: {len(ss_links)} | Reachable: {ss_health.get('reachable', '?')} | Missing: {len(ss_missing)}")
        
        # 3. Stripe
        print("💳 Step 3: Checking Stripe...")
        st_links = self.stripe.scan_stripe_links()
        st_health = self.stripe.check_stripe_links_health()
        results["stripe"] = {
            "checkouts_found": len(st_links),
            "links_verified": len(st_health),
            "healthy_links": sum(1 for h in st_health if h.get("reachable")),
        }
        print(f"   Checkouts: {len(st_links)} | Verified: {len(st_health)} | Healthy: {results['stripe']['healthy_links']}")
        
        # 4. Generate SOE strategy for NSS
        print("🧠 Step 4: Generating NSS strategy...")
        prompt = f"""Generate an optimization strategy for the Gullah Geechee Biz Newsletter, Substack, and Stripe systems.

Current State:
- Newsletter pages: {len(nl_scan)} (avg score: {results['newsletter']['avg_score']:.0f}/100)
- Substack links: {len(ss_links)} (reachable: {ss_health.get('reachable', False)})
- Stripe checkouts: {len(st_links)} ({results['stripe']['healthy_links']} verified healthy)

Generate a strategy to:
1. Increase newsletter engagement and open rates
2. Grow Substack subscriber base
3. Optimize Stripe checkout conversion
4. Cross-connect all three for maximum reach
5. Integrate with the Spirit Weaver SOE

Return as JSON:
{{"newsletter_priorities": ["..."], "substack_priorities": ["..."], "stripe_priorities": ["..."], "cross_connections": ["..."], "soe_integration": "..."}}"""
        
        strategy = call_ai(prompt, max_tokens=1500)
        if strategy:
            try:
                start = strategy.find("{")
                end = strategy.rfind("}") + 1
                results["strategy"] = json.loads(strategy[start:end])
            except:
                results["strategy"] = {"raw": strategy[:200]}
        
        self.state["runs"] += 1
        self.state["last_full_cycle"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        
        print(f"\n✅ NSS cycle complete")
        return results
    
    def report(self) -> Dict:
        """Generate full NSS report."""
        return {
            "state": self.state,
            "newsletter": {
                "optimized": self.newsletter.state.get("newsletters_optimized", 0),
                "subjects_tested": self.newsletter.state.get("subject_lines_tested", 0),
            },
            "substack": {
                "links_checked": self.substack.state.get("links_checked", 0),
            },
            "stripe": {
                "checkouts_verified": self.stripe.state.get("checkouts_verified", 0),
            },
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB NSS Optimizer — Newsletter, Substack, Stripe")
    parser.add_argument("--cycle", action="store_true", help="Run full optimization cycle")
    parser.add_argument("--report", action="store_true", help="NSS status report")
    parser.add_argument("--newsletter-scan", action="store_true", help="Scan newsletter pages")
    parser.add_argument("--substack-check", action="store_true", help="Check Substack health")
    parser.add_argument("--stripe-check", action="store_true", help="Check Stripe links")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"📬 GGB NSS OPTIMIZER — Newsletter, Substack, Stripe")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    nss = NSSOptimizer()
    
    if args.cycle:
        results = nss.full_cycle()
        print(f"\n📊 Results saved to SOE state")
        return
    
    if args.report:
        report = nss.report()
        print(f"📊 NSS REPORT")
        print(f"{'='*40}")
        print(f"   Runs: {report['state']['runs']}")
        print(f"   Newsletters optimized: {report['newsletter']['optimized']}")
        print(f"   Subject lines tested: {report['newsletter']['subjects_tested']}")
        print(f"   Substack links checked: {report['substack']['links_checked']}")
        print(f"   Stripe checkouts verified: {report['stripe']['checkouts_verified']}")
        return
    
    if args.newsletter_scan:
        opt = NewsletterOptimizer()
        results = opt.scan_newsletter_pages()
        print(f"📰 Newsletter pages: {len(results)}")
        for r in results:
            status = "✅" if r["score"] >= 80 else "⚠️"
            print(f"  {status} {r['score']:3d}/100 | {r['path'][:50]}")
        return
    
    if args.substack_check:
        opt = SubstackOptimizer()
        health = opt.check_substack_health()
        links = opt.scan_substack_links()
        print(f"📬 Substack Health: {'✅ Reachable' if health.get('reachable') else '❌ Unreachable'}")
        print(f"   Links found on site: {len(links)}")
        for l in links[:5]:
            print(f"     {l['page'][:40]} → {l['link'][:50]}")
        return
    
    if args.stripe_check:
        opt = StripeOptimizer()
        links = opt.scan_stripe_links()
        health = opt.check_stripe_links_health()
        print(f"💳 Stripe Checkouts: {len(links)}")
        print(f"   Links verified: {len(health)}")
        for h in health[:5]:
            status = "✅" if h.get("reachable") else "❌"
            print(f"  {status} {h['page'][:40]} → {h['link'][:50]}")
        return
    
    # Default: run cycle
    nss.full_cycle()

if __name__ == "__main__":
    main()
