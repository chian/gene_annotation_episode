from __future__ import annotations
from copy import deepcopy
import hashlib
import re
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, canonical
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_infernal_contracts import native_infernal_digest
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_infernal_preparation_acquisition import _shape
PREFIX = 'native_infernal_preparation_'
PLAN_VERSION = PREFIX + 'result_worker_plan_v1'
MANIFEST_VERSION = PREFIX + 'result_worker_manifest_v1'
NUMERICAL_FILES = {'grading': 'grading.json', 'sheet': 'sheet.json', 'calculations': 'calculations.json'}

def failure(stage, code, record_key=None):
    return {'stage': stage, 'code': code, 'record_key': record_key}

def exception_code(error, fallback):
    """Keep literal machine codes; arbitrary exception text stays diagnostic.

    Already-recorded capture codes, including their file locators, are passed
    through separately and never normalized by this exception boundary.
    """
    candidate = getattr(error, 'code', str(error))
    return candidate if type(candidate) is str and re.fullmatch('[a-z][A-Za-z0-9_]{0,191}', candidate) else fallback

def exception_diagnostic(error):
    return {'exception_type': type(error).__name__, 'detail': str(error)}

def validate_failures(rows):
    if type(rows) is not list or any((type(row) is not dict or set(row) != {'stage', 'code', 'record_key'} or any((type(row[k]) is not str or not row[k] for k in ('stage', 'code'))) or (row['record_key'] is not None and (type(row['record_key']) is not str or not row['record_key'])) for row in rows)):
        raise ContractError(PREFIX + 'result_failures_invalid')
    return rows

def unique_failures(rows):
    validate_failures(rows)
    return list({(r['stage'], r['code'], r['record_key']): r for r in rows}.values())

def qualified_occurrences(bundle, bundle_ref, capture):
    """Pure association reconstruction from the original, validated capture.

    Input descriptors describe FINAL bytes. Only bytes equal to both the staged
    and expected identity qualify as original operands for the pure grader.
    """
    capture = _shape(capture)
    if not capture['bundle_validated'] or capture['bundle_artifact_ref'] != bundle_ref or type(bundle_ref) is not str or (not bundle_ref.startswith('artifact_')):
        raise ContractError(PREFIX + 'grading_validated_capture_required')
    declared = {}
    sources = {(r['role'], r['ordinal']): r for r in bundle['inputs']}
    for collection, direction in (('inputs', 'input'), ('working_copies', 'working_copy'), ('artifacts', 'output')):
        for index, row in enumerate(bundle[collection]):
            role = row['operand_role'] if direction == 'working_copy' else row['role']
            ordinal = row['operand_ordinal'] if direction == 'working_copy' else row.get('ordinal', 0)
            fmt = sources[role, ordinal]['format'] if direction == 'working_copy' else row['format']
            sha = row['sha256'] if direction == 'output' else row['final_sha256']
            size = row['size_bytes'] if direction == 'output' else row['final_size_bytes']
            complete = bundle['returncode'] == 0 and (not bundle['failures'])
            if direction == 'input':
                complete = sha is not None and sha == row['staged_sha256'] == row['expected_sha256'] and (size == row['staged_size_bytes'] == row['expected_size_bytes'])
            elif direction == 'working_copy' and (not row['mutable']):
                original = sources[role, ordinal]
                complete = sha is not None and sha == row['initial_sha256'] == row['source_sha256'] == original['expected_sha256'] and (size == row['initial_size_bytes'] == original['expected_size_bytes'])
            key = (direction, role, ordinal, row['relative_path'])
            declared[key] = {'occurrence_ref': bundle_ref + '#/' + collection + '/' + str(index), 'direction': direction, 'role': role, 'ordinal': ordinal, 'format': fmt, 'relative_path': row['relative_path'], 'sha256': sha, 'size_bytes': size, 'completeness': 'complete' if complete else 'partial'}
    result, seen, problems = ([], set(), deepcopy(capture['failures']))
    for row in capture['artifacts']:
        key = tuple((row[k] for k in ('direction', 'role', 'ordinal', 'relative_path')))
        actual = declared.get(key)
        if actual is None or key in seen or row['format'] != actual['format'] or (actual['sha256'] is None) or (row['artifact_ref'] != 'artifact_' + actual['sha256']):
            raise ContractError(PREFIX + 'grading_occurrence_association_conflict')
        seen.add(key)
        result.append({**actual, 'artifact_ref': row['artifact_ref']})
        if row['direction'] == 'input' and actual['completeness'] != 'complete':
            problems.append(failure('custody', PREFIX + 'input_not_original_selected_bytes', actual['occurrence_ref']))
    if (bundle['program'], bundle['mode']) == ('cmfetch', 'single_key'):
        raw = canonical(bundle['requested_job']).encode('utf-8')
        digest = hashlib.sha256(raw).hexdigest()
        result.append({'occurrence_ref': bundle_ref + '#/requested_job', 'direction': 'input', 'role': 'request', 'ordinal': 0, 'format': 'infernal_request_json', 'relative_path': 'request.json', 'artifact_ref': 'artifact_' + digest, 'sha256': digest, 'size_bytes': len(raw), 'completeness': 'complete'})
    for index, row in enumerate(bundle['failures']):
        matches = [r for r in result if r['role'] == row['role'] and (r['direction'] == 'input' and row['detail'].get('ordinal') == r['ordinal'] or (r['direction'] == 'working_copy' and row['detail'].get('operand_ordinal') == r['ordinal']) or (r['direction'] == 'output' and row['stage'] == 'outputs'))]
        problems.append(failure(row['stage'], row['code'], matches[0]['occurrence_ref'] if len(matches) == 1 else bundle_ref + '#/failures/' + str(index)))
    if bundle['returncode'] != 0:
        problems.append(failure('native', PREFIX + 'native_execution_unsuccessful', bundle_ref + '#/returncode'))
    return (result, unique_failures(problems))

def effective_parameters(bundle, occurrences):
    """Use only provenance already proved by this selected producer/capture.

    A previous SSI or merge partition operand has no producer request in this
    contract. Its bytes remain retained, while producer-dependent checks stay
    unknown. Self-reported binding metadata is never accepted as that proof.
    """
    original = deepcopy(bundle['requested_job']['native_infernal_preparation']['grading_parameters'])
    result, problems = (deepcopy(original), [])
    lookup = {(r['direction'], r['role'], r['ordinal']): r for r in occurrences}
    source = lookup.get(('input', 'models', 0))
    source_ok = source is not None and source['completeness'] == 'complete'
    if bundle['program'] in {'cmconvert', 'cmfetch', 'cmpress'}:
        authenticated = []
        copy = lookup.get(('working_copy', 'models', 0))
        copies = [r for r in bundle['working_copies'] if r['operand_role'] == 'models' and r['operand_ordinal'] == 0]
        valid_copy = source_ok and copy is not None and (len(copies) == 1) and (not copies[0]['mutable']) and (copy['completeness'] == 'complete') and (copy['sha256'] == source['sha256']) and (bundle['returncode'] is not None)
        for row in occurrences:
            if row['role'] not in {'ssi', 'i1m', 'i1i', 'i1f', 'i1p'}:
                continue
            selected_output = row['direction'] == 'output' and valid_copy and (bundle['program'] == 'cmpress' or (bundle['program'], bundle['mode']) == ('cmfetch', 'index'))
            if selected_output:
                authenticated.append({'artifact_ref': row['occurrence_ref'], 'artifact_sha256': row['sha256'], 'source_artifact_ref': source['occurrence_ref'], 'source_sha256': source['sha256'], 'expected_attempt_id': bundle['identity']['attempt_id'], 'actual_attempt_id': bundle['identity']['attempt_id'], 'staged_source_stem': copy['relative_path'], 'actual_relative_path': row['relative_path'], 'regular_file': True})
            elif row['direction'] != 'working_copy':
                problems.append(failure('metadata', PREFIX + 'artifact_binding_unavailable', row['occurrence_ref']))
        supplied = original.get('artifact_bindings')
        if supplied and native_infernal_digest(supplied) != native_infernal_digest(authenticated):
            problems.append(failure('metadata', PREFIX + 'supplied_artifact_bindings_conflict'))
        if authenticated or 'artifact_bindings' in original:
            result['artifact_bindings'] = authenticated
    if bundle['program'] in {'cmbuild', 'cmcalibrate', 'cmstat'}:
        authenticated = []
        output = lookup.get(('output', 'partition_scores', 0))
        settings = bundle['operation']['settings']
        has_gc = any((r['role'] == 'gc' for r in bundle['requested_job']['native_infernal_preparation']['operands']))
        if (bundle['program'], bundle['mode']) == ('cmcalibrate', 'partition_scores') and source_ok and (output is not None) and (not has_gc):
            authenticated.append({'artifact_ref': output['occurrence_ref'], 'source_model_artifact_ref': source['occurrence_ref'], 'source_model_sha256': source['sha256'], 'partition_index': settings['--part'], 'partition_count': settings['--ptot'], 'requested_megabases': settings['-L'], 'settings': deepcopy(settings)})
        bound = {r['artifact_ref'] for r in authenticated}
        for row in occurrences:
            if row['role'] == 'partition_scores' and row['direction'] != 'working_copy' and (row['occurrence_ref'] not in bound):
                problems.append(failure('metadata', PREFIX + 'partition_request_binding_unavailable', row['occurrence_ref']))
        if original.get('partition_requests') and native_infernal_digest(original['partition_requests']) != native_infernal_digest(authenticated):
            problems.append(failure('metadata', PREFIX + 'supplied_partition_requests_unverified'))
        result.pop('partition_requests', None)
        if authenticated:
            result['partition_requests'] = authenticated
    return (result, problems)
