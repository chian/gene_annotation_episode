"""Retained native 259 bytes plus explicitly synthetic source-grammar cases.

Only the retained little-endian 3/f fixture is authentic native producer
coverage. Constructed a--f/both-order bytes below test the documented grammar,
including malformed/truncated representations; they are not biological data.
"""
import hashlib
import json
import math
from pathlib import Path
import struct

import pytest

from gene_annotation_episode.hmmer_model_binary import decode_hmmer3_binary
from gene_annotation_episode.hmmer_model_data import ISSUE_CODES, extract_hmmer_models


NATIVE = Path(__file__).resolve().parents[1] / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/native"
MAGICS = dict(zip("abcdef", (0xE8EDEDB6, 0xE8EDEDB7, 0xE8EDEDB8,
                              0xE8EDEDB9, 0xE8EDEDB0, 0xE8EDEDBA)))


def occurrence(data, **updates):
    return {"occurrence_id": "output/models/0", "direction": "output", "role": "models",
            "ordinal": 0, "artifact_ref": "retained:binary", "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "completeness": "complete", **updates}


def extract(data, **updates):
    return extract_hmmer_models(data, occurrence=occurrence(data, **updates), format="hmmer_binary")


def codes(result):
    return {issue["code"] for issue in result["issues"]}


def synthetic(*, revision="f", order="little", flags=0, alphabet_type=2,
              nseq=3, effn=2.5, maxl=-1, name=b"same", acc=b"acc", desc=b"description",
              com=None, date=b"", stats=None):
    """Independent two-position grammar fixture in actual native write order."""
    prefix = "<" if order == "little" else ">"
    chunks, offsets = [], {}
    def put(field, kind, value):
        offsets[field] = sum(map(len, chunks))
        chunks.append(struct.pack(prefix + kind, value))
    def text(field, value):
        raw = b"" if value is None else value + b"\0"
        put(field + ".length", "i", len(raw))
        offsets[field] = sum(map(len, chunks))
        chunks.append(raw)
    def vector(field, values):
        for index, value in enumerate(values):
            put(field + "[" + str(index) + "]", "f", value)
    width = 20 if alphabet_type == 3 else 4
    row = [0.5, 0.25, 0.125, 0.125] + [0.0] * (width - 4)
    put("magic", "I", MAGICS[revision])
    put("flags", "i", flags)
    put("M", "i", 2)
    put("alphabet_type", "i", alphabet_type)
    for k in (1, 2):
        vector("match" + str(k), row)
    for k in (0, 1, 2):
        vector("insert" + str(k), row)
    for k in (0, 1, 2):
        vector("transitions" + str(k), [0.75, 0.125, 0.125, 0.5, 0.5, 1.0, 0.0])
    text("NAME", name)
    for field, bit, value in (("ACC", 9, acc), ("DESC", 1, desc)):
        if flags & (1 << bit):
            text(field, value)
    for field, bit, raw in (("RF", 2, b" xx\0"), ("MM", 17, b" m-\0"),
                            ("CONS", 16, b" AC\0"), ("CS", 3, b" <<\0"), ("CA", 13, b" 12\0")):
        if flags & (1 << bit):
            offsets[field] = sum(map(len, chunks))
            chunks.append(raw)
    text("COM", com)
    put("NSEQ", "i", nseq)
    put("EFFN", "f", effn)
    if revision >= "c":
        put("MAXL", "i", maxl)
    text("DATE", date)
    if flags & (1 << 8):
        for k, value in enumerate((0, 3, 8)):
            put("MAP[" + str(k) + "]", "i", value)
    put("CKSUM", "I", 0xFEDCBA98)
    if stats is None:
        stats = [0.75, -5.0, -2.0] if revision == "a" else [-5.0, 0.75, -4.0, 0.5, -2.0, 0.25]
    vector("stats", stats)
    for k, tag in enumerate(("GA1", "GA2", "TC1", "TC2", "NC1", "NC2")):
        put(tag, "f", 10.5 + k)
    if flags & (1 << 14):
        vector("composition", row)
    return b"".join(chunks), offsets


def change(data, offset, raw):
    return data[:offset] + raw + data[offset + len(raw):]


def assert_retained_bytes(record, data):
    """Each decoded native byte has exactly one native field or body source."""
    parts = list(record["representation"]["native_fields"])
    distributions = [record["composition"], *record["initial"].values()]
    for position in record["positions"]:
        distributions.extend(position[field] for field in ("match", "insert", "transitions"))
    for distribution in distributions:
        if distribution:
            parts.extend(cell["source"] for cell in distribution["cells"])
    parts = sorted((part for part in parts if part["byte_end"] > part["byte_start"]),
                   key=lambda part: part["byte_start"])
    cursor = record["locator"]["byte_start"]
    for part in parts:
        assert part["byte_start"] == cursor
        assert bytes.fromhex(part["raw_hex"]) == data[part["byte_start"]:part["byte_end"]]
        cursor = part["byte_end"]
    assert cursor == record["locator"]["byte_end"]


def test_authentic_native_binary_bytes_identity_body_and_exact_floats():
    data = (NATIVE / "hmmconvert_binary/stdout.log").read_bytes()
    assert hashlib.sha256(data).hexdigest() == "4d3f4b96321b7383137f3b19814fb1c1d7310e247da4dc0b84d2f879a2cd565c"
    result = extract(data)
    assert result["population"] == {"decoded_count": 1, "complete": True, "state": "decoded"}, result["issues"]
    record = result["records"][0]
    assert record["record_key"] == "output/models/0#model/0"
    assert record["locator"] == {"artifact_ref": "retained:binary", "record_ordinal": 0,
        "byte_start": 0, "byte_end": 2725, "line_start": None, "line_end": None}
    assert record["length"] == len(record["positions"]) == 12
    assert record["sequence_count"] == 3
    assert record["engine_text"] is None
    assert record["alphabet"]["kind"] == "amino"
    assert record["representation"]["binary_layout"] == "i32_u32_ieee754_binary32"
    assert record["positions"][0]["match"]["cells"][0]["probability"] == 1.0
    assert record["positions"][0]["match"]["cells"][1]["probability"] == 0.0
    cell = record["positions"][4]["match"]["cells"][4]
    assert cell == {"token": None, "negative_log_probability": None,
        "probability": 0.666663408279419, "state": "finite", "source": {
            "encoding": "ieee754_binary32_probability", "raw_hex": "74aa2a3f",
            "byte_start": 352, "byte_end": 356}}
    assert all(header["line"] is None for header in record["headers"])
    assert_retained_bytes(record, data)
    assert json.loads(json.dumps(result, allow_nan=False)) == result


@pytest.mark.parametrize("revision", list("abcdef"))
@pytest.mark.parametrize("order", ["little", "big"])
def test_synthetic_all_revisions_orders_and_flag_payloads(revision, order):
    data, offsets = synthetic(revision=revision, order=order, flags=(1 << 18) - 1)
    result = extract(data)
    assert result["population"]["complete"] is True, result["issues"]
    record = result["records"][0]
    assert record["format_tag"] == "HMMER3/" + revision
    assert record["representation"]["byte_order"] == order
    assert record["checksum"] == 0xFEDCBA98
    assert record["positions"][0]["annotations"] == {
        "RF": {"token": "x", "value": "x"}, "MM": {"token": "m", "value": "m"},
        "CONS": {"token": "A", "value": "A"}, "CS": {"token": "<", "value": "<"},
        "CA": {"token": "1", "value": "1"}, "MAP": {"token": "3", "value": 3}}
    assert record["flags"]["CA"] is True
    assert record["cutoffs"]["GA"]["values"] == [10.5, 11.5]
    assert len(record["composition"]["cells"]) == 4
    if revision == "a":
        assert [item["statistic"] for item in record["calibration"]] == ["LAMBDA", "MU", "TAU"]
        assert [item["parameters"][0]["value"] for item in record["calibration"]] == [0.75, -5.0, -2.0]
    else:
        assert [item["statistic"] for item in record["calibration"]] == ["MSV", "VITERBI", "FORWARD"]
    fields = {item["field"]: item for item in record["representation"]["native_fields"]}
    assert ("MAXL" in fields) == (revision >= "c")
    assert fields["COM"]["state"] == "native_missing_sentinel"
    assert fields["COM"]["value"] is None
    assert fields["DATE"]["value"] == ""
    assert fields["DATE"]["raw_hex"] == "00"
    assert fields["RF"]["raw_hex"] == "20787800"
    assert fields["RF"]["byte_start"] == offsets["RF"]
    assert_retained_bytes(record, data)


@pytest.mark.parametrize("alphabet_type,kind,width", [(1, "RNA", 4), (2, "DNA", 4), (3, "amino", 20)])
def test_synthetic_alphabets_and_absent_consensus_are_not_invented(alphabet_type, kind, width):
    data, _ = synthetic(revision="a", alphabet_type=alphabet_type)
    result = extract(data)
    assert result["population"]["complete"] is True
    record = result["records"][0]
    assert record["alphabet"]["kind"] == kind
    assert len(record["positions"][0]["match"]["cells"]) == width
    assert record["positions"][0]["annotations"] == {}
    assert record["calibration"] == [] and record["cutoffs"] == {}
    assert record["checksum"] is record["composition"] is None
    assert record["flags"]["CONS"] is False
    fields = record["representation"]["native_fields"]
    assert next(field for field in fields if field["field"] == "CKSUM")["state"] == "unused"
    assert all(field["state"] == "unused" for field in fields if field["field"].startswith("STATS."))


def test_unflagged_nonfinite_slots_remain_unused_native_bytes():
    data, offsets = synthetic(stats=[float("nan")] * 6)
    result = extract(data)
    assert result["population"]["complete"] is True
    record = result["records"][0]
    field = next(item for item in record["representation"]["native_fields"] if item["field"] == "STATS.MMU")
    assert field["state"] == "unused" and field["value"] is None
    assert field["raw_hex"] == data[offsets["stats[0]"]:offsets["stats[0]"] + 4].hex()
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("value", [-1, 0])
def test_native_missing_sentinels_differ_from_measured_zero(value):
    data, _ = synthetic(nseq=value, effn=value, maxl=value)
    result = extract(data)
    assert result["population"]["complete"] is True
    record = result["records"][0]
    expected = None if value == -1 else 0
    assert record["sequence_count"] == record["effective_sequence_count"] == record["maximum_length"] == expected
    fields = {row["field"]: row for row in record["representation"]["native_fields"]}
    assert fields["NSEQ"]["value"] == value
    assert fields["NSEQ"]["state"] == ("native_missing_sentinel" if value == -1 else "present")


@pytest.mark.parametrize("raw", [bytes.fromhex("00000080"), bytes.fromhex("01000000")])
def test_signed_zero_and_smallest_subnormal_keep_original_bits(raw):
    data, offsets = synthetic()
    result = extract(change(data, offsets["match1[0]"], raw))
    cell = result["records"][0]["positions"][0]["match"]["cells"][0]
    assert cell["source"]["raw_hex"] == raw.hex()
    assert struct.pack("<f", cell["probability"]) == raw
    assert result["population"]["complete"] is True
    if raw == bytes.fromhex("00000080"):
        assert math.copysign(1, cell["probability"]) == -1


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_probability_retains_raw_bytes_and_later_body(value):
    data, offsets = synthetic()
    raw = struct.pack("<f", value)
    result = extract(change(data, offsets["match1[0]"], raw))
    record = result["records"][0]
    assert record["terminated"] is True and record["sequence_count"] == 3
    cell = record["positions"][0]["match"]["cells"][0]
    assert cell["probability"] is None and cell["state"] == "invalid"
    assert cell["source"]["raw_hex"] == raw.hex()
    assert result["population"]["state"] == "partial"
    assert "binary_probability_invalid" in codes(result)
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("field,raw,code", [
    ("M", struct.pack("<i", -2), "binary_length_invalid"),
    ("alphabet_type", struct.pack("<i", 99), "alphabet_invalid"),
    ("flags", struct.pack("<i", 1 << 20), "binary_flags_unknown"),
    ("NAME.length", struct.pack("<i", -1), "binary_length_invalid"),
    ("NSEQ", struct.pack("<i", -2), "binary_native_value_invalid"),
    ("EFFN", struct.pack("<f", float("inf")), "binary_native_value_invalid"),
])
def test_corrupt_native_fields_are_localized_without_resynchronization(field, raw, code):
    data, offsets = synthetic()
    corrupted = change(data, offsets[field], raw)
    result = extract(corrupted + data)
    assert code in codes(result)
    if field in {"M", "alphabet_type", "flags", "NAME.length"}:
        assert len(result["records"]) == 1
        issue = result["records"][0]["issues"][-1]
        assert issue["code"] == "record_unterminated"
        assert bytes.fromhex(issue["details"]["remaining_raw_hex"]) == (corrupted + data)[issue["details"]["remaining_byte_start"]:]
    else:
        assert len(result["records"]) == 2
        assert result["records"][1]["issues"] == []


def test_string_and_annotation_terminators_are_not_silently_repaired():
    data, offsets = synthetic(flags=1 << 2)
    broken = change(data, offsets["NAME"] + 4, b"!")
    broken = change(broken, offsets["RF"] + 3, b"!")
    result = extract(broken)
    assert {"binary_string_invalid", "annotation_value_invalid"} <= codes(result)
    assert result["records"][0]["terminated"] is True
    assert_retained_bytes(result["records"][0], broken)


def test_each_truncation_preserves_complete_prefix_and_original_partial_bytes():
    data, _ = synthetic(flags=(1 << 18) - 1)
    baseline = extract(data)["records"][0]
    for cut in range(1, len(data)):
        content = data + data[:cut]
        result = extract(content)
        assert result["records"][0] == baseline
        assert result["population"]["complete"] is False
        assert result["population"]["state"] == "partial"
        if cut >= 4:
            record = result["records"][1]
            assert record["locator"]["byte_start"] == len(data)
            assert record["locator"]["byte_end"] == len(content)
            assert record["terminated"] is False
            assert_retained_bytes(record, content)
        assert codes(result) <= ISSUE_CODES
        json.dumps(result, allow_nan=False)


def test_untrusted_positive_dimensions_do_not_allocate_from_declared_model_size():
    data, offsets = synthetic()
    data = change(data[:18], offsets["M"], struct.pack("<i", 2**31 - 1))
    result = extract(data)
    record = result["records"][0]
    assert record["length"] == 2**31 - 1
    assert len(record["positions"]) == 1
    assert record["positions"][0]["match"]["cells"][0]["source"]["raw_hex"] == data[16:18].hex()
    assert "binary_field_truncated" in codes(result)


def test_duplicate_names_and_identical_artifact_occurrences_preserve_ordinals():
    data, _ = synthetic()
    result = extract(data + data)
    assert result["population"] == {"decoded_count": 2, "complete": True, "state": "decoded"}
    assert [r["record_key"] for r in result["records"]] == ["output/models/0#model/0", "output/models/0#model/1"]
    assert result["records"][1]["locator"]["byte_start"] == len(data)
    other = extract(data, occurrence_id="input/models/3", direction="input", ordinal=3)
    assert other["records"][0]["record_key"] == "input/models/3#model/0"
    assert other["occurrence"]["sha256"] == extract(data)["occurrence"]["sha256"]


@pytest.mark.parametrize("next_options", [{"revision": "e"}, {"order": "big"}])
def test_recognized_stream_layout_change_stops_at_exact_known_boundary(next_options):
    first, _ = synthetic()
    second, _ = synthetic(**next_options)
    result = extract(first + second)
    assert result["records"] == extract(first)["records"]
    assert result["population"] == {"decoded_count": 1, "complete": False, "state": "partial"}
    issue = result["issues"][-1]
    assert issue["code"] == "binary_stream_layout_changed"
    assert issue["details"]["byte_start"] == len(first)
    assert issue["details"]["raw_hex"] == second.hex()


@pytest.mark.parametrize("order", ["little", "big"])
@pytest.mark.parametrize("magic", list(range(0xE8EDEDB1, 0xE8EDEDB6)))
def test_historical_binary_layouts_stay_explicitly_unsupported(magic, order):
    data = magic.to_bytes(4, order) + b"historical native bytes"
    result = extract(data)
    assert result["population"] == {"decoded_count": None, "complete": False, "state": "unsupported"}
    assert result["records"] == [] and "decoder_unavailable" in codes(result)


def test_empty_and_unknown_binary_population_do_not_share_zero():
    assert extract(b"")["population"] == {"decoded_count": 0, "complete": True, "state": "decoded"}
    result = extract(b"\xff\xff\xff\xff")
    assert result["population"] == {"decoded_count": None, "complete": False, "state": "unsupported"}
    assert "binary_layout_unsupported" in codes(result)


def test_public_dispatch_preserves_outer_capture_and_digest_validation():
    data, _ = synthetic()
    good = extract(data)
    partial = extract(data, completeness="partial")
    assert partial["records"] == good["records"]
    assert partial["population"] == {"decoded_count": 1, "complete": False, "state": "partial"}
    invalid = extract(data, sha256="0" * 64, size_bytes=1)
    assert invalid["records"] == good["records"]
    assert invalid["population"]["state"] == "invalid"
    assert {"occurrence_digest_mismatch", "occurrence_size_mismatch"} <= codes(invalid)
    inner = decode_hmmer3_binary(data, occurrence=occurrence(data))
    assert set(inner) == {"records", "issues", "population"}
    assert inner == {key: good[key] for key in inner}
