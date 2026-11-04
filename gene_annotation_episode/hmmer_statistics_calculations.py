"""Independent hmmstat calculations from its saved sheet; no acquisition.

This mirrors the native model-statistic definitions while retaining each
operand, occupancy, composition weight, transition term and rounding residual.
These are model statistics, never annotation probabilities or progress credit.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math

from .hmmer_model_calculations import calculate_hmmer_model_components, _hmmer2
from .hmmer_statistics_data import SCHEMA as SHEET_SCHEMA, valid_operation


SCHEMA = "hmmer_statistics_components_v1"
AMINO_BACKGROUND_3_4 = dict(zip("ACDEFGHIKLMNPQRSTVWY", (
    .0787945, .0151600, .0535222, .0668298, .0397062, .0695071, .0229198,
    .0590092, .0594422, .0963728, .0237718, .0414386, .0482904, .0395639,
    .0540978, .0683364, .0540687, .0673417, .0114135, .0304133)))
ISSUE_CODES = frozenset({"sheet_invalid", "parameter_invalid", "model_unavailable",
    "transition_unavailable", "occupancy_invalid", "zero_denominator", "logarithm_nonfinite",
    "summary_association_invalid", "native_difference_exceeds_tolerance",
    "distribution_not_in_topology", "native_conversion_basis_incompatible"})
COMPONENT_STATES = frozenset({"present", "missing", "incomplete", "incompatible", "nonfinite"})


def native_hmmstat_parameters(engine_version, alphabet):
    """Explicit versioned native defaults; the calculator never selects them."""
    if engine_version != "3.4" or alphabet not in {"amino", "DNA", "RNA"}:
        raise ValueError("hmmer_statistics_native_parameters_unavailable")
    background = AMINO_BACKGROUND_3_4 if alphabet == "amino" else dict.fromkeys("ACGT" if alphabet == "DNA" else "ACGU", .25)
    return {"background": deepcopy(background), "length_probability": 350 / 351,
            "probability_tolerance": 1e-4, "summary_rounding_tolerance": .0051}


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _component(value=None, *, state="present", unit="dimensionless", inputs=()):
    assert state in COMPONENT_STATES
    if value is not None and not _finite(value):
        value, state = None, "nonfinite"
    return {"value": value, "state": state, "unit": unit, "inputs": deepcopy(list(inputs))}


def _combined(components):
    return next((state for state in ("incompatible", "nonfinite", "incomplete", "missing")
                 if any(c["state"] == state for c in components)), "present")


def calculate_hmmstat_components(sheet, *, background=None, length_probability=None,
                                 probability_tolerance=1e-4, summary_rounding_tolerance=.0051):
    """Recalculate model statistics, retaining native and independent quantities.

All parameters and saved sheets must be finite JSON. Invalid finite parameters
produce explicit unavailable components. A zero-weight log term contributes0;
a positive weight requiring log(0) is unavailable/nonfinite. Raw probabilities
are not renormalized; the derived composition has its own explicit normalization.
"""
    parameters = {"background": background, "length_probability": length_probability,
        "probability_tolerance": probability_tolerance, "summary_rounding_tolerance": summary_rounding_tolerance}
    # Reject non-JSON/NaN configuration rather than saving an un-replayable sheet.
    json.dumps(parameters, allow_nan=False)
    result = {"schema": SCHEMA, "operation": deepcopy(sheet.get("operation")) if isinstance(sheet, dict) else None,
              "parameters": deepcopy(parameters), "model_components": None,
              "rows": [], "checks": [], "issues": []}

    def issue(code, key=None, field=None, **details):
        assert code in ISSUE_CODES
        result["issues"].append({"code": code, "stage": "calculation", "record_key": key,
                                 "field": field, "details": details})

    def check(name, state, key=None, field=None, inputs=()):
        result["checks"].append({"name": name, "state": state, "record_key": key,
                                 "field": field, "inputs": deepcopy(list(inputs))})

    if (not isinstance(sheet, dict) or sheet.get("schema") != SHEET_SCHEMA
            or not valid_operation(sheet.get("operation")) or not isinstance(sheet.get("model_extraction"), dict)
            or not isinstance(sheet.get("native_rows"), list) or not isinstance(sheet.get("associations"), list)):
        issue("sheet_invalid")
        return result
    p1_valid = _finite(length_probability) and 0 < length_probability <= 1
    tolerance_valid = _finite(summary_rounding_tolerance) and summary_rounding_tolerance >= 0
    if length_probability is not None and not p1_valid:
        issue("parameter_invalid", field="length_probability")
    if not tolerance_valid:
        issue("parameter_invalid", field="summary_rounding_tolerance")
    extraction = sheet["model_extraction"]
    model_components = calculate_hmmer_model_components(extraction, background=background,
                                                       probability_tolerance=probability_tolerance)
    result["model_components"] = model_components
    models = {row["record_key"]: row for row in extraction.get("records", []) if isinstance(row, dict) and "record_key" in row}
    native_by_key = {row["record_key"]: row for row in sheet["native_rows"] if isinstance(row, dict) and "record_key" in row}
    for base in model_components["rows"]:
        key = base["record_key"]
        model = models[key]
        h2 = _hmmer2(model)
        positions = model["positions"]
        size = model.get("length")
        complete = (type(size) is int and size > 0 and len(positions) == size and model.get("terminated") is True
                    and [p.get("position") for p in positions] == list(range(1, size + 1)))
        operands = lambda field, **kw: [{"record_key": key, "field": field, **kw,
            **({"source_encoding": model["representation"]["encoding"],
                "qualification": ("hmmer2_quantized_nominal"
                    if model["representation"]["encoding"] == "hmmer2_ascii_millibit_log_odds"
                    else "binary_layout_interpretation")} if h2 else {})}]
        row = {"record_key": key, "native_record_keys": [], "components": {}, "positions": [],
               "composition": {"weights": [], "probabilities": []}, "native_comparisons": []}
        result["rows"].append(row)
        c = row["components"]
        c["mean_match_entropy"] = deepcopy(base["mean_match_entropy"])
        c["mean_match_relative_entropy"] = deepcopy(base["mean_match_relative_entropy"])
        c["sequence_count"] = deepcopy(base["sequence_count"])
        c["effective_sequence_count"] = deepcopy(base["effective_sequence_count"])
        c["effective_sequence_ratio"] = deepcopy(base["effective_sequence_ratio"])
        q_state = next((item["state"] for item in model_components["checks"]
                        if item["code"] == "background_compatible" and item["record_key"] == key), "unknown")
        bg_state = "present" if q_state == "pass" else "missing" if background is None else "incompatible"
        bg_entropy = (math.fsum(-q * math.log2(q) for q in background.values() if q)
                      if bg_state == "present" else None)
        c["background_entropy"] = _component(bg_entropy, state=bg_state, unit="bit",
                                               inputs=[{"parameter": "background"}])
        info_state = _combined([c["background_entropy"], c["mean_match_entropy"]])
        c["mean_match_information"] = _component(bg_entropy - c["mean_match_entropy"]["value"]
            if info_state == "present" else None, state=info_state, unit="bit_per_match_position",
            inputs=[{"parameter": "background"}, *operands("positions.match")])

        transition_values = []
        transition_state = "incompatible" if h2 else "present" if complete else "incomplete"
        if h2:
            issue("distribution_not_in_topology", key, "occupancy", qualification="hmmer2_state_absent")
        if complete and not h2:
            distributions = [model["initial"].get("transitions")] + [p.get("transitions") for p in positions[:-1]]
            validations = [base["initial"]["transitions"]] + [p["transitions"] for p in base["positions"][:-1]]
            for distribution, validation in zip(distributions, validations):
                state = _combined([group["mass"] for group in validation.values()])
                if state != "present":
                    transition_state = state
                    break
                transition_values.append([cell["probability"] for cell in distribution["cells"]])
        if transition_state != "present":
            issue("transition_unavailable", key, "transitions", state=transition_state)
        occupancy = []
        if transition_state == "present":
            occupancy.append(transition_values[0][0] + transition_values[0][1])
            for transition in transition_values[1:]:
                old = occupancy[-1]
                occupancy.append(old * (transition[0] + transition[1]) + (1 - old) * transition[5])
            tol = probability_tolerance if _finite(probability_tolerance) and probability_tolerance >= 0 else 0
            if any(not _finite(o) or not -tol <= o <= 1 + tol for o in occupancy):
                issue("occupancy_invalid", key, "occupancy")
                transition_state = "incompatible"
        occupancy_inputs = operands("initial.transitions") + operands("positions.transitions")
        if h2:
            for operand in occupancy_inputs:
                operand["qualification"] = "hmmer2_state_absent"
        occupancy_sum = math.fsum(occupancy) if transition_state == "present" else None
        entry_sum = math.fsum(occupancy[1:]) if transition_state == "present" else None
        c["occupancy_sum"] = _component(occupancy_sum, state=transition_state, unit="expected_match_state_count", inputs=occupancy_inputs)
        c["entry_occupancy_sum"] = _component(entry_sum, state=transition_state, unit="expected_match_state_count",
            inputs=occupancy_inputs + operands("positions", population="positions_2_through_M"))
        kl_values = [p["relative_entropy"] for p in base["positions"]]
        weighted_state = "incompatible" if h2 else _combined([c["occupancy_sum"], *kl_values]) if complete else "incomplete"
        weighted = None
        if weighted_state == "present":
            if occupancy_sum <= 0:
                weighted_state = "nonfinite"
                issue("zero_denominator", key, "occupancy_sum")
            else:
                weighted = math.fsum(o * kl["value"] for o, kl in zip(occupancy, kl_values)) / occupancy_sum
        c["weighted_emission_relative_entropy"] = _component(weighted, state=weighted_state, unit="bit_per_occupied_match_state",
            inputs=occupancy_inputs + operands("positions.match") + [{"parameter": "background"}])

        entry_terms, entry_states = [], []
        for ordinal, p in enumerate(base["positions"]):
            occ = _component(occupancy[ordinal] if transition_state == "present" else None,
                state=transition_state, unit="match_state_occupancy", inputs=occupancy_inputs + operands("position", position=ordinal + 1))
            term = None
            state = "incompatible" if h2 else "missing" if ordinal == 0 or length_probability is None else "incompatible" if not p1_valid else transition_state
            if ordinal > 0 and state == "present":
                previous, t = occupancy[ordinal - 1], transition_values[ordinal]
                weighted_logs = ((previous * t[0], (t[0],)), (previous * t[1], (t[0], t[3])),
                                 ((1 - previous) * t[5], (t[5],)))
                if any(weight != 0 and any(value <= 0 for value in values) for weight, values in weighted_logs):
                    state = "nonfinite"
                    issue("logarithm_nonfinite", key, "entry_transition", position=ordinal + 1)
                else:
                    term = math.fsum(weight * math.fsum(math.log(value / length_probability) for value in values)
                                     for weight, values in weighted_logs if weight != 0) / math.log(2)
            entry = _component(term, state=state, unit="bit", inputs=operands("transitions", position=ordinal)
                + occupancy_inputs + [{"parameter": "length_probability"}])
            row["positions"].append({"position": p["position"], "occupancy": occ,
                "relative_entropy": deepcopy(p["relative_entropy"]), "entry_transition_term": entry})
            if ordinal > 0:
                entry_terms.append(term)
                entry_states.append(entry)
        entry_state = "incompatible" if h2 else _combined([c["entry_occupancy_sum"], *entry_states]) if complete else "incomplete"
        if complete and size < 2 and not h2:
            entry_state = "nonfinite"
            issue("zero_denominator", key, "entry_occupancy_sum")
        entry_mean = None
        if entry_state == "present":
            if entry_sum <= 0:
                entry_state = "nonfinite"
                issue("zero_denominator", key, "entry_occupancy_sum")
            else:
                entry_mean = math.fsum(entry_terms) / entry_sum
        c["mean_entry_transition_term"] = _component(entry_mean, state=entry_state, unit="bit_per_occupied_entry_state",
            inputs=occupancy_inputs + [{"parameter": "length_probability"}])
        total_state = _combined([c["weighted_emission_relative_entropy"], c["mean_entry_transition_term"]])
        c["position_relative_entropy"] = _component(weighted + entry_mean if total_state == "present" else None,
            state=total_state, unit="bit_per_match_position", inputs=occupancy_inputs + operands("positions.match")
            + [{"parameter": "background"}, {"parameter": "length_probability"}])

        match_states = [p["match"]["mass"] for p in base["positions"]]
        composition_state = "incompatible" if h2 else _combined([c["occupancy_sum"], *match_states]) if complete else "incomplete"
        weights, mass = [], None
        if composition_state == "present":
            weights = [math.fsum(o * p["match"]["cells"][a]["probability"] for o, p in zip(occupancy, positions))
                       for a in range(len(base["alphabet"]["symbols"]))]
            mass = math.fsum(weights)
            if mass <= 0:
                composition_state = "nonfinite"
                issue("zero_denominator", key, "composition_weight_sum")
        c["composition_weight_sum"] = _component(mass, state=composition_state, unit="expected_emission_mass",
            inputs=occupancy_inputs + operands("positions.match"))
        probs = [value / mass for value in weights] if composition_state == "present" else []
        for a, symbol in enumerate(base["alphabet"]["symbols"]):
            inputs = occupancy_inputs + operands("positions.match", symbol=symbol)
            row["composition"]["weights"].append({"symbol": symbol, "component": _component(weights[a] if weights else None,
                state=composition_state, unit="expected_emission_mass", inputs=inputs)})
            row["composition"]["probabilities"].append({"symbol": symbol, "component": _component(probs[a] if probs else None,
                state=composition_state, unit="probability", inputs=inputs + operands("composition_weight_sum", role="denominator"))})
        comp_state = _combined([c["composition_weight_sum"], c["background_entropy"]])
        comp_kl = None
        if comp_state == "present":
            symbols = base["alphabet"]["symbols"]
            if any(p > 0 and background[s] == 0 for p, s in zip(probs, symbols)):
                comp_state = "nonfinite"
                issue("logarithm_nonfinite", key, "composition_relative_entropy")
            else:
                comp_kl = math.fsum(p * math.log2(p / background[s]) for p, s in zip(probs, symbols) if p)
        c["composition_relative_entropy"] = _component(comp_kl, state=comp_state, unit="bit",
            inputs=occupancy_inputs + operands("positions.match") + [{"parameter": "background"}])

        try:
            native_parameters = native_hmmstat_parameters(sheet["operation"]["engine_version"], base["alphabet"]["kind"])
            native_background_matches = background == native_parameters["background"]
            native_p1_matches = length_probability == native_parameters["length_probability"]
        except ValueError:
            native_background_matches = native_p1_matches = None
        for association in sheet["associations"]:
            if not isinstance(association, dict) or association.get("model_record_keys") != [key]:
                continue
            native = native_by_key.get(association.get("native_record_key"))
            if not isinstance(native, dict) or association.get("state") != "validated":
                issue("summary_association_invalid", key, "associations")
                continue
            row["native_record_keys"].append(native["record_key"])
            for field, component_name in (("relent", "mean_match_relative_entropy"), ("info", "mean_match_information"),
                                           ("p_relE", "position_relative_entropy"), ("compKL", "composition_relative_entropy")):
                component = c[component_name]
                native_value = native["values"][field]
                state = component["state"] if native["states"][field] == "present" else "nonfinite" if native["states"][field] == "nonfinite" else "incompatible"
                delta = component["value"] - native_value if state == "present" else None
                comparable = native_background_matches and (native_p1_matches if field == "p_relE" else True)
                if h2:
                    comparable = None
                outcome = ("not_applicable" if comparable is False else "unknown"
                    if comparable is None or state != "present" or not tolerance_valid else
                    "pass" if abs(delta) <= summary_rounding_tolerance else "fail")
                inputs = operands(component_name) + [{"record_key": native["record_key"], "field": field}]
                if h2:
                    inputs[0]["qualification"] = "hmmer2_native_conversion_changes_basis"
                    issue("native_conversion_basis_incompatible", key, field,
                          qualification="hmmer2_native_conversion_changes_basis")
                row["native_comparisons"].append({"native_record_key": native["record_key"], "field": field,
                    "native_value": native_value, "difference": _component(delta, state=state, unit="bit", inputs=inputs),
                    "native_parameters_match": comparable})
                check("native_rounding_agreement", outcome, key, field, inputs + [{"parameter": "summary_rounding_tolerance"}])
                if outcome == "fail":
                    issue("native_difference_exceeds_tolerance", key, field, difference=delta)
    return result
