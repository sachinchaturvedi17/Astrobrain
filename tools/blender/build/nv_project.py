# NaradVani avatar build step, run inside Blender 5.3 + MPFB 2.0.18 (exported from the working .blend).

import bpy, numpy as np, math, mathutils, os
SCR="/private/tmp/claude-501/-Users-sachin-Sachin-Portfolio-Astrobrain/bc3247f8-3353-4845-a232-61efc5d83125/scratchpad/"
OUT="/Users/sachin/Sachin Portfolio/Astrobrain/assets_src/textures"
def gblur(a, s):
    r=int(3*s); k=np.exp(-0.5*(np.arange(-r,r+1)/s)**2); k/=k.sum()
    pad=np.pad(a, [(r,r),(r,r)]+[(0,0)]*(a.ndim-2), mode='edge')
    b=np.apply_along_axis(lambda m: np.convolve(m,k,'valid'), 0, pad)
    return np.apply_along_axis(lambda m: np.convolve(m,k,'valid'), 1, b)
def project_photo(T=4096, ZL=((1.745,292),(1.693,410),(1.6761,457),(1.633,538),(1.602,611),(1.56,712),(1.50,800)),
                  eyeR=(388,465), eyeL=(550,450), mouth=(480,612,72,22), eyes_r=(40,15), sigma=28, strength=1.0):
    ref=bpy.data.images.load("/Users/sachin/Sachin Portfolio/Astrobrain/src/aipandit/web/static/naradvani.jpg", check_existing=True)
    PW,PH=ref.size; ph=np.array(ref.pixels[:],np.float32).reshape(PH,PW,4)[::-1,:,:3]   # row 0 = top
    # de-light: divide by blurred luminance, renormalise
    L=ph@np.array([0.3,0.59,0.11],np.float32); Lb=gblur(L,sigma)+1e-3
    dl=ph*(np.median(Lb[400:720,330:620])/Lb)[...,None]
    # transform: tilt around eye midpoint
    em=np.array([(eyeR[0]+eyeL[0])/2,(eyeR[1]+eyeL[1])/2]); ang=math.atan2(eyeL[1]-eyeR[1], eyeL[0]-eyeR[0])
    sx=math.hypot(eyeL[0]-eyeR[0], eyeL[1]-eyeR[1])/0.0596
    zs=np.array([z for z,_ in ZL]); ys=np.array([y for _,y in ZL])   # ys measured along the tilted vertical through em
    def to_photo(x,z):
        # vertical (in de-tilted frame) by piecewise mapping, horizontal by sx
        yv=np.interp(-z, -zs, ys)  # zs descending
        dv=yv-em[1]; du=x*sx
        ca,sa=math.cos(ang),math.sin(ang)
        return em[0]+du*ca-dv*sa, em[1]+du*sa+dv*ca
    body=bpy.data.objects["NaradVani"]; rig=bpy.data.objects["NaradVani.rig"]
    dg=bpy.context.evaluated_depsgraph_get(); rig.data.pose_position='REST'
    bp=body.modifiers.get("BustPreview")
    if bp: bp.show_viewport=False
    dg.update()
    me=bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg); me.transform(body.matrix_world)
    if bp: bp.show_viewport=True
    rig.data.pose_position='POSE'; dg.update()
    me.calc_loop_triangles(); uv=me.uv_layers.active.data
    nV=len(me.vertices); PX=np.zeros(nV); PY=np.zeros(nV); WV=np.zeros(nV)
    for v in me.vertices:
        x,y,z=v.co; n=v.normal
        if z<1.53 or z>1.76 or y>-0.04: continue
        fx,fy=to_photo(x,z)
        face=max(0.0,-n.y)
        w=np.clip((face-0.35)/0.35,0,1)
        w*=np.clip((0.066-abs(x))/0.012,0,1)          # inside face width
        w*=np.clip((1.742-z)/0.01,0,1)*np.clip((z-1.535)/0.015,0,1)
        PX[v.index],PY[v.index],WV[v.index]=fx,fy,w
    # base albedo (no tilak) upscaled to T
    base=np.load(SCR+"skin_before_tilak.npy").reshape(2048,2048,4)
    bimg=bpy.data.images.new("tmp_base",2048,2048); bimg.pixels=base.ravel(); bimg.scale(T,T)
    B=np.array(bimg.pixels[:],np.float32).reshape(T,T,4); bpy.data.images.remove(bimg)
    acc=np.zeros((T,T,2),np.float32); wgt=np.zeros((T,T),np.float32)
    for t in me.loop_triangles:
        vs=t.vertices; ws=[WV[i] for i in vs]
        if max(ws)<=0: continue
        p=np.array([uv[l].uv[:] for l in t.loops])*(T-1)
        x0,y0=np.floor(p.min(0)).astype(int); x1,y1=np.ceil(p.max(0)).astype(int)
        xs,yy=np.meshgrid(np.arange(x0,x1+1),np.arange(y0,y1+1))
        (ax,ay),(bx,by),(cx,cy)=p; den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
        if abs(den)<1e-12: continue
        l1=((by-cy)*(xs-cx)+(cx-bx)*(yy-cy))/den; l2=((cy-ay)*(xs-cx)+(ax-cx)*(yy-cy))/den; l3=1-l1-l2
        ins=(l1>=-0.002)&(l2>=-0.002)&(l3>=-0.002)
        if not ins.any(): continue
        X=xs[ins].clip(0,T-1); Y=yy[ins].clip(0,T-1); a,b,c=l1[ins],l2[ins],l3[ins]
        acc[Y,X,0]=a*PX[vs[0]]+b*PX[vs[1]]+c*PX[vs[2]]; acc[Y,X,1]=a*PY[vs[0]]+b*PY[vs[1]]+c*PY[vs[2]]
        wgt[Y,X]=a*ws[0]+b*ws[1]+c*ws[2]
    bpy.data.meshes.remove(me)
    m=wgt>0
    fx=acc[...,0][m]; fy=acc[...,1][m]
    # exclusion masks in photo space (mouth opening, eye openings)
    ex=np.ones_like(fx)
    mx,my,mrx,mry=mouth; d=((fx-mx)/mrx)**2+((fy-my)/mry)**2; ex*=np.clip((d-1)/0.6,0,1)
    for ec in (eyeR,eyeL):
        d=((fx-ec[0])/eyes_r[0])**2+((fy-ec[1])/eyes_r[1])**2; ex*=np.clip((d-1)/0.8,0,1)
    # hairmask: drop photo pixels that are hair (dark) so hair isn't painted onto skin
    ix=np.clip(fx.astype(int),0,PW-1); iy=np.clip(fy.astype(int),0,PH-1)
    Lp=gblur(L,2)[iy,ix]; ex*=np.clip((Lp-0.16)/0.08,0,1)
    # bilinear sample of de-lit photo
    x0=np.clip(np.floor(fx).astype(int),0,PW-2); y0=np.clip(np.floor(fy).astype(int),0,PH-2); tx=(fx-x0)[:,None]; ty=(fy-y0)[:,None]
    S=(dl[y0,x0]*(1-tx)*(1-ty)+dl[y0,x0+1]*tx*(1-ty)+dl[y0+1,x0]*(1-tx)*ty+dl[y0+1,x0+1]*tx*ty)
    # colour match photo samples to base in the blended region (mean & std per channel, weighted)
    w=(wgt[m]*ex)
    bvals=B[...,:3][m]
    ring=(wgt[m]>0.05)&(wgt[m]<0.45)&(ex>0.9)
    sel=w>0.6
    # photo colour at the same ring vs base colour at ring -> per-channel gain
    mu_s=S[ring].mean(0); mu_b=bvals[ring].mean(0); sd_s=1; sd_b=1
    gain=np.clip(sd_b/sd_s,0.6,1.6)*0+1.0   # keep photo contrast (detail); match mean only
    S=S*(mu_b/np.maximum(mu_s,1e-4))
    a=(np.clip(w,0,1)*strength)[:,None]
    out=B.copy(); vals=out[...,:3][m]; vals=vals*(1-a)+np.clip(S,0,1)*a; out[...,:3][m]=vals
    np.save(SCR+"skin4k_photo.npy", out.astype(np.float32))
    Wm=np.zeros((T,T),np.float32); Wm[m]=np.clip(w,0,1); np.save(SCR+"face_w.npy", Wm[::4,::4])
    return int(m.sum()), mu_s.tolist(), mu_b.tolist()
