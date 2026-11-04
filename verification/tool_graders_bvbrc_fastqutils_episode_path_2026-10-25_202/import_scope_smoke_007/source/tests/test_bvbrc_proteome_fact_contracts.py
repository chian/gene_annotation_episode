"""Finite selector and field-meaning checks, separate from saved-data tests."""
from copy import deepcopy

import pytest

from gene_annotation_episode import bvbrc_proteome_fact_contracts as c


@pytest.mark.parametrize("state,value,valid", [
    ("value", 0, True), ("value", 1.5, True), ("value", None, False),
    ("missing_input", None, True), ("missing_input", 0, False),
    ("zero_denominator", None, True), ("zero_denominator", 0, False),
    ("invalid", None, True), ("invalid", 1, False), ("value", True, False),
])
def test_numeric_fact_cannot_turn_missing_or_invalid_data_into_measured_zero(state, value, valid):
    schema = c.fact_schemas(binding_codes=(), binding_input_kinds=())["measurement"]["properties"]["cell"]
    cell = dict(state=state, value=value, reason_codes=[], source_field_refs=[])
    assert c._Validator(schema).is_valid(cell) is valid


def form(fields):
    return c.requested_form_schema(fields, binding_codes=(), binding_input_kinds=())


def checked(value):
    return c.validate_requested_form(value, binding_codes=(), binding_input_kinds=())


@pytest.mark.parametrize("metric", c.TRACK_METHODS)
def test_each_actual_calculator_track_quantity_has_one_explicit_selector(metric):
    native = c._COMPONENT_DEFS["NativeTrackComponents"]["properties"]
    assert metric in native
    selection = {"kind": "measurement", "target": "track_count", "track_key": "comp_genome_2", "metric": metric}
    result = form({"quantity": selection})
    assert checked(result) == result
    assert result["properties"]["quantity"]["x-bvbrc-proteome"] == selection


@pytest.mark.parametrize("selector", [
    {"kind": "measurement", "target": "association", "association_key": "comp_genome_7/row/0", "metric": "first_hsp_alignment_identity_percent"},
    {"kind": "measurement", "target": "summary", "track_key": "comp_genome_2", "summary": "first_hsp_identity_summary", "metric": "mean"},
    {"kind": "measurement", "target": "selection_count", "track_key": "comp_genome_1", "metric": "unknown"},
    {"kind": "measurement", "target": "inventory_count", "inventory_key": "original", "metric": "observed_header_count"},
    {"kind": "ratio", "track_key": "comp_genome_1", "metric": "complete_selected_reference_fraction"},
    {"kind": "population", "target": "track", "track_key": "comp_genome_2"},
    {"kind": "population", "target": "summary", "track_key": "comp_genome_2", "summary": "subject_endpoint_difference_summary"},
    {"kind": "population", "target": "inventory", "inventory_key": "original"},
    {"kind": "association", "association_key": "comp_genome_2/row/12"},
    {"kind": "selection", "association_key": "comp_genome_2/row/12"},
    {"kind": "requirements", "scope": "all"},
    {"kind": "qualifications", "scope": "all"},
])
def test_every_selector_family_is_closed_and_retains_exact_request(selector):
    result = form({"chosen": selector, "state": {"kind": "request_status", "field": "chosen"}})
    assert checked(result) == result
    result["properties"]["chosen"]["x-bvbrc-proteome"]["unexpected"] = 1
    with pytest.raises(c.ProteomeFactError):
        checked(result)


@pytest.mark.parametrize("selector", [
    {"kind": "measurement", "target": "track_count", "track_key": "ref_genome", "metric": "observed_bound_reference_count"},
    {"kind": "measurement", "target": "track_count", "track_key": "comp_genome_1\n", "metric": "observed_bound_reference_count"},
    {"kind": "association", "association_key": "comp_genome_1/row/01"},
    {"kind": "association", "association_key": "comp_genome_1/row/0\n"},
    {"kind": "population", "target": "inventory", "inventory_key": ""},
    {"kind": "measurement", "target": "track_count", "track_key": "comp_genome_1", "metric": "annotation_probability"},
    {"kind": "measurement", "target": "track_count", "track_key": "comp_genome_1", "metric": True},
    {"kind": "measurement", "path": "/tracks/0/*"},
])
def test_no_wildcard_unknown_confidence_or_noncanonical_identity(selector):
    with pytest.raises(c.ProteomeFactError):
        form({"value": selector})


@pytest.mark.parametrize("fields", [
    {"state": {"kind": "request_status", "field": "missing"}},
    {"state": {"kind": "request_status", "field": "state"}},
    {"a": {"kind": "request_status", "field": "b"}, "b": {"kind": "request_status", "field": "a"}},
])
def test_status_requests_cannot_cycle_or_reference_unrequested_values(fields):
    with pytest.raises(c.ProteomeFactError, match="status_target_invalid"):
        form(fields)


def test_parent_names_and_required_order_preserved_but_schema_cannot_be_weakened():
    result = form({"mean": {"kind": "measurement", "target": "summary", "track_key": "comp_genome_2",
                           "summary": "first_hsp_identity_summary", "metric": "mean"},
                   "status": {"kind": "request_status", "field": "mean"}})
    result["required"].reverse()
    detached = checked(result)
    assert detached == result and detached is not result
    altered = deepcopy(result)
    altered["properties"]["mean"]["properties"]["unit"] = {"type": "string"}
    with pytest.raises(c.ProteomeFactError, match="form_noncanonical"):
        checked(altered)
    altered = deepcopy(result)
    altered["required"] = ["mean", "mean"]
    with pytest.raises(c.ProteomeFactError, match="form_required_conflict"):
        checked(altered)


@pytest.mark.parametrize("kind", c.REFERENCE_KINDS)
def test_references_roundtrip_exact_escaped_analysis_and_saved_pointer(kind):
    pointer = "/components/value/a~1b~0c/0"
    value = c.encode_reference(kind, "analysis:/ α", pointer)
    assert c.decode_reference(value) == (kind, "analysis:/ α", pointer)
    assert c._Validator(c.reference_schema(kind)).is_valid(value)
    with pytest.raises(c.ProteomeFactError):
        c.decode_reference(value.replace("%2F", "%2f"))


@pytest.mark.parametrize("args", [
    ("wildcard", "analysis", "/sheet"),
    ("join", "", "/sheet"),
    ("join", "analysis", "sheet"),
    ("join", "analysis", "/bad~escape"),
    ("join", "\ud800", "/sheet"),
])
def test_invalid_reference_arguments_have_fixed_operand_free_errors(args):
    with pytest.raises(c.ProteomeFactError) as caught:
        c.encode_reference(*args)
    assert str(caught.value) == caught.value.code


def test_finite_requirements_and_numeric_types_preserve_missing_zero_distinction():
    schemas = c.fact_schemas(binding_codes=("proteome_requested_target_missing",),
                             binding_input_kinds=("scientific_metadata",))
    req = schemas["requirements"]["properties"]["requirements"]["items"]["properties"]
    assert "proteome_requested_target_missing" in req["code"]["enum"]
    assert "scientific_metadata" in req["required_input"]["enum"]
    cell_schema = schemas["measurement"]["properties"]["cell"]
    for state, value in (("value", 0), ("missing_input", None)):
        assert c._Validator(cell_schema).is_valid(dict(state=state, value=value, reason_codes=[], source_field_refs=[]))
    assert not c._Validator(cell_schema).is_valid(dict(state="value", value=True, reason_codes=[], source_field_refs=[]))
    assert not c._Validator(cell_schema).is_valid(dict(state="reliable", value=.9, reason_codes=[], source_field_refs=[]))
    assert schemas["selection"]["properties"]["selection"]["anyOf"][1] == {"type": "null"}
    assert "unrecognized" in schemas["association"]["properties"]["native_category"]["anyOf"][0]["enum"]


def test_schema_outputs_are_detached():
    schemas = c.fact_schemas(binding_codes=(), binding_input_kinds=())
    schemas["measurement"]["properties"]["cell"]["oneOf"][0]["properties"]["reason_codes"]["items"]["enum"].clear()
    fresh = c.fact_schemas(binding_codes=(), binding_input_kinds=())
    assert fresh["measurement"]["properties"]["cell"]["oneOf"][0]["properties"]["reason_codes"]["items"]["enum"]
