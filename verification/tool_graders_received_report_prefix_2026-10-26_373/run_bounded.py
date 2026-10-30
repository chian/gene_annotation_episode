"""Focused receipt-prefix checks under the existing local resource binding."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = PACKET / sys.argv[1]
directory.mkdir(exist_ok=False)
tests = ["tests/test_episode_received_report_prefix.py", "tests/test_episode_commissions.py",
    "tests/test_bvbrc_appservice_custody.py", "tests/test_episode_receipts.py"]
sources = ["gene_annotation_episode/" + name for name in (
    "episode_receipts.py", "episode_commissions.py", "bvbrc_appservice_custody.py",
    "episode_return_records.py", "episode_journal.py", "state.py", "communication.py",
    "runtime.py", "independent_execution.py", "execution_contracts.py", "local_jobs.py",
    "native_lifecycle.py", "_local_job_worker.py")]
sources += tests + [str(Path(__file__).relative_to(ROOT)),
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_010.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_011.md"]
pins = []
for name in sources:
    raw = (ROOT / name).read_bytes()
    snapshot = directory / "sources" / name
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(raw)
    pins.append({"path": name, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)})
(directory / "source_before.json").write_text(json.dumps(pins, indent=2) + "\n")
temporary, cache = directory / "temporary", directory / "cache"
temporary.mkdir()
cache.mkdir()
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp", str(temporary / "pytest"), *[str(ROOT / name) for name in tests]]
# These eight pre-existing episode_receipts failures were already reproduced
# with pre360 production modules. check001 preserves this run's same failures;
# they are not silently counted as passing checks of the receipt-prefix fix.
known_baseline = ["test_runtime_credits_only_requested_child_information_and_replay_keeps_history",
    "test_native_workbook_pages_return_one_finding_through_child_form_and_replay",
    "test_selected_state_read_delivers_existing_findings_but_detail_read_does_not",
    "test_different_parent_scalar_does_not_remove_child_inherited_information",
    "test_failed_form_repair_and_interruption_preserve_work_and_observation_boundary"]
argv += ["-k", " and ".join("not " + name for name in known_baseline)]
environment = {"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
    "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache)}
(directory / "request.json").write_text(json.dumps({"argv": argv, "cwd": str(directory),
    "policy": policy.to_dict(), "environment": environment}, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
        stderr_path=directory / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error)}
after = [{"path": row["path"], "sha256": hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
    "size_bytes": (ROOT / row["path"]).stat().st_size} for row in pins]
(directory / "source_after.json").write_text(json.dumps(after, indent=2) + "\n")
receipt["source_unchanged"] = after == pins
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": receipt["returncode"],
    "source_unchanged": receipt["source_unchanged"]}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
