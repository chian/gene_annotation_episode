"""Branch run of the A101 launch episode with its API child, by the real model: the launch episode looks up the
resource, the model commissions the API child on it, the child's model builds the request and submits it, and the
handoff row comes up to the launch episode in custody.

World (``launch_world.py``): real Store, RunJournal, ``job_services`` with the API route, both episodes' settings,
the real ``ModelProvider``. The route is bound to a service of this test process that speaks the NCBI BLAST Common
URL API (``episode_support/jobs/tests/blast_url_api_server.py``): the public NCBI service is contacted by the API
child's own branch test, and one tiny search there is enough. Selected only with ``-m model_run``."""
import asyncio
import json

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.jobs.tests.blast_url_api_server import (
    blast_url_api_service, route_configuration)

from ..messages.final_to_parent import RETURN_FORM
from . import launch_world

RUN = 'a101-api-launch'


@pytest.mark.model_run
def test_the_launch_commissions_the_api_child_and_receives_the_handoff_in_custody(tmp_path):
    with blast_url_api_service() as service:
        w = launch_world.world(tmp_path, route_configuration(service, tmp_path / 'api_jobs'))
        closed = asyncio.run(launch_world.linked(w, RUN).run())
        result = closed['result'].as_record()
        units = [unit[2] for unit in w['journal'].units(RUN, launch_world.path_of(RUN))]
        for unit in units:
            if unit['kind'] == 'child':
                print('UNIT child', unit['slot'], json.dumps(unit['arguments']), 'ASSIGNMENT',
                      json.dumps(unit['message']['assignment']), 'COMPLETION', json.dumps(unit['completion']),
                      'RESULT', json.dumps(unit['result']))
            else:
                print('UNIT tool', unit['tool'], json.dumps(unit['arguments']), flush=True)
        print('ENDED_BY', w['journal'].run_state(RUN)[1]['ended_by'], 'RESULT', json.dumps(result), flush=True)
        print('SERVICE_RECEIVED', json.dumps([item['fields'] for item in service.requests]), flush=True)
        assert RETURN_FORM.select(launch_world.SELECTION).admit(result, 'return') == result
        launches = [unit for unit in units if unit['kind'] == 'child']
        assert launches and all(unit['slot'] == 'launch_api' for unit in launches)
        # The handoff the child established is the launch episode's: held as returned, and its credit.
        handoff_ref, = result['execution_handoff_refs']
        assert result['execution_completed'] is True and result['credit'] == 1.0
        assert launches[-1]['result']['execution_handoff_refs'] == [handoff_ref]
        receipts = {item['ref']: item['how'] for item in w['journal'].receipts(RUN, launch_world.path_of(RUN))}
        assert receipts[handoff_ref] == 'returned'
        puts = service.received(CMD='Put')
        assert len(puts) == 1 and puts[0]['fields']['DATABASE'] == 'swissprot'
        assert puts[0]['fields']['PROGRAM'] in ('blastp', 'tblastn')
        # Resume replays both episodes: the model is not asked and nothing is sent.
        asked = len(list((tmp_path / 'model_calls').glob('call-*')))
        again = asyncio.run(launch_world.resumed(w, RUN).run())
        assert again['result'].as_record() == result and len(service.requests) == 1
        assert len(list((tmp_path / 'model_calls').glob('call-*'))) == asked
