"""Closed numerical projection contracts; no native execution in these tests."""
from copy import deepcopy
import math

import pytest

from gene_annotation_episode.blast_pairwise_result_views import (
    NATIVE_BLAST_METRICS, FAMILY_SOURCES, native_blast_fact_sources,
    projected_measurements, row_schema, validate_native_blast_result_selector,
)
from gene_annotation_episode.domain import ContractError, RECORD_SCHEMAS, REASONING_SCHEMA, validate_schema
from gene_annotation_episode.communication import validate_closed_schema


def selector(family="pairwise_hsp", metrics=None, rows=None):
    return {"version": "native_blast_result_selector_v1", "acquisition": "complete_bound_bundle",
        "projection": {"family": family, "metrics": metrics or list(NATIVE_BLAST_METRICS[family]),
                       "rows": rows or {"offset": 0, "limit": 20}}}


@pytest.mark.parametrize("program", ["blastn", "blastp", "blastx", "tblastn", "tblastx"])
@pytest.mark.parametrize("family", list(NATIVE_BLAST_METRICS))
def test_every_selected_program_accepts_both_exact_families(program, family):
    selected = selector(family)
    assert validate_native_blast_result_selector(selected, program=program) == selected
    assert native_blast_fact_sources()[FAMILY_SOURCES[family]]["report_schema"]["items"] == row_schema(family)
    validate_closed_schema({"type": "object", "additionalProperties": False,
        "properties": {"numbers": native_blast_fact_sources()[FAMILY_SOURCES[family]]["report_schema"]},
        "required": ["numbers"]})


@pytest.mark.parametrize("mutation", ["extra", "bool_offset", "float_limit", "negative", "zero_limit",
    "empty_metrics", "duplicate_metric", "wrong_family_metric", "empty_keys", "duplicate_key", "both_rows"])
def test_selector_has_no_implicit_defaults_or_cross_family_metric(mutation):
    selected = selector(metrics=["native_score_bits"])
    projection = selected["projection"]
    if mutation == "extra": selected["ranking"] = "bits"
    elif mutation == "bool_offset": projection["rows"]["offset"] = False
    elif mutation == "float_limit": projection["rows"]["limit"] = 1.0
    elif mutation == "negative": projection["rows"]["offset"] = -1
    elif mutation == "zero_limit": projection["rows"]["limit"] = 0
    elif mutation == "empty_metrics": projection["metrics"] = []
    elif mutation == "duplicate_metric": projection["metrics"] *= 2
    elif mutation == "wrong_family_metric": projection["metrics"] = ["observed_distinct_residue_pairs"]
    elif mutation == "empty_keys": projection["rows"] = {"record_keys": []}
    elif mutation == "duplicate_key": projection["rows"] = {"record_keys": ["x", "x"]}
    elif mutation == "both_rows": projection["rows"]["record_keys"] = ["x"]
    with pytest.raises(ContractError):
        validate_native_blast_result_selector(selected, program="blastp")


def test_projection_selects_saved_values_and_never_fabricates_zero():
    row = {"values": {"native_evalue": 0, "paired_identity": None, "query_length": 253},
           "unavailable": {"paired_identity": "incompatible_input"}}
    before = deepcopy(row)
    values, missing = projected_measurements(row, ["native_evalue", "paired_identity"])
    assert values == [{"name": "native_evalue", "value": 0}]
    assert missing == [{"name": "paired_identity", "reason": "incompatible_input"}]
    assert row == before


def test_native_marker_is_host_only_and_closed():
    schema = RECORD_SCHEMAS["observation"]["properties"]["native_blast_pairwise"]
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {"version", "program", "record_key", "search_key",
                                          "hit_ordinal", "hsp_ordinal", "bundle_artifact_ref"}
    assert "native_blast_pairwise" not in REASONING_SCHEMA["properties"]["observations"]["items"]["properties"]
    assert row_schema("pairwise_union")["properties"]["observation_ref"] == {"type": "null"}
    assert row_schema("pairwise_hsp")["properties"]["record_key"]["x-reference-namespace"] == "native_blast_pairwise_row"


def test_finite_json_contract_rejects_nonfinite_metrics():
    with pytest.raises(ContractError):
        validate_schema(math.nan, {"type": "number"})
