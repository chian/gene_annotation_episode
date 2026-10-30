"""Run the focused shared-boundary checks with original source and job receipts."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = PACKET / sys.argv[1]
directory.mkdir(exist_ok=False)
tests = ["tests/test_rna_comparison_report_boundary.py", "tests/test_rna_structure_report_boundary.py",
    "tests/test_communication.py"]
sources = ["gene_annotation_episode/" + name for name in (
    "communication.py", "form_reference_validation.py", "runtime.py",
    "rna_structure_result_views.py", "rna_structure_comparison_views.py",
    "rna_structure_comparison_contracts.py", "rna_structure_comparison_inputs.py",
    "rna_structure_comparison_calculations.py", "rna_structure_scan_calculations.py",
    "rna_structure_contracts.py", "rna_structure_topology.py", "rna_structure_native.py",
    "local_jobs.py", "native_lifecycle.py", "_local_job_worker.py")]
sources += tests + [str(Path(__file__).relative_to(ROOT)),
    "verification/tool_graders_rna_comparison_calculations_2026-10-26_367/fixture_helpers.py",
    "verification/tool_graders_rna_comparison_inputs_2026-10-26_366/fixture_helpers.py",
    "tests/fixtures/rna_structure_comparison_inputs_366/hand_examples.json"]
pins = []
for name in sources:
    raw = (ROOT / name).read_bytes()
    snapshot = directory / "sources" / name
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(raw)
    pins.append({"path": name, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)})
(directory / "source_before.json").write_text(json.dumps(pins, indent=2) + "\n")
temporary, cache = directory / "temporary", directory / "cache"
temporary.mkdir()
cache.mkdir()
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp", str(temporary / "pytest"), *[str(ROOT / name) for name in tests]]
environment = {"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
    "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache)}
(directory / "request.json").write_text(json.dumps({"argv": argv, "cwd": str(directory),
    "policy": policy.to_dict(), "environment": environment}, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
        stderr_path=directory / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error)}
after = [{"path": row["path"], "sha256": hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
    "size_bytes": (ROOT / row["path"]).stat().st_size} for row in pins]
(directory / "source_after.json").write_text(json.dumps(after, indent=2) + "\n")
receipt["source_unchanged"] = after == pins
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": receipt["returncode"],
    "source_unchanged": receipt["source_unchanged"]}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
