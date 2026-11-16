"""Closed provider schemas and saved validation without reconstruction."""

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.episodic_workflow.root.a101.library import bvbrc_proteome_bundle_contracts as c
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_appservice_contracts import contract_schema
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_proteome_data_contracts import proteome_data_schema
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_proteome_native_contracts import native_schema
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_proteome_sheet_contracts import proteome_sheet_schema


def test_schema_roots_are_closed_reachable_exact_imports_and_detached():
    for name in ("ProviderParameters", "ProviderSheet", "SuppliedData", "ResolutionOutcome"):
        schema = c.bundle_schema(name)
        Draft202012Validator.check_schema(schema)
        assert schema["$defs"][name]["additionalProperties"] is False
        reached = set()
        def walk(node):
            if type(node) is dict:
                if "$ref" in node:
                    target = node["$ref"][8:]
                    if target not in reached:
                        reached.add(target)
                        walk(schema["$defs"][target])
                for key, value in node.items():
                    if key != "$defs":
                        walk(value)
            elif type(node) is list:
                for value in node:
                    walk(value)
        walk(schema)
        assert reached == set(schema["$defs"])
    root = c.bundle_schema("ProviderSheet")
    for prefix, getter, name in (("Host", contract_schema, "OriginalTask"), ("Native", native_schema, "NativeProjectionResult"),
                                 ("Data", proteome_data_schema, "FeatureSequenceSnapshotResult"),
                                 ("Sheet", proteome_sheet_schema, "NativeSheetResult")):
        def rename(node):
            if type(node) is dict:
                return {k: "#/$defs/" + prefix + v[8:] if k == "$ref" else rename(v) for k, v in node.items()}
            return [rename(v) for v in node] if type(node) is list else node
        for definition, shape in getter(name)["$defs"].items():
            assert root["$defs"][prefix + definition] == rename(shape)
    root["$defs"]["ProviderSheet"]["properties"].clear()
    assert c.bundle_schema("ProviderSheet")["$defs"]["ProviderSheet"]["properties"]


def test_exact_finite_codes_and_required_input_mapping():
    assert type(c.BINDING_CODES) is frozenset and len(c.BINDING_CODES) == 42
    assert set(c.BINDING_INPUT_KINDS) == c.BINDING_CODES
    assert c.BINDING_INPUT_KINDS["proteome_artifact_digest_mismatch"] == "byte_version_evidence"
    assert c.BINDING_INPUT_KINDS["proteome_requested_target_missing"] == "scientific_metadata"
    assert c.PURE_REQUIRED_INPUT_KINDS["complete_artifact_bytes"] == "output_bytes"
    assert c.PURE_REQUIRED_INPUT_KINDS["complete_bytes"] == "input_bytes"
    enums = set()
    for schema in (native_schema("NativeProjectionResult"), proteome_data_schema("ProteinInventoryResult"),
                   proteome_sheet_schema("NativeSheetResult"), proteome_sheet_schema("NativeComponentsResult")):
        for value in schema["$defs"].values():
            required_input = value.get("properties", {}).get("required_input", {})
            enums.update(required_input.get("enum", []))
    assert enums == set(c.PURE_REQUIRED_INPUT_KINDS)
    error = c.ProteomeBundleError("proteome_parameters_invalid", "/field")
    assert error.code == str(error) == "proteome_parameters_invalid" and error.path == "/field"
    with pytest.raises(ValueError, match="unknown_proteome_bundle_failure_code"):
        c.ProteomeBundleError("arbitrary error prose")

