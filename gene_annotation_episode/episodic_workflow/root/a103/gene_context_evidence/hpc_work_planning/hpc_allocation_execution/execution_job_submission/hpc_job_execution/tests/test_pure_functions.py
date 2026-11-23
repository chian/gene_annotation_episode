"""The pure functions of the binding, called on real inputs: the real ``EpisodeView`` of the loop, the real library
assessment of a command's facts, the real controller and the real return form. No service and no job is touched."""
import importlib

import pytest
from yield_control import CompletionYieldController

from method_loop import EpisodeGoal, EpisodeRef, EpisodeRequest, EpisodeView, Grain
from method_loop.episode import ClosedRecord

from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import (
    assess_validations, digest)

PACKAGE = __name__.rsplit('.tests.', 1)[0]
WORKSPACE = '/work/run'
PATH = (('episode', 'hpc_job_execution'),)
JOB = {'argv': ['qsub', 'job.sh'], 'environment': {}}


class Message(ClosedRecord):
    def as_record(self):
        return {}


def module(name):
    return importlib.import_module(PACKAGE + '.' + name)


def assignment():
    return {'version': 'practical_assignment', 'assignment_id': 'a1', 'resource_kind': 'hpc',
            'workspace': WORKSPACE, 'endpoint': 'usable_handoff', 'requested_job': JOB,
            'progress_requirements': [
                {'key': 'in_workspace', 'credit': 1.0, 'predicate': {'kind': 'context_cwd', 'path': WORKSPACE}},
                {'key': 'handoff', 'credit': 3.0, 'predicate': {'kind': 'requested_job_handoff'}}],
            'completion_keys': ['handoff'],
            'initial_context': {'revision': 0, 'cwd': WORKSPACE, 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {}, 'resource_id': 'aurora'}


def view(outcomes=()):
    parent_input = module('messages.read_from_parent').read_from_parent(assignment(), None)
    goal = EpisodeGoal('execute the job', 'a handoff')
    return EpisodeView(grain=Grain('g', 'u', 'r', lambda *args: None), key='k', path=PATH,
                       units_consumed=len(outcomes), updates=(), controller_state=None,
                       episode_ref=EpisodeRef('run', PATH),
                       request=EpisodeRequest(goal, Message()), parent_input=parent_input, outcomes=tuple(outcomes),
                       records=None)


def handed_off_unit():
    job = {'argv': JOB['argv'], 'environment': {}, 'returncode': 0, 'execution_id': 'e1',
           'requested_job_sha256': digest(JOB), 'resource_kind': 'hpc', 'status': 'submitted', 'output_paths': [],
           'handoff': {'execution_id': 'e1', 'monitor_operation': 'm', 'results_operation': 'r'}}
    outcome = {'facts': {'requested_job': job}}
    context = {'revision': 1, 'cwd': WORKSPACE, 'environment': {}}
    receipt = {'operation_key': 'op1', 'context_after': context, 'outcome': outcome,
               'validations': assess_validations(assignment(), outcome, context,
                                                 checked_at='2026-11-19T00:00:00+00:00', tool_name='practical.job.start')}
    return {'arguments': {'command': 'qsub job.sh'},
            'outcome': {'status': 'completed', 'result': receipt, 'record_refs': ['ref1'], 'operation_ref': 'opref'}}


def test_the_read_from_parent_is_the_only_assignment_reader():
    parent_input = module('messages.read_from_parent').read_from_parent(assignment(), None)
    assert parent_input['assignment']['resource_kind'] == 'hpc' and parent_input['input_refs'] == []


def test_the_summary_of_a_fresh_episode_credits_what_the_initial_context_already_satisfies():
    summary = module('messages.internal_summary').internal_summary(view())
    assert summary['credit'] == 1.0 and summary['completion'] is None and summary['receipts'] == []
    assert module('credit').credit(summary, None) == 1.0


def test_a_command_that_observes_the_handoff_completes_the_endpoint_and_earns_its_credit():
    summary = module('messages.internal_summary').internal_summary(view([handed_off_unit()]))
    assert module('credit').credit(summary, None) == 4.0
    assert summary['handoff_refs'] == ['ref1'] and summary['completion']['operation_key'] == 'op1'
    result = module('messages.final_to_parent').final_to_parent(
        summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 4.0}, ['practical_receipt_digests'])
    assert result['credit'] == 4.0 and result['execution_completed'] is True
    assert result['execution_handoff_refs'] == ['ref1'] and result['finding']['handed_off'] is True
    assert result['practical_receipt_digests'] == [digest(summary['receipts'][0])]


def test_a_rejected_command_leaves_credit_unchanged_and_the_result_says_not_completed():
    unit = {'arguments': {'command': 'false'},
            'outcome': {'status': 'rejected', 'feedback': 'no'}}
    summary = module('messages.internal_summary').internal_summary(view([unit]))
    assert summary['credit'] == 1.0 and summary['actions'][0]['status'] == 'rejected'
    result = module('messages.final_to_parent').final_to_parent(
        summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}, [])
    assert result['execution_completed'] is False and result['execution_handoff_refs'] == []


def test_every_selectable_fact_is_returned_and_the_form_admits_the_result():
    module_ = module('messages.final_to_parent')
    summary = module('messages.internal_summary').internal_summary(view([handed_off_unit()]))
    selection = [name for name, spec in module_.RETURN_FORM.fields.items() if not spec.required]
    result = module_.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 4.0},
                                     selection)
    assert result['execution_result_origin'] == {'retained': False}
    assert module_.RETURN_FORM.admit(result, 'return') == result


def test_the_controller_is_the_completion_controller_over_the_completion_keys_target():
    parent_input = module('messages.read_from_parent').read_from_parent(assignment(), None)
    settings = {'task_yield_profiles': {'launch_hpc:practical_hpc_handoff': {
        'cutoff': 0.5, 'parameters': {'uncertainty_alpha': 0.05}}}}
    controller = module('yield_estimator').yield_controller(1.0, settings, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 3.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        module('yield_estimator').yield_controller(1.0, {'task_yield_profiles': {}}, parent_input)
