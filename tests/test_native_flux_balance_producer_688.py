"""Bounded producer verification; new solves require explicit selection.

Synthetic status/fault fixtures test custody, not native nonoptimal science.
Retained677 observations are reused without repeating that optimization.
"""
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

import pytest

from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.native_flux_balance_contracts import (
    ATTEMPT_DIRECTORY_NAME, DRIVER_MODULE, POLICY, RUN_PLAN_FILENAME, SOURCE_FUNCTION_SHA256,
    flux_balance_driver_argv, flux_balance_environment, flux_balance_output_files,
    validate_flux_balance_run_plan,
)
from gene_annotation_episode.native_flux_balance_storage import (
    decode_json, file_pin, immutable_bytes, immutable_json, read_json, retain_input,
)
from gene_annotation_episode import native_flux_balance_cobra_glpk as native

ATTEMPT = Path(os.environ["HMMER529_ATTEMPT"]) if "HMMER529_ATTEMPT" in os.environ else None
pytestmark = pytest.mark.skipif(ATTEMPT is None, reason="application/native work requires bounded529")

SBML = b'''<?xml version="1.0" encoding="UTF-8"?>
<sbml xmlns="http://www.sbml.org/sbml/level3/version1/core" xmlns:fbc="http://www.sbml.org/sbml/level3/version1/fbc/version2" level="3" version="1" fbc:required="false">
 <model id="producer688" name="explicit tiny pathway" fbc:strict="true">
  <listOfCompartments><compartment id="c" name="cytosol" constant="true"/><compartment id="unused" name="unused" constant="true"/></listOfCompartments>
  <listOfSpecies><species id="M_A" name="A" compartment="c" hasOnlySubstanceUnits="false" boundaryCondition="false" constant="false"/><species id="M_B" name="B" compartment="c" hasOnlySubstanceUnits="false" boundaryCondition="false" constant="false"/></listOfSpecies>
  <listOfParameters><parameter id="zero" value="0" constant="true"/><parameter id="ten" value="10" constant="true"/><parameter id="large" value="1000" constant="true"/></listOfParameters>
  <fbc:listOfGeneProducts><fbc:geneProduct fbc:id="G_g1" fbc:label="g1" fbc:name="gene one"/><fbc:geneProduct fbc:id="G_g2" fbc:label="g2"/></fbc:listOfGeneProducts>
  <listOfReactions>
   <reaction id="R_IN" name="input" reversible="false" fast="false" fbc:lowerFluxBound="zero" fbc:upperFluxBound="ten"><listOfProducts><speciesReference species="M_A" stoichiometry="1" constant="true"/></listOfProducts></reaction>
   <reaction id="R_AB" name="conversion" reversible="false" fast="false" fbc:lowerFluxBound="zero" fbc:upperFluxBound="large"><listOfReactants><speciesReference species="M_A" stoichiometry="1" constant="true"/></listOfReactants><listOfProducts><speciesReference species="M_B" stoichiometry="1" constant="true"/></listOfProducts><fbc:geneProductAssociation><fbc:or><fbc:geneProductRef fbc:geneProduct="G_g1"/><fbc:geneProductRef fbc:geneProduct="G_g2"/></fbc:or></fbc:geneProductAssociation></reaction>
   <reaction id="R_OUT" name="output" reversible="false" fast="false" fbc:lowerFluxBound="zero" fbc:upperFluxBound="large"><listOfReactants><speciesReference species="M_B" stoichiometry="1" constant="true"/></listOfReactants></reaction>
  </listOfReactions>
  <fbc:listOfObjectives fbc:activeObjective="obj"><fbc:objective fbc:id="obj" fbc:type="maximize"><fbc:listOfFluxObjectives><fbc:fluxObjective fbc:reaction="R_OUT" fbc:coefficient="1"/></fbc:listOfFluxObjectives></fbc:objective></fbc:listOfObjectives>
 </model>
</sbml>\n'''


def _json_model():
    return {"id": "producer688_json", "name": "explicit tiny pathway", "version": "1", "compartments": {"c": "cytosol", "unused": "unused"},
        "metabolites": [{"id": identifier, "name": identifier, "compartment": "c"} for identifier in ("A", "B")],
        "genes": [{"id": "g1", "name": "gene one"}, {"id": "g2", "name": ""}],
        "reactions": [{"id": "IN", "name": "input", "metabolites": {"A": 1}, "lower_bound": 0, "upper_bound": 10, "gene_reaction_rule": "", "objective_coefficient": 0},
            {"id": "AB", "name": "conversion", "metabolites": {"A": -1, "B": 1}, "lower_bound": 0, "upper_bound": 1000, "gene_reaction_rule": "g1 or g2", "objective_coefficient": 0},
            {"id": "OUT", "name": "output", "metabolites": {"B": -1}, "lower_bound": 0, "upper_bound": 1000, "gene_reaction_rule": "", "objective_coefficient": 1}]}


def _software():
    source = read_json(ATTEMPT / "source_pins_before.json")
    runtime = read_json(ATTEMPT / "stdlib_pins_before.json") + read_json(ATTEMPT / "dependency_pins_before.json")
    binary = read_json(ATTEMPT / "binary_pins_before.json")
    python = next(r for r in binary if r["path"] == sys.executable)
    runtime += [r for r in binary if r != python]
    known = {r["path"] for r in [python, *source, *runtime]}
    native_files = [r for r in read_json(ATTEMPT / "native_library_pins_before.json") if r["path"] not in known]
    distributions = [{"name": row.metadata["Name"], "version": row.version} for row in importlib.metadata.distributions(path=[str(ATTEMPT / "dependencies")])]
    return {"version": "fba_software_v1", "python": python, "python_version": sys.version, "python_home": str(ATTEMPT / "runtime"),
        "module_root": str(ATTEMPT / "source_snapshot"), "dependency_roots": [str(ATTEMPT / "dependencies")],
        "implementation_files": source, "runtime_files": runtime, "solver_runtime_files": native_files,
        "distributions": distributions, "solver_interface": "optlang.glpk_interface"}


def _selected_bound(value):
    return native.bound(value, role="selected_request", pointer="") | {"source": None}


def _plan(directory, profile, raw, *, changes=None, objective=None, options=None, software=None, operation_key=None):
    directory.mkdir(parents=True, exist_ok=True)
    input_path = directory / ("input.xml" if profile == "sbml" else "input.json")
    immutable_bytes(input_path, raw)
    software = software or _software()
    key = operation_key or "selected-" + profile
    owner = {"run_id": "producer688", "episode_id": "selected-local", "resource_id": "local-bounded529", "operation_key": key}
    lifecycle = directory / ".episode-operations" / digest({"run": owner["run_id"], "episode": owner["episode_id"]}) / digest(key)
    attempt = lifecycle / ATTEMPT_DIRECTORY_NAME
    request = {"argv": [software["python"]["path"], "-B", "-S", "-m", DRIVER_MODULE, RUN_PLAN_FILENAME],
        "environment": flux_balance_environment(software, attempt_directory=str(attempt), lifecycle_directory=str(lifecycle)),
        "native_flux_balance": {"version": "native_flux_balance_job_v1", "operation": "perform_flux_balance_analysis", "mode": "steady_state_linear_fba",
            "source_alias": "biomni.tool.systems_biology.perform_flux_balance_analysis",
            "source_function_sha256": SOURCE_FUNCTION_SHA256, "model_input": {"file": file_pin(input_path), "artifact_ref": None,
                "format": profile, "original_loader_selection": "sbml_file" if profile == "sbml" else "json_file", "repository_identifier": None, "acquisition_receipt_file": None},
            "constraints": changes, "objective": objective or {"kind": "model_default", "reaction_id": None},
            "solver_options": options or {"feasibility_tolerance": None, "optimality_tolerance": None, "integrality_tolerance": None},
            "software": software, "output_prefix": "outputs", "flux_output_name": "flux.csv"}}
    owner.update(execution_id=str(lifecycle / "native.json"), attempt_id=digest(key), requested_job_sha256=digest(request), assignment_sha256=digest({"fixture": profile}))
    return validate_flux_balance_run_plan({"version": "flux_balance_run_plan_v1", "identity": owner, "requested_job": request,
        "attempt_directory": str(attempt), "policy": POLICY, "outputs": flux_balance_output_files(request["native_flux_balance"])})


def _environment(monkeypatch, plan):
    for k, v in plan["requested_job"]["environment"].items():
        monkeypatch.setenv(k, v)


def _bundle(plan):
    root = Path(plan["attempt_directory"])
    manifest = read_json(root / "outputs/native-manifest.json")
    states = {r["role"]: r["state"] for r in manifest["files"]} | {"manifest": "present"}
    payloads = {}
    for row in plan["outputs"]:
        path = root / row["relative_path"]
        if path.is_file():
            pin = file_pin(path)
            file = {"artifact_ref": "fixture-artifact-" + row["role"] + "-" + pin["sha256"], "sha256": pin["sha256"],
                    "size_bytes": pin["size_bytes"], "format": row["format"]}
            payloads[row["role"]] = {"file": file, "bytes": path.read_bytes(), "state": states[row["role"]]}
        else:
            payloads[row["role"]] = {"file": None, "bytes": None, "state": states[row["role"]]}
    return payloads


def _parameters(sheet):
    unit = native.unknown_unit()
    def tolerances(ids):
        return [{"subject_id": identifier, "value": 1e-8, "unit": unit} for identifier in ids]
    reactions = [r["id"] for r in sheet["models"]["effective"]["reactions"]]
    problem = sheet["problems"]["effective"]
    constraints = [r["id"] for r in problem["constraints"]]
    return {"version": "fba_calculation_parameters_v1", "reaction_bound_tolerances": tolerances(reactions),
        "constraint_tolerances": tolerances(constraints), "active_flux_thresholds": tolerances(reactions),
        "objective_absolute_tolerance": 1e-8, "variable_bound_tolerances": tolerances([r["id"] for r in problem["variables"]]),
        "reaction_flux_tolerances": tolerances(reactions), "constraint_activity_tolerances": tolerances(constraints)}


def _parsed_calculated(plan):
    from gene_annotation_episode.flux_balance_readers import parse_fba_capture
    from gene_annotation_episode.flux_balance_sheet import populate_flux_balance_sheet
    from gene_annotation_episode.flux_balance_calculations import calculate_flux_balance_sheet
    bundle = parse_fba_capture(_bundle(plan), expected=plan["identity"])
    sheet = populate_flux_balance_sheet(bundle=bundle)
    return sheet, calculate_flux_balance_sheet(sheet, parameters=_parameters(sheet))


def test_source_audit_normalized_xml_and_json():
    raw = b'<a xmlns="urn:root" xmlns:x="urn:x" x:q=""><x:b> left &amp; right </x:b> tail <x:b/><c xmlns="urn:other"/></a>'
    audit, document = native._source_audit(raw, "sbml")
    assert document is None
    elements = audit["xml_elements"]
    assert [r["source_record_index"] for r in elements] == [0, 1, 2, 3]
    assert elements[0]["namespace_declarations"] == [{"prefix": "", "uri": "urn:root"}, {"prefix": "x", "uri": "urn:x"}]
    assert elements[0]["attributes"][0] == {"name": {"namespace_uri": "urn:x", "local_name": "q"}, "value": ""}
    assert elements[1]["text"] == " left & right " and elements[1]["tail"] == " tail "
    assert elements[2]["text"] is None and elements[2]["path"][-1]["sibling_ordinal"] == 1
    assert elements[3]["namespace_declarations"] == [{"prefix": "", "uri": "urn:other"}]
    with pytest.raises(ValueError, match="doctype"):
        native._source_audit(b'<!DOCTYPE a [<!ENTITY x "value">]><a>&x;</a>', "sbml")
    audit, value = native._source_audit(canonical(_json_model()).encode(), "cobra_json")
    assert audit["xml_elements"] is None and value["id"] == "producer688_json"


@pytest.mark.parametrize("rc", range(13))
@pytest.mark.parametrize("primal", range(1, 7))
def test_exact_native_return_predicate_synthetic(rc, primal):
    assert native._established_return(rc, primal) == ((rc == 0 and primal in {2, 3, 4}) or (rc in {6, 7, 8, 9} and primal in {2, 3}))


def test_synthetic_status_contradictions_and_missing_dual():
    assert native._established_return(0, 4, 4, 2)
    assert native._established_return(0, 2, 5, None)
    assert not native._established_return(0, 2, 4, 2)
    assert not native._established_return(0, 2, 5, 3)
    assert not native._established_return(True, 2)
    assert not native._established_return(0, 3, 3, 99)
    assert not native._established_return(0, 2, 5, True)


def test_synthetic_control_capture_preserves_values_and_actual_exceptions():
    class Control:
        @property
        def valid(self):
            return 1e-7
        @property
        def callback(self):
            return object()
        @property
        def failed(self):
            raise OSError("controlled getter unavailable")
    failures = []
    controls = native._controls(Control(), failures, "synthetic_parameters")
    assert controls["valid"] == 1e-7
    assert controls["callback"] == {"state": "unavailable", "type": "builtins.object"}
    assert controls["failed"] == {"state": "unavailable", "type": None}
    assert [(r["operation"], r["exception_class"]) for r in failures] == [
        ("synthetic_parameters/callback", "TypeError"), ("synthetic_parameters/failed", "OSError")]
    assert all(row["traceback"].startswith("Traceback") for row in failures)


def _live_model(tmp_path):
    source = tmp_path / "source.xml"
    source.write_bytes(SBML)
    diagnostics = {"warnings": [], "logging": [], "exceptions": []}
    context = native._load_model(source, profile="sbml", raw=SBML, scratch_directory=tmp_path, diagnostics=diagnostics)
    model = native._load_audited_model(source, context)
    return model, context, diagnostics


def test_native_snapshot_full_variable_basis_without_solve(tmp_path, monkeypatch):
    model, context, _ = _live_model(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("snapshot-only case must never optimize")
    monkeypatch.setattr(type(model), "optimize", forbidden)
    model.reactions.IN.bounds = (-10, 8)
    model.constraints.A.ub = 1
    model.constraints.A.lb = 1
    interface = model.problem
    aux = interface.Variable("aux", lb=0)
    free = interface.Variable("free")
    upper_only = interface.Variable("upper_only", ub=4)
    fixed = interface.Variable("fixed", lb=-0.0, ub=-0.0)
    model.add_cons_vars([aux, free, upper_only, fixed,
        interface.Constraint(model.reactions.AB.flux_expression + model.reactions.OUT.flux_expression + 2, ub=14, name="net_cap"),
        interface.Constraint(model.reactions.IN.forward_variable + model.reactions.IN.reverse_variable, ub=9, name="split_cap"),
        interface.Constraint(aux - model.reactions.OUT.flux_expression, lb=0, ub=0, name="aux_link")])
    model.objective = interface.Objective(.25 * model.reactions.IN.flux_expression - model.reactions.OUT.flux_expression + 1.5, direction="min")
    model.solver.update()
    captured = native.capture_cobra_glpk_problem(model, phase="effective")
    assert captured["representation"] == "complete_continuous_linear"
    assert (captured["variable_count"], captured["constraint_count"]) == (10, 5)
    assert captured["objective"]["interface_offset"]["value"] == 1.5
    assert captured["objective"]["direction"] == "min"
    rows = {r["id"]: r for r in captured["constraints"]}
    assert rows["A"]["lower"]["value"] == rows["A"]["upper"]["value"] == 1
    assert rows["net_cap"]["upper"]["value"] == 12 and rows["net_cap"]["constant"]["value"] == 0
    assert len(rows["split_cap"]["terms"]) == 2
    variables = {r["id"]: r for r in captured["variables"]}
    assert variables["free"]["lower"]["kind"] == "negative_infinity" and variables["free"]["upper"]["kind"] == "positive_infinity"
    assert variables["upper_only"]["lower"]["kind"] == "negative_infinity"
    assert variables["aux"]["upper"]["kind"] == "positive_infinity"
    assert variables["fixed"]["lower"]["value"] == 0
    assert native.bound(-0.0, role="effective_problem", pointer="")["float_hex"] == "-0x0.0p+0"
    metadata = native.capture_cobra_glpk_model(model, phase="effective", source_audit=context["source_audit"])
    assert [r["id"] for r in metadata["compartments"]] == ["c", "unused"]
    assert metadata["reactions"][1]["gpr_native"] is None
    assert metadata["reactions"][1]["gpr_source_pointer"].startswith("/source_audit/xml_elements/")
    assert metadata["reactions"][1]["gpr_loaded"] == "g1 or g2"
    assert native._raw_point(model)["glpk_primal_status_code"] == 1


@pytest.mark.parametrize("value", [0, -0.0, 1, 2, -1, True, float("nan"), float("inf")])
def test_native_option_validation_without_setter_or_solve(tmp_path, value):
    model, _, diagnostics = _live_model(tmp_path)
    job = {"constraints": None, "objective": {"kind": "model_default", "reaction_id": None},
           "solver_options": {"feasibility_tolerance": value, "optimality_tolerance": None, "integrality_tolerance": None}}
    application = native._request_application(job)
    assert not native._apply_request(model, job, application, diagnostics)
    assert application["constraint_changes"] == []
    assert application["solver_option_applications"][0]["application"] == "rejected"
    assert model.solver.status is None


def test_source_semantics_defaults_and_ignored_fields_without_solve(tmp_path):
    model, context, diagnostics = _live_model(tmp_path)
    raw = SBML.replace(b' fbc:upperFluxBound="ten"', b'').replace(b'boundaryCondition="false"', b'boundaryCondition="true"', 1)
    audit, _ = native._source_audit(raw, "sbml")
    source = native._source_information(audit, None)
    assert source["missing_bounds"] == {"IN", "EX_A"}
    assert {r["kind"] for r in source["features"]} >= {"boundary_exchange_creation", "default_bound"}
    supplied = _json_model() | {"objective_direction": "min", "solver": "not-selected"}
    audit, doc = native._source_audit(canonical(supplied).encode(), "cobra_json")
    source = native._source_information(audit, doc)
    assert source["unsupported"] and sum(f["kind"] == "ignored_json_field" for f in source["features"]) == 2
    job = {"constraints": [], "objective": {"kind": "single_reaction", "reaction_id": "absent"},
        "solver_options": {"feasibility_tolerance": None, "optimality_tolerance": None, "integrality_tolerance": None}}
    application = native._request_application(job)
    assert not native._apply_request(model, job, application, diagnostics)
    assert application["objective_application"] == "rejected"


def test_explicit_json_zero_objective_is_supplied_without_solve(tmp_path, monkeypatch):
    import cobra
    def forbidden(*args, **kwargs):
        raise AssertionError("source/objective inspection must not optimize")
    monkeypatch.setattr(cobra.Model, "optimize", forbidden)
    document = _json_model()
    for reaction in document["reactions"]:
        reaction["objective_coefficient"] = 0
    raw = canonical(document).encode()
    path = tmp_path / "explicit-zero.json"
    path.write_bytes(raw)
    diagnostics = {"warnings": [], "logging": [], "exceptions": []}
    context = native._load_model(path, profile="cobra_json", raw=raw, scratch_directory=tmp_path, diagnostics=diagnostics)
    model = native._load_audited_model(path, context)
    assert not context["source_information"]["missing_objective"]
    job = {"constraints": None, "objective": {"kind": "model_default", "reaction_id": None},
        "solver_options": {"feasibility_tolerance": None, "optimality_tolerance": None, "integrality_tolerance": None}}
    application = native._request_application(job)
    assert native._apply_request(model, job, application, diagnostics)
    model.solver.update()
    snapshot = native.capture_cobra_glpk_problem(model, phase="effective")
    assert snapshot["objective"]["terms"] == [] and snapshot["objective"]["terms_complete"]
    assert snapshot["objective"]["native_constant"]["value"] == snapshot["objective"]["interface_offset"]["value"] == 0
    assert model.solver.status is None
    for reaction in document["reactions"]:
        del reaction["objective_coefficient"]
    audit, supplied = native._source_audit(canonical(document).encode(), "cobra_json")
    assert native._source_information(audit, supplied)["missing_objective"]


def test_storage_immutable_confined_and_changed_identity(tmp_path):
    source, output = tmp_path / "source", tmp_path / "retained"
    source.write_bytes(b"complete native bytes")
    expected = retain_input(source, output, max_bytes=1024)
    assert expected["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        immutable_bytes(output, b"replacement")
    alias = tmp_path / "alias"
    alias.symlink_to(source)
    with pytest.raises(OSError):
        file_pin(alias)
    with pytest.raises(ValueError, match="duplicate_json"):
        decode_json(b'{"a":1,"a":2}')


def test_retained677_native_point_no_new_solve():
    packet = ATTEMPT / "source_snapshot/verification/tool_graders_flux_balance_native_contract_2026-10-29_677/probe"
    summary = read_json(packet / "probe_summary.json")
    assert summary["model_optimize_calls"] == 1
    assert summary["fluxes"] == {"IN": 7.0, "AB": 6.0, "OUT": 6.0}
    assert summary["aux_primal"] == 6 and summary["objective"] == -2.75
    assert read_json(packet / "native_passes.json")[0]["return_code"] == 0


def test_synthetic_pass_chronology_and_per_value_qualification(tmp_path, monkeypatch):
    model, _, diagnostics = _live_model(tmp_path)
    raw = native._raw_point(model)
    raw.update(glpk_status_code=5, glpk_primal_status_code=2, glpk_dual_status_code=2)
    event = {"typed": {"position": 0, "routine": "glp_simplex", "return_code": 0, "raw_status_code": 5,
        "primal_status_code": 2, "dual_status_code": 2, "parameters_pointer": "/native_capture_evidence/native_passes/0/parameters", "exception_pointer": None},
        "evidence": {"parameters": {}, "exception": None, "effective_problem_sha256": "a" * 64,
            "raw_status_after": {"entered": True, "returned": True, "same_original_problem": True,
                "problem_identity_before": raw["problem_identity"], "original_problem_identity": raw["problem_identity"]},
            "raw_getters": deepcopy(raw)}}
    final = deepcopy(raw)
    final["variables"][0]["primal"] = native.observation(float("nan"))
    final["variables"][1]["primal"] = native.observation(None)
    monkeypatch.setattr(native, "_raw_point", lambda _: deepcopy(final))
    point = native.capture_cobra_glpk_solution(model, None, optimize_call_count=1, native_passes=[event], diagnostics=diagnostics)
    assert point["point_state"] == "basic_solution"
    assert [r["primal"]["state"] for r in point["variable_values"]][:3] == ["nonfinite", "missing", "present"]
    assert point["native_cobra_objective"]["state"] == "missing"
    assert point["solution_object_state"] == "not_returned"
    final["variables"][0]["id"] = None
    final["constraints"][0]["id"] = None
    point = native.capture_cobra_glpk_solution(model, None, optimize_call_count=1, native_passes=[event], diagnostics=diagnostics)
    assert point["point_state"] == "basic_solution"
    assert len(point["variable_values"]) == 5 and len(point["constraint_values"]) == 1
    assert point["variable_values"][0]["variable_position"] == 1
    assert point["variable_values"][1]["primal"]["state"] == "present"
    assert point["variable_values"][1]["primal"]["source"]["pointer"] == "/variable_values/1/primal/value"
    assert {r["code"] for r in point["issues"]} >= {"variable_identity_conflict", "constraint_identity_conflict"}
    final = deepcopy(raw)
    later = deepcopy(event)
    later["typed"].update(position=1, return_code=10, raw_status_code=1, primal_status_code=1, dual_status_code=1)
    later["evidence"]["raw_getters"].update(glpk_status_code=1, glpk_primal_status_code=1, glpk_dual_status_code=1)
    final.update(glpk_status_code=1, glpk_primal_status_code=1, glpk_dual_status_code=1)
    point = native.capture_cobra_glpk_solution(model, None, optimize_call_count=1, native_passes=[event, later], diagnostics=diagnostics)
    assert point["point_state"] == "not_established"
    assert all(r["primal"]["state"] == "missing" for r in point["variable_values"])
    assert point["native_capture_evidence"]["native_passes"][0]["raw_getters"] == raw
    assert "raw_original_problem_after" not in point["native_capture_evidence"]["native_passes"][0]


def test_selected_no_solve_failures_and_source_retention(tmp_path, monkeypatch):
    from gene_annotation_episode.native_flux_balance_driver import run_flux_balance_native
    import cobra
    def forbidden(*args, **kwargs):
        raise AssertionError("pre-solve rejection must not call optimize")
    monkeypatch.setattr(cobra.Model, "optimize", forbidden)
    software = _software()
    for case in ("unsupported_option", "unknown_reaction", "bad_pin", "load_failure"):
        raw = b'<sbml xmlns="http://www.sbml.org/sbml/level3/version1/core" level="3" version="1"/>' if case == "load_failure" else SBML
        options = {"feasibility_tolerance": None, "optimality_tolerance": 1e-7 if case == "unsupported_option" else None, "integrality_tolerance": None}
        changes = [{"reaction_id": "unknown", "lower": _selected_bound(0), "upper": _selected_bound(10)}] if case == "unknown_reaction" else None
        plan = _plan(tmp_path / case, "sbml", raw, options=options, changes=changes, software=software)
        if case == "bad_pin":
            plan["requested_job"]["native_flux_balance"]["model_input"]["file"]["sha256"] = "0" * 64
            plan["identity"]["requested_job_sha256"] = digest(plan["requested_job"])
        _environment(monkeypatch, plan)
        manifest = run_flux_balance_native(plan)
        assert manifest["solve_call_count"] == 0 and manifest["execution_outcome"] == "failed", manifest["issues"]
        assert manifest["sealed"]
        output = Path(plan["attempt_directory"]) / "outputs"
        assert read_json(output / "selected-request.json")["requested_job"] == plan["requested_job"]
        assert (output / "original-model.xml").read_bytes() == raw
        if case == "load_failure":
            payload = read_json(output / "model-capture.json")
            assert payload["source_audit"]["xml_elements"] and payload["loaded_original"] is None
        if case == "unsupported_option":
            assert manifest["request_application"]["solver_option_applications"][1]["application"] == "rejected"
        assert not (Path(plan["attempt_directory"]) / ".native-flux-balance-solve-entered.json").exists()


def test_source_units_collisions_and_actual_partial_setter_without_solve(tmp_path, monkeypatch):
    model, context, diagnostics = _live_model(tmp_path)
    units = b'<listOfUnitDefinitions><unitDefinition id="supplied_flux"><listOfUnits><unit kind="mole" exponent="1" scale="-3" multiplier="1"/></listOfUnits></unitDefinition></listOfUnitDefinitions>'
    raw = SBML.replace(b'<listOfCompartments>', units + b'<listOfCompartments>').replace(b'value="0" constant="true"', b'value="0" units="supplied_flux" constant="true"').replace(b'value="10" constant="true"', b'value="10" units="supplied_flux" constant="true"')
    audit, _ = native._source_audit(raw, "sbml")
    source = native._source_information(audit, None)
    assert source["reactions"]["IN"]["flux_unit"]["native_text"] == "supplied_flux"
    assert source["reactions"]["AB"]["flux_unit"]["basis"] == "unknown"
    collision = SBML.replace(b'id="R_OUT"', b'id="AB"')
    audit, _ = native._source_audit(collision, "sbml")
    source = native._source_information(audit, None)
    assert source["unsupported"] and any(row["kind"] == "id_collision" for row in source["features"])
    job = {"constraints": [{"reaction_id": identifier, "lower": _selected_bound(lo), "upper": _selected_bound(hi)}
        for identifier, lo, hi in (("IN", -5, -2), ("AB", 0, 3), ("OUT", 0, 4))],
        "objective": {"kind": "model_default", "reaction_id": None},
        "solver_options": {"feasibility_tolerance": None, "optimality_tolerance": None, "integrality_tolerance": None}}
    import cobra
    original = cobra.Reaction.bounds
    def setter(reaction, value):
        if reaction.id == "AB":
            raise OSError("controlled setter failure after prior application")
        original.fset(reaction, value)
    monkeypatch.setattr(cobra.Reaction, "bounds", property(original.fget, setter))
    application = native._request_application(job)
    assert not native._apply_request(model, job, application, diagnostics)
    assert [r["application"] for r in application["constraint_changes"]] == ["applied", "rejected", "not_attempted"]
    model.solver.update()
    snapshot = native.capture_cobra_glpk_problem(model, phase="effective")
    variables = {row["id"]: row for row in snapshot["variables"]}
    assert variables[model.reactions.IN.forward_variable.name]["lower"]["value"] == 0
    reverse = variables[model.reactions.IN.reverse_variable.name]
    assert (reverse["lower"]["value"], reverse["upper"]["value"]) == (2, 5)
    assert model.reactions.OUT.upper_bound == 1000 and model.solver.status is None


def test_decoded_xml_audit_survives_source_interpretation_exception(tmp_path, monkeypatch):
    import cobra
    from gene_annotation_episode.native_flux_balance_driver import run_flux_balance_native
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid semantic source must never optimize")
    monkeypatch.setattr(cobra.Model, "optimize", forbidden)
    raw = SBML.replace(b'id="M_A" ', b'').replace(b'boundaryCondition="false"', b'boundaryCondition="true"', 1)
    plan = _plan(tmp_path / "invalid_boundary_id", "sbml", raw)
    _environment(monkeypatch, plan)
    manifest = run_flux_balance_native(plan)
    assert manifest["solve_call_count"] == 0 and manifest["execution_outcome"] == "failed"
    output = Path(plan["attempt_directory"]) / "outputs"
    payload = read_json(output / "model-capture.json")
    assert payload["source_audit"]["xml_elements"]
    assert any(r["code"] == "source_semantics_unsupported" for r in payload["source_audit"]["issues"])
    assert (output / "original-model.xml").read_bytes() == raw
    assert b'"operation":"source_information"' in (output / "native-log.txt").read_bytes()
    assert payload["loaded_original"] is None and manifest["request_realization"] != "exact"


def test_saved_emission_recalculation_cli_replay_and_tamper_no_solve(tmp_path, monkeypatch):
    retained = os.environ.get("HMMER_NATIVE_ORACLE_FBA_RETAINED")
    if retained is None:
        pytest.skip("requires explicitly supplied original producer emissions")
    from gene_annotation_episode.native_flux_balance_driver import main, run_flux_balance_native
    from gene_annotation_episode.flux_balance_calculations import calculate_flux_balance_sheet
    import cobra
    def forbidden(*args, **kwargs):
        raise AssertionError("saved/replay verification must not optimize")
    monkeypatch.setattr(cobra.Model, "optimize", forbidden)
    examples = []
    for profile in ("sbml", "cobra_json"):
        folder = Path(retained) / profile
        plan = read_json(folder / "selected-plan.json")
        sheet, calculated = _parsed_calculated(plan)
        before = digest(sheet)
        parameters = deepcopy(calculated["parameters"])
        parameters["objective_absolute_tolerance"] = 0
        recalculated = calculate_flux_balance_sheet(sheet, parameters=parameters)
        assert digest(sheet) == before
        assert recalculated["objective"]["full_calculated"]["value"] == 10
        assert main([str(folder / "selected-plan.json")]) == 0
        manifest = run_flux_balance_native(plan)
        solution = read_json(Path(plan["attempt_directory"]) / "outputs/solution-capture.json")
        assert len(solution["native_passes"]) == 1
        examples.append({"profile": profile, "public_optimize_calls": manifest["solve_call_count"],
            "native_passes": len(solution["native_passes"]), "point_state": solution["point_state"],
            "fluxes": {r["reaction_id"]: r["flux"]["value"] for r in solution["reaction_values"]},
            "variable_count": sheet["problems"]["effective"]["variable_count"],
            "constraint_count": sheet["problems"]["effective"]["constraint_count"],
            "calculated_objective": calculated["objective"]["full_calculated"]["value"],
            "candidate_feasibility": calculated["candidate_feasibility"], "request_realization": sheet["native"]["request_realization"],
            "evaluated_variable_bound_sides": calculated["evaluated_variable_bound_count"],
            "violated_variable_bound_sides": calculated["violated_variable_bound_count"],
            "constraint_activities": {r["constraint_id"]: r["activity"]["value"] for r in calculated["constraint_checks"]},
            "artifact_bytes": {r["role"]: r["identity"]["size_bytes"] for r in manifest["files"]},
            "original_sheet_sha256": calculated["sheet_sha256"], "saved_recalculation_sheet_sha256": recalculated["sheet_sha256"]})
        assert manifest["request_application"]["constraint_changes"] == [] if profile == "sbml" else len(manifest["request_application"]["constraint_changes"]) == 2
        altered = deepcopy(plan)
        altered["identity"]["requested_job_sha256"] = "0" * 64
        with pytest.raises(ValueError, match="original_attempt_mismatch"):
            run_flux_balance_native(altered)
    immutable_json(ATTEMPT / "verified-numerical-examples.json", examples)
    print(canonical({"authentic_original_cases": examples, "new_native_calls_in_this_test": 0}))


def test_controlled_exception_after_observed_return_and_csv_write_failure(tmp_path, monkeypatch):
    """Synthetic execution faults: zero native solves, not native measurements."""
    retained = os.environ.get("HMMER_NATIVE_ORACLE_FBA_RETAINED")
    if retained is None:
        pytest.skip("controlled transport fixture requires original retained bytes")
    import cobra
    import optlang.glpk_interface as interface
    from gene_annotation_episode import native_flux_balance_driver as driver
    original_plan = read_json(Path(retained) / "sbml/selected-plan.json")
    retained_payload = read_json(Path(original_plan["attempt_directory"]) / "outputs/solution-capture.json")
    native_calls = []
    # The wrapper observes a controlled Python routine return, not GLPK work.
    def controlled_native(problem, parameters):
        native_calls.append("controlled_return_only")
        return 0
    monkeypatch.setattr(interface, "glp_simplex", controlled_native)
    def controlled_optimize(model):
        interface.glp_simplex(model.solver.problem, model.solver.configuration._smcp)
        raise RuntimeError("controlled exception after the observed routine returned")
    monkeypatch.setattr(cobra.Model, "optimize", controlled_optimize)
    software = _software()
    plan = _plan(tmp_path / "controlled_exception", "sbml", SBML, software=software)
    _environment(monkeypatch, plan)
    manifest = driver.run_flux_balance_native(plan)
    assert manifest["solve_call_count"] == 1 and manifest["execution_outcome"] == "partial"
    output = Path(plan["attempt_directory"]) / "outputs"
    payload = read_json(output / "solution-capture.json")
    assert payload["solution_object_state"] == "not_returned"
    assert payload["point_state"] == "not_established"  # Actual unsolved getters are not promoted.
    assert len(payload["native_passes"]) == 1 and payload["native_passes"][0]["return_code"] == 0
    assert all(r["primal"]["state"] == "missing" for r in payload["variable_values"])
    assert (output / "problem-capture.json").is_file()
    # A transport stub supplies already retained bytes to exercise only the
    # post-capture writer branch. No Cobra Solution is constructed or restored.
    sentinel = object()
    monkeypatch.setattr(cobra.Model, "optimize", lambda model: sentinel)
    monkeypatch.setattr(native, "capture_cobra_glpk_solution", lambda *args, **kwargs: deepcopy(retained_payload))
    def failed_csv(*args, **kwargs):
        raise OSError("controlled CSV writer failure after native payload retention")
    monkeypatch.setattr(driver, "_csv", failed_csv)
    plan = _plan(tmp_path / "controlled_csv", "sbml", SBML, software=software)
    _environment(monkeypatch, plan)
    manifest = driver.run_flux_balance_native(plan)
    output = Path(plan["attempt_directory"]) / "outputs"
    assert manifest["execution_outcome"] == "partial" and manifest["solve_call_count"] == 1
    assert read_json(output / "solution-capture.json") == retained_payload
    assert next(r for r in manifest["files"] if r["role"] == "flux_csv")["state"] == "absent"
    assert len(native_calls) == 1
    immutable_json(ATTEMPT / "controlled-fault-evidence.json", {"evidence_class": "synthetic transport and exception plumbing",
        "actual_glpk_calls": 0, "controlled_routine_returns": len(native_calls), "cobra_solution_objects_constructed": 0,
        "authoritative_native_emissions_unchanged": str(Path(retained))})


def test_final_software_identity_failure_downgrades_exact_without_native_work(tmp_path, monkeypatch):
    """Controlled Python invocation only; the native optimizer is never called."""
    import cobra
    from gene_annotation_episode import native_flux_balance_driver as driver
    original_verify = driver._verify_software
    def verify(software, *, native_loaded=False):
        if native_loaded:
            raise ValueError("fba_software_file_changed")
        return original_verify(software)
    monkeypatch.setattr(driver, "_verify_software", verify)
    controlled_calls = []
    def return_no_solution(model):
        controlled_calls.append("python_stub_only")
        return None
    monkeypatch.setattr(cobra.Model, "optimize", return_no_solution)
    plan = _plan(tmp_path / "final_software_identity", "sbml", SBML)
    _environment(monkeypatch, plan)
    manifest = driver.run_flux_balance_native(plan)
    assert len(controlled_calls) == 1
    assert manifest["execution_outcome"] == "partial"
    assert manifest["request_realization"] == manifest["request_application"]["request_realization"] == "unknown"
    assert any(row["code"] == "binding_unavailable" for row in manifest["issues"])
    payload = read_json(Path(plan["attempt_directory"]) / "outputs/solution-capture.json")
    assert payload["native_passes"] == [] and payload["point_state"] == "not_established"


def test_invalid_selected_requests_and_envelopes_reject_before_invocation(tmp_path, monkeypatch):
    from gene_annotation_episode.native_flux_balance_driver import run_flux_balance_native
    import cobra
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid envelope must never invoke native work")
    monkeypatch.setattr(cobra.Model, "optimize", forbidden)
    plan = _plan(tmp_path / "invalid_selections", "sbml", SBML)
    change = {"reaction_id": "IN", "lower": _selected_bound(0), "upper": _selected_bound(10)}
    for changes in ([change, deepcopy(change)],
                    [change | {"lower": _selected_bound(11)}],
                    [change | {"lower": change["lower"] | {"value": float("nan")}}],
                    [change | {"lower": change["lower"] | {"kind": "unknown_kind"}}]):
        altered = deepcopy(plan)
        altered["requested_job"]["native_flux_balance"]["constraints"] = changes
        with pytest.raises(ValueError):
            run_flux_balance_native(altered)
    for field, value in (("role", "unsupported_role"), ("relative_path", "../escape"), ("format", "unsupported_format")):
        altered = deepcopy(plan)
        altered["outputs"][0][field] = value
        with pytest.raises(ValueError):
            run_flux_balance_native(altered)
    altered = deepcopy(plan)
    altered["requested_job"]["native_flux_balance"]["source_function_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source_function_mismatch"):
        run_flux_balance_native(altered)
    assert not Path(plan["attempt_directory"]).exists()


def test_selected_producer_native_sbml_and_json_once(tmp_path, monkeypatch):
    if os.environ.get("HMMER_NATIVE_ORACLE_FBA_PRODUCER") != "two-selected-cases-688":
        pytest.skip("two new original solves require this explicit selected verification")
    from gene_annotation_episode.native_flux_balance_driver import run_flux_balance_native
    software = _software()
    cases = [("sbml", SBML, None), ("cobra_json", canonical(_json_model()).encode(), [
        {"reaction_id": "AB", "lower": _selected_bound(0), "upper": _selected_bound(10)},
        {"reaction_id": "IN", "lower": _selected_bound(0), "upper": _selected_bound(10)}])]
    manifests, records = [], []
    for profile, raw, changes in cases:
        root = ATTEMPT / "producer-emissions" / profile
        plan = _plan(root, profile, raw, changes=changes, software=software,
            objective={"kind": "single_reaction", "reaction_id": "OUT"} if changes else None,
            options={"feasibility_tolerance": 1e-8, "optimality_tolerance": None, "integrality_tolerance": 1e-7} if changes else None)
        immutable_json(root / "selected-plan.json", plan)
        _environment(monkeypatch, plan)
        manifest = run_flux_balance_native(plan)
        manifests.append(manifest)
        records.append({"profile": profile, "plan": str(root / "selected-plan.json"), "manifest": manifest})
        # Preserve both actual selected calls before parsing/assertion repairs.
    immutable_json(ATTEMPT / "producer-emissions/results.json", records)
    for record in records:
        plan = read_json(record["plan"])
        manifest = record["manifest"]
        assert manifest["solve_call_count"] == 1, manifest["issues"]
        assert manifest["execution_outcome"] == "completed", manifest["issues"]
        assert {r["state"] for r in manifest["files"]} == {"present"}
        sheet, calculations = _parsed_calculated(plan)
        root = Path(record["plan"]).parent
        immutable_json(root / "parsed-sheet.json", sheet)
        immutable_json(root / "calculated.json", calculations)
        assert not [r for r in sheet["issues"] if r["code"] != "source_precision_unknown"], sheet["issues"]
        assert [r["flux"]["value"] for r in sheet["native_solution"]["native"]["reaction_values"]] == [10, 10, 10]
        assert calculations["candidate_feasibility"] == "passes_recorded_checks"
        assert calculations["objective"]["full_calculated"]["value"] == 10
        assert sheet["native"]["request_realization"] == "exact"
        assert run_flux_balance_native(plan) == manifest  # read-only replay; no second invocation.
        assert flux_balance_driver_argv(plan)[-1].endswith("/flux-balance-plan.json")


def test_selected_native_bound_and_objective_perturbations():
    """Three actual selected solves of one supplied, analytically known model."""
    if os.environ.get("HMMER_NATIVE_ORACLE_FBA_PERTURBATIONS") != "three-selected-perturbations-688":
        pytest.skip("three original perturbation solves require explicit selection")
    selected = os.environ.get("HMMER_NATIVE_ORACLE_FBA716_SOFTWARE")
    if selected is None:
        pytest.skip("requires the explicitly selected prepared714 software descriptor")
    from gene_annotation_episode import native_lifecycle
    from gene_annotation_episode.local_jobs import LocalJobPolicy
    from gene_annotation_episode.native_flux_balance_contracts import validate_flux_balance_software

    descriptor = Path(selected)
    assert descriptor.is_absolute()
    descriptor_pin = file_pin(descriptor)
    software = validate_flux_balance_software(read_json(descriptor))
    document = {"id": "selected_reaction_perturbations", "name": "supplied numerical branch model",
        "version": "1", "compartments": {"c": "supplied compartment"}, "genes": [],
        "metabolites": [{"id": "A", "name": "A", "compartment": "c"}],
        "reactions": [
            {"id": "UPTAKE", "name": "supplied input", "metabolites": {"A": 1},
                "lower_bound": 0, "upper_bound": 10, "gene_reaction_rule": "", "objective_coefficient": 0},
            {"id": "GROWTH", "name": "supplied growth drain", "metabolites": {"A": -1},
                "lower_bound": 0, "upper_bound": 1000, "gene_reaction_rule": "", "objective_coefficient": 1},
            {"id": "PRODUCT", "name": "supplied product drain", "metabolites": {"A": -1},
                "lower_bound": 0, "upper_bound": 1000, "gene_reaction_rule": "", "objective_coefficient": 0}]}
    raw = canonical(document).encode()
    input_sha = hashlib.sha256(raw).hexdigest()
    root = ATTEMPT / "producer-perturbations"
    root.mkdir(exist_ok=False)  # Keep an original failed attempt available for review.
    cases = [
        ("baseline", None, None, {"UPTAKE": 10, "GROWTH": 10, "PRODUCT": 0}, "GROWTH", 10),
        ("input_cap", [{"reaction_id": "UPTAKE", "lower": _selected_bound(0), "upper": _selected_bound(4)}],
            None, {"UPTAKE": 4, "GROWTH": 4, "PRODUCT": 0}, "GROWTH", 4),
        ("growth_clamped_product_objective", [
            {"reaction_id": "UPTAKE", "lower": _selected_bound(0), "upper": _selected_bound(4)},
            {"reaction_id": "GROWTH", "lower": _selected_bound(0), "upper": _selected_bound(0)}],
            {"kind": "single_reaction", "reaction_id": "PRODUCT"},
            {"UPTAKE": 4, "GROWTH": 0, "PRODUCT": 4}, "PRODUCT", 4)]
    records = []
    for name, changes, objective, expected_fluxes, objective_id, expected_objective in cases:
        folder = root / name
        plan = _plan(folder, "cobra_json", raw, changes=changes, objective=objective, software=software,
            operation_key="selected-perturbation-" + name)
        immutable_json(folder / "selected-plan.json", plan)
        lifecycle = Path(plan["identity"]["execution_id"]).parent
        lifecycle.mkdir(parents=True)
        immutable_json(lifecycle / RUN_PLAN_FILENAME, plan)
        handle = native_lifecycle.start_job(flux_balance_driver_argv(plan), cwd=lifecycle,
            policy=LocalJobPolicy(**POLICY), handle_path=plan["identity"]["execution_id"],
            env=plan["requested_job"]["environment"])
        execution = native_lifecycle.wait_job(handle)
        immutable_json(folder / "native-execution.json", {"returncode": execution.returncode, "metadata": execution.metadata})
        assert execution.returncode == 0, execution.metadata
        assert execution.metadata["verified_cgroup"] == {"memory_max": 21474836480, "memory_swap_max": 0,
            "kill_mode": "control-group", "oom_policy": "kill"}
        manifest = read_json(Path(plan["attempt_directory"]) / "outputs/native-manifest.json")
        records.append({"case": name, "plan": str(folder / "selected-plan.json"), "manifest": manifest})
        immutable_json(root / (name + "-result.json"), records[-1])

    summaries = []
    for record, (name, changes, objective, expected_fluxes, objective_id, expected_objective) in zip(records, cases, strict=True):
        plan = read_json(record["plan"])
        manifest = record["manifest"]
        sheet, calculations = _parsed_calculated(plan)
        folder = Path(record["plan"]).parent
        immutable_json(folder / "parsed-sheet.json", sheet)
        immutable_json(folder / "calculated.json", calculations)
        assert manifest["solve_call_count"] == 1 and manifest["execution_outcome"] == "completed", manifest["issues"]
        assert manifest["request_realization"] == sheet["native"]["request_realization"] == "exact"
        assert {row["state"] for row in manifest["files"]} == {"present"}
        job = plan["requested_job"]["native_flux_balance"]
        assert job["constraints"] == changes
        assert job["objective"] == (objective or {"kind": "model_default", "reaction_id": None})
        source = Path(job["model_input"]["file"]["path"])
        assert source.read_bytes() == raw and file_pin(source) == job["model_input"]["file"]
        assert job["model_input"]["file"]["sha256"] == input_sha
        assert (Path(plan["attempt_directory"]) / "outputs/original-model.json").read_bytes() == raw
        assert read_json(Path(plan["attempt_directory"]) / "outputs/selected-request.json")["requested_job"] == plan["requested_job"]
        application = manifest["request_application"]
        assert application["objective_application"] == ("applied" if objective else "model_default")
        assert [row["reaction_id"] for row in application["constraint_changes"]] == [row["reaction_id"] for row in changes or []]
        assert all(row["application"] == "applied" for row in application["constraint_changes"])
        for phase in ("loaded_original", "effective"):
            bounds = {row["id"]: (row["lower"]["value"], row["upper"]["value"]) for row in sheet["models"][phase]["reactions"]}
            expected_bounds = {"UPTAKE": (0, 10), "GROWTH": (0, 1000), "PRODUCT": (0, 1000)}
            if phase == "effective":
                expected_bounds.update({row["reaction_id"]: (row["lower"]["value"], row["upper"]["value"]) for row in changes or []})
            assert bounds == expected_bounds
            problem = sheet["problems"][phase]
            model = sheet["models"][phase]
            selected_id = objective_id if phase == "effective" else "GROWTH"
            position = next(row["position"] for row in model["reactions"] if row["id"] == selected_id)
            variables = next(row for row in problem["reaction_variables"] if row["reaction_position"] == position)
            coefficients = {row["variable_position"]: row["coefficient"]["value"]
                for row in problem["objective"]["terms"] if row["coefficient"]["value"] != 0}
            assert coefficients == {variables["forward_variable_position"]: 1, variables["reverse_variable_position"]: -1}
            assert problem["objective"]["direction"] == "max"
        solution = sheet["native_solution"]["native"]
        fluxes = {row["reaction_id"]: row["flux"]["value"] for row in solution["reaction_values"]}
        assert solution["model_optimize_call_count"] == 1 and solution["point_state"] == "basic_solution"
        assert solution["native_passes"] and all(row["routine"] == "glp_simplex" for row in solution["native_passes"])
        assert fluxes == expected_fluxes
        # This supplied model has one conservation equation and a single unit objective coefficient.
        assert fluxes["UPTAKE"] == fluxes["GROWTH"] + fluxes["PRODUCT"]
        assert calculations["objective"]["full_calculated"]["value"] == expected_objective
        assert calculations["objective"]["native_cobra"]["value"] == expected_objective
        assert calculations["candidate_feasibility"] == "passes_recorded_checks"
        assert calculations["native_solver_status"] == "optimal"
        summaries.append({"case": name, "fluxes": fluxes, "objective_reaction": objective_id,
            "calculated_objective": calculations["objective"]["full_calculated"],
            "original_input_sha256": input_sha, "sheet_sha256": calculations["sheet_sha256"],
            "solve_call_count": manifest["solve_call_count"], "request_application": application})
    assert len({record["manifest"]["attempt"]["operation_key"] for record in records}) == len(cases)
    assert file_pin(descriptor) == descriptor_pin and canonical(document).encode() == raw
    immutable_json(root / "verified-perturbations.json", {"software_file": descriptor_pin,
        "scope": "supplied numerical model; reaction bounds and objective only", "cases": summaries})
