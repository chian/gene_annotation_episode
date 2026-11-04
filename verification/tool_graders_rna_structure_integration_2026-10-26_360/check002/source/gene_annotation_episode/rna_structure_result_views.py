"""Closed RNA return shapes and exact projections of retained numerical cells.

Projection selects supplied data; it does not acquire, interpret or score science.
Failure ordinals are frozen before the selected action receipt is published.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .execution_contracts import checked, digest, obj
from .rna_structure_contracts import (CELL_STATES, COORDINATE_SYSTEM, METRIC_UNITS,
    MODES, OPERATIONS, RNA_ISSUE_CODES, RNA_SYMBOLS, ROW_METRICS, issue,
    validate_rna_issue, validate_rna_parameters, validate_rna_sheet,
    validate_rna_components)

FAMILY_METRICS = {"summary": ROW_METRICS["summary"], "pair": ROW_METRICS["pairs"],
    "stem": ROW_METRICS["stems"], "region": ROW_METRICS["regions"], "failure": ()}
FAMILY_SOURCES = {family: "execution_rna_structure_" + family + "_rows" for family in FAMILY_METRICS}
REFERENCE_SOURCE = "execution_rna_structure_result_refs"
SAVED_SOURCE = "execution_rna_structure_saved_sheet_inputs"
IDENTIFIER_NAMESPACES = ("native_rna_structure_row", "native_rna_structure_calculation",
    "native_rna_structure_result_receipt")
TEXT = {"type": "string", "minLength": 1, "pattern": "^[^\\u0000]+$"}
COUNT = {"type": "integer", "minimum": 0}
NUMBER = {"type": "number"}
SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}


def nullable(schema):
    return {"anyOf": [deepcopy(schema), {"type": "null"}]}


def reference(namespace):
    return {**TEXT, "format": "reference", "x-reference-namespace": namespace}


def identifier(namespace):
    return {**TEXT, "format": "identifier", "x-reference-namespace": namespace}


PARAMETERS_SCHEMA = obj({"schema": {"const": "rna_calculation_parameters_v1"},
    "topology": obj({"long_stem_min_pairs": {"type": "integer", "minimum": 1},
        "include_exterior_in_loop_size_statistics": {"const": False}}),
    "pair_composition": obj({"accepted_ordered_pair_types": {"type": "array", "uniqueItems": True,
        "items": {"enum": [a+b for a in "ACGU" for b in "ACGU"]}},
        "denominator": {"const": "unambiguous_pairs"}}),
    "energy": obj({"normalization": {"enum": ["none", "per_nt"]}})})
SAVED_INPUT_SCHEMA = obj({"schema": {"const": "rna_structure_saved_sheet_input_v1"},
    "result_receipt_key": identifier(IDENTIFIER_NAMESPACES[2]),
    "handoff_ref": reference("execution_handoff"), "source_ref": reference("execution_result"),
    "bundle_artifact_ref": reference("artifact"), "sheet_artifact_ref": reference("artifact"),
    "sheet_sha256": SHA, "record_key": TEXT, "operation": {"enum": list(OPERATIONS.values())},
    "mode": {"enum": list(MODES)}})
ROWS_SCHEMA = {"oneOf": [obj({"offset": COUNT, "limit": {"type": "integer", "minimum": 1}}),
    obj({"record_keys": {"type": "array", "minItems": 1, "uniqueItems": True, "items": TEXT}})]}
PROJECTION_SCHEMA = {"oneOf": [obj({"family": {"const": family}, "rows": ROWS_SCHEMA,
    "metrics": {"type": "array", "uniqueItems": True, "minItems": 0 if family == "failure" else 1,
        **({"maxItems": 0} if family == "failure" else {}), "items": {"enum": list(metrics)}
        if metrics else {"type": "string"}}}) for family, metrics in FAMILY_METRICS.items()]}
RESULT_SELECTOR_SCHEMA = {"oneOf": [obj({"version": {"const": "native_rna_structure_result_selector_v1"},
    "acquisition": {"const": "complete_bound_bundle"}, "projection": PROJECTION_SCHEMA}),
    obj({"version": {"const": "native_rna_structure_saved_sheet_selector_v1"},
        "acquisition": {"const": "retained_sheet_only"}, "saved_input": SAVED_INPUT_SCHEMA,
        "parameters": PARAMETERS_SCHEMA, "projection": PROJECTION_SCHEMA})]}
ISSUE_SCHEMA = obj({"stage": {"enum": ["input", "native", "capture", "parse", "calculate", "binding", "selection"]},
    "code": {"enum": sorted(RNA_ISSUE_CODES)}, "record_key": nullable(TEXT), "field": nullable(TEXT),
    "index": nullable(COUNT), "artifact_role": nullable({"enum": ["input", "model_parameter_input",
        "native_result", "model", "effective_parameters", "stdout", "stderr"]})})
PAIR_SCHEMA = {"type": "array", "minItems": 2, "maxItems": 2, "items": COUNT}
_ORIGINS = ["native_prediction", "native_evaluation", "derived_topology", "derived_sequence_composition"]


def validate_saved_rna_input(value):
    result = checked(value, SAVED_INPUT_SCHEMA, "rna_invalid_input_schema")
    if result["operation"] != OPERATIONS[result["mode"]] or re.fullmatch(r"rna_result_receipt:[0-9a-f]{64}", result["result_receipt_key"]) is None:
        raise ValueError("rna_input_identity_mismatch")
    return result


def validate_rna_structure_result_selector(value, *, mode):
    result = checked(value, RESULT_SELECTOR_SCHEMA, "rna_invalid_input_schema")
    if mode not in MODES:
        raise ValueError("rna_input_identity_mismatch")
    rows = result["projection"]["rows"]
    if "offset" in rows and any(type(rows[k]) is not int for k in ("offset", "limit")):
        raise ValueError("rna_invalid_input_schema")
    if "saved_input" in result:
        saved = validate_saved_rna_input(result["saved_input"])
        if saved["mode"] != mode:
            raise ValueError("rna_input_identity_mismatch")
        validate_rna_parameters(result["parameters"])
    return result


def rna_structure_row_schema(family):
    if family not in FAMILY_METRICS:
        raise ValueError("rna_invalid_input_schema")
    common = {"family": {"const": family}, "record_key": TEXT,
        "row_key": identifier(IDENTIFIER_NAMESPACES[0]), "source_ref": reference("execution_result"),
        "operation": {"enum": list(OPERATIONS.values())}, "mode": {"enum": list(MODES)}}
    if family == "failure":
        return obj({**common, "source_ref": nullable(reference("execution_result")),
            "result_receipt_key": identifier(IDENTIFIER_NAMESPACES[2]), "issue_ordinal": COUNT,
            "issue": ISSUE_SCHEMA})
    measurement = {"name": {"enum": list(FAMILY_METRICS[family])}, "unit": {"enum": sorted(set(METRIC_UNITS.values()))},
        "numerator": nullable(NUMBER), "denominator": nullable(NUMBER), "origin": {"enum": _ORIGINS}}
    common.update({"structure_key": nullable(TEXT), "subject_ref": nullable(reference("subject")),
        "sequence_id": nullable(TEXT), "structure_id": nullable(TEXT),
        "structure_origin": nullable({"enum": ["native_prediction", "supplied_unknown", "supplied_prediction", "supplied_observation"]}),
        "coordinate_system": {"const": COORDINATE_SYSTEM}, "status": {"enum": ["bound", "unbound", "partial", "invalid"]},
        "measurements": {"type": "array", "items": obj({**measurement, "value": NUMBER})},
        "unavailable": {"type": "array", "items": obj({**measurement,
            "state": {"enum": sorted(CELL_STATES - {"present"})}, "reason": {"enum": sorted(RNA_ISSUE_CODES)}})},
        "qualification_codes": {"type": "array", "uniqueItems": True, "items": {"enum": sorted(RNA_ISSUE_CODES)}},
        "calculation_key": identifier(IDENTIFIER_NAMESPACES[1]), "calculation_parameters": PARAMETERS_SCHEMA})
    if family == "pair":
        symbol = {"type": "string", "pattern": "^[" + RNA_SYMBOLS + "]$"}
        common.update(pair_key=TEXT, indices=PAIR_SCHEMA, symbol_i=nullable(symbol), symbol_j=nullable(symbol),
            ordered_pair=nullable({"type": "string", "pattern": "^[" + RNA_SYMBOLS + "]{2}$"}))
    elif family == "stem":
        common.update(stem_key=TEXT, pair_keys={"type": "array", "minItems": 1, "uniqueItems": True, "items": TEXT},
            pair_indices={"type": "array", "minItems": 1, "uniqueItems": True, "items": PAIR_SCHEMA})
    elif family == "region":
        common.update(region_key=TEXT, region_kind={"enum": ["exterior", "hairpin", "bulge", "internal", "multibranch"]},
            closing_pair_key=nullable(TEXT), immediate_branch_pair_keys={"type": "array", "uniqueItems": True, "items": TEXT},
            unpaired_intervals={"type": "array", "items": PAIR_SCHEMA})
    return obj(common)


def validate_rna_structure_row(value):
    row = checked(value, rna_structure_row_schema(value.get("family")), "rna_invalid_component_schema")
    if row["operation"] != OPERATIONS[row["mode"]]:
        raise ValueError("rna_input_identity_mismatch")
    if row["family"] == "failure":
        validate_rna_issue(row["issue"])
        if row["row_key"] != row["record_key"] + ":failure:" + str(row["issue_ordinal"]) or re.fullmatch(
                r"rna_result_receipt:[0-9a-f]{64}", row["result_receipt_key"]) is None:
            raise ValueError("rna_input_identity_mismatch")
        return row
    validate_rna_parameters(row["calculation_parameters"])
    if re.fullmatch(r"rna_calculation:[0-9a-f]{64}", row["calculation_key"]) is None or (
            row["status"] == "bound" and row["subject_ref"] is None or row["status"] == "unbound" and row["subject_ref"] is not None):
        raise ValueError("rna_invalid_component_schema")
    names = [cell["name"] for cell in row["measurements"] + row["unavailable"]]
    if len(names) != len(set(names)) or any(cell["unit"] != METRIC_UNITS[cell["name"]]
            for cell in row["measurements"] + row["unavailable"]):
        raise ValueError("rna_invalid_component_schema")
    family = row["family"]
    key = "summary" if family == "summary" else row[family + "_key"]
    if row["row_key"] != row["record_key"] + ":" + key:
        raise ValueError("rna_input_identity_mismatch")
    if row["structure_key"] not in (None, row["record_key"] + ":structure"):
        raise ValueError("rna_input_identity_mismatch")
    pairs = [row["indices"]] if family == "pair" else row["pair_indices"] if family == "stem" else []
    if any(type(i) is not int or type(j) is not int or i >= j for i, j in pairs):
        raise ValueError("rna_invalid_component_schema")
    if family == "pair" and (row["pair_key"] != "pair:%d:%d" % tuple(row["indices"]) or
            (row["symbol_i"] is None) != (row["symbol_j"] is None) or row["ordered_pair"] !=
            (None if row["symbol_i"] is None else row["symbol_i"] + row["symbol_j"])):
        raise ValueError("rna_invalid_component_schema")
    if family == "stem" and (row["pair_keys"] != ["pair:%d:%d" % tuple(pair) for pair in pairs] or
            row["stem_key"] != "stem:%d:%d" % tuple(pairs[0]) or any(
                inner != [outer[0] + 1, outer[1] - 1] for outer, inner in zip(pairs, pairs[1:]))):
        raise ValueError("rna_invalid_component_schema")
    if family == "region":
        intervals = row["unpaired_intervals"]
        pair_keys = row["immediate_branch_pair_keys"] + ([] if row["closing_pair_key"] is None else [row["closing_pair_key"]])
        if any(re.fullmatch(r"pair:(0|[1-9][0-9]*):(0|[1-9][0-9]*)", key) is None for key in pair_keys):
            raise ValueError("rna_invalid_component_schema")
        branches = [tuple(map(int, key.split(":")[1:])) for key in row["immediate_branch_pair_keys"]]
        closing = None if row["closing_pair_key"] is None else tuple(map(int, row["closing_pair_key"].split(":")[1:]))
        if (any(a >= b for a, b in intervals + [list(pair) for pair in branches] + ([] if closing is None else [list(closing)]))
                or any(left[1] >= right[0] for left, right in zip(intervals, intervals[1:]))
                or any(left[1] >= right[0] for left, right in zip(branches, branches[1:]))
                or (row["region_kind"] == "exterior") != (closing is None)
                or row["region_key"] != ("region:exterior" if closing is None else "region:%d:%d" % closing)
                or closing is not None and any(not closing[0] < a < b <= closing[1] for a, b in intervals)
                or closing is not None and any(not closing[0] < a < b < closing[1] for a, b in branches)
                or any(not (b <= c or d < a) for a, b in intervals for c, d in branches)):
            raise ValueError("rna_invalid_component_schema")
    return row


def rna_structure_fact_sources():
    result = {source: {"type": "array", "meaning": "Exactly requested original RNA quantities and specific qualifications; no annotation confidence or implied artifact access.",
        "report_schema": {"type": "array", "items": rna_structure_row_schema(family), "x-source": source}}
        for family, source in FAMILY_SOURCES.items()}
    result[REFERENCE_SOURCE] = {"type": "array", "meaning": "Requested RNA result sources only; no auxiliary bytes or unrequested numerical rows.",
        "report_schema": {"type": "array", "uniqueItems": True, "items": reference("execution_result"), "x-source": REFERENCE_SOURCE}}
    result[SAVED_SOURCE] = {"type": "array", "meaning": "Explicit original saved-sheet operands for deterministic recalculation; no new acquisition credit.",
        "report_schema": {"type": "array", "uniqueItems": True, "items": SAVED_INPUT_SCHEMA, "x-source": SAVED_SOURCE}}
    return deepcopy(result)


def merge_issues(*groups):
    result = []
    for group in groups:
        for value in group:
            value = validate_rna_issue(value)
            if value not in result:
                result.append(value)
    return result


def project_rna_prepublication(sheet, components, *, selector, components_sha256, failures=()):
    """Produce canonical row order from the complete saved family, then select."""
    sheet = validate_rna_sheet(sheet)
    components = validate_rna_components(components, sheet=sheet)
    selector = validate_rna_structure_result_selector(selector, mode=sheet["mode"])
    family, choice, metrics = (selector["projection"][key] for key in ("family", "rows", "metrics"))
    topology, structure, original = sheet["topology"], sheet["structure"] or {}, sheet["original_input"] or {}
    key = sheet["record_key"]
    rows, selection_issues = [], []
    population = None if family == "failure" or family != "summary" and (topology is None or topology["status"] != "valid") else 0
    items = [("summary", {})] if family == "summary" else []
    plural = {"pair": "pairs", "stem": "stems", "region": "regions"}.get(family)
    if population is not None and family != "summary":
        items = [(row[family + "_key"], row) for row in topology[plural]]
        if family == "region":
            items.sort(key=lambda item: (-1, -1) if item[1]["kind"] == "exterior" else tuple(map(int, item[1]["closing_pair_key"].split(":")[1:])))
    if population is not None:
        population = len(items)
    comp = {} if family in ("summary", "failure") else {row["row_key"]: row["cells"] for row in components[plural]}
    sequence_pairs = {row["pair_key"]: row for row in sheet["sequence_pairs"] or []}
    pairs = {row["pair_key"]: [row["i"], row["j"]] for row in (topology or {}).get("pairs") or []}
    for ordinal, (local_key, data) in enumerate(items):
        row_key = key + ":" + local_key
        if ("record_keys" in choice and row_key not in choice["record_keys"] or "offset" in choice and
                not choice["offset"] <= ordinal < choice["offset"] + choice["limit"]):
            continue
        cells = {cell["name"]: cell for cell in components["summary"] if family == "summary"} if family == "summary" else {cell["name"]: cell for cell in comp[local_key]}
        row = {"record_key": key, "structure_key": structure.get("structure_key"), "row_key": row_key,
            "ordinal": ordinal, "operation": sheet["operation"], "mode": sheet["mode"], "sequence_id": original.get("sequence_id"),
            "structure_id": structure.get("structure_id"), "structure_origin": structure.get("origin"),
            "coordinate_system": COORDINATE_SYSTEM, "sheet_status": sheet["status"], "family": family,
            "cells": [deepcopy(cells[metric]) for metric in metrics],
            "qualification_codes": list(dict.fromkeys(value["code"] for value in sheet["issues"]))}
        if family == "pair":
            row.update(pair_key=local_key, indices=pairs[local_key], **{field: sequence_pairs[local_key][field]
                for field in ("symbol_i", "symbol_j", "ordered_pair")})
        elif family == "stem":
            row.update(stem_key=local_key, pair_keys=data["pair_keys"], pair_indices=[pairs[p] for p in data["pair_keys"]])
        elif family == "region":
            row.update(region_key=local_key, region_kind=data["kind"], **{field: data[field]
                for field in ("closing_pair_key", "immediate_branch_pair_keys", "unpaired_intervals")})
        rows.append(row)
    if family != "failure":
        if "record_keys" in choice:
            for index, requested in enumerate(choice["record_keys"]):
                if requested not in {row["row_key"] for row in rows}:
                    selection_issues.append(issue("rna_requested_row_missing", stage="selection", record_key=key,
                        field=f"/selector/projection/rows/record_keys/{index}", index=index))
        elif population is None:
            selection_issues.append(issue("rna_requested_row_missing", stage="selection", record_key=key, field="/selector/projection/rows"))
    return {"schema": "rna_structure_prepublication_v1", "record_key": key, "operation": sheet["operation"], "mode": sheet["mode"],
        "selector": selector, "sheet_schema": sheet["schema"], "components_sha256": components_sha256,
        "parameters": deepcopy(components["parameters"]), "population_count": population, "rows": rows,
        "failures": merge_issues(failures, selection_issues), "requested_cells_accounted_for": family != "failure"}, selection_issues


def result_receipt_key(receipt):
    return "rna_result_receipt:" + digest({key: receipt[key] for key in ("run_id", "episode_id", "operation_key")})


def prepare_rna_structure_failure_selection(*, failures, selector, record_key):
    failures = [validate_rna_issue(row) for row in failures]
    if selector["projection"]["family"] != "failure":
        return {"failures": failures, "selection": None}
    choice, n = selector["projection"]["rows"], len(failures)
    keys = [record_key + ":failure:" + str(i) for i in range(n)]
    if "record_keys" in choice:
        selected = [i for i, key in enumerate(keys) if key in choice["record_keys"]]
        for i, key in enumerate(choice["record_keys"]):
            if key not in keys:
                failures.append(issue("rna_requested_row_missing", stage="selection", record_key=record_key,
                    field=f"/selector/projection/rows/record_keys/{i}", index=i))
    else:
        selected = list(range(n))[choice["offset"]:choice["offset"] + choice["limit"]]
    return {"failures": failures, "selection": {"version": "rna_structure_failure_selection_v1", "population_count": n,
        "selected_ordinals": selected, "supplemental_issue_ordinals": list(range(n, len(failures))),
        "requested_rows_accounted_for": True}}


def project_rna_structure_failure_rows(receipt, *, selector=None):
    job = receipt["target"]["assignment"]["requested_job"]["native_rna_structure"]
    if selector is None:
        ordinals = range(len(receipt["failures"]))
    else:
        if selector != receipt["assignment"]["selector"] or selector["projection"]["family"] != "failure":
            raise ValueError("rna_input_identity_mismatch")
        selection = receipt["failure_selection"]
        expected = prepare_rna_structure_failure_selection(failures=receipt["failures"][:selection["population_count"]],
            selector=selector, record_key=job["record_key"])
        if expected != {"failures": receipt["failures"], "selection": selection}:
            raise ValueError("rna_invalid_component_schema")
        ordinals = selection["selected_ordinals"] + selection["supplemental_issue_ordinals"]
    return [validate_rna_structure_row({"family": "failure", "record_key": job["record_key"],
        "row_key": job["record_key"] + ":failure:" + str(i), "source_ref": receipt["source_ref"],
        "result_receipt_key": result_receipt_key(receipt), "issue_ordinal": i,
        "operation": job["operation"], "mode": job["mode"], "issue": deepcopy(receipt["failures"][i])}) for i in ordinals]
