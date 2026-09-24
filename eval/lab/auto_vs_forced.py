"""Auto language detection vs forced language on the real reference clips (CPU). Prints detected language,
its probability, the top-5 language probabilities and the script mix of the auto transcript."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from faster_whisper import WhisperModel, decode_audio  # noqa: E402
from tts_textnorm import script_fractions               # noqa: E402

model = WhisperModel(sys.argv[1], device="cpu", compute_type="int8", cpu_threads=int(sys.argv[2]) if len(sys.argv) > 2 else 8)
for line in open(Path(__file__).parent / "refs_manifest.jsonl", encoding="utf-8"):
    r = json.loads(line)
    audio = decode_audio(r["file"], sampling_rate=16000)
    lang, prob, allp = model.detect_language(audio=audio[: 30 * 16000])
    top = sorted(allp, key=lambda x: -x[1])[:5]
    segs, info = model.transcribe(r["file"], language=None, beam_size=5, condition_on_previous_text=False)
    hyp = " ".join(s.text.strip() for s in segs)
    print(json.dumps({"file": Path(r["file"]).name, "detected": lang, "p": round(prob, 3),
                      "top5": [(l, round(p, 3)) for l, p in top], "auto_hyp_scripts": script_fractions(hyp),
                      "auto_hyp": hyp[:90]}, ensure_ascii=False), flush=True)
