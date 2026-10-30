"""Write SYNTHETIC H2 examples; never run BLAST or contact a service.

Only the optional verification of retained source transformation methods uses
a subprocess (Perl JSON::PP). The production modules never invoke it.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from test_bvbrc_homology_inputs import bundle, parse_all, parse_raw, raw_document
from test_bvbrc_homology_grader import example, program_document, metadata_and_sheet, add_subject
from gene_annotation_episode.bvbrc_homology_grader import calculate_homology_scores
from gene_annotation_episode.bvbrc_homology_inputs import _expected_processed, _decode_description


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def main():
    binding, artifacts, contents, parsed, metadata, sheet = example()
    scores2 = calculate_homology_scores(sheet, database_model={"temperature_bits": 2})
    saved = json.loads(json.dumps(sheet, allow_nan=False))
    scores1 = calculate_homology_scores(saved, database_model={"temperature_bits": 1})
    assert saved == sheet
    save("synthetic_binding.json", binding)
    save("synthetic_parse.json", parsed)
    save("synthetic_metadata_bindings.json", metadata)
    save("synthetic_sheet.json", sheet)
    save("synthetic_scores_temperature_2.json", scores2)
    save("synthetic_recalculated_temperature_1.json", scores1)
    table_binding, table_artifacts, table_contents = bundle(primary="tabular")
    table_parsed = parse_all(table_binding, table_artifacts, table_contents)
    _, table_sheet = metadata_and_sheet(table_parsed, table_artifacts, table_contents)
    save("synthetic_table_primary_sheet.json", table_sheet)
    programs = []
    for program in ("blastp", "blastn", "blastx", "tblastn", "tblastx"):
        for mode in ("database_identification", "pairwise_correspondence"):
            document = program_document(program)
            binding, artifacts, contents = bundle(document, mode=mode, extras=False)
            if mode == "pairwise_correspondence":
                add_subject(binding, document)
            _, other_sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents)
            scores = calculate_homology_scores(other_sheet)
            hsp = scores["alignment_supplements"]["queries"][0]["hits"][0]["hsps"][0]
            programs.append({"program": program, "scientific_mode": mode,
                "query_paired_coverage": hsp["alignment_components"]["fractions"]["query_paired_coverage"],
                "reference_paired_coverage": hsp["alignment_components"]["fractions"]["reference_paired_coverage"],
                "paired_query_positions": hsp["alignment_components"]["counts"]["paired_query_positions"],
                "paired_reference_positions": hsp["alignment_components"]["counts"]["paired_reference_positions"]})
    save("synthetic_program_modes.json", programs)
    document = program_document("blastx")
    document["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][0].update(
        query_from=15, query_to=7, query_frame=-1, hit_from=2, hit_to=4)
    binding, artifacts, contents = bundle(document, extras=False)
    _, reverse = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents)
    save("synthetic_reverse_blastx_sheet.json", reverse)
    save("synthetic_reverse_blastx_scores.json", calculate_homology_scores(reverse))

    harness = ROOT / "verification/tool_graders_bvbrc_homology_artifact_contract_2026-10-24/source_transform_harness.pl"
    source = OUT / "synthetic_transform_branches.raw.json"
    processed = OUT / "synthetic_transform_branches.processed.json"
    sidecar = OUT / "synthetic_transform_branches.metadata.json"
    completed = subprocess.run(["perl", str(harness), str(source), str(processed), str(sidecar)],
                               check=True, capture_output=True, text=True)
    raw = json.loads(source.read_bytes())
    expected = [_expected_processed(entry) for entry in raw["BlastOutput2"]]
    assert expected == json.loads(processed.read_bytes())
    expected_metadata = {}
    for hit in raw["BlastOutput2"][0]["report"]["results"]["search"]["hits"]:
        for desc in hit["description"]:
            transformed, values = _decode_description(desc)
            if values:
                expected_metadata[transformed["id"]] = values
    assert expected_metadata == json.loads(sidecar.read_bytes())
    save("source_transform_receipt.json", {"provenance": "SYNTHETIC input; retained source methods only; no scientific algorithm execution",
        "command": ["perl", str(harness.relative_to(ROOT)), str(source.relative_to(ROOT)), str(processed.relative_to(ROOT)), str(sidecar.relative_to(ROOT))],
        "source_harness_sha256": hashlib.sha256(harness.read_bytes()).hexdigest(),
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "processed_sha256": hashlib.sha256(processed.read_bytes()).hexdigest(),
        "metadata_sha256": hashlib.sha256(sidecar.read_bytes()).hexdigest(),
        "exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr,
        "branches_checked": 9, "processed_equality": True, "sidecar_equality": True,
        "failed_feature_prefix_observation": "Perl retained prior capture badprefix as id; native invalid id retained, association excluded"})
    measured = sheet["queries"][0]["blast_sheet"]["hits"][0]["measurements"]
    summary = {"provenance": "SYNTHETIC native-shaped fixtures; no live service or BLAST execution",
        "query_count": len(sheet["queries"]), "hit_count_query_0": len(sheet["queries"][0]["blast_sheet"]["hits"]),
        "hsp_count_query_0": sum(len(hit["hsps"]) for hit in sheet["queries"][0]["normalized_result"]["hits"]),
        "overlap_example": measured,
        "temperature_2": scores2["queries"][0]["conditional_function_weights"]["unadjusted_probabilities"],
        "temperature_1": scores1["queries"][0]["conditional_function_weights"]["unadjusted_probabilities"],
        "unannotated_kernel_fraction_temperature_2": scores2["queries"][0]["conditional_function_weights"]["unannotated_reference_kernel_fraction"],
        "representation_adjustment": scores2["queries"][0]["conditional_function_weights"]["representation_adjusted_probabilities"],
        "source_transform_branches_checked": 9, "program_mode_cases": programs,
        "table_primary_secondary_zero_query": {"report_index": table_sheet["queries"][1]["report_index"],
            "status": table_sheet["queries"][1]["status"], "blast_sheet": table_sheet["queries"][1]["blast_sheet"],
            "reason": "homology_primary_query_unavailable; raw zero-hit report retained separately"},
        "live_resource_verified": False, "episode_communication_verified": False}
    save("CHECK_RESULTS.json", summary)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
