import cv2,numpy as np
from PIL import Image
from grade import grade
src0=cv2.imread('/root/.claude/uploads/2286d1b8-feeb-5eef-b9bb-945a87594a0d/8c01d784-image.png')
h0,w0=src0.shape[:2]
# --- label outline: flood the grey surround from the image border
hv=cv2.cvtColor(cv2.GaussianBlur(src0,(0,0),2),cv2.COLOR_BGR2HSV).astype(np.float32)
bgc=((hv[...,2]<182)&(hv[...,1]<90)).astype(np.uint8)
m=np.zeros((h0+2,w0+2),np.uint8)
for x in range(0,w0,40):
    for y in (1,h0-2):
        if bgc[y,x]==1: cv2.floodFill(bgc,m,(x,y),2)
for y in range(0,h0,40):
    for x in (1,w0-2):
        if bgc[y,x]==1: cv2.floodFill(bgc,m,(x,y),2)
lab0=(bgc!=2).astype(np.uint8)
lab0=cv2.morphologyEx(lab0,cv2.MORPH_OPEN,np.ones((5,5),np.uint8))
n,cc,st,_=cv2.connectedComponentsWithStats(lab0);k=1+np.argmax(st[1:,4]);lab0=(cc==k).astype(np.uint8)
cn,_=cv2.findContours(lab0,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
poly=cv2.approxPolyDP(max(cn,key=cv2.contourArea),3.0,True)
lab0[:]=0;cv2.fillPoly(lab0,[poly],1);lab0=cv2.erode(lab0,np.ones((3,3),np.uint8))
x,y,w,h=cv2.boundingRect(lab0);print('label',x,y,w,h,'poly pts',len(poly))
# --- remove the appellation and side texts
img=src0.copy()
for (a,b,c,d) in [(520,40,1020,95),(100,350,300,460),(1240,350,1460,460)]:
    reg=img[b:d,a:c];hs=cv2.cvtColor(reg,cv2.COLOR_BGR2HSV)
    vv=hs[...,2].astype(np.int16);md=cv2.medianBlur(hs[...,2],31).astype(np.int16);ss=hs[...,1].astype(np.int16);ms=cv2.medianBlur(hs[...,1],31).astype(np.int16)
    mk=cv2.dilate(((vv<md-22)|(ss>ms+30)).astype(np.uint8),np.ones((5,5),np.uint8))
    out=cv2.inpaint(reg,mk,6,cv2.INPAINT_TELEA).astype(np.float32)
    rng=np.random.default_rng(2);nz=cv2.GaussianBlur(rng.normal(0,1,reg.shape[:2]).astype(np.float32),(0,0),.9)*4
    img[b:d,a:c]=np.clip(out+nz[...,None]*(mk[...,None]>0),0,255).astype(np.uint8)
img=grade(img,lab0.astype(bool),target=(234,241,246))
cv2.imwrite('clean.png',img);np.save('lab0.npy',lab0)
# --- onto the 1500x1000 canvas
OW,OH=1500,1000;sc=1360/w;LW,LH=int(round(w*sc)),int(round(h*sc));ox,oy=(OW-LW)//2,(OH-LH)//2
M=np.float32([[sc,0,ox-x*sc],[0,sc,oy-y*sc]])
src=cv2.warpAffine(img,M,(OW,OH),flags=cv2.INTER_AREA,borderValue=(255,255,255))
lab=(cv2.warpAffine(lab0.astype(np.float32),M,(OW,OH),flags=cv2.INTER_LINEAR)>.5).astype(np.uint8)
print('canvas label',ox,oy,LW,LH)
open('box.txt','w').write(f'{ox} {oy} {LW} {LH}')
H,W=OH,OW;L=lab.astype(bool)
hsv=cv2.cvtColor(src,cv2.COLOR_BGR2HSV).astype(np.float32);h,s,v=hsv[...,0],hsv[...,1]/255,hsv[...,2]/255
yy,xx=np.mgrid[0:H,0:W]
loose=L&(h>8)&(h<30)&(s>.36)&(v>.25)
strict=L&(h>8)&(h<30)&(s>.55)&(v>.35)
n,cc,st,_=cv2.connectedComponentsWithStats(loose.astype(np.uint8),connectivity=8)
cnt=np.bincount(cc[strict],minlength=n);keep=(cnt/np.maximum(st[:,4],1)>.35)&(st[:,4]>40);keep[0]=False
gold=keep[cc]
sc_=(gold&(abs(xx-750)<200)&(abs(yy-620)<200));sy,sx=np.nonzero(sc_);cxs,cys=np.median(sx),np.median(sy)
disk=((xx-cxs)**2+(yy-cys)**2)<(1.12*np.sqrt(sc_.sum()/np.pi))**2
gold|=disk&L&((s>.2)|(v<.5));print('sun',cxs,cys)
nb=np.zeros((H,W),bool);nb[oy+int(.12*LH):oy+int(.30*LH),ox+int(.1*LW):ox+int(.92*LW)]=True
dark=L&(v<.42)&~gold
screen=cv2.morphologyEx((dark&nb).astype(np.uint8),cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))>0
n,cc,st,_=cv2.connectedComponentsWithStats(screen.astype(np.uint8));screen[:]=False
for i in range(1,n):
    if st[i,4]>250: screen|=(cc==i)
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
scm=screen.astype(np.float32)
bev=cv2.GaussianBlur(np.clip(scm-np.roll(np.roll(scm,3,0),3,1),0,1),(0,0),1.1)
shd=cv2.GaussianBlur(np.clip(scm-np.roll(np.roll(scm,-3,0),-3,1),0,1),(0,0),1.2)
sheen=(.5+.5*np.sin((xx*.9+yy*1.7)/46.0))**6
scr=np.clip(src.astype(np.float32)*.88+np.array([150,190,170.])*(bev*.6+sheen*.12*scm)[...,None]-45*shd[...,None],0,255).astype(np.uint8)
Image.fromarray(paper[...,::-1]).save('a/sheet.jpg',quality=84)
save('paper.webp',paper,la);save('matrix.webp',paper,1-la)
save('gold.webp',src,ga*la);save('screen.webp',scr,sa*la);save('final.webp',src,la,90)
cnts,_=cv2.findContours(lab,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);c=cv2.approxPolyDP(max(cnts,key=cv2.contourArea),1.0,True)[:,0]
open('a/die.txt','w').write('M'+' L'.join(f'{p[0]},{p[1]}' for p in c)+' Z');print('die pts',len(c))
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
s2=over(P,srcf,ga*la);s3=over(s2,scr.astype(np.float32),sa*la);s4=over(s3,srcf,la)
cv2.imwrite('states.jpg',np.vstack([np.hstack([paper.astype(np.float32),P]),np.hstack([s2,s3]),np.hstack([s4,srcf])]).astype(np.uint8)[::2,::2])
