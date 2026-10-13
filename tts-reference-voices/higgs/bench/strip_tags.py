#!/usr/bin/env python3
"""Before scoring a run whose requests carried Higgs control tags (bench_tts.py --prompt-field higgs_text): rewrite
each row's `text` to the tag-free text (keeping the tagged one in `text_tagged`) and recount `letters`, so WER / CER
and pace are measured against the words that were meant to be spoken, not against `<|emotion:elation|>`.

    python higgs/bench/strip_tags.py higgs/results/Q_prompts/Q4_expr_tags_*/requests.jsonl
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TAG = re.compile(r"<\|[a-z_]+:[a-z_]+\|>")


def count_letters(text: str) -> int:
    return sum(1 for ch in text if ch.isalnum())


def main() -> None:
    for path in map(Path, sys.argv[1:]):
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        n = 0
        for r in rows:
            text = r.get("text") or ""
            if TAG.search(text) and "text_tagged" not in r:
                r["text_tagged"] = text
                r["text"] = re.sub(r"\s{2,}", " ", TAG.sub("", text)).strip()
                r["letters"] = count_letters(r["text"])
                if r.get("audio_s") and r.get("pace") and r["letters"]:
                    r["s_per_letter"] = round(r["audio_s"] / r["letters"], 5)
                    r["pace_ratio"] = round(r["s_per_letter"] / r["pace"], 3)
                n += 1
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
        print(f"{path}: {n} rows de-tagged")


if __name__ == "__main__":
    main()
