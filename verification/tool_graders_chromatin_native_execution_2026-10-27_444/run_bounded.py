"""Administrative launch/collection of immutable tests via existing lifecycle."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
sys.path.insert(0, str(REPO))
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect


def pin(path):
    path = Path(path)
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size}


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


operation, name = sys.argv[1:3]
attempt = PACKET / name
handle = NativeJobHandle(attempt / "handle.json")
if operation == "launch":
    attempt.mkdir(exist_ok=False)
    snapshot = attempt / "source_snapshot"
    shutil.copytree(REPO / "gene_annotation_episode", snapshot / "gene_annotation_episode", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(REPO / "method_loop", snapshot / "method_loop", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (snapshot / "tests").mkdir()
    shutil.copyfile(REPO / "tests/test_chromatin_native_execution_c3.py", snapshot / "tests/test_chromatin_native_execution_c3.py")
    for path in snapshot.rglob("*"):
        if path.is_file():
            path.chmod(0o444)
    python = REPO / "reference/episode_tools/.venv/bin/python"
    refsite = REPO / "reference/episode_tools/.venv/lib/python3.12/site-packages"
    rootsite = REPO / ".venv/lib/python3.12/site-packages"
    env = {"PYTHONPATH": os.pathsep.join(map(str, (snapshot, refsite, rootsite))), "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONSAFEPATH": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "C3_ORIGINAL_REPO": str(REPO), "C3_PACKET": str(PACKET), "C3_ATTEMPT": str(attempt),
        "HDF5_PLUGIN_PATH": str(attempt / "no-hdf5-plugins"), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    argv = [str(python), "-B", "-S", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp=" + str(attempt / "pytest"), str(snapshot / "tests/test_chromatin_native_execution_c3.py"), *sys.argv[3:]]
    policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
    pins = [pin(p) for p in sorted(snapshot.rglob("*")) if p.is_file()] + [pin(python), pin(__file__)]
    save(attempt / "source_pins_before.json", pins)
    save(attempt / "selected_request.json", {"argv": argv, "environment": env, "policy": policy.to_dict()})
    prepare_job(argv, cwd=attempt, policy=policy, handle_path=handle.path,
        stdout_path=attempt / "stdout.txt", stderr_path=attempt / "stderr.txt", env=env)
    resume_start(handle)
    print(json.dumps({"handle": str(handle.path), "unit": handle.read()["unit"], "state": status(handle)["state"]}))
elif operation == "collect":
    view = status(handle)
    if not view["terminal"]:
        print(json.dumps(view))
        raise SystemExit(3)
    result = collect(handle)
    before = json.loads((attempt / "source_pins_before.json").read_text())
    after = [pin(r["path"]) for r in before]
    save(attempt / "source_pins_after.json", after)
    save(attempt / "receipt.json", {"returncode": result.returncode, "terminal": view["terminal"], "quiescent": view["quiescent"],
        "metadata": result.metadata, "source_pins_unchanged": before == after, "handle": str(handle.path), "unit": handle.read()["unit"]})
    print(json.dumps({"returncode": result.returncode, "source_pins_unchanged": before == after}))
    raise SystemExit(result.returncode)
else:
    raise ValueError("unknown operation")
