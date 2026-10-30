"""Run only the composed Rfam verification under the existing local limits."""
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
directory = HERE / sys.argv[1]
directory.mkdir()
temporary = directory / "temporary"
temporary.mkdir()
paths = [ROOT / "tests/test_rfam_composed_workflow.py", Path(__file__),
    ROOT / "tests/test_execution_episodes_family.py", ROOT / "tests/test_execution_wiring.py",
    ROOT / "tests/test_practical_runtime.py",
    ROOT / "gene_annotation_episode/runtime.py", ROOT / "gene_annotation_episode/api_service_execution.py",
    ROOT / "gene_annotation_episode/api_services.py", ROOT / "gene_annotation_episode/api_rfam.py",
    ROOT / "gene_annotation_episode/execution_episodes.py", ROOT / "gene_annotation_episode/execution_service_setup.py",
    ROOT / "gene_annotation_episode/episode_return_records.py", ROOT / "gene_annotation_episode/tools.py",
    ROOT / "gene_annotation_episode/state.py", ROOT / "gene_annotation_episode/scientific_process_episodes.py",
    ROOT / "gene_annotation_episode/scientific_tool_library.py", ROOT / "gene_annotation_episode/tool_information.py",
    ROOT / "gene_annotation_episode/practical_yield.py", ROOT / "gene_annotation_episode/numerical.py"]
paths.extend(sorted((ROOT / "gene_annotation_episode").glob("rfam_batch*.py")))
paths.extend(sorted((ROOT / "method_loop").glob("*.py")))
paths.extend(sorted((ROOT / "research/slotted_process_library/publications/2026-10-24-001").rglob("*.json")))
paths.extend(path for path in (ROOT / "verification/tool_graders_rfam_transport_2026-10-26_234/live/single/003-fetch-json").iterdir() if path.is_file())


def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in dict.fromkeys(paths)}


command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp=" + str(temporary / "pytest"), "--junitxml=" + str(directory / "tests.xml"),
    str(ROOT / "tests/test_rfam_composed_workflow.py"), *sys.argv[2:]]
environment = {"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(directory / "cache"),
    "RFAM_WORKFLOW_RUNS": str(directory / "runs")}
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
before = hashes()
(directory / "intent.json").write_text(json.dumps({"command": command, "environment": environment,
    "policy": policy.to_dict(), "source_hashes_before": before}, indent=2, sort_keys=True) + "\n")
result = run_local_job(command, cwd=directory, policy=policy, env=environment)
receipt = {"scope": "Actual composed Workflow with controlled HTTP responses and scripted decisions; retained single native bytes and synthetic zero/generated-header batch; no live requests or configured model",
    "command": command, "environment": environment, "policy": policy.to_dict(),
    "source_hashes_before": before, "source_hashes_after": hashes(), "returncode": result.returncode,
    "metadata": result.metadata, "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
raise SystemExit(result.returncode)
