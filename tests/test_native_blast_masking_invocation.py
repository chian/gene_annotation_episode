"""Selected masking invocation and original custody, separate from core math.

Controlled process outcomes below are synthetic custody faults. The four final
native cases use only explicit runner-staged binaries and tiny supplied inputs.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import native_blast_masking_acquisition as capture
from gene_annotation_episode import native_blast_masking_driver as driver
from gene_annotation_episode import native_blast_masking_local as local
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_blast_masking_contracts import (
    ATTEMPT_NAME, BUNDLE_VERSION, MODES, NATIVE_BLAST_MASKING_JOB_SCHEMA,
    NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA, OWNER_NAME, PLAN_VERSION,
    compile_native_blast_masking_job, masking_occurrence_id, native_blast_digest as digest,
    requested_job_from_native_blast_masking, validate_native_blast_masking_job,
    validate_native_blast_masking_requested_job, validate_native_blast_masking_plan,
    validate_original_bundle,
)
from gene_annotation_episode.native_blast_masking_tool_info import (
    native_blast_masking_tool_contracts, validate_native_blast_masking_bindings,
)
from gene_annotation_episode.sequence_masking_contracts import sequence_masking_operation_schema
from gene_annotation_episode.state import Store

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "verification/tool_graders_masking_native_oracle_2026-10-28_612/retained_native"
POLICY = {"memory_bytes": 20 * 1024**3, "scratch_bytes": 4 * 1024**3, "wall_seconds": None}
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


def synthetic_native(monkeypatch, *, rc=0, output=b">dup\n0 - 3\n>dup\n", mutate=False, escape=None):
    calls = []
    def run(argv, **kw):
        calls.append((argv, kw))
        kw["stdout"].write(b"synthetic producer stdout\n")
        kw["stderr"].write(b"synthetic producer stderr\n")
        path = Path(argv[argv.index("-out") + 1])
        if escape is not None:
            path.symlink_to(escape)
        elif output is not None:
            path.write_bytes(output)
        if mutate:
            source = Path(argv[argv.index("-in") + 1])
            source.chmod(0o644)
            source.write_bytes(b">changed\nAAAA\n")
        return subprocess.CompletedProcess(argv, rc)
    monkeypatch.setattr(driver.subprocess, "run", run)
    return calls


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


def test_sealed_replay_keeps_exact_plan_originals_and_no_native_call(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    calls = synthetic_native(monkeypatch)
    bundle = driver.run_native_blast_masking(plan)
    assert bundle["returncode"] == 0 and not bundle["failures"] and len(calls) == 1
    assert "timeout" not in calls[0][1]
    assert calls[0][1]["env"]["TMPDIR"] == plan["attempt_directory"] + "/tmp"
    assert calls[0][0] == bundle["realized_argv"]
    source = bundle["inputs"][0]
    staged = Path(plan["attempt_directory"]) / source["relative_path"]
    assert staged.stat().st_mode & 0o222 == 0
    assert source["expected_sha256"] == source["staged_sha256"] == source["final_sha256"]
    Path(source["original_path"]).unlink()
    assert driver.run_native_blast_masking(plan) == bundle and len(calls) == 1
    altered = deepcopy(plan); altered["policy"]["scratch_bytes"] -= 1
    with pytest.raises(ValueError, match="identity_conflict"): driver.run_native_blast_masking(altered)


@pytest.mark.parametrize("fault", ["digest", "invalid", "empty", "gap", "rna", "record_binding", "missing", "software"])
def test_preflight_retains_input_and_specific_failure_without_native(tmp_path, monkeypatch, fault):
    plan = plan_for(tmp_path)
    job = plan["requested_job"]["native_blast_masking"]
    row = job["operands"][0]
    path = Path(row["path"])
    if fault == "digest": row["sha256"] = "0" * 64
    elif fault in {"invalid", "empty", "gap", "rna"}:
        path.write_bytes({"invalid": b"not fasta\n", "empty": b">a\n", "gap": b">a\nAC-G\n", "rna": b">a\nACGU\n"}[fault]); row.update(pin(path))
    elif fault == "record_binding": job["operand_bindings"] = [{"operand_role": "sequences", "operand_ordinal": 0, "record_ordinal": 99, "source_record_ref": None}]
    elif fault == "missing": path.unlink()
    elif fault == "software": job["software"]["sha256"] = "0" * 64
    reseal(plan)
    calls = synthetic_native(monkeypatch)
    bundle = driver.run_native_blast_masking(plan)
    assert not calls and bundle["returncode"] is None and bundle["failures"]
    assert validate_original_bundle(bundle, plan) == bundle
    assert driver.run_native_blast_masking(plan) == bundle
    if fault in {"invalid", "empty", "gap", "rna"}:
        f = next(f for f in bundle["failures"] if f["code"].endswith("invalid_fasta"))
        assert f["input_failures"] and set(f["input_failures"][0]) == {"code", "line_number", "record_ordinal"}


def test_unsealed_attempt_remains_uncertain(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    root = Path(plan["attempt_directory"]); root.mkdir()
    driver._atomic_new(root / OWNER_NAME, plan)
    calls = synthetic_native(monkeypatch)
    with pytest.raises(ValueError, match="unsealed_attempt_execution_uncertain"):
        driver.run_native_blast_masking(plan)
    assert calls == []


@pytest.mark.parametrize("fault", ["partial", "changed_staged", "changed_after_seal", "escaped_output"])
def test_partial_or_changed_bytes_are_retained_without_false_authentication(tmp_path, monkeypatch, fault):
    plan = plan_for(tmp_path)
    escape = tmp_path / "outside.txt"; escape.write_bytes(b"outside\n")
    raw = b">dup\n0 - 3\n>dup\n0 -"
    calls = synthetic_native(monkeypatch, rc=3 if fault == "partial" else 0, output=raw,
        mutate=fault == "changed_staged", escape=escape if fault == "escaped_output" else None)
    bundle = driver.run_native_blast_masking(plan)
    assert len(calls) == 1
    if fault == "changed_after_seal":
        (Path(plan["attempt_directory"]) / "selected.out").write_bytes(b"changed after original seal\n")
        with pytest.raises(ValueError, match="sealed_output_digest_mismatch"):
            driver.run_native_blast_masking(plan)
    monkeypatch.setattr(capture, "local_blast_masking_plan", lambda *a: deepcopy(plan))
    store = Store(tmp_path / "store")
    retained = capture.capture_local_bundle(store, target=target_for(plan), directory=tmp_path / "capture")
    assert retained["bundle_validated"]
    if fault == "partial":
        assert not retained["failures"] and len(retained["artifacts"]) == 4
        output = next(r for r in retained["artifacts"] if r["role"] == "mask")
        assert store.get_artifact(output["artifact_ref"]) == raw
        assert bundle["returncode"] == 3
    else:
        assert retained["failures"]
        if fault == "changed_staged":
            assert not any(r["direction"] == "input" for r in retained["artifacts"])
            f = next(f for f in retained["failures"] if f["code"] == "input_not_original")
            assert store.get_artifact(f["diagnostic_artifact_ref"]) == b">changed\nAAAA\n"
        elif fault == "changed_after_seal":
            f = next(f for f in retained["failures"] if f["code"] == "original_file_identity_mismatch")
            assert store.get_artifact(f["diagnostic_artifact_ref"]) == b"changed after original seal\n"
    source = capture.publish_original_source(store, bundle=bundle, capture=retained, prepared=None)
    assert store.get(source)["version"] == BUNDLE_VERSION
    shutil.rmtree(Path(plan["attempt_directory"]))
    monkeypatch.setattr(capture, "local_blast_masking_plan", lambda *a: pytest.fail("replay touched native paths"))
    assert capture.capture_local_bundle(store, target=target_for(plan), directory=tmp_path / "capture") == retained


def test_unsealed_capture_retains_partial_diagnostics_without_authenticated_rows(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    root = Path(plan["attempt_directory"]); root.mkdir()
    driver._atomic_new(root / OWNER_NAME, plan)
    (root / "selected.out").write_bytes(b">partial\n0 - 1\n")
    monkeypatch.setattr(capture, "local_blast_masking_plan", lambda *a: deepcopy(plan))
    store = Store(tmp_path / "store")
    value = capture.capture_local_bundle(store, target=target_for(plan), directory=tmp_path / "capture")
    assert not value["bundle_validated"] and not value["artifacts"]
    failure = next(f for f in value["failures"] if f["code"] == "unsealed_file")
    assert store.get_artifact(failure["diagnostic_artifact_ref"]) == b">partial\n0 - 1\n"


def test_generated_counts_reference_is_separate_and_non_self_referential(tmp_path, monkeypatch):
    plan = plan_for(tmp_path, "windowmasker", "create_counts")
    synthetic_native(monkeypatch, output=(FIXTURES / "outputs/windowmasker_counts.ascii").read_bytes())
    bundle = driver.run_native_blast_masking(plan)
    binding = bundle["statistics_binding"]
    assert binding["reference_occurrence_ids"] == [masking_occurrence_id(plan["identity"], "input", "reference_sequences")]
    assert binding["statistics_occurrence_id"] == masking_occurrence_id(plan["identity"], "output", "statistics")
    assert binding["producer_attempt_id"] == plan["identity"]["attempt_id"] and binding["producer_source_ref"] is None
    changed = deepcopy(bundle)
    changed["statistics_binding"]["reference_occurrence_ids"] = ["different-target"]
    with pytest.raises(ValueError, match="statistics_binding_conflict"): validate_original_bundle(changed, plan)


def test_occurrences_are_unique_across_original_owners(tmp_path):
    plan = plan_for(tmp_path)
    first = plan["identity"]
    other = {**first, "episode_id": "other-resource-child"}
    assert first["attempt_id"] == other["attempt_id"]
    assert masking_occurrence_id(first, "input", "sequences") != masking_occurrence_id(other, "input", "sequences")
    assert masking_occurrence_id(first, "input", "sequences") != masking_occurrence_id(first, "output", "mask")


def test_original_bundle_rejects_equal_valued_different_json_types(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    synthetic_native(monkeypatch)
    bundle = driver.run_native_blast_masking(plan)
    for field in ("operation", "requested_job"):
        changed = deepcopy(bundle)
        if field == "operation":
            changed["operation"]["parse_seqids"] = 0
        else:
            changed["requested_job"]["native_blast_masking"]["operands"][0]["ordinal"] = False
        with pytest.raises(ValueError): validate_original_bundle(changed, plan)


def test_local_reservation_preserves_allocation_and_never_dispatches(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    state = SimpleNamespace(assignment=assignment(plan), run_id=plan["identity"]["run_id"], episode_id=plan["identity"]["episode_id"])
    root = Path(plan["attempt_directory"]).parent
    monkeypatch.setattr(native_lifecycle, "resume_start", lambda *a, **k: pytest.fail("reservation dispatched"))
    handle = local.prepare_local_blast_masking(state, plan["identity"]["operation_key"], root=root, policy=LocalJobPolicy(**POLICY))
    assert handle.read()["stage"] == "prepared"
    assert local.local_blast_masking_plan(state.assignment, str(handle.path)) == plan
    altered = deepcopy(state.assignment); altered["constraints"]["allocation"]["memory_bytes"] //= 2
    with pytest.raises(ValueError, match="allocation_conflict"):
        local.local_blast_masking_plan(altered, str(handle.path))


@pytest.mark.parametrize("program,mode", LEGACY_MODES)
def test_actual_tiny_selected_driver_via_native_lifecycle(tmp_path, program, mode):
    """Four new driver-path verifications; no database or repeated parser oracle."""
    assert os.environ.get("HMMER529_ATTEMPT"), "actual invocation must use bounded529 runner"
    plan = plan_for(tmp_path, program, mode, actual=True)
    params = plan["requested_job"]["native_blast_masking"]["operation"]["requested_parameters"]
    if mode == "create_counts":
        params.update(unit=3, mem=16, t_low=1, t_high=64, checkdup=False)
    elif program == "windowmasker":
        params.update(window=7, t_low=1, t_high=64, t_extend=4, t_thres=8, set_t_low=1, set_t_high=64, dust=False)
    reseal(plan)
    state = SimpleNamespace(assignment=assignment(plan), run_id=plan["identity"]["run_id"], episode_id=plan["identity"]["episode_id"])
    handle = local.prepare_local_blast_masking(state, plan["identity"]["operation_key"],
        root=Path(plan["attempt_directory"]).parent, policy=LocalJobPolicy(**POLICY))
    native_lifecycle.resume_start(handle)
    outcome = native_lifecycle.wait_job(handle)
    assert outcome.returncode == 0, outcome.stderr_path.read_text()
    root = Path(plan["attempt_directory"])
    bundle = json.loads((root / "bundle.json").read_bytes())
    assert bundle["returncode"] == 0 and not bundle["failures"]
    assert driver.validate_native_blast_masking_bundle_files(bundle, root) == bundle
    store = Store(tmp_path / "store")
    retained = capture.capture_local_bundle(store, target=target_for(plan), directory=tmp_path / "capture")
    assert retained["bundle_validated"] and not retained["failures"]
    assert len(retained["artifacts"]) == len(bundle["inputs"]) + 3
    assert all(r["artifact_ref"] == "artifact_" + r["sha256"] for r in retained["artifacts"])
    assert capture.publish_original_source(store, bundle=bundle, capture=retained, prepared=None).startswith("source_")
    evidence = {"program": program, "mode": mode, "plan": plan, "bundle": bundle,
        "capture": retained, "native_handle": str(handle.path), "native_policy": outcome.metadata["policy"]}
    (tmp_path / "native_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
