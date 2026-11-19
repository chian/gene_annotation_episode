"""Shared lexical-table tests and retained prechange VDB parser regressions.

The JSON expectations were captured under bounded529 before the parser edit.
These synthetic fixtures are never described as authentic native verification;
no historical source snapshot is imported or executed for comparison.
"""
from copy import deepcopy
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search import blast_vdb_inputs as vdb




def read(contents, **changes):
    kwargs = dict(source_ref="synthetic:lexical655", source_version="synthetic-v1")
    kwargs.update(changes)
    return vdb.read_blast_vdb_sequence_table(contents, **kwargs)


def issue(code, field):
    return dict(code=code, field=field)


def test_exact_table_preserves_all_rows_text_locations_and_duplicate_ids():
    raw = (b"gnl|SRA|SRR1.1.2\tSRR1.1.2\t4\tacgu\r\n"
           b"\r\n"
           b"bad\trow\r\n"
           b"N/A\tSRR1.1.2\t4\tacgu\r\n"
           b"duplicate\tduplicate\t4\tACGU\textra\r\n"
           b"gnl|SRA|SRR1.1.2\tSRR1.1.2\t0004\tacgu\r\n"
           b"\tN/A\t-4\t\r\n"
           b"zero\tzero\t0\t\r\n")
    result = read(raw)
    assert set(result) == {"schema", "source_ref", "source_version", "input_identity", "native_text", "rows", "issues"}
    assert result["schema"] == "blast_vdb_sequence_table_v1"
    assert result["source_ref"] == "synthetic:lexical655" and result["source_version"] == "synthetic-v1"
    assert result["input_identity"] == {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
    assert result["native_text"] == raw.decode() and result["issues"] == []
    expected = [
        (["gnl|SRA|SRR1.1.2", "SRR1.1.2", "4", "acgu"],
         {"native_identifier": "gnl|SRA|SRR1.1.2", "native_accession": "SRR1.1.2", "length_lexeme": "4", "sequence_symbols": "acgu"}, 4, []),
        ([""], None, None, [issue("column_count_invalid", None)]),
        (["bad", "row"], None, None, [issue("column_count_invalid", None)]),
        (["N/A", "SRR1.1.2", "4", "acgu"],
         {"native_identifier": "N/A", "native_accession": "SRR1.1.2", "length_lexeme": "4", "sequence_symbols": "acgu"},
         4, [issue("field_unavailable", "native_identifier")]),
        (["duplicate", "duplicate", "4", "ACGU", "extra"], None, None, [issue("column_count_invalid", None)]),
        (["gnl|SRA|SRR1.1.2", "SRR1.1.2", "0004", "acgu"],
         {"native_identifier": "gnl|SRA|SRR1.1.2", "native_accession": "SRR1.1.2", "length_lexeme": "0004", "sequence_symbols": "acgu"}, 4, []),
        (["", "N/A", "-4", ""],
         {"native_identifier": "", "native_accession": "N/A", "length_lexeme": "-4", "sequence_symbols": ""}, None,
         [issue("field_empty", "native_identifier"), issue("field_unavailable", "native_accession"),
          issue("field_empty", "sequence_symbols"), issue("integer_lexeme_invalid", "length_lexeme")]),
        (["zero", "zero", "0", ""],
         {"native_identifier": "zero", "native_accession": "zero", "length_lexeme": "0", "sequence_symbols": ""},
         0, [issue("field_empty", "sequence_symbols")]),
    ]
    assert result["rows"] == [dict(row_ordinal=i, line_number=i + 1, cells=cells, fields=fields,
        native_reported_length=length, issues=issues) for i, (cells, fields, length, issues) in enumerate(expected)]


@pytest.mark.parametrize("lexeme, expected_length, expected_issues", [
    ("0", 0, []), ("0004", 4, []), ("42", 42, []),
    ("", None, [issue("field_empty", "length_lexeme")]),
    ("N/A", None, [issue("field_unavailable", "length_lexeme")]),
    *[(value, None, [issue("integer_lexeme_invalid", "length_lexeme")])
      for value in ("-1", "+4", "4.0", " 4", "4 ", "4e0", "4_0", "NaN", "\uff14", "\u0664", "n/a")],
])
def test_literal_native_integer_spellings(lexeme, expected_length, expected_issues):
    row = read(("id\tacc\t" + lexeme + "\tacgu").encode())["rows"][0]
    assert row["fields"]["length_lexeme"] == lexeme
    assert row["native_reported_length"] == expected_length
    assert row["issues"] == expected_issues


@pytest.mark.parametrize("field", ["native_identifier", "native_accession", "length_lexeme", "sequence_symbols"])
@pytest.mark.parametrize("value, code", [("", "field_empty"), ("N/A", "field_unavailable")])
def test_missing_fields_remain_literal_in_declared_column_order(field, value, code):
    fields = dict(native_identifier="id", native_accession="acc", length_lexeme="4", sequence_symbols="acgu")
    fields[field] = value
    row = read("\t".join(fields.values()).encode())["rows"][0]
    assert row["fields"] == fields and row["cells"] == list(fields.values())
    assert row["issues"] == [issue(code, field)]
    assert row["native_reported_length"] == (None if field == "length_lexeme" else 4)


@pytest.mark.parametrize("raw, cells", [
    (b"", None), (b"\n", [""]), (b"a\tb\tc", ["a", "b", "c"]),
    (b"\t\t\t\t", ["", "", "", "", ""]),
    (b"N/A\tN/A\tbogus\tN/A\tN/A", ["N/A", "N/A", "bogus", "N/A", "N/A"]),
])
def test_empty_input_and_wrong_width_have_no_guessed_fields(raw, cells):
    result = read(raw)
    assert result["native_text"] == raw.decode()
    assert result["rows"] == ([] if cells is None else [dict(row_ordinal=0, line_number=1,
        cells=cells, fields=None, native_reported_length=None, issues=[issue("column_count_invalid", None)])])


@pytest.mark.parametrize("ending", [b"", b"\n", b"\r\n", b"\r"])
def test_line_ending_is_retained_without_a_fabricated_trailing_row(ending):
    raw = b"id\tacc\t4\tacgu" + ending
    result = read(raw)
    assert result["native_text"].encode() == raw
    assert len(result["rows"]) == 1
    assert result["rows"][0]["cells"] == ["id", "acc", "4", "acgu"]


def test_splitlines_locations_include_blank_rows_for_other_decoded_separators():
    raw = "a\ta\t1\tu\u2028\u2028b\tb\t1\tU".encode()
    rows = read(raw)["rows"]
    assert [row["row_ordinal"] for row in rows] == [0, 1, 2]
    assert [row["line_number"] for row in rows] == [1, 2, 3]
    assert [row["cells"] for row in rows] == [["a", "a", "1", "u"], [""], ["b", "b", "1", "U"]]


def test_invalid_utf8_retains_original_byte_identity_and_existing_located_issue():
    raw = b"id\tacc\t4\tACGU\n\xff"
    assert read(raw) == dict(schema="blast_vdb_sequence_table_v1", source_ref="synthetic:lexical655",
        source_version="synthetic-v1", input_identity={"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)},
        native_text=None, rows=[], issues=[{"code": "blast_vdb_format_unsupported", "search_key": None,
            "hit_ordinal": None, "hsp_ordinal": None, "source_pointer": None, "details": {"encoding": "utf-8"}}])


def test_lexical_reading_never_normalizes_symbols_or_infers_selection_or_success():
    raw = "all\tgnl|SRA|not-split\t0\t??u\u00e9-\n".encode()
    result = read(raw, source_ref="  opaque source  ", source_version="  native-version  ")
    row = result["rows"][0]
    assert result["source_ref"] == "  opaque source  " and result["source_version"] == "  native-version  "
    assert row["fields"] == dict(native_identifier="all", native_accession="gnl|SRA|not-split",
                                 length_lexeme="0", sequence_symbols="??u\u00e9-")
    assert row["native_reported_length"] == 0 and row["issues"] == []
    assert "parse_context" not in result and "records" not in result
    with pytest.raises(TypeError):
        vdb.read_blast_vdb_sequence_table(raw, source_ref="synthetic", source_version="v1", extraction_context={})


@pytest.mark.parametrize("contents", ["id\tacc\t1\tA", bytearray(b"id\tacc\t1\tA"), None, 1])
def test_reader_requires_actual_bytes(contents):
    with pytest.raises(ValueError, match="^blast_vdb_record_value_invalid$"):
        read(contents)


@pytest.mark.parametrize("field", ["source_ref", "source_version"])
@pytest.mark.parametrize("value", [None, "", " \t", 1, False])
def test_reader_requires_nonblank_source_identity_strings(field, value):
    with pytest.raises(ValueError, match="^blast_vdb_record_value_invalid$"):
        read(b"id\tacc\t1\tA", **{field: value})


def test_returned_records_and_repeated_calls_are_detached():
    raw = b"id\tacc\t1\tu\nid\tacc\t1\tu\n"
    first = read(raw)
    baseline = deepcopy(first)
    first["rows"][0]["cells"][0] = "changed"
    first["rows"][0]["fields"]["sequence_symbols"] = "T"
    first["rows"][0]["issues"].append(issue("changed", None))
    first["input_identity"]["sha256"] = "0" * 64
    assert first["rows"][1] == baseline["rows"][1]
    assert read(raw) == baseline
    json.dumps(baseline, allow_nan=False)


def deny_external_access(patch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure supplied-byte parsing attempted external access")
    for target, names in (
        (builtins, ("open",)), (io, ("open", "FileIO")),
        (Path, ("open", "read_bytes", "write_bytes", "read_text", "write_text", "stat", "iterdir")),
        (socket, ("socket", "create_connection", "getaddrinfo")),
        (urllib.request, ("urlopen",)), (subprocess, ("Popen", "run", "check_call", "check_output")),
        (os, ("open", "system", "popen", "fork", "posix_spawn", "execve")),
    ):
        for name in names:
            if hasattr(target, name):
                patch.setattr(target, name, forbidden)
    return forbidden


def test_reader_is_pure_and_does_not_invoke_search_context_or_sequence_validation(monkeypatch):
    with monkeypatch.context() as patch:
        forbidden = deny_external_access(patch)
        patch.setattr(vdb, "_extraction_context", forbidden)
        patch.setattr(vdb, "_symbols", forbidden)
        result = read(b"all\tgnl|SRA|untouched\t0\tacgu?\n\n", source_ref="https://must-not-be-opened.invalid/data")
    assert result["rows"][0]["fields"]["sequence_symbols"] == "acgu?"
    assert result["rows"][0]["native_reported_length"] == 0
    assert result["rows"][1]["cells"] == [""]


def conversion_limit_lexeme():
    # Observe the bounded interpreter's actual setting; never change it.
    limit = sys.get_int_max_str_digits()
    assert limit > 0, "this targeted case requires an active interpreter conversion limit"
    return "9" * (limit + 1)


def test_conversion_limit_retains_valid_spelling_as_unavailable_conversion():
    size = conversion_limit_lexeme()
    raw = ("\tacc\t" + size + "\tacgu\n").encode()
    result = read(raw)
    row = result["rows"][0]
    assert result["native_text"].encode() == raw
    assert row["cells"] == ["", "acc", size, "acgu"]
    assert row["fields"] == dict(native_identifier="", native_accession="acc",
                                 length_lexeme=size, sequence_symbols="acgu")
    assert row["native_reported_length"] is None
    assert row["issues"] == [issue("field_empty", "native_identifier"),
                              issue("integer_conversion_unavailable", "length_lexeme")]

