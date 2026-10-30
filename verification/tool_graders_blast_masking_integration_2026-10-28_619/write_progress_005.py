"""Append the next fixed progress snapshot without modifying earlier records."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

packet=Path('verification/tool_graders_blast_masking_integration_2026-10-28_619')
previous=Path('research/tool_grader_progress_2026-10-27/PROGRESS_036.json')
destination=previous.with_name('PROGRESS_037.json')
assert not destination.exists()
value=json.loads(previous.read_text())
verification=json.loads((packet/'ROOT_VERIFICATION_003.json').read_text())
census=json.loads((packet/'OPERATION_LINK_UPDATE_004.json').read_text())
value['recorded_at']=datetime.now(timezone.utc).isoformat()
value['previous_progress_record']=str(previous)
value['previous_progress_sha256']=hashlib.sha256(previous.read_bytes()).hexdigest()
value['previous_turn_classification']='no_progress_accounting_restatement_only'
value['current_turn_classification']='progress_actual_nested_native_paths_verified_saved_status_branch_repaired'
value['changes_to_goal_or_scope']=False
value['current_turn_verification']={'checks':{r['attempt']:r for r in verification['checks']},
 'receipt_test_root_review':str(packet/'ROOT_VERIFICATION_003.json'),
 'current_source_pin_checks':verification['snapshot_matches'],
 'counts_overlap_do_not_sum':True,
 'worker_manifests':[
  'verification/tool_graders_blast_masking_results_2026-10-28_616/HANDOFF_MANIFEST_005.json',
  'verification/tool_graders_blast_masking_host_returns_2026-10-28_617/HANDOFF_MANIFEST_004.json',
  'verification/tool_graders_blast_masking_resource_wiring_2026-10-28_618/HANDOFF_MANIFEST_005.json'],
 'excluded_intermediate':'617 check076 passed an overpermissive provenance expectation; final078 replaces that correctness claim. Earlier evidence preserved.'}
value['current_native_verification']={'attempts':['check074_masking_workflow','check080_masking_workflow_counts_and_saved'],
 'new_native_commands':verification['new_native_commands'],'verified_selected_mode_paths':4,
 'full_selected_Workflow_path_verified':True,'configured_model_investigation':False,
 'limitations':verification['remaining']}
value['current_combined_sheet_operation_census']={
 'evidence':str(packet/'OPERATION_LINK_UPDATE_004.json'),
 **{k:census[k] for k in ('shared_groups','numerical_groups','typed_only_groups','linked_numerical_groups','linked_typed_only_groups','operation_name_links','distinct_operation_names','distinct_numerically_linked_operation_names','unlinked_numerical_groups')},
 'qualification':census['qualification']}
value['current_turn_accounting']={'new_complete_inventory_rows':0,'all_R1_through_R7_remain_open':True,
 **{k:census[k] for k in ('numerical_groups','typed_only_groups','linked_numerical_groups','linked_typed_only_groups','distinct_operation_names','distinct_numerically_linked_operation_names','operation_name_links','unlinked_numerical_groups')},
 'delta_from036':{'new_numerical_groups':1,'new_typed_only_groups':1,'new_distinct_operation_mode_names':4,'new_links':5},
 'qualification':'44linkednumerical groups reach124distinctoperation/mode names;2typed groups also cover4names, yielding125combined distinctnames and138links. One numerical group remains unlinked. Fulltool completion count remains unestablished; no inventory row is newly declared wholly finished.'}
value['accounting_review']='Historical112/114 reconciliation remains unchanged. Additive619 mapping adds one shared raw-sequence masking numerical group and one native Window statistics validation group:47groups/138links/125distinctoperation-mode names.43→44 linked numerical groups; no completed307-row claim.'
value['current_update_evidence']=[str(packet/'ROOT_VERIFICATION_003.json'),str(packet/'OPERATION_LINK_UPDATE_004.json'),
 'verification/tool_graders_masking_saved_status_2026-10-28_623/VERIFICATION_003.json',
 *value['current_turn_verification']['worker_manifests']]
for row in value['deliverables']:
 assert row['status']=='open'
 if row['id']=='R7':
  row['qualification']='Three utilities have four selected tiny local modes verified through original nested Workflow and requested typed final returns. Message presentation remains open, so all13 whole-utility closures remain open. Other ten utilities have actual help/version evidence and boundary planning, not implementations.'
  row['utilities_with_verified_selected_local_paths']=3
  row['verified_selected_local_mode_paths']=4
  m=row['current_masking_implementation']
  m.update(result_publication_complete=True,requested_episode_returns_complete=True,
    full_Workflow_complete=True,
    verification_scope='Four explicitly selected local modes through scripted shared Workflow; no configured-model claim or post-results scientific next-decision presentation proof.',
    new_source_evidence=str(packet/'ROOT_VERIFICATION_003.json'),
    saved_status_repair='verification/tool_graders_masking_saved_status_2026-10-28_623/VERIFICATION_003.json',
    remaining='621 results-decision and622 scientific-parent message drafts need printed user feedback and implementation; actual next-decision rendering still unverified. Other ten R7 utility contracts are being defined in620. No API/HPC masking binding is claimed.')
  row['next_utility_boundary_evidence']='verification/tool_graders_blast_utility_boundaries_2026-10-28_620'
 if row['id']=='R6':
  work=row['current_alias_work'];old_open=work['open_boundaries']
  # Existing036 already records the later059–061/065/067 outcomes. Retain the
  # obsolete pending items explicitly as resolved instead of silently dropping them.
  work['resolved_prior_open_boundaries']=[{'original_item':x,'status':'verified_with_recorded_limits',
   'evidence':'verification/tool_graders_uniprot_requested_returns_2026-10-28_601/ROOT_RECEIVED_CONTEXT_VERIFICATION_009.json',
   'followup_received_context_checks':['check065_received_context_direct_final','check067_current_receipt_exchange_tests']} for x in old_open[:2]]
  work['open_boundaries']=old_open[2:]
  work['status']='selected_H_return_paths_and_received_context_regressions_verified_presentation_and_provider_gaps_open'
  row['qualification']='Existing UniProtKB JSON record/search-page and literal query_uniprot alias paths retain their recorded parser, receipt, requested-return and shared Workflow verification. Presentation, downstream material access, wider provider modes and live-resource requirements remain open.'
  ub=value['uniprot_current_boundary']
  ub['resolved_prior_open_boundaries']=work['resolved_prior_open_boundaries']
  ub['open_boundaries']=work['open_boundaries']
  ub['shared_workflow_grant_variants']['qualification']='Original061 four variants passed. Its12 affected receipt fixture failures were subsequently resolved by065/067, as already recorded in036.latest_regression_resolution.'
value['current_workloads']=[
 {'agent':'/root/blast_utility_boundary_plan_620','boundary':'Exact next-ten utility data/invocation/shared-contract boundaries;20help/version calls verified; no utility production coding.'},
 {'agent':'/root/masking_results_decision_template_621','boundary':'One existing results episode decision template, traced from real074 saved input; draft only pending user feedback.'},
 {'agent':'/root/masking_scientific_return_template_622','boundary':'One immediate scientific-parent received-results template; independent original direct-child contract; draft only pending feedback.'},
 {'agent':'/root','boundary':'Assembled local masking path and narrow saved-status repair verified; fixed accounting updated; next review is concrete message drafts and620 coding interfaces.'}]
value['current_next_action']=[
 'Print621 results-decision and622 immediate scientific-parent templates for running user feedback; no concrete prompt implementation until feedback.',
 'Review620 actual ten-utility contracts and native help evidence; fix shared boundaries and exact file/interface ownership before assigning fresh parallel coding workers.',
 'Continue unresolvedR1–R7 work without restarting completed numerical implementations. Existing603/607/609and598message questions remain pending.',
 'Keep the fluorescence original full-sheet comparison gap explicit: saved return postconditions passed but two complete-sheet comparisons remain unverified after deliberate byte withdrawal.'
]
destination.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
assert [r['id'] for r in value['deliverables']]==['R1','R2','R3','R4','R5','R6','R7']
print(destination)
print('R1–R7 retained open; four selected local masking modes verified; no whole inventory completion increment')
