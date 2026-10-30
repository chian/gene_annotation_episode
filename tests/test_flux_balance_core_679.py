"""Shared FBA numerical tests; no optimization or production capture is run.

The hand examples are deliberate synthetic fixtures. The 677 case explicitly
transforms already retained API-probe operands into this new contract. That
transformation is test code, not evidence of a native producer implementation.
"""
from copy import deepcopy
import builtins
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.flux_balance_contracts import (
    ISSUE_CODES, flux_balance_schema, validate_flux_balance_record, validate_fba_artifact_payloads,
)
from gene_annotation_episode.flux_balance_sheet import populate_flux_balance_sheet, validate_flux_balance_sheet
from gene_annotation_episode.flux_balance_calculations import calculate_flux_balance_sheet


FILE = {"artifact_ref": "artifact:deliberate-synthetic-fba-fixture679", "sha256": "a" * 64,
        "size_bytes": 0, "format": "synthetic_fba_fixture_v1"}


def source(pointer=""):
    return {"file": deepcopy(FILE), "pointer": pointer}


def unit(text="fixture_flux_unit"):
    return {"native_text": text, "basis": "supplied" if text is not None else "unknown",
            "source": source() if text is not None else None}


def number(value=None, *, state=None, precision="full_native", pointer="/test/number"):
    if value is None:
        return {"value": None, "state": state or "missing", "native_token": None, "float_hex": None,
                "precision": "unknown", "source": None, "missing_reason": "not_returned"}
    return {"value": value, "state": state or "present", "native_token": repr(value),
            "float_hex": value.hex() if type(value) is float else None,
            "precision": precision, "source": source(pointer), "missing_reason": None}


def unavailable(state, token):
    return {"value": None, "state": state, "native_token": token, "float_hex": None,
            "precision": "unknown", "source": source(), "missing_reason": None}


def bound(value=None, *, kind=None):
    return {"value": value, "kind": kind or ("finite" if value is not None else "missing"),
            "native_token": repr(value) if value is not None else None,
            "float_hex": value.hex() if type(value) is float else None, "source": source()}


def term(position, coefficient):
    return {"variable_position": position, "coefficient": number(coefficient)}


def make_sheet(fluxes=(10.0, 10.0, 10.0)):
    reactions = []
    variables = []
    joins = []
    for position, identifier in enumerate(("IN", "AB", "OUT")):
        upper = 10.0 if position == 0 else 1000.0
        reactions.append({"position": position, "id": identifier, "name": identifier,
            "lower": bound(0.0), "upper": bound(upper), "flux_unit": unit(), "boundary_kind": "unknown",
            "boundary_source": None, "gpr_native": None, "gene_positions": [], "associations": [],
            "annotation_pointer": None, "notes_pointer": None, "gpr_source_pointer": None, "gpr_loaded": None})
        for index, name, high in ((2 * position, identifier, upper), (2 * position + 1, identifier + "_reverse", 0.0)):
            variables.append({"position": index, "native_index": index + 1, "optlang_position": index,
                "id": name, "kind": "continuous", "native_kind_code": 1, "native_bound_type_code": 4,
                "lower": bound(0.0), "upper": bound(high), "unit": unit(), "source": source()})
        joins.append({"reaction_position": position, "reaction_id": identifier,
            "forward_variable_position": 2 * position, "forward_variable_id": identifier,
            "reverse_variable_position": 2 * position + 1, "reverse_variable_id": identifier + "_reverse",
            "flux_expression_pointer": "/fixture/flux_expression"})
    model = {"model_id": "synthetic_two_metabolite_679", "model_name": "Deliberate numerical fixture",
        "compartments": [{"position": 0, "id": "c", "name": None}], "genes": [],
        "metabolites": [{"position": i, "id": name, "name": name, "compartment_position": 0,
            "formula": None, "charge": number(), "associations": [], "annotation_pointer": None, "notes_pointer": None}
            for i, name in enumerate(("A", "B"))], "reactions": reactions,
        "stoichiometry": [{"metabolite_position": i, "reaction_position": j,
            "coefficient": number(v), "coefficient_unit": unit("1")}
            for i, j, v in ((0, 0, 1), (0, 1, -1), (1, 1, 1), (1, 2, -1))],
        "groups": [], "annotations": {"fixture": "synthetic"}, "notes": {}, "sbml_metadata": None,
        "native_cobra_json": None, "native_sbml_export": None, "medium": [], "medium_state": "not_retained",
        "medium_basis": "unknown", "population": {"compartments": 1, "genes": 0, "metabolites": 2,
            "reactions": 3, "groups": 0, "completeness": "complete"}}
    constraints = []
    for i, name, terms in ((0, "A", [(0, 1), (1, -1), (2, -1), (3, 1)]),
                           (1, "B", [(2, 1), (3, -1), (4, -1), (5, 1)])):
        constraints.append({"position": i, "native_index": i + 1, "optlang_position": i, "id": name,
            "kind": "metabolite_balance", "metabolite_position": i, "constant": number(0),
            "terms": [term(*pair) for pair in terms], "terms_complete": True,
            "lower": bound(0), "upper": bound(0), "native_bound_type_code": 5,
            "indicator_variable_position": None, "active_when": 1, "expression_kind": "linear",
            "native_expression_pointer": "/fixture/expression", "unit": unit(), "source": source()})
    objective = {"direction": "max", "native_direction_code": 2, "native_constant": number(0),
        "interface_offset": number(0), "symbolic_constant": number(0), "terms": [term(4, 1), term(5, -1)],
        "terms_complete": True, "expression_kind": "linear", "native_expression_pointer": "/fixture/objective",
        "unit": unit(), "source": source()}
    problem = {"version": "cobra_glpk_problem_snapshot_v1", "phase": "effective", "variable_count": 6,
        "constraint_count": 2, "variables": variables, "constraints": constraints, "objective": objective,
        "reaction_variables": joins, "representation": "complete_continuous_linear", "native_optlang_json": None,
        "native_glpk_text": None, "native_lp_text": None, "issues": []}
    native_solution = {"version": "cobra_glpk_solution_capture_v1", "model_optimize_call_count": 1,
        "native_passes": [], "solution_object_state": "returned", "optlang_status": "optimal",
        "cobra_solution_status": "optimal", "glpk_status_code": 5, "glpk_primal_status_code": 2,
        "glpk_dual_status_code": 2, "point_state": "basic_solution", "native_glpk_objective": number(10),
        "native_optlang_objective": number(10), "native_cobra_objective": number(10),
        "variable_values": [{"variable_position": row["position"], "variable_id": row["id"],
            "primal": number(fluxes[row["position"] // 2] if row["position"] % 2 == 0 else 0),
            "reduced_cost": number()} for row in variables],
        "constraint_values": [], "reaction_values": [{"reaction_position": i, "reaction_id": row["id"],
            "flux": number(fluxes[i]), "reduced_cost": number()} for i, row in enumerate(reactions)],
        "configuration_after_solve": None, "diagnostics_pointer": "", "issues": []}
    solver = {"interface": None, "name": None, "version": None, "cobra_version": None, "optlang_version": None,
        "raw_status": "optimal", "status": "optimal", "feasibility_tolerance": number(),
        "optimality_tolerance": number(), "integrality_tolerance": number(), "raw_parameters_file": None,
        "diagnostic_file": None, "alternate_optimum_claim": "not_assessed", "alternate_claim_source": None}
    native = {"version": "native_fba_result_v1", "solver": solver, "objective": number(10),
        "flux_rows": [{"source_row_index": i, "reaction_id": row["id"], "reaction_position": i,
            "reaction_name": row["name"], "flux": number(fluxes[i]), "csv_lower": deepcopy(row["lower"]),
            "csv_upper": deepcopy(row["upper"]), "association": "matched"} for i, row in enumerate(reactions)],
        "solve_call_count": 1, "constraint_changes": [], "objective_request": {"kind": "model_default", "reaction_id": None},
        "objective_application": "model_default", "request_realization": "exact", "execution_outcome": "completed",
        "source_active_count": None, "source_active_threshold": number(), "source_log_file": None, "issues": []}
    original_problem = deepcopy(problem); original_problem["phase"] = "loaded_original"
    bundle = {"models": {"loaded_original": deepcopy(model), "effective": model, "source": deepcopy(FILE),
            "input_profile": "unknown", "loader": None, "source_to_loaded_ids": [], "source_feature_audit": [], "issues": []},
        "problems": {"loaded_original": original_problem, "effective": problem, "source": deepcopy(FILE),
            "configuration_before_solve": None, "issues": []},
        "native_solution": {"native": native_solution, "source": deepcopy(FILE), "issues": []},
        "native": native, "original_request_file": deepcopy(FILE), "native_manifest_file": None,
        "retained_files": [deepcopy(FILE)], "issues": []}
    return populate_flux_balance_sheet(bundle=bundle)


def parameters(sheet, *, tolerance=0.0, active=1e-6):
    model, problem = sheet["models"]["effective"], sheet["problems"]["effective"]
    reactions = model["reactions"] if model else []
    variables = problem["variables"] if problem else []
    constraints = problem["constraints"] if problem else []
    def entries(rows, unit_key, value):
        return [{"subject_id": row["id"], "value": value, "unit": deepcopy(row[unit_key])} for row in rows]
    return {"version": "fba_calculation_parameters_v1", "reaction_bound_tolerances": entries(reactions, "flux_unit", tolerance),
        "constraint_tolerances": entries(constraints, "unit", tolerance), "active_flux_thresholds": entries(reactions, "flux_unit", active),
        "objective_absolute_tolerance": tolerance, "variable_bound_tolerances": entries(variables, "unit", tolerance),
        "reaction_flux_tolerances": entries(reactions, "flux_unit", tolerance), "constraint_activity_tolerances": entries(constraints, "unit", tolerance)}


def calc(sheet, **kwargs):
    return calculate_flux_balance_sheet(sheet, parameters=parameters(sheet, **kwargs))


def test_two_metabolite_hand_example_and_detached_native_numbers():
    sheet = make_sheet()
    before = deepcopy(sheet)
    result = calc(sheet)
    assert [row["equality_residual"]["value"] for row in result["constraint_checks"]] == [0, 0]
    assert result["objective"]["full_calculated"]["value"] == 10
    assert result["flux_coverage_fraction"]["value"] == 1
    assert result["variable_coverage_fraction"]["value"] == 1
    assert result["active_count"] == 3
    assert result["evaluated_reaction_bound_count"] == 6
    assert result["evaluated_variable_bound_count"] == 12
    assert result["candidate_feasibility"] == "passes_recorded_checks"
    assert sheet == before
    result["reaction_checks"][0]["flux"]["value"] = 999
    assert sheet == before


def test_violating_candidate_does_not_erase_native_optimal_claim():
    result = calc(make_sheet((10.0, 12.0, 12.0)))
    assert [row["equality_residual"]["value"] for row in result["constraint_checks"]] == [-2, 0]
    assert result["objective"]["full_calculated"]["value"] == 12
    assert result["objective"]["legacy_minus_calculated"]["value"] == -2
    assert result["candidate_feasibility"] == "fails_recorded_checks"
    assert result["native_solver_status"] == "optimal"
    assert result["violated_constraint_count"] == 1


def test_missing_ab_preserves_other_fluxes_and_sparse_objective():
    sheet = make_sheet()
    sheet["native_solution"]["native"]["reaction_values"][1]["flux"] = number()
    sheet["native_solution"]["native"]["variable_values"][2]["primal"] = number()
    sheet["native"]["flux_rows"].pop(1)
    result = calc(sheet)
    assert result["valid_flux_count"] == 2
    assert result["flux_coverage_fraction"]["value"] == pytest.approx(2 / 3)
    assert all(row["activity"]["value"] is None for row in result["constraint_checks"])
    assert result["objective"]["full_calculated"]["value"] == 10
    assert result["active_count"] is None
    assert result["candidate_feasibility"] == "partial_checks"


def test_csv_only_never_invents_split_or_auxiliary_primals():
    sheet = make_sheet()
    sheet["native_solution"]["native"] = None
    result = calc(sheet)
    assert all(row["flux_basis"] == "flux_csv" for row in result["reaction_checks"])
    assert result["valid_variable_count"] == 0
    assert all(row["activity"]["value"] is None for row in result["constraint_checks"])
    assert result["candidate_feasibility"] == "partial_checks"
    assert result["objective"]["full_calculated"]["value"] is None


@pytest.mark.parametrize("kind", ["reaction", "variable", "constraint"])
def test_duplicate_native_values_are_ambiguous_not_absent(kind):
    sheet = make_sheet()
    solution = sheet["native_solution"]["native"]
    if kind == "constraint":
        solution["constraint_values"] = [{"constraint_position": 0, "constraint_id": "A", "activity": number(0), "shadow_price": number()}]
    key = kind + "_values"
    solution[key].append(deepcopy(solution[key][0]))
    result = calc(sheet)
    if kind == "reaction":
        assert result["reaction_checks"][0]["flux_basis"] == "unavailable"
        assert result["reaction_checks"][0]["flux"]["value"] is None
        assert result["reaction_checks"][0]["csv_flux"]["value"] == 10
    elif kind == "variable":
        assert result["variable_checks"][0]["primal"]["value"] is None
        assert result["constraint_checks"][0]["activity"]["value"] is None
    else:
        assert result["constraint_checks"][0]["native_activity"]["value"] is None
    assert any(row["code"] == "duplicate_" + kind + "_id" for row in result["issues"])


def test_native_invalid_flux_cannot_fallback_to_good_csv():
    sheet = make_sheet()
    sheet["native_solution"]["native"]["reaction_values"][0]["flux"] = unavailable("nonfinite", "nan")
    result = calc(sheet)
    assert result["reaction_checks"][0]["flux"]["state"] == "nonfinite"
    assert result["reaction_checks"][0]["flux_basis"] == "unavailable"
    assert result["valid_flux_count"] == 2


def test_all_three_flux_observations_remain_separate():
    sheet = make_sheet()
    sheet["native"]["flux_rows"][0]["flux"] = number(9)
    sheet["native_solution"]["native"]["variable_values"][0]["primal"] = number(8)
    result = calc(sheet)
    row = result["reaction_checks"][0]
    assert row["flux"]["value"] == 10
    assert row["csv_minus_flux"]["value"] == -1
    assert row["csv_flux_comparison"] == "conflicts"
    assert row["variable_net_flux"]["value"] == 8
    assert row["native_minus_variable_net_flux"]["value"] == 2
    assert row["variable_net_comparison"] == "conflicts"


def test_negative_flux_and_infinite_sides_are_not_zero_violations():
    sheet = make_sheet((-2.0, -2.0, -2.0))
    for row in sheet["models"]["effective"]["reactions"]:
        row["lower"], row["upper"] = bound(kind="negative_infinity"), bound(kind="positive_infinity")
    for row in sheet["problems"]["effective"]["variables"]:
        row["lower"], row["upper"] = bound(kind="negative_infinity"), bound(kind="positive_infinity")
    result = calc(sheet)
    assert result["evaluated_reaction_bound_count"] == result["evaluated_variable_bound_count"] == 0
    assert all(row["bound_comparison"] == "passes" for row in result["reaction_checks"])
    assert result["reaction_checks"][0]["lower_violation"]["state"] == "not_applicable"
    assert result["objective"]["full_calculated"]["value"] == -2
    assert result["active_count"] == 3
    assert result["candidate_feasibility"] == "passes_recorded_checks"


def test_missing_tolerances_preserve_numbers_without_finite_side_counts():
    sheet = make_sheet((10.0, 12.0, 12.0))
    settings = parameters(sheet)
    for key in settings:
        if isinstance(settings[key], list):
            settings[key] = []
    settings["objective_absolute_tolerance"] = None
    result = calculate_flux_balance_sheet(sheet, parameters=settings)
    assert result["constraint_checks"][0]["equality_residual"]["value"] == -2
    assert result["constraint_checks"][0]["comparison"] == "unknown"
    assert result["evaluated_reaction_bound_count"] == result["evaluated_variable_bound_count"] == 0
    assert result["candidate_feasibility"] == "partial_checks"
    assert result["objective"]["legacy_minus_calculated"]["value"] == -2
    assert result["objective"]["legacy_comparison"] == "unknown"


def test_missing_bound_prevents_vacuous_pass():
    sheet = make_sheet()
    sheet["models"]["effective"]["reactions"][0]["lower"] = bound()
    result = calc(sheet)
    assert result["reaction_checks"][0]["bound_comparison"] == "unknown"
    assert result["evaluated_reaction_bound_count"] == 5
    assert result["candidate_feasibility"] == "partial_checks"


def test_unknown_units_keep_row_arithmetic_but_no_cross_row_maximum():
    sheet = make_sheet()
    for row in sheet["problems"]["effective"]["constraints"]:
        row["unit"] = unit(None)
    result = calc(sheet)
    assert result["constraint_checks"][0]["equality_residual"]["value"] == 0
    assert result["max_abs_balance_residual"]["value"] is None
    assert "unknown_units" in result["max_abs_balance_residual"]["issue_codes"]


def test_different_declared_units_keep_rows_and_qualify_aggregate():
    sheet = make_sheet()
    sheet["problems"]["effective"]["constraints"][1]["unit"] = unit("different_scale")
    result = calc(sheet)
    assert result["constraint_checks"][1]["activity"]["value"] == 0
    assert result["max_abs_balance_residual"]["state"] == "incompatible"
    settings = parameters(sheet)
    settings["reaction_bound_tolerances"][0]["unit"] = unit("different_scale")
    result = calculate_flux_balance_sheet(sheet, parameters=settings)
    assert result["reaction_checks"][0]["bound_comparison"] == "unknown"
    assert "unit_incompatible" in result["reaction_checks"][0]["lower_violation"]["issue_codes"]


def test_partial_populations_preserve_original_positions_and_expected_counts():
    sheet = make_sheet()
    model = sheet["models"]["effective"]
    model["reactions"].pop(1); model["population"]["completeness"] = "partial"
    problem = sheet["problems"]["effective"]
    problem["variables"].pop(2); problem["representation"] = "partial"
    result = calc(sheet)
    assert [row["reaction_position"] for row in result["reaction_checks"]] == [0, 2]
    assert result["expected_reaction_count"] == 3
    assert result["valid_flux_count"] == 2
    assert [row["variable_position"] for row in result["variable_checks"]] == [0, 1, 3, 4, 5]
    assert result["expected_variable_count"] == 6
    assert result["candidate_feasibility"] == "partial_checks"


def test_sparse_incomplete_and_zero_coefficient_operands_are_distinct():
    sheet = make_sheet()
    problem = sheet["problems"]["effective"]
    solution = sheet["native_solution"]["native"]
    solution["variable_values"][0]["primal"] = number()
    problem["objective"]["terms"].append(term(0, 0))
    result = calc(sheet)
    assert result["objective"]["full_calculated"]["value"] == 10
    problem["objective"]["terms_complete"] = False; problem["representation"] = "partial"
    result = calc(sheet)
    assert result["objective"]["full_calculated"]["value"] is None
    assert "term_population_incomplete" in result["objective"]["native_basis_calculated"]["issue_codes"]


@pytest.mark.parametrize("form", ["integer", "binary", "nonlinear", "indicator", "unknown_direction"])
def test_unsupported_or_unknown_form_cannot_get_full_continuous_verdict(form):
    sheet = make_sheet()
    problem = sheet["problems"]["effective"]
    if form in {"integer", "binary"}:
        problem["representation"] = "complete_mixed_integer_linear"
        problem["variables"][0]["kind"] = form
    elif form == "unknown_direction":
        problem["objective"]["direction"] = "unknown"
    else:
        problem["representation"] = "unsupported"
        if form == "nonlinear":
            problem["constraints"][0]["expression_kind"] = "nonlinear"
        else:
            problem["constraints"][0]["indicator_variable_position"] = 0
    result = calc(sheet)
    assert result["candidate_feasibility"] == "partial_checks"


def test_unestablished_point_is_missing_not_getter_default_zero():
    sheet = make_sheet()
    solution = sheet["native_solution"]["native"]
    solution["point_state"] = "not_established"
    with pytest.raises(ValueError, match="schema_invalid|primal_not_established"):
        validate_flux_balance_sheet(sheet)
    for row in solution["variable_values"]:
        row["primal"] = number()
    for row in solution["reaction_values"]:
        row["flux"] = number()
    sheet["native"]["flux_rows"] = []
    result = calc(sheet)
    assert result["candidate_feasibility"] == "unknown"
    assert result["valid_variable_count"] == result["valid_flux_count"] == 0


@pytest.mark.parametrize("status", ["infeasible", "unbounded", "time_limit", "iteration_limit", "numerical_failure"])
def test_native_status_never_erases_established_candidate_residuals(status):
    sheet = make_sheet()
    sheet["native"]["solver"]["status"] = status
    sheet["native"]["solver"]["raw_status"] = status
    result = calc(sheet)
    assert result["native_solver_status"] == status
    assert result["constraint_checks"][0]["equality_residual"]["value"] == 0
    assert result["candidate_feasibility"] == "passes_recorded_checks"
    assert result["optimum_multiplicity"] == "not_assessed"


def test_objective_disagreement_alone_is_not_constraint_infeasibility():
    sheet = make_sheet()
    sheet["native_solution"]["native"]["native_glpk_objective"] = number(99)
    result = calc(sheet)
    assert result["objective"]["glpk_comparison"] == "conflicts"
    assert result["candidate_feasibility"] == "passes_recorded_checks"


def test_formatted_objective_rounding_and_unknown_precision_remain_explicit():
    sheet = make_sheet()
    sheet["native"]["objective"] = number(10.0, precision="formatted_6dp")
    sheet["problems"]["effective"]["objective"]["interface_offset"] = number(4e-7)
    result = calc(sheet)
    assert result["objective"]["legacy_minus_calculated"]["value"] != 0
    assert result["objective"]["legacy_comparison"] == "agrees"
    sheet["native"]["objective"]["precision"] = "unknown"
    result = calc(sheet)
    assert result["objective"]["legacy_comparison"] == "unknown"


@pytest.mark.parametrize("case", ["unknown_precision", "different_flux", "conflicting_bounds"])
def test_optional_csv_diagnostics_cannot_change_established_point_feasibility(case):
    sheet = make_sheet()
    csv = sheet["native"]["flux_rows"][0]
    if case == "unknown_precision":
        csv["flux"]["precision"] = "unknown"
    elif case == "different_flux":
        csv["flux"] = number(9)
    else:
        csv["association"] = "conflicting"
        csv["csv_upper"] = bound(11)
    result = calc(sheet)
    assert result["candidate_feasibility"] == "passes_recorded_checks"
    assert result["reaction_checks"][0]["csv_flux"]["value"] == (9 if case == "different_flux" else 10)
    if case == "unknown_precision":
        assert result["reaction_checks"][0]["csv_flux_comparison"] == "unknown"
    elif case == "different_flux":
        assert result["reaction_checks"][0]["csv_flux_comparison"] == "conflicts"
    else:
        sheet["native_solution"]["native"]["reaction_values"].pop(0)
        result = calc(sheet)
        assert result["reaction_checks"][0]["csv_flux"]["value"] == 10
        assert result["reaction_checks"][0]["flux"]["value"] is None
        assert result["reaction_checks"][0]["flux_basis"] == "unavailable"


def test_removed_invalid_native_row_with_located_issue_never_allows_csv_fallback():
    sheet = make_sheet()
    solution = sheet["native_solution"]["native"]
    solution["reaction_values"].pop(0)
    solution["issues"].append({"code": "schema_invalid", "stage": "parse", "field": "/reaction_values/0/flux/value",
        "source_row_index": 0, "reaction_position": 0, "metabolite_position": None, "variable_position": None,
        "constraint_position": None, "detail_file": deepcopy(FILE)})
    result = calc(sheet)
    assert result["reaction_checks"][0]["flux_basis"] == "unavailable"
    assert result["reaction_checks"][0]["flux"]["value"] is None
    assert not any(issue["code"] == "duplicate_reaction_id" for issue in result["issues"])


def test_native_activity_conflict_remains_distinct_from_calculated_row():
    sheet = make_sheet()
    sheet["native_solution"]["native"]["constraint_values"] = [{"constraint_position": 0,
        "constraint_id": "A", "activity": number(3), "shadow_price": number()}]
    result = calc(sheet)
    row = result["constraint_checks"][0]
    assert row["activity"]["value"] == 0
    assert row["native_activity"]["value"] == 3
    assert row["native_minus_calculated_activity"]["value"] == 3
    assert row["native_activity_comparison"] == "conflicts"
    assert row["comparison"] == "passes"


def test_unknown_populations_and_missing_request_do_not_become_zero_or_default():
    sheet = make_sheet()
    sheet["models"]["effective"] = None
    sheet["problems"]["effective"] = None
    sheet["native_solution"]["native"] = None
    sheet["native"].update(solve_call_count=None, objective_request=None, constraint_changes=None,
        objective_application="unknown", request_realization="unknown", execution_outcome="unknown")
    sheet["original_request_file"] = None
    result = calc(sheet)
    assert result["expected_reaction_count"] is result["valid_flux_count"] is None
    assert result["expected_variable_count"] is result["valid_variable_count"] is None
    assert result["active_count"] is None
    assert result["candidate_feasibility"] == "unknown"


def test_known_empty_population_has_zero_counts_but_no_coverage_denominator():
    sheet = make_sheet()
    model, problem, solution = sheet["models"]["effective"], sheet["problems"]["effective"], sheet["native_solution"]["native"]
    for key in ("compartments", "genes", "metabolites", "reactions", "groups", "stoichiometry"):
        model[key] = []
        if key in model["population"]:
            model["population"][key] = 0
    for key in ("variables", "constraints", "reaction_variables"):
        problem[key] = []
    problem["variable_count"] = problem["constraint_count"] = 0
    problem["objective"]["terms"] = []
    for key in ("variable_values", "reaction_values", "constraint_values"):
        solution[key] = []
    sheet["native"]["flux_rows"] = []
    result = calc(sheet)
    assert result["expected_reaction_count"] == result["valid_flux_count"] == 0
    assert result["expected_variable_count"] == result["valid_variable_count"] == 0
    assert result["flux_coverage_fraction"]["value"] is None
    assert result["flux_coverage_fraction"]["issue_codes"] == ["zero_denominator"]
    assert result["active_count"] == 0
    assert result["max_abs_balance_residual"]["value"] is None


def test_two_alternative_points_never_imply_unique_optimum():
    sheet = make_sheet()
    model, problem, solution = sheet["models"]["effective"], sheet["problems"]["effective"], sheet["native_solution"]["native"]
    reaction = deepcopy(model["reactions"][1]); reaction.update(position=3, id="AB2", name="AB2")
    model["reactions"].append(reaction); model["population"]["reactions"] = 4
    model["stoichiometry"].extend([{"metabolite_position": i, "reaction_position": 3,
        "coefficient": number(value), "coefficient_unit": unit("1")} for i, value in ((0, -1), (1, 1))])
    for pos, identifier, upper in ((6, "AB2", 1000), (7, "AB2_reverse", 0)):
        variable = deepcopy(problem["variables"][2]); variable.update(position=pos, native_index=pos + 1,
            optlang_position=pos, id=identifier, upper=bound(upper))
        problem["variables"].append(variable)
        solution["variable_values"].append({"variable_position": pos, "variable_id": identifier,
            "primal": number(0), "reduced_cost": number()})
    problem["variable_count"] = 8
    problem["reaction_variables"].append({"reaction_position": 3, "reaction_id": "AB2",
        "forward_variable_position": 6, "forward_variable_id": "AB2", "reverse_variable_position": 7,
        "reverse_variable_id": "AB2_reverse", "flux_expression_pointer": "/fixture/AB2"})
    problem["constraints"][0]["terms"].extend([term(6, -1), term(7, 1)])
    problem["constraints"][1]["terms"].extend([term(6, 1), term(7, -1)])
    solution["reaction_values"].append({"reaction_position": 3, "reaction_id": "AB2", "flux": number(0), "reduced_cost": number()})
    sheet["native"]["flux_rows"] = []
    first = calc(sheet)
    solution["reaction_values"][1]["flux"] = number(0); solution["variable_values"][2]["primal"] = number(0)
    solution["reaction_values"][3]["flux"] = number(10); solution["variable_values"][6]["primal"] = number(10)
    second = calc(sheet)
    assert first["candidate_feasibility"] == second["candidate_feasibility"] == "passes_recorded_checks"
    assert first["objective"]["full_calculated"]["value"] == second["objective"]["full_calculated"]["value"] == 10
    assert first["optimum_multiplicity"] == second["optimum_multiplicity"] == "not_assessed"


def test_inconsistent_native_token_and_value_cannot_be_labeled_full_precision():
    record = number(1)
    record["native_token"] = "20"
    with pytest.raises(ValueError, match="native_token"):
        validate_flux_balance_record("Number", record)
    record = number(9007199254740993)
    assert validate_flux_balance_record("Number", record)["value"] == 9007199254740993


def test_full_precision_negative_zero_and_hex_mismatch_validation():
    recorded = number(-0.0)
    checked = validate_flux_balance_record("Number", recorded)
    assert math.copysign(1, checked["value"]) == -1
    assert checked["float_hex"] == "-0x0.0p+0"
    recorded["float_hex"] = "0x0.0p+0"
    with pytest.raises(ValueError, match="schema_invalid"):
        validate_flux_balance_record("Number", recorded)


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), "10"])
def test_malformed_numeric_types_never_become_numbers(value):
    recorded = number(10)
    recorded["value"] = value
    with pytest.raises(ValueError, match="schema_invalid"):
        validate_flux_balance_record("Number", recorded)


def test_duplicate_terms_and_conflicting_joins_reject_without_summing():
    sheet = make_sheet()
    problem = sheet["problems"]["effective"]
    problem["constraints"][0]["terms"].append(deepcopy(problem["constraints"][0]["terms"][0]))
    with pytest.raises(ValueError):
        validate_flux_balance_sheet(sheet)
    sheet = make_sheet()
    sheet["native_solution"]["native"]["variable_values"][0]["variable_id"] = "OUT"
    with pytest.raises(ValueError, match="variable_identity_conflict"):
        validate_flux_balance_sheet(sheet)


def test_partial_missing_position_cannot_borrow_id_from_an_existing_other_position():
    sheet = make_sheet()
    problem = sheet["problems"]["effective"]
    problem["representation"] = "partial"
    problem["variables"].pop(2)
    sheet["native_solution"]["native"]["variable_values"][2]["variable_id"] = "IN"
    with pytest.raises(ValueError, match="variable_identity_conflict"):
        validate_flux_balance_sheet(sheet)


def test_overflow_is_explicit_and_compensated_sum_retains_small_term():
    sheet = make_sheet()
    objective = sheet["problems"]["effective"]["objective"]
    objective["terms"] = [term(0, 1e308)]
    result = calc(sheet)
    assert result["objective"]["native_basis_calculated"]["state"] == "overflow"
    assert result["objective"]["native_basis_calculated"]["value"] is None
    objective["terms"] = [term(0, 1), term(2, 1), term(4, 1)]
    for row, value in zip(sheet["native_solution"]["native"]["variable_values"][::2], [1e16, 1.0, -1e16]):
        row["primal"] = number(value)
    result = calc(sheet)
    assert result["objective"]["full_calculated"]["value"] == 1.0


def test_finite_constant_and_nonzero_rhs_are_each_applied_once():
    sheet = make_sheet()
    row = sheet["problems"]["effective"]["constraints"][0]
    row["constant"] = number(3)
    row["lower"] = row["upper"] = bound(3)
    objective = sheet["problems"]["effective"]["objective"]
    objective["native_constant"] = number(2)
    objective["interface_offset"] = number(1.5)
    objective["symbolic_constant"] = number(3.5)
    result = calc(sheet)
    assert result["constraint_checks"][0]["activity"]["value"] == 3
    assert result["constraint_checks"][0]["equality_residual"]["value"] == 0
    assert result["objective"]["native_basis_calculated"]["value"] == 12
    assert result["objective"]["full_calculated"]["value"] == 13.5


def test_parameters_cannot_select_unknown_or_duplicate_entity():
    sheet = make_sheet()
    settings = parameters(sheet)
    settings["variable_bound_tolerances"][0]["subject_id"] = "invented"
    with pytest.raises(ValueError, match="missing_parameters"):
        calculate_flux_balance_sheet(sheet, parameters=settings)
    settings = parameters(sheet)
    settings["active_flux_thresholds"].append(deepcopy(settings["active_flux_thresholds"][0]))
    with pytest.raises(ValueError, match="missing_parameters"):
        calculate_flux_balance_sheet(sheet, parameters=settings)


def test_detached_schema_and_explicit_bytes_boundary():
    schema = flux_balance_schema("Number")
    schema["properties"].clear()
    assert "state" in flux_balance_schema("Number")["properties"]
    assert isinstance(ISSUE_CODES, frozenset)
    with pytest.raises(ValueError, match="unsupported_host_schema"):
        flux_balance_schema("FBAArtifactPayloads")
    roles = "original_model selected_request effective_model effective_problem solution flux_csv native_log manifest".split()
    payloads = {role: {"file": None, "bytes": None, "state": "absent"} for role in roles}
    raw = b"source bytes"
    payloads["flux_csv"] = {"file": deepcopy(FILE), "bytes": raw, "state": "present"}
    checked = validate_fba_artifact_payloads(payloads)
    assert checked["flux_csv"]["bytes"] is raw
    checked["flux_csv"]["file"]["format"] = "changed"
    assert payloads["flux_csv"]["file"]["format"] == FILE["format"]
    payloads["flux_csv"]["state"] = "absent"
    with pytest.raises(ValueError, match="artifact_identity_conflict"):
        validate_fba_artifact_payloads(payloads)


def test_saved_sheet_recalculation_without_files_solver_or_imports(monkeypatch):
    sheet = make_sheet((10.0, 12.0, 12.0))
    encoded = json.dumps(sheet, allow_nan=False)
    saved = json.loads(encoded)
    tight, loose = parameters(saved), parameters(saved, tolerance=2, active=11)
    def forbidden(*args, **kwargs):
        raise AssertionError("calculator attempted external work")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(builtins, "__import__", forbidden)
    first = calculate_flux_balance_sheet(saved, parameters=tight)
    second = calculate_flux_balance_sheet(saved, parameters=loose)
    assert first["candidate_feasibility"] == "fails_recorded_checks"
    assert second["candidate_feasibility"] == "passes_recorded_checks"
    assert first["active_count"] == 3 and second["active_count"] == 2
    assert first["sheet_sha256"] == second["sheet_sha256"]
    assert json.dumps(saved, allow_nan=False) == encoded


def _normalized_probe677():
    """Explicit test transformation of three hash-pinned saved API artifacts.

    Metadata not observed in those probe files remains fixture metadata. This
    conversion does not claim to implement the future producer/capture format.
    """
    root = Path(__file__).parents[1] / "verification/tool_graders_flux_balance_native_contract_2026-10-29_677/probe"
    pins = {"effective_problem.json": "4b7976dd1641d74ee0e692f752db2909b040dba6da824cd160b8c9ec07196d2b",
        "native_solution.json": "9b2e4f2088f81cf4c3acf353e16c782da98b3dd0823978962b3d3b692042225c",
        "solution.json": "ccc06fc47b323519a909d69fa8be2224992bd28f2caa7969ded368b52f3e8729"}
    captured, files = {}, {}
    for name, expected in pins.items():
        raw = (root / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
        files[name] = {"artifact_ref": "test-transformation677:" + name, "sha256": expected,
            "size_bytes": len(raw), "format": "retained677_api_probe_json"}
        captured[name] = json.loads(raw)
    problem_data, native_data, cobra_data = (captured[name] for name in pins)
    sheet = make_sheet((7.0, 6.0, 6.0))
    sheet["retained_files"].extend(files.values())
    model = sheet["models"]["effective"]
    model["annotations"]["fixture"] = "test-only normalization of retained 677 point, not production capture"
    model["reactions"][0]["lower"], model["reactions"][0]["upper"] = bound(-10), bound(8)
    for row in model["reactions"][1:]:
        row["upper"] = bound(kind="positive_infinity")
    def loc(name, pointer):
        return {"file": deepcopy(files[name]), "pointer": pointer}
    def scalar(raw, name, pointer):
        assert raw["state"] == "finite"
        return {"value": raw["value"], "state": "present", "native_token": raw["native_token"],
            "float_hex": raw["float_hex"], "precision": "full_native", "source": loc(name, pointer), "missing_reason": None}
    def probe_bound(raw, name, pointer, side):
        if raw["state"] == "missing":
            # In these inspected optlang getter snapshots None means unbounded.
            return {"kind": "negative_infinity" if side == "lower" else "positive_infinity", "value": None,
                "native_token": None, "float_hex": None, "source": loc(name, pointer)}
        return {"kind": "finite", "value": raw["value"], "native_token": raw["native_token"],
            "float_hex": raw["float_hex"], "source": loc(name, pointer)}
    problem = sheet["problems"]["effective"]
    template = deepcopy(problem["variables"][0])
    problem["variables"] = []
    for raw in problem_data["variables"]:
        i = raw["position"]
        row = {**deepcopy(template), "position": i, "native_index": i + 1, "optlang_position": i,
            "id": raw["name"], "kind": raw["type"], "unit": unit(None),
            "source": loc("effective_problem.json", f"/variables/{i}")}
        for side in ("lower", "upper"):
            row[side] = probe_bound(raw[side], "effective_problem.json", f"/variables/{i}/{side}", side)
        problem["variables"].append(row)
    template = deepcopy(problem["constraints"][0])
    problem["constraints"] = []
    for raw in problem_data["constraints"]:
        i = raw["position"]
        row = {**deepcopy(template), "position": i, "native_index": i + 1, "optlang_position": i, "id": raw["name"],
            "kind": "metabolite_balance" if i < 2 else "additional_linear", "metabolite_position": i if i < 2 else None,
            "constant": scalar(raw["offset"], "effective_problem.json", f"/constraints/{i}/offset"),
            "terms": [{"variable_position": term["variable_position"],
                "coefficient": scalar(term["coefficient"], "effective_problem.json", f"/constraints/{i}/terms/{j}/coefficient")}
                for j, term in enumerate(raw["terms"])], "active_when": raw["active_when"], "unit": unit(None),
            "native_expression_pointer": f"/constraints/{i}/expression", "source": loc("effective_problem.json", f"/constraints/{i}")}
        for side in ("lower", "upper"):
            row[side] = probe_bound(raw[side], "effective_problem.json", f"/constraints/{i}/{side}", side)
        problem["constraints"].append(row)
    problem["variable_count"], problem["constraint_count"] = 7, 5
    problem["native_optlang_json"] = problem_data["optlang_json"]
    objective = problem["objective"]
    objective.update(direction="min", native_direction_code=1, unit=unit(None),
        native_constant=scalar(native_data["glpk_objective_constant"], "native_solution.json", "/glpk_objective_constant"),
        interface_offset=scalar(native_data["optlang_objective_offset"], "native_solution.json", "/optlang_objective_offset"),
        symbolic_constant=scalar(problem_data["objective"]["offset"], "effective_problem.json", "/objective/offset"),
        terms=[{"variable_position": term["variable_position"],
            "coefficient": scalar(term["coefficient"], "effective_problem.json", f"/objective/terms/{j}/coefficient")}
            for j, term in enumerate(problem_data["objective"]["terms"])])
    for row, raw in zip(problem["reaction_variables"], problem_data["reaction_variables"]):
        row.update(forward_variable_id=raw["forward_name"], reverse_variable_id=raw["reverse_name"])
    for row in model["reactions"]:
        row["flux_unit"] = unit(None)
    solution = sheet["native_solution"]["native"]
    solution["variable_values"] = [{"variable_position": row["position"], "variable_id": row["name"],
        "primal": scalar(row["primal"], "native_solution.json", f"/variables/{i}/primal"),
        "reduced_cost": scalar(row["dual"], "native_solution.json", f"/variables/{i}/dual")}
        for i, row in enumerate(native_data["variables"])]
    solution["constraint_values"] = [{"constraint_position": row["position"], "constraint_id": row["name"],
        "activity": scalar(row["primal"], "native_solution.json", f"/constraints/{i}/primal"),
        "shadow_price": scalar(row["dual"], "native_solution.json", f"/constraints/{i}/dual")}
        for i, row in enumerate(native_data["constraints"])]
    solution["native_glpk_objective"] = scalar(native_data["native_objective"], "native_solution.json", "/native_objective")
    solution["native_cobra_objective"] = scalar(cobra_data["objective"], "solution.json", "/objective")
    # The probe records this actual optlang value in configuration/summary; this
    # fixture only uses the three selected files, so unavailable stays missing.
    solution["native_optlang_objective"] = number()
    for i, row in enumerate(solution["reaction_values"]):
        row["flux"] = scalar(cobra_data["fluxes"][i]["value"], "solution.json", f"/fluxes/{i}/value")
    sheet["native"]["objective"] = number()
    sheet["native"]["flux_rows"] = []
    return validate_flux_balance_sheet(sheet), pins


def test_retained_677_point_normalized_only_for_numerical_verification():
    sheet, pins = _normalized_probe677()
    result = calc(sheet)
    rows = {row["constraint_id"]: row for row in result["constraint_checks"]}
    assert [row["flux"]["value"] for row in result["reaction_checks"]] == [7, 6, 6]
    assert result["variable_checks"][6]["primal"]["value"] == 6
    assert rows["A_c"]["activity"]["value"] == 1
    assert rows["A_c"]["equality_residual"]["value"] == 0
    assert rows["net_cap"]["activity"]["value"] == 12
    assert rows["split_cap"]["activity"]["value"] == 7
    assert rows["split_cap"]["upper_slack"]["value"] == 2
    assert rows["aux_link"]["equality_residual"]["value"] == 0
    assert result["objective"]["native_basis_calculated"]["value"] == -4.25
    assert result["objective"]["full_calculated"]["value"] == -2.75
    assert result["objective"]["glpk_comparison"] == result["objective"]["cobra_comparison"] == "agrees"
    assert result["evaluated_variable_bound_count"] == 11
    assert result["candidate_feasibility"] == "passes_recorded_checks"
    assert result["max_abs_balance_residual"]["value"] is None  # source units are unknown
    attempt = os.environ.get("HMMER529_ATTEMPT")
    if attempt:
        Path(attempt, "fba679_numerical_examples.json").write_text(json.dumps({
            "fixture_identity": "test-only transformation of retained677 API probe; no new solve; no production capture",
            "source_hashes": pins, "sheet": sheet, "calculations": result}, indent=2, allow_nan=False) + "\n")
