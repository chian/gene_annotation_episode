ROW_FIELDS = {
    "generated_sequence": frozenset({"kind", "record_key", "locator", "model_keys", "origin",
        "name", "description", "sequence", "alphabet", "residue_sha256", "sample_index",
        "embedded_interval", "alignment_key", "values"}),
    "generated_alignment": frozenset({"kind", "record_key", "locator", "model_keys", "origin",
        "format", "sequence_keys", "annotations", "values"}),
    "generated_trace": frozenset({"kind", "record_key", "locator", "model_keys", "sequence_keys", "name", "trace_family", "values"}),
}
SEQUENCE_VALUE_NAMES = frozenset({"residue_count", "canonical_count", "gc_count",
                                 "ambiguity_count", "gap_count", "column_count"})
COMPONENT_NAMES = frozenset({*SEQUENCE_VALUE_NAMES, "gc_fraction_canonical", "gc_denominator",
    "gap_fraction", "row_count", "expected_sequence_count", "actual_sequence_count", "score_bits", "structure_score_bits"})

