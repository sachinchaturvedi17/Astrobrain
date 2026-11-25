"""
Round 7: Eyebrows & Facial Character Upgrade + Viewport Cleanup for naradvani_mp.blend
Run inside Blender (Scripting tab -> Run Script, or via Blender CLI / MCP):
  /Applications/Blender.app/Contents/MacOS/Blender -b assets_src/private/metaperson/naradvani_mp.blend --python tools/blender/build/r7_eyebrows_facial_character.py
"""

import os
import bpy

PROJ_ROOT = "/Users/sachin/Desktop/projects/Astrobrain"
TEX_DIR = os.path.join(PROJ_ROOT, "assets_src/private/metaperson/textures")
REV_DIR = os.path.join(PROJ_ROOT, "assets_src/private/review")


def reload_head_textures():
    """Reload upgraded Round 7 head albedo and normal maps into Blender."""
    albedo_path = os.path.join(TEX_DIR, "mp_head_albedo_r2.png")
    normal_path = os.path.join(TEX_DIR, "mp_head_normal_r6.png")

    for img in bpy.data.images:
        fp = bpy.path.abspath(img.filepath) if img.filepath else ""
        if "mp_head_albedo_r2" in img.name or fp.endswith("mp_head_albedo_r2.png"):
            if img.packed_file:
                img.unpack(method="USE_ORIGINAL")
            img.filepath = albedo_path
            img.reload()
            print(f"[R7] Reloaded head albedo: {img.name}")
        elif "mp_head_normal_r6" in img.name or fp.endswith("mp_head_normal_r6.png"):
            if img.packed_file:
                img.unpack(method="USE_ORIGINAL")
            img.filepath = normal_path
            img.reload()
            print(f"[R7] Reloaded head normal: {img.name}")


def apply_facial_character_shapekeys():
    """Dial in warm, approachable ~40-year-old facial expression via ARKit shape keys."""
    target_weights = {
        "mouthSmileLeft": 0.24,
        "mouthSmileRight": 0.24,
        "cheekSquintLeft": 0.20,
        "cheekSquintRight": 0.20,
        "eyeSquintLeft": 0.16,
        "eyeSquintRight": 0.16,
        "browInnerUp": 0.10,
        "browOuterUpLeft": 0.05,
        "browOuterUpRight": 0.05,
        "jawOpen": 0.03,
    }

    updated_meshes = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data.shape_keys:
            continue
        kb = obj.data.shape_keys.key_blocks
        touched = False
        for k_name, val in target_weights.items():
            if k_name in kb:
                kb[k_name].value = val
                touched = True
        if touched:
            updated_meshes.append(obj.name)
    print(f"[R7] Applied warm facial character shape keys to: {updated_meshes}")


def cleanup_viewport():
    """Hide Armature overlay and inspection camera frustums in viewport for clean inspection."""
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            obj.hide_viewport = True
        elif obj.type == "CAMERA":
            obj.hide_viewport = True

    # Also disable relationship lines and bone overlays in open 3D viewports if running interactively
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.overlay.show_bones = False
                        space.overlay.show_relationship_lines = False
                        space.overlay.show_extras = False
    print("[R7] Cleaned up viewport overlays (Armature, camera frustum lines, relationship lines hidden).")


def render_r7_views():
    """Render CamFront, Cam34, and CamFace for Round 7 review."""
    os.makedirs(REV_DIR, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"

    cameras = {
        "CamFront": os.path.join(REV_DIR, "r7_front.png"),
        "Cam34": os.path.join(REV_DIR, "r7_34.png"),
        "CamFace": os.path.join(REV_DIR, "r7_face_close.png"),
    }
    for cam_name, out_path in cameras.items():
        cam = bpy.data.objects.get(cam_name)
        if cam:
            cam.hide_viewport = False
            scene.camera = cam
            scene.render.filepath = out_path
            bpy.ops.render.render(write_still=True)
            cam.hide_viewport = True
            print(f"[R7] Rendered {cam_name} -> {out_path}")


if __name__ == "__main__":
    reload_head_textures()
    apply_facial_character_shapekeys()
    cleanup_viewport()
    render_r7_views()
    bpy.ops.wm.save_mainfile()
    print("[R7] Round 7 complete and saved.")
