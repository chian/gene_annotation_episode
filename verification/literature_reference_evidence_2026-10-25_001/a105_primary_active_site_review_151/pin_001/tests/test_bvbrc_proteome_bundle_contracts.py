"""Closed provider schemas and saved validation without reconstruction."""
import ast
from copy import deepcopy
import hashlib
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import bvbrc_proteome_bundle_contracts as c
from gene_annotation_episode import bvbrc_proteome_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_appservice_contracts import contract_schema
from gene_annotation_episode.bvbrc_proteome_data_contracts import proteome_data_schema
from gene_annotation_episode.bvbrc_proteome_native_contracts import native_schema
from gene_annotation_episode.bvbrc_proteome_sheet_contracts import proteome_sheet_schema
from test_bvbrc_proteome_bundle_resolution import fixture, consume


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


@pytest.mark.parametrize("change", ["extra", "duplicate", "nan", "boolean", "tuple", "unicode"])
def test_parameters_reject_closed_shape_and_non_json_contract_violations(change):
    parameters = fixture(supplementary=False)["parameters"]
    if change == "extra":
        parameters["extra"] = 3
    elif change == "duplicate":
        parameters["native_documents"].append(deepcopy(parameters["native_documents"][0]))
    elif change == "nan":
        parameters["calculation_parameters"]["minimum_identity_fraction"] = float("nan")
    elif change == "boolean":
        parameters["calculation_parameters"]["minimum_identity_fraction"] = True
    elif change == "tuple":
        parameters["native_documents"] = tuple(parameters["native_documents"])
    else:
        parameters["analysis_id"] = "\ud800"
    with pytest.raises(c.ProteomeBundleError, match="parameters_invalid"):
        c.validate_parameters(parameters)


def test_recursive_json_and_detached_parameters():
    parameters = fixture(supplementary=False)["parameters"]
    checked = c.validate_parameters(parameters)
    checked["calculation_parameters"]["track_keys"].clear()
    assert parameters["calculation_parameters"]["track_keys"]
    parameters["recursive"] = parameters
    with pytest.raises(c.ProteomeBundleError):
        c.validate_parameters(parameters)


@pytest.fixture(scope="module")
def saved():
    return consume(fixture())["sheet"]


def test_saved_validation_calls_no_native_constructor_calculator_or_projection(saved, monkeypatch):
    from gene_annotation_episode import bvbrc_proteome_bundle_resolution as resolution
    from gene_annotation_episode import bvbrc_proteome_bundle_projection as projection
    from gene_annotation_episode import bvbrc_proteome_inputs as inputs
    from gene_annotation_episode import bvbrc_proteome_native as native
    from gene_annotation_episode import bvbrc_proteome_joins as joins
    from gene_annotation_episode import bvbrc_proteome_sheet as sheet
    from gene_annotation_episode import bvbrc_proteome_calculators as calculators
    def forbidden(*args, **kwargs):
        raise AssertionError("saved validation cannot reconstruct work")
    for module, names in ((resolution, ("consume_bundle", "build_native_sheet", "build_native_joins", "calculate_native_components", "parse_genome_comparison")),
                          (projection, ("project_requested_facts",)), (inputs, ("index_original_inputs", "read_protein_fasta", "read_feature_metadata", "read_genome_metadata", "read_feature_sequences")),
                          (native, ("parse_genome_comparison",)), (joins, ("build_native_joins",)),
                          (sheet, ("build_native_sheet",)), (calculators, ("calculate_native_components",))):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    checked = c.validate_provider_sheet(saved)
    assert checked == saved and checked is not saved
    checked["supplied_values"].clear()
    assert saved["supplied_values"]


@pytest.mark.parametrize("change", ["analysis", "task", "index_parameter", "primary", "resolution", "source", "result", "links", "unknown"])
def test_saved_copy_and_identity_corruption_is_rejected(saved, change):
    corrupted = deepcopy(saved)
    if change == "analysis":
        corrupted["analysis_id"] = "another"
    elif change == "task":
        corrupted["original_task"]["native_application_id"] = "Homology"
    elif change == "index_parameter":
        corrupted["original_task"]["effective_parameters"]["value"]["user_genomes"][1] = "/wrong.faa"
    elif change == "primary":
        corrupted["parameters"]["primary_document_id"] = "absent"
    elif change == "resolution":
        corrupted["input_resolution"][1]["result_index"] = 1
    elif change == "source":
        corrupted["input_resolution"][0]["content"]["sha256"] = "0" * 64
    elif change == "result":
        corrupted["inventory_results"] = []
    elif change == "links":
        corrupted["supplied_values"][0]["value"]["native_links"] = []
    else:
        corrupted["unknown"] = True
    with pytest.raises(c.ProteomeBundleError):
        c.validate_provider_sheet(corrupted)


def test_saved_wrapper_rejects_unbounded_host_diagnostic_and_numerically_equal_changed_copy(saved):
    corrupted = deepcopy(saved)
    corrupted["diagnostics"].append(dict(code="arbitrary-host-code", phase="publication", path="", severity="error", evidence_refs=[]))
    with pytest.raises(c.ProteomeBundleError, match="saved_sheet_invalid"):
        c.validate_provider_sheet(corrupted)
    corrupted = deepcopy(saved)
    cell = corrupted["native_results"][0]["value"]["reference_rows"][0]["aa_length"]
    cell["value"] = float(cell["value"])
    with pytest.raises(c.ProteomeBundleError, match="saved_sheet_invalid"):
        c.validate_provider_sheet(corrupted)


def test_facade_abi_and_transitive_pin_closure():
    import inspect
    assert adapter.ADAPTER_ID == "bvbrc_proteome" and adapter.ADAPTER_VERSION == "1"
    assert list(inspect.signature(adapter.consume_bundle).parameters) == ["bundle", "artifact_bytes", "supplied_values", "requested_form", "parameters"]
    directory = Path(adapter.__file__).parent
    visited = {"__init__.py"}
    pending = ["bvbrc_proteome_bundle_adapter.py"]
    assets = set()
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        tree = ast.parse((directory / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1:
                modules = [node.module] if node.module else [alias.name for alias in node.names]
                for module in modules:
                    path = module.split(".")[0] + ".py"
                    assert (directory / path).is_file()
                    pending.append(path)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "with_name":
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str) and node.args[0].value.endswith(".json"):
                    assets.add(node.args[0].value)
    assert visited | assets == set(adapter._DEPENDENCIES)
    digest = hashlib.sha256()
    for name in sorted(visited | assets):
        raw = (directory / name).read_bytes()
        digest.update(name.encode() + b"\0" + str(len(raw)).encode() + b"\0" + raw)
    assert adapter.implementation_sha256() == digest.hexdigest()
