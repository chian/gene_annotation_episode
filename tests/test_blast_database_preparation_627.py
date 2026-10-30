"""Retained native makeblastdb facts and pure relationship/projection checks.

No test invokes makeblastdb or a database search. Native binaries were run once
in runner529/check084; these tests use the retained capture and metadata JSON.
Mutated cases below are explicitly synthetic counterexamples.
"""
from copy import deepcopy
import builtins
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import blast_database_preparation as p
from gene_annotation_episode import native_blast_standard_database_contracts as standard
from gene_annotation_episode.domain import ContractError


EVIDENCE = Path(__file__).resolve().parents[1] / "verification" / "tool_graders_blast_database_preparation_2026-10-28_627"


def retained(name="build_dna_v5"):
    fixture = json.loads((EVIDENCE / "PREPARATION_INPUTS_001.json").read_text())
    return next(c for c in fixture["cases"] if c["name"] == name), fixture["source_capture"]


def project(record, receipt, **kwargs):
    return p.project_prepared_blast_database(record, contract="standard",
        preparation_receipt=receipt, input_manifest=None, metadata_manifests=[], **kwargs)


def forbid_io(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("pure preparation port attempted file/process/network access")
    for obj, name in [(builtins, "open"), (Path, "open"), (Path, "resolve"),
                      (Path, "glob"), (os, "stat"), (os, "listdir"),
                      (subprocess, "run"), (subprocess, "Popen"),
                      (socket, "socket"), (socket, "getaddrinfo"),
                      (standard, "validate_standard_blast_database_job")]:
        monkeypatch.setattr(obj, name, fail)


@pytest.mark.parametrize("name,count,residues,unit,files,native_bytes", [
    ("build_dna_v4", 3, 31, "nt", 7, 461),
    ("build_dna_v5", 3, 31, "nt", 10, 49613),
    ("build_protein_v5", 2, 35, "aa", 10, 49522),
])
def test_authentic_full_native_families_and_numerical_facts(name, count, residues, unit, files, native_bytes):
    case, receipt = retained(name)
    original = deepcopy(case["arguments"])
    metadata_row = case["native_metadata_files"][0]
    raw = (EVIDENCE / metadata_row["relative_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == metadata_row["sha256"]
    assert len(raw) == metadata_row["size_bytes"]
    native = json.loads(raw)
    record = p.populate_database_artifact_set(**original)
    assert record["outputs"] == original["outputs"]
    assert record["inputs"] == original["inputs"]
    assert record["original_outcome"] == original["outcome"]
    assert record["inventory_complete"] is True
    assert record["compatibility"] == "unverified"
    assert not any(c["name"] == "native_integrity" for c in record["checks"])
    fields = {f["field_name"]: f for f in record["native_metadata"]}
    for row in fields.values():
        assert row["value"] == native[row["json_pointer"][1:]]
        assert row["occurrence_id"] == metadata_row["source_occurrence_id"]
    assert fields["database_sequence_count"]["value"] == count
    assert fields["database_residue_count"]["value"] == residues
    assert fields["database_residue_count"]["unit"] == unit
    assert fields["database_bytes"]["value"] == native_bytes
    assert record["operation"]["parameters"]["max_file_size"] is None
    assert record["operation"]["parameters"]["taxid"] is None
    assert record["failures"] == []
    manifest = project(record, receipt)["manifest"]
    assert len(manifest["files"]) == files
    assert manifest["files"] == [
        {"path": row["native_path"], "sha256": row["sha256"], "size_bytes": row["size_bytes"]}
        for row in record["outputs"] if row["role"] in {"database_file", "database_metadata"}]
    # The writer metadata's files/bytes-total exclude its own JSON sidecar. The
    # captured family contains that sidecar as an additional actual component.
    assert len(native["files"]) == files - 1
    assert sum(row["size_bytes"] for row in manifest["files"]) == native_bytes + len(raw)
    assert manifest["preparation"]["receipt"] == receipt
    assert manifest["preparation"]["argv"] == original["argv"]
    assert manifest["preparation"]["input_manifest"] is None
    record["outputs"][0]["sha256"] = "f" * 64
    assert case["arguments"] == original


def test_saved_only_revalidation_and_projection_are_pure_and_detached(monkeypatch):
    case, receipt = retained()
    record = p.populate_database_artifact_set(**case["arguments"])
    saved = json.loads(json.dumps(record))
    expected = project(saved, receipt)
    forbid_io(monkeypatch)
    assert p.populate_database_artifact_set(**case["arguments"]) == saved
    checked = p.validate_database_artifact_relationships(saved)
    assert checked == saved
    assert project(saved, receipt) == expected
    assert standard.validate_standard_prepared_blast_database_manifest(expected["manifest"]) == expected["manifest"]
    checked["outputs"].clear()
    assert saved["outputs"]


def test_native_duplicate_id_failure_keeps_actual_partial_build_and_returncode():
    case, receipt = retained("build_duplicate_ids")
    record = p.populate_database_artifact_set(**case["arguments"])
    assert record["original_outcome"]["returncode"] == 1
    assert len(record["outputs"]) == 7  # Five database fragments and two streams.
    assert record["outputs"] == case["arguments"]["outputs"]
    assert record["inventory_complete"] is True  # Complete capture of a failed build.
    assert record["native_metadata"] == []
    assert record["compatibility"] == "unverified"
    result = project(record, receipt)
    assert result["status"] == "unavailable" and result["manifest"] is None
    assert {f["code"] for f in result["failures"]} >= {
        "native_nonzero_exit", "output_family_incomplete", "preparation_not_successful"}
    assert next(f for f in result["failures"] if f["code"] == "native_nonzero_exit")["native_returncode"] == 1


@pytest.mark.parametrize("state,expected", [("failed", "native_start_failed"), ("unknown", "preparation_not_successful")])
def test_no_start_preserves_observed_failure_vs_unknown(state, expected):
    case, receipt = retained()
    args = case["arguments"]
    args.update(outputs=[], native_metadata=[])
    args["outcome"] = {"started": False, "returncode": None, "state": state,
                       "writer_closed": True, "inventory_complete": True}
    record = p.populate_database_artifact_set(**args)
    assert record["original_outcome"] == args["outcome"]
    assert record["failures"][0]["code"] == expected
    assert project(record, receipt)["status"] == "unavailable"


def test_missing_native_count_is_not_zero_and_invalid_count_is_qualified():
    case, receipt = retained()
    args = case["arguments"]
    native = next(f for f in args["native_metadata"] if f["field_name"] == "database_sequence_count")
    native.update(value=None, missing_reason="native_field_absent")
    record = p.populate_database_artifact_set(**args)
    assert next(f for f in record["native_metadata"] if f["field_name"] == "database_sequence_count")["value"] is None
    assert project(record, receipt)["status"] == "available"
    native["missing_reason"] = "native_field_invalid"
    record = p.populate_database_artifact_set(**args)
    assert project(record, receipt)["status"] == "unavailable"
    assert "native_document_invalid" in {f["code"] for f in record["failures"]}


@pytest.mark.parametrize("change", [
    lambda a: a["outcome"].update(inventory_complete=False),
    lambda a: a["outcome"].update(state="incomplete", writer_closed=False, inventory_complete=False),
    lambda a: a["outputs"][0].update(completeness="partial"),
    lambda a: a["outputs"][0].update(native_path=None),
])
def test_incomplete_capture_keeps_components_and_cannot_project(change):
    case, receipt = retained()
    args = case["arguments"]
    change(args)
    record = p.populate_database_artifact_set(**args)
    assert record["outputs"] == args["outputs"]
    assert record["inventory_complete"] is False
    result = project(record, receipt)
    assert result["manifest"] is None
    assert "output_inventory_incomplete" in {f["code"] for f in result["failures"]}


def test_three_core_extensions_do_not_establish_v5_family_or_complete_capture():
    case, receipt = retained()
    args = case["arguments"]
    args["outputs"] = [r for r in args["outputs"] if r["native_path"].endswith((".nhr", ".nin", ".nsq"))]
    args["native_metadata"] = []
    record = p.populate_database_artifact_set(**args)
    assert record["inventory_complete"] is True  # The caller's capture fact is retained.
    assert project(record, receipt)["status"] == "unavailable"
    assert "output_family_incomplete" in {f["code"] for f in record["failures"]}
    args["outcome"]["inventory_complete"] = False
    record = p.populate_database_artifact_set(**args)
    assert record["inventory_complete"] is False


@pytest.mark.parametrize("suffix", [".nos", ".ntf", ".nin"])
def test_missing_native_listed_component_is_unavailable_without_dropping_others(suffix):
    case, receipt = retained()
    args = case["arguments"]
    args["outputs"] = [r for r in args["outputs"] if not r["native_path"].endswith(suffix)]
    record = p.populate_database_artifact_set(**args)
    assert record["outputs"] == args["outputs"]
    assert project(record, receipt)["status"] == "unavailable"
    assert "output_family_incomplete" in {f["code"] for f in record["failures"]}


def test_unknown_additional_component_is_retained_in_projected_family():
    case, receipt = retained()
    args = case["arguments"]
    row = deepcopy(args["outputs"][0])
    row.update(occurrence_id="synthetic-future-component", ordinal=99,
               native_path=args["native_paths"][0] + ".future", artifact_ref="synthetic-future-bytes",
               native_format="unknown", sha256="e" * 64, size_bytes=0)
    args["outputs"].append(row)
    record = p.populate_database_artifact_set(**args)
    manifest = project(record, receipt)["manifest"]
    assert manifest["files"][-1] == {"path": row["native_path"], "sha256": "e" * 64, "size_bytes": 0}


@pytest.mark.parametrize("field,value", [
    ("database_format_version", 4), ("database_title", "a different requested title"),
])
def test_native_metadata_request_conflicts_keep_both_values(field, value):
    case, receipt = retained()
    args = case["arguments"]
    native = next(f for f in args["native_metadata"] if f["field_name"] == field)
    native["value"] = value
    record = p.populate_database_artifact_set(**args)
    assert record["native_metadata"] == args["native_metadata"]
    assert record["operation"] == args["operation"]
    assert project(record, receipt)["status"] == "unavailable"
    assert "database_metadata_conflict" in {f["code"] for f in record["failures"]}


def test_conflicting_native_counts_and_wrong_molecule_units_are_qualified():
    case, receipt = retained()
    args = case["arguments"]
    row = deepcopy(next(f for f in args["native_metadata"] if f["field_name"] == "database_sequence_count"))
    row.update(value=0, json_pointer="/contradictory-count")
    args["native_metadata"].append(row)
    residues = next(f for f in args["native_metadata"] if f["field_name"] == "database_residue_count")
    residues["unit"] = "aa"
    record = p.populate_database_artifact_set(**args)
    assert {f["code"] for f in record["failures"]} >= {"database_metadata_conflict", "database_kind_conflict"}
    assert record["native_metadata"][-1]["value"] == 0
    assert project(record, receipt)["manifest"] is None


def test_explicit_taxid_and_mask_dependencies_keep_occurrences_not_byte_identity():
    case, receipt = retained()
    args = case["arguments"]
    for role, fmt in [("taxid_map", "text"), ("mask_input", "maskinfo_asn1_text")]:
        row = deepcopy(args["inputs"][0])
        row.update(occurrence_id=role, role=role, ordinal=len(args["inputs"]), native_format=fmt,
                   native_path="/synthetic/" + role, artifact_ref="synthetic:" + role)
        args["inputs"].append(row)
        args["operation"]["input_occurrence_ids"].append(role)
        args["dependency_bindings"].append({"role": role, "occurrence_id": role})
    args["operation"]["parameters"].update(taxid_map_occurrence_id="taxid_map", mask_occurrence_ids=["mask_input"])
    record = p.populate_database_artifact_set(**args)
    assert record["dependencies"] == args["dependency_bindings"]
    assert len({row["sha256"] for row in record["inputs"]}) == 1  # Explicit synthetic equal-byte occurrences.
    assert len(record["inputs"]) == 3
    args["dependency_bindings"].pop()
    with pytest.raises(ContractError, match="artifact_set_dependency_population"):
        p.populate_database_artifact_set(**args)


@pytest.mark.parametrize("change", [
    lambda a: a["inputs"][0].update(size_bytes=True),
    lambda a: a["outputs"].append(deepcopy(a["outputs"][0])),
    lambda a: a["native_metadata"][0].update(occurrence_id="missing"),
    lambda a: a["native_metadata"][1].update(value=True),
    lambda a: a["native_paths"].__setitem__(0, "/not/../normalized"),
    lambda a: a["operation"]["parameters"].update(database_format_version=True),
    lambda a: a["identity"].update(function_confidence=0.99),
])
def test_malformed_contracts_reject_without_native_work(change):
    case, _ = retained()
    change(case["arguments"])
    with pytest.raises(ContractError, match="blast_utility_"):
        p.populate_database_artifact_set(**case["arguments"])


def test_saved_forged_observations_and_compatibility_are_rejected():
    case, _ = retained()
    record = p.populate_database_artifact_set(**case["arguments"])
    altered = deepcopy(record); altered["checks"].clear()
    with pytest.raises(ContractError, match="preparation_observation_conflict"):
        p.validate_database_artifact_relationships(altered)
    altered = deepcopy(record); altered["compatibility"] = "validated"
    with pytest.raises(ContractError, match="database_compatibility_evidence"):
        p.validate_database_artifact_relationships(altered)


def test_same_path_conflicting_output_bytes_are_schema_relationship_error():
    case, _ = retained()
    args = case["arguments"]
    row = deepcopy(args["outputs"][0])
    row.update(occurrence_id="synthetic-conflicting-capture", ordinal=99, sha256="b" * 64)
    args["outputs"].append(row)
    with pytest.raises(ContractError, match="artifact_path_identity_conflict"):
        p.populate_database_artifact_set(**args)


def test_projection_receipt_collision_is_specific_unavailability():
    case, receipt = retained()
    record = p.populate_database_artifact_set(**case["arguments"])
    receipt["path"] = record["outputs"][0]["native_path"]
    result = project(record, receipt)
    assert result["status"] == "unavailable" and result["manifest"] is None
    assert {f["code"] for f in result["failures"]} == {"supplied_binding_conflict"}


def test_additional_rps_delta_contracts_are_not_silently_accepted():
    case, receipt = retained()
    record = p.populate_database_artifact_set(**case["arguments"])
    with pytest.raises(ContractError, match="projection_contract_unsupported"):
        p.project_prepared_blast_database(record, contract="additional", preparation_receipt=receipt,
                                          input_manifest=None, metadata_manifests=[])


def operand(manifest):
    # Synthetic operand for regression of the original pure relationship
    # validator only. It is not a requested job and no BLAST search is built.
    result = {key: deepcopy(manifest[key]) for key in ("database_key", "kind", "identity", "native_paths")}
    result.update(role="target", manifest=deepcopy(manifest), manifest_file={
        "path": "/synthetic/prepared_manifest.json", "sha256": "d" * 64,
        "size_bytes": 123, "artifact_ref": "synthetic:manifest"})
    return result


@pytest.mark.parametrize("collision", ["receipt", "metadata", "input_manifest"])
def test_direct_manifest_and_original_operand_reject_same_path_conflicts(collision):
    case, receipt = retained()
    manifest = project(p.populate_database_artifact_set(**case["arguments"]), receipt)["manifest"]
    target = manifest["files"][0]
    conflict = {**target, "sha256": "c" * 64, "artifact_ref": "synthetic:collision"}
    if collision == "metadata":
        manifest["metadata_manifests"] = [conflict]
    elif collision == "input_manifest":
        manifest["preparation"]["input_manifest"] = conflict
    else:
        manifest["preparation"]["receipt"] = conflict
    with pytest.raises(ValueError, match="database_file_identity_conflict"):
        standard.validate_standard_prepared_blast_database_manifest(manifest)
    with pytest.raises(ValueError, match="database_file_identity_conflict"):
        standard._database(operand(manifest))


def test_original_operand_retains_manifest_file_and_operand_identity_checks():
    case, receipt = retained()
    manifest = project(p.populate_database_artifact_set(**case["arguments"]), receipt)["manifest"]
    assert standard.validate_standard_prepared_blast_database_manifest(manifest) == manifest
    selected = operand(manifest)
    assert standard._database(selected) is None
    selected["manifest_file"]["path"] = manifest["files"][0]["path"]
    with pytest.raises(ValueError, match="database_file_identity_conflict"):
        standard._database(selected)
    selected = operand(manifest)
    selected["identity"]["value"] = "other"
    with pytest.raises(ValueError, match="database_manifest_operand_mismatch:identity"):
        standard._database(selected)
