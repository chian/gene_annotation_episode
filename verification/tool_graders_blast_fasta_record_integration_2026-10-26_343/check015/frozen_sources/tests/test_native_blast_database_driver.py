"""Synthetic executable/file custody checks; no BLAST program or dataset runs."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from gene_annotation_episode import native_blast_database_contracts as c
from gene_annotation_episode import native_blast_database_driver as driver
from test_native_blast_database_contracts import job_for, checkpoint, forbid_io

ROOT = Path(__file__).resolve().parents[1]
PSSM = b'''PssmWithParameters ::= { pssm { isProtein TRUE, numRows 2, numColumns 2,
 query seq { inst { repr raw, mol aa, length 2, seq-data iupacaa "AC" } },
 finalData { scores { 1, 2, 3, 4 }, lambda 1.0, kappa 1.0, h 1.0 } } }
'''
MSA = b"CLUSTAL W\n\nfirst AC-D\nsecond ACED\n\nfirst EF\nsecond EF\n"


def file_identity(path):
    raw = Path(path).read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw), "artifact_ref": None}


def write(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return file_identity(path)


def save_json(path, value):
    return write(path, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode())


def fixture(base, program="psiblast", query="sequence", behavior="complete", checkpoint_output=True):
    base.mkdir(parents=True, exist_ok=True)
    deploy = base / "deployment"
    for name in ("__init__.py", "native_blast_database_contracts.py", "native_blast_database_driver.py", "blast_pssm_inputs.py"):
        write(deploy / "gene_annotation_episode" / name, (ROOT / "gene_annotation_episode" / name).read_bytes())
    runtime = write(base / "runtime-file", b"synthetic explicit additional runtime-file identity\n")
    python = file_identity(Path(sys.executable).resolve())
    manifest = {"version": "native_blast_database_producer_manifest_v1", "module_root": str(deploy),
        "entry_module": "gene_annotation_episode.native_blast_database_driver",
        "python": {k: python[k] for k in ("path", "sha256", "size_bytes")},
        "package_files": [{"relative_path": str(p.relative_to(deploy)), **{k: file_identity(p)[k] for k in ("sha256", "size_bytes")}}
            for p in sorted(deploy.rglob("*")) if p.is_file()],
        "runtime_files": [{k: runtime[k] for k in ("path", "sha256", "size_bytes")}]}
    manifest_identity = save_json(base / "producer-manifest.json", manifest)
    # This small script simulates the selected process's file/exit behavior. It
    # neither reads a real database nor emits authentic scientific measurements.
    script = ("#!" + sys.executable + "\n" + '''import json, os, pathlib, sys
argv = sys.argv[1:]
with open("native-invocations.log", "a") as log:
    log.write(json.dumps({"argv": argv, "cwd": os.getcwd()}) + "\\n")
assert sys.stdin.read() == ""
mode = os.environ["SYNTHETIC_BEHAVIOR"]
print("synthetic stdout:" + "x" * 1048583)
sys.stderr.write("synthetic stderr\\n")
report = pathlib.Path(argv[argv.index("-out") + 1])
if mode != "missing":
    if mode == "symlink":
        report.symlink_to(pathlib.Path(os.environ["OUTSIDE_FILE"]))
    else:
        report.write_bytes(b'{"synthetic":true,"not_native_measurements":true}\\n' if mode != "nonzero" else b'{"partial":')
for flag in ("-out_pssm", "-out_ascii_pssm"):
    if flag in argv and mode != "no_checkpoint":
        prefix = pathlib.Path(argv[argv.index(flag) + 1])
        prefix.write_bytes(b"synthetic base checkpoint\\n")
        subdir = prefix.parent / "native-emitted-subdir"
        subdir.mkdir()
        (subdir / "arbitrary-name").write_bytes(b"synthetic second checkpoint\\n")
if mode == "family_escape" and "-out_pssm" in argv:
    (pathlib.Path(argv[argv.index("-out_pssm") + 1]).parent / "escape").symlink_to(pathlib.Path(os.environ["OUTSIDE_FILE"]))
raise SystemExit(7 if mode == "nonzero" else 0)
''').encode()
    executable = base / "synthetic-native-command"
    software = write(executable, script)
    executable.chmod(0o700)
    job = job_for(program, query)
    job["software"] = {"executable": software["path"], "sha256": software["sha256"], "engine_version": None}
    outside = base / "outside-file"
    write(outside, b"outside must not be captured\n")
    job["environment"] = {"SYNTHETIC_BEHAVIOR": behavior, "OUTSIDE_FILE": str(outside)}
    query_bytes = {"sequence": b">one\nACGT\n>two\nACGTAC\n", "msa": MSA, "pssm": PSSM}[query]
    job["inputs"][0].update(write(base / "selected-query", query_bytes))
    job["inputs"].append({"input_key": "metadata", "role": "metadata", "format": "json",
        **write(base / "metadata.json", b"declared JSON deliberately not parsed by producer\x00\xff")})
    job["metadata_inputs"] = [{"input_key": "metadata", "consumer": "profile", "schema_id": "unregistered.example"}]
    for db in job["databases"]:
        key = db["database_key"]
        prefix = base / ("db-" + key)
        db["native_paths"] = [str(prefix)]
        m = db["manifest"]
        m["native_paths"] = db["native_paths"]
        data = write(prefix / "data.bin" if db["kind"] == "vdb" else prefix.with_suffix(".pin"), b"synthetic database bytes only\n")
        m["files"] = [{k: data[k] for k in ("path", "sha256", "size_bytes")}]
        m["preparation"]["receipt"] = write(base / (key + ".receipt.json"), b"opaque receipt, not JSON\x00\xff")
        m["preparation"]["input_manifest"] = write(base / (key + ".inputs.json"), b"opaque input manifest\xff")
        m["metadata_manifests"] = [write(base / (key + ".metadata.json"), b"opaque database metadata\x00")]
        m["access"]["offline_configuration"] = write(base / (key + ".offline.json"), b"opaque explicit synthetic offline configuration\xff")
        db["manifest_file"] = save_json(base / (key + ".manifest.json"), m)
    if checkpoint_output and program in {"psiblast", "deltablast"}:
        checkpoint(checkpoint(job), "checkpoint_ascii")
    request = c.requested_job_from_native_blast_database(job)
    owner = {"run_id": "synthetic-313", "episode_id": "synthetic-hpc-child", "resource_id": "synthetic-hpc",
        "operation_key": "explicit-selected-operation", "assignment_sha256": "d" * 64,
        "requested_job_sha256": c._digest(request), "execution_id": None}
    owner["attempt_id"] = c._digest(owner["operation_key"])
    owner["submission_token"] = c._digest({k: owner[k] for k in ("run_id", "episode_id", "assignment_sha256", "operation_key")})
    attempt = base / "attempt"
    attempt.mkdir()
    plan = {"version": "native_blast_database_run_plan_v1", "identity": owner, "requested_job": request,
        "attempt_directory": str(attempt), "input_paths": {r["input_key"]: str(attempt / "inputs" / r["input_key"]) for r in job["inputs"]},
        "database_paths": {r["database_key"]: r["native_paths"] for r in job["databases"]},
        "output_directory": str(attempt / "outputs"), "resource_environment": {"RESOURCE_SETTING": "explicit"},
        "producer_manifest": manifest_identity}
    path = attempt / "selected-plan.json"
    save_json(path, plan)
    return path, plan, manifest


def refresh_plan(path, plan):
    job = plan["requested_job"]["native_blast_database"]
    plan["requested_job"] = c.requested_job_from_native_blast_database(job)
    plan["identity"]["requested_job_sha256"] = c._digest(plan["requested_job"])
    save_json(path, plan)


def run_fixture(path, plan, *, shadow=None):
    manifest = json.loads(Path(plan["producer_manifest"]["path"]).read_bytes())
    deployment = manifest["module_root"] if shadow is None else str(shadow)
    result = subprocess.run([sys.executable, "-B", "-m", "gene_annotation_episode.native_blast_database_driver", str(path)],
        cwd=path.parent, env={"PYTHONPATH": deployment, "PYTHONDONTWRITEBYTECODE": "1", "PBS_JOBID": "313.synthetic"},
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    (path.parent / "wrapper.stdout").write_bytes(result.stdout)
    (path.parent / "wrapper.stderr").write_bytes(result.stderr)
    bundle_path = path.parent / "bundle.json"
    bundle = json.loads(bundle_path.read_bytes()) if bundle_path.exists() else None
    return result, bundle


def validate_bundle(bundle, plan):
    return c.validate_native_blast_database_bundle(bundle, original_job=plan["requested_job"]["native_blast_database"],
        attempt_identity={"identity": {**plan["identity"], "execution_id": "313.synthetic"},
            "attempt_directory": plan["attempt_directory"], "plan_sha256": c._digest(plan)})


@pytest.mark.parametrize("program,query", [(p, q) for p in c.PROGRAMS for q in
    ({"psiblast": ["sequence", "msa", "pssm"], "tblastn_vdb": ["sequence", "pssm"]}.get(p, ["sequence"]))])
def test_exported_driver_exact_one_simulated_invocation_and_byte_retention(tmp_path, program, query):
    path, plan, manifest = fixture(tmp_path, program, query)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 0, result.stderr.decode()
    assert bundle["failures"] == []
    assert bundle["producer_verification"]["status"] == "verified"
    assert bundle["producer_verification"]["manifest"] == manifest
    assert validate_bundle(bundle, plan) == bundle
    count = (path.parent / "native-invocations.log").read_text().splitlines()
    assert len(count) == 1
    assert json.loads(count[0])["argv"] == bundle["realized_argv"][1:]
    assert json.loads(count[0])["cwd"] == str(path.parent)
    assert bundle["process"]["started"] and bundle["process"]["returncode"] == 0
    assert bundle["process"]["native_elapsed_seconds"] >= 0
    assert bundle["associations"]["master_record_ordinal"] is None
    assert "-msa_master_idx" not in bundle["realized_argv"]
    assert bundle["environment"]["RESOURCE_SETTING"] == "explicit"
    assert "PBS_JOBID" not in bundle["environment"] and "HOME" not in bundle["environment"]
    assert bundle["environment"]["TMPDIR"] == str(path.parent / "tmp")
    for artifact in bundle["artifacts"]:
        actual = file_identity(path.parent / artifact["relative_path"])
        assert (actual["sha256"], actual["size_bytes"]) == (artifact["sha256"], artifact["size_bytes"])
        if artifact["database_key"] is not None and artifact["role"] != "database_manifest":
            assert artifact["format"] == "opaque"
    stdout = next(a for a in bundle["artifacts"] if a["role"] == "stdout")
    assert stdout["size_bytes"] > 1024**2
    query_artifact = next(a for a in bundle["artifacts"] if a["input_key"] == "query")
    assert (path.parent / query_artifact["relative_path"]).read_bytes() == Path(plan["requested_job"]["native_blast_database"]["inputs"][0]["path"]).read_bytes()
    assert all(row["sidecar_artifacts"][0]["role"] == "preparation_input_manifest" for row in bundle["database_manifest"])
    if program in {"psiblast", "deltablast"}:
        families = [r for r in bundle["output_manifest"] if r["output_key"].startswith("checkpoint_")]
        assert all(len(r["artifact_keys"]) == 2 and r["inventory_complete"] for r in families)
    # Replay validates original sealed bytes and returns without running again.
    replay, saved = run_fixture(path, plan)
    assert replay.returncode == 0 and saved == bundle
    assert len((path.parent / "native-invocations.log").read_text().splitlines()) == 1


@pytest.mark.parametrize("behavior,code,returncode", [("nonzero", "native_nonzero_exit", 7),
    ("missing", "required_output_missing", 0), ("symlink", "output_path_escape", 0),
    ("family_escape", "output_path_escape", 0)])
def test_native_partial_missing_escape_and_wrapper_exit_are_distinct(tmp_path, behavior, code, returncode):
    path, plan, _ = fixture(tmp_path, behavior=behavior)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 1, result.stderr.decode()
    assert bundle["process"]["returncode"] == returncode
    assert code in {f["code"] for f in bundle["failures"]}
    assert validate_bundle(bundle, plan) == bundle
    assert len((path.parent / "native-invocations.log").read_text().splitlines()) == 1
    assert any(a["role"] == "stdout" for a in bundle["artifacts"])
    if behavior == "nonzero":
        report = next(a for a in bundle["artifacts"] if a["role"] == "primary_report")
        assert (path.parent / report["relative_path"]).read_bytes() == b'{"partial":'
        assert report["content_assessment"] == "not_parsed"
    if behavior == "family_escape":
        row = next(r for r in bundle["output_manifest"] if r["output_key"] == "checkpoint_asn")
        assert len(row["artifact_keys"]) == 2 and not row["inventory_complete"]


def test_no_checkpoint_emission_is_not_missing_report(tmp_path):
    path, plan, _ = fixture(tmp_path, behavior="no_checkpoint")
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 0, result.stderr.decode()
    assert not bundle["failures"]
    assert all(r["presence"] == "not_emitted" and r["artifact_keys"] == []
        for r in bundle["output_manifest"] if r["output_key"].startswith("checkpoint_"))


@pytest.mark.parametrize("change,code", [("package", "producer_file_identity_mismatch"), ("runtime", "producer_file_identity_mismatch"),
    ("extra", "producer_package_inventory_mismatch"), ("missing", "producer_file_missing"),
    ("symlink", "producer_package_inventory_mismatch"), ("manifest", "producer_manifest_invalid"),
    ("duplicate_json", "producer_manifest_invalid"), ("shadow", "producer_runtime_path_mismatch")])
def test_manifest_alone_cannot_certify_actual_package_or_runtime(tmp_path, change, code):
    path, plan, manifest = fixture(tmp_path)
    deploy = Path(manifest["module_root"])
    shadow = None
    if change == "package":
        with (deploy / "gene_annotation_episode/__init__.py").open("ab") as stream:
            stream.write(b"\n# changed after manifest\n")
    elif change == "runtime":
        Path(manifest["runtime_files"][0]["path"]).write_bytes(b"changed")
    elif change == "extra":
        write(deploy / "unexpected", b"extra")
    elif change == "missing":
        (deploy / "gene_annotation_episode/blast_pssm_inputs.py").unlink()
    elif change == "symlink":
        (deploy / "escaped-file").symlink_to(tmp_path / "outside-file")
    elif change == "manifest":
        with Path(plan["producer_manifest"]["path"]).open("ab") as stream:
            stream.write(b"\n")
    elif change == "duplicate_json":
        raw = Path(plan["producer_manifest"]["path"]).read_bytes().rstrip()
        raw = raw[:-1] + b',"version":"native_blast_database_producer_manifest_v1"}'
        plan["producer_manifest"] = write(Path(plan["producer_manifest"]["path"]), raw)
        save_json(path, plan)
    elif change == "shadow":
        shadow = tmp_path / "other-package"
        shutil.copytree(deploy, shadow)
    result, bundle = run_fixture(path, plan, shadow=shadow)
    assert result.returncode == 1, result.stderr.decode()
    assert code in {f["code"] for f in bundle["failures"]}
    assert not bundle["process"]["started"]
    assert not (path.parent / "native-invocations.log").exists()
    assert validate_bundle(bundle, plan) == bundle


@pytest.mark.parametrize("change,code", [("query_missing", "input_missing"), ("query_changed", "input_identity_mismatch"),
    ("query_invalid", "input_native_incompatible"), ("database_missing", "database_file_missing"),
    ("database_changed", "database_identity_mismatch"), ("manifest_invalid", "database_manifest_invalid"),
    ("sidecar_missing", "database_file_missing"), ("sidecar_changed", "database_identity_mismatch"),
    ("sidecar_directory", "database_file_unreadable"), ("software_changed", "software_identity_mismatch"),
    ("software_missing", "software_missing"), ("not_executable", "native_start_failed")])
def test_setup_failures_seal_actual_partial_custody_without_invocation(tmp_path, change, code):
    path, plan, _ = fixture(tmp_path)
    job = plan["requested_job"]["native_blast_database"]
    db = job["databases"][0]
    if change == "query_missing":
        Path(job["inputs"][0]["path"]).unlink()
    elif change == "query_changed":
        Path(job["inputs"][0]["path"]).write_bytes(b">other\nACGT\n")
    elif change == "query_invalid":
        job["inputs"][0].update(write(Path(job["inputs"][0]["path"]), b"not FASTA"))
        refresh_plan(path, plan)
    elif change == "database_missing":
        Path(db["manifest"]["files"][0]["path"]).unlink()
    elif change == "database_changed":
        Path(db["manifest"]["files"][0]["path"]).write_bytes(b"changed database bytes")
    elif change == "manifest_invalid":
        db["manifest_file"] = write(Path(db["manifest_file"]["path"]), b"not JSON")
        refresh_plan(path, plan)
    elif change.startswith("sidecar_"):
        selected = Path(db["manifest"]["access"]["offline_configuration"]["path"])
        if change == "sidecar_changed":
            selected.write_bytes(b"different bytes")
        else:
            selected.unlink()
            if change == "sidecar_directory":
                selected.mkdir()
    elif change == "software_changed":
        with Path(job["software"]["executable"]).open("ab") as stream:
            stream.write(b"\n# changed\n")
    elif change == "software_missing":
        Path(job["software"]["executable"]).unlink()
    elif change == "not_executable":
        Path(job["software"]["executable"]).chmod(0o600)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 1, result.stderr.decode()
    assert code in {f["code"] for f in bundle["failures"]}
    assert bundle["process"] == {"started": False, "returncode": None, "started_at": None, "finished_at": None, "native_elapsed_seconds": None}
    assert not (path.parent / "native-invocations.log").exists()
    assert validate_bundle(bundle, plan) == bundle


def test_exact_shared_sidecar_identity_is_one_capture_with_two_roles(tmp_path):
    path, plan, _ = fixture(tmp_path)
    db = plan["requested_job"]["native_blast_database"]["databases"][0]
    db["manifest"]["access"]["offline_configuration"] = deepcopy(db["manifest"]["preparation"]["input_manifest"])
    db["manifest_file"] = save_json(Path(db["manifest_file"]["path"]), db["manifest"])
    refresh_plan(path, plan)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 0, result.stderr.decode()
    sides = bundle["database_manifest"][0]["sidecar_artifacts"]
    assert sides[0]["artifact_key"] == sides[1]["artifact_key"]
    bad = deepcopy(bundle)
    bad["database_manifest"][0]["sidecar_artifacts"].reverse()
    with pytest.raises(ValueError, match="sidecar_selection"):
        validate_bundle(bad, plan)


def test_unsealed_attempt_never_reinvoked_and_changed_sealed_file_rejected(tmp_path):
    path, plan, _ = fixture(tmp_path)
    save_json(path.parent / driver.OWNER_NAME, plan)
    result, bundle = run_fixture(path, plan)
    assert result.returncode != 0 and bundle is None
    assert b"unsealed_attempt_execution_uncertain" in result.stderr
    assert not (path.parent / "native-invocations.log").exists()
    other = tmp_path / "independent-explicit-fixture"
    path, plan, _ = fixture(other)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 0
    a = next(a for a in bundle["artifacts"] if a["role"] == "primary_report")
    (path.parent / a["relative_path"]).write_bytes(b"changed after seal")
    replay, _ = run_fixture(path, plan)
    assert replay.returncode != 0 and b"sealed_artifact_identity_mismatch" in replay.stderr
    assert len((path.parent / "native-invocations.log").read_text().splitlines()) == 1


def test_bundle_validator_forbids_io_and_forged_relationships(tmp_path, monkeypatch):
    path, plan, _ = fixture(tmp_path, query="msa")
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 0
    with monkeypatch.context() as pure:
        forbid_io(pure)
        assert validate_bundle(bundle, plan) == bundle
        for change in (lambda b: b["identity"].update(execution_id="wrong"),
            lambda b: b["plan"]["input_paths"].update(query="/attempt/forged"),
            lambda b: b["realized_argv"].append("-remote"),
            lambda b: b["associations"].update(master_record_ordinal=0),
            lambda b: b["database_manifest"][0]["sidecar_artifacts"].reverse(),
            lambda b: b["database_manifest"][0]["checks"].pop(),
            lambda b: b["producer_verification"]["checks"].pop(),
            lambda b: b["output_manifest"].pop(),
            lambda b: b["artifacts"][0].update(relative_path="../escape"),
            lambda b: b["input_manifest"][0].update(observed_sha256="f" * 64),
            lambda b: b["producer_verification"].update(package_inventory_exact=False)):
            bad = deepcopy(bundle)
            change(bad)
            with pytest.raises(ValueError):
                validate_bundle(bad, plan)


def test_invalid_complete_plan_rejected_before_native_invocation(tmp_path):
    path, plan, _ = fixture(tmp_path)
    plan["database_paths"]["target"] = ["/replacement"]
    save_json(path, plan)
    result, bundle = run_fixture(path, plan)
    assert result.returncode != 0 and bundle is None
    assert b"selected_database_paths_mismatch" in result.stderr
    assert not (path.parent / driver.OWNER_NAME).exists()


@pytest.mark.parametrize("ordinal,ignore", [(1, False), (None, True)])
def test_selected_msa_ordinal_and_exclusion_survive_bundle(tmp_path, ordinal, ignore):
    path, plan, _ = fixture(tmp_path, query="msa")
    plan["requested_job"]["native_blast_database"]["query"].update(msa_master_record_ordinal=ordinal, ignore_msa_master=ignore)
    refresh_plan(path, plan)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 0, result.stderr.decode()
    assert bundle["associations"]["master_record_ordinal"] == ordinal
    assert bundle["associations"]["ignore_msa_master"] is ignore
    if ordinal is not None:
        assert bundle["realized_argv"][bundle["realized_argv"].index("-msa_master_idx") + 1] == "2"


def test_vdb_directory_inventory_rejects_undeclared_dataset_file(tmp_path):
    path, plan, _ = fixture(tmp_path, program="blastn_vdb")
    db = plan["requested_job"]["native_blast_database"]["databases"][0]
    write(Path(db["native_paths"][0]) / "undeclared", b"extra dataset file")
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 1, result.stderr.decode()
    assert "database_manifest_invalid" in {f["code"] for f in bundle["failures"]}
    assert not bundle["process"]["started"]


def test_final_seal_check_excludes_changed_bytes_without_recapture(tmp_path):
    path, plan, _ = fixture(tmp_path)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 0
    report = next(a for a in bundle["artifacts"] if a["role"] == "primary_report")
    original_sha = report["sha256"]
    report_path = path.parent / report["relative_path"]
    raw = report_path.read_bytes()
    report_path.write_bytes(b"X" + raw[1:])
    # Exercise the actual final file check against a previously measured set;
    # no process or measurement implementation is replaced by this fixture.
    driver._seal_output_checks(bundle)
    assert original_sha not in {a["sha256"] for a in bundle["artifacts"]}
    assert {"output_changed_during_seal", "required_output_missing"} <= {f["code"] for f in bundle["failures"]}
    assert validate_bundle(bundle, plan) == bundle
    assert len((path.parent / "native-invocations.log").read_text().splitlines()) == 1


@pytest.mark.parametrize("query,program,raw,ordinal", [("msa", "psiblast", MSA, 9),
    ("msa", "psiblast", b"CLUSTAL W\n\na AC\nb A\n", None),
    ("pssm", "tblastn_vdb", b'PssmWithParameters ::= { pssm { numRows 2, numColumns 2, finalData { scores { 1, 2, 3, 4 }, lambda 1.0, kappa 1.0, h 1.0 } } }', None),
    ("pssm", "psiblast", b"PssmWithParameters ::= { pssm {", None)])
def test_actual_input_restrictions_fail_without_guessed_master(tmp_path, query, program, raw, ordinal):
    path, plan, _ = fixture(tmp_path, program, query)
    job = plan["requested_job"]["native_blast_database"]
    job["inputs"][0].update(write(Path(job["inputs"][0]["path"]), raw))
    job["query"]["msa_master_record_ordinal"] = ordinal
    refresh_plan(path, plan)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 1, result.stderr.decode()
    assert not bundle["process"]["started"]
    assert "input_native_incompatible" in {f["code"] for f in bundle["failures"]}
    assert bundle["associations"]["master_record_ordinal"] == ordinal
    assert any(a["input_key"] == "query" for a in bundle["artifacts"])


def test_malformed_selected_producer_schema_seals_failure(tmp_path):
    path, plan, manifest = fixture(tmp_path)
    manifest["python"] = []
    plan["producer_manifest"] = save_json(Path(plan["producer_manifest"]["path"]), manifest)
    save_json(path, plan)
    # run_fixture needs module_root only; no consumer derives an interpreter
    # from malformed schema values before validation.
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 1, result.stderr.decode()
    assert bundle["producer_verification"]["manifest"] is None
    assert "producer_manifest_invalid" in {f["code"] for f in bundle["failures"]}
    assert not bundle["process"]["started"]


def test_family_requires_initially_empty_directory(tmp_path):
    path, plan, _ = fixture(tmp_path)
    write(Path(plan["output_directory"]) / "checkpoint_asn" / "preexisting", b"old unrelated bytes")
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 1, result.stderr.decode()
    assert not bundle["process"]["started"]
    assert "output_inventory_incomplete" in {f["code"] for f in bundle["failures"]}
    assert not (path.parent / "native-invocations.log").exists()


def test_exact_attempt_input_already_staged_is_measured_not_overwritten(tmp_path):
    path, plan, _ = fixture(tmp_path)
    job = plan["requested_job"]["native_blast_database"]
    staged = Path(plan["input_paths"]["query"])
    job["inputs"][0].update(write(staged, Path(job["inputs"][0]["path"]).read_bytes()))
    refresh_plan(path, plan)
    before = file_identity(staged)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 0, result.stderr.decode()
    assert file_identity(staged) == before
    assert validate_bundle(bundle, plan) == bundle


def test_pure_bundle_rejects_null_sidecar_without_applicable_failure_and_database_reorder(tmp_path):
    path, plan, _ = fixture(tmp_path, program="deltablast")
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 0
    bad = deepcopy(bundle)
    bad["database_manifest"].reverse()
    bad["associations"]["external_manifest_keys"].reverse()
    with pytest.raises(ValueError, match="selected_order"):
        validate_bundle(bad, plan)
    bad = deepcopy(bundle)
    sidecar = bad["database_manifest"][0]["sidecar_artifacts"][0]
    key = sidecar["artifact_key"]
    sidecar["artifact_key"] = None
    bad["artifacts"] = [a for a in bad["artifacts"] if a["artifact_key"] != key]
    bad["process"] = {"started": False, "returncode": None, "started_at": None, "finished_at": None, "native_elapsed_seconds": None}
    bad["failures"] = [{"code": "database_manifest_invalid", "database_key": "target", "input_key": None,
        "output_key": None, "artifact_key": None, "native_returncode": None}]
    with pytest.raises(ValueError, match="artifact_missing_failure"):
        validate_bundle(bad, plan)


def test_prepared_pbs_tmp_cache_directories_are_reused(tmp_path):
    path, plan, _ = fixture(tmp_path)
    for name in ("tmp", "cache"):
        (path.parent / name).mkdir()
        write(path.parent / name / "existing-resource-file", b"prepared resource byte")
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 0, result.stderr.decode()
    assert bundle["process"]["started"] and not bundle["failures"]
    assert len((path.parent / "native-invocations.log").read_text().splitlines()) == 1
    for name in ("tmp", "cache"):
        assert (path.parent / name / "existing-resource-file").read_bytes() == b"prepared resource byte"


@pytest.mark.parametrize("kind", ["file", "symlink"])
def test_prepared_control_path_must_be_canonical_directory(tmp_path, kind):
    path, plan, _ = fixture(tmp_path)
    if kind == "file":
        write(path.parent / "tmp", b"not a directory")
    else:
        (path.parent / "tmp").symlink_to(tmp_path)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 1, result.stderr.decode()
    assert not bundle["process"]["started"]
    assert "native_start_failed" in {f["code"] for f in bundle["failures"]}


@pytest.mark.parametrize("condition", ["equal_content", "first_missing", "first_missing_second_changed", "repeated_exact"])
def test_each_metadata_identity_survives_missing_or_equal_content(tmp_path, condition):
    path, plan, _ = fixture(tmp_path)
    db = plan["requested_job"]["native_blast_database"]["databases"][0]
    first = write(tmp_path / "first-metadata", b"same declared bytes\x00\xff")
    second = deepcopy(first) if condition == "repeated_exact" else write(tmp_path / "second-metadata", b"same declared bytes\x00\xff")
    db["manifest"]["metadata_manifests"] = [first, second]
    db["manifest_file"] = save_json(Path(db["manifest_file"]["path"]), db["manifest"])
    refresh_plan(path, plan)
    if condition.startswith("first_missing"):
        Path(first["path"]).unlink()
    if condition.endswith("second_changed"):
        Path(second["path"]).write_bytes(b"changed complete bytes\xff")
    result, bundle = run_fixture(path, plan)
    assert result.returncode == (1 if condition.startswith("first_missing") else 0), result.stderr.decode()
    rows = bundle["database_manifest"][0]["metadata_manifest_artifacts"]
    assert [r["identity"] for r in rows] == [first, second]
    assert rows[1]["artifact_key"] is not None
    if condition.startswith("first_missing"):
        assert rows[0]["artifact_key"] is None
        assert not bundle["process"]["started"] and not (path.parent / "native-invocations.log").exists()
    elif condition == "equal_content":
        assert rows[0]["artifact_key"] != rows[1]["artifact_key"]
        bad = deepcopy(bundle)
        selected = bad["database_manifest"][0]["metadata_manifest_artifacts"]
        selected[0]["artifact_key"], selected[1]["artifact_key"] = selected[1]["artifact_key"], selected[0]["artifact_key"]
        with pytest.raises(ValueError, match="metadata_artifact_identity"):
            validate_bundle(bad, plan)
    else:
        assert rows[0]["artifact_key"] == rows[1]["artifact_key"]
    if condition.endswith("second_changed"):
        actual = next(a for a in bundle["artifacts"] if a["artifact_key"] == rows[1]["artifact_key"])
        assert actual["sha256"] != second["sha256"]
        assert "database_identity_mismatch" in {f["code"] for f in bundle["failures"]}
    assert validate_bundle(bundle, plan) == bundle
    bad = deepcopy(bundle)
    bad["database_manifest"][0]["metadata_manifest_artifacts"][0]["identity"]["path"] = "/wrong-original"
    with pytest.raises(ValueError, match="metadata_selection"):
        validate_bundle(bad, plan)


def test_unavailable_input_parser_is_not_malformed_scientific_input(tmp_path):
    path, plan, manifest = fixture(tmp_path, query="pssm")
    parser = "gene_annotation_episode/blast_pssm_inputs.py"
    (Path(manifest["module_root"]) / parser).unlink()
    # The declared complete deployment really has only the three producer
    # package files; file verification passes but the optional parser is absent.
    manifest["package_files"] = [r for r in manifest["package_files"] if r["relative_path"] != parser]
    plan["producer_manifest"] = save_json(Path(plan["producer_manifest"]["path"]), manifest)
    save_json(path, plan)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 1, result.stderr.decode()
    assert bundle["producer_verification"]["status"] == "verified"
    assert not bundle["process"]["started"]
    assert {f["code"] for f in bundle["failures"]} == {"producer_input_parser_unavailable"}
    failure = bundle["failures"][0]
    assert failure["input_key"] == "query" and failure["artifact_key"] is not None
    artifact = next(a for a in bundle["artifacts"] if a["artifact_key"] == failure["artifact_key"])
    assert (path.parent / artifact["relative_path"]).read_bytes() == PSSM
    assert not (path.parent / "native-invocations.log").exists()
    assert validate_bundle(bundle, plan) == bundle


def test_parser_import_location_must_match_verified_selected_package(tmp_path):
    path, plan, manifest = fixture(tmp_path, query="pssm")
    alternate = tmp_path / "alternate-pssm-parser.py"
    identity = write(alternate, b'def read_blast_pssm(*args, **kwargs):\n    raise AssertionError("unselected parser must not be called")\n')
    manifest["runtime_files"].append({k: identity[k] for k in ("path", "sha256", "size_bytes")})
    init = Path(manifest["module_root"]) / "gene_annotation_episode/__init__.py"
    # Deliberately prepopulate the imported module from another declared runtime
    # path. Matching external bytes cannot substitute for the selected package's
    # parser. The real producer still performs all package checks.
    addition = ("\nimport importlib.util, sys\n"
        "_spec = importlib.util.spec_from_file_location(__name__ + '.blast_pssm_inputs', " + repr(str(alternate)) + ")\n"
        "_module = importlib.util.module_from_spec(_spec)\n"
        "sys.modules[_spec.name] = _module\n_spec.loader.exec_module(_module)\n")
    with init.open("ab") as stream:
        stream.write(addition.encode())
    init_identity = file_identity(init)
    row = next(r for r in manifest["package_files"] if r["relative_path"] == "gene_annotation_episode/__init__.py")
    row.update({k: init_identity[k] for k in ("sha256", "size_bytes")})
    plan["producer_manifest"] = save_json(Path(plan["producer_manifest"]["path"]), manifest)
    save_json(path, plan)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 1, result.stderr.decode()
    assert bundle["producer_verification"]["status"] == "verified"
    assert {f["code"] for f in bundle["failures"]} == {"producer_input_parser_unavailable"}
    assert not bundle["process"]["started"]
    assert not (path.parent / "native-invocations.log").exists()
    assert validate_bundle(bundle, plan) == bundle
