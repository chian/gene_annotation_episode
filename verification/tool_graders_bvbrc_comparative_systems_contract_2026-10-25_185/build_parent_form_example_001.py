"""Review-only specialization into the existing closed communication schema."""
import copy, json
from pathlib import Path
from gene_annotation_episode.communication import validate_closed_schema
from jsonschema import Draft202012Validator

BASE=Path(__file__).resolve().parent
s=json.loads((BASE/'HANDOFF_SCHEMAS_001.json').read_text())
examples=json.loads((BASE/'FILLED_EXAMPLES_001.json').read_text())
def obj(**p):return dict(type='object',properties=p,required=list(p),additionalProperties=False)
def expand(node,field=''):
    if '$ref' in node:return expand(s['$defs'][node['$ref'].split('/')[-1]],field)
    if 'anyOf' in node:
        nonnull=[n for n in node['anyOf'] if n.get('type')!='null']
        assert len(nonnull)==1 and len(node['anyOf'])==2
        r=expand(nonnull[0],field);r['type']=[r['type'],'null'];return r
    r={k:copy.deepcopy(v) for k,v in node.items() if k not in {'allOf','minLength','pattern'}}
    if 'type' not in r:
        assert r.get('enum')==[1,100];r['type']='integer'
    if r['type']=='object':r['properties']={k:expand(v,k) for k,v in r['properties'].items()}
    if r['type']=='array':r['items']=expand(r['items'],field)
    if r['type']=='string' and 'enum' not in r and 'const' not in r:
        ns='population' if field.endswith('population_id') or field=='population_id' else {'owner_id':'owner','pointer':'pointer','analysis_id':'analysis'}.get(field,'identifier')
        r.update(format='identifier',**{'x-reference-namespace':'bvbrc_comparative_systems_'+ns})
    return r
ratio=expand(s['$defs']['RatioComponentV1'])
status={'type':'string','enum':['satisfied','partial','invalid','unavailable']}
value=obj(field_id={'type':'string','enum':['retained_ec_percent']},
    values={'type':'array','items':ratio,'minItems':1,'maxItems':1},status=status)
fact=obj(source_ref={'type':'string','format':'identifier','x-reference-namespace':'execution_result'},
    field={'type':'string','enum':['retained_ec_percent']},value=value)
schema=obj(comparative_ratios={'type':'array','items':fact,'minItems':1,'maxItems':1,
    'x-source':'bvbrc_comparative_systems_ratios'})
validate_closed_schema(schema)
original=next(e['value'] for e in examples['examples'] if e['example_id']=='parent_return_fact')
form={'comparative_ratios':[original]}
Draft202012Validator(schema).validate(form)
(BASE/'PARENT_RATIO_FORM_EXAMPLE_001.json').write_text(json.dumps(schema,indent=2)+'\n')
(BASE/'PARENT_RATIO_FACT_EXAMPLE_001.json').write_text(json.dumps(form,indent=2)+'\n')
print('Existing closed communication schema validation passed; synthetic shape only, no admission.')
