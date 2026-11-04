"""Practical receipts retain ownership, factual qualification and signed progress."""
from copy import deepcopy
import json

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.practical_execution_records import (
    ASSIGNMENT_SCHEMA, COMPLETION_PROOF_SCHEMA, RECEIPT_SCHEMA,
    assess_validations, canonical, digest, validate_assignment)
from gene_annotation_episode.practical_execution_state import PracticalState


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


def test_baseline_is_initial_credit_and_cannot_be_replaced_on_reopen(tmp_path):
    value = assignment(tmp_path)
    baseline = {'facts': {'paths': [path_fact(value['workspace'] + '/env', kind='directory')]}}
    validations = assess_validations(value, baseline, value['initial_context'], checked_at=TIME)
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value,
        initial_validations=validations, initial_outcome=baseline)
    assert state.credit_view()['credit'] == state.credit_view()['initial_credit'] == 2
    assert state.receipts() == []
    assert state.completion_proof() is None
    reopened = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    assert reopened.credit_view() == state.credit_view()
    with pytest.raises(ValueError, match='baseline_already_frozen'):
        PracticalState(tmp_path / 'state', 'run', 'episode', value, initial_validations=[])
    with pytest.raises(ValueError, match='identity_conflict'):
        PracticalState(tmp_path / 'state', 'run', 'another-episode', value)


def test_baseline_cannot_inherit_requested_job_completion(tmp_path):
    value = assignment(tmp_path)
    outcome = outcome_for(value)
    validations = assess_validations(value, outcome, value['initial_context'],
        tool_name='practical.job.collect', checked_at=TIME)
    with pytest.raises(ValueError, match='baseline_cannot_complete'):
        PracticalState(tmp_path / 'state', 'run', 'episode', value,
            initial_validations=validations, initial_outcome=outcome)


def test_interruption_retains_uncertain_intent_without_resubmitting(tmp_path):
    value = assignment(tmp_path)
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    first = state.begin('op-1', 'practical.job.start', {'queue': 'debug'})
    assert first['state'] == 'new' and first['receipt'] is None
    reopened = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    pending = reopened.begin('op-1', 'practical.job.start', {'queue': 'debug'})
    assert pending['state'] == 'pending' and pending['intent'] == first['intent']
    with pytest.raises(ValueError, match='operation_identity_conflict'):
        reopened.begin('op-1', 'practical.job.start', {'queue': 'production'})
    with pytest.raises(ValueError, match='requires_reconciliation'):
        reopened.begin('op-2', 'practical.job.start', {})
    assert reopened.receipts() == []


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


def test_context_is_explicit_durable_and_revision_checked(tmp_path):
    value = assignment(tmp_path)
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    after = {'revision': 1, 'cwd': value['workspace'] + '/analysis', 'environment': {'THREADS': '2'}}
    finish(state, 'cd', 'practical.context', {'status': 'completed', 'facts': {}}, context_after=after)
    assert PracticalState(tmp_path / 'state', 'run', 'episode', value).context() == after
    # A shell's own exported variables have no persistent-context effect.
    finish(state, 'shell', 'practical.command', {'facts': {'command': {
        'argv': ['/bin/sh', '-c', 'export THREADS=8'], 'environment': {'THREADS': '2'},
        'returncode': 0, 'execution_id': 'command-2'}}})
    assert state.context() == after
    state.begin('bad-revision', 'practical.context', {})
    bad = {**after, 'cwd': value['workspace'], 'revision': 1}
    with pytest.raises(ValueError, match='revision_conflict'):
        state.finish('bad-revision', {'facts': {}}, [], context_after=bad)
    with pytest.raises(ValueError, match='outside_workspace'):
        state.finish('bad-revision', {'facts': {}}, [],
            context_after={**after, 'cwd': '/home/chian', 'revision': 2})


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


def test_unrelated_actions_do_not_erase_or_recredit_prior_command_progress(tmp_path):
    value = assignment(tmp_path)
    value['progress_requirements'].append({'key': 'dependency-check', 'credit': 3,
        'predicate': {'kind': 'command_exit', 'argv': ['bio', '--version'], 'returncode': 0}})
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    command = {'facts': {'command': {'argv': ['bio', '--version'], 'environment': {},
        'returncode': 0, 'execution_id': 'dependency-check'}}}
    finish(state, 'check', 'practical.command', command)
    assert state.credit_view()['credit'] == 3
    unrelated = finish(state, 'inspect', 'practical.inspect', {'facts': {}})
    assert unrelated['validations'] == []
    assert state.credit_view()['credit'] == 3
    command['facts']['command']['execution_id'] = 'later-check'
    finish(state, 'check-again', 'practical.command', command)
    assert state.credit_view()['credit'] == 3
    command['facts']['command']['returncode'] = 1
    finish(state, 'check-failed', 'practical.command', command)
    assert state.credit_view()['credit'] == 0


def test_unrelated_action_preserves_handoff_progress_when_other_endpoint_keys_pending(tmp_path):
    value = assignment(tmp_path, endpoint='usable_handoff')
    value['completion_keys'].append('needed-environment')
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    finish(state, 'start', 'practical.job.start', outcome_for(value, completed=False))
    assert state.credit_view()['credit'] == 5
    assert state.completion_proof() is None
    finish(state, 'inspect', 'practical.inspect', {'facts': {}})
    assert state.credit_view()['credit'] == 5
    assert state.completion_proof() is None


def test_cannot_drop_an_actual_negative_assessment_to_preserve_credit(tmp_path):
    value = assignment(tmp_path)
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    good = {'facts': {'paths': [path_fact(value['workspace'] + '/env', kind='directory')]}}
    finish(state, 'prepare', 'practical.inspect', good)
    assert state.credit_view()['credit'] == 2
    state.begin('missing', 'practical.inspect', {})
    bad = {'facts': {'paths': [path_fact(value['workspace'] + '/env', exists=False)]}}
    with pytest.raises(ValueError, match='assessment_missing'):
        state.finish('missing', bad, [])
    assert state.credit_view()['credit'] == 2


def test_model_flags_and_matching_generic_command_cannot_complete_job(tmp_path):
    value = assignment(tmp_path)
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    outcome = outcome_for(value)
    outcome['completed'] = True
    receipt = finish(state, 'generic-command', 'practical.command', outcome)
    assert not any(item['satisfied'] for item in receipt['validations'])
    assert state.completion_proof() is None


@pytest.mark.parametrize('mutation', ['wrong_argv', 'wrong_environment', 'wrong_digest',
    'wrong_kind', 'failed', 'nonzero', 'missing_output', 'unlisted_output'])
def test_endpoint_requires_actual_requested_work_and_outputs(tmp_path, mutation):
    value = assignment(tmp_path)
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    outcome = outcome_for(value)
    job = outcome['facts']['requested_job']
    if mutation == 'wrong_argv':
        job['argv'] = ['other-software']
    elif mutation == 'wrong_environment':
        job['environment'] = {'THREADS': '8'}
    elif mutation == 'wrong_digest':
        job['requested_job_sha256'] = '0' * 64
    elif mutation == 'wrong_kind':
        job['resource_kind'] = 'hpc'
    elif mutation == 'failed':
        job['status'] = 'failed'
    elif mutation == 'nonzero':
        job['returncode'] = 1
    elif mutation == 'missing_output':
        outcome['facts']['paths'][0] = path_fact(value['workspace'] + '/results.json', exists=False)
    else:
        job['output_paths'] = []
    finish(state, 'collect', 'practical.job.collect', outcome)
    assert state.completion_proof() is None


def test_exact_completion_proof_is_recovered_and_tampering_or_later_action_invalidates(tmp_path):
    value = assignment(tmp_path)
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    receipt = finish(state, 'collect', 'practical.job.collect', outcome_for(value))
    proof = state.completion_proof()
    Draft202012Validator(COMPLETION_PROOF_SCHEMA).validate(proof)
    assert proof['receipt_sha256'] == digest(receipt)
    assert state.verify_completion(proof) is True
    assert PracticalState(tmp_path / 'state', 'run', 'episode', value).verify_completion(proof) is True
    assert state.verify_completion({**proof, 'receipt_sha256': '0' * 64}) is False
    assert state.verify_completion({**proof, 'unit_ref': 'runtime-only'}) is False
    assert state.verify_completion({**proof, 'operation_key': 'not-collected'}) is False
    assert state.begin('collect', 'practical.job.collect', {})['state'] == 'completed'
    with pytest.raises(ValueError, match='already_completed'):
        state.begin('later', 'practical.inspect', {})
    assert state.verify_completion(proof) is True


def test_launch_handoff_is_different_from_physical_job_completion(tmp_path):
    value = assignment(tmp_path, endpoint='usable_handoff')
    state = PracticalState(tmp_path / 'handoff-state', 'run', 'episode', value)
    finish(state, 'start', 'practical.job.start', outcome_for(value, completed=False, output_exists=False))
    assert state.completion_proof()['endpoint'] == 'usable_handoff'
    completed = assignment(tmp_path)
    other = PracticalState(tmp_path / 'output-state', 'run', 'episode', completed)
    finish(other, 'start', 'practical.job.start', outcome_for(completed, completed=False, output_exists=False))
    assert other.completion_proof() is None


def test_false_validation_is_rejected_before_receipt_publication(tmp_path):
    value = assignment(tmp_path)
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    state.begin('inspect', 'practical.inspect', {})
    outcome = {'facts': {'paths': [path_fact(value['workspace'] + '/env', exists=False)]}}
    validations = assess_validations(value, outcome, state.context(), checked_at=TIME)
    validations[0]['satisfied'] = True
    with pytest.raises(ValueError, match='does_not_match_actual_facts'):
        state.finish('inspect', outcome, validations)
    assert state.receipts() == []
    assert state.begin('inspect', 'practical.inspect', {})['state'] == 'pending'


def test_receipt_integrity_is_checked_before_projection_or_completion(tmp_path):
    value = assignment(tmp_path)
    state = PracticalState(tmp_path / 'state', 'run', 'episode', value)
    finish(state, 'collect', 'practical.job.collect', outcome_for(value))
    path = next((tmp_path / 'state' / 'receipts').glob('*.json'))
    corrupted = json.loads(path.read_text())
    corrupted['outcome']['facts']['requested_job']['returncode'] = 99
    path.write_text(canonical(corrupted) + '\n')
    with pytest.raises(ValueError, match='receipt_identity_conflict'):
        state.credit_view()


def test_assignment_requires_closed_predicates_unique_keys_and_job_endpoint(tmp_path):
    value = assignment(tmp_path)
    Draft202012Validator(ASSIGNMENT_SCHEMA).validate(value)
    assert validate_assignment(value) == value
    bad = deepcopy(value)
    bad['completion_keys'] = ['needed-environment']
    with pytest.raises(ValueError, match='requires_requested_job_endpoint'):
        validate_assignment(bad)
    for credit in (-1, float('nan'), True):
        bad = deepcopy(value)
        bad['progress_requirements'][0]['credit'] = credit
        with pytest.raises(ValueError):
            validate_assignment(bad)
    bad = deepcopy(value)
    bad['progress_requirements'][1]['key'] = 'needed-environment'
    with pytest.raises(ValueError):
        validate_assignment(bad)
    bad = deepcopy(value)
    bad['progress_requirements'][0]['predicate']['invented'] = 'model says ready'
    with pytest.raises(ValueError, match='invalid_practical_predicate'):
        validate_assignment(bad)
