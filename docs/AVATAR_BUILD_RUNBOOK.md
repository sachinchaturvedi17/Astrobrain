# Building the NaradVani 3D avatar in Blender with Claude Code

Reference photo: `src/aipandit/web/static/naradvani.jpg`. What he looks like: a man of about 40, warm medium-brown skin, long wavy black hair past the shoulders, no beard (at most light stubble), wide expressive eyes, thick dark brows, a Vaishnava tilak (white U-shape with a red line) on the forehead, warm smile. A veena sits at his left. Keep it that way. Do not add a beard or make him old.

Licences: MPFB assets are CC0, the TalkingHead add-on, rig and weights are MIT (copied into `tools/blender/talkinghead/`). Every extra asset (hair, clothes, textures) must be CC0 or similarly free for commercial use; log each one in `docs/ASSETS.md`.

## Part A: one-time setup (you, about 25 minutes)

1. Install Blender 4.x from blender.org. Install `uv`: `brew install uv`.
2. In Blender: Edit > Preferences > Get Extensions (allow online access) > search "MPFB" > Install. The sidebar (View > Sidebar, press N) then shows an MPFB tab.
3. MPFB tab > System and resources > Web resources > Asset packs. Download "MakeHuman system assets" plus the packs for skin, hair, clothes, eyes, eyebrows, eyelashes, teeth, tongue. From "Functional asset packs" also download **Visemes 02** and **Faceunits 01**. Then Apply assets > Library Settings > Load pack from zip file, for each.
4. Install the TalkingHead add-on: Edit > Preferences > Add-ons > Install from Disk > `tools/blender/talkinghead/talkinghead-addon.py`. In its preferences set Data Directory to that same folder.
5. Register the rig: MPFB tab > New human > From scratch > Create human (dummy). Create assets > MakeRig > Load/Save rig > Load rig > `talkinghead.mpfbskel`; Load weights > `talkinghead.mhw`. Set library rig name `talkinghead`, identifying bone `LeftToe_End`, click Save rig to library. Delete the dummy. Restart Blender.
6. Install the Blender bridge: download `addon.py` from the official repo github.com/ahujasid/mcp-for-blender. In Blender: Edit > Preferences > Add-ons > Install from Disk > that file, then tick "Interface: Blender MCP". In a terminal run `claude mcp add blender uvx mcp-for-blender`, then fully quit and reopen Claude Code.
7. In Blender press N, open the BlenderMCP tab and click Connect to Claude. Leave Blender open.

## Part B: Claude Code builds it

Paste this to Claude Code (in the Astrobrain folder):

> Read docs/AVATAR_BUILD_RUNBOOK.md and docs/AVATAR3D_SPEC.md. Blender is open and connected through the blender MCP. Build the NaradVani avatar following Part B, using src/aipandit/web/static/naradvani.jpg as the reference. Work in rounds: change something, take a viewport screenshot, compare it with the photo, correct. Show me a screenshot after each round and stop for my approval before exporting.

Steps for Claude Code:

1. **Base.** MPFB New human from scratch: male, age about 40, Asian (South Asian) tendency, average build, height about 1.75 m. Create human. Add the custom rig `talkinghead` (Rigging > Add rig > Custom: talkinghead).
2. **Face match.** Compare front and three-quarter screenshots with the photo. Adjust the Model sliders (head width and height, forehead, eyebrow position, eye size and spacing, nose width and bridge, cheeks, mouth width, lips, jaw, chin) until the proportions are close. Keep a short change log.
3. **Assets.** Skin: a medium-brown PBR skin, GameEngine (PBR) material type, "Material instances" off. Eyes with warm dark-brown iris, thick dark eyebrows, eyelashes, teeth, tongue. Hair: the longest wavy black hair available (long hair asset, recolour to near black); if none is long enough, take the longest and extend it later. No beard. Clothing: a plain saffron/ochre upper garment or shawl (shoulders only matter), rudraksha mala if an asset exists.
4. **Tilak.** Paint the white U and red line as a small decal texture on the forehead region of the skin texture (or a thin decal mesh in front of the forehead). Keep it crisp at 1024 px.
5. **Check shapes.** On the export copy confirm the 52 ARKit shape keys and the 15 viseme shape keys exist and move the face correctly (test jawOpen, mouthSmile, eyeBlinkLeft/Right, browInnerUp, viseme_aa, viseme_PP).
6. **Export copy** exactly as in the MPFB section of the TalkingHead guide: Operations > Export copy with Bake mask modifiers, Bake subdiv modifiers, Bake modelling shapekeys, Delete helpers; Load meta-style visemes, Load arkit-style visemes, Interpolate visemes and faceunits. Root object must be named `Armature`. Apply all transforms. Fix materials for glTF (opaque, mask or blend as needed). File > Export > glTF Binary, Selected Objects only, Animation off. Save the `.blend` as `assets_src/naradvani.blend` (git-ignored if large) and the GLB as `assets_src/naradvani_raw.glb`.
7. **Optimise.** Using npm on the Mac: `npx @gltf-transform/cli optimize assets_src/naradvani_raw.glb src/aipandit/web/static/vendor/naradvani.glb --compress meshopt --texture-compress webp --texture-size 1024`. Target 6 MB or less. If a decoder file is needed, vendor it in `static/vendor/` (flat) and record it.
8. **Record.** Write `docs/ASSETS.md` listing every asset, source and licence.
9. **Then** implement the page part of `docs/AVATAR3D_SPEC.md` (three.js, driver, fallback, tests) and tag v1.3.0 locally. Do not push.

Acceptance: the GLB loads in the page, blinks, the mouth follows Hindi and English replies, the face is recognisably the man in the photo (long black hair, tilak, no beard), and Chat mode stays silent.

## Notes

- The Blender bridge can run any Python in Blender. Use only the official repo and keep Blender closed when you are not building.
- A MPFB character will look like a clean game-style character, not a photograph. Better skin textures and lighting (soft key light, warm rim light) close much of the gap.
- If MPFB hair cannot match the long wavy hair, hair cards or a better CC0 hair asset can be added later; this is the usual weak spot.
