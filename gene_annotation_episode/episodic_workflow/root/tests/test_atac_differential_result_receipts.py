"""Production ATAC host/receipt checks over authored lifecycle controls.

Real Store, Journal, selected-action, practical-source and return validators
are used. Native status/software bytes are explicit engineering fixtures:
these tests do not claim a MACS2 run or a full model-owned Workflow.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.atac_differential_result_receipts import (
    AtacDifferentialResultReceipts, empty_facts, empty_files, outcome,
)
from gene_annotation_episode.atac_differential_returns import AtacDifferentialReturns
from gene_annotation_episode.atac_differential_return_views import (
    PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE,
)
from gene_annotation_episode.native_atac_differential_results import (
    NativeAtacDifferentialResults, ORIGIN, SAVED_ORIGIN,
)
from gene_annotation_episode.native_atac_differential_contracts import POLICY
from gene_annotation_episode.practical_execution_records import assess_validations
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.state import Store
from test_atac_differential_returns import RuntimeFixture, schema_for
from test_atac_differential_operands import make_request, make_assignment


STAMP = '2026-10-27T00:00:00+00:00'


@pytest.fixture
def h(tmp_path):
    with Store(tmp_path / 'store') as store:
        f = RuntimeFixture(store)
        source = SimpleNamespace(store=store, request=make_request(store))
        requested = make_assignment(source)['requested_job']
        workspace = tmp_path / 'workspace'
        workspace.mkdir()
        assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'authored-atac-control',
            'resource_id': 'local-fixture', 'resource_kind': 'local', 'workspace': str(workspace),
            'endpoint': 'usable_handoff', 'requested_job': requested,
            'progress_requirements': [{'key': 'endpoint', 'credit': 1,
                'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['endpoint'],
            'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {'allocation': POLICY}}
        launch = f.child(f.root, schema_for(FAILURE_SOURCE), role='launch', index=0)
        launch_assignment = {'version': 'execution_launch_assignment_v1',
            'requests': {'local-fixture': deepcopy(assignment)}, 'immutable_input_versions': [],
            'constraints': {'allowed_resource_ids': ['local-fixture'], 'allowed_kinds': ['local']}}
        launch_request = plain(launch.request)
        launch_request['message']['episode_assignment'] = launch_assignment
        launch = replace(launch, assignment=launch_assignment, request=launch_request)
        f.persist(launch)
        f.commission(f.root, launch)
        native = f.context((*launch.path, ('launch_local', 'child_0')), assignment,
            __import__('gene_annotation_episode.runtime', fromlist=['TypedReportContract']).TypedReportContract(
                'Return original practical handoff', schema_for(FAILURE_SOURCE), lambda *_: True), launch)
        f.commission(launch, native)
        operation = f'{f.run_id}:{native.episode_id}:0'
        execution_id = str(workspace / '.episode-operations' / digest({'run': f.run_id, 'episode': native.episode_id})
            / digest(operation) / 'native.json')
        job = {'argv': requested['argv'], 'environment': requested['environment'], 'returncode': None,
            'execution_id': execution_id, 'requested_job_sha256': digest(requested), 'resource_kind': 'local',
            'status': 'running', 'output_paths': [], 'handoff': {'execution_id': execution_id,
                'monitor_operation': 'practical.job.status', 'results_operation': 'practical.job.collect'}}
        native_outcome = {'facts': {'requested_job': job}, 'native_outcome': {
            'attempt_operation_key': operation, 'attempt_id': digest(operation)}}
        start = {'version': 'practical_action_receipt_v1', 'run_id': f.run_id,
            'episode_id': native.episode_id, 'assignment_sha256': digest(assignment),
            'operation_key': operation, 'tool_name': 'practical.job.start', 'arguments': {},
            'context_before': assignment['initial_context'], 'context_after': assignment['initial_context'],
            'outcome': native_outcome, 'started_at': STAMP, 'finished_at': STAMP,
            'validations': assess_validations(assignment, native_outcome, assignment['initial_context'],
                checked_at=STAMP, tool_name='practical.job.start')}
        selected = {'kind': 'tool', 'tool': 'practical.job.start', 'arguments': {}}
        f.journal.save('runtime_actions', {'episode_id': native.episode_id, 'decision_index': 0,
            'action': canonical(selected), 'result': canonical({'status': 'completed', 'result': start,
                'record_refs': []}), 'credit': None})
        practical = PracticalReceiptInformation(store, f.run_id)
        handoff = practical.publish(native, start)
        store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
            (canonical({'status': 'completed', 'result': start, 'record_refs': [handoff]}), f.run_id, native.episode_id))
        f.receipts.receive(f.root.episode_id, [handoff], kind='own_action')
        child = f.child(f.root, schema_for(FAILURE_SOURCE), index=1)
        assigned = {**plain(child.assignment), 'handoff_ref': handoff}
        request = plain(child.request)
        request['message']['episode_assignment'] = assigned
        child = replace(child, assignment=assigned, request=request)
        f.persist(child)
        f.commission(f.root, child)
        target = {'version': 'execution_target_v1', 'handle': handoff, 'run_id': f.run_id,
            'resource_id': 'local-fixture', 'resource_kind': 'local', 'execution_id': execution_id,
            'request_sha256': digest(requested), 'origin_episode_id': native.episode_id,
            'assignment': assignment, 'scope': plain(f.scope)}
        resource = {'kind': 'local', 'policy': POLICY}
        calls = []
        observation = {'observed_at': STAMP, 'state': 'running', 'returncode': None,
            'failure_code': None, 'result_available': False, 'measurements': [], 'outputs': [], 'logs': [],
            'provenance_refs': [handoff], 'native': {'execution_id': execution_id,
                'version': 'durable_systemd_native_job_v2', 'state': 'running', 'terminal': False,
                'quiescent': False, 'metadata': {'policy': POLICY}}}
        def observe(target, *, operation_key):
            calls.append(operation_key)
            return deepcopy(observation)
        reader = SimpleNamespace(resources={'local-fixture': resource}, operations={'local-fixture':
            SimpleNamespace(validate_assignment=lambda value: value == assignment)}, observe_target=observe)
        owner = SimpleNamespace(store=store, run_id=f.run_id, directory=tmp_path / 'run',
            resources={'local-fixture': resource}, job_progress_provider=SimpleNamespace(targets=reader),
            acquired_record_unit=3, handoff_unit=1)
        owner._selected_result_action = MethodType(ExecutionEpisodes._selected_result_action, owner)
        owner._selection = lambda context, supplied: supplied
        owner.atac_results = NativeAtacDifferentialResults(owner)
        owner.atac_returns = AtacDifferentialReturns(owner)
        yield SimpleNamespace(f=f, store=store, owner=owner, child=child, launch=launch, native=native, start=start,
            target=target, reader=reader, calls=calls, observation=observation)


def select(h, index=0, name='execution.results.collect'):
    h.f.journal.save('runtime_actions', {'episode_id': h.child.episode_id, 'decision_index': index,
        'action': canonical({'kind': 'tool', 'tool': name, 'arguments': {}}), 'result': None, 'credit': None})
    return f'{h.f.run_id}:{h.child.episode_id}:{index}'


def commit(h, key, value):
    h.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
        (canonical(value), h.f.run_id, h.child.episode_id, int(key.rsplit(':', 1)[1])))


def test_selected_nonterminal_collection_freezes_exact_action_and_replays_without_current_binding(h, monkeypatch):
    results = h.owner.atac_results
    key = select(h)
    value = asyncio.run(results.execute(h.child, h.target, 'execution.results.collect', {}, key))
    commit(h, key, value)
    receipt = value['result']
    assert receipt['delivery_complete'] is False and receipt['capture'] is None
    assert receipt['worker_plan'] is None and receipt['sheet_evidence'] is None
    assert receipt['acquired_population'] is None
    assert receipt['facts'][FAILURE_SOURCE][0]['code'] == 'input_unavailable'
    assert results.facts(h.child)['execution_result_origin'] is None
    assert results.credit_view(h.child, {'initial_known_record_refs': []})['new_acquired_record_count'] == 0
    h.owner.resources.clear()
    h.reader.resources.clear()
    h.reader.operations.clear()
    h.reader.observe_target = lambda *_a, **_k: pytest.fail('Original observation was repeated')
    for row in h.target['assignment']['requested_job']['native_atac_differential']['input_bindings']:
        Path(row['path']).unlink()
    before = list(h.store.db.iterdump())
    assert asyncio.run(results.execute(h.child, h.target, 'execution.results.collect', {}, key)) == value
    assert list(h.store.db.iterdump()) == before and h.calls == [key]
    assert results.completion(h.child) is None


@pytest.mark.parametrize('fault', ['operation', 'arguments', 'tool', 'resource', 'attempt', 'request'])
def test_selected_result_identity_cannot_be_forged(h, fault):
    key = select(h)
    target, arguments, tool = deepcopy(h.target), {}, 'execution.results.collect'
    if fault == 'operation': key += '0'
    elif fault == 'arguments': arguments = {'extra': True}
    elif fault == 'tool': tool = 'execution.results.status'
    elif fault == 'resource': target['resource_id'] = 'unrelated'
    elif fault == 'attempt': target['execution_id'] += '.other'
    else: target['request_sha256'] = '0' * 64
    with pytest.raises(ValueError):
        asyncio.run(h.owner.atac_results.execute(h.child, target, tool, arguments, key))
    assert h.calls == []


@pytest.mark.parametrize('fault', ['start_key', 'start_tool', 'start_outcome', 'source', 'assignment', 'command'])
def test_original_practical_start_and_source_are_both_authoritative(h, fault):
    key = select(h)
    receipts = h.owner.atac_results.receipts
    async def check():
        async with receipts.locked_action(h.child, target=h.target, tool_name='execution.results.collect',
                arguments={}, operation_key=key) as action:
            proof = receipts.read_handoff(action)
            receipts.validate_handoff(proof, action.intent)
            altered = deepcopy(proof)
            if fault == 'start_key': altered['start_receipt']['operation_key'] += '0'
            elif fault == 'start_tool': altered['start_receipt']['tool_name'] = 'practical.job.status'
            elif fault == 'start_outcome': altered['start_receipt']['outcome']['facts']['requested_job']['returncode'] = 7
            elif fault == 'source': altered['source_record']['id'] = 'source_unrelated'
            elif fault == 'assignment': altered['assignment_snapshot']['assignment']['resource_id'] = 'unrelated'
            else: altered['body']['receipt']['outcome']['facts']['requested_job']['argv'] = ['/bin/false']
            with pytest.raises(ValueError): receipts.validate_handoff(altered, action.intent)
    asyncio.run(check())


@pytest.mark.parametrize('edge', ['scientific_launch', 'launch_local'])
def test_native_handoff_requires_each_original_selected_assignment(h, edge):
    key = select(h)
    parent = h.f.root if edge == 'scientific_launch' else h.launch
    row = h.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0',
        (h.f.run_id, parent.episode_id)).fetchone()
    selected = json.loads(row['action'])
    selected['assignment']['constraints'] = {'unselected': True}
    h.store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0',
        (canonical(selected), h.f.run_id, parent.episode_id))
    with pytest.raises(ValueError, match='commission_assignment_conflict'):
        asyncio.run(h.owner.atac_results.execute(h.child, h.target, 'execution.results.collect', {}, key))
    assert h.calls == []


@pytest.mark.parametrize('fault', ['request', 'resource', 'kind', 'constraint'])
def test_original_launch_choice_cannot_be_replaced_by_current_resource_permission(h, fault):
    launch = deepcopy(plain(h.launch.assignment))
    if fault == 'request': launch['requests']['local-fixture']['requested_job']['argv'] = ['/bin/false']
    elif fault == 'resource': launch['constraints']['allowed_resource_ids'] = ['another']
    elif fault == 'kind': launch['constraints']['allowed_kinds'] = ['hpc']
    else: launch['constraints']['allocation'] = {'memory_bytes': 1}
    with pytest.raises(ValueError):
        AtacDifferentialResultReceipts.validate_launch_selection(launch, h.target['assignment'])


def test_original_launch_instruction_pins_allow_explicit_additions_and_forbid_replacement(h):
    launch, selected = deepcopy(plain(h.launch.assignment)), deepcopy(h.target['assignment'])
    inherited = {'version': 'launch_instruction_selection_v1', 'library_id': 'launch_instructions_' + '1' * 64,
        'sections': [{'entry_id': 'software', 'section_id': 'native-mode', 'sha256': '2' * 64}]}
    launch['launch_instructions'] = inherited
    selected['launch_instructions'] = deepcopy(inherited)
    selected['launch_instructions']['sections'].append(
        {'entry_id': 'resource', 'section_id': 'scratch', 'sha256': '3' * 64})
    AtacDifferentialResultReceipts.validate_launch_selection(launch, selected)
    selected['launch_instructions']['sections'][0]['sha256'] = '4' * 64
    with pytest.raises(ValueError, match='launch_instruction_inheritance_conflict'):
        AtacDifferentialResultReceipts.validate_launch_selection(launch, selected)


@pytest.mark.parametrize('mode,qualified,expected', [
    ('native_result', True, ORIGIN), ('saved_sheet_recalculation', True, SAVED_ORIGIN),
    ('native_result', False, None), ('saved_sheet_recalculation', False, None)])
def test_origin_describes_only_the_qualified_retained_delivery(monkeypatch, mode, qualified, expected):
    # Authored publication projection isolates the origin decision; it is not
    # a claim that synthetic dictionaries passed native receipt authority.
    receipt = {'intent': {'assignment': {'selector': {'mode': mode}}}, 'delivery_complete': True,
        'facts': empty_facts(), 'sheet_evidence': {} if qualified else None,
        'projection': {} if qualified else None,
        'qualified_files': dict(empty_files(), **{name: {'artifact_ref': 'authored'} if qualified else None
            for name in ('sheet', 'calculations', 'projection')})}
    host = NativeAtacDifferentialResults(SimpleNamespace(store=None))
    context = SimpleNamespace(request={'report_contract': {'measurements': {'schema': schema_for(FAILURE_SOURCE)}}})
    monkeypatch.setattr(host.receipts, 'completed_receipts', lambda _: [receipt])
    assert host.facts(context)['execution_result_origin'] == expected


@pytest.mark.parametrize('state', ['records', 'header_zero', 'missing', 'unsealed', 'input_only'])
def test_native_acquisition_population_distinguishes_zero_missing_and_input_copies(state):
    artifact = {'artifact_ref': 'artifact_' + 'a' * 64, 'format': 'bedgraph4',
        'producer_outcome': 'succeeded', 'writer_closed': True}
    report = {'group': 'tracks', 'artifact': artifact, 'state': {'availability': 'present',
        'identity': 'verified', 'output_extent': 'complete', 'format': 'compatible'},
        'readable_data_row_count': 1 if state == 'records' else 0, 'data_row_count': 0,
        'reported_numbers': None}
    receipt = {'intent': {'assignment': {'selector': {'mode': 'native_result'}}}, 'native': {},
        'observation': {'native': {'terminal': True, 'quiescent': True}},
        'capture': {'files': [{'retained': {'file': {'artifact_ref': artifact['artifact_ref']}},
            'specification': {'format': artifact['format']}, 'outcome': 'verified'}]}}
    if state == 'missing': report['state']['availability'] = 'missing'
    elif state == 'unsealed': receipt['capture']['files'][0]['outcome'] = 'unsealed'
    elif state == 'input_only': report['group'] = 'bam_references'
    assert AtacDifferentialResultReceipts._has_native_population(receipt, {'parsed_extents': [report]}) == (
        state in ('records', 'header_zero'))


def test_repeated_population_and_saved_recalculation_add_no_acquisition(monkeypatch):
    # The existing operational projection deduplicates a physical population;
    # its unit is caller-owned and does not measure annotation confidence.
    host = NativeAtacDifferentialResults(SimpleNamespace(store=None, acquired_record_unit=3,
        handoff_unit=1, _selection=lambda context, supplied: supplied))
    receipts = host.receipts
    monkeypatch.setattr(receipts, 'completed_receipts', lambda _: [
        {'acquired_population': 'original-attempt'}, {'acquired_population': 'original-attempt'},
        {'acquired_population': None}])
    monkeypatch.setattr(receipts, 'baseline_populations', lambda *_: {'original-attempt'})
    own = host.credit_view(None, {'initial_known_record_refs': []})
    assert own['credit'] == 3 and own['new_acquired_record_count'] == 1
    received = host.credit_view(None, {'initial_known_record_refs': ['actual-received-bundle']})
    assert received['credit'] == 0 and received['new_acquired_record_count'] == 0


@pytest.mark.parametrize('kind', ['native_peak_rows', 'native_differential_rows', 'summary',
    'interval_components', 'derived_regions'])
@pytest.mark.parametrize('case', ['zero', 'unavailable', 'truncated', 'stream_failed', 'window_missing'])
def test_requested_projection_qualification_preserves_zero_and_partial_meanings(kind, case):
    # This isolates delivery qualification after receipt authority; all values
    # are authored controls, not native scientific results.
    projection = {'kind': kind, 'row_extent': 'complete', 'total_rows': 0, 'rows': [],
        'row_window': {'offset': 0, 'limit': 10}, 'failures': []}
    calculations = {'stream_states': [{'track_key': 'signal1', 'exhausted': True}],
        'failures': [], 'tables': [{'role': role, 'extent': 'complete'}
            for role in ('partitions', 'components', 'regions')]}
    if case == 'unavailable': projection['failures'] = [{'code': 'requested_field_unavailable'}]
    elif case == 'truncated': projection['row_extent'] = 'partial'
    elif case == 'stream_failed':
        calculations['stream_states'][0]['exhausted'] = False
        calculations['failures'] = [{'code': 'calculation_stream_failed'}]
    elif case == 'window_missing': projection['total_rows'] = 1
    receipt = {'projection': projection, 'sheet_evidence': {'calculations': calculations},
        'native': {'execution_receipt': {'returncode': 1}}}
    expected = (case == 'zero' or (case == 'stream_failed' and kind.startswith('native_'))
        or (case == 'window_missing' and kind == 'summary'))
    assert AtacDifferentialResultReceipts.requested_projection_complete(receipt) is expected
