"""Persist supplied-byte D1 envelopes for projection verification; no native calls."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def produce(output):
    from tests.test_native_hmmer_preparation_worker import CASES, P1, CURRENT, bundle_arguments
    from gene_annotation_episode.native_hmmer_preparation_worker import grade_hmmer_preparation
    from gene_annotation_episode.native_hmmer_preparation_contracts import PROGRAM_MODES
    selected = {}
    for row in CASES:
        if row["returncode"] == 0:
            selected.setdefault((row["program"], row["mode"]), (P1 / row["bundle"], row["bundle_sha256"]))
    for index in range(4):
        path = CURRENT / ("test_actual_all_selected_modes" + str(index)) / "hmmer-preparation-attempt/bundle.json"
        bundle = json.loads(path.read_text())
        selected[(bundle["program"], bundle["mode"])] = (path, digest(path))
    assert set(selected) == {(program, mode) for program, modes in PROGRAM_MODES.items() for mode in modes}
    filled = output / "filled"
    filled.mkdir()
    manifest = []
    for (program, mode), (source, expected_hash) in sorted(selected.items()):
        args = bundle_arguments(source, expected_hash)
        bundle = json.loads(source.read_text())
        args["parameters"] = bundle["requested_job"]["native_hmmer_preparation"]["grading_parameters"]
        grading = grade_hmmer_preparation(**args)
        target = filled / (program + "__" + mode + ".json")
        target.write_text(json.dumps(grading, indent=2, allow_nan=False) + "\n")
        manifest.append({"program": program, "mode": mode, "bundle": str(source.relative_to(ROOT)),
            "bundle_sha256": expected_hash, "grading": str(target.relative_to(output)),
            "grading_sha256": digest(target), "size_bytes": target.stat().st_size,
            "sheet_schema": grading["sheet"]["schema"], "sheet_issue_count": len(grading["sheet"]["issues"]),
            "calculation_row_count": len(grading["calculations"]["rows"]),
            "calculation_issue_count": len(grading["calculations"]["issues"])})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"native_invocations": 0, "saved_mode_count": len(manifest),
                      "total_envelope_bytes": sum(row["size_bytes"] for row in manifest)}))


if __name__ == "__main__":
    if sys.argv[1] == "--produce":
        produce(Path(sys.argv[2]))
    else:
        from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
        output = Path(__file__).parent / sys.argv[1]
        output.mkdir()
        paths = [ROOT / "gene_annotation_episode/native_hmmer_preparation_worker.py",
                 ROOT / "gene_annotation_episode/native_hmmer_preparation_contracts.py",
                 ROOT / "tests/test_native_hmmer_preparation_worker.py", Path(__file__)]
        paths += list((ROOT / "gene_annotation_episode").glob("hmmer_*_*.py"))
        before = {str(path.relative_to(ROOT)): digest(path) for path in paths}
        command = [str(ROOT / ".venv/bin/python"), str(Path(__file__)), "--produce", str(output)]
        policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
        (output / "intent.json").write_text(json.dumps({"argv": command, "policy": policy.to_dict(),
                                                       "source_hashes": before}, indent=2) + "\n")
        result = run_local_job(command, cwd=output, policy=policy,
                              env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
        after = {str(path.relative_to(ROOT)): digest(path) for path in paths}
        (output / "receipt.json").write_text(json.dumps({"returncode": result.returncode,
            "metadata": result.metadata, "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path),
            "source_hashes_before": before, "source_hashes_after": after,
            "sources_unchanged": before == after}, indent=2) + "\n")
        print(json.dumps({"returncode": result.returncode, "stdout": result.stdout_path.read_text(),
                          "stderr": result.stderr_path.read_text()}))
        raise SystemExit(result.returncode)
