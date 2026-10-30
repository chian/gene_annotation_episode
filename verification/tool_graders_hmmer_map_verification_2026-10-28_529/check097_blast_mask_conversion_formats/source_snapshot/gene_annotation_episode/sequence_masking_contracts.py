"""Closed, offline contracts for raw-sequence masking preparation.

Native observations may contain qualified invalid rows. Schema errors are caller
errors; native-data errors live in the retained checks/failures instead. This
module does not select native defaults, authenticate custody, or score function.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re

from .domain import ContractError


ALPHABETS = {"dna": frozenset("ACGTNRYKMSWBDHV"),
             "protein": frozenset("ACDEFGHIKLMNPQRSTVWYBXZJUO*")}
_MACHINE = re.compile(r"[a-z][a-z0-9_]*\Z")
_I32 = 2**31 - 1
_I64 = 2**63 - 1
_PCT = {k: ("number", 0, 100) for k in
        ("t_low_pct", "t_extend_pct", "t_thres_pct", "t_high_pct")}
PARAMETERS = {
    ("dustmasker", "mask"): {"window": ("integer", 1, _I32),
        "level": ("integer", 0, _I32), "linker": ("integer", 0, _I32)},
    ("segmasker", "mask"): {"window": ("integer", 1, _I32),
        "locut": ("number", 0, None), "hicut": ("number", 0, None)},
    ("windowmasker", "mask"): {
        **{k: ("integer", 1, _I32) for k in
           ("window", "t_thres", "t_low", "t_high", "set_t_low", "set_t_high")},
        "t_extend": ("integer", 0, _I32), **_PCT,
        "dust": ("boolean", None, None), "dust_level": ("integer", 0, _I32)},
    ("windowmasker", "create_counts"): {
        "checkdup": ("boolean", None, None), "mem": ("integer", 1, _I32),
        "unit": ("integer", 1, 16), "genome_size": ("integer", 1, _I64),
        "meta": ("text", None, None), "t_low": ("integer", 1, _I32),
        "t_high": ("integer", 1, _I32), **_PCT},
}


def _require(condition, code="invalid_relationship"):
    if not condition:
        raise ContractError("sequence_masking_" + code)


def _object(value, keys):
    _require(type(value) is dict and set(value) == set(keys.split()), "object_fields")


def _string(value, *, nullable=False, nonempty=False, machine=False):
    if value is None and nullable:
        return
    _require(type(value) is str, "string_required")
    _require(not nonempty or bool(value.strip()), "empty_string")
    _require(not machine or _MACHINE.fullmatch(value) is not None, "machine_string")


def _integer(value, low=0, high=None, *, nullable=False):
    if value is None and nullable:
        return
    _require(type(value) is int, "integer_required")
    _require((low is None or value >= low) and (high is None or value <= high), "integer_range")


def _number(value, low=None, high=None, *, nullable=False):
    if value is None and nullable:
        return
    _require(type(value) in (int, float), "number_required")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    _require(finite, "nonfinite_number")
    _require((low is None or value >= low) and (high is None or value <= high), "number_range")


def _enum(value, choices):
    _require(type(value) is str and value in choices.split(), "enum_value")


def _boolean(value):
    _require(type(value) is bool, "boolean_required")


def _list(value, validator):
    _require(type(value) is list, "list_required")
    for row in value:
        validator(row)


def _unique(values):
    _require(len(values) == len(set(values)), "duplicate_identity")


def _diagnostics(value):
    _list(value["checks"], _check)
    _list(value["failures"], _failure)


def _failure(value):
    _object(value, "stage code occurrence_id record_key line_number")
    _enum(value["stage"], "input parse association native statistics calculation custody")
    _string(value["code"], machine=True)
    for k in ("occurrence_id", "record_key"):
        _string(value[k], nullable=True, nonempty=True)
    _integer(value["line_number"], 1, nullable=True)


def _check(value):
    _object(value, "name status record_key reason")
    _string(value["name"], machine=True)
    _enum(value["status"], "pass fail unknown not_applicable")
    _string(value["record_key"], nullable=True, nonempty=True)
    _string(value["reason"], nullable=True, machine=True)


def _occurrence(value):
    _object(value, "occurrence_id direction role ordinal artifact_ref sha256 size_bytes completeness")
    for key in ("occurrence_id", "artifact_ref"):
        _string(value[key], nonempty=True)
    _enum(value["direction"], "input output")
    _enum(value["role"], "sequences reference_sequences statistics mask stdout stderr")
    _integer(value["ordinal"])
    _integer(value["size_bytes"])
    _string(value["sha256"])
    _require(re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None, "sha256")
    _enum(value["completeness"], "complete partial unknown")
    if value["role"] in ("sequences", "reference_sequences"):
        _require(value["direction"] == "input", "occurrence_direction")
    if value["role"] in ("mask", "stdout", "stderr"):
        _require(value["direction"] == "output", "occurrence_direction")


def _operation(value):
    _object(value, "version program mode engine_version input_format output_format masking_style parse_seqids requested_parameters")
    _enum(value["version"], "sequence_masking_operation_v1")
    _enum(value["program"], "dustmasker segmasker windowmasker")
    _enum(value["mode"], "mask create_counts")
    _string(value["engine_version"], nullable=True, nonempty=True)
    _enum(value["input_format"], "fasta")
    _enum(value["output_format"], "interval fasta ascii_statistics")
    _enum(value["masking_style"], "soft hard interval not_applicable")
    _boolean(value["parse_seqids"])
    specs = PARAMETERS.get((value["program"], value["mode"]))
    _require(specs is not None, "unsupported_program_mode")
    _object(value["requested_parameters"], " ".join(specs))
    for name, (kind, low, high) in specs.items():
        item = value["requested_parameters"][name]
        if item is None:
            continue
        if kind == "integer":
            _integer(item, low, high)
        elif kind == "number":
            _number(item, low, high)
        elif kind == "boolean":
            _boolean(item)
        else:
            _string(item)
            _require("\x00" not in item, "parameter_nul")
    if value["mode"] == "create_counts":
        _require(value["output_format"] == "ascii_statistics" and
                 value["masking_style"] == "not_applicable" and not value["parse_seqids"], "mode_format")
    elif value["output_format"] == "interval":
        _require(value["masking_style"] == "interval", "mode_format")
    else:
        _require(value["output_format"] == "fasta" and
                 (value["masking_style"] == "soft" or
                  value["masking_style"] == "hard" and value["program"] == "dustmasker"), "mode_format")


def _input_record(value):
    _object(value, "record_key occurrence record_ordinal byte_offset native_header molecule original_sequence normalized_sequence length checks failures")
    _occurrence(value["occurrence"])
    _require(value["occurrence"]["direction"] == "input" and
             value["occurrence"]["role"] in ("sequences", "reference_sequences"), "input_occurrence")
    _integer(value["record_ordinal"])
    _integer(value["byte_offset"])
    _require(value["byte_offset"] < value["occurrence"]["size_bytes"], "input_locator")
    _require(value["record_key"] == value["occurrence"]["occurrence_id"] +
             "#/records/" + str(value["record_ordinal"]), "record_identity")
    _string(value["native_header"])
    _enum(value["molecule"], "dna protein")
    _string(value["original_sequence"])
    _string(value["normalized_sequence"])
    _require(value["normalized_sequence"] == value["original_sequence"].upper(), "sequence_normalization")
    _require(not any(c.isspace() for c in value["original_sequence"]), "sequence_layout")
    _integer(value["length"], nullable=True)
    _diagnostics(value)
    for row in value["checks"]:
        _require(row["record_key"] == value["record_key"], "input_diagnostic_identity")
    for row in value["failures"]:
        _require(row["record_key"] == value["record_key"] and
                 row["occurrence_id"] == value["occurrence"]["occurrence_id"] and
                 row["stage"] == "input", "input_diagnostic_identity")
    if value["length"] is None:
        _require(bool(value["failures"]), "invalid_input_without_reason")
    else:
        _require(value["length"] == len(value["normalized_sequence"]) and
                 set(value["normalized_sequence"]) <= ALPHABETS[value["molecule"]], "input_length_substrate")
        _require(value["native_header"].strip() and
                 all(r["code"] == "empty_sequence" and value["length"] == 0 for r in value["failures"]),
                 "input_validity_length_conflict")


def _input_parse(value):
    _object(value, "version occurrence records checks failures")
    _enum(value["version"], "sequence_masking_input_v1")
    _occurrence(value["occurrence"])
    _list(value["records"], _input_record)
    _unique([r["record_key"] for r in value["records"]])
    for record in value["records"]:
        _require(record["occurrence"] == value["occurrence"], "input_occurrence")
    _diagnostics(value)


def _custody(value):
    _object(value, "producer_kind sequence_order order_basis output_complete native_returncode record_bindings")
    _enum(value["producer_kind"], "authenticated_native supplied_artifact")
    _list(value["sequence_order"], lambda x: _string(x, nonempty=True))
    _unique(value["sequence_order"])
    _enum(value["order_basis"], "native_fasta_iteration caller_declared unknown")
    _boolean(value["output_complete"])
    _integer(value["native_returncode"], None, nullable=True)
    def binding(row):
        _object(row, "output_record_ordinal input_record_key basis")
        _integer(row["output_record_ordinal"])
        _string(row["input_record_key"], nonempty=True)
        _enum(row["basis"], "native_fasta_iteration caller_declared")
        _require(row["input_record_key"] in value["sequence_order"], "binding_input_reference")
        if row["basis"] == "native_fasta_iteration":
            _require(value["producer_kind"] == "authenticated_native", "unauthenticated_native_basis")
    _list(value["record_bindings"], binding)
    _unique([r["output_record_ordinal"] for r in value["record_bindings"]])
    _unique([r["input_record_key"] for r in value["record_bindings"]])
    if value["order_basis"] == "native_fasta_iteration":
        _require(value["producer_kind"] == "authenticated_native", "unauthenticated_native_basis")


def _pair(value):
    _require(type(value) is list and len(value) == 2, "interval_shape")
    _integer(value[0]); _integer(value[1])
    _require(value[0] < value[1], "interval_bounds")


def _mask_runs(flags):
    """Single extraction helper for native sequence runs and schema consistency.

    This only extracts runs; shared-union cardinality remains in the calculator.
    """
    intervals, start = [], None
    for position, masked in enumerate(flags):
        if masked and start is None:
            start = position
        elif not masked and start is not None:
            intervals.append([start, position]); start = None
    if start is not None:
        intervals.append([start, len(flags)])
    return intervals


def _mask_record(value):
    _object(value, "output_record_ordinal input_record_key native_header output_locator native_intervals intervals_half_open output_sequence association completeness measurement failures")
    _integer(value["output_record_ordinal"])
    _string(value["input_record_key"], nullable=True, nonempty=True)
    _string(value["native_header"])
    loc = value["output_locator"]
    _object(loc, "byte_offset line_start line_end")
    _integer(loc["byte_offset"]); _integer(loc["line_start"], 1); _integer(loc["line_end"], 1)
    _require(loc["line_end"] >= loc["line_start"], "output_locator")
    def interval(row):
        _object(row, "start end_inclusive line_number")
        _integer(row["start"]); _integer(row["end_inclusive"]); _integer(row["line_number"], 1)
        _require(loc["line_start"] <= row["line_number"] <= loc["line_end"], "interval_locator")
    _list(value["native_intervals"], interval)
    _list(value["intervals_half_open"], _pair)
    _string(value["output_sequence"], nullable=True)
    _enum(value["association"], "authenticated_native_order caller_declared unresolved")
    _require((value["input_record_key"] is None) == (value["association"] == "unresolved"), "mask_association")
    _enum(value["completeness"], "complete partial unknown")
    _enum(value["measurement"], "exact_mask hard_mask_ambiguous unavailable")
    _list(value["failures"], _failure)
    if value["measurement"] != "unavailable":
        _require(value["input_record_key"] is not None and value["completeness"] == "complete", "measurement_custody")
    if value["measurement"] == "exact_mask":
        _require(not value["failures"], "exact_measurement_failures")


def _parsed(value):
    _object(value, "version format occurrence custody records unassigned_records checks failures")
    _enum(value["version"], "sequence_masking_parsed_output_v1")
    _enum(value["format"], "interval fasta")
    _occurrence(value["occurrence"])
    _require(value["occurrence"]["role"] == "mask", "output_occurrence")
    _custody(value["custody"])
    _list(value["records"], _mask_record)
    _list(value["unassigned_records"], _mask_record)
    all_records = value["records"] + value["unassigned_records"]
    _unique([r["output_record_ordinal"] for r in all_records])
    _unique([r["input_record_key"] for r in value["records"]])
    bindings = {r["output_record_ordinal"]: r for r in value["custody"]["record_bindings"]}
    for r in all_records:
        _require(r["output_locator"]["byte_offset"] < value["occurrence"]["size_bytes"], "output_locator")
        if value["format"] == "interval":
            _require(r["output_sequence"] is None, "interval_output_sequence")
        else:
            _require(r["output_sequence"] is not None and not r["native_intervals"], "fasta_output_rows")
    for r in value["records"]:
        key, ordinal = r["input_record_key"], r["output_record_ordinal"]
        _require(key in value["custody"]["sequence_order"], "mask_input_reference")
        if ordinal in bindings:
            b = bindings[ordinal]
            _require(b["input_record_key"] == key, "mask_binding_reference")
            expected = "authenticated_native_order" if b["basis"] == "native_fasta_iteration" else "caller_declared"
            _require(r["association"] == expected, "mask_binding_basis")
        else:
            c = value["custody"]
            _require(c["producer_kind"] == "authenticated_native" and
                     c["order_basis"] == "native_fasta_iteration" and c["output_complete"] and
                     c["native_returncode"] == 0 and value["occurrence"]["completeness"] == "complete" and
                     len(all_records) == len(c["sequence_order"]) and ordinal < len(c["sequence_order"]) and
                     c["sequence_order"][ordinal] == key and r["association"] == "authenticated_native_order",
                     "unproved_mask_association")
    for r in value["unassigned_records"]:
        _require(r["input_record_key"] is None, "unassigned_record_binding")
    _diagnostics(value)


def _outcome(value):
    _object(value, "returncode state output_complete")
    _integer(value["returncode"], None, nullable=True)
    _enum(value["state"], "succeeded failed incomplete unknown")
    _boolean(value["output_complete"])
    if value["state"] == "succeeded":
        _require(value["returncode"] == 0, "native_outcome")
    if value["state"] == "failed":
        _require(value["returncode"] is None or value["returncode"] != 0, "native_outcome")
    if value["state"] == "incomplete":
        _require(not value["output_complete"], "native_outcome")


def _statistics_binding(value):
    _object(value, "kind statistics_occurrence_id reference_occurrence_ids producer_source_ref producer_attempt_id provenance")
    _enum(value["kind"], "generated supplied")
    _string(value["statistics_occurrence_id"], nonempty=True)
    _list(value["reference_occurrence_ids"], lambda x: _string(x, nonempty=True))
    _unique(value["reference_occurrence_ids"])
    for k in ("producer_source_ref", "producer_attempt_id"):
        _string(value[k], nullable=True, nonempty=True)
    _enum(value["provenance"], "authenticated_generation caller_declared unknown")
    if value["kind"] == "generated":
        _require(bool(value["reference_occurrence_ids"]) and value["producer_attempt_id"] is not None,
                 "statistics_generation_provenance")
    if value["provenance"] == "authenticated_generation":
        _require(value["kind"] == "generated", "statistics_generation_provenance")


def _statistics(value):
    _object(value, "version occurrence format reference_binding format_version algorithm_version unit_length metadata_lines unit_counts thresholds percentiles checks failures")
    _enum(value["version"], "windowmasker_statistics_v1")
    _occurrence(value["occurrence"])
    _require(value["occurrence"]["role"] == "statistics", "statistics_occurrence")
    _enum(value["format"], "ascii_statistics")
    if value["reference_binding"] is not None:
        _statistics_binding(value["reference_binding"])
        _require(value["reference_binding"]["statistics_occurrence_id"] == value["occurrence"]["occurrence_id"],
                 "statistics_occurrence_reference")
    for k in ("format_version", "algorithm_version"):
        _string(value[k], nullable=True, nonempty=True)
    _integer(value["unit_length"], 1, 16, nullable=True)
    def metadata(row):
        _object(row, "line_number text"); _integer(row["line_number"], 1); _string(row["text"])
    _list(value["metadata_lines"], metadata)
    def unit(row):
        _object(row, "line_number unit_code_hex unit_code native_count")
        _integer(row["line_number"], 1); _integer(row["unit_code"]); _integer(row["native_count"])
        _string(row["unit_code_hex"], nonempty=True)
        _require(re.fullmatch(r"[0-9a-fA-F]+", row["unit_code_hex"]) is not None and
                 int(row["unit_code_hex"], 16) == row["unit_code"], "unit_code_lexeme")
    _list(value["unit_counts"], unit)
    _object(value["thresholds"], "t_low t_extend t_threshold t_high")
    for n in value["thresholds"].values():
        _integer(n, None, nullable=True)
    def percentile(row):
        _object(row, "line_number count percentage percentage_lexeme")
        _integer(row["line_number"], 1); _integer(row["count"]); _number(row["percentage"])
        _string(row["percentage_lexeme"], nonempty=True)
        try:
            parsed = float(row["percentage_lexeme"])
        except ValueError as exc:
            raise ContractError("sequence_masking_percentage_lexeme") from exc
        _require(parsed == row["percentage"], "percentage_lexeme")
    _list(value["percentiles"], percentile)
    _diagnostics(value)


def _sheet(value):
    _object(value, "version operation inputs parsed_output statistics native_outcome checks failures")
    _enum(value["version"], "sequence_masking_sheet_v1")
    _operation(value["operation"])
    _require(value["operation"]["mode"] == "mask", "sheet_mode")
    _list(value["inputs"], _input_record)
    _unique([r["record_key"] for r in value["inputs"]])
    _parsed(value["parsed_output"])
    _require(value["parsed_output"]["format"] == value["operation"]["output_format"], "sheet_format")
    inputs = {r["record_key"]: r for r in value["inputs"]}
    _require(set(inputs) == set(value["parsed_output"]["custody"]["sequence_order"]), "sheet_input_population")
    for row in value["parsed_output"]["records"]:
        source = inputs[row["input_record_key"]]
        if row["measurement"] in ("exact_mask", "hard_mask_ambiguous"):
            expected_molecule = "protein" if value["operation"]["program"] == "segmasker" else "dna"
            _require(source["molecule"] == expected_molecule and source["length"] is not None and
                     all(b <= source["length"] for a, b in
                     row["intervals_half_open"]), "exact_mask_substrate")
            if value["parsed_output"]["format"] == "interval":
                _require(all(r["start"] <= r["end_inclusive"] < source["length"] for r in row["native_intervals"]) and
                         row["intervals_half_open"] == [[r["start"], r["end_inclusive"] + 1]
                            for r in row["native_intervals"]], "native_interval_relationship")
            else:
                output = row["output_sequence"]
                normalized, original = output.upper(), source["normalized_sequence"]
                _require(len(output) == source["length"] and set(normalized) <= ALPHABETS[expected_molecule],
                         "native_sequence_substrate")
                if value["operation"]["masking_style"] == "soft":
                    _require(normalized == original and row["intervals_half_open"] ==
                             _mask_runs([c.islower() for c in output]), "native_soft_mask_relationship")
                else:
                    _require(all(a == b or b == "N" for a, b in zip(original, normalized)) and
                             row["intervals_half_open"] == _mask_runs([a != b and b == "N"
                                 for a, b in zip(original, normalized)]), "native_hard_mask_relationship")
                    expected = "hard_mask_ambiguous" if "N" in original else "exact_mask"
                    _require(row["measurement"] == expected, "native_hard_mask_ambiguity")
        if row["measurement"] == "hard_mask_ambiguous":
            _require(value["operation"]["masking_style"] == "hard", "hard_mask_style")
    if value["statistics"] is not None:
        _statistics(value["statistics"])
        _require(value["operation"]["program"] == "windowmasker", "unexpected_statistics")
    _outcome(value["native_outcome"])
    c = value["parsed_output"]["custody"]
    _require(c["native_returncode"] == value["native_outcome"]["returncode"] and
             c["output_complete"] == value["native_outcome"]["output_complete"], "outcome_custody_conflict")
    _diagnostics(value)
    for record in value["inputs"]:
        _require(all(row in value["failures"] for row in record["failures"]) and
                 all(row in value["checks"] for row in record["checks"]), "lost_input_diagnostics")
    for record in (value["parsed_output"], value["statistics"]):
        if record is not None:
            _require(all(row in value["failures"] for row in record["failures"]) and
                     all(row in value["checks"] for row in record["checks"]), "lost_output_diagnostics")


def _count(value):
    _object(value, "value unit missing_reason")
    _integer(value["value"], nullable=True)
    _enum(value["unit"], "nt aa intervals records")
    _string(value["missing_reason"], nullable=True, machine=True)
    _require((value["value"] is None) == (value["missing_reason"] is not None), "count_missing_reason")


def _fraction(value):
    _object(value, "numerator denominator value missing_reason")
    _integer(value["numerator"], nullable=True); _integer(value["denominator"], nullable=True)
    _number(value["value"], 0, 1, nullable=True)
    _string(value["missing_reason"], nullable=True, machine=True)
    _require((value["value"] is None) == (value["missing_reason"] is not None), "fraction_missing_reason")
    if value["value"] is not None:
        _require(value["numerator"] is not None and value["denominator"] not in (None, 0) and
                 value["numerator"] <= value["denominator"], "fraction_population")


def _record_components(value):
    _object(value, "record_key unit input_length native_interval_count merged_interval_count merged_intervals_half_open masked_positions unmasked_positions masked_fraction changed_positions checks failures")
    _string(value["record_key"], nonempty=True)
    _enum(value["unit"], "nt aa")
    for k in ("input_length", "native_interval_count", "merged_interval_count", "masked_positions", "unmasked_positions", "changed_positions"):
        _count(value[k])
        expected = "intervals" if k in ("native_interval_count", "merged_interval_count") else value["unit"]
        _require(value[k]["unit"] == expected, "component_unit")
    if value["merged_intervals_half_open"] is not None:
        _list(value["merged_intervals_half_open"], _pair)
    _fraction(value["masked_fraction"])
    _require(value["masked_fraction"]["numerator"] == value["masked_positions"]["value"] and
             value["masked_fraction"]["denominator"] == value["input_length"]["value"], "component_population")
    _diagnostics(value)


def _components(value):
    _object(value, "version analysis records checks failures")
    _enum(value["version"], "sequence_masking_components_v1")
    _enum(value["analysis"], "sequence_masking_preparation")
    _list(value["records"], _record_components)
    _unique([r["record_key"] for r in value["records"]])
    _diagnostics(value)


_VALIDATORS = {"Operation": _operation, "Occurrence": _occurrence, "InputRecord": _input_record,
    "Custody": _custody, "ParsedMaskOutput": _parsed, "SequenceMaskingSheet": _sheet,
    "SequenceMaskingComponents": _components, "StatisticsBinding": _statistics_binding,
    "WindowMaskerStatistics": _statistics, "NativeOutcome": _outcome, "InputParse": _input_parse,
    "Count": _count, "Fraction": _fraction, "RecordComponents": _record_components,
    "Failure": _failure, "Check": _check}


def validate_sequence_masking_record(kind: str, value: dict) -> dict:
    """Validate a closed typed value and return an independent finite JSON copy."""
    _require(type(kind) is str and kind in _VALIDATORS, "unknown_record_kind")
    _VALIDATORS[kind](value)
    return deepcopy(value)


def sequence_masking_operation_schema(*, program: str, mode: str) -> dict:
    """Expose the same closed parameter authority to invocation/tool schemas."""
    _require(type(program) is str and type(mode) is str and
             (program, mode) in PARAMETERS, "unsupported_program_mode")
    parameters = {}
    for name, (kind, low, high) in PARAMETERS[(program, mode)].items():
        field = {"type": ["string" if kind == "text" else kind, "null"]}
        if low is not None:
            field["minimum"] = low
        if high is not None:
            field["maximum"] = high
        if kind == "text":
            field["pattern"] = r"^[^\u0000]*$"
        parameters[name] = field
    properties = {
        "version": {"type": "string", "const": "sequence_masking_operation_v1"},
        "program": {"type": "string", "const": program},
        "mode": {"type": "string", "const": mode},
        "engine_version": {"type": ["string", "null"], "minLength": 1, "pattern": r"\S"},
        "input_format": {"type": "string", "const": "fasta"},
        "output_format": {"type": "string"}, "masking_style": {"type": "string"},
        "parse_seqids": {"type": "boolean"},
        "requested_parameters": {"type": "object", "properties": parameters,
            "required": list(parameters), "additionalProperties": False}}
    if mode == "create_counts":
        properties["output_format"]["const"] = "ascii_statistics"
        properties["masking_style"]["const"] = "not_applicable"
        properties["parse_seqids"]["const"] = False
        alternatives = None
    else:
        properties["output_format"]["enum"] = ["interval", "fasta"]
        properties["masking_style"]["enum"] = ["interval", "soft"] + (["hard"] if program == "dustmasker" else [])
        alternatives = [
            {"properties": {"output_format": {"const": "interval"}, "masking_style": {"const": "interval"}}},
            {"properties": {"output_format": {"const": "fasta"},
                "masking_style": {"enum": ["soft", "hard"] if program == "dustmasker" else ["soft"]}}}]
    result = {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}
    if alternatives is not None:
        result["oneOf"] = alternatives
    return result
