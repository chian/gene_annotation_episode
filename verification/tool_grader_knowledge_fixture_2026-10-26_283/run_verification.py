"""Run focused engineering fixtures within the existing local resource limits."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = Path(__file__).parent / sys.argv[1]
directory.mkdir()
tests = sys.argv[2:]
if not tests or any(not Path(value.split("::", 1)[0]).is_absolute() for value in tests):
    raise ValueError("explicit_absolute_test_paths_required")
paths = sorted({ROOT / name for name in (
    "tests/test_tool_knowledge.py", "tests/test_runtime.py",
    "tests/test_root_episode_boundary.py", "gene_annotation_episode/runtime.py",
    "gene_annotation_episode/tool_knowledge.py", "gene_annotation_episode/episode_journal.py",
    "gene_annotation_episode/composition_information.py", "gene_annotation_episode/local_jobs.py",
    "gene_annotation_episode/credit.py",
    "verification/tool_grader_knowledge_fixture_2026-10-26_283/run_verification.py",
)})


def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


before = hashes()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
argv = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "--basetemp=" + str(directory / "temporary"),
        "--junitxml=" + str(directory / "junit.xml"), *tests]
intent = {"argv": argv, "cwd": str(directory), "policy": asdict(policy),
          "source_sha256": before}
(directory / "intent.json").write_text(json.dumps(intent, indent=2) + "\n")
result = run_local_job(argv, cwd=directory, policy=policy,
    env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
         "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})
after = hashes()
receipt = {**intent, "source_sha256_after": after,
    "changed_sources": [name for name in before if before[name] != after[name]],
    "returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": result.returncode,
    "changed_sources": receipt["changed_sources"],
    "stdout_tail": result.stdout_path.read_text()[-10000:],
    "stderr_tail": result.stderr_path.read_text()[-2000:]}))
raise SystemExit(result.returncode)
