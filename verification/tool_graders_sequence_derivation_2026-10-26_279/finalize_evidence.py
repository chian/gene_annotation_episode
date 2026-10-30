"""Inspect retained evidence and record a new immutable manifest; run no tests."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
RUNS = (
    ('verification/tool_graders_sequence_translation_2026-10-26_280/check002', 67, 0),
    ('verification/tool_graders_sequence_extraction_2026-10-26_281/pytest_003', 54, 0),
    ('verification/tool_graders_sequence_derivation_2026-10-26_279/check003', 102, 9),
    ('verification/tool_graders_sequence_derivation_2026-10-26_279/check004', 8, 0),
    ('verification/tool_grader_knowledge_fixture_2026-10-26_283/check002', 13, 1),
    ('verification/tool_graders_sequence_derivation_2026-10-26_279/check005', 4, 0),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path)}


def source_hashes(receipt):
    return receipt.get('source_sha256_after', receipt.get('source_hashes_after'))


if (HERE / 'FINAL_MANIFEST.json').exists():
    raise RuntimeError('Immutable manifest already exists')
records = []
for directory, total, failed in RUNS:
    folder = ROOT / directory
    receipt = json.loads((folder / 'receipt.json').read_text())
    cases = list(ET.parse(folder / 'junit.xml').getroot().iter('testcase'))
    failures = [c for c in cases if c.find('failure') is not None or c.find('error') is not None]
    assert len(cases) == total and len(failures) == failed
    assert not any(c.find('skipped') is not None for c in cases)
    assert receipt['returncode'] == (1 if failed else 0)
    assert not receipt.get('changed_sources', [])
    assert receipt.get('sources_unchanged', True)
    records.append({'directory': directory, 'passed': total - failed, 'failed': failed,
                    'receipt': descriptor(folder / 'receipt.json'),
                    'junit': descriptor(folder / 'junit.xml')})

main = json.loads((HERE / 'check003/receipt.json').read_text())
accepted_changes = {'tests/test_sequence_views_integration.py', 'tests/test_tool_knowledge.py'}
for raw_path, digest in source_hashes(main).items():
    path = Path(raw_path)
    path = path if path.is_absolute() else ROOT / path
    relative = str(path.relative_to(ROOT))
    assert sha(path) == digest or relative in accepted_changes, relative

# Later checks establish the exact current fixed-test snapshots.
later = {
    'tests/test_sequence_views_integration.py': HERE / 'check004/receipt.json',
    'tests/test_tool_knowledge.py': ROOT / RUNS[4][0] / 'receipt.json',
    'tests/test_root_episode_boundary.py': HERE / 'check005/receipt.json',
}
for relative, receipt_path in later.items():
    hashes = source_hashes(json.loads(receipt_path.read_text()))
    assert sha(ROOT / relative) == hashes.get(relative, hashes.get(str(ROOT / relative)))

examples_path = HERE / 'FILLED_INTEGRATION_EXAMPLES_001.json'
examples = json.loads(examples_path.read_text())
assert examples['case_count'] == 8 and examples['operation_count'] == 10
assert len(examples['examples']) == 10
for example in examples['examples']:
    for key in ('native_artifact', 'grading_artifact'):
        item = example[key]
        path = ROOT / item['path']
        assert sha(path) == item['sha256']
        assert path.stat().st_size == item['size_bytes']

cases = list(ET.parse(HERE / 'check003/junit.xml').getroot().iter('testcase'))
new = [c for c in cases if 'sequence_derivation' in c.get('classname', '')]
assert len(new) == 16 and all(c.find('failure') is None and c.find('error') is None for c in new)
paths = set()
for raw_path in source_hashes(main):
    path = Path(raw_path)
    paths.add(path if path.is_absolute() else ROOT / path)
paths.update(ROOT / name for name in later)
manifest = {
    'schema': 'sequence_derivation_verified_evidence_v1',
    'scope_rows': ['A-L060-translation', 'A-L060-extraction'],
    'focused_grader_tests_passed': 121,
    'new_integration_tests_passed': 16,
    'actual_publication_examples': 10,
    'run_results': records,
    'report': descriptor(HERE / 'REPORT_001.md'),
    'filled_examples': descriptor(examples_path),
    'current_relevant_source_snapshots': [descriptor(p) for p in sorted(paths)],
    'qualification': 'Actual local operations and scripted child/parent communication. '
                     'Failed broad run retained; corrected subgroups passed separately. '
                     'No API/HPC, configured-model science, annotation-score or literature claim.',
}
with (HERE / 'FINAL_MANIFEST.json').open('x') as stream:
    json.dump(manifest, stream, indent=2)
    stream.write('\n')
print(json.dumps({'manifest': descriptor(HERE / 'FINAL_MANIFEST.json'),
                  'grader_tests': 121, 'integration_tests': 16, 'filled_operations': 10}))
