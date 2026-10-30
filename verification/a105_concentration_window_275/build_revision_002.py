"""Additive interface-revision artifacts and contract-oracle checks only.

No production reader/calculator, primary-source reading or new case is added.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('base275',HERE/'build_proposal_001.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
D=deepcopy(B.D)
obj,arr,enum,ref,nullable=B.obj,B.arr,B.enum,B.ref,B.nullable
TEXT,HEX=B.TEXT,B.HEX
ANALYTES=('substrate','total_product','fate_product')


def meaning(*values): return obj(value=enum(*values),witnesses=arr(ref('field')))


D['pair_relationships']=obj(**{name:obj(
    endpoint_comparability=meaning('same_series_supported','separately_measured_compatible','incompatible','unknown','conflicting'),
    selected_window=ref('relationship'),concentration_basis=ref('relationship'),
    physical_pairing=meaning('same_reaction_supported','paired_reactions_supported','separate_reactions_supported','unknown','conflicting'))
    for name in ANALYTES})
D['cross_relationships']=obj(**{name:obj(
    window_compatibility=ref('relationship'),concentration_basis=ref('relationship'),
    calibration_compatibility=ref('relationship'),
    endpoint_account=meaning('same_reaction_account_supported','compatible_separate_accounts_supported','incompatible','unknown','conflicting'),
    physical_pairing=meaning('same_reaction_supported','paired_reactions_supported','separate_reactions_supported','unknown','conflicting'))
    for name in ('chemical','fate')})
props=D['selection']['properties']
del props['relationships']
props.update(pair_relationships=ref('pair_relationships'),cross_relationships=ref('cross_relationships'))
D['selection']['required']=list(props)
D['selection']['properties']['version']={'const':'a105_concentration_window_selection_v2'}

# Retained scientific support has exact selectors/locations, with numerical
# observations omitted from display text. Full original quotations remain in
# EXTRACTION.selection, where they are host custody, not returned components.
D['field_binding']={'oneOf':[]}
for name in ('text_field','xlsx_field'):
    s=deepcopy(D[name]);del s['properties']['quote'];s['required'].remove('quote')
    D['field_binding']['oneOf'].append(s)
D['scientific_field']=obj(status=enum('retained','not_selected'),
    scientific_text=nullable(TEXT),display_status=enum('semantic_context','support_location_only','not_selected'),
    binding=nullable(ref('field_binding')),artifact_ref=nullable(TEXT),source_sha256=nullable(HEX))


def retained_meaning(source_schema):
    result=deepcopy(source_schema)
    result['properties']['witnesses']=arr(ref('scientific_field'))
    return result


D['scientific_assay']=deepcopy(D['assay'])
for k in D['scientific_assay']['properties']:
    if k not in ('arrangement','participants'):
        D['scientific_assay']['properties'][k]=ref('scientific_field')
D['scientific_assay']['properties']['arrangement']=retained_meaning(D['assay']['properties']['arrangement'])
D['scientific_assay']['properties']['participants']['items']['properties']['identity']=ref('scientific_field')
D['scientific_quantity']=obj(selection_status=enum('selected','not_selected'),
    **{k:ref('scientific_field') for k in ('analyte','coordinate','unit','record','measurement_identity')},
    **{k:retained_meaning(D['quantity']['properties'][k])
       for k in ('reading_meaning','concentration_basis','unit_association')},
    uncertainty=arr(ref('scientific_field')))
D['scientific_coefficient']=obj(selection_status=enum('selected','not_selected'),
    kind=enum('implicit_unit_coefficient','explicit_source_token',None),
    value=B.NUMBER_NULL,exact_value=nullable(ref('exact')),
    origin=enum('implicit_chemical_notation','reported','synthetic','unavailable'),
    relationship=retained_meaning(D['relationship']),reaction=ref('scientific_field'),
    coefficient_token_support=ref('scientific_field'),
    analyte=ref('scientific_field'),operand_roles=arr(enum(*B.ROLES),True),
    coefficient_meaning={'const':'moles_of_selected_analyte_per_reaction_equivalent'},
    conversion_direction={'const':'selected_concentration_change_divided_by_coefficient'},
    dependency_keys=arr(TEXT,True),reasons=ref('reasons'))


def retained_relations(definition):
    result=deepcopy(definition)
    for group in result['properties'].values():
        for key,value in group['properties'].items():
            group['properties'][key]=retained_meaning(D['relationship'] if value==ref('relationship') else value)
    return result


D['scientific_pair_relationships']=retained_relations(D['pair_relationships'])
D['scientific_cross_relationships']=retained_relations(D['cross_relationships'])
D['scientific_timing']=deepcopy(D['timing'])
D['scientific_timing']['properties']['source_meaning']=retained_meaning(D['timing']['properties']['source_meaning'])
D['scientific_context']=obj(usage={'const':'host_scientific_context_requires_scoped_parent_projection'},
    assay=ref('scientific_assay'),quantities=obj(**{r:ref('scientific_quantity') for r in B.ROLES}),
    stoichiometry=obj(**{a:ref('scientific_coefficient') for a in ANALYTES}),
    pair_relationships=ref('scientific_pair_relationships'),cross_relationships=ref('scientific_cross_relationships'),
    timing=ref('scientific_timing'))
D['association']=obj(selection_digest=HEX,extraction_digest=HEX,calculation_inputs_digest=nullable(HEX))

ep=D['extraction']['properties'];ep['version']={'const':'a105_concentration_window_extraction_v2'}
ep.update(selection_digest=HEX,scientific_context=ref('scientific_context'))
D['extraction']['required']=list(ep)
ip=D['calculation_inputs']['properties'];ip['version']={'const':'a105_concentration_window_calculation_inputs_v2'}
for key in ('context','relationships','timing'):del ip[key]
ip.update(selection_digest=HEX,scientific_context=ref('scientific_context'))
D['calculation_inputs']['required']=list(ip)
sp=D['sheet']['properties'];sp['version']={'const':'a105_concentration_window_sheet_v2'}
for key in ('relationship_meanings','source_timing_meaning'):del sp[key]
sp.update(scientific_context=ref('scientific_context'),association=ref('association'))
D['sheet']['required']=list(sp)
for family in ('pair_endpoint_comparability','pair_selected_window','pair_concentration_basis',
               'cross_window_compatibility','cross_concentration_basis','cross_calibration_compatibility','cross_endpoint_account'):
    D['reasons']['properties']['relationship']['items']['enum'].extend(family+'_'+status for status in ('unknown','conflicting','incompatible'))
D['cell']['properties'].update(interpretation_scope=enum('native_observation','descriptive_change','physical_window_change',
    'descriptive_cross_readout_comparison','physical_reaction_account','conditional_timing_sensitivity',
    'uncertainty_of_declared_estimates','unavailable'))
D['cell']['required']=list(D['cell']['properties'])


def resource(name):
    needed=set()
    def visit(v):
        if isinstance(v,dict):
            k=v.get('$ref','').removeprefix('#/$defs/')
            if k and k not in needed:needed.add(k);visit(D[k])
            for x in v.values():visit(x)
        elif isinstance(v,list):
            for x in v:visit(x)
    body=deepcopy(D[name]);visit(body)
    return {'$schema':'https://json-schema.org/draft/2020-12/schema',
            '$id':'urn:a105:concentration-window:275:proposal002:'+name,**body,
            '$defs':{k:deepcopy(D[k]) for k in sorted(needed)}}


def load(name):return json.loads((HERE/name).read_text())
def write(name,v):(HERE/name).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def m(v,*w):return dict(value=v,witnesses=list(w))


# All source fields/values come exclusively from the already frozen001 packet.
old_selection=load('SOURCE_SELECTION_PROPOSAL_001.json')
old_extraction=load('SOURCE_EXTRACTION_PROPOSAL_001.json')
old_inputs=load('SOURCE_CALCULATION_INPUTS_PROPOSAL_001.json')
old_sheet=load('SOURCE_SHEET_PROPOSAL_001.json')
artifacts={(a['source_ref'],a['representation']):a for a in old_extraction['source_artifacts']}
old_support=old_selection['relationships']['same_series']['witnesses']
selection=deepcopy(old_selection);selection['version']='a105_concentration_window_selection_v2';del selection['relationships']
selection['pair_relationships']={a:dict(endpoint_comparability=m('same_series_supported',*old_support),
    selected_window=m('supported',*old_support),concentration_basis=m('supported',*old_support),
    physical_pairing=m('same_reaction_supported',*old_support)) for a in ANALYTES}
selection['cross_relationships']={a:dict(window_compatibility=m('supported',*old_support),
    concentration_basis=m('supported',*old_support),calibration_compatibility=m('supported',*old_support),
    endpoint_account=m('same_reaction_account_supported',*old_support),
    physical_pairing=m('same_reaction_supported',*old_support)) for a in ('chemical','fate')}


def sf(field,*,support_only=False):
    if field is None:
        return dict(status='not_selected',scientific_text=None,display_status='not_selected',binding=None,artifact_ref=None,source_sha256=None)
    a=artifacts[field['source_ref'],field['representation']]
    return dict(status='retained',scientific_text=None if support_only else field['quote'],
        display_status='support_location_only' if support_only else 'semantic_context',
        binding={k:v for k,v in field.items() if k!='quote'},artifact_ref=a['artifact_ref'],source_sha256=a['sha256'])


def rm(value):return dict(value=value['value'],witnesses=[sf(w,support_only=True) for w in value['witnesses']])


def scientific_context(s,coefficients):
    assay={k:sf(v) for k,v in s['assay'].items() if k not in ('arrangement','participants')}
    assay.update(arrangement=rm(s['assay']['arrangement']),participants=[{**v,'identity':sf(v['identity'])} for v in s['assay']['participants']])
    quantities={}
    for role,q in s['quantities'].items():
        fields={k:sf(q[k] if q else None,support_only=k in ('coordinate','record','measurement_identity'))
                for k in ('analyte','coordinate','unit','record','measurement_identity')}
        quantities[role]=dict(selection_status='selected' if q else 'not_selected',**fields,
            **{k:rm(q[k]) if q else m('unknown') for k in ('reading_meaning','concentration_basis','unit_association')},
            uncertainty=[sf(w,support_only=True) for w in q['uncertainty']] if q else [])
    stoich={}
    for name,model in s['stoichiometry'].items():
        reading=coefficients[name]
        stoich[name]=dict(selection_status='selected' if model else 'not_selected',kind=model['kind'] if model else None,
            **{k:deepcopy(reading[k]) for k in ('value','exact_value','origin','dependency_keys','reasons')},
            relationship=rm(model['relationship']) if model else m('unknown'),
            reaction=sf(model['reaction'] if model else None,support_only=True),
            coefficient_token_support=sf(model['number']['field'] if model and model['number'] else None,support_only=True),
            analyte=sf(s['quantities'][name+'_start']['analyte'] if s['quantities'][name+'_start'] else None),
            operand_roles=[name+'_start',name+'_end'],
            coefficient_meaning='moles_of_selected_analyte_per_reaction_equivalent',
            conversion_direction='selected_concentration_change_divided_by_coefficient')
    return dict(usage='host_scientific_context_requires_scoped_parent_projection',assay=assay,quantities=quantities,
        stoichiometry=stoich,pair_relationships={a:{k:rm(v) for k,v in p.items()} for a,p in s['pair_relationships'].items()},
        cross_relationships={a:{k:rm(v) for k,v in p.items()} for a,p in s['cross_relationships'].items()},
        timing=dict(source_meaning=rm(s['timing']['source_meaning']),scenario=deepcopy(s['timing']['scenario'])))


def make_extraction(s):
    e=deepcopy(old_extraction);e.update(version='a105_concentration_window_extraction_v2',selection=deepcopy(s),
        selection_digest=B.digest(s),scientific_context=scientific_context(s,e['coefficients']))
    return e


def make_inputs(e):
    i=deepcopy(old_inputs)
    for k in ('context','relationships','timing'):del i[k]
    i.update(version='a105_concentration_window_calculation_inputs_v2',extraction_digest=B.digest(e),
        selection_digest=e['selection_digest'],scientific_context=deepcopy(e['scientific_context']),
        requested_cells=deepcopy(e['selection']['requested_cells']))
    return i


def make_sheet(i):
    s=deepcopy(old_sheet)
    for k in ('relationship_meanings','source_timing_meaning'):del s[k]
    s.update(version='a105_concentration_window_sheet_v2',scientific_context=deepcopy(i['scientific_context']),
        association=dict(selection_digest=i['selection_digest'],extraction_digest=i['extraction_digest'],calculation_inputs_digest=B.digest(i)))
    rows={r['component']:r for r in s['cells']}
    s['cells']=[rows[name] for name in i['requested_cells']]
    for row in s['cells']:
        n=row['component']
        row['interpretation_scope']=('unavailable' if row['status']=='unavailable' else
            'conditional_timing_sensitivity' if row['status']=='conditional_scenario' else
            'native_observation' if n in B.ROLES else
            'physical_reaction_account' if n.startswith('chemical_') or n=='fate_fraction' else 'physical_window_change')
        if n=='coordinate_span':row['interpretation_scope']='descriptive_change'
    return s


extraction=make_extraction(selection);inputs=make_inputs(extraction);sheet=make_sheet(inputs)

# Exactly the requested partial contrast: source numerical observations unchanged;
# product start/end comparability is unknown while substrate pairing stays known.
partial_selection=deepcopy(selection)
partial_selection['requested_cells']=['substrate_loss','total_product_gain','fate_product_gain','chemical_ratio','fate_fraction','coordinate_span']
partial_selection['pair_relationships']['total_product']['endpoint_comparability']=m('unknown')
partial_selection['pair_relationships']['total_product']['physical_pairing']=m('unknown')
partial_extraction=make_extraction(partial_selection);partial_inputs=make_inputs(partial_extraction)
partial_sheet=make_sheet(partial_inputs)
for row in partial_sheet['cells']:
    if row['component'] in ('total_product_gain','chemical_ratio','fate_fraction'):
        row.update(value=None,exact_value=None,conditional_value=None,conditional_exact_value=None,
                   status='unavailable',interpretation_scope='unavailable')
        row['reasons']['relationship']=['pair_endpoint_comparability_unknown']


# Review-only equality checks specify mandatory production validation behavior.
# They do not stand in for source parsing or general scientific arithmetic.
def check_extraction(e,*,original_selection):
    assert e['selection']==original_selection,'original_selection_mismatch'
    assert e['selection_digest']==B.digest(original_selection),'selection_digest_mismatch'
    assert e['scientific_context']==scientific_context(original_selection,e['coefficients']),'scientific_context_mismatch'
    assert e['quantities']==old_extraction['quantities'],'retained_scalar_or_source_binding_mismatch'
    assert e['source_artifacts']==old_extraction['source_artifacts'],'source_artifact_mismatch'
    assert e['coefficients']==old_extraction['coefficients'],'stoichiometric_value_or_dependency_mismatch'


def check_inputs(i,*,original_extraction):
    assert i==make_inputs(original_extraction),'calculation_inputs_upstream_mismatch'


def check_sheet(s,*,original_inputs,expected_sheet):
    assert s['scientific_context']==original_inputs['scientific_context'],'sheet_scientific_context_mismatch'
    assert s['association']==dict(selection_digest=original_inputs['selection_digest'],
        extraction_digest=original_inputs['extraction_digest'],calculation_inputs_digest=B.digest(original_inputs)),'sheet_upstream_association_mismatch'
    assert s==expected_sheet,'sheet_scope_or_value_mismatch'


if __name__=='__main__':
    schemas={name.upper():resource(name) for name in ('selection','extraction','calculation_inputs','sheet','covariance_document')}
    for s in schemas.values():Draft202012Validator.check_schema(s)
    write('SCHEMAS_002.json',schemas)
    for prefix,values in (('SOURCE',(selection,extraction,inputs,sheet)),('PARTIAL_CONTRAST',(partial_selection,partial_extraction,partial_inputs,partial_sheet))):
        for kind,value in zip(('SELECTION','EXTRACTION','CALCULATION_INPUTS','SHEET'),values):
            Draft202012Validator(schemas[kind]).validate(value)
            write(prefix+'_'+kind+'_PROPOSAL_002.json',value)
    check_extraction(extraction,original_selection=selection);check_inputs(inputs,original_extraction=extraction)
    check_sheet(sheet,original_inputs=inputs,expected_sheet=sheet)
    check_extraction(partial_extraction,original_selection=partial_selection)
    check_inputs(partial_inputs,original_extraction=partial_extraction)
    check_sheet(partial_sheet,original_inputs=partial_inputs,expected_sheet=partial_sheet)
    assert next(r for r in partial_sheet['cells'] if r['component']=='substrate_loss')['exact_value']=={'numerator':'100','denominator':'1'}
    assert all(r['status']=='unavailable' for r in partial_sheet['cells'] if r['component'] in ('total_product_gain','chemical_ratio','fate_fraction'))
    rejected=[]
    mutations=[('extraction_subject',extraction,lambda x:x['scientific_context']['assay']['molecule'].update(scientific_text='different subject'),lambda x:check_extraction(x,original_selection=selection)),
        ('extraction_quantity_basis',extraction,lambda x:x['scientific_context']['quantities']['substrate_start']['concentration_basis'].update(value='quenched_sample_concentration'),lambda x:check_extraction(x,original_selection=selection)),
        ('extraction_source_binding',extraction,lambda x:x['quantities']['substrate_start']['locations'][0].update(cell='B2'),lambda x:check_extraction(x,original_selection=selection)),
        ('extraction_selected_pair',extraction,lambda x:x['selection']['pair_relationships']['substrate']['endpoint_comparability'].update(value='unknown'),lambda x:check_extraction(x,original_selection=selection)),
        ('input_context_analyte',inputs,lambda x:x['scientific_context']['quantities']['substrate_start']['analyte'].update(scientific_text='wrong analyte'),lambda x:check_inputs(x,original_extraction=extraction)),
        ('input_model_value',inputs,lambda x:x['scientific_context']['stoichiometry']['total_product'].update(value=2),lambda x:check_inputs(x,original_extraction=extraction)),
        ('input_relationship_support',inputs,lambda x:x['scientific_context']['pair_relationships']['substrate']['selected_window'].update(witnesses=[]),lambda x:check_inputs(x,original_extraction=extraction)),
        ('input_digest_only',inputs,lambda x:x.update(extraction_digest='0'*64),lambda x:check_inputs(x,original_extraction=extraction)),
        ('sheet_condition',sheet,lambda x:x['scientific_context']['assay']['conditions'].update(scientific_text='different conditions'),lambda x:check_sheet(x,original_inputs=inputs,expected_sheet=sheet)),
        ('sheet_model_support',sheet,lambda x:x['scientific_context']['stoichiometry']['total_product']['reaction']['binding'].update(start=0),lambda x:check_sheet(x,original_inputs=inputs,expected_sheet=sheet)),
        ('sheet_unrequested_native',partial_sheet,lambda x:x['cells'].append(deepcopy(old_sheet['cells'][0])),lambda x:check_sheet(x,original_inputs=partial_inputs,expected_sheet=partial_sheet)),
        ('sheet_partial_promoted',partial_sheet,lambda x:next(r for r in x['cells'] if r['component']=='chemical_ratio').update(value=1.0,status='populated'),lambda x:check_sheet(x,original_inputs=partial_inputs,expected_sheet=partial_sheet))]
    for name,value,mutate,validate in mutations:
        changed=deepcopy(value);mutate(changed)
        try:validate(changed)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('undetected mutation: '+name)
    write('REVISION_CHECKS_002.json',dict(status='review_oracle_checks_not_production_validation',valid_schemas=5,
        valid_instances=8,authoritative_association_mutations_rejected=rejected,
        partial_contrast='known substrate delta retained; unknown total-product pairing blocks only its dependents',
        primary_sources_read=False,production_functions_run=False,shared_files_changed=False))
    print(json.dumps(dict(status='revision002_artifacts_created',schemas=5,instances=8,association_mutations_rejected=len(rejected))))
