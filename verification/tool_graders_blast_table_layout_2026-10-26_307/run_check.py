"""Verify the collector correction through the existing bounded local job."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
TESTS = [
    "test_blast_table_layout.py", "test_blast_archive_member_digest.py",
    "test_blast_report_collection.py", "test_blast_program_context.py",
    "test_blast_grading_inputs.py", "test_blast_pairwise_results.py",
    "test_blast_pairwise_result_views.py", "test_native_blast_hsp_sites.py",
    "test_blast_native_coordinate_conventions.py",
]


def source_hashes():
    paths = list((ROOT / "gene_annotation_episode").glob("*.py"))
    paths += list((ROOT / "tests").glob("*.py"))
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def main():
    directory = PACKET / "check_001"
    directory.mkdir()
    command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-o",
        f"cache_dir={directory / 'pytest-cache'}", "--basetemp", str(directory / "temporary"),
        "--junitxml", str(directory / "pytest.xml")]
    command += [str(ROOT / "tests" / name) for name in TESTS]
    before = source_hashes()
    result = run_local_job(command, cwd=directory,
        policy=LocalJobPolicy(20 * 1024**3, 4 * 1024**3),
        env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
    after = source_hashes()
    changed = [p for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)]
    receipt = {"command": command, "returncode": result.returncode,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path),
        "metadata": result.metadata, "source_sha256_before": before,
        "source_sha256_after": after, "changed_source_paths": changed}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(result.stdout_path.read_text())
    print(result.stderr_path.read_text())
    print(json.dumps({"receipt": str(directory / "receipt.json"),
                      "returncode": result.returncode, "changed_source_paths": changed}))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
