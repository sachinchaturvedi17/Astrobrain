"""Headless smoke test: MPFB human + talkinghead rig + export copy, then report."""
import bpy, addon_utils, importlib, os
from bl_ext.blender_org.mpfb.services import AssetService, ObjectService, HumanService, LocationService
from bl_ext.blender_org.mpfb.ui.operations.exportops.exportopspanel import EXPORTOPS_PROPERTIES

ARKIT = """browDownLeft browDownRight browInnerUp browOuterUpLeft browOuterUpRight cheekPuff cheekSquintLeft
cheekSquintRight eyeBlinkLeft eyeBlinkRight eyeLookDownLeft eyeLookDownRight eyeLookInLeft eyeLookInRight
eyeLookOutLeft eyeLookOutRight eyeLookUpLeft eyeLookUpRight eyeSquintLeft eyeSquintRight eyeWideLeft eyeWideRight
jawForward jawLeft jawOpen jawRight mouthClose mouthDimpleLeft mouthDimpleRight mouthFrownLeft mouthFrownRight
mouthFunnel mouthLeft mouthLowerDownLeft mouthLowerDownRight mouthPressLeft mouthPressRight mouthPucker mouthRight
mouthRollLower mouthRollUpper mouthShrugLower mouthShrugUpper mouthSmileLeft mouthSmileRight mouthStretchLeft
mouthStretchRight mouthUpperUpLeft mouthUpperUpRight noseSneerLeft noseSneerRight tongueOut""".split()
VISEMES = "sil PP FF TH DD kk CH SS nn RR aa E I O U".split()
VISEMES = ["viseme_" + v for v in VISEMES]

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

print("CREATE", bpy.ops.mpfb.create_human())
basemesh = next(o for o in bpy.data.objects if ObjectService.object_is_basemesh(o))
HumanService.add_custom_rig(basemesh, "custom.talkinghead", import_weights=True)
rig = ObjectService.find_object_of_type_amongst_nearest_relatives(basemesh, "Skeleton")

bpy.ops.object.select_all(action="DESELECT")
basemesh.select_set(True)
bpy.context.view_layer.objects.active = basemesh
sc = bpy.context.scene
for k, v in dict(mask_modifiers="BAKE", subdiv_modifiers="BAKE", bake_shapekeys=True, delete_helpers=True,
                 visemes_meta=True, faceunits_arkit=True, interpolate=True).items():
    EXPORTOPS_PROPERTIES.set_value(k, v, entity_reference=sc)
before = set(bpy.data.objects)
print("EXPORT_COPY", bpy.ops.mpfb.export_copy())
new = [o for o in bpy.data.objects if o not in before]
copy_mesh = next((o for o in new if ObjectService.object_is_basemesh(o) or (o.type == "MESH" and o.data.shape_keys)), None)
copy_rig = next((o for o in new if o.type == "ARMATURE"), None)
keys = [k.name for k in copy_mesh.data.shape_keys.key_blocks] if copy_mesh and copy_mesh.data.shape_keys else []

mpfb_ver = next((m.bl_info.get("version") for m in addon_utils.modules() if m.__name__.endswith(".mpfb")), None)
th = addon_utils.check("talkinghead-addon")
th_dir = bpy.context.preferences.addons["talkinghead-addon"].preferences.data_path if "talkinghead-addon" in bpy.context.preferences.addons else None
mcp = addon_utils.check("blender_mcp")

print("\n===== SMOKE REPORT =====")
print("Blender:", bpy.app.version_string)
print("MPFB:", mpfb_ver, "enabled:", addon_utils.check("bl_ext.blender_org.mpfb"))
print("Packs:", ", ".join(AssetService.get_pack_names()))
print("Rig registered:", "talkinghead" in [r["name"] for r in AssetService.get_custom_rigs(use_cache=False)],
      "| rig on human:", rig.name if rig else None, len(rig.data.bones) if rig else 0, "bones",
      "| LeftToe_End:", bool(rig and "LeftToe_End" in rig.data.bones),
      "| weighted vgroups:", len([g for g in basemesh.vertex_groups if rig and g.name in rig.data.bones]))
print("Export copy objects:", [(o.name, o.type) for o in new])
print("Export copy root armature:", copy_rig.name if copy_rig else None)
print("Shape keys total:", len(keys))
print("ARKit present: %d/52" % len([k for k in ARKIT if k in keys]), "missing:", [k for k in ARKIT if k not in keys])
print("Visemes present: %d/15" % len([k for k in VISEMES if k in keys]), "missing:", [k for k in VISEMES if k not in keys])
print("TalkingHead add-on (default, loaded):", th, "data dir:", th_dir,
      "| operators:", hasattr(bpy.ops.talkinghead, "build_targets"))
print("MCP bridge add-on (default, loaded):", mcp)
print("========================")
