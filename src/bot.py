import cv2,numpy as np
from PIL import Image
src=cv2.imread('/root/.claude/uploads/2286d1b8-feeb-5eef-b9bb-945a87594a0d/d08d3859-image.png')
H,W=src.shape[:2]
bl=cv2.GaussianBlur(src,(0,0),1.2)
hsv=cv2.cvtColor(bl,cv2.COLOR_BGR2HSV).astype(np.float32);s,v=hsv[...,1]/255,hsv[...,2]/255
bgc=((v>.80)&(s<.06)).astype(np.uint8)
m=np.zeros((H+2,W+2),np.uint8)
for p in [(2,2),(W-3,2),(2,H-3),(W-3,H-3),(2,H//2),(W-3,H//2)]:
    if bgc[p[1],p[0]]==1: cv2.floodFill(bgc,m,p,2)
fg=(bgc!=2).astype(np.uint8)
fg=cv2.morphologyEx(fg,cv2.MORPH_OPEN,np.ones((5,5),np.uint8))
n,cc,st,_=cv2.connectedComponentsWithStats(fg);k=1+np.argmax(st[1:,4]);fg=(cc==k).astype(np.uint8)
cn,_=cv2.findContours(fg,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);fg[:]=0;cv2.drawContours(fg,cn,-1,1,-1)
fg=cv2.erode(fg,np.ones((3,3),np.uint8))
x,y,w,h=cv2.boundingRect(fg);print('bottle bbox',x,y,w,h)
a=cv2.GaussianBlur(fg.astype(np.float32),(0,0),1.0)
# label bbox: bright pixels inside the bottle in the lower part
hs=cv2.cvtColor(src,cv2.COLOR_BGR2HSV).astype(np.float32)
lb=((hs[...,2]/255>.6)&(fg>0)).astype(np.uint8);lb[:int(H*.55)]=0
lb=cv2.morphologyEx(lb,cv2.MORPH_CLOSE,np.ones((25,25),np.uint8))
n,cc,st,_=cv2.connectedComponentsWithStats(lb);k=1+np.argmax(st[1:,4]);print('label bbox',st[k][:4])
pad=14;x0,y0,x1,y1=x-pad,y-pad,x+w+pad,y+h+pad
rgba=np.dstack([src[...,::-1],np.clip(a*255,0,255).astype(np.uint8)])[y0:y1,x0:x1]
print('crop',x0,y0,x1-x0,y1-y0)
Image.fromarray(rgba).save('a/bottle.webp',quality=90,method=5)
chk=np.full(rgba.shape[:2]+(3,),(200,120,220),np.uint8);al=rgba[...,3:]/255.;cv2.imwrite('botchk.jpg',(chk*(1-al)+rgba[...,2::-1]*al).astype(np.uint8)[::2,::2])
