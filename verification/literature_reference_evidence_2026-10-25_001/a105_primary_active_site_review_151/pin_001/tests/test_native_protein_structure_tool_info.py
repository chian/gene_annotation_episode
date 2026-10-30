from copy import deepcopy
import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.execution_contracts import canonical, digest, obj
from gene_annotation_episode.protein_structure_contracts import protein_structure_schema_definitions
from gene_annotation_episode.native_protein_structure_contracts import requested_job_from_protein_structure
from gene_annotation_episode.native_protein_structure_tool_info import protein_structure_tool_contracts, protein_structure_tool_information
from importlib import import_module
_f = import_module("verification.tool_graders_protein_structure_execution_2026-10-27_390.fixture_helpers")
job, software = _f.job, _f.software


def bindings():
    return [{"operation": op, "scientific_mode": mode, "software": software()} for op, mode in [
        ("inspect", None), ("extract_sequence", None), ("compare", "fit_then_evaluate_ca"), ("compare", "evaluate_declared_transform_ca")]]


def test_four_fields_and_grouped_modes():
    contracts = protein_structure_tool_contracts(bindings(), resource_kind="local", resource_id="local-selected")
    information = protein_structure_tool_information(bindings(), resource_kind="local", resource_id="local-selected")
    assert len(contracts) == len(information) == 3
    assert len({(r["name"], r["resources"]) for r in contracts}) == 3
    assert all(set(r) == {"name", "description", "resources", "instructions"} for r in information)
    assert all(r["invocation_route"] == {"kind": "commission", "routes": [{"entry_role": "launch", "resource_id": "local-selected", "resource_role": "launch_local"}]} for r in contracts)
    assert "does not" in information[0]["instructions"]
    assert "y@R+t" in information[2]["instructions"]
    with pytest.raises(ValueError): protein_structure_tool_contracts(bindings(), resource_kind="hpc", resource_id="x")


def test_real_schema_standalone_nested_and_two_narrowed_resources(tmp_path):
    b = bindings()
    inspect_schema = protein_structure_tool_contracts([b[0]], resource_kind="local", resource_id="local")[0]["input_schema"]
    extract_schema = protein_structure_tool_contracts([b[1]], resource_kind="local", resource_id="local")[0]["input_schema"]
    original_a = protein_structure_schema_definitions()
    for schema in (inspect_schema, extract_schema):
        original = deepcopy(schema)
        identifier = original.pop("$id")
        assert identifier == "urn:gene-annotation:protein-structure:schema:" + digest(original)
        assert all(schema["$defs"][k] == v for k, v in original_a.items())
        Draft202012Validator.check_schema(schema)
    assert inspect_schema["$id"] != extract_schema["$id"]
    measurements = []
    for name, schema in (("inspect", inspect_schema), ("extract", extract_schema)):
        (tmp_path / (name + "-input-schema.json")).write_text(canonical(schema))
        measurements.append({"operation": name, "serialized_bytes": len(canonical(schema).encode()),
            "outer_definitions_bytes": len(canonical(schema["$defs"]).encode()),
            "inner_resource_bytes": len(canonical(schema["allOf"][0]).encode())})
    (tmp_path / "schema_measurements.json").write_text(canonical(measurements))
    inspect_job = requested_job_from_protein_structure(job(tmp_path / "i", kind="inspect"))
    extract_job = requested_job_from_protein_structure(job(tmp_path / "e", kind="extract_sequence"))
    callable_schema = obj({"operation": {"const": "commission"}, "arguments": {"oneOf": [inspect_schema, extract_schema]}})
    practical_schema = obj({"assignment": obj({"requested_job": {"oneOf": [inspect_schema, extract_schema]}})})
    for request, schema in [(inspect_job, inspect_schema), (extract_job, extract_schema)]:
        assert Draft202012Validator(schema).is_valid(request)
        assert Draft202012Validator(callable_schema).is_valid({"operation": "commission", "arguments": request})
        assert Draft202012Validator(practical_schema).is_valid({"assignment": {"requested_job": request}})
        # This diagnostic establishes that duplicate outer definitions are
        # representational, not necessary for reference resolution. The public
        # generated contract above stays unchanged and keeps 003's definitions.
        without_outer_definitions = deepcopy(schema)
        del without_outer_definitions["$defs"]
        del without_outer_definitions["$id"]
        without_outer_definitions["$id"] = "urn:gene-annotation:protein-structure:schema:" + digest(without_outer_definitions)
        assert Draft202012Validator(obj({"requested_job": without_outer_definitions})).is_valid({"requested_job": request})
    for change in ("operation", "producer", "type", "missing"):
        bad = deepcopy(inspect_job)
        native = bad["native_protein_structure"]
        if change == "operation": native["request"]["operation"] = "extract_sequence"
        if change == "producer": native["software"]["python_sha256"] = "0" * 64
        if change == "type": native["request"]["structure_file"]["byte_length"] = "4"
        if change == "missing": del native["request"]["inventory"]
        assert not Draft202012Validator(callable_schema).is_valid({"operation": "commission", "arguments": bad})
        assert not Draft202012Validator(practical_schema).is_valid({"assignment": {"requested_job": bad}})


def test_comparison_mode_is_narrowed_inside_parent(tmp_path):
    schema = protein_structure_tool_contracts([bindings()[2]], resource_kind="local", resource_id="local")[0]["input_schema"]
    request = requested_job_from_protein_structure(job(tmp_path))
    parent = obj({"requested_job": schema})
    assert Draft202012Validator(parent).is_valid({"requested_job": request})
    request["native_protein_structure"]["request"]["parameters"]["mode"] = "evaluate_declared_transform_ca"
    assert not Draft202012Validator(parent).is_valid({"requested_job": request})
