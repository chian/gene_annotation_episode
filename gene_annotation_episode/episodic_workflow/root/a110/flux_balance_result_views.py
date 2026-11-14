"""Select FBA measurements from the sole retained sheet and calculations.

Scientific values are copied, never recomputed. Only structural association,
explicit filtering, pagination and source-free representation are performed.
"""
from copy import deepcopy

from .execution_contracts import digest
from .flux_balance_contracts import validate_flux_balance_record
from .flux_balance_sheet import validate_flux_balance_sheet
from .flux_balance_result_contracts import (RUN_FIELDS, POSITION_KEYS, FILTER_PATHS,
    validate_fba_projection_selector, validate_fba_projection)

__all__ = ["project_fba_result"]

_NUMBER = ("value", "state", "native_token", "float_hex", "precision", "missing_reason")
_BOUND = ("kind", "value", "native_token", "float_hex")
_SIDES = ("lower_slack", "upper_slack", "lower_violation", "upper_violation")
_ISSUE = ("code", "stage", "field", "source_row_index", "reaction_position", "metabolite_position", "variable_position", "constraint_position")
_LOCATORS = ("source_row_index", "reaction_position", "metabolite_position", "variable_position", "constraint_position")


def _copy(row, *keys):
    return {k: deepcopy(row[k]) for k in keys}


def _unit(row):
    return _copy(row, "native_text", "basis")


def _number(row):
    return _copy(row, *_NUMBER)


def _bound(row):
    return _copy(row, *_BOUND)


def _cell(row):
    return {**_copy(row, "value", "state", "issue_codes"), "unit": _unit(row["unit"])}


def _tolerance(rows, identifier):
    row = next((r for r in rows if r["subject_id"] == identifier), None)
    return None if row is None else {**_copy(row, "subject_id", "value"), "unit": _unit(row["unit"])}


def _associations(rows):
    return [_copy(r, "database", "accession") for r in rows]


def _definition(row):
    return None if row is None else {**_copy(row, "direction", "terms_complete", "expression_kind"),
        **{k: _number(row[k]) for k in ("native_constant", "interface_offset", "symbolic_constant")},
        "unit": _unit(row["unit"])}


def _position_map(rows, key, *, label):
    mapped = {}
    for row in rows:
        position = row[key]
        if position in mapped:
            raise ValueError("fba_calculation_row_association_mismatch:/" + label)
        mapped[position] = row
    return mapped


def _association(sheet, calculations):
    if calculations["sheet_sha256"] != digest(sheet):
        raise ValueError("fba_calculation_sheet_mismatch:/sheet_sha256")
    model, problem = sheet["models"]["effective"], sheet["problems"]["effective"]
    result = {}
    for axis, snapshot, key, id_key in (
        ("reaction", model, "reactions", None), ("variable", problem, "variables", "variable_id"),
        ("constraint", problem, "constraints", "constraint_id")):
        entities = [] if snapshot is None else snapshot[key]
        positions = _position_map(entities, "position", label=key)
        checks = _position_map(calculations[axis + "_checks"], axis + "_position", label=axis + "_checks")
        expected = None if snapshot is None else snapshot["population"]["reactions"] if axis == "reaction" else snapshot[axis + "_count"]
        if set(positions) != set(checks) or calculations["expected_" + axis + "_count"] != expected:
            raise ValueError("fba_calculation_row_association_mismatch:/" + axis + "_checks")
        for position, row in checks.items():
            if (id_key is not None and row[id_key] != positions[position]["id"]) or (
                    axis == "constraint" and row["metabolite_position"] != positions[position]["metabolite_position"]):
                raise ValueError("fba_calculation_row_association_mismatch:/" + axis + "_checks")
        result[axis] = checks
    if (calculations["native_solver_status"] != sheet["native"]["solver"]["status"]
            or calculations["optimum_multiplicity"] != sheet["native"]["solver"]["alternate_optimum_claim"]):
        raise ValueError("fba_calculation_row_association_mismatch:/native_solver_status")
    return result


def _run_values(sheet, calculations):
    native, solution = sheet["native"], sheet["native_solution"]["native"]
    problem, original = sheet["problems"]["effective"], sheet["problems"]["loaded_original"]
    model = sheet["models"]["effective"]
    result = {
        "native_run": {**_copy(native, "execution_outcome", "solve_call_count"),
            "solver_status": calculations["native_solver_status"], "raw_solver_status": native["solver"]["raw_status"],
            **{k: None if solution is None else solution[k] for k in ("point_state", "solution_object_state",
                "model_optimize_call_count", "optlang_status", "cobra_solution_status", "glpk_status_code",
                "glpk_primal_status_code", "glpk_dual_status_code")}},
        "request": {**_copy(native, "objective_request", "objective_application", "request_realization"),
            "constraint_changes": None if native["constraint_changes"] is None else [
                {**_copy(r, "reaction_id", "effective_reaction_position", "application", "issue_code"),
                 "requested_lower": _bound(r["requested_lower"]), "requested_upper": _bound(r["requested_upper"])}
                for r in native["constraint_changes"]]},
        "objective": {"check": {k: (_number(v) if "precision" in v else _cell(v)) if type(v) is dict else v
            for k, v in calculations["objective"].items()}, "definition": _definition(None if problem is None else problem["objective"]),
            "absolute_tolerance": calculations["parameters"]["objective_absolute_tolerance"]},
        "original_objective_definition": _definition(None if original is None else original["objective"]),
        "active_population": {**_copy(calculations, "active_count", "active_population_count", "expected_reaction_count"),
            "thresholds": [{**_copy(t, "subject_id", "value"), "unit": _unit(t["unit"])}
                for t in calculations["parameters"]["active_flux_thresholds"]]},
        "balance_residual": {"max_abs_balance_residual": _cell(calculations["max_abs_balance_residual"]),
            "expected_constraint_count": calculations["expected_constraint_count"], "representation": None if problem is None else problem["representation"]},
        "candidate_feasibility": {"candidate_feasibility": calculations["candidate_feasibility"],
            "model_completeness": None if model is None else model["population"]["completeness"],
            "problem_representation": None if problem is None else problem["representation"],
            "point_state": None if solution is None else solution["point_state"]},
        "optimum_multiplicity": _copy(calculations, "optimum_multiplicity"),
    }
    for field, keys in {
        "reaction_population": ("expected_reaction_count", "valid_flux_count", "flux_coverage_fraction"),
        "variable_population": ("expected_variable_count", "valid_variable_count", "variable_coverage_fraction"),
        "constraint_population": ("expected_constraint_count", "evaluated_constraint_count", "violated_constraint_count", "constraint_comparison_unknown_count"),
        "reaction_bound_counts": ("evaluated_reaction_bound_count", "violated_reaction_bound_count", "expected_reaction_count"),
        "variable_bound_counts": ("evaluated_variable_bound_count", "violated_variable_bound_count", "variable_bound_comparison_unknown_count", "expected_variable_count"),
    }.items():
        result[field] = {k: _cell(calculations[k]) if type(calculations[k]) is dict else calculations[k] for k in keys}
    return result


def _mapping(problem, reaction_position):
    if problem is None:
        return None
    row = next((r for r in problem["reaction_variables"] if r["reaction_position"] == reaction_position), None)
    return None if row is None else _copy(row, "reaction_position", "reaction_id", "forward_variable_position", "forward_variable_id", "reverse_variable_position", "reverse_variable_id")


def _reaction_values(row, *, model, problem, solution, check, parameters):
    mapping = _mapping(problem, row["position"])
    genes = {g["position"]: g for g in model["genes"]}
    values = {"name": row["name"], "bounds": {"lower": _bound(row["lower"]), "upper": _bound(row["upper"]), "unit": _unit(row["flux_unit"])},
        "boundary_kind": row["boundary_kind"], "associations": _associations(row["associations"]),
        "gpr": {**_copy(row, "gpr_native", "gpr_loaded", "gene_positions"), "source_gpr_retained": row["gpr_source_pointer"] is not None},
        "genes": [{"gene_position": p, "availability": "present" if p in genes else "unavailable",
            "id": genes[p]["id"] if p in genes else None, "name": genes[p]["name"] if p in genes else None,
            "associations": _associations(genes[p]["associations"]) if p in genes else None} for p in row["gene_positions"]],
        "solver_variables": mapping}
    if check is None:
        return values
    flux = {"flux": _number(check["flux"]), "flux_basis": check["flux_basis"]}
    bounds = {"lower": _bound(row["lower"]), "upper": _bound(row["upper"])}
    unit = _unit(row["flux_unit"])
    values.update({
        "flux": {**flux, "unit": unit},
        "bound_check": {**flux, **bounds, "unit": unit, **{k: _cell(check[k]) for k in _SIDES},
            "bound_comparison": check["bound_comparison"], "tolerance": _tolerance(parameters["reaction_bound_tolerances"], row["id"])},
        "active": {**flux, "unit": unit, "active": check["active"], "threshold": _tolerance(parameters["active_flux_thresholds"], row["id"])},
        "csv_comparison": {**flux, "csv_flux": _number(check["csv_flux"]), "csv_minus_flux": _cell(check["csv_minus_flux"]),
            "csv_flux_comparison": check["csv_flux_comparison"], "unit": unit, "tolerance": _tolerance(parameters["reaction_flux_tolerances"], row["id"])},
        "variable_net_comparison": {**flux, "variable_net_flux": _cell(check["variable_net_flux"]),
            "native_minus_variable_net_flux": _cell(check["native_minus_variable_net_flux"]), "variable_net_comparison": check["variable_net_comparison"],
            "unit": unit, "tolerance": _tolerance(parameters["reaction_flux_tolerances"], row["id"]), "solver_variables": mapping},
        "native_values": None if solution is None else {"point_state": solution["point_state"], "selected_flux": _number(check["flux"]),
            "flux_basis": check["flux_basis"], "flux_unit": unit, "reduced_cost_unit": None,
            "rows": [{**_copy(r, "reaction_position", "reaction_id"), "flux": _number(r["flux"]), "reduced_cost": _number(r["reduced_cost"])}
                for r in solution["reaction_values"] if r["reaction_position"] == row["position"]]},
    })
    return values


def _constraint_values(row, *, model, problem, solution, check, parameters):
    variables = {r["position"]: r for r in problem["variables"]}
    metabolites = {} if model is None else {r["position"]: r for r in model["metabolites"]}
    metabolite = metabolites.get(row["metabolite_position"])
    values = {
        "definition": {**_copy(row, "kind", "metabolite_position", "terms_complete", "expression_kind", "indicator_variable_position", "active_when"),
            "constant": _number(row["constant"]), "lower": _bound(row["lower"]), "upper": _bound(row["upper"]), "unit": _unit(row["unit"])},
        "terms": [{"variable_position": t["variable_position"], "coefficient": _number(t["coefficient"]),
            "variable_id": variables[t["variable_position"]]["id"] if t["variable_position"] in variables else None} for t in row["terms"]],
        "metabolite": None if row["metabolite_position"] is None else {"metabolite_position": row["metabolite_position"],
            "availability": "present" if metabolite is not None else "unavailable", "id": None if metabolite is None else metabolite["id"],
            "name": None if metabolite is None else metabolite["name"], "compartment_position": None if metabolite is None else metabolite["compartment_position"]},
    }
    if check is None:
        return values
    counts = _copy(check, "expected_term_count", "available_term_count")
    bounds = {"lower": _bound(row["lower"]), "upper": _bound(row["upper"])}
    values.update({
        "activity": {"activity": _cell(check["activity"]), "constant": _number(row["constant"]),
            **_copy(row, "expression_kind", "terms_complete"), **counts},
        "equality_residual": {"activity": _cell(check["activity"]), "equality_residual": _cell(check["equality_residual"]), **bounds, **counts},
        "bound_check": {"activity": _cell(check["activity"]), **bounds, **{k: _cell(check[k]) for k in _SIDES},
            "comparison": check["comparison"], **counts, "tolerance": _tolerance(parameters["constraint_tolerances"], row["id"])},
        "native_activity_comparison": {"native_activity": _number(check["native_activity"]), "activity": _cell(check["activity"]),
            "native_minus_calculated_activity": _cell(check["native_minus_calculated_activity"]), "native_activity_comparison": check["native_activity_comparison"],
            "unit": _unit(row["unit"]), **counts, "tolerance": _tolerance(parameters["constraint_activity_tolerances"], row["id"])},
        "native_values": None if solution is None else {"point_state": solution["point_state"], "selected_native_activity": _number(check["native_activity"]),
            "activity_unit": _unit(row["unit"]), "shadow_price_unit": None,
            "rows": [{**_copy(r, "constraint_position", "constraint_id"), "activity": _number(r["activity"]), "shadow_price": _number(r["shadow_price"])}
                for r in solution["constraint_values"] if r["constraint_position"] == row["position"]]},
    })
    return values


def _variable_values(row, *, solution, check, parameters):
    values = {"definition": {**_copy(row, "kind", "native_index", "optlang_position", "native_kind_code", "native_bound_type_code"),
        "lower": _bound(row["lower"]), "upper": _bound(row["upper"]), "unit": _unit(row["unit"])}}
    if check is None:
        return values
    values.update({
        "primal": {"primal": _number(check["primal"]), "unit": _unit(row["unit"]), "point_state": None if solution is None else solution["point_state"]},
        "bound_check": {"primal": _number(check["primal"]), "lower": _bound(row["lower"]), "upper": _bound(row["upper"]),
            "unit": _unit(row["unit"]), **{k: _cell(check[k]) for k in _SIDES}, "bound_comparison": check["bound_comparison"],
            "tolerance": _tolerance(parameters["variable_bound_tolerances"], row["id"])},
        "native_values": None if solution is None else {"point_state": solution["point_state"], "selected_primal": _number(check["primal"]),
            "primal_unit": _unit(row["unit"]), "reduced_cost_unit": None,
            "rows": [{**_copy(r, "variable_position", "variable_id"), "primal": _number(r["primal"]), "reduced_cost": _number(r["reduced_cost"])}
                for r in solution["variable_values"] if r["variable_position"] == row["position"]]},
    })
    return values


def _qualifications(sheet, calculations, *, selector, rows):
    view, phase = selector["view"], selector.get("snapshot_phase")
    selected = set() if view == "run_diagnostics" else {r[POSITION_KEYS[view][1]] for r in rows}
    metabolites = set()
    if view == "constraint_residuals":
        problem = sheet["problems"][phase]
        metabolites = set() if problem is None else {r["metabolite_position"] for r in problem["constraints"]
            if r["position"] in selected and r["metabolite_position"] is not None}
    csv_files = [number["source"]["file"] for r in sheet["native"]["flux_rows"]
        for number in (r["flux"], r["csv_lower"], r["csv_upper"]) if number["source"] is not None]
    result = []
    for issue in calculations["issues"]:
        scope = None
        if all(issue[k] is None for k in _LOCATORS):
            scope = "bundle"
        elif view == "csv_flux_rows":
            if issue["source_row_index"] in selected and issue["detail_file"] is not None and issue["detail_file"] in csv_files:
                scope = "selected_csv_row"
        elif view != "run_diagnostics":
            position_key = POSITION_KEYS[view][1]
            matching = issue[position_key] in selected or (view == "constraint_residuals" and issue["metabolite_position"] in metabolites)
            if matching:
                if issue["stage"] == "calculate" and phase == "effective":
                    scope = "selected_entity"
                elif issue["stage"] != "calculate" and issue["detail_file"] is not None:
                    source_match = any(source is not None and issue["detail_file"] == source for source in (sheet["models"]["source"], sheet["problems"]["source"]))
                    phase_match = type(issue["field"]) is str and issue["field"].startswith("/" + phase + "/")
                    solution_match = phase == "effective" and sheet["native_solution"]["source"] is not None and issue["detail_file"] == sheet["native_solution"]["source"]
                    if (source_match and phase_match) or solution_match:
                        scope = "selected_entity"
        if scope is not None:
            result.append({"scope": scope, "issue": _copy(issue, *_ISSUE)})
    for row in rows:
        if view == "csv_flux_rows" and row["availability"] == "ambiguous":
            result.append({"scope": "selected_csv_row", "issue": {"code": "flux_identity_conflict", "stage": "project", "field": None,
                **{k: row["source_row_index"] if k == "source_row_index" else None for k in _LOCATORS}}})
    return result


def project_fba_result(sheet: dict, calculations: dict, *, selector: dict) -> dict:
    """Copy exactly selected measurements with original identities and qualifiers."""
    selected = validate_fba_projection_selector(selector)
    sheet = validate_flux_balance_sheet(sheet)
    calculations = validate_flux_balance_record("FluxBalanceCalculations", calculations)
    checks = _association(sheet, calculations)
    view, phase = selected["view"], selected.get("snapshot_phase")
    model = sheet["models"][phase] if phase is not None else None
    problem = sheet["problems"][phase] if phase is not None else None
    native = sheet["native_solution"]["native"]
    population = {"axis": "run_fields" if view == "run_diagnostics" else POSITION_KEYS[view][3], "snapshot_phase": phase,
        "expected_count": None, "expected_count_basis": "snapshot_unavailable", "retained_count": 0,
        "model_completeness": None, "problem_representation": None}
    if view == "run_diagnostics":
        population.update(expected_count=len(RUN_FIELDS), expected_count_basis="field_catalog", retained_count=len(RUN_FIELDS))
        values = _run_values(sheet, calculations)
        rows = [{"field": field, "value": values[field]} for field in selected["fields"]]
    else:
        selected_key, position_key, identifier_key, _ = POSITION_KEYS[view]
        if view == "csv_flux_rows":
            entities = sheet["native"]["flux_rows"]
            population.update(expected_count_basis="unknown_csv_population", retained_count=len(entities))
        else:
            snapshot, collection = (model, "reactions") if view == "reaction_fluxes" else (problem, "constraints" if view == "constraint_residuals" else "variables")
            entities = [] if snapshot is None else snapshot[collection]
            if snapshot is not None:
                population.update(expected_count=snapshot["population"]["reactions"] if view == "reaction_fluxes" else snapshot["constraint_count" if view == "constraint_residuals" else "variable_count"],
                    expected_count_basis="model_population" if view == "reaction_fluxes" else "native_problem_count", retained_count=len(entities))
                population["model_completeness" if view == "reaction_fluxes" else "problem_representation"] = snapshot["population"]["completeness"] if view == "reaction_fluxes" else snapshot["representation"]
        by_position = {}
        for entity in entities:
            by_position.setdefault(entity["source_row_index" if view == "csv_flux_rows" else "position"], []).append(entity)
        rows = []
        for position in selected[selected_key]:
            if population["expected_count"] is not None and position >= population["expected_count"]:
                raise ValueError("fba_projection_position_out_of_range:/selector/" + selected_key)
            found = by_position.get(position, [])
            available = len(found) == 1
            ambiguous = len(found) > 1
            row = {position_key: position, identifier_key: None, "availability": "present" if available else "ambiguous" if ambiguous else "unavailable",
                "existence": "present" if found else "within_known_population" if population["expected_count"] is not None else "unknown",
                "unavailable_reason": None if available else "source_row_identity_conflict" if ambiguous else "source_row_not_retained" if view == "csv_flux_rows" else
                    "snapshot_unavailable" if population["expected_count_basis"] == "snapshot_unavailable" else "position_not_retained",
                "filter_match": None, "values": {f: None for f in selected["fields"]}}
            if available:
                entity = found[0]
                row[identifier_key] = entity["reaction_id" if view == "csv_flux_rows" else "id"]
                params = calculations["parameters"]
                if view == "reaction_fluxes":
                    values = _reaction_values(entity, model=model, problem=problem, solution=native, check=checks["reaction"][position] if phase == "effective" else None, parameters=params)
                elif view == "constraint_residuals":
                    values = _constraint_values(entity, model=model, problem=problem, solution=native, check=checks["constraint"][position] if phase == "effective" else None, parameters=params)
                elif view == "variable_bounds":
                    values = _variable_values(entity, solution=native, check=checks["variable"][position] if phase == "effective" else None, parameters=params)
                else:
                    values = {"name": entity["reaction_name"], "flux": {"flux": _number(entity["flux"]), "unit": None},
                        "bounds": {"lower": _bound(entity["csv_lower"]), "upper": _bound(entity["csv_upper"]), "unit": None},
                        "model_association": _copy(entity, "reaction_position", "association")}
                row["values"] = {f: values[f] for f in selected["fields"]}
            rows.append(row)
    selected_count = len(rows)
    filtering = selected.get("filter")
    matches, unknown = selected_count, 0
    if filtering is not None:
        matches = unknown = 0
        filtered = []
        for row in rows:
            group = row["values"][filtering["field"]]
            number = None if group is None else group[FILTER_PATHS[view][filtering["field"]]]
            known = number is not None and number["value"] is not None and number["state"] in {"present", "native", "calculated"}
            if known and number["value"] < filtering["minimum"]:
                continue
            row["filter_match"] = "matches" if known else "unknown"
            matches += int(known)
            unknown += int(not known)
            filtered.append(row)
        rows = filtered
    filtered_count = len(rows)
    offset, limit = selected["row_window"]["offset"], selected["row_window"]["limit"]
    rows = rows[offset:offset + limit]
    result = {"version": "flux_balance_result_view_v1", "selector": selected, "population": population,
        "page": {"selected_row_count": selected_count, "matched_row_count": matches, "filter_unknown_row_count": unknown,
            "filtered_row_count": filtered_count, "row_offset": offset, "returned_row_count": len(rows), "has_more": offset + len(rows) < filtered_count},
        "rows": rows, "qualification_issues": _qualifications(sheet, calculations, selector=selected, rows=rows)}
    return validate_fba_projection(result)
