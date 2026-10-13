import json,sys,urllib.request,concurrent.futures as cf
def size_of(url):
    req=urllib.request.Request(url,method='HEAD')
    for _ in range(3):
        try:
            with urllib.request.urlopen(req,timeout=30) as r: return int(r.headers.get('Content-Length',0))
        except Exception as e: err=e
    return -1
def main(path):
    r=json.load(open(path))
    items=[(i['metadata']['name'],i['metadata']['version'],i['download_info']['url']) for i in r['install']]
    with cf.ThreadPoolExecutor(16) as ex:
        sizes=list(ex.map(lambda t:size_of(t[2]),items))
    rows=sorted(zip(sizes,items),reverse=True)
    tot=sum(s for s in sizes if s>0)
    print(f"{path}: {len(items)} pkgs, total download {tot/1e9:.2f} GB; failed HEAD: {sum(1 for s in sizes if s<0)}")
    for s,(n,v,u) in rows[:25]:
        print(f"  {s/1e6:9.1f} MB  {n}=={v}  {u.split('/')[-1]}")
    return rows
if __name__=='__main__':
    for p in sys.argv[1:]: main(p); print()
