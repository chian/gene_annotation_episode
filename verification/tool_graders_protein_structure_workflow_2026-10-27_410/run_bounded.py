"""Run only packet410 Workflow checks in a read-only source snapshot."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
directory = PACKET / sys.argv[1]
directory.mkdir(exist_ok=False)
snapshot = directory / "source_snapshot"
temporary, cache = directory / "temporary", directory / "cache"
temporary.mkdir()
cache.mkdir()
diagnostic = len(sys.argv) > 2 and sys.argv[2] in {"--diagnose", "--diagnose-report"}
tests = [] if diagnostic else sys.argv[2:] or ["tests/test_protein_structure_workflow_integration.py"]
files = [path for package in ("gene_annotation_episode", "method_loop")
    for path in (REPO / package).rglob("*") if path.is_file()
    and "__pycache__" not in path.parts and path.suffix != ".pyc"]
files += [REPO / "pyproject.toml", Path(__file__),
    PACKET / "fixture_helpers.py", PACKET / "diagnose_retained.py", REPO / "tests/test_protein_structure_workflow_integration.py"]
for packet in ("tool_graders_protein_structure_execution_2026-10-27_390",
               "tool_graders_protein_structure_inputs_2026-10-27_386"):
    files.append(REPO / "verification" / packet / "fixture_helpers.py")
files.extend((REPO / "verification/tool_graders_protein_structure_inputs_2026-10-27_386/fixtures").glob("*"))
files.extend(path for path in (REPO / "research/slotted_process_library/publications/2026-10-24-001").rglob("*") if path.is_file())
pins = []
for source in sorted(set(files)):
    raw = source.read_bytes()
    relative = source.relative_to(REPO)
    destination = snapshot / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    destination.chmod(0o444)
    pins.append({"path": str(relative), "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)})
for path in sorted([path for path in snapshot.rglob("*") if path.is_dir()], key=lambda path: len(path.parts), reverse=True):
    path.chmod(0o555)
snapshot.chmod(0o555)
(directory / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(REPO / ".venv/bin/python"), "-B", "-m", "pytest", "-vv", "--tb=short",
    "-p", "no:cacheprovider", "--basetemp", str(temporary / "pytest"),
    "--rootdir", str(snapshot), "--junitxml", str(directory / "junit.xml"),
    *[str(snapshot / test) for test in tests]]
if diagnostic:
    argv = [str(REPO / ".venv/bin/python"), "-B", str(snapshot / Path(__file__).relative_to(REPO).parent / "diagnose_retained.py"),
        str(PACKET / sys.argv[3] / "temporary/pytest/protein-workflow4100"), sys.argv[2]]
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1",
    "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
    "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
(directory / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(directory),
    "policy": policy.to_dict(), "environment": environment, "executed_source_root": str(snapshot),
    "source_snapshot_readonly": True, "selected_tests": tests}, indent=2) + "\n")
receipt = {"returncode": None}
try:
    result = run_local_job(argv, cwd=directory, policy=policy,
        stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt.update(exception_type=type(error).__name__, exception=str(error))
finally:
    def after(root):
        rows = []
        for row in pins:
            path = root / row["path"]
            if path.is_file():
                raw = path.read_bytes()
                rows.append({"path": row["path"], "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)})
            else:
                rows.append({"path": row["path"], "missing": True})
        return rows
    executed_after, checkout_after = after(snapshot), after(REPO)
    (directory / "source_pins_after.json").write_text(json.dumps(executed_after, indent=2) + "\n")
    (directory / "checkout_source_pins_after.json").write_text(json.dumps(checkout_after, indent=2) + "\n")
    receipt["executed_source_pins_unchanged"] = executed_after == pins
    receipt["checkout_source_drift"] = [{"before": a, "after": b} for a, b in zip(pins, checkout_after) if a != b]
    receipt["executed_source_root"] = str(snapshot)
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": receipt["returncode"],
    "executed_source_pins_unchanged": receipt["executed_source_pins_unchanged"],
    "checkout_source_drift_count": len(receipt["checkout_source_drift"])}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
