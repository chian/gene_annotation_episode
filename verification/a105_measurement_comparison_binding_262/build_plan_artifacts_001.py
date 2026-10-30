"""Generate proposal documents only, from existing public schema/source records.

No acquisition, scientific validation, compilation, calculator or model call.
This is plan packaging, not an installed adapter or selected execution.
"""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PURE = ROOT / 'verification/a105_measurement_comparison_components_258'

def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

tree = ast.parse((ROOT/'gene_annotation_episode/literature_measurement_comparison_inputs.py').read_text())
node = next(n for n in tree.body if isinstance(n, ast.Assign)
    and any(isinstance(t, ast.Name) and t.id == '_SCHEMA_BUNDLE' for t in n.targets))
bundle = json.loads(ast.literal_eval(node.value.args[0]))
def pure_schema(name):
    item = bundle['resources'][name]
    return {**deepcopy(item['body']), '$defs': {k: deepcopy(bundle['definitions'][k]) for k in item['definition_names']}}

def obj(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)
def arr(items):
    return dict(type='array', items=items)
def enum(values):
    return dict(enum=list(values))
def ref(namespace):
    return dict(type='string', format='reference', **{'x-reference-namespace':namespace})

roles = ['left','right','epsilon_signal','epsilon_nuisance','nuisance']
selection = pure_schema('SELECTION')
qdef = bundle['definitions']['quantity_selection']['properties']
fields = ['row_label','quantity_label', *['subject.'+k for k in qdef['subject']['properties']],
    *['assay.'+k for k in qdef['assay']['properties']]]
window = obj({'start':dict(type='integer',minimum=0), 'end':dict(type='integer',minimum=1)})
contexts = obj({r:obj({k:arr(window) for k in fields}) for r in roles})
request = obj({'version':{'const':'literature_measurement_comparison_population_v1'},
    'selection':{'$ref':'#/$defs/selection'}, 'return_context':contexts})
request.update({'$schema':selection['$schema'], '$defs':deepcopy(selection['$defs'])})
request['$defs']['selection'] = {k:v for k,v in selection.items() if k not in ('$defs','$id','$schema')}
save('POPULATION_REQUEST_SCHEMA_001.json', request)

sheet_schema = pure_schema('SHEET')
components = sheet_schema['$defs']['cell']['properties']['component']['enum']
location = obj({'source_ref':ref('source'), 'artifact_ref':ref('artifact'),
    'representation':enum(['original','text']), 'start':dict(type='integer',minimum=0),
    'end':dict(type='integer',minimum=1)})
fragment = obj({'text':dict(type='string',minLength=1), 'location':location})
context = obj({'field':enum(fields), 'status':enum(['selected','not_selected','source_unavailable']),
    'fragments':arr(fragment)})
meaning_props = {k:deepcopy(bundle['definitions']['quantity_value']['properties'][k]) for k in
    ('role','estimator_scale','quantity_kind','semantics','normalization','origin','relation','approximate')}
meaning_props.update({'qualification':deepcopy(qdef['qualification']['properties']['value']),
    'reported_uncertainty_statistic':deepcopy(bundle['definitions']['uncertainty_selection']['properties']['statistic']['properties']['value']),
    'reported_uncertainty_meaning':{'const':'reported_spread_not_joint_estimator_covariance'},
    'contexts':arr(context)})
role_meaning = obj(meaning_props)
relationships = {'type':'array','items':{'oneOf':[obj({'name':{'const':k},'value':deepcopy(v)})
    for k,v in sheet_schema['properties']['relationship_meanings']['properties'].items()]}}
premise_states = {k:enum([*bundle['definitions']['model_meaning']['properties']['value']['enum'],'not_selected']) for k in
    ('common_model.applicability','optical.raw_optical_relation','optical.coefficient_applicability',
    'optical.estimate_scale_applicability','optical.nuisance_quantity_linkage',
    'optical.scenario.common_rate_equality','optical.scenario.linear_mixture_on_estimate_scale')}
premises = arr({'oneOf':[obj({'name':{'const':k},'state':deepcopy(v)}) for k,v in premise_states.items()]})
binding = deepcopy(sheet_schema['properties']['estimate_bindings']['items'])
binding['properties']['source_locations'] = arr(location)
binding['required'].append('source_locations')
props = {'row_version':{'const':'measurement_comparison_return_v1'},
    'sheet_ref':ref('source'),'evidence_source_ref':ref('source'),
    'evaluation_scope':{'const':'source_measurement_comparison'},'component':enum(components),
    'cell':{'$ref':'#/$defs/cell'},'source_kind':enum(['primary_source','synthetic_fixture']),
    'assertion_question':deepcopy(selection['properties']['assertion']['properties']['question']),
    'role_meanings':arr(role_meaning),'relationships':relationships,'model_conditions':premises,
    'conversion_conditions':arr(obj({'role':enum(['left','right']),
        'kind':deepcopy(bundle['definitions']['conversion']['properties']['kind']),
        'direction':deepcopy(bundle['definitions']['conversion']['properties']['direction']['properties']['value']),
        'support_status':deepcopy(bundle['definitions']['conversion']['properties']['support_status']['properties']['value'])})),
    'covariance_provenance':arr(obj({k:deepcopy(bundle['definitions']['covariance_block']['properties'][k]) for k in
        ('source_ref','artifact_ref','basis','variance_status','origin','systematic_coverage','derivation','status')})),
    'model_settings':obj({'common_variance_interpretation':enum(['not_selected','known_joint_estimator_covariance','estimated_joint_estimator_covariance','unknown']),
        'common_combination':enum(['not_selected','generalized_least_squares','not_requested']),
        'optical_observation_equation':enum([None,'y=h+s*alpha*f']),
        'optical_signal_role':enum([None,'left','right']),'optical_nuisance_sign':enum([None,-1,1]),
        'scenario_anchor_role':enum([None,'left','right'])}),
    'dependencies':arr(binding), 'dependence':deepcopy(sheet_schema['properties']['dependence']),
    'assumptions':deepcopy(sheet_schema['properties']['assumptions']),
    'withheld_locations':arr(location)}
rows = {'$schema':sheet_schema['$schema'],'type':'array','x-source':'literature_measurement_comparison_cells',
    'x-unique-by':['sheet_ref','component'],'items':obj(props),'$defs':deepcopy(sheet_schema['$defs'])}
save('TYPED_RETURN_SCHEMA_001.json',rows)
save('ASSIGNMENT_ADDITION_SCHEMA_001.json',arr(enum(components)))
for name in ('SELECTION','EXTRACTION','CALCULATION_INPUTS','SHEET','COVARIANCE_DOCUMENT'):
    save('PURE_'+name+'_SCHEMA_001.json',pure_schema(name))

pair=['endpoint','denominator']
common=['construct','preparation_target','protocol','functional_bearing','left_validity','right_validity']
scientific=['attribution','sampling','systematic_coverage','left_readout_isolation','right_readout_isolation']
conv=['direction','support_status']
mapping={}
for c in components:
    if c.startswith('native_'):
        r=c.removeprefix('native_'); rs=[r]; rel=[]; ms=[]; cov=False
    elif c.startswith('converted_'):
        r=c.removeprefix('converted_'); rs=[r]; rel=[]; ms=['conversion.'+r]; cov=False
    elif c.startswith('protocol_'):
        rs=['left','right']; rel=pair+scientific+['protocol','functional_bearing','left_validity','right_validity']; ms=['conversion.left','conversion.right']; cov=False
    elif c.startswith('common_') or c in ('standardized_difference','squared_standardized_difference','weight_left','weight_right','combined_estimate','combined_variance','combined_standard_uncertainty'):
        rs=['left','right']; rel=list(dict.fromkeys(pair+common+scientific)); ms=['conversion.left','conversion.right','common_model.applicability']; cov=not c.startswith('common_')
    elif c in ('difference_variance','difference_standard_uncertainty'):
        rs=['left','right']; rel=pair+['sampling','systematic_coverage']; ms=['conversion.left','conversion.right']; cov=True
    elif c.startswith('spectral_'):
        rs=['epsilon_nuisance','epsilon_signal']; rel=[]; ms=['optical.coefficient_applicability']; cov=c.endswith('_variance')
    elif c in ('observed_interference','corrected_estimate','corrected_estimate_variance'):
        rs=['epsilon_nuisance','epsilon_signal','nuisance']; rs=(['$signal']+rs) if c!='observed_interference' else rs
        rel=['attribution','systematic_coverage','$signal_validity','$signal_readout_isolation']; ms=['optical.coefficient_applicability','optical.raw_optical_relation','optical.estimate_scale_applicability','optical.nuisance_quantity_linkage']; cov=c.endswith('_variance')
    else:
        rs=['$signal','$anchor']+(['epsilon_nuisance','epsilon_signal'] if c=='required_nuisance_equivalent_scenario' else [])
        rel=pair+['protocol','functional_bearing','attribution','left_validity','right_validity','left_readout_isolation','right_readout_isolation']
        ms=['conversion.left','conversion.right','optical.raw_optical_relation','optical.scenario.common_rate_equality','optical.scenario.linear_mixture_on_estimate_scale']
        if c=='required_nuisance_equivalent_scenario':ms+=['optical.coefficient_applicability']
        cov=False
    mapping[c]={'maximum_roles':rs,'relationship_names':rel,'model_premises':ms,'uses_covariance':cov,
        'numeric_return':'exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix',
        'context_rule':'only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows',
        'dependency_rule':'actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence'}
save('PER_CELL_PROJECTION_MAP_001.json',mapping)

# Existing actual packages are read as engineering evidence. No paper is opened.
examples=[]
for case,selected in [('ORIGINAL_NFN',['protocol_ratio','protocol_difference','required_nuisance_equivalent_scenario','combined_estimate']),
    ('SYNTHETIC_COMMON',['combined_estimate','combined_variance']),
    ('SYNTHETIC_SINGULAR_KNOWN',['combined_estimate','combined_variance','weight_left']),
    ('SYNTHETIC_SINGULAR_PLUGIN',['combined_estimate','combined_variance','weight_left'])]:
    extraction=json.loads((PURE/(case+'_EXTRACTION_ACTUAL_010.json')).read_text())
    existing=json.loads((PURE/(case+'_SHEET_ACTUAL_010.json')).read_text())
    withheld=[]
    artifacts={(a['source_ref'],a['representation']):a['artifact_ref'] for a in extraction['source_artifacts']}
    def collect_numeric(value):
        if isinstance(value,dict):
            if {'witness','number_start','number_end'}<=value.keys():
                w=value['witness']; a,b=value['number_start'],value['number_end']
                loc={k:w[k] for k in ('source_ref','representation')}
                loc.update(artifact_ref=artifacts[(w['source_ref'],w['representation'])],
                    start=w['start']+len(w['quote'][:a].encode()),end=w['start']+len(w['quote'][:b].encode()))
                if loc not in withheld:withheld.append(loc)
            for child in value.values():collect_numeric(child)
        elif isinstance(value,list):
            for child in value:collect_numeric(child)
    collect_numeric(extraction)
    for b in extraction['covariance_blocks']:
        if b['raw_document_utf8']:
            withheld.append({'source_ref':b['source_ref'],'artifact_ref':b['artifact_ref'],'representation':'original',
                'start':0,'end':len(b['raw_document_utf8'].encode())})
    args={'version':'literature_measurement_comparison_population_v1','selection':deepcopy(extraction['selection']),
        'return_context':{r:{f:[] for f in fields} for r in roles}}
    args['selection']['requested_cells']=selected
    # Explicit example: request only distinct subject/endpoint labels, no numeric observations.
    for role,item in extraction['quantities'].items():
        if item is None:continue
        s=item['selection']
        for field in ['row_label','quantity_label',*['subject.'+k for k in qdef['subject']['properties']],
            'assay.direct_endpoint','assay.denominator','assay.fit_basis','assay.inferred_quantity']:
            w=s
            for k in field.split('.'):w=w.get(k) if isinstance(w,dict) else None
            if w and not any(loc['artifact_ref']==w.get('artifact_ref',next((a['artifact_ref'] for a in extraction['source_artifacts'] if a['source_ref']==w['source_ref'] and a['representation']==w['representation']),None))
                and w['start']<loc['end'] and loc['start']<w['end'] for q in extraction['quantities'].values() if q for loc in q['value']['source_locations']):
                args['return_context'][role][field]=[{'start':w['start'],'end':w['end']}]
        # Existing converted Nfn context: select narrow recorded protocol pieces;
        # this does not acquire source bytes or reinterpret experimental meaning.
        if case=='ORIGINAL_NFN' and role in ('left','right'):
            w=s['assay']['conditions']; quote=w['quote']
            marker='NAD\n+\nreduction with NADPH.' if role=='left' else 'Ferredoxin reduction with NADPH.'
            a=quote.index(marker);b=quote.index('The reaction was started',a)
            args['return_context'][role]['assay.conditions']=[
                {'start':w['start'],'end':w['start']+len(quote[:quote.index('TTC reduction with NADPH.')].encode())},
                {'start':w['start']+len(quote[:a].encode()),'end':w['start']+len(quote[:b].encode())}]
    Draft202012Validator(request).validate(args)
    save(case+'_REQUEST_EXAMPLE_001.json',args)
    selected_cells=[next(c for c in existing['cells'] if c['component']==name) for name in selected]
    # Cells are copied exactly, not recomputed or passed off as selected episode results.
    save(case+'_SAVED_CELL_EXCERPT_001.json',{'status':'existing_pure_output_not_selected_integration',
        'source':str((PURE/(case+'_SHEET_ACTUAL_010.json')).relative_to(ROOT)),'cells':selected_cells})
    proposed=[]
    for cell in selected_cells:
        name=cell['component']; spec=mapping[name]; optical=args['selection']['optical']
        signal='left' if optical is None else optical['signal_role']
        anchor=('right' if signal=='left' else 'left') if optical is None or optical['scenario'] is None else optical['scenario']['anchor_role']
        resolve=lambda v: v.replace('$signal',signal).replace('$anchor',anchor)
        needed=list(dict.fromkeys(resolve(r) for r in spec['maximum_roles']))
        if name=='observed_interference':needed.insert(0,signal)
        role_rows=[]; bindings=[]
        for r in needed:
            q=extraction['quantities'][r]
            if q is None:continue
            s=q['selection']; value=q['value']; meaning={k:deepcopy(value[k]) for k in
                ('role','estimator_scale','quantity_kind','semantics','normalization','origin','relation','approximate')}
            meaning.update(qualification=s['qualification']['value'],reported_uncertainty_statistic=q['reported_uncertainty']['statistic'],
                reported_uncertainty_meaning=q['reported_uncertainty']['meaning'],contexts=[])
            for f in fields:
                witness=s
                for k in f.split('.'):witness=witness.get(k) if isinstance(witness,dict) else None
                windows=args['return_context'][r][f]; fragments=[]
                for w in windows:
                    artifact=next(a['artifact_ref'] for a in extraction['source_artifacts'] if a['source_ref']==witness['source_ref'] and a['representation']==witness['representation'])
                    loc={k:witness[k] for k in ('source_ref','representation')};loc.update(artifact_ref=artifact,**w)
                    fragments.append({'text':witness['quote'].encode()[w['start']-witness['start']:w['end']-witness['start']].decode(),'location':loc})
                meaning['contexts'].append({'field':f,'status':'selected' if windows else 'source_unavailable' if witness is None else 'not_selected','fragments':fragments})
            role_rows.append(meaning)
            if r in cell['operand_roles']:
                binding={k:deepcopy(value[k]) for k in ('role','owner_key','physical_owner_key','dependency_keys','estimator_scale')}
                binding.update(unit=value['canonical_unit'],source_locations=[{k:v for k,v in loc.items() if k!='quote'} for loc in value['source_locations']]);bindings.append(binding)
        rnames=list(dict.fromkeys(resolve(r) for r in spec['relationship_names']))
        rels=[{'name':r,'value':existing['relationship_meanings'][r]} for r in rnames]
        conditions=[];conversions=[]
        for path in spec['model_premises']:
            if path.startswith('conversion.'):
                r=path.split('.')[1];v=args['selection']['common_quantity'][r+'_conversion']
                conversions.append({'role':r,'kind':v['kind'],'direction':v['direction']['value'],'support_status':v['support_status']['value']});continue
            value=args['selection']
            for k in path.split('.'):value=value.get(k) if isinstance(value,dict) else None
            conditions.append({'name':path,'state':'not_selected' if value is None else value['value']})
        common=args['selection']['common_model'] if 'common_model.applicability' in spec['model_premises'] else None
        opt_used=any(p.startswith('optical.') for p in spec['model_premises']);scenario_used=any(p.startswith('optical.scenario.') for p in spec['model_premises'])
        cov=[{k:deepcopy(b[k]) for k in ('source_ref','artifact_ref','basis','variance_status','origin','systematic_coverage','derivation','status')}
            for b in extraction['covariance_blocks'] if spec['uses_covariance'] and
                (b['source_ref'] in cell['uncertainty']['covariance_source_refs'] or b['status']=='unavailable' and any(b['reasons'][family] for family in b['reasons']))]
        deps=[deepcopy(d) for d in existing['dependence'] if set(d['roles'])<=set(needed)]
        assumptions=[a for a in existing['assumptions'] if a=='no_reference_distribution_assumed'
            or a=='common_unbiased_quantity_model' and common is not None
            or a=='estimated_weights_treated_as_plugin' and cell['uncertainty']['variance_status']=='estimated'
            or a=='fixed_reaction_conversion' and any(c['kind']=='fixed_reaction_scale' for c in conversions)
            or a in ('common_rate_equality_stipulated','linear_estimate_scale_mapping_stipulated') and scenario_used
            or a=='linear_mixture_on_selected_estimate_scale' and opt_used
            or a=='first_order_covariance_propagation' and cell['uncertainty']['scope']=='first_order_operand_propagation']
        proposed.append({'row_version':'measurement_comparison_return_v1','sheet_ref':'source_'+hashlib.sha256(('PLAN_ONLY_'+case).encode()).hexdigest(),
            'evidence_source_ref':args['selection']['source_ref'],'evaluation_scope':'source_measurement_comparison','component':name,
            'cell':deepcopy(cell),'source_kind':args['selection']['source_kind'],'assertion_question':args['selection']['assertion']['question'],
            'role_meanings':role_rows,'relationships':rels,'model_conditions':conditions,'conversion_conditions':conversions,'covariance_provenance':cov,
            'model_settings':{'common_variance_interpretation':'not_selected' if common is None else common['variance_interpretation'],
                'common_combination':'not_selected' if common is None else common['combination'],
                'optical_observation_equation':'y=h+s*alpha*f' if opt_used and optical is not None else None,
                'optical_signal_role':signal if opt_used and optical is not None else None,
                'optical_nuisance_sign':optical['nuisance_sign'] if opt_used and optical is not None else None,
                'scenario_anchor_role':anchor if scenario_used and optical is not None and optical['scenario'] is not None else None},
            'dependencies':bindings,'dependence':deps,'assumptions':assumptions,'withheld_locations':deepcopy(withheld)})
    Draft202012Validator(rows).validate(proposed)
    for row in proposed:
        assert row['cell']==next(c for c in existing['cells'] if c['component']==row['component'])
        for meaning in row['role_meanings']:
            for context in meaning['contexts']:
                for fragment in context['fragments']:
                    loc=fragment['location']
                    assert not any(loc['artifact_ref']==w['artifact_ref'] and loc['start']<w['end'] and w['start']<loc['end'] for w in withheld), (case,meaning['role'],context['field'])
    save(case+'_PROPOSED_TYPED_ROWS_001.json',{'status':'plan_only_no_selected_operation_or_admission',
        'sheet_ref_meaning':'schema-valid invented placeholder, no source record created','rows':proposed})
    examples.append({'case':case,'request':case+'_REQUEST_EXAMPLE_001.json','cells':case+'_SAVED_CELL_EXCERPT_001.json',
        'proposed_typed_rows':case+'_PROPOSED_TYPED_ROWS_001.json','status':'plan_only_not_selected_execution'})
save('EXAMPLES_INDEX_001.json',examples)
literal=obj({'comparison':deepcopy(rows),'limit':{'type':'string','enum':['quantitative_comparability_unresolved','conditional_scenario_only','declared_common_model']}})
alias=obj({'comparison':{'$ref':'episode-fact:literature_measurement_comparison_cells'},'limit':deepcopy(literal['properties']['limit'])})
save('LITERAL_PARENT_FORM_001.json',literal)
save('ALIAS_PARENT_FORM_001.json',alias)
example_args=json.loads((OUT/'ORIGINAL_NFN_REQUEST_EXAMPLE_001.json').read_text())
profile={'profile':'operation_contract_information_v1','decision_protocol':'decision_exchange_v1',
    'explicit_lookup':{'response':{'response_type':'request_context','lookup':{'view':'composition_information','operation':'episode.operation_contract',
        'arguments':{'operation':'literature.measurement_comparison.populate'}}}},
    'explicit_return_lookup':{'response':{'response_type':'request_context','lookup':{'view':'composition_information','operation':'episode.return_contract',
        'arguments':{'role':'literature','source':'literature_measurement_comparison_cells'}}}},
    'tool_selection':{'kind':'tool','tool':'literature.measurement_comparison.populate','arguments':json.dumps(example_args,separators=(',',':'))},
    'note':'Selection object before ordinary decision-exchange envelope. arguments is a JSON string only under this explicit existing transport profile.'}
save('PROFILE_TRANSPORT_EXAMPLE_001.json',profile)
checks={'status':'proposal_schema_checks_only','production_or_tests_changed':False,'selected_execution':False,
    'source_io':False,'science_validators_or_calculators':False,'model_run':False,
    'schemas_checked':[],'request_examples_validated':len(examples),'proposed_typed_row_packages_validated':len(examples),
    'typed_cells_equal_saved_pure_cells':True,'context_fragments_do_not_overlap_withheld_numeric_locations':True,
    'typed_row_package_scope':'proposal packaging of copied pure cells; sheet_ref placeholders do not name created records'}
for name in ['POPULATION_REQUEST_SCHEMA_001.json','TYPED_RETURN_SCHEMA_001.json','LITERAL_PARENT_FORM_001.json','ALIAS_PARENT_FORM_001.json']:
    Draft202012Validator.check_schema(json.loads((OUT/name).read_text()));checks['schemas_checked'].append(name)
save('PLAN_ARTIFACT_CHECK_001.json',checks)
