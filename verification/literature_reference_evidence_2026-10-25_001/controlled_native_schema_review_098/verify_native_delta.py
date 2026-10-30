"""Parent check of the exact per-condition native-context declaration delta."""
import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from gene_annotation_episode import literature_controlled_response_v3_inputs as live
from gene_annotation_episode import literature_controlled_response_v3_population as population
from gene_annotation_episode import literature_controlled_response_storage as native
from test_literature_controlled_response_v3_inputs import Fixture

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'verification/literature_reference_evidence_2026-10-25_001'
OUT=Path(__file__).resolve().parent
before=BASE/'controlled_source_stages_089/pin_002/gene_annotation_episode/literature_controlled_response_v3_inputs.py'
spec=importlib.util.spec_from_file_location('gene_annotation_episode._accepted_native_schema_098',before)
accepted=importlib.util.module_from_spec(spec);spec.loader.exec_module(accepted)
old,new=accepted._schemas(),live._schemas()
unchanged={key:old[key]==new[key] for key in new if not key.startswith('NATIVE_')}
assert len(unchanged)==5 and all(unchanged.values())
native_only={}
for key in new:
    Draft202012Validator.check_schema(new[key])
    if not key.startswith('NATIVE_'):continue
    candidate=deepcopy(new[key]);context=candidate['$defs']['SemanticContext']
    declaration=context['properties'].pop('condition_control_applications')
    assert set(declaration['properties'])=={'condition1','condition0'}
    assert declaration['additionalProperties'] is False
    context['required'].remove('condition_control_applications')
    native_only[key]=candidate==old[key]
assert len(native_only)==2 and all(native_only.values())
assert 'selection_basis' not in json.dumps(new)

# The old design constructor is checked in memory, never overwriting its
# historical expanded JSON or manifests.
builder=BASE/'a105_controlled_v3_partial_design_078/build_declarations_007.py'
tree=ast.parse(builder.read_text())
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name=='put':node.body=ast.parse('captured[n]=x').body
ast.fix_missing_locations(tree)
namespace={'__file__':str(builder),'captured':{}}
exec(compile(tree,str(builder),'exec'),namespace)
matches={key:namespace['captured'][key+'.json']==value for key,value in new.items()}
assert all(matches.values())

f=Fixture()
# The baseline fixture explicitly uses a shared-reference assumption for BOTH
# conditions. Construct a different, fully declared source arrangement instead
# of falsely asserting the original fixture already has two applications.
clause='Constructed B was measured under Condition one, matched for condition1, and reused for condition0 under stated invariance.'
f.append(clause)
clause_witness=f.witness(clause)
f.args['relationships']['condition1_control_application']={'value':'matched_condition_control','witnesses':[deepcopy(clause_witness)]}
f.args['relationships']['condition0_control_application']={'value':'shared_reference_assumption','witnesses':[deepcopy(clause_witness)]}
f.args['relationships']['control_reference_reuse']={'value':'same_reference_with_stated_invariance','witnesses':[deepcopy(clause_witness)]}
for role in ('empty_condition1','empty_condition0'):
    f.args['arms'][role]['condition']=deepcopy(f.args['relationships']['condition1_target'])
extraction=f.read();populated=population.populate_controlled_response_v3(extraction)
rows=native._component_rows(extraction,populated,'source_'+'0'*24)
row=next(row for row in rows if row['component_key']=='final:controlled_response_difference')
wanted={condition:extraction['relationships'][condition+'_control_application']['effective_value']
        for condition in ('condition1','condition0')}
assert len(set(wanted.values()))==2
assert row['context']['condition_control_applications']==wanted
assert row['context']['control_application'] is None
raw=next(row for row in rows if row['component_key']=='raw:protein_condition1:primary')
operand=extraction['arms']['protein_condition1']['calculation_operand']
assert raw['native_reading']=={key:operand[key] for key in raw['native_reading']}
assert raw['native_reading']['value']==10 and raw['native_reading']['unit']=='nmol/min'
result=dict(unchanged_source_local_population_schemas=unchanged,
    exact_two_native_schema_deltas=native_only,all_seven_current_constructor_matches=matches,
    metavalidation_count=7,selection_basis_gate_present=False,
    actual_constructed_control_applications=wanted,common_application=None,
    native_source_value_unit=[raw['native_reading']['value'],raw['native_reading']['unit']],
    current_v3_module_sha256=hashlib.sha256(Path(live.__file__).read_bytes()).hexdigest(),
    scope='Pure constructed source/population/native-projection check; native repository and episode integration still under development',
    original_goal_changed=False)
with (OUT/'RESULTS.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(result,indent=2))
