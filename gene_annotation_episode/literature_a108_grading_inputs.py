"""Authenticate organism-context observations for A108 subscoring graders.

The episode supplies the biological interpretation and exact source selections.
The reader supplies witnessed statements and canonical observation identity;
neither the operation nor its caller supplies numerical evidence scores.
"""
from copy import deepcopy

from .domain import REF, ContractError, validate_schema
from .literature_a108_grading import INPUT_VERSION, grading_input_schema
from .literature_a108_sources import ContextSources, source_selector_schema


def grading_population_schema(*, legacy=False):
    schema = deepcopy(grading_input_schema())
    props = schema['properties']
    props.pop('version')
    schema['required'].remove('version')
    props['source_ref'] = {**deepcopy(REF), 'x-reference-namespace': 'source'}
    selections = {'type': 'array', 'items': source_selector_schema()}
    props['target_identity_evidence'] = deepcopy(selections)
    props['target_identity_evidence']['description'] = (
        'Exact source selections for target organism/strain/sample identity when established here. '
        'An explicit caller organism/strain assignment is a valid source for the assigned '
        'target context; unspecified sample conditions or locus do not invalidate that identity. '
        'It is not itself positive biological evidence or proof of the protein\'s provenance. '
        'May be empty when target_identity.support_refs are already received typed identity/context '
        'records; those records are authenticated independently. Source presence does not establish identity.')
    schema['required'].extend(('source_ref', 'target_identity_evidence'))
    observation = props['observations']['items']
    for name in ('original_observation_key', 'source_refs', 'measurement_keys'):
        observation['properties'].pop(name)
        observation['required'].remove(name)
    observation['properties']['original_observation_ref'] = {
        **deepcopy(REF), 'x-reference-namespace': 'reference',
        'description': (
            'The source-anchored reference for this distinct original biological observation: '
            'reference_type literature_result, or assay for an actual original experimental grouping. '
            'Its label and contexts identify the observation, not the publication as a whole; '
            'distinct observations within one paper use distinct references. Ordinary physiology '
            'prose uses literature_result and needs no assay entity. '
            'Its original exact source anchor is part of count identity: matching labels at '
            'different source spans do not establish the same original observation. '
            'Reuse this reference for repeated paper/database representations. An observation or '
            'assessment wrapper is evidence, not another identity for counting the original result.')}
    observation['properties']['evidence'] = {**deepcopy(selections), 'minItems': 1}
    observation['properties']['origin_link_evidence'] = deepcopy(selections)
    observation['required'].extend(('evidence', 'origin_link_evidence'))
    return schema


def _require_record(read_record, reference, kinds=None):
    record = read_record(reference)
    if kinds is not None and record.get('record_type') not in kinds:
        raise ContractError('a108_grading_record_type_mismatch')
    return record


def read_grading_inputs(arguments, *, read_source, read_record,
                        canonical_observation, retain_selection=None, read_cells=None):
    """Return only the numerical grader's typed, authenticated input object.

``canonical_observation`` is repository-owned and resolves original identities
using retained source/claim semantics. It returns key and original source ref.
Source-to-original publication equivalence is likewise repository-owned; an
explicit cross-source link remains a witnessed scientific interpretation.
"""
    validate_schema(arguments, grading_population_schema())
    args = deepcopy(arguments)
    _require_record(read_record, args['source_ref'], {'source'})
    _require_record(read_record, args['assertion_ref'], {'hypothesis'})
    if args['target_context_ref'] is not None:
        _require_record(read_record, args['target_context_ref'], {'context'})
    for reference in args['target_identity']['support_refs']:
        _require_record(read_record, reference)
    sources = ContextSources(read_source, read_record)
    target_evidence = [sources.select(item) for item in args.pop('target_identity_evidence')]
    if retain_selection is not None:
        for item in target_evidence:
            retain_selection({'role': 'target_identity', **item})
    primary = args.pop('source_ref')
    for index, observation in enumerate(args['observations']):
        _require_record(read_record, observation['context_claim_ref'], {'hypothesis'})
        _require_record(read_record, observation['source_subject_ref'],
            {'input', 'read_subject', 'reference', 'feature', 'product', 'context'})
        if observation['source_context_ref'] is not None:
            _require_record(read_record, observation['source_context_ref'], {'context'})
        original = _require_record(read_record, observation['original_observation_ref'],
            {'reference'})
        if original.get('reference_type') not in {'literature_result', 'assay'}:
            raise ContractError('a108_grading_original_observation_reference_type_mismatch')
        if not original.get('source_ref'):
            raise ContractError('a108_grading_original_observation_source_missing')
        for criterion in observation['criteria'].values():
            for reference in criterion['support_refs']:
                _require_record(read_record, reference)
        selected = [sources.select(item) for item in observation.pop('evidence')]
        links = [sources.select(item) for item in observation.pop('origin_link_evidence')]
        origin = canonical_observation(original, [item['source_ref'] for item in selected])
        if not origin['source_matches'] and not links:
            raise ContractError('a108_grading_original_observation_link_unwitnessed')
        if origin['source_ref'] is not None:
            _require_record(read_record, origin['source_ref'], {'source'})
        observation['original_observation_key'] = origin['key']
        observation['source_refs'] = list(dict.fromkeys([
            *[item['source_ref'] for item in selected + links],
            *([origin['source_ref']] if origin['source_ref'] is not None else []), primary]))
        # A quoted phenotype and its representations are an observation unit,
        # not extra quantitative measurement rows created by this source reader.
        observation['measurement_keys'] = []
        observation['qualifications'] = list(dict.fromkeys([
            *observation['qualifications'],
            *[qualification for item in selected + links for qualification in item['qualifications']]]))
        if all(item['identity_only'] for item in selected):
            observation['origin'] = 'annotation_lead'
            observation['qualifications'].append('identity_metadata_is_not_a_contextual_biological_observation')
        if not origin['source_matches']:
            observation['qualifications'].append('cross_source_original_observation_link_is_witnessed_interpretation')
        if retain_selection is not None:
            for role, items in (('observation', selected), ('original_observation_link', links)):
                for item in items:
                    retain_selection({'role': role, 'observation_index': index, **item})
    args['version'] = INPUT_VERSION
    validate_schema(args, grading_input_schema())
    return args


__all__ = ['grading_population_schema', 'read_grading_inputs']
