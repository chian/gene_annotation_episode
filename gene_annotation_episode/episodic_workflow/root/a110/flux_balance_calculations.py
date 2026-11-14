"""The sole numerical authority for saved continuous flux-balance evidence.

Equations use effective solver variables, including split and auxiliary columns.
Native numbers remain untouched. Every comparison needs its explicit parameter;
solver settings are evidence and never implicit diagnostic tolerances.
"""
from __future__ import annotations

from copy import deepcopy
from collections import defaultdict
import json
import math

from .flux_balance_contracts import validate_flux_balance_record
from .flux_balance_sheet import validate_flux_balance_sheet
from .execution_contracts import digest

__all__ = ["calculate_flux_balance_sheet"]

_UNKNOWN_UNIT = {"native_text": None, "basis": "unknown", "source": None}
_FRACTION_UNIT = {"native_text": "1", "basis": "supplied", "source": None}


def _issue(code, *, field=None, reaction_position=None, variable_position=None, constraint_position=None):
    return {"code": code, "stage": "calculate", "field": field, "source_row_index": None,
        "reaction_position": reaction_position, "metabolite_position": None,
        "variable_position": variable_position, "constraint_position": constraint_position, "detail_file": None}


def _cell(value=None, *, state=None, unit=None, codes=()):
    return {"value": value, "state": state or ("calculated" if value is not None else "missing"),
        "unit": deepcopy(unit if unit is not None else _UNKNOWN_UNIT), "issue_codes": list(dict.fromkeys(codes))}


def _missing(reason="not_returned"):
    return {"value": None, "state": "missing", "native_token": None, "float_hex": None,
        "precision": "unknown", "source": None, "missing_reason": reason}


def _ambiguous(rows, key):
    result = _missing()
    source = next((row[key]["source"] for row in rows if row[key]["source"] is not None), None)
    if source is not None:
        result.update(state="invalid", source=deepcopy(source), missing_reason=None)
    return result


def _present(number):
    return number["state"] == "present"


def _as_cell(number, unit, missing_code):
    if _present(number):
        return _cell(number["value"], unit=unit)
    return _cell(state="invalid" if number["state"] in {"invalid", "nonfinite"} else "missing",
        unit=unit, codes=[missing_code])


def _linear_combination(constant, pairs, *, complete, unit):
    """Accurately sum one recorded equation; no absent coefficient is invented.

    ``pairs`` contains (coefficient Number/Cell, operand Number/Cell). A proven
    zero coefficient needs no primal. The count is usable retained terms, not a
    claim that an incomplete sparse population has been reconstructed.
    """
    products = []
    codes = []
    states = []
    available = 0
    if not complete:
        codes.append("term_population_incomplete")
        states.append("missing")
    if constant["value"] is None:
        codes.extend(constant.get("issue_codes", ["coefficient_nonfinite"]))
        states.append("invalid" if constant["state"] == "nonfinite" else constant["state"] if constant["state"] in {"invalid", "overflow", "incompatible"} else "missing")
    else:
        products.append(constant["value"])
    for coefficient, operand in pairs:
        if coefficient["value"] is None:
            states.append("invalid" if coefficient["state"] in {"invalid", "nonfinite"} else "missing")
            codes.append("coefficient_nonfinite")
            continue
        if coefficient["value"] == 0:
            available += 1
            continue
        if operand["value"] is None:
            states.append("invalid" if operand["state"] == "nonfinite" else operand["state"] if operand["state"] in {"invalid", "overflow", "incompatible"} else "missing")
            codes.extend(operand.get("issue_codes", ["variable_nonfinite" if operand["state"] == "nonfinite" else "variable_missing"]))
            continue
        try:
            product = coefficient["value"] * operand["value"]
            if not math.isfinite(product):
                raise OverflowError
        except OverflowError:
            states.append("overflow"); codes.append("numeric_overflow")
            continue
        products.append(product)
        available += 1
    if states:
        state = next(item for item in ("overflow", "invalid", "incompatible", "missing") if item in states)
        return _cell(state=state, unit=unit, codes=codes), available
    try:
        total = math.fsum(products)
        if not math.isfinite(total):
            raise OverflowError
    except (OverflowError, ValueError):
        return _cell(state="overflow", unit=unit, codes=["numeric_overflow"]), available
    return _cell(total, unit=unit), available


def _literal(value):
    # Internal exact algebraic constants, never retained as native observations.
    return {"value": value, "state": "calculated", "issue_codes": []}


def _difference(left, right, unit):
    return _linear_combination(_literal(0), [(_literal(1), left), (_literal(-1), right)],
        complete=True, unit=unit)[0]


def _compatible(left, right):
    # A caller-supplied tolerance in unknown units is explicitly tied to this
    # exact native entity, so a single-equation comparison remains meaningful.
    # A known declaration conflicting with unknown/another unit cannot convert.
    if left["basis"] == right["basis"] == "unknown":
        return left["native_text"] == right["native_text"]
    return left["native_text"] is not None and left["native_text"] == right["native_text"]


def _parameter(tolerances, identifier, unit):
    tolerance = tolerances.get(identifier)
    if tolerance is None:
        return None, "missing_parameters"
    if not _compatible(unit, tolerance["unit"]):
        return None, "unit_incompatible"
    return tolerance["value"], None


def _bound_checks(primal, lower, upper, unit, tolerance, parameter_issue):
    """Shared slacks/violations for variables, reactions and constraint rows.

    Counts are finite sides with a computed violation AND applicable tolerance.
    Infinite sides are not_applicable. A known empty bound set passes only for
    an actual finite point. Missing operands never pass by vacuous comparison.
    """
    result = {}
    comparisons = []
    evaluated = violated = 0
    for side, bound, infinite in (("lower", lower, "negative_infinity"), ("upper", upper, "positive_infinity")):
        if bound["kind"] == infinite:
            slack = violation = _cell(state="not_applicable", unit=unit)
        elif bound["kind"] != "finite":
            slack = violation = _cell(state="invalid" if bound["kind"] == "invalid" else "missing", unit=unit, codes=["bound_invalid"])
            comparisons.append("unknown")
        elif primal["value"] is None:
            slack = violation = _cell(state=primal["state"] if primal["state"] in {"invalid", "overflow", "incompatible"} else "missing",
                unit=unit, codes=primal.get("issue_codes", ()))
            comparisons.append("unknown")
        else:
            operand = _literal(bound["value"])
            slack = _difference(primal, operand, unit) if side == "lower" else _difference(operand, primal, unit)
            if slack["value"] is None:
                violation = deepcopy(slack); comparisons.append("unknown")
            else:
                violation = _cell(max(-slack["value"], 0.0), unit=unit)
                if tolerance is None:
                    violation["issue_codes"].append(parameter_issue or "missing_parameters")
                    comparisons.append("unknown")
                else:
                    failed = violation["value"] > tolerance
                    evaluated += 1; violated += int(failed)
                    comparisons.append("fails" if failed else "passes")
        result[side + "_slack"] = deepcopy(slack)
        result[side + "_violation"] = deepcopy(violation)
    if primal["value"] is None:
        comparisons.append("unknown")
    result["comparison"] = "fails" if "fails" in comparisons else "unknown" if "unknown" in comparisons else "passes"
    return result, evaluated, violated


def _native_difference(native, calculated, unit, tolerance, parameter_issue=None, *, calculated_precision="full_native"):
    difference = _difference(_as_cell(native, unit, "input_missing"), calculated, unit)
    comparison = "unknown"
    if difference["value"] is not None:
        if tolerance is None:
            difference["issue_codes"].append(parameter_issue or "missing_parameters")
        elif native["precision"] == "unknown" or calculated_precision == "unknown":
            difference["issue_codes"].append("source_precision_unknown")
        else:
            # The legacy writer reports six decimal places. Its rounding envelope
            # belongs to that source, not to the explicit diagnostic tolerance.
            envelope = (0.5e-6 if native["precision"] == "formatted_6dp" else 0.0)
            envelope += 0.5e-6 if calculated_precision == "formatted_6dp" else 0.0
            comparison = "agrees" if abs(difference["value"]) <= tolerance + envelope else "conflicts"
            if comparison == "conflicts":
                difference["issue_codes"].append("native_derived_conflict")
    return difference, comparison


def _selected_values(rows, position_key, number_key):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[position_key]].append(row)
    numbers, duplicate_positions = {}, set()
    for position, items in grouped.items():
        if len(items) == 1:
            numbers[position] = deepcopy(items[0][number_key])
        else:
            numbers[position] = _ambiguous(items, number_key)
            duplicate_positions.add(position)
    return numbers, duplicate_positions


def _coverage(valid, expected):
    if expected is None:
        return _cell(unit=_FRACTION_UNIT, codes=["partial_population"])
    if expected == 0:
        return _cell(unit=_FRACTION_UNIT, codes=["zero_denominator"])
    return _cell(valid / expected, unit=_FRACTION_UNIT,
        codes=["partial_population"] if valid != expected else ())


def _all_issues(sheet):
    issues = []
    for item in (sheet, sheet["models"], sheet["problems"], sheet["native_solution"], sheet["native"],
            sheet["problems"]["loaded_original"], sheet["problems"]["effective"], sheet["native_solution"]["native"]):
        if item is not None:
            issues.extend(deepcopy(item.get("issues", [])))
    return issues


def _validate_selections(parameters, model, problem):
    reactions = {row["id"] for row in model["reactions"]} if model else set()
    variables = {row["id"] for row in problem["variables"]} if problem else set()
    constraints = {row["id"] for row in problem["constraints"]} if problem else set()
    indexes = {}
    for key in ("reaction_bound_tolerances", "constraint_tolerances", "active_flux_thresholds",
            "variable_bound_tolerances", "reaction_flux_tolerances", "constraint_activity_tolerances"):
        allowed = variables if key == "variable_bound_tolerances" else constraints if key.startswith("constraint") else reactions
        if any(row["subject_id"] not in allowed for row in parameters[key]):
            raise ValueError("missing_parameters:/" + key + "/subject_id")
        indexes[key] = {row["subject_id"]: row for row in parameters[key]}
    return indexes


def _objective_check(problem, solution, native, parameters, primals):
    objective = problem["objective"] if problem else None
    unit = objective["unit"] if objective else _UNKNOWN_UNIT
    if objective and objective["expression_kind"] == "linear":
        pairs = [(term["coefficient"], primals.get(term["variable_position"], _missing())) for term in objective["terms"]]
        basis, _ = _linear_combination(objective["native_constant"], pairs, complete=objective["terms_complete"], unit=unit)
        full, _ = _linear_combination(objective["interface_offset"], [(_literal(1), basis)], complete=True, unit=unit)
    else:
        basis = full = _cell(state="incompatible" if objective else "missing", unit=unit,
            codes=["unsupported_problem_form" if objective else "objective_unavailable"])
    result = {"native_basis_calculated": basis, "full_calculated": full}
    for name, source_key in (("glpk", "native_glpk_objective"), ("optlang", "native_optlang_objective"),
            ("cobra", "native_cobra_objective"), ("legacy", None)):
        value = native["objective"] if name == "legacy" else solution[source_key] if solution else _missing()
        result["native_" + name] = deepcopy(value)
        difference, comparison = _native_difference(value, basis if name == "glpk" else full,
            unit, parameters["objective_absolute_tolerance"])
        result[name + "_minus_calculated"] = difference
        result[name + "_comparison"] = comparison
    return result


def calculate_flux_balance_sheet(sheet: dict, *, parameters: dict) -> dict:
    """Calculate candidate diagnostics from a detached saved sheet only.

    This function makes no I/O or scientific-library calls. Constraint checks
    do not assert optimality or whole-model infeasibility. Native solver statuses
    and objective discrepancies are separate retained observations.
    """
    sheet = validate_flux_balance_sheet(sheet)
    parameters = validate_flux_balance_record("FBACalculationParameters", parameters)
    model = sheet["models"]["effective"]
    problem = sheet["problems"]["effective"]
    solution = sheet["native_solution"]["native"]
    native = sheet["native"]
    settings = _validate_selections(parameters, model, problem)
    issues = _all_issues(sheet)
    primals, duplicate_variables = _selected_values(solution["variable_values"] if solution else [], "variable_position", "primal")
    native_fluxes, duplicate_reactions = _selected_values(solution["reaction_values"] if solution else [], "reaction_position", "flux")
    native_activities, duplicate_constraints = _selected_values(solution["constraint_values"] if solution else [], "constraint_position", "activity")
    # A reader may recover independent rows and retain the duplicate's identity
    # as an issue. Such a conflict is not permission to choose a CSV replacement.
    unusable_reactions, unusable_variables, unusable_constraints = set(), set(), set()
    if solution:
        for issue in solution["issues"]:
            for key, codes, positions in (("reaction_position", {"duplicate_reaction_id", "flux_identity_conflict", "schema_invalid"}, unusable_reactions),
                    ("variable_position", {"duplicate_variable_id", "variable_identity_conflict", "schema_invalid"}, unusable_variables),
                    ("constraint_position", {"duplicate_constraint_id", "constraint_identity_conflict", "schema_invalid"}, unusable_constraints)):
                if issue["code"] in codes and issue[key] is not None:
                    positions.add(issue[key])
    for positions, code, key in ((duplicate_variables, "duplicate_variable_id", "variable_position"),
            (duplicate_reactions, "duplicate_reaction_id", "reaction_position"),
            (duplicate_constraints, "duplicate_constraint_id", "constraint_position")):
        for position in sorted(positions):
            issues.append(_issue(code, **{key: position}))
    for position in duplicate_variables | unusable_variables:
        primals[position] = _missing("decode_failed")
    for position in duplicate_constraints | unusable_constraints:
        native_activities[position] = _missing("decode_failed")
    variables = problem["variables"] if problem else []
    # A missing model column cannot establish an ID/position association merely
    # because a value still appears at that position in a partial solution.
    primals = {row["position"]: primals[row["position"]] for row in variables if row["position"] in primals}
    variable_checks = []
    evaluated_variable_sides = violated_variable_sides = 0
    for variable in variables:
        primal = primals.get(variable["position"], _missing())
        unit = variable["unit"]
        tolerance, parameter_issue = _parameter(settings["variable_bound_tolerances"], variable["id"], unit)
        bounds, evaluated, violated = _bound_checks(_as_cell(primal, unit, "variable_missing"), variable["lower"], variable["upper"], unit, tolerance, parameter_issue)
        comparison = bounds.pop("comparison")
        variable_checks.append({"variable_position": variable["position"], "variable_id": variable["id"],
            "primal": deepcopy(primal), **bounds, "bound_comparison": comparison})
        evaluated_variable_sides += evaluated; violated_variable_sides += violated
    csv_by_id = defaultdict(list)
    for row in native["flux_rows"]:
        csv_by_id[row["reaction_id"]].append(row)
    joins = {row["reaction_position"]: row for row in problem["reaction_variables"]} if problem else {}
    variable_units = {row["position"]: row["unit"] for row in variables}
    reactions = model["reactions"] if model else []
    reaction_checks = []
    evaluated_reaction_sides = violated_reaction_sides = 0
    reaction_consistency_complete = True
    for reaction in reactions:
        position, identifier, unit = reaction["position"], reaction["id"], reaction["flux_unit"]
        actual = native_fluxes.get(position, _missing())
        csv_rows = csv_by_id[identifier]
        csv_identified = (len(csv_rows) == 1 and csv_rows[0]["reaction_position"] == position
            and csv_rows[0]["association"] in {"matched", "conflicting"})
        csv = csv_rows[0]["flux"] if csv_identified else _ambiguous(csv_rows, "flux") if csv_rows else _missing()
        if position in duplicate_reactions | unusable_reactions:
            flux, basis = _ambiguous([row for row in (solution["reaction_values"] if solution else []) if row["reaction_position"] == position], "flux"), "unavailable"
        elif _present(actual):
            flux, basis = actual, "native_solution"
        elif actual["state"] == "missing" and _present(csv) and csv_rows[0]["association"] == "matched":
            flux, basis = csv, "flux_csv"
        else:
            flux = actual if actual["state"] != "missing" else csv if not _present(csv) else _missing("decode_failed")
            basis = "unavailable"
        tolerance, parameter_issue = _parameter(settings["reaction_bound_tolerances"], identifier, unit)
        bounds, evaluated, violated = _bound_checks(_as_cell(flux, unit, "flux_missing"), reaction["lower"], reaction["upper"], unit, tolerance, parameter_issue)
        comparison = bounds.pop("comparison")
        evaluated_reaction_sides += evaluated; violated_reaction_sides += violated
        flux_tolerance, flux_parameter_issue = _parameter(settings["reaction_flux_tolerances"], identifier, unit)
        csv_difference, csv_comparison = _native_difference(csv, _as_cell(flux, unit, "flux_missing"), unit,
            flux_tolerance, flux_parameter_issue, calculated_precision=flux["precision"])
        join = joins.get(position)
        if join is None:
            net = _cell(unit=unit, codes=["variable_missing"])
        elif any(not _compatible(unit, variable_units.get(join[key], _UNKNOWN_UNIT)) for key in ("forward_variable_position", "reverse_variable_position")):
            net = _cell(state="incompatible", unit=unit, codes=["unit_incompatible"])
        else:
            net, _ = _linear_combination(_literal(0), [(_literal(1), primals.get(join["forward_variable_position"], _missing())),
                (_literal(-1), primals.get(join["reverse_variable_position"], _missing()))], complete=True, unit=unit)
        net_difference, net_comparison = _native_difference(flux, net, unit, flux_tolerance, flux_parameter_issue)
        threshold, threshold_issue = _parameter(settings["active_flux_thresholds"], identifier, unit)
        active = abs(flux["value"]) > threshold if _present(flux) and threshold is not None else None
        if threshold_issue:
            issues.append(_issue(threshold_issue, field="active_flux_thresholds", reaction_position=position))
        if basis != "native_solution" or net_comparison != "agrees":
            reaction_consistency_complete = False
        reaction_checks.append({"reaction_position": position, "flux": deepcopy(flux), **bounds, "bound_comparison": comparison,
            "active": active, "flux_basis": basis, "csv_flux": deepcopy(csv), "csv_minus_flux": csv_difference,
            "csv_flux_comparison": csv_comparison, "variable_net_flux": net,
            "native_minus_variable_net_flux": net_difference, "variable_net_comparison": net_comparison})
    constraint_checks = []
    constraints = problem["constraints"] if problem else []
    for constraint in constraints:
        position, identifier, unit = constraint["position"], constraint["id"], constraint["unit"]
        supported = constraint["expression_kind"] == "linear" and constraint["indicator_variable_position"] is None
        if supported:
            activity, available = _linear_combination(constraint["constant"], [
                (term["coefficient"], primals.get(term["variable_position"], _missing())) for term in constraint["terms"]],
                complete=constraint["terms_complete"], unit=unit)
        else:
            activity, available = _cell(state="incompatible", unit=unit, codes=["unsupported_problem_form"]), 0
        tolerance, parameter_issue = _parameter(settings["constraint_tolerances"], identifier, unit)
        bounds, _, _ = _bound_checks(activity, constraint["lower"], constraint["upper"], unit, tolerance, parameter_issue)
        lower, upper = constraint["lower"], constraint["upper"]
        if lower["kind"] == upper["kind"] == "finite" and lower["value"] == upper["value"]:
            residual = _difference(activity, _literal(lower["value"]), unit)
        elif lower["kind"] in {"missing", "invalid"} or upper["kind"] in {"missing", "invalid"}:
            residual = _cell(unit=unit, codes=["bound_invalid"])
        else:
            residual = _cell(state="not_applicable", unit=unit)
        native_activity = native_activities.get(position, _missing())
        activity_tolerance, activity_parameter_issue = _parameter(settings["constraint_activity_tolerances"], identifier, unit)
        difference, agreement = _native_difference(native_activity, activity, unit, activity_tolerance, activity_parameter_issue)
        constraint_checks.append({"constraint_id": identifier, "constraint_position": position,
            "metabolite_position": constraint["metabolite_position"], "activity": activity, "equality_residual": residual,
            **bounds, "expected_term_count": len(constraint["terms"]) if constraint["terms_complete"] else None,
            "available_term_count": available,
            "native_activity": deepcopy(native_activity), "native_minus_calculated_activity": difference,
            "native_activity_comparison": agreement})
    objective = _objective_check(problem, solution, native, parameters, primals)
    expected_reactions = model["population"]["reactions"] if model else None
    expected_variables = problem["variable_count"] if problem else None
    expected_constraints = problem["constraint_count"] if problem else None
    valid_flux_count = sum(_present(row["flux"]) for row in reaction_checks) if model else None
    valid_variable_count = sum(_present(row["primal"]) for row in variable_checks) if problem else None
    active_population = sum(row["active"] is not None for row in reaction_checks)
    active_count = sum(row["active"] is True for row in reaction_checks) if expected_reactions is not None and active_population == expected_reactions else None
    balance_rows = [row for row, source in zip(constraint_checks, constraints) if source["kind"] == "metabolite_balance"
        and row["equality_residual"]["state"] != "not_applicable"]
    residuals = [row["equality_residual"] for row in balance_rows if row["equality_residual"]["value"] is not None]
    if not residuals:
        maximum = _cell(codes=["constraint_unavailable"])
    elif any(row["unit"]["native_text"] is None or row["unit"]["basis"] == "unknown" for row in residuals):
        maximum = _cell(codes=["unknown_units"])
    elif any(not _compatible(residuals[0]["unit"], row["unit"]) for row in residuals[1:]):
        maximum = _cell(state="incompatible", codes=["unit_incompatible"])
    else:
        maximum = _cell(max(abs(row["value"]) for row in residuals), unit=residuals[0]["unit"],
            codes=["partial_population"] if len(residuals) != len(balance_rows) or len(constraints) != expected_constraints else ())
    violated_constraints = sum(row["comparison"] == "fails" for row in constraint_checks)
    evaluated_constraints = sum(row["comparison"] != "unknown" for row in constraint_checks)
    variable_unknown = sum(row["bound_comparison"] == "unknown" for row in variable_checks)
    complete = (model is not None and model["population"]["completeness"] == "complete"
        and problem is not None and problem["representation"] == "complete_continuous_linear"
        and solution is not None and solution["point_state"] == "basic_solution"
        and valid_flux_count == expected_reactions and valid_variable_count == expected_variables
        and len(constraints) == expected_constraints and evaluated_constraints == expected_constraints
        and variable_unknown == 0 and all(row["bound_comparison"] != "unknown" for row in reaction_checks)
        and reaction_consistency_complete and problem["objective"]["direction"] != "unknown"
        and objective["full_calculated"]["value"] is not None)
    has_relevant_check = bool(evaluated_reaction_sides or evaluated_variable_sides or evaluated_constraints)
    if violated_reaction_sides or violated_variable_sides or violated_constraints:
        candidate = "fails_recorded_checks"
    elif complete:
        candidate = "passes_recorded_checks"
    elif has_relevant_check or any(row["activity"]["value"] is not None for row in constraint_checks) or any(
            row["lower_slack"]["value"] is not None or row["upper_slack"]["value"] is not None for row in [*variable_checks, *reaction_checks]):
        candidate = "partial_checks"
    else:
        candidate = "unknown"
    if candidate in {"partial_checks", "unknown"}:
        issues.append(_issue("partial_population"))
    if problem and problem["representation"] != "complete_continuous_linear":
        issues.append(_issue("unsupported_problem_form" if problem["representation"] != "partial" else "partial_population"))
    # Retain explicit located calculations issues alongside individual cells.
    def cell_issues(item, location=None):
        if isinstance(item, dict):
            location = {key: item[key] for key in ("reaction_position", "variable_position", "constraint_position") if key in item} or location or {}
            if "issue_codes" in item:
                issues.extend(_issue(code, **location) for code in item["issue_codes"])
            else:
                for child in item.values():
                    cell_issues(child, location)
        elif isinstance(item, list):
            for child in item:
                cell_issues(child, location)
    cell_issues([variable_checks, reaction_checks, constraint_checks, objective, maximum])
    unique_issues = []
    seen_issues = set()
    for issue in issues:
        key = json.dumps(issue, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if key not in seen_issues:
            seen_issues.add(key); unique_issues.append(issue)
    result = {"version": "flux_balance_calculations_v1",
        "sheet_sha256": digest(sheet),
        "parameters": parameters, "reaction_checks": reaction_checks, "variable_checks": variable_checks,
        "constraint_checks": constraint_checks, "objective": objective,
        "expected_reaction_count": expected_reactions, "valid_flux_count": valid_flux_count,
        "flux_coverage_fraction": _coverage(valid_flux_count, expected_reactions),
        "expected_variable_count": expected_variables, "valid_variable_count": valid_variable_count,
        "variable_coverage_fraction": _coverage(valid_variable_count, expected_variables),
        "evaluated_variable_bound_count": evaluated_variable_sides, "violated_variable_bound_count": violated_variable_sides,
        "variable_bound_comparison_unknown_count": variable_unknown,
        "evaluated_constraint_count": evaluated_constraints, "expected_constraint_count": expected_constraints,
        "violated_constraint_count": violated_constraints,
        "constraint_comparison_unknown_count": sum(row["comparison"] == "unknown" for row in constraint_checks),
        "evaluated_reaction_bound_count": evaluated_reaction_sides, "violated_reaction_bound_count": violated_reaction_sides,
        "active_count": active_count, "active_population_count": active_population,
        "max_abs_balance_residual": maximum, "candidate_feasibility": candidate,
        "native_solver_status": native["solver"]["status"], "optimum_multiplicity": native["solver"]["alternate_optimum_claim"],
        "issues": unique_issues}
    return validate_flux_balance_record("FluxBalanceCalculations", result)
