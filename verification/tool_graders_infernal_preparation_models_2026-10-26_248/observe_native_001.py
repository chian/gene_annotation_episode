"""Explicit tiny format/alias/failure observations; never imported by a grader."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OLD = ROOT / "verification/tool_graders_infernal_preparation_boundaries_2026-10-26_246/native"
BIN = ROOT / "resources/software/infernal-1.1.5-install/bin"
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, program, args, inputs, text_inputs=None):
    directory = BASE / "native" / name
    directory.mkdir(parents=True, exist_ok=False)
    for source, target in inputs:
        shutil.copyfile(source, directory / target)
    for target, content in (text_inputs or {}).items():
        (directory / target).write_bytes(content if isinstance(content, bytes) else content.encode())
    command = [str(BIN / program), *args]
    request = {"command": command, "binary_sha256": digest(BIN / program), "policy": POLICY.to_dict(),
        "inputs": [{"path": p.name, "sha256": digest(p), "size_bytes": p.stat().st_size} for p in directory.iterdir()],
        "started_at": datetime.now(timezone.utc).isoformat()}
    (directory / "request.json").write_text(json.dumps(request, indent=2)+"\n")
    result = run_local_job(command, cwd=directory, policy=POLICY,
        stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
        env={"OMP_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    receipt = {**request, "returncode": result.returncode, "metadata": result.metadata,
        "finished_at": datetime.now(timezone.utc).isoformat(), "artifacts": [
            {"path": str(p.relative_to(directory)), "sha256": digest(p), "size_bytes": p.stat().st_size}
            for p in directory.rglob("*") if p.is_file()]}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
    print(name, result.returncode, flush=True)
    return directory


if __name__ == "__main__":
    group = sys.argv[1]
    if group == "convert":
        for mode in ("binary", "legacy"):
            run("cmconvert_"+mode+"_to_ascii", "cmconvert", ["-a", "-o", "converted.cm", "model.cm"],
                [(OLD / ("cmconvert_"+mode) / "converted.out", "model.cm")])
    elif group == "fetch":
        original = OLD / "cmcalibrate_tiny/model.cm"
        run("cmfetch_alias_unindexed", "cmfetch", ["-f", "-o", "fetched.cm", "models.cm", "keys.txt"],
            [(original, "models.cm")], {"keys.txt": "fixture246\nTEST246\n"})
        index = run("cmfetch_alias_index", "cmfetch", ["--index", "models.cm"], [(original, "models.cm")])
        run("cmfetch_alias_indexed", "cmfetch", ["-f", "-o", "fetched.cm", "models.cm", "keys.txt"],
            [(original, "models.cm"), (index / "models.cm.ssi", "models.cm.ssi")], {"keys.txt": "fixture246\nTEST246\n"})
        run("cmfetch_duplicate_request_failure", "cmfetch", ["-f", "-o", "fetched.cm", "models.cm", "keys.txt"],
            [(original, "models.cm")], {"keys.txt": "fixture246\nfixture246\n"})
    elif group == "press":
        original = OLD / "cmcalibrate_tiny/model.cm"
        run("cmpress_calibrated", "cmpress", ["models.cm"], [(original, "models.cm")])
        run("cmpress_duplicate_failure", "cmpress", ["models.cm"], [], {"models.cm": original.read_bytes()*2})
    elif group == "fetch_empty":
        run("cmfetch_missing_all_unindexed", "cmfetch", ["-f", "-o", "fetched.cm", "models.cm", "keys.txt"],
            [(OLD / "cmcalibrate_tiny/model.cm", "models.cm")], {"keys.txt": "missing_key\n"})
    else:
        raise ValueError("select convert, fetch or press")
