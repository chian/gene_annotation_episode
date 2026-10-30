"""Lossless schema review pages, not summaries or replacement authority."""
from pathlib import Path
import hashlib
import json
from jsonschema import Draft202012Validator

HERE=Path(__file__).resolve().parent
OWN=HERE.parent/'a105_summary_precision_components_248'
names=('SELECTION','EXTRACTION','CALCULATION_INPUTS','SHEET')
roots={n:json.loads((OWN/(n+'_SCHEMA_002.json')).read_text()) for n in names}
for schema in roots.values():Draft202012Validator.check_schema(schema)
pool={};seen={}

def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def encode(v):
    if not isinstance(v,(dict,list)):return v
    key=canonical(v)
    if key not in seen:
        name='N'+str(len(seen)+1);seen[key]=name
        pool[name]=['object',[[k,encode(x)] for k,x in v.items()]] if isinstance(v,dict) else ['array',[encode(x) for x in v]]
    return {'node':seen[key]}
encoded={k:encode(v) for k,v in roots.items()}
def decode(ref):
    if not isinstance(ref,dict):return ref
    kind,value=pool[ref['node']]
    return {k:decode(v) for k,v in value} if kind=='object' else [decode(v) for v in value]
assert canonical({k:decode(v) for k,v in encoded.items()})==canonical(roots)
lines=['ROOTS '+canonical(encoded)]
for n in sorted(pool,key=lambda n:int(n[1:])):lines.append(n+' '+canonical(pool[n]))
pages=[];current=[];size=0
for line in lines:
    if current and size+len(line)>11000:
        pages.append('\n'.join(current)+'\n');current=[];size=0
    current.append(line);size+=len(line)+1
if current:pages.append('\n'.join(current)+'\n')
for i,content in enumerate(pages,1):
    with (HERE/f'SCHEMA_LOSSLESS_PAGE_{i:02d}_001.txt').open('x') as f:f.write(content)
manifest={'status':'lossless_roundtrip_and_schema_validation_passed; human_read_pending',
    'node_count':len(pool),'source_files':[{ 'name':n+'_SCHEMA_002.json',
        'sha256':hashlib.sha256((OWN/(n+'_SCHEMA_002.json')).read_bytes()).hexdigest()} for n in names],
    'pages':[{'name':f'SCHEMA_LOSSLESS_PAGE_{i:02d}_001.txt','bytes':len(content.encode())}
        for i,content in enumerate(pages,1)]}
with (HERE/'LOSSLESS_REVIEW_MANIFEST_001.json').open('x') as f:json.dump(manifest,f,indent=2);f.write('\n')
print(json.dumps({'nodes':len(pool),'pages':len(pages),'page_bytes':[len(x.encode()) for x in pages],'roundtrip':True}))
