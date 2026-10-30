"""Actual native keyword reads of explicitly labelled synthetic FCS fixtures."""

from copy import deepcopy
import re

import pytest

from fluorescence_flowio_test_support import require_bounded_runtime, mutate_writer

require_bounded_runtime()

from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode import fluorescence_event_preparation as preparation
from gene_annotation_episode import fluorescence_preparation_contracts as contracts
from gene_annotation_episode import fluorescence_preparation_readers as readers
from test_fluorescence_preparation import (
    native, _codes, _comp_case, _fcs, _file, _matrix, _parse, _request, _retain,
)


def _edited_text(raw, transform):
    """Test-only segment mutation with exact offsets; never a scientific reader."""
    first, last, data_first, data_last = [int(raw[index:index + 8]) for index in (10, 18, 26, 34)]
    text = transform(raw[first:last + 1])
    data = raw[data_first:data_last + 1]
    while True:
        start = first + len(text)
        rebuilt = re.sub(rb'(\$BEGINDATA/)\d+', lambda match: match[1] + str(start).encode(), text)
        rebuilt = re.sub(rb'(\$ENDDATA/)\d+', lambda match: match[1] + str(start + len(data) - 1).encode(), rebuilt)
        if rebuilt == text:
            break
        text = rebuilt
    header = bytearray(raw[:first])
    for index, value in ((18, start - 1), (26, start), (34, start + len(data) - 1)):
        header[index:index + 8] = f"{value:>8}".encode()
    result = bytes(header) + text + data
    _retain(result, "fcs", "explicit TEXT mutation of a synthetic native-writer fixture")
    return result


def test_exact_selected_keyword_does_not_take_alias_precedence(native):
    raw = _fcs(native, [[110, 60]], metadata=dict(spill="2,A,B,1,0.1,0.2,1", spillover="2,A,B,1,0,0,1"))
    parent = _parse(raw)
    first, second = _matrix(raw, parent, keyword="spill"), _matrix(raw, parent, keyword="spillover")
    assert first["state"] == second["state"] == "available"
    assert first["values"] == [[1, .1], [.2, 1]]
    assert second["values"] == [[1, 0], [0, 1]]
    assert first["raw_token"] == "2,A,B,1,0.1,0.2,1"
    assert first["file"] == parent["source"]["file"]


def test_absent_selected_keyword_is_unavailable_even_when_alias_exists(native):
    raw = _fcs(native, [[110, 60]], metadata=dict(spillover="2,A,B,1,0,0,1"))
    parent = _parse(raw)
    matrix = _matrix(raw, parent, keyword="spill")
    assert matrix["state"] == "unavailable"
    assert matrix["raw_token"] is None and matrix["values"] == []
    assert {row["code"] for row in matrix["problems"]} == {"parameter_unavailable"}


@pytest.mark.parametrize("token", ["2,A,A,1,0,0,1", "2,A,B,1,0,1", "2,A,B,1,0,nan,1",
                                    "2,A,B,1,0,inf,1", "0", "wrong", "2,A,B,1,0,0,1,5",
                                    "2,A,B,1\n.0,0,0,1"])
def test_bad_matrix_preserves_exact_native_token_without_coefficients(native, token):
    raw = _fcs(native, [[110, 60]], metadata=dict(spill=token))
    matrix = _matrix(raw, _parse(raw))
    assert matrix["state"] == "incompatible"
    assert matrix["raw_token"] == token and matrix["values"] == []
    assert {row["code"] for row in matrix["problems"]} == {"parameter_invalid"}


@pytest.mark.parametrize("token", ["2,A,C,1,0,0,1", "2, A,B,1,0,0,1"])
def test_matrix_axes_require_exact_declared_native_labels(native, token):
    raw = _fcs(native, [[110, 60]], metadata=dict(spill=token))
    matrix = _matrix(raw, _parse(raw))
    assert matrix["state"] == "incompatible"
    assert {row["code"] for row in matrix["problems"]} == {"channel_mapping_incompatible"}


def test_escaped_delimiter_uses_actual_native_parser_and_preserves_axis(native):
    raw = _fcs(native, [[110, 60]], names=("A/B", "B"), metadata=dict(spill="2,A/B,B,1,0.1,0.2,1"))
    assert b"A//B" in raw
    parent = _parse(raw, ("A/B", "B"))
    matrix = _matrix(raw, parent)
    assert matrix["state"] == "available"
    assert matrix["axis_tokens"] == ["A/B", "B"]
    assert matrix["raw_token"] == "2,A/B,B,1,0.1,0.2,1"
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix,
        request=_request(parent, contracts.COMPENSATE_METHOD, matrix=matrix))
    assert outcome["data"]["events"][0]["values"][0]["measurement"]["value"] == pytest.approx(100)


def test_duplicate_selected_metadata_is_rejected_without_first_or_last_guess(native):
    raw = _fcs(native, [[110, 60]], metadata=dict(spill="2,A,B,1,0.1,0.2,1"))
    raw = _edited_text(raw, lambda text: text + b"SPILL/2,A,B,1,0,0,1/")
    matrix = _matrix(raw, _parse(raw))
    assert matrix["state"] == "incompatible"
    assert matrix["raw_token"] is None and matrix["values"] == []
    assert {row["code"] for row in matrix["problems"]} == {"parameter_invalid"}


def test_literal_dollar_in_value_is_retained_and_rejected_not_normalized(native):
    token = "2,A,B,$1,0.1,0.2,1"
    raw = _fcs(native, [[110, 60]], metadata=dict(spill=token))
    parent = _parse(raw)
    assert next(row["value"] for row in parent["source"]["metadata"] if row["name"] == "flowio.text.spill") == token.replace("$", "")
    matrix = _matrix(raw, parent)
    assert matrix["state"] == "incompatible"
    assert matrix["raw_token"] == token and matrix["values"] == []


def test_literal_dollar_scaling_token_is_not_fabricated_gain(native):
    raw = _fcs(native, [[100]], names=("A",), metadata=dict(p1g="$2"))
    parent = _parse(raw, ("A",))
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=_request(parent))
    assert outcome["status"] == "incompatible" and "parameter_invalid" in _codes(outcome)
    assert outcome["parameters"]["scaling"]["channels"][0]["png_raw"] == "$2"
    assert outcome["data"] is None


def test_duplicate_gain_is_rejected_while_original_encoded_semantics_survive(native):
    raw = _fcs(native, [[100]], names=("A",), metadata=dict(p1g="2"))
    raw = _edited_text(raw, lambda text: text + b"$P1G/4/")
    parent = _parse(raw, ("A",))
    assert parent["events"][0]["values"][0]["measurement"]["value"] == 100
    outcome = preparation.prepare_fcs_scaling(raw, parent=parent, request=_request(parent))
    assert outcome["status"] == "incompatible" and "parameter_invalid" in _codes(outcome)
    assert outcome["parameters"]["scaling"]["channels"][0]["png_raw"] is None


def test_explicit_selected_dataset_keeps_its_matrix_and_native_count(native):
    first = _fcs(native, [[9, 8]], metadata=dict(spill="2,A,B,1,0,0,1"))
    second = _fcs(native, [[110, 60]], metadata=dict(spill="2,A,B,1,0.1,0.2,1"))
    while True:
        updated = mutate_writer(first, text_updates={"$NEXTDATA": str(len(first))})
        if updated == first:
            break
        first = updated
    raw = first + second
    _retain(raw, "fcs", "explicit two-dataset concatenation of synthetic native-writer files")
    parent = _parse(raw, dataset=1)
    matrix = _matrix(raw, parent)
    assert matrix["state"] == "available" and matrix["dataset_position"] == 1
    assert matrix["values"] == [[1, .1], [.2, 1]]
    assert parent["source"]["native_event_count"] == 1


def test_received_separate_matrix_artifact_preserves_support_identity(native):
    raw = _fcs(native, [[110, 60]])
    parent = _parse(raw)
    support_raw = _fcs(native, [[1, 2]], metadata=dict(spill="2,A,B,1,0.1,0.2,1"))
    support = deepcopy(parent["source"])
    support.update(key="matrix-support", file=_file(support_raw, "fcs"))
    matrix = _matrix(support_raw, parent, source=support)
    request = _request(parent, contracts.COMPENSATE_METHOD, matrix=matrix)
    outcome = preparation.prepare_spill_compensation(parent, matrix=matrix, request=request)
    assert matrix["file"] == support["file"] != parent["source"]["file"]
    assert outcome["parameters"]["compensation"]["file"] == support["file"]
    assert outcome["data"]["events"][0]["values"][0]["measurement"]["value"] == pytest.approx(100)


@pytest.mark.parametrize("fault", ["extra_locator", "bool_dataset", "wrong_dataset", "wrong_keyword", "unordered_channels", "mixed_domain"])
def test_reader_rejects_malformed_explicit_bindings(native, fault):
    raw = _fcs(native, [[110, 60]], metadata=dict(spill="2,A,B,1,0.1,0.2,1"))
    parent = _parse(raw)
    locator = dict(dataset_position=0, keyword="spill")
    if fault == "extra_locator": locator["precedence"] = "spillover"
    elif fault == "bool_dataset": locator["dataset_position"] = False
    elif fault == "wrong_dataset": locator["dataset_position"] = 1
    elif fault == "wrong_keyword": locator["keyword"] = "SPILL"
    elif fault == "unordered_channels": parent["channels"].reverse()
    elif fault == "mixed_domain": parent["channels"][1]["domain_key"] = "another"
    with pytest.raises(core.FluorescenceContractError):
        readers.read_fcs_spill_matrix(raw, source=parent["source"], locator=locator, channels=parent["channels"])


def test_matrix_identity_mismatch_is_specific(native):
    raw, parent, _, _ = _comp_case(native)
    matrix = _matrix(raw + b"changed", parent)
    assert matrix["state"] == "incompatible"
    assert {row["code"] for row in matrix["problems"]} == {"parameter_identity_mismatch"}


def test_matrix_coefficient_substitution_fails_before_native_solve(native):
    _, parent, matrix, request = _comp_case(native)
    matrix["values"][0][0] = 2
    with pytest.raises(core.FluorescenceContractError):
        preparation.prepare_spill_compensation(parent, matrix=matrix, request=request)


def test_unavailable_native_library_retains_selected_raw_matrix(native, monkeypatch):
    raw, parent, _, _ = _comp_case(native)
    monkeypatch.setattr(readers, "_load_flowutils", lambda: None)
    matrix = _matrix(raw, parent)
    assert matrix["state"] == "unavailable" and matrix["raw_token"] == "2,A,B,1,0.1,0.2,1"
    assert {row["code"] for row in matrix["problems"]} == {"backend_unavailable"}


def test_native_constructor_failure_retains_selected_spill_token(native):
    token = "2,A,B,1,0.1,0.2,1"
    raw = _fcs(native, [[110, 60]], metadata=dict(spill=token, p1g="malformed"))
    parent = _parse(raw)
    assert parent["source"]["extent"] == "unavailable"
    matrix = _matrix(raw, parent)
    assert matrix["state"] == "incompatible"
    assert matrix["raw_token"] == token and matrix["axis_tokens"] == ["A", "B"]
    assert matrix["values"] == []
    assert {row["code"] for row in matrix["problems"]} == {"parameter_invalid"}
