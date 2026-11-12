"""Version « +4 dB » validée par Louis (vidéos du gland et du fumier) : le son doux à -10 LUFS, poussé de 4 dB dans
le limiteur (≈ -8,3 LUFS, pics < -0,4 dBFS), sans grésillement.

    python3 src/mastering.py output/ma_video.mp4        → output/ma_video_plus4db.mp4 et ..._plus4db_leger.mp4

Le gain est calé automatiquement pour chaque voix (elles n'arrivent pas toutes au même niveau).
"""
import os
import re
import subprocess
import sys

PRE = "highpass=f=110:p=2,equalizer=f=250:t=q:w=1:g=-1.5,equalizer=f=2600:t=q:w=1:g=1.5"
CMP = ("compand=attacks=0.012:decays=0.25:points=-80/-80|-40/-30|-24/-17|-12/-10|0/-5:soft-knee=10:gain=0,"
       "acompressor=threshold=-16dB:ratio=3:attack=8:release=90:knee=6")
LIM = "alimiter=limit=0.85:attack=5:release=60:level=false"
SAFE = "alimiter=limit=0.84:attack=1:release=20:level=false"     # rattrape les pics de l'encodage AAC


def lufs(path, af=None):
    cmd = ["ffmpeg", "-nostats", "-i", path]
    if af:
        cmd += ["-af", af + ",ebur128"]
    else:
        cmd += ["-af", "ebur128"]
    out = subprocess.run(cmd + ["-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])


def gain_for(src, target=-10.0):
    """Gain (dB) avant le limiteur pour que la version douce tombe à `target` LUFS (deux passes)."""
    v = 8.0
    for _ in range(3):
        got = lufs(src, f"{PRE},{CMP},volume={v:.2f}dB,{LIM}")
        v += (target - got) * 1.6          # le limiteur rogne une partie du gain : on corrige un peu plus fort
        if abs(target - got) < 0.1:
            break
    return v


def main(src):
    base, ext = os.path.splitext(src)
    v = gain_for(src) + 4.0
    out = base + "_plus4db" + ext
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-c:v", "copy", "-af",
                    f"{PRE},{CMP},volume={v:.2f}dB,{LIM},{SAFE}", "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
                    "-movflags", "+faststart", out], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", out, "-c:v", "libx264", "-crf", "28", "-preset",
                    "slow", "-maxrate", "1500k", "-bufsize", "3000k", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", base + "_plus4db_leger" + ext], check=True)
    print(out, f"{lufs(out):.1f} LUFS")


if __name__ == "__main__":
    main(sys.argv[1])
