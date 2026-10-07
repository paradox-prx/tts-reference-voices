// Tag helpers mirroring app/studio/tags.py + text.py (the server re-validates everything).

export const TAG_RE = /<\|\s*([A-Za-z_]+)\s*:\s*([A-Za-z_]+)\s*\|>/g;
export const ANY_TAG_RE = /<\|[^|<>]*\|>/g;

export type Vocab = Record<string, string[]>;

export function isValid(vocab: Vocab, cat: string, val: string) {
  return !!vocab[cat] && vocab[cat].includes(val);
}

const PROSODY_SLOT: Record<string, string> = {
  speed_very_slow: "speed", speed_slow: "speed", speed_fast: "speed", speed_very_fast: "speed",
  pitch_low: "pitch", pitch_high: "pitch", expressive_high: "expressive", expressive_low: "expressive",
};
export function slotOf(cat: string, val: string) {
  if (cat === "prosody") return PROSODY_SLOT[val] ?? "";
  return cat === "emotion" || cat === "style" ? cat : "";
}

const END = /[.!?]["'”’)\]]*(?=\s|$)|[۔؟؛]/g;

/** index where the sentence containing `pos` starts (after the previous terminator / newline, skipping spaces) */
export function sentenceStart(text: string, pos: number) {
  let start = 0;
  END.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = END.exec(text))) {
    const e = m.index + m[0].length;
    if (e > pos) break;
    if (e <= pos) start = e;
  }
  const nl = text.lastIndexOf("\n", Math.max(0, pos - 1));
  if (nl + 1 > start && nl < pos) start = nl + 1;
  while (start < text.length && /\s/.test(text[start]) && text[start] !== "\n") start++;
  return start;
}

/** insert a tag at the start of the sentence under `pos`, after the sentence's existing tags; a tag of the same slot
 *  there is replaced. sfx tags get an onomatopoeia placeholder. Returns [text, caret]. */
export function insertTag(text: string, pos: number, cat: string, val: string, sound?: string): [string, number] {
  const tok = `<|${cat}:${val}|>`;
  if (cat === "sfx") {
    const ins = tok + (sound ?? "") + " ";
    const at = sentenceStart(text, pos);
    return [text.slice(0, at) + ins + text.slice(at), at + ins.length];
  }
  let at = sentenceStart(text, pos);
  const slot = slotOf(cat, val);
  // walk the existing leading tags of this sentence
  const lead = /^\s*<\|\s*([A-Za-z_]+)\s*:\s*([A-Za-z_]+)\s*\|>/;
  let cursor = at;
  for (;;) {
    const m = lead.exec(text.slice(cursor));
    if (!m || m[1] === "sfx") break;
    const s = slotOf(m[1].toLowerCase(), m[2].toLowerCase());
    if (slot && s === slot) {  // replace the same-slot tag
      const old = m[0].trim();
      const out = text.slice(0, cursor) + text.slice(cursor).replace(lead, (x) => x.replace(old, tok));
      return [out, pos > cursor ? pos + tok.length - old.length : pos];
    }
    if (m[1] === cat && m[2] === val) return [text, pos]; // already there
    cursor += m[0].length;
  }
  at = cursor;
  return [text.slice(0, at) + tok + text.slice(at), pos >= at ? pos + tok.length : pos];
}

export function stripTags(text: string) {
  return text.replace(ANY_TAG_RE, "").replace(/[ \t]{2,}/g, " ").trim();
}

export function tagCount(text: string) {
  return (text.match(ANY_TAG_RE) || []).length;
}
