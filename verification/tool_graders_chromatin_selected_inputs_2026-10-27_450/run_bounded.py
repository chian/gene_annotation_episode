"""Pin this authority suite and retain its original bounded native handle."""
from pathlib import Path
import hashlib
import json
import sys


PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
ATTEMPT = PACKET / sys.argv[1]
ATTEMPT.mkdir(exist_ok=False)
SNAPSHOT = ATTEMPT / "source_snapshot"
TESTS = ["test_chromatin_interaction_operands.py"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


paths = []
for package in ("gene_annotation_episode", "method_loop"):
    paths.extend(path for path in (ROOT / package).rglob("*") if path.is_file()
        and "__pycache__" not in path.parts and path.suffix != ".pyc")
paths.extend(ROOT / name for name in ("pyproject.toml",))
paths.extend(ROOT / "tests" / name for name in TESTS)
paths.append(Path(__file__))
pins = []
for path in sorted(set(paths)):
    relative, raw = path.relative_to(ROOT), path.read_bytes()
    destination = SNAPSHOT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    destination.chmod(0o444)
    pins.append({"path": str(relative), "source_path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)})
for path in sorted((path for path in SNAPSHOT.rglob("*") if path.is_dir()), key=lambda path: len(path.parts), reverse=True):
    path.chmod(0o555)
SNAPSHOT.chmod(0o555)
for name in ("temporary", "cache"):
    (ATTEMPT / name).mkdir()
save(ATTEMPT / "source_pins_before.json", pins)
interpreter = ROOT / ".venv/bin/python"
binary = {"path": str(interpreter), "resolved_path": str(interpreter.resolve()), "sha256": sha(interpreter)}
save(ATTEMPT / "binary_pin_before.json", binary)
sys.path.insert(0, str(SNAPSHOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import prepare_job, start_prepared, wait_job, status

policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(interpreter), "-B", "-m", "pytest", "-q", "-c", str(SNAPSHOT / "pyproject.toml"),
    *[str(SNAPSHOT / "tests" / name) for name in TESTS],
    "--basetemp", str(ATTEMPT / "temporary/pytest"), "--junitxml", str(ATTEMPT / "junit.xml"),
    "-o", "cache_dir=" + str(ATTEMPT / "cache")]
environment = {"PYTHONPATH": str(SNAPSHOT), "PYTHONDONTWRITEBYTECODE": "1",
    "TMPDIR": str(ATTEMPT / "temporary"), "XDG_CACHE_HOME": str(ATTEMPT / "cache")}
save(ATTEMPT / "selected_request.json", {"argv": argv, "environment": environment,
    "cwd": str(ATTEMPT), "policy": policy.to_dict()})
handle = None
try:
    handle = prepare_job(argv, cwd=ATTEMPT, policy=policy, handle_path=ATTEMPT / "native.json",
        stdout_path=ATTEMPT / "stdout.txt", stderr_path=ATTEMPT / "stderr.txt", env=environment)
    start_prepared(handle)
    outcome = wait_job(handle)
    receipt = {"returncode": outcome.returncode, "metadata": outcome.metadata, "final_status": status(handle)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error),
        "final_status": None if handle is None else status(handle)}
finally:
    executed = [{**before, "sha256": sha(SNAPSHOT / before["path"]),
        "size_bytes": (SNAPSHOT / before["path"]).stat().st_size} for before in pins]
    checkout = [{**before, "sha256": sha(Path(before["source_path"])),
        "size_bytes": Path(before["source_path"]).stat().st_size} for before in pins]
    after_binary = {"path": str(interpreter), "resolved_path": str(interpreter.resolve()), "sha256": sha(interpreter)}
    save(ATTEMPT / "source_pins_after.json", executed)
    save(ATTEMPT / "checkout_source_pins_after.json", checkout)
    save(ATTEMPT / "binary_pin_after.json", after_binary)
    receipt.update(executed_source_pins_unchanged=executed == pins, binary_pins_unchanged=after_binary == binary,
        checkout_drift=[{"before": a, "after": b} for a, b in zip(pins, checkout) if a != b])
    save(ATTEMPT / "receipt.json", receipt)
print(json.dumps({key: receipt[key] for key in ("returncode", "executed_source_pins_unchanged", "binary_pins_unchanged")}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
