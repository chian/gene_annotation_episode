"""Run selected registration checks from immutable retained project sources."""
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
tests = sys.argv[2:] or [
    "tests/test_protein_structure_resource_registration.py",
    "tests/test_execution_episodes_family.py::test_one_owner_and_data_descriptor_reconstruct_all_operands",
    "tests/test_execution_episodes_family.py::test_dynamic_resources_keep_several_hpcs_and_explicit_selected_request",
    "tests/test_execution_episodes_family.py::test_api_request_keeps_typed_service_job_and_its_explicit_resource",
    "tests/test_execution_tool_contract_declarations.py",
    "tests/test_execution_wiring.py::test_all_three_resources_reconstruct_before_model_entry_without_work",
    "tests/test_protein_structure_source_boundaries.py",
]
# Retain helpers too, but invoke only the explicit selected tests above.
files = [path for package in ("gene_annotation_episode", "method_loop", "tests")
    for path in (REPO / package).rglob("*") if path.is_file()
    and "__pycache__" not in path.parts and path.suffix != ".pyc"]
files += [REPO / "pyproject.toml", Path(__file__)]
for packet, names in (
    ("tool_graders_protein_structure_execution_2026-10-27_390", ["fixture_helpers.py"]),
    ("tool_graders_protein_structure_inputs_2026-10-27_386", ["fixture_helpers.py"]),
):
    files.extend(REPO / "verification" / packet / name for name in names)
files.extend((REPO / "verification/tool_graders_protein_structure_inputs_2026-10-27_386/fixtures").glob("*"))
files.extend(REPO / "verification/tool_graders_native_hmmer_producer_2026-10-24/runs" / name / "plan.json"
    for name in ("nhmmer_sequence_ordinary", "nhmmer_profile_ordinary", "hmmscan_search_ordinary"))
files.extend(p for p in (REPO / 'verification/tool_graders_protein_structure_shared_contract_2026-10-27_380').glob('*.md')
    if p.name.casefold() not in {'agents.md', 'agent.md', 'goal.md'})
files.extend(p for p in (REPO / 'verification/tool_graders_protein_structure_result_host_contract_2026-10-27_403').glob('*.md')
    if p.name.casefold() not in {'agents.md', 'agent.md', 'goal.md'})
pins = []
for source in sorted(set(files)):
    if source.name.casefold() in {'agents.md', 'agent.md', 'goal.md'}:
        continue
    if not source.is_file():
        raise FileNotFoundError(source)
    raw = source.read_bytes()
    relative = source.relative_to(REPO)
    destination = snapshot / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    destination.chmod(0o444)
    pins.append({"path": str(relative), "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)})
for path in sorted([path for path in snapshot.rglob("*") if path.is_dir()],
        key=lambda path: len(path.parts), reverse=True):
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
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1",
    "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
    "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
request = {"argv": argv, "cwd": str(directory), "policy": policy.to_dict(),
    "environment": environment, "executed_source_root": str(snapshot),
    "source_snapshot_readonly": True, "selected_tests": tests}
(directory / "selected_request.json").write_text(json.dumps(request, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=directory, policy=policy,
        stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt", env=environment)
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

    executed_after, checkout_after = after(snapshot), after(REPO)
    (directory / "source_pins_after.json").write_text(json.dumps(executed_after, indent=2) + "\n")
    (directory / "checkout_source_pins_after.json").write_text(json.dumps(checkout_after, indent=2) + "\n")
    receipt["executed_source_pins_unchanged"] = executed_after == pins
    receipt["checkout_source_drift"] = [{"before": a, "after": b}
        for a, b in zip(pins, checkout_after) if a != b]
    receipt["executed_source_root"] = str(snapshot)
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": receipt["returncode"],
    "executed_source_pins_unchanged": receipt["executed_source_pins_unchanged"],
    "checkout_source_drift_count": len(receipt["checkout_source_drift"])}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
