"""The A101 monitor on a job of the public NCBI BLAST service that a run of the A101 ``api_job_execution`` branch
test launched and left outstanding (``execution_job_submission/api_job_execution/tests/
test_branch_api_job_execution_model_run.py``; it prints its ``WORLD_DIRECTORY``).

``A101_API_BRANCH_DIRECTORY`` names that world directory. It is only read: the test copies it (the Store with the
job's handoff row, the journal, the route's workspace ``api_jobs`` with the recorded submission and the rate state)
into its own directory and binds the API route to the copied workspace, so what its checks write is its own. The
copied rate state holds the time of the last status request, so the provider's spacing (ten seconds between
contacts, sixty between status requests of one job) is kept from the first check on. Nothing is submitted: the
monitor has no action that submits, and the copied ``submission.json`` is the route's answer for the job's handle.

- ``test_the_request_for_the_outstanding_job`` (no model, no contact with the service): the request the model
  will read for this job, printed.
- ``test_the_monitor_checks_the_outstanding_job_with_the_real_model`` (``-m model_run``, real network): three
  visits of the monitor, as a head commissions them one after another while the job is outstanding. Each visit is
  one monitor Episode that runs by its own decisions with the real model; it is passed the job's handoff row and
  the check rows of the visits before it. Before a visit the caller waits until the route's rate state permits a
  status request. The visits end early when a check shows that the job has ended. Each check's provider status is
  printed with its time (``PROVIDER_STATUS``), and the timeline of all of them at the end.

A service that cannot be reached, or a job that is still waiting after the three visits, is a result the test
prints; it is not hidden and it does not fail the test."""
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import time

import pytest

from episode_runtime import RunJournal
from episode_runtime.work_tables import WorkRows
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.jobs.api_job_route import ApiJobRoute, PROTOCOLS
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import JOB_STATES
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services

from ...execution_job_submission.api_job_execution.tests import api_world
from ..messages import final_to_parent
from .test_branch_execution_progress_assessment_model_run import SELECTABLE, Switch, monitor, path_of

LAUNCH_WORLD = 'A101_API_BRANCH_DIRECTORY'
LAUNCH_RUN = 'a101-api-ncbi-blast'              # the run id of the launch test
VISITS = ('visit-1', 'visit-2', 'visit-3')


def say(*values):
    print(*values, flush=True)


def files_of(directory):
    """Every file below ``directory`` with its bytes: what a contact or a submission would change."""
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in sorted(directory.rglob('*')) if path.is_file()}


@pytest.fixture(scope='module')
def outstanding(tmp_path_factory):
    if LAUNCH_WORLD not in os.environ:
        pytest.skip(LAUNCH_WORLD + ' must name the world directory of an API launch run with an outstanding job')
    source = Path(os.environ[LAUNCH_WORLD])
    before = files_of(source / 'api_jobs')
    directory = tmp_path_factory.mktemp('api_monitor') / 'world'
    shutil.copytree(source, directory, ignore=shutil.ignore_patterns('model_calls*'))
    assert files_of(source / 'api_jobs') == before == files_of(directory / 'api_jobs')
    say('LAUNCH_WORLD', source, 'COPIED_TO', directory)
    route = api_world.ncbi_route(directory / 'api_jobs')
    configuration = {
        'local': {}, 'pbs': {}, 'api': {api_world.RESOURCE: route},
        'capabilities': [{'resource_id': api_world.RESOURCE, 'kind': 'api', 'availability': 'unknown',
                          'observed_at': 'caller_configuration', 'provenance_refs': [], 'knowledge_entry_ids': [],
                          'tool_names': ['job.launch', 'job.check', 'job.fetch']}],
        'event_ledger_directory': str(directory / 'events'),
        'estimate_table_path': str(directory / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(directory / 'launch'),
        'tool_knowledge_directory': str(directory / 'knowledge')}
    switch = Switch()
    store, journal = Store(directory / 'store'), RunJournal(directory / 'journal.sqlite3')
    submitted = [unit[2]['outcome'] for unit in journal.units(LAUNCH_RUN, api_world.path_of(LAUNCH_RUN))
                 if unit[2]['tool'] == 'submit' and unit[2]['outcome']['handoff_refs']]
    handoff_ref, = submitted[-1]['handoff_refs']
    handoff = WorkRows(store).row(handoff_ref)
    yield {'store': store, 'journal': journal, 'configuration': configuration, 'tmp': directory,
           'services': {**job_services(configuration), 'switch': lambda: switch},
           'provider': ModelProvider(load_config(), directory / 'model_calls_monitor', directory),
           'source': source, 'source_before': before, 'handoff_ref': handoff_ref, 'handoff': handoff,
           'route': ApiJobRoute(route, resource_id=api_world.RESOURCE),
           'job_directory': directory / 'api_jobs' / handoff['job']}
    store.close()


def show(request):
    say('\n=== INSTRUCTIONS ===\n' + request.instructions)
    say('=== CONTEXT ===\n' + json.dumps(request.context, indent=1))
    say('=== OUTPUT SCHEMA ===\n' + json.dumps(request.output_schema))


def offered(request):
    return [line.split(':')[0][2:] for line in request.instructions.splitlines() if line.startswith('- ')]


def recorded_submission(held):
    """The route's record of the job's one submission in the copied workspace: the intent and the answer."""
    directory = held['job_directory']
    return {name: (directory / name).read_bytes() for name in ('submitting', 'submission.json', 'submit.response',
                                                              'request.json')}


def test_the_request_for_the_outstanding_job(outstanding):
    held = outstanding
    native = held['handoff']['detail']['native']
    say('HANDOFF', json.dumps({'job': held['handoff']['job'], 'submitted_at': held['handoff']['at'],
                               'kind': held['handoff']['detail']['kind'], 'native': native}))
    say('RECORDED_STATUS', (held['job_directory'] / 'status.json').read_text())
    assert held['handoff']['detail']['kind'] == 'api' and native['service'] == 'ncbi_blast'
    # The handoff recorded the launch run's directory; the route serves the job from the copied workspace.
    assert native['directory'] == str(held['source'] / 'api_jobs' / held['handoff']['job'])
    assert json.loads(recorded_submission(held)['submission.json'])['remote_id'] == native['remote_id']
    request = asyncio.run(monitor(held, held['handoff_ref'], 'request-only', blast=True).next_decision())
    show(request)
    assert offered(request) == ['progress_observe']
    assert request.context['job']['resource_kind'] == 'api'
    assert request.context['job']['seconds_between_status_requests'] == 60
    # Reading the request asked nothing of the service: the route's workspace is as it was copied.
    assert files_of(held['tmp'] / 'api_jobs') == held['source_before']


def provider_checks(held, refs):
    """What each check row shows of the provider, with the route's reply kept as the row's artifact."""
    shown = []
    for ref in refs:
        row = WorkRows(held['store']).row(ref)
        reply = json.loads(held['store'].get_artifact(row['source_ref']))
        shown.append({'check_ref': ref, 'observed_at': row['at'], 'state': row['detail']['state'],
                      'result_available': row['detail']['result_available'],
                      'provider_status': row['detail']['assessment']['provider_status'],
                      'has_hits': row['detail']['assessment']['has_hits'],
                      'http_status': reply['http_status'], 'information': reply['information'],
                      'from_record': reply['from_record']})
    return shown


@pytest.mark.model_run
def test_the_monitor_checks_the_outstanding_job_with_the_real_model(outstanding):
    held = outstanding
    journal, handoff_ref = held['journal'], held['handoff_ref']
    remote_id = held['handoff']['detail']['native']['remote_id']
    submission = recorded_submission(held)
    recorded = json.loads((held['job_directory'] / 'status.json').read_text())
    say('JOB', remote_id, 'SUBMITTED_AT', held['handoff']['at'], 'LAST_RECORDED_STATUS', json.dumps(
        {'observed_at': recorded['observed_at'], 'provider_status': recorded['reply']['provider_status']}))
    timeline, known = [], []
    for visit in VISITS:
        wait = held['route'].spacing('status', remote_id)
        say('VISIT', visit, 'AT', datetime.now().astimezone().isoformat(), 'SECONDS_UNTIL_A_STATUS_REQUEST_MAY_BE_SENT',
            round(wait, 1))
        time.sleep(wait)                                       # the provider's spacing, from the route's rate state
        linked = monitor(held, handoff_ref, visit, blast=True, known=known)
        request = asyncio.run(linked.next_decision())
        show(request)
        assert 'progress_log' not in offered(request) and 'progress_wait' not in offered(request)
        result = asyncio.run(linked.run())['result'].as_record()
        units = [unit[2] for unit in journal.units(visit, path_of(visit))]
        answers = {call['position']: call['response'] for call in journal.model_calls(visit, path_of(visit))}
        for position, unit in enumerate(units):
            outcome = unit['outcome']
            say('UNIT', visit, unit['tool'], 'MODEL_ANSWER', json.dumps(answers[position]), '->', json.dumps(
                {name: outcome[name] for name in ('status', 'state', 'result_available', 'observed_at',
                                                  'assessment', 'informative', 'failure', 'check_ref')
                 if name in outcome}))
        say('ENDED_BY', journal.run_state(visit)[1]['ended_by'], 'RESULT', json.dumps(result))
        assert journal.run_state(visit)[1]['ended_by'] == 'yield_stop'
        assert final_to_parent.RETURN_FORM.select(SELECTABLE).admit(result, 'return') == result
        assert {unit['tool'] for unit in units} <= {'progress_observe', 'progress_read'}
        checks = provider_checks(held, result['check_refs'])
        for check in checks:
            say('PROVIDER_STATUS', visit, json.dumps(check))
            assert check['state'] in JOB_STATES
            assert check['provider_status'] in PROTOCOLS['ncbi_blast'].STATES
        timeline += [{'visit': visit, **check} for check in checks]
        refused = [unit['outcome']['failure'] for unit in units if unit['outcome']['status'] == 'failed']
        for failure in refused:
            say('REQUEST_NOT_ANSWERED', visit, json.dumps(failure))
        timeline += [{'visit': visit, 'failure_code': failure['code'],
                      'sent': failure['detail'].get('sent', True)} for failure in refused]
        known += result['check_refs']
        if result['finding']['observed'] and result['finding']['state'] != 'queued':
            break
    say('TIMELINE', json.dumps(timeline, indent=1))
    # The provider was asked for status no faster than its spacing: the checks it answered, after the last one
    # the launch run's workspace recorded.
    asked = [recorded['observed_at'], *(item['observed_at'] for item in timeline
                                        if 'observed_at' in item and not item['from_record'])]
    gaps = [(datetime.fromisoformat(later) - datetime.fromisoformat(earlier)).total_seconds()
            for earlier, later in zip(asked, asked[1:])]
    say('SECONDS_BETWEEN_STATUS_REQUESTS', json.dumps([round(gap, 1) for gap in gaps]))
    assert all(gap >= held['configuration']['api'][api_world.RESOURCE]['poll_spacing_seconds'] for gap in gaps)
    # Nothing was submitted: the route's record of the one submission is as it was copied and the workspace holds
    # that one job. The route wrote only below the copy; whether the launch run's own workspace is as it was when
    # it was copied is printed (another process may use it).
    assert recorded_submission(held) == submission
    assert [path.name for path in (held['tmp'] / 'api_jobs').iterdir() if path.is_dir()] == [held['handoff']['job']]
    say('LAUNCH_WORKSPACE_AS_COPIED', files_of(held['source'] / 'api_jobs') == held['source_before'])
    say('FINAL_STATUS', (held['job_directory'] / 'status.json').read_text())
    say('WORLD_DIRECTORY', held['tmp'])
