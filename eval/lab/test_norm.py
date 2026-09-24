import json, sys, unicodedata
sys.path.insert(0, '.')
import jiwer
from whisper_normalizers import BasicTextNormalizer, EnglishTextNormalizer
from tts_textnorm import UrduNormalizer, nospace, script_fractions
R = '/home/vector/tts-reference-voices'
un, b0, b1, en = UrduNormalizer(), BasicTextNormalizer(), BasicTextNormalizer(remove_diacritics=True), EnglishTextNormalizer()
ref = json.load(open(f'{R}/voices/shehbaz/references/references.json'))['qwen3-tts']['text']
print('REF      :', ref)
print('basic    :', b0(ref))
print('basic+rd :', b1(ref))
print('urdu     :', un(ref))
def cp(s): return ' '.join(f'{c}:{ord(c):04X}' for c in s)
for w in ['پُرعزم', 'وسطیٰ', 'وطنِ', 'ہوئے', 'گۓ', 'خانۂ', 'آج', 'بدقسمتی']:
    print(f'{w!r:12} basic={b0(w)!r:14} basic_rd={b1(w)!r:12} [{cp(b1(w))}]  urdu={un(w)!r}')
# idempotence + token counts over all Urdu texts
texts = []
p = json.load(open(f'{R}/bench/pools/ur.json'))
for k in ('short','medium','long','xlong'): texts += p[k]
texts += [s['plain_text'] for s in json.load(open(f'{R}/benchmarks/shehbaz_ur.json'))['samples']]
assert all(un(un(t)) == un(t) for t in texts), 'not idempotent'
splits = sum(len(b0(t).split()) - len(t.split()) for t in texts)
print(f'{len(texts)} Urdu texts: UrduNormalizer idempotent; whisper basic() adds {splits} spurious tokens total '
      f'(words split at harakat); texts affected: {sum(len(b0(t).split()) != len(un(t).split()) for t in texts)}')
# simulated ASR hypothesis for the reference text with typical orthographic variants
hyp = ref.replace('ی', 'ي').replace('ک', 'ك').replace('ُ', '').replace('ِ', '').replace('۔', '.').replace('خود مختاری', 'خودمختاری')
for name, f in [('raw', lambda s: s), ('whisper basic', b0), ('whisper basic rd', b1), ('urdu', un)]:
    r_, h_ = f(ref), f(hyp)
    print(f'{name:17} WER={jiwer.wer(r_, h_):.3f} CER={jiwer.cer(r_, h_):.3f} CER-nospace={jiwer.cer(nospace(r_), nospace(h_)):.3f}')
print('scripts', script_fractions('یہ test ہے'), script_fractions('यह एक परीक्षण है'))
# English
for a, b in [('The Prime Minister said thirty million lives.', 'the prime minister said 30 million lives'),
             ("We're going to win, 100 percent!", 'we are gonna win 100%'),
             ('It was twenty-five years ago, in nineteen ninety nine.', 'It was 25 years ago in 1999.'),
             ('Colour and favourite', 'color and favorite')]:
    print(repr(en(a)), '|', repr(en(b)), '| WER', round(jiwer.wer(en(a), en(b)), 3))
