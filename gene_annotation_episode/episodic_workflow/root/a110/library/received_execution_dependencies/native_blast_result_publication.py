from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import re
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.blast_pairwise_result_views import NATIVE_BLAST_METRICS, projected_measurements, row_schema, validate_native_blast_result_selector
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, identity, validate_schema
from gene_annotation_episode.episodic_workflow.root.a110.materials import artifact_path
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_contracts import finite_json_copy, native_blast_digest
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_result_worker import record_key, validate_native_blast_correspondence_collections
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_hmmer_result_publication import _subject_chunks
_PREPARED_VERSION = 'native_blast_prepared_grading_v2'
_SCHEMA_VERSION = 'native_blast_retained_grading_v2'
_ARTIFACT_FIELDS = ('bundle_artifact_ref', 'source_grading_artifact_ref', 'grading_artifact_ref', 'sheet_artifact_ref', 'scores_artifact_ref', 'selected_rows_artifact_ref')

def _failure(stage, code, record_key=None):
    return {'stage': stage, 'code': code, 'record_key': record_key}

def _read_json(store, ref):
    with artifact_path(store, ref).open(encoding='utf-8') as stream:
        return finite_json_copy(json.load(stream))

def _captured_paths(store, bundle, artifacts):
    declared, paths, failures, seen = ({}, [], [], set())
    for kind, rows in (('input', bundle['inputs']), ('output', bundle['artifacts'])):
        for row in rows:
            key = (row['role'], row['format'], row['relative_path'])
            if key in declared:
                raise ContractError('native_blast_duplicate_bundle_artifact')
            declared[key] = (kind, row)
    for item in artifacts:
        if type(item) is not dict or set(item) != {'role', 'format', 'relative_path', 'artifact_ref'}:
            raise ContractError('native_blast_captured_artifact_shape_invalid')
        key = (item['role'], item['format'], item['relative_path'])
        if key not in declared or key in seen:
            raise ContractError('native_blast_captured_artifact_binding_invalid')
        seen.add(key)
        kind, native = declared[key]
        expected = native['actual_sha256'] if kind == 'input' else native['sha256']
        try:
            stored = store.get(item['artifact_ref'])
            if stored.get('record_type') != 'artifact' or stored['sha256'] != expected or stored['size'] != native['size_bytes']:
                raise ContractError('native_blast_captured_artifact_digest_mismatch')
            if kind == 'input' and (expected != native['expected_sha256'] or native['size_bytes'] != native['expected_size_bytes']):
                raise ContractError('native_blast_input_not_original_selected_bytes')
            paths.append({**item, 'kind': kind, 'path': str(artifact_path(store, item['artifact_ref']))})
        except (ValueError, OSError) as error:
            failures.append(_failure('custody', str(error) if isinstance(error, ValueError) else 'native_blast_captured_artifact_unreadable'))
    for key in declared.keys() - seen:
        failures.append(_failure('custody', 'native_blast_captured_artifact_missing:' + key[0]))
    return (paths, sorted(failures, key=lambda row: (row['stage'], row['code'])))

def _binding_snapshots(store, bundle):
    snapshots = {}
    for binding in bundle['operand_bindings']:
        for key in ('subject_ref', 'reference_ref'):
            ref = binding[key]
            if ref is None or ref in snapshots:
                continue
            try:
                record = store.get(ref)
                digest = hashlib.sha256()
                for chunk in _subject_chunks(store, ref):
                    digest.update(chunk)
                snapshots[ref] = {'record_type': record['record_type'], 'length': store.subject_length(ref), 'molecule': store.subject_molecule(ref), 'sequence_sha256': digest.hexdigest(), 'accession': record.get('accession'), 'error': None}
            except (ValueError, OSError, KeyError, UnicodeError) as error:
                snapshots[ref] = {'error': 'native_blast_store_binding_unavailable', 'detail': str(error)}
    return snapshots

def _qualified_grading(store, source_ref, bundle, prepared, selector):
    if type(prepared) is not dict or set(prepared) != {'version', *_ARTIFACT_FIELDS, 'failures', 'numerical_complete'} or prepared['version'] != _PREPARED_VERSION:
        raise ContractError('native_blast_prepared_grading_required')
    source = store.get(source_ref)
    if source.get('record_type') != 'source' or source.get('provider') != 'episode.execution_result' or source.get('origin') != 'tool' or (source.get('version') != 'native_blast_bundle_v1') or (source.get('artifact_ref') != prepared['bundle_artifact_ref']) or (prepared['source_grading_artifact_ref'] not in source.get('auxiliary_artifact_refs', [])) or (source.get('accession') != 'native_blast_' + native_blast_digest(bundle['identity'])) or (source.get('retrieved_at') != bundle['finished_at']):
        raise ContractError('native_blast_publication_source_custody_mismatch')
    if _read_json(store, prepared['bundle_artifact_ref']) != bundle:
        raise ContractError('native_blast_captured_bundle_identity_mismatch')
    selected = _read_json(store, prepared['grading_artifact_ref'])
    original = _read_json(store, prepared['source_grading_artifact_ref'])
    for envelope in (selected, original):
        if set(envelope) != {'schema', 'provider', 'native_artifact_ref', 'grading'} or envelope['schema'] != 'tool_grading_artifact_v1' or envelope['provider'] != source['provider'] or (envelope['native_artifact_ref'] != source['artifact_ref']):
            raise ContractError('native_blast_grading_source_custody_mismatch')
    grading, stable = (selected['grading'], original['grading'])
    expected_schema = _SCHEMA_VERSION
    if grading.get('schema') != expected_schema or stable.get('schema') != expected_schema or grading.get('bundle_sha256') != native_blast_digest(bundle) or (grading.get('selector') != selector) or (grading.get('failures') != prepared['failures']) or (grading.get('numerical_complete') != prepared['numerical_complete']) or any((grading.get(field) != prepared[field] for field in _ARTIFACT_FIELDS if field not in {'bundle_artifact_ref', 'grading_artifact_ref'})) or any((grading.get(field) != value for field, value in stable.items())):
        raise ContractError('native_blast_prepared_grading_identity_mismatch')
    for field in ('sheet_artifact_ref', 'scores_artifact_ref', 'complete_rows_artifact_ref'):
        if stable.get(field) is not None:
            artifact_path(store, stable[field])
    if stable.get('sheet_artifact_ref') is not None and (stable.get('scores_artifact_ref') is not None):
        try:
            validate_native_blast_correspondence_collections(_read_json(store, stable['sheet_artifact_ref']), _read_json(store, stable['scores_artifact_ref']))
        except (ValueError, KeyError, TypeError, IndexError) as error:
            raise ContractError('native_blast_retained_correspondence_conflict') from error
    captured = [{k: v for k, v in row.items() if k != 'kind'} for row in stable['captured_artifacts']]
    _, custody_failures = _captured_paths(store, bundle, captured)
    original_failures = {(row['stage'], row['code']) for row in prepared['failures']}
    if any(((row['stage'], row['code']) not in original_failures for row in custody_failures)):
        raise ContractError('native_blast_retained_capture_changed')
    if any((row['artifact_ref'] not in source['auxiliary_artifact_refs'] for row in captured)):
        raise ContractError('native_blast_source_captured_artifact_missing')
    return grading

def _frozen_rows(store, grading, selector, bundle):
    selected_ref, rows_ref = (grading['selected_rows_artifact_ref'], grading['complete_rows_artifact_ref'])
    if selected_ref is None:
        return []
    if rows_ref is None:
        raise ContractError('native_blast_complete_rows_unavailable')
    requested = selector['projection']
    selection = requested['rows']
    wanted = selection.get('record_keys')
    rows, expected, seen, ordinal = ([], [], set(), 0)
    with artifact_path(store, rows_ref).open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['family'] != requested['family']:
                continue
            if row['record_key'] in seen:
                raise ContractError('native_blast_complete_row_duplicate')
            seen.add(row['record_key'])
            if row['record_key'] != record_key(bundle, row['search_key'], row['family'], row['hit_ordinal'], row['hsp_ordinal']):
                raise ContractError('native_blast_complete_row_identity_mismatch')
            chosen = row['record_key'] in wanted if wanted is not None else selection['offset'] <= ordinal < selection['offset'] + selection['limit']
            if chosen:
                values, unavailable = projected_measurements(row, requested['metrics'])
                rows.append(row)
                expected.append({'version': 'native_blast_selected_row_v1', 'family': row['family'], 'record_key': row['record_key'], 'native_ordinal': ordinal, 'measurements': values, 'unavailable': unavailable})
            ordinal += 1
    with artifact_path(store, selected_ref).open(encoding='utf-8') as stream:
        actual = [json.loads(line) for line in stream]
    if actual != expected:
        raise ContractError('native_blast_selected_rows_frozen_measurement_mismatch')
    return list(zip(rows, expected))

def _validate_sequence(store, operand, reference, *, scope=None, intervals=()):
    if operand['binding_error']:
        raise ContractError(operand['binding_error'])
    if store.subject_length(reference) != operand['length'] or store.subject_molecule(reference) != operand['molecule']:
        raise ContractError('native_blast_subject_molecule_or_length_mismatch')
    digest = hashlib.sha256()
    for chunk in _subject_chunks(store, reference):
        digest.update(chunk)
    if digest.hexdigest() != operand['sequence_sha256']:
        raise ContractError('native_blast_subject_sequence_mismatch')
    if scope is not None:
        if reference not in store.reference_subset([reference], scope):
            raise ContractError('native_blast_subject_outside_scope')
        for interval in intervals:
            if not (type(interval) is list and len(interval) == 2 and all((type(v) is int for v in interval)) and (0 <= interval[0] < interval[1] <= operand['length'])):
                raise ContractError('native_blast_subject_interval_invalid')
            footprint = store.map_segments(reference, [{'start': interval[0], 'end': interval[1]}])
            if store.roots(reference) and (not footprint or not store.scope_covers(footprint, scope)):
                raise ContractError('native_blast_subject_interval_outside_scope')

def _record(store, kind, payload, scope, publish):
    if publish:
        return store.put(kind, payload, origin='tool', scope=scope)['id']
    ref = identity(kind, {'origin': 'tool', 'record': payload})
    expected = {**payload, 'id': ref, 'record_type': kind, 'origin': 'tool'}
    if store.get(ref) != expected:
        raise ContractError('native_blast_frozen_record_mismatch')
    return ref

def _reference(store, operand, grading, source_ref, scope, publish):
    if operand['binding_error']:
        raise ContractError(operand['binding_error'])
    supplied = (operand['binding'] or {}).get('reference_ref')
    if supplied is not None:
        record = store.get(supplied)
        if record.get('record_type') != 'reference' or record.get('accession') != operand['native_id']:
            raise ContractError('native_blast_reference_binding_identity_mismatch')
        _validate_sequence(store, operand, supplied)
        return supplied
    seqref = grading['sequence_artifact_refs'].get('reference')
    if seqref is None:
        raise ContractError('native_blast_reference_sequence_unavailable')
    sequence = store.get(seqref)
    artifact_path(store, seqref)
    if sequence['sha256'] != operand['sequence_sha256'] or sequence['size'] != operand['length']:
        raise ContractError('native_blast_reference_sequence_mismatch')
    accession = operand['native_id']
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:/+%#?=;&@~-]{0,199}', accession):
        accession = identity('native_operand', {'artifact_ref': operand['artifact_ref'], 'role': operand['operand_role'], 'ordinal': operand['record_ordinal']})
    payload = {'reference_type': 'protein' if operand['molecule'] == 'protein' else 'sequence', 'source_ref': source_ref, 'accession': accession, 'label': operand['native_title'][:512], 'sequence_ref': seqref, 'molecule': operand['molecule'], 'length': operand['length'], 'term_refs': [], 'context_refs': []}
    return _record(store, 'reference', payload, scope, publish)

def _publication(store, *, source_ref, bundle, prepared, scope, selector, publish):
    selector = validate_native_blast_result_selector(selector, program=bundle['program'])
    scope = store.validate_scope(scope)
    grading = _qualified_grading(store, source_ref, bundle, prepared, selector)
    result = {'record_refs': [source_ref], 'rows': [], 'failures': deepcopy(prepared['failures'])}
    for row, selected in _frozen_rows(store, grading, selector, bundle):
        projected = {key: deepcopy(row[key]) for key in ('record_key', 'search_key', 'hit_ordinal', 'hsp_ordinal', 'program', 'coordinate_units', 'native_status')}
        projected.update(source_ref=source_ref, observation_ref=None, subject_ref=None, reference_refs=[], status='invalid' if row['invalid'] else 'unbound', measurements=selected['measurements'], unavailable=selected['unavailable'])
        try:
            if row['invalid']:
                raise ContractError('native_blast_invalid_native_row')
            query, reference = (row['operands'].get('query'), row['operands'].get('reference'))
            if query is None or reference is None:
                raise ContractError('native_blast_operand_unavailable')
            subject = (query['binding'] or {}).get('subject_ref')
            if subject is None:
                raise ContractError('native_blast_subject_binding_unavailable')
            selection = query['selected_interval'] or [0, query['length']]
            intervals = [selection]
            if row['family'] == 'pairwise_hsp':
                intervals.append(row['intervals']['query'])
            _validate_sequence(store, query, subject, scope=scope, intervals=intervals)
            with store.transaction():
                ref = _reference(store, reference, grading, source_ref, scope, publish)
                observation = None
                if row['family'] == 'pairwise_hsp':
                    all_values, _ = projected_measurements(row, NATIVE_BLAST_METRICS['pairwise_hsp'])
                    payload = {'subject_refs': [subject], 'source_subject_refs': [ref], 'kind': 'comparison', 'source_ref': source_ref, 'measurements': [{'name': value['name'], 'value': {'type': 'number', 'value': value['value'], 'unit_ref': None}} for value in all_values], 'dependencies': list(dict.fromkeys([source_ref, subject, ref])), 'anchor': None, 'operand_intervals': [{'role': axis, 'subject_ref': operand_ref, 'start': row['intervals'][axis][0], 'end': row['intervals'][axis][1], 'unit': row['coordinate_units'][axis], 'model_unit': row['coordinate_units']['alignment']} for axis, operand_ref in (('query', subject), ('reference', ref))], 'native_blast_pairwise': {'version': 'native_blast_pairwise_observation_v1', 'program': bundle['program'], 'record_key': row['record_key'], 'search_key': row['search_key'], 'hit_ordinal': row['hit_ordinal'], 'hsp_ordinal': row['hsp_ordinal'], 'bundle_artifact_ref': prepared['bundle_artifact_ref']}}
                    observation = _record(store, 'observation', payload, scope, publish)
            projected.update(observation_ref=observation, subject_ref=subject, reference_refs=[ref], status='published')
            if row['family'] == 'pairwise_hsp':
                result['record_refs'].extend([ref, observation])
        except (ValueError, KeyError, TypeError, OSError) as error:
            if str(error) != 'native_blast_subject_binding_unavailable':
                projected['status'] = 'invalid'
            result['failures'].append(_failure('publication', str(error) if isinstance(error, ValueError) else 'native_blast_row_publication_failed', row['record_key']))
        validate_schema(projected, row_schema(row['family']))
        result['rows'].append(projected)
    result['record_refs'] = list(dict.fromkeys(result['record_refs']))
    return result

def validate_native_blast_publication(store, *, source_ref, bundle, prepared, scope, selector, publication):
    """Authenticate a frozen return without writes, parsing or recalculation."""
    expected = _publication(store, source_ref=source_ref, bundle=bundle, prepared=prepared, scope=scope, selector=selector, publish=False)
    if finite_json_copy(publication) != expected:
        raise ContractError('native_blast_frozen_publication_mismatch')
    return expected
