"""Caller-owned bounded local verification; preserve every invocation receipt."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

run = Path(__file__).parent / ("check_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
run.mkdir()
policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
arguments = sys.argv[1:] or ["tests/test_native_blast_database_result_worker.py", "tests/test_native_blast_database_result_views.py"]
command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", *[str(ROOT / x) if x.startswith("tests/") else x for x in arguments],
           "-q", "--basetemp=" + str(run / "tmp"), "-p", "no:cacheprovider"]
environment = dict(os.environ, PYTHONPATH=str(ROOT) + ":" + str(ROOT / "tests"), PYTHONDONTWRITEBYTECODE="1")
try:
    result = run_local_job(command, cwd=run, policy=policy, env=environment,
        stdout_path=run / "stdout.txt", stderr_path=run / "stderr.txt")
    receipt = dict(command=command, policy=policy.to_dict(), returncode=result.returncode,
        stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path), metadata=result.metadata)
except Exception as error:
    receipt = dict(command=command, policy=policy.to_dict(), error_type=type(error).__name__, error=str(error))
(run / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n")
print(str(run))
print(json.dumps({k: receipt[k] for k in ("returncode", "error_type", "error") if k in receipt}))
sys.exit(receipt.get("returncode", 1))
