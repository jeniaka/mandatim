#!/usr/bin/env python3
"""
מצפה המנדטים — שרת מקומי + פרוקסי
==================================
מגיש את mandates2026.html מ-origin אמיתי (פותר את חסימת ה-CSP)
ומעביר בקשות לאתרי הסקרים דרך /api/fetch (פותר CORS).

הרצה מקומית:
    python3 server.py
    ואז http://localhost:8787

פריסה ל-Render (Web Service, Python):
    Build Command:  (ריק)
    Start Command:  python3 server.py
    השרת מאזין ל-$PORT אוטומטית.

ללא תלויות חיצוניות. תואם Python 3.9+ כולל 3.13 (בלי מודול cgi).
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# קונסולת Windows (cp1255) מפילה הדפסות עם עברית/סמלים; מכריחים UTF-8 בטוח.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
PAGE = HERE / "mandates2026.html"
PORT = int(os.environ.get("PORT", 8787))

# רק דומיינים ברשימה יעברו דרך הפרוקסי — מונע שימוש בשרת כ-open relay.
ALLOWED_HOSTS = {
    "en.wikipedia.org",
    "he.wikipedia.org",
    "skarim.kan.org.il",
    "www.kan.org.il",
    "kan.org.il",
    "www.skarim.org",
    "skarim.org",
    "api.askio.co.il",
    "www.srugim.co.il",
    "elections.walla.co.il",
}

UA = "mandates-dashboard/1.0 (internal newsroom tool; contact: devops@keshet.prd)"
TIMEOUT = 20


def host_allowed(host: str) -> bool:
    host = (host or "").lower()
    return host in ALLOWED_HOSTS or any(
        host.endswith("." + h) for h in ALLOWED_HOSTS
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "MandatesProxy/1.0"
    protocol_version = "HTTP/1.1"

    # ---------- helpers ----------
    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

    # ---------- routes ----------
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parts = urllib.parse.urlsplit(self.path)
        route = parts.path

        if route in ("/", "/index.html"):
            return self.serve_page()
        if route == "/api/health":
            return self._json(200, {"ok": True, "allowed": sorted(ALLOWED_HOSTS)})
        if route == "/api/fetch":
            return self.proxy(urllib.parse.parse_qs(parts.query))

        self._send(404, b"not found", "text/plain; charset=utf-8")

    def serve_page(self):
        if not PAGE.exists():
            msg = f"לא נמצא {PAGE.name} לצד server.py".encode("utf-8")
            return self._send(500, msg, "text/plain; charset=utf-8")
        self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")

    def proxy(self, qs):
        target = (qs.get("url") or [""])[0]
        if not target:
            return self._json(400, {"error": "חסר פרמטר url"})

        u = urllib.parse.urlsplit(target)
        if u.scheme not in ("http", "https"):
            return self._json(400, {"error": "סכימה לא נתמכת"})
        if not host_allowed(u.hostname):
            return self._json(
                403,
                {
                    "error": f"הדומיין {u.hostname} לא ברשימת ההיתר",
                    "hint": "הוסיפו אותו ל-ALLOWED_HOSTS ב-server.py",
                },
            )

        req = urllib.request.Request(
            target,
            headers={"User-Agent": UA, "Accept": "application/json, text/html;q=0.9"},
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                body = r.read()
                ctype = r.headers.get("Content-Type", "application/json")
            self._send(200, body, ctype)
            print(f"  ✓ {u.hostname}{u.path[:60]}  ({len(body):,} bytes)")
        except urllib.error.HTTPError as e:
            self._json(e.code, {"error": f"המקור החזיר {e.code} {e.reason}"})
            print(f"  ✗ {u.hostname} → HTTP {e.code}")
        except Exception as e:
            self._json(502, {"error": f"{type(e).__name__}: {e}"})
            print(f"  ✗ {u.hostname} → {e}")

def main():
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("\n  מצפה המנדטים")
    print(f"  דף:     http://localhost:{PORT}")
    print(f"  פרוקסי: /api/fetch?url=…   ({len(ALLOWED_HOSTS)} דומיינים מותרים)")
    print("  Ctrl+C לעצירה\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  נעצר.")
        srv.shutdown()


if __name__ == "__main__":
    main()
