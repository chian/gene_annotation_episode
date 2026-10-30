"""Closed-shape and relationship cases; all hand-authored fixtures are synthetic."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.blast_preparation_contracts import (
    blast_preparation_document_schema, validate_blast_preparation_document,
)
from gene_annotation_episode.blast_utility_contracts import (
    blast_utility_record_name_for_version, blast_utility_schema_for_version,
    blast_utility_result_version_for_operation, validate_blast_utility_record as core,
    validate_blast_utility_operation,
)
from gene_annotation_episode.domain import ContractError


def operation(mode, **updates):
    entries = [{"ordinal": 0, "database_key": "db", "native_path_index": 0,
                "native_reference": "/source/db", "line_number": None}]
    parameters = {
        "convert_gi_list": {"input_occurrence_id": "ids", "output_path": "out/ids.gil"},
        "convert_seqid_list": {"input_occurrence_id": "ids", "output_path": "out/ids.bsl", "title": "selected", "seqid_database_key": None},
        "inspect_seqid_list": {"input_occurrence_id": "ids"},
        "create_subset_alias": {"output_prefix": "out/subset", "title": "subset", "source_database_key": "db",
            "restriction": {"kind": "seqid_list", "occurrence_id": "ids", "format": "seqid_list_binary"}},
        "aggregate_databases": {"output_prefix": "out/aggregate", "title": "aggregate",
            "classic_list": {"source": "inline", "entries": entries}, "vdb_list": None},
        "aggregate_volumes": {"output_prefix": "out/volume", "title": "volumes", "source_database_key": "db",
            "num_volumes": 1, "volume_entries": entries},
        "create_megablast_index": {"input_format": "fasta", "input_occurrence_id": "sequence", "source_database_key": None,
            "old_style_index": True, "legacy": True, "output_prefix": "out/index", "idmap": False,
            "db_mask": None, "nmer": 8, "ws_hint": 8, "stride": 2, "volume_size_mb": 10,
            "verbosity": "normal", "statistics_path": None},
        "show_filters": {"source_database_key": "db"},
        "create_profile_database": {"profile_list_occurrence_id": "list", "profile_entries": [{"ordinal": 0,
            "input_occurrence_id": "profile", "native_reference": "input.asn", "line_number": 1, "token_ordinal": 0}],
            "profile_type": "rps", "input_format": "pssm_asn1_text", "output_prefix": "out/profiles", "title": "profiles",
            "database_format_version": 5, "max_smp_per_volume": 2500, "create_sequence_indexes": True,
            "word_score_threshold": 9.82, "force_threshold": True, "gap_open": None, "gap_extend": None,
            "scale": 100.0, "matrix": "BLOSUM80", "observations_threshold": 6.0, "exclude_invalid": False,
            "taxid": None, "taxid_map_occurrence_id": None},
    }
    program = "makeprofiledb" if mode == "create_profile_database" else "makembindex" if mode in {"create_megablast_index", "show_filters"} else "blastdb_aliastool"
    ids = (["ids"] if mode in {"convert_gi_list", "convert_seqid_list", "inspect_seqid_list", "create_subset_alias"}
        else ["sequence"] if mode == "create_megablast_index" else ["list", "profile"] if mode == "create_profile_database" else [])
    key = "db" if mode in {"create_subset_alias", "aggregate_volumes", "show_filters"} else None
    molecule = "unknown" if mode in {"convert_gi_list", "convert_seqid_list", "inspect_seqid_list"} else "protein" if mode == "create_profile_database" else "dna"
    value = {"version": "blast_utility_operation_v2", "program": program, "mode": mode,
        "input_occurrence_ids": ids, "database_key": key, "molecule": molecule, "parameters": parameters[mode]}
    value.update(updates)
    return value


MODES = ["convert_gi_list", "convert_seqid_list", "inspect_seqid_list", "create_subset_alias", "aggregate_databases",
         "aggregate_volumes", "create_megablast_index", "show_filters", "create_profile_database"]


@pytest.mark.parametrize("mode", MODES)
def test_all_nine_operations_and_exact_result_registry(mode):
    value = operation(mode)
    assert validate_blast_utility_operation(value) == value
    expected = "blast_database_inspection_v2" if mode in {"inspect_seqid_list", "show_filters"} else "blast_database_artifact_set_v2"
    assert blast_utility_result_version_for_operation(value) == expected
    assert blast_utility_record_name_for_version(expected) in {"DatabaseInspection", "DatabaseArtifactSet"}
    copy = blast_utility_schema_for_version(expected)
    copy.clear()
    assert blast_utility_schema_for_version(expected)


@pytest.mark.parametrize("field,value", [("max_smp_per_volume", True), ("max_smp_per_volume", 0),
    ("word_score_threshold", float("inf")), ("scale", float("nan")), ("gap_open", False)])
def test_strict_numeric_types_and_finite_values(field, value):
    op = operation("create_profile_database")
    op["parameters"][field] = value
    with pytest.raises(ContractError):
        validate_blast_utility_operation(op)


def test_selection_relationships_reject_extra_missing_and_invented_values():
    changes = []
    op = operation("aggregate_databases"); op["parameters"]["classic_list"]["entries"][0]["ordinal"] = 1; changes.append(op)
    op = operation("aggregate_databases"); op["parameters"]["classic_list"]["entries"][0]["native_reference"] = "two names"; changes.append(op)
    op = operation("create_subset_alias"); op["database_key"] = "other"; changes.append(op)
    op = operation("create_megablast_index"); op["parameters"]["old_style_index"] = False; changes.append(op)
    op = operation("convert_seqid_list"); op["molecule"] = "protein"; changes.append(op)
    op = operation("create_profile_database"); op["input_occurrence_ids"].append("extra"); changes.append(op)
    for op in changes:
        with pytest.raises(ContractError):
            validate_blast_utility_operation(op)


@pytest.mark.parametrize("profile_type", ["rps", "delta", "cobalt"])
@pytest.mark.parametrize("input_format", ["pssm_asn1_text", "pssm_asn1_binary"])
def test_declared_profile_variants_are_not_dropped(profile_type, input_format):
    op = operation("create_profile_database")
    op["parameters"].update(profile_type=profile_type, input_format=input_format)
    assert validate_blast_utility_operation(op) == op


def test_parameter_observations_require_location_and_do_not_accept_requested_defaults():
    observed = {"parameter": "ws_hint", "scope_key": "stderr", "value": 10, "effect": "effective",
        "occurrence_id": "stderr", "line_number": 1, "native_lexeme": "adjusted to 10", "missing_reason": None}
    assert core("ParameterObservation", observed) == observed
    for updates in ({"value": True}, {"occurrence_id": None}, {"value": None}, {"effect": "ignored"}):
        with pytest.raises(ContractError):
            core("ParameterObservation", {**observed, **updates})
    ignored = {**observed, "value": None, "effect": "ignored"}
    assert core("ParameterObservation", ignored) == ignored
    unknown = {**ignored, "effect": "unknown", "occurrence_id": None, "line_number": None,
               "native_lexeme": None, "missing_reason": "native_field_absent"}
    assert core("ParameterObservation", unknown) == unknown


def test_document_is_closed_copied_and_alias_length_is_not_exact_extracted_length():
    field = {"field_name": "database_residue_count", "value": 13, "unit": "symbols", "value_basis": "native_reported",
        "native_lexeme": "13", "occurrence_id": "alias", "line_number": 4, "json_pointer": None, "missing_reason": None}
    doc = {"version": "blast_preparation_document_v1", "kind": "alias", "occurrence_id": "alias",
        "native_fields": [field], "rows": [{"row_ordinal": 0, "line_number": 4, "native_key": "LENGTH",
            "value_lexeme": "13", "tokens": []}], "checks": [], "failures": []}
    assert validate_blast_preparation_document(doc) == doc
    result = validate_blast_preparation_document(doc); result["native_fields"][0]["value"] = 12
    assert doc["native_fields"][0]["value"] == 13
    bad = deepcopy(doc); bad["native_fields"][0]["value_basis"] = "native_reported_exact"
    with pytest.raises(ContractError): validate_blast_preparation_document(bad)
    bad = deepcopy(doc); bad["native_fields"][0]["value"] = 12
    with pytest.raises(ContractError): validate_blast_preparation_document(bad)
    with pytest.raises(ContractError): validate_blast_preparation_document({**doc, "invented": 0})
    schema = blast_preparation_document_schema(); schema.clear(); assert blast_preparation_document_schema()


def test_legacy_operation_stays_byte_identical_and_new_version_is_not_injected():
    op = {"version": "blast_utility_operation_v1", "program": "blastdbcmd", "mode": "info",
        "input_occurrence_ids": [], "database_key": "db", "molecule": "dna", "parameters": {"exact_length": True}}
    serialized = json.dumps(op, separators=(",", ":"))
    assert json.dumps(validate_blast_utility_operation(op), separators=(",", ":")) == serialized
    assert blast_utility_result_version_for_operation(op) == "blast_database_inspection_v1"


def test_input_copy_receipt_preserves_missing_and_changed_states_without_fake_defaults():
    pair = {"sha256": "1" * 64, "size_bytes": 1}
    row = {"kind": "input_copy", "input_key": "source", "source_path": "/source/a", "relative_path": "inputs/a",
           "expected": pair, "staged": pair, "final": None}
    assert core("MaterializationReceipt", row) == row
    with pytest.raises(ContractError): core("MaterializationReceipt", {**row, "relative_path": "../a"})


def test_volume_entries_can_bind_multiple_explicit_sources_without_losing_parent_source():
    op = operation("aggregate_volumes")
    op["parameters"]["volume_entries"].append({"ordinal": 1, "database_key": "second",
        "native_path_index": 0, "native_reference": "/source/second", "line_number": None})
    op["parameters"]["num_volumes"] = 2
    assert validate_blast_utility_operation(op)["database_key"] == "db"
