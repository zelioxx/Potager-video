"""Version « voix au maximum » : la voix seule est rendue la plus forte possible SANS grésiller, puis on ajoute
les bruitages (et, en option, une petite musique de fond) nettement en dessous, sans pics.

    python3 src/mastering_voix.py fumier            → output/<vidéo>_voix_max.mp4 (+ _leger)
    python3 src/mastering_voix.py fumier --musique  → output/<vidéo>_voix_max_musique.mp4 (+ _leger)

Voix : coupe des graves inutiles, porte douce (les blancs restent propres, comme sur les comptes de référence),
présence vers 3 kHz et un peu d'air (la voix paraît plus forte à volume égal), dé-esseur, compression douce, puis
le gain le plus fort possible tant que le limiteur reste discret (médiane ≤ 1,5 dB, 95e centile ≤ 6 dB : le niveau de la version « +4 dB » que tu as jugée propre) :
au-delà, c'est là que la voix commence à « grésiller ». Pics finaux sous -1,5 dB, 44,1 kHz (format de sortie de
TikTok) pour qu'il ne reste plus de saturation après leur réencodage.
"""
import os
import re
import subprocess
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE = ("highpass=f=90:p=2,agate=threshold=0.012:ratio=2.5:range=0.12:attack=3:release=200,"
         "equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1.2:g=3,treble=g=2:f=8000,deesser=i=0.4,"
         "acompressor=threshold=-22dB:ratio=3:attack=6:release=90:knee=6:makeup=4,"
         "acompressor=threshold=-10dB:ratio=4:attack=1.5:release=40:knee=4")      # attrape les attaques avant le limiteur
LIM = "alimiter=limit=0.84:attack=4:release=60:level=false"
FX_UNDER, FX_PEAK_UNDER = 14.0, 12.0          # bruitages : sous le niveau médian de la voix / sous les syllabes
MUS_UNDER, MUS_DUCK = 19.0, 6.0               # musique : sous la voix dans les blancs, et encore -6 dB sous la parole
SR = 44100


def ff(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def lufs(path):
    out = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1]), float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out)[-1])


def db(a):
    return 20 * np.log10(np.maximum(a, 1e-9))


def win(x, w, fn):
    k = int(w * SR)
    n = len(x) // k
    return fn(x[: n * k].reshape(n, k))


def voice_master(src, tmp):
    """Gain le plus fort possible avant que le limiteur ne travaille trop."""
    pre = os.path.join(tmp, "v_pre.wav")
    ff("-i", src, "-af", f"aresample={SR}:resampler=soxr,{VOICE}", "-c:a", "pcm_f32le", "-ac", "1", pre)
    best = None
    for g in np.arange(0.0, 16.01, 1.0):
        post = os.path.join(tmp, "v_post.wav")
        ff("-i", pre, "-af", f"volume={g:.1f}dB,{LIM}", "-c:a", "pcm_f32le", post)
        a, _ = sf.read(pre)
        b, _ = sf.read(post)
        a = a * 10 ** (g / 20)
        n = min(len(a), len(b))
        ea = win(a[:n], 0.01, lambda m: np.sqrt((m ** 2).mean(1)))
        eb = win(b[:n], 0.01, lambda m: np.sqrt((m ** 2).mean(1)))
        act = ea > 0.02
        gr = db(ea[act]) - db(eb[act])
        med, p95 = np.median(gr), np.percentile(gr, 95)
        if med <= 1.5 and p95 <= 6.0:
            best = (g, med, p95)
        else:
            break
    g, med, p95 = best
    out = os.path.join(tmp, "v_master.wav")
    ff("-i", pre, "-af", f"volume={g:.1f}dB,{LIM}", "-c:a", "pcm_f32le", out)
    print(f"voix : +{g:.0f} dB avant le limiteur (réduction médiane {med:.1f} dB, 95e centile {p95:.1f} dB)")
    return out


def main(project, music=False):
    sys.argv = ["render.py", project]
    sys.path.insert(0, os.path.join(ROOT, "src"))
    import render
    tmp = os.path.join(ROOT, "output", "tmp_voixmax_" + project)
    os.makedirs(tmp, exist_ok=True)
    sv, sfx_ = os.path.join(tmp, "voix.wav"), os.path.join(tmp, "bruitages.wav")
    render.build_audio(os.path.join(tmp, "mix.wav"), stems=(sv, sfx_))
    v, _ = sf.read(voice_master(sv, tmp))
    fx, sr0 = sf.read(sfx_)
    fx = np.interp(np.linspace(0, len(fx) - 1, int(len(fx) * SR / sr0)), np.arange(len(fx)), fx)
    n = min(len(v), len(fx))
    v, fx = v[:n], fx[:n]
    lv = win(v, 0.1, lambda m: db(np.sqrt((m ** 2).mean(1))))
    pv = win(v, 0.01, lambda m: db(np.abs(m).max(1)))
    v_med = np.median(lv[lv > lv.max() - 30])
    v_pk = np.median(pv[pv > pv.max() - 12])
    # bruitages : le plus fort à 14 dB sous la voix, pics plafonnés 12 dB sous les syllabes
    lf = win(fx, 0.1, lambda m: db(np.sqrt((m ** 2).mean(1))))
    fx *= 10 ** ((v_med - FX_UNDER - lf.max()) / 20)
    pf = win(fx, 0.01, lambda m: np.abs(m).max(1))
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    gg = uniform_filter1d(minimum_filter1d(np.minimum(1, 10 ** ((v_pk - FX_PEAK_UNDER) / 20) / np.maximum(pf, 1e-9)),
                                           5), 3)
    env = np.repeat(gg, int(0.01 * SR))
    fx *= np.concatenate([env, np.full(n - len(env), 1.0)])
    mix = v + fx
    if music:
        from musique import bed
        m = bed(n / SR, SR)[:n].astype(np.float64)
        lm = win(m, 0.1, lambda a: db(np.sqrt((a ** 2).mean(1))))
        m *= 10 ** ((v_med - MUS_UNDER - np.percentile(lm, 90)) / 20)
        # elle s'efface sous la voix (ducking doux) et remonte un peu dans les blancs
        e = np.repeat(lv > v_med - 18, int(0.1 * SR)).astype(np.float64)
        e = np.concatenate([e, np.zeros(n - len(e))])
        e = uniform_filter1d(e, int(0.35 * SR))
        m *= 10 ** (-MUS_DUCK * e / 20)
        mix = mix + m
    tag = "_voix_max_musique" if music else "_voix_max"
    wav = os.path.join(tmp, "mix_final.wav")
    sf.write(wav, np.stack([mix, mix], 1), SR, subtype="FLOAT")
    video = os.path.join(ROOT, "output", render.CFG["out"])
    base, ext = os.path.splitext(video)
    out = base + tag + ext
    # pics après encodage AAC sous -1 dB (sinon le réencodage de TikTok sature) : on resserre si besoin
    for lim in (0.82, 0.8, 0.75, 0.71):
        ff("-i", video, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
           "-af", f"aresample=176400:resampler=soxr,alimiter=limit={lim}:attack=1:release=20:level=false,"
                  f"aresample={SR}:resampler=soxr", "-c:a", "aac", "-b:a", "256k",      # limiteur suréchantillonné
           "-ar", str(SR), "-shortest", "-movflags", "+faststart", out)
        if lufs(out)[1] <= -1.0:
            break
    ff("-i", out, "-c:v", "libx264", "-crf", "28", "-preset", "slow", "-maxrate", "1500k", "-bufsize", "3000k",
       "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", base + tag + "_leger" + ext)
    i, tp = lufs(out)
    print(f"{out}  {i:.1f} LUFS, pic {tp:.1f} dB")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1], "--musique" in sys.argv)
