"""Pure finite A108 reference context compatibility calculations.

Inputs declare biological requirements, joint-domain support and physical sample
units. This module performs no source interpretation, calibration, I/O, target
transfer or annotation-credit aggregation. Domain bounds are logical bounds;
reported SD/SEM/plus-minus magnitudes never become admissible value intervals.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import math

from .literature_experimental_contracts import ExperimentalContractError

VERSION = "a108_context_compatibility_v1"
COMPONENTS = (
    "sample_weight", "supported_weight", "unresolved_weight", "incompatible_weight",
    "coverage_lower", "coverage_upper", "coverage_point",
    "capability_lower", "capability_upper", "capability_point",
    "selected_lower", "selected_upper", "selected_point", "sampling_lower", "sampling_upper",
)
FORMULAS = {
    "sample_weight": "sum_known_unique_context_weights",
    "supported_weight": "sum_known_weights_times_L",
    "unresolved_weight": "sum_known_weights_times_(U-L)",
    "incompatible_weight": "sum_known_weights_times_(1-U)",
    "coverage_lower": "sum(w*L)/W_or_max(0,sum(marginal_lower)-(J-1))",
    "coverage_upper": "sum(w*U)/W_or_min(marginal_upper)",
    "coverage_point": "coverage_lower_if_exactly_equal_to_upper",
    "capability_lower": "1-product_states(1-L)",
    "capability_upper": "1-product_states_and_permitted_remainder(1-U)",
    "capability_point": "capability_lower_if_exactly_equal_to_upper",
    "selected_lower": "requested_question_lower",
    "selected_upper": "requested_question_upper",
    "selected_point": "requested_question_point",
    "sampling_lower": "max(0,coverage_lower-sqrt(log(2/alpha)/(2*n)))",
    "sampling_upper": "min(1,coverage_upper+sqrt(log(2/alpha)/(2*n)))",
}
REASONS = (
    "question_unreported", "scope_unreported", "scope_unresolved", "scope_conflicting",
    "frame_unreported", "sample_denominator_requires_paired_contexts", "requirement_unobserved", "unit_basis_mismatch", "value_unreported",
    "domain_conflict", "domain_membership_unresolved", "state_relation_unresolved",
    "routes_unreported", "requirements_incomplete", "joint_support_unresolved",
    "joint_support_conflicting", "weight_unreported", "no_context_units",
    "pairing_unknown", "unpaired_capability_unavailable", "unpaired_route_design_unsupported",
    "marginal_unreported", "coverage_unresolved", "capability_unresolved",
    "permitted_remainder_unexamined", "duplicate_context_coalesced", "shared_measurement_dependency",
    "sampling_question_not_coverage", "sampling_requires_paired_contexts", "sampling_requires_defined_scope",
    "sampling_requires_defined_frame", "sampling_requires_equal_weights", "sampling_census",
    "sampling_design_unknown", "sampling_cluster_unreported", "sampling_clusters_not_unique",
    "sampling_alpha_unreported", "sampling_no_context_units", "numerical_model_range",
)
CONDITIONAL_CODES = (
    "native_unit_bases_as_declared", "explicit_domain_union", "declared_joint_support",
    "declared_scope", "known_positive_weights_only", "fixed_paired_sample_frame",
    "logical_domain_not_confidence_interval", "necessary_same_frame_marginals",
    "declared_permitted_remainder", "requested_question_kind", "independent_equal_weight_units",
    "unique_known_sampling_clusters", "specified_alpha", "deterministic_model_domains",
    "hoeffding_outer_sampling_enclosure",
)
QUESTION_KINDS = ("organism_capability", "sample_context_coverage", "unreported")
ORIGINS = ("reported", "graph_derived", "synthetic")
SCOPE_STATUSES = FRAME_STATUSES = ("defined", "unreported")
PAIRINGS = ("paired", "unpaired_marginals", "unknown")
WEIGHT_BASES = ("equal_units", "measured_duration", "measured_volume", "inclusion_weight")
SAMPLING_DESIGNS = ("census", "independent_equal_weight", "unknown")
UNITS = NATIVE_UNITS = ("ppbv_H2_gas", "ppmv_H2_gas", "uM_H2_solution", "percent_O2_gas",
    "percent_O2_saturation_solution", "mM", "uM", "nm", "minutes", "state")
SCOPE_MATCHES = ("matched", "unresolved", "conflicting")
RELATIONS = ("numeric", "supported", "incompatible", "unresolved")
JOINT_SUPPORTS = ("established", "unresolved", "conflicting")
COUNT_RELATIONS = ("exact", "at_least", "at_most", "unknown")
REPLICATE_KINDS = ("biological", "technical", "timepoint", "unknown")
_INPUT_FIELDS = ("question_kind", "origin", "scope_status", "frame_status", "pairing", "weight_basis",
    "sampling_design", "alpha", "permitted_remainder", "requirements", "routes", "contexts", "marginals")
_OBSERVATION_FIELDS = ("requirement_key", "measurement_key", "unit", "interval", "relation", "reported_sd",
    "reported_sem", "reported_plusminus", "reported_count", "count_relation", "replicate_kind")


def empty_context_inputs():
    """Canonical absent-input question, retaining physical [0,1] unknowns."""
    return dict(question_kind="unreported", origin="reported", scope_status="unreported",
        frame_status="unreported", pairing="unknown", weight_basis="equal_units", sampling_design="unknown",
        alpha=None, permitted_remainder=None, requirements=[], routes=None, contexts=[], marginals=[])


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _fields(value, fields, path):
    if not isinstance(value, dict) or set(value) != set(fields):
        _fail("closed_fields_required", path)


def _enum(value, values, path):
    if not isinstance(value, str) or value not in values:
        _fail("unsupported_" + path.rsplit(".", 1)[-1], path)


def _number(value, path, *, nullable=False, positive=False, nonnegative=False):
    if value is None and nullable:
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", path)
    if positive and value <= 0:
        _fail("positive_value_required", path)
    if nonnegative and value < 0:
        _fail("nonnegative_value_required", path)


def _identity(value, path):
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_identity_required", path)


def _array(value, path):
    if not isinstance(value, list):
        _fail("array_required", path)


def _interval(value, path):
    _fields(value, ("lower", "upper", "lower_closed", "upper_closed"), path)
    for side in ("lower", "upper"):
        _number(value[side], path + "." + side, nullable=True)
        if type(value[side + "_closed"]) is not bool:
            _fail("boolean_required", path + "." + side + "_closed")
        if value[side] is None and value[side + "_closed"]:
            _fail("unbounded_endpoint_must_be_open", path)
    lo, hi = value["lower"], value["upper"]
    if lo is not None and hi is not None:
        if lo > hi or (lo == hi and not (value["lower_closed"] and value["upper_closed"])):
            _fail("nonempty_ordered_interval_required", path)


def _validate(inputs):
    _fields(inputs, _INPUT_FIELDS, "inputs")
    for key, values in (("question_kind", QUESTION_KINDS), ("origin", ORIGINS),
        ("scope_status", SCOPE_STATUSES), ("frame_status", FRAME_STATUSES), ("pairing", PAIRINGS),
        ("weight_basis", WEIGHT_BASES), ("sampling_design", SAMPLING_DESIGNS)):
        _enum(inputs[key], values, key)
    _number(inputs["alpha"], "alpha", nullable=True)
    if inputs["alpha"] is not None and not 0 < inputs["alpha"] < 1:
        _fail("alpha_between_zero_and_one_required", "alpha")
    if inputs["permitted_remainder"] is not None and type(inputs["permitted_remainder"]) is not bool:
        _fail("boolean_or_null_required", "permitted_remainder")
    for key in ("requirements", "contexts", "marginals"):
        _array(inputs[key], key)
    requirements = {}
    for i, row in enumerate(inputs["requirements"]):
        path = f"requirements.{i}"
        _fields(row, ("key", "unit", "supported", "incompatible"), path)
        _identity(row["key"], path + ".key")
        _enum(row["unit"], UNITS, path + ".unit")
        if row["key"] in requirements:
            _fail("duplicate_requirement_key", path + ".key")
        requirements[row["key"]] = row
        for key in ("supported", "incompatible"):
            _array(row[key], path + "." + key)
            for j, region in enumerate(row[key]):
                _interval(region, f"{path}.{key}.{j}")
        if row["unit"] == "state" and (row["supported"] or row["incompatible"]):
            _fail("state_domains_must_be_empty", path)
    if inputs["routes"] is not None:
        _array(inputs["routes"], "routes")
        if not inputs["routes"]:
            _fail("nonempty_routes_required", "routes")
        seen = set()
        for i, row in enumerate(inputs["routes"]):
            path = f"routes.{i}"
            _fields(row, ("key", "requirements", "requirements_complete", "joint_support"), path)
            _identity(row["key"], path + ".key")
            if row["key"] in seen:
                _fail("duplicate_route_key", path + ".key")
            seen.add(row["key"])
            _array(row["requirements"], path + ".requirements")
            used = set()
            for key in row["requirements"]:
                _identity(key, path + ".requirements")
                if key not in requirements:
                    _fail("unknown_requirement_key", path + ".requirements")
                if key in used:
                    _fail("duplicate_route_requirement", path + ".requirements")
                used.add(key)
            if type(row["requirements_complete"]) is not bool:
                _fail("boolean_required", path + ".requirements_complete")
            _enum(row["joint_support"], JOINT_SUPPORTS, path + ".joint_support")
    contexts, measurements = {}, {}
    duplicated, aliased = False, False
    for i, row in enumerate(inputs["contexts"]):
        path = f"contexts.{i}"
        _fields(row, ("key", "weight", "cluster_key", "scope_match", "observations"), path)
        _identity(row["key"], path + ".key")
        if row["key"] in contexts and contexts[row["key"]] != row:
            _fail("duplicate_context_conflict", path + ".key")
        _number(row["weight"], path + ".weight", nullable=True, positive=True)
        if inputs["weight_basis"] == "equal_units" and row["weight"] not in (None, 1):
            _fail("equal_unit_weight_must_be_one", path + ".weight")
        if row["cluster_key"] is not None:
            _identity(row["cluster_key"], path + ".cluster_key")
        _enum(row["scope_match"], SCOPE_MATCHES, path + ".scope_match")
        _array(row["observations"], path + ".observations")
        used = set()
        for j, obs in enumerate(row["observations"]):
            opath = f"{path}.observations.{j}"
            _fields(obs, _OBSERVATION_FIELDS, opath)
            for key in ("requirement_key", "measurement_key"):
                _identity(obs[key], opath + "." + key)
            key = obs["requirement_key"]
            if key not in requirements:
                _fail("unknown_requirement_key", opath + ".requirement_key")
            if key in used:
                _fail("duplicate_context_requirement", opath + ".requirement_key")
            used.add(key)
            _enum(obs["unit"], UNITS, opath + ".unit")
            _enum(obs["relation"], RELATIONS, opath + ".relation")
            if obs["interval"] is not None:
                _interval(obs["interval"], opath + ".interval")
            if obs["unit"] == "state":
                if obs["interval"] is not None or obs["relation"] == "numeric":
                    _fail("state_relation_required", opath)
            elif obs["relation"] != "numeric":
                _fail("numeric_relation_required", opath + ".relation")
            for key in ("reported_sd", "reported_sem", "reported_plusminus"):
                _number(obs[key], opath + "." + key, nullable=True, nonnegative=True)
            if obs["unit"] == "state" and any(obs[key] is not None for key in ("reported_sd", "reported_sem", "reported_plusminus")):
                _fail("state_uncertainty_requires_numeric_unit", opath)
            count = obs["reported_count"]
            if count is not None and (type(count) is not int or count < 0):
                _fail("nonnegative_integer_required", opath + ".reported_count")
            _enum(obs["count_relation"], COUNT_RELATIONS, opath + ".count_relation")
            if count is None and obs["count_relation"] != "unknown":
                _fail("missing_count_relation_must_be_unknown", opath + ".count_relation")
            _enum(obs["replicate_kind"], REPLICATE_KINDS, opath + ".replicate_kind")
            signature = {k: v for k, v in obs.items() if k not in ("requirement_key", "measurement_key")}
            mkey = obs["measurement_key"]
            if mkey in measurements and measurements[mkey] != signature:
                _fail("duplicate_measurement_conflict", opath + ".measurement_key")
            if mkey in measurements and row["key"] not in contexts:
                aliased = True
            measurements[mkey] = signature
        if row["key"] in contexts:
            if contexts[row["key"]] != row:
                _fail("duplicate_context_conflict", path + ".key")
            duplicated = True
        else:
            contexts[row["key"]] = row
    seen = set()
    for i, row in enumerate(inputs["marginals"]):
        path = f"marginals.{i}"
        _fields(row, ("requirement_key", "lower", "upper"), path)
        _identity(row["requirement_key"], path + ".requirement_key")
        if row["requirement_key"] not in requirements:
            _fail("unknown_requirement_key", path + ".requirement_key")
        if row["requirement_key"] in seen:
            _fail("duplicate_marginal_key", path + ".requirement_key")
        seen.add(row["requirement_key"])
        for key in ("lower", "upper"):
            _number(row[key], path + "." + key)
        if not 0 <= row["lower"] <= row["upper"] <= 1:
            _fail("ordered_unit_fraction_bounds_required", path)
    if inputs["pairing"] == "paired" and inputs["marginals"]:
        _fail("paired_marginals_must_be_empty", "marginals")
    if inputs["pairing"] == "unpaired_marginals" and inputs["contexts"]:
        _fail("unpaired_contexts_must_be_empty", "contexts")
    return list(contexts.values()), duplicated, aliased


def _lo(row):
    return -math.inf if row["lower"] is None else row["lower"]


def _hi(row):
    return math.inf if row["upper"] is None else row["upper"]


def _overlap(a, b):
    lo, hi = max(_lo(a), _lo(b)), min(_hi(a), _hi(b))
    if lo < hi:
        return True
    if lo > hi or not math.isfinite(lo):
        return False
    return all((row["lower"] != lo or row["lower_closed"]) and
               (row["upper"] != lo or row["upper_closed"]) for row in (a, b))


def _contains(region, value):
    return (_lo(region) < _lo(value) or (_lo(region) == _lo(value) and
        (not value["lower_closed"] or region["lower_closed"]))) and (
        _hi(region) > _hi(value) or (_hi(region) == _hi(value) and
        (not value["upper_closed"] or region["upper_closed"])))


def _covered(value, regions):
    """Containment in a union, merging touching intervals only across no gap."""
    merged = []
    for region in sorted(regions, key=lambda r: (_lo(r), not r["lower_closed"])):
        region = dict(region)
        if not merged:
            merged.append(region)
            continue
        prev = merged[-1]
        join = _lo(region) < _hi(prev) or (_lo(region) == _hi(prev) and
            (region["lower_closed"] or prev["upper_closed"]))
        if not join:
            merged.append(region)
        elif _hi(region) > _hi(prev):
            prev["upper"], prev["upper_closed"] = region["upper"], region["upper_closed"]
        elif _hi(region) == _hi(prev):
            prev["upper_closed"] |= region["upper_closed"]
    return any(_contains(region, value) for region in merged)


def _scope_reasons(inputs, context):
    if inputs["question_kind"] == "unreported":
        return ["question_unreported"]
    if inputs["scope_status"] != "defined":
        return ["scope_unreported"]
    if context["scope_match"] != "matched":
        return ["scope_" + context["scope_match"]]
    return []


def _membership(inputs, context, req, obs):
    reasons = _scope_reasons(inputs, context)
    low, high = 0, 1
    if not reasons:
        if obs is None:
            reasons = ["requirement_unobserved"]
        elif obs["unit"] != req["unit"]:
            reasons = ["unit_basis_mismatch"]
        elif req["unit"] == "state":
            relation = obs["relation"]
            if relation == "supported":
                low = 1
            elif relation == "incompatible":
                high = 0
            else:
                reasons = ["state_relation_unresolved"]
        elif any(_overlap(a, b) for a in req["supported"] for b in req["incompatible"]):
            reasons = ["domain_conflict"]
        elif obs["interval"] is None:
            reasons = ["value_unreported"]
        elif _covered(obs["interval"], req["supported"]):
            low = 1
        elif _covered(obs["interval"], req["incompatible"]):
            high = 0
        else:
            reasons = ["domain_membership_unresolved"]
    return dict(context_key=context["key"], requirement_key=req["key"],
        measurement_key=obs["measurement_key"] if obs else None, unit=obs["unit"] if obs else req["unit"],
        native_observation=deepcopy(obs["interval"]) if obs else None,
        supported_domains=deepcopy(req["supported"]), incompatible_domains=deepcopy(req["incompatible"]),
        ell=low, u=high, reasons=reasons)


def _cell(value, component, *, reason=None, conditional=(), bound=None):
    if value is not None:
        try:
            converted = float(value)
        except (OverflowError, ValueError):
            converted = None
        if converted is not None and math.isfinite(converted):
            exact = Fraction(converted)
            if bound == "lower" and exact > value:
                converted = math.nextafter(converted, -math.inf)
            elif bound == "upper" and exact < value:
                converted = math.nextafter(converted, math.inf)
            elif bound is None and converted == 0 and value != 0:
                converted = None
        if converted is None or not math.isfinite(converted):
            value, reason = None, "numerical_model_range"
        else:
            value, reason = converted, None
    return dict(value=value, unit="context_weight" if component.endswith("weight") else "dimensionless",
        status="unavailable" if value is None else "populated", formula=FORMULAS[component], origin="derived",
        unavailable_reason=reason, conditional_on=list(conditional))


def _sampling_reason(inputs, contexts):
    if inputs["question_kind"] != "sample_context_coverage":
        return "sampling_question_not_coverage"
    if inputs["pairing"] != "paired":
        return "sampling_requires_paired_contexts"
    if inputs["scope_status"] != "defined":
        return "sampling_requires_defined_scope"
    if inputs["frame_status"] != "defined":
        return "sampling_requires_defined_frame"
    if inputs["weight_basis"] != "equal_units" or any(row["weight"] != 1 for row in contexts):
        return "sampling_requires_equal_weights"
    if inputs["sampling_design"] == "census":
        return "sampling_census"
    if inputs["sampling_design"] != "independent_equal_weight":
        return "sampling_design_unknown"
    if not contexts:
        return "sampling_no_context_units"
    if any(row["cluster_key"] is None for row in contexts):
        return "sampling_cluster_unreported"
    if len({row["cluster_key"] for row in contexts}) != len(contexts):
        return "sampling_clusters_not_unique"
    if inputs["alpha"] is None:
        return "sampling_alpha_unreported"
    return None


def _epsilon_upper(alpha, n):
    # Float alpha is an exact binary rational. 2000 digits retains its complete
    # decimal expansion, including subnormals; next_plus encloses ln/sqrt rounding.
    with localcontext() as ctx:
        ctx.prec = 2000
        a = Decimal.from_float(alpha) if type(alpha) is float else Decimal(alpha)
        ratio = (Decimal(2) / a).next_plus()
        log = ratio.ln().next_plus()
        scaled = (log / Decimal(2 * n)).next_plus()
        return Fraction(scaled.sqrt().next_plus())


def populate_context_compatibility(inputs):
    """Validate closed operands and populate logical C/O and optional sampling cells."""
    unique, duplicated, aliased = _validate(inputs)
    qualifications = []
    if duplicated:
        qualifications.append("duplicate_context_coalesced")
    if aliased:
        qualifications.append("shared_measurement_dependency")
    memberships, routes_by_context, contexts = [], [], []
    for context in unique:
        observed = {row["requirement_key"]: row for row in context["observations"]}
        local = [_membership(inputs, context, req, observed.get(req["key"])) for req in inputs["requirements"]]
        memberships.extend(local)
        by_req = {row["requirement_key"]: row for row in local}
        route_results = []
        for route in inputs["routes"] or []:
            reasons = _scope_reasons(inputs, context)
            low = int(all(by_req[key]["ell"] for key in route["requirements"]))
            high = int(all(by_req[key]["u"] for key in route["requirements"]))
            if not route["requirements_complete"]:
                low = 0
                reasons.append("requirements_incomplete")
            if len(route["requirements"]) > 1 and route["joint_support"] != "established":
                low = 0
                reasons.append("joint_support_" + route["joint_support"])
            if _scope_reasons(inputs, context):
                low, high = 0, 1
            result = dict(context_key=context["key"], route_key=route["key"], L=low, U=high, reasons=list(dict.fromkeys(reasons)))
            routes_by_context.append(result)
            route_results.append(result)
        reasons = _scope_reasons(inputs, context)
        if inputs["routes"] is None:
            low, high = 0, 1
            reasons.append("routes_unreported")
        else:
            low, high = int(any(row["L"] for row in route_results)), int(any(row["U"] for row in route_results))
        if reasons:
            low, high = 0, 1
        contexts.append(dict(context_key=context["key"], weight=context["weight"], cluster_key=context["cluster_key"],
            L=low, U=high, reasons=list(dict.fromkeys(reasons))))
    for row in (*memberships, *routes_by_context, *contexts):
        qualifications.extend(row["reasons"])
    known = [row for row in contexts if row["weight"] is not None]
    weights = [Fraction(row["weight"]) for row in known]
    total = sum(weights, Fraction(0))
    supported = sum((w * row["L"] for w, row in zip(weights, known)), Fraction(0))
    unresolved = sum((w * (row["U"] - row["L"]) for w, row in zip(weights, known)), Fraction(0))
    incompatible = total - supported - unresolved
    c_low, c_high = Fraction(0), Fraction(1)
    c_reason = None
    if inputs["question_kind"] == "unreported":
        c_reason = "question_unreported"
    elif inputs["scope_status"] != "defined":
        c_reason = "scope_unreported"
    elif inputs["frame_status"] != "defined":
        c_reason = "frame_unreported"
    elif inputs["pairing"] == "paired":
        if not contexts:
            c_reason = "no_context_units"
        elif len(known) != len(contexts):
            c_reason = "weight_unreported"
        else:
            c_low, c_high = supported / total, (supported + unresolved) / total
    elif inputs["pairing"] == "unpaired_marginals":
        routes = inputs["routes"]
        marginals = {row["requirement_key"]: row for row in inputs["marginals"]}
        if routes is None or len(routes) != 1 or not routes[0]["requirements_complete"] or not set(marginals).issubset(routes[0]["requirements"]):
            c_reason = "unpaired_route_design_unsupported"
        else:
            keys = routes[0]["requirements"]
            lows = [Fraction(marginals[key]["lower"]) if key in marginals else Fraction(0) for key in keys]
            highs = [Fraction(marginals[key]["upper"]) if key in marginals else Fraction(1) for key in keys]
            c_low, c_high = max(Fraction(0), sum(lows, Fraction(0)) - (len(keys) - 1)), min(highs, default=Fraction(1))
            if len(keys) > 1 and routes[0]["joint_support"] != "established":
                c_low = Fraction(0)
                qualifications.append("joint_support_" + routes[0]["joint_support"])
            if any(key not in marginals for key in keys):
                qualifications.append("marginal_unreported")
    else:
        c_reason = "pairing_unknown"
    if c_reason:
        qualifications.append(c_reason)
    o_low, o_high = Fraction(0), Fraction(1)
    o_reason = None
    if inputs["question_kind"] == "unreported":
        o_reason = "question_unreported"
    elif inputs["scope_status"] != "defined":
        o_reason = "scope_unreported"
    elif inputs["pairing"] == "unpaired_marginals":
        o_reason = "unpaired_capability_unavailable"
    else:
        o_low = Fraction(int(any(row["L"] for row in contexts)))
        o_high = Fraction(int(any(row["U"] for row in contexts) or inputs["permitted_remainder"] is not False))
        if inputs["permitted_remainder"] is not False:
            qualifications.append("permitted_remainder_unexamined")
    if o_reason:
        qualifications.append(o_reason)
    if inputs["question_kind"] == "sample_context_coverage":
        selected = c_low, c_high, c_reason
    elif inputs["question_kind"] == "organism_capability":
        selected = o_low, o_high, o_reason
    else:
        selected = Fraction(0), Fraction(1), "question_unreported"
    logical_conditions = ("native_unit_bases_as_declared", "explicit_domain_union", "declared_joint_support",
        "declared_scope", "logical_domain_not_confidence_interval")
    coverage_conditions = (*logical_conditions, "necessary_same_frame_marginals" if inputs["pairing"] == "unpaired_marginals" else "fixed_paired_sample_frame")
    cells = {}
    mass_reason = ("frame_unreported" if inputs["frame_status"] != "defined" else
        "sample_denominator_requires_paired_contexts" if inputs["pairing"] != "paired" else
        "no_context_units" if not contexts else
        "weight_unreported" if len(known) != len(contexts) else None)
    if mass_reason:
        qualifications.append(mass_reason)
    for key, value in zip(COMPONENTS[:4], (total, supported, unresolved, incompatible)):
        cells[key] = _cell(value if mass_reason is None else None, key, reason=mass_reason,
            conditional=(*logical_conditions, "fixed_paired_sample_frame", "known_positive_weights_only"))
    for prefix, lo, hi, reason, conditions in (
        ("coverage", c_low, c_high, c_reason, coverage_conditions),
        ("capability", o_low, o_high, o_reason, (*logical_conditions, "declared_permitted_remainder")),
        ("selected", *selected, (*logical_conditions, "requested_question_kind")),
    ):
        for side, value in (("lower", lo), ("upper", hi)):
            key = prefix + "_" + side
            cells[key] = _cell(value, key, conditional=conditions, bound=side)
        key = prefix + "_point"
        cells[key] = _cell(lo if lo == hi else None, key, reason=reason or ("capability_unresolved" if prefix == "capability" or (prefix == "selected" and inputs["question_kind"] == "organism_capability") else "coverage_unresolved"), conditional=conditions)
    sampling_reason = _sampling_reason(inputs, unique)
    actual_n = len(contexts) if sampling_reason is None else None
    sampling_conditions = ("independent_equal_weight_units", "unique_known_sampling_clusters", "specified_alpha",
        "deterministic_model_domains", "hoeffding_outer_sampling_enclosure")
    if sampling_reason is None:
        epsilon = _epsilon_upper(inputs["alpha"], actual_n)
        sampling_low, sampling_high = max(Fraction(0), c_low - epsilon), min(Fraction(1), c_high + epsilon)
    else:
        sampling_low = sampling_high = None
        qualifications.append(sampling_reason)
    for side, value in (("lower", sampling_low), ("upper", sampling_high)):
        key = "sampling_" + side
        cells[key] = _cell(value, key, reason=sampling_reason, conditional=sampling_conditions, bound=side)
    if any(row["unavailable_reason"] == "numerical_model_range" for row in cells.values()):
        qualifications.append("numerical_model_range")
    return dict(version=VERSION, inputs=deepcopy(inputs), cells={key: cells[key] for key in COMPONENTS},
        memberships=memberships, routes_by_context=routes_by_context, contexts=contexts,
        counts=dict(context_units=len(contexts), distinct_known_clusters=len({row["cluster_key"] for row in unique if row["cluster_key"] is not None}), actual_sampling_n=actual_n),
        qualifications=list(dict.fromkeys(qualifications)))


__all__ = ["VERSION", "COMPONENTS", "FORMULAS", "REASONS", "CONDITIONAL_CODES", "QUESTION_KINDS", "ORIGINS",
    "SCOPE_STATUSES", "FRAME_STATUSES", "PAIRINGS", "WEIGHT_BASES", "SAMPLING_DESIGNS", "UNITS", "NATIVE_UNITS",
    "SCOPE_MATCHES", "RELATIONS", "JOINT_SUPPORTS", "COUNT_RELATIONS", "REPLICATE_KINDS",
    "empty_context_inputs", "populate_context_compatibility"]
