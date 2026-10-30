"""Existing masking-sheet authority over authentic 636 conversion artifacts."""
import builtins
from copy import deepcopy
import io
import json
import socket
import subprocess
from unittest.mock import patch

import jsonschema
import pytest

from gene_annotation_episode.blast_maskinfo_inputs import parse_blast_maskinfo, populate_mask_conversion
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.sequence_masking_contracts import sequence_masking_molecule, sequence_masking_operation_schema, validate_sequence_masking_record as core
from gene_annotation_episode.sequence_masking_inputs import parse_masking_input_fasta
from gene_annotation_episode.sequence_masking_calculations import calculate_sequence_masking_components
from gene_annotation_episode.sequence_masking_result_views import project_masking_result, QUANTITIES
from test_blast_maskinfo_inputs_639 import occurrence, retained


def operation(case):
    return {"version": "sequence_masking_operation_v1", "program": "convert2blastmask", "mode": "convert_mask",
        "engine_version": None, "input_format": "fasta", "input_mask_basis": "lowercase_input",
        "molecule": "protein" if case["declared_molecule"] == "protein" else "dna",
        "output_format": case["native_format"], "masking_style": "interval", "parse_seqids": case["parse_seqids"],
        "requested_parameters": {"masking_algorithm": case["declared_upstream_algorithm"], "masking_options": case["declared_upstream_options"]}}


def build(case_id, *, input_bytes=None, output_bytes=None, state=None, complete=True, supplied=False,
          explicit=False, bindings=None, modify=None):
    case, original, data = retained(case_id)
    op = operation(case)
    original = original if input_bytes is None else input_bytes
    data = data if output_bytes is None else output_bytes
    inp = occurrence(original, "input", "sequences")
    inputs = parse_masking_input_fasta(original, occurrence=inp, molecule=sequence_masking_molecule(op))["records"]
    out = occurrence(data, completeness="complete" if complete else "partial")
    parsed = parse_blast_maskinfo(data, occurrence=out, native_format=op["output_format"])
    state = state or ("succeeded" if case["returncode"] == 0 else "failed")
    rc = 0 if state == "succeeded" else 1 if state == "failed" else None
    outcome = {"returncode": rc, "state": state, "output_complete": complete}
    basis = "caller_declared" if supplied else "native_single_input" if op["output_format"] == "interval" else "native_masked_input_iteration"
    custody = {"producer_kind": "supplied_artifact" if supplied else "authenticated_native", "sequence_order": [r["record_key"] for r in inputs],
        "order_basis": basis, "output_complete": complete, "native_returncode": rc, "record_bindings": []}
    if explicit or op["output_format"] == "interval" and len(inputs) == 1:
        masked = [r for r in inputs if any(c.islower() for c in r["original_sequence"])]
        custody["record_bindings"] = [{"output_record_ordinal": n, "input_record_key": r["record_key"], "basis": basis}
                                      for n, r in enumerate(masked[:len(parsed["records"])])]
    if bindings is not None:
        custody["record_bindings"] = bindings
    if modify:
        modify(op, inputs, parsed, custody, outcome)
    sheet = populate_mask_conversion(operation=op, input_records=inputs, parsed_maskinfo=parsed, custody=custody, native_outcome=outcome)
    return sheet, calculate_sequence_masking_components(sheet)


@pytest.mark.parametrize("case_id", ["nucleotide_xml_parsed", "nucleotide_text_parsed", "nucleotide_xml_unparsed"])
def test_authentic_omission_uses_shared_sheet_and_one_numerical_authority(case_id):
    sheet, calculated = build(case_id)
    assert sheet["version"] == "sequence_masking_sheet_v1"
    rows = calculated["records"]
    assert [r["masked_positions"]["value"] for r in rows] == [5, 0, 4, 3]
    assert [r["input_length"]["value"] for r in rows] == [12, 8, 8, 8]
    assert [r["masked_fraction"]["value"] for r in rows] == [5 / 12, 0, .5, .375]
    assert [r["native_interval_count"]["value"] for r in rows] == [3, None, 2, 2]
    assert rows[1]["native_interval_count"]["missing_reason"] == "native_mask_record_not_emitted"
    assert rows[1]["merged_intervals_half_open"] == []
    assert rows[1]["unmasked_positions"]["value"] == 8
    parsed = sheet["parsed_output"]
    assert [r["output_record_ordinal"] for r in parsed["records"]] == [0, 1, 2]
    assert [r["input_record_key"] for r in parsed["records"]] == ["input#/records/0", "input#/records/2", "input#/records/3"]
    assert parsed["known_zero_records"] == [{"input_record_key": "input#/records/1", "output_occurrence_id": "mask",
                                            "evidence_kind": "authenticated_complete_conversion_omission"}]
    assert all(r["native_header"] == "" for r in parsed["records"])
    assert not sheet["failures"]


def test_authentic_duplicates_are_occurrences_and_caller_declarations_stay_declared():
    sheet, actual = build("duplicate_headers_xml")
    assert [r["masked_fraction"]["value"] for r in actual["records"]] == [2 / 6, 4 / 6]
    assert all(r["association"] == "authenticated_native_masked_order" for r in sheet["parsed_output"]["records"])
    unresolved, numbers = build("duplicate_headers_xml", supplied=True)
    assert len(unresolved["parsed_output"]["unassigned_records"]) == 2
    assert all(r["masked_fraction"]["value"] is None for r in numbers["records"])
    declared, actual = build("duplicate_headers_xml", supplied=True, explicit=True)
    assert [r["masked_positions"]["value"] for r in actual["records"]] == [2, 4]
    assert all(r["association"] == "caller_declared" for r in declared["parsed_output"]["records"])
    assert any(r["reason"] == "caller_declared_association" for r in declared["checks"])


def test_authentic_protein_and_single_interval_units():
    sheet, rows = build("protein_xml")
    value = rows["records"][0]
    assert value["unit"] == "aa" and value["masked_fraction"]["value"] == 7 / 19
    assert value["masked_positions"] == {"value": 7, "unit": "aa", "missing_reason": None}
    assert value["changed_positions"] == {"value": None, "unit": "aa", "missing_reason": "not_applicable"}
    sheet, actual = build("single_interval")
    assert actual["records"][0]["masked_fraction"]["value"] == .5
    assert sheet["parsed_output"]["records"][0]["association"] == "authenticated_single_input"
    assert sheet["parsed_output"]["native_maskinfo"]["roots"] == []


@pytest.mark.parametrize("state,complete,supplied", [("failed", True, False), ("unknown", True, False),
    ("succeeded", False, False), ("succeeded", True, True)])
def test_identical_empty_output_does_not_supply_zero_without_original_success(state, complete, supplied):
    sheet, values = build("uppercase_only_xml", state=state, complete=complete, supplied=supplied)
    assert not sheet["parsed_output"]["known_zero_records"]
    assert values["records"][0]["masked_fraction"]["value"] is None
    assert "input_mask_record_absent" in {r["code"] for r in sheet["failures"]}


def test_successful_uppercase_zero_is_separate_from_empty_or_failed_input():
    sheet, rows = build("uppercase_only_xml")
    assert rows["records"][0]["masked_fraction"]["value"] == 0
    assert sheet["parsed_output"]["records"] == []
    failed, rows = build("malformed_xml")
    assert failed["parsed_output"]["known_zero_records"] == [] and rows["records"] == []
    empty_interval, rows = build("single_interval", input_bytes=b">lcl|interval_a\nACGT\n", output_bytes=b"")
    assert rows["records"][0]["masked_fraction"]["value"] == 0
    assert empty_interval["parsed_output"]["records"] == []
    assert empty_interval["parsed_output"]["custody"]["record_bindings"] == []


def test_multi_input_bare_stream_is_unassigned_and_binary_unavailable():
    sheet, rows = build("single_interval", input_bytes=b">a\nAAaa\n>b\nNNtt\n")
    assert len(sheet["parsed_output"]["unassigned_records"]) == 1 and not sheet["parsed_output"]["records"]
    assert all(r["masked_fraction"]["value"] is None for r in rows["records"])
    assert "maskinfo_bare_interval_multirecord_unresolved" in {f["code"] for f in sheet["failures"]}
    sheet, rows = build("nucleotide_binary_parsed")
    assert all(r["masked_fraction"]["value"] is None for r in rows["records"])
    assert not sheet["parsed_output"]["known_zero_records"]


def test_failed_after_closed_record_survives_only_with_independent_binding():
    _, _, data = retained("nucleotide_xml_parsed")
    data = data[:data.index(b"        <Seq-loc>", data.index(b"        <Seq-loc>") + 1)]
    binding = [{"output_record_ordinal": 0, "input_record_key": "input#/records/0", "basis": "caller_declared"}]
    sheet, rows = build("nucleotide_xml_parsed", output_bytes=data, state="failed", complete=False, bindings=binding)
    assert rows["records"][0]["masked_positions"]["value"] == 5
    assert sheet["parsed_output"]["records"][0]["association"] == "caller_declared"
    binding[0]["basis"] = "native_masked_input_iteration"
    unproved, unproved_rows = build("nucleotide_xml_parsed", output_bytes=data, state="failed", complete=False, bindings=binding)
    assert not unproved["parsed_output"]["records"]
    assert unproved_rows["records"][0]["masked_positions"]["value"] is None
    assert not sheet["parsed_output"]["known_zero_records"]
    assert rows["records"][1]["masked_fraction"]["value"] is None
    sheet, rows = build("nucleotide_xml_parsed", output_bytes=data, state="failed", complete=False)
    assert rows["records"][0]["masked_positions"]["value"] is None


@pytest.mark.parametrize("change", [lambda b: b.replace(b">3</Seq-interval_to>", b">30</Seq-interval_to>", 1),
    lambda b: b.replace(b">2</Seq-interval_from>", b">1</Seq-interval_from>", 1),
    lambda b: b.replace(b">mask_a</Object-id_str>", b">wrong</Object-id_str>")])
def test_source_conflict_prevents_order_proof_and_any_omission_inference(change):
    _, _, data = retained("nucleotide_xml_parsed")
    sheet, rows = build("nucleotide_xml_parsed", output_bytes=change(data))
    assert not sheet["parsed_output"]["known_zero_records"]
    assert not sheet["parsed_output"]["records"]
    assert all(r["masked_positions"]["value"] is None for r in rows["records"])


def test_schema_exact_fields_and_explicit_molecule():
    case, _, _ = retained("protein_xml")
    op = operation(case)
    assert sequence_masking_molecule(op) == "protein"
    schema = sequence_masking_operation_schema(program="convert2blastmask", mode="convert_mask")
    jsonschema.validate(op, schema)
    op["requested_parameters"]["masking_options"] = ""
    assert core("Operation", op) == op
    for path, value in [("molecule", None), ("input_mask_basis", "unknown"), ("masking_style", "soft")]:
        bad = deepcopy(op); bad[path] = value
        with pytest.raises(ContractError):
            core("Operation", bad)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)
    for name in ("masking_algorithm", "masking_options"):
        bad = deepcopy(op); bad["requested_parameters"][name] = None
        with pytest.raises(ContractError):
            core("Operation", bad)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)


def test_saved_recalculation_denies_io_and_rejects_forged_omission_or_locator():
    sheet, expected = build("nucleotide_xml_parsed")
    saved = json.loads(json.dumps(sheet))
    def denied(*args, **kwargs):
        raise AssertionError("saved calculation attempted I/O")
    with patch.object(builtins, "open", denied), patch.object(io, "open", denied), patch.object(socket, "socket", denied), patch.object(subprocess, "Popen", denied):
        assert calculate_sequence_masking_components(saved) == expected
    for mutate in (lambda s: s["parsed_output"]["known_zero_records"][0].update(input_record_key="input#/records/0"),
                   lambda s: s["parsed_output"]["records"][1].update(output_record_ordinal=9),
                   lambda s: s["parsed_output"]["records"][0]["output_locator"].update(byte_offset=0),
                   lambda s: s["native_outcome"].update(state="unknown"),
                   lambda s: s["parsed_output"]["native_maskinfo"]["roots"][0].update(algorithm_id=99),
                   lambda s: s["parsed_output"]["native_maskinfo"]["records"][0]["intervals"][0].update(start=1)):
        bad = deepcopy(sheet); mutate(bad)
        with pytest.raises(ContractError):
            calculate_sequence_masking_components(bad)


def test_projection_copies_exact_components_and_fulfills_known_zero_native_absence():
    for name in ("nucleotide_xml_parsed", "protein_xml"):
        sheet, calculated = build(name)
        selector = {"version": "native_blast_masking_result_selector_v1", "mode": "native_result",
            "records": {"mode": "all"}, "quantities": list(QUANTITIES), "statistics_fields": [], "statistics_unit_codes": [],
            "include_checks": True, "artifacts": [], "saved_data": [], "saved_sheet_ref": None}
        projection = project_masking_result(source_ref="result", operation=sheet["operation"], native_outcome=sheet["native_outcome"],
            sheet=sheet, calculations=calculated, statistics=None, occurrences=[sheet["inputs"][0]["occurrence"], sheet["parsed_output"]["occurrence"]],
            selector=selector, failures=[], saved_data=[])
        assert projection["status"]["state"] == "complete"
        by_key = {r["record_key"]: r for r in calculated["records"]}
        assert all(r["value"] == by_key[r["record_key"]][r["quantity"]] for r in projection["quantities"])
        assert projection["artifacts"] == []


@pytest.mark.parametrize("case_id", ["dustmasker_interval", "dustmasker_soft", "dustmasker_hard",
    "segmasker_interval", "segmasker_soft", "windowmasker_interval", "windowmasker_soft"])
def test_legacy_serialized_sheets_and_components_equal_original_097_implementation(case_id):
    import importlib.util
    from pathlib import Path
    import test_sequence_masking as legacy_tests
    from gene_annotation_episode import sequence_masking_inputs as current_inputs
    from gene_annotation_episode.sequence_masking_calculations import calculate_sequence_masking_components as current_calculate
    root = Path(__file__).resolve().parents[1]
    baseline = root / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check097_blast_mask_conversion_formats/source_snapshot/gene_annotation_episode"
    def original_module(name):
        spec = importlib.util.spec_from_file_location("gene_annotation_episode._legacy639_" + name, baseline / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    original_inputs = original_module("sequence_masking_inputs")
    original_calculate = original_module("sequence_masking_calculations").calculate_sequence_masking_components
    actual = legacy_tests.native_sheet(case_id)
    with patch.object(legacy_tests, "parse_masking_input_fasta", original_inputs.parse_masking_input_fasta), \
         patch.object(legacy_tests, "parse_sequence_masking_output", original_inputs.parse_sequence_masking_output), \
         patch.object(legacy_tests, "populate_sequence_masking_sheet", original_inputs.populate_sequence_masking_sheet), \
         patch.object(legacy_tests, "calculate_sequence_masking_components", original_calculate):
        expected = legacy_tests.native_sheet(case_id)
    assert actual == expected
    assert json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)
    assert "native_maskinfo" not in actual[0]["parsed_output"]


def test_explicit_native_order_binding_cannot_remap_the_complete_masked_population():
    binding = [{"output_record_ordinal": 0, "input_record_key": "input#/records/2", "basis": "native_masked_input_iteration"}]
    sheet, rows = build("nucleotide_xml_parsed", bindings=binding)
    assert sheet["parsed_output"]["unassigned_records"][0]["output_record_ordinal"] == 0
    assert rows["records"][0]["masked_positions"]["value"] is None
    assert not sheet["parsed_output"]["known_zero_records"]


def test_declared_options_mismatch_and_invalid_input_cannot_prove_omission():
    def changed(op, inputs, parsed, custody, outcome):
        op["requested_parameters"]["masking_options"] = "different original declaration"
    sheet, rows = build("uppercase_only_xml", modify=changed)
    assert not sheet["parsed_output"]["known_zero_records"]
    assert rows["records"][0]["masked_fraction"]["value"] is None
    assert "maskinfo_metadata_invalid" in {f["code"] for f in sheet["failures"]}
    sheet, rows = build("uppercase_only_xml", input_bytes=b">lcl|uppercase_only\nAC-GT\n")
    assert not sheet["parsed_output"]["known_zero_records"]
    assert rows["records"][0]["input_length"]["value"] is None


@pytest.mark.parametrize("basis", ["native_masked_input_iteration", "native_single_input"])
def test_legacy_saved_shapes_do_not_acquire_conversion_association(basis):
    import test_sequence_masking as legacy_tests
    sheet, _ = legacy_tests.build(b">one\nACGT\n", b">one\n1 - 2\n")
    sheet["parsed_output"]["custody"]["order_basis"] = basis
    with pytest.raises(ContractError, match="legacy_custody_variant"):
        calculate_sequence_masking_components(sheet)
    sheet, _ = legacy_tests.build(b">one\nACGT\n", b">one\n1 - 2\n")
    sheet["parsed_output"]["records"][0]["association"] = "authenticated_single_input"
    with pytest.raises(ContractError, match="enum_value"):
        calculate_sequence_masking_components(sheet)
