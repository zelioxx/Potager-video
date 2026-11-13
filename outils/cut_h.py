"""Détourage (rembg, BiRefNet) : python3 outils/cut_h.py source.png sortie.png  (garde les gros morceaux)."""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage
from rembg import remove, new_session
src, out = sys.argv[1], sys.argv[2]
sess = new_session("birefnet-general")
o = remove(Image.open(src).convert("RGB"), session=sess)
a = np.asarray(o).copy()
lab, n = ndimage.label(a[..., 3] > 30)
if n > 1:
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > sizes.max() * 0.02])
    a[..., 3] = np.where(keep, a[..., 3], 0)
Image.fromarray(a).save(out)
print(out, Image.fromarray(a).getbbox())
