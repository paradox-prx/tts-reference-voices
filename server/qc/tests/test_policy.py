"""Decision logic (policy.gate / policy.bad) on fake metrics."""
from __future__ import annotations

import pytest

from tts_qc import policy
from tts_qc.policy import BAD, GATE, Thresholds

GOOD_AUDIO = {"duration_s": 10.0, "speech_ratio": 0.9, "lead_sil_s": 0.1, "trail_sil_s": 0.2,
              "max_internal_sil_s": 0.6, "pace_ratio": 1.0}
GOOD_ASR = {"wer": 0.05, "cer": 0.02, "cer_nospace": 0.02, "char_ratio": 1.0, "del_run": 0, "ins_run": 0,
            "repeat_excess": 0, "token_run": 1, "token_run_ref": 1, "char_runs": 0, "char_runs_ref": 0,
            "max_word_s": 1.2, "max_word_voiced": 0.95, "max_gap_s": 0.4, "max_gap_voiced": 0.9,
            "unaligned_tail_s": 0.3, "seg_max_cr": 1.5,
            "script_arabic": 1.0, "script_arabic_ref": 1.0}
GOOD_SIM = {"sim_speech_s": 9.5, "sim_prompt_base": 0.97, "sim_heldout_base": 0.97, "sim_prompt_large": 0.8,
            "sim_heldout_large": 0.8}


def take(**changes) -> dict:
    return {**GOOD_AUDIO, **GOOD_ASR, **GOOD_SIM, **changes}


@pytest.mark.parametrize("lang", ["en", "ur"])
def test_good_take_passes_gate_and_is_not_bad(lang: str) -> None:
    assert policy.gate(take(), lang) == []
    assert policy.bad(take(), lang) == []


@pytest.mark.parametrize("changes, lang, reason", [
    ({"cer_nospace": 0.2}, "ur", "cer_nospace>0.15"),
    ({"wer": 0.25}, "en", "wer>0.2"),
    ({"char_ratio": 0.8}, "ur", "char_ratio<0.85"),
    ({"char_ratio": 1.2}, "en", "char_ratio>1.15"),
    ({"del_run": 4}, "ur", "del_run>=4"),
    ({"del_run": 3}, "en", "del_run>=3"),
    ({"ins_run": 4}, "en", "ins_run>=4"),
    ({"repeat_excess": 4}, "ur", "repeat_excess>=4"),
    ({"token_run": 3}, "ur", "token_run>=3"),
    ({"char_runs": 1}, "ur", "char_run>=1"),
    ({"max_word_s": 5.5, "max_word_voiced": 0.99}, "ur", "long_word>2.5"),
    ({"max_gap_s": 9.0, "max_gap_voiced": 0.97}, "en", "word_gap>2"),
    ({"unaligned_tail_s": 6.4}, "ur", "unaligned_tail>3"),
    ({"max_internal_sil_s": 4.0}, "ur", "pause>2"),
    ({"trail_sil_s": 6.0}, "en", "trail_sil>1.5"),
    ({"lead_sil_s": 1.2}, "en", "lead_sil>1"),
    ({"speech_ratio": 0.5}, "en", "speech_ratio<0.6"),
    ({"speech_ratio": 0.0}, "en", "no_speech"),
    ({"pace_ratio": 0.5}, "ur", "pace<0.6"),
    ({"pace_ratio": 2.0}, "ur", "pace>1.8"),
    ({"sim_prompt_base": 0.86}, "en", "sim<0.88"),
])
def test_each_gate_rule(changes: dict, lang: str, reason: str) -> None:
    reasons = policy.gate(take(**changes), lang)
    assert reasons == [reason]
    # the offline label is stricter: whatever fails the gate is also bad, except SIM, which `bad` judges with the
    # other model (WavLM-Large; see test_sim_thresholds_follow_duration_bucket_and_model)
    if not reason.startswith("sim"):
        assert policy.bad(take(**changes), lang)


def test_language_specific_text_gates() -> None:
    # Urdu gates on CER-nospace, not WER (Whisper's own Urdu WER is 13-26 % on real speech)
    assert policy.gate(take(wer=0.3, cer_nospace=0.05), "ur") == []
    # English gates on WER; the deletion-run limit is lower for English (3) than for Urdu (4)
    assert policy.gate(take(cer_nospace=0.3), "en") == []
    assert policy.gate(take(del_run=3), "ur") == []


def test_repeats_the_input_already_has_do_not_count() -> None:
    assert policy.gate(take(token_run=3, token_run_ref=3), "ur") == []
    assert policy.gate(take(char_runs=1, char_runs_ref=1), "ur") == []


def test_long_pause_absorbed_into_a_word_or_between_words_is_not_a_loop() -> None:
    # synthetic 4 s gap: the ASR stretches one word to 5.24 s but only 26 % of it is voiced
    assert policy.gate(take(max_word_s=5.24, max_word_voiced=0.26), "ur") == []
    # the same pause left between two words (silent) is judged by the pause check, not the word-gap check
    assert policy.gate(take(max_gap_s=4.0, max_gap_voiced=0.05), "en") == []


def test_sim_thresholds_follow_duration_bucket_and_model() -> None:
    assert policy.gate(take(sim_speech_s=3.0, sim_prompt_base=0.86), "en") == []            # short bucket: 0.85
    assert policy.gate(take(sim_speech_s=3.0, sim_prompt_base=0.84), "en") == ["sim<0.85"]
    assert policy.gate(take(sim_speech_s=1.5, sim_prompt_base=0.10), "en") == []            # < 2 s: no verdict
    assert policy.gate(take(sim_prompt_large=0.45), "en", sim_model="large") == ["sim<0.5"]
    assert policy.gate(take(sim_prompt_large=0.45, sim_speech_s=4.0), "en", sim_model="large") == []
    assert policy.bad(take(sim_prompt_large=0.45), "en") == ["sim<0.5"]
    # bad also checks the held-out centroid; the gate does not
    assert policy.bad(take(sim_heldout_large=0.45), "ur") == ["sim_heldout<0.5"]
    assert policy.gate(take(sim_heldout_base=0.5), "ur") == []


def test_missing_metrics_and_disabled_checks_give_no_reason() -> None:
    audio_only = {**GOOD_AUDIO}
    assert policy.gate(audio_only, "ur") == []
    assert policy.gate(take(wer=0.9, cer_nospace=0.9, sim_prompt_base=0.1), "ur", checks=["audio"]) == []
    assert policy.gate(take(wer=0.9, cer_nospace=0.9), "und") == []            # no ASR verdict for 'und'
    assert policy.gate(take(sim_prompt_base=0.1), "en", sim_model=None) == []


def test_bad_only_detectors() -> None:
    assert policy.gate(take(seg_max_cr=14.0), "ur") == []
    assert policy.bad(take(seg_max_cr=14.0), "ur") == ["cr>2.4"]
    assert policy.bad(take(script_arabic=0.5), "ur") == ["script_drift"]
    assert policy.bad(take(script_arabic=0.5), "en") == []


def test_several_reasons_are_all_reported() -> None:
    reasons = policy.gate(take(cer_nospace=0.4, char_ratio=0.6, del_run=9, trail_sil_s=3.0), "ur")
    assert reasons == ["trail_sil>1.5", "cer_nospace>0.15", "char_ratio<0.85", "del_run>=4"]


def test_reason_codes_parse_into_metric_names_like_the_gateway() -> None:
    reasons = policy.gate(take(cer_nospace=0.4, del_run=9, sim_prompt_base=0.1, trail_sil_s=3), "ur")
    names = [r.split(">")[0].split("<")[0].strip() for r in reasons]            # gateway quality.py
    assert names == ["trail_sil", "cer_nospace", "del_run", "sim"]


def test_thresholds_from_env_and_overrides() -> None:
    t = Thresholds.from_env(GATE, environ={"TTS_QC_CER_NOSPACE_UR": "0.12", "TTS_QC_DEL_RUN_EN": "5",
                                           "TTS_QC_SIM_HELDOUT": "yes", "TTS_QC_PORT": "1"})
    assert (t.cer_nospace_ur, t.del_run_en, t.sim_heldout) == (0.12, 5, True)
    assert policy.gate(take(cer_nospace=0.13), "ur", t) == ["cer_nospace>0.12"]
    assert GATE.updated({"wer_en": 0.3}).wer_en == 0.3
    with pytest.raises(ValueError):
        GATE.updated({"no_such_threshold": 1})


def test_bad_thresholds_are_at_least_as_strict_as_gate() -> None:
    g, b = GATE.as_dict(), BAD.as_dict()
    for lower_is_stricter in ("cer_nospace_ur", "wer_en", "char_ratio_hi", "del_run_ur", "del_run_en", "ins_run",
                              "repeat_excess", "long_word_s", "word_gap_s", "unaligned_tail_s", "pace_hi"):
        assert b[lower_is_stricter] <= g[lower_is_stricter], lower_is_stricter
    for higher_is_stricter in ("char_ratio_lo", "pace_lo"):
        assert b[higher_is_stricter] >= g[higher_is_stricter], higher_is_stricter
