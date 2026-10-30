"""Design constructors only: no production reader/calculator implementation."""
from copy import deepcopy as cp
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
from gene_annotation_episode import literature_controlled_response_v2_inputs as v2
from gene_annotation_episode import literature_controlled_response_owner_calculations as owner

def obj(p):return dict(type='object',properties=p,required=list(p),additionalProperties=False)
def ref(n):return {'$ref':'#/$defs/'+n}
def arr(x,**kw):return dict(type='array',items=x,**kw)
def null(x):return {'anyOf':[x,{'type':'null'}]}
def enum(*x):return {'enum':list(x)}
def put(n,x):
    with (HERE/n).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
T={'type':'string','minLength':1};I={'type':'integer','minimum':0};B={'type':'boolean'}
ROLES=list(v2.controlled_response_v2_arguments_schema()['properties']['arms']['properties'])
S=v2.controlled_response_v2_arguments_schema()
S['properties']['version']={'const':'controlled_response_source_selection_v3'}
D=S['$defs']
D['ReadingSelector']=obj({'role':enum(*ROLES),'reading_key':null(T)})
D['Assignment']=obj({r:null(T) for r in ROLES})
D['ScopeRelation']=obj({'value':enum('same','explicit_compatible','not_applicable','unknown','conflicting'),'witnesses':arr(ref('Witness'))})
D['Authority']=obj({'status':enum('source_explicit','not_established','conflicting'),'reading':null(ref('ReadingSelector')),'witnesses':arr(ref('Witness'))})
D['ReconciliationNomination']=obj({'role':enum(*ROLES),
    'relationship':obj({'value':enum('same_reported_mean_and_display','exact_duplicate','alternative_estimates','unknown','conflicting'),'witnesses':arr(ref('Witness'))}),
    'authority':ref('Authority'),
    'normalization':ref('ScopeRelation'),'calibration':ref('ScopeRelation'),'revision':ref('ScopeRelation'),
    'model_scope':ref('ScopeRelation')})
S['properties']['companion_readings']=arr(obj({'reading_key':T,'primary_role':enum(*ROLES),'reading':ref('Arm')}))
S['properties']['joint_reading_assignments']=arr(obj({'assignment':ref('Assignment'),
    'admissibility':obj({'value':enum('compatible','unknown','conflicting'),'witnesses':arr(ref('Witness'))})}))
# Separate scope rows preserve the complete original069 assignment objects.
D['JointScope']=obj({'assignment_index':I,'normalization':ref('ScopeRelation'),'calibration':ref('ScopeRelation'),
    'revision':ref('ScopeRelation'), 'covariance_scope':ref('ScopeRelation'),'model_scope':ref('ScopeRelation'),
    'covariance_selection':cp(S['properties']['covariance']),
    'variance_status':cp(S['properties']['variance_status']),'model_kind':cp(S['properties']['model_kind'])})
D['LocalPairNomination']=obj({'pair_key':T,'condition':enum('condition1','condition0'),
    'protein':ref('ReadingSelector'),'control':ref('ReadingSelector'),
    'admissibility':obj({'value':enum('compatible','unknown','conflicting'),'witnesses':arr(ref('Witness'))}),
    'scope':ref('ScopeRelation'),'covariance_selection':cp(S['properties']['covariance']),
    'variance_status':cp(S['properties']['variance_status'])})
for name,shape in [('joint_scopes',arr(ref('JointScope'))),('reading_reconciliations',arr(ref('ReconciliationNomination'))),('local_pair_assignments',arr(ref('LocalPairNomination')))]:S['properties'][name]=shape
S['required'] += ['companion_readings','joint_reading_assignments','joint_scopes','reading_reconciliations','local_pair_assignments']
put('SELECTION_SCHEMA_V3_007.json',S)

# Public source-v2 schemas remain unchanged; v3 retains empty covariance text.
E=v2._extraction_schema();ED=E['$defs']
ED['CovarianceExtraction']['properties']['raw_text']=null({'type':'string'})
ED['V3Selection']=v2.embed(S,'V3S_',ED)
E['properties']['version']={'const':'controlled_response_source_extraction_v3'}
E['properties']['selection']=ref('V3Selection')
ED['ReadingSelector']=cp(D['ReadingSelector'])
ED['Authority']=cp(D['Authority'])
ED['ScopeRelation']=cp(D['ScopeRelation'])
ED['RetainedRepresentation']['properties']['reading_key']=null(T)
ED['RetainedRepresentation']['required'].append('reading_key')
ED['Assignment']=cp(D['Assignment'])
ED['ScopeRelationExtraction']=obj({'selection':cp(D['ScopeRelation']),'witnesses':arr(ref('WitnessRecord')),
    'effective_value':cp(D['ScopeRelation']['properties']['value'])})
ED['CompanionExtraction']=obj({'reading_key':T,'primary_role':enum(*ROLES),'reading':ref('ArmExtraction')})
ED['ReconciliationDecision']=obj({'role':enum(*ROLES),'selection':cp(D['ReconciliationNomination']),
    'witnesses':arr(ref('WitnessRecord')),'reading_selectors':arr(ref('ReadingSelector'),minItems=1),
    'scientific_correspondence':enum('same','unknown','conflicting'),
    'method':enum('single','exact_equivalence','explicit_reported_mean_display','unresolved'),
    'state':enum('ready','unknown_authority','conflicting_authority','different_domains','scientific_conflict','unsupported_group_projection','unimplemented_model'),
    'selected_reading':null(ref('ReadingSelector')),'normalized_domain_checks':arr(obj({'reading':ref('ReadingSelector'),
       'relation_to_selected':enum('equal','contains','disjoint','unknown')})),
    'model_state':enum('original_source_model','none','unresolved'),
    'qualifications':arr(enum('conditional_digitization_not_sampling','source_explicit_reported_mean','same_representation_not_replication',
        'mixed_original_origins_retained','unsupported_group_origin','unavailable_group_identity','source_scope_unresolved'),uniqueItems=True)})
ED['ConditionalInput']=obj({'reading_assignment':ref('Assignment'),'scope_index':I,
    'source_covariance':null(ref('CovarianceExtraction')),'requested_model':ref('RequestedModel'),'effective_model':ref('EffectiveModel'),
    'calculation_inputs':ref('OwnerInputs')})
E['properties']['calculation_inputs']=null(ref('OwnerInputs'))
for name,shape in [('companion_extractions',arr(ref('CompanionExtraction'))),
    ('projection_status',enum('ready','unresolved_active_reconciliation')),
    ('final_projection_basis',null(obj({'reading_assignment':ref('Assignment'),'covariance_scope':enum('base','joint'), 'scope_index':null(I), 'reconciled_roles':arr(enum(*ROLES),uniqueItems=True)}))),
    ('reconciliation_decisions',arr(ref('ReconciliationDecision'))),
    ('joint_scope_extractions',arr(obj({'assignment_index':I,'witnesses':arr(ref('WitnessRecord')),'effective_admissibility':enum('compatible','unknown','conflicting'),
        'source_covariance':null(ref('CovarianceExtraction')),'requested_model':ref('RequestedModel'),'effective_model':ref('EffectiveModel')}))),
    ('alternative_inputs',arr(ref('ConditionalInput'))),
    ('partial_calculation_inputs',null(ref('OwnerInputs'))),
    ('partial_projection_state',enum('not_required','ready','unsupported_origin_projection','unavailable_group_identity')),
    ('component_local_inputs',ref('LocalInputs'))]:E['properties'][name]=shape
E['required'] += ['companion_extractions','projection_status','final_projection_basis','reconciliation_decisions','joint_scope_extractions','alternative_inputs',
    'partial_calculation_inputs','partial_projection_state','component_local_inputs']
ED['DependencyRecord']['properties']['reader_contract_version']={'const':'controlled_response_source_extraction_v3'}
for name in ['literature_controlled_response_v3_inputs.py','literature_controlled_response_local_calculations.py']:
    ED['DependencyRecord']['properties']['expected_module_fingerprints']['properties'][name]=cp(v2.SHA)
    ED['DependencyRecord']['properties']['expected_module_fingerprints']['required'].append(name)

# Standalone component-local PARSED input: never a four-arm OwnerInputs wrapper.
LD=cp(v2._extraction_schema()['$defs'])
LD['CovarianceExtraction']['properties']['raw_text']=null({'type':'string'})
LD['ReadingSelector']=cp(D['ReadingSelector'])
LD['CovarianceDocument']=obj({k:cp(LD['CovarianceExtraction']['properties'][k]) for k in ['source_ref','artifact_ref','byte_sha256','raw_text','variables','matrix_tokens','exact_matrix','source_model','source_validation','diagnostics']})
LD['CovarianceDocument']['properties']['document_state']=enum('available','unavailable','unsupported_format')
LD['CovarianceDocument']['required'].append('document_state')
LD['LocalReading']=obj({'reading':ref('ReadingSelector'),'arm':null(ref('O_Arm')),
    'reported_uncertainty':ref('UncertaintyCanonical'),
    'source_kind':null(cp(D['Arm']['properties']['source_kind'])),
    'measurement_method':enum('text','graph','not_selected')})
LD['LocalReading']['allOf']=[{'if':{'properties':{'arm':{'type':'null'}}},'then':{'properties':{'source_kind':{'type':'null'},'measurement_method':{'const':'not_selected'}}},
    'else':{'properties':{'source_kind':cp(D['Arm']['properties']['source_kind'])}}}]
LD['LocalPair']=obj({'pair_key':T,'condition':enum('condition1','condition0'),
    'protein':ref('ReadingSelector'),'control':ref('ReadingSelector'),
    'target':cp(owner.controlled_response_owner_arguments_schema()['$defs']['Relationships']['properties']['condition1_target']),
    'control_application':enum('matched_condition_control','shared_reference_assumption','unknown','conflicting'),
    'joint_admissibility':enum('compatible','unknown','conflicting'),
    'scope_state':enum('same','explicit_compatible','not_applicable','unknown','conflicting'),
    'covariance_index':null(I),'protein_binding':null(ref('CovarianceBindingExtraction')),
    'control_binding':null(ref('CovarianceBindingExtraction')),'variance_status':enum('known','estimated','unknown')})
L=obj({'version':{'const':'controlled_response_local_inputs_v1'},'readings':arr(ref('LocalReading')),
    'pairs':arr(ref('LocalPair')),'source_covariances':arr(ref('CovarianceDocument'))})
L.update({'$defs':LD,'$schema':'https://json-schema.org/draft/2020-12/schema'})
ED['LocalInputs']=v2.embed(L,'Local_',ED)
ED['ScopeKey']=obj({'kind':enum('base','joint','local'),'index':null(I)})
ED['CovarianceDocument']=v2.embed({'$defs':LD,**ref('CovarianceDocument')},'Document_',ED)
E['properties']['covariance_document_scopes']=arr(obj({'scope':ref('ScopeKey'),'document':null(ref('CovarianceDocument'))}))
E['required'].append('covariance_document_scopes')
ED['BoundCovarianceScope']=obj({'scope':ref('ScopeKey'),'document':null(ref('CovarianceDocument')),
    'bindings':arr(obj({'reading':ref('ReadingSelector'),'binding':ref('CovarianceBindingExtraction')})),
    'whole_projection':null(ref('CovarianceExtraction'))})
put('EXTRACTION_SCHEMA_V3_007.json',E);put('LOCAL_INPUT_SCHEMA_007.json',L)

RD=cp(LD)
RD['Dependency']=obj({'scientific_readings':arr(ref('ReadingSelector'),uniqueItems=True),
    'numeric_readings':arr(ref('ReadingSelector'),uniqueItems=True),
    'uncertainty_readings':arr(ref('ReadingSelector'),uniqueItems=True),
    'covariance_index':null(I),'covariance_owner_ids':arr(T,uniqueItems=True),
    'source_variable_indices':arr(I,uniqueItems=True),'model_readings':arr(ref('ReadingSelector'),uniqueItems=True),
    'unresolved_readings':arr(ref('ReadingSelector'),uniqueItems=True),
    'numeric_fields':arr(obj({'reading':ref('ReadingSelector'),'fields':arr(enum('value','threshold','relation','approximate','unit','status','origin','digitization_interval','digitization_interval_presence'),uniqueItems=True)})),
    'full_source_covariance_required':B})
# Existing complete Cell, extended with precise local reasons; original Cell not modified.
RD['LocalCell']=cp(RD['H_Cell'])
RD['LocalCell']['properties']['origin']=null(cp(RD['LocalCell']['properties']['origin']))
RD['LocalCell']['properties']['unavailable_reason']['anyOf'][0]['items']['enum'] += [
    'unknown_joint_applicability','conflicting_joint_applicability','unknown_covariance_owner','source_full_covariance_invalid',
    'source_covariance_unassessed','local_covariance_binding_unknown','local_covariance_binding_conflicting','local_scope_unresolved']
RD['LocalCell']['properties']['formula_code']['enum'] += ['local_joint_covariance','local_square_root_variance']
RD['LocalPopulationInputs']=v2.embed(L,'Parsed_',RD)
R=obj({'version':{'const':'controlled_response_local_sheet_v1'},'inputs':ref('LocalPopulationInputs'),
    'raw':arr(obj({'reading':ref('ReadingSelector'),'cell':ref('LocalCell'),'reported_uncertainty':ref('UncertaintyCanonical'),'dependencies':ref('Dependency')})),
    'pairs':arr(obj({'pair_key':T,'difference':ref('LocalCell'),'variance':ref('LocalCell'),'standard_uncertainty':ref('LocalCell'),
        'dependencies':obj({k:ref('Dependency') for k in ['difference','variance','standard_uncertainty']})})),
    'full_covariance_checks':arr(obj({'covariance_index':I,'source_validation':enum('valid','invalid','unassessed'),
        'document_state':enum('available','unavailable','unsupported_format')}))})
R.update({'$defs':RD,'$schema':'https://json-schema.org/draft/2020-12/schema'});put('LOCAL_OUTPUT_SCHEMA_007.json',R)

PD=cp(ED)
PD['LocalSheet']=v2.embed(R,'Result_',PD)
components=list(v2._sheet_schema()['properties']['cells']['properties'])
PD['ComponentDependency']=cp(RD['Dependency'])
P=obj({'version':{'const':'controlled_response_conditional_population_v3'},
    'projection_status':enum('ready','unresolved_active_reconciliation'),
    'final_sheet':null(ref('OwnerSheet')),'partial_sheet':null(ref('OwnerSheet')),
    'local_sheet':ref('LocalSheet'),'unresolved_roles':arr(enum(*ROLES),uniqueItems=True),
    'alternatives':arr(obj({'reading_assignment':ref('Assignment'),'scope_index':I,'sheet':ref('OwnerSheet')})),
    'unaffected_components':arr(obj({'component':T,'cell':ref('H_Cell'),'dependencies':ref('ComponentDependency')})),
    'conditional_components':arr(obj({'assignment_index':I,'component':enum(*components),'cell':ref('H_Cell'),'dependencies':ref('ComponentDependency')}))})
P.update({'$defs':PD,'$schema':'https://json-schema.org/draft/2020-12/schema'});put('POPULATION_SCHEMA_V3_007.json',P)

# Exact closed native fact view: full private payload is not parent possession.
FD=cp(RD)
FD['SemanticContext']=obj({'endpoint_id':null(T),'normalization_id':null(T),'subject_construct_ids':arr(T,uniqueItems=True),
    'condition_ids':arr(T,uniqueItems=True),'owner_ids':arr(T,uniqueItems=True),'owner_state':enum('known','unknown','conflicting'),
    'control_application':null(enum('matched_condition_control','shared_reference_assumption','unknown','conflicting')),
    'condition_control_applications':obj({k:null(enum('matched_condition_control','shared_reference_assumption','unknown','conflicting')) for k in ['condition1','condition0']}),
    'control_reuse':null(enum('distinct_observations','same_reference_with_stated_invariance','unknown','conflicting')),
    'protein_arrangements':arr(enum('protein_present','protein_free_control','empty_vector_control','other_specified','unknown','conflicting'),uniqueItems=True),
    'variance_status':enum('known','estimated','unknown'),'model_kind':enum('none','known_joint_normal_source_means'),
    'representation_state':enum('single','reconciled','unresolved','conditional'),
    'source_kinds':arr(enum('primary_source','retained_extraction','synthetic_fixture'),uniqueItems=True),
    'original_origins':arr(enum('reported','graph_derived','synthetic'),uniqueItems=True),
    'measurement_methods':arr(enum('text','graph','not_selected'),uniqueItems=True),
    **{k+'_state':enum('known','unknown','conflicting') for k in ['endpoint','normalization','subject_construct','condition']}})
FD['JointScopeWitness']=obj({'witness_ref':dict(type='string',format='reference',**{'x-reference-namespace':'reference'}),
    'authentication':enum('exact_utf8_byte_span','image_bytes_and_geometry_only','unavailable'),
    'attribution':enum('literal_source_record','investigating_episode_interpretation')})
for name,selected_values,effective_values in [
    ('JointScopeRelation',['same','explicit_compatible','not_applicable','unknown','conflicting'],['same','explicit_compatible','not_applicable','unknown','conflicting']),
    ('JointAdmissibility',['compatible','unknown','conflicting'],['compatible','unknown','conflicting']),
    ('JointVarianceRequest',['known','estimated','unknown'],['known','estimated','unknown']),
    ('JointModelRequest',['none','known_joint_normal_source_means'],['none','known_joint_normal_source_means','unknown'])]:
    FD[name]=obj({'selected_value':enum(*selected_values),'effective_value':enum(*effective_values),
        'witnesses':arr(ref('JointScopeWitness'))})
FD['JointScopeContext']=obj({'reading_assignment':cp(D['Assignment']),
    'assignment_admissibility':ref('JointAdmissibility'),
    'effective_admissibility':enum('compatible','unknown','conflicting'),
    **{name:ref('JointScopeRelation') for name in ['normalization','calibration','revision','covariance_scope','model_scope']},
    'requested_model':obj({'variance_status':ref('JointVarianceRequest'),'model_kind':ref('JointModelRequest')}),
    'effective_model':ref('EffectiveModel'),
    'covariance_context':null(obj({'source_ref':dict(type='string',format='reference',**{'x-reference-namespace':'source'}),
        'source_validation':cp(ED['CovarianceExtraction']['properties']['source_validation']),
        'projection_state':cp(ED['CovarianceExtraction']['properties']['projection_state']),
        'source_model':null(ref('SourceModel'))}))})
FD['NumericLocation']={'oneOf':[obj({'kind':{'const':'utf8_span'},'source_ref':T,'start':I,'end':{'type':'integer','minimum':1}}),
    obj({'kind':{'const':'image_region'},'source_ref':T,'region':ref('Box')}),obj({'kind':{'const':'unresolved'},'source_ref':T})]}
FD['NativeReading']=obj({k:cp(LD['O_Arm']['properties'][k]) for k in ['value','threshold','relation','approximate','unit','status','origin','digitization_interval','source_observation_id']})
F=obj({'version':{'const':'literature_controlled_response_component_fact_v3'},'sheet_ref':dict(type='string',format='reference',**{'x-reference-namespace':'source'}),'component_key':T,
    'kind':enum('native_raw','local_difference','local_variance','local_standard_uncertainty','final','conditional'),
    'component':enum(*components,'local_difference','local_variance','local_standard_uncertainty'),
    'reading':null(ref('ReadingSelector')),'reading_assignment':null(cp(D['Assignment'])),'pair_key':null(T),
    'cell':ref('LocalCell'),'native_reading':null(ref('NativeReading')),'reported_uncertainty':null(ref('UncertaintyCanonical')),
    'reported_uncertainty_unit':cp(FD['TextUnitRecord']['properties']['canonical_unit']),
    'numeric_locations':arr(ref('NumericLocation')),
    'context':ref('SemanticContext'),'dependencies':ref('Dependency'),'joint_scope_context':null(ref('JointScopeContext'))})
F.update({'$defs':FD,'$schema':'https://json-schema.org/draft/2020-12/schema'});put('NATIVE_FACT_SCHEMA_V3_007.json',F)
Return={'type':'array','items':{k:cp(v) for k,v in F.items() if k not in ('$defs','$schema')},'$defs':cp(FD),
    '$schema':'https://json-schema.org/draft/2020-12/schema','x-source':'literature_controlled_response_component_cells'}
put('NATIVE_RETURN_SCHEMA_V3_007.json',Return)

put('API_007.json',{'source_module':'gene_annotation_episode/literature_controlled_response_v3_inputs.py',
    'source_api':['controlled_response_v3_arguments_schema() -> dict','validate_controlled_response_v3_selection(arguments) -> dict',
        'read_controlled_response_v3_inputs(arguments, *, read_source) -> SourceExtractionV3',
        'validate_controlled_response_v3_extraction(arguments, extraction) -> SourceExtractionV3'],
    'local_module':'gene_annotation_episode/literature_controlled_response_local_calculations.py',
    'local_api':['controlled_response_local_arguments_schema() -> dict','validate_controlled_response_local_inputs(inputs) -> LocalInputs',
        'populate_controlled_response_local(inputs) -> LocalSheet','validate_controlled_response_local_sheet(inputs, sheet) -> LocalSheet'],
    'population_api':['populate_controlled_response_v3(extraction) -> ConditionalPopulationV3',
        'validate_controlled_response_v3_population(extraction, population) -> ConditionalPopulationV3'],
    'native_api':['LiteratureControlledResponseRepository.populate_v3(context, arguments, operation_key) -> ToolOutcome',
        'LiteratureControlledResponseRepository.read(sheet_ref) -> OriginalPopulationPayload',
        'LiteratureControlledResponseRepository.project_cells(sheet_refs, *, permitted_record_refs, components) -> NativeFactV3[]',
        'LiteratureControlledResponseRepository.fact_cells(context, sheet_refs, *, components) -> NativeFactV3[]',
        'LiteratureControlledResponseRepository.validate_fact_values(context, cells) -> None',
        'LiteratureControlledResponseRepository.receive_cells(context, cells, operation_key) -> None',
        'LiteratureControlledResponseRepository.received_cells(context) -> NativeFactV3[]'],
    'native_host_context':{'fields':['run_id','episode_id','role','assignment','scope','received_record_refs'],
        'authority':'Actual ordinary episode/tool context supplied by Workflow, never model-selected owner IDs or caller-composed proof'},
    'native_form_source':'literature_controlled_response_component_cells',
    'native_tables':{'operations':'literature_controlled_response_operations','received':'literature_controlled_response_component_received',
        'delivery':'literature_controlled_response_component_delivery_bindings'},
    'native_component_identity':['sheet_ref','component_key'],
    'native_runtime_proof':'Inherited _runtime_delivery_cells reads successful runtime_report_attempts at run:parent:decision:typed_form; exact child runtime_episodes.request.report_contract (or authenticated selected repair), original form and child_episode_id/delivery_ref must match. No proof argument is accepted.',
    'shared_stage_api':[
        'open_controlled_response_sources(arguments, *, read_source) -> SourceContext[v1|v2|v3]',
        'read_controlled_response_arm_science(context, selected_arm, *, reading_selector=None) -> ArmScience',
        'read_controlled_response_text_measurement(context, selected, *, endpoint, reading_selector=None) -> MeasurementReading',
        'finish_controlled_response_arm(context, arm_science, *, measurement, reading_selector=None) -> ArmExtraction',
        'read_controlled_response_covariance_document(context, scope_key) -> CovarianceDocumentStage | None',
        'bind_controlled_response_covariance_scope(context, scope_key, document, *, readings) -> BoundCovarianceScope',
        'finish_controlled_response_inputs(context, *, arms, companion_arms=None, covariance_scopes=None) -> SourceExtraction',
        'validate_controlled_response_saved_science(arguments, extraction, *, measurement_checks) -> SourceExtraction'],
    'shared_contract':'SHARED_STAGE_EXTENSION_006.md plus AUTHORITY_SELECTION_AND_ABSENT_ARM_CORRECTION_009.md defines exact selectors, stage payloads, one closure, scope keys, binding and identities; old v1/v2 keyword-absent behavior is exact',
    'absent_local_arm_contract':'LocalReading.arm=null requires source_kind=null and measurement_method=not_selected; explicit unavailable raw cell origin=null; selected missing readings retain actual nonnull Arm and source kind',
    'source_calls_sheet':False,'local_calls_whole_owner_or_legacy_sheet':False})
print('Constructed seven corrected exact closed schemas and API declaration; no production changes.')
