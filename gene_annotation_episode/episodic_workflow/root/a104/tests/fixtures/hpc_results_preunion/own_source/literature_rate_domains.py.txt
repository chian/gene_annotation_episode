"""Exact reported-operand enclosures, without sampling or independence claims.

Marginal source limits define a Cartesian enclosure, not co-attainability or a
confidence interval. Finite JSON numbers are outward projections of retained
rationals. This module neither reads scientific sources nor fits a model.
"""
from copy import deepcopy
from fractions import Fraction
import math

VERSION = "reported_rate_domain_v1"
NAMESPACE = "literature_rate_source_domain_cells"
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
    from .literature_experimental_contracts import RATE_UNITS
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


def rate_source_domain_cells_schema():
    """A separate closed view; existing native rows remain unchanged."""
    from .domain import obj
    from .literature_rate_storage import rate_source_cells_schema, UNAVAILABLE_REASONS
    from .literature_rate_native_inputs import NATIVE_REASONS
    schema = rate_source_cells_schema()
    schema["x-source"] = NAMESPACE
    properties = schema["items"]["properties"]
    properties["reported_domain"] = obj({
        "kind": {"type": "string", "enum": ["point", "lower_bounded", "upper_bounded", "finite_interval", "unbounded", "undefined", "unavailable", "numerical_range"]},
        "lower": {"type": ["number", "null"]}, "upper": {"type": ["number", "null"]},
        "lower_inclusive": {"type": "boolean"}, "upper_inclusive": {"type": "boolean"},
        "projection": {"type": "string", "enum": ["exact", "outward", "none"]},
        "basis": {"type": "string", "enum": ["reported_point", "reported_censoring", "reported_operand_algebra", "stored_numerical_point", "legacy_stored_cell"]},
        "conditioning": {"type": "string", "enum": ["reported_endpoint_normalization_unit_relations", "stored_source_cell"]},
        "failure": {"type": ["string", "null"], "enum": [*UNAVAILABLE_REASONS, *NATIVE_REASONS, None]}})
    schema["items"]["required"] = list(properties)
    return schema


# These pure view helpers deliberately preserve the original native masking and
# scientific label renderer. Domain rows never fall through a generic record
# expansion merely because their closed contract has an additional field.
def is_row(value):
    from collections.abc import Mapping
    from jsonschema import Draft202012Validator
    # Use a module-level cache assigned lazily to avoid the storage import cycle.
    global _domain_row_validator
    if "_domain_row_validator" not in globals():
        _domain_row_validator = Draft202012Validator(rate_source_domain_cells_schema()["items"])
    from .communication import plain
    return isinstance(value, Mapping) and _domain_row_validator.is_valid(plain(value))


def base_rows(rows):
    """Validate exact new rows before presenting their original native fields."""
    from .domain import ContractError
    from .communication import plain
    result = []
    for row in rows:
        if not is_row(row):
            raise ContractError("literature_rate_domain_display_contract_mismatch")
        result.append({key: plain(value) for key, value in row.items() if key != "reported_domain"})
    return result


def rows_from_reports(reports):
    from collections.abc import Mapping
    for report in reports:
        if isinstance(report, Mapping):
            for rows in report.values():
                if isinstance(rows, (list, tuple)) and rows and all(is_row(row) for row in rows):
                    yield from rows


def hidden_records(rows):
    from .literature_rate_source_render import hidden_records as native_hidden_records
    return native_hidden_records(base_rows(rows))


def own_rows(content, display_rows):
    from .literature_rate_source_render import own_rows as native_own_rows
    display_rows = list(display_rows)
    matched = {(row["sheet_ref"], row["component"]) for row in native_own_rows(content, base_rows(display_rows))}
    return [row for row in display_rows if (row["sheet_ref"], row["component"]) in matched]


def render_received(parts, rows, records, *, section, table, comparison_number=None):
    from .literature_rate_source_render import render_received as native_render_received
    rows = list(rows)
    if not rows:
        return
    native_render_received(parts, base_rows(rows), records, section=section, table=table,
        comparison_number=comparison_number)
    render_domains(parts, rows, section=section, table=table)


def render_domains(parts, rows, *, section, table):
    """Only actually returned domain fields, after their common base is shown."""
    from .literature_rate_source_render import _COMPONENTS
    rows = list(rows)
    base_rows(rows)
    section(parts, "Reported-operand numerical domains",
        "Conditional logical enclosures of the reported operands with the recorded endpoint, normalization and units. "
        "Outward projection marks numerical rounding; approximation remains separate. These are not sampling confidence intervals "
        "or evidence of independence or endpoint co-attainability. Status above concerns the point estimate.")
    section(parts, "Requested reported domains", table(
        ("Component", "Domain kind", "Lower", "Lower inclusive", "Upper", "Upper inclusive", "Numerical projection", "Basis", "Conditioning", "Failure"),
        ((_COMPONENTS[row["component"]], *(row["reported_domain"][field] for field in
          ("kind", "lower", "lower_inclusive", "upper", "upper_inclusive", "projection", "basis", "conditioning", "failure"))) for row in rows)))
