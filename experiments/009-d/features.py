import numpy as np
import cv2

def orientation(rgb):
    gray=cv2.cvtColor(rgb.astype("float32"),cv2.COLOR_RGB2GRAY)
    gx=cv2.Sobel(gray,-1,1,0,ksize=3)/8;gy=cv2.Sobel(gray,-1,0,1,ksize=3)/8
    blur=lambda v:cv2.GaussianBlur(v,(0,0),2)
    a,b,c=blur(gx*gx),blur(gx*gy),blur(gy*gy)
    phi=0.5*np.arctan2(2*b,a-c)
    reliability=np.sqrt((a-c)**2+4*b*b)/(a+c+1)
    return np.stack((np.cos(phi),np.sin(phi)),axis=-1)*reliability[:,:,None],np.hypot(gx,gy)

def unit(v):
    return v/max(1.e-6,np.linalg.norm(v))
