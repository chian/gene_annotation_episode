"""Independent final interface checks; no proposed production module exists yet."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import math
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OWN=HERE.parent/'a105_summary_precision_components_248'
sys.path.insert(0,str(ROOT))
from gene_annotation_episode.domain import ContractError,validate_schema
from jsonschema import Draft202012Validator

manifests=[]
for path in sorted(OWN.glob('*MANIFEST_00[123].json')):
    manifest=json.loads(path.read_text())
    for entry in manifest['files']:
        target=(OWN/entry['path']).resolve()
        assert target.is_relative_to(OWN.resolve()) and target.name!='GOAL.md'
        raw=target.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==entry['sha256'],entry['path']
        if 'bytes' in entry:assert len(raw)==entry['bytes']
    manifests.append({'name':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'files_verified':len(manifest['files'])})
schemas={name:json.loads((OWN/(name+'_SCHEMA_002.json')).read_text())
    for name in ('SELECTION','EXTRACTION','CALCULATION_INPUTS')}
schemas['SHEET']=json.loads((OWN/'SHEET_SCHEMA_003.json').read_text())
for schema in schemas.values():Draft202012Validator.check_schema(schema)
selection=json.loads((OWN/'ACTUAL_SOURCE_SELECTION_PROPOSAL_002.json').read_text())
inputs=json.loads((OWN/'ACTUAL_SOURCE_CALCULATION_INPUT_PROPOSAL_002.json').read_text())
validate_schema(selection,schemas['SELECTION']);validate_schema(inputs,schemas['CALCULATION_INPUTS'])
examples=json.loads((OWN/'CELL_CONFORMANCE_EXAMPLES_003.json').read_text())
valid_names=('actual242_proposed_sheet','partial_missing_central_value_proposed_sheet',
    'partial_attempted_scenario_proposed_sheet')
for name in valid_names:validate_schema(examples[name],schemas['SHEET'])
base=examples['actual242_proposed_sheet']
source=base['source_cells'];scenario=base['scenario_cells']
assert source['independent_preparation_count']['value']==2
assert source['statistical_estimator_count']['value'] is None
assert source['mean_standard_error']['value'] is None
assert math.isclose(source['relative_reported_sd']['value'],1/31)
assert math.isclose(scenario['mean_variance']['value'],float(Fraction(9,500000000000)))
assert math.isclose(scenario['mean_standard_error']['value'],math.sqrt(1.8e-11))
assert len(scenario['mean_variance']['stipulated_assumptions'])==4
assert len(scenario['mean_interval_lower']['stipulated_assumptions'])==6
for group in (source,scenario):
    assert group['mean_interval_confidence_level']['origin']=='proposed'
rejections=[]
for group_name in ('source_cells','scenario_cells'):
    names=list(base[group_name])
    for index,name in enumerate(names):
        for field,wrong in [('formula_code','summary_precision_'+names[(index+1)%len(names)]),
            ('unit','dimensionless' if name in ('source_summary_count','independent_preparation_count',
                'statistical_estimator_count','mean_interval_df') else 'count')]:
            mutant=deepcopy(base);mutant[group_name][name][field]=wrong
            try:validate_schema(mutant,schemas['SHEET'])
            except ContractError:pass
            else:raise AssertionError((group_name,name,field))
            rejections.append({'group':group_name,'cell':name,'field':field})
partial=examples['partial_missing_central_value_proposed_sheet']
assert partial['source_cells']['reported_parameter']['value'] is None
assert partial['source_cells']['reported_sd']['value']==12
assert partial['source_cells']['mean_standard_error']['value']==6
task=(OWN/'TASK_PROPOSAL_001.txt').read_bytes()
assert task==(HERE.parent/'a105_independent_preparation_review_246/SUMMARY_PRECISION_TASK_PROPOSAL_004.txt').read_bytes()
proposed=json.loads((OWN/'PLAN_MANIFEST_001.json').read_text())['proposed_production_files']
assert all(not (ROOT/name).exists() for name in proposed)
report={'status':'passed','manifests':manifests,'four_schemas_valid':True,
    'actual_source_selection_and_inputs_valid':True,'valid_proposed_sheet_shapes':list(valid_names),
    'independent_bad_formula_unit_rejections':rejections,'actual_source_n_preserved_statistical_n_unknown':True,
    'scenario_precision_matches_independent_root246_arithmetic':True,
    'missing_parameter_preserves_SD_and_SE':True,'TASK_byte_identical':True,
    'production_files_absent':True,'no_proposed_calculator_execution':True,
    'scope':'Interface conformance and proposed arithmetic shapes, not selected integration or A105 adequacy.'}
with (HERE/'ROOT_FROZEN_PLAN_CHECK_003.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'status':'passed','manifests':manifests,'bad_pairings_rejected':len(rejections),
    'valid_sheet_shapes':len(valid_names),'production_files_absent':True}))
