"""Populate saved numerical examples from retained text, without native jobs.

Run this script after run_native.py only when intentionally rebuilding the
fixtures. Ordinary tests read retained native files and never run HMMER.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.nhmmer_inputs import parse_nhmmer_artifacts, build_nhmmer_sheet
from gene_annotation_episode.nhmmer_grader import calculate_nhmmer_scores


def main():
    directory = Path(__file__).resolve().parent
    examples = []
    fields = ("native_evalue", "native_score_bits", "native_bias_bits", "native_accuracy", "model_length",
        "sequence_length", "model_span_positions", "sequence_span_positions", "sequence_envelope_positions",
        "model_span_coverage", "sequence_span_coverage", "sequence_envelope_coverage", "paired_positions",
        "insert_positions", "delete_positions", "alignment_columns", "paired_model_coverage",
        "paired_sequence_coverage", "posterior_lower_mean", "posterior_upper_mean")
    for name in ("nhmmer_sequence", "nhmmer_profile", "nhmmer_msa", "nhmmer_z_watson", "nhmmer_z_both", "nhmmscan"):
        run = directory / name
        native = parse_nhmmer_artifacts(program="nhmmscan" if name == "nhmmscan" else "nhmmer",
            artifacts={"stdout": (run / "stdout.txt").read_text(), "tblout": (run / "hits.tbl").read_text()},
            artifact_refs={"stdout": name + "/stdout.txt", "tblout": name + "/hits.tbl"}, engine_version="3.4")
        sheet = build_nhmmer_sheet(native, inputs=json.loads((run / "inputs.json").read_text()))
        scores = calculate_nhmmer_scores(sheet)
        for filename, value in (("sheet.json", sheet), ("scores.json", scores)):
            (run / filename).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
        examples.append({"run": name, "kind": "synthetic_sequences_real_HMMER_3.4_execution",
            "program": sheet["operation"]["program"], "query_construction_mode": sheet["operation"]["query_construction_mode"],
            "loci": [{"record_key": row["record_key"], "identities": row["identities"], "strand": row["strand"],
                **{field: row[field] for field in fields}, "posterior_residue_denominator": row["components"]["posterior_lower_mean"]["denominator"]}
                for row in scores["loci"]], "issues": scores["issues"]})
    (directory / "filled_examples.json").write_text(json.dumps(examples, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps(examples, indent=2))


if __name__ == "__main__":
    main()
