"""The job services, run by the real runner on real jobs.

Every test links the ``job_probe`` test episode with a real ``Store``, ``RunJournal`` and model provider and the
services ``job_services`` builds. Local jobs are real detached systemd services of this machine
(``LocalJobRoute``); the remote route (``PbsSshRoute``) runs its real remote program through a local shell as its
transport, which carries a login-mode job end to end. No PBS scheduler exists on this machine, so a batch-mode job
reaches the scheduler call and is refused there; nothing stands in for the scheduler. These tests need the
workflow launcher (``tools/one_workflow.sh``): a local job runs inside the launcher's slice."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys

import pytest

from episode_runtime import BindingRegistry, CustodyError, RunJournal, link, resume
from episode_runtime.estimate_table import EstimateTable, EstimateTableError
from episode_runtime.job_access import JOB_LEDGER, JobAccess, RouteRequestError, job_handle
from episode_runtime.resource_adapters import ResourceAdapters
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs import action_value
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.gene_context_evidence.hpc_prediction import (
    log_score)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc_ledger import HPC_LEDGER, ledger_id
from gene_annotation_episode.episodic_workflow.episode_support.jobs.instruction_libraries import (
    InstructionLibraries)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.jobs.native_events import NATIVE_EVENT_RECEIPTS
from gene_annotation_episode.episodic_workflow.episode_support.jobs.pbs_job_route import PbsSshRoute
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import ToolKnowledge

from .job_probe.episode import JobProbe

LIBRARY = Path(__file__).resolve().parents[2]
SETTINGS = {'job_probe': {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}}
LOCAL, REMOTE, UNBOUND = 'local_test', 'remote_test', 'elsewhere'
SCHEDULER = {'qsub': 'qsub', 'qstat': 'qstat', 'qdel': 'qdel', 'qselect': 'qselect'}


def capability(resource_id, kind):
    return {'resource_id': resource_id, 'kind': kind, 'availability': 'available',
            'observed_at': '2026-11-19T00:00:00+00:00', 'provenance_refs': [], 'knowledge_entry_ids': [],
            'tool_names': ['job.launch', 'job.check', 'job.fetch', 'job.cancel']}


class Switch:
    """A real service of the test run: whether the next cut the plan asks for is wanted."""

    def __init__(self):
        self.fail = False


@pytest.fixture
def world(tmp_path):
    store = Store(tmp_path / 'store')
    question = store.artifact('what is six times seven', 'text/plain')
    launch = LaunchInstructions.freeze(tmp_path / 'frozen_launch', source=LIBRARY / 'instructions' / 'launch')
    knowledge = ToolKnowledge.freeze(tmp_path / 'frozen_knowledge', source=LIBRARY / 'knowledge')
    configuration = {
        'local': {LOCAL: {'workspace': str(tmp_path / 'jobs'),
                          'policy': {'memory_bytes': 256 * 1024 ** 2, 'scratch_bytes': 64 * 1024 ** 2},
                          'cpu_threads': 1}},
        'pbs': {REMOTE: {'ssh_argv': ['/bin/sh', '-c'], 'python_executable': sys.executable,
                         'workspace': str(tmp_path / 'remote'), 'scheduler': SCHEDULER, 'poll_seconds': 0.05}},
        'capabilities': [capability(LOCAL, 'local'), capability(REMOTE, 'hpc'), capability(UNBOUND, 'hpc')],
        'event_ledger_directory': str(tmp_path / 'events'),
        'estimate_table_path': str(tmp_path / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(launch.directory),
        'tool_knowledge_directory': str(knowledge.directory)}
    switch = Switch()
    yield {'store': store, 'question': question, 'switch': switch, 'tmp': tmp_path, 'configuration': configuration,
           'services': {**job_services(configuration), 'switch': lambda: switch},
           'journal': RunJournal(tmp_path / 'journal.sqlite3'),
           'provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)}
    store.close()


def collaborators(world):
    return {'store': world['store'], 'model_provider': world['provider'], 'continuation': SETTINGS,
            'services': world['services']}


def run(world, run_id, plan, *, input_refs=(), job_refs=()):
    entry = {'assignment': {'input_refs': list(input_refs), 'job_refs': list(job_refs)},
             'message': {'plan': plan}, 'selection': []}
    linked = link(BindingRegistry([JobProbe()]), 'job_probe', entry, run_id=run_id, journal=world['journal'],
                  collaborators=collaborators(world))
    return asyncio.run(linked.run())['result'].as_record()


def again(world, run_id):
    return asyncio.run(resume(BindingRegistry([JobProbe()]), run_id=run_id, journal=world['journal'],
                              collaborators=collaborators(world)).run())['result'].as_record()


def path_of(run_id):
    return (('job_probe', run_id),)


def outcomes(world, run_id):
    return [unit[2]['outcome'] for unit in world['journal'].units(run_id, path_of(run_id))]


def step(tool_name, /, read=None, **arguments):
    return ({'tool': tool_name, 'arguments': arguments} if read is None
            else {'tool': tool_name, 'arguments': arguments, 'read': read})


def earlier(index, *field):
    return {'from': index, 'field': list(field)}


def python_job(code):
    return {'command': [sys.executable, '-c', code], 'env': {}}


def launch_step(job, *, resource_id=LOCAL, inputs=None, cut=None, read=None):
    return step('launch', read, resource_id=resource_id, job=job, inputs=inputs or {},
                estimates={'gain': {'value': 2.0, 'lower': 1.0, 'upper': 4.0}, 'done_about': '16:00'}, cut=cut)


def answer_job(release):
    """Reads its staged input, waits until ``release`` exists, then writes its answer."""
    return python_job(
        "import pathlib,time\n"
        "question=pathlib.Path('question.txt').read_text()\n"
        "while not pathlib.Path(" + repr(str(release)) + ").exists(): time.sleep(0.02)\n"
        "pathlib.Path('answer.txt').write_text(question.upper()+': 42')\nprint('answered')")


def counted_job(log):
    """Appends one line to ``log`` each time it really runs."""
    return python_job("import pathlib\nwith open(" + repr(str(log)) + ",'a') as s: s.write('ran\\n')\n"
                      "pathlib.Path('answer.txt').write_text('done')")


# -- job_access: launch, check, wait, fetch; a job left outstanding and taken up by a later run ----------------
def test_a_job_is_launched_checked_left_outstanding_and_fetched_by_a_later_run(world):
    release = world['tmp'] / 'release'
    first = run(world, 'launching', [
        launch_step(answer_job(release), inputs={'question.txt': world['question']}),
        step('check', handoff_ref=earlier(0, 'handoff_ref'), cut=None),
        step('fetch', handoff_ref=earlier(0, 'handoff_ref'), names=None, cut=None)],
        input_refs=[world['question']])
    launched, checked, early = outcomes(world, 'launching')
    assert launched['status'] == 'completed' and launched['kind'] == 'local'
    assert (launched['adopted'], launched['replayed']) == (False, False)
    assert launched['job'] == job_handle(world['journal'].attempts('launching', path_of('launching'))[0][2],
                                         LOCAL, 'job')
    assert checked['state'] == 'running' and checked['result_available'] is False
    assert checked['assessment'] == {'state_seen': 'running', 'handoff_at': launched['submitted_at']}
    # Results are not asked of a job that has not ended: a failed request is a returned outcome, and no row.
    assert early['status'] == 'failed' and early['failure']['code'] == 'results_not_available'
    assert [job['job'] for job in first['outstanding_jobs']] == [launched['job']]
    job = first['outstanding_jobs'][0]
    assert job['latest_check']['state'] == 'running' and job['estimates']['done_about'] == '16:00'
    assert first['outstanding_job_refs'] == [launched['handoff_ref'], checked['check_ref']]
    assert first['finding'] == {'plan_steps': 3, 'steps_done': 3} and first['credit'] == 3.0
    # The row is a work-table row in custody; its reply is an artifact the unit produced.
    receipts = {item['ref']: item for item in world['journal'].receipts('launching', path_of('launching'))}
    assert receipts[launched['handoff_ref']]['how'] == 'produced' and receipts[launched['reply_ref']]['unit'] == 0
    assert [build['name'] for build in world['journal'].service_builds('launching')] == ['job_access']

    release.touch()          # the job ends while no Episode is open
    handoff_ref = launched['handoff_ref']
    second = run(world, 'extracting', [
        step('wait', handoff_ref=handoff_ref),
        step('check', handoff_ref=handoff_ref, cut=None),
        step('fetch', handoff_ref=handoff_ref, names=None, cut=None),
        step('echo', read=['native_events', 'targets', [earlier(0, 'receipts', 0, 'handle')]])],
        job_refs=first['outstanding_job_refs'])
    waited, finished, fetched, read = outcomes(world, 'extracting')
    assert waited['status'] == 'completed' and waited['result']['reason'] == 'state_changed'
    receipt = json.loads(world['store'].get_artifact(waited['receipts'][0]['receipt_ref']))
    assert receipt['version'] == 'detached_job_receipt_v1' and receipt['returncode'] == 0
    assert waited['record_refs'] == [waited['receipts'][0]['row_ref'], waited['receipts'][0]['receipt_ref']]
    assert finished['state'] == 'finished' and finished['result_available'] is True
    assert fetched['status'] == 'completed' and fetched['outcome'] == 'results_acquired'
    results = {item['name']: item for item in fetched['results']}
    assert sorted(results) == ['answer.txt', 'result.json', 'stderr.log', 'stdout.log']   # the staged input is not one
    assert world['store'].get_artifact(results['answer.txt']['ref']) == b'WHAT IS SIX TIMES SEVEN: 42'
    assert world['store'].get_artifact(results['stdout.log']['ref']) == b'answered\n'
    assert fetched['result_refs'] == [item['ref'] for item in fetched['results']]
    assert read['read'][0]['handle'] == waited['receipts'][0]['handle'] and read['read'][0]['job_ref'] == launched['job']
    assert second['outstanding_jobs'] == []                   # the closure row is held
    held = {item['ref']: item['how'] for item in world['journal'].receipts('extracting', path_of('extracting'))}
    assert held[handoff_ref] == 'entry' and held[fetched['closure_ref']] == 'produced'
    assert set(fetched['result_refs']) <= set(second['record_refs'])


def test_a_unit_cut_after_its_launch_takes_over_its_handoff_and_does_not_launch_again(world):
    log = world['tmp'] / 'ran.log'
    plan = [launch_step(counted_job(log), cut='after'), step('wait', handoff_ref=earlier(0, 'handoff_ref')),
            step('fetch', handoff_ref=earlier(0, 'handoff_ref'), names=['answer.txt'], cut='after')]
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='cut after the effect'):
        run(world, 'cut_after', plan)
    world['switch'].fail = False
    result = again(world, 'cut_after')
    launched, _, fetched = outcomes(world, 'cut_after')
    assert launched['replayed'] is True and launched['adopted'] is False
    assert world['journal'].times_begun('cut_after', path_of('cut_after'), 0) == 2
    assert [item.name for item in (world['tmp'] / 'jobs').iterdir()] == [launched['job']]
    assert log.read_text() == 'ran\n'                          # the job ran once
    assert fetched['replayed'] is False and result['outstanding_jobs'] == []
    # The same cut after a fetch: the rerun takes over the closure row and the result artifact it names.
    world['switch'].fail = True
    with pytest.raises(RuntimeError):
        run(world, 'cut_fetch', [launch_step(counted_job(world['tmp'] / 'other.log')),
                                 step('wait', handoff_ref=earlier(0, 'handoff_ref')),
                                 step('fetch', handoff_ref=earlier(0, 'handoff_ref'), names=['answer.txt'],
                                      cut='after')])
    world['switch'].fail = False
    closed = again(world, 'cut_fetch')
    refetched = outcomes(world, 'cut_fetch')[2]
    assert refetched['replayed'] is True and refetched['results'][0]['name'] == 'answer.txt'
    assert world['store'].get_artifact(refetched['result_refs'][0]) == b'done'
    assert refetched['closure_ref'] in closed['record_refs'] and refetched['result_refs'][0] in closed['record_refs']


def test_a_unit_cut_before_its_handoff_row_committed_finds_the_job_it_submitted(world):
    log = world['tmp'] / 'ran.log'
    plan = [launch_step(counted_job(log), cut='inside'), step('wait', handoff_ref=earlier(0, 'handoff_ref'))]
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='before the handoff row committed'):
        run(world, 'cut_inside', plan)
    assert world['journal'].receipts('cut_inside', path_of('cut_inside')) == []     # nothing is held of the job
    world['switch'].fail = False
    again(world, 'cut_inside')
    launched = outcomes(world, 'cut_inside')[0]
    assert launched['replayed'] is False and launched['adopted'] is True         # the route had the job
    assert [item.name for item in (world['tmp'] / 'jobs').iterdir()] == [launched['job']]
    assert log.read_text() == 'ran\n'


def test_a_job_is_cancelled_and_closed(world):
    never = world['tmp'] / 'never'
    result = run(world, 'cancelling', [
        launch_step(answer_job(never), inputs={'question.txt': world['question']}),
        step('cancel', handoff_ref=earlier(0, 'handoff_ref')),
        step('check', handoff_ref=earlier(0, 'handoff_ref'), cut=None)], input_refs=[world['question']])
    _, cancelled, after = outcomes(world, 'cancelling')
    assert cancelled['status'] == 'completed' and cancelled['outcome'] == 'cancelled'
    assert cancelled['state'] == 'cancelled' and cancelled['results'] == []
    assert after['state'] == 'cancelled' and result['outstanding_jobs'] == []


def test_job_records_are_read_only_in_custody_and_an_unbound_resource_is_refused(world):
    first = run(world, 'owner', [launch_step(counted_job(world['tmp'] / 'ran.log')),
                                 step('wait', handoff_ref=earlier(0, 'handoff_ref'))])
    handoff_ref = first['outstanding_job_refs'][0]
    with pytest.raises(CustodyError, match='record_not_held'):
        run(world, 'stranger', [step('check', handoff_ref=handoff_ref, cut=None)])     # the row was not passed
    with pytest.raises(LookupError, match='job_resource_not_bound:nowhere'):
        run(world, 'nowhere', [launch_step(counted_job(world['tmp'] / 'x.log'), resource_id='nowhere')])
    with pytest.raises(CustodyError):                          # an input the Episode does not hold is not staged
        run(world, 'unheld_input', [launch_step(counted_job(world['tmp'] / 'y.log'),
                                                inputs={'question.txt': world['question']})])
    with pytest.raises(TypeError, match='job_access_route_lacks:r:'):
        JobAccess({'r': object()})


# -- a command a unit waits for; the remote route through its transport ----------------------------------------
def test_a_waited_command_runs_once_on_the_local_and_on_the_remote_route(world):
    script = 'echo "hello $GREETING"; cat question.txt > copy.txt; echo counted >> ' + str(world['tmp'] / 'remote.log')
    run(world, 'commands', [
        step('command', resource_id=LOCAL, job=counted_job(world['tmp'] / 'local.log'), inputs={}),
        step('command', resource_id=REMOTE, inputs={'question.txt': world['question']},
             job={'mode': 'login', 'script': script, 'arguments': [], 'env': {'GREETING': 'there'}}),
        step('launch', resource_id=REMOTE, inputs={}, estimates=None, cut=None,
             job={'mode': 'batch', 'script': '#!/bin/sh\ntrue\n', 'arguments': ['-l', 'select=1'], 'env': {}}),
        step('echo', read=['job_access', 'resources']), step('echo', read=['job_access', 'describe', REMOTE])],
        input_refs=[world['question']])
    local, remote, batch, resources, described = outcomes(world, 'commands')
    assert local['status'] == 'completed' and local['fetch']['state'] == 'finished'
    assert (world['tmp'] / 'local.log').read_text() == 'ran\n'
    assert remote['status'] == 'completed' and remote['launch']['kind'] == 'pbs'
    files = {item['name']: world['store'].get_artifact(item['ref']) for item in remote['fetch']['results']}
    assert files == {'copy.txt': b'what is six times seven', 'stdout.log': b'hello there\n', 'stderr.log': b''}
    assert (world['tmp'] / 'remote.log').read_text() == 'counted\n'
    # No PBS scheduler is installed here: the submission reaches the scheduler call and the request fails.
    assert batch['status'] == 'failed' and batch['failure'] == {
        'code': 'scheduler_command_unavailable', 'detail': {'command': 'qsub'}}
    assert resources['read'] == [{'resource_id': LOCAL, 'kind': 'local'}, {'resource_id': REMOTE, 'kind': 'pbs'}]
    assert described['read']['modes'] == ['batch', 'login'] and described['read']['scheduler'] == 'pbs'


def test_the_remote_route_submits_a_handle_once_and_reports_cancels_and_reads_its_job(tmp_path):
    configuration = {'ssh_argv': ['/bin/sh', '-c'], 'python_executable': sys.executable,
                     'workspace': str(tmp_path / 'remote'), 'scheduler': SCHEDULER, 'poll_seconds': 0.05}
    route = PbsSshRoute(configuration, resource_id=REMOTE)
    release = tmp_path / 'release'
    job = {'mode': 'login', 'arguments': [], 'env': {},
           'script': 'echo started; while [ ! -e ' + str(release) + ' ]; do sleep 0.05; done; echo ended; exit 3'}
    first = route.submit('job_aaaaaaaaaaaaaaaa', job, {'in/data.txt': b'staged'}, {'run_id': 'r', 'episode_id': 'e'})
    second = route.submit('job_aaaaaaaaaaaaaaaa', job, {'in/data.txt': b'staged'}, {'run_id': 'r', 'episode_id': 'e'})
    assert (first['adopted'], second['adopted']) == (False, True) and second['native'] == first['native']
    assert second['submitted_at'] == first['submitted_at']
    assert route.status('job_aaaaaaaaaaaaaaaa', first['native'])['state'] == 'running'
    with pytest.raises(RouteRequestError, match='results_not_available'):
        route.results('job_aaaaaaaaaaaaaaaa', first['native'])
    release.touch()
    asyncio.run(route.wait('job_aaaaaaaaaaaaaaaa', first['native']))
    status = route.status('job_aaaaaaaaaaaaaaaa', first['native'])
    assert status['state'] == 'failed' and status['reply']['native']['returncode'] == 3
    names = [item['name'] for item in route.results('job_aaaaaaaaaaaaaaaa', first['native'])]
    assert names == ['stderr.log', 'stdout.log']
    assert route.read('job_aaaaaaaaaaaaaaaa', first['native'], 'stdout.log', 8, 100) == b'ended\n'
    with pytest.raises(RouteRequestError, match='file_name_outside_the_job_directory'):
        route.read('job_aaaaaaaaaaaaaaaa', first['native'], '../release', 0, 10)
    # A job that is cancelled while it runs.
    other = route.submit('job_bbbbbbbbbbbbbbbb', {**job, 'script': 'sleep 600'}, {}, {'run_id': 'r', 'episode_id': 'e'})
    route.cancel('job_bbbbbbbbbbbbbbbb', other['native'])
    asyncio.run(route.wait('job_bbbbbbbbbbbbbbbb', other['native']))
    assert route.status('job_bbbbbbbbbbbbbbbb', other['native'])['state'] == 'cancelled'
    # A submission that began and left neither a record nor a process is not repeated on a guess.
    (tmp_path / 'remote' / 'job_cccccccccccccccc').mkdir()
    (tmp_path / 'remote' / 'job_cccccccccccccccc' / 'submitting').touch()
    with pytest.raises(RouteRequestError, match='submission_outcome_unknown'):
        route.submit('job_cccccccccccccccc', job, {}, {'run_id': 'r', 'episode_id': 'e'})
    with pytest.raises(RouteRequestError, match='job_not_found'):
        route.status('job_dddddddddddddddd', {})
    broken = PbsSshRoute({**configuration, 'ssh_argv': [str(tmp_path / 'no_such_transport')]}, resource_id=REMOTE)
    with pytest.raises(RouteRequestError, match='transport_unavailable'):
        broken.status('job_aaaaaaaaaaaaaaaa', {})
    with pytest.raises(ValueError, match='pbs_route_configuration_requires_exactly'):
        PbsSshRoute({'ssh_argv': ['ssh']}, resource_id=REMOTE)


# -- native events ---------------------------------------------------------------------------------------------
def test_a_wait_returns_at_its_reconsideration_time_and_an_unknown_target_is_a_failed_outcome(world):
    soon = (datetime.now(timezone.utc) + timedelta(seconds=0.3)).isoformat()
    unknown = {'version': 'event_condition_v1', 'reconsider_at': None, 'events': [
        {'handle': 'native_event_target_' + '0' * 24, 'event': 'state_changed', 'after_cursor': 0}]}
    result = run(world, 'waits', [
        step('wait_condition', condition={'version': 'event_condition_v1', 'events': [], 'reconsider_at': soon}),
        step('wait_condition', condition=unknown)])
    reconsidered, refused = outcomes(world, 'waits')
    assert reconsidered['status'] == 'completed' and reconsidered['result']['reason'] == 'reconsideration'
    assert reconsidered['receipts'] == [] and reconsidered['record_refs'] == []
    assert refused['status'] == 'failed' and refused['feedback']['code'] == 'unknown_wait_target'
    assert result['record_refs'] == []
    assert NATIVE_EVENT_RECEIPTS.key == ('handle', 'record_ref')


# -- the estimate table ----------------------------------------------------------------------------------------
EXPECTATION = {'gain': {'value': 2.0, 'lower': 1.0, 'upper': 4.0}, 'cost': 0.5,
               'prediction': {'outcomes': [{'label': 'hit', 'probability': 0.5}]}}


def test_expectations_are_recorded_before_an_action_and_a_decision_reads_the_recorded_statistics(world):
    kind = 'A102 planned HPC job'
    plan = [step('expect', kind=kind, expectation=EXPECTATION, key='action_one'),
            launch_step(counted_job(world['tmp'] / 'ran.log'), cut='after',
                        read=['estimate_table', 'kind_statistics', kind]),
            step('resolve', key='action_one', actual={'gain': 3.0, 'cost': 0.75, 'outcome': 'results_acquired',
                                                      'duration_seconds': 120.0}),
            step('echo', read=['estimate_table', 'kind_statistics', kind])]
    world['switch'].fail = True
    with pytest.raises(RuntimeError):
        run(world, 'estimates', plan)
    table = EstimateTable(world['configuration']['estimate_table_path'])       # the same durable file
    assert table.expectation('action_one')['actual'] is None and table.kinds() == [kind]
    # The table changes before the interrupted unit is decided again.
    table.expect(kind, EXPECTATION, key='another_action', at='2026-11-19T10:00:00+00:00')
    world['switch'].fail = False
    again(world, 'estimates')
    reads = world['journal'].service_reads('estimates', path_of('estimates'))
    assert [item['position'] for item in reads] == [1, 3]
    # The decision of unit 1 was made again on what it first read (one open action), not on the changed table.
    assert reads[0]['value'] == {'kind': kind, 'resolved': 0, 'open': 1, 'gain': None, 'cost': None,
                                 'duration_seconds': None, 'expected_gain': 0.0, 'obtained_gain': 0.0,
                                 'correction': None}
    expected, _, resolved, after = outcomes(world, 'estimates')
    assert expected['expected'] == EXPECTATION and expected['actual'] is None
    assert resolved['actual']['gain'] == 3.0 and resolved['resolved_at'] > resolved['expected_at']
    assert after['read'] == {'kind': kind, 'resolved': 1, 'open': 1,
                             'gain': {'low': 3.0, 'typical': 3.0, 'high': 3.0},
                             'cost': {'low': 0.75, 'typical': 0.75, 'high': 0.75},
                             'duration_seconds': {'low': 120.0, 'typical': 120.0, 'high': 120.0},
                             'expected_gain': 2.0, 'obtained_gain': 3.0, 'correction': 1.5}


def test_the_estimate_table_writes_a_key_once_and_keeps_observations_and_measurements(world, tmp_path):
    table = EstimateTable(tmp_path / 'direct.sqlite3')
    first = table.expect('kind', EXPECTATION, key='k', at='2026-11-19T10:00:00+00:00')
    assert table.expect('kind', EXPECTATION, key='k', at='2026-11-19T11:00:00+00:00') == first   # the first time stands
    with pytest.raises(EstimateTableError, match='identity_conflict:expectation:k'):
        table.expect('kind', {**EXPECTATION, 'cost': 9.0}, key='k', at='2026-11-19T10:00:00+00:00')
    with pytest.raises(EstimateTableError, match='no_expectation_recorded_before_the_action'):
        table.resolve('unknown', {'gain': 1.0, 'cost': 1.0, 'outcome': 'x'}, at='2026-11-19T10:00:00+00:00')
    with pytest.raises(EstimateTableError, match='expected_gain_band_must_be_ordered'):
        table.expect('kind', {'gain': {'value': 5.0, 'lower': 1.0, 'upper': 4.0}, 'cost': 1.0}, key='bad', at='t')
    actual = {'gain': 1.0, 'cost': 0.25, 'outcome': 'failed'}
    done = table.resolve('k', actual, at='2026-11-19T12:00:00+00:00')
    assert table.resolve('k', actual, at='2026-11-19T13:00:00+00:00') == done
    with pytest.raises(EstimateTableError, match='identity_conflict:actual:k'):
        table.resolve('k', {**actual, 'gain': 2.0}, at='2026-11-19T12:00:00+00:00')
    for index, gain in enumerate((0.0, 2.0, 4.0, 6.0)):
        table.expect('spread', EXPECTATION, key='s' + str(index), at='2026-11-19T10:0' + str(index) + ':00+00:00')
        table.resolve('s' + str(index), {'gain': gain, 'cost': 1.0, 'outcome': 'ok'}, at='2026-11-19T12:00:00+00:00')
    spread = EstimateTable(tmp_path / 'direct.sqlite3').kind_statistics('spread')   # another object, the same file
    assert spread['gain'] == pytest.approx({'low': 0.6, 'typical': 3.0, 'high': 5.4})
    assert spread['correction'] == 1.5 and [row['key'] for row in table.rows('spread', 2)] == ['s3', 's2']
    # Observations and measurements, written by a tool unit of a real run.
    profile = {'resource_id': REMOTE, 'backend': 'hpc', 'tool': 'foldseek', 'implementation': 'v9',
               'parameters': 'default', 'hardware': 'gpu'}
    observation = {'observed_at': 1000.0, 'features': {'residues': 300, 'nodes': None}, 'success': True,
                   'provenance': ['job 1'], 'metrics': {'work': {'seconds': 60.0, 'censored': False},
                                                         'queue': {'seconds': 30.0, 'censored': True},
                                                         'memory_bytes': {'value': 2e9, 'unit': 'bytes',
                                                                          'censored': False}}}
    run(world, 'measuring', [step('measure', resource=REMOTE, queue={'queued': 7}, at=1000.0, attempt_id='attempt_1',
                                  profile=profile, observation=observation)])
    measured = outcomes(world, 'measuring')[0]
    assert measured['latest']['state'] == 'fresh' and measured['latest']['data'] == {'queued': 7}
    assert measured['history'][0]['id'] == 'shared:attempt_1' and measured['history'][0]['metrics']['work'][
        'weight'] == pytest.approx(2 ** (-1 / (14 * 86400)))
    shared = EstimateTable(world['configuration']['estimate_table_path'])
    assert shared.latest(REMOTE, 'queue', 1000.0 + 121)['state'] == 'stale'
    assert shared.latest(REMOTE, 'queue', 1000.0 + 121)['data'] is None
    assert shared.latest(LOCAL, 'queue', 2000.0) == {'resource_id': LOCAL, 'kind': 'queue', 'state': 'unknown',
                                                     'data': None}
    assert [row['metrics'].keys() for row in shared.history(profile, 1001.0, True)] == [{'queue'}]
    assert shared.profiles(None, 1001.0) == [{'profile': profile, 'latest_observed_at': 1000.0, 'attempt_count': 1}]
    shared.record(attempt_id='attempt_1', profile=profile, observation=observation)       # the same again
    with pytest.raises(EstimateTableError, match='identity_conflict:attempt:attempt_1'):
        shared.record(attempt_id='attempt_1', profile=profile, observation={**observation, 'success': False})
    with pytest.raises(EstimateTableError, match='resource_measurement_unit_conflict'):
        shared.record(attempt_id='attempt_2', profile=profile, observation={**observation, 'metrics': {
            'memory_bytes': {'value': 1.0, 'unit': 'kb', 'censored': False}}})
    assert shared.policy()['queue_seconds'] == 120 and shared.as_record()['path'].endswith('table.sqlite3')


def test_the_action_value_calculation():
    prediction = {'current_support': [0.5, 0.5], 'outcomes': [
        {'label': 'a', 'probability': 0.5, 'support_after': [1.0, 0.0]},
        {'label': 'b', 'probability': 0.5, 'support_after': [0.0, 1.0]}]}
    assert action_value.discrimination(prediction) == pytest.approx(1.0)
    flat = {'current_support': [0.5, 0.5], 'outcomes': [{'label': 'n', 'probability': 1.0, 'support_after': [0.5, 0.5]}]}
    assert action_value.discrimination(flat) == pytest.approx(0.0)
    partial = {'current_support': [0.5, 0.5], 'outcomes': [
        {'label': 'a', 'probability': 0.5, 'support_after': [0.9, 0.1]},
        {'label': 'n', 'probability': 0.5, 'support_after': [0.5, 0.5]}]}
    after = 0.5 * action_value.entropy([0.9, 0.1]) + 0.5 * math.log(2)
    assert action_value.discrimination(partial) == pytest.approx((math.log(2) - after) / math.log(2))
    assert action_value.definitive_outcomes(partial, 0.9) == ['a']
    assert action_value.discrimination({'current_support': [1.0, 0.0], 'outcomes': flat['outcomes'][:0] + [
        {'label': 'n', 'probability': 1.0, 'support_after': [1.0, 0.0]}]}) == 0.0
    with pytest.raises(ValueError, match='summing_to_one'):
        action_value.entropy([0.5, 0.6])
    gain = action_value.expected_gain({'low': 1.0, 'typical': 2.0, 'high': 6.0}, 0.5, 1.5)
    assert gain == {'value': 1.5, 'lower': 0.75, 'upper': 4.5}
    job = {'name': 'launch', 'expected_gain': gain, 'cost': 2.0}
    lookup = {'name': 'lookup', 'expected_gain': {'value': 4.2, 'lower': 4.0, 'upper': 4.4}, 'cost': 0.5}
    weak = {'name': 'weak', 'expected_gain': {'value': 1.0, 'lower': 0.5, 'upper': 1.5}, 'cost': 0.5}
    assert action_value.refusal(job, [job, weak], 0.1) is None
    assert action_value.refusal(job, [job, weak, lookup], 0.1)['preferred'] == 'lookup'
    assert action_value.refusal({**job, 'cost': 4.45}, [], 0.1)['reason'] == 'not_worth_its_cost'


# -- the HPC ledger as a work table ----------------------------------------------------------------------------
def test_the_hpc_ledger_is_shared_in_custody_and_its_credit_is_derived_from_held_evidence(world):
    commission = {'credit': {'model_scale': 2.0, 'validation_scale': 1.0, 'validation_slots': [
        {'id': 'slot_work', 'metric': 'work', 'weight': 1.5}]}, 'obligations': {'structures': {'credit': 3.0}}}
    predicted = {'mu': math.log1p(60), 'sigma': 0.5, 'elapsed': 0}
    reference = {'mu': math.log1p(600), 'sigma': 1.0, 'elapsed': 0}
    forecast = {'plan_id': 'plan_1', 'issued_at': 100.0, 'elapsed': {}, 'prediction': {'times': {'work': predicted}},
                'reference': {'times': {'work': reference}}}
    first = run(world, 'predicting', [
        step('ledger_forecast', commission=commission, forecast=forecast, slots=['slot_work']),
        step('ledger_forecast', commission=commission, forecast={**forecast, 'issued_at': 150.0},
             slots=['slot_work'])])
    frozen, later = outcomes(world, 'predicting')
    assert frozen['ledger'] == ledger_id(commission) and later['reserved'] == {'slot_work': frozen['forecast']}
    assert len(first['record_refs']) == 3                     # the commission and two forecasts, returned in custody
    measured = {'plan_id': 'plan_1', 'metrics': {'work': {'seconds': 62.0, 'censored': False, 'observed_at': 200.0}}}
    second = run(world, 'allocating', [
        step('ledger_score', ledger=frozen['ledger'], measured=measured, obligation='structures',
             result_ref='result_1', model_ref='model_1', improvement=0.25),
        step('ledger_conflict', ledger=frozen['ledger'])], job_refs=first['record_refs'])
    scored, conflict = outcomes(world, 'allocating')
    gain = 1.5 * (log_score(predicted, 62.0) - log_score(reference, 62.0))
    view = scored['credit_view']
    assert view['components'] == pytest.approx({'actual': 3.0, 'model': 0.5, 'validation': gain})
    assert view['credit'] == pytest.approx(3.5 + gain)
    assert [row['slot'] for row in view['contributions']] == ['actual:structures', 'model', 'validation:slot_work']
    assert scored['kinds'] == {'forecast': 2, 'measured': 1, 'score': 1, 'accept': 1}
    assert conflict['refused'] == 'immutable_hpc_evidence_conflict:note_one' and conflict['again'] == 'note_one'
    rows = world['store']._db.execute('SELECT COUNT(*) FROM episode_work_rows WHERE table_name=?',
                                     (HPC_LEDGER.name,)).fetchone()[0]
    assert rows == 3 + 5                                       # each Episode's own rows, in the Store's work rows
    assert len(second['record_refs']) == 5 and set(second['record_refs']) <= set(scored['refs']) | {
        ref for ref in second['record_refs'] if ref not in scored['refs']}
    assert set(first['record_refs']) <= set(scored['refs'])    # the rows it was handed are part of its ledger
    with pytest.raises(ValueError, match='original_hpc_commission_missing'):
        run(world, 'without_rows', [step('ledger_score', ledger=frozen['ledger'], measured=measured,
                                         obligation='structures', result_ref='r', model_ref='m', improvement=0.1)])


# -- resource adapters -----------------------------------------------------------------------------------------
def test_an_episode_works_through_the_adapter_its_assignment_selects(world):
    assignment = {'resource_selection': {'resource_id': LOCAL}, 'objective': 'answer'}
    job = python_job("import pathlib\npathlib.Path('answer.txt').write_text('via the adapter')")
    result = run(world, 'adapting', [
        step('echo', read=['resource_adapter', 'declared_capabilities']),
        step('echo', read=['resource_adapter', 'catalog', assignment]),
        step('echo', read=['resource_adapter', 'is_bound', UNBOUND]),
        step('adapter_prepare', assignment=assignment),
        step('adapter_execute', assignment=assignment, tool='job.launch',
             arguments={'job': job, 'inputs': {}, 'estimates': None}),
        step('wait', handoff_ref=earlier(4, 'handoff_ref')),
        step('adapter_check', handoff={'resource_selection': {'resource_id': LOCAL},
                                       'handoff_ref': earlier(4, 'handoff_ref')}),
        step('adapter_execute', assignment=assignment, tool='job.fetch',
             arguments={'handoff_ref': earlier(4, 'handoff_ref'), 'names': ['answer.txt']})])
    declared, catalog, bound, prepared, launched, _, checked, fetched = outcomes(world, 'adapting')
    assert [item['resource_id'] for item in declared['read']] == [LOCAL, REMOTE, UNBOUND]
    assert [entry['name'] for entry in catalog['read']] == ['job.launch', 'job.check', 'job.fetch', 'job.cancel']
    assert bound['read'] is False and prepared['resource']['kind'] == 'local'
    assert launched['status'] == 'completed' and checked['state'] == 'finished'
    assert world['store'].get_artifact(fetched['result_refs'][0]) == b'via the adapter'
    assert result['outstanding_jobs'] == []
    assert [build['name'] for build in world['journal'].service_builds('adapting')] == ['resource_adapter',
                                                                                        'native_events']
    adapters = world['services']['resource_adapter']()
    assert adapters.bound_resource_ids() == [LOCAL, REMOTE] and adapters is world['services']['resources']()
    assert adapters.adapter_capabilities()[REMOTE]['kind'] == 'hpc'
    assert adapters.facts(assignment)['resource']['resource_id'] == LOCAL
    assert adapters.decision_context(assignment)['capability']['resource_id'] == LOCAL
    with pytest.raises(LookupError, match='resource_not_bound:elsewhere'):
        run(world, 'unbound', [step('adapter_prepare', assignment={'resource_selection': {'resource_id': UNBOUND}})])
    with pytest.raises(LookupError, match='resource_tool_not_in_the_adapters_catalog:job.destroy'):
        run(world, 'no_tool', [step('adapter_execute', assignment=assignment, tool='job.destroy', arguments={})])
    with pytest.raises(ValueError, match='bound_resource_is_not_declared:x'):
        ResourceAdapters([capability(LOCAL, 'local')], {'x': adapters._selected(assignment)})
    with pytest.raises(TypeError, match='resource_adapter_lacks'):
        ResourceAdapters([capability(LOCAL, 'local')], {LOCAL: object()})


# -- instruction libraries -------------------------------------------------------------------------------------
def test_the_frozen_instruction_libraries_are_read_by_decisions_and_looked_up_by_tools(world):
    run(world, 'instructions', [
        step('echo', read=['instruction_libraries', 'context']),
        step('echo', read=['instruction_libraries', 'for_resource', {'launch_prompt_entry': 'launch-aurora'}]),
        step('lookup', name='launch.instructions.search', arguments={'query': 'aurora', 'offset': 0, 'limit': 5}),
        step('lookup', name='knowledge.search', arguments={'query': '', 'offset': 0, 'limit': 2}),
        step('echo', read=['instruction_libraries', 'catalog'])])
    context, resource, launch, knowledge, catalog = outcomes(world, 'instructions')
    assert context['read']['launch_instruction_library']['library_id'].startswith('launch_instructions_')
    assert context['read']['tool_knowledge']['library_id'].startswith('tool_knowledge_')
    assert resource['read']['sections'] and all(section['text'] for section in resource['read']['sections'])
    assert launch['status'] == 'completed' and launch['result']['total'] >= 1
    assert knowledge['status'] == 'completed' and len(knowledge['result']['entries']) == 2
    names = [entry['name'] for entry in catalog['read']]
    assert 'knowledge.search' in names and 'launch.instructions.read' in names
    reads = world['journal'].service_reads('instructions', path_of('instructions'))
    assert [item['request']['member'] for item in reads] == ['context', 'for_resource', 'catalog']
    libraries = InstructionLibraries(world['configuration']['launch_instructions_directory'],
                                     world['configuration']['tool_knowledge_directory'])
    assert libraries.for_resource({}) is None
    with pytest.raises(LookupError, match='instruction_library_operation_unknown:nothing'):
        libraries.execute('nothing', {})


def test_the_services_configuration_names_every_part(world):
    with pytest.raises(ValueError, match='job_services_configuration_requires_exactly'):
        job_services({'local': {}})
    assert sorted(job_services(world['configuration'])) == ['estimate_table', 'instruction_libraries', 'job_access',
                                                            'native_events', 'resource_adapter', 'resources']
    assert JOB_LEDGER.record_refs == ('source_ref', 'result_refs')
