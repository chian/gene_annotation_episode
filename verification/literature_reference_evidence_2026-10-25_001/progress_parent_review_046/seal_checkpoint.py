"""Seal046 progress without accepting unfinished reader/model work."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    prior_path = BASE / 'CHECKPOINT_045.json'
    prior = json.loads(prior_path.read_bytes())
    for name, digest in prior['files'].items():
        assert fingerprint(ROOT / name)['sha256'] == digest, name
    paths = [prior_path, Path(__file__), BASE / 'PROGRESS_046.md']
    verified_manifests = {}
    specifications = [
        ('a105_controlled_graph_design_061', 'MANIFEST_002.json', '44926eefdb91b3a77e1363ce0d6d9a5c5adb7c68c1cd02f37cfe6397f2f2f5cc'),
        ('a105_contract_profile_model_design_062', 'MANIFEST_001.json', '94d6809da24fec7532b451ab3b349e119980233b774fe7862002a8ffa2385605')]
    for folder, name, expected_digest in specifications:
        stage = BASE / folder
        manifest_path = stage / name
        assert fingerprint(manifest_path)['sha256'] == expected_digest
        manifest = json.loads(manifest_path.read_bytes())
        entries = manifest.get('files', manifest)
        if isinstance(entries, list):
            entries = {row['path']: {key: row[key] for key in ('bytes', 'sha256')} for row in entries}
        for relative, expected in entries.items():
            assert fingerprint(stage / relative) == expected, relative
        verified_manifests[folder] = len(entries)
        paths.append(manifest_path)
    graph_review = BASE / 'controlled_graph_parent_review_061'
    paths.extend(path for path in graph_review.rglob('*') if path.is_file())
    reader_review = BASE / 'controlled_response_source_parent_review_056'
    paths.extend(reader_review / name for name in ('PRELIMINARY_REVIEW_008_001.md',
        'reproduce_defined_unit_partial_008_001.py', 'DEFINED_UNIT_PARTIAL_PROBE_008_001.json'))
    paths.extend(path for path in (reader_review / 'reader008_preliminary_001').rglob('*') if path.is_file())
    files = dict(prior['files'])
    files.update({str(path.relative_to(ROOT)): fingerprint(path)['sha256'] for path in paths})
    result = {'checkpoint': '046', 'goal_complete': False, 'current_goal_execution': 'progress',
              'previous_goal_turn': 'progress', 'prior045_paths_verified': len(prior['files']),
              'manifests_verified': verified_manifests, 'files': files,
              'scope': 'Graph declaration acceptance/bounded coding release and preliminary source-reader review with independently reproduced valid-partial defect. No final reader or configured-model acceptance.',
              'open_work': ['056 corrections/final pin/root acceptance', '063 final graph code/pin/root review',
                            '062 remaining proposal/template/recipe review and fresh-generation decision',
                            'native controlled-reader integration and contrasting primary evidence',
                            'remaining A105 and later scoped literature responsibilities']}
    with (BASE / 'CHECKPOINT_046.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': True, 'prior045_verified': len(prior['files']),
                      'manifests_verified': verified_manifests, 'frozen_paths': len(files)}))


if __name__ == '__main__':
    main()
