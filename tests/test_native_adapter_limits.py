"""Operational native-job boundaries, using explicitly synthetic processes.

No fixture below is a PDF interpreter, covariance-model search, or scientific
result. The real runner executes these small processes to exercise adapter
resource propagation and preservation of ordinary native failures.
"""
import asyncio
from pathlib import Path
import json
import sqlite3
import sys

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.document_tools import pdf_native
from gene_annotation_episode.rna_evidence import local_configuration, run_cmsearch
from gene_annotation_episode import read_mapping


POLICY = {'memory_bytes': 256 * 1024 ** 2, 'scratch_bytes': 2 * 1024 ** 2}
MODEL = b"INFERNAL1/a [synthetic header]\nNAME synthetic\nCLEN 4\nALPH RNA\nCM\n//\n"


def synthetic_executable(tmp_path, *, kind, fail=False, wait_phase=None):
    path = tmp_path / (kind + "_synthetic.py")
    path.write_text(f"#!{sys.executable}\n" + """
from pathlib import Path
import sys
import time

KIND = """ + repr(kind) + "\nFAIL = " + repr(fail) + "\nWAIT_PHASE = " + repr(wait_phase) + """
args = sys.argv[1:]
phase = ("version" if args == ["-v"] or args == ["--version"] else "help" if args == ["-h"]
    else "index" if KIND == "mapper" and "-d" in args else "map" if KIND == "mapper" else "work")
if phase == WAIT_PHASE:
    if KIND == "mapper" and phase == "map":
        print("synthetic_query\\t4\\t0\\t4\\t+\\tsynthetic_reference\\t4\\t0\\t4\\t4\\t4\\t60\\tcg:Z:4M\\tcs:Z:=ACGT", flush=True)
    for i in range(8):
        Path('resource-test-'+str(i)).write_bytes(b'x' * 512000)
        time.sleep(.05)
if phase == "version":
    print("pdfinfo version synthetic" if KIND == "pdf" else "synthetic-process-not-minimap2")
elif phase == "help":
    print("# INFERNAL synthetic; controlled process fixture" if KIND == "cmsearch" else "Synthetic help; no mapping algorithm.")
elif KIND == "pdf":
    print("Pages: 1")
    sys.stderr.write("synthetic native diagnostic\\n")
    raise SystemExit(17 if FAIL else 0)
elif KIND == "cmsearch":
    Path(args[args.index("--tblout")+1]).write_bytes(b"# synthetic empty table\\n")
    print("synthetic native output")
    sys.stderr.write("synthetic native diagnostic\\n")
    raise SystemExit(17 if FAIL else 0)
elif "-d" in args:
    Path(args[args.index("-d")+1]).write_bytes(b"synthetic index\\n")
else:
    sys.stderr.write("synthetic native diagnostic\\n")
""")
    path.chmod(0o755)
    return path


@pytest.mark.parametrize("fail", [False, True])
def test_pdf_version_and_work_use_shared_policy_without_rewriting_native_failure(tmp_path, fail):
    executable = synthetic_executable(tmp_path, kind="pdf", fail=fail)
    source = tmp_path / "synthetic.pdf"
    source.write_bytes(b"explicitly not a PDF; process protocol fixture")
    result = pdf_native(source, operation="info", executables={"pdfinfo": executable}, job_limits=POLICY)
    assert result.metadata["job_limits"] == POLICY
    assert set(result.metadata["local_jobs"]) == {"version", "work"}
    assert all(job["policy"] == POLICY for job in result.metadata["local_jobs"].values())
    assert result.metadata["returncode"] == (17 if fail else 0)
    assert result.stdout == b"Pages: 1\n" and result.content == result.stdout
    assert result.stderr == b"synthetic native diagnostic\n"
    if not fail:
        assert result.metadata["page_count"] == 1


@pytest.mark.parametrize("fail", [False, True])
def test_cmsearch_help_and_work_keep_policy_and_native_output_meaning(tmp_path, fail):
    executable = synthetic_executable(tmp_path, kind="cmsearch", fail=fail)
    configured = local_configuration(executable=executable, cpu=0, job_limits=POLICY)
    result = run_cmsearch(sequence="ACGT", subject_ref="synthetic_subject", model=MODEL,
        model_ref="synthetic_model", configuration=configured)
    assert result.metadata["configuration"]["job_limits"] == POLICY
    assert set(result.metadata["local_jobs"]) == {"help", "work"}
    assert all(job["policy"] == POLICY for job in result.metadata["local_jobs"].values())
    assert result.metadata["returncode"] == (17 if fail else 0)
    assert result.stdout == b"synthetic native output\n"
    assert result.stderr == b"synthetic native diagnostic\n"
    assert result.table == b"# synthetic empty table\n"
    assert result.input_fasta == b">synthetic_subject\nACGT\n"
    command = result.metadata["command"]
    assert command[command.index("--cpu")+1] == "0"


@pytest.mark.parametrize("kind,phase", [("pdf", "version"), ("cmsearch", "work")])
def test_native_adapter_limit_is_reported_as_operational_failure(tmp_path, kind, phase):
    executable = synthetic_executable(tmp_path, kind=kind, wait_phase=phase)
    policy = {**POLICY, "scratch_bytes": 1024**2}
    with pytest.raises(AcquisitionError) as raised:
        if kind == "pdf":
            source = tmp_path / "synthetic.pdf"
            source.write_bytes(b"synthetic process fixture")
            pdf_native(source, operation="info", executables={"pdfinfo": executable}, job_limits=policy)
        else:
            run_cmsearch(sequence="ACGT", subject_ref="synthetic_subject", model=MODEL,
                model_ref="synthetic_model", configuration=local_configuration(executable=executable),
                job_limits=policy)
    assert raised.value.code == "local_job_resource_limit"
    assert raised.value.phase == "local_execution"


def test_mapper_uses_same_runner_for_all_native_phases_and_builds_index_inside_job(tmp_path, monkeypatch):
    executable = synthetic_executable(tmp_path, kind="mapper")
    directory = tmp_path / "job"
    directory.mkdir()
    (directory/"queries.fasta").write_bytes(b">synthetic_query\nACGT\n")
    (directory/"references.fasta").write_bytes(b">synthetic_reference\nACGT\n")
    # The empty synthetic mapping has no placements to project. This is a
    # runner integration test, not a substitute PAF/parser accuracy test.
    monkeypatch.setattr(read_mapping, "project_output", lambda directory: None)
    result = asyncio.run(read_mapping.run_mapping(directory,
        configuration=read_mapping.local_configuration(executable=executable,
            cache_dir=tmp_path/"cache", job_limits=POLICY), preset="map-ont"))
    assert result.metadata["configuration"]["job_limits"] == POLICY
    assert set(result.metadata["local_jobs"]) == {"version", "help", "index", "map"}
    assert all(job["policy"] == POLICY for job in result.metadata["local_jobs"].values())
    command = result.metadata["commands"]["index"]
    assert Path(command[command.index("-d")+1]).parent == directory
    assert len(list((tmp_path/"cache").glob("*.mmi"))) == 1
    assert result.metadata["returncode"] == 0


def test_mapper_resource_failure_retains_complete_valid_native_rows(tmp_path):
    executable = synthetic_executable(tmp_path, kind="mapper", wait_phase="map")
    directory = tmp_path / "job"
    directory.mkdir()
    (directory/"queries.fasta").write_bytes(b">synthetic_query\nACGT\n")
    (directory/"references.fasta").write_bytes(b">synthetic_reference\nACGT\n")
    with sqlite3.connect(directory/"operands.sqlite") as operands:
        operands.execute("CREATE TABLE operands(role TEXT,subject_ref TEXT,length INTEGER)")
        operands.executemany("INSERT INTO operands VALUES(?,?,?)", [
            ("query", "synthetic_query", 4), ("reference", "synthetic_reference", 4)])
    policy = {**POLICY, "scratch_bytes": 1024**2}
    result = asyncio.run(read_mapping.run_mapping(directory,
        configuration=read_mapping.local_configuration(executable=executable,
            cache_dir=tmp_path/"cache", job_limits=policy), preset="map-ont"))
    failure = result.metadata["resource_failure"]
    assert failure["code"] == "local_job_resource_limit"
    assert failure["operational"]["resource"] == "scratch_bytes"
    assert result.metadata["returncode"] != 0
    row, = [json.loads(line) for line in (directory/"placements.jsonl").read_text().splitlines()]
    assert row["query_name"] == "synthetic_query" and row["reference_name"] == "synthetic_reference"
    assert row["query_interval"] == row["reference_interval"] == [0, 4]
    assert (directory/"projection-errors.jsonl").read_bytes() == b""


def test_mapper_checks_known_cached_copy_size_before_host_copy(tmp_path, monkeypatch):
    executable = synthetic_executable(tmp_path, kind="mapper")
    configuration = read_mapping.local_configuration(executable=executable,
        cache_dir=tmp_path/"cache", job_limits=POLICY)
    monkeypatch.setattr(read_mapping, "project_output", lambda directory: None)
    for ordinal in range(2):
        directory = tmp_path / f"job-{ordinal}"
        directory.mkdir()
        (directory/"queries.fasta").write_bytes(b">synthetic_query\nACGT\n")
        (directory/"references.fasta").write_bytes(b">synthetic_reference\nACGT\n")
        if ordinal == 0:
            asyncio.run(read_mapping.run_mapping(directory, configuration=configuration, preset="map-ont"))
            index, = (tmp_path/"cache").glob("*.mmi")
            # A synthetic oversized cache member must not be copied first and
            # discovered only when the subsequent native process is launched.
            index.write_bytes(b"x" * (POLICY["scratch_bytes"]+1))
        else:
            with pytest.raises(AcquisitionError) as raised:
                asyncio.run(read_mapping.run_mapping(directory, configuration=configuration, preset="map-ont"))
            assert raised.value.code == "local_job_resource_limit"
            assert raised.value.phase == "local_preflight"
            assert raised.value.operational["resource"] == "scratch_bytes"
            assert not (directory/"references.mmi").exists()
