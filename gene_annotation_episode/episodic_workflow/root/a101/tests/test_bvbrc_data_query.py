"""Pure D1 contracts, retained native request oracles and legacy isolation.

Retained response/schema bytes are historical observations, not new live calls.
All punctuation, mixed/open ranges and failure examples here are fixtures.
"""
from copy import deepcopy
from decimal import Decimal
import builtins
import io
import os
import socket
import sqlite3
import subprocess
import urllib.request

import pytest

from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_data_fields import FIELD_REGISTRY, METADATA_FIELDS, MOLECULAR_MEASUREMENT_FIELDS, NUMERICAL_FIELDS
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_data_query import encode_native_query, validate_data_query
from gene_annotation_episode.episodic_workflow.root.a101.domain import ContractError


BASE = "https://www.bv-brc.org/api"


def request(collection="genome", mode="page", filters=None, **kwargs):
    return {"version": "bvbrc_data_request_v2", "collection": collection,
            "mode": mode, "filters": [] if filters is None else filters, **kwargs}


def eq(field, value):
    return {"field": field, "operator": "eq", "value": value}


def bounds(field="genome_length", lower=10, upper=20,
           lower_inclusive=True, upper_inclusive=True):
    return {"field": field, "operator": "range", "lower": lower,
            "upper": upper, "lower_inclusive": lower_inclusive,
            "upper_inclusive": upper_inclusive}


def facet(field="annotation", **kwargs):
    return {"field": field, "offset": 0, "limit": 2, "min_count": 1,
            "sort": "index", "include_missing": True, **kwargs}


def fails(original, code):
    before = deepcopy(original)
    with pytest.raises(ContractError) as raised:
        validate_data_query(original)
    assert str(raised.value) == code
    assert original == before


def test_numeric_identifiers_and_numeric_text_are_not_reclassified_by_projection():
    assert "taxon_id" in METADATA_FIELDS["genome"]
    assert "gene_id" in METADATA_FIELDS["genome_feature"]
    assert FIELD_REGISTRY["protein_feature"]["fields"]["e_value"]["numeric_text_grammar"] == "finite_nonnegative_decimal_scientific"
    assert validate_data_query(request("protein_feature", filters=[eq("e_value", "1.25E-9")]))
    fails(request("protein_feature", filters=[eq("e_value", 1.25e-9)]), "bvbrc_filter_value_type_mismatch")
    fails(request("ppi", filters=[eq("score", 7.9219284)]), "bvbrc_filter_value_type_mismatch")
    assert FIELD_REGISTRY["ppi"]["fields"]["score"]["observed_variants"] == ["finite_json_number"]
    assert NUMERICAL_FIELDS["bioset_result"] == tuple(MOLECULAR_MEASUREMENT_FIELDS)


@pytest.mark.parametrize("original,code", [
    (request(collection="clinical_unknown"), "bvbrc_unknown_collection"),
    (request(fields=["feature_id"]), "bvbrc_unknown_field"),
    (request(filters=[eq("evil:field", "x")]), "bvbrc_unknown_field"),
    (request(sort=[{"field": "tpm", "direction": "asc"}]), "bvbrc_unknown_field"),
    (request(mode="facet", facet=facet("annotation")), "bvbrc_unknown_field"),
    (request(filters=[eq("genome_name", "E. coli")]), "bvbrc_exact_filter_field_not_supported"),
    (request(filters=[eq("genome_id", ["x"])]), "bvbrc_filter_value_shape_mismatch"),
    (request(filters=[eq("genome_id", None)]), "bvbrc_filter_value_shape_mismatch"),
    (request(filters=[{"field": "genome_id", "operator": "in", "value": []}]), "bvbrc_filter_value_shape_mismatch"),
    (request(filters=[{"field": "genome_id", "operator": "in", "value": "x"}]), "bvbrc_filter_value_shape_mismatch"),
    (request(filters=[{"field": "genome_id", "operator": "in", "value": [["x"]]}]), "bvbrc_filter_value_shape_mismatch"),
    (request(filters=[{"field": "genome_id", "operator": "in", "value": ["x", 2]}]), "bvbrc_filter_value_type_mismatch"),
    (request(filters=[bounds(lower=None, upper=None, lower_inclusive=False, upper_inclusive=False)]), "bvbrc_invalid_range_bounds"),
    (request(filters=[bounds(lower=None)]), "bvbrc_invalid_range_bounds"),
    (request(filters=[bounds(upper=None)]), "bvbrc_invalid_range_bounds"),
    (request(filters=[bounds(lower=30, upper=20)]), "bvbrc_invalid_range_bounds"),
    (request(filters=[bounds(lower="2026-10-24")]), "bvbrc_filter_value_type_mismatch"),
    (request(filters=[bounds(field="genome_id")]), "bvbrc_range_filter_field_not_supported"),
    (request(filters=[bounds(field="date_created")]), "bvbrc_unknown_field"),
    (request(sort=[{"field": "genome_id", "direction": "asc"}, {"field": "genome_id", "direction": "desc"}]), "bvbrc_duplicate_sort_field"),
])
def test_named_semantic_failures(original, code):
    fails(original, code)


@pytest.mark.parametrize("field,bad_values", [
    ("genome_id", [1, 1.0, False]), ("genome_length", ["12", 12.0, True]),
    ("gc_content", ["1.25", False]), ("public", [0, 1, "true"]),
])
def test_scalar_type_separation(field, bad_values):
    for value in bad_values:
        fails(request(filters=[eq(field, value)]), "bvbrc_filter_value_type_mismatch")
        fails(request(filters=[{"field": field, "operator": "in", "value": [value]}]), "bvbrc_filter_value_type_mismatch")
    if field in ("genome_length", "gc_content"):
        fails(request(filters=[bounds(field, lower=True)]), "bvbrc_filter_value_type_mismatch")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_numbers_are_rejected_anywhere_with_stable_code(value):
    for original in (request(filters=[eq("gc_content", value)]), request(limit=value),
                     request(filters=[bounds(lower=value)]), request(extra={"nested": [value]})):
        with pytest.raises(ContractError, match="^bvbrc_nonfinite_number$"):
            validate_data_query(original)
    with pytest.raises(ContractError, match="^bvbrc_nonfinite_number$"):
        encode_native_query(request(), base_url=BASE, page_selector={"offset": value, "limit": 2})


@pytest.mark.parametrize("original", [
    None, [], {}, request(version="old"), request(mode="unknown"),
    request(fields=[]), request(fields=["genome_id", "genome_id"]), request(sort=None),
    request(offset=-1), request(offset=False), request(offset=2.0), request(limit=0),
    request(limit=25001), request(limit=True), request(limit=2.0), request(url=BASE),
    request(headers={"Accept": "application/json"}), request(auth="token"),
    request(filters=()), request(filters=[eq("genome_id", Decimal("1.2"))]),
    request(filters=[{"field": "genome_length", "operator": "gt", "value": 2}]),
    request(filters=[{"field": "genome_id", "operator": "eq"}]),
    request(filters=[{"field": "genome_id", "operator": "exists", "present": 1}]),
    request(filters=[{**eq("genome_id", "x"), "q": "*:*"}]),
    request(mode="facet", facet=facet(limit=0)), request(mode="facet", facet=facet(offset=0.0)),
])
def test_closed_json_syntax_failures(original):
    fails(original, "bvbrc_data_request_schema_invalid")


def test_non_json_keys_and_cycles_fail_without_mutating_inputs():
    with pytest.raises(ContractError, match="^bvbrc_data_request_schema_invalid$"):
        validate_data_query({**request(), 1: "not a JSON key"})
    original = request()
    original["filters"].append(original)
    with pytest.raises(ContractError, match="^bvbrc_data_request_schema_invalid$"):
        validate_data_query(original)
    assert original["filters"][0] is original


@pytest.mark.parametrize("mode", ["count", "facet"])
@pytest.mark.parametrize("key,value", [("fields", []), ("sort", []), ("offset", 0), ("limit", 1)])
def test_count_and_facet_reject_page_arguments_even_when_empty(mode, key, value):
    extra = {"facet": facet("genome_id")} if mode == "facet" else {}
    fails(request(mode=mode, **extra, **{key: value}), "bvbrc_mode_parameter_conflict")


@pytest.mark.parametrize("selector", [{}, [], {"offset": 1}, {"offset": 1, "limit": 0},
    {"offset": False, "limit": 2}, {"offset": 1.0, "limit": 2}, {"offset": 1, "limit": 25001},
    {"offset": -1, "limit": 2}, {"offset": 1, "limit": 2, "fields": []}])
def test_page_selector_is_exact_closed_pair(selector):
    with pytest.raises(ContractError, match="^bvbrc_invalid_page_selector$"):
        encode_native_query(request(), base_url=BASE, page_selector=selector)


def test_page_selector_never_applies_to_count_or_facet():
    for mode in ("count", "facet"):
        extra = {"facet": facet("genome_id")} if mode == "facet" else {}
        with pytest.raises(ContractError, match="^bvbrc_invalid_page_selector$"):
            encode_native_query(request(mode=mode, **extra), base_url=BASE,
                                page_selector={"offset": 0, "limit": 1})


@pytest.mark.parametrize("endpoint", [None, 4, "file:///tmp/api", "ftp://example.org/api",
    "https:///api", "https://user:password@example.org/api", "https://user@example.org/api",
    BASE + "?q=x", BASE + "#fragment", "https://[invalid/api"])
def test_configured_endpoint_rejects_non_http_credentials_query_and_fragment(endpoint):
    with pytest.raises(ContractError, match="^bvbrc_invalid_base_url$"):
        encode_native_query(request(), base_url=endpoint)


def test_pure_calls_need_no_files_network_store_or_native_execution(monkeypatch):
    def prohibited(*_args, **_kwargs):
        raise AssertionError("pure query preparation attempted external I/O")

    originals = [request(), request(mode="count", filters=[eq("genome_id", "511145.12")]),
                 request(mode="facet", facet=facet("genome_id"))]
    with monkeypatch.context() as patch:
        for module, attribute in [(builtins, "open"), (io, "open"), (os, "open"),
            (socket, "socket"), (socket, "create_connection"), (urllib.request, "urlopen"),
            (urllib.request, "build_opener"), (subprocess, "Popen"), (os, "system"), (sqlite3, "connect")]:
            patch.setattr(module, attribute, prohibited)
        for original in originals:
            assert validate_data_query(original) == original
            result = encode_native_query(original, base_url=BASE)
            assert result["original_request"] == original
        with pytest.raises(ContractError, match="^bvbrc_unknown_collection$"):
            validate_data_query(request(collection="unsupported"))

