import { forwardRef, useEffect, useImperativeHandle, useLayoutEffect, useRef } from "react";
import { insertTag, isValid, type Vocab } from "../lib/tags";

/* A contentEditable text editor where Higgs control tags (<|cat:val|>) render as coloured, removable chips. The value
 * is the plain string with tags; the DOM is only re-rendered when the value changes from outside (tag insert, preset,
 * example), so typing never fights the browser. */

const TOKEN = /<\|\s*([A-Za-z_]+)\s*:\s*([A-Za-z_]+)\s*\|>|<\|[^|<>]*\|>/g;
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const LABEL: Record<string, string> = { emotion: "", prosody: "", style: "", sfx: "♪ " };

function renderHTML(text: string, vocab: Vocab) {
  let out = "", last = 0;
  TOKEN.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = TOKEN.exec(text))) {
    out += esc(text.slice(last, m.index));
    const cat = (m[1] || "").toLowerCase(), val = (m[2] || "").toLowerCase();
    const ok = cat && isValid(vocab, cat, val);
    const label = ok ? `${LABEL[cat] ?? ""}${val.replace(/_/g, " ")}` : "invalid tag";
    out += `<span class="chip ${ok ? cat : "invalid"}" contenteditable="false" data-tag="${esc(m[0])}" ` +
      `title="${esc(m[0])}">${esc(label)}<button class="x" tabindex="-1" aria-label="Remove ${esc(label)} tag">×</button></span>`;
    last = m.index + m[0].length;
  }
  out += esc(text.slice(last));
  return out;
}

function serialize(root: Node): string {
  let s = "";
  root.childNodes.forEach((n, i) => {
    if (n.nodeType === Node.TEXT_NODE) s += n.textContent ?? "";
    else if (n instanceof HTMLElement) {
      if (n.dataset.tag) s += n.dataset.tag;
      else if (n.tagName === "BR") s += "\n";
      else if (n.tagName === "DIV" || n.tagName === "P") s += (i > 0 ? "\n" : "") + serialize(n);
      else s += serialize(n);
    }
  });
  return s;
}

function nodeLen(n: Node): number {
  if (n.nodeType === Node.TEXT_NODE) return (n.textContent ?? "").length;
  if (n instanceof HTMLElement && n.dataset.tag) return n.dataset.tag.length;
  if (n instanceof HTMLElement && n.tagName === "BR") return 1;
  let s = 0;
  n.childNodes.forEach((c) => (s += nodeLen(c)));
  return s;
}

function getCaret(root: HTMLElement): number | null {
  const sel = window.getSelection();
  if (!sel || !sel.rangeCount) return null;
  const r = sel.getRangeAt(0);
  if (!root.contains(r.startContainer)) return null;
  let pos = 0, found = false;
  const walk = (n: Node) => {
    if (found) return;
    if (n === r.startContainer) {
      if (n.nodeType === Node.TEXT_NODE) pos += r.startOffset;
      else for (let i = 0; i < r.startOffset; i++) pos += nodeLen(n.childNodes[i]);
      found = true;
      return;
    }
    if (n instanceof HTMLElement && n.dataset.tag) {
      if (n.contains(r.startContainer)) { pos += nodeLen(n); found = true; return; }
      pos += nodeLen(n);
      return;
    }
    if (n.nodeType === Node.TEXT_NODE) { pos += nodeLen(n); return; }
    n.childNodes.forEach(walk);
  };
  root.childNodes.forEach(walk);
  return found ? pos : null;
}

function setCaret(root: HTMLElement, pos: number) {
  const sel = window.getSelection();
  if (!sel) return;
  let acc = 0;
  const range = document.createRange();
  for (const n of Array.from(root.childNodes)) {
    const len = nodeLen(n);
    if (n.nodeType === Node.TEXT_NODE && pos <= acc + len) {
      range.setStart(n, pos - acc);
      range.collapse(true);
      sel.removeAllRanges(); sel.addRange(range);
      return;
    }
    if (pos <= acc + len && n instanceof HTMLElement && n.dataset.tag && pos > acc) {
      range.setStartAfter(n); range.collapse(true);
      sel.removeAllRanges(); sel.addRange(range);
      return;
    }
    acc += len;
  }
  range.selectNodeContents(root); range.collapse(false);
  sel.removeAllRanges(); sel.addRange(range);
}

export type TagEditorHandle = { insertTag: (cat: string, val: string, sound?: string) => void; focus: () => void };

type Props = { value: string; onChange: (v: string) => void; vocab: Vocab; dir: "ltr" | "rtl"; font: string;
  placeholder: string; onSubmit?: () => void; label: string };

const TagEditor = forwardRef<TagEditorHandle, Props>(function TagEditor(
  { value, onChange, vocab, dir, font, placeholder, onSubmit, label }, ref) {
  const el = useRef<HTMLDivElement>(null);
  const shown = useRef<string | null>(null);   // value the DOM currently shows
  const pendingCaret = useRef<number | null>(null);
  const lastCaret = useRef<number>(value.length);

  useLayoutEffect(() => {
    if (!el.current || shown.current === value) return;
    el.current.innerHTML = renderHTML(value, vocab);
    shown.current = value;
    if (pendingCaret.current != null) { setCaret(el.current, pendingCaret.current); pendingCaret.current = null; }
  }, [value, vocab]);

  useEffect(() => {
    const onSel = () => { if (el.current) { const c = getCaret(el.current); if (c != null) lastCaret.current = c; } };
    document.addEventListener("selectionchange", onSel);
    return () => document.removeEventListener("selectionchange", onSel);
  }, []);

  useImperativeHandle(ref, () => ({
    insertTag(cat, val, sound) {
      const cur = shown.current ?? value;
      const pos = Math.min(lastCaret.current, cur.length);
      const [next, caret] = insertTag(cur, pos, cat, val, sound);
      pendingCaret.current = caret;
      lastCaret.current = caret;
      el.current?.focus();
      onChange(next);
    },
    focus() { el.current?.focus(); },
  }));

  const sync = () => {
    if (!el.current) return;
    const v = serialize(el.current);
    shown.current = v;
    // a chip removed by the browser (backspace) or a pasted tag token: re-render so chips stay consistent
    const chips = el.current.querySelectorAll("[data-tag]").length;
    const tokens = (v.match(TOKEN) || []).length;
    if (chips !== tokens) {
      const c = getCaret(el.current);
      shown.current = null;
      pendingCaret.current = c;
    }
    onChange(v);
  };

  return (
    <div className="editor-wrap">
      <div
        ref={el}
        className={`editor ${font}`}
        contentEditable
        suppressContentEditableWarning
        role="textbox"
        aria-multiline="true"
        aria-label={label}
        dir={dir}
        lang={dir === "rtl" ? "ur" : "en"}
        data-placeholder={placeholder}
        data-empty={value.length === 0 ? "true" : "false"}
        spellCheck={false}
        onInput={sync}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); onSubmit?.(); return; }
          if (e.key === "Enter") { e.preventDefault(); document.execCommand("insertText", false, "\n"); }
        }}
        onPaste={(e) => {
          e.preventDefault();
          document.execCommand("insertText", false, e.clipboardData.getData("text/plain"));
        }}
        onClick={(e) => {
          const t = e.target as HTMLElement;
          if (t.classList.contains("x")) {
            const chip = t.closest("[data-tag]") as HTMLElement;
            if (!chip || !el.current) return;
            // offset of the chip in the serialized value
            let acc = 0;
            for (const n of Array.from(el.current.childNodes)) {
              if (n === chip) break;
              acc += nodeLen(n);
            }
            const tok = chip.dataset.tag!;
            let after = acc + tok.length;
            const cur = shown.current ?? value;
            // an sfx chip takes its sound word with it
            if (/^<\|\s*sfx:/.test(tok)) { const m = /^\S*\s?/.exec(cur.slice(after)); if (m) after += m[0].length; }
            pendingCaret.current = acc;
            shown.current = null;
            onChange(cur.slice(0, acc) + cur.slice(after));
          }
        }}
      />
    </div>
  );
});

export default TagEditor;
