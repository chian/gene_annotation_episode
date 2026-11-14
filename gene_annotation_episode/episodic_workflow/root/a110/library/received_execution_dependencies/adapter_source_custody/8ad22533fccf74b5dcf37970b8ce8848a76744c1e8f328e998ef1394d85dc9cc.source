"""Pure descriptive calculations over a saved GenomeComparison native sheet.

The native fractions describe rounded first-HSP identity and subject endpoint
difference, not all-HSP coverage. This module neither populates the sheet nor
establishes joins, executed-input membership, or annotation confidence. Public
calculation validates the complete supplied contracts before doing arithmetic.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import math

from .bvbrc_proteome_data_contracts import ProteomeDataError
from .bvbrc_proteome_sheet_contracts import validate_proteome_sheet_data


_IDENTITY = "native_first_hsp_alignment_identity_fraction"
_ENDPOINT = "native_subject_endpoint_difference_fraction"
_MATERIALIZED = {"table_field_block", "published_association"}
_SCOPE_KEYS = ("track_key", "reference_row_ordinal", "association_key", "protein_key",
               "report_key", "query_ordinal", "hit_ordinal", "hsp_ordinal")
_LEGACY = ("legacy_first_hsp_only", "legacy_rounded_fraction",
           "legacy_subject_endpoint_difference", "legacy_zero_fallback_possible",
           "native_category_not_orthology_probability",
           "postfilter_cannot_recover_filtered_associations", "dependence_not_independence")
_JOIN_REASONS = {"not_supplied": "row_join_missing", "unmatched": "row_join_missing",
                 "ambiguous": "row_join_ambiguous", "conflicting": "row_join_conflict"}


def _unique(items):
    seen, result = set(), []
    for item in items:
        key = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            result.append(deepcopy(item))
    return result


def _cell(value=None, *, state="value", reasons=(), fields=()):
    return {"state": state, "value": value, "reason_codes": list(dict.fromkeys(reasons)),
            "source_fields": _unique(fields)}


def _scope(**values):
    return {key: values.get(key) for key in _SCOPE_KEYS}


def _diagnostic(code, *, path="", scope=None, fields=(), severity="qualification"):
    return {"code": code, "severity": severity, "path": path,
            "scope": _scope() if scope is None else deepcopy(scope),
            "source_fields": _unique(fields)}


def _requirement(code, required_input, *, scope=None, fields=()):
    return {"code": code, "required_input": required_input,
            "scope": _scope() if scope is None else deepcopy(scope),
            "source_fields": _unique(fields)}


def _invalid(code, path, required_input):
    result = {"status": "invalid", "value": None,
              "requirements": [_requirement(code, required_input)],
              "diagnostics": [_diagnostic(code, path=path, severity="error")]}
    return validate_proteome_sheet_data("NativeComponentsResult", result)


def _percent(row, name):
    native = row[name]
    fields = [native["source_field"]]
    if row["layout_state"] != "source_field_located":
        return _cell(state="ambiguous", reasons=["native_table_layout_uncertain"], fields=fields)
    if native["presence"] == "invalid":
        return _cell(state="invalid", reasons=["native_invalid_cell"], fields=fields)
    if native["presence"] != "value":
        return _cell(state="missing_input", reasons=["native_missing_cell"], fields=fields)
    return _cell(100 * native["value"], fields=fields)


def _association_components(row, parameters):
    failed, unknown = [], []
    for condition, field, parameter in (
        ("identity", _IDENTITY, "minimum_identity_fraction"),
        ("subject_endpoint_difference", _ENDPOINT,
         "minimum_subject_endpoint_difference_fraction"),
        ("category", "native_hit_category", "allowed_hit_categories"),
    ):
        limit = parameters[parameter]
        if limit is None:
            continue
        cell = row[field]
        if row["layout_state"] != "source_field_located" or cell["presence"] != "value":
            unknown.append(condition)
        elif condition == "category":
            if cell["value"] not in limit:
                failed.append(condition)
        elif Decimal(cell["lexeme"]) < Decimal(str(limit)):
            failed.append(condition)
    scope = _scope(track_key=row["track_key"], association_key=row["association_key"],
                   reference_row_ordinal=row["reference_row_ordinal"])
    identity, endpoint = _percent(row, _IDENTITY), _percent(row, _ENDPOINT)
    diagnostics = list(row["diagnostics"])
    for name, value in ((_IDENTITY, identity), (_ENDPOINT, endpoint)):
        diagnostics.extend(_diagnostic(code, path="/" + name, scope=scope,
                                       fields=value["source_fields"])
                           for code in value["reason_codes"])
    if unknown:
        diagnostics.append(_diagnostic("selection_unknown", scope=scope))
    return {"association_key": row["association_key"], "track_key": row["track_key"],
            "first_hsp_alignment_identity_percent": identity,
            "subject_endpoint_difference_percent": endpoint,
            "selection": "fail" if failed else "unknown" if unknown else "pass",
            "failed_conditions": failed, "unknown_conditions": unknown,
            "diagnostics": _unique(diagnostics)}


def _fraction_summary(rows, field):
    """Each emitted row belongs to exactly one missingness/layout partition."""
    partitions = {key: [] for key in ("value", "omitted", "explicit_null", "blank", "invalid", "layout")}
    for row in rows:
        key = row[field]["presence"] if row["layout_state"] == "source_field_located" else "layout"
        partitions[key].append(row)
    included = partitions["value"]
    values = [row[field]["value"] for row in included]
    fields = [row[field]["source_field"] for row in included]
    result = {"used_association_keys": [row["association_key"] for row in included],
              "unit": "fraction", "native_rounding_quantum": 0.001}
    names = {"value": "value_count", "omitted": "omitted_count", "explicit_null": "null_count",
             "blank": "blank_count", "invalid": "invalid_count", "layout": "layout_uncertain_count"}
    for key, name in names.items():
        result[name] = _cell(len(partitions[key]), fields=[row[field]["source_field"] for row in partitions[key]])
    total = math.fsum(values)
    result["sum"] = _cell(total, fields=fields)
    for name, value in (("mean", total / len(values) if values else None),
                        ("minimum", min(values) if values else None),
                        ("maximum", max(values) if values else None)):
        result[name] = (_cell(value, fields=fields) if values else
                        _cell(state="not_applicable", reasons=["no_eligible_values"]))
    return result


def _protein_key(protein):
    return protein["inventory_key"], protein["record_ordinal"]


def _bound_population(published, selected_keys, sequence_groups):
    """Distinct occurrences/pairs in published rows; groups precede postfilter.

    Unresolved association counts concern the interpretable published rows.
    Unresolved sequence count concerns distinct bound subject occurrences only;
    unbound subject rows are already counted separately and cannot be deduplicated.
    """
    references, subjects, selected, pairs = set(), set(), set(), set()
    unresolved_ref = unresolved_sub = 0
    for row in published:
        ref = _protein_key(row["reference_protein"]) if row["reference_join_state"] == "joined" else None
        sub = _protein_key(row["subject_protein"]) if row["subject_join_state"] == "joined" else None
        if ref is None:
            unresolved_ref += 1
        else:
            references.add(ref)
            if row["association_key"] in selected_keys:
                selected.add(ref)
        if sub is None:
            unresolved_sub += 1
        else:
            subjects.add(sub)
        if ref is not None and sub is not None:
            pairs.add((ref, sub))
    partners = defaultdict(set)
    for ref, sub in pairs:
        partners[sub].add(ref)
    grouped_subjects = set()
    group_count = 0
    for group in sequence_groups:
        present = subjects.intersection(_protein_key(member) for member in group["members"])
        if present:
            group_count += 1
            grouped_subjects.update(present)
    return {
        "observed_bound_reference_count": len(references),
        "observed_bound_subject_count": len(subjects),
        "unresolved_reference_association_count": unresolved_ref,
        "unresolved_subject_association_count": unresolved_sub,
        "multiple_reference_subject_count": sum(len(refs) > 1 for refs in partners.values()),
        "excess_bound_pair_count": len(pairs) - len(partners),
        "observed_selected_reference_count": len(selected),
        "demonstrated_subject_sequence_group_count": group_count,
        "unresolved_subject_sequence_count": len(subjects - grouped_subjects),
    }


def _ratio(numerator, denominator, *, unavailable=()):
    """Numerator and denominator survive every unavailable/zero ratio result."""
    fields = numerator["source_fields"] + denominator["source_fields"]
    reasons = list(unavailable)
    if numerator["state"] != "value":
        reasons.extend(numerator["reason_codes"])
    if denominator["state"] != "value":
        reasons.append("denominator_unavailable")
        reasons.extend(denominator["reason_codes"])
    if reasons:
        fraction = _cell(state="missing_input", reasons=reasons, fields=fields)
    elif denominator["value"] == 0:
        fraction = _cell(state="zero_denominator", reasons=["denominator_zero"], fields=fields)
    else:
        fraction = _cell(numerator["value"] / denominator["value"], fields=fields)
    return {"numerator": deepcopy(numerator), "denominator": deepcopy(denominator), "fraction": fraction}


def _materialization_reasons(track):
    if track["native_materialization"] == "not_in_projection":
        return ["track_missing_from_projection"]
    if track["native_materialization"] not in _MATERIALIZED:
        return ["track_materialization_unknown"]
    return []


def _membership_reasons(track, published, representation_conflict):
    reasons = _materialization_reasons(track)
    if track["complete_published_association_membership"] != "yes":
        reasons.append("reference_membership_unresolved")
    if representation_conflict:
        reasons.append("representation_conflict")
    reasons.extend(_JOIN_REASONS[row["reference_join_state"]] for row in published
                   if row["reference_join_state"] != "joined")
    return list(dict.fromkeys(reasons))


def _track_components(track, rows, association_components, primary, sheet, reference_count):
    references = {row["row_ordinal"]: row for row in primary["reference_rows"]}
    published = [row for row in rows if row["layout_state"] == "source_field_located"
                 and row["native_subject_identifier_present"]
                 and references[row["reference_row_ordinal"]]["patric_id"]["presence"] == "value"]
    selected_keys = {row["association_key"] for row in association_components if row["selection"] == "pass"}
    groups = sheet["joins"]["sequence_groups"] if sheet["joins"] is not None else []
    counts = _bound_population(published, selected_keys, groups)
    result = {name: _cell(value) for name, value in counts.items()}
    categories = Counter()
    for row in rows:
        cell = row["native_hit_category"]
        category = cell["value"] if row["layout_state"] == "source_field_located" and cell["presence"] == "value" else None
        categories["bi" if category == "bi (<->)" else "uni" if category == "uni (->)" else
                   "missing_category" if category is None else "other_category"] += 1
    result.update({"native_" + name + "_count": _cell(categories[name])
                   for name in ("bi", "uni", "other_category", "missing_category")})
    selected_counts = Counter(row["selection"] for row in association_components)
    selection_counts = {name: _cell(selected_counts[name]) for name in ("pass", "fail", "unknown")}
    representation_conflict = any(item["state"] == "conflicting" for item in sheet["representation_comparisons"])
    complete_reasons = _membership_reasons(track, published, representation_conflict)
    observed_reasons = _materialization_reasons(track)
    selected_reasons = complete_reasons + (["selection_unknown"] if selected_counts["unknown"] else [])
    no_published_reasons = list(complete_reasons)
    if reference_count["state"] != "value":
        no_published_reasons.extend(["denominator_unavailable", *reference_count["reason_codes"]])
    no_published = (_cell(state="missing_input", reasons=no_published_reasons)
                    if no_published_reasons else
                    _cell(reference_count["value"] - counts["observed_bound_reference_count"],
                          fields=reference_count["source_fields"]))
    qualifications = list(_LEGACY)
    qualifications.extend(code for count in (reference_count, track["input_record_count"])
                          for code in count["reason_codes"])
    qualifications.extend(complete_reasons)
    qualifications.extend(_JOIN_REASONS[row["subject_join_state"]] for row in published
                          if row["subject_join_state"] != "joined")
    qualifications.append("observed_subset_not_total")
    if any(row["layout_state"] != "source_field_located" for row in rows):
        qualifications.append("native_table_layout_uncertain")
    if primary["projection_completeness"] != "complete_document":
        qualifications.append("projection_incomplete")
    if sheet["directional_attachment"] is None or sheet["directional_attachment"]["state"] == "unavailable":
        qualifications.append("full_reports_not_retained")
    if counts["demonstrated_subject_sequence_group_count"]:
        qualifications.append("sequence_equivalence_not_feature_identity")
    result.update({
        "track_key": track["track_key"], "materialization": track["native_materialization"],
        "source_scope": primary["projection_completeness"],
        "source_association_record_count": _cell(len(rows)),
        "published_association_record_count": _cell(len(published)),
        "reference_input_record_count": deepcopy(reference_count),
        "comparison_input_record_count": deepcopy(track["input_record_count"]),
        "no_published_reference_count": no_published,
        "first_hsp_identity_summary": _fraction_summary(rows, _IDENTITY),
        "subject_endpoint_difference_summary": _fraction_summary(rows, _ENDPOINT),
        "observed_reference_fraction": _ratio(result["observed_bound_reference_count"], reference_count,
                                                unavailable=observed_reasons),
        "complete_published_reference_fraction": _ratio(result["observed_bound_reference_count"], reference_count,
                                                          unavailable=complete_reasons),
        "selection_counts": selection_counts,
        "observed_selected_reference_fraction": _ratio(result["observed_selected_reference_count"], reference_count,
                                                         unavailable=observed_reasons),
        "complete_selected_reference_fraction": _ratio(result["observed_selected_reference_count"], reference_count,
                                                         unavailable=selected_reasons),
        "qualifications": list(dict.fromkeys(qualifications)),
    })
    return result


def calculate_native_components(sheet: dict, *, parameters: dict) -> dict:
    """Return NativeComponentsResult without modifying or reacquiring inputs.

    All thresholds are explicit and inclusive. Disabled filters differ from an
    empty allowed-category list. Known failure dominates unknown conditions,
    with both retained. Exact-input denominators remain unavailable under the
    current correction002 witness boundary; visible rows never replace them.
    """
    try:
        saved = validate_proteome_sheet_data("NativeSheet", sheet)
    except ProteomeDataError as error:
        return _invalid("sheet_relationship_invalid", "/sheet" + error.path, "valid_saved_sheet")
    try:
        options = validate_proteome_sheet_data("NativeCalculationParameters", parameters)
    except ProteomeDataError as error:
        return _invalid("calculation_parameters_invalid", "/parameters" + error.path, "valid_parameters")
    tracks = {track["track_key"]: track for track in saved["tracks"]}
    keys = options["track_keys"]
    if len(keys) != len(set(keys)) or any(key not in tracks or key == "ref_genome" for key in keys):
        return _invalid("calculation_parameters_invalid", "/parameters/track_keys", "valid_parameters")
    primary = next(result["value"] for result in saved["native_results"] if result["value"] is not None
                   and result["value"]["source"]["content"]["source_ref"] == saved["primary_source_ref"])
    sheet_bytes = json.dumps(saved, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False, allow_nan=False).encode("utf-8")
    rows = [row for row in saved["association_rows"] if row["track_key"] in keys]
    associations = [_association_components(row, options) for row in rows]
    reference_count = tracks["ref_genome"]["input_record_count"]
    calculated_tracks = [_track_components(tracks[key], [row for row in rows if row["track_key"] == key],
                         [row for row in associations if row["track_key"] == key],
                         primary, saved, reference_count) for key in keys]
    requirements = list(saved["requirements"])
    diagnostics = list(saved["diagnostics"])
    for track in calculated_tracks:
        scope = _scope(track_key=track["track_key"])
        if track["reference_input_record_count"]["state"] != "value" or track["comparison_input_record_count"]["state"] != "value":
            requirements.append(_requirement("exact_executed_input_missing", "execution_input_witness", scope=scope))
        if track["unresolved_reference_association_count"]["value"] or track["unresolved_subject_association_count"]["value"]:
            requirements.append(_requirement("row_join_missing", "occurrence_mapping", scope=scope))
    requirements = _unique(requirements)
    diagnostics = _unique(diagnostics)
    components = {
        "version": "bvbrc_proteome_native_components_proposal_v1",
        "formula_version": "native_descriptive_components_v1",
        "sheet_sha256": hashlib.sha256(sheet_bytes).hexdigest(), "parameters": options,
        "associations": associations, "tracks": calculated_tracks,
        "used_component_families": ["legacy_identity", "legacy_subject_endpoint_difference", "native_category",
                                    "explicit_occurrence_membership", "full_sequence_identity"],
        "retained_unused_component_families": ["feature_function_assignments", "feature_taxonomy", "feature_families",
                                               "genomic_or_layout_coordinates", "directional_hsps"],
        "requirements": requirements, "diagnostics": diagnostics,
    }
    partial = bool(requirements or diagnostics or any(row["diagnostics"] for row in associations))
    result = {"status": "partial" if partial else "ok", "value": components,
              "requirements": deepcopy(requirements), "diagnostics": deepcopy(diagnostics)}
    return validate_proteome_sheet_data("NativeComponentsResult", result)


__all__ = ["calculate_native_components"]
