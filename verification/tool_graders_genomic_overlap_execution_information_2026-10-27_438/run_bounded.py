"""Retain each readonly-source information-port check through local_jobs."""
from pathlib import Path
import hashlib
import json
import sys


PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
attempt = PACKET / sys.argv[1]
attempt.mkdir(exist_ok=False)
snapshot = attempt / "source_snapshot"
temporary, cache = attempt / "temporary", attempt / "cache"
temporary.mkdir()
cache.mkdir()
sources = []
for package in ("gene_annotation_episode", "method_loop"):
    sources.extend(p for p in (ROOT / package).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
sources.extend(ROOT / name for name in (
    "tests/test_genomic_overlap_execution_information.py", "pyproject.toml",
    "verification/tool_graders_genomic_overlap_execution_contracts_2026-10-27_426/fixtures.py",
    "verification/tool_graders_genomic_overlap_native_contract_2026-10-27_425/WORKED_EXAMPLE.json",
))
sources.append(Path(__file__))
pins = []
for source in sorted(set(sources)):
    if source.name.casefold() in {'agents.md', 'agent.md', 'goal.md'}:
        continue
    relative = source.relative_to(ROOT)
    raw = source.read_bytes()
    destination = snapshot / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    destination.chmod(0o444)
    pins.append({"path": str(relative), "source_path": str(source),
        "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)})
for directory in sorted((p for p in snapshot.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
    directory.chmod(0o555)
snapshot.chmod(0o555)
(attempt / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")
interpreter = ROOT / ".venv/bin/python"
binary_pin = {"path": str(interpreter), "resolved": str(interpreter.resolve()),
    "sha256": hashlib.sha256(interpreter.read_bytes()).hexdigest()}
(attempt / "binary_pin_before.json").write_text(json.dumps(binary_pin, indent=2) + "\n")
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(interpreter), "-B", "-m", "pytest", "-q", "-c", str(snapshot / "pyproject.toml"),
    str(snapshot / "tests/test_genomic_overlap_execution_information.py"),
    "--basetemp", str(temporary / "pytest"), "--junitxml", str(attempt / "pytest.xml"),
    "-o", "cache_dir=" + str(cache), *sys.argv[2:]]
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1",
    "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
    "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
(attempt / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(attempt),
    "policy": policy.to_dict(), "environment": environment, "source_snapshot_readonly": True,
    "executed_source_root": str(snapshot)}, indent=2) + "\n")
try:
    outcome = run_local_job(argv, cwd=attempt, policy=policy, stdout_path=attempt / "stdout.txt",
        stderr_path=attempt / "stderr.txt", env=environment)
    receipt = {"returncode": outcome.returncode, "metadata": outcome.metadata,
        "stdout_path": str(outcome.stdout_path), "stderr_path": str(outcome.stderr_path)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error)}
finally:
    executed, checkout = [], []
    for pin in pins:
        for path, rows in ((snapshot / pin["path"], executed), (Path(pin["source_path"]), checkout)):
            if path.is_file():
                raw = path.read_bytes()
                rows.append({**pin, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)})
            else:
                rows.append({"path": pin["path"], "missing": True})
    for name, rows in (("source_pins_after", executed), ("checkout_source_pins_after", checkout)):
        (attempt / (name + ".json")).write_text(json.dumps(rows, indent=2) + "\n")
    binary_after = {"path": str(interpreter), "resolved": str(interpreter.resolve()),
        "sha256": hashlib.sha256(interpreter.read_bytes()).hexdigest()}
    (attempt / "binary_pin_after.json").write_text(json.dumps(binary_after, indent=2) + "\n")
    receipt.update(executed_source_pins_unchanged=executed == pins,
        binary_pins_unchanged=binary_pin == binary_after,
        checkout_source_drift=[{"before": a, "after": b} for a, b in zip(pins, checkout) if a != b],
        executed_source_root=str(snapshot))
    (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"attempt": str(attempt), "returncode": receipt["returncode"],
    "executed_source_pins_unchanged": receipt["executed_source_pins_unchanged"],
    "binary_pins_unchanged": receipt["binary_pins_unchanged"],
    "checkout_source_drift_count": len(receipt["checkout_source_drift"])}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
