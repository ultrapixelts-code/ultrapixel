import cv2,numpy as np
from PIL import Image
B=np.asarray(Image.open('../l3/a/bottle.webp')).astype(np.float32)   # RGBA, label already there (old art)
rgb=B[...,:3][...,::-1].copy();al=B[...,3]
H,W=al.shape
hsv=cv2.cvtColor(rgb.astype(np.uint8),cv2.COLOR_BGR2HSV);v=hsv[...,2].astype(np.float32)
br=(v>140)&(al>128);br[:600]=False;br[H-40:]=False
br=cv2.morphologyEx(br.astype(np.uint8),cv2.MORPH_CLOSE,np.ones((15,15),np.uint8))
cols=np.nonzero(br.sum(0)>150)[0];xl,xr=cols.min()+1,cols.max()-1
top=np.full(W,np.nan);bot=np.full(W,np.nan)
for x in range(xl,xr+1):
    r=np.nonzero(br[:,x])[0]
    if len(r): top[x]=r.min();bot[x]=r.max()
xs=np.arange(int(xl+.15*(xr-xl)),int(xr-.15*(xr-xl)))
# robust edges from the middle columns: median-filter the raw edges first
from scipy.ndimage import median_filter
top=median_filter(np.nan_to_num(top,nan=np.nanmedian(top)),31);bot=median_filter(np.nan_to_num(bot,nan=np.nanmedian(bot)),31)
pt=np.polyfit(xs,top[xs],2);pb=np.polyfit(xs,bot[xs],2)
T=np.polyval(pt,np.arange(W));Bo=np.polyval(pb,np.arange(W))
print('label cols',xl,xr,'top',T[[xl,(xl+xr)//2,xr]].round(1),'bot',Bo[[xl,(xl+xr)//2,xr]].round(1))
cx=(xl+xr)/2;hw=(xr-xl)/2;R=hw*1.04;pm=np.arcsin(hw/R)
F=cv2.imread('clean.png').astype(np.float32);lab0=np.load('lab0.npy').astype(np.float32)
x0,y0,w0,h0=cv2.boundingRect(lab0.astype(np.uint8))
F=F[y0:y0+h0,x0:x0+w0];M0=lab0[y0:y0+h0,x0:x0+w0]
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
t=np.clip((xx-cx)/R,-.999,.999);u=(np.arcsin(t)/pm+1)/2
vv=(yy-T[None,:])/(Bo-T)[None,:]
mx=(u*(w0-1)).astype(np.float32);my=(vv*(h0-1)).astype(np.float32)
inside=(xx>=xl)&(xx<=xr)&(vv>=0)&(vv<=1)
warped=cv2.remap(F,mx,my,cv2.INTER_AREA if False else cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
wm=cv2.remap(M0,mx,my,cv2.INTER_LINEAR,borderValue=0)*inside
# cylinder shading from the original label: per-column brightness profile
colv=np.array([np.median(v[int(T[x])+4:int(Bo[x])-4,x]) if xl<=x<=xr else np.nan for x in range(W)])
ok=~np.isnan(colv);colv=np.interp(np.arange(W),np.nonzero(ok)[0],colv[ok]);colv=cv2.GaussianBlur(colv[None,:].astype(np.float32),(0,0),6)[0]
shade=np.clip(colv/np.percentile(colv[xl:xr],90),0,1.05)
lab_rgb=warped*shade[None,:,None]*np.array([.92,.955,.975],np.float32)
# corners outside the chamfer: glass, taken from just above the label
glass=np.zeros_like(rgb)
for x in range(W):
    ya=int(max(0,np.nan_to_num(T[x],nan=0)-8));glass[:,x]=rgb[ya,x]
inside_f=inside.astype(np.float32)
a=wm[...,None]
out=rgb*(1-inside_f[...,None])+inside_f[...,None]*(lab_rgb*a+glass*(1-a))
out=np.clip(out,0,255)
Image.fromarray(np.dstack([out[...,::-1],al]).astype(np.uint8)).save('a/bottle.webp',quality=90,method=5)
bg=np.full_like(out,240);aa=al[...,None]/255;cv2.imwrite('bchk.jpg',(bg*(1-aa)+out*aa)[560:H].astype(np.uint8))
print('bottle',W,H,'label box',xl,int(T.min()),xr-xl,int(Bo.max()-T.min()))
