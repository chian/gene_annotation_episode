"""Independent synthetic numerical/custody checks against an explicit code pin.

No primary paper, actual model, episode/controller, or scientific-credit run.
The rank-one uncertainty oracle is a directional response of the mathematical
contrast, independently simplified to49/169, not a paper measurement.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import sys
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction

parser = argparse.ArgumentParser()
parser.add_argument('--pin', type=Path, required=True)
parser.add_argument('--store', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
options = parser.parse_args()
pin = options.pin.resolve()
sys.dont_write_bytecode = True
sys.path[:0] = [str(pin), str(pin/'tests')]

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_product_coupling_storage import LiteratureProductCouplingRepository
from gene_annotation_episode.literature_compiled_assay_inputs import (
    COMMON_REQUEST, COMMON_POPULATION, COMMON_CONTEXT, COMMON_ARM_CONTEXT,
    COMMON_ROLES, COMMON_GROUPS, COMMON_ASSUMPTIONS, COMMON_PARAMETER_KINDS,
    read_common_assessment_inputs,
)
from gene_annotation_episode.literature_compiled_assay_calculations import populate_common_assessment
from test_literature_product_coupling_212 import Source
from test_literature_product_coupling_binding_218 import rebind

assert not options.store.exists(), 'Use a fresh synthetic store.'
store = Store(options.store)
store.create_problem(raw_sequence='ATGGCT', molecule='dna')
sources = {}
rows = {}


def publish(raw):
    artifact = store.artifact(raw, 'application/xml' if raw.startswith(b'<') else 'application/json')
    ref = store.put('source', {'provider':'explicitly_synthetic_root224', 'accession':None,
        'uri':None, 'artifact_ref':artifact, 'text_ref':None, 'request_ref':None,
        'version':None, 'retrieved_at':None}, origin='caller')['id']
    sources[ref] = {'artifact_ref':artifact, 'content':raw}
    return ref


fixtures = [Source(product='4', cofactor='8'), Source(product='3', cofactor='9')]
refs = [publish(s.content) for s in fixtures]
raw = (b'<article><p>Q</p><p>Explicit synthetic assumptions and applicable controls.</p>'
       b'<table><tr><th>Construct</th><th>Kd</th><th>S</th><th>B</th><th>k</th><th>f</th><th>c</th></tr>'
       b'<tr><th>name</th><th>uM</th><th>uM</th><th>per_min</th><th>fraction</th><th>fraction</th><th>fraction</th></tr>'
       b'<tr><td>Q</td><td>2</td><td>11</td><td>1</td><td>0.8</td><td>0.6</td><td>2</td></tr>'
       b'<tr><td>Q</td><td>7</td><td>11</td><td>0.5</td><td>1.2</td><td>0.4</td><td>3</td></tr></table></article>')
parameters = publish(raw)
ctx = BindingContext('synthetic224', 'child224', 'literature', (('literature','child224'),),
    store.validate_scope(), {'version':'literature_assignment_v1', 'source_refs':list(sources),
    'question_context_refs':[], 'requested_product_coupling_components':[
        'reported_product_activity','reported_cofactor_activity']}, {}, tuple(sources))
repo = LiteratureProductCouplingRepository(store, ctx.run_id)
sheet_refs = []
for i, (fixture, ref) in enumerate(zip(fixtures, refs)):
    args = fixture.args()
    args['context']['construct'] = fixture.witness('Q')
    args = rebind(args, {fixture.reference:ref})
    outcome = repo.populate(ctx, args, 'native_'+str(i))
    ctx = replace(ctx, received_record_refs=(*ctx.received_record_refs,*outcome['record_refs']))
    sheet_refs.append(outcome['result']['sheet_ref'])
    for row in outcome['result']['cells']:
        rows[(row['sheet_ref'], row['component'])] = row


def witness(start, end):
    return dict(source_ref=parameters, representation='original', start=start, end=end,
                quote=raw[start:end].decode())


table_rows = list(re.finditer(rb'<tr>(.*?)</tr>', raw, re.S))


def cell(row, column):
    block = table_rows[row]
    match = list(re.finditer(rb'<(?:td|th)>(.*?)</(?:td|th)>', block.group(), re.S))[column]
    start = block.start()+match.start(1)
    return witness(start, start+len(match.group(1)))


support_start = raw.index(b'Explicit synthetic')
support = witness(support_start, raw.index(b'</p>', support_start))


def meaning(value):
    return {'value':value, 'witnesses':[] if value=='unknown' else [support]}


request = {'version':COMMON_REQUEST, 'population_version':COMMON_POPULATION,
    'source_ref':refs[0], 'source_kind':'synthetic_fixture',
    'assertion':{**{k:None for k in COMMON_CONTEXT},
                 'resolution':'binding_occupancy_alternative', 'question':'named_alternative'},
    'arms':{a:{k:cell(i,0) if k=='construct' else None for k in COMMON_ARM_CONTEXT}
            for a,i in [('reference',2),('test',3)]},
    'subject_relationship':meaning('same_construct_supported'),
    'relationships':{g:{k:meaning('compatible_supported')
                       for k in ('endpoint','normalization','preparation','conditions')} for g in COMMON_GROUPS},
    'product_reporter_relationship':meaning('author_assigned_pair'),
    'sampling_relationship':meaning('unknown'), 'estimates':{r:None for r in COMMON_ROLES},
    'model':{'kind':'one_site_equilibrium','scope':'conditional_sensitivity',
             'substrate_ownership':'shared_owner', 'substrate_uncertainty':'selected_estimate_covariance',
             'assumptions':{k:meaning('stipulated_sensitivity') for k in COMMON_ASSUMPTIONS}},
    'correction_factorization':meaning('supported'), 'covariance_source_refs':[],
    'requested_cells':['product_reference_contrast','productive_use_reference_contrast',
        'occupancy_reference_contrast','post_binding_residual_ratio','binding_only_log_residual',
        'binding_only_residual_variance','fully_corrected_activity_reference_contrast']}
for arm,i,sheet in [('reference',2,sheet_refs[0]),('test',3,sheet_refs[1])]:
    for base,component in [('product','reported_product_activity'),('reporter','reported_cofactor_activity')]:
        request['estimates'][base+'_'+arm] = {'kind':'received_component',
            'namespace':'literature_product_coupling_cells', 'sheet_ref':sheet, 'component':component}
    for column,base in enumerate(('Kd','free_substrate','background','recovery','active_fraction','nuisance_response'),1):
        selected_row = 2 if base=='free_substrate' else i
        number = cell(selected_row,column)
        request['estimates'][base+'_'+arm] = {'kind':'source_parameter', 'source_kind':'synthetic_fixture',
            'parameter_kind':meaning(COMMON_PARAMETER_KINDS[base]), 'layout':'table', 'record':None,
            'number':{'witness':number,'number_start':0,'number_end':len(number['quote'])},
            'row_label':cell(selected_row,0), 'quantity_label':cell(0,column), 'unit':cell(1,column),
            'semantics':meaning('reported_point'), 'method':support, 'assay':None,'conditions':None,
            'normalization':None,'population':None,'physical_identity':None,'reported_spread':None}


def read_source(ref, representation):
    if ref not in ctx.received_record_refs or representation!='original':
        raise ContractError('synthetic_source_not_received')
    return deepcopy(sources[ref])


def read_component(selected):
    key = selected['sheet_ref'], selected['component']
    return [] if key not in rows else [deepcopy(rows[key])]


def bind(args):
    return read_common_assessment_inputs(args, read_source=read_source,
        read_component=read_component, read_record=store.get)


def exact(row):
    value = row['exact_value'] or row['conditional_exact_value']
    return None if value is None else Fraction(int(value['numerator']), int(value['denominator']))


bound = bind(request)
roles = ['product_test','product_reference','Kd_test','Kd_reference','free_substrate_test']
direction = [1,2,-1,3,4]
covariance = {'version':'a105_common_assessment_covariance_v1', 'roles':roles,
    'owner_keys':[bound['estimates'][r]['owner_key'] for r in roles],
    'units':[bound['estimates'][r]['unit'] for r in roles],
    'dependency_keys':[bound['estimates'][r]['dependency_keys'] for r in roles],
    'covariance':[[a*b for b in direction] for a in direction],
    'basis':'joint_covariance_of_selected_estimates','variance_status':'known','origin':'synthetic'}
covariance_ref = publish(json.dumps(covariance).encode())
ctx = replace(ctx, received_record_refs=(*ctx.received_record_refs,covariance_ref))
request['covariance_source_refs'] = [covariance_ref]
bound = bind(request)
saved = deepcopy(bound)
result = populate_common_assessment(bound)
assert bound == saved, 'Pure calculation mutated inputs.'
actual = {r['component']:r for r in result['cells']}
expected = {'product_reference_contrast':Fraction(3,4),
    'productive_use_reference_contrast':Fraction(2,3),
    'occupancy_reference_contrast':Fraction(13,18),
    'post_binding_residual_ratio':Fraction(27,26),
    'binding_only_residual_variance':Fraction(49,169),
    'fully_corrected_activity_reference_contrast':Fraction(10,13)}
for name, value in expected.items():
    assert exact(actual[name]) == value, (name, actual[name], value)
assert math.isclose(actual['binding_only_log_residual']['conditional_value'], math.log(27/26), rel_tol=1e-13)
assert 'synthetic' in actual['binding_only_residual_variance']['input_origins']

incompatible = deepcopy(request)
incompatible['relationships']['binding']['endpoint'] = meaning('incompatible')
blocked = {r['component']:r for r in populate_common_assessment(bind(incompatible))['cells']}
assert blocked['product_reference_contrast']['value'] == .75
assert blocked['fully_corrected_activity_reference_contrast']['conditional_value'] is None
assert 'relationship_incompatible' in blocked['fully_corrected_activity_reference_contrast']['relationship_reasons']

module_files = {name:Path(module.__file__).resolve() for name,module in sys.modules.items()
    if name.startswith(('gene_annotation_episode','method_loop','test_literature_')) and getattr(module,'__file__',None)}
outside = {name:str(path) for name,path in module_files.items() if not path.is_relative_to(pin)}
assert not outside, outside
receipt = {'scope':'Independent synthetic reader/repository/pure-calculation checks, no paper/model/episode execution.',
    'expected_exact':{k:str(v) for k,v in expected.items()}, 'all_exact_oracles_passed':True,
    'independent_log_oracle_passed':True, 'known_binding_incompatibility_blocks_full_correction':True,
    'native_product_contrast_preserved':True, 'pure_inputs_unchanged':True,
    'imports_outside_pin':outside, 'module_count':len(module_files),
    'imported_source_sha256':{str(path.relative_to(pin)):hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in set(module_files.values())}}
store.close()
with options.output.open('x') as handle:
    json.dump(receipt, handle, indent=2, sort_keys=True)
    handle.write('\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='imported_source_sha256'}))
