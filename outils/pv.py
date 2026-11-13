"""Planche de contrôle des aperçus : python3 outils/pv.py sortie.jpg  (lit output/preview_*.jpg)"""
import glob, sys, os
from PIL import Image, ImageDraw
fs = sorted(glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "preview_*.jpg")))
cols = 5; w, h = 360, 640
s = Image.new("RGB", (cols * w, ((len(fs) + cols - 1) // cols) * h), "white")
for i, f in enumerate(fs):
    im = Image.open(f).convert("RGB").resize((w, h)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 60, 16], fill=(255, 255, 0)); d.text((2, 2), os.path.basename(f)[8:13], fill=(0, 0, 0))
    s.paste(im, ((i % cols) * w, (i // cols) * h))
s.save(sys.argv[1], quality=85)
