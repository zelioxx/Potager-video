"""Miniatures « le sapin qui perd ses aiguilles » : python3 outils/miniature_sapin.py
→ output/miniatures/miniature_sapin{,_b}_{3x4,9x16,16x9}.jpg
A : le salon, le sapin desséché à côté du radiateur, aiguilles au sol : « TON SAPIN PERD SES AIGUILLES ? ».
B : fond beige, avant / après : « PRÈS DU RADIATEUR » (desséché) → « LOIN DE LA CHALEUR » (vert)."""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from gfx import YEL, RED, WHITE, GREEN, title_img, icon, put, tag_img, W, H  # noqa: E402
from scenes_citron import photo_hd  # noqa: E402
from scenes_fumier import Cam  # noqa: E402
import scenes_sapin as S  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "miniatures")
FORMATS = {"3x4": (1080, 1440), "9x16": (1080, 1920), "16x9": (1280, 720)}


def titles(c, lines, cx, y0, maxw, gap=0.9):
    y = y0
    for txt, col, size, rot in lines:
        im = title_img(txt, col, size, maxw)
        put(c, im, cx, y + im.height / 2, 1.0, rot)
        y += im.height * gap
    return y


def scene_full(z, fx, fy):
    """Le salon vue table, cadré par la caméra (z, fx, fy) : radiateur, sapin sec, tas d'aiguilles."""
    cam = Cam(z, fx, fy)
    full = photo_hd(S.SALON_B).resize((W, H), Image.LANCZOS)
    from scenes_citron import zoomed
    w = zoomed(full, cam.z, cam.fx, cam.fy).copy().convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rx, ry = cam.p(*S.RAD_B)
    S.sp(lay, S.RADIATEUR, rx, ry, 215 * cam.z, 0.5, 1.0)
    x, y = cam.p(*S.TREE_B)
    S.soft_shadow(lay, x, y, 260 * cam.z, 90)
    S.needles(lay, 30.0, 0.0, x, y, S.TREE_H * cam.z, 14, z=cam.z)
    S.tree(lay, S.SEC, x, y, S.TREE_H * cam.z)
    w.alpha_composite(lay)
    S.heat(w, cam, 0.3, 1.0, *S.RAD_B, 300)
    a = np.asarray(w).astype(np.float32)
    yy = np.arange(H)[:, None]
    a[..., :3] *= (1 - np.clip((780 - yy) / 780, 0, 1) ** 1.4 * 0.5)[..., None]
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def scene_a(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    if land:
        full = scene_full(1.0, 540, 960)
        c = full.resize((cw, int(H * cw / W)), Image.LANCZOS)
        y0 = int(S.TREE_B[1] * cw / W - ch * 0.92)
        c = c.crop((0, y0, cw, y0 + ch))
        titles(c, [("TON SAPIN", WHITE, 120, -3), ("PERD SES", YEL, 110, -3), ("AIGUILLES ?", YEL, 120, -3)],
               cw * 0.8, ch * 0.08, cw * 0.36, 0.86)
    else:
        full = scene_full(1.45 if tall else 1.6, 640, 820 if tall else 880)
        c = full.resize((cw, int(H * cw / W)), Image.LANCZOS)
        y0 = (c.height - ch) // 2 + (0 if tall else 120)
        c = c.crop((0, y0, cw, y0 + ch))
        titles(c, [("TON SAPIN PERD", WHITE, 150, -3), ("SES AIGUILLES ?", YEL, 150, -3),
                   ("MAUVAIS ENDROIT !", RED, 120, -4)], cw / 2, 290 if tall else ch * 0.035, cw * 0.94, 0.88)
    return c


def pair_img():
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base = 1500
    for x, st, lbl, good in ((240, S.SEC, "PRÈS DU RADIATEUR", False), (860, S.SAPIN, "LOIN DE LA CHALEUR", True)):
        S.soft_shadow(c, x, base, 300, 90)
        if not good:
            S.needles(c, 30.0, 0.0, x, base, 700, 14)
        S.tree(c, st, x, base, 700)
        put(c, tag_img(lbl, 40), x, base + 90, 1.0, 4 if good else -4)
        put(c, icon("check" if good else "cross", 130), x + 200, base - 640, 1.0)
    put(c, icon("arrow_down", 130), 540, base - 330, 1.0, rot=90)
    return c.crop(c.getbbox())


def scene_b(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    c = S.beige().resize((cw, ch), Image.LANCZOS)
    p = pair_img()
    if land:
        k = min(ch * 0.86 / p.height, cw * 0.58 / p.width)
        put(c, p, cw * 0.69, ch / 2 + 10, k)
        titles(c, [("SES AIGUILLES", WHITE, 110, -3), ("TOMBENT ?", RED, 140, -4), ("CHANGE-LE", YEL, 110, -3),
                   ("DE PLACE !", YEL, 120, -3)], cw * 0.2, ch * 0.08, cw * 0.38, 0.86)
    else:
        yb = titles(c, [("SES AIGUILLES TOMBENT ?", WHITE, 140, -3), ("CHANGE-LE DE PLACE !", RED, 130, -4)],
                    cw / 2, 290 if tall else ch * 0.035, cw * 0.94, 0.9)
        bottom = 1640 if tall else ch - 30
        k = min((bottom - yb - 30) / p.height, cw * 0.96 / p.width)
        put(c, p, cw / 2, (yb + 15 + bottom) / 2, k)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for tg, fn in (("", scene_a), ("_b", scene_b)):
        for f, (cw, ch) in FORMATS.items():
            path = os.path.join(OUT, f"miniature_sapin{tg}_{f}.jpg")
            fn(cw, ch).convert("RGB").save(path, quality=93)
            print(path)


if __name__ == "__main__":
    main()
