"""Populate source cells from an explicitly inherited graph reconstruction.

This is a controlled extraction representation, not the paper's original table,
a fresh graph digitization, source acquisition or a model-backed episode.
"""
from pathlib import Path
import csv
import hashlib
import io
import json

from gene_annotation_episode.domain import identity
from gene_annotation_episode.literature_experimental_contracts import HEADERS
from gene_annotation_episode.literature_rate_reader import read_rate_table
from gene_annotation_episode.literature_rate_calculations import populate_rate_contrast


def main():
    directory = Path(__file__).resolve().parent
    packet = "research/experimental_scoring_review_2026-10-23/a105_sheet_construction_001/CSID_NUMERICAL_CELLS_003.md"
    # These operands are transcribed from the already-read retained packet.
    # The count is three measurements, with biological preparation identity
    # and between-arm pairing unspecified. No independent-unit facts are added.
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
    writer.writerow(HEADERS)
    for arm, condition, mean, sd in [
        ("no_inhibitor", "no_added_L2HG", "~0.16062356", "0.01025723"),
        ("L2HG", "5_mM_L2HG", "~0.10483983", "0.01091"),
    ]:
        writer.writerow(["N-terminal His-tagged E. coli CsiD preparation", "Supplementary_Figure_5",
            arm, condition, "oxygen_consumption", "amount_per_time_per_preparation", mean,
            "umol/min", "sd", sd, "3", "unspecified", "graph_derived"])
    text = stream.getvalue()
    (directory / "csid_retained_extraction.tsv").write_text(text)
    table = {"source_ref": identity("source", {"retained_packet": packet}),
        "artifact_ref": "artifact_" + hashlib.sha256(text.encode()).hexdigest(),
        "text": text, "representation": "retained_extraction", "delimiter": "\t"}
    extracted = read_rate_table(table,
        expected_subject="N-terminal His-tagged E. coli CsiD preparation",
        expected_experiment="Supplementary_Figure_5")
    selection = dict(reference_arm="no_inhibitor", test_arm="L2HG",
        reference_condition="no_added_L2HG", test_condition="5_mM_L2HG")
    observed = populate_rate_contrast(extracted, **selection)
    conditional = populate_rate_contrast(extracted, **selection,
        dependence="independent", observation_model="independent_normal_groups")
    result = {"provenance": {"representation": "controlled_retained_extraction",
        "original_source": "10.1038/s41467-018-07563-6",
        "original_locator": "Supplementary Figure 5, supplement PDF page 7",
        "retained_packet": packet, "fresh_primary_source_validation": False,
        "digits_are_inherited_graph_reconstruction": True,
        "L2HG_SD_is_approximately_0_01091": True,
        "conditional_model_is_not_an_extracted_fact": True,
        "source_ref_is_example_identity_not_a_Store_record": True},
        "source_sheet_without_added_model": observed,
        "separate_conditional_statistical_illustration": conditional}
    (directory / "csid_populated_source_sheet.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n")
    summary = {name: cell["value"] for name, cell in observed["cells"].items()}
    summary["conditional_source_index"] = conditional["cells"]["source_signed_index"]["value"]
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
