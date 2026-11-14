"""Pure selection of saved masking preparation facts, without numerical work.

Native measurements and their missing reasons come from the shared masking
sheet/components or the separate WindowMasker statistics reader. References are
custody operands; returning a quantity never implicitly grants an input file.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .domain import ContractError
from .native_blast_contracts import finite_json_copy
from .sequence_masking_contracts import sequence_masking_molecule, validate_sequence_masking_record as core


PREFIX = "native_blast_masking_"
QUANTITIES = ("input_length", "native_interval_count", "merged_interval_count",
              "masked_positions", "unmasked_positions", "changed_positions", "masked_fraction")
STATISTICS_FIELDS = ("format_version", "algorithm_version", "unit_length", "thresholds", "percentiles")
SAVED_SCHEMAS = {"sheet": "sequence_masking_sheet_v1", "calculations": "sequence_masking_components_v1",
                 "parsed_statistics": "windowmasker_statistics_v1"}
IDENTIFIER_NAMESPACES = tuple(PREFIX + name for name in ("record", "occurrence", "statistics"))
_STR = {"type": "string", "minLength": 1}
_NULL_STR = {"type": ["string", "null"], "minLength": 1}
_MACHINE = {"type": "string", "pattern": r"^[a-z][a-z0-9_]*$"}
_NULL_MACHINE = {"anyOf": [_MACHINE, {"type": "null"}]}
_UINT = {"type": "integer", "minimum": 0}
_NULL_UINT = {"type": ["integer", "null"], "minimum": 0}
_SOURCE = {**_STR, "format": "reference", "x-reference-namespace": "execution_result"}
_ARTIFACT = {**_STR, "format": "reference", "x-reference-namespace": "artifact"}
_RECORD = {**_STR, "format": "reference", "x-reference-namespace": PREFIX + "record"}
_OCCURRENCE = {**_STR, "format": "reference", "x-reference-namespace": PREFIX + "occurrence"}


def _object(properties, *, required=None):
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required, "additionalProperties": False}


def _array(items, *, unique=False):
    return {"type": "array", "items": items, **({"uniqueItems": True} if unique else {})}


COUNT_SCHEMA = _object({"value": _NULL_UINT, "unit": {"enum": ["nt", "aa", "intervals", "records"]},
                        "missing_reason": _NULL_MACHINE})
FRACTION_SCHEMA = _object({"numerator": _NULL_UINT, "denominator": _NULL_UINT,
    "value": {"type": ["number", "null"], "minimum": 0, "maximum": 1}, "missing_reason": _NULL_MACHINE})
STATUS_SCHEMA = _object({"source_ref": _SOURCE,
    "state": {"enum": ["complete", "partial", "failed", "unavailable"]},
    "native_state": {"enum": ["succeeded", "failed", "incomplete", "unknown"]}, "output_complete": {"type": "boolean"}})
ARTIFACT_SCHEMA = _object({"occurrence_id": _OCCURRENCE, "direction": {"enum": ["input", "output"]},
    "role": {"enum": ["sequences", "reference_sequences", "statistics", "mask", "stdout", "stderr"]},
    "ordinal": _UINT, "artifact_ref": _ARTIFACT, "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "size_bytes": _UINT, "completeness": {"enum": ["complete", "partial", "unknown"]}})
QUANTITY_SCHEMA = _object({"source_ref": _SOURCE, "record_key": _RECORD,
    "quantity": {"enum": list(QUANTITIES)}, "value": {"oneOf": [COUNT_SCHEMA, FRACTION_SCHEMA]}})
CHECK_SCHEMA = _object({"source_ref": _SOURCE, "name": _MACHINE,
    "status": {"enum": ["pass", "fail", "unknown", "not_applicable"]},
    "record_key": {"anyOf": [_RECORD, {"type": "null"}]}, "reason": _NULL_MACHINE})
FAILURE_SCHEMA = _object({"source_ref": _SOURCE,
    "stage": {"enum": ["input", "parse", "association", "native", "statistics", "calculation", "custody"]},
    "code": _MACHINE, "occurrence_id": _NULL_STR, "record_key": _NULL_STR,
    "line_number": {"type": ["integer", "null"], "minimum": 1}})
_BINDING_SCHEMA = _object({"kind": {"enum": ["generated", "supplied"]},
    "statistics_occurrence_id": _STR, "reference_occurrence_ids": _array(_STR, unique=True),
    "producer_source_ref": _NULL_STR, "producer_attempt_id": _NULL_STR,
    "provenance": {"enum": ["authenticated_generation", "caller_declared", "unknown"]}})
_UNIT_SCHEMA = _object({"line_number": {"type": "integer", "minimum": 1},
    "unit_code_hex": {"type": "string", "pattern": "^[0-9a-fA-F]+$"}, "unit_code": _UINT, "native_count": _UINT})
_PERCENTILE_SCHEMA = _object({"line_number": {"type": "integer", "minimum": 1}, "count": _UINT,
    "percentage": {"type": "number"}, "percentage_lexeme": _STR})
_STAT_FIELDS = {"format_version": _NULL_STR, "algorithm_version": _NULL_STR,
    "unit_length": {"type": ["integer", "null"], "minimum": 1, "maximum": 16},
    "thresholds": _object({k: {"type": ["integer", "null"]} for k in ("t_low", "t_extend", "t_threshold", "t_high")}),
    "percentiles": _array(_PERCENTILE_SCHEMA)}
STATISTICS_SCHEMA = _object({"source_ref": _SOURCE,
    "statistics_ref": {**_STR, "format": "reference", "x-reference-namespace": PREFIX + "statistics"}, "occurrence_id": _STR,
    "reference_binding": {"anyOf": [_BINDING_SCHEMA, {"type": "null"}]},
    "fields": _object(_STAT_FIELDS, required=[]), "unit_counts": _array(_UNIT_SCHEMA),
    "missing_unit_codes": _array(_UINT, unique=True)})
SAVED_DATA_SCHEMA = _object({"source_ref": _SOURCE, "kind": {"enum": list(SAVED_SCHEMAS)},
    "artifact_ref": _ARTIFACT, "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "size_bytes": _UINT, "schema": {"enum": list(SAVED_SCHEMAS.values())}})
_SLOT_SCHEMA = _object({"direction": {"enum": ["input", "output"]},
    "role": ARTIFACT_SCHEMA["properties"]["role"], "ordinal": {"type": "integer", "const": 0}})
NATIVE_BLAST_MASKING_RESULT_SELECTOR_SCHEMA = _object({
    "version": {"const": PREFIX + "result_selector_v1"}, "mode": {"enum": ["native_result", "saved_recalculation"]},
    "records": {"oneOf": [_object({"mode": {"const": "all"}}), _object({"mode": {"const": "selected"},
        "entries": _array(_object({"operand_role": {"const": "sequences"},
            "operand_ordinal": {"type": "integer", "const": 0}, "record_ordinal": _UINT}), unique=True)})]},
    "quantities": _array({"enum": list(QUANTITIES)}, unique=True),
    "statistics_fields": _array({"enum": list(STATISTICS_FIELDS)}, unique=True),
    "statistics_unit_codes": _array(_UINT, unique=True), "include_checks": {"type": "boolean"},
    "artifacts": _array(_SLOT_SCHEMA, unique=True), "saved_data": _array({"enum": list(SAVED_SCHEMAS)}, unique=True),
    "saved_sheet_ref": {"anyOf": [_ARTIFACT, {"type": "null"}]}})


def _error(code):
    raise ContractError(PREFIX + code)


def _shape(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        _error("result_fields_invalid")


def _text(value):
    if type(value) is not str or not value or "\0" in value:
        _error("result_reference_invalid")


def _schema(value, schema):
    from jsonschema import Draft202012Validator
    if next(Draft202012Validator(schema).iter_errors(value), None) is not None:
        _error("result_schema_invalid")


def _list(value):
    if type(value) is not list:
        _error("result_list_required")
    return value


def _slot(row):
    return tuple(row[k] for k in ("direction", "role", "ordinal"))


def _occurrences(rows):
    values = [core("Occurrence", row) for row in _list(rows)]
    if len({_slot(r) for r in values}) != len(values) or len({r["occurrence_id"] for r in values}) != len(values):
        _error("result_occurrence_duplicate")
    return values


def validate_masking_result_selector(selector: dict, *, operation: dict) -> dict:
    operation = core("Operation", operation)
    selector = finite_json_copy(selector)
    _schema(selector, NATIVE_BLAST_MASKING_RESULT_SELECTOR_SCHEMA)
    for row in selector["records"].get("entries", []):
        if type(row["operand_ordinal"]) is not int or type(row["record_ordinal"]) is not int:
            _error("result_record_selector_invalid")
    for row in selector["artifacts"]:
        if type(row["ordinal"]) is not int:
            _error("result_artifact_selector_invalid")
    if any(type(code) is not int for code in selector["statistics_unit_codes"]):
        _error("result_statistics_selector_invalid")
    if (selector["mode"] == "native_result") != (selector["saved_sheet_ref"] is None):
        _error("result_saved_sheet_selection_invalid")
    counts = operation["mode"] == "create_counts"
    if counts and (selector["quantities"] or selector["records"].get("entries") or selector["mode"] == "saved_recalculation"):
        _error("counts_have_no_mask_quantities")
    if operation["program"] != "windowmasker" and (selector["statistics_fields"] or selector["statistics_unit_codes"]):
        _error("statistics_selection_not_applicable")
    slots = {("output", "stdout", 0), ("output", "stderr", 0)}
    slots |= ({("input", "reference_sequences", 0), ("output", "statistics", 0)} if counts else
              {("input", "sequences", 0), ("output", "mask", 0)})
    if not counts and operation["program"] == "windowmasker":
        slots.add(("input", "statistics", 0))
    if any(_slot(row) not in slots for row in selector["artifacts"]):
        _error("result_artifact_role_not_selected_operation")
    allowed_saved = set() if counts else {"sheet", "calculations"}
    if operation["program"] == "windowmasker":
        allowed_saved.add("parsed_statistics")
    if not set(selector["saved_data"]) <= allowed_saved:
        _error("result_saved_data_not_applicable")
    return selector


def masking_fact_sources() -> dict:
    entries = {"status": (STATUS_SCHEMA, "Recorded native state and selected preparation result availability."),
        "artifacts": (ARTIFACT_SCHEMA, "Only explicitly requested original artifact occurrences."),
        "quantities": (QUANTITY_SCHEMA, "Exact requested shared masking components; no function confidence."),
        "checks": (CHECK_SCHEMA, "Selected-record and relevant global saved validation checks."),
        "statistics": (STATISTICS_SCHEMA, "Requested original WindowMasker native statistics and provenance."),
        "failures": (FAILURE_SCHEMA, "Retained typed failures relevant to this selected preparation result."),
        "saved_data": (SAVED_DATA_SCHEMA, "Only explicitly requested immutable shared sheets, components or parsed statistics.")}
    result = {}
    for name, (schema, meaning) in entries.items():
        source = "execution.masking_" + name
        schema = _array(deepcopy(schema))
        result[source] = {"type": schema["type"], "meaning": meaning, "report_schema": {**schema, "x-source": source}}
    return result


FACT_SOURCES = masking_fact_sources()
PROJECTION_FIELDS = ("status", "artifacts", "quantities", "checks", "statistics", "failures", "saved_data", "record_refs")


def validate_masking_fact_values(source, values):
    """Validate typed public facts; custody and selected scope belong to the host."""
    if type(source) is not str or source not in FACT_SOURCES:
        _error("unknown_fact_source")
    values = finite_json_copy(values)
    _schema(values, FACT_SOURCES[source]["report_schema"])
    name = source.removeprefix("execution.masking_")
    for row in values:
        if name in {"checks", "failures"}:
            core("Check" if name == "checks" else "Failure", {k: v for k, v in row.items() if k != "source_ref"})
        elif name == "artifacts":
            core("Occurrence", row)
            if row["artifact_ref"] != "artifact_" + row["sha256"]:
                _error("fact_artifact_identity_conflict")
        elif name == "quantities":
            core("Fraction" if row["quantity"] == "masked_fraction" else "Count", row["value"])
            if row["quantity"] != "masked_fraction":
                units = {"intervals"} if row["quantity"] in {"native_interval_count", "merged_interval_count"} else {"nt", "aa"}
                if row["value"]["unit"] not in units:
                    _error("fact_quantity_unit_conflict")
        elif name == "saved_data":
            if (row["schema"] != SAVED_SCHEMAS[row["kind"]] or row["artifact_ref"] != "artifact_" + row["sha256"]
                    or type(row["size_bytes"]) is not int):
                _error("fact_saved_data_identity_conflict")
        elif name == "statistics":
            if row["statistics_ref"] != row["occurrence_id"] + "#/statistics":
                _error("fact_statistics_identity_conflict")
            if row["reference_binding"] is not None:
                core("StatisticsBinding", row["reference_binding"])
                if row["reference_binding"]["statistics_occurrence_id"] != row["occurrence_id"]:
                    _error("fact_statistics_binding_conflict")
            for unit in row["unit_counts"]:
                if (any(type(unit[k]) is not int for k in ("line_number", "unit_code", "native_count"))
                        or int(unit["unit_code_hex"], 16) != unit["unit_code"]):
                    _error("fact_statistics_unit_invalid")
            if any(type(v) is not int for v in row["missing_unit_codes"]) or set(row["missing_unit_codes"]) & {u["unit_code"] for u in row["unit_counts"]}:
                _error("fact_statistics_missing_unit_conflict")
            fields = row["fields"]
            if "unit_length" in fields and fields["unit_length"] is not None and type(fields["unit_length"]) is not int:
                _error("fact_statistics_unit_length_invalid")
            if "thresholds" in fields and any(v is not None and type(v) is not int for v in fields["thresholds"].values()):
                _error("fact_statistics_threshold_invalid")
            for pct in fields.get("percentiles", []):
                try:
                    parsed = float(pct["percentage_lexeme"])
                except ValueError as error:
                    raise ContractError(PREFIX + "fact_percentile_lexeme_invalid") from error
                if type(pct["line_number"]) is not int or type(pct["count"]) is not int or type(pct["percentage"]) not in (int, float) or parsed != pct["percentage"]:
                    _error("fact_percentile_value_conflict")
    return values


def failure(stage, code, occurrence_id=None, record_key=None, line_number=None):
    return core("Failure", {"stage": stage, "code": code, "occurrence_id": occurrence_id,
                            "record_key": record_key, "line_number": line_number})


def unique_failures(rows):
    result = []
    for row in _list(rows):
        row = core("Failure", row)
        if row not in result:
            result.append(row)
    return result


def _wanted_record(key, selector, occurrences):
    if selector["records"]["mode"] == "all":
        return True
    inputs = [r for r in occurrences if _slot(r) == ("input", "sequences", 0)]
    return any(key == r["occurrence_id"] + "#/records/" + str(entry["record_ordinal"])
        for r in inputs for entry in selector["records"]["entries"])


def validate_masking_projection(projection, *, source_ref, operation, selector, occurrences):
    """Check selected identities and fields only; do not calculate or reproject."""
    _text(source_ref)
    selector = validate_masking_result_selector(selector, operation=operation)
    occurrences = _occurrences(occurrences)
    projection = finite_json_copy(projection)
    _shape(projection, PROJECTION_FIELDS)
    for name in PROJECTION_FIELDS[:-1]:
        validate_masking_fact_values("execution.masking_" + name, [projection[name]] if name == "status" else projection[name])
    if projection["status"]["source_ref"] != source_ref:
        _error("projection_source_conflict")
    expected = { _slot(r): r for r in occurrences }
    chosen = [expected[_slot(r)] for r in selector["artifacts"] if _slot(r) in expected]
    kinds = []
    for row in projection["saved_data"]:
        if (row["kind"] in kinds or row["kind"] not in selector["saved_data"] or row["source_ref"] != source_ref
                or row["schema"] != SAVED_SCHEMAS[row["kind"]] or row["artifact_ref"] != "artifact_" + row["sha256"]
                or type(row["size_bytes"]) is not int):
            _error("projection_saved_data_conflict")
        kinds.append(row["kind"])
    if kinds != [kind for kind in selector["saved_data"] if kind in kinds]:
        _error("projection_saved_data_order_conflict")
    if projection["artifacts"] != chosen or projection["record_refs"] != list(dict.fromkeys(
            [source_ref, *[r["artifact_ref"] for r in chosen], *[r["artifact_ref"] for r in projection["saved_data"]]])):
        _error("projection_artifact_grant_conflict")
    seen = set()
    for row in projection["quantities"]:
        cell_kind = "Fraction" if row["quantity"] == "masked_fraction" else "Count"
        core(cell_kind, row["value"])
        key = row["record_key"], row["quantity"]
        inputs = [r for r in occurrences if r["direction"] == "input" and r["role"] == "sequences"]
        if (row["source_ref"] != source_ref or key in seen or row["quantity"] not in selector["quantities"]
                or not _wanted_record(row["record_key"], selector, occurrences)
                or not any(re.fullmatch(re.escape(r["occurrence_id"]) + r"#/records/(0|[1-9][0-9]*)", row["record_key"]) for r in inputs)):
            _error("projection_quantity_association_conflict")
        if cell_kind == "Count":
            unit = "intervals" if row["quantity"] in {"native_interval_count", "merged_interval_count"} else "aa" if sequence_masking_molecule(operation) == "protein" else "nt"
            if row["value"]["unit"] != unit:
                _error("projection_quantity_unit_conflict")
        seen.add(key)
    if projection["checks"] and not selector["include_checks"]:
        _error("projection_unrequested_checks")
    for name, kind in (("checks", "Check"), ("failures", "Failure")):
        for row in projection[name]:
            core(kind, {k: v for k, v in row.items() if k != "source_ref"})
            if row["source_ref"] != source_ref or row["record_key"] is not None and not _wanted_record(row["record_key"], selector, occurrences):
                _error("projection_diagnostic_association_conflict")
    wanted_statistics = bool(selector["statistics_fields"] or selector["statistics_unit_codes"])
    if len(projection["statistics"]) > 1 or projection["statistics"] and not wanted_statistics:
        _error("projection_statistics_population_conflict")
    for row in projection["statistics"]:
        stats = next((r for r in occurrences if r["role"] == "statistics"), None)
        if (stats is None or row["source_ref"] != source_ref or row["occurrence_id"] != stats["occurrence_id"]
                or row["statistics_ref"] != stats["occurrence_id"] + "#/statistics"
                or set(row["fields"]) != set(selector["statistics_fields"])):
            _error("projection_statistics_association_conflict")
        if row["reference_binding"] is not None:
            core("StatisticsBinding", row["reference_binding"])
            if row["reference_binding"]["statistics_occurrence_id"] != row["occurrence_id"]:
                _error("projection_statistics_binding_conflict")
        codes = {r["unit_code"] for r in row["unit_counts"]}
        if not codes <= set(selector["statistics_unit_codes"]) or row["missing_unit_codes"] != [c for c in selector["statistics_unit_codes"] if c not in codes]:
            _error("projection_statistics_selection_conflict")
        for unit in row["unit_counts"]:
            if int(unit["unit_code_hex"], 16) != unit["unit_code"]:
                _error("projection_statistics_lexeme_conflict")
    return projection


def project_masking_result(*, source_ref, operation, native_outcome, sheet, calculations,
        statistics, occurrences, selector, failures, saved_data):
    """Copy exact saved values and retain unavailable selections as typed facts."""
    _text(source_ref)
    operation, outcome = core("Operation", operation), core("NativeOutcome", native_outcome)
    selector = validate_masking_result_selector(selector, operation=operation)
    occurrences = _occurrences(occurrences)
    slots = {_slot(r): r for r in occurrences}
    problems, inputs, components, checks = unique_failures(failures), [], {}, []
    unfulfilled = False
    if sheet is not None:
        sheet = core("SequenceMaskingSheet", sheet)
        if sheet["operation"] != operation or sheet["native_outcome"] != outcome:
            _error("projection_sheet_context_conflict")
        inputs = sheet["inputs"]
        if any(slots.get(_slot(r["occurrence"])) != r["occurrence"] for r in inputs) or slots.get(_slot(sheet["parsed_output"]["occurrence"])) != sheet["parsed_output"]["occurrence"]:
            _error("projection_sheet_occurrence_conflict")
        checks += sheet["checks"]
        problems += sheet["failures"]
        if sheet["statistics"] != statistics:
            _error("projection_sheet_statistics_conflict")
    if calculations is not None:
        calculations = core("SequenceMaskingComponents", calculations)
        components = {r["record_key"]: r for r in calculations["records"]}
        if sheet is None or set(components) != {r["record_key"] for r in inputs}:
            _error("projection_component_population_conflict")
        checks += calculations["checks"]
        problems += calculations["failures"]
    if statistics is not None:
        statistics = core("WindowMaskerStatistics", statistics)
        if operation["program"] != "windowmasker" or slots.get(_slot(statistics["occurrence"])) != statistics["occurrence"]:
            _error("projection_statistics_occurrence_conflict")
        checks += statistics["checks"]
        problems += statistics["failures"]
    selected_inputs = inputs if selector["records"]["mode"] == "all" else []
    if selector["records"]["mode"] == "selected":
        by_position = {(r["occurrence"]["role"], r["occurrence"]["ordinal"], r["record_ordinal"]): r for r in inputs}
        source = slots.get(("input", "sequences", 0))
        for entry in selector["records"]["entries"]:
            row = by_position.get(tuple(entry[k] for k in ("operand_role", "operand_ordinal", "record_ordinal")))
            if row is None:
                unfulfilled = True
                oid = source["occurrence_id"] if source else None
                problems.append(failure("association", "requested_input_record_absent", oid,
                    oid + "#/records/" + str(entry["record_ordinal"]) if oid else None))
            else:
                selected_inputs.append(row)
    quantities = []
    wants_sequence_quantities = bool(selector["quantities"]) and (
        selector["records"]["mode"] == "all" or bool(selector["records"]["entries"]))
    if wants_sequence_quantities and sheet is None:
        unfulfilled = True
        problems.append(failure("calculation", "saved_masking_sheet_unavailable"))
    elif selector["quantities"] and selector["records"]["mode"] == "all" and not selected_inputs:
        unfulfilled = True
        problems.append(failure("input", "requested_input_population_unavailable"))
    for source in selected_inputs:
        key, component = source["record_key"], components.get(source["record_key"])
        if component is None and selector["quantities"]:
            unfulfilled = True
            problems.append(failure("calculation", "saved_masking_components_unavailable", source["occurrence"]["occurrence_id"], key))
            continue
        for name in selector["quantities"]:
            quantities.append({"source_ref": source_ref, "record_key": key, "quantity": name, "value": deepcopy(component[name])})
    artifacts = []
    for request in selector["artifacts"]:
        row = slots.get(_slot(request))
        if row is None:
            unfulfilled = True
            problems.append(failure("custody", "requested_artifact_unavailable"))
        else:
            artifacts.append(row)
    available_saved = {}
    for row in _list(saved_data):
        _schema(row, SAVED_DATA_SCHEMA)
        if row["source_ref"] != source_ref or row["kind"] in available_saved or row["schema"] != SAVED_SCHEMAS[row["kind"]]:
            _error("saved_data_context_conflict")
        available_saved[row["kind"]] = row
    selected_saved = []
    for kind in selector["saved_data"]:
        if kind not in available_saved:
            unfulfilled = True
            problems.append(failure("calculation", "requested_saved_" + kind + "_unavailable"))
        else:
            selected_saved.append(deepcopy(available_saved[kind]))
    stats = []
    if selector["statistics_fields"] or selector["statistics_unit_codes"]:
        if statistics is None:
            unfulfilled = True
            problems.append(failure("statistics", "requested_statistics_unavailable"))
        else:
            oid = statistics["occurrence"]["occurrence_id"]
            units = [r for r in statistics["unit_counts"] if r["unit_code"] in selector["statistics_unit_codes"]]
            stats.append({"source_ref": source_ref, "statistics_ref": oid + "#/statistics", "occurrence_id": oid,
                "reference_binding": statistics["reference_binding"],
                "fields": {name: deepcopy(statistics[name]) for name in selector["statistics_fields"]},
                "unit_counts": deepcopy(units), "missing_unit_codes": [code for code in selector["statistics_unit_codes"] if code not in {r["unit_code"] for r in units}]})
            if any(statistics[name] is None or name == "thresholds" and any(v is None for v in statistics[name].values()) for name in selector["statistics_fields"]):
                unfulfilled = True
                problems.append(failure("statistics", "requested_statistics_field_unavailable", oid))
    problems = [p for p in unique_failures(problems) if p["record_key"] is None or _wanted_record(p["record_key"], selector, occurrences)]
    selected_checks = []
    if selector["include_checks"]:
        if sheet is None and statistics is None:
            unfulfilled = True
            problems.append(failure("calculation", "requested_checks_unavailable"))
        for check in checks:
            core("Check", check)
            if (check["record_key"] is None or _wanted_record(check["record_key"], selector, occurrences)) and check not in selected_checks:
                selected_checks.append(check)
    zero_keys = {r["input_record_key"] for r in sheet["parsed_output"].get("known_zero_records", [])} if sheet is not None else set()
    unavailable = any(r["value"]["value"] is None and
        r["value"]["missing_reason"] not in {"hard_mask_ambiguous", "not_applicable"} and not (
            r["quantity"] == "native_interval_count" and r["record_key"] in zero_keys and
            r["value"]["missing_reason"] == "native_mask_record_not_emitted") for r in quantities)
    useful = bool(artifacts or quantities or stats or selected_saved)
    if not unfulfilled and not unavailable:
        state = "complete"
    elif useful:
        state = "partial"
    else:
        state = "failed" if outcome["state"] == "failed" else "unavailable"
    result = {"status": {"source_ref": source_ref, "state": state, "native_state": outcome["state"], "output_complete": outcome["output_complete"]},
        "artifacts": artifacts, "quantities": quantities, "checks": [{"source_ref": source_ref, **r} for r in selected_checks],
        "statistics": stats, "failures": [{"source_ref": source_ref, **r} for r in problems], "saved_data": selected_saved,
        "record_refs": list(dict.fromkeys([source_ref, *[r["artifact_ref"] for r in artifacts], *[r["artifact_ref"] for r in selected_saved]]))}
    return validate_masking_projection(result, source_ref=source_ref, operation=operation, selector=selector, occurrences=occurrences)
