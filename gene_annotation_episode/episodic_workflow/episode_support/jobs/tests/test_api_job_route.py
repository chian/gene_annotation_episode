"""The API job route, against a real HTTP server of this test process that speaks the NCBI BLAST Common URL API
(``blast_url_api_server.py``), and through the real runner: ``job_services`` binds the route by resource id and the
``job_probe`` test episode launches, checks and fetches through ``JobAccess`` with a real ``Store`` and
``RunJournal``. The route's HTTP client is the one it has; nothing of it is replaced."""
import asyncio
import json
import shutil
import time

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from episode_runtime.job_access import RouteRequestError
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.jobs.api_job_route import ApiJobRoute, SPACING
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import LOGS, status_reading
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services

from .blast_url_api_server import blast_url_api_service, route_configuration
from .job_probe.episode import JobProbe

QUERY = 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ'
JOB = {'program': 'blastp', 'database': 'swissprot', 'hitlist_size': 5, 'query_file': 'query.fasta'}
FILES = {'query.fasta': QUERY.encode()}
OWNER = {'run_id': 'run', 'episode_id': 'episode'}
API = 'blast_test'


@pytest.fixture
def service():
    with blast_url_api_service() as running:
        yield running


def route_on(service, directory, **settings):
    return ApiJobRoute(route_configuration(service, directory / 'api_jobs', **settings), resource_id=API)


def spaced(route, action, remote_id=None):
    time.sleep(route.spacing(action, remote_id))


def failure(call, *arguments):
    with pytest.raises(RouteRequestError) as raised:
        call(*arguments)
    return raised.value.failure


# -- the three requests of the protocol ------------------------------------------------------------------------
def test_a_job_is_submitted_asked_and_fetched_with_one_request_each(service, tmp_path):
    route = route_on(service, tmp_path)
    made = route.submit('job_a', JOB, FILES, OWNER)
    put, = service.requests
    assert put['method'] == 'POST' and put['fields'] == {
        'CMD': 'Put', 'PROGRAM': 'blastp', 'DATABASE': 'swissprot', 'QUERY': '>query\n' + QUERY + '\n',
        'FORMAT_TYPE': 'Text', 'HITLIST_SIZE': '5', 'tool': 'api-job-route-test'}
    # Nothing authenticates: no contact address was configured, so none is sent, and no credential header.
    assert put['user_agent'] == 'api-job-route-test' and put['authorization'] is None and put['cookie'] is None
    native = made['native']
    assert native['remote_id'] == 'TESTRID0001' and native['expected_seconds'] == 0 and made['adopted'] is False
    assert native['request'] == {'program': 'blastp', 'database': 'swissprot', 'hitlist_size': 5,
                                 'query_title': 'query', 'query_length': len(QUERY),
                                 'sequence_sha256': native['request']['sequence_sha256']}
    assert made['reply']['http_status'] == 200 and made['reply']['information'] == ['RID = TESTRID0001', 'RTOE = 0']

    spaced(route, 'status', 'TESTRID0001')
    waiting = route.status('job_a', native)
    assert (waiting['state'], waiting['result_available']) == ('queued', False)
    assert waiting['reply']['provider_status'] == 'WAITING' and waiting['reply']['from_record'] is False
    # Results are not asked of a job that is not known to have finished; nothing is sent for the refusal.
    assert failure(route.results, 'job_a', native) == {'code': 'results_not_available',
                                                       'detail': {'job': 'job_a', 'state': 'queued'}}
    spaced(route, 'status', 'TESTRID0001')
    ready = route.status('job_a', native)
    assert (ready['state'], ready['result_available']) == ('finished', True)
    assert ready['reply']['provider_status'] == 'READY' and ready['reply']['has_hits'] is True
    assert [item['fields']['FORMAT_OBJECT'] for item in service.received(CMD='Get')] == ['SearchInfo'] * 2

    spaced(route, 'fetch')
    catalog = route.results('job_a', native)
    assert [(item['name'], item['media_type']) for item in catalog] == [
        ('blast_result.json', 'application/json'), ('blast_result.json2.zip', 'application/zip')]
    document = route.read('job_a', native, 'blast_result.json', 0, catalog[0]['bytes'])
    search = json.loads(document)['BlastOutput2']['report']['results']['search']
    assert search['query_title'] == 'query' and search['query_len'] == len(QUERY)
    assert route.read('job_a', native, 'blast_result.json', 2, 5) == document[2:7]
    assert len(route.read('job_a', native, 'blast_result.json2.zip', 0, catalog[1]['bytes'])) == catalog[1]['bytes']
    assert failure(route.read, 'job_a', native, 'other.json', 0, 1)['code'] == 'result_file_missing'
    # What is known is not asked again: the ended state and the fetched results are answered from the record.
    again = route.status('job_a', native)
    assert again['state'] == 'finished' and again['reply']['from_record'] is True
    assert again['observed_at'] == ready['observed_at'] and route.results('job_a', native) == catalog
    assert [item['fields']['CMD'] for item in service.requests] == ['Put', 'Get', 'Get', 'Get']
    assert len(service.received(FORMAT_TYPE='JSON2')) == 1


def test_a_handle_is_submitted_at_most_once(service, tmp_path):
    route = route_on(service, tmp_path)
    first = route.submit('job_a', JOB, FILES, OWNER)
    # The same handle again (a unit that runs again), also from a route built anew (a resumed run): the recorded
    # submission is returned with its original time and nothing is sent.
    second = route_on(service, tmp_path).submit('job_a', JOB, FILES, OWNER)
    assert second == {**first, 'adopted': True}
    assert len(service.received(CMD='Put')) == 1
    # Another handle is another job.
    spaced(route, 'submit')
    assert route.submit('job_b', JOB, FILES, OWNER)['native']['remote_id'] == 'TESTRID0002'


def test_a_copied_workspace_serves_the_recorded_job_keeps_its_spacing_and_does_not_submit_again(service, tmp_path):
    """A run's directory is copied to go on with its outstanding job elsewhere: the route bound to the copy finds
    the job by its handle, although the handoff recorded the first directory."""
    first = route_on(service, tmp_path / 'first', request_spacing=0.05, poll_spacing=0.6)
    made = first.submit('job_a', JOB, FILES, OWNER)
    spaced(first, 'status', 'TESTRID0001')
    assert first.status('job_a', made['native'])['reply']['provider_status'] == 'WAITING'
    shutil.copytree(tmp_path / 'first', tmp_path / 'copy')
    copy = route_on(service, tmp_path / 'copy', request_spacing=0.05, poll_spacing=0.6)
    assert made['native']['directory'] == str(tmp_path / 'first' / 'api_jobs' / 'job_a')
    # The copied answer of the submission is the submission: nothing is sent for the same handle.
    again = copy.submit('job_a', JOB, FILES, OWNER)
    assert again == {**made, 'adopted': True, 'native': {
        **made['native'], 'directory': str(tmp_path / 'copy' / 'api_jobs' / 'job_a')}}
    assert len(service.received(CMD='Put')) == 1
    # The copied rate state holds the time of the last status request: the copy keeps the provider's spacing.
    early = failure(copy.status, 'job_a', made['native'])
    assert early['code'] == SPACING and early['detail']['sent'] is False
    assert len(service.received(FORMAT_OBJECT='SearchInfo')) == 1
    spaced(copy, 'status', 'TESTRID0001')
    ready = copy.status('job_a', made['native'])
    assert ready['state'] == 'finished' and ready['reply']['provider_status'] == 'READY'
    polls = [item['at'] for item in service.received(FORMAT_OBJECT='SearchInfo')]
    assert len(polls) == 2 and polls[1] - polls[0] >= 0.6
    # What the copy learned is its own: the first workspace still holds the earlier status.
    assert json.loads((tmp_path / 'first' / 'api_jobs' / 'job_a' / 'status.json').read_text())['state'] == 'queued'


def test_the_status_reading_of_an_api_job_holds_the_provider_status_and_whether_there_are_hits(service, tmp_path):
    """``job_progress.status_reading`` (the ``assess`` of a monitor's check) on the route's real status replies."""
    route = route_on(service, tmp_path)
    native = route.submit('job_a', JOB, FILES, OWNER)['native']
    handoff = {'detail': {'kind': route.kind, 'native': native}}
    spaced(route, 'status', native['remote_id'])
    waiting = route.status('job_a', native)
    assert waiting['state'] == 'queued' and status_reading(waiting, handoff) == {
        'returncode': None, 'duration_seconds': None, 'elapsed_seconds': None, 'outputs': [],
        'provider_status': 'WAITING', 'has_hits': None}
    spaced(route, 'status', native['remote_id'])
    ready = route.status('job_a', native)
    assert ready['state'] == 'finished' and status_reading(ready, handoff) == {
        'returncode': None, 'duration_seconds': None, 'elapsed_seconds': None, 'outputs': [],
        'provider_status': 'READY', 'has_hits': True}
    # The ended state is answered from the route's record, and is read the same.
    assert status_reading(route.status('job_a', native), handoff) == status_reading(ready, handoff)
    # A job of this route keeps no log a monitor could read a window of.
    assert LOGS[route.kind] == () and failure(route.read, 'job_a', native, 'stdout.log', 0, 10) == {
        'code': 'result_file_missing', 'detail': {'job': 'job_a', 'name': 'stdout.log'}}


def test_a_plain_json_reply_and_a_fasta_query_are_read(service, tmp_path):
    service.archive, service.waiting_polls = False, 0
    route = route_on(service, tmp_path)
    native = route.submit('job_a', JOB, {'query.fasta': ('>target one protein\n' + QUERY[:20] + '\n'
                                                         + QUERY[20:] + '\n').encode()}, OWNER)['native']
    assert native['request']['query_title'] == 'target' and native['request']['query_length'] == len(QUERY)
    assert service.requests[0]['fields']['QUERY'] == '>target\n' + QUERY + '\n'
    spaced(route, 'status', native['remote_id'])
    assert route.status('job_a', native)['state'] == 'finished'
    spaced(route, 'fetch')
    assert [item['name'] for item in route.results('job_a', native)] == ['blast_result.json']


def test_a_configured_contact_address_is_sent_and_none_is_sent_without_one(service, tmp_path):
    route = route_on(service, tmp_path, contact_email='contact@example.org')
    assert route.describe()['contact_configured'] is True and route.describe()['authentication'] == 'none'
    route.submit('job_a', JOB, FILES, OWNER)
    assert service.requests[0]['fields']['email'] == 'contact@example.org'


# -- the provider's spacing rules --------------------------------------------------------------------------------
def test_a_contact_that_comes_too_early_is_not_sent_and_says_when_it_may_be(service, tmp_path):
    route = route_on(service, tmp_path, request_spacing=0.3, poll_spacing=1.0)
    native = route.submit('job_a', JOB, FILES, OWNER)['native']
    early = failure(route.status, 'job_a', native)
    assert early['code'] == SPACING and early['detail']['sent'] is False
    assert 0 < early['detail']['retry_after_seconds'] <= 0.3 and len(service.requests) == 1
    early = failure(route.submit, 'job_b', JOB, FILES, OWNER)
    assert early['code'] == SPACING and len(service.requests) == 1
    # A refused submission left no intent: the same handle is submitted once the spacing permits it.
    spaced(route, 'submit')
    assert route.submit('job_b', JOB, FILES, OWNER)['adopted'] is False
    spaced(route, 'status', native['remote_id'])
    assert route.status('job_a', native)['state'] == 'queued'
    # The same remote job is asked again only after the poll spacing; another contact only after the request spacing.
    time.sleep(0.35)
    early = failure(route.status, 'job_a', native)
    assert early['code'] == SPACING and 0.3 < early['detail']['retry_after_seconds'] <= 1.0
    spaced(route, 'status', native['remote_id'])
    assert route.status('job_a', native)['state'] == 'finished'
    polls = [item['at'] for item in service.received(FORMAT_OBJECT='SearchInfo')]
    contacts = [item['at'] for item in service.requests]
    assert polls[1] - polls[0] >= 1.0 and min(b - a for a, b in zip(contacts, contacts[1:])) >= 0.3


def test_wait_polls_at_the_provider_spacing_until_the_job_has_ended(tmp_path):
    with blast_url_api_service(waiting_polls=2, expected_seconds=1) as service:
        route = route_on(service, tmp_path, request_spacing=0.05, poll_spacing=0.3)
        made = route.submit('job_a', JOB, FILES, OWNER)
        asyncio.run(route.wait('job_a', made['native']))
        polls = [item['at'] for item in service.received(FORMAT_OBJECT='SearchInfo')]
        assert len(polls) == 3 and polls[0] - service.requests[0]['at'] >= 1.0      # the service's own estimate
        assert min(b - a for a, b in zip(polls, polls[1:])) >= 0.3
        assert route.status('job_a', made['native'])['state'] == 'finished'


# -- a service that refuses, fails or is not there ---------------------------------------------------------------
def test_a_refused_submission_is_recorded_and_not_sent_again(service, tmp_path):
    service.submit_status = 503
    route = route_on(service, tmp_path)
    refused = failure(route.submit, 'job_a', JOB, FILES, OWNER)
    assert refused['code'] == 'provider_http_503' and refused['detail']['http_status'] == 503
    service.submit_status = 200
    assert failure(route.submit, 'job_a', JOB, FILES, OWNER)['code'] == 'provider_http_503'
    assert len(service.requests) == 1


def test_a_reply_without_a_job_identity_is_a_failed_submission(service, tmp_path):
    service.give_rid = False
    refused = failure(route_on(service, tmp_path).submit, 'job_a', JOB, FILES, OWNER)
    assert refused['code'] == 'provider_submission_response_invalid'
    assert refused['detail']['reason'] == 'blast_submission_rid_missing'
    assert refused['detail']['information'] == ['RID =', 'RTOE = 0']


def test_a_redirect_is_not_followed(service, tmp_path):
    service.redirect_to = service.url + '?elsewhere=1'
    refused = failure(route_on(service, tmp_path).submit, 'job_a', JOB, FILES, OWNER)
    assert refused['code'] == 'provider_redirect_not_followed' and len(service.requests) == 1


def test_a_service_that_is_not_there_is_a_failed_request_and_the_outcome_stays_unknown(tmp_path):
    with blast_url_api_service() as service:
        route = route_on(service, tmp_path)
    # The service has stopped listening: the request cannot be made.
    lost = failure(route.submit, 'job_a', JOB, FILES, OWNER)
    assert lost['code'] == 'provider_connection_failed' and lost['detail']['sent'] == 'unknown'
    # The intent was recorded before the request, so the same handle is never sent a second time on a guess.
    assert failure(route.submit, 'job_a', JOB, FILES, OWNER) == {
        'code': 'submission_outcome_unknown', 'detail': {'job': 'job_a', 'sent': 'unknown'}}


def test_a_failed_and_an_unknown_remote_job_are_states_and_end_a_wait(service, tmp_path):
    service.final, service.waiting_polls = 'FAILED', 0
    route = route_on(service, tmp_path)
    native = route.submit('job_a', JOB, FILES, OWNER)['native']
    asyncio.run(route.wait('job_a', native))
    failed = route.status('job_a', native)
    assert (failed['state'], failed['result_available']) == ('failed', False)
    assert failure(route.results, 'job_a', native)['detail']['state'] == 'failed'
    spaced(route, 'submit')
    other = route.submit('job_b', JOB, FILES, OWNER)['native']
    service.jobs.clear()                                     # the service no longer knows the job
    with pytest.raises(RouteRequestError) as unknown:
        asyncio.run(route.wait('job_b', other))
    assert unknown.value.failure['code'] == 'job_state_unknown'
    assert unknown.value.failure['detail']['provider_status'] == 'UNKNOWN'


def test_the_service_has_no_cancel_and_a_job_that_is_not_of_the_form_raises(service, tmp_path):
    route = route_on(service, tmp_path)
    native = route.submit('job_a', JOB, FILES, OWNER)['native']
    assert failure(route.cancel, 'job_a', native)['code'] == 'cancel_not_offered_by_the_service'
    with pytest.raises(ValueError, match='ncbi_blast_job_requires_exactly'):
        route.submit('job_b', {**JOB, 'email': 'x'}, FILES, OWNER)
    with pytest.raises(ValueError, match='ncbi_blast_job_program_database_or_hitlist_size_invalid'):
        route.submit('job_b', {**JOB, 'program': 'psiblast'}, FILES, OWNER)
    with pytest.raises(ValueError, match='ncbi_blast_job_requires_a_single_query_sequence'):
        route.submit('job_b', JOB, {'query.fasta': b'>a\nMKT\n>b\nMKV\n'}, OWNER)
    with pytest.raises(ValueError, match='api_route_configuration_requires_exactly'):
        ApiJobRoute({'service': 'ncbi_blast'}, resource_id=API)
    with pytest.raises(ValueError, match='api_route_base_url_must_be_a_plain_http_address_without_credentials'):
        ApiJobRoute({**route_configuration(service, tmp_path / 'other'),
                     'base_url': 'https://user:secret@example.org/Blast.cgi'}, resource_id=API)
    assert len(service.requests) == 1


# -- through the real runner: job_services binds the route, JobAccess keeps the rows in custody ------------------
class Switch:
    """A real service of the test run: whether the cut the plan asks for is wanted."""

    def __init__(self):
        self.fail = False


@pytest.fixture
def world(service, tmp_path):
    store = Store(tmp_path / 'store')
    configuration = {
        'local': {}, 'pbs': {}, 'api': {API: route_configuration(service, tmp_path / 'api_jobs')},
        'capabilities': [{'resource_id': API, 'kind': 'api', 'availability': 'available',
                          'observed_at': '2026-11-19T00:00:00+00:00', 'provenance_refs': [],
                          'knowledge_entry_ids': [], 'tool_names': ['job.launch', 'job.check', 'job.fetch']}],
        'event_ledger_directory': str(tmp_path / 'events'),
        'estimate_table_path': str(tmp_path / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(tmp_path / 'launch'),
        'tool_knowledge_directory': str(tmp_path / 'knowledge')}
    switch = Switch()
    yield {'store': store, 'query': store.artifact(QUERY.encode(), 'text/plain'), 'switch': switch,
           'service': service, 'journal': RunJournal(tmp_path / 'journal.sqlite3'),
           'collaborators': {'store': store, 'model_provider': ModelProvider(load_config(), tmp_path / 'model_calls',
                                                                             tmp_path),
                             'continuation': {'job_probe': {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}},
                             'services': {**job_services(configuration), 'switch': lambda: switch}}}
    store.close()


def step(tool_name, **arguments):
    return {'tool': tool_name, 'arguments': arguments}


def linked(world, run_id, plan):
    entry = {'assignment': {'input_refs': [world['query']], 'job_refs': []}, 'message': {'plan': plan},
             'selection': []}
    return link(BindingRegistry([JobProbe()]), 'job_probe', entry, run_id=run_id, journal=world['journal'],
                collaborators=world['collaborators'])


def outcomes(world, run_id):
    return [unit[2]['outcome'] for unit in world['journal'].units(run_id, (('job_probe', run_id),))]


def launch_step(world, cut=None):
    return step('launch', resource_id=API, job=JOB, inputs={'query.fasta': world['query']}, estimates=None, cut=cut)


def test_job_services_binds_the_api_route_by_its_resource_id(world):
    result = asyncio.run(linked(world, 'described', [
        {**step('echo'), 'read': ['job_access', 'resources']},
        {**step('echo'), 'read': ['job_access', 'describe', API]}]).run())['result'].as_record()
    listed, described = (outcome['read'] for outcome in outcomes(world, 'described'))
    assert listed == [{'resource_id': API, 'kind': 'api'}] and result['credit'] == 2.0
    assert described['service'] == 'ncbi_blast' and described['authentication'] == 'none'
    assert described['request_schema']['required'] == ['program', 'database', 'hitlist_size']
    assert described['query_unit_by_program']['blastp'] == 'aa' and described['cancel_offered'] is False
    with pytest.raises(ValueError, match='job_services_configuration_requires_exactly'):
        job_services({'api': {}})


def test_a_command_is_launched_once_waited_for_and_fetched_into_custody(world):
    job = step('command', resource_id=API, job=JOB, inputs={'query.fasta': world['query']})
    result = asyncio.run(linked(world, 'command', [job]).run())['result'].as_record()
    done, = outcomes(world, 'command')
    assert done['status'] == 'completed' and done['launch']['kind'] == 'api'
    fetched = done['fetch']
    assert fetched['outcome'] == 'results_acquired' and fetched['state'] == 'finished'
    names = {item['name']: item['ref'] for item in fetched['results']}
    assert sorted(names) == ['blast_result.json', 'blast_result.json2.zip']
    report = json.loads(world['store'].get_artifact(names['blast_result.json']))['BlastOutput2']['report']
    assert report['program'] == 'blastp' and report['results']['search']['query_len'] == len(QUERY)
    # The handoff and closure rows are work-table rows the unit produced, each with the service's reply as an
    # artifact; the job is closed, so the Episode leaves none outstanding.
    held = {item['ref']: item['how'] for item in world['journal'].receipts('command', (('job_probe', 'command'),))}
    assert held[done['launch']['handoff_ref']] == 'produced' and held[fetched['closure_ref']] == 'produced'
    assert json.loads(world['store'].get_artifact(done['launch']['reply_ref']))['remote_id'] == 'TESTRID0001'
    assert {done['launch']['handoff_ref'], fetched['closure_ref'], *names.values()} <= set(result['record_refs'])
    assert result['outstanding_jobs'] == []
    sent = [item['fields'] for item in world['service'].requests]
    assert [item['CMD'] for item in sent] == ['Put', 'Get', 'Get', 'Get'] and sent[-1]['FORMAT_TYPE'] == 'JSON2'


@pytest.mark.parametrize('cut', ['after', 'inside'])
def test_a_cut_launch_is_not_submitted_again_on_resume(world, cut):
    """``after``: the handoff row committed and the unit was cut (the rerun takes the row over, the route is not
    asked). ``inside``: the unit was cut before the row committed (the route is asked and returns the submission it
    recorded). The service receives one submission either way."""
    plan = [launch_step(world, cut=cut), step('check', handoff_ref={'from': 0, 'field': ['handoff_ref']}, cut=None)]
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='cut'):
        asyncio.run(linked(world, 'cut', plan).run())
    assert len(world['service'].received(CMD='Put')) == 1
    world['switch'].fail = False
    time.sleep(0.06)                                          # the request spacing of the test service
    result = asyncio.run(resume(BindingRegistry([JobProbe()]), run_id='cut', journal=world['journal'],
                                collaborators=world['collaborators']).run())['result'].as_record()
    launched, checked = outcomes(world, 'cut')
    assert launched['status'] == 'completed' and launched['submitted_at'] <= checked['observed_at']
    assert (launched['replayed'], launched['adopted']) == ((True, False) if cut == 'after' else (False, True))
    assert checked['state'] == 'queued' and checked['result_available'] is False
    assert len(world['service'].received(CMD='Put')) == 1 and len(world['service'].requests) == 2
    assert [job['job'] for job in result['outstanding_jobs']] == [launched['job']]
    # A finished run replays from the journal: nothing is sent.
    again = asyncio.run(resume(BindingRegistry([JobProbe()]), run_id='cut', journal=world['journal'],
                               collaborators=world['collaborators']).run())['result'].as_record()
    assert again == result and len(world['service'].requests) == 2
