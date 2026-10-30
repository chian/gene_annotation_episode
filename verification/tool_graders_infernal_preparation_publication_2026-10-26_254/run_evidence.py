"""Collect complete saved numerical examples under the same local limits."""
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


root = Path(__file__).resolve().parents[2]
work = Path(__file__).resolve().parent
destination = work / "evidence_001"
destination.mkdir()
temporary = destination / "temporary"
temporary.mkdir()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
command = [str(root / ".venv/bin/python"), str(work / "collect_evidence.py"), *sys.argv[1:]]
result = run_local_job(command, cwd=destination, policy=policy,
    env={"PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary), "TMP": str(temporary),
        "TEMP": str(temporary), "XDG_CACHE_HOME": str(destination / "cache")})
(destination / "receipt.json").write_text(json.dumps({"command": command, "policy": policy.to_dict(),
    "returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}, indent=2, sort_keys=True) + "\n")
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
raise SystemExit(result.returncode)
