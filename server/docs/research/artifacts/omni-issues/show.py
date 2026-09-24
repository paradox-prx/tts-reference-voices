import json,sys,re
db=json.load(open('db.json'))
n=int(sys.argv[1]); lim=int(sys.argv[2]) if len(sys.argv)>2 else 2500
i=db.get(str(n))
if not i: print('NOT IN DB',n); sys.exit()
kind='PR' if 'pull_request' in i else 'IS'
merged=i.get('pull_request',{}).get('merged_at')
print(f"#{n} {kind} {i['state']} created={i['created_at'][:10]} closed={(i.get('closed_at') or '')[:10]} merged={merged} comments={i['comments']} labels={[l['name'] for l in i['labels']]}")
print('TITLE:',i['title'])
b=i.get('body') or ''
b=re.sub(r'<!--.*?-->','',b,flags=re.S)
b=re.sub(r'\n\s*\n+','\n',b)
print(b[:lim])
print('-'*80)
