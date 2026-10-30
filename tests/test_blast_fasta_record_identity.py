"""Supplied synthetic FASTA bytes; no acquisition or native BLAST execution."""
import builtins
import hashlib
import io
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.blast_fasta_record_identity import (
    blast_record_identity, parse_blast_fasta_source_records as parse,
)
from gene_annotation_episode.domain import parse_sequences


def locator(ordinal):
    return dict(kind="fasta_record", record_ordinal=ordinal)


def test_original_file_and_full_symbol_identities_are_separate():
    raw = b">s0\nACDEFGHIKL\n>s1\nACDEPQRSTV\n"
    result = parse(raw)
    assert set(result) == {"schema", "file_sha256", "size_bytes", "records", "issues"}
    assert result["schema"] == "blast_fasta_source_records_v1"
    assert result["file_sha256"] == "84ae36a79e704b527256bdd454f360535de0517c7a7dffdf7927b4f67026aacc"
    assert result["size_bytes"] == 30 and result["issues"] == []
    assert [(r["record_ordinal"], r["byte_start"], r["byte_end"], r["header"], r["symbols"])
            for r in result["records"]] == [(0, 0, 15, "s0", "ACDEFGHIKL"), (1, 15, 30, "s1", "ACDEPQRSTV")]
    assert [r["sequence_sha256"] for r in result["records"]] == [
        "be5884f5108f13d3e64bda3992e916bc204e704322e49bb1623ef9a7b496e64b",
        "f287ecbc4ac4c62be5c3deae84ca86ae001be2061987568c4a1d8eedebd55f64"]
    for row in result["records"]:
        assert set(row) == {"record_ordinal", "byte_start", "byte_end", "header", "symbols",
                            "sequence_sha256", "sequence_length", "status", "issues"}
        assert row["sequence_length"] == 10 and row["status"] == "available" and row["issues"] == []


@pytest.mark.parametrize("invalid,code", [(b"> \r\nACD\n", "empty_sequence_identifier"),
    (b">bad\n\t\n", "empty_sequence"), (">bad\né\n".encode(), "unrepresentable_sequence_symbol"),
    (b">bad\nAC\x00D\n", "unrepresentable_sequence_symbol")])
def test_invalid_original_slot_does_not_compact_later_record(invalid, code):
    raw = b">same\nac de\n" + invalid + b">same\nPQRS\n"
    result = parse(raw)
    assert [r["record_ordinal"] for r in result["records"]] == [0, 1, 2]
    first, broken, last = result["records"]
    assert first["symbols"] == "ACDE" and last["symbols"] == "PQRS"
    assert first["header"] == last["header"] == "same"
    assert broken["status"] == "incompatible" and broken["issues"] == [code]
    assert all(broken[k] is None for k in ("symbols", "sequence_sha256", "sequence_length"))
    assert raw[broken["byte_start"]:broken["byte_end"]] == invalid
    assert last["byte_start"] == len(b">same\nac de\n") + len(invalid)
    assert last["byte_end"] == len(raw)


@pytest.mark.parametrize("raw,issues", [(b"", ["empty_input"]), (b" \n\t", ["empty_input"]),
    (b"ACGT\n", ["sequence_before_fasta_header"]),
    (b">ok\nACD\n>bad\n\xff\n", ["input_not_utf8"])])
def test_whole_file_failures_preserve_byte_identity(raw, issues):
    result = parse(raw)
    assert result["records"] == [] and result["issues"] == issues
    assert result["file_sha256"] == hashlib.sha256(raw).hexdigest() and result["size_bytes"] == len(raw)


def test_preheader_failure_preserves_unambiguous_header_slots():
    raw = b"ACGT\nextra\n >same title  \r\na c\tde\r\n >same title  \nP Q\n"
    result = parse(raw)
    assert result["issues"] == ["sequence_before_fasta_header"]
    assert [r["record_ordinal"] for r in result["records"]] == [0, 1]
    assert [r["symbols"] for r in result["records"]] == ["ACDE", "PQ"]
    assert [r["header"] for r in result["records"]] == ["same title  "] * 2
    assert result["records"][0]["byte_start"] == 11


def test_original_utf8_byte_offsets_and_parser_line_whitespace_convention():
    raw = " \r\n >α description  \r\na c\tde\u2028  >β\nPQ\n".encode()
    result = parse(raw)
    assert result["issues"] == []
    first, second = result["records"]
    assert first["header"] == "α description  " and first["byte_start"] == 3
    assert raw[first["byte_start"]:first["byte_end"]] == " >α description  \r\na c\tde\u2028".encode()
    assert raw[second["byte_start"]:second["byte_end"]] == "  >β\nPQ\n".encode()
    assert [r["symbols"] for r in result["records"]] == [r.sequence for r in parse_sequences(raw, format="fasta")]


def test_wrapping_case_and_header_change_bytes_but_not_symbols():
    first = parse(b">one\nac de\nfg\n")
    second = parse(b">different\r\nACDEFG\r\n")
    assert first["file_sha256"] != second["file_sha256"]
    assert first["records"][0]["sequence_sha256"] == second["records"][0]["sequence_sha256"]


def test_no_molecule_inference_translation_gap_or_stop_removal():
    result = parse(b">not an annotation\naugt-*?123\n")
    row, = result["records"]
    assert row["symbols"] == "AUGT-*?123" and row["sequence_length"] == 10
    assert row["issues"] == [] and row["status"] == "available"


@pytest.mark.parametrize("contents", [None, "", ">a\nACD", bytearray(b">a\nACD"), memoryview(b"x")])
def test_only_supplied_bytes_are_accepted(contents):
    with pytest.raises(ValueError, match="^blast_fasta_bytes_required$"):
        parse(contents)


def test_source_qualified_keys_and_absent_null_pointer_semantics():
    assert blast_record_identity(source_ref="original source", pointer="/a~1b/~0", record_locator=None) == (
        "original source", "pointer", "/a~1b/~0")
    assert blast_record_identity(source_ref="original source", pointer="", record_locator=locator(2)) == (
        "original source", "fasta_record", 2)
    assert blast_record_identity(source_ref=" ", pointer="", record_locator=None) == (" ", "pointer", "")
    assert blast_record_identity(source_ref="s", pointer="", record_locator=None) != blast_record_identity(
        source_ref="s", pointer="", record_locator=locator(0))


@pytest.mark.parametrize("source", [None, "", 1, False])
def test_invalid_source(source):
    with pytest.raises(ValueError, match="^blast_record_source_invalid$"):
        blast_record_identity(source_ref=source, pointer="", record_locator=None)


@pytest.mark.parametrize("pointer", [None, "not-pointer", "/bad~", "/bad~2", 1, False])
def test_invalid_pointer(pointer):
    with pytest.raises(ValueError, match="^blast_record_pointer_invalid$"):
        blast_record_identity(source_ref="s", pointer=pointer, record_locator=None)


@pytest.mark.parametrize("value", [False, 0, [], {}, {"kind": "fasta_record"},
    {"record_ordinal": 0}, {"kind": "json", "record_ordinal": 0},
    {"kind": "fasta_record", "record_ordinal": 0, "extra": None},
    locator(-1), locator(True), locator(1.0), locator("1")])
def test_closed_locator(value):
    with pytest.raises(ValueError, match="^blast_record_locator_invalid$"):
        blast_record_identity(source_ref="s", pointer="", record_locator=value)


def test_fasta_locator_never_allows_a_fabricated_json_pointer():
    with pytest.raises(ValueError, match="^record_locator_pointer_conflict$"):
        blast_record_identity(source_ref="s", pointer="/records/0", record_locator=locator(0))


def test_helpers_are_pure(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("helpers operate on supplied values only")
    for obj, name in ((builtins, "open"), (io, "open"), (Path, "read_bytes"), (Path, "read_text"),
                      (socket, "socket"), (socket, "create_connection"), (subprocess, "Popen"), (subprocess, "run")):
        monkeypatch.setattr(obj, name, forbidden)
    assert parse(b">x\nACD\n")["records"][0]["symbols"] == "ACD"
    assert blast_record_identity(source_ref="s", pointer="", record_locator=locator(1)) == ("s", "fasta_record", 1)
