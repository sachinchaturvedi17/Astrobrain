# Blender setup for the NaradVani avatar, scripted (for Claude Code on the Mac)

Blender 5.3.0 is installed at /Applications/Blender.app. Goal: finish Part A of `docs/AVATAR_BUILD_RUNBOOK.md` with the command line and Python instead of clicking. Quit the Blender window first. Do not take over the screen. If a step truly cannot be scripted, stop, say exactly which one, and I will do it by hand.

Binary: `/Applications/Blender.app/Contents/MacOS/Blender` (use `-b` for background, `--python`, `--command`).

## Facts to check first (they may have changed)

- MPFB (extension id `mpfb`, current release 2.0.18 as of Oct 2026) supports Blender 4.2 LTS and newer, with fixes for 5.x. Confirm it works on 5.3. If it does not, install Blender 4.5 LTS side by side and use that for the build.
- The MakeHuman community announced on 2026-11-08 that its forum and asset repository would be down for some time. MPFB's asset packs (system assets, Visemes 02, Faceunits 01, skins, hair, clothes) may therefore not download. Test reachability early. If it is down, report it before doing anything else; do not substitute assets of unknown licence.

## Steps

1. Run `Blender --command extension --help` to learn the exact syntax, then install and enable MPFB from the official extensions repository.
2. Asset packs: read MPFB's own source (its asset pack installer) to see where "Load pack from zip file" unpacks to, then download the packs and install them the same way. Needed: MakeHuman system assets; Visemes 02; Faceunits 01; skin, hair, clothes, eyes, eyebrows, eyelashes, teeth, tongue. Record every pack and its licence in `docs/ASSETS.md`.
3. TalkingHead add-on: install `tools/blender/talkinghead/talkinghead-addon.py` as an add-on, enable it, and set its Data Directory preference to `tools/blender/talkinghead/` (absolute path). It is a legacy-style add-on (bl_info, Blender 4.0 minimum); check it loads on 5.3 and fix nothing in it without telling me.
4. Rig registration (done by clicking in the guide): create a dummy MPFB human, load `talkinghead.mpfbskel` and `talkinghead.mhw`, save the rig to the library as `talkinghead` with identifying bone `LeftToe_End`, delete the dummy. Find the MPFB services or operators that do this and script it. If that is not possible headless, do it once through the Blender MCP bridge (step 5).
5. Blender bridge: `brew install uv` if missing, then `claude mcp add blender uvx mcp-for-blender`. The project's README offers a one-line installer; read the script before running anything piped from the web. Install its `addon.py` into Blender, enable it, and tell me to restart Claude Code and press Connect to Claude in the BlenderMCP sidebar tab.
6. Smoke test (headless): create an MPFB human with the `talkinghead` rig, confirm the basemesh has the ARKit and viseme shape keys after export copy, and print a short report: Blender version, MPFB version, packs installed, rig registered yes/no, shape key counts.

When all of that passes, continue with Part B of `docs/AVATAR_BUILD_RUNBOOK.md` only after I say go.
