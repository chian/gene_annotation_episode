"""Retain every328 check under the caller's20GiB/4GiB/no-wall-cap boundary."""
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    label, *tests = sys.argv[1:]
    directory = HERE / label
    directory.mkdir()
    temporary = directory / "temporary"
    temporary.mkdir()
    tests = tests or [str(ROOT / "tests/test_native_blast_database_convergence_binding.py")]
    command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q", *tests,
        "--basetemp", str(temporary / "pytest"), "-o", "cache_dir=" + str(temporary / "pytest-cache"),
        "--junitxml", str(directory / "junit.xml")]
    policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
    sources = ["gene_annotation_episode/native_blast_database_convergence.py",
        "gene_annotation_episode/native_blast_database_metadata.py", "gene_annotation_episode/blast_native_iteration_records.py",
        "gene_annotation_episode/blast_iteration_inputs.py", "gene_annotation_episode/blast_iteration_calculators.py",
        "gene_annotation_episode/blast_report_collection.py", "tests/test_native_blast_database_convergence_binding.py"]
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources}
    result = run_local_job(command, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
        stderr_path=directory / "stderr.txt", env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(temporary), "XDG_CACHE_HOME": str(directory / "cache")})
    receipt = dict(command=command, policy=policy.to_dict(), returncode=result.returncode,
        metadata=result.metadata, source_hashes=hashes,
        evidence_kind="source-derived synthetic actual313/316/M/311 paths; no native database search or scientific service")
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
    print((directory / "stdout.txt").read_text())
    print((directory / "stderr.txt").read_text())
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
