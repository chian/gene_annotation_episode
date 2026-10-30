"""Run owned worker/publication verification under the existing local limits."""
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
temporary, cache = directory / "temporary", directory / "cache"
temporary.mkdir()
cache.mkdir()
tests = sys.argv[2:] or ["tests/test_rna_structure_comparison_worker.py", "tests/test_rna_structure_comparison_publication.py"]
files = [REPO / "gene_annotation_episode" / name for name in (
    "rna_structure_comparison_worker.py", "rna_structure_comparison_publication.py",
    "rna_structure_comparison_contracts.py", "rna_structure_comparison_inputs.py", "rna_structure_comparison_calculations.py",
    "rna_structure_scan_calculations.py", "rna_structure_comparison_views.py", "rna_structure_contracts.py",
    "rna_structure_native.py", "rna_structure_topology.py", "execution_contracts.py", "local_jobs.py", "native_lifecycle.py",
    "_local_job_worker.py", "practical_execution_state.py", "materials.py", "rna_structure_result_views.py")]
files += [REPO / path.split("::")[0] for path in tests]
files += [PACKET / "fixture_helpers.py", PACKET / "run_bounded.py"]
files += [REPO / "verification" / name / "fixture_helpers.py" for name in (
    "tool_graders_rna_comparison_inputs_2026-10-26_366", "tool_graders_rna_comparison_calculations_2026-10-26_367")]
files += list((REPO / "verification/tool_graders_rna_comparison_contract_2026-10-26_362").glob("CONTRACT_ADDENDUM_*.md"))
files += [REPO / "verification/tool_graders_rna_comparison_contract_2026-10-26_362/PLAN_001.md"]
files += list((REPO / "tests/fixtures/rna_structure_comparison_worker_369").rglob("*.md"))
files += [REPO / "tests/fixtures/rna_structure_comparison_calculations_367/retained357" / (name + ".json")
    for name in ("prediction", "evaluation")]
files += [Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")]
pins = []
for source in dict.fromkeys(files):
    content = source.read_bytes()
    relative = source.relative_to(REPO) if source.is_relative_to(REPO) else Path("immutable_authority") / source.name
    snapshot = directory / "source_snapshot" / relative
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(content)
    pins.append({"path": str(source), "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)})
(directory / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(REPO / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp", str(temporary / "pytest"), *[str(REPO / path) for path in tests]]
environment = {"PYTHONPATH": str(REPO), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
(directory / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(directory),
    "policy": policy.to_dict(), "environment": environment}, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
        stderr_path=directory / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "detail": str(error)}
finally:
    after = [{"path": row["path"], "sha256": hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest(),
        "size_bytes": Path(row["path"]).stat().st_size} for row in pins]
    (directory / "source_pins_after.json").write_text(json.dumps(after, indent=2) + "\n")
    receipt["source_pins_unchanged"] = after == pins
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": receipt["returncode"], "source_pins_unchanged": receipt["source_pins_unchanged"]}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
