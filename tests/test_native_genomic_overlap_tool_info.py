"""Actual four-field information and explicit local commissioning shape."""
from copy import deepcopy
from importlib import import_module

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.native_genomic_overlap_contracts import (
    genomic_overlap_execution_schema, requested_job_from_genomic_overlap, validate_genomic_overlap_bindings,
)
from gene_annotation_episode.native_genomic_overlap_tool_info import (
    genomic_overlap_tool_contracts, genomic_overlap_tool_information,
)

f = import_module("verification.tool_graders_genomic_overlap_execution_contracts_2026-10-27_426.fixtures")


def test_four_substantive_information_fields_and_exact_commission_route():
    rows = genomic_overlap_tool_contracts([f.binding()], resource_kind="local", resource_id="selected-local")
    info = genomic_overlap_tool_information([f.binding()], resource_kind="local", resource_id="selected-local")
    assert len(rows) == len(info) == 1
    assert set(info[0]) == {"name", "description", "resources", "instructions"}
    assert info[0]["name"] == "analyze_genomic_region_overlap"
    assert info[0]["resources"] == "local"
    assert rows[0]["invocation_route"] == {"kind": "commission", "routes": [
        {"entry_role": "launch", "resource_id": "selected-local", "resource_role": "launch_local"}]}
    assert set(rows[0]) == set(info[0]) | {"input_schema", "invocation_route"}
    for term in ("unstranded_outer_span", "coordinate_rows_v1", "practical.job.start", "20 GiB", "4 GiB",
                 "zero swap", "-wo -sorted", "genomic_overlap_native_batch_v1", "zero denominator", "half-open"):
        assert term in info[0]["instructions"]


def test_empty_bindings_expose_no_working_operation():
    assert validate_genomic_overlap_bindings([]) == []
    assert genomic_overlap_tool_contracts([], resource_kind="local", resource_id="local") == []
    assert genomic_overlap_tool_information([], resource_kind="local", resource_id="local") == []
    schema = genomic_overlap_execution_schema("RequestedJob", bindings=[])
    Draft202012Validator.check_schema(schema)
    assert not Draft202012Validator(schema).is_valid(requested_job_from_genomic_overlap(f.job()))


@pytest.mark.parametrize("kind,identifier", [("hpc", "x"), ("api", "x"), ("local", ""), ("local", None), ("local", "bad\0")])
def test_invalid_resource_bindings_cannot_claim_an_operation(kind, identifier):
    with pytest.raises(ValueError, match="binding_mismatch"):
        genomic_overlap_tool_contracts([f.binding()], resource_kind=kind, resource_id=identifier)


def test_duplicate_software_binding_is_rejected_and_distinct_deployments_stay_explicit():
    original = f.binding()
    with pytest.raises(ValueError, match="duplicate_binding"):
        validate_genomic_overlap_bindings([original, deepcopy(original)])
    second = deepcopy(original)
    second["software"]["module_root"] = "/second/explicit/snapshot"
    rows = genomic_overlap_tool_contracts([original, second], resource_kind="local", resource_id="local")
    assert len(rows) == 1
    schema = rows[0]["input_schema"]
    for bind in (original, second):
        job = f.job()
        job["software"] = deepcopy(bind["software"])
        assert Draft202012Validator(schema).is_valid(requested_job_from_genomic_overlap(job))
    wrong = f.job()
    wrong["software"]["module_root"] = "/unselected/snapshot"
    assert not Draft202012Validator(schema).is_valid(requested_job_from_genomic_overlap(wrong))


def test_standalone_and_nested_sibling_schemas_resolve_only_their_own_bound_software():
    first = f.binding()
    second = deepcopy(first)
    second["software"]["python_executable"] = "/second/explicit/python"
    a = genomic_overlap_execution_schema("RequestedJob", bindings=[first])
    b = genomic_overlap_execution_schema("RequestedJob", bindings=[second])
    for schema in (a, b):
        Draft202012Validator.check_schema(schema)
    assert a["allOf"][0]["$id"] != b["allOf"][0]["$id"]
    parent = {"type": "object", "properties": {"requested_job": {"oneOf": [a, b]}},
              "required": ["requested_job"], "additionalProperties": False}
    for bind, own_schema, other_schema in ((first, a, b), (second, b, a)):
        job = f.job()
        job["software"] = deepcopy(bind["software"])
        request = requested_job_from_genomic_overlap(job)
        assert Draft202012Validator(own_schema).is_valid(request)
        assert not Draft202012Validator(other_schema).is_valid(request)
        assert Draft202012Validator(parent).is_valid({"requested_job": request})
        request["native_genomic_overlap"]["software"]["python_sha256"] = "f" * 64
        assert not Draft202012Validator(parent).is_valid({"requested_job": request})


def test_information_and_schemas_are_detached_from_original_bindings():
    binding = f.binding()
    rows = genomic_overlap_tool_contracts([binding], resource_kind="local", resource_id="local")
    original = deepcopy(rows)
    binding["software"]["implementation_files"].clear()
    assert rows == original
    rows[0]["input_schema"].clear()
    assert genomic_overlap_tool_contracts([f.binding()], resource_kind="local", resource_id="local") == original
