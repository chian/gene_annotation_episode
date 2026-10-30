"""Run this packet's retained-byte checks through the existing local job boundary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
WATCHED = [
    "gene_annotation_episode/blast_report_collection.py",
    "gene_annotation_episode/blast_grading_inputs.py",
    "gene_annotation_episode/blast_program_context.py",
    "gene_annotation_episode/blast_pairwise_results.py",
    "gene_annotation_episode/native_blast_result_worker.py",
    "gene_annotation_episode/native_blast_hsp_views.py",
    "tests/test_blast_archive_member_digest.py",
    "tests/test_blast_report_collection.py",
    "tests/test_blast_program_context.py",
    "tests/test_blast_grading_inputs.py",
]


def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in WATCHED if (ROOT / name).is_file()}


def main():
    label, kind = sys.argv[1:]
    directory = PACKET / label
    directory.mkdir()
    command = [str(ROOT / ".venv/bin/python")]
    if kind in {"probe", "compare"}:
        command += [str(PACKET / "native_probe.py")]
        if kind == "compare":
            command.append(str(PACKET / "baseline_001"))
    elif kind == "tests":
        command += ["-m", "pytest", "-q", "-o", f"cache_dir={directory / 'pytest-cache'}",
                    "--basetemp", str(directory / "temporary"),
                    "--junitxml", str(directory / "pytest.xml")]
        command += [str(ROOT / name) for name in (
            "tests/test_blast_archive_member_digest.py",
            "tests/test_blast_report_collection.py",
            "tests/test_blast_program_context.py",
            "tests/test_blast_grading_inputs.py",
        )]
    else:
        raise ValueError("unknown_check_kind")
    before = hashes()
    result = run_local_job(command, cwd=directory,
        policy=LocalJobPolicy(20 * 1024**3, 4 * 1024**3),
        env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
    receipt = {"command": command, "returncode": result.returncode,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path),
        "metadata": result.metadata, "source_sha256_before": before,
        "source_sha256_after": hashes()}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(result.stdout_path.read_text())
    print(result.stderr_path.read_text())
    print(json.dumps({"receipt": str(directory / "receipt.json"), "returncode": result.returncode}))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
