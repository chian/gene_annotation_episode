"""Verify completed XML/source records without importing or running tests."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


OUT = Path('/tmp/api-planning-publication-preparation-20261022-001')
ROOT = Path('/tmp/api-planning-root-final-20261022-004')
CHECKOUT = Path('/tmp/gene-annotation-hmmer-api-20261022-004')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
inputs = json.loads((ROOT/'INPUTS.json').read_text())
consumers = json.loads((ROOT/'CONSUMERS_INPUTS.json').read_text())
assert inputs['files'] == consumers['files']
assert sha(ROOT/'INPUTS.json') == consumers['source_manifest_sha256']
assert len(inputs['files']) == 344
for name, row in inputs['files'].items():
    path = CHECKOUT/name
    assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes'], name
    assert sha(OUT/'candidate'/name) == row['sha256'], name
actual = {str(path.relative_to(CHECKOUT)) for prefix in ('gene_annotation_episode', 'method_loop', 'tests')
    for path in (CHECKOUT/prefix).rglob('*.py') if '__pycache__' not in path.parts}
assert actual == set(inputs['files'])
pin = hashlib.sha256()
for name, row in sorted(inputs['files'].items()):
    if not name.startswith('tests/'):
        pin.update(name.encode()+b'\0'+bytes.fromhex(row['sha256']))
assert pin.hexdigest() == inputs['runtime_pin'] == '16435877cddb566a9b802b6b3ce942595a9564b4cc10f8ca52b75f4007d9689d'
groups, identities = {}, set()
for group, count, seconds in [('legacy', 135, 463.04), ('consumers', 180, 600.15), ('detached', 1, 26.97)]:
    xml_path, log_path = ROOT/(group+'.xml'), ROOT/(group+'.log')
    document = ET.parse(xml_path)
    cases = list(document.iter('testcase'))
    assert len(cases) == count
    assert not list(document.iter('failure')) and not list(document.iter('error')) and not list(document.iter('skipped'))
    names = [(case.attrib['classname'], case.attrib['name']) for case in cases]
    assert len(names) == len(set(names))
    assert identities.isdisjoint(names), group
    identities.update(names)
    log = log_path.read_text()
    assert f'{count} passed in {seconds:.2f}s' in log
    groups[group] = {'cases': count, 'seconds': seconds, 'failures': 0, 'errors': 0, 'skips': 0,
        'xml_sha256': sha(xml_path), 'log_sha256': sha(log_path),
        'command': consumers['command'] if group == 'consumers' else inputs['commands'][group],
        'nodes': [{'classname': a, 'name': b} for a, b in names]}
assert len(identities) == 316
record = {'version': 'api004_independent_root_xml_and_source_check_v1',
    'runtime_pin': pin.hexdigest(), 'runtime_count': 133, 'test_count_at_root_commands': 211,
    'all344_actual_and_staged_source_test_members_match_original_root_INPUTS': True,
    'source_inputs_sha256': sha(ROOT/'INPUTS.json'), 'consumers_inputs_sha256': sha(ROOT/'CONSUMERS_INPUTS.json'),
    'groups': groups, 'distinct_cases': len(identities), 'group_nodes_disjoint': True,
    'supplemental_scope030': 'Pending actual node result; neither counted nor assumed to change old tests.',
    'no_application_or_test_execution': True,
    'limit': 'This independently checks retained XML/log/source relationships. Root owns command exit/result ledger and final publication authorization.'}
path = OUT/'FINAL_ROOT_XML_AND_SOURCE_CHECK.json'
with path.open('x') as stream:
    stream.write(json.dumps(record, indent=2, sort_keys=True)+'\n')
print(json.dumps({'record': str(path), 'sha256': sha(path), 'distinct_cases': 316,
    'groups': {name: row['cases'] for name, row in groups.items()}, 'runtime_pin': pin.hexdigest()}, indent=2))
