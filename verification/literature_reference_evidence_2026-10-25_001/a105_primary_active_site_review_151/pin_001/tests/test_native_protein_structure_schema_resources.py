"""Fixed schema resources stay private; current payload checks still execute."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from importlib import import_module, util
from pathlib import Path
import sys

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.exceptions import NoSuchResource

from gene_annotation_episode import native_protein_structure_contracts as contracts
from gene_annotation_episode.execution_contracts import digest, obj
from gene_annotation_episode.native_protein_structure_worker import execute_protein_structure_request

_fixtures = import_module(
    "verification.tool_graders_protein_structure_execution_2026-10-27_390.fixture_helpers")
_TYPES = (
    "Software", "ScientificRequest", "NativeProteinJob", "RequestedProteinJob",
    "NativeProteinBinding", "NativeProteinRunPlan", "NativeProteinBundle",
    "WorkerInput", "NativeProteinResult", "FileIdentity",
)


@pytest.fixture(scope="module")
def before():
    path = Path(__file__).resolve().parents[1] / (
        "verification/tool_graders_protein_structure_schema_resources_2026-10-27_417/"
        "prechange/native_protein_structure_contracts.py")
    name = "gene_annotation_episode._native_protein_structure_before_417"
    spec = util.spec_from_file_location(name, path)
    module = util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop(name, None)


def _request_file(request):
    if request["operation"] == "inspect":
        return request["structure_file"]
    if request["operation"] == "extract_sequence":
        return request["selection"]["file_identity"]
    return request["fixed_selection"]["file_identity"]


@pytest.mark.parametrize("type_name", _TYPES)
def test_exact_schema_and_both_resources_match_prechange(before, monkeypatch, type_name):
    captured = []
    strict = contracts._STRICT

    def construct(document, *, registry):
        captured.append(registry)
        return strict(document, registry=registry)

    contracts._execution_validator.cache_clear()
    monkeypatch.setattr(contracts, "_STRICT", construct)
    validator = contracts._execution_validator(type_name)
    original = before.protein_structure_execution_schema(type_name)
    assert validator.schema == original == contracts.protein_structure_execution_schema(type_name)
    assert len(captured) == 1
    registry, = captured
    resources = (original, original["allOf"][0])
    assert set(registry) == {resource["$id"] for resource in resources}
    for resource in resources:
        body = deepcopy(resource)
        identifier = body.pop("$id")
        assert identifier == "urn:gene-annotation:protein-structure:schema:" + digest(body)
        assert registry.contents(identifier) == resource
    assert "$schema" not in original["allOf"][0]
    assert contracts._execution_validator(type_name) is validator


def test_one_construction_crawl_and_every_warm_payload_checked(monkeypatch):
    requests = [_fixtures.requests(kind)[0] for kind in ("inspect", "extract_sequence", "compare")]
    crawls, validated = [], []
    crawl = Registry.crawl

    def record_crawl(registry):
        crawls.append(tuple(registry))
        return crawl(registry)

    contracts._execution_validator.cache_clear()
    monkeypatch.setattr(Registry, "crawl", record_crawl)
    validator = contracts._execution_validator("ScientificRequest")
    assert len(crawls) == 1
    iter_errors = contracts._STRICT.iter_errors

    def record_validation(instance, value, *args, **kwargs):
        if instance is validator:
            validated.append(deepcopy(value))
        yield from iter_errors(instance, value, *args, **kwargs)

    monkeypatch.setattr(contracts._STRICT, "iter_errors", record_validation)
    for request in requests:
        assert contracts._checked(request, "ScientificRequest") == request
        request["unexpected_field"] = "invalid current payload"
        with pytest.raises(ValueError, match="invalid_schema"):
            contracts._checked(request, "ScientificRequest")
        del request["unexpected_field"]
        assert contracts._checked(request, "ScientificRequest") == request
    assert len(validated) == 9
    assert len(crawls) == 1


@pytest.mark.parametrize("kind", ["inspect", "extract_sequence", "compare"])
@pytest.mark.parametrize("bad_length", [True, 4.0, "4", float("nan"), float("inf"), -float("inf")])
def test_warm_inner_reference_preserves_strict_counts(before, kind, bad_length):
    request, _ = _fixtures.requests(kind)
    current = contracts._execution_validator("ScientificRequest")
    original = before._execution_validator("ScientificRequest")
    assert current.is_valid(request) and original.is_valid(request)
    bad = deepcopy(request)
    _request_file(bad)["byte_length"] = bad_length
    assert not current.is_valid(bad) and not original.is_valid(bad)
    with pytest.raises(ValueError, match="invalid_schema"):
        contracts.validate_protein_structure_request(bad)


@pytest.mark.parametrize("bad_number", [True, "1.0", float("nan"), float("inf"), -float("inf")])
def test_warm_inner_reference_preserves_finite_number_type(before, bad_number):
    request, _ = _fixtures.requests("compare")
    request["parameters"]["distance_threshold_A"] = 1.0
    assert contracts.validate_protein_structure_request(request) == request
    request["parameters"]["distance_threshold_A"] = bad_number
    assert not contracts._execution_validator("ScientificRequest").is_valid(request)
    assert not before._execution_validator("ScientificRequest").is_valid(request)
    with pytest.raises(ValueError, match="invalid_schema"):
        contracts.validate_protein_structure_request(request)


@pytest.mark.parametrize("change", ["tuple", "dict_subclass", "int_subclass", "nul", "wrong_role"])
def test_plain_types_and_relationships_remain_checked(change):
    request, _ = _fixtures.requests("extract_sequence")
    contracts.validate_protein_structure_request(request)
    if change == "tuple":
        request["supplied_metadata_files"] = ()
    elif change == "dict_subclass":
        request = type("UnplainDict", (dict,), {})(request)
    elif change == "int_subclass":
        _request_file(request)["byte_length"] = type("UnplainInt", (int,), {})(4)
    elif change == "nul":
        _request_file(request)["artifact_ref"] += "\0"
    else:
        request["selection"]["structure_role"] = "moving"
    with pytest.raises(ValueError, match="conflicting_identity" if change == "wrong_role" else "invalid_schema"):
        contracts.validate_protein_structure_request(request)


@pytest.fixture(scope="module")
def native_results():
    results = {}
    software = _fixtures.software()
    for kind in ("inspect", "extract_sequence", "compare"):
        request, inputs = _fixtures.requests(kind)
        results[kind] = execute_protein_structure_request(request, input_bytes=inputs, software=software)
    return results


@pytest.mark.parametrize("kind", ["inspect", "extract_sequence", "compare"])
def test_all_native_alternatives_validate_without_warm_discovery(before, native_results, monkeypatch, kind):
    value = native_results[kind]
    original = before.validate_native_protein_structure_result(value)
    assert contracts.validate_native_protein_structure_result(value) == original

    def no_crawl(_registry):
        pytest.fail("warm native validation repeated schema resource discovery")

    monkeypatch.setattr(Registry, "crawl", no_crawl)
    returned = contracts.validate_native_protein_structure_result(value)
    assert returned == value and returned is not value
    returned["request"]["operation"] = "changed detached result"
    for mutate in ("unexpected", "strict_count", "version"):
        changed = deepcopy(value)
        if mutate == "unexpected":
            changed["unexpected"] = 1
        elif mutate == "strict_count":
            _request_file(changed["request"])["byte_length"] = True
        else:
            changed["version"] = "unselected_native_format"
        with pytest.raises(ValueError, match="invalid_schema"):
            contracts.validate_native_protein_structure_result(changed)
    assert contracts.validate_native_protein_structure_result(value) == value


@pytest.mark.parametrize("inner", [False, True])
def test_public_documents_cannot_mutate_prepared_resources(before, inner):
    value, _ = _fixtures.requests("extract_sequence")
    validator = contracts._execution_validator("ScientificRequest")
    original = deepcopy(validator.schema)
    exported = contracts.protein_structure_execution_schema("ScientificRequest")
    target = exported["allOf"][0] if inner else exported
    target["$defs"]["FileIdentity"]["properties"]["byte_length"]["type"] = "string"
    target["$defs"]["ExtractRequest"]["required"] = []
    target["$id"] = "https://example.invalid/unselected-schema"
    assert validator.schema == original == before.protein_structure_execution_schema("ScientificRequest")
    assert contracts.validate_protein_structure_request(value) == value
    bad = deepcopy(value)
    _request_file(bad)["byte_length"] = "4"
    assert not validator.is_valid(bad)


def test_unknown_resources_are_not_retrieved(monkeypatch):
    captured = []
    strict = contracts._STRICT

    def construct(document, *, registry):
        captured.append(registry)
        return strict(document, registry=registry)

    contracts._execution_validator.cache_clear()
    monkeypatch.setattr(contracts, "_STRICT", construct)
    contracts._execution_validator("Software")
    with pytest.raises(NoSuchResource):
        captured[0].get_or_retrieve("https://example.invalid/unselected-schema")


def test_bound_public_schemas_stay_current_and_separate(before, tmp_path):
    software = _fixtures.software()
    binding = {"operation": "compare", "scientific_mode": "fit_then_evaluate_ca", "software": software}
    unchanged_private = contracts._execution_validator("RequestedProteinJob")
    selected = contracts.requested_job_from_protein_structure(_fixtures.job(tmp_path))
    variants = [deepcopy(binding) for _ in range(4)]
    variants[1].update(operation="inspect", scientific_mode=None)
    variants[2]["scientific_mode"] = "evaluate_declared_transform_ca"
    variants[3]["software"]["python_sha256"] = "0" * 64
    schemas = [contracts.protein_structure_execution_schema("RequestedProteinJob", bindings=[row]) for row in variants]
    for row, schema in zip(variants, schemas):
        assert schema == before.protein_structure_execution_schema("RequestedProteinJob", bindings=[row])
    assert len({schema["$id"] for schema in schemas}) == len(schemas)
    assert [Draft202012Validator(schema).is_valid(selected) for schema in schemas] == [True, False, False, False]
    assert Draft202012Validator(obj({"request": {"oneOf": schemas}})).is_valid({"request": selected})
    variants[0]["software"]["python_sha256"] = "1" * 64
    newest = contracts.protein_structure_execution_schema("RequestedProteinJob", bindings=[variants[0]])
    assert not Draft202012Validator(newest).is_valid(selected)
    assert Draft202012Validator(schemas[0]).is_valid(selected)
    assert contracts._execution_validator("RequestedProteinJob") is unchanged_private


def test_concurrent_distinct_current_payloads_need_no_registry_discovery(monkeypatch):
    cases = []
    for kind in ("inspect", "extract_sequence", "compare"):
        for chain in ("A", "C", "D", "E"):
            request, _ = _fixtures.requests(kind, fixed_kwargs={"chain": chain})
            assert contracts.validate_protein_structure_request(request) == request
            invalid = deepcopy(request)
            _request_file(invalid)["byte_length"] = 4.0
            cases.extend([(request, True), (invalid, False)])
    assert len({digest(value) for value, _ in cases}) == len(cases)

    def no_crawl(_registry):
        pytest.fail("concurrent warm payload validation repeated schema discovery")

    monkeypatch.setattr(Registry, "crawl", no_crawl)

    def check(case):
        value, expected = case
        if not expected:
            with pytest.raises(ValueError, match="invalid_schema"):
                contracts.validate_protein_structure_request(value)
            return False
        returned = contracts.validate_protein_structure_request(value)
        assert returned == value and returned is not value
        returned["operation"] = "detached"
        return True

    with ThreadPoolExecutor(max_workers=4) as executor:
        assert list(executor.map(check, cases)) == [expected for _, expected in cases]


def test_unknown_type_does_not_enter_cache():
    contracts._execution_validator.cache_clear()
    for _ in range(2):
        with pytest.raises(ValueError, match="invalid_schema"):
            contracts._execution_validator("UnselectedType")
    assert contracts._execution_validator.cache_info().currsize == 0
