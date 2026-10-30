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


fixtures = [Source(product='4', cofactor='8'), Source(product='0', cofactor='9')]
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
    if i == 1:
        args['quantities']['product']['measurement_semantics']=fixture.interpretation('reported_nondetection','Negligible product; not detected')
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



from gene_annotation_episode.literature_compiled_assay_storage import LiteratureCompiledAssayRepository
from gene_annotation_episode.literature_compiled_assay_render import render_common_received, task_relevant, common_task_relevant
from gene_annotation_episode.literature_experimental_prompt import _section, _table
request['requested_cells']=['estimate_product_test']
ctx=replace(ctx,assignment={**ctx.assignment,'requested_compiled_assay_components_v3':request['requested_cells']})
repo=LiteratureCompiledAssayRepository(store,ctx.run_id)
assert repo.has_work(ctx) is False
outcome=repo.populate(ctx,request,'root226synthetic_nativeND')
owned=replace(ctx,received_record_refs=(*ctx.received_record_refs,*outcome['record_refs']))
assert repo.has_work(owned) is False
assert repo.v3_projection().has_work(owned) is True
row,=outcome['result']['cells']
assert row['value']==0 and row['native_semantics']=='reported_nondetection' and row['origin']=='synthetic'
parts=[];render_common_received(parts,[row],section=_section,table=_table)
text='\n'.join(parts)
assert 'reported_nondetection' in text and 'synthetic' in text
state={'literature_assignment':ctx.assignment,'last_local_outcome':outcome}
assert common_task_relevant(state) is True and task_relevant(state) is False
store.close()
receipt={'scope':'Explicitly synthetic actual repository/native-ND component and direct common renderer/task-relevance checks. Not full episode/shared-loop delivery.',
    'native_zero_explicitly_rendered_as_reported_nondetection':True,
    'synthetic_origin_rendered':True,'v3_work_does_not_trigger_legacy_has_work':True,
    'v3_projection_has_actual_own_work':True,'common_task_relevant_legacy_task_irrelevant':True,
    'rendered_text':text}
with options.output.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='rendered_text'}))
