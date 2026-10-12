import cv2,numpy as np
from PIL import Image
B=np.asarray(Image.open('../l3/a/bottle.webp')).astype(np.float32)
K=2  # work at twice the old resolution so the label text stays sharp on retina screens
B=cv2.resize(B,(B.shape[1]*K,B.shape[0]*K),interpolation=cv2.INTER_LANCZOS4)
rgb=B[...,:3][...,::-1].copy();al=np.clip(B[...,3],0,255);H,W=al.shape
cx,R=163.0*K,150.0*K
# 1. take the old label off: rebuild the glass between y0 and y1 column by column from the glass just above and below it
y0,y1=652*K,928*K
top=rgb[y0-8*K:y0].mean(0);bot=rgb[y1:y1+8*K].mean(0)
for y in range(y0,y1):
    k=(y-y0)/(y1-y0);rgb[y]=top*(1-k)+bot*k
rgb[y0:y1]=cv2.GaussianBlur(rgb[y0-4:y1+4],(0,0),sigmaX=.6,sigmaY=3*K)[4:-4]
# 2. the new label, wrapped on the cylinder: 60 degrees each side, flat proportions kept along the arc
F=cv2.imread('clean.png').astype(np.float32);M0=np.load('lab0.npy').astype(np.float32)
pm=np.deg2rad(60);Lw=2*R*pm;Lh=Lw*F.shape[0]/F.shape[1];yc=790.0*K;e=5.0*K
tw=int(Lw*1.15);th=int(tw*F.shape[0]/F.shape[1])
F=cv2.resize(F,(tw,th),interpolation=cv2.INTER_AREA);M0=cv2.resize(M0,(tw,th),interpolation=cv2.INTER_AREA)
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
s=np.clip((xx-cx)/R,-.9999,.9999);phi=np.arcsin(s)
u=(phi/pm+1)/2
ytop=yc-Lh/2+e*(1-np.cos(phi));ybot=yc+Lh/2+e*(1-np.cos(phi))
v=(yy-ytop)/(ybot-ytop)
lab=cv2.remap(F,(u*(tw-1)).astype(np.float32),(v*(th-1)).astype(np.float32),cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
m=cv2.remap(M0,(u*(tw-1)).astype(np.float32),(v*(th-1)).astype(np.float32),cv2.INTER_LINEAR,borderValue=0)
dx=R*np.sin(pm)-np.abs(xx-cx);dy=np.minimum(yy-ytop,ybot-yy)
a=np.clip(dx+.5,0,1)*np.clip(dy+.5,0,1)*m
# 3. light: the cylinder turns away (Lambert), a soft key from the left, the studio strip as a faint sheen
lam=.58+.42*np.cos(phi)**.9
key=1+.07*np.sin(phi*-1+.2)
spec=.10*np.exp(-((phi+.72)/.07)**2)+.05*np.exp(-((phi-.95)/.05)**2)
shade=(lam*key)[...,None]*np.array([.93,.955,.975],np.float32)
lab=lab*shade+255*spec[...,None]
# a hair of shadow just outside the label edge where it lifts off the glass
ring=np.clip(1-np.abs(dy+1.2*K)/(1.6*K),0,1)*(dx>0)*(dy<0)
rgb=rgb*(1-.25*ring[...,None])
out=rgb*(1-a[...,None])+lab*a[...,None]
out=np.clip(out,0,255)
Image.fromarray(np.dstack([out[...,::-1],al]).astype(np.uint8)).save('a/bottle.webp',quality=92,method=5)
bg=np.full_like(out,244);aa=al[...,None]/255;cv2.imwrite('bchk.jpg',(bg*(1-aa)+out*aa)[520*K:H].astype(np.uint8))
x0=cx-R*np.sin(pm);print('label on bottle: x',round(x0,1),'w',round(2*R*np.sin(pm),1),'y',round(yc-Lh/2,1),'h',round(Lh,1))
