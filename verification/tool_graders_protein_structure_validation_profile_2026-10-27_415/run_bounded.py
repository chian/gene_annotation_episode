"""Execute one retained-result cProfile experiment under original local limits."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
REFERENCE = REPO / "verification/tool_graders_protein_structure_workflow_2026-10-27_410/check007/temporary/pytest/protein-workflow4100"
directory = PACKET / sys.argv[1]
directory.mkdir(exist_ok=False)
snapshot = directory / "source_snapshot"
temporary, cache = directory / "temporary", directory / "cache"
temporary.mkdir()
cache.mkdir()
files = [path for package in ("gene_annotation_episode", "method_loop")
    for path in (REPO / package).rglob("*") if path.is_file()
    and "__pycache__" not in path.parts and path.suffix != ".pyc"]
files += [REPO / "pyproject.toml", Path(__file__), PACKET / "profile_retained.py"]
files += [REPO / "verification/tool_graders_protein_structure_workflow_2026-10-27_410" / name
    for name in ("run_bounded.py", "diagnose_retained.py")]
files.extend(path for path in (REPO / "research/slotted_process_library/publications/2026-10-24-001").rglob("*") if path.is_file())
files.extend(p for p in (REPO / 'verification/tool_graders_protein_structure_shared_contract_2026-10-27_380').glob('*.md')
    if p.name.casefold() not in {'agents.md', 'agent.md', 'goal.md'})
files.extend(p for p in (REPO / 'verification/tool_graders_protein_structure_result_host_contract_2026-10-27_403').glob('*.md')
    if p.name.casefold() not in {'agents.md', 'agent.md', 'goal.md'})
pins = []
for source in sorted(set(files)):
    if source.name.casefold() in {'agents.md', 'agent.md', 'goal.md'}:
        continue
    raw = source.read_bytes()
    relative = source.relative_to(REPO)
    destination = snapshot / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    destination.chmod(0o444)
    pins.append({"path": str(relative), "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)})
for path in sorted([path for path in snapshot.rglob("*") if path.is_dir()], key=lambda path: len(path.parts), reverse=True):
    path.chmod(0o555)
snapshot.chmod(0o555)
(directory / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")


def input_pins():
    rows = []
    for path in sorted(REFERENCE.rglob("*")):
        if path.is_file():
            raw = path.read_bytes()
            rows.append({"path": str(path.relative_to(REFERENCE)), "sha256": hashlib.sha256(raw).hexdigest(),
                "byte_length": len(raw), "symlink": path.is_symlink()})
    return rows


original_before = input_pins()
(directory / "retained_input_pins_before.json").write_text(json.dumps(original_before, indent=2) + "\n")
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(REPO / ".venv/bin/python"), "-B", str(snapshot / (PACKET / "profile_retained.py").relative_to(REPO)), str(REFERENCE)]
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1",
    "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
    "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
(directory / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(directory),
    "policy": policy.to_dict(), "environment": environment, "executed_source_root": str(snapshot),
    "source_snapshot_readonly": True, "retained_input": str(REFERENCE),
    "workload": "cProfile actual retained410 report diagnostic; original diagnostic logic; no native rerun"}, indent=2) + "\n")
receipt = {"returncode": None}
try:
    result = run_local_job(argv, cwd=directory, policy=policy,
        stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt.update(exception_type=type(error).__name__, exception=str(error))
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
    original_after = input_pins()
    (directory / "source_pins_after.json").write_text(json.dumps(executed_after, indent=2) + "\n")
    (directory / "checkout_source_pins_after.json").write_text(json.dumps(checkout_after, indent=2) + "\n")
    (directory / "retained_input_pins_after.json").write_text(json.dumps(original_after, indent=2) + "\n")
    receipt["executed_source_pins_unchanged"] = executed_after == pins
    receipt["checkout_source_drift"] = [{"before": a, "after": b} for a, b in zip(pins, checkout_after) if a != b]
    receipt["retained_input_pins_unchanged"] = original_before == original_after
    receipt["executed_source_root"] = str(snapshot)
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": receipt["returncode"],
    "executed_source_pins_unchanged": receipt["executed_source_pins_unchanged"],
    "retained_input_pins_unchanged": receipt["retained_input_pins_unchanged"],
    "checkout_source_drift_count": len(receipt["checkout_source_drift"])}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
