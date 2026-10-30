"""Lossless review of proposed integration schemas, reusing reviewed resources."""
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from jsonschema import Draft202012Validator
from gene_annotation_episode.literature_kinetic_inputs import kinetic_arguments_schema

PLAN = HERE.parent / 'a105_summary_precision_binding_251'
PURE = HERE.parent / 'a105_summary_precision_components_248'
def read(path): return json.loads(path.read_text())
def canon(value): return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
known = {'reviewed_selection002': read(PURE/'SELECTION_SCHEMA_002.json'),
         'reviewed_sheet004_defs': read(PURE/'SHEET_SCHEMA_004.json')['$defs'],
         'unchanged_legacy_kinetic_arguments': kinetic_arguments_schema()}
sheet = read(PURE/'SHEET_SCHEMA_004.json')
for population in ('source_cells', 'scenario_cells'):
    branch = sheet['properties'][population]
    if 'properties' not in branch:
        branch = next(value for value in branch['anyOf'] if 'properties' in value)
    for name, value in branch['properties'].items():
        known[population + '_' + name] = value
for label, filename in [('SELECTION','SELECTION_SCHEMA_002.json'), ('EXTRACTION','EXTRACTION_SCHEMA_004.json'),
                        ('CALCULATION_INPUTS','CALCULATION_INPUTS_SCHEMA_004.json'), ('SHEET','SHEET_SCHEMA_004.json')]:
    copied = PLAN / ('ORIGINAL_' + label + '_SCHEMA_001.json')
    assert read(copied) == read(PURE / filename), copied
index = {canon(value): name for name, value in known.items()}
names = ['SELECTED_ARGUMENTS_SCHEMA_001.json', 'REQUEST_ROSTER_SCHEMA_001.json',
         'RETURN_ROWS_SCHEMA_001.json', 'OPERATION_UNION_SCHEMA_001.json']
schemas = {name: read(PLAN/name) for name in names}
assert schemas[names[0]]['properties']['selection'] == known['reviewed_selection002']
assert schemas[names[2]]['$defs'] == known['reviewed_sheet004_defs']
assert schemas[names[3]]['anyOf'] == [known['unchanged_legacy_kinetic_arguments'], schemas[names[0]]]
pool, seen = {}, {}
def encode(value):
    if not isinstance(value,(dict,list)): return value
    key = canon(value)
    if key in index: return {'reviewed': index[key]}
    if key not in seen:
        name = 'N' + str(len(seen)+1)
        seen[key] = name
        pool[name] = (['object', [[k,encode(v)] for k,v in value.items()]] if isinstance(value,dict)
                      else ['array', [encode(v) for v in value]])
    return {'node': seen[key]}
def decode(value):
    if not isinstance(value,dict): return value
    if 'reviewed' in value: return known[value['reviewed']]
    kind, items = pool[value['node']]
    return {k:decode(v) for k,v in items} if kind=='object' else [decode(v) for v in items]
roots = {name: encode(value) for name,value in schemas.items()}
assert {name:decode(value) for name,value in roots.items()} == schemas
for value in schemas.values(): Draft202012Validator.check_schema(value)
lines = ['ROOTS ' + canon(roots)]
for name in sorted(pool, key=lambda value:int(value[1:])): lines.append(name+' '+canon(pool[name]))
pages=[]; current=[]; size=0
for line in lines:
    if current and size+len(line)>10500:
        pages.append('\n'.join(current)+'\n');current=[];size=0
    current.append(line);size+=len(line)+1
if current:pages.append('\n'.join(current)+'\n')
for number, content in enumerate(pages,1):
    with (HERE/f'NEW_SCHEMA_NODES_PAGE_{number:02d}_001.txt').open('x') as output:output.write(content)
manifest = {'lossless_roundtrip':True, 'human_read_complete':False, 'new_unique_nodes':len(pool),
            'pages':[{'name':f'NEW_SCHEMA_NODES_PAGE_{i:02d}_001.txt','bytes':len(page.encode())} for i,page in enumerate(pages,1)],
            'reviewed_resources':{name:sha256(canon(value).encode()).hexdigest() for name,value in known.items()},
            'proposed_schema_hashes':{name:sha256((PLAN/name).read_bytes()).hexdigest() for name in names}}
with (HERE/'SCHEMA_REVIEW_MANIFEST_001.json').open('x') as output:json.dump(manifest,output,indent=2);output.write('\n')
print(json.dumps({'lossless_roundtrip':True,'new_unique_nodes':len(pool),'pages':len(pages),'page_bytes':[len(p.encode()) for p in pages]}))
