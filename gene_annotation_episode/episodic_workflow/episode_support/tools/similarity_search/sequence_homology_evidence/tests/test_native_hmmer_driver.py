"""Synthetic process faults and custody checks; real native runs are retained separately."""
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_hmmer_contracts import native_hmmer_digest, requested_job_from_native
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.native_hmmer_driver import main, run_native_hmmer, validate_native_hmmer_bundle_files
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.tests.test_native_hmmer_contracts import job_for


FIXTURES = Path(__file__).resolve().parents[7] / "gene_annotation_episode/episodic_workflow/episode_support/readers/similarity_search/tests/fixtures/hmmer_search"
HMM = FIXTURES / "model.hmm"
FASTA = FIXTURES / "query.fa"


def plan_for(tmp_path, program="hmmsearch"):
    job = job_for(program)
    executable = tmp_path / "selected-executable"
    executable.write_text("synthetic test executable; subprocess is replaced by a test fixture\n")
    executable.chmod(0o700)
    job["software"] = {"executable": str(executable), "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(), "engine_version": "synthetic-test"}
    for row in job["operands"]:
        source = HMM if row["format"] == "hmmer3_ascii" else FASTA
        if row["role"].startswith("profile_database_h3"):
            source = Path(str(HMM) + "." + row["role"].rsplit("_", 1)[1])
        row.update(path=str(source), size_bytes=source.stat().st_size, sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    request = requested_job_from_native(job)
    return {"version": "native_hmmer_run_plan", "identity": {"run_id": "synthetic-run", "episode_id": "resource-child",
        "resource_id": "local", "execution_id": "original-execution", "attempt_id": "attempt-one",
        "operation_key": "selected-start", "requested_job_sha256": native_hmmer_digest(request)},
        "requested_job": request, "attempt_directory": str(tmp_path / "attempt"),
        "policy": {'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4 * 1024 ** 3}}


def fake_native(monkeypatch, *, returncode=0, tables=True):
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        kwargs["stdout"].write(b"synthetic complete retained stdout\n[ok]\n")
        kwargs["stderr"].write(b"native diagnostic retained\n")
        for flag in ("--tblout", "--domtblout"):
            if tables and flag in argv:
                Path(argv[argv.index(flag) + 1]).write_bytes(b"# no hits in synthetic native table\n")
        if "--chkhmm" in argv:
            prefix = argv[argv.index("--chkhmm")+1]
            Path(prefix + "-1.hmm").write_bytes(b"model one\n")
            Path(prefix + "-2.hmm").write_bytes(b"model two\n")
        return subprocess.CompletedProcess(argv, returncode)
    monkeypatch.setattr("gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.native_hmmer_driver.subprocess.run", run)
    return calls


def seal(plan):
    plan["identity"]["requested_job_sha256"] = native_hmmer_digest(plan["requested_job"])
    return plan


def test_exact_cli_operand_and_existing_unowned_directory(tmp_path):
    with pytest.raises(ValueError, match="exact_plan_file_operand"):
        main([])
    plan = plan_for(tmp_path)
    Path(plan["attempt_directory"]).mkdir()
    with pytest.raises(ValueError, match="not_exclusively_owned"):
        run_native_hmmer(plan)
