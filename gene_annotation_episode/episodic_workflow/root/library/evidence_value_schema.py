"""Original retained numerical-value schemas private to root record readers."""

def obj(properties: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required, "additionalProperties": False}


REF = {"type": "string", "maxLength": 256,
       "pattern": r"^(?:[a-z][a-z_]*_[a-f0-9]{24,64}|@[A-Za-z][A-Za-z0-9_]*)$",
       "description": "Copy an existing persistent record ID exactly as supplied. In a reasoning commit only, @name refers to an earlier successfully processed row declared with alias name in this same commit. Ordinary tool calls require existing persistent IDs."}
NULL_REF = {"anyOf": [REF, {"type": "null"}]}
NUMBER_ATOM = obj({"type": {"const": "number"}, "value": {"type": "number"}, "unit_ref": NULL_REF,
        "bound": {"enum": ["less_than", "less_or_equal", "greater_than", "greater_or_equal"],
            "description": "An explicit source-reported bound (<, <=, > or >=) on value, in unit_ref. Preserve the threshold rather than replacing a censored value with zero or an exact measurement. Omission adds no precision claim. A bounded threshold is not an exact coordinate, coverage, extent or arithmetic operand."},
        "qualifier": {"const": "approximate", "description": "An explicit source approximation such as ~. Omission adds no precision claim and does not mean scientifically exact."},
        "uncertainty": {**obj({"representation": {"const": "plus_minus"},
            "magnitude": {"type": "number", "minimum": 0},
            "statistic": {"const": "unspecified"}}),
            "description": "A source-reported plus/minus magnitude in this number's enclosing unit. The statistic is unspecified: do not infer SD, SE, CI, a probability distribution or interval endpoints. Omit when no uncertainty is reported."}},
        required=["type", "value", "unit_ref"])

METRIC_NAMES = ["context_association_index", "length", "gc_fraction", "ambiguous_fraction", "identity_fraction", "query_coverage",
    "target_coverage", "alignment_score", "bitscore", "evalue", "model_score", "count", "start", "end",
    "strand", "genetic_code", "feature_kind", "reference_ref", "profile_ref", "source_taxon", "annotation_ref",
    "missing_data", "boundary_state", "match_state", "activity", "growth_rate", "observed_growth", "temperature",
    "ph", "salinity", "time", "replicate", "control_ref", "relation_ref", "substrate_ref", "product_ref",
    "cofactor_ref", "location_ref", "sample_ref", "condition_ref", "biomass", "dna_concentration", "coverage",
    "quality_score", "reading_frame", "stop_count", "intron_count", "native_confidence", "assay_outcome",
    "extraction_batch", "environment_ref", "medium_ref", "oxygen_relationship", "source_reference", "query_start", "query_end", "molecule_model",
    "concentration", "dissociation_constant"]
# Native tool-grader components. These are named measurements, not new credit
# axes or a shared confidence scale. Denominators/native arrays remain retained
# in the tool's own numerical sheet.
METRIC_NAMES += [
    "alignment_columns", "paired_positions", "identical_positions", "substituted_positions",
    "query_gap_columns", "reference_gap_columns", "query_aligned_positions",
    "reference_aligned_positions", "paired_identity", "alignment_identity",
    "query_paired_coverage", "reference_paired_coverage", "query_aligned_coverage",
    "reference_aligned_coverage", "query_length", "reference_length",
    "unambiguous_nucleotide_count", "ambiguous_symbol_count", "ambiguity_fraction",
    "gc_count", "gc_denominator", "quality_observation_count", "mean_phred",
    "mean_error_probability", "expected_error_count", "interval_length_nt",
    "protein_length_aa", "internal_stop_count", "terminal_stop_count",
    "query_span", "reference_span", "native_matching_bases", "native_block_length",
    "native_alignment_identity", "inserted_bases", "deleted_bases",
    "reference_skipped_bases", "cs_equal_positions", "cs_substituted_positions",
    "native_ambiguity_count", "query_span_coverage", "reference_span_coverage", "mapping_quality",
    "model_length", "sequence_length", "model_span_positions", "sequence_span_residues",
    "sequence_envelope_residues", "model_span_coverage", "sequence_span_coverage",
    "sequence_envelope_coverage", "insert_positions", "delete_positions",
    "paired_model_coverage", "paired_sequence_coverage", "sequence_identity_fraction",
    "consensus_identity_fraction", "alignment_identity_fraction", "api_identity_fraction",
    "native_domain_score_bits", "native_domain_bias_bits", "native_conditional_evalue",
    "native_independent_evalue", "native_accuracy", "posterior_lower_mean", "posterior_upper_mean",
    "native_score_bits", "native_bias_bits", "native_evalue", "sequence_span_positions",
    "sequence_envelope_positions", "original_length", "retained_residues", "match_state_residues",
    "deleted_model_positions", "insert_state_residues", "terminal_unaligned_residues",
    "missing_model_positions", "nonresidue_model_positions", "trimmed_residues",
    "model_occupancy", "sequence_match_coverage", "posterior_bounded_residue_count",
    "posterior_unavailable_residue_count",
]
# Infernal uses nucleotide/model coordinates and preserves its own score names.
# These are tool measurements, not additions to annotation-credit dimensions.
METRIC_NAMES += [
    "bias_bits", "model_span_length", "model_span_fraction", "sequence_span_length",
    "sequence_span_fraction", "consensus_length", "hit_count", "union_numerator",
    "union_denominator", "union_span_fraction", "unselected_hit_count",
    "unknown_selection_count", "invalid_geometry_count", "native_bit_score", "native_avg_pp",
    "retained_nucleotides", "model_match_nucleotides", "model_gap_positions",
    "retained_insert_nucleotides", "retained_local_end_nucleotides",
    "local_end_skipped_model_positions", "total_insert_nucleotides",
    "total_local_end_nucleotides", "omitted_nucleotides", "sequence_matched_coverage",
    "posterior_available_count", "posterior_unavailable_count", "row_count",
    "occupancy_numerator", "occupancy_denominator", "occupancy", "missing_rows",
    "nonresidue_rows", "unavailable_rows", "observed_two_nucleotide_pairs",
    "canonical_pairs", "noncanonical_pairs", "unambiguous_pair_denominator",
    "canonical_pair_fraction", "excluded_gap_rows", "excluded_missing_rows",
    "excluded_ambiguous_rows", "excluded_nonresidue_rows", "excluded_unavailable_rows",
]
# Sequence transformations publish counts and verified correspondence, without
# adding evidence axes or assigning confidence to the transformed product.
METRIC_NAMES += [
    "input_length_nt", "selected_length_nt", "frame_skipped_nt",
    "translated_length_nt", "trailing_untranslated_bases", "translated_codon_count",
    "output_symbol_count", "amino_acid_symbol_count", "terminal_stop_symbol_count",
    "omitted_terminal_stop_codon_count", "ambiguous_codon_count",
    "ambiguous_output_symbol_count", "mapped_output_symbol_count",
    "compatible_codon_count", "incompatible_codon_count", "unknown_codon_count",
    "selected_input_fraction", "selected_input_fraction_denominator_nt",
    "input_symbol_count", "requested_segment_count", "selected_symbol_occurrence_count",
    "distinct_selected_input_symbol_count", "repeated_selected_input_symbol_count",
    "selected_input_fraction_denominator_symbols", "expected_output_symbol_count",
    "output_length_difference", "compared_symbol_count", "matching_symbol_count",
    "mismatching_symbol_count", "unmapped_output_symbol_count", "source_segment_count",
]
# Selected reference sites have their own explicit population and denominators.
# Shared count names retain their literal meanings; these are not credit axes.
METRIC_NAMES += [
    "requested_position_count", "unique_requested_position_count", "duplicate_requested_position_count",
    "query_gap_positions", "reference_skip_positions", "outside_alignment_positions",
    "unavailable_positions", "aligned_reference_positions", "selected_insertion_events",
    "inserted_query_positions", "selected_paired_identity", "selected_alignment_identity",
    "selected_reference_aligned_fraction", "selected_reference_paired_fraction",
    "selected_query_paired_units", "selected_reference_paired_units",
    "selected_query_paired_coverage", "selected_reference_paired_coverage",
]
# Paired native BLAST measurements retain HSP scores and explicit union counts.
# The union is a derived view of those same HSPs, never an extra observation.
METRIC_NAMES += [
    "native_raw_score", "observed_distinct_residue_pairs", "observed_identical_residue_pairs",
    "observed_paired_query_positions", "observed_paired_reference_positions",
    "hsps_with_geometry", "hsps_without_geometry", "query_selected_length",
    "reference_selected_length", "query_selected_paired_positions",
    "reference_selected_paired_positions", "query_selected_paired_coverage",
    "reference_selected_paired_coverage", "conflicting_mapping_count", "identical_mapping_group_count",
]
METRIC_NAMES += ['trait_conservation_index']
METRIC_NAMES += ['bootstrap_split_matches', 'bootstrap_split_denominator', 'bootstrap_split_frequency',
                 'unrooted_robinson_foulds_distance', 'matched_taxon_count', 'native_reference_member_count',
                 'placement_membership_intersection', 'placement_membership_union', 'placement_membership_stability']
OBSERVATION_KINDS = ["sequence_composition", "gene_prediction", "alignment", "profile_match", "structure_match",
    "taxonomy_assignment", "source_annotation", "source_content", "assay_report", "biochemical_assay",
    "genetic_phenotype", "growth_assay", "context_measurement", "read_support", "coordinate_mapping",
    "reaction_context", "mechanism", "comparison", "context"]
