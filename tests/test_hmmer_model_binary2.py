"""HMMER2.3.2-layout engineering controls, not native producer evidence.

Bytes are explicitly packed from the primary WriteBinHMM field order. No test
calls HMMER, converts a model or claims an executed historical producer/ABI.
Existing numerical authorities are exercised for source admission and topology,
not reimplemented as a second entropy/probability oracle.
"""
from copy import deepcopy
import hashlib
import json
import struct

import pytest

from gene_annotation_episode.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.hmmer_model_binary2 import MAGIC, binary2_header, decode_hmmer2_binary
from gene_annotation_episode.hmmer_model_calculations import (
    calculate_hmmer_model_components, validate_hmmer_probability_cell, validate_hmmer_probability_vector,
)


def packed(*, order="little", alphabet=2, annotated=True, evd=True, scale=0.7, unused=float("nan")):
    """Engineered field declarations mirror the complete upstream writer order."""
    prefix = "<" if order == "little" else ">"
    output, offsets = bytearray(), {}
    flags = (1 << 5) | (1 << 1) | (1 << 9) | (1 << 10) | (1 << 11) | (1 << 12)
    if annotated: flags |= (1 << 2) | (1 << 3) | (1 << 8)
    if evd: flags |= 1 << 7
    width = 4 if alphabet == 2 else 20
    def add(field, raw):
        offsets[field] = len(output); output.extend(raw)
    def scalar(field, value, kind="i"):
        add(field, struct.pack(prefix + kind, value))
    def text(field, value):
        raw = b"" if value is None else value.encode() + b"\0"
        scalar(field + ".length", len(raw)); add(field, raw)
    scalar("magic", MAGIC, "I"); scalar("flags", flags)
    text("NAME", "engineered_h2"); text("ACC", "fixture.1"); text("DESC", "literal engineered model")
    scalar("M", 2); scalar("alphabet_type", alphabet)
    if annotated:
        add("RF", b"\xffxy"); add("CS", b"\0ab")
        for position, value in enumerate([-77, 3, 8]): scalar("MAP[" + str(position) + "]", value)
    text("COM", "first command\nsecond command"); scalar("NSEQ", 3)
    text("DATE", None); scalar("CKSUM", -12345)
    for name in ["GA", "TC", "NC"]:
        scalar(name + "1", 3.25, "f"); scalar(name + "2", 1.5, "f")
    for index in range(8): scalar("XT[" + str(index) + "]", 0.5, "f")
    scalar("NULT.p1", 0.9, "f")
    for index in range(width): scalar("NULE[" + str(index) + "]", 1 / width, "f")
    if evd: scalar("EVD.mu", -2.5, "f"); scalar("EVD.lambda", scale, "f")
    scalar("TBD1", 0.25, "f")
    for name, values in [("begin", [unused, 0.75, 0.0]), ("end", [unused, 0.25, 1.0])]:
        for position, value in enumerate(values): scalar(name + "[" + str(position) + "]", value, "f")
    for position in range(2):
        for index in range(width): scalar("match[" + str(position) + "][" + str(index) + "]", 1 / width, "f")
    for index in range(width): scalar("insert[0][" + str(index) + "]", 1 / width, "f")
    for index, value in enumerate([0.25, 0.25, 0.25, 0.5, 0.5, 0.5, 0.5]): scalar("transitions[0][" + str(index) + "]", value, "f")
    return bytes(output), offsets


def occurrence(raw, **changes):
    return {"occurrence_id": "input/models/0", "direction": "input", "role": "models",
        "ordinal": 0, "artifact_ref": "engineered:binary2", "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw), "completeness": "complete", **changes}


def extract(raw, **changes):
    return extract_hmmer_models(raw, occurrence=occurrence(raw, **changes), format="hmmer_binary")


@pytest.mark.parametrize("order,alphabet", [(order, alphabet) for order in ["little", "big"] for alphabet in [2, 3]])
def test_declared_original_binary2_layout_retains_actual_fields_probability_bytes_and_configured_topology(order, alphabet):
    raw, offsets = packed(order=order, alphabet=alphabet)
    result = extract(raw)
    assert result["population"] == {"decoded_count": 1, "complete": True, "state": "decoded"}, result["issues"]
    record, = result["records"]
    assert record["format_tag"] == "HMMER2.0" and record["engine_text"] is None
    assert record["locator"]["line_start"] is record["locator"]["line_end"] is None
    assert record["length"] == 2 and record["sequence_count"] == 3
    assert record["effective_sequence_count"] is record["checksum"] is None
    assert record["representation"]["encoding"] == "hmmer2_binary_probability"
    assert record["representation"]["byte_order"] == order
    assert record["alphabet"]["symbols"] == list("ACGT" if alphabet == 2 else "ACDEFGHIKLMNPQRSTVWY")
    assert record["initial"] == {"insert": None, "transitions": None}
    assert record["positions"][-1]["insert"] is record["positions"][-1]["transitions"] is None
    assert [p["annotations"]["MAP"]["value"] for p in record["positions"]] == [3, 8]
    assert [p["annotations"]["RF"]["value"] for p in record["positions"]] == ["x", "y"]
    legacy = record["representation"]["legacy"]
    assert legacy["checksum"]["value"] == -12345
    assert legacy["null_transitions"]["symbols"] == ["slot_0"]
    assert legacy["begin_transitions"]["symbols"] == ["B->D1"]
    assert len(legacy["entry_exit"]) == 2 and legacy["entry_exit"][1]["cells"][1]["probability"] == 1.0
    header = binary2_header(record)
    assert header["body_start"] == offsets["match[0][0]"]
    assert header["fields"]["begin[0]"]["state"] == "unused"
    assert header["fields"]["begin[0]"]["value"] is None
    assert header["fields"]["RF"]["raw_hex"] == "ff7879"
    cell = record["positions"][0]["match"]["cells"][0]
    assert cell["source"]["byte_start"] == offsets["match[0][0]"] and cell["token"] is None
    assert cell["source"]["raw_hex"] == raw[offsets["match[0][0]"]:offsets["match[0][0]"] + 4].hex()
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_binary2_evd_is_one_native_mu_lambda_pair_without_invented_hmmer3_calibrations():
    raw, _ = packed(); record = extract(raw)["records"][0]
    calibration, = record["calibration"]
    assert calibration["mode"] is None and calibration["statistic"] == "EVD"
    assert [(p["name"], p["unit"]) for p in calibration["parameters"]] == [("mu", "bit"), ("lambda", "inverse_bit")]
    assert calibration["parameters"][0]["value"] == -2.5
    expected = struct.unpack("<f", struct.pack("<f", 0.7))[0]
    assert calibration["parameters"][1]["value"] == expected
    assert record["representation"]["legacy"]["evd"][0]["values"] == [-2.5, expected]
    assert not any(row["statistic"] in {"MSV", "VITERBI", "FORWARD"} for row in record["calibration"])


@pytest.mark.parametrize("annotated,evd", [(False, False), (False, True), (True, False)])
def test_optional_payload_flags_define_exact_framing_without_default_annotations_or_calibration(annotated, evd):
    raw, _ = packed(annotated=annotated, evd=evd); result = extract(raw); record, = result["records"]
    assert result["population"]["complete"], result["issues"]
    assert bool(record["calibration"]) is evd
    assert bool(record["positions"][0]["annotations"]) is annotated
    assert binary2_header(record) is not None


@pytest.mark.parametrize("cut", [1, 4, 9, 24, 100, -1, -9])
def test_truncation_retains_observed_prefix_without_padding_or_searching_a_new_magic(cut):
    raw, _ = packed(); cut = len(raw) + cut if cut < 0 else cut
    result = extract(raw[:cut]); assert result["population"]["complete"] is False
    assert any(i["code"] == "binary_field_truncated" for i in result["issues"])
    if result["records"]:
        record = result["records"][0]
        assert record["terminated"] is False and record["locator"]["byte_end"] == cut
        assert all(len(p["match"]["cells"]) <= 4 for p in record["positions"])


@pytest.mark.parametrize("changed", ["negative-length", "unknown-flags", "unknown-alphabet", "negative-string"])
def test_unknown_or_unframeable_fields_stop_before_any_guessed_following_model(changed):
    raw, offsets = packed(); raw = bytearray(raw)
    field, value = {"negative-length": ("M", -1), "unknown-flags": ("flags", 1 << 30),
        "unknown-alphabet": ("alphabet_type", 1), "negative-string": ("NAME.length", -1)}[changed]
    raw[offsets[field]:offsets[field] + 4] = struct.pack("<i", value)
    result = extract(bytes(raw))
    assert result["population"]["complete"] is False and len(result["records"]) == 1
    assert result["records"][0]["positions"] == []
    assert any(i["code"] == "record_unterminated" for i in result["issues"])


@pytest.mark.parametrize("value", [-0.1, 1.1, float("inf"), float("nan")])
def test_invalid_native_probability_keeps_raw_cell_and_surrounding_cells_without_zero_substitution(value):
    raw, offsets = packed(); mutable = bytearray(raw); position = offsets["match[0][0]"]
    mutable[position:position + 4] = struct.pack("<f", value)
    result = extract(bytes(mutable)); cell = result["records"][0]["positions"][0]["match"]["cells"][0]
    assert cell["state"] == "invalid" and cell["probability"] is None
    assert cell["source"]["raw_hex"] == bytes(mutable[position:position + 4]).hex()
    assert result["records"][0]["positions"][1]["match"]["cells"][0]["probability"] == 0.25
    assert result["records"][0]["terminated"] and result["population"]["state"] == "partial"


@pytest.mark.parametrize("scale", [0.0, -1.0, float("inf"), float("nan")])
def test_invalid_native_evd_scale_stays_raw_and_never_fills_other_calibrations(scale):
    raw, offsets = packed(scale=scale); result = extract(raw); record = result["records"][0]
    assert record["calibration"] == [] and record["representation"]["legacy"]["evd"][0]["values"][1] is None
    native = next(v for v in record["representation"]["native_fields"] if v["field"] == "EVD.lambda")
    assert native["raw_hex"] == raw[offsets["EVD.lambda"]:offsets["EVD.lambda"] + 4].hex()
    assert "calibration_invalid" in {i["code"] for i in result["issues"]}


def test_original_occurrence_order_multiple_models_and_layout_change_are_explicit():
    first, _ = packed(); second, _ = packed(annotated=False, evd=False)
    result = extract(first + second)
    assert result["population"]["complete"] and [r["locator"]["record_ordinal"] for r in result["records"]] == [0, 1]
    assert result["records"][1]["locator"]["byte_start"] == len(first)
    changed, _ = packed(order="big")
    mixed = extract(first + changed)
    assert mixed["population"]["complete"] is False and len(mixed["records"]) == 1
    assert "binary_stream_layout_changed" in {i["code"] for i in mixed["issues"]}


def test_capture_and_digest_qualification_are_independent_of_decoded_original_probabilities():
    raw, _ = packed(); full = extract(raw)
    partial = extract(raw, completeness="partial")
    assert partial["records"] == full["records"] and partial["population"]["state"] == "partial"
    wrong = extract(raw, sha256="0" * 64)
    assert wrong["records"] == full["records"] and wrong["population"]["state"] == "invalid"


def test_common_saved_calculator_uses_original_binary2_cells_and_retains_missing_topology_without_native_or_parser(monkeypatch):
    raw, _ = packed(); data = extract(raw); before = deepcopy(data)
    def forbidden(*a, **k): raise AssertionError("saved common calculation reparsed or read bytes")
    monkeypatch.setattr("gene_annotation_episode.hmmer_model_binary2.decode_hmmer2_binary", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    result = calculate_hmmer_model_components(data)
    row, = result["rows"]
    assert data == before and row["sequence_count"]["value"] == 3
    assert row["effective_sequence_count"]["state"] == "missing" and row["effective_sequence_ratio"]["value"] is None
    assert row["declared_length"]["value"] == 2 and row["mean_match_entropy"]["state"] == "present"
    assert row["initial"]["insert"]["mass"]["value"] is None
    assert row["positions"][-1]["insert"]["mass"]["value"] is None
    assert any(i["code"] == "transition_population_excludes_exit" for i in result["issues"])
    assert row["positions"][0]["match"]["mass"]["inputs"][0]["qualification"] == "binary_layout_interpretation"


@pytest.mark.parametrize("change", ["offset", "native-value", "native-length", "field-order", "count-alias", "body-bounds"])
def test_saved_binary2_cells_cannot_change_their_original_field_or_array_slot(change):
    raw, _ = packed(); data = extract(raw); record = data["records"][0]
    cell = record["positions"][0]["match"]["cells"][0]
    if change == "offset": cell["source"]["byte_start"] += 4; cell["source"]["byte_end"] += 4
    elif change == "native-value": next(v for v in record["representation"]["native_fields"] if v["field"] == "M")["value"] = 3
    elif change == "native-length": record["length"] = 3
    elif change == "field-order": record["representation"]["native_fields"][2:4] = list(reversed(record["representation"]["native_fields"][2:4]))
    elif change == "count-alias": next(v for v in record["representation"]["native_fields"] if v["field"] == "M")["value"] = 2.0
    else: record["locator"]["byte_end"] += 4
    result = validate_hmmer_probability_cell(cell, record=record, field="match", position_ordinal=0, cell_index=0)
    assert result["state"] == "incompatible" and result["probability"] is None


def test_original_binary2_legacy_slots_use_actual_bytes_and_do_not_synthesize_null_complements():
    raw, offsets = packed(); record = extract(raw)["records"][0]; legacy = record["representation"]["legacy"]
    for name, symbols, indices in [("null_emissions", record["alphabet"]["symbols"], tuple(range(4))),
            ("special_transitions", ["NB", "NN", "EC", "EJ", "CT", "CC", "JB", "JJ"], tuple(range(8))),
            ("null_transitions", ["slot_0"], (0,)), ("begin_transitions", ["B->D1"], (0,))]:
        checked = validate_hmmer_probability_vector(legacy[name], record=record,
            field="legacy." + name, position_ordinal=None, symbols=symbols, indices=indices)
        assert checked["state"] == "present", checked
    p1, = legacy["null_transitions"]["cells"]
    assert p1["source"]["byte_start"] == offsets["NULT.p1"]
    assert legacy["null_transitions"]["symbols"] == ["slot_0"]


def test_low_level_declared_reader_is_same_public_dispatcher_value_without_occurrence_rewriting():
    raw, _ = packed(); direct = decode_hmmer2_binary(raw, occurrence=occurrence(raw)); full = extract(raw)
    assert all(full[key] == direct[key] for key in ["records", "issues", "population"])


def test_every_original_binary2_byte_is_retained_in_native_fields_or_body_cells_exactly_once():
    raw, _ = packed(); record, = extract(raw)["records"]
    pieces = list(record["representation"]["native_fields"])
    for row in record["positions"]:
        for field in ["match", "insert", "transitions"]:
            if row[field] is not None:
                pieces.extend(cell["source"] for cell in row[field]["cells"])
    cursor = 0
    for part in sorted((p for p in pieces if p["byte_end"] > p["byte_start"]), key=lambda p: p["byte_start"]):
        assert part["byte_start"] == cursor
        assert bytes.fromhex(part["raw_hex"]) == raw[part["byte_start"]:part["byte_end"]]
        cursor = part["byte_end"]
    assert cursor == len(raw)


@pytest.mark.parametrize("annotated", [True, False])
def test_untrusted_binary2_model_length_never_allocates_an_unobserved_population(annotated):
    raw, offsets = packed(annotated=annotated)
    raw = raw[:offsets["M"]] + struct.pack("<i", 2 ** 31 - 1) + raw[offsets["M"] + 4:]
    result = extract(raw); record, = result["records"]
    assert record["length"] == 2 ** 31 - 1 and record["positions"] == []
    assert record["locator"]["byte_end"] == len(raw) and record["terminated"] is False
    assert "binary_field_truncated" in {issue["code"] for issue in result["issues"]}


def test_existing_statistics_consumer_retains_binary_layout_qualification_without_false_quantization_or_h3_occupancy():
    from gene_annotation_episode.hmmer_statistics_calculations import calculate_hmmstat_components
    from test_hmmer_statistics_data import make_sheet
    raw, _ = packed(); sheet = make_sheet(raw, b"", model_format="hmmer_binary")
    components = calculate_hmmstat_components(sheet)
    row, = components["rows"]
    inputs = row["components"]["mean_match_information"]["inputs"]
    native_inputs = [value for value in inputs if value.get("source_encoding") == "hmmer2_binary_probability"]
    assert native_inputs and all(value["qualification"] == "binary_layout_interpretation" for value in native_inputs)
    assert row["components"]["occupancy_sum"]["state"] == "incompatible"
    assert row["components"]["mean_match_entropy"] == components["model_components"]["rows"][0]["mean_match_entropy"]


@pytest.mark.parametrize("capture", ["complete", "partial", "invalid_cell"])
def test_existing_artifact_profile_separates_binary2_body_framing_capture_and_unknown_custody(capture):
    from gene_annotation_episode.hmmer_artifact_calculations import calculate_hmmer_artifact_components
    from test_hmmer_artifact_data import payload, populate
    raw, offsets = packed()
    if capture == "invalid_cell":
        position = offsets["match[0][0]"]
        raw = raw[:position] + struct.pack("<f", 2.0) + raw[position + 4:]
    original = payload(raw, "models", oid="engineered/input/models/0")
    output = payload(raw, "converted_models", "output", oid="engineered/output/converted_models/0",
        completeness="partial" if capture == "partial" else "complete")
    operation = {"program": "hmmconvert", "mode": "binary", "engine_version": "engineered-layout-control", "settings": {}}
    sheet = populate(operation, {"models": [original]}, {"converted_models": [output]})
    components = calculate_hmmer_artifact_components(sheet)
    artifact = next(row for row in components["rows"] if row["kind"] == "artifact"
        and row["occurrence_id"] == output["occurrence"]["occurrence_id"])
    assert artifact["format"] == "hmmer_binary"
    assert artifact["decoded_record_count"]["value"] == 1
    assert artifact["internal_content_state"] == {"complete": "decoded", "partial": "partial", "invalid_cell": "invalid"}[capture]
    assert artifact["authenticated_custody_state"] == "not_applicable"
    assert artifact["revision"] == "2.0"
