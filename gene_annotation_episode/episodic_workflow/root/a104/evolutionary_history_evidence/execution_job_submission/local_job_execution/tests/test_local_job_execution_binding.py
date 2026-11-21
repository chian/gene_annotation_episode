"""The local job execution episode, offline: no model is asked. The class-definition checks, the ten-file set, the
forms, and the episode stepped by the real runner (``next_decision`` and ``run_unit``) on a real Store, RunJournal
and the real job services: the decision request as the model would see it, a launch that starts a real detached
local job and ends the Episode at handoff, resume, a hold, and a launch the resource refuses. The stepped tests
need the workflow launcher (``tools/one_workflow.sh``): a local job runs inside the launcher's slice."""
import ast
import asyncio
import importlib
import json
from pathlib import Path

import pytest

from episode_runtime import BindingRegistry, EpisodeBinding, ModelRequest, RunJournal, ToolCall, link, resume
from episode_runtime.job_access import JOB_LEDGER
from method_loop import FormError

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    violations)

from ..episode import LocalJobExecution
from .launch_world import (HANDOFF_CREDIT, JOB_CODE, PATH, POLICY, REFUSING_POLICY, RESOURCE_ID, collaborators, entry,
                           job_ended, world)

MODULE = ('gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.'
          'execution_job_submission.local_job_execution')
FOLDER = Path(__file__).resolve().parent.parent
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py'}
EPISODE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'
LAUNCH = {'action': {'name': 'launch_job', 'resource_id': RESOURCE_ID}}
RUN = 'a104-local-offline'


def folder_files():
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in relative.parts or relative.parts[0] == 'tests' or path.is_dir():
            continue
        found.add(relative.as_posix())
    return found


def linked_run(held, journal, calls='model_calls'):
    return link(BindingRegistry([LocalJobExecution()]), PATH, entry(held), run_id=RUN, journal=journal,
                collaborators=collaborators(held, calls))


def launch_call(linked):
    """The unit the episode's own ``action`` makes of the answer ``launch_job``."""
    summary = LocalJobExecution.internal_summary(linked.view)
    return LocalJobExecution.action(LAUNCH, summary, linked.view.records, None)


# -- the binding ---------------------------------------------------------------------------------------------------
def test_the_class_passes_the_definition_checks_and_offers_two_defined_actions():
    episode = importlib.import_module(MODULE + '.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    goal = importlib.import_module(MODULE + '.goal')
    assert classes[0].binding_path == goal.BINDING_PATH
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == {}
    assert set(classes[0].tools) == {'launch_job', 'hold_launch'}
    assert tuple(classes[0].services) == ('job_access',)


def test_the_folder_holds_exactly_the_ten_file_set():
    assert folder_files() == FILES


def test_no_module_imports_another_episode_folder():
    own = MODULE
    for relative in sorted(folder_files()):
        tree = ast.parse((FOLDER / relative).read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                if name.startswith(EPISODE_PACKAGE):
                    assert name == own or name.startswith(own + '.'), (relative, name)
            if isinstance(node, ast.ImportFrom) and node.level > 1:
                raise AssertionError((relative, 'relative import above the episode folder'))


def test_the_assignment_form_has_one_field_per_schema_property():
    from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.practical_execution_records import (
        ASSIGNMENT_SCHEMA)
    assert set(ASSIGNMENT_SCHEMA['properties']) == set(LocalJobExecution.assignment_form.fields)


def test_a_remote_resource_assignment_is_not_admitted():
    with pytest.raises(FormError):
        LocalJobExecution.assignment_form.admit({'version': 'practical_assignment_v1', 'resource_kind': 'hpc'},
                                                'assignment')


def test_the_parent_input_is_the_assignment_and_the_credit_its_handoff_requirement_defines(tmp_path):
    held = world(tmp_path)
    requirements = [{'key': 'handoff', 'credit': 4.0, 'predicate': {'kind': 'requested_job_handoff'}},
                    {'key': 'made', 'credit': 9.0, 'predicate': {
                        'kind': 'path_exists', 'path': held['workspace'] + '/answer.txt', 'object_type': 'file'}}]
    assignment = LocalJobExecution.assignment_form.admit(
        {**held['assignment'], 'progress_requirements': requirements}, 'assignment')
    parent = LocalJobExecution.read_from_parent(assignment, {})
    # A launch ends at handoff: only the handoff requirement is its to earn, and its credit is the target.
    assert parent == {'assignment': assignment, 'handoff_credit': 4.0}
    held['store'].close()


def test_the_return_is_controlled_data_only():
    form = LocalJobExecution.return_form
    assert {name: (spec.type, spec.required) for name, spec in form.fields.items()} == {
        'credit': ('number', True), 'finding': ('record', True),
        'execution_handoff_refs': ('record_refs', False), 'execution_completed': ('boolean', False)}
    final = importlib.import_module(MODULE + '.messages.final_to_parent')
    assert {spec.type for spec in final.FINDING_FORM.fields.values()} == {'integer'}


# -- the decision the model is asked for ---------------------------------------------------------------------------
def test_the_first_decision_request_shows_the_assignment_once_the_resource_the_credit_and_the_two_actions(tmp_path):
    held = world(tmp_path)
    linked = linked_run(held, RunJournal(tmp_path / 'journal.sqlite3'))
    request = asyncio.run(linked.next_decision())
    print('REQUEST', json.dumps({'instructions': request.instructions, 'context': request.context,
                                 'output_schema': request.output_schema}, indent=1))
    assert isinstance(request, ModelRequest)
    assert request.context == {
        'assignment': held['assignment'],
        'resource': {'resource_id': RESOURCE_ID, 'kind': 'local', 'workspace': held['workspace'],
                     'policy': request.context['resource']['policy'], 'cpu_threads': 1},
        'actions_so_far': {'launches': [], 'holds': []},
        'credit': {'handoff_earns': HANDOFF_CREDIT, 'earned_by_each_action_so_far': []}}
    assert {name: request.context['resource']['policy'][name] for name in POLICY} == POLICY
    assert json.dumps(request.context).count('a104-local-1') == 1 and json.dumps(request.context).count(
        json.dumps(JOB_CODE)) == 1                                   # the assignment and its job are shown once
    # The answer is one of two defined actions; every field of each takes its value from a fixed set.
    assert violations(request.output_schema) == []
    actions = request.output_schema['properties']['action']['anyOf']
    assert [(one['properties']['name']['enum'], sorted(one['properties'])) for one in actions] == [
        (['launch_job'], ['name', 'resource_id']), (['hold_launch'], ['name', 'reason'])]
    assert actions[0]['properties']['resource_id']['enum'] == [RESOURCE_ID]
    assert actions[1]['properties']['reason']['enum'] == ['constraints_not_met', 'launch_failed']
    assert all('enum' in field for one in actions for field in one['properties'].values())
    for stated in ('assignment.requested_job', 'launch_job', 'hold_launch', 'only thing that earns credit',
                   'You do not write, change or run a command'):
        assert stated in request.instructions
    # Asked again, the decision is the same and nothing was consumed: no model call, no unit.
    assert asyncio.run(linked.next_decision()) == request and linked.view.units_consumed == 0
    assert not list((tmp_path / 'model_calls').glob('call-*'))
    held['store'].close()


def test_the_launch_takes_its_command_from_the_assignment_and_a_hold_carries_only_its_reason(tmp_path):
    held = world(tmp_path)
    linked = linked_run(held, RunJournal(tmp_path / 'journal.sqlite3'))
    asyncio.run(linked.next_decision())
    job = held['assignment']['requested_job']
    assert launch_call(linked) == ToolCall('launch_job', {'resource_id': RESOURCE_ID, 'command': job['argv'],
                                                          'environment': job['environment']})
    summary = LocalJobExecution.internal_summary(linked.view)
    held_back = LocalJobExecution.action({'action': {'name': 'hold_launch', 'reason': 'launch_failed'}}, summary,
                                         linked.view.records, None)
    assert held_back == ToolCall('hold_launch', {'reason': 'launch_failed'})
    held['store'].close()


# -- the launch ----------------------------------------------------------------------------------------------------
def test_a_launch_starts_the_real_job_writes_its_handoff_row_and_ends_the_episode_at_handoff(tmp_path):
    held = world(tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    linked = linked_run(held, journal)
    asyncio.run(linked.next_decision())
    unit = asyncio.run(linked.run_unit(launch_call(linked)))
    outcome = unit['outcome']
    assert outcome['status'] == 'completed' and outcome['kind'] == 'local' and outcome['resource_id'] == RESOURCE_ID
    # The handoff is a job ledger row in the Episode's custody, produced by this unit.
    records = linked.view.records
    row = records.table(JOB_LEDGER).get(outcome['handoff_ref'])
    assert (row['event'], row['job'], row['detail']['kind']) == ('handoff', outcome['job'], 'local')
    assert records.receipt(outcome['handoff_ref'])['how'] == 'produced'
    assert set(unit['produced']) == {outcome['handoff_ref'], outcome['reply_ref']}
    # The handoff earned the credit the assignment's requirement defines, and the Episode ended there.
    summary = LocalJobExecution.internal_summary(linked.view)
    assert LocalJobExecution.credit(summary, records) == HANDOFF_CREDIT
    assert summary['launches'] == [{'status': 'handed_off', 'job': outcome['job'],
                                    'submitted_at': outcome['submitted_at'], 'handoff_ref': outcome['handoff_ref']}]
    assert linked.view.controller_state.stop and linked.view.units_consumed == 1
    with pytest.raises(RuntimeError, match='episode_stopped_by_its_yield_controller'):
        asyncio.run(linked.next_decision())
    closed = asyncio.run(linked.run())
    result = closed['result'].as_record()
    assert result == {'credit': HANDOFF_CREDIT,
                      'finding': {'launches_handed_off': 1, 'launches_failed': 0, 'holds': 0},
                      'execution_handoff_refs': [outcome['handoff_ref']], 'execution_completed': True}
    assert journal.run_state(RUN)[1]['ended_by'] == 'yield_stop'
    # The job is real and detached: it does its work whether or not the Episode is still there.
    directory = job_ended(held, outcome['job'])
    assert (directory / 'answer.txt').read_text() == '42'
    assert (directory / 'stdout.log').read_text() == 'a104 job done\n'
    # Resume replays the closed run: the same result, no second job, no model call.
    resumed = asyncio.run(resume(BindingRegistry([LocalJobExecution()]), run_id=RUN, journal=journal,
                                 collaborators=collaborators(held, 'model_calls_resumed')).run())
    assert resumed['result'].as_record() == result
    assert [path.name for path in (tmp_path / 'jobs').iterdir()] == [outcome['job']]
    assert not list(tmp_path.glob('model_calls*/call-*'))
    held['store'].close()


def test_a_hold_earns_nothing_and_the_next_decision_shows_it(tmp_path):
    held = world(tmp_path)
    linked = linked_run(held, RunJournal(tmp_path / 'journal.sqlite3'))
    asyncio.run(linked.next_decision())
    unit = asyncio.run(linked.run_unit(ToolCall('hold_launch', {'reason': 'constraints_not_met'})))
    assert unit['outcome'] == {'status': 'held', 'reason': 'constraints_not_met'} and unit['produced'] == []
    summary = LocalJobExecution.internal_summary(linked.view)
    assert LocalJobExecution.credit(summary, linked.view.records) == 0.0
    assert summary['holds'] == ['constraints_not_met'] and summary['credit_by_action'] == [0.0]
    assert not (tmp_path / 'jobs').exists() or not list((tmp_path / 'jobs').iterdir())        # nothing started
    assert LocalJobExecution.final_to_parent(summary, {'credit': 0.0}, ['execution_handoff_refs',
                                                                        'execution_completed']) == {
        'credit': 0.0, 'finding': {'launches_handed_off': 0, 'launches_failed': 0, 'holds': 1},
        'execution_handoff_refs': [], 'execution_completed': False}
    # The Episode goes on (its controller, not the task, would end it): the model is shown the hold and its credit.
    assert not linked.view.controller_state.stop
    request = asyncio.run(linked.next_decision())
    assert request.context['actions_so_far'] == {'launches': [], 'holds': ['constraints_not_met']}
    assert request.context['credit'] == {'handoff_earns': HANDOFF_CREDIT, 'earned_by_each_action_so_far': [0.0]}
    # A launch after the hold earns the handoff and ends the Episode.
    launched = asyncio.run(linked.run_unit(launch_call(linked)))['outcome']
    assert linked.view.controller_state.stop and linked.view.controller_state.current_credit == HANDOFF_CREDIT
    job_ended(held, launched['job'])
    held['store'].close()


def test_a_launch_the_resource_refuses_starts_no_job_earns_nothing_and_is_counted_as_failed(tmp_path):
    held = world(tmp_path, REFUSING_POLICY)
    linked = linked_run(held, RunJournal(tmp_path / 'journal.sqlite3'))
    asyncio.run(linked.next_decision())
    unit = asyncio.run(linked.run_unit(launch_call(linked)))
    outcome = unit['outcome']
    assert outcome['status'] == 'failed' and unit['produced'] == []
    assert linked.view.records.table(JOB_LEDGER).select() == []
    summary = LocalJobExecution.internal_summary(linked.view)
    assert summary['launches'] == [{'status': 'failed', 'job': outcome['job'],
                                    'failure_code': outcome['failure']['code']}]
    assert LocalJobExecution.credit(summary, linked.view.records) == 0.0
    assert LocalJobExecution.final_to_parent(summary, {'credit': 0.0}, [])['finding'] == {
        'launches_handed_off': 0, 'launches_failed': 1, 'holds': 0}
    # The Episode goes on: the model is shown the failed launch and that it earned nothing.
    assert not linked.view.controller_state.stop
    request = asyncio.run(linked.next_decision())
    assert request.context['actions_so_far'] == {'launches': summary['launches'], 'holds': []}
    assert request.context['credit']['earned_by_each_action_so_far'] == [0.0]
    held['store'].close()
