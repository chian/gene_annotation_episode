"""Purpose-specific A108 assessments of organism and sample-context evidence.

The source adapter authenticates observations and their original identities.
An episode assesses the scientific connection using the selected grader's
criteria. Counts are calculated from those assessed observation sets; criterion
labels are never converted into numerical strength weights.
"""
from gene_annotation_episode.episodic_workflow.root.a106.domain import obj
UNIT = 'distinct_contextual_observations'
COMPONENTS = ('support_count', 'conflict_count', 'overlap_count', 'evidence_amount', 'net_support', 'unresolved_count')
DOMAIN_BY_TYPE = {'physiology_resource_response': 'physiology', 'physiology_metabolic_observation': 'physiology', 'environment_ph': 'environment', 'environment_temperature': 'environment', 'environment_oxygen_redox': 'environment', 'environment_salinity_water': 'environment', 'substrate_availability': 'availability', 'cofactor_availability': 'availability', 'localization_microscopy': 'localization', 'localization_fractionation': 'localization', 'localization_curated_observation': 'localization'}
GRADER_TYPES = tuple(DOMAIN_BY_TYPE)
DOMAINS = tuple(dict.fromkeys(DOMAIN_BY_TYPE.values()))
ORIGINS = ('organism_physiology_report', 'observed_phenotype', 'recorded_sample_condition', 'curated_observation', 'prediction', 'annotation_lead')
RELATIONS = ('support', 'conflict', 'unresolved')
TARGET_RELATIONSHIPS = ('direct', 'qualified_transfer', 'conditional', 'unknown')

def reference_schema(namespace=None, nullable=False):
    result = {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference'}
    if namespace is not None:
        result['x-reference-namespace'] = namespace
    return result

def strings_schema():
    return {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}

def references_schema(namespace=None):
    return {'type': 'array', 'items': reference_schema(namespace), 'uniqueItems': True}

def relation_schema():
    return obj({'original_observation_key': {'type': 'string', 'minLength': 1}, 'original_observation_ref': reference_schema(), 'context_claim_ref': reference_schema('hypothesis'), 'source_subject_ref': reference_schema(), 'source_context_ref': reference_schema('context', True), 'origin': {'enum': list(ORIGINS)}, 'target_relationship': {'enum': list(TARGET_RELATIONSHIPS)}, 'requested_relation': {'enum': list(RELATIONS)}, 'relation': {'enum': list(RELATIONS)}, 'source_refs': references_schema('source'), 'measurement_keys': strings_schema(), 'qualifications': strings_schema(), 'reasons': strings_schema()})

def observation_sets_schema():
    return obj({name: strings_schema() for name in RELATIONS})

def missing_inputs_schema():
    return {'type': 'array', 'items': obj({'original_observation_key': {'type': 'string', 'minLength': 1}, 'context_claim_ref': reference_schema('hypothesis'), 'reasons': strings_schema()})}

def grading_cell_schema():
    return obj({'component': {'enum': list(COMPONENTS)}, 'domain': {'enum': list(DOMAINS)}, 'value': {'type': ['integer', 'null']}, 'available_value': {'type': ['integer', 'null']}, 'status': {'enum': ['populated', 'conditional', 'partial', 'unavailable']}, 'unit': {'const': UNIT}, 'observation_sets': observation_sets_schema(), 'observation_refs': references_schema(), 'relation_refs': references_schema('hypothesis'), 'source_subject_refs': references_schema(), 'source_context_refs': references_schema('context'), 'source_refs': references_schema('source'), 'measurement_keys': strings_schema(), 'relations': {'type': 'array', 'items': relation_schema()}, 'qualifications': strings_schema(), 'missing_inputs': missing_inputs_schema(), 'formula': {'type': 'string'}, 'meaning': {'type': 'string'}})
