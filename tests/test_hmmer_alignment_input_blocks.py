"""Block input contract cases; literal byte strings are authored edge cases.

Explicit fixture tests read retained cmemit output or upstream Easel inputs
unchanged. These tests perform no native execution and define no scorer.
"""

import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_alignment_input_blocks import decode_native_block_alignment


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "resources/software/infernal-1.1.5/easel/esl_msa_testfiles"
EMISSIONS = ROOT / "verification/tool_graders_infernal_preparation_emission_2026-10-26_250/native"
FORMATS = ("psiblast", "selex", "clustal", "clustallike")
BATCH_FIELDS = {
    "version", "format", "alphabet", "records", "diagnostics", "end_state",
    "next_byte_offset", "trailing_range",
}
RECORD_FIELDS = {
    "record_ordinal", "reader_state", "native_status_equivalent", "byte_start", "byte_end",
    "line_start", "line_end", "header_valid", "column_count", "declared_row_count",
    "declared_column_count", "block_count", "rows", "column_annotations", "events", "diagnostics",
}
ROW_FIELDS = {
    "row_ordinal", "name", "name_bytes_hex", "description", "aligned_sequence", "segments",
    "annotation_fragments", "column_annotations", "geometry_valid", "symbols_valid",
    "identity_unambiguous", "diagnostics",
}
EVENT_FIELDS = {"event_ordinal", "kind", "block_index", "row_ordinal", "tag", "raw", "value", "locator"}
SEGMENT_FIELDS = {
    "event_ordinal", "byte_start", "byte_end", "column_start", "column_end", "aligned_start",
    "aligned_end", "operation", "basis", "source_text", "decoded_text",
}
DIAGNOSTIC_FIELDS = {
    "code", "record_ordinal", "row_ordinal", "event_ordinal", "byte_start", "byte_end", "details",
}


def decode(content, fmt="psiblast", alphabet="amino"):
    batch = decode_native_block_alignment(content, declared_format=fmt, alphabet=alphabet)
    assert_contract(batch, content)
    return batch


def assert_contract(batch, content):
    assert set(batch) == BATCH_FIELDS
    assert json.loads(json.dumps(batch)) == batch
    if batch["trailing_range"] is not None:
        assert batch["trailing_range"] == {"byte_start": batch["next_byte_offset"], "byte_end": len(content)}
    for record in batch["records"]:
        assert set(record) == RECORD_FIELDS
        assert record["declared_row_count"] is None
        assert record["declared_column_count"] is None
        # SELEX's native ErrorInBlock may rewind inside already inspected Events.
        assert b"".join(e["raw"].encode("utf-8", "surrogateescape") for e in record["events"]) == content[:record["byte_end"]]
        for ordinal, event in enumerate(record["events"]):
            assert set(event) == EVENT_FIELDS
            assert event["event_ordinal"] == ordinal
            locator = event["locator"]
            assert set(locator) == {"line", "byte_start", "byte_end"}
            assert event["raw"].encode("utf-8", "surrogateescape") == content[locator["byte_start"]:locator["byte_end"]]
        for ordinal, row in enumerate(record["rows"]):
            assert set(row) == ROW_FIELDS
            assert row["row_ordinal"] == ordinal
            assert row["name"].encode("utf-8", "surrogateescape").hex() == row["name_bytes_hex"]
            assert row["description"] is None
            if row["aligned_sequence"] is None:
                assert row["segments"] == []
                assert row["geometry_valid"] is False
            else:
                assert "".join(s["decoded_text"] for s in row["segments"]) == row["aligned_sequence"]
            aligned = 0
            for segment in row["segments"]:
                assert set(segment) == SEGMENT_FIELDS
                assert segment["aligned_start"] == aligned
                aligned = segment["aligned_end"]
                assert aligned - segment["aligned_start"] == len(segment["decoded_text"])
                if segment["operation"] == "native_gap":
                    assert segment["basis"] == "selex_physical_columns"
                    assert all(segment[key] is None for key in ("event_ordinal", "byte_start", "byte_end", "column_start", "column_end"))
                    assert segment["source_text"] == ""
                else:
                    event = record["events"][segment["event_ordinal"]]
                    base = event["locator"]["byte_start"]
                    assert segment["byte_start"] == base + segment["column_start"]
                    assert segment["byte_end"] == base + segment["column_end"]
                    assert segment["source_text"].encode("utf-8", "surrogateescape") == content[segment["byte_start"]:segment["byte_end"]]
                if segment["operation"] == "ignore":
                    assert segment["basis"] == "input_ignored"
                    assert segment["decoded_text"] == ""
            for annotation in row["column_annotations"].values():
                assert set(annotation) == {"text", "valid", "basis", "fragments"}
            assert all(fragment in record["events"] for fragment in row["annotation_fragments"])
        for annotation in record["column_annotations"].values():
            assert set(annotation) == {"text", "valid", "basis", "fragments"}
        for diagnostic in record["diagnostics"]:
            assert set(diagnostic) == DIAGNOSTIC_FIELDS
            assert set(diagnostic["details"]) == {"expected", "actual", "token_hex"}
    for diagnostic in batch["diagnostics"]:
        assert set(diagnostic) == DIAGNOSTIC_FIELDS
        assert set(diagnostic["details"]) == {"expected", "actual", "token_hex"}


def complete(batch, width, blocks):
    assert batch["end_state"] == "eof"
    assert batch["diagnostics"] == []
    assert len(batch["records"]) == 1
    record = batch["records"][0]
    assert record["reader_state"] == "complete"
    assert record["native_status_equivalent"] == 0
    assert record["column_count"] == width
    assert record["block_count"] == blocks
    assert record["header_valid"] is True
    assert all(row["geometry_valid"] and row["symbols_valid"] and row["identity_unambiguous"] for row in record["rows"])
    return record


def failed(batch, code, status=7):
    assert len(batch["records"]) == 1
    record = batch["records"][0]
    assert record["reader_state"] != "complete"
    assert record["native_status_equivalent"] == status
    assert code in [d["code"] for d in record["diagnostics"]]
    assert all(not row["geometry_valid"] for row in record["rows"])
    return record


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("content", [b"", b" \t\r\n\x00\t\n"])
def test_empty_input_has_no_alignment_occurrence(fmt, content):
    batch = decode(content, fmt)
    assert batch["records"] == []
    assert batch["end_state"] == "eof"
    assert batch["next_byte_offset"] == len(content)
    assert batch["trailing_range"] is None
    assert batch["diagnostics"][0]["code"] == "empty_alignment"
    assert batch["diagnostics"][0]["details"]["actual"] == 0


@pytest.mark.parametrize("content,fmt,alphabet,error", [
    ("a AC\n", "selex", "DNA", "hmmer_alignment_content_invalid"),
    (b"a AC\n", "stockholm", "DNA", "hmmer_alignment_format_invalid"),
    (b"a AC\n", "CLUSTAL", "DNA", "hmmer_alignment_format_invalid"),
    (b"a AC\n", None, "DNA", "hmmer_alignment_format_invalid"),
    (b"a AC\n", "selex", None, "hmmer_alignment_alphabet_invalid"),
    (b"a AC\n", "selex", "dna", "hmmer_alignment_alphabet_invalid"),
])
def test_argument_misuse(content, fmt, alphabet, error):
    with pytest.raises(ValueError, match=f"^{error}$"):
        decode_native_block_alignment(content, declared_format=fmt, alphabet=alphabet)


def test_psiblast_ordered_duplicate_occurrences_case_rf_and_crlf():
    content = b"dup  A-c-\r\ndup  G-t-\r\n\r\ndup  T-\r\ndup  C-"
    record = complete(decode(content), 6, 2)
    assert [row["name"] for row in record["rows"]] == ["dup", "dup"]
    assert [row["aligned_sequence"] for row in record["rows"]] == ["A-c-T-", "G-t-C-"]
    assert record["column_annotations"]["RF"]["text"] == "x-.-x-"
    assert record["column_annotations"]["RF"]["basis"] == "native_format_derivation"
    assert all(e["kind"] != "annotation" for e in record["events"])
    assert record["rows"][0]["segments"][1]["column_start"] == 5


def test_psiblast_case_failure_precedes_name_storage_and_keeps_prefix():
    record = failed(decode(b"a Aa\nb AA\nunused AA\n"), "psiblast_case_conflict")
    assert [row["name"] for row in record["rows"]] == ["a"]
    assert record["rows"][0]["aligned_sequence"] == "Aa"
    assert record["events"][-1]["raw"] == "b AA\n"


@pytest.mark.parametrize("content,code", [
    (b"a AA\nb  AA\n", "block_geometry_mismatch"),
    (b"a AA\nb A\n", "block_geometry_mismatch"),
    (b"a A.\n", "invalid_sequence_byte"),
    (b"a AO\n", "invalid_sequence_byte"),
    (b"a Ao\n", "invalid_sequence_byte"),
    (b"a A_\n", "invalid_sequence_byte"),
    (b"a A*\n", "invalid_sequence_byte"),
    (b"a A~\n", "invalid_sequence_byte"),
    (b"a AC 2\n", "invalid_sequence_byte"),
    (b"a A\rb\n", "invalid_sequence_byte"),
    (b"a AA\nb CC\n\na GG\n", "row_count_mismatch"),
    (b"a AA\nb CC\n\nb GG\na TT\n", "row_order_mismatch"),
    (b"a AA\n\na GG\nb TT\n", "row_count_mismatch"),
])
def test_psiblast_native_rejections(content, code):
    failed(decode(content), code)


def test_psiblast_nul_sequence_is_unknown_but_rf_remains_neutral():
    record = complete(decode(b"a A\x00-\n", alphabet="DNA"), 3, 1)
    assert record["rows"][0]["aligned_sequence"] == "AN-"
    assert record["column_annotations"]["RF"]["text"] == "x--"
    alias = next(s for s in record["rows"][0]["segments"] if s["operation"] == "symbol_alias")
    assert alias["source_text"] == "\x00"
    assert alias["decoded_text"] == "N"


@pytest.mark.parametrize("fmt,header,consensus", [
    ("psiblast", b"", b""),
    ("clustal", b"CLUSTAL alignment\n", b" **\n"),
])
def test_c_visible_nul_name_and_full_token_continuation(fmt, header, consensus):
    first = header + b"a\x00z AC\n" + consensus
    record = complete(decode(first, fmt), 2, 1)
    assert record["rows"][0]["name"] == "a"
    assert record["rows"][0]["name_bytes_hex"] == "61"
    assert b"a\x00z" in record["events"][-1 if fmt == "psiblast" else -2]["raw"].encode()
    # Continuation geometry is block-local; the C-visible prefix can match.
    record = complete(decode(first + b"\na GT\n" + consensus, fmt), 4, 2)
    assert record["rows"][0]["aligned_sequence"] == "ACGT"
    failed(decode(first + b"\na\x00z GT\n" + consensus, fmt), "row_order_mismatch")


def test_selex_physical_gaps_and_all_native_annotation_tags():
    content = (
        b"# ordinary comment\n#=RF   x..x\n#=MM   m..m\n#=CS   >..<\n"
        b"long   AC G\n#=SS   (..)\n#=SA   1234\nx    ATCGTT\nblank\n"
    )
    record = complete(decode(content, "selex", "DNA"), 6, 1)
    assert [row["aligned_sequence"] for row in record["rows"]] == ["--AC-G", "ATCGTT", "------"]
    assert {tag: ann["text"] for tag, ann in record["column_annotations"].items()} == {
        "RF": "..x..x", "MM": "..m..m", "SS_cons": "..>..<",
    }
    first = record["rows"][0]
    assert {tag: ann["text"] for tag, ann in first["column_annotations"].items()} == {"SS": "..(..)", "SA": "..1234"}
    assert [e["tag"] for e in first["annotation_fragments"]] == ["SS", "SA"]
    assert record["column_annotations"]["SS_cons"]["fragments"][0]["tag"] == "CS"
    gaps = [s for s in first["segments"] if s["operation"] == "native_gap"]
    assert [(s["aligned_start"], s["aligned_end"]) for s in gaps] == [(0, 2)]
    alias = next(s for s in first["segments"] if s["operation"] == "symbol_alias")
    assert (alias["column_start"], alias["aligned_start"], alias["decoded_text"]) == (9, 4, "-")


def test_selex_mm_multiplicity_last_value_wins_each_block():
    content = b"#=MM ab\n#=MM cd\na    AC\n\n#=MM ef\n#=MM gh\na    GT\n"
    record = complete(decode(content, "selex"), 4, 2)
    assert record["column_annotations"]["MM"]["text"] == "cdgh"
    assert len(record["column_annotations"]["MM"]["fragments"]) == 4
    assert record["rows"][0]["aligned_sequence"] == "ACGT"


def test_selex_column_zero_comments_and_indented_sequence_name():
    record = complete(decode(b"# ignored\na AC\n # XX\n# ignored again\n", "selex"), 3, 1)
    assert [row["name"] for row in record["rows"]] == ["a", "#"]
    assert [row["aligned_sequence"] for row in record["rows"]] == ["AC-", "-XX"]
    assert [e["kind"] for e in record["events"]].count("comment") == 2


def test_selex_missing_later_data_uses_native_name_right_edge():
    # The token-only long name contributes rpos even though lpos is -1.
    record = complete(decode(b"a AC\nverylongname\n", "selex"), 10, 1)
    assert [r["aligned_sequence"] for r in record["rows"]] == ["AC--------", "----------"]


@pytest.mark.parametrize("terminator", [b"\n", b"\r\n"])
def test_selex_error_rewinds_before_terminator_but_retains_inspected_block(terminator):
    lines = [b"a    AC", b"#=SS xx", b"#=SS yy", b"b    AC", b"", b"unread AC"]
    content = terminator.join(lines)
    batch = decode(content, "selex")
    record = failed(batch, "annotation_cardinality_mismatch")
    error_start = len(lines[0]) + len(lines[1]) + 2 * len(terminator)
    expected_cursor = error_start + len(lines[2])
    assert batch["next_byte_offset"] == expected_cursor
    assert content[expected_cursor:expected_cursor + len(terminator)] == terminator
    assert record["byte_end"] > expected_cursor
    assert record["events"][-1]["kind"] == "blank"
    assert record["diagnostics"][0]["event_ordinal"] == 2


@pytest.mark.parametrize("content,code", [
    (b"#=SS xx\na    AC\n", "annotation_order_mismatch"),
    (b"#=SA xx\na    AC\n", "annotation_order_mismatch"),
    (b"#=RF xx\n#=RF yy\na    AC\n", "annotation_cardinality_mismatch"),
    (b"#=CS xx\n#=CS yy\na    AC\n", "annotation_cardinality_mismatch"),
    (b"a AC\n#=SA xx\n#=SA yy\n", "annotation_cardinality_mismatch"),
    (b"a AC\nb GT\n\na AC\n", "row_count_mismatch"),
    (b"a AC\nb GT\n\nb AC\na GT\n", "row_order_mismatch"),
    (b"#=RF xx\na    AC\n\na    GT\n#=RF xx\n", "annotation_order_mismatch"),
    (b"a AC\tG\n", "invalid_sequence_byte"),
])
def test_selex_native_rejections(content, code):
    failed(decode(content, "selex"), code)


@pytest.mark.parametrize("content,corner", [
    (b"blank\na AC\n", "selex_first_data_missing"),
    (b"a AC\nb \v\n", "selex_negative_data_width"),
    (b"#=RF xx\n", "selex_no_sequence_rows"),
])
def test_selex_unestablished_source_corners(content, corner):
    batch = decode(content, "selex")
    record = failed(batch, "native_source_semantics_unestablished", None)
    assert batch["end_state"] == "source_semantics_unestablished"
    assert record["diagnostics"][-1]["details"]["actual"] == corner


def test_selex_reversible_names_and_digital_nul_alias():
    record = complete(decode(b"\xff\xc3\xa9 A\x00C\n", "selex", "DNA"), 3, 1)
    assert record["rows"][0]["name_bytes_hex"] == "ffc3a9"
    assert record["rows"][0]["aligned_sequence"] == "ANC"


def test_selex_internal_nonascii_digital_error_differs_from_ctype_edge():
    record = failed(decode(b"a A\xffC\n", "selex"), "invalid_sequence_byte")
    assert record["rows"][0]["aligned_sequence"] == "A"
    record = failed(decode(b"a AC\xff\n", "selex"), "native_source_semantics_unestablished", None)
    assert record["diagnostics"][0]["details"]["actual"] == "nonascii_ctype"


@pytest.mark.parametrize("fmt,header,ok", [
    ("clustal", b"CLUSTAL 2.1 multiple sequence alignment", True),
    ("clustal", b"CLUSTALW alignment", True),
    ("clustal", b"MUSCLE multiple sequence alignment", False),
    ("clustallike", b"MUSCLE multiple sequence alignment", True),
    ("clustal", b"CLUSTAL Alignment", False),
    ("clustallike", b"MUSCLE", False),
    ("clustal", b"CLUSTALalignment", False),
    ("clustal", b"CLUSTAL\x00alignment", True),
])
def test_clustal_header_rules(fmt, header, ok):
    batch = decode(header + b"\na AC\n **\n", fmt)
    if ok:
        complete(batch, 2, 1)
    else:
        failed(batch, "invalid_header")


def test_clustal_trailing_tokens_ignored_and_consensus_is_not_rf():
    content = b"CLUSTAL alignment\n\na AC 999 anything \xff\nb GT text\n **\n"
    record = complete(decode(content, "clustal"), 2, 1)
    assert [r["aligned_sequence"] for r in record["rows"]] == ["AC", "GT"]
    assert record["column_annotations"] == {}
    assert record["events"][-1]["kind"] == "consensus"
    assert record["rows"][0]["segments"][-1]["decoded_text"] == ""
    assert record["rows"][0]["segments"][-1]["source_text"].endswith("\udcff")


@pytest.mark.parametrize("suffix,ok,code", [
    (b"", False, "missing_consensus_line"),
    (b"\n", True, None),
    (b" **", True, None),
    (b"\x00\n", True, None),
    (b"\t\n", False, "missing_name"),
    (b" \t**\n", False, "empty_sequence"),
])
def test_clustal_consensus_is_required_and_tabs_are_not_consensus(suffix, ok, code):
    batch = decode(b"CLUSTAL alignment\na AC\n" + suffix, "clustal")
    if ok:
        complete(batch, 2, 1)
    else:
        failed(batch, code)


@pytest.mark.parametrize("content,code", [
    (b"CLUSTAL alignment\n", "empty_alignment"),
    (b"CLUSTAL alignment\na AC\nb  GT\n **\n", "block_geometry_mismatch"),
    (b"CLUSTAL alignment\na AC\nb G\n **\n", "block_geometry_mismatch"),
    (b"CLUSTAL alignment\na AC\nb GT\n **\n\nb AC\na GT\n **\n", "row_order_mismatch"),
    (b"CLUSTAL alignment\na AC\nb GT\n **\n\na AC\n **\n", "row_count_mismatch"),
])
def test_clustal_native_rejections(content, code):
    failed(decode(content, "clustal"), code)


@pytest.mark.parametrize("fmt,content", [
    ("psiblast", b"a A\xffC\n"),
    ("clustal", b"CLUSTAL alignment\na A\xffC\n **\n"),
    ("psiblast", b"\xff AC\n"),
    ("clustal", b"CLUSTAL alignment\n\xff AC\n **\n"),
])
def test_unestablished_nonascii_ctype_is_not_claimed_native_status_seven(fmt, content):
    record = failed(decode(content, fmt), "native_source_semantics_unestablished", None)
    assert record["diagnostics"][0]["details"]["actual"] == "nonascii_ctype"


@pytest.mark.parametrize("fmt,prefix,suffix", [
    ("psiblast", b"a AC\n\n", b"different GT\nrest AC\n"),
    ("clustal", b"CLUSTAL alignment\na AC\n **\n\n", b"CLUSTAL alignment\nrest AC\n"),
    ("selex", b"a AC\n\n", b"different GT\n\nrest AC\n"),
])
def test_malformed_whole_file_suffix_never_becomes_complete_first_msa(fmt, prefix, suffix):
    batch = decode(prefix + suffix, fmt)
    record = failed(batch, "row_order_mismatch")
    assert len(batch["records"]) == 1
    assert record["rows"][0]["aligned_sequence"] == "AC"
    assert record["block_count"] == 1
    assert batch["trailing_range"] is not None


@pytest.mark.parametrize("name,digest,width,blocks,nseq", [
    ("aligned_clustal", "aacde9e96408bb894a79665ab28dc3c3bbf2a87976123f69052a6f361701821a", 12, 1, 3),
    ("clustal_long_interleaved", "38e73055c801d84b0bafbbbbe35093d7740e324194ef626cbd2268efd20f5c1e", 74, 2, 2),
])
def test_unchanged_authentic_retained_cmemit_clustal(name, digest, width, blocks, nseq):
    content = (EMISSIONS / name / "emitted.out").read_bytes()
    assert hashlib.sha256(content).hexdigest() == digest
    record = complete(decode(content, "clustal", "RNA"), width, blocks)
    assert len(record["rows"]) == nseq
    assert len([e for e in record["events"] if e["kind"] == "consensus"]) == blocks
    assert record["column_annotations"] == {}
    if name == "aligned_clustal":
        assert [r["aligned_sequence"] for r in record["rows"]] == ["GCGC-UAAGCGC", "GCGCUAAAGCGC", "GCGAUUUAUCGU"]
    else:
        assert record["rows"][0]["aligned_sequence"] == "GGGAGUAUAGUGUACUaGGU.AACACGUAUGGGUUCAGACCGUACGGUCCUGGGUUC--UCCCCAGUACGCACA"


@pytest.mark.parametrize("name,digest,width,blocks", [
    ("selex.good.1", "6b689ba1c0c6830a6e4738d712f35afa949aeb316a9d7767242128cc4734d2a0", 20, 1),
    ("selex.good.2", "bc1a9b240181e162d57284fbd94b74b3a0d44ed4076ff4b5c9e4ca05bff0efe2", 40, 2),
])
def test_unchanged_upstream_selex_valid_inputs(name, digest, width, blocks):
    content = (UPSTREAM / "selex" / name).read_bytes()
    assert hashlib.sha256(content).hexdigest() == digest
    record = complete(decode(content, "selex"), width, blocks)
    assert [r["aligned_sequence"] for r in record["rows"]] == ["ACDEFGHIKLMNPQRSTVWY" * blocks] * 5
    if blocks == 2:
        assert record["column_annotations"]["RF"]["text"] == "x" * 40
        assert record["column_annotations"]["SS_cons"]["text"] == "x" * 40
        assert record["rows"][4]["column_annotations"]["SA"]["text"] == "x" * 40
        assert not content.endswith(b"\n") and b"\r\n" in content


def test_upstream_selex_first_missing_data_corner_stays_unavailable():
    content = (UPSTREAM / "selex" / "selex.good.3").read_bytes()
    assert hashlib.sha256(content).hexdigest() == "f5144577fc39aa34e1dfbb97e8686df4d479d58016c5a28bbfaf553ea7795a4f"
    record = failed(decode(content, "selex"), "native_source_semantics_unestablished", None)
    assert record["diagnostics"][0]["details"]["actual"] == "selex_first_data_missing"
    assert len(record["rows"]) == 7


@pytest.mark.parametrize("index,code", [
    (2, "row_count_mismatch"), (3, "annotation_order_mismatch"), (4, "annotation_order_mismatch"),
    (5, "annotation_cardinality_mismatch"), (6, "annotation_cardinality_mismatch"),
    (7, "annotation_cardinality_mismatch"), (8, "annotation_cardinality_mismatch"),
    (9, "annotation_order_mismatch"), (10, "annotation_order_mismatch"),
    (11, "annotation_order_mismatch"), (12, "annotation_order_mismatch"),
    (13, "annotation_order_mismatch"), (14, "row_order_mismatch"),
])
def test_unchanged_upstream_selex_malformed_inputs(index, code):
    content = (UPSTREAM / "selex" / f"selex.bad.{index}").read_bytes()
    failed(decode(content, "selex"), code)


@pytest.mark.parametrize("name,digest,width,blocks,nseq,alphabet", [
    ("psiblast.good.1", "cbd57eab6959a8a9ef8d7de7aff80b1f3eb08e297e02bf9d605382311b68a2e3", 165, 3, 4, "amino"),
    ("psiblast.good.2", "4bdcc103bc1e48fc94fde761e92805029e3d3db179735f3c317053bee23188df", 73, 2, 5, "RNA"),
])
def test_unchanged_upstream_psiblast_inputs(name, digest, width, blocks, nseq, alphabet):
    content = (UPSTREAM / "psiblast" / name).read_bytes()
    assert hashlib.sha256(content).hexdigest() == digest
    record = complete(decode(content, "psiblast", alphabet), width, blocks)
    assert len(record["rows"]) == nseq
    assert len(record["column_annotations"]["RF"]["text"]) == width


@pytest.mark.parametrize("payload", [b"x\x00x", b"x\xc3\xa9x"])
def test_selex_annotation_bytes_retained_without_claiming_character_indexed_support(payload):
    content = b"#=RF " + payload + b"\na    " + b"A" * len(payload) + b"\n"
    record = complete(decode(content, "selex"), len(payload), 1)
    annotation = record["column_annotations"]["RF"]
    assert annotation["text"].encode("utf-8", "surrogateescape") == payload
    assert annotation["valid"] is False
    diagnostic = record["diagnostics"][0]
    assert diagnostic["code"] == "native_source_semantics_unestablished"
    assert diagnostic["details"]["actual"] == "annotation_byte_interpretation"
    assert diagnostic["byte_start"] == 6
    assert record["native_status_equivalent"] == 0


def test_selex_overwritten_mm_byte_corner_does_not_poison_surviving_value():
    record = complete(decode(b"#=MM x\x00x\n#=MM abc\na    ACG\n", "selex"), 3, 1)
    assert record["column_annotations"]["MM"]["text"] == "abc"
    assert record["column_annotations"]["MM"]["valid"] is True
    assert len(record["column_annotations"]["MM"]["fragments"]) == 2
    assert record["diagnostics"] == []


@pytest.mark.parametrize("fmt,header,consensus", [
    ("psiblast", b"", b""), ("clustal", b"CLUSTAL alignment\n", b" **\n"),
])
def test_later_block_exceeding_exact_native_row_capacity_is_not_executed(fmt, header, consensus):
    # Source-only unsafe array case. These bytes are never passed to a native oracle.
    block = b"".join(f"s{i:02d} AC\n".encode() for i in range(16))
    content = header + block + consensus + b"\n" + block + b"s16 AC\n" + consensus
    record = failed(decode(content, fmt), "native_source_semantics_unestablished", None)
    assert record["diagnostics"][-1]["details"]["actual"] == "block_row_storage_overrun"
    assert len(record["rows"]) == 16


def test_clustal_nul_inside_sequence_token_is_unknown_alias():
    record = complete(decode(b"CLUSTAL alignment\na A\x00C\n ***\n", "clustal", "RNA"), 3, 1)
    assert record["rows"][0]["aligned_sequence"] == "ANC"


def test_upstream_selex_comment_only_input_has_no_alignment_occurrence():
    content = (UPSTREAM / "selex" / "selex.bad.1").read_bytes()
    batch = decode(content, "selex")
    assert batch["records"] == []
    assert batch["diagnostics"][0]["code"] == "empty_alignment"


def test_upstream_selex_complex_physical_layout():
    content = (UPSTREAM / "selex" / "selex.good.4").read_bytes()
    assert hashlib.sha256(content).hexdigest() == "2c583468c2268306feef69bb9c62cd90e4727738e93a6d24f2d8338ef6fd1d62"
    record = complete(decode(content, "selex", "RNA"), 31, 1)
    assert len(record["rows"]) == 11
    assert record["rows"][2]["aligned_sequence"] == "AUGGAUGCGCACC-AUCA-GGGCGUaucuau"


def test_selex_failed_sequence_retains_already_appended_annotation_values():
    content = b"#=RF xxx\n#=MM abc\n#=MM def\na    AC1\n"
    record = failed(decode(content, "selex"), "invalid_sequence_byte")
    assert record["column_annotations"]["RF"]["text"] == "xxx"
    assert record["column_annotations"]["MM"]["text"] == "def"
    assert len(record["column_annotations"]["MM"]["fragments"]) == 2
    assert record["column_annotations"]["RF"]["valid"] is False
    assert record["rows"][0]["aligned_sequence"] == "AC"


@pytest.mark.parametrize("global_rf", [True, False])
def test_selex_annotation_limitation_targets_its_own_global_or_row_map(global_rf):
    content = (
        b"#=RF x\x00x\na    ACG\n#=SS abc\nb    GTG\n#=SS def\n"
        if global_rf else
        b"a    ACG\n#=SS x\x00x\nb    GTG\n#=SS def\n"
    )
    record = complete(decode(content, "selex"), 3, 1)
    assert record["rows"][1]["column_annotations"]["SS"]["valid"] is True
    diagnostic = record["diagnostics"][0]
    assert diagnostic["details"]["actual"] == "annotation_byte_interpretation"
    if global_rf:
        assert record["column_annotations"]["RF"]["valid"] is False
        assert record["rows"][0]["column_annotations"]["SS"]["valid"] is True
        assert diagnostic["row_ordinal"] is None
    else:
        assert record["rows"][0]["column_annotations"]["SS"]["valid"] is False
        assert diagnostic["row_ordinal"] == 0
        assert record["rows"][0]["diagnostics"] == [diagnostic]
