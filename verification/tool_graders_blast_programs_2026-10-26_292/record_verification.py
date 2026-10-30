"""Index retained paired-BLAST implementation verification, without execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).parent
GOAL = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
POLICY = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path)}


assert sha(GOAL) == '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
runs = [
    ('tool_graders_blast_collection_2026-10-26_293', 'check003', 173),
    ('tool_graders_blast_pairwise_2026-10-26_294', 'checks_004', 139),
    ('tool_graders_blast_geometry_2026-10-26_295', 'checks_004', 506),
    ('tool_graders_blast_geometry_2026-10-26_295', 'checks_005', 68),
    ('tool_graders_blast_local_2026-10-26_296', 'final_checks', 117),
    ('tool_graders_blast_publication_2026-10-26_297', 'check002', 75),
    ('tool_graders_blast_publication_2026-10-26_297', 'check003', 1),
    ('tool_graders_blast_publication_2026-10-26_297', 'check004', 23),
    ('tool_graders_blast_integration_2026-10-26_298', 'final_checks', 97),
    ('tool_graders_blast_regressions_2026-10-26_299', 'checks_003', 34),
]
evidence = []
for directory, run, expected in runs:
    path = ROOT / 'verification' / directory / run
    receipt = json.loads((path / 'receipt.json').read_text())
    metadata = receipt.get('metadata', receipt)
    assert receipt.get('returncode', metadata.get('native_returncode')) == 0
    assert metadata['policy'] == POLICY
    junit = path / 'junit.xml'
    if junit.exists():
        suites = ET.parse(junit).getroot().findall('testsuite')
        counts = {name: sum(int(suite.get(name, 0)) for suite in suites)
                  for name in ('tests', 'errors', 'failures', 'skipped')}
        assert counts == {'tests': expected, 'errors': 0, 'failures': 0, 'skipped': 0}
        proof = descriptor(junit)
    else:
        logs = [p for p in (path / 'stdout.txt', path / 'stdout.log') if p.exists()]
        assert len(logs) == 1
        assert re.search(r'\b' + str(expected) + r' passed\b', logs[0].read_text())
        proof = descriptor(logs[0])
    evidence.append({'run': str(path.relative_to(ROOT)), 'passing_checks': expected,
                     'receipt': descriptor(path / 'receipt.json'), 'test_outcome': proof})

latest = ROOT / 'verification/tool_graders_blast_integration_2026-10-26_298'
latest_receipt = json.loads((latest / 'final_checks/receipt.json').read_text())
assert latest_receipt['changed_sources'] == []
verified = json.loads((latest / 'FINAL_SOURCE_HASHES.json').read_text())
relevant_names = [
    'blast_program_context.py', 'blast_report_collection.py', 'blast_pairwise_results.py',
    'blast_pairwise_grader.py', 'blast_pairwise_result_views.py',
    'native_blast_contracts.py', 'native_blast_driver.py', 'native_blast_tool_info.py',
    'native_blast_local.py', 'native_blast_acquisition.py', 'native_blast_result_worker.py',
    'native_blast_result_publication.py', 'native_blast_results.py', 'native_blast_returns.py',
    'execution_episodes.py', 'execution_progress.py', 'practical_execution_operations.py',
    'practical_execution_records.py', 'domain.py', 'state.py', 'infernal_result_presentation.py',
]
current = []
for name in relevant_names:
    relative = 'gene_annotation_episode/' + name
    assert sha(ROOT / relative) == verified[relative], relative
    current.append(descriptor(ROOT / relative))
index = ROOT / 'gene_annotation_episode/knowledge/index.json'
manual = ROOT / 'gene_annotation_episode/knowledge/native-blast-pairwise.md'
assert sha(index) == '424f7a35ea822ba3e0c227a1e21cd54d5f5bd769681b25acb3b381be08ce3ce1'
assert sha(manual) == '1a4701c011ba1ea1e80e036dc66b5f2489f78b28bc3f35e5f85014dab7ef8cb9'
current.extend((descriptor(index), descriptor(manual)))
files = [
    'tool_graders_blast_pairwise_2026-10-26_294/filled_001/summary.json',
    'tool_graders_blast_publication_2026-10-26_297/FINAL_FILLED_EXAMPLES.json',
    'tool_graders_blast_integration_2026-10-26_298/FILLED_PARENT_FORMS.json',
    'tool_graders_blast_integration_2026-10-26_298/FILLED_SCIENTIFIC_FORWARDING_FORM.json',
    'tool_graders_blast_integration_2026-10-26_298/FILLED_PARTIAL_AND_ZERO_FORMS.json',
]
manifest = {
    'schema': 'native_pairwise_blast_implementation_verification_v1',
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'scope_rows': ['A-L069-' + name + '-pairwise' for name in ('blastn', 'blastp', 'blastx', 'tblastn', 'tblastx')],
    'report': descriptor(BASE / 'REPORT_001.md'),
    'contracts': [descriptor(p) for p in sorted(BASE.glob('CONTRACT*.md'))],
    'run_results': evidence,
    'full_workflow_passing_checks': 97,
    'full_workflow_native_program': 'blastx',
    'all_five_program_native_capture_and_numerical_verification': True,
    'actual_retained_native_example_count': 20,
    'test_counts_overlap': True,
    'verified_relevant_source_snapshots': current,
    'source_after_manifest': descriptor(latest / 'FINAL_SOURCE_HASHES.json'),
    'filled_verification_examples': [descriptor(ROOT / 'verification' / name) for name in files],
    'library_retrieval_receipt': descriptor(BASE / 'knowledge_check001/receipt.json'),
    'library_snapshot_qualification': '298 initially targeted the wrong knowledge directory. Root separate retrieval check and actual index/manual hashes are separate evidence, not retroactive before/after coverage.',
    'qualification': 'Five implemented local pairwise numerical graders and their shared execution/return path. Actual native producer/capture/numerical checks cover five programs; the complete scripted Workflow numerical example is reverse BLASTX. No database/API/HPC, configured-model scientific benefit or all-suite pass claim.',
    'unresolved_broad_regression_provenance_cases': 5,
    'native_pairwise_selected_column_connection_counted': False,
}
with (BASE / 'VERIFICATION_MANIFEST_001.json').open('x') as stream:
    json.dump(manifest, stream, indent=2)
    stream.write('\n')
print(json.dumps({'scope_rows': manifest['scope_rows'], 'recorded_runs': len(evidence),
                  'actual_retained_native_examples': 20, 'full_workflow_checks': 97}))
