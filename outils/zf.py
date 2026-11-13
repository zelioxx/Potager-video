"""Horodatage des sons (zipformer FR en streaming) → <dossier>/zf.json.   python3 outils/zf.py <dossier_travail>"""
import sherpa_onnx, soundfile as sf, sys, json, numpy as np
S = sys.argv[1]; M = S + "/models/sherpa-onnx-streaming-zipformer-fr-2023-04-14/"
audio, sr = sf.read(S + "/voice16k.wav", dtype="float32")
r = sherpa_onnx.OnlineRecognizer.from_transducer(tokens=M + "tokens.txt", encoder=M + "encoder-epoch-29-avg-9-with-averaged-model.int8.onnx", decoder=M + "decoder-epoch-29-avg-9-with-averaged-model.int8.onnx", joiner=M + "joiner-epoch-29-avg-9-with-averaged-model.int8.onnx", num_threads=4, decoding_method="greedy_search")
s = r.create_stream(); s.accept_waveform(sr, audio); s.accept_waveform(sr, np.zeros(sr * 2, dtype=np.float32)); s.input_finished()
while r.is_ready(s): r.decode_stream(s)
res = r.get_result_all(s)
json.dump({"tokens": list(res.tokens), "ts": list(res.timestamps)}, open(S + "/zf.json", "w"), ensure_ascii=False)
print(r.get_result(s))
