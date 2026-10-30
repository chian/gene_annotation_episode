"""Plan artifacts only. Never reads a paper, source image or provider traffic."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import collections

ROOT = Path(__file__).resolve().parents[3]
OWN = Path(__file__).resolve().parent
PURE = OWN.parent / 'a105_endpoint_signal_components_241'

def save(name, value):
    (OWN/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')

def obj(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
def array(items, **kw): return {'type':'array','items':items,**kw}
def nullable(schema): return {'anyOf':[schema, {'type':'null'}]}
def enum(values): return {'type':'string','enum':list(values)}
def const(value): return {'const':value}
def ref(nullable=False, namespace='source'):
    return {'type':['string','null'] if nullable else 'string','format':'reference','x-reference-namespace':namespace}
def load(name): return json.loads((PURE/name).read_text())

pure_input = load('INPUT_SCHEMA_002.json')
pure_extraction = load('EXTRACTION_SCHEMA_002.json')
pure_sheet = load('SHEET_SCHEMA_002.json')
pure_covariance = load('COVARIANCE_SCHEMA_002.json')
cell = pure_sheet['properties']['cells']['items']
components = pure_input['properties']['requested_cells']['items']['enum']
context_fields = tuple(pure_input['properties']['context']['properties'])
# Repetition and numerical correction discussion stay in original host custody.
# The finite-window meaning is copied separately, with no coordinates.
selected_context_fields = tuple(x for x in context_fields if x not in
    ('sampling_window','correction_discussion','repetition'))
window = obj({'start':{'type':'integer','minimum':0},'end':{'type':'integer','minimum':1}})
context_selection = obj({name:array(deepcopy(window),uniqueItems=True) for name in selected_context_fields})
endpoint_request = obj({'version':const('literature_figure_endpoint_signal_population_v1'),
    'selection':pure_input, 'return_context':context_selection})

# Existing legacy schema is read as code through its pure factory only. No repo
# constructor, source bytes, calculator or model is called by this plan builder.
import sys
sys.path.insert(0,str(ROOT))
from gene_annotation_episode.literature_figure_inputs import figure_population_schema
legacy = figure_population_schema()
operation = {'type':'object','anyOf':[legacy,endpoint_request]}
location = obj({'source_ref':ref(),'artifact_ref':ref(namespace='artifact'),
    'representation':enum(('original','text')),
    'start':{'type':'integer','minimum':0},'end':{'type':'integer','minimum':1}})
fragment = obj({'text':{'type':'string','minLength':1},'location':location})
meaning = obj({'status':enum(('selected','not_selected','source_unavailable')),
    'fragments':array(fragment)})
interpretations = obj({name:obj({'value':{**deepcopy(schema['properties']['value']), 'type':'string'},
    'status':enum(('authenticated_interpretation','source_unavailable'))})
    for name,schema in pure_input['properties']['relationships']['properties'].items()})
dependency_meanings = ['same_selected_trace_shared_initial', 'D_equals_C_plus_G',
    'C_equals_F_times_D', 'H_equals_one_minus_F', 'dependent_views_not_independent_assays',
    'amplitude_not_initial_rate_g', 'fraction_not_function_probability']
uncertainty = obj({'availability':enum(('unreported','available','unavailable','unknown')),
    'source_ref':ref(True),
    'basis':nullable(enum(('joint_manual_reading_error','joint_physical_ordinate_estimates'))),
    'variance_status':nullable(enum(('known','estimated','unknown'))),
    'origin':nullable(enum(('source_reported','source_derived','synthetic'))),
    'coordinate_units_status':nullable(const('already_in_declared_native_coordinate_units')),
    'physical_uncertainty':enum(('unreported','supplied_physical_estimate_model','unknown')),
    'published_ratio_uncertainty':const('not_extracted')})
row_props = deepcopy(cell['properties'])
row_props.update({'row_version':const('endpoint_signal_return_v1'),
    'sheet_ref':ref(),'evidence_source_ref':ref(),'image_source_ref':ref(True),
    'evaluation_scope':const('source_endpoint_signal_contribution'),
    'source_kind':deepcopy(pure_input['properties']['source_kind']),
    'source_context':obj({name:deepcopy(meaning) for name in selected_context_fields}),
    'relationships':interpretations,
    'sampling_window':nullable(const('finite_selected_late_point_no_physical_time_extracted')),
    'uncertainty':uncertainty,
    'physical_preparation_count':{'type':'null'},
    'physical_preparation_count_status':const('not_extracted'),
    'molecular_attribution':const('not_established_by_signal_decomposition'),
    'functional_relevance':const('not_scored_by_endpoint_section'),
    'dependency_meanings':const(dependency_meanings),
    'source_scope':array(ref(),uniqueItems=True),
    'withheld_locations':array(deepcopy(location),uniqueItems=True),
    'withheld_image_source_refs':array(ref(),uniqueItems=True)})
rows = {'type':'array','items':obj(row_props),'x-source':'literature_endpoint_signal_cells'}
assignment_selector = array(enum(components),uniqueItems=True)
save('EXACT_SCHEMAS_001.json', {'operation_name':'literature.figure.populate',
    'operation_schema':operation,'legacy_request_schema':legacy,
    'endpoint_request_schema':endpoint_request,
    'assignment_field':'requested_endpoint_signal_components',
    'assignment_selector_schema':assignment_selector,'return_schema':rows,
    'provider':'literature.experimental.figure',
    'legacy_record_version':'literature_figure_record_v1',
    'endpoint_record_version':'literature_figure_endpoint_signal_record_v1',
    'endpoint_view':'endpoint_signal_components'})

example=load('EXAMPLE_INPUT_002.json')
selected=['retained_fraction','retained_fraction_variance']
example['requested_cells']=selected
contexts={name:[] for name in selected_context_fields}
for name in ('subject','organism','partners','endpoint','limitations'):
    witness=example['context'][name]
    contexts[name]=[{'start':witness['start'],'end':witness['end']}]
def within(name,text):
    witness=example['context'][name]
    before,_,_=witness['quote'].partition(text)
    assert text in witness['quote']
    start=witness['start']+len(before.encode())
    return {'start':start,'end':start+len(text.encode())}
contexts['experiment']=[within('experiment','Time course')]
contexts['condition']=[within('condition',text) for text in
    ('60 °C','0.75 mL assay mixture','1.6 M potassium phosphate (pH 7)',
     'MvhADG/HdrABC complex (∼0.1 unit)','MTZ (90 nmol)')]
contexts['experimental_system']=[within('experimental_system','anaerobic cuvettetes'),
    within('experimental_system','assay mixture')]
request={'version':'literature_figure_endpoint_signal_population_v1',
    'selection':example,'return_context':contexts}
save('PAIRED_SELECTED_INPUT_001.json', {'status':'reviewed_source_contract_IO_proposal_not_executed',
    'assignment':{'version':'literature_assignment_v1','question_context_refs':[],
        'source_refs':['source_kaster_primary','source_kaster_original_figure4'],
        'requested_endpoint_signal_components':selected},
    'operation':'literature.figure.populate','arguments':request})
projected={}
for name,windows in contexts.items():
    witness=example['context'][name]
    projected[name]= {'status':'selected' if windows else 'not_selected','fragments':[]}
    for w in windows:
        raw=witness['quote'].encode()
        text=raw[w['start']-witness['start']:w['end']-witness['start']].decode()
        projected[name]['fragments'].append({'text':text,'location':{
            'source_ref':witness['source_ref'],'artifact_ref':'artifact_'+'0'*64,
            'representation':witness['representation'],**w}})
constants=load('CELL_CONSTANTS_002.json')
def exact(q):
    return {'numerator':str(q.numerator),'denominator':str(q.denominator)}
conditions=['same_trace_shared_initial_ordinate','selected_finite_time_coordinate',
    'common_affine_native_ordinate','selected_ordinate_direction','uncorrected_source_trace',
    'source_displayed_baseline','baseline_extrapolation_stipulated','fast_component_completion_stipulated']
template={'row_version':'endpoint_signal_return_v1','sheet_ref':'source_'+'1'*24,
    'evidence_source_ref':'source_kaster_primary','image_source_ref':'source_kaster_original_figure4',
    'evaluation_scope':'source_endpoint_signal_contribution','source_kind':'primary_source',
    'source_context':projected,'relationships':{name:{'value':value['value'],
        'status':'authenticated_interpretation'} for name,value in example['relationships'].items()},
    'sampling_window':'finite_selected_late_point_no_physical_time_extracted',
    'uncertainty':{'availability':'unreported','source_ref':None,'basis':None,'variance_status':None,
        'origin':None,'coordinate_units_status':None,'physical_uncertainty':'unreported',
        'published_ratio_uncertainty':'not_extracted'},
    'physical_preparation_count':None,'physical_preparation_count_status':'not_extracted',
    'molecular_attribution':'not_established_by_signal_decomposition',
    'functional_relevance':'not_scored_by_endpoint_section','dependency_meanings':dependency_meanings,
    'source_scope':['source_kaster_primary','source_kaster_original_figure4'],
    'withheld_locations':[], 'withheld_image_source_refs':['source_kaster_original_figure4']}
locations=[]
def witnesses(v):
    if isinstance(v,dict):
        if {'source_ref','representation','start','end','quote'}<=v.keys():
            yield {k:v[k] for k in ('source_ref','representation','start','end')}
        else:
            for c in v.values():yield from witnesses(c)
    elif isinstance(v,list):
        for c in v:yield from witnesses(c)
for w in witnesses(example):
    entry={**w,'artifact_ref':'artifact_'+'0'*64}
    if entry not in locations:locations.append(entry)
template['withheld_locations']=locations
expected=[]
for name in selected:
    variance=name.endswith('_variance')
    q=None if variance else Fraction(131,142)
    lo=None if variance else Fraction(128,143)
    hi=None if variance else Fraction(67,71)
    expected.append({**deepcopy(template),'component':name,'value':None,
        'conditional_value':None if variance else float(q), 'exact_value':None,
        'conditional_exact_value':None if variance else exact(q),
        'lower':None if variance else float(lo),'upper':None if variance else float(hi),
        'exact_lower':None if variance else exact(lo),'exact_upper':None if variance else exact(hi),
        'unit':'dimensionless^2' if variance else 'dimensionless',
        'status':'unavailable' if variance else 'conditional_scenario','origin':'derived',
        'input_origins':['graph_derived_manual','reported'],'formula':constants['FORMULAS'][name],
        'meaning':constants['MEANINGS'][name],
        'conditional_on':conditions+(['first_order_covariance_propagation'] if variance else []),
        'unavailable_reasons':['covariance_unreported'] if variance else [],
        'qualifications':['manual_reading_not_physical_measurement','not_molecular_attribution',
            'physical_covariance_unreported',
            'first_order_covariance_propagation' if variance else 'reading_bounds_not_statistical_CI'],
        'bound_kind':'none' if variance else 'manual_reading_enclosure_not_confidence_interval',
        'primitive_owners':['endpoint_coordinate_'+'2'*24,'endpoint_coordinate_'+'3'*24,
            'endpoint_coordinate_'+'4'*24], 'contribution_key':'endpoint_contribution_'+'5'*24,
        'uncertainty_basis':None})
save('PAIRED_SELECTED_OUTPUT_001.json',{'status':'IO_proposal_not_selected_runtime_execution',
    'placeholder_identity_note':'Only host identities/artifact refs are symbolic; numerical values use the reviewed source contract. Exact outward float enclosure is production-calculator-owned; rational bounds are authoritative here.',
    'normal_typed_return':{'numbers':expected},
    'nested_narrower_request':['retained_fraction'],
    'nested_narrower_return':{'numbers':expected[:1]}})
for filename in ('INPUT_SCHEMA_002.json','EXTRACTION_SCHEMA_002.json','SHEET_SCHEMA_002.json',
    'COVARIANCE_SCHEMA_002.json'):
    # Lossless unique-node representation repairs earlier tool-output truncation.
    pass
roots={'INPUT':pure_input,'EXTRACTION':pure_extraction,'SHEET':pure_sheet,'COVARIANCE':pure_covariance}
counts=collections.Counter()
def scan(v):
    if isinstance(v,(dict,list)):
        counts[json.dumps(v,sort_keys=True,separators=(',',':'))]+=1
        for x in v.values() if isinstance(v,dict) else v:scan(x)
for v in roots.values():scan(v)
selected_nodes={k for k,c in counts.items() if c>1 and len(k)>140};names={};pool={}
def compact(v,skip=None):
    key=json.dumps(v,sort_keys=True,separators=(',',':')) if isinstance(v,(dict,list)) else None
    if key in selected_nodes and key!=skip:
        if key not in names:
            label='N'+str(len(names)+1);names[key]=label;pool[label]=compact(v,skip=key)
        return {'POOL':names[key]}
    if isinstance(v,dict):return {k:compact(x) for k,x in v.items()}
    if isinstance(v,list):return [compact(x) for x in v]
    return v
compact_roots={n:compact(v) for n,v in roots.items()}
def expand(v):
    if isinstance(v,dict) and set(v)=={'POOL'}:return expand(pool[v['POOL']])
    if isinstance(v,dict):return {k:expand(x) for k,x in v.items()}
    if isinstance(v,list):return [expand(x) for x in v]
    return v
assert {n:expand(v) for n,v in compact_roots.items()}==roots
(OWN/'PURE_SCHEMAS_LOSSLESS_001.txt').write_text('ROOTS '+json.dumps(compact_roots,separators=(',',':'))+'\n'+
    ''.join(k+' '+json.dumps(v,separators=(',',':'))+'\n' for k,v in pool.items()))
save('PLAN_ARTIFACT_CUSTODY_001.json',{'status':'plan_only_no_production_edits',
    'pure_pin':'a105_endpoint_signal_components_241/implementation_004/MANIFEST_003.json',
    'schema_pool_lossless_round_trip':True,'selected_context_fields':list(selected_context_fields),
    'read_paper_or_scientific_packet':False,'read_private_provider_payloads':False,
    'request_roster':selected,'initial_assignment_request_roster_equality':True})
print('Wrote exact operation/assignment/row schemas and paired IO proposal; no scientific reader/calculator/model or production mutation.')
