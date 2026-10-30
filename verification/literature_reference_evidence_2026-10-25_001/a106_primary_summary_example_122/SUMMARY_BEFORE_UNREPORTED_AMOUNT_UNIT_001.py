"""A106 retained summary statistics and explicit mean-covariance arithmetic.

The retained data are an input boundary, not a claim that a paper was parsed.
Reported spreads, raw-unit descriptive statistics, sampling variance estimates
and digitization constraints retain different meanings. No distributional fit,
confidence interval or causal/annotation score is invented here.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import math

from .domain import REF, obj, validate_schema
from .literature_assay_inputs import _fail, _finite, _keys, _nullable, _text, _witness_schema
from .literature_experimental_contracts import ExperimentalContractError
from .literature_perturbation_calculations import COMPONENTS as POINT_COMPONENTS, populate_source_restoration, _endpoint_reason
from .literature_summary_figure_reader import read_summary_figure

DATA_VERSION = "a106_source_measurements_v2"
VERSION = "a106_source_summary_restoration_v2"
ROLES = ("W", "K", "R", "A_reference", "A_restored", "B_pert", "B_rest")
SUMMARY_KINDS = ("arithmetic_mean", "geometric_mean", "median", "single_observation", "unknown")
SCALES = ("endpoint", "log10_endpoint", "ln_endpoint", "unknown")
SPREAD_KINDS = ("sd", "sem", "confidence_interval", "detection_limit", "untyped_pm", "unreported")
VARIANCE_STATUSES = ("known", "estimated", "unknown")
VARIANCE_SCOPES = ("technical_mean_within_studied_unit", "biological_unit_mean", "preparation_mean",
    "other_unit_mean", "source_reported_unresolved_scope", "mixed_estimator_scopes", "unavailable", "not_applicable")
UNIT_KINDS = ("culture", "organism", "preparation", "biological_unit", "technical_reading", "other", "unknown")
STATISTICS = ("summary_value", "reported_spread", "reported_count", "sample_sd", "mean_se", "mean_variance")
STAT_COMPONENTS = tuple(role + "_" + name for role in ROLES for name in STATISTICS)
CONTRAST_COMPONENTS = ("perturbation_mean_variance", "perturbation_variance_lower", "perturbation_variance_upper",
    "restoration_difference", "restoration_mean_variance", "restoration_variance_lower", "restoration_variance_upper",
    "shared_contrast_covariance")
COMPONENTS = (*POINT_COMPONENTS, *STAT_COMPONENTS, *CONTRAST_COMPONENTS)
DATA_FIELDS = ("version", "endpoint_unit", "exposure_unit", "origin", "uncertainty_basis", "measurements", "covariances")
ENTRY_FIELDS = ("value", "measurement_id", "value_scale", "summary_kind", "summary_scale", "uncertainty",
                "count", "raw_units", "graph", "digitization", "meaning_witnesses")
SPREAD_FIELDS = ("kind", "value", "lower", "upper", "coverage", "scale", "variance_status")
COUNT_FIELDS = ("n", "unit_kind", "independence")
INTERPRETATION_BASIS_FIELDS = ("summary_kind", "summary_scale", "spread_kind", "spread_scale",
    "count_n", "count_unit", "count_independence")
INTERPRETATION_BASES = ("source_reported", "source_supported_inference", "conditional_assumption", "unresolved")
COV_FIELDS = ("first", "second", "kind", "value", "variance_status", "witnesses")
_NUMERIC = {"type": ["number", "null"]}
_NATURAL_COUNT = {"type": ["integer", "null"], "minimum": 1}


def _choice(value, allowed, field):
    if not isinstance(value, str) or value not in allowed:
        _fail("unsupported_summary_meaning", field)


def _nonnegative(value, field, *, nullable=True):
    if value is None and nullable:
        return
    _finite(value, field)
    if value < 0:
        _fail("nonnegative_summary_value_required", field)


def _ratio(value):
    return Fraction(value)


def _project(exact):
    if exact is None:
        return None
    try:
        value = float(exact)
    except (OverflowError, ValueError):
        return None
    return value if math.isfinite(value) and (value != 0 or exact == 0) else None


def _sqrt(value):
    if value is None:
        return None
    with localcontext() as ctx:
        ctx.prec = 100
        q = Fraction(value)
        return (Decimal(q.numerator)/Decimal(q.denominator)).sqrt()


def _outward_rational(exact, direction):
    try:
        value=float(exact)
    except OverflowError:
        return math.nextafter(math.inf,0.) if direction<0 and exact>0 else None
    if not math.isfinite(value):
        return math.nextafter(math.inf,0.) if direction<0 and exact>0 else None
    if value==0 and exact>0:
        # Zero is a conservative lower bound, not a fabricated point estimate.
        return 0. if direction<0 else math.ulp(0.)
    actual=Fraction(value)
    if direction < 0 and actual > exact:
        value=math.nextafter(value,-math.inf)
    elif direction > 0 and actual < exact:
        value=math.nextafter(value,math.inf)
    return value if math.isfinite(value) else None


def covariance_variance_enclosure(first, second):
    """Sound rational outer bounds for Va+Vb−2Cov with unknown covariance.

    Bound sqrt(Va*Vb) by exact integer-isqrt arithmetic. The equivalent lower
    identity avoids catastrophic cancellation when the variances nearly agree.
    No decimal precision choice or sample-count cap establishes containment.
    """
    a,b=Fraction(first),Fraction(second)
    if a<0 or b<0:
        _fail("nonnegative_mean_variance_required","covariance_enclosure")
    product=a*b
    scale=1<<256
    denominator=product.denominator*scale
    radicand=product.numerator*product.denominator*scale*scale
    integer=math.isqrt(radicand)
    root_upper=Fraction(integer if integer*integer==radicand else integer+1,denominator)
    sum_upper=a+b+2*root_upper
    lower=(a-b)**2/sum_upper if sum_upper else Fraction(0)
    return _outward_rational(lower,-1),_outward_rational(sum_upper,1)


def _stat_unit(unit, scale):
    if scale == "unknown":
        return "unreported"
    if scale == "log10_endpoint":
        return "log10_" + unit
    if scale == "ln_endpoint":
        return "ln_" + unit
    return unit


def _raw_summary(raw, field):
    if raw is None:
        return None
    if not isinstance(raw, list) or not raw:
        _fail("nonempty_raw_unit_table_required", field)
    units = {}
    for index, row in enumerate(raw):
        here = field + f"[{index}]"
        _keys(row, ("unit_id", "values"), here)
        _text(row["unit_id"], here + ".unit_id")
        if row["unit_id"] in units:
            _fail("duplicate_raw_unit_identity", here + ".unit_id")
        values = row["values"]
        if not isinstance(values, list) or not values:
            _fail("nonempty_unit_readings_required", here + ".values")
        for i, value in enumerate(values):
            _finite(value, here + f".values[{i}]")
        units[row["unit_id"]] = sum(map(Fraction, values)) / len(values)
    n = len(units)
    mean = sum(units.values()) / n
    variance = sum((x-mean)**2 for x in units.values())/(n-1) if n > 1 else None
    return {"unit_means": units, "n": n, "mean": mean, "sample_variance": variance}


def _entry(entry, field, sources, unit):
    # Omission preserves historical v2 inputs/payloads exactly. A supplied basis
    # qualifies selected meanings; it neither validates source truth nor changes
    # numerical eligibility or calculation.
    has_basis = isinstance(entry, dict) and "interpretation_basis" in entry
    _keys(entry, (*ENTRY_FIELDS, "interpretation_basis") if has_basis else ENTRY_FIELDS, field)
    entry = deepcopy(entry)
    if has_basis:
        _keys(entry["interpretation_basis"], INTERPRETATION_BASIS_FIELDS, field + ".interpretation_basis")
        for name, basis in entry["interpretation_basis"].items():
            _choice(basis, INTERPRETATION_BASES, field + ".interpretation_basis." + name)
    value = entry["value"]
    if value is not None:
        _finite(value, field + ".value")
    if entry["measurement_id"] is not None:
        _text(entry["measurement_id"], field + ".measurement_id")
    for name, choices in (("value_scale", SCALES[:-1]), ("summary_kind", SUMMARY_KINDS), ("summary_scale", SCALES)):
        _choice(entry[name], choices, field + "." + name)
    _keys(entry["uncertainty"], SPREAD_FIELDS, field + ".uncertainty")
    spread = entry["uncertainty"]
    _choice(spread["kind"], SPREAD_KINDS, field + ".uncertainty.kind")
    _choice(spread["scale"], SCALES, field + ".uncertainty.scale")
    _choice(spread["variance_status"], VARIANCE_STATUSES, field + ".uncertainty.variance_status")
    _nonnegative(spread["value"], field + ".uncertainty.value")
    for name in ("lower", "upper", "coverage"):
        if spread[name] is not None:
            _finite(spread[name], field + ".uncertainty." + name)
    if spread["coverage"] is not None and not 0 < spread["coverage"] < 1:
        _fail("coverage_fraction_required", field + ".uncertainty.coverage")
    if spread["lower"] is not None and spread["upper"] is not None and spread["lower"] > spread["upper"]:
        _fail("ordered_reported_interval_required", field + ".uncertainty")
    if spread["kind"] == "unreported" and any(spread[k] is not None for k in ("value", "lower", "upper", "coverage")):
        _fail("unreported_spread_has_no_numbers", field + ".uncertainty")
    if spread["kind"] in ("sd", "sem", "untyped_pm") and any(spread[k] is not None for k in ("lower", "upper", "coverage")):
        _fail("spread_is_not_an_interval", field + ".uncertainty")
    if spread["kind"] == "detection_limit" and spread["coverage"] is not None:
        _fail("detection_limit_is_not_coverage", field + ".uncertainty")
    _keys(entry["count"], COUNT_FIELDS, field + ".count")
    count = entry["count"]
    n = count["n"]
    if n is not None and (type(n) is not int or n < 1):
        _fail("positive_integer_repeat_count_required", field + ".count.n")
    _choice(count["unit_kind"], UNIT_KINDS, field + ".count.unit_kind")
    _choice(count["independence"], ("independent", "not_independent", "unknown"), field + ".count.independence")
    if not isinstance(entry["meaning_witnesses"], list):
        _fail("witness_list_required", field + ".meaning_witnesses")
    entry["meaning_witnesses"] = [sources.witness(w, field + f".meaning_witnesses[{i}]")
                                   for i, w in enumerate(entry["meaning_witnesses"])]
    digit = entry["digitization"]
    if digit is not None:
        _keys(digit, ("lower", "upper", "kind"), field + ".digitization")
        for name in ("lower", "upper"):
            _finite(digit[name], field + ".digitization." + name)
        if digit["kind"] != "conditional_digitization_not_confidence_interval" or digit["lower"] > digit["upper"]:
            _fail("invalid_digitization_constraint", field + ".digitization")
        if value is not None and not digit["lower"] <= value <= digit["upper"]:
            _fail("digitization_must_contain_display_value", field + ".digitization")
    raw = _raw_summary(entry["raw_units"], field + ".raw_units")
    if raw is not None and entry["value_scale"] == "endpoint" and any(value < 0 for row in entry["raw_units"] for value in row["values"]):
        _fail("nonnegative_measurement_required", field + ".raw_units")
    graph = entry["graph"]
    if raw is not None and graph is not None:
        _fail("choose_raw_table_or_graph_representation", field)
    trace = None
    if raw is not None:
        if value is not None or entry["summary_kind"] != "arithmetic_mean" or entry["summary_scale"] != entry["value_scale"]:
            _fail("raw_unit_mean_representation_required", field)
        if n is not None and n != raw["n"]:
            _fail("raw_unit_count_mismatch", field + ".count.n")
        value = _project(raw["mean"])
        count["n"] = raw["n"]
    if graph is not None:
        _keys(graph, ("source_ref", "selection"), field + ".graph")
        if value is not None or digit is not None or entry["value_scale"] != "endpoint":
            _fail("graph_values_come_from_pixels", field + ".graph")
        image = sources.source(graph["source_ref"], "original")
        trace = read_summary_figure(image["content"], graph["selection"])
        if trace["unit"] != unit:
            _fail("graph_endpoint_unit_mismatch", field + ".graph")
        trace["source_ref"], trace["artifact_ref"] = graph["source_ref"], image["artifact_ref"]
        mean = trace["features"]["mean"]
        value = mean["value"]
        if value is not None:
            entry["digitization"] = {"lower": mean["lower"], "upper": mean["upper"], "kind": trace["bound_kind"]}
        if spread["value"] is not None or spread["lower"] is not None or spread["upper"] is not None:
            _fail("graph_spreads_come_from_pixels", field + ".uncertainty")
        caps = [(name, trace["features"][name]) for name in ("upper_error", "lower_error") if trace["features"][name] is not None]
        transform = {"endpoint": lambda x:Decimal(x), "log10_endpoint": lambda x:Decimal(x).log10(),
                     "ln_endpoint": lambda x:Decimal(x).ln()}.get(spread["scale"])
        entry["graph_cap_values"] = {"lower_error_cap":None,"upper_error_cap":None,
                                      "error_cap_scale":spread["scale"] if transform is not None else "endpoint"}
        for name,cap in caps:
            if cap["value"] is not None:
                with localcontext() as ctx:
                    ctx.prec=100
                    endpoint = Decimal(cap["decimal_value"])
                    projected = _project(transform(endpoint) if transform is not None else endpoint)
                    entry["graph_cap_values"]["upper_error_cap" if name=="upper_error" else "lower_error_cap"] = projected
        if value is not None and transform is not None:
            try:
                magnitudes, intervals = [], []
                for name, cap in caps:
                    if cap["value"] is None:
                        continue
                    if spread["kind"] in ("sd", "sem", "untyped_pm"):
                        central_mean, central_cap = Decimal(mean["decimal_value"]),Decimal(cap["decimal_value"])
                        if name == "upper_error" and central_cap < central_mean or name == "lower_error" and central_cap > central_mean:
                            _fail("error_cap_direction_mismatch", field + ".graph." + name)
                        with localcontext() as ctx:
                            ctx.prec=100
                            magnitudes.append(_project(abs(transform(central_cap)-transform(central_mean))))
                            if name == "upper_error":
                                low= max(Decimal(0),transform(cap["decimal_lower"])-transform(mean["decimal_upper"]))
                                high=max(Decimal(0),transform(cap["decimal_upper"])-transform(mean["decimal_lower"]))
                            else:
                                low= max(Decimal(0),transform(mean["decimal_lower"])-transform(cap["decimal_upper"]))
                                high=max(Decimal(0),transform(mean["decimal_upper"])-transform(cap["decimal_lower"]))
                            low_float,high_float=_project(low),_project(high)
                            if low_float is not None and high_float is not None:
                                intervals.append((max(0.,math.nextafter(low_float,-math.inf)),math.nextafter(high_float,math.inf)))
                    elif spread["kind"] == "confidence_interval":
                        with localcontext() as ctx:
                            ctx.prec=100
                            spread["upper" if name == "upper_error" else "lower"] = _project(transform(cap["decimal_value"]))
                if magnitudes and intervals:
                    # Both caps are retained. When their possible magnitudes
                    # overlap, the midpoint of the overlap is a declared
                    # digitization estimate of one symmetric spread. Otherwise
                    # there is no symmetric point, but both ranges survive.
                    low, high = max(x[0] for x in intervals), min(x[1] for x in intervals)
                    spread["value"] = magnitudes[0] if len(magnitudes)==1 else low+(high-low)/2 if low<=high else None
                    entry["graph_spread_digitization"] = {"lower":min(x[0] for x in intervals),"upper":max(x[1] for x in intervals),
                        "kind":"conditional_digitization_not_confidence_interval",
                        "interpretation":"symmetric_compatible" if low<=high else "asymmetric_readings"}
            except ExperimentalContractError:
                raise
            except (ValueError, OverflowError):
                # Keep the native pixel/endpoint trace even when a requested
                # log-statistical interpretation is outside its domain.
                spread["value"] = None
        if spread["lower"] is not None and spread["upper"] is not None and spread["lower"]>spread["upper"]:
            _fail("ordered_reported_interval_required",field+".uncertainty")
    if value is not None and entry["measurement_id"] is None:
        _fail("known_measurement_id_required", field + ".measurement_id")
    if value is not None and entry["value_scale"] == "endpoint" and value < 0:
        _fail("nonnegative_measurement_required", field + ".value")
    entry["value"] = value
    return entry, raw, trace


def read_summary_measurements(data, *, sources, reference, artifact_ref, status, key_function):
    """Read the exact retained v2 JSON plus any explicitly selected image bytes."""
    _keys(data, DATA_FIELDS, "data_source")
    if data["version"] != DATA_VERSION or data["uncertainty_basis"] != "per_measurement":
        _fail("unsupported_perturbation_summary_version", "data_source.version")
    from .literature_perturbation_inputs import ENDPOINT_UNITS, EXPOSURE_UNITS
    _choice(data["endpoint_unit"], ENDPOINT_UNITS, "data_source.endpoint_unit")
    _choice(data["exposure_unit"], EXPOSURE_UNITS, "data_source.exposure_unit")
    _choice(data["origin"], ("reported", "graph_derived", "synthetic"), "data_source.origin")
    _keys(data["measurements"], ROLES, "data_source.measurements")
    observations, summaries, raw, graphs, owners = {}, {}, {}, {}, {}
    for role in ROLES:
        unit = data["exposure_unit"] if role.startswith("A_") else data["endpoint_unit"]
        entry, table, graph = _entry(data["measurements"][role], "data_source.measurements." + role, sources, unit)
        key = key_function(reference, artifact_ref, entry["measurement_id"]) if entry["measurement_id"] is not None else None
        if key in owners and owners[key] != (entry, unit):
            _fail("shared_summary_measurement_mismatch", "data_source.measurements." + role)
        if key is not None:
            owners[key] = (entry, unit)
        point = entry["value"] if entry["value_scale"] == "endpoint" else None
        if status == "qualitative_only" and role in ("W", "K", "R") and point is not None:
            _fail("qualitative_endpoint_has_no_numeric_values", "data_source.measurements." + role)
        observations[role] = {"role": role, "value": point, "unit": unit,
            "raw_entry": deepcopy(data["measurements"][role]), "source_ref": reference,
            "artifact_ref": artifact_ref, "measurement_key": key}
        summaries[role], raw[role], graphs[role] = entry, table, graph
    covariances = data["covariances"]
    if not isinstance(covariances, list):
        _fail("covariance_list_required", "data_source.covariances")
    seen, retained_cov = set(), []
    for index, covariance in enumerate(covariances):
        field = f"data_source.covariances[{index}]"
        _keys(covariance, COV_FIELDS, field)
        row = deepcopy(covariance)
        for key in ("first", "second"):
            _choice(row[key], ("W", "K", "R"), field + "." + key)
        pair = tuple(sorted((row["first"], row["second"])))
        if pair[0] == pair[1] or pair in seen:
            _fail("unique_distinct_covariance_pair_required", field)
        seen.add(pair)
        _choice(row["kind"], ("unknown", "mean_covariance", "uncorrelated", "paired_units"), field + ".kind")
        _choice(row["variance_status"], VARIANCE_STATUSES, field + ".variance_status")
        if row["kind"] == "mean_covariance":
            _finite(row["value"], field + ".value")
        elif row["value"] is not None:
            _fail("covariance_value_not_applicable", field + ".value")
        if not isinstance(row["witnesses"], list):
            _fail("witness_list_required", field + ".witnesses")
        row["witnesses"] = [sources.witness(w, field + f".witnesses[{i}]") for i, w in enumerate(row["witnesses"])]
        retained_cov.append(row)
    # Fraction objects are used only while doing arithmetic; saved statistics
    # are finite JSON numbers plus original raw-unit values for provenance.
    return observations, {"version": DATA_VERSION, "measurements": summaries,
        "covariances": retained_cov, "graphs": graphs}


def _mean_statistics(entry):
    raw = _raw_summary(entry["raw_units"], "summary.raw_units")
    spread, count = entry["uncertainty"], entry["count"]
    variance = None
    method, reason, variance_status = "none", "mean_variance_unavailable", "unknown"
    sample_sd = _sqrt(raw["sample_variance"]) if raw is not None else None
    compatible = (entry["summary_kind"] == "arithmetic_mean" and entry["summary_scale"] == entry["value_scale"])
    independent = count["independence"] == "independent"
    if raw is not None and compatible and independent and raw["sample_variance"] is not None:
        variance = raw["sample_variance"] / raw["n"]
        method, reason, variance_status = "raw_independent_unit_mean", None, "estimated"
    elif spread["kind"] == "sem" and spread["value"] is not None:
        # This preserves the reported SEM interpretation, even if the source
        # underdescribes how that estimate was obtained. Contrast eligibility
        # separately requires the selected estimate/scale to be compatible.
        variance = Fraction(spread["value"])**2
        method, reason, variance_status = "reported_sem_squared", None, spread["variance_status"]
    elif (spread["kind"] == "sd" and spread["value"] is not None and compatible and independent
          and spread["scale"] == entry["value_scale"] and count["n"] is not None and count["n"] > 1):
        variance = Fraction(spread["value"])**2 / count["n"]
        method, reason, variance_status = "sd_squared_over_independent_n", None, spread["variance_status"]
    eligible = (compatible and entry["value_scale"] == "endpoint" and variance is not None
                and (raw is not None or spread["scale"] == "endpoint"))
    scope = ("unavailable" if variance is None else
        "technical_mean_within_studied_unit" if count["unit_kind"]=="technical_reading" else
        "preparation_mean" if count["unit_kind"]=="preparation" else
        "biological_unit_mean" if count["unit_kind"] in ("culture","organism","biological_unit") else
        "other_unit_mean" if count["unit_kind"]=="other" else "source_reported_unresolved_scope")
    return {"variance": variance, "se": _sqrt(variance), "sample_sd": sample_sd,
            "method": method, "reason": reason, "variance_status": variance_status,
            "contrast_eligible": eligible, "raw": raw,"variance_scope":scope}


def _covariances(summary, stats):
    roles = ("W", "K", "R")
    result = {(r, r): stats[r]["variance"] if stats[r]["contrast_eligible"] else None for r in roles}
    kinds, statuses = {}, {}
    for row in summary["covariances"]:
        a, b = row["first"], row["second"]
        cov = None
        if row["kind"] == "mean_covariance":
            cov = Fraction(row["value"])
        elif row["kind"] == "uncorrelated":
            cov = Fraction(0)
        elif row["kind"] == "paired_units":
            x, y = stats[a]["raw"], stats[b]["raw"]
            if x is None or y is None or set(x["unit_means"]) != set(y["unit_means"]) or x["n"] < 2:
                _fail("complete_shared_raw_units_required", "covariances")
            if not stats[a]["contrast_eligible"] or not stats[b]["contrast_eligible"]:
                _fail("paired_unit_mean_variance_not_supported", "covariances")
            cov = sum((v-x["mean"])*(y["unit_means"][u]-y["mean"]) for u,v in x["unit_means"].items()) / (x["n"]-1) / x["n"]
        result[a,b] = result[b,a] = cov
        kinds[a,b] = kinds[b,a] = row["kind"]
        statuses[a,b] = statuses[b,a] = "estimated" if row["kind"] == "paired_units" else row["variance_status"]
    for i, a in enumerate(roles):
        for b in roles[i+1:]:
            result.setdefault((a,b), None); result.setdefault((b,a), None)
            va, vb, cov = result[a,a], result[b,b], result[a,b]
            if va is not None and vb is not None and cov is not None and cov*cov > va*vb:
                _fail("mean_covariance_matrix_not_psd", "covariances")
    if all(value is not None for value in result.values()):
        a,b,c = (result[r,r] for r in roles)
        d,e,f = result["W","K"],result["W","R"],result["K","R"]
        if a*b*c + 2*d*e*f - a*f*f - b*e*e - c*d*d < 0:
            _fail("mean_covariance_matrix_not_psd", "covariances")
    return result, kinds, statuses


def _cell(value, unit, formula, *, reason=None, method="none", variance_status="unknown", lower=None, upper=None, bound_kind="none", conditional=()):
    number = _project(value)
    if value is not None and number is None:
        reason = "numerical_model_range"
    return {"value": number, "unit": unit, "status": "populated" if number is not None else "unavailable",
        "formula": formula, "origin": "derived", "unavailable_reason": reason,
        "conditional_on": list(conditional), "statistic_method": method, "variance_status": variance_status,
        "lower": lower, "upper": upper, "bound_kind": bound_kind,
        "lower_error_cap":None,"upper_error_cap":None,"error_cap_scale":"unknown","spread_reading":"not_applicable"}


def populate_summary_restoration(extraction, *, origin):
    """Calculate paired point and summary components from one validated input."""
    inputs = {name: extraction[name] for name in ("values", "measurement_keys", "endpoint_unit", "exposure_unit",
        "design", "measurement_status", "same_endpoint_scope", "amount_role", "orientation")}
    inputs["origin"] = origin
    legacy = populate_source_restoration(inputs)
    summary = extraction["summary_data"]
    statistics = {role: _mean_statistics(summary["measurements"][role]) for role in ROLES}
    covariance, kinds, covariance_status = _covariances(summary, statistics)
    cells = {name: {**deepcopy(cell), "statistic_method": "point_component", "variance_status": "unknown",
                   "lower": None, "upper": None, "bound_kind": "none", "lower_error_cap":None,"upper_error_cap":None,
                   "error_cap_scale":"unknown","spread_reading":"not_applicable"} for name, cell in legacy["cells"].items()}
    descriptors = {}
    for role in ROLES:
        entry, stat = summary["measurements"][role], statistics[role]
        native = {"W":"reference_endpoint","K":"perturbed_endpoint","R":"restored_endpoint"}.get(role)
        if native is not None:
            cells[native]["origin"] = "graph_derived" if entry["graph"] is not None else "derived" if entry["raw_units"] is not None else origin
            if entry["graph"] is not None and entry["value"] is None:
                cells[native]["unavailable_reason"] = summary["graphs"][role]["features"]["mean"]["unavailable_reason"]
        physical = extraction["exposure_unit"] if role.startswith("A_") else extraction["endpoint_unit"]
        unit = _stat_unit(physical, entry["value_scale"])
        variance_unit = _stat_unit(physical, entry["uncertainty"]["scale"] if stat["method"] == "reported_sem_squared" else entry["value_scale"])
        descriptors[role] = {"summary_kind": entry["summary_kind"], "value_scale": entry["value_scale"],
            "summary_scale": entry["summary_scale"], "spread_kind": entry["uncertainty"]["kind"],
            "spread_scale": entry["uncertainty"]["scale"], "count_unit": entry["count"]["unit_kind"],
            "independence": entry["count"]["independence"], "n": entry["count"]["n"]}
        if "interpretation_basis" in entry:
            descriptors[role]["interpretation_basis"] = deepcopy(entry["interpretation_basis"])
        digit = entry["digitization"]
        cells[role+"_summary_value"] = _cell(entry["value"], unit, "selected_summary_value",
            reason="summary_value_unreported" if entry["value"] is None else None,
            method="equal_unit_descriptive_mean" if entry["raw_units"] is not None else "selected_reported_summary",
            lower=digit["lower"] if digit else None, upper=digit["upper"] if digit else None,
            bound_kind=digit["kind"] if digit else "none")
        cells[role+"_summary_value"]["origin"] = "graph_derived" if entry["graph"] is not None else "derived" if entry["raw_units"] is not None else origin
        if entry["graph"] is not None and entry["value"] is None:
            cells[role+"_summary_value"]["unavailable_reason"] = summary["graphs"][role]["features"]["mean"]["unavailable_reason"]
        elif entry["raw_units"] is not None and entry["value"] is None:
            cells[role+"_summary_value"]["unavailable_reason"] = "numerical_model_range"
        spread = entry["uncertainty"]
        spread_digit = entry.get("graph_spread_digitization")
        cells[role+"_reported_spread"] = _cell(spread["value"], _stat_unit(physical, spread["scale"]), "reported_spread",
            reason="spread_value_unreported" if spread["value"] is None else None, method="reported_" + spread["kind"],
            variance_status=spread["variance_status"], lower=spread_digit["lower"] if spread_digit else spread["lower"], upper=spread_digit["upper"] if spread_digit else spread["upper"],
            bound_kind=spread_digit["kind"] if spread_digit else "reported_confidence_interval" if spread["kind"] == "confidence_interval" else "reported_detection_limit" if spread["kind"] == "detection_limit" else "none")
        cells[role+"_reported_spread"]["origin"] = "graph_derived" if entry["graph"] is not None else origin
        if entry["graph"] is not None:
            cells[role+"_reported_spread"].update(entry["graph_cap_values"],
                spread_reading=spread_digit["interpretation"] if spread_digit else "unresolved")
            if spread["kind"]=="confidence_interval" and (spread["lower"] is not None or spread["upper"] is not None):
                cells[role+"_reported_spread"]["spread_reading"]="reported_interval"
            if spread["value"] is None and spread["kind"] in ("sd","sem","untyped_pm"):
                cells[role+"_reported_spread"]["unavailable_reason"]=("graph_spread_scale_unresolved" if spread["scale"]=="unknown"
                    else "asymmetric_graph_error_readings" if spread_digit and spread_digit["interpretation"]=="asymmetric_readings"
                    else "graph_spread_unavailable")
        cells[role+"_reported_count"] = _cell(entry["count"]["n"], "count", "reported_unit_count",
            reason="count_unreported" if entry["count"]["n"] is None else None, method="reported_count")
        if entry["raw_units"] is not None:
            cells[role+"_reported_count"].update(origin="derived")
        cells[role+"_sample_sd"] = _cell(stat["sample_sd"], unit, "sample_sd_of_unit_means",
            reason="raw_unit_variation_unavailable" if stat["sample_sd"] is None else None, method="descriptive_sample_sd", variance_status="estimated")
        cells[role+"_mean_se"] = _cell(stat["se"], variance_unit, "sqrt_mean_variance", reason=stat["reason"],
            method=stat["method"], variance_status=stat["variance_status"])
        cells[role+"_mean_variance"] = _cell(stat["variance"], variance_unit+"_squared", "mean_variance", reason=stat["reason"],
            method=stat["method"], variance_status=stat["variance_status"])
        for suffix in ("mean_se","mean_variance"):
            cells[role+"_"+suffix]["variance_scope"] = stat["variance_scope"]
    rk_reason = _endpoint_reason(inputs, ("R","K"), restoration=True)
    rk_value = Fraction(inputs["values"]["R"])-Fraction(inputs["values"]["K"]) if rk_reason is None else None
    for prefix, a, b, prerequisite in (("perturbation", "W", "K", legacy["cells"]["perturbation_difference"]),
                                     ("restoration", "R", "K", {"value":rk_value,"unavailable_reason":rk_reason})):
        va, vb, cov = covariance[a,a], covariance[b,b], covariance[a,b]
        valid = prerequisite["value"] is not None
        exact = va + vb - 2*cov if valid and va is not None and vb is not None and cov is not None else None
        reason = prerequisite["unavailable_reason"] if not valid else "mean_variance_unavailable" if va is None or vb is None else "cross_arm_covariance_unknown" if cov is None else None
        marginal_statuses = [statistics[r]["variance_status"] for r in (a,b)]
        scopes = [statistics[r]["variance_scope"] for r in (a,b)]
        scope = scopes[0] if len(set(scopes))==1 else "mixed_estimator_scopes"
        status = ("unknown" if va is None or vb is None or "unknown" in marginal_statuses
                  else "known" if all(s=="known" for s in marginal_statuses) and (cov is None or covariance_status.get((a,b))=="known") else "estimated")
        unit = extraction["endpoint_unit"] + "_squared"
        cells[prefix+"_mean_variance"] = _cell(exact, unit, "Va+Vb-2Cov_mean", reason=reason,
            method="mean_covariance_contrast", variance_status=status if exact is not None else "unknown",
            conditional=("selected_same_endpoint_mean_estimators",))
        cells[prefix+"_mean_variance"]["variance_scope"] = scope if exact is not None else "unavailable"
        lo = hi = None
        if valid and va is not None and vb is not None:
            if cov is not None:
                lo = hi = _project(exact)
            else:
                lo,hi=covariance_variance_enclosure(va,vb)
        for suffix, value in (("lower",lo),("upper",hi)):
            cells[prefix+"_variance_"+suffix] = _cell(value, unit, "covariance_inequality_variance_bound",
                reason=None if value is not None else reason or "numerical_model_range", method="conditional_marginal_covariance_enclosure",
                variance_status=status, bound_kind="covariance_enclosure_not_confidence_interval",
                conditional=("selected_same_endpoint_mean_estimators", "retained_marginal_mean_variances"))
            cells[prefix+"_variance_"+suffix]["variance_scope"] = scope if value is not None else "unavailable"
    cells["restoration_difference"] = _cell(rk_value,
        extraction["endpoint_unit"], "R-K", reason=rk_reason, method="point_component")
    needed = (covariance["W","R"],covariance["W","K"],covariance["K","R"],covariance["K","K"])
    valid = cells["restoration_difference"]["value"] is not None and cells["perturbation_difference"]["value"] is not None
    shared = needed[0]-needed[1]-needed[2]+needed[3] if valid and all(x is not None for x in needed) else None
    cells["shared_contrast_covariance"] = _cell(shared, extraction["endpoint_unit"]+"_squared", "Cov_WR-Cov_WK-Cov_KR+V_K",
        reason="shared_contrast_covariance_unavailable" if shared is None else None,
        method="shared_control_mean_covariance", variance_status="estimated" if shared is not None else "unknown",
        conditional=("selected_same_endpoint_mean_estimators", "shared_K_measurement"))
    if shared is not None:
        scopes=[statistics[r]["variance_scope"] for r in ("W","K","R")]
        cells["shared_contrast_covariance"]["variance_scope"] = scopes[0] if len(set(scopes))==1 else "mixed_estimator_scopes"
        statuses=[statistics[r]["variance_status"] for r in ("W","K","R")]
        statuses += [covariance_status.get((a,b),"unknown") for a,b in (("W","K"),("W","R"),("K","R"))]
        cells["shared_contrast_covariance"]["variance_status"] = "unknown" if "unknown" in statuses else "known" if set(statuses)=={"known"} else "estimated"
    for name,cell in cells.items():
        cell.setdefault("variance_scope","unavailable" if name=="shared_contrast_covariance" else "not_applicable")
    return {"version": VERSION, "inputs": deepcopy(inputs), "primitive_order": list(ROLES), "cells": cells,
            "summary_descriptors": descriptors}


__all__ = ["DATA_VERSION", "VERSION", "ROLES", "COMPONENTS", "STAT_COMPONENTS", "SUMMARY_KINDS", "SCALES",
           "SPREAD_KINDS", "VARIANCE_STATUSES", "VARIANCE_SCOPES", "UNIT_KINDS", "read_summary_measurements", "populate_summary_restoration",
           "covariance_variance_enclosure"]
