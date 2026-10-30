"""Actual typed-form registration for selected RNA comparison facts.

Scientific inputs below are explicitly synthetic. These tests establish schema
and reference traversal, not original receipt authority or episode delivery.
"""
from copy import deepcopy
import importlib

import pytest

from gene_annotation_episode.communication import (
    ReportBoundaryError, form_with_facts, interpretation_schema,
    validate_closed_schema, validate_form,
)
from gene_annotation_episode.rna_structure_comparison_calculations import calculate_rna_comparison_components
from gene_annotation_episode.rna_structure_comparison_views import (
    PROJECTION_SOURCE, project_rna_comparison, rna_comparison_fact_sources,
)
from gene_annotation_episode.rna_structure_result_views import rna_structure_fact_sources
from gene_annotation_episode.runtime import TypedReportContract

f = importlib.import_module(
    "verification.tool_graders_rna_comparison_calculations_2026-10-26_367.fixture_helpers")
RECEIPT = "rna_comparison_receipt:" + "1" * 64
CALCULATION = "rna_comparison_calculation:" + "2" * 64


def form(properties):
    return {"type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False}


def schema():
    return form({"requested": rna_comparison_fact_sources()[PROJECTION_SOURCE]["report_schema"]})


@pytest.fixture(scope="module")
def projected_pair():
    sheet = f.pair(f.feature(energy=-3.0),
        f.feature("V", "GGGAAAUCC", energy=-2.0), energy=f.energy_request())
    components = calculate_rna_comparison_components(sheet)
    selections = [
        {"projection_id": "difference", "family": "energy_comparison",
            "comparison_ids": ["compare-V"], "metrics": ["energy_delta"],
            "include_order": True, "include_tolerance_band": False},
        {"projection_id": "two-structures", "family": "structures",
            "member_ids": ["WT", "V"], "fields": ["dot_bracket"]},
    ]
    return project_rna_comparison(sheet, components, projections=selections,
        result_receipt_key=RECEIPT, calculation_key=CALCULATION)


def resolve(value, namespace):
    return (namespace, value) in {
        ("rna_comparison_receipt", RECEIPT),
        ("rna_comparison_calculation", CALCULATION),
    }


def test_selected_recorded_numbers_and_two_structures_cross_typed_form(projected_pair):
    declaration = schema()
    original = deepcopy(declaration)
    contract = TypedReportContract("Compare the selected RNA variants", declaration, resolve)
    assert declaration == original and contract.schema == original
    assert interpretation_schema(declaration) == form({})
    payload = form_with_facts({}, declaration, {PROJECTION_SOURCE: projected_pair})
    assert validate_form(payload, contract.schema, resolve) == payload
    measurement, = payload["requested"][0]["payload"]["rows"][0]["measurements"]
    assert measurement["metric"] == "energy_delta" and measurement["value"] == 1.0
    assert measurement["unit"] == "kcal/mol" and "input_paths" not in measurement
    assert [r["values"] for r in payload["requested"][1]["payload"]["rows"]] == [
        [{"field": "dot_bracket", "state": "present", "value": "(((...)))", "reason": None}]] * 2
    with pytest.raises(ReportBoundaryError):
        form_with_facts({"requested": projected_pair}, declaration, {PROJECTION_SOURCE: []})


@pytest.mark.parametrize("source", list(rna_structure_fact_sources()))
def test_new_and_original_rna_schemas_coexist_without_changing_either(source):
    old = rna_structure_fact_sources()[source]["report_schema"]
    declaration = form({"old": old, "new": schema()["properties"]["requested"]})
    original = deepcopy(declaration)
    assert validate_closed_schema(declaration) == original
    assert validate_form({"old": [], "new": []}, declaration, lambda *_: False) == {"old": [], "new": []}


@pytest.mark.parametrize("change", [
    lambda n: n.update(description="unregistered meaning"),
    lambda n: n.update(**{"x-source": "execution_rna_structure_comparison_unregistered"}),
    lambda n: n["items"]["oneOf"][0].update(additionalProperties=True),
    lambda n: n["items"]["oneOf"][0]["properties"].update(free_text={"type": "string"}),
    lambda n: n["items"]["oneOf"][0]["properties"]["payload"]["properties"]["rows"].update(minItems=False),
    lambda n: n["items"]["oneOf"][0]["properties"]["payload"]["properties"]["rows"].update(minItems=0.0),
])
def test_changed_registered_shape_cannot_expand_or_change_return(change):
    node = schema()["properties"]["requested"]
    change(node)
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(form({"requested": node}))


def test_registration_does_not_allow_nesting_or_unbound_prose():
    node = schema()["properties"]["requested"]
    with pytest.raises(ReportBoundaryError, match="whole top-level"):
        validate_closed_schema(form({"nested": form({"requested": node})}))
    node.pop("x-source")
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(form({"unbound": node}))
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(form({"interpretation": {"type": "string"}}))


@pytest.mark.parametrize("denied", ["rna_comparison_receipt", "rna_comparison_calculation"])
def test_every_selected_result_identity_needs_current_reference_resolution(projected_pair, denied):
    visited = []
    def resolver(value, namespace):
        visited.append((value, namespace))
        return namespace != denied and resolve(value, namespace)
    with pytest.raises(ReportBoundaryError) as error:
        validate_form({"requested": projected_pair}, schema(), resolver)
    assert error.value.diagnostic["code"] == "unknown_reference"
    assert any(namespace == denied for _, namespace in visited)


def test_semantic_resolution_runs_again_after_schema_cache_hit(projected_pair):
    payload = {"requested": projected_pair}
    assert validate_form(payload, schema(), resolve) == payload
    with pytest.raises(ReportBoundaryError) as error:
        validate_form(payload, schema(), lambda *_: False)
    assert error.value.diagnostic["code"] == "unknown_reference"


@pytest.mark.parametrize("change", [
    lambda c: c.update(input_paths=["/operands/0/original_sheet"]),
    lambda c: c.update(value=float("nan")),
    lambda c: c.update(value="one"),
    lambda c: c.update(unit="confidence"),
])
def test_compact_numerical_return_rejects_expansion_and_wrong_value_types(projected_pair, change):
    rows = deepcopy(projected_pair)
    change(rows[0]["payload"]["rows"][0]["measurements"][0])
    with pytest.raises(ReportBoundaryError):
        validate_form({"requested": rows}, schema(), resolve)
