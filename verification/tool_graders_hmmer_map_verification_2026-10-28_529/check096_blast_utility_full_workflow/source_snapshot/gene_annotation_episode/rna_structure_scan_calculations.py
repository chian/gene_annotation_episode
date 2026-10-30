"""Counts and exact ranks over the parent's declared RNA scan population.

All members, including aliases and exclusions, remain in declared order.
Pairwise inputs are supplied complete by comparison_id, never discovered,
selected, or recomputed here. Ranks describe predicted/evaluated model energies
of the qualified finite population; they are not experimental stability.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import math

from .rna_structure_comparison_contracts import (
    POPULATED_COMPARISON_SCHEMA, SCAN_ENERGY_METRICS, SCAN_SITE_METRICS, checked,
    comparison_issue, validate_rna_comparison_components, validate_rna_comparison_sheet,
)
from .rna_structure_comparison_calculations import (
    _CHANGED, _UNCHANGED, _cell, _component_envelope, _fraction_cell,
    _native_energy_cells, _original_paths, _population, _qualify_energy, _rounded, _unique_issues,
)


def _exact_selected(cell):
    if cell["state"] != "present":
        return None
    if type(cell["value"]) not in (int, float) or type(cell["value"]) is float and not math.isfinite(cell["value"]):
        raise ValueError("invalid_selection")
    if cell["unit"] == "kcal/mol/nt":
        if type(cell["numerator"]) not in (int, float) or type(cell["denominator"]) is not int or cell["denominator"] <= 0:
            raise ValueError("invalid_selection")
        return Fraction(cell["numerator"]) / cell["denominator"]
    return Fraction(cell["value"])


def _scan_sites(sheet, comparisons, population):
    request = sheet["scan_request"]
    output = []
    for selection_id in request["topology_selection_ids"]:
        # A validates that each comparison has the exact same parent selection.
        selected = next(r for r in sheet["comparisons"][0]["resolved_selections"]
            if r["selection"]["selection_id"] == selection_id)
        indices = selected["indices"]
        for index in indices:
            transitions = []
            for inputs in sheet["comparisons"]:
                comparison = comparisons[inputs["comparison_id"]]
                row = next((r for r in comparison["all_site_rows"] if r["baseline_index"] == index), None)
                if row is None:
                    # A's complete-row validation rejects omitted available sites.
                    transitions.append("unavailable_topology")
                else:
                    transitions.append(row["transition"])
            changed = sum(t in _CHANGED for t in transitions)
            unchanged = sum(t in _UNCHANGED for t in transitions)
            decidable = changed + unchanged
            counts = {"decidable_variant_count": decidable, "changed_variant_count": changed,
                "unchanged_variant_count": unchanged,
                **{t + "_variant_count": transitions.count(t) for t in
                    ("lost_pairing", "gained_pairing", "reassigned_partner", "unavailable_topology", "unresolved_partner")},
                "deleted_variant_count": transitions.count("deleted_site"),
                "unmapped_variant_count": transitions.count("unmapped_site")}
            args = {"paths": ["/comparisons", "/scan_request"], "population": population, "selection": selection_id}
            cells = []
            for metric in SCAN_SITE_METRICS:
                if metric.endswith("fraction"):
                    numerator = changed if metric == "changed_variant_fraction" else unchanged
                    cell = _fraction_cell("rna_scan_site_v1", metric, numerator, decidable, **args)
                else:
                    cell = _cell("rna_scan_site_v1", metric, value=counts[metric], **args)
                cells.append(cell)
            output.append({"selection_id": selection_id, "baseline_index": index, "components": cells})
    return output


def _scan_components(sheet, pairwise_components):
    keys = [c["comparison_id"] for c in sheet["comparisons"]]
    if type(pairwise_components) is not dict or set(pairwise_components) != set(keys):
        raise ValueError("invalid_selection")
    for key in keys:
        value = checked(pairwise_components[key], POPULATED_COMPARISON_SCHEMA)
        if value["comparison_id"] != key:
            raise ValueError("invalid_selection")
    request = sheet["scan_request"]
    if request is None:
        return None
    baseline_id = sheet["selected_question"]["baseline_member_id"]
    baseline_index, baseline = next((i, o) for i, o in enumerate(sheet["operands"]) if o["member_id"] == baseline_id)
    population = _population(sheet)
    comparison_by_member = {c["variant_member_id"]: pairwise_components[c["comparison_id"]] for c in sheet["comparisons"]}
    selected_energy = request["energy"]
    scan_issues = [comparison_issue("selected_population_only", stage="calculate")]
    scan_issues = _unique_issues(scan_issues, *(o["issues"] for o in sheet["operands"]),
        *(c["issues"] for c in pairwise_components.values()))
    members = []
    result = {"request": deepcopy(request), "baseline_member_id": baseline_id, "members": members,
        "energy_components": [], "site_components": _scan_sites(sheet, pairwise_components, population),
        "baseline_rank_class": "not_requested", "issues": scan_issues}
    if selected_energy is None:
        for operand in sheet["operands"]:
            canonical = operand["canonical_member_id"]
            comparison = comparison_by_member.get(canonical)
            members.append({"member_id": operand["member_id"], "canonical_member_id": canonical,
                "membership_state": "alias" if operand["state"] == "alias" else "canonical",
                "energy_state": "not_requested", "comparison_id": None if comparison is None else comparison["comparison_id"],
                "energy": None, "delta": None, "exact_rank_start": None, "exact_rank_end": None,
                "issues": deepcopy(operand["issues"])})
        return result

    unit = "kcal/mol" if selected_energy["normalization"] == "none" else "kcal/mol/nt"
    population_paths = ["/selected_question/membership", "/comparisons", "/scan_request"]
    for index, operand in enumerate(sheet["operands"]):
        population_paths += [f"/operands/{index}/{field}" for field in ("state", "variant_identity", "original_bundle_software")]
        if operand["state"] != "alias":
            population_paths += _original_paths(index, operand["original_sheet"],
                (selected_energy["quantity"], "analysis_sequence", "model", "structure"))
    args = {"paths": population_paths, "population": population}
    original = baseline["original_sheet"]
    raw, baseline_cell, b = _native_energy_cells(original, baseline, baseline_index,
        selected_energy, side="baseline", population=population)
    proof = _qualify_energy([original, original], [baseline["original_bundle_software"]] * 2, selected_energy)
    scan_issues[:] = _unique_issues(scan_issues, proof["issues"])
    baseline_valid = b is not None and proof["state"] == "compatible" and baseline["variant_identity"] == "verified_analyzed_sequence"
    baseline_reason = "baseline_unavailable" if b is None else "baseline_comparability_unknown"
    if not baseline_valid:
        scan_issues.append(comparison_issue(baseline_reason, stage="calculate", member_id=baseline_id))
    baseline_state = (baseline["state"] if baseline["state"] in ("received_failure", "not_supplied", "not_tested")
        else "native_energy_unavailable" if b is None else "model_incompatible" if proof["state"] == "incompatible"
        else "comparable" if baseline_valid else "model_unknown")
    canonical_values = {}
    by_canonical = {}
    independent = {"native_energy_available_variant_count": 0,
        "received_failure_variant_count": 0, "not_supplied_variant_count": 0,
        "not_tested_variant_count": 0, "sheet_energy_unavailable_variant_count": 0}
    model_counts = {"model_incompatible_variant_count": 0, "model_unknown_variant_count": 0, "comparable_variant_count": 0}
    for operand in sheet["operands"]:
        if operand["state"] == "alias":
            continue
        member_id = operand["member_id"]
        comparison = comparison_by_member.get(member_id)
        member_issues = deepcopy(operand["issues"])
        if member_id == baseline_id:
            energy, state, exact = deepcopy(baseline_cell), baseline_state, b
            delta = _cell("rna_energy_compare_v1", "energy_delta", value=0.0 if baseline_valid else None,
                state="present" if baseline_valid else "unknown", reason=None if baseline_valid else baseline_reason,
                unit=unit, **args)
            member_issues = _unique_issues(member_issues, proof["issues"])
        else:
            energy_result = comparison["energy"]
            if energy_result is None:
                raise ValueError("invalid_selection")
            cells = {c["metric"]: c for c in energy_result["components"]}
            energy, delta = deepcopy(cells["variant_selected_energy"]), deepcopy(cells["energy_delta"])
            exact = _exact_selected(energy)
            member_issues = _unique_issues(member_issues, comparison["issues"], energy_result["compatibility"]["issues"])
            if cells["variant_native_energy"]["state"] == "present":
                independent["native_energy_available_variant_count"] += 1
            if operand["state"] in ("received_failure", "not_supplied", "not_tested"):
                state = operand["state"]
                independent[state + "_variant_count"] += 1
            elif exact is None:
                state = "native_energy_unavailable"
                independent["sheet_energy_unavailable_variant_count"] += 1
            elif energy_result["compatibility"]["state"] == "incompatible":
                state = "model_incompatible"
                model_counts["model_incompatible_variant_count"] += 1
            elif not baseline_valid:
                state = "model_unknown"
            elif energy_result["compatibility"]["state"] != "compatible" or operand["variant_identity"] != "verified_analyzed_sequence":
                state = "model_unknown"
                model_counts["model_unknown_variant_count"] += 1
            else:
                state = "comparable"
                model_counts["comparable_variant_count"] += 1
        if state == "comparable":
            canonical_values[member_id] = exact
        by_canonical[member_id] = {"member_id": member_id, "canonical_member_id": member_id,
            "membership_state": "canonical", "energy_state": state,
            "comparison_id": None if comparison is None else comparison["comparison_id"],
            "energy": energy, "delta": delta, "exact_rank_start": None, "exact_rank_end": None,
            "issues": member_issues}

    population_values = list(canonical_values.values()) if baseline_valid else []
    for member_id, row in by_canonical.items():
        eligible = member_id in canonical_values and baseline_valid
        exact = canonical_values.get(member_id)
        for field, metric in (("exact_rank_start", "member_rank_start"), ("exact_rank_end", "member_rank_end")):
            rank = ((1 + sum(e < exact for e in population_values)) if field == "exact_rank_start" else
                sum(e <= exact for e in population_values)) if eligible else None
            state = "present" if eligible else ("incompatible" if row["energy_state"] == "model_incompatible"
                else "failed" if row["energy_state"] == "received_failure" else "missing_input" if row["energy_state"] in
                    ("not_supplied", "not_tested", "native_energy_unavailable") else "unknown")
            reason = None if eligible else baseline_reason if not baseline_valid else (
                "model_setting_different" if row["energy_state"] == "model_incompatible" else
                row["energy_state"] if row["energy_state"] in ("received_failure", "not_supplied", "not_tested")
                else "requested_energy_unavailable" if row["energy_state"] == "native_energy_unavailable" else "baseline_comparability_unknown")
            row[field] = _cell("rna_scan_energy_v1", metric, value=rank, state=state, reason=reason, **args)
    for operand in sheet["operands"]:
        row = deepcopy(by_canonical[operand["canonical_member_id"]])
        if operand["state"] == "alias":
            row.update(member_id=operand["member_id"], membership_state="alias")
            row["issues"] = _unique_issues(row["issues"], operand["issues"])
        members.append(row)

    entries = len(sheet["operands"])
    canonical_count = len(by_canonical)
    variants = canonical_count - 1
    comparable = model_counts["comparable_variant_count"]
    lower = sum(e < b for key, e in canonical_values.items() if key != baseline_id) if baseline_valid else None
    equal = sum(e == b for key, e in canonical_values.items() if key != baseline_id) if baseline_valid else None
    higher = sum(e > b for key, e in canonical_values.items() if key != baseline_id) if baseline_valid else None
    tolerance = selected_energy["baseline_absolute_tolerance"]
    values = {"declared_entry_count": entries, "canonical_member_count": canonical_count,
        "alias_entry_count": entries - canonical_count, "declared_variant_count": variants, **independent,
        **model_counts, "rank_population_count": len(population_values),
        "lower_variant_count": lower, "equal_variant_count": equal, "higher_variant_count": higher,
        "baseline_rank_start": 1 + lower if baseline_valid else None,
        "baseline_rank_end": 1 + lower + equal if baseline_valid else None,
        "baseline_tie_count": 1 + equal if baseline_valid else None,
        "within_tolerance_variant_count": sum(abs(e - b) <= Fraction(tolerance) for key, e in canonical_values.items()
            if key != baseline_id) if baseline_valid and tolerance is not None else None,
        "lowest_energy_tie_count": population_values.count(min(population_values)) if baseline_valid else None}
    independent_names = {"declared_entry_count", "canonical_member_count", "alias_entry_count", "declared_variant_count", *independent}
    energy_names = {"baseline_selected_energy", "minimum_selected_energy", "baseline_energy_above_minimum"}
    for metric in SCAN_ENERGY_METRICS:
        if metric == "within_tolerance_variant_count" and tolerance is None:
            cell = _cell("rna_scan_energy_v1", metric, state="not_requested", reason="not_requested", **args)
        elif not baseline_valid and metric not in independent_names:
            cell = _cell("rna_scan_energy_v1", metric, state="unknown", reason=baseline_reason,
                **args, **({"unit": unit, "origin": baseline_cell["origin"]} if metric in energy_names - {"baseline_energy_above_minimum"}
                    else {"unit": unit} if metric in energy_names else {}))
        elif metric == "comparable_variant_fraction":
            cell = _fraction_cell("rna_scan_energy_v1", metric, comparable, variants, **args)
        elif metric in energy_names:
            if metric == "baseline_energy_above_minimum":
                value = _rounded(b - min(population_values))
                cell = _cell("rna_scan_energy_v1", metric, value=value, unit=unit,
                    state="present" if value is not None else "unknown",
                    reason=None if value is not None else "nonfinite_derived_value", **args)
            else:
                sources = [baseline_cell] if metric == "baseline_selected_energy" else [
                    by_canonical[key]["energy"] for key, e in canonical_values.items() if e == min(population_values)]
                source = sources[0]
                # Accepted addendum003: first declared tied minimum carries its
                # original ratio only; every tied minimum path remains visible.
                # This does not choose or return a best member/structure.
                cell = _cell("rna_scan_energy_v1", metric, value=source["value"], unit=unit,
                    numerator=source["numerator"], denominator=source["denominator"], origin=source["origin"],
                    paths=[p for s in sources for p in s["input_paths"]], population=population)
        else:
            cell = _cell("rna_scan_energy_v1", metric, value=values[metric], **args)
        result["energy_components"].append(cell)
    result["baseline_rank_class"] = "unavailable" if not baseline_valid else "not_lowest" if lower else "tied_lowest" if equal else "unique_lowest"
    return result


def calculate_rna_scan_components(sheet: dict, *, pairwise_components: dict) -> dict | None:
    """Count every declared member and rank qualified canonical energies."""
    sheet = validate_rna_comparison_sheet(sheet)
    result = _scan_components(sheet, pairwise_components)
    comparisons = [deepcopy(pairwise_components[c["comparison_id"]]) for c in sheet["comparisons"]]
    validate_rna_comparison_components(_component_envelope(sheet, comparisons, result), sheet=sheet)
    return result
