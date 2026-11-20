"""A real run of ``launch_api`` (a plain script, not pytest): real runner, real Store, the real public NCBI BLAST
service, the real model provider (never asked: the episode is code-decided). Usage: ``real_run.py <workdir>``.

First the refusals that need no network (a program that does not take the query's molecule), then the one real
submission, then a resume that must ask the model nothing and send nothing."""
import asyncio
import json
import sys
from pathlib import Path

from episode_runtime import BindingRegistry, link, resume

from ..episode import DatabaseBlastLaunchApi
from ...tests.hosted_world import RESOURCE, collaborators, world

PATH = DatabaseBlastLaunchApi.binding_path
SETTINGS = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.05}}
SELECTION = ['execution_handoff_refs', 'execution_completed']


def entry(held, **changes):
    assignment = {'version': 'database_blast_launch_api_assignment_v1', 'resource_id': RESOURCE,
                  'service': 'ncbi_blast', 'query_subject_refs': [held['subject']], 'program': 'blastp',
                  'database': 'swissprot', 'hitlist_size': 20, 'completion_target': 1.0,
                  'record_refs': [held['subject'], held['sequence_ref']], **changes}
    return {'assignment': assignment, 'message': {}, 'selection': SELECTION}


def linked(held, run_id, **changes):
    return link(BindingRegistry([DatabaseBlastLaunchApi()]), PATH, entry(held, **changes), run_id=run_id,
                journal=held['journal'], collaborators=collaborators(held, {PATH: SETTINGS}))


def jobs_started(held):
    return sorted(path.name for path in (held['directory'] / 'api_jobs').glob('*') if path.is_dir())


def main(workdir):
    base = Path(workdir).resolve()
    refused = world(base / 'refusal')
    try:
        asyncio.run(linked(refused, 'refuse-blastn', program='blastn').run())
        print('REFUSAL blastn on a protein: NOT REFUSED')
    except Exception as error:
        print('REFUSAL blastn on a protein:', type(error).__name__, str(error)[:160], '| jobs started at the service:',
              jobs_started(refused))
    held = world(base / 'real')
    run = linked(held, 'launch-api-1')
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    print('RESULT', json.dumps(result, default=str))
    journal = held['journal']
    path = tuple(tuple(item) for item in journal.episodes('launch-api-1')[0]['path'])
    print('RUN STATE', journal.run_state('launch-api-1')[1], '| units', [(unit[0], unit[2]['outcome']['status'])
                                                                       for unit in journal.units('launch-api-1', path)])
    print('MODEL CALLS', len(journal.model_calls('launch-api-1', path)))
    for recorded in sorted((held['directory'] / 'api_jobs').glob('*/submission.json')):
        made = json.loads(recorded.read_text())
        print('SERVICE SUBMISSION', json.dumps({key: made[key] for key in ('outcome', 'remote_id', 'expected_seconds')}))
    print('JOBS STARTED AT THE SERVICE', jobs_started(held))
    resumed = asyncio.run(resume(BindingRegistry([DatabaseBlastLaunchApi()]), run_id='launch-api-1',
                                 journal=journal, collaborators=collaborators(
                                     world(base / 'real'), {PATH: SETTINGS})).run())
    print('RESUME same result:', resumed['result'].as_record() == result, '| jobs started at the service:',
          jobs_started(held))


if __name__ == '__main__':
    main(sys.argv[1])
