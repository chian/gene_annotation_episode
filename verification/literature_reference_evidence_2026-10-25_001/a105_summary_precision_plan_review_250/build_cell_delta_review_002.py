"""Lossless003 additions relative to the four fully read002 schema pages."""
from copy import deepcopy
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
OWN=HERE.parent/'a105_summary_precision_components_248'
pool={}
for path in sorted(HERE.glob('SCHEMA_LOSSLESS_PAGE_*_001.txt')):
    for line in path.read_text().splitlines():
        label,value=line.split(' ',1)
        if label=='ROOTS':continue
        pool[label]=json.loads(value)

def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def decode(v):
    if not isinstance(v,dict):return v
    kind,payload=pool[v['node']]
    return {k:decode(x) for k,x in payload} if kind=='object' else [decode(x) for x in payload]
known={canonical(decode({'node':k})):k for k in pool}
added={}
def encode(v):
    if not isinstance(v,(dict,list)):return v
    key=canonical(v)
    if key not in known:
        label='M'+str(len(added)+1);known[key]=label;added[label]=None
        added[label]=['object',[[k,encode(x)] for k,x in v.items()]] if isinstance(v,dict) else ['array',[encode(x) for x in v]]
    return {'node':known[key]}
old=json.loads((OWN/'SHEET_SCHEMA_002.json').read_text())
new=json.loads((OWN/'SHEET_SCHEMA_003.json').read_text())
delta=json.loads((OWN/'CELL_SCHEMA_DELTA_003.json').read_text())
applied=deepcopy(old)
for operation in delta['rfc6902_patch']:
    parts=[x.replace('~1','/').replace('~0','~') for x in operation['path'].split('/')[1:]]
    parent=applied
    for part in parts[:-1]:parent=parent[int(part)] if isinstance(parent,list) else parent[part]
    key=int(parts[-1]) if isinstance(parent,list) else parts[-1]
    assert operation['op'] in ('add','replace')
    parent[key]=deepcopy(operation['value'])
assert canonical(applied)==canonical(new)
root=encode(new);pool.update(added)
assert canonical(decode(root))==canonical(new)
lines=['ROOT003 '+canonical(root),'DOMAINS '+canonical(delta['per_cell_domains'])]
lines.extend(k+' '+canonical(v) for k,v in added.items())
pages=[];current=[];size=0
for line in lines:
    if current and size+len(line)>11000:
        pages.append('\n'.join(current)+'\n');current=[];size=0
    current.append(line);size+=len(line)+1
if current:pages.append('\n'.join(current)+'\n')
for i,page in enumerate(pages,1):
    with (HERE/f'CELL_DELTA_LOSSLESS_PAGE_{i:02d}_002.txt').open('x') as f:f.write(page)
report={'patch_operations':len(delta['rfc6902_patch']),'exact_patch_roundtrip':True,
    'lossless_new_schema_roundtrip':True,'new_unique_nodes':len(added),
    'old_nodes_reused_from_fully_read002_pages':True,
    'pages':[{'name':f'CELL_DELTA_LOSSLESS_PAGE_{i:02d}_002.txt','bytes':len(p.encode())} for i,p in enumerate(pages,1)],
    'human_read':'pending'}
with (HERE/'CELL_DELTA_REVIEW_MANIFEST_002.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:report[k] for k in ('patch_operations','exact_patch_roundtrip','new_unique_nodes','pages')}))
