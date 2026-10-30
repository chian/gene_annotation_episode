"""Execute frozen scientific prompt sources with ordinary bounded local_jobs."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
sys.path.insert(0, str(REPO))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


def identity(path):
    raw = path.read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


directory = PACKET / sys.argv[1]
directory.mkdir(exist_ok=False)
tests = sys.argv[2:] or ["tests/test_rna_comparison_scientific_prompt.py",
    "tests/test_rna_comparison_presentation.py", "tests/test_scientific_process_prompt_delivery.py",
    "tests/test_alignment_result_presentation.py", "tests/test_decision_provider_frames.py"]
snapshot = directory / "source_snapshot"
files = [path for package in ("gene_annotation_episode", "method_loop")
    for path in (REPO / package).rglob("*") if path.is_file() and "__pycache__" not in path.parts
    and path.suffix in {".py", ".json", ".md", ".toml", ".txt"}]
files += [REPO / "pyproject.toml"]
files += [REPO / test.split("::")[0] for test in tests]
files += [REPO / "tests" / name for name in ("test_scientific_process_prompt_delivery.py",
    "test_rna_comparison_presentation.py", "test_bvbrc_genome_alignment_bundle_resolution.py",
    "test_bvbrc_genome_alignment_associations.py", "test_bvbrc_genome_alignment_retained_records.py",
    "test_bvbrc_genome_alignment_sheet.py", "test_mauve_v4_formats.py")]
files += [PACKET / "baseline_scientific_process_prompt.py", PACKET / "run_bounded.py"]
files += [REPO / "verification" / name / "fixture_helpers.py" for name in (
    "tool_graders_rna_comparison_inputs_2026-10-26_366",
    "tool_graders_rna_comparison_calculations_2026-10-26_367")]
files += [REPO / "verification/tool_graders_rna_comparison_shared_integration_2026-10-26_372/FILLED_ACTUAL_SCAN_001.json"]
files += [REPO / "verification" / path for path in (
    "tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/retained_sources/mauve/testdata/small.mauve",
    "tool_graders_mauve_sidecars_2026-10-25/FILLED_EXAMPLES_001.json",
    "tool_graders_mauve_v4_2026-10-25/official_small.document.json",
    "tool_graders_mauve_v4_2026-10-25/official_small.components.json")]
pins = []
for path in sorted(set(files)):
    relative = path.relative_to(REPO)
    target = snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(path.read_bytes())
    pins.append({"path": str(relative), **identity(path)})
(directory / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")
temporary, cache = directory / "temporary", directory / "cache"
temporary.mkdir()
cache.mkdir()
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(REPO / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
    "--basetemp", str(temporary / "pytest"), *[str(snapshot / test) for test in tests]]
environment = {"PYTHONPATH": str(snapshot), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
request = {"argv": argv, "cwd": str(directory), "policy": policy.to_dict(), "environment": environment,
    "execution_source": "source_snapshot", "live_source_after_used_for_execution": False}
(directory / "selected_request.json").write_text(json.dumps(request, indent=2) + "\n")
try:
    result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
        stderr_path=directory / "stderr.txt", env=environment)
    receipt = {"returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
except Exception as error:
    receipt = {"returncode": None, "exception_type": type(error).__name__, "exception": str(error)}
finally:
    after = [{"path": row["path"], **identity(REPO / row["path"])} for row in pins]
    frozen_after = [{"path": row["path"], **identity(snapshot / row["path"])} for row in pins]
    (directory / "source_pins_after.json").write_text(json.dumps(after, indent=2) + "\n")
    (directory / "snapshot_pins_after.json").write_text(json.dumps(frozen_after, indent=2) + "\n")
    receipt["live_source_pins_unchanged"] = after == pins
    receipt["executed_snapshot_pins_unchanged"] = frozen_after == pins
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": receipt["returncode"],
    "live_source_pins_unchanged": receipt["live_source_pins_unchanged"],
    "executed_snapshot_pins_unchanged": receipt["executed_snapshot_pins_unchanged"]}))
raise SystemExit(receipt["returncode"] if receipt["returncode"] is not None else 99)
