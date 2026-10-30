"""Retained native info bytes and independent qualification expectations.

The fixture context is controlled parser/projection input. It is not a new
native execution, an authenticated original Store collection, or a child run.
All checks run through bounded529; the original 673 Store is never opened.
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

from gene_annotation_episode import blast_vdb_utility_inputs as readers
from gene_annotation_episode.blast_utility_contracts import validate_blast_utility_result
from gene_annotation_episode.blast_utility_result_views import (
    FACT_PREFIX, VDB_DATABASE_FIELDS, project_blast_utility_result,
    validate_blast_utility_fact_values,
)
from test_blast_vdb_utility_inputs_663 import supplied
from test_blast_vdb_requested_views_667 import inputs, project_args, selector


ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / (
    "verification/tool_graders_hmmer_map_verification_2026-10-28_529/"
    "check131_vdb_workflow673_info/check131_vdb_workflow673_info_text/"
    "ORIGINAL_INFO_STDOUT.txt")
NATIVE_SHA = "cb65d0f9b71a60a74dcbabb602dcd86cdc29e6b5d65c2d0ec3d7c7235c174e0a"
OPERAND = ("/home/chia/repos/gene_annotation_episode/verification/"
           "tool_graders_blast_vdb_fixture_acquisition_2026-10-28_658/"
           "retained/fixture/ERR3487613")
WRAPPED_LEXEME = (
    " \n/home/chia/repos/gene_annotation_episode/verification/tool_graders_blast_vdb_"
    "\nfixture_acquisition_2026-10-28_658/retained/fixture/ERR3487613")
NUMBERS = {"vdb_sequence_count": 20, "vdb_total_unclipped_bases": 5000,
           "vdb_longest_sequence_bases": 250, "vdb_average_sequence_bases": 250}
LABELS = {"vdb_selected_inputs": "Database(s):", "vdb_resolved_paths": "Database(s) Full Path:",
          "vdb_csra_inputs": "CSRA Database(s):"}


def report(selected=" /one", resolved=" /one", csra=None, *, references=False):
    text = (f"Database(s):{selected}\nDatabase(s) Full Path:{resolved}\n"
            "\t20 sequences; 5,000 total bases (unclipped)\n"
            "\tLongest sequence: 250 bases\n\tAverage sequence: 250 bases\n")
    if csra is not None:
        text += "CSRA Database(s):" + csra + "\n"
    if csra is not None or references:
        text += "\t2 ref sequences; 9,000 total ref bases\n"
    return text.encode("utf-8")


def inspect(raw, **changes):
    args = supplied(raw, mode="info")
    args.update(changes)
    result = readers.parse_blast_vdb_inspection(raw, **args)
    return result, {row["field_name"]: row for row in result["native_fields"]}


def assert_missing(result, field, reason, lexeme):
    assert field["value"] is None
    assert field["missing_reason"] == reason
    assert field["native_lexeme"] == lexeme
    if reason == "native_field_absent":
        assert field["line_number"] is None and field["json_pointer"] == ""
        return
    stage, code = (("validation", "semantic_validation_unavailable")
                   if reason == "ambiguous_population" else ("parse", "native_document_invalid"))
    expected = {"stage": stage, "code": code, "occurrence_id": "stdout", "record_key": None,
                "line_number": field["line_number"], "native_returncode": None}
    assert result["failures"].count(expected) == 1


def authentic():
    raw = RETAINED.read_bytes()
    assert len(raw) == 423 and hashlib.sha256(raw).hexdigest() == NATIVE_SHA
    return raw


def test_authentic_wrapped_operand_retains_numbers_and_raw_unknowns():
    raw = authentic()
    args = supplied(raw, mode="info")
    selected = args["operation"]["parameters"]["database_selection"]["inputs"][0]
    selected.update(value=OPERAND, binding_native_path=OPERAND)
    args["database_binding"]["native_paths"] = [OPERAND]
    context = args["vdb_context"]["source_inputs"][0]
    context.update(selected_input={"kind": "path", "value": OPERAND}, binding_native_path=OPERAND)
    before = deepcopy(args)
    result = readers.parse_blast_vdb_inspection(raw, **args)
    fields = {row["field_name"]: row for row in result["native_fields"]}
    assert args == before
    for name, line in (("vdb_selected_inputs", 1), ("vdb_resolved_paths", 4)):
        assert_missing(result, fields[name], "ambiguous_population", WRAPPED_LEXEME)
        assert fields[name]["line_number"] == line
    assert {name: fields[name]["value"] for name in NUMBERS} == NUMBERS
    assert {name: fields[name]["unit"] for name in NUMBERS} == {
        "vdb_sequence_count": "sequences", "vdb_total_unclipped_bases": "nt",
        "vdb_longest_sequence_bases": "nt", "vdb_average_sequence_bases": "nt"}
    for name in ("vdb_csra_inputs", "vdb_reference_sequence_count", "vdb_reference_total_bases"):
        assert_missing(result, fields[name], "native_field_absent", None)
    assert result["completeness"] == "partial"
    assert result["path_sections"] == result["path_records"] == []
    assert len(result["failures"]) == 2
    checks = {row["name"]: row for row in result["checks"]}
    assert checks["syntax"]["status"] == "pass"
    assert checks["database_metadata"]["status"] == "unknown"
    assert checks["database_metadata"]["reason"] == "semantic_validation_unavailable"
    assert validate_blast_utility_result(json.loads(json.dumps(result))) == result
    assert RETAINED.read_bytes() == raw
    (Path(os.environ["HMMER529_ATTEMPT"]) / "VERIFIED_VALUES_678.json").write_text(json.dumps({
        "native_stdout_sha256": NATIVE_SHA, "native_stdout_size_bytes": len(raw),
        "context_kind": "controlled_parser_adapter_with_exact_known_operand",
        "native_helper_calls": 0, "original_store_opened": False,
        "numerical_values": NUMBERS, "inspection": result,
    }, indent=2) + "\n")


def test_inline_selected_order_duplicates_and_single_resolved_path():
    result, fields = inspect(report(selected=" /one /two /one"))
    assert fields["vdb_selected_inputs"]["value"] == ["/one", "/two", "/one"]
    assert fields["vdb_resolved_paths"]["value"] == ["/one"]
    assert result["completeness"] == "complete" and not result["failures"]


@pytest.mark.parametrize("payload", [" /one /two", " /one\tpart", " /one\u00a0part", " /one ", "  /one"])
def test_inline_resolved_whitespace_never_becomes_path_multiplicity(payload):
    result, fields = inspect(report(resolved=payload))
    assert_missing(result, fields["vdb_resolved_paths"], "ambiguous_population", payload)
    assert fields["vdb_selected_inputs"]["value"] == ["/one"]
    assert {name: fields[name]["value"] for name in NUMBERS} == NUMBERS


@pytest.mark.parametrize("field", list(LABELS))
@pytest.mark.parametrize("payload", [" \nabc_\ndef", " \nabc\ndef", " \nabcde\nfgh"])
def test_space_punctuation_and_forced_wraps_remain_unknown(field, payload):
    key = {"vdb_selected_inputs": "selected", "vdb_resolved_paths": "resolved", "vdb_csra_inputs": "csra"}[field]
    result, fields = inspect(report(**{key: payload}))
    assert_missing(result, fields[field], "ambiguous_population", payload)
    assert result["completeness"] == "partial"


@pytest.mark.parametrize("field,reason", [
    ("vdb_selected_inputs", "native_field_invalid"),
    ("vdb_resolved_paths", "ambiguous_population"),
    ("vdb_csra_inputs", "ambiguous_population"),
])
def test_header_padding_and_one_data_line_have_field_specific_meaning(field, reason):
    key = {"vdb_selected_inputs": "selected", "vdb_resolved_paths": "resolved", "vdb_csra_inputs": "csra"}[field]
    raw = report(**{key: " \nabcde"})
    args = supplied(raw, mode="info")
    args["operation"]["parameters"]["line_length"] = 5
    result = readers.parse_blast_vdb_inspection(raw, **args)
    fields = {row["field_name"]: row for row in result["native_fields"]}
    assert_missing(result, fields[field], reason, " \nabcde")


def test_inline_csra_uses_its_native_trailing_separator():
    result, fields = inspect(report(csra=" /one /two /one "))
    assert fields["vdb_csra_inputs"]["value"] == ["/one", "/two", "/one"]
    assert fields["vdb_csra_inputs"]["native_lexeme"] == " /one /two /one "
    assert fields["vdb_reference_sequence_count"]["value"] == 2
    assert fields["vdb_reference_total_bases"]["value"] == 9000
    assert result["completeness"] == "complete"


@pytest.mark.parametrize("payload,reason", [
    (" /one /two", "native_field_invalid"),
    (" /one  /two ", "native_field_invalid"),
    (" /one\tpart ", "ambiguous_population"),
    (" /one\bpart ", "ambiguous_population"),
    (" /one\fpart ", "ambiguous_population"),
    (" ", "native_field_invalid"),
])
def test_csra_invalid_and_unknown_are_distinct_and_keep_control_lexemes(payload, reason):
    result, fields = inspect(report(csra=payload))
    assert_missing(result, fields["vdb_csra_inputs"], reason, payload)
    assert fields["vdb_reference_sequence_count"]["value"] == 2


def test_blank_continuation_lines_are_retained_without_fragment_values():
    payload = " \n/first_\n\nsecond"
    result, fields = inspect(report(resolved=payload))
    assert_missing(result, fields["vdb_resolved_paths"], "ambiguous_population", payload)


def test_absent_empty_and_reported_reference_fields_are_distinct():
    result, fields = inspect(report(references=True))
    assert_missing(result, fields["vdb_csra_inputs"], "native_field_absent", None)
    assert fields["vdb_reference_sequence_count"]["value"] == 2
    assert fields["vdb_reference_total_bases"]["value"] == 9000
    empty, values = inspect(report(selected=" ", resolved=" ", csra=" "))
    for name in LABELS:
        assert_missing(empty, values[name], "native_field_invalid", " ")
    assert empty["completeness"] == "partial"
    assert {name: values[name]["value"] for name in NUMBERS} == NUMBERS


@pytest.mark.parametrize("payload", [" /unfinished", " \n/first_\nsecond"])
def test_open_list_at_eof_is_invalid_not_a_complete_prefix(payload):
    raw = report() + ("CSRA Database(s):" + payload).encode()
    args = supplied(raw, mode="info")
    args["occurrence"]["completeness"] = "partial"
    args["outcome"].update(state="incomplete", writer_closed=False, inventory_complete=False)
    result = readers.parse_blast_vdb_inspection(raw, **args)
    fields = {row["field_name"]: row for row in result["native_fields"]}
    assert_missing(result, fields["vdb_csra_inputs"], "native_field_invalid", payload)
    assert {name: fields[name]["value"] for name in NUMBERS} == NUMBERS
    assert {"output_completeness_unestablished", "output_writer_not_closed",
            "output_inventory_incomplete"} <= {row["code"] for row in result["failures"]}


def test_malformed_interruption_retains_list_bytes_and_valid_numbers():
    payload = " /one\n\tBROKEN REPORT"
    result, fields = inspect(report(resolved=payload))
    assert_missing(result, fields["vdb_resolved_paths"], "native_field_invalid", payload)
    assert {name: fields[name]["value"] for name in NUMBERS} == NUMBERS


def test_corrected_saved_projection_copies_unknowns_without_parsing_or_io(monkeypatch):
    raw = authentic()
    args = project_args(inputs(raw, mode="info"),
                        selector(database_fields=list(VDB_DATABASE_FIELDS), include_checks=True), raw)
    args = json.loads(json.dumps(args))
    saved = deepcopy(args["result"])

    def prohibited(*args, **kwargs):
        raise AssertionError("saved projection attempted native parsing, I/O or execution")

    with monkeypatch.context() as patch:
        for name in ("_vdb_info", "parse_blast_vdb_inspection", "parse_blast_vdb_diagnostics"):
            patch.setattr(readers, name, prohibited)
        patch.setattr(builtins, "open", prohibited)
        patch.setattr(Path, "open", prohibited)
        patch.setattr(Path, "read_bytes", prohibited)
        patch.setattr(Path, "read_text", prohibited)
        patch.setattr(socket, "socket", prohibited)
        patch.setattr(subprocess, "Popen", prohibited)
        view = project_blast_utility_result(**args)
        assert args["result"] == saved
        returned = validate_blast_utility_fact_values(FACT_PREFIX + "database_fields", view["database_fields"])
    assert [{k: v for k, v in row.items() if k not in {"source_ref", "database_key"}}
            for row in returned] == saved["native_fields"]
    assert view["status"]["result_completeness"] == "partial"
    assert view["status"]["state"] == "complete" and not view["missing"]
    assert {row["field_name"]: row["value"] for row in returned if row["field_name"] in NUMBERS} == NUMBERS


def test_saved_historical_shape_is_not_reparsed_or_reinterpreted(monkeypatch):
    """Controlled saved shape, not an edit/read of the historical 673 Store."""
    result, _ = inspect(authentic())
    historical = deepcopy(result)
    fragments = ["/home/chia/repos/gene_annotation_episode/verification/tool_graders_blast_vdb_",
                 "fixture_acquisition_2026-10-28_658/retained/fixture/ERR3487613"]
    for row in historical["native_fields"]:
        if row["field_name"] in {"vdb_selected_inputs", "vdb_resolved_paths"}:
            row.update(value=fragments.copy(), missing_reason=None)
    historical["completeness"] = "complete"
    historical["failures"] = []
    for row in historical["checks"]:
        if row["name"] == "database_metadata":
            row.update(status="pass", reason=None)
    frozen = json.loads(json.dumps(historical))

    def prohibited(*args, **kwargs):
        raise AssertionError("historical validation reparsed native bytes")

    monkeypatch.setattr(readers, "_vdb_info", prohibited)
    monkeypatch.setattr(readers, "parse_blast_vdb_inspection", prohibited)
    assert validate_blast_utility_result(historical) == frozen
    assert historical == frozen
