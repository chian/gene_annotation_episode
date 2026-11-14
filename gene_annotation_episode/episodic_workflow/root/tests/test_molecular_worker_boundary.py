"""Actual Root selection/custodian boundary; no native process or scientific claim.

The only substituted process port is prepare_job, which raises the same
injected exception before creating a handle. Source files, immutable reservation,
original/candidate command validation and the async Root caller are real.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import molecular_measurement_tools as original
from gene_annotation_episode import molecular_sequence_native as original_native
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.tool_native_sequence import ToolNativeSequence
from gene_annotation_episode.episodic_workflow.root.library import molecular_sequence_native as current_native
from gene_annotation_episode.episodic_workflow.root.library import molecular_sequence_driver as driver


OPERATIONS = ("protein_disorder", "arsenic_speciation", "protease_kinetics_saved")


class StopBeforeProcess(RuntimeError):
    pass


def arguments(operation, directory):
    if operation != "protease_kinetics_saved":
        # The process custodian transports copied JSON; no scientific worker
        # consumes these deliberately labelled transport-only operands.
        return {"request": {"controlled_transport_only": True}}
    path = directory / "supplied-transport-file.json"
    path.write_bytes(b"{}")
    return {"request": {"version": driver.REQUEST_VERSION_V2, "mode": "saved_sheet",
        "attempt_identity": {"run_id": "control", "episode_id": "control",
            "resource_id": "ordinary_saved_calculation", "operation_key": "control:0",
            "execution_id": str(directory / "native-handle.json")},
        "selection": {"operation": "analyze_protease_kinetics", "sheet_file": {
            "path": str(path), "sha256": hashlib.sha256(b"{}").hexdigest(), "size_bytes": 2}},
        "scientific_context": None}}


def observe(tmp_path, monkeypatch, operation, layout):
    directory = tmp_path / "owned"
    directory.mkdir()
    payload = arguments(operation, directory)
    policy = LocalJobPolicy(memory_bytes=128 * 1024 ** 2, scratch_bytes=64 * 1024 ** 2)
    host = SimpleNamespace(store=SimpleNamespace(db=SimpleNamespace(in_transaction=False)), local_job_policy=policy)
    calls, failure = [], StopBeforeProcess("no process was prepared")

    def prepare(command, **options):
        calls.append((list(command), dict(options)))
        raise failure

    monkeypatch.setattr(native_lifecycle, "prepare_job", prepare)
    for name in ("resume_start", "wait_job", "collect"):
        monkeypatch.setattr(native_lifecycle, name, lambda *a, **k: pytest.fail("process port must remain unreachable"))

    def root_call():
        return asyncio.run(ToolNativeSequence._sequence_worker_async(host, operation, deepcopy(payload),
            directory=directory, owned_directory=directory))

    with pytest.raises(StopBeforeProcess) as caught:
        if layout == "legacy":
            original.run_owned_molecular_worker(operation, deepcopy(payload), directory=directory,
                owned_directory=directory, policy=policy, cancel_event=None)
        else:
            root_call()
    assert caught.value is failure and len(calls) == 1
    return SimpleNamespace(directory=directory, payload=payload, policy=policy, host=host,
        calls=calls, failure=failure, root_call=root_call)


@pytest.mark.parametrize("operation,layout", [(operation, layout) for operation in OPERATIONS
    for layout in ("legacy", "current")], ids=[operation + "-" + layout for operation in OPERATIONS
    for layout in ("legacy", "current")])
def test_actual_root_route_preserves_recorded_reservation_and_policy(tmp_path, monkeypatch, operation, layout):
    value = observe(tmp_path, monkeypatch, operation, layout)
    path = value.directory / "execution-selection.json"
    before = path.read_bytes()
    selected = json.loads(before)
    program = "molecular_sequence_driver" if operation == "protease_kinetics_saved" else "sequence_worker"
    prefix = "gene_annotation_episode." + ("episodic_workflow.root.library." if layout == "current" else "")
    index = 3 if operation == "protease_kinetics_saved" else 2
    assert selected["command"][index] == prefix + program
    assert selected["request"] == {"operation": operation, "arguments": value.payload}
    assert selected["implementation_files"]
    for item in selected["implementation_files"]:
        assert hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() == item["sha256"]
    request_before = (value.directory / "worker-request.json").read_bytes()
    value.host.local_job_policy = LocalJobPolicy(memory_bytes=256 * 1024 ** 2, scratch_bytes=128 * 1024 ** 2)
    with pytest.raises(StopBeforeProcess) as caught:
        value.root_call()
    assert caught.value is value.failure and len(value.calls) == 2
    assert path.read_bytes() == before
    assert (value.directory / "worker-request.json").read_bytes() == request_before
    assert value.calls[1][0] == value.calls[0][0] == selected["command"]
    assert value.calls[1][1]["policy"].to_dict() == value.policy.to_dict()
    assert not (value.directory / "native-handle.json").exists()


@pytest.mark.parametrize("operation", ["protein_disorder", "protease_kinetics_saved"])
def test_changed_module_is_rejected_before_process_port(tmp_path, monkeypatch, operation):
    value = observe(tmp_path, monkeypatch, operation, "current")
    path = value.directory / "execution-selection.json"
    selected = json.loads(path.read_bytes())
    selected["command"][3 if operation == "protease_kinetics_saved" else 2] = "unassigned.worker"
    path.write_text(json.dumps(selected))
    with pytest.raises(ContractError, match="^molecular_tool_execution_selection_conflict$"):
        value.root_call()
    assert len(value.calls) == 1 and not (value.directory / "native-handle.json").exists()


def test_actual_native_error_is_caught_by_original_public_type():
    with pytest.raises(original_native._BoundaryError) as caught:
        current_native._fail("explicit_boundary_control", "/selection")
    assert type(caught.value) is original_native._BoundaryError
    assert caught.value.code == "molecular_sequence_explicit_boundary_control"
    assert type(caught.value).__module__ == "gene_annotation_episode.molecular_sequence_native"
