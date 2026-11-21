"""The A107 monitor on a job of the API route, without a model call: the run's caller steps the entry Episode.

The job is a BLAST search on a real HTTP server of this test process that speaks the NCBI BLAST Common URL API
(``episode_support/jobs/tests/blast_url_api_server.py``): it answers ``WAITING`` to the first status request of a
job and ``READY`` afterwards. The route is the real ``ApiJobRoute`` with its real HTTP client and its spacing rules
(made short); ``job_probe`` launches the job through ``job_access`` and the monitor is linked on the job's handoff
row, passed as a record. The Store, the journal, the job services, the estimate table and the yield controller are
the real ones. Nothing is faked. No service outside this process is contacted."""
import asyncio
from datetime import datetime
import json
import time

import pytest

from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.jobs.api_job_route import ApiJobRoute
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.jobs.tests.blast_url_api_server import (
    blast_url_api_service, route_configuration)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.tests.job_probe.episode import JobProbe
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    INPUT_CHARACTERS, admitted_by_provider, violations)

from ..episode import ExecutionProgressAssessment as Monitor
from ..messages import final_to_parent, read_from_parent
from ..task import CHECK_KIND
from .test_branch_execution_progress_assessment_model_run import (
    PATH, SELECTABLE, SETTINGS, Switch, collaborators, configuration, monitor, path_of)
from .test_monitor_units import credit_of, estimate, observe, options, stepped, summary_of, unit

API = 'blast_test'
QUERY = 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ'
JOB = {'program': 'blastp', 'database': 'swissprot', 'hitlist_size': 5, 'query_file': 'query.fasta'}
POLL_SPACING = 1.0
COST = SETTINGS[PATH]['cost']
NOT_MEASURED = {'returncode': None, 'duration_seconds': None, 'elapsed_seconds': None, 'outputs': []}
UNKNOWN_MEASUREMENTS = {
    'job_returncode': {'known': False}, 'job_duration_seconds': {'known': False},
    'job_elapsed_seconds': {'known': False}, 'stdout_bytes': {'known': False}, 'stderr_bytes': {'known': False},
    'log_window_refs': [], 'event_receipt_refs': []}


@pytest.fixture
def held(tmp_path):
    with blast_url_api_service(waiting_polls=1) as service:
        settings = {**configuration(tmp_path), 'api': {API: route_configuration(
            service, tmp_path / 'api_jobs', request_spacing=0.05, poll_spacing=POLL_SPACING)}}
        switch = Switch()
        world = {'store': Store(tmp_path / 'store'), 'configuration': settings, 'tmp': tmp_path, 'service': service,
                 'services': {**job_services(settings), 'switch': lambda: switch},
                 'journal': RunJournal(tmp_path / 'journal.sqlite3'),
                 'provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)}
        yield world
        world['store'].close()


def api_job(held, run_id='launch-api'):
    """Launch one BLAST job on the test service through ``job_access``; its handle and its handoff reference."""
    query = held['store'].artifact(QUERY.encode(), 'text/plain')
    plan = [{'tool': 'launch', 'arguments': {'resource_id': API, 'job': JOB, 'inputs': {'query.fasta': query},
                                             'estimates': None, 'cut': None}}]
    entry = {'assignment': {'input_refs': [query], 'job_refs': []}, 'message': {'plan': plan}, 'selection': []}
    asyncio.run(link(BindingRegistry([JobProbe()]), 'job_probe', entry, run_id=run_id, journal=held['journal'],
                     collaborators=collaborators(held)).run())
    launched = held['journal'].units(run_id, (('job_probe', run_id),))[0][2]['outcome']
    return launched['job'], launched['handoff_ref']


def spaced(held, remote_id='TESTRID0001'):
    """Wait until the provider's spacing permits a status request of the job: the route's own rule, read from the
    rate state of its workspace."""
    time.sleep(ApiJobRoute(held['configuration']['api'][API], resource_id=API).spacing('status', remote_id))


def polls(held):
    return held['service'].received(FORMAT_OBJECT='SearchInfo')


def offered(request):
    return [line.split(':')[0][2:] for line in request.instructions.splitlines() if line.startswith('- ')]


def read_again_until_stopped(linked, check_ref):
    """Read the held check again until the Episode's yield controller stops it. A re-read takes no time and makes
    no request to the service; it earns nothing. How many re-reads it took."""
    fields, count = summary_of(linked)['requested_fields'], 0
    while not linked.view.controller_state.stop:               # only the yield controller ends the Episode
        again = unit(linked, 'progress_read', {'check_ref': check_ref, 'requested_fields': fields})
        assert again['check_ref'] == check_ref
        count += 1
    return count


def test_the_request_for_an_api_job_offers_only_what_such_a_job_has(held):
    handle, handoff_ref = api_job(held)
    linked, request = stepped(held, handoff_ref, 'first')                    # every field asked, log windows too
    print('\nREQUEST INSTRUCTIONS\n' + request.instructions)
    print('REQUEST CONTEXT\n' + json.dumps(request.context, indent=1))
    print('REQUEST SCHEMA\n' + json.dumps(request.output_schema))
    assert 'log_windows' in summary_of(linked)['requested_fields'] and summary_of(linked)['job']['log_names'] == []
    # The request says first what the episode is for, and that logs are read only of a job that keeps them.
    assert request.instructions.startswith('You monitor one job.') and 'when it keeps logs' in request.instructions
    # A job of a web service has no log and no end event: only the check is offered, in the text and in the form.
    assert offered(request) == ['progress_observe']
    assert [item['tool']['enum'] for item in options(request)] == [['progress_observe']]
    for absent in ('progress_log', 'progress_wait', 'stdout.log', 'elapsed seconds', 'exec_command'):
        assert absent not in request.instructions
    # The request says what a check of such a job shows and what a check that comes too early is.
    for said in ('provider_status', 'has_hits', 'provider_spacing_required', 'seconds_between_status_requests'):
        assert said in request.instructions
    assert request.context['job'] == {
        'handle': handle, 'resource': API, 'resource_kind': 'api',
        'submitted_at': request.context['job']['submitted_at'], 'launch_estimates': None,
        'seconds_between_status_requests': POLL_SPACING}
    text, schema = admitted_by_provider(request, held['tmp'] / 'provider')
    assert violations(schema) == [] and len(text) <= INPUT_CHARACTERS
    # The decision asked nothing of the provider: what it read of the route and of the estimate table is recorded.
    assert [item['fields']['CMD'] for item in held['service'].requests] == ['Put']
    assert [read['request'] for read in held['journal'].service_reads('first', path_of('first'))] == [
        {'service': 'estimate_table', 'member': 'kind_statistics', 'arguments': [CHECK_KIND]},
        {'service': 'job_access', 'member': 'describe', 'arguments': [API]}]


def test_checks_of_a_queued_then_finished_api_job_and_a_check_the_provider_spacing_refuses(held):
    _, handoff_ref = api_job(held)
    linked, _ = stepped(held, handoff_ref, 'checks')
    spaced(held)
    first = observe(linked, probability=0.9)
    assert first['status'] == 'completed' and first['state'] == 'queued' and first['result_available'] is False
    assert first['assessment'] == {**NOT_MEASURED, 'provider_status': 'WAITING', 'has_hits': None}
    assert first['informative'] is True and credit_of(linked) == 1.0
    assert estimate(held, 'checks', 0)['actual'] == {'gain': 1.0, 'cost': 0.0, 'outcome': 'informative',
                                                     'state': 'queued'}
    # A check before the provider's spacing permits it: not sent, a failed unit, no check row, nothing earned.
    early = observe(linked, probability=0.5)
    assert early['status'] == 'failed' and early['failure']['code'] == 'provider_spacing_required'
    assert early['failure']['detail']['sent'] is False and early['failure']['detail']['action'] == 'status'
    assert 0 < early['failure']['detail']['retry_after_seconds'] <= POLL_SPACING
    assert len(polls(held)) == 1 and credit_of(linked) == 1.0
    assert [check['check_ref'] for check in summary_of(linked)['checks']] == [first['check_ref']]
    assert estimate(held, 'checks', 1)['actual'] is None             # the expectation stays open
    request = asyncio.run(linked.next_decision())
    assert offered(request) == ['progress_observe', 'progress_read']
    assert request.context['checks'] == [{
        'check_ref': first['check_ref'], 'observed_at': first['observed_at'], 'state': 'queued',
        'result_available': False, **NOT_MEASURED, 'provider_status': 'WAITING', 'has_hits': None,
        'made_by': 'this_monitor'}]
    assert request.context['units'] == [
        {'action': 'progress_observe', 'status': 'completed', 'check_ref': first['check_ref'],
         'new_information': True, 'credit_earned': 1.0},
        {'action': 'progress_observe', 'status': 'failed', 'failure_code': 'provider_spacing_required',
         'credit_earned': 0.0, 'failure_detail': early['failure']['detail']}]
    # When the spacing permits it the job is asked again: it has finished and its results are available.
    spaced(held)
    ready = observe(linked, probability=0.5)
    assert ready['state'] == 'finished' and ready['result_available'] is True and ready['informative'] is True
    assert ready['assessment'] == {**NOT_MEASURED, 'provider_status': 'READY', 'has_hits': True}
    assert credit_of(linked) == 2.0 and len(polls(held)) == 2
    assert polls(held)[1]['at'] - polls(held)[0]['at'] >= POLL_SPACING
    # The route answers the state of an ended job from its record: no request, the same check row, nothing new.
    again = observe(linked, probability=0.1)
    assert again['check_ref'] == ready['check_ref'] and again['informative'] is False
    assert credit_of(linked) == 2.0 and len(polls(held)) == 2
    assert estimate(held, 'checks', 3)['actual']['outcome'] == 'nothing_new'
    assert [check['state'] for check in summary_of(linked)['checks']] == ['queued', 'finished']
    # The monitor contacted the service for status only: it submitted nothing and fetched nothing.
    assert [item['fields']['CMD'] for item in held['service'].requests] == ['Put', 'Get', 'Get']
    assert held['service'].received(FORMAT_TYPE='JSON2') == []


def test_two_visits_of_an_api_job_return_queued_and_then_finished(held):
    """Two visits with the monitor's own settings. Its controller is the accumulation controller: it goes on after
    an informative check and ends the visit when further actions are not expected to earn more than they cost. The
    second visit is passed the first visit's check row as its baseline."""
    _, handoff_ref = api_job(held)
    first = monitor(held, handoff_ref, 'visit-1')
    asyncio.run(first.next_decision())
    spaced(held)
    waiting = observe(first, probability=0.9, cost=COST)
    assert waiting['state'] == 'queued' and first.view.controller_state.stop is False
    print('RE-READS UNTIL THE CONTROLLER STOPPED VISIT 1', read_again_until_stopped(first, waiting['check_ref']))
    result = asyncio.run(first.run())['result'].as_record()
    assert held['journal'].run_state('visit-1')[1]['ended_by'] == 'yield_stop'
    assert result == {
        'credit': 1.0,
        'finding': {'observed': True, 'state': 'queued', 'result_available': False,
                    'observed_at_unix_seconds': datetime.fromisoformat(waiting['observed_at']).timestamp()},
        'check_refs': [waiting['check_ref']], **UNKNOWN_MEASUREMENTS}
    assert final_to_parent.RETURN_FORM.select(SELECTABLE).admit(result, 'return') == result
    # The second visit holds the first check as what its commissioner already knows.
    second = monitor(held, handoff_ref, 'visit-2', known=result['check_refs'])
    request = asyncio.run(second.next_decision())
    assert [(check['made_by'], check['state'], check['provider_status']) for check in request.context['checks']] == [
        ('commissioner', 'queued', 'WAITING')]
    assert request.context['credit']['current'] == 0.0
    spaced(held)
    ready = observe(second, probability=0.9, cost=COST)
    assert ready['state'] == 'finished' and ready['informative'] is True
    print('RE-READS UNTIL THE CONTROLLER STOPPED VISIT 2', read_again_until_stopped(second, ready['check_ref']))
    result = asyncio.run(second.run())['result'].as_record()
    assert held['journal'].run_state('visit-2')[1]['ended_by'] == 'yield_stop'
    assert result == {
        'credit': 1.0,
        'finding': {'observed': True, 'state': 'finished', 'result_available': True,
                    'observed_at_unix_seconds': datetime.fromisoformat(ready['observed_at']).timestamp()},
        'check_refs': [ready['check_ref']], **UNKNOWN_MEASUREMENTS}
    assert len(polls(held)) == 2 and len(held['service'].received(CMD='Put')) == 1


def test_a_failed_and_an_unknown_api_job_are_states_of_the_check(held):
    held['service'].final, held['service'].waiting_polls = 'FAILED', 0
    _, handoff_ref = api_job(held)
    linked, _ = stepped(held, handoff_ref, 'failed')
    spaced(held)
    failed = observe(linked)
    assert failed['status'] == 'completed' and failed['state'] == 'failed' and failed['result_available'] is False
    assert failed['assessment'] == {**NOT_MEASURED, 'provider_status': 'FAILED', 'has_hits': None}
    assert Monitor.final_to_parent(summary_of(linked), {'credit': 1.0}, ())['finding']['state'] == 'failed'
    # A job the service does not know (any more).
    time.sleep(0.06)                                          # the request spacing of the test service
    _, other_ref = api_job(held, 'launch-other')
    held['service'].jobs.clear()
    other, _ = stepped(held, other_ref, 'unknown')
    spaced(held, 'TESTRID0002')
    unknown = observe(other)
    assert unknown['state'] == 'unknown' and unknown['assessment']['provider_status'] == 'UNKNOWN'


def test_an_api_job_passed_as_a_dependency_is_offered_and_its_commission_passes_its_handoff_row(held):
    _, target_ref = api_job(held)
    time.sleep(0.06)                                          # the request spacing of the test service
    dependency, dependency_ref = api_job(held, 'launch-dependency')
    linked, request = stepped(held, target_ref, 'with-dependency', dependencies=[dependency_ref])
    assert offered(request) == ['progress_observe', 'monitor_dependency']
    assert request.context['dependencies'] == [{
        'handle': dependency, 'resource_kind': 'api',
        'submitted_at': request.context['dependencies'][0]['submitted_at'], 'latest_check': None}]
    message = Monitor.msg_to_child('monitor', {'dependency_handle': dependency}, summary_of(linked))
    assert read_from_parent.ASSIGNMENT_FORM.admit(message.assignment, 'assignment') == {
        'version': 'monitor_assignment_v2', 'handoff_refs': [dependency_ref], 'known_progress_refs': [],
        'dependency_handoff_refs': [], 'requested_fields': list(read_from_parent.FIELD_OPTIONS),
        'information_unit': 1.0}


def test_a_later_visit_of_a_job_still_waiting_earns_nothing_and_only_its_controller_ends_it(held):
    held['service'].waiting_polls = 1000                      # the search stays unfinished
    _, handoff_ref = api_job(held)
    first = monitor(held, handoff_ref, 'visit-1')
    asyncio.run(first.next_decision())
    spaced(held)
    known = [observe(first, probability=0.9, cost=COST)['check_ref']]
    later = monitor(held, handoff_ref, 'visit-2', known=known)
    asyncio.run(later.next_decision())
    spaced(held)
    outcomes = []
    while not later.view.controller_state.stop:               # a check each time: sent when the spacing permits
        outcomes.append(observe(later, probability=0.1, cost=COST))
    print('UNITS UNTIL THE CONTROLLER STOPPED', [
        outcome['state'] if outcome['status'] == 'completed' else outcome['failure']['code'] for outcome in outcomes])
    assert outcomes[0]['state'] == 'queued' and outcomes[0]['informative'] is False
    assert all(outcome['status'] == 'failed' or outcome['informative'] is False for outcome in outcomes)
    result = asyncio.run(later.run())['result'].as_record()
    assert held['journal'].run_state('visit-2')[1]['ended_by'] == 'yield_stop'
    assert result['credit'] == 0.0 and result['finding']['state'] == 'queued'
    assert result['finding']['result_available'] is False and result['check_refs']
    # Every status request the service received kept the spacing; the refused checks were not sent.
    times = [item['at'] for item in polls(held)]
    assert min(later_ - earlier for earlier, later_ in zip(times, times[1:])) >= POLL_SPACING
    assert len(times) == 1 + len([outcome for outcome in outcomes if outcome['status'] == 'completed'])
