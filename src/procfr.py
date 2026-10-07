import cv2,numpy as np
from PIL import Image
src=cv2.imread('/root/.claude/uploads/2286d1b8-feeb-5eef-b9bb-945a87594a0d/0de02281-image.png')
# remove the appellation and origin lines (no protected-name or origin claim on a demo label)
for (x0,y0,x1,y1) in [(455,296,1085,400),(610,826,925,868)]:
    reg=src[y0:y1,x0:x1];hv=cv2.cvtColor(reg,cv2.COLOR_BGR2HSV)
    mk=((hv[...,2]<150)&((hv[...,0]>35)|(hv[...,1]<70))).astype(np.uint8)
    mk=cv2.dilate(mk,np.ones((7,7),np.uint8))
    out=cv2.inpaint(reg,mk,5,cv2.INPAINT_TELEA)
    rng=np.random.default_rng(1);n=cv2.GaussianBlur(rng.normal(0,1,reg.shape[:2]).astype(np.float32),(0,0),.8)*3
    out=np.clip(out.astype(np.float32)+n[...,None]*(mk[...,None]>0),0,255).astype(np.uint8)
    src[y0:y1,x0:x1]=out
cv2.imwrite('src_patched.png',src)
src=cv2.copyMakeBorder(src,200,200,200,200,cv2.BORDER_CONSTANT,value=(255,255,255))
H,W=src.shape[:2]
hsv=cv2.cvtColor(src,cv2.COLOR_BGR2HSV).astype(np.float32);s,v=hsv[...,1]/255,hsv[...,2]/255
bg=((v>.93)&(s<.05)).astype(np.uint8);m=np.zeros((H+2,W+2),np.uint8);cv2.floodFill(bg,m,(2,2),2)
lab=(bg!=2).astype(np.uint8)
lab=cv2.morphologyEx(lab,cv2.MORPH_OPEN,np.ones((7,7),np.uint8))
n,cc,st,_=cv2.connectedComponentsWithStats(lab);k=1+np.argmax(st[1:,4]);lab=(cc==k).astype(np.uint8)
cnts,_=cv2.findContours(lab,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);lab[:]=0;cv2.drawContours(lab,cnts,-1,1,-1)
lab=cv2.erode(lab,np.ones((3,3),np.uint8))
x,y,w,hh=cv2.boundingRect(lab);pad=int(w*.04);OW,OH=1500,1000
cw,ch=w+2*pad,hh+2*pad
if cw/ch<OW/OH: cw=int(ch*OW/OH)
else: ch=int(cw*OH/OW)
x0=x+w//2-cw//2;y0=y+hh//2-ch//2;print('crop',x0,y0,cw,ch,H,W)
src=cv2.resize(src[y0:y0+ch,x0:x0+cw],(OW,OH),interpolation=cv2.INTER_AREA)
lab=(cv2.resize(lab[y0:y0+ch,x0:x0+cw],(OW,OH),interpolation=cv2.INTER_AREA)>0).astype(np.uint8)
H,W=lab.shape
hsv=cv2.cvtColor(src,cv2.COLOR_BGR2HSV).astype(np.float32);h,s,v=hsv[...,0],hsv[...,1]/255,hsv[...,2]/255
cnts,_=cv2.findContours(lab,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
L=lab.astype(bool)
gold=L&(h>8)&(h<34)&(((s>.30)&(v>.2))|((s>.55)&(v>.12)))
strict=L&(h>8)&(h<34)&(s>.45)&(v>.15)
n,cc,st,_=cv2.connectedComponentsWithStats(gold.astype(np.uint8),connectivity=8)
cnt=np.bincount(cc[strict],minlength=n);keep=(cnt/np.maximum(st[:,4],1)>.3)&(st[:,4]>12);keep[0]=False
gold=keep[cc]
ink=L&(v<.52)&~gold
# screen relief = the house name
box=np.zeros((H,W),bool);box[int(.40*H):int(.60*H),int(.22*W):int(.78*W)]=True
yy,xx=np.mgrid[0:H,0:W];med=((xx-752)**2+(yy-163)**2)<122**2      # the medallion ground is screen-printed too
screen=cv2.morphologyEx((ink&(box|med)).astype(np.uint8),cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))>0
n,cc,st,cen=cv2.connectedComponentsWithStats(screen.astype(np.uint8));screen[:]=False
for i in range(1,n):
    if st[i,4]>600: screen|=(cc==i)
def soft(mk,d=3,b=1.0):
    a=cv2.dilate(mk.astype(np.uint8),np.ones((d,d),np.uint8)).astype(np.float32);return cv2.GaussianBlur(a,(0,0),b)
ga=soft(gold);sa=soft(screen,3,1.0);ia=soft(ink&~screen,2,.8)
# flat paper (no emboss): smooth colour field from plain paper pixels + grain
pm=(L&~gold&~ink&(s<.22)&(v>.74)).astype(np.float32)
def nc(sig):
    wgt=cv2.GaussianBlur(pm,(0,0),sig);return [cv2.GaussianBlur(src[...,c].astype(np.float32)*pm,(0,0),sig)/(wgt+1e-6) for c in range(3)],wgt
f1,w1=nc(90);f3=[np.full((H,W),np.median(src[...,c][pm>0])) for c in range(3)]
t1=np.clip(w1/.05,0,1)
field=np.dstack([t1*f1[c]+(1-t1)*f3[c] for c in range(3)])
rng=np.random.default_rng(3)
g=cv2.GaussianBlur(rng.normal(0,1,(H,W)).astype(np.float32),(0,0),.9)*2.2+cv2.GaussianBlur(rng.normal(0,1,(H,W)).astype(np.float32),(0,0),5)*6
fib=cv2.GaussianBlur(rng.normal(0,1,(H,W)).astype(np.float32),(0,0),sigmaX=7,sigmaY=.7)*2.5
paper=np.clip(field*(1+(g+fib)[...,None]*.012),0,255).astype(np.uint8)
la=cv2.GaussianBlur(lab.astype(np.float32),(0,0),.8)
def save(name,bgr,a,q=86):
    rgba=np.dstack([bgr[...,::-1],np.clip(a*255,0,255).astype(np.uint8)]);Image.fromarray(rgba).save('a/'+name,quality=q,method=5)
Image.fromarray(paper[...,::-1]).save('a/sheet.jpg',quality=84)
save('paper.webp',paper,la);save('matrix.webp',paper,1-la)
scm=screen.astype(np.float32)
bev=np.clip(scm-np.roll(np.roll(scm,3,0),3,1),0,1);bev=cv2.GaussianBlur(bev,(0,0),1.1)          # light catching the top-left edges
shd=np.clip(scm-np.roll(np.roll(scm,-3,0),-3,1),0,1);shd=cv2.GaussianBlur(shd,(0,0),1.2)
sheen=(.5+.5*np.sin((xx*.9+yy*1.7)/46.0))**6
scr=src.astype(np.float32)*.82+np.array([150,190,170.])*(bev*.75+sheen*.16*scm)[...,None]-60*shd[...,None]
scr=np.clip(scr,0,255).astype(np.uint8)
save('gold.webp',src,ga*la);save('screen.webp',scr,sa*la);save('final.webp',src,la,90)
c=max(cnts,key=cv2.contourArea);c=cv2.approxPolyDP(c,1.2,True)[:,0]
open('a/die.txt','w').write('M'+' L'.join(f'{p[0]},{p[1]}' for p in c)+' Z');print('pts',len(c))
def over(b,f,a):a=a[...,None];return (b*(1-a)+f*a)
# digital print: everything solid first — inks as they are, gold areas as flat ochre, house name as flat dark green
srcf=src.astype(np.float32)
och=cv2.GaussianBlur(srcf,(0,0),3)*.25+np.array([78,150,190.])*.75
dk=np.array([src[...,c][screen].mean() for c in range(3)])*.95
flatink=cv2.GaussianBlur(srcf,(0,0),1.2)
P=over(paper.astype(np.float32),och,ga*la)
P=over(P,flatink,ia*la)
P=over(P,(np.broadcast_to(dk,(H,W,3))*.42+paper*.58).astype(np.float32),sa*la)   # printed as a light flat base; the screen pass makes it dense
cv2.imwrite('pflat.jpg',P.astype(np.uint8))
ratio=np.clip(P/np.maximum(paper.astype(np.float32),1),0,1)[...,::-1]
k=1-ratio.max(2);d=np.maximum(1-k,1e-3);cmy=np.clip((1-ratio-k[...,None])/d[...,None],0,1)
one=np.ones_like(k)
def sv(name,rgb):Image.fromarray((np.clip(np.dstack(rgb),0,1)*255).astype(np.uint8)).resize((1125,750),Image.LANCZOS).save('a/'+name,quality=82)
sv('sepC.jpg',[1-cmy[...,0],one,one]);sv('sepM.jpg',[one,1-cmy[...,1],one]);sv('sepY.jpg',[one,one,1-cmy[...,2]]);sv('sepK.jpg',[1-k,1-k,1-k])
s0=paper.astype(np.float32);s1=P;s2=over(s1,srcf,ga*la);s3=over(s2,scr.astype(np.float32),sa*la);s4=over(s3,srcf,la)
cv2.imwrite('states.jpg',np.vstack([np.hstack([s0,s1,s2]),np.hstack([s3,s4,srcf])]).astype(np.uint8)[::2,::2])
