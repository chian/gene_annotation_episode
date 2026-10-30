"""Reproducible selected-reader demonstration; deterministic, no model inference."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_literature_completion_time_inputs import primary_fixture, SOURCE
from test_literature_completion_time_storage import setup
from gene_annotation_episode.literature_completion_time_storage import LiteratureCompletionTimeRepository
from gene_annotation_episode.literature_completion_time_prompt import COMPLETION_TIME_TASK


def main():
    directory = Path(__file__).parent
    args, sources, _ = primary_fixture()
    text = sources[SOURCE]["content"].decode()
    store, context, args = setup(directory / "primary_example_state_001", text=text, arguments=args)
    try:
        repo = LiteratureCompletionTimeRepository(store, context.run_id)
        outcome = repo.populate(context, args, "primary_completion_time_001")
        sheet_ref = outcome["result"]["sheet_ref"]
        saved = repo.read(sheet_ref)
        rows = repo.project_cells([sheet_ref], permitted_record_refs=outcome["record_refs"],
            components=["completion_time_ratio", "inverse_completion_time_ratio"])
        (directory / "PRIMARY_EXAMPLE_001.json").write_text(json.dumps({
            "source_original_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "execution_kind": "deterministic_selected_reader_with_explicit_source_interpretations_no_model_inference",
            "sheet_ref": sheet_ref, "sheet": saved["sheet"], "typed_requested_subset": rows,
            "scientific_limits": "Source-preparation endpoint-time comparison; no isolated molecular activity, contaminant fraction, probability or annotation credit."}, indent=2) + "\n")
        (directory / "COMPLETION_TIME_TASK_001.txt").write_text(COMPLETION_TIME_TASK + "\n")
        print(json.dumps({"sheet_ref": sheet_ref, "ratio_lower": rows[0]["reported_domain"]["lower"],
            "ratio_lower_inclusive": rows[0]["reported_domain"]["lower_inclusive"],
            "inverse_exact_upper": rows[1]["exact_domain"]["upper"]}))
    finally:
        store.close()

if __name__ == "__main__":
    main()
