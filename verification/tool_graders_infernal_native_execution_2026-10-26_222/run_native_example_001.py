"""Operator verification of one explicit tiny native case; not a runtime tool."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_infernal_contracts import native_infernal_digest, requested_job_from_infernal
from gene_annotation_episode.native_infernal_driver import run_native_infernal
from gene_annotation_episode.native_infernal_local import prepare_local_infernal, local_infernal_plan


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TUTORIAL = REPO / "resources/software/infernal-1.1.5/tutorial"
BIN = REPO / "resources/software/infernal-1.1.5-install/bin"
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def write_new(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def operand(path, role, fmt):
    raw = path.read_bytes()
    return {"role": role, "format": fmt, "path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw), "artifact_ref": "source_tutorial_" + role}


def main(case):
    if case not in {"cmsearch", "cmscan", "cmalign", "cmalign_native_failure"}:
        raise ValueError("one_explicit_verification_case_required")
    program = "cmalign" if case.startswith("cmalign") else case
    workspace = HERE / "runs" / case
    workspace.mkdir(parents=True)
    model = TUTORIAL / ("tRNA5.c.cm" if program == "cmalign" else "minifam.cm")
    sequences = TUTORIAL / "mrum-tRNAs10.fa"
    inputs = [operand(model, "models", "infernal_ascii"), operand(sequences, "sequences", "fasta")]
    if program == "cmscan":
        inputs += [operand(Path(str(model) + "." + suffix), "models_" + suffix, "infernal_" + suffix)
            for suffix in ("i1f", "i1i", "i1m", "i1p")]
    bindings, ordinal = [], -1
    for line in model.read_text().splitlines():
        if line.startswith("INFERNAL1/"):
            ordinal += 1
        elif line.startswith("NAME ") and len(bindings) == ordinal:
            bindings.append({"operand_role": "models", "record_ordinal": ordinal,
                "native_name": line.split()[1], "native_accession": None,
                "subject_ref": None, "reference_ref": "reference_tutorial_model_" + str(ordinal)})
    for ordinal, line in enumerate(line for line in sequences.read_text().splitlines() if line.startswith(">")):
        bindings.append({"operand_role": "sequences", "record_ordinal": ordinal,
            "native_name": line[1:].split()[0], "native_accession": None,
            "subject_ref": "subject_tutorial_sequence_" + str(ordinal), "reference_ref": None})
    outputs = [{"role": "stdout", "format": "infernal_stdout", "relative_path": "stdout.log"},
        {"role": "stderr", "format": "text", "relative_path": "stderr.log"}]
    if program == "cmalign":
        outputs += [{"role": role, "format": fmt, "relative_path": path} for role, fmt, path in (
            ("stockholm", "stockholm", "alignment.sto"), ("scores", "cmalign_sfile", "scores.txt"),
            ("inserts", "cmalign_ifile", "inserts.txt"), ("local_ends", "cmalign_elfile", "local-ends.txt"),
            ("traceback", "cmalign_tfile", "traceback.txt"))]
    else:
        outputs.append({"role": "tblout", "format": "infernal_tblout", "relative_path": "hits.tblout"})
        if program == "cmsearch":
            outputs.append({"role": "included_msa", "format": "stockholm", "relative_path": "included.sto"})
    executable = BIN / program
    job = {"version": "native_infernal_job_v1", "program": program,
        "software": {"executable": str(executable), "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
            "engine_version": "1.1.5 (caller declaration; native stdout retained separately)"},
        "environment": {"LC_ALL": "C"}, "operands": inputs, "operand_bindings": bindings,
        "options": ["--cpu", "1"] + (["--sample", "--seed", "42"] if case.endswith("failure") else []),
        "outputs": outputs, "table_format": None if program == "cmalign" else 2 if program == "cmscan" else 3,
        "metadata": {}, "grading_parameters": {}}
    request = requested_job_from_infernal(job)
    state = SimpleNamespace(run_id="native-infernal-222-" + case, episode_id="verification-local-child",
        assignment={"requested_job": request, "workspace": str(workspace), "resource_kind": "local",
            "resource_id": "local-verification-20GiB-4GiB"})
    operation = "selected-native-" + case
    root = workspace / ".episode-operations" / native_infernal_digest({"run": state.run_id,
        "episode": state.episode_id}) / native_infernal_digest(operation)
    root.mkdir(parents=True)
    source_before = {row["path"]: {"sha256": row["sha256"], "size_bytes": row["size_bytes"]} for row in inputs}
    write_new(root / "source-before.json", source_before)
    write_new(root / "assignment.json", state.assignment)
    handle = prepare_local_infernal(state, operation, root=root, policy=POLICY)
    assert handle.read()["stage"] == "prepared"
    assert not (root / "infernal-attempt").exists()
    native.start_prepared(handle)
    result = native.wait_job(handle)
    plan = local_infernal_plan(state.assignment, str(handle.path))
    bundle = json.loads((root / "infernal-attempt/bundle.json").read_bytes())
    assert run_native_infernal(plan) == bundle  # sealed replay, never a second command
    source_after = {name: {"sha256": hashlib.sha256(Path(name).read_bytes()).hexdigest(),
        "size_bytes": Path(name).stat().st_size} for name in source_before}
    assert source_after == source_before
    write_new(root / "source-after.json", source_after)
    write_new(root / "verification-receipt.json", {"observed_at": datetime.now(timezone.utc).isoformat(),
        "driver_returncode": result.returncode, "stdout_path": str(result.stdout_path),
        "stderr_path": str(result.stderr_path), "metadata": result.metadata,
        "native_realized_argv": bundle["realized_argv"], "native_returncode": bundle["returncode"],
        "bundle_sha256": hashlib.sha256((root / "infernal-attempt/bundle.json").read_bytes()).hexdigest(),
        "scope": "Real native producer and lifecycle bridge; no production episode communication verified."})
    index_path = HERE / "runs/index.json"
    index = json.loads(index_path.read_bytes()) if index_path.exists() else {}
    if case in index:
        raise ValueError("verification_case_already_recorded")
    index[case] = {"action_directory": str(root), "execution_id": str(handle.path)}
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    print(json.dumps({"case": case, "driver_returncode": result.returncode,
        "native_returncode": bundle["returncode"], "failures": bundle["failures"],
        "artifacts": bundle["artifacts"], "action_directory": str(root)}, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise ValueError("one_explicit_verification_case_required")
    main(sys.argv[1])
