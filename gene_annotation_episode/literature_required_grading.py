"""Commit an A105/A108 interpretation and its selected graders as one action.

Acquisition and metadata preparation remain ordinary work. This boundary admits
no completed scientific interpretation without its purpose-specific sheet; it
does not select a grader, infer applicability, or alter iterator credit.
"""
from copy import deepcopy
from dataclasses import replace
import json

from .communication import plain
from .domain import ContractError, canonical, obj, source_location_inputs, validate_schema
from .literature_assay_inputs import _Sources, _witness_schema
from .literature_experimental_contracts import ExperimentalContractError


SCIENTIFIC_SECTIONS = ('observations', 'assessments', 'annotation_updates',
                       'interpretation_accounts')
SCIENTIFIC_TYPES = {'observation', 'assessment', 'annotation', 'interpretation_account'}
ORIGINAL_RESULTS = {'literature_result', 'assay'}


def _requires_sheet(record):
    return (record['record_type'] in SCIENTIFIC_TYPES
            or record.get('reference_type') in ORIGINAL_RESULTS)


def action_schema(commit_schema, population_schema):
    commit_schema = deepcopy(commit_schema)
    assessment = commit_schema.get('properties', {}).get('assessments', {}).get('items', {})
    if 'investigation_finding' in assessment.get('properties', {}):
        assessment['required'] = list(dict.fromkeys([
            *assessment.get('required', ()), 'investigation_finding']))
    route = obj({
        'arguments': {'type': 'string', 'description':
            'JSON encoding of the exact existing grader argument object. Same-action '
            '@aliases are permitted in reference positions. Preserve missing/null '
            'scientific operands. The host resolves aliases and validates this '
            'complete standalone schema before grading: ' + canonical(population_schema)},
    })
    processing = {'anyOf': [
        obj({'kind': {'const': 'graded'}, 'gradings': {
            'type': 'array', 'minItems': 1, 'items': route}}),
        obj({'kind': {'const': 'no_applicable_evidence'}, 'examined': {
            'type': 'array', 'minItems': 1, 'items': _witness_schema()},
            'reason': {'type': 'string', 'minLength': 1, 'description':
                'Why the authenticated examined material contains no evidence applicable '
                'to the assigned axis/question. Missing grading inputs and access failures '
                'are not evidence absence.'}}),
    ]}
    processing['description'] = (
        'Required when interpreting examined evidence. Omit only for metadata '
        'preparation containing no original-result/assay references, observations, '
        'assessments, interpretation accounts or annotation conclusions. A '
        'no-applicable result contains no assessments '
        'or annotation conclusions; any retained raw observations must be anchored '
        'within its authenticated examined source spans.')
    return obj({'kind': {'type': 'string', 'const': 'reason'},
        'commit': deepcopy(commit_schema), 'evidence_processing': processing},
        required=['kind', 'commit'])


def _resolve(value, aliases, reference_position=False):
    if reference_position and isinstance(value, str) and value.startswith('@'):
        if value[1:] not in aliases:
            raise ContractError('required_grading_unresolved_alias', detail={'reference': value})
        return aliases[value[1:]]
    if isinstance(value, dict):
        return {key: _resolve(child, aliases,
            key in ('ref', 'dependencies') or key.endswith('_ref') or key.endswith('_refs'))
            for key, child in value.items()}
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
        claims.update(item['context_claim_ref'] for item in arguments['observations'])
    if record['record_type'] in {'annotation', 'interpretation_account'}:
        interpretations = [item for group in record['coherent_sets']
                           for item in group['interpretations']]
        return bool(interpretations) and all(
            item['hypothesis_ref'] in claims
            and item['assessment_refs'] and all(_matches_grading(store, ref, arguments,
                contextual=contextual, linked_observations=linked_observations)
                for ref in item['assessment_refs'])
            for item in interpretations)
    if record['record_type'] == 'assessment':
        if record['hypothesis_ref'] not in claims:
            return False
        if contextual and record['hypothesis_ref'] != arguments['assertion_ref']:
            arguments = {**arguments, 'observations': [item for item in arguments['observations']
                if item['context_claim_ref'] == record['hypothesis_ref']]}
        return _matches_grading(store, record['observation_ref'], arguments,
            contextual=contextual, linked_observations=linked_observations)
    if record['record_type'] == 'reference':
        originals = ([item['original_observation_ref'] for item in arguments['observations']]
                     if contextual else [arguments['experiment_ref']])
        if reference in originals:
            return True
        # An A105 result can describe an outcome of the selected assay without
        # becoming another experiment. Follow the explicit, same-source
        # observation link and an authenticated span containing the result in
        # the same source artifact. The observation may also quote the result's
        # surrounding context. Merely
        # sharing a paper, a support ref or an anchor does not establish this
        # relationship. A108 original observations retain their own identities.
        if contextual or record.get('reference_type') != 'literature_result':
            return False
        anchor = record.get('anchor')
        if anchor is None:
            return False
        for observation_ref in linked_observations:
            observation = store.get(observation_ref)
            observation_anchor = observation.get('anchor')
            subjects = observation.get('source_subject_refs', [])
            if (reference in subjects and arguments['experiment_ref'] in subjects
                    and record['source_ref'] == observation['source_ref']
                    and observation_anchor is not None
                    and anchor['source_ref'] == observation_anchor['source_ref']
                    and anchor['artifact_ref'] == observation_anchor['artifact_ref']
                    and observation_anchor['start'] <= anchor['start']
                    < anchor['end'] <= observation_anchor['end']
                    and _matches_grading(store, observation_ref, arguments, contextual=False)):
                return True
        return False
    if record['record_type'] != 'observation':
        return False
    units = (arguments['observations'] if contextual else [
        {'original_observation_ref': arguments['experiment_ref']}])
    linked = {*record.get('source_subject_refs', []), *record.get('subject_refs', []),
              *record.get('dependencies', [])}
    anchor = record.get('anchor')
    for unit in units:
        original_ref = unit['original_observation_ref']
        original = store.get(original_ref)
        original_anchor = original.get('anchor')
        sources = {arguments['source_ref'], original.get('source_ref')}
        for selection in [*unit.get('evidence', []), *unit.get('origin_link_evidence', [])]:
            sources.add(selection.get('source_ref', selection.get('witness', {}).get('source_ref')))
        # An explicit original-result link or its exact authenticated anchor
        # identifies the experiment/observation; source identity alone does not.
        if (record['source_ref'] in sources
                and (original_ref in linked or anchor is not None and anchor == original_anchor)):
            return True
    return False


def execute(context, selection, operation_key, repository, *, authorize_source_access):
    """Save the interpretation and its sheets before ordinary credit projection."""
    store = repository.store
    payload = plain(selection['commit'])
    processing = plain(selection.get('evidence_processing'))
    attempted = False
    try:
        # Validate the routing envelope here too: restored/direct actions must
        # obey exactly the same rule as newly validated model selections.
        validate_schema(selection, source_location_inputs(
            action_schema({'type': 'object'}, repository.population_schema()), allow_legacy_quote=True))
        if any(not isinstance(payload.get(section, []), list) for section in SCIENTIFIC_SECTIONS):
            raise ContractError('representation_error')
        scientific = [row for section in SCIENTIFIC_SECTIONS for row in payload.get(section, [])]
        source_subjects = payload.get('source_subjects', [])
        original_results = [row for row in (source_subjects if isinstance(source_subjects, list) else [])
            if isinstance(row, dict) and row.get('reference_type') in ORIGINAL_RESULTS]
        if (scientific or original_results) and processing is None:
            raise ContractError('applicable_evidence_requires_grading')
        if (processing is not None and processing['kind'] == 'no_applicable_evidence'
                and any(payload.get(section, []) for section in SCIENTIFIC_SECTIONS
                        if section != 'observations')):
            raise ContractError('no_applicable_evidence_cannot_assess_evidence')
        missing_findings = [row.get('alias') for row in payload.get('assessments', [])
            if isinstance(row, dict) and not isinstance(row.get('investigation_finding'), dict)]
        if missing_findings:
            raise ContractError('evidence_assessment_source_finding_required', detail={
                'assessment_aliases': missing_findings, 'required_field': 'investigation_finding',
                'meaning': 'Record the actual source claim, its subject and qualification. '
                    'A saved numerical sheet does not replace this scientific finding. '
                    'Preserve unknown target correspondence; do not manufacture target support.'})
        with store.transaction():
            if processing is not None and processing['kind'] == 'no_applicable_evidence':
                attempted = True
                def read_source(ref, representation):
                    record = repository._native_source(context, ref)
                    authorize_source_access(ref, representation)
                    artifact = record.get('artifact_ref' if representation == 'original' else 'text_ref')
                    if artifact is None:
                        raise ContractError('literature_source_representation_unavailable')
                    return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
                sources = _Sources(read_source)
                examined = [sources.witness(witness, f'examined[{index}]')
                            for index, witness in enumerate(processing['examined'])]
                processing['examined'] = [{**original, 'quote': witness['quote']}
                    for original, witness in zip(processing['examined'], examined)]
            ownership = ({'account_owner': (context.run_id, context.episode_id)}
                         if payload.get('interpretation_accounts') else {})
            attempted = True
            outcome = store.commit_reasoning(payload, plain(context.scope), operation_key, **ownership)
            if outcome['status'] not in ('completed', 'partial'):
                return outcome
            if processing is not None and processing['kind'] == 'no_applicable_evidence':
                for ref in outcome['record_refs']:
                    record = store.get(ref)
                    if not (record['record_type'] == 'observation'
                            or record.get('reference_type') in ORIGINAL_RESULTS):
                        continue
                    anchor = record.get('anchor')
                    if anchor is None or not any(
                            anchor['source_ref'] == witness['source_ref']
                            and anchor['artifact_ref'] == witness['artifact_ref']
                            and witness['start'] <= anchor['start'] < anchor['end'] <= witness['end']
                            for witness in examined):
                        raise ContractError('no_applicable_observation_outside_examined_material')
            if processing is None or processing['kind'] == 'no_applicable_evidence':
                return {**outcome, 'evidence_processing': processing}
            # Same-action records are possessed by this owner. Do not create
            # fabricated inter-episode delivery receipts for them.
            grading_context = replace(context, received_record_refs=tuple(dict.fromkeys([
                *context.received_record_refs, *outcome['record_refs']])))
            gradings = _resolve(processing['gradings'], outcome['aliases'])
            required_refs = {ref for ref in outcome['record_refs']
                             if _requires_sheet(store.get(ref))}
            linked = set()
            results = []
            for index, grading in enumerate(gradings):
                try:
                    arguments = json.loads(grading['arguments'])
                except (ValueError, TypeError) as error:
                    raise ContractError('required_grading_arguments_json_object_required') from error
                if not isinstance(arguments, dict):
                    raise ContractError('required_grading_arguments_json_object_required')
                arguments = _resolve(arguments, outcome['aliases'])
                from .literature_assay_inputs import materialize_text_witness_inputs
                def read_grading_source(ref, representation):
                    record = repository._native_source(grading_context, ref)
                    authorize_source_access(ref, representation)
                    artifact = record.get('artifact_ref' if representation == 'original' else 'text_ref')
                    if artifact is None:
                        raise ContractError('literature_source_representation_unavailable')
                    return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
                arguments = materialize_text_witness_inputs(arguments, read_source=read_grading_source)
                validate_schema(arguments, repository.population_schema())
                contextual = repository.provider == 'literature.a108.context_grading'
                # Descriptive metadata remain committed context. Only actual
                # results and scientific interpretations require a matching
                # sheet. Their already saved observation, hypothesis and
                # experiment/original-result links supply the association;
                # the episode does not enumerate that association again.
                linked_observations = [ref for ref in required_refs
                    if store.get(ref)['record_type'] == 'observation']
                graded_refs = [ref for ref in required_refs
                    if _matches_grading(store, ref, arguments, contextual=contextual,
                        linked_observations=linked_observations)]
                result = repository.populate(grading_context, arguments,
                    f'{operation_key}:grading:{index}')
                if result['status'] not in ('completed', 'partial') or not result['result'].get('sheet_ref'):
                    raise ContractError('required_grading_sheet_not_saved')
                linked.update(graded_refs)
                results.append(result)
            if linked != required_refs:
                raise ContractError('required_grading_interpretation_uncovered',
                    detail={'ungraded_interpretation_refs': sorted(required_refs - linked)})
            return {**outcome, 'record_refs': list(dict.fromkeys([
                *outcome['record_refs'], *[ref for result in results for ref in result['record_refs']]])),
                'changed_record_refs': list(dict.fromkeys([
                    *outcome['changed_record_refs'],
                    *[ref for result in results for ref in result['changed_record_refs']]])),
                'evidence_processing': {'kind': 'graded', 'gradings': results}}
    except (ContractError, ExperimentalContractError) as error:
        # The scientific unit rolls back together. Independent acquisitions
        # remain saved. Feedback is attached to the actual original action.
        return {'status': 'failed' if attempted else 'invalid',
            'record_refs': [], 'changed_record_refs': [],
            'result': None, 'feedback': {'category': 'required_evidence_grading',
                'code': getattr(error, 'code', str(error)),
                **({'field': error.field} if isinstance(error, ExperimentalContractError) else {}),
                **({'detail': error.detail} if error.detail else {}),
                **({'reasoning_errors': outcome['errors'], 'reasoning_conflicts': outcome['conflicts']}
                   if 'outcome' in locals() and (outcome['errors'] or outcome['conflicts']) else {})}}
