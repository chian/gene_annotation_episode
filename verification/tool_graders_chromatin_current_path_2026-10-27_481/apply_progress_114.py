"""Record completed numerical review and separately scoped barcode progress."""

raise SystemExit('Historical progress replay is retired; this script does not update current accounting.')
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'research/tool_grader_goal_2026-10-24'
STATUS = BASE / 'WORK_STATUS.json'
UPDATE = BASE / 'PROGRESS_UPDATE_114.json'
EXPECTED = '2247e462eb1188f90915adc9d43044e3eea7dc17adce39fda9bd18c502fedff3'
PACKET = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def pin(path):
    path = ROOT / path
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), sha256=digest(data), size_bytes=len(data))


def checked(directory, passed):
    receipt = json.loads((directory / 'receipt.json').read_text())
    assert receipt['returncode'] == 0 and receipt['terminal'] and receipt['quiescent']
    unchanged = {k: v for k, v in receipt.items() if k.endswith('_unchanged')}
    assert unchanged and all(v is True for v in unchanged.values())
    tests = ET.parse(directory / 'junit.xml').findall('.//testcase')
    assert len(tests) == passed
    assert not any(t.find(kind) is not None for t in tests for kind in ('failure', 'error', 'skipped'))
    return dict(directory=str(directory.relative_to(ROOT)), passed=passed,
                unit=receipt['unit'], terminal=True, quiescent=True, returncode=0,
                pin_checks=unchanged,
                evidence=[pin(directory / name) for name in ('receipt.json', 'junit.xml')])


raw = STATUS.read_bytes()
assert digest(raw) == EXPECTED and not UPDATE.exists()
old = json.loads(raw)
new = deepcopy(old)
previous = json.loads((BASE / 'PROGRESS_UPDATE_113.json').read_text())
scope_sha = digest((BASE / 'SCOPE.json').read_bytes())
assert scope_sha == previous['scope_sha256_unchanged']
assert len(new['rows']) == 308 and len(new['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 113
assert new['verified_bound_local_tool_mode_rows'] == 43

checks = [checked(PACKET / name, 7) for name in ('cooler002', 'hic001')]
modules = sorted((ROOT / 'gene_annotation_episode').glob('*chromatin*.py'))
assert len(modules) == 26
source_comparison = []
for module in modules:
    for name in ('cooler002', 'hic001'):
        frozen = PACKET / name / 'source_snapshot' / 'gene_annotation_episode' / module.name
        assert module.read_bytes() == frozen.read_bytes(), str(module)
    source_comparison.append(pin(module) | {'matches_both_executed_snapshots': True})

chromatin_summary = (
    'Root completed the numerical sheet/metadata/calculator/projection review. '
    'All26 chromatin modules match both481 executed source snapshots. '
    'The already-recorded7 Cooler and7 HIC full Workflow passes establish the declared contact-enrichment paths; '
    'no tests were rerun or newly added by this review. Raw6/mean4/fold1.5 and divisive6/mean3.25/fold24/13 '
    'remain the checked examples. Saved recalculation, partial/zero data, requested-only returns, original '
    'action credit, exact terminal-zero expectations and closed replay remain verified at those snapshots. '
    'This adds one numerical grader/local binding to the existing tally, not a complete-tool claim. '
    'Full episode insulation/weighted-Cooler coverage, messages/received operands, biological/further native '
    'coverage and HPC/API remain; later shared additions and historical failures stay explicitly separate.')
chromatin_evidence = dict(id='CHROMATIN-NUMERICAL-REVIEW-114',
    kind='root_review_of_existing_verified_implementation', summary=chromatin_summary,
    existing_checks=checks, new_test_runs=0, source_comparison=source_comparison,
    reports=[pin(PACKET / name) for name in ('ROOT_NUMERICAL_REVIEW_001.md', 'HANDOFF.md',
        'HANDOFF.json', 'CHECKED_CASES.json', 'SHARED_CONSUMER_COMPARISON_LATER.json')])

barcode_directory = ROOT / 'verification/tool_graders_barcode_numerical_2026-10-27_491'
barcode_check = checked(barcode_directory / 'check003', 59)
barcode_summary = (
    'Fresh491 implemented numerical records/parsers/metadata/calculators/projections against486/491 interfaces; '
    'latest bounded check003 passed59 at its immutable snapshot, including sheet-manifest and strict-decoding '
    'refinements. Earlier50/54 passes remain separate snapshots, not additional distinct tests. Root final '
    'component review remains pending. Fresh492 native modules/tests '
    'are written and verification is ongoing. Native/result custody/shared integration and complete Workflow '
    'remain unfinished. No barcode row or binding is added to the numerical tally.')
barcode_evidence = dict(id='BARCODE-PARTIAL-COMPONENTS-114',
    kind='partial_implementation_evidence', summary=barcode_summary,
    checks=[barcode_check], reports=[pin(barcode_directory / 'FROZEN_PUBLIC_PORTS.md')])

rows = {r['id']: r for r in new['rows']}
chromatin = rows['B-L124-analyze_chromatin_interactions']
chromatin.update(overall='numerical_grader_and_declared_local_episode_path_verified',
    numerical_sheet='implemented_reviewed_native_and_saved_numerical_fields_verified',
    metadata_extractor='implemented_reviewed_occurrence_reference_sample_and_population_joins_verified',
    deterministic_calculator='contact_and_insulation_components_reviewed_native_component_checks_passed',
    production_result_binding='declared_Cooler_and_HIC_contact_paths_and_saved_requested_returns_verified')
chromatin['evidence_ids'].append(chromatin_evidence['id'])
chromatin['note'] += ' Update114: ' + chromatin_summary
barcode = rows['B-L130-analyze_barcode_sequencing_data']
barcode.update(overall='numerical_and_native_implementation_in_progress',
    source_presence='upstream_source_inspected_corrected_replacement_modules_written',
    tool_information='local_information_written_verification_pending',
    invocation_contract='frozen_native_contract_written_verification_pending',
    numerical_sheet='implemented_59_test_snapshot_passed_root_review_pending',
    native_parser='implemented_59_test_snapshot_passed_root_review_pending',
    metadata_extractor='implemented_59_test_snapshot_passed_root_review_pending',
    deterministic_calculator='implemented_59_test_snapshot_passed_root_review_pending',
    production_result_binding='not_yet_implemented',
    numerical_verification='59_latest_snapshot_component_tests_passed_root_review_pending',
    integration_verification='not_yet_verified', live_resource_verification='native_verification_in_progress')
barcode['evidence_ids'].append(barcode_evidence['id'])
barcode['note'] += ' Update114: ' + barcode_summary
binding = next(r for r in new['resource_bindings'] if r['id'] == chromatin['id'] + '::local')
binding['production_result_binding'] = chromatin['production_result_binding']
binding['evidence_ids'].append(chromatin_evidence['id'])
new['verified_bound_local_tool_mode_rows'] = 44
new['verification_evidence'].extend([chromatin_evidence, barcode_evidence])
assert new['complete_scientific_tools_claimed'] == 0
assert [r['id'] for r in new['rows']] == [r['id'] for r in old['rows']]
assert [r['id'] for r in new['resource_bindings']] == [r['id'] for r in old['resource_bindings']]

body = encode(new)
update = deepcopy(previous)
update.update(recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=EXPECTED,
    new_status_sha256=digest(body),
    changes=[dict(id=b['id'], before=a, after=b) for a, b in zip(old['rows'], new['rows']) if a != b],
    resource_binding_changes=[dict(id=b['id'], before=a, after=b)
        for a, b in zip(old['resource_bindings'], new['resource_bindings']) if a != b],
    added_evidence=[chromatin_evidence, barcode_evidence],
    numerical_grader_progress_tally=dict(before=113, after=114,
        added_row_ids=[chromatin['id']], meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=43, after=44), remaining_fixed_rows_outside_tally=194,
    completed_work=[chromatin_summary], partial_work=[barcode_summary],
    findings_requiring_repair=[
        'NMF complete scientific-parent Workflow remains on its original490 handle; not yet counted.',
        'Barcode final numerical/native checks and result custody/shared/full Workflow integration remain.',
        'Chromatin full episode insulation/weighted-Cooler coverage, messages/received operands and other native/resources remain.',
        'ATAC messages, further modes/formats and resources remain.',
        'All other fixed308 rows/resource bindings and earlier unfinished obligations remain.'],
    previous_goal_turn_classification=previous['this_goal_turn_progress'],
    this_goal_turn_progress='completed_chromatin_numerical_review_accepted_declared_paths_recorded_barcode_component_implementation')
for item in update['work_item_states']:
    if item['id'] == 'U05':
        item['current_evidence'] += ' Update114: ' + chromatin_summary + ' ' + barcode_summary
assert [(r['id'], r['status']) for r in update['work_item_states']] == [(r['id'], r['status']) for r in previous['work_item_states']]
update['unfinished_work'].append(
    'Update114 supersedes only current-status wording: chromatin numerical review and declared contact paths accepted; '
    'its remaining modes/messages/resources stay open. NMF full Workflow and barcode complete integration remain. '
    'Fixed308 rows/288 bindings preserved;114 numerical graders,44 verified local rows,194 outside tally.')
assert digest(STATUS.read_bytes()) == EXPECTED
assert digest((BASE / 'SCOPE.json').read_bytes()) == scope_sha
with UPDATE.open('xb') as stream:
    stream.write(encode(update))
temporary = BASE / '.WORK_STATUS.progress114.tmp'
with temporary.open('xb') as stream:
    stream.write(body)
temporary.replace(STATUS)
assert digest(STATUS.read_bytes()) == update['new_status_sha256']
print(json.dumps(dict(progress_update=114, numerical_graders=114, total_fixed_rows=308,
    verified_local_rows=44, remaining_outside_tally=194, scope_unchanged=True,
    status_sha256=update['new_status_sha256'])))
