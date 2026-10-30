"""Run only retained-data grading CLIs, under the explicit local allocation."""
from pathlib import Path
import hashlib
import json
import sys

from gene_annotation_episode.infernal_native_result_views import NATIVE_INFERNAL_METRICS
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FIXTURES = ROOT / "tests/fixtures/native_infernal_result_worker"
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
SOURCES = ["native_infernal_result_worker.py", "infernal_native_result_views.py",
    "native_infernal_contracts.py", "infernal_search_inputs.py", "infernal_search_grader.py",
    "cmalign_inputs.py", "cmalign_grader.py"]


def main():
    examples = {}
    cases = [("cmsearch", "search_hit"), ("cmscan", "search_hit"),
        ("cmsearch", "search_sequence"), ("cmalign", "alignment_sequence"),
        ("cmalign", "alignment_column"), ("cmalign", "alignment_pair"),
        ("cmalign_native_failure", "alignment_sequence")]
    for case, family in cases:
        source = FIXTURES / case
        bundle = json.loads((source / "bundle.json").read_text())
        directory = OUT / "examples_001" / (case + "_" + family)
        directory.mkdir(parents=True, exist_ok=True)
        artifacts = []
        for kind, rows in (("input", bundle["inputs"]), ("output", bundle["artifacts"])):
            for row in rows:
                artifacts.append({**{k: row[k] for k in ("role", "format", "relative_path")},
                    "kind": kind, "artifact_ref": "captured_" + kind + "_" + row["role"],
                    "path": str(source / row["relative_path"])})
        selection = {"offset": 0, "limit": 2}
        if case == "cmalign" and family == "alignment_sequence":
            selection = {"record_keys": ["artifact:captured_output_stockholm/alignment:0/sequence:0",
                "artifact:captured_output_stockholm/alignment:0/sequence:8"]}
        plan = {"version": "native_infernal_grading_plan_v1", "bundle": bundle,
            "artifacts": artifacts, "directory": str(directory / "graded"), "failures": [],
            "selector": {"version": "native_infernal_result_selector_v1",
                "acquisition": "complete_bound_bundle", "projection": {"family": family,
                    "rows": selection, "metrics": list(NATIVE_INFERNAL_METRICS[family])}}}
        plan_path = directory / "plan.json"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
        command = [sys.executable, "-m", "gene_annotation_episode.native_infernal_result_worker", str(plan_path)]
        result = run_local_job(command, cwd=directory, policy=POLICY,
            stdout_path=directory / "stdout.log", stderr_path=directory / "stderr.log",
            env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
        receipt = {"command": command, "returncode": result.returncode,
            "metadata": result.metadata, "source_hashes": {name: hashlib.sha256(
                (ROOT / "gene_annotation_episode" / name).read_bytes()).hexdigest() for name in SOURCES},
            "bundle_sha256": hashlib.sha256((source / "bundle.json").read_bytes()).hexdigest()}
        (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(result.stderr_path.read_text())
        manifest = json.loads((directory / "graded/worker-result.json").read_text())
        rows = [json.loads(line) for line in (directory / "graded/selected-rows.ndjson").read_text().splitlines()]
        examples[case + "_" + family] = {"manifest": manifest, "selected_rows": rows,
            "receipt": str(directory.relative_to(OUT) / "receipt.json")}
        print(case, family, "complete=" + str(manifest["numerical_complete"]), "rows=" + str(len(rows)))
    (OUT / "SELECTED_EXAMPLES_001.json").write_text(json.dumps(examples, indent=2) + "\n")


if __name__ == "__main__":
    main()
