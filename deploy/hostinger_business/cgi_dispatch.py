"""Direct CLI/CGI request dispatcher for Hostinger Business Web Hosting (fallback when loopback worker is cold).

Usage (called by api_gateway.php):
  python3 cgi_dispatch.py <METHOD> <PATH> <QUERY_STRING>   (reads JSON body from stdin if POST)
Outputs a JSON envelope on stdout:
  {"status": 200, "content_type": "...", "headers": {...}, "body_b64": "..."}
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aipandit import v10_engine  # noqa: E402


def dispatch(method: str, path: str, query_string: str, raw_body: bytes) -> dict:
    clean_path = path.split("?", 1)[0]
    qs = urllib.parse.parse_qs(query_string, keep_blank_values=True)
    params = {k: v[0] for k, v in qs.items() if v}

    try:
        if method == "GET" and clean_path == "/api/v10/kundli-pdf":
            pdf_bytes = v10_engine.kundli_pdf(params)
            fname = re.sub(r"[^A-Za-z0-9_-]+", "_", str(params.get("name") or "chart")).strip("_") or "chart"
            return {
                "status": 200,
                "content_type": "application/pdf",
                "headers": {"Content-Disposition": f'attachment; filename="kundli_{fname}.pdf"'},
                "body_b64": base64.b64encode(pdf_bytes).decode("ascii"),
            }
        if method == "GET" and clean_path == "/api/v10/admin/users":
            out = v10_engine.admin_users(params)
            raw = json.dumps(out, ensure_ascii=False).encode("utf-8")
            return {
                "status": 200,
                "content_type": "application/json; charset=utf-8",
                "headers": {},
                "body_b64": base64.b64encode(raw).decode("ascii"),
            }
        if method == "POST" and clean_path.startswith("/api/v10/"):
            payload = json.loads(raw_body.decode("utf-8") or "{}") if raw_body else {}
            out = v10_engine.handle_v10(clean_path, payload)
            raw = json.dumps(out, ensure_ascii=False).encode("utf-8")
            return {
                "status": 200,
                "content_type": "application/json; charset=utf-8",
                "headers": {},
                "body_b64": base64.b64encode(raw).decode("ascii"),
            }
        err = json.dumps({"error": f"route not supported in CGI mode: {method} {clean_path}"}).encode("utf-8")
        return {"status": 404, "content_type": "application/json; charset=utf-8", "headers": {}, "body_b64": base64.b64encode(err).decode("ascii")}
    except ValueError as e:
        err = json.dumps({"error": str(e)[:200]}).encode("utf-8")
        return {"status": 400, "content_type": "application/json; charset=utf-8", "headers": {}, "body_b64": base64.b64encode(err).decode("ascii")}
    except Exception as e:
        err = json.dumps({"error": f"internal error: {e}"}).encode("utf-8")
        return {"status": 500, "content_type": "application/json; charset=utf-8", "headers": {}, "body_b64": base64.b64encode(err).decode("ascii")}


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REQUEST_METHOD", "GET")
    p = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("PATH_INFO", "/")
    q = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("QUERY_STRING", "")
    body = sys.stdin.buffer.read() if m == "POST" else b""
    res = dispatch(m, p, q, body)
    sys.stdout.write(json.dumps(res))
