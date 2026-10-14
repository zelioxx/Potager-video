# Generates one wav per clause with Kokoro (ff_siwis) and records clause timings per line.
import json, re, sys, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
P = sys.argv[1]; speed = float(sys.argv[2])
k = Kokoro("/root/.cache/hyperframes/tts/models/kokoro-v1.0.onnx", "/root/.cache/hyperframes/tts/voices/voices-v1.0.bin")
lines = json.load(open(f"{P}/build/script.json"))
out = []
for ln in lines:
    clauses = [c.strip() for c in re.findall(r"[^,:;…?!.]+[,:;…?!.]*", ln["text"]) if c.strip()]
    pieces, info, t = [], [], 0.0
    for c in clauses:
        spoken = c.replace("…", ",")
        a, sr = k.create(spoken, voice="ff_siwis", speed=speed, lang="fr-fr")
        dur = len(a)/sr
        info.append({"text": c, "start": round(t,3), "end": round(t+dur,3)})
        pieces.append(a)
        gap = 0.32 if c[-1] in ".?!…" else (0.2 if c[-1] in ":," else 0.06)
        pieces.append(np.zeros(int(gap*sr), dtype=np.float32)); t += dur + gap
    audio = np.concatenate(pieces[:-1])
    sf.write(f"{P}/assets/audio/{ln['id']}.wav", audio, sr)
    out.append({"id": ln["id"], "text": ln["text"], "duration": round(len(audio)/sr,3), "clauses": info})
    print(ln["id"], round(len(audio)/sr,2), "s")
json.dump(out, open(f"{P}/build/voice.json","w"), ensure_ascii=False, indent=1)
print("total", round(sum(o["duration"] for o in out),2))
