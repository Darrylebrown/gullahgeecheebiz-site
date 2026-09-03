#!/usr/bin/env python3
"""
GGB Sales Activation System — designed by the AI Think Tank.
Picks star products, builds sales funnels, optimizes pricing,
recovers abandoned carts, and targets B2B sales. Turns the
running system into a revenue-generating machine.
"""
import json, os, sys, time, sqlite3, requests, hashlib, random
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
SALES_DIR = LOGS_DIR / "sales-activation"
STATE_FILE = SALES_DIR / "sales-state.json"
STAR_FILE = SALES_DIR / "star-products.json"
FUNNEL_FILE = SALES_DIR / "funnel.json"
B2B_FILE = SALES_DIR / "b2b-targets.json"

SALES_DIR.mkdir(parents=True, exist_ok=True)

def get_api_key():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if "OPENROUTER_API_KEY" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def call_ai(prompt, model="ggb-free-auto", max_tokens=2000):
    """Route through OmniRoute gateway with auto-fallback.

    Validates the response is complete, parseable JSON (the system's prompts
    all demand JSON). Retries up to 3 times to absorb gateway 502s, truncated
    local-model output, and upstream flakes before giving up.
    """
    max_tokens = min(max_tokens, 4000)
    last = None
    for attempt in range(3):
        result = omniroute_shim.call_ai(prompt=prompt, model=model, max_tokens=max_tokens)
        if result:
            start, end = result.find("["), result.rfind("]") + 1
            if start >= 0 and end > start:
                try:
                    json.loads(result[start:end])
                    return result
                except Exception:
                    pass
            else:
                lb, rb = result.find("{"), result.rfind("}") + 1
                if lb >= 0 and rb > lb:
                    try:
                        json.loads(result[lb:rb])
                        return result
                    except Exception:
                        pass
        last = result
        if attempt < 2:
            time.sleep(2)
    return last

# ─── 1. STAR PRODUCT SELECTOR ────────────────────────────────────────────

class StarProductSelector:
    """Picks the best 10-15 products to focus all sales efforts on."""
    
    def __init__(self):
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text())
                if isinstance(data, dict):
                    # STATE_FILE is shared with SalesActivator (activations schema) —
                    # merge defaults so missing keys never KeyError.
                    return {
                        "runs": data.get("runs", 0),
                        "star_products": data.get("star_products", []),
                        "last_selection": data.get("last_selection", None),
                    }
            except:
                pass
        return {"runs": 0, "star_products": [], "last_selection": None}
    
    def _save_state(self):
        # Preserve keys owned by other components sharing this file (e.g. SalesActivator.activations)
        try:
            existing = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
        except:
            existing = {}
        existing.update(self.state)
        STATE_FILE.write_text(json.dumps(existing, indent=2))
    
    def _get_all_books(self) -> List[Dict]:
        try:
            conn = sqlite3.connect(str(PUB_DB))
            rows = conn.execute(
                "SELECT manifest_id, data FROM manifests WHERE state = 'published' ORDER BY RANDOM()"
            ).fetchall()
            conn.close()
            books = []
            for mid, data_json in rows:
                try:
                    data = json.loads(data_json) if data_json else {}
                except:
                    data = {}
                title = data.get("title", mid)
                if isinstance(title, dict):
                    title = title.get("canonical", str(title))
                books.append({"id": mid[:20], "title": str(title)[:80]})
            return books
        except:
            return []
    
    def select_star_products(self, count: int = 15) -> List[Dict]:
        """Use AI to select the best products to focus on."""
        books = self._get_all_books()
        if not books:
            return []
        
        sample = random.sample(books, min(50, len(books)))
        titles = "\n".join([f"- {b['title']}" for b in sample])
        
        prompt = f"""You are a publishing strategist for Gullah Geechee Biz. Select the TOP {count} books to focus ALL sales efforts on.

Available books (sample of 50 from {len(books)} total):
{titles}

Selection criteria:
1. Most commercially appealing title and topic
2. Best cultural storytelling potential
3. Widest audience appeal
4. Best cover/marketing potential
5. Strongest SEO potential

Return as JSON array of objects with "title" and "reason":
[{{"title": "...", "reason": "..."}}]"""
        
        result = call_ai(prompt, max_tokens=4000)
        if not result:
            return []
        
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            stars = json.loads(result[start:end])
            
            # Match back to full book data (fuzzy token-overlap: AI may reformat titles)
            def _tokens(t: str) -> set:
                return {w for w in t.lower().replace("-", " ").replace("—", " ").split() if len(w) > 2}
            
            matched = []
            for s in stars:
                st = _tokens(s.get("title", ""))
                best, best_score = None, 0
                for b in books:
                    score = len(st & _tokens(b["title"]))
                    if score > best_score:
                        best, best_score = b, score
                if best_score >= 3:
                    matched.append({**best, "reason": s.get("reason", ""), "selected_at": datetime.now(timezone.utc).isoformat()})
            
            self.state["star_products"] = matched[:count]
            self.state["last_selection"] = datetime.now(timezone.utc).isoformat()
            self.state["runs"] += 1
            self._save_state()
            
            STAR_FILE.write_text(json.dumps(matched[:count], indent=2))
            
            return matched[:count]
        except:
            return []

# ─── 2. SALES FUNNEL BUILDER ─────────────────────────────────────────────

class SalesFunnelBuilder:
    """Builds a complete sales funnel: lead magnet → landing page → email sequence."""
    
    def __init__(self):
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if FUNNEL_FILE.exists():
            try:
                return json.loads(FUNNEL_FILE.read_text())
            except:
                pass
        return {"funnels": [], "last_built": None}
    
    def _save_state(self):
        FUNNEL_FILE.write_text(json.dumps(self.state, indent=2))
    
    def build_lead_magnet(self, star_products: List[Dict]) -> Optional[Dict]:
        """Create a lead magnet from star products."""
        titles = "\n".join([f"- {p.get('title', '?')}" for p in star_products[:5]])
        
        prompt = f"""Design a high-value FREE lead magnet for Gullah Geechee Biz to capture email subscribers.

Star products available:
{titles}

The lead magnet should be:
1. A free PDF download (recipe collection, cultural guide, proverb book, etc.)
2. High perceived value (feels like $20+)
3. Directly related to the star products
4. Shareable on social media

Provide:
- Title
- Description (what's inside)
- Format (PDF, checklist, guide, etc.)
- How it connects to the paid products
- Suggested landing page headline
- Suggested email subject line for delivery

Return as JSON:
{{"title": "...", "description": "...", "format": "...", "connection": "...", "headline": "...", "email_subject": "..."}}"""
        
        result = call_ai(prompt, max_tokens=1500)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            magnet = json.loads(result[start:end])
            magnet["created_at"] = datetime.now(timezone.utc).isoformat()
            self.state["funnels"].append({"type": "lead_magnet", "data": magnet})
            self._save_state()
            return magnet
        except:
            return None
    
    def build_email_sequence(self, star_products: List[Dict]) -> Optional[Dict]:
        """Create a 5-day email nurture sequence."""
        titles = "\n".join([f"- {p.get('title', '?')}" for p in star_products[:5]])
        
        prompt = f"""Create a 5-day automated email sequence for Gullah Geechee Biz to convert subscribers into customers.

Star products to promote:
{titles}

Day 1: Welcome + deliver lead magnet
Day 2: Share the story behind Gullah Geechee Biz
Day 3: Feature one star product with a special offer
Day 4: Share customer testimonials / cultural impact
Day 5: Final call-to-action + bundle offer

For each day, provide:
- Subject line
- Email body (2-3 sentences)
- Call-to-action
- Product/offer to feature

Return as JSON array:
[{{"day": 1, "subject": "...", "body": "...", "cta": "...", "offer": "..."}}]"""
        
        result = call_ai(prompt, max_tokens=2000)
        if not result:
            return None
        
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            sequence = json.loads(result[start:end])
            self.state["funnels"].append({"type": "email_sequence", "data": sequence})
            self._save_state()
            return {"sequence": sequence, "created_at": datetime.now(timezone.utc).isoformat()}
        except:
            return None
    
    def build_landing_page(self, star_products: List[Dict], lead_magnet: Dict) -> Optional[str]:
        """Generate HTML for a high-converting landing page."""
        top = star_products[:3]
        products_html = "\n".join([f'<div class="product-card"><h3>{p.get("title", "?")[:40]}</h3><p class="price">$3.99</p><a href="#" class="btn">Buy Now</a></div>' for p in top])
        
        prompt = f"""Generate a complete HTML landing page for Gullah Geechee Biz.

Lead Magnet: {lead_magnet.get('title', 'Free Guide')}
Headline: {lead_magnet.get('headline', 'Discover Gullah Geechee Culture')}
Star Products: {[p.get('title', '?')[:40] for p in top]}

The page must:
1. Have a hero section with the lead magnet offer
2. Email capture form (name + email)
3. Featured products section
4. Social proof / testimonials section
5. Mobile responsive
6. Gullah Geechee cultural aesthetic (warm colors, nature imagery)
7. Fast loading (no heavy frameworks)

Return ONLY the complete HTML code. Include inline CSS."""
        
        result = call_ai(prompt, max_tokens=3000)
        if result:
            path = BASE_DIR / "landing" / "index.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            # Extract HTML from code block if present
            if "```html" in result:
                start = result.find("```html") + 7
                end = result.find("```", start)
                result = result[start:end].strip()
            path.write_text(result)
            self.state["funnels"].append({"type": "landing_page", "path": str(path)})
            self._save_state()
            return str(path)
        return None

# ─── 3. PRICING OPTIMIZER ────────────────────────────────────────────────

class PricingOptimizer:
    """Optimizes pricing tiers and A/B tests."""
    
    def __init__(self):
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        path = SALES_DIR / "pricing-state.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except:
                pass
        return {"tiers": [], "tests": [], "last_optimized": None}
    
    def _save_state(self):
        path = SALES_DIR / "pricing-state.json"
        path.write_text(json.dumps(self.state, indent=2))
    
    def generate_pricing_tiers(self) -> Optional[Dict]:
        """Generate optimized pricing tiers."""
        prompt = """Design 5 pricing tiers for Gullah Geechee Biz books and products.

Context:
- 1,817 books in catalog
- Distribution on Google Play, Shopify, Etsy, Amazon
- Target audience: Gullah Geechee community, cultural enthusiasts, educators, HBCUs
- Current price: $3.99 per book

Design tiers:
1. Single Book (individual purchase)
2. Bundle (3-5 books)
3. Collection (10-20 books)
4. Library Pack (50+ books)
5. Institutional License (unlimited access)

For each tier, provide:
- Price
- What's included
- Target customer
- Why this price works

Return as JSON:
[{"tier": "Single Book", "price": 0, "includes": "...", "target": "...", "rationale": "..."}]"""
        
        result = call_ai(prompt, max_tokens=1500)
        if not result:
            return None
        
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            tiers = json.loads(result[start:end])
            self.state["tiers"] = tiers
            self.state["last_optimized"] = datetime.now(timezone.utc).isoformat()
            self._save_state()
            return tiers
        except:
            return None

# ─── 4. ABANDONED CART RECOVERY ──────────────────────────────────────────

class CartRecoveryBuilder:
    """Builds abandoned cart recovery system."""
    
    def __init__(self):
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        path = SALES_DIR / "cart-recovery-state.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except:
                pass
        return {"sequences": [], "last_built": None}
    
    def _save_state(self):
        path = SALES_DIR / "cart-recovery-state.json"
        path.write_text(json.dumps(self.state, indent=2))
    
    def build_recovery_sequence(self) -> Optional[Dict]:
        """Create abandoned cart email sequence."""
        prompt = """Create a 3-email abandoned cart recovery sequence for Gullah Geechee Biz.

The sequence should:
1. Email 1 (1 hour after abandonment): Friendly reminder + social proof
2. Email 2 (24 hours later): Scarcity + limited-time offer
3. Email 3 (72 hours later): Final chance + bonus offer

For each email, provide:
- Subject line
- Body (2-3 sentences)
- Offer/discount (if any)
- Call-to-action

Return as JSON:
[{"email": 1, "timing": "1 hour", "subject": "...", "body": "...", "offer": "...", "cta": "..."}]"""
        
        result = call_ai(prompt, max_tokens=1500)
        if not result:
            return None
        
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            sequence = json.loads(result[start:end])
            self.state["sequences"] = sequence
            self.state["last_built"] = datetime.now(timezone.utc).isoformat()
            self._save_state()
            return {"sequence": sequence}
        except:
            return None

# ─── 5. B2B SALES PIPELINE ──────────────────────────────────────────────

class B2BSalesPipeline:
    """Targets HBCUs, schools, libraries, and cultural institutions."""
    
    def __init__(self):
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if B2B_FILE.exists():
            try:
                return json.loads(B2B_FILE.read_text())
            except:
                pass
        return {"targets": [], "outreach": [], "last_run": None}
    
    def _save_state(self):
        B2B_FILE.write_text(json.dumps(self.state, indent=2))
    
    def generate_b2b_targets(self) -> Optional[List[Dict]]:
        """Generate list of B2B targets using AI knowledge."""
        prompt = """Generate a list of 20 B2B sales targets for Gullah Geechee Biz books.

Target types:
- HBCUs (Historically Black Colleges and Universities)
- Southern K-12 school districts
- Public libraries in the Gullah Geechee Corridor (SC, GA, FL, NC)
- Cultural museums and heritage centers
- African American studies departments
- Church and community organizations

For each target, provide:
- Name
- Type (HBCU, school, library, museum, church, etc.)
- Location (city, state)
- Why they would buy Gullah Geechee books
- Suggested contact approach
- Estimated potential value ($)

Return as JSON array:
[{"name": "...", "type": "...", "location": "...", "relevance": "...", "approach": "...", "potential_value": 0}]"""
        
        result = call_ai(prompt, max_tokens=4000)
        if not result:
            return []
        
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            targets = json.loads(result[start:end])
            self.state["targets"] = targets
            self.state["last_run"] = datetime.now(timezone.utc).isoformat()
            self._save_state()
            return targets
        except:
            return []
    
    def generate_outreach_email(self, target: Dict) -> Optional[str]:
        """Generate a personalized outreach email for a B2B target."""
        prompt = f"""Write a professional outreach email to sell Gullah Geechee Biz books to this organization.

Organization: {target.get('name', 'Unknown')}
Type: {target.get('type', 'Unknown')}
Location: {target.get('location', 'Unknown')}
Relevance: {target.get('relevance', 'Cultural education')}

The email should:
1. Be personalized to this specific organization
2. Explain the value of Gullah Geechee cultural education
3. Offer bulk pricing and institutional licensing
4. Include a clear call-to-action
5. Be warm but professional

Write the complete email (subject line + body)."""
        
        result = call_ai(prompt, max_tokens=1000)
        if result:
            self.state["outreach"].append({"target": target.get("name"), "email": result[:200], "sent_at": datetime.now(timezone.utc).isoformat()})
            self._save_state()
        return result

# ─── MASTER ACTIVATOR ────────────────────────────────────────────────────

class SalesActivator:
    """Runs all 5 sales activation systems."""
    
    def __init__(self):
        self.star_selector = StarProductSelector()
        self.funnel_builder = SalesFunnelBuilder()
        self.pricing = PricingOptimizer()
        self.cart = CartRecoveryBuilder()
        self.b2b = B2BSalesPipeline()
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"activations": 0, "last_full_activation": None}
    
    def _save_state(self):
        # Preserve keys owned by other components sharing this file (e.g. StarProductSelector.runs)
        try:
            existing = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
        except:
            existing = {}
        existing.update(self.state)
        STATE_FILE.write_text(json.dumps(existing, indent=2))
    
    def full_activation(self) -> Dict:
        """Run all 5 sales activation systems."""
        print(f"\n{'='*60}")
        print(f"💰 GGB SALES ACTIVATION — Full System")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        results = {}
        
        # 1. Star Products
        print("⭐ Step 1: Selecting star products...")
        stars = self.star_selector.select_star_products(15)
        results["star_products"] = len(stars)
        print(f"   Selected {len(stars)} star products")
        for s in stars[:3]:
            print(f"     📖 {s.get('title', '?')[:50]}")
        
        # 2. Lead Magnet + Funnel
        print("\n🎯 Step 2: Building sales funnel...")
        magnet = self.funnel_builder.build_lead_magnet(stars)
        results["lead_magnet"] = bool(magnet)
        if magnet:
            print(f"   Lead Magnet: {magnet.get('title', '?')}")
        
        sequence = self.funnel_builder.build_email_sequence(stars)
        results["email_sequence"] = bool(sequence)
        if sequence:
            print(f"   Email Sequence: {len(sequence.get('sequence', []))} days")
        
        if magnet:
            page = self.funnel_builder.build_landing_page(stars, magnet)
            results["landing_page"] = bool(page)
            if page:
                print(f"   Landing Page: {page}")
        
        # 3. Pricing Tiers
        print("\n💰 Step 3: Optimizing pricing...")
        tiers = self.pricing.generate_pricing_tiers()
        results["pricing_tiers"] = bool(tiers)
        if tiers:
            for t in tiers[:3]:
                print(f"     ${t.get('price', '?'):>5} | {t.get('tier', '?')}")
        
        # 4. Cart Recovery
        print("\n🛒 Step 4: Building cart recovery...")
        recovery = self.cart.build_recovery_sequence()
        results["cart_recovery"] = bool(recovery)
        if recovery:
            print(f"   {len(recovery.get('sequence', []))} recovery emails")
        
        # 5. B2B Pipeline
        print("\n🏢 Step 5: Building B2B pipeline...")
        targets = self.b2b.generate_b2b_targets()
        results["b2b_targets"] = len(targets)
        if targets:
            for t in targets[:3]:
                print(f"     {t.get('name', '?')[:40]} | {t.get('type', '?')} | ${t.get('potential_value', 0)}")
        
        self.state["activations"] += 1
        self.state["last_full_activation"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        
        print(f"\n{'='*60}")
        print(f"✅ SALES ACTIVATION COMPLETE")
        print(f"{'='*60}")
        print(f"   Star Products: {results['star_products']}")
        print(f"   Lead Magnet: {'✅' if results.get('lead_magnet') else '❌'}")
        print(f"   Email Sequence: {'✅' if results.get('email_sequence') else '❌'}")
        print(f"   Landing Page: {'✅' if results.get('landing_page') else '❌'}")
        print(f"   Pricing Tiers: {'✅' if results.get('pricing_tiers') else '❌'}")
        print(f"   Cart Recovery: {'✅' if results.get('cart_recovery') else '❌'}")
        print(f"   B2B Targets: {results.get('b2b_targets', 0)}")
        
        return results

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Sales Activation System")
    parser.add_argument("--activate", action="store_true", help="Run full sales activation")
    parser.add_argument("--stars", action="store_true", help="Select star products only")
    parser.add_argument("--funnel", action="store_true", help="Build sales funnel only")
    parser.add_argument("--pricing", action="store_true", help="Optimize pricing only")
    parser.add_argument("--cart", action="store_true", help="Build cart recovery only")
    parser.add_argument("--b2b", action="store_true", help="Build B2B pipeline only")
    parser.add_argument("--report", action="store_true", help="Sales activation report")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"💰 GGB SALES ACTIVATION SYSTEM")
    print(f"   Designed by the AI Think Tank")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    activator = SalesActivator()
    
    if args.activate:
        activator.full_activation()
        return
    
    if args.stars:
        selector = StarProductSelector()
        stars = selector.select_star_products(15)
        print(f"⭐ Star Products Selected:")
        for s in stars:
            print(f"  📖 {s.get('title', '?')[:60]}")
            print(f"     {s.get('reason', '')[:80]}")
        return
    
    if args.funnel:
        stars = StarProductSelector().select_star_products(5)
        magnet = activator.funnel_builder.build_lead_magnet(stars)
        if magnet:
            print(f"🎯 Lead Magnet: {magnet.get('title', '?')}")
            print(f"   {magnet.get('description', '')[:100]}")
            print(f"   Headline: {magnet.get('headline', '')}")
        seq = activator.funnel_builder.build_email_sequence(stars)
        if seq:
            print(f"\n📧 Email Sequence:")
            for e in seq.get("sequence", []):
                print(f"   Day {e.get('day', '?')}: {e.get('subject', '')[:60]}")
        page = activator.funnel_builder.build_landing_page(stars, magnet or {})
        if page:
            print(f"\n🌐 Landing Page: {page}")
        return
    
    if args.pricing:
        tiers = activator.pricing.generate_pricing_tiers()
        if tiers:
            print(f"💰 Pricing Tiers:")
            for t in tiers:
                print(f"  ${t.get('price', '?'):>5} | {t.get('tier', '?'):25s} | {t.get('target', '')[:40]}")
        return
    
    if args.cart:
        recovery = activator.cart.build_recovery_sequence()
        if recovery:
            print(f"🛒 Cart Recovery Sequence:")
            for e in recovery.get("sequence", []):
                print(f"   Email {e.get('email', '?')} ({e.get('timing', '?')}): {e.get('subject', '')[:60]}")
        return
    
    if args.b2b:
        targets = activator.b2b.generate_b2b_targets()
        if targets:
            print(f"🏢 B2B Targets:")
            for t in targets:
                print(f"  {t.get('name', '?')[:45]:45s} | {t.get('type', '?'):15s} | ${t.get('potential_value', 0):>6}")
        return
    
    if args.report:
        print(f"📊 SALES ACTIVATION REPORT")
        print(f"{'='*40}")
        print(f"   Activations: {activator.state['activations']}")
        print(f"   Star Products: {len(activator.star_selector.state.get('star_products', []))}")
        print(f"   Funnels Built: {len(activator.funnel_builder.state.get('funnels', []))}")
        print(f"   Pricing Tiers: {len(activator.pricing.state.get('tiers', []))}")
        print(f"   Cart Sequences: {len(activator.cart.state.get('sequences', []))}")
        print(f"   B2B Targets: {len(activator.b2b.state.get('targets', []))}")
        print(f"   B2B Outreach: {len(activator.b2b.state.get('outreach', []))}")
        return
    
    # Default: full activation
    activator.full_activation()

if __name__ == "__main__":
    main()
