#!/usr/bin/env python3
"""Generate placeholder EPUBs for all books in the database."""
import sqlite3
import zipfile
from pathlib import Path

conn = sqlite3.connect('/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/publishing-bot/brain-state.db')
books = conn.execute('SELECT id, title FROM books').fetchall()
conn.close()

epub_dir = Path('/Users/darrylsmac/gullahgeecheebiz-site/publish/for-distribution/google-play')
epub_dir.mkdir(parents=True, exist_ok=True)

existing = set(f.stem for f in epub_dir.glob('*.epub'))
print(f'Total books: {len(books)}, Already have EPUBs: {len(existing)}')

created = 0
for book_id, title in books:
    short_id = book_id[-12:]
    if short_id not in existing:
        epub_path = epub_dir / f'{short_id}.epub'
        with zipfile.ZipFile(epub_path, 'w') as zf:
            zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_DEFLATED)
            container = '<?xml version="1.0" encoding="UTF-8"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
            zf.writestr('META-INF/container.xml', container)
            opf = f'<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">{book_id}</dc:identifier><dc:title>{title}</dc:title><dc:creator>Darryl Elliott Brown</dc:creator><dc:language>en</dc:language><dc:publisher>Gullah Geechee Biz</dc:publisher></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="ch1" href="chapters/ch1.xhtml" media-type="application/xhtml+xml"/></manifest><spine toc="nav"><itemref idref="ch1"/></spine></package>'
            zf.writestr('OEBPS/content.opf', opf)
            nav = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml"><head><title>TOC</title></head><body><nav epub:type="toc"><h1>Contents</h1><ol><li><a href="chapters/ch1.xhtml">Intro</a></li></ol></nav></body></html>'
            zf.writestr('OEBPS/nav.xhtml', nav)
            ch1 = f'<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml"><head><title>{title}</title></head><body><h1>{title}</h1><p>This is a placeholder EPUB for distribution testing.</p><p>Author: Darryl Elliott Brown</p><p>Publisher: Gullah Geechee Biz</p></body></html>'
            zf.writestr('OEBPS/chapters/ch1.xhtml', ch1)
        existing.add(short_id)
        created += 1
        if created % 50 == 0:
            print(f'  Created {created}/{len(books)} EPUBs...')

print(f'Done! Created {created} new EPUBs. Total: {len(existing)}')
