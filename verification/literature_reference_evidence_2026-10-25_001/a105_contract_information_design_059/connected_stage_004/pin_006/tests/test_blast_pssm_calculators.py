"""Numerical checks of supplied PSSMs; no native scoring algorithm is executed."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.blast_pssm_inputs import read_blast_pssm
from gene_annotation_episode.blast_pssm_calculators import calculate_blast_pssm_components


SOURCES = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_pssm_2026-10-26_306/sources"


def read(text):
    return read_blast_pssm(text.encode(), format="scoremat_asn_text", artifact_key="synthetic:test", source_ref="synthetic")


def calc(text):
    return calculate_blast_pssm_components(read(text))["matrices"][0]


def model(body="", *, data="finalData { scores { -2, 0, 5, 7, -32768, 9 }, lambda { 3, 10, -1 }, kappa { 4, 10, -2 }, h { 1, 10, 0 } }", query=True):
    master = 'query seq { inst { repr raw, mol aa, length 3, seq-data iupacaa "ACD" } },' if query else ""
    return "Pssm ::= { numRows 2, numColumns 3, rowLabels { \"A\", \"C\" }, " + master + body + data + " }"


def test_upstream_frequency_matrix_all_cells_and_independently_read_first_interior_last():
    sheet = read_blast_pssm((SOURCES / "pssm_freq_ratios.asn").read_bytes(), format="scoremat_asn_text",
        artifact_key="upstream:ratios", source_ref="pinned-primary-source")
    result = calculate_blast_pssm_components(sheet)
    row, = result["matrices"]
    assert result["status"] == "complete"
    matrix = row["matrix_values"]["freqRatios"]
    assert len(matrix) == 232 and all(len(v) == 26 for v in matrix)
    # Direct native text: line 76 => 576481676635514 * 10^-16;
    # line 3101 => index 3026 = 116*26+10; final column row 22 => line 6103.
    assert matrix[0][1] == 0.0576481676635514
    assert matrix[116][10] == 0.146111920368741
    assert matrix[231][22] == 0.0103478446174989
    assert matrix[0][0] == matrix[-1][-1] == 0.0
    assert row["matrix_values"]["scores"] is None
    assert row["residue_alphabet"] == list("-ABCDEFGHIKLMNPQRSTVWXYZU*")
    assert row["master"]["status"] == "complete"
    assert row["master"]["reported_length"] == row["master"]["decoded_length"] == 232
    assert row["master"]["sequence"].startswith("QIKDLLVSSS")
    assert row["master"]["column_to_residue"][-1] == {"column": 231, "master_position": 231, "symbol": "P"}
    assert row["native_parameters"]["pseudocount"] == 9


def test_upstream_zero_ratios_final_score_cardinality_and_native_statistics_defaults():
    sheet = read_blast_pssm((SOURCES / "pssm_zero_fratios.asn").read_bytes(), format="scoremat_asn_text",
        artifact_key="upstream:zeros", source_ref="pinned-primary-source")
    row, = calculate_blast_pssm_components(sheet)["matrices"]
    scores = row["matrix_values"]["scores"]
    ratios = row["matrix_values"]["freqRatios"]
    assert len(scores) == len(ratios) == 232 and all(len(r) == 28 for r in scores + ratios)
    assert all(v == 0.0 for r in ratios for v in r)
    # Native score lines 6507, 9765 (=6507+116*28+10), 13002.
    assert (scores[0][0], scores[116][10], scores[231][27]) == (-32768, -1, -3)
    assert scores[0][2] == 0
    assert row["native_statistics"]["lambda"] == row["native_statistics"]["h"] == 0.0
    assert row["native_statistics"]["kappa"] == 0.0402635999
    assert row["native_statistics"]["scalingFactor"] == 1
    assert "scalingFactor" not in sheet["pssms"][0]["native_pssm"]["finalData"]
    assert row["native_order"] == {"reported_by_row": None, "effective_by_row": False}
    assert row["is_protein"] is True
    assert "isProtein" not in sheet["pssms"][0]["native_pssm"]
    assert row["master"]["status"] == "unavailable" and row["master"]["sequence"] is None
    assert row["status"] == "partial"


@pytest.mark.parametrize("order,expected", [
    ("", [[-2, 0], [5, 7], [-32768, 9]]),
    ("byRow FALSE, ", [[-2, 0], [5, 7], [-32768, 9]]),
    ("byRow TRUE, ", [[-2, 7], [0, -32768], [5, 9]]),
])
def test_hand_calculated_nonsquare_reshape_preserves_negative_zero_and_sentinel(order, expected):
    row = calc(model(order))
    assert row["status"] == "complete"
    assert row["matrix_values"]["scores"] == expected
    assert row["master"]["column_to_residue"][2] == {"column": 2, "master_position": 2, "symbol": "D"}


def test_all_intermediate_vectors_counts_real_tuples_and_statistics_are_independent():
    data = '''finalData { scores { 1, 2, 3, 4, 5, 6 }, lambda { 4, 2, -3 }, kappa 0.125,
        h 0, scalingFactor 100, lambdaUngapped 0.4, kappaUngapped 0.05, hUngapped 1.2, wordScoreThreshold 9 },
        intermediateData { resFreqsPerPos { 0, 4, 2, 2, 3, 1 },
        weightedResFreqsPerPos { 0, 1, { 1, 2, -1 }, { 1, 2, -1 }, 0.75, 0.25 },
        freqRatios { 0, 2, 1, 1, 3, 1 }, informationContent { 0, 0.5, 1 },
        gaplessColumnWeights { 1, 2, 3 }, sigma { 2, 3, 4 }, intervalSizes { 1, 3, 2 },
        numMatchingSeqs { 4, 4, 4 }, numIndeptObsr { 2, 2.5, 3 } }'''
    row = calc(model(data=data))
    assert row["status"] == "complete"
    assert row["matrix_values"]["scores"] == [[1, 2], [3, 4], [5, 6]]
    assert row["matrix_values"]["weightedResFreqsPerPos"] == [[0.0, 1.0], [0.5, 0.5], [0.75, 0.25]]
    assert row["matrix_values"]["resFreqsPerPos"] == [[0, 4], [2, 2], [3, 1]]
    assert row["position_diagnostics"] == {"informationContent": [0.0, 0.5, 1.0], "gaplessColumnWeights": [1.0, 2.0, 3.0],
        "sigma": [2.0, 3.0, 4.0], "intervalSizes": [1, 3, 2], "numMatchingSeqs": [4, 4, 4], "numIndeptObsr": [2.0, 2.5, 3.0]}
    assert row["native_statistics"] == {"lambda": 0.5, "kappa": 0.125, "h": 0.0, "scalingFactor": 100,
        "lambdaUngapped": 0.4, "kappaUngapped": 0.05, "hUngapped": 1.2, "wordScoreThreshold": 9.0}
    assert set(row["array_status"].values()) == {"available"}


def test_wrong_size_array_preserved_in_sheet_without_suppressing_valid_sibling():
    sheet = read(model(data='''intermediateData { freqRatios { 0, 1, 2, 3, 4 },
        resFreqsPerPos { 1, 2, 3, 4, 5, 6 }, informationContent { 1, 2 }, sigma { 1, 2, 3 } }'''))
    row = calculate_blast_pssm_components(sheet)["matrices"][0]
    assert sheet["pssms"][0]["native_pssm"]["intermediateData"]["freqRatios"] == [0, 1, 2, 3, 4]
    assert row["matrix_values"]["freqRatios"] is None
    assert row["matrix_values"]["resFreqsPerPos"] == [[1, 2], [3, 4], [5, 6]]
    assert row["position_diagnostics"]["informationContent"] is None
    assert row["position_diagnostics"]["sigma"] == [1, 2, 3]
    assert row["array_status"]["pssm.intermediateData.freqRatios"] == "incompatible"
    assert row["status"] == "partial"


@pytest.mark.parametrize("value,code", [("{ 1, 10, -1000 }", "real_underflow"),
    ("1e-1000", "real_underflow"), ("{ 1, 2, -2000 }", "real_underflow"),
    ("{ 1, 10, 1000 }", "real_unrepresentable"), ("{ 1, 2, 2000 }", "real_unrepresentable"),
    ("PLUS-INFINITY", "real_nonfinite"), ("NOT-A-NUMBER", "real_nonfinite"), ("{ 1, 3, 2 }", "real_invalid")])
def test_nonfinite_overflow_underflow_invalid_real_never_become_measured_zero(value, code):
    row = calc(model(data=f"intermediateData {{ freqRatios {{ 0, {value}, 0, 0, 0, 0 }}, resFreqsPerPos {{ 1, 2, 3, 4, 5, 6 }} }}"))
    assert row["matrix_values"]["freqRatios"] is None
    assert row["matrix_values"]["resFreqsPerPos"] is not None
    problem = next(i for i in row["issues"] if i["code"] == code)
    assert problem["field"] == "pssm.intermediateData.freqRatios[1]"
    assert problem["record_ordinal"] == 0 and problem["character_span"] is not None


def test_subnormal_real_and_exact_native_zero_remain_distinct():
    row = calc(model(data="intermediateData { freqRatios { { 1, 2, -1074 }, { 0, 10, -1000 }, 0, 0, 0, 0 } }"))
    assert row["matrix_values"]["freqRatios"][0] == [5e-324, 0.0]


def test_missing_final_intermediate_master_and_unknown_alphabet_have_explicit_missingness():
    row = calc(model(data="intermediateData { freqRatios { 1, 2, 3, 4, 5, 6 } }", query=False))
    assert row["matrix_values"]["scores"] is None and row["native_statistics"]["scalingFactor"] is None
    assert row["master"]["column_to_residue"] is None
    assert row["status"] == "partial"
    empty = calc("Pssm ::= { numRows 2, numColumns 3 }")
    assert empty["status"] == "unavailable"
    assert empty["residue_alphabet"] is None
    assert all(v is None for v in empty["matrix_values"].values())


def test_duplicate_scores_and_truncated_arrays_cannot_get_derived_success():
    duplicate = calc(model(data="finalData { scores { 1, 2, 3, 4, 5, 6 }, scores { 6, 5, 4, 3, 2, 1 }, lambda 0.3, kappa 0.04, h 1 }"))
    assert duplicate["matrix_values"]["scores"] is None and duplicate["status"] == "incompatible"
    truncated = calc('Pssm ::= { numRows 2, numColumns 3, intermediateData { freqRatios { 1, 2, 3, 4, 5, 6')
    assert truncated["matrix_values"]["freqRatios"] is None and truncated["status"] == "incompatible"
    complete_array = calc('Pssm ::= { numRows 2, numColumns 3, intermediateData { freqRatios { 1, 2, 3, 4, 5, 6 }')
    assert complete_array["matrix_values"]["freqRatios"] == [[1, 2], [3, 4], [5, 6]]
    assert complete_array["status"] == "partial"


def test_invalid_enclosing_array_parent_is_incompatible_not_missing():
    row = calc(model(data="finalData 7, intermediateData { freqRatios { 1, 2, 3, 4, 5, 6 } }"))
    assert row["array_status"]["pssm.finalData.scores"] == "incompatible"
    assert row["array_status"]["pssm.intermediateData.freqRatios"] == "available"
    assert row["matrix_values"]["scores"] is None
    assert row["status"] == "partial"


@pytest.mark.parametrize("query,code,status", [
    ('set { seq-set { seq { inst { length 3, seq-data iupacaa "ACD" } }, seq { inst { length 3, seq-data iupacaa "EFG" } } } }', "master_compound_unsupported", "unavailable"),
    ('seq { inst { length 3, seq-data ncbi8aa \'010203\'H } }', "master_encoding_unsupported", "unavailable"),
    ('seq { inst { length 3, seq-data ncbistdaa \'0103FF\'H } }', "master_code_invalid", "incompatible"),
    ('seq { inst { length 4, seq-data iupacaa "ACD" } }', "master_length_incompatible", "incompatible"),
    ('seq { inst { seq-data iupacaa "ACD" } }', "master_length_missing", "unavailable"),
    ('seq { inst { length 3, seq-data iupacaa "AcD" } }', "master_code_invalid", "incompatible"),
    ('seq { inst { repr delta, length 3, seq-data iupacaa "ACD" } }', "master_representation_unsupported", "unavailable"),
])
def test_unsupported_ambiguous_and_inconsistent_masters_preserve_positional_matrices(query, code, status):
    row = calc(model("query " + query + ", ", query=False))
    assert row["master"]["status"] == status and row["master"]["column_to_residue"] is None
    assert row["matrix_values"]["scores"] is not None and row["status"] == "partial"
    assert any(i["code"] == code for i in row["issues"])


@pytest.mark.parametrize("encoding", ['ncbistdaa \'010304\'H', 'iupacaa "ACD"', 'ncbieaa "ACD"'])
def test_all_supported_master_encodings_give_the_same_exact_mapping(encoding):
    row = calc(model(f"query seq {{ inst {{ length 3, seq-data {encoding} }} }}, ", query=False))
    assert row["master"]["status"] == "complete" and row["master"]["sequence"] == "ACD"


@pytest.mark.parametrize("encoding", ['ncbistdaa \'010004\'H', 'ncbieaa "A-D"'])
def test_known_gap_code_preserves_native_columns_and_later_indices_on_recalculation(encoding):
    sheet = read(model(f"query seq {{ inst {{ length 3, seq-data {encoding} }} }}, ", query=False))
    row = calculate_blast_pssm_components(sheet)["matrices"][0]
    assert row["status"] == row["master"]["status"] == "complete"
    assert row["master"]["sequence"] == "A-D"
    assert row["master"]["column_to_residue"] == [
        {"column": 0, "master_position": 0, "symbol": "A"},
        {"column": 1, "master_position": None, "symbol": "-"},
        {"column": 2, "master_position": 2, "symbol": "D"}]
    assert calculate_blast_pssm_components(json.loads(json.dumps(sheet)))["matrices"][0] == row


def test_explicit_alphabet_unknown_dimensions_and_nucleotide_native_code_indices():
    explicit = calc(model())
    assert explicit["residue_alphabet"] == ["A", "C"] and explicit["alphabet_source"] == "rowLabels"
    absent = calc(model().replace('rowLabels { "A", "C" }, ', ""))
    assert absent["residue_alphabet"] is None and absent["matrix_values"]["scores"] is not None
    nucleotide = calc("Pssm ::= { isProtein FALSE, numRows 16, numColumns 1, intermediateData { freqRatios { " + ", ".join("0" for _ in range(16)) + " } } }")
    assert nucleotide["residue_alphabet"] == list("-ACMGRSVTWYHKDBN")
    assert nucleotide["alphabet_source"] == "ncbi4na"


def test_saved_json_recalculation_is_pure_and_preserves_input(monkeypatch):
    sheets = [read_blast_pssm((SOURCES / filename).read_bytes(), format="scoremat_asn_text",
        artifact_key="upstream:" + filename, source_ref="pinned-primary-source")
        for filename in ("pssm_freq_ratios.asn", "pssm_zero_fratios.asn")]
    originals = deepcopy(sheets)
    saved = json.loads(json.dumps(sheets, allow_nan=False))
    expected = [calculate_blast_pssm_components(s) for s in sheets]
    def forbidden(*args, **kwargs):
        raise AssertionError("calculation attempted acquisition, filesystem or execution")
    import builtins
    import os
    import socket
    import subprocess
    import requests
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    assert [calculate_blast_pssm_components(s) for s in saved] == expected
    assert sheets == originals


def test_calculator_rejects_nonfinite_json_and_changed_internal_record_identity():
    sheet = read(model())
    sheet["pssms"][0]["native_pssm"]["extra"] = float("nan")
    with pytest.raises(ValueError, match="sheet_invalid"):
        calculate_blast_pssm_components(sheet)
    sheet = read(model())
    sheet["pssms"][0]["pssm_key"] = "biological:name"
    with pytest.raises(ValueError, match="record_identity_invalid"):
        calculate_blast_pssm_components(sheet)


def test_exact_component_shapes_and_numerical_meanings_are_available():
    components = calculate_blast_pssm_components(read(model()))
    assert set(components) == {"schema", "status", "matrices", "issues", "definitions"}
    row = components["matrices"][0]
    assert set(row) == {"pssm_key", "record_ordinal", "status", "dimensions", "is_protein", "native_order",
        "residue_alphabet", "alphabet_source", "matrix_values", "position_diagnostics", "native_statistics",
        "native_parameters", "master", "array_status", "issues"}
    for field in [*("matrix_values." + k for k in row["matrix_values"]),
                  *("position_diagnostics." + k for k in row["position_diagnostics"]),
                  *("native_statistics." + k for k in row["native_statistics"])]:
        assert set(components["definitions"][field]) == {"source", "formula", "units", "population", "missingness", "identity", "uncertainty"}
