"""Build ready-to-upload ZIP bundles for Hostinger Business Web Hosting (hPanel).

Run from the project root:
    python3 deploy/hostinger_business/build_upload_zip.py

Outputs:
1. deploy/hostinger_public_html.zip  -> Upload/extract into your site's `public_html/` via hPanel File Manager or Import Site
2. deploy/Astrobrain_app.zip         -> Upload/extract into your SSH home directory `~/Astrobrain/`
"""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = ROOT / "src" / "aipandit" / "web" / "static"
DEPLOY_DIR = ROOT / "deploy"
HB_DIR = DEPLOY_DIR / "hostinger_business"


def build_public_html_zip() -> Path:
    out_zip = DEPLOY_DIR / "hostinger_public_html.zip"
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(STATIC_DIR / "index.html", "index.html")
        zf.write(HB_DIR / ".htaccess", ".htaccess")
        zf.write(HB_DIR / "api_gateway.php", "api_gateway.php")
        for f in sorted(STATIC_DIR.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                rel = f.relative_to(STATIC_DIR)
                zf.write(f, str(Path("static") / rel))
    return out_zip


def build_app_zip() -> Path:
    out_zip = DEPLOY_DIR / "Astrobrain_app.zip"
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in ("pyproject.toml", "README.md", "run_server.py"):
            p = ROOT / fname
            if p.exists():
                zf.write(p, fname)
        for folder in ("src", "deploy"):
            base = ROOT / folder
            for f in sorted(base.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts and not f.name.endswith((".pyc", ".zip", ".bak")):
                    zf.write(f, str(f.relative_to(ROOT)))
    return out_zip


if __name__ == "__main__":
    p1 = build_public_html_zip()
    p2 = build_app_zip()
    print(f"Created {p1} ({p1.stat().st_size // 1024} KB)")
    print(f"Created {p2} ({p2.stat().st_size // 1024} KB)")
