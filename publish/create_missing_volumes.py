#!/usr/bin/env python3
"""Create missing encyclopedia volumes on Gumroad: create draft -> presign/upload EPUB -> attach -> enable -> verify.
Stops on the 10/day creation quota error. Only counts API-confirmed results as success."""
import json, os, sys, time, sqlite3, urllib.request, urllib.parse

BASE = '/Users/darrylsmac/gullahgeecheebiz-site'
TOKEN = None
for line in open(f'{BASE}/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
API = 'https://api.gumroad.com/v2'
EPUB_DIR = f'{BASE}/publish/for-distribution/google-play'
EVENT = f'{BASE}/publish/event_stream.jsonl'

def api(method, path, data=None, json_body=None):
    url = API + path
    body = None
    if json_body is not None:
        body = json.dumps(json_body).encode()
    elif data is not None:
        body = urllib.parse.urlencode(data).encode()
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header('Authorization', 'Bearer ' + TOKEN)
    if body:
        r.add_header('Content-Type', 'application/json' if json_body is not None else 'application/x-www-form-urlencoded')
    try:
        resp = urllib.request.urlopen(r, timeout=120)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()[:500]
        try:
            return {'error': e.code, 'body': json.loads(raw)}
        except Exception:
            return {'error': e.code, 'body': raw}

def log(action, detail):
    with open(EVENT, 'a') as f:
        f.write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            'source_bot': 'PUBLISHING_TANK_OWNER', 'action': action, 'detail': detail}) + '\n')

def s3_put(url, content, ctype):
    r = urllib.request.Request(url, data=content, method='PUT', headers={'Content-Type': ctype})
    try:
        resp = urllib.request.urlopen(r, timeout=240)
        return resp.status, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, {}

def create_and_publish(vol):
    vol = int(vol)
    tag = f'{vol:02d}'
    title = f'Encyclopedia Volume {tag}'
    epub = f'{EPUB_DIR}/pedia-vol-{tag}.epub'
    if not os.path.exists(epub):
        return {'ok': False, 'error': f'missing epub {epub}'}
    fsize = os.path.getsize(epub)
    fname = os.path.basename(epub)

    # 1) create draft
    d = api('POST', f'/products?access_token={urllib.parse.quote(TOKEN)}', data={
        'name': title,
        'description': f'{title} \u2014 Gullah Geechee cultural heritage collection. Preserve the past. Inspire the future.',
        'price': '999', 'currency': 'usd', 'customizable_price': 'true', 'published': 'false',
    })
    if d.get('error') or not d.get('success'):
        return {'ok': False, 'quota': 'only create 10 products' in str(d), 'error': str(d.get('body') or d)[:220]}
    pid = d['product']['id']
    time.sleep(0.6)

    # 2) presign
    pr = api('POST', f'/files/presign?access_token={urllib.parse.quote(TOKEN)}',
             data={'filename': fname, 'file_size': str(fsize)})
    if not (isinstance(pr, dict) and pr.get('success')):
        return {'ok': False, 'pid': pid, 'error': f'presign: {str(pr)[:200]}'}
    parts = pr.get('parts') or []
    upid, key = pr.get('upload_id'), pr.get('key')
    with open(epub, 'rb') as f:
        content = f.read()
    etags = []
    for part in parts:
        p_url = part.get('presigned_url') or part.get('url')
        st, h2 = s3_put(p_url, content, 'application/epub+zip')
        if st not in (200, 204):
            return {'ok': False, 'pid': pid, 'error': f'S3 PUT {st}'}
        etags.append({'part_number': part.get('part_number', 1), 'etag': (h2.get('ETag') or '').strip('"')})
    # 3) complete
    comp = api('POST', f'/files/complete?access_token={urllib.parse.quote(TOKEN)}',
               json_body={'upload_id': upid, 'key': key, 'parts': etags})
    if not (isinstance(comp, dict) and comp.get('success')):
        return {'ok': False, 'pid': pid, 'error': f'complete: {str(comp)[:200]}'}
    final_url = comp.get('file_url') or pr.get('file_url')
    # 4) attach to product (replaces files list)
    att = api('PUT', f'/products/{urllib.parse.quote(pid)}?{urllib.parse.urlencode({"access_token": TOKEN, "files[][url]": final_url})}')
    if not (isinstance(att, dict) and att.get('success')):
        return {'ok': False, 'pid': pid, 'error': f'attach: {str(att)[:200]}'}
    time.sleep(0.6)
    # 5) publish/enable
    en = api('PUT', f'/products/{urllib.parse.quote(pid)}/enable?access_token={urllib.parse.quote(TOKEN)}')
    if not (isinstance(en, dict) and en.get('success')):
        return {'ok': False, 'pid': pid, 'error': f'enable: {str(en)[:200]}'}
    time.sleep(0.6)
    # 6) verify via API
    g = api('GET', f'/products/{urllib.parse.quote(pid)}?access_token={urllib.parse.quote(TOKEN)}')
    p = g.get('product', {}) if isinstance(g, dict) else {}
    url = p.get('short_url') or p.get('url')
    files = [(f.get('file_name'), f.get('size')) for f in (p.get('files') or [])]
    if not (p.get('published') and url):
        return {'ok': False, 'pid': pid, 'error': f'verify: published={p.get("published")} url={url} files={files}'}
    # 7) verify landing HTTP 200
    try:
        rr = urllib.request.urlopen(url, timeout=60)
        http = rr.status
    except Exception as e:
        http = f'ERR {e}'
    return {'ok': True, 'volume': vol, 'id': pid, 'url': url, 'http': http, 'files': files}

if __name__ == '__main__':
    vols = [int(x) for x in sys.argv[1:]]
    results = []
    for v in vols:
        print(f'VOL {v:02d}: creating...', flush=True)
        r = create_and_publish(v)
        results.append(r)
        if r.get('quota'):
            print('QUOTA HIT — stopping, remaining queued for next run', flush=True)
            stamp = f'{BASE}/publish/.quota_log_stamp'
            import os as _os, time as _t
            try:
                last = _os.path.getmtime(stamp)
            except OSError:
                last = 0
            if _t.time() - last > 3 * 3600:  # at most one quota event per 3h
                log('gumroad_creation_quota', f'10/day cap hit creating vol {v:02d}; vols {v}-{vols[-1]} still queued')
                open(stamp, 'w').close()
            break
        if r.get('ok'):
            print(f'  OK {r["url"]} http={r["http"]} files={r["files"]}', flush=True)
            log('gumroad_volume_created', f'Vol {r["volume"]:02d} live: {r["url"]} (http {r["http"]}, files {r["files"]})')
            # DB update
            conn = sqlite3.connect(f'{BASE}/publish/publisher.db')
            cur = conn.cursor()
            rows = cur.execute('SELECT rowid, manifest_id, data FROM manifests').fetchall()
            for rid, mid, data in rows:
                try:
                    jd = json.loads(data)
                except Exception:
                    continue
                t = jd.get('title') or jd.get('name') or ''
                if f'Volume {r["volume"]:02d}' in t or f'Volume {r["volume"]}' == t or t.strip() == f'Volume {r["volume"]:02d}':
                    jd['gumroad_url'] = r['url']
                    jd['gumroad_status'] = 'live'
                    cur.execute('UPDATE manifests SET state=?, data=?, updated_at=? WHERE rowid=?',
                                ('published', json.dumps(jd), time.strftime('%Y-%m-%dT%H:%M:%S'), rid))
            conn.commit()
            conn.close()
        else:
            print(f'  FAIL {r.get("error")}', flush=True)
            log('gumroad_volume_failed', f'Vol {v:02d}: {r.get("error")}')
        time.sleep(1.5)
    ok = [r for r in results if r.get('ok')]
    print(f'\n=== {len(ok)}/{len(results)} succeeded ===')
    for r in ok:
        print(r['url'])
