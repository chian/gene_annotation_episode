"""Closed retained-input RNA comparison contracts; no scientific execution.

The schemas describe stored values, not a formula language. Input relationships
are checked against supplied records. Component validation checks representation
and relationships only; publication separately checks deterministic arithmetic.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re

from jsonschema import Draft202012Validator, validators

from .rna_structure_contracts import (
    COORDINATE_SYSTEM, RNA_SYMBOLS, OPERATIONS, RNA_ISSUE_CODES,
    _same, validate_rna_sheet,
)

SELECTOR_VERSION = "native_rna_structure_comparison_selector_v1"
SHEET_VERSION = "rna_structure_comparison_sheet_v1"
COMPONENTS_VERSION = "rna_structure_comparison_components_v1"
CALCULATOR_VERSION = "rna_comparison_calculators_v1"
COLUMN_COORDINATE_SYSTEM = "zero_based_declared_alignment_columns"
PROFILE = "vienna_2_7_retained_linear_model_v1"
UNCERTAINTY_REASON = "selected_inputs_do_not_produce_comparison_uncertainty"
COMPARISON_REASONS = frozenset("""
not_requested not_supplied not_tested received_failure zero_denominator
invalid_selection duplicate_operand_requires_alias
duplicate_sequence_variant_requires_representative invalid_alias
saved_operand_not_received original_receipt_mismatch retained_sheet_missing
retained_sheet_digest_mismatch original_structure_unavailable original_topology_invalid
original_sequence_unavailable sequence_identity_unverified unsupported_index_map
correspondence_not_supplied invalid_correspondence substitution_manifest_mismatch
partial_correspondence unmapped_selected_site unresolved_partner unresolved_pair_endpoints
supplied_alignment_gap selected_site_absent invalid_site_selection
requested_energy_unavailable energy_kind_mismatch energy_structure_mismatch
native_model_missing model_setting_missing model_setting_different
parameter_identity_missing parameter_identity_different unsupported_model_profile
software_generation_unverified equal_array_generation_rule_used different_sequence_lengths
baseline_unavailable baseline_comparability_unknown selected_population_only
duplicate_alias_excluded comparison_uncertainty_not_produced nonfinite_derived_value
selected_window_omits_members unknown_source_origin projection_not_requested
projection_mismatch selected_inputs_do_not_produce_comparison_uncertainty
""".split())
CELL_STATES = frozenset(("present", "not_requested", "not_produced", "missing_input",
    "invalid_input", "incompatible", "failed", "truncated", "unknown"))
CELL_ORIGINS = frozenset(("retained_native_prediction", "retained_native_evaluation",
    "derived_correspondence", "derived_topology_comparison", "derived_energy_difference",
    "derived_scan_count", "derived_scan_rank"))
SITE_TRANSITIONS = ("unchanged_unpaired", "unchanged_partner", "lost_pairing",
    "gained_pairing", "reassigned_partner", "deleted_site", "inserted_site",
    "unmapped_site", "unresolved_partner", "unavailable_topology")
PAIR_RELATIONS = ("preserved", "lost", "gained", "unresolved_baseline", "unresolved_variant")
PAIRING_STATES = ("changed", "unchanged_in_complete_correspondence", "unresolved", "not_requested")
ENERGY_STATES = ("not_requested", "comparable", "native_energy_unavailable", "model_incompatible",
    "model_unknown", "not_supplied", "not_tested", "received_failure")
RANK_CLASSES = ("unique_lowest", "tied_lowest", "not_lowest", "unavailable", "not_requested")
PREDICATES = ("lower_than_baseline", "equal_to_baseline", "higher_than_baseline",
    "within_baseline_tolerance", "model_incompatible", "model_unknown",
    "energy_unavailable", "received_failure", "not_supplied", "not_tested")
PAIR_METRICS = tuple("""baseline_pair_count variant_pair_count baseline_mapped_pair_count
variant_mapped_pair_count baseline_unresolved_pair_count variant_unresolved_pair_count
preserved_pair_count lost_pair_count gained_pair_count known_pair_change_count
pair_symmetric_difference_count preserved_baseline_pair_fraction mapped_baseline_pair_fraction
mapped_variant_pair_fraction alignment_inserted_nt alignment_deleted_nt""".split())
SITE_METRICS = tuple("""requested_site_count shared_site_count decidable_site_count
changed_site_count unchanged_site_count lost_pairing_site_count gained_pairing_site_count
reassigned_partner_site_count deleted_site_count inserted_site_count unmapped_site_count
unavailable_topology_site_count unresolved_partner_site_count decidable_site_fraction
changed_site_fraction unchanged_site_fraction""".split())
ENERGY_METRICS = ("baseline_native_energy", "variant_native_energy", "baseline_selected_energy",
    "variant_selected_energy", "energy_delta", "energy_absolute_delta", "baseline_tolerance")
SCAN_ENERGY_METRICS = tuple("""declared_entry_count canonical_member_count alias_entry_count
declared_variant_count native_energy_available_variant_count received_failure_variant_count
not_supplied_variant_count not_tested_variant_count sheet_energy_unavailable_variant_count
model_incompatible_variant_count model_unknown_variant_count comparable_variant_count
rank_population_count lower_variant_count equal_variant_count higher_variant_count
baseline_rank_start baseline_rank_end baseline_tie_count
comparable_variant_fraction within_tolerance_variant_count baseline_selected_energy
minimum_selected_energy baseline_energy_above_minimum lowest_energy_tie_count""".split())
SCAN_MEMBER_RANK_METRICS = ("member_rank_start", "member_rank_end")
SCAN_SITE_METRICS = tuple("""decidable_variant_count changed_variant_count unchanged_variant_count
lost_pairing_variant_count gained_pairing_variant_count reassigned_partner_variant_count
deleted_variant_count unmapped_variant_count unavailable_topology_variant_count
unresolved_partner_variant_count changed_variant_fraction unchanged_variant_fraction""".split())
COMPARISON_METRICS = frozenset((*PAIR_METRICS, *SITE_METRICS, *ENERGY_METRICS,
    *SCAN_ENERGY_METRICS, *SCAN_MEMBER_RANK_METRICS, *SCAN_SITE_METRICS, "change_indicator"))
COMPARISON_UNITS = frozenset(("nt", "sites", "pairs", "fraction", "indicator", "kcal/mol",
    "kcal/mol/nt", "entries", "candidates", "aliases", "variants", "rank"))
MODEL_SETTING_NAMES = ("temperature_c", "dangles", "noLP", "noGU", "noGUclosure",
    "special_hp", "logML", "min_loop_size", "max_bp_span", "circ", "gquad")
OTHER_SCALAR_SETTING_NAMES = tuple("""backbone_length backtrack backtrack_type betaScale circ_alpha0
circ_penalty compute_bpp cv_fact energy_set helical_rise nc_fact nonstandards oldAliEn
pf_smooth ribo salt saltDPXInit saltDPXInitFact saltMLLower saltMLUpper sfact uniq_ML window_size""".split())
ARRAY_SETTING_NAMES = ("alias", "pair", "rtype")
COMPATIBILITY_FIELDS = (
    "energy_kind", "unit", "baseline.structure_association", "variant.structure_association",
    "model.engine", "model.engine_version", "hard_constraints", "soft_constraints",
    "parameter_artifact.sha256", "parameter_artifact.size_bytes", "parameter_load_return",
    "parameter_save_return", "other_observed_settings.name_set",
    *("effective_settings." + name for name in MODEL_SETTING_NAMES),
    *("other_observed_settings." + name for name in (*OTHER_SCALAR_SETTING_NAMES, *ARRAY_SETTING_NAMES)),
    *("software." + name for name in ("worker_source_sha256", "rna_module_sha256",
        "rna_extension_sha256", "viennarna_distribution_version")),
)


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
        "additionalProperties": False}


def nullable(schema):
    return {"anyOf": [deepcopy(schema), {"type": "null"}]}


def array(schema, *, minimum=0, unique=False):
    return {"type": "array", "items": schema, "minItems": minimum,
        **({"uniqueItems": True} if unique else {})}


def enum(values):
    return {"enum": list(values)}


ID = {"type": "string", "minLength": 1, "pattern": r"^[^\u0000\r\n]+$"}
COUNT = {"type": "integer", "minimum": 0}
NUMBER = {"type": "number"}
SHA256 = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
BOOLEAN = {"type": "boolean"}
NULL = {"type": "null"}
TEXT = {"type": "string"}
RNA_CHAR = {"type": "string", "pattern": "^[" + RNA_SYMBOLS + RNA_SYMBOLS.lower() + "]$"}
PATH = {"type": "string", "pattern": r"^/(?:[^~\u0000\r\n]|~[01])*$"}
PAIR = {"type": "array", "minItems": 2, "maxItems": 2, "items": COUNT}


def _reference(namespace):
    return {**ID, "format": "reference", "x-reference-namespace": namespace}


def _identifier(namespace):
    return {**ID, "format": "identifier", "x-reference-namespace": namespace}


RNA_COMPARISON_PARAMETERS_SCHEMA = obj({
    "schema": {"const": "rna_comparison_parameters_v1"},
    "arithmetic": {"const": "retained_binary64_values_v1"},
    "tie_rule": {"const": "exact_selected_numeric_value"},
    "site_denominator": {"const": "decidable_selected_shared_sites"},
    "pair_difference": {"const": "alignment_column_pair_sets"},
    "native_uncertainty_policy": {"const": "retain_no_fabricated_transfer"},
})
COMPARISON_ISSUE_SCHEMA = obj({
    "stage": enum(("selection", "authority", "input", "correspondence", "compatibility", "calculate", "projection")),
    "code": enum(sorted(COMPARISON_REASONS)), "member_id": nullable(ID),
    "comparison_id": nullable(ID), "selection_id": nullable(ID), "field": nullable(PATH),
    "index": nullable(COUNT),
})
ENERGY_REQUEST_SCHEMA = obj({"quantity": enum(("native_mfe", "native_evaluation")),
    "normalization": enum(("none", "per_nt")), "compatibility_profile": {"const": PROFILE},
    "baseline_absolute_tolerance": nullable({"type": "number", "minimum": 0})})
SITE_SELECTION_SCHEMA = obj({"selection_id": ID, "coordinate_member_id": ID,
    "positions": array(COUNT), "intervals": array(PAIR), "unpaired_region_keys": array(ID),
    "combine": {"const": "set_union"}})
ALIGNMENT_COLUMN_SCHEMA = obj({"column": COUNT, "baseline_index": nullable(COUNT),
    "variant_index": nullable(COUNT)})
PARTIAL_MATCH_SCHEMA = obj({"baseline_index": COUNT, "variant_index": COUNT})
_AUTHORITY = obj({"kind": {"const": "parent_assignment"}, "source_ref": nullable(_reference("source"))})
CORRESPONDENCE_REQUEST_SCHEMA = {"oneOf": [
    obj({"kind": {"const": "identical_sequence"}}),
    obj({"kind": {"const": "substitution_only"}, "substitutions": array(obj({
        "index": COUNT, "baseline_symbol": RNA_CHAR, "variant_symbol": RNA_CHAR}))}),
    obj({"kind": {"const": "supplied_complete_alignment"}, "authority": _AUTHORITY,
        "columns": array(ALIGNMENT_COLUMN_SCHEMA)}),
    obj({"kind": {"const": "supplied_partial_correspondence"}, "authority": _AUTHORITY,
        "matches": array(PARTIAL_MATCH_SCHEMA)}),
]}
COMPARISON_REQUEST_SCHEMA = obj({"comparison_id": ID, "variant_member_id": ID,
    "correspondence": nullable(CORRESPONDENCE_REQUEST_SCHEMA),
    "site_selections": array(SITE_SELECTION_SCHEMA), "calculate_pair_changes": BOOLEAN,
    "energy": nullable(ENERGY_REQUEST_SCHEMA)})

# Exact existing source records are retained. Their scientific relationships are
# delegated to the original pure validator, never reinterpreted here.
_OLD_ID = {"type": "string", "minLength": 1, "pattern": r"^[^\u0000]+$"}


def _old_reference(namespace):
    return {**_OLD_ID, "format": "reference", "x-reference-namespace": namespace}


def _old_identifier(namespace):
    return {**_OLD_ID, "format": "identifier", "x-reference-namespace": namespace}


_OLD_ISSUE = obj({"stage": enum(("input", "native", "capture", "parse", "calculate", "binding", "selection")),
    "code": enum(sorted(RNA_ISSUE_CODES)), "record_key": nullable(_OLD_ID), "field": nullable(_OLD_ID),
    "index": nullable(COUNT), "artifact_role": nullable(enum(("input", "model_parameter_input",
        "native_result", "model", "effective_parameters", "stdout", "stderr")))})
SAVED_INPUT_SCHEMA = obj({"schema": {"const": "rna_structure_saved_sheet_input_v1"},
    "result_receipt_key": _old_identifier("native_rna_structure_result_receipt"),
    "handoff_ref": _old_reference("execution_handoff"), "source_ref": _old_reference("execution_result"),
    "bundle_artifact_ref": _old_reference("artifact"), "sheet_artifact_ref": _old_reference("artifact"),
    "sheet_sha256": SHA256, "record_key": _OLD_ID,
    "operation": enum(OPERATIONS.values()), "mode": enum(OPERATIONS)})
RNA_FAILURE_ROW_SCHEMA = obj({"family": {"const": "failure"}, "record_key": _OLD_ID,
    "row_key": _old_identifier("native_rna_structure_row"), "source_ref": nullable(_old_reference("execution_result")),
    "operation": enum(OPERATIONS.values()), "mode": enum(OPERATIONS),
    "result_receipt_key": _old_identifier("native_rna_structure_result_receipt"),
    "issue_ordinal": COUNT, "issue": _OLD_ISSUE})
SOFTWARE_SCHEMA = obj({"python_executable": _OLD_ID, "python_sha256": SHA256,
    "python_version": nullable(_OLD_ID), "worker_module": {"const": "gene_annotation_episode.native_rna_structure_worker"},
    "worker_source_sha256": SHA256, "viennarna_distribution_version": nullable(_OLD_ID),
    "rna_module_sha256": nullable(SHA256), "rna_extension_sha256": nullable(SHA256)})
MEMBER_SCHEMA = {"oneOf": [
    obj({"member_id": ID, "kind": {"const": "saved_sheet"}, "saved_input": SAVED_INPUT_SCHEMA}),
    obj({"member_id": ID, "kind": {"const": "received_failure"}, "failure": RNA_FAILURE_ROW_SCHEMA}),
    obj({"member_id": ID, "kind": {"const": "declared_absent"}, "state": enum(("not_supplied", "not_tested"))}),
    obj({"member_id": ID, "kind": {"const": "alias"}, "canonical_member_id": ID}),
]}
SCAN_REQUEST_SCHEMA = obj({"scan_id": ID, "population_unit": {"const": "unique_analyzed_sequence_variant"},
    "baseline_in_rank": {"const": True}, "member_order": {"const": "as_declared"},
    "energy": nullable(ENERGY_REQUEST_SCHEMA), "topology_selection_ids": array(ID, unique=True)})
QUESTION_SCHEMA = obj({"kind": enum(("pairwise", "scan")), "baseline_member_id": ID,
    "membership": array(MEMBER_SCHEMA, minimum=1), "comparisons": array(COMPARISON_REQUEST_SCHEMA),
    "scan": nullable(SCAN_REQUEST_SCHEMA)})
MEMBER_SELECTION_SCHEMA = {"oneOf": [obj({"kind": {"const": "explicit"},
    "member_ids": array(ID, unique=True)}), obj({"kind": {"const": "exceptions"},
    "predicates": array(enum(PREDICATES), minimum=1, unique=True)})]}


def _projection(family, **fields):
    return obj({"projection_id": ID, "family": {"const": family}, **fields})


RNA_COMPARISON_PROJECTION_REQUEST_SCHEMA = {"oneOf": [
    _projection("energy_comparison", comparison_ids=array(ID, unique=True),
        metrics=array(enum(ENERGY_METRICS), unique=True), include_order=BOOLEAN, include_tolerance_band=BOOLEAN),
    _projection("structures", member_ids=array(ID, unique=True),
        fields=array(enum(("original_sequence", "analysis_sequence", "dot_bracket", "pairs")), minimum=1, unique=True)),
    _projection("position_changes", comparison_id=ID, selection_id=ID,
        transitions=array(enum(SITE_TRANSITIONS), minimum=1, unique=True)),
    _projection("pair_changes", comparison_ids=array(ID, unique=True),
        relations=array(enum(PAIR_RELATIONS), minimum=1, unique=True)),
    _projection("comparison_counts", comparison_ids=array(ID, unique=True), selection_ids=array(ID, unique=True),
        metrics=array(enum((*PAIR_METRICS, *SITE_METRICS)), unique=True), include_pairing_change_state=BOOLEAN),
    _projection("scan_energy", scan_id=ID, metrics=array(enum(SCAN_ENERGY_METRICS), unique=True), include_rank_class=BOOLEAN),
    _projection("scan_sites", scan_id=ID, selection_ids=array(ID, unique=True),
        metrics=array(enum(SCAN_SITE_METRICS), unique=True)),
    _projection("scan_members", scan_id=ID, members=MEMBER_SELECTION_SCHEMA,
        fields=array(enum(("energy", "delta", "rank_start", "rank_end", "eligibility")), minimum=1, unique=True),
        order={"const": "declared"}, limit=nullable(COUNT)),
]}
RNA_COMPARISON_SELECTOR_SCHEMA = obj({"version": {"const": SELECTOR_VERSION},
    "acquisition": {"const": "retained_inputs_only"}, "question": QUESTION_SCHEMA,
    "parameters": RNA_COMPARISON_PARAMETERS_SCHEMA,
    "projections": array(RNA_COMPARISON_PROJECTION_REQUEST_SCHEMA, minimum=1)})

# Fixed metric metadata validates the representation; it contains no executable
# formulas or expression strings beyond the accepted formula identifiers.
METRIC_SPECS = {}
for _metric in PAIR_METRICS:
    _unit = "fraction" if _metric.endswith("fraction") else "nt" if _metric.startswith("alignment_") else "pairs"
    METRIC_SPECS["rna_pair_compare_v1." + _metric] = {
        "metric": _metric, "units": (_unit,),
        "origins": ("derived_correspondence",) if _metric.startswith("alignment_") else ("derived_topology_comparison",)}
for _metric in (*SITE_METRICS, "change_indicator"):
    METRIC_SPECS["rna_site_compare_v1." + _metric] = {"metric": _metric,
        "units": ("indicator" if _metric == "change_indicator" else "fraction" if _metric.endswith("fraction") else "sites",),
        "origins": ("derived_topology_comparison",)}
for _metric in ENERGY_METRICS:
    METRIC_SPECS["rna_energy_compare_v1." + _metric] = {"metric": _metric,
        "units": ("kcal/mol",) if "native_energy" in _metric else ("kcal/mol", "kcal/mol/nt"),
        "origins": ("derived_energy_difference",) if _metric in ("energy_delta", "energy_absolute_delta", "baseline_tolerance")
            else ("retained_native_prediction", "retained_native_evaluation")}
for _metric in (*SCAN_ENERGY_METRICS, *SCAN_MEMBER_RANK_METRICS):
    _energy_metric = _metric in ("baseline_selected_energy", "minimum_selected_energy", "baseline_energy_above_minimum")
    _unit = ("entries" if _metric == "declared_entry_count" else "aliases" if _metric == "alias_entry_count"
        else "rank" if "rank_start" in _metric or "rank_end" in _metric else "fraction" if _metric.endswith("fraction")
        else "candidates" if _metric in ("canonical_member_count", "rank_population_count", "baseline_tie_count", "lowest_energy_tie_count")
        else "variants")
    _origins = (("derived_energy_difference",) if _metric == "baseline_energy_above_minimum" else
        ("retained_native_prediction", "retained_native_evaluation") if _energy_metric else
        ("derived_scan_rank",) if _unit == "rank" else ("derived_scan_count",))
    METRIC_SPECS["rna_scan_energy_v1." + _metric] = {"metric": _metric,
        "units": ("kcal/mol", "kcal/mol/nt") if _energy_metric else (_unit,), "origins": _origins}
for _metric in SCAN_SITE_METRICS:
    METRIC_SPECS["rna_scan_site_v1." + _metric] = {"metric": _metric,
        "units": ("fraction" if _metric.endswith("fraction") else "variants",), "origins": ("derived_scan_count",)}
COMPARISON_FORMULAS = frozenset(METRIC_SPECS)
NUMERIC_CELL_SCHEMA = obj({"metric": enum(sorted(COMPARISON_METRICS)), "value": nullable(NUMBER),
    "unit": enum(sorted(COMPARISON_UNITS)), "state": enum(sorted(CELL_STATES)),
    "reason": nullable(enum(sorted(COMPARISON_REASONS))), "numerator": nullable(NUMBER),
    "denominator": nullable(NUMBER), "origin": enum(sorted(CELL_ORIGINS)),
    "formula_id": enum(sorted(COMPARISON_FORMULAS)), "input_paths": array(PATH, unique=True),
    "population_id": nullable(ID), "selection_id": nullable(ID),
    "uncertainty": obj({"state": {"const": "not_produced"}, "value": NULL,
        "reason": {"const": UNCERTAINTY_REASON}})})
MAP_ENTRY_SCHEMA = obj({"index": COUNT, "state": enum(("matched", "gap", "unknown")),
    "counterpart_index": nullable(COUNT), "column": nullable(COUNT)})
POPULATED_CORRESPONDENCE_SCHEMA = obj({"request": CORRESPONDENCE_REQUEST_SCHEMA,
    "state": enum(("valid", "invalid", "missing_input")), "columns": array(ALIGNMENT_COLUMN_SCHEMA),
    "matches": array(PARTIAL_MATCH_SCHEMA), "baseline_to_variant": array(MAP_ENTRY_SCHEMA),
    "variant_to_baseline": array(MAP_ENTRY_SCHEMA), "baseline_length_nt": nullable(COUNT),
    "variant_length_nt": nullable(COUNT), "issues": array(COMPARISON_ISSUE_SCHEMA)})
RESOLVED_SELECTION_SCHEMA = obj({"selection": SITE_SELECTION_SCHEMA, "indices": array(COUNT, unique=True)})
PARTNER_SCHEMA = obj({"state": enum(("unpaired", "mapped", "gap", "unmapped", "unavailable")),
    "local_index": nullable(COUNT), "column": nullable(COUNT), "counterpart_index": nullable(COUNT)})
SITE_CHANGE_SCHEMA = obj({"column": nullable(COUNT), "baseline_index": nullable(COUNT),
    "variant_index": nullable(COUNT), "baseline_symbol": nullable(RNA_CHAR), "variant_symbol": nullable(RNA_CHAR),
    "baseline_partner": PARTNER_SCHEMA, "variant_partner": PARTNER_SCHEMA,
    "transition": enum(SITE_TRANSITIONS), "change_indicator": NUMERIC_CELL_SCHEMA,
    "issues": array(COMPARISON_ISSUE_SCHEMA)})
PAIR_CHANGE_SCHEMA = obj({"relation": enum(PAIR_RELATIONS), "columns": nullable(PAIR),
    "baseline_pair": nullable(PAIR), "variant_pair": nullable(PAIR), "baseline_pair_key": nullable(ID),
    "variant_pair_key": nullable(ID), "gap_endpoint": BOOLEAN, "issues": array(COMPARISON_ISSUE_SCHEMA)})
NATIVE_ENERGY_SCHEMA = obj({"value": nullable(NUMBER), "numeric_text": nullable(TEXT),
    "unit": {"const": "kcal/mol"}, "state": enum(sorted(CELL_STATES - {"unknown"})),
    "reason": nullable(enum(sorted(RNA_ISSUE_CODES))), "structure_key": nullable(_OLD_ID),
    "engine": enum((None, "ViennaRNA")), "engine_version": nullable(_OLD_ID), "model_key": nullable(_OLD_ID)})
COMPATIBILITY_SCHEMA = obj({"profile": {"const": PROFILE}, "state": enum(("compatible", "incompatible", "unknown")),
    "checks": array(obj({"field": enum(COMPATIBILITY_FIELDS),
        "outcome": enum(("equal", "different", "missing", "unsupported", "equal_by_versioned_generation_rule"))})),
    "issues": array(COMPARISON_ISSUE_SCHEMA)})
ENERGY_COMPARISON_SCHEMA = obj({"request": ENERGY_REQUEST_SCHEMA,
    "baseline_native": nullable(NATIVE_ENERGY_SCHEMA), "variant_native": nullable(NATIVE_ENERGY_SCHEMA),
    "compatibility": COMPATIBILITY_SCHEMA, "components": array(NUMERIC_CELL_SCHEMA),
    "order": enum(("variant_lower", "equal", "variant_higher", "unavailable")),
    "baseline_tolerance_band": enum(("below", "within", "above", "not_requested", "unavailable"))})
POPULATED_COMPARISON_SCHEMA = obj({"comparison_id": ID, "baseline_member_id": ID, "variant_member_id": ID,
    "correspondence": nullable(POPULATED_CORRESPONDENCE_SCHEMA),
    "resolved_selections": array(RESOLVED_SELECTION_SCHEMA), "all_site_rows": array(SITE_CHANGE_SCHEMA),
    "all_pair_rows": array(PAIR_CHANGE_SCHEMA), "components": array(NUMERIC_CELL_SCHEMA),
    "pairing_change_state": enum(PAIRING_STATES), "energy": nullable(ENERGY_COMPARISON_SCHEMA),
    "issues": array(COMPARISON_ISSUE_SCHEMA)})
SCAN_MEMBER_SCHEMA = obj({"member_id": ID, "canonical_member_id": ID,
    "membership_state": enum(("canonical", "alias")), "energy_state": enum(ENERGY_STATES),
    "comparison_id": nullable(ID), "energy": nullable(NUMERIC_CELL_SCHEMA), "delta": nullable(NUMERIC_CELL_SCHEMA),
    "exact_rank_start": nullable(NUMERIC_CELL_SCHEMA), "exact_rank_end": nullable(NUMERIC_CELL_SCHEMA),
    "issues": array(COMPARISON_ISSUE_SCHEMA)})
POPULATED_SCAN_SCHEMA = obj({"request": SCAN_REQUEST_SCHEMA, "baseline_member_id": ID,
    "members": array(SCAN_MEMBER_SCHEMA), "energy_components": array(NUMERIC_CELL_SCHEMA),
    "site_components": array(obj({"selection_id": ID, "baseline_index": COUNT,
        "components": array(NUMERIC_CELL_SCHEMA)})), "baseline_rank_class": enum(RANK_CLASSES),
    "issues": array(COMPARISON_ISSUE_SCHEMA)})


def _original_sheet_schema():
    """Closed JSON shape of existing 354 records; original validator owns meaning."""
    binding = obj({"subject_ref": _OLD_ID, "sequence_artifact_ref": _OLD_ID,
        "start": COUNT, "end": COUNT, "strand": enum(("+", "-"))})
    base = {"record_key": _OLD_ID, "sequence_id": nullable(_OLD_ID), "normalization": enum(("exact", "uppercase_ascii")),
        "subject_binding": nullable(binding)}
    original = {"oneOf": [obj({**base, "schema": {"const": "rna_prediction_input_v1"}, "sequence": TEXT}),
        obj({**base, "schema": {"const": "rna_feature_input_v1"}, "sequence": nullable(TEXT),
            "structure_id": nullable(_OLD_ID), "dot_bracket": TEXT,
            "structure_origin": enum(("supplied_unknown", "supplied_prediction", "supplied_observation")),
            "structure_source_ref": nullable(_OLD_ID), "energy_mode": enum(("none", "viennarna_evaluate"))})]}
    analysis = obj({"original_sequence": TEXT, "analysis_sequence": TEXT,
        "case_operation": enum(("exact", "uppercase_ascii")), "original_to_analysis_indices": array(COUNT),
        "length_nt": COUNT, "alphabet": enum(("ACGU", "RNA_IUPAC")),
        "symbol_counts": obj({s: COUNT for s in RNA_SYMBOLS}), "ambiguous_indices": array(COUNT)})
    structure = obj({"structure_key": _OLD_ID, "structure_id": nullable(_OLD_ID), "dot_bracket": TEXT,
        "origin": enum(("native_prediction", "supplied_unknown", "supplied_prediction", "supplied_observation")),
        "source_ref": nullable(_OLD_ID), "energy_dot_bracket": nullable(TEXT),
        "energy_conversion": nullable(obj({"kind": enum(("identity", "bracket_alphabet_to_parentheses")), "index_map": array(COUNT)}))})
    pair = obj({"pair_key": _OLD_ID, "i": COUNT, "j": COUNT, "opening_token": TEXT, "closing_token": TEXT,
        "parent_pair_key": nullable(_OLD_ID), "stem_key": _OLD_ID, "child_pair_keys": array(_OLD_ID)})
    stem = obj({"stem_key": _OLD_ID, "pair_keys": array(_OLD_ID), "outer_pair": PAIR, "inner_pair": PAIR})
    region = obj({"region_key": _OLD_ID, "kind": enum(("hairpin", "bulge", "internal", "multibranch", "exterior")),
        "closing_pair_key": nullable(_OLD_ID), "immediate_branch_pair_keys": array(_OLD_ID),
        "unpaired_intervals": array(PAIR), "unpaired_indices": array(COUNT),
        "five_prime_unpaired_indices": nullable(array(COUNT)), "three_prime_unpaired_indices": nullable(array(COUNT))})
    position = obj({"index": COUNT, "input_index": COUNT, "bracket": TEXT, "partner_index": nullable(COUNT),
        "pair_key": nullable(_OLD_ID), "stem_key": nullable(_OLD_ID), "unpaired_region_key": nullable(_OLD_ID)})
    topology = obj({"schema": {"const": "rna_topology_v1"}, "coordinate_system": {"const": COORDINATE_SYSTEM},
        "dot_bracket": TEXT, "length_nt": COUNT, "status": enum(("valid", "invalid", "unsupported")),
        "positions": nullable(array(position)), "pairs": nullable(array(pair)), "stems": nullable(array(stem)),
        "regions": nullable(array(region)), "issues": array(_OLD_ISSUE)})
    settings = {"temperature_c": NUMBER, "dangles": COUNT, "min_loop_size": COUNT,
        "max_bp_span": {"type": "integer"}, **{name: BOOLEAN for name in
            ("noLP", "noGU", "noGUclosure", "special_hp", "logML", "circ", "gquad")}}
    selected = obj({"schema": {"const": "vienna_rna_model_spec_v1"}, **settings,
        "hard_constraints": NULL, "soft_constraints": NULL,
        "parameters": obj({"kind": enum(("turner2004", "supplied_parameter_file")), "operand_role": nullable(_OLD_ID)})})
    model = obj({"schema": {"const": "vienna_rna_effective_model_v1"}, "model_key": _OLD_ID,
        "selected": selected, "engine": {"const": "ViennaRNA"}, "engine_version": _OLD_ID,
        "effective_settings": obj(settings), "other_observed_settings": array(obj({"name": _OLD_ID,
            "value": {"anyOf": [NUMBER, BOOLEAN, TEXT, NULL]}, "state": enum(("observed", "unavailable"))})),
        "parameter_artifact": obj({"relative_path": _OLD_ID, "sha256": SHA256, "size_bytes": COUNT}),
        "parameter_load_return": {"type": "integer"}, "parameter_save_return": {"type": "integer"}})
    uncertainty = obj({"state": {"const": "not_produced"}, "value": NULL,
        "reason": {"const": "selected_algorithm_does_not_produce_uncertainty"}})
    return obj({"schema": enum(("rna_mfe_prediction_sheet_v1", "rna_supplied_structure_feature_sheet_v1")),
        "operation": enum(OPERATIONS.values()), "mode": enum(OPERATIONS), "record_key": _OLD_ID,
        "original_input": nullable(original), "coordinate_system": {"const": COORDINATE_SYSTEM},
        "analysis_sequence": nullable(analysis), "structure": nullable(structure), "topology": nullable(topology),
        "sequence_pairs": nullable(array(obj({"pair_key": _OLD_ID, "symbol_i": nullable(TEXT),
            "symbol_j": nullable(TEXT), "ordered_pair": nullable(TEXT), "unambiguous": nullable(BOOLEAN)}))),
        "native_mfe": NATIVE_ENERGY_SCHEMA, "native_evaluation": NATIVE_ENERGY_SCHEMA,
        "native_uncertainty": obj({name: uncertainty for name in ("pair_probabilities", "ensemble_free_energy_kcal_mol",
            "mfe_frequency", "ensemble_diversity", "energy_standard_error", "energy_interval")}),
        "model": nullable(model), "subject_binding": nullable(binding), "status": enum(("complete", "partial", "invalid")),
        "issues": array(_OLD_ISSUE), "native_input": nullable(obj({"format": enum(("rna_native_record_json_v1", "biomni_rna_structure_text_v0")),
            "sha256": SHA256, "byte_count": COUNT})), "legacy_quantities": NULL})


ORIGINAL_SHEET_SCHEMA = _original_sheet_schema()
RETAINED_OPERAND_SCHEMA = obj({"member_id": ID,
    "state": enum(("saved_sheet", "received_failure", "not_supplied", "not_tested", "alias")),
    "canonical_member_id": ID, "saved_input": nullable(SAVED_INPUT_SCHEMA),
    "original_sheet": nullable(ORIGINAL_SHEET_SCHEMA), "original_bundle_software": nullable(SOFTWARE_SCHEMA),
    "received_failure": nullable(RNA_FAILURE_ROW_SCHEMA),
    "variant_identity": enum(("verified_analyzed_sequence", "unverified", "not_applicable")),
    "issues": array(COMPARISON_ISSUE_SCHEMA)})
COMPARISON_INPUTS_SCHEMA = obj({"comparison_id": ID, "baseline_member_id": ID, "variant_member_id": ID,
    "correspondence": nullable(POPULATED_CORRESPONDENCE_SCHEMA),
    "resolved_selections": array(RESOLVED_SELECTION_SCHEMA), "calculate_pair_changes": BOOLEAN,
    "energy_request": nullable(ENERGY_REQUEST_SCHEMA), "issues": array(COMPARISON_ISSUE_SCHEMA)})
RNA_COMPARISON_SHEET_SCHEMA = obj({"schema": {"const": SHEET_VERSION},
    "coordinate_system": {"const": COORDINATE_SYSTEM}, "column_coordinate_system": {"const": COLUMN_COORDINATE_SYSTEM},
    "selected_question": QUESTION_SCHEMA, "parameters": RNA_COMPARISON_PARAMETERS_SCHEMA,
    "operands": array(RETAINED_OPERAND_SCHEMA), "comparisons": array(COMPARISON_INPUTS_SCHEMA),
    "scan_request": nullable(SCAN_REQUEST_SCHEMA), "issues": array(COMPARISON_ISSUE_SCHEMA)})
RNA_COMPARISON_COMPONENTS_SCHEMA = obj({"schema": {"const": COMPONENTS_VERSION},
    "calculator_version": {"const": CALCULATOR_VERSION}, "input_sheet_sha256": SHA256,
    "parameters": RNA_COMPARISON_PARAMETERS_SCHEMA, "comparisons": array(POPULATED_COMPARISON_SCHEMA),
    "scan": nullable(POPULATED_SCAN_SCHEMA), "used_input_paths": array(PATH, unique=True),
    "unused_input_paths": array(PATH, unique=True), "issues": array(COMPARISON_ISSUE_SCHEMA)})


_STRICT_VALIDATOR = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda checker, value: type(value) is int)
        .redefine("number", lambda checker, value: type(value) in (int, float) and
            (type(value) is int or math.isfinite(value))))


def _require(condition, code="invalid_selection"):
    if not condition:
        raise ValueError(code)


def _json_values(value):
    if type(value) is dict:
        _require(all(type(k) is str for k in value))
        for child in value.values():
            _json_values(child)
    elif type(value) is list:
        for child in value:
            _json_values(child)
    else:
        _require(value is None or type(value) in (str, bool, int) or
            type(value) is float and math.isfinite(value))


def checked(value, schema, code="invalid_selection"):
    try:
        _json_values(value)
        _require(_STRICT_VALIDATOR(schema).is_valid(value), code)
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError(code) from error
    return deepcopy(value)


def canonical(value):
    _json_values(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def comparison_digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def parse_rna_comparison_json(raw: bytes | str):
    """Strict supplied-byte JSON decoding; duplicate keys have no last-wins path."""
    _require(type(raw) in (bytes, str))
    def pairs(rows):
        result = {}
        for key, value in rows:
            _require(key not in result)
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError("invalid_selection")
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
        _json_values(value)
    except (UnicodeDecodeError, TypeError, ValueError) as error:
        raise ValueError("invalid_selection") from error
    return value


def validate_rna_comparison_parameters(value: dict) -> dict:
    return checked(value, RNA_COMPARISON_PARAMETERS_SCHEMA)


def validate_rna_comparison_projection_request(value: dict) -> dict:
    return checked(value, RNA_COMPARISON_PROJECTION_REQUEST_SCHEMA)


def _unique(rows, key, code="invalid_selection"):
    values = [row[key] for row in rows]
    _require(len(set(values)) == len(values), code)


def _validate_question(question):
    question = checked(question, QUESTION_SCHEMA)
    members = question["membership"]
    _unique(members, "member_id")
    by_id = {m["member_id"]: m for m in members}
    baseline = question["baseline_member_id"]
    _require(baseline in by_id and by_id[baseline]["kind"] != "alias")
    descriptors = []
    for member in members:
        kind = member["kind"]
        if kind == "alias":
            target = by_id.get(member["canonical_member_id"])
            _require(target is not None and target["kind"] != "alias", "invalid_alias")
        elif kind in ("saved_sheet", "received_failure"):
            data = member["saved_input" if kind == "saved_sheet" else "failure"]
            _require(data["operation"] == OPERATIONS[data["mode"]])
            _require(re.fullmatch(r"rna_result_receipt:[0-9a-f]{64}", data["result_receipt_key"]) is not None)
            if kind == "saved_sheet":
                _require(data not in descriptors, "duplicate_operand_requires_alias")
                descriptors.append(data)
            else:
                from .rna_structure_contracts import validate_rna_issue
                validate_rna_issue(data["issue"])
                _require(data["row_key"] == data["record_key"] + ":failure:" + str(data["issue_ordinal"]))
    comparisons = question["comparisons"]
    _unique(comparisons, "comparison_id")
    _unique(comparisons, "variant_member_id")
    canonical_variants = [m["member_id"] for m in members if m["kind"] != "alias" and m["member_id"] != baseline]
    _require(set(c["variant_member_id"] for c in comparisons) == set(canonical_variants))
    if question["kind"] == "pairwise":
        _require(len(canonical_variants) == 1 and len(comparisons) == 1 and question["scan"] is None)
    else:
        _require(question["scan"] is not None)
    for comparison in comparisons:
        _unique(comparison["site_selections"], "selection_id")
        for selection in comparison["site_selections"]:
            _require(selection["coordinate_member_id"] in (baseline, comparison["variant_member_id"]))
    scan = question["scan"]
    if scan is not None:
        reused = {}
        for comparison in comparisons:
            _require(_same(comparison["energy"], scan["energy"]))
            selections = {s["selection_id"]: s for s in comparison["site_selections"]}
            for key in scan["topology_selection_ids"]:
                _require(key in selections and selections[key]["coordinate_member_id"] == baseline)
                _require(key not in reused or _same(selections[key], reused[key]))
                reused[key] = selections[key]
        _require(bool(comparisons) or not scan["topology_selection_ids"])
    return question


def _validate_projection_relationships(projection, question):
    comparisons = {c["comparison_id"]: c for c in question["comparisons"]}
    members = {m["member_id"] for m in question["membership"]}
    family = projection["family"]
    selected = projection.get("comparison_ids", [])
    _require(all(key in comparisons for key in selected))
    if family == "structures":
        _require(set(projection["member_ids"]) <= members)
    elif family == "energy_comparison":
        _require(all(comparisons[key]["energy"] is not None for key in selected))
    elif family == "position_changes":
        comparison = comparisons.get(projection["comparison_id"])
        _require(comparison is not None and projection["selection_id"] in
            {s["selection_id"] for s in comparison["site_selections"]})
    elif family in ("pair_changes", "comparison_counts"):
        pairs_needed = family == "pair_changes" or bool(set(projection["metrics"]) & set(PAIR_METRICS)) or projection["include_pairing_change_state"]
        if pairs_needed:
            _require(all(comparisons[key]["calculate_pair_changes"] for key in selected))
        if family == "comparison_counts":
            if set(projection["metrics"]) & set(SITE_METRICS):
                _require(bool(projection["selection_ids"]))
            for key in selected:
                _require(set(projection["selection_ids"]) <= {s["selection_id"] for s in comparisons[key]["site_selections"]})
    else:
        scan = question["scan"]
        _require(scan is not None and projection["scan_id"] == scan["scan_id"])
        if family == "scan_energy" or family == "scan_members" and projection["fields"] != ["eligibility"]:
            _require(scan["energy"] is not None)
        if family == "scan_sites":
            _require(set(projection["selection_ids"]) <= set(scan["topology_selection_ids"]))
        if family == "scan_members" and projection["members"]["kind"] == "explicit":
            _require(set(projection["members"]["member_ids"]) <= members)


def validate_rna_comparison_selector(value: dict) -> dict:
    value = checked(value, RNA_COMPARISON_SELECTOR_SCHEMA)
    _validate_question(value["question"])
    _unique(value["projections"], "projection_id")
    for projection in value["projections"]:
        _validate_projection_relationships(projection, value["question"])
    return value


def resolve_comparison_input_path(sheet, pointer):
    """Resolve an actual RFC 6901 path; never traverse an absent/null field."""
    checked(pointer, PATH)
    current = sheet
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if type(current) is dict:
            _require(token in current)
            current = current[token]
        elif type(current) is list:
            _require(re.fullmatch(r"0|[1-9][0-9]*", token) is not None)
            index = int(token)
            _require(index < len(current))
            current = current[index]
        else:
            raise ValueError("invalid_selection")
    return current


def validate_rna_comparison_issue(value: dict, *, sheet: dict | None = None) -> dict:
    value = checked(value, COMPARISON_ISSUE_SCHEMA)
    if sheet is not None:
        members = {m["member_id"] for m in sheet["selected_question"]["membership"]}
        comparisons = {c["comparison_id"]: c for c in sheet["selected_question"]["comparisons"]}
        _require(value["member_id"] is None or value["member_id"] in members)
        _require(value["comparison_id"] is None or value["comparison_id"] in comparisons)
        if value["selection_id"] is not None:
            _require(value["comparison_id"] is not None and value["selection_id"] in
                {s["selection_id"] for s in comparisons[value["comparison_id"]]["site_selections"]})
        if value["field"] is not None:
            resolve_comparison_input_path(sheet, value["field"])
    return value


def comparison_issue(code, *, stage, member_id=None, comparison_id=None,
        selection_id=None, field=None, index=None):
    return validate_rna_comparison_issue({"stage": stage, "code": code, "member_id": member_id,
        "comparison_id": comparison_id, "selection_id": selection_id, "field": field, "index": index})


def validate_rna_comparison_sheet(value: dict) -> dict:
    value = checked(value, RNA_COMPARISON_SHEET_SCHEMA)
    _validate_question(value["selected_question"])
    # Reconstruct only input representation, never pairing changes/deltas/ranks.
    from .rna_structure_comparison_inputs import _populate
    operands = {r["member_id"]: {k: deepcopy(r[k]) for k in
        ("original_sheet", "original_bundle_software", "received_failure")}
        for r in value["operands"] if r["state"] != "alias"}
    expected = _populate(value["selected_question"], value["parameters"], operands)
    _require(_same(value, expected), "invalid_selection")
    return value


def validate_rna_comparison_components(value: dict, *, sheet: dict) -> dict:
    """Validate stored shape and declared relationships, without importing B."""
    sheet = validate_rna_comparison_sheet(sheet)
    value = checked(value, RNA_COMPARISON_COMPONENTS_SCHEMA)
    _require(value["input_sheet_sha256"] == comparison_digest(sheet))
    _require(_same(value["parameters"], sheet["parameters"]))
    _validate_component_relationships(value, sheet)
    return value


def _validate_component_relationships(value, sheet):
    _validate_components(value, sheet)


def _walk_issues(value, sheet):
    if type(value) is dict:
        if set(value) == set(COMPARISON_ISSUE_SCHEMA["properties"]):
            validate_rna_comparison_issue(value, sheet=sheet)
        else:
            for child in value.values():
                _walk_issues(child, sheet)
    elif type(value) is list:
        for child in value:
            _walk_issues(child, sheet)


def _cell_relationship(cell, sheet, *, prefix=None, selection_id=None):
    spec = METRIC_SPECS[cell["formula_id"]]
    _require(cell["metric"] == spec["metric"] and cell["unit"] in spec["units"] and cell["origin"] in spec["origins"])
    if prefix is not None:
        _require(cell["formula_id"].startswith(prefix + "."))
    _require(cell["selection_id"] == selection_id)
    for pointer in cell["input_paths"]:
        resolve_comparison_input_path(sheet, pointer)
    present = cell["state"] == "present"
    _require((cell["value"] is not None and cell["reason"] is None) if present else
        (cell["value"] is None and cell["reason"] is not None))
    if cell["unit"] in ("nt", "sites", "pairs", "entries", "candidates", "aliases", "variants", "rank"):
        if present:
            _require(type(cell["value"]) is int and cell["value"] >= (1 if cell["unit"] == "rank" else 0))
            _require(cell["numerator"] == cell["value"] and type(cell["numerator"]) is int)
        _require(cell["denominator"] is None)
    elif cell["unit"] == "fraction":
        for name in ("numerator", "denominator"):
            _require(cell[name] is None or type(cell[name]) is int and cell[name] >= 0)
        if present:
            _require(cell["numerator"] is not None and cell["denominator"] is not None and
                cell["denominator"] > 0 and 0 <= cell["value"] <= 1 and cell["numerator"] <= cell["denominator"])
        if cell["denominator"] == 0:
            _require(not present)
    elif cell["unit"] == "indicator":
        if present:
            _require(type(cell["value"]) is int and cell["value"] in (0, 1))
        _require(cell["denominator"] is None)
    elif cell["unit"] == "kcal/mol":
        _require(cell["denominator"] is None)
    elif cell["unit"] == "kcal/mol/nt":
        if cell["metric"] in ("baseline_selected_energy", "variant_selected_energy", "minimum_selected_energy") and present:
            _require(type(cell["denominator"]) is int and cell["denominator"] > 0 and cell["numerator"] is not None)
        elif cell["metric"] not in ("baseline_selected_energy", "variant_selected_energy", "minimum_selected_energy"):
            _require(cell["denominator"] is None)
    if cell["metric"] in ("baseline_tolerance", "energy_absolute_delta", "baseline_energy_above_minimum") and present:
        _require(cell["value"] >= 0)


def _cells(rows, sheet, *, prefix, selection_id=None, expected=None):
    _unique(rows, "metric")
    if expected is not None:
        _require(set(c["metric"] for c in rows) == set(expected))
    for cell in rows:
        _cell_relationship(cell, sheet, prefix=prefix, selection_id=selection_id)
    return {c["metric"]: c for c in rows}


def _native_pair(sheet, indices, key):
    if indices is None:
        _require(key is None)
        return
    _require(sheet is not None and sheet["topology"] is not None and sheet["topology"]["status"] == "valid")
    pairs = {p["pair_key"]: [p["i"], p["j"]] for p in sheet["topology"]["pairs"]}
    _require(key in pairs and indices == pairs[key] and indices[0] < indices[1])


def _site_coordinates(inputs, baseline, variant):
    from .rna_structure_comparison_inputs import _length
    correspondence = inputs["correspondence"]
    a_length, b_length = _length(baseline), _length(variant)
    if correspondence is not None and correspondence["state"] == "valid":
        if correspondence["request"]["kind"] == "supplied_partial_correspondence":
            rows = [(i, m["baseline_index"], m["variant_index"]) for i, m in enumerate(correspondence["matches"])]
            rows += [(None, m["index"], None) for m in correspondence["baseline_to_variant"] if m["state"] == "unknown"]
            rows += [(None, None, m["index"]) for m in correspondence["variant_to_baseline"] if m["state"] == "unknown"]
            return rows
        return [(r["column"], r["baseline_index"], r["variant_index"]) for r in correspondence["columns"]]
    return [(None, i, None) for i in range(a_length or 0)] + [(None, None, i) for i in range(b_length or 0)]


def _partner_relationship(partner, index, original, mapping):
    if index is None or original is None or original["topology"] is None or original["topology"]["status"] != "valid":
        _require(partner == {"state": "unavailable", "local_index": None, "column": None, "counterpart_index": None})
        return
    topology = original["topology"]
    _require(index < topology["length_nt"])
    local = topology["positions"][index]["partner_index"]
    if local is None:
        _require(partner == {"state": "unpaired", "local_index": None, "column": None, "counterpart_index": None})
        return
    _require(partner["local_index"] == local)
    entry = None if mapping is None else mapping[local]
    expected = {"state": "unmapped", "local_index": local, "column": None, "counterpart_index": None}
    if entry is not None and entry["state"] != "unknown":
        expected.update(state="mapped" if entry["state"] == "matched" else "gap",
            column=entry["column"], counterpart_index=entry["counterpart_index"])
    _require(partner == expected)


def _validate_site_rows(rows, inputs, baseline, variant, sheet):
    expected = _site_coordinates(inputs, baseline, variant)
    actual = [(r["column"], r["baseline_index"], r["variant_index"]) for r in rows]
    _require(actual == expected)
    correspondence = inputs["correspondence"]
    valid_map = correspondence is not None and correspondence["state"] == "valid"
    for row in rows:
        for side, original, map_field in (("baseline", baseline, "baseline_to_variant"),
                ("variant", variant, "variant_to_baseline")):
            index = row[side + "_index"]
            analysis = None if original is None else original["analysis_sequence"]
            symbol = None if analysis is None or index is None or index >= analysis["length_nt"] else analysis["analysis_sequence"][index]
            _require(row[side + "_symbol"] == symbol)
            mapping = correspondence[map_field] if valid_map else None
            _partner_relationship(row[side + "_partner"], index, original, mapping)
        indicator = row["change_indicator"]
        _cell_relationship(indicator, sheet, prefix="rna_site_compare_v1")
        _require(indicator["metric"] == "change_indicator")
        if row["transition"] in SITE_TRANSITIONS[:5]:
            _require(indicator["state"] == "present" and indicator["value"] == int(row["transition"] in SITE_TRANSITIONS[2:5]))
            _require(row["baseline_index"] is not None and row["variant_index"] is not None)
        else:
            _require(indicator["state"] != "present")


def _validate_pair_rows(rows, inputs, baseline, variant):
    seen = set()
    correspondence = inputs["correspondence"]
    valid_map = correspondence is not None and correspondence["state"] == "valid"
    covered = {"baseline_pair_key": [], "variant_pair_key": []}
    for row in rows:
        identity = (row["relation"], row["baseline_pair_key"], row["variant_pair_key"])
        _require(identity not in seen)
        seen.add(identity)
        _native_pair(baseline, row["baseline_pair"], row["baseline_pair_key"])
        _native_pair(variant, row["variant_pair"], row["variant_pair_key"])
        for key in covered:
            if row[key] is not None:
                covered[key].append(row[key])
        relation = row["relation"]
        _require((row["baseline_pair"] is not None) == (relation in ("preserved", "lost", "unresolved_baseline")))
        _require((row["variant_pair"] is not None) == (relation in ("preserved", "gained", "unresolved_variant")))
        if relation.startswith("unresolved"):
            _require(row["columns"] is None and not row["gap_endpoint"])
        else:
            _require(valid_map and row["columns"] is not None and row["columns"][0] < row["columns"][1])
        gap = False
        for pair_field, mapping_field in (("baseline_pair", "baseline_to_variant"), ("variant_pair", "variant_to_baseline")):
            pair = row[pair_field]
            if pair is None or not valid_map:
                continue
            mapped = [correspondence[mapping_field][i] for i in pair]
            columns = [m["column"] for m in mapped]
            if row["columns"] is not None:
                _require(columns == row["columns"])
            else:
                _require(None in columns)
            gap = gap or any(m["state"] == "gap" for m in mapped)
        if not relation.startswith("unresolved"):
            _require(row["gap_endpoint"] == gap)
    if valid_map and all(original is not None and original["topology"] is not None and
            original["topology"]["status"] == "valid" for original in (baseline, variant)):
        for key, original in (("baseline_pair_key", baseline), ("variant_pair_key", variant)):
            expected = {pair["pair_key"] for pair in original["topology"]["pairs"]}
            _require(len(covered[key]) == len(set(covered[key])) and set(covered[key]) == expected)


def _energy_relationship(value, inputs, baseline, variant, sheet):
    request = inputs["energy_request"]
    if request is None:
        _require(value is None)
        return
    _require(value is not None and _same(value["request"], request))
    quantity = request["quantity"]
    for side, original in (("baseline", baseline), ("variant", variant)):
        _require(_same(value[side + "_native"], None if original is None else original[quantity]))
    compatibility = value["compatibility"]
    _unique(compatibility["checks"], "field")
    for check in compatibility["checks"]:
        if check["outcome"] == "equal_by_versioned_generation_rule":
            _require(check["field"] in {"other_observed_settings." + name for name in ARRAY_SETTING_NAMES})
    outcomes = {r["outcome"] for r in compatibility["checks"]}
    if compatibility["state"] == "compatible":
        _require(set(r["field"] for r in compatibility["checks"]) == set(COMPATIBILITY_FIELDS))
        _require(outcomes <= {"equal", "equal_by_versioned_generation_rule"})
    elif "different" in outcomes:
        _require(compatibility["state"] == "incompatible")
    cells = _cells(value["components"], sheet, prefix="rna_energy_compare_v1", expected=ENERGY_METRICS)
    unit = "kcal/mol" if request["normalization"] == "none" else "kcal/mol/nt"
    for metric, cell in cells.items():
        _require(cell["unit"] == ("kcal/mol" if "native_energy" in metric else unit))
        if cell["origin"].startswith("retained_native_"):
            _require(cell["origin"] == ("retained_native_prediction" if quantity == "native_mfe" else "retained_native_evaluation"))
        if metric in ("energy_delta", "energy_absolute_delta") and compatibility["state"] != "compatible":
            _require(cell["state"] != "present")
    for side, original in (("baseline", baseline), ("variant", variant)):
        raw = cells[side + "_native_energy"]
        native = None if original is None else original[quantity]
        if native is not None and native["state"] == "present":
            _require(raw["state"] == "present" and raw["value"] == native["value"])
        else:
            _require(raw["state"] != "present")
    if compatibility["state"] != "compatible" or cells["energy_delta"]["state"] != "present":
        _require(value["order"] == "unavailable")
    if request["baseline_absolute_tolerance"] is None:
        _require(cells["baseline_tolerance"]["state"] == "not_requested" and value["baseline_tolerance_band"] == "not_requested")
    else:
        _require(cells["baseline_tolerance"]["state"] == "present" and
            cells["baseline_tolerance"]["value"] == request["baseline_absolute_tolerance"])


def _validate_components(value, sheet):
    _walk_issues(value, sheet)
    _require([c["comparison_id"] for c in value["comparisons"]] == [c["comparison_id"] for c in sheet["comparisons"]])
    operands = {r["member_id"]: r for r in sheet["operands"]}
    for supplied, inputs in zip(value["comparisons"], sheet["comparisons"]):
        for field in ("comparison_id", "baseline_member_id", "variant_member_id", "correspondence", "resolved_selections"):
            _require(_same(supplied[field], inputs[field]))
        baseline = operands[inputs["baseline_member_id"]]["original_sheet"]
        variant = operands[inputs["variant_member_id"]]["original_sheet"]
        topology_requested = inputs["calculate_pair_changes"] or bool(inputs["resolved_selections"])
        if topology_requested:
            _validate_site_rows(supplied["all_site_rows"], inputs, baseline, variant, sheet)
        else:
            _require(not supplied["all_site_rows"])
        if inputs["calculate_pair_changes"]:
            _validate_pair_rows(supplied["all_pair_rows"], inputs, baseline, variant)
        else:
            _require(not supplied["all_pair_rows"] and supplied["pairing_change_state"] == "not_requested")
        selections = {r["selection"]["selection_id"]: r for r in inputs["resolved_selections"]}
        groups = {}
        for cell in supplied["components"]:
            selection = cell["selection_id"]
            _require(selection is None or selection in selections)
            groups.setdefault(selection, []).append(cell)
        pair_cells = groups.pop(None, [])
        _cells(pair_cells, sheet, prefix="rna_pair_compare_v1", expected=PAIR_METRICS if inputs["calculate_pair_changes"] else None)
        if not inputs["calculate_pair_changes"]:
            _require(all(c["state"] == "not_requested" for c in pair_cells))
        _require(set(groups) == set(selections))
        original_topologies = [None if original is None else original["topology"] for original in (baseline, variant)]
        valid_topology = all(topology is not None and topology["status"] == "valid" for topology in original_topologies)
        valid_map = inputs["correspondence"] is not None and inputs["correspondence"]["state"] == "valid"
        if not (valid_topology and valid_map):
            for cell in pair_cells:
                metric = cell["metric"]
                side = 0 if metric == "baseline_pair_count" else 1 if metric == "variant_pair_count" else None
                if side is not None:
                    topology = original_topologies[side]
                    if topology is None or topology["status"] != "valid":
                        _require(cell["state"] != "present")
                elif not (metric.startswith("alignment_") and valid_map):
                    _require(cell["state"] != "present")
        invalid_selections = {i["selection_id"] for i in inputs["issues"] if i["code"] == "invalid_site_selection"}
        for selection, rows in groups.items():
            _cells(rows, sheet, prefix="rna_site_compare_v1", selection_id=selection, expected=SITE_METRICS)
            if selection in invalid_selections:
                _require(all(c["state"] != "present" and c["reason"] == "invalid_site_selection" for c in rows))
            elif not (valid_topology and valid_map):
                biological = {"changed_site_count", "unchanged_site_count", "lost_pairing_site_count",
                    "gained_pairing_site_count", "reassigned_partner_site_count", "changed_site_fraction", "unchanged_site_fraction"}
                _require(all(c["state"] != "present" for c in rows if c["metric"] in biological))
        _energy_relationship(supplied["energy"], inputs, baseline, variant, sheet)
    _validate_scan(value["scan"], sheet, value["comparisons"])
    for field in ("used_input_paths", "unused_input_paths"):
        for pointer in value[field]:
            resolve_comparison_input_path(sheet, pointer)
    _require(not (set(value["used_input_paths"]) & set(value["unused_input_paths"])))


def _validate_scan(scan, sheet, comparisons):
    request = sheet["scan_request"]
    if request is None:
        _require(scan is None)
        return
    _require(scan is not None and _same(scan["request"], request))
    baseline = sheet["selected_question"]["baseline_member_id"]
    _require(scan["baseline_member_id"] == baseline)
    originals = {r["member_id"]: r for r in sheet["operands"]}
    by_variant = {c["variant_member_id"]: c for c in comparisons}
    _require([r["member_id"] for r in scan["members"]] == list(originals))
    for member in scan["members"]:
        original = originals[member["member_id"]]
        alias = original["state"] == "alias"
        canonical_id = original["canonical_member_id"]
        _require(member["canonical_member_id"] == canonical_id and member["membership_state"] == ("alias" if alias else "canonical"))
        comparison = by_variant.get(canonical_id)
        _require(member["comparison_id"] == (comparison["comparison_id"] if comparison is not None else None))
        for field, metric in (("exact_rank_start", "member_rank_start"), ("exact_rank_end", "member_rank_end")):
            cell = member[field]
            if cell is not None:
                _cell_relationship(cell, sheet, prefix="rna_scan_energy_v1")
                _require(cell["metric"] == metric)
                if member["energy_state"] != "comparable":
                    _require(cell["state"] != "present")
        for field in ("energy", "delta"):
            if member[field] is not None:
                _cell_relationship(member[field], sheet)
                _require(member[field]["metric"] in (("baseline_selected_energy", "variant_selected_energy") if field == "energy" else ("energy_delta",)))
        if request["energy"] is None:
            _require(member["energy_state"] == "not_requested" and all(member[k] is None for k in ("energy", "delta", "exact_rank_start", "exact_rank_end")))
    if request["energy"] is None:
        _require(not scan["energy_components"] and scan["baseline_rank_class"] == "not_requested")
    else:
        _cells(scan["energy_components"], sheet, prefix="rna_scan_energy_v1", expected=SCAN_ENERGY_METRICS)
    selections = {}
    for inputs in sheet["comparisons"]:
        for item in inputs["resolved_selections"]:
            if item["selection"]["selection_id"] in request["topology_selection_ids"]:
                selections[item["selection"]["selection_id"]] = item
    expected_sites = [(key, i) for key in request["topology_selection_ids"] for i in selections[key]["indices"]]
    _require([(r["selection_id"], r["baseline_index"]) for r in scan["site_components"]] == expected_sites)
    for row in scan["site_components"]:
        _cells(row["components"], sheet, prefix="rna_scan_site_v1", selection_id=row["selection_id"], expected=SCAN_SITE_METRICS)
