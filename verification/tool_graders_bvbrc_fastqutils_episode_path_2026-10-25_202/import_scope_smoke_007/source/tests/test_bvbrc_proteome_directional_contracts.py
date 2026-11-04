"""Saved-data shape and native-inconsistency contracts; no external acquisition."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.bvbrc_proteome_directional import parse_genome_comparison_directional_report
from gene_annotation_episode.bvbrc_proteome_directional_contracts import (
    ProteomeDirectionalError, directional_schema, validate_directional_report,
)
from gene_annotation_episode.bvbrc_proteome_native_contracts import native_schema


@pytest.fixture
def result():
    path = Path(__file__).parent / "fixtures/bvbrc_proteome_directional/biopython_text_2221L_blastp_001.txt"
    data = path.read_bytes()
    source = {"content": {"source_ref": "fixture", "artifact_field": "artifact_ref", "artifact_ref": path.name,
                          "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data)},
              "body_complete": True, "object_complete": "yes"}
    return parse_genome_comparison_directional_report(data, source=source, declared_format="ncbi_blastall_blastp_pairwise_text_v1", report_key="saved-report")


def test_schema_is_closed_data_and_source_contract_is_exact():
    schema = directional_schema("DirectionalReportResult")
    Draft202012Validator.check_schema(schema)
    source_schema = native_schema("NativeSource")
    for name, definition in source_schema["$defs"].items():
        assert schema["$defs"][name] == definition
    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(schema)
    schema["$defs"]["NativeSource"]["properties"]["trusted"] = {}
    assert "trusted" not in directional_schema("NativeSource")["$defs"]["NativeSource"]["properties"]


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(confidence=1),
    lambda r: r["source"].update(executed=True),
    lambda r: r["source"]["content"].update(byte_count=True),
    lambda r: r["queries"][0].update(ordinal=1),
    lambda r: r["queries"][0].update(banner_ordinal=99),
    lambda r: r["queries"][0].update(boundary="eof_complete"),
    lambda r: r["queries"][1]["subjects"][0]["hsps"][1].update(ordinal=0),
    lambda r: r["queries"][0]["header_text"].update(value="different"),
    lambda r: r["queries"][0]["identifier_token"].update(value="wrong", native_text="wrong"),
    lambda r: r["queries"][0]["header_text"]["locations"][0].update(sha256="0" * 64),
    lambda r: r["queries"][0]["header_text"]["locations"][0]["span"].update(byte_end=10**9),
    lambda r: r["queries"][0]["header_text"]["locations"][0]["span"].update(byte_start=0),
    lambda r: r["queries"][0]["length"].update(value=True),
    lambda r: r["queries"][0]["length"].update(value=0.0),
    lambda r: r["queries"][1]["subjects"][0]["hsps"][1]["expect"].update(value=0),
    lambda r: r["queries"][1]["subjects"][0]["hsps"][1]["expect"].update(value="0"),
    lambda r: r["queries"][1]["subjects"][0]["hsps"][1]["expect"].update(value="Infinity"),
    lambda r: r["queries"][1]["subjects"][0]["hsps"][1]["gap_count"].update(native_text="0"),
    lambda r: r["queries"][0]["descriptions"][0].update(ellipsis_suffix=False),
])
def test_malformed_or_reassociated_projections_rejected(result, mutation):
    mutation(result)
    with pytest.raises(ProteomeDirectionalError) as caught:
        validate_directional_report(result)
    assert caught.value.code == "directional_contract_invalid"
    assert caught.value.path.startswith("/") or caught.value.path == ""
    assert str(caught.value) == "directional_contract_invalid"


def test_contradictory_source_preserved_but_removing_issue_is_invalid():
    path = Path(__file__).parent / "fixtures/bvbrc_proteome_directional/biopython_text_2221L_blastp_001.txt"
    data = path.read_bytes().replace(b"Identities = 353/414", b"Identities = 415/414")
    source = {"content": {"source_ref": "constructed-contradiction", "artifact_field": "artifact_ref", "artifact_ref": "constructed-bytes",
                          "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data)},
              "body_complete": True, "object_complete": "yes"}
    result = parse_genome_comparison_directional_report(data, source=source, declared_format="ncbi_blastall_blastp_pairwise_text_v1", report_key="inconsistent-observation")
    target = result["queries"][1]["subjects"][0]["hsps"][0]
    assert target["identity_count"]["value"] == 415 and target["identity_count"]["state"] == "present"
    assert result["parse_state"] == "partial"
    assert validate_directional_report(result) == result
    target["issues"] = [i for i in target["issues"] if i["code"] != "count_out_of_bounds"]
    with pytest.raises(ProteomeDirectionalError):
        validate_directional_report(result)


def test_all_six_geometry_issues_are_required_at_saved_boundary():
    path = Path(__file__).parent / "fixtures/bvbrc_proteome_directional/biopython_text_2221L_blastp_001.txt"
    data = path.read_bytes().replace(b"Identities = 353/414", b"Identities = 415/413")
    data = data.replace(b"Query: 1   MENS", b"Query: 99   MENS").replace(b"(600 letters)", b"(80 letters)")
    data = data.replace(b"Sbjct: 1   MENS", b"Sbjct: 1   ENS")
    source = {"content": {"source_ref": "constructed-geometry", "artifact_field": "artifact_ref", "artifact_ref": "constructed-bytes",
                          "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data)},
              "body_complete": True, "object_complete": "yes"}
    result = parse_genome_comparison_directional_report(data, source=source, declared_format="ncbi_blastall_blastp_pairwise_text_v1", report_key="geometry")
    target = result["queries"][1]["subjects"][0]["hsps"][0]
    issues = target["issues"] + [i for b in target["traceback_blocks"] for i in b["issues"]]
    expected = {"count_out_of_bounds", "alignment_denominator_mismatch", "coordinate_symbol_count_mismatch", "coordinate_out_of_bounds", "nonprotein_coordinate_order", "traceback_width_mismatch"}
    assert expected <= {i["code"] for i in issues}
    for code in expected:
        changed = deepcopy(result)
        h = changed["queries"][1]["subjects"][0]["hsps"][0]
        h["issues"] = [i for i in h["issues"] if i["code"] != code]
        for block in h["traceback_blocks"]:
            block["issues"] = [i for i in block["issues"] if i["code"] != code]
        with pytest.raises(ProteomeDirectionalError):
            validate_directional_report(changed)


def test_statistic_kind_unused_cells_and_non_json_types_rejected(result):
    stats = result["queries"][2]["statistics"]
    stat = next(s for s in stats if s["kind"] == "matrix")
    stat["integer_value"] = deepcopy(next(s for s in stats if s["kind"] == "gap_open")["integer_value"])
    with pytest.raises(ProteomeDirectionalError):
        validate_directional_report(result)
    with pytest.raises(ProteomeDirectionalError):
        validate_directional_report({"not_plain_json": {1, 2}})
    recursive = {}
    recursive["self"] = recursive
    with pytest.raises(ProteomeDirectionalError):
        validate_directional_report(recursive)


def test_saved_round_trip_does_not_reinfer_native_values(result):
    saved = json.loads(json.dumps(result))
    validated = validate_directional_report(saved)
    assert saved == validated
    validated["queries"][1]["subjects"][0]["hsps"][1]["identity_count"]["value"] = 0
    assert saved["queries"][1]["subjects"][0]["hsps"][1]["identity_count"]["value"] == 115
