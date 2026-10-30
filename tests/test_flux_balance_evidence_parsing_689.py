"""Supplied-byte 007/008/009/010 evidence tests, with no native invocation.

All new captures here are explicitly synthetic transformations of the 680
TEST-normalized 677 fixture. They establish byte contracts, not producer output,
original execution custody, episode delivery or authentic new solver branches.
"""
from copy import deepcopy
import builtins
import io
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.flux_balance_contracts import validate_flux_balance_record
from gene_annotation_episode.flux_balance_readers import (
    parse_cobra_glpk_model_capture, parse_cobra_glpk_problem_capture,
    parse_cobra_glpk_solution_capture, parse_fba_capture,
)
from gene_annotation_episode.flux_balance_sheet import populate_flux_balance_sheet
from gene_annotation_episode.flux_balance_calculations import calculate_flux_balance_sheet
from test_flux_balance_core_679 import parameters
from test_flux_balance_readers_680 import (
    bound, bundle, captures, encode, file, location, missing, number, parsed,
    parse_model, parse_problem, parse_solution, replace_role,
)
from test_flux_balance_parser_recovery_686 import relocated


OPTIONS = ("feasibility_tolerance", "optimality_tolerance", "integrality_tolerance")


def update_manifest(payloads, expected):
    manifest = json.loads(payloads["manifest"]["bytes"])
    manifest["attempt"] = deepcopy(expected)
    manifest["effective_problem_sha256"] = (payloads["effective_problem"]["file"] or {}).get("sha256")
    for row in manifest["files"]:
        payload = payloads[row["role"]]
        row["state"] = payload["state"]
        row["identity"] = None if payload["file"] is None else {
            key: payload["file"][key] for key in ("sha256", "size_bytes")}
        if payload["file"] is not None:
            row["format"] = payload["file"]["format"]
    replace_role(payloads, "manifest", manifest)


def select(payloads, expected, edit):
    selected = json.loads(payloads["selected_request"]["bytes"])
    edit(selected["requested_job"]["native_flux_balance"])
    expected["requested_job_sha256"] = digest(selected["requested_job"])
    selected["attempt"] = deepcopy(expected)
    replace_role(payloads, "selected_request", selected)
    update_manifest(payloads, expected)


def retained(name, payloads, result):
    attempt = os.environ.get("HMMER529_ATTEMPT")
    if attempt:
        Path(attempt, f"fba689_{name}.json").write_text(json.dumps({
            "fixture_identity": "synthetic supplied-byte records using TEST-normalized677 inputs; no solve or production capture",
            "manifest": json.loads(payloads["manifest"]["bytes"]),
            "selected_request": json.loads(payloads["selected_request"]["bytes"]),
            "result": result,
        }, indent=2, allow_nan=False) + "\n")


def synthetic_bundle(captures, *, constraints=None, objective="model_default", options=None):
    """Create a declared synthetic before/after pair with only selected changes."""
    capture = deepcopy(captures)
    for key in ("models", "problems"):
        capture[key]["loaded_original"] = relocated(capture[key]["effective"], "/effective", "/loaded_original")
    capture["problems"]["loaded_original"]["phase"] = "loaded_original"
    if objective == "single_reaction":
        obj = capture["problems"]["effective"]["objective"]
        obj["terms"] = [{"variable_position": pos, "coefficient": number(value,
            f"/effective/objective/terms/{i}/coefficient/value", "effective_problem")}
            for i, (pos, value) in enumerate(((4, 1), (5, -1)))]
        for key in ("native_constant", "interface_offset", "symbolic_constant"):
            obj[key] = number(0, f"/effective/objective/{key}/value", "effective_problem")
    for name, value in (options or {}).items():
        if name != "optimality_tolerance":
            capture["problems"]["configuration_before_solve"][name] = number(
                value, "/configuration_before_solve/" + name + "/value", "effective_problem")
    for role, key in (("effective_model", "models"), ("effective_problem", "problems")):
        capture["raw"][role] = encode(capture[key])
        capture["files"][role] = file(capture["raw"][role], capture[key]["version"])
    payloads, expected = bundle(capture)
    def edit(job):
        job["objective"] = {"kind": objective, "reaction_id": "OUT" if objective == "single_reaction" else None}
        job["constraints"] = deepcopy(constraints)
        job["solver_options"].update(options or {})
    select(payloads, expected, edit)
    selected = json.loads(payloads["selected_request"]["bytes"])["requested_job"]["native_flux_balance"]
    changes = []
    positions = {row["id"]: row["position"] for row in capture["models"]["effective"]["reactions"]}
    for index, row in enumerate(selected["constraints"] or []):
        entry = {"reaction_id": row["reaction_id"], "effective_reaction_position": positions.get(row["reaction_id"]),
                 "application": "applied", "issue_code": None}
        for side in ("lower", "upper"):
            entry["requested_" + side] = deepcopy(row[side])
            entry["requested_" + side]["source"] = location("selected_request",
                f"/requested_job/native_flux_balance/constraints/{index}/{side}")
        changes.append(entry)
    application = {"version": "cobra_fba_request_application_v1",
        "selected_request": location("selected_request", "/requested_job"),
        "constraint_changes": changes, "objective_request": selected["objective"],
        "objective_application": "model_default" if objective == "model_default" else "applied",
        "objective_requested_source": location("selected_request", "/requested_job/native_flux_balance/objective"),
        "objective_effective_source": location("effective_problem", "/effective/objective"),
        "solver_option_applications": [{"name": name,
            "application": "not_requested" if selected["solver_options"][name] is None else "applied",
            "requested_source": location("selected_request", "/requested_job/native_flux_balance/solver_options/" + name),
            "effective_source": None if selected["solver_options"][name] is None else location("effective_problem", "/configuration_before_solve/" + name),
            "issue_code": None} for name in OPTIONS],
        "request_realization": "exact", "issues": []}
    manifest = json.loads(payloads["manifest"]["bytes"])
    manifest["request_application"] = application
    replace_role(payloads, "manifest", manifest)
    return payloads, expected


def change(reaction, lower, upper):
    result = {"reaction_id": reaction, "lower": bound(lower, ""), "upper": bound(upper, "")}
    result["lower"]["source"] = result["upper"]["source"] = None
    return result


def edit_role(payloads, expected, role, edit):
    value = json.loads(payloads[role]["bytes"])
    edit(value)
    replace_role(payloads, role, value)
    if role != "manifest":
        update_manifest(payloads, expected)


def issue_at(result, field, code="request_effective_mismatch"):
    return any(row["code"] == code and row["field"] == field for row in result["issues"])


def audit(profile="sbml"):
    """Deliberate XML character-data/source-tree fixture, not XML loading."""
    elements = []
    names = [("urn:sbml", "sbml", None), ("urn:sbml", "model", 0),
             ("urn:fbc", "geneProductAssociation", 1), ("urn:fbc", "or", 2),
             ("urn:fbc", "geneProductRef", 3), ("urn:fbc", "geneProductRef", 3)]
    for index, (namespace, name, parent) in enumerate(names):
        ordinal = sum(1 for previous in elements if previous["parent_source_record_index"] == parent
            and previous["path"][-1]["name"] == {"namespace_uri": namespace, "local_name": name})
        step = {"name": {"namespace_uri": namespace, "local_name": name}, "sibling_ordinal": ordinal}
        elements.append({"source_record_index": index,
            "path": ([] if parent is None else deepcopy(elements[parent]["path"])) + [step],
            "parent_source_record_index": parent, "child_source_record_indices": [],
            "namespace_declarations": [{"prefix": "", "uri": "urn:sbml"}, {"prefix": "fbc", "uri": "urn:fbc"}] if index == 0 else [],
            "attributes": [], "text": " \n" if index == 0 else "" if index == 1 else None,
            "tail": None if index == 0 else "\n"})
        if parent is not None:
            elements[parent]["child_source_record_indices"].append(index)
    elements[1]["attributes"] = [
        {"name": {"namespace_uri": None, "local_name": "id"}, "value": "M & source"},
        {"name": {"namespace_uri": "urn:fbc", "local_name": "lowerFluxBound"}, "value": "LB_IN"},
        {"name": {"namespace_uri": None, "local_name": "empty"}, "value": ""}]
    for index, identifier in ((4, "first"), (5, "second")):
        elements[index]["attributes"] = [{"name": {"namespace_uri": "urn:fbc", "local_name": "geneProduct"}, "value": identifier}]
    return {"version": "cobra_fba_source_audit_v1", "input_profile": profile,
        "original_model": location("original_model", ""),
        "xml_elements": elements if profile == "sbml" else None, "issues": []}


@pytest.mark.parametrize("state", ["absent", "null"])
def test_old_optional_absence_and_null_remain_distinct(captures, state):
    payload = deepcopy(captures["models"])
    if state == "null":
        payload["source_audit"] = None
        for phase in ("loaded_original", "effective"):
            payload[phase]["native_capture_evidence"] = None
    result = parse_model(payload, captures)
    assert ("source_audit" in result) == (state == "null")
    assert ("native_capture_evidence" in result["effective"]) == (state == "null")
    if state == "null":
        assert result["source_audit"] is result["effective"]["native_capture_evidence"] is None
    payloads, expected = bundle(captures)
    if state == "null":
        edit_role(payloads, expected, "manifest", lambda m: m.update(request_application=None))
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native"]["objective_application"] == "unknown"
    assert result["native"]["constraint_changes"] == []
    assert result["native"]["request_realization"] == "exact"  # retained legacy assertion, contract010


@pytest.mark.parametrize("load_failed", [False, True])
def test_typed_xml_audit_preserves_character_data_tree_and_load_failure(captures, load_failed):
    payload = deepcopy(captures["models"])
    payload["source_audit"] = audit()
    if load_failed:
        payload["loaded_original"] = payload["effective"] = None
    else:
        for phase in ("loaded_original", "effective"):
            payload[phase]["reactions"][1].update(gpr_native=None,
                gpr_source_pointer="/source_audit/xml_elements/2", gpr_loaded="first or second")
    before = deepcopy(payload)
    result = parse_model(payload, captures)
    assert result["issues"] == [] and payload == before
    bound_audit = {**deepcopy(payload["source_audit"]), "original_model": {
        "file": captures["files"]["original_model"], "pointer": ""}}
    assert result["source_audit"] == bound_audit
    assert result["source_audit"]["xml_elements"][1]["text"] == ""
    assert result["source_audit"]["xml_elements"][2]["text"] is None
    assert result["source_audit"]["xml_elements"][5]["path"][-1]["sibling_ordinal"] == 1
    assert result["source_audit"]["xml_elements"][1]["attributes"][1]["value"] == "LB_IN"
    if load_failed:
        assert result["loaded_original"] is result["effective"] is None
    else:
        assert result["effective"]["reactions"][1]["gpr_native"] is None


@pytest.mark.parametrize("defect", ["malformed", "original_identity", "profile", "whole_pointer", "child_join"])
def test_bad_optional_audit_does_not_discard_snapshots(captures, defect):
    payload = deepcopy(captures["models"])
    payload["source_audit"] = audit()
    a = payload["source_audit"]
    if defect == "malformed":
        del a["xml_elements"]
    elif defect == "original_identity":
        a["original_model"] = {"file": {**captures["files"]["original_model"], "sha256": "9" * 64}, "pointer": ""}
    elif defect == "profile":
        a["input_profile"] = "cobra_json"
        a["xml_elements"] = None
    elif defect == "whole_pointer":
        a["original_model"]["pointer"] = "/invented-XML-pointer"
    else:
        a["xml_elements"][3]["child_source_record_indices"] = [5, 4]
    result = parse_model(payload, captures)
    assert result["source_audit"] is None
    assert len(result["effective"]["reactions"]) == len(result["loaded_original"]["reactions"]) == 3
    assert any(row["field"].startswith("/source_audit") for row in result["issues"])
    validate_flux_balance_record("ParsedModelSnapshots", result)


def test_json_audit_and_missing_source_fields_stay_distinct_from_loaded_defaults(captures):
    payload = deepcopy(captures["models"])
    payload.update(input_profile="cobra_json", source_audit=audit("cobra_json"))
    payload["loader"].update(name="load_json_model", id_replacement="none")
    payload["effective"]["native_capture_evidence"] = {"original_json_gpr": "", "loaded_default": 1000}
    row = payload["effective"]["reactions"][1]
    row.update(gpr_native="", gpr_source_pointer="/effective/native_capture_evidence/original_json_gpr")
    original = file(b'{"reactions":[{}]}', "cobra_json")
    raw = encode(payload)
    result = parse_cobra_glpk_model_capture(raw, source=file(raw, payload["version"]), original_model=original)
    assert result["source_audit"]["xml_elements"] is None
    assert result["effective"]["reactions"][1]["gpr_native"] == ""
    assert "gene_reaction_rule" not in json.loads(b'{"reactions":[{}]}')["reactions"][0]


def test_native_evidence_is_opaque_and_cannot_authorize_fake_files(captures):
    fake = {"artifact_ref": "fake", "sha256": "4" * 64, "size_bytes": 1, "format": "sbml"}
    payload = deepcopy(captures["models"])
    raw_evidence = {"fake_file": fake, "address": {"role": [], "pointer": "not a typed pointer"},
                    "native_token": "nan", "value": None}
    payload["effective"]["native_capture_evidence"] = deepcopy(raw_evidence)
    models = parse_model(payload, captures)
    assert models["effective"]["native_capture_evidence"] == raw_evidence
    problem = deepcopy(captures["problems"])
    problem["effective"]["variables"][0]["lower"]["source"] = {"file": fake, "pointer": ""}
    raw = encode(problem)
    result = parse_cobra_glpk_problem_capture(raw, source=file(raw, problem["version"]), models=models)
    assert [row["position"] for row in result["effective"]["variables"]] == list(range(1, 7))
    assert any(row["code"] == "artifact_identity_conflict" for row in result["issues"])


def test_native_pass_diagnostics_and_raw_getter_pointers_remain_opaque(captures):
    payload = deepcopy(captures["solution"])
    evidence = {"version": "cobra_glpk_solution_evidence_v1", "diagnostics": {"warnings": [], "logging": [], "exceptions": []},
        "configuration_after_solve": {"integer_controls": None},
        "raw_getters": {"final": "not an earlier-pass substitute"}, "native_passes": []}
    for index, row in enumerate(payload["native_passes"]):
        evidence["native_passes"].append({"parameters": {"actual": 1}, "exception": None,
            "raw_getters": {"primal": 7, "native_token": "7.0", "position": index}})
        row["parameters_pointer"] = f"/native_capture_evidence/native_passes/{index}/parameters"
    payload["native_capture_evidence"] = evidence
    payload["diagnostics_pointer"] = "/native_capture_evidence/diagnostics"
    payload["configuration_after_solve"]["integer_controls_pointer"] = "/native_capture_evidence/configuration_after_solve/integer_controls"
    result = parse_solution(payload, captures)
    assert result["issues"] == []
    assert result["native"]["native_capture_evidence"] == evidence
    assert result["native"]["variable_values"][0]["primal"]["value"] == 7
    payload["native_passes"][0]["parameters_pointer"] += "/missing"
    result = parse_solution(payload, captures)
    assert result["native"]["native_capture_evidence"] == evidence
    assert [row["variable_position"] for row in result["native"]["variable_values"]] == list(range(7))
    assert any(row["field"].startswith("/native_passes/0") for row in result["issues"])


@pytest.mark.parametrize("constraints", [None, []], ids=["selected_null", "selected_empty"])
def test_known_no_changes_stays_empty_with_exact_observed_default(captures, constraints):
    payloads, expected = synthetic_bundle(captures, constraints=constraints)
    original = deepcopy(payloads)
    result = parse_fba_capture(payloads, expected=expected)
    assert payloads == original
    assert result["native"]["constraint_changes"] == []
    assert result["native"]["objective_application"] == "model_default"
    assert result["native"]["request_realization"] == "exact"
    assert json.loads(payloads["selected_request"]["bytes"])["requested_job"]["native_flux_balance"]["constraints"] == constraints
    retained("known_no_changes_" + str(constraints is None), payloads, result)


def test_null_application_changes_remain_unknown(captures):
    payloads, expected = synthetic_bundle(captures)
    def alter(manifest):
        manifest["request_realization"] = "unknown"
        manifest["request_application"].update(constraint_changes=None, request_realization="unknown")
    edit_role(payloads, expected, "manifest", alter)
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native"]["constraint_changes"] is None
    assert result["native"]["request_realization"] == "unknown"


def test_exact_bound_application_and_digest_before_source_binding(captures):
    request = change("IN", -10.0, 8.0)
    for side in ("lower", "upper"):
        request[side]["source"] = location("selected_request", f"/requested_job/native_flux_balance/constraints/0/{side}/value")
    payloads, expected = synthetic_bundle(captures, constraints=[request], options={"feasibility_tolerance": 1e-6})
    original = deepcopy(payloads)
    result = parse_fba_capture(payloads, expected=expected)
    selected = json.loads(payloads["selected_request"]["bytes"])
    assert digest(selected["requested_job"]) == expected["requested_job_sha256"]
    assert result["native"]["request_realization"] == "exact"
    actual = result["native"]["constraint_changes"][0]
    assert actual["application"] == "applied" and actual["effective_reaction_position"] == 0
    assert actual["requested_lower"]["source"] == {"file": payloads["selected_request"]["file"],
        "pointer": "/requested_job/native_flux_balance/constraints/0/lower"}
    assert payloads == original
    retained("exact_bound_and_original_digest", payloads, result)


@pytest.mark.parametrize("defect", ["bound_value", "order", "reaction_id", "position"])
def test_selected_order_and_bound_records_cannot_be_replaced(captures, defect):
    payloads, expected = synthetic_bundle(captures, constraints=[change("IN", -10, 8), change("AB", 0, "inf")])
    def alter(manifest):
        rows = manifest["request_application"]["constraint_changes"]
        if defect == "bound_value":
            rows[0]["requested_lower"].update(value=-11, native_token="-11")
        elif defect == "order":
            rows.reverse()
            for index, row in enumerate(rows):
                for side in ("lower", "upper"):
                    row["requested_" + side]["source"]["pointer"] = f"/requested_job/native_flux_balance/constraints/{index}/{side}"
        elif defect == "reaction_id":
            rows[0]["reaction_id"] = "WRONG"
        else:
            rows[0]["effective_reaction_position"] = 2
    edit_role(payloads, expected, "manifest", alter)
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native"]["request_realization"] == "mismatch"
    assert result["native"]["constraint_changes"][0]["application"] == "unknown"
    assert len(result["native_solution"]["native"]["variable_values"]) == 7


@pytest.mark.parametrize("lower,upper,native", [
    (2, 7, ((2, 7), (0, 0))), (-8, -2, ((0, 0), (2, 8))),
    (-10, 8, ((0, 8), (0, 10))), ("-inf", "inf", ((0, "inf"), (0, "inf"))),
    (0, 0, ((0, 0), (0, 0))),
])
def test_pinned_native_sign_split_readback(captures, lower, upper, native):
    payloads, expected = synthetic_bundle(captures, constraints=[change("IN", lower, upper)])
    def model_edit(model):
        for side, value in (("lower", lower), ("upper", upper)):
            model["effective"]["reactions"][0][side] = bound(value, f"/effective/reactions/0/{side}/value")
    def problem_edit(problem):
        for position, sides in enumerate(native):
            for side, value in zip(("lower", "upper"), sides):
                problem["effective"]["variables"][position][side] = bound(value,
                    f"/effective/variables/{position}/{side}/value", "effective_problem")
    edit_role(payloads, expected, "effective_model", model_edit)
    edit_role(payloads, expected, "effective_problem", problem_edit)
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native"]["constraint_changes"][0]["application"] == "applied"
    assert result["native"]["request_realization"] == "exact"


@pytest.mark.parametrize("defect,realization", [("missing_native", "unknown"), ("wrong_native", "mismatch"),
    ("wrong_model", "mismatch"), ("missing_and_wrong_native", "mismatch")])
def test_applied_bound_requires_both_model_and_solver_readback(captures, defect, realization):
    payloads, expected = synthetic_bundle(captures, constraints=[change("IN", -10, 8)])
    if defect == "wrong_model":
        edit_role(payloads, expected, "effective_model", lambda m: m["effective"]["reactions"][0].update(
            upper=bound(9, "/effective/reactions/0/upper/value")))
    else:
        def alter(problem):
            rows = problem["effective"]["variables"]
            if defect in {"missing_native", "missing_and_wrong_native"}:
                rows[0]["upper"] = {"kind": "missing", "value": None, "native_token": None, "float_hex": None, "source": None}
            if defect in {"wrong_native", "missing_and_wrong_native"}:
                rows[1]["upper"] = bound(11, "/effective/variables/1/upper/value", "effective_problem")
        edit_role(payloads, expected, "effective_problem", alter)
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native"]["request_realization"] == realization
    assert result["native"]["constraint_changes"][0]["application"] == "unknown"
    if realization == "mismatch":
        assert issue_at(result, "/request_application/constraint_changes/0")
    retained("bound_readback_" + defect, payloads, result)


@pytest.mark.parametrize("objective", ["model_default", "single_reaction"])
@pytest.mark.parametrize("defect,realization", [(None, "exact"), ("direction", "mismatch"),
    ("coefficient", "mismatch"), ("missing_constant", "unknown"),
    ("incomplete_terms", "unknown"), ("missing_and_wrong", "mismatch")])
def test_objective_choice_uses_original_and_effective_readback(captures, objective, defect, realization):
    payloads, expected = synthetic_bundle(captures, objective=objective)
    if defect:
        def alter(problem):
            obj = problem["effective"]["objective"]
            if defect == "direction":
                obj["direction"] = "max"  # original normalized engineering fixture is min
            elif defect in {"coefficient", "missing_and_wrong"}:
                obj["terms"][0]["coefficient"] = number(9, "/effective/objective/terms/0/coefficient/value", "effective_problem")
            if defect in {"missing_constant", "missing_and_wrong"}:
                obj["native_constant"] = missing()
            elif defect == "incomplete_terms":
                obj["terms_complete"] = False
                problem["effective"]["representation"] = "partial"
        edit_role(payloads, expected, "effective_problem", alter)
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native"]["request_realization"] == realization
    assert result["native"]["objective_application"] == (("model_default" if objective == "model_default" else "applied") if defect is None else "unknown")


@pytest.mark.parametrize("defect,realization", [("mismatch", "mismatch"), ("missing", "unknown")])
def test_supported_option_uses_actual_configuration_readback(captures, defect, realization):
    payloads, expected = synthetic_bundle(captures, options={"integrality_tolerance": 1e-6})
    edit_role(payloads, expected, "effective_problem", lambda p: p["configuration_before_solve"].update(
        integrality_tolerance=missing() if defect == "missing" else number(1e-5,
            "/configuration_before_solve/integrality_tolerance/value", "effective_problem")))
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native"]["request_realization"] == realization
    assert result["native"]["objective_application"] == "model_default"


def no_solve(payloads, expected):
    payloads["solution"] = {"file": None, "bytes": None, "state": "absent"}
    update_manifest(payloads, expected)


def test_rejected_unsupported_optimality_and_partial_application_preserve_rows(captures):
    requests = [change("IN", -10, 8), change("AB", 0, "inf"), change("OUT", 0, "inf")]
    payloads, expected = synthetic_bundle(captures, constraints=requests)
    no_solve(payloads, expected)
    def alter(manifest):
        application = manifest["request_application"]
        application["constraint_changes"][1].update(application="rejected", issue_code="constraint_rejected")
        application["constraint_changes"][2].update(application="not_attempted")
        application.update(objective_application="not_attempted", request_realization="mismatch")
        manifest.update(solve_call_count=0, execution_outcome="failed", request_realization="mismatch")
    edit_role(payloads, expected, "manifest", alter)
    result = parse_fba_capture(payloads, expected=expected)
    assert [row["application"] for row in result["native"]["constraint_changes"]] == ["applied", "rejected", "not_attempted"]
    assert result["native"]["objective_application"] == "not_attempted"
    assert result["native"]["solve_call_count"] == 0 and result["native"]["request_realization"] == "mismatch"
    retained("partial_application", payloads, result)
    payloads, expected = synthetic_bundle(captures, options={"optimality_tolerance": 1e-6})
    no_solve(payloads, expected)
    def reject(manifest):
        application = manifest["request_application"]
        application.update(objective_application="not_attempted", request_realization="mismatch")
        application["solver_option_applications"][1].update(application="rejected", issue_code="solver_option_unsupported", effective_source=None)
        manifest.update(solve_call_count=0, execution_outcome="failed", request_realization="mismatch")
    edit_role(payloads, expected, "manifest", reject)
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native"]["solve_call_count"] == 0 and result["native"]["request_realization"] == "mismatch"
    assert result["native"]["objective_application"] == "not_attempted"


@pytest.mark.parametrize("defect", ["shape", "bound_role", "aggregate"])
def test_malformed_application_preserves_other_native_facts(captures, defect):
    payloads, expected = synthetic_bundle(captures, constraints=[change("IN", -10, 8)])
    def alter(manifest):
        if defect == "shape":
            del manifest["request_application"]["objective_request"]
        elif defect == "bound_role":
            manifest["request_application"]["constraint_changes"][0]["requested_lower"]["source"]["role"] = []
        else:
            manifest["request_realization"] = "unknown"
    edit_role(payloads, expected, "manifest", alter)
    before = deepcopy(payloads)
    result = parse_fba_capture(payloads, expected=expected)
    assert payloads == before
    assert result["native"]["solve_call_count"] == 1 and result["native"]["solver"]["status"] == "optimal"
    assert result["native"]["request_realization"] == ("mismatch" if defect == "aggregate" else "unknown")
    assert len(result["models"]["effective"]["reactions"]) == 3
    assert len(result["problems"]["effective"]["variables"]) == 7
    assert len(result["native_solution"]["native"]["variable_values"]) == 7


@pytest.mark.parametrize("defect", ["missing", "digest"])
def test_application_without_bound_selected_request_cannot_certify_original(captures, defect):
    payloads, expected = synthetic_bundle(captures)
    if defect == "missing":
        payloads["selected_request"] = {"file": None, "bytes": None, "state": "absent"}
        update_manifest(payloads, expected)
    else:
        expected["requested_job_sha256"] = "9" * 64
    result = parse_fba_capture(payloads, expected=expected)
    assert result["original_request_file"] is None
    assert result["native"]["objective_request"] is None
    assert result["native"]["constraint_changes"] is None
    assert result["native"]["request_realization"] == "unknown"
    assert len(result["native_solution"]["native"]["variable_values"]) == 7


def test_new_evidence_populates_same_saved_sheet_and_calculator_without_io(captures, tmp_path, monkeypatch):
    payloads, expected = synthetic_bundle(captures, constraints=[change("IN", -10, 8)])
    model = json.loads(payloads["effective_model"]["bytes"])
    model["source_audit"] = audit()
    model["effective"]["native_capture_evidence"] = {"opaque": {"artifact_ref": "not-authority", "sha256": "a" * 64, "size_bytes": 0, "format": "raw"}}
    replace_role(payloads, "effective_model", model)
    update_manifest(payloads, expected)
    before = deepcopy(payloads)
    def forbidden(*args, **kwargs):
        raise AssertionError("supplied-byte evidence or saved calculator attempted external work")
    with monkeypatch.context() as guarded:
        for owner, name in ((builtins, "open"), (io, "open"), (os, "open"), (Path, "open"),
                            (socket, "socket"), (socket, "create_connection"),
                            (subprocess, "Popen"), (subprocess, "run"), (builtins, "__import__")):
            guarded.setattr(owner, name, forbidden)
        result = parse_fba_capture(payloads, expected=expected)
        sheet = populate_flux_balance_sheet(bundle=result)
    assert payloads == before
    path = tmp_path / "synthetic_sheet689.json"
    path.write_bytes(encode(sheet))
    saved = json.loads(path.read_bytes())
    original = deepcopy(saved)
    settings = parameters(saved)
    with monkeypatch.context() as guarded:
        for owner, name in ((builtins, "open"), (io, "open"), (os, "open"), (Path, "open"),
                            (socket, "socket"), (socket, "create_connection"),
                            (subprocess, "Popen"), (subprocess, "run"), (builtins, "__import__")):
            guarded.setattr(owner, name, forbidden)
        calculated = calculate_flux_balance_sheet(saved, parameters=settings)
    assert saved == original
    assert calculated["objective"]["native_basis_calculated"]["value"] == -4.25
    assert calculated["objective"]["full_calculated"]["value"] == -2.75
    assert calculated["active_count"] == 3
    assert saved["native"]["constraint_changes"][0]["application"] == "applied"
    assert saved["models"]["source_audit"]["xml_elements"][1]["text"] == ""
    retained("saved_sheet_no_io", payloads, {"sheet": saved, "calculations": calculated})


def test_opaque_earlier_pass_getters_do_not_replace_unestablished_final_point(captures):
    payload = deepcopy(captures["solution"])
    payload["point_state"] = "not_established"
    evidence = {"native_passes": [{"raw_getters": {"primal": 7, "objective": -4.25}}],
                "raw_getters": {"primal": 0, "status": "UNDEF"}}
    payload["native_capture_evidence"] = deepcopy(evidence)
    result = parse_solution(payload, captures)
    assert result["native"]["point_state"] == "not_established"
    assert result["native"]["variable_values"] == result["native"]["reaction_values"] == []
    assert result["native"]["native_capture_evidence"] == evidence


@pytest.mark.parametrize("raw_status,status", [("numeric", "numerical_failure"), ("UNRECOGNIZED", "unknown")])
def test_reader_uses_shared_status_normalization_without_manifest(captures, raw_status, status):
    payloads, expected = bundle(captures)
    payloads["manifest"] = {"file": None, "bytes": None, "state": "absent"}
    solution = json.loads(payloads["solution"]["bytes"])
    solution["optlang_status"] = raw_status
    replace_role(payloads, "solution", solution)
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native"]["solver"]["raw_status"] == raw_status
    assert result["native"]["solver"]["status"] == status


def test_g4_external_prior_source_is_preserved_as_unresolved_association(captures):
    payloads, expected = synthetic_bundle(captures, constraints=[change("IN", -10, 8)])
    external = {"artifact_ref": "external_prior_not_in_eight_roles", "sha256": "8" * 64,
                "size_bytes": 12, "format": "retained_prior_fixture"}
    def add_prior(job):
        job["constraints"][0]["lower"]["source"] = {"file": external, "pointer": "/prior/lower"}
    select(payloads, expected, add_prior)
    before = deepcopy(payloads)
    result = parse_fba_capture(payloads, expected=expected)
    assert payloads == before
    assert result["original_request_file"] is None
    assert result["native"]["request_realization"] == "unknown"
    assert result["native"]["constraint_changes"] is None
    assert any(row["code"] == "artifact_identity_conflict" for row in result["issues"])
    assert len(result["native_solution"]["native"]["variable_values"]) == 7


@pytest.mark.parametrize("later", [1e-5, None], ids=["later_changed", "later_unavailable"])
def test_later_configuration_does_not_rewrite_before_solve_application(captures, later):
    payloads, expected = synthetic_bundle(captures, options={"feasibility_tolerance": 1e-6})
    captured = missing() if later is None else number(later,
        "/configuration_after_solve/feasibility_tolerance/value", "solution")
    edit_role(payloads, expected, "solution", lambda s: s["configuration_after_solve"].update(
        feasibility_tolerance=deepcopy(captured)))
    edit_role(payloads, expected, "manifest", lambda m: m["actual_solver"].update(
        feasibility_tolerance=deepcopy(captured)))
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native"]["request_realization"] == "exact"
    assert result["problems"]["configuration_before_solve"]["feasibility_tolerance"]["value"] == 1e-6
    assert result["native_solution"]["native"]["configuration_after_solve"]["feasibility_tolerance"]["value"] == later
    assert result["native"]["solver"]["feasibility_tolerance"]["value"] == later


@pytest.mark.parametrize("value", [0, 1, 2])
def test_matching_out_of_range_readback_cannot_establish_supported_option(value, captures):
    payloads, expected = synthetic_bundle(captures, options={"feasibility_tolerance": value})
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native"]["request_realization"] == "mismatch"
    assert issue_at(result, "/request_application/solver_option_applications/0")


@pytest.mark.parametrize("field", ["unrequested_reaction_bound", "native_row", "stoichiometry"])
def test_unrequested_original_effective_change_cannot_establish_exact(field, captures):
    payloads, expected = synthetic_bundle(captures)
    if field == "unrequested_reaction_bound":
        edit_role(payloads, expected, "effective_model", lambda m: m["effective"]["reactions"][0].update(
            upper=bound(9, "/effective/reactions/0/upper/value")))
    elif field == "native_row":
        edit_role(payloads, expected, "effective_problem", lambda p: p["effective"]["constraints"][0].update(
            constant=number(3, "/effective/constraints/0/constant/value", "effective_problem")))
    else:
        edit_role(payloads, expected, "effective_model", lambda m: m["effective"]["stoichiometry"][0].update(
            coefficient=number(3, "/effective/stoichiometry/0/coefficient/value")))
    result = parse_fba_capture(payloads, expected=expected)
    assert result["native"]["request_realization"] == "mismatch"
    assert issue_at(result, "/request_application/selected_request")
