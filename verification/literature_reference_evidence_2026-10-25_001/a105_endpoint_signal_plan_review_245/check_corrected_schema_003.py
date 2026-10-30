"""Independent component-discriminator checks of additive244 schema002."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from gene_annotation_episode.domain import ContractError,validate_schema
from jsonschema import Draft202012Validator
HERE=Path(__file__).resolve().parent
OWN=HERE.parent/'a105_endpoint_signal_binding_244'
PURE=HERE.parent/'a105_endpoint_signal_components_241'
old=json.loads((OWN/'EXACT_SCHEMAS_001.json').read_text())
new=json.loads((OWN/'EXACT_SCHEMAS_002.json').read_text())
base=deepcopy(new)
rules=base['return_schema']['items'].pop('allOf')
assert base==old,'Unexpected change beyond the reviewed discriminator'
constants=json.loads((PURE/'CELL_CONSTANTS_002.json').read_text())
names=old['return_schema']['items']['properties']['component']['enum']
assert [r['if']['properties']['component']['const'] for r in rules]==names
Draft202012Validator.check_schema(new['return_schema'])
rows=json.loads((OWN/'PAIRED_SELECTED_OUTPUT_002.json').read_text())['normal_typed_return']['numbers']
validate_schema(rows,new['return_schema'])
assert (OWN/'PAIRED_SELECTED_INPUT_001.json').read_bytes()==(OWN/'PAIRED_SELECTED_INPUT_002.json').read_bytes()
assert (OWN/'PAIRED_SELECTED_OUTPUT_001.json').read_bytes()==(OWN/'PAIRED_SELECTED_OUTPUT_002.json').read_bytes()
checked=[]
for name in names:
    # Shape fixtures only. The other exemplar fields are not a new scientific
    # calculation or an assertion of source data for these component names.
    fixture=deepcopy(rows[0]);fixture['component']=name
    ratio=name.startswith(('retained_fraction','additional_fraction'))
    variance=name.endswith('_variance')
    unit=('dimensionless^2' if ratio else 'pixel^2') if variance else ('dimensionless' if ratio else 'direction_oriented_pixel')
    fixture.update(unit=unit,formula=constants['FORMULAS'][name],meaning=constants['MEANINGS'][name])
    validate_schema([fixture],new['return_schema'])
    for field,wrong in [('unit','dimensionless' if unit!='dimensionless' else 'pixel^2'),
        ('formula','invalid_formula'),('meaning','invalid_meaning')]:
        mutant=deepcopy(fixture);mutant[field]=wrong
        try:validate_schema([mutant],new['return_schema'])
        except ContractError:pass
        else:raise AssertionError((name,field,'bad row accepted'))
        checked.append({'component':name,'field':field,'rejected':True})
    # Wrong-but-otherwise-registered formulas/meanings exercise the new
    # per-component rule rather than just the old generic enumeration.
    other=names[(names.index(name)+1)%len(names)]
    for field,table in [('formula','FORMULAS'),('meaning','MEANINGS')]:
        mutant=deepcopy(fixture);mutant[field]=constants[table][other]
        validate_schema([mutant],old['return_schema'])
        try:validate_schema([mutant],new['return_schema'])
        except ContractError:pass
        else:raise AssertionError((name,field,'wrong registered pairing accepted'))
        checked.append({'component':name,'field':'wrong_registered_'+field,'rejected':True})
receipt={'status':'passed','base001_unchanged_except_items_allOf':True,
    'paired_IO_byte_unchanged':True,'valid_component_shapes':len(names),
    'rejected_mutations':checked,'scientific_case_count_added':0,
    'schema002_sha256':hashlib.sha256((OWN/'EXACT_SCHEMAS_002.json').read_bytes()).hexdigest(),
    'implementation_release':'pending custody/cold proof addendum review'}
with (HERE/'ROOT_CORRECTED_SCHEMA_CHECK_003.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps({'status':'passed','valid_shapes':len(names),'rejected_mutations':len(checked),
    'unrelated_schema_changes':False}))
