# מצפה המנדטים · Mandatim 2026

Live dashboard tracking Israeli 2026 election poll mandates.
Zero-dependency Python HTTP server: serves `mandates2026.html` from a real
origin (fixes CSP) and proxies whitelisted poll sources via `/api/fetch`
(fixes CORS).

## Run locally

```bash
python3 server.py
# open http://localhost:8787
```

## Deploy (Render)

One-click via the included `render.yaml` blueprint:

1. Go to <https://render.com> → **New +** → **Blueprint**.
2. Connect this repo (`jeniaka/mandatim`).
3. Render reads `render.yaml`, creates a free Python web service.
4. Get a public URL like `https://mandatim.onrender.com`.

Start command: `python3 server.py` — the server binds to `$PORT` automatically.
No build step, no external dependencies (Python 3.9+, incl. 3.13).
