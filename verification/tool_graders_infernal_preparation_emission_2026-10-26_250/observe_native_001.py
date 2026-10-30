"""Explicit tiny cmemit format observations; never imported by production code."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRIOR = ROOT / "verification/tool_graders_infernal_preparation_boundaries_2026-10-26_246"
EXECUTABLE = ROOT / "resources/software/infernal-1.1.5-install/bin/cmemit"
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, flags, *, unstructured=False, duplicate=False, source_override=None):
    folder = BASE / "native" / name
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "cache").mkdir()
    source = source_override or PRIOR / ("native/cmbuild_noss/built.cm" if unstructured else "native/cmcalibrate_tiny/model.cm")
    data = source.read_bytes()
    (folder / "model.cm").write_bytes(data + data if duplicate else data)
    command = [str(EXECUTABLE), *flags, "--seed", "181", "-o", "emitted.out", "model.cm"]
    environment = {"XDG_CACHE_HOME": str(folder / "cache"), "OMP_NUM_THREADS": "1",
                   "INFERNAL_NCPU": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    request = {"command": command, "environment": environment,
               "policy": POLICY.to_dict(), "cwd": str(folder),
               "binary_sha256": sha(EXECUTABLE), "input_sha256": sha(folder / "model.cm"),
               "source_path": str(source), "source_sha256": sha(source),
               "input_transform": "duplicate_complete_records" if duplicate else "none",
               "started_at": datetime.now(timezone.utc).isoformat()}
    (folder / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    result = run_local_job(command, cwd=folder, policy=POLICY,
                          stdout_path=folder / "stdout.txt", stderr_path=folder / "stderr.txt", env=environment)
    receipt = {**request, "returncode": result.returncode, "metadata": result.metadata,
               "finished_at": datetime.now(timezone.utc).isoformat(), "files": [
                   {"path": str(p.relative_to(folder)), "size_bytes": p.stat().st_size, "sha256": sha(p)}
                   for p in sorted(folder.rglob("*")) if p.is_file()]}
    (folder / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(name, result.returncode, flush=True)


if __name__ == "__main__":
    for fmt in ("Pfam", "AFA", "A2M", "Clustal", "Phylip"):
        run("aligned_" + fmt.lower(), ["-a", "-N", "3", "--outformat", fmt])
    for aligned in (False, True):
        for hmm in (False, True):
            run("trace_" + ("aligned" if aligned else "unaligned") + ("_hmm" if hmm else "_cm"),
                ["-a" if aligned else "-u", "-N", "2", "--tfile", "traces.txt", *(["--hmmonly"] if hmm else [])])
    run("consensus_hmm", ["-c", "--hmmonly"])
    run("consensus_dna", ["-c", "--dna"])
    run("aligned_dna_hmm", ["-a", "-N", "2", "--hmmonly", "--dna"])
    run("unaligned_dna", ["-u", "-N", "2", "--dna", "--idx", "7"])
    run("unaligned_auto_hmm", ["-u", "-N", "2"], unstructured=True)
    run("unaligned_local_exp", ["-u", "-N", "2", "-l", "--exp", "0.8"])
    for flags, label in ((["--u5p"], "5p"), (["--u3p"], "3p"), (["--u5p", "--u3p"], "both")):
        run("unaligned_trunc_" + label, ["-u", "-N", "2", *flags])
    run("embedded", ["-u", "-N", "2", "-e", "40", "--iid"])
    run("embedded_3p", ["-u", "-N", "2", "-e", "40", "--iid", "--u3p"])
    run("aligned_trunc_fixed", ["-a", "-N", "2", "--a5p", "3", "--a3p", "9"])
    run("aligned_trunc_random", ["-a", "-N", "2", "--a5p", "0", "--a3p", "0"])
    run("aligned_trunc_invalid", ["-a", "-N", "2", "--a5p", "0", "--a3p", "9"])
    run("duplicate_models", ["-a", "-N", "2"], duplicate=True)
