"""Construct review schemas/examples only; never imports proposed production code."""
from pathlib import Path
from copy import deepcopy as dc
from fractions import Fraction
import hashlib
import json
import math
import importlib.metadata
from scipy.stats import t
from gene_annotation_episode.literature_kinetic_inputs import kinetic_arguments_schema, read_kinetic_inputs, _UNIT_TABLES, _normalize
from gene_annotation_episode.literature_assay_inputs import _witness_schema

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
REVIEW=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_independent_preparation_review_246'
PACKET=ROOT/'research/experimental_scoring_review_2026-10-23/a105_independent_preparation_case_242'

def write(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def obj(fields):
    return {'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}
def enum(*values): return {'enum':list(values)}
def nullable(s): return {'anyOf':[dc(s),{'type':'null'}]}
def arr(s,unique=False):
    v={'type':'array','items':dc(s)}
    if unique:v['uniqueItems']=True
    return v
S={'type':'string','minLength':1}
N={'type':'number'}
I={'type':'integer','minimum':0}
B={'type':'boolean'}
REF={'type':'string','format':'reference'}
W=_witness_schema()
AW=obj({**dc(W['properties']),'artifact_ref':dc(S)})
LOC=obj({name:dc(AW['properties'][name]) for name in ('source_ref','artifact_ref','representation','start','end')})
NS=obj({'witness':dc(W),'number_start':dc(I),'number_end':{'type':'integer','minimum':1}})
ANS=obj({**dc(NS['properties']),'witness':dc(AW)})
ASTATES=('source_supported','source_contradicted','unknown','conflicting')
ACODES=('one_estimate_per_preparation','equal_weight_arithmetic_mean','sample_sd_n_minus_one','iid_common_mean_finite_variance','normal_sampling_units')
AFIELDS=('row_footnote_applicability','statistical_count_matches_sd',*ACODES)
CM=('physical_preparation_count','statistical_estimator_count','both_same_count','technical_measurement_count','unknown','conflicting')
def assessment(w):return obj({'state':enum(*ASTATES),'witnesses':arr(w)})
def cm(w):return obj({'value':enum(*CM),'witnesses':arr(w)})
SCEN=obj({'version':{'const':'a105_summary_precision_scenario_v1'},'count_rule':enum('source_statistical_count','one_per_physical_preparation'),'stipulated_assumptions':arr(enum(*ACODES),True)})
INTER=obj({'row_footnote_applicability':assessment(W),'source_count_meaning':cm(W),'statistical_count':nullable(NS),**{k:assessment(W) for k in AFIELDS if k!='row_footnote_applicability'}})
KS=kinetic_arguments_schema()
KS['properties']['denominator']={'type':'null'}
# All selected comparison meanings have no comparison in this one-summary route.
for field, schema in KS['properties']['comparison']['properties'].items():
    schema['properties']['value']={'const':'unknown'}
    schema['properties']['witnesses']['maxItems']=0
KS['properties']['numerator']=KS['properties']['numerator']['anyOf'][0]
SEL=obj({'version':{'const':'a105_kinetic_summary_precision_selection_v1'},'kinetic_selection':KS,'interpretation':INTER,'scenario':nullable(SCEN),'interval_request':enum('none','student_t_95')})
COUNT=obj({'selector':ANS,'raw_number':S,'value':nullable({'type':'integer'}),'notation':enum('decimal_digits','english_cardinal','unsupported'),'relation':enum('point','lt','le','gt','ge','unresolved'),'approximate':nullable(B),'status':enum('exact','qualified','range_or_alternatives','unsupported','not_positive'),'unavailable_reason':nullable(enum('exact_count_qualified','count_range_or_alternatives','unsupported_count_literal','positive_count_required'))})
RAT=obj({'numerator':{'type':'string','pattern':'^(0|-?[1-9][0-9]*)$'},'denominator':{'type':'string','pattern':'^[1-9][0-9]*$'}})
CANUNIT=enum('uM','per_min','uM^-1min^-1')
PREASONS=('source_measurement_unreported','source_kinetic_unit_unreported','unsupported_source_kinetic_unit','source_operand_qualification_unknown','source_operand_qualification_conflicting','source_numeric_range')
INPUT=obj({'version':{'const':'a105_kinetic_summary_precision_inputs_v1'},'source_kind':enum('primary_source','synthetic_fixture'),'parameter_kind':enum('Km','kcat','catalytic_efficiency','unknown','conflicting'),'source_origin':enum('reported','synthetic'),'source_parameter_status':enum('point','censored','missing','conflicting'),'source_parameter_reason':nullable(enum(*PREASONS)),'parameter_approximate':B,'parameter_native_exact':nullable(RAT),'sd_native_exact':nullable(RAT),'canonical_scale_exact':nullable(RAT),'canonical_unit':nullable(CANUNIT),'uncertainty_statistic':enum('sd','sem','ci','unspecified','unreported'),'uncertainty_reason':nullable(enum('source_uncertainty_unit_unavailable','source_numeric_range')),'source_count':nullable(COUNT),'source_statistical_count':nullable(COUNT),'source_count_meaning':enum(*CM),'repetition_basis':enum('biological_preparations','technical_measurements','unspecified'),'estimate_basis':enum('fit_to_averaged_curve','between_fitted_parameters','unknown'),'assessments':obj({k:enum(*ASTATES) for k in AFIELDS}),'scenario':nullable(SCEN),'interval_request':enum('none','student_t_95'),'dependencies':obj({**{k:nullable(LOC) for k in ('parameter_source','spread_source','count_source','statistical_count_source')},'physical_measurement_id':nullable(S)})})
COMP=('reported_parameter','reported_sd','source_summary_count','independent_preparation_count','statistical_estimator_count','relative_reported_sd','mean_variance','mean_standard_error','relative_mean_standard_error','mean_interval_df','mean_interval_confidence_level','mean_interval_t_multiplier','mean_interval_halfwidth','mean_interval_lower','mean_interval_upper')
REASONS=tuple(dict.fromkeys((*PREASONS,'source_uncertainty_unit_unavailable','censored_parameter','conflicting_parameter','reported_sd_unreported','reported_statistic_not_sd','source_summary_count_unreported','source_count_not_exact','row_footnote_applicability_unknown','row_footnote_applicability_conflicting','row_footnote_applicability_contradicted','physical_preparation_count_unknown','statistical_estimator_count_unknown','statistical_count_conflicting','statistical_count_sd_relationship_unknown','insufficient_estimator_count','sample_sd_convention_unknown','iid_model_unknown','mean_identity_unknown','normality_unknown','source_condition_contradicted','source_condition_conflicting','zero_parameter_for_relative_precision','interval_not_requested','positive_sd_required_for_student_t','scenario_assumption_conflicts_with_source','numerical_model_range')))
LIMITS=('source_summaries_do_not_reconstruct_raw_measurements','physical_count_does_not_define_statistical_count','source_conditions_and_stipulations_distinct','random_precision_does_not_include_unknown_systematics','shared_calibration_does_not_shrink_with_preparation_count','dependent_precision_representations_not_independent_assays','pNPP_repeatability_not_physiological_specificity','no_cross_construct_contrast','no_assay_error_probability','no_target_transfer_or_annotation_credit')
CELL=obj({'value':nullable(N),'unit':nullable(enum('uM','per_min','uM^-1min^-1','uM_squared','per_min_squared','uM_inverse_squared_min_inverse_squared','dimensionless','count')),'status':enum('populated','unavailable'),'qualification':enum('source_reported','derived_source_supported_conditions','conditional_on_stipulated_assumptions','unavailable'),'formula_code':enum(*('summary_precision_'+c for c in COMP)),'origin':enum('reported','derived','proposed','synthetic'),'approximate':B,'source_exact_value':nullable(RAT),'conditional_on':arr(enum(*ACODES),True),'stipulated_assumptions':arr(enum(*ACODES),True),'unavailable_reason':nullable(enum(*REASONS))})
CELLS=obj({c:dc(CELL) for c in COMP})
SHEET=obj({'version':{'const':'a105_kinetic_summary_precision_sheet_v1'},'axis':{'const':'A105'},'evaluation_scope':{'const':'source_kinetic_summary_precision'},'inputs':INPUT,'source_cells':CELLS,'scenario_cells':nullable(CELLS),'contribution':obj({'kind':{'const':'one_summary_precision_contribution'},'dependency_sources':arr(LOC,True),'physical_measurement_id':nullable(S),'independence_inferred':{'const':False}}),'limits':arr(enum(*LIMITS),True),'total_uncertainty':{'type':'null'},'assay_error_probability':{'type':'null'},'annotation_credit':{'type':'null'}})
# Explicit closed shape of reused existing extraction, without changing that reader.
def meaning(choices):return obj({'value':enum(*choices),'witnesses':arr(AW)})
PUNIT=obj({'witness':AW,'raw_unit':S,'canonical_unit':nullable(CANUNIT),'multiplier':nullable(N),'unavailable_reason':nullable(enum('unsupported_source_kinetic_unit'))})
NUM=obj({'selector':ANS,'raw_number':S,'value':N,'relation':enum('point','lt','le','gt','ge'),'approximate':B})
CINTER=obj({'selector':obj({'witness':AW,**{k:I for k in ('lower_start','lower_end','upper_start','upper_end')}}),'raw_values':{'type':'array','items':S,'minItems':2,'maxItems':2},'values':{'type':'array','items':N,'minItems':2,'maxItems':2}})
CONF=obj({'witness':AW,'value':N})
CANUNC=obj({'statistic':enum('sd','sem','ci','unspecified','unreported'),'magnitude':nullable(N),'interval':nullable({'type':'array','items':N,'minItems':2,'maxItems':2}),'confidence_level':nullable(N),'count':nullable({'type':'integer','minimum':1}),'repetition_basis':enum('biological_preparations','technical_measurements','unspecified'),'estimate_basis':enum('fit_to_averaged_curve','between_fitted_parameters','unknown')})
SUBJ=obj({k:nullable(S) for k in ('organism','genotype','molecule','construct')})
CTX=obj({k:nullable(S) for k in ('substrate','preparation','experiment','experimental_system','conditions','endpoint','normalization')})
COP=obj({'parameter_kind':enum('Km','kcat','catalytic_efficiency'),'unit':nullable(CANUNIT),'value':nullable(N),'status':enum('point','censored','missing','conflicting'),'relation':enum('eq','lt','le','gt','ge','none'),'approximate':B,'origin':enum('reported','graph_derived','calculated','synthetic'),'measurement_id':S,'physical_measurement_id':nullable(S),'subject':SUBJ,'context':CTX,'uncertainty':CANUNC,'source':LOC,'unavailable_reason':nullable(enum(*PREASONS))})
UNC=obj({'meanings':obj({'statistic':meaning(('sd','sem','ci','unspecified','unreported')),'unit_relationship':meaning(('same_as_parameter','explicit_unit','unknown')),'repetition_basis':meaning(('biological_preparations','technical_measurements','unspecified')),'estimate_basis':meaning(('fit_to_averaged_curve','between_fitted_parameters','unknown'))}),'magnitude':nullable(NUM),'interval':nullable(CINTER),'unit':nullable(PUNIT),'effective_unit':nullable(PUNIT),'confidence_level':nullable(CONF),'count':nullable(COUNT),'canonical':CANUNC,'unavailable_reason':nullable(enum('source_uncertainty_unit_unavailable','source_numeric_range'))})
ROP=obj({'parameter_kind':meaning(('Km','kcat','catalytic_efficiency','unknown','conflicting')),'subject':obj({k:nullable(AW) for k in SUBJ['properties']}),'context':obj({k:nullable(AW) for k in CTX['properties']}),'measurement_identity':nullable(AW),'number':nullable(NUM),'unit':nullable(PUNIT),'qualification':meaning(('reported_point','source_qualified_approximate','unknown','conflicting')),'approximate':B,'source_origin':enum('reported','synthetic'),'canonical_value':nullable(N),'uncertainty':UNC,'calculation_operand':nullable(COP),'unavailable_reasons':arr(S)})
COMPARISON={k:dc(v) for k,v in KS['properties']['comparison']['properties'].items()}
for v in COMPARISON.values():v['properties']['witnesses']=arr(AW)
CINPUT=obj({'version':{'const':'a105_kinetic_contrast_inputs_v1'},**{k:dc(v['properties']['value']) for k,v in COMPARISON.items()},'numerator':nullable(COP),'denominator':{'type':'null'}})
KINEXT=obj({'version':{'const':'a105_kinetic_source_extraction_v3'},'source_ref':REF,'source_kind':enum('primary_source','synthetic_fixture'),'operands':obj({'numerator':ROP,'denominator':{'type':'null'}}),'comparison':obj(COMPARISON),'calculation_inputs':CINPUT,'input_unavailable_reasons':obj({'numerator':arr(S),'denominator':arr(S)}),'source_refs':arr(REF,True),'implementation_dependencies':obj({k:S for k in ('custody_module','custody_sha256','scalar_module','scalar_sha256','scalar_scope_module','scalar_scope_sha256')})})
AINTER=obj({'row_footnote_applicability':assessment(AW),'source_count_meaning':cm(AW),'statistical_count':nullable(COUNT),**{k:assessment(AW) for k in AFIELDS if k!='row_footnote_applicability'}})
EXTRACTION=obj({'version':{'const':'a105_kinetic_summary_precision_extraction_v1'},'selection':SEL,'kinetic_extraction':KINEXT,'interpretation':AINTER,'source_refs':arr(REF,True),'calculation_inputs':INPUT})
for name,schema in [('SELECTION_SCHEMA_001.json',SEL),('EXTRACTION_SCHEMA_001.json',EXTRACTION),('CALCULATION_INPUTS_SCHEMA_001.json',INPUT),('SHEET_SCHEMA_001.json',SHEET)]:
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema',**schema}
    write(name,schema)
# Exact source selection plus explicit scenario, still a proposed argument, not a saved production result.
selection=json.loads((REVIEW/'ROOT_ENRICHED_SELECTION_004.json').read_text())
row_w=dc(selection['numerator']['measurement']['number']['witness'])
foot_w=dc(selection['numerator']['context']['preparation'])
unknown=lambda:{'state':'unknown','witnesses':[]}
interpretation={k:unknown() for k in AFIELDS}
interpretation['row_footnote_applicability']={'state':'source_supported','witnesses':[row_w,foot_w]}
interpretation['source_count_meaning']={'value':'physical_preparation_count','witnesses':[foot_w]}
interpretation['statistical_count']=None
proposed={'version':'a105_kinetic_summary_precision_selection_v1','kinetic_selection':selection,'interpretation':interpretation,'scenario':{'version':'a105_summary_precision_scenario_v1','count_rule':'one_per_physical_preparation','stipulated_assumptions':list(ACODES)},'interval_request':'student_t_95'}
write('ACTUAL_SOURCE_SELECTION_PROPOSAL_001.json',proposed)
# Exercise only EXISTING source reader, read-only callback on retained public bytes.
def read_source(reference,representation):
    assert reference=='@elife2015AP'
    content=(PACKET/'sources'/('elife-06181-v2.pdf' if representation=='original' else 'elife-06181-v2.txt')).read_bytes()
    return {'artifact_ref':'sha256_'+hashlib.sha256(content).hexdigest(),'content':content}
existing=read_kinetic_inputs(selection,read_source=read_source)
write('EXISTING_READER_REEXECUTION_001.json',existing)
# Check declared standalone plan schemas and the embedded reuse result.
import jsonschema
for schema in (SEL,INPUT,SHEET,EXTRACTION):jsonschema.Draft202012Validator.check_schema(schema)
jsonschema.Draft202012Validator(SEL).validate(proposed)
jsonschema.Draft202012Validator(KINEXT).validate(existing)
x,s,n=Fraction('3.1'),Fraction('.1'),2
scale=_UNIT_TABLES['catalytic_efficiency'][_normalize(existing['operands']['numerator']['unit']['raw_unit'])][1]
v=s*s/n
se=math.sqrt(float(v))
quant=float(t.ppf(.975,n-1))
write('PROPOSED_NUMERICAL_EXAMPLE_001.json',{'status':'plan_arithmetic_only_not_new_component_execution','source':{'x_native_exact':str(x),'sd_native_exact':str(s),'physical_preparation_count':n,'ordinary_statistical_estimator_count':None,'ordinary_mean_variance':None,'ordinary_mean_se':None,'relative_reported_sd_exact':str(s/x),'relative_reported_sd':float(s/x),'canonical_parameter':float(x*scale),'canonical_sd':float(s*scale),'canonical_scale_exact':str(scale)},'explicit_scenario':proposed['scenario'],'conditional':{'statistical_estimator_count':n,'mean_variance_native_exact':str(v),'mean_variance_canonical_exact':str(v*scale*scale),'mean_variance_canonical':float(v*scale*scale),'mean_se_native':se,'mean_se_canonical':se*float(scale),'relative_mean_se':se/float(x),'proposed_confidence_level':.95,'df':n-1,'t_multiplier':quant,'halfwidth_native':quant*se,'lower_native':float(x)-quant*se,'upper_native':float(x)+quant*se,'lower_canonical':(float(x)-quant*se)*float(scale),'upper_canonical':(float(x)+quant*se)*float(scale)},'synthetic_supported_n4':{'x':10,'sd':2,'statistical_n':4,'variance':1,'se':1,'t_df3':float(t.ppf(.975,3))},'calibration_uncertainty':None,'total_uncertainty':None,'assay_error_probability':None,'annotation_credit':None})
(HERE/'TASK_PROPOSAL_001.txt').write_bytes((REVIEW/'SUMMARY_PRECISION_TASK_PROPOSAL_004.txt').read_bytes())
write('PLAN_CHECKS_001.json',{'status':'passed','schemas_checked':4,'actual_proposed_selection_valid':True,'existing_reader_result_valid_in_closed_reuse_schema':True,'existing_reader_canonical_parameter':existing['operands']['numerator']['canonical_value'],'existing_reader_canonical_sd':existing['operands']['numerator']['uncertainty']['canonical']['magnitude'],'existing_reader_count':existing['operands']['numerator']['uncertainty']['canonical']['count'],'task_preserved_byte_for_byte':(HERE/'TASK_PROPOSAL_001.txt').read_bytes()==(REVIEW/'SUMMARY_PRECISION_TASK_PROPOSAL_004.txt').read_bytes(),'new_component_execution':False,'production_tests':False,'selected_episode':False,'provider_model':False,'versions':{k:importlib.metadata.version(k) for k in ('scipy','jsonschema','Pillow')}})
print('Plan schemas, existing-reader reproduction and exact TASK copy validated; no proposed production component executed.')
