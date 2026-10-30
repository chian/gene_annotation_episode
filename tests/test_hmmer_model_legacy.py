"""Retained native 259 H2 output and explicitly synthetic grammar/error fixtures.

These tests never invoke a converter or model loader. The native fixture is a
real retained hmmconvert output for a synthetic alignment, not biological data.
Synthetic cases establish parsing behavior, not historical producer coverage.
"""
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_model_data import ISSUE_CODES, TRANSITIONS, extract_hmmer_models
from gene_annotation_episode.hmmer_model_legacy import decode_hmmer2_ascii


NATIVE = (Path(__file__).resolve().parents[1] /
          "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/native")


def native():
    data = (NATIVE / "hmmconvert_legacy2/stdout.log").read_bytes()
    assert hashlib.sha256(data).hexdigest() == "37a65d6515e1d4b657ff8ea3ce70cc002e6fedfec9abcb43d9bced646b87de7b"
    return data


def occurrence(data, **overrides):
    return {"occurrence_id": "output/models/0", "direction": "output", "role": "models",
            "ordinal": 0, "artifact_ref": "retained:legacy", "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data), "completeness": "complete", **overrides}


def decode(data, **overrides):
    return decode_hmmer2_ascii(data, occurrence=occurrence(data, **overrides))


def codes(result):
    return {issue["code"] for issue in result["issues"]}


def tokens(distribution):
    return [cell["token"] for cell in distribution["cells"]]


def synthetic(symbols="ACGU", *, map_flag="no", rf="-", cs="-", extra_headers=""):
    """Labeled format fixture, constructed from the retained source grammar."""
    width = len(symbols)
    mapping = " 7" if map_flag.lower() == "yes" else ""
    return ("HMMER2.0 [synthetic grammar fixture]\nNAME synthetic\nDESC\nLENG 1\n"
            f"ALPH Nucleic\nRF no\nCS no\nMAP {map_flag}\nNSEQ 0\n"
            f"{extra_headers}"
            "XT 0 * -1000 -1000 0 * 0 *\nNULT 0 *\n"
            f"NULE {' '.join(['0'] * width)}\nHMM {' '.join(symbols)}\n"
            "m->m m->i m->d i->m i->i d->m d->d b->m m->e\n"
            "0 * *\n"
            f"1 {' '.join(['0'] * width)}{mapping}\n"
            f"{rf} {' '.join(['*'] * width)}\n"
            f"{cs} * * * * * * * * 0\n//\n").encode()


def test_retained_native_output_keeps_all_source_fields_and_identity():
    data = native()
    result = decode(data)
    assert set(result) == {"records", "issues", "population"}
    assert result["population"] == {"decoded_count": 1, "complete": True, "state": "decoded"}
    assert result["issues"] == []
    record = result["records"][0]
    assert record["record_key"] == "output/models/0#model/0"
    assert record["locator"] == {"artifact_ref": "retained:legacy", "record_ordinal": 0,
        "byte_start": 0, "byte_end": len(data), "line_start": 1, "line_end": len(data.splitlines())}
    assert record["format_tag"] == "HMMER2.0"
    assert record["engine_text"] == "[converted from 3.4]"
    assert (record["length"], record["sequence_count"]) == (12, 3)
    assert record["effective_sequence_count"] is record["maximum_length"] is record["checksum"] is None
    assert record["composition"] is None and record["calibration"] == []
    assert record["initial"] == {"insert": None, "transitions": None}
    assert record["flags"] == {"RF": True, "CS": False, "MAP": True}
    assert record["alphabet"] == {"kind": "amino", "symbols": list("ACDEFGHIKLMNPQRSTVWY")}
    rep = record["representation"]
    assert set(rep) == {"schema", "encoding", "topology", "byte_order", "binary_layout",
                        "header_semantics", "native_fields", "legacy"}
    assert rep["encoding"] == "hmmer2_ascii_millibit_log_odds" and rep["topology"] == "hmmer2_configured"
    assert rep["byte_order"] is rep["binary_layout"] is None and rep["native_fields"] == []
    assert rep["header_semantics"] == "original_ascii_headers"
    legacy = rep["legacy"]
    assert set(legacy) == {"null_emissions", "special_transitions", "null_transitions",
                          "begin_transitions", "entry_exit", "checksum", "evd"}
    assert legacy["checksum"] is None and legacy["evd"] == []
    lines = [line.split() for line in data.decode().splitlines()]
    for tag, field in (("NULE", "null_emissions"), ("XT", "special_transitions"), ("NULT", "null_transitions")):
        source_index = next(index for index, line in enumerate(lines) if line[0] == tag)
        assert tokens(legacy[field]) == lines[source_index][1:]
        assert legacy[field]["line"] == source_index + 1
    assert legacy["special_transitions"]["symbols"] == ["NB", "NN", "EC", "EJ", "CT", "CC", "JB", "JJ"]
    assert legacy["null_transitions"]["symbols"] == ["slot_0", "slot_1"]
    assert legacy["begin_transitions"]["symbols"] == ["B->M1", "unused", "B->D1"]
    assert tokens(legacy["begin_transitions"]) == ["0", "*", "*"]
    assert [p["position"] for p in record["positions"]] == list(range(1, 13))
    for index, position in enumerate(record["positions"]):
        source = position["line"] - 1
        assert tokens(position["match"]) == lines[source][1:21]
        assert tokens(position["insert"]) == lines[source + 1][1:]
        assert tokens(position["transitions"]) == lines[source + 2][1:8]
        assert tokens(legacy["entry_exit"][index]) == lines[source + 2][8:10]
        assert legacy["entry_exit"][index]["position"] == index + 1
        assert legacy["entry_exit"][index]["line"] == position["transitions"]["line"] == source + 3
        assert position["insert"]["line"] == source + 2
        assert position["annotations"] == {"MAP": {"token": str(index + 1), "value": index + 1},
            "RF": {"token": "x", "value": "x"}, "CS": {"token": "-", "value": "-"}}
    assert all(cell["state"] == "structural_zero" for cell in record["positions"][-1]["insert"]["cells"])
    assert all(cell["state"] == "structural_zero" for cell in record["positions"][-1]["transitions"]["cells"])
    assert tokens(legacy["entry_exit"][-1]) == ["*", "0"]
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_native_scores_references_and_nominal_range_do_not_erase_population():
    result = decode(native())
    record = result["records"][0]
    nulls = record["representation"]["legacy"]["null_emissions"]["cells"]
    cell = record["positions"][0]["match"]["cells"][0]
    assert nulls[0]["source"]["score"] == 656
    assert nulls[0]["source"]["reference"] == {"kind": "uniform_alphabet", "denominator": 20}
    assert cell["source"]["score"] == 3666 and cell["token"] == "3666"
    assert cell["source"]["reference"] == {"kind": "nule", "cell_index": 0}
    assert cell["negative_log_probability"] is None and cell["probability"] is None
    assert cell["source"]["nominal_probability"] > 1 and cell["state"] == "quantized_out_of_range"
    position5 = record["positions"][4]["match"]["cells"]
    for index, score, null_score in ((4, 4070, -333), (19, 3454, -717)):
        assert position5[index]["source"]["score"] == score
        assert nulls[index]["source"]["score"] == null_score
        assert position5[index]["source"]["reference"] == {"kind": "nule", "cell_index": index}
        assert position5[index]["state"] == "finite"
        assert 0 < position5[index]["probability"] < 1
    assert result["population"]["complete"] is True and result["population"]["decoded_count"] == 1


@pytest.mark.parametrize("symbols,kind", [("ACGT", "DNA"), ("ACGU", "RNA")])
def test_synthetic_nucleic_keeps_original_label_and_actual_body_alphabet(symbols, kind):
    result = decode(synthetic(symbols))
    assert result["population"]["complete"] is True, result["issues"]
    record = result["records"][0]
    assert record["sequence_count"] == 0 and record["effective_sequence_count"] is None
    assert record["alphabet"] == {"kind": kind, "symbols": list(symbols)}
    assert next(h["value"] for h in record["headers"] if h["tag"] == "ALPH") == "Nucleic"
    assert all(cell["probability"] == 0.25 for cell in record["positions"][0]["match"]["cells"])
    assert record["flags"] == {"RF": False, "CS": False, "MAP": False}


def test_synthetic_unknown_headers_commands_duplicate_legacy_values_and_empty_description():
    data = synthetic(extra_headers="COM first native command\nCOM second native command\n"
                     "CUSTOM café α\nCKSUM -12345\nEVD -2.5 0.7\nEVD -3 0.8\nGA 2.5 1.5\n")
    result = decode(data)
    record = result["records"][0]
    legacy = record["representation"]["legacy"]
    assert [h["value"] for h in record["headers"] if h["tag"] == "COM"] == ["first native command", "second native command"]
    assert next(h["tokens"] for h in record["headers"] if h["tag"] == "CUSTOM") == ["café", "α"]
    assert next(h["value"] for h in record["headers"] if h["tag"] == "DESC") == ""
    assert legacy["checksum"]["token"] == "-12345" and legacy["checksum"]["value"] == -12345
    assert legacy["checksum"]["meaning"] == "hmmer2_legacy_checksum" and record["checksum"] is None
    assert [item["values"] for item in legacy["evd"]] == [[-2.5, 0.7], [-3, 0.8]]
    assert all(item["unit"] is None for item in legacy["evd"])
    assert record["calibration"] == [] and record["cutoffs"]["GA"]["values"] == [2.5, 1.5]
    assert [(issue["code"], issue["field"]) for issue in result["issues"]] == [("header_duplicate", "EVD")]


def test_synthetic_multibyte_crlf_duplicate_model_and_occurrence_coordinates():
    one = synthetic(extra_headers="CUSTOM café α\n").replace(b"\n", b"\r\n")
    prefix = b"# explicit format fixture\r\n\r\n"
    data = prefix + one + b"\r\n" + one
    result = decode(data)
    first, second = result["records"]
    assert result["population"] == {"decoded_count": 2, "complete": True, "state": "decoded"}
    assert first["locator"]["byte_start"] == len(prefix)
    assert first["locator"]["byte_end"] == len(prefix) + len(one)
    assert second["locator"]["byte_start"] == len(prefix) + len(one) + 2
    assert second["locator"]["byte_end"] == len(data)
    assert first["locator"]["line_start"] == 3
    assert second["locator"]["line_start"] == len(prefix.splitlines()) + len(one.splitlines()) + 2
    assert first["record_key"] != second["record_key"]
    other = decode(one, occurrence_id="input/models/4", direction="input", ordinal=4)
    assert other["records"][0]["record_key"] == "input/models/4#model/0"
    assert other["records"][0]["locator"]["record_ordinal"] == 0


@pytest.mark.parametrize("replacement,expected_state", [(None, "reference_missing"), (b"bad", "invalid")])
def test_synthetic_missing_and_malformed_nule_are_distinct(replacement, expected_state):
    data = synthetic()
    data = data.replace(b"NULE 0 0 0 0\n", b"" if replacement is None else b"NULE " + replacement + b" 0 0 0\n")
    result = decode(data)
    record = result["records"][0]
    match = record["positions"][0]["match"]["cells"]
    assert match[0]["state"] == expected_state and match[0]["probability"] is None
    assert match[0]["source"]["score"] == 0 and match[0]["source"]["reference"] == {"kind": "nule", "cell_index": 0}
    assert result["population"]["decoded_count"] == 1 and result["population"]["complete"] is False
    assert "header_missing" in codes(result) if replacement is None else "probability_token_invalid" in codes(result)
    assert all(cell["state"] == "structural_zero" for cell in record["positions"][0]["insert"]["cells"])
    if replacement is not None:
        assert match[1]["probability"] == 0.25


def test_synthetic_short_nule_preserves_prefix_without_padding_or_uniform_fallback():
    result = decode(synthetic().replace(b"NULE 0 0 0 0", b"NULE 0 0"))
    record = result["records"][0]
    assert len(record["representation"]["legacy"]["null_emissions"]["cells"]) == 2
    assert [c["state"] for c in record["positions"][0]["match"]["cells"]] == [
        "finite", "finite", "reference_missing", "reference_missing"]
    assert "distribution_width_invalid" in codes(result)


def test_synthetic_zero_nule_reference_is_not_underflow_or_an_invented_probability():
    data = synthetic().replace(b"NULE 0 0 0 0", b"NULE * 0 0 0")
    result = decode(data)
    record = result["records"][0]
    reference = record["representation"]["legacy"]["null_emissions"]["cells"][0]
    cell = record["positions"][0]["match"]["cells"][0]
    assert reference["state"] == "structural_zero" and reference["probability"] == 0
    assert cell["token"] == "0" and cell["source"]["score"] == 0
    assert cell["state"] == "invalid" and cell["probability"] is None
    assert cell["source"]["nominal_probability"] == 0.0
    assert result["population"]["complete"] is True and result["issues"] == []
    zero = decode(data.replace(b"1 0 0 0 0", b"1 * 0 0 0"))["records"][0]["positions"][0]["match"]["cells"][0]
    assert zero["state"] == "structural_zero" and zero["probability"] == 0


@pytest.mark.parametrize("bad", ["NaN", "inf", "1.5", "2e3", "1_000", "**", "bad"])
def test_synthetic_malformed_integer_scores_are_preserved_and_localized(bad):
    data = synthetic().replace(b"1 0 0 0 0\n", f"1 {bad} 0 0 0\n".encode())
    result = decode(data)
    cell = result["records"][0]["positions"][0]["match"]["cells"][0]
    assert cell["token"] == bad and cell["source"]["score"] is None
    assert cell["probability"] is None and cell["state"] == "invalid"
    issue = next(i for i in result["issues"] if i["code"] == "probability_token_invalid")
    assert (issue["position"], issue["field"], issue["details"]["cell"]) == (1, "match", 0)
    assert issue["line"] == result["records"][0]["positions"][0]["line"]
    assert result["population"]["state"] == "partial" and codes(result) <= ISSUE_CODES


def test_synthetic_exact_signed_token_and_underflow_remain_distinct_from_zero():
    result = decode(synthetic().replace(b"1 0 0 0 0\n", b"1 +0000 -0000 -1000000 *\n"))
    cells = result["records"][0]["positions"][0]["match"]["cells"]
    assert [c["token"] for c in cells] == ["+0000", "-0000", "-1000000", "*"]
    assert [c["source"]["score"] for c in cells] == [0, 0, -1000000, None]
    assert cells[2]["state"] == "underflow" and cells[2]["probability"] is None
    assert cells[3]["state"] == "structural_zero" and cells[3]["probability"] == 0
    assert result["population"]["complete"] is True and "probability_underflow" in codes(result)
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_synthetic_duplicate_nule_does_not_select_a_convenient_reference():
    result = decode(synthetic().replace(b"NULE 0 0 0 0", b"NULE 0 0 0 0\nNULE -1000 -1000 -1000 -1000"))
    record = result["records"][0]
    assert record["representation"]["legacy"]["null_emissions"] is None
    assert len([h for h in record["headers"] if h["tag"] == "NULE"]) == 2
    assert all(c["probability"] is None for c in record["positions"][0]["match"]["cells"])
    assert "header_duplicate" in codes(result)


def test_synthetic_bad_labels_and_extra_transition_slots_remain_inspectable():
    data = synthetic().replace(b"m->e\n", b"m->x strange\n").replace(b"- * * * * * * * * 0\n", b"- * * * * * * * * 0 17\n")
    result = decode(data)
    record = result["records"][0]
    label_header = next(h for h in record["headers"] if h["tag"] == "m->m")
    assert [label_header["tag"]] + label_header["tokens"] == TRANSITIONS + ["b->m", "m->x", "strange"]
    assert record["positions"][0]["transitions"]["symbols"] == TRANSITIONS
    assert tokens(record["representation"]["legacy"]["entry_exit"][0]) == ["*", "0"]
    assert record["positions"][0]["extra_tokens"] == ["17"]
    assert {"transition_labels_invalid", "distribution_width_invalid"} <= codes(result)


@pytest.mark.parametrize("old,new,code", [
    (b"LENG 1", b"LENG 2", "length_mismatch"),
    (b"LENG 1", b"LENG -2", "header_number_invalid"),
    (b"NSEQ 0", b"NSEQ 0\nNSEQ 1", "header_duplicate"),
    (b"RF no", b"RF maybe", "header_value_invalid"),
    (b"1 0 0 0 0", b"2 0 0 0 0", "position_order_invalid"),
    (b"HMM A C G U", b"HMM A C U G", "alphabet_symbols_invalid"),
    (b"ALPH Nucleic", b"ALPH RNA", "alphabet_invalid"),
    (b"- * * * *\n", b"xx * * * *\n", "annotation_value_invalid"),
    (b"XT 0 * -1000 -1000 0 * 0 *\n", b"", "header_missing"),
])
def test_synthetic_structure_errors_keep_the_original_record(old, new, code):
    data = synthetic()
    assert old in data
    result = decode(data.replace(old, new))
    assert code in codes(result) and result["population"]["state"] == "partial"
    assert result["population"]["decoded_count"] == 1


def test_synthetic_numeric_rf_character_is_not_mistaken_for_a_match_row():
    result = decode(synthetic(rf="1"))
    assert result["population"]["complete"] is True, result["issues"]
    assert len(result["records"][0]["positions"]) == 1
    assert result["records"][0]["positions"][0]["annotations"]["RF"]["value"] == "1"


def test_synthetic_numeric_cs_character_is_not_mistaken_for_a_match_row():
    result = decode(synthetic(cs="1"))
    assert result["population"]["complete"] is True, result["issues"]
    assert len(result["records"][0]["positions"]) == 1
    assert result["records"][0]["positions"][0]["annotations"]["CS"]["value"] == "1"


def test_synthetic_wholly_corrupt_transition_labels_remain_a_source_header():
    data = synthetic().replace(" ".join(TRANSITIONS + ["b->m", "m->e"]).encode(),
                               b"bad0 bad1 bad2 bad3 bad4 bad5 bad6 bad7 bad8")
    result = decode(data)
    record = result["records"][0]
    header = next(h for h in record["headers"] if h["tag"] == "bad0")
    assert header["tokens"] == ["bad" + str(i) for i in range(1, 9)]
    assert len(record["positions"]) == 1
    assert tokens(record["representation"]["legacy"]["begin_transitions"]) == ["0", "*", "*"]
    assert codes(result) == {"transition_labels_invalid"}


def test_synthetic_map_flag_controls_exact_match_annotation_width():
    good = decode(synthetic(map_flag="yes"))
    assert good["population"]["complete"] is True
    assert good["records"][0]["positions"][0]["annotations"]["MAP"] == {"token": "7", "value": 7}
    bad = decode(synthetic(map_flag="yes").replace(b"1 0 0 0 0 7", b"1 0 0 0 0"))
    assert "annotation_width_invalid" in codes(bad)


@pytest.mark.parametrize("removed", [1, 2, 3])
def test_synthetic_truncated_last_position_keeps_available_rows_without_padding(removed):
    data = b"\n".join(synthetic().splitlines()[:-removed]) + b"\n"
    result = decode(data)
    record = result["records"][0]
    assert record["terminated"] is False and result["population"]["state"] == "partial"
    assert len(record["positions"]) == 1
    assert len(record["positions"][0]["match"]["cells"]) == 4
    if removed >= 2:
        assert record["positions"][0]["transitions"] is None
    if removed == 3:
        assert record["positions"][0]["insert"] is None


def test_synthetic_next_signature_resynchronizes_without_losing_prefix_or_ordinals():
    one = synthetic()
    partial = one[:one.index(b"1 0 0 0 0")]
    result = decode(one + partial + one)
    assert result["records"][0] == decode(one)["records"][0]
    assert result["population"] == {"decoded_count": 3, "complete": False, "state": "partial"}
    assert result["records"][1]["positions"] == [] and result["records"][1]["terminated"] is False
    assert result["records"][2]["record_key"] == "output/models/0#model/2"
    assert result["records"][2]["locator"]["byte_start"] == len(one) + len(partial)
    assert result["records"][2]["issues"] == []


def test_synthetic_hmmer_named_unknown_header_is_not_a_record_signature():
    result = decode(synthetic(extra_headers="HMMER_CUSTOM source metadata\n"))
    assert result["population"] == {"decoded_count": 1, "complete": True, "state": "decoded"}
    assert next(h["tokens"] for h in result["records"][0]["headers"]
                if h["tag"] == "HMMER_CUSTOM") == ["source", "metadata"]


def test_synthetic_invalid_utf8_retains_original_byte_bounds_and_reversible_text():
    data = synthetic(extra_headers="CUSTOM original\n").replace(b"original", b"\xff")
    result = decode(data)
    record = result["records"][0]
    assert record["locator"]["byte_end"] == len(data)
    assert next(h["value"] for h in record["headers"] if h["tag"] == "CUSTOM").encode("utf-8", "surrogateescape") == b"\xff"
    assert "text_encoding_invalid" in codes(result)
    assert json.loads(json.dumps(result, allow_nan=False)) == result


@pytest.mark.parametrize("data", [b"", b"\n\t\n", b"# explicit empty fixture\n"])
def test_explicit_empty_source_is_known_zero(data):
    assert decode(data)["population"] == {"decoded_count": 0, "complete": True, "state": "decoded"}


@pytest.mark.parametrize("data,state", [(b"garbage\n", "invalid"), (b"HMMER2.1 [future]\n//\n", "unsupported")])
def test_nonempty_unrecognized_source_is_not_a_zero_population(data, state):
    assert decode(data)["population"] == {"decoded_count": None, "complete": False, "state": state}


def test_public_dispatch_preserves_source_identity_and_capture_or_association_failures():
    data = native()
    full = extract_hmmer_models(data, occurrence=occurrence(data), format="hmmer2_ascii")
    assert full["records"] == decode(data)["records"]
    assert full["population"] == decode(data)["population"]
    capture = extract_hmmer_models(data, occurrence=occurrence(data, completeness="partial"), format="hmmer2_ascii")
    assert capture["records"] == full["records"]
    assert capture["population"]["complete"] is False and capture["population"]["decoded_count"] == 1
    bad = extract_hmmer_models(data, occurrence=occurrence(data, sha256="0" * 64), format="hmmer2_ascii")
    assert bad["records"] == full["records"]
    assert bad["population"]["state"] == "invalid" and "occurrence_digest_mismatch" in codes(bad)
