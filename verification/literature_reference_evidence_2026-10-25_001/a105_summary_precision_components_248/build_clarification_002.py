"""Additive review artifacts, existing-reader exercises, no new production code."""
from pathlib import Path
from copy import deepcopy as dc
from fractions import Fraction
import hashlib,json,math
import jsonschema
from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs,_UNIT_TABLES,_normalize
H=Path(__file__).resolve().parent
NEW='reported_sd_summarizes_counted_preparation_estimates'
OLDLIMIT='pNPP_repeatability_not_physiological_specificity'
NEWLIMIT='measurement_repeatability_does_not_establish_physiological_specificity'

def load(name):return json.loads((H/name).read_text())
def save(name,value):(H/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def rat(value):
    if value is None:return None
    f=Fraction(value);return {'numerator':str(f.numerator),'denominator':str(f.denominator)}
def patch_schema(node):
    if isinstance(node,list):
        return [NEWLIMIT if v==OLDLIMIT else patch_schema(v) for v in node]
    if not isinstance(node,dict):return node
    result={k:patch_schema(v) for k,v in node.items()}
    enums=result.get('enum')
    if enums and 'one_estimate_per_preparation' in enums and NEW not in enums:
        enums.insert(enums.index('one_estimate_per_preparation')+1,NEW)
    props=result.get('properties',{})
    if 'one_estimate_per_preparation' in props and NEW not in props:
        props[NEW]=dc(props['one_estimate_per_preparation'])
        result['required'].append(NEW)
    if props.get('version',{}).get('const')=='a105_kinetic_summary_precision_inputs_v1':
        props['sd_scale_exact']=dc(props['canonical_scale_exact'])
        props['sd_canonical_unit']=dc(props['canonical_unit'])
        props['sd_unit_basis']={'enum':['explicit_source_unit','inherited_parameter_unit','unavailable']}
        result['required'].extend(['sd_scale_exact','sd_canonical_unit','sd_unit_basis'])
        deps=props['dependencies']
        for k in ('parameter_unit_source','spread_unit_source'):
            deps['properties'][k]=dc(deps['properties']['spread_source'])
            deps['required'].append(k)
    if enums and 'statistical_estimator_count_unknown' in enums and 'sd_preparation_estimator_ownership_unknown' not in enums:
        enums.append('sd_preparation_estimator_ownership_unknown')
    return result

def json_patch(old,new,path=''):
    result=[]
    if type(old) is dict and type(new) is dict:
        for k in old.keys()-new.keys():result.append({'op':'remove','path':path+'/'+k})
        for k in new.keys()-old.keys():result.append({'op':'add','path':path+'/'+k,'value':dc(new[k])})
        for k in old.keys()&new.keys():result.extend(json_patch(old[k],new[k],path+'/'+k))
    elif old!=new:result.append({'op':'replace','path':path,'value':dc(new)})
    return result
schemas={}
deltas={}
for prefix in ('SELECTION','EXTRACTION','CALCULATION_INPUTS','SHEET'):
    original=load(prefix+'_SCHEMA_001.json')
    revised=patch_schema(original)
    jsonschema.Draft202012Validator.check_schema(revised)
    schemas[prefix]=revised
    save(prefix+'_SCHEMA_002.json',revised)
    deltas[prefix+'_SCHEMA_001.json']={'revised_file':prefix+'_SCHEMA_002.json','rfc6902_patch':json_patch(original,revised)}
save('SCHEMA_DELTAS_002.json',{'status':'prospective_preimplementation_schema_revision_not_runtime_migration','deltas':deltas,'semantic_checks_added':['physical roster mapping requires exact SD-estimator ownership','independent parameter and spread scales/locators/bases validated','no parameter-unit fallback from SD unit','mean variance/SE do not inherit missing central parameter failure','source_count_matches_sd assessment remains unknown when no separately selected count exists'],'unchanged_public_function_signatures':True,'unchanged_task':True})
actual=load('ACTUAL_SOURCE_SELECTION_PROPOSAL_001.json')
actual['interpretation'][NEW]={'state':'unknown','witnesses':[]}
actual['scenario']['stipulated_assumptions'].insert(1,NEW)
jsonschema.Draft202012Validator(schemas['SELECTION']).validate(actual)
save('ACTUAL_SOURCE_SELECTION_PROPOSAL_002.json',actual)

# Build exact proposed calculator inputs from the existing source reader's output.
def locator(w):return None if w is None else {k:w[k] for k in ('source_ref','artifact_ref','representation','start','end')}
def numberloc(number):
    if number is None:return None
    sel=number['selector'];w=sel['witness'];out=locator(w)
    out['start']+=len(w['quote'][:sel['number_start']].encode())
    out['end']=w['start']+len(w['quote'][:sel['number_end']].encode())
    return out

def inputs(extraction,interpretation,scenario=None):
    row=extraction['operands']['numerator'];unc=row['uncertainty'];op=row['calculation_operand']
    punit=row['unit'];sunit=unc['effective_unit']
    kind=row['parameter_kind']['value']
    def scale(unit):
        return (_UNIT_TABLES[kind].get(_normalize(unit['raw_unit']),[None,None])[1]
                if unit and unit['canonical_unit'] else None)
    pscale,sscale=scale(punit),scale(sunit)
    rel=unc['meanings']['unit_relationship']['value']
    out={'version':'a105_kinetic_summary_precision_inputs_v1','source_kind':extraction['source_kind'],'parameter_kind':kind,'source_origin':row['source_origin'],'source_parameter_status':op['status'] if op else 'missing','source_parameter_reason':op['unavailable_reason'] if op else 'source_measurement_unreported','parameter_approximate':row['approximate'],'parameter_native_exact':rat(row['number']['raw_number']) if row['number'] else None,'sd_native_exact':rat(unc['magnitude']['raw_number']) if unc['magnitude'] else None,'canonical_scale_exact':rat(pscale),'canonical_unit':punit['canonical_unit'] if punit else None,'sd_scale_exact':rat(sscale),'sd_canonical_unit':sunit['canonical_unit'] if sunit else None,'sd_unit_basis':('explicit_source_unit' if rel=='explicit_unit' else 'inherited_parameter_unit') if sscale is not None else 'unavailable','uncertainty_statistic':unc['canonical']['statistic'],'uncertainty_reason':unc['unavailable_reason'],'source_count':dc(unc['count']),'source_statistical_count':None,'source_count_meaning':interpretation['source_count_meaning']['value'],'repetition_basis':unc['canonical']['repetition_basis'],'estimate_basis':unc['canonical']['estimate_basis'],'assessments':{k:v['state'] for k,v in interpretation.items() if k not in ('source_count_meaning','statistical_count')},'scenario':dc(scenario),'interval_request':'none','dependencies':{'parameter_source':numberloc(row['number']),'spread_source':numberloc(unc['magnitude']),'count_source':numberloc(unc['count']),'statistical_count_source':None,'physical_measurement_id':op['physical_measurement_id'] if op else None,'parameter_unit_source':locator(punit['witness']) if punit else None,'spread_unit_source':locator(sunit['witness']) if sunit else None}}
    jsonschema.Draft202012Validator(schemas['CALCULATION_INPUTS']).validate(out)
    return out

actualinput=inputs(load('EXISTING_READER_REEXECUTION_001.json'),actual['interpretation'],actual['scenario'])
actualinput['interval_request']='student_t_95'
save('ACTUAL_SOURCE_CALCULATION_INPUT_PROPOSAL_002.json',actualinput)

# Synthetic source snippets exercise existing parser/units; not paper findings.
base=dc(actual['kinetic_selection'])
results=[]
for tag,center,punit,sunit,sd in [('missing_central_value',None,None,'s^-1','0.2'),('missing_parameter_unit','10',None,'s^-1','0.2'),('fully_units_known','10','s^-1','s^-1','0.2'),('both_units_missing','10',None,None,'0.2'),('different_native_time_units','10','s^-1','min^-1','12')]:
    text='Parameter kcat. Construct SYNTH-A.\n'
    text+=('Central estimate unavailable.\n' if center is None else f'Central estimate {center}'+(' '+punit if punit else '')+'.\n')
    text+=f'Reported SD {sd}'+(' '+sunit if sunit else '')+'.\n'
    text+='There are four independent preparations; the same four estimates are summarized by this SD.\n'
    text+='Each preparation supplies exactly one fitted kcat estimate, and this SD summarizes exactly those preparation estimates.\n'
    text+='SD uses the sample n-1 denominator. The estimates are IID with a common mean and finite variance.\n'
    text+='The central estimate, when available, is their equal-weight arithmetic mean.\n'
    raw=text.encode();sref='@synthetic248';aref='sha256_'+hashlib.sha256(raw).hexdigest()
    def w(quote):
        pos=text.index(quote);return {'source_ref':sref,'representation':'text','start':len(text[:pos].encode()),'end':len(text[:pos+len(quote)].encode()),'quote':quote}
    def numeric(full,token):
        start=full.index(token);return {'witness':w(full),'number_start':start,'number_end':start+len(token)}
    def meaning(value,quotes=()):return {'value':value,'witnesses':[w(q) for q in quotes]}
    k=dc(base);k['source_ref']=sref;k['source_kind']='synthetic_fixture'
    row=k['numerator']
    row['parameter_kind']=meaning('kcat',('Parameter kcat.',))
    row['subject']={f:None for f in row['subject']};row['subject']['construct']=w('SYNTH-A')
    row['context']={f:None for f in row['context']}
    row['measurement_identity']=None
    cfull=('Central estimate '+str(center)+(' '+punit if punit else '')+'.') if center is not None else None
    row['measurement']=None if center is None else {'number':numeric(cfull,center),'unit':w(punit) if punit else None}
    row['qualification']=meaning('unknown') if center is None else meaning('reported_point',(cfull,))
    sfull='Reported SD '+sd+(' '+sunit if sunit else '')+'.'
    u=row['uncertainty']
    u.update({'statistic':meaning('sd',('Reported SD',)),'magnitude':numeric(sfull,sd),'unit':w(sunit) if sunit else None,'unit_relationship':meaning('explicit_unit',(sfull,)) if sunit else meaning('same_as_parameter',(sfull,)),'count':numeric('There are four independent preparations; the same four estimates are summarized by this SD.','four'),'repetition_basis':meaning('biological_preparations',('four independent preparations',)),'estimate_basis':meaning('between_fitted_parameters',('Each preparation supplies exactly one fitted kcat estimate, and this SD summarizes exactly those preparation estimates.',))})
    def read_source(reference,representation):
        assert reference==sref and representation in ('original','text')
        return {'artifact_ref':aref,'content':raw}
    existing=read_kinetic_inputs(k,read_source=read_source)
    inter={key:{'state':'source_supported','witnesses':[w('Each preparation supplies exactly one fitted kcat estimate, and this SD summarizes exactly those preparation estimates.')]} for key in actual['interpretation'] if key not in ('source_count_meaning','statistical_count')}
    inter['statistical_count_matches_sd']={'state':'unknown','witnesses':[]}
    inter['normal_sampling_units']={'state':'unknown','witnesses':[]}
    inter['source_count_meaning']={'value':'both_same_count','witnesses':[w('There are four independent preparations; the same four estimates are summarized by this SD.')]}
    inter['statistical_count']=None
    selection={'version':'a105_kinetic_summary_precision_selection_v1','kinetic_selection':k,'interpretation':inter,'scenario':None,'interval_request':'none'}
    jsonschema.Draft202012Validator(schemas['SELECTION']).validate(selection)
    ci=inputs(existing,inter)
    # Expected proposed component arithmetic; this is not the unimplemented calculator.
    def frac(r):return Fraction(int(r['numerator']),int(r['denominator'])) if r else None
    xraw=frac(ci['parameter_native_exact']);xp=frac(ci['canonical_scale_exact']);sr=frac(ci['sd_native_exact']);sp=frac(ci['sd_scale_exact'])
    X=xraw*xp if xraw is not None and xp is not None else None
    S=sr*sp if sr is not None and sp is not None else None
    out={'reported_parameter':float(X) if X is not None else None,'reported_parameter_reason':ci['source_parameter_reason'],'reported_sd':float(S) if S is not None else None,'sd_unit':ci['sd_canonical_unit'],'mean_variance':float(S*S/4) if S is not None else None,'mean_standard_error':math.sqrt(float(S*S/4)) if S is not None else None,'precision_reason':None if S is not None else 'source_uncertainty_unit_unavailable','physical_preparation_count':4,'statistical_estimator_count':4,'relative_reported_sd':float(S/abs(X)) if S is not None and X is not None else None,'relative_mean_standard_error':math.sqrt(float(S*S/4))/float(abs(X)) if S is not None and X is not None else None,'relative_reason':ci['source_parameter_reason'] or (None if S is not None else 'source_uncertainty_unit_unavailable'),'total_uncertainty':None}
    if tag=='both_units_missing':assert out['reported_sd'] is None and out['statistical_estimator_count']==4
    else:assert out['reported_sd']==12 and out['mean_variance']==36 and out['mean_standard_error']==6
    if tag in ('missing_central_value','missing_parameter_unit'):
        assert ci['canonical_unit'] is None and ci['canonical_scale_exact'] is None and out['relative_reported_sd'] is None
    if tag in ('fully_units_known','different_native_time_units'):
        assert out['reported_parameter']==600 and out['relative_reported_sd']==.02 and out['relative_mean_standard_error']==.01
    save('SYNTHETIC_'+tag.upper()+'_SOURCE_002.json',{'source_kind':'synthetic_fixture','artifact_ref':aref,'text':text})
    save('SYNTHETIC_'+tag.upper()+'_EXISTING_READER_002.json',existing)
    results.append({'case':tag,'status':'existing_reader_actually_executed_new_calculator_output_proposed','selection':selection,'calculation_inputs':ci,'expected_component_subset':out})
save('SYNTHETIC_PARTIAL_IO_002.json',results)
# Explicit mapping scenarios. This checks declarative prerequisite design only.
casebase={'source_physical_n':2,'source_assessments':dc(actualinput['assessments']),'source_statistical_n':None}
oldstips=[a for a in actualinput['scenario']['stipulated_assumptions'] if a!=NEW]
save('ACTUAL_MAPPING_CASES_002.json',{'status':'proposed_prerequisite_examples_not_new_calculator_execution','source':casebase,'cases':[{'scenario_count_rule':'one_per_physical_preparation','stipulated_assumptions':oldstips,'expected_statistical_n':None,'expected_mean_se':None,'expected_reason':'sd_preparation_estimator_ownership_unknown'},{'scenario_count_rule':'one_per_physical_preparation','stipulated_assumptions':dc(actualinput['scenario']['stipulated_assumptions']),'expected_statistical_n':2,'expected_mean_variance_native':.005,'expected_mean_se_native':math.sqrt(.005),'expected_statistical_count_matches_sd_assessment':'unknown','expected_new_sd_roster_assessment':'unknown','expected_qualification':'conditional_on_stipulated_assumptions'}]})
# Verify frozen001 files and exact TASK; do not rewrite manifest001.
frozen=load('PLAN_MANIFEST_001.json')
for r in frozen['files']:
    assert hashlib.sha256((H/r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
assert (H/'TASK_PROPOSAL_001.txt').read_bytes()==(H.parent/'a105_independent_preparation_review_246/SUMMARY_PRECISION_TASK_PROPOSAL_004.txt').read_bytes()
save('CLARIFICATION_CHECKS_002.json',{'status':'passed','frozen001_files_unchanged':len(frozen['files']),'schemas_checked':4,'actual_selection_and_calculator_input_valid_in002_schemas':True,'synthetic_existing_reader_cases_executed':len(results),'synthetic_proposed_input_schemas_valid':len(results),'expected_basic_arithmetic_checked':True,'scenario_mapping_output_is_proposed':True,'new_production_calculator_executed':False,'production_or_test_files_changed':False,'task_changed':False,'new_paper_opened':False,'provider_model_called':False,'all_owned_processes_terminal':True})
# Additive manifest includes only002 files and points to preserved001.
records=[]
for p in sorted(H.glob('*002*')):
    if p.is_file() and p.name!='CLARIFICATION_MANIFEST_002.json':
        raw=p.read_bytes();records.append({'path':p.name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
save('CLARIFICATION_MANIFEST_002.json',{'status':'frozen_additive_plan_clarification_awaiting_root_review','production_release':False,'preserves001_manifest_sha256':hashlib.sha256((H/'PLAN_MANIFEST_001.json').read_bytes()).hexdigest(),'files':records,'manifest_excludes_itself':True})
print('Validated four revised schemas, actual selection/input, five existing-reader synthetic partial cases, frozen001 bytes and unchanged TASK. PLAN ONLY.')
