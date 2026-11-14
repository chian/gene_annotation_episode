"""Pure saved-record/current-identity controls; no LUMPY or native dispatch.

The original SR plan, seal and command controls are copied without alteration.
Their old thread environment is historical data and is never used to execute a
process. Current metadata deliberately supplies no thread-count ceiling.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.library import native_lumpy_execution as native
from gene_annotation_episode.episodic_workflow.root.library import native_lumpy_host as host


FIXTURES = Path(__file__).parent / "fixtures" / "lumpy_saved_driver_identity"
LEGACY = "gene_annotation_episode.native_lumpy_execution"
CURRENT = "gene_annotation_episode.episodic_workflow.root.library.native_lumpy_execution"
CURRENT_MODULES = (
    CURRENT,
    "gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_reference",
    "gene_annotation_episode.__init__",
    "gene_annotation_episode.episodic_workflow.__init__",
    "gene_annotation_episode.episodic_workflow.root.__init__",
    "gene_annotation_episode.episodic_workflow.root.library.__init__",
)
THREAD_METADATA = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS")


def original(name):
    return json.loads((FIXTURES / name).read_bytes())


@pytest.fixture(autouse=True)
def no_native_execution_or_original_path_reopen(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("pure identity control entered an execution or retained-path read port")
    for name in ("run_lumpy", "_regular", "_directory", "_read_control", "_verify_native_runtime"):
        monkeypatch.setattr(native, name, forbidden)
    for name in ("_regular", "_directory", "_read_control"):
        monkeypatch.setattr(host, name, forbidden)
    monkeypatch.setattr(native.subprocess, "run", forbidden)


def current_requested():
    """A current metadata proposal, explicitly not a physical-runtime witness."""
    selected = deepcopy(original("plan.json")["requested_job"])
    runtime = selected["native_lumpy"]["software"]["driver_runtime"]
    runtime["module_root"] = str(Path(native.__file__).resolve().parents[4])
    sources = native._current_module_sources(runtime["module_root"])
    assert set(CURRENT_MODULES) <= set(sources)
    assert not {
        "gene_annotation_episode.native_lifecycle",
        "gene_annotation_episode.episodic_workflow.root.library.native_lumpy_host",
        "gene_annotation_episode.episodic_workflow.root.library.native_lumpy_observations",
        "gene_annotation_episode.episodic_workflow.root.library.native_lumpy_software",
    }.intersection(sources)
    runtime["implementation_files"] = [
        {"module": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for name, path in sorted(sources.items())
    ]
    environment = selected["environment"]
    for name in THREAD_METADATA:
        environment.pop(name, None)
    environment["PYTHONPATH"] = os.pathsep.join(
        [runtime["module_root"], *native.shared._dependency_roots(runtime)])
    return native.requested_job_from_lumpy(selected["native_lumpy"], environment=environment)


def current_plan(selected):
    """Engineered current-policy proposal, never an authenticated old plan."""
    plan = deepcopy(original("plan.json"))
    plan["policy"] = deepcopy(native.POLICY)
    plan["requested_job"] = selected
    plan["identity"]["requested_job_sha256"] = native.digest(selected)
    return native.validate_lumpy_run_plan(plan)


def test_authentic_old_sr_records_retain_identity_and_existing_policy_rejection():
    plan, seal = original("plan.json"), original("seal.json")
    handle = original("handle.json")
    request = (FIXTURES / "request.json").read_bytes()
    # These actual old records predate the original validator's current policy.
    # Retain their bytes and rejection; never turn the obsolete field into a
    # current configuration or relabel the old success as current acceptance.
    assert set(plan["policy"]) - set(native.POLICY) == {"wall_seconds"}
    assert plan["policy"]["wall_seconds"] is None
    assert handle["metadata"]["policy"] == plan["policy"]
    assert hashlib.sha256(request).hexdigest() == handle["request_sha256"]
    assert json.loads(request)["command"] == handle["command"]
    assert plan["requested_job"]["argv"][4] == handle["command"][4] == LEGACY
    assert native.validate_lumpy_requested_job(plan["requested_job"]) == plan["requested_job"]
    assert seal["outcome"] == "succeeded" and seal["returncode"] == 0
    with pytest.raises(ValueError, match="^invalid_lumpy_runplan$"):
        native.validate_lumpy_run_plan(plan)
    with pytest.raises(ValueError, match="^invalid_lumpy_runplan$"):
        native.validate_lumpy_seal(seal, plan=plan)
    with pytest.raises(ValueError, match="^invalid_lumpy_runplan$"):
        host.validate_lumpy_original_controls(plan, handle, request)


@pytest.mark.parametrize("defect", ["command", "missing_driver", "missing_reference", "extra_argument"])
def test_saved_identity_cannot_be_relabelled_or_lose_its_required_sources(defect):
    selected = original("plan.json")["requested_job"]
    modules = selected["native_lumpy"]["software"]["driver_runtime"]["implementation_files"]
    if defect == "command":
        selected["argv"][4] = CURRENT
    elif defect == "extra_argument":
        selected["argv"].append("--unselected")
    else:
        excluded = LEGACY if defect == "missing_driver" else "gene_annotation_episode.native_atac_differential_reference"
        modules[:] = [row for row in modules if row["module"] != excluded]
    with pytest.raises(ValueError):
        native.validate_lumpy_requested_job(selected)


def test_legacy_supplied_extra_module_preserves_original_command_interpretation():
    selected = original("plan.json")["requested_job"]
    runtime = selected["native_lumpy"]["software"]["driver_runtime"]
    runtime["implementation_files"].append({"module": CURRENT,
        "sha256": hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest()})
    assert native.validate_lumpy_requested_job(selected) == selected
    assert native.requested_job_from_lumpy(selected["native_lumpy"],
        environment=selected["environment"])["argv"] == selected["argv"]
    assert selected["argv"][4] == LEGACY


def test_current_metadata_selects_the_actual_private_driver_without_new_thread_ceilings():
    selected = current_requested()
    assert selected["argv"][1:] == ["-B", "-S", "-m", CURRENT, "lumpy-plan.json"]
    assert native.validate_lumpy_requested_job(selected) == selected
    assert not set(THREAD_METADATA).intersection(selected["environment"])
    plan = current_plan(selected)
    assert native.lumpy_command_argv(plan) == original("seal.json")["argv"]
    assert not set(THREAD_METADATA).intersection(native._native_environment(plan))


@pytest.mark.parametrize("missing", [CURRENT_MODULES[0], CURRENT_MODULES[1], CURRENT_MODULES[4]])
def test_current_metadata_requires_driver_reference_and_package_startup_identity(missing):
    selected = current_requested()
    modules = selected["native_lumpy"]["software"]["driver_runtime"]["implementation_files"]
    modules[:] = [row for row in modules if row["module"] != missing]
    with pytest.raises(ValueError):
        native.validate_lumpy_requested_job(selected)


def test_current_inventory_cannot_claim_the_legacy_driver_command():
    selected = current_requested()
    selected["argv"][4] = LEGACY
    with pytest.raises(ValueError):
        native.validate_lumpy_requested_job(selected)


@pytest.mark.parametrize("value", [None, "7"])
def test_current_environment_does_not_require_a_thread_count(value):
    selected = current_requested()
    if value is not None:
        selected["environment"].update({name: value for name in THREAD_METADATA})
    assert native.validate_lumpy_requested_job(selected) == selected
    plan = current_plan(selected)
    assert not set(THREAD_METADATA).intersection(native._native_environment(plan))
    assert not set(THREAD_METADATA).intersection(native._driver_environment(plan))
