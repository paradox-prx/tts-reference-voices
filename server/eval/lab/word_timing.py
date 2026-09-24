import sys, json
from faster_whisper import WhisperModel
m = WhisperModel('../models/faster-whisper-large-v3', device='cpu', compute_type='int8', cpu_threads=8)
V = '/home/vector/tts-reference-voices/voices'
for f, lang in [(f'{V}/shehbaz/shehbaz_02.wav', 'ur'), ('synth/ur_syllable_loop12.wav', 'ur'), ('synth/ur_phrase_loop3.wav', 'ur'), ('synth/ur_gap4s.wav', 'ur')]:
    segs, _ = m.transcribe(f, language=lang, beam_size=5, condition_on_previous_text=False, word_timestamps=True)
    words = [w for s in segs for w in s.words]
    durs = [(round(w.end - w.start, 2), w.word.strip()) for w in words]
    gaps = [round(b.start - a.end, 2) for a, b in zip(words, words[1:])]
    chars = sum(len(w.word.strip()) for w in words)
    span = words[-1].end - words[0].start
    print(f.split('/')[-1], 'n_words', len(words), 'max word dur', max(durs), 'max gap', max(gaps), 'chars/s', round(chars / span, 2),
          'low-prob words', [(w.word.strip(), round(w.probability, 2)) for w in words if w.probability < 0.5])
    print('   ', [(w.word.strip(), round(w.start, 2), round(w.end, 2)) for w in words][3:9])
