"""Miniatures « rotation au potager » : python3 outils/miniature_rotation.py
→ output/miniatures/miniature_rotation{,_b}_{3x4,9x16,16x9}.jpg
A : fond beige, le plan sur sa feuille (4 zones au crayon) et la flèche qui tourne : « FAIS ÇA CET HIVER ! ».
B : fond beige, avant / après : beau pied de tomate « ANNÉE 1 » → pied malade « ANNÉE 3 » (même endroit)."""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from gfx import YEL, RED, WHITE, GREEN, title_img, icon, put, tag_img, W, H  # noqa: E402
import scenes_rotation as R  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "miniatures")
FORMATS = {"3x4": (1080, 1440), "9x16": (1080, 1920), "16x9": (1280, 720)}


def titles(c, lines, cx, y0, maxw, gap=0.9):
    y = y0
    for txt, col, size, rot in lines:
        im = title_img(txt, col, size, maxw)
        put(c, im, cx, y + im.height / 2, 1.0, rot)
        y += im.height * gap
    return y


def beige(cw, ch):
    return R.beige().resize((cw, ch), Image.LANCZOS) if (cw, ch) != (W, H) else R.beige().copy()


def plan_img():
    """La feuille avec les 4 dessins, leurs étiquettes et la flèche de rotation (détourée)."""
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    R.paper(c)
    R.zones(c, 99, [0, 0, 0, 0])
    _, _, _, (cx, cy), _, _ = R.paper_geom()
    put(c, R.turn_arrow(105), cx, cy, 1.0)
    return c.crop(c.getbbox())


def scene_a(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    c = beige(cw, ch)
    p = plan_img()
    if land:
        k = ch * 0.94 / p.height
        put(c, p, cw * 0.72, ch / 2, k, -3)
        titles(c, [("TON POTAGER", WHITE, 120, -3), ("RATE ?", RED, 150, -4), ("FAIS ÇA", YEL, 120, -3),
                   ("CET HIVER !", YEL, 120, -3)], cw * 0.25, ch * 0.08, cw * 0.46, 0.86)
    else:
        yb = titles(c, [("TON POTAGER RATE ?", WHITE, 150, -3), ("FAIS ÇA CET HIVER !", RED, 140, -4)],
                    cw / 2, 290 if tall else ch * 0.035, cw * 0.94, 0.9)
        bottom = 1640 if tall else ch - 30
        k = (bottom - yb - 30) / p.height
        put(c, p, cw / 2, (yb + 15 + bottom) / 2, k, -2)
    return c


def pair_img():
    """Beau pied (année 1) → pied malade (année 3), au même endroit."""
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base, ww = 1500, 880
    for x, st, lbl, good in ((290, "tomate_4", "ANNÉE 1", True), (790, R.SICK, "ANNÉE 3", False)):
        R.soft_shadow(c, x, base, 330, 80)
        R.tomato(c, x, base, ww, st)
        put(c, tag_img(lbl, 56), x, base + 90, 1.0, -4 if good else 4)
        put(c, icon("check" if good else "cross", 130), x + 150, base - 1000, 1.0)
    put(c, icon("arrow_down", 140), 540, base - 520, 1.0, rot=90)
    return c.crop(c.getbbox())


def scene_b(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    c = beige(cw, ch)
    p = pair_img()
    if land:
        k = ch * 0.92 / p.height
        put(c, p, cw * 0.7, ch / 2 + 10, k)
        titles(c, [("TOMATES", RED, 130, -3), ("AU MÊME", WHITE, 120, -3), ("ENDROIT ?", WHITE, 120, -3),
                   ("ERREUR !", YEL, 140, -4)], cw * 0.22, ch * 0.07, cw * 0.42, 0.86)
    else:
        yb = titles(c, [("TOMATES AU MÊME", WHITE, 150, -3), ("ENDROIT ? ERREUR !", RED, 140, -4)],
                    cw / 2, 290 if tall else ch * 0.035, cw * 0.94, 0.9)
        bottom = 1640 if tall else ch - 30
        k = min((bottom - yb - 30) / p.height, cw * 0.96 / p.width)
        put(c, p, cw / 2, (yb + 15 + bottom) / 2, k)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for tg, fn in (("", scene_a), ("_b", scene_b)):
        for f, (cw, ch) in FORMATS.items():
            path = os.path.join(OUT, f"miniature_rotation{tg}_{f}.jpg")
            fn(cw, ch).convert("RGB").save(path, quality=93)
            print(path)


if __name__ == "__main__":
    main()
