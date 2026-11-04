"""Synthetic profile contracts and separately labeled genuine paired geometry.

No profile search, deployment, acquisition or biological inference runs here.
"""
from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.blast_pairwise_grader import alignment_components
from gene_annotation_episode.blast_profile_calculators import ISSUE_CODES, calculate_blast_profile_components
from gene_annotation_episode.blast_profile_inputs import populate_blast_profile_sheet
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from test_blast_profile_inputs import make_inputs, model_record, provenance, synthetic_hit, synthetic_hsp


def calculate(inputs):
    return calculate_blast_profile_components(populate_blast_profile_sheet(**inputs))


def codes(result):
    return {issue["code"] for issue in result["issues"]}


@pytest.mark.parametrize("program,reverse,query_intervals,first_pair,units", [
    ("rpsblast", False, [[0, 50]], [0, 1], 50),
    ("rpstblastn", False, [[0, 150]], [0, 3], 150),
    ("rpstblastn", True, [[150, 300]], [297, 300], 150),
    ("deltablast", False, [[0, 50]], [0, 1], 50),
])
def test_synthetic_50_model_positions_and_translated_150_query_units(program, reverse, query_intervals, first_pair, units):
    inputs = make_inputs(program, reverse=reverse)
    original = deepcopy(inputs)
    result = calculate(inputs)
    assert result["status"] == "complete", result["issues"]
    assert inputs == original
    assert result["schema"] == "blast_profile_components_v1"
    assert set(result) == {"schema", "search_key", "status", "hsps", "models", "function_components", "dependence", "taxonomy", "issues"}
    hsp, model = result["hsps"][0], result["models"][0]
    assert hsp["geometry_program"] == ("blastx" if program == "rpstblastn" else "blastp")
    assert hsp["reference_axis_kind"] == "profile_model" and hsp["query_axis_kind"] == "sequence"
    assert hsp["representative_symbol_identity"] == {"numerator": 50, "denominator": 50, "value": 1, "unit": "fraction"}
    assert hsp["native_hsp"] == original["search"]["native"]["search"]["hits"][0]["hsps"][0]
    assert hsp["model_matches"][0]["specific_bits_margin"] == 2
    assert hsp["model_matches"][0]["reporting_bits_margin"] == 7
    assert model["geometry_complete"] is True
    assert model["paired_model_positions"] == 50 and model["paired_query_units"] == units
    assert model["observed_paired_query_intervals"] == query_intervals
    assert model["observed_paired_model_intervals"] == [[0, 50]]
    assert model["model_coverage"]["value"] == model["query_coverage"]["value"] == 0.5
    pair = hsp["native_components"]["pairs"][0]
    assert [pair["query_start"], pair["query_end"]] == first_pair
    assert result["function_components"] == [{"function": {"namespace": "EC", "value": "1.2.3.4"},
        "profile_keys": ["profile_1"], "hsp_row_keys": [hsp["row_key"]], "binding_indices": [0]}]
    assert result["taxonomy"] == {"status": "unavailable", "population": "model_training_sequences",
                                  "components": None, "reason": "model_training_membership_not_supplied"}
    assert set(hsp) == {"row_key", "source_locator", "native_hsp", "geometry_program", "query_axis_kind",
        "reference_axis_kind", "native_components", "reported_query_length", "full_query_length",
        "selected_query_interval", "reported_model_length", "representative_symbol_identity", "model_matches", "issues"}
    assert set(model) == {"profile_key", "profile_record", "binding_status", "row_keys", "reported_model_lengths",
        "geometry_complete", "observed_paired_query_intervals", "observed_paired_model_intervals", "paired_query_units",
        "paired_model_positions", "query_coverage", "selected_query_coverage", "model_coverage", "query_unit", "model_unit", "issues"}


def test_overlapping_hsps_are_union_coverage_and_native_scores_never_sum():
    hit = synthetic_hit(positions=30)
    second = synthetic_hsp(start=21, positions=30, bits=43.12345678901234)
    second.update(hit_from=21, hit_to=50)
    hit["hsps"].append(second)
    result = calculate(make_inputs(hits=[hit]))
    assert [hsp["native_components"]["native_scores"]["bit_score"] for hsp in result["hsps"]] == [42, 43.12345678901234]
    assert result["hsps"][1]["model_matches"][0]["specific_bits_margin"] == 43.12345678901234 - 40
    model = result["models"][0]
    assert len(model["row_keys"]) == 2
    assert model["paired_query_units"] == model["paired_model_positions"] == 50
    assert model["query_coverage"]["value"] == model["model_coverage"]["value"] == 0.5
    assert model["observed_paired_query_intervals"] == [[0, 50]]


def test_same_family_models_stay_separate_with_actual_query_overlap():
    inputs = make_inputs(hits=[synthetic_hit(), synthetic_hit(2, start=21)])
    inputs["model_relations"] = [{"left_profile_key": "profile_1", "right_profile_key": "profile_2",
                                  "relation": "same_family", "provenance": provenance("/families/0")}]
    result = calculate(inputs)
    assert len(result["models"]) == 2
    assert [row["paired_query_units"] for row in result["models"]] == [50, 50]
    assert result["dependence"]["relations"] == inputs["model_relations"]
    assert result["dependence"]["query_overlaps"] == [{"left_profile_key": "profile_1", "right_profile_key": "profile_2",
        "paired_query_overlap_units": 30, "query_unit": "aa", "complete_for_reported_hsps": True}]
    group = result["function_components"][0]
    assert group["profile_keys"] == ["profile_1", "profile_2"]
    assert group["binding_indices"] == [0, 1] and len(group["hsp_row_keys"]) == 2
    assert "probability" not in json.dumps(result)


def test_model_length_conflict_disables_only_model_denominator():
    inputs = make_inputs()
    inputs["profile_records"][0]["num_columns"] = 120
    result = calculate(inputs)
    model = result["models"][0]
    assert model["reported_model_lengths"] == [100]
    assert model["profile_record"]["num_columns"] == 120
    assert model["model_coverage"] == {"numerator": 50, "denominator": None, "value": None, "unit": "fraction"}
    assert model["query_coverage"]["value"] == 0.5
    assert result["hsps"][0]["model_matches"][0]["specific_bits_margin"] == 2
    assert "blast_profile_model_length_conflict" in codes(result)


@pytest.mark.parametrize("binding_change", ["none", "unbound_original", "same_length_wrong_operand"])
def test_unbound_query_keeps_source_numbers_without_full_query_denominator(binding_change):
    inputs = make_inputs("rpstblastn", reverse=True, unbound_operand=binding_change == "unbound_original")
    if binding_change == "none":
        inputs["query_binding"] = None
    elif binding_change == "same_length_wrong_operand":
        inputs["query_binding"]["operand"]["artifact_key"] = "other_same_length_query"
    result = calculate(inputs)
    hsp, model = result["hsps"][0], result["models"][0]
    assert hsp["reported_query_length"] == 300 and hsp["full_query_length"] is None
    assert hsp["native_components"]["counts"]["paired_query_positions"] == 150
    assert model["query_coverage"]["denominator"] is None and model["query_coverage"]["value"] is None
    assert model["model_coverage"]["value"] == 0.5
    assert result["status"] == "partial"


def test_missing_digest_does_not_erase_source_qualified_full_or_selected_lengths():
    inputs = make_inputs(hits=[synthetic_hit(start=21, positions=30)], selected=[20, 60], query_length=40, full_length=100)
    inputs["query_binding"]["sequence_sha256"] = None
    result = calculate(inputs)
    hsp, model = result["hsps"][0], result["models"][0]
    assert hsp["reported_query_length"] == 40 and hsp["full_query_length"] == 100
    assert hsp["selected_query_interval"] == [20, 60]
    assert model["query_coverage"]["value"] == 0.3
    assert model["selected_query_coverage"]["value"] == 0.75
    assert "blast_profile_query_digest_unavailable" in codes(result)
    assert result["status"] == "partial"


def test_selected_original_coordinates_keep_full_and_reported_lengths_separate():
    hit = synthetic_hit(start=21, positions=30)
    result = calculate(make_inputs(hits=[hit], selected=[20, 60], query_length=40, full_length=100))
    hsp, model = result["hsps"][0], result["models"][0]
    assert hsp["reported_query_length"] == 40 and hsp["full_query_length"] == 100
    assert hsp["selected_query_interval"] == [20, 60]
    assert hsp["native_hsp"]["query_from"] == 21
    assert model["observed_paired_query_intervals"] == [[20, 50]]
    assert model["query_coverage"]["value"] == 0.3
    assert model["selected_query_coverage"]["value"] == 0.75


def test_selected_bound_conflict_retains_observed_subset_and_null_full_coverages():
    result = calculate(make_inputs(selected=[20, 60]))
    model = result["models"][0]
    assert not model["geometry_complete"]
    assert model["paired_query_units"] == 50
    assert model["selected_query_coverage"]["numerator"] == 30
    assert model["query_coverage"]["value"] is None and model["model_coverage"]["value"] is None
    assert "blast_profile_selected_query_bounds_conflict" in codes(result)


def test_optional_thresholds_missing_conflicting_and_measured_zero_are_distinct():
    inputs = make_inputs(hits=[synthetic_hit(bits=0)])
    inputs["profile_records"][0].update(specific_bits_threshold=None, reporting_bits_threshold=0)
    result = calculate(inputs)
    match = result["hsps"][0]["model_matches"][0]
    assert match["specific_bits_threshold"] is None and match["specific_bits_margin"] is None
    assert match["reporting_bits_threshold"] == match["reporting_bits_margin"] == 0
    inputs = make_inputs()
    conflict = deepcopy(inputs["profile_records"][0])
    conflict.update(profile_key="same_model_conflicting_threshold", specific_bits_threshold=41)
    inputs["profile_records"].append(conflict)
    result = calculate(inputs)
    assert result["hsps"][0]["model_matches"][0]["specific_bits_margin"] is None
    assert result["hsps"][0]["model_matches"][0]["reporting_bits_margin"] == 7
    assert "blast_profile_threshold_conflict" in codes(result)


@pytest.mark.parametrize("both_missing", [False, True])
def test_database_version_does_not_invent_same_release_for_threshold_margin(both_missing):
    inputs = make_inputs()
    inputs["profile_records"][0]["database_identity"]["release"] = None
    if both_missing:
        inputs["search_binding"]["database_identity"]["release"] = None
    result = calculate(inputs)
    match = result["hsps"][0]["model_matches"][0]
    assert match["specific_bits_threshold"] == 40 and match["specific_bits_margin"] is None
    assert match["reporting_bits_threshold"] == 35 and match["reporting_bits_margin"] is None
    assert "blast_profile_threshold_release_unavailable" in codes(result)
    assert match["binding_status"] == ("available" if both_missing else "unavailable")


def test_malformed_original_hsp_and_description_ordinals_do_not_compact():
    hit = synthetic_hit()
    hit["description"].insert(0, "malformed description")
    hit["hsps"].insert(0, None)
    inputs = make_inputs(hits=[None, hit])
    result = calculate(inputs)
    hsp, model = result["hsps"][0], result["models"][0]
    assert hsp["row_key"]["hit_ordinal"] == hsp["row_key"]["hsp_ordinal"] == 1
    assert hsp["source_locator"]["pointer"].endswith("/hits/1/hsps/1")
    assert inputs["profile_bindings"][0]["description_ordinal"] == 1
    assert model["binding_status"] == "available" and model["paired_query_units"] == 50
    assert not model["geometry_complete"] and model["model_coverage"]["value"] is None
    original = next(issue for issue in result["issues"] if issue["code"] == "blast_profile_collector_issue"
                    and issue["details"]["native_issue"]["code"] == "blast_hsp_object_required")
    assert original["hit_ordinal"] == 1 and original["hsp_ordinal"] == 0
    assert original["source_pointer"].endswith("/hits/1/hsps/0")


def tabular_inputs(*, delimiter="\t", malformed=True, reverse=False, format_name="tabular7", header_only=False):
    program = "rpstblastn" if reverse else "rpsblast"
    inputs = make_inputs(program, reverse=reverse)
    fields = ["qseqid", "saccver", "qlen", "slen", "qstart", "qend", "sstart", "send", "qframe",
              "length", "nident", "gaps", "bitscore", "score", "evalue", "qseq", "sseq"]
    values = ["q", "cd00001.1", "300" if reverse else "100", "100", "300" if reverse else "1",
              "151" if reverse else "50", "1", "50", "-1" if reverse else "0", "50", "50", "0",
              "42.12345678901234", "95", "0", "A" * 50, "A" * 50]
    raw = ((f"# {program.upper()} 2.17.0+\n# Query: q\n# Database: synthetic_profiles\n# Fields: " + ", ".join(fields)
            + "\n" if format_name == "tabular7" else "") + ("bad row\n" if malformed else "") + delimiter.join(values)
           + (f"\n# {2 if malformed else 1} hits found\n" if format_name == "tabular7" else "\n")).encode()
    invocation = {"execution_program": program, "scientific_mode": "database", "resource_kind": "hpc",
                  "query_kind": "sequence", "reference_kind": "profile", "request": {"synthetic_context": True},
                  "effective_options": {}, "operands": [inputs["query_binding"]["operand"]],
                  "completion": {"native_returncode": 0, "producer_complete": True}}
    artifact = {"artifact_key": "synthetic_report", "role": "tabular_report", "format": format_name,
                "fields": None if header_only else fields, "delimiter": delimiter}
    search = parse_blast_report_collection({"synthetic_report": raw}, artifacts=[artifact], invocation=invocation)["searches"][0]
    inputs["search"] = search
    inputs["search_binding"]["search_key"] = deepcopy(search["search_key"])
    binding = inputs["profile_bindings"][0]
    binding["search_key"] = deepcopy(search["search_key"])
    binding["native_description"] = {name: search["normalized"]["hits"][0]["descriptions"][0].get(name)
                                     for name in ("id", "accession", "title", "taxid")}
    return inputs


@pytest.mark.parametrize("delimiter,reverse", [("\t", False), ("@", False), ("\t", True)])
def test_tabular_original_data_row_identity_and_directional_geometry(delimiter, reverse):
    result = calculate(tabular_inputs(delimiter=delimiter, reverse=reverse))
    assert len(result["hsps"]) == 1, result["issues"]
    hsp = result["hsps"][0]
    assert hsp["row_key"]["hsp_ordinal"] == 1
    assert hsp["source_locator"]["pointer"] == "/sections/0"
    assert hsp["source_locator"]["line_numbers"] == [6]
    assert hsp["source_locator"]["data_row_ordinals"] == [1]
    assert hsp["native_components"]["native_scores"]["bit_score"] == 42.12345678901234
    assert hsp["native_components"]["native_scores"]["evalue"] == 0
    assert hsp["model_matches"][0]["binding_status"] == "available"
    assert result["models"][0]["paired_query_units"] == (150 if reverse else 50)
    assert not result["models"][0]["geometry_complete"]
    assert result["models"][0]["query_coverage"]["value"] is None
    if reverse:
        assert hsp["native_hsp"]["fields"]["qstart"] == "300"
        assert hsp["native_components"]["pairs"][0]["query_start"] == 297


@pytest.mark.parametrize("change,expected_code", [
    ("ordinal", "blast_profile_report_source_conflict"),
    ("digest", "blast_profile_archive_member_conflict"),
    ("missing_digest", "blast_profile_archive_member_unverifiable"),
    ("missing_native_digest", "blast_profile_archive_member_unverifiable"),
    ("binding_member", "blast_profile_search_key_conflict"),
])
def test_archive_custody_checks_original_member_digest_and_full_search_key(change, expected_code):
    inputs = make_inputs(archive=True)
    assert inputs["search"]["search_key"]["member_ordinal"] == 1
    if change == "ordinal":
        inputs["report_source"]["member_ordinal"] = 2
    elif change == "digest":
        inputs["report_source"]["member_sha256"] = "0" * 64
    elif change == "missing_digest":
        inputs["report_source"]["member_sha256"] = None
    elif change == "missing_native_digest":
        del inputs["search"]["normalized"]["native"]["archive_member"]["sha256"]
    else:
        inputs["profile_bindings"][0]["search_key"]["member_ordinal"] = 2
    result = calculate(inputs)
    assert expected_code in codes(result)
    assert result["hsps"][0]["native_components"]["native_scores"]["bit_score"] == 42
    assert result["hsps"][0]["model_matches"][0]["specific_bits_margin"] is None
    assert result["models"][0]["model_coverage"]["value"] is None
    assert result["hsps"][0]["source_locator"]["member_ordinal"] == 1


def test_correct_archive_member_qualifies_without_using_container_digest_as_member_digest():
    inputs = make_inputs(archive=True)
    assert inputs["report_source"]["member_sha256"] != inputs["search"]["normalized"]["native"]["sha256"]
    result = calculate(inputs)
    assert result["status"] == "complete", result["issues"]
    assert result["hsps"][0]["source_locator"]["member_sha256"] == inputs["report_source"]["member_sha256"]


@pytest.mark.parametrize("format_name,header_only", [("tabular6", False), ("tabular7", True)])
def test_exact_table_layout_supports_bare_table6_and_header_only_fields(format_name, header_only):
    inputs = tabular_inputs(format_name=format_name, header_only=header_only, malformed=False, delimiter="@")
    result = calculate(inputs)
    assert result["status"] == "complete", result["issues"]
    assert result["models"][0]["model_coverage"]["value"] == 0.5
    layout = inputs["search"]["normalized"]["native"]["table_layout"]
    assert layout["format"] == format_name and layout["delimiter"] == "@"
    assert (layout["declared_fields"] is None) is header_only


@pytest.mark.parametrize("change,code,status", [("missing", "blast_profile_table_layout_unavailable", "unavailable"),
    ("invalid", "blast_profile_table_layout_invalid", "incompatible"),
    ("conflict", "blast_profile_table_layout_conflict", "incompatible")])
def test_missing_or_conflicting_table_layout_never_triggers_guessing(change, code, status):
    inputs = tabular_inputs(delimiter="@", malformed=False)
    native = inputs["search"]["normalized"]["native"]
    if change == "missing":
        del native["table_layout"]
    else:
        native["table_layout"]["delimiter"] = "invalid" if change == "invalid" else "\t"
    result = calculate(inputs)
    assert result["status"] == status and code in codes(result)
    assert result["models"][0]["paired_query_units"] is None
    assert native["rows"][0]["fields"]["bitscore"] == "42.12345678901234"


@pytest.mark.parametrize("field,value", [("search_pointer", "/sections/-1"), ("search_pointer", "/sections/00"),
    ("search_pointer", "/sections/+0"), ("search_pointer", "/sections/0/"), ("member_ordinal", 1), ("report_index", 1)])
def test_table_search_keys_cannot_alias_original_sections(field, value):
    inputs = tabular_inputs(malformed=False)
    for key in (inputs["search"]["search_key"], inputs["search_binding"]["search_key"], inputs["profile_bindings"][0]["search_key"]):
        key[field] = value
    result = calculate(inputs)
    assert result["status"] == "incompatible"
    assert "blast_profile_native_source_conflict" in codes(result)
    assert result["hsps"] == []
    assert inputs["search"]["native"]["search"]["rows"][0]["fields"]["bitscore"] == "42.12345678901234"


def test_json_nonsearch_pointer_and_changed_native_iteration_label_are_not_accepted():
    inputs = make_inputs()
    original = deepcopy(inputs["search"]["native"]["search"])
    document = inputs["search"]["normalized"]["native"]["document"]
    document["BlastOutput2"][0]["report"]["results"]["unestablished_branch"] = deepcopy(original)
    for key in (inputs["search"]["search_key"], inputs["search_binding"]["search_key"], inputs["profile_bindings"][0]["search_key"]):
        key["search_pointer"] = "/BlastOutput2/0/report/results/unestablished_branch"
    assert calculate(inputs)["status"] == "incompatible"
    inputs = make_inputs()
    inputs["search"]["iteration"] = 9
    result = calculate(inputs)
    assert result["status"] == "incompatible"
    assert any(issue["details"].get("reason") == "native_iteration_label_conflict" for issue in result["issues"])


@pytest.mark.parametrize("stage,provenance_missing,expected", [(None, False, "unavailable"),
    ("sequence_database", False, "incompatible"), ("domain_database", True, "unavailable")])
def test_unknown_delta_stage_is_not_inferred_from_position_title_or_show_domain_option(stage, provenance_missing, expected):
    inputs = make_inputs("deltablast")
    inputs["search_binding"]["stage"] = stage
    if provenance_missing:
        inputs["search_binding"]["provenance"] = None
    result = calculate(inputs)
    assert result["status"] == expected
    hsp = result["hsps"][0]
    assert hsp["native_components"]["native_scores"]["bit_score"] == 42
    assert hsp["representative_symbol_identity"]["value"] is None
    assert hsp["model_matches"][0]["specific_bits_margin"] is None
    assert inputs["search"]["program_context"]["reference_kind"] == "sequence"
    assert inputs["search"]["stage"] is None


def test_multiple_plausible_models_do_not_select_first_or_merge_geometry():
    inputs = make_inputs()
    second = deepcopy(inputs["profile_records"][0])
    second["profile_key"] = "different_model_same_native_identifier"
    inputs["profile_records"].append(second)
    binding = deepcopy(inputs["profile_bindings"][0])
    binding["profile_key"] = second["profile_key"]
    inputs["profile_bindings"].append(binding)
    result = calculate(inputs)
    assert [match["binding_status"] for match in result["hsps"][0]["model_matches"]] == ["ambiguous", "ambiguous"]
    assert all(row["paired_model_positions"] is None and row["row_keys"] == [] for row in result["models"])
    assert result["function_components"][0]["hsp_row_keys"] == []


@pytest.mark.parametrize("change,code", [
    ("wrong_release", "blast_profile_database_identity_conflict"),
    ("unknown_release", "blast_profile_database_identity_unavailable"),
    ("wrong_version", "blast_profile_model_identifier_conflict"),
    ("different_identifier", "blast_profile_model_identifier_link_missing"),
    ("description_title", "blast_profile_native_description_conflict"),
    ("different_iteration", "blast_profile_search_key_conflict"),
])
def test_exact_model_source_associations_do_not_use_titles_taxa_or_matching_indices(change, code):
    inputs = make_inputs()
    model = inputs["profile_records"][0]
    if change == "wrong_release":
        model["database_identity"]["release"] = "another_release"
    elif change == "unknown_release":
        model["database_identity"].update(version=None, release=None)
    elif change == "wrong_version":
        model["model_identifier"]["version"] = "2"
    elif change == "different_identifier":
        model["model_identifier"]["value"] = "unproven_alias"
    elif change == "description_title":
        inputs["profile_bindings"][0]["native_description"]["title"] = "changed"
    else:
        inputs["profile_bindings"][0]["search_key"]["search_pointer"] = "/BlastOutput2/0/report/results/iterations/1/search"
    result = calculate(inputs)
    assert code in codes(result)
    assert result["models"][0]["model_coverage"]["value"] is None
    assert result["hsps"][0]["native_components"]["native_scores"]["bit_score"] == 42
    assert result["hsps"][0]["model_matches"][0]["specific_bits_margin"] is None


def test_explicit_native_general_id_namespace_is_validated():
    inputs = make_inputs()
    inputs["profile_records"][0]["model_identifier"] = {"namespace": "CDD", "value": "1001", "version": None}
    assert calculate(inputs)["models"][0]["binding_status"] == "available"
    inputs["profile_records"][0]["model_identifier"]["namespace"] = "OTHER"
    result = calculate(inputs)
    assert "blast_profile_model_identifier_conflict" in codes(result)


def test_literal_native_general_identifier_is_not_forced_into_an_invented_alias():
    inputs = make_inputs()
    inputs["profile_records"][0]["model_identifier"] = {"namespace": "CDD", "value": "gnl|CDD|1001", "version": None}
    result = calculate(inputs)
    assert result["models"][0]["binding_status"] == "available"
    assert result["hsps"][0]["model_matches"][0]["specific_bits_margin"] == 2


@pytest.mark.parametrize("hits,missing,returncode,completed,status", [
    ([], False, 0, True, "no_reported_hits"), ([], True, 0, True, "unavailable"),
    ([], False, 2, False, "unavailable"), ([], False, None, None, "unavailable"),
])
def test_actual_zero_hit_report_is_distinct_from_missing_or_failed_report(hits, missing, returncode, completed, status):
    result = calculate(make_inputs(hits=hits, missing_hits=missing, native_returncode=returncode, producer_complete=completed))
    assert result["status"] == status
    assert result["hsps"] == []


def test_empty_bare_table_is_not_an_observed_zero_hit_search():
    inputs = tabular_inputs()
    inv = {"execution_program": "rpsblast", "scientific_mode": "database", "resource_kind": "hpc", "query_kind": "sequence",
        "reference_kind": "profile", "request": {}, "effective_options": {}, "operands": [],
        "completion": {"native_returncode": 0, "producer_complete": True}}
    artifact = {"artifact_key": "synthetic_report", "role": "tabular_report", "format": "tabular6",
                "fields": ["qseqid", "sseqid", "bitscore"], "delimiter": None}
    inputs["search"] = parse_blast_report_collection({"synthetic_report": b""}, artifacts=[artifact], invocation=inv)["searches"][0]
    inputs["query_binding"] = None
    inputs["profile_records"] = inputs["profile_bindings"] = inputs["function_bindings"] = []
    assert calculate(inputs)["status"] == "unavailable"


def test_missing_geometry_retains_valid_subset_but_no_complete_coverage():
    hit = synthetic_hit()
    hit["hsps"].append({"bit_score": 45, "score": 105, "align_len": 20, "identity": 10, "gaps": 0})
    result = calculate(make_inputs(hits=[hit]))
    assert len(result["hsps"]) == 2
    assert result["hsps"][1]["native_components"]["native_scores"]["bit_score"] == 45
    model = result["models"][0]
    assert model["paired_query_units"] == model["paired_model_positions"] == 50
    assert not model["geometry_complete"]
    assert model["query_coverage"]["value"] is None and model["model_coverage"]["value"] is None


def test_unresolved_context_or_normalized_program_override_cannot_restore_geometry():
    inputs = make_inputs(report_changes={"program": "blastp", "version": "BLASTP 2.17.0+"})
    result = calculate(inputs)
    assert result["status"] == "incompatible"
    assert result["hsps"][0]["geometry_program"] is None
    assert not result["hsps"][0]["native_components"]["geometry_available"]
    assert result["hsps"][0]["native_components"]["native_scores"]["bit_score"] == 42
    inputs["search"]["program_context"]["geometry_program"] = "blastp"
    assert calculate(inputs)["status"] == "incompatible"


@pytest.mark.parametrize("changes", [{"program": ["rpsblast"]}, {"version": 42}])
def test_malformed_native_program_tokens_preserve_readable_native_scores(changes):
    result = calculate(make_inputs(report_changes=changes))
    assert len(result["hsps"]) == 1
    hsp = result["hsps"][0]
    assert hsp["native_components"]["native_scores"]["bit_score"] == 42
    assert hsp["geometry_program"] is None
    assert not hsp["native_components"]["geometry_available"]
    assert hsp["model_matches"][0]["specific_bits_margin"] is None


def test_tampered_original_row_map_is_not_manufactured_or_compacted():
    inputs = make_inputs()
    inputs["search"]["row_map"][0]["hsp_ordinals"] = [9]
    result = calculate(inputs)
    assert result["status"] == "incompatible"
    assert result["hsps"] == []
    assert "blast_profile_row_map_conflict" in codes(result)
    assert inputs["search"]["native"]["search"]["hits"][0]["hsps"][0]["bit_score"] == 42


def test_saved_sheet_recalculation_forbids_files_network_processes_and_sequence_probability(monkeypatch):
    import gene_annotation_episode.blast_database_grader as sequence_calculator
    sheet = populate_blast_profile_sheet(**make_inputs("rpstblastn", reverse=True))
    saved = json.loads(json.dumps(sheet, allow_nan=False))
    expected = calculate_blast_profile_components(saved)

    def forbidden(*args, **kwargs):
        raise AssertionError("acquisition or sequence-population calculation forbidden")

    with monkeypatch.context() as patch:
        for owner, name in [(builtins, "open"), (Path, "open"), (Path, "read_bytes"), (Path, "read_text"),
                            (socket, "socket"), (subprocess, "Popen"), (subprocess, "run"),
                            (sequence_calculator, "calculate_database_probabilities")]:
            patch.setattr(owner, name, forbidden)
        assert calculate_blast_profile_components(saved) == expected
        assert populate_blast_profile_sheet(**{key: value for key, value in saved.items() if key != "schema"}) == saved
    assert saved == sheet
    assert all(issue["code"] in ISSUE_CODES for issue in expected["issues"])


def test_functions_are_explicit_and_target_context_does_not_change_calculation():
    inputs = make_inputs()
    inputs["function_bindings"] = []
    expected = calculate(inputs)
    assert expected["function_components"] == []
    inputs["target_context"] = {"taxonomy": {"taxid": 562}, "functions": ["title must not become function"]}
    assert calculate(inputs) == expected


@pytest.mark.parametrize("case", ["blastp_gaps", "blastx_reverse"])
def test_genuine_retained_paired_bytes_only_validate_shared_geometry(case):
    root = Path(__file__).resolve().parents[1]
    directory = root / "tests/fixtures/blast_paired_native_reports"
    manifest = json.loads((directory / "manifest.json").read_text())
    measurements = []
    for format_name in ("json15", "tabular7"):
        entry = next(item for item in manifest if item["name"] == case + "_" + format_name)
        raw = (directory / entry["name"] / Path(entry["path"]).name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        collection = parse_blast_report_collection({"report": raw}, artifacts=[entry["artifact"]], invocation=entry["invocation"])
        search = collection["searches"][0]
        assert search["program_context"]["scientific_mode"] == "pairwise"
        assert search["program_context"]["execution_program"] == ("blastp" if case == "blastp_gaps" else "blastx")
        hit = search["normalized"]["hits"][0]
        measurements.append(alignment_components(hit["hsps"][0], program=search["program_context"]["geometry_program"],
            query_length=search["normalized"]["query"]["length"], reference_length=hit["length"],
            coordinate_convention="blast_json2" if format_name == "json15" else "directional"))
    assert measurements[0]["pairs"] == measurements[1]["pairs"]
    assert measurements[0]["counts"] == measurements[1]["counts"]
    assert measurements[0]["counts"]["paired_columns"] == (243 if case == "blastp_gaps" else 80)
    if case == "blastx_reverse":
        assert measurements[0]["pairs"][0]["query_start"] == 239
        assert measurements[0]["counts"]["paired_query_positions"] == 240


@pytest.fixture(scope="module")
def original_profile_calculator():
    """The preserved original source is a parity oracle, not a new producer."""
    import importlib.util
    import os
    import sys
    selected = os.environ.get("HMMER_NATIVE_ORACLE_PROFILE_BASELINE_FILE")
    path = (Path(selected) if selected else
        Path(__file__).parent / "fixtures/blast_profile_calculator_before_shared_authority.py")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "2aa12ed2ac298848454f0ce2f12734083e4fa0115cbf1c12cd64f6dd712f321f")
    name = "gene_annotation_episode._profile_authority_baseline"
    specification = importlib.util.spec_from_file_location(name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def shared_authority_inputs(case):
    """Supplied profile contexts exercise policy boundaries without a search."""
    if case == "delta_eligible":
        return make_inputs("deltablast")
    if case == "translated_reverse":
        return make_inputs("rpstblastn", reverse=True)
    if case == "overlapping_hsps":
        hit = synthetic_hit(positions=30)
        second = synthetic_hsp(start=21, positions=30, bits=43.12345678901234)
        second.update(hit_from=21, hit_to=50)
        hit["hsps"].append(second)
        return make_inputs(hits=[hit])
    if case == "selected_original_axis":
        return make_inputs(hits=[synthetic_hit(start=21, positions=30)],
            selected=[20, 60], query_length=40, full_length=100)
    if case == "selected_bounds_conflict":
        return make_inputs(selected=[20, 60])
    if case == "partial_empty_clip":
        return make_inputs(hits=[synthetic_hit(positions=10)], selected=[20, 60])
    if case == "missing_geometry":
        hit = synthetic_hit()
        hit["hsps"].append(dict(bit_score=45, score=105, align_len=20, identity=10, gaps=0))
        return make_inputs(hits=[hit])
    if case in {"native_counts_only", "missing_paired_counts", "zero_paired_columns"}:
        hit = synthetic_hit(positions=5)
        hsp = hit["hsps"][0]
        if case == "zero_paired_columns":
            hsp.update(qseq="-----", hseq="AAAAA", identity=0, positive=0, gaps=5)
        else:
            del hsp["qseq"], hsp["hseq"]
            if case == "missing_paired_counts":
                del hsp["identity"], hsp["gaps"]
        return make_inputs(hits=[hit])
    inputs = make_inputs("deltablast" if case == "delta_ineligible" else "rpsblast")
    if case == "model_length_conflict":
        inputs["profile_records"][0]["num_columns"] = 120
    elif case == "unbound_query":
        inputs["query_binding"] = None
    elif case == "missing_digest":
        inputs = make_inputs(hits=[synthetic_hit(start=21, positions=30)],
            selected=[20, 60], query_length=40, full_length=100)
        inputs["query_binding"]["sequence_sha256"] = None
    elif case == "delta_ineligible":
        inputs["search_binding"]["stage"] = None
    elif case == "zero_threshold":
        inputs = make_inputs(hits=[synthetic_hit(bits=0)])
        inputs["profile_records"][0].update(specific_bits_threshold=0, reporting_bits_threshold=0)
    else:
        assert case == "rps_eligible"
    return inputs


@pytest.mark.parametrize("case", ["rps_eligible", "delta_eligible", "translated_reverse", "overlapping_hsps",
    "selected_original_axis", "selected_bounds_conflict", "partial_empty_clip", "missing_geometry",
    "model_length_conflict", "unbound_query", "missing_digest", "native_counts_only",
    "missing_paired_counts", "zero_paired_columns", "delta_ineligible", "zero_threshold"])
def test_shared_authority_preserves_whole_original_serialized_profile_result(original_profile_calculator, case):
    inputs = shared_authority_inputs(case)
    sheet = populate_blast_profile_sheet(**inputs)
    before = json.dumps(sheet, sort_keys=True, separators=(",", ":"), allow_nan=False)
    original = original_profile_calculator.calculate_blast_profile_components(sheet)
    current = calculate_blast_profile_components(sheet)
    assert json.dumps(current, sort_keys=True, separators=(",", ":"), allow_nan=False) == json.dumps(
        original, sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert json.dumps(sheet, sort_keys=True, separators=(",", ":"), allow_nan=False) == before
    if case == "partial_empty_clip":
        model = current["models"][0]
        assert model["geometry_complete"] is False
        assert model["selected_query_coverage"] == dict(numerator=0, denominator=40, value=None, unit="fraction")
        assert model["paired_query_units"] == model["paired_model_positions"] == 10
    elif case == "zero_paired_columns":
        assert current["hsps"][0]["representative_symbol_identity"] == dict(
            numerator=0, denominator=0, value=None, unit="fraction")
    elif case == "missing_paired_counts":
        assert current["hsps"][0]["representative_symbol_identity"] == dict(
            numerator=None, denominator=None, value=None, unit="fraction")


@pytest.mark.parametrize("case", ["rps_eligible", "partial_empty_clip", "delta_ineligible"])
def test_profile_consumes_actual_common_values_and_preserves_complete_gate(monkeypatch, case):
    from gene_annotation_episode import alignment_correspondence as common
    from gene_annotation_episode import blast_profile_calculators as profile
    inputs = shared_authority_inputs(case)
    native_components, ratios, sizes, lengths, fractions = [], [], [], [], []
    original_component = profile.alignment_components
    original_ratio, original_size, original_length = common._ratio, common.interval_union_length, common.interval_length
    original_fraction, original_profile_size = profile._fraction, profile._size

    def component(*args, **kwargs):
        value = original_component(*args, **kwargs)
        native_components.append(deepcopy(value))
        return value

    def ratio(numerator, denominator):
        value = original_ratio(numerator, denominator)
        ratios.append((numerator, denominator, value))
        return value

    def size(intervals):
        # Common callers include generators; detach only this observer's input.
        intervals = list(intervals)
        value = original_size(intervals)
        sizes.append((deepcopy(intervals), value))
        return value

    def length(interval):
        value = original_length(interval)
        lengths.append((deepcopy(interval), value))
        return value

    def fraction(numerator, denominator, *, complete=True):
        start = len(ratios)
        value = original_fraction(numerator, denominator, complete=complete)
        assert ratios[start:] == ([(numerator, denominator, value["value"])] if complete else [])
        fractions.append(value)
        return value

    def profile_size(intervals):
        start = len(sizes)
        value = original_profile_size(intervals)
        assert sizes[start:] == [(deepcopy(intervals), value)]
        return value

    monkeypatch.setattr(profile, "alignment_components", component)
    monkeypatch.setattr(common, "_ratio", ratio)
    monkeypatch.setattr(common, "interval_union_length", size)
    monkeypatch.setattr(common, "interval_length", length)
    monkeypatch.setattr(profile, "_fraction", fraction)
    monkeypatch.setattr(profile, "_size", profile_size)
    result = calculate(inputs)
    assert len(native_components) == len(result["hsps"]) == 1
    assert len(fractions) == 3 * len(result["models"]), "HSP identity must be copied, without another division"
    actual = result["hsps"][0]["representative_symbol_identity"]
    assert actual["value"] == (None if case == "delta_ineligible" else native_components[0]["fractions"]["paired_identity"])
    assert actual["numerator"] == (None if case == "delta_ineligible" else native_components[0]["counts"]["identical_pairs"])
    assert actual["denominator"] == (None if case == "delta_ineligible" else native_components[0]["counts"]["paired_columns"])
    if case == "partial_empty_clip":
        assert lengths.count(([20, 60], 40)) == 2  # reported-length qualification and selected denominator
        assert ([], 0) in sizes
        assert result["models"][0]["selected_query_coverage"]["numerator"] == 0
