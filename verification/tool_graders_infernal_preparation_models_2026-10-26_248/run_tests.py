"""Run owned pure-module tests through the existing local resource wrapper."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
name = sys.argv[1]
paths = sys.argv[2:] or ["tests/test_infernal_preparation_models.py", "tests/test_infernal_preparation_artifacts.py"]
directory = BASE / name
directory.mkdir(parents=True, exist_ok=False)
command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
           *[str(ROOT / p) for p in paths]]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
request = {"command": command, "policy": policy.to_dict(), "started_at": datetime.now(timezone.utc).isoformat()}
(directory / "request.json").write_text(json.dumps(request, indent=2)+"\n")
result = run_local_job(command, cwd=directory, policy=policy,
    stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
    env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
receipt = {**request, "returncode": result.returncode, "metadata": result.metadata,
    "finished_at": datetime.now(timezone.utc).isoformat(), "files": []}
for path in directory.rglob("*"):
    if path.is_file():
        receipt["files"].append({"path": str(path.relative_to(directory)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size})
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
print((directory / "stdout.txt").read_text())
print((directory / "stderr.txt").read_text())
print("returncode", result.returncode)
