#!/usr/bin/env python3
"""Vendor three.js (MIT) for the 3D avatar into src/aipandit/web/static/vendor/ (run on a machine with npm and network).

    python3 tools/vendor_three.py            # three@0.186.0
    python3 tools/vendor_three.py --version 0.186.0

Copies the minified build, GLTFLoader, BufferGeometryUtils and the meshopt decoder, and rewrites their bare imports to absolute
/static/vendor/ paths, because the page has a strict CSP (script-src 'self', no import maps). Also writes LICENSE-three.txt.
The flat vendor/ layout is required: the static server serves only files directly under static/vendor/.
"""
import argparse
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / "src" / "aipandit" / "web" / "static" / "vendor"
BASE = "/static/vendor/"
FILES = [  # (path inside the npm package, name in vendor/, rewrite imports?)
    ("build/three.module.min.js", "three.module.min.js", False),
    ("build/three.core.min.js", "three.core.min.js", False),
    ("examples/jsm/loaders/GLTFLoader.js", "GLTFLoader.js", True),
    ("examples/jsm/utils/BufferGeometryUtils.js", "BufferGeometryUtils.js", True),
    ("examples/jsm/libs/meshopt_decoder.module.js", "meshopt_decoder.module.js", False),
]


def rewrite(text: str) -> str:
    """Point the bare 'three' import and the sibling utils import at absolute vendor paths."""
    text = re.sub(r"""(from\s*)(['"])three\2""", lambda m: "%s'%sthree.module.min.js'" % (m.group(1), BASE), text)
    text = re.sub(r"""(from\s*)(['"])\.\./utils/BufferGeometryUtils\.js\2""", lambda m: "%s'%sBufferGeometryUtils.js'" % (m.group(1), BASE), text)
    return text


def leftovers(text: str) -> list:
    """Import specifiers that would break under the CSP (bare names or parent-relative paths)."""
    return [s for s in re.findall(r"""\bfrom\s*['"]([^'"]+)['"]""", text) if not (s.startswith(BASE) or s.startswith("./"))]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", default="0.186.0")
    ver = ap.parse_args().version
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(["npm", "pack", "three@" + ver, "--pack-destination", tmp, "--silent"], capture_output=True, text=True)
        if r.returncode:
            print(r.stderr or r.stdout, file=sys.stderr)
            return 1
        tgz = Path(tmp) / r.stdout.strip().splitlines()[-1]
        DEST.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tgz) as tar:
            for src, name, rw in FILES:
                try:
                    data = tar.extractfile("package/" + src).read().decode("utf-8")
                except KeyError:
                    print("missing in three@%s: %s (the build layout changed; check the package)" % (ver, src), file=sys.stderr)
                    return 2
                if rw:
                    data = rewrite(data)
                    bad = leftovers(data)
                    if bad:
                        print("unrewritten imports in %s: %s" % (name, bad), file=sys.stderr)
                        return 3
                (DEST / name).write_text(data, encoding="utf-8")
                print("%-32s %8.1f KB" % (name, len(data) / 1024))
            lic = tar.extractfile("package/LICENSE").read().decode("utf-8")
        (DEST / "LICENSE-three.txt").write_text(
            "three.js r%s, MIT licence. GLTFLoader, BufferGeometryUtils and the meshopt decoder (meshoptimizer by Arseny Kapoulkine, MIT) come from its examples.\n\n%s" % (ver.split(".")[1], lic),
            encoding="utf-8")
    print("done. Restart the server (static files are cached per path) and hard-refresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
