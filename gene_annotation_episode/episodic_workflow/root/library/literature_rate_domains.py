"""Exact reported-operand enclosures, without sampling or independence claims.

Marginal source limits define a Cartesian enclosure, not co-attainability or a
confidence interval. Finite JSON numbers are outward projections of retained
rationals. This module neither reads scientific sources nor fits a model.
"""
from copy import deepcopy
from fractions import Fraction
import math

VERSION = "reported_rate_domain_v1"
from gene_annotation_episode.episodic_workflow.root.library.literature_rate_domain_return_schema import NAMESPACE
DERIVED = ("rate_difference", "retained_fraction", "fractional_decrease")
INF = math.inf


def _point(value):
    return (value, True, value, True)


def _contains_zero(a):
    return (a[0] < 0 or a[0] == 0 and a[1]) and (a[2] > 0 or a[2] == 0 and a[3])


def _subtract(a, b):
    lower = -INF if a[0] == -INF or b[2] == INF else a[0] - b[2]
    upper = INF if a[2] == INF or b[0] == -INF else a[2] - b[0]
    return (lower, a[1] and b[3], upper, a[3] and b[1])


def _multiply(a, b):
    if a == _point(Fraction(0)) or b == _point(Fraction(0)):
        return _point(Fraction(0))
    candidates = []
    for x, xc in ((a[0], a[1]), (a[2], a[3])):
        for y, yc in ((b[0], b[1]), (b[2], b[3])):
            # Zero times an infinite endpoint is a limit, not NaN or a
            # measurement. Actual zero attainment is handled separately.
            value = (Fraction(0) if x == 0 or y == 0 else
                (INF if (x > 0) == (y > 0) else -INF) if x in (-INF, INF) or y in (-INF, INF) else x * y)
            closed = value not in (-INF, INF) and xc and yc
            candidates.append((value, closed))
    lower, upper = min(x for x, _ in candidates), max(x for x, _ in candidates)
    zero_attained = _contains_zero(a) or _contains_zero(b)
    return (lower, any(c for x, c in candidates if x == lower) or lower == 0 and zero_attained,
            upper, any(c for x, c in candidates if x == upper) or upper == 0 and zero_attained)


def _divide(b, a):
    if _contains_zero(a):
        return None
    inverse = (Fraction(0) if a[2] == INF else -INF if a[2] == 0 else 1 / a[2],
               a[3] if a[2] not in (-INF, INF, 0) else False,
               Fraction(0) if a[0] == -INF else INF if a[0] == 0 else 1 / a[0],
               a[1] if a[0] not in (-INF, INF, 0) else False)
    return _multiply(b, inverse)


def _encode(interval):
    if interval is None:
        return None
    def number(value):
        return None if value in (-INF, INF) else {"numerator": str(value.numerator), "denominator": str(value.denominator)}
    return {"lower": number(interval[0]), "lower_inclusive": bool(interval[1]),
            "upper": number(interval[2]), "upper_inclusive": bool(interval[3])}


def _project(interval, *, basis, conditioning, failure=None):
    result = {"kind": "undefined" if failure == "zero_reference_rate" else "unavailable",
        "lower": None, "upper": None, "lower_inclusive": False, "upper_inclusive": False,
        "projection": "none", "basis": basis, "conditioning": conditioning,
        "failure": failure}
    if interval is None:
        return result
    values, closed, outward, range_loss = [], [], False, False
    for index in (0, 2):
        exact = interval[index]
        if exact in (-INF, INF):
            values.append(None)
            closed.append(False)
            continue
        try:
            value = float(exact)
            if not math.isfinite(value):
                raise OverflowError
            inclusive = bool(interval[index + 1])
            if value == 0 and exact != 0:
                # Retain sign information and an outward subnormal endpoint;
                # this zero is an open logical limit, never a point estimate.
                value = (0.0 if exact > 0 else -math.ulp(0.0)) if index == 0 else (math.ulp(0.0) if exact > 0 else 0.0)
                inclusive, range_loss = False, True
            rounded = Fraction(value)
            if index == 0 and rounded > exact:
                value = math.nextafter(value, -INF)
            if index == 2 and rounded < exact:
                value = math.nextafter(value, INF)
            if not math.isfinite(value):
                raise OverflowError
            outward |= Fraction(value) != exact
            values.append(value)
            closed.append(inclusive)
        except (OverflowError, ValueError):
            # Relax only the endpoint that cannot be represented. Its other
            # endpoint can still carry useful numerical information.
            positive = exact > 0
            value = (math.nextafter(INF, 0) if positive else None) if index == 0 else (None if positive else math.nextafter(-INF, 0))
            values.append(value)
            closed.append(False)
            outward, range_loss = True, True
    lower, upper = values
    kind = ("unbounded" if lower is None and upper is None else
            "upper_bounded" if lower is None else "lower_bounded" if upper is None else
            "point" if lower == upper else "finite_interval")
    result.update(kind=kind, lower=lower, upper=upper,
        lower_inclusive=closed[0], upper_inclusive=closed[1],
        projection="outward" if outward else "exact",
        failure="numerical_model_range" if range_loss else None)
    return result


def _operand(row):
    from .literature_rate_native_inputs import _scale
    if row is None:
        return None, "source_measurement_unavailable"
    source = row["source"]
    unit, number = source["unit"], source["number"]
    reason = ("source_rate_unit_unreported" if number and unit is None else
        unit["unavailable_reason"] if unit and unit["unavailable_reason"] else
        "conflicting_measurement" if row["status"] == "conflicting" else
        "source_measurement_unavailable" if number is None else None)
    if reason:
        return None, reason
    q = Fraction(number["raw_number"].replace("−", "-")) * _scale(unit)
    return {"point": _point(q), "lt": (-INF, False, q, False),
        "le": (-INF, False, q, True), "gt": (q, False, INF, False),
        "ge": (q, True, INF, False)}[number["relation"]], None


def native_domain_trace(extraction, cells):
    """Basic algebra on already validated retained operands; no profile refit."""
    from .literature_rate_return_schema import RATE_UNITS
    from .literature_rate_native_inputs import native_pair_reason
    rows = {row["arm"]: row for row in extraction["rows"]}
    a, ar = _operand(rows.get("reference"))
    b, br = _operand(rows.get("test"))
    pair_reason = native_pair_reason(extraction)
    if all(rows.get(role) and rows[role]["unit"] for role in ("reference", "test")):
        if RATE_UNITS[rows["reference"]["unit"]][0] != RATE_UNITS[rows["test"]["unit"]][0]:
            pair_reason = "incompatible_rate_dimensions"
    # A censor qualifier must never mask a separate comparability failure.
    pair_reason = pair_reason or ar or br
    images = {"reference_rate": (a, ar), "test_rate": (b, br)}
    ratio = _divide(b, a) if pair_reason is None else None
    ratio_reason = pair_reason or ("zero_reference_rate" if ratio is None else None)
    images.update(rate_difference=(_subtract(a, b) if pair_reason is None else None, pair_reason),
        retained_fraction=(ratio, ratio_reason),
        fractional_decrease=(_subtract(_point(Fraction(1)), ratio) if ratio is not None else None, ratio_reason))
    components = {}
    def identity(row):
        source = row["source"]
        return (deepcopy(source["location"]) if source["location"] is not None else
            {"source_ref": source["source_ref"], "artifact_ref": source["artifact_ref"],
             "start": None, "end": None, "arm": row["arm"]})
    for name, cell in cells.items():
        interval, failure = images.get(name, (
            _point(Fraction(cell["value"])) if cell["value"] is not None else None,
            cell["unavailable_reason"]))
        basis = ("reported_operand_algebra" if name in DERIVED else
            "reported_point" if name in ("reference_rate", "test_rate") and interval and interval[0] == interval[2] else
            "reported_censoring" if name in ("reference_rate", "test_rate") else "stored_numerical_point")
        conditioning = "reported_endpoint_normalization_unit_relations" if name in DERIVED else "stored_source_cell"
        roles = ("reference",) if name in ("reference_rate", "reference_mean_se") else ("test",) if name in ("test_rate", "test_mean_se") else ("reference", "test")
        components[name] = {"input_rows": [identity(rows[role]) for role in roles if role in rows], "image": _encode(interval),
            "reported_domain": _project(interval, basis=basis, conditioning=conditioning, failure=failure)}
    return {"version": VERSION, "components": components}


def apply_native_domains(cells, trace):
    """Populate supported existing scalar/bound slots; full image stays in trace."""
    for name in DERIVED:
        cell = cells[name]
        domain = trace["components"][name]["reported_domain"]
        kind = domain["kind"]
        if domain["failure"]:
            cell.update(value=None, status="unavailable", unavailable_reason=domain["failure"])
        if kind in ("lower_bounded", "upper_bounded"):
            side = "lower" if kind == "lower_bounded" else "upper"
            cell.update(threshold=domain[side], bound=("g" if side == "lower" else "l") +
                ("e" if domain[side + "_inclusive"] else "t"))
        elif domain["failure"] is None:
            image = trace["components"][name]["image"]
            if image is not None and image["lower"] is not None and image["lower"] == image["upper"]:
                exact = image["lower"]
                value = float(Fraction(int(exact["numerator"]), int(exact["denominator"])))
                cell.update(value=value, status="populated", unavailable_reason=None)


from gene_annotation_episode.episodic_workflow.root.library.literature_rate_domain_return_schema import rate_source_domain_cells_schema
from gene_annotation_episode.episodic_workflow.root.library.literature_rate_domain_display import is_row
from gene_annotation_episode.episodic_workflow.root.library.literature_rate_domain_display import base_rows
from gene_annotation_episode.episodic_workflow.root.library.literature_rate_domain_display import rows_from_reports
from gene_annotation_episode.episodic_workflow.root.library.literature_rate_domain_display import hidden_records
from gene_annotation_episode.episodic_workflow.root.library.literature_rate_domain_display import own_rows
from gene_annotation_episode.episodic_workflow.root.library.literature_rate_domain_display import render_received
from gene_annotation_episode.episodic_workflow.root.library.literature_rate_domain_display import render_domains
