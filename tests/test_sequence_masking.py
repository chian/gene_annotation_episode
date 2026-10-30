"""Pure masking checks, including saved authentic native bytes from oracle 612.

All constructed byte strings below are labelled synthetic by their test context.
No native executable, acquisition, Store or model is used by these tests.
"""
import builtins
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

import jsonschema
import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.sequence_masking_contracts import (
    PARAMETERS, sequence_masking_operation_schema, validate_sequence_masking_record)
from gene_annotation_episode.sequence_masking_inputs import (
    parse_masking_input_fasta, preflight_masking_input_fasta, parse_sequence_masking_output,
    populate_sequence_masking_sheet)
from gene_annotation_episode.sequence_masking_calculations import calculate_sequence_masking_components
from gene_annotation_episode.windowmasker_statistics import parse_windowmasker_statistics


FIXTURES = Path(__file__).resolve().parents[1] / "verification/tool_graders_masking_native_oracle_2026-10-28_612/retained_native"


def occurrence(content, oid="input", role="sequences", completeness="complete"):
    return {"occurrence_id": oid, "direction": "output" if role == "mask" else "input", "role": role,
        "ordinal": 0, "artifact_ref": "retained:" + oid, "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content), "completeness": completeness}


def operation(program="dustmasker", format="interval", style=None, mode="mask", parse_seqids=False):
    return {"version": "sequence_masking_operation_v1", "program": program, "mode": mode,
        "engine_version": None, "input_format": "fasta", "output_format": format,
        "masking_style": style or ("not_applicable" if mode == "create_counts" else
                                  "interval" if format == "interval" else "soft"),
        "parse_seqids": parse_seqids,
        "requested_parameters": {k: None for k in PARAMETERS[(program, mode)]}}


def custody(records, *, complete=True, returncode=0, producer="authenticated_native", explicit=False):
    basis = "native_fasta_iteration" if producer == "authenticated_native" else "caller_declared"
    return {"producer_kind": producer, "sequence_order": [r["record_key"] for r in records],
        "order_basis": basis, "output_complete": complete, "native_returncode": returncode,
        "record_bindings": [{"output_record_ordinal": i, "input_record_key": r["record_key"], "basis": basis}
                            for i, r in enumerate(records)] if explicit else []}


def build(input_bytes, output_bytes, *, op=None, records=None, owner=None, statistics=None):
    op = operation() if op is None else op
    if records is None:
        records = parse_masking_input_fasta(input_bytes, occurrence=occurrence(input_bytes),
            molecule="protein" if op["program"] == "segmasker" else "dna")["records"]
    owner = custody(records) if owner is None else owner
    out = occurrence(output_bytes, "output", "mask", "complete" if owner["output_complete"] else "partial")
    parsed = parse_sequence_masking_output(output_bytes, format=op["output_format"], occurrence=out,
        input_records=records, operation=op, custody=owner)
    outcome = {"returncode": owner["native_returncode"], "state": "succeeded" if owner["native_returncode"] == 0 else
               "failed" if owner["native_returncode"] is not None else "unknown", "output_complete": owner["output_complete"]}
    sheet = populate_sequence_masking_sheet(operation=op, inputs=records, parsed_output=parsed,
                                          statistics=statistics, native_outcome=outcome)
    return sheet, calculate_sequence_masking_components(sheet)


def retained(pin):
    content = (FIXTURES / pin["path"]).read_bytes()
    assert len(content) == pin["size_bytes"]
    assert hashlib.sha256(content).hexdigest() == pin["sha256"]
    return content


def native_sheet(case_id):
    manifest = json.loads((FIXTURES / "ORACLE_MANIFEST.json").read_text())
    case = next(c for c in manifest["cases"] if c["case_id"] == case_id)
    source = next(r for r in manifest["inputs"] if r["input_id"] == case["input_id"])
    raw_input, raw_output = retained(source["retained"]), retained(case["primary_output"])
    fmt = "interval" if "interval" in case_id else "fasta"
    op = operation(case["program"], fmt, style="hard" if "hard" in case_id else None, parse_seqids=case["parse_seqids"])
    version_case = next(c for c in manifest["cases"] if c["case_id"] == case["program"] + "_version")
    op["engine_version"] = retained(version_case["stdout"]).decode().splitlines()[0].split(": ")[1]
    for name, value in case["selected_parameters"].items():
        key = name.lstrip("-")
        if key not in op["requested_parameters"]:
            continue
        kind = PARAMETERS[(op["program"], "mask")][key][0]
        op["requested_parameters"][key] = (value == "true" if kind == "boolean" else
                                           float(value) if kind == "number" else int(value))
    statistics = None
    if op["program"] == "windowmasker":
        counts_case = next(c for c in manifest["cases"] if c["mode"] == "create_counts")
        raw_stats = retained(counts_case["primary_output"])
        statistics = parse_windowmasker_statistics(raw_stats, occurrence=occurrence(raw_stats, "stats", "statistics"),
            format="ascii_statistics", reference_binding={"kind": "generated", "statistics_occurrence_id": "stats",
                "reference_occurrence_ids": ["reference:window_reference.fa"], "producer_source_ref": "oracle612:create_counts",
                "producer_attempt_id": manifest["attempt"], "provenance": "authenticated_generation"})
    return build(raw_input, raw_output, op=op, statistics=statistics)


@pytest.mark.parametrize("program,expected", [
    ("dustmasker", [(80, 80), (0, 32), (72, 72)]),
    ("segmasker", [(64, 64), (0, 20), (32, 72)]),
    ("windowmasker", [(80, 80), (0, 32), (0, 4)])])
@pytest.mark.parametrize("parsed", [False, True])
def test_saved_native_interval_soft_equivalence(program, expected, parsed):
    base = program + ("_parsed" if parsed else "")
    interval_sheet, interval = native_sheet(base + "_interval")
    soft_sheet, soft = native_sheet(base + "_soft")
    for index, (masked, length) in enumerate(expected):
        a, b = interval["records"][index], soft["records"][index]
        assert a["masked_positions"]["value"] == b["masked_positions"]["value"] == masked
        assert a["input_length"]["value"] == b["input_length"]["value"] == length
        assert a["masked_fraction"]["value"] == b["masked_fraction"]["value"] == masked / length
        assert a["merged_intervals_half_open"] == b["merged_intervals_half_open"]
        assert b["changed_positions"] == {"value": 0, "unit": b["unit"], "missing_reason": None}
        assert a["changed_positions"]["missing_reason"] == "not_applicable"
        assert b["native_interval_count"]["missing_reason"] == "not_applicable"
    # Original duplicate headers remain distinct. Native generated IDs do not
    # replace original identities or cause name-based joins.
    assert interval_sheet["inputs"][0]["native_header"] == interval_sheet["inputs"][1]["native_header"]
    assert interval["records"][0]["record_key"] != interval["records"][1]["record_key"]
    native = interval_sheet["parsed_output"]["records"][0]["native_header"]
    assert native.startswith("lcl|dup" if parsed else "dup")
    assert soft_sheet["inputs"][1]["original_sequence"].islower()
    assert soft_sheet["parsed_output"]["records"][1]["output_sequence"].isupper()
    if program == "windowmasker":
        assert interval_sheet["statistics"]["thresholds"]["t_low"] == 3
        assert interval_sheet["operation"]["requested_parameters"]["t_low"] == 1
        assert not interval_sheet["statistics"]["failures"]


def test_saved_native_dust_hard_ambiguity_preserves_exact_changed_count():
    sheet, result = native_sheet("dustmasker_hard")
    assert result["records"][0]["masked_positions"]["value"] == 80
    assert result["records"][1]["masked_positions"]["value"] == 0
    record = result["records"][2]
    assert record["input_length"]["value"] == 72
    assert record["changed_positions"]["value"] == 64
    assert record["masked_positions"]["value"] is None
    assert record["masked_fraction"] == {"numerator": None, "denominator": 72, "value": None,
                                          "missing_reason": "hard_mask_ambiguous"}
    assert sheet["parsed_output"]["records"][2]["measurement"] == "hard_mask_ambiguous"


def test_synthetic_overlap_duplicate_intervals_reuse_exact_shared_helpers():
    from gene_annotation_episode import genomic_overlap_calculations, hmmer_search_grader
    with patch.object(hmmer_search_grader, "_union", wraps=hmmer_search_grader._union) as union, \
         patch.object(genomic_overlap_calculations, "_ratio", wraps=genomic_overlap_calculations._ratio) as ratio:
        sheet, result = build(b">one\nACGTACGTACGT\n", b">generated\n0 - 3\n2 - 5\n8 - 8\n0 - 3\n")
    row = result["records"][0]
    assert union.call_count == ratio.call_count == 1
    assert len(sheet["parsed_output"]["records"][0]["native_intervals"]) == 4
    assert row["native_interval_count"]["value"] == 4
    assert row["merged_intervals_half_open"] == [[0, 6], [8, 9]]
    assert row["merged_interval_count"]["value"] == 2
    assert row["masked_positions"]["value"] == 7
    assert row["unmasked_positions"]["value"] == 5
    assert row["masked_fraction"]["value"] == 7 / 12


def test_synthetic_no_mask_absent_partial_and_native_failed_are_distinct():
    raw = b">a\nACGT\n>b\nACGT\n"
    records = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule="dna")["records"]
    _, complete = build(raw, b">a\n>b\n")
    assert [r["masked_positions"]["value"] for r in complete["records"]] == [0, 0]
    _, absent = build(raw, b"")
    assert all(r["masked_positions"]["value"] is None for r in absent["records"])
    owner = custody(records, complete=False, returncode=3, explicit=True)
    sheet, partial = build(raw, b">a\n0 - 1\n>b\n", owner=owner)
    assert partial["records"][0]["masked_positions"]["value"] == 2
    assert partial["records"][1]["masked_positions"]["value"] is None
    assert partial["records"][1]["masked_fraction"]["missing_reason"] == "output_record_incomplete"
    assert any(f["code"] == "native_failed" for f in sheet["failures"])
    unbound = custody(records, complete=False, returncode=3)
    sheet, unknown = build(raw, b">a\n0 - 1\n>b\n", owner=unbound)
    assert len(sheet["parsed_output"]["unassigned_records"]) == 2
    assert sheet["parsed_output"]["unassigned_records"][0]["intervals_half_open"] == [[0, 2]]
    assert all(r["masked_positions"]["value"] is None for r in unknown["records"])


def test_synthetic_supplied_outputs_require_explicit_record_bindings():
    raw = b">a\nACGT\n>b\nACGT\n"
    records = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule="dna")["records"]
    sheet, _ = build(raw, b">a\n0 - 1\n>b\n", owner=custody(records, producer="supplied_artifact"))
    assert not sheet["parsed_output"]["records"]
    owner = custody(records, producer="supplied_artifact", explicit=True)
    sheet, result = build(raw, b">different\n0 - 1\n>other\n", owner=owner)
    assert result["records"][0]["masked_positions"]["value"] == 2
    assert sheet["parsed_output"]["records"][0]["association"] == "caller_declared"


@pytest.mark.parametrize("invalid,reason", [(b"AC-GT", "gapped_input_unsupported"),
    (b"ACUGT", "unsupported_sequence_symbol"), (b"AC?GT", "unsupported_sequence_symbol"),
    (b"AC\xffGT", "input_not_utf8")])
def test_synthetic_invalid_substrate_has_no_denominator(invalid, reason):
    raw = b">one\n" + invalid + b"\n"
    records = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule="dna")["records"]
    assert records[0]["length"] is None
    assert records[0]["original_sequence"].encode("utf-8", errors="surrogateescape") == invalid
    sheet, result = build(raw, b">one\n0 - 1\n", records=records, owner=custody(records, explicit=True))
    assert any(f["code"] == reason for f in sheet["failures"])
    row = result["records"][0]
    assert row["input_length"]["missing_reason"] == reason
    assert row["masked_fraction"]["denominator"] is None
    assert row["masked_positions"]["value"] is None


def test_synthetic_empty_record_and_empty_file_are_different():
    raw = b">empty\n"
    parsed = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule="dna")
    assert parsed["records"][0]["length"] == 0
    assert parsed["records"][0]["failures"][0]["code"] == "empty_sequence"
    _, result = build(raw, b">empty\n", records=parsed["records"], owner=custody(parsed["records"], explicit=True))
    assert result["records"][0]["masked_fraction"] == {"numerator": 0, "denominator": 0, "value": None,
                                                      "missing_reason": "zero_denominator"}
    empty = parse_masking_input_fasta(b"", occurrence=occurrence(b""), molecule="dna")
    assert empty["records"] == []
    assert empty["failures"][0]["code"] == "empty_input"


@pytest.mark.parametrize("row,reason", [(b"bad row", "malformed_interval_row"),
    (b"8 - 9", "interval_out_of_bounds"), (b"3 - 1", "reversed_interval"),
    (b"-1 - 2", "malformed_interval_row")])
def test_synthetic_malformed_interval_preserves_valid_rows_and_other_records(row, reason):
    sheet, result = build(b">a\nACGT\n>b\nACGT\n", b">a\n0 - 1\n" + row + b"\n>b\n2 - 3\n")
    assert sheet["parsed_output"]["records"][0]["intervals_half_open"] == [[0, 2]]
    assert any(f["code"] == reason for f in sheet["failures"])
    assert result["records"][0]["masked_positions"]["value"] is None
    assert result["records"][1]["masked_positions"]["value"] == 2


@pytest.mark.parametrize("output,reason", [(b"acg", "output_sequence_length_mismatch"),
    (b"acga", "output_sequence_symbol_change"), (b"acg?", "unsupported_output_symbol")])
def test_synthetic_incompatible_soft_output_never_implies_mask(output, reason):
    sheet, result = build(b">a\nACGT\n", b">a\n" + output + b"\n", op=operation(format="fasta"))
    assert reason in {f["code"] for f in sheet["failures"]}
    assert result["records"][0]["masked_fraction"]["value"] is None
    assert result["records"][0]["changed_positions"]["value"] is None


def test_synthetic_original_bytes_ordinals_and_mixed_occurrences_survive():
    a = b">dup caf\xc3\xa9\r\n aC gT \r\n>dup\r\nA-\r\n>dup\r\nTGCA\r\n"
    b = b">dup\nCCCC\n"
    pa = parse_masking_input_fasta(a, occurrence=occurrence(a, "a"), molecule="dna")
    pb = parse_masking_input_fasta(b, occurrence=occurrence(b, "b"), molecule="dna")
    assert [r["record_ordinal"] for r in pa["records"]] == [0, 1, 2]
    assert [r["byte_offset"] for r in pa["records"]] == [0, a.index(b">dup", 1), a.rindex(b">dup")]
    assert pa["records"][0]["original_sequence"] == "aCgT"
    records = [pa["records"][2], pb["records"][0]]
    sheet, result = build(b"", b">dup\n1 - 2\n>dup\n", records=records)
    assert [r["record_key"] for r in result["records"]] == ["a#/records/2", "b#/records/0"]
    assert result["records"][0]["masked_fraction"]["value"] == .5
    assert sheet["inputs"][0]["byte_offset"] == a.rindex(b">dup")


def test_synthetic_saved_only_recalculation_denies_all_io_and_process_work():
    sheet, expected = build(b">one\nACGTACGTACGT\n", b">one\n0 - 3\n2 - 5\n8 - 8\n")
    saved = json.loads(json.dumps(sheet))
    def denied(*args, **kwargs):
        raise AssertionError("saved calculation attempted I/O or process work")
    with patch.object(builtins, "open", denied), patch.object(io, "open", denied), \
         patch.object(socket, "socket", denied), patch.object(subprocess, "Popen", denied):
        actual = calculate_sequence_masking_components(saved)
    assert actual == expected
    assert saved == sheet


@pytest.mark.parametrize("program,mode", [("dustmasker", "mask"), ("segmasker", "mask"),
    ("windowmasker", "mask"), ("windowmasker", "create_counts")])
def test_operation_schema_and_validation_have_one_parameter_authority(program, mode):
    op = operation(program, "ascii_statistics" if mode == "create_counts" else "interval", mode=mode)
    schema = sequence_masking_operation_schema(program=program, mode=mode)
    jsonschema.validate(op, schema)
    assert validate_sequence_masking_record("Operation", op) == op
    assert set(schema["properties"]["requested_parameters"]["required"]) == set(op["requested_parameters"])
    bad = deepcopy(op); bad["requested_parameters"]["extra"] = None
    with pytest.raises(ContractError, match="sequence_masking_object_fields"):
        validate_sequence_masking_record("Operation", bad)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)
    bad = deepcopy(op); bad["requested_parameters"].pop(next(iter(bad["requested_parameters"])))
    with pytest.raises(ContractError, match="sequence_masking_object_fields"):
        validate_sequence_masking_record("Operation", bad)
    schema["properties"]["requested_parameters"]["properties"].clear()
    assert sequence_masking_operation_schema(program=program, mode=mode)["properties"]["requested_parameters"]["properties"]


def test_contract_numerical_types_bounds_and_unknown_versions():
    op = operation("windowmasker", "ascii_statistics", mode="create_counts")
    op["requested_parameters"]["genome_size"] = 2**63 - 1
    assert validate_sequence_masking_record("Operation", op)["requested_parameters"]["genome_size"] == 2**63 - 1
    for value in (True, 0, 2**63, 1.5):
        op["requested_parameters"]["genome_size"] = value
        with pytest.raises(ContractError):
            validate_sequence_masking_record("Operation", op)
    for value in (float("nan"), float("inf"), -1, True):
        seg = operation("segmasker"); seg["requested_parameters"]["locut"] = value
        with pytest.raises(ContractError):
            validate_sequence_masking_record("Operation", seg)
    seg = operation("segmasker"); seg["requested_parameters"].update(locut=4.0, hicut=2.0)
    assert validate_sequence_masking_record("Operation", seg)["engine_version"] is None
    for func in (lambda: sequence_masking_operation_schema(program="dustmasker", mode="create_counts"),
                 lambda: validate_sequence_masking_record("Other", {})):
        with pytest.raises(ContractError):
            func()


def test_contract_rejects_wrong_associations_bytes_and_format_style():
    raw = b">a\nACGT\n"
    with pytest.raises(ContractError, match="content_occurrence_mismatch"):
        parse_masking_input_fasta(raw, occurrence=occurrence(b">b\nACGT\n"), molecule="dna")
    op = operation("segmasker", "fasta", "hard")
    with pytest.raises(ContractError, match="mode_format"):
        validate_sequence_masking_record("Operation", op)
    sheet, _ = build(raw, b">a\n0 - 1\n")
    bad = deepcopy(sheet); bad["parsed_output"]["records"][0]["input_record_key"] = "wrong#/records/0"
    with pytest.raises(ContractError):
        calculate_sequence_masking_components(bad)
    copied = validate_sequence_masking_record("SequenceMaskingSheet", sheet)
    copied["inputs"][0]["checks"].clear()
    assert sheet["inputs"][0]["checks"]


def test_saved_native_empty_and_failed_outputs_do_not_manufacture_zero_masks():
    manifest = json.loads((FIXTURES / "ORACLE_MANIFEST.json").read_text())
    for name in ("dustmasker_empty", "dustmasker_malformed", "windowmasker_missing_statistics"):
        case = next(c for c in manifest["cases"] if c["case_id"] == name)
        content = retained(case["primary_output"])
        assert content == b""
        source = next(r for r in manifest["inputs"] if r["input_id"] == case["input_id"])
        raw = retained(source["retained"])
        records = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule="dna")["records"]
        owner = custody(records, complete=case["native_output_complete"], returncode=case["returncode"])
        sheet, result = build(raw, content, op=operation(case["program"]), records=records, owner=owner)
        assert not sheet["parsed_output"]["records"]
        assert all(r["masked_positions"]["value"] is None for r in result["records"])
        assert any(f["code"] == "mask_output_absent" for f in sheet["failures"])


@pytest.mark.parametrize("raw,molecule", [
    (b">duplicate\naC gT\n>duplicate\nTGCA\n", "dna"),
    (b"", "dna"), (b">empty\n", "dna"), (b">bad\nA-C\n", "dna"),
    (b">bad\nAUC\n", "dna"), (b"not fasta\n", "dna"),
    (b">bad\nAC\xffG\n>good\nTGCA\n", "dna"),
    (b">protein\nacdefghiklmnpqrstvwy\n", "protein")])
def test_preflight_and_captured_parser_share_exact_input_validation(raw, molecule):
    preflight = preflight_masking_input_fasta(raw, molecule=molecule)
    parsed = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule=molecule)
    ordinals = {r["record_key"]: r["record_ordinal"] for r in parsed["records"]}
    assert preflight == {"version": "sequence_masking_preflight_v1",
        "valid": bool(parsed["records"]) and not parsed["failures"],
        "record_count": len(parsed["records"]),
        "failures": [{"code": f["code"], "record_ordinal": ordinals.get(f["record_key"]),
                      "line_number": f["line_number"]} for f in parsed["failures"]]}
    assert not ({"artifact_ref", "occurrence_id", "record_key"} & set(preflight))


@pytest.mark.parametrize("filename,molecule", [("dna.fa", "dna"), ("protein.fa", "protein"),
                                               ("window_target.fa", "dna")])
def test_preflight_saved_native_input_population(filename, molecule):
    manifest = json.loads((FIXTURES / "ORACLE_MANIFEST.json").read_text())
    source = next(r for r in manifest["inputs"] if r["input_id"] == filename)
    raw = retained(source["retained"])
    assert preflight_masking_input_fasta(raw, molecule=molecule) == {
        "version": "sequence_masking_preflight_v1", "valid": True, "record_count": 3, "failures": []}


@pytest.mark.parametrize("content,molecule", [("not bytes", "dna"), (True, "dna"), (b">a\nACGT\n", []),
                                            (b">a\nACGT\n", "rna")])
def test_preflight_malformed_caller_arguments_raise_stable_contract_error(content, molecule):
    with pytest.raises(ContractError, match="sequence_masking_"):
        preflight_masking_input_fasta(content, molecule=molecule)


@pytest.mark.parametrize("mode", ["interval", "soft", "hard"])
def test_saved_sheet_rejects_forged_exact_mask_assumptions(mode):
    op = operation(format="interval" if mode == "interval" else "fasta",
                   style="hard" if mode == "hard" else None)
    out = b">a\n0 - 1\n" if mode == "interval" else b">a\nacGT\n" if mode == "soft" else b">a\nNNGT\n"
    sheet, _ = build(b">a\nACGT\n", out, op=op)
    bad = deepcopy(sheet)
    bad["parsed_output"]["records"][0]["intervals_half_open"] = [[0, 4]]
    with pytest.raises(ContractError, match="relationship"):
        calculate_sequence_masking_components(bad)
    if mode != "interval":
        bad = deepcopy(sheet)
        bad["parsed_output"]["records"][0]["output_sequence"] = "TTGT"
        with pytest.raises(ContractError, match="relationship"):
            calculate_sequence_masking_components(bad)


def test_saved_sheet_cannot_erase_hard_n_ambiguity_or_input_failures():
    sheet, _ = build(b">a\nANNT\n", b">a\nNNNN\n", op=operation(format="fasta", style="hard"))
    sheet["parsed_output"]["records"][0]["measurement"] = "exact_mask"
    with pytest.raises(ContractError, match="native_hard_mask_ambiguity"):
        calculate_sequence_masking_components(sheet)
    raw = b">a\nA-CG\n"
    records = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule="dna")["records"]
    sheet, _ = build(raw, b">a\n0 - 1\n", records=records, owner=custody(records, explicit=True))
    sheet["failures"] = []
    with pytest.raises(ContractError, match="lost_input_diagnostics"):
        calculate_sequence_masking_components(sheet)


def test_incompatible_molecule_never_supplies_mask_denominator():
    raw = b">protein\nACGT\n"
    records = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule="protein")["records"]
    _, result = build(raw, b">protein\n0 - 1\n", records=records)
    row = result["records"][0]
    assert row["unit"] == "nt"
    assert row["input_length"]["value"] is None
    assert row["masked_fraction"]["missing_reason"] == "incompatible_input_molecule"


def test_partial_input_and_unassociated_soft_output_keep_original_data():
    raw = b">closed\nACGT\n>last\nAC\n"
    parsed = parse_masking_input_fasta(raw, occurrence=occurrence(raw, completeness="partial"), molecule="dna")
    assert [r["length"] for r in parsed["records"]] == [4, None]
    valid = b">a\nACGT\n"
    records = parse_masking_input_fasta(valid, occurrence=occurrence(valid), molecule="dna")["records"]
    sheet, _ = build(valid, b">unbound\naCGt\n", op=operation(format="fasta"), records=records,
                     owner=custody(records, producer="supplied_artifact"))
    assert sheet["parsed_output"]["unassigned_records"][0]["intervals_half_open"] == [[0, 1], [3, 4]]
