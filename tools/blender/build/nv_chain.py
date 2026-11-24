# NaradVani avatar build step, run inside Blender 5.3 + MPFB 2.0.18 (exported from the working .blend).

import bpy, numpy as np
SCR="/private/tmp/claude-501/-Users-sachin-Sachin-Portfolio-Astrobrain/bc3247f8-3353-4845-a232-61efc5d83125/scratchpad/"
def run_chain(front_rise=0.050):
    ns={}; exec(bpy.data.texts["nv_skin"].as_string(), ns); ns['rebuild_skin'](front_rise=front_rise); _raster=ns['_raster']
    ns={}; exec(bpy.data.texts["nv_project"].as_string(), ns); ns['project_photo'](eyes_r=(50,21))
    ns2={}; exec(bpy.data.texts["nv_tilak"].as_string(), ns2)
    ns2['paint_tilak'](img_name="nv_skin_4k.png", base_npy=SCR+"skin4k_photo.npy", arm_bot=0.0050, arm_top=0.0078, arm_hw=0.0011, top=0.046,
                    red_z=(0.004,0.030), red_hw=0.0017, cream=(0.86,0.70,0.42), redc=(0.58,0.05,0.05), strength=0.88)
    img=bpy.data.images["nv_skin_4k.png"]; T=img.size[0]; px=np.array(img.pixels[:],np.float32).reshape(T,T,4)
    M=np.load(SCR+"redmask.npy"); r=np.kron(M,np.ones((4,4),np.float32))
    for _ in range(6): r=(r+np.roll(r,1,0)+np.roll(r,-1,0)+np.roll(r,1,1)+np.roll(r,-1,1))/5
    px[...,:3]*=(1+r[...,None]*np.array([0.10,-0.035,-0.045],np.float32))
    fw=np.load(SCR+"face_w.npy"); small=px[::4,::4,:3]; lum=small@np.array([0.3,0.59,0.11])
    valid=(lum>0.12)&(~((small[...,0]>0.45)&(small[...,1]<0.2))); core=fw>0.85
    target=np.array([0.475,0.318,0.245])
    def boxblur(a, r, n=3):
        for _ in range(n):
            cc=np.cumsum(np.pad(a,((r+1,r),(0,0))+((0,0),)*(a.ndim-2),mode='edge'),0); a=(cc[2*r+1:]-cc[:-2*r-1])/(2*r+1)
            cc=np.cumsum(np.pad(a,((0,0),(r+1,r))+((0,0),)*(a.ndim-2),mode='edge'),1); a=(cc[:,2*r+1:]-cc[:,:-2*r-1])/(2*r+1)
        return a
    vm=valid.astype(np.float32); low=boxblur(small*vm[...,None],24)/(boxblur(vm,24)[...,None]+1e-4)
    wb=boxblur(np.clip(1-fw,0,1),6,2)[...,None]
    g=target/small[core&valid].mean(0)*(1-wb)+np.clip(target/np.maximum(low,1e-3),0.6,1.6)*wb
    g=np.where(vm[...,None]>0,g,1.0); px[...,:3]=np.clip(px[...,:3]*np.kron(g.astype(np.float32),np.ones((4,4,1),np.float32)),0,1)
    body=bpy.data.objects["NaradVani"]; rig=bpy.data.objects["NaradVani.rig"]
    dg=bpy.context.evaluated_depsgraph_get(); bp=body.modifiers.get("BustPreview")
    if bp: bp.show_viewport=False
    rig.data.pose_position='REST'; dg.update()
    me=bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg); me.transform(body.matrix_world)
    rig.data.pose_position='POSE'
    if bp: bp.show_viewport=True
    dg.update(); me.calc_loop_triangles()
    P=np.array([v.co[:] for v in me.vertices])
    for z0,dz,k in ((1.555,0.05,np.array([0.12,0.13,0.12])),(1.50,0.06,np.array([0.10,0.10,0.10]))):
        Mz=_raster(me,np.clip((z0-P[:,2])/dz,0,1),1024)
        for _ in range(4): Mz=(Mz+np.roll(Mz,1,0)+np.roll(Mz,-1,0)+np.roll(Mz,1,1)+np.roll(Mz,-1,1))/5
        px[...,:3]*=1-np.kron(Mz,np.ones((4,4),np.float32))[...,None]*k.astype(np.float32)
    bpy.data.meshes.remove(me)
    img.pixels=px.ravel(); img.save(); img.reload()
