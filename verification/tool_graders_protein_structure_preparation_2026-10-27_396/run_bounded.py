"""Freeze source bytes, then run all checks through existing local_jobs."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
run = PACKET / sys.argv[1]
run.mkdir(exist_ok=False)
snapshot = run / "source_snapshot"
temporary, cache = run / "temporary", run / "cache"
temporary.mkdir()
cache.mkdir()
tests = sys.argv[2:] or ["tests/test_native_protein_structure_preparation.py"]
files = []
for package in ("gene_annotation_episode", "method_loop"):
    files += [p for p in (REPO / package).rglob("*") if p.is_file() and "__pycache__" not in p.parts
              and p.suffix != ".pyc"]
files += [REPO / test.split("::")[0] for test in tests]
files += [REPO / "pyproject.toml", Path(__file__)]
for name in ("tool_graders_protein_structure_result_worker_2026-10-27_393",
             "tool_graders_protein_structure_preparation_2026-10-27_396"):
    source = REPO / "verification" / name
    files += list(source.glob("*.json"))
    files += [p for p in (source / "fixtures").rglob("*") if p.is_file()]
files.extend(p for p in (REPO / 'verification/tool_graders_protein_structure_result_worker_2026-10-27_393').glob('*.md')
    if p.name.casefold() not in {'agents.md', 'agent.md', 'goal.md'})
files.extend(p for p in (REPO / 'verification/tool_graders_protein_structure_preparation_2026-10-27_396').glob('*.md')
    if p.name.casefold() not in {'agents.md', 'agent.md', 'goal.md'})
files.extend(p for p in (REPO / 'verification/tool_graders_protein_structure_shared_contract_2026-10-27_380').glob('*.md')
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
for path in sorted([p for p in snapshot.rglob("*") if p.is_dir()], key=lambda p: len(p.parts), reverse=True):
    path.chmod(0o555)
snapshot.chmod(0o555)
(run / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
entry = run / "pytest_entry.py"
entry.write_text(
    "import json, pathlib, runpy, sys\n"
    "root = pathlib.Path(__file__).resolve().parent\n"
    "try:\n"
    "    runpy.run_module('pytest', run_name='__main__')\n"
    "finally:\n"
    "    imports = {name: str(getattr(module, '__file__', '')) for name, module in sys.modules.copy().items() "
    "if name.startswith(('gene_annotation_episode', 'method_loop'))}\n"
    "    (root / 'executed_imports.json').write_text(json.dumps(imports, indent=2))\n"
    "    assert all(pathlib.Path(path).is_relative_to(root / 'source_snapshot') for path in imports.values() if path)\n")
entry.chmod(0o444)
argv = [str(REPO / ".venv/bin/python"), "-B", str(entry), "-q", "-p", "no:cacheprovider",
        "--basetemp", str(temporary / "pytest"), "--rootdir", str(snapshot),
        *[str(snapshot / test) for test in tests]]
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache),
    "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
(run / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(run), "policy": policy.to_dict(),
    "environment": environment, "python_sha256": hashlib.sha256((REPO / ".venv/bin/python").read_bytes()).hexdigest(),
    "pytest_entry_sha256": hashlib.sha256(entry.read_bytes()).hexdigest()}, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=run, policy=policy, stdout_path=run / "stdout.txt", stderr_path=run / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error)}
finally:
    def after(root):
        rows = []
        for row in pins:
            path = root / row["path"]
            raw = path.read_bytes() if path.is_file() else None
            rows.append({"path": row["path"], "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)}
                        if raw is not None else {"path": row["path"], "missing": True})
        return rows
    executed, checkout = after(snapshot), after(REPO)
    (run / "source_pins_after.json").write_text(json.dumps(executed, indent=2) + "\n")
    (run / "checkout_source_pins_after.json").write_text(json.dumps(checkout, indent=2) + "\n")
    receipt["executed_source_pins_unchanged"] = executed == pins
    receipt["checkout_source_drift"] = [{"before": a, "after": b} for a, b in zip(pins, checkout) if a != b]
    receipt["local_jobs_module"] = sys.modules["gene_annotation_episode.local_jobs"].__file__
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(run), "returncode": receipt["returncode"],
    "executed_source_pins_unchanged": receipt["executed_source_pins_unchanged"],
    "checkout_source_drift_count": len(receipt["checkout_source_drift"])}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
