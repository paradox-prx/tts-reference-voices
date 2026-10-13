import json
from tokenizers import Tokenizer, models, pre_tokenizers, normalizers, decoders, Regex
# Qwen2TokenizerFast pattern (transformers/models/qwen2/tokenization_qwen2.py PRETOKENIZE_REGEX)
PAT = r"""(?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+"""
bpe = models.BPE.from_file("hf/vocab.json", "hf/merges.txt")
tok = Tokenizer(bpe)
tok.normalizer = normalizers.NFC()
tok.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Split(Regex(PAT), behavior="isolated"), pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=False)])
tok.decoder = decoders.ByteLevel()
ur = json.load(open("/home/vector/tts-reference-voices/bench/pools/ur.json"))
en = json.load(open("/home/vector/tts-reference-voices/bench/pools/en.json"))
def stats(lang, pool):
    for size in ["short","medium","long","xlong"]:
        if size not in pool: continue
        items = pool[size]
        words = sum(len(t.split()) for t in items); chars = sum(len(t) for t in items)
        toks = sum(len(tok.encode(t).ids) for t in items)
        print(f"{lang} {size:6s} n={len(items):3d} words={words/len(items):7.1f} chars={chars/len(items):7.1f} tokens={toks/len(items):7.1f} tok/word={toks/words:.2f} tok/char={toks/chars:.2f}")
stats("ur", ur); stats("en", en)
s = ur["short"][0]
enc = tok.encode(s)
print(s)
print(len(enc.ids), enc.ids[:40])
print([tok.decode([i]) for i in enc.ids[:40]])
# check roundtrip
print(tok.decode(enc.ids) == s)
print("---- refs")
for v in ["shehbaz","trump"]:
    r = json.load(open(f"/home/vector/tts-reference-voices/voices/{v}/references/references.json"))["qwen3-tts"]
    n = len(tok.encode(r["text"]).ids)
    frames = r["duration"]*12.5
    print(v, "dur", r["duration"], "frames", round(frames), "ref_text_tokens", n, "words", len(r["text"].split()))
for t in ["assistant\nhello", "assistant\n hello", "assistant\n\nhello"]:
    e = tok.encode(t); print(repr(t), [tok.decode([i]) for i in e.ids])
