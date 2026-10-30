"""Contract and mutation regressions for pure schema-construction reuse."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from importlib import import_module, util
from pathlib import Path
import sys

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import native_protein_structure_contracts as contracts
from gene_annotation_episode.execution_contracts import digest, obj

_fixtures = import_module(
    "verification.tool_graders_protein_structure_execution_2026-10-27_390.fixture_helpers")


@pytest.fixture(scope="module")
def before():
    path = Path(__file__).resolve().parents[1] / (
        "verification/tool_graders_protein_structure_schema_reuse_2026-10-27_416/"
        "prechange/native_protein_structure_contracts.py")
    name = "gene_annotation_episode._native_protein_structure_before_416"
    spec = util.spec_from_file_location(name, path)
    module = util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop(name, None)


@pytest.mark.parametrize("type_name", [
    "Software", "ScientificRequest", "NativeProteinJob", "RequestedProteinJob",
    "NativeProteinBinding", "NativeProteinRunPlan", "NativeProteinBundle",
    "WorkerInput", "NativeProteinResult", "FileIdentity",
])
def test_public_schema_and_content_identity_match_prechange(before, type_name):
    actual = contracts.protein_structure_execution_schema(type_name)
    assert actual == before.protein_structure_execution_schema(type_name)
    body = deepcopy(actual)
    identifier = body.pop("$id")
    assert identifier == "urn:gene-annotation:protein-structure:schema:" + digest(body)


@pytest.mark.parametrize("inner", [False, True])
def test_export_mutation_cannot_change_later_schema_or_validation(inner):
    value = _fixtures.software()
    assert contracts.validate_protein_structure_software(value) == value
    original = contracts.protein_structure_execution_schema("Software")
    exported = contracts.protein_structure_execution_schema("Software")
    target = exported["allOf"][0] if inner else exported
    target["$defs"]["Software"]["properties"]["python_executable"]["pattern"] = "^BROKEN$"
    target["$defs"]["NativeProteinJob"]["properties"]["environment"]["additionalProperties"] = False
    assert contracts.protein_structure_execution_schema("Software") == original
    checked = contracts.validate_protein_structure_software(value)
    checked["implementation_files"].clear()
    assert contracts.validate_protein_structure_software(value) == value


@pytest.mark.parametrize("kind", ["inspect", "extract_sequence", "compare"])
@pytest.mark.parametrize("bad_length", [True, 4.0, "4", float("nan"), float("inf")])
def test_warm_validation_still_checks_each_native_type(kind, bad_length):
    value, _ = _fixtures.requests(kind)
    assert contracts.validate_protein_structure_request(value) == value
    changed = deepcopy(value)
    file = (changed["structure_file"] if kind == "inspect" else
            changed["selection"]["file_identity"] if kind == "extract_sequence" else
            changed["fixed_selection"]["file_identity"])
    file["byte_length"] = bad_length
    with pytest.raises(ValueError, match="invalid_schema"):
        contracts.validate_protein_structure_request(changed)
    assert contracts.validate_protein_structure_request(value) == value


@pytest.mark.parametrize("change", ["tuple", "nul", "extra", "wrong_role"])
def test_warm_validation_preserves_plain_types_and_relations(change):
    value, _ = _fixtures.requests("extract_sequence")
    contracts.validate_protein_structure_request(value)
    changed = deepcopy(value)
    if change == "tuple":
        changed["supplied_metadata_files"] = ()
    elif change == "nul":
        changed["selection"]["file_identity"]["artifact_ref"] = "bad\0reference"
    elif change == "extra":
        changed["unselected_field"] = 1
    else:
        changed["selection"]["structure_role"] = "fixed"
    with pytest.raises(ValueError):
        contracts.validate_protein_structure_request(changed)


def test_bound_schemas_remain_specific_to_each_current_binding(before, tmp_path):
    selected = _fixtures.software()
    changed = deepcopy(selected)
    changed["python_sha256"] = "0" * 64
    bindings = [
        [{"operation": "inspect", "scientific_mode": None, "software": selected}],
        [{"operation": "extract_sequence", "scientific_mode": None, "software": selected}],
        [{"operation": "extract_sequence", "scientific_mode": None, "software": changed}],
        [{"operation": "compare", "scientific_mode": "fit_then_evaluate_ca", "software": selected}],
        [{"operation": "compare", "scientific_mode": "evaluate_declared_transform_ca", "software": selected}],
    ]
    schemas = [contracts.protein_structure_execution_schema("RequestedProteinJob", bindings=b) for b in bindings]
    for schema, binding in zip(schemas, bindings):
        assert schema == before.protein_structure_execution_schema("RequestedProteinJob", bindings=binding)
    assert len({s["$id"] for s in schemas}) == len(schemas)
    first = contracts.requested_job_from_protein_structure(_fixtures.job(tmp_path / "i", kind="inspect"))
    second = contracts.requested_job_from_protein_structure(_fixtures.job(tmp_path / "e", kind="extract_sequence"))
    altered = deepcopy(second)
    altered["native_protein_structure"]["software"] = changed
    union = Draft202012Validator(obj({"requested_job": {"oneOf": schemas[:3]}}))
    for request, index in [(first, 0), (second, 1), (altered, 2)]:
        assert union.is_valid({"requested_job": request})
        assert [Draft202012Validator(s).is_valid(request) for s in schemas[:3]] == [j == index for j in range(3)]
    bindings[0][0]["software"]["python_sha256"] = "1" * 64
    assert Draft202012Validator(schemas[0]).is_valid(first)
    newest = contracts.protein_structure_execution_schema("RequestedProteinJob", bindings=bindings[0])
    assert not Draft202012Validator(newest).is_valid(first)


def test_shared_validator_does_not_share_payload_outcomes_between_threads():
    valid, _ = _fixtures.requests("extract_sequence")
    invalid = deepcopy(valid)
    invalid["selection"]["structure_role"] = "moving"
    contracts.validate_protein_structure_request(valid)

    def run(index):
        value = valid if index % 2 == 0 else invalid
        try:
            return contracts.validate_protein_structure_request(value) == valid
        except ValueError as error:
            assert str(error) == "conflicting_identity"
            return False

    with ThreadPoolExecutor(max_workers=4) as executor:
        assert list(executor.map(run, range(32))) == [i % 2 == 0 for i in range(32)]
