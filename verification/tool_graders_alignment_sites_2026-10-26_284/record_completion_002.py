"""Index existing field/function verification; do not rerun or regrade tools."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).parent
NATIVE = ROOT / 'verification/tool_graders_native_blast_sites_2026-10-26_300'
FROZEN = ROOT / 'verification/tool_graders_bvbrc_pairwise_frozen_2026-10-26_301'
GOAL = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path)}


assert sha(GOAL) == '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
baseline = json.loads((BASE / 'BASELINE_VERIFICATION_001.json').read_text())
native = json.loads((NATIVE / 'SOURCE_AFTER.json').read_text())
index = json.loads((NATIVE / 'VERIFICATION_INDEX.json').read_text())
allowed_changes = {
    'gene_annotation_episode/alignment_site_action_records.py',
    'gene_annotation_episode/alignment_site_native.py',
    'gene_annotation_episode/blast_hsp_site_inputs.py',
    'gene_annotation_episode/blast_result_views.py',
    'gene_annotation_episode/knowledge/blast-hsp-columns.md',
    'gene_annotation_episode/knowledge/index.json',
}
current_changes = {p for p, digest in baseline['verified_source_sha256'].items()
                   if sha(ROOT / p) != digest}
assert current_changes == allowed_changes
for path, value in native.items():
    assert sha(ROOT / path) == value['sha256'], path
assert sha(ROOT / 'gene_annotation_episode/knowledge/index.json') == (
    '606c3eea05e28a50374cb2da7cf1eece1479c7d7b5276ad497d197de5de4f81b')
assert json.loads((NATIVE / 'final002/source_delta.json').read_text()) == {}

cases = set()
run_results = []
for name, expected in [('check003', 287), ('workflow001', 1),
                       ('check004', 8), ('final002', 27)]:
    run = NATIVE / name
    receipt = json.loads((run / 'receipt.json').read_text())
    assert receipt['native_returncode'] == 0
    assert receipt['policy'] == {'memory_bytes': 21474836480,
                                 'scratch_bytes': 4294967296, 'wall_seconds': None}
    root = ET.parse(run / 'junit.xml').getroot()
    actual = root.findall('.//testcase')
    assert len(actual) == expected
    assert not any(c.find(k) is not None for c in actual
                   for k in ('failure', 'error', 'skipped'))
    cases.update((c.get('classname'), c.get('name')) for c in actual)
    run_results.append({'run': str(run.relative_to(ROOT)), 'passing_checks': expected,
                        'receipt': descriptor(run / 'receipt.json'),
                        'test_outcome': descriptor(run / 'junit.xml')})
assert len(cases) == 297
assert cases == set(map(tuple, index['successful_test_cases']))
assert index['retained_report_count'] == 20
assert index['retained_published_hsp_count'] == 36
assert index['new_actual_native_executions'] == 1

knowledge = json.loads((BASE / 'knowledge_check001/result.json').read_text())
assert knowledge['new_scientific_records'] == 0 and not knowledge['native_execution']
assert len(knowledge['entries']) == 2
assert all(r['complete_text_recovered'] for r in knowledge['entries'])
assert json.loads((BASE / 'knowledge_check001/receipt.json').read_text())['returncode'] == 0
frozen_receipt = FROZEN / 'snapshot/verification/frozen_check_001/receipt.json'
assert json.loads(frozen_receipt.read_text())['returncode'] == 0
frozen_junit = FROZEN / 'snapshot/verification/frozen_check_001/junit.xml'
frozen_cases = ET.parse(frozen_junit).getroot().findall('.//testcase')
assert len(frozen_cases) == 5
assert not any(c.find(k) is not None for c in frozen_cases
               for k in ('failure', 'error', 'skipped'))

source_paths = set(baseline['verified_source_sha256']) | set(native)
manifest = {
    'schema': 'alignment_site_completion_verification_v1',
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'scope_rows': baseline['scope_rows'],
    'report': descriptor(BASE / 'REPORT_ADDENDUM_002.md'),
    'baseline': descriptor(BASE / 'BASELINE_VERIFICATION_001.json'),
    'contracts': [descriptor(BASE / name) for name in
                  ('CONTRACT_001.md', 'RETURN_CONTRACT_002.md')]
                 + [descriptor(NATIVE / name) for name in
                    ('CONTRACT_001.md', 'CONTRACT_ADDENDUM_002.md')],
    'native_verification': [descriptor(NATIVE / name) for name in
        ('HANDOFF.md', 'VERIFICATION.md', 'VERIFICATION_INDEX.json',
         'NATIVE_INPUT_HASHES.json', 'SOURCE_AFTER.json',
         'final002/source_before.json', 'final002/source_after.json',
         'final002/source_delta.json', 'POSTCHECK_SOURCE_STATUS.json')],
    'run_results': run_results,
    'native_extension_distinct_passing_cases': len(cases),
    'native_retained_report_count': 20,
    'native_retained_hsp_count': 36,
    'actual_new_full_workflow_execution': 'reverse_blastx_supplied_pair',
    'baseline_source_changes': sorted(current_changes),
    'current_relevant_source_snapshots': [descriptor(ROOT / path)
                                           for path in sorted(source_paths)],
    'library_retrieval': [descriptor(BASE / 'knowledge_check001' / name)
                           for name in ('receipt.json', 'result.json')],
    'separate_frozen_bvbrc_regression': {
        'passing_checks': 5, 'report': descriptor(FROZEN / 'REPORT.md'),
        'receipt': descriptor(frozen_receipt), 'test_outcome': descriptor(frozen_junit),
        'original_broad_result_unchanged': True},
    'test_counts_overlap': True,
    'pending_native_pairwise_hsp_connection': False,
    'qualification': 'Implemented field definitions, population functions, separate '
        'calculators and requested scientific-child returns for retained alignment '
        'selection. Baseline retained/native/scripted paths and one new actual '
        'reverse-BLASTX Workflow are separately qualified. No all-suite, every-resource, '
        'configured-model annotation, W05 or literature claim.',
}
with (BASE / 'COMPLETION_VERIFICATION_002.json').open('x') as stream:
    json.dump(manifest, stream, indent=2)
    stream.write('\n')
print(json.dumps({'scope_rows': manifest['scope_rows'],
                  'native_extension_distinct_passing_cases': len(cases),
                  'verified_relevant_source_files': len(source_paths)}))
