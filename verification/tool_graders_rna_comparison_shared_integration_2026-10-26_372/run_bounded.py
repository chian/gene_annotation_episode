"""Retain exact local-jobs verification requests, output and source pins."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
sys.path.insert(0, str(REPO))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
from gene_annotation_episode.scientific_process_episodes import _IMPLEMENTATION_FILES

directory = PACKET / sys.argv[1]
directory.mkdir(exist_ok=False)
tests = sys.argv[2:] or ["tests/test_rna_comparison_workflow.py", "tests/test_rna_comparison_shared_binding.py"]
files = [REPO / "gene_annotation_episode" / name for name in (
    "execution_episodes.py", "execution_progress.py", "communication.py", "episode_receipts.py",
    "episode_commissions.py", "bvbrc_appservice_custody.py",
    "rna_structure_comparison_results.py", "rna_structure_comparison_returns.py", "rna_structure_comparison_operands.py",
    "rna_structure_comparison_worker.py", "rna_structure_comparison_publication.py", "native_rna_structure_returns.py",
    "native_rna_structure_results.py", "rna_structure_comparison_views.py", "rna_structure_comparison_contracts.py",
    "rna_structure_comparison_inputs.py", "rna_structure_comparison_calculations.py",
    "rna_structure_scan_calculations.py", "rna_structure_contracts.py", "rna_structure_topology.py",
    "rna_structure_native.py", "local_jobs.py", "native_lifecycle.py", "_local_job_worker.py")]
files += [REPO / p.split("::")[0] for p in tests]
files += [REPO / "tests" / name for name in (
    "test_rna_comparison_workflow.py", "test_rna_comparison_shared_binding.py",
    "test_rna_structure_comparison_publication.py")]
files += [REPO / "gene_annotation_episode" / name for name in _IMPLEMENTATION_FILES]
files += [REPO / "gene_annotation_episode" / name for name in (
    "runtime.py", "episode_bindings.py", "episode_return_records.py", "form_reference_validation.py",
    "practical_yield.py", "practical_execution_records.py", "practical_receipt_information.py")]
files += [PACKET / name for name in ("run_bounded.py",)]
files += list((REPO / "tests/fixtures/rna_comparison_shared_372").glob("*"))
files += [REPO / "verification" / name / "fixture_helpers.py" for name in (
    "tool_graders_rna_comparison_inputs_2026-10-26_366",
    "tool_graders_rna_comparison_calculations_2026-10-26_367",
    "tool_graders_rna_comparison_worker_2026-10-26_369")]
files += [REPO / "tests/fixtures/rna_structure_comparison_inputs_366/hand_examples.json"]
files += [REPO / "verification/tool_graders_rna_comparison_contract_2026-10-26_362" / name
    for name in ("PLAN_001.md", *("CONTRACT_ADDENDUM_%03d.md" % n for n in range(1, 14)))]
files += [REPO / "tests" / name for name in ("test_native_rna_structure_results_integration.py", "test_native_rna_structure_acquisition.py")]
files += [REPO / "verification/tool_graders_rna_structure_results_2026-10-26_358/fixture_helpers.py"]
files = list(dict.fromkeys(files))
pins = []
for source in files:
    content = source.read_bytes()
    relative = source.relative_to(REPO)
    snapshot = directory / "source_snapshot" / relative
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(content)
    pins.append({"path": str(relative), "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)})
(directory / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")
temporary, cache = directory / "temporary", directory / "cache"
temporary.mkdir()
cache.mkdir()
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(REPO / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
    "--basetemp", str(temporary / "pytest"), *[str(REPO / p) for p in tests]]
environment = {"PYTHONPATH": str(REPO), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
request = {"argv": argv, "cwd": str(directory), "policy": policy.to_dict(), "environment": environment}
(directory / "selected_request.json").write_text(json.dumps(request, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
        stderr_path=directory / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error)}
finally:
    after = [{"path": row["path"], "sha256": hashlib.sha256((REPO / row["path"]).read_bytes()).hexdigest(),
        "size_bytes": (REPO / row["path"]).stat().st_size} for row in pins]
    (directory / "source_pins_after.json").write_text(json.dumps(after, indent=2) + "\n")
    receipt["source_pins_unchanged"] = after == pins
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": receipt["returncode"],
    "source_pins_unchanged": receipt["source_pins_unchanged"]}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
