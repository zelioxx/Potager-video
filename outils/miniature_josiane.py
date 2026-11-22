"""Miniatures « Josiane : faire rougir les tomates vertes » : python3 outils/miniature_josiane.py
→ output/miniatures/miniature_josiane{,_b}_{3x4,9x16,16x9}.jpg
3x4 : TikTok et grille Instagram ; 9x16 : couverture Reels Instagram / Facebook, YouTube Shorts ;
16x9 : vignette YouTube classique.
A : le salon, l'émoji mort de rire, la bêche barrée : « JOSIANE… PAS JARDINIÈRE ! ».
B : fond beige, tomate verte → tomate rouge grâce à la banane : « LE SECRET : UNE BANANE ! »."""
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from gfx import YEL, RED, WHITE, GREEN, title_img, icon, put  # noqa: E402
from scenes_citron import photo  # noqa: E402
from scenes_pothos_lumiere import sp, soft_shadow  # noqa: E402
from scenes import sparkles  # noqa: E402
import scenes_josiane as J  # noqa: E402
import scenes_tomates_vertes as TV  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "miniatures")
FORMATS = {"3x4": (1080, 1440), "9x16": (1080, 1920), "16x9": (1280, 720)}


def titles(c, lines, cx, y0, maxw, gap=0.9):
    y = y0
    for txt, col, size, rot in lines:
        im = title_img(txt, col, size, maxw)
        put(c, im, cx, y + im.height / 2, 1.0, rot)
        y += im.height * gap
    return y


def salon(cw, ch, cy):
    hd = photo(J.SALON).convert("RGB")
    k = hd.width / 1080
    ww = 1080
    hh = ww * ch / cw
    y0 = min(max(cy - hh / 2, 0), 1920 - hh)
    im = hd.crop((0, int(y0 * k), hd.width, int((y0 + hh) * k))).resize((cw, ch), Image.LANCZOS).convert("RGBA")
    a = np.asarray(im).astype(np.float32)
    yy = np.arange(ch)[:, None]
    al = np.clip((ch * 0.42 - yy) / (ch * 0.42), 0, 1) ** 1.4 * 0.5
    a[..., :3] *= (1 - al)[..., None]
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def beche_cross(c, x, y, h, rot=-8):
    soft_shadow(c, x, y, h * 0.3, 90)
    sp(c, J.BECHE, x, y, h, 0.5, 1.0, rot=rot)
    r = math.radians(rot)
    put(c, icon("cross", int(h * 0.3)), x - h * 0.5 * math.sin(r), y - h * 0.5 * math.cos(r), 1.0)


def scene_a(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    if land:
        c = salon(cw, ch, 1150)
        beche_cross(c, cw * 0.58, ch * 0.98, ch * 0.92)
        sp(c, J.EMOJI, cw * 0.84, ch * 0.62, ch * 0.42, 0.5, 0.5, rot=-8)
        titles(c, [("JOSIANE…", WHITE, 140, -3), ("PAS", RED, 140, -4), ("JARDINIÈRE !", RED, 140, -4)],
               cw * 0.24, ch * 0.12, cw * 0.44, 0.88)
    else:
        c = salon(cw, ch, 1000 if tall else 1080)
        base = 1650 if tall else ch * 0.97
        beche_cross(c, cw * 0.3, base, 900 if tall else 860)
        sp(c, J.EMOJI, cw * 0.74, base - 330, 360, 0.5, 0.5, rot=-8)
        sparkles(c, 0.5, 0.0, cw * 0.74, base - 330, 280, 8, 3, 1.0)
        titles(c, [("JOSIANE…", WHITE, 170, -3), ("PAS JARDINIÈRE !", RED, 150, -4)],
               cw / 2, 290 if tall else ch * 0.04, cw * 0.94, 0.9)
    return c


def beige(cw, ch):
    c = Image.new("RGBA", (cw, ch), (238, 228, 208, 255))
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    v = 1 - 0.24 * np.clip(((xx - cw / 2) / cw) ** 2 + ((yy - ch * 0.45) / ch) ** 2, 0, 1)
    a = np.asarray(c).astype(np.float32)
    a[..., :3] *= v[..., None]
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def trio(c, xl, xr, y, s):
    """Tomate verte → (banane) → tomate rouge."""
    for x, name in ((xl, TV.VERTE), (xr, TV.ROUGE)):
        soft_shadow(c, x, y + s * 0.42, s * 0.8, 80)
        sp(c, name, x, y, s, 0.5, 0.5)
    put(c, icon("arrow_down", int(s * 0.38)), (xl + xr) / 2, y - s * 0.32, 1.0, rot=90)
    soft_shadow(c, (xl + xr) / 2, y + s * 0.77, s * 1.1, 80)
    sp(c, TV.BANANE, (xl + xr) / 2, y + s * 0.75, s * 0.75, 0.5, 1.0, rot=-6)
    sparkles(c, 0.5, 0.0, xr, y, s * 0.7, 8, 9, 1.0)


def scene_b(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    c = beige(cw, ch)
    if land:
        trio(c, cw * 0.56, cw * 0.87, ch * 0.4, ch * 0.42)
        titles(c, [("TOMATES", GREEN, 130, -3), ("VERTES ?", GREEN, 130, -3), ("LE SECRET :", YEL, 100, -3),
                   ("UNE BANANE !", RED, 110, -4)], cw * 0.22, ch * 0.08, cw * 0.42, 0.86)
    else:
        yb = titles(c, [("TOMATES VERTES ?", GREEN, 160, -3), ("LE SECRET :", YEL, 130, -3),
                        ("UNE BANANE !", RED, 150, -4)], cw / 2, 290 if tall else ch * 0.04, cw * 0.94, 0.88)
        s = 420 if tall else 400
        trio(c, cw * 0.25, cw * 0.75, (1180 if tall else ch * 0.62), s)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for tg, fn in (("", scene_a), ("_b", scene_b)):
        for f, (cw, ch) in FORMATS.items():
            p = os.path.join(OUT, f"miniature_josiane{tg}_{f}.jpg")
            fn(cw, ch).convert("RGB").save(p, quality=93)
            print(p)


if __name__ == "__main__":
    main()
