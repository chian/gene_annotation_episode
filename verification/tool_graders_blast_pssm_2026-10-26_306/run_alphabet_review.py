"""Verify the additive native-alphabet correction in the bounded job path."""
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
TESTS = ["tests/test_blast_pssm_inputs.py", "tests/test_blast_pssm_calculators.py",
         "tests/test_blast_pssm_alphabet.py"]
SOURCES = ["gene_annotation_episode/blast_pssm_inputs.py",
           "gene_annotation_episode/blast_pssm_calculators.py", *TESTS]


def hashes():
    paths = [ROOT / name for name in SOURCES]
    paths += [p for p in (PACKET / "sources").iterdir() if p.is_file()]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    directory = PACKET / "alphabet_review001"
    directory.mkdir()
    command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-o",
        f"cache_dir={directory / 'pytest-cache'}", "--basetemp", str(directory / "temporary"),
        "--junitxml", str(directory / "pytest.xml"), *[str(ROOT / name) for name in TESTS]]
    before = hashes()
    result = run_local_job(command, cwd=directory,
        policy=LocalJobPolicy(20 * 1024**3, 4 * 1024**3),
        env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
    after = hashes()
    receipt = {"command": command, "returncode": result.returncode,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path),
        "metadata": result.metadata, "source_sha256_before": before, "source_sha256_after": after,
        "changed_source_paths": [p for p in before if before[p] != after[p]]}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(result.stdout_path.read_text())
    print(result.stderr_path.read_text())
    print(json.dumps({"receipt": str(directory / "receipt.json"), "returncode": result.returncode,
                      "changed_source_paths": receipt["changed_source_paths"]}))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
