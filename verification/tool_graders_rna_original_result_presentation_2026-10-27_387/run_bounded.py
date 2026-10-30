"""Run presentation checks with caller-owned local limits and retained receipts."""
from pathlib import Path
import hashlib
import json
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]


def main():
    label, *selected = sys.argv[1:]
    directory = PACKET / label
    directory.mkdir(exist_ok=False)
    for name in ("tmp", "cache"):
        (directory / name).mkdir()
    policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
    paths = sorted(set([*list((REPO / "gene_annotation_episode").glob("*rna_structure*.py")),
        REPO / "gene_annotation_episode/scientific_process_prompt.py", REPO / "gene_annotation_episode/providers.py",
        REPO / "gene_annotation_episode/execution_episodes.py", REPO / "gene_annotation_episode/local_jobs.py",
        REPO / "gene_annotation_episode/communication.py", REPO / "gene_annotation_episode/native_lifecycle.py",
        REPO / "gene_annotation_episode/progress_records.py", REPO / "gene_annotation_episode/execution_contracts.py",
        REPO / "tests/test_rna_structure_presentation.py",
        *(REPO / value for value in selected if value.startswith("tests/") and value.endswith(".py")),
        REPO / "verification/tool_graders_rna_structure_integration_2026-10-26_360/NUMERICAL_EXAMPLES.json",
        REPO / "verification/tool_graders_rna_single_input_text_contract_2026-10-27_384/PLAN_001.md",
        Path(__file__).resolve()]))
    before = {}
    for path in paths:
        raw = path.read_bytes()
        relative = str(path.relative_to(REPO))
        before[relative] = hashlib.sha256(raw).hexdigest()
        target = directory / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    argv = [str(REPO / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "--basetemp=" + str(directory / "tmp/pytest"), "--junitxml=" + str(directory / "junit.xml"),
        *(str(REPO / value) for value in selected)]
    env = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(REPO),
        "TMPDIR": str(directory / "tmp"), "TMP": str(directory / "tmp"), "TEMP": str(directory / "tmp"),
        "XDG_CACHE_HOME": str(directory / "cache"), "PIP_CACHE_DIR": str(directory / "cache/pip")}
    (directory / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(directory),
        "policy": policy.to_dict(), "environment": env, "source_sha256_before": before}, indent=2) + "\n")
    try:
        result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
            stderr_path=directory / "stderr.txt", env=env)
        receipt = {"returncode": result.returncode, "metadata": result.metadata,
            "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
    except Exception as error:
        receipt = {"exception": type(error).__name__, "detail": str(error)}
        for field in ("code", "phase", "operational", "diagnostic"):
            if hasattr(error, field):
                receipt[field] = getattr(error, field)
    after = {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    receipt.update(source_sha256_after=after, sources_unchanged=before == after)
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"directory": str(directory), "returncode": receipt.get("returncode"),
        "sources_unchanged": before == after, "exception": receipt.get("exception")}))
    return receipt.get("returncode", 1)


if __name__ == "__main__":
    raise SystemExit(main())
