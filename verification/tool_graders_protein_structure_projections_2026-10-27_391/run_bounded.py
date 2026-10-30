"""Run only selected391 tests in a frozen snapshot through bounded local_jobs."""
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
temporary, cache, snapshot = directory / "temporary", directory / "cache", directory / "source_snapshot"
temporary.mkdir()
cache.mkdir()
tests = sys.argv[2:] or ["tests/test_protein_structure_result_views.py"]
names = ("__init__", "protein_structure_contracts", "protein_structure_formats", "protein_structure_sequences",
    "protein_structure_correspondence", "protein_structure_metadata", "protein_structure_sheet",
    "protein_structure_calculations", "protein_structure_result_views", "sequence_ops", "biopython_pairwise_grader",
    "local_jobs", "native_lifecycle", "_local_job_worker", "execution_contracts", "domain")
files = [REPO / "gene_annotation_episode" / (name + ".py") for name in names]
files += [REPO / test.split("::")[0] for test in tests]
files += list(PACKET.glob("*.py"))
for packet in ("tool_graders_protein_structure_inputs_2026-10-27_386", "tool_graders_protein_structure_calculations_2026-10-27_389"):
    path = REPO / "verification" / packet
    files.append(path / "fixture_helpers.py")
    files.extend((path / "fixtures").glob("*"))
files += list((REPO / "verification/tool_graders_protein_structure_shared_contract_2026-10-27_380").glob("*"))
files += [REPO / "pyproject.toml"]
pins = []
for source in dict.fromkeys(files):
    if not source.is_file():
        continue
    data = source.read_bytes()
    relative = source.relative_to(REPO)
    target = snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    pins.append({"path": str(relative), "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)})
(directory / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(REPO / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp", str(temporary / "pytest"), *[str(snapshot / test) for test in tests]]
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip"),
    "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
(directory / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(directory), "policy": policy.to_dict(), "environment": environment}, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata, "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error)}
finally:
    after = [{"path": row["path"], "sha256": hashlib.sha256((REPO / row["path"]).read_bytes()).hexdigest(), "size_bytes": (REPO / row["path"]).stat().st_size} for row in pins]
    executed = [{"path": row["path"], "sha256": hashlib.sha256((snapshot / row["path"]).read_bytes()).hexdigest(), "size_bytes": (snapshot / row["path"]).stat().st_size} for row in pins]
    (directory / "source_pins_after.json").write_text(json.dumps(after, indent=2) + "\n")
    (directory / "executed_source_pins_after.json").write_text(json.dumps(executed, indent=2) + "\n")
    receipt["live_source_pins_unchanged"] = after == pins
    receipt["executed_source_pins_unchanged"] = executed == pins
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": receipt["returncode"],
    "live_source_pins_unchanged": receipt["live_source_pins_unchanged"], "executed_source_pins_unchanged": receipt["executed_source_pins_unchanged"]}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
