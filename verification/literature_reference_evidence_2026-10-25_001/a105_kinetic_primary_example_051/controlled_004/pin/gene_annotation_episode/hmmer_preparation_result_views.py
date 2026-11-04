"""Pure selection of retained HMMER preparation measurements and checks.

This module copies saved numerical cells. It does not parse native output,
calculate scores, open artifacts, authenticate custody, or create observations.
The closed catalogue follows the actual A1/B1/E1/S1/H1/F1 row layouts. See the
272 FIELDS.md and IDENTITY_HANDOFF_001.md for the deliberate identity exceptions.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
import math
import re

from .domain import ContractError
from .native_hmmer_preparation_contracts import PROGRAM_MODES, operand_contract, output_contract


_COLLECTIONS = ("input_records", "output_records", "native_rows", "calculations")
_DIRECTIONS = ("input", "working_copy", "output")
_COMPONENT_STATES = {"present", "missing", "incomplete", "incompatible", "nonfinite", "failed"}
_STATES = _COMPONENT_STATES | {"invalid", "native_missing_sentinel", "undetermined", "decoded", "partial", "unsupported", "unknown", "complete", "truncated", "not_measured"}
_OUTCOMES = {"pass", "fail", "unknown", "not_applicable"}
_M1_FIELDS = {"occurrence_id", "direction", "role", "ordinal", "artifact_ref", "sha256", "size_bytes", "completeness"}
_OCCURRENCE_FIELDS = _M1_FIELDS | {"format", "relative_path"}
_FAMILIES = {
    **dict.fromkeys(("hmmconvert", "hmmfetch", "hmmpress"), "artifact"),
    **dict.fromkeys(("hmmbuild", "alimask"), "alignment_preparation"),
    "hmmemit": "emission", "hmmsim": "simulation", "hmmstat": "statistics",
    "makehmmerdb": "fm", "hmmerfm-exactmatch": "fm",
}
_SHEET_EXTRA = {
    "artifact": {"model_extractions", "input_records", "output_records", "native_rows", "associations", "artifact_bindings"},
    "alignment_preparation": {"model_extraction", "input_records", "output_records", "native_rows", "associations"},
    "emission": {"model_extraction", "output_records", "native_rows", "associations"},
    "simulation": {"input_records", "native_rows", "associations", "native_abi"},
    "statistics": {"model_extraction", "summary", "native_rows", "associations"},
    "fm": {"input_records", "native_rows", "associations", "producer_contract", "source_binding", "database"},
}


def _error(code):
    raise ContractError("native_hmmer_preparation_projection_" + code)


def _contract_errors(code):
    """Malformed supplied structure is a contract failure, never an incidental exception."""
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except (AttributeError, KeyError, TypeError, IndexError, RecursionError, OverflowError) as exc:
                raise ContractError("native_hmmer_preparation_projection_" + code) from exc
        return wrapped
    return decorate


def _text(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or not value or "\x00" in value:
        _error("nonempty_text_required")


def _fields(value, fields, code="fields_invalid"):
    if type(value) is not dict or set(value) != set(fields):
        _error(code)


def _finite_json(value):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for child in value:
            _finite_json(child)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for child in value.values():
            _finite_json(child)
        return
    _error("finite_json_required")


def _number(value, *, nullable=True):
    if value is None and nullable:
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _error("finite_number_required")


def _integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        _error("integer_required")


# A spec is documentation and a closed field accessor, never a formula. The
# optional state path copies an existing native scalar's explicit state.
def _spec(unit, meaning, *, state=None, cell=True):
    return {"unit": unit, "meaning": meaning, "state": state, "cell": cell}


def _cells(entries, prefix=""):
    return {prefix + path: _spec(unit, meaning) for path, (unit, meaning) in entries.items()}


def _native(entries, prefix="", state=None):
    return {prefix + path: _spec(unit, meaning, cell=False,
        state=state + path if state else None) for path, (unit, meaning) in entries.items()}


_MODEL = _native({
    "length": ("match_state_count", "Native LENG: declared model match states."),
    "sequence_count": ("sequence_count", "Native NSEQ: training sequence count."),
    "effective_sequence_count": ("effective_sequence_count", "Native EFFN: effective training sequence count."),
    "maximum_length": ("residue_count", "Native MAXL: maximum expected hit length."),
    "checksum": ("checksum", "Native CKSUM digital sequence checksum; an identifier, not confidence."),
})
for _tag in ("GA", "TC", "NC"):
    for _part in ("sequence", "domain"):
        _MODEL[f"cutoffs.{_tag}.{_part}"] = _spec("bit", f"Native {_tag} {_part} score cutoff; no calibration is inferred.", cell=False)

_MODEL_COMPONENTS = _cells({
    "sequence_count": ("sequence_count", "Saved native NSEQ training count."),
    "effective_sequence_count": ("effective_sequence_count", "Saved native EFFN effective count."),
    "effective_sequence_ratio": ("effective_sequences_per_input_sequence", "Saved EFFN/NSEQ with its explicit positive NSEQ denominator."),
    "declared_length": ("match_state_count", "Saved native declared LENG."),
    "match_state_count": ("decoded_match_row_count", "Count of decoded match-position rows, separate from declared length."),
    "mean_match_entropy": ("bit_per_match_position", "Saved mean -sum(p log2 p) over every declared match position; raw probabilities are not normalized."),
    "mean_match_relative_entropy": ("bit_per_match_position", "Saved mean sum(p log2(p/q)) over every declared match position and explicit background q."),
})
for _container in ("composition", "initial.insert", "initial.transitions.M", "initial.transitions.I", "initial.transitions.D"):
    for _name in ("mass", "mass_residual"):
        _MODEL_COMPONENTS[_container + "." + _name] = _spec("probability_mass",
            "Saved " + ("probability sum" if _name == "mass" else "probability sum minus one") +
            " for " + _container + "; transition M/I/D outgoing populations stay separate.")

_A_CALC = {
    "population": _cells({
        "decoded_model_count": ("decoded_model_count", "Decoded models in the declared input or output population; unsupported decoding stays unknown."),
        "complete_model_count": ("complete_decoded_model_count", "Terminated decoded models without fatal extraction issues."),
        "primary_name_count": ("primary_name_occurrence_count", "Occurrences of usable native NAME headers."),
        "accession_count": ("accession_occurrence_count", "Occurrences of usable native ACC headers."),
        "distinct_primary_name_count": ("distinct_name_count", "Distinct usable NAME values in this direction's model population."),
        "distinct_accession_count": ("distinct_accession_count", "Distinct usable ACC values in this direction's model population."),
        "model_artifact_bytes": ("byte", "Sum of actual retained model artifact bytes in this direction."),
    }),
    "model_comparison": _cells({
        "source_length": ("match_state_count", "Source model's native LENG."),
        "output_length": ("match_state_count", "Output model's native LENG."),
        "length_difference": ("match_state_count", "Saved output LENG minus source LENG."),
        "source_cell_count": ("decoded_probability_cell_count", "Decoded source model body probability cells."),
        "output_cell_count": ("decoded_probability_cell_count", "Decoded output model body probability cells."),
        "compared_cell_count": ("compared_probability_cell_count", "Cells with comparable probabilities in the saved pair."),
        "max_absolute_probability_difference": ("absolute_probability_difference", "Largest absolute output-minus-source difference among compared cells."),
        "mean_absolute_probability_difference": ("absolute_probability_difference_per_compared_cell", "Sum of absolute differences divided by compared_cell_count; incomplete state is preserved."),
        **{name + "_optional_field_count": ("optional_field_path_count", "Count of saved optional field paths classified " + name + ".") for name in ("retained", "lost", "changed", "gained")},
    }),
    "key_population": _cells({
        name: ("decoded_model_count" if name == "returned_model_occurrence_count" else name, meaning)
        for name, meaning in {
            "requested_key_count": "All requested key occurrences, including repetitions.",
            "distinct_key_count": "Distinct requested key strings.",
            "resolved_key_count": "Key associations whose saved state is resolved.",
            "missing_key_count": "Key associations whose saved state is missing.",
            "ambiguous_key_count": "Key associations whose saved state is ambiguous.",
            "unknown_key_count": "Key associations whose saved state is unknown.",
            "fulfilled_key_count": "Requested keys with validated returned model associations.",
            "duplicate_key_occurrence_count": "Requested occurrences minus distinct key strings.",
            "selected_source_occurrence_count": "Distinct source model occurrences selected by the saved key associations.",
            "returned_model_occurrence_count": "Decoded returned model occurrences; alias duplicates remain separate.",
            "expected_returned_model_occurrence_count": "Expected output occurrences from the actual indexed/unindexed retrieval semantics.",
            "duplicate_representation_count": "Matched returned source occurrences minus distinct source occurrences.",
        }.items()}),
    "artifact": {**_cells({
        "size_bytes": ("byte", "Actual retained bytes for this artifact occurrence."),
        "decoded_record_count": ("decoded_model_count", "M1 decoded count; opaque binary and HMMER2 counts stay unavailable."),
    }), "offset_width": _spec("byte", "Native SSI offset width from its framing header.", cell=False)},
    "index_summary": _cells({
        **{"native_" + name: (name, "Native reported index " + name + ".") for name in ("model_count", "primary_name_count", "accession_count")},
        **{"decoded_input_" + name: (unit, "Decoded input " + name + " used in the native-summary comparison.") for name, unit in (("model_count", "decoded_model_count"), ("primary_name_count", "primary_name_occurrence_count"), ("accession_count", "accession_occurrence_count"))},
        **{name + "_difference": (name, "Native reported minus decoded input " + name + ".") for name in ("model_count", "primary_name_count", "accession_count")},
    }),
    "bundle": _cells({"member_count": ("present_bundle_member_count", "Captured pressed bundle member occurrences."),
        "bundle_byte_sum": ("byte", "Sum of captured .h3m/.h3i/.h3f/.h3p bytes; partial sums keep incomplete state.")}),
}
_A_NATIVE = {
    "artifact_metadata": _native({"measured_size_bytes": ("byte", "Byte count measured by the saved reader."),
        "offset_width": ("byte", "Native SSI offset width when its header was decoded."),
        "decoded_record_count": ("decoded_model_count", "Saved framing-only decoded count; this reader does not infer binary contents.")}),
    "requested_key": {}, "reported_path": {}, "diagnostic": {},
    "index_summary": _native({name: ("count", "Native index summary " + name + ".") for name in ("model_count", "primary_name_count", "accession_count")}),
}
_A_CHECKS = set("parameters_valid supplied_bytes_match_occurrence capture_complete model_population_complete conversion_population_equal model_relationship model_probability_equivalence expected_revision required_member_present member_nonempty binary_framing binary_internal_content supplied_artifact_binding authenticated_artifact_custody bundle_supplied_attempt_consistency bundle_revision_consistent native_model_count native_primary_name_count native_accession_count source_primary_names_unique source_accessions_unique requested_keys_unique all_requested_keys_resolved all_requested_keys_returned fetch_output_population native_diagnostics conversion_stdout_equal".split())

_B_UNITS = {
    "input_sequence_count": "sequence_count", "input_column_count": "alignment_column_count", "rf_consensus_count": "RF_consensus_column_count",
    "resaved_sequence_count": "sequence_count", "resaved_column_count": "resaved_alignment_column_count", "model_length": "match_state_count",
    "model_alignment_fraction": "match_states_per_input_alignment_column", "effective_sequence_count": "effective_sequence_count",
    "effective_input_sequence_ratio": "effective_sequences_per_input_sequence", "native_relative_entropy": "bit_per_match_position",
    "mean_match_entropy": "bit_per_match_position", "mean_match_relative_entropy": "bit_per_match_position",
    "requested_interval_count": "request_interval_count", "requested_union_count": "distinct_alignment_column_count",
    "actual_masked_count": "alignment_column_count", "newly_masked_count": "alignment_column_count", "removed_masked_count": "alignment_column_count",
    "retained_masked_count": "alignment_column_count", "masked_fraction": "masked_columns_per_input_alignment_column", "input_masked_count": "alignment_column_count",
    "input_alignment_count": "decoded_alignment_record_count", "processed_alignment_count": "output_validated_alignment_record_count",
    "unprocessed_alignment_count": "decoded_unprocessed_alignment_record_count", "mapped_model_position_count": "model_position_count", "native_mapping_row_count": "decoded_mapping_row_count",
}
_B_MEANINGS = {
    "input_sequence_count": "Sequence rows in the source alignment.", "input_column_count": "Source alignment width before Plan7 resaving.",
    "rf_consensus_count": "Non-gap RF columns in the source alignment.", "resaved_sequence_count": "Sequence rows in the separately saved output alignment.",
    "resaved_column_count": "Width in the separate resaved alignment coordinate system.", "model_length": "Native output model LENG.",
    "model_alignment_fraction": "Saved model match states divided by source alignment columns.",
    "effective_sequence_count": "Native output model EFFN.", "effective_input_sequence_ratio": "Saved output EFFN divided by source sequence count.",
    "native_relative_entropy": "Native printed build re/pos, separate from the independent KL calculation.",
    "mean_match_entropy": "Saved mean match entropy across all declared model positions.",
    "mean_match_relative_entropy": "Saved mean match KL against the explicitly supplied background.",
    "requested_interval_count": "Number of selected range occurrences, including overlaps.",
    "requested_union_count": "Distinct source alignment columns in the union of requested inclusive spans; mapping mode leaves this unmeasured.",
    "actual_masked_count": "Columns carrying m in the output MM annotation.", "newly_masked_count": "Output masked columns absent from source MM.",
    "removed_masked_count": "Source masked columns absent from output MM.", "retained_masked_count": "Intersection of source and output masked columns.",
    "masked_fraction": "Saved output masked-column count divided by source alignment width.", "input_masked_count": "Source MM masked columns; native absent MM means an empty mask.",
    "input_alignment_count": "Decoded source alignment records; unsupported population remains unknown.",
    "processed_alignment_count": "Source alignment record with validated native output; attempted selection alone is not completion.",
    "unprocessed_alignment_count": "Decoded source alignment records remaining after validated processing of the first record.",
    "mapped_model_position_count": "Positions in the saved deterministic model-to-source-alignment map.",
    "native_mapping_row_count": "Decoded native mapping rows; an existing empty output has zero rows with its saved qualification.",
}
_B_BUILD_NAMES = set("input_sequence_count input_column_count rf_consensus_count resaved_sequence_count resaved_column_count model_length model_alignment_fraction effective_sequence_count effective_input_sequence_ratio native_relative_entropy mean_match_entropy mean_match_relative_entropy".split())
_B_MASK_NAMES = set(_B_UNITS) - _B_BUILD_NAMES | {"input_sequence_count", "input_column_count", "rf_consensus_count"}
_B_CALC = {kind: _cells({name: (_B_UNITS[name], _B_MEANINGS[name]) for name in names}, "components.")
    for kind, names in (("build", _B_BUILD_NAMES), ("mask", _B_MASK_NAMES), ("mapping", _B_MASK_NAMES - set("actual_masked_count newly_masked_count removed_masked_count retained_masked_count masked_fraction input_masked_count".split())))}
_B_CALC["mapping"]["components.requested_union_count"]["unit"] = "alignment_column_count"
_B_CALC["build"].update({"model_components." + name: value for name, value in _MODEL_COMPONENTS.items()})
_B_CHECKS = set("artifact_binding source_geometry output_geometry association summary_counts summary_eff_nseq summary_relative_entropy source_checksum model_map rf_model_length sequence_membership sequence_content alignment_width mask_annotation requested_ranges range_capacity native_mapping model_components parameter_valid input_population_processed output_symbol_changes fragment_marking alphabet".split())

_E_CALC = {
    "generated_record": _cells({
        "length": ("residue_count", "Generated ASCII letter residues, excluding gaps, stop and missing symbols."),
        "canonical_residue_count": ("residue_count", "Generated residues in the saved model's canonical alphabet."),
        "ambiguous_residue_count": ("residue_count", "Generated BJZX amino or RYMKSWBDHVN nucleotide residues."),
        "noncanonical_unambiguous_residue_count": ("residue_count", "Generated amino O/U residues, separately retained."),
        "ambiguous_fraction": ("fraction_of_ungapped_residues", "Saved ambiguity count divided by positive generated residue length."),
        "gap_count": ("gap_count", "Generated alignment '-', '.' and '_' symbols."),
        "stop_count": ("stop_symbol_count", "Generated '*' symbols."),
        "missing_symbol_count": ("missing_data_symbol_count", "Generated '~' symbols."),
        "invalid_symbol_count": ("symbol_count", "Generated symbols outside the saved alphabet and recognized special symbols."),
    }),
    "model": _cells({
        "input_model_length": ("model_match_state_count", "Input model's native declared length."),
        "selected_N": ("requested_sample_count", "Explicit selected -N, separately missing in consensus mode."),
        "configured_expected_length": ("configured_expected_residue_count", "Explicit -L profile expected length; not a measured generated length."),
        "captured_sample_count": ("captured_generated_record_count", "Generated records associated with this exact model occurrence."),
        "expected_output_count": ("expected_generated_record_count", "Saved count expected from consensus mode or explicit -N."),
        "count_difference": ("captured_minus_expected_record_count", "Captured records minus expected generated records."),
        "total_length": ("residue_count", "Sum of lengths of associated captured generated records."),
        "minimum_length": ("residue_count", "Minimum associated generated record length."),
        "maximum_length": ("residue_count", "Maximum associated generated record length."),
        "mean_length": ("residues_per_captured_record", "Sum of generated lengths divided by captured record count."),
    }),
    "alignment": _cells({"alignment_width": ("alignment_column_count", "Width of the captured generated alignment."),
        "rf_match_column_count": ("rf_match_column_count", "Non-gap generated RF columns."),
        "captured_row_count": ("captured_generated_record_count", "Rows in the captured generated alignment.")}),
    "consensus": _cells({"mismatch_count": ("nominal_consensus_mismatch_count", "Native consensus disagreements with the saved nominal maximum-probability choices, including length difference."),
        "certain_mismatch_count": ("certain_consensus_mismatch_count", "Native symbols outside all choices allowed by explicit rounding tolerance, including length difference."),
        "ambiguous_position_count": ("decoded_ambiguous_position_count", "Decoded positions with multiple possible choices under the supplied tolerance.")}),
}
_E_CHECKS = {"sample_population_count", "alignment_geometry", "rf_matches_model_length", "consensus_agreement", "consensus_length"}
_S_SUMMARY_UNITS = {name: "inverse_bit" if name in {"lambda", "plambda"} else "dimensionless" if name == "tailp" else "sequence" if name.startswith("E10") else "trace_state" if name in {"almean", "alsd"} else "bit"
    for name in "tailp mu lambda E10 mufix E10fix mufix2 E10fix2 pmu plambda E10p almean alsd".split()}
_S_SUMMARY_MEANINGS = {
    "tailp": "Native selected fitting tail probability mass.", "mu": "Native fitted Gumbel location or Forward exponential tail threshold.",
    "lambda": "Native fitted inverse-bit scale.", "E10": "Native expected count at the tenth highest generated score under the independent fit.",
    "mufix": "Native location with fixed lambda.", "E10fix": "Native expected count at the tenth score using fixed lambda.",
    "mufix2": "Native location using native calibrated lambda.", "E10fix2": "Native expected count using native calibrated lambda.",
    "pmu": "Native printed calibration location; Hybrid's undetermined state is preserved.", "plambda": "Native printed calibrated inverse-bit scale.",
    "E10p": "Native expected count at the tenth score using printed calibration.", "almean": "Native mean M+D+I trace-state count.",
    "alsd": "Native sample standard deviation of M+D+I trace-state counts.",
}
_S_CALC = {
    "native_summary": _cells({name: (unit, _S_SUMMARY_MEANINGS[name]) for name, unit in _S_SUMMARY_UNITS.items()}, "components."),
    "native_rounding_residuals": _cells({name: (unit, "Saved independent minus native printed " + name + "; original sign and comparison qualification are retained.") for name, unit in _S_SUMMARY_UNITS.items() if name not in {"tailp", "pmu", "plambda"}}, "components."),
    "score_statistics": _cells({
        "observed_count": ("sequence", "Decoded generated score occurrences, separate from selected -N."),
        "declared_population": ("sequence", "Explicit selected -N denominator."),
        "mean": ("bit", "Saved complete-population score sum divided by observed_count."),
        "min": ("bit", "Minimum complete-population generated score."), "max": ("bit", "Maximum complete-population generated score."),
        "sample_variance": ("bit_squared", "Saved squared score residual sum divided by observed_count minus one."),
        "x10": ("bit", "Tenth highest score occurrence, retaining ties; requires ten occurrences."),
    }, "components."),
    "fit": _cells({
        "mu": ("bit", "Saved fit-variant location; Gumbel ML or selected Forward tail threshold."),
        "lambda": ("inverse_bit", "Saved fit-variant inverse-bit scale; original variant and calibration remain in retained data."),
        "survival_at_x10": ("dimensionless", "Saved fitted survival at the tenth highest score."),
        "E10": ("sequence", "Saved population times effective tail mass times survival at the tenth score."),
        "tail_mass": ("dimensionless", "Explicit selected tail mass for this saved fit row."),
        "tail_count": ("sequence", "Selected tail occurrence count; Forward uses floor(N*tail_mass)."),
        "tail_threshold": ("bit", "Smallest score in the selected tail population."),
    }, "components."),
    "alignment_statistics": _cells({"observed_count": ("sequence", "Observed native traceback rows in this occurrence/model group."),
        "alignment_mean": ("trace_state", "Saved mean native M+D+I trace-state count."),
        "alignment_sample_sd": ("trace_state", "Saved sample standard deviation of native M+D+I counts.")}, "components."),
}
for _kind in ("filter_recalculation", "native_experimental_filter_replay", "native_filter"):
    _S_CALC[_kind] = _cells({"count": ("sequence", "Saved generated-score passing occurrence count for this declared filter variant."),
        "fraction": ("dimensionless", "Saved passing count divided by explicit -N.")}, "components.")
_S_CALC["native_filter"]["components.rounding_residual"] = _spec("dimensionless", "Saved count/N minus native printed passing fraction.")
_S_CHECKS = {"native_rounding." + name for name in _S_SUMMARY_UNITS if name not in {"tailp", "pmu", "plambda"}} | {
    "hybrid_native_experimental_filter_count", "native_filter_count", "alignment_score_correspondence", "native_filter_fraction"}

_H_CALC = _cells({
    **{name: (spec["unit"], spec["meaning"]) for name, spec in _MODEL_COMPONENTS.items() if name in {"sequence_count", "effective_sequence_count", "effective_sequence_ratio", "mean_match_entropy", "mean_match_relative_entropy"}},
    "background_entropy": ("bit", "Saved -sum(q log2 q) for the explicitly supplied background."),
    "mean_match_information": ("bit_per_match_position", "Saved background entropy minus mean model match entropy."),
    "occupancy_sum": ("expected_match_state_count", "Saved sum of match-state occupancy from model transitions."),
    "entry_occupancy_sum": ("expected_match_state_count", "Saved occupancy sum over positions 2 through M."),
    "weighted_emission_relative_entropy": ("bit_per_occupied_match_state", "Saved occupancy-weighted match KL divided by positive occupancy sum."),
    "mean_entry_transition_term": ("bit_per_occupied_entry_state", "Saved weighted entry-transition log terms divided by entry occupancy, using explicit length probability."),
    "position_relative_entropy": ("bit_per_match_position", "Saved weighted emission relative entropy plus mean entry-transition term."),
    "composition_weight_sum": ("expected_emission_mass", "Saved sum of occupancy-weighted model emission masses."),
    "composition_relative_entropy": ("bit", "Saved normalized weighted composition KL against the explicit background."),
}, "components.")

_F_DATABASE = {
    "source_occurrence_count": ("sequence_occurrences", "Decoded source FASTA sequence occurrences."),
    "source_artifact_count": ("artifacts", "Supplied original source artifact occurrences."),
    "source_symbol_total": ("source_symbols", "Sum of decoded source sequence symbol counts."),
    "stored_segment_count": ("segments", "Decoded FM segment metadata rows; unknown when body decoding is unavailable."),
    "distinct_target_count": ("source_target_ids", "Distinct native source target IDs in decoded segments."),
    "declared_total_char_count": ("source_symbols_excluding_block_overlap", "Native total_char_count header excluding repeated block overlap."),
    "actual_database_bytes": ("bytes", "Actual captured database bytes, including headers and arrays."),
    "indexed_symbols": ("index_symbols_including_block_overlap", "Saved sum of forward block N-1, including overlap."),
    "indexed_unique_symbols": ("index_symbols_excluding_block_overlap", "Saved sum of forward block N-1-overlap."),
    "sentinel_count": ("logical_text_block_sentinels", "Decoded forward blocks, each with one logical sentinel."),
    "stored_bwt_sentinel_count": ("stored_section_sentinels", "Decoded forward/reverse BWT sections, each with one sentinel."),
    "ambiguity_range_count": ("stored_ranges", "Decoded ambiguity metadata ranges."),
    "covered_source_symbols": ("source_symbols", "Saved union length of validated source-coordinate segment intervals."),
    "ambiguity_union_symbols": ("source_symbols", "Saved source-coordinate ambiguity union length."),
    "ambiguity_fraction": ("fraction", "Saved ambiguity union symbols divided by positive source_symbol_total."),
}
_F_CALC = {
    "database_summary": _cells(_F_DATABASE, "components."),
    "block_validation": _cells({"bwt_symbol_mismatch_count": ("symbols", "Saved LF-cycle preceding-symbol mismatches against retained text."),
        "lf_visited_rows": ("rows", "Number of distinct BWT rows visited in the saved full LF consistency check.")}, "details."),
    "segment_validation": _cells({"compared_symbols": ("symbols", "Source segment symbols compared outside recorded ambiguous positions."),
        "mismatching_symbols": ("symbols", "Compared source/index symbol disagreements.")}, "components."),
    "location_validation": _cells({"native_anchor": ("one_based_source_coordinate", "Native f/r anchor in supplied source coordinates."),
        "query_length": ("symbols", "Saved literal query symbol length."), "interval_start": ("one_based_source_coordinate", "Saved inclusive source interval start."),
        "interval_end": ("one_based_source_coordinate", "Saved inclusive source interval end; reverse direction is reversal without complement.")}, "components."),
    "query_validation": _cells({name + "_location_count": ("location_occurrences", "Saved " + name + " locations for this exact query occurrence.") for name in ("valid", "invalid", "unresolved")}, "components."),
}
_F_EXACT = {
    "query_occurrence_count": ("query_occurrences", "Supplied literal query line occurrences, preserving duplicates."),
    "native_Q": ("query_occurrences_with_native_locations", "Native query occurrences with emitted locations; count-only uses raw intervals."),
    "native_H": ("native_emitted_location_occurrences", "Native emitted location occurrences; count-only uses raw FM intervals."),
    "native_R": ("query_occurrences_with_no_raw_interval", "Native query occurrences without a raw interval."),
    "native_unclassified_queries": ("query_occurrences", "Saved query count minus native_Q minus native_R, retaining negative/failed values."),
    "emitted_location_count": ("emitted_location_occurrences", "Decoded native location rows; absent in count-only mode."),
    **{name + "_location_count": ("emitted_location_occurrences", "Saved " + name + " classifications among emitted location occurrences.") for name in ("valid", "invalid", "unresolved")},
    "duplicate_location_count": ("repeated_resolved_tuple_occurrences", "Repeated resolved (query, source, direction, anchor) tuple occurrences."),
    **{name + "_location_fraction": ("fraction", "Saved " + name + " location count divided by positive emitted_location_count.") for name in ("valid", "invalid", "unresolved")},
    "expected_literal_location_count": (["literal_source_location_occurrences", "location_occurrences"], "Saved exhaustive literal-source location count when explicitly calculated; missing otherwise."),
    "missing_literal_location_count": ("location_occurrences", "Saved expected-minus-emitted tuple multiset count when explicitly compared."),
    "extra_literal_location_count": ("location_occurrences", "Saved emitted-minus-expected tuple multiset count when explicitly compared."),
}
_F_CALC["exactmatch_summary"] = _cells(_F_EXACT, "components.")
_F_DATABASE_CHECKS = {"source_custody", "decoded_layout", "dna_reader_compatibility", "metadata_partition", "total_char_count"}
_F_EXACT_CHECKS = {"native_query_population", "native_location_count", "native_location_query_count", "count_only_has_no_locations", "exhaustive_literal_agreement"}
_F_NULL_SCOPES = {
    "source_custody": {"supplied producer attempt and exact ordered source artifact identities/digests; independent symbol checks do not establish custody"},
    "decoded_layout": {"declared ABI, all metadata/arrays, framing, occurrence digest and byte count"},
    "dna_reader_compatibility": {"HMMER 3.4 fm_readFMmeta accepts DNA only; amino writer decoding is separate"},
    "metadata_partition": {"forward block sections refer once to every ordered segment/range row; paired sections share those rows"},
    "total_char_count": {"declared total, supplied source symbols, and sum(N-1-overlap) agree; no completeness inference for matches"},
    "native_query_population": {"count-only Q+R=N; locations Q+R<=N because native filters can discard every raw match; H>=Q"},
    "native_location_count": {"native location H versus parsed emitted rows; does not assert literal validity"},
    "native_location_query_count": {"native location Q versus emitted query groups; duplicate query occurrences stay separate"},
    "count_only_has_no_locations": {"count-only output must contain no locations; missing file remains missing"},
    "exhaustive_literal_agreement": {
        "multiset of every complete supplied query/source occurrence, enabled direction and native anchor; aggregate equality alone is insufficient",
        "complete source/query populations, known directions and unambiguous complete native locations required"},
}
_F_CHECKS = _F_DATABASE_CHECKS | _F_EXACT_CHECKS | set("decoded_array_symbols bwt_text_consistency suffix_samples counter_rows sentinel_encoding block_offsets paired_block_metadata ambiguity_bounds block_segment_coverage segment_coordinates segment_name source_symbols_outside_ambiguities source_ambiguity_membership block_overlap source_coverage hit_bounds hit_symbols hit_ambiguity hit_index_membership hit_source_name hit_duplicate_tuple".split())


def _definitions(program, mode):
    if type(program) is not str or program not in PROGRAM_MODES or type(mode) is not str or mode not in PROGRAM_MODES[program]:
        _error("program_mode_invalid")
    family = _FAMILIES[program]
    if family == "artifact":
        kinds = {name: deepcopy(value) for name, value in _A_CALC.items()
                 if name in {"population", "artifact"} or name == "bundle" and program == "hmmpress"
                 or name == "index_summary" and mode == "index" or name == "model_comparison" and mode != "index"
                 or name == "key_population" and program == "hmmfetch" and mode != "index"}
        return {"input_records": {"model": _MODEL}, "output_records": {"model": _MODEL},
            "native_rows": _A_NATIVE, "calculations": kinds}, _A_CHECKS
    if family == "alignment_preparation":
        kind = "build" if program == "hmmbuild" else "mask" if mode.startswith("mask_") else "mapping"
        coordinate = "one_based_model_position" if mode in {"mask_model", "model_to_alignment"} else "one_based_alignment_column"
        target = "one_based_alignment_column" if mode == "model_to_alignment" else "one_based_model_position"
        native = {"population": {"decoded_count": _spec("decoded_alignment_record_count", "Saved decoded alignment-record population; unsupported remains unknown.", cell=False, state="state")}}
        if program == "hmmbuild":
            native["build_summary"] = _native({"nseq": ("sequence_count", "Native reported source sequence count."), "alen": ("alignment_column_count", "Native source alignment columns."),
                "mlen": ("match_state_count", "Native output model match positions."), "W": ("residue_count", "Native maximum expected hit length."),
                "eff_nseq": ("effective_sequence_count", "Native effective training sequence count."), "re_per_position": ("bit_per_match_position", "Native printed model relative entropy per position.")})
        else:
            native["requested_interval"] = _native({name: (coordinate, "Selected inclusive " + name + " in the declared source coordinate system.") for name in ("start", "end")})
            if kind == "mapping":
                native["mapping"] = _native({name: (target if name.startswith("target_") else coordinate, "Native or requested inclusive " + name + "; coordinate system is fixed by this operation mode.")
                    for name in ("requested_start", "requested_end", "returned_source_start", "returned_source_end", "target_start", "target_end")})
        align = _native({"column_count": ("alignment_column_count", "Saved native alignment width."), "block_count": ("alignment_block_count", "Saved interleaved alignment block count.")})
        return {"input_records": {"alignment": align}, "output_records": {"alignment": align, "model": {}}, "native_rows": native, "calculations": {kind: _B_CALC[kind]}}, _B_CHECKS
    if family == "emission":
        kinds = {"generated_record": _E_CALC["generated_record"], "model": _E_CALC["model"]}
        if mode.startswith("consensus_"):
            kinds["consensus"] = _E_CALC["consensus"]
        if mode == "sample_core_aligned":
            kinds["alignment"] = _E_CALC["alignment"]
        out = {"alignment": _native({"native.column_count": ("alignment_column_count", "Saved generated Stockholm width."), "native.block_count": ("alignment_block_count", "Saved generated Stockholm block count.")}), "alignment_row": {}} if mode == "sample_core_aligned" else {"fasta": {}}
        return {"output_records": out, "native_rows": {name: {} for name in ("line", "fasta_header", "fasta_sequence", "header", "terminator", "sequence", "GC", "GR", "GS", "GF", "comment", "blank", "invalid")}, "calculations": kinds}, _E_CHECKS
    if family == "statistics":
        native = _native({"nseq": ("sequence_count", "Native reported training sequence count."), "eff_nseq": ("effective_sequence_count", "Native reported effective sequence count."),
            "M": ("match_state_count", "Native reported model length."), "relent": ("bit_per_match_position", "Native mean model relative entropy."),
            "info": ("bit_per_match_position", "Native mean model information."), "p_relE": ("bit_per_match_position", "Native position relative entropy."),
            "compKL": ("bit", "Native model composition KL.")}, "values.", "states.")
        return {"native_rows": {"model_statistic": native}, "calculations": {"model_statistic": _H_CALC}}, {"native_rounding_agreement"}
    if family == "simulation":
        summary = {name: (unit, _S_SUMMARY_MEANINGS[name]) for name, unit in _S_SUMMARY_UNITS.items() if mode != "forward" or name not in {"mufix2", "E10fix2"}}
        native = {
            "summary": _native(summary, "payload.values.", "payload.states."),
            "scores": _native({"declared_population": ("sequence", "Explicit -N for this generated vector."), "observed_count": ("sequence", "Actually decoded vector count; unavailable without the original ABI.")}, "payload."),
            "alignments": _native({"trace_state_count": ("trace_state", "Native M+D+I trace-state count."), "score": ("bit", "Native printed generated alignment score.")}, "payload.", "payload.states."),
            "filter": {**_native({"count": ("sequence", "Native passing score occurrences."), "fraction": ("dimensionless", "Native printed passing fraction.")}, "payload.", "payload.states."),
                "payload.denominator": _spec("sequence", "Explicit -N filter denominator.", cell=False)}, "xy_series": {},
        }
        calc = deepcopy(_S_CALC)
        if mode == "forward":
            for kind in ("native_summary", "native_rounding_residuals"):
                for name in ("mufix2", "E10fix2"):
                    calc[kind].pop("components." + name, None)
        if mode != "viterbi":
            calc.pop("alignment_statistics")
        if mode != "hybrid":
            calc.pop("native_experimental_filter_replay")
        return {"input_records": {"model": _MODEL}, "native_rows": native, "calculations": calc}, _S_CHECKS
    calc = deepcopy(_F_CALC)
    native = {"diagnostic": {}, "index_parameters": {"payload.value": _spec(["index_symbol_count", "suffix_array_sampling_interval"], "Native bin_length or suffix array sample rate only; categorical parameter rows have no numeric value.", state="payload.state", cell=False)}}
    if program == "makehmmerdb":
        for name in ("exactmatch_summary", "location_validation", "query_validation"):
            calc.pop(name)
    else:
        if mode == "count_only":
            calc["exactmatch_summary"]["components.native_Q"]["unit"] = "query_occurrences_with_raw_interval"
            calc["exactmatch_summary"]["components.native_H"]["unit"] = "raw_fm_interval_occurrences"
        native.update(exactmatch_hit=_native({"anchor": ("one_based_source_coordinate", "Native f/r source anchor; reversal has no complement.")}, "payload."),
            exactmatch_counts=_native({name: (calc["exactmatch_summary"]["components.native_" + name]["unit"], "Original native " + name + " count for the selected locations/count-only population.") for name in ("Q", "H", "R")}, "payload."))
    return {"input_records": {"fasta": {}, **({"query": {}} if program != "makehmmerdb" else {})}, "native_rows": native, "calculations": calc}, _F_CHECKS


def preparation_projection_catalog(program, mode):
    """Closed scalar field/meaning catalogue; no values are discovered at runtime."""
    definitions, checks = _definitions(program, mode)
    result = {}
    for collection, kinds in definitions.items():
        quantities = {}
        for kind, fields in kinds.items():
            for path, spec in fields.items():
                descriptor = quantities.setdefault(path, {"unit": [], "meaning": [], "source": []})
                descriptor["unit"].extend(spec["unit"] if type(spec["unit"]) is list else [spec["unit"]])
                descriptor["meaning"].append(kind + ": " + spec["meaning"])
                descriptor["source"].append(("calculations.rows" if collection == "calculations" else "sheet." + collection) + "/" + kind + "/" + path)
        for descriptor in quantities.values():
            units = sorted(set(descriptor["unit"]))
            descriptor["unit"] = units[0] if len(units) == 1 else units
            descriptor["meaning"] = " ".join(descriptor["meaning"])
            descriptor["source"] = "; ".join(descriptor["source"])
        result[collection] = {"quantities": dict(sorted(quantities.items())), "checks": sorted(checks)}
    return result


_ALL_PATHS = sorted({path for program, modes in PROGRAM_MODES.items() for mode in modes
    for entry in preparation_projection_catalog(program, mode).values() for path in entry["quantities"]})
_ALL_CHECKS = sorted(_A_CHECKS | _B_CHECKS | _E_CHECKS | _S_CHECKS | _F_CHECKS | {"native_rounding_agreement"})
_ALL_KINDS = sorted({kind for program, modes in PROGRAM_MODES.items() for mode in modes
    for kinds in _definitions(program, mode)[0].values() for kind in kinds})
_ALL_UNITS = sorted({unit for program, modes in PROGRAM_MODES.items() for mode in modes
    for kinds in _definitions(program, mode)[0].values() for fields in kinds.values()
    for spec in fields.values() for unit in (spec["unit"] if type(spec["unit"]) is list else [spec["unit"]])})
_ALL_ROLES, _ALL_FORMATS = set(), set()
for _program, _modes in PROGRAM_MODES.items():
    for _mode in _modes:
        for _contract in (operand_contract, output_contract):
            for _mapping in _contract(_program, _mode):
                _ALL_ROLES.update(_mapping)
                for _formats in _mapping.values():
                    _ALL_FORMATS.update(_formats)


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def _reference(namespace, *, identifier=False, nullable=False):
    return {"type": ["string", "null"] if nullable else "string", "format": "identifier" if identifier else "reference", "x-reference-namespace": namespace}


_SOURCE = _reference("execution_result")
_ARTIFACT = _reference("artifact")
_KEY = _reference("native_hmmer_preparation_row", identifier=True)
_SELECTION = _object({"direction": {"type": "string", "enum": list(_DIRECTIONS)},
    "role": {"type": "string", "enum": sorted(_ALL_ROLES)}, "ordinal": {"type": "integer", "minimum": 0}})
_WINDOW = {"oneOf": [_object({"offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1}}),
    _object({"record_keys": {"type": "array", "minItems": 1, "uniqueItems": True, "items": _KEY}})]}
_PROJECTION = _object({"collection": {"type": "string", "enum": list(_COLLECTIONS)}, "rows": _WINDOW,
    "quantities": {"type": "array", "uniqueItems": True, "items": {"type": "string", "enum": _ALL_PATHS}},
    "checks": {"type": "array", "uniqueItems": True, "items": {"type": "string", "enum": _ALL_CHECKS}}})
NATIVE_HMMER_PREPARATION_RESULT_SELECTOR_SCHEMA = _object({
    "version": {"const": "native_hmmer_preparation_result_selector_v1"},
    "acquisition": {"const": "complete_bound_bundle"}, "projection": {"oneOf": [_PROJECTION, {"type": "null"}]},
    "artifacts": {"type": "array", "uniqueItems": True, "items": _SELECTION}})
NATIVE_HMMER_PREPARATION_RESULT_SELECTOR_SCHEMA["anyOf"] = [
    {"properties": {"artifacts": {"minItems": 1}}},
    {"properties": {"projection": {"type": "object", "anyOf": [
        {"properties": {"quantities": {"minItems": 1}}}, {"properties": {"checks": {"minItems": 1}}}]}}}]
_CHECK_OCCURRENCE = _object({**_SELECTION["properties"], "artifact_ref": _ARTIFACT})
ROW_SCHEMA = _object({"record_key": _KEY, "kind": {"type": "string", "enum": _ALL_KINDS},
    "name": _reference("native_hmmer_preparation_name", identifier=True, nullable=True),
    "accession": _reference("native_hmmer_preparation_accession", identifier=True, nullable=True),
    "source_ref": _SOURCE, "artifact_ref": _reference("artifact", nullable=True),
    "quantities": {"type": "array", "items": _object({"path": {"type": "string", "enum": _ALL_PATHS},
        "value": {"type": ["number", "null"]}, "state": {"type": "string", "enum": sorted(_STATES)},
        "unit": {"type": ["string", "null"], "enum": [*_ALL_UNITS, None]}})},
    "checks": {"type": "array", "items": _object({"name": {"type": "string", "enum": _ALL_CHECKS},
        "outcome": {"type": "string", "enum": sorted(_OUTCOMES)},
        "occurrences": {"type": "array", "items": _CHECK_OCCURRENCE, "uniqueItems": True}})}})
ARTIFACT_SCHEMA = _object({"source_ref": _SOURCE, **_SELECTION["properties"], "artifact_ref": _ARTIFACT,
    "format": {"type": "string", "enum": sorted(_ALL_FORMATS)}, "size_bytes": {"type": "integer", "minimum": 0},
    "sha256": _reference("native_hmmer_preparation_sha256", identifier=True),
    "completeness": {"type": "string", "enum": ["complete", "partial", "unknown"]}})
POPULATION_SCHEMA = _object({"source_ref": _SOURCE,
    "collection": {"type": ["string", "null"], "enum": [*_COLLECTIONS, None]},
    **{name: {"type": "integer", "minimum": 0} for name in ("total_records", "returned_records", "omitted_records", "requested_artifact_count", "returned_artifact_count")},
    "missing_record_keys": {"type": "array", "items": _KEY, "uniqueItems": True},
    "missing_artifacts": {"type": "array", "items": _SELECTION, "uniqueItems": True}})
FAILURE_STAGES = ("software", "inputs", "staging", "preflight", "execution", "outputs", "capture", "prerequisite", "custody", "metadata", "native", "reading", "worker", "extraction", "parsing", "calculation", "grading", "projection", "selection", "format", "association", "validation", "unclassified")
FAILURE_SCHEMA = _object({"handoff_ref": _reference("execution_handoff"), "source_ref": _reference("execution_result", nullable=True),
    "stage": {"type": "string", "enum": list(FAILURE_STAGES)},
    "code": _reference("native_hmmer_preparation_failure_code", identifier=True),
    "record_key": _reference("native_hmmer_preparation_failure_record", identifier=True, nullable=True),
    "affected": {**_SELECTION, "type": ["object", "null"]}})
IDENTIFIER_NAMESPACES = tuple("native_hmmer_preparation_" + name for name in ("row", "name", "accession", "sha256", "failure_code", "failure_record"))


def preparation_fact_sources():
    descriptions = {
        "rows": (ROW_SCHEMA, "Requested saved numerical measurements and checks with exact row and artifact associations; generated values remain generated."),
        "artifacts": (ARTIFACT_SCHEMA, "Explicitly requested artifact occurrences and those required by selected rows/checks, preserving same-byte separate roles."),
        "population": (POPULATION_SCHEMA, "Decoded saved row and selected artifact accounting; this is not biological completeness."),
        "result_refs": (_SOURCE, "Original HMMER preparation result references."),
        "failures": (FAILURE_SCHEMA, "Recorded typed acquisition, grading or projection failures with their original handoff and affected occurrence."),
    }
    return {"execution_hmmer_preparation_" + name: {"type": "array", "meaning": meaning,
        "report_schema": {"type": "array", "items": deepcopy(schema), "x-source": "execution_hmmer_preparation_" + name}}
        for name, (schema, meaning) in descriptions.items()}


FACT_SOURCES = preparation_fact_sources()


def _unique_text_list(value, code):
    if type(value) is not list:
        _error(code)
    for item in value:
        _text(item)
    if len(set(value)) != len(value):
        _error("duplicate_request")


def _selection(value, program, mode):
    _fields(value, {"direction", "role", "ordinal"}, "artifact_selection_fields_invalid")
    _integer(value["ordinal"])
    if value["direction"] not in _DIRECTIONS:
        _error("artifact_direction_invalid")
    required, optional = (output_contract if value["direction"] == "output" else operand_contract)(program, mode)
    roles = {**required, **optional}
    if value["role"] not in roles or value["direction"] == "working_copy" and not (
            value["role"] == "models" and (program == "hmmpress" or program == "hmmfetch" and mode == "index")):
        _error("artifact_role_not_in_operation")
    return value["direction"], value["role"], value["ordinal"]


@_contract_errors("selector_structure_invalid")
def validate_preparation_result_selector(value, *, program, mode):
    """Validate exact typed selections without adding a default result window."""
    catalog = preparation_projection_catalog(program, mode)
    _finite_json(value)
    _fields(value, {"version", "acquisition", "projection", "artifacts"}, "selector_fields_invalid")
    if value["version"] != "native_hmmer_preparation_result_selector_v1" or value["acquisition"] != "complete_bound_bundle":
        _error("selector_version_or_acquisition_invalid")
    if type(value["artifacts"]) is not list:
        _error("artifact_selections_list_required")
    selected = [_selection(item, program, mode) for item in value["artifacts"]]
    if len(set(selected)) != len(selected):
        _error("duplicate_artifact_request")
    projection = value["projection"]
    if projection is not None:
        _fields(projection, {"collection", "rows", "quantities", "checks"}, "projection_fields_invalid")
        if type(projection["collection"]) is not str or projection["collection"] not in catalog:
            _error("collection_not_in_operation")
        entry = catalog[projection["collection"]]
        for name in ("quantities", "checks"):
            _unique_text_list(projection[name], "requested_fields_list_required")
            if set(projection[name]) - set(entry[name]):
                _error("field_not_in_operation_collection")
        window = projection["rows"]
        if type(window) is dict and set(window) == {"offset", "limit"}:
            _integer(window["offset"])
            _integer(window["limit"], 1)
        else:
            _fields(window, {"record_keys"}, "row_selection_invalid")
            _unique_text_list(window["record_keys"], "record_keys_list_required")
            if not window["record_keys"]:
                _error("record_keys_nonempty_required")
    if not value["artifacts"] and (projection is None or not projection["quantities"] and not projection["checks"]):
        _error("empty_selection")
    return deepcopy(value)


def _read(row, path):
    value = row
    for part in path.split("."):
        if value is None:
            return None
        if type(value) is not dict:
            _error("declared_field_container_invalid")
        if part not in value:
            return None
        value = value[part]
    return value


def _key(row, family, collection):
    if type(row) is not dict:
        _error("row_object_required")
    key = row.get("row_key") if family == "artifact" and "row_key" in row else row.get("record_key")
    if collection == "calculations" and key is None:
        if family == "emission" and row.get("kind") in {"model", "consensus"}:
            _text(row.get("model_record_key"))
            key = row["model_record_key"] + "#" + row["kind"]
        elif family == "fm" and row.get("kind") in {"database_summary", "exactmatch_summary"}:
            key = "aggregate/" + row["kind"]
    _text(key)
    return key


def _kind(row, family, collection):
    if family == "statistics":
        return "model_statistic"
    if family in {"artifact", "simulation"} and collection in {"input_records", "output_records"}:
        return "model"
    kind = row.get("kind")
    _text(kind)
    return kind


class _Saved:
    """In-memory identity/relationship index; never a parser or calculator."""

    def __init__(self, grading, occurrences):
        _finite_json(grading)
        _fields(grading, {"version", "operation", "formats", "metadata", "native_abi", "requested_parameters", "sheet", "calculations"}, "grading_fields_invalid")
        if grading["version"] != "native_hmmer_preparation_grading_v1":
            _error("grading_version_invalid")
        operation = grading["operation"]
        _fields(operation, {"program", "mode", "engine_version", "settings"}, "operation_fields_invalid")
        self.program, self.mode = operation["program"], operation["mode"]
        self.definitions, self.check_names = _definitions(self.program, self.mode)
        self.family = _FAMILIES[self.program]
        if operation["engine_version"] != "3.4":
            _error("engine_version_invalid")
        if any(type(grading[name]) is not dict for name in ("formats", "metadata", "requested_parameters")) or type(operation["settings"]) is not dict:
            _error("grading_metadata_invalid")
        self.grading, self.sheet, self.calculations = grading, grading["sheet"], grading["calculations"]
        self.occurrences, self.slots, self.records, self.record_occurrences, self.collections = {}, {}, {}, {}, {}
        self.models, self.associations = {}, []
        self._context()
        _finite_json(occurrences)
        if type(occurrences) is not list:
            _error("occurrences_list_required")
        for occurrence in occurrences:
            _fields(occurrence, _OCCURRENCE_FIELDS, "occurrence_fields_invalid")
            slot = _selection({k: occurrence[k] for k in ("direction", "role", "ordinal")}, self.program, self.mode)
            for name in ("occurrence_id", "artifact_ref", "relative_path"):
                _text(occurrence[name])
            relative = occurrence["relative_path"]
            if relative.startswith("/") or "\\" in relative or any(p in {"", ".", ".."} for p in relative.split("/")):
                _error("occurrence_relative_path_invalid")
            _integer(occurrence["size_bytes"])
            if type(occurrence["sha256"]) is not str or not re.fullmatch("[0-9a-f]{64}", occurrence["sha256"]):
                _error("occurrence_digest_invalid")
            if occurrence["completeness"] not in {"complete", "partial", "unknown"}:
                _error("occurrence_completeness_invalid")
            required, optional = (output_contract if slot[0] == "output" else operand_contract)(self.program, self.mode)
            if occurrence["format"] not in {**required, **optional}[slot[1]]:
                _error("occurrence_format_invalid")
            oid = occurrence["occurrence_id"]
            if oid in self.occurrences or slot in self.slots:
                _error("occurrence_identity_ambiguous")
            self.occurrences[oid], self.slots[slot] = occurrence, occurrence
        for oid, fmt in grading["formats"].items():
            if oid not in self.occurrences or self.occurrences[oid]["format"] != fmt or self.occurrences[oid]["direction"] == "working_copy":
                _error("grading_format_occurrence_mismatch")
        if self.sheet is None or self.calculations is None:
            if self.sheet is not None or self.calculations is not None:
                _error("grading_availability_inconsistent")
            return
        _fields(self.sheet, {"schema", "operation", "artifact_occurrences", "issues"} | _SHEET_EXTRA[self.family], "sheet_fields_invalid")
        if self.sheet["schema"] != "hmmer_" + self.family + "_sheet_v1" or self.sheet["operation"] != operation:
            _error("sheet_schema_or_operation_mismatch")
        metadata = grading["metadata"]
        for name in ({"artifact_bindings"} if self.family == "artifact" else {"producer_contract", "source_binding"} if self.family == "fm" else set()):
            if self.sheet[name] != metadata.get(name, [] if name == "artifact_bindings" else None):
                _error("sheet_metadata_mismatch")
        if self.family == "simulation":
            expected_abi = {k: grading["native_abi"][k] for k in ("byte_order", "float_format", "bytes_per_float")} if grading["native_abi"] is not None else None
            if self.sheet["native_abi"] != expected_abi:
                _error("sheet_native_abi_mismatch")
        calcfields = {"schema", "operation", "parameters", "rows", "checks", "issues"} | ({"model_components"} if self.family == "statistics" else set())
        _fields(self.calculations, calcfields, "calculation_fields_invalid")
        if self.calculations["schema"] != "hmmer_" + self.family + "_components_v1" or self.calculations["operation"] != operation:
            _error("calculation_schema_or_operation_mismatch")
        if type(self.calculations["parameters"]) is not dict or any(type(x) is not list for x in (self.sheet["issues"], self.calculations["issues"], self.calculations["checks"])):
            _error("grading_lists_invalid")
        if type(self.sheet["artifact_occurrences"]) is not list:
            _error("sheet_occurrences_invalid")
        seen = set()
        for occurrence in self.sheet["artifact_occurrences"]:
            _fields(occurrence, _M1_FIELDS, "sheet_occurrence_fields_invalid")
            oid = occurrence["occurrence_id"]
            if oid in seen or oid not in self.occurrences or occurrence != {key: self.occurrences[oid][key] for key in _M1_FIELDS}:
                _error("sheet_occurrence_mismatch")
            seen.add(oid)
        if seen != set(grading["formats"]):
            _error("sheet_format_population_mismatch")
        for collection, kinds in self.definitions.items():
            source = self.calculations["rows"] if collection == "calculations" else self.sheet[collection]
            if type(source) is not list:
                _error("collection_list_required")
            keys = set()
            self.collections[collection] = []
            for row in source:
                key, kind = _key(row, self.family, collection), _kind(row, self.family, collection)
                if kind not in kinds:
                    _error("row_kind_not_in_operation_collection")
                if key in keys:
                    _error("record_key_ambiguous")
                keys.add(key)
                self.collections[collection].append((key, kind, row))
                if collection != "calculations":
                    self.add_record(key, row, self.row_occurrence(key, kind, row))
        self._embedded_records()
        self._validate_associations()
        for key, kind, row in self.collections["calculations"]:
            self.allowed(row, key, kind, "calculations")
        for check in self.calculations["checks"]:
            self.check_identity(check)

    def _context(self):
        abi = self.grading["native_abi"]
        fields = {"byte_order", "float_format", "bytes_per_float", "uint8_bytes", "uint16_bytes", "uint32_bytes", "uint64_bytes", "int32_bytes", "c_int_bytes", "c_long_bytes", "c_float_bytes"}
        if abi is not None:
            _fields(abi, fields, "native_abi_fields_invalid")
            if abi["byte_order"] not in {"little", "big"} or abi["float_format"] not in {"ieee754_binary64", "unsupported"} or abi["float_format"] == "ieee754_binary64" and abi["bytes_per_float"] != 8:
                _error("native_abi_invalid")
            for field in fields - {"byte_order", "float_format"}:
                _integer(abi[field], 1)
        metadata = self.grading["metadata"]
        parameters = {
            "artifact": {"probability_tolerance", "expected_revision"},
            "alignment_preparation": {"background", "probability_tolerance", "summary_rounding_tolerance"},
            "emission": {"consensus_thresholds", "probability_rounding_tolerance"},
            "simulation": {"fixed_lambda", "fit_tolerance", "solver_iteration_limit", "rounding_tolerance", "tail_masses", "filter_criterion"},
            "statistics": {"background", "length_probability", "probability_tolerance", "summary_rounding_tolerance"},
            "fm": {"alphabet_normalization", "coordinate_policy", "exhaustive_literal_check"},
        }
        if set(self.grading["requested_parameters"]) - parameters[self.family]:
            _error("requested_parameters_undeclared")
        allowed = {"artifact_bindings"} if self.family == "artifact" else {"producer_contract", "source_binding"} if self.family == "fm" else set()
        if set(metadata) - allowed:
            _error("metadata_unrelated")
        for binding in metadata.get("artifact_bindings", []):
            _fields(binding, {"artifact_occurrence_id", "source_occurrence_id", "source_sha256", "producer_attempt_id", "staged_source_stem", "actual_relative_path"}, "artifact_binding_fields_invalid")
            for value in binding.values():
                _text(value)
        producer = metadata.get("producer_contract")
        if producer is not None:
            _fields(producer, {"format", "engine_version", "byte_order", "uint8_bytes", "uint16_bytes", "uint32_bytes", "uint64_bytes", "int32_bytes"}, "producer_fields_invalid")
            for field in ("format", "engine_version", "byte_order"):
                _text(producer[field])
            for field in set(producer) - {"format", "engine_version", "byte_order"}:
                _integer(producer[field], 1)
        binding = metadata.get("source_binding")
        if binding is not None:
            _fields(binding, {"database_occurrence_id", "source_occurrence_ids", "source_sha256s", "producer_attempt_id"}, "source_binding_fields_invalid")
            for field in ("database_occurrence_id", "producer_attempt_id"):
                _text(binding[field])
            ids, hashes = binding["source_occurrence_ids"], binding["source_sha256s"]
            if type(ids) is not list or type(hashes) is not list or not ids or len(ids) != len(hashes):
                _error("source_binding_population_invalid")
            for oid, digest in zip(ids, hashes):
                _text(oid)
                if type(digest) is not str or re.fullmatch("[0-9a-fA-F]{64}", digest) is None:
                    _error("source_binding_digest_invalid")

    def add_record(self, key, row, oid, *, model=False):
        _text(key)
        if oid is not None and oid not in self.occurrences:
            _error("row_occurrence_unknown")
        if key in self.records and self.records[key] != row:
            # B1 output model references intentionally point to the full M1 row.
            old = self.records[key]
            if not (model and old.get("kind") == "model" and old.get("locator") == row.get("locator") and self.record_occurrences[key] == oid):
                _error("record_key_ambiguous")
        self.records[key], self.record_occurrences[key] = row, oid
        if model:
            self.models[key] = row

    def row_occurrence(self, key, kind, row):
        locator = row.get("locator")
        if locator is not None and type(locator) is not dict:
            _error("row_locator_invalid")
        oid = row.get("occurrence_id") or (locator or {}).get("occurrence_id")
        if oid is None and locator is not None:
            # Exact structural row-key grammar disambiguates same-byte roles.
            ordinal = locator.get("record_ordinal")
            candidates = []
            for candidate in self.occurrences:
                suffixes = ["#" + kind + "/" + str(ordinal)]
                if kind == "model_statistic":
                    suffixes = ["#summary/" + str(ordinal)]
                if key in {candidate + suffix for suffix in suffixes}:
                    candidates.append(candidate)
            if len(candidates) != 1:
                _error("row_occurrence_ambiguous")
            oid = candidates[0]
        if oid is not None:
            if oid not in self.occurrences:
                _error("row_occurrence_unknown")
            if locator and locator.get("occurrence_id", oid) != oid:
                _error("row_locator_occurrence_mismatch")
            ordinal = (locator or {}).get("record_ordinal")
            if self.family == "artifact" and kind in _A_NATIVE:
                suffix = "#artifact" if kind == "artifact_metadata" else "#line/" + str((locator or {}).get("line"))
            elif self.family == "alignment_preparation" and kind == "population":
                suffix = "#population/0"
            else:
                _integer(ordinal)
                saved_kind = "summary" if kind == "model_statistic" else "native" if self.family == "emission" and kind not in {"model", "fasta", "alignment", "alignment_row"} else kind
                suffix = "#" + saved_kind + "/" + str(ordinal)
            if key != oid + suffix:
                _error("row_occurrence_identity_mismatch")
            if locator is not None:
                if type(locator) is not dict:
                    _error("row_locator_invalid")
                if "artifact_ref" in locator and locator["artifact_ref"] != self.occurrences[oid]["artifact_ref"]:
                    _error("row_artifact_mismatch")
                if "byte_start" in locator or "byte_end" in locator:
                    start, end = locator.get("byte_start"), locator.get("byte_end")
                    _integer(start)
                    _integer(end)
                    if not start <= end <= self.occurrences[oid]["size_bytes"]:
                        _error("row_locator_bounds")
        elif not (self.family == "artifact" and kind == "requested_key" and row.get("request_source") == "single_key"
                  or self.family == "alignment_preparation" and kind == "requested_interval"):
            _error("row_occurrence_required")
        return oid

    def _embedded_records(self):
        extractions = self.sheet.get("model_extractions", [])
        if "model_extraction" in self.sheet and self.sheet["model_extraction"] is not None:
            extractions = [*extractions, self.sheet["model_extraction"]]
        for extraction in extractions:
            _fields(extraction, {"schema", "occurrence", "format", "records", "population", "issues"}, "model_extraction_fields_invalid")
            oid = extraction["occurrence"].get("occurrence_id")
            if extraction["schema"] != "hmmer_model_extraction_v1" or oid not in self.occurrences or extraction["occurrence"] != {key: self.occurrences[oid][key] for key in _M1_FIELDS} or extraction["format"] != self.occurrences[oid]["format"]:
                _error("model_extraction_occurrence_mismatch")
            if type(extraction["records"]) is not list:
                _error("model_records_invalid")
            for ordinal, row in enumerate(extraction["records"]):
                key = oid + "#model/" + str(ordinal)
                if row.get("record_key") != key or row.get("locator", {}).get("record_ordinal") != ordinal:
                    _error("model_record_identity_invalid")
                self.add_record(key, row, self.row_occurrence(key, "model", row), model=True)
        if self.family == "simulation":
            for key, kind, row in self.collections["input_records"]:
                self.models[key] = row
        if self.family == "alignment_preparation":
            for collection in ("input_records", "output_records"):
                for key, kind, row in self.collections[collection]:
                    if kind == "alignment":
                        for ordinal, member in enumerate(row.get("rows", [])):
                            if member.get("record_key") != key + "/sequence/" + str(ordinal):
                                _error("alignment_member_identity_invalid")
                            self.add_record(member["record_key"], member, self.record_occurrences[key])
        if self.family == "fm" and self.sheet["database"] is not None:
            database = self.sheet["database"]
            oid = database.get("occurrence", {}).get("occurrence_id")
            if database.get("schema") != "hmmer_fm_extraction_v1" or oid not in self.occurrences or database["occurrence"] != {key: self.occurrences[oid][key] for key in _M1_FIELDS}:
                _error("database_occurrence_mismatch")
            for collection, kind in (("segments", "segment"), ("ambiguity_ranges", "ambiguity"), ("blocks", "block")):
                if type(database.get(collection)) is not list:
                    _error("database_records_invalid")
                for ordinal, row in enumerate(database[collection]):
                    key = oid + "#" + kind + "/" + (str(row.get("block_ordinal")) + "/" + str(row.get("section")) if kind == "block" else str(ordinal))
                    if row.get("record_key") != key:
                        _error("database_record_identity_invalid")
                    self.add_record(key, row, oid)

    def _refs(self, keys):
        if type(keys) is not list or any(type(key) is not str or key not in self.records for key in keys):
            _error("saved_record_reference_invalid")
        return set(keys)

    def _validate_associations(self):
        associations = self.sheet["associations"]
        if self.family == "fm":
            _fields(associations, {"source_binding_state", "segments", "query_groups", "hit_targets"}, "fm_associations_invalid")
            for group in associations["query_groups"]:
                key = group.get("record_key")
                self._refs(group.get("query_record_keys"))
                self._refs(group.get("hit_record_keys"))
                oid = group.get("occurrence_id")
                if oid not in self.occurrences:
                    _error("query_group_occurrence_invalid")
                self.add_record(key, group, oid)
                for hit in group["hit_record_keys"]:
                    if self.records[hit].get("payload", {}).get("group_key") != key:
                        _error("query_group_hit_mismatch")
            for association in associations["segments"]:
                self._refs([association["segment_record_key"]])
                if association["source_record_key"] is not None:
                    self._refs([association["source_record_key"]])
                    if self.records[association["source_record_key"]].get("source_ordinal") != self.records[association["segment_record_key"]].get("target_id"):
                        _error("segment_source_relationship_invalid")
            for association in associations["hit_targets"]:
                self._refs([association["hit_record_key"]])
                hit = self.records[association["hit_record_key"]]
                for candidate in association["candidates"]:
                    self._refs(candidate["segment_record_keys"])
                    if candidate["source_record_key"] is not None:
                        self._refs([candidate["source_record_key"]])
                        if self.records[candidate["source_record_key"]].get("source_ordinal") != candidate["target_id"]:
                            _error("hit_source_relationship_invalid")
                    if any(self.records[key]["target_id"] != candidate["target_id"] or self.records[key]["name"] != hit["payload"]["target_name"] for key in candidate["segment_record_keys"]):
                        _error("hit_segment_relationship_invalid")
            return
        if type(associations) is not list:
            _error("associations_list_required")
        self.associations = associations
        input_keys = {key for key, _, _ in self.collections.get("input_records", [])}
        output_keys = {key for key, _, _ in self.collections.get("output_records", [])}
        for association in associations:
            if type(association) is not dict:
                _error("association_object_required")
            for name in ("source_record_keys", "selected_source_record_keys", "output_record_keys", "key_row_keys", "model_record_keys", "model_keys", "record_keys", "candidate_model_record_keys"):
                if name in association:
                    self._refs(association[name])
            for name in ("source_record_key", "output_record_key", "summary_record_key", "resaved_record_key", "model_record_key", "native_record_key", "key_row_key"):
                if association.get(name) is not None:
                    self._refs([association[name]])
            if self.family == "artifact":
                for field in ("source_record_keys", "selected_source_record_keys"):
                    if not set(association.get(field, [])) <= input_keys:
                        _error("association_source_direction_invalid")
                if not set(association.get("output_record_keys", [])) <= output_keys:
                    _error("association_output_direction_invalid")
                for key in association.get("key_row_keys", []) + ([association["key_row_key"]] if association.get("key_row_key") is not None else []):
                    if self.records[key].get("kind") != "requested_key":
                        _error("association_requested_key_kind_invalid")
            if self.family == "alignment_preparation":
                source = association.get("source_record_key")
                if source is not None and (source not in input_keys or self.records[source].get("kind") != "alignment"):
                    _error("alignment_source_relationship_invalid")
                for field in ("output_record_key", "resaved_record_key"):
                    key = association.get(field)
                    if key is not None and (key not in output_keys or self.records[key].get("kind") != "alignment"):
                        _error("alignment_output_relationship_invalid")
                model, summary = association.get("model_record_key"), association.get("summary_record_key")
                if model is not None and model not in self.models or summary is not None and self.records[summary].get("kind") != "build_summary":
                    _error("alignment_model_summary_relationship_invalid")
            if self.family in {"emission", "simulation"}:
                model_keys = association.get("model_keys", []) if self.family == "simulation" else association.get("candidate_model_record_keys", []) + ([association["model_record_key"]] if association.get("model_record_key") is not None else [])
                if any(key not in self.models for key in model_keys):
                    _error("association_model_kind_invalid")
            if self.family in {"simulation", "emission"} and association.get("kind") != "model_population":
                key = association.get("record_key")
                self._refs([key])
                row = self.records[key]
                names = ("model_keys",) if self.family == "simulation" else ("model_record_key", "sample_ordinal")
                if any(row.get(name) != association.get(name) for name in names):
                    _error("saved_model_association_mismatch")
            if self.family == "statistics" and association.get("state") == "validated":
                native = self.records[association["native_record_key"]]
                keys = association["model_record_keys"]
                if len(keys) != 1 or keys[0] not in self.models:
                    _error("summary_model_association_invalid")
                model = self.models[keys[0]]
                if native["values"]["M"] != model["length"] or native["values"]["name"] != self.model_identifier(model, "NAME") or native["values"]["accession"] != self.model_identifier(model, "ACC"):
                    _error("summary_model_association_mismatch")

    @staticmethod
    def model_identifier(model, tag):
        headers = model.get("headers")
        if type(headers) is not list:
            _error("model_headers_invalid")
        rows = [h for h in headers if type(h) is dict and h.get("tag") == tag]
        if len(rows) != 1 or type(rows[0].get("tokens")) is not list or len(rows[0]["tokens"]) != 1:
            return None
        value = rows[0]["tokens"][0]
        _text(value)
        return value

    def _occurrences_for(self, keys):
        return {self.record_occurrences[key] for key in keys if key in self.record_occurrences and self.record_occurrences[key] is not None}

    def _association_keys(self, association):
        keys = set()
        for field in ("record_key", "key_row_key", "source_record_key", "output_record_key", "model_record_key", "native_record_key", "summary_record_key", "resaved_record_key"):
            key = association.get(field)
            if key is not None and key in self.records:
                keys.add(key)
        for field in ("record_keys", "key_row_keys", "source_record_keys", "selected_source_record_keys", "output_record_keys", "model_record_keys", "model_keys", "candidate_model_record_keys"):
            keys.update(association.get(field, []))
        return keys

    def allowed(self, row, key, kind, collection):
        """Derive permitted operand joins from saved row/association contracts.

        Component input claims cannot enlarge their own permitted relationship.
        A known identifier in another row's population is insufficient.
        """
        keys, oids = ({key} if key in self.records else set()), set()
        if collection != "calculations":
            # Include exact related calculation scope when native checks use this
            # record key. This does not select the calculation or disclose it.
            linked = [(k, t, r) for k, t, r in self.collections.get("calculations", []) if k == key]
            for calc_key, calc_kind, calc_row in linked:
                a, b = self.allowed(calc_row, calc_key, calc_kind, "calculations")
                keys.update(a)
                oids.update(b)
            if key in self.models:
                keys.add(key)
            if self.family == "simulation":
                keys.update(row.get("model_keys", []))
            if self.family == "emission":
                for association in self.associations:
                    if association.get("record_key") == key:
                        keys.update(self._association_keys(association))
            if self.family == "statistics":
                for association in self.associations:
                    if association.get("native_record_key") == key:
                        keys.update(self._association_keys(association))
            return keys, oids | self._occurrences_for(keys)
        if self.family == "artifact":
            if kind == "population":
                direction = row.get("direction")
                expected = [r[0] for r in self.collections[direction + "_records"]] if direction in {"input", "output"} else None
                if expected is None or key != direction + "_population" or row.get("record_keys") != expected:
                    _error("population_row_relationship_invalid")
                keys.update(expected)
                oids.update(o["occurrence_id"] for o in self.sheet["artifact_occurrences"] if o["direction"] == direction and o["role"] in {"models", "converted_models", "fetched_models", "binary_models"})
            elif kind == "artifact":
                oid = row.get("occurrence_id")
                if oid not in self.occurrences or key != oid:
                    _error("artifact_row_relationship_invalid")
                oids.add(oid)
                for binding in self.sheet["artifact_bindings"]:
                    if binding.get("artifact_occurrence_id") == oid:
                        source = binding.get("source_occurrence_id")
                        if source not in self.occurrences or self.occurrences[source]["direction"] != "input" or self.occurrences[source]["role"] != "models" or binding.get("source_sha256") != self.occurrences[source]["sha256"]:
                            _error("artifact_binding_relationship_invalid")
                        oids.add(source)
            elif kind == "model_comparison":
                matches = [a for a in self.associations if a.get("association_id") == row.get("association_id") and a.get("kind") == "model_pair"]
                if len(matches) != 1 or key != matches[0]["association_id"]:
                    _error("model_pair_association_invalid")
                association = matches[0]
                for field, plural in (("source_record_key", "source_record_keys"), ("output_record_key", "output_record_keys")):
                    expected = association[plural]
                    if len(expected) > 1 or row.get(field) != (expected[0] if expected else None):
                        _error("model_pair_relationship_invalid")
                keys.update(self._association_keys(association))
            elif kind == "key_population":
                if key != "key_population":
                    _error("key_population_identity_invalid")
                for association in self.associations:
                    keys.update(self._association_keys(association))
                oids.update(o["occurrence_id"] for o in self.sheet["artifact_occurrences"] if o["role"] in {"models", "fetched_models", "keys"})
            elif kind == "index_summary":
                if key != "index_summary":
                    _error("index_summary_identity_invalid")
                native = row.get("native_row_key")
                if native is not None:
                    self._refs([native])
                    if self.records[native].get("kind") != "index_summary":
                        _error("index_summary_relationship_invalid")
                    keys.add(native)
                keys.update(r[0] for r in self.collections["input_records"])
                oids.update(o["occurrence_id"] for o in self.sheet["artifact_occurrences"] if o["direction"] == "input" and o["role"] == "models")
            elif kind == "bundle":
                expected = [o["occurrence_id"] for o in self.sheet["artifact_occurrences"] if o["direction"] == "output" and o["role"] in {"binary_models", "ssi_index", "msv_profiles", "remaining_profiles"}]
                if key != "pressed_bundle" or row.get("member_occurrence_ids") != expected:
                    _error("bundle_relationship_invalid")
                oids.update(expected)
                for binding in self.sheet["artifact_bindings"]:
                    if binding.get("artifact_occurrence_id") in expected:
                        oid = binding.get("source_occurrence_id")
                        if oid not in self.occurrences:
                            _error("bundle_source_occurrence_invalid")
                        oids.add(oid)
        elif self.family == "alignment_preparation":
            matches = [a for a in self.associations if a.get("record_key") == key and a.get("relation") == ("build" if kind == "build" else "mask")]
            if not matches and kind in {"mask", "mapping"} and key == "unavailable#alignment/0" and row.get("source_record_key") is None:
                association = None
            elif len(matches) != 1:
                _error("alignment_calculation_association_invalid")
            else:
                association = matches[0]
            if association:
                pairs = (("source_record_key", "source_record_key"), ("output_record_key", "resaved_record_key" if kind == "build" else "output_record_key"))
                if kind == "build":
                    pairs += (("model_record_key", "model_record_key"), ("summary_record_key", "summary_record_key"))
                if any(row.get(a) != association.get(b) for a, b in pairs):
                    _error("alignment_calculation_relationship_invalid")
                keys.update(self._association_keys(association))
            if kind != "build":
                keys.update(k for k, t, _ in self.collections["native_rows"] if t in {"requested_interval", "mapping", "population"})
                oids.update(o["occurrence_id"] for o in self.sheet["artifact_occurrences"] if o["direction"] == "output" and o["role"] == "stdout")
            for parent in list(keys):
                record = self.records.get(parent, {})
                if record.get("kind") == "alignment":
                    keys.update(member["record_key"] for member in record["rows"])
        elif self.family == "emission":
            model = row.get("model_record_key")
            if model is not None and model not in self.models:
                _error("emission_model_reference_invalid")
            if model is not None:
                keys.add(model)
            if kind in {"model", "consensus"}:
                if model not in self.models:
                    _error("emission_aggregate_model_required")
                expected = [r[0] for r in self.collections["output_records"] if r[1] != "alignment" and r[2].get("model_record_key") == model]
                field = "record_keys" if kind == "model" else "actual_record_keys"
                if row.get(field) != expected:
                    _error("emission_population_relationship_invalid")
                keys.update(expected)
            else:
                original = self.records.get(key)
                if original is None or original.get("model_record_key") != model:
                    _error("emission_record_relationship_invalid")
                keys.add(key)
                if kind == "alignment":
                    keys.update(original["native"]["row_record_keys"])
            for parent in list(keys):
                original = self.records.get(parent, {})
                if original.get("alignment_record_key") is not None:
                    self._refs([original["alignment_record_key"]])
                    keys.add(original["alignment_record_key"])
        elif self.family == "statistics":
            if key not in self.models:
                _error("statistic_model_reference_invalid")
            keys.add(key)
            expected = [a["native_record_key"] for a in self.associations if a.get("model_record_keys") == [key] and a.get("state") == "validated"]
            if row.get("native_record_keys") != expected:
                _error("statistic_native_relationship_invalid")
            keys.update(expected)
        elif self.family == "simulation":
            source_keys, model_keys = row.get("source_record_keys"), row.get("model_keys")
            keys.update(self._refs(source_keys))
            keys.update(self._refs(model_keys))
            if any(model not in self.models for model in model_keys):
                _error("simulation_model_reference_invalid")
            for source in source_keys:
                if self.records[source].get("model_keys") != model_keys:
                    _error("simulation_source_model_mismatch")
            if type(row.get("details")) is not dict:
                _error("simulation_details_invalid")
            fit_key = row["details"].get("fit_record_key")
            if fit_key is not None:
                matches = [r for k, t, r in self.collections["calculations"] if k == fit_key and t in {"fit", "alignment_statistics"}]
                if len(matches) != 1 or matches[0]["model_keys"] != model_keys:
                    _error("simulation_fit_reference_invalid")
                keys.update(matches[0]["source_record_keys"])
            # A fit variant can use the same model's recorded calibration summary
            # in individual cell operands even when it is not the primary row.
            keys.update(k for k, t, r in self.collections["native_rows"] if t == "summary" and model_keys and r["model_keys"] == model_keys)
        else:
            self._fm_allowed(row, key, kind, keys, oids)
        self._refs(list(keys))
        return keys, oids | self._occurrences_for(keys)

    def _fm_allowed(self, row, key, kind, keys, oids):
        database = self.sheet["database"]
        dbkey = database["occurrence"]["occurrence_id"] if database else None
        associations = self.sheet["associations"]
        if kind == "database_summary":
            if row.get("record_key") != dbkey:
                _error("database_summary_relationship_invalid")
            keys.update(k for k, t, _ in self.collections["input_records"] if t == "fasta")
            if database:
                oids.add(dbkey)
                keys.update(r["record_key"] for field in ("segments", "blocks", "ambiguity_ranges") for r in database[field])
        elif kind == "exactmatch_summary":
            if row.get("record_key") is not None:
                _error("exactmatch_summary_identity_invalid")
            keys.update(k for collection in ("input_records", "native_rows") for k, _, _ in self.collections[collection])
            keys.update(group["record_key"] for group in associations["query_groups"])
            if database:
                oids.add(dbkey)
        elif kind in {"block_validation", "segment_validation"}:
            if not database:
                _error("database_validation_without_database")
            field = "blocks" if kind == "block_validation" else "segments"
            if not any(r["record_key"] == key for r in database[field]):
                _error("database_validation_record_invalid")
            keys.add(key)
            oids.add(dbkey)
            if kind == "segment_validation":
                matches = [a for a in associations["segments"] if a["segment_record_key"] == key]
                source = row.get("details", {}).get("source_record_key")
                if len(matches) != 1 or source != matches[0]["source_record_key"]:
                    _error("segment_validation_source_mismatch")
                if source:
                    keys.add(source)
            # Internal database joins are tied to the same decoded database
            # occurrence; its source associations remain explicitly recorded.
            keys.update(r["record_key"] for field in ("blocks", "segments", "ambiguity_ranges") for r in database[field])
            keys.update(a["source_record_key"] for a in associations["segments"] if a["source_record_key"] is not None)
        elif kind == "query_validation":
            if key not in self.records or self.records[key].get("kind") != "query":
                _error("query_validation_record_invalid")
            keys.add(key)
        elif kind == "location_validation":
            original = self.records.get(key, {})
            if original.get("kind") != "exactmatch_hit":
                _error("location_validation_record_invalid")
            groupkey = original["payload"]["group_key"]
            group = self.records[groupkey]
            if row.get("details", {}).get("query_record_keys") != group["query_record_keys"]:
                _error("location_query_relationship_invalid")
            keys.update([key, groupkey, *group["query_record_keys"]])
            matches = [a for a in associations["hit_targets"] if a["hit_record_key"] == key]
            if len(matches) != 1:
                _error("location_target_association_invalid")
            actual = row["details"].get("candidates")
            expected = matches[0]["candidates"]
            if type(actual) is not list or len(actual) != len(expected) or any(
                    a.get("source_record_key") != b["source_record_key"] or a.get("segment_record_keys") != b["segment_record_keys"] for a, b in zip(actual, expected)):
                _error("location_target_relationship_invalid")
            for candidate in expected:
                keys.update(candidate["segment_record_keys"])
                if candidate["source_record_key"] is not None:
                    keys.add(candidate["source_record_key"])

    def check_identity(self, check):
        if type(check) is not dict:
            _error("check_object_required")
        name = check.get("code", check.get("name"))
        outcome = check.get("state")
        if name not in self.check_names or outcome not in _OUTCOMES:
            _error("check_name_or_outcome_invalid")
        if self.family == "simulation":
            expected = {"name", "source_record_keys", "state", "details"}
            self._refs(check.get("source_record_keys"))
            if type(check.get("details")) is not dict:
                _error("check_details_invalid")
            explicit = check["details"].get("calculation_record_key")
            if explicit is not None and not any(key == explicit for key, _, _ in self.collections["calculations"]):
                _error("check_calculation_reference_unknown")
        else:
            expected = ({"code", "state", "row_key", "field", "inputs"} if self.family == "artifact" else
                        {"code", "state", "record_key", "inputs", "details"} if self.family == "alignment_preparation" else
                        {"code", "state", "record_key", "inputs"} if self.family == "emission" else
                        {"name", "state", "record_key", "field", "inputs"} if self.family == "statistics" else
                        {"name", "record_key", "state", "scope", "inputs"})
        _fields(check, expected, "check_fields_invalid")
        if self.family == "fm" and check["record_key"] is None and check["scope"] not in _F_NULL_SCOPES.get(name, set()):
            _error("null_key_check_scope_undeclared")
        return name, outcome

    def matching_checks(self, row, key, kind, collection, requested):
        result = []
        for name in requested:
            matched = []
            for check in self.calculations["checks"]:
                check_name, outcome = self.check_identity(check)
                if name != check_name:
                    continue
                if self.family == "simulation":
                    explicit = check["details"].get("calculation_record_key")
                    applies = (explicit == key if explicit is not None else
                        set(check["source_record_keys"]) == set(row["source_record_keys"])) if collection == "calculations" else key in check["source_record_keys"]
                else:
                    saved_key = check.get("row_key") if self.family == "artifact" else check.get("record_key")
                    target = row.get("model_record_key") if self.family == "emission" and collection == "calculations" and kind in {"model", "consensus"} else key
                    applies = saved_key is not None and saved_key == target
                    if self.family == "fm" and saved_key is None and collection == "calculations":
                        if kind == "exactmatch_summary":
                            applies = name in _F_EXACT_CHECKS
                        elif kind == "database_summary" and row["record_key"] is None:
                            applies = name in _F_DATABASE_CHECKS
                        elif name not in _F_EXACT_CHECKS | _F_DATABASE_CHECKS:
                            _error("null_key_check_scope_undeclared")
                    # E1 model population and consensus share a model operand,
                    # but their checks have separate declared row meanings.
                    if self.family == "emission" and collection == "calculations" and kind in {"model", "consensus"}:
                        applies &= name in ({"sample_population_count"} if kind == "model" else {"consensus_agreement", "consensus_length"})
                if applies:
                    allowed_keys, allowed_oids = self.allowed(row, key, kind, collection)
                    allowed_keys.add(key)  # The check can cite its own saved calculation row.
                    if self.family == "fm" and name == "source_coverage" and collection == "input_records" and kind == "fasta":
                        database = self.sheet["database"]
                        if database is not None:
                            allowed_oids.add(database["occurrence"]["occurrence_id"])
                    if self.family == "simulation":
                        check_keys = self._refs(check["source_record_keys"])
                        # An explicit comparison can involve a paired score and
                        # alignment population from the same recorded model.
                        models = row.get("model_keys", [])
                        for source in check_keys:
                            source_models = self.records[source].get("model_keys", [])
                            if collection == "calculations" and source_models != models:
                                _error("check_source_model_mismatch")
                        allowed_keys.update(check_keys)
                        allowed_oids.update(self._occurrences_for(check_keys))
                        oids = self._occurrences_for(check_keys)
                    else:
                        oids = self.input_occurrences(check["inputs"], allowed_keys, allowed_oids)
                    matched.append({"name": name, "outcome": outcome, "occurrences": [self.compact_occurrence(oid) for oid in self.occurrences if oid in oids]})
            result.extend(matched or [{"name": name, "outcome": "unknown", "occurrences": []}])
        return result

    def input_occurrences(self, inputs, allowed_keys, allowed_oids):
        found = set()
        if type(inputs) not in (list, dict):
            _error("component_inputs_invalid")
        def reference(key, *, occurrence=False):
            if key is None:
                return
            _text(key)
            if occurrence:
                if key not in self.occurrences or key not in allowed_oids:
                    _error("input_occurrence_relationship_invalid")
                found.add(key)
            elif key in self.records:
                if key not in allowed_keys:
                    _error("input_record_relationship_invalid")
                oid = self.record_occurrences[key]
                if oid is not None:
                    found.add(oid)
            elif key in self.occurrences:
                reference(key, occurrence=True)
            else:
                # A1 cell denominator points to the current comparison row.
                if key not in allowed_keys:
                    _error("input_record_reference_unknown")
        def walk(value, field=None):
            if type(value) is list:
                for child in value:
                    walk(child, field)
            elif type(value) is dict:
                for name, child in value.items():
                    if name in {"occurrence_id", "source_occurrence_id", "artifact_occurrence_id"}:
                        reference(child, occurrence=True)
                    elif name in {"record_key", "row_key", "source_record_key", "model_record_key"}:
                        reference(child)
                    elif name in {"record_keys", "source_record_keys", "model_keys"}:
                        if type(child) is not list:
                            _error("input_record_references_invalid")
                        for item in child:
                            reference(item)
                    elif name == "association_id":
                        matches = [a for a in self.associations if a.get("association_id") == child]
                        if len(matches) != 1:
                            _error("input_association_reference_unknown")
                        for item in self._association_keys(matches[0]):
                            reference(item)
                    elif name == "artifact_ref":
                        candidates = [oid for oid in allowed_oids if self.occurrences[oid]["artifact_ref"] == child]
                        if len(candidates) != 1:
                            _error("input_artifact_reference_ambiguous")
                        found.add(candidates[0])
                    elif name in {"inputs", "locator"}:
                        walk(child, name)
            elif type(value) is str and self.family == "fm":
                if value in self.records or value in self.occurrences:
                    reference(value)
                elif value not in _FM_INPUT_FIELDS:
                    _error("fm_input_field_undeclared")
        walk(inputs)
        return found

    def compact_occurrence(self, oid):
        return {name: self.occurrences[oid][name] for name in ("direction", "role", "ordinal", "artifact_ref")}

    def identity(self, row, key, kind, collection):
        original = self.records.get(key)
        model = self.models.get(key)
        if self.family == "emission" and collection == "calculations" and kind in {"model", "consensus"}:
            model = self.models[row["model_record_key"]]
        if self.family == "simulation" and row.get("model_keys") and len(row["model_keys"]) == 1:
            model = self.models.get(row["model_keys"][0])
        name = accession = None
        if model is not None:
            name, accession = (self.model_identifier(model, tag) for tag in ("NAME", "ACC"))
        elif original is not None:
            if self.family == "statistics":
                name, accession = original["values"]["name"], original["values"]["accession"]
            elif original.get("kind") == "alignment" and self.family == "alignment_preparation":
                for tag, field in (("ID", "name"), ("AC", "accession")):
                    matches = [event.get("value") for event in original.get("original_events", []) if event.get("kind") == "GF" and event.get("tag") == tag]
                    if len(matches) == 1:
                        if field == "name": name = matches[0]
                        else: accession = matches[0]
            elif self.family == "fm" and original.get("kind") == "fasta":
                name = original["payload"]["name"] or None
            else:
                name, accession = original.get("name"), original.get("accession")
        _text(name, nullable=True)
        _text(accession, nullable=True)
        aggregate = collection == "calculations" and (
            self.family == "artifact" and kind in {"population", "key_population", "bundle", "index_summary", "model_comparison"}
            or self.family == "emission" and kind in {"model", "consensus"}
            or self.family == "fm" and kind in {"database_summary", "exactmatch_summary"}
            or self.family == "simulation")
        oid = None if aggregate else self.record_occurrences.get(key)
        if self.family == "artifact" and collection == "calculations" and kind == "artifact":
            oid = row["occurrence_id"]
        return name, accession, oid


_FM_INPUT_FIELDS = set("arrays decoded BWT T SA counters_b counters_sb term_loc total_char_count alph_type source_binding sequences source_sequences queries hits alphabet_normalization source_symbol_total indexed_unique_symbols native_Q native_H native_R query_occurrence_count emitted_location_count query_groups expected_tuples native_locations exhaustive_literal_check".split())


def _quantity(saved, row, key, kind, collection, path):
    spec = saved.definitions[collection][kind].get(path)
    if spec is None:
        return {"path": path, "value": None, "state": "missing", "unit": None}, set()
    units = spec["unit"] if type(spec["unit"]) is list else [spec["unit"]]
    unit = units[0] if len(units) == 1 else None
    if saved.family == "fm" and collection == "native_rows" and kind == "index_parameters":
        parameter = row.get("payload", {}).get("parameter")
        if parameter not in {"bin_length", "suffix array sample rate"}:
            return {"path": path, "value": None, "state": "missing", "unit": None}, set()
        unit = "index_symbol_count" if parameter == "bin_length" else "suffix_array_sampling_interval"
    value = _read(row, path)
    oids = set()
    if spec["cell"] and value is not None:
        _fields(value, {"value", "state", "unit", "inputs"}, "component_cell_fields_invalid")
        if value["state"] not in _COMPONENT_STATES or value["unit"] not in units:
            _error("component_state_or_unit_invalid")
        allowed_keys, allowed_oids = saved.allowed(row, key, kind, collection)
        allowed_keys.add(key)  # Saved within-row denominators, never another row.
        oids = saved.input_occurrences(value["inputs"], allowed_keys, allowed_oids)
        quantity = {"path": path, **{name: value[name] for name in ("value", "state", "unit")}}
    else:
        state = _read(row, spec["state"]) if spec["state"] else None
        if state is not None and state not in _STATES:
            _error("native_scalar_state_invalid")
        quantity = {"path": path, "value": value, "state": state if state is not None else "missing" if value is None else "present", "unit": unit}
        if not spec["cell"]:
            oid = saved.record_occurrences.get(key)
            if oid is not None:
                oids.add(oid)
    _number(quantity["value"])
    return quantity, oids


@_contract_errors("saved_structure_invalid")
def project_preparation_result(grading, *, selector, source_ref, occurrences):
    """Project only requested saved scalar facts and required artifact references."""
    _text(source_ref)
    saved = _Saved(grading, occurrences)
    selector = validate_preparation_result_selector(selector, program=saved.program, mode=saved.mode)
    projection = selector["projection"]
    rows, artifacts, selected_oids = [], [], []
    population = {"source_ref": source_ref, "collection": None, "total_records": 0, "returned_records": 0,
        "omitted_records": 0, "missing_record_keys": [], "requested_artifact_count": len(selector["artifacts"]),
        "returned_artifact_count": 0, "missing_artifacts": []}
    for selected in selector["artifacts"]:
        occurrence = saved.slots.get(tuple(selected[name] for name in ("direction", "role", "ordinal")))
        if occurrence is None:
            population["missing_artifacts"].append(deepcopy(selected))
        else:
            selected_oids.append(occurrence["occurrence_id"])
    if projection is not None:
        if saved.sheet is None:
            _error("saved_numerical_grading_unavailable")
        collection = projection["collection"]
        source = saved.collections[collection]
        window = projection["rows"]
        if "record_keys" in window:
            by_key = {key: (key, kind, row) for key, kind, row in source}
            selected = [by_key[key] for key in window["record_keys"] if key in by_key]
            population["missing_record_keys"] = [key for key in window["record_keys"] if key not in by_key]
        else:
            selected = source[window["offset"]:window["offset"] + window["limit"]]
        for key, kind, row in selected:
            name, accession, own_oid = saved.identity(row, key, kind, collection)
            quantities, needed = [], {own_oid} if own_oid is not None else set()
            for path in projection["quantities"]:
                quantity, oids = _quantity(saved, row, key, kind, collection, path)
                quantities.append(quantity)
                needed.update(oids)
            checks = saved.matching_checks(row, key, kind, collection, projection["checks"])
            for check in checks:
                for occurrence in check["occurrences"]:
                    needed.add(saved.slots[tuple(occurrence[k] for k in ("direction", "role", "ordinal"))]["occurrence_id"])
            selected_oids.extend(oid for oid in saved.occurrences if oid in needed and oid not in selected_oids)
            rows.append({"record_key": key, "kind": kind, "name": name, "accession": accession, "source_ref": source_ref,
                "artifact_ref": saved.occurrences[own_oid]["artifact_ref"] if own_oid is not None else None,
                "quantities": quantities, "checks": checks})
        population.update(collection=collection, total_records=len(source), returned_records=len(rows), omitted_records=len(source) - len(rows))
    for oid in selected_oids:
        occurrence = saved.occurrences[oid]
        artifacts.append({"source_ref": source_ref, **{name: occurrence[name] for name in ARTIFACT_SCHEMA["properties"] if name != "source_ref"}})
    population["returned_artifact_count"] = len(artifacts)
    return {"rows": rows, "artifacts": artifacts, "population": population}


__all__ = ["preparation_projection_catalog", "validate_preparation_result_selector", "project_preparation_result", "preparation_fact_sources",
    "NATIVE_HMMER_PREPARATION_RESULT_SELECTOR_SCHEMA", "ROW_SCHEMA", "ARTIFACT_SCHEMA", "POPULATION_SCHEMA", "FAILURE_SCHEMA", "FAILURE_STAGES", "IDENTIFIER_NAMESPACES", "FACT_SOURCES"]
