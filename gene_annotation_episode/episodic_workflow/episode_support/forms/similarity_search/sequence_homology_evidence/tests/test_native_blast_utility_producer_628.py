"""Producer/custody engineering fixtures, not native BLAST measurements.

Every selected subprocess is replaced with an explicit controlled fixture here.
Native format evidence belongs to retained084/085 and separately selected runs.
"""
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import native_blast_utility_driver as driver
from gene_annotation_episode.episodic_workflow.episode_support.jobs.similarity_search.sequence_homology_evidence import native_blast_utility_local as local
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.similarity_search.sequence_homology_evidence import native_blast_utility_acquisition as acquisition
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.sequence_homology_evidence.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.native_blast_utility_contracts import ATTEMPT_NAME, BUNDLE_NAME, BUNDLE_VERSION, OWNER_NAME, PLAN_VERSION, database_file_selections, native_blast_digest, requested_job_from_native_blast_utility, staged_relative, validate_native_blast_utility_bundle, validate_native_blast_utility_plan
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.sequence_homology_evidence.native_worker_files import _atomic_new, _encoded
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.practical_execution_records import canonical
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.tests.test_blast_utility_contracts_625 import operation


POLICY = {'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4 * 1024 ** 3}
FAMILY = {"nhr": b"fixture header", "nin": b"fixture index", "nsq": b"fixture symbols",
          "ndb": b"fixture v5 member", "njs": b'{"fixture_only":true}', "future-member": b"retain this too"}


def identity(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data), "artifact_ref": None}


def job_fixture(tmp_path, mode="create_sequence_database"):
    source = tmp_path / "selected"
    software = identity(source / operation(mode)["program"], b"fixture software: never executed\n")
    Path(software["path"]).chmod(0o755)
    job = {"version": "native_blast_utility_job_v1", "operation": operation(mode),
        "software": {"executable": software["path"], "sha256": software["sha256"], "engine_version": "fixture-only"},
        "environment": {"BLAST_USAGE_REPORT": "false", "NCBI_DONT_USE_NCBIRC": "1"}, "inputs": [], "databases": [],
        "outputs": [{"role": "stdout", "path_kind": "file", "relative_path": "logs/native.stdout", "format": {
            "create_sequence_database": "text", "extract_sequences": "blastdbcmd_tabular_v1", "info": "blastdb_info_text",
            "metadata": "blastdb_metadata_json", "integrity": "blastdbcheck_text"}[mode]},
            {"role": "stderr", "path_kind": "file", "relative_path": "logs/native.stderr", "format": "text"}]}
    if mode == "create_sequence_database":
        fasta = identity(source / "supplied.fa", b">ALPHA\nACGTACGT\n")
        job["inputs"] = [{**fasta, "input_key": "source", "role": "sequence_input", "format": "fasta"}]
        job["outputs"].append({"role": "database_family", "path_kind": "prefix", "relative_path": "db/tiny", "format": "blastdb_family"})
    else:
        files = [identity(source / ("tiny." + suffix), data) for suffix, data in FAMILY.items()]
        receipt = identity(source / "receipt.json", b'{"fixture_only":"preparation"}')
        metadata = identity(source / "metadata.json", b'{"fixture_only":"metadata"}')
        inputs = identity(source / "input-manifest.json", b'{"fixture_only":"inputs"}')
        offline = identity(source / "offline.ini", b"fixture_only=true\n")
        provenance = {"source_ref": "source_fixture_only", "pointer": ""}
        db_identity = {"namespace": "fixture", "value": "tiny", "version": None, "release": None,
            "scope": None, "preparation_type": "sequence_database", "source": provenance}
        manifest = {"version": "native_blast_standard_prepared_database_manifest_v1", "database_key": "tiny",
            "kind": "blast_nucleotide_sequence", "identity": db_identity, "native_paths": [str(source / "tiny")],
            "files": [{k: v for k, v in f.items() if k != "artifact_ref"} for f in files],
            "preparation": {"method": "other_recorded", "preparation_type": "sequence_database",
                "software": {"name": "fixture-only", "version": None, "executable_sha256": None},
                "argv": None, "source": provenance, "input_manifest": inputs, "receipt": receipt},
            "metadata_manifests": [metadata], "access": {"mode": "prepared_local", "offline_configuration": offline},
            "inventory_complete": True}
        manifest_file = identity(source / "prepared.json", json.dumps(manifest, sort_keys=True).encode())
        job["databases"] = [{"database_key": "tiny", "role": "target", "kind": manifest["kind"], "identity": db_identity,
            "native_paths": manifest["native_paths"], "manifest_file": manifest_file, "manifest": manifest}]
    return job


def plan_fixture(tmp_path, job=None, *, root=None, operation_key="selected-operation"):
    job = job_fixture(tmp_path) if job is None else job
    request = requested_job_from_native_blast_utility(job)
    root = tmp_path / "reservation" if root is None else root
    root.mkdir(parents=True, exist_ok=True)
    return {"version": PLAN_VERSION, "identity": {"run_id": "run-fixture", "episode_id": "episode-fixture",
        "resource_id": "local-fixture", "execution_id": str(root / "native.json"),
        "attempt_id": native_blast_digest(operation_key), "operation_key": operation_key,
        "requested_job_sha256": native_blast_digest(request)}, "requested_job": request,
        "attempt_directory": str(root / ATTEMPT_NAME), "policy": deepcopy(POLICY)}


def test_plan_validation_is_detached_and_pure(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("pure plan validation performed IO")
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "resolve", forbidden)
    monkeypatch.setattr(driver.subprocess, "run", forbidden)
    result = validate_native_blast_utility_plan(plan)
    assert result == plan and result is not plan
    result["identity"]["run_id"] = "other"
    assert plan["identity"]["run_id"] == "run-fixture"


@pytest.mark.parametrize("change", [
    lambda p: p.update(unselected=True),
    lambda p: p["identity"].update(attempt_id="a" * 64),
    lambda p: p["identity"].update(requested_job_sha256="b" * 64),
    lambda p: p["identity"].update(execution_id="/other/native.json"),
    lambda p: p.update(attempt_directory="/other/blast-utility-attempt"),
    lambda p: p["policy"].update(memory_bytes=True),
    lambda p: p["policy"].update(scratch_bytes=0),
    lambda p: p["requested_job"]["argv"].append("-unselected"),
])
def test_plan_rejects_unselected_or_invalid_reservation(tmp_path, change):
    plan = plan_fixture(tmp_path)
    change(plan)
    with pytest.raises(ValueError):
        validate_native_blast_utility_plan(plan)


