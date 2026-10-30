"""680 reader tests; normalized captures are TEST transformations, not a producer.

The untouched five-column CSV is authentic retained 677 output.  The normalized
fixtures below explicitly translate 677's diagnostic API evidence into the
frozen contract.  No final-format production capture or additional solve is
claimed. SBML/JSON profile equivalence is a controlled normalized-format test.
"""
from copy import deepcopy
import builtins
import hashlib
import json
import math
from pathlib import Path

import pytest

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.flux_balance_contracts import validate_flux_balance_record
from gene_annotation_episode.flux_balance_readers import (
    parse_biomni_fba_csv, parse_cobra_glpk_model_capture,
    parse_cobra_glpk_problem_capture, parse_cobra_glpk_solution_capture, parse_fba_capture,
)

PROBE = Path(__file__).resolve().parents[1] / "verification/tool_graders_flux_balance_native_contract_2026-10-29_677/probe"
UNKNOWN_UNIT = {"native_text": None, "basis": "unknown", "source": None}
ROLES = ("original_model", "selected_request", "effective_model", "effective_problem", "solution", "flux_csv", "native_log", "manifest")


def read(name):
    return json.loads((PROBE / name).read_bytes())


def encode(value):
    return json.dumps(value, allow_nan=False, separators=(",", ":")).encode()


def file(raw, format):
    sha = hashlib.sha256(raw).hexdigest()
    return {"artifact_ref": "artifact_" + sha, "sha256": sha, "size_bytes": len(raw), "format": format}


def location(role, pointer):
    return {"role": role, "pointer": pointer}


def number(value, pointer, role="effective_model"):
    if type(value) is dict:
        return {"value": value["value"], "state": "present" if value["state"] == "finite" else value["state"],
                "native_token": value["native_token"], "float_hex": value["float_hex"],
                "precision": "full_native", "source": location(role, pointer),
                "missing_reason": "not_returned" if value["state"] == "missing" else None}
    return {"value": value, "state": "present", "native_token": str(value),
            "float_hex": value.hex() if type(value) is float else None, "precision": "full_native",
            "source": location(role, pointer), "missing_reason": None}


def missing():
    return {"value": None, "state": "missing", "native_token": None, "float_hex": None,
            "precision": "unknown", "source": None, "missing_reason": "unsupported_api"}


def bound(value, pointer, role="effective_model", lower=False):
    if type(value) is dict:
        if value["state"] == "missing":
            value = "-inf" if lower else "inf"
        else:
            return {"kind": "finite", "value": value["value"], "native_token": value["native_token"],
                    "float_hex": value["float_hex"], "source": location(role, pointer)}
    return {"kind": ("negative_infinity" if value == "-inf" else "positive_infinity") if type(value) is str else "finite",
            "value": None if type(value) is str else value, "native_token": str(value),
            "float_hex": value.hex() if type(value) is float else None, "source": location(role, pointer)}


def normalize_model(raw, phase):
    """Test-only translation of recorded model data, with no new biological data."""
    native = raw["cobra_json"]
    base = "/" + phase
    genes = [{"position": i, "id": row["id"], "name": row.get("name"), "associations": [],
              "supplied_target_refs": [], "annotation_pointer": None, "notes_pointer": None}
             for i, row in enumerate(native["genes"])]
    metabolites = [{"position": i, "id": row["id"], "name": row.get("name"), "compartment_position": 0,
        "formula": row.get("formula"), "charge": number(row["charge"], f"{base}/native_cobra_json/metabolites/{i}/charge"),
        "associations": [], "annotation_pointer": None, "notes_pointer": None}
        for i, row in enumerate(native["metabolites"])]
    reactions, stoich = [], []
    gene_pos = {row["id"]: row["position"] for row in genes}
    met_pos = {row["id"]: row["position"] for row in metabolites}
    for i, row in enumerate(native["reactions"]):
        loaded = raw["reactions"][i]
        reactions.append({"position": i, "id": row["id"], "name": row.get("name"),
            "lower": bound(row["lower_bound"], f"{base}/native_cobra_json/reactions/{i}/lower_bound"),
            "upper": bound(row["upper_bound"], f"{base}/native_cobra_json/reactions/{i}/upper_bound"),
            "flux_unit": deepcopy(UNKNOWN_UNIT), "boundary_kind": "unknown", "boundary_source": None,
            "gpr_native": None, "gpr_source_pointer": None, "gpr_loaded": loaded["gpr"],
            "gene_positions": [gene_pos[name] for name in loaded["gene_ids_in_model_order"]],
            "associations": [], "annotation_pointer": None, "notes_pointer": None})
        for j, term in enumerate(loaded["stoichiometry"]):
            stoich.append({"metabolite_position": met_pos[term["metabolite_id"]], "reaction_position": i,
                "coefficient": number(term["coefficient"], f"{base}/stoichiometry/{len(stoich)}/coefficient/value"),
                "coefficient_unit": deepcopy(UNKNOWN_UNIT)})
    return {"model_id": native["id"], "model_name": native.get("name"),
        "compartments": [{"position": i, "id": key, "name": value} for i, (key, value) in enumerate(raw["compartments"])],
        "genes": genes, "metabolites": metabolites, "reactions": reactions, "stoichiometry": stoich,
        "groups": [], "annotations": {}, "notes": {}, "sbml_metadata": raw.get("sbml_metadata"),
        "native_cobra_json": native, "native_sbml_export": None,
        "medium": [], "medium_state": "not_retained", "medium_basis": "unknown",
        "population": {"compartments": len(raw["compartments"]), "genes": len(genes),
                       "metabolites": len(metabolites), "reactions": len(reactions), "groups": 0, "completeness": "complete"}}


def model_payload(profile="sbml"):
    return {"version": "cobra_model_capture_v1",
        "loaded_original": normalize_model(read("original_loaded_model.json"), "loaded_original"),
        "effective": normalize_model(read("effective_model.json"), "effective"),
        "input_profile": profile,
        "loader": {"name": "read_sbml_model" if profile == "sbml" else "load_json_model", "cobra_version": "0.32.1",
                   "number_type": "float64", "id_replacement": "cobra_F_REPLACE" if profile == "sbml" else "none"},
        "source_to_loaded_ids": [], "source_feature_audit": [], "issues": []}


def normalized_config(role, pointer):
    raw = read("configuration.json")
    result = {"interface": raw["interface"], "glpk_version": raw["glpk_version"],
        "cobra_version": raw["distributions"]["cobra"], "optlang_version": raw["distributions"]["optlang"],
        "swiglpk_version": raw["distributions"]["swiglpk"],
        "model_tolerance": number(raw["model_tolerance"], pointer + "/model_tolerance/value", role),
        "presolve": raw["configuration"]["presolve"], "verbosity": raw["configuration"]["verbosity"],
        "timeout_seconds": raw["configuration"]["timeout"], "optimality_tolerance": missing(),
        "simplex_controls": raw["simplex_control"], "integer_controls_pointer": ""}
    for key in ("feasibility", "integrality"):
        result[key + "_tolerance"] = number(raw["public_tolerances"][key], pointer + "/" + key + "_tolerance/value", role)
    return result


def normalize_problem(raw, phase):
    """Test transformation using documented GLPK codes, not a production capture."""
    base, role = "/" + phase, "effective_problem"
    def type_code(lb, ub):
        if lb["kind"] == "finite" and ub["kind"] == "finite":
            return 5 if lb["value"] == ub["value"] else 4
        return 2 if lb["kind"] == "finite" else 3 if ub["kind"] == "finite" else 1
    variables, constraints = [], []
    for i, row in enumerate(raw["variables"]):
        path = f"{base}/variables/{i}"
        lower, upper = bound(row["lower"], path + "/lower/value", role, True), bound(row["upper"], path + "/upper/value", role)
        variables.append({"position": i, "native_index": i + 1, "optlang_position": i, "id": row["name"],
            "kind": row["type"], "native_kind_code": 1, "native_bound_type_code": type_code(lower, upper),
            "lower": lower, "upper": upper, "unit": deepcopy(UNKNOWN_UNIT), "source": location(role, path)})
    def terms(rows, path):
        return [{"variable_position": row["variable_position"],
                 "coefficient": number(row["coefficient"], f"{path}/{i}/coefficient/value", role)} for i, row in enumerate(rows)]
    for i, row in enumerate(raw["constraints"]):
        path = f"{base}/constraints/{i}"
        lower, upper = bound(row["lower"], path + "/lower/value", role, True), bound(row["upper"], path + "/upper/value", role)
        constraints.append({"position": i, "native_index": i + 1, "optlang_position": i, "id": row["name"],
            "kind": "metabolite_balance" if i < 2 else "additional_linear", "metabolite_position": i if i < 2 else None,
            "constant": number(row["offset"], path + "/constant/value", role),
            "terms": terms(row["terms"], path + "/terms"), "terms_complete": True,
            "lower": lower, "upper": upper, "native_bound_type_code": type_code(lower, upper),
            "indicator_variable_position": None, "active_when": row["active_when"], "expression_kind": "linear",
            "native_expression_pointer": f"{base}/native_optlang_json/constraints/{i}/expression",
            "unit": deepcopy(UNKNOWN_UNIT), "source": location(role, path)})
    native = read("native_solution.json")
    obj = raw["objective"]
    return {"version": "cobra_glpk_problem_snapshot_v1", "phase": phase,
        "variable_count": len(variables), "constraint_count": len(constraints),
        "variables": variables, "constraints": constraints,
        "objective": {"direction": obj["direction"], "native_direction_code": 1 if obj["direction"] == "min" else 2,
            "native_constant": number(native["glpk_objective_constant"], base + "/objective/native_constant/value", role),
            "interface_offset": number(obj["offset"], base + "/objective/interface_offset/value", role),
            "symbolic_constant": number(obj["offset"], base + "/objective/symbolic_constant/value", role),
            "terms": terms(obj["terms"], base + "/objective/terms"), "terms_complete": True, "expression_kind": "linear",
            "native_expression_pointer": base + "/native_optlang_json/objective/expression",
            "unit": deepcopy(UNKNOWN_UNIT), "source": location(role, base + "/objective")},
        "reaction_variables": [{"reaction_position": row["reaction_position"], "reaction_id": row["reaction_id"],
            "forward_variable_position": row["forward_position"], "forward_variable_id": row["forward_name"],
            "reverse_variable_position": row["reverse_position"], "reverse_variable_id": row["reverse_name"],
            "flux_expression_pointer": ""} for row in raw["reaction_variables"]],
        "representation": "complete_continuous_linear", "native_optlang_json": raw["optlang_json"],
        "native_glpk_text": None, "native_lp_text": None, "issues": []}


def problem_payload():
    return {"version": "cobra_glpk_problem_capture_v1",
        "loaded_original": normalize_problem(read("original_problem.json"), "loaded_original"),
        "effective": normalize_problem(read("effective_problem.json"), "effective"),
        "configuration_before_solve": normalized_config("effective_problem", "/configuration_before_solve"), "issues": []}


def solution_payload():
    native, cobra, role = read("native_solution.json"), read("solution.json"), "solution"
    return {"version": "cobra_glpk_solution_capture_v1", "model_optimize_call_count": 1,
        "native_passes": [{"position": i, "routine": row["routine"], "return_code": row["return_code"],
            "raw_status_code": row["raw_status"], "primal_status_code": row["primal_status"],
            "dual_status_code": row["dual_status"], "parameters_pointer": "/configuration_after_solve/simplex_controls",
            "exception_pointer": None} for i, row in enumerate(native["native_passes"])],
        "solution_object_state": "returned", "optlang_status": native["optlang_status"], "cobra_solution_status": cobra["status"],
        "glpk_status_code": native["glpk_status"], "glpk_primal_status_code": native["glpk_primal_status"],
        "glpk_dual_status_code": native["glpk_dual_status"], "point_state": "basic_solution",
        "native_glpk_objective": number(native["native_objective"], "/native_glpk_objective/value", role),
        "native_optlang_objective": number(cobra["objective"], "/native_optlang_objective/value", role),
        "native_cobra_objective": number(cobra["objective"], "/native_cobra_objective/value", role),
        "variable_values": [{"variable_position": row["position"], "variable_id": row["name"],
            "primal": number(row["primal"], f"/variable_values/{i}/primal/value", role),
            "reduced_cost": number(row["dual"], f"/variable_values/{i}/reduced_cost/value", role)} for i, row in enumerate(native["variables"])],
        "constraint_values": [{"constraint_position": row["position"], "constraint_id": row["name"],
            "activity": number(row["primal"], f"/constraint_values/{i}/activity/value", role),
            "shadow_price": number(row["dual"], f"/constraint_values/{i}/shadow_price/value", role)} for i, row in enumerate(native["constraints"])],
        "reaction_values": [{"reaction_position": i, "reaction_id": row["reaction_id"],
            "flux": number(row["value"], f"/reaction_values/{i}/flux/value", role),
            "reduced_cost": number(cobra["reduced_costs"][i]["value"], f"/reaction_values/{i}/reduced_cost/value", role)} for i, row in enumerate(cobra["fluxes"])],
        "configuration_after_solve": normalized_config(role, "/configuration_after_solve"), "diagnostics_pointer": "", "issues": []}


@pytest.fixture
def captures():
    models, problems, solution = model_payload(), problem_payload(), solution_payload()
    original = (PROBE / "original.xml").read_bytes()
    raw = {"original_model": original, "effective_model": encode(models), "effective_problem": encode(problems),
           "solution": encode(solution), "flux_csv": (PROBE / "flux.csv").read_bytes(), "native_log": b"native diagnostic text\n"}
    formats = {"original_model": "sbml", "effective_model": models["version"], "effective_problem": problems["version"],
               "solution": solution["version"], "flux_csv": "biomni_fba_csv_v1", "native_log": "utf8_text"}
    files = {role: file(data, formats[role]) for role, data in raw.items()}
    return {"models": models, "problems": problems, "solution": solution, "raw": raw, "files": files}


def parsed(captures):
    c = captures
    m = parse_cobra_glpk_model_capture(c["raw"]["effective_model"], source=c["files"]["effective_model"], original_model=c["files"]["original_model"])
    p = parse_cobra_glpk_problem_capture(c["raw"]["effective_problem"], source=c["files"]["effective_problem"], models=m)
    s = parse_cobra_glpk_solution_capture(c["raw"]["solution"], source=c["files"]["solution"], problem=p["effective"])
    return m, p, s


def parse_model(payload, c):
    raw = encode(payload)
    return parse_cobra_glpk_model_capture(raw, source=file(raw, "cobra_model_capture_v1"), original_model=c["files"]["original_model"])


def parse_problem(payload, c):
    raw = encode(payload)
    return parse_cobra_glpk_problem_capture(raw, source=file(raw, "cobra_glpk_problem_capture_v1"), models=parsed(c)[0])


def parse_solution(payload, c):
    raw = encode(payload)
    return parse_cobra_glpk_solution_capture(raw, source=file(raw, "cobra_glpk_solution_capture_v1"), problem=parsed(c)[1]["effective"])


def codes(parsed):
    return {row["code"] for row in parsed["issues"]}


def test_authentic_csv_retains_native_fluxes_and_original_indices(captures):
    c = captures
    assert c["files"]["flux_csv"]["sha256"] == "fc2b47649252d0d3a756f3e2877a9e1293f9123e1a08e435d971cf640693c52c"
    result = parse_biomni_fba_csv(c["raw"]["flux_csv"], model=parsed(c)[0]["effective"], source=c["files"]["flux_csv"])
    assert [(r["source_row_index"], r["reaction_id"], r["reaction_position"], r["flux"]["value"]) for r in result["rows"]] == [(0, "IN", 0, 7), (1, "AB", 1, 6), (2, "OUT", 2, 6)]
    assert all(r["flux"]["precision"] == "unknown" and r["flux"]["float_hex"] is None for r in result["rows"])
    assert result["rows"][2]["csv_upper"]["kind"] == "positive_infinity"


def test_normalized_recorded_point_uses_native_basis_and_separate_objective_parts(captures):
    m, p, s = parsed(captures)
    assert m["issues"] == p["issues"] == s["issues"] == []
    assert len(p["effective"]["variables"]) == 7
    assert len(p["effective"]["constraints"]) == 5
    assert p["effective"]["constraints"][0]["lower"]["value"] == 1
    assert p["effective"]["objective"]["native_constant"]["value"] == 0
    assert p["effective"]["objective"]["interface_offset"]["value"] == 1.5
    assert p["loaded_original"]["objective"]["interface_offset"]["value"] == 0
    assert s["native"]["native_glpk_objective"]["value"] == -4.25
    assert s["native"]["native_cobra_objective"]["value"] == -2.75
    assert [(r["variable_id"], r["primal"]["value"]) for r in s["native"]["variable_values"]][-1] == ("aux", 6)
    assert s["native"]["native_glpk_objective"]["source"] == {"file": captures["files"]["solution"], "pointer": "/native_glpk_objective/value"}


@pytest.mark.parametrize("profile", ["sbml", "cobra_json"])
def test_normalized_profiles_feed_the_identical_shared_records(captures, profile):
    payload = model_payload(profile)
    raw = encode(payload)
    original_raw = captures["raw"]["original_model"] if profile == "sbml" else (PROBE / "original_export.json").read_bytes()
    result = parse_cobra_glpk_model_capture(raw, source=file(raw, "cobra_model_capture_v1"), original_model=file(original_raw, profile))
    validate_flux_balance_record("ParsedModelSnapshots", result)
    assert result["input_profile"] == profile
    assert [(r["id"], r["lower"]["value"], r["upper"]["kind"]) for r in result["effective"]["reactions"]] == [("IN", -10, "finite"), ("AB", 0, "positive_infinity"), ("OUT", 0, "positive_infinity")]


def test_original_and_loaded_gpr_raw_metadata_not_reinterpreted(captures):
    payload = captures["models"]
    row = payload["effective"]["reactions"][1]
    row["gpr_native"], row["gpr_loaded"] = "source-specific unresolved rule", "one and two"
    payload["effective"]["annotations"]["opaque"] = {"role": "unrecognized", "pointer": "do not bind"}
    result = parse_model(payload, captures)
    assert result["effective"]["reactions"][1]["gpr_native"] == "source-specific unresolved rule"
    assert result["effective"]["annotations"]["opaque"] == {"role": "unrecognized", "pointer": "do not bind"}


def test_csv_malformed_unknown_duplicate_and_reordered_rows_do_not_shift(captures):
    raw = b"reaction_id,reaction_name,flux,lower_bound,upper_bound\nOUT,last,6,0,inf\nbroken,row\nIN,first,7,-10,8\nUNKNOWN,x,4,0,8\nAB,middle,nan,0,inf\nIN,duplicate,7,-10,8\n"
    result = parse_biomni_fba_csv(raw, source=file(raw, "biomni_fba_csv_v1"), model=parsed(captures)[0]["effective"])
    assert [(r["source_row_index"], r["reaction_position"]) for r in result["rows"]] == [(0, 2), (2, 0), (3, None), (4, 1), (5, 0)]
    assert [r["association"] for r in result["rows"]] == ["matched", "duplicate", "unknown", "matched", "duplicate"]
    assert result["rows"][3]["flux"]["state"] == "nonfinite"
    assert result["rows"][3]["flux"]["source"]["pointer"] == "/rows/4/flux"


@pytest.mark.parametrize("token,state", [("", "missing"), ("true", "invalid"), ("nan", "nonfinite"), ("-inf", "nonfinite"), ("1e9999", "invalid"), ("1e-9999", "invalid"), ("0", "present"), ("-0.0", "present"), ("0.123456789123456789", "present")])
def test_csv_number_precision_missing_and_signed_zero(token, state):
    raw = ("reaction_id,reaction_name,flux,lower_bound,upper_bound\nR,name," + token + ",-inf,inf\n").encode()
    result = parse_biomni_fba_csv(raw, model=None, source=file(raw, "biomni_fba_csv_v1"))
    n = result["rows"][0]["flux"]
    assert n["state"] == state and n["native_token"] == token
    assert n["precision"] == "unknown" and n["float_hex"] is None
    if token == "-0.0":
        assert math.copysign(1, n["value"]) == -1


def test_partial_models_keep_expected_populations_and_positions(captures):
    payload = captures["models"]
    payload["effective"]["reactions"][1]["lower"]["value"] = True
    result = parse_model(payload, captures)
    assert [(r["position"], r["id"]) for r in result["effective"]["reactions"]] == [(0, "IN"), (2, "OUT")]
    assert result["effective"]["population"]["reactions"] == 3
    assert result["effective"]["population"]["completeness"] == "partial"
    assert result["loaded_original"]["population"]["completeness"] == "complete"
    assert "partial_population" in codes(result)


def test_partial_problem_keeps_auxiliary_rows_and_marks_lost_terms(captures):
    payload = captures["problems"]
    payload["effective"]["variables"][2]["lower"]["value"] = True
    payload["effective"]["constraints"][0]["terms"][0]["coefficient"]["float_hex"] = "0x1.0p+4"
    result = parse_problem(payload, captures)
    assert result["effective"]["representation"] == "partial"
    assert [r["position"] for r in result["effective"]["variables"]] == [0, 1, 3, 4, 5, 6]
    assert result["effective"]["variable_count"] == 7
    assert result["effective"]["constraints"][0]["terms_complete"] is False
    assert result["effective"]["constraints"][4]["id"] == "aux_link"


def test_duplicate_terms_are_not_summed(captures):
    payload = captures["problems"]
    row = payload["effective"]["constraints"][3]
    row["terms"].append(deepcopy(row["terms"][0]))
    result = parse_problem(payload, captures)
    retained = result["effective"]["constraints"][3]
    assert retained["terms_complete"] is False
    assert [r["variable_position"] for r in retained["terms"]] == [0]


def test_duplicate_native_solution_is_ambiguity_not_missing(captures):
    payload = captures["solution"]
    payload["reaction_values"].append(deepcopy(payload["reaction_values"][1]))
    result = parse_solution(payload, captures)
    assert len(result["native"]["reaction_values"]) == 4
    assert "duplicate_reaction_id" in codes(result)


def test_bad_native_value_preserves_other_values_and_exact_zero_sign(captures):
    payload = captures["solution"]
    payload["variable_values"][1]["primal"] = number(-0.0, "/variable_values/1/primal/value", "solution")
    payload["variable_values"][2]["primal"]["float_hex"] = "0x1.0p+1"
    result = parse_solution(payload, captures)
    assert [r["variable_position"] for r in result["native"]["variable_values"]] == [0, 1, 3, 4, 5, 6]
    assert result["native"]["variable_values"][1]["primal"]["float_hex"] == "-0x0.0p+0"


@pytest.mark.parametrize("parser,role", [(parse_cobra_glpk_model_capture, "effective_model"), (parse_cobra_glpk_problem_capture, "effective_problem"), (parse_cobra_glpk_solution_capture, "solution"), (parse_biomni_fba_csv, "flux_csv")])
def test_byte_identity_is_checked_before_decoding(captures, parser, role):
    kwargs = {"source": captures["files"][role]}
    if role == "effective_model": kwargs["original_model"] = captures["files"]["original_model"]
    if role == "effective_problem": kwargs["models"] = parsed(captures)[0]
    if role == "solution": kwargs["problem"] = parsed(captures)[1]["effective"]
    if role == "flux_csv": kwargs["model"] = None
    result = parser(captures["raw"][role] + b"changed", **kwargs)
    assert "artifact_identity_conflict" in codes(result)
    assert result.get("effective") is None and result.get("native") is None and not result.get("rows")


def bundle(c):
    payloads = {role: {"file": None, "bytes": None, "state": "absent"} for role in ROLES}
    for role, raw in c["raw"].items():
        payloads[role] = {"file": c["files"][role], "bytes": raw, "state": "present"}
    pin = {"path": "/explicit-test/python", "sha256": "1" * 64, "size_bytes": 1}
    software = {"version": "fba_software_v1", "python": pin, "python_version": "3.12",
        "python_home": "/explicit-test", "module_root": "/explicit-test/modules", "dependency_roots": ["/explicit-test/dependencies"],
        "implementation_files": [], "runtime_files": [], "solver_runtime_files": [],
        "distributions": [{"name": key, "version": value} for key, value in read("configuration.json")["distributions"].items()],
        "solver_interface": "optlang.glpk_interface"}
    model = c["files"]["original_model"]
    job = {"version": "native_flux_balance_job_v1", "operation": "perform_flux_balance_analysis",
        "mode": "steady_state_linear_fba", "source_alias": "biomni.tool.systems_biology.perform_flux_balance_analysis",
        "model_input": {"file": {"path": "/explicit-test/original.xml", "sha256": model["sha256"], "size_bytes": model["size_bytes"]},
            "artifact_ref": model["artifact_ref"], "format": "sbml", "original_loader_selection": "sbml_file",
            "repository_identifier": None, "acquisition_receipt_file": None}, "constraints": None,
        "objective": {"kind": "model_default", "reaction_id": None},
        "solver_options": {"feasibility_tolerance": None, "integrality_tolerance": None, "optimality_tolerance": None},
        "software": software, "output_prefix": "fba", "flux_output_name": "flux.csv", "source_function_sha256": "2" * 64}
    request = {"argv": ["/explicit-test/python", "driver.py"], "environment": {}, "native_flux_balance": job}
    attempt = {"run_id": "test680", "episode_id": "episode680", "resource_id": "local680", "execution_id": "/explicit-test/run",
        "attempt_id": "attempt680", "operation_key": "fba680", "requested_job_sha256": digest(request), "assignment_sha256": "3" * 64}
    selected = {"version": "flux_balance_selected_request_v1", "attempt": attempt, "requested_job": request}
    raw = encode(selected)
    payloads["selected_request"] = {"file": file(raw, selected["version"]), "bytes": raw, "state": "present"}
    solver = {"interface": "optlang.glpk_interface", "name": "GLPK", "version": "5.0", "cobra_version": "0.32.1", "optlang_version": "1.9.1",
        "raw_status": "optimal", "status": "optimal", "feasibility_tolerance": number(1e-7, "/actual_solver/feasibility_tolerance/value", "manifest"),
        "integrality_tolerance": number(1e-7, "/actual_solver/integrality_tolerance/value", "manifest"), "optimality_tolerance": missing(),
        "raw_parameters_file": None, "diagnostic_file": None, "alternate_optimum_claim": "not_assessed", "alternate_claim_source": None}
    manifest = {"version": "flux_balance_native_manifest_v1", "sealed": True, "attempt": attempt,
        "software_sha256": digest(software), "model_identity": {key: model[key] for key in ("sha256", "size_bytes")},
        "actual_distributions": software["distributions"], "actual_solver": solver, "source_function_sha256": job["source_function_sha256"],
        "effective_problem_sha256": c["files"]["effective_problem"]["sha256"],
        "files": [{"role": role, "relative_path": role, "format": row["file"]["format"], "state": "present",
                   "identity": {key: row["file"][key] for key in ("sha256", "size_bytes")}} for role, row in payloads.items() if role != "manifest"],
        "solve_call_count": 1, "execution_outcome": "completed", "request_realization": "exact", "issues": []}
    raw = encode(manifest)
    payloads["manifest"] = {"file": file(raw, manifest["version"]), "bytes": raw, "state": "present"}
    return payloads, attempt


def replace_role(payloads, role, value):
    raw = encode(value)
    payloads[role] = {"file": file(raw, payloads[role]["file"]["format"]), "bytes": raw, "state": "present"}


def test_normalized_complete_bundle_does_not_copy_solution_into_legacy_objective(captures):
    payloads, expected = bundle(captures)
    result = parse_fba_capture(payloads, expected=expected)
    assert result["issues"] == []
    assert result["native"]["solve_call_count"] == 1
    assert result["native"]["request_realization"] == "exact"
    assert result["native"]["objective"]["state"] == "missing"
    assert result["native_solution"]["native"]["native_cobra_objective"]["value"] == -2.75
    assert len(result["retained_files"]) == 8


@pytest.mark.parametrize("change", ["attempt", "software", "source", "model", "role", "solver", "distribution", "unsealed", "problem_hash"])
def test_manifest_identity_conflicts_preserve_independent_csv(captures, change):
    payloads, expected = bundle(captures)
    manifest = json.loads(payloads["manifest"]["bytes"])
    if change == "attempt": manifest["attempt"]["attempt_id"] = "different"
    if change == "software": manifest["software_sha256"] = "8" * 64
    if change == "source": manifest["source_function_sha256"] = "8" * 64
    if change == "model": manifest["model_identity"]["sha256"] = "8" * 64
    if change == "role": manifest["files"][0]["role"] = "flux_csv"
    if change == "solver": manifest["actual_solver"]["interface"] = "other.interface"
    if change == "distribution": manifest["actual_distributions"][0]["version"] = "wrong"
    if change == "unsealed": manifest["sealed"] = False
    if change == "problem_hash": manifest["effective_problem_sha256"] = "8" * 64
    replace_role(payloads, "manifest", manifest)
    result = parse_fba_capture(payloads, expected=expected)
    assert codes(result) & {"artifact_identity_conflict", "model_identity_conflict", "writer_not_closed"}
    assert result["native"]["request_realization"] == "unknown"
    assert [row["flux"]["value"] for row in result["native"]["flux_rows"]] == [7, 6, 6]


def test_legacy_csv_only_keeps_unknown_solve_count_request_and_problem(captures):
    payloads, expected = bundle(captures)
    for role in ROLES:
        if role != "flux_csv": payloads[role] = {"file": None, "bytes": None, "state": "absent"}
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native"]["solve_call_count"] is None
    assert result["native"]["execution_outcome"] == "unknown"
    assert result["original_request_file"] is None
    assert result["native"]["objective_request"] is None
    assert result["native"]["constraint_changes"] is None
    assert result["problems"]["effective"] is None
    assert len(result["native"]["flux_rows"]) == 3


def test_truncated_csv_and_missing_model_do_not_fabricate_full_data(captures):
    payloads, expected = bundle(captures)
    raw = captures["raw"]["flux_csv"].split(b"OUT,")[0] + b"OUT,fixture"
    payloads["flux_csv"] = {"file": file(raw, "biomni_fba_csv_v1"), "bytes": raw, "state": "truncated"}
    for role in ("manifest", "effective_model", "original_model", "effective_problem", "solution"):
        payloads[role] = {"file": None, "bytes": None, "state": "absent"}
    result = parse_fba_capture(payloads, expected=expected)
    assert "artifact_truncated" in codes(result)
    assert [row["reaction_id"] for row in result["native"]["flux_rows"]] == ["IN", "AB"]
    assert all(row["reaction_position"] is None for row in result["native"]["flux_rows"])


def test_foreign_source_reference_is_not_rebound_as_local_data(captures):
    payload = captures["solution"]
    payload["variable_values"][1]["primal"]["source"] = {"role": "unbound", "pointer": "/value"}
    result = parse_solution(payload, captures)
    assert [row["variable_position"] for row in result["native"]["variable_values"]] == [0, 2, 3, 4, 5, 6]
    assert "artifact_missing" in codes(result)


def test_duplicate_json_keys_and_truncated_json_are_not_valid_snapshots(captures):
    for raw in (b'{"version": 1,"version": 2}', captures["raw"]["effective_model"][:-4]):
        result = parse_cobra_glpk_model_capture(raw, source=file(raw, "cobra_model_capture_v1"), original_model=captures["files"]["original_model"])
        assert result["effective"] is None
        assert "schema_invalid" in codes(result)


def test_pure_readers_need_no_file_access_scientific_import_or_solver(captures, monkeypatch):
    payloads, expected = bundle(captures)
    def forbidden(*args, **kwargs):
        raise AssertionError("Reader performed file or scientific access")
    original_import = builtins.__import__
    def importing(name, *args, **kwargs):
        if name.split(".")[0] in {"cobra", "optlang", "swiglpk", "numpy", "pandas", "sympy", "libsbml"}: forbidden()
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(builtins, "__import__", importing)
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native_solution"]["native"]["variable_values"][-1]["primal"]["value"] == 6


def test_source_locations_after_prior_malformed_solution_rows_keep_original_indices(captures):
    payload = captures["solution"]
    payload["reaction_values"][0]["flux"]["value"] = True
    payload["reaction_values"][2]["reaction_id"] = "wrong"
    result = parse_solution(payload, captures)
    assert [row["reaction_position"] for row in result["native"]["reaction_values"]] == [1]
    assert any(i["reaction_position"] == 0 and i["field"].startswith("/reaction_values/0") for i in result["issues"])
    assert any(i["reaction_position"] == 2 and i["field"] == "/reaction_values/2" for i in result["issues"])


def test_unestablished_native_getter_values_are_not_a_candidate(captures):
    payload = captures["solution"]
    payload["point_state"] = "not_established"
    result = parse_solution(payload, captures)
    assert result["native"]["point_state"] == "not_established"
    assert result["native"]["variable_values"] == result["native"]["reaction_values"] == []
    assert result["native"]["optlang_status"] == "optimal"
    assert "primal_not_established" in codes(result)


def test_source_join_conflict_retains_other_model_data(captures):
    payload = captures["models"]
    payload["source_to_loaded_ids"] = [{"kind": "reaction", "source_record_index": 0, "source_id": "R_IN",
        "loaded_id": "WRONG", "loaded_position": 0, "state": "mapped", "source": location("original_model", "")}]
    result = parse_model(payload, captures)
    assert result["source_to_loaded_ids"] == []
    assert len(result["effective"]["reactions"]) == 3
    assert "model_identity_conflict" in codes(result)


def test_declared_complete_population_with_hole_is_qualified(captures):
    payload = captures["models"]
    del payload["effective"]["reactions"][1]
    result = parse_model(payload, captures)
    assert result["effective"]["population"]["reactions"] == 3
    assert result["effective"]["population"]["completeness"] == "partial"
    assert [row["position"] for row in result["effective"]["reactions"]] == [0, 2]


def test_mismatched_present_variable_join_does_not_erase_independent_problem(captures):
    payload = captures["problems"]
    payload["effective"]["reaction_variables"][1]["forward_variable_id"] = "WRONG"
    result = parse_problem(payload, captures)
    assert result["effective"]["representation"] == "partial"
    assert len(result["effective"]["variables"]) == 7
    assert [row["reaction_position"] for row in result["effective"]["reaction_variables"]] == [0, 2]


def test_selected_request_digest_and_model_pin_checked_without_manifest(captures):
    payloads, expected = bundle(captures)
    request = json.loads(payloads["selected_request"]["bytes"])
    request["requested_job"]["native_flux_balance"]["model_input"]["file"]["sha256"] = "7" * 64
    expected["requested_job_sha256"] = digest(request["requested_job"])
    request["attempt"] = expected
    replace_role(payloads, "selected_request", request)
    payloads["manifest"] = {"file": None, "bytes": None, "state": "absent"}
    result = parse_fba_capture(payloads, expected=expected)
    assert "model_identity_conflict" in codes(result)
    assert result["original_request_file"] is None
    assert len(result["native"]["flux_rows"]) == 3


def test_captured_software_version_conflict_cannot_keep_exact_realization(captures):
    c = deepcopy(captures)
    c["solution"]["configuration_after_solve"]["cobra_version"] = "other"
    c["raw"]["solution"] = encode(c["solution"])
    c["files"]["solution"] = file(c["raw"]["solution"], "cobra_glpk_solution_capture_v1")
    payloads, expected = bundle(c)
    result = parse_fba_capture(payloads, expected=expected)
    assert "artifact_identity_conflict" in codes(result)
    assert result["native"]["request_realization"] == "mismatch"
    assert result["native_solution"]["native"]["configuration_after_solve"]["cobra_version"] == "other"


@pytest.mark.parametrize("format", ["biomni_fba_log_v1", "utf8_text"])
def test_only_declared_legacy_log_grammar_populates_rounded_objective(captures, format):
    payloads, expected = bundle(captures)
    raw = b"# Flux Balance Analysis (FBA) Research Log\n\n## Step 4: Solving FBA optimization problem\n- Optimization status: optimal\n- Objective value: -2.750000\n\n## Step 5: Analyzing flux distribution\n- Number of active reactions (flux > 1e-6): 3\n"
    payloads["native_log"] = {"file": file(raw, format), "bytes": raw, "state": "present"}
    payloads["manifest"] = {"file": None, "bytes": None, "state": "absent"}
    result = parse_fba_capture(payloads, expected=expected)
    objective = result["native"]["objective"]
    if format == "utf8_text":
        assert objective["state"] == "missing"
    else:
        assert objective["value"] == -2.75 and objective["native_token"] == "-2.750000"
        assert objective["precision"] == "formatted_6dp"
        assert result["native"]["source_active_count"] == 3


def test_role_addressed_request_hashes_original_bytes_before_retained_binding(captures):
    payloads, expected = bundle(captures)
    request = json.loads(payloads["selected_request"]["bytes"])
    request["requested_job"]["native_flux_balance"]["constraints"] = [{"reaction_id": "IN",
        "lower": bound(-10.0, "/requested_job/native_flux_balance/constraints/0/lower/value", "selected_request"),
        "upper": bound(8.0, "/requested_job/native_flux_balance/constraints/0/upper/value", "selected_request")}]
    expected["requested_job_sha256"] = digest(request["requested_job"])
    request["attempt"] = expected
    original = deepcopy(request)
    replace_role(payloads, "selected_request", request)
    manifest = json.loads(payloads["manifest"]["bytes"])
    manifest["attempt"] = expected
    for row in manifest["files"]:
        if row["role"] == "selected_request":
            row["identity"] = {key: payloads["selected_request"]["file"][key] for key in ("sha256", "size_bytes")}
    replace_role(payloads, "manifest", manifest)
    result = parse_fba_capture(payloads, expected=expected)
    assert result["issues"] == []
    assert result["native"]["request_realization"] == "exact"
    assert result["native"]["constraint_changes"][0]["requested_lower"]["source"] == {
        "file": payloads["selected_request"]["file"], "pointer": "/requested_job/native_flux_balance/constraints/0/lower/value"}
    assert json.loads(payloads["selected_request"]["bytes"]) == original


@pytest.mark.parametrize("change", ["raw_job", "expected_digest"])
def test_selected_request_tampering_does_not_certify_request(captures, change):
    payloads, expected = bundle(captures)
    if change == "raw_job":
        request = json.loads(payloads["selected_request"]["bytes"])
        request["requested_job"]["native_flux_balance"]["output_prefix"] = "tampered"
        replace_role(payloads, "selected_request", request)
    else:
        expected["requested_job_sha256"] = "6" * 64
    result = parse_fba_capture(payloads, expected=expected)
    assert result["original_request_file"] is None
    assert result["native"]["objective_request"] is None
    assert "artifact_identity_conflict" in codes(result)
    assert len(result["native"]["flux_rows"]) == 3


def test_bad_model_cross_references_preserve_other_native_rows(captures):
    c = deepcopy(captures)
    c["problems"]["effective"]["reaction_variables"][1]["reaction_position"] = 9
    c["problems"]["effective"]["constraints"][0]["metabolite_position"] = 9
    c["solution"]["reaction_values"][1]["reaction_position"] = 9
    for role, key, format in (("effective_problem", "problems", "cobra_glpk_problem_capture_v1"), ("solution", "solution", "cobra_glpk_solution_capture_v1")):
        c["raw"][role] = encode(c[key])
        c["files"][role] = file(c["raw"][role], format)
    payloads, expected = bundle(c)
    result = parse_fba_capture(payloads, expected=expected)
    assert result["problems"]["effective"]["representation"] == "partial"
    assert len(result["problems"]["effective"]["variables"]) == 7
    assert [row["constraint_position"] for row in result["native_solution"]["native"]["constraint_values"]] == [0, 1, 2, 3, 4]
    assert [row["reaction_position"] for row in result["native_solution"]["native"]["reaction_values"]] == [0, 2]


def test_duplicate_stoichiometry_preserves_remaining_model_populations(captures):
    payload = captures["models"]
    payload["effective"]["stoichiometry"].append(deepcopy(payload["effective"]["stoichiometry"][0]))
    result = parse_model(payload, captures)
    assert result["effective"]["population"]["completeness"] == "partial"
    assert len(result["effective"]["reactions"]) == 3
    assert [(r["metabolite_position"], r["reaction_position"]) for r in result["effective"]["stoichiometry"]] == [(0, 1), (1, 1), (1, 2)]


def test_json_source_pointer_must_resolve_in_supplied_capture(captures):
    payload = captures["models"]
    payload["effective"]["reactions"][1]["lower"]["source"]["pointer"] = "/absent"
    result = parse_model(payload, captures)
    assert [row["position"] for row in result["effective"]["reactions"]] == [0, 2]
    assert "schema_invalid" in codes(result)


def test_json_pointer_escaping_preserves_exact_native_key(captures):
    payload = captures["models"]
    payload["effective"]["annotations"]["a/b~"] = 0
    payload["effective"]["metabolites"][0]["charge"]["source"]["pointer"] = "/effective/annotations/a~1b~0"
    result = parse_model(payload, captures)
    assert result["issues"] == []
    assert result["effective"]["metabolites"][0]["charge"]["source"]["pointer"] == "/effective/annotations/a~1b~0"


def test_bundle_can_resolve_a_pointer_into_another_supplied_json_role(captures):
    c = deepcopy(captures)
    c["solution"]["variable_values"][0]["primal"]["source"] = location("effective_problem", "/not-present")
    c["raw"]["solution"] = encode(c["solution"])
    c["files"]["solution"] = file(c["raw"]["solution"], "cobra_glpk_solution_capture_v1")
    payloads, expected = bundle(c)
    result = parse_fba_capture(payloads, expected=expected)
    assert [row["variable_position"] for row in result["native_solution"]["native"]["variable_values"]] == [1, 2, 3, 4, 5, 6]
    assert any(issue["variable_position"] == 0 for issue in result["native_solution"]["issues"])
