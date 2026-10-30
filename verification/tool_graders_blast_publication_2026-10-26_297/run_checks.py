"""Explicit operator verification through the shared bounded local-job runner."""
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
directory = Path(__file__).resolve().parent / sys.argv[1]
directory.mkdir()
(directory / "temporary").mkdir()
policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
result = run_local_job([str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q",
    str(ROOT / "tests/test_blast_pairwise_result_views.py"), str(ROOT / "tests/test_blast_pairwise_publication.py"),
    "--basetemp", str(directory / "temporary/pytest"), "-o", "cache_dir=" + str(directory / "pytest-cache"), *sys.argv[2:]],
    cwd=directory, policy=policy, stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
    env={"PYTHONPATH": str(ROOT), "TMPDIR": str(directory / "temporary")})
(directory / "receipt.json").write_text(json.dumps(result.metadata, indent=2) + "\n")
print(json.dumps({"returncode": result.returncode, "directory": str(directory)}))
print((directory / "stdout.txt").read_text())
print((directory / "stderr.txt").read_text())
raise SystemExit(result.returncode)
