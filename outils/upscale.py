"""Agrandit ×4 une photo de décor avec EDSR (OpenCV dnn_superres), par tuiles : plus de détail et moins de
blocs JPEG que l'agrandissement classique quand la caméra zoome dans la photo.
    python3 outils/upscale.py <modele EDSR_x4.pb> <photo> <sortie.png>"""
import sys
import cv2
import numpy as np

model, src, out = sys.argv[1:4]
sr = cv2.dnn_superres.DnnSuperResImpl_create()
sr.readModel(model)
sr.setModel("edsr", 4)
im = cv2.imread(src)
h, w = im.shape[:2]
T, P = 192, 12
res = np.zeros((h * 4, w * 4, 3), np.uint8)
for y in range(0, h, T):
    for x in range(0, w, T):
        y0, x0 = max(0, y - P), max(0, x - P)
        y1, x1 = min(h, y + T + P), min(w, x + T + P)
        o = sr.upsample(im[y0:y1, x0:x1])
        oy, ox = (y - y0) * 4, (x - x0) * 4
        th, tw = min(T, h - y) * 4, min(T, w - x) * 4
        res[y * 4:y * 4 + th, x * 4:x * 4 + tw] = o[oy:oy + th, ox:ox + tw]
    print(f"{src} : {min(100, int((y + T) / h * 100))} %", flush=True)
cv2.imwrite(out, res)
print(out, res.shape)
