"""Miniatures « poinsettia et froid du parking » : python3 outils/miniature_poinsettia.py
→ output/miniatures/miniature_poinsettia{,_b}_{3x4,9x16,16x9}.jpg
3x4 : TikTok et grille Instagram ; 9x16 : couverture Reels Instagram / Facebook, YouTube Shorts ;
16x9 : vignette YouTube classique.
A : le poinsettia sur le parking glacé (photo fournie), givre, -2 °C : « IL MEURT SUR LE PARKING ! ».
B : fond beige, avant / après : en forme au magasin → nu 5 jours après (« 5 MIN DE FROID SUFFISENT »)."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from gfx import YEL, RED, WHITE, BLUE, DARK, F_TITLE, title_img, icon, put, tag_img, text_img  # noqa: E402
from scenes_citron import photo_hd  # noqa: E402
from scenes_arrosage_soir import thermo_cold  # noqa: E402
import scenes_poinsettia as P  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "miniatures")
FORMATS = {"3x4": (1080, 1440), "9x16": (1080, 1920), "16x9": (1280, 720)}


def titles(c, lines, cx, y0, maxw, gap=0.9):
    y = y0
    for txt, col, size, rot in lines:
        im = title_img(txt, col, size, maxw)
        put(c, im, cx, y + im.height / 2, 1.0, rot)
        y += im.height * gap
    return y


def icy_parking(cw, ch, ww, cx, cy):
    hd = photo_hd(P.PANNEAU).convert("RGB")
    k = hd.width / 1080
    hh = ww * ch / cw
    x0 = min(max(cx - ww / 2, 0), 1080 - ww)
    y0 = min(max(cy - hh / 2, 0), 1920 - hh)
    im = hd.crop((int(x0 * k), int(y0 * k), int((x0 + ww) * k), int((y0 + hh) * k))).resize((cw, ch), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    lum = a.mean(2, keepdims=True)
    a = (a * 0.55 + lum * 0.45) * np.array([0.86, 0.95, 1.12], np.float32) * 0.88
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    edge = np.clip(1 - np.minimum(np.minimum(xx, cw - xx), np.minimum(yy, ch - yy)) / (0.16 * min(cw, ch)), 0, 1)
    edge = edge ** 1.6
    a = a * (1 - edge[..., None] * 0.6) + np.array([0.9, 0.95, 1.0], np.float32) * edge[..., None] * 0.6
    al = (np.clip((ch * 0.4 - yy[:, :1]) / (ch * 0.4), 0, 1) ** 1.4 * 0.5)
    a = a * (1 - al[..., None])
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")


def snow(c, n, seed=3):
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(seed)
    for _ in range(n):
        x, y, s = r.uniform(0, c.width), r.uniform(0, c.height), r.uniform(2, 6)
        d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 255, 255, int(r.uniform(140, 230))))


def scene_a(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    if land:
        c = icy_parking(cw, ch, 1080, 540, 1250)
        px, py, ph = cw * 0.735, ch * 0.97, ch * 0.82
    else:
        c = icy_parking(cw, ch, 1080, 540, 1000 if tall else 1150)
        px, py, ph = cw * 0.5, (1640 if tall else ch * 0.96), 820
    P.soft_shadow(c, px, py, ph * 0.5, 120)
    P.poins(c, P.SAIN, px, py, ph)
    P.frost_plant(c, px, py, ph * 0.9, 0.85, seed=4)
    snow(c, 80 if not land else 50)
    if land:
        titles(c, [("TON", WHITE, 120, -3), ("POINSETTIA", RED, 140, -3), ("MEURT SUR", WHITE, 120, -3),
                   ("LE PARKING !", YEL, 130, -4)], cw * 0.26, ch * 0.06, cw * 0.48, 0.86)
    else:
        top = 290 if tall else int(ch * 0.04)
        yb = titles(c, [("TON POINSETTIA", RED, 160, -3), ("MEURT SUR LE PARKING !", YEL, 130, -4)],
                    cw / 2, top, cw * 0.94, 0.9)
        put(c, thermo_cold(170), cw * 0.86, yb + 170, 1.0)
        put(c, text_img("-2 °C", F_TITLE, 90, BLUE, 7, DARK), cw * 0.86, yb + 330, 1.0)
    return c


def beige(cw, ch):
    c = Image.new("RGBA", (cw, ch), (238, 228, 208, 255))
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    v = 1 - 0.24 * np.clip(((xx - cw / 2) / cw) ** 2 + ((yy - ch * 0.45) / ch) ** 2, 0, 1)
    a = np.asarray(c).astype(np.float32)
    a[..., :3] *= v[..., None]
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def duo(c, xl, xr, y, h, lab_size):
    for x, name, lbl, good in ((xl, P.SAIN, "AU MAGASIN", True), (xr, P.NU, "5 JOURS APRÈS", False)):
        P.soft_shadow(c, x, y, h * 0.5, 90)
        P.poins(c, name, x, y, h)
        put(c, tag_img(lbl, lab_size), x, y + lab_size * 1.4, 1.0, -4 if good else 4)
    put(c, icon("arrow_down", int(h * 0.22)), (xl + xr) / 2, y - h * 0.45, 1.0, rot=90)


def scene_b(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    c = beige(cw, ch)
    if land:
        duo(c, cw * 0.56, cw * 0.86, ch * 0.8, ch * 0.62, 34)
        titles(c, [("5 MIN", YEL, 170, -3), ("DE FROID", YEL, 130, -3), ("SUFFISENT !", RED, 120, -4)],
               cw * 0.21, ch * 0.12, cw * 0.4, 0.86)
    else:
        top = 290 if tall else int(ch * 0.04)
        yb = titles(c, [("5 MIN DE FROID…", YEL, 160, -3), ("ET VOILÀ !", RED, 170, -4)],
                    cw / 2, top, cw * 0.94, 0.9)
        base = 1520 if tall else ch * 0.86
        h = min(640, base - yb - 60)
        duo(c, cw * 0.27, cw * 0.75, base, h, 46)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for tg, fn in (("", scene_a), ("_b", scene_b)):
        for f, (cw, ch) in FORMATS.items():
            p = os.path.join(OUT, f"miniature_poinsettia{tg}_{f}.jpg")
            fn(cw, ch).convert("RGB").save(p, quality=93)
            print(p)


if __name__ == "__main__":
    main()
