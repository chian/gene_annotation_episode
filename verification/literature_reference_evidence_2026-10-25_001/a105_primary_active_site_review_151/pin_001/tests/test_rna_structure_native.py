import importlib.util
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from gene_annotation_episode.rna_structure_contracts import validate_rna_native_record
from gene_annotation_episode.rna_structure_native import (
    parse_rna_native_record, parse_biomni_rna_prediction_text,
    populate_rna_prediction_sheet, populate_rna_feature_sheet,
)

PACKET = Path(__file__).resolve().parents[1] / "verification/tool_graders_rna_structure_core_2026-10-26_354"
SPEC = importlib.util.spec_from_file_location("rna_native_fixture_helpers", PACKET / "fixture_helpers.py")
F = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(F)


def parse(raw, mode="supplied_features", key="synthetic-rna"):
    return parse_rna_native_record(raw, format="rna_native_record_json_v1", expected_mode=mode, record_key=key)


def test_absent_native_is_different_from_actual_empty_bytes():
    absent, empty = parse(None), parse(b"")
    assert absent["raw_sha256"] is absent["raw_byte_count"] is None
    assert absent["issues"][0]["code"] == "rna_native_result_missing"
    assert empty["raw_byte_count"] == 0
    assert empty["raw_sha256"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert empty["issues"][0]["code"] == "rna_invalid_native_schema"
    request = F.feature_input()
    sheet = F.feature_sheet(request, native=absent)
    assert sheet["native_input"] is None
    assert sheet["topology"]["pairs"][0]["j"] == 8
    assert sheet["status"] == "partial"
    assert sheet["structure"]["origin"] == "supplied_unknown"
    F.retain("missing_and_empty", original_input=request, absent=absent, empty=empty, supplied_sheet=sheet)


@pytest.mark.parametrize("raw,code", [(b"", "rna_invalid_native_schema"),
    (b"{", "rna_output_truncated"), (b'{"schema":"unfinished', "rna_output_truncated"),
    (b'{"x":1,"x":2}', "rna_invalid_native_schema"),
    (b'{"x":NaN}', "rna_nonfinite_energy"), (b'{"x":Infinity}', "rna_nonfinite_energy"),
    (b"\xff", "rna_invalid_native_schema"), (b"[]", "rna_invalid_native_schema"),
    (b"Total estimated free energy: -6.30 kcal/mol", "rna_invalid_native_schema")])
def test_wrong_missing_and_malformed_formats_are_qualified(raw, code):
    result = parse(raw)
    assert result["status"] == "invalid"
    assert result["record"] is None
    assert result["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["raw_byte_count"] == len(raw)
    assert result["issues"][0]["code"] == code
    F.retain("malformed_" + hashlib.sha256(raw).hexdigest(), raw_hex=raw.hex(), parse=result)


def test_fully_parsed_native_failure_is_valid_parsing_and_retains_supplied_topology():
    request = F.feature_input(energy_mode="viennarna_evaluate")
    record = F.native_record(request, native_failure="rna_native_dependency_missing")
    record["status"] = "failed"
    assert validate_rna_native_record(record, expected_mode="supplied_features") == record
    native = F.parsed(record)
    assert native["status"] == "valid"
    assert native["record"]["status"] == "failed"
    sheet = F.feature_sheet(request, native=native)
    assert len(sheet["topology"]["pairs"]) == 3
    assert sheet["native_evaluation"]["state"] == "failed"
    assert sheet["native_evaluation"]["reason"] == "rna_native_dependency_missing"
    assert sheet["native_mfe"]["state"] == "not_requested"
    F.retain("native_dependency_failure", original_input=request, native_record=record, parse=native, sheet=sheet)


def test_native_prediction_failure_does_not_guess_an_all_dot_structure():
    request = F.prediction_input()
    native = F.parsed(F.native_record(request, native_failure="rna_native_dependency_missing"))
    sheet = populate_rna_prediction_sheet(native, record_key=request["record_key"], original_input=request,
        model_metadata=None, subject_binding=None)
    assert native["status"] == "valid"
    assert sheet["analysis_sequence"]["length_nt"] == 9
    assert sheet["topology"] is sheet["structure"] is sheet["sequence_pairs"] is None
    assert sheet["status"] == "invalid"
    F.retain("prediction_failure", original_input=request, parse=native, sheet=sheet)


def test_invalid_original_container_and_absent_native_still_use_original_job_identity():
    for mode, populate in (("mfe_prediction", populate_rna_prediction_sheet), ("supplied_features", populate_rna_feature_sheet)):
        native = parse(None, mode=mode, key="actual-job-key")
        sheet = populate(native, record_key="actual-job-key", original_input=None, model_metadata=None, subject_binding=None)
        assert sheet["record_key"] == "actual-job-key"
        assert sheet["original_input"] is sheet["topology"] is sheet["analysis_sequence"] is None
        assert sheet["status"] == "invalid"
        F.retain("missing_original_" + mode, native=native, sheet=sheet)


def test_corrupt_topology_table_does_not_overwrite_independent_supplied_input():
    request = F.feature_input()
    record = F.native_record(request)
    record["topology"]["pairs"][0]["j"] = 7
    native = F.parsed(record)
    assert native["status"] == "partial"
    assert native["record"]["topology"] is None
    assert "rna_topology_table_mismatch" in [row["code"] for row in native["issues"]]
    sheet = F.feature_sheet(request, native=native)
    assert sheet["topology"]["pairs"][0]["j"] == 8
    assert sheet["native_evaluation"]["state"] == "not_requested"
    assert sheet["status"] == "partial"
    F.retain("corrupt_native_topology", original_input=request, malformed_native=record, parse=native, sheet=sheet)


def test_native_record_key_and_independent_original_sequence_are_checked():
    record = F.native_record(F.feature_input())
    raw = json.dumps(record).encode()
    assert parse(raw, key="other-job")["issues"][0]["code"] == "rna_input_identity_mismatch"
    with pytest.raises(ValueError, match="rna_input_identity_mismatch"):
        populate_rna_feature_sheet(F.parsed(record), record_key="other-job", original_input=F.feature_input(), model_metadata=None, subject_binding=None)
    request = F.prediction_input()
    native = F.parsed(F.native_record(request, prediction_structure="(((...)))", energy=-1.25))
    changed = F.prediction_input("AAAUUUAAA")
    sheet = populate_rna_prediction_sheet(native, record_key=request["record_key"], original_input=changed,
        model_metadata=None, subject_binding=None)
    assert sheet["topology"] is None
    assert sheet["native_mfe"]["value"] is None
    assert sheet["native_mfe"]["reason"] == "rna_input_identity_mismatch"


@pytest.mark.parametrize("energy_text,expected", [("-5.00", -5.0), ("-1.23456789012345", -1.23456789012345),
    ("-5e-1", -0.5), ("+2.5E+1", 25.0), ("0.0", 0.0), ("-0.0", -0.0)])
def test_retained_legacy_numeric_text_is_copied_without_rounding(energy_text, expected):
    # Synthetic serialization in the inspected real wrapper's exact file format.
    raw = f"Sequence: GGGAAACCC\nStructure: (((...)))\nMinimum Free Energy: {energy_text} kcal/mol\n".encode()
    native = parse_biomni_rna_prediction_text(raw, record_key="legacy-case", expected_sequence="GGGAAACCC")
    assert native["status"] == "valid"
    assert native["record"]["native_mfe"]["value"] == expected
    assert native["record"]["native_mfe"]["numeric_text"] == energy_text
    assert native["record"]["input"] is native["record"]["model"] is None
    request = F.prediction_input(record_key="legacy-case")
    sheet = populate_rna_prediction_sheet(native, record_key="legacy-case", original_input=request, model_metadata=None, subject_binding=None)
    assert sheet["native_mfe"]["numeric_text"] == energy_text
    assert sheet["status"] == "partial"
    F.retain("legacy_energy_" + energy_text.replace("+", "plus").replace("-", "minus"), raw_utf8=raw.decode(), native=native, sheet=sheet)


def test_generic_legacy_dispatch_requires_independent_context_and_matches_direct_parser():
    raw = b"Sequence: GGGAAACCC\nStructure: (((...)))\nMinimum Free Energy: -1.2 kcal/mol\n"
    absent = parse_rna_native_record(raw, format="biomni_rna_structure_text_v0", expected_mode="mfe_prediction", record_key="x")
    assert absent["issues"][0]["code"] == "rna_legacy_context_missing"
    generic = parse_rna_native_record(raw, format="biomni_rna_structure_text_v0", expected_mode="mfe_prediction", record_key="x", expected_sequence="GGGAAACCC")
    direct = parse_biomni_rna_prediction_text(raw, record_key="x", expected_sequence="GGGAAACCC")
    assert generic == direct
    bad = parse_biomni_rna_prediction_text(raw, record_key="x", expected_sequence="GGGAAAUUU")
    assert bad["issues"][0]["code"] == "rna_input_identity_mismatch"


@pytest.mark.parametrize("text", ["nan", "inf", "-inf", "1e999"])
def test_nonfinite_legacy_values_are_failures_not_energies(text):
    raw = f"Sequence: GGGAAACCC\nStructure: (((...)))\nMinimum Free Energy: {text} kcal/mol\n".encode()
    native = parse_biomni_rna_prediction_text(raw, record_key="x", expected_sequence="GGGAAACCC")
    assert native["record"] is None
    assert native["issues"][0]["code"] == "rna_nonfinite_energy"


def test_native_energy_association_and_units_are_validated():
    request = F.prediction_input()
    record = F.native_record(request, prediction_structure="(((...)))", energy=-1.25)
    record["native_mfe"]["structure_key"] = "other:structure"
    native = F.parsed(record)
    assert native["status"] == "partial"
    assert native["record"]["native_mfe"]["value"] is None
    assert native["record"]["native_mfe"]["reason"] == "rna_energy_structure_mismatch"
    assert len(native["record"]["topology"]["pairs"]) == 3
    record = F.native_record(request, prediction_structure="(((...)))", energy=-1.25)
    record["native_mfe"]["numeric_text"] = "-1.2"
    assert F.parsed(record)["status"] == "partial"


def test_original_input_subject_binding_is_never_invented_or_silently_reassigned():
    request = F.feature_input()
    binding = {"subject_ref": "subject:x", "sequence_artifact_ref": "artifact:x", "start": 0, "end": 9, "strand": "+"}
    with pytest.raises(ValueError, match="rna_subject_binding_conflict"):
        populate_rna_feature_sheet(F.parsed(F.native_record(request)), record_key=request["record_key"], original_input=request,
            model_metadata=None, subject_binding=binding)


def test_mixed_nested_brackets_have_explicit_energy_conversion_only():
    request = F.feature_input("[{...}]", "GGAAACC", energy_mode="viennarna_evaluate")
    sheet = F.feature_sheet(request, native=F.parsed(F.native_record(request, native_failure="rna_native_dependency_missing")))
    assert sheet["structure"]["dot_bracket"] == "[{...}]"
    assert sheet["structure"]["energy_dot_bracket"] == "((...))"
    assert sheet["structure"]["energy_conversion"] == {"kind": "bracket_alphabet_to_parentheses", "index_map": [0, 1, 2, 3, 4, 5, 6]}
    assert sheet["native_evaluation"]["value"] is None
    F.retain("mixed_bracket_conversion", original_input=request, sheet=sheet)


@pytest.mark.parametrize("path,value", [
    (("native_evaluation", "state"), []), (("model",), []),
    (("input", "normalization"), []), (("input", "energy_mode"), {}),
    (("topology", "length_nt"), True), (("native_uncertainty",), []),
    (("issues",), None), (("status",), {}),
])
def test_invalid_native_container_fields_never_escape_as_untyped_errors(path, value):
    record = F.native_record(F.feature_input(energy_mode="viennarna_evaluate"), energy=-1.5)
    destination = record
    for name in path[:-1]:
        destination = destination[name]
    destination[path[-1]] = value
    native = F.parsed(record)
    assert native["status"] in ("partial", "invalid")
    assert native["issues"]
    if native["record"] is not None:
        validate_rna_native_record(native["record"], expected_mode="supplied_features")
    F.retain("invalid_field_" + "_".join(path), synthetic_input_record=record, parse=native)


def test_selected_energy_failure_cannot_be_relabelled_not_requested():
    request = F.feature_input(energy_mode="viennarna_evaluate")
    record = F.native_record(request, native_failure="rna_native_dependency_missing")
    record["native_evaluation"] = F.unavailable_energy()
    with pytest.raises(ValueError, match="rna_native_result_incompatible"):
        validate_rna_native_record(record, expected_mode="supplied_features")
    parsed = F.parsed(record)
    assert parsed["status"] == "partial"
    assert parsed["record"]["native_evaluation"]["state"] == "incompatible"
    assert len(parsed["record"]["topology"]["pairs"]) == 3


def test_missing_retained_model_is_explicit_and_not_reconstructed_from_environment():
    request = F.prediction_input()
    record = F.native_record(request, prediction_structure="(((...)))", energy=-1.25)
    record["model"] = None
    native = F.parsed(record)
    assert native["status"] == "partial"
    assert native["record"]["model"] is None
    assert native["record"]["native_mfe"]["value"] == -1.25
    assert "rna_model_snapshot_missing" in [row["code"] for row in native["issues"]]
    record = F.native_record(request, prediction_structure="(((...)))", energy=-1.25)
    record["native_mfe"]["model_key"] = None
    native = F.parsed(record)
    assert native["status"] == "partial"
    assert native["record"]["native_mfe"]["value"] is None


def test_rejected_native_sentinel_remains_a_failure_without_a_heuristic_threshold():
    request = F.feature_input(energy_mode="viennarna_evaluate")
    record = F.native_record(request, native_failure="rna_native_failed")
    native = F.parsed(record)
    sheet = F.feature_sheet(request, native=native)
    assert sheet["native_evaluation"]["value"] is None
    assert sheet["native_evaluation"]["reason"] == "rna_native_failed"
    # The actual producer owns API-specific sentinel classification; the pure
    # reader never scrapes or converts this retained diagnostic into an energy.
    F.retain("rejected_native_sentinel", qualification="Synthetic rejected-return diagnostic; no native call",
        retained_stdout={"schema": "rna_raw_native_return_v1", "record_key": request["record_key"],
            "call": "fold_compound.eval_structure", "structure_value": None, "energy_repr": "inf"},
        native_record=record, parsed=native, sheet=sheet)
