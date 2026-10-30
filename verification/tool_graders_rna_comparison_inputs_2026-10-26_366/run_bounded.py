"""Run selected verification through local_jobs with retained input/output pins."""
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
tests = sys.argv[2:] or ["tests/test_rna_structure_comparison_contracts.py", "tests/test_rna_structure_comparison_inputs.py"]
files = [REPO / "gene_annotation_episode" / name for name in (
    "rna_structure_comparison_contracts.py", "rna_structure_comparison_inputs.py",
    "rna_structure_contracts.py", "rna_structure_topology.py", "rna_structure_native.py",
    "rna_structure_calculations.py", "local_jobs.py", "native_lifecycle.py", "_local_job_worker.py")]
files += [REPO / p.split("::")[0] for p in tests]
files += [PACKET / name for name in ("fixture_helpers.py", "INTERFACES_001.md", "run_bounded.py")]
files += list((REPO / "tests/fixtures/rna_structure_comparison_inputs_366").glob("*"))
files += [REPO / "verification/tool_graders_rna_comparison_contract_2026-10-26_362" / name
    for name in ("PLAN_001.md", "CONTRACT_ADDENDUM_001.md", "CONSUMER_FINDINGS_001.md")]
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
argv = [str(REPO / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
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
