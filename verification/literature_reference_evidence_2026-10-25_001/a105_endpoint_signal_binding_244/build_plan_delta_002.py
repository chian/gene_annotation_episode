"""Additive exact row-discriminator correction; no production imports/edits."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from gene_annotation_episode.domain import ContractError, validate_schema

OWN=Path(__file__).resolve().parent
PURE=OWN.parent/'a105_endpoint_signal_components_241'
def read(name):return json.loads((OWN/name).read_text())
def save(name,value):(OWN/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
old=read('EXACT_SCHEMAS_001.json')
new=deepcopy(old)
constants=json.loads((PURE/'CELL_CONSTANTS_002.json').read_text())
names=old['return_schema']['items']['properties']['component']['enum']
rules=[]
for name in names:
    variance=name.endswith('_variance')
    base=name.removesuffix('_variance')
    fraction=base in ('retained_fraction','additional_fraction')
    unit=('dimensionless^2' if fraction else 'pixel^2') if variance else (
        'dimensionless' if fraction else 'direction_oriented_pixel')
    rules.append({'if':{'properties':{'component':{'const':name}},'required':['component']},
        'then':{'properties':{'unit':{'const':unit},
            'formula':{'const':constants['FORMULAS'][name]},
            'meaning':{'const':constants['MEANINGS'][name]}}}})
new['return_schema']['items']['allOf']=rules
save('EXACT_SCHEMAS_002.json',new)
save('EXACT_SCHEMA_DELTA_002.json',{'base':'EXACT_SCHEMAS_001.json',
    'changes':[{'op':'add','path':'/return_schema/items/allOf','value':rules}],
    'unchanged':'Every existing node, including base closed row fields, operation/request/assignment schemas and identifiers.'})
# The paired input and scientific outputs are unchanged. Preserve the original
# bytes in the additive002copies, rather than retrospectively relabel001.
for kind in ('INPUT','OUTPUT'):
    (OWN/f'PAIRED_SELECTED_{kind}_002.json').write_bytes((OWN/f'PAIRED_SELECTED_{kind}_001.json').read_bytes())
Draft202012Validator.check_schema(new['return_schema'])
source_rows=read('PAIRED_SELECTED_OUTPUT_002.json')['normal_typed_return']['numbers']
validate_schema(source_rows,new['return_schema'])
mutations=[]
for rule in rules:
    name=rule['if']['properties']['component']['const']
    good=deepcopy(source_rows[0]);good['component']=name
    expected=rule['then']['properties']
    for field,value in expected.items():good[field]=value['const']
    validate_schema([good],new['return_schema'])
    for field,wrong in (('unit','pixel^2' if good['unit']!='pixel^2' else 'dimensionless'),
        ('formula','s*(a-t)' if good['formula']!='s*(a-t)' else '(a-b)/(a-t)'),
        ('meaning',constants['MEANINGS']['total_amplitude'] if name!='total_amplitude'
            else constants['MEANINGS']['retained_fraction'])):
        bad=deepcopy(good);bad[field]=wrong
        try:validate_schema([bad],new['return_schema'])
        except ContractError:mutations.append({'component':name,'field':field,'rejected':True})
        else:raise AssertionError((name,field,'bad discriminator accepted'))
assert deepcopy({k:v for k,v in new['return_schema']['items'].items() if k!='allOf'})==old['return_schema']['items']
hashes={name:hashlib.sha256((OWN/name).read_bytes()).hexdigest() for name in
    ('EXACT_SCHEMAS_001.json','PAIRED_SELECTED_INPUT_001.json','PAIRED_SELECTED_OUTPUT_001.json')}
save('PLAN_SCHEMA_CHECK_002.json',{'status':'additive_plan_only','full_paired_return_valid':True,
    'all10_component_valid_unit_formula_meaning_pairs_pass':True,
    'all30_wrong_component_field_mutations_rejected':mutations,
    'all_inherited_base_closed_fields_exact':True,'original001_hashes':hashes,
    'production_edits':0,'actual_scientific_execution':False})
print('Plan002schema valid; all10 valid pairs pass, all30 wrong unit/formula/meaning mutations rejected;001unchanged.')
