"""Run D2b checks from frozen executed source through the existing local_jobs.

Only metadata copying/hashing runs in this outer launcher. Tests, CLI workers
and every numerical call run in the cgroup managed by local_jobs.
"""
from pathlib import Path
import hashlib
import json
import os
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
run = PACKET / sys.argv[1]
run.mkdir(exist_ok=False)
snapshot = run / "source_snapshot"
temporary, cache = run / "temporary", run / "cache"
temporary.mkdir()
cache.mkdir()
files = []
for package in ("gene_annotation_episode", "method_loop"):
    files += [p for p in (REPO / package).rglob("*") if p.is_file() and "__pycache__" not in p.parts
              and p.suffix in (".py", ".json", ".toml", ".md", ".txt")]
files += [REPO / "pyproject.toml", REPO / "tests/test_protein_structure_result_worker.py"]
files += list(PACKET.glob("*.py")) + list(PACKET.glob("*.json")) + list((PACKET / "fixtures").glob("*.json"))
files.extend(p for p in (REPO / 'verification/tool_graders_protein_structure_shared_contract_2026-10-27_380').glob('*.md')
    if p.name.casefold() not in {'agents.md', 'agent.md', 'goal.md'})
pins = []
for source in dict.fromkeys(files):
    if source.name.casefold() in {'agents.md', 'agent.md', 'goal.md'}:
        continue
    raw = source.read_bytes()
    relative = source.relative_to(REPO)
    target = snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    target.chmod(0o444)
    pins.append({"path": str(relative), "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)})
for directory in sorted([p for p in snapshot.rglob("*") if p.is_dir()], key=lambda p: len(p.parts), reverse=True):
    directory.chmod(0o555)
snapshot.chmod(0o555)
(run / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
tests = sys.argv[2:] or ["tests/test_protein_structure_result_worker.py"]
entry = run / "pytest_entry.py"
entry.write_text(
    "import json, os, pathlib, runpy, sys\n"
    "root = pathlib.Path(__file__).resolve().parent\n"
    "os.environ.update({k: str(root / 'temporary') for k in ('TMPDIR', 'TMP', 'TEMP')})\n"
    "import gene_annotation_episode.protein_structure_result_worker as worker\n"
    "assert pathlib.Path(worker.__file__).is_relative_to(root / 'source_snapshot')\n"
    "(root / 'executed_imports_before.json').write_text(json.dumps({'worker': worker.__file__}, indent=2))\n"
    "try:\n"
    "    runpy.run_module('pytest', run_name='__main__')\n"
    "finally:\n"
    "    imports = {name: str(getattr(module, '__file__', '')) for name, module in sys.modules.copy().items() "
    "if name.startswith(('gene_annotation_episode', 'method_loop'))}\n"
    "    (root / 'executed_imports_after.json').write_text(json.dumps(imports, indent=2))\n"
    "    assert all(pathlib.Path(path).is_relative_to(root / 'source_snapshot') for path in imports.values() if path)\n")
entry.chmod(0o444)
argv = [str(REPO / ".venv/bin/python"), "-B", str(entry), "-q", "-p", "no:cacheprovider",
        "--basetemp", str(temporary / "pytest"), *[str(snapshot / p) for p in tests]]
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache),
    "PIP_CACHE_DIR": str(cache / "pip"), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
(run / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(run),
    "policy": policy.to_dict(), "environment": environment,
    "python_sha256": hashlib.sha256((REPO / ".venv/bin/python").read_bytes()).hexdigest(),
    "pytest_entry_sha256": hashlib.sha256(entry.read_bytes()).hexdigest()}, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=run, policy=policy, stdout_path=run / "stdout.txt",
                           stderr_path=run / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error)}
finally:
    def pin(root, original):
        raw = (root / original["path"]).read_bytes()
        return {"path": original["path"], "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)}
    after = [pin(snapshot, row) for row in pins]
    live = [pin(REPO, row) for row in pins]
    (run / "source_pins_after.json").write_text(json.dumps(after, indent=2) + "\n")
    (run / "live_source_pins_after.json").write_text(json.dumps(live, indent=2) + "\n")
    receipt["executed_snapshot_pins_unchanged"] = pins == after
    receipt["live_source_drift"] = [{"before": before, "after": now} for before, now in zip(pins, live) if before != now]
    owned = {"gene_annotation_episode/protein_structure_result_worker.py", "tests/test_protein_structure_result_worker.py"}
    receipt["owned_live_source_pins_unchanged"] = all(row["before"]["path"] not in owned for row in receipt["live_source_drift"])
    receipt["local_jobs_module"] = sys.modules["gene_annotation_episode.local_jobs"].__file__
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(run), "returncode": receipt["returncode"],
    "executed_snapshot_pins_unchanged": receipt["executed_snapshot_pins_unchanged"],
    "owned_live_source_pins_unchanged": receipt["owned_live_source_pins_unchanged"]}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
