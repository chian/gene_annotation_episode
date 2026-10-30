"""Additive checkpoint: accepted059 mechanics; broader literature goal active."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    prior_path = BASE / 'CHECKPOINT_044_ADDENDUM_001.json'
    prior = json.loads(prior_path.read_bytes())
    for name, digest in prior['files'].items():
        assert fingerprint(ROOT / name)['sha256'] == digest, name
    stage = BASE / 'a105_contract_information_design_059/connected_stage_004'
    path = stage / 'MANIFEST_010.json'
    assert fingerprint(path)['sha256'] == 'e1803d714cb736a2a6daf062ed7ede12eb0af4a97a39c3949fa19669b239bd59'
    delivery = json.loads(path.read_bytes())
    for name, expected in delivery.items():
        assert fingerprint(stage / name) == expected, name
    graph = BASE / 'a105_controlled_graph_design_061'
    graph_path = graph / 'MANIFEST_001.json'
    assert fingerprint(graph_path)['sha256'] == 'b91d2f600b401db81e500482ede008e1bd77c1901e69f98ff89c60985ccb7606'
    graph_manifest = json.loads(graph_path.read_bytes())
    for name, expected in graph_manifest['files'].items():
        actual = fingerprint(graph / name)
        assert actual['sha256'] == expected['sha256'] and actual['bytes'] == expected['bytes'], name
    review = BASE / 'contract_information_parent_review_059/connected_review_005'
    names = ['reproduce_invalid_query_reply_001.py', 'INVALID_QUERY_REPLY_RECEIPT_001.json',
             'reproduce_invalid_query_reply_002.py', 'INVALID_QUERY_REPLY_RECEIPT_002.json',
             'verify_connected_delivery_010.py', 'verify_connected_delivery_010_revision_002.py',
             'CONNECTED_DELIVERY_ROOT_RECEIPT_010_revision_002.json', 'ROOT_VERIFIER_CORRECTION_010.md',
             'ACCEPTANCE_010.md']
    paths = [prior_path, Path(__file__), BASE / 'PROGRESS_045.md', path, graph_path,
             BASE / 'parent_launch_030/BOUNDARY_018.json', *(review / name for name in names)]
    files = dict(prior['files'])
    files.update({str(path.relative_to(ROOT)): fingerprint(path)['sha256'] for path in paths})
    result = {'checkpoint': '045', 'goal_complete': False, 'current_goal_execution': 'progress',
              'previous_implementation_goal_turn': 'progress',
              'prior044_addendum_paths_verified': len(prior['files']),
              'accepted059_delivery_entries_verified': len(delivery),
              'proposal061_entries_verified': len(graph_manifest['files']),
              'files': files,
              'scope': 'Accepted bounded059 mechanical integration and independently reproduced saved-query correction; no configured-profile scientific run or full A105/full-goal completion.',
              'open_work': ['056 immutable reader008 review', '061 additive002 graph/count-only design and schema review',
                            '062 fresh configured-profile scientific execution proposal',
                            'A105 remaining scientific coverage and later scoped literature responsibilities']}
    with (BASE / 'CHECKPOINT_045.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': True, 'prior_paths_verified': len(prior['files']),
                      'delivery059_verified': len(delivery),
                      'graph061_verified': len(graph_manifest['files']), 'frozen_paths': len(files)}))


if __name__ == '__main__':
    main()
