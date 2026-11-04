"""Saved-data calculations for Infernal model preparation and inspection.

CM effective count D=(Z_nt/calibration_dbsize_nt)*random_hit_count. The
exponential inverse is mu-log(E/D)/lambda (or mu-log(P)/lambda); survival
is D*exp(-lambda*max(0,score-mu)). HMM Forward uses D=Z_nt/MAXL and its
own fit. Native HMM P conversions use the native exponential inverse for each
separately recorded fit. These are model calibration statistics, not biological
confidence. Missing fit, denominator or provenance remains unavailable.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import math
import re

from .infernal_preparation_schema import (
    check, field_input, issue, new_calculations, require_finite_json,
    validate_common_sheet, value,
)
from .infernal_preparation_statistics import (
    CM_ALGORITHMS, IDENTITY_FIELDS, ROW_FIELDS, VALUE_FIELDS, VALUE_UNITS,
)


COMPONENT_UNITS = {
    "paired_consensus_fraction": "fraction", "paired_consensus_numerator": "nt",
    "consensus_length_denominator": "nt", "mu_extrap_calculated": "bit", "mu_extrap_residual": "bit",
    "actual_calibration_nt": "nt", "partition_chunk_count": "count", "total_calibration_chunk_count": "count", "predicted_seconds": "second",
    "predicted_bytes": "byte", "effective_random_hit_count": "expected_count", "score_at_evalue": "bit",
    "score_at_pvalue": "bit", "evalue_at_score": "expected_count", "native_conversion_residual": "bit",
    "native_rounding_half_width": "bit",
}
COMPONENT_NAMES = frozenset(COMPONENT_UNITS)
PARAMETER_NAMES = frozenset({"search_space_mb", "evalue", "pvalue", "score_bits", "rounding_absolute_tolerance",
    "requested_megabases", "partition_index", "partition_count", "partition_requests"})
CHECK_NAMES = frozenset({"paired_topology_coherent", "build_header_counts_consistent", "summary_header_counts_consistent",
    "build_population_complete", "calibration_fit_consistent", "calibration_length_consistent",
    "calibration_stdout_consistent", "native_conversion_consistent", "native_cutoff_consistent",
    "model_reference_valid", "partition_score_count_consistent", "partition_request_binding",
    "partition_population_complete", "partition_settings_consistent", "partition_merged_hit_counts",
    "split_command_count_consistent", "training_alignment_complete"})
ISSUE_CODES = frozenset("infernal_statistics_calculation_"+s for s in (
    "domain_invalid", "overflow", "underflow", "model_reference_invalid", "native_mismatch", "header_mismatch",
    "partition_request_missing", "partition_request_mismatch", "partition_population_invalid",
    "partition_settings_mismatch", "partition_seed_unknown", "partition_gc_identity_unknown", "partition_hit_count_mismatch",
))


def _parameters(parameters):
    if type(parameters) is not dict or set(parameters)-PARAMETER_NAMES:
        raise ValueError("infernal_statistics_parameters_invalid")
    require_finite_json(parameters)
    for name, item in parameters.items():
        if name == "partition_requests":
            if type(item) is not list:
                raise ValueError("infernal_statistics_partition_requests_invalid")
            fields = {"artifact_ref", "source_model_artifact_ref", "source_model_sha256", "partition_index",
                      "partition_count", "requested_megabases", "settings"}
            for req in item:
                if type(req) is not dict or set(req) != fields:
                    raise ValueError("infernal_statistics_partition_request_fields")
                if any(type(req[k]) is not str or not req[k] for k in ("artifact_ref", "source_model_artifact_ref")):
                    raise ValueError("infernal_statistics_partition_request_reference")
                if type(req["source_model_sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", req["source_model_sha256"]):
                    raise ValueError("infernal_statistics_partition_source_digest")
                if any(type(req[k]) is not int or req[k] < 1 for k in ("partition_index", "partition_count")):
                    raise ValueError("infernal_statistics_partition_index")
                if req["partition_index"] > req["partition_count"]:
                    raise ValueError("infernal_statistics_partition_index")
                if type(req["requested_megabases"]) not in (int, float) or not math.isfinite(req["requested_megabases"]) or req["requested_megabases"] <= 0:
                    raise ValueError("infernal_statistics_partition_length")
                if type(req["settings"]) is not dict or any(type(k) is not str or not k.startswith("-") or
                    type(v) not in (str, int, float, bool) for k, v in req["settings"].items()):
                    raise ValueError("infernal_statistics_partition_settings")
            continue
        if type(item) not in (int, float) or not math.isfinite(item):
            raise ValueError("infernal_statistics_parameter_number")
        if name in {"partition_index", "partition_count"} and (type(item) is not int or item < 1):
            raise ValueError("infernal_statistics_parameter_positive_integer")
        if name in {"search_space_mb", "evalue", "pvalue", "requested_megabases"} and item <= 0:
            raise ValueError("infernal_statistics_parameter_positive")
        if name == "pvalue" and item > 1:
            raise ValueError("infernal_statistics_pvalue_range")
        if name == "rounding_absolute_tolerance" and item < 0:
            raise ValueError("infernal_statistics_tolerance_negative")
    if all(k in parameters for k in ("partition_index", "partition_count")) and parameters["partition_index"] > parameters["partition_count"]:
        raise ValueError("infernal_statistics_partition_index")


def _inputs(*cells):
    result = []
    for cell in cells:
        for source in cell["inputs"]:
            if source not in result:
                result.append(deepcopy(source))
    return result


def _present(*cells):
    return all(c["state"] == "present" for c in cells)


def _missing(unit, *cells):
    priority = ("invalid", "failed", "truncated", "incompatible", "missing", "not_measured")
    state = next((s for s in priority if any(c["state"] == s for c in cells)), "missing")
    return value(state=state, basis="derived", unit=unit, inputs=_inputs(*cells))


def _issue(result, code, row, field=None):
    result["issues"].append(issue("infernal_statistics_calculation_"+code, stage="calculation",
        artifact_ref=row["locator"]["artifact_ref"], record_key=row["record_key"], field=field))


def _derived(number, unit, cells, result, row, field):
    try:
        finite = math.isfinite(number)
    except OverflowError:
        finite = False
    if not finite:
        _issue(result, "overflow", row, field)
        return value(state="invalid", basis="derived", unit=unit, inputs=_inputs(*cells))
    return value(number, basis="derived", unit=unit, inputs=_inputs(*cells))


def _half(cell):
    """Native formatter precision, including suppressed trailing %g zeros."""
    token = cell["native_token"]
    if cell["state"] != "present" or token is None or type(cell["value"]) is int:
        return 0.0
    if cell["basis"] == "native_reported" and any(i["field"].rsplit(".",1)[-1] in {"evalue", "pvalue"} for i in cell["inputs"]):
        # cmstat uses C %g (six significant digits), even when it omits zero
        # decimals. Treating a printed 1 as rounded to .5 is incorrect here.
        return 0.0 if cell["value"] == 0 else 0.5*10.0**(math.floor(math.log10(abs(cell["value"]))) - 5)
    try:
        result = float(Decimal(10) ** Decimal(Decimal(token).as_tuple().exponent) / 2)
    except (InvalidOperation, ValueError, OverflowError):
        return 0.0
    if cell["basis"] == "derived" and cell["unit"] == "nt" and any(i["field"] == "search_space_nt" for i in cell["inputs"]):
        result *= 1e6
    return result if math.isfinite(result) else 0.0


def _within(a, b, tolerance=0):
    if not _present(a, b):
        return "unknown"
    return "pass" if abs(a["value"]-b["value"]) <= _half(a)+_half(b)+tolerance else "fail"


def _parameter(parameters, name, operation, flag, row, field, unit, *, multiplier=1):
    if name in parameters:
        number = parameters[name]*multiplier
        return value(number if math.isfinite(number) else None, state="present" if math.isfinite(number) else "invalid", basis="derived", unit=unit)
    if flag in operation["settings"]:
        setting = operation["settings"][flag]
        if type(setting) not in (int, float):
            return value(state="invalid", basis="derived", unit=unit)
        number = setting*multiplier
        return value(number if math.isfinite(number) else None, state="present" if math.isfinite(number) else "invalid", basis="derived", unit=unit)
    return deepcopy(row["values"].get(field, value(state="missing", unit=unit)))


def _row_result(row):
    return {"record_key": row["record_key"], "components": {
        name: value(state="incompatible", basis="derived", unit=unit) for name, unit in COMPONENT_UNITS.items()}, "checks": []}


def _model(row, models, result, target):
    keys = row["model_keys"]
    model = models.get(keys[0]) if len(keys) == 1 else None
    ok = model is not None and model["content_validation"] == "parsed_headers_and_boundaries"
    if ok and row["identity"].get("name") is not None:
        ok = model["name"] == row["identity"]["name"]
    if ok and "accession" in row["identity"]:
        ok = model["accession"] == row["identity"]["accession"]
    target["checks"].append(check("model_reference_valid", "pass" if ok else "unknown" if not keys else "fail",
                                   [field_input(row["locator"], "model_keys")]))
    if keys and not ok:
        _issue(result, "model_reference_invalid", row)
    return model if ok else None


def _paired(row, target, result):
    vals = row["values"]
    bps, length = vals["base_pairs"], vals["consensus_length"]
    out = target["components"]
    out["consensus_length_denominator"] = deepcopy(length)
    out["paired_consensus_numerator"] = _missing("nt", bps)
    out["paired_consensus_fraction"] = _missing("fraction", bps, length)
    if bps["state"] == "present":
        out["paired_consensus_numerator"] = _derived(2*bps["value"], "nt", [bps], result, row, "paired_consensus_numerator")
    coherent = None
    if _present(bps, length):
        coherent = type(bps["value"]) is int and bps["value"] >= 0 and length["value"] > 0 and 2*bps["value"] <= length["value"]
        if coherent:
            out["paired_consensus_fraction"] = _derived(2*bps["value"]/length["value"], "fraction", [bps, length], result, row, "paired_consensus_fraction")
        else:
            out["paired_consensus_fraction"] = value(state="invalid", basis="derived", unit="fraction", inputs=_inputs(bps, length))
            _issue(result, "domain_invalid", row, "paired_consensus_fraction")
    target["checks"].append(check("paired_topology_coherent", "unknown" if coherent is None else "pass" if coherent else "fail", _inputs(bps, length)))


def _header_checks(row, model, target, result, tolerance):
    if model is None:
        return
    pairs = [(row["values"][k], model["fields"][tag]) for k, tag in
             (("nseq", "NSEQ"), ("consensus_length", "CLEN"))]
    family = row["identity"].get("model_family", "cm")
    eff = model["fields"]["EFFN"] if family == "cm" else (model["filter_hmm"] or {"fields": {}})["fields"].get("EFFN", value())
    pairs.append((row["values"]["eff_nseq"], eff))
    if family == "cm":
        pairs.extend((row["values"][k], model["topology"][tag]) for k, tag in
                     (("base_pairs", "base_pair_nodes"), ("bifurcations", "bifurcation_nodes")))
    if row["kind"] == "model_statistic":
        pairs.append((row["values"]["max_hit_length"], model["fields"]["W"]))
    outcomes = [_within(a, b, tolerance) for a, b in pairs]
    outcome = "fail" if "fail" in outcomes else "unknown" if "unknown" in outcomes else "pass"
    target["checks"].append(check("build_header_counts_consistent" if row["kind"] == "build" else "summary_header_counts_consistent",
                                  outcome, _inputs(*(c for pair in pairs for c in pair))))
    if outcome == "fail":
        _issue(result, "header_mismatch", row)


def _chunks(length):
    if length["state"] != "present" or length["value"] <= 0:
        return None
    number = length["value"]*100
    if not math.isfinite(number):
        return None
    return math.floor(number+0.5)


def _calibration(row, target, model, operation, parameters, result, tolerance):
    values = row["values"]
    out = target["components"]
    lam, mu, tail, reported = (values[k] for k in ("lambda", "mu_orig", "tail_probability_mass", "mu_extrap"))
    out["actual_calibration_nt"] = deepcopy(values["calibration_dbsize_nt"])
    out["mu_extrap_calculated"] = _missing("bit", lam, mu, tail)
    out["mu_extrap_residual"] = _missing("bit", lam, mu, tail, reported)
    if row["identity"]["source"] == "stdout" and model:
        fits = [f for f in model["calibration"].values() if f and f["algorithm"] == row["identity"]["algorithm"]]
        if len(fits) == 1:
            pairs = [(values[k], fits[0][k]) for k in ("lambda", "mu_orig", "random_hit_count")]
            outcomes = [_within(a, b, tolerance) for a, b in pairs]
            status = "fail" if "fail" in outcomes else "unknown" if "unknown" in outcomes else "pass"
            target["checks"].append(check("calibration_stdout_consistent", status, _inputs(*(c for pair in pairs for c in pair))))
            if status == "fail":
                _issue(result, "native_mismatch", row)
    if _present(lam, mu, tail):
        if lam["value"] <= 0 or not 0 < tail["value"] <= 1:
            _issue(result, "domain_invalid", row, "mu_extrap_calculated")
            out["mu_extrap_calculated"] = value(state="invalid", basis="derived", unit="bit", inputs=_inputs(lam, mu, tail))
        else:
            expected = mu["value"]+math.log(tail["value"])/lam["value"]
            out["mu_extrap_calculated"] = _derived(expected, "bit", [lam, mu, tail], result, row, "mu_extrap_calculated")
            if reported["state"] == "present" and math.isfinite(expected):
                out["mu_extrap_residual"] = _derived(expected-reported["value"], "bit", [lam, mu, tail, reported], result, row, "mu_extrap_residual")
                # All printed input precisions contribute to this consistency
                # interval; a rounded lambda is not an exact hidden fit.
                lo_lam, lo_tail = lam["value"]-_half(lam), tail["value"]-_half(tail)
                if lo_lam > 0 and lo_tail > 0:
                    lo = mu["value"]-_half(mu)+math.log(lo_tail)/lo_lam
                    hi = mu["value"]+_half(mu)+math.log(min(1, tail["value"]+_half(tail)))/(lam["value"]+_half(lam))
                    status = "pass" if lo-tolerance <= reported["value"]+_half(reported) and hi+tolerance >= reported["value"]-_half(reported) else "fail"
                else:
                    status = "unknown"
                target["checks"].append(check("calibration_fit_consistent", status, _inputs(lam, mu, tail, reported)))
                if status == "fail":
                    _issue(result, "native_mismatch", row, "mu_extrap")
    requested = _parameter(parameters, "requested_megabases", operation, "-L", row, "requested_megabases", "Mnt")
    chunks = _chunks(requested)
    out["total_calibration_chunk_count"] = _missing("count", requested)
    if chunks is not None:
        out["total_calibration_chunk_count"] = value(chunks, basis="derived", unit="count", inputs=_inputs(requested))
    elif requested["state"] == "present":
        _issue(result, "overflow", row, "total_calibration_chunk_count")
        out["total_calibration_chunk_count"] = value(state="invalid", basis="derived", unit="count", inputs=_inputs(requested))
    if chunks is not None and values["calibration_dbsize_nt"]["state"] == "present":
        expected = chunks*10000
        status = "pass" if expected == values["calibration_dbsize_nt"]["value"] else "fail"
        target["checks"].append(check("calibration_length_consistent", status, _inputs(requested, values["calibration_dbsize_nt"])))
        if status == "fail":
            _issue(result, "native_mismatch", row, "calibration_dbsize_nt")


def _fit(model, algorithm):
    if model is None:
        return None
    if algorithm in CM_ALGORITHMS:
        fits = [f for f in model["calibration"].values() if f and f["algorithm"] == algorithm]
        return fits[0] if len(fits) == 1 else None
    if algorithm == "hmm_glocal_forward":
        return model["efp7gf"]
    native = {"hmm_local_forward": ("LOCAL", "FORWARD"), "hmm_local_viterbi": ("LOCAL", "VITERBI")}.get(algorithm)
    if native and model["filter_hmm"]:
        fits = [s for s in model["filter_hmm"]["stats"] if (s["mode"], s["algorithm"]) == native]
        return fits[0] if len(fits) == 1 else None
    return None


def _conversion_interval(component, mu, lam, e, p, score, d_cells, family):
    """Bounds implied by original printed precisions, not an acceptance score."""
    mus = (mu["value"]-_half(mu), mu["value"]+_half(mu))
    lambdas = (lam["value"]-_half(lam), lam["value"]+_half(lam))
    if lambdas[0] <= 0:
        return None
    ds = (None,)
    if component != "score_at_pvalue":
        if not _present(*d_cells) or len(d_cells) < 2:
            return None
        z, size = d_cells[:2]
        if z["value"]-_half(z) <= 0 or size["value"]-_half(size) <= 0:
            return None
        ds = ((z["value"]-_half(z))/(size["value"]+_half(size)),
              (z["value"]+_half(z))/(size["value"]-_half(size)))
        if family == "cm":
            count = d_cells[2]
            ds = (ds[0]*(count["value"]-_half(count)), ds[1]*(count["value"]+_half(count)))
        if ds[0] <= 0:
            return None
    selected = e if component == "score_at_evalue" else p if component == "score_at_pvalue" else score
    if selected["state"] != "present":
        return None
    xs = (selected["value"]-_half(selected), selected["value"]+_half(selected))
    if component == "score_at_pvalue":
        xs = (xs[0], min(1, xs[1]))
    if component != "evalue_at_score" and xs[0] <= 0:
        return None
    answers = []
    try:
        for m in mus:
            for l in lambdas:
                for x in xs:
                    for d in ds:
                        if component == "score_at_evalue":
                            answers.append(m-(math.log(x)-math.log(d))/l)
                        elif component == "score_at_pvalue":
                            answers.append(m-math.log(x)/l)
                        else:
                            answers.append(math.exp(math.log(d)-l*max(0,x-m)))
    except (ValueError, OverflowError):
        return None
    return (min(answers),max(answers)) if answers and all(math.isfinite(x) for x in answers) else None


def _conversion(row, target, model, operation, parameters, result, tolerance):
    out = target["components"]
    algorithm = row["identity"]["algorithm"]
    family = row["identity"]["model_family"]
    mode = row["identity"]["mode"]
    if family == "hmm" and (algorithm == "hmm_glocal_viterbi" or (algorithm != "hmm_local_forward" and mode != "scores_at_pvalue")):
        return
    fit = _fit(model, algorithm)
    for name in ("effective_random_hit_count", "score_at_evalue", "score_at_pvalue", "evalue_at_score", "native_conversion_residual", "native_rounding_half_width"):
        out[name] = value(state="missing", basis="derived", unit=COMPONENT_UNITS[name])
    if fit is None:
        return
    mu, lam = (fit["mu_extrap"], fit["lambda"]) if family == "cm" else (fit["location"], fit["scale"])
    if not _present(mu, lam):
        for name in ("score_at_evalue", "score_at_pvalue", "evalue_at_score"):
            out[name] = _missing(COMPONENT_UNITS[name], mu, lam)
        return
    if lam["value"] <= 0:
        _issue(result, "domain_invalid", row, "lambda")
        for name in ("score_at_evalue", "score_at_pvalue", "evalue_at_score"):
            out[name] = value(state="invalid", basis="derived", unit=COMPONENT_UNITS[name], inputs=_inputs(mu, lam))
        return
    z = _parameter(parameters, "search_space_mb", operation, "-Z", row, "search_space_nt", "nt", multiplier=1e6)
    e = _parameter(parameters, "evalue", operation, "-E", row, "evalue", "expected_count")
    p = _parameter(parameters, "pvalue", operation, "-P", row, "pvalue", "fraction")
    score = _parameter(parameters, "score_bits", operation, "-T", row, "threshold_bits", "bit")
    if mode.startswith("evalues_at_") and mode != "evalues_at_score" and model:
        cutoff = model["fields"][mode[-2:].upper()]
        status = _within(row["values"]["threshold_bits"], cutoff, tolerance)
        target["checks"].append(check("native_cutoff_consistent", status, _inputs(row["values"]["threshold_bits"], cutoff)))
        if status == "fail":
            _issue(result, "native_mismatch", row, "threshold_bits")
        # Recalculation uses the actual reported selected threshold. Header
        # disagreement is retained above, never repaired in-place.
    d = None
    d_cells = [z]
    if family == "cm":
        size, count = fit["calibration_dbsize_nt"], fit["random_hit_count"]
        d_cells += [size, count]
        if _present(z, size, count) and z["value"] > 0 and size["value"] > 0 and count["value"] > 0:
            d = z["value"]/size["value"]*count["value"]
    elif algorithm == "hmm_local_forward" and model["filter_hmm"]:
        size = model["filter_hmm"]["fields"]["MAXL"]
        d_cells += [size]
        if _present(z, size) and z["value"] > 0 and size["value"] > 0:
            d = z["value"]/size["value"]
    if d is not None:
        out["effective_random_hit_count"] = _derived(d, "expected_count", d_cells, result, row, "effective_random_hit_count")
        if not math.isfinite(d) or d <= 0:
            d = None
    if e["state"] == "present" and d is not None:
        if e["value"] > 0:
            answer = mu["value"]-(math.log(e["value"])-math.log(d))/lam["value"]
            out["score_at_evalue"] = _derived(answer, "bit", [mu, lam, e, *d_cells], result, row, "score_at_evalue")
        else:
            _issue(result, "domain_invalid", row, "evalue")
    if p["state"] == "present":
        if 0 < p["value"] <= 1:
            out["score_at_pvalue"] = _derived(mu["value"]-math.log(p["value"])/lam["value"], "bit",
                [mu, lam, p], result, row, "score_at_pvalue")
        else:
            _issue(result, "domain_invalid", row, "pvalue")
    if score["state"] == "present" and d is not None:
        exponent = -lam["value"]*max(0, score["value"]-mu["value"])
        answer = math.exp(math.log(d)+exponent)
        if answer == 0 and d > 0:
            _issue(result, "underflow", row, "evalue_at_score")
            out["evalue_at_score"] = value(state="invalid", basis="derived", unit="expected_count", inputs=_inputs(mu, lam, score, *d_cells))
        else:
            out["evalue_at_score"] = _derived(answer, "expected_count", [mu, lam, score, *d_cells], result, row, "evalue_at_score")
    component, native_field = ("score_at_evalue", "threshold_bits") if mode == "scores_at_evalue" else (
        ("score_at_pvalue", "threshold_bits") if mode == "scores_at_pvalue" else ("evalue_at_score", "evalue"))
    native, calculated = row["values"][native_field], out[component]
    if _present(native, calculated):
        unit = calculated["unit"]
        residual = calculated["value"]-native["value"]
        out["native_conversion_residual"] = _derived(residual, unit, [calculated, native], result, row, "native_conversion_residual")
        out["native_rounding_half_width"] = value(_half(native), basis="derived", unit=unit, inputs=_inputs(native))
        overridden = any(k in parameters for k in ("search_space_mb", "evalue", "pvalue", "score_bits"))
        interval = _conversion_interval(component,mu,lam,e,p,score,d_cells,family)
        status = ("not_applicable" if overridden else "unknown" if interval is None else
                  "pass" if interval[0]-tolerance <= native["value"]+_half(native) and interval[1]+tolerance >= native["value"]-_half(native) else "fail")
        target["checks"].append(check("native_conversion_consistent", status, _inputs(calculated, native)))
        if status == "fail":
            _issue(result, "native_mismatch", row, native_field)


def _partition_checks(sheet, parameters, result, targets):
    rows = [r for r in sheet["native_rows"] if r["kind"] == "partition"]
    if not rows:
        return
    artifacts = {a["artifact_ref"]: a for a in sheet["artifacts"]}
    requests = parameters.get("partition_requests")
    by_artifact = defaultdict(list)
    for req in requests or []:
        by_artifact[req["artifact_ref"]].append(req)
    rows_by_artifact = defaultdict(list)
    for row in rows:
        rows_by_artifact[row["locator"]["artifact_ref"]].append(row)
    ignored = {"--part", "--ptot", "--split", "--merge", "--proot", "--cfile", "--pfile", "--cbash",
               "--cpu", "--nforecast", "--noforecast", "--forecast", "--memreq",
               "--hfile", "--sfile", "--ffile", "--xfile", "--qqfile"}
    signatures = []
    sources = []
    for req in requests or []:
        signatures.append({k: v for k, v in req["settings"].items() if k not in ignored})
        sources.append((req["source_model_artifact_ref"], req["source_model_sha256"], req["requested_megabases"]))
    coherent = bool(requests) and all(s == signatures[0] for s in signatures) and all(s == sources[0] for s in sources)
    selected = {k: v for k, v in sheet["operation"]["settings"].items() if k not in ignored}
    if coherent:
        coherent = all(all(k in signature and signature[k] == v for k, v in selected.items()) for signature in signatures)
    seed_known = bool(requests) and all(type(r["settings"].get("--seed")) is int and r["settings"]["--seed"] > 0 for r in requests)
    gc_unknown = bool(requests) and any("--gc" in r["settings"] for r in requests)
    population = None
    if requests:
        totals = {r["partition_count"] for r in requests}
        complete_partition_set = (len(totals) == 1 and sorted(r["partition_index"] for r in requests) == list(range(1, next(iter(totals))+1)))
        population = (set(rows_by_artifact) == set(by_artifact) and all(len(v) == 1 for v in by_artifact.values()) and
                      (complete_partition_set if sheet["operation"]["mode"] == "merge_scores" else len(requests) == 1))
        for ref, grouped in rows_by_artifact.items():
            request = by_artifact.get(ref, [])
            if len(request) != 1:
                population = False
                continue
            source_ref = request[0]["source_model_artifact_ref"]
            models = [m for m in sheet["input_records"] if m["kind"] == "model" and m["locator"]["artifact_ref"] == source_ref]
            expected = {(i, a) for i in range(len(models)) for a in CM_ALGORITHMS}
            actual = [(r["identity"]["model_ordinal"], r["identity"]["algorithm"]) for r in grouped]
            population &= (bool(models) and len(actual) == len(expected) and set(actual) == expected and
                artifacts[ref]["completeness"] == "complete" and artifacts.get(source_ref, {}).get("completeness") == "complete" and
                all(m["content_validation"] == "parsed_headers_and_boundaries" for m in models))
    binding_outcomes = []
    for row in rows:
        target = targets[row["record_key"]]
        count = row["values"]["score_count"]
        valid = count["state"] == "present" and count["value"] == len(row["series"]) and all(p["x"]["state"] == "present" for p in row["series"])
        target["checks"].append(check("partition_score_count_consistent", "pass" if valid else "fail", _inputs(count)))
        if not valid:
            _issue(result, "partition_population_invalid", row, "score_count")
        reqs = by_artifact.get(row["locator"]["artifact_ref"], [])
        binding = None
        if requests is not None:
            binding = False
            if len(reqs) == 1:
                req = reqs[0]
                source = artifacts.get(req["source_model_artifact_ref"])
                reported_length = row["values"]["requested_megabases"]
                binding = (source is not None and source["role"] == "models" and source["sha256"] == req["source_model_sha256"]
                    and req["partition_index"] == row["identity"]["partition_index"] and
                    req["partition_count"] == row["identity"]["partition_count"] and
                    reported_length["state"] == "present" and reported_length["value"] == req["requested_megabases"])
                if binding:
                    expected_keys = [m["record_key"] for m in sheet["input_records"] if m["kind"] == "model" and m["locator"]["artifact_ref"] == source["artifact_ref"]]
                    ordinal = row["identity"]["model_ordinal"]
                    binding = type(ordinal) is int and ordinal < len(expected_keys) and row["model_keys"] == [expected_keys[ordinal]]
                if binding and sheet["operation"]["mode"] == "partition_scores":
                    settings = sheet["operation"]["settings"]
                    binding = all(flag not in settings or settings[flag] == req[field] for flag, field in
                                  (("--part", "partition_index"), ("--ptot", "partition_count"), ("-L", "requested_megabases")))
        binding_outcomes.append(binding)
        target["checks"].append(check("partition_request_binding", "unknown" if binding is None else "pass" if binding else "fail",
                                      _inputs(row["values"]["score_count"])))
        target["checks"].append(check("partition_population_complete", "unknown" if population is None else "pass" if population else "fail"))
        settings_outcome = "unknown" if not requests or not seed_known or gc_unknown else "pass" if coherent else "fail"
        target["checks"].append(check("partition_settings_consistent", settings_outcome))
        if binding is None:
            _issue(result, "partition_request_missing", row)
        elif not binding:
            _issue(result, "partition_request_mismatch", row)
        if population is False:
            _issue(result, "partition_population_invalid", row)
        if requests and not coherent:
            _issue(result, "partition_settings_mismatch", row)
        if requests and not seed_known:
            _issue(result, "partition_seed_unknown", row)
        if gc_unknown:
            _issue(result, "partition_gc_identity_unknown", row)
    if sheet["operation"]["mode"] == "merge_scores":
        associations = {a["output_keys"][0]: a["input_keys"][0] for a in sheet["associations"]
                        if a["relation"] == "calibrated_from" and a["status"] == "validated" and
                        len(a["input_keys"]) == len(a["output_keys"]) == 1}
        for row in sheet["native_rows"]:
            if row["kind"] != "calibration" or row["identity"]["source"] != "model_header" or len(row["model_keys"]) != 1:
                continue
            original = associations.get(row["model_keys"][0])
            contributing = [r for r in rows if r["model_keys"] == [original] and r["identity"]["algorithm"] == row["identity"]["algorithm"]]
            measured = row["values"]["random_hit_count"]
            ready = population is True and coherent and seed_known and not gc_unknown and all(b is True for b in binding_outcomes) and all(
                r["values"]["score_count"]["state"] == "present" and r["values"]["score_count"]["value"] == len(r["series"]) and
                all(s["x"]["state"] == "present" for s in r["series"]) for r in contributing)
            status = "unknown"
            if ready and contributing and measured["state"] == "present":
                status = "pass" if sum(r["values"]["score_count"]["value"] for r in contributing) == measured["value"] else "fail"
            targets[row["record_key"]]["checks"].append(check("partition_merged_hit_counts", status,
                _inputs(measured, *(r["values"]["score_count"] for r in contributing))))
            if status == "fail":
                _issue(result, "partition_hit_count_mismatch", row)


def calculate_infernal_statistics(sheet, *, parameters):
    """Calculate from the saved sheet only; explicit parameters never rerun work."""
    validate_common_sheet(sheet)
    _parameters(parameters)
    if sheet["operation"]["program"] not in {"cmbuild", "cmcalibrate", "cmstat"}:
        raise ValueError("infernal_statistics_program_mismatch")
    all_records = sheet["input_records"]+sheet["output_records"]+sheet["native_rows"]
    keys = [r.get("record_key") for r in all_records]
    if len(set(keys)) != len(keys):
        raise ValueError("infernal_statistics_duplicate_record_key")
    for row in all_records:
        kind = row.get("kind")
        if kind in ROW_FIELDS:
            if set(row) != ROW_FIELDS[kind] or set(row["values"]) != VALUE_FIELDS[kind]:
                raise ValueError("infernal_statistics_row_fields_invalid")
            if any(cell["unit"] != VALUE_UNITS[kind][name] for name, cell in row["values"].items()):
                raise ValueError("infernal_statistics_row_units_invalid")
            if kind in IDENTITY_FIELDS and (set(row["identity"]) != IDENTITY_FIELDS[kind] or type(row["model_keys"]) is not list or type(row["series"]) is not list):
                raise ValueError("infernal_statistics_identity_fields_invalid")
            if kind in IDENTITY_FIELDS and any(type(p) is not dict or set(p) != {"index", "x", "y"} or
                type(p["index"]) is not int or p["index"] != i for i, p in enumerate(row["series"])):
                raise ValueError("infernal_statistics_series_shape_invalid")
    models = {m["record_key"]: m for m in all_records if m["kind"] == "model"}
    operation = sheet["operation"]
    result = new_calculations(operation, parameters)
    tolerance = parameters.get("rounding_absolute_tolerance", 0)
    targets = {}
    for row in all_records:
        kind = row["kind"]
        if kind == "model":
            continue
        target = _row_result(row)
        targets[row["record_key"]] = target
        result["rows"].append(target)
        out = target["components"]
        if kind == "training_alignment":
            target["checks"].append(check("training_alignment_complete", "pass" if row["content_validation"] == "parsed" else
                "unknown" if row["content_validation"] == "partial" else "fail", [field_input(row["locator"], "content_validation")]))
            continue
        model = _model(row, models, result, target) if kind in {"build", "build_refinement", "calibration", "model_statistic"} else None
        if kind == "build" or (kind == "model_statistic" and row["identity"]["mode"] == "summary"):
            _paired(row, target, result)
            _header_checks(row, model, target, result, tolerance)
            if kind == "build":
                population = [m for m in sheet["output_records"] if m["kind"] == "model"]
                native = [r for r in sheet["native_rows"] if r["kind"] == "build"]
                complete = all(a["completeness"] == "complete" for a in sheet["artifacts"] if a["role"] in {"stdout", "built_models"})
                status = "unknown" if not complete else "pass" if len(population) == len(native) and all(r["model_keys"] for r in native) else "fail"
                target["checks"].append(check("build_population_complete", status))
        elif kind == "calibration":
            _calibration(row, target, model, operation, parameters, result, tolerance)
        elif kind == "model_statistic":
            _conversion(row, target, model, operation, parameters, result, tolerance)
        elif kind == "resource_estimate":
            seconds = row["values"]["predicted_seconds"]
            mb = row["values"]["predicted_mb"]
            out["predicted_seconds"] = deepcopy(seconds)
            out["predicted_bytes"] = _derived(mb["value"]*1e6, "byte", [mb], result, row, "predicted_bytes") if mb["state"] == "present" else _missing("byte", mb)
            if out["predicted_bytes"]["state"] == "present":
                out["predicted_bytes"]["basis"] = "native_prediction"
            if row["identity"]["estimate_kind"] == "partition_command_count":
                count = row["values"]["command_count"]
                expected = parameters.get("partition_count", operation["settings"].get("--ptot"))
                status = "unknown" if expected is None or count["state"] != "present" else "pass" if expected == count["value"] else "fail"
                target["checks"].append(check("split_command_count_consistent", status, _inputs(count)))
        elif kind == "partition":
            requests = [r for r in parameters.get("partition_requests", []) if r["artifact_ref"] == row["locator"]["artifact_ref"]]
            request = requests[0] if len(requests) == 1 else {}
            # An embedded command is a native statement, not the selected
            # request. Workload arithmetic needs explicit original metadata or
            # explicit recalculation parameters; it never authenticates itself.
            requested = parameters.get("requested_megabases", request.get("requested_megabases", operation["settings"].get("-L")))
            length = value(requested, basis="derived", unit="Mnt")
            chunks = _chunks(length)
            out["total_calibration_chunk_count"] = _missing("count", length)
            if chunks is not None:
                out["total_calibration_chunk_count"] = value(chunks, basis="derived", unit="count", inputs=_inputs(length))
            p = parameters.get("partition_index", request.get("partition_index", operation["settings"].get("--part")))
            total = parameters.get("partition_count", request.get("partition_count", operation["settings"].get("--ptot")))
            out["partition_chunk_count"] = value(state="missing", basis="derived", unit="count", inputs=_inputs(length))
            out["actual_calibration_nt"] = _missing("nt", length)
            if chunks is None and length["state"] == "present":
                _issue(result, "overflow", row, "total_calibration_chunk_count")
                for name in ("total_calibration_chunk_count", "partition_chunk_count", "actual_calibration_nt"):
                    out[name] = value(state="invalid", basis="derived", unit=COMPONENT_UNITS[name], inputs=_inputs(length))
            if chunks is not None and type(p) is int and type(total) is int and 0 < p <= total:
                count = 0 if p > chunks else (chunks-p)//total+1
                out["partition_chunk_count"] = value(count, basis="derived", unit="count", inputs=_inputs(length))
                out["actual_calibration_nt"] = _derived(count*10000, "nt", [out["partition_chunk_count"]], result, row, "actual_calibration_nt")
    _partition_checks(sheet, parameters, result, targets)
    require_finite_json(result)
    return result


__all__ = ["calculate_infernal_statistics", "COMPONENT_NAMES", "COMPONENT_UNITS", "PARAMETER_NAMES",
           "CHECK_NAMES", "ISSUE_CODES", "ROW_FIELDS"]
