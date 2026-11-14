"""Current worker route/reservation controls; every native launch port is stopped.

Public-module records below are explicitly supplied transport controls and are
validated by the unchanged original custodian. They are not historical native
execution receipts. Scientific numerical work is never executed by this suite.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import molecular_measurement_tools as original
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.local_jobs import LocalJobPolicy, LocalJobResult
from gene_annotation_episode.episodic_workflow.root import tool_native_sequence as current
from gene_annotation_episode.episodic_workflow.root.library import ordinary_scientific_worker_ports
from . import original_scientific_native_sequence as oracle
from .test_molecular_worker_boundary import observe, StopBeforeProcess


ROUTES = (
    ("protein_conservation_native", "muscle_alignment_driver", "muscle_alignment_driver"),
    ("protein_conservation_result", "protein_conservation_result_worker", "protein_conservation_result_worker"),
    ("protein_phylogeny_iqtree_native", "iqtree_phylogeny_driver", "iqtree_phylogeny_driver"),
    ("protein_phylogeny_result", "protein_phylogeny_result_worker", "protein_phylogeny_result_worker"),
    ("macs2_peak_result", "sequence_analysis_worker", "sequence_worker"),
    ("somatic_variant_native", "somatic_variant_driver", "somatic_variant_driver"),
    ("somatic_variant_result", "somatic_variant_result_worker", "somatic_variant_result_worker"),
    ("homer_motif_result", "native_homer_worker", "native_homer_worker"),
    ("tf_binding_native", "tf_binding_driver", "tf_binding_driver"),
    ("tf_binding_result", "tf_binding_result_worker", "tf_binding_result_worker"),
    ("itc_binding", "physical_measurement_worker", "sequence_worker"),
    ("liftover_point", "physical_measurement_worker", "sequence_worker"),
    ("circular_dichroism", "physical_measurement_worker", "sequence_worker"),
)


@pytest.mark.parametrize("operation,private_program,public_program", ROUTES,
    ids=[row[0] for row in ROUTES])
def test_current_route_replays_actual_and_supplied_public_reservations(tmp_path, monkeypatch,
        operation, private_program, public_program):
    value = observe(tmp_path, monkeypatch, operation, "current")
    path = value.directory / "execution-selection.json"
    before = path.read_bytes()
    selected = json.loads(before)
    assert selected["command"][2] == "gene_annotation_episode.episodic_workflow.root.library." + private_program
    assert selected["request"] == {"operation": operation, "arguments": value.payload}
    assert selected["implementation_files"]
    for pin in selected["implementation_files"]:
        assert hashlib.sha256(Path(pin["path"]).read_bytes()).hexdigest() == pin["sha256"]
    request_before = (value.directory / "worker-request.json").read_bytes()
    value.host.local_job_policy = LocalJobPolicy(memory_bytes=256 * 1024 ** 2, scratch_bytes=128 * 1024 ** 2)
    with pytest.raises(StopBeforeProcess) as caught:
        value.root_call()
    assert caught.value is value.failure and len(value.calls) == 2
    assert path.read_bytes() == before
    assert value.calls[1][0] == value.calls[0][0] == selected["command"]
    assert value.calls[1][1]["policy"].to_dict() == value.policy.to_dict()

    # Explicit supplied original-module control: source pins remain actual and
    # unchanged; original validation, rather than an invented schema, admits it.
    selected["command"][2] = "gene_annotation_episode." + public_program
    path.write_text(json.dumps(selected))
    supplied = path.read_bytes()
    with pytest.raises(StopBeforeProcess) as caught:
        original.run_owned_molecular_worker(operation, deepcopy(value.payload), directory=value.directory,
            owned_directory=value.directory, policy=value.host.local_job_policy, cancel_event=None)
    assert caught.value is value.failure and len(value.calls) == 3
    with pytest.raises(StopBeforeProcess) as caught:
        value.root_call()
    assert caught.value is value.failure and len(value.calls) == 4
    assert path.read_bytes() == supplied
    assert value.calls[2][0] == value.calls[3][0] == selected["command"]
    assert value.calls[3][1]["policy"].to_dict() == value.policy.to_dict()
    assert (value.directory / "worker-request.json").read_bytes() == request_before
    selected["command"][2] = "unassigned.worker"
    path.write_text(json.dumps(selected))
    with pytest.raises(ContractError, match="^molecular_tool_execution_selection_conflict$"):
        value.root_call()
    assert len(value.calls) == 4 and not (value.directory / "native-handle.json").exists()




