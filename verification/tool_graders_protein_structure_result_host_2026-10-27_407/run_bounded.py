"""Execute each host check from a pinned snapshot under the local job policy."""
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
tests = sys.argv[2:] or ["tests/test_native_protein_structure_results.py"]
files = [REPO / "pyproject.toml", Path(__file__), PACKET / "fixture_helpers.py",
         REPO / "tests/test_protein_structure_record_publication.py"]
for package in ("gene_annotation_episode", "method_loop"):
    files.extend(p for p in (REPO / package).rglob("*") if p.is_file()
                 and "__pycache__" not in p.parts and p.suffix != ".pyc")
files.extend(REPO / test.split("::")[0] for test in tests)
for name in ("tool_graders_protein_structure_inputs_2026-10-27_386",
             "tool_graders_protein_structure_execution_2026-10-27_390",
             "tool_graders_protein_structure_result_receipts_2026-10-27_406"):
    source = REPO / "verification" / name
    files.append(source / "fixture_helpers.py")
    if (source / "fixtures").is_dir():
        files.extend(p for p in (source / "fixtures").rglob("*") if p.is_file())
for name in ("tool_graders_protein_structure_shared_contract_2026-10-27_380",
             "tool_graders_protein_structure_result_worker_2026-10-27_393/fixtures"):
    files.extend(p for p in (REPO / "verification" / name).iterdir() if p.is_file())
capture_packet = REPO / "verification/tool_graders_protein_structure_capture_2026-10-27_392"
examples = capture_packet / "FILLED_CAPTURE_EXAMPLES_001.json"
files.append(examples)
for row in json.loads(examples.read_bytes()):
    example = REPO / row["original_example_path"]
    assert hashlib.sha256(example.read_bytes()).hexdigest() == row["original_example_sha256"]
    files.append(example)
    identities = [row["capture"]["bundle_file"]] + [item["observed"]
        for item in row["capture"]["files"] if item["observed"] is not None]
    for identity in identities:
        path = example.parent / "store/artifacts" / identity["sha256"][:2] / identity["sha256"]
        raw = path.read_bytes()
        assert len(raw) == identity["byte_length"] and hashlib.sha256(raw).hexdigest() == identity["sha256"]
        files.append(path)
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
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(REPO / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp", str(temporary / "pytest"), "--rootdir", str(snapshot),
    *[str(snapshot / test) for test in tests]]
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
(directory / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(directory),
    "policy": policy.to_dict(), "environment": environment, "executed_source_root": str(snapshot),
    "source_snapshot_readonly": True}, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
        stderr_path=directory / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error)}
finally:
    def after(root):
        result = []
        for row in pins:
            path = root / row["path"]
            if path.is_file():
                raw = path.read_bytes()
                result.append({"path": row["path"], "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)})
            else:
                result.append({"path": row["path"], "missing": True})
        return result
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
