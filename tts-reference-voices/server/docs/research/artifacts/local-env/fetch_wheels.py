#!/usr/bin/env python3
"""Fill a local wheelhouse from a `pip install --dry-run --report` JSON using many parallel
HTTP range requests per file (this box's uplink throttles each TCP connection to ~15-25 KB/s,
so pip's single-connection download is ~20x slower than the aggregate link).

- Reuses bodies already in ~/.cache/pip/http-v2 (pip's own cache) when present.
- Verifies sha256 from the report before accepting a file.
- Resumable: finished parts are kept in <out>/.parts/.

Usage:
  python3 fetch_wheels.py report.json /home/vector/qwen3-tts-server/wheelhouse --conns 24
  pip install --no-index --find-links /home/vector/qwen3-tts-server/wheelhouse vllm==0.28.0 vllm-omni==0.28.0
  python3 fetch_wheels.py hf:Qwen/Qwen3-TTS-12Hz-1.7B-Base /home/vector/qwen3-tts-server/models/Qwen3-TTS-12Hz-1.7B-Base \
      --revision fd4b254389122332181a7c3db7f27e918eec64e3
  (then pass the local dir as the model path; LFS files are sha256-verified against the Hub's LFS oid)
Stdlib only.
"""
import argparse, concurrent.futures as cf, hashlib, json, os, shutil, sys, time, urllib.request

PIP_CACHE = os.path.expanduser("~/.cache/pip/http-v2")


def pip_cache_body(url):
    h = hashlib.sha224(url.encode()).hexdigest()
    p = os.path.join(PIP_CACHE, *list(h[:5]), h) + ".body"
    return p if os.path.exists(p) else None


def sha256_of(path):
    d = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            d.update(b)
    return d.hexdigest()


def head_size(url):
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60) as r:
        return int(r.headers["Content-Length"])


def fetch_range(url, start, end, part, retries=30):
    want = end - start + 1
    for attempt in range(retries):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if have >= want:
            return want
        req = urllib.request.Request(url, headers={"Range": f"bytes={start + have}-{end}"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r, open(part, "ab") as f:
                shutil.copyfileobj(r, f, 1 << 16)
        except Exception:
            time.sleep(min(2 * (attempt + 1), 20))
    raise RuntimeError(f"range {start}-{end} failed for {url}")


def fetch(url, sha, dest, pool, chunk, conns):
    if os.path.exists(dest) and (not sha or sha256_of(dest) == sha):
        return "present"
    body = pip_cache_body(url)
    if body and (not sha or sha256_of(body) == sha):
        shutil.copy(body, dest)
        return "pip-cache"
    size = head_size(url)
    chunk = min(chunk, max(262144, size // conns + 1))  # small files still use all connections
    partdir = os.path.join(os.path.dirname(dest), ".parts", os.path.basename(dest))
    os.makedirs(partdir, exist_ok=True)
    ranges = [(s, min(s + chunk, size) - 1) for s in range(0, size, chunk)]
    futs = [pool.submit(fetch_range, url, s, e, os.path.join(partdir, f"{i:06d}")) for i, (s, e) in enumerate(ranges)]
    for f in futs:
        f.result()
    tmp = dest + ".tmp"
    with open(tmp, "wb") as out:
        for i in range(len(ranges)):
            with open(os.path.join(partdir, f"{i:06d}"), "rb") as p:
                shutil.copyfileobj(p, out, 1 << 20)
    if sha and sha256_of(tmp) != sha:
        os.remove(tmp)
        shutil.rmtree(partdir, ignore_errors=True)
        raise RuntimeError(f"sha256 mismatch: {dest}")
    os.replace(tmp, dest)
    shutil.rmtree(partdir, ignore_errors=True)
    return f"downloaded {size / 1e6:.1f} MB"


def hf_items(repo, revision, patterns):
    import fnmatch
    url = f"https://huggingface.co/api/models/{repo}/tree/{revision}?recursive=true"
    tree = json.load(urllib.request.urlopen(url, timeout=120))
    for t in tree:
        if t["type"] != "file" or (patterns and not any(fnmatch.fnmatch(t["path"], p) for p in patterns)):
            continue
        sha = (t.get("lfs") or {}).get("oid")  # sha256 for LFS files; small git files are not verified
        yield t["path"], f"https://huggingface.co/{repo}/resolve/{revision}/{t['path']}", sha


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", help="pip --report JSON, or hf:<org>/<repo> to mirror a HF model repo")
    ap.add_argument("out", help="wheelhouse dir, or local model dir for hf:")
    ap.add_argument("--conns", type=int, default=24)
    ap.add_argument("--chunk-mb", type=float, default=4)
    ap.add_argument("--only", nargs="*", help="pip: only these distribution names; hf: glob patterns")
    ap.add_argument("--revision", default="main", help="hf: branch or commit sha")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.report.startswith("hf:"):
        jobs = [(path, url, sha, path) for path, url, sha in hf_items(a.report[3:], a.revision, a.only)]
    else:
        items = json.load(open(a.report))["install"]
        if a.only:
            keep = {n.lower().replace("_", "-") for n in a.only}
            items = [i for i in items if i["metadata"]["name"].lower().replace("_", "-") in keep]
        jobs = [(f"{i['metadata']['name']}=={i['metadata']['version']}", i["download_info"]["url"],
                 (i["download_info"].get("archive_info", {}).get("hashes") or {}).get("sha256"),
                 i["download_info"]["url"].split("/")[-1]) for i in items]
    chunk = int(a.chunk_mb * 1e6)
    t0 = time.time()
    failed = 0
    with cf.ThreadPoolExecutor(a.conns) as pool:
        for label, url, sha, rel in jobs:
            dest = os.path.join(a.out, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                res = fetch(url, sha, dest, pool, chunk, a.conns)
            except Exception as e:
                res, failed = f"FAILED {e}", failed + 1
            print(f"[{time.time() - t0:7.0f}s] {label}: {res}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
