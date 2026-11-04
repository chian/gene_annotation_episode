"""Shared master metadata: retained native inputs and explicit synthetic cases.

These checks decode supplied data only; no native BLAST operation is executed.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import pytest

from gene_annotation_episode import blast_pssm_calculators as calculators
from gene_annotation_episode import blast_pssm_master_inputs as masters
from gene_annotation_episode.blast_pssm_inputs import read_blast_pssm


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "verification/tool_graders_blast_pssm_2026-10-26_306/sources"
EXTRACT = masters.extract_blast_pssm_master_metadata


def read(text, *, format="scoremat_asn_text", artifact_key="synthetic:master"):
    return read_blast_pssm(text.encode(), format=format,
                          artifact_key=artifact_key, source_ref="synthetic:319")


def model(*, inst='repr raw, mol aa, length 3, seq-data iupacaa "ACD"',
          query=None, columns="3", extra="", data="intermediateData { freqRatios { 0, 1, 2, 3, 4, 5 } }"):
    if query is None:
        query = f"seq {{ inst {{ {inst} }} }}"
    return (f'Pssm ::= {{ numRows 2, numColumns {columns}, rowLabels {{ "A", "C" }}, '
            f'{extra}' + (f"query {query}, " if query else "") + data + " }")


def row(text):
    sheet = read(text)
    result, = EXTRACT(sheet)["records"]
    assert result["master"] == calculators.calculate_blast_pssm_components(sheet)["matrices"][0]["master"]
    return result


def native_sheet(name):
    return read_blast_pssm((SOURCES / name).read_bytes(), format="scoremat_asn_text",
                          artifact_key="retained:" + name, source_ref="pinned-primary-source")


def native_sequence_oracle():
    # Read the actual primary-source code table separately from the implementation
    # and join it to the original literal bytes, not the populated sheet or score.
    source = (SOURCES / "seqport_util.cpp").read_text()
    table = source.split('" code ncbistdaa ,', 1)[1].split('" }                            -- end of table', 1)[0]
    symbols = re.findall(r'symbol \\"(.)\\"', table)
    assert len(symbols) == 28
    native = (SOURCES / "pssm_freq_ratios.asn").read_text()
    token = re.search(r"seq-data ncbistdaa '([^']*)'H", native).group(1)
    return "".join(symbols[code] for code in bytes.fromhex(token))


def test_retained_native_master_full_sequence_encoding_length_and_mapping():
    sheet = native_sheet("pssm_freq_ratios.asn")
    expected = native_sequence_oracle()
    assert len(expected) == 232
    assert expected[:10] == "QIKDLLVSSS" and expected[-1] == "P"
    result = EXTRACT(sheet)
    assert set(result) == {"schema", "artifact_key", "source_ref", "input_identity", "records", "issues"}
    assert result["schema"] == "blast_pssm_master_metadata_v1"
    assert {k: result[k] for k in ("artifact_key", "source_ref", "input_identity")} == {
        k: sheet[k] for k in ("artifact_key", "source_ref", "input_identity")}
    assert sheet["input_identity"] == {
        "sha256": "56bc1fdf3e1591254e5e031e4b3d84067525954093ab74e3b868a586b7aa613b", "size_bytes": 208617}
    record, = result["records"]
    assert set(record) == {"pssm_key", "record_ordinal", "master", "issues"}
    assert record["pssm_key"] == '["retained:pssm_freq_ratios.asn",0]' and record["record_ordinal"] == 0
    assert record["master"] == dict(status="complete", encoding="ncbistdaa", reported_length=232,
        decoded_length=232, sequence=expected,
        column_to_residue=[dict(column=i, master_position=i, symbol=s) for i, s in enumerate(expected)])
    assert record["master"] == calculators.calculate_blast_pssm_components(sheet)["matrices"][0]["master"]
    assert record["issues"] == result["issues"] == []


def test_retained_native_zero_ratio_checkpoint_has_no_invented_master():
    sheet = native_sheet("pssm_zero_fratios.asn")
    assert sheet["input_identity"] == {
        "sha256": "385d3086fa8e91e2b8dbffec07ff5acd63e9f4450624450cf3e66aec10f26882", "size_bytes": 220408}
    result = EXTRACT(sheet)
    record, = result["records"]
    assert record["master"] == dict(status="unavailable", encoding=None, reported_length=None,
                                    decoded_length=None, sequence=None, column_to_residue=None)
    assert record["issues"] == result["issues"] == [dict(code="master_missing", record_ordinal=0,
                                                        field="pssm.query", character_span=None)]
    assert record["master"] == calculators.calculate_blast_pssm_components(sheet)["matrices"][0]["master"]


def test_concatenated_retained_native_records_keep_order_and_independent_master_states():
    # This multi-record container is synthetic; each constituent is unchanged
    # retained upstream native input. It is not a newly executed native search.
    names = ["pssm_freq_ratios.asn", "pssm_zero_fratios.asn", "pssm_freq_ratios.asn"]
    raw = b"\n".join((SOURCES / name).read_bytes() for name in names)
    sheet = read_blast_pssm(raw, format="scoremat_asn_text", artifact_key="synthetic:native-concatenation",
                          source_ref="synthetic-container-of-retained-native-inputs")
    result = EXTRACT(sheet)
    assert [r["record_ordinal"] for r in result["records"]] == [0, 1, 2]
    assert [r["master"]["status"] for r in result["records"]] == ["complete", "unavailable", "complete"]
    expected = native_sequence_oracle()
    assert [r["master"]["sequence"] for r in result["records"]] == [expected, None, expected]
    assert [r["master"] for r in result["records"]] == [
        r["master"] for r in calculators.calculate_blast_pssm_components(sheet)["matrices"]]
    assert result["issues"] == [dict(code="master_missing", record_ordinal=1,
                                     field="pssm.query", character_span=None)]


@pytest.mark.parametrize("encoding,sequence", [
    ('iupacaa "ACD"', "ACD"), ('ncbieaa "ACD"', "ACD"), ("ncbistdaa '010304'H", "ACD"),
    ("ncbistdaa '01 03\n04'h", "ACD"), ('ncbieaa "A-D"', "A-D"), ("ncbistdaa '010004'H", "A-D"),
    ('iupacaa "UOJ"', "UOJ"), ('ncbieaa "UO*"', "UO*"), ("ncbistdaa '181A1B'H", "UOJ"),
])
def test_supported_native_codes_preserve_exact_original_columns(encoding, sequence):
    result = row(model(inst=f"length 3, seq-data {encoding}"))
    assert result["master"] == dict(status="complete", encoding=encoding.split()[0], reported_length=3,
        decoded_length=3, sequence=sequence, column_to_residue=[
            dict(column=i, master_position=None if symbol == "-" else i, symbol=symbol)
            for i, symbol in enumerate(sequence)])
    assert result["issues"] == []


@pytest.mark.parametrize("inst,code,status,sequence,reported", [
    ('length 3, seq-data ncbi8aa \'010304\'H', "master_encoding_unsupported", "unavailable", None, 3),
    ('length 3, seq-data ncbistdaa \'010304\'B', "master_encoding_unsupported", "unavailable", None, 3),
    ('length 3, seq-data ncbistdaa "010304"', "master_encoding_unsupported", "unavailable", None, 3),
    ('length 3, seq-data ncbistdaa \'0103FF\'H', "master_code_invalid", "incompatible", None, 3),
    ('length 3, seq-data ncbistdaa \'0103F\'H', "master_code_invalid", "incompatible", None, 3),
    ('length 3, seq-data ncbistdaa \'01ZZ04\'H', "master_code_invalid", "incompatible", None, 3),
    ('length 3, seq-data iupacaa "AcD"', "master_code_invalid", "incompatible", None, 3),
    ('length 3, seq-data iupacaa "A-D"', "master_code_invalid", "incompatible", None, 3),
    ('length 3, seq-data iupacaa "A*D"', "master_code_invalid", "incompatible", None, 3),
    ('length 3, seq-data ncbieaa 123', "master_code_invalid", "incompatible", None, 3),
    ('length 3', "master_shape_invalid", "incompatible", None, 3),
    ('length 3, seq-data { iupacaa "ACD", ncbieaa "ACD" }', "master_shape_invalid", "incompatible", None, 3),
    ('seq-data iupacaa "ACD"', "master_length_missing", "unavailable", "ACD", None),
    ('length -1, seq-data iupacaa "ACD"', "master_length_missing", "unavailable", "ACD", None),
    ('length 0, seq-data iupacaa "ACD"', "master_length_incompatible", "incompatible", "ACD", 0),
    ('length 4, seq-data iupacaa "ACD"', "master_length_incompatible", "incompatible", "ACD", 4),
    ('repr delta, length 3, seq-data iupacaa "ACD"', "master_representation_unsupported", "unavailable", None, 3),
    ('mol dna, length 3, seq-data iupacaa "ACD"', "master_molecule_incompatible", "incompatible", None, 3),
    ('mol rna, length 3, seq-data iupacaa "ACD"', "master_molecule_incompatible", "incompatible", None, 3),
])
def test_bad_or_unsupported_master_data_remains_qualified_record(inst, code, status, sequence, reported):
    result = row(model(inst=inst))
    master = result["master"]
    assert master["status"] == status and master["sequence"] == sequence
    assert master["decoded_length"] == (len(sequence) if sequence is not None else None)
    assert master["reported_length"] == reported and master["column_to_residue"] is None
    assert any(issue["code"] == code for issue in result["issues"])


@pytest.mark.parametrize("columns", ["0", "-1", "TRUE", "4", "3, numColumns 3"])
def test_bad_model_column_relation_keeps_decoded_sequence_without_map(columns):
    result = row(model(columns=columns))
    assert result["master"] == dict(status="incompatible", encoding="iupacaa", reported_length=3,
                                    decoded_length=3, sequence="ACD", column_to_residue=None)
    assert result["issues"][-1]["code"] == "master_length_incompatible"


def test_missing_model_columns_keep_decoded_sequence_and_native_missing_field_issue():
    result = row(model().replace("numColumns 3, ", ""))
    assert result["master"] == dict(status="incompatible", encoding="iupacaa", reported_length=3,
                                    decoded_length=3, sequence="ACD", column_to_residue=None)
    assert {i["code"] for i in result["issues"]} == {"asn_required_field_missing", "master_length_incompatible"}


@pytest.mark.parametrize("extra", ["isProtein FALSE, ", "isProtein 1, ", "isProtein TRUE, isProtein TRUE, "])
def test_incompatible_model_molecule_cannot_supply_a_protein_master(extra):
    result = row(model(extra=extra))
    assert result["master"]["status"] == "incompatible"
    assert result["master"]["sequence"] is None
    assert result["issues"][-1]["code"] == "master_molecule_incompatible"


@pytest.mark.parametrize("query,code,status", [
    ("", "master_missing", "unavailable"),
    ('set { seq-set { seq { inst { length 3, seq-data iupacaa "ACD" } }, seq { inst { length 3, seq-data iupacaa "EFG" } } } }',
     "master_compound_unsupported", "unavailable"),
    ("other {}", "master_shape_invalid", "incompatible"),
    ("seq {}", "master_shape_invalid", "incompatible"),
    ("seq { inst 1 }", "master_shape_invalid", "incompatible"),
    ('seq { inst { length 3, length 3, seq-data iupacaa "ACD" } }', "master_shape_invalid", "incompatible"),
])
def test_missing_compound_and_malformed_query_never_select_an_arbitrary_master(query, code, status):
    result = row(model(query=query))
    assert result["master"]["status"] == status and result["master"]["sequence"] is None
    assert result["issues"][-1]["code"] == code


def test_all_records_original_ordinals_issue_spans_and_truncated_tail_survive():
    text = (model() + '\nOther ::= { }\n' + model(query="") + '\n' +
            'Pssm ::= { numRows 2, numColumns 3, query seq { inst { length 3, seq-data iupacaa "EFG" } }')
    sheet = read(text, artifact_key="synthetic:é")
    result = EXTRACT(sheet)
    assert [r["record_ordinal"] for r in result["records"]] == [0, 2, 3]
    assert [r["pssm_key"] for r in result["records"]] == ['["synthetic:é",0]', '["synthetic:é",2]', '["synthetic:é",3]']
    assert [r["master"]["sequence"] for r in result["records"]] == ["ACD", None, "EFG"]
    assert result["records"][2]["master"]["status"] == "complete"
    assert any(i["code"] == "asn_truncated" and i["record_ordinal"] == 3 for i in result["issues"])
    assert any(i["code"] == "asn_type_unsupported" and i["record_ordinal"] == 1 for i in result["issues"])
    expected = deepcopy(sheet["issues"])
    for source, extracted in zip(sheet["pssms"], result["records"]):
        assert extracted["issues"][:len(source["issues"])] == source["issues"]
        for issue in extracted["issues"]:
            if issue not in expected:
                expected.append(issue)
    assert result["issues"] == expected
    assert len(result["issues"]) == len({json.dumps(i, sort_keys=True) for i in result["issues"]})


def test_master_failure_location_points_at_original_native_value():
    sheet = read(model(inst='length 4, seq-data iupacaa "ACD"'))
    issue = EXTRACT(sheet)["records"][0]["issues"][-1]
    assert issue["field"] == "pssm.query.seq.inst.length"
    assert issue["record_ordinal"] == 0
    assert sheet["native_text"][slice(*issue["character_span"])] == "4"


@pytest.mark.parametrize("text,format,code", [
    ("", "scoremat_asn_text", "empty_input"),
    ("not an ASN record", "scoremat_asn_text", "asn_syntax_invalid"),
    ("Pssm ::=", "scoremat_asn_text", "asn_truncated"),
    ("uninterpreted", "ascii_pssm", "unsupported_format"),
])
def test_unreadable_native_inputs_keep_identity_and_original_issues(text, format, code):
    sheet = read(text, format=format)
    result = EXTRACT(sheet)
    assert result["records"] == []
    assert result["issues"] == sheet["issues"]
    assert code in {i["code"] for i in result["issues"]}
    assert result["input_identity"] == dict(sha256=hashlib.sha256(text.encode()).hexdigest(), size_bytes=len(text.encode()))


def test_master_extraction_adds_no_matrix_or_statistic_calculation_issues():
    sheet = read(model(data='finalData { scores { 1 }, lambda 1e-1000, kappa 0.04, h 1 }'))
    result = EXTRACT(sheet)
    assert result["records"][0]["master"]["status"] == "complete"
    assert result["issues"] == []
    assert {i["code"] for i in calculators.calculate_blast_pssm_components(sheet)["issues"]} >= {
        "array_length_incompatible", "real_underflow"}


@pytest.mark.parametrize("change,code", [
    (lambda s: s.update(schema="wrong"), "blast_pssm_sheet_invalid"),
    (lambda s: s.update(extra=None), "blast_pssm_sheet_invalid"),
    (lambda s: s.update(pssms={}), "blast_pssm_sheet_invalid"),
    (lambda s: s["pssms"][0].update(native_pssm=[]), "blast_pssm_record_invalid"),
    (lambda s: s["pssms"][0].update(native_record=[]), "blast_pssm_record_invalid"),
    (lambda s: s["pssms"][0].update(native_params=[]), "blast_pssm_record_invalid"),
    (lambda s: s["pssms"][0].update(record_ordinal=True), "blast_pssm_record_identity_invalid"),
    (lambda s: s["pssms"][0].update(pssm_key="biological-name"), "blast_pssm_record_identity_invalid"),
    (lambda s: s["pssms"].append(deepcopy(s["pssms"][0])), "blast_pssm_record_identity_invalid"),
    (lambda s: s["pssms"][0].update(issues=[{"code": "unknown"}]), "blast_pssm_record_issues_invalid"),
    (lambda s: s["pssms"][0]["native_pssm"].update(extra=float("nan")), "blast_pssm_sheet_invalid"),
    (lambda s: s["pssms"][0]["native_pssm"].update(extra=float("inf")), "blast_pssm_sheet_invalid"),
])
def test_saved_sheet_validation_errors_remain_the_existing_calculator_errors(change, code):
    sheet = read(model())
    change(sheet)
    for function in (EXTRACT, calculators.calculate_blast_pssm_components):
        with pytest.raises(ValueError) as error:
            function(sheet)
        assert error.value.args == (code,)
    assert calculators._validate_sheet is masters._validate_sheet
    assert calculators._master is masters._master


def test_saved_extraction_uses_no_scoring_acquisition_execution_or_input_mutation(monkeypatch):
    import builtins
    import os
    import socket
    import subprocess
    import requests

    sheets = [native_sheet("pssm_freq_ratios.asn"), native_sheet("pssm_zero_fratios.asn"),
              read(model(inst='length 4, seq-data iupacaa "ACD"'))]
    saved = json.loads(json.dumps(sheets, allow_nan=False))
    before = deepcopy(saved)
    expected = [EXTRACT(sheet) for sheet in saved]
    def forbidden(*args, **kwargs):
        raise AssertionError("master extraction attempted scoring, I/O, acquisition or execution")
    for name in ("calculate_blast_pssm_components", "_components", "_array", "_number", "_real"):
        monkeypatch.setattr(calculators, name, forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    actual = [EXTRACT(sheet) for sheet in saved]
    assert actual == expected and saved == before
    actual[0]["input_identity"]["size_bytes"] = 0
    actual[0]["records"][0]["master"]["column_to_residue"][0]["symbol"] = "X"
    actual[1]["records"][0]["issues"][0]["code"] = "changed"
    actual[2]["issues"][0]["character_span"][0] = -1
    assert saved == before
    assert actual[1]["issues"][0]["code"] == "master_missing"
    assert actual[2]["records"][0]["issues"][0]["character_span"][0] >= 0
