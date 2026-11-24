# NaradVani avatar build step, run inside Blender 5.3 + MPFB 2.0.18 (exported from the working .blend).

import bpy, bmesh, mathutils, math, numpy as np
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
def build_mala(name="NaradVani.mala", drop=0.17, half_w=0.075, top=1.47, R=0.0055, n_front=40, n_back=18, seed=3):
    rng = np.random.default_rng(seed)
    body = bpy.data.objects["NaradVani"]; rig = bpy.data.objects["NaradVani.rig"]
    dg = bpy.context.evaluated_depsgraph_get()
    rig.data.pose_position = 'REST'; dg.update()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg)
    bvh = BVHTree.FromPolygons([v.co for v in me.vertices], [p.vertices for p in me.polygons])
    bpy.data.meshes.remove(me)
    hm = body.modifiers["Hide helpers"]; bp_=body.modifiers.get("BustPreview")
    if bp_: bp_.show_viewport=False
    hm.show_viewport = False; dg.update()
    full = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg)
    bg = body.vertex_groups["body"].index
    kd = KDTree(len(full.vertices))
    for v in full.vertices:
        if v.co.z > 1.0 and any(g.group == bg and g.weight > 0.5 for g in body.data.vertices[v.index].groups): kd.insert(v.co, v.index)
    kd.balance(); bpy.data.meshes.remove(full); hm.show_viewport = True
    if bp_: bp_.show_viewport=True
    rig.data.pose_position = 'POSE'; dg.update()
    pts = []
    for i in range(n_front):
        t = -1 + 2*i/(n_front-1)
        x = half_w*math.sin(t*math.pi/2)*(1.0+0.15*(1-abs(t)))
        z = top - drop*(1-t*t)**0.9
        hit = bvh.ray_cast(mathutils.Vector((x,-0.5,z)), mathutils.Vector((0,1,0)))
        if hit[0]: pts.append(hit[0]+hit[1]*(R+0.011))
    for i in range(1, n_back):
        a = math.pi*i/n_back
        hit = bvh.ray_cast(mathutils.Vector((half_w*math.cos(a),0.5,top+0.005+0.02*math.sin(a))), mathutils.Vector((0,-1,0)))
        if hit[0]: pts.append(hit[0]+hit[1]*(R+0.011))
    bm = bmesh.new(); bm.loops.layers.uv.new('UVMap')
    for p in pts:
        rot=mathutils.Euler(rng.uniform(0,6.283,3)).to_matrix().to_4x4()
        bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=10, radius=R*(0.9+0.2*rng.random()), matrix=mathutils.Matrix.Translation(p)@rot, calc_uvs=True)
    old = bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    mm = bpy.data.meshes.new(name); bm.to_mesh(mm); bm.free()
    ob = bpy.data.objects.new(name, mm)
    for c in body.users_collection: c.objects.link(ob)
    ob.parent = rig; ob.matrix_parent_inverse = rig.matrix_world.inverted()
    bones = {b.name for b in rig.data.bones if b.use_deform}
    gi = {g.index: g.name for g in body.vertex_groups if g.name in bones}
    groups = {}
    for v in mm.vertices:
        acc = {}
        for co, idx, dist in kd.find_n(v.co, 3):
            w = 1/(dist+1e-4)
            for ge in body.data.vertices[idx].groups:
                if ge.group in gi: acc[gi[ge.group]] = acc.get(gi[ge.group],0)+ge.weight*w
        s = sum(acc.values()) or 1
        for n_, w in acc.items():
            g = groups.get(n_) or ob.vertex_groups.new(name=n_); groups[n_] = g; g.add([v.index], w/s, 'REPLACE')
    ob.modifiers.new("Armature",'ARMATURE').object = rig
    mat = bpy.data.materials.get("NaradVani.mala") or bpy.data.materials.new("NaradVani.mala"); mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (0.16,0.055,0.025,1); b.inputs["Roughness"].default_value = 0.55
    mm.materials.append(mat)
    for p in mm.polygons: p.use_smooth = True
    return ob, len(pts), sorted(groups)
