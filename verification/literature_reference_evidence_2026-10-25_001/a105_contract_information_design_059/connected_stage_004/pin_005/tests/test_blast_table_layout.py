"""Supplied table layouts survive parsing without reconstruction guesses."""
from copy import deepcopy

import pytest

from test_blast_report_collection import (
    FIELDS, collect, descriptor, invocation, operand, trow,
)


def layout(search):
    return search["normalized"]["native"]["table_layout"]


def test_custom_delimiter_and_literal_hash_do_not_change_original_format():
    text = trow(subject="s#1") + trow("q2") + trow()
    result = collect(raw=text.replace("\t", "@").encode(),
        artifact=descriptor(format="tabular6", fields=FIELDS, delimiter="@"),
        inv=invocation(operands=[operand(), operand("q2")]))
    assert [s["search_key"]["search_pointer"] for s in result["searches"]] == [
        "/sections/0", "/sections/1", "/sections/2"]
    assert [s["native"]["line_numbers"] for s in result["searches"]] == [[1], [2], [3]]
    for search in result["searches"]:
        assert layout(search) == {"format": "tabular6", "declared_fields": FIELDS, "delimiter": "@"}
        assert search["normalized"]["hits"][0]["hsps"][0]["query_to"] == 4
    assert result["searches"][0]["native"]["search"]["rows"][0]["values"][1] == "s#1"


def test_header_fields_are_distinct_from_absent_caller_declaration():
    raw = ("# BLASTP 2.17.0+\n# Query: q\n# Fields: " + ", ".join(FIELDS)
           + "\n# 1 hits found\n" + trow()).encode()
    search, = collect(raw=raw, artifact=descriptor(format="tabular7"))["searches"]
    assert layout(search) == {"format": "tabular7", "declared_fields": None, "delimiter": "\t"}
    assert search["native"]["search"]["fields"] == FIELDS
    assert search["reporting"]["native_hit_count"] == 1


def test_original_field_declaration_is_retained_before_std_expansion():
    raw = b"q\ts\t100\t4\t0\t0\t1\t4\t1\t4\t1e-8\t20\n"
    search, = collect(raw=raw, artifact=descriptor(format="tabular6", fields=["STD"]))["searches"]
    assert layout(search)["declared_fields"] == ["STD"]
    assert len(search["native"]["search"]["fields"]) == 12
    assert search["normalized"]["hits"][0]["hsps"][0]["bit_score"] == 20


def test_conflicting_header_does_not_replace_original_declaration():
    search, = collect(raw=b"# Query: q\n# Fields: subject id, query id\nq\ts\n",
        artifact=descriptor(format="tabular7", fields=["qseqid", "sseqid"]))["searches"]
    assert layout(search)["declared_fields"] == ["qseqid", "sseqid"]
    assert search["native"]["search"]["fields"] == ["sseqid", "qseqid"]
    assert search["normalized"]["hits"] == []
    assert "blast_tabular_declared_fields_conflict" in {i["code"] for i in search["issues"]}


@pytest.mark.parametrize("raw,format_name,fields,count", [
    (b"", "tabular6", FIELDS, None),
    (b"# BLASTP 2.17.0+\n# Query: q\n# 0 hits found\n", "tabular7", None, 0),
])
def test_empty_and_explicit_zero_keep_layout_and_different_meanings(raw, format_name, fields, count):
    search, = collect(raw=raw,
        artifact=descriptor(format=format_name, fields=fields, delimiter="@"))["searches"]
    assert layout(search) == {"format": format_name, "declared_fields": fields, "delimiter": "@"}
    assert search["reporting"]["native_hit_count"] == count


def test_declaration_is_detached_from_caller_and_collection_descriptor():
    declared = deepcopy(FIELDS)
    supplied = descriptor(format="tabular6", fields=declared)
    result = collect(raw=trow().encode(), artifact=supplied)
    search, = result["searches"]
    declared[0] = "changed caller"
    assert layout(search)["declared_fields"] == FIELDS
    result["artifacts"][0]["fields"][1] = "changed collection"
    assert layout(search)["declared_fields"] == FIELDS
    assert search["native"]["search"]["fields"] == FIELDS


def test_json_search_does_not_receive_table_inputs():
    search, = collect()["searches"]
    assert "table_layout" not in search["normalized"]["native"]
