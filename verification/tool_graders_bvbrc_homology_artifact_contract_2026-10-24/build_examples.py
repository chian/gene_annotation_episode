"""SYNTHETIC source-shape illustrations; no production Homology parser or job.

Only existing BLAST pure readers/calculators run here. The small Perl program
extracts the retained producer's exact massage/decode methods and runs them on
the synthetic JSON. It does not load HomologySearch, run BLAST, or acquire data.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gene_annotation_episode.blast_grading_inputs import parse_blast_json, parse_blast_tabular
from gene_annotation_episode.blast_pairwise_grader import alignment_components, build_pairwise_sheet
from gene_annotation_episode.blast_database_grader import build_database_sheet, calculate_database_probabilities

PRODUCER = ROOT / "verification/tool_graders_bvbrc_application_artifacts_2026-10-24/sources/homology_service/lib/Bio/P3/HomologySearch/HomologySearch.pm"
FIELDS = "qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore qlen slen".split()


def save(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def hsp(num, bit_score, qfrom, qto, sfrom, sto, qseq, hseq):
    identical = sum(a == b and a != "-" for a, b in zip(qseq, hseq))
    return {"num": num, "bit_score": bit_score, "score": bit_score * 2,
            "evalue": 0.00001, "identity": identical, "positive": identical,
            "query_from": qfrom, "query_to": qto, "hit_from": sfrom, "hit_to": sto,
            "align_len": len(qseq), "gaps": qseq.count("-") + hseq.count("-"),
            "qseq": qseq, "hseq": hseq, "midline": "".join(a if a == b else " " for a, b in zip(qseq, hseq))}


def entry(query_id, title, qlen, hits, program="blastp", database="SYNTHETIC_DATABASE_PATH"):
    return {"report": {"program": program, "version": "BLASTP SYNTHETIC_FORMAT_EXAMPLE",
        "reference": "SYNTHETIC; no algorithm was executed",
        "search_target": {"db": database}, "params": {"expect": 0.00001},
        "results": {"search": {"query_id": query_id, "query_title": title,
        "query_len": qlen, "hits": hits}}}}


def expect_value_error(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except ValueError as error:
        return str(error)
    raise AssertionError("Expected the current reader to reject this representation")


def main():
    hits = [
        {"num": 1, "len": 8, "description": [{"id": "gnl|BL_ORD_ID|0", "accession": "0",
            "title": "fig|999999.1.peg.1|SYN_A|ALT_A   SYNTHETIC_FUNCTION_ALPHA   [SYNTHETIC_ORGANISM_A | 999999.1]"}],
         "hsps": [hsp(1, 20, 1, 4, 2, 5, "ACDE", "ACDE"),
                  hsp(2, 18, 3, 6, 4, 7, "DEFG", "DEFG"),
                  hsp(3, 20, 1, 4, 2, 5, "ACDE", "ACDE")]},
        {"num": 2, "len": 8, "description": [{"id": "gnl|BL_ORD_ID|1", "accession": "1",
            "title": "fig|999999.2.peg.1|SYN_B|ALT_B   SYNTHETIC_FUNCTION_BETA   [SYNTHETIC_ORGANISM_B | 999999.2]"}],
         "hsps": [hsp(1, 18, 1, 4, 1, 4, "ACDE", "ACDQ")]},
        {"num": 3, "len": 8, "description": [{"id": "gnl|BL_ORD_ID|2", "accession": "2",
            "title": "synthetic_reference_without_assignment"}],
         "hsps": [hsp(1, 16, 1, 4, 1, 4, "ACDE", "ACDQ")]},
    ]
    raw = {"BlastOutput2": [entry("Query_1", "synthetic_query_hit", 10, hits),
                            entry("Query_2", "synthetic_query_zero", 4, [])]}
    save("examples/synthetic_database/blast_out.raw.json", raw)
    raw_file = OUT / "examples/synthetic_database/blast_out.raw.json"

    # Extract exactly the two producer methods; JSON::PP supplies only the
    # JSON encode/decode object expected by those methods. No service imports.
    source = PRODUCER.read_text()
    methods = source[source.index("sub massage_blast_json\n"):source.index("sub find_db_in_path\n")]
    harness = """use strict;
use JSON::PP;
package SyntheticHomologyTransform;
sub json { return $_[0]->{json}; }
""" + methods + """
package main;
local $/;
open(my $in, '<', $ARGV[0]) or die $!;
my $text = <$in>;
my $codec = JSON::PP->new->pretty->canonical;
my $self = bless({json => $codec}, 'SyntheticHomologyTransform');
my ($processed, $metadata) = $self->massage_blast_json($text);
open(my $proc, '>', $ARGV[1]) or die $!;
print $proc $codec->encode($processed);
open(my $meta, '>', $ARGV[2]) or die $!;
print $meta $codec->encode($metadata);
"""
    (OUT / "source_transform_harness.pl").write_text(harness)
    proc_file = raw_file.with_name("blast_out.json")
    metadata_file = raw_file.with_name("blast_out.metadata.json")
    transform = subprocess.run(["perl", str(OUT / "source_transform_harness.pl"),
        str(raw_file), str(proc_file), str(metadata_file)], check=True, capture_output=True, text=True)
    processed = json.loads(proc_file.read_text())
    sidecar = json.loads(metadata_file.read_text())
    assert processed[0]["report"]["results"]["search"]["query_id"] == "synthetic_query_hit"
    assert processed[0]["report"]["results"]["search"]["hits"][0]["description"][0]["id"] == "fig|999999.1.peg.1"
    assert sidecar["fig|999999.1.peg.1"]["function"] == "SYNTHETIC_FUNCTION_ALPHA"

    # Explicitly author the header-declared table shape, including the source's
    # subject-prefix removal. This is not blast_formatter output or equivalence
    # verification of that program's identifier spelling.
    rows = []
    for hit in hits:
        for segment in hit["hsps"]:
            vals = ["synthetic_query_hit", hit["description"][0]["id"].removeprefix("gnl|"),
                    100 * segment["identity"] / segment["align_len"], segment["align_len"],
                    segment["align_len"] - segment["identity"], 0,
                    segment["query_from"], segment["query_to"], segment["hit_from"], segment["hit_to"],
                    segment["evalue"], segment["bit_score"], 10, hit["len"]]
            rows.append("\t".join(map(str, vals)))
    table = "\n".join(rows) + "\n"
    (raw_file.parent / "blast_headers.txt").write_text("\t".join(FIELDS) + "\n")
    (raw_file.parent / "blast_out.txt").write_text(table)
    (raw_file.parent / "input.faa").write_text(">synthetic_query_hit\nACDEFGHIKL\n>synthetic_query_zero\nWWWW\n")
    save("examples/synthetic_database/PROVENANCE.json", {
        "provenance_kind": "SYNTHETIC", "native_job_executed": False,
        "authoring": "Hand-authored outfmt15-shaped JSON and 14-column TSV; source methods transformed JSON locally.",
        "query_sequences": "Arbitrary fixtures, not a biological target.",
        "function_labels": "Literal synthetic annotations already supplied in synthetic metadata; no production inference.",
        "task_id": None, "workspace_object_ids": None, "archive_available": False,
        "algorithm_version": None, "database_release": None, "population_counts": None,
        "native_producer_version_claim": False,
    })

    direct_rejections = {
        "multiquery_raw": expect_value_error(parse_blast_json, raw_file.read_bytes(), mode="database", resource="api"),
        "processed_array": expect_value_error(parse_blast_json, proc_file.read_bytes(), mode="database", resource="api"),
    }
    request = {"program": "blastp", "query_length": 10, "max_target_seqs": 300}
    single = {"BlastOutput2": [deepcopy(raw["BlastOutput2"][0])]}
    normalized = parse_blast_json(json.dumps(single).encode(), mode="database", resource="api", request=request)
    # Explicit manual metadata bridge, only for this example's injective raw
    # preferred accession keys. This is not an implementation of the proposal.
    metadata, joins = [], []
    for hit_index in (0, 1):
        native_desc = hits[hit_index]["description"][0]
        changed_desc = processed[0]["report"]["results"]["search"]["hits"][hit_index]["description"][0]
        md = sidecar[changed_desc["id"]]
        joins.append({"report_index": 0, "hit_index": hit_index, "description_index": 0,
                      "raw_id": native_desc["id"], "raw_accession": native_desc["accession"],
                      "processed_id": changed_desc["id"], "metadata_key": changed_desc["id"]})
        metadata.append({"accession": native_desc["accession"], "source": "SYNTHETIC:bvbrc_metadata.function",
            "functions": [{"function": md["function"], "source": "SYNTHETIC:bvbrc_metadata.function", "evidence": []}],
            "taxid": None, "lineage": [], "origin": {"annotation_origin": "synthetic_title_derived_sidecar"},
            "assembly": {}, "sequence_group": None, "study_groups": [], "join_proof": joins[-1]})
    sheet = build_database_sheet(normalized, reference_metadata=metadata)
    scores = calculate_database_probabilities(sheet, model={"temperature_bits": 2})
    save("examples/synthetic_database/manual_metadata_bridge.json", joins)
    save("examples/synthetic_database/normalized_query_0.json", normalized)
    save("examples/synthetic_database/reference_metadata.json", metadata)
    save("examples/synthetic_database/sheet.json", sheet)
    save("examples/synthetic_database/scores_temperature_2.json", scores)
    assert sheet["hits"][0]["measurements"]["hsp_count"] == 3
    assert sheet["hits"][0]["measurements"]["observed_paired_query_positions"] == 6
    assert sheet["hits"][0]["measurements"]["query_paired_coverage"] == 0.6
    assert sheet["hits"][0]["measurements"]["reference_paired_coverage"] == 0.75
    assert sheet["hits"][0]["measurements"]["overlap_pair_representations"] == 6
    assert scores["unadjusted_probabilities"] == {"SYNTHETIC_FUNCTION_ALPHA": 2/3, "SYNTHETIC_FUNCTION_BETA": 1/3}
    assert scores["representation_adjusted_probabilities"] is None
    assert scores["unannotated_reference_kernel_fraction"] == 1/7
    saved = json.loads((raw_file.parent / "sheet.json").read_text())
    alternate = calculate_database_probabilities(saved, model={"temperature_bits": 1})
    assert alternate["unadjusted_probabilities"] == {"SYNTHETIC_FUNCTION_ALPHA": 0.8, "SYNTHETIC_FUNCTION_BETA": 0.2}
    save("examples/synthetic_database/recalculated_scores_temperature_1.json", alternate)

    zero = {"BlastOutput2": [deepcopy(raw["BlastOutput2"][1])]}
    zero_norm = parse_blast_json(json.dumps(zero).encode(), mode="database", resource="api")
    zero_sheet = build_database_sheet(zero_norm)
    zero_scores = calculate_database_probabilities(zero_sheet)
    save("examples/synthetic_database/zero_query_sheet.json", zero_sheet)
    assert zero_norm["search"]["hit_array_present"] is True
    assert zero_sheet["coverage"]["native_hit_count"] == 0
    assert zero_scores["unadjusted_probabilities"] is None

    table_norm = parse_blast_tabular(table.encode(), mode="database", resource="api", fields=FIELDS, request=request)
    table_sheet = build_database_sheet(table_norm)
    save("examples/synthetic_database/table_only_sheet.json", table_sheet)
    assert table_sheet["hits"][1]["hsp_components"][0]["fractions"]["alignment_identity"] == 0.75
    assert table_sheet["hits"][0]["measurements"]["query_paired_coverage"] is None
    assert table_sheet["hits"][0]["hsp_components"][0]["counts"]["identical_pairs"] is None
    assert len(table_sheet["normalized_result"]["native"]["rows"]) == 5

    empty_table = parse_blast_tabular(b"", mode="database", resource="api", fields=FIELDS, request=request)
    assert empty_table["search"]["hit_array_present"] is False
    missing = deepcopy(zero)
    del missing["BlastOutput2"][0]["report"]["results"]["search"]["hits"]
    missing_norm = parse_blast_json(json.dumps(missing).encode(), mode="database", resource="api")
    assert missing_norm["search"]["hit_array_present"] is False
    save("examples/missing_hits.raw.json", missing)

    partial = deepcopy(single)
    partial["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][1]["query_to"] = 99
    partial["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][1]["evalue"] = -1
    partial_norm = parse_blast_json(json.dumps(partial).encode(), mode="database", resource="api")
    partial_sheet = build_database_sheet(partial_norm)
    save("examples/partial.raw.json", partial)
    save("examples/partial_sheet.json", partial_sheet)
    assert len(partial_norm["hits"][0]["hsps"]) == 3
    assert partial_sheet["hits"][0]["measurements"]["observed_paired_query_positions"] == 4
    assert partial_sheet["hits"][0]["measurements"]["query_paired_coverage"] is None

    # Separate explicit one-query / one-subject fixture, not best-hit selection.
    paired = {"BlastOutput2": [entry("Query_1", "synthetic_pair_query", 10, [deepcopy(hits[0])], database="SYNTHETIC_SINGLE_SUBJECT_DATABASE")]}
    save("examples/synthetic_pairwise/blast_out.raw.json", paired)
    (OUT / "examples/synthetic_pairwise/subject.faa").write_text(">synthetic_pair_subject\nXACDEFGY\n")
    save("examples/synthetic_pairwise/mode_binding.json", {"provenance_kind": "SYNTHETIC",
        "scientific_mode": "pairwise_correspondence", "execution_mode": "database_backed_blast",
        "query_member_count": 1, "subject_member_count": 1,
        "subject_length": 8, "database_exhaustiveness_evidence": "The author-supplied fixture contains only this one subject; no runtime database is claimed."})
    direct_rejections["database_backed_pairwise"] = expect_value_error(parse_blast_json,
        json.dumps(paired).encode(), mode="pairwise", resource="api")
    pair_norm = parse_blast_json(json.dumps(paired).encode(), mode="database", resource="api")
    pair_norm["mode"] = "pairwise"  # Explicit fixture-only scientific-mode projection.
    pair_sheet = build_pairwise_sheet(pair_norm)
    save("examples/synthetic_pairwise/sheet.json", pair_sheet)
    assert pair_sheet["union"]["counts"]["distinct_residue_pairs"] == 6
    assert pair_sheet["union"]["identical_mapping_hsp_groups"] == [[0, 2]]
    assert pair_sheet["union"]["fractions"]["paired_identity"] == 1.0

    translated = hsp(1, 12, 15, 7, 2, 4, "ACD", "ACD")
    translated["query_frame"] = -1
    translated_components = alignment_components(translated, program="blastx", query_length=15, reference_length=5)
    assert translated_components["counts"]["paired_query_positions"] == 9
    assert translated_components["fractions"]["query_paired_coverage"] == 0.6
    assert translated_components["pairs"][0]["query_start"] == 12
    assert translated_components["pairs"][-1]["query_start"] == 6
    save("examples/translated_reverse_hsp.json", {"provenance_kind": "SYNTHETIC",
        "program": "blastx", "query_length": 15, "reference_length": 5,
        "native_shaped_hsp": translated, "components": translated_components})

    # Demonstrate a real lossy source transformation on synthetic descriptions:
    # two description IDs rewrite to the same key; metadata last-write wins.
    collision = deepcopy(single)
    descriptions = collision["BlastOutput2"][0]["report"]["results"]["search"]["hits"]
    descriptions[1]["description"][0]["title"] = "fig|999999.1.peg.1|SYN_B|ALT_B   SYNTHETIC_FUNCTION_BETA   [SYNTHETIC_ORGANISM_B | 999999.2]"
    save("examples/synthetic_collision/blast_out.raw.json", collision)
    collision_dir = OUT / "examples/synthetic_collision"
    subprocess.run(["perl", str(OUT / "source_transform_harness.pl"),
        str(collision_dir / "blast_out.raw.json"), str(collision_dir / "blast_out.json"),
        str(collision_dir / "blast_out.metadata.json")], check=True, capture_output=True, text=True)
    collision_meta = json.loads((collision_dir / "blast_out.metadata.json").read_text())
    assert collision_meta["fig|999999.1.peg.1"]["function"] == "SYNTHETIC_FUNCTION_BETA"
    assert len(collision_meta) == 1

    save("CHECK_RESULTS.json", {
        "verification_kind": "SYNTHETIC source-transformation and existing-BLAST-function checks",
        "native_bvbrc_job_executed": False, "native_bvbrc_job_artifacts_tested": False,
        "proposed_bvbrc_parsers_tested": False, "production_integration_tested": False,
        "existing_shared_functions_checked": ["parse_blast_json", "parse_blast_tabular", "alignment_components", "build_pairwise_sheet", "build_database_sheet", "calculate_database_probabilities"],
        "native_shaped_report_count": 2, "hit_count_query_0": 3, "hsp_count_query_0": 5,
        "query_0_hit_0": sheet["hits"][0]["measurements"],
        "temperature_2_function_weights": scores["unadjusted_probabilities"],
        "temperature_1_function_weights": alternate["unadjusted_probabilities"],
        "representation_adjustment": None,
        "source_transform_sha256": hashlib.sha256(methods.encode()).hexdigest(),
        "source_transform_stdout": transform.stdout,
        "current_reader_rejections": direct_rejections,
        "checks": ["source query/description transformations", "multiple queries retained in original",
            "all three hits and five HSPs retained", "overlap and duplicate mapping union",
            "literal synthetic metadata assignments joined via unique native accessions",
            "explicit zero-hit query", "missing hits remain unknown", "empty table remains unknown",
            "table identity percentage available but paired coverage and exact identity count unavailable",
            "valid partial components survive malformed independent HSP fields",
            "pairwise calculator shares exact union mathematics", "reverse translated coordinates cover nine original nt",
            "offline saved-sheet temperature recalculation", "missing database population prevents correction",
            "source metadata collision demonstrably loses earlier description metadata"],
        "all_listed_checks_passed": True,
    })
    print(json.dumps({"status": "passed", "checks": 15,
        "source_transform": "exact retained methods on synthetic data",
        "shared_BLAST_functions": 6, "production_code_changed": False,
        "native_jobs": 0, "function_weights_T2": scores["unadjusted_probabilities"]}))


if __name__ == "__main__":
    main()
