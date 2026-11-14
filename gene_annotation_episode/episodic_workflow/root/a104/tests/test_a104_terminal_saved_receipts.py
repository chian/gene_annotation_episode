"""Controlled terminal custody connections, distinct from real producer tests."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a104.tests.a104_controlled_terminal_receipts import HOMES, construct, module
from gene_annotation_episode.episodic_workflow.root.a104.tests.retained_fluorescence_fixture import unpack as fluorescence_cases
from gene_annotation_episode.episodic_workflow.root.a104.tests.retained_protein_fixture import unpack as protein_case


@pytest.fixture(scope='module')
def descriptors(tmp_path_factory):
    fluorescence = fluorescence_cases(tmp_path_factory.mktemp('terminal-fluorescence-descriptors'))
    protein = protein_case(tmp_path_factory.mktemp('terminal-protein-descriptors'))
    yield {'fluorescence': fluorescence[0], 'protein': protein}
    for case in (*fluorescence, protein):
        case.verify_unchanged()


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('family', ('fluorescence', 'protein'))
@pytest.mark.parametrize('returncode', (0, 1))
def test_controlled_saved_terminal_handoff_native_and_observation_reopen(tmp_path, descriptors, home, family, returncode):
    terminal = module('terminal_scientific_evidence')
    Store = module('state').Store
    with Store(tmp_path / 'store') as store:
        case = construct(tmp_path / 'case', store, descriptors[family], family, home, returncode=returncode)
        intent = {'target': case.target, 'scope': case.scope}
        handoff = terminal.read_terminal_handoff(store, case.run_id, case.target, case.scope)
        assert handoff['start_receipt'] == case.receipt
        terminal.validate_terminal_handoff(handoff, intent, store, case.run_id)
        observation = terminal.terminal_observation(case.target, case.proof)
        assert observation['state'] == ('completed' if returncode == 0 else 'failed')
        assert terminal.validate_terminal_observation(observation, intent, store, case.run_id) == observation
        host = (case.result_binding.native_fluorescence_results if family == 'fluorescence'
            else case.result_binding.native_protein_structure_results)
        native = terminal.terminal_native_snapshot(host.receipts, SimpleNamespace(intent=intent), observation)
        assert native['original_plan'] == case.plan
        assert native['driver_started'] is (None if returncode == 0 else False)
        terminal.validate_terminal_native(native, intent, observation, store, case.run_id)
        # Original scientific command bytes are not re-executed or fetched to
        # reopen a saved handoff. The already captured plan artifact remains.
        Path(case.proof['plan_snapshot']['captured_path']).unlink()
        original_scope = deepcopy(case.scope)
        with pytest.raises(ValueError):
            terminal.read_terminal_handoff(store, case.run_id, case.target, {'subject_refs': []})
        changed = deepcopy(native)
        changed['plan_file']['sha256'] = '0' * 64
        with pytest.raises(ValueError):
            terminal.validate_terminal_native(changed, intent, observation, store, case.run_id)
        assert case.scope == original_scope
        baseline = (deepcopy(handoff), deepcopy(native), deepcopy(observation))
    with Store(tmp_path / 'store') as reopened:
        assert terminal.read_terminal_handoff(reopened, case.run_id, case.target, case.scope) == baseline[0]
        terminal.validate_terminal_native(baseline[1], intent, baseline[2], reopened, case.run_id)
        assert terminal.validate_terminal_observation(baseline[2], intent, reopened, case.run_id) == baseline[2]
        # A different commissioned role cannot borrow the original local result.
        journal = module('episode_journal').Journal(reopened, case.run_id)
        row = reopened.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? '
            'AND decision_index=0', (case.run_id, case.parent.episode_id)).fetchone()
        selection = json.loads(row['action'])
        selection['role'] = 'launch_hpc'
        journal.save('runtime_actions', {'episode_id': case.parent.episode_id, 'decision_index': 0,
            'action': module('execution_contracts').canonical(selection), 'result': None, 'credit': None})
        with pytest.raises(ValueError):
            terminal.read_terminal_handoff(reopened, case.run_id, case.target, case.scope)


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('family', ('fluorescence', 'protein'))
@pytest.mark.parametrize('status', ('failed', 'unavailable'))
def test_current_policy_native_failure_keeps_real_practical_receipt_and_replay(
        tmp_path, descriptors, monkeypatch, home, family, status):
    Store = module('state').Store
    current = module('library.native_terminal_transport')
    acquisition = module('acquisition')
    calls = []
    async def controlled(operation, state, tool_name, arguments, operation_key):
        assert operation.configuration['policy'] == {'memory_bytes': 5 * 1024**3, 'scratch_bytes': 4 * 1024**3}
        calls.append((tool_name, deepcopy(arguments), operation_key))
        if status == 'unavailable':
            raise acquisition.AcquisitionError('controlled_native_unavailable', phase='controlled_operation',
                operational={'policy': deepcopy(operation.configuration['policy'])})
        return {'facts': {}, 'native_outcome': {'failure': {'code': 'controlled_native_failed'}}}, []
    monkeypatch.setattr(current.TerminalExecution, 'execute', controlled)
    with Store(tmp_path / 'store') as store:
        case = construct(tmp_path / 'case', store, descriptors[family], family, home,
            returncode=1, publish_saved=False)
        arguments = {'cmd': ['/controlled-native-unavailable'], 'workdir': case.context.assignment['workspace'], 'env': {}}
        selected = {'kind': 'tool', 'tool': 'exec_command', 'arguments': arguments}
        key = f'{case.run_id}:{case.context.episode_id}:0'
        canonical = module('execution_contracts').canonical
        case.journal.save('runtime_actions', {'episode_id': case.context.episode_id, 'decision_index': 0,
            'action': canonical(selected), 'result': None, 'credit': None})
        returned = asyncio.run(case.launch_binding.execute(case.context, 'exec_command', arguments, key))
        assert returned['status'] == 'completed'  # Original action returned a failure receipt.
        receipt = returned['result']
        assert receipt['outcome']['facts'] == {}
        assert receipt['outcome']['native_outcome']['failure']['code'] == (
            'execution_action_failed' if status == 'unavailable' else 'controlled_native_failed')
        state = case.launch_binding.state(case.context)
        assert state.credit_view()['credit'] == 0 and state.completion_proof() is None
        case.journal.save('runtime_actions', {'episode_id': case.context.episode_id, 'decision_index': 0,
            'action': canonical(selected), 'result': canonical(returned), 'credit': 0})
        assert asyncio.run(case.launch_binding.execute(case.context, 'exec_command', arguments, key)) == returned
        assert len(calls) == 1
        information = module('practical_receipt_information').PracticalReceiptInformation(store, case.run_id)
        reference, = returned['record_refs']
        assert information.read(reference, case.scope)['receipt'] == receipt
