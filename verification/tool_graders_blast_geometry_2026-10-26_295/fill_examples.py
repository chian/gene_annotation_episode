"""Retain filled geometry sheets from already retained actual paired outputs."""
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tests"))

from test_blast_native_coordinate_conventions import CASES, NATIVE, retained_search, site_sheet
from gene_annotation_episode.blast_database_grader import build_database_sheet
from gene_annotation_episode.blast_hsp_site_calculators import calculate_blast_hsp_column_components
from gene_annotation_episode.blast_pairwise_grader import alignment_components, build_pairwise_sheet


def main():
    destination = PACKET / "filled_examples"
    destination.mkdir()
    manifest, summaries, score_comparisons = [], [], []
    for folder, case, *_ in CASES:
        search, lengths = retained_search(folder, case, "json15")
        table, _ = retained_search(folder, case, "tabular7")
        pair = build_pairwise_sheet(search["normalized"])
        tab_pair = build_pairwise_sheet(table["normalized"])
        program = search["normalized"]["search"]["program"]
        sites = [site_sheet(row["native"], program, lengths) for row in pair["hsps"]]
        site_scores = [calculate_blast_hsp_column_components(row) for row in sites]
        db_input = json.loads(json.dumps(search["normalized"]))
        db_input["mode"] = "database"
        output = {"evidence_kind": "actual_retained_native_pairwise_outputs",
            "live_execution_in_workload295": False, "search": search, "tabular_search": table,
            "pairwise_sheet": pair, "tabular_pairwise_sheet": tab_pair,
            "selected_hsp_sheets": sites, "selected_hsp_components": site_scores,
            "database_caller_test": {"evidence_kind": "synthetic_database_envelope_of_actual_paired_measurements",
                                     "sheet": build_database_sheet(db_input)}}
        (destination / (case + ".json")).write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
        first = pair["hsps"][0]["components"]
        summaries.append({"case": case, "hsp_count": len(pair["hsps"]), "first_hsp": {
            "counts": first["counts"], "fractions": first["fractions"],
            "first_pair": first["pairs"][0], "last_pair": first["pairs"][-1]},
            "union_counts": pair["union"]["counts"], "union_fractions": pair["union"]["fractions"]})
        for fmt in ("json15", "tabular7"):
            directory = NATIVE / folder / (case + "_" + fmt)
            for path in sorted(directory.rglob("*")):
                if path.is_file() and path.name in {"report.json", "report.tsv", "plan.json", "bundle.json", "receipt.json", "query_sequence.fa", "subject_sequence.fa"}:
                    raw = path.read_bytes()
                    manifest.append({"path": str(path.relative_to(ROOT)), "size_bytes": len(raw),
                                     "sha256": hashlib.sha256(raw).hexdigest()})
        if program in ("blastx", "tblastn", "tblastx"):
            for ordinal, (hsp, row) in enumerate(zip(search["normalized"]["hits"][0]["hsps"], table["native"]["search"]["rows"])):
                score_comparisons.append({"case": case, "hsp_ordinal": ordinal,
                    "json_hsp": hsp, "tabular_original_fields": row["fields"],
                    "reported_bit_score_difference": hsp["bit_score"] - float(row["fields"]["bitscore"]),
                    "note": "Original numeric lexemes and native values; no score-matching rule changed by geometry295."})
    search, lengths = retained_search("native_ranges", "blastx_range_reverse", "json15")
    hsp = search["normalized"]["hits"][0]["hsps"][0]
    selected = {"evidence_kind": "actual_retained_native_selected_range",
        "search": search, "explicit_full_operand_lengths": lengths,
        "components": alignment_components(hsp, program="blastx", query_length=lengths["query"],
            reference_length=lengths["reference"], coordinate_convention="blast_json2"),
        "qualification": "Full length supplied explicitly; reported query length 186 remains unchanged; original coordinates are not offset."}
    (destination / "blastx_range_reverse.json").write_text(json.dumps(selected, indent=2, allow_nan=False) + "\n")
    (destination / "native_artifact_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (destination / "native_score_comparison_evidence.json").write_text(json.dumps(score_comparisons, indent=2) + "\n")
    (destination / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    for row in summaries:
        print(json.dumps(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
