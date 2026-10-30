"""Seal043's additive source-reader review without freezing active implementations."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    prior = json.loads((BASE / 'CHECKPOINT_043.json').read_bytes())
    for name, expected in prior['files'].items():
        assert digest(ROOT / name) == expected, name
    paths = [BASE / 'CHECKPOINT_043.json', BASE / 'PROGRESS_043_ADDENDUM_001.md',
             BASE / 'CONTROLLED_RESPONSE_READER_RELEASE_008.md', Path(__file__)]
    review = BASE / 'controlled_response_source_parent_review_056'
    paths.extend(review / name for name in (
        'reproduce_confidence_punctuation_007.py', 'CONFIDENCE_PUNCTUATION_RECEIPT_007.json',
        'verify_fixture_algebra_007.py', 'FIXTURE_ALGEBRA_RECEIPT_007.json',
        'verify_proposal_007.py', 'PROPOSAL_RECEIPT_007.json'))
    stage = BASE / 'a105_controlled_response_design_056/reader_stage_007'
    paths.append(stage / 'DELIVERY_007.json')
    delivery = json.loads((stage / 'DELIVERY_007.json').read_bytes())
    for name, record in delivery['artifacts'].items():
        path = stage / name
        assert path.stat().st_size == record['bytes'] and digest(path) == record['sha256'], name
        paths.append(path)
    files = {str(path.relative_to(ROOT)): digest(path) for path in sorted(set(paths))}
    output = {'checkpoint': '043_addendum_001', 'same_goal_execution_as': '043',
              'goal_complete': False, 'current_goal_execution': 'progress',
              'prior043_entries_verified': len(prior['files']), 'files': files,
              'active_unsealed_work': ['056 text/JSON reader implementation008',
                                       '059 connected information integration',
                                       '060 actual-model selected-source scientific audit'],
              'root_scientific_packet_reset_before_conversion_pending': '060',
              'scope': 'Accepted007 proposal and bounded pure-reader release. No implemented source reader, graph/native release, scientific030 acceptance, complete A105/goal/routing/W05 claim.'}
    with (BASE / 'CHECKPOINT_043_ADDENDUM_001.json').open('x') as stream:
        json.dump(output, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': True, 'prior043_verified': len(prior['files']),
                      'proposal_artifacts_verified': len(delivery['artifacts']), 'frozen_paths': len(files)}))


if __name__ == '__main__':
    main()
