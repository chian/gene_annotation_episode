"""The plain file results of a real local job, acquired through the real runner on the built job service.

Each run is linked with the public API and stepped with ``EpisodeRun.next_decision`` and ``run_unit``: the
Episode's own ``decide`` is shown, each unit is the ``ToolCall`` the Episode's own ``action`` builds from the answer
a model gives, and the status request, the fetch and the window reads run as real tool units (journaled attempts,
custody receipts, ``credit`` and the controller's step) on a real detached local job. The model is not asked here;
the run with the real model is ``test_branch_execution_result_acquisition_model_run.py``."""
import asyncio
import hashlib
import importlib
import json

import pytest

from episode_runtime import ModelRequest, Rejected, resume
from yield_control import AccumulationYieldController, BoundedQualityYieldController

from .plain_world import (ExecutionResultAcquisition, JOB_LEDGER, PACKAGE, PATH, RESULT_TEXT, collaborators,
                          entry_input, finishing_job, launch_job, linked, waiting_job, world)

goal_file = importlib.import_module(PACKAGE + '.goal')
task_file = importlib.import_module(PACKAGE + '.task')
final_file = importlib.import_module(PACKAGE + '.messages.final_to_parent')
SIZE = len(RESULT_TEXT)
STATUS, COLLECT, READ = 'execution_results_status', 'execution_results_collect', 'execution_results_read'


def _summary(run):
    return ExecutionResultAcquisition.internal_summary(run.view)


def _credit(run):
    return ExecutionResultAcquisition.credit(_summary(run), run.view.records)


def _selected(run, tool, **operands):
    """The unit the Episode's own ``action`` builds from the answer a model gives for ``tool``."""
    answer = {'selection': {'kind': 'tool', 'tool': tool, 'arguments': operands}}
    return task_file.action(answer, _summary(run), run.view.records, None)


def _unit(run, tool, **operands):
    return asyncio.run(run.run_unit(_selected(run, tool, **operands)))['outcome']


def _offered(request):
    """The operations the answer schema of a request admits."""
    return [option['properties']['tool']['enum'][0]
            for option in request.output_schema['properties']['selection']['anyOf']]


def _journal_path(run_id):
    return ((PATH.replace('/', '__'), run_id),)


def _until_stopped(run):
    """Status requests until the Episode's yield controller stops it; how many were run."""
    count = 0
    while not run.view.controller_state.as_record()['decision']['stop']:
        _unit(run, STATUS)
        count += 1
    return count


def test_the_first_decision_states_the_purpose_the_job_the_operations_and_the_credit(tmp_path):
    w = world(tmp_path)
    launch_run, handoff_ref = launch_job(w, finishing_job(), wait_for_end=True)
    entry = entry_input(w, launch_run, handoff_ref)
    _, run = linked(w, 'plain-first', entry)
    request = asyncio.run(run.next_decision())
    print('REQUEST', PATH, json.dumps({'instructions': request.instructions, 'context': request.context,
                                       'output_schema': request.output_schema}, sort_keys=True))
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    assert isinstance(ExecutionResultAcquisition.yield_controller(0.0, w['settings'], run.view.parent_input),
                      AccumulationYieldController)
    # The purpose first, then what a result acquisition is and earns, then the operations offered now.
    assert request.instructions.startswith(goal_file.GOAL + task_file.RESULT_INSTRUCTIONS)
    assert request.instructions.endswith(task_file.ANSWER_INSTRUCTION)
    assert _offered(request) == [STATUS, COLLECT]
    for entry_ in (task_file.STATUS, task_file.COLLECT):
        assert '\n- ' + entry_['name'] + ': ' + entry_['description'] in request.instructions
    assert READ + ':' not in request.instructions                         # no file is fetched yet
    for stale in ('knowledge.', 'launch.instructions', 'exec_command', 'ssh', 'iterator', 'physical attempt',
                  'stopping budget', 'provider tools'):
        assert stale not in request.instructions
    # The context: the job of the held handoff row, what was requested, nothing acquired yet, the credit.
    assert set(request.context) == {'feedback', 'job', 'complete', 'credit', 'requested', 'first_window_bytes',
                                    'acquisitions'}
    job = request.context['job']
    row = run.view.records.table(JOB_LEDGER).get(handoff_ref)
    assert (job['job'], job['resource_id'], job['kind']) == (row['job'], 'local_test', 'local')
    assert job['handoff_ref'] == handoff_ref and job['last_observed_state'] == 'not_observed'
    assert job['results_fetched'] is False
    assert request.context['requested'] == [{'path': w['result_path'], 'offset': 0, 'limit': None,
                                             'fetched_file_bytes': None}]
    assert request.context['acquisitions'] == [] and request.context['complete'] is False
    assert request.context['credit'] == {'credit_unit': 1.0, 'current_credit': 0.0, 'credit_of_each_unit': []}
    assert request.context['first_window_bytes'] == 4096
    assert run.view.records.receipt(handoff_ref)['how'] == 'entry'
    # An answer that names an operation not offered now, or no operation, is rejected: no unit.
    with pytest.raises(Rejected):
        _selected(run, READ, path=w['result_path'], offset=0, limit=4)
    with pytest.raises(Rejected):
        task_file.action({'selection': {'kind': 'tool', 'tool': 'exec_command', 'arguments': {'cmd': 'ls'}}},
                         _summary(run), run.view.records, None)
    w['store'].close()


def test_the_status_the_fetch_and_the_windows_of_a_finished_job(tmp_path):
    w = world(tmp_path, log_window_bytes=8)
    launch_run, handoff_ref = launch_job(w, finishing_job(), wait_for_end=True)
    entry = entry_input(w, launch_run, handoff_ref)
    registry, run = linked(w, 'plain-finished', entry)
    asyncio.run(run.next_decision())

    # The status request: the job service's check row is the record; no bytes, no credit.
    status = _unit(run, STATUS)
    records = run.view.records
    assert status['status'] == 'completed' and status['state'] == 'finished'
    assert status['result_available'] is True
    check = records.table(JOB_LEDGER).get(status['check_ref'])
    assert check['event'] == 'check' and records.receipt(check['id'])['how'] == 'produced'
    summary = _summary(run)
    assert summary['job']['last_observed_state'] == 'finished' and summary['job']['closed'] is False
    assert summary['acquisitions'] == [{'tool': STATUS, 'status': 'completed', 'state': 'finished',
                                        'result_available': True}]
    assert _credit(run) == 0.0

    # The fetch: the requested file is an artifact this Episode holds, the job is closed, and the first window
    # (8 bytes here) is retained as a result record read back through custody.
    collected = _unit(run, COLLECT)
    assert collected['status'] == 'completed', collected
    summary = _summary(run)
    file = summary['fetched_files'][w['result_path']]
    assert file['bytes'] == SIZE and records.get_artifact(file['ref']) == RESULT_TEXT.encode()
    assert records.receipt(file['ref'])['how'] == 'produced'
    closure = records.table(JOB_LEDGER).get(summary['job']['closure_ref'])
    assert closure['event'] == 'closure' and closure['detail']['outcome'] == 'results_acquired'
    assert [item['name'] for item in closure['detail']['results']] == ['result.txt']
    source = records.get(collected['result_ref'])
    assert source['provider'] == 'episode.execution_result' and source['artifact_ref'] == collected['artifact_ref']
    body = json.loads(records.get_artifact(collected['artifact_ref']))
    assert body['windows'] == [{'path': w['result_path'], 'artifact_ref': file['ref'], 'offset': 0,
                                'returned_bytes': 8, 'size_bytes': SIZE,
                                'sha256': hashlib.sha256(RESULT_TEXT.encode()[:8]).hexdigest()}]
    assert body['assignment'] == summary['assignment'] and body['closure_ref'] == closure['id']
    assert _credit(run) == 8 / SIZE and summary['completed'] is False

    # The next decision offers a further window of the fetched file and no second fetch.
    request = asyncio.run(run.next_decision())
    assert _offered(request) == [STATUS, READ]
    read_option = request.output_schema['properties']['selection']['anyOf'][1]
    assert read_option['properties']['arguments']['properties']['path']['enum'] == [w['result_path']]
    assert request.context['requested'][0]['fetched_file_bytes'] == SIZE
    assert request.context['job']['results_fetched'] is True
    assert request.context['job']['last_observed_state'] == 'finished'
    assert request.context['credit']['credit_of_each_unit'] == [0.0, 8 / SIZE]
    assert request.context['acquisitions'][1]['windows'] == [{'path': w['result_path'], 'offset': 0,
                                                              'returned_bytes': 8, 'size_bytes': SIZE}]
    with pytest.raises(Rejected):                                          # the job is closed: no second fetch
        _selected(run, COLLECT)
    with pytest.raises(Rejected):                                          # a path that was not fetched
        _selected(run, READ, path=w['result_path'] + '.other', offset=0, limit=4)

    # A further window earns its newly covered bytes; a window of bytes already retained earns nothing.
    read = _unit(run, READ, path=w['result_path'], offset=4, limit=12)
    assert read['status'] == 'completed' and _credit(run) == 16 / SIZE
    again = _unit(run, READ, path=w['result_path'], offset=0, limit=16)
    assert again['status'] == 'completed' and _credit(run) == 16 / SIZE
    rest = _unit(run, READ, path=w['result_path'], offset=16, limit=1024)
    assert rest['status'] == 'completed' and _credit(run) == 1.0
    summary = _summary(run)
    assert summary['completed'] is True and summary['initial'] == []
    assert [len(result['windows']) for result in summary['own']] == [1, 1, 1, 1]

    # Nothing is left to acquire: status requests earn nothing and the yield controller stops the Episode.
    checks = _until_stopped(run)
    closed = asyncio.run(run.run())
    assert closed['record'].ended_by == 'yield_stop' and closed['record'].units_consumed == 5 + checks
    returned = closed['result'].as_record()
    assert final_file.RETURN_FORM.select(entry['selection']).admit(returned, 'return') == returned
    finding = returned['finding']
    assert final_file.FINDING_FORM.admit(finding, 'finding') == finding
    assert returned['credit'] == 1.0 and returned['execution_completed'] is True
    assert finding == {'execution_completed': True, 'acquisitions': 5 + checks, 'failure_count': 0,
                       'job_state': 'finished', 'results_not_available': 0, 'windows_acquired': 4,
                       'bytes_acquired': 8 + 12 + 16 + (SIZE - 16)}
    assert returned['execution_handoff_refs'] == [handoff_ref]
    rows = [records.table(JOB_LEDGER).get(ref) for ref in returned['execution_job_record_refs']]
    assert [row['event'] for row in rows] == ['check', 'closure']       # the latest check and the closure
    # The retained results: each result record; selected with them, its information artifact and the fetched file.
    assert len(returned['execution_result_refs']) == 4
    assert all(records.get(ref)['provider'] == 'episode.execution_result' for ref in returned['execution_result_refs'])
    assert len(returned['execution_result_artifact_refs']) == 4 + 1
    assert file['ref'] in returned['execution_result_artifact_refs']
    assert all(records.holds(ref) for ref in returned['execution_result_artifact_refs'])
    json.dumps(returned, allow_nan=False)

    # Resume replays the recorded units: the same result, no unit run again.
    units = len(w['journal'].units('plain-finished', _journal_path('plain-finished')))
    again = asyncio.run(resume(registry, run_id='plain-finished', journal=w['journal'],
                               collaborators=collaborators(w)).run())
    assert again['result'].as_record() == returned
    assert len(w['journal'].units('plain-finished', _journal_path('plain-finished'))) == units
    w['store'].close()


def test_a_job_that_has_not_ended_refuses_the_fetch_and_the_refusal_is_an_outcome(tmp_path):
    w = world(tmp_path)
    release = tmp_path / 'release'
    launch_run, handoff_ref = launch_job(w, waiting_job(release), wait_for_end=False)
    try:
        entry = entry_input(w, launch_run, handoff_ref)
        registry, run = linked(w, 'plain-unfinished', entry)
        asyncio.run(run.next_decision())
        refused = _unit(run, COLLECT)
        assert refused['status'] == 'failed' and refused['failure']['code'] == 'results_not_available'
        summary = _summary(run)
        assert summary['acquisitions'] == [{'tool': COLLECT, 'status': 'failed',
                                            'failure_code': 'results_not_available'}]
        assert summary['job']['closed'] is False and summary['fetched_files'] == {} and summary['own'] == []
        assert _credit(run) == 0.0
        status = _unit(run, STATUS)
        assert status['state'] == 'running' and status['result_available'] is False
        request = asyncio.run(run.next_decision())
        assert _offered(request) == [STATUS, COLLECT]
        assert request.context['job']['last_observed_state'] == 'running'
        assert request.context['acquisitions'][0]['failure_code'] == 'results_not_available'
        # Units that earn nothing: the yield controller stops the Episode and the return says what was refused.
        checks = _until_stopped(run)
        closed = asyncio.run(run.run())
        assert closed['record'].ended_by == 'yield_stop'
        returned = closed['result'].as_record()
        assert final_file.RETURN_FORM.select(entry['selection']).admit(returned, 'return') == returned
        assert returned['credit'] == 0.0 and returned['execution_completed'] is False
        assert returned['finding'] == {
            'execution_completed': False, 'acquisitions': 1 + checks, 'failure_count': 1, 'job_state': 'running',
            'results_not_available': 1, 'windows_acquired': 0, 'bytes_acquired': 0}
        assert returned['execution_result_refs'] == [] and returned['execution_result_artifact_refs'] == []
        assert returned['execution_handoff_refs'] == [handoff_ref]
        latest, = returned['execution_job_record_refs']                    # the latest check: the job is open
        assert run.view.records.table(JOB_LEDGER).get(latest)['detail']['state'] == 'running'
        again = asyncio.run(resume(registry, run_id='plain-unfinished', journal=w['journal'],
                                   collaborators=collaborators(w)).run())
        assert again['result'].as_record() == returned
    finally:
        release.touch()
    w['store'].close()


def test_a_finite_selector_is_bounded_and_a_window_outside_it_is_an_invalid_outcome(tmp_path):
    w = world(tmp_path, log_window_bytes=4)
    launch_run, handoff_ref = launch_job(w, finishing_job(), wait_for_end=True)
    entry = entry_input(w, launch_run, handoff_ref,
                        selector=lambda path: {'path': path, 'offset': 5, 'limit': 10})
    _, run = linked(w, 'plain-finite', entry)
    asyncio.run(run.next_decision())
    controller = ExecutionResultAcquisition.yield_controller(0.0, w['settings'], run.view.parent_input)
    assert isinstance(controller, BoundedQualityYieldController) and controller.maximum_credit == 1.0
    collected = _unit(run, COLLECT)
    assert collected['status'] == 'completed'
    summary = _summary(run)
    assert summary['requested'] == {w['result_path']: [5, 10]}
    assert summary['own'][0]['windows'][0]['offset'] == 5 and _credit(run) == 4 / 10
    outside = _unit(run, READ, path=w['result_path'], offset=0, limit=8)
    assert outside['status'] == 'invalid' and outside['feedback']['code'] == 'execution_results_selector_conflict'
    summary = _summary(run)
    assert summary['acquisitions'][1] == {'tool': READ, 'status': 'invalid',
                                          'window': {'path': w['result_path'], 'offset': 0, 'limit': 8},
                                          'failure_code': 'execution_results_selector_conflict'}
    assert _credit(run) == 4 / 10
    inside = _unit(run, READ, path=w['result_path'], offset=9, limit=6)
    assert inside['status'] == 'completed'
    closed = asyncio.run(run.run())
    returned = closed['result'].as_record()
    assert closed['record'].ended_by == 'yield_stop' and returned['credit'] == 1.0
    assert returned['finding']['execution_completed'] is True and returned['finding']['failure_count'] == 1
    assert returned['finding']['bytes_acquired'] == 10
    w['store'].close()


def test_bytes_an_earlier_acquisition_retained_earn_nothing_in_a_later_one(tmp_path):
    w = world(tmp_path, log_window_bytes=8)
    launch_run, handoff_ref = launch_job(w, finishing_job(), wait_for_end=True)
    entry = entry_input(w, launch_run, handoff_ref)
    _, first = linked(w, 'plain-earlier', entry)
    asyncio.run(first.next_decision())
    earlier = _unit(first, COLLECT)
    file_ref = _summary(first)['fetched_files'][w['result_path']]['ref']
    assert _credit(first) == 8 / SIZE

    # A later commission of the same assignment passes the earlier result, its artifact and the fetched file.
    later = entry_input(w, launch_run, handoff_ref)
    later['assignment'].update(initial_result_refs=[earlier['result_ref']],
                               initial_result_artifact_refs=[earlier['artifact_ref'], file_ref])
    _, run = linked(w, 'plain-later', later)
    asyncio.run(run.next_decision())
    summary = _summary(run)
    assert [result['ref'] for result in summary['initial']] == [earlier['result_ref']]
    assert summary['own'] == [] and summary['job']['closed'] is False and _credit(run) == 0.0
    assert run.view.records.receipt(earlier['result_ref'])['how'] == 'entry'
    again = _unit(run, COLLECT)                                            # the same first 8 bytes: nothing new
    assert again['status'] == 'completed' and _credit(run) == 0.0
    assert _summary(run)['completed'] is False
    rest = _unit(run, READ, path=w['result_path'], offset=8, limit=1024)
    assert rest['status'] == 'completed' and _credit(run) == (SIZE - 8) / SIZE
    summary = _summary(run)
    assert summary['completed'] is True                                    # the earlier and the own windows cover
    assert summary['execution_progress']['execution_result_refs'] == [again['result_ref'], rest['result_ref']]

    # A passed result of another selector of the job is not an earlier result of this assignment.
    other = entry_input(w, launch_run, handoff_ref, selector=lambda path: {'path': path, 'offset': 0, 'limit': 4})
    other['assignment'].update(initial_result_refs=[earlier['result_ref']],
                               initial_result_artifact_refs=[earlier['artifact_ref'], file_ref])
    _, third = linked(w, 'plain-other-selector', other)
    asyncio.run(third.next_decision())
    assert _summary(third)['initial'] == []
    w['store'].close()
