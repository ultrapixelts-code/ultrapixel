import cv2,numpy as np
s=cv2.imread('/root/.claude/uploads/2286d1b8-feeb-5eef-b9bb-945a87594a0d/401edc9b-image.png')
img=s.copy()
# box to clear -> clean paper reference of the same size (no protected appellation, no unverifiable claim on a demo label)
jobs=[((555,48,1000,94),(555,104,1000,150),False),
      ((68,346,272,456),(30,172,234,282),False),
      ((1290,345,1502,455),(1321,172,1533,282),False)]
for (x0,y0,x1,y1),(a0,b0,a1,b1),flip in jobs:
    patch=s[b0:b1,a0:a1].copy()
    if flip: patch=patch[:,::-1]
    src=img.copy();src[y0:y1,x0:x1]=patch
    mask=np.zeros(img.shape[:2],np.uint8);mask[y0+2:y1-2,x0+2:x1-2]=255
    img=cv2.seamlessClone(src,img,mask,((x0+x1)//2,(y0+y1)//2),cv2.NORMAL_CLONE)
cv2.imwrite('cleaned.png',img)
cv2.imwrite('cchk.jpg',cv2.vconcat([cv2.hconcat([img[20:130,500:1050],cv2.resize(img[320:480,40:320],(550,314))[:110]]),cv2.hconcat([img[330:440,1250:1530],img[330:440,1250:1520]])]) if False else img[0:520,0:1536][::1,::1])
