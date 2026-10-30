from pathlib import Path
import json
P=Path(__file__).resolve().parent
def obj(p):return {'type':'object','properties':p,'required':list(p),'additionalProperties':False}
def s():return {'type':'string'}
def n():return {'type':'integer','minimum':0}
def c(x):return {'const':x}
w=obj({'path':s(),'sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'},'bytes':n()})
result=obj({'version':c('configured_literature_localization_preparation_result_v1'),'status':c('prepared_not_started'),
 'run_directory':s(),'workspace':s(),'execution_implementation_sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'},
 **{k:{'$ref':'#/$defs/witness'} for k in ['custody_result','receipt','case_launch','parameters','working_database_after_prepare','config','focus','policy_source']},
 'native_registry_ref':s(),'public_search_registry_ref':s(),'inherited_refs':c(200),'source_guards_unchanged':c(True),
 'native_registry_counts':obj({k:c(0) for k in ['orders','handoffs','samples']}),
 'preserved_old_runtime_counts':obj({'runtime_runs':c(1),'runtime_episodes':c(1),'runtime_actions':c(179),'runtime_observations':c(175),'runtime_model_calls':c(180)}),
 'new_scientific_runs_started':c(0),'model_http_native_calls':c(0),'limits':{'type':'array','items':s()}})
failure=obj({'version':c('configured_literature_localization_preparation_failure_v1'),
 'phase':{'enum':['validate_inputs','source_before_guard','custody','verify_custody','prepare_case','derive_parameters','validate_policy','source_after_guard']},
 'exception_type':s(),'message':s(),'source_unchanged':{'type':['boolean','null']},'source_guard_error_type':{'type':['string','null']},
 'run_directory':s(),'preserve_partial':c(True),'automatic_retry':c(False),'model_http_native_calls':c(0)})
x={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:configured-literature-localization-preparation-operator:20261022:001',
 'description':'Unadopted operator engineering outputs only; never an episode parent form, runtime gate or production schema.',
 '$defs':{'witness':w,'result':result,'failure':failure}}
with (P/'OPERATOR_OUTPUT_SCHEMA001.json').open('x') as f:json.dump(x,f,sort_keys=True,indent=2);f.write('\n')
