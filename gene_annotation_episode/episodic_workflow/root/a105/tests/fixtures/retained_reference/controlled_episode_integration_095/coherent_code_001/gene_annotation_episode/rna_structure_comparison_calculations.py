"""Deterministic comparisons of explicitly retained RNA sheets.

The functions consume closed, validated inputs. They do not discover inputs,
evaluate a thermodynamic model, select work, or turn predictions into observed
stability. Exact rational arithmetic precedes the single binary64 rounding of
derived energy values; tolerance is never a tie rule.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import math

from .rna_structure_contracts import _same, validate_rna_sheet
from .rna_structure_comparison_contracts import (
    ARRAY_SETTING_NAMES, CALCULATOR_VERSION, COMPATIBILITY_FIELDS,
    COMPONENTS_VERSION, ENERGY_METRICS, ENERGY_REQUEST_SCHEMA, METRIC_SPECS,
    MODEL_SETTING_NAMES, OTHER_SCALAR_SETTING_NAMES, PAIR_METRICS, PROFILE,
    SITE_METRICS, SOFTWARE_SCHEMA, UNCERTAINTY_REASON, checked,
    comparison_digest, comparison_issue, validate_rna_comparison_components,
    validate_rna_comparison_sheet,
)

# Accepted 362/addendum001 generation proof, not a native array observation.
_RECOGNIZED_SOFTWARE = {
    "worker_source_sha256": "d1c2e045856aa235e14ef5e7807139243e4e184d26d5978ce046726269f9d0c7",
    "rna_module_sha256": "3d136533fd55f2ca6bb4cbb7428004b5da2e79c8cee53aef76c6662624d91946",
    "rna_extension_sha256": "451e5ac69fba96b9d9a0640d1311b844962a1f97143d050446ebd459dfd0494d",
    "viennarna_distribution_version": "2.7.0",
}
_CHANGED = frozenset(("lost_pairing", "gained_pairing", "reassigned_partner"))
_UNCHANGED = frozenset(("unchanged_unpaired", "unchanged_partner"))
_DECIDABLE = _CHANGED | _UNCHANGED


def _unique_issues(*groups):
    result = []
    for group in groups:
        for issue in group:
            if issue not in result:
                result.append(deepcopy(issue))
    return result


def _population(sheet, *, comparison_id=None, selection_id=None):
    return "rna_comparison_population:" + comparison_digest({
        "input_sheet_sha256": comparison_digest(sheet), "calculator_version": CALCULATOR_VERSION,
        "comparison_id": comparison_id, "selection_id": selection_id,
        "scan_id": None if sheet["scan_request"] is None else sheet["scan_request"]["scan_id"],
    })


def _cell(prefix, metric, *, value=None, state="present", reason=None,
        numerator=None, denominator=None, paths=(), population=None, selection=None,
        unit=None, origin=None):
    formula = prefix + "." + metric
    spec = METRIC_SPECS[formula]
    unit = spec["units"][0] if unit is None else unit
    origin = spec["origins"][0] if origin is None else origin
    if state == "present" and value is None:
        raise ValueError("missing_numerical_value")
    if state == "present" and unit in ("nt", "sites", "pairs", "entries", "candidates", "aliases", "variants", "rank", "indicator"):
        numerator = value
    return {"metric": metric, "value": value if state == "present" else None,
        "unit": unit, "state": state, "reason": None if state == "present" else reason,
        "numerator": numerator, "denominator": denominator, "origin": origin,
        "formula_id": formula, "input_paths": list(dict.fromkeys(paths)),
        "population_id": population, "selection_id": selection,
        "uncertainty": {"state": "not_produced", "value": None, "reason": UNCERTAINTY_REASON}}


def _fraction_cell(prefix, metric, numerator, denominator, **kwargs):
    return _cell(prefix, metric, value=float(Fraction(numerator, denominator)) if denominator else None,
        state="present" if denominator else "unknown", reason=None if denominator else "zero_denominator",
        numerator=numerator, denominator=denominator, **kwargs)


def _rounded(value):
    try:
        result = float(value)
    except OverflowError:
        return None
    return result if math.isfinite(result) else None


def _comparison_inputs(sheet, comparison_id):
    for index, inputs in enumerate(sheet["comparisons"]):
        if inputs["comparison_id"] == comparison_id:
            operands = {o["member_id"]: (i, o) for i, o in enumerate(sheet["operands"])}
            return index, inputs, operands[inputs["baseline_member_id"]], operands[inputs["variant_member_id"]]
    raise ValueError("invalid_selection")


def _length(original):
    if original is None:
        return None
    if original["structure"] is not None:
        return len(original["structure"]["dot_bracket"])
    if original["analysis_sequence"] is not None:
        return original["analysis_sequence"]["length_nt"]
    value = original["original_input"]
    return None if value is None or value["sequence"] is None else len(value["sequence"])


def _topology(original):
    return None if original is None else original["topology"]


def _valid_topology(original):
    topology = _topology(original)
    return topology is not None and topology["status"] == "valid"


def _topology_failure(original):
    return (("invalid_input", "original_topology_invalid") if _topology(original) is not None
        else ("missing_input", "original_structure_unavailable"))


def _comparison_failure(inputs, a, b):
    for original in (a, b):
        if not _valid_topology(original):
            return _topology_failure(original)
    correspondence = inputs["correspondence"]
    if correspondence is None:
        return "missing_input", "correspondence_not_supplied"
    if correspondence["state"] == "invalid":
        return "invalid_input", "invalid_correspondence"
    if correspondence["state"] != "valid":
        return "missing_input", "invalid_correspondence"
    return None


def _original_paths(index, original, fields):
    root = f"/operands/{index}/original_sheet"
    return [root] if original is None else [root + "/" + field for field in fields]


def _topology_model_issues(a, b, comparison_id):
    """Report known supplied model differences without selecting an energy."""
    models = [None if original is None else original["model"] for original in (a, b)]
    if None in models:
        return []
    differences = []
    if any(not _same(models[0][name], models[1][name]) for name in
            ("engine", "engine_version", "effective_settings")):
        differences.append("model_setting_different")
    observed = [{r["name"]: r for r in m["other_observed_settings"]} for m in models]
    for name in observed[0].keys() & observed[1].keys():
        left, right = observed[0][name], observed[1][name]
        if left["state"] == right["state"] == "observed" and left["value"] is not None and right["value"] is not None and not _same(left["value"], right["value"]):
            differences.append("model_setting_different")
    if any(models[0]["parameter_artifact"][name] != models[1]["parameter_artifact"][name] for name in ("sha256", "size_bytes")):
        differences.append("parameter_identity_different")
    return [comparison_issue(code, stage="compatibility", comparison_id=comparison_id)
        for code in dict.fromkeys(differences)]


def _site_coordinates(inputs, a, b):
    correspondence = inputs["correspondence"]
    if correspondence is not None and correspondence["state"] == "valid":
        if correspondence["request"]["kind"] == "supplied_partial_correspondence":
            return ([(i, m["baseline_index"], m["variant_index"]) for i, m in enumerate(correspondence["matches"])]
                + [(None, m["index"], None) for m in correspondence["baseline_to_variant"] if m["state"] == "unknown"]
                + [(None, None, m["index"]) for m in correspondence["variant_to_baseline"] if m["state"] == "unknown"])
        return [(c["column"], c["baseline_index"], c["variant_index"]) for c in correspondence["columns"]]
    return [(None, i, None) for i in range(_length(a) or 0)] + [(None, None, i) for i in range(_length(b) or 0)]


def _partner(original, index, mapping):
    result = {"state": "unavailable", "local_index": None, "column": None, "counterpart_index": None}
    if index is None or not _valid_topology(original):
        return result
    partner = original["topology"]["positions"][index]["partner_index"]
    if partner is None:
        return {**result, "state": "unpaired"}
    entry = None if mapping is None else mapping[partner]
    if entry is None or entry["state"] == "unknown":
        return {**result, "state": "unmapped", "local_index": partner}
    return {"state": "mapped" if entry["state"] == "matched" else "gap",
        "local_index": partner, "column": entry["column"], "counterpart_index": entry["counterpart_index"]}


def _symbol(original, index):
    analysis = None if original is None else original["analysis_sequence"]
    return None if analysis is None or index is None or index >= analysis["length_nt"] else analysis["analysis_sequence"][index]


def _site_changes(sheet, comparison_id):
    ci, inputs, (ai, ao), (bi, bo) = _comparison_inputs(sheet, comparison_id)
    if not inputs["calculate_pair_changes"] and not inputs["resolved_selections"]:
        return {"all_site_rows": [], "components": [], "issues": []}
    a, b = ao["original_sheet"], bo["original_sheet"]
    correspondence = inputs["correspondence"]
    mapped = correspondence is not None and correspondence["state"] == "valid"
    amap = correspondence["baseline_to_variant"] if mapped else None
    bmap = correspondence["variant_to_baseline"] if mapped else None
    failure = _comparison_failure(inputs, a, b)
    population = _population(sheet, comparison_id=comparison_id)
    paths = [f"/comparisons/{ci}/correspondence", *_original_paths(ai, a, ("topology", "analysis_sequence")),
        *_original_paths(bi, b, ("topology", "analysis_sequence"))]
    rows, issues = [], _unique_issues(inputs["issues"], _topology_model_issues(a, b, comparison_id))
    for column, left, right in _site_coordinates(inputs, a, b):
        pa, pb = _partner(a, left, amap), _partner(b, right, bmap)
        if mapped and column is not None and left is None:
            transition, state, reason = "inserted_site", "missing_input", "selected_site_absent"
        elif mapped and column is not None and right is None:
            transition, state, reason = "deleted_site", "missing_input", "selected_site_absent"
        elif not _valid_topology(a) or not _valid_topology(b):
            transition = "unavailable_topology"
            state, reason = failure
        elif not mapped or column is None:
            transition = "unmapped_site"
            state, reason = failure or ("unknown", "unmapped_selected_site")
        elif pa["state"] == pb["state"] == "unpaired":
            transition, state, reason = "unchanged_unpaired", "present", None
        elif pa["state"] == "unpaired":
            transition, state, reason = "gained_pairing", "present", None
        elif pb["state"] == "unpaired":
            transition, state, reason = "lost_pairing", "present", None
        elif pa["column"] is None or pb["column"] is None:
            transition, state, reason = "unresolved_partner", "unknown", "unresolved_partner"
        else:
            transition = "unchanged_partner" if pa["column"] == pb["column"] else "reassigned_partner"
            state, reason = "present", None
        row_issues = [] if reason is None else [comparison_issue(reason, stage="calculate", comparison_id=comparison_id)]
        rows.append({"column": column, "baseline_index": left, "variant_index": right,
            "baseline_symbol": _symbol(a, left), "variant_symbol": _symbol(b, right),
            "baseline_partner": pa, "variant_partner": pb, "transition": transition,
            "change_indicator": _cell("rna_site_compare_v1", "change_indicator",
                value=int(transition in _CHANGED) if state == "present" else None,
                state=state, reason=reason, paths=paths, population=population), "issues": row_issues})
    components = []
    biological = {"changed_site_count", "unchanged_site_count", "lost_pairing_site_count",
        "gained_pairing_site_count", "reassigned_partner_site_count", "changed_site_fraction", "unchanged_site_fraction"}
    for si, resolved in enumerate(inputs["resolved_selections"]):
        selection = resolved["selection"]
        sid = selection["selection_id"]
        selected_paths = [*paths, f"/comparisons/{ci}/resolved_selections/{si}"]
        args = {"paths": selected_paths, "population": _population(sheet, comparison_id=comparison_id, selection_id=sid), "selection": sid}
        invalid = any(i["code"] == "invalid_site_selection" and i["selection_id"] == sid for i in inputs["issues"])
        index_field = "baseline_index" if selection["coordinate_member_id"] == inputs["baseline_member_id"] else "variant_index"
        by_index = {r[index_field]: r for r in rows if r[index_field] is not None}
        chosen = [by_index[i] for i in resolved["indices"]]
        counts = {t: sum(r["transition"] == t for r in chosen) for t in (*_DECIDABLE,
            "deleted_site", "inserted_site", "unmapped_site", "unavailable_topology", "unresolved_partner")}
        changed = sum(counts[t] for t in _CHANGED)
        unchanged = sum(counts[t] for t in _UNCHANGED)
        decidable, requested = changed + unchanged, len(resolved["indices"])
        values = {"requested_site_count": requested,
            "shared_site_count": sum(r["baseline_index"] is not None and r["variant_index"] is not None for r in chosen),
            "decidable_site_count": decidable, "changed_site_count": changed, "unchanged_site_count": unchanged,
            **{t + "_site_count": counts[t] for t in ("lost_pairing", "gained_pairing", "reassigned_partner", "unavailable_topology", "unresolved_partner")},
            **{t + "_count": counts[t] for t in ("deleted_site", "inserted_site", "unmapped_site")}}
        fractions = {"decidable_site_fraction": (decidable, requested),
            "changed_site_fraction": (changed, decidable), "unchanged_site_fraction": (unchanged, decidable)}
        for metric in SITE_METRICS:
            if invalid:
                cell = _cell("rna_site_compare_v1", metric, state="invalid_input", reason="invalid_site_selection", **args)
            elif failure and (metric in biological or metric == "shared_site_count" and not mapped):
                cell = _cell("rna_site_compare_v1", metric, state=failure[0], reason=failure[1], **args)
            elif metric in fractions:
                cell = _fraction_cell("rna_site_compare_v1", metric, *fractions[metric], **args)
            else:
                cell = _cell("rna_site_compare_v1", metric, value=values[metric], **args)
            components.append(cell)
    issues = _unique_issues(issues, *(r["issues"] for r in rows))
    return {"all_site_rows": rows, "components": components, "issues": issues}


def calculate_rna_site_changes(sheet: dict, *, comparison_id: str) -> dict:
    """Compare every declared coordinate, then count each retained site union."""
    return _site_changes(validate_rna_comparison_sheet(sheet), comparison_id)


def _pair_changes(sheet, comparison_id):
    ci, inputs, (ai, ao), (bi, bo) = _comparison_inputs(sheet, comparison_id)
    if not inputs["calculate_pair_changes"]:
        return {"all_pair_rows": [], "components": [], "pairing_change_state": "not_requested", "issues": []}
    a, b = ao["original_sheet"], bo["original_sheet"]
    correspondence = inputs["correspondence"]
    valid_map = correspondence is not None and correspondence["state"] == "valid"
    failure = _comparison_failure(inputs, a, b)
    paths = [f"/comparisons/{ci}/correspondence", *_original_paths(ai, a, ("topology",)), *_original_paths(bi, b, ("topology",))]
    args = {"paths": paths, "population": _population(sheet, comparison_id=comparison_id)}
    originals = [o["topology"]["pairs"] if _valid_topology(o) else None for o in (a, b)]
    maps, unknown = [], []
    for pairs, field in zip(originals, ("baseline_to_variant", "variant_to_baseline")):
        mapped_pairs, unmapped = {}, []
        for pair in pairs or []:
            columns = [correspondence[field][i]["column"] for i in (pair["i"], pair["j"])] if valid_map else [None, None]
            if None in columns:
                unmapped.append(pair)
            else:
                mapped_pairs[tuple(columns)] = pair
        maps.append(mapped_pairs)
        unknown.append(unmapped)
    rows = []
    def append(relation, columns, left=None, right=None):
        gap = False
        if columns is not None:
            for pair, field in ((left, "baseline_to_variant"), (right, "variant_to_baseline")):
                if pair is not None:
                    gap = gap or any(correspondence[field][i]["state"] == "gap" for i in (pair["i"], pair["j"]))
        row_issues = [comparison_issue("unresolved_pair_endpoints", stage="calculate", comparison_id=comparison_id)] if relation.startswith("unresolved") else []
        rows.append({"relation": relation, "columns": None if columns is None else list(columns),
            "baseline_pair": None if left is None else [left["i"], left["j"]],
            "variant_pair": None if right is None else [right["i"], right["j"]],
            "baseline_pair_key": None if left is None else left["pair_key"],
            "variant_pair_key": None if right is None else right["pair_key"],
            "gap_endpoint": gap, "issues": row_issues})
    A, B = set(maps[0]), set(maps[1])
    if failure is None:
        for columns in sorted(A | B):
            append("preserved" if columns in A & B else "lost" if columns in A else "gained",
                columns, maps[0].get(columns), maps[1].get(columns))
        for pair in unknown[0]:
            append("unresolved_baseline", None, left=pair)
        for pair in unknown[1]:
            append("unresolved_variant", None, right=pair)
    elif not valid_map:
        for pair in originals[0] or []:
            append("unresolved_baseline", None, left=pair)
        for pair in originals[1] or []:
            append("unresolved_variant", None, right=pair)
    change = len(A - B) + len(B - A)
    values = {"baseline_mapped_pair_count": len(A), "variant_mapped_pair_count": len(B),
        "baseline_unresolved_pair_count": len(unknown[0]), "variant_unresolved_pair_count": len(unknown[1]),
        "preserved_pair_count": len(A & B), "lost_pair_count": len(A - B), "gained_pair_count": len(B - A),
        "known_pair_change_count": change, "pair_symmetric_difference_count": change}
    fractions = {"preserved_baseline_pair_fraction": (len(A & B), len(A)),
        "mapped_baseline_pair_fraction": (len(A), len(originals[0] or [])),
        "mapped_variant_pair_fraction": (len(B), len(originals[1] or []))}
    components = []
    for metric in PAIR_METRICS:
        if metric in ("baseline_pair_count", "variant_pair_count"):
            side = 0 if metric.startswith("baseline") else 1
            if originals[side] is None:
                state, reason = _topology_failure((a, b)[side])
                cell = _cell("rna_pair_compare_v1", metric, state=state, reason=reason, **args)
            else:
                cell = _cell("rna_pair_compare_v1", metric, value=len(originals[side]), **args)
        elif metric.startswith("alignment_"):
            if valid_map and correspondence["request"]["kind"] != "supplied_partial_correspondence":
                field = "baseline_index" if metric == "alignment_inserted_nt" else "variant_index"
                cell = _cell("rna_pair_compare_v1", metric, value=sum(c[field] is None for c in correspondence["columns"]), **args)
            else:
                state, reason = ("unknown", "partial_correspondence") if valid_map else (
                    ("missing_input", "correspondence_not_supplied") if correspondence is None else
                    ("invalid_input" if correspondence["state"] == "invalid" else "missing_input", "invalid_correspondence"))
                cell = _cell("rna_pair_compare_v1", metric, state=state, reason=reason, **args)
        elif failure:
            cell = _cell("rna_pair_compare_v1", metric, state=failure[0], reason=failure[1], **args)
        elif metric == "pair_symmetric_difference_count" and any(unknown):
            cell = _cell("rna_pair_compare_v1", metric, state="unknown", reason="unresolved_pair_endpoints", **args)
        elif metric in fractions:
            cell = _fraction_cell("rna_pair_compare_v1", metric, *fractions[metric], **args)
        else:
            cell = _cell("rna_pair_compare_v1", metric, value=values[metric], **args)
        components.append(cell)
    complete = valid_map and not any(m["state"] == "unknown" for field in ("baseline_to_variant", "variant_to_baseline") for m in correspondence[field])
    state = "changed" if failure is None and change else "unchanged_in_complete_correspondence" if failure is None and complete else "unresolved"
    issues = _unique_issues(inputs["issues"], _topology_model_issues(a, b, comparison_id), *(r["issues"] for r in rows),
        [] if failure is None else [comparison_issue(failure[1], stage="calculate", comparison_id=comparison_id)])
    return {"all_pair_rows": rows, "components": components, "pairing_change_state": state, "issues": issues}


def calculate_rna_pair_changes(sheet: dict, *, comparison_id: str) -> dict:
    """Compare pair sets in declared alignment-column coordinates."""
    return _pair_changes(validate_rna_comparison_sheet(sheet), comparison_id)


def qualify_rna_energy_comparison(baseline: dict | None, variant: dict | None, *,
        request: dict, baseline_software: dict | None, variant_software: dict | None) -> dict:
    """Qualify retained scientific settings; opaque names confer no equivalence."""
    request = checked(request, ENERGY_REQUEST_SCHEMA)
    originals = [validate_rna_sheet(s) if s is not None else None for s in (baseline, variant)]
    software = [checked(s, SOFTWARE_SCHEMA) if s is not None else None for s in (baseline_software, variant_software)]
    return _qualify_energy(originals, software, request)


def _qualify_energy(originals, software, request):
    quantity = request["quantity"]
    energies = [None if s is None else s[quantity] for s in originals]
    models = [None if s is None else s["model"] for s in originals]
    checks, issues = {}, []
    def check(field, outcome, reason=None):
        checks[field] = outcome
        if reason is not None:
            issues.append(comparison_issue(reason, stage="compatibility"))
    def compare(field, values, *, absent_reason="model_setting_missing", difference_reason="model_setting_different", accepted=None):
        if any(v is None for v in values):
            check(field, "missing", absent_reason)
        elif not _same(values[0], values[1]):
            check(field, "different", difference_reason)
        elif accepted is not None and not accepted(values[0]):
            check(field, "unsupported", "unsupported_model_profile")
        else:
            check(field, "equal")
    kinds = [None if s is None else "native_mfe" if s["mode"] == "mfe_prediction" else "native_evaluation" for s in originals]
    if None in kinds:
        check("energy_kind", "missing", "requested_energy_unavailable")
    elif any(kind != quantity for kind in kinds):
        check("energy_kind", "unsupported", "energy_kind_mismatch")
    else:
        check("energy_kind", "equal")
    compare("unit", [None if e is None else e["unit"] for e in energies], absent_reason="requested_energy_unavailable", accepted=lambda v: v == "kcal/mol")
    for side, original, energy, model in zip(("baseline", "variant"), originals, energies, models):
        field = side + ".structure_association"
        if original is None or energy["state"] != "present" or original["structure"] is None:
            check(field, "missing", "requested_energy_unavailable")
        elif model is None:
            check(field, "missing", "native_model_missing")
        elif energy["structure_key"] != original["structure"]["structure_key"] or energy["model_key"] != model["model_key"] or energy["engine"] != model["engine"] or energy["engine_version"] != model["engine_version"]:
            check(field, "different", "energy_structure_mismatch")
        else:
            check(field, "equal")
    for name, expected in (("engine", "ViennaRNA"), ("engine_version", "2.7.0")):
        compare("model." + name, [None if m is None else m[name] for m in models],
            absent_reason="native_model_missing", difference_reason="model_setting_different", accepted=lambda v, e=expected: v == e)
    for name in ("hard_constraints", "soft_constraints"):
        if any(m is None for m in models):
            check(name, "missing", "native_model_missing")
        elif all(m["selected"][name] is None for m in models):
            check(name, "equal")
        else:
            check(name, "unsupported", "unsupported_model_profile")
    for name in MODEL_SETTING_NAMES:
        values = [None if m is None else m["effective_settings"][name] for m in models]
        compare("effective_settings." + name, values)
        if all(m is not None for m in models) and any(not _same(m["selected"][name], m["effective_settings"][name]) for m in models):
            check("effective_settings." + name, "different", "model_setting_different")
    for name in ("sha256", "size_bytes"):
        compare("parameter_artifact." + name, [None if m is None else m["parameter_artifact"][name] for m in models],
            absent_reason="parameter_identity_missing", difference_reason="parameter_identity_different")
    for name in ("parameter_load_return", "parameter_save_return"):
        if any(m is None for m in models):
            check(name, "missing", "parameter_identity_missing")
        elif all(type(m[name]) is int and m[name] != 0 for m in models):
            check(name, "equal")
        else:
            check(name, "unsupported", "parameter_identity_missing")
    observed = [{r["name"]: r for r in m["other_observed_settings"]} if m is not None else {} for m in models]
    names = set(OTHER_SCALAR_SETTING_NAMES) | set(ARRAY_SETTING_NAMES)
    if any(set(records) - names for records in observed):
        check("other_observed_settings.name_set", "unsupported", "unsupported_model_profile")
    elif any(set(records) != names for records in observed):
        check("other_observed_settings.name_set", "missing", "model_setting_missing")
    else:
        check("other_observed_settings.name_set", "equal")
    for name in OTHER_SCALAR_SETTING_NAMES:
        records = [s.get(name) for s in observed]
        field = "other_observed_settings." + name
        if any(r is None or r["state"] != "observed" or r["value"] is None for r in records):
            check(field, "missing", "model_setting_missing")
            continue
        values = [r["value"] for r in records]
        scalar_types = (str,) if name in ("backtrack_type", "nonstandards") else (int, float, bool)
        if any(type(v) not in scalar_types for v in values):
            check(field, "unsupported", "unsupported_model_profile")
        else:
            compare(field, values, accepted=(lambda v: type(v) is int and v == 0) if name == "energy_set" else
                (lambda v: v == "") if name == "nonstandards" else None)
    for name, expected in _RECOGNIZED_SOFTWARE.items():
        values = [None if s is None else s[name] for s in software]
        outcome = "missing" if None in values else "equal" if values == [expected, expected] else "unsupported"
        check("software." + name, outcome, None if outcome == "equal" else "software_generation_unverified")
    premises = all(value == "equal" for value in checks.values())
    for name in ARRAY_SETTING_NAMES:
        records = [s.get(name) for s in observed]
        if premises and all(r is not None and r["state"] == "unavailable" and r["value"] is None for r in records):
            check("other_observed_settings." + name, "equal_by_versioned_generation_rule", "equal_array_generation_rule_used")
        else:
            check("other_observed_settings." + name, "missing" if any(r is None or r["state"] == "unavailable" for r in records) else "unsupported", "software_generation_unverified")
    outcomes = set(checks.values())
    state = "incompatible" if "different" in outcomes else "unknown" if outcomes & {"missing", "unsupported"} else "compatible"
    return {"profile": PROFILE, "state": state,
        "checks": [{"field": f, "outcome": checks[f]} for f in COMPATIBILITY_FIELDS], "issues": _unique_issues(issues)}


def _native_energy_cells(original, operand, operand_index, request, *, side, population):
    """Return raw/selected cells and an exact value, retaining absent records."""
    quantity = request["quantity"]
    record = None if original is None else original[quantity]
    path = f"/operands/{operand_index}/original_sheet" + ("/" + quantity if original is not None else "")
    paths = [path]
    origin = "retained_native_prediction" if quantity == "native_mfe" else "retained_native_evaluation"
    state, reason = "present", None
    if record is None:
        reason = operand["state"] if operand["state"] in ("received_failure", "not_supplied", "not_tested") else "requested_energy_unavailable"
        state = "failed" if reason == "received_failure" else "missing_input"
    elif record["state"] != "present":
        state, reason = record["state"], "requested_energy_unavailable"
    raw = _cell("rna_energy_compare_v1", side + "_native_energy", value=None if record is None else record["value"],
        state=state, reason=reason, paths=paths, population=population, origin=origin)
    exact = None if state != "present" else Fraction(record["value"])
    numerator, denominator = None, None
    unit = "kcal/mol" if request["normalization"] == "none" else "kcal/mol/nt"
    if request["normalization"] == "per_nt":
        paths = [*paths, f"/operands/{operand_index}/original_sheet" + ("/analysis_sequence" if original is not None else "")]
        if exact is not None:
            analysis = original["analysis_sequence"]
            if analysis is None:
                state, reason, exact = "missing_input", "original_sequence_unavailable", None
            elif analysis["length_nt"] == 0:
                state, reason, exact, denominator = "unknown", "zero_denominator", None, 0
            else:
                numerator, denominator = record["value"], analysis["length_nt"]
                exact /= denominator
    value = _rounded(exact) if exact is not None else None
    if exact is not None and value is None:
        state, reason, exact = "unknown", "nonfinite_derived_value", None
    # Unnormalized values preserve the exact original scalar representation.
    if state == "present" and request["normalization"] == "none":
        value = record["value"]
    selected = _cell("rna_energy_compare_v1", side + "_selected_energy", value=value, state=state,
        reason=reason, numerator=numerator, denominator=denominator, paths=paths,
        population=population, unit=unit, origin=origin)
    return raw, selected, exact


def _energy_comparison(sheet, comparison_id):
    ci, inputs, (ai, ao), (bi, bo) = _comparison_inputs(sheet, comparison_id)
    request = inputs["energy_request"]
    if request is None:
        return None
    a, b = ao["original_sheet"], bo["original_sheet"]
    population = _population(sheet, comparison_id=comparison_id)
    compatibility = _qualify_energy([a, b], [ao["original_bundle_software"], bo["original_bundle_software"]], request)
    compatibility["issues"] = [{**issue, "comparison_id": comparison_id} for issue in compatibility["issues"]]
    if _length(a) is not None and _length(b) is not None and _length(a) != _length(b):
        compatibility["issues"].append(comparison_issue("different_sequence_lengths", stage="compatibility", comparison_id=comparison_id))
    ar, ac, ae = _native_energy_cells(a, ao, ai, request, side="baseline", population=population)
    br, bc, be = _native_energy_cells(b, bo, bi, request, side="variant", population=population)
    paths = list(dict.fromkeys([*ac["input_paths"], *bc["input_paths"], f"/comparisons/{ci}/energy_request",
        f"/operands/{ai}/original_bundle_software", f"/operands/{bi}/original_bundle_software",
        f"/operands/{ai}/original_sheet" + ("/model" if a is not None else ""),
        f"/operands/{bi}/original_sheet" + ("/model" if b is not None else "")]))
    args = {"paths": paths, "population": population, "unit": ac["unit"]}
    state, reason, delta = "present", None, None
    if ae is None or be is None:
        missing = ac if ae is None else bc
        state, reason = missing["state"], missing["reason"]
    elif compatibility["state"] != "compatible":
        state = "incompatible" if compatibility["state"] == "incompatible" else "unknown"
        preferred = next((i["code"] for i in compatibility["issues"] if i["code"] in
            ("model_setting_different", "parameter_identity_different", "energy_structure_mismatch")), None)
        reason = preferred or "baseline_comparability_unknown"
    else:
        delta = be - ae
        if _rounded(delta) is None:
            state, reason, delta = "unknown", "nonfinite_derived_value", None
    d = _cell("rna_energy_compare_v1", "energy_delta", value=_rounded(delta) if delta is not None else None,
        state=state, reason=reason, **args)
    absolute = _cell("rna_energy_compare_v1", "energy_absolute_delta", value=_rounded(abs(delta)) if delta is not None else None,
        state=state, reason=reason, **args)
    tolerance = request["baseline_absolute_tolerance"]
    tc = _cell("rna_energy_compare_v1", "baseline_tolerance", value=tolerance,
        state="not_requested" if tolerance is None else "present", reason="not_requested" if tolerance is None else None, **args)
    order = "unavailable" if delta is None else "variant_lower" if delta < 0 else "variant_higher" if delta > 0 else "equal"
    band = "not_requested" if tolerance is None else "unavailable" if delta is None else (
        "below" if delta < -Fraction(tolerance) else "above" if delta > Fraction(tolerance) else "within")
    cells = {c["metric"]: c for c in (ar, br, ac, bc, d, absolute, tc)}
    return {"request": deepcopy(request), "baseline_native": None if a is None else deepcopy(a[request["quantity"]]),
        "variant_native": None if b is None else deepcopy(b[request["quantity"]]), "compatibility": compatibility,
        "components": [cells[m] for m in ENERGY_METRICS], "order": order, "baseline_tolerance_band": band}


def calculate_rna_energy_comparison(sheet: dict, *, comparison_id: str) -> dict | None:
    """Return only the explicitly selected native energy comparison."""
    return _energy_comparison(validate_rna_comparison_sheet(sheet), comparison_id)


def _component_envelope(sheet, comparisons, scan):
    used = {"/parameters", "/selected_question", "/comparisons", "/scan_request"}
    def visit(value):
        if isinstance(value, dict):
            if "input_paths" in value:
                used.update(value["input_paths"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(comparisons)
    visit(scan)
    positions = {operand["member_id"]: i for i, operand in enumerate(sheet["operands"])}
    for inputs in sheet["comparisons"]:
        if inputs["calculate_pair_changes"] or inputs["resolved_selections"]:
            indices = [positions[inputs[field]] for field in ("baseline_member_id", "variant_member_id")]
            if all(sheet["operands"][i]["original_sheet"] is not None and
                    sheet["operands"][i]["original_sheet"]["model"] is not None for i in indices):
                used.update(f"/operands/{i}/original_sheet/model" for i in indices)
    # Explicit classification of retained fields not used in numerical formulas.
    unused = []
    for i, operand in enumerate(sheet["operands"]):
        used.update(f"/operands/{i}/{name}" for name in ("member_id", "state", "canonical_member_id", "variant_identity", "issues"))
        for field, retained in operand.items():
            root = f"/operands/{i}/{field}"
            pointers = [root + "/" + key for key in retained] if field == "original_sheet" and retained is not None else [root]
            for pointer in pointers:
                if not any(p == pointer or p.startswith(pointer + "/") or pointer.startswith(p + "/") for p in used):
                    unused.append(pointer)
    return {"schema": COMPONENTS_VERSION, "calculator_version": CALCULATOR_VERSION,
        "input_sheet_sha256": comparison_digest(sheet), "parameters": deepcopy(sheet["parameters"]),
        "comparisons": comparisons, "scan": scan, "used_input_paths": sorted(used),
        "unused_input_paths": unused, "issues": _unique_issues(sheet["issues"],
            *(c["issues"] for c in comparisons), [] if scan is None else scan["issues"])}


def calculate_rna_comparison_components(sheet: dict) -> dict:
    """Compose comparison and scan arithmetic without acquisition or I/O."""
    sheet = validate_rna_comparison_sheet(sheet)
    comparisons = []
    for inputs in sheet["comparisons"]:
        key = inputs["comparison_id"]
        sites, pairs, energy = _site_changes(sheet, key), _pair_changes(sheet, key), _energy_comparison(sheet, key)
        comparisons.append({**{field: deepcopy(inputs[field]) for field in
            ("comparison_id", "baseline_member_id", "variant_member_id", "correspondence", "resolved_selections")},
            "all_site_rows": sites["all_site_rows"], "all_pair_rows": pairs["all_pair_rows"],
            "components": pairs["components"] + sites["components"], "pairing_change_state": pairs["pairing_change_state"],
            "energy": energy, "issues": _unique_issues(inputs["issues"], sites["issues"], pairs["issues"],
                [] if energy is None else energy["compatibility"]["issues"])})
    from .rna_structure_scan_calculations import _scan_components
    scan = _scan_components(sheet, {c["comparison_id"]: c for c in comparisons})
    result = _component_envelope(sheet, comparisons, scan)
    return validate_rna_comparison_components(result, sheet=sheet)
