# Generates one wav per script line, clause by clause, and records clause timings.
#   python3 -I build/tts.py <project> <voice_dir>
# <voice_dir> is a sherpa-onnx Piper voice (vits-piper-fr_FR-tom-medium from the k2-fsa/sherpa-onnx
# "tts-models" GitHub release). length_scale < 1 speeds the read up for a punchy delivery.
import glob, json, re, sys
import numpy as np, soundfile as sf, sherpa_onnx

P, VD = sys.argv[1], sys.argv[2]
LENGTH_SCALE, NOISE, NOISE_W = 0.84, 0.72, 0.9

model = glob.glob(f"{VD}/*.onnx")[0]
tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
    vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=model, tokens=f"{VD}/tokens.txt", data_dir=f"{VD}/espeak-ng-data",
                                               noise_scale=NOISE, noise_scale_w=NOISE_W, length_scale=LENGTH_SCALE),
    num_threads=4)))


def trim(x, sr, thr=0.012):
    """Cut leading/trailing silence so clause timings match the audible speech."""
    idx = np.where(np.abs(x) > thr)[0]
    if not len(idx):
        return x
    a, b = max(0, idx[0] - int(0.02 * sr)), min(len(x), idx[-1] + int(0.04 * sr))
    return x[a:b]


lines = json.load(open(f"{P}/build/script.json"))
out = []
for ln in lines:
    clauses = [c.strip() for c in re.findall(r"[^,:;…?!.]+[,:;…?!.]*", ln["text"]) if c.strip()]
    pieces, info, t = [], [], 0.0
    for c in clauses:
        g = tts.generate(c.replace("…", ","), sid=0, speed=1.0)
        sr = g.sample_rate
        a = trim(np.array(g.samples, dtype=np.float32), sr)
        dur = len(a) / sr
        info.append({"text": c, "start": round(t, 3), "end": round(t + dur, 3)})
        pieces.append(a)
        gap = 0.26 if c[-1] in ".?!…" else (0.14 if c[-1] in ":," else 0.04)
        pieces.append(np.zeros(int(gap * sr), dtype=np.float32))
        t += dur + gap
    audio = np.concatenate(pieces[:-1])
    sf.write(f"{P}/assets/audio/{ln['id']}.wav", audio, sr)
    out.append({"id": ln["id"], "text": ln["text"], "duration": round(len(audio) / sr, 3), "sample_rate": sr, "clauses": info})
    print(ln["id"], round(len(audio) / sr, 2), "s")
json.dump(out, open(f"{P}/build/voice.json", "w"), ensure_ascii=False, indent=1)
print("total", round(sum(o["duration"] for o in out), 2))
