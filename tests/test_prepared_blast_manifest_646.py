"""Public prepared-data ports reuse search semantics without synthetic searches.

Descriptors here are synthetic. They establish validation behavior, not native
database compatibility, application of offline configuration or file existence.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode import native_blast_database_contracts as c
from test_native_blast_database_contracts import database, forbid_io


@pytest.mark.parametrize("kind", ["blast_protein_sequence", "rps_profile", "delta_profile", "vdb"])
def test_manifest_and_operand_ports_are_pure_and_return_detached_values(monkeypatch, kind):
    operand = database(kind=kind)
    original = deepcopy(operand)
    forbid_io(monkeypatch)
    manifest = c.validate_prepared_blast_database_manifest(operand["manifest"])
    selected = c.validate_native_blast_database_operand(operand)
    assert manifest == original["manifest"]
    assert selected == original
    manifest["files"][0]["size_bytes"] = 99
    selected["identity"]["source"]["pointer"] = "/different"
    assert operand == original


@pytest.mark.parametrize("mutation,reason", [
    ("incomplete", "database_complete_inventory_required"),
    ("duplicate", "database_inventory_duplicate_path"),
    ("uncovered_prefix", "database_native_path_not_in_inventory"),
    ("wrong_preparation", "database_preparation_type_mismatch"),
    ("wrong_method", "database_preparation_method_mismatch"),
    ("conflicting_receipt", "database_file_identity_conflict"),
    ("bad_provenance", "provenance_pointer_invalid"),
])
def test_manifest_and_real_operand_reject_the_same_relationship_defects(mutation, reason):
    operand = database(kind="rps_profile")
    manifest = operand["manifest"]
    if mutation == "incomplete":
        manifest["inventory_complete"] = False
    elif mutation == "duplicate":
        manifest["files"].append(deepcopy(manifest["files"][0]))
    elif mutation == "uncovered_prefix":
        manifest["files"][0]["path"] = "/unrelated/database.pin"
    elif mutation == "wrong_preparation":
        manifest["preparation"]["preparation_type"] = "delta"
    elif mutation == "wrong_method":
        manifest["preparation"]["method"] = "makeblastdb"
    elif mutation == "conflicting_receipt":
        manifest["preparation"]["receipt"]["path"] = manifest["files"][0]["path"]
    else:
        manifest["preparation"]["source"]["pointer"] = "/bad~escape"
    for function, value in ((c.validate_prepared_blast_database_manifest, manifest),
                            (c.validate_native_blast_database_operand, operand)):
        with pytest.raises(ValueError, match="^native_blast_database_" + reason + "$"):
            function(value)


def test_operand_manifest_file_is_checked_without_fabricating_one_for_bare_manifest():
    operand = database(kind="rps_profile")
    operand["manifest_file"]["path"] = operand["manifest"]["files"][0]["path"]
    assert c.validate_prepared_blast_database_manifest(operand["manifest"]) == operand["manifest"]
    with pytest.raises(ValueError, match="native_blast_database_database_file_identity_conflict"):
        c.validate_native_blast_database_operand(operand)


def test_vdb_manifest_requires_recorded_offline_configuration_but_does_not_apply_it():
    operand = database(kind="vdb")
    operand["manifest"]["access"]["offline_configuration"] = None
    for function, value in ((c.validate_prepared_blast_database_manifest, operand["manifest"]),
                            (c.validate_native_blast_database_operand, operand)):
        with pytest.raises(ValueError, match="native_blast_database_offline_configuration_unestablished"):
            function(value)


def test_operand_still_checks_exact_selected_identity():
    operand = database(kind="rps_profile")
    operand["database_key"] = "another-selection"
    with pytest.raises(ValueError, match="native_blast_database_database_manifest_operand_mismatch:database_key"):
        c.validate_native_blast_database_operand(operand)


@pytest.mark.parametrize("invalid", [True, float("nan"), float("inf")])
def test_manifest_does_not_accept_boolean_or_nonfinite_file_sizes(invalid):
    manifest = database(kind="rps_profile")["manifest"]
    manifest["files"][0]["size_bytes"] = invalid
    with pytest.raises(ValueError):
        c.validate_prepared_blast_database_manifest(manifest)
