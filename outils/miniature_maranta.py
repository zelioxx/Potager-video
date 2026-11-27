"""Miniatures « nouvelle plante qui meurt en 2 semaines » : python3 outils/miniature_maranta.py
→ output/miniatures/miniature_maranta{,_b}_{3x4,9x16,16x9}.jpg
A : le salon, le maranta abîmé sur la table : « TA PLANTE MEURT APRÈS L'ACHAT ? CE N'EST PAS TA FAUTE ! ».
B : fond beige, avant / après : « EN JARDINERIE » (très belle) → « 2 SEMAINES APRÈS » (abîmée)."""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from gfx import YEL, RED, WHITE, GREEN, title_img, icon, put, tag_img, W, H  # noqa: E402
from scenes_citron import photo_hd  # noqa: E402
import scenes_maranta as M  # noqa: E402
from scenes_rotation import beige as beige_full  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "miniatures")
FORMATS = {"3x4": (1080, 1440), "9x16": (1080, 1920), "16x9": (1280, 720)}


def titles(c, lines, cx, y0, maxw, gap=0.9):
    y = y0
    for txt, col, size, rot in lines:
        im = title_img(txt, col, size, maxw)
        put(c, im, cx, y + im.height / 2, 1.0, rot)
        y += im.height * gap
    return y


def salon(cw, ch, ww, cx, cy):
    hd = photo_hd(M.SALON).convert("RGB")
    k = hd.width / 1080
    hh = ww * ch / cw
    x0 = min(max(cx - ww / 2, 0), 1080 - ww)
    y0 = min(max(cy - hh / 2, 0), 1920 - hh)
    im = hd.crop((int(x0 * k), int(y0 * k), int((x0 + ww) * k), int((y0 + hh) * k))).resize((cw, ch), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    yy = np.arange(ch)[:, None]
    a *= (1 - np.clip((ch * 0.42 - yy) / (ch * 0.42), 0, 1) ** 1.4 * 0.5)[..., None]
    s = cw / ww
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA"), (lambda x, y: ((x - x0) * s, (y - y0) * s)), s


def scene_a(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    if land:
        c, P, s = salon(cw, ch, 1080, 560, 900)
        x, y = cw * 0.73, ch * 0.9
        M.soft_shadow(c, x, y, 230, 90)
        M.maranta(c, 4, x, y, ch * 0.95)
        titles(c, [("TA PLANTE", WHITE, 130, -3), ("MEURT APRÈS", YEL, 120, -3), ("L'ACHAT ?", YEL, 130, -3),
                   ("PAS TA FAUTE !", GREEN, 105, -4)], cw * 0.25, ch * 0.07, cw * 0.46, 0.86)
    else:
        c, P, s = salon(cw, ch, 760, M.TABLE[0] - 20, M.TABLE[1] - (330 if tall else 260))
        x, y = P(*M.TABLE)
        M.soft_shadow(c, x, y, M.FRAME_W * s * 0.42, 90)
        M.maranta(c, 4, x, y, M.FRAME_W * s)
        titles(c, [("TA PLANTE MEURT", WHITE, 150, -3), ("APRÈS L'ACHAT ?", YEL, 150, -3),
                   ("PAS TA FAUTE !", GREEN, 130, -4)], cw / 2, 290 if tall else ch * 0.035, cw * 0.94, 0.88)
    return c


def pair_img():
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base = 1500
    for x, st, lbl, good in ((250, 1, "EN JARDINERIE", True), (850, 4, "2 SEMAINES APRÈS", False)):
        M.soft_shadow(c, x, base, 300, 90)
        M.maranta(c, st, x, base, 640)
        put(c, tag_img(lbl, 46), x, base + 90, 1.0, -4 if good else 4)
        put(c, icon("check" if good else "cross", 130), x + 170, base - 560, 1.0)
    put(c, icon("arrow_down", 130), 540, base - 300, 1.0, rot=90)
    return c.crop(c.getbbox())


def scene_b(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    c = beige_full().resize((cw, ch), Image.LANCZOS)
    p = pair_img()
    if land:
        k = min(ch * 0.85 / p.height, cw * 0.56 / p.width)
        put(c, p, cw * 0.7, ch / 2 + 10, k)
        titles(c, [("EN 2 SEMAINES", WHITE, 110, -3), ("ELLE MEURT ?", RED, 130, -4), ("VOICI", YEL, 110, -3),
                   ("POURQUOI !", YEL, 120, -3)], cw * 0.21, ch * 0.08, cw * 0.4, 0.86)
    else:
        yb = titles(c, [("EN 2 SEMAINES…", WHITE, 150, -3), ("ELLE MEURT ?", RED, 170, -4)],
                    cw / 2, 290 if tall else ch * 0.035, cw * 0.94, 0.9)
        bottom = 1640 if tall else ch - 30
        k = min((bottom - yb - 30) / p.height, cw * 0.96 / p.width)
        put(c, p, cw / 2, (yb + 15 + bottom) / 2, k)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for tg, fn in (("", scene_a), ("_b", scene_b)):
        for f, (cw, ch) in FORMATS.items():
            path = os.path.join(OUT, f"miniature_maranta{tg}_{f}.jpg")
            fn(cw, ch).convert("RGB").save(path, quality=93)
            print(path)


if __name__ == "__main__":
    main()
