"""Recalculate retained numerical sheets with all external operations forbidden."""
import builtins
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

from gene_annotation_episode.blast_database_grader import build_database_sheet, calculate_database_probabilities
from gene_annotation_episode.blast_hsp_site_calculators import calculate_blast_hsp_column_components
from gene_annotation_episode.blast_pairwise_grader import build_pairwise_sheet
from gene_annotation_episode.bvbrc_homology_inputs import _reported_bit_score_agrees


PACKET = Path(__file__).resolve().parent


def forbidden(*args, **kwargs):
    raise AssertionError("saved calculation attempted an external operation")


def main():
    source = PACKET / "filled_examples"
    cases = ["blastx_reverse", "tblastn_reverse", "tblastx_frames", "blastp_gaps", "blastn_reverse"]
    saved = {name: json.loads((source / (name + ".json")).read_text()) for name in cases}
    scores = json.loads((source / "native_score_comparison_evidence.json").read_text())
    snapshot = json.dumps(saved, sort_keys=True)
    with patch.object(builtins, "open", forbidden), patch.object(Path, "open", forbidden), \
            patch.object(socket, "socket", forbidden), patch.object(subprocess, "Popen", forbidden):
        for row in saved.values():
            for field in ("pairwise_sheet", "tabular_pairwise_sheet"):
                assert build_pairwise_sheet(row[field]["input"]) == row[field]
            for sheet, expected in zip(row["selected_hsp_sheets"], row["selected_hsp_components"]):
                assert calculate_blast_hsp_column_components(sheet) == expected
            database = row["database_caller_test"]["sheet"]
            assert build_database_sheet(database["normalized_result"]) == database
            assert calculate_database_probabilities(database)["unadjusted_probabilities"] is None
        for score in scores:
            assert _reported_bit_score_agrees(score["tabular_original_fields"]["bitscore"], score["json_hsp"]["bit_score"])
    assert json.dumps(saved, sort_keys=True) == snapshot
    result = {"saved_cases": cases, "saved_cases_recalculated": len(saved),
        "native_bit_score_comparisons": len(scores), "all_matched": True,
        "external_operations_forbidden_during_calculation": ["file_open", "socket", "subprocess"],
        "raw_inputs_unchanged": True,
        "additive_correction": "292 CONTRACT_ADDENDUM_005 resolves the former integer-bit-score discrepancy. The earlier evidence file's no-rule-change note describes its pre-addendum generation; its scores and lexemes remain untouched."}
    (PACKET / "saved_recalculation_and_score_resolution.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
