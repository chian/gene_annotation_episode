"""Writer-derived synthetic fixtures; no retained GenomeComparison job output.

The explicit fixture columns below are independent of parser constants. Values
exercise the published writer's associations and legacy numerical meanings.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.bvbrc_proteome_native import (
    native_schema, parse_genome_comparison, validate_native_projection,
)
from gene_annotation_episode.bvbrc_proteome_native_contracts import NativeValidationError


JSON_FORMAT = "genome_comparison_json_v1"
TSV_FORMAT = "genome_comparison_tsv_v1"
CONTRACT = {
    "id": "GenomeComparison_inspected_source_v1",
    "application_tree": "5c365e1dca2b3a8c311d7d352e862ff1442eefc9",
    "application_sha256": "4267b35bdd5ad858b833fa2b84eb794c91e95b7f5abc0628b90ec4d6a0a33c14",
    "dependency_tree": "18196fe0df123702457e4af2e0b1e0707d5f5281",
    "deployment_match": "unobserved", "deployment_evidence": [],
}
REFERENCE_HEADER = (
    "ref_genome_contig\tref_genome_gene\tref_genome_aa_length\tref_genome_patric_id\t"
    "ref_genome_locus_tag\tref_genome_gene_name\tref_genome_plfam_id\tref_genome_pgfam_id\t"
    "ref_genome_function\tref_genome_start\tref_genome_end\tref_genome_strand"
)
# Comparison 1 was skipped by the producer; 2 and 4 are actual field IDs.
COMPARISON_HEADER = (
    "comp_genome_2_hit\tcomp_genome_2_contig\tcomp_genome_2_gene\tcomp_genome_2_aa_length\t"
    "comp_genome_2_patric_id\tcomp_genome_2_locus_tag\tcomp_genome_2_gene_name\t"
    "comp_genome_2_function\tcomp_genome_2_percent_identity\tcomp_genome_2_seq_coverage\t"
    "comp_genome_4_hit\tcomp_genome_4_contig\tcomp_genome_4_gene\tcomp_genome_4_aa_length\t"
    "comp_genome_4_patric_id\tcomp_genome_4_locus_tag\tcomp_genome_4_gene_name\t"
    "comp_genome_4_function\tcomp_genome_4_percent_identity\tcomp_genome_4_seq_coverage"
)
HEADER = REFERENCE_HEADER + "\t" + COMPARISON_HEADER
NAMES = "\t".join(["reference"] + [""] * 11 + ["same display label"] + [""] * 9 + ["same display label"] + [""] * 9)
REF_A = ["ctgA", "0", "100", "refA", "locusA", "geneA", "PL1", "PG1", "native product A", "1", "303", "+"]
REF_B = ["ctgB", "2", "40", "refB", "locusB", "geneB", "PL2", "PG2", "native product B", "364", "486", "-"]
COMP_A = ["bi (<->)", "ctgS", "8", "100", "subjectA", "locS", "geneS", "native subject product", "0.875", "0.990"]
COMP_B = ["uni (->)", "ctgT", "9", "120", "subjectB", "locT", "geneT", "second product", "0.000", "0.500"]


def source(content, *, body=True, obj="yes"):
    return {
        "content": {"source_ref": "synthetic_source_001", "artifact_field": "artifact_ref",
                    "artifact_ref": "synthetic_bytes_001", "sha256": hashlib.sha256(content).hexdigest(),
                    "byte_count": len(content)},
        "body_complete": body, "object_complete": obj,
    }


def parse(content, fmt=JSON_FORMAT, *, body=True, obj="yes", contract=None):
    result = parse_genome_comparison(content, source=source(content, body=body, obj=obj),
                                    declared_format=fmt, source_contract=deepcopy(CONTRACT if contract is None else contract))
    Draft202012Validator(native_schema("NativeProjectionResult")).validate(result)
    if result["value"] is not None:
        assert validate_native_projection(result["value"]) == result["value"]
    return result


def document(rows, names=None, **extra):
    return json.dumps({"genome_names": names or {"ref_genome": "reference", "comp_genome_2": "same display label",
                      "comp_genome_4": "same display label"}, "feature_matches": rows, **extra}).encode()


def native_rows():
    fields = HEADER.split("\t")
    return [dict(zip(fields, REF_A + COMP_A + COMP_B)),
            dict(zip(fields[:12], REF_B)) | dict(zip(fields[22:], COMP_A))]


def table(*data, final_newline=True):
    # Headers sort among gene-number-zero data in the native writer.
    lines = ["\t".join(REF_A + COMP_A + COMP_B), NAMES, "\t".join(REF_B + [""] * 10 + COMP_A), HEADER]
    if data:
        lines = [NAMES, HEADER, *data]
    return ("\n".join(lines) + ("\n" if final_newline else "")).encode()


def codes(result):
    return {item["code"] for item in result["diagnostics"]}


@pytest.mark.parametrize("group,field,replacement,code", [
    ("reference_rows", "reference_row_key", "ref_genome/row/999", "reference_key_conflict"),
    ("reference_rows", "reference_row_key", "comp_genome_2/row/0", "reference_key_conflict"),
    ("associations", "association_key", "comp_genome_2/row/999", "association_key_conflict"),
    ("associations", "association_key", "comp_genome_9/row/0", "association_key_conflict"),
])
@pytest.mark.parametrize("fmt", [JSON_FORMAT, TSV_FORMAT])
def test_saved_record_keys_cannot_claim_another_native_row_or_track(group, field, replacement, code, fmt):
    value = parse(document(native_rows()) if fmt == JSON_FORMAT else table(), fmt)["value"]
    value[group][0][field] = replacement
    with pytest.raises(NativeValidationError, match="^native_projection_" + code + "$"):
        validate_native_projection(value)


def test_json_tsv_shared_native_measurements_and_actual_skipped_comparison_ids():
    js, ts = parse(document(native_rows())), parse(table(), TSV_FORMAT)
    assert js["status"] == ts["status"] == "ok"
    for result in (js, ts):
        value = result["value"]
        assert value["physical_record_count"] == 2
        assert [track["track_key"] for track in value["tracks"]] == ["ref_genome", "comp_genome_2", "comp_genome_4"]
        assert [(a["reference_row_ordinal"], a["comparison_ordinal"], a["patric_id"]["value"])
                for a in value["associations"]] == [(0, 2, "subjectA"), (0, 4, "subjectB"), (1, 4, "subjectA")]
        assert [a["percent_identity"]["value"] for a in value["associations"]] == [0.875, 0, 0.875]
        assert [a["seq_coverage"]["value"] for a in value["associations"]] == [0.99, 0.5, 0.99]
        assert value["associations"][0]["seq_coverage"]["lexeme"] == "0.990"
        assert value["reference_rows"][0]["gene"]["value"] == 0
        assert {"native_source_version_unverified", "legacy_hsp_data_not_retained"} <= codes(result)
        assert all(d["severity"] == "qualification" for d in result["diagnostics"])
    for j, t in zip(js["value"]["associations"], ts["value"]["associations"]):
        for name in ("hit", "gene", "aa_length", "patric_id", "function", "percent_identity", "seq_coverage"):
            assert (j[name]["value"], j[name]["presence"]) == (t[name]["value"], t[name]["presence"])
    # Literal physical lines 0 and 2, despite the headers being at lines 1 and 3.
    assert [r["native_pointer"] for r in ts["value"]["reference_rows"]] == ["/rows/0", "/rows/2"]
    field = ts["value"]["associations"][2]["percent_identity"]["source_field"]
    assert field == {"source_ref": "synthetic_source_001", "sha256": hashlib.sha256(table()).hexdigest(),
                     "pointer": "/rows/2/30", "row_ordinal": 2, "field_name": "comp_genome_4_percent_identity"}


def test_original_json_number_spelling_and_numeric_strings():
    content = (b'{"genome_names":{"ref_genome":"R","comp_genome_7":"C"},"feature_matches":['
               b'{"ref_genome_patric_id":"r","ref_genome_gene":-0,"ref_genome_aa_length":1.00e+02,'
               b'"comp_genome_7_patric_id":"s","comp_genome_7_percent_identity":8.750E-1,'
               b'"comp_genome_7_seq_coverage":"+0.9900"}]}')
    result = parse(content)
    assert result["status"] == "ok"
    row, association = result["value"]["reference_rows"][0], result["value"]["associations"][0]
    assert (row["gene"]["value"], row["gene"]["lexeme"]) == (0, "-0")
    assert (row["aa_length"]["value"], row["aa_length"]["lexeme"]) == (100, "1.00e+02")
    assert (association["percent_identity"]["value"], association["percent_identity"]["lexeme"]) == (0.875, "8.750E-1")
    assert (association["seq_coverage"]["value"], association["seq_coverage"]["lexeme"]) == (0.99, "+0.9900")


def test_measured_zero_omitted_null_blank_and_invalid_remain_distinct():
    rows = [{"ref_genome_patric_id": f"r{i}", "ref_genome_aa_length": raw}
            for i, raw in enumerate((0, None, "", False))]
    rows.append({"ref_genome_patric_id": "r4"})
    result = parse(document(rows))
    cells = [row["aa_length"] for row in result["value"]["reference_rows"]]
    assert [(cell["value"], cell["presence"], cell["lexeme"]) for cell in cells] == [
        (0, "value", "0"), (None, "explicit_null", None), (None, "blank", ""),
        (None, "invalid", "false"), (None, "omitted", None)]
    assert result["status"] == "partial"
    assert [row["valid"] for row in result["value"]["reference_rows"]] == [True, True, True, False, True]


@pytest.mark.parametrize("raw", [True, False, "NaN", "Infinity", "-Infinity", "25 aa", " 1", "1 ", [], {}, "1e9999", "1e-9999"])
def test_invalid_numbers_keep_valid_adjacent_cells_and_rows(raw):
    rows = native_rows()
    rows[0]["comp_genome_2_percent_identity"] = raw
    result = parse(document(rows))
    value = result["value"]
    assert result["status"] == "partial"
    assert len(value["reference_rows"]) == 2 and len(value["associations"]) == 3
    broken = value["associations"][0]
    assert broken["valid"] is False and broken["percent_identity"]["presence"] == "invalid"
    assert broken["percent_identity"]["value"] is None and broken["seq_coverage"]["value"] == 0.99
    assert value["associations"][1]["valid"] and value["associations"][2]["valid"]


@pytest.mark.parametrize("name,raw,expected", [
    ("percent_identity", "1.00000000000000000000001", "native_fraction_out_of_range"),
    ("seq_coverage", "-0.001", "native_fraction_out_of_range"),
    ("gene", -1, "native_number_invalid"), ("aa_length", "2.5", "native_number_invalid"),
])
def test_fraction_bounds_and_nonnegative_integer_lengths_are_checked_before_rounding(name, raw, expected):
    row = native_rows()[0]
    row["comp_genome_2_" + name] = raw
    result = parse(document([row]))
    assert expected in codes(result)
    assert result["value"]["associations"][0][name]["presence"] == "invalid"


def test_coordinates_are_preserved_without_inferring_genome_intervals_or_lengths():
    # The producer draws a 100-aa user sequence at 1..303, then leaves a gap.
    rows = [{"ref_genome_patric_id": "user_A", "ref_genome_contig": "UNKNOWN",
             "ref_genome_start": 1, "ref_genome_end": 303},
            {"ref_genome_patric_id": "user_B", "ref_genome_contig": "UNKNOWN",
             "ref_genome_start": 364, "ref_genome_end": 486},
            {"ref_genome_patric_id": "raw_C", "ref_genome_start": "-2.5", "ref_genome_end": "+0.25"}]
    result = parse(document(rows))
    assert result["status"] == "ok"
    assert [(row["start"]["value"], row["end"]["value"], row["aa_length"]["presence"])
            for row in result["value"]["reference_rows"]] == [(1, 303, "omitted"), (364, 486, "omitted"), (-2.5, 0.25, "omitted")]


def test_name_only_json_tracks_and_all_blank_tsv_blocks_are_not_fabricated_associations():
    js = parse(document([{"ref_genome_patric_id": "r"}]))
    ts = parse(table("\t".join(REF_A + [""] * 20)), TSV_FORMAT)
    assert js["status"] == ts["status"] == "ok"
    assert js["value"]["associations"] == ts["value"]["associations"] == []
    assert [track["materialization"] for track in js["value"]["tracks"]] == ["reference_rows", "unknown", "unknown"]
    assert [track["materialization"] for track in ts["value"]["tracks"]] == ["reference_rows", "table_field_block", "table_field_block"]
    assert "track_materialization_unknown" in codes(js)
    assert "track_materialization_unknown" not in codes(ts)


def test_emitted_null_comparison_keys_survive_as_malformed_association():
    result = parse(document([{"ref_genome_patric_id": "r", "comp_genome_2_patric_id": None}]))
    assert len(result["value"]["associations"]) == 1
    association = result["value"]["associations"][0]
    assert association["patric_id"]["presence"] == "explicit_null" and association["valid"] is False


def test_native_source_order_not_names_independent_sort_or_compressed_track_numbers():
    rows = [{"ref_genome_patric_id": "r9", "comp_genome_4_patric_id": "s4", "comp_genome_2_patric_id": "s2"},
            {"ref_genome_patric_id": "r1", "comp_genome_2_patric_id": "other"}]
    names = {"comp_genome_4": "same", "ref_genome": "same", "comp_genome_2": "same", "comp_genome_1": "skipped"}
    result = parse(document(rows, names))
    assert [t["track_key"] for t in result["value"]["tracks"]] == list(names)
    assert [(a["reference_row_ordinal"], a["comparison_ordinal"], a["patric_id"]["value"])
            for a in result["value"]["associations"]] == [(0, 4, "s4"), (0, 2, "s2"), (1, 2, "other")]
    assert result["value"]["tracks"][3]["materialization"] == "unknown"


def test_missing_display_track_preserves_known_association_and_adds_qualification():
    result = parse(document([{"ref_genome_patric_id": "r", "comp_genome_9_patric_id": "s"}], {"ref_genome": "R"}))
    assert result["value"]["associations"][0]["comparison_ordinal"] == 9
    assert result["value"]["tracks"][1]["display_name"] is None
    assert "native_comparison_track_missing" in codes(result)


def test_malformed_json_rows_keep_every_original_ordinal_and_later_valid_measurement():
    result = parse(document([native_rows()[0], 7, None, {}, native_rows()[1]]))
    assert result["status"] == "partial"
    value = result["value"]
    assert value["physical_record_count"] == 5
    assert [row["row_ordinal"] for row in value["reference_rows"]] == list(range(5))
    assert [row["valid"] for row in value["reference_rows"]] == [True, False, False, False, True]
    assert value["associations"][-1]["reference_row_ordinal"] == 4
    assert value["associations"][-1]["percent_identity"]["value"] == 0.875


def test_unknown_fields_have_escaped_original_paths_and_preserved_binding():
    rows = native_rows()
    rows[0]["extra/~field"] = {"unmodeled": [1, 2]}
    content = document(rows, extra_top={"unused": True})
    result = parse(content)
    assert result["status"] == "partial"
    assert result["value"]["unsupported_field_paths"] == ["/extra_top", "/feature_matches/0/extra~1~0field"]
    assert result["value"]["source"] == source(content)
    assert result["value"]["reference_rows"][0]["valid"] is False
    assert result["value"]["reference_rows"][1]["valid"] is True
    assert result["value"]["associations"][0]["percent_identity"]["value"] == 0.875


def test_unknown_empty_json_member_has_a_real_pointer_without_invalid_source_field_name():
    result = parse(document([{"ref_genome_patric_id": "r", "": 23}]))
    assert result["status"] == "partial"
    assert result["value"]["unsupported_field_paths"] == ["/feature_matches/0/"]
    diagnostic = result["value"]["reference_rows"][0]["diagnostics"][0]
    assert diagnostic["source_fields"][0]["pointer"] == "/feature_matches/0/"
    assert diagnostic["source_fields"][0]["field_name"] is None


@pytest.mark.parametrize("content,path", [
    (b'{"genome_names":{"ref_genome":"a","ref_genome":"b"},"feature_matches":[]}', "/genome_names/ref_genome"),
    (b'{"genome_names":{"ref_genome":"a"},"feature_matches":[{"ref_genome_patric_id":"r","ref_genome_patric_id":"s"}]}',
     "/feature_matches/0/ref_genome_patric_id"),
    (b'{"genome_names":{"ref_genome":"a"},"feature_matches":[],"extra":{"a/b":1,"a/b":2}}', "/extra/a~1b"),
])
def test_duplicate_json_members_are_rejected_before_any_projection(content, path):
    result = parse(content)
    assert result["status"] == "invalid" and result["value"] is None
    assert result["diagnostics"][0]["code"] == "duplicate_json_member"
    assert result["diagnostics"][0]["path"] == path


def test_duplicate_reference_ids_remain_separate_rows_with_ambiguity_qualification():
    rows = native_rows()
    rows[1]["ref_genome_patric_id"] = rows[0]["ref_genome_patric_id"]
    result = parse(document(rows))
    assert len(result["value"]["reference_rows"]) == 2
    assert len({row["reference_row_key"] for row in result["value"]["reference_rows"]}) == 2
    assert len(result["value"]["associations"]) == 3
    assert all("native_duplicate_reference_id" in {d["code"] for d in row["diagnostics"]}
               for row in result["value"]["reference_rows"])


@pytest.mark.parametrize("body,obj,complete,status", [
    (True, "yes", "complete_document", "ok"),
    (False, "yes", "partial_or_unknown_artifact", "partial"),
    (True, "no", "partial_or_unknown_artifact", "partial"),
    (True, "unknown", "partial_or_unknown_artifact", "partial"),
    (False, "unknown", "partial_or_unknown_artifact", "partial"),
])
def test_valid_json_document_has_exact_body_object_completeness(body, obj, complete, status):
    result = parse(document(native_rows()), body=body, obj=obj)
    assert result["status"] == status and result["value"]["projection_completeness"] == complete
    assert result["value"]["source"]["object_complete"] == obj
    assert ("source_bytes_incomplete" in codes(result)) == (not body)
    assert ("source_object_incomplete" in codes(result)) == (obj != "yes")
    assert len(result["value"]["associations"]) == 3


@pytest.mark.parametrize("body,obj", [(False, "yes"), (True, "no"), (True, "unknown")])
def test_partial_tsv_excludes_unterminated_tail_and_preserves_complete_prefix(body, obj):
    good = "\t".join(REF_A + COMP_A + COMP_B)
    content = table(good) + b"partial final\t12\t\xe2\x82"
    result = parse(content, TSV_FORMAT, body=body, obj=obj)
    assert result["status"] == "partial"
    assert result["value"]["projection_completeness"] == "complete_prefix_only"
    assert result["value"]["physical_record_count"] == 1
    assert len(result["value"]["associations"]) == 2
    assert result["value"]["source"]["content"]["byte_count"] == len(content)
    assert result["value"]["source"]["content"]["sha256"] == hashlib.sha256(content).hexdigest()


def test_complete_no_newline_tsv_retains_final_data_row():
    content = table("\t".join(REF_A + COMP_A + COMP_B), final_newline=False)
    result = parse(content, TSV_FORMAT)
    assert result["status"] == "ok" and result["value"]["physical_record_count"] == 1
    assert len(result["value"]["associations"]) == 2
    prefix = parse(content, TSV_FORMAT, obj="unknown")
    assert prefix["status"] == "partial" and prefix["value"]["physical_record_count"] == 0


def test_tsv_malformed_neighbors_preserve_literal_cells_and_physical_locations():
    good_a = "\t".join(REF_A + COMP_A + [""] * 10)
    broken = "\t".join(REF_B + COMP_B + [""] * 10 + ["extra tab value"])
    short = "\t".join(["short contig", "3", "25", "short-id"])
    good_b = "\t".join(REF_B + [""] * 10 + COMP_A)
    content = table(good_a, broken, short, good_b)
    result = parse(content, TSV_FORMAT)
    value = result["value"]
    assert result["status"] == "partial" and value["physical_record_count"] == 4
    assert [row["valid"] for row in value["reference_rows"]] == [True, False, False, True]
    assert value["reference_rows"][2]["aa_length"]["value"] == 25
    assert value["reference_rows"][2]["start"]["presence"] == "omitted"
    assert value["associations"][1]["valid"] is False
    assert value["associations"][1]["seq_coverage"]["value"] == 0.5
    assert value["associations"][-1]["reference_row_ordinal"] == 3
    assert value["associations"][-1]["native_pointer"] == "/rows/5"
    assert value["unsupported_field_paths"] == ["/rows/3/32"]


def test_unescaped_embedded_newline_is_two_invalid_physical_rows_not_repaired():
    cells = REF_A + COMP_A + [""] * 10
    cells[8] = "unescaped\nproduct"
    result = parse(table("\t".join(cells), "\t".join(REF_B + [""] * 20)), TSV_FORMAT)
    assert result["status"] == "partial"
    assert result["value"]["physical_record_count"] == 3
    assert [row["valid"] for row in result["value"]["reference_rows"]] == [False, False, True]
    assert result["value"]["reference_rows"][0]["function"]["value"] == "unescaped"
    assert result["value"]["reference_rows"][1]["contig"]["value"] == "product"


@pytest.mark.parametrize("mutator", [
    lambda body: body + HEADER.encode() + b"\n",
    lambda body: body + NAMES.encode() + b"\n",
    lambda body: body.replace(b"comp_genome_2_hit", b"comp_genome_1_hit", 1),
    lambda body: body.replace(b"ref_genome_contig\tref_genome_gene", b"ref_genome_gene\tref_genome_contig", 1),
])
def test_missing_or_ambiguous_or_incompatible_table_headers_are_fatal(mutator):
    result = parse(mutator(table()), TSV_FORMAT)
    assert result["status"] == "invalid" and result["value"] is None
    assert "native_table_header_invalid" in codes(result)


@pytest.mark.parametrize("content,expected", [
    (b"\xff", "native_encoding_invalid"), (b'{"genome_names":', "native_json_invalid"),
    (b'{"genome_names":{"ref_genome":"R"},"feature_matches":[NaN]}', "native_json_invalid"),
    (b'[]', "native_schema_incompatible"),
    (b'{"genome_names":{},"feature_matches":[]}', "native_schema_incompatible"),
    (b'{"genome_names":{"ref_genome":"R"},"feature_matches":{}}', "native_schema_incompatible"),
])
def test_invalid_document_has_no_salvaged_projection(content, expected):
    result = parse(content, body=False, obj="unknown")
    assert result["status"] == "invalid" and result["value"] is None
    assert codes(result) == {expected}


def test_invalid_encoding_in_complete_tsv_line_is_fatal_even_when_artifact_partial():
    content = table("\t".join(REF_A + [""] * 20)) + b"\xff\n"
    for body, obj in [(True, "yes"), (False, "unknown")]:
        result = parse(content, TSV_FORMAT, body=body, obj=obj)
        assert result["value"] is None and "native_encoding_invalid" in codes(result)


@pytest.mark.parametrize("field,replacement", [("sha256", "0" * 64), ("byte_count", 0)])
def test_content_binding_mismatch_is_rejected_before_decoding(field, replacement):
    content = b"\xff"
    binding = source(content)
    binding["content"][field] = replacement
    result = parse_genome_comparison(content, source=binding, declared_format=JSON_FORMAT, source_contract=CONTRACT)
    assert result["status"] == "invalid" and result["value"] is None
    assert codes(result) == {"artifact_digest_mismatch"}


@pytest.mark.parametrize("field,replacement", [("object_complete", True), ("object_complete", "maybe"), ("body_complete", 1)])
def test_source_three_state_completeness_does_not_accept_boolean_substitution(field, replacement):
    content = document([])
    binding = source(content)
    binding[field] = replacement
    result = parse_genome_comparison(content, source=binding, declared_format=JSON_FORMAT, source_contract=CONTRACT)
    assert result["value"] is None and codes(result) == {"artifact_binding_unqualified"}


@pytest.mark.parametrize("field,value", [("application_tree", "unknown"), ("id", "Other_v1"), ("deployment_match", "different")])
def test_other_source_version_is_incompatible_not_silently_reinterpreted(field, value):
    contract = deepcopy(CONTRACT)
    contract[field] = value
    result = parse(document(native_rows()), contract=contract)
    assert result["value"] is None and codes(result) == {"native_schema_incompatible"}
    assert result["requirements"][0]["required_input"] == "native_producer_version"


def test_declared_deployment_evidence_is_preserved_but_not_authenticated():
    contract = deepcopy(CONTRACT)
    contract.update(deployment_match="demonstrated", deployment_evidence=[{
        "source_ref": "caller_supplied_evidence", "sha256": "a" * 64, "pointer": "/version",
        "row_ordinal": None, "field_name": "version"}])
    result = parse(document([]), contract=contract)
    assert result["status"] == "ok" and result["value"]["source_contract"] == contract
    assert "native_source_version_unverified" not in codes(result)
    assert "legacy_hsp_data_not_retained" in codes(result)


def test_empty_complete_json_is_zero_observed_records_not_search_completion():
    result = parse(document([]))
    assert result["status"] == "ok" and result["value"]["physical_record_count"] == 0
    assert result["value"]["reference_rows"] == result["value"]["associations"] == []
    assert {"legacy_hsp_data_not_retained", "track_materialization_unknown"} <= codes(result)


def test_detached_sources_schema_projection_and_separate_parse_calls():
    content = document(native_rows())
    supplied, contract = source(content), deepcopy(CONTRACT)
    first = parse_genome_comparison(content, source=supplied, declared_format=JSON_FORMAT, source_contract=contract)
    validated = validate_native_projection(first["value"])
    supplied["content"]["source_ref"] = "changed"
    contract["deployment_match"] = "different"
    validated["associations"][0]["percent_identity"]["value"] = 0
    schema = native_schema("NativeProjection")
    schema["$defs"]["NativeProjection"]["properties"].clear()
    assert first["value"]["source"]["content"]["source_ref"] == "synthetic_source_001"
    assert first["value"]["source_contract"]["deployment_match"] == "unobserved"
    assert first["value"]["associations"][0]["percent_identity"]["value"] == 0.875
    assert parse(content)["value"] == first["value"]
    assert native_schema("NativeProjection")["$defs"]["NativeProjection"]["properties"]


@pytest.mark.parametrize("mutation", [
    lambda v: v.update(physical_record_count=99),
    lambda v: v["reference_rows"][0].update(row_ordinal=1),
    lambda v: v["associations"][0].update(reference_row_ordinal=99),
    lambda v: v["associations"][0].update(comparison_ordinal=1),
    lambda v: v["associations"][0]["percent_identity"]["source_field"].update(source_ref="artifact-instead-of-source"),
    lambda v: v["associations"][0]["percent_identity"]["source_field"].update(pointer="/wrong"),
    lambda v: v["associations"][0]["percent_identity"].update(value=0.5),
    lambda v: v["associations"][0]["percent_identity"].update(value=True),
    lambda v: v["associations"][0]["percent_identity"].update(value=float("nan")),
    lambda v: v["tracks"][1].update(materialization="unknown"),
    lambda v: v["source"].update(object_complete="unknown"),
    lambda v: v.update(extra_field="not part of the frozen shape"),
])
def test_projection_validator_rejects_broken_relationships_and_non_native_values(mutation):
    value = parse(document(native_rows()))["value"]
    mutation(value)
    with pytest.raises(NativeValidationError, match="native_projection_"):
        validate_native_projection(value)


def test_unsupported_contract_and_format_fail_explicitly():
    with pytest.raises(ValueError, match="unknown_proteome_native_contract"):
        native_schema("ProteomeSheet")
    content = document([])
    result = parse_genome_comparison(content, source=source(content), declared_format="blast_json2", source_contract=CONTRACT)
    assert result["value"] is None and codes(result) == {"native_schema_incompatible"}


@pytest.mark.parametrize("mutation", [
    lambda v: v["tracks"][0]["source_fields"][0].update(pointer="/rows/90/0", row_ordinal=90),
    lambda v: v["tracks"][1]["source_fields"][1].update(pointer="/rows/90/12", row_ordinal=90),
    lambda v: v["reference_rows"][0]["locus_tag"].update(value=None, presence="explicit_null"),
])
def test_tsv_projection_validator_checks_native_header_locations_and_cell_states(mutation):
    value = parse(table(), TSV_FORMAT)["value"]
    mutation(value)
    with pytest.raises(NativeValidationError, match="native_projection_"):
        validate_native_projection(value)


def test_projection_validator_rejects_removed_duplicate_qualification():
    rows = [{"ref_genome_patric_id": "same"}, {"ref_genome_patric_id": "same"}]
    value = parse(document(rows))["value"]
    value["reference_rows"][1]["diagnostics"] = []
    with pytest.raises(NativeValidationError, match="native_projection_duplicate_reference_qualification_missing"):
        validate_native_projection(value)


def test_tsv_crlf_is_a_line_terminator_and_blank_cells_are_not_null():
    result = parse(table("\t".join(REF_A + [""] * 20)).replace(b"\n", b"\r\n"), TSV_FORMAT)
    assert result["status"] == "ok" and result["value"]["physical_record_count"] == 1
    assert result["value"]["associations"] == []


def test_string_missingness_preserves_empty_text_and_omitted_null_invalid_values():
    rows = [{"ref_genome_patric_id": "r0", "ref_genome_locus_tag": ""},
            {"ref_genome_patric_id": "r1", "ref_genome_locus_tag": None},
            {"ref_genome_patric_id": "r2", "ref_genome_locus_tag": 0},
            {"ref_genome_patric_id": "r3"}]
    result = parse(document(rows))
    assert [(r["locus_tag"]["value"], r["locus_tag"]["presence"]) for r in result["value"]["reference_rows"]] == [
        ("", "blank"), (None, "explicit_null"), (None, "invalid"), (None, "omitted")]


def test_invalid_native_hit_category_is_not_encoded_as_confidence_or_valid_selection():
    row = native_rows()[0]
    row["comp_genome_2_hit"] = "ortholog"
    result = parse(document([row]))
    bad = result["value"]["associations"][0]
    assert bad["hit"]["value"] == "ortholog" and bad["hit"]["presence"] == "value"
    assert bad["valid"] is False and "native_hit_category_invalid" in codes(result)
    assert bad["percent_identity"]["value"] == 0.875


def test_no_io_network_native_program_model_or_existing_calculator_dependencies(monkeypatch):
    # Modules and their package schemas are already imported. Calls must be pure.
    def forbidden(*args, **kwargs):
        raise AssertionError("parser/validator attempted IO or scientific execution")
    content = document(native_rows())
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = parse(content)
    assert result["value"]["associations"][0]["percent_identity"]["value"] == 0.875


def test_packaged_schema_is_the_exact_accepted_002_contract():
    import gene_annotation_episode.bvbrc_proteome_native_contracts as contracts
    path = Path(contracts.__file__).with_name("bvbrc_proteome_native_schemas.json")
    # Prospective request-content amendment, preserving the accepted contract.
    original = json.loads(path.read_text())
    enum = original["$defs"]["ContentBinding"]["properties"]["artifact_field"]["enum"]
    assert enum == ["artifact_ref", "text_ref", "stdout_ref", "stderr_ref", "request_ref"]
    assert enum.pop() == "request_ref"
    restored = (json.dumps(original, indent=2, ensure_ascii=False) + "\n").encode()
    assert hashlib.sha256(restored).hexdigest() == "c84fecffe0170b7c77948f411593a55ae63e902f976e8a42463a0053c1a1f01d"
    definitions = json.loads(path.read_text())["$defs"]
    assert len(definitions) == 16
    for name in definitions:
        Draft202012Validator.check_schema(native_schema(name))
