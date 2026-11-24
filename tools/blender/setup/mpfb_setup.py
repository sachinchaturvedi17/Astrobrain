"""Headless MPFB setup: install asset packs, register the talkinghead custom rig.
Usage: Blender -b --python mpfb_setup.py -- <zips_dir> <talkinghead_dir>
"""
import bpy, sys, os, glob, json

zips_dir, th_dir = sys.argv[sys.argv.index("--") + 1:]

import importlib
mpfb = importlib.import_module("bl_ext.blender_org.mpfb")
from bl_ext.blender_org.mpfb.services import LocationService, AssetService, ObjectService

data_dir = LocationService.get_user_data()
print("MPFB_DATA_DIR", data_dir)

# 1. Asset packs via MPFB's own operator (same as "Load pack from zip file")
AssetService.rescan_pack_metadata()
have = set(AssetService.get_pack_names())
for z in sorted(glob.glob(os.path.join(zips_dir, "*.zip"))):
    pk = os.path.basename(z)[:-4].replace("_cc0", "").replace("_ccby", "")
    if pk in have:
        print("PACK", pk, "already installed"); continue
    r = bpy.ops.mpfb.load_pack(filepath=z)
    print("PACK", os.path.basename(z), r)
AssetService.rescan_pack_metadata()
print("PACKS_INSTALLED", AssetService.get_pack_names())

# 2. Rig registration
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

print("CREATE", bpy.ops.mpfb.create_human())
basemesh = next(o for o in bpy.data.objects if ObjectService.object_is_basemesh(o))
bpy.ops.object.select_all(action="DESELECT")
basemesh.select_set(True)
bpy.context.view_layer.objects.active = basemesh

print("LOAD_RIG", bpy.ops.mpfb.load_rig(filepath=os.path.join(th_dir, "talkinghead.mpfbskel")))
rig = ObjectService.find_object_of_type_amongst_nearest_relatives(basemesh, "Skeleton")
print("RIG_OBJ", rig and rig.name, rig and len(rig.data.bones))

bpy.ops.object.select_all(action="DESELECT")
basemesh.select_set(True)
bpy.context.view_layer.objects.active = basemesh
print("LOAD_WEIGHTS", bpy.ops.mpfb.load_weights(filepath=os.path.join(th_dir, "talkinghead.mhw")))

from bl_ext.blender_org.mpfb.ui.create_assets.makerig import MakeRigProperties
scene = bpy.context.scene
MakeRigProperties.set_value("library_rig_name", "talkinghead", entity_reference=scene)
MakeRigProperties.set_value("library_identifying_bones", "LeftToe_End", entity_reference=scene)
MakeRigProperties.set_value("library_also_save_weights", True, entity_reference=scene)

bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
print("SAVE_TO_LIBRARY", bpy.ops.mpfb.save_rig_to_library())

# delete dummy
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

rigs_dir = LocationService.get_user_data("rigs")
print("RIGS_DIR", rigs_dir, sorted(os.listdir(rigs_dir)) if os.path.isdir(rigs_dir) else None)
AssetService.invalidate_custom_rig_cache()
print("CUSTOM_RIGS", [r["name"] for r in AssetService.get_custom_rigs(use_cache=False)])
