"""Root source/receipt/accounting review. Stdlib only; never imports the app."""
from pathlib import Path
import ast
from collections import Counter
import hashlib
import json

REPO = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
RUNS = REPO / 'verification/tool_graders_hmmer_map_verification_2026-10-28_529'


def pin(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(REPO)), 'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data)}


def save(name, value):
    (PACKET / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def methods(path):
    tree = ast.parse(path.read_text())
    client = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'PublicClients')
    return {node.name: ast.dump(node, include_attributes=False) for node in client.body if isinstance(node, ast.FunctionDef)}


attempts = ['check201_native739', 'check202_gene737', 'check203_addgene738',
            'check204_support739', 'check204b_support739', 'check204c_support739', 'check204d_support739']
reviews, latest = [], {}
for name in attempts:
    directory = RUNS / name
    receipt = json.loads((directory / 'receipt.json').read_text())
    assert receipt['terminal'] is True and receipt['quiescent'] is True
    for field in ['source_unchanged', 'dependency_unchanged', 'stdlib_unchanged',
                  'binary_unchanged', 'selected_stdlib_source_unchanged']:
        assert receipt[field] is True, (name, field)
    policy = receipt['metadata']['policy']
    assert policy == {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None}
    assert receipt['returncode'] == {'check201_native739': 4, 'check202_gene737': 0,
        'check203_addgene738': 0, 'check204_support739': 4, 'check204b_support739': 1,
        'check204c_support739': 0, 'check204d_support739': 0}[name]
    audit = json.loads((directory / 'execution_audit.json').read_text())
    reports = [json.loads(line) for line in (directory / 'case_reports.jsonl').read_text().splitlines()]
    calls = [row for row in reports if row['phase'] == 'call']
    if name != 'check201_native739':
        latest.update({row['nodeid']: {'attempt': name, 'outcome': row['outcome']} for row in calls})
    reviews.append({'attempt': name, 'receipt': receipt, 'audit': audit,
                    'case_call_outcomes': dict(Counter(row['outcome'] for row in calls))})

passed = sorted(node for node, record in latest.items() if record['outcome'] == 'passed')
failed = sorted(node for node, record in latest.items() if record['outcome'] != 'passed')
regressions = [node for node in passed if not any(name in node for name in ['test_sequence_support_739.py', 'test_ncbi_gene_native_737.py', 'test_addgene_sequence_native_738.py'])]
assert len(passed) == 178 and len(regressions) == 5 and len(failed) == 1
assert failed[0].endswith('::test_selected_current_nucleotide_capture_through_actual_bounded_client_and_shared_cds_path')
save('CASE_IDS_001.json', {'latest': latest, 'distinct_passed': passed, 'remaining_failed': failed,
    'existing_regressions': regressions, 'new_component_passed': len(passed)-len(regressions),
    'original201_capture_custody_cases_excluded_from_clean_union': 2})

before = methods(RUNS / 'check200c_initial736/source_snapshot/gene_annotation_episode/acquisition.py')
after = methods(REPO / 'gene_annotation_episode/acquisition.py')
changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
assert changed == ['_http', '_read_bounded_response', 'addgene_sequences', 'ncbi_gene', 'ncbi_search', 'ncbi_sequence']
snapshots = []
for relative, attempt in [
    ('gene_annotation_episode/acquisition.py', 'check204d_support739'),
    ('gene_annotation_episode/coding_sequence_support.py', 'check204d_support739'),
    ('gene_annotation_episode/coding_sequence_native.py', 'check204d_support739'),
    ('gene_annotation_episode/ncbi_gene_native.py', 'check202_gene737'),
    ('gene_annotation_episode/addgene_sequence_native.py', 'check203_addgene738'),
    ('tests/test_sequence_support_739.py', 'check204d_support739'),
    ('tests/test_ncbi_gene_native_737.py', 'check202_gene737'),
    ('tests/test_addgene_sequence_native_738.py', 'check203_addgene738'),
]:
    current, snapshot = REPO / relative, RUNS / attempt / 'source_snapshot' / relative
    assert current.read_bytes() == snapshot.read_bytes(), relative
    snapshots.append({'current': pin(current), 'snapshot': pin(snapshot), 'equal': True})
shared = []
for relative in ['gene_annotation_episode/sequence_extraction_grader.py',
                 'gene_annotation_episode/sequence_views.py', 'gene_annotation_episode/sequence_mapping.py',
                 'gene_annotation_episode/genbank_intake.py']:
    current = REPO / relative
    previous = RUNS / 'check200c_initial736/source_snapshot' / relative
    assert current.read_bytes() == previous.read_bytes(), relative
    shared.append(pin(current))
pins = [pin(REPO / path) for path in [
    'gene_annotation_episode/acquisition.py', 'gene_annotation_episode/coding_sequence_support.py',
    'gene_annotation_episode/coding_sequence_native.py', 'gene_annotation_episode/ncbi_gene_native.py',
    'gene_annotation_episode/addgene_sequence_native.py', 'tests/test_sequence_support_739.py',
    'tests/test_ncbi_gene_native_737.py', 'tests/test_addgene_sequence_native_738.py',
    'verification/tool_graders_sequence_support_integration_2026-10-29_739/CONTRACT_001.md',
    'verification/tool_graders_sequence_support_integration_2026-10-29_739/CONTRACT_001_A.md',
    'verification/tool_graders_sequence_support_integration_2026-10-29_739/CONTRACT_001_B.md',
    'verification/tool_graders_sequence_support_integration_2026-10-29_739/review_001.py',
    'verification/tool_graders_ncbi_gene_native_2026-10-29_737/VERIFICATION_001.json',
    'verification/tool_graders_addgene_sequence_native_2026-10-29_738/VERIFICATION_001.json',
]]
save('SOURCE_PINS_001.json', {'pins': pins, 'checked_current_snapshot_pairs': snapshots,
    'unchanged_reused_authorities': shared, 'changed_public_client_methods_only': changed})
remaining = [
    'Original authentic AJ320226.1 input is currently absent at named paths; one explicit new request failed network is unreachable, with no snapshot/bases retained. Actual source-CDS verification remains unproved.',
    'Selected Gene/locus/accession-version/CDS host associations, public ToolInfo, actual resource-child invocation, retained publication, constrained requested returns and saved/closed episode replay remain required.',
    'Mixed-orientation and supplied remote-reference/zero-length CDS modes remain explicitly unavailable in this adapter and require faithful shared extraction support.',
    'Addgene public page supplies three authenticated-download metadata entries, no bases. An authorized access route or supplied sequence files remain pending; no provider fallback.',
    'Original201 unbound NSS mapping remains an audit failure. Prospective parser replay and later NSS selection do not retroactively authorize it.',
    'Production TASK/STEERING decision traces and running feedback remain required. No new template implemented.',
    'All earlier FBA/restriction and R1-R7 requirements remain open; no completed tool/name/group increment.',
]
review = {'kind': 'component_source_and_receipt_review_not_whole_tool_completion',
    'distinct_component_checks_passed': 173, 'existing_regressions_passed': 5,
    'distinct_clean_scope_cases_passed': 178, 'single_fresh178_case_run': False,
    'native_cases': {'Gene': {'records': 1, 'loci': 3, 'locus_commentaries': [11,3,11]},
        'Addgene': {'sequence_ids': ['513490','91118','91449'], 'source_full': 1,
                    'source_partial': 2, 'base_sequences_obtained': 0, 'authentication_required': True}},
    'engineered_native_extraction_example': {'selected_symbol_occurrences': 10,
        'distinct_selected_input_symbols': 7, 'repeated_selected_input_symbols': 3,
        'mismatching_symbols': 0, 'biological_measurement': False},
    'numerical_authority': 'existing sequence_extraction_sheet_v1 / calculate_extraction_scores unchanged',
    'actual_selected_public_acquisition_attempts': 3, 'successful_public_responses_retained': 2,
    'new_successful_authentic_CDS_extractions': 0, 'new_installations': 0,
    'external_model_calls': 0, 'no_runtime_episode_controller_credit_or_prompt_edits': True,
    'whole_tool_increment': 0, 'new_connected_operation_names': 0, 'new_numerical_groups': 0,
    'attempts': reviews, 'remaining': remaining}
save('ROOT_REVIEW_001.json', review)
print(json.dumps({'passed': len(passed), 'new': 173, 'regressions': len(regressions),
    'unresolved_failed': failed, 'source_snapshot_pairs': len(snapshots), 'shared_authorities_unchanged': len(shared),
    'collection_receipts_found': [row['attempt'] for row in reviews if row['receipt'] is not None]}, indent=2))
