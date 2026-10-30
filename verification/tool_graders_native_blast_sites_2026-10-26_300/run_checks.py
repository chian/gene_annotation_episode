"""Run a named retained verification under the exact caller local allocation."""
from pathlib import Path
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


def source_snapshot():
    """Capture this checkout's complete Python and knowledge inputs, not a glob subset."""
    paths = set((ROOT / "gene_annotation_episode").rglob("*.py"))
    paths.update((ROOT / "tests").rglob("*.py"))
    paths.update(path for path in (ROOT / "gene_annotation_episode/knowledge").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts)
    paths.add(Path(__file__).resolve())
    return {str(path.relative_to(ROOT)): {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
        for path in sorted(paths)}


def main():
    name, *arguments = sys.argv[1:]
    directory = Path(__file__).resolve().parent / name
    directory.mkdir()
    temporary = directory / "temporary"
    temporary.mkdir()
    policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
    command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", *arguments,
        "--basetemp=" + str(temporary / "pytest"), "--junitxml=" + str(directory / "junit.xml")]
    source = source_snapshot()
    (directory / "source_before.json").write_text(json.dumps(source, indent=2) + "\n")
    (directory / "intent.json").write_text(json.dumps({"command": command,
        "policy": policy.to_dict(), "source_coverage":
        "All gene_annotation_episode/**/*.py, tests/**/*.py, every knowledge file and this launcher",
        "source_hashes": source}, indent=2) + "\n")
    result = run_local_job(command, cwd=directory, policy=policy,
        stdout_path=directory / "stdout.log", stderr_path=directory / "stderr.log",
        env={"PYTHONPATH": str(ROOT) + os.pathsep + str(ROOT / "tests"),
             "EPISODE_NATIVE_BLAST_SITE_EXAMPLES": str(directory / "examples"),
             **{key: str(temporary) for key in ("TMPDIR", "TMP", "TEMP")}})
    (directory / "receipt.json").write_text(json.dumps(result.metadata, indent=2) + "\n")
    after = source_snapshot()
    (directory / "source_after.json").write_text(json.dumps(after, indent=2) + "\n")
    (directory / "source_delta.json").write_text(json.dumps({key: {
        "before": source.get(key), "after": after.get(key)}
        for key in sorted(set(source) | set(after)) if source.get(key) != after.get(key)}, indent=2) + "\n")
    print(json.dumps({"returncode": result.returncode, "directory": str(directory)}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
