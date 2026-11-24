# NaradVani avatar build step, run inside Blender 5.3 + MPFB 2.0.18 (exported from the working .blend).

import bpy, bmesh, mathutils, numpy as np, math
from mathutils.bvhtree import BVHTree
def ss(a,b,x):
    t=min(1,max(0,(x-a)/(b-a))); return t*t*(3-2*t)
def build_hair(n_roots=300, layers=(0.003,0.008,0.014), seed=4, hair_front=0.062, length=(0.30,0.40),
               wave_a=0.010, wave_l=0.065, n_fly=45, seg=18, n_baby=0):
    rng=np.random.default_rng(seed)
    body=bpy.data.objects["NaradVani"]; rig=bpy.data.objects["NaradVani.rig"]
    brow=bpy.data.objects["NaradVani.mindfront_eyebrows_11"]
    dg=bpy.context.evaluated_depsgraph_get(); rig.data.pose_position='REST'
    hm=body.modifiers["Hide helpers"]; bp=body.modifiers.get("BustPreview")
    if bp: bp.show_viewport=False
    hm.show_viewport=False; dg.update()
    full=bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg); full.transform(body.matrix_world)
    hm.show_viewport=True
    if bp: bp.show_viewport=True
    bz=max((brow.matrix_world@mathutils.Vector(c)).z for c in brow.bound_box)
    rig.data.pose_position='POSE'; dg.update()
    bg=body.vertex_groups["body"].index
    arm={body.vertex_groups[n].index for n in ("LeftArm","RightArm","LeftForeArm","RightForeArm","LeftHand","RightHand") if n in body.vertex_groups}
    good=[]; 
    for v in body.data.vertices:
        gs={g.group:g.weight for g in v.groups}
        if gs.get(bg,0)>0.5 and sum(gs.get(a,0) for a in arm)<0.3: good.append(v.index)
    gset=set(good)
    polys=[p.vertices[:] for p in full.polygons if all(i in gset for i in p.vertices)]
    verts=[v.co.copy() for v in full.vertices]
    bvh=BVHTree.FromPolygons(verts, polys)
    # scalp candidates
    C=mathutils.Vector((0,-0.02,1.70))
    scalp=[]
    for i in good:
        p=verts[i]
        if p.z<1.585: continue
        front=p.y<-0.035
        hl=bz+hair_front-6.0*p.x*p.x if front else 0
        if front and p.z<hl: continue
        if abs(p.x)>0.068 and p.z<1.705 and p.y<0.0: continue   # ears / sideburn area
        if p.z<1.62 and p.y<0.02: continue
        scalp.append(i)
    sp=np.array([verts[i][:] for i in scalp])
    # random roots from scalp verts (uniformish by picking verts then jitter)
    pw=1.0+2.0*(sp[:,1]<-0.03)+1.5*(sp[:,2]>1.74)
    pw=pw/pw.sum()
    roots=sp[rng.choice(len(sp), n_roots, replace=True, p=pw)]+rng.normal(0,0.006,(n_roots,3))
    bm=bmesh.new(); uvl=bm.loops.layers.uv.new("UVMap")
    weights=[]   # per vert z for later weighting
    def card(path, width, u0, u1, normals):
        n=len(path); prev=None
        for k in range(n):
            p=path[k]; d=(path[min(k+1,n-1)]-path[max(k-1,0)]).normalized()
            side=d.cross(normals[k]).normalized()
            w=width*(1-0.45*(k/(n-1)))
            a=bm.verts.new(p-side*w/2); b=bm.verts.new(p+side*w/2)
            if prev:
                f=bm.faces.new((prev[0],prev[1],b,a))
                vv=1-k/(n-1); vp=1-(k-1)/(n-1)
                for l in f.loops:
                    if l.vert is prev[0]: l[uvl].uv=(u0,vp)
                    elif l.vert is prev[1]: l[uvl].uv=(u1,vp)
                    elif l.vert is b: l[uvl].uv=(u1,vv)
                    else: l[uvl].uv=(u0,vv)
            prev=(a,b)
    def grow(root, off, L, phase, stray=0.0, fwd=0.0):
        p=mathutils.Vector(root); loc,nrm,_,_=bvh.find_nearest(p); p=loc+nrm*off
        path=[p.copy()]; normals=[nrm.copy()]; step=L/seg
        for k in range(seg):
            loc,nrm,_,dist=bvh.find_nearest(p)
            back=mathutils.Vector((0,1,0)); down=mathutils.Vector((0,0,-1))
            rad=mathutils.Vector((p.x, p.y-C.y, 0)); rad=rad.normalized() if rad.length>1e-5 else mathutils.Vector((0,1,0))
            g=ss(1.74,1.64,p.z)
            want=(back*((1-g)*0.9 - fwd*g) + down*(0.35+2.2*g) + rad*(0.16+0.30*g)).normalized()
            if stray: want=(want+mathutils.Vector(rng.normal(0,stray,3))).normalized()
            on_skull = p.z>1.655 and nrm is not None and nrm.z>0.15
            t=(want-nrm*want.dot(nrm)) if on_skull else want
            if t.length<1e-6: t=want
            p=p+t.normalized()*step
            loc,nrm,_,dist=bvh.find_nearest(p)
            lay=off*(1+0.8*k/seg)
            if loc is not None and (p-loc).dot(nrm)<lay: p=loc+nrm*lay
            n_out = nrm if on_skull else rad
            path.append(p.copy()); normals.append(n_out.copy())
        # waves (grow along length) perpendicular to path, in normal & side directions
        for k in range(len(path)):
            s=k/(len(path)-1); amp=wave_a*ss(0.15,0.55,s)
            d=(path[min(k+1,len(path)-1)]-path[max(k-1,0)]).normalized()
            side=d.cross(normals[k]).normalized()
            arc=s*L
            path[k]=path[k]+normals[k]*amp*0.25*math.sin(2*math.pi*arc/wave_l+phase)+side*amp*math.sin(2*math.pi*arc/wave_l+phase+0.6)
        return path, normals
    # clumps share wave phase
    for i,r in enumerate(roots):
        off=layers[i%len(layers)]
        L=rng.uniform(*length)*(0.75 if r[1]<-0.05 else 1.0)
        phase=(round(r[0]*40)+round(r[1]*40))*1.3
        fwd=0.55 if (abs(r[0])>0.045 and r[1]<-0.005 and rng.random()<0.7) else 0.0
        path,nr=grow(r, off, L*(1.08 if fwd else 1.0), phase, fwd=fwd)
        u0=rng.uniform(0,0.75-0.22); card(path, rng.uniform(0.022,0.034), u0, u0+rng.uniform(0.16,0.22), nr)
    # hairline short cards: denser front edge combed back
    front=sp[(sp[:,1]<-0.04)]
    for r in front[rng.choice(len(front), min(0,len(front)), replace=False)]:
        path,nr=grow(r, 0.0015, rng.uniform(0.08,0.14), 0.0)
        u0=rng.uniform(0,0.6); card(path, rng.uniform(0.008,0.013), u0, u0+0.12, nr)
    # baby hairs along the front hairline
    if n_baby>0:
        fr=sp[sp[:,1]<-0.05]
        edge=[]
        for p in fr:
            same=fr[np.abs(fr[:,0]-p[0])<0.006]
            if p[2] <= same[:,2].min()+0.008: edge.append(p)
        edge=np.array(edge)
        for k in range(n_baby):
            r=edge[rng.integers(len(edge))]+rng.normal(0,0.003,3)
            loc,nrm,_,_=bvh.find_nearest(mathutils.Vector(r)); p0=loc+nrm*0.0008
            dirv=(mathutils.Vector((rng.normal(0,0.5),-0.6,-1.0))).normalized()
            dirv=(dirv-nrm*dirv.dot(nrm)).normalized()
            L=rng.uniform(0.008,0.022); path=[]; nr=[]
            for s in range(6):
                q=p0+dirv*L*s/5+nrm*0.0015*math.sin(math.pi*s/5)
                path.append(q); nr.append(nrm)
            u0=rng.uniform(0.76,0.92); card(path, rng.uniform(0.003,0.006), u0, u0+0.05, nr)
    # flyaways
    for r in sp[rng.choice(len(sp), n_fly, replace=False)]:
        path,nr=grow(r, 0.016, rng.uniform(0.08,0.22), rng.uniform(0,6), stray=0.55)
        u0=rng.uniform(0.76,0.9); card(path, rng.uniform(0.006,0.012), u0, u0+0.08, nr)
    bpy.data.meshes.remove(full)
    old=bpy.data.objects.get("NaradVani.hair_cards")
    if old: bpy.data.objects.remove(old, do_unlink=True)
    me=bpy.data.meshes.new("NaradVani.hair_cards"); bm.to_mesh(me); bm.free()
    ob=bpy.data.objects.new("NaradVani.hair_cards", me); body.users_collection[0].objects.link(ob)
    ob.parent=rig; ob.matrix_parent_inverse=rig.matrix_world.inverted()
    G={n:ob.vertex_groups.new(name=n) for n in ("Head","Neck","Spine2")}
    for v in me.vertices:
        z=v.co.z; wh=ss(1.50,1.62,z); wn=ss(1.38,1.52,z)*(1-wh); ws=1-wh-wn
        for n,w in (("Head",wh),("Neck",wn),("Spine2",ws)):
            if w>0.001: G[n].add([v.index],w,'REPLACE')
    ob.modifiers.new("Armature",'ARMATURE').object=rig
    mat=bpy.data.materials.get("NaradVani.hair") or bpy.data.materials.new("NaradVani.hair"); mat.use_nodes=True
    nt=mat.node_tree; b=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    tx=nt.nodes.get("hairTex") or nt.nodes.new("ShaderNodeTexImage"); tx.name="hairTex"; tx.image=bpy.data.images["nv_hair_strands.png"]
    rd=nt.nodes.get("AlphaClip") or nt.nodes.new("ShaderNodeMath"); rd.name="AlphaClip"; rd.operation='ROUND'
    nt.links.new(tx.outputs["Color"], b.inputs["Base Color"]); nt.links.new(tx.outputs["Alpha"], rd.inputs[0]); nt.links.new(rd.outputs[0], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value=0.42
    mat.surface_render_method='DITHERED'; mat.use_backface_culling=False
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth=True
    ob.visible_shadow=False
    return ob, len(me.vertices), len(me.polygons), len(sp)
