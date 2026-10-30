"""Append verified boundaries without changing fixed scope or earlier results."""
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
prior = json.loads((HERE / 'PROGRESS_UPDATE_011.json').read_text())
before_hash = hashlib.sha256(raw).hexdigest()
assert before_hash == prior['new_status_sha256']
assert not (HERE / 'PROGRESS_UPDATE_012.json').exists()
work = json.loads(raw)
old = deepcopy(work)
evidence = []

def add(identity, passed, summary, qualification, paths):
    reports = [{'path': name, 'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()} for name in paths]
    assert identity not in {row['id'] for row in work['verification_evidence']}
    evidence.append({'id': identity, 'kind': 'implemented_component_or_path_verification',
        'passed': passed, 'failed': 0, 'summary': summary, 'qualification': qualification, 'reports': reports})

add('BVBRC-APPSERVICE-MONITOR-HANDLE-031', 31,
    'Assigned and recursive monitor handle custody verified;31 distinct new cases pass across initial/followup runs;72 existing regressions pass separately.',
    'Initial30 pass plus1 wrong exception-message assertion; corrected exact structured diagnostic passed.72 overlap earlier native monitor/host evidence. No live execution.',
    ['docs/verification/tool_graders_bvbrc_monitor_handle_binding_2026-10-24/verification-results.json',
     'docs/verification/tool_graders_bvbrc_monitor_handle_binding_2026-10-24/README.md'])
add('BVBRC-HOMOLOGY-WORKFLOW-003', 3,
    'Complete ordinary Homology Workflow and saved replay passed3 tests:3 hits,.60/.75 coverage,15 decisions/actions/observations,4 admitted returns,partial preservation and offline recalculation.',
    'Synthetic native responses and scripted choices at preserved pin0e12e3f2bf4a. Final657.93s suite passes; earlier replay assertion compared service outcome to runtime-added snapshot. No live/detached/configured-model claim.',
    ['verification/tool_graders_bvbrc_homology_workflow_2026-10-24/passed-pin-0e12e3f2bf4a.pytest-result.json',
     'verification/tool_graders_bvbrc_homology_workflow_2026-10-24/passed-pin-0e12e3f2bf4a-examples/numerical-example.json',
     'verification/tool_graders_bvbrc_homology_workflow_2026-10-24/README.md'])
add('BVBRC-HOMOLOGY-COMPOSED-WORKFLOW-004', 4,
    'Real library selection,three-slot scientific construction,launch/API/results and requested numerical return to root passed4 tests;15 actions/observations and4 admissions.',
    'Controlled native responses at previous pin; root receives only3 measurement rows. Test-source differences after import are separately retained. No live/model/detached/restart proof;pairwise path separate.',
    ['verification/tool_graders_bvbrc_homology_composed_workflow_2026-10-24/ACTUAL_RUN_SUMMARY.json',
     'verification/tool_graders_bvbrc_homology_composed_workflow_2026-10-24/pytest-result-001.json',
     'verification/tool_graders_bvbrc_homology_composed_workflow_2026-10-24/TEST-SOURCE-SCOPE.json'])
add('BVBRC-HOMOLOGY-SUBJECT-BINDING-158', 158,
    'Pairwise subject now joined to original submitted reference FASTA/member/inventory/native ID;76 adapter+71 association+11 library cases passed at repaired pin6431e9b48d60.',
    'Synthetic pure/native-shaped fixtures. Earlier subject-digest counterexample is retained. Full corrected pairwise Workflow and new installed-wheel verification still running;existing database complete paths retained at prior pin.',
    ['verification/tool_graders_bvbrc_homology_subject_binding_2026-10-24/integrated-tests.result.json',
     'verification/tool_graders_bvbrc_homology_subject_binding_2026-10-24/integrated-tests.log',
     'verification/tool_graders_bvbrc_homology_subject_binding_2026-10-24/README.md',
     'verification/tool_graders_bvbrc_homology_pairwise_workflow_2026-10-24/pure-proof-gap-before-repair.json',
     'verification/tool_graders_bvbrc_homology_pairwise_workflow_2026-10-24/pure-proof-gap-after-repair.json'])

rows = {row['id']: row for row in work['rows']}
bindings = {row['id']: row for row in work['resource_bindings']}
identities = ['C-L190-Homology','C-L221-preparation','C-L222-submission','C-L223-status',
    'C-L224-artifact-acquisition','C-L225-input-transfer','C-L226-parsing-and-grading','C-L227-return']
for identity in identities:
    row = rows[identity]
    if identity == 'C-L223-status':
        row['evidence_ids'] = list(dict.fromkeys([*row['evidence_ids'], evidence[0]['id']]))
        row['note'] += ' Update012:31 monitor-handle boundary cases and72 overlapping regressions verify the actual original selection/custody; method_loop was not changed.'
    elif identity in {'C-L221-preparation','C-L222-submission','C-L224-artifact-acquisition'}:
        row['integration_verification'] = 'ordinary_and_composed_Homology_database_Workflow_native_to_requested_parent_numbers_verified'
        row['evidence_ids'] = list(dict.fromkeys([*row['evidence_ids'], evidence[1]['id'], evidence[2]['id']]))
        row['note'] += ' Update012: original selected preparation/submission/acquisition now verified through actual Homology numerical delivery and composed library-to-root path with synthetic native responses.'
    elif identity == 'C-L225-input-transfer':
        continue  # Full create/upload path was not run; do not imply new proof.
    else:
        if identity == 'C-L190-Homology':
            row.update(overall='database_episode_paths_verified_pairwise_subject_repaired_full_pairwise_verification_running',
                metadata_extractor='explicit_native_query_function_taxon_source_population_mappings_plus_original_pairwise_reference_association',
                production_result_binding='selected_database_native_artifact_sheet_calculations_and_typed_parent_root_delivery_verified_pairwise_binding_repaired',
                numerical_verification='prior369_component_and_package_evidence_plus158_repaired_adapter_subject_library_cases',
                integration_verification='ordinary_database3_and_composed_database4_pass_pairwise_composed_running')
        else:
            row.update(overall='MinHash_and_Homology_database_paths_verified_pairwise_repair_testing_other_applications_unfinished',
                production_result_binding='MinHash_prior_verified_and_Homology_database_numeric_parent_root_returns_verified',
                numerical_verification='prior_MinHash_Homology_components_plus158_repaired_subject_adapter_library_cases',
                integration_verification='MinHash_prior_paths_preserved_Homology_database_ordinary_and_composed_paths_verified_pairwise_running')
        row['evidence_ids'] = list(dict.fromkeys([*row['evidence_ids'], *[item['id'] for item in evidence[1:]]]))
        row['note'] += ' Update012: ordinary database Workflow3 tests and composed scientific/library Workflow4 tests passed with3 hits,.60/.75 coverage and15 actions/observations each. Earlier numeric-reference admission defect is repaired. A separate pairwise digest counterexample exposed a real original-reference association gap; new pure validation is connected and158 component/library tests pass. Full pairwise Workflow and fresh installed package are running, not yet claimed. Earlier runs retain original pins and observations;live deployment and other named application graders remain unfinished.'
    binding = bindings[identity+'::api']
    for key in ('invocation_contract','production_result_binding','integration_verification','live_resource_verification'):
        binding[key] = row[key]
    binding['evidence_ids'] = deepcopy(row['evidence_ids'])

work['verification_evidence'].extend(evidence)
assert len(work['rows']) == len(old['rows']) == 308
assert len(work['resource_bindings']) == len(old['resource_bindings']) == 288
assert work['complete_scientific_tools_claimed'] == old['complete_scientific_tools_claimed'] == 0
changes = []
for group in ('rows','resource_bindings'):
    original = {row['id']: row for row in old[group]}
    assert set(original) == {row['id'] for row in work[group]}
    for row in work[group]:
        if row != original[row['id']]:
            changes.append({'group':group,'id':row['id'],'before':original[row['id']],'after':deepcopy(row)})
after = (json.dumps(work,indent=2)+'\n').encode()
update = {'schema':'tool_grader_progress_update_v1','date':'2026-10-24',
    'recorded_at':datetime.now(timezone.utc).isoformat(),'author':'root',
    'previous_status_sha256':before_hash,'new_status_sha256':hashlib.sha256(after).hexdigest(),
    'changes':changes,'added_evidence':evidence,'scope_changes':False,
    'specific_pending_NCBI_job_verification_included':False,'complete_scientific_tools_claimed':0}
with (HERE/'PROGRESS_UPDATE_012.json').open('x') as record:
    record.write(json.dumps(update,indent=2)+'\n')
path.write_bytes(after)
print(json.dumps({'checkpoint':12,'changes':len(changes),'added_evidence':len(evidence),
    'scope_rows':308,'resource_bindings':288,'complete_scientific_tools_claimed':0,
    'new_status_sha256':update['new_status_sha256']}))
