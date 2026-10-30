"""FBA admission preserves selection and cannot fall into generic execution."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_execution_records import ASSIGNMENT_SCHEMA, validate_assignment
from gene_annotation_episode.native_flux_balance_contracts import POLICY

pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")
SELECTION = {"version": "flux_balance_execution_selection_v1",
    "environment_realization": "operation_scoped_tmp_and_cache_v1"}
FIXTURE = Path(__file__).resolve().parents[1] / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check151c_producer688/producer-emissions/sbml/selected-plan.json"


@pytest.fixture
def assignment(tmp_path):
    job = json.loads(FIXTURE.read_text())["requested_job"]
    return {"version": "practical_assignment_v1", "assignment_id": "selected-fba-assignment",
        "resource_kind": "local", "resource_id": "selected-local", "workspace": str(tmp_path),
        "endpoint": "usable_handoff", "requested_job": job,
        "progress_requirements": [{"key": "handoff", "credit": 1,
            "predicate": {"kind": "requested_job_handoff"}}], "completion_keys": ["handoff"],
        "initial_context": {"revision": 0, "cwd": str(tmp_path), "environment": {}},
        "inventory_snapshot": {}, "constraints": {"allocation": deepcopy(POLICY)}}


@pytest.mark.parametrize("explicit", [False, True])
def test_original_job_and_assignment_remain_exact_detached(assignment, explicit):
    if explicit: assignment["native_flux_balance_execution"] = deepcopy(SELECTION)
    before = deepcopy(assignment)
    validated = validate_assignment(assignment)
    assert validated == before and assignment == before
    Draft202012Validator.check_schema(ASSIGNMENT_SCHEMA)
    assert Draft202012Validator(ASSIGNMENT_SCHEMA).is_valid(validated)
    validated["requested_job"]["environment"]["TMPDIR"] = "/changed"
    if explicit: validated["native_flux_balance_execution"]["version"] = "changed"
    assert assignment == before


@pytest.mark.parametrize("selection", [None, False, True, [], {},
    {**SELECTION, "extra": True}, {**SELECTION, "environment_realization": "automatic"},
    {**SELECTION, "version": "flux_balance_execution_selection_v2"}])
def test_invalid_environment_realization_is_rejected(assignment, selection):
    assignment["native_flux_balance_execution"] = selection
    with pytest.raises(ValueError, match="fba_environment_selection_invalid"):
        validate_assignment(assignment)
    assert not Draft202012Validator(ASSIGNMENT_SCHEMA).is_valid(assignment)


def test_selection_cannot_attach_to_generic_job(assignment):
    assignment["requested_job"] = {"argv": ["/selected/generic"], "environment": {}}
    assert validate_assignment(assignment) == assignment
    assert Draft202012Validator(ASSIGNMENT_SCHEMA).is_valid(assignment)
    assignment["native_flux_balance_execution"] = deepcopy(SELECTION)
    with pytest.raises(ValueError, match="fba_environment_selection_invalid"):
        validate_assignment(assignment)
    assert not Draft202012Validator(ASSIGNMENT_SCHEMA).is_valid(assignment)


@pytest.mark.parametrize("fault", ["hpc", "missing_resource", "empty_resource", "changed_job", "extra_job"])
def test_admission_cannot_substitute_resource_or_requested_job(assignment, fault):
    if fault == "hpc": assignment["resource_kind"] = "hpc"
    elif fault == "missing_resource": del assignment["resource_id"]
    elif fault == "empty_resource": assignment["resource_id"] = ""
    elif fault == "changed_job": assignment["requested_job"]["environment"]["OMP_NUM_THREADS"] = "8"
    else: assignment["requested_job"]["other_native_job"] = {}
    with pytest.raises(ValueError): validate_assignment(assignment)


def test_admitted_shape_cannot_enter_unbound_generic_local_execution(assignment, monkeypatch):
    operations = LocalPracticalOperations({"kind": "local", "workspace": assignment["workspace"], "policy": POLICY})
    selected = validate_assignment(assignment)
    from gene_annotation_episode import native_lifecycle
    def forbidden(*args, **kwargs): raise AssertionError("unbound FBA attempted dispatch")
    monkeypatch.setattr(native_lifecycle, "prepare_job", forbidden)
    monkeypatch.setattr(native_lifecycle, "start_prepared", forbidden)
    monkeypatch.setattr(native_lifecycle, "resume_start", forbidden)
    with pytest.raises(ValueError, match="native_flux_balance_operation_mode_software_format_not_bound"):
        operations.initial_outcome(selected)
    class State:
        assignment = selected
        def context(self): forbidden()
    with pytest.raises(ValueError, match="native_flux_balance_operation_mode_software_format_not_bound"):
        operations._execute(State(), "practical.job.start", {}, "selected-child-action")
