"""UniProt alias selection through existing API ownership and saved receipts."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.api_uniprot import UniProtService
from gene_annotation_episode.resource_tool_information import bound_resource_tool_contracts
from gene_annotation_episode.tool_information import make_tool_info, workflow_execution_catalogs
from gene_annotation_episode.tools import ToolRegistry
from test_api_service_integration import (assignment, generic_host, service_responses,
    test_shared_loop_service_handoff_monitor_native_result_and_terminal_zero as run_shared_service_case)
from test_api_service_recovery import remember, selected_intent
from test_execution_episodes_family import context, launch_assignment, select
from test_uniprot_publication import RecordedClient, harness, protein, snapshot


def alias(endpoint="/uniprotkb/P12345", **extra):
    return {"operation": "query_uniprot", "endpoint": endpoint, **extra}


def test_alias_is_declared_only_through_the_bound_api_resource(generic_host):
    h = generic_host
    contracts = bound_resource_tool_contracts(h.family)
    row, = [row for row in contracts if row["name"] == "query_uniprot"]
    assert row["resources"] == "api"
    assert row["invocation_route"] == {"kind": "commission", "routes": [
        {"entry_role": "launch", "resource_id": "uniprot", "resource_role": "launch_api"}]}
    assert row["input_schema"] == {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    info = make_tool_info(row, "api")
    assert "immutable service-request operands" in info["instructions"]
    assert "one existing client call" in info["instructions"]
    declared = [entry for entry in workflow_execution_catalogs()["api"] if entry["name"] == "query_uniprot"]
    assert len(declared) == 1 and declared[0]["instructions"] == row["instructions"]
    tools = h.family.api_execution.tools
    assert "query_uniprot" not in tools.catalog()
    assert tools.execute("query_uniprot", {}, operation_key="unavailable-direct-alias")["feedback"]["code"] == "unknown_tool"
    assert h.client.requests == []


def test_literal_alias_runs_through_shared_loop_with_existing_reference_form(tmp_path, service_responses):
    # Reuse the actual shared-loop reference-form path and its original replay,
    # completion-zero and closed-history checks. Native fact-family forms are
    # intentionally separate unfinished work.
    run_shared_service_case(tmp_path, service_responses, "uniprot", "uniprot",
        alias("/uniprotkb/search?query=gene%3AybhP&size=1"),
        {"cursor": "actual-next-cursor", "size": 1}, "query_uniprot", "api.uniprot.collect")


@pytest.mark.parametrize("selected_request", [
    alias("https://elsewhere.test/uniprotkb/P12345"),
    alias("http://rest.uniprot.org/uniprotkb/P12345"),
    alias("/uniprotkb/search?query=x&size=2", max_results=3),
    alias("/uniprotkb/search?query=x", max_results=501),
    alias("/uniprotkb/search?query=x", max_results=True),
    alias("/uniprotkb/search?query=x&query=y"),
    alias("/uniprotkb/search?query=x&fields=accession"),
    alias("/uniprotkb/P12345", max_results=5),
    alias("/uniprotkb/P12345.fasta"),
    alias("/uniref/UniRef50_P12345"),
    {"operation": "query_uniprot", "prompt": "find a human protein"},
])
def test_unsupported_alias_inputs_fail_before_transport(harness, selected_request):
    client = RecordedClient(snapshot(protein(), {"accession": "P12345"}))
    service = UniProtService(ToolRegistry(harness, clients=client))
    with pytest.raises(ValueError):
        service.prepare("query_uniprot", selected_request, {}, scope=None, previous_events=[])
    assert client.calls == []


def test_alias_original_endpoint_is_immutable_but_effective_page_is_explicit(harness):
    request = alias("https://rest.uniprot.org/uniprotkb/search?query=gene%3AybhP&cursor=opaque%2Btoken", max_results=2)
    arguments = {"query": "gene:ybhP", "size": 2, "cursor": "opaque+token"}
    native = snapshot({"results": [protein()]}, {**arguments, "format": "json"})
    client = RecordedClient(native)
    service = UniProtService(ToolRegistry(harness, clients=client))
    assert service.validate_request(request, None) == request
    assert [entry["name"] for entry in service.launch_catalog(request)] == ["query_uniprot"]
    prepared = service.prepare("query_uniprot", request, {}, scope=None, previous_events=[])
    assert prepared["request"] == request and prepared["native_arguments"] == arguments
    assert service.invoke(prepared) == native
    assert service.decode(prepared, native)["handoff_ready"]
    cached = service.prepare("api.uniprot.collect", request, {}, scope=None, previous_events=[], selector={})
    assert cached["cache_original"] and cached["native_arguments"] == arguments
    next_page = service.prepare("api.uniprot.collect", request, {}, scope=None, previous_events=[],
                                selector={"cursor": "next-token", "size": 1})
    assert next_page["native_arguments"] == {"query": "gene:ybhP", "size": 1, "cursor": "next-token"}
    assert not next_page["cache_original"]
    for name, changes in (("query_uniprot", {"endpoint": "/uniprotkb/Q12345"}),
                          ("api.uniprot.search", {})):
        with pytest.raises(ValueError):
            service.prepare(name, request, changes, scope=None, previous_events=[])
    assert client.calls == [("search", arguments)]


@pytest.mark.parametrize("operation,arguments,change,code", [
    ("record", {"accession": "P12345"}, {"request": {}}, "request_missing_accession"),
    ("search", {"query": "chosen", "size": 2}, {"request": {"size": 2}}, "request_missing_query"),
    ("search", {"query": "chosen", "size": 2}, {"request": {"query": "chosen"}}, "request_missing_size"),
    ("search", {"query": "chosen", "size": 2, "cursor": "first"},
     {"request": {"query": "chosen", "size": 2}}, "request_missing_cursor"),
    ("search", {"query": "chosen", "size": 2},
     {"request": {"query": "chosen", "size": 2, "cursor": "unexpected"}}, "request_conflict_cursor"),
    ("record", {"accession": "P12345"}, {"service": "other"}, "response_required"),
    ("record", {"accession": "P12345"}, {"transport": {"status": 404}}, "http_response_not_successful"),
    ("record", {"accession": "P12345"}, {"transport": {"response": {"status": True}}}, "http_response_not_successful"),
    ("record", {"accession": "P12345"}, {"transport": {"response": {"headers": []}}}, "response_headers_invalid"),
    ("record", {"accession": "P12345"}, {"transport": []}, "response_transport_invalid"),
    ("record", {"accession": "P12345"}, {"request": {"accession": "P12345", "format": "fasta"}}, "request_invalid"),
])
def test_actual_snapshot_request_and_transport_are_checked_separately(harness, operation, arguments, change, code):
    body = protein() if operation == "record" else {"results": [protein()]}
    native = replace(snapshot(body, arguments), **change)
    tools = ToolRegistry(harness, clients=RecordedClient(native))
    service = UniProtService(tools)
    selected = {"operation": operation, **arguments}
    prepared = service.prepare("api.uniprot." + operation, selected, {}, scope=None, previous_events=[])
    with pytest.raises(ValueError, match=code):
        service.decode(prepared, native)
    retained = tools.execute("public.uniprot." + operation, arguments, operation_key="mismatched-source")
    assert retained["status"] == "partial", retained
    assert retained["result"]["count"] == 0 and "uniprot_publication" not in retained["result"]
    assert len(retained["record_refs"]) == 1
    source = harness.get(retained["result"]["source_ref"])
    assert harness.get_artifact(source["artifact_ref"]) == native.content


def test_secondary_correspondence_and_unknown_transport_remain_distinct(harness):
    body = protein()
    body["secondaryAccessions"] = ["Q12345"]
    native = replace(snapshot(body, {"accession": "Q12345"}), transport={})
    service = UniProtService(ToolRegistry(harness, clients=RecordedClient(native)))
    request = alias("/uniprotkb/Q12345.json")
    prepared = service.prepare("query_uniprot", request, {}, scope=None, previous_events=[])
    facts = service.decode(prepared, native)["facts"]
    assert facts["accession"] == "P12345" and facts["http_status"] is None
    result = service.publish(request, {}, native, harness.validate_scope(None), "secondary")
    assert result["status"] == "completed", result
    record = result["result"]["uniprot_publication"]["records"][0]["record"]
    assert record["identity"]["requested_accession"] == "Q12345"
    assert record["identity"]["accession_relation"] == "secondary"
    wrong = service.prepare("query_uniprot", alias("/uniprotkb/R12345"), {}, scope=None, previous_events=[])
    with pytest.raises(ValueError, match="accession_unmatched"):
        service.decode(wrong, replace(native, request={"accession": "R12345"}))


def test_alias_receipt_replay_recovers_original_publication_without_extra_calls(generic_host, monkeypatch):
    h = generic_host
    request = assignment("uniprot", "uniprot", alias("/uniprotkb/P12345", max_results=None))
    parent = context(h, "launch", launch_assignment({"uniprot": request}), "alias-parent")
    assert h.family.prepare_assignment(parent, "launch_api", request, h.scope, "unexecuted") == request
    changed = deepcopy(request)
    changed["request"]["endpoint"] = "/uniprotkb/Q12345"
    with pytest.raises(ValueError, match="original_request_conflict"):
        h.family.prepare_assignment(parent, "launch_api", changed, h.scope, "unexecuted")
    launch = context(h, "launch_api", request, "alias-api")
    service = h.family.api_execution.services["uniprot"]
    decode, first = service.decode, True

    def interrupted(prepared, response):
        nonlocal first
        if first:
            first = False
            raise asyncio.CancelledError()
        return decode(prepared, response)

    monkeypatch.setattr(service, "decode", interrupted)
    key = selected_intent(h, launch, 0, "query_uniprot")
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(h.family.execute(launch, "query_uniprot", {}, key))
    launched = asyncio.run(h.family.execute(launch, "query_uniprot", {}, key))
    remember(h, launch, 0, launched)
    assert launched["status"] == "completed", launched
    assert len(h.client.requests) == 1
    monkeypatch.setattr(service, "decode", decode)
    handoff, = launched["record_refs"]
    original = h.family.api_execution._read_handoff(handoff, h.scope)
    assert original["assignment"]["request"] == request["request"]
    receiver = context(h, "results", {"version": "execution_results_assignment_v1",
        "handoff_ref": handoff, "selector": {}}, "alias-results")
    core, first = h.family.api_execution, True
    index = core._index_result

    def interrupt_index(*args):
        nonlocal first
        if first:
            first = False
            raise asyncio.CancelledError()
        return index(*args)

    monkeypatch.setattr(core, "_index_result", interrupt_index)
    key = selected_intent(h, receiver, 0, "api.uniprot.collect")
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(h.family.execute(receiver, "api.uniprot.collect", {}, key))
    counts = (h.store.count("source"), h.store.count("reference"))
    result = asyncio.run(h.family.execute(receiver, "api.uniprot.collect", {}, key))
    remember(h, receiver, 0, result)
    assert result["status"] == "completed", result
    assert result["result"]["uniprot_publication"]["records"][0]["anchor"]["primary_accession"] == "P12345"
    assert (h.store.count("source"), h.store.count("reference")) == counts
    assert asyncio.run(h.family.execute(receiver, "api.uniprot.collect", {}, key)) == result
    assert len(h.client.requests) == 1
    proof = h.family.completion_for_action(receiver, key)
    assert proof is not None and h.family.verify_completion(receiver, proof)
    for ref in result["record_refs"]:
        acquired = core.read_result(ref, h.scope)
        assert acquired["service_request"] == request["request"]
        assert acquired["source_ref"] == result["result"]["source_ref"]


def test_failed_native_correspondence_retains_diagnostic_bytes_without_handoff(generic_host, monkeypatch):
    h = generic_host
    native = snapshot(protein("Q12345"), {"accession": "P12345"})
    client = h.family.api_execution.services["uniprot"].client
    monkeypatch.setattr(client, "uniprot_record", lambda accession: native)
    request = assignment("uniprot", "uniprot", alias())
    launch = context(h, "launch_api", request, "alias-mismatch")
    result = select(h, launch, 0, "query_uniprot")
    assert result["status"] == "failed" and result["record_refs"] == []
    assert result["feedback"]["response_retained"] is True
    assert "accession_unmatched" in result["feedback"]["code"]
    paths = list(h.family.api_execution._episode_directory(launch.episode_id).glob("actions/*/snapshot.json"))
    assert len(paths) == 1
    assert h.store.get_artifact(json.loads(paths[0].read_text())["content_ref"]) == native.content
