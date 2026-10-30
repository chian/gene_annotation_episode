"""Save filled API publication examples; no live request or native execution.

Run with this checkout's .venv/bin/python and an unused generation label. Native
phmmer pages are retained historical outputs; transport, status, submission, and
all hmmscan data here are explicitly synthetic verification inputs.
"""
from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import urllib.request
from unittest.mock import patch

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

from gene_annotation_episode.state import Store
from gene_annotation_episode.hmmer_search_grader import calculate_hmmer_search_scores
from test_hmmer_grading_publication import (PAGE1, PAGE2, receiver, grading_for,
    numeric, synthetic_payload)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n')


def prohibited(*args, **kwargs):
    raise AssertionError('saved examples use supplied data only')


def main():
    label = sys.argv[1]
    if re.fullmatch(r'[a-z0-9-]+', label) is None:
        raise ValueError('generation_label_required')
    output = Path(__file__).resolve().parent/label
    output.mkdir(exist_ok=False)
    rows = []
    cases = [
        ('retained-phmmer-page1', {'body': PAGE1.read_bytes()}, 'historical_actual_service_page', PAGE1),
        ('retained-phmmer-page2', {'body': PAGE2.read_bytes(), 'page': 2}, 'historical_actual_service_page', PAGE2),
        ('synthetic-hmmscan-positive', {'body': synthetic_payload('hmmscan'),
            'algorithm': 'hmmscan', 'sequence': 'MACDEFGHIKLM'}, 'synthetic_hmmscan_numerical_fixture', None),
        ('synthetic-hmmscan-empty', {'body': {'status': 'SUCCESS', 'page_count': 1,
            'result': {'stats': {'algo': 'hmmscan', 'nreported': 0}, 'hits': []}},
            'algorithm': 'hmmscan'}, 'synthetic_hmmscan_empty_fixture', None),
    ]
    with ExitStack() as stack:
        for target in ('socket.create_connection', 'requests.sessions.Session.request',
                       'urllib.request.urlopen', 'subprocess.Popen'):
            stack.enter_context(patch(target, prohibited))
        for name, arguments, classification, original in cases:
            directory = output/name
            directory.mkdir()
            with Store(directory/'workspace') as store:
                _, client, _, result_owner = receiver(store, **arguments)
                outcome = result_owner.act('api.hmmer.result')
                assert outcome['status'] == 'completed', outcome
                grading = grading_for(store, outcome)
                source = store.get(outcome['result']['source_ref'])
                native = store.get_artifact(source['artifact_ref'])
                (directory/'native-response.json').write_bytes(native)
                write(directory/'sheet.json', grading['sheet'])
                write(directory/'scores.json', grading['scores'])
                write(directory/'publication.json', outcome)
                observations = [store.get(r) for r in outcome['record_refs']
                                if store.get(r)['record_type'] == 'observation']
                write(directory/'observations.json', observations)
                values = [numeric(store, o['id']) for o in observations]
                assert result_owner.act('api.hmmer.result', index=0) == outcome
                source_ref = source['id']
            with Store(directory/'workspace') as reopened:
                from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
                retained, = source_tool_gradings(reopened, source_ref)
                assert calculate_hmmer_search_scores(retained['sheet']) == retained['scores']
                assert calculate_hmmer_search_scores(retained['sheet'], parameters={}) == retained['scores']
            rows.append({'name': name, 'input_classification': classification,
                'transport_classification': 'explicitly_synthetic_submission_status_and_http_transport',
                'original_native_path': str(original.relative_to(ROOT)) if original else None,
                'native_sha256': sha256(native).hexdigest(), 'native_bytes': len(native),
                'tool_calls': [x[0] for x in client.calls], 'observation_count': len(observations),
                'numeric_observations': values, 'saved_sheet_recalculation_after_reopen': True,
                'network_and_native_execution_prohibited': True, 'replay_unchanged': True})
    write(output/'NUMERICAL_EXAMPLES.json', rows)
    sources = ['gene_annotation_episode/'+n for n in ('tools.py', 'api_execution.py',
        'hmmer_graders.py', 'hmmer_search_inputs.py', 'hmmer_search_grader.py',
        'tool_grading_artifacts.py', 'provider_jobs.py', 'acquisition.py',
        'api_service_execution.py', 'execution_episodes.py', 'runtime.py')]
    write(output/'SOURCE_HASHES.json', {p: sha256((ROOT/p).read_bytes()).hexdigest()
        for p in sources if (ROOT/p).is_file()})
    print(json.dumps({'output': str(output.relative_to(ROOT)), 'cases': len(rows),
                      'status': 'completed', 'new_live_requests': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
