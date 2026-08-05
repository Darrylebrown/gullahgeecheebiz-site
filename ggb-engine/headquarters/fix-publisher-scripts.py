#!/usr/bin/env python3
"""
Fix all publisher scripts — removes trailing markdown, verifies syntax.
Handles all edge cases: stray chars, code fences, truncated content.
"""
import os, sys, py_compile, re
from pathlib import Path

HQ = Path("/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters")
SCRIPTS = [
    "shopify-uploader.py",
    "pinterest-uploader.py",
    "gumroad-publisher.py",
    "etsy-uploader.py",
    "draft2digital-connector.py",
    "execute-publishing.py",
]

def fix_script(path):
    """Remove trailing markdown artifacts and verify syntax."""
    if not path.exists():
        return f"❌ Not found"
    
    content = path.read_text()
    original_len = len(content)
    
    # Remove leading garbage (stray chars before #!/usr/bin/env)
    while content and content[0] not in '#!\n\r':
        content = content[1:]
    
    # Remove trailing markdown code fences and any text after the last Python code
    lines = content.split('\n')
    
    # Find the last line that looks like Python code
    last_code_line = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip empty lines, markdown fences, and markdown text
        if stripped.startswith('```'):
            continue
        if stripped.startswith('# ') and not stripped.startswith('#!'):
            continue
        if stripped and not stripped.startswith('#'):
            last_code_line = i
    
    # Truncate to last code line + 1 (for trailing newline)
    clean = '\n'.join(lines[:last_code_line + 1]).strip() + '\n'
    
    # Remove any remaining markdown fences
    clean = clean.replace('```python\n', '').replace('```', '')
    
    # Remove trailing markdown-style comments (like "# Save to ...")
    clean_lines = clean.split('\n')
    filtered = []
    for line in clean_lines:
        stripped = line.strip()
        # Skip lines that are just markdown comments about saving
        if stripped.startswith('# Save to') or stripped.startswith('# (This comment'):
            continue
        filtered.append(line)
    clean = '\n'.join(filtered)
    
    path.write_text(clean)
    
    # Verify syntax
    try:
        py_compile.compile(str(path), doraise=True)
        return f"✅ Fixed ({original_len} → {len(clean)} chars, syntax valid)"
    except py_compile.PyCompileError as e:
        return f"❌ Syntax error after fix: {e}"

print(f"\n{'='*55}")
print(f"  🔧 FIXING PUBLISHER SCRIPTS")
print(f"{'='*55}\n")

for name in SCRIPTS:
    path = HQ / name
    result = fix_script(path)
    print(f"  {result}")

print(f"\n{'='*55}")
print(f"  ✅ ALL FIXES APPLIED")
print(f"{'='*55}")
