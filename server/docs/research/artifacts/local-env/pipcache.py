import json,hashlib,os,sys
base=os.path.expanduser('~/.cache/pip/http-v2')
def path_for(url):
    h=hashlib.sha224(url.encode()).hexdigest()
    return os.path.join(base,*list(h[:5]),h)
for rep in sys.argv[1:]:
    r=json.load(open(rep))
    hit=miss=0; hb=mb=0
    rows=[]
    for i in r['install']:
        u=i['download_info']['url']; n=i['metadata']['name']; v=i['metadata']['version']
        p=path_for(u)
        ok=os.path.exists(p+'.body') or os.path.exists(p)
        sz=os.path.getsize(p+'.body') if os.path.exists(p+'.body') else 0
        rows.append((ok,sz,n,v))
        if ok: hit+=1; hb+=sz
        else: miss+=1
    print(f"{rep}: cached {hit} (={hb/1e9:.2f} GB of bodies), missing {miss}")
    for ok,sz,n,v in sorted(rows,key=lambda t:-t[1])[:15]:
        if ok: print(f"   cached {sz/1e6:8.1f} MB {n}=={v}")
