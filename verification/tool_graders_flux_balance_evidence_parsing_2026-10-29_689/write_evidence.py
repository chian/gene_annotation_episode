"""Host stdlib metadata/hash/diff packaging only; no application/data imports."""
from pathlib import Path
import difflib
import hashlib
import json

repo = Path('/home/chia/repos/gene_annotation_episode')
packet = repo / 'verification/tool_graders_flux_balance_evidence_parsing_2026-10-29_689'
runner = repo / 'verification/tool_graders_hmmer_map_verification_2026-10-28_529'

def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path.relative_to(repo)) if path.is_relative_to(repo) else str(path),
            'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}

def read(path):
    return json.loads(Path(path).read_text())

production = repo / 'gene_annotation_episode/flux_balance_readers.py'
tests = repo / 'tests/test_flux_balance_evidence_parsing_689.py'
baseline = packet / 'before_flux_balance_readers.py'
patch = ''.join(difflib.unified_diff(baseline.read_text().splitlines(keepends=True), production.read_text().splitlines(keepends=True),
    fromfile='a/gene_annotation_episode/flux_balance_readers.py', tofile='b/gene_annotation_episode/flux_balance_readers.py'))
patch += ''.join(difflib.unified_diff([], tests.read_text().splitlines(keepends=True), fromfile='/dev/null', tofile='b/tests/test_flux_balance_evidence_parsing_689.py'))
(packet / 'EXACT_CODE_DIFF_001.patch').write_text(patch)
checks = []
support = []
for name in ('check152_parsing689', 'check152a_parsing689'):
    attempt = runner / name
    receipt = read(attempt / 'receipt.json')
    audit = read(attempt / 'execution_audit.json')
    reports = [json.loads(line) for line in (attempt / 'case_reports.jsonl').read_text().splitlines()]
    selected = read(attempt / 'selected_request.json')
    checks.append({'attempt': str(attempt.relative_to(repo)), 'receipt': receipt, 'audit': audit,
        'passed_call_count': sum(r['phase'] == 'call' and r['outcome'] == 'passed' for r in reports),
        'failed_report_count': sum(r['outcome'] == 'failed' for r in reports),
        'record_pins': [pin(attempt / leaf) for leaf in ('receipt.json', 'execution_audit.json', 'case_reports.jsonl',
            'selected_request.json', 'selected_tests.json', 'stdout.txt', 'stderr.txt', 'handle.json')],
        'frozen_reader': pin(attempt / 'source_snapshot/gene_annotation_episode/flux_balance_readers.py'),
        'frozen_contracts': pin(attempt / 'source_snapshot/gene_annotation_episode/flux_balance_contracts.py'),
        'frozen_new_tests': pin(attempt / 'source_snapshot/tests/test_flux_balance_evidence_parsing_689.py'),
        'example_pins': [pin(path) for path in sorted(attempt.glob('fba689_*.json'))]})
    for relative in selected['support_files']:
        source = repo / relative
        frozen = attempt / 'source_snapshot' / relative
        support.append({'attempt': name, 'original': pin(source), 'frozen': pin(frozen),
                        'same_bytes': source.read_bytes() == frozen.read_bytes()})
    assert production.read_bytes() == (attempt / 'source_snapshot/gene_annotation_episode/flux_balance_readers.py').read_bytes()
    assert receipt['returncode'] == 0 and receipt['terminal'] and receipt['quiescent']
    assert all(receipt[key] for key in ('source_unchanged', 'dependency_unchanged', 'stdlib_unchanged', 'binary_unchanged'))
    assert not audit['outside_modules'] and not audit['unbound_mappings']
assert tests.read_bytes() == (runner / 'check152a_parsing689/source_snapshot/tests/test_flux_balance_evidence_parsing_689.py').read_bytes()
unchanged = []
for line in (packet / 'SOURCE_PINS_BEFORE_001.txt').read_text().splitlines():
    sha, relative = line.split(None, 1)
    relative = relative.strip()
    after = pin(repo / relative)
    unchanged.append({'path': relative, 'before_sha256': sha, 'after': after, 'same_bytes': sha == after['sha256']})

result = {
    'record_type': 'flux_balance_evidence_parsing_689',
    'production': pin(production), 'new_tests': pin(tests), 'baseline': pin(baseline),
    'exact_diff': pin(packet / 'EXACT_CODE_DIFF_001.patch'),
    'source_comparison': unchanged,
    'checks': checks, 'distinct_cases': 73, 'new_cases': 62, 'unchanged_existing_cases': 11,
    'support_file_identity_comparisons': support,
    'verification_resources': {'dependencies_from': str((runner / 'check005/dependencies').relative_to(repo)),
        'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'swap_bytes': 0, 'wall_seconds': None,
        'same_handle_observed_until_terminal_and_quiescent': True},
    'native_solves': 0, 'downloads': 0, 'acquisition': 0,
    'public_signatures_unchanged': True,
    'analytical_authority': ['gene_annotation_episode/flux_balance_sheet.py', 'gene_annotation_episode/flux_balance_calculations.py'],
    'limits': [
        'These are supplied-byte synthetic/TEST-normalized fixtures; no authentic new native branch was executed by689.',
        'Source-audit validation checks typed tree/addresses and identity, not independent XML decoding of the original bytes.',
        'G4 external prior-source authority outside the eight roles remains unresolved; original selected bytes are preserved and unavailable association remains unknown.',
        'No capture host, Store, publication, worker, prompt, requested child return, full episode or live-resource binding is established by these checks.',
        'The separate688 authentic emission report is not included as an executed689 check.',
        'First61 cases used initial new test file; second12 cases only added tests. Production reader identical in both snapshots; no passing case repeated.'
    ],
    'read_trace': ['full original attachment and repeated objective/entire OPERATING PRINCIPLES',
        'AGENTS.md and relevant grader principles/fixed FBA inventory row',
        'full679 contracts001-010 and exact681 RECORD_ADDITIONS_001',
        'complete current reader, shared contracts, sheet and calculator; current canonical digest helper',
        '680/683/684/686 tests and handoffs; relevant679 fixture/parameter consumers',
        'complete pinned Cobra Reaction.update_variable_bounds and current688 before/after configuration consumers',
        'bounded529 run_checks.py and bounded_entry.py'],
}
(packet / 'EVIDENCE_001.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
(packet / 'SOURCE_PINS_AFTER_001.txt').write_text('\n'.join(f"{pin(repo / path)['sha256']}  {path}" for path in (
    'gene_annotation_episode/flux_balance_readers.py', 'gene_annotation_episode/flux_balance_contracts.py',
    'gene_annotation_episode/flux_balance_sheet.py', 'gene_annotation_episode/flux_balance_calculations.py',
    'tests/test_flux_balance_evidence_parsing_689.py')) + '\n')
print(json.dumps({'checks': [{ 'attempt': c['attempt'], 'passed': c['passed_call_count'],
    'scratch_bytes': c['receipt']['metadata']['observed_scratch_bytes']} for c in checks],
    'support_files_unchanged': all(row['same_bytes'] for row in support),
    'production_pin': result['production'], 'new_test_pin': result['new_tests']}))
