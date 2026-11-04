"""Inspectable synthetic numerical examples for the pure Homology adapters."""
from copy import deepcopy
import hashlib
import json
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_homology_metadata import read_homology_metadata, bind_homology_metadata
from gene_annotation_episode.bvbrc_homology_grader import (
    build_homology_sheet, calculate_homology_alignment_supplements, calculate_homology_scores,
)
from test_bvbrc_homology_inputs import (
    FIXTURES, artifact, bundle, encoded, parse_all, parse_raw, query_binding, raw_document, replace_content,
    read_homology_processed_json, read_homology_tabular,
)
from gene_annotation_episode.bvbrc_homology_inputs import FIELDS, _expected_processed


F, G = "SYNTHETIC_FUNCTION_ALPHA", "SYNTHETIC_FUNCTION_BETA"


def supplied():
    return {"schema": "bvbrc_homology_metadata_bindings_v1", "description_links": [], "records": [],
        "bindings": [], "sequence_identity_bindings": [], "target_context_by_query": [], "database_profile": None}


def metadata_and_sheet(parsed, artifacts, contents, extra=None):
    links = [link for query in parsed["queries"] for link in query["description_links"]]
    native = read_homology_metadata(contents["homology_metadata_json"], artifact=artifacts["homology_metadata_json"],
        description_links=links) if "homology_metadata_json" in contents else None
    metadata = bind_homology_metadata(parsed, native_metadata=native, supplied_metadata=extra if extra is not None else supplied())
    return metadata, build_homology_sheet(parsed, metadata=metadata)


def example():
    binding, artifacts, contents = bundle()
    parsed = parse_all(binding, artifacts, contents)
    metadata, sheet = metadata_and_sheet(parsed, artifacts, contents)
    return binding, artifacts, contents, parsed, metadata, sheet


def program_document(program):
    query_translated = program in {"blastx", "tblastx"}
    reference_translated = program in {"tblastn", "tblastx"}
    symbols = "ACT" if program == "blastn" else "MKT"
    hsp = {"bit_score": 20, "score": 40, "evalue": 0.0, "align_len": 3, "identity": 3, "gaps": 0,
        "qseq": symbols, "hseq": symbols, "query_from": 1, "query_to": 9 if query_translated else 3,
        "hit_from": 1, "hit_to": 9 if reference_translated else 3}
    if query_translated:
        hsp["query_frame"] = 1
    if reference_translated:
        hsp["hit_frame"] = 1
    report = {"report": {"program": program, "version": "SYNTHETIC", "search_target": {"db": "SYNTHETIC_DATABASE_PATH"},
        "params": {}, "results": {"search": {"query_id": "Query_1", "query_title": "SYNTHETIC-query",
            "query_len": 15 if query_translated else 5, "hits": [{"len": 15 if reference_translated else 5,
                "description": [{"id": "SYNTHETIC-subject", "title": "SYNTHETIC unassigned reference"}], "hsps": [hsp]}]}}}}
    return {"BlastOutput2": [report]}


def add_subject(binding, doc):
    program = doc["BlastOutput2"][0]["report"]["program"]
    length = doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["len"]
    binding["subject_binding"] = {"source_ref": "SYNTHETIC-supplied-reference", "member_ref": "SYNTHETIC-member-reference",
        "subject_ref": "SYNTHETIC-reference-subject", "sequence_sha256": hashlib.sha256(("A" * length).encode()).hexdigest(),
        "length": length, "molecule": "aa" if program in {"blastp", "blastx"} else "nt",
        "database_membership": {"source_ref": "SYNTHETIC-database-inventory", "pointer": "/members", "member_count": 1},
        "native_hit_links": [{"report_index": 0, "hit_index": 0, "description_index": 0}]}


def source_record(index, function="FUNCTION", taxid=None):
    return {"record_index": index, "source_ref": "SYNTHETIC-explicit-records", "pointer": f"/features/{index}",
        "source_identifier": {"namespace": "patric_id", "value": f"fig|999999.{index}.peg.1"}, "aliases": [],
        "function_assignments": [{"function": function, "assignment_scope": "subject_sequence",
            "source_ref": "SYNTHETIC-explicit-records", "pointer": f"/features/{index}/function", "evidence": []}],
        "genome_id": "999999.1", "taxid": taxid, "lineage": [], "origin": {}, "assembly_measurements": {},
        "full_sequence_identity": None, "study_groups": []}


def metadata_link(index, hit_index=0, description_index=0):
    return {"report_index": 0, "hit_index": hit_index, "description_index": description_index, "record_index": index,
        "linkage_source_ref": "SYNTHETIC-explicit-links", "linkage_pointer": f"/links/{index}"}


def full_sequence_link(hit_index, *, sequence="ACDEFGHI"):
    digest = hashlib.sha256(sequence.encode()).hexdigest()
    return {"report_index": 0, "hit_index": hit_index, "kind": "full_sequence_digest", "algorithm": "sha256",
        "digest": digest, "sequence_group": "sha256:" + digest, "molecule": "aa", "sequence_length": len(sequence),
        "source_ref": "SYNTHETIC-full-sequences", "pointer": f"/sequences/{hit_index}",
        "linkage_source_ref": "SYNTHETIC-sequence-links", "linkage_pointer": f"/links/{hit_index}"}


def test_proposal_numerical_example_all_components_and_explicit_real_ids():
    _, _, _, parsed, metadata, sheet = example()
    assert len(sheet["queries"]) == 2
    db = sheet["queries"][0]["blast_sheet"]
    hit = db["hits"][0]
    measured = hit["measurements"]
    assert measured["observed_paired_query_positions"] == 6
    assert measured["observed_paired_reference_positions"] == 6
    assert measured["query_paired_coverage"] == .6
    assert measured["reference_paired_coverage"] == .75
    assert measured["hsp_count"] == 3 and measured["unique_pair_count"] == 6
    assert measured["overlap_pair_representations"] == 6
    assert hit["associations"][0]["native_identifier"] == "0"
    assert hit["associations"][0]["accession"] == "fig|999999.1.peg.1"
    assert hit["associations"][0]["taxid"] is None  # genome 999999.1 is not NCBI taxid 999999
    assert db["coverage"]["groups_with_explicit_function"] == 2
    assert db["coverage"]["groups_without_explicit_function"] == 1
    assert db["search_limits"]["limit_reached"] is True
    scored = calculate_homology_scores(sheet, database_model={"temperature_bits": 2})
    kernel = scored["queries"][0]["conditional_function_weights"]
    assert kernel["function_masses"] == {F: 1, G: .5}
    assert kernel["unadjusted_probabilities"] == {F: 2 / 3, G: 1 / 3}
    assert kernel["unannotated_reference_kernel_fraction"] == 1 / 7
    assert kernel["representation_adjusted_probabilities"] is None
    assert "source_quality" in kernel["retained_measurements_not_used_by_this_model"]
    assert db["source_quality"]["numerical_summaries"] == []
    zero = sheet["queries"][1]["blast_sheet"]
    assert zero["search_limits"]["reported_hit_count"] == 0
    assert scored["queries"][1]["conditional_function_weights"]["unadjusted_probabilities"] is None
    assert metadata["queries"][0]["sequence_identity_bindings"] == []


def test_saved_sheet_recalculation_has_no_reader_network_subprocess_or_mutation(tmp_path, monkeypatch):
    *_, sheet = example()
    path = tmp_path / "SYNTHETIC-sheet.json"
    path.write_text(json.dumps(sheet, allow_nan=False))
    saved = path.read_bytes()
    reopened = json.loads(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError("Saved-sheet recalculation must use supplied data only")
    for name in ("read_homology_raw_json", "read_homology_processed_json", "read_homology_tabular"):
        monkeypatch.setattr("gene_annotation_episode.bvbrc_homology_inputs." + name, forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr("gene_annotation_episode.bvbrc_homology_grader.build_homology_sheet", forbidden)
    t2 = calculate_homology_scores(reopened, database_model={"temperature_bits": 2})
    t1 = calculate_homology_scores(reopened, database_model={"temperature_bits": 1})
    priors = calculate_homology_scores(reopened, database_model={"temperature_bits": 2, "function_priors": {F: 1, G: 2}})
    assert t2["queries"][0]["conditional_function_weights"]["unadjusted_probabilities"] == {F: 2 / 3, G: 1 / 3}
    assert t1["queries"][0]["conditional_function_weights"]["unadjusted_probabilities"] == {F: .8, G: .2}
    assert priors["queries"][0]["conditional_function_weights"]["unadjusted_probabilities"] == {F: .5, G: .5}
    assert reopened == sheet and path.read_bytes() == saved


@pytest.mark.parametrize("program", ["blastp", "blastn", "blastx", "tblastn", "tblastx"])
@pytest.mark.parametrize("mode", ["database_identification", "pairwise_correspondence"])
def test_all_five_programs_and_both_scientific_modes_reuse_shared_geometry(program, mode):
    doc = program_document(program)
    binding, artifacts, contents = bundle(doc, mode=mode, extras=False)
    if mode == "pairwise_correspondence":
        add_subject(binding, doc)
    parsed = parse_raw(binding, artifacts, contents)
    _, sheet = metadata_and_sheet(parsed, artifacts, contents)
    db = sheet["queries"][0]["blast_sheet"]
    if mode == "pairwise_correspondence":
        assert db["schema"] == "blast_pairwise_sheet_v1"
        measured = db["union"]["fractions"]
        assert db["input"]["search"]["database"] == "SYNTHETIC_DATABASE_PATH"
        assert db["input"]["native"]["document"]["BlastOutput2"][0]["report"]["search_target"]["db"] == "SYNTHETIC_DATABASE_PATH"
    else:
        measured = db["hits"][0]["measurements"]
    assert measured["query_paired_coverage"] == .6
    assert measured["reference_paired_coverage"] == .6
    supplements = calculate_homology_alignment_supplements(sheet)
    component = supplements["queries"][0]["hits"][0]["hsps"][0]["alignment_components"]
    assert component["counts"]["paired_columns"] == 3
    assert len(component["pairs"]) == 3
    assert component["counts"]["paired_query_positions"] == (9 if program in {"blastx", "tblastx"} else 3)
    assert component["counts"]["paired_reference_positions"] == (9 if program in {"tblastn", "tblastx"} else 3)
    scores = calculate_homology_scores(sheet)
    assert (scores["queries"][0]["conditional_function_weights"] is None) == (mode == "pairwise_correspondence")


def test_reverse_translated_geometry_and_span_original_nt_denominator():
    doc = program_document("blastx")
    hsp = doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][0]
    hsp.update(query_from=15, query_to=7, query_frame=-1, hit_from=2, hit_to=4)
    binding, artifacts, contents = bundle(doc, extras=False)
    _, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents)
    component = sheet["queries"][0]["blast_sheet"]["hits"][0]["hsp_components"][0]
    assert [[pair["query_start"], pair["query_end"]] for pair in component["pairs"]] == [[12, 15], [9, 12], [6, 9]]
    assert component["counts"]["paired_query_positions"] == 9
    assert component["fractions"]["query_paired_coverage"] == .6
    supplement = calculate_homology_alignment_supplements(sheet)["queries"][0]["hits"][0]
    assert supplement["hsps"][0]["spans"]["query"]["interval"] == [6, 15]
    assert supplement["span_union"]["query"]["coverage"]["value"] == .6


@pytest.mark.parametrize("changes,issue", [({"query_frame": 2}, "frame_coordinate_phase_conflict"),
    # Native BLAST+ 2.17.0 JSON15 permits ascending negative-frame bounds.
    # Preserve the direction-conflict case with positive-frame reverse bounds;
    # the original failing expectation is retained in geometry295/checks_001.
    ({"query_from": 9, "query_to": 1, "query_frame": 1}, "frame_coordinate_direction_conflict"),
    ({"query_to": 30}, "traceback_coordinate_span_conflict"),
    ({"query_strand": "Minus"}, "strand_coordinate_conflict")])
def test_bad_translation_geometry_keeps_native_scores_and_valid_counts(changes, issue):
    doc = program_document("blastx")
    doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][0].update(changes)
    binding, artifacts, contents = bundle(doc, extras=False)
    _, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents)
    component = sheet["queries"][0]["blast_sheet"]["hits"][0]["hsp_components"][0]
    assert component["counts"]["identical_pairs"] == 3
    assert component["native_scores"]["bit_score"] == 20
    assert component["geometry_available"] is False
    assert issue in {row["code"] for row in component["issues"]}


def test_pairwise_overlap_requires_actual_subject_proof_and_rejects_model_kernel():
    doc = raw_document()
    doc["BlastOutput2"] = doc["BlastOutput2"][:1]
    doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"] = doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"][:1]
    binding, artifacts, contents = bundle(doc, mode="pairwise_correspondence", extras=False)
    parsed = parse_raw(binding, artifacts, contents)
    _, missing = metadata_and_sheet(parsed, artifacts, contents)
    assert missing["queries"][0]["blast_sheet"] is None
    assert missing["queries"][0]["normalized_result"]["hits"][0]["hsps"][0]["bit_score"] == 20
    assert missing["queries"][0]["status"] == "unavailable"
    add_subject(binding, doc)
    _, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents)
    union = sheet["queries"][0]["blast_sheet"]["union"]
    assert union["counts"]["distinct_residue_pairs"] == 6
    assert union["identical_mapping_hsp_groups"] == [[0, 2]]
    assert union["fractions"]["paired_identity"] == 1
    with pytest.raises(ValueError, match="homology_database_model_unused_for_pairwise"):
        calculate_homology_scores(sheet, database_model={"temperature_bits": 2})
    binding["subject_binding"]["database_membership"]["member_count"] = 2
    _, wrong = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents)
    assert wrong["queries"][0]["blast_sheet"] is None


def test_table_only_counts_span_coverage_and_no_exact_identity_or_correspondence():
    binding, artifacts, contents = bundle(primary="tabular")
    parsed = read_homology_tabular(contents["blast_tabular"], header_content=contents["blast_tabular_header"],
        artifact=artifacts["blast_tabular"], header_artifact=artifacts["blast_tabular_header"], binding=binding)
    metadata = bind_homology_metadata(parsed, native_metadata=None, supplied_metadata=supplied())
    sheet = build_homology_sheet(parsed, metadata=metadata)
    db = sheet["queries"][0]["blast_sheet"]
    component = db["hits"][1]["hsp_components"][0]
    assert component["fractions"]["alignment_identity"] == .75
    assert component["counts"]["identical_pairs"] is None and component["counts"]["paired_columns"] is None
    assert component["fractions"]["query_paired_coverage"] is None
    supplement = calculate_homology_alignment_supplements(sheet)["queries"][0]
    assert supplement["native_tabular_measurements"][3]["mismatch"] == 1
    assert supplement["native_tabular_measurements"][3]["gapopen"] == 0
    assert supplement["hits"][1]["hsps"][0]["substitution_columns"]["value"] is None
    assert supplement["hits"][0]["span_union"]["query"]["coverage"]["value"] == .6
    assert supplement["hits"][0]["span_union"]["reference"]["coverage"]["value"] == .75


def test_gapped_traceback_substitutions_gap_runs_and_span_are_separate():
    doc = program_document("blastp")
    query = doc["BlastOutput2"][0]["report"]["results"]["search"]
    query["query_len"] = 10
    hit = query["hits"][0]
    hit["len"] = 10
    hit["hsps"][0].update(qseq="AC--DEFG", hseq="ACGH-EQG", query_from=1, query_to=6, hit_from=1, hit_to=7,
                          align_len=8, identity=3, gaps=3)
    binding, artifacts, contents = bundle(doc, extras=False)
    _, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents)
    supplement = calculate_homology_alignment_supplements(sheet)["queries"][0]["hits"][0]["hsps"][0]
    assert supplement["query_gap_runs"]["value"] == 1
    assert supplement["reference_gap_runs"]["value"] == 1
    assert supplement["alignment_components"]["counts"]["query_gap_columns"] == 2
    assert supplement["substitution_columns"]["value"] == 1
    assert supplement["alignment_components"]["reported_counts"]["identity"] == 3
    assert supplement["alignment_components"]["counts"]["identical_pairs"] == 4
    assert supplement["spans"]["query"]["coverage"]["value"] == .6
    assert supplement["alignment_components"]["fractions"]["query_paired_coverage"] == .5


def test_malformed_and_partial_hsps_preserve_valid_observed_coverage_without_complete_fraction():
    doc = raw_document()
    hsps = doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"]
    hsps[1]["hseq"] = "BROKEN"
    hsps.append(None)
    binding, artifacts, contents = bundle(doc)
    _, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents)
    measured = sheet["queries"][0]["blast_sheet"]["hits"][0]["measurements"]
    assert measured["hsp_count"] == 4
    assert measured["observed_paired_query_positions"] == 4
    assert measured["query_paired_coverage"] is None
    assert measured["maximum_bit_score"] == 20


def test_overwritten_sidecar_never_assigns_last_record_to_all_descriptions():
    doc = raw_document("synthetic_collision")
    binding, artifacts, contents = bundle(doc, extras=False)
    replace_content(binding, artifacts, contents, "homology_metadata_json",
                    (FIXTURES / "synthetic_collision/blast_out.metadata.json").read_bytes())
    parsed = parse_raw(binding, artifacts, contents)
    metadata, sheet = metadata_and_sheet(parsed, artifacts, contents)
    db = sheet["queries"][0]["blast_sheet"]
    assert db["functions"] == []
    assert len(db["hits"]) == 3
    assert db["hits"][0]["measurements"]["query_paired_coverage"] == .6
    assert metadata["native_metadata"]["records"][0]["function_assignments"][0]["function"] == G
    assert metadata["native_metadata"]["bindings"] == []


def test_raw_sidecar_conflict_and_wrong_native_scalar_cannot_authorize_assignment():
    binding, artifacts, contents = bundle()
    sidecar = json.loads(contents["homology_metadata_json"])
    sidecar["fig|999999.1.peg.1"]["function"] = "SYNTHETIC_WRONG"
    replace_content(binding, artifacts, contents, "homology_metadata_json", encoded(sidecar))
    _, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents)
    assert [row["function"] for row in sheet["queries"][0]["blast_sheet"]["functions"]] == [G]
    doc = raw_document()
    doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["description"][0]["taxid"] = "invalid"
    binding, artifacts, contents = bundle(doc, extras=False)
    extra = supplied()
    extra["records"] = [source_record(7)]
    extra["bindings"] = [metadata_link(7)]
    _, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents, extra)
    db = sheet["queries"][0]["blast_sheet"]
    assert db["functions"] == []
    assert db["normalized_result"]["hits"][0]["descriptions"][0]["taxid"] == "invalid"
    assert "blast_description_binding_native_identity_invalid" in {item["code"] for item in db["issues"]}


def test_external_explicit_records_survive_native_overwrite_and_wrong_indices_are_local():
    doc = raw_document("synthetic_collision")
    binding, artifacts, contents = bundle(doc, extras=False)
    extra = supplied()
    extra["records"] = [source_record(8, "EXACT_A"), source_record(3, "EXACT_B")]
    extra["bindings"] = [metadata_link(8), metadata_link(3, hit_index=1), metadata_link(99, hit_index=2)]
    metadata, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents, extra)
    db = sheet["queries"][0]["blast_sheet"]
    assert {row["function"] for row in db["functions"]} == {"EXACT_A", "EXACT_B"}
    assert db["description_bindings"][0]["metadata_index"] == 0
    assert db["reference_metadata"][0]["native_metadata_record"]["record_index"] == 8
    assert metadata["unresolved_metadata"][0]["binding"]["record_index"] == 99


def test_interval_scoped_or_whole_contig_title_assignments_remain_unused():
    binding, artifacts, contents = bundle()
    binding["database_binding"]["requested_selection"]["db_type"] = "fna"
    extra = supplied()
    row = source_record(0)
    row["function_assignments"][0]["assignment_scope"] = "reference_interval"
    extra["records"] = [row]
    extra["bindings"] = [metadata_link(0)]
    metadata, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents, extra)
    assert sheet["queries"][0]["blast_sheet"]["functions"] == []
    assert all(record["excluded_function_assignments"] for record in metadata["queries"][0]["reference_metadata"])


def test_taxon_conflicts_and_target_context_do_not_cross_associations():
    doc = raw_document()
    doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["description"][0]["taxid"] = 562
    binding, artifacts, contents = bundle(doc, extras=False)
    extra = supplied()
    extra["records"] = [source_record(0, taxid=620), source_record(1, "OTHER", taxid=562)]
    extra["records"][1]["lineage"] = [{"rank": "species", "taxid": 562}]
    extra["bindings"] = [metadata_link(0), metadata_link(1, hit_index=1)]
    extra["target_context_by_query"] = [{"report_index": 0, "taxid": 562,
        "lineage": [{"rank": "species", "taxid": 562}], "source": "SYNTHETIC-independent-target", "independent_of_search": True}]
    _, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents, extra)
    db = sheet["queries"][0]["blast_sheet"]
    assert [row["function"] for row in db["functions"]] == ["OTHER"]
    assert "metadata_taxon_conflicts_with_native" in {item["code"] for item in db["issues"]}
    assert db["taxonomy"]["ranks"][0]["target_matching_fraction"] == 1
    assert db["taxonomy"]["ranks"][0]["unknown_group_count"] == 2


def test_full_sequence_grouping_uses_exact_h1_operands_and_no_label_fallback():
    binding, artifacts, contents = bundle()
    extra = supplied()
    extra["sequence_identity_bindings"] = [full_sequence_link(0), full_sequence_link(1)]
    metadata, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents, extra)
    assert metadata["queries"][0]["sequence_identity_bindings"] == extra["sequence_identity_bindings"]
    db = sheet["queries"][0]["blast_sheet"]
    assert len(db["sequence_groups"]) == 2 and db["dependence"]["duplicate_native_hit_count"] == 1
    scores = calculate_homology_scores(sheet)
    assert scores["queries"][0]["conditional_function_weights"]["unadjusted_probabilities"] == {F: .5, G: .5}
    extra["sequence_identity_bindings"][1]["sequence_length"] = 99
    _, damaged = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents, extra)
    assert len(damaged["queries"][0]["blast_sheet"]["sequence_groups"]) == 3
    assert "blast_sequence_binding_reference_length_mismatch" in {item["code"] for item in damaged["queries"][0]["blast_sheet"]["issues"]}


def test_population_adjustment_requires_actual_matching_explicit_profile():
    binding, artifacts, contents = bundle()
    extra = supplied()
    extra["database_profile"] = {"database": "SYNTHETIC_DATABASE_PATH", "release": None,
        "count_unit": "unique_sequences", "scope": "searched_database", "source": "SYNTHETIC-independent-profile",
        "total_count": 100, "function_counts": {F: 80, G: 20}}
    _, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents, extra)
    scores = calculate_homology_scores(sheet, database_model={"temperature_bits": 2})
    kernel = scores["queries"][0]["conditional_function_weights"]
    assert kernel["representation_adjusted_probabilities"] == {F: 1 / 3, G: 2 / 3}
    # These are supplied SYNTHETIC population operands, never inferred from db_num or hits.
    extra["database_profile"]["count_unit"] = "genomes"
    _, mismatch = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents, extra)
    assert calculate_homology_scores(mismatch)["queries"][0]["conditional_function_weights"]["representation_adjusted_probabilities"] is None


def test_quality_measurement_units_methods_and_feature_genome_links_are_required():
    binding, artifacts, contents = bundle(extras=False)
    extra = supplied()
    record = source_record(0)
    record["assembly_measurements"] = {"completeness_fraction": .95, "contamination_fraction": .03, "contig_count": 2,
        "source": "SYNTHETIC-quality", "measurement_units": {"completeness_fraction": "fraction", "contamination_fraction": "fraction", "contig_count": "count"},
        "measurement_methods": {"completeness_fraction": "SYNTHETIC-marker-method", "contamination_fraction": "SYNTHETIC-marker-method", "contig_count": "SYNTHETIC-count"},
        "feature_to_genome_link": {"source_ref": "SYNTHETIC-feature-record", "pointer": "/features/0/genome_id",
            "genome_id": "999999.1", "feature_identifier": record["source_identifier"]}}
    extra["records"] = [record]
    extra["bindings"] = [metadata_link(0)]
    _, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents, extra)
    measurements = sheet["queries"][0]["blast_sheet"]["source_quality"]["numerical_summaries"]
    assert {row["field"]: row["mean"] for row in measurements} == {"completeness_fraction": .95, "contamination_fraction": .03, "contig_count": 2}
    record["assembly_measurements"]["measurement_units"]["completeness_fraction"] = "percent"
    _, invalid = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents, extra)
    summaries = invalid["queries"][0]["blast_sheet"]["source_quality"]["numerical_summaries"]
    assert "completeness_fraction" not in {row["field"] for row in summaries}
    assert record["assembly_measurements"]["completeness_fraction"] == .95


def test_processed_only_metadata_preserves_unknown_raw_title_and_native_associations():
    binding, artifacts, contents = bundle(primary="processed")
    entries = json.loads(contents["homology_processed_json"])
    binding["query_bindings"] = [query_binding(entry, i) for i, entry in enumerate(entries)]
    parsed = read_homology_processed_json(contents["homology_processed_json"], artifact=artifacts["homology_processed_json"], binding=binding)
    metadata, sheet = metadata_and_sheet(parsed, artifacts, contents)
    assert {row["function"] for row in sheet["queries"][0]["blast_sheet"]["functions"]} == {F, G}
    assert all(row["origin"]["original_title"] is None for row in metadata["native_metadata"]["records"])


def test_malformed_metadata_document_never_discards_native_geometry():
    binding, artifacts, contents = bundle()
    replace_content(binding, artifacts, contents, "homology_metadata_json", b'{"bad":1,"bad":2}')
    metadata, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents)
    assert metadata["native_metadata"]["status"] == "invalid"
    assert sheet["queries"][0]["blast_sheet"]["functions"] == []
    assert sheet["queries"][0]["blast_sheet"]["hits"][0]["measurements"]["query_paired_coverage"] == .6


@pytest.mark.parametrize("program", ["blastp", "blastn", "blastx", "tblastn", "tblastx"])
@pytest.mark.parametrize("mode", ["database_identification", "pairwise_correspondence"])
@pytest.mark.parametrize("representation", ["processed", "tabular"])
def test_other_representations_cover_five_programs_and_two_modes(program, mode, representation):
    doc = program_document(program)
    binding, artifacts, contents = bundle(doc, mode=mode, primary=representation, extras=False)
    if mode == "pairwise_correspondence":
        add_subject(binding, doc)
    if representation == "processed":
        entries = [_expected_processed(entry) for entry in doc["BlastOutput2"]]
        replace_content(binding, artifacts, contents, "homology_processed_json", encoded(entries))
        binding["query_bindings"] = [query_binding(entries[0], 0)]
        parsed = read_homology_processed_json(contents["homology_processed_json"], artifact=artifacts["homology_processed_json"], binding=binding)
    else:
        search = doc["BlastOutput2"][0]["report"]["results"]["search"]
        hit, = search["hits"]
        hsp, = hit["hsps"]
        fields = ["Query_1", "SYNTHETIC-subject", "100.0", "3", "0", "0", "1", str(hsp["query_to"]),
                  "1", str(hsp["hit_to"]), "0.0", "20", str(search["query_len"]), str(hit["len"])]
        replace_content(binding, artifacts, contents, "blast_tabular", ("\t".join(fields) + "\n").encode())
        replace_content(binding, artifacts, contents, "blast_tabular_header", ("\t".join(FIELDS) + "\n").encode())
        binding["query_bindings"][0]["native_query"]["query_title"] = None
        parsed = read_homology_tabular(contents["blast_tabular"], header_content=contents["blast_tabular_header"],
            artifact=artifacts["blast_tabular"], header_artifact=artifacts["blast_tabular_header"], binding=binding)
    _, sheet = metadata_and_sheet(parsed, artifacts, contents)
    assert sheet["queries"][0]["query_binding_status"] == "validated"
    assert sheet["queries"][0]["blast_sheet"] is not None
    scores = calculate_homology_scores(sheet)
    assert (scores["queries"][0]["pairwise_correspondence"] is not None) == (mode == "pairwise_correspondence")
    supplement = scores["alignment_supplements"]["queries"][0]["hits"][0]
    assert supplement["span_union"]["query"]["coverage"]["value"] == .6
    component = supplement["hsps"][0]["alignment_components"]
    assert component["geometry_available"] == (representation == "processed")


def test_sidecar_from_different_task_cannot_attach_even_when_literal_ids_match():
    binding, artifacts, contents = bundle()
    parsed = parse_raw(binding, artifacts, contents)
    wrong = deepcopy(artifacts["homology_metadata_json"])
    wrong["task_association"]["task_id"] = "SYNTHETIC-other-task"
    native = read_homology_metadata(contents["homology_metadata_json"], artifact=wrong,
        description_links=[link for query in parsed["queries"] for link in query["description_links"]])
    metadata = bind_homology_metadata(parsed, native_metadata=native, supplied_metadata=supplied())
    sheet = build_homology_sheet(parsed, metadata=metadata)
    assert "homology_metadata_artifact_binding_conflict" in {row["code"] for row in metadata["diagnostics"]}
    assert sheet["queries"][0]["blast_sheet"]["functions"] == []
    assert len(metadata["records"]) == 2


def test_invalid_prior_set_is_local_to_query_and_never_silently_filtered():
    *_, sheet = example()
    scores = calculate_homology_scores(sheet, database_model={"temperature_bits": 2, "function_priors": {F: 1, G: 2}})
    assert scores["queries"][0]["conditional_function_weights"]["unadjusted_probabilities"] == {F: .5, G: .5}
    assert scores["queries"][1]["conditional_function_weights"] is None
    assert scores["queries"][1]["diagnostics"][0]["code"] == "complete_nonnegative_function_priors_required"


@pytest.mark.parametrize("key", ["report_index", "hit_index", "description_index"])
@pytest.mark.parametrize("value", [False, 0.0, "0"])
def test_pairwise_subject_links_require_integer_original_ordinals(key, value):
    doc = program_document("blastp")
    binding, artifacts, contents = bundle(doc, mode="pairwise_correspondence", extras=False)
    add_subject(binding, doc)
    binding["subject_binding"]["native_hit_links"][0][key] = value
    _, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents)
    assert sheet["queries"][0]["blast_sheet"] is None
    assert sheet["queries"][0]["diagnostics"][-1]["code"] == "homology_pairwise_subject_membership_unproved"


def test_malformed_hsp_calculation_keeps_other_hsps_and_queries():
    doc = raw_document()
    doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"].append(None)
    binding, artifacts, contents = bundle(doc)
    _, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents)
    scored = calculate_homology_scores(sheet, database_model={"temperature_bits": 2})
    assert len(scored["queries"]) == 2
    hsps = scored["alignment_supplements"]["queries"][0]["hits"][0]["hsps"]
    assert len(hsps) == 4
    assert hsps[0]["alignment_components"]["counts"]["identical_pairs"] == 4
    assert hsps[-1]["alignment_components"]["geometry_available"] is False
    assert scored["queries"][0]["conditional_function_weights"]["unadjusted_probabilities"] == {F: 2 / 3, G: 1 / 3}
    assert scored["queries"][1]["conditional_function_weights"]["unadjusted_probabilities"] is None
    # A corrupted saved independent HSP is exposed, never repaired into a native locator.
    sheet["queries"][0]["normalized_result"]["hits"][0]["hsps"][-1] = None
    rescored = calculate_homology_scores(sheet)
    assert rescored["alignment_supplements"]["queries"][0]["hits"][0]["hsps"][-1]["source_locator"]["pointer"] is None
    assert rescored["queries"][1]["conditional_function_weights"] is not None


def test_original_normalized_input_map_reference_never_populates_invented_coordinates():
    binding, artifacts, contents = bundle(extras=False)
    query_binding = binding["query_bindings"][0]
    query_binding["sequence_transform"].update(kind="verified_fasta_normalization", coordinate_map_ref="SYNTHETIC-supplied-map-ref")
    query_binding["supplied_length"] = 13
    query_binding["supplied_sequence_sha256"] = "2" * 64
    _, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents)
    supplement = calculate_homology_alignment_supplements(sheet)["queries"][0]
    assert supplement["original_supplied_coordinate_projection"] == "unavailable"
    assert supplement["hits"][0]["span_union"]["query"]["coverage"]["denominator"] == 10
    assert sheet["queries"][0]["query_binding"]["sequence_transform"]["coordinate_map_ref"] == "SYNTHETIC-supplied-map-ref"


def test_target_context_boolean_report_index_is_not_an_ordinal():
    binding, artifacts, contents = bundle(extras=False)
    extra = supplied()
    extra["target_context_by_query"] = [{"report_index": False, "taxid": 562, "lineage": [],
        "source": "SYNTHETIC-independent-source", "independent_of_search": True}]
    metadata, sheet = metadata_and_sheet(parse_raw(binding, artifacts, contents), artifacts, contents, extra)
    assert metadata["queries"][0]["target_context"] == {}
    assert sheet["queries"][0]["blast_sheet"]["taxonomy"]["target_independent_of_search"] is None


def test_native_metadata_previously_read_against_different_description_cannot_rebind_by_ordinal():
    binding, artifacts, contents = bundle()
    first = parse_raw(binding, artifacts, contents)
    native = read_homology_metadata(contents["homology_metadata_json"], artifact=artifacts["homology_metadata_json"],
        description_links=[link for query in first["queries"] for link in query["description_links"]])
    doc = raw_document()
    description = doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["description"][0]
    description["title"] = description["title"].replace("SYNTHETIC_FUNCTION_ALPHA", "SYNTHETIC_CHANGED")
    replace_content(binding, artifacts, contents, "blast_json15_raw", encoded(doc))
    current = parse_raw(binding, artifacts, contents)
    metadata = bind_homology_metadata(current, native_metadata=native, supplied_metadata=supplied())
    sheet = build_homology_sheet(current, metadata=metadata)
    assert [row["function"] for row in sheet["queries"][0]["blast_sheet"]["functions"]] == [G]
    assert sheet["queries"][0]["blast_sheet"]["hits"][0]["measurements"]["maximum_bit_score"] == 20
