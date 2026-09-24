# tts-reference-voices

Reference voices and benchmark texts for voice-clone TTS (Qwen3-TTS 12Hz 1.7B Base, Higgs Audio v3), as used in
the September 2026 expressive-tag experiments. Each voice folder follows the `voice-server/v1` layout
(`VOICES_DIR/<id>/`): clips, `transcripts.json` with their exact words, `clips.json` with where every clip came
from, `voice.json` with display metadata, and `references/` with the exact combined references those runs
conditioned on.

```
voices/
  trump/     1 clip, 23 s, English, podium speech
  shehbaz/   8 clips, 90 s, Urdu, formal televised address
benchmarks/
  trump_en.json                 43 English test prompts
  shehbaz_ur.json               43 Urdu test prompts
  shehbaz_ur_expressive.json    the same Urdu prompts, re-tagged for livelier Higgs delivery
bench/
  bench_tts.py                  concurrency / text-length / streaming-latency benchmark for a /v1/audio/speech server
  pools/{en,ur}.json            de-duplicated short / medium / long / xlong text pools
NOTES.md                        everything learned so far: settings, measured numbers, failure modes, vLLM-Omni API
```

**Setting up a server? Read `NOTES.md` first, then `bench/README.md`.**

## Which reference to use

| file | for | what it is |
|---|---|---|
| `references/qwen3-tts.wav` | Qwen3-TTS (in-context clone) | best-ranked clips joined, up to 30 s, with the matching transcript in `references.json` |
| `references/higgs-v3.wav` | Higgs Audio v3 | **trump**: the whole clip. **shehbaz**: the three most animated clips (05, 06, 08; 39 s), picked by pitch variation |
| `references/higgs-v3-full90.wav` | Higgs Audio v3 | **shehbaz** only: all 90 s. Kept for comparison: it made every emotion come out flat |

Every reference is built the same way: each clip is cleaned (24 kHz mono, 60 Hz high-pass, silence-trimmed,
-20 LUFS), clips are ranked, and they're joined with 0.35 s gaps. `references.json` lists the source clips,
the transcript to pass as the reference text, and a sha256 for each file.

## What worked, and what to watch for

**Qwen3-TTS (Base, voice clone)**

- **Sampling:** temperature 0.9, top_k 50, repetition_penalty 1.05. Output is 24 kHz.
- **Conditioning:** the in-context prompt is the reference audio plus its exact transcript. The speaker x-vector is averaged over every clip.
- **No tags or instructions:** the Base model has no inline tags and no `instruct`. Send `plain_text` from the benchmarks; bracket tags like `[angry]` are read out loud.
- **Urdu isn't a supported language.** With `language="Auto"` it speaks recognizable, accented Urdu, but in 4 of 43 prompts it skipped a sentence, padded with silence and filler, or looped on a repeated syllable. Check each output's duration against the text length, and ideally its WER, then retry with a new seed.

**Higgs Audio v3**

- **Sampling:** temperature 0.8, top_k 50, top_p off (Boson's recommended cloning settings).
- **Delivery comes from the reference.** A long, calm reference flattens every tag. A shorter, livelier one plus the tags restated at the start of every sentence (as in `shehbaz_ur_expressive.json`) raised the shouting sample from 163 Hz to 226 Hz median pitch, and from 3.9 to 6.3 semitones of pitch variation.
- **30 s ceiling:** a generation ends at about 30 s and silently drops the rest of the text. Split longer text at sentence ends into parts of about 20 s, open each part with the tags still in force, and join the parts.
- **Weak speed tags in Urdu:** fast and very-fast barely changed the speaking rate.

## Benchmarks

Each file has 43 samples, one per Higgs control tag. Every sample has `higgs_text` (with `<|category:value|>` tags) and
`plain_text` (tags removed, for models without tag support). The texts are **fictional test prompts** written in
the speaker's register for benchmarking. They are not real statements by the speaker, and the topics are
deliberately apolitical.

## Provenance and use

- **Sources:** the clips are short excerpts of public broadcasts; see each folder's `clips.json` for the source video and cut points.
- **Rights:** they stay with the broadcasters. The clips are here for research and benchmarking of speech synthesis.
- **Don't impersonate:** don't use them to impersonate the speakers or to make audio presented as real statements.
- **Label your output:** mark anything you generate from them as AI-generated.
