"""Transcription (Whisper medium, sherpa-onnx) par blocs de ~10 s coupés dans les silences.
    python3 outils/asr3.py <dossier_travail> <voix_16k.wav>      (modèles dans <dossier_travail>/models)"""
import sherpa_onnx, soundfile as sf, sys, re, subprocess
S = sys.argv[1]; wav = sys.argv[2]; M = S + "/models/sherpa-onnx-whisper-medium/"
audio, sr = sf.read(wav, dtype="float32")
out = subprocess.run(["ffmpeg", "-i", wav, "-af", "silencedetect=n=-35dB:d=0.25", "-f", "null", "-"], capture_output=True, text=True).stderr
starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]; ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
cuts = [(a + b) / 2 for a, b in zip(starts, ends)]; dur = len(audio) / sr
segs = []; s0 = 0
for c in cuts + [dur]:
    if c - s0 > 9 or c == dur: segs.append((s0, c)); s0 = c
rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=M + "medium-encoder.int8.onnx", decoder=M + "medium-decoder.int8.onnx", tokens=M + "medium-tokens.txt", language="fr", task="transcribe", num_threads=4)
for a, b in segs:
    st = rec.create_stream(); st.accept_waveform(sr, audio[int(a * sr):int(b * sr)]); rec.decode_stream(st)
    print(f"{a:.1f}-{b:.1f}: {st.result.text.strip()}", flush=True)
