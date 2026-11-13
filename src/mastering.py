"""Version « +4 dB » validée par Louis : la VOIX seule passe dans la chaîne douce (-10 LUFS) poussée de 4 dB
(≈ -8,3 LUFS), puis on ajoute les bruitages APRÈS, à un niveau plafonné sous la voix.

    python3 src/mastering.py fumier          → output/<vidéo>_plus4db.mp4 et ..._plus4db_leger.mp4

Pourquoi les bruitages après : la compression du mastering remonte tout ce qui est faible. Avant, les bruitages
(et les whoosh des transitions) tombés dans les blancs de la voix ressortaient presque au niveau de la voix (à ~7 dB
seulement), ce qui densifie le son et fait baisser la vidéo par la normalisation de volume des plateformes.
Maintenant : les bruitages restent au moins 12 dB sous le niveau moyen de la voix, et leurs pics au moins 9 dB sous
les pics des syllabes, partout (pendant la parole comme dans les blancs).
"""
import os
import re
import subprocess
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE = "highpass=f=110:p=2,equalizer=f=250:t=q:w=1:g=-1.5,equalizer=f=2600:t=q:w=1:g=1.5"
CMP = ("compand=attacks=0.012:decays=0.25:points=-80/-80|-40/-30|-24/-17|-12/-10|0/-5:soft-knee=10:gain=0,"
       "acompressor=threshold=-16dB:ratio=3:attack=8:release=90:knee=6")
LIM = "alimiter=limit=0.85:attack=5:release=60:level=false"
SAFE = "alimiter=limit=0.84:attack=1:release=20:level=false"     # rattrape les pics de l'encodage AAC
FX_UNDER = 12.0          # dB : niveau des bruitages (fenêtres de 100 ms) sous le niveau médian de la voix
FX_PEAK_UNDER = 9.0      # dB : pics des bruitages sous le pic médian des syllabes


def lufs(path, af=None):
    out = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", (af + "," if af else "") + "ebur128", "-f", "null",
                          "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])


def gain_for(src, target=-10.0):
    """Gain (dB) avant le limiteur pour que la version douce tombe à `target` LUFS."""
    v = 8.0
    for _ in range(3):
        got = lufs(src, f"{PRE},{CMP},volume={v:.2f}dB,{LIM}")
        if abs(target - got) < 0.1:
            break
        v += (target - got) * 1.6
    return v


def frames(x, w, sr, fn):
    k = int(w * sr)
    n = len(x) // k
    return fn(x[: n * k].reshape(n, k)), k


def main(project):
    sys.argv = ["render.py", project]
    sys.path.insert(0, os.path.join(ROOT, "src"))
    import render
    tmp = os.path.join(ROOT, "output", "tmp_master_" + project)
    os.makedirs(tmp, exist_ok=True)
    sv, sfx_ = os.path.join(tmp, "voix.wav"), os.path.join(tmp, "bruitages.wav")
    render.build_audio(os.path.join(tmp, "mix.wav"), stems=(sv, sfx_))
    # 1) la voix seule dans la chaîne validée (+4 dB au-dessus de la version douce à -10 LUFS)
    # même gain que la version +4 dB validée (calé sur le mixage complet) : la voix sort exactement pareil
    g = gain_for(os.path.join(tmp, "mix.wav")) + 4.0
    mv = os.path.join(tmp, "voix_master.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", sv, "-af", f"{PRE},{CMP},volume={g:.2f}dB,{LIM}",
                    "-c:a", "pcm_f32le", "-ar", "48000", "-ac", "1", mv], check=True)
    v, sr = sf.read(mv)
    fx, sr2 = sf.read(sfx_)
    if sr2 != sr:
        fx = np.interp(np.linspace(0, len(fx) - 1, int(len(fx) * sr / sr2)), np.arange(len(fx)), fx)
    n = min(len(v), len(fx))
    v, fx = v[:n], fx[:n]
    # 2) les bruitages plafonnés sous la voix masterisée
    db = lambda a: 20 * np.log10(np.maximum(a, 1e-9))
    lv, _ = frames(v, 0.1, sr, lambda m: db(np.sqrt((m ** 2).mean(1))))
    pv, _ = frames(v, 0.01, sr, lambda m: db(np.abs(m).max(1)))
    speech = lv > lv.max() - 30
    v_med = np.median(lv[speech])
    v_pk = np.median(pv[pv > pv.max() - 12])
    lf, k100 = frames(fx, 0.1, sr, lambda m: db(np.sqrt((m ** 2).mean(1))))
    G = 10 ** ((v_med - FX_UNDER - lf.max()) / 20)        # le bruitage le plus fort : 12 dB sous la voix
    fx = fx * G
    # plafond des pics (10 ms), lissé pour ne pas « hacher » le son
    pf, k10 = frames(fx, 0.01, sr, lambda m: np.abs(m).max(1))
    cap = 10 ** ((v_pk - FX_PEAK_UNDER) / 20)
    gg = np.minimum(1.0, cap / np.maximum(pf, 1e-9))
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    gg = uniform_filter1d(minimum_filter1d(gg, 5), 3)
    env = np.repeat(gg, k10)
    env = np.concatenate([env, np.full(n - len(env), env[-1] if len(env) else 1.0)])
    fx = fx * env
    mix = v + fx
    out_wav = os.path.join(tmp, "mix_master.wav")
    sf.write(out_wav, np.stack([mix, mix], 1), sr, subtype="FLOAT")
    # 3) sur la vidéo (rendue au volume d'origine)
    video = os.path.join(ROOT, "output", render.CFG["out"])
    base, ext = os.path.splitext(video)
    out = base + "_plus4db" + ext
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", video, "-i", out_wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-af", SAFE, "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", out, "-c:v", "libx264", "-crf", "28", "-preset", "slow",
                    "-maxrate", "1500k", "-bufsize", "3000k", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags",
                    "+faststart", base + "_plus4db_leger" + ext], check=True)
    lfx, _ = frames(fx, 0.1, sr, lambda m: db(np.sqrt((m ** 2).mean(1))))
    pfx, _ = frames(fx, 0.01, sr, lambda m: db(np.abs(m).max(1)))
    print(f"{out}  {lufs(out):.1f} LUFS")
    print(f"voix : niveau médian {v_med:.1f} dB, pic médian des syllabes {v_pk:.1f} dB")
    print(f"bruitages : niveau max {lfx.max():.1f} dB (≥ {v_med - lfx.max():.1f} dB sous la voix), "
          f"pic max {pfx.max():.1f} dB (≥ {v_pk - pfx.max():.1f} dB sous les syllabes)")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1])
