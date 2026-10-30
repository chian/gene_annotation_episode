"""Record each selected bounded verification request and its actual receipt."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
sys.path.insert(0, str(REPO))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = PACKET / sys.argv[1]
directory.mkdir(exist_ok=False)
tests = sys.argv[2:] or ["tests/test_rna_comparison_operand_authority.py", "tests/test_rna_comparison_results_adapter.py",
    "tests/test_rna_comparison_authority_transactions.py"]
files = [REPO / "gene_annotation_episode" / name for name in (
    "rna_structure_comparison_operands.py", "rna_structure_comparison_results.py", "rna_structure_comparison_returns.py",
    "native_rna_structure_returns.py", "rna_structure_comparison_worker.py", "rna_structure_comparison_publication.py",
    "rna_structure_comparison_contracts.py", "rna_structure_comparison_inputs.py", "rna_structure_comparison_calculations.py",
    "rna_structure_scan_calculations.py", "rna_structure_comparison_views.py", "native_rna_structure_results.py",
    "native_rna_structure_result_publication.py", "episode_receipts.py", "episode_return_records.py", "communication.py",
    "local_jobs.py", "native_lifecycle.py", "_local_job_worker.py")]
files += [REPO / p.split("::")[0] for p in tests]
files += [REPO / "tests/fixtures/rna_comparison_results_371/helpers.py", Path(__file__).resolve()]
files += list((REPO / "verification/tool_graders_rna_comparison_contract_2026-10-26_362").glob("*.md"))
files += [REPO / "verification/tool_graders_rna_structure_results_2026-10-26_358/fixture_helpers.py"]
files += [REPO / "verification" / name / "fixture_helpers.py" for name in (
    "tool_graders_rna_structure_core_2026-10-26_354", "tool_graders_rna_comparison_inputs_2026-10-26_366",
    "tool_graders_rna_comparison_calculations_2026-10-26_367")]
# Preserve the actual imported host and method-loop sources as well as the
# focused scientific modules; a fixture's selected-action methods are real.
files += sorted((REPO / "gene_annotation_episode").glob("*.py"))
files += sorted((REPO / "method_loop").glob("*.py"))
files = list(dict.fromkeys(files))
pins = []
for path in files:
    raw = path.read_bytes()
    relative = path.relative_to(REPO)
    target = directory / "source_snapshot" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    pins.append({"path": str(relative), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)})
(directory / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")
temporary, cache = directory / "temporary", directory / "cache"
temporary.mkdir()
cache.mkdir()
policy = LocalJobPolicy(21474836480, 4294967296, wall_seconds=None)
argv = [str(REPO / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp", str(temporary / "pytest"), *[str(REPO / p) for p in tests]]
environment = {"PYTHONPATH": str(REPO), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache),
    "PIP_CACHE_DIR": str(cache / "pip"), "RNA_COMPARISON_E_EXAMPLES": str(directory / "examples")}
request = {"argv": argv, "cwd": str(directory), "policy": policy.to_dict(), "environment": environment}
(directory / "selected_request.json").write_text(json.dumps(request, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "detail": str(error)}
finally:
    after = [{"path": row["path"], "sha256": hashlib.sha256((REPO / row["path"]).read_bytes()).hexdigest(),
        "size_bytes": (REPO / row["path"]).stat().st_size} for row in pins]
    (directory / "source_pins_after.json").write_text(json.dumps(after, indent=2) + "\n")
    receipt["source_pins_unchanged"] = after == pins
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": receipt["returncode"], "source_pins_unchanged": receipt["source_pins_unchanged"]}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
