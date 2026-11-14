"""Commit an A105/A108 interpretation and its selected graders as one action.

Acquisition and metadata preparation remain ordinary work. This boundary admits
no completed scientific interpretation without its purpose-specific sheet; it
does not select a grader, infer applicability, or alter iterator credit.
"""
from copy import deepcopy
from dataclasses import replace
import json
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError, canonical, obj, source_location_inputs, validate_schema
from gene_annotation_episode.episodic_workflow.root.a104.literature_assay_inputs import _Sources, _witness_schema
from gene_annotation_episode.episodic_workflow.root.a104.literature_experimental_contracts import ExperimentalContractError
SCIENTIFIC_SECTIONS = ('observations', 'assessments', 'annotation_updates', 'interpretation_accounts')
SCIENTIFIC_TYPES = {'observation', 'assessment', 'annotation', 'interpretation_account'}
ORIGINAL_RESULTS = {'literature_result', 'assay'}

def _requires_sheet(record):
    return record['record_type'] in SCIENTIFIC_TYPES or record.get('reference_type') in ORIGINAL_RESULTS

def action_schema(commit_schema, population_schema):
    commit_schema = deepcopy(commit_schema)
    assessment = commit_schema.get('properties', {}).get('assessments', {}).get('items', {})
    if 'investigation_finding' in assessment.get('properties', {}):
        assessment['required'] = list(dict.fromkeys([*assessment.get('required', ()), 'investigation_finding']))
    route = obj({'arguments': {'type': 'string', 'description': 'JSON encoding of the exact existing grader argument object. Same-action @aliases are permitted in reference positions. Preserve missing/null scientific operands. The host resolves aliases and validates this complete standalone schema before grading: ' + canonical(population_schema)}})
    processing = {'anyOf': [obj({'kind': {'const': 'graded'}, 'gradings': {'type': 'array', 'minItems': 1, 'items': route}}), obj({'kind': {'const': 'no_applicable_evidence'}, 'examined': {'type': 'array', 'minItems': 1, 'items': _witness_schema()}, 'reason': {'type': 'string', 'minLength': 1, 'description': 'Why the authenticated examined material contains no evidence applicable to the assigned axis/question. Missing grading inputs and access failures are not evidence absence.'}})]}
    processing['description'] = 'Required when interpreting examined evidence. Omit only for metadata preparation containing no original-result/assay references, observations, assessments, interpretation accounts or annotation conclusions. A no-applicable result contains no assessments or annotation conclusions; any retained raw observations must be anchored within its authenticated examined source spans.'
    return obj({'kind': {'type': 'string', 'const': 'reason'}, 'commit': deepcopy(commit_schema), 'evidence_processing': processing}, required=['kind', 'commit'])

def _resolve(value, aliases, reference_position=False):
    if reference_position and isinstance(value, str) and value.startswith('@'):
        if value[1:] not in aliases:
            raise ContractError('required_grading_unresolved_alias', detail={'reference': value})
        return aliases[value[1:]]
    if isinstance(value, dict):
        return {key: _resolve(child, aliases, key in ('ref', 'dependencies') or key.endswith('_ref') or key.endswith('_refs')) for key, child in value.items()}
    if isinstance(value, list):
        return [_resolve(child, aliases, reference_position) for child in value]
    return value

def _matches_grading(store, reference, arguments, *, contextual, linked_observations=()):
    """Bind a saved scientific record to this grader's actual observation/claim.

Use the existing original observation/experiment identity and the assessed
hypothesis; there is no second model-supplied list of these same links.
"""
    record = store.get(reference)
    if not _requires_sheet(record):
        return False
    claims = {arguments['assertion_ref']}
    if contextual:
        claims.update((item['context_claim_ref'] for item in arguments['observations']))
    if record['record_type'] in {'annotation', 'interpretation_account'}:
        interpretations = [item for group in record['coherent_sets'] for item in group['interpretations']]
        return bool(interpretations) and all((item['hypothesis_ref'] in claims and item['assessment_refs'] and all((_matches_grading(store, ref, arguments, contextual=contextual, linked_observations=linked_observations) for ref in item['assessment_refs'])) for item in interpretations))
    if record['record_type'] == 'assessment':
        if record['hypothesis_ref'] not in claims:
            return False
        if contextual and record['hypothesis_ref'] != arguments['assertion_ref']:
            arguments = {**arguments, 'observations': [item for item in arguments['observations'] if item['context_claim_ref'] == record['hypothesis_ref']]}
        return _matches_grading(store, record['observation_ref'], arguments, contextual=contextual, linked_observations=linked_observations)
    if record['record_type'] == 'reference':
        originals = [item['original_observation_ref'] for item in arguments['observations']] if contextual else [arguments['experiment_ref']]
        if reference in originals:
            return True
        if contextual or record.get('reference_type') != 'literature_result':
            return False
        anchor = record.get('anchor')
        if anchor is None:
            return False
        for observation_ref in linked_observations:
            observation = store.get(observation_ref)
            observation_anchor = observation.get('anchor')
            subjects = observation.get('source_subject_refs', [])
            if reference in subjects and arguments['experiment_ref'] in subjects and (record['source_ref'] == observation['source_ref']) and (observation_anchor is not None) and (anchor['source_ref'] == observation_anchor['source_ref']) and (anchor['artifact_ref'] == observation_anchor['artifact_ref']) and (observation_anchor['start'] <= anchor['start'] < anchor['end'] <= observation_anchor['end']) and _matches_grading(store, observation_ref, arguments, contextual=False):
                return True
        return False
    if record['record_type'] != 'observation':
        return False
    units = arguments['observations'] if contextual else [{'original_observation_ref': arguments['experiment_ref']}]
    linked = {*record.get('source_subject_refs', []), *record.get('subject_refs', []), *record.get('dependencies', [])}
    anchor = record.get('anchor')
    for unit in units:
        original_ref = unit['original_observation_ref']
        original = store.get(original_ref)
        original_anchor = original.get('anchor')
        sources = {arguments['source_ref'], original.get('source_ref')}
        for selection in [*unit.get('evidence', []), *unit.get('origin_link_evidence', [])]:
            sources.add(selection.get('source_ref', selection.get('witness', {}).get('source_ref')))
        if record['source_ref'] in sources and (original_ref in linked or (anchor is not None and anchor == original_anchor)):
            return True
    return False
