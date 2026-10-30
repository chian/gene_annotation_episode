"""Native 259 fixtures and explicitly synthetic error cases; no native execution."""
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_model_data import (
    ALPHABETS, ISSUE_CODES, TRANSITIONS, extract_hmmer_models,
)


NATIVE = Path(__file__).resolve().parents[1] / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/native"


def native(name="hmmbuild_protein", filename="profile.hmm"):
    return (NATIVE / name / filename).read_bytes()


def occurrence(data, **overrides):
    return {"occurrence_id": "output/models/0", "direction": "output", "role": "models",
            "ordinal": 0, "artifact_ref": "retained:protein", "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data), "completeness": "complete", **overrides}


def extract(data, **overrides):
    return extract_hmmer_models(data, occurrence=occurrence(data, **overrides), format="hmmer3_ascii")


def codes(result):
    return {item["code"] for item in result["issues"]}


def mutate_line(data, predicate, transform):
    lines = data.decode().splitlines()
    index = next(i for i, line in enumerate(lines) if predicate(line))
    lines[index] = transform(lines[index])
    return ("\n".join(lines) + "\n").encode()


def test_full_native_protein_body_and_provenance():
    data = native()
    supplied = occurrence(data)
    result = extract_hmmer_models(data, occurrence=supplied, format="hmmer3_ascii")
    assert set(result) == {"schema", "occurrence", "format", "records", "population", "issues"}
    assert result["schema"] == "hmmer_model_extraction_v1"
    assert result["occurrence"] == supplied and result["occurrence"] is not supplied
    assert result["population"] == {"decoded_count": 1, "complete": True, "state": "decoded"}
    assert result["issues"] == []
    record = result["records"][0]
    assert record["record_key"] == "output/models/0#model/0"
    assert record["locator"] == {"artifact_ref": "retained:protein", "record_ordinal": 0,
        "byte_start": 0, "byte_end": len(data), "line_start": 1, "line_end": len(data.splitlines())}
    assert record["format_tag"] == "HMMER3/f" and record["engine_text"] == "[3.4 | Aug 2023]"
    assert (record["length"], record["sequence_count"], record["effective_sequence_count"]) == (12, 3, 3.0)
    assert record["checksum"] == 1992437505
    assert record["maximum_length"] is None and record["cutoffs"] == {}
    assert record["alphabet"] == {"kind": "amino", "symbols": list("ACDEFGHIKLMNPQRSTVWY")}
    assert [p["position"] for p in record["positions"]] == list(range(1, 13))
    assert all(len(p["match"]["cells"]) == len(p["insert"]["cells"]) == 20 for p in record["positions"])
    assert all(len(p["transitions"]["cells"]) == 7 for p in record["positions"])
    assert record["initial"]["transitions"]["symbols"] == TRANSITIONS
    assert len(record["composition"]["cells"]) == len(record["initial"]["insert"]["cells"]) == 20
    position = record["positions"][4]
    assert position["annotations"] == {"MAP": {"token": "5", "value": 5},
        "CONS": {"token": "F", "value": "F"}, "RF": {"token": "x", "value": "x"},
        "MM": {"token": "-", "value": "-"}, "CS": {"token": "-", "value": "-"}}
    assert position["match"]["cells"][4]["token"] == "0.40547"
    assert position["match"]["cells"][19]["token"] == "1.09861"
    with localcontext() as context:
        context.prec = 50
        expected = float((-Decimal("0.40547")).exp())
    assert position["match"]["cells"][4]["probability"] == pytest.approx(expected, abs=1e-15)
    assert position["match"]["cells"][0] == {"token": "*", "negative_log_probability": None,
                                           "probability": 0.0, "state": "structural_zero"}
    assert json.loads(json.dumps(result, allow_nan=False)) == result


@pytest.mark.parametrize("kind,suffix", [("amino", "protein"), ("DNA", "dna"), ("RNA", "rna")])
def test_all_native_alphabets(kind, suffix):
    result = extract(native("hmmbuild_" + suffix))
    assert result["population"]["complete"] is True, result["issues"]
    record = result["records"][0]
    assert record["alphabet"] == {"kind": kind, "symbols": ALPHABETS[kind]}
    assert len(record["positions"]) == record["length"] == 12
    if kind != "amino":
        assert record["maximum_length"] > 0
    if kind == "RNA":
        assert record["cutoffs"]["GA"]["sequence"] == 10.1
        assert record["cutoffs"]["GA"]["domain"] is None
        assert record["cutoffs"]["GA"]["domain_supplied"] is False


@pytest.mark.parametrize("revision", list("abcdef"))
def test_each_native_ascii_revision_preserves_its_actual_grammar(revision):
    data = native("hmmconvert_annotated_3" + revision, "stdout.log")
    result = extract(data)
    assert result["population"]["complete"] is True, result["issues"]
    record = result["records"][0]
    expected = {"MAP", "RF", "CS"} | ({"CONS"} if revision >= "e" else set()) | ({"MM"} if revision == "f" else set())
    assert record["format_tag"] == "HMMER3/" + revision
    assert set(record["flags"]) == expected
    assert all(set(p["annotations"]) == expected for p in record["positions"])
    assert record["cutoffs"]["GA"]["values"] == [12.3, 4.5]
    assert record["cutoffs"]["TC"]["values"] == [15.6, 6.7]
    assert record["cutoffs"]["NC"]["values"] == [8.9, 2.1]
    assert record["cutoffs"]["GA"]["domain_supplied"] is True
    baseline = extract(native("hmmbuild_annotated"))["records"][0]
    for expected, actual in zip(baseline["positions"], record["positions"]):
        for field in ("match", "insert", "transitions"):
            assert actual[field]["cells"] == expected[field]["cells"]
            assert actual[field]["symbols"] == expected[field]["symbols"]
    stats = {row["statistic"]: row for row in record["calibration"]}
    if revision == "a":
        assert set(stats) == {"VLAMBDA", "VMU", "FTAU"}
        assert stats["VMU"]["parameters"] == [{"name": "mu", "token": "-5.908600", "value": -5.9086, "unit": "bit"}]
    else:
        assert set(stats) == {"MSV", "VITERBI", "FORWARD"}
        assert stats["MSV"]["parameters"][0]["value"] == -5.9086
        assert stats["VITERBI"]["parameters"][0]["value"] == -6.1309
    if revision == "f":
        assert record["positions"][1]["annotations"]["MM"]["value"] == "m"
        assert record["positions"][1]["annotations"]["CONS"]["value"] == "x"


def test_missing_optional_headers_are_not_default_values_or_annotations():
    data = b"\n".join(line for line in native().splitlines()
        if line.split()[0] not in {b"ACC", b"DESC", b"DATE", b"NSEQ", b"EFFN", b"CKSUM", b"STATS", b"COMPO"}) + b"\n"
    result = extract(data)
    assert result["population"]["complete"] is True
    record = result["records"][0]
    assert record["sequence_count"] is record["effective_sequence_count"] is record["checksum"] is None
    assert record["calibration"] == [] and record["composition"] is None
    assert record["cutoffs"] == {}


def test_ordered_unknown_and_command_headers_and_utf8_byte_locators():
    data = native().replace(b"LENG  12", "COM   [1] supplied fixture command\nCOM   [2] second command\nCUSTOM  café \u03b1\nLENG  12".encode())
    data = data.replace(b"\n", b"\r\n")
    result = extract(b"# retained fixture\r\n\r\n" + data + b"\r\n" + data)
    assert result["population"]["complete"] is True
    first, second = result["records"]
    custom = [h for h in first["headers"] if h["tag"] in {"CUSTOM", "COM"}]
    assert [h["tag"] for h in custom] == ["COM", "COM", "CUSTOM"]
    assert custom[2]["tokens"] == ["café", "\u03b1"]
    assert first["locator"]["byte_start"] == len(b"# retained fixture\r\n\r\n")
    assert first["locator"]["byte_end"] - first["locator"]["byte_start"] == len(data)
    assert second["locator"]["byte_start"] == first["locator"]["byte_end"] + 2


def test_actual_single_matrix_native_command_header_and_counts():
    result = extract(native("hmmbuild_singlemx"))
    assert result["population"]["complete"] is True, result["issues"]
    record = result["records"][0]
    assert record["sequence_count"] == record["effective_sequence_count"] == 1
    commands = [header for header in record["headers"] if header["tag"] == "COM"]
    assert len(commands) == 1
    assert commands[0]["value"] == "[1] [HMM created from a query sequence]"
    assert next(header["value"] for header in record["headers"] if header["tag"] == "NAME") == "single"


def test_identical_bytes_and_duplicate_native_names_keep_occurrence_identity():
    data = native()
    result = extract(data + data)
    assert result["population"]["decoded_count"] == 2 and result["population"]["complete"]
    assert [r["record_key"] for r in result["records"]] == ["output/models/0#model/0", "output/models/0#model/1"]
    other = extract(data, occurrence_id="input/models/0", direction="input")
    assert other["records"][0]["record_key"] != result["records"][0]["record_key"]
    assert other["occurrence"]["sha256"] == extract(data)["occurrence"]["sha256"]


@pytest.mark.parametrize("fraction", [0.1, 0.4, 0.9])
def test_valid_first_model_survives_truncated_later_model(fraction):
    data = native()
    result = extract(data + data[:int(len(data) * fraction)])
    assert result["records"][0] == extract(data)["records"][0]
    assert result["population"] == {"decoded_count": 2, "complete": False, "state": "partial"}
    assert not result["records"][1]["terminated"]
    assert "record_unterminated" in codes(result)


def test_complete_prefix_survives_invalid_utf8_and_garbage_after_it():
    data = native()
    result = extract(data + b"\xff not a model\n")
    assert result["records"][0] == extract(data)["records"][0]
    assert result["population"]["state"] == "partial"
    assert "signature_invalid" in codes(result)


@pytest.mark.parametrize("token", ["NaN", "inf", "-0.1", "1e999", "bad", "1_000"])
def test_invalid_probability_tokens_retain_cells_without_zero_substitution(token):
    data = mutate_line(native(), lambda line: line.split()[0] == "5",
                       lambda line: line.replace("0.40547", token))
    result = extract(data)
    cell = result["records"][0]["positions"][4]["match"]["cells"][4]
    assert cell == {"token": token, "negative_log_probability": None, "probability": None, "state": "invalid"}
    assert "probability_token_invalid" in codes(result)
    assert result["population"]["complete"] is False


def test_probability_underflow_is_not_native_zero():
    result = extract(native().replace(b"0.40547", b"1000.00000"))
    cell = result["records"][0]["positions"][4]["match"]["cells"][4]
    assert cell == {"token": "1000.00000", "negative_log_probability": 1000.0,
                    "probability": None, "state": "underflow"}
    assert "probability_underflow" in codes(result)
    assert result["population"]["complete"] is True


def test_incomplete_rows_are_not_padded_and_missing_rows_stay_absent():
    data = native()
    lines = data.splitlines()
    shortened = b"\n".join(lines[:-2]) + b"\n"  # last transition and terminator absent
    result = extract(shortened)
    assert result["records"][0]["positions"][-1]["transitions"] is None
    assert "distribution_missing" in codes(result)
    data = data.replace(b"0.00000        *        *  0.69315  0.69315  0.00000        *", b"0.00000 * * 0.69315 0.69315 0.00000")
    result = extract(data)
    assert len(result["records"][0]["positions"][-1]["transitions"]["cells"]) == 6
    assert "distribution_width_invalid" in codes(result)


def test_truncated_record_boundary_does_not_absorb_next_valid_model():
    data = native()
    partial = data[:data.index(b"      5")]
    result = extract(partial + data)
    assert len(result["records"]) == 2
    assert result["records"][1]["terminated"] is True
    assert len(result["records"][1]["positions"]) == 12
    assert result["records"][1]["issues"] == []
    assert result["records"][1]["locator"]["byte_start"] == len(partial)


def test_wrong_declared_alphabet_does_not_silently_relabel_body():
    result = extract(native("hmmbuild_dna").replace(b"ALPH  DNA", b"ALPH  RNA"))
    assert "alphabet_symbols_invalid" in codes(result)
    assert result["records"][0]["alphabet"] == {"kind": "RNA", "symbols": list("ACGT")}


@pytest.mark.parametrize("old,new,code", [
    (b"LENG  12", b"LENG  13", "length_mismatch"),
    (b"NSEQ  3", b"NSEQ  three", "header_number_invalid"),
    (b"NSEQ  3", b"NSEQ  3\nNSEQ  4", "header_duplicate"),
    (b"RF    yes", b"RF    maybe", "header_value_invalid"),
    (b"STATS LOCAL FORWARD   -4.8052  0.72057\n", b"", "calibration_incomplete"),
    (b"m->m", b"m->x", "transition_labels_invalid"),
    (b"      2         *", b"      8         *", "position_order_invalid"),
    (b"      5 F x - -", b"      5 FF x - -", "annotation_value_invalid"),
    (b"      5 F x - -", b"      5 F x -", "annotation_width_invalid"),
])
def test_structural_and_metadata_defects_are_localized(old, new, code):
    data = native()
    assert old in data
    result = extract(data.replace(old, new))
    assert code in codes(result)
    assert result["population"]["state"] == "partial"
    assert all(issue["record_key"] == "output/models/0#model/0" for issue in result["issues"])


def test_duplicate_numeric_header_does_not_arbitrarily_choose_a_value():
    result = extract(native().replace(b"NSEQ  3", b"NSEQ  3\nNSEQ  4"))
    record = result["records"][0]
    assert record["sequence_count"] is None
    assert [h["tokens"] for h in record["headers"] if h["tag"] == "NSEQ"] == [["3"], ["4"]]


def test_mismatched_size_or_hash_preserves_records_but_invalidates_association():
    result = extract(native(), size_bytes=1, sha256="0" * 64)
    assert result["population"] == {"decoded_count": 1, "complete": False, "state": "invalid"}
    assert {"occurrence_size_mismatch", "occurrence_digest_mismatch"} <= codes(result)
    assert result["records"][0]["issues"] == []


@pytest.mark.parametrize("completeness", ["partial", "unknown"])
def test_explicit_capture_status_does_not_change_decoded_native_body(completeness):
    result = extract(native(), completeness=completeness)
    assert result["population"] == {"decoded_count": 1, "complete": False, "state": "partial"}
    assert result["records"] == extract(native())["records"]


@pytest.mark.parametrize("format,name", [("hmmer2_ascii", "hmmconvert_legacy2"), ("hmmer_binary", "hmmconvert_binary")])
def test_actual_newly_supported_encodings_use_common_population_and_identity(format, name):
    data = native(name, "stdout.log")
    result = extract_hmmer_models(data, occurrence=occurrence(data), format=format)
    assert result["population"] == {"decoded_count": 1, "complete": True, "state": "decoded"}
    assert result["records"][0]["record_key"] == "output/models/0#model/0"
    assert result["records"][0]["length"] == len(result["records"][0]["positions"]) == 12
    assert result["records"][0]["sequence_count"] == 3
    assert result["occurrence"] == occurrence(data)


@pytest.mark.parametrize("data", [b"", b"\n\t\n", b"# no models\n"])
def test_explicit_empty_ascii_population_is_known_zero(data):
    assert extract(data)["population"] == {"decoded_count": 0, "complete": True, "state": "decoded"}


def test_unknown_revision_does_not_claim_a_decoded_zero_population():
    result = extract(b"HMMER3/g [future version]\n//\n")
    assert result["population"] == {"decoded_count": None, "complete": False, "state": "unsupported"}
    assert "revision_unsupported" in codes(result)


@pytest.mark.parametrize("update", [{"ordinal": True}, {"direction": {}}, {"size_bytes": -1}, {"extra": 1}])
def test_invalid_occurrence_contract_returns_specific_failure(update):
    result = extract(native(), **update)
    assert result["population"]["state"] == "invalid"
    assert codes(result) == {"occurrence_invalid"}


def test_issues_use_closed_codes_and_specific_fields():
    result = extract(native().replace(b"0.40547", b"bad"))
    issue = next(i for i in result["issues"] if i["code"] == "probability_token_invalid")
    assert codes(result) <= ISSUE_CODES
    assert issue["record_key"] == "output/models/0#model/0"
    assert (issue["position"], issue["field"], issue["stage"]) == (5, "match", "extraction")
