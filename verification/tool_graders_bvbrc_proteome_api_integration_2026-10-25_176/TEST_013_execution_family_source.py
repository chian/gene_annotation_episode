"""The launch family preserves explicit operands and original native custody.

No model, HTTP endpoint, SSH connection or PBS scheduler runs in these checks.
The local native test executes only its own small project-storage job.
"""
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import (ExecutionEpisodes, LAUNCH_VERSION,
    RESULTS_VERSION, NATIVE_RESULT_ORIGIN)
from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def native_assignment(workspace, resource_id='here', *, kind='local', argv=None):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'fixed-request-'+resource_id,
        'resource_id': resource_id, 'resource_kind': kind, 'workspace': str(workspace),
        'endpoint': 'usable_handoff', 'requested_job': {'argv': argv or ['/bin/true'], 'environment': {}},
        'progress_requirements': [{'key': 'handoff', 'credit': 7,
            'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['handoff'],
        'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {}}


def launch_assignment(requests, *, constraints=None, versions=None):
    return {'version': LAUNCH_VERSION, 'requests': deepcopy(requests),
        'immutable_input_versions': versions or [], 'constraints': constraints or {}}


@pytest.fixture
def host(tmp_path):
    workspace = tmp_path/'project'
    workspace.mkdir()
    store = Store(tmp_path/'store')
    target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
    journal = Journal(store, 'family-fixture')
    configuration = {'kind': 'local', 'workspace': str(workspace), 'policy': {
        'memory_bytes': 128*1024**2, 'scratch_bytes': 8*1024**2, 'wall_seconds': None}}
    family = ExecutionEpisodes(None, store=store, directory=tmp_path/'run', run_id=journal.run_id,
        resources={'here': configuration}, initial_information={}, tool_registry=ToolRegistry(store),
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=4, log_roles=['stdout', 'stderr'])
    yield SimpleNamespace(store=store, journal=journal, family=family, workspace=workspace,
        scope={'subject_refs': [target]}, target=target, tmp_path=tmp_path)
    store.close()


def context(h, role, assignment, episode_id, *, path=None):
    path = path or ((role, episode_id),)
    request = {'message': {'scope': h.scope, 'episode_assignment': deepcopy(assignment)}}
    value = BindingContext(h.journal.run_id, episode_id, role, path, h.scope, assignment, request)
    with h.store.transaction():
        h.journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'running'})
    return value


def select(h, ctx, index, name, arguments=None):
    arguments = arguments or {}
    key = f'{ctx.run_id}:{ctx.episode_id}:{index}'
    with h.store.transaction():
        h.journal.save('runtime_actions', {'episode_id': ctx.episode_id, 'decision_index': index,
            'action': canonical({'kind': 'tool', 'tool': name, 'arguments': arguments}),
            'result': None, 'credit': None})
    result = asyncio.run(h.family.execute(ctx, name, arguments, key))
    with h.store.transaction():
        h.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? '
            'AND decision_index=?', (canonical(result), ctx.run_id, ctx.episode_id, index))
    return result


def selection(ctx, references, initial=()):
    return {'run_id': ctx.run_id, 'episode_id': ctx.episode_id, 'known_record_refs': list(references),
            'initial_known_record_refs': list(initial)}


def test_one_owner_and_data_descriptor_reconstruct_all_operands(host):
    h = host
    registry = EpisodeBindingRegistry([h.family])
    assert registry.roles == ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')
    assert registry.entry_roles == ('launch', 'results')
    record = h.family.as_record()
    assert record['binding_id'] == 'execution_episodes'
    restored = ExecutionEpisodes(None, store=h.store, directory=h.tmp_path/'restored',
        run_id=h.journal.run_id, tool_registry=h.family.tool_registry, **record['configuration'])
    assert restored.as_record() == record
    assert restored.api_execution is None
    assert h.family.initial_decision_context(None)['execution_resource_capabilities'][0] == {
        'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(h.workspace),
        'availability': 'unknown', 'tool_names': h.family.capabilities()[0]['tool_names'],
        'policy': h.family.resources['here']['policy'], 'inventory_snapshot': None}
    with pytest.raises(ValueError, match='duplicate_episode_role'):
        registry.register(restored)


def test_dynamic_resources_keep_several_hpcs_and_explicit_selected_request(host):
    h = host
    resources = {}
    requests = {}
    for resource_id in ('hpc-one', 'hpc-two'):
        path = h.workspace/resource_id
        resources[resource_id] = {'kind': 'pbs_ssh', 'workspace': str(path),
            'ssh_argv': ['unexecuted-ssh', resource_id], 'python_executable': '/usr/bin/python3',
            'account': 'EpiCalib'}
        requests[resource_id] = native_assignment(path, resource_id, kind='hpc')
    family = ExecutionEpisodes(None, store=h.store, directory=h.tmp_path/'hpc-run', run_id=h.journal.run_id,
        resources=resources, initial_information={}, tool_registry=h.family.tool_registry,
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=4, log_roles=['stdout'])
    parent = context(h, 'launch', launch_assignment(requests), 'parent')
    assert family.allowed_children(parent, []) == ('launch_hpc',)
    selected = family.prepare_assignment(parent, 'launch_hpc', requests['hpc-two'], h.scope, 'unexecuted')
    assert selected == requests['hpc-two']
    changed = deepcopy(selected)
    changed['requested_job']['argv'] = ['/bin/false']
    with pytest.raises(ValueError, match='original_request_conflict'):
        family.prepare_assignment(parent, 'launch_hpc', changed, h.scope, 'unexecuted')
    changed = deepcopy(selected)
    changed.pop('resource_id')
    with pytest.raises(ValueError, match='invalid_execution_assignment'):
        family.prepare_assignment(parent, 'launch_hpc', changed, h.scope, 'unexecuted')
    assert set(family.assignment_schema('launch')['properties']['requests']['properties']) == set(resources)


def test_api_request_keeps_typed_service_job_and_its_explicit_resource(host):
    h = host
    resources = {'service-two': {'kind': 'hmmer_api', 'service': 'ebi_hmmer'}}
    family = ExecutionEpisodes(None, store=h.store, directory=h.tmp_path/'api-run', run_id=h.journal.run_id,
        resources=resources, initial_information={}, tool_registry=h.family.tool_registry,
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=4, log_roles=[])
    request = {'version': 'api_execution_assignment_v1', 'resource_id': 'service-two',
        'service': 'ebi_hmmer', 'subject_ref': h.target, 'algorithm': 'phmmer', 'database': 'reference',
        'parameters': {'E': .01}, 'page_size': 10, 'endpoint': 'usable_handoff', 'constraints': {}}
    parent = context(h, 'launch', launch_assignment({'service-two': request}), 'api-parent')
    assert family.allowed_children(parent, []) == ('launch_api',)
    selected = family.prepare_assignment(parent, 'launch_api', request, h.scope, 'unexecuted')
    assert selected == request and 'requested_job' not in selected
    child = context(h, 'launch_api', request, 'api-child',
        path=(('launch', 'api-parent'), ('launch_api', 'api-child')))
    family.initialize(child)  # Pure assignment custody, no service operation.
    assert {entry['name'] for entry in family.catalog(child)} == {'api.hmmer.databases',
        'api.hmmer.prepare', 'api.hmmer.submit', 'api.hmmer.status', 'api.hmmer.check_handoff'}
    changed = deepcopy(request)
    changed['database'] = 'different'
    with pytest.raises(ValueError, match='original_request_conflict'):
        family.prepare_assignment(parent, 'launch_api', changed, h.scope, 'unexecuted')


def test_parent_constraints_input_versions_and_instruction_pins_are_preserved(host):
    h = host
    request = native_assignment(h.workspace)
    request['constraints'] = {'memory_bytes': 128*1024**2}
    parent_assignment = launch_assignment({'here': request}, constraints={'allowed_resource_ids': ['here'],
        'allowed_kinds': ['local'], 'memory_bytes': 128*1024**2})
    parent = context(h, 'launch', parent_assignment, 'parent')
    assert h.family.prepare_assignment(parent, 'launch_local', request, h.scope, 'unexecuted') == request
    missing_constraint = deepcopy(parent_assignment)
    missing_constraint['constraints']['scratch_bytes'] = 8*1024**2
    with pytest.raises(ValueError, match='parent_constraint_conflict'):
        h.family.prepare_assignment(replace(parent, assignment=missing_constraint), 'launch_local',
            request, h.scope, 'unexecuted')
    restricted = deepcopy(parent_assignment)
    restricted['constraints']['allowed_resource_ids'] = ['elsewhere']
    assert h.family.allowed_children(replace(parent, assignment=restricted), []) == ()
    with pytest.raises(ValueError, match='resource_selection_conflict'):
        h.family.prepare_assignment(replace(parent, assignment=restricted), 'launch_local', request, h.scope, 'unexecuted')
    pin = {'version': 'launch_instruction_selection_v1', 'library_id': 'launch_instructions_'+'a'*64,
        'sections': [{'entry_id': 'software', 'section_id': 'run', 'sha256': 'b'*64}]}
    pinned = deepcopy(parent_assignment)
    pinned['launch_instructions'] = pin
    with pytest.raises(ValueError, match='inheritance_conflict'):
        h.family.prepare_assignment(replace(parent, assignment=pinned), 'launch_local', request, h.scope, 'unexecuted')
    selected = {**request, 'launch_instructions': pin}
    assert h.family.prepare_assignment(replace(parent, assignment=pinned), 'launch_local', selected,
        h.scope, 'unexecuted')['launch_instructions'] == pin
    subject = h.store.get(h.target)
    versions = [{'reference': h.target, 'version': None, 'content_sha256': hashlib.sha256(
        h.store.get_artifact(subject['sequence_ref'])).hexdigest()}]
    valid = launch_assignment({'here': request}, versions=versions)
    assert h.family.prepare_assignment(parent, 'launch', valid, h.scope, 'unexecuted') == valid
    versions[0]['content_sha256'] = '0'*64
    invalid = launch_assignment({'here': request}, versions=versions)
    with pytest.raises(ValueError, match='input_version_conflict'):
        h.family.prepare_assignment(parent, 'launch', invalid, h.scope, 'unexecuted')


def launched_local(h):
    output = h.workspace/'result.bin'
    request = native_assignment(h.workspace, argv=[sys.executable, '-c',
        'from pathlib import Path; Path('+repr(str(output))+').write_bytes(bytes(range(10)))'])
    parent = context(h, 'launch', launch_assignment({'here': request}), 'launch-parent')
    child = context(h, 'launch_local', request, 'native-child',
        path=(('launch', 'launch-parent'), ('launch_local', 'native-child')))
    h.family.initialize(child)
    outcome = select(h, child, 0, 'practical.job.start')
    assert outcome['status'] == 'completed'
    handle = native.NativeJobHandle(Path(outcome['result']['outcome']['facts']['requested_job']['execution_id']))
    assert native.wait_job(handle).returncode == 0
    return parent, child, outcome, output


def test_actual_local_delegation_received_credit_and_parent_endpoint_proof(host, monkeypatch):
    h = host
    parent, child, outcome, output = launched_local(h)
    reference, = outcome['record_refs']
    assert h.family.state(child).credit_view()['credit'] == 7
    assert h.family.facts(child, {})['execution_handoff_refs'] == [reference]
    before = h.family.state(child).receipts()
    assert h.family.project_credit(parent, selection(parent, []))['credit'] == 0
    assert h.family.project_credit(parent, selection(parent, [reference, reference]))['credit'] == 3
    assert h.family.project_credit(parent, selection(parent, [reference], [reference]))['credit'] == 0
    with h.store.transaction():
        h.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': 0,
            'action': canonical({'kind': 'episode_child', 'role': 'launch_local', 'assignment': plain(child.assignment)}),
            'result': canonical({'status': 'completed', 'record_refs': [reference], 'changed_record_refs': []}), 'credit': 3})
    key = f'{parent.run_id}:{parent.episode_id}:0'
    proof = h.family.completion_for_action(parent, key)
    assert proof['endpoint'] == 'usable_handoff'
    assert h.family.verify_completion(parent, proof)
    changed = {**proof, 'receipt_sha256': '0'*64}
    assert not h.family.verify_completion(parent, changed)
    monkeypatch.setattr(LocalPracticalOperations, 'execute', lambda *a, **k: pytest.fail('proof must not execute'))
    monkeypatch.setattr(h.family.job_progress_provider.targets, 'observe_target', lambda *a, **k: pytest.fail('proof must not observe'))
    assert h.family.verify_completion(parent, proof)
    assert h.family.state(child).receipts() == before
    form_schema = {'type': 'object', 'properties': {
        'handoffs': h.family.fact_sources('launch')['execution_handoff_refs']['report_schema'],
        'completed': {'type': 'boolean', 'x-source': 'execution_completed'}},
        'required': ['handoffs', 'completed'], 'additionalProperties': False}
    h.family.validate_report(parent, {'handoffs': [reference], 'completed': True}, form_schema)
    with pytest.raises(ValueError, match='disagrees_with_recorded_facts'):
        h.family.validate_report(parent, {'handoffs': [], 'completed': True}, form_schema)


def test_results_actual_bounded_windows_exact_replay_completion_and_unchanged_launch(host, monkeypatch):
    h = host
    _, child, original, output = launched_local(h)
    reference, = original['record_refs']
    before = deepcopy(h.family.state(child).receipts())
    assignment = {'version': RESULTS_VERSION, 'handoff_ref': reference, 'selector': {'paths': [str(output)]}}
    receiver = context(h, 'results', assignment, 'result-receiver')
    h.family.initialize(receiver)
    first = select(h, receiver, 0, 'execution.results.collect')
    window, = first['result']['windows']
    assert base64.b64decode(window['bytes_base64']) == bytes(range(4))
    assert h.family.completion_for_action(receiver, f'{receiver.run_id}:{receiver.episode_id}:0') is None
    second = select(h, receiver, 1, 'execution.results.read', {'path': str(output), 'offset': 4, 'limit': 6})
    proof = h.family.completion_for_action(receiver, f'{receiver.run_id}:{receiver.episode_id}:1')
    assert proof['endpoint'] == 'usable_handoff'
    assert proof['validation_keys'] == ['requested_filesystem_acquisition',
        'successful_exact_attempt_observed', 'attempt_output_version_unverified']
    assert h.family.verify_completion(receiver, proof)
    assert h.family.completion_for_action(receiver, f'{receiver.run_id}:{receiver.episode_id}:0') is None
    assert h.family.project_credit(receiver, selection(receiver,
        first['record_refs']+second['record_refs']))['credit'] == 4
    assert h.family.facts(receiver, {})['execution_completed'] is True
    original_sources = h.family.facts(receiver, {})['execution_result_refs']
    assert set(original_sources) == set(first['record_refs']+second['record_refs'])
    for reference in original_sources:
        assert h.family.resolve(receiver, reference, 'execution_result')
    monkeypatch.setattr(h.family.job_progress_provider.targets, 'observe_target', lambda *a, **k: pytest.fail('replay must not poll'))
    monkeypatch.setattr(h.family.job_progress_provider.targets, 'read_file', lambda *a, **k: pytest.fail('replay must not read'))
    replay = asyncio.run(h.family.execute(receiver, 'execution.results.collect', {},
        f'{receiver.run_id}:{receiver.episode_id}:0'))
    assert replay == first
    rejected = select(h, receiver, 2, 'execution.results.status')
    assert rejected['status'] == 'invalid'
    assert rejected['feedback']['code'] == 'execution_results_assignment_already_completed'
    assert h.family.verify_completion(receiver, proof)
    assert h.family.state(child).receipts() == before


def test_result_selector_rejects_escape_and_altered_window_before_read(host, monkeypatch):
    h = host
    parent, _, outcome, output = launched_local(h)
    reference, = outcome['record_refs']
    escape = {'version': RESULTS_VERSION, 'handoff_ref': reference,
              'selector': {'path': '/etc/passwd', 'offset': 0, 'limit': 1}}
    with pytest.raises(ValueError, match='outside_workspace'):
        h.family.prepare_assignment(parent, 'results', escape, h.scope, 'unexecuted')
    assignment = {'version': RESULTS_VERSION, 'handoff_ref': reference,
                  'selector': {'path': str(output), 'offset': 3, 'limit': 3}}
    receiver = context(h, 'results', assignment, 'bounded-result')
    monkeypatch.setattr(h.family.job_progress_provider.targets, 'observe_target', lambda *a, **k: pytest.fail('invalid selection must not observe'))
    invalid = select(h, receiver, 0, 'execution.results.read', {'path': str(output), 'offset': 2, 'limit': 3})
    assert invalid['status'] == 'invalid'
    assert invalid['feedback']['code'] == 'execution_results_selector_conflict'
    assert not list((h.tmp_path/'run'/'execution-results').glob('**/*.receipt.json'))


def test_preterminal_bytes_stay_partial_and_repeated_final_bytes_add_no_credit(host, monkeypatch):
    h = host
    _, child, original, output = launched_local(h)
    reference, = original['record_refs']
    assignment = {'version': RESULTS_VERSION, 'handoff_ref': reference,
                  'selector': {'path': str(output), 'offset': 0, 'limit': 4}}
    receiver = context(h, 'results', assignment, 'live-file-receiver')
    original_observe = h.family.job_progress_provider.targets.observe_target
    observations = 0

    def observed(target, *, operation_key):
        nonlocal observations
        result = original_observe(target, operation_key=operation_key)
        observations += 1
        if observations == 1:
            # A controlled provider state exercises custody while the writer
            # is live; only this returned observation is changed in the fixture.
            result = {**result, 'state': 'running', 'returncode': None}
        return result

    monkeypatch.setattr(h.family.job_progress_provider.targets, 'observe_target', observed)
    first = select(h, receiver, 0, 'execution.results.collect')
    status = select(h, receiver, 1, 'execution.results.status')
    assert status['result']['observation']['state'] == 'completed'
    assert h.family.completion_for_action(receiver, f'{receiver.run_id}:{receiver.episode_id}:1') is None
    final = select(h, receiver, 2, 'execution.results.collect')
    proof = h.family.completion_for_action(receiver, f'{receiver.run_id}:{receiver.episode_id}:2')
    assert proof is not None and h.family.verify_completion(receiver, proof)
    assert h.family.project_credit(receiver, selection(receiver,
        first['record_refs']+status['record_refs']+final['record_refs']))['credit'] == 2
    assert h.family.state(child).receipts() == [original['result']]


def test_overwritten_path_is_current_filesystem_acquisition_without_attempt_output_claim(host):
    h = host
    _, child, original, output = launched_local(h)
    handoff_ref, = original['record_refs']
    original_receipts = deepcopy(h.family.state(child).receipts())
    original_execution = original['result']['outcome']['facts']['requested_job']['execution_id']
    assert output.read_bytes() == bytes(range(10))
    output.write_bytes(b'NEW!')
    assignment = {'version': RESULTS_VERSION, 'handoff_ref': handoff_ref,
                  'selector': {'path': str(output), 'offset': 0, 'limit': 4}}
    receiver = context(h, 'results', assignment, 'overwritten-path-receiver')
    acquired = select(h, receiver, 0, 'execution.results.collect')
    body = acquired['result']
    assert body['target']['execution_id'] == original_execution
    assert body['observation']['state'] == 'completed' and body['observation']['returncode'] == 0
    assert base64.b64decode(body['windows'][0]['bytes_base64']) == b'NEW!'
    assert body['acquisition_origin'] == NATIVE_RESULT_ORIGIN
    assert body['acquisition_origin']['attempt_output_version'] == 'unverified'
    facts = h.family.facts(receiver, {})
    assert facts['execution_result_origin'] == NATIVE_RESULT_ORIGIN
    assert facts['execution_completed'] is True
    schema = {'type': 'object', 'properties': {'origin': h.family.fact_sources('results')[
        'execution_result_origin']['report_schema']}, 'required': ['origin'], 'additionalProperties': False}
    h.family.validate_report(receiver, {'origin': NATIVE_RESULT_ORIGIN}, schema)
    with pytest.raises(ValueError):
        h.family.validate_report(receiver, {'origin': {**NATIVE_RESULT_ORIGIN,
            'attempt_output_version': 'verified'}}, schema)
    proof = h.family.completion_for_action(receiver, f'{receiver.run_id}:{receiver.episode_id}:0')
    assert h.family.verify_completion(receiver, proof)
    assert proof['endpoint'] == 'usable_handoff'
    assert 'attempt_output_version_unverified' in proof['validation_keys']
    assert h.family.state(child).receipts() == original_receipts


def test_pending_handle_resolution_uses_scoped_durable_service_before_store_lookup(host, monkeypatch):
    h = host
    parent = context(h, 'launch', launch_assignment({'here': native_assignment(h.workspace)}), 'yielding-parent')
    handle = 'execution_fixture_live_child'

    class ScopedHandles:
        def reference_in_context(self, context, reference, namespace):
            return (context.run_id == parent.run_id and plain(context.scope) == h.scope
                and reference == handle and namespace in {'execution_handle', 'execution'})

    h.family.services = ScopedHandles()
    monkeypatch.setattr(h.store, 'get', lambda *a, **k: pytest.fail('durable handles are not Store records'))
    assert h.family.resolve(parent, handle, 'execution_handle')
    assert h.family.resolve(parent, handle, 'execution')
    assert not h.family.resolve(parent, 'execution_unknown', 'execution_handle')
    assert not h.family.resolve(replace(parent, scope={'subject_refs': ['outside-target']}), handle, 'execution_handle')
    assert not h.family.resolve(replace(parent, run_id='outside-run'), handle, 'execution')
