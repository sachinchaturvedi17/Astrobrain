# NaradVani avatar build step, run inside Blender 5.3 + MPFB 2.0.18 (exported from the working .blend).

import bpy, bmesh, mathutils
from mathutils.kdtree import KDTree
def build_shawl(A=(0.21,1.53), B=(-0.17,0.99), hw=0.085, offset=0.007, zr=(0.95,1.60), xr=0.30):
    body = bpy.data.objects["NaradVani"]; rig = bpy.data.objects["NaradVani.rig"]
    dg = bpy.context.evaluated_depsgraph_get()
    rig.data.pose_position = 'REST'; dg.update()
    hm = body.modifiers.get("Hide helpers")
    bp_=body.modifiers.get("BustPreview")
    if bp_: bp_.show_viewport=False
    hm.show_viewport = False; dg.update()
    full = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg)
    assert len(full.vertices) == len(body.data.vertices), (len(full.vertices), len(body.data.vertices))
    kd = KDTree(len(full.vertices))
    bg = body.vertex_groups["body"].index
    isbody = [any(g.group == bg and g.weight > 0.5 for g in v.groups) for v in body.data.vertices]
    for v in full.vertices:
        if v.co.z > 0.9 and isbody[v.index]: kd.insert(v.co, v.index)
    kd.balance(); bpy.data.meshes.remove(full)
    hm.show_viewport = True
    if bp_: bp_.show_viewport=True; dg.update()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg)
    rig.data.pose_position = 'POSE'
    bm = bmesh.new(); bm.from_mesh(me)
    dl = bm.verts.layers.deform.active
    if dl is not None: bm.verts.layers.deform.remove(dl)
    bm.verts.ensure_lookup_table()
    kill = [v for v in bm.verts if not (zr[0] < v.co.z < zr[1] and abs(v.co.x) < xr)]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    A3 = mathutils.Vector((A[0],0,A[1])); B3 = mathutils.Vector((B[0],0,B[1]))
    d = (B3-A3).normalized(); n = mathutils.Vector((-d.z,0,d.x)).normalized()
    for sign in (+1,-1):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=A3+n*hw*sign, plane_no=n*sign, clear_outer=True)
    bm.normal_update()
    for v in bm.verts: v.co += v.normal*offset
    old = bpy.data.objects.get("NaradVani.shawl")
    mat = bpy.data.materials.get("NaradVani.shawl")
    if old: bpy.data.objects.remove(old, do_unlink=True)
    sm = bpy.data.meshes.new("NaradVani.shawl"); bm.to_mesh(sm); bm.free()
    sh = bpy.data.objects.new("NaradVani.shawl", sm)
    for c in body.users_collection: c.objects.link(sh)
    sh.parent = rig; sh.matrix_parent_inverse = rig.matrix_world.inverted(); sh.matrix_world = body.matrix_world.copy()
    bones = {b.name for b in rig.data.bones if b.use_deform}
    gi = {g.index: g.name for g in body.vertex_groups if g.name in bones}
    groups = {}
    for v in sm.vertices:
        acc = {}
        for co, idx, dist in kd.find_n(v.co, 4):
            w = 1.0/(dist+1e-4)
            for ge in body.data.vertices[idx].groups if idx < len(body.data.vertices) else []:
                if ge.group in gi: acc[gi[ge.group]] = acc.get(gi[ge.group],0)+ge.weight*w
        s = sum(acc.values()) or 1
        for name, w in acc.items():
            g = groups.get(name) or sh.vertex_groups.new(name=name); groups[name] = g
            g.add([v.index], w/s, 'REPLACE')
    sh.modifiers.new("Armature",'ARMATURE').object = rig
    if mat: sm.materials.append(mat)
    for p in sm.polygons: p.use_smooth = True
    bpy.data.meshes.remove(me)
    bpy.context.view_layer.objects.active = sh
    for o in bpy.context.selected_objects: o.select_set(False)
    sh.select_set(True)
    sm.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.01); bpy.ops.object.mode_set(mode='OBJECT')
    return sh
