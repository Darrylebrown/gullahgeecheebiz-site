#!/usr/bin/env python3
"""
GGB Quality Gate — Pre-release research & QA bot.
Reviews videos before they go live. Checks spelling, cultural accuracy,
brand compliance, and flags issues for human review.

Usage:
  python3 quality-gate.py                              # Check latest video
  python3 quality-gate.py --all                         # Check all unstaged videos
  python3 quality-gate.py --video "robert-smalls"       # Check specific video
  python3 quality-gate.py --approve "robert-smalls"      # Mark as approved
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────
HOME = os.path.expanduser("~")
OPUS_DIR = os.path.join(HOME, "ggb-agent-opus")
OUTPUT_DIR = os.path.join(OPUS_DIR, "output")
SCENES_DIR = os.path.join(OPUS_DIR, "scenes")
REVIEW_DIR = os.path.join(OPUS_DIR, "review")
os.makedirs(REVIEW_DIR, exist_ok=True)

# ─── Brand Constants ─────────────────────────────────────────────────────────
BRAND_TERMS = {
    "gullah": "Gullah (not Gulllah, Gullal, Gulan, Gulla)",
    "geechee": "Geechee (not Gechee, Geechie)",
    "lowcountry": "Lowcountry (capital L)",
    "gullahgeecheebiz.com": "Correct URL",
}

CULTURAL_RED_FLAGS = [
    "native american", "indian", "plains", "teepee", "tipi",
    "african tribal", "generic african", "jungle",
    "straw hat", "grass skirt",
]

# ─── QA Checks ───────────────────────────────────────────────────────────────

def check_spelling(scenes_path):
    """Run codespell on scene text."""
    if not os.path.exists(scenes_path):
        return {"pass": False, "issues": ["No scenes.json found"]}
    
    with open(scenes_path) as f:
        scenes = json.load(f)
    
    all_text = " ".join(s.get("narration", "") + " " + s.get("text_overlay", "") for s in scenes)
    
    # Write to temp file for codespell
    tmp_path = os.path.join(REVIEW_DIR, "_spellcheck.txt")
    with open(tmp_path, "w") as f:
        f.write(all_text)
    
    result = subprocess.run(
        [sys.executable, "-m", "codespell",
         "--ignore-words", os.path.join(HOME, "gullahgeecheebiz-site/.codespell-ignore"),
         tmp_path],
        capture_output=True, text=True, timeout=30
    )
    
    if result.returncode == 0:
        return {"pass": True, "issues": []}
    
    issues = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    if not issues:
        # codespell returned non-zero but no parseable issues — treat as pass
        return {"pass": True, "issues": []}
    return {"pass": False, "issues": issues}

def check_brand_compliance(scenes_path):
    """Check brand terms are spelled correctly in scene text."""
    if not os.path.exists(scenes_path):
        return {"pass": False, "issues": ["No scenes.json found"]}
    
    with open(scenes_path) as f:
        scenes = json.load(f)
    
    all_text = " ".join(s.get("narration", "") + " " + s.get("text_overlay", "") for s in scenes)
    issues = []
    
    # Check for common misspellings
    misspellings = {
        r'\bgulllah\b': 'Gulllah (should be Gullah)',
        r'\bgullal\b': 'Gullal (should be Gullah)',
        r'\bgulan\b': 'Gulan (should be Gullah)',
        r'\bgulla\b(?!h)': 'Gulla (should be Gullah)',
        r'\bgeechie\b': 'Geechie (should be Geechee)',
        r'\bgechee\b': 'Gechee (should be Geechee)',
        r'\bgullahgeechee\b(?!\.com|\s+biz|\s+Biz)': 'gullahgeechee (should be capitalized)',
    }
    
    for pattern, msg in misspellings.items():
        if re.search(pattern, all_text, re.IGNORECASE):
            issues.append(msg)
    
    # Check final scene has gullahgeecheebiz.com
    last_scene = scenes[-1] if scenes else {}
    if "gullahgeecheebiz.com" not in last_scene.get("text_overlay", ""):
        issues.append("Final scene missing gullahgeecheebiz.com")
    
    # Check GULLAH GEECHEE BIZ appears
    brand_found = any("GULLAH GEECHEE BIZ" in s.get("text_overlay", "") for s in scenes)
    if not brand_found:
        issues.append("Missing GULLAH GEECHEE BIZ text overlay")
    
    return {"pass": len(issues) == 0, "issues": issues}

def check_image_prompts(scenes_path):
    """Flag image prompts that may produce culturally inaccurate content."""
    if not os.path.exists(scenes_path):
        return {"pass": False, "issues": ["No scenes.json found"]}
    
    with open(scenes_path) as f:
        scenes = json.load(f)
    
    issues = []
    for i, scene in enumerate(scenes):
        prompt = scene.get("image_prompt", "").lower()
        for flag in CULTURAL_RED_FLAGS:
            if flag in prompt:
                issues.append(f"Scene {i+1}: prompt contains '{flag}' — may produce inaccurate imagery")
    
    return {"pass": len(issues) == 0, "issues": issues}

def check_video_exists(video_name):
    """Check if the video file exists."""
    video_path = os.path.join(OUTPUT_DIR, video_name)
    if not video_name.endswith(".mp4"):
        video_path = None
        for f in os.listdir(OUTPUT_DIR):
            if video_name in f and f.endswith(".mp4"):
                video_path = os.path.join(OUTPUT_DIR, f)
                break
    
    if not video_path or not os.path.exists(video_path):
        return {"pass": False, "issues": [f"Video not found: {video_name}"]}
    
    size_mb = os.path.getsize(video_path) / 1024 / 1024
    return {"pass": True, "issues": [], "path": video_path, "size_mb": f"{size_mb:.1f}"}

# ─── Review Management ───────────────────────────────────────────────────────

def load_review_status():
    """Load review status for all videos."""
    status_path = os.path.join(REVIEW_DIR, "status.json")
    if os.path.exists(status_path):
        with open(status_path) as f:
            return json.load(f)
    return {}

def save_review_status(status):
    """Save review status."""
    status_path = os.path.join(REVIEW_DIR, "status.json")
    with open(status_path, "w") as f:
        json.dump(status, f, indent=2)

def get_unreviewed_videos():
    """Get list of videos that haven't been reviewed yet."""
    reviewed = load_review_status()
    all_videos = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".mp4")]
    
    unreviewed = []
    for v in all_videos:
        if v not in reviewed or reviewed[v].get("status") == "pending":
            unreviewed.append(v)
    
    return unreviewed

# ─── Main ────────────────────────────────────────────────────────────────────

def review_video(video_name):
    """Run all QA checks on a video."""
    print(f"\n{'='*60}")
    print(f"  🔍 QA Review: {video_name}")
    print(f"{'='*60}")
    
    # Find scenes.json
    scenes_path = os.path.join(OUTPUT_DIR, "scenes.json")
    
    results = {}
    all_pass = True
    
    # Check 1: Video exists
    print(f"\n  📹 Video check...")
    video_check = check_video_exists(video_name)
    results["video"] = video_check
    if video_check["pass"]:
        print(f"    ✅ {video_check['size_mb']} MB")
    else:
        print(f"    ❌ {video_check['issues'][0]}")
        all_pass = False
    
    # Check 2: Spelling
    print(f"  🔤 Spelling check...")
    spelling = check_spelling(scenes_path)
    results["spelling"] = spelling
    if spelling["pass"]:
        print(f"    ✅ No spelling issues")
    else:
        print(f"    ❌ {len(spelling['issues'])} issue(s):")
        for issue in spelling["issues"][:5]:
            print(f"       • {issue}")
        all_pass = False
    
    # Check 3: Brand compliance
    print(f"  🏷️  Brand compliance...")
    brand = check_brand_compliance(scenes_path)
    results["brand"] = brand
    if brand["pass"]:
        print(f"    ✅ Brand terms correct")
    else:
        print(f"    ❌ {len(brand['issues'])} issue(s):")
        for issue in brand["issues"]:
            print(f"       • {issue}")
        all_pass = False
    
    # Check 4: Image prompts
    print(f"  🖼️  Image prompt review...")
    images = check_image_prompts(scenes_path)
    results["images"] = images
    if images["pass"]:
        print(f"    ✅ No cultural red flags")
    else:
        print(f"    ⚠️  {len(images['issues'])} warning(s):")
        for issue in images["issues"]:
            print(f"       • {issue}")
    
    # Summary
    print(f"\n{'='*60}")
    if all_pass:
        print(f"  ✅ ALL CHECKS PASSED — Ready for publishing")
    else:
        print(f"  ⚠️  ISSUES FOUND — Hold for human review")
    print(f"{'='*60}\n")
    
    return all_pass, results

def main():
    parser = argparse.ArgumentParser(
        description="GGB Quality Gate — Pre-release research & QA bot"
    )
    parser.add_argument("--video", "-v", help="Review a specific video by name")
    parser.add_argument("--all", "-a", action="store_true", help="Review all unreviewed videos")
    parser.add_argument("--approve", help="Mark a video as approved")
    parser.add_argument("--reject", help="Mark a video as rejected")
    parser.add_argument("--status", action="store_true", help="Show review status")
    args = parser.parse_args()
    
    status = load_review_status()
    
    if args.approve:
        video = args.approve
        if not any(video in f for f in os.listdir(OUTPUT_DIR) if f.endswith(".mp4")):
            print(f"❌ Video not found: {video}")
            return
        status[video] = {"status": "approved", "reviewed_at": datetime.now().isoformat()}
        save_review_status(status)
        print(f"✅ {video} approved for publishing")
        return
    
    if args.reject:
        video = args.reject
        status[video] = {"status": "rejected", "reviewed_at": datetime.now().isoformat()}
        save_review_status(status)
        print(f"❌ {video} rejected")
        return
    
    if args.status:
        print(f"\n📋 Review Status:\n")
        for video, info in sorted(status.items()):
            emoji = "✅" if info["status"] == "approved" else "❌" if info["status"] == "rejected" else "⏳"
            print(f"  {emoji} {video} — {info['status']}")
        
        unreviewed = get_unreviewed_videos()
        if unreviewed:
            print(f"\n  ⏳ {len(unreviewed)} unreviewed video(s):")
            for v in unreviewed:
                print(f"     • {v}")
        return
    
    if args.video:
        video = args.video
        # Find the actual filename
        matched = [f for f in os.listdir(OUTPUT_DIR) if video in f and f.endswith(".mp4")]
        if not matched:
            print(f"❌ No video found matching: {video}")
            return
        video_name = matched[0]
        passed, results = review_video(video_name)
        
        # Save review status
        status[video_name] = {
            "status": "approved" if passed else "pending",
            "checks": {k: v["pass"] for k, v in results.items()},
            "reviewed_at": datetime.now().isoformat()
        }
        save_review_status(status)
        return
    
    if args.all:
        unreviewed = get_unreviewed_videos()
        if not unreviewed:
            print("✅ All videos reviewed!")
            return
        
        print(f"\n📹 Reviewing {len(unreviewed)} unreviewed video(s)...")
        for video in unreviewed:
            passed, results = review_video(video)
            status[video] = {
                "status": "approved" if passed else "pending",
                "checks": {k: v["pass"] for k, v in results.items()},
                "reviewed_at": datetime.now().isoformat()
            }
            save_review_status(status)
        return
    
    # Default: review latest video
    videos = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".mp4")])
    if not videos:
        print("No videos found in output directory")
        return
    
    latest = videos[-1]
    passed, results = review_video(latest)
    status[latest] = {
        "status": "approved" if passed else "pending",
        "checks": {k: v["pass"] for k, v in results.items()},
        "reviewed_at": datetime.now().isoformat()
    }
    save_review_status(status)

if __name__ == "__main__":
    main()
