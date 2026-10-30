"""Administrative immutable test staging and original-handle observation.

Scientific/capture tests execute only under the existing native lifecycle.
Collection never relaunches an unfinished attempt or deletes its failure files.
"""
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
from gene_annotation_episode import native_lifecycle as native


def pin(path):
    path = Path(path)
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return {"path": str(path), "sha256": hasher.hexdigest(), "size_bytes": path.stat().st_size}


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


operation, name = sys.argv[1:3]
attempt = PACKET / name
handle = native.NativeJobHandle(attempt / "handle.json")
if operation == "launch":
    attempt.mkdir(exist_ok=False)
    snapshot, fixtures = attempt / "source_snapshot", attempt / "fixtures"
    shutil.copytree(REPO / "gene_annotation_episode", snapshot / "gene_annotation_episode", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(REPO / "method_loop", snapshot / "method_loop", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (snapshot / "tests").mkdir()
    shutil.copyfile(REPO / "tests/test_native_chromatin_interaction_capture.py", snapshot / "tests/test_native_chromatin_interaction_capture.py")
    shutil.copyfile(__file__, attempt / "run_bounded.py")
    fixtures.mkdir()
    shutil.copyfile(REPO / "verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json", fixtures / "WORKED_RECORDS.json")
    native_inputs = {}
    for ordinal, case in enumerate(("raw", "weighted", "insulation")):
        root = REPO / "verification/tool_graders_chromatin_native_execution_2026-10-27_444/check007/pytest" / f"test_real440_native_producer_a{ordinal}" / ".episode-operations/ee8cf68818af282810af73716ab17d4021635f18874450bed4ce9da4c12c0801/fccaceaa328ade276f1ce4bcca18842fb027d81859945b80e1fe7f3a4ab63880"
        original = native.NativeJobHandle(root / "native.json")
        view = native.status(original)
        if not (view["terminal"] and view["quiescent"] and view["metadata"]["native_returncode"] == 0):
            raise ValueError("original_native_fixture_not_terminal_success")
        plan = json.loads((root / "chromatin-plan.json").read_text())
        output = Path(plan["attempt_directory"])
        native_inputs[case] = {"evidence_kind": "genuinely_executed_native_on_serialized_synthetic_source",
            "authority": "C3 fixture action references, not full episode authority",
            "plan": pin(root / "chromatin-plan.json"), "handle": pin(original.path),
            "terminal": view["terminal"], "quiescent": view["quiescent"], "native_returncode": view["metadata"]["native_returncode"],
            "closure_observation": view,
            "producer_pins": [pin(output / spec["relative_path"]) for spec in plan["outputs"] if (output / spec["relative_path"]).is_file()]}
    save(fixtures / "NATIVE_INPUTS.json", native_inputs)
    python = attempt / "runtime/python"
    python.parent.mkdir()
    shutil.copyfile("/usr/bin/python3.12", python)
    python.chmod(0o555)
    for directory in (snapshot, fixtures):
        for path in directory.rglob("*"):
            if path.is_file():
                path.chmod(0o444)
    (attempt / "run_bounded.py").chmod(0o444)
    refsite = REPO / "reference/episode_tools/.venv/lib/python3.12/site-packages"
    rootsite = REPO / ".venv/lib/python3.12/site-packages"
    for directory in ("tmp", "cache"):
        (attempt / directory).mkdir()
    environment = {"PYTHONPATH": os.pathsep.join(map(str, (snapshot, refsite, rootsite))), "PYTHONHOME": "/usr",
        "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONSAFEPATH": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "TMPDIR": str(attempt / "tmp"), "TMP": str(attempt / "tmp"), "TEMP": str(attempt / "tmp"),
        "XDG_CACHE_HOME": str(attempt / "cache"), "PIP_CACHE_DIR": str(attempt / "cache/pip"),
        "CHROMATIN_CAPTURE_FIXTURES": str(fixtures), "CHROMATIN_CAPTURE_ATTEMPT": str(attempt),
        "HDF5_PLUGIN_PATH": str(attempt / "unbound-hdf5-plugins"), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    argv = [str(python), "-B", "-S", "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "--basetemp=" + str(attempt / "pytest"), str(snapshot / "tests/test_native_chromatin_interaction_capture.py"), *sys.argv[3:]]
    policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
    pins = [pin(p) for directory in (snapshot, fixtures) for p in sorted(directory.rglob("*")) if p.is_file()]
    pins.extend([pin(python), pin(attempt / "run_bounded.py")])
    save(attempt / "source_pins_before.json", pins)
    save(attempt / "selected_request.json", {"argv": argv, "environment": environment, "policy": policy.to_dict()})
    native.prepare_job(argv, cwd=attempt, policy=policy, handle_path=handle.path,
        stdout_path=attempt / "stdout.txt", stderr_path=attempt / "stderr.txt", env=environment)
    native.resume_start(handle)
    print(json.dumps({"handle": str(handle.path), "unit": handle.read()["unit"], "state": native.status(handle)["state"]}))
elif operation == "collect":
    view = native.status(handle)
    if not view["terminal"]:
        print(json.dumps({"handle": str(handle.path), "state": view["state"], "terminal": view["terminal"], "quiescent": view["quiescent"]}))
        raise SystemExit(3)
    result = native.collect(handle)
    before = json.loads((attempt / "source_pins_before.json").read_text())
    after = [pin(row["path"]) for row in before]
    native_inputs = json.loads((attempt / "fixtures/NATIVE_INPUTS.json").read_text())
    native_pins = [row for evidence in native_inputs.values() for row in [evidence["plan"], evidence["handle"], *evidence["producer_pins"]]]
    current_native = [pin(row["path"]) for row in native_pins]
    save(attempt / "source_pins_after.json", after)
    save(attempt / "native_pins_after.json", current_native)
    save(attempt / "receipt.json", {"returncode": result.returncode, "terminal": view["terminal"], "quiescent": view["quiescent"],
        "metadata": result.metadata, "source_pins_unchanged": before == after, "native_pins_unchanged": native_pins == current_native,
        "handle": str(handle.path), "unit": handle.read()["unit"]})
    print(json.dumps({"returncode": result.returncode, "source_pins_unchanged": before == after, "native_pins_unchanged": native_pins == current_native}))
    raise SystemExit(result.returncode)
else:
    raise ValueError("unknown operation")
