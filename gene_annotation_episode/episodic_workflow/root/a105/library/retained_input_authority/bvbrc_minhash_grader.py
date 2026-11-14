"""Pure readers and numerical components for the native BV-BRC Minhash result.

The input is the synchronous RPC's result[0], a list of four-field rows, not
an AppService task or a Mash TSV. Acquisition and receipt custody belong to
the caller. No function here performs I/O, chooses work, or assigns credit.

Native measurements and their types remain in ``native_result``/``native_row``.
The numerical cells are parsed values, not calibrated annotation probabilities.
Calculators use explicit pair metadata joined on BOTH row index and genome ID.
See verification/tool_graders_bvbrc_minhash_2026-10-24/README.md for numerical
meanings, missing-data behavior, pinned sources, and verification limitations.
"""
from __future__ import annotations
MINHASH_DIAGNOSTIC_CODES = ('ambiguous_pair_metadata', 'binomial_integer_precision_unsupported', 'binomial_tail_unavailable', 'counts_integer_conversion_unavailable', 'distance_numeric_range_unsupported', 'distance_saturated_at_one', 'distance_underflow_or_rounding', 'eight_native_arguments_required', 'empty_result_completeness_unknown', 'invalid_counts_token', 'invalid_genome_id', 'invalid_native_number', 'kmer_space_overflow_log_calculation_used', 'minhash_sheet_required', 'missing_calculation_input', 'missing_native_field', 'native_integer_argument_required', 'native_number_outside_unit_interval', 'native_numeric_conversion_underflow', 'native_request_object_required', 'native_result_array_required', 'native_row_arity', 'native_row_array_required', 'negative_native_number', 'nonfinite_native_number', 'null_model_numeric_range_unsupported', 'null_native_field', 'pair_metadata_array_required', 'pair_metadata_genome_id_mismatch', 'pair_metadata_missing', 'pair_metadata_object_required', 'pair_metadata_row_index_mismatch', 'positive_integer_metadata_required', 'query_identifier_required', 'random_jaccard_rounded_to_one', 'random_jaccard_underflow', 'recomputed_pvalue_rounded_to_one', 'recomputed_pvalue_underflow', 'reported_pvalue_zero_precision_unknown', 'request_method_mode_mismatch', 'row_identity_unavailable', 'shared_fraction_underflow_or_rounding', 'shared_hashes_exceed_union', 'sheet_native_row_count_mismatch', 'sheet_native_row_mismatch', 'structured_metadata_provenance_required', 'structured_provenance_required', 'unsupported_minhash_mode', 'valid_hash_counts_required', 'workspace_fasta_path_required', 'zero_compared_union_hashes', 'zero_union_calculations_unavailable')
