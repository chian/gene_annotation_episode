"""Retain a readonly executed-source snapshot and one local_jobs test attempt."""
from pathlib import Path
import hashlib
import json
import sys


PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
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
    "tests/test_native_genomic_overlap_local.py", "tests/test_native_genomic_overlap_driver.py", "pyproject.toml",
))
sources.extend(path for packet in ("tool_graders_genomic_overlap_contract_2026-10-27_418", "tool_graders_genomic_overlap_native_contract_2026-10-27_425", "tool_graders_genomic_overlap_implementation_2026-10-27_422")
    for path in (REPO / "verification" / packet).glob("*") if path.is_file())
sources.extend((Path(__file__), PACKET / "verify_worker.py", PACKET / "fixture_helpers.py"))
entries = [(source, source.relative_to(REPO)) for source in sorted(set(sources))]
pins = []
for source, relative in entries:
    if source.name.casefold() in {'agents.md', 'agent.md', 'goal.md'}:
        continue
    raw = source.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    destination = snapshot / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    destination.chmod(0o444)
    pins.append({"path": str(relative), "source_path": str(source),
        "sha256": checksum, "byte_length": len(raw)})
for path in sorted((p for p in snapshot.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts), reverse=True):
    path.chmod(0o555)
snapshot.chmod(0o555)
(attempt / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")

sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
worker = snapshot / (PACKET / "verify_worker.py").relative_to(REPO)
argv = [str(REPO / ".venv/bin/python"), "-B", str(worker), str(attempt), str(snapshot)]
binary_paths = [REPO / ".venv/bin/python", REPO / "software/bedtools/ubuntu-2.31.1+dfsg-2/installation/usr/bin/bedtools"]
binary_pins = [{"path": str(path), "resolved": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in binary_paths]
(attempt / "binary_pins_before.json").write_text(json.dumps(binary_pins, indent=2) + "\n")
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1",
    "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
    "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
request = {"argv": argv, "cwd": str(attempt), "policy": policy.to_dict(),
    "environment": environment, "executed_source_root": str(snapshot), "source_snapshot_readonly": True}
(attempt / "selected_request.json").write_text(json.dumps(request, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=attempt, policy=policy,
        stdout_path=attempt / "stdout.txt", stderr_path=attempt / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error)}
finally:
    binary_after = [{"path": str(path), "resolved": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in binary_paths]
    (attempt / "binary_pins_after.json").write_text(json.dumps(binary_after, indent=2) + "\n")
    executed_after, checkout_after = [], []
    for pin in pins:
        for path, output in ((snapshot / pin["path"], executed_after),
                (Path(pin["source_path"]), checkout_after)):
            if path.is_file():
                raw = path.read_bytes()
                output.append({**pin, "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)})
            else:
                output.append({"path": pin["path"], "missing": True})
    (attempt / "source_pins_after.json").write_text(json.dumps(executed_after, indent=2) + "\n")
    (attempt / "checkout_source_pins_after.json").write_text(json.dumps(checkout_after, indent=2) + "\n")
    receipt.update(executed_source_pins_unchanged=executed_after == pins, binary_pins_unchanged=binary_after == binary_pins,
        checkout_source_drift=[{"before": a, "after": b} for a, b in zip(pins, checkout_after) if a != b],
        executed_source_root=str(snapshot))
    (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"attempt": str(attempt), "returncode": receipt["returncode"],
    "executed_source_pins_unchanged": receipt["executed_source_pins_unchanged"],
    "checkout_source_drift_count": len(receipt["checkout_source_drift"])}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
