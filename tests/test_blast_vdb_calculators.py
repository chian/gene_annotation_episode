"""Exact VDB synthetic oracles and retained paired-native geometry regressions."""
from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import types

import pytest

from gene_annotation_episode.blast_vdb_inputs import populate_blast_vdb_sheet as populate
from gene_annotation_episode.blast_vdb_calculators import calculate_blast_vdb_components as calculate
from gene_annotation_episode.blast_pairwise_grader import alignment_components, blast_hsp_column_correspondence
from gene_annotation_episode.blast_sequence_database import _rows
from gene_annotation_episode import alignment_correspondence as common
from gene_annotation_episode import blast_pairwise_grader as paired
from gene_annotation_episode import blast_vdb_calculators as module
from test_blast_vdb_inputs import collect, inputs, hsp, identity, provenance, entity, sequence, metadata


def codes(result):
    return {i["code"] for i in result["issues"]}


def feature(values, *, interval, identifier="feature", strand=1, translation=None, genetic_code=None,
            codon_start=None, kind="CDS", function=None, hit=0):
    member = values["member_bindings"][hit]; fid = identity(identifier, "synthetic:feature")
    mid = "feature:" + identifier
    native = dict(feature_identifier=fid, key=kind, location=f"{interval[0]+1}..{interval[1]}", segments=[interval],
        strand=strand, partial5=False, partial3=False, codon_start=codon_start, genetic_code=genetic_code,
        translation=translation, qualifiers=[], member_sequence_metadata_key=f"member{hit}")
    assignments = [] if function is None else [dict(function=function, evidence=[], source=provenance("/function"))]
    values["reference_metadata"].append(metadata(mid, entity("feature", dataset=member["dataset_key"], member=member["member_identifier"], feature=fid),
        identifiers=[fid], feature=native, functions=assignments))
    values["feature_bindings"].append(dict(search_key=deepcopy(values["search"]["search_key"]), hit_ordinal=member["hit_ordinal"],
        member_binding_index=hit, member_identifier=deepcopy(member["member_identifier"]), feature_identifier=fid,
        feature_kind=kind, member_interval=interval, segments=[interval], location_status="exact", strand=strand,
        genetic_code=genetic_code, codon_start=codon_start, function=function, feature_sequence_sha256=None,
        translation_metadata_key=mid, provenance=provenance("/features/" + identifier)))


def translated_case(reverse=False, offset=False):
    symbols = "TTTAGCCATAAA" if reverse else "CCCATGGCTAAACCCCCC"
    native = hsp("MAK", query_from=1, query_to=3, hit_from=1 if reverse else 4, hit_to=9 if reverse else 12,
                 hit_frame=-1 if reverse else 1)
    search = collect(program="tblastn_vdb", query="MAKGGG", selected=[0, 3],
        hits=[dict(len=len(symbols), description=[dict(id="NC_X.1", accession="NC_X.1")], hsps=[native])])["searches"][0]
    values = inputs(search, symbols=[symbols], kind="reference")
    feature(values, interval=[0, 9] if reverse else [3, 12], strand=-1 if reverse else 1,
        translation="MAK", genetic_code=1, codon_start=1, function={"namespace": "EC", "value": "1.2.3.4"})
    if offset:
        # Off-frame reference translation is independently supplied and valid;
        # the HSP codon map cannot be transferred by its overlapping span.
        feature(values, interval=[4, 13], identifier="offset", translation="WLN", genetic_code=1, codon_start=1)
    return values


def population_entity(kind, member=None, group=None, feature_id=None, sample=None):
    return dict(kind=kind, member_key=member, sequence_group_key=group, feature_identifier=feature_id, sample_key=sample)


def population(values, count_unit, members, *, functions=None, function_members=None):
    datasets = [dict(dataset_key=d["dataset_key"], identifier=deepcopy(d["identifier"]), snapshot=deepcopy(d["snapshot"]),
        sra_mode=d["search_context"]["sra_mode"], include_filtered_reads=d["search_context"]["include_filtered_reads"]) for d in values["dataset_records"]]
    return dict(population_key=count_unit, datasets=datasets, count_unit=count_unit, scope="searched_population", total_count=len(members),
        complete=True, members=members, function_counts=functions, function_members=function_members,
        source=provenance("/population/" + count_unit), native_record={"fixture_kind": "synthetic_measured_enumeration", "members": deepcopy(members)})


def test_two_reads_one_sequence_exact_components():
    values = inputs(); sheet = populate(**values); before = deepcopy(sheet); result = calculate(sheet)
    assert sheet == before
    assert set(result) == {"schema", "search_key", "status", "hsps", "subjects", "membership", "sequence_groups", "sample_groups",
                           "feature_components", "taxonomy", "source_quality", "population_components", "issues"}
    for row in result["hsps"]:
        assert row["native_components"]["counts"]["paired_columns"] == 8
        assert row["native_components"]["counts"]["identical_pairs"] == 8
        assert row["substitutions"]["value"] == 0
        assert row["full_query_coverage"]["value"] == 1
        assert row["selected_query_coverage"]["value"] == 1
        assert row["full_member_coverage"]["value"] == 1
    membership = result["membership"]
    assert membership["reported_subject_count"]["value"] == 2
    assert membership["origin_bound_subject_count"]["value"] == 2
    assert membership["counts_by_kind"][0]["origin_member_count"]["value"] == 2
    assert membership["native_search_statistics"]["db_num"] == 123
    assert result["sequence_groups"]["demonstrated_group_count"]["value"] == 1
    assert result["sequence_groups"]["duplicate_subject_representations"]["value"] == 1
    assert result["sample_groups"]["observed_origin_sample_count"]["value"] == 2
    assert result["population_components"]["function_weight_model"]["status"] == "unavailable"
    assert result["status"] == "partial"


def test_sample_merge_and_missing_preserve_literal_denominators():
    values = inputs()
    values["member_bindings"][1]["sample_key"] = "S0"
    values["dataset_records"][1]["sample_links"][0].update(sample_key="S0", sample_identifier=identity("S0", "sample"))
    sample = next(m for m in values["reference_metadata"] if m["metadata_key"] == "sample1")
    sample["entity"]["sample_key"] = "S0"; sample["identifiers"] = [identity("S0", "sample")]
    result = calculate(populate(**values))
    assert result["sample_groups"]["observed_origin_sample_count"]["value"] == 1
    absent = calculate(populate(**inputs(samples=False)))
    assert absent["sample_groups"]["observed_origin_sample_count"]["value"] == 0
    assert absent["sample_groups"]["unresolved_origin_member_count"]["value"] == 2
    assert not absent["sample_groups"]["complete_for_origin_members"]


def test_catalogue_membership_does_not_create_observed_origins():
    search = collect(hits=[dict(len=8, description=[dict(id="NC_X.1", accession="NC_X.1")], hsps=[hsp()])])["searches"][0]
    values = inputs(search, kind="reference")
    values["member_bindings"][0]["relationship"] = "catalog_membership"
    other = deepcopy(values["dataset_records"][0]); other["dataset_key"] = "D1"
    values["dataset_records"].append(other)
    candidate = deepcopy(values["member_bindings"][0]); candidate["dataset_key"] = "D1"
    values["member_bindings"].append(candidate)
    result = calculate(populate(**values))
    membership = result["membership"]
    assert membership["reported_subject_count"]["value"] == 1
    assert membership["origin_ambiguous_subject_count"]["value"] == 1
    assert len(membership["catalogue_members"]) == 2 and not membership["origin_members"]
    assert result["hsps"][0]["native_components"]["native_scores"]["bit_score"] == 20
    assert result["sample_groups"]["observed_origin_sample_count"]["value"] == 0
    values["member_bindings"].pop()
    result = calculate(populate(**values))
    assert result["membership"]["origin_bound_subject_count"]["value"] == 0


def test_overlap_union_and_feature_nonoverlap():
    native = dict(len=12, description=[dict(id="r1", accession="r1")], hsps=[
        hsp("AAAAAA"), hsp("AAAAAA", query_from=4, query_to=9, hit_from=4, hit_to=9)])
    values = inputs(collect(query="A" * 12, selected=[0, 9], hits=[native])["searches"][0], symbols=["A" * 12])
    feature(values, interval=[4, 8], kind="misc_feature")
    feature(values, interval=[10, 12], identifier="outside", kind="misc_feature")
    result = calculate(populate(**values)); subject = result["subjects"][0]
    assert subject["observed_paired_query_units"]["value"] == 9
    assert subject["full_query_coverage"]["value"] == .75
    assert subject["selected_query_coverage"]["value"] == 1
    assert result["feature_components"][0]["feature_paired_nt_coverage"]["value"] == 1
    assert result["feature_components"][0]["paired_subject_fraction_in_feature"]["value"] == 4 / 9
    assert result["feature_components"][1]["relation_status"] == "nonoverlap"
    assert result["feature_components"][1]["feature_paired_nt_coverage"]["value"] == 0


@pytest.mark.parametrize("reverse", [False, True])
def test_translated_exact_feature_correspondence(reverse):
    result = calculate(populate(**translated_case(reverse=reverse)))
    row = result["hsps"][0]; feature_row = result["feature_components"][0]
    assert row["query_span"]["value"] == 3 and row["reference_span"]["value"] == 9
    assert row["full_query_coverage"]["value"] == .5
    assert row["selected_query_coverage"]["value"] == 1
    assert row["full_member_coverage"]["value"] == (.75 if reverse else .5)
    assert feature_row["relation_status"] == "translated_correspondence"
    assert feature_row["corresponding_feature_residue_union"] == [0, 1, 2]
    assert feature_row["feature_paired_residue_coverage"]["value"] == 1
    assert feature_row["hsp_rows"][0]["identical_query_feature_residues"]["value"] == 3
    columns = row["correspondence"]["columns"]
    positions = [list(range(c["reference_interval"][1]-1, c["reference_interval"][0]-1, -1)) if reverse
                 else list(range(*c["reference_interval"])) for c in columns]
    assert positions == ([[8, 7, 6], [5, 4, 3], [2, 1, 0]] if reverse else [[3, 4, 5], [6, 7, 8], [9, 10, 11]])
    mapping = feature_row["translation_map"]
    assert mapping["status"] == "available"
    assert [c["member_positions"] for c in mapping["codons"]] == positions
    assert [c["oriented_triplet"] for c in mapping["codons"]] == ["ATG", "GCT", "AAA"]
    assert [c["translated_symbol"] for c in mapping["codons"]] == ["M", "A", "K"]
    assert [c["feature_residue_index"] for c in mapping["codons"]] == [0, 1, 2]
    assert mapping["leading_untranslated_member_positions"] == []
    assert mapping["trailing_untranslated_member_positions"] == []


def test_codon_map_leading_trailing_bases_terminal_stop_and_noncoding_null():
    symbols = "AATGGCTTAACC"
    native = dict(len=len(symbols), description=[dict(id="r1", accession="r1")], hsps=[hsp("MA", hit_from=2, hit_to=7, hit_frame=2)])
    values = inputs(collect(program="tblastn_vdb", query="MA", hits=[native])["searches"][0], symbols=[symbols], kind="reference")
    feature(values, interval=[0, len(symbols)], translation="MA", codon_start=2, genetic_code=1)
    feature(values, interval=[0, 1], identifier="noncoding", kind="misc_feature")
    result = calculate(populate(**values)); row = result["feature_components"][0]
    mapping = row["translation_map"]
    assert mapping["leading_untranslated_member_positions"] == [0]
    assert mapping["trailing_untranslated_member_positions"] == [10, 11]
    assert mapping["codons"][-1] == dict(ordinal=2, member_positions=[7, 8, 9], oriented_triplet="TAA",
        translated_symbol="*", feature_residue_index=None, feature_symbol=None, terminal_stop=True)
    assert row["feature_translation_length"]["value"] == 2
    assert row["feature_paired_residue_coverage"]["value"] == 1
    assert result["feature_components"][1]["translation_map"] is None


def test_missing_translation_does_not_fabricate_empty_codon_positions():
    values = translated_case(); values["reference_metadata"][-1]["feature"]["translation"] = None
    mapping = calculate(populate(**values))["feature_components"][0]["translation_map"]
    assert mapping["status"] == "unavailable" and mapping["codons"] == []
    assert mapping["leading_untranslated_member_positions"] is None
    assert mapping["trailing_untranslated_member_positions"] is None


def test_synthetic_reverse_translated_table_and_json_have_same_triplets():
    fields = ["qseqid", "sseqid", "saccver", "qlen", "slen", "qstart", "qend", "sstart", "send", "sframe", "length", "nident", "gaps", "bitscore", "evalue", "qseq", "sseq"]
    raw = b"# TBLASTN 2.17.0+\n# Query: q\n# Database: synthetic-selected\nq\tNC_X.1\tNC_X.1\t6\t12\t1\t3\t9\t1\t-1\t3\t3\t0\t20\t.001\tMAK\tMAK\n# 1 hits found\n"
    search = collect(program="tblastn_vdb", query="MAKGGG", selected=[0, 3], raw=raw, format_name="tabular7", fields=fields)["searches"][0]
    values = inputs(search, symbols=["TTTAGCCATAAA"], kind="reference")
    feature(values, interval=[0, 9], strand=-1, translation="MAK", genetic_code=1, codon_start=1)
    table = calculate(populate(**values)); native = calculate(populate(**translated_case(reverse=True)))
    assert table["feature_components"][0]["translation_map"]["codons"] == native["feature_components"][0]["translation_map"]["codons"]
    assert table["feature_components"][0]["feature_paired_residue_coverage"]["value"] == 1
    assert table["hsps"][0]["native_hsp"]["hit_from"] == 9
    assert native["hsps"][0]["native_hsp"]["hit_from"] == 1


def test_translated_offset_code_sequence_and_strand_conflicts_keep_overlap():
    values = translated_case(offset=True)
    result = calculate(populate(**values)); offset = result["feature_components"][1]
    assert offset["paired_reference_overlap_nt"]["value"] == 8
    assert offset["hsp_rows"][0]["complete_paired_codons"]["value"] == 2
    assert offset["hsp_rows"][0]["partial_codon_overlap_nt"]["value"] == 2
    assert offset["relation_status"] == "overlap_only"
    values = translated_case(); values["dataset_records"][0]["search_context"]["subject_genetic_code"] = 2
    bad = calculate(populate(**values))
    assert bad["feature_components"][0]["paired_reference_overlap_nt"]["value"] == 9
    assert bad["feature_components"][0]["feature_paired_residue_coverage"]["value"] is None
    assert "blast_vdb_feature_code_conflict" in codes(bad)
    values = translated_case(reverse=True)
    values["feature_bindings"][0]["strand"] = 1
    values["reference_metadata"][-1]["feature"].update(strand=1, translation="F​SH".replace("\u200b", ""))
    bad = calculate(populate(**values))
    assert bad["feature_components"][0]["paired_reference_overlap_nt"]["value"] == 9
    assert bad["feature_components"][0]["relation_status"] == "overlap_only"
    values = translated_case()
    values["member_bindings"][0]["reference_identity"]["sequence_sha256"] = "f" * 64
    bad = calculate(populate(**values))
    assert bad["feature_components"][0]["paired_reference_overlap_nt"]["value"] == 9
    assert bad["feature_components"][0]["translation_map"]["status"] != "available"
    assert "blast_vdb_feature_sequence_unavailable" in codes(bad)


def test_reverse_phase_cannot_be_repaired_by_conflicting_metadata_length():
    values = translated_case(reverse=True)
    # Native 12-nt length makes 1..9/frame -2 invalid. A false 13-nt metadata
    # length must not repair it by changing the shared geometry denominator.
    raw = deepcopy(values["search"]["native"]["search"]["hits"])
    raw[0]["hsps"][0]["hit_frame"] = -2
    search = collect(program="tblastn_vdb", query="MAKGGG", selected=[0, 3], hits=raw)["searches"][0]
    values = inputs(search, symbols=["TTTAGCCATAAAA"], kind="reference")
    result = calculate(populate(**values))
    assert result["hsps"][0]["native_components"]["counts"]["paired_columns"] == 3
    assert not result["hsps"][0]["native_components"]["geometry_available"]
    assert "frame_coordinate_phase_conflict" in codes(result)


def test_full_unknown_and_unbound_query_extent():
    native = dict(len=8, description=[dict(id="r1", accession="r1")], hsps=[hsp("ACGTAC")])
    values = inputs(collect(hits=[native])["searches"][0])
    result = calculate(populate(**values))
    assert result["subjects"][0]["full_query_coverage"]["value"] == .75
    assert result["subjects"][0]["selected_query_coverage"]["value"] == .75
    assert result["subjects"][0]["coordinate_context"]["query"]["selected_interval"] is None
    values["dataset_records"][0]["search_context"]["query_extent"] = {"mode": "unknown", "interval": None, "source": None}
    result = calculate(populate(**values))
    assert result["subjects"][0]["full_query_coverage"]["value"] == .75
    assert result["subjects"][0]["selected_query_coverage"]["value"] is None
    values["query_binding"] = None
    result = calculate(populate(**values))
    assert result["subjects"][0]["full_query_coverage"]["value"] is None


def test_pssm_coordinates_are_not_biological_sequence_identity():
    native = dict(len=9, description=[dict(id="r1", accession="r1")], hsps=[hsp("MAK", hit_to=9, hit_frame=1)])
    values = inputs(collect(program="tblastn_vdb", query="MAK", query_kind="pssm", hits=[native])["searches"][0], symbols=["ATGGCTAAA"])
    mapping = dict(pssm_key="pssm", num_columns=3, columns=[dict(column=0, master_position=0, symbol="M"),
        dict(column=1, master_position=None, symbol="-"), dict(column=2, master_position=1, symbol="K")])
    values["reference_metadata"].append(metadata("master", entity("query_master", pssm="pssm"),
        source=provenance("/master"), master_mapping=mapping))
    result = calculate(populate(**values))
    assert result["hsps"][0]["query_axis_kind"] == "pssm_master"
    assert result["hsps"][0]["full_query_coverage"]["value"] == 1
    assert "blast_vdb_query_biological_identity_unestablished" in codes(result)
    values["reference_metadata"][-1]["master_mapping"]["pssm_key"] = "wrong_same_length"
    assert calculate(populate(**values))["hsps"][0]["full_query_coverage"]["value"] is None


def test_native_numbers_without_traceback_and_partial_output():
    native = dict(len=8, description=[dict(id="r1", accession="r1")], hsps=[dict(bit_score=42, evalue=0,
        align_len=5, identity=4, gaps=1, query_from=1, query_to=5, hit_from=1, hit_to=4)])
    values = inputs(collect(hits=[native], completion={"native_returncode": 1, "producer_complete": False})["searches"][0])
    result = calculate(populate(**values)); row = result["hsps"][0]
    assert row["native_components"]["native_scores"]["bit_score"] == 42
    assert row["native_components"]["native_scores"]["evalue"] == 0
    assert row["substitutions"]["value"] == 0
    assert row["full_query_coverage"]["value"] is None and row["correspondence"]["columns"] == []
    assert result["status"] == "partial"


def test_original_archive_and_hsp_ordinals_shared_private_port():
    native = dict(len=8, description=[dict(id="r1", accession="r1")], hsps=[None, hsp()])
    collection = collect(hits=[native], archive=True)
    values = inputs(collection["searches"][0])
    mechanical = []
    normalized, index, incomplete, ordinals = _rows({"search": values["search"], "report_source": values["report_source"]}, mechanical)
    assert not mechanical and incomplete == {0} and ordinals == [0]
    assert index["hits"][0]["hsps"][0]["row_key"]["hsp_ordinal"] == 1
    result = calculate(populate(**values))
    assert result["hsps"][0]["row_key"]["hsp_ordinal"] == 1
    assert result["hsps"][0]["source_locator"]["pointer"].endswith("/hits/0/hsps/1")
    assert result["subjects"][0]["observed_paired_reference_nt"]["value"] == 8
    assert result["subjects"][0]["full_query_coverage"]["value"] is None
    second = inputs(collection["searches"][1]); second["member_bindings"] = values["member_bindings"]
    result = calculate(populate(**second))
    assert result["membership"]["origin_bound_subject_count"]["value"] == 0
    values["report_source"]["member_sha256"] = "f" * 64
    result = calculate(populate(**values))
    assert result["status"] == "incompatible" and not result["hsps"]


def table_values():
    fields = ["qseqid", "sseqid", "saccver", "qlen", "slen", "qstart", "qend", "sstart", "send", "length", "nident", "gaps", "bitscore", "evalue", "qseq", "sseq"]
    raw = b"# BLASTN 2.17.0+\n# Query: q\n# Database: synthetic-selected\nbad\nq\tr1\tr1\t8\t8\t1\t8\t1\t8\t8\t8\t0\t20\t0.001\tACGTACGT\tACGTACGT\n# 2 hits found\n"
    return inputs(collect(raw=raw, format_name="tabular7", fields=fields)["searches"][0])


def test_table_descriptor_native_row_zero_invalid_and_row_one_preserved():
    values = table_values(); result = calculate(populate(**values))
    row = result["hsps"][0]
    assert row["row_key"]["hsp_ordinal"] == 1
    assert row["source_locator"]["line_numbers"] == [5]
    assert row["source_locator"]["data_row_ordinals"] == [1]
    assert result["subjects"][0]["full_query_coverage"]["value"] is None
    broken = deepcopy(values); broken["search"]["normalized"]["native"].pop("table_layout")
    assert "blast_vdb_table_layout_unavailable" in codes(calculate(populate(**broken)))
    broken = deepcopy(values); broken["search"]["row_map"][0]["hsp_ordinals"] = [0]
    assert "blast_vdb_native_row_map_conflict" in codes(calculate(populate(**broken)))


def test_zero_hits_requires_actual_report_success_and_bound_query():
    values = inputs(collect(hits=[])["searches"][0])
    assert calculate(populate(**values))["status"] == "no_reported_hits"
    values["search"]["reporting"]["native_returncode"] = 1
    assert calculate(populate(**values))["status"] == "unavailable"
    values = inputs(collect(raw=b"", format_name="tabular6", fields=["qseqid", "sseqid"])["searches"][0])
    assert calculate(populate(**values))["status"] != "no_reported_hits"


def test_distinct_population_units_and_filter_conflict():
    values = inputs(); members = []
    for i in range(10):
        m = values["member_bindings"][i % 2]
        memberkey = {k: deepcopy(m[k]) for k in ("dataset_key", "member_kind", "member_identifier")}
        if i >= 2:
            memberkey["member_identifier"] = identity(f"extra{i}")
        members.append(population_entity("read", member=memberkey))
    function = {"namespace": "EC", "value": "1.2.3.4"}
    reads = population(values, "reads", members, functions=[dict(function=function, count=3, assignment_scope="whole_sequence", source=provenance("/function-pop"))])
    digest = values["sequence_identity_bindings"][0]["binding"]["sequence_group"]
    sequences = population(values, "unique_sequences", [population_entity("unique_sequence", group=g) for g in [digest, "sha256:" + "1"*64, "sha256:" + "2"*64, "sha256:" + "3"*64]])
    samples = population(values, "samples", [population_entity("sample", sample=s) for s in ["S0", "S1", "S2", "S3", "S4"]])
    values["population_records"] = [reads, sequences, samples]
    result = calculate(populate(**values)); records = result["population_components"]["records"]
    assert [r["observed_fraction_of_supplied_population"]["value"] for r in records] == [.2, .25, .4]
    assert records[0]["function_components"][0]["population_function_fraction"]["value"] == .3
    assert records[0]["function_components"][0]["observed_function_entity_count"]["value"] is None
    values["population_records"][0]["datasets"][0]["include_filtered_reads"] = True
    result = calculate(populate(**values))
    assert result["population_components"]["records"][0]["observed_fraction_of_supplied_population"]["value"] is None
    assert "blast_vdb_population_filter_mismatch" in codes(result)


def test_population_duplicates_zero_and_reporting_limits():
    values = inputs(); pop = population(values, "reads", [])
    values["population_records"] = [pop]
    result = calculate(populate(**values))
    assert result["population_components"]["records"][0]["observed_fraction_of_supplied_population"]["value"] is None
    m = {k: deepcopy(values["member_bindings"][0][k]) for k in ("dataset_key", "member_kind", "member_identifier")}
    e = population_entity("read", member=m)
    pop["members"] = [e, e]; pop["total_count"] = 2
    assert "blast_vdb_population_count_conflict" in codes(calculate(populate(**values)))
    pop["members"] = [e]; pop["total_count"] = 1
    values["search"]["reporting"]["requested_hit_limit"] = 2
    result = calculate(populate(**values))["population_components"]["records"][0]
    assert result["observed_entity_count"]["value"] == 1
    assert result["observed_fraction_of_supplied_population"]["value"] is None


def test_feature_population_counts_instances_and_overlapping_functions_once():
    values = inputs()
    fn = {"namespace": "EC", "value": "1.2.3.4"}
    feature(values, interval=[0, 8], identifier="f0", kind="misc_feature", function=fn, hit=0)
    feature(values, interval=[0, 8], identifier="f1", kind="misc_feature", function=fn, hit=1)
    members = []
    for i in range(8):
        binding = values["member_bindings"][i % 2]
        key = {k: deepcopy(binding[k]) for k in ("dataset_key", "member_kind", "member_identifier")}
        members.append(population_entity("feature", member=key, feature_id=identity(f"f{i}", "synthetic:feature")))
    pop = population(values, "features", members, functions=[dict(function=fn, count=2, assignment_scope="feature", source=provenance("/f-count"))],
                     function_members=[dict(function=fn, entities=members[:2])])
    values["population_records"] = [pop]
    result = calculate(populate(**values)); record = result["population_components"]["records"][0]
    assert record["observed_entity_count"]["value"] == 2
    assert record["observed_fraction_of_supplied_population"]["value"] == .25
    assert record["function_components"][0]["observed_function_entity_count"]["value"] == 2
    assert result["sequence_groups"]["demonstrated_group_count"]["value"] == 1


def test_partial_native_hsp_population_is_observed_subset_only():
    native = dict(len=8, description=[dict(id="r1", accession="r1")], hsps=[hsp(), None])
    values = inputs(collect(hits=[native])["searches"][0])
    key = {k: deepcopy(values["member_bindings"][0][k]) for k in ("dataset_key", "member_kind", "member_identifier")}
    values["population_records"] = [population(values, "reads", [population_entity("read", member=key)])]
    result = calculate(populate(**values))["population_components"]["records"][0]
    assert result["observed_entity_count"]["value"] == 1
    assert result["observed_fraction_of_supplied_population"]["value"] is None
    assert not result["observed_fraction_of_supplied_population"]["complete_for_reported_hsps"]


@pytest.mark.parametrize("failure", ["missing_layout", "source_conflict", "entirely_malformed", "failed_empty"])
def test_unavailable_report_cannot_establish_zero_observed_population(failure):
    values = table_values() if failure == "missing_layout" else inputs()
    members = [population_entity("read", member={k: deepcopy(m[k])
        for k in ("dataset_key", "member_kind", "member_identifier")}) for m in values["member_bindings"]]
    fn = {"namespace": "EC", "value": "1.2.3.4"}
    values["population_records"] = [population(values, "reads", members,
        functions=[dict(function=fn, count=1, assignment_scope="whole_sequence", source=provenance("/count"))],
        function_members=[dict(function=fn, entities=members[:1])])]
    if failure == "missing_layout":
        values["search"]["normalized"]["native"].pop("table_layout")
    elif failure == "source_conflict":
        values["report_source"]["artifact_key"] = "wrong-source"
    else:
        values["search"] = collect(hits=[None] if failure == "entirely_malformed" else [],
            completion={"native_returncode": 1, "producer_complete": False} if failure == "failed_empty" else None)["searches"][0]
    result = calculate(populate(**values)); record = result["population_components"]["records"][0]
    assert result["status"] == ("incompatible" if failure == "source_conflict" else "unavailable")
    assert record["total_count"]["value"] == len(members)
    assert record["observed_entity_count"]["value"] is None
    assert record["observed_fraction_of_supplied_population"]["numerator"] is None
    assert record["observed_fraction_of_supplied_population"]["value"] is None
    assert not record["observed_fraction_of_supplied_population"]["complete_for_reported_hsps"]
    assert record["function_components"][0]["population_function_fraction"]["value"] == 1 / len(members)
    assert record["function_components"][0]["observed_function_entity_count"]["value"] is None
    assert result["membership"]["reported_subject_count"]["value"] is None
    assert not result["membership"]["complete_for_reported_subjects"]
    assert result["sequence_groups"]["demonstrated_group_count"]["value"] is None
    assert result["sample_groups"]["observed_origin_sample_count"]["value"] is None


def test_qualified_empty_report_establishes_zero_and_partial_subjects_preserve_subsets():
    values = inputs()
    members = [population_entity("read", member={k: deepcopy(m[k])
        for k in ("dataset_key", "member_kind", "member_identifier")}) for m in values["member_bindings"]]
    values["population_records"] = [population(values, "reads", members)]
    original = deepcopy(values["search"]["native"]["search"]["hits"][0])
    values["search"] = collect(hits=[original, None])["searches"][0]
    result = calculate(populate(**values)); record = result["population_components"]["records"][0]
    assert result["membership"]["reported_subject_count"]["value"] == 1
    assert result["membership"]["reported_hsp_count"]["value"] == 1
    assert not result["membership"]["complete_for_reported_subjects"]
    assert not result["sequence_groups"]["complete_for_reported_subjects"]
    assert record["observed_entity_count"]["value"] == 1
    assert record["observed_fraction_of_supplied_population"]["value"] is None
    assert "blast_hit_object_required" in codes(result)
    values["search"] = collect(hits=[])["searches"][0]
    values["member_bindings"] = []; values["sequence_identity_bindings"] = []
    result = calculate(populate(**values)); record = result["population_components"]["records"][0]
    assert result["status"] == "no_reported_hits"
    assert record["observed_entity_count"]["value"] == 0
    assert record["observed_fraction_of_supplied_population"]["value"] == 0


def test_repeated_native_subjects_of_same_member_feature_union_once():
    symbols = "CCCATGGCTAAACCCCCC"
    hits = [dict(len=len(symbols), description=[dict(id="NC_X.1", accession="NC_X.1")], hsps=[native])
        for native in (hsp("MA", hit_from=4, hit_to=9, hit_frame=1),
                       hsp("AK", query_from=2, query_to=3, hit_from=7, hit_to=12, hit_frame=1))]
    values = inputs(collect(program="tblastn_vdb", query="MAKGGG", selected=[0, 3], hits=hits)["searches"][0],
                    symbols=[symbols, symbols], kind="reference")
    values["member_bindings"][1].update(dataset_key="D0", sample_key="S0")
    values["dataset_records"] = values["dataset_records"][:1]
    values["reference_metadata"] = [m for m in values["reference_metadata"] if m["entity"]["dataset_key"] == "D0"]
    feature(values, interval=[3, 12], translation="MAK", genetic_code=1, codon_start=1)
    second = deepcopy(values["feature_bindings"][0]); second.update(hit_ordinal=1, member_binding_index=1)
    values["feature_bindings"].append(second)
    result = calculate(populate(**values)); rows = result["feature_components"]
    assert len(rows) == 1
    assert rows[0]["feature_binding_indices"] == [0, 1]
    assert [h["row_key"]["hit_ordinal"] for h in rows[0]["hsp_rows"]] == [0, 1]
    assert rows[0]["relation_status"] == "translated_correspondence"
    assert rows[0]["corresponding_feature_residue_union"] == [0, 1, 2]
    assert rows[0]["paired_reference_overlap_nt"]["value"] == 9
    assert rows[0]["feature_paired_residue_coverage"]["value"] == 1
    assert result["membership"]["reported_subject_count"]["value"] == 2
    assert len(result["membership"]["origin_members"]) == 1


@pytest.mark.parametrize("assignment_scope", ["feature", "sample"])
def test_function_assignment_scope_cannot_be_promoted_to_whole_member(assignment_scope):
    values = inputs(); member = values["member_bindings"][0]
    key = {k: deepcopy(member[k]) for k in ("dataset_key", "member_kind", "member_identifier")}
    fn = {"namespace": "EC", "value": "1.2.3.4"}; entities = [population_entity("read", member=key)]
    source = next(m for m in values["reference_metadata"] if m["metadata_key"] == "member0")
    source["functions"] = [dict(function=fn, evidence=[], source=provenance("/member-function"))]
    pop = population(values, "reads", entities,
        functions=[dict(function=fn, count=1, assignment_scope=assignment_scope, source=provenance("/count"))],
        function_members=[dict(function=fn, entities=entities)])
    values["population_records"] = [pop]
    result = calculate(populate(**values)); row = result["population_components"]["records"][0]["function_components"][0]
    assert row["population_function_count"]["value"] == 1
    assert row["population_function_fraction"]["value"] is None
    assert row["observed_function_entity_count"]["value"] is None
    assert "blast_vdb_population_function_assignments_unavailable" in codes(result)
    pop["function_counts"][0]["assignment_scope"] = "whole_sequence"
    row = calculate(populate(**values))["population_components"]["records"][0]["function_components"][0]
    assert row["population_function_fraction"]["value"] == 1
    assert row["observed_function_entity_count"]["value"] == 1


@pytest.mark.parametrize("count_unit", ["unique_sequences", "samples"])
def test_population_entity_specific_unknowns_keep_only_observed_subsets(count_unit):
    values = inputs()
    if count_unit == "unique_sequences":
        group = values["sequence_identity_bindings"][0]["binding"]["sequence_group"]
        members = [population_entity("unique_sequence", group=group)]
        values["sequence_identity_bindings"].pop()
    else:
        members = [population_entity("sample", sample="S0"), population_entity("sample", sample="S1")]
        values["member_bindings"][1]["sample_key"] = None
    values["population_records"] = [population(values, count_unit, members)]
    result = calculate(populate(**values))["population_components"]["records"][0]
    assert result["observed_entity_count"]["value"] == 1
    assert result["observed_fraction_of_supplied_population"]["value"] is None
    assert not result["observed_fraction_of_supplied_population"]["complete_for_reported_hsps"]


def test_native_statistics_and_raw_invalid_fields_cannot_be_laundered():
    values = inputs()
    values["search"]["normalized"]["search"]["statistics"]["db_num"] = 42
    result = calculate(populate(**values))
    assert result["status"] == "incompatible" and "blast_vdb_native_reporting_conflict" in codes(result)
    native = dict(len=8, description=[dict(id="r1", accession="r1")], hsps=[hsp(score="not a number")])
    values = inputs(collect(hits=[native])["searches"][0])
    result = calculate(populate(**values))
    assert result["hsps"][0]["native_hsp"]["score"] == "not a number"
    assert result["hsps"][0]["native_components"]["native_scores"]["score"] is None


def test_conflicting_sequence_digests_do_not_invent_independent_sequences():
    values = inputs()
    wrong = deepcopy(values["sequence_identity_bindings"][0])
    wrong["binding"].update(digest="c" * 64, sequence_group="sha256:" + "c" * 64)
    values["sequence_identity_bindings"].append(wrong)
    result = calculate(populate(**values))
    assert result["sequence_groups"]["grouped_subject_count"]["value"] == 1
    assert result["sequence_groups"]["ungrouped_subject_count"]["value"] == 1
    assert result["sequence_groups"]["duplicate_subject_representations"]["value"] == 0
    assert result["subjects"][0]["full_query_coverage"]["value"] == 1


def test_missing_table_descriptor_does_not_manufacture_measured_zero_counts():
    values = table_values(); values["search"]["normalized"]["native"].pop("table_layout")
    result = calculate(populate(**values))
    assert result["status"] == "unavailable"
    assert result["membership"]["reported_subject_count"]["value"] is None
    assert not result["membership"]["complete_for_reported_subjects"]


def test_conflicting_sample_key_is_not_arbitrarily_first_sample():
    values = inputs()
    values["member_bindings"][1]["sample_key"] = "S0"
    values["dataset_records"][1]["sample_links"][0]["sample_key"] = "S0"
    result = calculate(populate(**values))
    assert result["sample_groups"]["observed_origin_sample_count"]["value"] == 0
    assert result["sample_groups"]["unresolved_origin_member_count"]["value"] == 2
    assert "blast_vdb_sample_link_conflict" in codes(result)


def test_taxonomy_three_groups_and_measured_quality_without_sample_promotion():
    hits = [dict(len=8, description=[dict(id=f"r{i}", accession=f"r{i}")], hsps=[hsp()]) for i in range(3)]
    values = inputs(collect(hits=hits)["searches"][0], symbols=["ACGTACGT", "ACGTACGA", "ACGTACGC"])
    for i, taxid in enumerate([10, 10, 20]):
        m = next(m for m in values["reference_metadata"] if m["metadata_key"] == f"member{i}")
        m.update(taxid=taxid, taxid_scope="entity_organism", lineage=[dict(taxid=taxid, rank="species", name=str(taxid))])
    values["target_context"] = dict(query_operand=deepcopy(values["query_binding"]["operand"]), taxid=10,
        lineage=[dict(taxid=10, rank="species", name="A")], independent_of_search=True, source=provenance("/target"))
    m = values["reference_metadata"][0]
    m["assembly"] = dict(identifier=identity("assembly"), completeness_percent=97.5, contamination_percent=120,
        contig_count=3, contig_n50=100, total_sequence_length=200, method="CheckM", method_version="synthetic",
        source=provenance("/checkm"), linkage_source=provenance("/member-to-assembly"))
    result = calculate(populate(**values)); rank = result["taxonomy"]["sequence_group_ranks"][0]
    assert rank["same_taxon_pair_count"] == 1 and rank["comparable_pair_count"] == 3
    assert rank["same_taxon_pair_fraction"]["value"] == 1 / 3
    assert rank["different_taxon_pair_fraction"]["value"] == 2 / 3
    assert rank["target_matching_fraction"]["value"] == 2 / 3
    assert result["source_quality"]["records"][0]["completeness_fraction"]["value"] == .975
    assert result["source_quality"]["records"][0]["contamination_fraction"]["value"] == 1.2
    for m in values["reference_metadata"]:
        if m["entity"]["kind"] == "member":
            m["taxid_scope"] = "sample_context"
    result = calculate(populate(**values))
    rank = result["taxonomy"]["sequence_group_ranks"][0]
    assert rank["unknown_group_count"] == 3 and rank["same_taxon_pair_fraction"]["value"] is None


def test_saved_sheet_recalculation_forbids_io_and_sequence_scoring(monkeypatch):
    sheet = json.loads(json.dumps(populate(**translated_case())))
    expected = calculate(sheet)
    def forbidden(*args, **kwargs):
        raise AssertionError("I/O or wrong scoring path attempted")
    from gene_annotation_episode import blast_sequence_database, blast_database_grader
    for module, names in [(builtins, ["open"]), (Path, ["open", "read_text", "read_bytes"]),
                          (socket, ["socket", "create_connection"]), (subprocess, ["Popen", "run"]),
                          (blast_sequence_database, ["_admit", "build_database_sheet", "calculate_database_probabilities"]),
                          (blast_database_grader, ["build_database_sheet", "calculate_database_probabilities"])]:
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    assert calculate(sheet) == expected


def test_retained_paired_native_geometry_is_only_geometry_evidence():
    packet = Path(__file__).resolve().parent / "fixtures/blast_paired_native_reports"
    manifest = json.loads((packet / "manifest.json").read_text())
    assert manifest
    # The VDB execution identity is deliberately never substituted into these
    # actual paired fixtures. Their original shared geometry is the oracle.
    from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
    tested = 0; comparisons = {}
    for row in manifest:
        if row["invocation"]["execution_program"] not in {"blastn", "tblastn"}:
            continue
        raw = (packet / row["name"] / Path(row["path"]).name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
        collected = parse_blast_report_collection({row["artifact"]["artifact_key"]: raw},
            artifacts=[row["artifact"]], invocation=row["invocation"])
        for search in collected["searches"]:
            key = search["search_key"]
            source = dict(artifact_key=key["artifact_key"], artifact_ref=row["path"], member_ordinal=None, member_sha256=None)
            issues = []
            normalized, index, incomplete, ordinals = _rows({"search": search, "report_source": source}, issues)
            assert normalized is not None and not issues and not incomplete
            assert search["program_context"]["scientific_mode"] == "pairwise"
            results = []
            query_length = search["operand_binding"]["length"] if search["operand_binding"] else normalized["query"]["length"]
            for hit in normalized["hits"]:
                for native in hit["hsps"]:
                    components = alignment_components(native, program=row["invocation"]["execution_program"],
                        query_length=query_length, reference_length=hit["length"],
                        coordinate_convention="blast_json2" if normalized["format"] == "json2" else "directional")
                    correspondence = blast_hsp_column_correspondence(native, program=row["invocation"]["execution_program"],
                        query_length=query_length, reference_length=hit["length"],
                        coordinate_convention="blast_json2" if normalized["format"] == "json2" else "directional")
                    assert components["geometry_available"] and correspondence["geometry_status"] == "available"
                    results.append(components["pairs"])
            name = row["name"].removesuffix("_json15").removesuffix("_tabular7").removesuffix("_tabular6")
            comparisons.setdefault(name, []).append(results)
        tested += 1
    assert tested >= 8
    for results in comparisons.values():
        assert all(result == results[0] for result in results)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


@pytest.fixture(scope="module")
def before_shared_authority():
    """Pinned test-only arithmetic baseline; its dependencies are current ports."""
    path = Path(__file__).resolve().parent / "fixtures/blast_vdb_calculator_before_shared_authority.py"
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "5c47851f0d5e8987631cf022fac540d2a6d5268b1a30520ea7944ec4fce4d011"
    baseline = types.ModuleType("gene_annotation_episode._vdb_before_shared_authority")
    baseline.__file__ = str(path)
    baseline.__package__ = "gene_annotation_episode"
    exec(compile(raw, str(path), "exec"), baseline.__dict__)
    return baseline


def _shared_authority_case(case):
    if case in {"feature_forward", "feature_reverse", "feature_offset", "feature_code_conflict", "native_member_length_conflict"}:
        values = translated_case(reverse=case in {"feature_reverse", "native_member_length_conflict"},
            offset=case == "feature_offset")
        if case == "feature_code_conflict":
            values["dataset_records"][0]["search_context"]["subject_genetic_code"] = 2
        elif case == "native_member_length_conflict":
            hits = deepcopy(values["search"]["native"]["search"]["hits"])
            hits[0]["hsps"][0]["hit_frame"] = -2
            values = inputs(collect(program="tblastn_vdb", query="MAKGGG", selected=[0, 3], hits=hits)["searches"][0],
                symbols=["TTTAGCCATAAAA"], kind="reference")
        return values
    if case in {"empty_success", "failed_empty"}:
        return inputs(collect(hits=[], completion={"native_returncode": 1, "producer_complete": False}
            if case == "failed_empty" else None)["searches"][0])
    if case == "malformed_table_sibling":
        return table_values()
    if case == "ordinary":
        return inputs()
    if case == "unknown_query_extent":
        values = inputs()
        for dataset in values["dataset_records"]:
            dataset["search_context"]["query_extent"] = dict(mode="unknown", interval=None, source=None)
        return values
    if case == "unbound_query":
        values = inputs(); values["query_binding"] = None
        return values
    if case in {"unknown_lengths", "reverse_unknown_length"}:
        reverse = case == "reverse_unknown_length"
        native = hsp("MAK", hit_to=9, hit_frame=-2) if reverse else hsp()
        collection = collect(program="tblastn_vdb" if reverse else "blastn_vdb", query="MAK" if reverse else "ACGTACGT",
            hits=[dict(description=[dict(id="r1", accession="r1")], hsps=[native])])
        document = deepcopy(collection["searches"][0]["normalized"]["native"]["document"])
        if not reverse:
            document["BlastOutput2"][0]["report"]["results"]["search"].pop("query_len")
        search = collect(program="tblastn_vdb" if reverse else "blastn_vdb", query="MAK" if reverse else "ACGTACGT",
            raw=json.dumps(document).encode())["searches"][0]
        values = inputs(search)
        if not reverse:
            values["query_binding"] = None
        values["sequence_identity_bindings"] = []
        for row in values["reference_metadata"]:
            row["sequence"] = None
        return values
    selected = [6, 8] if case in {"selected_empty_clip", "partial_empty_clip"} else [2, 6] if case == "selected_native_width" else None
    if case in {"reported_only", "reported_invalid_identity", "reported_zero_paired"}:
        native = dict(align_len=5, identity=4, gaps=1, query_from=1, query_to=5, hit_from=1, hit_to=4, bit_score=42, evalue=0)
        if case == "reported_invalid_identity":
            native["identity"] = 5
        elif case == "reported_zero_paired":
            native.update(align_len=1, identity=0, gaps=1)
    else:
        native = hsp("ACGT", r="ACGA", identity=4) if case == "native_count_conflict" else hsp("ACGT")
        if case == "traceback_span_conflict":
            native["query_to"] = 6
        elif case == "invalid_traceback":
            native["qseq"] = "AC?T"
        elif case == "selected_native_width":
            native.update(query_from=3, query_to=6)
    hsps = [native, None] if case == "partial_empty_clip" else [native]
    collection = collect(selected=selected, hits=[dict(len=8, description=[dict(id="r1", accession="r1")], hsps=hsps)])
    if case == "selected_native_width":
        document = deepcopy(collection["searches"][0]["normalized"]["native"]["document"])
        document["BlastOutput2"][0]["report"]["results"]["search"]["query_len"] = 4
        collection = collect(selected=selected, raw=json.dumps(document).encode())
    return inputs(collection["searches"][0])


@pytest.mark.parametrize("case", [
    "ordinary", "native_count_conflict", "reported_only", "reported_invalid_identity", "reported_zero_paired",
    "invalid_traceback", "traceback_span_conflict", "selected_native_width", "selected_empty_clip", "partial_empty_clip",
    "unknown_query_extent", "unbound_query", "unknown_lengths", "reverse_unknown_length", "native_member_length_conflict",
    "feature_forward", "feature_reverse", "feature_offset", "feature_code_conflict", "empty_success", "failed_empty",
    "malformed_table_sibling",
])
def test_whole_components_match_pinned_pre_shared_authority(case, before_shared_authority):
    sheet = populate(**_shared_authority_case(case)); before = _canonical(sheet)
    expected = before_shared_authority.calculate_blast_vdb_components(sheet)
    actual = calculate(sheet)
    assert _canonical(actual) == _canonical(expected)
    assert _canonical(sheet) == before
    if case not in {"empty_success", "failed_empty"}:
        assert actual["hsps"]
    if case in {"unknown_lengths", "reverse_unknown_length"}:
        row = actual["hsps"][0]
        assert row["native_components"]["denominators"]["reference_length"] is None
        if case == "unknown_lengths":
            assert row["native_components"]["denominators"]["query_length"] is None
        assert row["query_span"]["value"] is not None and row["reference_span"]["value"] is not None
    if case in {"reported_only", "invalid_traceback", "traceback_span_conflict"}:
        row = actual["hsps"][0]
        assert not row["native_components"]["geometry_available"]
        assert row["query_span"]["value"] is not None and row["reference_span"]["value"] is not None
    if case in {"selected_empty_clip", "partial_empty_clip"}:
        coverage = actual["subjects"][0]["selected_query_coverage"]
        assert coverage["numerator"] == 0 and coverage["value"] is None


@pytest.mark.parametrize("case", [
    "native_count_conflict", "reported_only", "reported_invalid_identity", "reported_zero_paired",
    "traceback_span_conflict", "unknown_lengths", "reverse_unknown_length", "native_member_length_conflict",
])
def test_common_hsp_artifacts_supply_literal_cells_once(case, monkeypatch):
    """Observe actual shared outputs, without replacing their scientific cells."""
    artifacts, calculations, receiving = [], [], []
    original_artifacts = module.alignment_component_artifacts
    original_calculate = paired.calculate_correspondence_components
    original_correspondence = module.blast_hsp_column_correspondence
    def calculate_common(sheet):
        result = original_calculate(sheet)
        calculations.append(result)
        return result
    def calculate_artifacts(*args, **kwargs):
        result = original_artifacts(*args, **kwargs)
        artifacts.append(result)
        return result
    def receive_component(*args, **kwargs):
        receiving.append(kwargs["precomputed_components"])
        return original_correspondence(*args, **kwargs)
    monkeypatch.setattr(paired, "calculate_correspondence_components", calculate_common)
    monkeypatch.setattr(module, "alignment_component_artifacts", calculate_artifacts)
    monkeypatch.setattr(module, "blast_hsp_column_correspondence", receive_component)
    result = calculate(populate(**_shared_authority_case(case)))
    assert result["hsps"] and len(artifacts) == len(calculations) == len(receiving) == len(result["hsps"])
    for hsp_row, (legacy, _, calculated), observed, received in zip(result["hsps"], artifacts, calculations, receiving):
        assert calculated is observed and received is legacy
        assert _canonical(hsp_row["native_components"]) == _canonical(legacy)
        assert _canonical(hsp_row["substitutions"]["value"]) == _canonical(calculated["rows"][0]["counts"]["substituted_positions"])
        for field, axis in (("query_span", "query"), ("reference_span", "reference")):
            span = legacy["endpoint_spans"][axis]
            assert _canonical(hsp_row[field]["value"]) == _canonical(span["positions"] if span is not None else None)


def test_common_interval_and_fraction_ports_keep_local_availability(before_shared_authority, monkeypatch):
    intervals, widths, fractions = [], [], []
    original_union, original_width, original_ratio = common.interval_union_length, common.interval_length, common._ratio
    def union_length(value):
        intervals.append(deepcopy(value))
        return original_union(value)
    def interval_length(value):
        widths.append(deepcopy(value))
        return original_width(value)
    def ratio(numerator, denominator):
        fractions.append((numerator, denominator))
        return original_ratio(numerator, denominator)
    monkeypatch.setattr(common, "interval_union_length", union_length)
    monkeypatch.setattr(common, "interval_length", interval_length)
    monkeypatch.setattr(common, "_ratio", ratio)
    operand = [[8, 10], [0, 4], [2, 6], [6, 8], [0, 4]]
    assert module._length(operand) == before_shared_authority._length(operand)
    assert intervals == [operand]
    sheet = populate(**_shared_authority_case("selected_native_width"))
    datasets = {row["dataset_key"]: {"record": row} for row in sheet["dataset_records"]}
    actual_issues, expected_issues = [], []
    actual_axis = module._query_axis(sheet, datasets, sheet["reference_metadata"], actual_issues)
    expected_axis = before_shared_authority._query_axis(sheet, datasets, sheet["reference_metadata"], expected_issues)
    assert _canonical((actual_axis, actual_issues)) == _canonical((expected_axis, expected_issues))
    assert widths == [sheet["query_binding"]["operand"]["selected_interval"]]
    widths.clear()
    actual = module._coverage([[2, 6]], [[0, 4]], False, actual_axis, 8, None)
    expected = before_shared_authority._coverage([[2, 6]], [[0, 4]], False, expected_axis, 8, None)
    assert _canonical(actual) == _canonical(expected) and widths == [[2, 6]] and not fractions
    for args in ((None, 4), (1, None), (1, 0), (1, -1), (10**400, 1, False), (1, 4, True, "incompatible_input")):
        assert _canonical(module._ratio(*args)) == _canonical(before_shared_authority._ratio(*args))
    assert not fractions
    for args in ((0, 4), (3, 4)):
        assert _canonical(module._ratio(*args)) == _canonical(before_shared_authority._ratio(*args))
    assert fractions == [(0, 4), (3, 4)]
