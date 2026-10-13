import json,urllib.request,sys
repos=sys.argv[1:]
for repo in repos:
    url=f"https://huggingface.co/api/models/{repo}/tree/main?recursive=true"
    try:
        with urllib.request.urlopen(url,timeout=60) as r: tree=json.load(r)
    except Exception as e:
        print(f"## {repo}: ERROR {e}"); continue
    files=[t for t in tree if t['type']=='file']
    tot=sum(f.get('size',0) for f in files)
    try:
        with urllib.request.urlopen(f"https://huggingface.co/api/models/{repo}",timeout=60) as r: info=json.load(r)
        sha=info.get('sha'); gated=info.get('gated'); lm=info.get('lastModified')
    except Exception as e: sha=gated=lm=str(e)
    print(f"## {repo}  sha={sha} gated={gated} lastModified={lm}  files={len(files)} total={tot/1e9:.3f} GB")
    for f in sorted(files,key=lambda f:-f.get('size',0)):
        lfs=' (lfs)' if f.get('lfs') else ''
        print(f"   {f.get('size',0)/1e6:10.2f} MB  {f['path']}{lfs}")
