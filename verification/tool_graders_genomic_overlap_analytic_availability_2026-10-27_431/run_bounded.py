"""Pin all fixture dependencies and run the focused suites through local_jobs."""
from pathlib import Path
import hashlib
import json
import sys
import traceback


PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
FROZEN = {
    "verification/tool_graders_genomic_overlap_result_contract_2026-10-27_428/DATA_CONTRACT.json":
        "cdfb97a319668d1a3774fe8715d040ec00348f5e1a8107058382b578a4f1ee76",
}
attempt = PACKET / sys.argv[1]
attempt.mkdir(exist_ok=False)
snapshot = attempt / "source_snapshot"
temporary, cache = attempt / "temporary", attempt / "cache"
temporary.mkdir()
cache.mkdir()
sources = []
for package in ("gene_annotation_episode", "method_loop"):
    sources.extend(path for path in (REPO / package).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
sources.extend(REPO / path for path in (
    "tests/test_genomic_overlap_inputs.py", "tests/test_genomic_overlap_calculations.py",
    "tests/test_genomic_overlap_result_views.py", "tests/test_genomic_overlap_analytic_capture_loss.py",
    "pyproject.toml",
    *FROZEN,
))
for relative in (
        "verification/tool_graders_genomic_overlap_contract_2026-10-27_418",
        "verification/tool_graders_genomic_overlap_native_2026-10-27_421/run002/work"):
    sources.extend(path for path in (REPO / relative).rglob("*") if path.is_file())
sources.extend((Path(__file__), PACKET / "verify_worker.py"))
entries = [(source, source.relative_to(REPO)) for source in sorted(set(sources))]
pins = []
for source, relative in entries:
    if source.name.casefold() in {'agents.md', 'agent.md', 'goal.md'}:
        continue
    raw = source.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    expected = FROZEN.get(str(relative))
    if expected is not None and checksum != expected:
        raise ValueError("frozen_authority_digest_mismatch:" + str(relative))
    destination = snapshot / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    destination.chmod(0o444)
    pins.append({"path": str(relative), "source_path": str(source),
                 "sha256": checksum, "byte_length": len(raw)})
for path in sorted((path for path in snapshot.rglob("*") if path.is_dir()),
                   key=lambda path: len(path.parts), reverse=True):
    path.chmod(0o555)
snapshot.chmod(0o555)
(attempt / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")

sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
interpreter = REPO / ".venv/bin/python"
interpreter_pin = {"path": str(interpreter), "resolved_path": str(interpreter.resolve()),
    "sha256": hashlib.sha256(interpreter.read_bytes()).hexdigest()}
worker = snapshot / (PACKET / "verify_worker.py").relative_to(REPO)
argv = [str(interpreter), "-B", str(worker), str(attempt), str(snapshot)]
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1",
    "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
    "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
request = {"argv": argv, "cwd": str(attempt), "policy": policy.to_dict(), "environment": environment,
    "executed_source_root": str(snapshot), "source_snapshot_readonly": True,
    "interpreter": interpreter_pin,
    "scope": "original 96 pure + 41 projection cases and targeted analytic capture-loss cases"}
(attempt / "selected_request.json").write_text(json.dumps(request, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=attempt, policy=policy,
        stdout_path=attempt / "stdout.txt", stderr_path=attempt / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error),
               "traceback": traceback.format_exc()}
finally:
    executed_after, checkout_after = [], []
    for pin in pins:
        for path, output in ((snapshot / pin["path"], executed_after), (Path(pin["source_path"]), checkout_after)):
            if path.is_file():
                raw = path.read_bytes()
                output.append({**pin, "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)})
            else:
                output.append({"path": pin["path"], "missing": True})
    (attempt / "source_pins_after.json").write_text(json.dumps(executed_after, indent=2) + "\n")
    (attempt / "checkout_source_pins_after.json").write_text(json.dumps(checkout_after, indent=2) + "\n")
    receipt.update(executed_source_pins_unchanged=executed_after == pins,
        checkout_source_drift=[{"before": a, "after": b} for a, b in zip(pins, checkout_after) if a != b],
        executed_source_root=str(snapshot), interpreter=interpreter_pin,
        interpreter_pin_unchanged=hashlib.sha256(interpreter.read_bytes()).hexdigest() == interpreter_pin["sha256"])
    (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"attempt": str(attempt), "returncode": receipt["returncode"],
    "executed_source_pins_unchanged": receipt["executed_source_pins_unchanged"],
    "checkout_source_drift_count": len(receipt["checkout_source_drift"]),
    "interpreter_pin_unchanged": receipt["interpreter_pin_unchanged"]}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
