# Third-party assets and tools for the NaradVani 3D avatar

Shipped file: `src/aipandit/web/static/vendor/naradvani.glb` (5.12 MB, built 2026-11-22). Every asset in it is CC0, MIT, or made for this project. Nothing in it needs an attribution credit, but the credits below are kept anyway.

## What is inside naradvani.glb

| Part | Source | Licence | Notes |
|---|---|---|---|
| Base mesh, face shape keys | MakeHuman base mesh via MPFB 2.0.18 (`makehuman_system_assets`) | CC0 | Bust cut at mid-chest, capped; arms-down pose baked into rest pose |
| 52 ARKit shape keys | Faceunits 01 pack (Mika Suominen) via MPFB export copy | CC0 | |
| 15 Oculus viseme shape keys | Visemes 02 pack (Mika Suominen) via MPFB export copy | CC0 | |
| Rig (22 bones kept of 76) and weights | `tools/blender/talkinghead/talkinghead.mpfbskel`, `talkinghead.mhw` from met4citizen/TalkingHead | MIT (Mika Suominen) | Root node named `Armature` |
| Skin albedo (4K) | Project reference photo `src/aipandit/web/static/naradvani.jpg` projected onto the face, de-lit and colour-matched; rest of body from MakeHuman "Middleage african male" skin (`makehuman_system_assets`), recoloured | Photo: the project's own image. Skin: CC0 | Tilak, redness, scalp shading painted procedurally |
| Skin pore normal (2K), roughness (1K) | Generated procedurally for this project | Project's own | |
| Eyes, iris texture, cornea, tear line | Generated procedurally for this project | Project's own | Replaces the MPFB low-poly eyes |
| Hair (strand cards, strand texture, baby hairs) | Generated procedurally for this project | Project's own | Replaces earlier CC-BY test hair, which is not shipped |
| Eyebrows | Mindfront eyebrows 11, pack `eyebrows01` (Mindfront) | CC0 | |
| Eyelashes | Mindfront eyelashes 02, pack `eyelashes01` (Mindfront) | CC0 | |
| Teeth, tongue | Teeth base, Tongue01 (`makehuman_system_assets`) | CC0 | |
| Shawl (geometry, weave, folds) | Generated from the body surface for this project | Project's own | |
| Rudraksha mala (2 strands) | Generated procedurally for this project | Project's own | |

## Asset packs installed in MPFB (not all shipped)

Source page: https://static.makehumancommunity.org/assets/assetpacks.html. Downloads from `files.makehumancommunity.org` (mirror `files2`). Licences come from each pack's own `packs/<name>.json`.

| Pack | Licence | Authors | Shipped? |
|---|---|---|---|
| makehuman_system_assets | CC0 | makehuman_system | Base mesh, skin base, teeth, tongue |
| visemes02 | CC0 | Mika Suominen | Yes (visemes) |
| faceunits01 | CC0 | Mika Suominen | Yes (ARKit) |
| eyebrows01 | CC0 | Mindfront | Yes |
| eyelashes01 | CC0 | Mindfront | Yes |
| skins01, skins02, skins03 | CC0 | various (see pack json) | No |
| hair01 | CC0 | various | No |
| hair02, hair03 | **CC-BY** | Elvaerwyn; culturalibre, grinsegold, punkduck | No (used only in tests) |
| shirts01 | CC0 | various | No |
| shirts02, shirts03 | **CC-BY** | Elvaerwyn, EWS, janexx, Mindfront, punkduck, DredNicolson | No (used only in tests) |

If any CC-BY asset is ever shipped, add a credit line on the site naming the asset, the author and the CC-BY licence.

## Tools (not shipped)

| Tool | Source | Licence |
|---|---|---|
| Blender 5.3.0 | blender.org | GPL (output is not covered) |
| MPFB 2.0.18 | extensions.blender.org, id `mpfb` | GPL-3.0-or-later (output is not covered) |
| TalkingHead Blender add-on | met4citizen/TalkingHead, copied to `tools/blender/talkinghead/` | MIT |
| MCP for Blender add-on + `mcp-for-blender` 2.3.1 | github.com/ahujasid/mcp-for-blender | MIT |
| glTF-Transform CLI 4 | npm `@gltf-transform/cli` | MIT |

## Vendored runtime libraries (shipped in static/vendor/)

| File | Source | Licence |
|---|---|---|
| `three.module.js`, `three.core.js` | three.js r186 (npm `three@0.186.0`, `build/`) | MIT (three.js authors), see `static/vendor/LICENSE-three.txt` |
| `GLTFLoader.js`, `BufferGeometryUtils.js`, `SkeletonUtils.js` | three.js r186 `examples/jsm/`, bare imports rewritten to `/static/vendor/` by `tools/vendor_three.py` | MIT |
| `meshopt_decoder.module.js` | three.js r186 `examples/jsm/libs/` (meshoptimizer by Arseny Kapoulkine) | MIT |

## Runtime requirements of the GLB

`EXT_meshopt_compression`, `EXT_texture_webp` and `KHR_mesh_quantization` are required extensions. three.js `GLTFLoader` needs `MeshoptDecoder` (from three's `examples/jsm/libs/meshopt_decoder.module.js`, MIT), vendored flat in `static/vendor/` when the page part is built. The cornea uses `KHR_materials_transmission`, which needs `MeshPhysicalMaterial` (GLTFLoader handles this).
