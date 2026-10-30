"""Snapshot the executed project sources and retain each bounded pytest attempt."""
from pathlib import Path
import hashlib
import json
import os
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
directory = PACKET / sys.argv[1]
directory.mkdir(exist_ok=False)
snapshot = directory / "source_snapshot"
temporary, cache = directory / "temporary", directory / "cache"
temporary.mkdir()
cache.mkdir()
tests = sys.argv[2:] or ["tests/test_protein_structure_selection.py"]
files = []
for package in ("gene_annotation_episode", "method_loop"):
    files += [p for p in (REPO / package).rglob("*") if p.is_file()
        and "__pycache__" not in p.parts and p.suffix != ".pyc"]
files += [REPO / test.split("::")[0] for test in tests]
if any("test_literature_controlled_response_communication.py" in test
       or "test_literature_gel_communication.py" in test for test in tests):
    files += [REPO / "tests" / name for name in (
        "literature_controlled_response_worker_fixture_095.py",
        "literature_gel_worker_fixture_107.py",
        "test_literature_controlled_response_v2_inputs.py",
        "test_literature_controlled_response_v3_inputs.py",
        "test_literature_gel_inputs.py", "test_runtime.py")]
    design = REPO / "verification/literature_reference_evidence_2026-10-25_001/a105_controlled_full_source_design_069"
    files += [design / "CONSTRUCTED_SOURCE_CASES_001.json", design / "CONSTRUCTED_SOURCE_ROSTER_001.json"]
    files += [design / row["encoded_image_file"] for row in json.loads(
        (design / "CONSTRUCTED_SOURCE_ROSTER_001.json").read_bytes()) if row["encoded_image_file"] is not None]
files += [REPO / "pyproject.toml", Path(__file__)]
files += [p for p in (PACKET / "prechange").iterdir() if p.is_file()]
for name in ("tool_graders_protein_structure_inputs_2026-10-27_386",
             "tool_graders_protein_structure_execution_2026-10-27_390"):
    source = REPO / "verification" / name
    files.append(source / "fixture_helpers.py")
    if (source / "fixtures").is_dir():
        files += [p for p in (source / "fixtures").rglob("*") if p.is_file()]
files += [p for p in (REPO / "verification/tool_graders_protein_structure_shared_contract_2026-10-27_380").iterdir() if p.is_file()]
files += [p for p in (REPO / "verification/tool_graders_protein_structure_result_worker_2026-10-27_393/fixtures").iterdir() if p.is_file()]
if (PACKET / "fixtures").exists():
    files += [p for p in (PACKET / "fixtures").iterdir() if p.is_file()]
pins = []
for source in sorted(set(files)):
    raw = source.read_bytes()
    relative = source.relative_to(REPO)
    destination = snapshot / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    destination.chmod(0o444)
    pins.append({"path": str(relative), "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)})
for path in sorted([p for p in snapshot.rglob("*") if p.is_dir()], key=lambda p: len(p.parts), reverse=True):
    path.chmod(0o555)
snapshot.chmod(0o555)
(directory / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")
# Imports and the worker's PYTHONPATH both prefer this fixed snapshot. The
# checkout remains available only to the control wrapper for after-run pins.
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(REPO / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp", str(temporary / "pytest"), "--rootdir", str(snapshot),
    *[str(snapshot / test) for test in tests]]
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
request = {"argv": argv, "cwd": str(directory), "policy": policy.to_dict(), "environment": environment,
    "executed_source_root": str(snapshot), "source_snapshot_readonly": True}
(directory / "selected_request.json").write_text(json.dumps(request, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
        stderr_path=directory / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error)}
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
    executed_after = after(snapshot)
    checkout_after = after(REPO)
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
