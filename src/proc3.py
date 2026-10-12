import cv2,numpy as np
from PIL import Image
f=cv2.imread('flat.png')[:,96:1440].astype(np.float32)        # unwarped label, label edges trimmed
h0,w0=f.shape[:2]
hsv=cv2.cvtColor(f.astype(np.uint8),cv2.COLOR_BGR2HSV).astype(np.float32);s,v=hsv[...,1]/255,hsv[...,2]/255
# even out the cylinder shading: per-column gain from plain paper pixels
pp=(s<.16)&(v>.6)
col=np.array([np.median(v[pp[:,x],x]) if pp[:,x].sum()>40 else np.nan for x in range(w0)])
col=np.interp(np.arange(w0),np.arange(w0)[~np.isnan(col)],col[~np.isnan(col)]);col=cv2.GaussianBlur(col[None,:].astype(np.float32),(0,0),25)[0]
gain=np.median(col[w0//3:2*w0//3])/col
f=np.clip(f*gain[None,:,None],0,255)
# remove the appellation and the side texts (no protected name, no unverified sustainability claim on a demo label)
def rel(x0,y0,x1,y1):return int(x0*w0/1152*1536/1536*1152/1152) ,0
img=f.astype(np.uint8)
S=w0/1344.
boxes=[(530,30,1010,92),(125,305,285,425),(1265,305,1440,425)]   # in flat.png coordinates (x before trim) at 1536 width
for (x0,y0,x1,y1) in boxes:
    x0-=96;x1-=96;x0=max(0,x0);x1=min(w0,x1)
    reg=img[y0:y1,x0:x1];hv=cv2.cvtColor(reg,cv2.COLOR_BGR2HSV)
    vv=hv[...,2].astype(np.int16);md=cv2.medianBlur(hv[...,2],31).astype(np.int16);ss=hv[...,1].astype(np.int16);ms=cv2.medianBlur(hv[...,1],31).astype(np.int16)
    mk=((vv<md-22)|(ss>ms+30)).astype(np.uint8)
    mk=cv2.dilate(mk,np.ones((5,5),np.uint8))
    out=cv2.inpaint(reg,mk,6,cv2.INPAINT_TELEA).astype(np.float32)
    rng=np.random.default_rng(2);n=cv2.GaussianBlur(rng.normal(0,1,reg.shape[:2]).astype(np.float32),(0,0),.9)*4
    img[y0:y1,x0:x1]=np.clip(out+n[...,None]*(mk[...,None]>0),0,255).astype(np.uint8)
cv2.imwrite('clean.png',img)
# place on the 1500x1000 canvas with a rounded-rectangle die
OW,OH=1500,1000;LW,LH=1340,int(round(1340*h0/w0));ox,oy=(OW-LW)//2,(OH-LH)//2
lab_img=cv2.resize(img,(LW,LH),interpolation=cv2.INTER_AREA)
src=np.full((OH,OW,3),255,np.uint8);src[oy:oy+LH,ox:ox+LW]=lab_img
lab=np.zeros((OH,OW),np.uint8);r=22
cv2.rectangle(lab,(ox+r,oy),(ox+LW-1-r,oy+LH-1),1,-1);cv2.rectangle(lab,(ox,oy+r),(ox+LW-1,oy+LH-1-r),1,-1)
for cx,cy in [(ox+r,oy+r),(ox+LW-1-r,oy+r),(ox+r,oy+LH-1-r),(ox+LW-1-r,oy+LH-1-r)]:cv2.circle(lab,(cx,cy),r,1,-1)
print('label box',ox,oy,LW,LH)
H,W=OH,OW;L=lab.astype(bool)
hsv=cv2.cvtColor(src,cv2.COLOR_BGR2HSV).astype(np.float32);h,s,v=hsv[...,0],hsv[...,1]/255,hsv[...,2]/255
yy,xx=np.mgrid[0:H,0:W]
loose=L&(h>9)&(h<32)&(s>.28)&(v>.25)
strict=L&(h>9)&(h<32)&(s>.42)&(v>.3)
n,cc,st,_=cv2.connectedComponentsWithStats(loose.astype(np.uint8),connectivity=8)
cnt=np.bincount(cc[strict],minlength=n);keep=(cnt/np.maximum(st[:,4],1)>.25)&(st[:,4]>15);keep[0]=False
gold=keep[cc]
# the sun is foil all over, its shaded side included
sc=(gold&(abs(xx-750)<200)&(abs(yy-650)<200));sy,sx=np.nonzero(sc);cxs,cys=np.median(sx),np.median(sy)
disk=((xx-cxs)**2+(yy-cys)**2)<(1.15*np.sqrt(sc.sum()/np.pi))**2
gold|=disk&L&((s>.2)|(v<.5));print('sun',cxs,cys)
# relief letters: the dark parts of the name
nb=np.zeros((H,W),bool);nb[oy+int(.13*LH):oy+int(.33*LH),ox+int(.08*LW):ox+int(.92*LW)]=True
dark=L&(v<.42)&~gold
screen=cv2.morphologyEx((dark&nb).astype(np.uint8),cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))>0
n,cc,st,_=cv2.connectedComponentsWithStats(screen.astype(np.uint8));screen[:]=False
for i in range(1,n):
    if st[i,4]>250: screen|=(cc==i)
# digital print = everything inked that is neither foil nor relief: landscape greens/teals, line work, text
def soft(mk,d=3,b=1.0):
    a=cv2.dilate(mk.astype(np.uint8),np.ones((d,d),np.uint8)).astype(np.float32);return cv2.GaussianBlur(a,(0,0),b)
ga=soft(gold);sa=soft(screen,3,1.0)
pm=(L&~gold&~screen&(s<.2)&(v>.6)).astype(np.float32)
def nc(sig):
    wgt=cv2.GaussianBlur(pm,(0,0),sig);return [cv2.GaussianBlur(src[...,c].astype(np.float32)*pm,(0,0),sig)/(wgt+1e-6) for c in range(3)],wgt
f1,w1=nc(260);f3=[np.full((H,W),np.median(src[...,c][pm>0])) for c in range(3)];t1=np.clip(w1/.05,0,1)
field=np.dstack([t1*f1[c]+(1-t1)*f3[c] for c in range(3)])
fh=cv2.cvtColor(np.clip(field,0,255).astype(np.uint8),cv2.COLOR_BGR2HSV).astype(np.float32);fs,fv=fh[...,1]/255,fh[...,2]/255
ink=L&~gold&~screen&((v<fv*.8)|(s>fs+.12))
ink=cv2.morphologyEx(ink.astype(np.uint8),cv2.MORPH_OPEN,np.ones((2,2),np.uint8))>0
up=yy<oy+int(.40*LH);ink&=~up|(v<fv*.7)|(s>fs+.18)
n,cc,st,_=cv2.connectedComponentsWithStats(ink.astype(np.uint8));ok=st[:,4]>=25;ok[0]=False;ink=ok[cc]
ia=soft(ink,2,.8)
rng=np.random.default_rng(3)
g=cv2.GaussianBlur(rng.normal(0,1,(H,W)).astype(np.float32),(0,0),.9)*2.2+cv2.GaussianBlur(rng.normal(0,1,(H,W)).astype(np.float32),(0,0),5)*6
fib=cv2.GaussianBlur(rng.normal(0,1,(H,W)).astype(np.float32),(0,0),sigmaX=7,sigmaY=.7)*2.5
paper=np.clip(field*(1+(g+fib)[...,None]*.012),0,255).astype(np.uint8)
la=cv2.GaussianBlur(lab.astype(np.float32),(0,0),.8)
def save(name,bgr,a,q=86):
    rgba=np.dstack([bgr[...,::-1],np.clip(a*255,0,255).astype(np.uint8)]);Image.fromarray(rgba).save('a/'+name,quality=q,method=5)
# relief layer: dense colour, bevel highlight, soft sheen
scm=screen.astype(np.float32)
bev=cv2.GaussianBlur(np.clip(scm-np.roll(np.roll(scm,3,0),3,1),0,1),(0,0),1.1)
shd=cv2.GaussianBlur(np.clip(scm-np.roll(np.roll(scm,-3,0),-3,1),0,1),(0,0),1.2)
sheen=(.5+.5*np.sin((xx*.9+yy*1.7)/46.0))**6
scr=np.clip(src.astype(np.float32)*.85+np.array([150,190,170.])*(bev*.7+sheen*.14*scm)[...,None]-55*shd[...,None],0,255).astype(np.uint8)
Image.fromarray(paper[...,::-1]).save('a/sheet.jpg',quality=84)
save('paper.webp',paper,la);save('matrix.webp',paper,1-la)
save('gold.webp',src,ga*la);save('screen.webp',scr,sa*la);save('final.webp',src,la,90)
cnts,_=cv2.findContours(lab,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);c=cv2.approxPolyDP(max(cnts,key=cv2.contourArea),1.0,True)[:,0]
open('a/die.txt','w').write('M'+' L'.join(f'{p[0]},{p[1]}' for p in c)+' Z');print('pts',len(c))
def over(b,f,a):a=a[...,None];return (b*(1-a)+f*a)
srcf=src.astype(np.float32)
och=cv2.GaussianBlur(srcf,(0,0),3)*.25+np.array([78,150,190.])*.75
dk=np.array([src[...,c][screen].mean() for c in range(3)])
P=over(paper.astype(np.float32),och,ga*la)
P=over(P,cv2.GaussianBlur(srcf,(0,0),.8),ia*la)
P=over(P,(np.broadcast_to(dk,(H,W,3))*.42+paper*.58).astype(np.float32),sa*la)
ratio=np.clip(P/np.maximum(paper.astype(np.float32),1),0,1)[...,::-1]
k=1-ratio.max(2);d=np.maximum(1-k,1e-3);cmy=np.clip((1-ratio-k[...,None])/d[...,None],0,1);one=np.ones_like(k)
def sv(name,rgb):Image.fromarray((np.clip(np.dstack(rgb),0,1)*255).astype(np.uint8)).resize((1125,750),Image.LANCZOS).save('a/'+name,quality=82)
sv('sepC.jpg',[1-cmy[...,0],one,one]);sv('sepM.jpg',[one,1-cmy[...,1],one]);sv('sepY.jpg',[one,one,1-cmy[...,2]]);sv('sepK.jpg',[1-k,1-k,1-k])
s0=paper.astype(np.float32);s2=over(P,srcf,ga*la);s3=over(s2,scr.astype(np.float32),sa*la);s4=over(s3,srcf,la)
cv2.imwrite('states.jpg',np.vstack([np.hstack([s0,P]),np.hstack([s2,s3]),np.hstack([s4,srcf])]).astype(np.uint8)[::2,::2])
