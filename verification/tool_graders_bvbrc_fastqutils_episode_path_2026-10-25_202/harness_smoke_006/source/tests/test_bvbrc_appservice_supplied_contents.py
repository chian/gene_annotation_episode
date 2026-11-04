"""Explicit retained input custody and publication; controlled native transport.

These checks establish supplied-file transport, not a phylogeny scientific
adapter, configured-model decision or live BV-BRC execution.
"""
from copy import deepcopy
from types import SimpleNamespace
import json

import pytest

from gene_annotation_episode.bvbrc_appservice_contracts import ContractValidationError, validate_contract
from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustodyError
from test_bvbrc_appservice_custody import saved, selector, request
from test_bvbrc_appservice_host import driver
from test_bvbrc_appservice_inputs import output_target, download_args


def results_context(saved, bindings, *, index=3):
    handoff = saved.source(b'{"handoff":"controlled custody fixture"}')
    saved.own(saved.root, handoff["source_ref"], index=0)
    selected = {**selector(), "supplied_contents": deepcopy(bindings)}
    context = saved.child(saved.root, "results", {
        "version": "execution_results_assignment_v1", "handoff_ref": handoff["source_ref"],
        "selector": selected}, index)
    return context, handoff


def test_raw_content_is_an_explicit_operand_with_before_commission_custody(saved):
    tree = saved.source(b"((a:0,b:1):2,c:3);\n")
    saved.own(saved.root, tree["source_ref"], index=1)
    context, handoff = results_context(saved, [tree])
    assert saved.custody.initial_references(context) == [handoff["source_ref"], tree["source_ref"]]
    assert saved.custody.content(context, tree) == b"((a:0,b:1):2,c:3);\n"


@pytest.mark.parametrize("received_index", [None, 4])
def test_source_presence_or_later_parent_receipt_does_not_grant_content(saved, received_index):
    tree = saved.source(b"(a,b);\n")
    context, _ = results_context(saved, [tree])
    if received_index is not None:
        saved.own(saved.root, tree["source_ref"], index=received_index)
    with pytest.raises(AppServiceCustodyError, match="input_not_possessed"):
        saved.custody.initial_references(context)


def test_content_received_through_actual_typed_child_return_is_usable(saved):
    child = saved.child(saved.root, "scientific_process", {}, 1)
    tree = saved.source(b"(a:1,b:2);\n")
    saved.own(child, tree["source_ref"], index=0)
    saved.admit(saved.root, child, tree["source_ref"])
    context, _ = results_context(saved, [tree])
    assert tree["source_ref"] in saved.custody.initial_references(context)
    assert saved.custody.content(context, tree) == b"(a:1,b:2);\n"


@pytest.mark.parametrize("field,value,code", [
    ("sha256", "0" * 64, "input_bytes_mismatch"),
    ("byte_count", 500, "input_bytes_mismatch"),
    ("artifact_field", "stderr_ref", "artifact_field_conflict"),
])
def test_supplied_content_requires_exact_original_source_bytes(saved, field, value, code):
    tree = saved.source(b"(a,b);\n")
    saved.own(saved.root, tree["source_ref"], index=1)
    wrong = {**tree, field: value}
    context, _ = results_context(saved, [wrong])
    with pytest.raises(AppServiceCustodyError, match=code):
        saved.custody.initial_references(context)


def test_no_nested_json_search_for_unselected_content(saved):
    raw = saved.source(b"(a,b);\n")
    description = saved.source(json.dumps({"unselected": raw}).encode())
    saved.own(saved.root, description["source_ref"], index=1)
    context, _ = results_context(saved, [])
    assert raw["source_ref"] not in saved.custody.initial_references(context)
    with pytest.raises(AppServiceCustodyError, match="input_not_possessed"):
        saved.custody.content(context, raw)


def test_omitted_and_empty_are_preserved_and_conflicting_bindings_rejected(saved):
    original = selector()
    assert validate_contract("ResultSelector", original) == original
    assert "supplied_contents" not in original
    empty = {**original, "supplied_contents": []}
    assert validate_contract("ResultSelector", empty) == empty
    content = saved.source(b"(a,b);\n")
    with pytest.raises(ContractValidationError, match="supplied_content_binding_conflict"):
        validate_contract("ResultSelector", {**original, "supplied_contents": [
            content, {**content, "sha256": "0" * 64}]})


def acquire_with_contents(d, contents, *, probe=None):
    selected = {**selector(), "supplied_contents": deepcopy(contents)}
    if probe is not None:
        pin = {"adapter_id": "test_supplied_bytes_probe", "adapter_version": "1",
               "implementation_sha256": "1" * 64}
        d.api.configuration["selected-api"]["scientific_adapters"] = [pin]
        d.service.scientific_adapters = {(pin["adapter_id"], "1"): (probe, pin["implementation_sha256"])}
        selected["endpoint"] = "requested_projection"
        selected["adapter"] = {"adapter_id": pin["adapter_id"], "adapter_version": "1", "parameters": {}}
        selected["requested_schema"] = {"type": "object", "properties": {"byte_count": {"type": "integer"}},
                                        "required": ["byte_count"], "additionalProperties": False}
    query = request()
    obj = output_target(query)
    d.tree(query)
    handoff = d.launch_task()
    context = d.results(handoff, selection=selected)
    d.api.initialize(context)
    d.client.value = ["https://fixture.invalid/exact-output"]
    cap = d.call("download_capability", {"objects": [obj], "generation": 0,
        "predecessor_receipt_ref": None}, context=context)
    args = download_args(obj, {"kind": "acquired", "receipt_ref": cap["source_ref"], "input_index": 0})
    d.client.body = b"current task output"
    acquired = d.call("download", args, context=context)
    body = d.api.read_result(d.last_outcome["result"]["source_ref"], context.scope)
    return context, args, acquired, body


@pytest.mark.parametrize("number", [0, 2])
def test_original_content_bindings_survive_publication_and_replay(driver, number):
    d = driver
    contents = [d.saved.source(raw) for raw in [b"(a,b);\n", b"(c,d);\n"][:number]]
    for index, content in enumerate(contents):
        # Each supplied reference was received by a completed parent action.
        d.saved.own(d.saved.root, content["source_ref"], index=index)
    context, args, acquired, body = acquire_with_contents(d, contents)
    assert body["bundle"]["supplied_contents"] == contents
    assert body["publication_inputs"]["selector"]["supplied_contents"] == contents
    assert len(body["bundle"]["artifacts"]) == 1
    assert all(c["source_ref"] not in body["record_refs"] for c in contents)
    before = (len(d.client.calls), d.store.count("source"), d.store.db.execute(
        "SELECT COUNT(*) FROM runtime_actions").fetchone()[0], d.store.db.execute(
        "SELECT COUNT(*) FROM runtime_observations").fetchone()[0])
    outcome = deepcopy(d.last_outcome)
    assert d.invoke(context, "download", args, acquired["value"]["origin"]["operation_key"]) == outcome
    assert d.api.read_result(body["source_ref"], context.scope) == body
    assert before == (len(d.client.calls), d.store.count("source"), d.store.db.execute(
        "SELECT COUNT(*) FROM runtime_actions").fetchone()[0], d.store.db.execute(
        "SELECT COUNT(*) FROM runtime_observations").fetchone()[0])


def test_pure_adapter_receives_exact_explicit_bytes_once(driver):
    d = driver
    raw = b"((a:0,b:1):2,c:3);\n"
    content = d.saved.source(raw)
    d.saved.own(d.saved.root, content["source_ref"], index=0)
    calls = []

    def consume(bundle, *, artifact_bytes, supplied_values, requested_form, parameters):
        calls.append(deepcopy(bundle))
        assert artifact_bytes[content["artifact_ref"]] == raw
        assert set(artifact_bytes) == {content["artifact_ref"], bundle["artifacts"][0]["raw_artifact_ref"]}
        assert bundle["supplied_contents"] == [content]
        return {"adapter_id": "test_supplied_bytes_probe", "adapter_version": "1", "status": "ok",
            "sheet": None, "components": None, "facts": {"byte_count": len(raw)},
            "missing_requirements": [], "diagnostics": []}

    def validate_parameters(parameters):
        assert parameters == {}

    def validate_requested_form(form):
        assert form == {"type": "object", "properties": {"byte_count": {"type": "integer"}},
                        "required": ["byte_count"], "additionalProperties": False}

    probe = SimpleNamespace(consume_bundle=consume, validate_parameters=validate_parameters,
                            validate_requested_form=validate_requested_form)
    context, args, acquired, body = acquire_with_contents(d, [content], probe=probe)
    assert body["publication"]["adapter_result"]["facts"] == {"byte_count": len(raw)}
    assert len(calls) == 1
    d.invoke(context, "download", args, acquired["value"]["origin"]["operation_key"])
    assert d.api.read_result(body["source_ref"], context.scope) == body
    assert len(calls) == 1
