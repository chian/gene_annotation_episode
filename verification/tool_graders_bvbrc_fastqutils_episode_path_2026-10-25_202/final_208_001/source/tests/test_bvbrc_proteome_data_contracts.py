"""Saved-data integrity, not native execution or source-custody verification."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_proteome_data_contracts import (
    ProteomeDataError, proteome_data_schema, validate_proteome_data,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ("verification/tool_graders_bvbrc_proteome_sheet_contract_2026-10-25_165/"
                  "B1_PRECISION_EXAMPLES_002.json")


def inventory():
    return json.loads(EXAMPLE.read_text())["expected_inventory"]


def field(pointer, ordinal=None, name=None):
    return {"source_ref": "supplied-test", "sha256": hashlib.sha256(b"synthetic supplied bytes").hexdigest(),
            "pointer": pointer, "row_ordinal": ordinal, "field_name": name}


def string(value, pointer, ordinal=0, name=None):
    return {"value": value, "presence": "omitted" if value is None else "blank" if value == "" else "value",
            "source_field": field(pointer, ordinal, name)}


def number(value, pointer, ordinal=0, name=None):
    return {"value": value, "presence": "omitted" if value is None else "value",
            "lexeme": None if value is None else str(value), "source_field": field(pointer, ordinal, name)}


def metadata(name, supplied):
    schema = proteome_data_schema(name)["$defs"][name]
    row = {"row_ordinal": 0, "source_field": field("/0", 0), "valid": True, "diagnostics": []}
    for key, shape in schema["properties"].items():
        if shape.get("$ref") == "#/$defs/NativeString":
            row[key] = string(supplied.get(key), "/0/" + key, name=key)
        elif shape.get("$ref") == "#/$defs/NativeNumber":
            row[key] = number(supplied.get(key), "/0/" + key, name=key)
    if name == "FeatureSequenceRecord":
        row["molecule"] = "aa"
        raw = supplied["sequence"].upper().encode()
        row.update(sequence_symbol_count=len(raw), computed_sha256=hashlib.sha256(raw).hexdigest(),
                   computed_md5=hashlib.md5(raw).hexdigest())
    return row


def snapshot(name, row, convention="unknown"):
    formats = {"FeatureSnapshot": "bvbrc_genome_feature_json_array_v1",
               "GenomeSnapshot": "bvbrc_genome_json_array_v1",
               "FeatureSequenceSnapshot": "bvbrc_feature_sequence_json_array_v1"}
    value = {"version": "bvbrc_proteome_metadata_proposal_v1", "snapshot_key": "supplied-metadata",
             "format": formats[name], "source": {"content": {"source_ref": "supplied-test",
                 "artifact_field": "artifact_ref", "artifact_ref": "synthetic-artifact",
                 "sha256": field("")["sha256"], "byte_count": 24},
                 "body_complete": True, "object_complete": "yes"},
             "population": {"origin": "supplied_snapshot", "query_source": None, "selected_fields": [],
                 "offset": None, "requested_limit": None, "reported_total_count": None,
                 "population_complete": "unknown", "completeness_evidence": []},
             "records": [row], "unsupported_field_paths": [], "diagnostics": []}
    if name == "FeatureSnapshot":
        value["coordinate_convention"] = {"value": convention,
            "source_fields": [] if convention == "unknown" else [field("/coordinate-declaration")]}
    return value


def input_index():
    schema = proteome_data_schema("SourceContract")["$defs"]["SourceContract"]["properties"]
    contract = {key: definition["const"] for key, definition in schema.items() if "const" in definition}
    contract.update(deployment_match="unobserved", deployment_evidence=[])
    parent = field("/submitted")
    value = {"version": "bvbrc_proteome_input_index_proposal_v1",
             "parameter_source": {"kind": "submitted", "source_field": parent},
             "reference_original_index": 3, "inputs": [], "source_contract": contract,
             "run_parameter_snapshots": [], "diagnostics": []}
    for index, (kind, pointer, text, track) in enumerate([
            ("genome_id", "/genome_ids/0", "G1", "comp_genome_1"),
            ("genome_id", "/genome_ids/1", "G2", "comp_genome_2"),
            ("user_genome", "/user_genomes/0", "/files/F1", "ref_genome"),
            ("user_feature_group", "/user_feature_groups/0", "/groups/FG1", "comp_genome_3")], 1):
        value["inputs"].append({"input_key": pointer, "parameter_pointer": pointer,
            "original_index": index, "kind": kind, "value": text, "expected_track_key": track,
            "source_field": field("/submitted" + pointer)})
    parameters = {"kind": "submitted", "source_field": parent}
    for key in ("min_ident", "min_seq_cov", "min_positives", "max_e_val"):
        parameters[key] = {"value": 0 if key == "min_ident" else None,
            "presence": "value" if key == "min_ident" else "omitted",
            "source_field": field("/submitted/" + key, name=key)}
    value["run_parameter_snapshots"] = [parameters]
    return value


def change(value, path, replacement):
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement


def test_frozen_complete_invalid_values_and_independent_occurrences_survive():
    original = inventory()
    value = validate_proteome_data("ProteinInventory", original)
    assert [row["sequence_symbol_count"] for row in value["records"]] == [4, 5, 0]
    assert value["records"][1]["sequence"] == "AA-?1"
    assert value["records"][0]["description"] == "  first description\t"
    assert value["duplicate_identifier_groups"][0]["record_ordinals"] == [0, 1]
    value["records"][0]["header"] = "mutated"
    assert original == inventory()


@pytest.mark.parametrize("path,replacement", [
    (("observed_header_count",), 2), (("complete_record_count",), 2), (("valid_complete_record_count",), 3),
    (("records", 0, "record_ordinal"), 7), (("records", 0, "sequence_symbol_count"), 5),
    (("records", 0, "sequence_sha256"), "0" * 64), (("records", 0, "sequence_md5"), "0" * 32),
    (("records", 0, "sequence"), "acde"), (("records", 0, "description"), "first description"),
    (("records", 0, "source_field", "pointer"), "/records/1"),
    (("records", 0, "source_field", "sha256"), "0" * 64),
    (("records", 0, "byte_end_exclusive"), 35), (("records", 2, "byte_end_exclusive"), 58),
    (("records", 1, "valid_sequence"), True), (("records", 2, "sequence"), None),
    (("source", "body_complete"), False), (("source", "object_complete"), "unknown"),
    (("duplicate_identifier_groups",), []), (("sequence_groups",), []),
    (("sequence_groups", 0, "members", 0, "inventory_key"), "unrelated-input"),
    (("sequence_groups", 0, "members", 0, "record_ordinal"), 1),
    (("records", 0, "header"), "bad\nheader"),
])
def test_fasta_saved_integrity_mutations_rejected(path, replacement):
    value = inventory()
    change(value, path, replacement)
    with pytest.raises(ProteomeDataError):
        validate_proteome_data("ProteinInventory", value)


def test_incomplete_last_record_stays_unknown_with_prefix_preserved():
    value = inventory()
    row = value["records"][-1]
    row.update(record_complete=False, valid_sequence=False, sequence=None,
               sequence_symbol_count=None, sequence_sha256=None, sequence_md5=None)
    value["complete_record_count"] = 2
    value["source"]["object_complete"] = "unknown"
    assert validate_proteome_data("ProteinInventory", value) == value
    row["sequence_symbol_count"] = 0
    with pytest.raises(ProteomeDataError, match="incomplete_sequence_conflict"):
        validate_proteome_data("ProteinInventory", value)


@pytest.mark.parametrize("supplied", [{"feature_id": "feature:1"}, {"patric_id": "fig|1.1.peg.1"},
                                      {"feature_id": "feature:1", "aa_length": 0, "start": -2}])
def test_feature_identities_are_optional_alternatives_and_unknown_coordinates_preserved(supplied):
    row = metadata("FeatureRecord", supplied)
    assert validate_proteome_data("FeatureRecord", row) == row


@pytest.mark.parametrize("name,supplied", [
    ("FeatureRecord", {"product": "an assignment"}),
    ("FeatureRecord", {"feature_id": "   "}),
    ("FeatureRecord", {"feature_id": "x", "aa_length": -1}),
    ("FeatureRecord", {"feature_id": "x", "aa_sequence_md5": "not-a-digest"}),
    ("GenomeRecord", {"genome_id": "g", "taxon_id": 0}),
    ("GenomeRecord", {"genome_id": "g", "taxon_id": 562.5}),
])
def test_invalid_metadata_cannot_be_marked_valid(name, supplied):
    row = metadata(name, supplied)
    with pytest.raises(ProteomeDataError, match="metadata_validity_conflict"):
        validate_proteome_data(name, row)
    row["valid"] = False
    assert validate_proteome_data(name, row) == row


def test_feature_coordinates_have_explicit_convention_without_inferred_order():
    row = metadata("FeatureRecord", {"feature_id": "x", "start": 8, "end": 2})
    value = snapshot("FeatureSnapshot", row, "one_based_closed")
    assert validate_proteome_data("FeatureSnapshot", value) == value
    value["coordinate_convention"]["value"] = "zero_based_half_open"
    with pytest.raises(ProteomeDataError, match="metadata_validity_conflict"):
        validate_proteome_data("FeatureSnapshot", value)
    value["records"][0]["valid"] = False
    assert validate_proteome_data("FeatureSnapshot", value) == value


def test_metadata_source_locations_are_bound_to_actual_row_and_column():
    value = snapshot("GenomeSnapshot", metadata("GenomeRecord", {"genome_id": "g", "taxon_id": 562}))
    assert validate_proteome_data("GenomeSnapshot", value) == value
    value["records"][0]["taxon_id"]["source_field"]["pointer"] = "/1/taxon_id"
    with pytest.raises(ProteomeDataError, match="source_location_conflict"):
        validate_proteome_data("GenomeSnapshot", value)


def test_sequence_metadata_preserves_native_md5_case_and_checks_actual_string():
    digest = hashlib.md5(b"ACDE").hexdigest()
    row = metadata("FeatureSequenceRecord", {"md5": digest.upper(), "sequence": "acde"})
    assert validate_proteome_data("FeatureSequenceRecord", row) == row
    row["md5"]["value"] = "0" * 32
    with pytest.raises(ProteomeDataError, match="metadata_validity_conflict"):
        validate_proteome_data("FeatureSequenceRecord", row)
    row["valid"] = False
    assert validate_proteome_data("FeatureSequenceRecord", row)["computed_md5"] == digest


def test_native_lexeme_relationship_and_no_boolean_as_numeric():
    value = number(.875, "/score")
    value["lexeme"] = "8.750E-1"
    assert validate_proteome_data("NativeNumber", value) == value
    value["lexeme"] = ".9"
    with pytest.raises(ProteomeDataError, match="numeric_lexeme_conflict"):
        validate_proteome_data("NativeNumber", value)
    value["value"] = True
    with pytest.raises(ProteomeDataError, match="schema_invalid"):
        validate_proteome_data("NativeNumber", value)


@pytest.mark.parametrize("bad", [float("inf"), float("nan"), float("-inf")])
def test_nonfinite_parameters_rejected(bad):
    value = input_index()
    value["run_parameter_snapshots"][0]["min_ident"]["value"] = bad
    with pytest.raises(ProteomeDataError, match="nonfinite_number"):
        validate_proteome_data("InputIndex", value)


def test_original_input_order_reference_and_zero_parameter_snapshot():
    value = input_index()
    assert validate_proteome_data("InputIndex", value) == value
    assert value["run_parameter_snapshots"][0]["min_ident"]["value"] == 0
    value["inputs"][1]["expected_track_key"] = "comp_genome_1"
    with pytest.raises(ProteomeDataError, match="input_track_conflict"):
        validate_proteome_data("InputIndex", value)


@pytest.mark.parametrize("path,replacement", [
    (("reference_original_index",), 5), (("inputs", 0, "original_index"), 2),
    (("inputs", 1, "input_key"), "/genome_ids/0"),
    (("inputs", 2, "source_field", "pointer"), "/other/user_genomes/0"),
    (("run_parameter_snapshots",), []),
    (("run_parameter_snapshots", 0, "max_e_val", "source_field", "pointer"), "/submitted/min_ident"),
])
def test_original_input_relationship_mutations(path, replacement):
    value = input_index()
    change(value, path, replacement)
    with pytest.raises(ProteomeDataError):
        validate_proteome_data("InputIndex", value)


def test_schema_and_values_return_detached_copies_and_no_missing_validator_stub():
    schema = proteome_data_schema("ProteinInventory")
    schema["$defs"].clear()
    assert proteome_data_schema("ProteinInventory")["$defs"]
    for name in ("NativeSource", "ParameterSource"):
        value = inventory()["source"] if name == "NativeSource" else input_index()["parameter_source"]
        assert validate_proteome_data(name, value) == value
    with pytest.raises(ProteomeDataError, match="unknown_contract"):
        proteome_data_schema("NativeJoins")


def test_recursive_and_invalid_unicode_saved_values_fail_with_fixed_errors():
    value = inventory()
    value["diagnostics"].append(value)
    with pytest.raises(ProteomeDataError, match="recursive_json"):
        validate_proteome_data("ProteinInventory", value)
    value = inventory()
    value["records"][0]["header"] = "\ud800"
    with pytest.raises(ProteomeDataError, match="invalid_unicode"):
        validate_proteome_data("ProteinInventory", value)


def test_excessive_nesting_has_a_fixed_contract_failure():
    value = {}
    for _ in range(1400):
        value = {"nested": value}
    with pytest.raises(ProteomeDataError, match="excessive_nesting"):
        validate_proteome_data("NativeSource", value)


def test_invalid_records_cannot_be_presented_as_an_ok_result():
    data = inventory()
    result = {"status": "partial", "value": data, "requirements": [], "diagnostics": []}
    assert validate_proteome_data("ProteinInventoryResult", result) == result
    result["status"] = "ok"
    with pytest.raises(ProteomeDataError, match="successful_result_"):
        validate_proteome_data("ProteinInventoryResult", result)


def test_saved_validation_does_not_read_sources_or_call_scientific_functions(monkeypatch):
    import socket
    import subprocess
    from gene_annotation_episode import bvbrc_proteome_native, blast_pairwise_grader
    value = inventory()
    validate_proteome_data("ProteinInventory", value)  # load static package schema

    def forbidden(*args, **kwargs):
        raise AssertionError("validation attempted source IO or scientific work")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(bvbrc_proteome_native, "parse_genome_comparison", forbidden)
    monkeypatch.setattr(blast_pairwise_grader, "alignment_components", forbidden)
    monkeypatch.setattr(blast_pairwise_grader, "build_pairwise_sheet", forbidden)
    assert validate_proteome_data("ProteinInventory", value) == value
