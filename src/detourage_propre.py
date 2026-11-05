"""Détourage propre sur fond blanc : retire le blanc mêlé aux bords (décontamination) et resserre l'alpha."""
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
src, out, photo = sys.argv[1], sys.argv[2], sys.argv[3]
im = np.asarray(Image.open(src).convert('RGBA')).astype(np.float32)
a = im[..., 3] / 255.0
rgb = np.asarray(Image.open(photo).convert('RGB').resize(Image.open(src).size)).astype(np.float32)
bg = np.array([250.0, 250.0, 250.0])
# couleur du fond réellement présente : médiane des pixels transparents proches
near = (a < 0.05) & ndimage.binary_dilation(a > 0.5, iterations=6)
if near.any():
    bg = np.median(rgb[near], axis=0)
safe = np.maximum(a, 1e-3)[..., None]
fg = (rgb - (1 - a[..., None]) * bg) / safe
fg = np.clip(fg, 0, 255)
# là où l'alpha est faible, la couleur est peu fiable : on prend celle des pixels opaques voisins
solid = a > 0.9
idx = ndimage.distance_transform_edt(~solid, return_distances=False, return_indices=True)
neigh = rgb[idx[0], idx[1]]
w = np.clip((a - 0.25) / 0.65, 0, 1)[..., None]
fg = fg * w + neigh * (1 - w)
# alpha resserré (supprime le halo) sans érosion en escalier
a2 = np.clip((a - 0.12) / 0.8, 0, 1) ** 1.15
res = np.dstack([fg, a2 * 255]).clip(0, 255).astype(np.uint8)
Image.fromarray(res, 'RGBA').save(out)
print(out, 'fond', bg.round())
