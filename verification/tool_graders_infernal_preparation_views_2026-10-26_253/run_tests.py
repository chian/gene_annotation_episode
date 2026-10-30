"""Run owned tests through the existing 20-GiB/4-GiB local job boundary."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
directory = BASE / sys.argv[1]
directory.mkdir(parents=True, exist_ok=False)
audit = sys.argv[2:] == ["--audit"]
paths = ([str((BASE / "audit_projection.py").relative_to(ROOT))] if audit else
         sys.argv[2:] or ["tests/test_infernal_preparation_result_views.py"])
command = ([str(ROOT / ".venv/bin/python"), str(ROOT / paths[0])] if audit else
           [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
            "--basetemp", str(directory / "pytest"), *[str(ROOT / path) for path in paths]])
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
source_paths = ["gene_annotation_episode/infernal_preparation_result_views.py", *paths]
request = {"command": command, "policy": policy.to_dict(), "started_at": datetime.now(timezone.utc).isoformat(),
    "source_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in source_paths}}
(directory / "request.json").write_text(json.dumps(request, indent=2) + "\n")
result = run_local_job(command, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
    stderr_path=directory / "stderr.txt", env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
receipt = {**request, "returncode": result.returncode, "metadata": result.metadata,
    "finished_at": datetime.now(timezone.utc).isoformat()}
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print((directory / "stdout.txt").read_text())
print((directory / "stderr.txt").read_text())
print("returncode", result.returncode)
raise SystemExit(result.returncode)
