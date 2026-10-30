"""Add verification evidence to fixed rows; never redefine the supplied goal."""

raise SystemExit('Historical progress replay is retired; this script does not update current accounting.')
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import os
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
TRACKER = ROOT / 'research/tool_grader_goal_2026-10-24'
STATUS = TRACKER / 'WORK_STATUS.json'
UPDATE = TRACKER / 'PROGRESS_UPDATE_112.json'
assert not UPDATE.exists()
original = STATUS.read_bytes()
assert hashlib.sha256(original).hexdigest() == '5986fce57a3701eb92d77e8ef55e45c4cdc9c560eff6dd904c8f9a6d45d6d40e'
current = json.loads(original)
before = deepcopy(current)
previous = json.loads((TRACKER / 'PROGRESS_UPDATE_111.json').read_text())
scope_before = (TRACKER / 'SCOPE.json').read_bytes()
assert len(current['rows']) == 308 and len(current['resource_bindings']) == 288
rows = {r['id']: r for r in current['rows']}
assert len(rows) == 308


def pin(path):
    path = ROOT / path
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}


def checked_attempt(path):
    base = ROOT / 'verification' / path
    receipt = json.loads((base / 'receipt.json').read_text())
    assert receipt['terminal'] and receipt['quiescent']
    pins = {k: v for k, v in receipt.items() if 'unchanged' in k}
    assert pins and all(v is True for v in pins.values())
    doc = ET.fromstring((base / 'junit.xml').read_bytes())
    suites = [doc] if doc.tag == 'testsuite' else list(doc.iter('testsuite'))
    counts = {k: sum(int(s.get(k, '0')) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    counts['passed'] = counts['tests'] - counts['failures'] - counts['errors'] - counts['skipped']
    return {'attempt': path, 'returncode': receipt['returncode'], 'terminal': True, 'quiescent': True,
        'unit': receipt['unit'], 'pin_checks': pins, **counts}


nmf_note = ('484/check003 passed55 numerical/native checks with actual scikit-learn1.7.2 fits and preserved native warnings, '
    'complete arrays, positional metadata and saved numerical calculations. Root488/check002 passed4 actual local-resource '
    'episode, monitoring, original-attempt and closed-replay cases; the selected matrix was fitted once, '
    'SSE1.9138191182688943e-08, native residual0.0001383408514600178 and derived residual0.00013834085146004034. '
    '488/shared001 passed5 actual library/schema/received-input/frozen-prefix and metadata-version cases. '
    'All receipts are terminal/quiescent with unchanged recorded source/dependency/interpreter/stdlib pins. '
    '488/check001 failed before test execution because its numerical-only dependency environment lacked Bio; it remains recorded. '
    'Shared result dispatch, typed facts, received-reference protection/admission, credit, completion and result information '
    'are written.489 result/custody refinements and490 complete scientific-parent Workflow verification remain in progress; '
    'these component/resource passes do not establish the full typed-return path or add this row to the tally. '
    'Message review and HPC deployment remain unfinished. No W05/literature changes.')
atac_note = ('478/check005 completed3 of4 full Workflow checks; native measurements, requested typed returns, saved-only '
    'recalculation and gains7/3/2/0 passed, but closed replay reread deleted BAM bytes.487 extracted exact received-input '
    'metadata validation;21 focused checks passed, including actual missing/tampered staging with all MACS2 steps not_run. '
    'Current-source replay rejected an unrelated changed scientific-binding implementation.487/replay003 then passed the '
    'retained original Workflow replay using authenticated478 sources plus only that correction:6 episodes,8 actions,8 '
    'observations and all saved forms/history unchanged,43 removed paths still absent,zero new native work/decisions. '
    'Original failed receipts were not overwritten. Root later added NMF handling to the helper; that addition is outside '
    '487 verification. Final root acceptance/current integration and message work remain open; no tally increment here.')
bv_note = ('Root480/check011 restored the actual native test fixtures and reran148 previously missing-fixture nodes:146 '
    'passed and2 failed because their redelivery fixtures supplied an empty original request. Those two test fixtures '
    'were corrected to record the actual closed request/return contract;480/check012 passed both. All original terminal '
    'receipts and pins are retained. Together with earlier308 baseline passes and2 corrected positive cases this covers '
    'the original458 nodes across separately pinned runs, not one combined458-test pass. The additional original-request '
    'rejection case remains separate. This repairs already-counted BV-BRC consumers and adds no new tool. Live service '
    'execution and other fixed resource/native-format work remain unfinished.')

specs = [
    ('NMF-COMPONENT-RESOURCE-SHARED-112', nmf_note,
        ['tool_graders_expression_nmf_native_grader_2026-10-27_484/check003',
         'tool_graders_expression_nmf_integration_2026-10-27_488/check001',
         'tool_graders_expression_nmf_integration_2026-10-27_488/check002',
         'tool_graders_expression_nmf_integration_2026-10-27_488/shared001']),
    ('ATAC-RECEIVED-INPUT-REPLAY-112', atac_note,
        ['tool_graders_atac_episode_path_2026-10-27_478/check005',
         'tool_graders_atac_input_identity_replay_2026-10-27_487/check001',
         'tool_graders_atac_input_identity_replay_2026-10-27_487/replay003']),
    ('BVBRC-ORIGINAL-CONTRACT-FIXTURES-112', bv_note,
        ['tool_graders_bvbrc_compact_return_consumers_2026-10-27_480/check011',
         'tool_graders_bvbrc_compact_return_consumers_2026-10-27_480/check012']),
]
added = []
for key, summary, attempts in specs:
    assert not any(e['id'] == key for e in current['verification_evidence'])
    evidence = {'id': key, 'kind': 'verified_scoped_implementation_evidence', 'summary': summary,
        'checks': [checked_attempt(p) for p in attempts],
        'reports': [pin('verification/' + p + '/' + name) for p in attempts for name in ('receipt.json', 'junit.xml')]}
    current['verification_evidence'].append(evidence)
    added.append(evidence)

nmf = rows['B-L128-perform_gene_expression_nmf_analysis']
nmf.update(overall='numerical_native_and_resource_checks_passed_full_typed_Workflow_in_progress',
    source_presence='actual_native_and_numerical_implementation_present',
    tool_information='actual_local_name_description_resources_instructions_and_commission_route_verified',
    invocation_contract='selected_local_resource_episode_original_attempt_verified',
    numerical_sheet='complete_input_prepared_factors_native_diagnostics_and_separate_components_verified',
    native_parser='exact_native_five_file_formats_original_input_and_ordered_axes_verified',
    metadata_extractor='positional_gene_sample_conditions_replicates_and_unknowns_preserved',
    deterministic_calculator='residuals_SSE_norms_loadings_contributions_fractions_and_saved_recalculation_verified',
    production_result_binding='shared_result_dispatch_return_credit_and_completion_written_full_Workflow_in_progress',
    numerical_verification='55_component_checks_and_actual_selected_resource_numeric_example_passed',
    integration_verification='4_resource_episode_and5_shared_catalog_input_schema_checks_passed_full_path_in_progress',
    live_resource_verification='actual_local_NMF_selected_fit_verified_full_parent_return_pending')
nmf['evidence_ids'].append(specs[0][0])
nmf['note'] += ' Update112: ' + nmf_note
atac = rows['B-L125-analyze_atac_seq_differential_accessibility']
atac['integration_verification'] = '3_original_full_Workflow_checks_and_separate_narrow_fixed_closed_replay_passed_final_review_pending'
atac['evidence_ids'].append(specs[1][0]); atac['note'] += ' Update112: ' + atac_note
bv_ids = ('C-L190-Homology','C-L193-CodonTree','C-L194-GeneTree','C-L202-GenomeAlignment',
    'C-L204-MSA','C-L205-MetaCATS','C-L206-GenomeComparison','C-L207-ComparativeSystems','C-L209-FastqUtils')
for key in bv_ids:
    row = rows[key]
    row['evidence_ids'].append(specs[2][0]); row['note'] += ' Update112: ' + bv_note
for row in current['resource_bindings']:
    if row['id'] == nmf['id'] + '::local':
        row.update(invocation_contract='selected_original_local_NMF_episode_verified',
            production_result_binding='shared_result_consumer_wiring_written_full_delivery_in_verification',
            integration_verification='4_actual_resource_and5_shared_checks_passed_full_scientific_parent_path_pending',
            live_resource_verification='one_actual_local_sklearn_fit_in_resource_episode_verified',
            prerequisites_present='pinned_sklearn_1_7_2_native_environment_executed',
            native_format_observed='five_full_native_NMF_files_with_X_W_H_diagnostics_and_manifest')
        row['evidence_ids'].append(specs[0][0])
assert (TRACKER / 'SCOPE.json').read_bytes() == scope_before
assert current['complete_scientific_tools_claimed'] == 0
assert [r['id'] for r in current['rows']] == [r['id'] for r in before['rows']]
assert [r['id'] for r in current['resource_bindings']] == [r['id'] for r in before['resource_bindings']]
raw = (json.dumps(current, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
changes = [{'id': a['id'], 'before': a, 'after': b} for a,b in zip(before['rows'],current['rows']) if a != b]
resource_changes = [{'id': a['id'], 'before': a, 'after': b}
    for a,b in zip(before['resource_bindings'],current['resource_bindings']) if a != b]
update = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-27', 'author': 'root',
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'previous_status_sha256': hashlib.sha256(original).hexdigest(), 'new_status_sha256': hashlib.sha256(raw).hexdigest(),
    'scope_sha256_unchanged': hashlib.sha256(scope_before).hexdigest(), 'scope_changes': [],
    'changes': changes, 'resource_binding_changes': resource_changes, 'added_evidence': added,
    'numerical_grader_progress_tally': {**deepcopy(previous['numerical_grader_progress_tally']),
        'before':112, 'after':112, 'added_row_ids':[]},
    'verified_bound_local_tool_mode_rows': {'before':42,'after':42}, 'remaining_fixed_rows_outside_tally':196,
    'completed_work':[nmf_note,atac_note,bv_note],
    'findings_requiring_repair':[
        'NMF full original-to-received typed-return path and final result/custody refinement tests remain unfinished.',
        'ATAC final root acceptance and current integration qualification remain unfinished.',
        'Chromatin481 original current-snapshot suites remain live; final receipt acceptance is pending.',
        'Earlier native-format/resource/message and fixed tool/mode work remain open.'],
    'work_item_states':deepcopy(previous['work_item_states']),
    'unfinished_work':[*deepcopy(previous['unfinished_work']),nmf_note,atac_note],
    'inventory_maintenance_counted_as_implementation_progress':False,
    'specific_pending_NCBI_job_verification_included':False, 'complete_scientific_tools_claimed':0,
    'previous_goal_turn_classification':'no_progress_status_report_only',
    'this_goal_turn_progress':'implemented_NMF_shared_result_consumers_and_verified_selected_native_resource_and_shared_boundaries'}
with UPDATE.open('x') as f: json.dump(update,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
assert STATUS.read_bytes() == original
pending=STATUS.with_name('WORK_STATUS.update112.pending')
with pending.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
os.replace(pending,STATUS)
print(json.dumps({'update':112,'changed_tool_rows':len(changes),'changed_resource_rows':len(resource_changes),
    'tally':112,'total':308,'new_status_sha256':hashlib.sha256(raw).hexdigest()}))
