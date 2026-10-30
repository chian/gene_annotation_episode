"""Retain complete generated examples and compare frozen v1 computations."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def work(directory):
    from gene_annotation_episode.blast_iteration_calculators import calculate_blast_iteration_components
    from tests.test_blast_iteration_target_context import example, run, taxonomy
    manifest, summaries = [], []
    for name in ("distinct_targets", "missing_first_target", "conflicting_first_target"):
        args = example()
        if name == "missing_first_target":
            args["target_contexts"].pop(0)
        elif name == "conflicting_first_target":
            extra = deepcopy(args["target_contexts"][0])
            extra["target_context"]["lineage"][0]["taxid"] = 99
            args["target_contexts"].append(extra)
        sheet, result = run(args)
        target = directory / name
        target.mkdir()
        for filename, value in (("inputs.json", args), ("sheet.json", sheet), ("components.json", result)):
            path = target / filename
            raw = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
            path.write_bytes(raw)
            manifest.append(dict(path=str(path.relative_to(directory)), size_bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(), classification="synthetic_target_taxonomy"))
        summaries.append(dict(example=name, searches=[dict(
            qualification=row["target_context_qualification"],
            target_matching_fraction=taxonomy(row)["ranks"][0]["target_matching_fraction"],
            parsed_hsps=row["counts"]["parsed_hsp_count"]["value"])
            for row in result["searches"]]))
    old_root = ROOT / "verification/tool_graders_blast_native_iteration_parser_2026-10-26_316/examples002"
    old_manifest = json.loads((old_root / "MANIFEST.json").read_text())
    for row in old_manifest:
        raw = (old_root / row["path"]).read_bytes()
        assert len(raw) == row["size_bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
    compared = []
    for row in old_manifest:
        if row["path"].endswith("/iteration-sheet.json"):
            path = old_root / row["path"]
            before = json.loads(path.with_name("iteration-components.json").read_text())
            actual = calculate_blast_iteration_components(json.loads(path.read_text()))
            assert actual == before, row["example"]
            compared.append(row["example"])
    (directory / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (directory / "NUMERICAL_SUMMARY.json").write_text(json.dumps(summaries, indent=2) + "\n")
    (directory / "V1_REPLAY.json").write_text(json.dumps(dict(examples=compared,
        exact_equal=True, old_artifacts_verified=len(old_manifest)), indent=2) + "\n")
    print(json.dumps(dict(summaries=summaries, exact_old_v1_replays=len(compared), verified_old_artifacts=len(old_manifest))))


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--work":
        work(Path(sys.argv[2]))
        return 0
    directory = HERE / sys.argv[1]
    directory.mkdir()
    temporary = directory / "temporary"
    temporary.mkdir()
    command = [str(ROOT / ".venv/bin/python"), "-B", str(Path(__file__).resolve()), "--work", str(directory)]
    policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
    result = run_local_job(command, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
        stderr_path=directory / "stderr.txt", env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(temporary), "XDG_CACHE_HOME": str(directory / "cache")})
    (directory / "receipt.json").write_text(json.dumps(dict(command=command, policy=policy.to_dict(),
        returncode=result.returncode, metadata=result.metadata), indent=2) + "\n")
    print((directory / "stdout.txt").read_text())
    print((directory / "stderr.txt").read_text())
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
