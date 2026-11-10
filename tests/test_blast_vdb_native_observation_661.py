"""One selected evidence-collection attempt; native failure remains a failure.

Run only through bounded529. This test introduces no production capability.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

from gene_annotation_episode.blast_vdb_inputs import read_blast_vdb_sequence_table


def pin(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return {'path': str(path), 'size_bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def split_args(text):
    result, start, depth, quoted, escaped = [], 0, 0, False, False
    for index, character in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif character == '\\':
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in '([{':
            depth += 1
        elif character in ')]}':
            depth -= 1
        elif character == ',' and depth == 0:
            result.append(text[start:index].strip())
            start = index + 1
    result.append(text[start:].strip())
    return result


def trace_integer(token):
    """strace retains C integer spelling, including umask's octal result."""
    sign = -1 if token.startswith('-') else 1
    magnitude = token.lstrip('-')
    base = 16 if magnitude.startswith('0x') else 8 if len(magnitude) > 1 and magnitude.startswith('0') else 10
    return sign * int(magnitude, base)


def trace_evidence(contents, selection, observation_returncode, stderr):
    """Conservative syscall facts; unfamiliar/unbound content stays unresolved."""
    text = contents.decode('utf-8', errors='strict')
    pending, events, unparsed = {}, [], []
    for number, line in enumerate(text.splitlines(), 1):
        prefix = re.fullmatch(r'\s*(\d+)\s+(\d+\.\d+)\s+(.*)', line)
        if prefix is None:
            unparsed.append({'line_number': number, 'raw': line})
            continue
        pid, timestamp, body = int(prefix[1]), prefix[2], prefix[3]
        lines = [number]
        if body.endswith('<unfinished ...>'):
            pending[pid] = (body[:-len('<unfinished ...>')], number)
            continue
        resumed = re.match(r'<\.\.\. (\w+) resumed>(.*)', body)
        if resumed:
            prior = pending.pop(pid, None)
            if prior is None or not prior[0].startswith(resumed[1] + '('):
                unparsed.append({'line_number': number, 'raw': line})
                continue
            body, lines = prior[0] + resumed[2], [prior[1], number]
        match = re.fullmatch(r'(\w+)\((.*)\)\s+=\s+(.*)', body)
        if match is None:
            if not body.startswith(('--- ', '+++ ')):
                unparsed.append({'line_number': number, 'raw': line})
            continue
        result = re.match(r'(-?(?:0x[0-9a-f]+|\d+))(?:\b|<)', match[3])
        events.append(dict(pid=pid, timestamp=timestamp, syscall=match[1], arguments=match[2],
                           result=match[3], result_integer=trace_integer(result[1]) if result else None,
                           source_line_numbers=lines))
    pins = {row['path']: row for row in selection['runtime_pins'] + selection['selected_inputs']}
    namespace = {row['namespace_path']: row['host_path'] for row in selection['namespace_file_bindings']}
    interfaces = set(selection['permitted_system_interfaces'])
    descriptors, bindings, unexpected, networks, helper_execs, namespace_events = {}, [], [], [], [], []
    ipc, socket_events = [], []
    exits, failed_accesses = {}, []

    def classify(path, pid):
        if path is None:
            return 'unresolved_descriptor', None
        system_path = re.sub(r'^/proc/' + str(pid) + r'/', '/proc/self/', path)
        if system_path in interfaces:
            return 'declared_system_interface', None
        original = namespace.get(path, path)
        try:
            original = str(Path(original).resolve(strict=True))
        except OSError:
            pass
        if original in pins:
            return 'declared_before_pinned_file', pins[original]
        if path.startswith(('socket:', 'UNIX', 'TCP', 'UDP', 'NETLINK', 'pipe:', 'anon_inode:')):
            return 'undeclared_socket_or_ipc', None
        return 'undeclared_file_content', None

    for event in events:
        pid, call, raw, result = event['pid'], event['syscall'], event['arguments'], event['result_integer']
        args = split_args(raw)
        if call in ('open', 'openat', 'openat2') and result is not None:
            if result >= 0:
                named = re.match(r'\d+<([^>]+)>', event['result'])
                path = named[1] if named else None
                descriptors[(pid, result)] = dict(path=path, open_source_line_numbers=event['source_line_numbers'],
                                                 opened_by_pid=pid)
            else:
                failed_accesses.append(event)
        elif call in ('clone', 'clone3', 'fork', 'vfork') and result is not None and result > 0:
            for (parent, fd), value in list(descriptors.items()):
                if parent == pid:
                    descriptors[(result, fd)] = dict(value)
        elif call in ('dup', 'dup2', 'dup3') and result is not None and result >= 0:
            fd = re.match(r'(\d+)', args[0])
            if fd and (pid, int(fd[1])) in descriptors:
                descriptors[(pid, result)] = dict(descriptors[(pid, int(fd[1]))])
        if call == 'execve' and result == 0 and args[0] == '"/native/blast_vdb_cmd"':
            helper_execs.append(event)
        if call in ('clone', 'clone3', 'unshare', 'setns') and 'CLONE_NEWNET' in raw:
            namespace_events.append(event)
        if call in ('exit', 'exit_group'):
            try:
                exits[pid] = int(args[0])
            except ValueError:
                pass
        content = call in ('read', 'readv', 'pread64', 'preadv', 'preadv2') and result is not None and result > 0
        mapping = call in ('mmap', 'mmap2') and result is not None and result >= 0 and len(args) >= 5
        fdtext = args[0] if content else args[4] if mapping else None
        fdmatch = re.fullmatch(r'(\d+)(?:<([^>]+)>)?', fdtext or '')
        if fdmatch:
            fd = int(fdmatch[1])
            original_open = descriptors.get((pid, fd))
            path = fdmatch[2] or (original_open or {}).get('path')
            classification, before_pin = classify(path, pid)
            row = dict(pid=pid, syscall=call, file_descriptor=fd, observed_descriptor_path=path,
                       source_line_numbers=event['source_line_numbers'], result=event['result'],
                       byte_count=result if content else None,
                       mapping_length=int(args[1]) if mapping and args[1].isdigit() else None,
                       original_open=original_open, classification=classification, before_pin=before_pin)
            bindings.append(row)
            if classification.startswith(('undeclared_', 'unresolved_')) or (
                    classification == 'declared_before_pinned_file' and original_open is None):
                unexpected.append(row)
            if classification == 'undeclared_socket_or_ipc':
                ipc.append(row)
                if path is None or path.startswith(('socket:', 'TCP', 'UDP')):
                    networks.append(row)
        elif content:
            unexpected.append(dict(pid=pid, syscall=call, source_line_numbers=event['source_line_numbers'],
                                   classification='unparsed_content_descriptor', arguments=raw))
        if call in ('socket', 'socketpair', 'connect', 'accept', 'accept4', 'sendto', 'sendmsg',
                    'recvfrom', 'recvmsg', 'recvmmsg', 'shutdown'):
            socket_events.append(event)
        if call in ('recvfrom', 'recvmsg', 'recvmmsg') and result is not None and result > 0:
            ipc.append(event)
            # NETLINK is the local kernel namespace-setup exchange, not remote molecular content.
            # It remains an undeclared IPC evidence gap in this preselected attempt.
            if re.match(r'\d+<NETLINK:', args[0]) is None:
                networks.append(event)
            unexpected.append(dict(pid=pid, syscall=call, source_line_numbers=event['source_line_numbers'],
                                   classification='undeclared_socket_or_ipc', arguments=raw, result=event['result']))
        if call == 'close' and result == 0:
            fd = re.match(r'(\d+)', args[0])
            if fd:
                descriptors.pop((pid, int(fd[1])), None)
    all_pids = sorted({row['pid'] for row in events})
    trace_errors = [line for line in stderr.decode('utf-8', errors='replace').splitlines()
                    if line.startswith(('strace:', '/usr/bin/strace:'))]
    trace_complete = bool(events) and not pending and not unparsed and not trace_errors and all(pid in exits for pid in all_pids)
    helper_returncode = exits.get(helper_execs[0]['pid']) if len(helper_execs) == 1 else None
    config_reads = [row for row in bindings if row['observed_descriptor_path'] == '/config/offline.kfg'
                    and row['syscall'] in ('read', 'readv', 'pread64', 'preadv', 'preadv2', 'mmap', 'mmap2')]
    network_namespace = any(event['result_integer'] is not None and event['result_integer'] >= 0
                            for event in namespace_events)
    return dict(trace_complete=trace_complete, traced_pids=all_pids, exit_status_by_pid=exits,
                event_count=len(events), unmatched_syscall_fragments=pending, unparsed_trace_lines=unparsed,
                trace_diagnostics=trace_errors, helper_exec_events=helper_execs, helper_returncode=helper_returncode,
                network_namespace_observed=network_namespace, namespace_events=namespace_events,
                config_read_observed=bool(config_reads), config_read_events=config_reads,
                file_read_bindings=bindings, unexpected_reads=unexpected,
                network_content_observed=bool(networks) if trace_complete else None,
                network_content_events=networks, socket_or_ipc_content_events=ipc,
                socket_events=socket_events, failed_file_accesses=failed_accesses,
                interpretation='syscall_facts_only_no_offline_binding_or_production_success_claim')


def companion_records(contents):
    rows = []
    for number, line in enumerate(contents.decode('ascii').splitlines(), 1):
        if line.startswith('>'):
            rows.append(dict(defline=line[1:], line_number=number, sequence=''))
        else:
            assert rows and line and not any(c.isspace() for c in line)
            rows[-1]['sequence'] += line
    return rows


def test_selected_native_observation():
    attempt = Path(os.environ['HMMER529_ATTEMPT']).resolve(strict=True)
    snapshot = Path(__file__).resolve().parents[1]
    packet = snapshot / 'verification/tool_graders_blast_vdb_native_observation_2026-10-28_661'
    selection = json.loads((packet / 'SELECTED_REQUEST.json').read_text())
    assert str(attempt) == selection['attempt_path']
    handle = json.loads((attempt / 'handle.json').read_text())
    assert handle['stage'] == 'released'
    assert handle['metadata']['policy'] == {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
    assert handle['metadata']['verified_cgroup']['memory_max'] == 21474836480
    assert handle['metadata']['verified_cgroup']['memory_swap_max'] == 0
    assert 'runtime_max' not in handle['metadata']['verified_cgroup']
    registered = json.loads((attempt / 'native_library_pins_before.json').read_text())
    registered_by_path = {row['path']: row for row in registered}
    before = selection['runtime_pins'] + selection['selected_inputs']
    assert [pin(row['path']) for row in before] == before
    assert all(registered_by_path[row['path']] == row for row in selection['runtime_pins'])
    applied = dict(selection)
    native = Path(selection['observation_cwd'])
    native.mkdir(exist_ok=False)
    (native / 'work/cache').mkdir(parents=True)
    (native / 'tmp').mkdir()
    stdout, stderr, trace = native / 'stdout.bin', native / 'stderr.bin', native / 'syscalls.log'
    assert selection['helper_argv'][6] == '%i\t%a\t%l\t%s'
    applied.update(started_at=datetime.now(timezone.utc).isoformat(),
                   bounded_handle_pin=pin(attempt / 'handle.json'),
                   bounded_cgroup_membership=Path('/proc/self/cgroup').read_text(),
                   inherited_descriptors='stdin_devnull_stdout_file_stderr_file_close_fds_true',
                   fresh_work_files=[], fresh_tmp_files=[])
    save(native / 'applied_request.json', applied)
    save(native / 'pins_before.json', before)
    with stdout.open('xb') as out, stderr.open('xb') as err:
        process = subprocess.Popen(selection['observation_argv'], cwd=native,
                                   env=selection['observation_environment'], stdin=subprocess.DEVNULL,
                                   stdout=out, stderr=err, close_fds=True)
        # The enclosing durable service enforces the selected resources. No timeout or retry.
        returncode = process.wait()
    after = [pin(row['path']) for row in before]
    save(native / 'pins_after.json', after)
    stdout_bytes, stderr_bytes = stdout.read_bytes(), stderr.read_bytes()
    finish_observation(selection, applied, handle, attempt, native, native,
                       returncode, process.pid, before, after, stdout_bytes, stderr_bytes)


def finish_observation(selection, applied, handle, attempt, native, destination,
                       returncode, process_pid, before, after, stdout_bytes, stderr_bytes):
    stdout, stderr, trace = native / 'stdout.bin', native / 'stderr.bin', native / 'syscalls.log'
    evidence = (trace_evidence(trace.read_bytes(), selection, returncode, stderr_bytes)
                if trace.exists() else dict(trace_complete=False, helper_exec_events=[], helper_returncode=None,
                    network_namespace_observed=None, config_read_observed=None, file_read_bindings=[],
                    unexpected_reads=[], network_content_observed=None, trace_diagnostics=['trace_file_absent']))
    save(destination / 'trace_evidence.json', evidence)
    lexical = read_blast_vdb_sequence_table(stdout_bytes, source_ref=str(stdout),
                                           source_version=selection['helper_pin']['sha256'])
    save(destination / 'lexical_table.json', lexical)
    companion_path = next(Path(row['path']) for row in selection['selected_inputs'] if row['path'].endswith('.fasta'))
    companion = companion_records(companion_path.read_bytes())
    assert len(companion) == 20 and all(len(row['sequence']) == 250 for row in companion)
    comparisons = []
    helper_started = bool(evidence['helper_exec_events'])
    for ordinal, expected in enumerate(companion[:2]):
        actual = lexical['rows'][ordinal] if ordinal < len(lexical['rows']) and helper_started else None
        fields = actual['fields'] if actual else None
        comparisons.append(dict(expected_companion_ordinal=ordinal, companion_defline=expected['defline'],
            companion_sequence=expected['sequence'], companion_length=len(expected['sequence']),
            companion_sequence_sha256=hashlib.sha256(expected['sequence'].encode('ascii')).hexdigest(),
            native_row_ordinal=actual['row_ordinal'] if actual else None,
            length_equal=actual['native_reported_length'] == len(expected['sequence']) if actual else None,
            sequence_equal=fields['sequence_symbols'] == expected['sequence'] if fields else None,
            selector_equal=fields['native_identifier'] == selection['helper_argv'][4].split(',')[ordinal] if fields else None))
    actual_rows = None if not helper_started else [dict(
        row_ordinal=row['row_ordinal'], line_number=row['line_number'],
        native_identifier=row['fields']['native_identifier'] if row['fields'] else None,
        native_accession=row['fields']['native_accession'] if row['fields'] else None,
        native_reported_length=row['native_reported_length'],
        sequence=row['fields']['sequence_symbols'] if row['fields'] else None,
        lexical_issues=row['issues']) for row in lexical['rows']]
    unverified = ['production_utility_integration', 'requested_episode_return', 'info_and_paths_modes',
                  'all_entry_reference_filtered_WGS_alias_modes', 'full_run_census_sample_and_clipping_semantics']
    if not helper_started:
        unverified += ['helper_execution', 'helper_returncode', 'returned_native_identifiers_accessions_lengths_sequences',
                       'companion_equality', 'helper_config_application', 'helper_offline_dependency_closure']
    if not evidence['trace_complete']:
        unverified += ['complete_syscall_coverage']
    if evidence['unexpected_reads']:
        unverified += ['all_file_content_reads_declared_before_execution']
    if not evidence['network_namespace_observed']:
        unverified += ['successful_separate_network_namespace']
    if not evidence['config_read_observed']:
        unverified += ['actual_offline_configuration_read']
    result = dict(schema='blast_vdb_native_observation_v1', selected_request=applied,
        resource_receipt={'handle_path': str(attempt / 'handle.json'), 'verified_metadata': handle['metadata'],
                          'terminal_receipt_path': str(attempt / 'receipt.json'), 'terminal': None, 'quiescent': None},
        native_outcome={'observation_returncode': returncode, 'helper_exec_observed': helper_started,
                        'helper_returncode': evidence['helper_returncode'],
                        'state': 'helper_not_executed' if not helper_started else 'helper_executed_observed',
                        'stderr_utf8': stderr_bytes.decode('utf-8', errors='replace'),
                        'observation_pid': process_pid,
                        'observation_returncode_basis': 'saved_process_wait_result' if returncode is not None else 'not_persisted_before_original_postprocessing_failure',
                        'analysis_at': datetime.now(timezone.utc).isoformat()},
        archive_config_runtime_before_after={'before': before, 'after': after, 'unchanged': before == after},
        config_read_observed=evidence['config_read_observed'],
        network_namespace_observed=evidence['network_namespace_observed'],
        trace_complete=evidence['trace_complete'], file_read_bindings=evidence['file_read_bindings'],
        unexpected_reads=evidence['unexpected_reads'], network_content_observed=evidence['network_content_observed'],
        streams={'stdout': pin(stdout), 'stderr': pin(stderr), 'trace': pin(trace) if trace.exists() else None,
                 'stream_owner': 'observation_process_tree', 'writers_closed': True},
        trace_evidence=pin(destination / 'trace_evidence.json'), lexical_table=pin(destination / 'lexical_table.json'),
        returned_rows=actual_rows, companion_equality_checks=comparisons,
        new_work_tmp_files=[pin(p) for root in (native / 'work', native / 'tmp')
                            for p in sorted(root.rglob('*')) if p.is_file()],
        unverified_items=unverified, offline_binding_created=False, scientific_scores_created=False,
        evidence_collection_test_does_not_establish_native_success=True)
    receipt_path = attempt / 'receipt.json'
    if receipt_path.is_file():
        result['resource_receipt'].update(json.loads(receipt_path.read_text()))
        result['resource_receipt']['receipt_pin'] = pin(receipt_path)
    result['config_read_mechanisms'] = sorted({row['syscall'] for row in evidence.get('config_read_events', [])})
    result['socket_or_ipc_content_observed'] = bool(evidence.get('socket_or_ipc_content_events', []))
    result['offline_closure_verified'] = False
    if result['unexpected_reads']:
        result['unverified_items'].append('predeclared_system_interface_and_IPC_closure')
    result['helper_environment_observed'] = None
    if evidence['helper_exec_events']:
        result['helper_environment_observed'] = split_args(evidence['helper_exec_events'][0]['arguments'])[2]
    save(destination / 'NATIVE_OBSERVATION.json', result)
    assert before == after
    assert not result['offline_binding_created'] and not result['scientific_scores_created']
    if not helper_started:
        assert result['returned_rows'] is None
        assert all(row['sequence_equal'] is None for row in comparisons)
    print(json.dumps({'observation_returncode': returncode, 'helper_exec_observed': helper_started,
                      'helper_returncode': evidence['helper_returncode'], 'trace_complete': evidence['trace_complete'],
                      'result_path': str(destination / 'NATIVE_OBSERVATION.json')}))
    return result, evidence


def test_saved_native_observation(monkeypatch):
    """Read one retained attempt only; never invoke the operation again."""
    import socket
    def forbidden(*args, **kwargs):
        raise AssertionError('saved_verification_must_not_launch_or_acquire')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    current = Path(os.environ['HMMER529_ATTEMPT']).resolve(strict=True)
    snapshot = Path(__file__).resolve().parents[1]
    packet = snapshot / 'verification/tool_graders_blast_vdb_native_observation_2026-10-28_661'
    selection = json.loads((packet / 'SELECTED_REQUEST.json').read_text())
    attempt = Path(selection['attempt_path'])
    assert current.name == 'check121b_vdb_native661_saved' and current != attempt
    native = attempt / 'temporary/native_observation'
    expected = json.loads((packet / 'SAVED_INPUT_PINS.json').read_text())
    assert [pin(row['path']) for row in expected] == expected
    original_receipt = json.loads((attempt / 'receipt.json').read_text())
    original_audit = json.loads((attempt / 'execution_audit.json').read_text())
    assert original_receipt['terminal'] is True and original_receipt['quiescent'] is True
    assert original_receipt['returncode'] == original_audit['pytest_returncode'] == 1
    assert original_audit['outside_modules'] == original_audit['unbound_mappings'] == []
    assert original_audit['native_unchanged'] and original_audit['original_retained_fixtures_unchanged']
    assert trace_integer('002') == 2 and trace_integer('010') == 8
    assert trace_integer('-1') == -1 and trace_integer('0x10') == 16
    # Parsing stays tied to the literal C representation; unknown spellings fail visibly.
    applied = json.loads((native / 'applied_request.json').read_text())
    before = json.loads((native / 'pins_before.json').read_text())
    after = json.loads((native / 'pins_after.json').read_text())
    assert [pin(row['path']) for row in before] == before == after
    destination = current / 'temporary/saved_observation'
    destination.mkdir(exist_ok=False)
    result, evidence = finish_observation(selection, applied, json.loads((attempt / 'handle.json').read_text()),
        attempt, native, destination, None, None, before, after,
        (native / 'stdout.bin').read_bytes(), (native / 'stderr.bin').read_bytes())
    assert result['native_outcome']['helper_exec_observed'] is True
    assert result['native_outcome']['helper_returncode'] == 0
    assert len(result['returned_rows']) == 2
    assert all(row['length_equal'] and row['sequence_equal'] and row['selector_equal']
               for row in result['companion_equality_checks'])
    assert result['returned_rows'][0]['native_accession'] == 'SRA:ERR3487613.1.1'
    assert result['returned_rows'][1]['native_accession'] == 'SRA:ERR3487613.1.2'
    assert result['network_namespace_observed'] is True
    assert result['config_read_observed'] is True
    assert result['offline_closure_verified'] is False
    assert [pin(row['path']) for row in expected] == expected
    save(destination / 'SAVED_VERIFICATION.json', dict(schema='blast_vdb_native_saved_verification_v1',
        original_attempt_path=str(attempt), original_receipt=original_receipt,
        original_test_failure_preserved=True, helper_not_rerun=True,
        strace_not_rerun=True, bwrap_not_rerun=True, no_acquisition=True,
        native_stdout_bytes=result['streams']['stdout']['size_bytes'],
        input_pins_before=expected, input_pins_after=[pin(row['path']) for row in expected],
        original_native_outcome=result['native_outcome'],
        trace_complete=result['trace_complete'], unexpected_reads_count=len(result['unexpected_reads']),
        source_module_pin=pin(__file__), lexical_reader_module_pin=pin(snapshot / 'gene_annotation_episode/blast_vdb_inputs.py')))
