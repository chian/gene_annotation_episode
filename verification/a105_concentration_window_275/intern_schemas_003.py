"""Lossless exact JSON node interning for review; no schema/science changes."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
original_bytes=(HERE/'SCHEMAS_003.json').read_bytes()
original=json.loads(original_bytes)
nodes=[];intern={}


def encode(v):
    if isinstance(v,dict):
        kind='object';payload=tuple((k,encode(child)) for k,child in v.items())
    elif isinstance(v,list):
        kind='array';payload=tuple(encode(child) for child in v)
    else:
        kind=type(v).__name__;payload=v
    key=(kind,payload)
    if key not in intern:
        i=len(nodes);intern[key]=i
        nodes.append(dict(id=i,kind=kind,**({'members':[list(x) for x in payload]} if kind=='object' else
            {'items':list(payload)} if kind=='array' else {'value':payload})))
    return intern[key]


roots={name:encode(value) for name,value in original.items()}


def decode(i):
    n=nodes[i]
    return {k:decode(v) for k,v in n['members']} if n['kind']=='object' else (
        [decode(v) for v in n['items']] if n['kind']=='array' else n['value'])


restored={name:decode(i) for name,i in roots.items()}
assert restored==original
restored_bytes=(json.dumps(restored,indent=2,ensure_ascii=False)+'\n').encode()
assert restored_bytes==original_bytes
pages=[];current=[]
def page_bytes(rows):
    return ('[\n'+',\n'.join(json.dumps(x,separators=(',',':'),ensure_ascii=False) for x in rows)+'\n]\n').encode()
for row in nodes:
    if len(page_bytes([*current,row]))>12000:
        assert current;pages.append(current);current=[]
    current.append(row)
if current:pages.append(current)
paths=[]
for i,rows in enumerate(pages,1):
    path=HERE/f'SCHEMA_NODES_003_PAGE_{i:03d}.json'
    data=page_bytes(rows);assert len(data)<=12000
    path.write_bytes(data)
    paths.append(dict(path=str(path.relative_to(HERE)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
        first_node=rows[0]['id'],last_node=rows[-1]['id']))
root_record=dict(encoding='object.members preserves key order; array.items preserves order; primitive.value preserves exact JSON scalar type; child integers address exact nodes by id',
    roots=roots,node_count=len(nodes),pages=paths,
    original_schema_file='SCHEMAS_003.json',original_schema_sha256=hashlib.sha256(original_bytes).hexdigest(),
    roundtrip_tree_equal=True,roundtrip_original_file_bytes_equal=True)
(HERE/'SCHEMA_ROOTS_003.json').write_text(json.dumps(root_record,indent=2)+'\n')
print(json.dumps(dict(nodes=len(nodes),pages=len(pages),max_page_bytes=max(p['bytes'] for p in paths),
    roundtrip_tree_equal=True,roundtrip_original_file_bytes_equal=True)))
