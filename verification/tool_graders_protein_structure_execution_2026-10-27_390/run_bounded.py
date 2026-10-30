"""Retain source bytes/pins and run selected C tests inside the fixed boundary."""
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
tests = sys.argv[2:] or ["tests/test_native_protein_structure_" + name + ".py" for name in ("contracts", "execution", "tool_info")]
files = list((REPO / "gene_annotation_episode").glob("native_protein_structure_*.py"))
files += [REPO / "gene_annotation_episode" / ("protein_structure_" + name + ".py")
    for name in ("contracts", "formats", "sequences", "correspondence", "metadata", "sheet", "calculations")]
files += [REPO / "gene_annotation_episode" / (name + ".py") for name in (
    "local_jobs", "native_lifecycle", "_local_job_worker", "execution_contracts", "domain",
    "practical_execution_state", "practical_execution_records", "sequence_ops", "biopython_pairwise_grader")]
files += [REPO / p.split("::")[0] for p in tests]
files += [PACKET / "fixture_helpers.py", Path(__file__)]
inputs_packet = REPO / "verification/tool_graders_protein_structure_inputs_2026-10-27_386"
files += [inputs_packet / "fixture_helpers.py", *list((inputs_packet / "fixtures").glob("*"))]
files += list((REPO / "verification/tool_graders_protein_structure_shared_contract_2026-10-27_380").glob("*"))
pins = []
for source in dict.fromkeys(files):
    if not source.is_file():
        continue
    content = source.read_bytes()
    relative = source.relative_to(REPO)
    snapshot = directory / "source_snapshot" / relative
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(content)
    pins.append({"path": str(relative), "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)})
(directory / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(REPO / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp", str(temporary / "pytest"), *[str(REPO / p) for p in tests]]
environment = {"PYTHONPATH": str(REPO), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
(directory / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(directory), "policy": policy.to_dict(), "environment": environment}, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata, "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error)}
finally:
    after = [{"path": row["path"], "sha256": hashlib.sha256((REPO / row["path"]).read_bytes()).hexdigest(), "size_bytes": (REPO / row["path"]).stat().st_size} for row in pins]
    (directory / "source_pins_after.json").write_text(json.dumps(after, indent=2) + "\n")
    receipt["source_pins_unchanged"] = after == pins
    receipt["source_drift"] = [{"before": old, "after": new} for old, new in zip(pins, after) if old != new]
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": receipt["returncode"], "source_pins_unchanged": receipt["source_pins_unchanged"]}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
