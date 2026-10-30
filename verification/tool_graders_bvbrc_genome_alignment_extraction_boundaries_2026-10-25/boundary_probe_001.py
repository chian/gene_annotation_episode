"""Small offline boundary mechanics; synthetic receipts are NOT host authentication.

This file is deliberately not a production extractor, receipt authenticator or
complete log parser. It tests the proposed receipt-bytes/task split and records
existing public-validator/native-reader behavior. Every write stays beside it.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.bvbrc_appservice_readers import decode_job_result, decode_task_info
from gene_annotation_episode.bvbrc_genome_alignment_input_contracts import (
    validate_genome_alignment_inputs, validate_genome_alignment_associations,
)
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.mauve_backbone_formats import parse_mauve_bbcols
from gene_annotation_episode.xmfa_formats import parse_mauve_xmfa

PREFIX = 'bvbrc_genome_alignment_'
LABEL = 'SYNTHETIC receipt/task/provenance; no host custody or live service proof'


def content(raw, name):
    return {'source_ref': 'synthetic:source:' + name, 'artifact_field': 'artifact_ref',
            'artifact_ref': 'artifact_' + hashlib.sha256(raw).hexdigest(),
            'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)}


def fail(code):
    raise ValueError(PREFIX + code)


def actual_bytes(binding, data):
    raw = data.get(binding['artifact_ref'])
    if raw is None:
        fail('content_missing')
    if len(raw) != binding['byte_count'] or hashlib.sha256(raw).hexdigest() != binding['sha256']:
        fail('content_digest_conflict')
    return raw


def make_log_record(task, raw, *, ref_name='stdout', body_complete=True):
    native = content(raw, ref_name + ':native')
    request = {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1',
        'required_application_id': 'GenomeAlignment', 'parameters': deepcopy(task['submitted_parameters']),
        'start_parameters': {}, 'definition_inputs': [], 'input_bindings': [], 'workspace_targets': []}
    args = {'handoff_ref': task['submission_receipt_ref'], 'file': 'stdout'}
    operands = {'operation': 'api.bvbrc_appservice.task_info', 'request_sha256': digest(request),
        'arguments_sha256': digest(args), 'native_operands': {'request': request, 'arguments': args,
        'selector': None, 'call': {'task_id': task['task_id'], 'file': 'stdout'}, 'local_failure': None}}
    origin = {'run_id': 'synthetic_run', 'episode_id': 'synthetic_results',
        'operation_key': 'synthetic_run:synthetic_results:1', 'name': operands['operation'],
        'arguments_sha256': digest(args), 'assignment_sha256': '0' * 64, 'scope_sha256': '1' * 64}
    value = {'receipt': {'version': 'bvbrc_appservice_support_receipt_v1',
        'receipt_ref': 'synthetic:source:' + ref_name, 'purpose': 'support', 'origin': origin,
        'snapshot': {'source_ref': native['source_ref'], 'content': native,
            'retrieved_at': '2026-10-25T00:00:00Z', 'media_type': 'text/plain',
            'transport': {'status': 200, 'body_complete': body_complete,
                'received_body_bytes': len(raw)}, 'selected_operands': operands},
        'effect_receipt_refs': [], 'status': 'ok' if body_complete else 'partial', 'diagnostics': []},
        'original_handoff_ref': task['submission_receipt_ref'], 'task_id': task['task_id'],
        'file': 'stdout', 'reported_object_uuid': None,
        'returned_representation': 'signature_redacted_http_bytes', 'body_complete': body_complete,
        'local_window': None}
    validate_contract('TaskInfoReceipt', value)
    stored = deepcopy(value)
    del stored['receipt']['receipt_ref']
    envelope = {'version': 'bvbrc_appservice_retained_receipt_v1', 'contract': 'TaskInfoReceipt', 'value': stored}
    encoded = canonical(envelope).encode()
    binding = content(encoded, ref_name)
    record = {'receipt_content': binding, 'record': {'source_ref': binding['source_ref'],
        'contract': 'TaskInfoReceipt', 'value': value}}
    return record, {binding['artifact_ref']: encoded, native['artifact_ref']: raw}


def check_record_mechanics(task, row, data):
    """Only synthetic task_info bytes/semantic checks, never Store authenticity."""
    if type(row) is not dict or set(row) != {'receipt_content', 'record'}:
        fail('argument_invalid')
    record = row['record']
    if set(record) != {'source_ref', 'contract', 'value'} or record['contract'] != 'TaskInfoReceipt':
        fail('argument_invalid')
    value = validate_contract('TaskInfoReceipt', record['value'])
    encoded = actual_bytes(row['receipt_content'], data)
    expected = deepcopy(value)
    del expected['receipt']['receipt_ref']
    expected = canonical({'version': 'bvbrc_appservice_retained_receipt_v1',
        'contract': 'TaskInfoReceipt', 'value': expected}).encode()
    if encoded != expected or row['receipt_content']['source_ref'] != record['source_ref']:
        fail('metadata_record_unverified')
    snap = value['receipt']['snapshot']
    if snap is None:
        fail('content_missing')
    raw = actual_bytes(snap['content'], data)
    selected = snap['selected_operands']
    native = selected['native_operands']
    if (value['task_id'] != task['task_id'] or value['original_handoff_ref'] != task['submission_receipt_ref']
        or selected['operation'] != 'api.bvbrc_appservice.task_info'
        or native['call'] != {'task_id': task['task_id'], 'file': value['file']}
        or native['arguments'] != {'handoff_ref': task['submission_receipt_ref'], 'file': value['file']}
        or selected['request_sha256'] != digest(native['request'])
        or selected['arguments_sha256'] != digest(native['arguments'])
        or native['request']['parameters'] != task['submitted_parameters']):
        fail('metadata_task_conflict')
    return value, raw


def probe_argv(task, row, data):
    value, raw = check_record_mechanics(task, row, data)
    if not value['body_complete'] or value['local_window'] is not None:
        fail('invocation_missing')
    text = decode_task_info(raw, task_id=task['task_id'], file='stdout')['value']['text']
    if text is None:
        fail('invocation_missing')
    # Narrow fixture grammar intentionally covers only one progressive command
    # with its exact first output token and observed input operand count.
    groups = list(re.finditer(r'^Running progressiveMauve with params:  ([^\n]*)\n', text, re.M))
    if len(groups) != 1:
        fail('invocation_conflict' if groups else 'invocation_missing')
    group = groups[0]
    first = group.group(1)
    count = len(task['submitted_parameters']['genome_ids'])
    rest = text[group.end():].splitlines()
    if not first.startswith('--output=') or len(rest) < count + 1:
        fail('invocation_missing')
    paths = rest[:count]
    if any(not p.startswith('/') or any(x in p for x in ('\r', '\x00')) for p in paths):
        fail('invocation_conflict')
    return ['progressiveMauve', first, *paths]


def check_case(name, expected_code, fn):
    try:
        value = fn()
        code = None
    except ValueError as error:
        value, code = None, str(error)
    assert code == expected_code, (name, code, expected_code)
    return {'name': name, 'expected_failure': expected_code, 'actual_failure': code,
        'passed': True, 'value': value, 'provenance': LABEL}


def main():
    example = json.loads((ROOT / 'verification/tool_graders_bvbrc_genome_alignment_inputs_2026-10-25/multiple_files_concatenated.json').read_text())
    task = deepcopy(example['inputs']['original_task'])
    task['task_id'] = 'SYNTHETIC_GA_001'
    task['submitted_parameters']['genome_ids'] = ['123.1', '456.2']
    task['submitted_parameters'].update(output_path='/synthetic', output_file='run')
    log = (b'Fetching genomes...\nFetching genome: 123.1\nWriting /task/work/123.1.fasta...\n'
           b'Fetching genome: 456.2\nWriting /task/work/456.2.fasta...\nRunning Mauve...\n'
           b'Running progressiveMauve with params:  --output=/task/work/alignment.xmfa\n'
           b'/task/work/123.1.fasta\n/task/work/456.2.fasta\n'
           b'Sequence loaded successfully.\nchild process exited with code 0\n')
    good, raw = make_log_record(task, log)
    results = [check_case('actual_log_bytes_match_reported_task', None, lambda: probe_argv(task, good, raw))]
    foreign = deepcopy(task)
    foreign['task_id'] = 'SYNTHETIC_FOREIGN_TASK'
    results.append(check_case('identical_bytes_wrong_task', PREFIX + 'metadata_task_conflict',
        lambda: probe_argv(foreign, good, raw)))
    changed = deepcopy(raw)
    native_ref = good['record']['value']['receipt']['snapshot']['content']['artifact_ref']
    changed[native_ref] = log + b'changed'
    results.append(check_case('native_log_digest_mismatch', PREFIX + 'content_digest_conflict',
        lambda: probe_argv(task, good, changed)))
    missing = {k: v for k, v in raw.items() if k != native_ref}
    results.append(check_case('native_log_bytes_missing', PREFIX + 'content_missing',
        lambda: probe_argv(task, good, missing)))
    truncated, truncated_raw = make_log_record(task, log, ref_name='partial', body_complete=False)
    results.append(check_case('whole_invocation_in_incomplete_transport_stays_unverified', PREFIX + 'invocation_missing',
        lambda: probe_argv(task, truncated, truncated_raw)))
    repeated, repeated_raw = make_log_record(task, log + log, ref_name='repeated')
    results.append(check_case('do_not_select_first_of_multiple_command_groups', PREFIX + 'invocation_conflict',
        lambda: probe_argv(task, repeated, repeated_raw)))
    altered = deepcopy(good)
    altered['record']['value']['task_id'] = 'SYNTHETIC_FORGED_VALUE'
    results.append(check_case('typed_value_disagrees_with_retained_envelope', PREFIX + 'metadata_record_unverified',
        lambda: probe_argv(task, altered, raw)))
    accepted, rejected = [], []
    for row, data in ((good, raw), (altered, raw)):
        try:
            checked, _ = check_record_mechanics(task, row, data)
            accepted.append(checked['task_id'])
        except ValueError as error:
            rejected.append(str(error))
    assert accepted == [task['task_id']] and rejected == [PREFIX + 'metadata_record_unverified']
    results.append({'name': 'per_record_recovery_preserves_valid_neighbor', 'passed': True,
        'accepted_tasks': accepted, 'rejected_codes': rejected, 'provenance': LABEL})

    # The real validator explicitly validates relationships, not historical truth.
    inputs = validate_genome_alignment_inputs(example['inputs'])
    asserted_lengths = [r['source_length'] for r in inputs['member_bindings']]
    for f in inputs['files']:
        f.update(path_state='unverified', same_run_state='unverified', genome_occurrence_indices=[],
                 same_run_evidence=[], requirement_ids=['run:' + f['file_id']])
    for m in inputs['member_bindings']:
        m.update(state='unverified', source_length=None, components=[], genome_occurrence_indices=[],
                 evidence=[], requirement_ids=[])
    inputs['invocation'].update(effective_recipe=None, recipe_basis='unknown', observed_argv=None,
        mode='unknown', mode_basis='unknown', ordered_file_ids=[], evidence=[])
    inputs['requirements'] = [{'requirement_id': 'run:' + f['file_id'], 'kind': 'byte_version_evidence',
        'role': 'genome_alignment_staged_input', 'source_refs': [f['content']['source_ref']],
        'reason_code': PREFIX + 'staged_file_run_unverified'} for f in inputs['files']]
    checked = validate_genome_alignment_inputs(inputs)
    assert [m['source_length'] for m in checked['member_bindings']] == [None, None]
    results.append({'name': 'shape_valid_same_run_assertion_is_not_admitted_by_custody', 'passed': True,
        'shape_valid_claimed_member_lengths': asserted_lengths,
        'after_no_native_witness_member_lengths': [m['source_length'] for m in checked['member_bindings']],
        'retained_file_record_lengths': [[len(r['sequence']) for r in f['records']] for f in checked['files']],
        'record_counts': [len(f['records']) for f in checked['files']],
        'genome_census_state': checked['genome_census_state'], 'provenance': example['provenance']})
    assoc_example = json.loads((ROOT / 'verification/tool_graders_bvbrc_genome_alignment_inputs_2026-10-25/explicit_interval_join.json').read_text())
    assoc = validate_genome_alignment_associations(assoc_example['associations'])
    results.append({'name': 'injective_typed_interval_map_has_no_native_export_witness', 'passed': True,
        'shape_valid_map': assoc['bbcols_interval_joins'][0],
        'admitted_state': 'unverified', 'admitted_xmfa_block_index': None,
        'reason_code': PREFIX + 'metadata_record_unverified', 'provenance': assoc_example['provenance']})

    manifest = {'id': task['task_id'], 'app': {'id': 'GenomeAlignment'},
        'parameters': task['submitted_parameters'], 'success': 0,
        'output_files': [['/synthetic/.run/alignment.xmfa', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa']]}
    object_binding = {'path': '/synthetic/run', 'uuid': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'type': 'job_result', 'metadata_receipt_ref': None}
    parsed = decode_job_result(canonical(manifest).encode(), original_task=task,
        object_binding=object_binding, evidence_ref='synthetic:manifest')
    assert parsed['records'][0]['association']['byte_version_status'] == 'unknown'
    assert parsed['value']['success'] == 0
    results.append({'name': 'manifest_records_object_even_on_failure_and_does_not_bind_bytes', 'passed': True,
        'native_success': parsed['value']['success'], 'output': parsed['records'][0],
        'provenance': LABEL})
    wrong = deepcopy(manifest)
    wrong['id'] = 'SYNTHETIC_OTHER_TASK'
    rejected_manifest = decode_job_result(canonical(wrong).encode(), original_task=task,
        object_binding=object_binding, evidence_ref='synthetic:wrong-manifest')
    assert rejected_manifest['status'] == 'invalid' and rejected_manifest['records'][0]['association'] is None
    results.append({'name': 'native_manifest_wrong_task_rejected', 'passed': True,
        'status': rejected_manifest['status'], 'provenance': LABEL})

    native = ROOT / 'verification/tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/native_examples'
    def artifact(path):
        data = path.read_bytes()
        return data, {'source_ref': 'retained-upstream-example:' + path.name,
            'raw_artifact_ref': 'artifact_' + hashlib.sha256(data).hexdigest(),
            'sha256': hashlib.sha256(data).hexdigest()}
    bbraw, bba = artifact(native / 'separate.xmfa.bbcols')
    xmraw, xma = artifact(native / 'separate.xmfa')
    bb = parse_mauve_bbcols(bbraw, artifact=bba, dialect='libmems_interval_columns_members_v1', encoding='ascii')
    xm = parse_mauve_xmfa(xmraw, artifact=xma, dialect='mauve1', alphabet='dna', encoding='ascii')
    assert bb['status'] == xm['status'] == 'ok'
    ranges = [r['columns_0based_half_open'] for r in bb['value']['rows']]
    assert ranges == [[33, 52], [0, 33]]
    results.append({'name': 'authentic_upstream_native_numbers_survive_missing_run_join', 'passed': True,
        'bbcols_column_ranges': ranges, 'native_interval_indices': [r['native_interval_index_0based']['value'] for r in bb['value']['rows']],
        'bbcols_unique_columns': 52, 'xmfa_observed_blocks': len(xm['value']['blocks']),
        'interval_join_state': 'unverified', 'bbcols_sha256': bba['sha256'], 'xmfa_sha256': xma['sha256'],
        'provenance': 'Authentic retained upstream bytes; no original BV-BRC task/run/producer proof'})
    output = {'created_at': datetime.now(timezone.utc).isoformat(), 'scope': __doc__,
        'synthetic_stdout_ascii': log.decode(), 'synthetic_retained_record': good,
        'case_count': len(results), 'passed': all(r['passed'] for r in results), 'results': results,
        'actual_execution': 'Offline Python only; existing validators/readers plus small boundary mechanics. No Store authentication, native program, service or episode execution.'}
    destination = HERE / 'BOUNDARY_PROBES_001.json'
    with destination.open('x') as f:
        json.dump(output, f, indent=2)
        f.write('\n')
    print(json.dumps({'case_count': output['case_count'], 'passed': output['passed'],
        'argv': results[0]['value'], 'native_bbcols_unique_columns': 52,
        'missing_staged_member_lengths': [None, None], 'output': str(destination.relative_to(ROOT))}))


if __name__ == '__main__':
    main()
