"""SYNTHETIC arithmetic only; no sequences, alignments, searches, or readers.

These invented operands exercise the formulas in NATIVE_SCORE_CONTRACT.md.
They are not BLAST/HMMER output, calibrated model parameters, biological
observations, adopted scoring policy, or evidence that A101 is complete.
Run with python3; stdout is the result artifact. Uses only the standard library.
"""

import json
import math


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-15), (a, b)


def bit_score(raw_score, scale_lambda, K):
    return (scale_lambda * raw_score - math.log(K)) / math.log(2)


def sigmoid(z):
    return 1 / (1 + math.exp(-z))


def union_length(intervals):
    # Inclusive integer intervals. Repeated intervals add no positions.
    positions = set()
    for start, stop in intervals:
        assert 1 <= start <= stop
        positions.update(range(start, stop + 1))
    return len(positions)


blast = {
    "fixture_status": "synthetic_not_program_output",
    "target_label": "supplied_sequence_Q",
    "target_length_aa": 300,
    "reference_length_aa": 260,
    "alignment_columns": 240,
    "identical_columns": 180,
    "query_gap_columns": 4,
    "reference_gap_columns": 4,
    "query_start_1based": 20,
    "query_end_1based": 255,
    "reference_start_1based": 5,
    "reference_end_1based": 240,
    "substitution_sum_raw_points": 230,
    "gap_opens": 2,
    "gap_open_points": 11,
    "gap_extension_points_per_column": 1,
    "lambda_inverse_raw_points": 0.267,
    "K": 0.041,
    "effective_query_length": 280,
    "effective_database_length": 1_000_000,
    "statistical_regime": "stipulated_simple_single_HSP_Karlin_Altschul",
}
blast["gap_columns"] = blast["query_gap_columns"] + blast["reference_gap_columns"]
blast["residue_pair_columns"] = blast["alignment_columns"] - blast["gap_columns"]
blast["raw_score_points"] = (
    blast["substitution_sum_raw_points"]
    - blast["gap_opens"] * blast["gap_open_points"]
    - blast["gap_columns"] * blast["gap_extension_points_per_column"]
)
blast["bit_score"] = bit_score(
    blast["raw_score_points"], blast["lambda_inverse_raw_points"], blast["K"]
)
blast["effective_search_space"] = (
    blast["effective_query_length"] * blast["effective_database_length"]
)
blast["E_from_raw"] = (
    blast["K"] * blast["effective_search_space"]
    * math.exp(-blast["lambda_inverse_raw_points"] * blast["raw_score_points"])
)
blast["E_from_bits"] = blast["effective_search_space"] * 2 ** (-blast["bit_score"])
close(blast["E_from_raw"], blast["E_from_bits"])
blast["E_after_tenfold_effective_search_space"] = 10 * blast["E_from_raw"]
blast["identity_fraction_all_columns"] = blast["identical_columns"] / blast["alignment_columns"]
blast["identity_fraction_residue_pairs"] = blast["identical_columns"] / blast["residue_pair_columns"]
blast["query_span_aa"] = blast["query_end_1based"] - blast["query_start_1based"] + 1
blast["reference_span_aa"] = blast["reference_end_1based"] - blast["reference_start_1based"] + 1
assert blast["query_span_aa"] == blast["alignment_columns"] - blast["query_gap_columns"]
assert blast["reference_span_aa"] == blast["alignment_columns"] - blast["reference_gap_columns"]
blast["query_span_coverage"] = blast["query_span_aa"] / blast["target_length_aa"]
blast["reference_span_coverage"] = blast["reference_span_aa"] / blast["reference_length_aa"]
blast["query_paired_residue_coverage"] = blast["residue_pair_columns"] / blast["target_length_aa"]

hmmer = {
    "fixture_status": "synthetic_not_program_output",
    "program_shape": "hmmscan_protein",
    "target_label": "supplied_sequence_Q",
    "sequence_length_aa": 300,
    "profile_match_states": 120,
    "full_sequence_bit_score": 62.0,
    "full_sequence_bias_bits": 2.0,
    "domain_bit_score": 60.0,
    "domain_bias_bits": 1.0,
    "profile_forward_tau_bits": 5.0,
    "profile_forward_lambda_inverse_bits": math.log(2),
    "Z_profiles": 20_000,
    "domZ_reported_profiles": 8,
    "hmm_from_1based": 5,
    "hmm_to_1based": 112,
    "ali_from_1based": 21,
    "ali_to_1based": 128,
    "env_from_1based": 18,
    "env_to_1based": 132,
    "match_states_emitting_sequence_residues": 102,
    "deleted_match_states_in_span": 6,
    "inserted_sequence_residues_in_span": 6,
    "synthetic_GA_sequence_bits": 25.0,
    "synthetic_GA_domain_bits": 24.0,
}
for scope, score in (("sequence", 62.0), ("domain", 60.0)):
    log_p = -hmmer["profile_forward_lambda_inverse_bits"] * (score - hmmer["profile_forward_tau_bits"])
    hmmer[f"{scope}_log_tail_P"] = log_p
    hmmer[f"{scope}_tail_P"] = math.exp(log_p)
hmmer["sequence_E"] = hmmer["Z_profiles"] * hmmer["sequence_tail_P"]
hmmer["domain_independent_E"] = hmmer["Z_profiles"] * hmmer["domain_tail_P"]
hmmer["domain_conditional_E"] = hmmer["domZ_reported_profiles"] * hmmer["domain_tail_P"]
hmmer["independent_to_conditional_ratio"] = hmmer["domain_independent_E"] / hmmer["domain_conditional_E"]
close(hmmer["independent_to_conditional_ratio"], hmmer["Z_profiles"] / hmmer["domZ_reported_profiles"])
hmmer["profile_span_states"] = hmmer["hmm_to_1based"] - hmmer["hmm_from_1based"] + 1
hmmer["sequence_alignment_span_aa"] = hmmer["ali_to_1based"] - hmmer["ali_from_1based"] + 1
hmmer["sequence_envelope_span_aa"] = hmmer["env_to_1based"] - hmmer["env_from_1based"] + 1
assert hmmer["profile_span_states"] == hmmer["match_states_emitting_sequence_residues"] + hmmer["deleted_match_states_in_span"]
assert hmmer["sequence_alignment_span_aa"] == hmmer["match_states_emitting_sequence_residues"] + hmmer["inserted_sequence_residues_in_span"]
hmmer["profile_span_coverage"] = hmmer["profile_span_states"] / hmmer["profile_match_states"]
hmmer["profile_emission_coverage"] = hmmer["match_states_emitting_sequence_residues"] / hmmer["profile_match_states"]
hmmer["sequence_alignment_span_coverage"] = hmmer["sequence_alignment_span_aa"] / hmmer["sequence_length_aa"]
hmmer["sequence_envelope_span_coverage"] = hmmer["sequence_envelope_span_aa"] / hmmer["sequence_length_aa"]
hmmer["sequence_GA_margin_bits"] = hmmer["full_sequence_bit_score"] - hmmer["synthetic_GA_sequence_bits"]
hmmer["domain_GA_margin_bits"] = hmmer["domain_bit_score"] - hmmer["synthetic_GA_domain_bits"]
hmmer["domain_score_before_stated_bias_bits"] = hmmer["domain_bit_score"] + hmmer["domain_bias_bits"]

sites = {"declared_sites": 5, "assessable_sites": 4, "compatible_sites": 3, "unknown_sites": 1}
sites["assessable_fraction"] = sites["assessable_sites"] / sites["declared_sites"]
sites["compatible_fraction_among_assessable"] = sites["compatible_sites"] / sites["assessable_sites"]
sites["compatible_fraction_lower"] = sites["compatible_sites"] / sites["declared_sites"]
sites["compatible_fraction_upper"] = (sites["compatible_sites"] + sites["unknown_sites"]) / sites["declared_sites"]
close(sites["assessable_fraction"] * sites["compatible_fraction_among_assessable"], sites["compatible_fraction_lower"])

overlap = {"query_length_aa": 300, "intervals_1based_inclusive": [[20, 255], [200, 280], [20, 255]]}
overlap["unique_aligned_span_aa"] = union_length(overlap["intervals_1based_inclusive"])
overlap["span_union_coverage"] = overlap["unique_aligned_span_aa"] / overlap["query_length_aa"]
assert overlap["unique_aligned_span_aa"] == 261
assert union_length([[20, 255], [200, 280]]) == overlap["unique_aligned_span_aa"]

self_normalization = {"pair_raw": 200, "query_self_raw": 600, "reference_self_raw": 520}
self_normalization["illustrative_raw_ratio"] = 200 / math.sqrt(600 * 520)
self_normalization["incorrect_bit_substitution_ratio"] = blast["bit_score"] / math.sqrt(
    bit_score(600, 0.267, 0.041) * bit_score(520, 0.267, 0.041)
)
assert not math.isclose(self_normalization["illustrative_raw_ratio"], self_normalization["incorrect_bit_substitution_ratio"])

# Entirely invented coefficients to check dimensional arithmetic. NOT a fit.
coefficients = {
    "intercept": -3.0,
    "blast_bits": 0.025,
    "hmmer_domain_bits": 0.02,
    "blast_x_hmmer_bits_squared": -0.0002,
    "blast_query_span_fraction": 0.5,
    "blast_reference_span_fraction": 0.5,
    "hmmer_profile_span_fraction": 0.5,
    "blast_identity_fraction": 0.5,
    "site_compatible_fraction": 0.5,
}
terms = {
    "intercept": coefficients["intercept"],
    "blast_bits": coefficients["blast_bits"] * blast["bit_score"],
    "hmmer_domain_bits": coefficients["hmmer_domain_bits"] * hmmer["domain_bit_score"],
    "blast_x_hmmer_bits_squared": coefficients["blast_x_hmmer_bits_squared"] * blast["bit_score"] * hmmer["domain_bit_score"],
    "blast_query_span_fraction": coefficients["blast_query_span_fraction"] * blast["query_span_coverage"],
    "blast_reference_span_fraction": coefficients["blast_reference_span_fraction"] * blast["reference_span_coverage"],
    "hmmer_profile_span_fraction": coefficients["hmmer_profile_span_fraction"] * hmmer["profile_span_coverage"],
    "blast_identity_fraction": coefficients["blast_identity_fraction"] * blast["identity_fraction_all_columns"],
}
z_base = sum(terms.values())
z_lower = z_base + coefficients["site_compatible_fraction"] * sites["compatible_fraction_lower"]
z_upper = z_base + coefficients["site_compatible_fraction"] * sites["compatible_fraction_upper"]
joint = {
    "status": "synthetic_coefficients_not_calibrated_not_function_probabilities",
    "coefficients": coefficients,
    "summands_excluding_site": terms,
    "site_summand_bounds": [0.3, 0.4],
    "linear_index_bounds": [z_lower, z_upper],
    "logistic_transform_bounds": [sigmoid(z_lower), sigmoid(z_upper)],
    "real_A101_combined_score": None,
    "real_A101_combined_score_status": "calibration_absent",
}
assert 0 <= joint["logistic_transform_bounds"][0] <= joint["logistic_transform_bounds"][1] <= 1

result = {
    "all_values_are_synthetic": True,
    "scientific_programs_executed": [],
    "arithmetic_assertions": "passed",
    "blast": blast,
    "hmmer": hmmer,
    "site_correspondence": sites,
    "overlap_and_duplicate": overlap,
    "raw_self_normalization_boundary": self_normalization,
    "unadopted_joint_combination_arithmetic": joint,
}
print(json.dumps(result, indent=2, allow_nan=False))
