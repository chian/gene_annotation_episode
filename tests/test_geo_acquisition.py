"""Engineered retained SOFT controls; no GEO download or data analysis occurs."""
from copy import deepcopy
import gzip
import hashlib

import pytest

from gene_annotation_episode import geo_acquisition as geo


SOURCE = "source_" + "b" * 24
SOFT = ("^SERIES = GSE1\r\n!Series_title = Original μ title\r\n"
    "!Series_sample_id = GSM1\r\n!Series_sample_id = GSM1\r\n!Series_sample_id = GSM2\r\n"
    "!Series_platform_id = GPL1\r\n!Series_platform_id = GPL2\r\n"
    "^SAMPLE = GSM1\r\n!Sample_platform_id = GPL1\r\n!Sample_series_id = GSE1\r\n"
    "!Sample_characteristics_ch1 = condition: supplied\r\n!Unknown_field = original = value\r\n"
    "#ID_REF = native probe identifier\r\n#VALUE = scale and units undeclared\r\n"
    "!sample_table_begin\r\nID_REF\tVALUE\tCALL\r\np1\t0\t\r\np1\t1e-9999\tNA\r\n!sample_table_end\r\n"
    "^PLATFORM = GPL1\r\n#ID = native platform probe\r\n!platform_table_begin\r\nID\tGene Symbol\r\np1\tGeneA\r\np1\tOtherLabel\r\n!platform_table_end\r\n"
    "^PLATFORM = GPL2\r\n!platform_table_begin\r\nID\tGene Symbol\r\np1\tGeneB\r\n!platform_table_end\r\n"
    "^SAMPLE = GSM2\r\n!Sample_platform_id = GPL2\r\n!sample_table_begin\r\nID_REF\tVALUE\r\np1\t\r\n!sample_table_end\r\n"
    "^UNRECOGNIZED = literal\r\n!Unrecognized_value = retain all\r\n").encode("utf-8")


def parse(raw=SOFT, *, encoding="identity", complete=True, limit=geo.MAX_DECODED_BYTES, **changes):
    arguments = dict(source_ref=SOURCE, artifact_ref="artifact_" + hashlib.sha256(raw).hexdigest(),
        content_encoding=encoding, body_complete=complete, max_decoded_bytes=limit)
    arguments.update(changes)
    return geo.parse_geo_soft(raw, **arguments)


def codes(value):
    return [row["code"] for row in value["issues"]]


def test_all_ordered_entities_repeated_fields_platforms_probes_and_native_cells_survive_without_pivot():
    value = parse()
    assert value["representation_state"] == "complete" and value["native_parse_complete"] is True
    assert value["matching_population_coverage"] == "unknown"
    assert [(row["entity_type"], row["identifier"]) for row in value["entities"]] == [
        ("SERIES", "GSE1"), ("SAMPLE", "GSM1"), ("PLATFORM", "GPL1"),
        ("PLATFORM", "GPL2"), ("SAMPLE", "GSM2"), ("UNRECOGNIZED", "literal")]
    series, sample, platform, other_platform, other_sample, unknown = value["entities"]
    assert [row["value"] for row in series["attributes"] if row["name"] == "Series_sample_id"] == [" GSM1", " GSM1", " GSM2"]
    table, = sample["tables"]
    assert table["header"]["cells"] == ["ID_REF", "VALUE", "CALL"]
    assert [row["cells"] for row in table["rows"]] == [["p1", "0", ""], ["p1", "1e-9999", "NA"]]
    assert table["probe_identifier_column"] == platform["tables"][0]["probe_identifier_column"] == 0
    assert other_sample["tables"][0]["rows"][0]["cells"] == ["p1", ""]
    assert platform["tables"][0]["rows"][0]["cells"] == ["p1", "GeneA"]
    assert other_platform["tables"][0]["rows"][0]["cells"] == ["p1", "GeneB"]
    assert unknown["attributes"][0]["value"] == " retain all"
    assert value["native_text"].encode("utf-8") == SOFT
    assert "matrix" not in value and "units" not in value and "replicates" not in value


def test_native_relations_retain_explicit_sample_platform_context_and_repeated_occurrences():
    value = parse()
    relations = value["relations"]
    assert [(row["to_identifier"], row["target_entity_ordinals"]) for row in relations
        if row["native_relation"] == "Series_sample_id"] == [("GSM1", [1]), ("GSM1", [1]), ("GSM2", [4])]
    assert [(row["from_identifier"], row["to_identifier"], row["target_entity_ordinals"]) for row in relations
        if row["native_relation"] == "Sample_platform_id"] == [("GSM1", "GPL1", [2]), ("GSM2", "GPL2", [3])]
    for relation in relations:
        ordinal = relation["from_entity_ordinal"]
        assert value["entities"][ordinal]["identifier"] == relation["from_identifier"]
    # Identical p1 labels on different platforms never establish a gene join.
    assert not any(row["native_relation"] == "gene" for row in relations)


def test_utf8_byte_locations_address_original_decoded_lines_without_numeric_conversion():
    value = parse()
    raw = value["native_text"].encode("utf-8")
    for entity in value["entities"]:
        assert raw[entity["byte_start"]:entity["byte_end"]].startswith(("^"+entity["entity_type"]).encode())
        for table in entity["tables"]:
            for row in [table["header"], *table["rows"]]:
                actual = raw[row["byte_start"]:row["byte_end"]].decode("utf-8").rstrip("\r\n")
                assert actual.split("\t") == row["cells"]


@pytest.mark.parametrize("encoding", ["identity", "gzip"])
def test_explicit_content_encoding_and_capture_completeness_are_separate(encoding):
    raw = gzip.compress(SOFT) if encoding == "gzip" else SOFT
    value = parse(raw, encoding=encoding, complete=False)
    assert value["native_text"].encode("utf-8") == SOFT and value["native_parse_complete"] is True
    assert value["decoding"]["decoded_complete"] is True
    assert value["capture"]["body_complete"] is False and "capture_not_complete" in codes(value)
    assert value["representation_state"] == "partial"
    assert value["decoding"]["total_decoded_bytes"] == len(SOFT)
    assert value["capture"]["retained_raw_bytes"] == len(raw)


def test_concatenated_gzip_members_are_all_retained_in_original_order():
    cut = 100
    raw = gzip.compress(SOFT[:cut]) + gzip.compress(SOFT[cut:])
    value = parse(raw, encoding="gzip")
    assert value["decoding"]["completed_gzip_members"] == 2
    assert value["native_text"].encode("utf-8") == SOFT
    assert value["decoding"]["decoded_complete"] is True


def test_exact_decoded_limit_allows_empty_following_gzip_member_without_losing_its_completion():
    raw = gzip.compress(SOFT[:100]) + gzip.compress(SOFT[100:]) + gzip.compress(b"")
    value = parse(raw, encoding="gzip", limit=len(SOFT))
    assert value["decoding"]["completed_gzip_members"] == 3
    assert value["decoding"]["decoded_complete"] is True and value["decoding"]["decoded_limit_reached"] is False
    assert value["native_text"].encode("utf-8") == SOFT


@pytest.mark.parametrize("encoding", ["identity", "gzip"])
def test_declared_decoded_limit_bounds_inflation_and_never_fabricates_total_or_complete_parse(encoding):
    raw = b"^SERIES = GSE1\n!Series_title = " + b"A" * (1024 * 1024)
    captured = gzip.compress(raw) if encoding == "gzip" else raw
    value = parse(captured, encoding=encoding, limit=128)
    state = value["decoding"]
    assert state["retained_decoded_bytes"] == 128 and state["decoded_limit_reached"] is True
    assert state["observed_decoded_bytes_lower_bound"] >= 129 and state["total_decoded_bytes"] is None
    assert state["decoded_complete"] is False and value["native_parse_complete"] is False
    assert len(value["native_text"].encode("utf-8")) == 128
    assert "decoded_byte_limit_reached" in codes(value)


@pytest.mark.parametrize("raw, expected", [(b"not gzip", "invalid_gzip"), (gzip.compress(SOFT)[:-5], "incomplete_gzip")])
def test_invalid_or_incomplete_gzip_preserves_decode_prefix_without_calling_it_a_complete_document(raw, expected):
    value = parse(raw, encoding="gzip")
    assert value["decoding"]["error"] == expected and expected in codes(value)
    assert value["decoding"]["decoded_complete"] is False and value["native_parse_complete"] is False
    if value["native_text"]:
        assert SOFT.startswith(value["native_text"].encode("utf-8"))


@pytest.mark.parametrize("raw, expected", [(b"", "native_entities_unavailable"), (b"\xff", "invalid_native_utf8"),
    (b"ordinary text\n", "native_entities_unavailable")])
def test_missing_or_undecodable_entities_remain_unknown_instead_of_observed_zero(raw, expected):
    value = parse(raw)
    assert value["entity_count"] is None and value["parse_state"] == "unavailable"
    assert expected in codes(value)


@pytest.mark.parametrize("tail, expected", [("ID_REF\tVALUE\np1\t0\n", "native_table_not_closed"),
    ("ID_REF\tVALUE\np1\n!sample_table_end\n", "native_row_width_conflict"),
    ("ID_REF\tVALUE\np1\t0\n!platform_table_end\n", "native_table_marker_conflict"),
    ("ID_REF\tID_REF\tVALUE\np1\tp2\t0\n!sample_table_end\n", "native_probe_column_ambiguous")])
def test_partial_or_contradictory_table_geometry_keeps_actual_rows(tail, expected):
    raw = ("^SAMPLE = GSM1\n!sample_table_begin\n" + tail).encode()
    value = parse(raw, complete=False)
    assert expected in codes(value) and value["native_parse_complete"] is False
    assert value["entities"][0]["tables"][0]["rows"]
    assert value["representation_state"] == "partial"


def test_repeated_entity_ids_keep_all_targets_without_a_first_or_last_winner():
    raw = b"^SERIES = GSE1\n!Series_sample_id = GSM1\n^SAMPLE = GSM1\n!Sample_title = first\n^SAMPLE = GSM1\n!Sample_title = second\n"
    value = parse(raw)
    assert value["entity_count"] == 3 and value["relations"][0]["target_entity_ordinals"] == [1, 2]
    assert [row["attributes"][0]["value"] for row in value["entities"][1:]] == [" first", " second"]
    assert "native_entity_identity_repeated" in codes(value)


def test_unknown_table_context_keeps_rows_without_assigning_sample_probe_semantics():
    raw = b"^SAMPLE = GSM1\n!unknown_table_begin\nID_REF\tVALUE\np1\t0\n!unknown_table_end\n"
    value = parse(raw)
    table = value["entities"][0]["tables"][0]
    assert table["rows"][0]["cells"] == ["p1", "0"] and table["probe_identifier_column"] is None
    assert "native_table_entity_context_conflict" in codes(value)


def test_decoded_limit_inside_utf8_retains_exact_byte_identity_and_unknown_parsed_population():
    raw = b"^SERIES = GSE1\n!Series_title = " + "μ".encode("utf-8")
    value = parse(raw, limit=len(raw)-1)
    assert value["decoding"]["decoded_sha256"] == hashlib.sha256(raw[:-1]).hexdigest()
    assert value["native_text"] is None and value["entity_count"] is None
    assert "decoded_byte_limit_reached" in codes(value) and "invalid_native_utf8" in codes(value)


def test_metadata_values_and_non_cr_lf_unicode_separators_are_not_flattened_or_split():
    raw = "^SAMPLE = GSM1\n!Sample_characteristics_ch1 = x: a\u2028b\vvalue = literal\n".encode()
    value = parse(raw)
    assert value["entities"][0]["attributes"][0]["value"] == " x: a\u2028b\vvalue = literal"
    assert value["native_text"].encode() == raw


@pytest.mark.parametrize("changes", [dict(content_encoding="auto"), dict(content_encoding=True), dict(body_complete=1),
    dict(max_decoded_bytes=True), dict(max_decoded_bytes=0), dict(max_decoded_bytes=geo.MAX_DECODED_BYTES + 1),
    dict(source_ref=SOURCE + "\n"), dict(artifact_ref="artifact_" + "0" * 64)])
def test_input_contract_requires_actual_bytes_closed_refs_explicit_encoding_and_limits(changes):
    with pytest.raises(ValueError): parse(**changes)


@pytest.mark.parametrize("change", ["cells", "relation", "count", "decode", "extra"])
def test_closed_dto_validation_binds_tables_relations_and_counts_to_exact_retained_text(change):
    value = parse()
    if change == "cells": value["entities"][1]["tables"][0]["rows"][0]["cells"][1] = "99"
    elif change == "relation": value["relations"][0]["to_identifier"] = "GSM999"
    elif change == "count": value["entity_count"] = 0
    elif change == "decode": value["decoding"]["decoded_sha256"] = "0" * 64
    else: value["extra"] = True
    with pytest.raises(ValueError): geo.validate_geo_result(value)


def test_result_schema_is_detached_and_provisional_transport_contract_is_not_exposed():
    value = parse()
    assert geo.validate_geo_result(deepcopy(value)) == value
    schema = geo.geo_result_schema(); schema.clear()
    assert geo.geo_result_schema()["additionalProperties"] is False
    assert not hasattr(geo, "ARGUMENTS_SCHEMA") and not hasattr(geo, "geo_request_spec")
