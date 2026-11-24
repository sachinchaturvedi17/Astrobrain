# NaradVani avatar build step, run inside Blender 5.3 + MPFB 2.0.18 (exported from the working .blend).

import bpy, numpy as np, math, mathutils
from mathutils.bvhtree import BVHTree
def style_hair(sweep_deg=14, vol=0.010, flare=0.022, wave_a=0.0075, wave_l=0.055, lift=0.006,
               bk="/private/tmp/claude-501/-Users-sachin-Sachin-Portfolio-Astrobrain/bc3247f8-3353-4845-a232-61efc5d83125/scratchpad/hair_refit_co.npy"):
    h = bpy.data.objects["NaradVani.punkduck_alpha7_long"]; body = bpy.data.objects["NaradVani"]; rig = bpy.data.objects["NaradVani.rig"]
    P = np.load(bk).astype(np.float64)
    dg = bpy.context.evaluated_depsgraph_get(); rig.data.pose_position='REST'; dg.update()
    bme = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg); bme.transform(body.matrix_world)
    rig.data.pose_position='POSE'; dg.update()
    bvh = BVHTree.FromPolygons([v.co for v in bme.vertices],[p.vertices for p in bme.polygons])
    dist = np.array([bvh.find_nearest(mathutils.Vector(p))[3] or 0 for p in P]); bpy.data.meshes.remove(bme)
    def ss(a,b,x):
        t = np.clip((x-a)/(b-a),0,1); return t*t*(3-2*t)
    C = np.array([0.0,-0.02,1.70])
    x,y,z = P[:,0],P[:,1],P[:,2]
    # 1 sweep back (rotate about X through C), front/top only
    ws = ss(1.63,1.74,z) * ss(0.0,-0.10,y)
    th = -math.radians(sweep_deg)*ws
    ry, rz = y-C[1], z-C[2]
    y2 = C[1] + ry*np.cos(th) - rz*np.sin(th); z2 = C[2] + ry*np.sin(th) + rz*np.cos(th)
    P2 = np.c_[x, y2, z2]
    # 2 volume: horizontal radial push growing with distance from scalp, flare lower down
    d = P2[:,:2] - C[:2]; r = np.linalg.norm(d,axis=1)+1e-6; u = d/r[:,None]
    amt = vol*np.clip(dist/0.03,0,1.6)*ss(1.80,1.70,P2[:,2]) + flare*ss(1.56,1.20,P2[:,2])
    # 3 waves, growing down the length, phase varies around head
    ang = np.arctan2(d[:,0], d[:,1])
    wv = wave_a*ss(1.64,1.40,P2[:,2])*np.sin(2*np.pi*P2[:,2]/wave_l + 3*ang)
    tang = np.c_[-u[:,1], u[:,0]]
    P2[:,:2] += u*(amt+wv)[:,None] + tang*(0.4*wv*np.cos(2*np.pi*P2[:,2]/wave_l))[:,None]
    # top lift
    top = ss(1.74,1.80,P2[:,2]); P2[:,2] += lift*top
    h.data.vertices.foreach_set("co", P2.astype(np.float32).ravel()); h.data.update()
    return float(np.abs(P2-P).max())
