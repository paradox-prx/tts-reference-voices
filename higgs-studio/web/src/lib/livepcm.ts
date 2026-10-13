// Play a raw s16le 24 kHz mono PCM stream while it downloads (Web Audio scheduling).

export class LivePcmPlayer {
  ctx: AudioContext;
  private next = 0;
  private carry: Uint8Array | null = null;
  private sources: AudioBufferSourceNode[] = [];
  private abort = new AbortController();
  received = 0; // seconds of audio received
  started = false;
  onFirstAudio?: () => void;
  onEnd?: () => void;

  constructor(private sampleRate = 24000) {
    this.ctx = new AudioContext({ sampleRate });
  }

  async play(url: string) {
    const r = await fetch(url, { signal: this.abort.signal });
    if (!r.ok || !r.body) throw new Error(`stream failed: HTTP ${r.status}`);
    const reader = r.body.getReader();
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      if (value && value.length) this.push(value);
    }
    const left = Math.max(0, this.next - this.ctx.currentTime);
    setTimeout(() => this.onEnd?.(), left * 1000 + 50);
  }

  private push(bytes: Uint8Array) {
    let b = bytes;
    if (this.carry) {
      const m = new Uint8Array(this.carry.length + b.length);
      m.set(this.carry); m.set(b, this.carry.length); b = m; this.carry = null;
    }
    if (b.length % 2) { this.carry = b.slice(b.length - 1); b = b.slice(0, b.length - 1); }
    const n = b.length / 2;
    if (!n) return;
    const dv = new DataView(b.buffer, b.byteOffset, b.length);
    const buf = this.ctx.createBuffer(1, n, this.sampleRate);
    const ch = buf.getChannelData(0);
    for (let i = 0; i < n; i++) ch[i] = dv.getInt16(i * 2, true) / 32768;
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.ctx.destination);
    const now = this.ctx.currentTime;
    if (!this.started) { this.started = true; this.next = now + 0.12; this.onFirstAudio?.(); }
    if (this.next < now) this.next = now + 0.03; // underrun: restart a little ahead
    src.start(this.next);
    this.next += buf.duration;
    this.received += buf.duration;
    this.sources.push(src);
  }

  stop() {
    this.abort.abort();
    for (const s of this.sources) { try { s.stop(); } catch { /* not started */ } }
    this.ctx.close().catch(() => undefined);
  }
}
