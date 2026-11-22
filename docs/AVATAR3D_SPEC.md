# NaradVani 3D avatar: build spec (for v1.3.0)

Goal: replace the 2D living portrait in Talk mode with a real-time 3D NaradVani (head and shoulders, seated guide) that blinks, breathes, glances, lifts brows and moves his lips to the words. Chat mode stays silent with blinking only. Free to run: no per-minute cost.

Honest expectation: a rigged 3D character is a stylised game-style face. It will move far more convincingly than the 2D photo trick but will not match the photo's realism. The photoreal route is a neural video avatar (HeyGen LiveAvatar, Simli, Anam, MuseTalk on a GPU), which costs per minute. This spec is the free path.

## What I verified (Nov 2026)

- `met4citizen/TalkingHead` is MIT, v1.8.2, depends on three ^0.186. It needs a GLB with a Mixamo-compatible rig, the 52 ARKit blendshapes and the 15 Oculus viseme shape keys. Built-in lip-sync: en, de, fi, fr, lt, pt_br, bn. **No Hindi.** Browser `speechSynthesis` gives no word timestamps, so its own pipeline needs real audio (`speakAudio`).
- Its sample avatars are NOT usable commercially except `mpfb.glb` (CC0, Blender + MPFB). `brunette.glb`, `avaturn.glb`, `avatarsdk.glb`, `vroid.glb` are non-commercial. `mpfb.glb` is 36 MB and a woman in a suit, so it is a test asset only.
- Ready Player Me shut down on 31 Jan 2026; do not plan on it.
- Avaturn makes rigged GLBs (ARKit blendshapes and visemes) from a selfie. Its free-plan commercial terms are not stated on its pricing page; PRO is $800 per month. Read the Terms before shipping anything made with it.
- This sandbox has no npm, pip or Blender, so none of this was built or tested here. Claude Code on the Mac must do it.

## Constraints in this repo

- Strict CSP: `script-src 'self'`, no inline scripts, no importmap (an inline importmap is blocked). Use `<script type="module" src="/static/avatar3d.js">` and import three by absolute path, e.g. `import * as THREE from "/static/vendor/three.module.js"`. Rewrite bare `three` specifiers in the vendored GLTFLoader and any addon files to that path.
- The static server serves only files directly in `static/`, `static/fonts/`, `static/vendor/` and only whitelisted extensions. Add `.glb` (`model/gltf-binary`) and `.mjs` if used to `STATIC_TYPES`, plus wasm only if a decoder needs it. Files are cached per path, so restart the server after changes.
- Chat stays silent. Talk mode must always be able to fall back: no WebGL, GLB failed, or a slow phone -> use the existing 2D `AMLive` portrait -> still image. The Chat | Talk switch, mic, status text and AI-character note stay as they are.

## Asset (the hard part)

Needed: upper body of the man in `naradvani.jpg`: about 40, long wavy black hair past the shoulders, no beard, Vaishnava tilak (white U with a red line), saffron shawl. Match the photo as closely as possible. Build steps are in `docs/AVATAR_BUILD_RUNBOOK.md`. Rig: Mixamo-compatible or at least a head and neck bone; blendshapes: ARKit 52 + Oculus 15 (`viseme_aa`, `viseme_E`, `viseme_I`, `viseme_O`, `viseme_U`, `viseme_PP`, `viseme_FF`, `viseme_TH`, `viseme_DD`, `viseme_kk`, `viseme_CH`, `viseme_SS`, `viseme_nn`, `viseme_RR`, `viseme_sil`).

Options, in order:
1. Blender + MPFB (CC0 base, hair and clothes assets), then run the repo's `blender/` scripts to build visemes from ARKit shapes. Clean licence, most work.
2. Avaturn from `naradvani.jpg` (user's own account, user reads the Terms first). Fast and closest likeness; commercial licence must be confirmed.
3. A purchased or CC0 model with ARKit shapes (check licence per asset).
Record the source and licence of the final GLB in `docs/ASSETS.md`.
Optimise with `@gltf-transform/cli`: meshopt or draco, WebP textures at 1024 px or less, head-and-shoulders only. Budget: 6 MB or less, runs at 30 fps on a mid phone.

## Driver

- Use plain three.js + GLTFLoader with our own driver (not TalkingHead's pipeline), so Hindi, Hinglish and browser voice keep working. Reuse `live.js` text logic: `visemeTrack`/`openness` and the word-boundary re-sync.
- Map text to Oculus visemes (vowels: aa/E/I/O/U; m/b/p/Devanagari labials: PP; f/v: FF; t/d/n: DD/nn; s/z: SS; k/g: kk; ch/j: CH; r: RR), blend with `jawOpen`, smooth with about 60 ms easing, hold visemes about 70 ms.
- Idle: blink with random gaps, double blink 18%, brow micro-movements, eye saccades toward the camera, breathing on chest bone, small head sway. Talk: nod on sentence starts, brow raise on `?`, slow head tilt while listening to the mic.
- Keep `window.AMLive`'s public API (`mount, setMode, speak, stop, listen, stopListening, micSupported`) so `app.js` does not change; add `AMLive.use3d(canvas)` or a mount option, with automatic fallback.
- Warm glow and a simple shop backdrop (lamp, shelf) as three.js scene lights and a background plane. Keep it off on phones if fps drops.

## Tests and checks

- `node --check` all JS; pure tests for viseme mapping with a stub scene; a test that the page works with `AMLive` 3D disabled.
- Playwright: open `#ask`, Talk mode, WebGL canvas present and non-blank; fall back when `WebGLRenderingContext` is stubbed out.
- Verify real browser: voice, mic, lips on a Hindi and an English reply, on desktop and a phone.

## Later upgrade (optional)

Server TTS (Piper Hindi/English voice, check each voice's licence) returns audio plus word timings, enabling TalkingHead's `speakAudio` or audio-driven visemes for exact lip-sync, and a consistent NaradVani voice on every device.
