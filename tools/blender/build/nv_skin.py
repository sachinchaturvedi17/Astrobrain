# NaradVani avatar build step, run inside Blender 5.3 + MPFB 2.0.18 (exported from the working .blend).

import bpy, numpy as np, mathutils
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
SCR = "/private/tmp/claude-501/-Users-sachin-Sachin-Portfolio-Astrobrain/bc3247f8-3353-4845-a232-61efc5d83125/scratchpad/"
def _rest_body():
    body = bpy.data.objects["NaradVani"]; rig = bpy.data.objects["NaradVani.rig"]
    dg = bpy.context.evaluated_depsgraph_get(); rig.data.pose_position='REST'; dg.update()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg); me.transform(body.matrix_world)
    rig.data.pose_position='POSE'; dg.update(); me.calc_loop_triangles(); return me
def _raster(me, val, S):
    uv = me.uv_layers.active.data; mask = np.zeros((S,S),np.float32)
    for t in me.loop_triangles:
        vv=[val[i] for i in t.vertices]
        if max(vv)<=0: continue
        p=np.array([uv[l].uv[:] for l in t.loops])*(S-1)
        x0,y0=np.floor(p.min(0)).astype(int); x1,y1=np.ceil(p.max(0)).astype(int)
        xs,ys=np.meshgrid(np.arange(x0,x1+1),np.arange(y0,y1+1))
        (ax,ay),(bx,by),(cx,cy)=p; den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
        if abs(den)<1e-9: continue
        l1=((by-cy)*(xs-cx)+(cx-bx)*(ys-cy))/den; l2=((cy-ay)*(xs-cx)+(ax-cx)*(ys-cy))/den; l3=1-l1-l2
        ins=(l1>=-0.01)&(l2>=-0.01)&(l3>=-0.01); vp=l1*vv[0]+l2*vv[1]+l3*vv[2]
        yy,xx=ys[ins].clip(0,S-1),xs[ins].clip(0,S-1); mask[yy,xx]=np.maximum(mask[yy,xx],vp[ins])
    return mask
def _blur(m, n):
    for _ in range(n): m=(m+np.roll(m,1,0)+np.roll(m,-1,0)+np.roll(m,1,1)+np.roll(m,-1,1))/5
    return m
def rebuild_skin(front_rise=0.052, brow_dilate=0.0022, brow_alpha=0.7):
    body = bpy.data.objects["NaradVani"]; hair = bpy.data.objects["NaradVani.hair_cards"]
    brow = bpy.data.objects["NaradVani.mindfront_eyebrows_11"]
    dg = bpy.context.evaluated_depsgraph_get()
    rig = bpy.data.objects["NaradVani.rig"]; rig.data.pose_position='REST'; dg.update()
    hb = BVHTree.FromObject(hair, dg); hinv = hair.matrix_world.inverted()
    bwm = brow.evaluated_get(dg).to_mesh(); bpts = np.array([(brow.matrix_world @ v.co)[:] for v in bwm.vertices]); brow.evaluated_get(dg).to_mesh_clear()
    rig.data.pose_position='POSE'; dg.update()
    bz = bpts[:,2].max()
    me = _rest_body()
    # base colour from original texture
    src = bpy.data.images["middleage_darkskinned_male_diffuse.png"]; W,H = src.size
    px = np.array(src.pixels[:],np.float32).reshape(H,W,4); rgb = px[...,:3]
    g=(rgb@np.array([0.3,0.59,0.11],np.float32))[...,None]; rgb=(g+(rgb-g)*0.72)*np.array([1.36,1.33,1.30],np.float32)
    # scalp mask
    val = np.zeros(len(me.vertices),np.float32)
    for v in me.vertices:
        w = v.co; front = w.y < -0.06
        zmin = (bz + front_rise + 0.005*np.sin(w.x*170+0.7)+0.003*np.sin(w.x*430+2.1)) if front else bz
        if w.z < zmin - 0.014: continue
        loc,nrm,idx,dist = hb.find_nearest(hinv @ w)
        if dist is None: continue
        val[v.index] = 0.7*np.clip((0.030-dist)/0.020,0,1)*np.clip((w.z-(zmin-0.008))/0.024,0,1)
    S=1024; m = _raster(me,val,S); m2=_blur(np.kron(m,np.ones((H//S,W//S),np.float32)),4)
    a=(np.clip(m2,0,1)*0.93)[...,None]; rgb = rgb*(1-a)+np.array([0.028,0.022,0.019],np.float32)*a
    # brow shadow: skin verts whose (x,z) lies within dilate of brow verts and in front
    from mathutils.kdtree import KDTree
    kd = KDTree(len(bpts))
    for i,p in enumerate(bpts): kd.insert(mathutils.Vector((p[0],0,p[2])), i)
    kd.balance()
    bv = np.zeros(len(me.vertices),np.float32)
    ymin = bpts[:,1].min()
    for v in me.vertices:
        if abs(v.co.z-bz) > 0.03 or v.co.y > ymin+0.03: continue
        co, i, d = kd.find(mathutils.Vector((v.co.x,0,v.co.z)))
        bv[v.index] = np.clip(1-(d/brow_dilate)**2, 0, 1)
    bm_ = _blur(np.kron(_raster(me,bv,S),np.ones((H//S,W//S),np.float32)),3)
    a=(np.clip(bm_,0,1)*brow_alpha)[...,None]; rgb = rgb*(1-a)+np.array([0.03,0.022,0.018],np.float32)*a
    bpy.data.meshes.remove(me)
    px[...,:3]=np.clip(rgb,0,1)
    np.save(SCR+"skin_before_tilak.npy", px.ravel())
    img = bpy.data.images["nv_skin_medium_brown.png"]; img.pixels = px.ravel(); img.save(); img.reload()
    return float((m>0.5).mean()), int((bv>0.3).sum())
