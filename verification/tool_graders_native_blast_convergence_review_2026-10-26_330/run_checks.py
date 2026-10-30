"""Keep a new, bounded local verification receipt for this read-only review."""
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCES = [
    "gene_annotation_episode/native_blast_database_convergence.py",
    "gene_annotation_episode/native_blast_database_metadata.py",
    "gene_annotation_episode/native_blast_database_result_worker.py",
    "gene_annotation_episode/native_blast_database_result_views.py",
    "gene_annotation_episode/blast_native_iteration_records.py",
    "gene_annotation_episode/blast_iteration_inputs.py",
    "gene_annotation_episode/blast_iteration_calculators.py",
    "tests/test_native_blast_database_convergence_binding.py",
    "tests/test_native_blast_database_convergence_worker.py",
    "tests/test_native_blast_convergence_review_330.py",
]


def identities():
    return [dict(path=name, sha256=hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
        size_bytes=(ROOT / name).stat().st_size) for name in SOURCES]


def main():
    label, *tests = sys.argv[1:]
    directory = HERE / label
    directory.mkdir()
    temporary = directory / "temporary"
    temporary.mkdir()
    tests = tests or ["tests/test_native_blast_convergence_review_330.py"]
    command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q",
        *[str(ROOT / name) for name in tests], "--basetemp", str(temporary / "pytest"),
        "-o", "cache_dir=" + str(temporary / "pytest-cache"),
        "--junitxml", str(directory / "junit.xml")]
    before = identities()
    policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
    result = run_local_job(command, cwd=directory, policy=policy,
        stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
        env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(temporary), "XDG_CACHE_HOME": str(directory / "cache")})
    receipt = dict(command=command, policy=policy.to_dict(), returncode=result.returncode,
        metadata=result.metadata, before=before, after=identities(),
        evidence_kind="synthetic retained-input worker/bridge checks; no BLAST scientific execution")
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
    print((directory / "stdout.txt").read_text())
    print((directory / "stderr.txt").read_text())
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
