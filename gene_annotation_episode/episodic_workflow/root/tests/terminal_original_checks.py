"""Practical receipts retain ownership, factual qualification and signed progress."""
from copy import deepcopy
import json

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.episodic_workflow.root.practical_execution_records import (
    ASSIGNMENT_SCHEMA, COMPLETION_PROOF_SCHEMA, RECEIPT_SCHEMA,
    assess_validations, canonical, digest, validate_assignment)
from terminal_original_persistence import PracticalState


TIME = '2026-10-22T20:00:00+00:00'


def assignment(tmp_path, *, endpoint='completed_job_outputs'):
    workspace = str(tmp_path / 'work')
    output = workspace + '/results.json'
    terminal = ({'kind': 'requested_job_handoff'} if endpoint == 'usable_handoff'
        else {'kind': 'requested_job_outputs', 'output_paths': [output]})
    return {'version': 'practical_assignment_v1', 'assignment_id': 'assigned-analysis',
        'resource_kind': 'local', 'workspace': workspace, 'endpoint': endpoint,
        'requested_job': {'argv': ['/opt/bio/python', 'analysis.py'], 'environment': {'THREADS': '1'}},
        'progress_requirements': [
            {'key': 'needed-environment', 'credit': 2,
                'predicate': {'kind': 'path_exists', 'path': workspace + '/env', 'object_type': 'directory'}},
            {'key': 'requested-result', 'credit': 5, 'predicate': terminal}],
        'completion_keys': ['requested-result'],
        'initial_context': {'revision': 0, 'cwd': workspace, 'environment': {'THREADS': '1'}},
        'inventory_snapshot': {'remote_status': 'unavailable', 'catalog': None},
        'constraints': {'charging_account': 'EpiCalib'}}


def path_fact(path, *, exists=True, kind='file', sha256=None):
    return {'path': path, 'exists': exists, 'object_type': kind if exists else 'missing', 'sha256': sha256}


def outcome_for(value, *, completed=True, exitcode=0, output_exists=True):
    job = {'requested_job_sha256': digest(value['requested_job']),
        **deepcopy(value['requested_job']), 'resource_kind': value['resource_kind'],
        'execution_id': 'physical-job-actual-1', 'status': 'completed' if completed else 'running',
        'returncode': exitcode if completed else None,
        'output_paths': [value['workspace'] + '/results.json'],
        'handoff': {'execution_id': 'physical-job-actual-1',
            'monitor_operation': 'practical.job.status', 'results_operation': 'practical.job.collect'}}
    return {'status': 'completed', 'facts': {'requested_job': job,
        'paths': [path_fact(value['workspace'] + '/results.json', exists=output_exists)]},
        'evidence_refs': ['actual-operation-receipt']}


def finish(state, key, tool, outcome, *, context_after=None, arguments=None):
    state.begin(key, tool, arguments or {})
    context = context_after or state.context()
    validations = assess_validations(state.assignment, outcome, context, checked_at=TIME, tool_name=tool)
    return state.finish(key, outcome, validations, context_after=context_after)


def test_receipt_replay_keeps_original_bytes_times_and_context(tmp_path):
    value = assignment(tmp_path)
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    outcome = {'status': 'completed', 'facts': {}}
    receipt = finish(state, 'op-1', 'practical.inspect', outcome)
    path = next((tmp_path / 'state' / 'receipts').glob('*.json'))
    before = path.read_bytes()
    assert state.begin('op-1', 'practical.inspect', {}) == {
        'state': 'completed', 'intent': state.begin('op-1', 'practical.inspect', {})['intent'],
        'receipt': receipt}
    assert state.finish('op-1', outcome, receipt['validations']) == receipt
    assert path.read_bytes() == before
    assert len(state.receipts()) == 1
    assert state.credit_view()['credit'] == 0
    with pytest.raises(ValueError, match='receipt_conflict'):
        state.finish('op-1', {'status': 'completed', 'facts': {}, 'different': True}, receipt['validations'])
    Draft202012Validator(RECEIPT_SCHEMA).validate(receipt)


def test_progress_deduplicates_and_losses_remain_signed(tmp_path):
    value = assignment(tmp_path)
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    environment = value['workspace'] + '/env'
    gains, previous = [], 0
    for index, exists in enumerate((True, True, False, False, True)):
        outcome = {'facts': {'paths': [path_fact(environment, exists=exists, kind='directory')]}}
        finish(state, f'op-{index}', 'practical.inspect', outcome)
        credit = state.credit_view()['credit']
        gains.append(credit - previous)
        previous = credit
    assert gains == [2, 0, -2, 0, 2]
    assert len(state.receipts()) == 5
    assert state.completion_proof() is None


def test_executed_unsuccessful_command_has_receipt_and_assessed_diagnostic(tmp_path):
    value = assignment(tmp_path)
    value['progress_requirements'].append({'key': 'diagnosed-cli', 'credit': 1,
        'predicate': {'kind': 'command_exit', 'argv': ['tool', '--check'], 'returncode': 2}})
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    receipt = finish(state, 'diagnose', 'practical.command', {'status': 'completed',
        'native_outcome': 'failed', 'facts': {'command': {'argv': ['tool', '--check'],
        'environment': {}, 'returncode': 2, 'execution_id': 'physical-command'}}})
    assert receipt['outcome']['native_outcome'] == 'failed'
    assert state.credit_view()['credit'] == 1
    assert state.completion_proof() is None



from real_time_credit_fixture import progress_time
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import UnitRef

def completion_context(*, run_id="run-practical", episode_id="episode-practical",
                       unit_index=0, action_index=7):
    unit = UnitRef(episode_id, unit_index).as_record()
    proof = {"version": "practical_completion_v1", "run_id": run_id,
        "episode_id": episode_id, "assignment_sha256": "a" * 64,
        "endpoint": "completed_job_outputs", "operation_key": "recorded-operation",
        "receipt_sha256": "b" * 64, "validation_keys": ["requested_outputs"]}
    return {"version": "completed_action_estimation_context_v5",
        "progress_time": progress_time(10. * (unit_index + 1), run_id=run_id,
            episode_id=episode_id, decision_index=action_index),
        "current_completion_evidence": {"version": "completed_action_evidence_v1",
            "run_id": run_id, "episode_id": episode_id, "unit_ref": unit,
            "original_decision_index": action_index, "action_kind": "tool",
            "received_record_refs": [], "received_progress_refs": [],
            "progress_records": [], "child_return": None, "unavailable_reasons": []},
        "practical_completion": {**proof, "unit_ref": unit, "action_index": action_index}}


