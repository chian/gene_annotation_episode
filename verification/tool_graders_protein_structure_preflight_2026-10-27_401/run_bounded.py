"""Freeze executed code and run preflight verification through existing local_jobs.

Only file copying/hashing runs outside the bounded worker. Preserve every run,
including failures, and keep the executed snapshot independent of live edits.
"""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
baseline = len(sys.argv) > 2 and sys.argv[2] == "--baseline-preflight"
source_root = PACKET / "check005/source_snapshot" if baseline else REPO
preflight_files = {"gene_annotation_episode/episode_services.py", "gene_annotation_episode/episode_bindings.py",
    "gene_annotation_episode/scientific_process_episodes.py"}
prechange = REPO / "verification/tool_graders_protein_structure_operands_2026-10-27_398/check005/source_snapshot"
run = PACKET / sys.argv[1]
run.mkdir(exist_ok=False)
snapshot = run / "source_snapshot"
temporary, cache = run / "temporary", run / "cache"
temporary.mkdir()
cache.mkdir()
files = []
for directory in ("gene_annotation_episode", "method_loop", "tests",
                  "research/slotted_process_library/publications"):
    files += [p for p in (source_root / directory).rglob("*") if p.is_file()
              and "__pycache__" not in p.parts and p.suffix != ".pyc"]
files += [source_root / "pyproject.toml"]
source_packet = source_root / PACKET.relative_to(REPO)
files += list(source_packet.glob("*.py"))
for directory in ("tool_graders_protein_structure_inputs_2026-10-27_386",
                  "tool_graders_protein_structure_execution_2026-10-27_390"):
    helper = source_root / "verification" / directory
    files += [helper / "fixture_helpers.py"] + list((helper / "fixtures").glob("*"))
files.extend(p for p in (source_packet).glob('*.md')
    if p.name.casefold() not in {'agents.md', 'agent.md', 'goal.md'})
files.extend(p for p in (source_root / 'verification/tool_graders_protein_structure_shared_contract_2026-10-27_380').glob('*.md')
    if p.name.casefold() not in {'agents.md', 'agent.md', 'goal.md'})
files.extend(p for p in (source_root / 'verification/tool_graders_protein_structure_operand_boundary_2026-10-27_394').glob('*.md')
    if p.name.casefold() not in {'agents.md', 'agent.md', 'goal.md'})
pins = []
for source in dict.fromkeys(files):
    if source.name.casefold() in {'agents.md', 'agent.md', 'goal.md'}:
        continue
    relative = source.relative_to(source_root)
    raw = ((prechange / relative).read_bytes() if baseline and str(relative) in preflight_files
           else source.read_bytes())
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
tests = sys.argv[3 if baseline else 2:] or ["tests/test_protein_structure_alignment_preflight.py"]
entry = run / "pytest_entry.py"
entry.write_text(
    "import json, os, pathlib, runpy, sys\n"
    "root = pathlib.Path(__file__).resolve().parent\n"
    "os.environ.update({k: str(root / 'temporary') for k in ('TMPDIR', 'TMP', 'TEMP')})\n"
    "import gene_annotation_episode.episode_services as service\n"
    "assert pathlib.Path(service.__file__).is_relative_to(root / 'source_snapshot')\n"
    "(root / 'executed_imports_before.json').write_text(json.dumps({'service': service.__file__}, indent=2))\n"
    "try:\n"
    "    runpy.run_module('pytest', run_name='__main__')\n"
    "finally:\n"
    "    imports = {name: str(getattr(module, '__file__', '')) for name, module in sys.modules.copy().items() "
    "if name.startswith(('gene_annotation_episode', 'method_loop'))}\n"
    "    (root / 'executed_imports_after.json').write_text(json.dumps(imports, indent=2))\n"
    "    assert all(pathlib.Path(path).is_relative_to(root / 'source_snapshot') for path in imports.values() if path)\n")
entry.chmod(0o444)
argv = [str(REPO / ".venv/bin/python"), "-B", str(entry), "-q", "--maxfail=1", "-p", "no:cacheprovider",
        "--basetemp", str(temporary / "pytest"), *[str(snapshot / p) for p in tests]]
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache),
    "PIP_CACHE_DIR": str(cache / "pip"), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
(run / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(run),
    "policy": policy.to_dict(), "environment": environment,
    "source_snapshot_origin": str(source_root),
    "preflight_baseline_origin": str(prechange) if baseline else None,
    "preflight_baseline_replacements": sorted(preflight_files) if baseline else [],
    "launcher_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
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
    owned = {"gene_annotation_episode/episode_services.py", "gene_annotation_episode/episode_bindings.py",
        "gene_annotation_episode/scientific_process_episodes.py", "tests/test_protein_structure_alignment_preflight.py"}
    receipt["owned_live_source_pins_unchanged"] = all(row["before"]["path"] not in owned for row in receipt["live_source_drift"])
    receipt["local_jobs_module"] = sys.modules["gene_annotation_episode.local_jobs"].__file__
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(run), "returncode": receipt["returncode"],
    "executed_snapshot_pins_unchanged": receipt["executed_snapshot_pins_unchanged"],
    "owned_live_source_pins_unchanged": receipt["owned_live_source_pins_unchanged"]}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
