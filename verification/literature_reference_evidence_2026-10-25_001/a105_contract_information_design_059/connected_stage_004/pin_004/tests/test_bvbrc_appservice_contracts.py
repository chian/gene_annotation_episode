from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.bvbrc_appservice_contracts import (
    ContractValidationError, contract_schema, validate_contract, validate_request,
)


SHA = "a" * 64
OWNER = {"run_id": "run", "launch_episode_id": "launch", "parent_commission_operation_key": "run:root:1",
         "original_launch_assignment_sha256": SHA}


def request():
    return {"version": "bvbrc_appservice_request_v1", "effect_contract": "selected_api_effects_v1",
            "required_application_id": "Homology", "parameters": {}, "start_parameters": {},
            "definition_inputs": [], "input_bindings": [], "workspace_targets": []}


def content():
    return {"source_ref": "source:input", "artifact_field": "artifact_ref", "artifact_ref": "artifact:input",
            "sha256": SHA, "byte_count": 4}


def input_binding(kind, value):
    return {"binding_id": "input", "parameter_pointer": "/file", "kind": kind,
            "content": content() if kind == "retained_bytes" else None,
            "workspace_path": value if kind in {"retained_bytes", "workspace_object"} else None,
            "inline_value": value if kind in {"inline_parameter", "supplied_link"} else None,
            "link_evidence": {"content": content(), "pointer": "/url"} if kind == "supplied_link" else None,
            "members": []}


def effect(kind="appservice_submit", **slot):
    return {"version": "selected_api_effects_v1", "original_job_owner": deepcopy(OWNER),
            "resource_id": "api:configured", "kind": kind, "slot": {"kind": kind, **slot},
            "payload_sha256": SHA, "predecessor_evidence_refs": []}


def test_all_frozen_schemas_are_self_contained_and_exactly_reachable():
    package = Path(__file__).parents[1] / "gene_annotation_episode/bvbrc_appservice_schemas.json"
    frozen = Path(__file__).parents[1] / "verification/tool_graders_bvbrc_appservice_execution_contract_2026-10-24/CONTRACT_SCHEMA.json"
    definitions = json.loads(package.read_text())["$defs"]
    original = json.loads(frozen.read_text())["$defs"]
    assert len(original) == 72
    assert set(definitions) - set(original) == {"ResolvedObject", "ResolvedUpload", "ResolvedCapability", "ResolvedInputs"}
    for name in original:
        if name not in {"BoundInputs", "WorkspaceObject", "ResultSelector", "ArtifactBundle", "ContentBinding", "ArtifactMember"}:
            assert definitions[name] == original[name]
    # Prospective pre-acquisition selection amendment; original bytes stay fixed.
    member = deepcopy(definitions["ArtifactMember"])
    assert member["properties"].pop("requirement_ids") == {
        "type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True}
    assert member == original["ArtifactMember"]
    # Prospective request-content amendment; the immutable original is retained.
    content = deepcopy(definitions["ContentBinding"])
    enum = content["properties"]["artifact_field"]["enum"]
    assert enum == original["ContentBinding"]["properties"]["artifact_field"]["enum"] + ["request_ref"]
    assert enum.pop() == "request_ref"
    assert content == original["ContentBinding"]
    # The additive retained-byte contract is optional. All original fields,
    # required sets and definitions remain exactly the frozen original shape.
    for name in ("ResultSelector", "ArtifactBundle"):
        amended = deepcopy(definitions[name])
        assert amended["properties"].pop("supplied_contents") == {
            "type": "array", "items": {"$ref": "#/$defs/ContentBinding"},
            "minItems": 0, "uniqueItems": True}
        assert amended == original[name]
    bound = deepcopy(definitions["BoundInputs"])
    for key in ("resource_id", "resolved"):
        bound["properties"].pop(key)
        bound["required"].remove(key)
    assert bound == original["BoundInputs"]
    workspace = deepcopy(definitions['WorkspaceObject'])
    workspace['properties']['path'] = {'type': 'string', 'minLength': 1}
    workspace.pop('anyOf')
    assert workspace == original['WorkspaceObject']
    assert definitions["ResolvedCapability"]["properties"]["entry"] == original["CapabilityReceipt"]["properties"]["entries"]["items"]
    for name in definitions:
        schema = contract_schema(name)
        Draft202012Validator.check_schema(schema)
        seen = set()

        def walk(value):
            if isinstance(value, dict):
                if "$ref" in value:
                    key = value["$ref"].removeprefix("#/$defs/")
                    if key not in seen:
                        seen.add(key)
                        walk(schema["$defs"][key])
                for key, child in value.items():
                    if key != "$defs":
                        walk(child)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(schema)
        assert set(schema["$defs"]) == seen
        assert all(schema["$defs"][key] == definitions[key] for key in seen)
    schema = contract_schema("OriginalJobOwner")
    schema["$defs"]["OriginalJobOwner"]["properties"].clear()
    assert contract_schema("OriginalJobOwner")["$defs"]["OriginalJobOwner"]["properties"]


def test_frozen_shape_examples_still_pass_their_original_expectations():
    path = Path(__file__).parents[1] / "verification/tool_graders_bvbrc_appservice_execution_contract_2026-10-24/SCHEMA_EXAMPLES.json"
    examples = json.loads(path.read_text())
    for item in examples["positive"]:
        assert validate_contract(item["schema"], item["value"]) == item["value"]
    for item in examples["negative"]:
        with pytest.raises(ContractValidationError):
            validate_contract(item["schema"], item["value"])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), (1, 2), {1: "x"}, b"bytes", object()])
def test_only_plain_finite_json_is_accepted(value):
    with pytest.raises(ContractValidationError):
        validate_contract("Json", {"nested": value})


def test_recursive_json_is_rejected_but_shared_json_is_detached():
    value = []
    value.append(value)
    with pytest.raises(ContractValidationError, match="recursive_json"):
        validate_contract("Json", value)
    row = {"x": [1, 0, False, None]}
    copied = validate_contract("Json", [row, row])
    row["x"].append(2)
    assert copied == [{"x": [1, 0, False, None]}] * 2


@pytest.mark.parametrize("name,value", [
    ("Range", [False, 3]), ("Range", [1.0, 3]), ("ListingOptions", {"recursive": True}),
    ("CreationOptions", {"downloadLinks": False}), ("StartParameters", {"disable_preflight": True}),
    ("ListingOptions", {"recursive": 1.0}),
    ("MemberFact", {"member_id": "input", "member_pointer": "", "length": True,
                    "molecule": None, "sequence_sha256": None, "evidence": None}),
])
def test_native_integer_fields_reject_boolean_and_float_substitutes(name, value):
    with pytest.raises(ContractValidationError):
        validate_contract(name, value)


@pytest.mark.parametrize("kind,value", [("retained_bytes", "/owner/home/reads"),
    ("workspace_object", "/owner/home/exact object"), ("inline_parameter", [0, False, None]),
    ("inline_parameter", None), ("supplied_link", "https://example.invalid/original?key=secret")])
def test_input_kinds_have_exact_original_parameter_relationships(kind, value):
    original = request()
    original["parameters"] = {"file": deepcopy(value)}
    original["input_bindings"] = [input_binding(kind, value)]
    checked = validate_request(original)
    assert checked == original
    assert checked["start_parameters"] == {}
    original["parameters"]["file"] = "changed"
    assert checked["parameters"]["file"] == value
    with pytest.raises(ContractValidationError, match="input_parameter_value_conflict"):
        validate_request(original)


@pytest.mark.parametrize("kind", ["retained_bytes", "workspace_object", "inline_parameter", "supplied_link"])
def test_wrong_kind_fields_are_rejected(kind):
    value = input_binding(kind, "value")
    if kind == "retained_bytes":
        value["workspace_path"] = None
    elif kind == "workspace_object":
        value["content"] = content()
    elif kind == "inline_parameter":
        value["workspace_path"] = "/owner/home/input"
    else:
        value["content"] = content()
    with pytest.raises(ContractValidationError, match="input_kind_content_conflict"):
        validate_contract("InputBinding", value)


def test_pointer_resolution_handles_escapes_and_checks_exact_json_types():
    value = request()
    value["parameters"] = {"a/b": {"~field": [True]}}
    binding = input_binding("inline_parameter", True)
    binding["parameter_pointer"] = "/a~1b/~0field/0"
    value["input_bindings"] = [binding]
    assert validate_request(value) == value
    binding["inline_value"] = 1
    with pytest.raises(ContractValidationError, match="input_parameter_value_conflict"):
        validate_request(value)
    binding["parameter_pointer"] = "/a~1b/~0field/00"
    with pytest.raises(ContractValidationError, match="parameter_pointer_missing"):
        validate_request(value)


def test_duplicate_ids_and_unbound_targets_are_rejected():
    value = request()
    value["parameters"] = {"file": "x"}
    value["input_bindings"] = [input_binding("inline_parameter", "x")] * 2
    with pytest.raises(ContractValidationError, match="duplicate_binding_id"):
        validate_request(value)
    value["input_bindings"] = []
    value["workspace_targets"] = [{"target_id": "target", "path": "/owner/home/file", "type": "txt",
        "purpose": "input", "input_binding_id": "absent", "metadata": {},
        "allow_overwrite": False, "allow_create_parents": False}]
    with pytest.raises(ContractValidationError, match="unknown_input_binding"):
        validate_request(value)


def test_semantic_ranges_effects_and_capability_predecessors():
    with pytest.raises(ContractValidationError, match="range_conflict"):
        validate_contract("Range", [4, 3])
    assert validate_contract("Range", [4, None]) == [4, None]
    with pytest.raises(ContractValidationError, match="object_size_conflict"):
        validate_contract("ObservedRange", {"start": 0, "end_inclusive": 4, "total_size": 4})
    invalid = effect()
    invalid["slot"] = {"kind": "shock_upload", "shock_node_id": "exact-node"}
    with pytest.raises(ContractValidationError, match="effect_slot_kind_conflict"):
        validate_contract("EffectDescriptor", invalid)
    later = effect("download_capability", object_identity="exact-object", generation=1)
    with pytest.raises(ContractValidationError, match="capability_predecessor_conflict"):
        validate_contract("EffectDescriptor", later)
    later["predecessor_evidence_refs"] = ["effect:prior", "capability:prior"]
    assert validate_contract("EffectDescriptor", later) == later
    later["slot"]["generation"] = 0
    with pytest.raises(ContractValidationError, match="capability_predecessor_conflict"):
        validate_contract("EffectDescriptor", later)


def test_capability_operation_checks_relationship_inside_operation_union():
    args = {"objects": [{"kind": "original_target", "target_id": "output"}],
            "generation": 1, "predecessor_receipt_ref": None}
    selection = {"name": "api.bvbrc_appservice.download_capability", "arguments": args}
    with pytest.raises(ContractValidationError, match="capability_predecessor_conflict"):
        validate_contract("OperationSelection", selection)


def test_effect_receipt_does_not_confirm_without_issued_time_and_source():
    receipt = {"version": "selected_api_effect_receipt_v1", "effect_ref": "effect:1", "descriptor": effect(),
        "operation_key": "run:launch:1", "state": "prepared_not_issued", "issued_at": None,
        "confirmation_source_ref": None, "native_effect_identifiers": {}, "ancillary_effects": [], "failure": None}
    assert validate_contract("EffectReceipt", receipt) == receipt
    receipt["state"] = "confirmed"
    with pytest.raises(ContractValidationError, match="effect_issue_time_missing"):
        validate_contract("EffectReceipt", receipt)
    receipt["issued_at"] = "2026-10-24T00:00:00+00:00"
    with pytest.raises(ContractValidationError, match="effect_confirmation_conflict"):
        validate_contract("EffectReceipt", receipt)
    receipt["confirmation_source_ref"] = "source:actual"
    assert validate_contract("EffectReceipt", receipt) == receipt


def test_projection_requires_adapter_and_closed_requested_schema():
    selector = {"version": "bvbrc_appservice_result_selector_v1", "endpoint": "requested_projection",
        "requirements": [{"requirement_id": "raw", "role": "exact_role", "required": True,
                          "declared_format": {"format": "format", "version": None, "mode": None,
                              "producer_source_ref": None, "transformation_evidence": []},
                          "producer_rule_evidence": None, "exact_object": None}],
        "adapter": None, "requested_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "supplied_metadata": [], "supplied_capabilities": []}
    with pytest.raises(ContractValidationError, match="scientific_adapter_unbound"):
        validate_contract("ResultSelector", selector)
    selector["adapter"] = {"adapter_id": "separately-bound", "adapter_version": "v1", "parameters": {}}
    assert validate_contract("ResultSelector", selector) == selector
    selector["requested_schema"]["additionalProperties"] = True
    with pytest.raises(ContractValidationError, match="requested_schema_not_closed"):
        validate_contract("ResultSelector", selector)


def test_unknown_contract_and_validation_errors_do_not_echo_secret_values():
    with pytest.raises(ContractValidationError, match="unknown_appservice_contract"):
        contract_schema("not-a-contract")
    with pytest.raises(ContractValidationError) as captured:
        validate_contract("OriginalJobOwner", {"secret": "sensitive-capability-token"})
    assert "sensitive-capability-token" not in str(captured.value)
    assert "sensitive-capability-token" not in json.dumps(captured.value.diagnostics)


def test_all_contract_json_pointers_reject_invalid_escape_sequences():
    with pytest.raises(ContractValidationError, match="invalid_json_pointer"):
        validate_contract("SourceEvidence", {"content": content(), "pointer": "/bad~2escape"})
    assert validate_contract("SourceEvidence", {"content": content(), "pointer": "/valid~01"})["pointer"] == "/valid~01"


def test_resolved_input_addendum_has_eleven_closed_distinct_branches():
    schema = contract_schema("ResolvedInputs")["$defs"]["ResolvedInputs"]
    assert len(schema["oneOf"]) == 11
    for branch in schema["oneOf"]:
        assert branch["additionalProperties"] is False
        # Metadata is also used before submission, when no native task exists.
        # The results path carries the original task through this same branch.
        optional = ({"original_task"} if branch["properties"]["operation"]["const"]
                    == "api.bvbrc_appservice.workspace_metadata" else set())
        assert set(branch["required"]) == set(branch["properties"]) - optional
        assert branch["properties"]["operation"]["const"].startswith("api.bvbrc_appservice.")
    assert validate_contract("ResolvedInputs", {"operation": "api.bvbrc_appservice.enumerate_apps"}) == {
        "operation": "api.bvbrc_appservice.enumerate_apps"}
    for value in ({"operation": "api.bvbrc_appservice.enumerate_apps", "objects": []},
                  {"operation": "api.bvbrc_appservice.prepare"},
                  {"operation": "api.bvbrc_appservice.status", "native_operands": {}},
                  {"operation": "api.bvbrc_appservice.workspace_metadata", "objects": []}):
        with pytest.raises(ContractValidationError):
            validate_contract("ResolvedInputs", value)


def test_bound_inputs_requires_explicit_resource_and_resolved_operation():
    bound = {"version": "bvbrc_appservice_bound_inputs_v1", "original_job_owner": deepcopy(OWNER),
        "request_sha256": SHA, "selected_argument_sha256": SHA, "definition": None, "inputs": [],
        "objects": [], "support_receipt_refs": [], "original_handoff_ref": None,
        "capability": None, "custody_proof_refs": [], "resource_id": "api:configured",
        "resolved": {"operation": "api.bvbrc_appservice.enumerate_apps"}}
    assert validate_contract("BoundInputs", bound) == bound
    for field in ("resource_id", "resolved"):
        incomplete = deepcopy(bound)
        incomplete.pop(field)
        with pytest.raises(ContractValidationError):
            validate_contract("BoundInputs", incomplete)
    prepared = {"version": "bvbrc_appservice_prepared_operation_v1",
        "execution_contract": "bvbrc_appservice_execution_v1", "operation": "api.bvbrc_appservice.enumerate_apps",
        "purpose": "support", "request_sha256": SHA, "arguments_sha256": SHA, "bound_inputs": bound,
        "mutates_remote": False, "effects": [], "native_kind": "rpc", "native_operands": {}}
    assert validate_contract("PreparedOperation", prepared) == prepared
    prepared["operation"] = "api.bvbrc_appservice.task_info"
    with pytest.raises(ContractValidationError, match="prepared_resolved_operation_conflict"):
        validate_contract("PreparedOperation", prepared)
