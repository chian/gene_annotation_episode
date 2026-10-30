"""Bounded runner for exactly one explicitly selected live action."""
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


directory = Path(__file__).resolve().parent
repo = directory.parents[1]
job = directory / "live" / sys.argv[1]
ordinal, action = sys.argv[2], sys.argv[3]
assert action in {"submit", "status", "fetch-json", "fetch-tblout", "fetch-out"}
if action == "submit" and any(job.glob("*-submit")):
    raise RuntimeError("prior submission intent exists; preserve that attempt and do not repeat it")
output = job / f"{ordinal}-{action}"
output.mkdir()
temporary = output / "temporary"
temporary.mkdir()
command = [str(repo / ".venv/bin/python"), str(directory / "capture_action.py"), str(job), action]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
environment = {"PYTHONPATH": str(repo), "PYTHONDONTWRITEBYTECODE": "1",
               "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
               "XDG_CACHE_HOME": str(output / "cache")}
intent = {"command": command, "policy": policy.to_dict(), "environment": environment,
          "selected_action": action, "transport_timeout_seconds": 45,
          "job_input_manifest": str(job / "input-manifest.json")}
(output / "intent.json").write_text(json.dumps(intent, indent=2) + "\n")
result = run_local_job(command, cwd=output, policy=policy, env=environment)
receipt = {**intent, "returncode": result.returncode, "stdout_path": str(result.stdout_path),
           "stderr_path": str(result.stderr_path), "metadata": result.metadata}
(output / "verification-receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({"returncode": result.returncode, "receipt": str(output / "verification-receipt.json")}))
raise SystemExit(result.returncode)
