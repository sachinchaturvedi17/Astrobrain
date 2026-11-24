import bpy

bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.context.scene.render.filepath = bpy.path.abspath("//naradvani_warm_preview.png")
cam = bpy.data.objects.get('CamFront')

if cam:
    bpy.context.scene.camera = cam
    bpy.ops.render.render(write_still=True)
    print("Render saved as naradvani_warm_preview.png in the metaperson folder.")
else:
    print("CamFront not found.")
