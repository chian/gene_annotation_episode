"""684 review reproductions against the unchanged supplied-byte parsers.

These intentionally assert the required recovery behavior; current failures are
review evidence, not a repaired implementation. The 680 helpers transform the
retained 677 diagnostic records for tests only. No solve or producer is invoked.
"""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from test_flux_balance_readers_680 import (
    captures, location, parse_model, parse_problem, parse_solution,
)


def observed(name, payload, invoke):
    """Retain the exact controlled payload and actual result before assertions."""
    supplied = deepcopy(payload)
    try:
        result = {"returned": invoke(payload)}
    except Exception as error:
        result = {"exception": {"type": type(error).__name__, "message": str(error)}}
    result["input_unchanged"] = supplied == payload
    attempt = os.environ.get("HMMER529_ATTEMPT")
    if attempt:
        Path(attempt, f"fba684_{name}.json").write_text(json.dumps({
            "fixture_identity": "controlled malformed input in TEST-normalized retained 677 records; no new solve",
            "input": supplied,
            "actual": result,
        }, indent=2, allow_nan=False) + "\n")
    return result


def test_model_join_issue_keeps_original_row_after_malformed_predecessor(captures):
    payload = deepcopy(captures["models"])
    payload["source_to_loaded_ids"] = [
        {},
        {"kind": "reaction", "source_record_index": 1, "source_id": "R_OUT",
         "loaded_id": "WRONG", "loaded_position": 2, "state": "mapped",
         "source": location("original_model", "")},
        {"kind": "reaction", "source_record_index": 2, "source_id": "R_IN",
         "loaded_id": "IN", "loaded_position": 0, "state": "mapped",
         "source": location("original_model", "")},
    ]
    actual = observed("model_join_index", payload, lambda value: parse_model(value, captures))
    assert "exception" not in actual, actual
    result = actual["returned"]
    assert actual["input_unchanged"]
    assert [(r["position"], r["id"]) for r in result["effective"]["reactions"]] == [(0, "IN"), (1, "AB"), (2, "OUT")]
    assert [(r["source_record_index"], r["loaded_position"], r["loaded_id"]) for r in result["source_to_loaded_ids"]] == [(2, 0, "IN")]
    conflicts = [row for row in result["issues"] if row["code"] == "model_identity_conflict"]
    assert len(conflicts) == 1
    assert conflicts[0]["source_row_index"] == 1, conflicts
    assert conflicts[0]["field"].startswith("/source_to_loaded_ids/1"), conflicts


def test_problem_join_issue_keeps_original_row_after_malformed_predecessor(captures):
    payload = deepcopy(captures["problems"])
    payload["effective"]["reaction_variables"][0]["forward_variable_position"] = True
    payload["effective"]["reaction_variables"][2]["forward_variable_id"] = "WRONG"
    actual = observed("problem_join_index", payload, lambda value: parse_problem(value, captures))
    assert "exception" not in actual, actual
    result = actual["returned"]
    assert actual["input_unchanged"]
    assert result["effective"]["representation"] == "partial"
    assert [r["position"] for r in result["effective"]["variables"]] == list(range(7))
    assert [r["position"] for r in result["effective"]["constraints"]] == list(range(5))
    assert [r["reaction_position"] for r in result["effective"]["reaction_variables"]] == [1]
    conflicts = [row for row in result["issues"] if row["code"] == "variable_identity_conflict" and row["reaction_position"] == 2]
    assert len(conflicts) == 1
    assert conflicts[0]["field"] == "/effective/reaction_variables/2", conflicts


@pytest.mark.parametrize("malformed_role", [[], {}], ids=["list", "object"])
def test_malformed_source_role_is_located_without_losing_independent_solution_rows(captures, malformed_role):
    payload = deepcopy(captures["solution"])
    payload["variable_values"][0]["primal"]["source"] = {
        "role": malformed_role, "pointer": "/variable_values/0/primal/value",
    }
    name = "source_role_" + type(malformed_role).__name__
    actual = observed(name, payload, lambda value: parse_solution(value, captures))
    assert "exception" not in actual, actual
    result = actual["returned"]
    assert actual["input_unchanged"]
    assert [r["variable_position"] for r in result["native"]["variable_values"]] == [1, 2, 3, 4, 5, 6]
    assert [r["reaction_position"] for r in result["native"]["reaction_values"]] == [0, 1, 2]
    assert len(result["native"]["constraint_values"]) == 5
    issues = [row for row in result["issues"] if row["variable_position"] == 0]
    assert any(row["code"] == "schema_invalid" and row["source_row_index"] == 0 and
               row["field"].startswith("/variable_values/0") for row in issues), issues
