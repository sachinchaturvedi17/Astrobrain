# 3D avatar page: finish and verify (for Claude Code on the Mac)

The page code for v1.3.0 is written and unit-tested, but it could not be run in a browser where it was written (no npm, no GPU). Do these steps in order. Nothing here should be pushed; commit and tag locally only.

## 1. Vendor three.js
```
python3 tools/vendor_three.py
```
Creates `three.module.js`, `three.core.js` (r186 ships no minified builds), `GLTFLoader.js`, `BufferGeometryUtils.js`, `meshopt_decoder.module.js` and `LICENSE-three.txt` in `src/aipandit/web/static/vendor/`. If it reports a missing path, the three.js build layout changed: adjust `FILES` in the tool, keep the vendor folder flat. Add three.js (MIT) and the meshopt decoder (MIT) to `docs/ASSETS.md`.

## 2. Tests
Run the full suite, including the pytest ones: `python3 -m pytest -q` (and `PYTHONPATH=src python3 -m unittest discover -s tests -p "test_v*pure.py"`). `tests/test_v130_pure.py::VendorToolTests` also checks the vendored loaders have no bare imports.

## 3. Real browser (server: `python3 -m aipandit.web --port 8001`, restart after any static change, hard refresh)
Open the Ask page, switch to Talk, and check with the console open:
- No CSP violations. If the meshopt decoder is blocked, the GLB cannot load: check the `'wasm-unsafe-eval'` token in the CSP header.
- `AM3D.report()` in the console: `active: true`, `missing: []`, `bones` includes head, neck, chest, eyeL, eyeR, `fps` at or near 60 on desktop.
- The model faces the camera. If it faces away, set `AM3D.CFG.faceYaw = Math.PI` (and make it the default in `avatar3d.js`).
- Framing: the bust sits in the circular portrait with the eyes about 40% from the top, the shoulders at the bottom and the cut edge hidden by the circle. Tune `CFG.margin` (zoom: larger = further away), `CFG.shiftY` (positive moves the model lower), `CFG.fov`.
- Motion directions: head nod goes down on speech, tilt is a roll, eyes look left and right (not up and down). If an axis is wrong, fix the sign in `rotate()` calls in `start()`.
- Hair cards and eyelashes look cut-out and smooth (no black boxes, no sorting artefacts). Material tuning lives in `tuneMaterial()`.
- Lip-sync on an English and a Hindi reply, and on a long reply: mouth follows the words, closes on m/b/p, rests on spaces and punctuation, and re-syncs on browser word boundaries.
- Chat mode: silent, blinks and breathes only. Switching Chat/Talk, leaving Ask and coming back, and resizing the window do not leak WebGL contexts or leave two canvases.
- Fallback: `?avatar=2d` shows the 2D portrait. Rename the GLB temporarily: the page shows the 2D portrait with no errors that break the page. In Playwright, stub `WebGLRenderingContext` away before load: 2D portrait again.
- Phone (or devtools mobile emulation with CPU throttling): runs smoothly, or drops quality once and then falls back to 2D ("too slow").

## 4. Private test avatar (licence unresolved)
To compare with the MetaPerson build, copy `assets_src/private/metaperson/naradvani_mp.glb` to `src/aipandit/web/static/vendor/naradvani_mp.glb` and open the page with `?model=mp`. That path is git-ignored. Delete the copy before building a wheel (`static/vendor/*` is package data) and never commit it until the Avatar SDK terms are resolved.

## 5. Finish
Record what changed in `CHANGELOG_v1.md`, commit locally on this branch, tag `v1.3.0` if it is not already tagged, and do not push.
