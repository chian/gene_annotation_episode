"""Inspectable descriptive RNA components from saved sheets and explicit parameters.

These ordinary functions never predict a structure, evaluate thermodynamics,
read artifacts, call native software or acquire data. Native energies are copied
unchanged; optional division by length is a descriptive normalization. There is
no overall score or gene-annotation probability.
"""
from __future__ import annotations

from copy import deepcopy

from .rna_structure_contracts import (
    COMPOSITION_METRICS, METRIC_UNITS, PAIR_TYPES, TOPOLOGY_METRICS, _require,
    issue, no_native_uncertainty, validate_rna_parameters, validate_rna_sheet,
)


def _cell(name, value, *, origin, fields, state="present", reason=None, numerator=None, denominator=None):
    return {"name": name, "value": value, "unit": METRIC_UNITS[name], "state": state, "reason": reason,
        "numerator": numerator, "denominator": denominator, "origin": origin,
        "formula_id": "native:mfe" if name == "mfe_kcal_mol" else "native:eval_structure" if name == "evaluated_energy_kcal_mol" else "rna_v1:" + name,
        "input_fields": fields, "uncertainty": no_native_uncertainty()}


def _topology_unavailable(sheet):
    topology = sheet["topology"]
    if topology is not None:
        return ("incompatible" if topology["status"] == "unsupported" else "invalid_input", topology["issues"][0]["code"])
    if sheet["original_input"] is None:
        return "invalid_input", "rna_invalid_input_schema"
    requested = sheet["native_mfe"] if sheet["mode"] == "mfe_prediction" else sheet["native_evaluation"]
    if requested["state"] not in ("present", "not_requested", "not_produced"):
        return requested["state"], requested["reason"]
    return "missing_input", "rna_native_result_missing"


def _topology(sheet, parameters):
    summary, pairs, stems, regions, errors = [], [], [], [], []
    origin = "derived_topology"

    def add(name, value, fields, **options):
        summary.append(_cell(name, value, origin=origin, fields=fields, **options))

    def ratio(name, numerator, denominator, fields, reason):
        add(name, numerator / denominator if denominator else None, fields,
            numerator=numerator, denominator=denominator,
            state="present" if denominator else "incompatible", reason=None if denominator else reason)

    topology = sheet["topology"]
    if topology is None or topology["status"] != "valid":
        state, reason = _topology_unavailable(sheet)
        for name in TOPOLOGY_METRICS:
            add(name, None, ["/topology"], state=state, reason=reason)
        return {"summary": summary, "pairs": pairs, "stems": stems, "regions": regions, "issues": errors}

    n = topology["length_nt"]
    pair_count = len(topology["pairs"])
    unpaired = n - 2 * pair_count
    spans = [pair["j"] - pair["i"] for pair in topology["pairs"]]
    lengths = [len(stem["pair_keys"]) for stem in topology["stems"]]
    stem_count = len(lengths)
    long_count = sum(length >= parameters["long_stem_min_pairs"] for length in lengths)
    closed_regions = [region for region in topology["regions"] if region["kind"] != "exterior"]
    closed_sizes = [len(region["unpaired_indices"]) for region in closed_regions]
    exterior = next(region for region in topology["regions"] if region["kind"] == "exterior")
    add("n_nt", n, ["/topology/length_nt"])
    add("pair_count", pair_count, ["/topology/pairs"])
    add("paired_nt", 2 * pair_count, ["/topology/pairs"])
    add("unpaired_nt", unpaired, ["/topology/length_nt", "/topology/pairs"])
    ratio("paired_fraction", 2 * pair_count, n, ["/topology/pairs", "/topology/length_nt"], "rna_zero_length_denominator")
    ratio("unpaired_fraction", unpaired, n, ["/topology/pairs", "/topology/length_nt"], "rna_zero_length_denominator")
    ratio("mean_pair_span_nt", sum(spans), pair_count, ["/topology/pairs"], "zero_pair_denominator")
    add("stem_count", stem_count, ["/topology/stems"])
    # The explicit v1 empty-maximum convention is zero pairs for zero stems.
    add("longest_stem_pairs", max(lengths, default=0), ["/topology/stems"])
    ratio("mean_stem_pairs", sum(lengths), stem_count, ["/topology/stems"], "zero_stem_denominator")
    add("stack_count", sum(length - 1 for length in lengths), ["/topology/stems"])
    add("long_stem_count", long_count, ["/topology/stems", "/parameters/topology/long_stem_min_pairs"])
    ratio("long_stem_fraction", long_count, stem_count,
        ["/topology/stems", "/parameters/topology/long_stem_min_pairs"], "zero_stem_denominator")
    for name, kind in (("hairpin_count", "hairpin"), ("bulge_count", "bulge"),
            ("internal_loop_count", "internal"), ("multibranch_count", "multibranch")):
        add(name, sum(region["kind"] == kind for region in closed_regions), ["/topology/regions"])
    loop_fields = ["/topology/regions", "/parameters/topology/include_exterior_in_loop_size_statistics"]
    ratio("loop_mean_unpaired_nt", sum(closed_sizes), len(closed_sizes), loop_fields, "zero_closed_loop_denominator")
    add("loop_max_unpaired_nt", max(closed_sizes) if closed_sizes else None, loop_fields,
        state="present" if closed_sizes else "incompatible", reason=None if closed_sizes else "zero_closed_loop_denominator")
    add("external_unpaired_nt", len(exterior["unpaired_indices"]), ["/topology/regions"])
    for index, pair in enumerate(topology["pairs"]):
        pairs.append({"row_key": pair["pair_key"], "cells": [_cell("pair_span_nt", spans[index], origin=origin,
            fields=[f"/topology/pairs/{index}/i", f"/topology/pairs/{index}/j"])]})
    for index, stem in enumerate(topology["stems"]):
        stems.append({"row_key": stem["stem_key"], "cells": [
            _cell("stem_length_pairs", lengths[index], origin=origin, fields=[f"/topology/stems/{index}/pair_keys"]),
            _cell("stack_count", lengths[index] - 1, origin=origin, fields=[f"/topology/stems/{index}/pair_keys"])]})
    for index, region in enumerate(topology["regions"]):
        cells = [_cell("loop_unpaired_nt", len(region["unpaired_indices"]), origin=origin,
                    fields=[f"/topology/regions/{index}/unpaired_indices"]),
            _cell("branch_count", len(region["immediate_branch_pair_keys"]), origin=origin,
                    fields=[f"/topology/regions/{index}/immediate_branch_pair_keys"])]
        for metric, key in (("five_prime_unpaired_nt", "five_prime_unpaired_indices"),
                ("three_prime_unpaired_nt", "three_prime_unpaired_indices")):
            side = region[key]
            cells.append(_cell(metric, len(side) if side is not None else None, origin=origin,
                fields=[f"/topology/regions/{index}/{key}"],
                state="present" if side is not None else "incompatible",
                reason=None if side is not None else "rna_region_side_not_defined"))
        regions.append({"row_key": region["region_key"], "cells": cells})
    return {"summary": summary, "pairs": pairs, "stems": stems, "regions": regions, "issues": errors}


def _composition(sheet, parameters):
    origin = "derived_sequence_composition"
    fields = ["/sequence_pairs"]
    topology = sheet["topology"]
    reason = state = None
    if topology is None or topology["status"] != "valid":
        state, reason = _topology_unavailable(sheet)
    elif sheet["analysis_sequence"] is None:
        if sheet["original_input"] is not None and sheet["original_input"]["sequence"] is None:
            state, reason = "missing_input", "no_sequence_supplied"
        else:
            state = "invalid_input"
            reason = next((row["code"] for row in sheet["issues"] if row["code"] in
                ("rna_empty_sequence", "rna_invalid_sequence_symbol", "rna_invalid_input_schema")), "rna_invalid_input_schema")
    elif sheet["analysis_sequence"]["length_nt"] != topology["length_nt"]:
        state, reason = "incompatible", "rna_sequence_structure_length_mismatch"
    if reason is not None:
        return {"summary": [_cell(name, None, origin=origin, fields=fields, state=state, reason=reason)
            for name in COMPOSITION_METRICS], "issues": []}
    counts = {pair: 0 for pair in PAIR_TYPES}
    for row in sheet["sequence_pairs"]:
        if row["unambiguous"]:
            counts[row["ordered_pair"]] += 1
    unambiguous = sum(counts.values())
    ambiguous = len(sheet["sequence_pairs"]) - unambiguous
    accepted = sum(counts[pair] for pair in parameters["accepted_ordered_pair_types"])
    parameter_fields = ["/sequence_pairs", "/parameters/pair_composition/accepted_ordered_pair_types",
        "/parameters/pair_composition/denominator"]
    summary = [
        _cell("unambiguous_pair_count", unambiguous, origin=origin, fields=fields),
        _cell("ambiguous_pair_count", ambiguous, origin=origin, fields=fields),
        _cell("accepted_pair_count", accepted, origin=origin, fields=parameter_fields),
        _cell("accepted_pair_fraction", accepted / unambiguous if unambiguous else None,
            origin=origin, fields=parameter_fields, numerator=accepted, denominator=unambiguous,
            state="present" if unambiguous else "incompatible",
            reason=None if unambiguous else "zero_unambiguous_pair_denominator")]
    summary.extend(_cell("pair_count_" + pair, counts[pair], origin=origin, fields=fields) for pair in PAIR_TYPES)
    return {"summary": summary, "issues": []}


def _energy(sheet, parameters):
    summary, normalized = [], []
    topology = sheet["topology"]
    denominator = topology["length_nt"] if topology is not None and topology["status"] == "valid" else None
    for field, metric, per_nt, origin in (("native_mfe", "mfe_kcal_mol", "mfe_per_nt", "native_prediction"),
            ("native_evaluation", "evaluated_energy_kcal_mol", "evaluated_energy_per_nt", "native_evaluation")):
        energy = sheet[field]
        summary.append(_cell(metric, energy["value"], origin=origin, fields=["/" + field + "/value"],
            state=energy["state"], reason=energy["reason"]))
        fields = ["/" + field + "/value", "/topology/length_nt", "/parameters/energy/normalization"]
        if parameters["normalization"] == "none":
            normalized.append(_cell(per_nt, None, origin=origin, fields=["/parameters/energy/normalization"],
                state="not_requested", reason="normalization_not_requested"))
        elif energy["state"] != "present":
            normalized.append(_cell(per_nt, None, origin=origin, fields=fields, state=energy["state"],
                reason=energy["reason"], numerator=None, denominator=denominator))
        elif denominator is None or denominator == 0:
            state, reason = _topology_unavailable(sheet) if denominator is None else ("incompatible", "rna_zero_length_denominator")
            normalized.append(_cell(per_nt, None, origin=origin, fields=fields, state=state,
                reason=reason, numerator=energy["value"], denominator=denominator))
        else:
            normalized.append(_cell(per_nt, energy["value"] / denominator, origin=origin, fields=fields,
                numerator=energy["value"], denominator=denominator))
    return {"summary": summary + normalized, "issues": []}


def _parameter_subset(name, value):
    # These validation-only values are not implicit calculation choices. Each
    # public specialized function consumes and returns only its supplied subset.
    parameters = {"schema": "rna_calculation_parameters_v1",
        "topology": {"long_stem_min_pairs": 1, "include_exterior_in_loop_size_statistics": False},
        "pair_composition": {"accepted_ordered_pair_types": [], "denominator": "unambiguous_pairs"},
        "energy": {"normalization": "none"}}
    parameters[name] = value
    return validate_rna_parameters(parameters)[name]


def calculate_rna_topology_components(sheet: dict, *, parameters: dict) -> dict:
    """Count indexed topology, exposed loop sizes and explicitly selected long stems."""
    return _topology(validate_rna_sheet(sheet), _parameter_subset("topology", parameters))


def calculate_rna_pair_composition(sheet: dict, *, parameters: dict) -> dict:
    """Count all 16 ordered ACGU pair types; exclude ambiguity from the ratio denominator."""
    return _composition(validate_rna_sheet(sheet), _parameter_subset("pair_composition", parameters))


def calculate_rna_energy_components(sheet: dict, *, parameters: dict) -> dict:
    """Copy native energies and optionally divide each by the saved structure length."""
    return _energy(validate_rna_sheet(sheet), _parameter_subset("energy", parameters))


def _calculate(sheet, parameters):
    topology = _topology(sheet, parameters["topology"])
    composition = _composition(sheet, parameters["pair_composition"])
    energy = _energy(sheet, parameters["energy"])
    summary = topology["summary"] + composition["summary"] + energy["summary"]
    used = sorted({pointer for family in [summary, *[row["cells"] for rows in
        (topology["pairs"], topology["stems"], topology["regions"]) for row in rows]]
        for cell in family for pointer in cell["input_fields"] if not pointer.startswith("/parameters/")})
    unused = ["/native_uncertainty", "/model", "/subject_binding", "/native_input", "/legacy_quantities",
        "/native_mfe/numeric_text", "/native_mfe/engine", "/native_mfe/engine_version", "/native_mfe/model_key",
        "/native_evaluation/numeric_text", "/native_evaluation/engine", "/native_evaluation/engine_version",
        "/native_evaluation/model_key", "/analysis_sequence/symbol_counts", "/original_input/sequence_id"]
    return {"schema": "rna_structure_components_v1", "sheet_schema": sheet["schema"], "record_key": sheet["record_key"],
        "parameters": deepcopy(parameters), "calculator_version": "rna_structure_calculations_v1",
        "summary": summary, "pairs": topology["pairs"], "stems": topology["stems"], "regions": topology["regions"],
        "issues": deepcopy(sheet["issues"]), "used_native_fields": used, "unused_native_fields": unused}


def calculate_rna_prediction_components(sheet: dict, *, parameters: dict) -> dict:
    """Assemble the prediction's named components; no weighted total is calculated."""
    value = validate_rna_sheet(sheet)
    _require(value["mode"] == "mfe_prediction", "rna_invalid_sheet_schema")
    return _calculate(value, validate_rna_parameters(parameters))


def calculate_rna_feature_components(sheet: dict, *, parameters: dict) -> dict:
    """Assemble supplied-structure components independently of optional native success."""
    value = validate_rna_sheet(sheet)
    _require(value["mode"] == "supplied_features", "rna_invalid_sheet_schema")
    return _calculate(value, validate_rna_parameters(parameters))
