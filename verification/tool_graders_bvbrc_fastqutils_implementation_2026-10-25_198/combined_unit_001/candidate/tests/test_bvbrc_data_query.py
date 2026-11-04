"""Pure D1 contracts, retained native request oracles and legacy isolation.

Retained response/schema bytes are historical observations, not new live calls.
All punctuation, mixed/open ranges and failure examples here are fixtures.
"""
from copy import deepcopy
from decimal import Decimal
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import urllib.request
from urllib.parse import parse_qsl, urlsplit

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import bvbrc_data_fields as fields_module
from gene_annotation_episode import bvbrc_data_query as query_module
from gene_annotation_episode.bvbrc_data_fields import (
    COLLECTIONS, FIELD_CONTRACT_VERSION, FIELD_REGISTRY, METADATA_FIELDS,
    MOLECULAR_MEASUREMENT_FIELDS, NUMERICAL_FIELDS, SELECTABLE_FIELDS,
)
from gene_annotation_episode.bvbrc_data_query import (
    COMPILER_VERSION, DATA_QUERY_SCHEMA, PREPARED_DATA_QUERY_SCHEMA,
    encode_native_query, validate_data_query,
)
from gene_annotation_episode.domain import ContractError


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "verification/tool_graders_bvbrc_data_contract_2026-10-24"
FROZEN_BYTES = (EVIDENCE / "D1_QUERY_CONTRACT_FROZEN.json").read_bytes()
FROZEN = json.loads(FROZEN_BYTES)
BASE = "https://www.bv-brc.org/api"
FEATURE_IDS = [
    "PATRIC.511145.12.NC_000913.CDS.822959.823720.rev",
    "RefSeq.511145.12.NC_000913.CDS.822959.823720.rev",
]
UNIQUE_KEYS = [
    ("genome", "genome_id"), ("genome_feature", "feature_id"),
    ("genome_sequence", "sequence_id"), ("feature_sequence", "md5"),
    ("protein_family_ref", "family_id"), ("protein_feature", "id"),
    ("sequence_feature", "id"), ("sequence_feature_vt", "id"),
    ("structured_assertion", "id"), ("id_ref", "id"), ("taxonomy", "taxon_id"),
    ("pathway", "id"), ("pathway_ref", "id"), ("subsystem", "id"),
    ("subsystem_ref", "id"), ("enzyme_class_ref", "ec_number"),
    ("gene_ontology_ref", "go_id"), ("protein_structure", "pdb_id"),
    ("ppi", "id"), ("experiment", "exp_id"), ("bioset", "bioset_id"),
    ("bioset_result", "id"),
]


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


def compiled(original, **kwargs):
    result = encode_native_query(original, base_url=BASE, **kwargs)
    Draft202012Validator(PREPARED_DATA_QUERY_SCHEMA).validate(result)
    Draft202012Validator({**FROZEN["schemas"], "$ref": "#/$defs/PreparedQuery"}).validate(result)
    return result


def parameters(prepared):
    return [(pair["name"], pair["value"]) for pair in prepared["native_request"]["query_parameters"]]


def fails(original, code):
    before = deepcopy(original)
    with pytest.raises(ContractError) as raised:
        validate_data_query(original)
    assert str(raised.value) == code
    assert original == before


def test_exact_exports_registry_versions_and_factored_schema_semantics():
    assert hashlib.sha256(FROZEN_BYTES).hexdigest() == (
        "23483aed4a1f84a4ec265a4223f66385322e73a1fc82f9889168f5251586c714")
    assert FIELD_REGISTRY == FROZEN["field_registry"]
    assert len(FIELD_REGISTRY) == 22
    assert sum(len(item["fields"]) for item in FIELD_REGISTRY.values()) == 318
    assert COLLECTIONS == tuple(name for name, _ in UNIQUE_KEYS)
    assert fields_module.__all__ == tuple(FROZEN["exports"]["bvbrc_data_fields.py"])
    for name in ("FIELD_CONTRACT_VERSION", "MOLECULAR_MEASUREMENT_FIELDS",
                 "SUPPLIED_METADATA_FIELDS", "UNAVAILABLE_REASONS", "ISSUE_CODES"):
        assert getattr(fields_module, name) == FROZEN["exports"]["bvbrc_data_fields.py"][name]
    for name, key in (("SELECTABLE_FIELDS", "selectable_fields"),
                      ("NUMERICAL_FIELDS", "numerical_fields"), ("METADATA_FIELDS", "metadata_fields")):
        assert getattr(fields_module, name) == {
            collection: tuple(record[key]) for collection, record in FROZEN["field_registry"].items()}
    assert COMPILER_VERSION == "bvbrc_solr_compiler_v1"
    assert set(query_module.__all__) == {
        "DATA_QUERY_SCHEMA", "PREPARED_DATA_QUERY_SCHEMA", "COMPILER_VERSION",
        "validate_data_query", "encode_native_query"}

    def expand_field(v, defs):
        if isinstance(v, dict):
            if v == {"$ref": "#/$defs/Field"}:
                return defs["Field"]
            return {k: expand_field(x, defs) for k, x in v.items()}
        if isinstance(v, list):
            return [expand_field(x, defs) for x in v]
        return v

    for schema in (DATA_QUERY_SCHEMA, PREPARED_DATA_QUERY_SCHEMA):
        Draft202012Validator.check_schema(schema)
        for name, definition in FROZEN["schemas"]["$defs"].items():
            assert expand_field(schema["$defs"][name], schema["$defs"]) == definition


@pytest.mark.parametrize("collection,unique_key", UNIQUE_KEYS)
def test_all_collection_defaults_use_actual_native_unique_key(collection, unique_key):
    native_bytes = (EVIDENCE / f"schema_{collection}.body").read_bytes()
    native = json.loads(native_bytes)["schema"]
    assert hashlib.sha256(native_bytes).hexdigest() == FIELD_REGISTRY[collection]["schema_sha256"]
    assert native["uniqueKey"] == unique_key
    native_fields = {field["name"]: field for field in native["fields"]}
    for name, spec in FIELD_REGISTRY[collection]["fields"].items():
        source = native_fields[name]
        assert spec["solr_type"] == source["type"]
        assert spec["multi_valued"] == source.get("multiValued", False)
        assert spec["indexed"] == source.get("indexed", True)
        assert spec["stored"] == source.get("stored", True)

    original = request(collection)
    prepared = compiled(original)
    assert prepared["original_request"] == original
    assert prepared["effective_request"] == {
        "version": "bvbrc_data_effective_query_v2", "collection": collection,
        "mode": "page", "filters": [], "fields": [unique_key],
        "sort": [{"field": unique_key, "direction": "asc"}],
        "offset": 0, "limit": 25, "facet": None,
    }
    assert prepared["field_selection"] == {
        "requested_fields": None, "defaulted_fields": [unique_key], "custody_added_fields": []}
    assert prepared["sort_selection"] == {
        "requested_sort": None, "defaulted_sort": [{"field": unique_key, "direction": "asc"}],
        "tie_breaker_added": None}
    for mode in ("count", "facet"):
        extra = {"facet": facet(unique_key)} if mode == "facet" else {}
        metadata = compiled(request(collection, mode, **extra))
        assert parameters(metadata)[:3] == [("q", "*:*"), ("rows", "0"), ("start", "0")]
        assert metadata["effective_request"]["fields"] == []
        assert metadata["effective_request"]["sort"] == []
        assert metadata["query_population"] == prepared["query_population"]


def test_requested_projections_and_sort_order_with_recorded_identity_additions():
    original = request("genome_feature", fields=["aa_length", "product"],
                       sort=[{"field": "aa_length", "direction": "desc"}], offset=5, limit=4)
    prepared = compiled(original, page_selector={"offset": 9, "limit": 3})
    assert prepared["original_request"] == original
    assert prepared["effective_request"]["fields"] == ["aa_length", "product", "feature_id"]
    assert prepared["field_selection"] == {
        "requested_fields": ["aa_length", "product"], "defaulted_fields": [],
        "custody_added_fields": ["feature_id"]}
    assert prepared["sort_selection"] == {
        "requested_sort": [{"field": "aa_length", "direction": "desc"}],
        "defaulted_sort": [], "tie_breaker_added": {"field": "feature_id", "direction": "asc"}}
    assert parameters(prepared) == [
        ("q", "*:*"), ("rows", "3"), ("start", "9"),
        ("fl", "aa_length,product,feature_id"), ("sort", "aa_length desc,feature_id asc")]
    assert prepared["native_request"]["url"] == (
        BASE + "/genome_feature/?q=%2A%3A%2A&rows=3&start=9"
        "&fl=aa_length%2Cproduct%2Cfeature_id&sort=aa_length%20desc%2Cfeature_id%20asc")


def test_supplied_identity_sort_preserves_direction_position_and_omitted_vs_empty_sort():
    sort = [{"field": "genome_id", "direction": "desc"}, {"field": "genome_length", "direction": "asc"}]
    prepared = compiled(request(fields=["genome_id"], sort=sort))
    assert prepared["effective_request"]["sort"] == sort
    assert prepared["sort_selection"]["tie_breaker_added"] is None
    assert prepared["field_selection"]["custody_added_fields"] == []
    empty_sort = compiled(request(sort=[]))
    assert empty_sort["original_request"]["sort"] == []
    assert empty_sort["sort_selection"]["requested_sort"] == []
    assert empty_sort["sort_selection"]["defaulted_sort"] == [{"field": "genome_id", "direction": "asc"}]
    assert "sort" not in validate_data_query(request())


def test_original_and_returned_branches_are_detached_and_keep_integer_float_order():
    original = request("bioset_result", filters=[
        {"field": "log2_fc", "operator": "in", "value": [1, -0.0, 1.0, 1]},
        eq("entity_name", "μ protein"),
    ], fields=["log2_fc", "id"], sort=[])
    before = deepcopy(original)
    validated = validate_data_query(original)
    assert validated == original and validated is not original
    assert list(validated) == list(original)
    assert [type(v) for v in validated["filters"][0]["value"]] == [int, float, float, int]
    validated["filters"][0]["value"].append(8)
    assert original == before
    prepared = compiled(original)
    assert parameters(prepared)[0][1] == '(log2_fc:("1" OR "\\-0.0" OR "1.0" OR "1")) AND (entity_name:"μ protein")'
    prepared["effective_request"]["filters"][0]["value"].append(9)
    prepared["field_selection"]["requested_fields"].append("fpkm")
    assert prepared["original_request"] == original == before
    assert prepared["query_population"]["filters"] == original["filters"]
    assert json.dumps(original, ensure_ascii=False) == json.dumps(before, ensure_ascii=False)


@pytest.mark.parametrize("mode,stem", [("count", "feature_count_solr"), ("facet", "feature_facet_solr_zero")])
def test_exact_retained_native_count_facet_requests_are_independent_oracles(mode, stem):
    native_meta = json.loads((EVIDENCE / (stem + ".meta.json")).read_bytes())
    body = (EVIDENCE / (stem + ".body")).read_bytes()
    assert hashlib.sha256(body).hexdigest() == native_meta["sha256"]
    assert json.loads(body)["response"]["numFound"] == 2
    extra = {"facet": facet()} if mode == "facet" else {}
    prepared = compiled(request("genome_feature", mode,
        [{"field": "feature_id", "operator": "in", "value": FEATURE_IDS}], **extra))
    assert prepared["native_request"]["url"] == native_meta["url"]
    assert parameters(prepared) == parse_qsl(urlsplit(native_meta["url"]).query)
    assert prepared["native_request"]["headers"] == [
        {"name": "User-Agent", "value": "gene-annotation-episode/0.2"},
        {"name": "Accept", "value": native_meta["request_headers"]["Accept"]},
        {"name": "Content-Type", "value": native_meta["request_headers"]["Content-Type"]},
    ]
    assert prepared["native_request"]["method"] == "GET"
    assert prepared["native_request"]["body"] is None
    assert prepared["field_selection"] == {
        "requested_fields": None, "defaulted_fields": [], "custody_added_fields": []}
    assert prepared["sort_selection"] == {
        "requested_sort": None, "defaulted_sort": [], "tie_breaker_added": None}


@pytest.mark.parametrize("symbol,escaped", [
    ("\\", r"\\"), ('"', r'\"'), ("+", r"\+"), ("-", r"\-"), ("!", r"\!"),
    ("(", r"\("), (")", r"\)"), ("{", r"\{"), ("}", r"\}"), ("[", r"\["),
    ("]", r"\]"), ("^", r"\^"), ("~", r"\~"), ("*", r"\*"), ("?", r"\?"),
    (":", r"\:"), ("/", r"\/"), ("&", r"\&"), ("|", r"\|"), ("%", "%"),
    (" ", " "), (",", ","), ("μ", "μ"),
])
def test_solr_literal_escaping_precedes_url_encoding(symbol, escaped):
    prepared = compiled(request(filters=[eq("genome_id", "a" + symbol + "z")]))
    expected = 'genome_id:"a' + escaped + 'z"'
    assert parameters(prepared)[0] == ("q", expected)
    assert parse_qsl(urlsplit(prepared["native_request"]["url"]).query)[0] == ("q", expected)
    assert len(parse_qsl(urlsplit(prepared["native_request"]["url"]).query)) == 5


def test_literal_cannot_inject_query_operators_parameters_or_encoded_delimiters():
    value = 'x") OR *:*&rows=999&fq={!join}%22+\\'
    prepared = compiled(request(filters=[eq("genome_id", value)]))
    expected = r'genome_id:"x\"\) OR \*\:\*\&rows=999\&fq=\{\!join\}%22\+\\"'
    assert parameters(prepared)[0] == ("q", expected)
    decoded = parse_qsl(urlsplit(prepared["native_request"]["url"]).query)
    assert decoded == parameters(prepared)
    assert decoded[1] == ("rows", "25")
    assert all(key != "fq" for key, _ in decoded)
    assert "%2522" in prepared["native_request"]["url"]


@pytest.mark.parametrize("predicate,expression", [
    (bounds(), "genome_length:[10 TO 20]"),
    (bounds(lower_inclusive=False), "genome_length:{10 TO 20]"),
    (bounds(upper_inclusive=False), "genome_length:[10 TO 20}"),
    (bounds(lower_inclusive=False, upper_inclusive=False), "genome_length:{10 TO 20}"),
    (bounds(lower=None, lower_inclusive=False), "genome_length:{* TO 20]"),
    (bounds(upper=None, upper_inclusive=False), "genome_length:[10 TO *}"),
    (bounds(lower=10, upper=10, lower_inclusive=False), "genome_length:{10 TO 10]"),
    (bounds(field="gc_content", lower=-1.5, upper=2e-10), "gc_content:[-1.5 TO 2e-10]"),
])
def test_inclusive_strict_open_and_equal_empty_ranges(predicate, expression):
    assert parameters(compiled(request(filters=[predicate])))[0] == ("q", expression)


@pytest.mark.parametrize("stem,predicate,count", [
    ("solr_range_inclusive", bounds(lower=4639675, upper=4639675), 1),
    ("solr_range_exclusive", bounds(lower=4639675, upper=None, lower_inclusive=False, upper_inclusive=False), 0),
])
def test_retained_native_range_boundaries_match_generated_terms(stem, predicate, count):
    native_bytes = (EVIDENCE / (stem + ".body")).read_bytes()
    meta = json.loads((EVIDENCE / (stem + ".meta.json")).read_bytes())
    assert hashlib.sha256(native_bytes).hexdigest() == meta["sha256"]
    native = json.loads(native_bytes)
    assert native["response"]["numFound"] == count
    prepared = compiled(request(filters=[eq("genome_id", "511145.12"), predicate],
                                fields=["genome_id", "genome_length"], limit=2))
    # The native fixture predates D1's redundant, explicit AND parentheses.
    terms = native["responseHeader"]["params"]["q"].split(" AND ")
    assert parameters(prepared)[0] == ("q", " AND ".join("(" + term + ")" for term in terms))


def test_exists_negation_and_membership_keep_literal_order_and_duplicates():
    conditions = [{"field": "genome_id", "operator": "in", "value": ["B", "A", "B"]},
                  {"field": "genome_length", "operator": "exists", "present": False}]
    prepared = compiled(request(filters=conditions))
    assert parameters(prepared)[0] == (
        "q", '(genome_id:("B" OR "A" OR "B")) AND ((*:* AND -genome_length:[* TO *]))')
    assert prepared["original_request"]["filters"] == conditions
    assert parameters(compiled(request(filters=[conditions[1]])))[0][1] == "(*:* AND -genome_length:[* TO *])"
    positive = {"field": "genome_length", "operator": "exists", "present": True}
    assert parameters(compiled(request(filters=[positive])))[0][1] == "genome_length:[* TO *]"


@pytest.mark.parametrize("collection", COLLECTIONS)
def test_every_field_checks_actual_collection_membership_and_capability_flags(collection):
    for name, spec in FROZEN["field_registry"][collection]["fields"].items():
        assert validate_data_query(request(collection, fields=[name]))["fields"] == [name]
        value = {"int": 1, "long": 1, "float": 1.25, "boolean": True}.get(spec["solr_type"], "x")
        cases = [
            ("exact_filter_supported", request(collection, filters=[eq(name, value)]), "bvbrc_exact_filter_field_not_supported"),
            ("existence_filter_supported", request(collection, filters=[{"field": name, "operator": "exists", "present": True}]), "bvbrc_exists_filter_field_not_supported"),
            ("range_filter_supported", request(collection, filters=[bounds(name)]), "bvbrc_range_filter_field_not_supported"),
            ("sort_supported", request(collection, sort=[{"field": name, "direction": "asc"}]), "bvbrc_sort_field_not_supported"),
            ("facet_supported", request(collection, mode="facet", facet=facet(name)), "bvbrc_facet_field_not_supported"),
        ]
        for flag, selected, code in cases:
            if spec[flag]:
                assert validate_data_query(selected) == selected
            else:
                fails(selected, code)
    assert set(NUMERICAL_FIELDS[collection]).isdisjoint(METADATA_FIELDS[collection])
    assert set(SELECTABLE_FIELDS[collection]) == set(NUMERICAL_FIELDS[collection]) | set(METADATA_FIELDS[collection])


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


def test_finite_numeric_literals_preserve_precision_and_boolean_types():
    integer = 9007199254740993
    prepared = compiled(request("genome_feature", filters=[eq("gene_id", integer)]))
    assert parameters(prepared)[0] == ("q", 'gene_id:"9007199254740993"')
    assert type(prepared["original_request"]["filters"][0]["value"]) is int
    for value, expected in [(1e-300, r'gc_content:"1e\-300"'),
                            (1e30, r'gc_content:"1e\+30"'),
                            (True, 'public:"true"'), (False, 'public:"false"')]:
        field = "public" if type(value) is bool else "gc_content"
        assert parameters(compiled(request(filters=[eq(field, value)])))[0] == ("q", expected)
    for value in (integer, "511145"):
        selected = request("taxonomy", filters=[eq("taxon_id", value)])
        if type(value) is int:
            fails(selected, "bvbrc_filter_value_type_mismatch")
        else:
            assert validate_data_query(selected) == selected
    # Native multivalue int fields take scalar document-membership operands.
    selected = request("taxonomy", filters=[{"field": "lineage_ids", "operator": "in", "value": [1, 2, 1]}])
    assert parameters(compiled(selected))[0] == ("q", 'lineage_ids:("1" OR "2" OR "1")')


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


def test_facet_mode_requires_its_request_and_has_no_document_bucket_limit():
    fails(request(mode="facet"), "bvbrc_mode_parameter_conflict")
    for mode in ("page", "count"):
        fails(request(mode=mode, facet=facet("genome_id")), "bvbrc_mode_parameter_conflict")
    prepared = compiled(request(mode="facet", facet=facet("genome_id", limit=30000,
                                                       offset=50000, include_missing=False, sort="count")))
    assert parameters(prepared)[3:] == [
        ("facet", "true"), ("facet.field", "genome_id"), ("facet.limit", "30000"),
        ("facet.offset", "50000"), ("facet.mincount", "1"), ("facet.missing", "false"), ("facet.sort", "count")]


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


def test_population_identity_ignores_windows_projection_sort_and_mode_but_includes_semantics():
    original = request("genome_feature", filters=[{"field": "feature_id", "operator": "in", "value": FEATURE_IDS}])
    baseline = compiled(original)["query_population"]
    variants = [request("genome_feature", mode="count", filters=original["filters"]),
                request("genome_feature", mode="facet", filters=original["filters"], facet=facet()),
                request("genome_feature", mode="facet", filters=original["filters"], facet=facet("feature_id", limit=100, offset=20)),
                {**original, "fields": ["aa_length"], "sort": [{"field": "start", "direction": "desc"}], "limit": 25000, "offset": 234}]
    for variant in variants:
        assert compiled(variant)["query_population"] == baseline
    assert compiled(original, page_selector={"offset": 22, "limit": 2})["query_population"] == baseline
    assert encode_native_query(original, base_url=BASE + "///")["query_population"] == baseline
    canonical_record = {key: value for key, value in baseline.items() if key != "population_key"}
    assert baseline["population_key"] == hashlib.sha256(json.dumps(
        canonical_record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    assert canonical_record["field_contract_version"] == FIELD_CONTRACT_VERSION
    assert canonical_record["compiler_version"] == COMPILER_VERSION
    assert canonical_record["visibility"] == "public_unauthenticated"
    for other in [request("genome_feature"), request("protein_feature", filters=original["filters"]),
                  request("genome_feature", filters=[eq("feature_id", FEATURE_IDS[0])]),
                  request("genome_feature", filters=[{"field": "feature_id", "operator": "in", "value": list(reversed(FEATURE_IDS))}])]:
        assert compiled(other)["query_population"]["population_key"] != baseline["population_key"]
    assert encode_native_query(original, base_url="http://other.invalid/api")["query_population"]["population_key"] != baseline["population_key"]
    assert encode_native_query(original, base_url=BASE + "/v2")["query_population"]["population_key"] != baseline["population_key"]


def test_unicode_population_hash_uses_utf8_without_ascii_escaping_and_is_deterministic():
    original = request(filters=[eq("genome_id", "μЖ")])
    first = compiled(original)
    second = compiled(original)
    assert json.dumps(first, ensure_ascii=False) == json.dumps(second, ensure_ascii=False)
    population = dict(first["query_population"])
    key = population.pop("population_key")
    assert key == hashlib.sha256(json.dumps(population, sort_keys=True,
        ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    assert key != hashlib.sha256(json.dumps(population, sort_keys=True,
        ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


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


def test_legacy_rql_gt_lt_requests_keep_their_original_native_meanings():
    from gene_annotation_episode.api_bvbrc import request_url

    for operator in ("gt", "lt"):
        meta = json.loads((EVIDENCE / f"range_{operator}.meta.json").read_bytes())
        legacy = {"collection": "genome", "filters": [eq("genome_id", "511145.12"),
            {"field": "genome_length", "operator": operator, "value": 4639675}],
            "fields": ["genome_id", "genome_length"],
            "sort": [{"field": "genome_id", "direction": "asc"}], "limit": 2, "offset": 0}
        assert request_url(BASE, legacy) == meta["url"]
        native = json.loads((EVIDENCE / f"range_{operator}.body").read_bytes())
        assert native == [{"genome_id": "511145.12", "genome_length": 4639675}]
        fails(request(filters=[legacy["filters"][1]]), "bvbrc_data_request_schema_invalid")
