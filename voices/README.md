# Preset voices

Each folder here is one preset voice. Folders are scanned whenever the voice list is requested, so a new folder
appears in the Studio's voice list without code changes or a restart. The audio stays local: `.gitignore` keeps
everything in this folder except this README.

```
voices/
  callagent/
    callagent_01.wav        one or more reference clips (wav / mp3 / flac / ogg / opus / m4a; a .wav wins over other
                            formats of the same name)
    transcripts.json        {"callagent_01.wav": "exact words spoken in the clip"}   (required)
    persona.json            optional card overrides, see below
    reference.json          optional exact cut used as the reference, see below
  Asad(pashto)/             "(pashto)" in the folder name sets the language and gives the voice id "asad"
```

**Folder name.** The voice id is the lower-cased name without the bracketed part. The card's language comes
from `language` in `persona.json` (or the built-in defaults in `app/studio/personas.json`). Without one, a
bracketed hint in the folder name decides it: `(english)`, `(urdu)`, `(pashto)`, `(punjabi)`/`(shahmukhi)`,
`(gurmukhi)` or `(sindhi)`. With neither, the transcript's script decides.

**Reference length.** The engine accepts at most 30 s of reference audio. Clips that fit are joined with
0.3 s gaps up to 29.5 s. A longer first clip is cut automatically at a pause near a sentence end, with the
transcript cut at the matching place. That cut is estimated, not checked against the audio. For an exact
reference, write `reference.json`:

```json
{"clip": "callagent_01.wav", "start": 0.0, "end": 27.1, "text": "exact words spoken between start and end"}
```

`reference.json` can also be a list of such objects; they are joined in order.

**persona.json** (all keys optional):

```json
{"name": "Ali", "role": "Calm support agent", "language": "ur", "gender": "male",
 "description": "Warm, unhurried call-centre voice", "hidden": false, "public_figure": false,
 "delivery": {"speed": "normal", "expressiveness": "normal", "pitch": "normal", "emotion": "", "strength": "light"}}
```

`hidden: true` removes the voice from the Studio. `public_figure: true` marks the card as a real person's
voice.

**Pace.** Higgs copies the pace of the reference. The voice's seconds-per-letter, measured from the
reference, drives the duration estimates and the duration QC.
