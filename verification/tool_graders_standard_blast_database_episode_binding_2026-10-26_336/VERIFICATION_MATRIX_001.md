# Standard database E contract-to-test trace

This is a trace of implemented assertions, not a blanket passing-test claim.
Final outcomes and exact source identities are recorded separately. The
end-to-end fixture uses fake PBS and an explicitly synthetic native-file emitter;
it calls the actual original-attempt worker, M/R worker and episode returns.
No local database BLAST or live HPC execution is represented by these fixtures.

| Contract | Actual tests |
| --- | --- |
| E1 | episode_binding: five_selected_pbs_children_collect_and_return_original_facts; results: received_complete_query_publishes_only_native_query_observation (all five programs); saved_complete_master_map_publishes_without_redecoding (tblastn supplied PSSM). |
| E2 | acquisition: original_identity_and_partial_siblings, actual_original_pbs_reader_authenticates_before_capture; results: selected_metadata_requires_actual_parent_receipt, original_input_store_possession_does_not_authorize_launch, original_handoff_must_have_been_received_by_commissioning_parent; returns: actual_received_form_is_required_and_saved_row_cannot_be_rewritten, frozen_observation_requires_original_commission_handoff_and_record. |
| E3 | acquisition: complete_chunks_and_frozen_replay, same_selected_capture_resumes_verified_existing_bytes, interrupted_capture_changed_prefix_is_preserved_and_not_missing, plan_and_bundle_transfer_failures_keep_exact_meaning, complete_native_report_larger_than_one_chunk_is_exactly_retained. |
| E4 | results: retained_paired_range_stays_paired_and_synthetic_database_uses_saved_full_axis, received_complete_query_publishes_only_native_query_observation, complete_biological_identity_is_required_without_losing_native_rows, sparse_malformed_original_hsp_retains_valid_sibling_and_qualified_pointer. |
| E5 | results: actual_preparation_and_frozen_replay_without_remote_or_calculation; episode_binding: zero_hits_are_a_complete_selected_result_and_empty_return. Metadata-free HSP values remain typed source facts. |
| E6 | returns: every_native_consumer_qualifies_frozen_measurements_and_missing_reference, actual_received_form_is_required_and_saved_row_cannot_be_rewritten, interval_marker_source_and_saved_index_tampering_is_rejected; results: retained range frozen-calculation artifact mutation. |
| E7 | results: empty_streams_and_projection_reuse_preserve_original_source_and_observation, parameter_recalculation_preserves_original_hsp_publication_payload; returns: repeated_projection_receipts_union_only_actual_received_cells, distinct_saved_calculations_keep_separate_rows_without_new_observations. |
| E8 | returns: successful_original_collect_immediately_has_exact_zero_future_expectation; results: nonzero_native_retains_readable_rows_without_completion, missing_explicit_row_is_specific_incomplete_projection, invalid_model_before_generation_retains_original_exception, abrupt_worker_failure_retains_atomic_siblings_without_valid_manifest. |
| E9 | Existing native6 acquisition/results/returns/episode_binding; existing paired results, typed API BLAST return integration, native return admission; execution family/progress/PBS/communication/tool knowledge regressions. Historical unrelated failures remain separately identified. |
| E10 | returns: repeated_projection_receipts_union_only_actual_received_cells (both receive orders), frozen_forwarded_projection_remains_an_authorized_subset, received_cell_conflicts_are_specific_and_preserve_originals, received_row_context_conflicts_never_choose_a_projection. |
| E11 | episode_binding: failed_original_attempt_crosses_all_boundaries_without_handoff_credit. The authenticated failed HPC attempt reaches launch, the scientific parent, results, real M/R and the exact immediate-parent form; usable handoff, completion and handoff credit remain false/zero. |
| Addendum003 | results: search_calculation_failure_retains_native_scores_and_typed_failure; incompatible explicit priors preserve null303, raw HSP cells and the closed search-qualified failure. |
| Addendum004 | results: null_pssm_calculation_is_unavailable_without_recalculation checks E's saved null consumer. R333 check007 separately exercises the actual-file worker's injected PSSM exception, retained sequence sibling, artifact-qualified failure and diagnostic. E does not claim its detached consumer fault injection is a second worker execution. |

All numerical statements are assertions against actual parser/calculator outputs;
E adds no scientific row-count calculation. The historical retained BLASTX
JSON15 file remains paired-format evidence. A separate explicitly synthetic
database fixture demonstrates the full 244-nt query, reported 186-nt range,
qualified 186/244 coverage and reverse first codon interval [212,215).

Resource-failure tests inject abrupt worker outcomes; they do not physically
exhaust host memory or scratch. Live prepared HPC execution, scientific API
execution and deployment availability remain unverified in this workload.
