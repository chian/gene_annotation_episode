"""Selected-record tests. Fake software pins are labelled control fixtures."""
from copy import deepcopy
import gzip
import hashlib
import os
from pathlib import Path
import struct
import sys

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.native_atac_differential_contracts import (
    POLICY, MODE, OPERATION, REQUIRED_DEPENDENCIES, REQUIRED_MODULES, ATTEMPT_DIRECTORY_NAME,
    _dependency_roots, atac_execution_schema, atac_output_files, atac_command_argv,
    canonical, digest, requested_job_from_atac, validate_atac_request,
    validate_atac_native_job, validate_atac_requested_job, validate_atac_run_plan,
)


def identity(raw, format="bam"):
    sha = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref="artifact_" + sha, sha256=sha, size_bytes=len(raw), format=format)


def bam_bytes(*, text=b"@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:chrToy\tLN:12000\n", length=12000):
    raw = b"BAM\x01" + struct.pack("<i", len(text)) + text
    raw += struct.pack("<i", 1) + struct.pack("<i", 7) + b"chrToy\0" + struct.pack("<i", length)
    return gzip.compress(raw, mtime=0)


def fake_software():
    files = ["/fixture/native/macs2", "/fixture/site/MACS2/callpeak_cmd.py", "/fixture/site/MACS2/bdgdiff_cmd.py",
        "/fixture/site/MACS2/IO/Parser.cpython-311-x86_64-linux-gnu.so", "/fixture/site/numpy/__init__.py"]
    return {"driver_runtime": {"python_executable": "/fixture/python", "python_sha256": "0" * 64,
        "python_version": "3.12.0", "module_root": "/fixture/source",
        "implementation_files": [{"module": name, "sha256": digest(name)} for name in sorted(REQUIRED_MODULES)],
        "dependencies": [{"distribution": name, "version": "control-fixture", "package_root": "/fixture/deps/" + name,
            "files": [{"path": "/fixture/deps/" + name + "/__init__.py", "sha256": digest(name), "size_bytes": 1}]}
            for name in sorted(REQUIRED_DEPENDENCIES)]},
        "macs2_runtime": {"python_executable": "/fixture/native/python", "python_sha256": "0" * 64,
            "python_version": "3.11.13", "macs2_script": files[0], "macs2_sha256": "0" * 64,
            "macs2_version": "2.2.9.1", "import_roots": ["/fixture/site"],
            "files": [{"path": path, "sha256": "0" * 64, "size_bytes": 1} for path in files]}}


def job_fixture(directory, *, software=None, inputs=None):
    directory.mkdir(parents=True, exist_ok=True)
    inputs = [bam_bytes(), bam_bytes()] if inputs is None else inputs
    bindings, occurrences, samples, conditions = [], [], [], []
    for i, raw in enumerate(inputs, 1):
        path = directory / f"original{i}.bam"
        path.write_bytes(raw)
        file = identity(raw)
        bindings.append(dict(input_key=f"input{i}", file=file, path=str(path)))
        occurrences.append(dict(input_key=f"input{i}", condition_id=f"condition{i}", sample_id=f"sample{i}", reference_id="reference", file=file))
        samples.append(dict(sample_id=f"sample{i}", input_artifact_refs=[file["artifact_ref"]], reference_id="reference",
            biospecimen_id=None, replicate_id=None, origin="synthetic_engineering_fixture"))
        conditions.append(dict(condition_id=f"condition{i}", label=None, sample_ids=[f"sample{i}"]))
    request = dict(version="atac_differential_request_v1", operation=OPERATION, mode=MODE, comparison_key="comparison",
        reference=dict(reference_id="reference", assembly_accession_version=None, source_refs=[], aliases=[],
            contigs=[dict(chromosome="chrToy", length_bp=12000, sequence_accession_version=None, sequence_sha256=None, source_refs=[])]),
        samples=samples, conditions=conditions, inputs=occurrences,
        callpeak=dict(genome_size_argument="12000", qvalue_cutoff=0.05, keep_duplicates=1, nomodel=True, shift_bp=-100,
            extension_size_bp=200, store_bedgraph=True, spmr=False, broad=False, downsample=False),
        bdgdiff=dict(cutoff_log10_lr=3, minimum_length_bp=50, maximum_gap_bp=0), output_prefix="outputs")
    software = fake_software() if software is None else software
    return dict(request=request, software=software, input_bindings=bindings)


def requested(job, directory):
    driver = job["software"]["driver_runtime"]
    env = dict(PYTHONPATH=os.pathsep.join([driver["module_root"], *_dependency_roots(driver)]), PYTHONHOME=sys.base_prefix,
        PYTHONNOUSERSITE="1", PYTHONSAFEPATH="1", PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
        TMP=str(directory / "tmp"), TEMP=str(directory / "tmp"), TMPDIR=str(directory / "tmp"),
        XDG_CACHE_HOME=str(directory / "cache"), PIP_CACHE_DIR=str(directory / "cache/pip"))
    return requested_job_from_atac(job, environment=env)


def plan_fixture(directory, *, job=None):
    job = job_fixture(directory) if job is None else job
    selected = requested(job, directory)
    operation, run, episode = "selected-start", "control-fixture", "local-child"
    root = directory / ".episode-operations" / digest({"run": run, "episode": episode}) / digest(operation)
    return validate_atac_run_plan(dict(version="atac_differential_run_plan_v1", identity=dict(run_id=run, episode_id=episode,
        resource_id="local", execution_id=str(root / "native.json"), attempt_id=digest(operation), operation_key=operation,
        requested_job_sha256=digest(selected), assignment_sha256=digest("control-fixture-not-episode-authority")),
        requested_job=selected, attempt_directory=str(root / ATTEMPT_DIRECTORY_NAME), policy=POLICY, outputs=atac_output_files(job["request"])))


def path_for(plan, key):
    return Path(plan["attempt_directory"]) / next(r["relative_path"] for r in plan["outputs"] if r["file_key"] == key)


def test_exact_treatment_commands_and_output_occurrences(tmp_path):
    plan = plan_fixture(tmp_path)
    first, second = [atac_command_argv(plan, step) for step in ("callpeak1", "callpeak2")]
    assert first[first.index("-t") + 1] != second[second.index("-t") + 1]
    for i, argv in enumerate((first, second), 1):
        assert "-c" not in argv and argv.count("--outdir") == 1 and argv.count("-B") == 2
        assert argv[argv.index("-n") + 1] == f"c{i}"
    assert len(plan["outputs"]) == 31
    assert len({r["relative_path"] for r in plan["outputs"]}) == 31
    assert plan["outputs"][-1]["file_key"] == "bundle"
    assert atac_command_argv(plan, "bdgdiff") == []


@pytest.mark.parametrize("mutation", [
    lambda j: j["request"]["callpeak"].update(spmr=True),
    lambda j: j["request"]["callpeak"].update(keep_duplicates=True),
    lambda j: j["request"]["bdgdiff"].update(maximum_gap_bp=50),
    lambda j: j["request"].update(output_prefix="../escape"),
    lambda j: j["request"]["inputs"][1].update(condition_id="condition1"),
    lambda j: j["input_bindings"][1].update(file=j["input_bindings"][0]["file"] | {"sha256": "f" * 64}),
    lambda j: j["software"]["macs2_runtime"].update(macs2_version="2.2.9.2"),
])
def test_rejects_changed_selected_contract(tmp_path, mutation):
    job = job_fixture(tmp_path)
    mutation(job)
    with pytest.raises(ValueError):
        validate_atac_native_job(job)


def test_shared_input_sample_and_path_keep_occurrences(tmp_path):
    job = job_fixture(tmp_path)
    job["request"]["samples"] = job["request"]["samples"][:1]
    job["request"]["conditions"][1]["sample_ids"] = ["sample1"]
    job["request"]["inputs"][1]["sample_id"] = "sample1"
    job["input_bindings"][1]["path"] = job["input_bindings"][0]["path"]
    assert len(validate_atac_native_job(job)["request"]["inputs"]) == 2


def test_closed_bound_schema_and_recompiled_request(tmp_path):
    job = job_fixture(tmp_path)
    selected = requested(job, tmp_path)
    schema = atac_execution_schema("RequestedJob", bindings=[dict(operation=OPERATION, mode=MODE, software=job["software"])])
    assert Draft202012Validator(schema).is_valid(selected)
    selected["argv"].append("--other")
    assert not Draft202012Validator(schema).is_valid(selected)
    with pytest.raises(ValueError):
        validate_atac_requested_job(selected)
    bad = deepcopy(job["request"])
    bad["findings"] = "unconstrained text"
    with pytest.raises(ValueError):
        validate_atac_request(bad)
