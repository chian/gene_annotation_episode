"""Purpose-specific A108 assessments of organism and sample-context evidence.

The source adapter authenticates observations and their original identities.
An episode assesses the scientific connection using the selected grader's
criteria. Counts are calculated from those assessed observation sets; criterion
labels are never converted into numerical strength weights.
"""
from copy import deepcopy

from .domain import ContractError, obj, validate_schema

INPUT_VERSION = 'a108_context_observation_inputs_v1'
VERSION = 'a108_context_observation_sheet_v1'
SCOPE = 'a108_organism_context_observations'
UNIT = 'distinct_contextual_observations'
COMPONENTS = ('support_count', 'conflict_count', 'overlap_count',
              'evidence_amount', 'net_support', 'unresolved_count')
DOMAIN_BY_TYPE = {
    'physiology_resource_response': 'physiology',
    'physiology_metabolic_observation': 'physiology',
    'environment_ph': 'environment',
    'environment_temperature': 'environment',
    'environment_oxygen_redox': 'environment',
    'environment_salinity_water': 'environment',
    'substrate_availability': 'availability',
    'cofactor_availability': 'availability',
    'localization_microscopy': 'localization',
    'localization_fractionation': 'localization',
    'localization_curated_observation': 'localization',
}
GRADER_TYPES = tuple(DOMAIN_BY_TYPE)
DOMAINS = tuple(dict.fromkeys(DOMAIN_BY_TYPE.values()))
ORIGINS = ('organism_physiology_report', 'observed_phenotype',
           'recorded_sample_condition', 'curated_observation',
           'prediction', 'annotation_lead')
RELATIONS = ('support', 'conflict', 'unresolved')
TARGET_RELATIONSHIPS = ('direct', 'qualified_transfer', 'conditional', 'unknown')

# These common identities are prerequisites, not scored checklist items.
COMMON_CRITERIA = ('source_subject_identity', 'original_observation_identity',
                   'context_applicability', 'function_context_connection')
SPECIFIC_CRITERIA = {
    'physiology_resource_response': (
        'resource_role', 'response_endpoint', 'culture_circumstance', 'response_interpretation'),
    'physiology_metabolic_observation': (
        'chemical_process_identity', 'organism_metabolic_mode', 'metabolic_observation_meaning'),
    'environment_ph': ('ph_circumstance', 'ph_compartment', 'ph_function_relation'),
    'environment_temperature': (
        'thermal_circumstance', 'thermal_duration_state', 'activity_stability_distinction'),
    'environment_oxygen_redox': (
        'oxygen_redox_property', 'oxygen_redox_exposure', 'oxygen_redox_function_relation'),
    'environment_salinity_water': (
        'ionic_water_property', 'ionic_water_compartment', 'ionic_water_function_relation'),
    'substrate_availability': (
        'substrate_chemical_identity', 'substrate_presence_supply', 'substrate_access_scope'),
    'cofactor_availability': (
        'cofactor_active_form', 'cofactor_supply_route', 'cofactor_access_scope'),
    'localization_microscopy': (
        'microscopy_molecule_construct', 'microscopy_location_assignment',
        'microscopy_resolution', 'microscopy_spatial_relation'),
    'localization_fractionation': (
        'fractionation_molecule_preparation', 'fraction_marker_assignment',
        'fractionation_distribution', 'fractionation_spatial_relation'),
    'localization_curated_observation': (
        'curated_molecule_identity', 'curated_evidence_origin',
        'curated_location_meaning', 'curated_spatial_relation'),
}
CRITERIA_BY_TYPE = {kind: (*COMMON_CRITERIA, *specific, 'conflict_scope')
                    for kind, specific in SPECIFIC_CRITERIA.items()}
CRITERION_QUESTIONS = {
    'source_subject_identity': 'Does the source identify the organism, strain, sample or molecular subject that actually has this observed property?',
    'original_observation_identity': 'Is this the identified original biological observation, with repeated reports, derived descriptions and technical replicates kept together?',
    'context_applicability': 'Do received target context and source evidence establish this direct, qualified-transfer or condition-specific relationship, at its stated organism/strain/sample scope?',
    'function_context_connection': 'Does this observed biological property bear on the proposed function in the declared contextual question, without treating physiological fit as identification of the individual protein?',
    'conflict_scope': 'For a conflicting relation, does the observation contradict the proposed role within its actual scope, rather than reporting an unexamined condition, missing source, alternative route or nonspecific failure?',
    'resource_role': 'Is the actual resource and its physiological role identified, retaining sole versus supplemental nutrition and chemical form?',
    'response_endpoint': 'Does the source establish the stated growth, survival, yield or other organism-level response without silently converting one endpoint into another?',
    'culture_circumstance': 'Are the relevant organism/culture/state circumstances established at the resolution of this physiological claim?',
    'response_interpretation': 'Does the documented response support this resource-use interpretation, retaining nutrient mixtures and other causes of failure to grow?',
    'chemical_process_identity': 'Are the chemical substrate, donor, acceptor or product identities needed for this specific physiological statement established?',
    'organism_metabolic_mode': 'Does the source establish the organism-level respiratory, consumption, production or assimilation behavior, including valid documented physiology without requiring a new assay?',
    'metabolic_observation_meaning': 'Does the interpretation preserve the source distinction between metabolic mode, uptake, disappearance, assimilation, pool and flux, and any community or alternative-route qualifications?',
    'ph_circumstance': 'Is this an actual reported pH or pH circumstance, with measured, culture-set and organism-trait meanings kept distinct?',
    'ph_compartment': 'Does the selected pH concern the relevant medium, sample or cellular compartment rather than assuming external and intracellular pH are equal?',
    'ph_function_relation': 'Is the relation to the proposed role supported at this pH scope, without converting one assay pH or an optimum into exclusion elsewhere?',
    'thermal_circumstance': 'Does the observation establish the relevant growth, exposure or activity temperature rather than inferring the sample temperature from a taxon label?',
    'thermal_duration_state': 'Does the stated thermal history, duration and physiological or molecular state support this particular comparison?',
    'activity_stability_distinction': 'Does the comparison retain the distinction between growth temperature, activity temperature, stability and melting temperature?',
    'oxygen_redox_property': 'Is the actual oxygen or redox property established, keeping dissolved oxygen, gas atmosphere, reported anaerobic state and electrode potential distinct?',
    'oxygen_redox_exposure': 'Does the documented location/state/exposure support the particular contextual claim without extending it to every time or compartment?',
    'oxygen_redox_function_relation': 'Does evidence establish the proposed role\'s relevant oxygen requirement, sensitivity or redox relationship, beyond a guessed implication of its name?',
    'ionic_water_property': 'Is the actual ionic or water property identified, preserving salt concentration, ionic strength, osmolarity and water activity as different quantities?',
    'ionic_water_compartment': 'Does the observation concern the relevant sample/medium/compartment and state rather than a habitat label substituted for its measurement?',
    'ionic_water_function_relation': 'Is the proposed role connected to this property without unsupported conversions or equating whole-organism tolerance with molecular activity?',
    'substrate_chemical_identity': 'Does the observation concern the actual substrate chemical form required by the proposed role, rather than an analogue or unspecified related substance?',
    'substrate_presence_supply': 'Does the source establish the selected presence, supply, production or absence claim, distinguishing endogenous observation, recorded medium supply and missing database entries?',
    'substrate_access_scope': 'Does the selected presence or access claim stay within the observed sample/compartment and documented transport relationship, retaining free-versus-total and mutant-versus-target limitations?',
    'cofactor_active_form': 'Does the observation identify the relevant cofactor and active chemical/oxidation form, without equating total metal or inactive precursor with active cofactor?',
    'cofactor_supply_route': 'Does the documented observation establish this endogenous synthesis, environmental supply, import, salvage or recycling relationship rather than merely an annotated gene?',
    'cofactor_access_scope': 'Does the observed cofactor relationship apply at the claimed compartment and physiological state, with accessible pool and missing transport qualifications retained?',
    'microscopy_molecule_construct': 'Is the observed molecule/construct/tag and its actual organism or expression host established?',
    'microscopy_location_assignment': 'Does the source-supported marker/background interpretation establish the selected observed location?',
    'microscopy_resolution': 'Does the spatial interpretation stay within the actual optical resolution and tag/background qualifications?',
    'microscopy_spatial_relation': 'Does the observed location bear on the proposed role\'s required access, without treating whole-cell detection as colocalization or colocalization as binding?',
    'fractionation_molecule_preparation': 'Are the actual molecule, organism and preparation represented by this distribution established?',
    'fraction_marker_assignment': 'Does the source support the fraction-to-compartment assignment with its actual marker, contamination and recovery qualifications?',
    'fractionation_distribution': 'Does this represent the original distribution observation, keeping its fractions, normalized profiles and repeated views together?',
    'fractionation_spatial_relation': 'Does the source-qualified distribution bear on the proposed role\'s required compartment or access without implying physical binding?',
    'curated_molecule_identity': 'Does the native record identify the actual molecule and organism, including any transfer from a characterized homolog?',
    'curated_evidence_origin': 'Does the selected native evidence provenance support an observed localization, rather than a prediction or propagation of the annotation being evaluated?',
    'curated_location_meaning': 'Are the actual location term, record version and evidence qualifiers preserved?',
    'curated_spatial_relation': 'Does that documented location bear on the proposed role\'s required spatial relationship in the actual target context?',
}
FORMULAS = {
    'support_count': '|support observation set|',
    'conflict_count': '|conflict observation set|',
    'overlap_count': '|support intersect conflict|',
    'evidence_amount': '|support union conflict|',
    'net_support': '|support| - |conflict|',
    'unresolved_count': '|unresolved observation set|',
}
MEANINGS = {
    'support_count': 'Distinct original observations with assessed supporting contextual relations.',
    'conflict_count': 'Distinct original observations with assessed conflicting contextual relations.',
    'overlap_count': 'Original observations that support one selected relation and conflict with another.',
    'evidence_amount': 'Distinct original observations with assessed support or conflict, counted once across relations.',
    'net_support': 'Supporting minus conflicting original-observation count; separate from the amount of evidence.',
    'unresolved_count': 'Original observations whose selected contextual connection is unresolved; not positive evidence credit.',
}


def reference_schema(namespace=None, nullable=False):
    result = {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference'}
    if namespace is not None:
        result['x-reference-namespace'] = namespace
    return result


def strings_schema():
    return {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}


def references_schema(namespace=None):
    return {'type': 'array', 'items': reference_schema(namespace), 'uniqueItems': True}


def interpretation_schema():
    return obj({'status': {'enum': ['supported', 'unknown', 'conflicting', 'not_applicable']},
                'support_refs': references_schema()})


def observation_schema():
    return obj({
        'original_observation_key': {'type': 'string', 'minLength': 1},
        'original_observation_ref': reference_schema(),
        'context_claim_ref': reference_schema('hypothesis'),
        'source_subject_ref': reference_schema(),
        'source_context_ref': reference_schema('context', True),
        'source_refs': references_schema('source'),
        'measurement_keys': strings_schema(),
        'origin': {'enum': list(ORIGINS)},
        'target_relationship': {'enum': list(TARGET_RELATIONSHIPS), 'description':
            'Relationship of the observed source organism/conditions to the assigned target '
            'organism/context, at the stated species, strain or sample resolution. This is '
            'a contextual comparison, not proof of the input protein\'s molecular provenance.'},
        'relation': {'enum': list(RELATIONS)},
        'criteria': {'type': 'object', 'properties': {
            name: {**interpretation_schema(), 'description': question}
            for name, question in CRITERION_QUESTIONS.items()},
            'additionalProperties': False},
        'qualifications': strings_schema(),
    })


def grading_input_schema():
    schema = obj({'version': {'const': INPUT_VERSION},
        'assertion_ref': reference_schema('hypothesis'),
        'target_context_ref': {**reference_schema('context', True), 'description':
            'Source-bound context record for the organism/strain and any conditions being '
            'assessed. Use the explicit caller-supplied context when provided. Unknown sample '
            'conditions or genomic locus may remain unknown within that known organism context. '
            'Null means the organism/context itself is unestablished, not merely that the '
            'individual protein has not been experimentally assigned to a genomic copy.'},
        'target_identity': {**interpretation_schema(), 'description':
            'Is the identity of the organism/context under assessment established at its '
            'declared resolution by received context records or an explicit caller assignment? '
            'A witnessed caller assignment can establish the assigned context; it does not '
            'supply a positive biological observation. This criterion does not require '
            'experimental proof of this protein\'s origin or molecular function. Preserve '
            'conditional identity and genuinely missing organism information.'},
        'grader_type': {'enum': list(GRADER_TYPES)},
        'observations': {'type': 'array', 'items': observation_schema()}})
    schema['allOf'] = []
    for kind, criteria in CRITERIA_BY_TYPE.items():
        observation_rule = {'properties': {
            'criteria': {'propertyNames': {'enum': list(criteria)}}}}
        consequence = {'properties': {'observations': {'items': observation_rule}}}
        schema['allOf'].append({
            'if': {'properties': {'grader_type': {'const': kind}}},
            'then': consequence})
    return schema


def relation_schema():
    return obj({
        'original_observation_key': {'type': 'string', 'minLength': 1},
        'original_observation_ref': reference_schema(),
        'context_claim_ref': reference_schema('hypothesis'),
        'source_subject_ref': reference_schema(),
        'source_context_ref': reference_schema('context', True),
        'origin': {'enum': list(ORIGINS)},
        'target_relationship': {'enum': list(TARGET_RELATIONSHIPS)},
        'requested_relation': {'enum': list(RELATIONS)},
        'relation': {'enum': list(RELATIONS)},
        'source_refs': references_schema('source'),
        'measurement_keys': strings_schema(),
        'qualifications': strings_schema(),
        'reasons': strings_schema(),
    })


def observation_sets_schema():
    return obj({name: strings_schema() for name in RELATIONS})


def missing_inputs_schema():
    return {'type': 'array', 'items': obj({
        'original_observation_key': {'type': 'string', 'minLength': 1},
        'context_claim_ref': reference_schema('hypothesis'), 'reasons': strings_schema()})}


def grading_cell_schema():
    return obj({'component': {'enum': list(COMPONENTS)},
        'domain': {'enum': list(DOMAINS)},
        'value': {'type': ['integer', 'null']},
        'available_value': {'type': ['integer', 'null']},
        'status': {'enum': ['populated', 'conditional', 'partial', 'unavailable']},
        'unit': {'const': UNIT},
        'observation_sets': observation_sets_schema(),
        'observation_refs': references_schema(),
        'relation_refs': references_schema('hypothesis'),
        'source_subject_refs': references_schema(),
        'source_context_refs': references_schema('context'),
        'source_refs': references_schema('source'),
        'measurement_keys': strings_schema(),
        'relations': {'type': 'array', 'items': relation_schema()},
        'qualifications': strings_schema(),
        'missing_inputs': missing_inputs_schema(),
        'formula': {'type': 'string'}, 'meaning': {'type': 'string'}})


def grading_sheet_schema():
    return obj({'version': {'const': VERSION}, 'axis': {'const': 'A108'},
        'evaluation_scope': {'const': SCOPE},
        'assertion_ref': reference_schema('hypothesis'),
        'target_context_ref': reference_schema('context', True),
        'grader_type': {'enum': list(GRADER_TYPES)},
        'domain': {'enum': list(DOMAINS)},
        'cells': obj({name: grading_cell_schema() for name in COMPONENTS}),
        'relations': {'type': 'array', 'items': relation_schema()},
        'annotation_credit': {'type': 'null'}})


def count_sets(sets):
    """Exact set cardinalities, shared by subscoring and main sheets."""
    support, conflict, unresolved = (set(sets[name]) for name in RELATIONS)
    return dict(support_count=len(support), conflict_count=len(conflict),
        overlap_count=len(support & conflict), evidence_amount=len(support | conflict),
        net_support=len(support) - len(conflict), unresolved_count=len(unresolved))


def sets_from_relations(relations):
    return {name: sorted({row['original_observation_key'] for row in relations
                         if row['relation'] == name}) for name in RELATIONS}


def relation_metadata(relations):
    """Only the original identities needed to interpret the selected result."""
    def unique(values):
        return list(dict.fromkeys(values))
    return {
        'observation_refs': unique(row['original_observation_ref'] for row in relations),
        'relation_refs': unique(row['context_claim_ref'] for row in relations),
        'source_subject_refs': unique(row['source_subject_ref'] for row in relations),
        'source_context_refs': unique(row['source_context_ref'] for row in relations
                                      if row['source_context_ref'] is not None),
        'source_refs': unique(ref for row in relations for ref in row['source_refs']),
        'measurement_keys': unique(key for row in relations for key in row['measurement_keys']),
        'qualifications': unique(q for row in relations for q in row['qualifications']),
    }


def _assess_observation(observation, grader_type, target_known):
    reasons = []
    if not target_known:
        reasons.append('target_organism_context_unestablished')
    if not observation['source_refs']:
        reasons.append('source_observation_unwitnessed')
    if observation['origin'] in ('prediction', 'annotation_lead'):
        reasons.append('origin_is_not_observed_context_evidence')
    if observation['target_relationship'] == 'unknown':
        reasons.append('target_context_relationship_unknown')
    required = (*COMMON_CRITERIA, *SPECIFIC_CRITERIA[grader_type])
    if observation['relation'] == 'conflict':
        required = (*required, 'conflict_scope')
    for name in required:
        criterion = observation['criteria'].get(name)
        if criterion is None:
            reasons.append('criterion_missing:' + name)
        elif criterion['status'] != 'supported':
            reasons.append('criterion_' + criterion['status'] + ':' + name)
        elif not criterion['support_refs']:
            reasons.append('criterion_unwitnessed:' + name)
    if observation['relation'] == 'unresolved':
        reasons.append('source_context_connection_unresolved')
    row = {name: deepcopy(observation[name]) for name in (
        'original_observation_key', 'original_observation_ref', 'context_claim_ref',
        'source_subject_ref', 'source_context_ref', 'origin', 'target_relationship',
        'source_refs', 'measurement_keys', 'qualifications')}
    row.update(requested_relation=observation['relation'],
        relation='unresolved' if reasons else observation['relation'], reasons=reasons)
    return row


def _component_relations(component, relations, sets):
    if component == 'evidence_amount':
        return deepcopy(relations)
    if component == 'overlap_count':
        overlap = set(sets['support']) & set(sets['conflict'])
        return [deepcopy(row) for row in relations
                if row['original_observation_key'] in overlap and row['relation'] != 'unresolved']
    selected = {'support_count': {'support'}, 'conflict_count': {'conflict'},
                'net_support': {'support', 'conflict'}, 'unresolved_count': {'unresolved'}}[component]
    return [deepcopy(row) for row in relations if row['relation'] in selected]


def grade_context_evidence(inputs):
    """Assess each selected contextual relation and compute its observation counts.

    All scientific judgments remain explicit, source-supported inputs. There is
    no inference of biological truth from reference possession or type checking.
    """
    validate_schema(inputs, grading_input_schema())
    args = deepcopy(inputs)
    target_known = (args['target_context_ref'] is not None
        and args['target_identity']['status'] == 'supported'
        and bool(args['target_identity']['support_refs']))
    relations, selected = [], set()
    for observation in args['observations']:
        key = (observation['original_observation_key'], observation['context_claim_ref'])
        if key in selected:
            raise ContractError('a108_duplicate_observation_relation')
        selected.add(key)
        relations.append(_assess_observation(observation, args['grader_type'], target_known))
    sets = sets_from_relations(relations)
    values = count_sets(sets)
    missing = [{'original_observation_key': row['original_observation_key'],
                'context_claim_ref': row['context_claim_ref'], 'reasons': row['reasons']}
               for row in relations if row['relation'] == 'unresolved']
    status = ('unavailable' if not relations else 'partial' if missing else
              'conditional' if any(row['target_relationship'] != 'direct' for row in relations)
              else 'populated')
    cells = {}
    for component in COMPONENTS:
        delivered = _component_relations(component, relations, sets)
        value = values[component] if relations else None
        cells[component] = {'component': component, 'domain': DOMAIN_BY_TYPE[args['grader_type']],
            'value': value, 'available_value': value, 'status': status, 'unit': UNIT,
            'observation_sets': sets_from_relations(delivered),
            **relation_metadata(delivered), 'relations': delivered,
            'missing_inputs': deepcopy(missing),
            'formula': FORMULAS[component], 'meaning': MEANINGS[component]}
    result = {'version': VERSION, 'axis': 'A108', 'evaluation_scope': SCOPE,
        'assertion_ref': args['assertion_ref'], 'target_context_ref': args['target_context_ref'],
        'grader_type': args['grader_type'], 'domain': DOMAIN_BY_TYPE[args['grader_type']],
        'cells': cells, 'relations': relations, 'annotation_credit': None}
    validate_schema(result, grading_sheet_schema())
    return result


__all__ = ['INPUT_VERSION', 'VERSION', 'SCOPE', 'UNIT', 'COMPONENTS', 'GRADER_TYPES',
    'DOMAINS', 'DOMAIN_BY_TYPE', 'ORIGINS', 'COMMON_CRITERIA', 'SPECIFIC_CRITERIA',
    'CRITERIA_BY_TYPE', 'CRITERION_QUESTIONS', 'RELATIONS', 'TARGET_RELATIONSHIPS',
    'reference_schema', 'references_schema', 'strings_schema', 'interpretation_schema',
    'observation_schema', 'observation_sets_schema', 'relation_schema',
    'missing_inputs_schema', 'grading_input_schema', 'grading_cell_schema',
    'grading_sheet_schema', 'grade_context_evidence', 'count_sets',
    'sets_from_relations', 'relation_metadata']
