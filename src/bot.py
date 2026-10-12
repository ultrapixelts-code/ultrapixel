import cv2,numpy as np
from PIL import Image
im=cv2.imread('/root/.claude/uploads/2286d1b8-feeb-5eef-b9bb-945a87594a0d/c7302cce-image.png')
P=im[:, :735].copy()
H,W=P.shape[:2]
mask=np.full((H,W),cv2.GC_BGD,np.uint8)
# probable bottle: a column band; sure-fg along the axis
mask[0:1020,180:560]=cv2.GC_PR_BGD
mask[10:990,205:530]=cv2.GC_PR_FGD
mask[40:960,330:400]=cv2.GC_FGD
mask[650:960,230:500]=cv2.GC_FGD
bg=np.zeros((1,65),np.float64);fg=np.zeros((1,65),np.float64)
cv2.grabCut(P,mask,None,bg,fg,8,cv2.GC_INIT_WITH_MASK)
fgm=((mask==1)|(mask==3)).astype(np.uint8)
n,cc,st,_=cv2.connectedComponentsWithStats(fgm);k=1+np.argmax(st[1:,4]);fgm=(cc==k).astype(np.uint8)
fgm=cv2.morphologyEx(fgm,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
# symmetrise: bottle is vertical & symmetric -> use per-row width from the mask, centred on the axis
ys,xs=np.nonzero(fgm);print('bbox',xs.min(),xs.max(),ys.min(),ys.max())
cv2.imwrite('fgm.png',fgm*255)
chk=P.copy();chk[fgm==0]=(200,120,220);cv2.imwrite('botchk.jpg',chk[:, 150:600])
# symmetric silhouette from the grabcut mask
c=np.nonzero(fgm.any(1))[0];y0,y1=c.min(),c.max()
L_=np.array([np.nonzero(fgm[y])[0].min() if fgm[y].any() else -1 for y in range(H)]);R_=np.array([np.nonzero(fgm[y])[0].max() if fgm[y].any() else -1 for y in range(H)])
rows=np.arange(y0+5,y1-5);cx=np.median((L_[rows]+R_[rows])/2.0);print('axis',cx)
hw=np.minimum(cx-L_,R_-cx).astype(np.float32);hw[(L_<0)]=0
hw=np.convolve(np.where(hw>0,hw,0),np.ones(5)/5,'same')
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
sil=np.clip(hw[:,None]-np.abs(xx-cx)+.5,0,1)
sil[:y0]=0;sil[y1+1:]=0
# remove the appellation and side texts on the bottle label
img=P.copy()
for (a,b,c2,d) in [(290,672,420,700),(205,762,262,806),(455,762,515,806)]:
    reg=img[b:d,a:c2];hv=cv2.cvtColor(reg,cv2.COLOR_BGR2HSV)
    vv=hv[...,2].astype(np.int16);md=cv2.medianBlur(hv[...,2],15).astype(np.int16)
    mk=cv2.dilate((vv<md-20).astype(np.uint8),np.ones((3,3),np.uint8))
    img[b:d,a:c2]=cv2.inpaint(reg,mk,4,cv2.INPAINT_TELEA)
pad=12;xa,xb=int(cx-hw.max()-pad),int(cx+hw.max()+pad);ya,yb=max(0,y0-pad),min(H,y1+pad)
rgba=np.dstack([img[...,::-1],(sil*255).astype(np.uint8)])[ya:yb,xa:xb]
Image.fromarray(rgba).save('a/bottle.webp',quality=90,method=5)
print('crop',xa,ya,xb-xa,yb-ya)
# label box on the bottle (bright paper rows/cols in the lower part)
hs=cv2.cvtColor(P,cv2.COLOR_BGR2HSV);br=(hs[...,2]>150)&(sil>.5);br[:600]=False
r=np.nonzero(br.sum(1)>80)[0];cc_=np.nonzero(br.sum(0)>80)[0];print('label rows',r.min(),r.max(),'cols',cc_.min(),cc_.max())
ch=np.full(rgba.shape[:2]+(3,),(200,120,220),np.float32);al=rgba[...,3:]/255.;cv2.imwrite('botchk2.jpg',(ch*(1-al)+rgba[...,2::-1]*al).astype(np.uint8))
