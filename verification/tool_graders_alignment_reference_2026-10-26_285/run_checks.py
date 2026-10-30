"""Run supplied-data verification under the existing local resource lifecycle."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = Path(__file__).resolve().parent / sys.argv[1]
directory.mkdir()
policy = LocalJobPolicy(memory_bytes=20*1024**3, scratch_bytes=4*1024**3)
command = [str(ROOT/".venv/bin/python"), "-m", "pytest", "-q", "-o", "addopts=",
           "-p", "no:cacheprovider", "--basetemp", str(directory/"temporary"),
           *[str(ROOT/name) for name in (sys.argv[2:] or ["tests/test_alignment_site_graders.py"])]]
result = run_local_job(command, cwd=directory, policy=policy,
    stdout_path=directory/"stdout.log", stderr_path=directory/"stderr.log",
    env={**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
receipt = {"command": command, "policy": policy.to_dict(), "returncode": result.returncode,
           "metadata": result.metadata}
(directory/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
print(json.dumps({"returncode": result.returncode, "stdout": str(result.stdout_path), "stderr": str(result.stderr_path)}))
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
