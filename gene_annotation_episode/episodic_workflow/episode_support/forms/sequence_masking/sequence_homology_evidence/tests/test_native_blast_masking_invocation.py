"""Selected masking invocation and original custody, separate from core math.

Controlled process outcomes below are synthetic custody faults. The four final
native cases use only explicit runner-staged binaries and tiny supplied inputs.
"""
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_masking.sequence_homology_evidence import native_blast_masking_driver as driver
from gene_annotation_episode.episodic_workflow.episode_support.jobs.sequence_masking.sequence_homology_evidence import native_blast_masking_local as local
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.sequence_homology_evidence import native_lifecycle
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.sequence_homology_evidence.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_masking.sequence_homology_evidence.native_blast_masking_contracts import ATTEMPT_NAME, BUNDLE_VERSION, MODES, NATIVE_BLAST_MASKING_JOB_SCHEMA, NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA, OWNER_NAME, PLAN_VERSION, compile_native_blast_masking_job, masking_occurrence_id, native_blast_digest as digest, requested_job_from_native_blast_masking, validate_native_blast_masking_job, validate_native_blast_masking_requested_job, validate_native_blast_masking_plan, validate_original_bundle
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_masking.sequence_homology_evidence.native_blast_masking_tool_info import (
    native_blast_masking_tool_contracts, validate_native_blast_masking_bindings,
)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_masking.sequence_homology_evidence.sequence_masking_contracts import sequence_masking_operation_schema
from gene_annotation_episode.state import Store

ROOT = Path(__file__).resolve().parents[7]
FIXTURES = ROOT / "gene_annotation_episode/episodic_workflow/episode_support/forms/sequence_masking/sequence_homology_evidence/tests/fixtures/masking_native"
POLICY = {'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4 * 1024 ** 3}
LEGACY_MODES = (("dustmasker", "mask"), ("segmasker", "mask"),
                ("windowmasker", "mask"), ("windowmasker", "create_counts"))


def pin(path):
    raw = path.read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def job_for(tmp_path, program="dustmasker", mode="mask", *, actual=False, fmt=None, style=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    if actual:
        binary = ROOT / "resources/software/ncbi-blast-2.17.0+/bin" / program
        assert binary.is_file(), "actual native verification requires runner --native-executable"
    else:
        binary = tmp_path / (program + "-synthetic")
        binary.write_bytes(b"synthetic executable identity; process outcome replaced by test\n")
        binary.chmod(0o700)
    op_schema = sequence_masking_operation_schema(program=program, mode=mode)
    params = {k: None for k in op_schema["properties"]["requested_parameters"]["properties"]}
    fmt = fmt or ("ascii_statistics" if mode == "create_counts" else "interval")
    style = style or ("not_applicable" if mode == "create_counts" else "interval" if fmt == "interval" else "soft")
    operation = {"version": "sequence_masking_operation_v1", "program": program, "mode": mode,
        "engine_version": "1.0.0; package blast 2.17.0" if actual else "synthetic", "input_format": "fasta",
        "output_format": fmt, "masking_style": style, "parse_seqids": False, "requested_parameters": params}
    filename = ("window_reference.fa" if mode == "create_counts" else "protein.fa" if program == "segmasker"
        else "window_target.fa" if program == "windowmasker" else "dna.fa")
    role = "reference_sequences" if mode == "create_counts" else "sequences"
    source = tmp_path / filename
    source.write_bytes((FIXTURES / "inputs" / filename).read_bytes())
    operands = [{"role": role, "ordinal": 0, "path": str(source), "format": "fasta", **pin(source), "artifact_ref": None}]
    binding = None
    if program == "windowmasker" and mode == "mask":
        stats = tmp_path / "supplied.ascii"
        stats.write_bytes((FIXTURES / "outputs/windowmasker_counts.ascii").read_bytes())
        operands.append({"role": "statistics", "ordinal": 0, "path": str(stats), "format": "ascii_statistics", **pin(stats), "artifact_ref": None})
        binding = {"kind": "supplied", "statistics_occurrence_id": "supplied:reference:statistics:0",
            "reference_occurrence_ids": [], "producer_source_ref": None, "producer_attempt_id": None, "provenance": "unknown"}
    return {"version": "native_blast_masking_job_v1", "operation": operation,
        "software": {"executable": str(binary), "sha256": pin(binary)["sha256"], "engine_version": operation["engine_version"]},
        "environment": {"LC_ALL": "C"}, "operands": operands, "operand_bindings": [], "statistics_binding": binding,
        "outputs": [{"role": "statistics" if mode == "create_counts" else "mask", "format": fmt, "relative_path": "selected.out"},
                    {"role": "stdout", "format": "text", "relative_path": "stdout.txt"},
                    {"role": "stderr", "format": "text", "relative_path": "stderr.txt"}]}


def plan_for(tmp_path, program="dustmasker", mode="mask", *, actual=False):
    job = job_for(tmp_path / "supplied", program, mode, actual=actual)
    request = requested_job_from_native_blast_masking(job)
    workspace = tmp_path / "workspace"
    key, run, episode = "selected-start", "invocation615", "local-child615"
    root = workspace / ".episode-operations" / digest({"run": run, "episode": episode}) / digest(key)
    root.mkdir(parents=True)
    return {"version": PLAN_VERSION, "identity": {"run_id": run, "episode_id": episode, "resource_id": "local615",
        "execution_id": str(root / "native.json"), "attempt_id": digest(key), "operation_key": key,
        "requested_job_sha256": digest(request)}, "requested_job": request,
        "attempt_directory": str(root / ATTEMPT_NAME), "policy": POLICY.copy()}


def reseal(plan):
    plan["requested_job"] = requested_job_from_native_blast_masking(plan["requested_job"]["native_blast_masking"])
    plan["identity"]["requested_job_sha256"] = digest(plan["requested_job"])
    return plan


def assignment(plan):
    root = Path(plan["attempt_directory"]).parents[3]
    return {"workspace": str(root), "resource_kind": "local", "resource_id": plan["identity"]["resource_id"],
        "requested_job": plan["requested_job"], "constraints": {"allocation": plan["policy"]}}


def target_for(plan):
    identity = plan["identity"]
    return {"version": "execution_target_v1", "handle": "source_original615", "run_id": identity["run_id"],
        "origin_episode_id": identity["episode_id"], "resource_kind": "local", "resource_id": identity["resource_id"],
        "execution_id": identity["execution_id"], "request_sha256": identity["requested_job_sha256"],
        "assignment": assignment(plan), "scope": {}}


@pytest.mark.parametrize("program,mode", LEGACY_MODES)
def test_exact_single_command_shared_schema_and_null_omission(tmp_path, program, mode):
    job = job_for(tmp_path, program, mode)
    assert Draft202012Validator(NATIVE_BLAST_MASKING_JOB_SCHEMA).is_valid(job)
    request = requested_job_from_native_blast_masking(job)
    assert Draft202012Validator(NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA).is_valid(request)
    assert validate_native_blast_masking_requested_job(request) == request
    paths = {r["role"]: r["path"] for r in job["operands"]}
    argv = compile_native_blast_masking_job(job, input_paths=paths, output_directory=".")
    expected = [job["software"]["executable"]]
    if mode == "create_counts":
        expected += ["-mk_counts", "-in", paths["reference_sequences"], "-infmt", "fasta", "-sformat", "ascii", "-fa_list", "false"]
    else:
        if program == "windowmasker":
            expected += ["-ustat", paths["statistics"]]
        expected += ["-in", paths["sequences"], "-infmt", "fasta", "-outfmt", "interval"]
    assert argv == expected + ["-out", "selected.out"]
    params = job["operation"]["requested_parameters"]
    params[next(iter(params))] = False if mode == "create_counts" else 7
    argv = requested_job_from_native_blast_masking(job)["argv"]
    assert argv.count("-" + next(iter(params))) == 1
    assert ("-checkdup" not in argv or argv[argv.index("-checkdup") + 1] == "false")


def test_flags_precision_parameter_authority_and_requested_command(tmp_path):
    job = job_for(tmp_path, fmt="fasta", style="hard")
    job["operation"]["parse_seqids"] = True
    job["operation"]["requested_parameters"].update(level=0, linker=1, window=64)
    argv = requested_job_from_native_blast_masking(job)["argv"]
    assert argv.count("-hard_masking") == argv.count("-parse_seqids") == 1
    assert argv[argv.index("-level") + 1] == "0"
    request = requested_job_from_native_blast_masking(job)
    request["argv"].append("-help")
    with pytest.raises(ValueError, match="compiler_mismatch"):
        validate_native_blast_masking_requested_job(request)
    job = job_for(tmp_path / "seg", "segmasker")
    job["operation"]["requested_parameters"]["locut"] = 2.2000000000000006
    argv = requested_job_from_native_blast_masking(job)["argv"]
    assert float(argv[argv.index("-locut") + 1]) == 2.2000000000000006


@pytest.mark.parametrize("fault", ["program", "mode", "format", "style", "extra_parameter", "bool_parameter", "nan", "engine",
    "extra_operand", "binding_ordinal", "statistics", "duplicate_output", "output_overlap", "temporary", "escape", "environment"])
def test_invalid_job_relationships_reject_before_execution(tmp_path, fault):
    job = job_for(tmp_path)
    if fault == "program": job["operation"]["program"] = "blastn"
    elif fault == "mode": job["operation"]["mode"] = "create_counts"
    elif fault == "format": job["outputs"][0]["format"] = "text"
    elif fault == "style": job["operation"]["masking_style"] = "soft"
    elif fault == "extra_parameter": job["operation"]["requested_parameters"]["in"] = "/etc/passwd"
    elif fault == "bool_parameter": job["operation"]["requested_parameters"]["level"] = False
    elif fault == "nan": job["operation"]["requested_parameters"]["level"] = float("nan")
    elif fault == "engine": job["software"]["engine_version"] = "different"
    elif fault == "extra_operand": job["operands"].append(deepcopy(job["operands"][0]))
    elif fault == "binding_ordinal": job["operand_bindings"] = [{"operand_role": "sequences", "operand_ordinal": True, "record_ordinal": 0, "source_record_ref": None}]
    elif fault == "statistics": job["statistics_binding"] = {"not": "allowed"}
    elif fault == "duplicate_output": job["outputs"][1]["role"] = "mask"
    elif fault == "output_overlap": job["outputs"][1]["relative_path"] = "selected.out/child"
    elif fault == "temporary": job["outputs"][0]["relative_path"] = "tmp/result"
    elif fault == "escape": job["outputs"][0]["relative_path"] = "../result"
    elif fault == "environment": job["environment"]["TMPDIR"] = "/tmp"
    with pytest.raises(ValueError): validate_native_blast_masking_job(job)


def test_path_and_plan_confinement(tmp_path):
    plan = plan_for(tmp_path)
    job = plan["requested_job"]["native_blast_masking"]
    source = Path(job["operands"][0]["path"])
    job["outputs"][0]["relative_path"] = source.name
    with pytest.raises(ValueError, match="aliases"):
        compile_native_blast_masking_job(job, input_paths={"sequences": str(source)}, output_directory=str(source.parent))
    job["operands"][0]["path"] = plan["attempt_directory"] + "/input.fa"
    reseal(plan)
    with pytest.raises(ValueError, match="inside_attempt"): validate_native_blast_masking_plan(plan)


@pytest.mark.parametrize("fault", ["hpc", "duplicate", "format_style", "program"])
def test_tool_information_is_bound_to_exact_local_mode(tmp_path, fault):
    job = job_for(tmp_path)
    binding = {"program": "dustmasker", "mode": "mask", "software": job["software"],
        "output_formats": ["interval", "fasta"], "masking_styles": ["interval", "soft", "hard"]}
    info = native_blast_masking_tool_contracts([binding], resource_kind="local", resource_id="bound615")[0]
    assert info["name"] == "native.dustmasker.mask"
    assert all(info[k] for k in ("name", "description", "resources", "instructions"))
    assert info["invocation_route"] == {"kind": "commission", "routes": [{"entry_role": "launch", "resource_id": "bound615", "resource_role": "launch_local"}]}
    if fault == "hpc":
        with pytest.raises(ValueError): native_blast_masking_tool_contracts([binding], resource_kind="hpc", resource_id="bound615")
    else:
        rows = [binding]
        if fault == "duplicate": rows.append(deepcopy(binding))
        elif fault == "format_style": binding["output_formats"] = ["interval"]; binding["masking_styles"] = ["soft"]
        elif fault == "program": binding["program"] = "blastp"
        with pytest.raises(ValueError): validate_native_blast_masking_bindings(rows)


def test_occurrences_are_unique_across_original_owners(tmp_path):
    plan = plan_for(tmp_path)
    first = plan["identity"]
    other = {**first, "episode_id": "other-resource-child"}
    assert first["attempt_id"] == other["attempt_id"]
    assert masking_occurrence_id(first, "input", "sequences") != masking_occurrence_id(other, "input", "sequences")
    assert masking_occurrence_id(first, "input", "sequences") != masking_occurrence_id(first, "output", "mask")


