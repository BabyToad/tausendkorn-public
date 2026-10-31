"""Dev-only perturbation test (blur / perspective / scale), after Fable's audit script.

    W=models/yolo11s-blur.pt CONF=0.4 TAG=blur uv run --group gpu python -m tausendkorn.gpu.perturb base blur_s3
"""
import json, sys, numpy as np, cv2
from ultralytics import YOLO
from tausendkorn.eval import load_split, load_image
from tausendkorn.match import match
from tausendkorn.gpu.yolo import tiles, TILE
import os; W_=os.environ["W"]; CONF=float(os.environ.get("CONF","0.4"))
model=YOLO(W_)
tr={r["file_name"]:r for r in load_split("train")}
names=open("splits/dev.txt").read().split()
def count(arr):
    H,W=arr.shape[:2]; grid=tiles(W,H); xs=sorted({x for x,_ in grid}); ys=sorted({y for _,y in grid}); pts=[]
    for tx,ty in grid:
        i,j=xs.index(tx),ys.index(ty)
        cx0=0 if i==0 else (xs[i-1]+TILE+tx)/2; cx1=W if i==len(xs)-1 else (tx+TILE+xs[i+1])/2
        cy0=0 if j==0 else (ys[j-1]+TILE+ty)/2; cy1=H if j==len(ys)-1 else (ty+TILE+ys[j+1])/2
        res=model.predict(arr[ty:ty+TILE,tx:tx+TILE,::-1],imgsz=TILE,conf=CONF,max_det=1000,verbose=False)[0]
        for (x0,y0,x1,y1),cls in zip(res.boxes.xyxy.tolist(),res.boxes.cls.tolist()):
            gx,gy=tx+(x0+x1)/2,ty+(y0+y1)/2
            if cx0<=gx<cx1 and cy0<=gy<cy1 and int(cls)==0: pts.append([gx,gy])
    return pts
def persp(arr, pts, top=0.6):
    """Keystone: top edge shrunk to `top` of width (camera tilted), bottom unchanged, same canvas."""
    H,W=arr.shape[:2]; m=(1-top)/2*W
    src=np.float32([[0,0],[W,0],[W,H],[0,H]]); dst=np.float32([[m,0],[W-m,0],[W,H],[0,H]])
    Hm=cv2.getPerspectiveTransform(src,dst)
    out=cv2.warpPerspective(arr,Hm,(W,H),borderValue=(20,20,20))
    p=cv2.perspectiveTransform(np.float32(pts).reshape(-1,1,2),Hm).reshape(-1,2).tolist()
    return out,p
def scale(arr,pts,s):
    out=cv2.resize(arr,None,fx=s,fy=s,interpolation=cv2.INTER_AREA); return out,(np.array(pts)*s).tolist()
conds={
 "base": lambda a,p:(a,p),
 "blur_s2": lambda a,p:(cv2.GaussianBlur(a,(0,0),2),p),
 "blur_s3": lambda a,p:(cv2.GaussianBlur(a,(0,0),3),p),
 "blur_s4": lambda a,p:(cv2.GaussianBlur(a,(0,0),4),p),
 "persp_0.6": lambda a,p:persp(a,p,0.6),
 "persp_0.45": lambda a,p:persp(a,p,0.45),
 "scale_0.7": lambda a,p:scale(a,p,0.7),
 "scale_0.55": lambda a,p:scale(a,p,0.55),
 "scale_1.4": lambda a,p:scale(a,p,1.4),
 "persp_0.45_up1.5": lambda a,p:scale(*persp(a,p,0.45),1.5),
}
sel=sys.argv[1:] or list(conds)
res={}
for c in sel:
    errs=[];tp=fp=fn=0
    for n in names:
        r=tr[n]; arr=np.asarray(load_image(r["path"])); a,p=conds[c](arr,r["kernel_points"])
        pts=count(a); m=match(pts,p); e=len(pts)-r["count"]; errs.append(e); tp+=m["tp"];fp+=m["fp"];fn+=m["fn"]
    errs=np.array(errs)
    res[c]=dict(sum=int(errs.sum()),mae=float(np.abs(errs).mean()),bias=float(errs.mean()),max=int(np.abs(errs).max()),P=tp/max(tp+fp,1),R=tp/max(tp+fn,1),errs=errs.tolist())
    print(c, {k:(round(v,3) if isinstance(v,float) else v) for k,v in res[c].items() if k!="errs"}, flush=True)
json.dump(res,open("runs/blur_eval/"+os.environ.get("TAG","run")+".json","w"),indent=1)
