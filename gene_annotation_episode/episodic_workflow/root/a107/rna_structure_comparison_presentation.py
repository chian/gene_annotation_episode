"""Render already selected RNA comparison facts without expanding their scope.

These functions never acquire data, calculate scientific values or authenticate
custody. Existing result admission owns authority. A detached presentation view
removes exact duplicate facts; the original state and typed returns are intact.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import json

from jsonschema import Draft202012Validator, ValidationError

from .rna_structure_comparison_contracts import SELECTOR_VERSION
from .rna_structure_comparison_views import (
    PAIR_POPULATION_FIELDS, PROJECTION_SOURCE, PROJECTION_VERSION,
    RNA_COMPARISON_PROJECTION_RESULT_SCHEMA, SCAN_POPULATION_FIELDS,
    SITE_POPULATION_FIELDS,
)

_RECEIVED = "received_rna_comparison_values"
_RECEIPT_VERSION = "rna_structure_comparison_result_receipt_v1"
_VALIDATORS = {branch["properties"]["family"]["const"]: Draft202012Validator(branch)
    for branch in RNA_COMPARISON_PROJECTION_RESULT_SCHEMA["oneOf"]}
_LABELS = {
    "dot_bracket": "Dot-bracket", "original_sequence": "Original sequence",
    "analysis_sequence": "Analysis sequence", "pairs": "Base pairs",
    "native_mfe": "native minimum free energy",
    "native_evaluation": "native evaluated structure energy",
    "none": "none", "per_nt": "per nucleotide",
    "supplied_unknown": "supplied; origin unknown",
    "retained_native_prediction": "retained native prediction",
    "retained_native_evaluation": "retained native evaluation",
    "unique_lowest": "uniquely lowest", "tied_lowest": "tied lowest",
    "not_lowest": "not lowest", "unchanged_in_complete_correspondence":
        "unchanged in complete correspondence",
}


def _human(value):
    return "unavailable" if value is None else _LABELS.get(value, str(value).replace("_", " "))


def _value(value):
    if value is None:
        return "unavailable"
    if type(value) is bool:
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return "; ".join(_value(item) if not isinstance(item, (list, tuple))
            else "(" + ", ".join(_value(part) for part in item) + ")" for item in value) or "empty"
    return str(value) if value != "" else '""'


def _escape(value):
    return _value(value).replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def _table(headers, rows):
    rows = list(rows)
    if not rows:
        return "No selected rows returned."
    return "\n".join(["| " + " | ".join(_escape(v) for v in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(_escape(v) for v in row) + " |" for row in rows)])


def _checked_projection(row):
    if not isinstance(row, Mapping) or row.get("schema") != PROJECTION_VERSION:
        raise ValueError("rna_comparison_projection_shape_invalid")
    validator = _VALIDATORS.get(row.get("family"))
    if validator is None:
        raise ValueError("rna_comparison_projection_shape_invalid")
    try:
        # JSON Schema's number type alone does not reject NaN or infinity.
        json.dumps(row, allow_nan=False)
        validator.validate(row)
    except (TypeError, ValueError, ValidationError) as error:
        raise ValueError("rna_comparison_projection_shape_invalid") from error
    return deepcopy(dict(row))


def _append_rows(target, values):
    if not isinstance(values, list):
        raise ValueError("rna_comparison_projection_list_required")
    for value in values:
        row = _checked_projection(value)
        if row not in target:
            target.append(row)


def has_received_rna_comparison_context(state: Mapping) -> bool:
    """An empty group does not change an otherwise unrelated prompt's owner."""
    if not isinstance(state, Mapping):
        return False
    groups = state.get(_RECEIVED)
    return isinstance(groups, list) and any(isinstance(group, Mapping)
        and group.get("fact_source") == PROJECTION_SOURCE and bool(group.get("facts"))
        for group in groups)


def is_rna_comparison_results_context(state: Mapping) -> bool:
    if not isinstance(state, Mapping):
        return False
    assignment = state.get("execution_assignment")
    return (isinstance(assignment, Mapping)
        and assignment.get("version") == "execution_results_assignment_v1"
        and isinstance(assignment.get("selector"), Mapping)
        and assignment["selector"].get("version") == SELECTOR_VERSION)


def _is_receipt(value):
    return isinstance(value, Mapping) and value.get("version") == _RECEIPT_VERSION


def _own_outcome(body, status):
    return {"status": status, "operation": body["tool_name"],
        "delivery_complete": body["delivery_complete"],
        "issues": deepcopy(body["issues"]),
        "preparation_failure": deepcopy(body["preparation_failure"])}


def select_rna_comparison_presentation(state: Mapping) -> dict:
    """Select named, admitted values and remove only their exact display copies."""
    context, projections = deepcopy(dict(state)), []
    groups = context.get(_RECEIVED, [])
    if isinstance(groups, list):
        remaining = []
        for group in groups:
            if isinstance(group, Mapping) and group.get("fact_source") == PROJECTION_SOURCE:
                _append_rows(projections, group["facts"])
            else:
                remaining.append(group)
        if remaining:
            context[_RECEIVED] = remaining
        else:
            context.pop(_RECEIVED, None)

    # The ordinary parent forms are dictionaries with caller-chosen field names.
    # Do not search recursively or remove mixed/unrelated report information.
    reports = context.get("child_reports")
    if isinstance(reports, list) and projections:
        filtered = []
        for report in reports:
            if not isinstance(report, Mapping):
                filtered.append(report)
                continue
            item = dict(report)
            for name, values in report.items():
                if isinstance(values, list):
                    kept = [row for row in values if row not in projections]
                    if len(kept) != len(values):
                        if kept:
                            item[name] = kept
                        else:
                            item.pop(name)
            if item or not report:
                filtered.append(item)
        context["child_reports"] = filtered

    own_outcome = None
    if is_rna_comparison_results_context(state):
        progress = context.get("execution_progress")
        if isinstance(progress, dict) and PROJECTION_SOURCE in progress:
            _append_rows(projections, progress.pop(PROJECTION_SOURCE))
        outcome = context.get("last_local_outcome")
        if isinstance(outcome, Mapping) and _is_receipt(outcome.get("result")):
            body = outcome["result"]
            _append_rows(projections, body["projection_rows"])
            own_outcome = _own_outcome(body, outcome.get("status"))
            # The compact outcome renders the operation/status once. Preserve
            # feedback or other non-receipt data for its existing owner.
            rest = {key: value for key, value in outcome.items() if key not in
                {"status", "result", "record_refs", "changed_record_refs"} and value is not None}
            if rest:
                context["last_local_outcome"] = rest
            else:
                context.pop("last_local_outcome", None)
    return {"context": context, "projections": projections, "own_outcome": own_outcome}


def _state(value):
    state = _human(value["state"])
    return state if value.get("reason") is None else state + ": " + _human(value["reason"])


def _measurements(cells):
    # Counts/ranks often repeat their value as a numerator with no denominator.
    # That duplicate is not extra decision information. Actual ratios and a
    # known numerator for an unavailable value retain their supplied operands.
    with_ratio = any(cell["denominator"] is not None or (
        cell["numerator"] is not None and cell["numerator"] != cell["value"]) for cell in cells)
    headers = ["Measurement", "Value", "Unit"]
    if with_ratio:
        headers += ["Numerator", "Denominator"]
    headers += ["State", "Origin"]
    rows = []
    for cell in cells:
        row = [_human(cell["metric"]), cell["value"], cell["unit"]]
        if with_ratio:
            row += [cell["numerator"], cell["denominator"]]
        rows.append([*row, _state(cell), _human(cell["origin"])])
    return _table(headers, rows)


def _issues(issues):
    rows = []
    for issue in issues:
        scope = "; ".join(label + " " + str(issue[name]) for name, label in (
            ("member_id", "member"), ("comparison_id", "comparison"), ("selection_id", "selection"))
            if issue.get(name) is not None) or "scope not supplied"
        row = (scope, _human(issue.get("stage")), _human(issue["code"]))
        if row not in rows:
            rows.append(row)
    return _table(("Affected selection", "Stage", "Qualification"), rows)


def _partner(partner):
    if partner["state"] == "unpaired":
        return "unpaired"
    return (_human(partner["state"]) + "; local index " + _value(partner["local_index"])
        + "; counterpart index " + _value(partner["counterpart_index"])
        + "; alignment column " + _value(partner["column"]))


def _qualification(value):
    parts = []
    population = value["population"]
    if population is not None:
        parts += ["Scan population", _table(("Count", "Value"),
            ((_human(name), population[name]) for name in SCAN_POPULATION_FIELDS)),
            "Applies only to the declared comparable population; it does not establish a global optimum."]
    for key, fields, label in (("site_populations", SITE_POPULATION_FIELDS, "Selected-site coverage"),
                              ("pair_populations", PAIR_POPULATION_FIELDS, "Pair correspondence coverage")):
        for row in value[key]:
            title = label + " — " + row["comparison_id"]
            if key == "site_populations":
                title += "; selection " + row["selection_id"]
            parts += [title, _table(("Count", "Value"), ((_human(name), row[name]) for name in fields))]
    if value["issues"]:
        parts += ["Scoped qualifications", _issues(value["issues"])]
    scoped_codes = {issue["code"] for issue in value["issues"]}
    additional = [code for code in value["codes"] if code not in scoped_codes]
    if additional:
        parts.append("Additional input qualifications (member scope not supplied): "
            + "; ".join(_human(code) for code in additional) + ".")
    return parts


def _has_numeric_cell(value):
    if isinstance(value, Mapping):
        return ("metric" in value and "uncertainty" in value) or any(_has_numeric_cell(v) for v in value.values())
    return isinstance(value, list) and any(_has_numeric_cell(v) for v in value)


def _projection_text(row):
    family, payload, qualification = row["family"], row["payload"], row["qualification"]
    parts = ["Requested RNA " + _human(family) + " — " + row["projection_id"]]
    if row["delivery"] != "values":
        parts.append("Return state: " + _human(row["delivery"]) + ".")
    if family == "energy_comparison":
        for item in payload["rows"]:
            parts += ["Baseline " + item["baseline_member_id"] + "; variant " + item["variant_member_id"]
                + "; comparison " + item["comparison_id"],
                "Quantity: " + _human(item["energy_kind"]) + "; normalization: " + _human(item["normalization"])
                + "; compatibility: " + _human(item["compatibility_state"]) + ".",
                _measurements(item["measurements"])]
            if item["order"] is not None:
                parts.append("Selected ordering: " + _human(item["order"]) + ".")
            if item["tolerance_band"] is not None:
                parts.append("Selected tolerance classification: " + _human(item["tolerance_band"]) + ".")
    elif family == "structures":
        parts.append("Sequence coordinates: zero based.")
        parts.append(_table(("Member", "Selected field", "Complete supplied value", "Origin", "State"),
            ((item["member_id"], _human(value["field"]), value["value"], _human(item["structure_origin"]), _state(value))
                for item in payload["rows"] for value in item["values"])))
        for item in payload["rows"]:
            if item["issues"]:
                parts += ["Structure qualifications — " + item["member_id"], _issues(item["issues"])]
    elif family == "position_changes":
        parts += ["Comparison " + payload["comparison_id"] + "; selection " + payload["selection_id"],
            "Sequence indices and alignment columns are separate, zero-based coordinates.",
            _table(("Baseline base", "Baseline index", "Variant base", "Variant index", "Alignment column",
                "Baseline partner", "Variant partner", "Transition", "Change indicator", "Indicator state"),
                ((item["baseline_symbol"], item["baseline_index"], item["variant_symbol"], item["variant_index"],
                  item["column"], _partner(item["baseline_partner"]), _partner(item["variant_partner"]),
                  _human(item["transition"]), item["change_indicator"]["value"], _state(item["change_indicator"]))
                 for item in payload["rows"]))]
        for item in payload["rows"]:
            if item["issues"]:
                parts.append(_issues(item["issues"]))
    elif family == "pair_changes":
        parts += ["Pair endpoints use each sequence's zero-based indices; alignment columns are separate.",
            _table(("Comparison", "Relation", "Baseline endpoints", "Variant endpoints", "Alignment columns", "Gap endpoint"),
                ((item["comparison_id"], _human(item["change"]["relation"]), item["change"]["baseline_pair"],
                  item["change"]["variant_pair"], item["change"]["columns"], item["change"]["gap_endpoint"])
                 for item in payload["rows"]))]
        for item in payload["rows"]:
            if item["change"]["issues"]:
                parts.append(_issues(item["change"]["issues"]))
    elif family == "comparison_counts":
        for item in payload["rows"]:
            parts.append("Comparison " + item["comparison_id"] + ("; selection " + item["selection_id"]
                if item["selection_id"] is not None else ""))
            parts.append(_measurements(item["measurements"]))
            if item["pairing_change_state"] is not None:
                parts.append("Selected pairing-change state: " + _human(item["pairing_change_state"]) + ".")
    elif family == "scan_energy":
        parts += ["Baseline " + qualification["baseline_member_id"] + "; scan " + payload["scan_id"]
            + "; selected model-energy comparison.", _measurements(payload["measurements"])]
        if payload["rank_class"] is not None:
            parts.append("Baseline rank class: " + _human(payload["rank_class"]) + ".")
    elif family == "scan_sites":
        parts.append("Baseline " + qualification["baseline_member_id"] + "; scan " + payload["scan_id"]
            + "; baseline indices are zero based.")
        for item in payload["rows"]:
            parts += ["Baseline index " + str(item["baseline_index"]) + "; selection " + item["selection_id"],
                _measurements(item["measurements"])]
    elif family == "scan_members":
        parts += ["Scan " + payload["scan_id"],
            _table(("Matched members", "Returned members", "Omitted by selected window"),
                [(payload["matched_count"], payload["returned_count"], payload["omitted_count"])])]
        for item in payload["rows"]:
            parts.append("Selected member " + item["member_id"] + ("; alias of " + item["canonical_member_id"]
                if item["member_id"] != item["canonical_member_id"] else ""))
            cells = [value["cell"] for value in item["values"] if "cell" in value]
            if cells:
                parts.append(_measurements(cells))
            for value in item["values"]:
                if value["field"] == "eligibility":
                    parts.append("Selected eligibility: " + _human(value["state"]) + ".")
    parts.extend(_qualification(qualification))
    if _has_numeric_cell(payload):
        parts.append("Comparison uncertainty: not produced by the selected inputs.")
    return "\n\n".join(parts)


def render_rna_comparison_projections(projections: Sequence[Mapping]) -> str:
    rows = []
    _append_rows(rows, list(projections))
    return "\n\n".join(_projection_text(row) for row in rows)


def render_rna_comparison_own_outcome(outcome: Mapping | None) -> str | None:
    if outcome is None:
        return None
    parts = [_table(("Selected operation", "Action outcome", "Requested comparison delivery complete"),
        [(outcome["operation"], outcome["status"], outcome["delivery_complete"])])]
    if outcome["issues"]:
        parts.append(_issues(outcome["issues"]))
    failure = outcome["preparation_failure"]
    if failure is not None:
        parts += ["Calculation/input failure", _table(("Failure", "Member", "Artifact role"),
            [(_human(failure["code"]), failure.get("member_id"), _human(failure.get("artifact_role")))])]
    return "\n\n".join(parts)


def render_rna_comparison_lookup(result: Mapping) -> str | None:
    """Recognize exact values at the requested result boundary, never a deep search."""
    content = result.get("result", result) if isinstance(result, Mapping) else result
    if _is_receipt(content):
        status = result.get("status") if isinstance(result, Mapping) and content is not result else None
        return "\n\n".join(filter(None, [render_rna_comparison_own_outcome(_own_outcome(content, status)),
            render_rna_comparison_projections(content["projection_rows"])]))
    if isinstance(content, Mapping) and content.get("schema") == PROJECTION_VERSION:
        return render_rna_comparison_projections([content])
    if isinstance(content, list) and content and all(isinstance(row, Mapping)
            and row.get("schema") == PROJECTION_VERSION for row in content):
        return render_rna_comparison_projections(content)
    return None


__all__ = ["has_received_rna_comparison_context", "is_rna_comparison_results_context",
    "select_rna_comparison_presentation", "render_rna_comparison_projections",
    "render_rna_comparison_own_outcome", "render_rna_comparison_lookup"]
