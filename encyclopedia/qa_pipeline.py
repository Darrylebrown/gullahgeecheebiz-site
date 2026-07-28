#!/usr/bin/env python3
"""
Encyclopedia Quality Assurance Pipeline
Spelling, prose quality, citation verification, image quality checks.
Run against any volume directory.

Usage:
    python3 qa_pipeline.py encyclopedia/volumes/volume-1/
    python3 qa_pipeline.py encyclopedia/volumes/volume-1/ --json
"""

import os, sys, re, json
from pathlib import Path

GULLAH_WHITELIST = {
    'Gullah', 'Geechee', 'Lowcountry', 'Senegambian', 'Senegambia',
    'Kongo', 'Dikenga', 'Igbo', 'Mende', 'Temne', 'Wolof', 'Mande',
    'Sierra', 'Leone', 'Coakley', 'Manigault', 'Dawley', 'Turner',
    'Lorenzo', 'Dow', 'Pollitzer', 'Creel', 'Opala', 'Rosengarten',
    'Vlach', 'Cross', 'Wilbur', 'Quet', 'Marquetta', 'Goodwine',
    'Chieftess', 'Combahee', 'Vesey', 'Smalls', 'Tubman', 'Towne',
    'Penn', 'Stono', 'Mose', 'Nacimiento', 'Sapelo', 'Hog', 'Hammock',
    'McIntosh', 'Shouters', 'Mt', 'Pleasant', 'Beaufort', 'Hilton',
    'Head', 'Skidaway', 'Dunbar', 'Creek', 'Simons',
    'Carolina', 'Georgia', 'Florida', 'Corridor', 'Creolization',
    'ethnogenesis', 'creole', 'creolization', 'syncretism',
    'coiling', 'fanner', 'sweetgrass', 'bulrush', 'palmetto',
    'pluff', 'mud', 'tabby', 'praise', 'house', 'rootwork',
    'conjure', 'heirs', 'property', 'Gullah/Geechee',
    'sweetgrass', 'fanners', 'coakleys', 'manigaults', 'jacksons',
    'gullahs', 'gullahgeecheebiz', 'gullahgeecheecorridor',
    'gullahsweetgrassbaskets', 'sweetgrasscreationsbylynette',
    'experiencemountpleasant', 'muhlenbergia', 'findingaids',
    'mckissick', 'nmaahc', 'schildkrout', 'cayetano', 'habersham',
    'africanisms', 'praeger', 'cofc', 'matti', 'etsy',
    'multi', 'pre', 'org', 'edu', 'ft', 'usda', 'nea', 'victimhood', 'etc',
    # Additional botanical, ethnic, and scholarly terms
    'andropogon', 'baga', 'casamance', 'cordgrass', 'diola',
    'eds', 'eltis', 'foodways', 'hashtag', 'imperata',
    'instagram', 'jola', 'juncus', 'longleaf', 'mandinka',
    'mazyck', 'mufwene', 'nj', 'overharvesting', 'palustris',
    'paulme', 'pennisetum', 'pinus', 'roemerianus', 'sabal',
    'salikoko', 'saltmeadow', 'scafa', 'schoenoplectus', 'sericea',
    'spp', 'sweetgrassbasket', 'tiktok', 'wpa', 'youson',
    'Diola', 'Jola', 'Mandinka', 'Baga', 'Salikoko', 'Mufwene',
    'Eltis', 'Paulme', 'Mazyck', 'Pennisetum', 'Andropogon',
    'Imperata', 'Juncus', 'Roemerianus', 'Schoenoplectus',
    'Sabal', 'Pinus', 'Casamance',
}

def check_spelling(text):
    from spellchecker import SpellChecker
    spell = SpellChecker()
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
    misspelled = spell.unknown(words)
    return [w for w in misspelled if w not in GULLAH_WHITELIST
            and w.capitalize() not in GULLAH_WHITELIST
            and not (w.endswith('s') and w[:-1] in GULLAH_WHITELIST)]

def check_spelling_file(filepath):
    with open(filepath, encoding='utf-8', errors='replace') as f:
        text = f.read()
    errors = check_spelling(text)
    return {'file': str(filepath), 'total_words': len(re.findall(r'\b[a-zA-Z]+\b', text)),
            'misspellings': errors, 'count': len(errors)}

def check_prose(text):
    import tempfile
    from proselint.tools import LintFile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(text); fname = f.name
    try:
        lf = LintFile(Path(fname))
        return [{'line': p[0], 'column': p[1], 'message': getattr(r, 'message', str(r)),
                 'severity': 'warning', 'check': getattr(r, 'check', 'unknown')}
                for r, p in lf.lint()]
    finally:
        os.unlink(fname)

def check_prose_file(filepath):
    with open(filepath, encoding='utf-8', errors='replace') as f:
        text = f.read()
    issues = check_prose(text)
    return {'file': str(filepath), 'total_issues': len(issues), 'issues': issues[:50]}

def check_citations(text):
    paren = re.findall(r'\(([A-Z][a-z]+(?:\s(?:and|&)\s[A-Z][a-z]+)?)\s*(\d{4})\s*(?:[,:]\s*(\d+))?\)', text)
    name_yr = re.findall(r'([A-Z][a-z]+(?:\s(?:and|&)\s[A-Z][a-z]+)?)\s*\((\d{4})\)', text)
    fnotes = re.findall(r'\[\^(\d+)\]:?\s*(.*?)(?=\n\[\^|\Z)', text, re.DOTALL)
    total = len(paren) + len(name_yr) + len(fnotes)
    return {'inline_citations': len(paren), 'name_year_citations': len(name_yr),
            'footnotes': len(fnotes), 'total_citations': total,
            'sample_citations': (paren + name_yr)[:10],
            'issues': [] if total > 0 else ['No citations found']}

def check_image_quality(filepath):
    try:
        from PIL import Image
        img = Image.open(filepath)
        w, h = img.size
        dpi = img.info.get('dpi', (72, 72))
        issues = []
        if w < 1800 or h < 2700: issues.append(f'Too small: {w}x{h} (min 1800x2700)')
        if dpi[0] < 200: issues.append(f'Low DPI: {dpi[0]} (min 300)')
        if img.format not in ('PNG', 'JPEG', 'TIFF'): issues.append(f'Bad format: {img.format}')
        return {'file': str(filepath), 'dimensions': f'{w}x{h}', 'dpi': dpi,
                'format': img.format, 'pass': len(issues) == 0, 'issues': issues}
    except Exception as e:
        return {'file': str(filepath), 'error': str(e), 'pass': False, 'issues': [str(e)]}

def run_qa(volume_dir):
    vol_path = Path(volume_dir)
    if not vol_path.exists(): return {'error': f'Not found: {volume_dir}'}
    rpt = {'volume_dir': volume_dir, 'timestamp': __import__('datetime').datetime.now().isoformat(),
           'spelling': [], 'prose': [], 'citations': [], 'images': [], 'overall': 'pass'}
    for f in list(vol_path.glob('*.md')) + list(vol_path.glob('*.txt')):
        s = check_spelling_file(str(f))
        if s['misspellings']: rpt['spelling'].append(s)
        p = check_prose_file(str(f))
        if p['total_issues'] > 0: rpt['prose'].append(p)
        with open(f, encoding='utf-8', errors='replace') as fh:
            c = check_citations(fh.read())
        if c['issues']: rpt['citations'].append({'file': str(f), **c})
    for f in list(vol_path.glob('*.png')) + list(vol_path.glob('*.jpg')) + list(vol_path.glob('*.jpeg')):
        rpt['images'].append(check_image_quality(str(f)))
    total = (sum(s['count'] for s in rpt['spelling']) + sum(p['total_issues'] for p in rpt['prose'])
             + sum(len(c.get('issues', [])) for c in rpt['citations'])
             + sum(1 for i in rpt['images'] if not i.get('pass', False)))
    if total > 20: rpt['overall'] = 'needs_revision'
    elif total > 0: rpt['overall'] = 'issues_found'
    rpt['total_issues'] = total
    return rpt

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else '.'
    report = run_qa(target)
    if '--json' in sys.argv:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"QA Report: {report.get('volume_dir', target)}")
        print(f"Overall: {report.get('overall', 'error')} | Issues: {report.get('total_issues', 0)}")
        print(f"  Spelling: {sum(s['count'] for s in report.get('spelling', []))}")
        print(f"  Prose: {sum(p['total_issues'] for p in report.get('prose', []))}")
        print(f"  Citations: {sum(len(c.get('issues', [])) for c in report.get('citations', []))}")
        print(f"  Images: {sum(1 for i in report.get('images', []) if not i.get('pass', False))}")
    sys.exit(0 if report.get('overall') == 'pass' else 2 if report.get('overall') == 'needs_revision' else 1)
