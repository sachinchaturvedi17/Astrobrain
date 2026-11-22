#!/usr/bin/env python3
"""Download Leaflet 1.9.4 from the npm registry into static/vendor/ (run once on your machine).
Verifies the tarball against the registry's dist.integrity (sha512)."""
import base64, hashlib, io, json, pathlib, tarfile, urllib.request

VER = "1.9.4"
DEST = pathlib.Path(__file__).resolve().parent.parent / "src/aipandit/web/static/vendor"


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def main():
    meta = json.loads(get(f"https://registry.npmjs.org/leaflet/{VER}"))
    tgz = get(meta["dist"]["tarball"])
    algo, _, b64 = meta["dist"]["integrity"].partition("-")
    if algo != "sha512" or base64.b64encode(hashlib.sha512(tgz).digest()).decode() != b64:
        raise SystemExit("integrity check FAILED - nothing written")
    DEST.mkdir(parents=True, exist_ok=True)
    want = {"package/dist/leaflet.js": "leaflet.js", "package/dist/leaflet.css": "leaflet.css"}
    with tarfile.open(fileobj=io.BytesIO(tgz)) as tf:
        for member, out in want.items():
            (DEST / out).write_bytes(tf.extractfile(member).read())
            print("wrote", DEST / out)
    print("Leaflet", VER, "verified and installed.")


if __name__ == "__main__":
    main()
