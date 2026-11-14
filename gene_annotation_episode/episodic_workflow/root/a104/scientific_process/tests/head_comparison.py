"""Strict retained observation comparison, with one declared fresh descriptor field.

Only fresh same-stage scientific binding descriptors may have their current
implementation digest represented by a marker in comparison copies. Every
original payload is retained, every digest must match the actual full stage
source map, and saved historical carriers never pass through this function.
"""
import hashlib
import json
from pathlib import Path
PREFIX = 'gene_annotation_episode/episodic_workflow/root/a104/'
def scientific_digest(source_map):
    values = {path[len(PREFIX):]: digest for path, digest in source_map.items()
        if path.startswith(PREFIX) and path.endswith('.py') and 'tests' not in Path(path).parts}
    assert values
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()

def comparable(value, expected_digest, *, path=(), descriptors=None):
    if descriptors is None: descriptors = []
    if isinstance(value, list):
        return [comparable(item, expected_digest, path=(*path, index), descriptors=descriptors)
            for index, item in enumerate(value)]
    if not isinstance(value, dict): return value
    if 'implementation_sha256' in value and value.get('binding_id') == 'scientific_process':
        assert set(value) == {'version', 'binding_id', 'implementation_sha256', 'configuration'}
        assert value['version'] == 'scientific_process_episode_v10'
        assert value['implementation_sha256'] == expected_digest, ('unproven_fresh_descriptor', path)
        assert isinstance(value['configuration'], dict)
        descriptors.append(list(path))
        return {key: ('<authenticated-current-scientific-implementation>' if key == 'implementation_sha256'
            else comparable(item, expected_digest, path=(*path, key), descriptors=descriptors))
            for key, item in value.items()}
    return {key: comparable(item, expected_digest, path=(*path, key), descriptors=descriptors)
        for key, item in value.items()}

def observations(reports):
    result = {}
    for report in reports:
        if report['phase'] != 'call': continue
        assert report['outcome'] == 'passed'
        assert report['nodeid'] not in result
        properties = report['properties']
        assert len(properties) == 1, ('exactly_one_complete_observation_required', report['nodeid'])
        key, value = properties[0]
        result[report['nodeid']] = {key: json.loads(value)}
    return result

def compare(original, connected):
    before = observations(original['reports']); after = observations(connected['reports'])
    assert before.keys() == after.keys()
    old_digest = scientific_digest(original['source_sha256'])
    new_digest = scientific_digest(connected['source_sha256'])
    rows = []
    for nodeid in sorted(before):
        old_paths, new_paths = [], []
        old_value = comparable(before[nodeid], old_digest, descriptors=old_paths)
        new_value = comparable(after[nodeid], new_digest, descriptors=new_paths)
        assert old_paths == new_paths, ('descriptor_custody_paths_changed', nodeid)
        assert old_value == new_value, ('original_scientific_observation_changed', nodeid, before[nodeid], after[nodeid])
        rows.append({'nodeid': nodeid, 'full_payload_equal': True,
            'fresh_descriptor_paths': old_paths})
    return {'status': 'passed_full_scientific_head_observation_comparison',
        'original_implementation_sha256': old_digest, 'connected_implementation_sha256': new_digest,
        'observations': rows, 'saved_historical_descriptors_rewritten': False,
        'original_payloads_preserved': True}
