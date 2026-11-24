# NaradVani avatar build step, run inside Blender 5.3 + MPFB 2.0.18 (exported from the working .blend).

import bpy, numpy as np, mathutils
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
def paint_tilak(img_name="nv_skin_medium_brown.png", z0=1.684, arm_bot=0.0052, arm_top=0.0068, arm_hw=0.0012, top=0.044,
                red_z=(0.005,0.033), red_hw=0.0015, cream=(0.94,0.86,0.66), redc=(0.62,0.04,0.04), strength=0.93,
                base_npy="/private/tmp/claude-501/-Users-sachin-Sachin-Portfolio-Astrobrain/bc3247f8-3353-4845-a232-61efc5d83125/scratchpad/skin_before_tilak.npy"):
    body = bpy.data.objects["NaradVani"]; rig = bpy.data.objects["NaradVani.rig"]
    dg = bpy.context.evaluated_depsgraph_get()
    bp_=body.modifiers.get("BustPreview")
    if bp_: bp_.show_viewport=False
    rig.data.pose_position = 'REST'; dg.update()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg)
    rig.data.pose_position = 'POSE'
    if bp_: bp_.show_viewport=True
    dg.update()
    me.transform(body.matrix_world); me.calc_loop_triangles()
    tris = me.loop_triangles; uvl = me.uv_layers.active.data
    bvh = BVHTree.FromPolygons([v.co for v in me.vertices], [t.vertices for t in tris])
    img = bpy.data.images[img_name]; W,H = img.size
    base = np.load(base_npy).reshape(H,W,4)
    def seg(px,pz,ax,az,bx,bz):
        vx,vz=bx-ax,bz-az; t=np.clip(((px-ax)*vx+(pz-az)*vz)/(vx*vx+vz*vz),0,1)
        return np.hypot(px-(ax+t*vx), pz-(az+t*vz)), t
    step=0.00015; X,Z=np.meshgrid(np.arange(-0.014,0.014,step), np.arange(-0.016,0.052,step))
    aL,_=seg(X,Z,-arm_bot,0.004,-arm_top,top); aR,_=seg(X,Z,arm_bot,0.004,arm_top,top)
    r=np.hypot(X,Z-0.004); arc=np.where(Z<0.004,np.abs(r-arm_bot),1)
    d_u=np.minimum(np.minimum(aL,aR),arc)-arm_hw
    dr,td=seg(X,Z,0,-0.0005,0,-0.011); d_drop=dr-(0.0022*(1-td)+0.0004)
    d_cream=np.minimum(d_u,d_drop)
    rd,tr=seg(X,Z,0,red_z[0],0,red_z[1]); d_red=rd-(red_hw*np.sin(np.pi*np.clip(tr,0,1))**0.5+0.0002)
    soft=0.00025; a_c=np.clip(0.5-d_cream/soft,0,1); a_r=np.clip(0.5-d_red/soft,0,1)
    cream=np.array(cream,np.float32); redc=np.array(redc,np.float32)
    acc=np.zeros((H,W,3),np.float32); acw=np.zeros((H,W),np.float32); cnt=np.zeros((H,W),np.float32)
    for i,j in np.argwhere(np.minimum(d_cream,d_red)<0.0015):
        hit=bvh.ray_cast(mathutils.Vector((X[i,j],-0.5,z0+Z[i,j])), mathutils.Vector((0,1,0)))
        if hit[0] is None: continue
        t=tris[hit[2]]; a,b,c=(me.vertices[k].co for k in t.vertices)
        ua,ub,uc=(mathutils.Vector((*uvl[l].uv,0)) for l in t.loops)
        uv=barycentric_transform(hit[0],a,b,c,ua,ub,uc); px_,py_=int(uv.x*W),int(uv.y*H)
        if not (0<=px_<W and 0<=py_<H): continue
        ac,ar=a_c[i,j],a_r[i,j]
        acc[py_,px_]+=cream*ac*(1-ar)+redc*ar; acw[py_,px_]+=max(ac,ar); cnt[py_,px_]+=1
    bpy.data.meshes.remove(me)
    m=cnt>0; alpha=np.zeros((H,W),np.float32); alpha[m]=acw[m]/cnt[m]
    col=np.zeros((H,W,3),np.float32); col[m]=acc[m]/np.maximum(acw[m],1e-6)[:,None]
    out=base.copy(); out[...,:3]=base[...,:3]*(1-alpha[...,None]*strength)+col*alpha[...,None]*strength
    img.pixels=out.ravel(); img.save(); img.reload()
    return int(m.sum())
