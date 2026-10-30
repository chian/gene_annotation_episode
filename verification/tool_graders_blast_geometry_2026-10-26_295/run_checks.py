"""Bounded, retained verification only; never launches a BLAST search."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
SOURCES = [
    "gene_annotation_episode/blast_pairwise_grader.py",
    "gene_annotation_episode/blast_hsp_site_inputs.py",
    "gene_annotation_episode/blast_database_grader.py",
    "gene_annotation_episode/bvbrc_homology_grader.py",
    "gene_annotation_episode/bvbrc_homology_inputs.py",
    "tests/test_blast_native_coordinate_conventions.py",
    "tests/test_bvbrc_homology_grader.py",
]


def main():
    label, *selected = sys.argv[1:]
    directory = PACKET / label
    directory.mkdir()
    temporary = directory / "temporary"
    temporary.mkdir()
    manifest = []
    for name in SOURCES:
        source = ROOT / name
        if not source.exists():
            continue
        target = directory / "source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        raw = source.read_bytes()
        manifest.append({"path": name, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)})
    (directory / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if selected[0] == "python":
        command = [str(ROOT / ".venv/bin/python"), *selected[1:]]
    else:
        command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", *selected,
                   "--basetemp", str(temporary / "pytest"), "--junitxml", str(directory / "junit.xml")]
    policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
    result = run_local_job(command, cwd=directory, policy=policy,
        stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
        env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
             "XDG_CACHE_HOME": str(directory / "cache")})
    receipt = {"command": command, "policy": asdict(policy), "returncode": result.returncode,
               "metadata": result.metadata}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
    print((directory / "stdout.txt").read_text())
    print((directory / "stderr.txt").read_text())
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
