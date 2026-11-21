"""The monitor's pieces on real jobs, without a model call: the run's caller steps the entry Episode
(``EpisodeRun.next_decision`` and ``EpisodeRun.run_unit``, the system's public calls).

Each test starts a real detached local job through ``job_access`` (the ``job_probe`` launch of the branch test's
world) and links the monitor on the job's handoff row, passed as a record. ``next_decision`` returns the episode's
own model request (printed by the first test: it is what the model reads); ``run_unit`` runs a tool of the episode
as its next unit with the arguments its ``action`` builds. The Store, the journal, the job services, the estimate
table, the native event ledger and the yield controller are the real ones. Nothing is faked. These tests need the
workflow launcher (``tools/one_workflow.sh``): a local job runs inside the launcher's slice."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import sys
import time

import pytest

from episode_runtime import BindingRegistry, CustodyError, ModelRequest, ToolCall, link, resume
from episode_runtime.estimate_table import EstimateTable
from method_loop import FormError

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import check_expectation
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import outstanding_jobs
from gene_annotation_episode.episodic_workflow.episode_support.jobs.tests.test_job_services import (
    LOCAL, REMOTE, SCHEDULER, launch_step)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    INPUT_CHARACTERS, admitted_by_provider, violations)

from ..episode import ExecutionProgressAssessment as Monitor
from ..goal import GOAL
from ..messages import final_to_parent, read_from_parent
from ..task import CHECK_KIND, selection_schema
from .test_branch_execution_progress_assessment_model_run import (
    PATH, SELECTABLE, SETTINGS, collaborators, held_world, launched, monitor, path_of, started_job)

# At cost zero an accumulating controller never stops: the stepped tests name several units.
STEPPED = {**SETTINGS, PATH: {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}}


@pytest.fixture
def held(tmp_path):
    world = held_world(tmp_path, pbs={REMOTE: {
        'ssh_argv': ['/bin/sh', '-c'], 'python_executable': sys.executable, 'workspace': str(tmp_path / 'remote'),
        'scheduler': SCHEDULER, 'poll_seconds': 0.05}})
    yield world
    (tmp_path / 'release').touch()          # every job of ``started_job`` ends
    world['store'].close()


def stepped(held, handoff_ref, run_id, **options):
    """The linked monitor and its first decision (no model call, no unit)."""
    linked = monitor(held, handoff_ref, run_id, settings=STEPPED, **options)
    return linked, asyncio.run(linked.next_decision())


def summary_of(linked):
    return Monitor.internal_summary(linked.view)


def unit(linked, name, arguments):
    return asyncio.run(linked.run_unit(ToolCall(name, arguments)))['outcome']


def observe(linked, probability=0.5, cost=0.0):
    """The check unit as ``action`` builds it from the model's ``informative_probability``."""
    summary = summary_of(linked)
    return unit(linked, 'progress_observe', {
        'handoff_ref': summary['handoff_ref'], 'known_progress_refs': summary['known_progress_refs'],
        'requested_fields': summary['requested_fields'], 'information_unit': summary['information_unit'],
        'expectation': check_expectation(probability, summary['information_unit'], cost)})


def credit_of(linked):
    return Monitor.credit(summary_of(linked), linked.view.records)


def estimate(held, run_id, position):
    """The estimate-table row of the check that was unit ``position`` of the run."""
    key = held['journal'].attempts(run_id, path_of(run_id))[position][2]
    return EstimateTable(held['configuration']['estimate_table_path']).expectation(key)


def job_file(held, handle, name):
    return held['tmp'] / 'jobs' / handle / name


def wait_for(path):
    while not path.exists() or not path.stat().st_size:      # a wait on the job, not on a clock
        time.sleep(0.02)


def options(request):
    return [option['properties'] for option in request.output_schema['properties']['selection']['anyOf']]


def test_the_first_request_states_the_purpose_the_job_and_the_actions_offered_now(held):
    handle, handoff_ref, _ = started_job(held, finished=False)
    linked, request = stepped(held, handoff_ref, 'first')
    print('\nREQUEST ROLE', request.role)
    print('REQUEST INSTRUCTIONS\n' + request.instructions)
    print('REQUEST CONTEXT\n' + json.dumps(request.context, indent=1))
    print('REQUEST SCHEMA\n' + json.dumps(request.output_schema))
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    # The purpose comes first; then exactly the actions offered now, each with what it does; then what earns credit.
    assert request.instructions.startswith(GOAL) and 'You monitor one job.' in GOAL
    offered = [line.split(':')[0][2:] for line in request.instructions.splitlines() if line.startswith('- ')]
    assert offered == ['progress_observe', 'progress_log', 'progress_wait']
    assert 'Credit: you earn one information_unit for each check' in request.instructions
    assert 'exec_command' not in request.instructions and 'ssh' not in request.instructions
    # The context shows the job once, and what the decision needs; no controller internals.
    assert set(request.context) == {'job', 'now', 'checks', 'units', 'credit', 'earlier_checks_of_this_kind'}
    assert request.context['job'] == {
        'handle': handle, 'resource': LOCAL, 'resource_kind': 'local',
        'submitted_at': request.context['job']['submitted_at'],
        'launch_estimates': {'gain': {'value': 2.0, 'lower': 1.0, 'upper': 4.0}, 'done_about': '16:00'}}
    assert request.context['checks'] == [] and request.context['units'] == []
    assert request.context['credit'] == {'current': 0.0, 'information_unit': 1.0, 'cost_of_one_action': 0.0}
    assert request.context['earlier_checks_of_this_kind'] == {
        'resolved': 0, 'open': 0, 'expected_gain': 0.0, 'obtained_gain': 0.0, 'correction': None}
    # The decision form offers the same three actions, each with controlled arguments only.
    tools = options(request)
    assert [item['tool']['enum'] for item in tools] == [['progress_observe'], ['progress_log'], ['progress_wait']]
    assert tools[0]['arguments']['properties'] == {
        'informative_probability': {'type': 'number', 'minimum': 0, 'maximum': 1}}
    assert tools[1]['arguments']['properties']['log'] == {'enum': ['stdout.log', 'stderr.log'], 'type': 'string'}
    # The request is one the model endpoint takes (its rules for a strict output schema, its input limit).
    text, schema = admitted_by_provider(request, held['tmp'] / 'provider')
    assert violations(schema) == [] and len(text) <= INPUT_CHARACTERS
    # Nothing was asked and nothing was consumed; what the decision read of the estimate table is recorded.
    journal, path = held['journal'], path_of('first')
    assert journal.model_calls('first', path) == [] and journal.units('first', path) == []
    assert [read['request'] for read in journal.service_reads('first', path)] == [
        {'service': 'estimate_table', 'member': 'kind_statistics', 'arguments': [CHECK_KIND]}]
    assert journal.receipts('first', path)[0]['ref'] == handoff_ref
    assert journal.receipts('first', path)[0]['how'] == 'entry'


def test_a_check_of_a_running_job_earns_one_unit_and_a_check_that_shows_nothing_new_earns_none(held):
    handle, handoff_ref, _ = started_job(held, finished=False)
    linked, _ = stepped(held, handoff_ref, 'running')
    assert credit_of(linked) == 0.0 and summary_of(linked)['latest'] is None
    first = observe(linked, probability=0.9)
    assert first['status'] == 'completed' and first['state'] == 'running' and first['result_available'] is False
    assert first['informative'] is True and first['replayed'] is False
    reading = first['assessment']
    assert reading['returncode'] is None and reading['duration_seconds'] is None
    assert reading['elapsed_seconds'] > 0
    assert [(item['name'], item['available']) for item in reading['outputs']] == [
        ('stdout.log', True), ('stderr.log', True)]
    assert credit_of(linked) == 1.0 == linked.view.controller_state.current_credit
    # The expectation was recorded under the unit's operation key before the request, and resolved after it.
    row = estimate(held, 'running', 0)
    assert row['kind'] == CHECK_KIND and row['expected'] == {
        'gain': {'value': 0.9, 'lower': 0.0, 'upper': 1.0}, 'cost': 0.0,
        'outcomes': [{'label': 'informative', 'probability': 0.9},
                     {'label': 'nothing_new', 'probability': pytest.approx(0.1)}]}
    assert row['actual'] == {'gain': 1.0, 'cost': 0.0, 'outcome': 'informative', 'state': 'running'}
    assert row['resolved_at'] == first['observed_at']
    # The check row is in custody: produced by the unit, read by the summary through the Episode's records.
    receipts = {item['ref']: item for item in held['journal'].receipts('running', path_of('running'))}
    assert receipts[first['check_ref']]['how'] == 'produced' and receipts[first['check_ref']]['unit'] == 0
    summary = summary_of(linked)
    assert [check['check_ref'] for check in summary['checks']] == [first['check_ref']]
    assert summary['checks'][0]['made_by'] == 'this_monitor' and summary['latest']['state'] == 'running'
    assert summary['received_check_refs'] == [first['check_ref']]
    # A second check of the job, still running: the elapsed time and the log sizes changed, no fact did.
    second = observe(linked, probability=0.2)
    assert second['state'] == 'running' and second['informative'] is False
    assert second['check_ref'] != first['check_ref'] and credit_of(linked) == 1.0
    assert estimate(held, 'running', 1)['actual'] == {'gain': 0.0, 'cost': 0.0, 'outcome': 'nothing_new',
                                                      'state': 'running'}
    # The next decision shows both checks, what each unit earned and how the expectations turned out; a held
    # check can now be read again.
    request = asyncio.run(linked.next_decision())
    assert [check['check_ref'] for check in request.context['checks']] == [first['check_ref'], second['check_ref']]
    assert request.context['units'] == [
        {'action': 'progress_observe', 'status': 'completed', 'check_ref': first['check_ref'],
         'new_information': True, 'credit_earned': 1.0},
        {'action': 'progress_observe', 'status': 'completed', 'check_ref': second['check_ref'],
         'new_information': False, 'credit_earned': 0.0}]
    assert request.context['credit']['current'] == 1.0
    assert request.context['earlier_checks_of_this_kind'] == {
        'resolved': 2, 'open': 0, 'expected_gain': pytest.approx(1.1), 'obtained_gain': 1.0,
        'correction': pytest.approx(1.0 / 1.1)}
    assert '- progress_read:' in request.instructions
    read_option = options(request)[1]
    assert read_option['tool']['enum'] == ['progress_read']
    assert read_option['arguments']['properties']['check_ref']['enum'] == [first['check_ref'], second['check_ref']]
    # Reading a held check again goes through custody, asks nothing of the job and earns nothing.
    read = unit(linked, 'progress_read', {'check_ref': first['check_ref'],
                                          'requested_fields': summary['requested_fields']})
    assert read == {'status': 'completed', **{name: value for name, value in summary['checks'][0].items()
                                              if name != 'made_by'}}
    assert read['state'] == 'running' and read['returncode'] is None and credit_of(linked) == 1.0
    # A window of the job's log comes into custody; its text is shown to the next decision only.
    wait_for(job_file(held, handle, 'stdout.log'))
    window = unit(linked, 'progress_log', {'handoff_ref': handoff_ref, 'log': 'stdout.log', 'offset': 0,
                                           'limit': 6})
    assert window['status'] == 'completed' and window['text'] == 'step 1' and window['bytes'] == 6
    assert held['store'].get_artifact(window['content_ref']) == b'step 1' and credit_of(linked) == 1.0
    request = asyncio.run(linked.next_decision())
    assert request.context['units'][-1] == {'action': 'progress_log', 'status': 'completed', 'log': 'stdout.log',
                                            'offset': 0, 'bytes': 6, 'credit_earned': 0.0, 'text': 'step 1'}
    assert 'text' not in request.context['units'][-2]
    # A wait on a job that does not end returns at its reconsideration time; nothing was received.
    summary = summary_of(linked)
    waited = unit(linked, 'progress_wait', {
        'event_target': summary['job']['event_target'], 'after_cursor': summary['event_cursor'],
        'reconsider_at': (datetime.now(timezone.utc) + timedelta(seconds=0.3)).isoformat()})
    assert waited['status'] == 'completed' and waited['woke_on'] == 'reconsideration'
    assert waited['receipt_refs'] == [] and waited['event_cursor'] == 0 and credit_of(linked) == 1.0
    assert '- progress_wait:' in asyncio.run(linked.next_decision()).instructions
    # Resume replays the five units: nothing runs again and the summary is the same.
    before = summary_of(linked)
    again = resume(BindingRegistry([Monitor()]), run_id='running', journal=held['journal'],
                   collaborators=collaborators(held, STEPPED))
    asyncio.run(again.next_decision())
    assert summary_of(again) == before and len(held['journal'].units('running', path_of('running'))) == 5
    assert [held['journal'].times_begun('running', path_of('running'), index) for index in range(5)] == [1] * 5


def test_the_controller_stops_a_monitor_whose_checks_show_nothing_new_and_the_return_is_controlled(held):
    _, handoff_ref, _ = started_job(held, finished=True)
    linked = monitor(held, handoff_ref, 'finished')            # the settings of the branch test
    asyncio.run(linked.next_decision())
    first = observe(linked, probability=1.0, cost=SETTINGS[PATH]['cost'])
    assert first['state'] == 'finished' and first['result_available'] is True and first['informative'] is True
    assert first['assessment']['returncode'] == 0 and first['assessment']['duration_seconds'] >= 0
    assert first['assessment']['elapsed_seconds'] is None
    checks = [first]
    while not linked.view.controller_state.stop:               # only the yield controller ends the Episode
        checks.append(observe(linked, probability=0.0, cost=SETTINGS[PATH]['cost']))
        assert checks[-1]['informative'] is False
    print('UNITS UNTIL THE CONTROLLER STOPPED', len(checks),
          linked.view.controller_state.as_record()['scores'])
    assert len(checks) > 1
    with pytest.raises(RuntimeError, match='episode_stopped_by_its_yield_controller'):
        observe(linked, probability=0.0, cost=SETTINGS[PATH]['cost'])
    result = asyncio.run(linked.run())['result'].as_record()
    assert held['journal'].run_state('finished')[1]['ended_by'] == 'yield_stop'
    assert result == {
        'credit': 1.0,
        'finding': {'observed': True, 'state': 'finished', 'result_available': True,
                    'observed_at_unix_seconds': datetime.fromisoformat(checks[-1]['observed_at']).timestamp()},
        'check_refs': [item['check_ref'] for item in checks],
        'job_returncode': {'known': True, 'value': 0},
        'job_duration_seconds': {'known': True, 'value': first['assessment']['duration_seconds']},
        'job_elapsed_seconds': {'known': False},
        'stdout_bytes': {'known': True, 'value': first['assessment']['outputs'][0]['bytes']},
        'stderr_bytes': {'known': True, 'value': 0},
        'log_window_refs': [], 'event_receipt_refs': []}
    assert final_to_parent.RETURN_FORM.select(SELECTABLE).admit(result, 'return') == result
    # A commission that selects nothing gets the required fields only; a field the form does not declare fails.
    assert set(final_to_parent.RETURN_FORM.select(()).fields) == {'credit', 'finding', 'check_refs'}
    with pytest.raises(FormError):
        final_to_parent.RETURN_FORM.select(('monitoring_progress_snapshots',))
    # The closed run replays to the same result.
    again = asyncio.run(resume(BindingRegistry([Monitor()]), run_id='finished', journal=held['journal'],
                               collaborators=collaborators(held)).run())
    assert again['result'].as_record() == result


def test_a_wait_wakes_on_the_end_event_of_a_job_that_ended_and_its_receipt_comes_into_custody(held):
    _, handoff_ref, _ = started_job(held, finished=True)
    linked, request = stepped(held, handoff_ref, 'waiting')
    assert '- progress_wait:' in request.instructions
    summary = summary_of(linked)
    waited = unit(linked, 'progress_wait', {
        'event_target': summary['job']['event_target'], 'after_cursor': 0,
        'reconsider_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()})
    assert waited['status'] == 'completed' and waited['woke_on'] == 'state_changed' and waited['event_cursor'] > 0
    assert len(waited['receipt_refs']) == 2 and all(linked.view.records.holds(ref) for ref in waited['receipt_refs'])
    summary = summary_of(linked)
    assert summary['event_receipt_refs'] == waited['receipt_refs'] and summary['event_cursor'] > 0
    # Waiting earned nothing, and the event is not offered again; the check after it is what informs.
    assert credit_of(linked) == 0.0
    request = asyncio.run(linked.next_decision())
    assert '- progress_wait:' not in request.instructions
    assert request.context['units'] == [{'action': 'progress_wait', 'status': 'completed',
                                         'woke_on': 'state_changed', 'credit_earned': 0.0}]
    assert observe(linked)['state'] == 'finished' and credit_of(linked) == 1.0
    assert Monitor.final_to_parent(summary_of(linked), {'credit': 1.0}, ('event_receipt_refs',))[
        'event_receipt_refs'] == waited['receipt_refs']


def test_checks_the_commissioner_passes_are_the_baseline_and_only_what_they_do_not_show_earns_credit(held):
    handle, handoff_ref, _ = started_job(held, finished=False)
    earlier, _ = stepped(held, handoff_ref, 'earlier')
    known = observe(earlier)['check_ref']
    # The next monitor is passed that check row in custody. The job still runs: its check shows nothing new.
    linked, request = stepped(held, handoff_ref, 'later', known=[known])
    assert request.context['checks'][0]['check_ref'] == known
    assert request.context['checks'][0]['made_by'] == 'commissioner' and request.context['credit']['current'] == 0.0
    same = observe(linked)
    assert same['state'] == 'running' and same['informative'] is False and credit_of(linked) == 0.0
    summary = summary_of(linked)
    assert [check['made_by'] for check in summary['checks']] == ['commissioner', 'this_monitor']
    assert summary['received_check_refs'] == [same['check_ref']]             # the baseline is not returned again
    assert Monitor.final_to_parent(summary, {'credit': 0.0}, ())['finding']['state'] == 'running'
    # The job ends: the check after it shows new facts and earns one unit.
    (held['tmp'] / 'release').touch()
    wait_for(job_file(held, handle, 'result.json'))
    ended = observe(linked)
    assert ended['state'] == 'finished' and ended['informative'] is True and credit_of(linked) == 1.0
    # A monitor that is not passed the handoff row cannot be linked on it; one that is not passed the check
    # row cannot read it.
    with pytest.raises(CustodyError):
        stepped(held, 'row_' + '0' * 64, 'no-such-row')
    stranger, _ = stepped(held, handoff_ref, 'stranger')
    with pytest.raises(CustodyError, match='record_not_held'):
        unit(stranger, 'progress_read', {'check_ref': known, 'requested_fields': summary['requested_fields']})


def test_a_request_the_job_service_cannot_answer_is_a_failed_unit_with_no_check_row(held):
    handle, handoff_ref, _ = started_job(held, finished=True)
    linked, _ = stepped(held, handoff_ref, 'lost')
    job_file(held, handle, 'native.json').unlink()          # the resource no longer knows the job
    failed = observe(linked, probability=0.7)
    assert failed['status'] == 'failed' and failed['failure']['code'] == 'local_job_not_found'
    assert credit_of(linked) == 0.0 and summary_of(linked)['checks'] == []
    # The expectation was recorded before the request and stays open: nothing was observed to resolve it.
    row = estimate(held, 'lost', 0)
    assert row['expected']['gain']['value'] == 0.7 and row['actual'] is None
    request = asyncio.run(linked.next_decision())
    assert request.context['units'] == [{'action': 'progress_observe', 'status': 'failed',
                                         'failure_code': 'local_job_not_found', 'credit_earned': 0.0,
                                         'failure_detail': {'job': handle}}]
    assert request.context['earlier_checks_of_this_kind']['open'] == 1
    missing = unit(linked, 'progress_log', {'handoff_ref': handoff_ref, 'log': 'stdout.log', 'offset': 0,
                                            'limit': 10})
    assert missing['status'] == 'completed' and missing['text'] == 'finished\n'        # the log is still there
    assert Monitor.final_to_parent(summary_of(linked), {'credit': 0.0}, SELECTABLE) == {
        'credit': 0.0, 'finding': {'observed': False}, 'check_refs': [],
        'job_returncode': {'known': False}, 'job_duration_seconds': {'known': False},
        'job_elapsed_seconds': {'known': False}, 'stdout_bytes': {'known': False}, 'stderr_bytes': {'known': False},
        'log_window_refs': [missing['window_ref'], missing['content_ref']], 'event_receipt_refs': []}


def test_a_job_on_the_remote_route_is_read_by_its_own_reading_and_offers_no_wait(held):
    units, _ = launched(held, 'launch-remote', [launch_step(
        {'mode': 'login', 'script': 'echo started; exit 3', 'arguments': [], 'env': {}}, resource_id=REMOTE)])
    handle, handoff_ref = units[0]['job'], units[0]['handoff_ref']
    wait_for(held['tmp'] / 'remote' / handle / 'exit_code')
    linked, request = stepped(held, handoff_ref, 'remote')
    assert request.context['job']['resource_kind'] == 'pbs'
    assert '- progress_wait:' not in request.instructions        # the route names no event target
    checked = observe(linked)
    assert checked['state'] == 'failed' and checked['result_available'] is True
    assert checked['assessment'] == {'returncode': 3, 'duration_seconds': None, 'elapsed_seconds': None,
                                     'outputs': []}
    assert credit_of(linked) == 1.0
    window = unit(linked, 'progress_log', {'handoff_ref': handoff_ref, 'log': 'stdout.log', 'offset': 0,
                                           'limit': 100})
    assert window['text'] == 'started\n'
    result = Monitor.final_to_parent(summary_of(linked), {'credit': 1.0}, ('job_returncode', 'stdout_bytes'))
    assert result['finding']['state'] == 'failed' and result['job_returncode'] == {'known': True, 'value': 3}
    assert result['stdout_bytes'] == {'known': False}


def test_only_the_requested_fields_are_kept_shown_and_counted(held):
    _, handoff_ref, _ = started_job(held, finished=False)
    linked, request = stepped(held, handoff_ref, 'narrow', fields=['execution_status'])
    assert '- progress_log:' not in request.instructions          # log windows were not asked for
    first = observe(linked)
    summary = summary_of(linked)
    assert summary['checks'] == [{'check_ref': first['check_ref'], 'observed_at': first['observed_at'],
                                  'state': 'running', 'made_by': 'this_monitor'}]
    assert Monitor.final_to_parent(summary, {'credit': 1.0}, SELECTABLE)['finding'] == {
        'observed': True, 'state': 'running',
        'observed_at_unix_seconds': datetime.fromisoformat(first['observed_at']).timestamp()}
    with pytest.raises(FormError):
        stepped(held, handoff_ref, 'wider', fields=['execution_status', 'private_reasoning'])


def test_a_dependency_the_commissioner_passes_is_offered_and_its_commission_passes_its_handoff_row(held):
    _, target_ref, _ = started_job(held, finished=False, name='target')
    dependency, dependency_ref, _ = started_job(held, finished=False, name='dependency')
    linked, request = stepped(held, target_ref, 'with-dependency', dependencies=[dependency_ref])
    assert '- monitor_dependency:' in request.instructions
    assert request.context['dependencies'] == [{
        'handle': dependency, 'resource_kind': 'local',
        'submitted_at': request.context['dependencies'][0]['submitted_at'], 'latest_check': None}]
    assert options(request)[-1] == {'kind': {'enum': ['monitor_dependency'], 'type': 'string'},
                                    'dependency_handle': {'enum': [dependency], 'type': 'string'}}
    # With a check held, every action is offered; the request is still one the model endpoint takes.
    observe(linked)
    request = asyncio.run(linked.next_decision())
    assert [line.split(':')[0][2:] for line in request.instructions.splitlines() if line.startswith('- ')] == [
        'progress_observe', 'progress_read', 'progress_log', 'progress_wait', 'monitor_dependency']
    assert violations(admitted_by_provider(request, held['tmp'] / 'provider')[1]) == []
    summary = summary_of(linked)
    message = Monitor.msg_to_child('monitor', {'dependency_handle': dependency}, summary)
    assert message.selection == () and message.message == {}
    assert read_from_parent.ASSIGNMENT_FORM.admit(message.assignment, 'assignment') == {
        'version': 'monitor_assignment_v2', 'handoff_refs': [dependency_ref], 'known_progress_refs': [],
        'dependency_handoff_refs': [], 'requested_fields': list(read_from_parent.FIELD_OPTIONS),
        'information_unit': 1.0}
    with pytest.raises(KeyError):                             # a job the commissioner did not pass as a dependency
        Monitor.msg_to_child('monitor', {'dependency_handle': 'job_' + '0' * 32}, summary)
    assert selection_schema(summary)['properties']['selection']['anyOf'][-1]['properties'][
        'dependency_handle'] == {'enum': [dependency]}


def test_the_heads_commission_names_a_held_job_by_its_rows_and_the_monitor_runs_on_that_commission(held):
    """The commissioner (the A107 head) builds the monitor's commission from the outstanding jobs of its summary
    (``job_records.outstanding_jobs`` over the records it holds). Here those are the rows an Episode really holds
    of a real job (its handoff row and one check row); the monitor is then linked on the commission the head's own
    ``msg_to_child`` built and checks the job."""
    from ...messages import msg_to_child as head_to_child
    handle, handoff_ref, _ = started_job(held, finished=False)
    holder, _ = stepped(held, handoff_ref, 'holder')
    known = observe(holder)['check_ref']
    jobs = outstanding_jobs(holder.view.records)
    assert [(job['job'], job['record_refs']) for job in jobs] == [(handle, [handoff_ref, known])]
    assert jobs[0]['latest_check']['state'] == 'running'
    call = {'handoff_ref': handoff_ref, 'requested_fields': list(read_from_parent.FIELD_OPTIONS),
            'return_fields': ['job_returncode']}
    head = {'outstanding_jobs': jobs, 'information_unit': 1.0}      # what the commission reads of the head's summary
    message = head_to_child.msg_to_child('monitor', call, head)
    assert message.message == {} and message.selection == ('job_returncode',)      # nothing the model wrote passes
    assert message.objective == 'Assess the progress of job ' + handle + '.'
    assert message.assignment == {
        'version': 'monitor_assignment_v2', 'handoff_refs': [handoff_ref], 'known_progress_refs': [known],
        'dependency_handoff_refs': [], 'requested_fields': list(read_from_parent.FIELD_OPTIONS),
        'information_unit': 1.0}
    entry = {'assignment': message.assignment, 'message': message.message, 'selection': list(message.selection)}
    linked = link(BindingRegistry([Monitor()]), PATH, entry, run_id='from-head', journal=held['journal'],
                  collaborators=collaborators(held, STEPPED))
    request = asyncio.run(linked.next_decision())
    assert [(check['check_ref'], check['made_by']) for check in request.context['checks']] == [
        (known, 'commissioner')]
    (held['tmp'] / 'release').touch()
    wait_for(job_file(held, handle, 'result.json'))
    ended = observe(linked)
    assert ended['state'] == 'finished' and ended['informative'] is True and credit_of(linked) == 1.0
    result = Monitor.final_to_parent(summary_of(linked), {'credit': 1.0}, message.selection)
    assert result['finding']['state'] == 'finished' and result['check_refs'] == [ended['check_ref']]
    assert result['job_returncode'] == {'known': True, 'value': 0}
    assert final_to_parent.RETURN_FORM.select(message.selection).admit(result, 'return') == result
    with pytest.raises(KeyError):                 # a job the commissioner does not hold as outstanding
        head_to_child.msg_to_child('monitor', {**call, 'handoff_ref': 'row_' + '0' * 64}, head)
