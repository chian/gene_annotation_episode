"""Seal accepted actual delivery proofs; ongoing source/graph/profile work is open."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    prior_path = BASE / 'CHECKPOINT_044.json'
    prior = json.loads(prior_path.read_bytes())
    for name, expected in prior['files'].items():
        assert digest(ROOT / name) == expected, name
    delivery = BASE / 'a105_model_saved_source_audit_060/delivery_review_002'
    manifest = json.loads((delivery / 'MANIFEST_002.json').read_bytes())
    paths = [prior_path, Path(__file__), BASE / 'PROGRESS_044_ADDENDUM_001.md',
             delivery / 'MANIFEST_002.json', delivery / 'FINAL_VERIFY_002.json']
    for name, row in manifest['files'].items():
        path = delivery / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
        paths.append(path)
    review = BASE / 'model_source_parent_review_060'
    paths.extend(review / name for name in ('reproduce_readonly_delivery_002.py',
        'READONLY_DELIVERY_ROOT_RECEIPT_002.json', 'verify_delivery_seal_002.py',
        'DELIVERY_SEAL_RECEIPT_002.json'))
    paths.extend(path for path in (review / 'fresh_readonly_delivery_002').rglob('*') if path.is_file())
    files = {str(path.relative_to(ROOT)): digest(path) for path in sorted(set(paths))}
    result = {'checkpoint': '044_addendum_001', 'same_goal_execution_as': '044',
              'goal_complete': False, 'current_goal_execution': 'progress',
              'prior044_entries_verified': len(prior['files']),
              'delivery002_entries_verified': len(manifest['files']), 'files': files,
              'scope': 'Accepted actual030 source-correct typed numerical delivery and fresh original-pin source-free mode=ro parent projection. No complete A105 reliability,whole root closure,routing,W05 or full-goal claim.',
              'active_unsealed_work': ['056 controlled-response source reader008',
                                       '059 coherent connected profile integration',
                                       '061 source-bound graph proposal']}
    with (BASE / 'CHECKPOINT_044_ADDENDUM_001.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': True, 'prior044_verified': len(prior['files']),
                      'delivery002_verified': len(manifest['files']), 'frozen_paths': len(files)}))


if __name__ == '__main__':
    main()
