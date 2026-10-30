"""Run saved-profile comparison under the same selected local resource limits."""
from pathlib import Path
import hashlib
import json
import sys

packet = Path(__file__).resolve().parent
root = packet.parents[1]
directory = packet / sys.argv[1]
directory.mkdir(exist_ok=False)
snapshot = directory / "source_snapshot"
files = [path for package in ("gene_annotation_episode", "method_loop")
    for path in (root / package).rglob("*") if path.is_file()
    and "__pycache__" not in path.parts and path.suffix != ".pyc"]
files += [Path(__file__), packet / "analyze_profiles.py"]
pins = []
for source in sorted(files):
    raw = source.read_bytes()
    relative = source.relative_to(root)
    target = snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    target.chmod(0o444)
    pins.append({"path": str(relative), "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)})
for path in sorted([path for path in snapshot.rglob("*") if path.is_dir()], key=lambda p: len(p.parts), reverse=True):
    path.chmod(0o555)
snapshot.chmod(0o555)
(directory / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")
temporary, cache = directory / "temporary", directory / "cache"
temporary.mkdir()
cache.mkdir()
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(root / ".venv/bin/python"), "-B", str(snapshot / (packet / "analyze_profiles.py").relative_to(root)),
    str(root), str(packet), str(directory)]
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
(directory / "selected_request.json").write_text(json.dumps({"argv": argv, "policy": policy.to_dict(),
    "cwd": str(directory), "environment": environment, "source_snapshot_readonly": True}, indent=2) + "\n")
receipt = {"returncode": None}
try:
    result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
        stderr_path=directory / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata}
except Exception as error:
    receipt.update(exception_type=type(error).__name__, exception=str(error))
finally:
    after = [{"path": row["path"], "sha256": hashlib.sha256((snapshot / row["path"]).read_bytes()).hexdigest(),
        "byte_length": (snapshot / row["path"]).stat().st_size} for row in pins]
    receipt["executed_source_pins_unchanged"] = after == pins
    (directory / "source_pins_after.json").write_text(json.dumps(after, indent=2) + "\n")
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
