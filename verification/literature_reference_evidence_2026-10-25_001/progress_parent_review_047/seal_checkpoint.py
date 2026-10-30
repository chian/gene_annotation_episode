"""Seal accepted008 mechanics and explicit unfinished scientific reset/review."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]


def fp(path):
    raw = path.read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def main():
    previous_path = BASE / 'CHECKPOINT_046.json'
    previous = json.loads(previous_path.read_bytes())
    for name, digest in previous['files'].items():
        assert fp(ROOT / name)['sha256'] == digest, name
    paths = [previous_path, Path(__file__), BASE / 'PROGRESS_047.md']
    reader = BASE / 'a105_controlled_response_design_056/implementation_stage_008'
    delivery_path = reader / 'DELIVERY_008.json'
    assert fp(delivery_path)['sha256'] == '855bf0e1f761617b7d2331f046592cd190497783e21eaa95c52e91465bba9d4c'
    delivery = json.loads(delivery_path.read_bytes())
    for name, expected in delivery['artifact_hashes'].items():
        assert fp(reader / name) == expected, name
    paths.append(delivery_path)
    review = BASE / 'controlled_response_source_parent_review_056'
    paths.extend(review / name for name in ('reproduce_defined_unit_partial_008_002.py',
        'DEFINED_UNIT_PARTIAL_PROBE_008_002.json', 'verify_reader_delivery_008.py',
        'DELIVERY_ROOT_RECEIPT_008.json', 'ACCEPTANCE_008.md'))
    paths.append(BASE / 'controlled_graph_parent_review_061/CODE_REVIEW_PROGRESS_063_001.md')
    paths.append(BASE / 'a105_gel_case_parent_review_064/RESEARCH_RELEASE_001.md')
    gel = BASE / 'a105_gel_case_review_064'
    seal_path = gel / 'SEAL_005.json'
    assert fp(seal_path)['sha256'] == 'ef4e324aa975be3d3b60de9322544309c4705ca7135d174a26c9ae24e6df781f'
    seal = json.loads(seal_path.read_bytes())
    for row in seal['files']:
        assert fp(gel / row['name']) == {key: row[key] for key in ('bytes', 'sha256')}, row['name']
    paths.append(seal_path)
    files = dict(previous['files'])
    files.update({str(path.relative_to(ROOT)): fp(path)['sha256'] for path in paths})
    result = {'checkpoint': '047', 'goal_complete': False, 'current_goal_execution': 'progress',
        'previous_goal_turn': 'progress', 'prior046_paths_verified': len(previous['files']),
        'accepted008_artifacts_verified': len(delivery['artifact_hashes']),
        '064_packet_artifact_hashes_verified_NOT_scientific_acceptance': len(seal['files']),
        'root064_full_primary_review_and_postpaper_reset_PENDING': True,
        'files': files, 'open_work': ['063 full tests/manifest/root acceptance',
            '064 root original packet review then complete authority reset before conversion',
            'versioned controlled-reader native integration and actual selected typed delivery',
            '062 remaining template/recipe review and later model-generation decision',
            'remaining A105 and later full-goal responsibilities']}
    with (BASE / 'CHECKPOINT_047.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': True, 'prior046_verified': len(previous['files']),
                      'accepted008_artifacts': len(delivery['artifact_hashes']),
                      '064_artifact_hashes_only': len(seal['files']), 'frozen_paths': len(files),
                      'root064_review_reset_pending': True}))


if __name__ == '__main__':
    main()
