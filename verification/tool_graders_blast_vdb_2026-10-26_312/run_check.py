"""Execute only parser/calculator tests under the existing caller-owned limits."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]


def hashes():
    files = [ROOT / "gene_annotation_episode" / name for name in (
        "blast_vdb_inputs.py", "blast_vdb_calculators.py", "blast_sequence_database.py",
        "blast_report_collection.py", "blast_pairwise_grader.py", "blast_program_context.py")]
    files += [ROOT / "tests" / name for name in ("test_blast_vdb_inputs.py", "test_blast_vdb_calculators.py")]
    files += [ROOT / "verification/tool_graders_blast_vdb_contract_2026-10-26_309" / name for name in (
        "PROPOSED_CONTRACT_001.md", "PROPOSED_CONTRACT_ADDENDUM_002.md", "sources/MANIFEST.json")]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def main():
    directory = PACKET / (sys.argv[1] if len(sys.argv) > 1 else "check_001")
    directory.mkdir()
    command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-o", f"cache_dir={directory/'pytest-cache'}",
        "--basetemp", str(directory / "temporary"), "--junitxml", str(directory / "pytest.xml"),
        str(ROOT / "tests/test_blast_vdb_inputs.py"), str(ROOT / "tests/test_blast_vdb_calculators.py")]
    before = hashes()
    result = run_local_job(command, cwd=directory, policy=LocalJobPolicy(20 * 1024**3, 4 * 1024**3),
        env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
    receipt = dict(command=command, returncode=result.returncode, metadata=result.metadata,
        stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path), source_sha256_before=before, source_sha256_after=hashes())
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(result.stdout_path.read_text()); print(result.stderr_path.read_text())
    print(json.dumps({"receipt": str(directory / "receipt.json"), "returncode": result.returncode}))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
