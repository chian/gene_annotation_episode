"""Exact semantic Cartesian inventory, not an execution/stopping budget."""
TASKS = ('panel_identity', 'alignment_suitability', 'family_phylogeny', 'target_placement',
    'characterized_clades', 'organismal_history', 'paralog_discrimination', 'robustness', 'synthesis')
EXPECTED_COUNTS = {
    'test_actual_build_projector_controller_and_request': 2 * (1 + len(TASKS)),
    'test_returned_outcome_enters_original_iterator_and_replays': 5 * 2 * 2,
    'test_actual_reasoning_and_saved_wait_keep_original_paths': 3,
    'test_custom_service_instructions_keep_original_precedence': 2,
    'test_default_instructions_keep_actual_publication_and_original_read_order': 2,
    'test_actual_publication_controls_default_instruction_replacement': 3,
    'test_actual_provider_preserves_complete_presentation_precedence': 8,
    'test_actual_saved_model_context_and_zero_exchange_restore': 2 * 2 * 2,
    'test_actual_saved_checkpoint_suspension_and_form_replay': 1,
    'test_ready_owned_child_precedes_another_decision': 1,
}
