"""Pure supplied-byte checks; retained 644 text is pinned, never rerun native."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode import blast_preparation_inputs as readers
from gene_annotation_episode.blast_preparation_contracts import validate_blast_preparation_document
from gene_annotation_episode.domain import ContractError


PACKET = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_preparation_inputs_2026-10-28_648"


def occurrence(raw, *, oid="source", role="stdout", fmt="text", direction="output", completeness="complete"):
    return {"occurrence_id": oid, "direction": direction, "role": role, "ordinal": 0,
        "artifact_ref": "retained/" + oid, "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw), "native_format": fmt, "completeness": completeness,
        "native_path": "/selected/" + oid}


def native(identifier):
    rows = json.loads((PACKET / "native_text_fixtures.json").read_text())["fixtures"]
    row = next(row for row in rows if row["id"] == identifier)
    raw = row["contents_utf8"].encode("utf-8")
    assert hashlib.sha256(raw).hexdigest() == row["sha256"]
    assert len(raw) == row["size_bytes"]
    return raw


def read(parser, raw, **options):
    return parser(raw, occurrence=occurrence(raw), **options)


def fields(document):
    return {row["field_name"]: row for row in document["native_fields"]}


def codes(document):
    return {row["code"] for row in document["failures"]}


def test_profile_whitespace_list_preserves_duplicates_literal_quotes_and_utf8_byte_spans():
    raw = '  α.asn\tb.asn\r\nα.asn  "two words"\n#literal\n'.encode()
    record = read(readers.parse_blast_preparation_list, raw, grammar="profile_whitespace_tokens")
    expected = ["α.asn", "b.asn", "α.asn", '"two', 'words"', "#literal"]
    assert [row["original_token"] for row in record["rows"]] == expected
    assert [(r["line_number"], r["token_ordinal"]) for r in record["rows"]] == [(1, 0), (1, 1), (2, 0), (2, 1), (2, 2), (3, 0)]
    assert [(r["start_byte"], r["end_byte"]) for r in record["rows"][:3]] == [(2, 8), (9, 14), (16, 22)]
    for row in record["rows"]:
        assert raw[row["start_byte"]:row["end_byte"]].decode() == row["original_token"]
    assert record["failures"] == []


def test_database_lines_are_trimmed_whole_names_not_shell_or_profile_tokens():
    raw = ' \t db B \t\n\n db_A\n db B\n#literal\n"name"\n'.encode()
    record = read(readers.parse_blast_preparation_list, raw, grammar="blast_database_lines")
    assert [r["original_token"] for r in record["rows"]] == ["db B", "db_A", "db B", "#literal", '"name"']
    assert [r["line_number"] for r in record["rows"]] == [1, 3, 4, 5, 6]
    assert all(r["token_ordinal"] == 0 for r in record["rows"])
    for row in record["rows"]:
        assert raw[row["start_byte"]:row["end_byte"]].decode() == row["original_token"]


@pytest.mark.parametrize("grammar", ["shell", "", None, []])
def test_unselected_list_grammar_is_rejected(grammar):
    with pytest.raises(ContractError, match="preparation_list_grammar"):
        read(readers.parse_blast_preparation_list, b"x\n", grammar=grammar)


def test_list_empty_and_invalid_utf8_do_not_create_entries():
    assert codes(read(readers.parse_blast_preparation_list, b" \t\n", grammar="blast_database_lines")) == {"native_document_invalid"}
    raw = b"first\n\xff\nlast\n"
    document = read(readers.parse_blast_preparation_list, raw, grammar="profile_whitespace_tokens")
    assert [r["original_token"] for r in document["rows"]] == ["first", "last"]
    assert [r["start_byte"] for r in document["rows"]] == [0, 8]
    assert document["failures"][0]["line_number"] == 2


@pytest.mark.parametrize("case,order", [("08_alias_inline", ["db_a/tiny", "db_b/tiny"]), ("09_alias_file", ["db_b/tiny", "db_a/tiny"])])
def test_retained_aggregate_alias_preserves_selection_order_and_native_counts(case, order):
    raw = native("retained_native/" + case + "/aggregate.nal")
    result = read(readers.parse_blast_alias_document, raw)
    assert [t["value"] for t in result["rows"][1]["tokens"]] == order
    assert [t["native_lexeme"] for t in result["rows"][1]["tokens"]] == ['"' + p + '"' for p in order]
    assert result["rows"][1]["value_lexeme"].endswith(" ")
    assert fields(result)["database_sequence_count"]["value"] == 6
    assert fields(result)["database_residue_count"]["value"] == 66
    assert fields(result)["database_sequence_count"]["line_number"] == 6
    assert result["failures"] == []


def test_retained_binary_alias_length_13_stays_native_reported_not_extracted_12():
    raw = native("retained_binary_alias/01_binary_subset_alias/subset.nal")
    document = read(readers.parse_blast_alias_document, raw)
    assert [r["native_key"] for r in document["rows"]] == ["TITLE", "DBLIST", "SEQIDLIST", "NSEQ", "LENGTH"]
    assert document["rows"][2]["tokens"] == [{"ordinal": 0, "value": "bound.bsl", "native_lexeme": "bound.bsl"}]
    length = fields(document)["database_residue_count"]
    assert (length["value"], length["native_lexeme"], length["line_number"], length["unit"], length["value_basis"]) == (13, "13", 8, "symbols", "native_reported")


def test_alias_quoted_order_repeated_tokens_unknown_keys_and_no_shell_unescaping():
    raw = b'DBLIST "dir with spaces/db" repeat "repeat" "dir\\db"\nVDBLIST "vdb"\nTAXIDLIST "ids list"\nCUSTOM exact  text \n'
    document = read(readers.parse_blast_alias_document, raw)
    assert [t["value"] for t in document["rows"][0]["tokens"]] == ["dir with spaces/db", "repeat", "repeat", "dir\\db"]
    assert document["rows"][3] == {"row_ordinal": 3, "line_number": 4, "native_key": "CUSTOM", "value_lexeme": "exact  text ", "tokens": []}
    assert document["native_fields"] == []
    assert document["failures"] == []


def test_alias_malformed_numeric_quote_and_duplicate_counts_preserve_other_facts():
    raw = b'TITLE retained\nDBLIST "unterminated\nNSEQ 1\nNSEQ 2\nLENGTH nope\n'
    document = read(readers.parse_blast_alias_document, raw)
    assert len(document["rows"]) == 5
    assert document["rows"][1]["value_lexeme"] == '"unterminated'
    assert [f["value"] for f in document["native_fields"] if f["field_name"] == "database_sequence_count"] == [1, 2]
    assert fields(document)["database_residue_count"]["value"] is None
    assert fields(document)["database_residue_count"]["missing_reason"] == "native_field_invalid"
    assert codes(document) == {"native_row_invalid", "database_metadata_conflict", "native_document_invalid"}


@pytest.mark.parametrize("case,count", [("03_seqid_unbound_info", 2), ("05_seqid_bound_info", 1)])
def test_retained_seqid_info_preserves_stored_count_and_located_native_dates(case, count):
    raw = native("retained_native/" + case + "/stdout")
    document = read(readers.parse_blast_seqid_list_info, raw)
    found = fields(document)
    assert found["identifier_list_count"]["value"] == count
    assert found["identifier_list_count"]["unit"] == "identifiers"
    assert found["identifier_list_count"]["line_number"] == 1
    assert found["identifier_list_created_at_native"]["value"] == "Oct 28, 2026  06:59 PM"
    assert document["rows"] == []
    assert document["failures"] == []
    if count == 1:
        assert found["identifier_list_database_length"]["value"] == 33
        assert found["identifier_list_database_length"]["unit"] == "symbols"
        assert found["identifier_list_database_volumes"]["value"] == ["tiny"]
        assert found["identifier_list_database_volumes"]["line_number"] == 7
        assert found["identifier_list_database_volumes"]["native_lexeme"] == "\tDB Vols: \n\t\ttiny"
        assert found["identifier_list_database_created_at_native"]["value"] == "Oct 28, 2026  6:05 PM"
    else:
        assert "identifier_list_database_length" not in found


def test_seqid_empty_invalid_duplicate_and_unrecognized_lines_remain_qualified():
    empty = read(readers.parse_blast_seqid_list_info, b"")
    assert empty["native_fields"] == [] and "native_document_invalid" in codes(empty)
    invalid = read(readers.parse_blast_seqid_list_info, b"Seqidlist file is not in blast db version 5 format\n")
    assert "native_format_unsupported" in codes(invalid)
    document = read(readers.parse_blast_seqid_list_info, b"Num of Ids: nope\nNum of Ids: 0\nTitle: \nCreate Date: native date\nFuture: 4\n\tDB Vols: \n")
    assert [f["value"] for f in document["native_fields"] if f["field_name"] == "identifier_list_count"] == [None, 0]
    assert fields(document)["identifier_list_database_volumes"]["value"] is None
    assert fields(document)["identifier_list_title"]["value"] == ""
    assert {"native_document_invalid", "database_metadata_conflict", "native_diagnostic_unrecognized"} <= codes(document)


def test_retained_gi_diagnostic_count_is_converted_occurrences_not_stored_ids():
    raw = native("retained_native/01_gi_convert/stderr")
    document = read(readers.parse_blast_aliastool_diagnostics, raw)
    assert document["rows"] == [{"line_number": 1, "category": "converted_gi_count", "native_lexeme": "Converted 3 GIs into binary GI file", "native_count": 3}]
    assert list(fields(document)) == ["identifier_list_converted_count"]
    assert fields(document)["identifier_list_converted_count"]["unit"] == "identifier_occurrences"
    assert document["failures"] == []


@pytest.mark.parametrize("identifier,count", [("retained_native/08_alias_inline/stderr", 6), ("retained_binary_alias/01_binary_subset_alias/stderr", 1)])
def test_retained_alias_created_diagnostic_keeps_native_count(identifier, count):
    document = read(readers.parse_blast_aliastool_diagnostics, native(identifier))
    assert document["rows"][0]["category"] == "created_alias_sequence_count"
    assert fields(document)["database_sequence_count"]["value"] == count


def test_retained_failed_text_subset_is_not_replaced_by_binary_subset_success():
    document = read(readers.parse_blast_aliastool_diagnostics, native("retained_native/06_subset_alias/stderr"))
    assert document["rows"][0]["category"] == "native_error"
    assert document["native_fields"] == []
    assert codes(document) == {"preparation_not_successful"}
    assert document["failures"][0]["native_returncode"] is None


def test_retained_new_index_locates_effective_hint_ignored_output_and_removed_member():
    document = read(readers.parse_makembindex_diagnostics, native("retained_native/10_new_index/stderr"))
    rows = document["rows"]
    assert [r["category"] for r in rows] == ["parameter_adjusted", "parameter_ignored", "member_created", "empty_member_removed"]
    adjusted = rows[0]["parameter_observation"]
    assert (adjusted["parameter"], adjusted["value"], adjusted["effect"], adjusted["scope_key"], adjusted["line_number"]) == ("ws_hint", 10, "effective", "source", 1)
    assert rows[1]["parameter_observation"]["parameter"] == "output_prefix"
    assert rows[1]["parameter_observation"]["value"] is None
    assert rows[2]["native_output_reference"].endswith("/db/tiny.00.idx")
    assert rows[3]["native_output_reference"].endswith("/db/tiny.01.idx")
    assert document["native_fields"] == []
    assert document["failures"] == []


def test_retained_old_index_parameters_are_ignored_without_fabricated_effective_values():
    document = read(readers.parse_makembindex_diagnostics, native("retained_native/11_old_index/stderr"))
    assert [(r["parameter_observation"]["parameter"], r["parameter_observation"]["value"], r["parameter_observation"]["effect"]) for r in document["rows"][:2]] == [("stride", None, "ignored"), ("ws_hint", None, "ignored")]
    assert document["rows"][2]["native_output_reference"] == "old.00.idx"
    empty = read(readers.parse_makembindex_diagnostics, native("retained_native/12_index_filters/stdout"))
    assert empty["rows"] == [] and empty["native_fields"] == []


def test_retained_successful_profile_aux_has_native_length_k_and_only_four_header_parameters():
    raw = native("retained_profile28/01_rps_existing28row_profile/profiles.aux")
    document = read(readers.parse_makeprofiledb_aux, raw)
    assert len(raw) == 70
    assert document["rows"] == [{"native_profile_ordinal": 0, "sequence_length": 320,
        "karlin_k": 0.0375672, "length_line_number": 9, "k_line_number": 10}]
    assert [(r["parameter"], r["value"], r["line_number"]) for r in document["parameter_observations"]] == [("matrix", "BLOSUM62", 1), ("gap_open", 11, 2), ("gap_extend", 1, 3), ("scale", 1.0, 8)]
    assert all(r["scope_key"] == r["occurrence_id"] == "source" for r in document["parameter_observations"])
    assert document["native_fields"] == [] and document["failures"] == []
    assert validate_blast_preparation_document(json.loads(json.dumps(document))) == document


def test_aux_bad_middle_pair_keeps_original_native_ordinals_and_valid_later_pair():
    header = b"BLOSUM62\n11\n1\n0.000000e+00\n0.000000e+00\n0\n0\n1.000000\n"
    document = read(readers.parse_makeprofiledb_aux, header + b"320\n.0375672\nbad\n.05\n42\n.1\n")
    assert [(r["native_profile_ordinal"], r["sequence_length"], r["length_line_number"]) for r in document["rows"]] == [(0, 320, 9), (2, 42, 13)]
    assert document["failures"][0]["line_number"] == 11


@pytest.mark.parametrize("bad", [b"nan", b"inf", b"1e999", b"true", b"1_000"])
def test_aux_nonfinite_or_non_native_k_is_invalid_not_zero(bad):
    raw = native("retained_profile28/01_rps_existing28row_profile/profiles.aux")
    document = read(readers.parse_makeprofiledb_aux, raw.rsplit(b"3.756720e-02", 1)[0] + bad + b"\n")
    assert document["rows"] == []
    assert codes(document) == {"native_row_invalid"}


def test_aux_missing_header_and_truncated_final_pair_preserve_partial_information():
    empty = read(readers.parse_makeprofiledb_aux, b"")
    assert empty["rows"] == []
    assert all(r["value"] is None and r["effect"] == "unknown" and r["missing_reason"] == "native_field_absent" for r in empty["parameter_observations"])
    raw = native("retained_profile28/01_rps_existing28row_profile/profiles.aux")
    document = read(readers.parse_makeprofiledb_aux, raw + b"7\n")
    assert document["rows"][0]["sequence_length"] == 320
    assert document["failures"][0]["line_number"] == 11
    changed = read(readers.parse_makeprofiledb_aux, raw.replace(b"0.000000e+00", b"1.000000e+00", 1))
    assert "native_document_invalid" in codes(changed)
    assert changed["native_fields"] == [] and changed["rows"] == document["rows"]


@pytest.mark.parametrize("case,category,reference", [("13_profile_rps", "profile_size_conflict", None), ("14_profile_delta", "missing_weighted_frequencies", "profiles/pssm_freq_ratios.asn"), ("15_profile_cobalt", "missing_core_blocks", "profiles/pssm_freq_ratios.asn")])
def test_retained_failed_profile_diagnostics_remain_specific(case, category, reference):
    document = read(readers.parse_makeprofiledb_diagnostics, native("retained_native/" + case + "/stderr"))
    assert document["rows"][0]["category"] == category
    assert document["rows"][0]["native_reference"] == reference
    assert document["native_fields"] == []
    assert codes(document) == {"preparation_not_successful"}


def test_profile_exclusions_preserve_repeated_reference_without_input_membership():
    raw = b"Warning: repeat.asn was excluded: due to too few independent observations\nWarning: repeat.asn was excluded: it conatins an invalid CD\n"
    document = read(readers.parse_makeprofiledb_diagnostics, raw)
    assert [r["native_reference"] for r in document["rows"]] == ["repeat.asn", "repeat.asn"]
    assert [r["category"] for r in document["rows"]] == ["excluded_low_observations", "excluded_invalid"]
    assert document["failures"] == []
    assert all(set(r) == {"line_number", "category", "native_reference", "native_lexeme"} for r in document["rows"])


@pytest.mark.parametrize("message,category,reference", [
    ("Error: INPUT ERROR: p.asn contains no frequency ratios.", "missing_frequency_ratios", "p.asn"),
    ("Error: INPUT ERROR: p.asn contains no observations information for building delta database", "missing_independent_observations", "p.asn"),
    ("Error: ERROR: Gap open penalties do not match", "parameter_conflict", None),
    ("Error: ERROR: Scaling factors do not match", "parameter_conflict", None),
    ("Error: ERROR: Number of frequencies and observations columns do not match in p.asn", "profile_size_conflict", "p.asn"),
    ("Error: INPUT ERROR: p.asn does not exists", "native_error", "p.asn"),
])
def test_source_grounded_additional_profile_diagnostics(message, category, reference):
    result = read(readers.parse_makeprofiledb_diagnostics, (message + "\n").encode())
    assert result["rows"][0]["category"] == category
    assert result["rows"][0]["native_reference"] == reference


@pytest.mark.parametrize("parser", [readers.parse_blast_aliastool_diagnostics, readers.parse_makembindex_diagnostics, readers.parse_makeprofiledb_diagnostics])
def test_empty_diagnostics_never_invent_measurements_and_unknown_lines_are_retained(parser):
    document = read(parser, b"\n")
    assert document["rows"] == [] and document["native_fields"] == []
    unknown = read(parser, "Future diagnostic α 4\n".encode())
    assert unknown["rows"][0]["category"] == "unknown"
    assert unknown["rows"][0]["native_lexeme"] == "Future diagnostic α 4"
    assert codes(unknown) == {"native_diagnostic_unrecognized"}


@pytest.mark.parametrize("parser", [readers.parse_blast_alias_document, readers.parse_blast_seqid_list_info, readers.parse_blast_aliastool_diagnostics, readers.parse_makembindex_diagnostics, readers.parse_makeprofiledb_aux, readers.parse_makeprofiledb_diagnostics])
def test_every_parser_checks_actual_supplied_identity_and_bytes_type(parser):
    with pytest.raises(ContractError, match="input_identity_mismatch"):
        parser(b"other", occurrence=occurrence(b"source"))
    with pytest.raises(ContractError, match="bytes_required"):
        parser("source", occurrence=occurrence(b"source"))


def test_partial_capture_remains_qualified_and_occurrence_inputs_are_unchanged():
    raw = native("retained_profile28/01_rps_existing28row_profile/profiles.aux")
    source = occurrence(raw, oid="actual-aux", role="profile_file", fmt="blast_profile_aux_text", completeness="partial")
    before = deepcopy(source)
    document = readers.parse_makeprofiledb_aux(raw, occurrence=source)
    assert source == before
    assert document["occurrence_id"] == "actual-aux"
    assert all(r["scope_key"] == "actual-aux" for r in document["parameter_observations"])
    assert codes(document) == {"output_completeness_unestablished"}
    assert document["rows"][0]["karlin_k"] == 0.0375672


def test_pure_parsing_and_saved_validation_do_not_open_paths_or_start_native(monkeypatch):
    raw = native("retained_profile28/01_rps_existing28row_profile/profiles.aux")
    source = occurrence(raw)

    def forbidden(*args, **kwargs):
        raise AssertionError("reader attempted external work")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("pathlib.Path.open", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    document = readers.parse_makeprofiledb_aux(raw, occurrence=source)
    assert validate_blast_preparation_document(json.loads(json.dumps(document))) == document
    assert document["rows"][0]["sequence_length"] == 320
