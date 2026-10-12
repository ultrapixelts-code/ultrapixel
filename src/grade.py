import cv2,numpy as np
def grade(img,mask=None,target=(232,240,245)):
    """Brighter, cleaner label: ivory paper near white, livelier gold and greens, crisper detail. img BGR uint8."""
    f=img.astype(np.float32)
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV).astype(np.float32);s,v=hsv[...,1]/255,hsv[...,2]/255
    sel=(s<.2)&(v>.55)
    if mask is not None: sel&=mask
    pap=np.array([np.median(f[...,c][sel]) for c in range(3)])
    f=f*(np.array(target,np.float32)/pap)               # white balance + exposure: paper -> bright ivory
    f=np.clip(f,0,255)
    # gentle S-curve for contrast, highlights protected
    x=f/255;x=np.where(x<.5,.5*(2*x)**1.12,1-.5*(2*(1-x))**1.12);f=x*255
    hsv=cv2.cvtColor(np.clip(f,0,255).astype(np.uint8),cv2.COLOR_BGR2HSV).astype(np.float32)
    h,s,v=hsv[...,0],hsv[...,1],hsv[...,2]
    gold=(h>8)&(h<34)&(s>70)
    green=(h>60)&(h<110)&(s>35)
    s=np.where(gold,s*1.28,np.where(green,s*1.18,s));v=np.where(gold,np.minimum(255,v*1.12+6),v)
    hsv=np.dstack([h,np.clip(s,0,255),np.clip(v,0,255)]).astype(np.uint8)
    f=cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR).astype(np.float32)
    bl=cv2.GaussianBlur(f,(0,0),1.6);f=f+.55*(f-bl)          # crisper print and foil edges
    bl=cv2.GaussianBlur(f,(0,0),12);f=f+.18*(f-bl)           # a little local contrast for the relief
    out=np.clip(f,0,255).astype(np.uint8)
    if mask is not None: out=np.where(mask[...,None],out,img)
    return out
