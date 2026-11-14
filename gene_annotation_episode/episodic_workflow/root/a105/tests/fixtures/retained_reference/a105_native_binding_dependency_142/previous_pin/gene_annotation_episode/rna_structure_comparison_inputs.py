"""Retain supplied RNA comparison inputs and explicit coordinate correspondence.

No folds, acquisition, pairing-change arithmetic, energy deltas or ranks occur
here. The caller supplies every selected operand and owns source authority.
"""
from __future__ import annotations

from copy import deepcopy

from .rna_structure_contracts import _same, validate_rna_sheet
from .rna_structure_comparison_contracts import (
    COLUMN_COORDINATE_SYSTEM, COORDINATE_SYSTEM, CORRESPONDENCE_REQUEST_SCHEMA,
    SHEET_VERSION, SOFTWARE_SCHEMA, _require, _validate_question, checked,
    comparison_issue, validate_rna_comparison_parameters, validate_rna_comparison_selector,
)


def _length(sheet):
    """Original structural coordinates take precedence, even for invalid text."""
    if sheet is None:
        return None
    if sheet["structure"] is not None:
        return len(sheet["structure"]["dot_bracket"])
    if sheet["analysis_sequence"] is not None:
        return sheet["analysis_sequence"]["length_nt"]
    original = sheet["original_input"]
    if original is not None and original["sequence"] is not None:
        return len(original["sequence"])
    return None


def _sequence(sheet):
    return None if sheet is None or sheet["analysis_sequence"] is None else sheet["analysis_sequence"]["analysis_sequence"]


def _unknown_map(length):
    return [] if length is None else [{"index": i, "state": "unknown",
        "counterpart_index": None, "column": None} for i in range(length)]


def _identity_index_map(sheet):
    if sheet is None or sheet["analysis_sequence"] is None:
        return True
    sequence = sheet["analysis_sequence"]
    return sequence["original_to_analysis_indices"] == list(range(sequence["length_nt"]))


def build_rna_correspondence(baseline: dict | None, variant: dict | None, *, request: dict) -> dict:
    """Build full maps solely from the exact selected request and original sheets.

    Scientific correspondence errors yield an invalid map with explicit unknown
    coordinates; malformed closed containers raise ValueError. Invalid original
    topology does not erase its actual coordinate extent or fabricate partners.
    """
    request = checked(request, CORRESPONDENCE_REQUEST_SCHEMA)
    baseline = validate_rna_sheet(baseline) if baseline is not None else None
    variant = validate_rna_sheet(variant) if variant is not None else None
    lengths = (_length(baseline), _length(variant))
    result = {"request": request, "state": "valid", "columns": deepcopy(request.get("columns", [])),
        "matches": deepcopy(request.get("matches", [])), "baseline_to_variant": _unknown_map(lengths[0]),
        "variant_to_baseline": _unknown_map(lengths[1]), "baseline_length_nt": lengths[0],
        "variant_length_nt": lengths[1], "issues": []}

    def qualify(code, *, state=None, index=None):
        if state is not None:
            result["state"] = state
        value = comparison_issue(code, stage="correspondence", index=index)
        if value not in result["issues"]:
            result["issues"].append(value)

    if None in lengths:
        qualify("original_structure_unavailable", state="missing_input")
        return result
    if not all(_identity_index_map(sheet) for sheet in (baseline, variant)):
        qualify("unsupported_index_map", state="invalid")
        return result
    a, b = _sequence(baseline), _sequence(variant)
    kind = request["kind"]
    if kind in ("identical_sequence", "substitution_only"):
        if a is None or b is None:
            qualify("original_sequence_unavailable", state="missing_input")
            return result
        if len(a) != len(b) or len(a) != lengths[0] or len(b) != lengths[1] or not a:
            qualify("invalid_correspondence", state="invalid")
            return result
        if kind == "identical_sequence":
            if a != b:
                qualify("invalid_correspondence", state="invalid")
                return result
        else:
            expected = [{"index": i, "baseline_symbol": left, "variant_symbol": right}
                for i, (left, right) in enumerate(zip(a, b)) if left != right]
            original_a = baseline["original_input"]["sequence"]
            original_b = variant["original_input"]["sequence"]
            substitutions = request["substitutions"]
            if [s["index"] for s in substitutions] != [s["index"] for s in expected] or any(
                actual["baseline_symbol"] not in (e["baseline_symbol"], original_a[e["index"]]) or
                actual["variant_symbol"] not in (e["variant_symbol"], original_b[e["index"]])
                for actual, e in zip(substitutions, expected)):
                qualify("substitution_manifest_mismatch", state="invalid")
                return result
        result["columns"] = [{"column": i, "baseline_index": i, "variant_index": i} for i in range(len(a))]
    elif kind == "supplied_complete_alignment":
        columns = request["columns"]
        if ([c["column"] for c in columns] != list(range(len(columns))) or
                any(c["baseline_index"] is None and c["variant_index"] is None for c in columns) or
                [c["baseline_index"] for c in columns if c["baseline_index"] is not None] != list(range(lengths[0])) or
                [c["variant_index"] for c in columns if c["variant_index"] is not None] != list(range(lengths[1]))):
            qualify("invalid_correspondence", state="invalid")
            return result
    else:
        matches = request["matches"]
        a_indices = [m["baseline_index"] for m in matches]
        b_indices = [m["variant_index"] for m in matches]
        if (any(i >= lengths[0] for i in a_indices) or any(i >= lengths[1] for i in b_indices) or
                a_indices != sorted(set(a_indices)) or b_indices != sorted(set(b_indices))):
            qualify("invalid_correspondence", state="invalid")
            return result
        qualify("partial_correspondence")
    if a is None or b is None:
        qualify("original_sequence_unavailable")
    elif len(a) != lengths[0] or len(b) != lengths[1]:
        qualify("sequence_identity_unverified")
    if lengths[0] != lengths[1]:
        qualify("different_sequence_lengths")
    columns = result["columns"] if kind != "supplied_partial_correspondence" else [
        {"column": i, **row} for i, row in enumerate(result["matches"])]
    for row in columns:
        for side, other, field in (("baseline_index", "variant_index", "baseline_to_variant"),
                ("variant_index", "baseline_index", "variant_to_baseline")):
            index = row[side]
            if index is not None:
                result[field][index] = {"index": index, "state": "matched" if row[other] is not None else "gap",
                    "counterpart_index": row[other], "column": row["column"]}
    if any(row["baseline_index"] is None or row["variant_index"] is None for row in columns):
        qualify("supplied_alignment_gap")
    return result


def _resolve_selection(selection, original_sheet):
    """Return the exact set union, or reject the whole selection as unusable."""
    n = _length(original_sheet)
    if n is None:
        return [], not (selection["positions"] or selection["intervals"] or selection["unpaired_region_keys"])
    if any(i >= n for i in selection["positions"]) or any(not 0 <= start < end <= n
            for start, end in selection["intervals"]):
        return [], False
    indices = set(selection["positions"])
    for start, end in selection["intervals"]:
        indices.update(range(start, end))
    if selection["unpaired_region_keys"]:
        topology = original_sheet["topology"] if original_sheet is not None else None
        if topology is None or topology["status"] != "valid":
            return [], False
        regions = {r["region_key"]: r for r in topology["regions"]}
        if any(key not in regions for key in selection["unpaired_region_keys"]):
            return [], False
        for key in selection["unpaired_region_keys"]:
            indices.update(regions[key]["unpaired_indices"])
    return sorted(indices), True


def _operand_issues(member, original_sheet, *, kind):
    member_id = member["member_id"]
    codes = []
    if kind in ("not_supplied", "not_tested", "received_failure"):
        codes.append(kind)
    elif kind == "alias":
        codes.append("duplicate_alias_excluded")
    elif original_sheet is not None:
        if original_sheet["structure"] is None:
            codes.append("original_structure_unavailable")
        if original_sheet["topology"] is not None and original_sheet["topology"]["status"] != "valid":
            codes.append("original_topology_invalid")
        if original_sheet["analysis_sequence"] is None:
            codes.append("original_sequence_unavailable")
        if original_sheet["structure"] is not None and original_sheet["structure"]["origin"] == "supplied_unknown":
            codes.append("unknown_source_origin")
    return [comparison_issue(code, stage="input", member_id=member_id) for code in codes]


def _populate(question, parameters, operands):
    """Internal reconstruction port shared with saved-sheet validation."""
    question = _validate_question(question)
    parameters = validate_rna_comparison_parameters(parameters)
    canonical = [m for m in question["membership"] if m["kind"] != "alias"]
    _require(type(operands) is dict and set(operands) == {m["member_id"] for m in canonical})
    rows, scan_sequences = [], {}
    for member in question["membership"]:
        kind, member_id = member["kind"], member["member_id"]
        state = member["state"] if kind == "declared_absent" else kind
        source = None
        if kind != "alias":
            source = operands[member_id]
            _require(type(source) is dict and set(source) == {
                "original_sheet", "original_bundle_software", "received_failure"})
        original = software = failure = None
        if kind == "saved_sheet":
            _require(source["original_sheet"] is not None, "retained_sheet_missing")
            original = validate_rna_sheet(source["original_sheet"])
            descriptor = member["saved_input"]
            _require(all(original[k] == descriptor[k] for k in ("record_key", "mode", "operation")), "original_receipt_mismatch")
            _require(source["received_failure"] is None)
            if source["original_bundle_software"] is not None:
                software = checked(source["original_bundle_software"], SOFTWARE_SCHEMA)
                _require(software["python_executable"].startswith("/"))
        elif kind == "received_failure":
            _require(_same(source["received_failure"], member["failure"]), "original_receipt_mismatch")
            _require(source["original_sheet"] is None and source["original_bundle_software"] is None)
            failure = deepcopy(member["failure"])
        elif kind != "alias":
            _require(all(value is None for value in source.values()))
        identity = "not_applicable"
        issues = _operand_issues(member, original, kind=state)
        if question["kind"] == "scan" and kind != "alias":
            sequence = _sequence(original)
            identity = "unverified" if sequence is None else "verified_analyzed_sequence"
            if sequence is not None:
                _require(sequence not in scan_sequences, "duplicate_sequence_variant_requires_representative")
                scan_sequences[sequence] = member_id
            else:
                issues.append(comparison_issue("sequence_identity_unverified", stage="input", member_id=member_id))
        rows.append({"member_id": member_id, "state": state,
            "canonical_member_id": member["canonical_member_id"] if kind == "alias" else member_id,
            "saved_input": deepcopy(member.get("saved_input")), "original_sheet": deepcopy(original),
            "original_bundle_software": software, "received_failure": failure,
            "variant_identity": identity, "issues": issues})
    by_id = {row["member_id"]: row for row in rows}
    baseline_id = question["baseline_member_id"]
    baseline = by_id[baseline_id]["original_sheet"]
    comparisons = []
    for selected in question["comparisons"]:
        comparison_id = selected["comparison_id"]
        variant = by_id[selected["variant_member_id"]]["original_sheet"]
        issues, correspondence = [], None
        if selected["correspondence"] is not None:
            correspondence = build_rna_correspondence(baseline, variant, request=selected["correspondence"])
            correspondence["issues"] = [{**i, "comparison_id": comparison_id} for i in correspondence["issues"]]
            issues.extend(deepcopy(correspondence["issues"]))
        elif selected["calculate_pair_changes"] or selected["site_selections"]:
            issues.append(comparison_issue("correspondence_not_supplied", stage="correspondence", comparison_id=comparison_id))
        resolved = []
        for selection in selected["site_selections"]:
            original = by_id[selection["coordinate_member_id"]]["original_sheet"]
            indices, usable = _resolve_selection(selection, original)
            resolved.append({"selection": deepcopy(selection), "indices": indices})
            if not usable:
                issues.append(comparison_issue("invalid_site_selection", stage="selection",
                    member_id=selection["coordinate_member_id"], comparison_id=comparison_id,
                    selection_id=selection["selection_id"]))
        comparisons.append({"comparison_id": comparison_id, "baseline_member_id": baseline_id,
            "variant_member_id": selected["variant_member_id"], "correspondence": correspondence,
            "resolved_selections": resolved, "calculate_pair_changes": selected["calculate_pair_changes"],
            "energy_request": deepcopy(selected["energy"]), "issues": issues})
    return {"schema": SHEET_VERSION, "coordinate_system": COORDINATE_SYSTEM,
        "column_coordinate_system": COLUMN_COORDINATE_SYSTEM, "selected_question": question,
        "parameters": parameters, "operands": rows, "comparisons": comparisons,
        "scan_request": deepcopy(question["scan"]), "issues": []}


def populate_rna_comparison_sheet(selector: dict, *, operands: dict[str, dict]) -> dict:
    """Retain the selected inputs, full maps and selected-index unions only."""
    selector = validate_rna_comparison_selector(selector)
    return _populate(selector["question"], selector["parameters"], operands)
