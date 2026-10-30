"""Run selected return-boundary checks through the existing bounded job runner."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
ATTEMPT = PACKET / sys.argv[1]
ATTEMPT.mkdir(exist_ok=False)
SNAPSHOT = ATTEMPT / "source_snapshot"
names = sys.argv[2:] or ["test_chromatin_interaction_return_views.py"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


paths = []
for package in ("gene_annotation_episode", "method_loop"):
    paths += [p for p in (ROOT / package).rglob("*") if p.is_file()
              and "__pycache__" not in p.parts and p.suffix != ".pyc"]
paths += [ROOT / name for name in (
    "pyproject.toml", 
    "tests/test_chromatin_interaction_return_views.py",
    "tests/test_communication.py",
    "verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json")]
paths.append(Path(__file__))
paths.extend(ROOT / "tests" / name for name in names)
pins = []
for path in sorted(set(paths)):
    relative = path.relative_to(ROOT)
    raw = path.read_bytes()
    destination = SNAPSHOT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    destination.chmod(0o444)
    pins.append({"path": str(relative), "source_path": str(path),
                 "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)})
for path in sorted((p for p in SNAPSHOT.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
    path.chmod(0o555)
SNAPSHOT.chmod(0o555)
for name in ("temporary", "cache"):
    (ATTEMPT / name).mkdir()
save(ATTEMPT / "source_pins_before.json", pins)
interpreter = ROOT / ".venv/bin/python"
binary = {"path": str(interpreter), "resolved_path": str(interpreter.resolve()), "sha256": sha(interpreter)}
save(ATTEMPT / "binary_pin_before.json", binary)
sys.path.insert(0, str(SNAPSHOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(interpreter), "-B", "-m", "pytest", "-q", "-c", str(SNAPSHOT / "pyproject.toml"),
    *[str(SNAPSHOT / "tests" / name) for name in names],
    "--basetemp", str(ATTEMPT / "temporary/pytest"), "--junitxml", str(ATTEMPT / "junit.xml"),
    "-o", "cache_dir=" + str(ATTEMPT / "cache")]
environment = {"PYTHONPATH": str(SNAPSHOT), "PYTHONDONTWRITEBYTECODE": "1",
               "TMPDIR": str(ATTEMPT / "temporary"), "XDG_CACHE_HOME": str(ATTEMPT / "cache")}
save(ATTEMPT / "selected_request.json", {"argv": argv, "environment": environment,
    "cwd": str(ATTEMPT), "policy": policy.to_dict()})
try:
    outcome = run_local_job(argv, cwd=ATTEMPT, policy=policy,
        stdout_path=ATTEMPT / "stdout.txt", stderr_path=ATTEMPT / "stderr.txt", env=environment)
    receipt = {"returncode": outcome.returncode, "metadata": outcome.metadata}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error)}
finally:
    executed, checkout = [], []
    for before in pins:
        for path, output in ((SNAPSHOT / before["path"], executed), (Path(before["source_path"]), checkout)):
            output.append({**before, "sha256": sha(path), "size_bytes": path.stat().st_size}
                          if path.is_file() else {"path": before["path"], "missing": True})
    after_binary = {"path": str(interpreter), "resolved_path": str(interpreter.resolve()), "sha256": sha(interpreter)}
    save(ATTEMPT / "source_pins_after.json", executed)
    save(ATTEMPT / "checkout_source_pins_after.json", checkout)
    save(ATTEMPT / "binary_pin_after.json", after_binary)
    receipt.update(executed_source_pins_unchanged=executed == pins,
        binary_pins_unchanged=after_binary == binary,
        checkout_drift=[{"before": a, "after": b} for a, b in zip(pins, checkout) if a != b])
    save(ATTEMPT / "receipt.json", receipt)
print(json.dumps(receipt))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
