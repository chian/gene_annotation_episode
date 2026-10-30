"""Pure database-copy joins with synthetic same-file, separately retained roles.

No native command, acquisition, database-content read, or historical-run edit.
The 647 fixture builders supply the unchanged public population contracts.
"""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.blast_database_preparation import (
    populate_database_artifact_set,
    validate_database_artifact_relationships,
)
from gene_annotation_episode.blast_preparation_inputs import parse_blast_alias_document
from gene_annotation_episode.blast_preparation_population import (
    populate_blast_preparation_artifact_set as populate,
    validate_blast_preparation_relationships,
)
from gene_annotation_episode.domain import ContractError
from test_blast_preparation_contracts_647 import operation
from test_blast_preparation_population_647 import common, database, occurrence, projection


def volume_args(*, metadata_first=False):
    """A declared one-member synthetic DB; .njs is also retained as metadata."""
    raw = b'{"fixture":"synthetic database member and metadata"}\n'
    source = occurrence("db-file", "database_file", raw,
        fmt="blastdb_metadata_json", path="/source/db.njs")
    metadata = {**source, "occurrence_id": "db-metadata",
        "role": "database_metadata", "native_format": "json"}
    copied = {**source, "occurrence_id": "copy", "ordinal": 1,
        "native_path": "/attempt/out/volume.00.njs"}
    _, binding = database()
    originals = [metadata, source] if metadata_first else [source, metadata]
    binding["occurrence_ids"] = [r["occurrence_id"] for r in originals]
    pair = {k: source[k] for k in ("sha256", "size_bytes")}
    receipt = {"kind": "database_copy", "database_key": "db",
        "source_path": source["native_path"], "relative_path": "out/volume.00.njs",
        "expected": deepcopy(pair), "staged": deepcopy(pair), "final": deepcopy(pair)}
    alias_raw = b"TITLE volumes\nDBLIST /attempt/out/volume.00\nNSEQ 3\nLENGTH 33\n"
    alias = occurrence("alias", "alias_file", alias_raw, direction="output",
        fmt="blast_alias_text", path="/attempt/out/volume.nal")
    return common(operation("aggregate_volumes"), inputs=[*originals, copied],
        outputs=[alias], bindings=[binding], materializations=[receipt],
        documents=[parse_blast_alias_document(alias_raw, occurrence=alias)])


def assert_dependency_failure(args):
    record = populate(**args)
    assert {r["code"] for r in record["failures"]} == {"dependency_unavailable"}
    assert record["inputs"] == args["inputs"]
    assert record["materializations"] == args["materializations"]
    assert projection(record)["status"] == "unavailable"
    assert validate_blast_preparation_relationships(json.loads(json.dumps(record))) == record
    forged = deepcopy(record)
    forged["failures"] = []
    with pytest.raises(ContractError, match="blast_utility_preparation_failure_missing"):
        validate_blast_preparation_relationships(forged)


@pytest.mark.parametrize("metadata_first", [False, True])
def test_same_file_distinct_roles_survive_population_projection_and_saved_validation(metadata_first):
    args = volume_args(metadata_first=metadata_first)
    supplied = deepcopy(args)
    record = populate(**args)
    assert args == supplied
    assert record["failures"] == []
    assert record["inputs"] == supplied["inputs"]
    assert record["database_bindings"] == supplied["database_bindings"]
    assert record["materializations"] == supplied["materializations"]
    originals = [r for r in record["inputs"] if r["native_path"] == "/source/db.njs"]
    assert {(r["occurrence_id"], r["role"], r["native_format"]) for r in originals} == {
        ("db-file", "database_file", "blastdb_metadata_json"),
        ("db-metadata", "database_metadata", "json"),
    }
    assert len({(r["artifact_ref"], r["sha256"], r["size_bytes"]) for r in originals}) == 1
    assert record["native_metadata"] == supplied["documents"][0]["native_fields"]
    assert {r["field_name"]: r["value"] for r in record["native_metadata"]} == {
        "database_title": "volumes", "database_sequence_count": 3, "database_residue_count": 33,
    }
    saved = json.loads(json.dumps(record))
    assert validate_database_artifact_relationships(saved) == record
    prepared = projection(saved)
    assert prepared["status"] == "available"
    assert {r["path"] for r in prepared["manifest"]["files"]} == {
        "/source/db.njs", "/attempt/out/volume.00.njs", "/attempt/out/volume.nal",
    }
    context = {k: args.pop(k) for k in ("database_bindings", "materializations", "documents")}
    assert populate_database_artifact_set(**args, preparation_context=context,
        dependency_bindings=record["dependencies"], native_metadata=record["native_metadata"]) == record


@pytest.mark.parametrize("case", ["missing_file", "wrong_role", "wrong_source_path"])
def test_metadata_cannot_replace_missing_or_wrong_database_file(case):
    args = volume_args()
    if case == "missing_file":
        args["inputs"] = [r for r in args["inputs"] if r["occurrence_id"] != "db-file"]
        args["database_bindings"][0]["occurrence_ids"].remove("db-file")
    elif case == "wrong_role":
        args["inputs"][0].update(role="database_manifest", native_format="json")
    else:
        args["inputs"][0]["native_path"] = "/different/db.njs"
    assert_dependency_failure(args)


def test_matching_file_from_another_database_binding_is_not_the_selected_original():
    args = volume_args()
    selected = args["database_bindings"][0]
    selected["occurrence_ids"] = ["db-metadata"]
    other = deepcopy(selected)
    other.update(database_key="other", occurrence_ids=["db-file"])
    other["identity"]["value"] = "other"
    other["source_ref"] = "manifest-other"
    args["database_bindings"].append(other)
    args["operation"]["parameters"]["num_volumes"] = 2
    args["operation"]["parameters"]["volume_entries"].append({"ordinal": 1,
        "database_key": "other", "native_path_index": 0,
        "native_reference": "/source/db", "line_number": None})
    alias_raw = b"TITLE volumes\nDBLIST /attempt/out/volume.00 /source/db\nNSEQ 6\nLENGTH 66\n"
    alias = occurrence("alias", "alias_file", alias_raw, direction="output",
        fmt="blast_alias_text", path="/attempt/out/volume.nal")
    args["outputs"] = [alias]
    args["documents"] = [parse_blast_alias_document(alias_raw, occurrence=alias)]
    assert_dependency_failure(args)


@pytest.mark.parametrize("saved", [False, True])
def test_two_matching_database_files_remain_ambiguous_even_with_metadata(saved):
    args = volume_args(metadata_first=True)
    target = populate(**args) if saved else args
    original = next(r for r in target["inputs"] if r["occurrence_id"] == "db-file")
    target["inputs"].append({**original, "occurrence_id": "another-original", "ordinal": 2})
    target["database_bindings"][0]["occurrence_ids"].append("another-original")
    with pytest.raises(ContractError, match="blast_utility_materialization_original_ambiguous"):
        validate_blast_preparation_relationships(target) if saved else populate(**target)


@pytest.mark.parametrize("field,value", [("sha256", "0" * 64), ("size_bytes", 999)])
@pytest.mark.parametrize("saved", [False, True])
def test_copy_expected_identity_must_match_selected_file(field, value, saved):
    args = volume_args()
    target = populate(**args) if saved else args
    target["materializations"][0]["expected"][field] = value
    with pytest.raises(ContractError, match="blast_utility_materialization_original_identity"):
        validate_blast_preparation_relationships(target) if saved else populate(**target)


@pytest.mark.parametrize("field,value,code", [
    ("database_key", "unselected", "materialization_database_reference"),
    ("final", {"sha256": "0" * 64, "size_bytes": 999}, "materialization_final_identity"),
])
def test_receipt_wrong_database_or_final_identity_is_rejected(field, value, code):
    args = volume_args()
    args["materializations"][0][field] = value
    with pytest.raises(ContractError, match="blast_utility_" + code):
        populate(**args)


@pytest.mark.parametrize("phase", ["staged", "final"])
def test_changed_copy_is_retained_as_identity_failure(phase):
    args = volume_args()
    changed = {"sha256": "0" * 64, "size_bytes": 999}
    args["materializations"][0][phase] = changed
    if phase == "final":
        args["inputs"][2].update(changed, artifact_ref="artifact_" + changed["sha256"])
    record = populate(**args)
    assert {r["code"] for r in record["failures"]} == {"input_identity_mismatch"}
    assert record["failures"][0]["occurrence_id"] == "copy"
    assert record["inputs"] == args["inputs"]
    assert projection(record)["status"] == "unavailable"
    assert validate_blast_preparation_relationships(json.loads(json.dumps(record))) == record
