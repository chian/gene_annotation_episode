"""663 parser checks: one authentic saved extraction; source-derived edge fixtures.

All context objects here are explicit controlled bindings for parser tests. They
do not authenticate a production request or establish offline native closure.
"""
from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.blast_database_extraction import (
    normalize_blast_utility_sequence_symbols, parse_blastdbcmd_sequences,
)
from gene_annotation_episode.blast_utility_contracts import validate_blast_utility_result
from gene_annotation_episode.blast_vdb_inputs import read_blast_vdb_sequence_table
from gene_annotation_episode.blast_vdb_utility_inputs import (
    normalize_blast_vdb_extraction, parse_blast_vdb_diagnostics,
    parse_blast_vdb_extraction, parse_blast_vdb_inspection,
)
from gene_annotation_episode.domain import ContractError


ROOT = Path(__file__).resolve().parents[1]
AUTHENTIC = (ROOT / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/"
    "check121_vdb_native661/temporary/native_observation")
STDOUT_SHA = "3be1e1b841530c2818893eb9a396ca8dcd5257203b4778bdda93719fdc47110c"


def occurrence(raw, oid="stdout", role="stdout", fmt="blast_vdb_cmd_table_v1", direction="output"):
    digest = hashlib.sha256(raw).hexdigest()
    return dict(occurrence_id=oid, direction=direction, role=role, ordinal=0,
        artifact_ref="artifact_" + digest, sha256=digest, size_bytes=len(raw),
        native_format=fmt, completeness="complete", native_path=None)


def provenance(pointer=""):
    return {"source_ref": "controlled-request663", "pointer": pointer}


def identity(value):
    return dict(namespace="blast_vdb_cmd.entry", value=value, version=None)


def supplied(raw=b"A\ta\t4\tacgt\n", *, selectors=("A",), kind="entries", mode="extract_sequences", stderr=b""):
    fmt = ("blast_vdb_cmd_table_v1" if mode == "extract_sequences" else
           "blast_vdb_info_text_v1" if mode == "info" else "blast_vdb_paths_text_v1")
    selection = (dict(kind="entries", source="entry", selectors=[dict(ordinal=n, value=v) for n, v in enumerate(selectors)],
                      batch_occurrence_id=None) if kind == "entries" else {"kind": kind}) if mode == "extract_sequences" else None
    operation = dict(version="blast_utility_operation_v3", program="blast_vdb_cmd", mode=mode,
        input_occurrence_ids=["db-file", "db-manifest"], database_key="controlled-vdb", molecule="dna",
        parameters=dict(database_selection=dict(source="db", inputs=[dict(ordinal=0, kind="path",
            value="/supplied/tiny.vdb", binding_native_path="/supplied/tiny.vdb", list_entry_ordinal=None)],
            list_occurrence_id=None), line_length=80, selection=selection,
            include_filtered_reads=False, output_format=fmt))
    binding = dict(database_key="controlled-vdb", kind="vdb", molecule="dna",
        identity=dict(namespace="controlled", value="tiny", version=None, release=None),
        source_ref="controlled-request663", native_paths=["/supplied/tiny.vdb"],
        occurrence_ids=["db-file", "db-manifest"], inventory_complete=True)
    context = dict(version="blast_vdb_utility_context_v1", source_inputs=[dict(ordinal=0,
        selected_input=dict(kind="path", value="/supplied/tiny.vdb"), binding_native_path="/supplied/tiny.vdb",
        dataset_key=None, dataset_type="csra" if kind == "all_references" else "unknown",
        snapshot=dict(release=None, snapshot_id=None, manifest_sha256=None), run_identifiers=[], source=provenance())],
        selection_kind=kind if selection is not None else None, include_filtered_reads=False,
        entry_identifier_bindings=[dict(selector_ordinal=n, identifier=identity(v), source=provenance())
            for n, v in enumerate(selectors)] if selection is not None and kind == "entries" else [],
        member_bindings=[], sample_links=[], dependency_database_bindings=[], declared_dependencies=[])
    return dict(occurrence=occurrence(raw, fmt=fmt), operation=operation, database_binding=binding,
        outcome=dict(started=True, returncode=0, state="succeeded", writer_closed=True, inventory_complete=True),
        operation_input_occurrences=[], vdb_context=context,
        stderr_contents=stderr, stderr_occurrence=occurrence(stderr, oid="stderr", role="stderr", fmt="text"))


def codes(result):
    return {f["code"] for f in result["failures"]}


def saved_args(args):
    args = deepcopy(args)
    args["stderr_diagnostics"] = parse_blast_vdb_diagnostics(args.pop("stderr_contents"),
        occurrence=args.pop("stderr_occurrence"), outcome=args["outcome"])
    return args


def test_authentic_saved_two_native_rows_and_recalculation(tmp_path):
    """Original native661 bytes; supplied custody context is a controlled adapter."""
    raw, stderr = (AUTHENTIC / "stdout.bin").read_bytes(), (AUTHENTIC / "stderr.bin").read_bytes()
    assert len(raw) == 594 and hashlib.sha256(raw).hexdigest() == STDOUT_SHA and stderr == b""
    selectors = ("gnl|SRA|ERR3487613.1.1", "gnl|SRA|ERR3487613.1.2")
    args = supplied(raw, selectors=selectors, stderr=stderr)
    result = parse_blast_vdb_extraction(raw, **args)
    assert result["version"] == "blast_sequence_extraction_v2"
    assert result["population_completeness"] == "complete_selection" and not result["failures"]
    assert [r["native_identifier"] for r in result["records"]] == list(selectors)
    assert [r["native_accession"] for r in result["records"]] == ["SRA:ERR3487613.1.1", "SRA:ERR3487613.1.2"]
    assert [r["native_reported_length"] for r in result["records"]] == [250, 250]
    assert [r["returned_symbol_count"] for r in result["records"]] == [250, 250]
    assert [hashlib.sha256(r["normalized_sequence"].encode()).hexdigest() for r in result["records"]] == [
        "03a47a624dd902c7f364914de37206018e410e51a19b67a632ff07ab5f34d0eb",
        "0c00cfb9195e3e67b0a80edd9a74a6712f74927b032a26d38c3e5cd252e341af"]
    for row in result["records"]:
        assert row["native_oid"] is row["requested_range"] is row["effective_range"] is row["vdb_member"] is None
        assert row["native_length_basis"] == "returned_sequence"
    lexical = read_blast_vdb_sequence_table(raw, source_ref=args["occurrence"]["artifact_ref"],
        source_version=args["occurrence"]["native_format"])
    saved = tmp_path / "saved-lexical.json"
    saved.write_text(json.dumps(lexical))
    assert normalize_blast_vdb_extraction(json.loads(saved.read_text()), **saved_args(args)) == result
    assert validate_blast_utility_result(json.loads(json.dumps(result))) == result


def test_original_ordinals_missing_n_a_and_every_selector_occurrence():
    raw = b"A\ta\t4\tacgt\r\nmalformed\r\n\r\nB\tb\tN/A\tACGT\r\nC\tc\t4\tN/A\r\nD\td\t4\tACGT\r\n"
    args = supplied(raw, selectors=("A", "A", "D", "absent"))
    result = parse_blast_vdb_extraction(raw, **args)
    assert [r["native_row_ordinal"] for r in result["records"]] == [0, 3, 4, 5]
    assert [r["line_number"] for r in result["records"]] == [1, 4, 5, 6]
    assert result["records"][0]["matched_selector_ordinals"] == [0, 1]
    assert result["records"][-1]["matched_selector_ordinals"] == [2]
    assert result["missing_selector_ordinals"] == [3]
    assert [r["returned_symbol_count"] for r in result["records"]] == [4, None, None, 4]
    assert result["records"][1]["original_sequence"] == "ACGT"
    assert result["records"][2]["original_sequence"] == "N/A"
    assert result["population_completeness"] == "partial_selection"
    assert {f["line_number"] for f in result["failures"] if f["code"] == "native_row_invalid"} >= {2, 3, 4, 5}


@pytest.mark.parametrize("symbols,reported", [("acgt", 4), ("ACGU", 4), ("ACGX", 4), ("AC GT", 4), ("", 0), ("ACGT", 3)])
def test_declared_dna_numerical_agreement_with_classic(symbols, reported):
    raw = f"A\ta\t{reported}\t{symbols}\n".encode()
    result = parse_blast_vdb_extraction(raw, **supplied(raw))
    classic_raw = b"0\t" + raw
    classic_args = supplied(raw)
    classic_args["operation"] = dict(version="blast_utility_operation_v1", program="blastdbcmd", mode="extract_sequences",
        input_occurrence_ids=["db-file", "db-manifest"], database_key="controlled-vdb", molecule="dna",
        parameters=dict(selectors=[dict(ordinal=0, value="A")], output_format="blastdbcmd_tabular_v1",
            range=None, strand="plus", get_dups=False, target_only=False))
    classic_args["database_binding"]["kind"] = "blast_nucleotide_sequence"
    classic = parse_blastdbcmd_sequences(classic_raw,
        occurrence=occurrence(classic_raw, fmt="blastdbcmd_tabular_v1"),
        **{k: classic_args[k] for k in ("operation", "database_binding", "outcome")})
    row, original = result["records"][0], classic["records"][0]
    assert row["normalized_sequence"] == original["normalized_sequence"]
    assert row["returned_symbol_count"] == original["returned_symbol_count"]
    assert row["normalized_sequence"] == normalize_blast_utility_sequence_symbols(symbols, "dna")[0]
    assert ("sequence_symbol_invalid" in codes(result)) == ("sequence_symbol_invalid" in codes(classic))
    assert ("sequence_length_conflict" in codes(result)) == ("sequence_length_conflict" in codes(classic))


def test_literal_and_explicit_mapping_no_guessed_sra_alias():
    raw = b"gnl|SRA|RUN.1.2\tSRA:RUN.1.2\t4\tACGT\n"
    args = supplied(raw, selectors=("RUN.1.2", "SRA:RUN.1.2", "SRA:RUN.1.2"))
    result = parse_blast_vdb_extraction(raw, **args)
    assert result["records"][0]["matched_selector_ordinals"] == [1, 2]
    assert result["missing_selector_ordinals"] == [0]
    explicit = parse_blast_vdb_extraction(raw, record_bindings=[dict(native_row_ordinal=0,
        selector_ordinals=[0, 1, 2])], **args)
    assert explicit["records"][0]["association"] == "explicit"
    with pytest.raises(ContractError, match="supplied_binding_conflict"):
        parse_blast_vdb_extraction(raw, record_bindings=[dict(native_row_ordinal=0, selector_ordinals=[0])], **args)
    assert explicit["records"][0]["vdb_member"] is None


@pytest.mark.parametrize("kind", ["all_native_sequences", "all_references"])
def test_controlled_all_enumerations_and_empty_capture_do_not_invent_selectors(kind):
    raw = b"A\ta\t4\tACGT\nA\ta\t4\tACGT\n"
    result = parse_blast_vdb_extraction(raw, **supplied(raw, kind=kind))
    assert [r["association"] for r in result["records"]] == ["not_applicable", "not_applicable"]
    assert all(r["matched_selector_ordinals"] == [] for r in result["records"])
    assert result["missing_selector_ordinals"] == result["unexpected_record_keys"] == []
    assert result["population_completeness"] == "complete_selection"
    empty = parse_blast_vdb_extraction(b"", **supplied(b"", kind=kind))
    assert empty["records"] == [] and empty["population_completeness"] == "complete_selection"
    assert not empty["failures"]


@pytest.mark.parametrize("message,category", [
    ("Failed to find Bioseq for 'A'", "bioseq_not_found"),
    ("Bioseq constains no sequence data", "sequence_data_absent"),
    ("Empty Bioseq", "empty_bioseq"),
    ("Iterator returns BLAST_SEQSRC_ERROR", "iterator_error"),
    ("Failed to retrieve requested item", "retrieval_failed"),
    ("unfamiliar native diagnostic", "unknown"),
])
def test_source_derived_diagnostics_even_with_native_zero(message, category):
    stderr = ("\n" + message + "\r\n").encode()
    args = supplied(stderr=stderr)
    diagnostic = parse_blast_vdb_diagnostics(stderr, occurrence=args["stderr_occurrence"], outcome=args["outcome"])
    assert diagnostic["native_bytes_hex"] == stderr.hex() and diagnostic["native_text"] == stderr.decode()
    row = diagnostic["diagnostics"][0]
    assert row["category"] == category and row["line_number"] == 2
    assert row["byte_start"] == 1 and row["byte_end"] == len(stderr)
    result = parse_blast_vdb_extraction(b"A\ta\t4\tacgt\n", **args)
    assert result["records"][0]["completeness"] == "complete"
    assert result["population_completeness"] == "partial_selection"
    assert result["original_outcome"]["state"] == "succeeded"
    assert ("native_diagnostic_unrecognized" if category == "unknown" else "selection_incomplete") in codes(result)


def test_native_nonzero_open_writer_and_missing_selector_stay_distinct():
    raw = b"A\ta\t4\tACGT\n"
    args = supplied(raw, selectors=("A", "missing"))
    args["outcome"].update(state="failed", returncode=2)
    result = parse_blast_vdb_extraction(raw, **args)
    assert "native_nonzero_exit" in codes(result) and "output_inventory_incomplete" not in codes(result)
    assert result["records"][0]["returned_symbol_count"] == 4 and result["missing_selector_ordinals"] == [1]
    args = supplied(raw[:-1]); args["outcome"].update(state="incomplete", returncode=None, writer_closed=False, inventory_complete=False)
    args["occurrence"]["completeness"] = "partial"
    result = parse_blast_vdb_extraction(raw[:-1], **args)
    assert {"output_writer_not_closed", "output_inventory_incomplete", "output_completeness_unestablished"} <= codes(result)
    assert result["records"][0]["completeness"] == "partial"
    assert result["population_completeness"] == "partial_selection"


def test_saved_custody_rows_context_and_diagnostics_cannot_be_spliced():
    raw = b"A\ta\t4\tACGT\n"
    args = supplied(raw)
    table = read_blast_vdb_sequence_table(raw, source_ref=args["occurrence"]["artifact_ref"], source_version=args["occurrence"]["native_format"])
    for name, value in [("source_ref", "different"), ("source_version", "wrong-format")]:
        changed = deepcopy(table); changed[name] = value
        with pytest.raises(ContractError, match="input_identity_mismatch"):
            normalize_blast_vdb_extraction(changed, **saved_args(args))
    changed = deepcopy(table); changed["rows"][0]["cells"][0] = "substituted"
    with pytest.raises(ContractError, match="vdb_sequence_table_conflict"):
        normalize_blast_vdb_extraction(changed, **saved_args(args))
    changed_args = saved_args(args); changed_args["stderr_diagnostics"]["original_outcome"]["returncode"] = 1
    with pytest.raises(ContractError, match="original_attempt_conflict"):
        normalize_blast_vdb_extraction(table, **changed_args)
    changed_args = deepcopy(args); changed_args["vdb_context"]["source_inputs"][0]["selected_input"]["value"] = "/wrong"
    with pytest.raises(ContractError, match="vdb_source_input_conflict"):
        parse_blast_vdb_extraction(raw, **changed_args)
    changed_args = deepcopy(args); changed_args["stderr_occurrence"]["occurrence_id"] = "stdout"
    with pytest.raises(ContractError, match="duplicate_occurrence_identity"):
        parse_blast_vdb_extraction(raw, **changed_args)


def test_explicit_dataset_member_sample_and_reference_extent_only():
    raw = b"A\ta\t4\tACGT\n"
    args = supplied(raw)
    ctx = args["vdb_context"]; ctx["source_inputs"][0]["dataset_key"] = "dataset"
    ctx["sample_links"] = [dict(dataset_key="dataset", link=dict(sample_key="sample",
        sample_identifier=dict(namespace="explicit", value="sample", version=None), biosample_identifier=None, source=provenance()))]
    member = dict(binding_key="m", native_identifier="A", dataset_key="dataset", member_kind="reference",
        member_identifier=identity("A"), relationship="catalog_membership", read_identity=None,
        reference_identity=dict(identifier=identity("A"), full_length=19, sequence_sha256=None, source=provenance()),
        sample_key="sample", provenance=provenance())
    ctx["member_bindings"] = [member]
    result = parse_blast_vdb_extraction(raw, **args)
    row = result["records"][0]
    assert row["vdb_member"] == member and row["native_reported_length"] == row["returned_symbol_count"] == 4
    assert row["requested_range"] is row["effective_range"] is None
    ctx["member_bindings"].append({**member, "binding_key": "conflicting", "relationship": "reported_origin"})
    result = parse_blast_vdb_extraction(raw, **args)
    assert result["records"][0]["vdb_member"] is None and "supplied_binding_conflict" in codes(result)
    ctx["member_bindings"] = [member]; ctx["sample_links"] = []
    with pytest.raises(ContractError, match="vdb_member_sample_link"):
        parse_blast_vdb_extraction(raw, **args)


INFO = (b"Database(s): \n/supplied/one\n/supplied/two\nDatabase(s) Full Path: \n"
    b"/resolved/one\n/resolved/two\n\t1,002 sequences; 100,300 total bases (unclipped)\n"
    b"\tLongest sequence: 250 bases\n\tAverage sequence: 99 bases\n"
    b"\t2 ref sequences; 9,000 total ref bases\n")


def test_source_derived_info_wrapping_populations_average_and_absent_csra_label():
    result = parse_blast_vdb_inspection(INFO, **supplied(INFO, mode="info"))
    fields = {f["field_name"]: f for f in result["native_fields"]}
    assert result["completeness"] == "partial" and result["path_records"] == result["path_sections"] == []
    for name in ("vdb_selected_inputs", "vdb_resolved_paths"):
        assert fields[name]["value"] is None and fields[name]["missing_reason"] == "ambiguous_population"
    assert fields["vdb_resolved_paths"]["native_lexeme"] == " \n/resolved/one\n/resolved/two"
    assert fields["vdb_sequence_count"]["value"] == 1002 and fields["vdb_sequence_count"]["native_lexeme"] == "1,002"
    assert fields["vdb_average_sequence_bases"]["value"] == 99  # Native integer, not 100300 / 1002.
    assert fields["vdb_reference_sequence_count"]["value"] == 2
    assert fields["vdb_csra_inputs"]["value"] is None and fields["vdb_csra_inputs"]["missing_reason"] == "native_field_absent"
    assert fields["vdb_reference_total_bases"]["unit"] == "nt"


@pytest.mark.parametrize("tail,expected", [
    (b"\tAverage sequence: 99 bases\n", "duplicate_native_identity"),
    (b"\tAverage sequence: 100 bases\n", "database_metadata_conflict"),
    (b"unrecognized extra line\n", "native_document_invalid"),
])
def test_info_retains_duplicate_conflicting_and_unknown_native_content(tail, expected):
    raw = INFO + tail
    result = parse_blast_vdb_inspection(raw, **supplied(raw, mode="info"))
    assert expected in codes(result) and result["completeness"] == "partial"
    assert any(f["field_name"] == "vdb_sequence_count" and f["value"] == 1002 for f in result["native_fields"])


def test_info_zero_and_truncation_missing_are_not_conflated():
    raw = (b"Database(s): /supplied/tiny.vdb\nDatabase(s) Full Path: /supplied/tiny.vdb\n"
        b"\t0 sequences; 0 total bases (unclipped)\n\tLongest sequence: 0 bases\n\tAverage sequence: 0 bases\n")
    result = parse_blast_vdb_inspection(raw, **supplied(raw, mode="info"))
    assert result["completeness"] == "complete"
    fields = {f["field_name"]: f["value"] for f in result["native_fields"]}
    assert fields["vdb_sequence_count"] == 0 and fields["vdb_reference_sequence_count"] is None
    cut = raw[:raw.index(b"\tAverage")]
    result = parse_blast_vdb_inspection(cut, **supplied(cut, mode="info"))
    assert result["completeness"] == "partial" and "native_document_invalid" in codes(result)
    assert next(f for f in result["native_fields"] if f["field_name"] == "vdb_average_sequence_bases")["value"] is None


def test_wrapped_native_input_tokens_preserve_punctuation_and_words():
    raw = INFO.replace(b"/supplied/one\n/supplied/two", b"/supplied/sequence:one\n/supplied/bases:two")
    raw = raw.replace(b"/resolved/one\n/resolved/two", b"/resolved/sequence:one\n/resolved/bases:two")
    result = parse_blast_vdb_inspection(raw, **supplied(raw, mode="info"))
    fields = {f["field_name"]: f for f in result["native_fields"]}
    assert result["completeness"] == "partial"
    for name in ("vdb_selected_inputs", "vdb_resolved_paths"):
        assert fields[name]["value"] is None and fields[name]["missing_reason"] == "ambiguous_population"
    assert fields["vdb_selected_inputs"]["native_lexeme"] == " \n/supplied/sequence:one\n/supplied/bases:two"
    assert fields["vdb_resolved_paths"]["native_lexeme"] == " \n/resolved/sequence:one\n/resolved/bases:two"


def test_repeated_and_conflicting_info_fields_keep_all_located_values():
    raw = INFO + b"\tAverage sequence: 99 bases\n\tAverage sequence: 100 bases\n"
    result = parse_blast_vdb_inspection(raw, **supplied(raw, mode="info"))
    assert {"duplicate_native_identity", "database_metadata_conflict"} <= codes(result)
    assert [f["value"] for f in result["native_fields"] if f["field_name"] == "vdb_average_sequence_bases"] == [99, 99, 100]


def test_source_derived_paths_sections_typo_duplicates_and_literal_dependencies():
    raw = b"VDB(s): \n/supplied/tiny.vdb\n/supplied/tiny.vdb\n/undeclared/native.vdb\nVDB Alias File(s): None\nBlats DB Alias File(s): \n/supplied/known.nal\n"
    args = supplied(raw, mode="paths_all")
    args["vdb_context"]["declared_dependencies"] = [dict(role="database", ordinal=7,
        database_key="controlled-vdb", native_path_index=0, native_reference="chosen-alias",
        source="vdblist", list_occurrence_id=None, list_entry_ordinal=None)]
    result = parse_blast_vdb_inspection(raw, **args)
    assert result["completeness"] == "complete" and result["native_fields"] == []
    assert [s["presence"] for s in result["path_sections"]] == ["reported_values", "reported_empty", "reported_values"]
    assert [p["native_path_ordinal"] for p in result["path_records"]] == [0, 1, 2, 3]
    assert [p["matched_dependency_ordinals"] for p in result["path_records"]] == [[7], [7], [], []]
    assert result["path_records"][-1]["kind"] == "blast_db_alias"
    assert result["path_records"][0]["native_path"] == result["path_records"][1]["native_path"]


def test_paths_top_level_empty_missing_sections_and_bad_extra_content():
    raw = b"VDB(s): None\n"
    result = parse_blast_vdb_inspection(raw, **supplied(raw, mode="paths"))
    assert result["completeness"] == "complete" and result["path_records"] == []
    assert [s["presence"] for s in result["path_sections"]] == ["reported_empty", "not_reported", "not_reported"]
    missing = parse_blast_vdb_inspection(raw, **supplied(raw, mode="paths_all"))
    assert missing["completeness"] == "partial" and "native_document_invalid" in codes(missing)
    raw = b"VDB(s): \n/supplied/tiny.vdb\nwarning about something\n"
    result = parse_blast_vdb_inspection(raw, **supplied(raw, mode="paths"))
    assert len(result["path_records"]) == 1 and result["completeness"] == "partial"


@pytest.mark.parametrize("extra", [b"None\n", b"VDB(s): \n/repeated/section.vdb\n"])
def test_malformed_paths_keep_earlier_good_rows(extra):
    raw = b"VDB(s): \n/supplied/tiny.vdb\n" + extra
    result = parse_blast_vdb_inspection(raw, **supplied(raw, mode="paths"))
    assert result["completeness"] == "partial" and "native_document_invalid" in codes(result)
    assert result["path_records"][0]["native_path"] == "/supplied/tiny.vdb"


def test_incomplete_streams_do_not_make_full_inspection_from_complete_looking_text():
    args = supplied(INFO, mode="info")
    args["outcome"].update(state="incomplete", returncode=None, writer_closed=False, inventory_complete=False)
    args["stderr_occurrence"]["completeness"] = "unknown"
    result = parse_blast_vdb_inspection(INFO, **args)
    assert result["completeness"] == "partial"
    assert {"output_writer_not_closed", "output_inventory_incomplete", "output_completeness_unestablished"} <= codes(result)


def test_database_list_dependencies_use_supplied_native_path_index_only():
    raw = b"VDB(s): \n/second/source.vdb\n/undeclared/source.vdb\n"
    args = supplied(raw, mode="paths")
    ctx = args["vdb_context"]
    dependency = deepcopy(args["database_binding"])
    dependency.update(database_key="second", occurrence_ids=["second-file"], native_paths=["/first/source.vdb", "/second/source.vdb"])
    ctx["dependency_database_bindings"] = [dependency]
    ctx["declared_dependencies"] = [dict(role="database", ordinal=11, database_key="second", native_path_index=1,
        native_reference="second-selected-alias", source="vdblist", list_occurrence_id=None, list_entry_ordinal=None)]
    result = parse_blast_vdb_inspection(raw, **args)
    assert [r["matched_dependency_ordinals"] for r in result["path_records"]] == [[11], []]


def test_bare_reported_path_tokens_are_retained_without_dependency_inference():
    raw = b"VDB(s): \nreported-native-token\nreported-native-token\nVDB Alias File(s): None\nBlats DB Alias File(s): None\n"
    result = parse_blast_vdb_inspection(raw, **supplied(raw, mode="paths_all"))
    assert result["completeness"] == "complete"
    assert [p["native_path"] for p in result["path_records"]] == ["reported-native-token", "reported-native-token"]
    assert [p["matched_dependency_ordinals"] for p in result["path_records"]] == [[], []]
    assert [p["native_path_ordinal"] for p in result["path_records"]] == [0, 1]


def test_invalid_utf8_and_prefixed_native_messages_preserve_qualifications():
    raw = b"\xff\n"
    result = parse_blast_vdb_extraction(raw, **supplied(raw))
    assert result["records"] == [] and "native_format_unsupported" in codes(result)
    stderr = b"unverified prefix: Empty Bioseq\n\xff\n"
    args = supplied(stderr=stderr)
    diagnostics = parse_blast_vdb_diagnostics(stderr, occurrence=args["stderr_occurrence"], outcome=args["outcome"])
    assert diagnostics["native_text"] is None and diagnostics["native_bytes_hex"] == stderr.hex()
    assert diagnostics["diagnostics"][0]["native_prefix"] == "unverified prefix: "
    assert diagnostics["diagnostics"][1]["native_line"] is None
    assert {"selection_incomplete", "native_diagnostic_unrecognized"} <= codes(diagnostics)


def test_batch_list_occurrences_are_independent_from_database_membership():
    raw = b"A\ta\t4\tACGT\n"
    args = supplied(raw)
    batch = occurrence(b"A\n", oid="batch", role="entry_batch", fmt="text", direction="input")
    args["operation"]["input_occurrence_ids"].append("batch")
    args["operation"]["parameters"]["selection"].update(source="entry_batch", batch_occurrence_id="batch")
    args["operation_input_occurrences"] = [batch]
    result = parse_blast_vdb_extraction(raw, **args)
    assert result["operation_input_occurrences"] == [batch]
    assert "batch" not in result["database_binding"]["occurrence_ids"]
    args["database_binding"]["occurrence_ids"].append("batch")
    with pytest.raises(ContractError, match="duplicate_occurrence_identity"):
        parse_blast_vdb_extraction(raw, **args)


def test_parsers_and_saved_normalizer_perform_no_io(monkeypatch):
    raw = b"A\ta\t4\tACGT\n"; args = supplied(raw)
    info_args = supplied(INFO, mode="info")
    lexical = read_blast_vdb_sequence_table(raw, source_ref=args["occurrence"]["artifact_ref"], source_version=args["occurrence"]["native_format"])
    saved = saved_args(args)

    def prohibited(*args, **kwargs):
        raise AssertionError("parser attempted filesystem, network or process access")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", prohibited)
        patch.setattr(Path, "open", prohibited)
        patch.setattr(Path, "read_bytes", prohibited)
        patch.setattr(Path, "read_text", prohibited)
        patch.setattr(socket, "socket", prohibited)
        patch.setattr(subprocess, "Popen", prohibited)
        parsed = parse_blast_vdb_extraction(raw, **args)
        assert normalize_blast_vdb_extraction(lexical, **saved) == parsed
        assert parse_blast_vdb_inspection(INFO, **info_args)["completeness"] == "partial"
