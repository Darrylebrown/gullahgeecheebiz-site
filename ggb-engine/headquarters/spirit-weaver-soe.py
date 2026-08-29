#!/usr/bin/env python3
"""
GGB Autonomous SOE — Spirit Weaver. A self-sustaining Search Optimization
Engine that continuously analyzes, predicts, and optimizes every piece of
content for maximum discoverability across all platforms.
"""
import json, os, sys, time, sqlite3, requests, hashlib, re, random
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
SOE_DIR = LOGS_DIR / "soe"
STATE_FILE = SOE_DIR / "soe-state.json"
TRENDS_FILE = SOE_DIR / "trends.json"
STRATEGIES_FILE = SOE_DIR / "strategies.json"
PERFORMANCE_FILE = SOE_DIR / "performance.json"

SOE_DIR.mkdir(parents=True, exist_ok=True)

# ─── Spirit Weaver SOE ─────────────────────────────────────────────────────

class SpiritWeaverSOE:
    """Autonomous Search Optimization Engine — the Spirit Weaver."""
    
    def __init__(self):
        self.api_key = self._get_api_key()
        self.state = self._load_state()
        self.trends = self._load_trends()
        self.strategies = self._load_strategies()
        self.performance = self._load_performance()
    
    def _get_api_key(self) -> str:
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text().split("\n"):
                if "OPENROUTER_API_KEY" in line:
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        return ""
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"runs": 0, "last_scan": None, "optimizations": 0, "trends_predicted": 0}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _load_trends(self) -> List[Dict]:
        if TRENDS_FILE.exists():
            try:
                return json.loads(TRENDS_FILE.read_text())
            except:
                pass
        return []
    
    def _save_trends(self):
        TRENDS_FILE.write_text(json.dumps(self.trends[-100:], indent=2))
    
    def _load_strategies(self) -> List[Dict]:
        if STRATEGIES_FILE.exists():
            try:
                return json.loads(STRATEGIES_FILE.read_text())
            except:
                pass
        return []
    
    def _save_strategies(self):
        STRATEGIES_FILE.write_text(json.dumps(self.strategies[-50:], indent=2))
    
    def _load_performance(self) -> Dict:
        if PERFORMANCE_FILE.exists():
            try:
                return json.loads(PERFORMANCE_FILE.read_text())
            except:
                pass
        return {"pages_optimized": 0, "avg_score": 0, "top_keywords": [], "platform_scores": {}}
    
    def _save_performance(self):
        PERFORMANCE_FILE.write_text(json.dumps(self.performance, indent=2))
    
    def _call_ai(self, prompt: str, max_tokens: int = 2000) -> Optional[str]:
        if not self.api_key:
            return None
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": "google/gemini-2.5-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
                timeout=30
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except:
            pass
        return None
    
    # ─── TREND PREDICTION ─────────────────────────────────────────────────
    
    def predict_trends(self) -> List[Dict]:
        """Use AI to predict trending topics in Gullah Geechee culture and publishing."""
        prompt = """Predict the top 5 trending topics in Gullah Geechee culture, African American heritage, and self-publishing for the next 30 days.

For each trend, provide:
- Trend name
- Why it's trending
- Estimated search volume (low/medium/high)
- How Gullah Geechee Biz can capitalize on it
- Suggested content type (article, video, book, social post)

Return as JSON array:
[{"name": "...", "reason": "...", "volume": "...", "opportunity": "...", "content_type": "..."}]"""
        
        result = self._call_ai(prompt, max_tokens=1500)
        if not result:
            return []
        
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            if start >= 0 and end > start:
                trends = json.loads(result[start:end])
                for t in trends:
                    t["predicted_at"] = datetime.now(timezone.utc).isoformat()
                self.trends.extend(trends)
                self.state["trends_predicted"] += len(trends)
                self._save_trends()
                self._save_state()
                return trends
        except:
            pass
        return []
    
    # ─── SEO AUDIT ────────────────────────────────────────────────────────
    
    def audit_page(self, html_path: Path) -> Dict:
        """Audit a single HTML page for SEO issues."""
        content = html_path.read_text()
        rel_path = str(html_path.relative_to(BASE_DIR))
        
        issues = []
        score = 100
        
        # Check title
        title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
        if not title_match:
            issues.append("Missing title tag")
            score -= 20
        else:
            title = title_match.group(1)
            if len(title) < 10:
                issues.append(f"Title too short ({len(title)} chars)")
                score -= 10
            elif len(title) > 70:
                issues.append(f"Title too long ({len(title)} chars)")
                score -= 5
        
        # Check meta description
        desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', content, re.IGNORECASE)
        if not desc_match:
            issues.append("Missing meta description")
            score -= 15
        else:
            desc = desc_match.group(1)
            if len(desc) < 50:
                issues.append(f"Description too short ({len(desc)} chars)")
                score -= 5
            elif len(desc) > 160:
                issues.append(f"Description too long ({len(desc)} chars)")
                score -= 5
        
        # Check for h1
        if not re.search(r'<h1[^>]*>', content, re.IGNORECASE):
            issues.append("Missing H1 tag")
            score -= 10
        
        # Check for images without alt text
        imgs_no_alt = len(re.findall(r'<img[^>]+(?:alt=["\'\s])[^>]*>', content, re.IGNORECASE))
        total_imgs = len(re.findall(r'<img[^>]*>', content, re.IGNORECASE))
        if total_imgs > 0 and imgs_no_alt < total_imgs:
            missing_alt = total_imgs - imgs_no_alt
            issues.append(f"{missing_alt} images missing alt text")
            score -= 5 * missing_alt
        
        # Check for canonical
        if not re.search(r'<link\s+rel=["\']canonical["\']', content, re.IGNORECASE):
            issues.append("Missing canonical tag")
            score -= 5
        
        # Check for Open Graph
        if not re.search(r'<meta\s+property=["\']og:', content, re.IGNORECASE):
            issues.append("Missing Open Graph tags")
            score -= 10
        
        # Check word count
        text = re.sub(r'<[^>]+>', '', content)
        words = len(text.split())
        if words < 100:
            issues.append(f"Very low word count ({words} words)")
            score -= 10
        
        score = max(0, score)
        
        return {
            "path": rel_path,
            "score": score,
            "issues": issues,
            "title": title_match.group(1) if title_match else "MISSING",
            "word_count": words,
            "audited_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def scan_all_pages(self) -> List[Dict]:
        """Scan all HTML pages on the site for SEO issues."""
        html_files = sorted(BASE_DIR.rglob("*.html"))
        html_files = [f for f in html_files if "node_modules" not in str(f)]
        
        results = []
        for f in html_files:
            result = self.audit_page(f)
            results.append(result)
        
        # Update performance
        scores = [r["score"] for r in results]
        self.performance["pages_optimized"] = len(results)
        self.performance["avg_score"] = sum(scores) / len(scores) if scores else 0
        self.performance["last_scan"] = datetime.now(timezone.utc).isoformat()
        self._save_performance()
        
        return results
    
    # ─── DEEP OPTIMIZATION — Appeal & Connectivity ──────────────────────
    
    def deep_optimize_page(self, html_path: Path) -> Optional[Dict]:
        """Deep optimization: improve appeal, connectivity, and engagement."""
        content = html_path.read_text()
        rel_path = str(html_path.relative_to(BASE_DIR))
        
        # Get all page links for connectivity analysis
        all_links = re.findall(r'href=["\']([^"\']+)["\']', content)
        internal_links = [l for l in all_links if not l.startswith("http") and not l.startswith("#") and not l.startswith("mailto:")]
        external_links = [l for l in all_links if l.startswith("http")]
        
        # Get page text for content analysis
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'\s+', ' ', text).strip()
        word_count = len(text.split())
        
        # Check for CTAs
        has_cta = bool(re.search(r'buy|shop|subscribe|join|sign up|get started|learn more|donate|support', content, re.IGNORECASE))
        
        # Check for social sharing
        has_social = bool(re.search(r'twitter|facebook|instagram|pinterest|share|social', content, re.IGNORECASE))
        
        # Check for related content links
        has_related = bool(re.search(r'related|more|also|recommended|you might', content, re.IGNORECASE))
        
        # Check for images
        images = re.findall(r'<img[^>]*>', content)
        
        # Check for structured data
        has_structured = bool(re.search(r'application/ld\+json|itemscope|itemtype', content))
        
        issues = []
        score = 100
        
        if word_count < 200:
            issues.append(f"Thin content ({word_count} words)")
            score -= 15
        elif word_count < 500:
            issues.append(f"Light content ({word_count} words)")
            score -= 5
        
        if len(internal_links) < 3:
            issues.append(f"Low internal connectivity ({len(internal_links)} internal links)")
            score -= 15
        elif len(internal_links) < 6:
            issues.append(f"Could use more internal links ({len(internal_links)})")
            score -= 5
        
        if not has_cta:
            issues.append("No call-to-action found")
            score -= 10
        
        if not has_social:
            issues.append("No social sharing elements")
            score -= 10
        
        if not has_related:
            issues.append("No related content links")
            score -= 10
        
        if len(images) == 0:
            issues.append("No images on page")
            score -= 10
        
        if not has_structured:
            issues.append("No structured data (schema.org)")
            score -= 5
        
        score = max(0, score)
        
        return {
            "path": rel_path,
            "score": score,
            "issues": issues,
            "word_count": word_count,
            "internal_links": len(internal_links),
            "external_links": len(external_links),
            "has_cta": has_cta,
            "has_social": has_social,
            "has_related": has_related,
            "image_count": len(images),
            "has_structured": has_structured,
        }
    
    def deep_scan_all(self) -> List[Dict]:
        """Deep scan all pages for appeal and connectivity issues."""
        html_files = sorted(BASE_DIR.rglob("*.html"))
        html_files = [f for f in html_files if "node_modules" not in str(f)]
        
        results = []
        for f in html_files:
            result = self.deep_optimize_page(f)
            results.append(result)
        
        scores = [r["score"] for r in results]
        self.performance["deep_scan"] = {
            "pages": len(results),
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "last_scan": datetime.now(timezone.utc).isoformat(),
        }
        self._save_performance()
        
        return results
    
    def ai_enhance_page(self, html_path: Path) -> Optional[str]:
        """Use AI to enhance a page's appeal and connectivity."""
        content = html_path.read_text()
        rel_path = str(html_path.relative_to(BASE_DIR))
        
        # Get current page info
        title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
        title = title_match.group(1) if title_match else "Untitled"
        
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'\s+', ' ', text).strip()[:500]
        
        # Get all internal pages for connectivity suggestions
        all_pages = sorted(BASE_DIR.rglob("*.html"))
        all_pages = [f for f in all_pages if "node_modules" not in str(f)]
        page_titles = []
        for p in all_pages[:20]:
            p_content = p.read_text()
            p_title = re.search(r'<title>(.*?)</title>', p_content, re.IGNORECASE)
            if p_title:
                p_rel = str(p.relative_to(BASE_DIR))
                page_titles.append(f"{p_rel}: {p_title.group(1)}")
        
        prompt = f"""Enhance this webpage for maximum appeal and connectivity.

Page: {rel_path}
Current Title: {title}
Content Preview: {text[:300]}

Available pages on this site (for internal linking):
{chr(10).join(page_titles[:10])}

Generate enhancements:
1. An improved, more compelling title (under 60 chars)
2. A more engaging meta description (under 160 chars)
3. 3-5 suggested internal links to other pages (use exact paths from the list)
4. A call-to-action suggestion
5. Suggested social sharing text
6. Suggested related content section HTML

Return as JSON:
{{"title": "...", "description": "...", "internal_links": [{{"path": "...", "anchor": "..."}}], "cta": "...", "social_text": "...", "related_html": "..."}}"""
        
        result = self._call_ai(prompt, max_tokens=2000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                enhancements = json.loads(result[start:end])
                
                # Apply title
                new_title = enhancements.get("title", title)
                content = re.sub(r'<title>.*?</title>', f'<title>{new_title}</title>', content, count=1)
                
                # Apply description
                new_desc = enhancements.get("description", "")
                if new_desc:
                    desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'].*?["\']', content, re.IGNORECASE)
                    if desc_match:
                        content = re.sub(
                            r'<meta\s+name=["\']description["\']\s+content=["\'].*?["\']',
                            f'<meta name="description" content="{new_desc}"',
                            content, count=1
                        )
                    else:
                        content = content.replace('</head>', f'  <meta name="description" content="{new_desc}">\n</head>', 1)
                
                # Add internal links before closing body
                links = enhancements.get("internal_links", [])
                if links and '</body>' in content:
                    links_html = '\n  <!-- Related Content -->\n  <div class="related-content">\n    <h3>Explore More</h3>\n    <ul>\n'
                    for link in links[:5]:
                        path = link.get("path", "")
                        anchor = link.get("anchor", path)
                        links_html += f'      <li><a href="/{path}">{anchor}</a></li>\n'
                    links_html += '    </ul>\n  </div>\n'
                    content = content.replace('</body>', f'{links_html}</body>', 1)
                
                # Add social sharing if not present
                if not re.search(r'social|share', content, re.IGNORECASE):
                    social_text = enhancements.get("social_text", f"Check out {new_title}")
                    social_html = f'''
  <!-- Social Sharing -->
  <div class="social-share">
    <p>Share this: 
      <a href="https://twitter.com/intent/tweet?text={social_text.replace(' ', '%20')}" target="_blank">Twitter</a> |
      <a href="https://www.facebook.com/sharer/sharer.php?u=https://gullahgeecheebiz.com/{rel_path.replace('/index.html', '').replace('.html', '')}" target="_blank">Facebook</a> |
      <a href="https://pinterest.com/pin/create/button/?url=https://gullahgeecheebiz.com/{rel_path.replace('/index.html', '').replace('.html', '')}&description={social_text.replace(' ', '%20')}" target="_blank">Pinterest</a>
    </p>
  </div>
'''
                    content = content.replace('</body>', f'{social_html}</body>', 1)
                
                html_path.write_text(content)
                self.state["optimizations"] += 1
                self._save_state()
                
                return json.dumps({
                    "path": rel_path,
                    "old_title": title,
                    "new_title": new_title,
                    "links_added": len(links),
                    "social_added": not re.search(r'social|share', content, re.IGNORECASE) == False,
                })
        except:
            pass
        return None
    
    def deep_optimize_all(self, limit: int = 159) -> List[str]:
        """Deep optimize all pages for max appeal and connectivity."""
        results = self.deep_scan_all()
        sorted_results = sorted(results, key=lambda r: r["score"])
        
        optimized = []
        for r in sorted_results[:limit]:
            html_path = BASE_DIR / r["path"]
            result = self.ai_enhance_page(html_path)
            if result:
                optimized.append(result)
        
        return optimized
    
    # ─── STRATEGY GENERATION ─────────────────────────────────────────────
    
    def generate_strategy(self) -> Dict:
        """Generate an SEO strategy based on current performance and trends."""
        trends = self.predict_trends()
        
        prompt = f"""Generate an SEO strategy for Gullah Geechee Biz based on:

Current Performance:
- Pages: {self.performance.get('pages_optimized', 0)}
- Avg SEO Score: {self.performance.get('avg_score', 0):.0f}/100
- Top Keywords: {self.performance.get('top_keywords', [])[:5]}

Predicted Trends:
{json.dumps(trends[:3], indent=2)}

Generate a strategy with:
1. Top 3 SEO priorities for the next 7 days
2. Specific keywords to target
3. Content types to create
4. Platforms to focus on
5. How to measure success

Return as JSON:
{{"priorities": ["...", "...", "..."], "keywords": ["...", "..."], "content_types": ["..."], "platforms": ["..."], "metrics": ["..."], "rationale": "..."}}"""
        
        result = self._call_ai(prompt, max_tokens=1500)
        if not result:
            return {"error": "No strategy generated"}
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                strategy = json.loads(result[start:end])
                strategy["generated_at"] = datetime.now(timezone.utc).isoformat()
                self.strategies.append(strategy)
                self._save_strategies()
                return strategy
        except:
            pass
        
        return {"error": "Failed to parse strategy"}
    
    # ─── REPORT ──────────────────────────────────────────────────────────
    
    def report(self) -> Dict:
        """Generate a full SOE report."""
        return {
            "state": self.state,
            "performance": self.performance,
            "active_trends": len(self.trends),
            "active_strategies": len(self.strategies),
            "latest_strategy": self.strategies[-1] if self.strategies else None,
            "latest_trends": self.trends[-5:] if self.trends else [],
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Autonomous SOE — Spirit Weaver")
    parser.add_argument("--scan", action="store_true", help="Scan all pages for SEO issues")
    parser.add_argument("--optimize", type=int, nargs="?", const=10, help="Optimize low-scoring pages")
    parser.add_argument("--trends", action="store_true", help="Predict trending topics")
    parser.add_argument("--strategy", action="store_true", help="Generate SEO strategy")
    parser.add_argument("--report", action="store_true", help="Full SOE report")
    parser.add_argument("--full-cycle", action="store_true", help="Run full SOE cycle")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"🔍 GGB AUTONOMOUS SOE — SPIRIT WEAVER")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    soe = SpiritWeaverSOE()
    
    if args.scan:
        print("🔍 Scanning all pages...")
        results = soe.scan_all_pages()
        low = [r for r in results if r["score"] < 80]
        print(f"   Pages scanned: {len(results)}")
        print(f"   Avg score: {soe.performance['avg_score']:.0f}/100")
        print(f"   Pages needing optimization: {len(low)}")
        if low:
            print(f"\n   Lowest scoring pages:")
            for r in sorted(low, key=lambda x: x["score"])[:5]:
                print(f"     {r['score']:3d}/100 | {r['path'][:60]}")
                for issue in r['issues'][:3]:
                    print(f"           ⚠️  {issue}")
        return
    
    if args.optimize:
        n = args.optimize
        print(f"🔧 Optimizing top {n} low-scoring pages...")
        results = soe.optimize_all_pages(limit=n)
        print(f"   Optimized: {len(results)} pages")
        for r in results:
            data = json.loads(r)
            print(f"     ✅ {data['path'][:50]}")
            print(f"        '{data['old_title'][:40]}' → '{data['new_title'][:40]}'")
        return
    
    if args.trends:
        print("🔮 Predicting trends...")
        trends = soe.predict_trends()
        print(f"   Predicted {len(trends)} trends:")
        for t in trends:
            print(f"     📈 {t['name']:40s} | {t['volume']:6s} | {t['content_type']}")
        return
    
    if args.strategy:
        print("🧠 Generating SEO strategy...")
        strategy = soe.generate_strategy()
        print(f"\n   Priorities:")
        for p in strategy.get("priorities", []):
            print(f"     🎯 {p}")
        print(f"\n   Keywords: {', '.join(strategy.get('keywords', [])[:5])}")
        print(f"\n   Rationale: {strategy.get('rationale', '')[:200]}")
        return
    
    if args.report:
        report = soe.report()
        print(f"📊 SOE REPORT")
        print(f"{'='*40}")
        print(f"   Runs: {report['state']['runs']}")
        print(f"   Optimizations: {report['state']['optimizations']}")
        print(f"   Trends predicted: {report['state']['trends_predicted']}")
        print(f"   Pages optimized: {report['performance']['pages_optimized']}")
        print(f"   Avg SEO score: {report['performance']['avg_score']:.0f}/100")
        print(f"   Active trends: {report['active_trends']}")
        print(f"   Active strategies: {report['active_strategies']}")
        if report['latest_trends']:
            print(f"\n   Latest trends:")
            for t in report['latest_trends'][:3]:
                print(f"     📈 {t.get('name', 'Unknown')}")
        return
    
    if args.full_cycle:
        print("🔄 Full SOE cycle: Scan → Optimize → Predict → Strategize\n")
        
        # Step 1: Scan
        print("🔍 Step 1: Scanning pages...")
        results = soe.scan_all_pages()
        low = [r for r in results if r["score"] < 80]
        print(f"   {len(results)} pages, {len(low)} need optimization\n")
        
        # Step 2: Optimize
        print("🔧 Step 2: Optimizing low-scoring pages...")
        optimized = soe.deep_optimize_all(limit=10)
        print(f"   Optimized {len(optimized)} pages\n")
        
        # Step 3: Predict trends
        print("🔮 Step 3: Predicting trends...")
        trends = soe.predict_trends()
        print(f"   Predicted {len(trends)} trends\n")
        
        # Step 4: Generate strategy
        print("🧠 Step 4: Generating strategy...")
        strategy = soe.generate_strategy()
        print(f"   Strategy generated\n")
        
        soe.state["runs"] += 1
        soe._save_state()
        
        print(f"{'='*60}")
        print(f"✅ SOE CYCLE COMPLETE")
        print(f"{'='*60}")
        print(f"   Pages scanned: {len(results)}")
        print(f"   Pages optimized: {len(optimized)}")
        print(f"   Trends predicted: {len(trends)}")
        print(f"   Strategy: {strategy.get('rationale', '')[:100]}...")
        return
    
    # Default: report
    report = soe.report()
    print(f"📊 SOE REPORT")
    print(f"{'='*40}")
    print(f"   Runs: {report['state']['runs']}")
    print(f"   Optimizations: {report['state']['optimizations']}")
    print(f"   Avg SEO score: {report['performance']['avg_score']:.0f}/100")

if __name__ == "__main__":
    main()
