# Next phase: avatar realism + human voice (plan, not yet started)

Status: written 2026-11-23. Nothing here is built. Do NOT push, and do NOT
export or commit private assets (assets_src/private/) without approval.

## 0. Keep (do not break)
- avatar3d.js page, lip-sync driver, fallback chain (3D -> 2D -> still), ?avatar=2d, ?model=mp
- Both Blender builds (assets_src/naradvani.blend, assets_src/private/metaperson/)
- GLB contract: 52 ARKit + 15 Oculus viseme shape keys, root "Armature",
  bones Head, Neck, Spine1/2, LeftEye, RightEye. Final GLB <= 8 MB.
- Strict CSP, 319 pytest passing, browser-TTS fallback.

## 1. Licence gate (decides which avatar can ship)
- MetaPerson free export is marked non-commercial. Terms (EULA) page still unread.
  Until resolved, MetaPerson-derived files stay in assets_src/private/ and are
  used for private testing only. Fix = read the EULA / email Avatar SDK.
- Clean-licence path = MPFB (CC0) build. Realism work below targets THIS one
  for shipping; the private one can be improved in parallel for comparison.

## 2. Avatar realism (Blender, via Claude Code + MCP)
Reference: naradvani.jpg. Always render a side-by-side against it BEFORE export.
1. Hair: replace stringy cards with layered cards (3 to 4 layers, alpha-clipped,
   root-to-tip gradient, wave clumps, flyaway wisps at hairline), proper normals.
2. Face: age ~40, fuller cheeks/jaw, slight nasolabial and under-eye detail;
   adjust via MPFB targets, then re-verify all 52+15 shape keys still work.
3. Skin: 2K albedo with pores/variation, subtle roughness map, warm
   subsurface-look via baked tint (no runtime SSS cost).
4. Eyes: depth (iris recess), wet rim, slightly smaller pupil highlight.
5. Mala: even bead spacing, beads rest on the collar/chest (no floating), 2 strands.
6. Shawl: cloth folds (normal map or sculpt), thickness at edges, believable drape.
7. Chest/neck: clavicle and trapezius definition, neck-to-shawl contact shadow.
8. Budget check: GLB <= 8 MB (meshopt + WebP), check frame time stays smooth.
Acceptance: render comparison approved by user, then export, then page check
(?avatar=3d at 120 fps desktop, phone-emulated), then pytest.

## 3. Voice (server-side, human-sounding)
Goal: one consistent NaradVani voice (Hindi + English), audio returned to the
page with timing info so lip-sync follows the audio, not the text.

Candidates (licences from model cards found 2026-11-23; re-verify before shipping):
| Option | Licence (as listed) | Notes |
|---|---|---|
| Kokoro-82M | Apache-2.0 weights | Small, CPU-friendly. Hindi voices listed are female (hf_alpha, hf_beta; graded C). Male Hindi voice NOT confirmed. |
| Indic Parler-TTS (AI4Bharat) | Apache-2.0 on HF card (one aggregator says MIT; HF card may be gated) | ~0.9B params, heavy/slow on CPU. Voice set by text description (e.g. male, calm, low pitch). |
| Piper | Engine MIT; EACH VOICE has its own licence in its MODEL_CARD | Fast CPU. Many voices are non-commercial; pick only voices whose card allows commercial use. |
Avoid: models marked non-commercial/research-only (e.g. Indri, Coqui XTTS CPML).

Plan:
1. Bake-off: same 6 NaradVani lines (Hindi, English, Hinglish) through each viable
   candidate; user listens and picks. Record licence + model card URL for the winner in docs/ASSETS.md.
2. Add endpoint (e.g. POST /api/tts) returning audio (+ word/phoneme timings if the
   engine provides them; otherwise derive timings from audio via forced alignment
   or amplitude envelope). Rate-limit it; cache by text hash; no user data stored.
3. Page: play returned audio; drive visemes from timings (or envelope as fallback).
   Keep browser SpeechSynthesis as automatic fallback if the endpoint is down/slow.
4. Tests: endpoint contract, fallback path, CSP unchanged (media-src 'self' blob: if needed).

## 4. Order (updated by user: avatar finishing FIRST, voice after)
A. Blender realism rounds on the clean MPFB build: hair -> face/skin -> eyes -> mala/shawl -> chest/neck.
   One round at a time, comparison render vs naradvani.jpg, user approves each.
B. Final export (<= 8 MB), page verification, pytest, local commit + tag (no push).
C. Licence read (MetaPerson EULA) in parallel, whenever convenient.
D. Voice bake-off, then /api/tts + audio-driven lip-sync (section 3).

## 5. Prompt to paste into a fresh Claude Code session (Blender open, MCP server started)
Read docs/NEXT_PHASE_REALISM_VOICE.md and docs/AVATAR_BUILD_RUNBOOK.md.
Start with section 2 only (avatar realism) on the clean MPFB build. Work in rounds:
one improvement area per round, render a comparison against naradvani.jpg into
assets_src/review/, and stop for my approval after each round. Do not export,
commit or push anything without my approval. Keep the GLB contract and the 8 MB budget.
