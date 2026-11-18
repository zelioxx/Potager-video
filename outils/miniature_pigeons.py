"""Miniatures « pigeons et choux » : python3 outils/miniature_pigeons.py
→ output/miniatures/miniature_pigeons_choux{,_b}_{3x4,9x16,16x9}.jpg
3x4 : TikTok et grille Instagram ; 9x16 : couverture Reels Instagram / Facebook, YouTube Shorts ;
16x9 : vignette YouTube classique. Décor HD du potager enneigé + vrais détourages de la banque."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from gfx import YEL, RED, WHITE, DARK, title_img, icon, put  # noqa: E402
from scenes_citron import photo_hd  # noqa: E402
import scenes_pigeons_choux as S  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "miniatures")
FORMATS = {"3x4": (1080, 1440), "9x16": (1080, 1920), "16x9": (1280, 720)}


def background(cw, ch, cy=1150, zoom=1.0):
    """Décor HD recadré au format (centré sur le grand carré), un peu assombri en haut pour le titre."""
    hd = photo_hd(S.POTAGER).convert("RGB")
    k = hd.width / 1080
    ww = 1080 / zoom
    hh = ww * ch / cw
    if hh > 1920:
        hh = 1920
        ww = hh * cw / ch
    x0 = (1080 - ww) / 2
    y0 = min(max(cy - hh / 2, 0), 1920 - hh)
    im = hd.crop((int(x0 * k), int(y0 * k), int((x0 + ww) * k), int((y0 + hh) * k))).resize((cw, ch), Image.LANCZOS)
    im = im.convert("RGBA")
    a = np.zeros((ch, 1), np.float32)
    y = np.arange(ch)
    a[:, 0] = np.clip((ch * 0.42 - y) / (ch * 0.42), 0, 1) ** 1.4 * 150
    sh = Image.new("RGBA", (cw, ch), (20, 18, 14, 0))
    sh.putalpha(Image.fromarray(np.repeat(a, cw, 1).astype("uint8")))
    im.alpha_composite(sh)
    return im


def snow(c, n, seed=3):
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(seed)
    for _ in range(n):
        x, y, s = r.uniform(0, c.width), r.uniform(0, c.height), r.uniform(2, 6)
        d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 255, 255, int(r.uniform(120, 220))))


def bits(c, x, y, spread, n=10, seed=5, size=22):
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(seed)
    for _ in range(n):
        ang = r.uniform(-np.pi * 0.95, -np.pi * 0.05)
        q = r.uniform(0.3, 1.0)
        px, py = x + np.cos(ang) * spread * q, y + np.sin(ang) * spread * q * 0.7
        s = size * r.uniform(0.6, 1.2)
        col = (int(r.uniform(90, 140)), int(r.uniform(150, 190)), int(r.uniform(70, 100)), 255)
        d.polygon([(px - s, py), (px, py - s * 0.6), (px + s * 0.8, py + s * 0.2), (px - s * 0.2, py + s * 0.6)],
                  fill=col)


def titles(c, lines, cx, y0, maxw, gap=0.92):
    y = y0
    for txt, col, size, rot in lines:
        im = title_img(txt, col, size, maxw)
        put(c, im, cx, y + im.height / 2, 1.0, rot)
        y += im.height * gap


def scene_a(cw, ch):
    """Le chou dévoré et les deux pigeons coupables (flèche sur celui qui picore)."""
    land = cw > ch
    tall = ch / cw > 1.5                              # 9:16 : tout dans la zone 3:4 du centre (grilles)
    c = background(cw, ch, cy=1250)
    if land:
        gx, gy, cabw = cw * 0.77, ch * 0.97, ch * 0.62
    else:
        gx, gy, cabw = cw * 0.56, (1640 if tall else ch * 0.955), 600
    S.ground_shadow(c, gx, gy - cabw * 0.04, cabw * 0.95, 80)
    S.sp(c, S.CHOU, gx, gy, cabw, 0.5, 1.0)
    bits(c, gx - cabw * 0.2, gy - cabw * 0.6, cabw * 0.45, 9, size=cabw * 0.03)
    pw = cabw * 0.72
    px, py = gx - cabw * 0.42, gy + cabw * 0.04
    S.pigeon(c, S.PIG, px, py, pw, False, 0.0, peck=1.0)                 # il picore le chou
    S.pigeon(c, S.PIG, gx + cabw * 0.5, gy - cabw * 0.07, pw * 0.92, True, 0.0)
    snow(c, 70 if not land else 45)
    if land:
        titles(c, [("CHOUX", YEL, 165, -3), ("DÉVORÉS ?", YEL, 165, -3),
                   ("LE COUPABLE :", RED, 120, -4)], cw * 0.27, ch * 0.08, cw * 0.5, 0.86)
        put(c, icon("arrow_down", 120), px - pw * 0.05, py - pw * 0.78, 1.0, 0)
    else:
        titles(c, [("CHOUX DÉVORÉS", YEL, 170, -3), ("EN HIVER ?", WHITE, 140, -3),
                   ("LE COUPABLE !", RED, 150, -4)], cw / 2, (290 if tall else ch * 0.04), cw * 0.92, 0.88)
        put(c, icon("arrow_down", 150), px - pw * 0.05, py - pw * 0.8, 1.0, 0)
    return c


def scene_b(cw, ch):
    """L'épouvantail couvert de pigeons au milieu des choux rongés."""
    land = cw > ch
    tall = ch / cw > 1.5
    c = background(cw, ch, cy=1250)
    if land:
        ex, ey, eh = cw * 0.72, ch * 1.02, ch * 0.92
    elif tall:
        ex, ey, eh = cw * 0.5, 1700, 1000
    else:
        ex, ey, eh = cw * 0.5, ch * 1.0, ch * 0.62
    ew = eh * S._src(S.EPOUV).width / S._src(S.EPOUV).height
    for dx, fl in ((-0.42, False), (0.42, True)):                       # choux rongés au pied
        cwb = ew * 0.62
        S.ground_shadow(c, ex + dx * ew * 1.05, ey - eh * 0.04, cwb * 0.9, 70)
        S.sp(c, S.CHOU_N if dx > 0 else S.CHOU, ex + dx * ew * 1.05, ey - eh * 0.03, cwb, 0.5, 1.0, flip=fl)
    S.sp(c, S.EPOUV, ex, ey, ew, 0.5, 1.0, cold=5)
    arm_y = ey - eh * 0.66
    pw = ew * 0.32
    S.pigeon(c, S.PIG, ex - ew * 0.36, arm_y, pw, False, 0.0, peck=1.0)
    S.pigeon(c, S.PIG, ex + ew * 0.37, arm_y, pw, True, 0.0)
    S.pigeon(c, S.PIG, ex + ew * 0.04, ey - eh * 0.935, pw * 0.95, False, 0.0, peck=1.0)
    snow(c, 70 if not land else 45, 8)
    if land:
        titles(c, [("L'ÉPOUVANTAIL ?", YEL, 135, -3), ("ÇA MARCHE", RED, 150, -4), ("PAS !", RED, 150, -4)],
               cw * 0.27, ch * 0.1, cw * 0.5, 0.88)
        put(c, icon("cross", 140), min(ex + ew * 0.55, cw - 90), ch * 0.2, 1.0)
    else:
        titles(c, [("L'ÉPOUVANTAIL", YEL, 170, -3), ("ÇA MARCHE PAS !", RED, 150, -4)],
               cw / 2, (290 if tall else ch * 0.05), cw * 0.92, 0.88)
        put(c, icon("cross", 160), min(ex + ew * 0.5, cw - 100), ey - eh * 0.84, 1.0)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for tag, fn in (("", scene_a), ("_b", scene_b)):
        for f, (cw, ch) in FORMATS.items():
            p = os.path.join(OUT, f"miniature_pigeons_choux{tag}_{f}.jpg")
            fn(cw, ch).convert("RGB").save(p, quality=93)
            print(p)


if __name__ == "__main__":
    main()
