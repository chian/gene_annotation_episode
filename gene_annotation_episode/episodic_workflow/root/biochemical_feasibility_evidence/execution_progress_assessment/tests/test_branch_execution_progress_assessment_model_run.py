"""The A110 monitor with the real model on a REAL local job (``-m model_run``).

A real detached local job is started through the Stage 1b ``job_access`` local route (``job_probe`` launches it, as
``episode_support/jobs/tests/test_job_services.py`` does); the job's handoff row, a record, is passed to the monitor
in custody (``handoff_refs`` of the entry assignment: the row exists in the Store). (1a) the job is still running
when the monitor starts; (1b) the job has already finished; (1c) the monitor is handed a second job as a direct
dependency and commissions a monitor of its own kind for it. The monitor runs with the real ``ModelProvider``, the
real ``job_services`` and its own settings. Nothing is scripted or faked."""
import asyncio

import pytest

from episode_runtime import BindingRegistry, ChildCall, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.jobs.tests.job_probe.episode import JobProbe
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import ToolKnowledge
from gene_annotation_episode.episodic_workflow.episode_support.jobs.tests.test_job_services import (
    LIBRARY, LOCAL, capability, launch_step, step, earlier, python_job)

from ..episode import ExecutionProgressAssessment
from ..messages import final_to_parent, read_from_parent

PATH = ExecutionProgressAssessment.binding_path
GRAIN = PATH.replace('/', '__')          # the name of the binding's Episodes in a journal path
SETTINGS = {'job_probe': {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}},
            PATH: {'cost': 0.2, 'parameters': {'uncertainty_alpha': 0.05}}}
SELECTABLE = tuple(name for name, field in final_to_parent.RETURN_FORM.fields.items() if not field.required)


class Switch:
    fail = False


def configuration(tmp_path, pbs=None):
    launch = LaunchInstructions.freeze(tmp_path / 'frozen_launch', source=LIBRARY / 'instructions' / 'launch')
    knowledge = ToolKnowledge.freeze(tmp_path / 'frozen_knowledge', source=LIBRARY / 'knowledge')
    return {
        'local': {LOCAL: {'workspace': str(tmp_path / 'jobs'),
                          'policy': {'memory_bytes': 256 * 1024 ** 2, 'scratch_bytes': 64 * 1024 ** 2},
                          'cpu_threads': 1}},
        'pbs': pbs or {}, 'capabilities': [capability(LOCAL, 'local')],
        'event_ledger_directory': str(tmp_path / 'events'),
        'estimate_table_path': str(tmp_path / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(launch.directory),
        'tool_knowledge_directory': str(knowledge.directory)}


def held_world(tmp_path, pbs=None):
    settings = configuration(tmp_path, pbs)
    switch = Switch()
    return {'store': Store(tmp_path / 'store'), 'configuration': settings, 'tmp': tmp_path,
            'services': {**job_services(settings), 'switch': lambda: switch},
            'journal': RunJournal(tmp_path / 'journal.sqlite3'),
            'provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)}


def collaborators(held, settings=SETTINGS):
    return {'store': held['store'], 'model_provider': held['provider'], 'continuation': settings,
            'services': held['services']}


def path_of(run_id):
    return ((GRAIN, run_id),)


def launched(held, run_id, plan):
    """Run a ``job_probe`` plan; the outcomes of its units and its result."""
    entry = {'assignment': {'input_refs': [], 'job_refs': []}, 'message': {'plan': plan}, 'selection': []}
    result = asyncio.run(link(BindingRegistry([JobProbe()]), 'job_probe', entry, run_id=run_id,
                              journal=held['journal'], collaborators=collaborators(held)).run())['result'].as_record()
    return [unit[2]['outcome'] for unit in held['journal'].units(run_id, (('job_probe', run_id),))], result


def started_job(held, finished, name=None):
    """Start a real local job through job_access; its handle, the reference of its handoff row and the launch
    run's result. ``finished``: the job is released and waited for until it has ended. The job prints a line every
    0.2 seconds until the file ``release`` exists."""
    release = held['tmp'] / 'release'
    job = python_job("import pathlib,time\n"
                     "n=0\n"
                     "while not pathlib.Path(" + repr(str(release)) + ").exists():\n"
                     "    n+=1; print('step', n, flush=True); time.sleep(0.2)\n"
                     "pathlib.Path('answer.txt').write_text('done')\nprint('finished', flush=True)")
    plan = [launch_step(job)]
    if finished:
        release.touch()
        plan += [step('wait', handoff_ref=earlier(0, 'handoff_ref'))]
    units, result = launched(held, 'launch-' + (name or ('finished' if finished else 'running')), plan)
    return units[0]['job'], units[0]['handoff_ref'], result


def monitor(held, handoff_ref, run_id, *, known=(), dependencies=(), settings=SETTINGS, fields=None):
    """Link the monitor on the job of ``handoff_ref``: the handoff row is passed as a record."""
    assignment = {'version': 'monitor_assignment', 'handoff_refs': [handoff_ref],
                  'known_progress_refs': list(known), 'dependency_handoff_refs': list(dependencies),
                  'requested_fields': list(read_from_parent.FIELD_OPTIONS if fields is None else fields),
                  'information_unit': 1.0}
    entry = {'assignment': assignment, 'message': {}, 'selection': list(SELECTABLE)}
    return link(BindingRegistry([ExecutionProgressAssessment()]), PATH, entry, run_id=run_id,
                journal=held['journal'], collaborators=collaborators(held, settings))


def report(held, run_id, result):
    units = [unit[2] for unit in held['journal'].units(run_id, path_of(run_id))]
    calls = held['journal'].model_calls(run_id, path_of(run_id))
    print('ENDED_BY', held['journal'].run_state(run_id)[1].get('ended_by'))
    print('SERVICE BUILDS', [build['name'] for build in held['journal'].service_builds(run_id)])
    print('TOOLS', [(u.get('kind'), u.get('tool'), u.get('arguments'), (u.get('outcome') or {}).get('status'))
                    for u in units])
    print('MODEL ANSWERS', [call['response'] for call in calls])
    print('RESULT', result)
    return units, calls


def check(held, run_id, handoff_ref):
    result = asyncio.run(monitor(held, handoff_ref, run_id).run())['result'].as_record()
    units, calls = report(held, run_id, result)
    assert held['journal'].run_state(run_id)[1]['ended_by'] == 'yield_stop'
    assert any(unit.get('tool') == 'progress_observe' for unit in units)
    assert result['credit'] > 0 and result['finding']['observed'] is True
    # The check went through the job service, with its expectation in the estimate table, and came back in custody.
    assert {'job_access', 'estimate_table'} <= {build['name'] for build in held['journal'].service_builds(run_id)}
    receipts = {item['ref']: item['how'] for item in held['journal'].receipts(run_id, path_of(run_id))}
    assert receipts[handoff_ref] == 'entry' and result['check_refs']
    assert all(receipts[ref] == 'produced' for ref in result['check_refs'])
    assert final_to_parent.RETURN_FORM.select(SELECTABLE).admit(result, 'return') == result
    before = len(calls)
    again = asyncio.run(resume(BindingRegistry([ExecutionProgressAssessment()]), run_id=run_id,
                               journal=held['journal'], collaborators=collaborators(held)).run())
    assert again['result'].as_record() == result
    assert len(held['journal'].model_calls(run_id, path_of(run_id))) == before
    return result


@pytest.mark.model_run
def test_monitor_checks_a_job_still_running(tmp_path):
    held = held_world(tmp_path)
    _, handoff_ref, _ = started_job(held, finished=False)
    try:
        result = check(held, 'monitor-running', handoff_ref)
    finally:
        (tmp_path / 'release').touch()
    assert result['finding']['state'] == 'running' and result['finding']['result_available'] is False
    assert result['job_returncode'] == {'known': False} and result['job_elapsed_seconds']['known'] is True


@pytest.mark.model_run
def test_monitor_checks_a_job_already_finished(tmp_path):
    held = held_world(tmp_path)
    _, handoff_ref, _ = started_job(held, finished=True)
    result = check(held, 'monitor-finished', handoff_ref)
    assert result['finding']['state'] == 'finished' and result['finding']['result_available'] is True
    assert result['job_returncode'] == {'known': True, 'value': 0} and result['job_duration_seconds']['known']


@pytest.mark.model_run
def test_monitor_commissions_a_monitor_of_its_own_kind_for_a_direct_dependency(tmp_path):
    """The commission is named by the test (``run_unit``); the dependency monitor runs by its own decisions, with
    the real model, on the dependency's handoff row passed in custody."""
    held = held_world(tmp_path)
    _, target_ref, _ = started_job(held, finished=True, name='target')
    dependency, dependency_ref, _ = started_job(held, finished=True, name='dependency')
    run_id = 'monitor-dependency'
    linked = monitor(held, target_ref, run_id, dependencies=[dependency_ref])
    outcome = asyncio.run(linked.run_unit(ChildCall('monitor', {'dependency_handle': dependency})))
    print('CHILD MESSAGE', outcome['message'])
    print('CHILD RESULT', outcome['result'], outcome['completion'])
    print('CHILD MODEL ANSWERS', [call['response'] for call in held['journal'].model_calls(
        run_id, (*path_of(run_id), (GRAIN, 'monitor_0')))])
    assert outcome['message']['assignment']['handoff_refs'] == [dependency_ref]
    assert outcome['completion']['ended_by'] == 'yield_stop'
    assert outcome['result']['finding']['observed'] is True and outcome['result']['finding']['state'] == 'finished'
    # The dependency's check rows came back in custody and count as this monitor's received progress.
    receipts = {item['ref']: item['how'] for item in held['journal'].receipts(run_id, path_of(run_id))}
    assert outcome['result']['check_refs'] and all(receipts[ref] == 'returned'
                                                   for ref in outcome['result']['check_refs'])
    summary = ExecutionProgressAssessment.internal_summary(linked.view)
    assert summary['dependencies'][0]['latest_check']['state'] == 'finished'
    assert ExecutionProgressAssessment.credit(summary, linked.view.records) == outcome['result']['credit'] > 0
