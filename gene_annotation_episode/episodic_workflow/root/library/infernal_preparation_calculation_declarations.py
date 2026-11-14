COMPONENT_UNITS = {
    "paired_consensus_fraction": "fraction", "paired_consensus_numerator": "nt",
    "consensus_length_denominator": "nt", "mu_extrap_calculated": "bit", "mu_extrap_residual": "bit",
    "actual_calibration_nt": "nt", "partition_chunk_count": "count", "total_calibration_chunk_count": "count", "predicted_seconds": "second",
    "predicted_bytes": "byte", "effective_random_hit_count": "expected_count", "score_at_evalue": "bit",
    "score_at_pvalue": "bit", "evalue_at_score": "expected_count", "native_conversion_residual": "bit",
    "native_rounding_half_width": "bit",
}

CHECK_NAMES = frozenset({"paired_topology_coherent", "build_header_counts_consistent", "summary_header_counts_consistent",
    "build_population_complete", "calibration_fit_consistent", "calibration_length_consistent",
    "calibration_stdout_consistent", "native_conversion_consistent", "native_cutoff_consistent",
    "model_reference_valid", "partition_score_count_consistent", "partition_request_binding",
    "partition_population_complete", "partition_settings_consistent", "partition_merged_hit_counts",
    "split_command_count_consistent", "training_alignment_complete"})

