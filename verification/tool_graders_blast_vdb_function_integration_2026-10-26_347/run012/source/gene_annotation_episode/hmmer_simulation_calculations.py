"""Independent offline hmmsim calculations from the saved S1 numerical sheet.

Gumbel ML solves the Lawless complete-data equation used by Easel. Forward
fits the largest floor(N*tail_mass) occurrences to an exponential distribution.
Original scores, native fits and their rounding are never overwritten. A
printed calibration is available only to printed-parameter diagnostics; Hybrid
pmu is undetermined and never becomes an established calibrated location.
"""
from __future__ import annotations

from copy import deepcopy
import math
import operator

from .hmmer_simulation_data import SCHEMA as SHEET_SCHEMA, SUMMARY_UNITS, recorded_tail_masses


SCHEMA = "hmmer_simulation_components_v1"
COMPONENT_STATES = frozenset({"present", "missing", "incomplete", "incompatible", "nonfinite", "failed"})
ISSUE_CODES = frozenset({"sheet_invalid", "parameters_invalid", "parameter_invalid", "tail_schedule_missing",
    "tail_schedule_invalid", "score_vector_missing", "score_vector_incomplete", "score_vector_invalid",
    "population_insufficient", "constant_population", "fit_failed", "fit_nonfinite", "empty_tail",
    "calibration_missing", "calibration_ambiguous", "calibration_undetermined", "calibration_invalid",
    "filter_criterion_missing", "filter_criterion_invalid", "filter_variant_unavailable",
    "native_rounding_difference", "alignment_score_difference", "alignment_population_incomplete",
    "source_association_unresolved", "score_vector_rounded"})
DEFAULT_PARAMETERS = {"fixed_lambda": 0.693147, "fit_tolerance": 1e-10,
                      "solver_iteration_limit": 200, "rounding_tolerance": 5.1e-5}
_OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge}
_PARAMETER_FIELDS = set(DEFAULT_PARAMETERS) | {"tail_masses", "filter_criterion"}

# Ordinary field documentation, not an interpreter or a scoring language.
COMPONENT_MEANINGS = {
    "observed_count": "Number of decoded score occurrences; not the requested -N.",
    "mean": "sum(score_i)/observed_count, in bits; complete population only.",
    "sample_variance": "sum((score_i-mean)**2)/(observed_count-1), in bit squared.",
    "x10": "Tenth highest occurrence (ties retained), in bits; requires at least ten.",
    "mu": "Gumbel complete-data location or Forward minimum selected-tail score, in bits.",
    "lambda": "Gumbel Lawless ML slope or reciprocal mean(tail_i-mu), in inverse bits.",
    "E10": "N*survival(x10), or N*selected_tail_mass*exponential_survival(x10).",
    "tail_count": "floor(N*selected_tail_mass); the actual selected occurrences, including ties.",
    "tail_threshold": "Minimum of the selected largest floor(N*tail_mass) score occurrences.",
    "alignment_mean": "sum(native M+D+I trace-state counts)/observed alignment rows.",
    "alignment_sample_sd": "sqrt(sum((count_i-mean)**2)/(N-1)), in trace states.",
    "filter_fraction": "passing occurrence count divided by explicitly recorded -N.",
    "rounding_residual": "independently recalculated value minus original printed native value.",
}


def _finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def _input(record_key, field):
    return {"record_key": record_key, "field": field}


def _component(value, unit, inputs, state="present"):
    assert state in COMPONENT_STATES
    if value is None and state == "present":
        state = "missing"
    if value is not None and not _finite(value):
        value, state = None, "nonfinite"
    return {"value": value if state == "present" else None, "state": state, "unit": unit,
            "inputs": deepcopy(inputs)}


def _gumbel_survival(x, mu, slope):
    """Stable 1-exp(-exp(-lambda*(x-mu))) over finite double inputs."""
    y = slope * (x-mu)
    if y < -7.0:  # exp(-exp(7)) is below binary64 range; survival rounds to one.
        return 1.0
    return -math.expm1(-math.exp(-y))


def _exponential_survival(x, mu, slope):
    return 1.0 if x < mu else math.exp(-slope * (x-mu))


def _fixed_location(values, slope):
    minimum = min(values)
    return minimum - math.log(math.fsum(math.exp(-slope*(x-minimum)) for x in values)/len(values))/slope


def _gumbel_fit(values, tolerance, limit):
    """Translation-stable Lawless ML; safeguarded Newton, explicit finite limit."""
    if len(values) < 2:
        return None, None, "population_insufficient", 0, None
    minimum = min(values)
    z = [x-minimum for x in values]
    mean = math.fsum(z)/len(z)
    variance = math.fsum((x-mean)**2 for x in z)/(len(z)-1)
    if variance == 0:
        return None, None, "constant_population", 0, None
    if not math.isfinite(variance):
        return None, None, "fit_nonfinite", 0, None
    slope = math.pi / math.sqrt(6*variance)
    left, right, residual = 0.0, None, None
    for iteration in range(1, limit+1):
        if not math.isfinite(slope) or slope <= 0:
            return None, None, "fit_nonfinite", iteration, None
        weights = [math.exp(-slope*x) for x in z]
        mass = math.fsum(weights)
        weighted_mean = math.fsum(x*w for x, w in zip(z, weights))/mass
        weighted_var = math.fsum(w*(x-weighted_mean)**2 for x, w in zip(z, weights))/mass
        residual = 1/slope - mean + weighted_mean
        if abs(residual) <= tolerance:
            return _fixed_location(values, slope), slope, None, iteration, residual
        if residual > 0:
            left = slope
        else:
            right = slope
        derivative = -1/(slope*slope) - weighted_var
        candidate = slope - residual/derivative
        if candidate <= left or (right is not None and candidate >= right) or not math.isfinite(candidate):
            candidate = (left+right)/2 if right is not None else slope*2
        slope = candidate
    return None, None, "fit_failed", limit, residual


def calculate_hmmsim_components(sheet, *, parameters=None):
    """Calculate inspectable quantities; never acquire, execute or mutate inputs.

    Parameters: tail_masses (Forward; otherwise the native full-population fit),
    fixed_lambda, fit_tolerance (absolute Lawless equation residual in bits),
    solver_iteration_limit, rounding_tolerance (absolute, in each quantity's
    units), and filter_criterion={threshold,meaning,comparison,fit_variant}.
    Meaning is score or survival_probability. Fit variants are independent,
    fixed_lambda, native_lambda or native_calibration. Forward tail variants
    are returned separately per tail; native_calibration uses full-population
    origins. Native filtering is reconstructed only with its recorded criterion.
    All printed-parameter calibration residual checks remain explicitly unknown
    because the unrounded native calibration parameters were not exported.
    """
    operation = sheet.get("operation") if isinstance(sheet, dict) else None
    result = {"schema": SCHEMA, "operation": deepcopy(operation), "parameters": {},
              "rows": [], "checks": [], "issues": []}

    def issue(code, key=None, field=None, **details):
        assert code in ISSUE_CODES
        result["issues"].append({"code": code, "stage": "calculation", "record_key": key,
                                 "field": field, "details": details})

    if (not isinstance(sheet, dict) or sheet.get("schema") != SHEET_SCHEMA or
            not isinstance(operation, dict) or not isinstance(operation.get("settings"), dict) or
            not isinstance(sheet.get("native_rows"), list) or not isinstance(sheet.get("input_records"), list)):
        issue("sheet_invalid")
        return result
    if parameters is not None and (not isinstance(parameters, dict) or set(parameters)-_PARAMETER_FIELDS):
        issue("parameters_invalid")
        result["parameters"] = deepcopy(parameters)
        return result
    p = {**DEFAULT_PARAMETERS, **deepcopy(parameters or {})}
    mode, settings = operation.get("mode"), operation["settings"]
    if "tail_masses" not in p:
        masses, error = recorded_tail_masses(settings) if mode == "forward" else ([1.0], None)
        p["tail_masses"] = masses
        if error:
            issue(error, field="tail_masses")
    p.setdefault("filter_criterion", None)
    result["parameters"] = p
    invalid_parameters = False
    for field in ("fixed_lambda", "fit_tolerance", "rounding_tolerance"):
        if not _finite(p[field]) or p[field] <= 0:
            issue("parameter_invalid", field=field)
            invalid_parameters = True
    if type(p["solver_iteration_limit"]) is not int or p["solver_iteration_limit"] <= 0:
        issue("parameter_invalid", field="solver_iteration_limit")
        invalid_parameters = True
    if p["tail_masses"] is not None and (not isinstance(p["tail_masses"], list) or not p["tail_masses"] or
            any(not _finite(t) or not 0 < t <= 1 for t in p["tail_masses"])):
        issue("tail_schedule_invalid", field="tail_masses")
        invalid_parameters = True
    elif mode != "forward" and p["tail_masses"] != [1.0]:
        issue("parameter_invalid", field="tail_masses", reason="gumbel_complete_fit_uses_the_full_population")
        invalid_parameters = True
    criterion = p["filter_criterion"]
    if criterion is not None and (not isinstance(criterion, dict) or
            set(criterion) != {"threshold", "meaning", "comparison", "fit_variant"} or
            not _finite(criterion.get("threshold")) or criterion.get("meaning") not in {"score", "survival_probability"} or
            criterion.get("comparison") not in _OPS or
            criterion.get("fit_variant") not in {"independent", "fixed_lambda", "native_lambda", "native_calibration"} or
            (criterion.get("meaning") == "survival_probability" and not 0 <= criterion["threshold"] <= 1)):
        issue("filter_criterion_invalid", field="filter_criterion")
        invalid_parameters = True
    if invalid_parameters:
        return result
    native_rows = sheet["native_rows"]
    if any(not isinstance(r, dict) or not all(k in r for k in ("kind", "record_key", "model_keys", "payload", "locator"))
           or not isinstance(r["payload"], dict) or not isinstance(r["model_keys"], list) for r in native_rows):
        issue("sheet_invalid", field="native_rows")
        return result

    def add(kind, sources, model_keys, components, details=None):
        row = {"kind": kind, "record_key": "calculation/" + str(len(result["rows"])),
               "source_record_keys": [s["record_key"] for s in sources], "model_keys": deepcopy(model_keys),
               "components": components, "details": details or {}}
        result["rows"].append(row)
        return row

    def check(name, sources, state, **details):
        result["checks"].append({"name": name, "source_record_keys": [s["record_key"] for s in sources],
                                 "state": state, "details": details})

    def native_component(row, field, unit=None):
        payload = row["payload"]
        value = payload.get("values", {}).get(field)
        state = payload.get("states", {}).get(field, "missing")
        state = state if state in COMPONENT_STATES else "incompatible"
        if not row["model_keys"]:
            state = "incompatible"
        return _component(value, unit or SUMMARY_UNITS.get(field, "dimensionless"),
                          [_input(row["record_key"], "payload.values."+field)], state)

    summaries = [r for r in native_rows if r["kind"] == "summary"]
    for summary in summaries:
        add("native_summary", [summary], summary["model_keys"],
            {field: native_component(summary, field) for field in summary["payload"].get("values", {})},
            {"origin": "native_printed", "pmu_status": summary["payload"].get("states", {}).get("pmu"),
             "uncertainty": "native_fit_uncertainty_not_reported"})

    def calibration(model_keys, key):
        candidates = [s for s in summaries if s["model_keys"] == model_keys and model_keys]
        if not candidates:
            issue("calibration_missing", key)
            return None, None, None
        pairs = {(s["payload"].get("values", {}).get("pmu"), s["payload"].get("values", {}).get("plambda")) for s in candidates}
        # Forward repeats the same calibration on its selected tail rows. More
        # than one summary artifact is not an authoritative single calibration.
        occurrences = {s["locator"]["occurrence_id"] for s in candidates}
        if len(pairs) != 1 or len(occurrences) != 1:
            issue("calibration_ambiguous", key)
            return None, None, None
        source = candidates[0]
        mu, slope = next(iter(pairs))
        if not _finite(slope) or slope <= 0 or source["payload"].get("states", {}).get("plambda") != "present":
            issue("calibration_invalid", key, "plambda")
            return None, None, source
        if mode == "hybrid":
            issue("calibration_undetermined", key, "pmu")
            return None, slope, source
        if not _finite(mu) or source["payload"].get("states", {}).get("pmu") != "present":
            issue("calibration_invalid", key, "pmu")
            return None, slope, source
        return mu, slope, source

    def residuals(fitrow, summary, mapping, *, comparable=True, qualification=None):
        comps = {}
        for computed, field in mapping.items():
            calc = fitrow["components"].get(computed)
            native = native_component(summary, field)
            operands = (calc["inputs"] if calc else []) + native["inputs"]
            if calc and calc["state"] == native["state"] == "present":
                residual = calc["value"] - native["value"]
                comps[field] = _component(residual, calc["unit"], operands)
                passed = abs(residual) <= p["rounding_tolerance"]
                check("native_rounding."+field, [summary], ("pass" if passed else "fail") if comparable else "unknown",
                      residual=residual, tolerance=p["rounding_tolerance"],
                      qualification=None if comparable else qualification or "calibration_inputs_are_printed_rounded_values")
                if comparable and not passed:
                    issue("native_rounding_difference", summary["record_key"], field, residual=residual)
            else:
                comps[field] = _component(None, native["unit"], operands,
                                         calc["state"] if calc and calc["state"] != "present" else native["state"])
        add("native_rounding_residuals", [summary], fitrow["model_keys"], comps,
            {"fit_record_key": fitrow["record_key"], "comparable": comparable})

    score_rows = [r for r in native_rows if r["kind"] == "scores"]
    for model in sheet["input_records"]:
        key = model.get("record_key")
        if not any(r["model_keys"] == [key] for r in score_rows):
            issue("score_vector_missing", key)
            add("score_statistics", [], [key], {field: _component(None, unit, [], "missing") for field, unit in
                (("observed_count", "sequence"), ("mean", "bit"), ("min", "bit"), ("max", "bit"),
                 ("sample_variance", "bit_squared"), ("x10", "bit"))}, {"population": "missing"})

    for source in score_rows:
        key, model_keys, data = source["record_key"], source["model_keys"], source["payload"]
        values, n = data.get("values"), data.get("declared_population")
        operands = [_input(key, "payload.values")]
        ninputs = [_input(key, "payload.declared_population")]
        state = "present"
        if data.get("representation") == "printed_3_decimal":
            state = "incompatible"
            issue("score_vector_rounded", key)
        elif not model_keys:
            state = "incompatible"
            issue("source_association_unresolved", key)
        elif values is None:
            state = "missing"
        elif not isinstance(values, list) or any(not _finite(x) for x in values):
            state = "nonfinite"
            issue("score_vector_invalid", key)
        elif type(n) is not int or n <= 0:
            state = "incompatible"
            issue("score_vector_invalid", key, "declared_population")
        elif data.get("completeness") != "complete" or len(values) != n or data.get("observed_count") != len(values):
            state = "incomplete"
            issue("score_vector_incomplete", key)
        if state == "present" and not values:
            state = "missing"
        statistics = {
            "observed_count": _component(len(values) if isinstance(values, list) else None, "sequence", [_input(key, "payload.values")]),
            "declared_population": _component(n, "sequence", ninputs),
        }
        x10, mean = None, None
        if state == "present":
            try:
                mean = math.fsum(values)/len(values)
                variance = math.fsum((x-mean)**2 for x in values)/(len(values)-1) if len(values) > 1 else None
                x10 = sorted(values, reverse=True)[9] if len(values) >= 10 else None
                for field, value, unit in (("mean", mean, "bit"), ("min", min(values), "bit"), ("max", max(values), "bit"),
                                           ("sample_variance", variance, "bit_squared"), ("x10", x10, "bit")):
                    statistics[field] = _component(value, unit, operands)
            except (OverflowError, ValueError):
                state = "nonfinite"
            if len(values) < 10:
                issue("population_insufficient", key, "x10", required=10, actual=len(values))
        if state != "present":
            for field in ("mean", "min", "max", "sample_variance", "x10"):
                statistics[field] = _component(None, "bit_squared" if field == "sample_variance" else "bit", operands, state)
        add("score_statistics", [source], model_keys, statistics,
            {"sample_variance_denominator": len(values)-1 if isinstance(values, list) and values else None,
             "population": "generated_model_scores", "independence": "not_established",
             "representation": data.get("representation")})

        pmu, plambda, cal_source = calibration(model_keys, key)
        cal_inputs = ([_input(cal_source["record_key"], "payload.values."+f) for f in ("pmu", "plambda")]
                      if cal_source else [])
        relevant = [s for s in summaries if model_keys and s["model_keys"] == model_keys]
        masses = p["tail_masses"] if mode == "forward" else [1.0]
        if mode not in {"viterbi", "msv", "hybrid", "forward"}:
            issue("sheet_invalid", key, "mode")
            continue
        fits = []
        for tail_index, tail_mass in enumerate(masses or []):
            fitstate, error, count, mu, slope, iterations, equation_residual = state, None, None, None, None, 0, None
            tail = None
            try:
                if state == "present":
                    count = math.floor(n * tail_mass) if mode == "forward" else n
                    tail = sorted(values)[-count:] if count else []
                    if mode == "forward":
                        if not tail:
                            error = "empty_tail"
                        else:
                            mu = min(tail)
                            offset_mean = math.fsum(x-mu for x in tail)/len(tail)
                            if offset_mean == 0:
                                error = "constant_population"
                            else:
                                slope = 1/offset_mean
                                if not _finite(slope) or slope <= 0:
                                    error = "fit_nonfinite"
                    else:
                        mu, slope, error, iterations, equation_residual = _gumbel_fit(values, p["fit_tolerance"], p["solver_iteration_limit"])
                    if error:
                        fitstate = "nonfinite" if error == "fit_nonfinite" else "failed"
                        issue(error, key, "fit", tail_mass=tail_mass)
            except (OverflowError, ValueError, ZeroDivisionError):
                fitstate = "nonfinite"
                issue("fit_nonfinite", key, "fit", tail_mass=tail_mass)
            tail_inputs = operands + [_input(None, "parameters.tail_masses."+str(tail_index))]
            fit_inputs = tail_inputs + [_input(None, "parameters.fit_tolerance"), _input(None, "parameters.solver_iteration_limit")]
            family = "exponential" if mode == "forward" else "gumbel"
            variants = [("independent", mu, slope, fitstate, fit_inputs)]
            fixed_mu = None
            try:
                if state == "present":
                    fixed_mu = min(tail) if mode == "forward" and tail else (
                        _fixed_location(values, p["fixed_lambda"]) if mode != "forward" and len(values) > 1 else None)
            except (ValueError, OverflowError, ZeroDivisionError):
                pass
            fixed_state = state if state != "present" else ("present" if fixed_mu is not None else "failed")
            variants.append(("fixed_lambda", fixed_mu, p["fixed_lambda"], fixed_state,
                             tail_inputs + [_input(None, "parameters.fixed_lambda")]))
            if mode != "forward":
                mu2 = None
                if state == "present" and len(values) > 1 and plambda is not None:
                    try:
                        mu2 = _fixed_location(values, plambda)
                    except (ValueError, OverflowError, ZeroDivisionError):
                        pass
                variants.append(("native_lambda", mu2, plambda,
                                 state if state != "present" else "present" if mu2 is not None else "missing",
                                 operands + ([_input(cal_source["record_key"], "payload.values.plambda")] if cal_source else [])))
            variants.append(("native_calibration", pmu, plambda,
                "incompatible" if mode == "hybrid" else state if state != "present" else
                "present" if pmu is not None and plambda is not None else "missing", operands + cal_inputs))
            for variant, vmu, vslope, vstate, vinputs in variants:
                survival, expected = None, None
                effective_mass = 1.0 if variant == "native_calibration" or mode != "forward" else tail_mass
                if vstate == "present" and (not _finite(vmu) or not _finite(vslope) or vslope <= 0):
                    vstate = "nonfinite"
                if vstate == "present" and x10 is not None:
                    survival = (_exponential_survival if family == "exponential" else _gumbel_survival)(x10, vmu, vslope)
                    expected = n * effective_mass * survival
                mass_inputs = [_input(None, "parameters.tail_masses."+str(tail_index))]
                selection_inputs = operands+ninputs+mass_inputs if mode == "forward" else operands
                if variant == "native_calibration":
                    mu_inputs = [_input(cal_source["record_key"], "payload.values.pmu")] if cal_source else []
                    slope_inputs = [_input(cal_source["record_key"], "payload.values.plambda")] if cal_source else []
                elif variant == "native_lambda":
                    slope_inputs = [_input(cal_source["record_key"], "payload.values.plambda")] if cal_source else []
                    mu_inputs = operands+slope_inputs
                elif variant == "fixed_lambda":
                    slope_inputs = [_input(None, "parameters.fixed_lambda")]
                    mu_inputs = selection_inputs if mode == "forward" else operands+slope_inputs
                else:
                    mu_inputs = selection_inputs + ([] if mode == "forward" else
                        [_input(None, "parameters.fit_tolerance"), _input(None, "parameters.solver_iteration_limit")])
                    slope_inputs = mu_inputs
                survival_inputs = operands+mu_inputs+slope_inputs
                comp = {"mu": _component(vmu, "bit", mu_inputs, vstate),
                        "lambda": _component(vslope, "inverse_bit", slope_inputs, vstate),
                        "survival_at_x10": _component(survival, "dimensionless", survival_inputs, vstate if x10 is not None else "missing"),
                        "E10": _component(expected, "sequence", survival_inputs+ninputs+
                            (mass_inputs if mode == "forward" and variant != "native_calibration" else []), vstate if x10 is not None else "missing"),
                        "tail_mass": _component(tail_mass, "dimensionless", mass_inputs),
                        "tail_count": _component(count, "sequence", ninputs+(mass_inputs if mode == "forward" else []), state),
                        "tail_threshold": _component(min(tail) if tail else None, "bit", selection_inputs, state)}
                fitrow = add("fit", [source] + ([cal_source] if cal_source and variant in {"native_lambda", "native_calibration"} else []),
                    model_keys, comp, {"variant": variant, "family": family, "tail_ordinal": tail_index,
                        "expectation_population_mass": effective_mass,
                        "iterations": iterations if variant == "independent" else None,
                        "lawless_residual": equation_residual if variant == "independent" else None,
                        "calibration_precision": "printed_rounded" if variant in {"native_lambda", "native_calibration"} else None,
                        "fit_uncertainty": "not_estimated"})
                fits.append((fitrow, vmu, vslope, vstate, effective_mass))
                matching = [s for s in relevant if _finite(s["payload"].get("values", {}).get("tailp")) and
                            abs(s["payload"]["values"]["tailp"]-tail_mass) <= 5.00001e-5]
                for summary in matching:
                    fields = ({"mu": "mu", "lambda": "lambda", "E10": "E10"} if variant == "independent" else
                              {"mu": "mufix", "E10": "E10fix"} if variant == "fixed_lambda" else
                              {"mu": "mufix2", "E10": "E10fix2"} if variant == "native_lambda" else {"E10": "E10p"})
                    # Changed parameters remain legitimate new calculations, not
                    # a claim that the original native run used those values.
                    comparable = ((variant == "independent" and (mode == "forward" or p["fit_tolerance"] == 1e-5)) or
                                  (variant == "fixed_lambda" and p["fixed_lambda"] == 0.693147))
                    qualification = ("selected_solver_tolerance_differs_from_native_1e-5" if variant == "independent" else
                                     "selected_fixed_lambda_differs_from_native_0.693147" if variant == "fixed_lambda" else None)
                    residuals(fitrow, summary, fields, comparable=comparable, qualification=qualification)

        native_criterion = None
        threshold = settings.get("--pthresh")
        if _finite(threshold) and 0 <= threshold <= 1 and mode != "forward":
            native_criterion = {"threshold": threshold, "meaning": "survival_probability",
                                "comparison": "<=", "fit_variant": "native_calibration"}
        if mode == "hybrid" and native_criterion is not None and state == "present" and cal_source is not None and plambda is not None:
            # Reproduce the experimental native diagnostic with its actual
            # undetermined zero. This is deliberately not an available fitted
            # or calibrated model variant and cannot satisfy a selected
            # native_calibration criterion.
            native_zero = cal_source["payload"].get("values", {}).get("pmu")
            if native_zero == 0:
                passing = sum(_exponential_survival(x, native_zero, plambda) <= threshold for x in values)
                replay = add("native_experimental_filter_replay", [source, cal_source], model_keys,
                    {"count": _component(passing, "sequence", operands+cal_inputs+[_input(None, "operation.settings.--pthresh")]),
                     "fraction": _component(passing/n, "dimensionless", operands+cal_inputs+ninputs+[_input(None, "operation.settings.--pthresh")])},
                    {"criterion": native_criterion, "family": "exponential", "pmu_status": "undetermined",
                     "calibration_precision": "printed_rounded", "interpretation": "experimental_native_diagnostic_only"})
                for native in [r for r in native_rows if r["kind"] == "filter" and r["model_keys"] == model_keys]:
                    check("hybrid_native_experimental_filter_count", [source, native],
                          "pass" if passing == native["payload"].get("count") else "unknown", calculated=passing,
                          native=native["payload"].get("count"), calculation_record_key=replay["record_key"],
                          qualification="undetermined_zero_location_and_printed_slope")
        selections = [("selected", criterion)] if criterion is not None else []
        if native_criterion is not None:
            selections.append(("native", native_criterion))
        elif any(r["kind"] == "filter" and r["model_keys"] == model_keys for r in native_rows):
            issue("filter_criterion_missing", key)
        for origin, selection in selections:
            candidates = [(r, mu, slope, st, mass) for r, mu, slope, st, mass in fits if r["details"]["variant"] == selection["fit_variant"]]
            if selection["meaning"] == "score":
                candidates = [(None, None, None, state, 1.0)]
            if not candidates:
                issue("filter_variant_unavailable", key, selection["fit_variant"])
                candidates = [(None, None, None, "missing", 1.0)]
            # Calibration is a full-population variant repeated on each Forward
            # tail row; keep one diagnostic, with its explicit same inputs.
            if selection["fit_variant"] == "native_calibration" and candidates:
                candidates = candidates[:1]
            for fitrow, mu, slope, fs, mass in candidates:
                passing = None
                f_inputs = operands + [_input(None, "parameters.filter_criterion" if origin == "selected" else "operation.settings.--pthresh")]
                if fitrow:
                    f_inputs += fitrow["components"]["mu"]["inputs"] + fitrow["components"]["lambda"]["inputs"]
                    if mode == "forward" and selection["fit_variant"] != "native_calibration":
                        f_inputs += fitrow["components"]["tail_mass"]["inputs"]
                if state == fs == "present":
                    if selection["meaning"] == "score":
                        measured = values
                    else:
                        survivor = _exponential_survival if mode == "forward" else _gumbel_survival
                        measured = [mass*survivor(x, mu, slope) for x in values]
                    passing = sum(_OPS[selection["comparison"]](x, selection["threshold"]) for x in measured)
                fstate = state if state != "present" else fs
                calculated = add("filter_recalculation", [source], model_keys,
                    {"count": _component(passing, "sequence", f_inputs, fstate),
                     "fraction": _component(passing/n if passing is not None else None, "dimensionless", f_inputs+ninputs, fstate)},
                    {"origin": origin, "criterion": deepcopy(selection),
                     "fit_record_key": fitrow["record_key"] if fitrow else None,
                     "calibration_precision": "printed_rounded" if selection["fit_variant"] == "native_calibration" else None})
                if origin == "native":
                    for native in [r for r in native_rows if r["kind"] == "filter" and model_keys and r["model_keys"] == model_keys]:
                        observed = native["payload"].get("count")
                        check("native_filter_count", [source, native],
                              "pass" if passing is not None and passing == observed else "unknown",
                              calculated=passing, native=observed, qualification="printed_calibration_parameters_only",
                              calculation_record_key=calculated["record_key"])

    # Alignment occurrences keep their simulation order. Separate files never
    # silently become one larger population, even if all names are identical.
    groups = {}
    for r in native_rows:
        if r["kind"] == "alignments":
            groups.setdefault((r["locator"]["occurrence_id"], tuple(r["model_keys"])), []).append(r)
    n = settings.get("-N")
    for (_, model_keys), rows in groups.items():
        lengths = [r["payload"].get("trace_state_count") for r in rows]
        inputs = [_input(r["record_key"], "payload.trace_state_count") for r in rows]
        state = ("incompatible" if not model_keys or any(r["payload"].get("states", {}).get("trace_state_count") != "present" for r in rows)
                 else "incomplete" if type(n) is not int or len(rows) != n
                 else "nonfinite" if any(not _finite(x) for x in lengths) else "present")
        mean = math.fsum(lengths)/len(lengths) if state == "present" and lengths else None
        sd = math.sqrt(math.fsum((x-mean)**2 for x in lengths)/(len(lengths)-1)) if mean is not None and len(lengths)>1 else None
        calculated = add("alignment_statistics", rows, list(model_keys),
            {"observed_count": _component(len(rows), "sequence", inputs),
             "alignment_mean": _component(mean, "trace_state", inputs, state),
             "alignment_sample_sd": _component(sd, "trace_state", inputs, state)},
            {"count_meaning": "M+D+I_trace_states", "sample_variance_denominator": len(rows)-1})
        if state == "incomplete":
            issue("alignment_population_incomplete", rows[0]["record_key"])
        for summary in summaries:
            if summary["model_keys"] == list(model_keys):
                residuals(calculated, summary, {"alignment_mean": "almean", "alignment_sample_sd": "alsd"})
        vectors = [r for r in score_rows if r["model_keys"] == list(model_keys) and r["payload"].get("representation") == "native_binary64"]
        if len(vectors) == 1 and isinstance(vectors[0]["payload"].get("values"), list):
            vector = vectors[0]["payload"]["values"]
            for r in rows:
                i, printed = r["payload"].get("sample_ordinal"), r["payload"].get("score")
                if type(i) is int and i < len(vector) and _finite(vector[i]) and _finite(printed):
                    delta = vector[i]-printed
                    # The native alignment file prints three decimals, regardless
                    # of the four-decimal summary rounding tolerance.
                    if abs(delta) > 0.000500001:
                        issue("alignment_score_difference", r["record_key"], "score", residual=delta)
            check("alignment_score_correspondence", [vectors[0], *rows],
                  "fail" if any(i["code"] == "alignment_score_difference" and i["record_key"] in {r["record_key"] for r in rows}
                                 for i in result["issues"]) else "pass")

    for r in native_rows:
        if r["kind"] != "filter":
            continue
        data, key = r["payload"], r["record_key"]
        count, denominator, fraction = data.get("count"), data.get("denominator"), data.get("fraction")
        operands = [_input(key, "payload.count"), _input(key, "payload.denominator")]
        state = ("incompatible" if not r["model_keys"] or data.get("states", {}).get("count") != "present" else
                 "missing" if denominator is None else "present" if type(denominator) is int and denominator>0
                 and type(count) is int and 0<=count<=denominator else "incompatible")
        value = count/denominator if state == "present" else None
        delta = value-fraction if value is not None and _finite(fraction) else None
        add("native_filter", [r], r["model_keys"],
            {"count": _component(count, "sequence", [_input(key, "payload.count")], state),
             "fraction": _component(value, "dimensionless", operands, state),
             "rounding_residual": _component(delta, "dimensionless", operands+[_input(key, "payload.fraction")], state)},
            {"criterion_status": "native_experimental_undetermined_calibration" if mode == "hybrid" else
             "native_forward_filter_unavailable" if mode == "forward" else "native_calibration"})
        check("native_filter_fraction", [r], "unknown" if delta is None else
              "pass" if abs(delta)<=p["rounding_tolerance"] else "fail", residual=delta)
    return result
