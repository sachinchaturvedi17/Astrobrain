import bpy

# Hide armature in viewport for a clear look
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        obj.hide_viewport = True

# Add warmth to expression
head = next((o for o in bpy.data.objects if o.type == 'MESH' and o.data.shape_keys and len(o.data.shape_keys.key_blocks) > 50), None)
if head:
    keys = head.data.shape_keys.key_blocks
    targets = {'smile': 0.25, 'squint': 0.15, 'browInnerUp': 0.1}
    for t, val in targets.items():
        for k in keys.keys():
            if t.lower() in k.lower():
                keys[k].value = val
    print("Shape keys updated.")

# Save as a new working file
new_path = bpy.data.filepath.replace("_pre_realism", "_working")
bpy.ops.wm.save_as_mainfile(filepath=new_path)
print(f"Saved to {new_path}")
