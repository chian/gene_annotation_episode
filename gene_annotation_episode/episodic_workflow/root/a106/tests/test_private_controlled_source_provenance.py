"""Authenticate inert captured source bytes against all six actual saved maps."""
import hashlib
import json
from pathlib import Path

def test_six_actual_records_bind_exact_inert_captured_source_bytes():
    directory=Path(__file__).parent/'fixtures'/'controlled_response_captured_sources_20261112'
    raw=(directory/'manifest.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='d3c2718b85c43205ded6e1813a0a5a0505fc5f81273adb6a6d94c859b68a83b1'
    manifest=json.loads(raw)
    capture=(directory/manifest['capture_file']).read_bytes()
    assert hashlib.sha256(capture).hexdigest()==manifest['capture_sha256']=='6df168b88f36cd530f6d10b9c6a056e5db372a8152408c831438778f7a131ea9'
    records=json.loads(capture);assert len(records)==manifest['records']==6
    actual={}
    for row in manifest['sources']:
        assert row['inert_file']==row['original_name']+'.txt' and Path(row['inert_file']).name==row['inert_file']
        source=directory/row['inert_file'];assert source.suffix=='.txt'
        actual[row['original_name']]=hashlib.sha256(source.read_bytes()).hexdigest()
        assert actual[row['original_name']]==row['sha256']
    assert len(actual)==14 and len(manifest['profiles'])==2
    union=set()
    for record in records:
        extraction=record['result'] if record['kind']=='extraction' else record['saved']['extraction']
        dependencies=extraction['implementation_dependencies']
        assert dependencies==manifest['profiles'][dependencies['reader_contract_version']]
        expected=dependencies['expected_module_fingerprints']
        assert {name:actual[name] for name in expected}==expected
        union.update(expected)
    assert union==set(actual)
