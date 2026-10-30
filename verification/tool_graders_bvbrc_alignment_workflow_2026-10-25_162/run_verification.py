"""Run the existing full alignment Workflow suite exactly once and retain receipts."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
OWNED = Path(__file__).resolve().parent
TEST = ROOT / "tests/test_bvbrc_alignment_episode_flow.py"
PYTHON = ROOT / ".venv/bin/python"


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def write_new(name, value):
    with (OWNED / name).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    # A prior receipt prevents accidental reuse or duplicate launching.
    if any((OWNED / name).exists() for name in
           ("command.json", "process-start.json", "process-terminal.json", "pytest.log")):
        raise RuntimeError("This verification directory already has a run receipt")
    sys.path[:0] = [str(ROOT / "tests"), str(ROOT)]
    spec = importlib.util.spec_from_file_location("alignment_workflow_existing_test", TEST)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    explicit = set().union(*(module.explicit_source_paths(case) for case in module.CASES))
    used = explicit | module.loaded_source_paths()
    hashes = module.source_hashes(used)
    write_new("SOURCE_HASHES_BEFORE.json", hashes)
    write_new("SOURCE_CLOSURE_BEFORE.json", {
        "explicit_inputs": sorted(str(path.relative_to(ROOT)) for path in explicit),
        "loaded_modules": sorted(str(path.relative_to(ROOT)) for path in module.loaded_source_paths()),
        "existing_test_sha256": digest_file(TEST),
        "runner_sha256": digest_file(Path(__file__)),
    })
    run_parent = module.EVIDENCE / "runs"
    earlier = sorted(path.name for path in run_parent.iterdir() if path.is_dir())
    write_new("EXISTING_RUN_DIRECTORIES.json", earlier)
    argv = [str(PYTHON), "-m", "pytest", "tests/test_bvbrc_alignment_episode_flow.py",
            "-vv", "--junitxml=" + str(OWNED / "pytest.junit.xml")]
    write_new("command.json", {"argv": argv, "shell_display": shlex.join(argv),
        "cwd": str(ROOT), "stdout_and_stderr": str(OWNED / "pytest.log"),
        "wrapper_pid": os.getpid(), "python": sys.executable,
        "python_version": sys.version, "captured_at": timestamp(),
        "scope": "controlled HTTP and scripted choices over retained native bytes",
        "production_changes_authorized": False})
    started_at = timestamp()
    start = time.monotonic()
    with (OWNED / "pytest.log").open("xb") as log:
        process = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        write_new("process-start.json", {"pid": process.pid, "wrapper_pid": os.getpid(),
            "started_at": started_at, "command": argv, "status": "running"})
        print(json.dumps({"pytest_pid": process.pid, "wrapper_pid": os.getpid(),
            "started_at": started_at, "log": str(OWNED / "pytest.log")}), flush=True)
        returncode = process.wait()
    later = sorted(path.name for path in run_parent.iterdir() if path.is_dir())
    new_runs = [str(run_parent / name) for name in later if name not in earlier]
    write_new("process-terminal.json", {"pid": process.pid, "wrapper_pid": os.getpid(),
        "started_at": started_at, "ended_at": timestamp(), "elapsed_seconds": time.monotonic() - start,
        "returncode": returncode, "status": "exited", "new_run_directories": new_runs,
        "log_sha256": digest_file(OWNED / "pytest.log"),
        "junit_sha256": digest_file(OWNED / "pytest.junit.xml") if (OWNED / "pytest.junit.xml").is_file() else None})
    write_new("SOURCE_HASHES_AFTER.json", module.source_hashes(used))
    print(json.dumps({"returncode": returncode, "new_run_directories": new_runs}), flush=True)
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
