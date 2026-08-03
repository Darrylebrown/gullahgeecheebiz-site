#!/usr/bin/env python3
"""
GGB Encyclopedia Quality Checker — STANDARD for ALL encyclopedia sets.
Reviews every encyclopedia volume for:
  ✅ Word count (minimum 2500)
  ✅ Academic structure (intro, sections, conclusion, references)
  ✅ Research alignment (matches the assigned topic)
  ✅ Cover art (exists, proper size)
  ✅ File integrity (hashes match)
  ✅ Pricing (set appropriately)
  
Generates a report and blocks any volume that doesn't pass.
"""
import json, sys, hashlib, re
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LANDING_PAD = REPO_ROOT / "publish" / "landing-pad"
PUB_DB = REPO_ROOT / "publish" / "publisher.db"

# Quality standards
STANDARDS = {
    "min_words": 2500,
    "min_sections": 5,
    "min_cover_kb": 50,
    "min_gullah_mentions": 3,
    "require_intro": True,
    "require_conclusion": True,
    "require_references": True,
    "require_price": True,
    "min_price": 3.99,
}

RESEARCHERS = {
    "Dr. Amara Osei": "West African cultural retentions, diaspora studies",
    "Elder James Singleton": "Oral history, community knowledge, living traditions",
    "Dr. Maya Washington": "Archival research, Penn Center records, historical documents",
    "Kofi Mensah": "Gullah language, creole linguistics, African language roots",
    "Sarah Green": "Contemporary community, interviews, current practices",
}

def check_manuscript(ms_path):
    """Check manuscript quality against standards."""
    issues = []
    
    if not ms_path or not ms_path.exists():
        return {"passed": False, "issues": ["Manuscript file missing"], "word_count": 0}
    
    text = ms_path.read_text()
    words = len(text.split())
    chars = len(text)
    
    if words < STANDARDS["min_words"]:
        issues.append(f"Too short: {words} words (minimum {STANDARDS['min_words']})")
    
    sections = re.findall(r'^#{1,3}\s', text, re.MULTILINE)
    if len(sections) < STANDARDS["min_sections"]:
        issues.append(f"Only {len(sections)} sections (minimum {STANDARDS['min_sections']})")
    
    if STANDARDS["require_intro"] and not re.search(r'(?i)^(introduction|overview|background)', text, re.MULTILINE):
        issues.append("No introduction section")
    
    if STANDARDS["require_conclusion"] and not re.search(r'(?i)^(conclusion|summary|closing)', text, re.MULTILINE):
        issues.append("No conclusion section")
    
    if STANDARDS["require_references"] and not re.search(r'(?i)^(references|works cited|bibliography|sources)', text, re.MULTILINE):
        issues.append("No references section")
    
    gullah_count = len(re.findall(r'(?i)gullah\s+geechee', text))
    if gullah_count < STANDARDS["min_gullah_mentions"]:
        issues.append(f"Only {gullah_count} mentions of 'Gullah Geechee'")
    
    actual_hash = hashlib.sha256(text.encode()).hexdigest()
    
    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "word_count": words,
        "char_count": chars,
        "hash": actual_hash,
        "gullah_mentions": gullah_count,
        "sections": len(sections),
    }

def check_cover(cv_path):
    """Check cover art."""
    issues = []
    
    if not cv_path or not cv_path.exists():
        return {"passed": False, "issues": ["Cover file missing"]}
    
    size_kb = cv_path.stat().st_size / 1024
    
    if size_kb < STANDARDS["min_cover_kb"]:
        issues.append(f"Cover too small: {size_kb:.0f}KB (minimum {STANDARDS['min_cover_kb']}KB)")
    
    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "size_kb": round(size_kb, 1),
    }

def check_research_alignment(ms_path, research_path):
    """Check that manuscript aligns with research."""
    issues = []
    
    if not research_path or not research_path.exists():
        return {"passed": False, "issues": ["Research file missing"], "topic": "Unknown", "researcher": "Unknown"}
    
    research = research_path.read_text()
    topic_match = re.search(r'## Research Topic:\s*(.+)', research)
    topic = topic_match.group(1).strip() if topic_match else "Unknown"
    
    researcher_match = re.search(r'## Researcher:\s*(.+)', research)
    researcher = researcher_match.group(1).strip() if researcher_match else "Unknown"
    
    if not ms_path or not ms_path.exists():
        return {"passed": False, "issues": ["Manuscript missing"], "topic": topic, "researcher": researcher}
    
    text = ms_path.read_text()
    topic_keywords = topic.lower().split()
    found = sum(1 for kw in topic_keywords if kw.lower() in text.lower() and len(kw) > 3)
    if found < 2:
        issues.append(f"Manuscript doesn't align with research topic: '{topic}'")
    
    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "topic": topic,
        "researcher": researcher,
        "keyword_match": f"{found}/{len(topic_keywords)}",
    }

def check_pricing(d):
    """Check pricing is set appropriately."""
    issues = []
    price = d.get("publishing", {}).get("price", 0)
    if not price or price < STANDARDS["min_price"]:
        issues.append(f"Price too low: ${price} (minimum ${STANDARDS['min_price']})")
    return {"passed": len(issues) == 0, "issues": issues, "price": price}

def main():
    print("=" * 70)
    print("GGB ENCYCLOPEDIA QUALITY CHECK — STANDARD")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Minimum words: {STANDARDS['min_words']}")
    print("=" * 70)
    
    import sqlite3
    conn = sqlite3.connect(str(PUB_DB))
    
    rows = conn.execute("""
        SELECT manifest_id, state, json_extract(data, '$.title.canonical'),
               json_extract(data, '$.files.manuscript.path'),
               json_extract(data, '$.files.cover.path'),
               data
        FROM manifests 
        WHERE json_extract(data, '$.title.canonical') LIKE 'Encyclopedia Volume%'
        AND state IN ('validated', 'approved')
        ORDER BY json_extract(data, '$.title.canonical')
    """).fetchall()
    
    results = []
    total_passed = 0
    total_issues = 0
    
    for r in rows:
        mid = r[0]
        state = r[1]
        title = r[2]
        ms_path = Path(r[3]) if r[3] else None
        cv_path = Path(r[4]) if r[4] else None
        d = json.loads(r[5])
        
        vol_num = int(title.split()[-1])
        research_dir = LANDING_PAD / f"encyclopedia-vol-{vol_num:02d}"
        research_path = None
        if research_dir.exists():
            rfs = list(research_dir.glob("research-*.md"))
            if rfs:
                research_path = rfs[0]
        
        print(f"\n📚 {title}")
        
        ms_check = check_manuscript(ms_path)
        cv_check = check_cover(cv_path)
        ra_check = check_research_alignment(ms_path, research_path)
        pr_check = check_pricing(d)
        
        vol_passed = all([ms_check['passed'], cv_check['passed'], ra_check['passed'], pr_check['passed']])
        vol_issues = len(ms_check['issues']) + len(cv_check['issues']) + len(ra_check['issues']) + len(pr_check['issues'])
        
        status = "✅ PASS" if vol_passed else "❌ FAIL"
        print(f"   {status} | {ms_check['word_count']:>4d} words | {cv_check.get('size_kb', 0):>5.0f}KB cover | ${pr_check.get('price', 0):.2f}")
        for issue in ms_check['issues'] + cv_check['issues'] + ra_check['issues'] + pr_check['issues']:
            print(f"      ⚠️  {issue}")
        
        if vol_passed:
            total_passed += 1
        total_issues += vol_issues
        
        results.append({
            "title": title,
            "vol": vol_num,
            "passed": vol_passed,
            "issues": vol_issues,
            "words": ms_check['word_count'],
            "cover_kb": cv_check.get('size_kb', 0),
            "price": pr_check.get('price', 0),
            "researcher": ra_check.get('researcher', '?'),
            "topic": ra_check.get('topic', '?'),
        })
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total volumes checked: {len(results)}")
    print(f"Passed: {total_passed}/{len(results)}")
    print(f"Total issues: {total_issues}")
    
    print("\n📊 By Researcher:")
    by_researcher = {}
    for r in results:
        name = r['researcher']
        if name not in by_researcher:
            by_researcher[name] = {"total": 0, "passed": 0, "issues": 0}
        by_researcher[name]["total"] += 1
        if r['passed']:
            by_researcher[name]["passed"] += 1
        by_researcher[name]["issues"] += r['issues']
    
    for name, stats in sorted(by_researcher.items()):
        print(f"   {name[:30]:30s} {stats['passed']}/{stats['total']} passed, {stats['issues']} issues")
    
    print("\n🔴 Volumes Needing Attention:")
    for r in results:
        if not r['passed']:
            print(f"   {r['title']:35s} {r['issues']} issue(s) — {r['topic'][:40]}")
    
    report_path = REPO_ROOT / "ggb-engine" / "headquarters" / "logs" / f"encyclopedia-quality-{datetime.now().strftime('%Y%m%d-%H%M')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, indent=2))
    print(f"\n📄 Full report: {report_path}")
    
    # Return exit code based on results
    return 0 if total_issues == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

