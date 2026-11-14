"""Synthetic relationship cases for pure 624 contracts; no native execution."""
from copy import deepcopy
import hashlib
import json

import jsonschema
import pytest

from gene_annotation_episode.blast_utility_contracts import (
    SCHEMAS, validate_blast_utility_operation, validate_blast_utility_record,
    validate_blast_utility_result,
)
from gene_annotation_episode.domain import ContractError


def occurrence(key="out", *, role="stdout", direction="output", fmt="text", data=b"synthetic\n"):
    return {"occurrence_id": key, "direction": direction, "role": role, "ordinal": 0,
        "artifact_ref": "synthetic:" + key, "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data), "native_format": fmt, "completeness": "complete",
        "native_path": "/retained/" + key}


def outcome(**updates):
    return {"started": True, "returncode": 0, "state": "succeeded",
            "writer_closed": True, "inventory_complete": True, **updates}


def failure(code="native_row_invalid", **updates):
    return {"stage": "parse", "code": code, "occurrence_id": "out", "record_key": None,
            "line_number": 1, "native_returncode": None, **updates}


def observation(**updates):
    return {"name": "syntax", "status": "pass", "subject_refs": ["out"],
        "method": "native_format_parser", "reason": None, "evidence_occurrence_ids": ["out"], **updates}


def operation(mode="extract_sequences", *, molecule="dna", **parameters):
    variants = {
        "create_sequence_database": ("makeblastdb", {
            "input_type": "fasta", "database_format_version": 5, "output_prefix": "db/tiny",
            "title": "synthetic", "parse_seqids": True, "hash_index": False,
            "max_file_size": None, "taxid": None, "taxid_map_occurrence_id": None,
            "mask_occurrence_ids": []}),
        "extract_sequences": ("blastdbcmd", {
            "selectors": [{"ordinal": 0, "value": "ALPHA"}],
            "output_format": "blastdbcmd_tabular_v1", "range": None, "strand": "plus",
            "get_dups": False, "target_only": False}),
        "info": ("blastdbcmd", {"exact_length": True}),
        "metadata": ("blastdbcmd", {}),
        "integrity": ("blastdbcheck", {"full": True, "stride": None, "random_count": None,
            "ends_count": None, "no_isam": False, "legacy_file_checks": False,
            "require_taxids": False, "cdd_delta": False}),
    }
    program, selected = variants[mode]
    return {"version": "blast_utility_operation_v1", "program": program, "mode": mode,
        "input_occurrence_ids": ["source"] if program == "makeblastdb" else [],
        "database_key": None if program == "makeblastdb" else "tiny",
        "molecule": molecule, "parameters": {**selected, **parameters}}


def binding(*, molecule="dna"):
    return {"database_key": "tiny", "kind": "blast_nucleotide_sequence" if molecule == "dna"
        else "blast_protein_sequence", "molecule": molecule,
        "identity": {"namespace": "fixture", "value": "tiny", "version": None, "release": None},
        "source_ref": "synthetic:manifest", "native_paths": ["/retained/tiny"],
        "occurrence_ids": ["db-file"], "inventory_complete": True}


def field(**updates):
    return {"field_name": "database_sequence_count", "value": 2, "unit": "sequences",
        "value_basis": "native_reported_exact", "native_lexeme": "2", "occurrence_id": "out",
        "line_number": 1, "json_pointer": None, "missing_reason": None, **updates}


def extraction():
    return {"version": "blast_sequence_extraction_v1", "operation": operation(),
        "database_binding": binding(), "original_outcome": outcome(),
        "output_occurrence": occurrence(fmt="blastdbcmd_tabular_v1", data=b"7\tALPHA\tALPHA.1\t4\tacgt\n"),
        "records": [{"record_key": "out#/records/2", "native_row_ordinal": 2, "line_number": 4,
            "matched_selector_ordinals": [0], "association": "exact", "native_oid": 7,
            "native_identifier": "ALPHA", "native_accession": "ALPHA.1", "native_reported_length": 4,
            "native_length_basis": "full_sequence", "original_sequence": "acgt",
            "normalized_sequence": "ACGT", "returned_symbol_count": 4, "molecule": "dna",
            "requested_range": None, "effective_range": {"start_0based": 0, "end_exclusive": 4, "strand": "plus"},
            "completeness": "complete", "checks": [], "failures": []}],
        "missing_selector_ordinals": [], "unexpected_record_keys": [],
        "population_completeness": "complete_selection", "checks": [], "failures": []}


def inspection():
    return {"version": "blast_database_inspection_v1", "operation": operation("info"),
        "database_binding": binding(), "output_occurrence": occurrence(fmt="blastdb_info_text"),
        "original_outcome": outcome(), "native_fields": [field()], "completeness": "complete",
        "checks": [observation()], "failures": []}


def integrity():
    return {"version": "blast_database_integrity_v1", "operation": operation("integrity"),
        "database_binding": binding(), "stdout_occurrence": occurrence(fmt="blastdbcheck_text"),
        "stderr_occurrence": occurrence("err", role="stderr"), "original_outcome": outcome(),
        "scope": "unknown", "observed_checked_count": None, "observed_population_count": None,
        "observed_sampled_oids": None, "realized_seed": None, "diagnostics": [],
        "checks": [], "failures": []}


def artifact_set(version=5):
    op = operation("create_sequence_database", database_format_version=version)
    outputs = [occurrence("tiny." + ext, role="database_file", fmt="blastdb_binary", data=ext.encode())
               for ext in ("nhr", "nin", "nsq", "ndb", "not", "ntf", "nto")]
    return {"version": "blast_database_artifact_set_v1", "kind": "sequence_database",
        "operation": op, "original_outcome": outcome(), "database_key": "tiny",
        "identity": {"namespace": "fixture", "value": "tiny", "version": None, "release": None,
            "scope": None, "preparation_type": "sequence_database",
            "source": {"source_ref": "synthetic:manifest", "pointer": ""}},
        "software": {"name": "makeblastdb", "version": None, "executable_sha256": None},
        "argv": ["makeblastdb", "-in", "/retained/source"], "native_paths": ["/retained/tiny"],
        "inputs": [occurrence("source", role="sequence_input", direction="input", fmt="fasta")],
        "outputs": outputs, "dependencies": [], "inventory_complete": True,
        "native_metadata": [], "detail": {k: op["parameters"][k] for k in (
            "input_type", "database_format_version", "parse_seqids", "hash_index", "taxid",
            "taxid_map_occurrence_id", "mask_occurrence_ids")},
        "compatibility": "unverified", "checks": [], "failures": []}


def prepared_manifest():
    artifacts = artifact_set()
    receipt = {"path": "/retained/receipt.json", "sha256": "a" * 64, "size_bytes": 2, "artifact_ref": None}
    return {"version": "native_blast_standard_prepared_database_manifest_v1", "database_key": "tiny",
        "kind": "blast_nucleotide_sequence", "identity": artifacts["identity"],
        "native_paths": artifacts["native_paths"],
        "files": [{"path": r["native_path"], "sha256": r["sha256"], "size_bytes": r["size_bytes"]}
                  for r in artifacts["outputs"]],
        "preparation": {"method": "makeblastdb", "preparation_type": "sequence_database",
            "software": artifacts["software"], "argv": artifacts["argv"],
            "source": artifacts["identity"]["source"], "input_manifest": None, "receipt": receipt},
        "metadata_manifests": [], "access": {"mode": "prepared_local", "offline_configuration": None},
        "inventory_complete": True}


def assert_invalid(kind, value, code=None):
    with pytest.raises(ContractError, match="^blast_utility_" + (code or "")):
        validate_blast_utility_record(kind, value)


def test_exported_schemas_are_closed_valid_json_schemas():
    assert set(SCHEMAS) == {"ArtifactOccurrence", "NativeOutcome", "UtilityFailure", "ValidationObservation",
        "DatabaseBinding", "NativeField", "Operation", "SequenceExtraction", "DatabaseInspection",
        "DatabaseIntegrity", "DatabaseArtifactSet", "PreparedDatabaseProjection",
        "PreparationDocument", "ParameterObservation", "MaterializationReceipt",
        "VDBUtilityContext", "VDBMember"}

    def object_branches(schema):
        if "anyOf" in schema:
            for branch in schema["anyOf"]:
                yield from object_branches(branch)
        else:
            yield schema

    for schema in SCHEMAS.values():
        jsonschema.Draft202012Validator.check_schema(schema)
        for branch in object_branches(schema):
            assert branch["type"] == "object"
            assert branch["additionalProperties"] is False
            assert set(branch["required"]) == set(branch["properties"])


@pytest.mark.parametrize("factory", [extraction, inspection, integrity, artifact_set])
def test_result_round_trip_is_detached_and_saved_only(factory):
    original = factory()
    returned = validate_blast_utility_result(original)
    assert returned == original
    assert returned is not original and returned["operation"] is not original["operation"]
    restored = json.loads(json.dumps(returned, allow_nan=False))
    assert validate_blast_utility_result(restored) == original
    returned["operation"]["molecule"] = "protein"
    assert original["operation"]["molecule"] == "dna"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), (1, 2), {1: "not-string"}, b"bytes"])
def test_rejects_non_json_and_nonfinite_values_before_shape_validation(bad):
    value = occurrence()
    value["unexpected"] = bad
    assert_invalid("ArtifactOccurrence", value, "finite_json_required")


def test_rejects_cycles_but_detaches_repeated_acyclic_objects():
    value = occurrence()
    value["cycle"] = value
    assert_invalid("ArtifactOccurrence", value, "finite_json_required")
    data = artifact_set()
    shared = {"name": "same", "version": None, "executable_sha256": None}
    data["software"] = shared
    result = validate_blast_utility_record("DatabaseArtifactSet", data)
    assert result["software"] is not shared


@pytest.mark.parametrize("key,bad", [("ordinal", True), ("size_bytes", -1), ("size_bytes", 1.0),
    ("sha256", "A" * 64), ("sha256", "0" * 63), ("direction", "both"),
    ("native_path", "/retained/../outside"), ("native_path", "/retained//out"),
    ("native_path", "/retained/./out"), ("native_path", "relative"), ("artifact_ref", "")])
def test_occurrence_schema_and_path_rejections(key, bad):
    value = occurrence(); value[key] = bad
    assert_invalid("ArtifactOccurrence", value)


def test_every_key_required_and_extra_fields_rejected():
    value = occurrence()
    for key in value:
        omitted = deepcopy(value); omitted.pop(key)
        assert_invalid("ArtifactOccurrence", omitted, "schema_invalid")
    assert_invalid("ArtifactOccurrence", {**value, "confidence": 1.0}, "schema_invalid")


def test_same_bytes_are_distinct_occurrences_not_duplicate_identities():
    value = artifact_set()
    another = deepcopy(value["outputs"][0]); another["occurrence_id"] = "same-bytes-second-occurrence"
    another["native_path"] = "/retained/tiny.extra"
    value["outputs"].append(another)
    saved = validate_blast_utility_record("DatabaseArtifactSet", value)
    assert saved["outputs"][-1]["sha256"] == saved["outputs"][0]["sha256"]
    value["outputs"][-1]["occurrence_id"] = value["outputs"][0]["occurrence_id"]
    assert_invalid("DatabaseArtifactSet", value, "duplicate_occurrence_identity")


@pytest.mark.parametrize("updates", [dict(started=False), dict(returncode=1), dict(writer_closed=False),
    dict(state="failed"), dict(state="incomplete"), dict(returncode=True)])
def test_native_outcome_contradictions(updates):
    assert_invalid("NativeOutcome", outcome(**updates))


def test_returncode_zero_does_not_claim_captured_inventory():
    value = outcome(inventory_complete=False)
    assert validate_blast_utility_record("NativeOutcome", value) == value
    before_start = outcome(started=False, returncode=None, state="failed", writer_closed=False, inventory_complete=False)
    assert validate_blast_utility_record("NativeOutcome", before_start) == before_start


@pytest.mark.parametrize("mode", ["create_sequence_database", "extract_sequences", "info", "metadata", "integrity"])
def test_exact_selected_operation_variants(mode):
    value = operation(mode)
    assert validate_blast_utility_operation(value) == value
    value["parameters"]["implicit_default"] = 1
    assert_invalid("Operation", value, "schema_invalid")


@pytest.mark.parametrize("selector", ["all", "ALL", "A,B", "A B", "A\tB", "A\x00B", "A\x7fB"])
def test_specific_entry_selection_cannot_expand_to_another_population(selector):
    assert_invalid("Operation", operation(selectors=[{"ordinal": 0, "value": selector}]), "selector_value")


def test_duplicate_requested_values_preserve_distinct_ordinals():
    value = operation(selectors=[{"ordinal": 0, "value": "ALPHA"}, {"ordinal": 1, "value": "ALPHA"}])
    assert len(validate_blast_utility_operation(value)["parameters"]["selectors"]) == 2
    value["parameters"]["selectors"][1]["ordinal"] = 0
    assert_invalid("Operation", value, "selector_ordinals")


def test_operation_cross_field_constraints():
    assert_invalid("Operation", operation(molecule="protein", strand="minus"), "protein_strand")
    assert_invalid("Operation", operation(get_dups=True, target_only=True), "extraction_option_conflict")
    assert_invalid("Operation", operation(range={"start_1based": 4, "end_1based": 3}), "range_order")
    assert_invalid("Operation", operation("integrity", random_count=0), "integrity_sampling_conflict")
    assert_invalid("Operation", operation("create_sequence_database", output_prefix="../tiny"))
    value = operation("create_sequence_database", taxid=1, taxid_map_occurrence_id="map")
    value["input_occurrence_ids"].append("map")
    assert_invalid("Operation", value, "taxid_map_exclusive")
    value["parameters"]["taxid"] = None
    value["parameters"]["parse_seqids"] = False
    assert_invalid("Operation", value, "taxid_map_parse_seqids")


@pytest.mark.parametrize("updates", [dict(kind="blast_protein_sequence"), dict(molecule="unknown"),
    dict(native_paths=["/db/tiny", "/db/tiny"]), dict(occurrence_ids=["same", "same"])])
def test_database_binding_relationships(updates):
    assert_invalid("DatabaseBinding", {**binding(), **updates})


@pytest.mark.parametrize("name,value,unit", [
    ("database_title", "Native title", "text"), ("database_created_at_native", "Oct 1, 2026", "text"),
    ("database_format_version", 5, "version"), ("database_sequence_count", 0, "sequences"),
    ("database_residue_count", 14, "nt"), ("database_residue_count", 7, "aa"),
    ("database_residue_count", 7, "symbols"), ("database_bytes", 4096, "bytes"),
    ("database_file_names", ["tiny.nhr", "tiny.nin"], "paths"),
    ("database_volume_names", ["tiny.00", "tiny.01"], "paths")])
def test_native_field_meanings_and_units(name, value, unit):
    row = field(field_name=name, value=value, unit=unit)
    assert validate_blast_utility_record("NativeField", row) == row


@pytest.mark.parametrize("updates", [dict(value=True), dict(value=2.0), dict(value=-1), dict(unit="aa"),
    dict(value=None), dict(missing_reason="native_field_absent"),
    dict(line_number=None), dict(json_pointer="not/a/pointer"), dict(json_pointer="/bad~2")])
def test_native_field_rejects_unit_type_and_missing_source_conflicts(updates):
    assert_invalid("NativeField", field(**updates))


def test_native_field_absence_zero_and_approximation_are_distinct():
    zero = field(value=0, native_lexeme="0")
    absent = field(value=None, native_lexeme=None, missing_reason="native_field_absent")
    approximate = field(value=1000, native_lexeme="1,000", value_basis="native_reported_approximate")
    for value in (zero, absent, approximate):
        assert validate_blast_utility_record("NativeField", value) == value
    root_pointer = field(line_number=None, json_pointer="")
    assert validate_blast_utility_record("NativeField", root_pointer) == root_pointer


def test_parse_check_cannot_claim_native_integrity():
    assert_invalid("ValidationObservation", observation(name="native_integrity"), "integrity_method")
    assert_invalid("ValidationObservation", observation(status="unknown"), "observation_reason")
    assert_invalid("ValidationObservation", observation(method="native_full_check"), "integrity_method")


def test_original_native_row_identity_survives_filtered_rows_and_exact_duplicates():
    value = extraction()
    value["operation"]["parameters"]["selectors"].append({"ordinal": 1, "value": "ALPHA"})
    value["records"][0]["matched_selector_ordinals"] = [0, 1]
    saved = validate_blast_utility_result(value)
    assert saved["records"][0]["record_key"] == "out#/records/2"
    assert saved["records"][0]["line_number"] == 4
    assert saved["records"][0]["matched_selector_ordinals"] == [0, 1]
    value["records"][0]["matched_selector_ordinals"] = [0]
    assert_invalid("SequenceExtraction", value, "exact_selector_association")


def test_explicit_alias_preserves_its_distinct_basis_and_all_exact_matches():
    value = extraction()
    value["operation"]["parameters"]["selectors"].append({"ordinal": 1, "value": "my-alias"})
    row = value["records"][0]
    row["association"] = "explicit"; row["matched_selector_ordinals"] = [0, 1]
    assert validate_blast_utility_result(value)["records"][0]["association"] == "explicit"
    row["matched_selector_ordinals"] = [1]
    assert_invalid("SequenceExtraction", value, "supplied_binding_conflict")


def test_repeated_native_oid_does_not_erase_original_row_occurrences():
    value = extraction()
    repeated = deepcopy(value["records"][0])
    repeated.update(record_key="out#/records/9", native_row_ordinal=9, line_number=12)
    value["records"].append(repeated)
    saved = validate_blast_utility_result(value)
    assert [r["native_oid"] for r in saved["records"]] == [7, 7]
    assert [r["native_row_ordinal"] for r in saved["records"]] == [2, 9]


def test_missing_selectors_and_unexpected_rows_cannot_be_hidden():
    value = extraction()
    value["records"][0]["association"] = "unresolved"
    value["records"][0]["native_identifier"] = "OTHER"
    value["records"][0]["native_accession"] = None
    value["records"][0]["matched_selector_ordinals"] = []
    value["missing_selector_ordinals"] = [0]
    value["unexpected_record_keys"] = ["out#/records/2"]
    value["population_completeness"] = "partial_selection"
    assert validate_blast_utility_result(value) == value
    value["missing_selector_ordinals"] = []
    assert_invalid("SequenceExtraction", value, "missing_selector_population")


def test_contradictory_native_length_is_preserved_with_unavailable_derived_fields():
    value = extraction(); row = value["records"][0]
    row["native_reported_length"] = 17
    assert_invalid("SequenceExtraction", value, "native_length_unqualified")
    row["returned_symbol_count"] = None; row["effective_range"] = None
    row["completeness"] = "partial"
    row["failures"] = [failure("sequence_length_conflict", record_key=row["record_key"], line_number=4)]
    value["population_completeness"] = "partial_selection"
    saved = validate_blast_utility_result(value)
    assert saved["records"][0]["native_reported_length"] == 17
    assert saved["records"][0]["normalized_sequence"] == "ACGT"


def test_native_symbol_errors_are_qualified_partial_data():
    value = extraction(); row = value["records"][0]
    row["original_sequence"] = "AC?T"; row["normalized_sequence"] = "AC?T"
    assert_invalid("SequenceExtraction", value, "returned_sequence_symbols")
    row["returned_symbol_count"] = None; row["effective_range"] = None
    row["completeness"] = "partial"
    row["failures"] = [failure("sequence_symbol_invalid", record_key=row["record_key"], line_number=4)]
    value["population_completeness"] = "partial_selection"
    assert validate_blast_utility_result(value)["records"][0]["original_sequence"] == "AC?T"


def test_protein_internal_stop_semantics_reuse_existing_sequence_parser():
    value = extraction(); row = value["records"][0]
    value["operation"]["molecule"] = "protein"; value["database_binding"] = binding(molecule="protein")
    row.update(molecule="protein", original_sequence="m*kz", normalized_sequence="M*KZ")
    assert validate_blast_utility_result(value)["records"][0]["returned_symbol_count"] == 4


def test_returned_fragment_does_not_replace_native_full_length():
    value = extraction(); row = value["records"][0]
    requested = {"start_1based": 3, "end_1based": 6}
    value["operation"]["parameters"]["range"] = requested
    row.update(native_reported_length=20, requested_range=requested,
        effective_range={"start_0based": 2, "end_exclusive": 6, "strand": "plus"})
    saved = validate_blast_utility_result(value)["records"][0]
    assert (saved["native_reported_length"], saved["returned_symbol_count"]) == (20, 4)
    row["effective_range"]["end_exclusive"] = 8
    assert_invalid("SequenceExtraction", value, "effective_range")


@pytest.mark.parametrize("strand", ["plus", "minus"])
def test_forged_effective_origin_cannot_preserve_length_but_shift_requested_range(strand):
    value = extraction(); row = value["records"][0]
    requested = {"start_1based": 3, "end_1based": 6}
    value["operation"]["parameters"].update(range=requested, strand=strand)
    row.update(native_reported_length=20, requested_range=requested,
        effective_range={"start_0based": 0, "end_exclusive": 4, "strand": strand})
    assert_invalid("SequenceExtraction", value, "effective_range_origin")


def test_effective_end_must_equal_observed_full_length_clipping():
    value = extraction(); row = value["records"][0]
    requested = {"start_1based": 3, "end_1based": 30}
    value["operation"]["parameters"]["range"] = requested
    row.update(native_reported_length=6, requested_range=requested,
        effective_range={"start_0based": 2, "end_exclusive": 6, "strand": "plus"})
    assert validate_blast_utility_result(value)["records"][0]["effective_range"]["end_exclusive"] == 6
    row.update(original_sequence="acg", normalized_sequence="ACG", returned_symbol_count=3,
        effective_range={"start_0based": 2, "end_exclusive": 5, "strand": "plus"})
    assert_invalid("SequenceExtraction", value, "effective_range_end")


def test_malformed_skipped_row_failure_keeps_original_locator():
    value = extraction()
    value["failures"] = [failure(record_key="out#/records/1", line_number=2)]
    value["population_completeness"] = "partial_selection"
    assert validate_blast_utility_result(value)["failures"][0]["record_key"] == "out#/records/1"
    value["failures"][0]["record_key"] = "other#/records/1"
    assert_invalid("SequenceExtraction", value, "failure_record_reference")


@pytest.mark.parametrize("stage,code", [("parse", "native_row_invalid"),
                                       ("association", "record_association_unresolved")])
def test_complete_selection_cannot_hide_retained_parse_or_association_failures(stage, code):
    value = extraction()
    value["failures"] = [failure(code, stage=stage)]
    assert_invalid("SequenceExtraction", value, "complete_selection_failures")


@pytest.mark.parametrize("target", ["evidence", "subject", "native_field", "failure"])
def test_dangling_joins_rejected(target):
    value = inspection()
    if target == "evidence": value["checks"][0]["evidence_occurrence_ids"] = ["ghost"]
    if target == "subject": value["checks"][0]["subject_refs"] = ["ghost"]
    if target == "native_field": value["native_fields"][0]["occurrence_id"] = "ghost"
    if target == "failure": value["failures"] = [failure(occurrence_id="ghost")]
    assert_invalid("DatabaseInspection", value)


def test_result_input_occurrence_reference_must_be_in_explicit_database_binding():
    value = inspection()
    value["operation"]["input_occurrence_ids"] = ["unbound-input"]
    assert_invalid("DatabaseInspection", value, "result_input_reference")
    value["database_binding"]["occurrence_ids"].append("unbound-input")
    assert validate_blast_utility_result(value) == value


def test_conflicting_native_metadata_are_retained_as_distinct_observations():
    value = inspection()
    value["native_fields"].append(field(value=3, native_lexeme="3", line_number=2))
    value["completeness"] = "partial"
    value["failures"] = [failure("database_metadata_conflict", line_number=2)]
    assert [f["value"] for f in validate_blast_utility_result(value)["native_fields"]] == [2, 3]


def test_approximate_and_exact_native_counts_keep_separate_meanings():
    value = inspection()
    value["native_fields"] = [field(value=1000, native_lexeme="1000",
        value_basis="native_reported_approximate"), field(value=1001, native_lexeme="1001", line_number=2)]
    rows = validate_blast_utility_result(value)["native_fields"]
    assert [row["value"] for row in rows] == [1000, 1001]
    assert [row["value_basis"] for row in rows] == ["native_reported_approximate", "native_reported_exact"]


def test_zero_exit_and_full_request_cannot_invent_full_integrity():
    value = integrity()
    assert validate_blast_utility_result(value)["scope"] == "unknown"
    value["scope"] = "all_sequences"
    assert_invalid("DatabaseIntegrity", value, "integrity_full_evidence")


def test_observed_full_and_sampled_checks_keep_distinct_scope():
    full = integrity(); full["scope"] = "all_sequences"
    full["diagnostics"] = [{"occurrence_id": "out", "line_number": 1, "category": "check_pass", "native_oid": None}]
    full["checks"] = [observation(name="native_integrity", method="native_full_check")]
    full["observed_checked_count"] = full["observed_population_count"] = 10
    assert validate_blast_utility_result(full)["scope"] == "all_sequences"
    sample = deepcopy(full); sample["scope"] = "selected_sample"
    sample["operation"] = operation("integrity", full=False, random_count=2)
    sample["checks"][0]["method"] = "native_sample_check"
    sample["observed_checked_count"] = 2; sample["observed_sampled_oids"] = [1, 8]
    assert validate_blast_utility_result(sample)["observed_population_count"] == 10
    sample["checks"][0]["method"] = "native_full_check"
    assert_invalid("DatabaseIntegrity", sample, "integrity_full_scope")


def test_nonzero_execution_failure_does_not_assert_corrupt_sequences():
    value = integrity()
    value["original_outcome"] = outcome(state="failed", returncode=1)
    value["failures"] = [failure("native_nonzero_exit", stage="native", native_returncode=1)]
    value["diagnostics"] = [{"occurrence_id": "out", "line_number": 1,
        "category": "execution_failure", "native_oid": None}]
    saved = validate_blast_utility_result(value)
    assert saved["scope"] == "unknown" and saved["observed_checked_count"] is None
    value["failures"][0]["native_returncode"] = 2
    assert_invalid("DatabaseIntegrity", value, "failure_outcome_conflict")


@pytest.mark.parametrize("version", [4, 5])
def test_database_version_and_all_supplied_output_files_retained(version):
    value = artifact_set(version)
    saved = validate_blast_utility_result(value)
    assert saved["detail"]["database_format_version"] == version
    assert len(saved["outputs"]) == 7
    assert saved["compatibility"] == "unverified"
    value["detail"]["database_format_version"] = 4 if version == 5 else 5
    assert_invalid("DatabaseArtifactSet", value, "artifact_set_detail")


def test_preparation_dependencies_join_explicit_roles_and_original_inputs():
    value = artifact_set()
    op = value["operation"]
    op["input_occurrence_ids"].extend(["taxmap", "mask"])
    op["parameters"].update(taxid_map_occurrence_id="taxmap", mask_occurrence_ids=["mask"])
    value["detail"].update(taxid_map_occurrence_id="taxmap", mask_occurrence_ids=["mask"])
    value["inputs"].extend([occurrence("taxmap", role="taxid_map", direction="input"),
        occurrence("mask", role="mask_input", direction="input", fmt="maskinfo_xml")])
    value["dependencies"] = [{"role": "taxid_map", "occurrence_id": "taxmap"},
                             {"role": "mask_input", "occurrence_id": "mask"}]
    assert validate_blast_utility_result(value)["dependencies"] == value["dependencies"]
    value["dependencies"][1]["occurrence_id"] = "taxmap"
    assert_invalid("DatabaseArtifactSet", value, "artifact_set_dependency_population")


def test_partial_inventory_is_preserved_but_cannot_claim_complete_capture():
    value = artifact_set()
    value["original_outcome"] = outcome(state="incomplete", writer_closed=False, inventory_complete=False)
    assert_invalid("DatabaseArtifactSet", value, "artifact_set_inventory_completeness")
    value["inventory_complete"] = False
    value["outputs"][0]["completeness"] = "partial"
    value["failures"] = [failure("output_inventory_incomplete", stage="capture", occurrence_id=None, line_number=None)]
    assert len(validate_blast_utility_result(value)["outputs"]) == 7


def test_database_compatibility_requires_full_native_evidence():
    value = artifact_set(); value["compatibility"] = "validated"
    assert_invalid("DatabaseArtifactSet", value, "database_compatibility_evidence")
    key = value["outputs"][0]["occurrence_id"]
    value["checks"] = [observation(name="native_integrity", method="native_sample_check",
        subject_refs=["tiny"], evidence_occurrence_ids=[key])]
    assert_invalid("DatabaseArtifactSet", value, "database_compatibility_evidence")
    value["checks"][0]["method"] = "native_full_check"
    assert_invalid("DatabaseArtifactSet", value, "database_compatibility_evidence")
    diagnostic = occurrence("integrity-proof", role="diagnostics", fmt="blastdbcheck_text")
    value["outputs"].append(diagnostic)
    value["checks"][0]["evidence_occurrence_ids"] = [diagnostic["occurrence_id"]]
    assert validate_blast_utility_result(value)["compatibility"] == "validated"


def test_protein_residue_unit_conflict_needs_qualification():
    value = inspection()
    value["operation"]["molecule"] = "protein"
    value["database_binding"] = binding(molecule="protein")
    value["native_fields"] = [field(field_name="database_residue_count", value=22, unit="nt")]
    assert_invalid("DatabaseInspection", value, "native_metadata_conflict_unqualified")
    value["failures"] = [failure("database_kind_conflict")]
    value["completeness"] = "partial"
    assert validate_blast_utility_result(value)["native_fields"][0]["unit"] == "nt"


def test_execution_failure_diagnostic_cannot_be_relabeled_as_integrity_failure():
    value = integrity()
    value["original_outcome"] = outcome(state="failed", returncode=1)
    value["scope"] = "all_sequences"
    value["diagnostics"] = [{"occurrence_id": "out", "line_number": 1,
        "category": "execution_failure", "native_oid": None}]
    value["checks"] = [observation(name="native_integrity", method="native_full_check", status="fail",
        reason="native_nonzero_exit")]
    assert_invalid("DatabaseIntegrity", value, "integrity_observation_evidence")


def test_early_full_check_failure_preserves_unknown_observed_scope():
    value = integrity()
    value["original_outcome"] = outcome(state="failed", returncode=1)
    value["diagnostics"] = [{"occurrence_id": "out", "line_number": 1,
        "category": "check_failure", "native_oid": 0}]
    value["checks"] = [observation(name="native_integrity", method="native_full_check", status="fail",
        reason="native_integrity_failure")]
    value["failures"] = [failure("native_integrity_failure", stage="validation")]
    saved = validate_blast_utility_result(value)
    assert saved["scope"] == "unknown" and saved["observed_checked_count"] is None


def test_prepared_projection_uses_standard_manifest_relationship_validation():
    value = {"status": "available", "manifest": prepared_manifest(), "failures": []}
    assert validate_blast_utility_record("PreparedDatabaseProjection", value) == value
    value["manifest"]["native_paths"] = ["/retained/not-in-inventory"]
    assert_invalid("PreparedDatabaseProjection", value, "database_native_path_not_in_inventory")


def test_unavailable_projection_requires_typed_reason_and_no_manifest():
    value = {"status": "unavailable", "manifest": None,
        "failures": [failure("preparation_not_successful", stage="projection", occurrence_id=None, line_number=None)]}
    assert validate_blast_utility_record("PreparedDatabaseProjection", value) == value
    value["failures"] = []
    assert_invalid("PreparedDatabaseProjection", value, "unavailable_projection_reason")


@pytest.mark.parametrize("value,code", [({}, "unknown_result_version"),
    ({"version": "blast_utility_operation_v1"}, "unknown_result_version"),
    ({"version": "blast_database_inspection_v2"}, "schema_invalid"),
    ({"version": "blast_database_inspection_v999"}, "unknown_result_version"),
    ({"version": []}, "unknown_result_version"), ([], "unknown_result_version")])
def test_result_dispatch_only_admits_exact_result_versions(value, code):
    with pytest.raises(ContractError, match="^blast_utility_" + code + "$"):
        validate_blast_utility_result(value)
