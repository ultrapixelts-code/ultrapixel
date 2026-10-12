import cv2,numpy as np
src=cv2.imread('/root/.claude/uploads/2286d1b8-feeb-5eef-b9bb-945a87594a0d/a8dfb0c3-image.png').astype(np.float32)
H,W=src.shape[:2]
tb=np.load('tb.npy');xs=np.arange(W)
def fit(row,lo,hi,cands):
    pts=[(x,row[x]) for x in cands if not np.isnan(row[x]) and lo<row[x]<hi]
    X=np.array([p[0] for p in pts]);Y=np.array([p[1] for p in pts]);return np.polyfit(X,Y,2),X,Y
cands=list(range(60,700,8))+list(range(1300,1480,8))
pt,X,Y=fit(tb[0],15,140,cands);pb,X2,Y2=fit(tb[1],900,980,cands)
top=np.polyval(pt,xs);bot=np.polyval(pb,xs)
print('top',top[[0,384,768,1152,1535]].round(1),'bot',bot[[0,384,768,1152,1535]].round(1))
m=10;OH=900
top+=m;bot-=m
yy=np.linspace(0,1,OH)[:,None]
mapy=(top[None,:]+(bot-top)[None,:]*yy).astype(np.float32)
mapx=np.repeat(xs[None,:].astype(np.float32),OH,0)
out=cv2.remap(src,mapx,mapy,cv2.INTER_CUBIC)
cv2.imwrite('flat.png',np.clip(out,0,255).astype(np.uint8))
