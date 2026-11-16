"""Custody faults and actual selected native modes under the bounded test worker."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from gene_annotation_episode.episodic_workflow.root.library import native_infernal_preparation_driver as driver
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_infernal_contracts import native_infernal_digest
from gene_annotation_episode.episodic_workflow.root.library.native_infernal_preparation_contracts import (
    requested_job_from_infernal_preparation,
)


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "gene_annotation_episode/episodic_workflow/root/a107/tests/fixtures/infernal_preparation/compiled/NATIVE_COMPILED_INDEX_001.json"
INDEX = json.loads(INDEX_PATH.read_text())
CASES = INDEX["cases"]
POLICY = LocalJobPolicy(5 * 1024 ** 3, 4 * 1024 ** 3)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_job(program, mode):
    case = next(c for c in CASES if (c["program"], c["mode"]) == (program, mode))
    path = ROOT / case["request_path"]
    assert digest(path) == case["request_sha256"]
    return json.loads(path.read_bytes())


def make_plan(tmp_path, selected=None):
    selected = native_job("cmconvert", "ascii") if selected is None else selected
    request = requested_job_from_infernal_preparation(selected)
    return {"version": driver.PLAN_VERSION, "identity": {"run_id": "producer251-test",
        "episode_id": "selected-local-child", "resource_id": "local", "execution_id": str(tmp_path / "native.json"),
        "operation_key": "selected-command", "attempt_id": native_infernal_digest("selected-command"),
        "requested_job_sha256": native_infernal_digest(request)}, "requested_job": request,
        "attempt_directory": str(tmp_path / "infernal-preparation-attempt"), "policy": POLICY.to_dict()}


def synthetic_plan(tmp_path, program="cmconvert", mode="ascii"):
    selected = native_job(program, mode)
    for row in selected["operands"]:
        path = tmp_path / (row["role"] + "-" + str(row["ordinal"]))
        path.write_bytes(Path(row["path"]).read_bytes())
        row["path"] = str(path)
    executable = tmp_path / "synthetic-executable"
    executable.write_bytes(b"Synthetic process boundary fixture; never executed.\n")
    executable.chmod(0o700)
    selected["software"].update(executable=str(executable), sha256=digest(executable), engine_version="synthetic")
    return make_plan(tmp_path, selected)


def reseal(plan):
    plan["requested_job"] = requested_job_from_infernal_preparation(plan["requested_job"]["native_infernal_preparation"])
    plan["identity"]["requested_job_sha256"] = native_infernal_digest(plan["requested_job"])
    return plan


def fake_native(monkeypatch, plan, *, returncode=0, callback=None, outputs=True):
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        kwargs["stdout"].write(b"synthetic stdout\n")
        if outputs:
            for output in plan["requested_job"]["native_infernal_preparation"]["outputs"]:
                if output["role"] not in {"stdout", "stderr"}:
                    (kwargs["cwd"] / output["relative_path"]).write_bytes(b"synthetic retained output\n")
        if callback:
            callback(argv, kwargs)
        return subprocess.CompletedProcess(argv, returncode)
    monkeypatch.setattr(driver.subprocess, "run", run)
    return calls


def test_exact_cli_operand_count():
    with pytest.raises(ValueError, match="exact_plan_file_operand_required"):
        driver.main([])
    with pytest.raises(ValueError, match="exact_plan_file_operand_required"):
        driver.main(["one", "two"])
