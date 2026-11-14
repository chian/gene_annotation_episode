from __future__ import annotations
import json
import re
import hashlib
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.blast_search as blast
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, identity

def require_permitted_hsp(observation_ref, permitted_inputs):
    if not isinstance(permitted_inputs, (tuple, list)) or any((not isinstance(ref, str) or not ref for ref in permitted_inputs)):
        raise ContractError('blast_hsp_inputs_not_bound')
    if observation_ref not in permitted_inputs:
        raise ContractError('blast_hsp_input_not_received')

def _immutable_record(row):
    payload = {key: value for key, value in row.items() if key not in {'id', 'record_type', 'origin'}}
    if row['id'] != identity(row['record_type'], {'origin': row['origin'], 'record': payload}):
        raise ContractError('blast_hsp_record_identity_conflict')

def retained_hsp_component(store, observation, source):
    """Resolve exactly the bound retained sheet, without a calculator call.

    The host validates the observation/native operand relationship in
    ``_original_hsp``. This accessor additionally checks source/artifact custody,
    normalized native bytes, original address and the retained compact address.
    """
    from gene_annotation_episode.episodic_workflow.root.a110.tool_grading_artifacts import source_tool_grading_entries
    binding = observation['native_blast'].get('shared_projection')
    if not isinstance(binding, dict) or binding.get('version') != blast.HSP_PROJECTION_VERSION or set(binding) != {'version', 'grading_artifact_ref', 'native_artifact_ref', 'hit_row', 'hsp_row'} or (binding['native_artifact_ref'] != source['artifact_ref']):
        raise ContractError('blast_shared_hsp_binding_conflict')
    candidates = [entry['grading'] for entry in source_tool_grading_entries(store, source['id']) if entry['artifact_ref'] == binding['grading_artifact_ref']]
    if len(candidates) != 1:
        raise ContractError('blast_shared_hsp_grading_artifact_conflict')
    grading, = candidates
    normalized = (grading.get('sheet') or {}).get('normalized_result', {})
    content = store.get_artifact(source['artifact_ref'])
    metadata = json.loads(store.get_artifact(source['request_ref']))
    if normalized.get('native', {}).get('sha256') != hashlib.sha256(content).hexdigest() or normalized.get('native', {}).get('document') != json.loads(content) or normalized.get('search', {}).get('request') != metadata['request'] or (normalized.get('mode') != 'database') or (normalized.get('format') != 'json2') or (normalized.get('resource') != 'api'):
        raise ContractError('blast_shared_hsp_native_source_conflict')
    component, _ = blast.shared_hsp_component(grading, hit_ordinal=observation['native_blast']['hit_ordinal'], hsp_ordinal=observation['native_blast']['hsp_ordinal'], address={key: binding[key] for key in ('hit_row', 'hsp_row')})
    return component

def _original_hsp(store, observation_ref, permitted_inputs, scope):
    require_permitted_hsp(observation_ref, permitted_inputs)
    scope = store.validate_scope(scope)
    observation = store.get(observation_ref)
    if observation.get('native_blast_standard_database') is not None:
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_standard_database_result_publication import validate_standard_blast_database_observation
        validate_standard_blast_database_observation(store, observation)
        raise ContractError('native_blast_standard_database_biological_reference_unavailable')
    if observation.get('native_blast_database') is not None:
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_database_result_publication import validate_native_blast_database_observation
        validate_native_blast_database_observation(store, observation)
        raise ContractError('native_blast_database_biological_reference_unavailable')
    if observation.get('record_type') != 'observation' or observation.get('origin') != 'tool' or observation.get('kind') != 'comparison' or (not (observation.get('native_blast') or observation.get('native_blast_pairwise'))):
        raise ContractError('native_blast_hsp_observation_required')
    if 'native_blast' in observation and 'native_blast_pairwise' in observation:
        raise ContractError('native_blast_pairwise_mixed_native_markers')
    _immutable_record(observation)
    if not store.reference_subset([observation_ref], scope):
        raise ContractError('blast_hsp_outside_assigned_scope')
    footprint = [segment for interval in observation.get('operand_intervals') or [] if interval['role'] == 'query' and store.roots(interval['subject_ref']) for segment in store.map_segments(interval['subject_ref'], [{'start': interval['start'], 'end': interval['end']}])]
    if footprint and (not store.scope_covers(footprint, scope)):
        raise ContractError('blast_hsp_outside_assigned_scope')
    if len(observation['subject_refs']) != 1 or len(observation['source_subject_refs']) != 1:
        raise ContractError('blast_hsp_operand_identity_conflict')
    if observation.get('native_blast_pairwise'):
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_hsp_views import native_blast_pairwise_hsp
        bound = native_blast_pairwise_hsp(store, observation)
        return (observation, bound['source'], bound['reference'], bound['native_hsp'])
    source = store.get(observation['source_ref'])
    if source.get('record_type') != 'source' or source.get('provider') != 'ncbi_blast' or source.get('origin') != 'external':
        raise ContractError('native_blast_source_required')
    _immutable_record(source)
    try:
        metadata = json.loads(store.get_artifact(source['request_ref']))
        request = metadata['request']
        parsed = blast.document(store.get_artifact(source['artifact_ref']))
        blast.validate_identity(parsed, request)
        native_locator = observation['native_blast']
        if native_locator['report_ordinal'] != 0:
            raise ValueError('blast_single_query_report_required')
        hit = parsed['search']['hits'][native_locator['hit_ordinal']]
        native = hit['hsps'][native_locator['hsp_ordinal']]
        query_ref = observation['subject_refs'][0]
        reference_ref = observation['source_subject_refs'][0]
        reference = store.get(reference_ref)
        if request['subject_ref'] != query_ref or request['query_length'] != store.subject_length(query_ref) or reference.get('record_type') != 'reference' or (reference['source_ref'] != source['id']) or (reference['length'] != hit['len']):
            raise ValueError('blast_hsp_operand_identity_conflict')
        _immutable_record(reference)
        descriptions = [row for row in hit.get('description') or [] if isinstance(row, dict)]
        first = descriptions[0] if descriptions else {}
        accession = first.get('accession') or first.get('id')
        if not isinstance(accession, str) or len(accession) > 200 or re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:/+%#?=;&@~-]*', accession) is None:
            accession = identity('source_local_hit', {'source_ref': source['id'], 'hit_ordinal': native_locator['hit_ordinal']})
        if reference['accession'] != accession:
            raise ValueError('blast_hsp_reference_identity_conflict')
        original_marker = blast.native_hsp_metadata(native, program=request['algorithm'], query_length=request['query_length'], reference_length=reference['length'], hit_ordinal=native_locator['hit_ordinal'], hsp_ordinal=native_locator['hsp_ordinal'])
        if original_marker != {key: value for key, value in native_locator.items() if key != 'shared_projection'}:
            raise ValueError('blast_hsp_native_geometry_conflict')
        binding = native_locator.get('shared_projection')
        source_projection = metadata.get('transport', {}).get('hsp_projection_version')
        if binding is not None:
            if source_projection != blast.HSP_PROJECTION_VERSION:
                raise ValueError('blast_shared_hsp_source_projection_conflict')
            component = retained_hsp_component(store, observation, source)
            row = blast.hsp_row(native, component=component, program=request['algorithm'], query_length=request['query_length'], reference_length=reference['length'], hit_ordinal=native_locator['hit_ordinal'], hsp_ordinal=native_locator['hsp_ordinal'])
        else:
            if source_projection is not None:
                raise ValueError('blast_shared_hsp_binding_missing')
            row = {'query_interval': [min(native['query_from'], native['query_to']) - 1, max(native['query_from'], native['query_to'])], 'reference_interval': [min(native['hit_from'], native['hit_to']) - 1, max(native['hit_from'], native['hit_to'])]}
        expected_intervals = [{'role': role, 'subject_ref': ref, 'start': interval[0], 'end': interval[1], 'unit': store.subject_unit(ref), 'model_unit': blast.PROGRAM_UNITS[request['algorithm']][2]} for role, ref, interval in (('query', query_ref, row['query_interval']), ('reference', reference_ref, row['reference_interval']))]
        if observation.get('operand_intervals') != expected_intervals:
            raise ValueError('blast_hsp_operand_geometry_conflict')
        measured = {item['name']: item['value'] for item in observation['measurements']}
        if measured.get('reference_ref') != {'type': 'reference', 'ref': reference_ref}:
            raise ValueError('blast_hsp_reference_identity_conflict')
        if binding is not None:
            expected = {'reference_ref': {'type': 'reference', 'ref': reference_ref}, **{name: {'type': 'number', 'value': value, 'unit_ref': None} for name, value in row['measurements'].items()}}
            if measured != expected:
                raise ValueError('blast_hsp_native_measurement_conflict')
        original_rids = []
        for ref in source.get('parent_source_refs', []):
            parent = store.get(ref)
            if parent.get('provider') == 'ncbi_blast':
                try:
                    original_rids.append(blast.submission(store.get_artifact(parent['artifact_ref']))[0])
                except (ValueError, UnicodeError):
                    pass
        if request.get('job_id') not in original_rids:
            raise ValueError('blast_original_submission_identity_conflict')
    except (ValueError, TypeError, KeyError, IndexError) as error:
        raise ContractError(str(error) if isinstance(error, ValueError) else 'blast_hsp_native_record_invalid') from error
    return (observation, source, reference, native)

def blast_hsp_facts(store, references):
    """Project already qualified acquisition records; never acquire or grade."""
    result = []
    for reference in dict.fromkeys(references):
        record = store.get(reference)
        if record.get('record_type') != 'observation' or not record.get('native_blast'):
            continue
        if record.get('origin') != 'tool' or record.get('kind') != 'comparison' or len(record.get('source_subject_refs', [])) != 1:
            raise ContractError('native_blast_hsp_observation_required')
        record, _, _, _ = _original_hsp(store, reference, [reference], None)
        values = {row['name']: row['value'] for row in record['measurements']}
        native = {}
        for name in ('bitscore', 'alignment_score', 'evalue', 'query_coverage', 'target_coverage'):
            if name in values and values[name].get('type') != 'number':
                raise ContractError('blast_hsp_native_measurement_required')
            native[name] = values[name]['value'] if name in values else None
        identity_value = values.get('identity_fraction')
        if identity_value is not None and identity_value.get('type') != 'number':
            raise ContractError('blast_hsp_native_measurement_required')
        result.append({'hsp_ref': reference, 'reference_ref': record['source_subject_refs'][0], **native, 'identity_fraction': identity_value['value'] if identity_value is not None else None})
    return result
