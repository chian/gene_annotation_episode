"""Supplied synthetic inputs only; these tests do not execute GenomeComparison."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_proteome_data_contracts import validate_proteome_data
from gene_annotation_episode.bvbrc_proteome_inputs import (
    index_original_inputs, read_feature_metadata, read_feature_sequences,
    read_genome_metadata, read_protein_fasta,
)


def source(raw, *, complete="yes", body=True, reference="synthetic-supplied-input"):
    return {"content": {"source_ref": reference, "artifact_field": "artifact_ref",
            "artifact_ref": reference + "-bytes", "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_count": len(raw)}, "body_complete": body, "object_complete": complete}


def field(reference="synthetic-parameter-record", pointer="/parameters", *, sha="a" * 64):
    return {"source_ref": reference, "sha256": sha, "pointer": pointer,
            "row_ordinal": None, "field_name": None}


def population(*, complete="yes", origin="supplied_snapshot"):
    return {"origin": origin, "query_source": None, "selected_fields": [], "offset": None,
            "requested_limit": None, "reported_total_count": None,
            "population_complete": complete, "completeness_evidence": []}


def coordinates(value="unknown"):
    return {"value": value, "source_fields": [] if value == "unknown" else [field("synthetic-coordinate-documentation", "") ]}


def source_contract():
    return {"id": "GenomeComparison_inspected_source_v1",
            "application_tree": "5c365e1dca2b3a8c311d7d352e862ff1442eefc9",
            "application_sha256": "4267b35bdd5ad858b833fa2b84eb794c91e95b7f5abc0628b90ec4d6a0a33c14",
            "dependency_tree": "18196fe0df123702457e4af2e0b1e0707d5f5281",
            "deployment_match": "unobserved", "deployment_evidence": []}


def task():
    return {"resource_id": "synthetic-api", "task_id": "synthetic-task",
            "required_application_id": "GenomeComparison", "native_application_id": "GenomeComparison",
            "submitted_parameters": {"genome_ids": ["G1", "G2"], "user_genomes": ["/F1"],
                "user_feature_groups": ["/FG1"], "reference_genome_index": 3,
                "min_ident": 0, "min_seq_cov": None, "max_e_val": 1e-5},
            "submitted_start_parameters": {}, "scheduler_returned_parameters": None,
            "effective_parameters": None, "submission_receipt_ref": "synthetic-submission-receipt",
            "submission_operation_key": "synthetic-operation",
            "submission_source_ref": "synthetic-parameter-record"}


def effective(original, **changes):
    values = {**deepcopy(original["submitted_parameters"]), **changes}
    raw = json.dumps({"effective": values}).encode()
    original["effective_parameters"] = {"value": values,
        "evidence": {"content": source(raw, reference="synthetic-effective-record")["content"], "pointer": "/effective"}}
    evidence = original["effective_parameters"]["evidence"]
    return {"kind": "effective", "source_field": field(evidence["content"]["source_ref"],
            evidence["pointer"], sha=evidence["content"]["sha256"])}


def index(original=None, **kwargs):
    return index_original_inputs(task() if original is None else original,
        parameter_source=kwargs.pop("parameter_source", {"kind": "submitted", "source_field": field()}),
        source_contract=kwargs.pop("source_contract", source_contract()), **kwargs)


def fasta(raw, **kwargs):
    return read_protein_fasta(raw, source=kwargs.pop("source", source(raw)),
        declared_format=kwargs.pop("declared_format", "protein_fasta_utf8_v1"),
        inventory_key=kwargs.pop("inventory_key", "synthetic-inventory"), **kwargs)


_READERS = {"feature": (read_feature_metadata, "bvbrc_genome_feature_json_array_v1", "FeatureSnapshot"),
            "genome": (read_genome_metadata, "bvbrc_genome_json_array_v1", "GenomeSnapshot"),
            "sequence": (read_feature_sequences, "bvbrc_feature_sequence_json_array_v1", "FeatureSequenceSnapshot")}


def metadata(data, kind="feature", **kwargs):
    raw = data if type(data) is bytes else json.dumps(data, ensure_ascii=False).encode()
    reader, fmt, _ = _READERS[kind]
    if kind == "feature":
        kwargs.setdefault("coordinate_convention", coordinates())
    return reader(raw, source=kwargs.pop("source", source(raw)),
        declared_format=kwargs.pop("declared_format", fmt), snapshot_key=kwargs.pop("snapshot_key", "synthetic-metadata"),
        population=kwargs.pop("population", population()), **kwargs)


def codes(result):
    return {item["code"] for item in result["diagnostics"]}


def assert_envelope(result, name):
    assert set(result) == {"status", "value", "requirements", "diagnostics"}
    assert validate_proteome_data(name + "Result", result) == result
    if result["status"] == "invalid":
        assert result["value"] is None
        assert result["requirements"] and result["diagnostics"]


def test_precision_correction_is_reused_as_synthetic_input_only():
    path = Path(__file__).parents[1] / "verification/tool_graders_bvbrc_proteome_sheet_contract_2026-10-25_165/B1_PRECISION_EXAMPLES_002.json"
    example = json.loads(path.read_text())
    assert example["origin"] == "constructed_supplied_input_and_expected_contract_values_not_production_reader_output"
    expected = example["expected_inventory"]
    result = fasta(example["raw_input_utf8"].encode(), source=expected["source"], inventory_key=expected["inventory_key"])
    value = result["value"]
    for key in set(expected) - {"diagnostics"}:
        assert value[key] == expected[key]
    assert result["status"] == "partial"
    assert {"duplicate_identifier", "fasta_empty_sequence", "fasta_sequence_invalid"} <= codes(result)
    assert_envelope(result, "ProteinInventory")


def test_fasta_duplicate_ids_and_equal_full_sequences_keep_every_occurrence():
    result = fasta(b">dup\nAAAA\n>dup\nAAAA\n>different\nAAAA\n>other\nCCCC\n")
    value = result["value"]
    assert [row["record_ordinal"] for row in value["records"]] == [0, 1, 2, 3]
    assert value["observed_header_count"] == value["complete_record_count"] == value["valid_complete_record_count"] == 4
    assert value["duplicate_identifier_groups"] == [{"identifier": "dup", "record_ordinals": [0, 1]}]
    assert [[r["record_ordinal"] for r in group["members"]] for group in value["sequence_groups"]] == [[0, 1, 2], [3]]
    assert "input_record_count" not in value
    assert result["status"] == "partial"


@pytest.mark.parametrize("text,normalized,valid", [
    ("acde", "ACDE", True), (" bxzjuo*\t", "BXZJUO*", True),
    ("AA-?1", "AA-?1", False), ("", "", False), (" \n\t", "", False),
    ("aéß\u00a0", "Aéß\u00a0", False), ("a\v\fc\rd", "ACD", True),
])
def test_complete_sequences_retain_normalized_text_count_and_utf8_hashes(text, normalized, valid):
    result = fasta((">id\n" + text).encode())
    record = result["value"]["records"][0]
    assert record["sequence"] == normalized
    assert record["sequence_symbol_count"] == len(normalized)
    assert record["sequence_sha256"] == hashlib.sha256(normalized.encode()).hexdigest()
    assert record["sequence_md5"] == hashlib.md5(normalized.encode()).hexdigest()
    assert record["valid_sequence"] is valid
    assert len(result["value"]["sequence_groups"]) == int(valid)


def test_fasta_crlf_multibyte_offsets_and_exact_header_whitespace():
    raw = ">  idé  first\t\r\nacde\r\n>next\v\f trailing \t\nCC\n".encode()
    records = fasta(raw)["value"]["records"]
    assert records[0]["header"] == "  idé  first\t"
    assert records[0]["identifier"] == "idé"
    assert records[0]["description"] == "  first\t"
    assert records[0]["byte_start"] == 0
    assert records[0]["byte_end_exclusive"] == raw.index(b">next")
    assert records[1]["byte_start"] == raw.index(b">next")
    assert records[1]["byte_end_exclusive"] == len(raw)
    assert records[1]["description"] == "\v\f trailing \t"


def test_fasta_only_physical_line_start_opens_record():
    result = fasta(b">first\nAA>BB\n>second\nAC\n")
    assert result["value"]["observed_header_count"] == 2
    assert result["value"]["records"][0]["sequence"] == "AA>BB"
    assert result["value"]["records"][0]["valid_sequence"] is False
    assert result["value"]["records"][1]["valid_sequence"] is True


@pytest.mark.parametrize("header", ["", " \t\v\f\r"])
def test_fasta_empty_identifier_retains_header_and_sequence(header):
    result = fasta((">" + header + "\nACD\n").encode())
    record = result["value"]["records"][0]
    assert record["header"] == header.removesuffix("\r")
    assert record["identifier"] is record["description"] is None
    assert record["sequence"] == "ACD" and record["valid_sequence"] is True
    assert result["value"]["valid_complete_record_count"] == 0
    assert result["value"]["sequence_groups"] == []


@pytest.mark.parametrize("complete,body", [("unknown", True), ("no", True), ("unknown", False), ("yes", False)])
@pytest.mark.parametrize("suffix", [b">last\nACD\n", b">last\nACD", b">par", b">\xc3"])
def test_fasta_partial_records_never_promoted_by_eof_or_newline(complete, body, suffix):
    raw = b">first\nAAAA\n" + suffix
    result = fasta(raw, source=source(raw, complete=complete, body=body))
    assert result["status"] == "partial"
    rows = result["value"]["records"]
    assert len(rows) == 2
    assert rows[-1]["record_complete"] is False
    for key in ("sequence", "sequence_symbol_count", "sequence_sha256", "sequence_md5"):
        assert rows[-1][key] is None
    if b"\n" not in suffix:
        assert rows[-1]["header"] is None
        assert rows[0]["record_complete"] is False
    else:
        assert rows[0]["sequence"] == "AAAA"
    assert "fasta_record_incomplete" in codes(result)


def test_fasta_partial_final_sequence_invalid_utf8_keeps_closed_neighbors():
    raw = b">first\nACDE\n>last\n\xff"
    result = fasta(raw, source=source(raw, complete="unknown"))
    assert result["status"] == "partial"
    assert result["value"]["records"][0]["sequence"] == "ACDE"
    assert result["value"]["records"][1]["sequence"] is None


@pytest.mark.parametrize("raw", [b">\xff\nAC\n", b">x\n\xff\n", b"\xff"])
def test_fasta_complete_bad_utf8_is_fatal(raw):
    result = fasta(raw)
    assert result["status"] == "invalid" and codes(result) == {"encoding_invalid"}
    assert_envelope(result, "ProteinInventory")


@pytest.mark.parametrize("raw", [b"", b" \t\r\n\v\f"])
def test_fasta_complete_empty_has_observed_zero_without_execution_claim(raw):
    result = fasta(raw)
    assert result["status"] == "ok"
    assert result["value"]["records"] == []
    assert result["value"]["observed_header_count"] == 0
    assert result["value"]["sequence_groups"] == []


def test_fasta_leading_nonblank_text_does_not_erase_usable_records():
    result = fasta(b"bad-prefix\n>id\nACDE\n")
    assert result["status"] == "partial" and "fasta_header_invalid" in codes(result)
    assert result["value"]["records"][0]["byte_start"] == len(b"bad-prefix\n")
    assert result["value"]["records"][0]["sequence"] == "ACDE"
    assert fasta(b"no-record")["status"] == "invalid"


@pytest.mark.parametrize("kind", ["fasta", "feature", "genome", "sequence"])
@pytest.mark.parametrize("error", ["digest", "bytes", "not_bytes", "format", "key", "source"])
def test_every_byte_reader_checks_exact_binding_and_declared_contract(kind, error):
    raw = b">id\nACD\n" if kind == "fasta" else b"[]"
    kwargs = {"source": source(raw)}
    if error == "digest": kwargs["source"]["content"]["sha256"] = "0" * 64
    if error == "bytes": kwargs["source"]["content"]["byte_count"] += 1
    if error == "not_bytes": raw = bytearray(raw)
    if error == "format": kwargs["declared_format"] = "filename.json"
    if error == "key": kwargs["inventory_key" if kind == "fasta" else "snapshot_key"] = ""
    if error == "source": kwargs["source"]["surplus"] = True
    if kind == "fasta":
        result = fasta(raw, **kwargs)
        name = "ProteinInventory"
    else:
        reader, fmt, name = _READERS[kind]
        if kind == "feature": kwargs["coordinate_convention"] = coordinates()
        result = reader(raw, source=kwargs.pop("source"), declared_format=kwargs.pop("declared_format", fmt),
                        snapshot_key=kwargs.pop("snapshot_key", "input"), population=population(), **kwargs)
    assert result["status"] == "invalid"
    assert_envelope(result, name)


@pytest.mark.parametrize("raw,code,path", [
    (b'[{"feature_id":"a","feature_id":"b"}]', "duplicate_json_member", "/0/feature_id"),
    (b'[{"feature_id":"a","unknown":{"x":1,"x":2}}]', "duplicate_json_member", "/0/unknown/x"),
    (b'[{"feature_id":"a"}', "json_invalid", ""),
    (b'[{"feature_id":"a","aa_length":NaN}]', "json_invalid", ""),
    (b'[{"feature_id":"a","aa_length":Infinity}]', "json_invalid", ""),
    (b'{"records":[]}', "format_incompatible", ""), (b'\xff', "encoding_invalid", ""),
])
def test_metadata_fatal_documents_have_no_first_or_last_member_selection(raw, code, path):
    result = metadata(raw)
    assert result["status"] == "invalid"
    assert result["diagnostics"][0]["code"] == code
    assert result["diagnostics"][0]["path"] == path


@pytest.mark.parametrize("kind,good", [("feature", {"feature_id": "f"}), ("genome", {"genome_id": "g"}),
    ("sequence", {"md5": hashlib.md5(b"ACD").hexdigest(), "sequence": "ACD"})])
def test_metadata_scalar_neighbors_keep_original_ordinals_and_invalid_cells(kind, good):
    result = metadata([good, 3, None, [good], good], kind)
    assert result["status"] == "partial"
    rows = result["value"]["records"]
    assert [r["row_ordinal"] for r in rows] == list(range(5))
    assert [r["valid"] for r in rows] == [True, False, False, False, True]
    assert rows[1]["source_field"]["pointer"] == "/1"
    for key, cell in rows[1].items():
        if type(cell) is dict and "presence" in cell:
            assert cell["presence"] == "invalid"


@pytest.mark.parametrize("record,valid", [
    ({"feature_id": "only-f"}, True), ({"patric_id": "only-p"}, True),
    ({"feature_id": " f ", "patric_id": " p "}, True), ({"feature_id": " "}, False),
    ({"feature_id": 3}, False), ({"feature_id": True}, False), ({"product": "enzyme"}, False),
    ({"feature_id": "f", "genome_id": None, "product": "", "aa_length": 0}, True),
    ({"feature_id": "f", "genome_id": "", "annotation": None, "strand": "-"}, True),
])
def test_feature_identity_optional_fields_and_unmodified_strings(record, valid):
    result = metadata([record])
    row = result["value"]["records"][0]
    assert row["valid"] is valid
    for key, value in record.items():
        if type(value) is str:
            assert row[key]["value"] == value
    assert row["start"]["presence"] == "omitted"


def test_metadata_null_blank_omitted_and_explicit_zero_are_distinct():
    row = metadata([{"feature_id": "f", "product": "", "gene": None, "aa_length": 0}])["value"]["records"][0]
    assert row["product"]["presence"] == "blank" and row["product"]["value"] == ""
    assert row["gene"]["presence"] == "explicit_null"
    assert row["genome_id"]["presence"] == "omitted"
    assert row["aa_length"] == {"value": 0, "presence": "value", "lexeme": "0", "source_field": row["aa_length"]["source_field"]}


def test_unknown_metadata_fields_remain_exact_escaped_paths_without_invalidating_known_cells():
    result = metadata([{"feature_id": "f", "unknown/name~": {"x": [1]}, "": "retained"}])
    assert result["value"]["records"][0]["valid"] is True
    assert result["value"]["unsupported_field_paths"] == ["/0/unknown~1name~0", "/0/"]
    assert "unknown_metadata_fields_retained" in codes(result)


@pytest.mark.parametrize("raw,expected,lexeme", [
    (b'0', 0, '0'), (b'2e1', 20, '2e1'), (b'"+0020.00"', 20, '+0020.00'),
    (b'"0.000E+4"', 0, '0.000E+4'), (b'9007199254740993', 9007199254740993, '9007199254740993'),
])
def test_feature_integer_measurements_preserve_exact_lexemes(raw, expected, lexeme):
    result = metadata(b'[{"feature_id":"f","aa_length":' + raw + b'}]')
    cell = result["value"]["records"][0]["aa_length"]
    assert cell["value"] == expected and type(cell["value"]) is int
    assert cell["lexeme"] == lexeme and cell["presence"] == "value"


@pytest.mark.parametrize("raw", [b'-1', b'2.5', b'true', b'"20 aa"', b'" 20 "', b'1e309', b'1e-9999', b'{}'])
def test_invalid_numeric_cell_preserves_valid_neighbor_and_exact_native_lexeme(raw):
    result = metadata(b'[{"feature_id":"f","aa_length":' + raw + b'},{"feature_id":"g","aa_length":0}]')
    rows = result["value"]["records"]
    assert rows[0]["valid"] is False and rows[0]["aa_length"]["presence"] == "invalid"
    assert rows[1]["valid"] is True and rows[1]["aa_length"]["value"] == 0


@pytest.mark.parametrize("taxon,valid,presence", [(None, True, "explicit_null"), ("", True, "blank"),
    (1, True, "value"), ("562.0", True, "value"), (0, False, "invalid"), (-1, False, "invalid"),
    (562.5, False, "invalid"), (False, False, "invalid")])
def test_genome_taxon_optional_positive_integral_only(taxon, valid, presence):
    row = metadata([{"genome_id": "g", "taxon_id": taxon}], "genome")["value"]["records"][0]
    assert row["valid"] is valid and row["taxon_id"]["presence"] == presence
    assert row["genome_name"]["presence"] == "omitted"


def test_genome_missing_taxon_is_not_zero_or_inferred_from_name():
    result = metadata([{"genome_id": "g"}, {"genome_name": "taxon 562"}], "genome")
    rows = result["value"]["records"]
    assert rows[0]["valid"] is True and rows[0]["taxon_id"]["value"] is None
    assert rows[1]["valid"] is False


@pytest.mark.parametrize("convention,start,end,valid", [
    ("unknown", -2, 0, True), ("unknown", 12, 2, True),
    ("one_based_closed", 12, 2, True), ("one_based_closed", 0, 3, False),
    ("one_based_closed", 1, 1, True), ("zero_based_half_open", 0, 0, True),
    ("zero_based_half_open", 3, 12, True), ("zero_based_half_open", 12, 3, False),
    ("zero_based_half_open", -1, 12, False),
])
def test_coordinates_follow_supplied_convention_without_inference(convention, start, end, valid):
    result = metadata([{"feature_id": "f", "start": start, "end": end, "strand": "-"}], coordinate_convention=coordinates(convention))
    row = result["value"]["records"][0]
    assert row["valid"] is valid
    if valid or convention == "zero_based_half_open" and start == 12:
        assert (row["start"]["value"], row["end"]["value"]) == (start, end)
    assert row["strand"]["value"] == "-" and row["aa_length"]["presence"] == "omitted"
    assert ("coordinate_convention_unknown" in codes(result)) is (convention == "unknown")


@pytest.mark.parametrize("convention", [{"value": "one_based_closed", "source_fields": []},
    {"value": "guessed", "source_fields": []}])
def test_coordinate_convention_needs_documented_supported_argument(convention):
    result = metadata([{"feature_id": "f"}], coordinate_convention=convention)
    assert result["status"] == "invalid"
    assert result["requirements"][0]["required_input"] == "coordinate_convention"


@pytest.mark.parametrize("kind", ["feature", "genome", "sequence"])
def test_source_and_population_completeness_remain_independent(kind):
    good = {"feature": {"feature_id": "f"}, "genome": {"genome_id": "g"},
            "sequence": {"md5": hashlib.md5(b"ACD").hexdigest(), "sequence": "ACD"}}[kind]
    raw = json.dumps([good]).encode()
    pop = population(complete="unknown", origin="later_database_snapshot")
    pop["offset"], pop["requested_limit"] = 0, 25000
    result = metadata(raw, kind, population=pop)
    assert result["status"] == "partial"
    assert result["value"]["source"]["object_complete"] == "yes"
    assert result["value"]["population"] == pop
    assert {"metadata_population_unknown", "later_snapshot_not_original_input"} <= codes(result)
    other = metadata(raw, kind, source=source(raw, complete="no", body=False))
    assert other["status"] == "partial"
    assert other["value"]["records"][0]["valid"] is True
    assert {"source_bytes_incomplete", "source_object_incomplete"} <= codes(other)
    assert other["value"]["population"]["population_complete"] == "yes"


def test_md5_case_and_exact_sequence_text_retained_with_normalized_digests():
    digest = hashlib.md5(b"ACD*").hexdigest()
    row = metadata([{"md5": digest.upper(), "sequence": "ac d*\n"}], "sequence")["value"]["records"][0]
    assert row["valid"] is True and row["md5"]["value"] == digest.upper()
    assert row["sequence"]["value"] == "ac d*\n"
    assert row["computed_md5"] == digest
    assert row["computed_sha256"] == hashlib.sha256(b"ACD*").hexdigest()
    assert row["sequence_symbol_count"] == 4


@pytest.mark.parametrize("sequence", ["", "AA-?1", "aéß", " \t"])
def test_feature_sequence_invalid_text_still_has_complete_count_and_hashes(sequence):
    normalized = {"": "", "AA-?1": "AA-?1", "aéß": "Aéß", " \t": ""}[sequence]
    digest = hashlib.md5(normalized.encode()).hexdigest()
    row = metadata([{"md5": digest, "sequence": sequence}], "sequence")["value"]["records"][0]
    assert row["valid"] is False
    assert row["sequence"]["value"] == sequence
    assert row["sequence_symbol_count"] == len(normalized)
    assert row["computed_md5"] == digest
    assert row["computed_sha256"] == hashlib.sha256(normalized.encode()).hexdigest()


def test_feature_sequence_digest_conflict_retains_source_identity_and_measured_sequence():
    result = metadata([{"md5": "0" * 32, "sequence": "ACD"}], "sequence")
    row = result["value"]["records"][0]
    assert row["valid"] is False and row["md5"]["value"] == "0" * 32
    assert row["computed_md5"] == hashlib.md5(b"ACD").hexdigest()
    assert "sequence_digest_conflict" in codes(result)


@pytest.mark.parametrize("md5", ["bad", "g" * 32, 3, True])
def test_malformed_md5_is_local_and_never_coerced(md5):
    result = metadata([{"md5": md5, "sequence": "ACD"}], "sequence")
    row = result["value"]["records"][0]
    assert row["valid"] is False and row["md5"]["presence"] == "invalid"
    assert row["sequence_symbol_count"] == 3
    feature = metadata([{"feature_id": "f", "aa_sequence_md5": md5}])["value"]["records"][0]
    assert feature["valid"] is False


def test_feature_optional_md5_and_shared_sequence_do_not_collapse_features():
    digest = hashlib.md5(b"ACD").hexdigest().upper()
    result = metadata([{"feature_id": "f", "aa_sequence_md5": digest},
                       {"feature_id": "g", "aa_sequence_md5": digest}])
    assert [r["feature_id"]["value"] for r in result["value"]["records"]] == ["f", "g"]
    assert all(r["valid"] for r in result["value"]["records"])
    assert "duplicate_identifier" not in codes(result)


def test_invalid_escaped_surrogate_is_not_encoded_as_a_sequence_measurement():
    result = metadata(b'[{"md5":"00000000000000000000000000000000","sequence":"\\ud800"}]', "sequence")
    row = result["value"]["records"][0]
    assert row["valid"] is False and row["sequence"]["presence"] == "invalid"
    assert row["computed_md5"] is row["sequence_symbol_count"] is None


def test_original_input_reordering_preserves_original_pointers_and_every_occurrence():
    result = index()
    assert result["status"] == "ok"
    entries = result["value"]["inputs"]
    assert [(r["value"], r["original_index"], r["expected_track_key"]) for r in entries] == [
        ("/F1", 3, "ref_genome"), ("G1", 1, "comp_genome_1"),
        ("G2", 2, "comp_genome_2"), ("/FG1", 4, "comp_genome_3")]
    assert entries[0]["input_key"] == entries[0]["parameter_pointer"] == "/user_genomes/0"
    assert entries[0]["source_field"]["pointer"] == "/parameters/user_genomes/0"
    assert "input_order_is_not_execution_proof" in codes(result)
    original = task()
    original["submitted_parameters"]["genome_ids"] = ["same", "same"]
    assert len(index(original)["value"]["inputs"]) == 4


@pytest.mark.parametrize("key", ["genome_ids", "user_genomes", "user_feature_groups"])
@pytest.mark.parametrize("value", [None, "path", [1], [""], [True]])
def test_input_index_never_invents_missing_or_invalid_arrays(key, value):
    original = task()
    original["submitted_parameters"][key] = value
    result = index(original)
    assert result["status"] == "invalid" and "input_arrays_unavailable" in codes(result)
    del original["submitted_parameters"][key]
    assert index(original)["status"] == "invalid"


@pytest.mark.parametrize("reference", [None, 0, -1, 5, "3", 3.0, True])
def test_input_index_reference_must_be_explicit_one_based_integer(reference):
    original = task()
    original["submitted_parameters"]["reference_genome_index"] = reference
    result = index(original)
    assert result["status"] == "invalid" and "input_reference_index_invalid" in codes(result)


def test_recorded_submitted_and_effective_thresholds_are_separate_without_fabricated_lexemes():
    original = task()
    effective(original, min_ident=0.1, min_seq_cov=0.3, min_positives=0.2)
    result = index(original)
    submitted, observed = result["value"]["run_parameter_snapshots"]
    assert submitted["kind"] == "submitted" and observed["kind"] == "effective"
    assert submitted["min_ident"]["value"] == 0 and observed["min_ident"]["value"] == 0.1
    assert submitted["min_seq_cov"]["presence"] == "explicit_null"
    assert submitted["min_positives"]["presence"] == "omitted"
    assert "lexeme" not in submitted["min_ident"]
    assert observed["min_ident"]["source_field"]["pointer"] == "/effective/min_ident"


def test_effective_source_without_submitted_locator_is_partial_not_fabricated():
    original = task()
    selected = effective(original, min_ident=0.1)
    result = index(original, parameter_source=selected)
    assert result["status"] == "partial"
    assert [s["kind"] for s in result["value"]["run_parameter_snapshots"]] == ["effective"]
    assert result["requirements"][0]["code"] == "parameter_source_conflict"
    assert result["requirements"][0]["required_input"] == "original_parameters"


def test_additional_submitted_locator_supplies_actual_snapshot_without_selecting_mapping():
    original = task()
    selected = effective(original, min_ident=0.1)
    additional = {"kind": "submitted", "source_field": field()}
    result = index(original, parameter_source=selected, additional_parameter_sources=[additional, deepcopy(additional)])
    assert result["status"] == "ok"
    assert [s["kind"] for s in result["value"]["run_parameter_snapshots"]] == ["submitted", "effective"]
    assert result["value"]["parameter_source"] == selected
    assert all(r["source_field"]["source_ref"] == "synthetic-effective-record" for r in result["value"]["inputs"])


def test_effective_parameters_may_fill_only_recorded_omissions():
    original = task()
    del original["submitted_parameters"]["reference_genome_index"]
    original["submitted_parameters"]["user_feature_groups"] = None
    selected = effective(original, reference_genome_index=2, user_feature_groups=[])
    result = index(original, parameter_source=selected)
    assert result["status"] == "partial"
    assert result["value"]["reference_original_index"] == 2
    assert len(result["value"]["inputs"]) == 3


@pytest.mark.parametrize("change", [{"reference_genome_index": 1}, {"genome_ids": ["G2", "G1"]},
                                   {"user_genomes": []}, {"user_feature_groups": ["/other"]}])
def test_effective_parameter_input_contradiction_cannot_rewrite_original_mapping(change):
    original = task()
    selected = effective(original, **change)
    result = index(original, parameter_source=selected)
    assert result["status"] == "invalid" and "parameter_source_conflict" in codes(result)


@pytest.mark.parametrize("part", ["source_ref", "sha256", "pointer"])
def test_effective_source_must_match_existing_evidence_exactly(part):
    original = task()
    selected = effective(original)
    selected["source_field"][part] = "b" * 64 if part == "sha256" else "/wrong"
    result = index(original, parameter_source=selected)
    assert result["status"] == "invalid" and "parameter_source_conflict" in codes(result)


def test_conflicting_additional_parameter_locations_rejected():
    additional = {"kind": "submitted", "source_field": field(pointer="/other")}
    result = index(additional_parameter_sources=[additional])
    assert result["status"] == "invalid" and "parameter_source_conflict" in codes(result)
    assert index(additional_parameter_sources={})["status"] == "invalid"


def test_parameter_wrong_application_or_submission_source_rejected():
    original = task()
    original["native_application_id"] = original["required_application_id"] = "Homology"
    assert index(original)["status"] == "invalid"
    selected = {"kind": "submitted", "source_field": field("other-source")}
    assert index(parameter_source=selected)["status"] == "invalid"
    wrong = source_contract()
    wrong["deployment_match"] = "different"
    assert index(source_contract=wrong)["status"] == "invalid"


def test_scheduler_returned_parameters_are_not_assumed_effective():
    original = task()
    selected = effective(original)
    original["scheduler_returned_parameters"] = original["effective_parameters"]
    original["effective_parameters"] = None
    assert index(original, parameter_source=selected)["status"] == "invalid"
    assert [s["kind"] for s in index(original)["value"]["run_parameter_snapshots"]] == ["submitted"]


@pytest.mark.parametrize("invalid", [True, "0.1", {}, []])
def test_recorded_threshold_invalid_types_survive_as_local_invalid_cells(invalid):
    original = task()
    original["submitted_parameters"]["min_ident"] = invalid
    result = index(original)
    assert result["status"] == "partial"
    snapshot = result["value"]["run_parameter_snapshots"][0]
    assert snapshot["min_ident"]["presence"] == "invalid"
    assert snapshot["max_e_val"]["value"] == 1e-5


def test_all_readers_return_detached_contracts_and_make_no_network_or_subprocess_calls(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("acquisition or execution attempted")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    raw = b">a\nACD\n"
    supplied_source = source(raw)
    saved_source = deepcopy(supplied_source)
    result = fasta(raw, source=supplied_source)
    result["value"]["source"]["content"]["artifact_ref"] = "changed"
    assert supplied_source == saved_source
    for kind in _READERS:
        pop = population()
        saved_pop = deepcopy(pop)
        result = metadata([], kind, population=pop)
        result["value"]["population"]["selected_fields"].append("changed")
        assert pop == saved_pop
    original, selected, contract = task(), {"kind": "submitted", "source_field": field()}, source_contract()
    saved = deepcopy((original, selected, contract))
    result = index(original, parameter_source=selected, source_contract=contract)
    result["value"]["run_parameter_snapshots"][0]["source_field"]["pointer"] = "/changed"
    result["value"]["parameter_source"]["source_field"]["pointer"] = "/changed"
    assert (original, selected, contract) == saved


def test_deeply_nested_supplied_contract_is_an_explicit_invalid_input():
    malformed = {}
    node = malformed
    for _ in range(1200):
        node["next"] = {}
        node = node["next"]
    result = fasta(b"", source=malformed)
    assert result["status"] == "invalid"
    assert codes(result) == {"supplied_contract_invalid"}
    assert_envelope(result, "ProteinInventory")


def test_partial_empty_fasta_does_not_establish_complete_empty_inventory():
    result = fasta(b"", source=source(b"", complete="unknown"))
    assert result["status"] == "partial"
    assert result["value"]["observed_header_count"] == 0
    assert result["value"]["source"]["object_complete"] == "unknown"
    assert "source_object_incomplete" in codes(result)


def test_fasta_full_sequence_equality_never_groups_matching_prefixes_or_invalid_headers():
    result = fasta(b">a\nAAAA\n>b\nAAAAC\n>\nAAAA\n")
    assert [[m["record_ordinal"] for m in group["members"]] for group in result["value"]["sequence_groups"]] == [[0], [1]]
    assert result["value"]["complete_record_count"] == 3
    assert result["value"]["valid_complete_record_count"] == 2


def test_complete_header_without_line_terminator_keeps_trailing_carriage_return():
    row = fasta(b">id\r")["value"]["records"][0]
    assert row["header"] == "id\r" and row["description"] == "\r"
    assert row["sequence"] == "" and row["sequence_symbol_count"] == 0


@pytest.mark.parametrize("kind,data", [("feature", [{"feature_id": "f", "product": "one"}, {"feature_id": "f", "product": "two"}]),
    ("genome", [{"genome_id": "g", "taxon_id": 1}, {"genome_id": "g", "taxon_id": 2}]),
    ("sequence", [{"md5": hashlib.md5(b"ACD").hexdigest(), "sequence": "ACD"},
                  {"md5": hashlib.md5(b"ACD").hexdigest().upper(), "sequence": "acd"}])])
def test_metadata_repeated_identities_preserve_all_assignments(kind, data):
    result = metadata(data, kind)
    assert result["status"] == "partial"
    assert "duplicate_identifier" in codes(result)
    rows = result["value"]["records"]
    assert len(rows) == 2 and all(r["valid"] for r in rows)
    assert [r["row_ordinal"] for r in rows] == [0, 1]


def test_population_fields_are_preserved_and_invalid_numeric_count_is_not_accepted():
    pop = population(complete="no")
    pop.update(offset=20, requested_limit=10, selected_fields=["genome_id"],
               query_source=field("synthetic-query", "/query"),
               reported_total_count={"value": 32, "presence": "value", "lexeme": "3.2e1", "source_field": field("synthetic-query", "/total")})
    result = metadata([{"genome_id": "g"}], "genome", population=pop)
    assert result["value"]["population"] == pop and result["status"] == "partial"
    assert "metadata_population_incomplete" in codes(result)
    pop["reported_total_count"].update(value=-1, lexeme="-1")
    assert metadata([], "genome", population=pop)["status"] == "invalid"


def test_json_member_duplicates_after_escape_decoding_are_fatal():
    result = metadata(b'[{"feature_id":"f","a/b":1,"a\\/b":2}]')
    assert result["status"] == "invalid"
    assert result["diagnostics"][0]["path"] == "/0/a~1b"


def test_absent_reference_index_and_explicit_empty_inputs_do_not_receive_defaults():
    original = task()
    del original["submitted_parameters"]["reference_genome_index"]
    assert index(original)["status"] == "invalid"
    original["submitted_parameters"].update(genome_ids=[], user_genomes=[], user_feature_groups=[], reference_genome_index=1)
    result = index(original)
    assert result["status"] == "invalid" and "input_reference_index_invalid" in codes(result)


def test_actual_effective_source_may_be_added_without_making_it_selected():
    original = task()
    observed = effective(original, min_ident=0.25)
    result = index(original, additional_parameter_sources=[observed])
    assert result["value"]["parameter_source"]["kind"] == "submitted"
    assert result["value"]["run_parameter_snapshots"][1]["min_ident"]["value"] == 0.25
    assert result["value"]["inputs"][0]["source_field"]["source_ref"] == "synthetic-parameter-record"


def test_escaped_surrogate_numeric_text_retains_invalid_cell_without_unencodable_lexeme():
    result = metadata(b'[{"feature_id":"f","aa_length":"\\ud800"},{"feature_id":"g","aa_length":3}]')
    assert result["status"] == "partial"
    rows = result["value"]["records"]
    assert rows[0]["aa_length"]["presence"] == "invalid"
    assert rows[0]["aa_length"]["lexeme"] is None
    assert rows[1]["aa_length"]["value"] == 3
    json.dumps(result, ensure_ascii=False).encode("utf-8")


def test_unencodable_json_member_name_is_explicit_document_encoding_failure():
    result = metadata(b'[{"feature_id":"f","\\ud800":1}]')
    assert result["status"] == "invalid" and codes(result) == {"encoding_invalid"}
    json.dumps(result, ensure_ascii=False).encode("utf-8")


def test_original_input_strings_must_be_encodable_without_replacement():
    original = task()
    original["submitted_parameters"]["user_genomes"] = ["\ud800"]
    result = index(original)
    assert result["status"] == "invalid" and "input_arrays_unavailable" in codes(result)
    json.dumps(result, ensure_ascii=False).encode("utf-8")
