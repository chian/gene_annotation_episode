"""Exact recorded RNA form recognition, without widening the model grammar."""
from copy import deepcopy

import pytest

from gene_annotation_episode.communication import (
    ReportBoundaryError, form_with_facts, interpretation_schema,
    validate_closed_schema, validate_form,
)
from gene_annotation_episode.rna_structure_result_views import (
    FAMILY_SOURCES, rna_structure_fact_sources,
)
from gene_annotation_episode.runtime import TypedReportContract


def form(fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


@pytest.mark.parametrize("source", list(rna_structure_fact_sources()))
def test_each_exact_rna_fact_constructs_actual_typed_contract(source):
    schema = form({"requested": rna_structure_fact_sources()[source]["report_schema"]})
    original = deepcopy(schema)
    contract = TypedReportContract("Inspect requested RNA measurements", schema, lambda *_: False)
    assert contract.schema == original and schema == original
    assert interpretation_schema(schema) == form({})
    assert form_with_facts({}, schema, {source: []}) == {"requested": []}
    assert validate_form({"requested": []}, contract.schema, lambda *_: False) == {"requested": []}


@pytest.mark.parametrize("source", list(rna_structure_fact_sources()))
def test_rna_fact_cannot_be_nested(source):
    node = rna_structure_fact_sources()[source]["report_schema"]
    with pytest.raises(ReportBoundaryError, match="whole top-level fields"):
        validate_closed_schema(form({"nested": form({"requested": node})}))


@pytest.mark.parametrize("change", [
    lambda node: node.update(description="extra unregistered meaning"),
    lambda node: node.update(**{"x-source": "execution_rna_structure_unregistered"}),
    lambda node: node["items"].update(additionalProperties=True),
    lambda node: node["items"]["properties"].update(free_text={"type": "string"}),
    lambda node: node["items"]["properties"]["calculation_parameters"]["properties"]["topology"]["properties"]["long_stem_min_pairs"].update(minimum=True),
    lambda node: node["items"]["properties"]["calculation_parameters"]["properties"]["topology"]["properties"]["long_stem_min_pairs"].update(minimum=1.0),
])
def test_only_the_entire_exact_registered_schema_is_accepted(change):
    node = rna_structure_fact_sources()[FAMILY_SOURCES["summary"]]["report_schema"]
    change(node)
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(form({"requested": node}))


def test_nullable_rna_source_still_needs_actual_reference_resolution():
    schema = form({"failure": rna_structure_fact_sources()[FAMILY_SOURCES["failure"]]["report_schema"]})
    row = {"family": "failure", "record_key": "original-rna", "row_key": "original-rna:failure:0",
        "source_ref": None, "result_receipt_key": "receipt-one", "issue_ordinal": 0,
        "operation": "analyze_rna_secondary_structure_features", "mode": "supplied_features",
        "issue": {"stage": "native", "code": "rna_native_dependency_missing", "record_key": "original-rna",
            "field": "/software/rna_module_sha256", "index": None, "artifact_role": None}}
    visited = []
    def resolve(value, namespace):
        visited.append((value, namespace))
        return namespace != "execution_result"
    assert validate_form({"failure": [row]}, schema, resolve)["failure"][0]["source_ref"] is None
    assert visited == [(row["row_key"], "native_rna_structure_row"),
        (row["result_receipt_key"], "native_rna_structure_result_receipt")]
    row["source_ref"] = "source-not-received"
    with pytest.raises(ReportBoundaryError) as error:
        validate_form({"failure": [row]}, schema, resolve)
    assert error.value.diagnostic["code"] == "unknown_reference"


def test_rna_registration_does_not_allow_unrestricted_interpretations():
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(form({"interpretation": {"type": "string"}}))
    node = rna_structure_fact_sources()[FAMILY_SOURCES["summary"]]["report_schema"]
    node.pop("x-source")
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(form({"unbound": node}))
