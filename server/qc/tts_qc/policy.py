"""Verdicts on one take's metrics (scorer.Scorer.score): the online `gate` and the offline, stricter `bad` label.

gate  What production computes per non-streaming take: the gateway's pace band (TTS_SUSPECT_BAND, 0.6-1.8 x the
      voice's expected s/letter) plus this sidecar's ASR, audio and SIM checks with GATE thresholds. A failing take is
      retried by the gateway (fresh sampling).
bad   An independent-as-possible offline label for evaluating the gate and the retry policy (server/eval/retry_sim.py):
      stricter thresholds on the same ASR metrics, the other SIM model (WavLM-Large, the seed-tts scale, instead of
      the gate's wavlm-base-plus-sv), and two extra detectors (Whisper compression ratio, script drift). It shares the
      ASR with the gate, so it is a proxy, not ground truth: human listening of all gate-fails plus ~10-15% of passes
      is the real oracle (eval-tooling.md finding 27); retry_sim.py --labels takes such labels.

Reason codes are "<metric><op><threshold>" ("cer_nospace>0.15", "del_run>=4", "sim<0.88", "trail_sil>1.5"), so the
gateway's metrics label (the part before '>' / '<') is the metric name. Definitions (checks.py, scorer.py):
  wer / cer_nospace   normalized word error rate / character error rate with all spaces removed (Urdu)
  char_ratio          ASR letters / input letters (after normalization): < lo skipped text, > hi loop or filler
  del_run / ins_run   longest run of consecutive deleted / inserted words in the alignment
  repeat_excess       n-gram repetition beyond the input text, weighted by n (n = 1..4)
  token_run           longest run of one repeated word (counts only when longer than the input's own)
  char_run            letters repeated >= 4 times in a row ('آآآآ'), beyond the input's own
  long_word           longest ASR word timestamp > threshold with > long_word_voiced of it voiced: a loop the ASR
                      swallowed (synthetic Urdu loops: 4.9-5.5 s, 98-99 % voiced; a 4 s pause: 5.2 s, 26 % voiced)
  word_gap            longest stretch before / between ASR words that no word covers, when > word_gap_voiced of it
                      is voiced: a loop the ASR skipped (English 3 x 3 s phrase loop: a 9.0 s gap, 97 % voiced)
  unaligned_tail      seconds of audio after the last ASR word (babble, filler, noise tail)
  pause / lead_sil / trail_sil   longest internal / leading / trailing silence (energy VAD, 20 ms, p95 - 35 dB)
  speech_ratio        voiced frames / all frames
  pace                (duration / input letters) / the voice's expected s/letter
  sim                 cosine(take, prompt reference) with the gate's SIM model, threshold by the take's speech
                      duration (leading/trailing silence trimmed): no verdict under sim_min_s, `short` under
                      sim_long_s, `long` above
  cr                  largest Whisper segment compression ratio (UTF-8 bytes): real Urdu <= 1.8, loops 14-18
  script_drift        Urdu: share of Arabic-script letters in the transcript more than 10 points below the input's
The initial thresholds are the eval research's proposals (eval-tooling.md findings 17, 21, 26) and the Kaggle notes;
recalibrate them on the first scored batch of good takes (about the 1st percentile of good takes).
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, fields, replace
from typing import Iterable

CHECKS = ("asr", "sim", "audio")


@dataclass(frozen=True)
class Thresholds:
    # ASR (text) checks; language-specific where the language matters
    cer_nospace_ur: float = 0.15    # Urdu gates on CER-nospace: Whisper's own Urdu WER is 13-26 % on real speech
    wer_en: float = 0.20            # English: Kaggle good takes < 1 % WER; 0.22 was the NOTES re-roll rule
    char_ratio_lo: float = 0.85
    char_ratio_hi: float = 1.15
    del_run_ur: int = 4
    del_run_en: int = 3
    ins_run: int = 4
    repeat_excess: int = 4
    token_run: int = 3
    char_run: int = 1
    long_word_s: float = 2.5        # real clips: longest word 1.0-2.2 s
    long_word_voiced: float = 0.8
    word_gap_s: float = 2.0         # real: voiced gaps <= 0.68 s; a 2.52 s pause at 36 %
    word_gap_voiced: float = 0.5
    unaligned_tail_s: float = 3.0   # real clips 0.09-0.49 s; a 6 s noise/silence tail 6.4 s
    # audio checks (energy VAD) and pace
    pause_s: float = 2.0            # real clips: longest natural pause <= 1.5 s
    trail_sil_s: float = 1.5
    lead_sil_s: float = 1.0
    speech_ratio: float = 0.6
    pace_lo: float = 0.6            # = the gateway's TTS_SUSPECT_BAND
    pace_hi: float = 1.8
    # speaker similarity vs the prompt reference, by trimmed speech duration
    sim_min_s: float = 2.0          # a 2 s crop already loses ~0.2 (WavLM-Large): no verdict below this
    sim_long_s: float = 5.0
    sim_short_base: float = 0.85
    sim_long_base: float = 0.88     # the Kaggle gate; base-plus-sv cross-speaker 0.75-0.80, same speaker >= 0.975
    sim_short_large: float = 0.40
    sim_long_large: float = 0.50    # WavLM-Large cross-speaker 0.11-0.18, same speaker 0.87-0.95
    sim_heldout: bool = False       # also require the held-out-centroid SIM above the same threshold
    # extra detectors (0 = off)
    max_cr: float = 0.0             # Whisper compression ratio (its own fallback threshold is 2.4)
    script_drift: float = 0.0       # Urdu: allowed drop of the Arabic-script share vs the input (0.1 = 10 points)

    @classmethod
    def from_env(cls, base: "Thresholds | None" = None, prefix: str = "TTS_QC_",
                 environ: dict[str, str] | None = None) -> "Thresholds":
        """`base` with every field overridden by <prefix><FIELD> (e.g. TTS_QC_CER_NOSPACE_UR=0.12)."""
        env = os.environ if environ is None else environ
        base = base or cls()
        changes = {}
        for f in fields(cls):
            raw = env.get(prefix + f.name.upper())
            if raw is None or raw == "":
                continue
            typ = type(getattr(base, f.name))
            changes[f.name] = raw.strip().lower() in ("1", "true", "yes", "on") if typ is bool else typ(raw)
        return replace(base, **changes)

    def updated(self, overrides: dict | None) -> "Thresholds":
        if not overrides:
            return self
        unknown = set(overrides) - {f.name for f in fields(self)}
        if unknown:
            raise ValueError(f"unknown threshold(s): {sorted(unknown)}")
        return replace(self, **overrides)

    def as_dict(self) -> dict:
        return asdict(self)


GATE = Thresholds()
BAD = Thresholds(cer_nospace_ur=0.10, wer_en=0.10, char_ratio_lo=0.90, char_ratio_hi=1.10, del_run_ur=3, del_run_en=3,
                 ins_run=3, repeat_excess=3, long_word_s=2.0, word_gap_s=1.5, unaligned_tail_s=2.0, pace_lo=0.7,
                 pace_hi=1.5, sim_heldout=True, max_cr=2.4, script_drift=0.1)
GATE_SIM_MODEL = "base"    # the sidecar default (TTS_QC_SIM_MODEL)
BAD_SIM_MODEL = "large"


def _g(x: float) -> str:
    return f"{x:g}"


def judge(m: dict, lang: str, t: Thresholds, sim_model: str | None, checks: Iterable[str] = CHECKS) -> list[str]:
    """Reason codes for one take (empty = pass). `m` is Scorer.score()'s metrics; checks whose metrics are missing
    (ASR off, language 'und', SIM skipped or too short) give no reason."""
    checks = set(checks)
    reasons: list[str] = []
    add = reasons.append
    if "audio" in checks and m.get("duration_s") is not None:
        if not m.get("speech_ratio"):
            add("no_speech")
        else:
            if m["max_internal_sil_s"] > t.pause_s:
                add(f"pause>{_g(t.pause_s)}")
            if m["lead_sil_s"] > t.lead_sil_s:
                add(f"lead_sil>{_g(t.lead_sil_s)}")
            if m["trail_sil_s"] > t.trail_sil_s:
                add(f"trail_sil>{_g(t.trail_sil_s)}")
            if m["speech_ratio"] < t.speech_ratio:
                add(f"speech_ratio<{_g(t.speech_ratio)}")
        pr = m.get("pace_ratio")
        if pr is not None:
            if pr < t.pace_lo:
                add(f"pace<{_g(t.pace_lo)}")
            elif pr > t.pace_hi:
                add(f"pace>{_g(t.pace_hi)}")
    if "asr" in checks and m.get("wer") is not None and lang in ("en", "ur"):
        if lang == "ur" and m["cer_nospace"] > t.cer_nospace_ur:
            add(f"cer_nospace>{_g(t.cer_nospace_ur)}")
        if lang == "en" and m["wer"] > t.wer_en:
            add(f"wer>{_g(t.wer_en)}")
        cr = m.get("char_ratio")
        if cr is not None and cr < t.char_ratio_lo:
            add(f"char_ratio<{_g(t.char_ratio_lo)}")
        elif cr is not None and cr > t.char_ratio_hi:
            add(f"char_ratio>{_g(t.char_ratio_hi)}")
        dr = t.del_run_ur if lang == "ur" else t.del_run_en
        if m["del_run"] >= dr:
            add(f"del_run>={dr}")
        if m["ins_run"] >= t.ins_run:
            add(f"ins_run>={t.ins_run}")
        if m["repeat_excess"] >= t.repeat_excess:
            add(f"repeat_excess>={t.repeat_excess}")
        if m["token_run"] >= t.token_run and m["token_run"] > m.get("token_run_ref", 1):
            add(f"token_run>={t.token_run}")
        if m["char_runs"] - m.get("char_runs_ref", 0) >= t.char_run:
            add(f"char_run>={t.char_run}")
        if (m.get("max_word_s") or 0) > t.long_word_s and (m.get("max_word_voiced") or 0) > t.long_word_voiced:
            add(f"long_word>{_g(t.long_word_s)}")
        if (m.get("max_gap_s") or 0) > t.word_gap_s and (m.get("max_gap_voiced") or 0) > t.word_gap_voiced:
            add(f"word_gap>{_g(t.word_gap_s)}")
        if (m.get("unaligned_tail_s") or 0) > t.unaligned_tail_s:
            add(f"unaligned_tail>{_g(t.unaligned_tail_s)}")
        if t.max_cr and (m.get("seg_max_cr") or 0) > t.max_cr:
            add(f"cr>{_g(t.max_cr)}")
        if (t.script_drift and lang == "ur" and m.get("script_arabic") is not None
                and m["script_arabic"] < m.get("script_arabic_ref", 1.0) - t.script_drift):
            add("script_drift")
    if "sim" in checks and sim_model:
        s, dur = m.get(f"sim_prompt_{sim_model}"), m.get("sim_speech_s") or 0.0
        if s is not None and dur >= t.sim_min_s:
            thr = getattr(t, f"sim_{'long' if dur >= t.sim_long_s else 'short'}_{sim_model}")
            if s < thr:
                add(f"sim<{_g(thr)}")
            h = m.get(f"sim_heldout_{sim_model}")
            if t.sim_heldout and h is not None and h < thr:
                add(f"sim_heldout<{_g(thr)}")
    return reasons


def gate(m: dict, lang: str, t: Thresholds = GATE, sim_model: str | None = GATE_SIM_MODEL,
         checks: Iterable[str] = CHECKS) -> list[str]:
    return judge(m, lang, t, sim_model, checks)


def bad(m: dict, lang: str, t: Thresholds = BAD, sim_model: str | None = BAD_SIM_MODEL) -> list[str]:
    return judge(m, lang, t, sim_model, CHECKS)
