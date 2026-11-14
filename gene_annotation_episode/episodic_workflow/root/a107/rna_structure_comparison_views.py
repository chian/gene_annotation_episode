"""Exact parent-selected projections of retained RNA comparison components.

This module selects supplied facts. It does not calculate scientific components,
authenticate publication identities, access Store, or invoke native operations.
Publication must independently compare components to deterministic recalculation.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .rna_structure_contracts import COORDINATE_SYSTEM, _same
from .rna_structure_comparison_contracts import (
    COMPARISON_ISSUE_SCHEMA, COMPARISON_REASONS, COUNT, ENERGY_COMPARISON_SCHEMA,
    ENERGY_STATES, ID, NUMERIC_CELL_SCHEMA, PAIR, PAIR_CHANGE_SCHEMA, PAIR_METRICS,
    PAIRING_STATES, RANK_CLASSES, RNA_COMPARISON_PROJECTION_REQUEST_SCHEMA,
    SELECTOR_VERSION, SITE_CHANGE_SCHEMA, SITE_METRICS, array, checked, enum,
    nullable, obj, comparison_issue, validate_rna_comparison_components,
    validate_rna_comparison_selector, validate_rna_comparison_sheet,
)

PROJECTION_VERSION = "rna_comparison_projection_v1"
PROJECTION_SOURCE = "execution_rna_structure_comparison_projections"
IDENTIFIER_NAMESPACES = ("rna_comparison_receipt", "rna_comparison_calculation")
SITE_POPULATION_FIELDS = (
    "requested_site_count", "decidable_site_count", "deleted_site_count",
    "inserted_site_count", "unmapped_site_count", "unavailable_topology_site_count",
    "unresolved_partner_site_count",
)
PAIR_POPULATION_FIELDS = (
    "baseline_pair_count", "variant_pair_count", "baseline_mapped_pair_count",
    "variant_mapped_pair_count", "baseline_unresolved_pair_count", "variant_unresolved_pair_count",
)
SCAN_POPULATION_FIELDS = (
    "declared_variant_count", "alias_entry_count", "native_energy_available_variant_count",
    "comparable_variant_count", "received_failure_variant_count", "not_supplied_variant_count",
    "not_tested_variant_count", "sheet_energy_unavailable_variant_count",
    "model_incompatible_variant_count", "model_unknown_variant_count", "rank_population_count",
)
_NULLABLE_SCAN_COUNTS = frozenset(("comparable_variant_count", "model_incompatible_variant_count",
    "model_unknown_variant_count", "rank_population_count"))
_MEMBER_CELL_FIELDS = {"energy": "energy", "delta": "delta",
    "rank_start": "exact_rank_start", "rank_end": "exact_rank_end"}
_REQUESTS = {branch["properties"]["family"]["const"]: branch
    for branch in RNA_COMPARISON_PROJECTION_REQUEST_SCHEMA["oneOf"]}


def _publication_identifier(namespace):
    return {"type": "string", "pattern": "^" + namespace + ":[0-9a-f]{64}$",
        "format": "identifier", "x-reference-namespace": namespace}


_REASON = nullable(enum(sorted(COMPARISON_REASONS)))
_STRING_VALUE = nullable({"type": "string"})
RETURNED_NUMERIC_CELL_SCHEMA = obj({key: deepcopy(value)
    for key, value in NUMERIC_CELL_SCHEMA["properties"].items() if key != "input_paths"})
RETURNED_SITE_CHANGE_SCHEMA = obj({key: deepcopy(RETURNED_NUMERIC_CELL_SCHEMA if key == "change_indicator" else value)
    for key, value in SITE_CHANGE_SCHEMA["properties"].items()})
STRUCTURE_VALUE_SCHEMA = {"oneOf": [obj({"field": {"const": name},
    "state": enum(("present", "missing_input", "invalid_input")),
    "value": nullable(array(PAIR)) if name == "pairs" else _STRING_VALUE,
    "reason": _REASON}) for name in
    _REQUESTS["structures"]["properties"]["fields"]["items"]["enum"]]}
SELECTED_MEMBER_VALUE_SCHEMA = {"oneOf": [
    obj({"field": enum(_MEMBER_CELL_FIELDS), "cell": RETURNED_NUMERIC_CELL_SCHEMA}),
    obj({"field": {"const": "eligibility"}, "state": enum(ENERGY_STATES)}),
]}
PROJECTION_QUALIFICATION_SCHEMA = obj({
    "codes": array(enum(sorted(COMPARISON_REASONS)), unique=True),
    "domain": enum(("pairwise", "selected_sites", "declared_scan")),
    "baseline_member_id": ID, "member_ids": array(ID, unique=True),
    # Addendum005: unavailable retained counts stay null, never invented zeros.
    "site_populations": array(obj({"comparison_id": ID, "selection_id": ID,
        **{field: nullable(COUNT) for field in SITE_POPULATION_FIELDS}})),
    "pair_populations": array(obj({"comparison_id": ID,
        **{field: nullable(COUNT) for field in PAIR_POPULATION_FIELDS}})),
    "population": nullable(obj({field: nullable(COUNT) if field in _NULLABLE_SCAN_COUNTS else COUNT
        for field in SCAN_POPULATION_FIELDS})),
    "issues": array(COMPARISON_ISSUE_SCHEMA),
})
_ENERGY_PROPERTIES = ENERGY_COMPARISON_SCHEMA["properties"]
_PAYLOADS = {
    "energy_comparison": obj({"rows": array(obj({"comparison_id": ID,
        "baseline_member_id": ID, "variant_member_id": ID,
        "energy_kind": _ENERGY_PROPERTIES["request"]["properties"]["quantity"],
        "normalization": _ENERGY_PROPERTIES["request"]["properties"]["normalization"],
        "measurements": array(RETURNED_NUMERIC_CELL_SCHEMA), "order": nullable(_ENERGY_PROPERTIES["order"]),
        "tolerance_band": nullable(_ENERGY_PROPERTIES["baseline_tolerance_band"]),
        "compatibility_state": _ENERGY_PROPERTIES["compatibility"]["properties"]["state"]}))}),
    "structures": obj({"rows": array(obj({"member_id": ID,
        "coordinate_system": {"const": COORDINATE_SYSTEM},
        "structure_origin": nullable(enum(("native_prediction", "supplied_unknown", "supplied_prediction", "supplied_observation"))),
        "values": array(STRUCTURE_VALUE_SCHEMA), "issues": array(COMPARISON_ISSUE_SCHEMA)}))}),
    "position_changes": obj({"comparison_id": ID, "selection_id": ID, "rows": array(RETURNED_SITE_CHANGE_SCHEMA)}),
    "pair_changes": obj({"rows": array(obj({"comparison_id": ID, "change": PAIR_CHANGE_SCHEMA}))}),
    "comparison_counts": obj({"rows": array(obj({"comparison_id": ID, "selection_id": nullable(ID),
        "measurements": array(RETURNED_NUMERIC_CELL_SCHEMA), "pairing_change_state": nullable(enum(PAIRING_STATES))}))}),
    "scan_energy": obj({"scan_id": ID, "measurements": array(RETURNED_NUMERIC_CELL_SCHEMA),
        "rank_class": nullable(enum(RANK_CLASSES))}),
    "scan_sites": obj({"scan_id": ID, "rows": array(obj({"selection_id": ID, "baseline_index": COUNT,
        "measurements": array(RETURNED_NUMERIC_CELL_SCHEMA)}))}),
    "scan_members": obj({"scan_id": ID, "matched_count": COUNT, "returned_count": COUNT,
        "omitted_count": COUNT, "rows": array(obj({"member_id": ID, "canonical_member_id": ID,
            "values": array(SELECTED_MEMBER_VALUE_SCHEMA)}))}),
}
RNA_COMPARISON_PROJECTION_RESULT_SCHEMA = {"oneOf": [obj({
    "schema": {"const": PROJECTION_VERSION}, "projection_id": ID, "family": {"const": family},
    "result_receipt_key": _publication_identifier(IDENTIFIER_NAMESPACES[0]),
    "calculation_key": _publication_identifier(IDENTIFIER_NAMESPACES[1]),
    "population_id": nullable(ID), "selection": _REQUESTS[family],
    "delivery": enum(("values", "qualified_unavailability", "empty_selected_set")),
    "payload": payload, "qualification": PROJECTION_QUALIFICATION_SCHEMA,
}) for family, payload in _PAYLOADS.items()]}


def rna_comparison_fact_sources() -> dict:
    """Return the one exact source schema; registration is a host responsibility."""
    return deepcopy({PROJECTION_SOURCE: {"type": "array",
        "meaning": "Exactly selected retained RNA comparison facts and required population qualifications; no implied native acquisition or annotation confidence.",
        "report_schema": {"type": "array", "items": RNA_COMPARISON_PROJECTION_RESULT_SCHEMA,
            "x-source": PROJECTION_SOURCE}}})


def _require(condition):
    if not condition:
        raise ValueError("projection_mismatch")


def _context(sheet, components, projections, result_receipt_key, calculation_key):
    for value, namespace in ((result_receipt_key, IDENTIFIER_NAMESPACES[0]),
            (calculation_key, IDENTIFIER_NAMESPACES[1])):
        _require(type(value) is str and re.fullmatch(namespace + r":[0-9a-f]{64}", value) is not None)
    sheet = validate_rna_comparison_sheet(sheet)
    components = validate_rna_comparison_components(components, sheet=sheet)
    selection = validate_rna_comparison_selector({"version": SELECTOR_VERSION,
        "acquisition": "retained_inputs_only", "question": sheet["selected_question"],
        "parameters": sheet["parameters"], "projections": projections})
    return sheet, components, selection["projections"]


def _cells(rows, selection_id=None):
    return {c["metric"]: c for c in rows if c["selection_id"] == selection_id}


def _selected_cells(rows, metrics, selection_id=None):
    cells = _cells(rows, selection_id)
    _require(all(metric in cells for metric in metrics))
    return [_returned_cell(cells[metric]) for metric in metrics]


def _returned_cell(cell):
    """Keep exact numerical meaning; complete source paths stay retained (006)."""
    return {field: deepcopy(cell[field]) for field in RETURNED_NUMERIC_CELL_SCHEMA["properties"]}


def _unique(values):
    result = []
    for value in values:
        if value not in result:
            result.append(deepcopy(value))
    return result


def _numeric_cells(value):
    if type(value) is dict:
        if set(value) == set(RETURNED_NUMERIC_CELL_SCHEMA["properties"]):
            yield value
        else:
            for child in value.values():
                yield from _numeric_cells(child)
    elif type(value) is list:
        for child in value:
            yield from _numeric_cells(child)


def _structure_value(operand, field):
    original = operand["original_sheet"]
    state, reason, value = "present", None, None
    if original is None:
        state = "missing_input"
        reason = operand["state"] if operand["state"] in ("received_failure", "not_supplied", "not_tested") else "original_structure_unavailable"
    elif field in ("original_sequence", "analysis_sequence"):
        analysis, request = original["analysis_sequence"], original["original_input"]
        value = request["sequence"] if field == "original_sequence" and request is not None else (
            analysis["analysis_sequence"] if field == "analysis_sequence" and analysis is not None else None)
        if analysis is None:
            invalid_original = request is not None and request["sequence"] is not None
            state = "invalid_input" if invalid_original else "missing_input"
            reason = "original_sequence_unavailable"
    else:
        structure, topology = original["structure"], original["topology"]
        if structure is None:
            state, reason = "missing_input", "original_structure_unavailable"
        elif topology is None or topology["status"] != "valid":
            state, reason = "invalid_input", "original_topology_invalid"
            value = structure["dot_bracket"] if field == "dot_bracket" else None
        else:
            value = structure["dot_bracket"] if field == "dot_bracket" else [
                [pair["i"], pair["j"]] for pair in topology["pairs"]]
    return {"field": field, "state": state, "value": deepcopy(value), "reason": reason}


def _member_matches(member, predicates, comparisons):
    # Predicates select recorded classifications, never rounded energy numbers.
    if member["membership_state"] == "alias" or member["comparison_id"] is None:
        return False
    energy = comparisons[member["comparison_id"]]["energy"]
    states = {"model_incompatible": "model_incompatible", "model_unknown": "model_unknown",
        "energy_unavailable": "native_energy_unavailable", "received_failure": "received_failure",
        "not_supplied": "not_supplied", "not_tested": "not_tested"}
    orders = {"lower_than_baseline": "variant_lower", "equal_to_baseline": "equal", "higher_than_baseline": "variant_higher"}
    for predicate in predicates:
        if predicate in states and member["energy_state"] == states[predicate]:
            return True
        if energy is not None and member["energy_state"] == "comparable":
            if predicate in orders and energy["order"] == orders[predicate]:
                return True
            if predicate == "within_baseline_tolerance" and energy["baseline_tolerance_band"] == "within":
                return True
    return False


def _scan_issue_relevant(issue, family, selected_ids):
    if issue["selection_id"] is not None and issue["selection_id"] not in selected_ids:
        return False
    if family == "scan_sites":
        return True
    # An energy return must not carry unrelated site/correspondence work merely
    # because the retained question also requested those calculations.
    return issue["stage"] in ("input", "authority", "compatibility", "projection") or issue["code"] in (
        "selected_population_only", "baseline_unavailable", "baseline_comparability_unknown",
        "nonfinite_derived_value")


def _project_one(sheet, components, selection, result_receipt_key, calculation_key):
    family = selection["family"]
    baseline = sheet["selected_question"]["baseline_member_id"]
    operands = {row["member_id"]: row for row in sheet["operands"]}
    comparisons = {row["comparison_id"]: row for row in components["comparisons"]}
    scan = components["scan"]
    comparison_ids = selection.get("comparison_ids", [selection["comparison_id"]] if "comparison_id" in selection else [])
    selected_comparisons = [comparisons[key] for key in comparison_ids]
    selected_sites = []
    selected_pairs = []
    issues, codes, qualification_cells = [], [], []
    unavailable, empty = False, False
    members = _unique([baseline, *[c["variant_member_id"] for c in selected_comparisons]]) if selected_comparisons else []
    qualification = {"codes": [], "domain": "declared_scan" if family.startswith("scan_") else
        "selected_sites" if family == "position_changes" or family == "comparison_counts" and
        bool(set(selection["metrics"]) & set(SITE_METRICS)) else "pairwise",
        "baseline_member_id": baseline, "member_ids": members,
        "site_populations": [], "pair_populations": [], "population": None, "issues": []}

    def add_count_population(comparison, selection_id, fields, target):
        nonlocal unavailable
        cells = _selected_cells(comparison["components"], fields, selection_id)
        qualification_cells.extend(cells)
        row = {"comparison_id": comparison["comparison_id"]}
        if selection_id is not None:
            row["selection_id"] = selection_id
        for cell in cells:
            row[cell["metric"]] = cell["value"] if cell["state"] == "present" else None
        target.append(row)

    if family == "energy_comparison":
        rows = []
        for comparison in selected_comparisons:
            energy = comparison["energy"]
            _require(energy is not None)
            rows.append({"comparison_id": comparison["comparison_id"], "baseline_member_id": baseline,
                "variant_member_id": comparison["variant_member_id"], "energy_kind": energy["request"]["quantity"],
                "normalization": energy["request"]["normalization"],
                "measurements": _selected_cells(energy["components"], selection["metrics"]),
                "order": energy["order"] if selection["include_order"] else None,
                "tolerance_band": energy["baseline_tolerance_band"] if selection["include_tolerance_band"] else None,
                "compatibility_state": energy["compatibility"]["state"]})
            issues.extend(energy["compatibility"]["issues"])
            unavailable |= selection["include_order"] and energy["order"] == "unavailable"
            unavailable |= selection["include_tolerance_band"] and energy["baseline_tolerance_band"] in ("not_requested", "unavailable")
        payload, empty = {"rows": rows}, not rows
    elif family == "structures":
        rows, members = [], selection["member_ids"]
        qualification["member_ids"] = deepcopy(members)
        for key in members:
            selected_operand = operands[key]
            operand = operands[selected_operand["canonical_member_id"]]
            original = operand["original_sheet"]
            structure = None if original is None else original["structure"]
            row_issues = _unique([*selected_operand["issues"], *operand["issues"]])
            values = [_structure_value(operand, field) for field in selection["fields"]]
            rows.append({"member_id": key, "coordinate_system": COORDINATE_SYSTEM,
                "structure_origin": None if structure is None else structure["origin"],
                "values": values, "issues": row_issues})
            for value in values:
                if value["state"] != "present":
                    unavailable = True
                    codes.append(value["reason"])
            issues.extend(row_issues)
        payload, empty = {"rows": rows}, not rows
    elif family == "position_changes":
        comparison = selected_comparisons[0]
        sid = selection["selection_id"]
        resolved = next(row for row in comparison["resolved_selections"] if row["selection"]["selection_id"] == sid)
        index_field = "baseline_index" if resolved["selection"]["coordinate_member_id"] == baseline else "variant_index"
        by_index = {row[index_field]: row for row in comparison["all_site_rows"] if row[index_field] is not None}
        _require(all(index in by_index for index in resolved["indices"]))
        selected_rows = [by_index[index] for index in resolved["indices"]]
        rows = [{**deepcopy(row), "change_indicator": _returned_cell(row["change_indicator"])}
            for row in selected_rows if row["transition"] in selection["transitions"]]
        unavailable |= any(row["change_indicator"]["state"] != "present" for row in selected_rows)
        selected_sites.append((comparison, sid))
        payload = {"comparison_id": comparison["comparison_id"], "selection_id": sid, "rows": rows}
        empty = not rows
    elif family == "pair_changes":
        rows = [{"comparison_id": comparison["comparison_id"], "change": deepcopy(row)}
            for comparison in selected_comparisons for row in comparison["all_pair_rows"]
            if row["relation"] in selection["relations"]]
        selected_pairs = selected_comparisons
        unavailable |= any(_cells(c["components"])["pair_symmetric_difference_count"]["state"] != "present"
            for c in selected_comparisons)
        payload, empty = {"rows": rows}, not rows
    elif family == "comparison_counts":
        rows = []
        pair_metrics = [metric for metric in selection["metrics"] if metric in PAIR_METRICS]
        site_metrics = [metric for metric in selection["metrics"] if metric in SITE_METRICS]
        for comparison in selected_comparisons:
            if pair_metrics or selection["include_pairing_change_state"]:
                selected_pairs.append(comparison)
                state = comparison["pairing_change_state"] if selection["include_pairing_change_state"] else None
                unavailable |= state in ("unresolved", "not_requested")
                rows.append({"comparison_id": comparison["comparison_id"], "selection_id": None,
                    "measurements": _selected_cells(comparison["components"], pair_metrics), "pairing_change_state": state})
            if site_metrics:
                for sid in selection["selection_ids"]:
                    selected_sites.append((comparison, sid))
                    rows.append({"comparison_id": comparison["comparison_id"], "selection_id": sid,
                        "measurements": _selected_cells(comparison["components"], site_metrics, sid), "pairing_change_state": None})
        payload, empty = {"rows": rows}, not rows
    elif family == "scan_energy":
        payload = {"scan_id": selection["scan_id"],
            "measurements": _selected_cells(scan["energy_components"], selection["metrics"]),
            "rank_class": scan["baseline_rank_class"] if selection["include_rank_class"] else None}
        unavailable |= payload["rank_class"] in ("unavailable", "not_requested")
        empty = not selection["metrics"] and not selection["include_rank_class"]
    elif family == "scan_sites":
        rows = []
        for sid in selection["selection_ids"]:
            for row in scan["site_components"]:
                if row["selection_id"] == sid:
                    rows.append({"selection_id": sid, "baseline_index": row["baseline_index"],
                        "measurements": _selected_cells(row["components"], selection["metrics"], sid)})
            invalid = [issue for c in components["comparisons"] for issue in c["issues"]
                if issue["selection_id"] == sid and issue["code"] == "invalid_site_selection"]
            if invalid:
                unavailable = True
                codes.append("invalid_site_selection")
        payload, empty = {"scan_id": selection["scan_id"], "rows": rows}, not rows or not selection["metrics"]
    else:
        choice = selection["members"]
        matching = [member for member in scan["members"] if
            member["member_id"] in choice["member_ids"]] if choice["kind"] == "explicit" else [
            member for member in scan["members"] if _member_matches(member, choice["predicates"], comparisons)]
        returned = matching if selection["limit"] is None else matching[:selection["limit"]]
        rows = []
        for member in returned:
            values = []
            for field in selection["fields"]:
                if field == "eligibility":
                    values.append({"field": field, "state": member["energy_state"]})
                else:
                    cell = member[_MEMBER_CELL_FIELDS[field]]
                    _require(cell is not None)
                    values.append({"field": field, "cell": _returned_cell(cell)})
            rows.append({"member_id": member["member_id"], "canonical_member_id": member["canonical_member_id"], "values": values})
            issues.extend(member["issues"])
        if choice["kind"] == "exceptions" and set(choice["predicates"]) & {
                "lower_than_baseline", "equal_to_baseline", "higher_than_baseline", "within_baseline_tolerance"}:
            unavailable |= scan["baseline_rank_class"] in ("unavailable", "not_requested")
            if "within_baseline_tolerance" in choice["predicates"]:
                unavailable |= scan["request"]["energy"] is None or scan["request"]["energy"]["baseline_absolute_tolerance"] is None
                if scan["request"]["energy"] is None or scan["request"]["energy"]["baseline_absolute_tolerance"] is None:
                    codes.append("not_requested")
        payload = {"scan_id": selection["scan_id"], "matched_count": len(matching),
            "returned_count": len(returned), "omitted_count": len(matching) - len(returned), "rows": rows}
        empty = not returned
        if len(matching) != len(returned):
            issues.append(comparison_issue("selected_window_omits_members", stage="projection"))
        qualification["member_ids"] = _unique([baseline, *[member["member_id"] for member in returned]])

    if family.startswith("scan_"):
        if family != "scan_members":
            qualification["member_ids"] = [baseline]
        # Aggregate codes are bounded; internal member-specific issue arrays are
        # not a second unrequested scan-member return.
        selected_ids = set(selection.get("selection_ids", []))
        relevant_issues = [issue for issue in scan["issues"] if _scan_issue_relevant(issue, family, selected_ids)]
        codes.extend(issue["code"] for issue in relevant_issues)
        if family in ("scan_energy", "scan_members") and scan["request"]["energy"] is not None:
            counts = _selected_cells(scan["energy_components"], SCAN_POPULATION_FIELDS)
            qualification_cells.extend(counts)
            qualification["population"] = {cell["metric"]: cell["value"] if cell["state"] == "present" else None for cell in counts}
        allowed_members = set(qualification["member_ids"])
        allowed_canonical = {operands[key]["canonical_member_id"] for key in allowed_members}
        allowed_comparisons = {c["comparison_id"] for c in components["comparisons"] if c["variant_member_id"] in allowed_canonical}
        issues.extend(relevant_issues)
        issues = [issue for issue in issues if _scan_issue_relevant(issue, family, selected_ids) and
            (issue["member_id"] is None or issue["member_id"] in allowed_members | allowed_canonical) and
            (issue["comparison_id"] is None or issue["comparison_id"] in allowed_comparisons)]
    else:
        for member_id in qualification["member_ids"]:
            issues.extend(operands[member_id]["issues"])
        if family not in ("structures", "energy_comparison"):
            selected_sids = {sid for _, sid in selected_sites}
            for comparison in selected_comparisons:
                issues.extend(issue for issue in comparison["issues"] if
                    issue["selection_id"] is None or issue["selection_id"] in selected_sids)

    for comparison, sid in selected_sites:
        add_count_population(comparison, sid, SITE_POPULATION_FIELDS, qualification["site_populations"])
        unavailable |= any(issue["code"] == "invalid_site_selection" and issue["selection_id"] == sid for issue in comparison["issues"])
    for comparison in selected_pairs:
        add_count_population(comparison, None, PAIR_POPULATION_FIELDS, qualification["pair_populations"])
    payload_cells = list(_numeric_cells(payload))
    unavailable |= any(cell["state"] != "present" for cell in payload_cells)
    codes.extend(cell["reason"] for cell in [*payload_cells, *qualification_cells] if cell["reason"] is not None)
    qualification["issues"] = _unique(issues)
    qualification["codes"] = _unique([*codes, *[issue["code"] for issue in qualification["issues"]]])
    populations = {cell["population_id"] for cell in [*payload_cells, *qualification_cells] if cell["population_id"] is not None}
    result = {"schema": PROJECTION_VERSION, "projection_id": selection["projection_id"], "family": family,
        "result_receipt_key": result_receipt_key, "calculation_key": calculation_key,
        "population_id": next(iter(populations)) if len(populations) == 1 else None,
        "selection": deepcopy(selection), "delivery": "qualified_unavailability" if unavailable else
            "empty_selected_set" if empty else "values", "payload": payload, "qualification": qualification}
    return checked(result, RNA_COMPARISON_PROJECTION_RESULT_SCHEMA, "projection_mismatch")


def project_rna_comparison(sheet: dict, components: dict, *, projections: list[dict],
        result_receipt_key: str, calculation_key: str) -> list[dict]:
    """Select exactly the explicit projection list, in that order, from saved data."""
    sheet, components, projections = _context(sheet, components, projections, result_receipt_key, calculation_key)
    return [_project_one(sheet, components, selection, result_receipt_key, calculation_key) for selection in projections]


def validate_rna_comparison_projection(value: dict, *, sheet: dict, components: dict,
        selection: dict, result_receipt_key: str, calculation_key: str) -> dict:
    """Reconstruct the selected projection, without rerunning scientific formulas."""
    value = checked(value, RNA_COMPARISON_PROJECTION_RESULT_SCHEMA, "projection_mismatch")
    sheet, components, selections = _context(sheet, components, [selection], result_receipt_key, calculation_key)
    expected = _project_one(sheet, components, selections[0], result_receipt_key, calculation_key)
    _require(_same(value, expected))
    return deepcopy(value)
