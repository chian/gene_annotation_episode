from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_rna_structure_contracts import POLICY, RUN_PLAN_FILENAME
from gene_annotation_episode.native_rna_structure_local import prepare_local_rna_structure, local_rna_structure_plan
from gene_annotation_episode.practical_execution_state import _read
from test_native_rna_structure_contracts import plan


def reservation(tmp_path):
    selected, assignment, root = plan(tmp_path)
    state = SimpleNamespace(run_id="run", episode_id="local", assignment=assignment)
    return selected, state, root


def test_prepare_only_reserves_and_repeated_preparation_keeps_original_handle(tmp_path, monkeypatch):
    selected, state, root = reservation(tmp_path)
    monkeypatch.setattr(native_lifecycle, "start_prepared", lambda *a, **k: pytest.fail("preparation started native work"))
    handle = prepare_local_rna_structure(state, "selected-operation", root=root, policy=LocalJobPolicy(**POLICY))
    original = handle.path.read_bytes()
    assert handle.read()["stage"] == "prepared" and not Path(selected["attempt_directory"]).exists()
    assert _read(root / RUN_PLAN_FILENAME) == selected
    assert local_rna_structure_plan(state.assignment, str(handle.path)) == selected
    again = prepare_local_rna_structure(state, "selected-operation", root=root, policy=LocalJobPolicy(**POLICY))
    assert again.path == handle.path and again.path.read_bytes() == original


def test_selected_shared_lifecycle_start_produces_terminal_bundle(tmp_path):
    selected, state, root = reservation(tmp_path)
    handle = prepare_local_rna_structure(state, "selected-operation", root=root, policy=LocalJobPolicy(**POLICY))
    assert handle.read()["stage"] == "prepared"
    native_lifecycle.start_prepared(handle)
    result = native_lifecycle.wait_job(handle)
    assert result.returncode == 0
    assert local_rna_structure_plan(state.assignment, str(handle.path)) == selected
    bundle = _read(Path(selected["attempt_directory"]) / "bundle.json")
    assert bundle["native_status"] == "complete" and bundle["identity"] == selected["identity"]
    (root / "test-native-receipt.json").write_text(json.dumps({"returncode": result.returncode, "metadata": result.metadata}, indent=2) + "\n")


@pytest.mark.parametrize("change", [lambda a: a.update(resource_id="wrong"), lambda a: a.update(resource_kind="hpc"),
    lambda a: a.update(workspace=a["workspace"] + "-elsewhere")])
def test_reservation_cannot_be_rebound_to_other_assignment(tmp_path, change):
    selected, state, root = reservation(tmp_path)
    handle = prepare_local_rna_structure(state, "selected-operation", root=root, policy=LocalJobPolicy(**POLICY))
    wrong = deepcopy(state.assignment)
    change(wrong)
    with pytest.raises(ValueError):
        local_rna_structure_plan(wrong, str(handle.path))


@pytest.mark.parametrize("key", ["command", "cwd", "stdout"])
def test_changed_native_reservation_rejected_before_use(tmp_path, key):
    selected, state, root = reservation(tmp_path)
    handle = prepare_local_rna_structure(state, "selected-operation", root=root, policy=LocalJobPolicy(**POLICY))
    original = handle.read()
    original[key] = ["changed"] if key == "command" else "/changed"
    handle.path.write_text(json.dumps(original))
    with pytest.raises(ValueError, match="rna_original_attempt_mismatch"):
        local_rna_structure_plan(state.assignment, str(handle.path))


def test_changed_lifecycle_request_digest_or_environment_is_rejected(tmp_path):
    selected, state, root = reservation(tmp_path)
    handle = prepare_local_rna_structure(state, "selected-operation", root=root, policy=LocalJobPolicy(**POLICY))
    request_path = Path(handle.read()["paths"]["request"])
    request = json.loads(request_path.read_bytes())
    request["env"]["TMPDIR"] = "/outside"
    request_path.write_text(json.dumps(request))
    with pytest.raises(ValueError, match="rna_original_attempt_mismatch"):
        local_rna_structure_plan(state.assignment, str(handle.path))


def test_wrong_policy_or_operation_directory_does_not_reserve(tmp_path):
    selected, state, root = reservation(tmp_path)
    with pytest.raises(ValueError):
        prepare_local_rna_structure(state, "selected-operation", root=root, policy=LocalJobPolicy(1024, 1024))
    with pytest.raises(ValueError):
        prepare_local_rna_structure(state, "different-operation", root=root, policy=LocalJobPolicy(**POLICY))
    assert not (root / "native.json").exists()
