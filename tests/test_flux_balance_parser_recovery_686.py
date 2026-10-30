"""006 recovery cases in TEST-normalized retained 677 records; no new solve.

These deliberately malformed fixtures exercise supplied-byte recovery only.
Original array indices are independent of scientific entity/source-record
positions. The four original 684 reproductions remain in their unchanged file.
"""
from copy import deepcopy
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.flux_balance_contracts import validate_flux_balance_record
from gene_annotation_episode.flux_balance_readers import (
    parse_cobra_glpk_model_capture, parse_cobra_glpk_problem_capture,
    parse_cobra_glpk_solution_capture, parse_fba_capture,
)
from test_flux_balance_readers_680 import (
    bundle, captures, encode, file, location, missing, number, parsed,
)


def relocated(row, before, after):
    """Relocate only this synthetic row's own addresses when inserting a row."""
    row = deepcopy(row)

    def visit(value):
        if type(value) is dict:
            for key, item in value.items():
                if (key == "pointer" or key.endswith("_pointer")) and type(item) is str:
                    if item == before or item.startswith(before + "/"):
                        value[key] = after + item[len(before):]
                else:
                    visit(item)
        elif type(value) is list:
            for item in value:
                visit(item)
    visit(row)
    return row


def prepend_malformed(payload, field):
    path = "/effective/" + field
    payload["effective"][field] = [{}] + [relocated(row, f"{path}/{i}", f"{path}/{i + 1}")
        for i, row in enumerate(payload["effective"][field])]


def retain(name, supplied, result):
    attempt = os.environ.get("HMMER529_ATTEMPT")
    if attempt:
        Path(attempt, f"fba686_{name}.json").write_text(json.dumps({
            "fixture_identity": "controlled malformed TEST-normalized retained 677 records; no new solve or production capture",
            "supplied": supplied, "returned": result, "caller_bytes_unchanged": True,
        }, indent=2, allow_nan=False) + "\n")


def read_payload(payload, captures, kind, *, models=None, name):
    before = deepcopy(payload)
    raw = encode(payload)
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    source = file(raw, payload["version"])
    if kind == "models":
        result = parse_cobra_glpk_model_capture(raw, source=source, original_model=captures["files"]["original_model"])
        record = "ParsedModelSnapshots"
    elif kind == "problems":
        models = parsed(captures)[0] if models is None else models
        result = parse_cobra_glpk_problem_capture(raw, source=source, models=models)
        record = "ParsedProblemSnapshots"
    else:
        result = parse_cobra_glpk_solution_capture(raw, source=source, problem=parsed(captures)[1]["effective"])
        record = "ParsedNativeSolution"
    assert payload == before and encode(payload) == raw
    assert hashlib.sha256(raw).hexdigest() == raw_sha256
    assert validate_flux_balance_record(record, result) == result
    retain(name, payload, result)
    return result


def located(result, payload, code, pointer, index, **positions):
    issues = [issue for issue in result["issues"] if issue["code"] == code and issue["field"] == pointer]
    assert len(issues) == 1, result["issues"]
    issue = issues[0]
    assert issue["source_row_index"] == index
    assert all(issue[key] == value for key, value in positions.items())
    # Every asserted locator resolves in the ORIGINAL supplied document.
    value = payload
    for token in pointer[1:].split("/"):
        value = value[int(token)] if type(value) is list else value[token]
    return value


def group(position=0):
    return {"position": position, "id": f"group{position}", "name": None, "kind": "collection",
            "members": [], "annotation_pointer": None, "notes_pointer": None}


def test_source_join_array_index_is_neither_loaded_nor_source_record_position(captures):
    payload = deepcopy(captures["models"])
    payload["source_to_loaded_ids"] = [{},
        {"kind": "reaction", "source_record_index": 41, "source_id": "R_OUT", "loaded_id": "WRONG",
         "loaded_position": 2, "state": "mapped", "source": location("original_model", "")},
        {"kind": "reaction", "source_record_index": 81, "source_id": "R_IN", "loaded_id": "IN",
         "loaded_position": 0, "state": "mapped", "source": location("original_model", "")}]
    result = read_payload(payload, captures, "models", name="source_join_positions")
    located(result, payload, "model_identity_conflict", "/source_to_loaded_ids/1", 1)
    assert [(row["source_record_index"], row["loaded_position"]) for row in result["source_to_loaded_ids"]] == [(81, 0)]
    assert result["effective"]["population"]["completeness"] == "complete"
    assert result["loaded_original"]["population"]["completeness"] == "complete"


@pytest.mark.parametrize("field", ["compartments", "genes", "metabolites", "reactions", "groups"])
def test_model_population_rejection_keeps_original_row_index(captures, field):
    payload = deepcopy(captures["models"])
    if field == "groups":
        payload["effective"]["groups"] = [group()]
        payload["effective"]["population"]["groups"] = 1
    expected = payload["effective"]["population"][field]
    assert expected > 0
    prepend_malformed(payload, field)
    rows = payload["effective"][field]
    outside = relocated(rows[-1], f"/effective/{field}/{len(rows) - 1}", f"/effective/{field}/{len(rows)}")
    outside.update(position=expected, id="outside_population")
    rows.append(outside)
    result = read_payload(payload, captures, "models", name="model_population_" + field)
    located(result, payload, "model_identity_conflict", f"/effective/{field}/{expected + 1}", expected + 1)
    assert [row["position"] for row in result["effective"][field]] == list(range(expected))
    assert result["effective"]["population"][field] == expected
    assert result["effective"]["population"]["completeness"] == "partial"
    assert result["loaded_original"]["population"]["completeness"] == "complete"


@pytest.mark.parametrize("field", ["gene_positions", "compartment_position", "stoichiometry", "medium", "group_members"])
def test_model_relationship_rejection_keeps_original_nested_path(captures, field):
    payload = deepcopy(captures["models"])
    model = payload["effective"]
    positions = {}
    if field == "gene_positions":
        prepend_malformed(payload, "reactions")
        model["reactions"][3]["gene_positions"] = [999]
        pointer, index = "/effective/reactions/3/gene_positions", 3
        positions = {"reaction_position": 2}
    elif field == "compartment_position":
        prepend_malformed(payload, "metabolites")
        model["metabolites"][2]["compartment_position"] = 999
        pointer, index = "/effective/metabolites/2/compartment_position", 2
        positions = {"metabolite_position": 1}
    elif field == "stoichiometry":
        prepend_malformed(payload, "stoichiometry")
        model["stoichiometry"][2]["reaction_position"] = 999
        pointer, index = "/effective/stoichiometry/2", 2
        positions = {"reaction_position": 999, "metabolite_position": 0}
    elif field == "medium":
        model["medium"] = [{}] + [{"reaction_position": position,
            "native_value": number(7, f"/effective/medium/{index}/native_value/value"),
            "native_meaning": "cobra_medium_entry", "source": location("effective_model", f"/effective/medium/{index}")}
            for index, position in ((1, 999), (2, 0))]
        pointer, index = "/effective/medium/1", 1
        positions = {"reaction_position": 999}
    else:
        model["groups"] = [{}, {}, group()]
        model["population"]["groups"] = 1
        model["groups"][2]["members"] = [
            {"kind": "reaction", "position": 0, "id": "IN"},
            {"kind": "reaction", "position": 2, "id": "WRONG"},
            {"kind": "reaction", "position": 1, "id": "AB"}]
        pointer, index = "/effective/groups/2/members/1", 1
    result = read_payload(payload, captures, "models", name="model_relationship_" + field)
    located(result, payload, "model_identity_conflict", pointer, index, **positions)
    effective = result["effective"]
    assert effective["population"] == {**model["population"], "completeness": "partial"}
    assert [row["position"] for row in effective["reactions"]] == [0, 1, 2]
    assert result["loaded_original"]["population"]["completeness"] == "complete"
    if field == "gene_positions":
        assert effective["reactions"][2]["gene_positions"] == []
    elif field == "compartment_position":
        assert [row["position"] for row in effective["metabolites"]] == [0]
    elif field == "stoichiometry":
        assert [(row["metabolite_position"], row["reaction_position"]) for row in effective["stoichiometry"]] == [(0, 0), (1, 1), (1, 2)]
    elif field == "medium":
        assert [(row["reaction_position"], row["native_value"]["value"]) for row in effective["medium"]] == [(0, 7)]
    else:
        assert [row["id"] for row in effective["groups"][0]["members"]] == ["IN", "AB"]


@pytest.mark.parametrize("field", ["variables", "constraints"])
@pytest.mark.parametrize("malformed_predecessor", [True, False], ids=["filtered_predecessor", "no_predecessor"])
def test_problem_population_rejection_keeps_original_row_index(captures, field, malformed_predecessor):
    payload = deepcopy(captures["problems"])
    count_key = field[:-1] + "_count"
    expected = payload["effective"][count_key]
    if malformed_predecessor:
        prepend_malformed(payload, field)
    rows = payload["effective"][field]
    original_index = len(rows)
    outside = relocated(rows[-1], f"/effective/{field}/{len(rows) - 1}", f"/effective/{field}/{len(rows)}")
    outside.update(position=expected, native_index=expected + 1, optlang_position=expected, id="outside_population")
    rows.append(outside)
    result = read_payload(payload, captures, "problems", name=f"problem_population_{field}_{malformed_predecessor}")
    located(result, payload, "schema_invalid", f"/effective/{field}/{original_index}", original_index,
            **{field[:-1] + "_position": expected})
    assert result["effective"][count_key] == expected
    assert [row["position"] for row in result["effective"][field]] == list(range(expected))
    # Keep the established representation policy: filtering an extra row alone
    # leaves a full expected population; a malformed predecessor marks partial.
    assert result["effective"]["representation"] == ("partial" if malformed_predecessor else "complete_continuous_linear")
    assert result["loaded_original"]["representation"] == "complete_continuous_linear"


@pytest.mark.parametrize("kind", ["constraint", "objective"])
def test_sparse_term_error_keeps_original_expression_and_term_indices(captures, kind):
    payload = deepcopy(captures["problems"])
    prepend_malformed(payload, "constraints")
    # A second filtering step rejects both duplicate constraint identities.
    duplicate = relocated(payload["effective"]["constraints"][1], "/effective/constraints/1", "/effective/constraints/6")
    payload["effective"]["constraints"].append(duplicate)
    path = "/effective/constraints/4" if kind == "constraint" else "/effective/objective"
    expression = payload["effective"]["constraints"][4] if kind == "constraint" else payload["effective"]["objective"]
    expression["terms"] = [{"variable_position": position,
        "coefficient": number(coefficient, f"{path}/terms/{i}/coefficient/value", "effective_problem")}
        for i, (position, coefficient) in enumerate(((0, 1), (9, -1), (4, 2)))]
    expression["terms"][0]["coefficient"]["value"] = True
    result = read_payload(payload, captures, "problems", name="sparse_indices_" + kind)
    located(result, payload, "variable_identity_conflict", path + "/terms/1", 1,
            variable_position=9, constraint_position=3 if kind == "constraint" else None)
    assert [row["position"] for row in result["effective"]["constraints"]] == [1, 2, 3, 4]
    retained = next(row for row in result["effective"]["constraints"] if row["position"] == 3) if kind == "constraint" else result["effective"]["objective"]
    assert retained["terms_complete"] is False
    assert [(term["variable_position"], term["coefficient"]["value"]) for term in retained["terms"]] == [(4, 2)]
    assert retained["terms"][0]["coefficient"]["source"]["pointer"] == path + "/terms/2/coefficient/value"
    assert result["effective"]["constraint_count"] == 5
    assert result["loaded_original"]["representation"] == "complete_continuous_linear"


def test_cross_model_joins_keep_indices_after_two_earlier_filters(captures):
    payload = deepcopy(captures["problems"])
    prepend_malformed(payload, "reaction_variables")
    payload["effective"]["reaction_variables"][1]["forward_variable_id"] = "WRONG"
    payload["effective"]["reaction_variables"][3]["reaction_id"] = "WRONG"
    prepend_malformed(payload, "constraints")
    payload["effective"]["constraints"][1]["native_index"] = True
    payload["effective"]["constraints"][2]["metabolite_position"] = 999
    result = read_payload(payload, captures, "problems", name="cross_model_joins")
    located(result, payload, "variable_identity_conflict", "/effective/reaction_variables/1", 1, reaction_position=0)
    located(result, payload, "flux_identity_conflict", "/effective/reaction_variables/3", 3, reaction_position=2)
    located(result, payload, "constraint_identity_conflict", "/effective/constraints/2", 2,
            constraint_position=1, metabolite_position=999)
    assert [row["reaction_position"] for row in result["effective"]["reaction_variables"]] == [1]
    assert [row["position"] for row in result["effective"]["constraints"]] == [2, 3, 4]
    assert len(result["effective"]["variables"]) == result["effective"]["variable_count"] == 7
    assert result["effective"]["constraint_count"] == 5
    assert result["loaded_original"]["representation"] == "complete_continuous_linear"


def test_missing_partial_model_join_uses_original_problem_array_index(captures):
    model_payload = deepcopy(captures["models"])
    model_payload["effective"]["reactions"][2]["lower"]["value"] = True
    models = read_payload(model_payload, captures, "models", name="missing_model_reaction")
    payload = deepcopy(captures["problems"])
    prepend_malformed(payload, "reaction_variables")
    result = read_payload(payload, captures, "problems", models=models, name="partial_model_join")
    located(result, payload, "partial_population", "/effective/reaction_variables/3", 3, reaction_position=2)
    assert [row["reaction_position"] for row in result["effective"]["reaction_variables"]] == [0, 1, 2]
    assert result["effective"]["representation"] == "partial"


@pytest.mark.parametrize("role,code", [([], "schema_invalid"), ({}, "schema_invalid"), ("unbound", "artifact_missing")], ids=["list", "object", "unknown_string"])
@pytest.mark.parametrize("address_kind", ["pointer", "identity"])
def test_bad_role_type_is_located_at_the_address_and_other_data_survive(captures, role, code, address_kind):
    payload = deepcopy(captures["solution"])
    if address_kind == "pointer":
        payload["variable_values"][0]["primal"]["source"] = {"role": role, "pointer": "/variable_values/0/primal/value"}
        path, positions = "/variable_values/0/primal/source/role", {"variable_position": 0}
    else:
        issue = {"code": "source_precision_unknown", "stage": "capture", "field": None,
            "source_row_index": None, "reaction_position": None, "metabolite_position": None,
            "variable_position": None, "constraint_position": None, "detail_file": None}
        payload["issues"] = [deepcopy(issue), deepcopy(issue)]
        payload["issues"][0]["detail_file"] = {"role": role,
            "identity": {key: captures["files"]["effective_problem"][key] for key in ("sha256", "size_bytes")}}
        path, positions = "/issues/0/detail_file/role", {}
    result = read_payload(payload, captures, "solution", name=f"role_{address_kind}_{type(role).__name__}")
    located(result, payload, code, path, 0, **positions)
    assert [row["variable_position"] for row in result["native"]["variable_values"]] == list(range(1 if address_kind == "pointer" else 0, 7))
    assert [row["flux"]["value"] for row in result["native"]["reaction_values"]] == [7, 6, 6]
    assert len(result["native"]["constraint_values"]) == 5
    assert result["native"]["native_glpk_objective"]["value"] == -4.25
    assert result["native"]["native_cobra_objective"]["value"] == -2.75
    assert result["native"]["optlang_status"] == "optimal"
    if address_kind == "identity":
        assert issue in result["native"]["issues"]


def changed_bundle(captures, update):
    supplied = deepcopy(captures)
    update(supplied)
    for role, key in (("effective_model", "models"), ("effective_problem", "problems"), ("solution", "solution")):
        supplied["raw"][role] = encode(supplied[key])
        supplied["files"][role] = file(supplied["raw"][role], supplied[key]["version"])
    return bundle(supplied)


@pytest.mark.parametrize("point_state", ["basic_solution", "not_established"])
def test_bundle_solution_model_join_keeps_row_index_after_solution_filters(captures, point_state):
    def update(supplied):
        supplied["problems"]["effective"] = None
        solution = supplied["solution"]
        solution["point_state"] = point_state
        solution["reaction_values"][2]["reaction_position"] = 9
        if point_state == "basic_solution":
            solution["reaction_values"][0]["flux"]["value"] = True
            solution["reaction_values"][2]["flux"]["source"]["pointer"] = ""
        else:
            for row in solution["reaction_values"][1:]:
                row["flux"] = missing()
    payloads, expected = changed_bundle(captures, update)
    before = deepcopy(payloads)
    result = parse_fba_capture(payloads, expected=expected)
    assert payloads == before
    source = json.loads(payloads["solution"]["bytes"])
    located(result["native_solution"], source, "flux_identity_conflict", "/reaction_values/2", 2, reaction_position=9)
    assert [row["reaction_position"] for row in result["native_solution"]["native"]["reaction_values"]] == [1]
    assert [row["flux"]["value"] for row in result["native"]["flux_rows"]] == [7, 6, 6]
    assert result["native_solution"]["native"]["point_state"] == point_state
    assert result["problems"]["loaded_original"]["representation"] == "complete_continuous_linear"
    retain("bundle_model_join_" + point_state, source, result)


def test_recovery_bundle_uses_no_files_network_subprocess_or_imports(captures, monkeypatch):
    def update(supplied):
        supplied["solution"]["variable_values"][0]["primal"]["source"]["role"] = []
        prepend_malformed(supplied["problems"], "reaction_variables")
        supplied["problems"]["effective"]["reaction_variables"][3]["reaction_id"] = "WRONG"
    payloads, expected = changed_bundle(captures, update)
    before = deepcopy(payloads)

    def forbidden(*args, **kwargs):
        raise AssertionError("supplied-byte recovery attempted external work")

    with monkeypatch.context() as guarded:
        for owner, name in ((builtins, "open"), (io, "open"), (os, "open"), (Path, "open"),
                            (socket, "socket"), (socket, "create_connection"),
                            (subprocess, "Popen"), (subprocess, "run"), (builtins, "__import__")):
            guarded.setattr(owner, name, forbidden)
        result = parse_fba_capture(payloads, expected=expected)
    assert payloads == before
    assert result["native_solution"]["native"]["variable_values"][0]["variable_position"] == 1
    assert len(result["native_solution"]["native"]["variable_values"]) == 6
    assert result["problems"]["effective"]["variable_count"] == 7
    assert result["problems"]["effective"]["constraint_count"] == 5
    assert [row["flux"]["value"] for row in result["native"]["flux_rows"]] == [7, 6, 6]
