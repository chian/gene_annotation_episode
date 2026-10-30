"""Run explicitly selected tests through the existing bounded local facility."""
import json
import os
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

root = Path(__file__).resolve().parents[2]
directory = Path(__file__).resolve().parent / sys.argv[1]
directory.mkdir(exist_ok=False)
command = [str(root / ".venv/bin/python"), "-B", "-m", "pytest", "-q", *[
    str(root / name) for name in (sys.argv[2:] or ["tests/test_native_blast_database_metadata.py"])]]
result = run_local_job(command, cwd=directory, policy=LocalJobPolicy(
    memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3, wall_seconds=None),
    stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
    env={**os.environ, "PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(directory)})
(directory / "receipt.json").write_text(json.dumps(dict(command=command, returncode=result.returncode,
    metadata=result.metadata, stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path)), indent=2) + "\n")
print(json.dumps(dict(returncode=result.returncode, receipt=str(directory / "receipt.json"))))
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
