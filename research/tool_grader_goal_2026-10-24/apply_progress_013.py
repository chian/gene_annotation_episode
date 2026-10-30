"""Append verified repairs and contradictory full-path evidence; preserve scope."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = HERE / 'WORK_STATUS.json'
raw = path.read_bytes()
prior = json.loads((HERE / 'PROGRESS_UPDATE_012.json').read_text())
before_hash = hashlib.sha256(raw).hexdigest()
assert before_hash == prior['new_status_sha256']
assert not (HERE / 'PROGRESS_UPDATE_013.json').exists()
work = json.loads(raw)
old = deepcopy(work)
evidence = []


def add(identity, passed, failed, summary, qualification, paths):
    assert identity not in {row['id'] for row in work['verification_evidence']}
    reports = [{'path': name, 'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
               for name in paths]
    evidence.append({'id': identity, 'kind': 'component_or_path_verification',
        'passed': passed, 'failed': failed, 'summary': summary,
        'qualification': qualification, 'reports': reports})


add('BVBRC-HOMOLOGY-INSTALLED-SUBJECT-REPAIR', 1, 0,
    'Isolated wheel verifies both scientific modes, original-reference conflict rejection, E-value independence and offline recalculation.',
    'One recorded verification script, not a full installed Workflow. The scientific adapter pin is 6431e9b48d60; this wheel predates the later two execution-binding repairs.',
    ['verification/tool_graders_bvbrc_homology_packaging_2026-10-24_002/verification.json'])
add('BVBRC-HOMOLOGY-PARTIAL-PROJECTION-002', 2, 0,
    'Unproved pairwise reference retains real native hit counts and raw data; unrequested pairwise facts do not invalidate a requested native count.',
    'Focused synthetic supplied-data cases, not full execution or live service verification.',
    ['verification/tool_graders_bvbrc_homology_subject_binding_2026-10-24/partial-projection-followup.result.json',
     'verification/tool_graders_bvbrc_homology_subject_binding_2026-10-24/partial-projection-followup.log'])
add('BVBRC-HOMOLOGY-ORDER-DEFECT', 75, 2,
    'Full pairwise run confirmed valid final .6/.6/3/1 calculation but admitted earlier null values because hashed directory order was treated as chronology.',
    '28m57s controlled Workflow completed 16 observations and four admissions; two actual return assertions failed. Replay was not reached. Original records and provenance correction are retained. Repaired full rerun is pending.',
    ['verification/tool_graders_bvbrc_homology_pairwise_workflow_2026-10-24/integrated-order-defect-summary.json',
     'verification/tool_graders_bvbrc_homology_pairwise_workflow_2026-10-24/pytest-integrated-order-defect.xml'])
add('BVBRC-API-BINDING-REPAIRS-022', 22, 0,
    'Applied chronological action enumeration and role-scoped support forwarding; six focused regressions and sixteen existing recovery/MinHash cases pass.',
    'Twenty-two distinct cases across candidate and corrected-fixture runs, not a single all-green invocation. The first ordering fixture omitted the mandatory trailing newline; corrected before/after evidence is explicit. No method_loop or scientific-score edit.',
    ['verification/tool_graders_bvbrc_binding_repairs_2026-10-24/README.md',
     'verification/tool_graders_bvbrc_binding_repairs_2026-10-24/candidate-regressions.json',
     'verification/tool_graders_bvbrc_binding_repairs_2026-10-24/candidate-regressions.log',
     'verification/tool_graders_bvbrc_binding_repairs_2026-10-24/original-corrected-fixture.log',
     'verification/tool_graders_bvbrc_binding_repairs_2026-10-24/production-focused.json',
     'verification/tool_graders_bvbrc_binding_repairs_2026-10-24/production-focused.log'])
add('BVBRC-APPSERVICE-TRANSFER-WORKFLOW-004', 4, 0,
    'Full material.parse, preparation, Workspace creation, exact-byte upload, submission, typed support/handoff return and reopened Workflow replay pass.',
    'Four tests in 85.36s used controlled native responses and an isolated candidate. All 299 candidate package files match applied production. Original 60 bytes retained; gains [0,0,0,2], then exact zero. No live service or scientific execution claim.',
    ['verification/tool_graders_bvbrc_appservice_transfer_workflow_2026-10-24/RESULTS.json',
     'verification/tool_graders_bvbrc_appservice_transfer_workflow_2026-10-24/README.md',
     'verification/tool_graders_bvbrc_appservice_transfer_workflow_2026-10-24/candidate-production-byte-comparison.json',
     'verification/tool_graders_bvbrc_appservice_transfer_workflow_2026-10-24/pytest-candidate.log'])

rows = {row['id']: row for row in work['rows']}
bindings = {row['id']: row for row in work['resource_bindings']}
scientific = ['C-L190-Homology', 'C-L226-parsing-and-grading', 'C-L227-return']
for identity in scientific:
    row = rows[identity]
    row['overall'] = 'prior_database_paths_verified_ordering_defect_repaired_full_pairwise_rerun_pending'
    row['production_result_binding'] = 'native_sheet_components_and_typed_returns_bound_chronological_selection_repaired'
    row['numerical_verification'] = 'prior_components_preserved_repaired_subject_wheel_and_two_partial_projection_cases_verified'
    row['integration_verification'] = 'prior_database_paths_preserved_pairwise_stale_return_reproduced_repaired_full_rerun_pending'
    row['evidence_ids'] = list(dict.fromkeys([*row['evidence_ids'], *[item['id'] for item in evidence]]))
    row['note'] += (' Update013: final pairwise numbers were correct but two full-run assertions failed because '
        'the binding returned an older partial result. This contradicts any general complete-return claim; '
        'the passing older database runs remain facts at their original pins. Action ordering is repaired, '
        'six focused cases and sixteen existing regressions pass, and the full pairwise rerun is pending. '
        'Support-return collision is separately repaired and the complete create/upload/submit/parent/replay '
        'path passes four tests. Installed scientific-component verification and two partial-value checks '
        'also pass. Live deployment, other applications and goal-wide completion remain unverified.')

for identity in ['C-L221-preparation', 'C-L222-submission', 'C-L225-input-transfer']:
    row = rows[identity]
    row['integration_verification'] = 'full_original_bytes_create_upload_submit_typed_parent_support_and_reopened_replay_verified'
    if identity == 'C-L225-input-transfer':
        row['overall'] = 'selected_input_transfer_and_complete_typed_Workflow_verified_live_unverified'
        row['production_result_binding'] = 'original_ContentBinding_bytes_to_created_Shock_node_and_original_submit_evidence_verified'
    row['evidence_ids'] = list(dict.fromkeys([*row['evidence_ids'], evidence[3]['id'], evidence[4]['id']]))
    row['note'] += (' Update013: four complete Workflow cases verify exact original 60-byte upload, one '
        'create/upload/submit, wrong-kind receipt rejection with no extra effect or observation, three '
        'support receipts plus one handoff returned through API/launch, terminal zero, and reopened replay. '
        'The support-field collision was repaired in the binding. Candidate execution is byte-identical '
        'to all 299 applied production package files; no live-resource claim.')

row = rows['C-L224-artifact-acquisition']
row['integration_verification'] = 'prior_database_paths_verified_pairwise_chronological_return_repair_full_rerun_pending'
row['evidence_ids'] = list(dict.fromkeys([*row['evidence_ids'], evidence[2]['id'], evidence[3]['id']]))
row['note'] += (' Update013: acquisition retained correct final pairwise numerical values, but return '
    'selection used an older partial publication. Chronological enumeration is repaired; the full '
    'pairwise rerun is pending. No saved acquisition or historical report was rewritten.')

changed_ids = {*scientific, 'C-L221-preparation', 'C-L222-submission', 'C-L224-artifact-acquisition', 'C-L225-input-transfer'}
for identity in changed_ids:
    row, binding = rows[identity], bindings[identity + '::api']
    for key in ('invocation_contract', 'production_result_binding', 'integration_verification', 'live_resource_verification'):
        binding[key] = row[key]
    binding['evidence_ids'] = deepcopy(row['evidence_ids'])

work['verification_evidence'].extend(evidence)
assert len(work['rows']) == len(old['rows']) == 308
assert len(work['resource_bindings']) == len(old['resource_bindings']) == 288
assert work['complete_scientific_tools_claimed'] == old['complete_scientific_tools_claimed'] == 0
changes = []
for group in ('rows', 'resource_bindings'):
    original = {row['id']: row for row in old[group]}
    assert set(original) == {row['id'] for row in work[group]}
    for row in work[group]:
        if row != original[row['id']]:
            changes.append({'group': group, 'id': row['id'], 'before': original[row['id']], 'after': deepcopy(row)})
after = (json.dumps(work, indent=2) + '\n').encode()
update = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-24',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': before_hash, 'new_status_sha256': hashlib.sha256(after).hexdigest(),
    'changes': changes, 'added_evidence': evidence, 'scope_changes': False,
    'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_013.json').open('x') as record:
    record.write(json.dumps(update, indent=2) + '\n')
path.write_bytes(after)
print(json.dumps({'checkpoint': 13, 'changes': len(changes), 'added_evidence': len(evidence),
    'scope_rows': 308, 'resource_bindings': 288, 'complete_scientific_tools_claimed': 0,
    'new_status_sha256': update['new_status_sha256']}))
