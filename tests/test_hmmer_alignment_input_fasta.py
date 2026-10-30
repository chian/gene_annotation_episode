"""Native AFA/A2M input contract cases; all literal inputs are authored tests.

Only the two explicitly named cmemit artifacts below are retained native
emission outputs.  Their emission receipts do not establish input conformance.
This module performs no native execution and defines no numerical scorer.
"""

import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_alignment_input_fasta import decode_native_fasta_alignment
from gene_annotation_episode.hmmer_alignment_input_types import (
    NativeAlignmentLine,
    alignment_input_diagnostic,
    iter_native_alignment_lines,
)


ROOT = Path(__file__).resolve().parents[1]
EMISSIONS = ROOT / "verification/tool_graders_infernal_preparation_emission_2026-10-26_250/native"

BATCH_FIELDS = {
    "version", "format", "alphabet", "records", "diagnostics", "end_state",
    "next_byte_offset", "trailing_range",
}
RECORD_FIELDS = {
    "record_ordinal", "reader_state", "native_status_equivalent", "byte_start",
    "byte_end", "line_start", "line_end", "header_valid", "column_count",
    "declared_row_count", "declared_column_count", "block_count", "rows",
    "column_annotations", "events", "diagnostics",
}
ROW_FIELDS = {
    "row_ordinal", "name", "name_bytes_hex", "description", "aligned_sequence",
    "segments", "annotation_fragments", "column_annotations", "geometry_valid",
    "symbols_valid", "identity_unambiguous", "diagnostics",
}
EVENT_FIELDS = {
    "event_ordinal", "kind", "block_index", "row_ordinal", "tag", "raw", "value", "locator",
}
SEGMENT_FIELDS = {
    "event_ordinal", "byte_start", "byte_end", "column_start", "column_end",
    "aligned_start", "aligned_end", "operation", "basis", "source_text", "decoded_text",
}
DIAGNOSTIC_FIELDS = {
    "code", "record_ordinal", "row_ordinal", "event_ordinal", "byte_start", "byte_end", "details",
}


def decode(content, fmt="afa", alphabet="amino"):
    return decode_native_fasta_alignment(content, declared_format=fmt, alphabet=alphabet)


def assert_contract(batch, content):
    """Assert saved byte custody and closed shapes, independent of grammar rules."""
    assert set(batch) == BATCH_FIELDS
    assert json.loads(json.dumps(batch)) == batch
    for diagnostic in batch["diagnostics"]:
        assert set(diagnostic) == DIAGNOSTIC_FIELDS
        assert set(diagnostic["details"]) == {"expected", "actual", "token_hex"}
    for record in batch["records"]:
        assert set(record) == RECORD_FIELDS
        assert record["block_count"] is None
        assert record["declared_column_count"] is None
        assert record["declared_row_count"] is None
        assert b"".join(event["raw"].encode("utf-8", "surrogateescape")
                        for event in record["events"]) == content[:batch["next_byte_offset"]]
        for ordinal, event in enumerate(record["events"]):
            assert set(event) == EVENT_FIELDS
            assert event["event_ordinal"] == ordinal
            assert set(event["locator"]) == {"line", "byte_start", "byte_end"}
            locator = event["locator"]
            assert event["raw"].encode("utf-8", "surrogateescape") == content[
                locator["byte_start"]:locator["byte_end"]
            ]
        for ordinal, row in enumerate(record["rows"]):
            assert set(row) == ROW_FIELDS
            assert row["row_ordinal"] == ordinal
            assert row["name"].encode("utf-8", "surrogateescape").hex() == row["name_bytes_hex"]
            cursor = 0
            for segment in row["segments"]:
                assert set(segment) == SEGMENT_FIELDS
                assert segment["aligned_start"] == cursor
                cursor = segment["aligned_end"]
                assert cursor - segment["aligned_start"] == len(segment["decoded_text"])
                if segment["operation"] == "native_gap":
                    assert segment["basis"] == "a2m_insert_slot"
                    assert segment["event_ordinal"] is None
                    assert segment["byte_start"] is segment["byte_end"] is None
                    assert segment["column_start"] is segment["column_end"] is None
                    assert segment["source_text"] == ""
                    assert set(segment["decoded_text"]) == {"-"}
                else:
                    event = record["events"][segment["event_ordinal"]]
                    assert event["row_ordinal"] == ordinal
                    assert segment["byte_start"] == event["locator"]["byte_start"] + segment["column_start"]
                    assert segment["byte_end"] == event["locator"]["byte_start"] + segment["column_end"]
                    assert segment["source_text"].encode("utf-8", "surrogateescape") == content[
                        segment["byte_start"]:segment["byte_end"]
                    ]
                    if segment["operation"] == "ignore":
                        assert segment["basis"] == "input_ignored"
                        assert segment["decoded_text"] == ""
            if row["aligned_sequence"] is not None:
                assert "".join(s["decoded_text"] for s in row["segments"]) == row["aligned_sequence"]
            if row["geometry_valid"]:
                assert len(row["aligned_sequence"]) > 0
                if record["reader_state"] == "complete":
                    assert cursor == record["column_count"]
            if record["reader_state"] == "complete":
                # Every sequence/blank payload byte is copied, aliased or ignored.
                for event in record["events"]:
                    if event["row_ordinal"] != ordinal or event["kind"] not in ("sequence", "blank"):
                        continue
                    raw = event["raw"].encode("utf-8", "surrogateescape")
                    payload = raw[:-2] if raw.endswith(b"\r\n") else raw[:-1] if raw.endswith(b"\n") else raw
                    source = b"".join(s["source_text"].encode("utf-8", "surrogateescape")
                                      for s in row["segments"] if s["event_ordinal"] == event["event_ordinal"])
                    assert source == payload
    if batch["trailing_range"] is not None:
        assert batch["trailing_range"] == {
            "byte_start": batch["next_byte_offset"], "byte_end": len(content)
        }


def test_native_byte_lines_lf_crlf_and_control_bytes():
    content = b"\nA\r\nB\rC\vD\fE\nlast\r"
    assert list(iter_native_alignment_lines(content)) == [
        NativeAlignmentLine(1, 0, 0, 1, b""),
        NativeAlignmentLine(2, 1, 2, 4, b"A"),
        NativeAlignmentLine(3, 4, 11, 12, b"B\rC\vD\fE"),
        NativeAlignmentLine(4, 12, 17, 17, b"last\r"),
    ]
    assert list(iter_native_alignment_lines(b"")) == []
    assert list(iter_native_alignment_lines(b"x\n")) == [NativeAlignmentLine(1, 0, 1, 2, b"x")]
    assert list(iter_native_alignment_lines(b"x\r\r\n")) == [NativeAlignmentLine(1, 0, 2, 4, b"x\r")]


@pytest.mark.parametrize("content", ["x", bytearray(b"x"), memoryview(b"x"), None, False])
def test_byte_line_argument_misuse(content):
    with pytest.raises(ValueError, match="^hmmer_alignment_content_invalid$"):
        iter_native_alignment_lines(content)


def test_diagnostic_closed_shape_and_exact_detail_types():
    diagnostic = alignment_input_diagnostic(
        "native_source_semantics_unestablished", record_ordinal=0, row_ordinal=2,
        event_ordinal=4, byte_start=12, byte_end=13, expected=-1,
        actual="a2m_nul", token_hex="00",
    )
    assert set(diagnostic) == DIAGNOSTIC_FIELDS
    assert diagnostic["details"] == {"expected": -1, "actual": "a2m_nul", "token_hex": "00"}


@pytest.mark.parametrize("code,kwargs", [
    ("invented", {}), (None, {}), ("empty_alignment", {"row_ordinal": True}),
    ("empty_alignment", {"event_ordinal": -1}),
    ("empty_alignment", {"byte_start": 2, "byte_end": 1}),
    ("empty_alignment", {"expected": True}), ("empty_alignment", {"actual": []}),
    ("empty_alignment", {"token_hex": "AB"}), ("empty_alignment", {"token_hex": "0"}),
    ("empty_alignment", {"token_hex": "gg"}), ("empty_alignment", {"token_hex": b"00"}),
])
def test_diagnostic_rejects_contract_misuse(code, kwargs):
    with pytest.raises(ValueError, match="^hmmer_alignment_diagnostic_invalid$"):
        alignment_input_diagnostic(code, **kwargs)


@pytest.mark.parametrize("content,fmt,alphabet,error", [
    ("text", "afa", "DNA", "content"), (bytearray(b"x"), "afa", "DNA", "content"),
    (b"", "AFA", "DNA", "format"), (b"", "stockholm", "DNA", "format"),
    (b"", [], "DNA", "format"), (b"", "afa", None, "alphabet"),
    (b"", "afa", "dna", "alphabet"), (b"", "afa", [], "alphabet"),
])
def test_decoder_argument_misuse(content, fmt, alphabet, error):
    with pytest.raises(ValueError, match=f"^hmmer_alignment_{error}_invalid$"):
        decode(content, fmt, alphabet)


@pytest.mark.parametrize("fmt", ["afa", "a2m"])
@pytest.mark.parametrize("content", [b"", b"\n \t\r\n\x00\t\n"])
def test_empty_file_is_eof_without_an_alignment_occurrence(fmt, content):
    batch = decode(content, fmt)
    assert_contract(batch, content)
    assert batch["records"] == []
    assert batch["end_state"] == "eof"
    assert batch["next_byte_offset"] == len(content)
    assert batch["trailing_range"] is None
    assert batch["diagnostics"] == [
        alignment_input_diagnostic("empty_alignment", byte_start=0, byte_end=len(content), actual=0)
    ]


def test_afa_multiline_whitespace_description_and_duplicate_identity():
    content = b" \t\n \t>dup first desc  \r\n\t AC G \r\n \vT_\n>dup\tsecond\t \nA CGT_\n"
    batch = decode(content, alphabet="DNA")
    assert_contract(batch, content)
    record = batch["records"][0]
    assert record["reader_state"] == "complete"
    assert record["native_status_equivalent"] == 0
    assert record["column_count"] == 5
    assert record["column_annotations"] == {}
    assert [r["aligned_sequence"] for r in record["rows"]] == ["ACGT_", "ACGT_"]
    assert [r["description"] for r in record["rows"]] == ["first desc  ", "second\t "]
    assert [r["name"] for r in record["rows"]] == ["dup", "dup"]
    assert all(r["identity_unambiguous"] for r in record["rows"])


@pytest.mark.parametrize("fmt", ["afa", "a2m"])
def test_header_bytes_are_reversible_and_nul_is_a_token_delimiter(fmt):
    content = b"\x00 \t\n\t>\x00n\xc3\xa9\xff\x00\t d\xe2\x98\x83  \r\nAC"
    batch = decode(content, fmt, "DNA")
    assert_contract(batch, content)
    row = batch["records"][0]["rows"][0]
    assert row["name_bytes_hex"] == b"n\xc3\xa9\xff".hex()
    assert row["description"].encode("utf-8", "surrogateescape") == b"d\xe2\x98\x83  "
    assert row["aligned_sequence"] == "AC"
    assert batch["records"][0]["events"][-1]["locator"] == {
        "line": 3, "byte_start": len(content) - 2, "byte_end": len(content),
    }


@pytest.mark.parametrize("fmt", ["afa", "a2m"])
def test_header_tokens_do_not_split_at_bare_cr_vt_or_ff(fmt):
    content = b">a\rb\vc\fd desc \r\nAC\n"
    row = decode(content, fmt, "DNA")["records"][0]["rows"][0]
    assert row["name_bytes_hex"] == b"a\rb\vc\fd".hex()
    assert row["description"] == "desc "


@pytest.mark.parametrize("content,fmt,code", [
    (b"not a header\n>x\nAA\n", "afa", "invalid_header"),
    (b"\v\n>x\nAA\n", "afa", "invalid_header"),
    (b"\x00>x\nAA\n", "afa", "invalid_header"),
    (b">\nAA\n", "afa", "invalid_header"),
    (b">\nAA\n", "a2m", "missing_name"),
    (b"> \t\x00\nAA\n", "afa", "missing_name"),
    (b"> \t\x00\nAA\n", "a2m", "missing_name"),
])
def test_invalid_header_preserves_consumed_and_trailing_bytes(content, fmt, code):
    batch = decode(content, fmt)
    assert_contract(batch, content)
    assert batch["records"][0]["native_status_equivalent"] == 7
    assert batch["records"][0]["reader_state"] == "invalid"
    assert batch["diagnostics"][0]["code"] == code
    assert batch["next_byte_offset"] == content.index(b"\n") + 1


@pytest.mark.parametrize("alphabet,expected", [("amino", "AXC"), ("DNA", "ANC"), ("RNA", "ANC")])
def test_afa_nul_sequence_byte_has_native_unknown_alias(alphabet, expected):
    content = b">x\nA\x00C\n"
    batch = decode(content, alphabet=alphabet)
    assert_contract(batch, content)
    row = batch["records"][0]["rows"][0]
    assert row["aligned_sequence"] == expected
    alias, = [s for s in row["segments"] if s["operation"] == "symbol_alias"]
    assert (alias["byte_start"], alias["byte_end"], alias["aligned_start"], alias["aligned_end"]) == (4, 5, 1, 2)
    assert alias["source_text"] == "\x00"


@pytest.mark.parametrize("alphabet,sequence", [
    ("amino", b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-._*~"),
    ("DNA", b"acgtuRYMKSWHBVDNXI-._*~"),
    ("RNA", b"acgtuRYMKSWHBVDNXI-._*~"),
])
def test_afa_keeps_ordinary_alphabet_aliases_lexical(alphabet, sequence):
    content = b">x\n" + sequence + b"\n"
    batch = decode(content, alphabet=alphabet)
    assert_contract(batch, content)
    assert batch["records"][0]["rows"][0]["aligned_sequence"] == sequence.decode()
    assert batch["records"][0]["native_status_equivalent"] == 0


@pytest.mark.parametrize("bad", [b"\t", b"\r", b"\v", b"\f", b"\xff", b"?", b"9"])
def test_afa_internal_invalid_byte_is_not_whitespace_or_a_newline(bad):
    content = b">x\nAC" + bad + b"GT\n>later\nAAAA\n"
    batch = decode(content, alphabet="DNA")
    assert_contract(batch, content)
    record = batch["records"][0]
    assert record["native_status_equivalent"] == 7
    assert record["reader_state"] == "partial"
    assert record["rows"][0]["aligned_sequence"] == "AC"
    assert not record["rows"][0]["symbols_valid"]
    diagnostic = batch["diagnostics"][0]
    assert diagnostic["code"] == "invalid_sequence_byte"
    assert (diagnostic["byte_start"], diagnostic["byte_end"]) == (5, 6)
    assert diagnostic["details"]["token_hex"] == bad.hex()
    assert batch["next_byte_offset"] == content.index(b">later")


@pytest.mark.parametrize("fmt,content", [
    ("afa", b"\xff>x\nAC\n"),
    ("afa", b">x\n \xffAC\n"),
    ("a2m", b">x\nAC\xff\n"),
    ("a2m", b">x\n \xc3\xa9AC\n"),
])
def test_nonascii_ctype_paths_preserve_unestablished_source_semantics(fmt, content):
    batch = decode(content, fmt, "DNA")
    assert_contract(batch, content)
    record = batch["records"][0]
    assert batch["end_state"] == "source_semantics_unestablished"
    assert record["native_status_equivalent"] is None
    assert batch["diagnostics"][0]["details"]["actual"] == "nonascii_ctype"
    assert batch["diagnostics"][0]["details"]["token_hex"] in {"ff", "c3"}
    if fmt == "a2m":
        assert all(r["aligned_sequence"] is None and r["segments"] == [] for r in record["rows"])


def test_afa_empty_row_consumes_next_header_without_inventing_its_row():
    content = b">empty\n \t\n>unparsed\nAC\n"
    batch = decode(content)
    assert_contract(batch, content)
    record = batch["records"][0]
    assert [r["name"] for r in record["rows"]] == ["empty"]
    assert record["events"][-1]["raw"] == ">unparsed\n"
    assert record["events"][-1]["row_ordinal"] is None
    assert batch["next_byte_offset"] == content.index(b"AC")
    assert batch["diagnostics"][0]["code"] == "empty_sequence"
    assert record["native_status_equivalent"] == 7


def test_afa_unequal_suffix_is_one_failed_alignment_without_padding():
    content = b">a\nAC\n>b\nA\n>unparsed\nAC\n"
    batch = decode(content)
    assert_contract(batch, content)
    record = batch["records"][0]
    assert len(batch["records"]) == 1
    assert record["reader_state"] == "partial"
    assert record["native_status_equivalent"] == 7
    assert [r["aligned_sequence"] for r in record["rows"]] == ["AC", "A"]
    assert [r["geometry_valid"] for r in record["rows"]] == [True, False]
    assert batch["diagnostics"][0]["details"] == {"expected": 2, "actual": 1, "token_hex": None}
    assert batch["next_byte_offset"] == content.index(b"AC", content.index(b">unparsed"))
    assert not any(s["operation"] == "native_gap" for r in record["rows"] for s in r["segments"])


def test_afa_second_set_of_headers_is_more_rows_in_one_msa():
    content = b">a\nAC\n>b\nGT\n\n>a\nTG\n>b\nCA\n"
    batch = decode(content, alphabet="DNA")
    assert_contract(batch, content)
    assert len(batch["records"]) == 1
    assert [r["aligned_sequence"] for r in batch["records"][0]["rows"]] == ["AC", "GT", "TG", "CA"]
    assert batch["records"][0]["reader_state"] == "complete"


def retained_emission(case, expected_sha256):
    directory = EMISSIONS / case
    content = (directory / "emitted.out").read_bytes()
    assert hashlib.sha256(content).hexdigest() == expected_sha256
    receipt = json.loads((directory / "receipt.json").read_text())
    assert receipt["returncode"] == 0
    emitted, = [f for f in receipt["files"] if f["path"] == "emitted.out"]
    assert emitted["sha256"] == expected_sha256
    return content


def test_retained_native_a2m_aligned_emission_bytes_unchanged():
    content = retained_emission(
        "aligned_a2m", "7e85ea14332e2dff9ff62f274e81c07fa59699c96f48236a46a8d41dd2b24197"
    )
    batch = decode(content, "a2m", "RNA")
    assert_contract(batch, content)
    record = batch["records"][0]
    assert record["reader_state"] == "complete"
    assert record["column_count"] == 12
    assert record["column_annotations"]["RF"] == {
        "text": "xxxxxxxxxxxx", "valid": True, "basis": "native_format_derivation", "fragments": [],
    }
    assert [r["aligned_sequence"] for r in record["rows"]] == [
        "GCGC-UAAGCGC", "GCGCUAAAGCGC", "GCGAUUUAUCGU",
    ]


def test_retained_native_a2m_insertions_have_exact_expansion_and_source_mapping():
    content = retained_emission(
        "a2m_insertions", "4a47f0cd7fad3b309d62e69985932c31b12358e0befa0e78d0d4cb92b7ed22e3"
    )
    batch = decode(content, "a2m", "RNA")
    assert_contract(batch, content)
    record = batch["records"][0]
    assert record["reader_state"] == "complete"
    assert record["native_status_equivalent"] == 0
    assert record["column_count"] == 17
    assert record["column_annotations"]["RF"]["text"] == "xx.xxx.xxx..xxx.x"
    assert [r["aligned_sequence"] for r in record["rows"]] == [
        "GC-GC-uUAA--GCG-C", "GC-GUC-U-A--ACG-C", "-UgG---CGA--U-AaC",
        "-A-AUA--AA------G", "GC-G-G-CCCggACG-C",
    ]
    row = record["rows"][0]
    generated = [(s["aligned_start"], s["aligned_end"]) for s in row["segments"]
                 if s["operation"] == "native_gap"]
    assert generated == [(2, 3), (10, 12), (15, 16)]
    assert "".join(s["source_text"] for s in row["segments"]) == "GCGC-uUAAGCGC"


@pytest.mark.parametrize("content", [
    b">a\naaACgTt\n>b\ncA-Cgg\n>c\nA-T\n",
    b">a\n.a.aA.C...gT.t.\n>b\nc...A-.C.g.g\n>c\n...A-..T...\n",
])
def test_authored_a2m_leading_trailing_insert_slots_and_dotful_equivalence(content):
    batch = decode(content, "a2m", "DNA")
    assert_contract(batch, content)
    record = batch["records"][0]
    assert record["reader_state"] == "complete"
    assert record["column_count"] == 8
    assert record["column_annotations"]["RF"]["text"] == "..xx.x.."
    assert [r["aligned_sequence"] for r in record["rows"]] == [
        "aaACgTt-", "c-A--Cgg", "--A--T--",
    ]


def test_a2m_multiline_inserts_whitespace_and_uppercase_o_are_preserved_as_source():
    content = b">dup a\n\tOaaA.\n \tcO Cg \t\nTtO\n>dup b\ncA-Cgg\n"
    batch = decode(content, "a2m", "DNA")
    assert_contract(batch, content)
    record = batch["records"][0]
    assert record["reader_state"] == "complete"
    assert record["column_annotations"]["RF"]["text"] == "..x.x.x.."
    assert [r["aligned_sequence"] for r in record["rows"]] == ["aaAcCgTt-", "c-A---Cgg"]
    ignored = "".join(s["source_text"] for r in record["rows"] for s in r["segments"]
                      if s["operation"] == "ignore")
    assert ignored.count("O") == 3
    assert "\t" in ignored and "." in ignored
    assert all(r["identity_unambiguous"] for r in record["rows"])


@pytest.mark.parametrize("content,expected,actual,next_marker", [
    (b">a\nAC\n>b\nA\n>unparsed\nAC\n", 2, 1, b"AC\n"),
    (b">a\nAC\n>b\nACG\n>unparsed\nAC\n", 2, 3, b">unparsed"),
    (b">a\nac\n>b\nAc\n", 0, 1, None),
])
def test_a2m_consensus_failures_never_invent_expanded_rows(content, expected, actual, next_marker):
    batch = decode(content, "a2m", "DNA")
    assert_contract(batch, content)
    record = batch["records"][0]
    assert record["reader_state"] == "partial"
    assert record["native_status_equivalent"] == 7
    assert record["column_count"] is None and record["column_annotations"] == {}
    assert all(r["aligned_sequence"] is None and r["segments"] == [] for r in record["rows"])
    assert batch["diagnostics"][0]["code"] == "a2m_consensus_count_mismatch"
    assert batch["diagnostics"][0]["details"] == {"expected": expected, "actual": actual, "token_hex": None}
    if next_marker is None:
        assert batch["next_byte_offset"] == len(content)
    elif next_marker == b"AC\n":
        assert batch["next_byte_offset"] == content.rindex(next_marker)
    else:
        assert batch["next_byte_offset"] == content.index(next_marker)


@pytest.mark.parametrize("symbol,corner", [(b"o", "a2m_lowercase_o"), (b"\x00", "a2m_nul")])
def test_a2m_structural_digital_discrepancies_remain_unestablished(symbol, corner):
    content = b">a\nAC" + symbol + b"\n>unparsed\nAC\n"
    batch = decode(content, "a2m", "DNA")
    assert_contract(batch, content)
    record = batch["records"][0]
    assert batch["end_state"] == record["reader_state"] == "source_semantics_unestablished"
    assert record["native_status_equivalent"] is None
    assert record["rows"][0]["aligned_sequence"] is None
    assert record["rows"][0]["segments"] == []
    assert batch["diagnostics"][0]["details"] == {
        "expected": None, "actual": corner, "token_hex": symbol.hex(),
    }
    assert batch["next_byte_offset"] == content.index(b">unparsed")


@pytest.mark.parametrize("content", [
    b">empty\n>next\nAc\n",
    b">first\nac\nO\n>next\nAAc\n",
])
def test_a2m_zero_consensus_unsafe_insert_slot_is_not_a_native_status_claim(content):
    batch = decode(content, "a2m", "DNA")
    assert_contract(batch, content)
    assert batch["end_state"] == "source_semantics_unestablished"
    assert batch["records"][0]["native_status_equivalent"] is None
    assert batch["diagnostics"][0]["details"]["actual"] == "a2m_zero_consensus_insert_slot"
    assert all(r["segments"] == [] for r in batch["records"][0]["rows"])


@pytest.mark.parametrize("bad", [b"_", b"*", b"~", b"?", b"9", b"\r", b"\v", b"\f"])
def test_a2m_forbidden_bytes_are_rejected_without_generated_gaps(bad):
    # Keep CR inside payload; CR immediately before LF is a line terminator.
    content = b">a\nAC" + bad + b"T\n>unparsed\nACT\n"
    batch = decode(content, "a2m", "DNA")
    assert_contract(batch, content)
    assert batch["records"][0]["native_status_equivalent"] == 7
    assert batch["diagnostics"][0]["code"] == "invalid_sequence_byte"
    assert batch["diagnostics"][0]["details"]["token_hex"] == bad.hex()
    assert all(r["segments"] == [] for r in batch["records"][0]["rows"])


def test_a2m_native_structural_error_precedes_digital_error():
    content = b">a\nA\n>b\n?AC\n"
    batch = decode(content, "a2m", "DNA")
    assert batch["diagnostics"][0]["code"] == "a2m_consensus_count_mismatch"
    assert batch["diagnostics"][0]["details"]["actual"] == 2


def test_a2m_native_digital_error_precedes_structural_length_assertion():
    batch = decode(b">a\nAo?\n", "a2m", "DNA")
    assert batch["records"][0]["native_status_equivalent"] == 7
    assert batch["diagnostics"][0]["code"] == "invalid_sequence_byte"
    assert batch["diagnostics"][0]["details"]["token_hex"] == "3f"


def test_a2m_empty_row_can_receive_defined_insertion_slot_gaps():
    content = b">empty\n>inserted\nac\n"
    batch = decode(content, "a2m", "DNA")
    assert_contract(batch, content)
    record = batch["records"][0]
    assert record["reader_state"] == "complete"
    assert record["column_annotations"]["RF"]["text"] == ".."
    assert [r["aligned_sequence"] for r in record["rows"]] == ["--", "ac"]


def test_a2m_zero_column_native_ok_is_not_usable_alignment_geometry():
    content = b">empty\n>ignored\nO . \t\n"
    batch = decode(content, "a2m", "DNA")
    assert_contract(batch, content)
    record = batch["records"][0]
    assert record["native_status_equivalent"] == 0
    assert record["reader_state"] == "invalid"
    assert record["column_count"] == 0
    assert [r["aligned_sequence"] for r in record["rows"]] == ["", ""]
    assert not any(r["geometry_valid"] for r in record["rows"])
    assert batch["diagnostics"][0]["code"] == "empty_alignment"
