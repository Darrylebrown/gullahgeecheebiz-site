#!/usr/bin/env python3
"""
Gullah Geechee Biz — Redemption API Server
Runs on the M1, handles instant ebook redemptions.
No manual work needed — customer enters code, gets download immediately.
"""

import json, os, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

HOME = os.path.expanduser("~")
CODES_FILE = os.path.join(HOME, "gullahgeecheebiz-site", "downloads", "codes", "codes.json")
EBOOKS_DIR = os.path.join(HOME, "ebooks", "mass")
PORT = 8765

class RedemptionHandler(BaseHTTPRequestHandler):
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        if path == "/redeem":
            self.handle_redeem()
        elif path == "/status":
            self.handle_status()
        else:
            self.send_error(404, "Not found")
    
    def handle_redeem(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json_response(400, {"success": False, "error": "Invalid JSON"})
            return
        
        code = data.get("code", "").upper().strip()
        email = data.get("email", "").strip()
        
        if not code or len(code) != 19:
            self._json_response(400, {"success": False, "error": "Invalid code format."})
            return
        
        # Load codes
        if not os.path.exists(CODES_FILE):
            self._json_response(500, {"success": False, "error": "System not ready. Try again later."})
            return
        
        with open(CODES_FILE) as f:
            codes = json.load(f)
        
        # Find the code
        found = None
        idx = None
        for i, c in enumerate(codes):
            if c["code"] == code:
                found = c
                idx = i
                break
        
        if not found:
            self._json_response(404, {"success": False, "error": "Code not found. Check and try again."})
            return
        
        if found["redeemed"]:
            self._json_response(409, {"success": False, "error": "This code has already been redeemed."})
            return
        
        # Mark as redeemed
        codes[idx]["redeemed"] = True
        codes[idx]["redeemed_at"] = str(datetime.now())
        codes[idx]["redeemed_by"] = email or "anonymous"
        
        with open(CODES_FILE, "w") as f:
            json.dump(codes, f, indent=2)
        
        # Find the ebook file
        slug = found["ebook_slug"]
        ebook_path = os.path.join(EBOOKS_DIR, f"{slug}.docx")
        if not os.path.exists(ebook_path):
            ebook_path = os.path.join(EBOOKS_DIR, f"{slug}.epub")
        
        if not os.path.exists(ebook_path):
            self._json_response(500, {"success": False, "error": "Ebook file not found. Contact support."})
            return
        
        # Build title from slug
        title = " ".join(word.capitalize() for word in slug.split("-"))
        
        # Return success with download info
        self._json_response(200, {
            "success": True,
            "title": title,
            "message": f"✅ Code redeemed! Your download for '{title}' is ready.",
            "download_url": f"http://localhost:{PORT}/download/{slug}"
        })
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path.startswith("/download/"):
            slug = path.split("/download/")[1]
            ebook_path = os.path.join(EBOOKS_DIR, f"{slug}.docx")
            if not os.path.exists(ebook_path):
                ebook_path = os.path.join(EBOOKS_DIR, f"{slug}.epub")
            
            if os.path.exists(ebook_path):
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{slug}.docx"')
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(ebook_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            
            self.send_error(404, "File not found")
        elif path == "/status":
            self.handle_status()
        else:
            self.send_error(404)
    
    def handle_status(self):
        if not os.path.exists(CODES_FILE):
            self._json_response(200, {"total": 0, "redeemed": 0, "active": 0})
            return
        
        with open(CODES_FILE) as f:
            codes = json.load(f)
        
        total = len(codes)
        redeemed = sum(1 for c in codes if c["redeemed"])
        
        self._json_response(200, {
            "total": total,
            "redeemed": redeemed,
            "active": total - redeemed,
            "status": "running"
        })
    
    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
    
    def log_message(self, format, *args):
        msg = format % args
        if "redeem" in msg.lower() or "download" in msg.lower():
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def main():
    print(f"📖 Gullah Geechee Biz — Redemption API Server")
    print(f"   Codes file: {CODES_FILE}")
    print(f"   Ebooks dir: {EBOOKS_DIR}")
    print(f"   Listening on: http://localhost:{PORT}")
    print(f"")
    print(f"   Endpoints:")
    print(f"     POST /redeem   — Redeem a code (instant)")
    print(f"     GET  /download/<slug> — Download an ebook")
    print(f"     GET  /status   — Server status")
    print(f"")
    print(f"   Press Ctrl+C to stop")
    
    server = HTTPServer(("0.0.0.0", PORT), RedemptionHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
