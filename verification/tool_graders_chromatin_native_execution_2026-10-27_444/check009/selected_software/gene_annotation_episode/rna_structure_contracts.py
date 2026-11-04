"""Closed pure contracts for the two RNA scientific operations.

Validation is deterministic data validation, not a native-execution or biological
acceptance gate. No validator imports ViennaRNA or accesses files, Store, network,
subprocesses or a model service. Original invalid scientific strings remain valid
containers so they can be retained with specific input issues.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
import math
import re
from pathlib import PurePosixPath

COORDINATE_SYSTEM = "zero_based_sequence_indices_and_half_open_intervals"
MODES = ("mfe_prediction", "supplied_features")
OPERATIONS = dict(zip(MODES, ("predict_rna_secondary_structure", "analyze_rna_secondary_structure_features")))
INPUT_SCHEMAS = dict(zip(MODES, ("rna_prediction_input_v1", "rna_feature_input_v1")))
SHEET_SCHEMAS = dict(zip(MODES, ("rna_mfe_prediction_sheet_v1", "rna_supplied_structure_feature_sheet_v1")))
NATIVE_FORMATS = ("rna_native_record_json_v1", "biomni_rna_structure_text_v0")
RNA_SYMBOLS = "ACGURYSWKMBDHVN"
PAIR_TYPES = tuple(a + b for a in "ACGU" for b in "ACGU")
CELL_STATES = frozenset(("present", "not_requested", "not_produced", "missing_input",
    "invalid_input", "incompatible", "failed", "truncated"))
ARTIFACT_ROLES = frozenset(("input", "model_parameter_input", "native_result", "model",
    "effective_parameters", "stdout", "stderr"))
UNCERTAINTY_REASON = "selected_algorithm_does_not_produce_uncertainty"
UNCERTAINTY_NAMES = ("pair_probabilities", "ensemble_free_energy_kcal_mol", "mfe_frequency",
    "ensemble_diversity", "energy_standard_error", "energy_interval")

# Values explain concrete states; they are not executable grading rules.
RNA_ISSUE_MEANINGS = {
    "not_requested": "The selected operation did not request this quantity.",
    UNCERTAINTY_REASON: "Neither selected single-structure algorithm produces this uncertainty.",
    "no_sequence_supplied": "The optional original sequence is null.",
    "zero_pair_denominator": "The valid topology has zero pairs.",
    "zero_stem_denominator": "The valid topology has zero stems.",
    "zero_closed_loop_denominator": "The valid topology has zero closed loops.",
    "zero_unambiguous_pair_denominator": "No pair has two unambiguous RNA bases.",
    "normalization_not_requested": "The caller selected no energy normalization.",
    "native_metadata_not_retained": "The recorded legacy output did not retain native settings/version.",
    "rna_empty_sequence": "A supplied sequence is empty, rather than absent.",
    "rna_empty_structure": "The supplied structure is empty.",
    "rna_invalid_sequence_symbol": "A sequence symbol is outside the declared normalized alphabet.",
    "rna_sequence_structure_length_mismatch": "Sequence and structure lengths differ.",
    "rna_unbalanced_structure": "At least one opening or closing bracket has no partner.",
    "rna_mismatched_bracket": "A closing bracket has an incompatible opening token.",
    "rna_crossing_pairs_unsupported": "The balanced typed bracket pairs cross; no nested subset is emitted.",
    "rna_native_dependency_missing": "The selected native dependency was unavailable.",
    "rna_software_identity_mismatch": "The actual interpreter, worker or native import identity conflicts with an explicitly bound Software field.",
    "rna_native_api_unsupported": "The actual native API lacks a required operation or field.",
    "rna_parameter_load_failed": "The selected native parameter load/save operation failed.",
    "rna_native_failed": "The selected native operation failed.",
    "rna_nonfinite_energy": "The recorded energy was not a finite number.",
    "rna_energy_structure_mismatch": "A native energy is associated with a different structure/model.",
    "rna_input_identity_mismatch": "Supplied or recorded input identities/content disagree or are unavailable.",
    "rna_topology_table_mismatch": "Recorded topology disagrees with exact reconstruction.",
    "rna_output_truncated": "The declared output ends inside an incomplete serialized value.",
    "rna_requested_metric_unavailable": "A requested metric has no available value.",
    "rna_subject_binding_conflict": "Supplied subject binding and original binding disagree.",
    "rna_invalid_native_schema": "Native bytes or their container do not satisfy the declared format.",
    "rna_invalid_parameter_schema": "Calculator/model parameter container or operands are invalid.",
    "rna_model_snapshot_missing": "A required retained effective model snapshot is absent.",
    "rna_native_result_missing": "The native artifact is actually absent, not an empty file.",
    "rna_native_result_incompatible": "Recorded native fields cannot consistently describe the selected operation.",
    "rna_requested_row_missing": "The selected saved row does not exist.",
    "rna_zero_length_denominator": "A known zero nucleotide denominator cannot be divided.",
    "rna_capture_unavailable": "A selected original artifact could not be acquired.",
    "rna_capture_digest_mismatch": "Acquired bytes disagree with the original digest/size.",
    "rna_original_attempt_mismatch": "A receipt or artifact names another original attempt.",
    "rna_unsealed_native_attempt": "The original attempt is not sealed.",
    "rna_unknown_native_setting": "A requested native setting is not in the closed contract.",
    "rna_output_path_conflict": "Declared output paths conflict.",
    "rna_region_side_not_defined": "This region kind has no two-side definition.",
    # Additional concrete validation codes, covered by the dedicated tests.
    "rna_invalid_structure_symbol": "A structure character is outside .()[]{}.",
    "rna_invalid_input_schema": "The input container, primitive types or coordinate convention is invalid.",
    "rna_invalid_sheet_schema": "The saved sheet has invalid or contradictory fields.",
    "rna_invalid_component_schema": "A saved component disagrees with its sheet/parameters or closed cell schema.",
    "rna_legacy_context_missing": "The selected legacy parser requires an independently supplied original sequence.",
}
RNA_ISSUE_CODES = frozenset(RNA_ISSUE_MEANINGS)
ISSUE_STAGES = frozenset(("input", "native", "capture", "parse", "calculate", "binding", "selection"))

TOPOLOGY_METRICS = ("n_nt", "pair_count", "paired_nt", "unpaired_nt", "paired_fraction",
    "unpaired_fraction", "mean_pair_span_nt", "stem_count", "longest_stem_pairs",
    "mean_stem_pairs", "stack_count", "long_stem_count", "long_stem_fraction",
    "hairpin_count", "bulge_count", "internal_loop_count", "multibranch_count",
    "loop_mean_unpaired_nt", "loop_max_unpaired_nt", "external_unpaired_nt")
COMPOSITION_METRICS = ("unambiguous_pair_count", "ambiguous_pair_count", "accepted_pair_count",
    "accepted_pair_fraction", *("pair_count_" + pair for pair in PAIR_TYPES))
ENERGY_METRICS = ("mfe_kcal_mol", "evaluated_energy_kcal_mol", "mfe_per_nt", "evaluated_energy_per_nt")
ROW_METRICS = {"summary": TOPOLOGY_METRICS + COMPOSITION_METRICS + ENERGY_METRICS,
    "pairs": ("pair_span_nt",), "stems": ("stem_length_pairs", "stack_count"),
    "regions": ("loop_unpaired_nt", "branch_count", "five_prime_unpaired_nt", "three_prime_unpaired_nt")}
METRIC_UNITS = {
    "n_nt": "nt", "pair_count": "pairs", "paired_nt": "nt", "unpaired_nt": "nt",
    "paired_fraction": "dimensionless", "unpaired_fraction": "dimensionless",
    "mean_pair_span_nt": "nt", "stem_count": "stems", "longest_stem_pairs": "pairs",
    "mean_stem_pairs": "pairs/stem", "stack_count": "stacks", "long_stem_count": "stems",
    "long_stem_fraction": "dimensionless", "hairpin_count": "regions", "bulge_count": "regions",
    "internal_loop_count": "regions", "multibranch_count": "regions", "loop_mean_unpaired_nt": "nt",
    "loop_max_unpaired_nt": "nt", "external_unpaired_nt": "nt", "unambiguous_pair_count": "pairs",
    "ambiguous_pair_count": "pairs", "accepted_pair_count": "pairs", "accepted_pair_fraction": "dimensionless",
    **{"pair_count_" + p: "pairs" for p in PAIR_TYPES}, "mfe_kcal_mol": "kcal/mol",
    "evaluated_energy_kcal_mol": "kcal/mol", "mfe_per_nt": "kcal/mol/nt",
    "evaluated_energy_per_nt": "kcal/mol/nt", "pair_span_nt": "nt", "stem_length_pairs": "pairs",
    "loop_unpaired_nt": "nt", "branch_count": "pairs", "five_prime_unpaired_nt": "nt",
    "three_prime_unpaired_nt": "nt"}


def _require(condition, code="rna_invalid_native_schema"):
    if not condition:
        raise ValueError(code)


def _object(value, keys, code="rna_invalid_native_schema"):
    _require(type(value) is dict and set(value) == set(keys), code)


def _id(value):
    return type(value) is str and bool(value) and "\0" not in value


def _count(value):
    return type(value) is int and value >= 0


def _number(value):
    # Python integers are finite; do not coerce arbitrarily large integers to a
    # float merely to validate their container type.
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _contract_errors(code):
    """Normalize malformed container failures to the declared validator error."""
    def decorate(function):
        @wraps(function)
        def checked(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except (TypeError, KeyError, AttributeError, IndexError, OverflowError) as error:
                raise ValueError(code) from error
        return checked
    return decorate


def _same(left, right):
    """Exact container/scalar equality, keeping bool/float out of integer slots."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def issue(code: str, *, stage: str, record_key=None, field=None, index=None, artifact_role=None) -> dict:
    """Construct one closed issue; full native diagnostic prose belongs elsewhere."""
    value = {"stage": stage, "code": code, "record_key": record_key, "field": field,
        "index": index, "artifact_role": artifact_role}
    return validate_rna_issue(value)


def _leaf_fields(names):
    return dict.fromkeys(names.split())


def _issue_pointer_shapes():
    """Declared member grammar only, not instance existence or index bounds.

    None marks a scalar leaf, a one-element tuple an array, and a dictionary a
    closed member set. This is a data-path validator, never a scoring language.
    Member unions cover the explicitly declared contract variants.
    """
    binding = _leaf_fields("subject_ref sequence_artifact_ref start end strand")
    inputs = _leaf_fields("schema record_key sequence_id sequence normalization structure_id dot_bracket structure_origin structure_source_ref energy_mode")
    inputs["subject_binding"] = binding
    pair = {**_leaf_fields("pair_key i j opening_token closing_token parent_pair_key stem_key"), "child_pair_keys": (None,)}
    stem = {"stem_key": None, "pair_keys": (None,), "outer_pair": (None,), "inner_pair": (None,)}
    region = {**_leaf_fields("region_key kind closing_pair_key"), "immediate_branch_pair_keys": (None,),
        "unpaired_intervals": ((None,),), "unpaired_indices": (None,),
        "five_prime_unpaired_indices": (None,), "three_prime_unpaired_indices": (None,)}
    issue_shape = _leaf_fields("stage code record_key field index artifact_role")
    topology = {**_leaf_fields("schema coordinate_system dot_bracket length_nt status"),
        "positions": (_leaf_fields("index input_index bracket partner_index pair_key stem_key unpaired_region_key"),),
        "pairs": (pair,), "stems": (stem,), "regions": (region,), "issues": (issue_shape,)}
    uncertainty = _leaf_fields("state value reason")
    cell = {**_leaf_fields("name value unit state reason numerator denominator origin formula_id"),
        "input_fields": (None,), "uncertainty": uncertainty}
    component_row = {"row_key": None, "cells": (cell,)}
    settings = _leaf_fields("temperature_c dangles noLP noGU noGUclosure special_hp logML min_loop_size max_bp_span circ gquad")
    selected_model = {**settings, **_leaf_fields("schema hard_constraints soft_constraints"),
        "parameters": _leaf_fields("kind operand_role")}
    model = {**selected_model, **_leaf_fields("model_key engine engine_version parameter_load_return parameter_save_return"),
        "selected": selected_model, "effective_settings": settings,
        "other_observed_settings": (_leaf_fields("name value state"),),
        "parameter_artifact": _leaf_fields("relative_path sha256 size_bytes")}
    energy = _leaf_fields("value numeric_text unit state reason structure_key engine engine_version model_key")
    parameters = {**_leaf_fields("schema kind operand_role"),
        "topology": _leaf_fields("long_stem_min_pairs include_exterior_in_loop_size_statistics"),
        "pair_composition": {"accepted_ordered_pair_types": (None,), "denominator": None},
        "energy": {"normalization": None}}
    return {
        "input": inputs, "original_input": inputs, "subject_binding": binding,
        **_leaf_fields("sequence dot_bracket normalization record_key mode schema status"),
        "analysis_sequence": {**_leaf_fields("original_sequence analysis_sequence case_operation length_nt alphabet"),
            "original_to_analysis_indices": (None,), "symbol_counts": dict.fromkeys(RNA_SYMBOLS), "ambiguous_indices": (None,)},
        "structure": {**_leaf_fields("structure_key structure_id dot_bracket origin source_ref energy_dot_bracket"),
            "energy_conversion": {"kind": None, "index_map": (None,)}},
        "topology": topology, "native_mfe": energy, "native_evaluation": energy,
        "native_uncertainty": {name: uncertainty for name in UNCERTAINTY_NAMES}, "model": model,
        "native_input": _leaf_fields("format sha256 byte_count"),
        "sequence_pairs": (_leaf_fields("pair_key symbol_i symbol_j ordered_pair unambiguous"),),
        "parameters": parameters, "outputs": (_leaf_fields("role format relative_path"),),
        "operands": (_leaf_fields("role path format sha256 size_bytes artifact_ref"),),
        "files": (_leaf_fields("kind role format relative_path state sha256 size_bytes artifact_ref path"),),
        "software": _leaf_fields("python_executable python_sha256 python_version worker_module worker_source_sha256 viennarna_distribution_version rna_module_sha256 rna_extension_sha256"),
        "identity": _leaf_fields("run_id episode_id resource_id execution_id attempt_id operation_key requested_job_sha256"),
        "selector": {"version": None, "acquisition": None,
            "parameters": {key: parameters[key] for key in ("schema", "topology", "pair_composition", "energy")},
            "saved_input": _leaf_fields("schema result_receipt_key handoff_ref source_ref bundle_artifact_ref sheet_artifact_ref sheet_sha256 record_key operation mode"),
            "projection": {"family": None,
            "rows": {"record_keys": (None,), "offset": None, "limit": None}, "metrics": (None,)}},
        "summary": (cell,), "pairs": ({**pair, **component_row},),
        "stems": ({**stem, **component_row},), "regions": ({**region, **component_row},),
        "effective_settings": settings, "parameter_artifact": _leaf_fields("relative_path sha256 size_bytes"),
    }


_ISSUE_POINTER_SHAPES = _issue_pointer_shapes()


def _valid_issue_pointer(field):
    if type(field) is not str or not field.startswith("/") or "\0" in field or re.search(r"~(?![01])", field):
        return False
    shape = _ISSUE_POINTER_SHAPES
    for token in field[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(shape, tuple):
            if re.fullmatch(r"0|[1-9][0-9]*", token) is None:
                return False
            shape = shape[0]
        elif isinstance(shape, dict) and token in shape:
            shape = shape[token]
        else:
            return False
    return True


@_contract_errors("rna_invalid_native_schema")
def validate_rna_issue(value: dict) -> dict:
    _object(value, ("stage", "code", "record_key", "field", "index", "artifact_role"))
    _require(value["stage"] in ISSUE_STAGES and value["code"] in RNA_ISSUE_CODES)
    _require(value["record_key"] is None or _id(value["record_key"]))
    _require(value["index"] is None or _count(value["index"]))
    _require(value["artifact_role"] is None or value["artifact_role"] in ARTIFACT_ROLES)
    field = value["field"]
    _require(field is None or _valid_issue_pointer(field))
    return deepcopy(value)


def _issues(values, record_key=None):
    _require(type(values) is list)
    for value in values:
        validate_rna_issue(value)
        if record_key is not None:
            _require(value["record_key"] in (None, record_key), "rna_input_identity_mismatch")


def no_native_uncertainty() -> dict:
    return {"state": "not_produced", "value": None, "reason": UNCERTAINTY_REASON}


def native_uncertainty() -> dict:
    return {name: no_native_uncertainty() for name in UNCERTAINTY_NAMES}


def unavailable_energy(state="not_requested", reason="not_requested", *, structure_key=None) -> dict:
    return {"value": None, "numeric_text": None, "unit": "kcal/mol", "state": state,
        "reason": reason, "structure_key": structure_key, "engine": None,
        "engine_version": None, "model_key": None}


@_contract_errors("rna_invalid_input_schema")
def validate_rna_subject_binding(value: dict) -> dict:
    code = "rna_invalid_input_schema"
    _object(value, ("subject_ref", "sequence_artifact_ref", "start", "end", "strand"), code)
    _require(_id(value["subject_ref"]) and _id(value["sequence_artifact_ref"]), code)
    _require(_count(value["start"]) and _count(value["end"]) and value["start"] < value["end"], code)
    _require(value["strand"] in ("+", "-"), code)
    return deepcopy(value)


@_contract_errors("rna_invalid_input_schema")
def validate_rna_input(value: dict, *, mode: str) -> dict:
    """Validate the container, preserving even empty/invalid scientific strings."""
    code = "rna_invalid_input_schema"
    _require(mode in MODES, code)
    keys = ("schema", "record_key", "sequence_id", "sequence", "normalization", "subject_binding")
    if mode == "supplied_features":
        keys += ("structure_id", "dot_bracket", "structure_origin", "structure_source_ref", "energy_mode")
    _object(value, keys, code)
    _require(value["schema"] == INPUT_SCHEMAS[mode] and _id(value["record_key"]), code)
    _require(value["sequence_id"] is None or _id(value["sequence_id"]), code)
    _require(type(value["sequence"]) is str or (mode == "supplied_features" and value["sequence"] is None), code)
    _require(value["normalization"] in ("exact", "uppercase_ascii"), code)
    if value["subject_binding"] is not None:
        validate_rna_subject_binding(value["subject_binding"])
    if mode == "supplied_features":
        _require(type(value["dot_bracket"]) is str, code)
        _require(value["structure_id"] is None or _id(value["structure_id"]), code)
        _require(value["structure_origin"] in ("supplied_unknown", "supplied_prediction", "supplied_observation"), code)
        _require(value["structure_source_ref"] is None or _id(value["structure_source_ref"]), code)
        _require(value["structure_origin"] == "supplied_unknown" or value["structure_source_ref"] is not None, code)
        _require(value["energy_mode"] in ("none", "viennarna_evaluate"), code)
    return deepcopy(value)


def analyze_rna_input_sequence(value: dict, *, mode: str) -> tuple[dict | None, list[dict]]:
    """Normalize only ASCII case, then count exact symbols without expansion.

    A length mismatch still retains independently valid symbol counts. Consumers
    must check matching structure length before using positional sequence pairs.
    """
    request = validate_rna_input(value, mode=mode)
    original = request["sequence"]
    key = request["record_key"]
    if original is None:
        return None, [issue("no_sequence_supplied", stage="input", record_key=key, field="/sequence")]
    if not original:
        return None, [issue("rna_empty_sequence", stage="input", record_key=key, field="/sequence")]
    sequence = (original.translate(str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
        if request["normalization"] == "uppercase_ascii" else original)
    alphabet = "ACGU" if mode == "mfe_prediction" else RNA_SYMBOLS
    errors = [issue("rna_invalid_sequence_symbol", stage="input", record_key=key, field="/sequence", index=i)
        for i, symbol in enumerate(sequence) if symbol not in alphabet]
    if errors:
        return None, errors
    analysis = {"original_sequence": original, "analysis_sequence": sequence,
        "case_operation": request["normalization"], "original_to_analysis_indices": list(range(len(sequence))),
        "length_nt": len(sequence), "alphabet": "ACGU" if mode == "mfe_prediction" else "RNA_IUPAC",
        "symbol_counts": {symbol: sequence.count(symbol) for symbol in RNA_SYMBOLS},
        "ambiguous_indices": [i for i, symbol in enumerate(sequence) if symbol not in "ACGU"]}
    if mode == "supplied_features" and len(sequence) != len(request["dot_bracket"]):
        errors.append(issue("rna_sequence_structure_length_mismatch", stage="input", record_key=key, field="/sequence"))
    return analysis, errors


@_contract_errors("rna_invalid_parameter_schema")
def validate_rna_parameters(value: dict) -> dict:
    code = "rna_invalid_parameter_schema"
    _object(value, ("schema", "topology", "pair_composition", "energy"), code)
    _require(value["schema"] == "rna_calculation_parameters_v1", code)
    _object(value["topology"], ("long_stem_min_pairs", "include_exterior_in_loop_size_statistics"), code)
    _require(type(value["topology"]["long_stem_min_pairs"]) is int and value["topology"]["long_stem_min_pairs"] >= 1, code)
    _require(value["topology"]["include_exterior_in_loop_size_statistics"] is False, code)
    _object(value["pair_composition"], ("accepted_ordered_pair_types", "denominator"), code)
    accepted = value["pair_composition"]["accepted_ordered_pair_types"]
    _require(type(accepted) is list and all(type(p) is str and p in PAIR_TYPES for p in accepted), code)
    _require(len(accepted) == len(set(accepted)) and value["pair_composition"]["denominator"] == "unambiguous_pairs", code)
    _object(value["energy"], ("normalization",), code)
    _require(value["energy"]["normalization"] in ("none", "per_nt"), code)
    return deepcopy(value)


@_contract_errors("rna_topology_table_mismatch")
def validate_topology(value: dict) -> dict:
    """Cross-check the complete indexed topology, not just producer aggregates."""
    from .rna_structure_topology import parse_rna_topology
    _object(value, ("schema", "coordinate_system", "dot_bracket", "length_nt", "status",
        "positions", "pairs", "stems", "regions", "issues"), "rna_topology_table_mismatch")
    _require(type(value["dot_bracket"]) is str, "rna_topology_table_mismatch")
    expected = parse_rna_topology(value["dot_bracket"], coordinate_system=COORDINATE_SYSTEM)
    _require(_same(value, expected), "rna_topology_table_mismatch")
    return deepcopy(value)


_MODEL_FIELDS = ("temperature_c", "dangles", "noLP", "noGU", "noGUclosure", "special_hp", "logML",
    "min_loop_size", "max_bp_span", "circ", "gquad")


def _model_settings(value):
    code = "rna_invalid_parameter_schema"
    _require(_number(value["temperature_c"]) and value["temperature_c"] > -273.15, code)
    _require(type(value["dangles"]) is int and value["dangles"] in range(4), code)
    _require(all(type(value[k]) is bool for k in ("noLP", "noGU", "noGUclosure", "special_hp", "logML")), code)
    _require(_count(value["min_loop_size"]), code)
    _require(type(value["max_bp_span"]) is int and (value["max_bp_span"] == -1 or value["max_bp_span"] >= 1), code)
    _require(value["circ"] is False and value["gquad"] is False, code)


@_contract_errors("rna_invalid_parameter_schema")
def validate_rna_model_spec_shape(value: dict) -> dict:
    """Check selected model shape only; no parameter file or native API is opened."""
    code = "rna_invalid_parameter_schema"
    _object(value, ("schema", *_MODEL_FIELDS, "hard_constraints", "soft_constraints", "parameters"), code)
    _require(value["schema"] == "vienna_rna_model_spec_v1", code)
    _model_settings(value)
    _require(value["hard_constraints"] is None and value["soft_constraints"] is None, code)
    _object(value["parameters"], ("kind", "operand_role"), code)
    _require(value["parameters"] in ({"kind": "turner2004", "operand_role": None},
        {"kind": "supplied_parameter_file", "operand_role": "model_parameter_input"}), code)
    return deepcopy(value)


@_contract_errors("rna_invalid_parameter_schema")
def validate_rna_effective_model_shape(value: dict) -> dict:
    """Check retained observed settings and their agreement with selected values."""
    code = "rna_invalid_parameter_schema"
    _object(value, ("schema", "model_key", "selected", "engine", "engine_version", "effective_settings",
        "other_observed_settings", "parameter_artifact", "parameter_load_return", "parameter_save_return"), code)
    _require(value["schema"] == "vienna_rna_effective_model_v1" and _id(value["model_key"]), code)
    _require(value["engine"] == "ViennaRNA" and _id(value["engine_version"]), code)
    validate_rna_model_spec_shape(value["selected"])
    _object(value["effective_settings"], _MODEL_FIELDS, code)
    _model_settings(value["effective_settings"])
    _require(all(value["selected"][k] == value["effective_settings"][k] for k in _MODEL_FIELDS), "rna_native_result_incompatible")
    _require(type(value["other_observed_settings"]) is list, code)
    names = []
    for setting in value["other_observed_settings"]:
        _object(setting, ("name", "value", "state"), code)
        _require(_id(setting["name"]) and setting["name"] not in _MODEL_FIELDS, code)
        names.append(setting["name"])
        _require(setting["state"] in ("observed", "unavailable"), code)
        _require(setting["value"] is None or type(setting["value"]) in (str, bool) or _number(setting["value"]), code)
        _require(setting["state"] != "unavailable" or setting["value"] is None, code)
    _require(len(names) == len(set(names)), code)
    artifact = value["parameter_artifact"]
    _object(artifact, ("relative_path", "sha256", "size_bytes"), code)
    path = artifact["relative_path"]
    _require(_id(path) and not PurePosixPath(path).is_absolute() and
        str(PurePosixPath(path)) == path and ".." not in PurePosixPath(path).parts and path != ".", code)
    _require(type(artifact["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", artifact["sha256"]) is not None, code)
    _require(_count(artifact["size_bytes"]), code)
    _require(type(value["parameter_load_return"]) is int and type(value["parameter_save_return"]) is int, code)
    return deepcopy(value)


def make_rna_structure(request: dict, dot_bracket: str, *, for_energy: bool) -> dict:
    """Build supplied/returned structure metadata; no structure is predicted here."""
    from .rna_structure_topology import parse_rna_topology
    mode = "mfe_prediction" if request["schema"] == INPUT_SCHEMAS["mfe_prediction"] else "supplied_features"
    request = validate_rna_input(request, mode=mode)
    topology = parse_rna_topology(dot_bracket, coordinate_system=COORDINATE_SYSTEM)
    conversion = energy_string = None
    if for_energy and topology["status"] == "valid":
        energy_string = dot_bracket.translate(str.maketrans("[]{}", "()()"))
        conversion = {"kind": "identity" if energy_string == dot_bracket else "bracket_alphabet_to_parentheses",
            "index_map": list(range(len(dot_bracket)))}
    return {"structure_key": request["record_key"] + ":structure",
        "structure_id": request.get("structure_id"), "dot_bracket": dot_bracket,
        "origin": "native_prediction" if mode == "mfe_prediction" else request["structure_origin"],
        "source_ref": request.get("structure_source_ref"), "energy_dot_bracket": energy_string,
        "energy_conversion": conversion}


def sequence_pair_rows(topology: dict | None, analysis: dict | None) -> list[dict] | None:
    """Join sequence symbols by exact indices only; mismatched length is unusable."""
    if topology is None or topology["status"] != "valid":
        return None
    sequence = (analysis["analysis_sequence"] if analysis is not None and
        analysis["length_nt"] == topology["length_nt"] else None)
    rows = []
    for pair in topology["pairs"]:
        left, right = (sequence[pair["i"]], sequence[pair["j"]]) if sequence is not None else (None, None)
        rows.append({"pair_key": pair["pair_key"], "symbol_i": left, "symbol_j": right,
            "ordered_pair": left + right if sequence is not None else None,
            "unambiguous": left in "ACGU" and right in "ACGU" if sequence is not None else None})
    return rows


def _validate_analysis(value, *, mode, request=None, require_available=False):
    if value is None:
        if request is not None and require_available:
            expected, _ = analyze_rna_input_sequence(request, mode=mode)
            _require(expected is None, "rna_input_identity_mismatch")
        return
    _object(value, ("original_sequence", "analysis_sequence", "case_operation", "original_to_analysis_indices",
        "length_nt", "alphabet", "symbol_counts", "ambiguous_indices"))
    if request is None:
        # Used only for independently recorded legacy sequence metadata. This
        # validation object is not retained as an invented original request.
        temporary = {"schema": INPUT_SCHEMAS["mfe_prediction"], "record_key": "validation",
            "sequence_id": None, "sequence": value["original_sequence"],
            "normalization": value["case_operation"], "subject_binding": None}
        expected, _ = analyze_rna_input_sequence(temporary, mode="mfe_prediction")
    else:
        expected, _ = analyze_rna_input_sequence(request, mode=mode)
    _require(_same(value, expected), "rna_input_identity_mismatch")


def _validate_structure(value, topology, *, mode, record_key, request=None):
    if value is None:
        _require(topology is None, "rna_topology_table_mismatch")
        return
    _object(value, ("structure_key", "structure_id", "dot_bracket", "origin", "source_ref",
        "energy_dot_bracket", "energy_conversion"))
    _require(value["structure_key"] == record_key + ":structure", "rna_input_identity_mismatch")
    _require(value["structure_id"] is None or _id(value["structure_id"]))
    _require(type(value["dot_bracket"]) is str)
    _require(value["source_ref"] is None or _id(value["source_ref"]))
    origins = ("native_prediction",) if mode == "mfe_prediction" else ("supplied_unknown", "supplied_prediction", "supplied_observation")
    _require(value["origin"] in origins)
    if value["origin"] in ("supplied_prediction", "supplied_observation"):
        _require(value["source_ref"] is not None)
    if mode == "mfe_prediction":
        _require(value["source_ref"] is None and value["structure_id"] is None)
    if request is not None and mode == "supplied_features":
        for field, original_field in (("dot_bracket", "dot_bracket"), ("structure_id", "structure_id"),
                ("origin", "structure_origin"), ("source_ref", "structure_source_ref")):
            _require(value[field] == request[original_field], "rna_input_identity_mismatch")
    _require(topology is not None, "rna_topology_table_mismatch")
    validate_topology(topology)
    _require(topology["dot_bracket"] == value["dot_bracket"], "rna_topology_table_mismatch")
    if value["energy_dot_bracket"] is None:
        _require(value["energy_conversion"] is None, "rna_energy_structure_mismatch")
    else:
        _require(topology["status"] == "valid", "rna_energy_structure_mismatch")
        converted = value["dot_bracket"].translate(str.maketrans("[]{}", "()()"))
        expected = {"kind": "identity" if converted == value["dot_bracket"] else "bracket_alphabet_to_parentheses",
            "index_map": list(range(len(converted)))}
        _require(value["energy_dot_bracket"] == converted and _same(value["energy_conversion"], expected), "rna_energy_structure_mismatch")


def _validate_energy(value, *, structure, model):
    _object(value, ("value", "numeric_text", "unit", "state", "reason", "structure_key", "engine", "engine_version", "model_key"))
    _require(value["unit"] == "kcal/mol" and value["state"] in CELL_STATES)
    _require(value["reason"] is None or value["reason"] in RNA_ISSUE_CODES)
    for field in ("structure_key", "engine_version", "model_key"):
        _require(value[field] is None or _id(value[field]))
    _require(value["engine"] in (None, "ViennaRNA"))
    if value["structure_key"] is not None:
        _require(structure is not None and value["structure_key"] == structure["structure_key"], "rna_energy_structure_mismatch")
    if value["state"] == "present":
        _require(_number(value["value"]), "rna_nonfinite_energy")
        _require(value["reason"] is None and value["engine"] == "ViennaRNA", "rna_energy_structure_mismatch")
        _require(structure is not None and value["structure_key"] == structure["structure_key"], "rna_energy_structure_mismatch")
        if value["numeric_text"] is not None:
            text = value["numeric_text"]
            _require(type(text) is str and re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text) is not None)
            _require(math.isfinite(float(text)) and float(text) == value["value"], "rna_energy_structure_mismatch")
        if model is not None:
            _require(value["model_key"] == model["model_key"] and
                value["engine_version"] == model["engine_version"], "rna_energy_structure_mismatch")
    else:
        _require(value["value"] is None and value["numeric_text"] is None and value["reason"] is not None)


def _validate_measurement_relationships(value, *, mode, request):
    """Shared native/sheet relationships, independent of execution success."""
    structure, topology = value["structure"], value["topology"]
    _validate_structure(structure, topology, mode=mode, record_key=value["record_key"], request=request)
    model = value["model"]
    if model is not None:
        validate_rna_effective_model_shape(model)
    _require(_same(value["native_uncertainty"], native_uncertainty()))
    for field in ("native_mfe", "native_evaluation"):
        _validate_energy(value[field], structure=structure, model=model)
        energy = value[field]
        if energy["state"] not in ("present", "not_requested", "not_produced"):
            _require(any(row["code"] == energy["reason"] for row in value["issues"]), "rna_native_result_incompatible")
        if energy["state"] == "present":
            _require(topology is not None and topology["status"] == "valid", "rna_energy_structure_mismatch")
            analysis = value["analysis_sequence"]
            _require(analysis is not None and analysis["length_nt"] == topology["length_nt"] and
                not analysis["ambiguous_indices"], "rna_energy_structure_mismatch")
    irrelevant = "native_evaluation" if mode == "mfe_prediction" else "native_mfe"
    _require(value[irrelevant]["state"] == "not_requested" and value[irrelevant]["reason"] == "not_requested", "rna_native_result_incompatible")
    requested = "native_mfe" if mode == "mfe_prediction" else "native_evaluation"
    if mode == "mfe_prediction" or (request is not None and request["energy_mode"] == "viennarna_evaluate"):
        _require(value[requested]["state"] not in ("not_requested", "not_produced"), "rna_native_result_incompatible")
    if value[requested]["state"] == "present" and model is None:
        _require(any(row["code"] in ("rna_model_snapshot_missing", "native_metadata_not_retained")
            for row in value["issues"]), "rna_model_snapshot_missing")
    if mode == "supplied_features" and request is not None and request["energy_mode"] == "none":
        _require(value["native_evaluation"]["state"] == "not_requested", "rna_native_result_incompatible")
    if mode == "mfe_prediction" and structure is not None:
        _require(topology["status"] == "valid", "rna_native_result_incompatible")
        _require(value["analysis_sequence"] is not None and
            value["analysis_sequence"]["length_nt"] == topology["length_nt"], "rna_input_identity_mismatch")


@_contract_errors("rna_invalid_native_schema")
def validate_rna_native_record(value: dict, *, expected_mode: str) -> dict:
    """Accept consistent complete, failed and partial records; reject contradictions."""
    _require(expected_mode in MODES)
    _object(value, ("schema", "operation", "mode", "record_key", "input", "analysis_sequence", "structure", "topology",
        "native_mfe", "native_evaluation", "native_uncertainty", "model", "status", "issues"))
    _require(value["schema"] == "rna_native_record_v1" and value["mode"] == expected_mode and
        value["operation"] == OPERATIONS[expected_mode])
    _require(_id(value["record_key"]) and value["status"] in ("complete", "partial", "failed"))
    _issues(value["issues"], value["record_key"])
    request = value["input"]
    if request is not None:
        validate_rna_input(request, mode=expected_mode)
        _require(request["record_key"] == value["record_key"], "rna_input_identity_mismatch")
        _validate_analysis(value["analysis_sequence"], mode=expected_mode, request=request)
        _, errors = analyze_rna_input_sequence(request, mode=expected_mode)
        _require(all(any(row["code"] == error["code"] and row["index"] == error["index"] for row in value["issues"])
            for error in errors), "rna_native_result_incompatible")
    elif any(row["code"] == "native_metadata_not_retained" for row in value["issues"]) and expected_mode == "mfe_prediction":
        _require(value["model"] is None and value["status"] != "complete")
        _validate_analysis(value["analysis_sequence"], mode=expected_mode)
    else:
        _require(value["status"] == "failed" and value["analysis_sequence"] is None and value["structure"] is None)
        _require(any(row["stage"] == "input" for row in value["issues"]))
    _validate_measurement_relationships(value, mode=expected_mode, request=request)
    if value["topology"] is not None:
        for error in value["topology"]["issues"]:
            _require(any(row["code"] == error["code"] and row["index"] == error["index"] for row in value["issues"]), "rna_native_result_incompatible")
    if value["status"] == "complete":
        _require(value["input"] is not None and value["topology"] is not None and
            value["topology"]["status"] == "valid", "rna_native_result_incompatible")
        requested_energy = expected_mode == "mfe_prediction" or request["energy_mode"] == "viennarna_evaluate"
        if requested_energy:
            energy = value["native_mfe" if expected_mode == "mfe_prediction" else "native_evaluation"]
            _require(energy["state"] == "present" and value["model"] is not None, "rna_native_result_incompatible")
        _require(all(row["code"] == "no_sequence_supplied" for row in value["issues"]), "rna_native_result_incompatible")
    elif value["status"] in ("partial", "failed"):
        _require(bool(value["issues"]), "rna_native_result_incompatible")
    return deepcopy(value)


@_contract_errors("rna_invalid_native_schema")
def validate_rna_native_parse(value: dict) -> dict:
    """Validate a reader result supplied to a populator, including absent bytes."""
    _object(value, ("schema", "format", "expected_mode", "raw_sha256", "raw_byte_count", "status", "record", "issues"))
    _require(value["schema"] == "rna_native_parse_v1" and value["format"] in NATIVE_FORMATS and value["expected_mode"] in MODES)
    _require(value["status"] in ("valid", "partial", "invalid"))
    _issues(value["issues"])
    if value["raw_sha256"] is None or value["raw_byte_count"] is None:
        _require(value["raw_sha256"] is None and value["raw_byte_count"] is None and value["record"] is None and value["status"] == "invalid")
        _require(any(row["code"] == "rna_native_result_missing" for row in value["issues"]))
    else:
        _require(type(value["raw_sha256"]) is str and re.fullmatch("[0-9a-f]{64}", value["raw_sha256"]) is not None)
        _require(_count(value["raw_byte_count"]))
    if value["record"] is not None:
        validate_rna_native_record(value["record"], expected_mode=value["expected_mode"])
        _require(value["status"] != "invalid")
    else:
        _require(value["status"] == "invalid" and bool(value["issues"]))
    return deepcopy(value)


@_contract_errors("rna_invalid_sheet_schema")
def validate_rna_sheet(value: dict) -> dict:
    """Validate saved data relationships before any calculation or recalculation."""
    code = "rna_invalid_sheet_schema"
    _object(value, ("schema", "operation", "mode", "record_key", "original_input", "coordinate_system",
        "analysis_sequence", "structure", "topology", "sequence_pairs", "native_mfe", "native_evaluation",
        "native_uncertainty", "model", "subject_binding", "status", "issues", "native_input", "legacy_quantities"), code)
    mode = value["mode"]
    _require(mode in MODES and value["schema"] == SHEET_SCHEMAS[mode] and value["operation"] == OPERATIONS[mode], code)
    _require(_id(value["record_key"]) and value["coordinate_system"] == COORDINATE_SYSTEM, code)
    _require(value["status"] in ("complete", "partial", "invalid") and value["legacy_quantities"] is None, code)
    _issues(value["issues"], value["record_key"])
    request = value["original_input"]
    if request is not None:
        validate_rna_input(request, mode=mode)
        _require(request["record_key"] == value["record_key"], "rna_input_identity_mismatch")
        _validate_analysis(value["analysis_sequence"], mode=mode, request=request, require_available=True)
        _, errors = analyze_rna_input_sequence(request, mode=mode)
        _require(all(any(row["code"] == error["code"] and row["index"] == error["index"] for row in value["issues"])
            for error in errors), code)
    else:
        _require(value["analysis_sequence"] is None and value["structure"] is None and value["subject_binding"] is None, code)
        _require(any(row["code"] == "rna_invalid_input_schema" for row in value["issues"]), code)
    if value["subject_binding"] is not None:
        validate_rna_subject_binding(value["subject_binding"])
        _require(request is not None and _same(value["subject_binding"], request["subject_binding"]), "rna_subject_binding_conflict")
    _validate_measurement_relationships(value, mode=mode, request=request)
    if value["topology"] is not None:
        _require(all(any(row["code"] == error["code"] and row["index"] == error["index"] for row in value["issues"])
            for error in value["topology"]["issues"]), code)
    _require(_same(value["sequence_pairs"], sequence_pair_rows(value["topology"], value["analysis_sequence"])), code)
    if value["native_input"] is not None:
        native = value["native_input"]
        _object(native, ("format", "sha256", "byte_count"), code)
        _require(native["format"] in NATIVE_FORMATS and type(native["sha256"]) is str and
            re.fullmatch("[0-9a-f]{64}", native["sha256"]) is not None and _count(native["byte_count"]), code)
    else:
        _require(any(row["code"] == "rna_native_result_missing" for row in value["issues"]), code)
    valid_topology = value["topology"] is not None and value["topology"]["status"] == "valid"
    expected_status = ("invalid" if not valid_topology else "partial" if
        any(row["code"] != "no_sequence_supplied" for row in value["issues"]) else "complete")
    _require(value["status"] == expected_status, code)
    return deepcopy(value)


@_contract_errors("rna_invalid_component_schema")
def validate_rna_components(value: dict, *, sheet: dict) -> dict:
    """Check every saved cell against its data and explicit ordinary-function parameters."""
    from .rna_structure_calculations import _calculate
    code = "rna_invalid_component_schema"
    validated_sheet = validate_rna_sheet(sheet)
    _object(value, ("schema", "sheet_schema", "record_key", "parameters", "calculator_version", "summary",
        "pairs", "stems", "regions", "issues", "used_native_fields", "unused_native_fields"), code)
    parameters = validate_rna_parameters(value["parameters"])
    expected = _calculate(validated_sheet, parameters)
    _require(_same(value, expected), code)
    return deepcopy(value)
