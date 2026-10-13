#!/bin/bash
# usage: q.sh name "query terms"
cd /tmp/claude-1013/-home-vector/60c91189-44d6-4cdb-b0f5-2bf4adb23fb3/scratchpad/research/omni-issues
name=$1; shift
for attempt in 1 2 3; do
  curl -s -G "https://api.github.com/search/issues" --data-urlencode "q=repo:vllm-project/vllm-omni $*" --data-urlencode per_page=100 -o s/$name.json
  if python3 -c "import json;d=json.load(open('s/$name.json'));assert 'items' in d" 2>/dev/null; then break; fi
  sleep 20
done
python3 - "$name" <<'PY'
import json,sys
name=sys.argv[1]
d=json.load(open(f's/{name}.json'))
if 'items' not in d: print('ERR',d.get('message')); sys.exit()
print(f'### {name} total',d['total_count'])
for i in d['items'][:60]:
    kind='PR' if 'pull_request' in i else 'IS'
    print(i['number'],kind,i['state'],i['created_at'][:10],i['title'][:110])
PY
sleep 7
