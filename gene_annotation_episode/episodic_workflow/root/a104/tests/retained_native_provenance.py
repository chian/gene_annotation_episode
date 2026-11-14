"""Authenticate original producer source data; never import or execute it."""
import hashlib
import json
from pathlib import Path
import tarfile

SOURCE_PROFILES = {
    'fluorescence/native_fluorescence_preparation.py.txt': 'e2c9f22d19c89cf6435ef66e6307c452234f05cb25649ed4220582835037b241',
    'fluorescence/native_fluorescence_contracts.py.txt': '3b5703437ee1dbd28f572699adab891d4ae095eb57ad36cd4b242cd56da56495',
    'fluorescence/native_lifecycle.py.txt': '7956bc4583baa31237106e1358a9e0f5e6e952b07f78c3bca334979fde276195',
    'protein/native_protein_structure_contracts.py.txt': '44e7308e77e0e6fdcc25cdf4bfa1448037150875c40284ae13ecfe668fc81774',
}

def verify_retained_native_provenance(directory=None):
    directory = Path(directory) if directory is not None else Path(__file__).parent / 'fixtures/native_reader_provenance'
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    assert manifest['version'] == 'a104_retained_native_producer_provenance_v1'
    assert manifest['source_profiles'] == SOURCE_PROFILES
    assert manifest['original_sources_executed'] is False and manifest['historical_policy_is_data_only'] is True
    archive = directory / 'original_producer_sources.tar.gz'
    digest = lambda raw: hashlib.sha256(raw).hexdigest()
    assert digest(archive.read_bytes()) == manifest['archive_sha256']
    raw = {}
    with tarfile.open(archive, 'r:gz') as stream:
        members = stream.getmembers()
        assert len(members) == len({member.name for member in members}) == 9
        assert {member.name for member in members} == set(manifest['members'])
        for member in members:
            assert member.isfile() and not member.issym() and not member.islnk()
            path = Path(member.name); assert not path.is_absolute() and '..' not in path.parts
            body = stream.extractfile(member).read()
            expected = manifest['members'][member.name]
            assert len(body) == expected['size_bytes'] and digest(body) == expected['sha256']
            raw[member.name] = body
    for name, expected in SOURCE_PROFILES.items():
        assert digest(raw[name]) == expected
        family, filename = name.split('/'); filename = filename.removesuffix('.txt')
        for phase in ('before', 'after'):
            pins = json.loads(raw[family + '/source_pins_' + phase + '.json'])
            row, = [item for item in pins if item['path'].endswith('/gene_annotation_episode/' + filename)]
            assert row['sha256'] == expected and row['size_bytes'] == len(raw[name])
    original049 = json.loads(raw['fluorescence/original049_receipt.json'])
    assert original049['returncode'] == 1
    assert original049['terminal'] is original049['quiescent'] is original049['source_unchanged'] is True
    return {'version': manifest['version'], 'archive_sha256': manifest['archive_sha256'],
        'source_profiles': SOURCE_PROFILES, 'all_original_before_and_after_pins_match': True,
        'original049_outer_returncode': 1, 'original049_full_workflow_passed': False,
        'original_sources_executed': False, 'historical_policy_is_data_only': True}
