"""Branch run of the A101 ``api_job_execution`` episode alone, on the public, unauthenticated NCBI BLAST service.

World (``api_world.py``): real Store with the protein query, RunJournal, the job services of ``job_services`` with the
API route bound to ``https://blast.ncbi.nlm.nih.gov/Blast.cgi`` (no contact address, no credential, the service's
documented spacing), the episode's own settings, the real ``ModelProvider``. The assignment is the one a launching
parent passes: the query in custody, the database fixed (``swissprot``: small), the program and the hit-list size
left to the episode. Real network. Selected only with ``-m model_run``.

Two tests, in order, on one world:

1. the launch: the model builds the request, the service takes it, the handoff row is in custody, and resume
   replays the run (the model is not asked, the service is not contacted, nothing is submitted a second time);
2. the job, as the route defines: the route's own wait (status requests at the provider's spacing, without a
   deadline), then one check and the fetch through ``JobAccess`` in an Episode that was handed the handoff row
   (the ``job_probe`` test episode of the job services).

A service that does not take the submission, or that ends the search without a result, is a result: the test
reports it and is skipped with the recorded failure, after the controlled return was admitted. A queue can be
long. The world's directory is durable: with ``A101_API_BRANCH_DIRECTORY`` naming the directory of an earlier
process of this file (it is printed), the recorded run is resumed there instead of a new one being linked, so the
job that process left outstanding is waited for and fetched without a second submission."""
import asyncio
import json
import os
from pathlib import Path

import pytest

from episode_runtime import BindingRegistry, link
from episode_runtime.work_tables import WorkRows
from gene_annotation_episode.episodic_workflow.episode_support.jobs.api_job_route import ApiJobRoute
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.jobs.tests.job_probe.episode import JobProbe

from . import api_world
from ..messages.final_to_parent import RETURN_FORM

RUN = 'a101-api-ncbi-blast'
EARLIER = 'A101_API_BRANCH_DIRECTORY'


class Switch:
    fail = False


def say(*values):
    print(*values, flush=True)


def workspace_state(directory):
    """Every file of the route's workspace with its size and modification time: what a contact would change."""
    return {str(path.relative_to(directory)): (path.stat().st_size, path.stat().st_mtime_ns)
            for path in sorted(directory.rglob('*')) if path.is_file()}


def model_calls(w):
    return len(list(w['directory'].glob('model_calls*/call-*')))


def submissions(w):
    return [unit[2] for unit in w['journal'].units(RUN, api_world.path_of(RUN)) if unit[2]['tool'] == 'submit']


@pytest.fixture(scope='module')
def branch(tmp_path_factory):
    earlier = os.environ.get(EARLIER)
    directory = Path(earlier) if earlier else tmp_path_factory.mktemp('api_branch')
    say('WORLD_DIRECTORY', directory)
    w = api_world.world(directory, api_world.ncbi_route(directory / 'api_jobs'))
    yield w
    w['store'].close()


@pytest.mark.model_run
def test_the_model_builds_the_blast_request_and_the_public_ncbi_service_takes_it(branch):
    w = branch
    if w['made_before']:
        asked = model_calls(w)
        closed = asyncio.run(api_world.resumed(w, RUN).run())        # the run an earlier process recorded
        assert model_calls(w) == asked
    else:
        run = api_world.linked(w, RUN)
        api_world.show(asyncio.run(run.next_decision()))
        closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    units = [unit[2] for unit in w['journal'].units(RUN, api_world.path_of(RUN))]
    for unit in units:
        shown = {name: value for name, value in unit['outcome'].items() if name != 'result'}
        say('UNIT', unit['tool'], json.dumps(unit['arguments']), '->', json.dumps(shown))
    say('ENDED_BY', w['journal'].run_state(RUN)[1]['ended_by'], 'MODEL_CALLS', model_calls(w), 'RESULT',
        json.dumps(result))
    assert RETURN_FORM.select(api_world.SELECTION).admit(result, 'return') == result
    made = submissions(w)
    assert result['finding']['submissions'] == len(made)
    # What the model built is the request of the assigned job (``action`` admitted nothing else).
    for unit in made:
        assert unit['arguments']['request']['database'] == 'swissprot'
        assert unit['arguments']['request']['program'] in ('blastp', 'tblastn')
    if not result['execution_completed']:
        assert result['execution_handoff_refs'] == [] and result['credit'] == 0.0
        pytest.skip('the public service took no submission: ' + json.dumps(
            [unit['outcome']['failure'] for unit in made]))

    # -- the handoff ------------------------------------------------------------------------------------------
    handoff_ref, = result['execution_handoff_refs']
    assert result['credit'] == 1.0 and made[-1]['outcome']['handoff_refs'] == [handoff_ref]
    row = WorkRows(w['store']).row(handoff_ref)
    native = row['detail']['native']
    say('HANDOFF', json.dumps({'job': row['job'], 'at': row['at'], 'kind': row['detail']['kind'], 'native': native}))
    say('REPLY', w['store'].get_artifact(row['source_ref']).decode())
    assert row['event'] == 'handoff' and row['detail']['kind'] == 'api' and native['service'] == 'ncbi_blast'
    assert native['request']['query_length'] == len(api_world.QUERY)
    receipts = {item['ref']: item['how'] for item in w['journal'].receipts(RUN, api_world.path_of(RUN))}
    assert receipts[handoff_ref] == 'produced' and receipts[row['source_ref']] == 'produced'

    # -- resume: the recorded units replay; the model is not asked and the service is not contacted ------------
    asked, before = model_calls(w), workspace_state(w['directory'] / 'api_jobs')
    again = asyncio.run(api_world.resumed(w, RUN).run())
    assert again['result'].as_record() == result and model_calls(w) == asked
    assert workspace_state(w['directory'] / 'api_jobs') == before
    recorded = [name for name in before if name.endswith('submission.json')]
    assert len(recorded) == len(made)                        # one recorded submission per submit unit, no more


@pytest.mark.model_run
def test_the_job_is_waited_for_checked_and_fetched_as_the_route_defines(branch):
    w = branch
    made = submissions(w)
    if not made or not made[-1]['outcome']['handoff_refs']:
        pytest.skip('no submission was accepted: there is no job')
    handoff_ref, = made[-1]['outcome']['handoff_refs']
    row = WorkRows(w['store']).row(handoff_ref)
    native = row['detail']['native']
    route = ApiJobRoute(w['configuration']['api'][api_world.RESOURCE], resource_id=api_world.RESOURCE)
    say('WAITING_FOR', native['remote_id'], 'submitted', row['at'])
    asyncio.run(route.wait(row['job'], native))
    ended = route.status(row['job'], native)
    say('STATUS', json.dumps(ended))
    plan = [{'tool': 'check', 'arguments': {'handoff_ref': handoff_ref, 'cut': None}},
            {'tool': 'fetch', 'arguments': {'handoff_ref': handoff_ref, 'names': None, 'cut': None}}]
    collaborators = {**w['collaborators'], 'services': {**job_services(w['configuration']), 'switch': Switch},
                     'continuation': {'job_probe': {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}}}
    entry = {'assignment': {'input_refs': [], 'job_refs': [handoff_ref]}, 'message': {'plan': plan}, 'selection': []}
    asyncio.run(link(BindingRegistry([JobProbe()]), 'job_probe', entry, run_id='extract', journal=w['journal'],
                     collaborators=collaborators).run())
    checked, fetched = (unit[2]['outcome'] for unit in w['journal'].units('extract', (('job_probe', 'extract'),)))
    say('CHECK', json.dumps(checked))
    say('FETCH', json.dumps(fetched))
    assert checked['status'] == 'completed' and checked['state'] == ended['state']
    if ended['state'] != 'finished':
        assert fetched['status'] == 'failed' and fetched['failure']['code'] == 'results_not_available'
        pytest.skip('the service ended the search without a result: ' + json.dumps(ended['reply']))
    assert fetched['status'] == 'completed' and fetched['outcome'] == 'results_acquired'
    files = {item['name']: item for item in fetched['results']}
    report = json.loads(w['store'].get_artifact(files['blast_result.json']['ref']))['BlastOutput2']
    report = (report[0] if isinstance(report, list) else report)['report']
    search = report['results']['search']
    say('RESULT_FILES', json.dumps({name: item['bytes'] for name, item in files.items()}))
    say('REPORT', json.dumps({'program': report['program'], 'version': report['version'],
                              'database': report['search_target'], 'query_len': search['query_len'],
                              'hits': len(search.get('hits', [])),
                              'first_hit': [item['accession'] for item in search['hits'][0]['description']][:3]
                              if search.get('hits') else None}))
    assert report['program'] == made[-1]['arguments']['request']['program']
    assert search['query_len'] == len(api_world.QUERY)
