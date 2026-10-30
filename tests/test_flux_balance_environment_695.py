"""Explicit environment realization and failed-attempt replay; no native solve."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.native_flux_balance_contracts import (
    ATTEMPT_DIRECTORY_NAME, ENVIRONMENT_FILENAME, OWNER_FILENAME, STARTED_FILENAME,
    bind_flux_balance_environment, flux_balance_driver_argv,
    validate_flux_balance_environment_binding, validate_flux_balance_run_plan,
)

pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")
SELECTION = {"version": "flux_balance_execution_selection_v1",
             "environment_realization": "operation_scoped_tmp_and_cache_v1"}
RELOCATED = ("TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME", "PIP_CACHE_DIR")
FIXTURE = (Path(__file__).resolve().parents[1] / "verification" /
    "tool_graders_hmmer_map_verification_2026-10-28_529/check151c_producer688/producer-emissions/sbml/selected-plan.json")


@pytest.fixture
def saved_plan():
    # Exact previously emitted selection. This is not another native execution.
    return json.loads(FIXTURE.read_text())


def _v2(saved_plan, tmp_path):
    plan = deepcopy(saved_plan)
    identity = plan["identity"]
    identity.update(run_id="environment695", episode_id="local-selected", operation_key="child-selected-start")
    identity["attempt_id"] = digest(identity["operation_key"])
    root = tmp_path / ".episode-operations" / digest({"run": identity["run_id"], "episode": identity["episode_id"]}) / identity["attempt_id"]
    identity["execution_id"] = str(root / "native.json")
    identity["assignment_sha256"] = digest({"fixture": "explicit-environment-selection", "selection": SELECTION})
    plan.update(version="flux_balance_run_plan_v2", attempt_directory=str(root / ATTEMPT_DIRECTORY_NAME))
    plan["environment_binding"] = bind_flux_balance_environment(plan["requested_job"],
        execution_id=identity["execution_id"], attempt_directory=plan["attempt_directory"], selection=SELECTION)
    return validate_flux_balance_run_plan(plan)


def test_original_v1_remains_literal_and_detached(saved_plan):
    original = deepcopy(saved_plan)
    assert validate_flux_balance_run_plan(saved_plan) == original
    binding = bind_flux_balance_environment(saved_plan["requested_job"], execution_id=saved_plan["identity"]["execution_id"],
        attempt_directory=saved_plan["attempt_directory"], selection=None)
    assert binding["selection"] is None
    assert all(row["selected"] == row["realized"] for row in binding["relocations"])
    assert saved_plan == original


def test_explicit_paths_preserve_request_and_every_other_operand(saved_plan, tmp_path):
    original = deepcopy(saved_plan)
    plan = _v2(saved_plan, tmp_path)
    binding = plan["environment_binding"]
    assert plan["requested_job"] == original["requested_job"]
    assert plan["identity"]["requested_job_sha256"] == digest(original["requested_job"])
    assert binding["requested_job_sha256"] == digest(original["requested_job"])
    assert [r["name"] for r in binding["relocations"]] == list(RELOCATED)
    assert {k for k in binding["requested_environment"] if binding["requested_environment"][k]
            != binding["realized_environment"][k]} == set(RELOCATED)
    root = str(Path(plan["identity"]["execution_id"]).parent)
    assert all(binding["realized_environment"][k] == root for k in RELOCATED[:3])
    assert binding["realized_environment"]["XDG_CACHE_HOME"] == plan["attempt_directory"] + "/cache"
    assert binding["realized_environment"]["PIP_CACHE_DIR"] == plan["attempt_directory"] + "/cache/pip"
    assert flux_balance_driver_argv(plan) == [*original["requested_job"]["argv"][:-1], root + "/flux-balance-plan.json"]
    result = validate_flux_balance_environment_binding(binding, requested_job=plan["requested_job"],
        execution_id=plan["identity"]["execution_id"], attempt_directory=plan["attempt_directory"], selection=SELECTION)
    result["relocations"][0]["selected"] = "changed-output"
    assert saved_plan == original and binding["relocations"][0]["selected"] != "changed-output"


@pytest.mark.parametrize("selection", [False, True, "automatic", [], {}, {**SELECTION, "extra": True},
    {**SELECTION, "environment_realization": "any_environment"}])
def test_invalid_selection(saved_plan, tmp_path, selection):
    plan = _v2(saved_plan, tmp_path)
    with pytest.raises(ValueError, match="fba_environment_selection_invalid"):
        bind_flux_balance_environment(plan["requested_job"], execution_id=plan["identity"]["execution_id"],
            attempt_directory=plan["attempt_directory"], selection=selection)


def test_missing_selection_cannot_move_paths(saved_plan, tmp_path):
    plan = _v2(saved_plan, tmp_path)
    with pytest.raises(ValueError, match="fba_runtime_environment_mismatch"):
        bind_flux_balance_environment(plan["requested_job"], execution_id=plan["identity"]["execution_id"],
            attempt_directory=plan["attempt_directory"], selection=None)
    plan["version"] = "flux_balance_run_plan_v1"
    del plan["environment_binding"]
    with pytest.raises(ValueError, match="fba_runtime_environment_mismatch"):
        validate_flux_balance_run_plan(plan)


@pytest.mark.parametrize("mutation", ["extra", "order", "requested", "realized", "digest", "selection"])
def test_binding_is_exact(saved_plan, tmp_path, mutation):
    plan = _v2(saved_plan, tmp_path)
    binding = plan["environment_binding"]
    if mutation == "extra": binding["extra"] = True
    elif mutation == "order": binding["relocations"].reverse()
    elif mutation == "requested": binding["requested_environment"]["TMP"] = "/different"
    elif mutation == "realized": binding["realized_environment"]["OMP_NUM_THREADS"] = "8"
    elif mutation == "digest": binding["requested_job_sha256"] = "0" * 64
    else: binding["selection"] = None
    with pytest.raises(ValueError, match="fba_environment_(binding_mismatch|selection_invalid)"):
        validate_flux_balance_run_plan(plan)


@pytest.mark.parametrize("field", ["PYTHONPATH", "OPENBLAS_NUM_THREADS", "XDG_CACHE_HOME"])
def test_original_environment_cannot_be_substituted(saved_plan, tmp_path, field):
    plan = _v2(saved_plan, tmp_path)
    plan["requested_job"]["environment"][field] = "/changed" if field != "OPENBLAS_NUM_THREADS" else "8"
    plan["identity"]["requested_job_sha256"] = digest(plan["requested_job"])
    with pytest.raises(ValueError, match="fba_runtime_environment_mismatch"):
        validate_flux_balance_run_plan(plan)


def test_closed_versions_and_original_attempt(saved_plan, tmp_path):
    v1 = deepcopy(saved_plan)
    v1["environment_binding"] = {}
    with pytest.raises(ValueError, match="fba_invalid_run_plan"):
        validate_flux_balance_run_plan(v1)
    plan = _v2(saved_plan, tmp_path)
    del plan["environment_binding"]
    with pytest.raises(ValueError, match="fba_invalid_run_plan"):
        validate_flux_balance_run_plan(plan)
    plan = _v2(saved_plan, tmp_path)
    plan["identity"]["operation_key"] = "different-child-decision"
    with pytest.raises(ValueError, match="fba_original_attempt_mismatch"):
        validate_flux_balance_run_plan(plan)


def _failed_attempt(saved_plan, tmp_path, monkeypatch, mismatch=False):
    from gene_annotation_episode import native_flux_balance_driver as driver
    plan = _v2(saved_plan, tmp_path)
    for k, v in plan["environment_binding"]["realized_environment"].items(): monkeypatch.setenv(k, v)
    monkeypatch.setenv("UNSELECTED_ENV_695", "must not be retained")
    if mismatch: monkeypatch.delenv("TMP", raising=False)
    def stop_before_native(*args, **kwargs):
        raise ValueError("controlled_software_unavailable_695")
    def no_model(*args, **kwargs):
        raise AssertionError("environment tests cannot load or optimize a model")
    monkeypatch.setattr(driver, "_verify_software", stop_before_native)
    monkeypatch.setattr(driver.capture, "_load_model", no_model)
    manifest = driver.run_flux_balance_native(plan)
    assert manifest["solve_call_count"] == 0 and manifest["execution_outcome"] == "failed"
    return driver, plan, manifest


@pytest.mark.parametrize("mismatch", [False, True])
def test_actual_environment_control_and_closed_replay(saved_plan, tmp_path, monkeypatch, mismatch):
    driver, plan, manifest = _failed_attempt(saved_plan, tmp_path, monkeypatch, mismatch)
    root = Path(plan["attempt_directory"])
    observation = json.loads((root / ENVIRONMENT_FILENAME).read_text())
    assert observation["plan_sha256"] == digest(plan)
    assert observation["expected_environment"] == plan["environment_binding"]["realized_environment"]
    assert set(observation["observed_environment"]) == set(observation["expected_environment"])
    assert observation["observed_environment"]["TMP"] == (None if mismatch else observation["expected_environment"]["TMP"])
    assert json.loads((root / STARTED_FILENAME).read_text())["environment_observation_sha256"] == digest(observation)
    assert json.loads((root / OWNER_FILENAME).read_text()) == plan
    assert json.loads((root / "outputs/selected-request.json").read_text())["requested_job"] == saved_plan["requested_job"]
    assert "UNSELECTED_ENV_695" not in observation["observed_environment"]
    log = (root / "outputs/native-log.txt").read_text()
    assert ("fba_runtime_environment_mismatch" in log) is mismatch
    before = {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    monkeypatch.setenv("TMP", "different replaying process")
    def forbidden(*args, **kwargs): raise AssertionError("replay may not verify software, load or optimize")
    monkeypatch.setattr(driver, "_verify_software", forbidden)
    assert driver.run_flux_balance_native(plan) == manifest
    assert before == {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("mutation", ["missing", "observed", "plan", "expected"])
def test_environment_control_must_match_original_start(saved_plan, tmp_path, monkeypatch, mutation):
    driver, plan, _ = _failed_attempt(saved_plan, tmp_path, monkeypatch)
    path = Path(plan["attempt_directory"]) / ENVIRONMENT_FILENAME
    if mutation == "missing": path.unlink()
    else:
        value = json.loads(path.read_text())
        if mutation == "observed": value["observed_environment"]["TMP"] = "tampered"
        elif mutation == "plan": value["plan_sha256"] = "0" * 64
        else: value["expected_environment"]["TMP"] = "tampered"
        path.chmod(0o600)
        path.write_text(json.dumps(value))
    with pytest.raises((ValueError, FileNotFoundError)):
        driver.run_flux_balance_native(plan)
