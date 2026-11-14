"""Source-bound v3 readers and closed parsed contracts for internal A105 sheets.

These host functions read experimental quantities and preserve source meanings.
"""
from __future__ import annotations
from copy import deepcopy as cp
import json
from functools import lru_cache
from jsonschema import Draft202012Validator
from . import literature_controlled_response_v2_inputs as v2
from . import literature_controlled_response_owner_calculations as owner
from . import literature_controlled_response_inputs as shared

@lru_cache(maxsize=1)
def _schemas():
    schemas = {}
    def obj(p):return dict(type='object',properties=p,required=list(p),additionalProperties=False)
    def ref(n):return {'$ref':'#/$defs/'+n}
    def arr(x,**kw):return dict(type='array',items=x,**kw)
    def null(x):return {'anyOf':[x,{'type':'null'}]}
    def enum(*x):return {'enum':list(x)}
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
    schemas['SELECTION_SCHEMA_V3_007'] = S
    
    # Public v2 remains unchanged. Its copied v3 covariance text type below
    # additionally retains authenticated empty UTF8 as an unsupported partial.
    E=v2._extraction_schema();ED=E['$defs']
    # Empty authenticated UTF8 is a retained unsupported source, not missing.
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
    schemas['EXTRACTION_SCHEMA_V3_007'] = E;schemas['LOCAL_INPUT_SCHEMA_007'] = L
    
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
    R.update({'$defs':RD,'$schema':'https://json-schema.org/draft/2020-12/schema'});schemas['LOCAL_OUTPUT_SCHEMA_007'] = R
    
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
    P.update({'$defs':PD,'$schema':'https://json-schema.org/draft/2020-12/schema'});schemas['POPULATION_SCHEMA_V3_007'] = P
    
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
    F.update({'$defs':FD,'$schema':'https://json-schema.org/draft/2020-12/schema'});schemas['NATIVE_FACT_SCHEMA_V3_007'] = F
    Return={'type':'array','items':{k:cp(v) for k,v in F.items() if k not in ('$defs','$schema')},'$defs':cp(FD),
        '$schema':'https://json-schema.org/draft/2020-12/schema','x-source':'literature_controlled_response_component_cells'}
    schemas['NATIVE_RETURN_SCHEMA_V3_007'] = Return
    
    return schemas

def controlled_response_v3_arguments_schema():
    return cp(_schemas()["SELECTION_SCHEMA_V3_007"])


def _extraction_schema():
    return cp(_schemas()["EXTRACTION_SCHEMA_V3_007"])


def validate_controlled_response_v3_selection(arguments):
    selected = shared._validate_selection(arguments, controlled_response_v3_arguments_schema())
    roster = {(role, None): arm for role, arm in selected["arms"].items()}
    keys = set()
    for row in selected["companion_readings"]:
        key = row["reading_key"]
        if key in keys:
            shared._fail("duplicate_companion_reading_key", "companion_readings")
        keys.add(key)
        roster[(row["primary_role"], key)] = row["reading"]
    def selector(value, field):
        if (value["role"], value["reading_key"]) not in roster:
            shared._fail("controlled_reading_selector_unresolved", field)
    for arm in roster.values():
        if arm and arm["measurement"] and arm["measurement"]["kind"] == "linear_bar":
            v2.graph_reader._validate(v2._graph_request(selected, arm["measurement"]))
    maps = set()
    for row in selected["joint_reading_assignments"]:
        key = tuple(row["assignment"][r] for r in shared.PRIMITIVE_ORDER)
        if key in maps:
            shared._fail("duplicate_joint_reading_assignment", "joint_reading_assignments")
        maps.add(key)
        for role, reading_key in row["assignment"].items():
            selector({"role": role, "reading_key": reading_key}, "joint_reading_assignments")
    indices = [r["assignment_index"] for r in selected["joint_scopes"]]
    if indices != list(range(len(selected["joint_reading_assignments"]))):
        shared._fail("joint_scope_roster_mismatch", "joint_scopes")
    roles = set()
    for row in selected["reading_reconciliations"]:
        role = row["role"]
        if role in roles:
            shared._fail("duplicate_reconciliation_role", "reading_reconciliations")
        roles.add(role)
        auth = row["authority"]
        if auth["status"] == "source_explicit":
            if auth["reading"] is None or auth["reading"]["role"] != role:
                shared._fail("authority_reading_role_mismatch", "reading_reconciliations")
            selector(auth["reading"], "reading_reconciliations.authority.reading")
        elif auth["reading"] is not None:
            shared._fail("authority_reading_without_designation", "reading_reconciliations")
        minimum = 2 if auth["status"] == "conflicting" else 1 if auth["status"] == "source_explicit" else 0
        if len({shared._nomination_key(w) for w in auth["witnesses"]}) < minimum:
            shared._fail("interpretation_witness_required", "reading_reconciliations.authority")
    needed = {r["primary_role"] for r in selected["companion_readings"]}
    if not needed <= roles:
        shared._fail("reading_reconciliation_missing", "reading_reconciliations")
    pairs = set()
    for row in selected["local_pair_assignments"]:
        if row["pair_key"] in pairs:
            shared._fail("duplicate_local_pair_key", "local_pair_assignments")
        pairs.add(row["pair_key"])
        for name, prefix in (("protein", "protein_"), ("control", "empty_")):
            value = row[name]
            selector(value, "local_pair_assignments." + name)
            if value["role"] != prefix + row["condition"]:
                shared._fail("local_pair_role_mismatch", "local_pair_assignments." + name)
    return selected


def _dependencies():
    import hashlib
    from pathlib import Path
    names = list(v2._dependencies()) + ['literature_controlled_response_v3_inputs.py',
        'literature_controlled_response_local_calculations.py']
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in names}


def _selector(role, key=None):
    return {'role': role, 'reading_key': key}


def read_controlled_response_v3_inputs(arguments, *, read_source):
    """Read every actual nomination in one authenticated shared source context."""
    validate_controlled_response_v3_selection(arguments)
    with shared.open_controlled_response_sources(arguments, read_source=read_source) as context:
        readings, arms, companions = {}, {}, []
        nominations = [(_selector(r), context.arguments['arms'][r]) for r in shared.PRIMITIVE_ORDER]
        nominations += [(_selector(row['primary_role'], row['reading_key']), row['reading'])
            for row in context.arguments['companion_readings']]
        for selector, selected in nominations:
            arm = None
            if selected is not None:
                science = shared.read_controlled_response_arm_science(context, selected, reading_selector=selector)
                endpoint = science['meanings']['endpoint']
                measurement = (shared.read_controlled_response_graph_measurement(context, selector, endpoint=endpoint)
                    if selected['measurement'] and selected['measurement']['kind'] == 'linear_bar' else
                    shared.read_controlled_response_text_measurement(context, selected['measurement'],
                        endpoint=endpoint, reading_selector=selector))
                arm = shared.finish_controlled_response_arm(context, science, measurement=measurement, reading_selector=selector)
            readings[(selector['role'], selector['reading_key'])] = arm
            if selector['reading_key'] is None: arms[selector['role']] = arm
            else: companions.append((selector, arm))
        scopes = []
        scope_selectors = [({'kind': 'base', 'index': None}, [_selector(r) for r in shared.PRIMITIVE_ORDER])]
        scope_selectors += [({'kind': 'joint', 'index': i}, [_selector(r, row['assignment'][r]) for r in shared.PRIMITIVE_ORDER])
            for i, row in enumerate(context.arguments['joint_reading_assignments'])]
        scope_selectors += [({'kind': 'local', 'index': i}, [row['protein'], row['control']])
            for i, row in enumerate(context.arguments['local_pair_assignments'])]
        for scope, selectors in scope_selectors:
            document = shared.read_controlled_response_covariance_document(context, scope)
            scopes.append(shared.bind_controlled_response_covariance_scope(context, scope, document,
                readings=[(s, readings[(s['role'], s['reading_key'])]) for s in selectors]))
        return shared.finish_controlled_response_inputs(context, arms=arms, companion_arms=companions, covariance_scopes=scopes)


def _relation(context, nomination, field):
    witnesses = [context.witness(w, field) for w in nomination['witnesses']]
    value = nomination['value']
    if any(w['canonical_locator'] is None for w in witnesses): value = 'unknown'
    return {'selection': cp(nomination), 'witnesses': witnesses, 'effective_value': value}


def _same_science(members):
    if not members or any(a is None for _, a in members): return 'unknown'
    arms = [a for _, a in members]
    if any(v['resolved_state'] == 'conflicting' for a in arms for v in a['meanings'].values()): return 'conflicting'
    if any(v['resolved_state'] != 'known' for a in arms for v in a['meanings'].values()): return 'unknown'
    first = arms[0]
    for arm in arms[1:]:
        if any(arm['meanings'][m]['canonical_id'] != first['meanings'][m]['canonical_id'] for m in shared._MEANINGS): return 'conflicting'
        if arm['protein_arrangement']['effective_value'] != first['protein_arrangement']['effective_value']: return 'conflicting'
        if arm['context'] != first['context']: return 'unknown'
    return 'same'


def _domain(arm):
    return shared._exact_response(arm['measurement'], graph=bool(arm['graph_details'])) if arm else None


def _domain_relation(selected, other):
    if selected is None or other is None or selected['unit'] is None or other['unit'] != selected['unit']:
        return 'unknown'
    if selected == other: return 'equal'
    if shared._response_domains_disjoint(selected, other): return 'disjoint'
    # A reported point can be consistent with a display without equating them.
    if selected['relation'] == 'eq' and selected['point'] is not None and other['lower'] and other['upper']:
        point = shared._fraction(selected['point'])
        if shared._fraction(other['lower']) <= point <= shared._fraction(other['upper']): return 'contains'
    return 'unknown'


def _reconcile(context, nomination, members):
    field = 'reading_reconciliations.' + nomination['role']
    relationship = _relation(context, nomination['relationship'], field + '.relationship')
    relations = {k: _relation(context, nomination[k], field + '.' + k) for k in ('normalization', 'calibration', 'revision', 'model_scope')}
    auth = nomination['authority']
    auth_witnesses = [context.witness(w, field + '.authority') for w in auth['witnesses']]
    science = _same_science(members)
    authority = auth['status'] if all(w['canonical_locator'] is not None for w in auth_witnesses) else 'not_established'
    state, method, chosen = 'unknown_authority', 'unresolved', None
    if science != 'same': state = 'scientific_conflict' if science == 'conflicting' else 'unsupported_group_projection'
    elif authority == 'conflicting' or relationship['effective_value'] == 'conflicting': state = 'conflicting_authority'
    elif any(r['effective_value'] in ('unknown', 'conflicting') for k, r in relations.items() if k != 'model_scope'):
        state = 'unsupported_group_projection'
    else:
        domains = [_domain(a) for s, a in members]
        if len(members) == 1:
            state, method, chosen = 'ready', 'single', members[0][0]
        elif relationship['effective_value'] == 'exact_duplicate' and domains[0] is not None and all(d == domains[0] for d in domains):
            state, method, chosen = 'ready', 'exact_equivalence', members[0][0]
        elif authority == 'source_explicit' and relationship['effective_value'] == 'same_reported_mean_and_display':
            selected = next((a for s, a in members if s == auth['reading']), None)
            domain = _domain(selected)
            checks = [_domain_relation(domain, d) for d in domains]
            if domain and domain['relation'] == 'eq' and not domain['approximate'] and all(c in ('equal', 'contains') for c in checks):
                state, method, chosen = 'ready', 'explicit_reported_mean_display', cp(auth['reading'])
            elif 'disjoint' in checks: state = 'different_domains'
        elif any(shared._response_domains_disjoint(a, b) for i, a in enumerate(domains) if a for b in domains[:i] if b):
            state = 'different_domains'
    selected_domain = _domain(next((a for s, a in members if s == chosen), None))
    qualifications = ['same_representation_not_replication'] if len(members) > 1 else []
    if any(a and a['graph_details'] for s, a in members): qualifications.append('conditional_digitization_not_sampling')
    if method == 'explicit_reported_mean_display': qualifications.append('source_explicit_reported_mean')
    origins = {a['calculation_operand']['origin'] for s, a in members if a}
    if len(origins) > 1: qualifications.append('mixed_original_origins_retained')
    model_state = ('original_source_model' if state == 'ready' and relations['model_scope']['effective_value'] in ('same', 'explicit_compatible')
        else 'none' if relations['model_scope']['effective_value'] == 'not_applicable' else 'unresolved')
    return {'role': nomination['role'], 'selection': cp(nomination),
        'witnesses': [w for r in [relationship, *relations.values()] for w in r['witnesses']] + auth_witnesses,
        'reading_selectors': [cp(s) for s, a in members], 'scientific_correspondence': science,
        'method': method, 'state': state, 'selected_reading': cp(chosen),
        'normalized_domain_checks': [{'reading': cp(s), 'relation_to_selected': _domain_relation(selected_domain, _domain(a))} for s, a in members],
        'model_state': model_state, 'qualifications': sorted(set(qualifications))}


def _requested(context, variance, model, field):
    return {'variance_status': shared._interpretation(context, variance, field + '.variance_status'),
        'model_kind': shared._interpretation(context, model, field + '.model_kind')}


def _owner_projection(arms, relationships, covariance, requested, *, variance_scope=True, model_scope=True):
    effective = shared._effective_model(requested, covariance if variance_scope else None, arms)
    if not model_scope: effective['model_kind'] = 'none'
    parsed = shared._calculation_inputs(arms, relationships, covariance, effective)
    parsed['version'] = 'controlled_response_owner_inputs_v2'
    owner.validate_controlled_response_owner_inputs(parsed)
    return parsed, effective


def _group_mask(role, members):
    """A real retained unresolved group, never an invented union origin."""
    from .domain import identity
    actual = [a for s, a in members if a]
    if not actual or _same_science(members) != 'same': return None, 'unavailable_group_identity'
    operands = [a['calculation_operand'] for a in actual]
    if len({a['origin'] for a in operands}) != 1: return None, 'unsupported_origin_projection'
    if any(a['source_observation_id'] is None for a in operands): return None, 'unavailable_group_identity'
    dimensions = {shared.RATE_UNITS[a['unit']][0] for a in operands if a['unit']}
    if len(dimensions) != 1 or any(a['unit'] is None for a in operands): return None, 'unavailable_group_identity'
    payload = {'primary_role': role, 'primary_reading_id': operands[0]['source_observation_id'],
        'companions': [{'reading_key': s['reading_key'], 'reading_id': a['calculation_operand']['source_observation_id']} for s, a in members[1:]],
        'scientific_owner_id': operands[0]['physical_observation_id'],
        'members': [{'source_kind': a['selection']['source_kind'], 'measurement_method':
            'graph' if a['graph_details'] else 'text' if a['selection']['measurement'] else 'not_selected'} for a in actual]}
    mask = cp(operands[0])
    mask.update(value=None, threshold=None, relation='none', status='ambiguous', digitization_interval=None,
        approximate=any(a['approximate'] for a in operands), source_observation_id=identity('controlled_active_reading_group_v3', payload))
    return mask, 'ready'


def _finish_v3(context, *, arms, companion_arms, covariance_scopes):
    selected = context.arguments
    relationships = cp(context.relationships)
    roster = {(r, None): arms[r] for r in shared.PRIMITIVE_ORDER}
    roster.update({(s['role'], s['reading_key']): a for s, a in companion_arms})
    scopes = {(s['scope']['kind'], s['scope']['index']): s for s in covariance_scopes}
    base_covariance = cp(scopes[('base', None)]['whole_projection'])
    requested = _requested(context, selected['variance_status'], selected['model_kind'], 'model')
    decisions = []
    assignment = {r: None for r in shared.PRIMITIVE_ORDER}
    unresolved = []
    groups = owner._groups([arms[r]['calculation_operand'] if arms[r] else None for r in shared.PRIMITIVE_ORDER])
    canceled = {r for g in groups if g['known_owner'] and g['coefficient'] == 0 for r in g['roles']}
    for nomination in selected['reading_reconciliations']:
        role = nomination['role']
        members = [(_selector(role), arms[role])] + [(s, a) for s, a in companion_arms if s['role'] == role]
        decision = _reconcile(context, nomination, members); decisions.append(decision)
        if decision['state'] == 'ready': assignment[role] = decision['selected_reading']['reading_key']
        elif role not in canceled or _same_science(members) != 'same': unresolved.append(role)
    joint_rows, alternatives = [], []
    for i, nomination in enumerate(selected['joint_reading_assignments']):
        spec = selected['joint_scopes'][i]
        admissibility = _relation(context, nomination['admissibility'], 'joint_reading_assignments')
        relations = {k: _relation(context, spec[k], 'joint_scopes.' + k) for k in
            ('normalization', 'calibration', 'revision', 'covariance_scope', 'model_scope')}
        compatible = admissibility['effective_value']
        for k in ('normalization', 'calibration', 'revision'):
            if relations[k]['effective_value'] == 'conflicting': compatible = 'conflicting'
            elif relations[k]['effective_value'] == 'unknown' and compatible != 'conflicting': compatible = 'unknown'
        covariance = cp(scopes[('joint', i)]['whole_projection'])
        request = _requested(context, spec['variance_status'], spec['model_kind'], 'joint_scopes')
        joint_arms = {r: roster[(r, nomination['assignment'][r])] for r in shared.PRIMITIVE_ORDER}
        parsed, effective = _owner_projection(joint_arms, relationships, covariance, request,
            variance_scope=relations['covariance_scope']['effective_value'] in ('same', 'explicit_compatible', 'not_applicable'),
            model_scope=relations['model_scope']['effective_value'] in ('same', 'explicit_compatible', 'not_applicable'))
        joint_rows.append({'assignment_index': i, 'witnesses': admissibility['witnesses'] +
            [w for rel in relations.values() for w in rel['witnesses']], 'effective_admissibility': compatible,
            'source_covariance': covariance, 'requested_model': request, 'effective_model': effective})
        if compatible == 'compatible':
            alternatives.append({'reading_assignment': cp(nomination['assignment']), 'scope_index': i,
                'source_covariance': covariance, 'requested_model': request, 'effective_model': effective, 'calculation_inputs': parsed})
    projection, basis = None, None
    effective = {'variance_status': 'unknown', 'model_kind': 'none', 'diagnostics': []}
    if not unresolved:
        matching = next((a for a in alternatives if a['reading_assignment'] == assignment), None)
        if all(v is None for v in assignment.values()):
            projection, effective = _owner_projection(arms, relationships, base_covariance, requested,
                model_scope=all(d['model_state'] == 'original_source_model' for d in decisions if d['state'] == 'ready'))
            basis = {'reading_assignment': cp(assignment), 'covariance_scope': 'base', 'scope_index': None,
                'reconciled_roles': [d['role'] for d in decisions if d['state'] == 'ready']}
        elif matching:
            projection, effective = cp(matching['calculation_inputs']), cp(matching['effective_model'])
            basis = {'reading_assignment': cp(assignment), 'covariance_scope': 'joint', 'scope_index': matching['scope_index'],
                'reconciled_roles': [d['role'] for d in decisions if d['state'] == 'ready']}
        else:
            unresolved = [r for r, key in assignment.items() if key is not None]
    partial, partial_state = None, 'not_required'
    if projection is None:
        masked_arms = {r: cp(dict(a)) if a is not None else None for r, a in arms.items()}
        partial_state = 'ready'
        for role in unresolved:
            members = [(_selector(role), arms[role])] + [(s, a) for s, a in companion_arms if s['role'] == role]
            mask, state = _group_mask(role, members)
            if state != 'ready': partial_state = state; break
            masked_arms[role]['calculation_operand'] = mask
        if partial_state == 'ready':
            partial, unused_effective = _owner_projection(masked_arms, relationships, base_covariance, requested, model_scope=False)
    unknown_uncertainty = {'statistic': 'unknown', 'magnitude': None, 'interval': None, 'confidence_level': None,
        'count': None, 'repetition_basis': 'unknown', 'estimate_basis': 'unknown'}
    local_readings = []
    for (role, key), arm in roster.items():
        local_readings.append({'reading': _selector(role, key), 'arm': cp(arm['calculation_operand']) if arm else None,
            'reported_uncertainty': cp(arm['reported_uncertainty']['canonical']) if arm else cp(unknown_uncertainty),
            'source_kind': arm['selection']['source_kind'] if arm else None,
            'measurement_method': 'graph' if arm and arm['graph_details'] else 'text' if arm and arm['selection']['measurement'] else 'not_selected'})
    documents, source_indices = [], {}
    for scope in covariance_scopes:
        document = scope['document']
        if document is not None and document['source_ref'] not in source_indices:
            source_indices[document['source_ref']] = len(documents); documents.append(cp(document))
    pairs = []
    for i, pair in enumerate(selected['local_pair_assignments']):
        scope = scopes[('local', i)]
        document = scope['document']
        admissibility = _relation(context, pair['admissibility'], 'local_pair_assignments.admissibility')
        scope_relation = _relation(context, pair['scope'], 'local_pair_assignments.scope')
        bindings = [b['binding'] for b in scope['bindings']]
        variance = shared._interpretation(context, pair['variance_status'], 'local_pair_assignments.variance_status')['effective_value']
        pairs.append({'pair_key': pair['pair_key'], 'condition': pair['condition'], 'protein': cp(pair['protein']), 'control': cp(pair['control']),
            'target': shared._relationships_inputs(relationships)[pair['condition'] + '_target'],
            'control_application': relationships[pair['condition'] + '_control_application']['effective_value'],
            'joint_admissibility': admissibility['effective_value'], 'scope_state': scope_relation['effective_value'],
            'covariance_index': source_indices[document['source_ref']] if document else None,
            'protein_binding': cp(bindings[0]) if document else None, 'control_binding': cp(bindings[1]) if document else None,
            'variance_status': variance})
    result = {'version': 'controlled_response_source_extraction_v3', 'selection': cp(selected), 'sources': cp(context.roster),
        'images': cp(context.images), 'arms': {r: cp(dict(a)) if a else None for r, a in arms.items()},
        'relationships': relationships, 'covariance': base_covariance, 'requested_model': requested, 'effective_model': effective,
        'calculation_inputs': projection, 'representation_reconciliations': shared._representations(arms), 'diagnostics': [],
        'implementation_dependencies': {'reader_contract_version': 'controlled_response_source_extraction_v3',
            'calculator_contract_version': 'controlled_response_owner_inputs_v2', 'expected_module_fingerprints': _dependencies()},
        'companion_extractions': [{'reading_key': s['reading_key'], 'primary_role': s['role'], 'reading': cp(dict(a))} for s, a in companion_arms],
        'projection_status': 'ready' if projection is not None else 'unresolved_active_reconciliation', 'final_projection_basis': basis,
        'reconciliation_decisions': decisions, 'joint_scope_extractions': joint_rows, 'alternative_inputs': alternatives,
        'partial_calculation_inputs': partial, 'partial_projection_state': partial_state,
        'component_local_inputs': {'version': 'controlled_response_local_inputs_v1', 'readings': local_readings, 'pairs': pairs, 'source_covariances': documents},
        'covariance_document_scopes': [{'scope': cp(s['scope']), 'document': cp(s['document'])} for s in covariance_scopes]}
    for record in result['representation_reconciliations']:
        for reading in record['readings']: reading['reading_key'] = None
    result['diagnostics'] = shared._unique_diagnostics(result, stable=True)
    Draft202012Validator(_extraction_schema()).validate(result)
    json.dumps(result, allow_nan=False)
    return cp(result)


def validate_controlled_response_v3_extraction(arguments, extraction):
    def check(selector, selected, measurement, *, source_records, image_records):
        if selected and selected['kind'] == 'linear_bar':
            arm = (extraction['arms'][selector['role']] if selector['reading_key'] is None else
                next(row['reading'] for row in extraction['companion_extractions'] if row['primary_role'] == selector['role'] and row['reading_key'] == selector['reading_key']))
            if arm['graph_details'] is None or arm['graph_details']['measurement'] != measurement:
                shared._fail('saved_graph_measurement_mismatch', 'measurement')
            return v2._validate_graph(selected, arm['graph_details'], sources={(s['source_ref'], s['representation']): s for s in source_records},
                images=image_records, request=arguments)
        return v2._validate_measurement(selected, measurement, source_records=source_records, image_records=image_records)
    return shared.validate_controlled_response_saved_science(arguments, extraction, measurement_checks=check)


__all__ = ['controlled_response_v3_arguments_schema', 'validate_controlled_response_v3_selection',
    'read_controlled_response_v3_inputs', 'validate_controlled_response_v3_extraction']
