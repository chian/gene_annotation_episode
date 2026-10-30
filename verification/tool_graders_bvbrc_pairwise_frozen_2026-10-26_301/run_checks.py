"""Run the frozen verification under the repository's existing local_jobs."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import traceback

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]
SNAPSHOT = EVIDENCE / "snapshot"
CHECK = SNAPSHOT / "verification/frozen_check_001"
sys.path.insert(0, str(SNAPSHOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
import gene_annotation_episode.local_jobs as local_jobs


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def main():
    if Path(local_jobs.__file__).resolve() != SNAPSHOT / "gene_annotation_episode/local_jobs.py":
        raise RuntimeError("local_jobs_must_be_frozen")
    CHECK.mkdir(parents=True, exist_ok=False)
    (CHECK / "temporary").mkdir()
    command = [str(ROOT / ".venv/bin/python"), "-B", str(EVIDENCE / "run_frozen_pytest.py")]
    policy = LocalJobPolicy(20 * 1024 ** 3, 4 * 1024 ** 3, None)
    environment = {"PYTHONPATH": str(SNAPSHOT) + ":" + str(SNAPSHOT / "tests"),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1", "TMPDIR": str(CHECK / "temporary")}
    request = {"command": command, "cwd": str(SNAPSHOT), "env": environment,
        "policy": policy.to_dict(), "started_at": datetime.now(timezone.utc).isoformat(),
        "local_jobs_path": str(Path(local_jobs.__file__).resolve()),
        "snapshot_manifest_sha256": hashlib.sha256((EVIDENCE / "SOURCE_SNAPSHOT_MANIFEST.json").read_bytes()).hexdigest(),
        "selected_test": "tests/test_bvbrc_homology_pairwise_workflow.py",
        "runner_sha256": hashlib.sha256((EVIDENCE / "run_frozen_pytest.py").read_bytes()).hexdigest()}
    write(CHECK / "request.json", request)
    print(json.dumps({"status": "starting", "request": str(CHECK / "request.json")}), flush=True)
    try:
        result = run_local_job(command, cwd=SNAPSHOT, policy=policy,
            stdout_path=CHECK / "stdout.txt", stderr_path=CHECK / "stderr.txt", env=environment)
    except BaseException as error:
        write(CHECK / "launcher_failure.json", {"type": type(error).__name__, "message": str(error),
            "traceback": traceback.format_exc(), "at": datetime.now(timezone.utc).isoformat()})
        raise
    receipt = asdict(result)
    receipt.update(stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path),
        finished_at=datetime.now(timezone.utc).isoformat())
    write(CHECK / "receipt.json", receipt)
    print(json.dumps({"returncode": result.returncode, "receipt": str(CHECK / "receipt.json")}), flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
