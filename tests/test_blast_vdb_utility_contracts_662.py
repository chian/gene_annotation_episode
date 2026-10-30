"""Pure shared-core checks with explicitly controlled fixtures, never native work."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.blast_utility_contracts import (
    SCHEMAS, blast_utility_schema_for_version, blast_utility_result_version_for_operation,
    validate_blast_utility_operation, validate_blast_utility_result,
    validate_blast_utility_record as core,
)
from gene_annotation_episode.blast_database_extraction import parse_blastdbcmd_sequences
from gene_annotation_episode.domain import ContractError


EVIDENCE = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_vdb_shared_core_2026-10-28_662"
LEGACY_VERSIONS = (
    "blast_utility_operation_v1", "blast_utility_operation_v2", "blast_sequence_extraction_v1",
    "blast_database_inspection_v1", "blast_database_inspection_v2", "blast_database_integrity_v1",
    "blast_database_artifact_set_v1", "blast_database_artifact_set_v2", "blast_preparation_document_v1",
)


def _legacy_snapshot():
    from test_blast_database_extraction_626 import context, occurrence
    from test_blast_preparation_contracts_647 import operation, MODES
    from test_blast_preparation_population_647 import (
        occurrence as prep_occurrence, common, populate, outcome,
    )
    from gene_annotation_episode.blast_preparation_inputs import (
        parse_blast_alias_document, parse_blast_seqid_list_info, parse_blast_aliastool_diagnostics,
    )
    classic = []
    for raw, ctx in [
        (b"0\tlcl|seqA\tseqA\t4\tacgt\n", context()),
        (b"0\tlcl|seqA\tseqA\t4\tACGT\nmalformed\n2\tlcl|seqB\tseqB\t3\tAUN\n", context(("seqA", "seqB"))),
        (b"0\tlcl|seqA\tseqA\t4\tACG\n", context()),
        (b"0\tlcl|seqA\tseqA\t4\tACGT\n", context(("seqA", "seqA", "absent"), returncode=1)),
        (b"0\tlcl|seqA\tseqA\t12\tCGTACG\n", context(selected_range={"start_1based": 2, "end_1based": 7})),
        (b"0\tlcl|seqA\tseqA\t4\tM*AA\n", context(molecule="protein")),
    ]:
        classic.append(parse_blastdbcmd_sequences(raw, occurrence=occurrence(raw), **ctx))
    docs = []
    for parser, raw, fmt in [
        (parse_blast_alias_document, b"TITLE controlled\nDBLIST /source/db /source/db\nNSEQ 2\nLENGTH 13\n", "blast_alias_text"),
        (parse_blast_seqid_list_info, b"Num of Ids: 2\nTitle: controlled\nCreate Date: retained\n", "blast_seqid_list_info_text"),
    ]:
        docs.append(parser(raw, occurrence=prep_occurrence("doc", "stdout", raw, direction="output", fmt=fmt)))
    raw = b"Converted 3 GIs into binary GI file\n"
    source = prep_occurrence("ids", "identifier_list", b"9\n3\n9\nnot-a-gi\n")
    stderr = prep_occurrence("stderr", "stderr", raw, direction="output", path="/attempt/stderr")
    binary = prep_occurrence("binary", "identifier_list", b"synthetic-binary", direction="output",
        fmt="gi_list_binary", path="/attempt/out/ids.gil")
    doc = parse_blast_aliastool_diagnostics(raw, occurrence=stderr)
    args = common(operation("convert_gi_list"), inputs=[source], outputs=[binary, stderr], documents=[doc])
    preparations = [populate(**args), populate(**{**args, "outcome": outcome(2)})]
    return {
        "fixture_basis": "controlled hand-authored bytes; no native execution",
        "schemas": {v: blast_utility_schema_for_version(v) for v in LEGACY_VERSIONS},
        "classic_results": classic, "preparation_documents": docs, "preparation_results": preparations,
        "preparation_operations": [validate_blast_utility_operation(operation(mode)) for mode in MODES],
        "preparation_result_versions": [blast_utility_result_version_for_operation(operation(mode)) for mode in MODES],
    }


def test_capture_or_compare_legacy_baseline():
    snapshot = _legacy_snapshot()
    attempt = os.environ.get("HMMER529_ATTEMPT")
    if os.environ.get("HMMER_NATIVE_ORACLE_CORE662_BASELINE") == "1":
        assert attempt
        destination = Path(attempt) / "temporary/legacy_before.json"
        assert not destination.exists()
        destination.write_text(json.dumps(snapshot, indent=2) + "\n")
    else:
        baseline = json.loads((EVIDENCE / "legacy_before.json").read_text())
        assert snapshot == baseline
        if attempt:
            (Path(attempt) / "temporary/legacy_after.json").write_text(json.dumps(snapshot, indent=2) + "\n")


def occurrence(oid, *, role="stdout", fmt="text", direction="output", raw=b"controlled"):
    return {"occurrence_id": oid, "direction": direction, "role": role, "ordinal": 0,
        "artifact_ref": "artifact_" + hashlib.sha256(raw).hexdigest(),
        "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
        "native_format": fmt, "completeness": "complete", "native_path": None}


def operation(variant="entry", database_source="db"):
    extract = variant in {"entry", "entry_batch", "all_native_sequences", "all_references"}
    selection = ({"kind": "entries", "source": variant,
        "selectors": [{"ordinal": 0, "value": "readA"}, {"ordinal": 1, "value": "readA"}],
        "batch_occurrence_id": "batch" if variant == "entry_batch" else None}
        if variant in {"entry", "entry_batch"} else {"kind": variant} if extract else None)
    ids = (["db-list"] if database_source == "dbs_file" else []) + (["batch"] if variant == "entry_batch" else [])
    return {"version": "blast_utility_operation_v3", "program": "blast_vdb_cmd",
        "mode": "extract_sequences" if extract else variant, "input_occurrence_ids": ids,
        "database_key": "selected", "molecule": "dna", "parameters": {
            "database_selection": {"source": database_source, "inputs": [
                {"ordinal": i, "kind": "path", "value": "/fixture/source.vdb",
                 "binding_native_path": "/fixture/source.vdb", "list_entry_ordinal": i if database_source == "dbs_file" else None}
                for i in range(2)], "list_occurrence_id": "db-list" if database_source == "dbs_file" else None},
            "line_length": 80, "selection": selection, "include_filtered_reads": False,
            "output_format": "blast_vdb_cmd_table_v1" if extract else "blast_vdb_info_text_v1" if variant == "info" else "blast_vdb_paths_text_v1"}}


def binding(key="selected", kind="vdb", path="/fixture/source.vdb"):
    return {"database_key": key, "kind": kind, "molecule": "dna",
        "identity": {"namespace": "controlled", "value": key, "version": None, "release": None},
        "source_ref": "captured:database-context", "native_paths": [path],
        "occurrence_ids": [key + "-file"], "inventory_complete": True}


def provenance(pointer="/supplied"):
    # Source references deliberately are not occurrence IDs. Authentication of
    # this selected source's contents belongs to the captured-context worker.
    return {"source_ref": "controlled:metadata", "pointer": pointer}


def identity(value="member"):
    return {"namespace": "controlled", "value": value, "version": None}


def context(op):
    p = op["parameters"]
    selection = p["selection"]
    return {"version": "blast_vdb_utility_context_v1", "source_inputs": [
        {"ordinal": row["ordinal"], "selected_input": {"kind": row["kind"], "value": row["value"]},
         "binding_native_path": row["binding_native_path"], "dataset_key": "dataset", "dataset_type": "csra",
         "snapshot": {"release": None, "snapshot_id": None, "manifest_sha256": None},
         "run_identifiers": [], "source": provenance()} for row in p["database_selection"]["inputs"]],
        "selection_kind": None if selection is None else selection["kind"],
        "include_filtered_reads": p["include_filtered_reads"], "member_bindings": [],
        "sample_links": [], "dependency_database_bindings": [], "declared_dependencies": [],
        "entry_identifier_bindings": [{"selector_ordinal": s["ordinal"],
            "identifier": {"namespace": "blast_vdb_cmd.entry", "value": s["value"], "version": None},
            "source": provenance("/selectors/" + str(s["ordinal"]))}
            for s in selection["selectors"]] if selection and selection["kind"] == "entries" else []}


def operation_inputs(op):
    return [occurrence(oid, role="entry_batch" if oid == "batch" else "database_list", direction="input")
            for oid in op["input_occurrence_ids"]]


def result(variant="entry", database_source="db"):
    op = operation(variant, database_source)
    common = {"operation": op, "database_binding": binding(), "vdb_context": context(op),
        "operation_input_occurrences": operation_inputs(op),
        "original_outcome": {"started": True, "returncode": 0, "state": "succeeded",
            "writer_closed": True, "inventory_complete": True},
        "output_occurrence": occurrence("out", fmt=op["parameters"]["output_format"]),
        "stderr_occurrence": occurrence("err", role="stderr", raw=b""), "checks": [], "failures": []}
    if op["mode"] == "extract_sequences":
        selected = variant in {"entry", "entry_batch"}
        row = {"record_key": "out#/records/0", "native_row_ordinal": 0, "line_number": 1,
            "matched_selector_ordinals": [0, 1] if selected else [],
            "association": "exact" if selected else "not_applicable", "native_oid": None,
            "native_identifier": "readA", "native_accession": "readA", "native_reported_length": 4,
            "native_length_basis": "returned_sequence", "original_sequence": "acgt",
            "normalized_sequence": "ACGT", "returned_symbol_count": 4, "molecule": "dna",
            "requested_range": None, "effective_range": None, "completeness": "complete",
            "checks": [], "failures": [], "vdb_member": None}
        return {**common, "version": "blast_sequence_extraction_v2", "records": [row],
            "missing_selector_ordinals": [], "unexpected_record_keys": [],
            "population_completeness": "complete_selection",
            "scope": {"kind": "selected_entries" if selected else variant}}
    return {**common, "version": "blast_database_inspection_v3", "native_fields": [],
        "path_sections": [], "path_records": [], "completeness": "complete"}


def failure(code, *, oid="out", row=None, line=None, stage="validation", rc=None):
    return {"stage": stage, "code": code, "occurrence_id": oid, "record_key": row,
        "line_number": line, "native_returncode": rc}


def member(kind="read"):
    return {"binding_key": "member-link", "native_identifier": "readA", "dataset_key": "dataset",
        "member_kind": kind, "member_identifier": identity("supplied-member"), "relationship": "catalog_membership",
        "read_identity": {"native_read_name": "supplied-read", "spot_id": None, "read_index": 0,
                          "source": provenance()} if kind == "read" else None,
        "reference_identity": {"identifier": identity("supplied-reference"), "full_length": 19,
            "sequence_sha256": None, "source": provenance()} if kind in {"reference", "wgs_sequence"} else None,
        "sample_key": None, "provenance": provenance()}


@pytest.mark.parametrize("variant", ["entry", "entry_batch", "all_native_sequences", "all_references", "info", "paths", "paths_all"])
@pytest.mark.parametrize("database_source", ["db", "dbs_file"])
def test_exact_variants_versions_order_and_detached_results(variant, database_source):
    from gene_annotation_episode.blast_vdb_utility_contracts import (
        validate_vdb_utility_operation, validate_vdb_utility_context,
        validate_vdb_sequence_extraction, validate_vdb_database_inspection,
    )
    value = result(variant, database_source)
    op = value["operation"]
    assert validate_vdb_utility_operation(op) == validate_blast_utility_operation(op) == op
    assert validate_vdb_utility_context(value["vdb_context"], operation=op,
        database_binding=value["database_binding"], operation_input_occurrences=value["operation_input_occurrences"]) == value["vdb_context"]
    assert blast_utility_result_version_for_operation(op) == value["version"]
    direct = validate_vdb_sequence_extraction if op["mode"] == "extract_sequences" else validate_vdb_database_inspection
    checked = direct(value)
    assert checked == validate_blast_utility_result(value) == value
    checked["vdb_context"]["source_inputs"][0]["dataset_type"] = "unknown"
    assert value["vdb_context"]["source_inputs"][0]["dataset_type"] == "csra"
    assert len(op["parameters"]["database_selection"]["inputs"]) == 2


def test_schema_build_is_detached_and_old_nested_enums_stay_closed():
    from gene_annotation_episode.blast_vdb_utility_contracts import build_vdb_utility_schemas
    from gene_annotation_episode.blast_preparation_contracts import DATABASE_DEPENDENCY_SCHEMA
    old = json.loads((EVIDENCE / "legacy_before.json").read_text())
    for version, schema in old["schemas"].items():
        assert blast_utility_schema_for_version(version) == schema
    base = {**SCHEMAS, "ArtifactOccurrence": deepcopy(old["schemas"]["blast_sequence_extraction_v1"]["properties"]["output_occurrence"]),
        "NativeField": deepcopy(old["schemas"]["blast_database_inspection_v1"]["properties"]["native_fields"]["items"]),
        "SequenceExtraction": old["schemas"]["blast_sequence_extraction_v1"],
        "DatabaseInspection": old["schemas"]["blast_database_inspection_v1"]}
    before = deepcopy(base)
    new = build_vdb_utility_schemas(base)
    assert base == before
    assert new["VDBUtilityContext"]["properties"]["declared_dependencies"]["items"] == DATABASE_DEPENDENCY_SCHEMA
    new["ArtifactOccurrence"]["properties"]["role"]["enum"].append("invented")
    assert base == before
    assert "entry_batch" not in old["schemas"]["blast_sequence_extraction_v1"]["properties"]["output_occurrence"]["properties"]["role"]["enum"]


@pytest.mark.parametrize("edit", [
    lambda v: v.update(program="blastdbcmd"), lambda v: v.update(version="blast_utility_operation_v2"),
    lambda v: v.update(molecule="protein"), lambda v: v["parameters"].update(ref=True),
    lambda v: v["parameters"].update(line_length=True), lambda v: v["parameters"].update(line_length=0),
    lambda v: v["parameters"].update(output_format="fasta"),
    lambda v: v["parameters"]["selection"]["selectors"][0].update(value="all"),
    lambda v: v["parameters"]["selection"]["selectors"][0].update(value="readA,readB"),
    lambda v: v["parameters"]["selection"]["selectors"][0].update(ordinal=1),
    lambda v: v["parameters"]["database_selection"].update(list_occurrence_id="undeclared"),
    lambda v: v["parameters"]["database_selection"]["inputs"][0].update(binding_native_path="relative"),
])
def test_request_contradictions_are_rejected_before_any_execution(edit):
    value = operation()
    edit(value)
    with pytest.raises(ContractError, match="^blast_utility_"):
        validate_blast_utility_operation(value)


@pytest.mark.parametrize("variant", ["all_references", "info", "paths", "paths_all"])
def test_filtered_flag_is_rejected_outside_its_native_views(variant):
    value = operation(variant)
    value["parameters"]["include_filtered_reads"] = True
    with pytest.raises(ContractError):
        validate_blast_utility_operation(value)


def test_input_occurrences_remain_separate_and_cross_binding_is_rejected():
    value = result("entry_batch", "dbs_file")
    assert validate_blast_utility_result(value) == value
    edits = [
        lambda v: v["database_binding"]["occurrence_ids"].append("batch"),
        lambda v: v["operation_input_occurrences"].reverse(),
        lambda v: v["operation_input_occurrences"][1].update(role="database_file"),
        lambda v: v["stderr_occurrence"].update(occurrence_id="out"),
        lambda v: v["vdb_context"]["source_inputs"][0]["selected_input"].update(value="/different"),
        lambda v: v["vdb_context"]["entry_identifier_bindings"][1]["identifier"].update(value="different"),
        lambda v: v["vdb_context"]["source_inputs"][0]["source"].update(pointer="/bad~2pointer"),
    ]
    for edit in edits:
        bad = deepcopy(value); edit(bad)
        with pytest.raises(ContractError): validate_blast_utility_result(bad)
    missing_csra = result("all_references")
    for source in missing_csra["vdb_context"]["source_inputs"]: source["dataset_type"] = "sra"
    with pytest.raises(ContractError, match="csra_input_required"): validate_blast_utility_result(missing_csra)


def test_row_identity_gaps_and_partial_work_are_not_compacted():
    value = result()
    row = deepcopy(value["records"][0])
    row.update(record_key="out#/records/2", native_row_ordinal=2, line_number=3)
    value["records"].append(row)
    value["failures"] = [failure("native_row_invalid", row="out#/records/1", line=2, stage="parse")]
    value["population_completeness"] = "partial_selection"
    checked = validate_blast_utility_result(value)
    assert [r["native_row_ordinal"] for r in checked["records"]] == [0, 2]
    assert all(r["matched_selector_ordinals"] == [0, 1] for r in checked["records"])
    bad = deepcopy(value); bad["records"][1]["record_key"] = "out#/records/1"
    with pytest.raises(ContractError, match="record_identity"): validate_blast_utility_result(bad)


def test_native_omissions_and_all_scope_are_not_replaced_by_inferences():
    for variant in ("all_native_sequences", "all_references"):
        value = result(variant)
        value["records"] = []
        assert validate_blast_utility_result(value)["population_completeness"] == "complete_selection"
    value = result()
    for field, invented in (("native_oid", 0), ("native_length_basis", "full_sequence"),
                           ("requested_range", {"start_1based": 1, "end_1based": 4}),
                           ("association", "not_applicable")):
        bad = deepcopy(value); bad["records"][0][field] = invented
        with pytest.raises(ContractError): validate_blast_utility_result(bad)
    bad = result("all_native_sequences"); bad["records"][0]["association"] = "unresolved"
    with pytest.raises(ContractError): validate_blast_utility_result(bad)
    bad = result("all_native_sequences"); bad["missing_selector_ordinals"] = [0]
    with pytest.raises(ContractError): validate_blast_utility_result(bad)


@pytest.mark.parametrize("original,molecule,expected", [
    ("acgtn", "dna", ("ACGTN", 5)), ("ACGU", "dna", ("ACGU", None)),
    ("A C", "dna", ("A C", None)), ("", "dna", ("", None)),
    ("A?", "dna", ("A?", None)), ("M*AA", "protein", ("M*AA", 4)),
])
def test_one_public_normalization_calculation_preserves_original_semantics(original, molecule, expected):
    from gene_annotation_episode.blast_database_extraction import normalize_blast_utility_sequence_symbols, _sequence_symbols
    assert normalize_blast_utility_sequence_symbols(original, molecule) == _sequence_symbols(original, molecule) == expected


def test_classic_parser_and_vdb_validation_use_the_public_symbol_authority(monkeypatch):
    import gene_annotation_episode.blast_database_extraction as extraction
    from test_blast_database_extraction_626 import context as classic_context, occurrence as classic_occurrence
    calls = []
    original = extraction.normalize_blast_utility_sequence_symbols
    def observe(symbols, molecule):
        calls.append((symbols, molecule))
        return original(symbols, molecule)
    monkeypatch.setattr(extraction, "normalize_blast_utility_sequence_symbols", observe)
    raw = b"0\tlcl|seqA\tseqA\t4\tacgt\n"
    extraction.parse_blastdbcmd_sequences(raw, occurrence=classic_occurrence(raw), **classic_context())
    validate_blast_utility_result(result())
    assert len(calls) >= 2 and set(calls) == {("acgt", "dna")}


def test_native_length_conflict_and_invalid_dna_preserve_symbols_with_null_counts():
    for sequence, native_length, code in (("ACGT", 5, "sequence_length_conflict"), ("ACGU", 4, "sequence_symbol_invalid")):
        value = result()
        row = value["records"][0]
        row.update(original_sequence=sequence, normalized_sequence=sequence,
                   native_reported_length=native_length, returned_symbol_count=None, completeness="partial")
        row["failures"] = [failure(code, row=row["record_key"], line=1)]
        value["failures"] = deepcopy(row["failures"])
        value["population_completeness"] = "partial_selection"
        checked = validate_blast_utility_result(value)
        assert checked["records"][0]["returned_symbol_count"] is None
        assert checked["records"][0]["original_sequence"] == sequence
        bad = deepcopy(value); bad["records"][0]["returned_symbol_count"] = 4
        with pytest.raises(ContractError): validate_blast_utility_result(bad)


def test_members_and_sample_links_require_supplied_unambiguous_relationships():
    value = result()
    link = member()
    value["vdb_context"]["member_bindings"] = [link]
    value["records"][0]["vdb_member"] = deepcopy(link)
    assert validate_blast_utility_result(value)["records"][0]["vdb_member"]["read_identity"]["read_index"] == 0
    bad = deepcopy(value); bad["records"][0]["vdb_member"] = None
    with pytest.raises(ContractError, match="member_record_binding"):
        validate_blast_utility_result(bad)
    for mutate in (
        lambda m: m.update(dataset_key="unselected"),
        lambda m: m.update(native_identifier="different"),
        lambda m: m.update(reference_identity=member("reference")["reference_identity"]),
        lambda m: m.update(sample_key="unbound"),
    ):
        bad = deepcopy(value); mutate(bad["vdb_context"]["member_bindings"][0])
        bad["records"][0]["vdb_member"] = deepcopy(bad["vdb_context"]["member_bindings"][0])
        with pytest.raises(ContractError): validate_blast_utility_result(bad)
    sample = {"dataset_key": "dataset", "link": {"sample_key": "sample", "sample_identifier": identity("sampleA"),
        "biosample_identifier": None, "source": provenance()}}
    value["vdb_context"]["sample_links"] = [sample, deepcopy(sample)]
    value["vdb_context"]["member_bindings"][0]["sample_key"] = "sample"
    value["records"][0]["vdb_member"]["sample_key"] = "sample"
    assert validate_blast_utility_result(value) == value
    value["vdb_context"]["sample_links"][1]["link"]["sample_identifier"]["value"] = "sampleB"
    with pytest.raises(ContractError, match="member_sample_link"): validate_blast_utility_result(value)
    value["vdb_context"]["member_bindings"][0]["sample_key"] = None
    value["records"][0]["vdb_member"]["sample_key"] = None
    assert len(validate_blast_utility_result(value)["vdb_context"]["sample_links"]) == 2
    conflicting = deepcopy(link); conflicting["binding_key"] = "other-link"
    conflicting["member_identifier"] = identity("different-member")
    value["vdb_context"]["member_bindings"].append(conflicting)
    with pytest.raises(ContractError, match="member_record_binding"): validate_blast_utility_result(value)
    value["records"][0]["vdb_member"] = None
    with pytest.raises(ContractError, match="member_conflict_unqualified"):
        validate_blast_utility_result(value)
    row = value["records"][0]
    row["failures"].append(failure("supplied_binding_conflict", row=row["record_key"], line=1, stage="association"))
    row["completeness"] = "partial"
    value["population_completeness"] = "partial_selection"
    assert validate_blast_utility_result(value)["records"][0]["vdb_member"] is None


def test_native_failure_capture_and_located_stderr_remain_separate():
    value = result()
    value["original_outcome"].update(returncode=2, state="failed")
    value["population_completeness"] = "partial_selection"
    value["failures"] = [failure("native_nonzero_exit", oid="err", stage="native", rc=2)]
    checked = validate_blast_utility_result(value)
    assert checked["records"][0]["returned_symbol_count"] == 4
    assert checked["output_occurrence"]["completeness"] == "complete"
    assert not any(f["code"] == "output_inventory_incomplete" for f in checked["failures"])
    bad = deepcopy(value); bad["failures"][0]["occurrence_id"] = "other-attempt-stderr"
    with pytest.raises(ContractError): validate_blast_utility_result(bad)
    value["original_outcome"].update(returncode=0, state="succeeded")
    value["failures"] = [failure("selection_incomplete", oid="err", line=2, stage="native")]
    assert validate_blast_utility_result(value) == value
    value["population_completeness"] = "complete_selection"
    with pytest.raises(ContractError): validate_blast_utility_result(value)


def field(name, value, unit, *, line=1, lexeme=None):
    return {"field_name": name, "value": value, "unit": unit, "value_basis": "native_reported",
        "native_lexeme": str(value) if lexeme is None and value is not None else lexeme,
        "occurrence_id": "out", "line_number": line, "json_pointer": None,
        "missing_reason": "native_field_absent" if value is None else None}


def test_info_populations_zero_missing_and_reported_average_stay_distinct():
    value = result("info")
    value["native_fields"] = [field("vdb_sequence_count", 3, "sequences"),
        field("vdb_total_unclipped_bases", 1001, "nt", line=2, lexeme="1,001"),
        field("vdb_average_sequence_bases", 333, "nt", line=3),
        field("vdb_reference_sequence_count", 0, "sequences", line=4),
        field("vdb_reference_total_bases", None, "nt", line=5)]
    assert validate_blast_utility_result(value) == value
    assert value["native_fields"][2]["value"] == 333  # 1001 / 3 is not recomputed.
    conflict = field("vdb_sequence_count", 4, "sequences", line=6)
    value["native_fields"].append(conflict)
    with pytest.raises(ContractError, match="native_metadata_conflict_unqualified"): validate_blast_utility_result(value)
    value["failures"] = [failure("database_metadata_conflict", line=6)]
    value["completeness"] = "partial"
    assert validate_blast_utility_result(value)["native_fields"][-1] == conflict
    bad = deepcopy(value); bad["native_fields"][0]["unit"] = "nt"
    with pytest.raises(ContractError): validate_blast_utility_result(bad)


def paths_result():
    value = result("paths_all", "dbs_file")
    value["path_sections"] = [
        {"kind": "vdb", "header_line_number": 1, "presence": "reported_values"},
        {"kind": "vdb_alias", "header_line_number": 4, "presence": "reported_empty"},
        {"kind": "blast_db_alias", "header_line_number": None, "presence": "not_reported"}]
    value["path_records"] = [{"kind": "vdb", "section_ordinal": 0, "native_path_ordinal": i,
        "native_path": "/fixture/source.vdb", "line_number": i + 2, "matched_dependency_ordinals": [7]} for i in range(2)]
    value["vdb_context"]["declared_dependencies"] = [{"role": "database", "ordinal": 7,
        "database_key": "selected", "native_path_index": 0, "native_reference": "/fixture/source.vdb",
        "source": "vdblist_file", "list_occurrence_id": "db-list", "list_entry_ordinal": 1}]
    return value


def test_paths_preserve_duplicates_empty_sections_and_exact_dependency_links():
    value = paths_result()
    assert validate_blast_utility_result(value) == value
    assert [r["native_path_ordinal"] for r in value["path_records"]] == [0, 1]
    edits = [
        lambda v: v["path_records"][0].update(matched_dependency_ordinals=[8]),
        lambda v: v["path_records"][0].update(native_path="source.vdb"),
        lambda v: v["path_records"][0].update(native_path="None"),
        lambda v: v["path_records"][0].update(section_ordinal=1),
        lambda v: v["vdb_context"]["declared_dependencies"][0].update(native_path_index=1),
        lambda v: v["vdb_context"]["declared_dependencies"][0].update(list_occurrence_id="unselected"),
        lambda v: v["vdb_context"]["dependency_database_bindings"].append(binding()),
    ]
    for edit in edits:
        bad = deepcopy(value); edit(bad)
        with pytest.raises(ContractError): validate_blast_utility_result(bad)
    value["path_records"][0].update(native_path="/reported/undeclared", matched_dependency_ordinals=[])
    assert validate_blast_utility_result(value)["path_records"][0]["native_path"] == "/reported/undeclared"
    assert value["vdb_context"]["dependency_database_bindings"] == []


def test_saved_results_revalidate_without_io_and_only_exact_result_programs_dispatch(monkeypatch):
    from gene_annotation_episode.blast_vdb_utility_contracts import validate_vdb_sequence_extraction
    value = json.loads(json.dumps(result()))
    def forbidden(*args, **kwargs): raise AssertionError("No acquisition or native work permitted")
    import subprocess
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    assert validate_vdb_sequence_extraction(value) == value
    for version in ("blast_sequence_extraction_v1", "blast_database_inspection_v2", "blast_database_inspection_v3"):
        bad = deepcopy(value); bad["version"] = version
        with pytest.raises(ContractError): validate_blast_utility_result(bad)


def test_direct_vdb_ports_preserve_common_contract_error_prefix_for_invalid_native_paths():
    from gene_annotation_episode.blast_vdb_utility_contracts import (
        validate_vdb_sequence_extraction, validate_vdb_database_inspection,
    )
    for variant, validate in (("entry", validate_vdb_sequence_extraction), ("info", validate_vdb_database_inspection)):
        value = result(variant)
        value["output_occurrence"]["native_path"] = "../unsafe"
        with pytest.raises(ContractError, match="^blast_utility_"):
            validate(value)


def test_capture_unknown_native_outcome_and_missing_entry_preserve_specific_qualifications():
    value = result("entry_batch")
    value["records"] = []
    value["missing_selector_ordinals"] = [0, 1]
    value["population_completeness"] = "unknown"
    value["original_outcome"].update(returncode=None, state="incomplete", writer_closed=False, inventory_complete=False)
    value["output_occurrence"]["completeness"] = "partial"
    value["stderr_occurrence"]["completeness"] = "unknown"
    value["failures"] = [failure("output_writer_not_closed", stage="capture"),
        failure("output_inventory_incomplete", stage="capture"),
        failure("output_completeness_unestablished", stage="capture"),
        failure("output_completeness_unestablished", oid="err", stage="capture"),
        failure("selection_incomplete", stage="association"),
        failure("native_outcome_unavailable", stage="native")]
    assert validate_blast_utility_result(value) == value
    bad = deepcopy(value); bad["failures"] = [f for f in bad["failures"] if f["code"] != "output_writer_not_closed"]
    with pytest.raises(ContractError, match="capture_unqualified"): validate_blast_utility_result(bad)


def test_explicit_association_cannot_erase_exact_duplicate_requests():
    value = result()
    value["records"][0].update(association="explicit", matched_selector_ordinals=[0])
    value["missing_selector_ordinals"] = [1]
    value["population_completeness"] = "partial_selection"
    with pytest.raises(ContractError, match="supplied_binding_conflict"): validate_blast_utility_result(value)
    value["records"][0]["matched_selector_ordinals"] = [0, 1]
    value["missing_selector_ordinals"] = []
    assert validate_blast_utility_result(value) == value


def test_dependency_lists_preserve_database_custody_and_bind_selected_list_ordinals():
    value = paths_result()
    for field, changed in (("list_entry_ordinal", 2), ("native_reference", "different-value")):
        bad = deepcopy(value)
        bad["vdb_context"]["declared_dependencies"][0][field] = changed
        with pytest.raises(ContractError, match="dependency_list_entry"): validate_blast_utility_result(bad)
    dependency = value["vdb_context"]["declared_dependencies"][0]
    dependency["list_occurrence_id"] = "original-alias-list"
    dependency["list_entry_ordinal"] = 17  # Supplied original alias list, not the selected dbs_file.
    value["database_binding"]["occurrence_ids"].append("original-alias-list")
    assert validate_blast_utility_result(value) == value
    value["database_binding"]["occurrence_ids"].remove("original-alias-list")
    with pytest.raises(ContractError, match="dependency_list_reference"): validate_blast_utility_result(value)


def test_path_dependencies_can_bind_separate_declared_databases_without_alias_inference():
    value = result("paths_all")
    extra = binding("declared-alias", path="/fixture/alias")
    value["vdb_context"]["dependency_database_bindings"] = [extra]
    value["vdb_context"]["declared_dependencies"] = [{"role": "database", "ordinal": 5,
        "database_key": extra["database_key"], "native_path_index": 0, "native_reference": "literal-alias",
        "source": "vdblist", "list_occurrence_id": None, "list_entry_ordinal": None}]
    value["path_sections"] = [{"kind": "vdb_alias", "header_line_number": 1, "presence": "reported_values"}]
    value["path_records"] = [{"kind": "vdb_alias", "section_ordinal": 0, "native_path_ordinal": 0,
        "native_path": "literal-alias", "line_number": 2, "matched_dependency_ordinals": [5]}]
    assert validate_blast_utility_result(value) == value
    value["path_records"][0]["native_path"] = "/fixture/alias"
    assert validate_blast_utility_result(value) == value
    value["path_records"][0]["native_path"] = "alias"
    with pytest.raises(ContractError, match="path_dependency_match"): validate_blast_utility_result(value)


def test_path_rows_cannot_cross_reported_section_boundaries_or_reorder_headers():
    value = paths_result()
    value["path_records"][1]["line_number"] = 5
    with pytest.raises(ContractError, match="path_section_reference"): validate_blast_utility_result(value)
    value = paths_result()
    value["path_sections"][0]["header_line_number"] = 6
    with pytest.raises(ContractError, match="path_section_order"): validate_blast_utility_result(value)


def test_supplied_full_reference_length_is_distinct_from_returned_native_length():
    value = result()
    value["vdb_context"]["member_bindings"] = [member("reference")]
    value["records"][0]["vdb_member"] = member("reference")
    checked = validate_blast_utility_result(value)
    row = checked["records"][0]
    assert row["vdb_member"]["reference_identity"]["full_length"] == 19
    assert row["native_reported_length"] == row["returned_symbol_count"] == 4
    assert row["effective_range"] is None and row["native_oid"] is None
