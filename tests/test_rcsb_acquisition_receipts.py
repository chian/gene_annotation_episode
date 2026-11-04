"""Engineered RCSB replies through pure, custody and ordinary registry owners.

The initial controls validate literal records/publication. Appended controls use
scripted current-episode choices and fake HTTP replies; no real HTTP, external
model, coordinate parser or numerical worker is exercised.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import rcsb_acquisition as rcsb
from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.communication import plain
from gene_annotation_episode.data_acquisition_receipts import acquisition_receipt_schema
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_runtime import action


SOURCE = "source_" + "a" * 24
NATIVE = {"rcsb_id": "4HHB", "cell": None, "rcsb_entry_info": {"count": 0},
    "unselected": {"ordered": [None, 0, False, "literal"]}}
_UNSET = object()


def _forbidden(*args, **kwargs):
    raise AssertionError("RCSB receipt controls attempted HTTP or native work")


def _arguments(kind="entry"):
    if kind == "entry":
        return dict(entry_id="4HHB", fields=["cell", "rcsb_entry_info"], max_bytes=8192)
    return dict(entry_id="4HHB", file_format="pdbx_mmcif_text", max_bytes=8192)


def _snapshot(kind="entry", *, native=_UNSET, raw=None, arguments=None, transport=None):
    arguments = _arguments(kind) if arguments is None else deepcopy(arguments)
    if raw is None:
        raw = ("  " + json.dumps(NATIVE if native is _UNSET else native,
            separators=(",", ":"), allow_nan=False) + "\n").encode() if kind == "entry" else b"unparsed bytes\x00\n"
    url = (rcsb.rcsb_entry_url(arguments["entry_id"]) if kind == "entry" else
        rcsb.rcsb_file_url(arguments["entry_id"], arguments["file_format"]))
    observed = dict(request=dict(method="GET", url=url), status=200,
        headers={"content-type": "application/json"}, body_complete=True,
        retained_body_bytes=len(raw), observed_body_bytes=len(raw), declared_body_bytes=len(raw),
        response_byte_limit=arguments["max_bytes"],
        request_policy=dict(automatic_redirects=False, timeout_seconds=3))
    if transport is not None:
        observed.update(deepcopy(transport))
    return SourceSnapshot(rcsb.SERVICE, url, arguments, "2026-11-01T00:00:00Z", raw,
        "application/json" if kind == "entry" else "application/octet-stream", observed)


def _legacy(snapshot, kind="entry"):
    builder = rcsb.rcsb_entry_result if kind == "entry" else rcsb.rcsb_file_result
    return builder(snapshot, arguments=snapshot.request, source_ref=SOURCE,
        artifact_ref="artifact_" + hashlib.sha256(snapshot.content).hexdigest())


@pytest.fixture
def publisher(tmp_path, monkeypatch):
    monkeypatch.setattr(PublicClients, "_http", _forbidden)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)
    with Store(tmp_path / "store") as store:
        yield store, ToolRegistry(store)


def _publish(tools, kind, snapshot, *, arguments=None):
    token = tools._publications.set([])
    try:
        return rcsb.publish_rcsb_request(tools, "public.rcsb." + kind,
            snapshot.request if arguments is None else arguments, snapshot)
    finally:
        tools._publications.reset(token)


def test_common_four_field_schema_and_source_less_failure_use_shared_authority():
    assert rcsb.rcsb_receipt_schema() == acquisition_receipt_schema(failure_codes=rcsb.RCSB_FAILURE_CODES)
    assert len(rcsb.RCSB_FAILURE_CODES) == len(set(rcsb.RCSB_FAILURE_CODES))
    failure = rcsb.failed_rcsb_receipt("data_acquisition_failed")
    assert failure == dict(acquired=False, source_ref=None, data_ref=None,
        failure_code="data_acquisition_failed")
    assert Draft202012Validator(rcsb.rcsb_receipt_schema()).is_valid(failure)
    assert rcsb.validate_rcsb_receipt(failure) == failure
    assert rcsb.validate_rcsb_receipt(failure) is not failure
    with pytest.raises(ContractError, match="rcsb_receipt_invalid"):
        rcsb.failed_rcsb_receipt("arbitrary_provider_text")


@pytest.mark.parametrize("change", [
    {"acquired": 1}, {"extra": None}, {"source_ref": None}, {"data_ref": None},
    {"source_ref": SOURCE + "\n"}, {"data_ref": "artifact_" + "f" * 63},
    {"failure_code": "data_acquisition_failed"},
    {"acquired": False, "failure_code": "data_acquisition_failed"},
])
def test_common_receipt_rejects_type_shape_and_reference_contradictions(change):
    value = dict(acquired=True, source_ref=SOURCE, data_ref="artifact_" + "f" * 64, failure_code=None)
    with pytest.raises(ContractError, match="rcsb_receipt_invalid"):
        rcsb.validate_rcsb_receipt({**value, **change})


def test_legacy_entry_literal_and_selected_null_zero_are_unchanged():
    snapshot = _snapshot()
    value = _legacy(snapshot)
    saved = deepcopy(value)
    assert set(value) == {"version", "source_ref", "raw_artifact_ref", "requested", "response",
        "parse_state", "observed_identity", "values", "issues"}
    assert value["version"] == "rcsb_entry_result_v1"
    assert value["observed_identity"] == dict(native_entry_id="4HHB", state="present", relation="exact_literal_match")
    assert value["values"] == [dict(field="cell", state="native_null", value=None),
        dict(field="rcsb_entry_info", state="present", value={"count": 0})]
    receipt = rcsb.rcsb_entry_receipt(value)
    assert receipt == dict(acquired=True, source_ref=SOURCE, data_ref=value["raw_artifact_ref"], failure_code=None)
    assert value == saved and "unselected" not in json.dumps(value)
    assert json.loads(snapshot.content) == NATIVE


@pytest.mark.parametrize("native,code", [
    ({}, "rcsb_native_entry_id_missing"), ({"rcsb_id": None}, "rcsb_native_entry_id_null"),
    ({"rcsb_id": 4}, "rcsb_native_entry_id_invalid"),
    ({"rcsb_id": "OTHER"}, "rcsb_native_entry_id_differs_from_request"),
    ({"rcsb_id": "4hhb"}, "rcsb_native_entry_id_differs_from_request"),
])
def test_entry_identity_confirmation_uses_native_literal_even_without_selected_fields(native, code):
    arguments = dict(entry_id="4HHB", fields=[], max_bytes=8192)
    value = _legacy(_snapshot(native=native, arguments=arguments))
    value["issues"] = []  # Engineering control: the old issue list is not the sole authority.
    assert rcsb.rcsb_entry_receipt(value) == rcsb.failed_rcsb_receipt(code, source_ref=SOURCE)
    assert value["values"] == [] and value["requested"]["entry_id"] == "4HHB"


@pytest.mark.parametrize("state,code", [
    ("missing", "rcsb_selected_field_missing"), ("unavailable", "rcsb_selected_field_unavailable"),
])
def test_missing_or_unavailable_selected_field_is_not_success_with_an_empty_issue_list(state, code):
    value = _legacy(_snapshot(native={"rcsb_id": "4HHB"},
        arguments=dict(entry_id="4HHB", fields=["cell"], max_bytes=8192)))
    value["issues"] = []
    value["values"][0]["state"] = state
    assert rcsb.rcsb_entry_receipt(value) == rcsb.failed_rcsb_receipt(code, source_ref=SOURCE)


@pytest.mark.parametrize("selected", ["OTHER", None])
def test_selected_native_id_cannot_contradict_the_observed_identity(selected):
    value = _legacy(_snapshot(arguments=dict(entry_id="4HHB", fields=["rcsb_id"], max_bytes=8192)))
    value["values"][0].update(state="native_null" if selected is None else "present", value=selected)
    value["issues"] = []
    assert rcsb.rcsb_entry_receipt(value) == rcsb.failed_rcsb_receipt("rcsb_request_conflict", source_ref=SOURCE)


@pytest.mark.parametrize("raw,code", [
    (b'{"rcsb_id":', "rcsb_invalid_native_json"),
    (b'{"rcsb_id":"4HHB","rcsb_id":"4HHB"}', "rcsb_invalid_native_json"),
    (b'{"rcsb_id":"4HHB","value":NaN}', "rcsb_invalid_native_json"),
    (b'[]', "rcsb_response_not_object"), (b'null', "rcsb_response_not_object"),
])
def test_malformed_or_nonobject_metadata_keeps_literal_bytes_without_invented_identity(raw, code):
    snapshot = _snapshot(raw=raw)
    value = _legacy(snapshot)
    value["issues"] = []
    assert rcsb.rcsb_entry_receipt(value) == rcsb.failed_rcsb_receipt(code, source_ref=SOURCE)
    assert snapshot.content == raw and value["observed_identity"]["state"] == "unavailable"


@pytest.mark.parametrize("change,code", [
    ({"http_status": None}, "rcsb_transport_metadata_unavailable"),
    ({"http_status": 302}, "rcsb_http_not_success"),
    ({"http_status": 404}, "rcsb_http_not_success"),
    ({"body_complete": False}, "rcsb_response_incomplete"),
    ({"body_complete": None}, "rcsb_transport_metadata_unavailable"),
    ({"observed_body_bytes": None}, "rcsb_transport_metadata_unavailable"),
    ({"observed_body_bytes": 0}, "rcsb_response_incomplete"),
    ({"declared_body_bytes": 0}, "rcsb_response_incomplete"),
])
@pytest.mark.parametrize("kind", ["entry", "file"])
def test_transfer_requires_explicit_response_confirmation_beyond_legacy_issues(kind, change, code):
    value = _legacy(_snapshot(kind), kind)
    value["issues"] = []
    value["response"].update(change)
    receipt = rcsb.rcsb_entry_receipt(value) if kind == "entry" else rcsb.rcsb_file_receipt(value)
    assert receipt == rcsb.failed_rcsb_receipt(code, source_ref=SOURCE)


@pytest.mark.parametrize("kind", ["entry", "file"])
def test_chunked_transfer_with_no_declared_length_is_confirmed(kind):
    value = _legacy(_snapshot(kind, transport={"declared_body_bytes": None}), kind)
    receipt = rcsb.rcsb_entry_receipt(value) if kind == "entry" else rcsb.rcsb_file_receipt(value)
    assert receipt["acquired"] is True and receipt["failure_code"] is None


@pytest.mark.parametrize("kind", ["entry", "file"])
def test_unprojected_transport_contradiction_remains_a_failure(kind):
    value = _legacy(_snapshot(kind, transport={"retained_body_bytes": False}), kind)
    assert value["response"]["http_status"] == 200 and value["response"]["body_complete"] is True
    receipt = rcsb.rcsb_entry_receipt(value) if kind == "entry" else rcsb.rcsb_file_receipt(value)
    assert receipt == rcsb.failed_rcsb_receipt("rcsb_transport_metadata_unavailable", source_ref=SOURCE)


@pytest.mark.parametrize("file_format", list(rcsb.FILE_FORMATS))
def test_file_confirmation_preserves_legacy_processing_label_and_unparsed_identity(file_format):
    arguments = dict(entry_id="pdb_00004hhb", file_format=file_format, max_bytes=8192)
    value = _legacy(_snapshot("file", arguments=arguments), "file")
    saved = deepcopy(value)
    assert value["version"] == "rcsb_file_result_v1"
    assert value["file"]["format"] == file_format and value["response"]["content_type"] == "application/json"
    assert value["observed_identity"] == dict(native_entry_id=None, state="not_parsed")
    assert rcsb.rcsb_file_receipt(value) == dict(acquired=True, source_ref=SOURCE,
        data_ref=value["file"]["artifact_ref"], failure_code=None)
    assert value == saved


@pytest.mark.parametrize("kind", ["entry", "file"])
def test_publication_preserves_actual_native_source_request_and_only_explicit_data(publisher, kind):
    store, tools = publisher
    snapshot = _snapshot(kind)
    receipt, refs = _publish(tools, kind, snapshot)
    source = store.get(receipt["source_ref"])
    assert receipt["acquired"] and refs == [source["id"], source["artifact_ref"]]
    assert receipt["data_ref"] == source["artifact_ref"]
    assert source["provider"] == rcsb.SERVICE and source["origin"] == "external" and source["version"] is None
    assert source["uri"] == snapshot.url and source["accession"] == snapshot.request["entry_id"]
    assert store.get_artifact(source["artifact_ref"]) == snapshot.content
    assert json.loads(store.get_artifact(source["request_ref"])) == {
        "request": snapshot.request, "transport": snapshot.transport}
    assert not source.get("auxiliary_artifact_refs")
    assert set(receipt) == {"acquired", "source_ref", "data_ref", "failure_code"}
    assert store.db.execute("SELECT count(*) FROM records WHERE record_type='source'").fetchone()[0] == 1


@pytest.mark.parametrize("case,code", [
    ("wrong_url", "rcsb_request_conflict"), ("wrong_service", "rcsb_request_conflict"),
    ("wrong_request", "rcsb_request_conflict"),
    ("missing_id", "rcsb_native_entry_id_missing"),
    ("missing_field", "rcsb_selected_field_missing"),
    ("http_error", "rcsb_http_not_success"),
    ("partial", "rcsb_response_incomplete"),
])
def test_captured_contradiction_retains_actual_source_bytes_and_returns_no_data(publisher, case, code):
    store, tools = publisher
    arguments = _arguments()
    snapshot = _snapshot()
    if case == "wrong_url":
        snapshot = replace(snapshot, url=snapshot.url + "/unselected")
    elif case == "wrong_service":
        snapshot = replace(snapshot, service="engineered_other_service")
    elif case == "wrong_request":
        snapshot = replace(snapshot, request={**arguments, "fields": []})
    elif case == "missing_id":
        snapshot = _snapshot(native={"cell": None, "rcsb_entry_info": {"count": 0}})
    elif case == "missing_field":
        snapshot = _snapshot(native={"rcsb_id": "4HHB", "cell": None})
    elif case == "http_error":
        snapshot = _snapshot(transport={"status": 404})
    else:
        snapshot = _snapshot(transport={"body_complete": False})
    receipt, refs = _publish(tools, "entry", snapshot, arguments=arguments)
    source = store.get(receipt["source_ref"])
    assert receipt == rcsb.failed_rcsb_receipt(code, source_ref=source["id"])
    assert refs == [source["id"]]
    assert store.get_artifact(source["artifact_ref"]) == snapshot.content
    assert source["uri"] == snapshot.url
    assert json.loads(store.get_artifact(source["request_ref"])) == {
        "request": snapshot.request, "transport": snapshot.transport}


def test_partial_coordinate_capture_retains_exact_prefix_without_data_confirmation(publisher):
    store, tools = publisher
    raw = b"captured partial coordinate bytes\x00"
    snapshot = _snapshot("file", raw=raw, transport={"body_complete": False,
        "observed_body_bytes": len(raw) + 9, "declared_body_bytes": len(raw) + 9})
    receipt, refs = _publish(tools, "file", snapshot)
    source = store.get(receipt["source_ref"])
    assert receipt == rcsb.failed_rcsb_receipt("rcsb_response_incomplete", source_ref=source["id"])
    assert refs == [source["id"]]
    assert store.get_artifact(source["artifact_ref"]) == raw
    assert json.loads(store.get_artifact(source["request_ref"])) == {
        "request": snapshot.request, "transport": snapshot.transport}


def test_unknown_operation_and_invalid_arguments_do_not_publish_a_source(publisher, monkeypatch):
    store, tools = publisher
    monkeypatch.setattr(tools, "_source", _forbidden)
    snapshot = _snapshot()
    with pytest.raises(ValueError, match="rcsb_operation_invalid"):
        rcsb.publish_rcsb_request(tools, "public.rcsb.unknown", snapshot.request, snapshot)
    with pytest.raises(ValueError):
        rcsb.publish_rcsb_request(tools, "public.rcsb.entry", {**snapshot.request, "max_bytes": True}, snapshot)
    assert store.db.execute("SELECT count(*) FROM records WHERE record_type='source'").fetchone()[0] == 0


def _receipt_rows(store):
    return {name: sorted((tuple(row) for row in store.db.execute(
        'SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr)
        for name, in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}


def _ordinary_rcsb_controller(path, initial):
    return FixtureController(str(path), initial, 1)


def _ordinary_rcsb_credit(*args, **kwargs):
    return 0


def _ordinary_rcsb_owner(store, tools, directory, scope, *, run_id, provider):
    workflow = Workflow(store, tools, provider, directory, run_id,
        _ordinary_rcsb_controller, _ordinary_rcsb_credit,
        project_child_credit=_ordinary_rcsb_credit, root_role="improvement",
        episode_record_receipts=True, initial_known_record_refs=[])
    root = workflow.build("improvement", "root",
        "Evaluate structural evidence for the supplied protein, keeping its correspondence to caller-selected "
        "reference data unresolved. One acquisition step does not settle a scientific conclusion.", scope)
    return workflow, root, workflow.binding_context(root.source)


@pytest.fixture
def ordinary_rcsb(request, tmp_path, monkeypatch):
    kind, calls = request.param, []
    selected = _snapshot(kind)
    operation, arguments = "public.rcsb." + kind, _arguments(kind)
    def http(client, service, url, params, media_type, **kwargs):
        assert service == rcsb.SERVICE and url == selected.url and params == {}
        assert kwargs == dict(max_bytes=8192, timeout_seconds=3, follow_redirects=False)
        calls.append(dict(service=service, url=url, media_type=media_type, **kwargs))
        return replace(selected, request=deepcopy(params))
    monkeypatch.setattr(PublicClients, "_http", http)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
        actor = ScriptedProvider([action(operation, arguments)])
        workflow, root, context = _ordinary_rcsb_owner(store, tools, tmp_path / "run", scope,
            run_id="rcsb-current-receipt-engineering", provider=actor)
        baseline = set(workflow.receipts.known(context.episode_id))
        assert workflow.permits_common_action(root.source, "tool")
        assert operation in {item["name"] for item in workflow.catalog(scope, source=root.source)}
        record = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(record))
        row, = store.db.execute("SELECT * FROM tool_operations")
        outcome = json.loads(row["result"])
        receipt = rcsb.validate_rcsb_receipt(outcome["result"])
        assert receipt["acquired"] and outcome["status"] == "completed"
        yield SimpleNamespace(kind=kind, selected=selected, calls=calls, store=store, tools=tools,
            scope=scope, actor=actor, workflow=workflow, root=root, context=context,
            baseline=baseline, operation=operation, arguments=arguments,
            operation_key=row["operation_key"], outcome=outcome, receipt=receipt,
            source=store.get(receipt["source_ref"]))


@pytest.mark.parametrize("ordinary_rcsb", ["entry", "file"], indirect=True)
def test_ordinary_rcsb_current_episode_receives_explicit_source_data_and_cached_result(ordinary_rcsb, monkeypatch):
    case = ordinary_rcsb
    store, tools, source = case.store, case.tools, case.source
    assert case.outcome["record_refs"] == [source["id"], source["artifact_ref"]]
    assert case.receipt == dict(acquired=True, source_ref=source["id"],
        data_ref=source["artifact_ref"], failure_code=None)
    assert store.get_artifact(source["artifact_ref"]) == case.selected.content
    assert json.loads(store.get_artifact(source["request_ref"])) == {
        "request": case.arguments, "transport": case.selected.transport}
    known = set(case.workflow.receipts.known(case.context.episode_id))
    assert known == case.baseline | {source["id"], source["artifact_ref"]}
    assert source["request_ref"] not in known
    resolve = case.workflow.resolver(plain(case.context.scope), context=case.context)
    for reference, namespace in ((source["id"], "source"), (source["artifact_ref"], "artifact")):
        assert resolve(reference, namespace) is True
        assert tools.retained_molecular_reference_access(case.context, reference, namespace) is True
        received, path = case.workflow.services.read_received_molecular_input(
            case.context, reference, namespace, file_format="text")
        assert received["failure"] is None and received["input"]["byte_verification"] == "verified"
        assert received["input"]["file"]["artifact_ref"] == source["artifact_ref"]
        assert path.read_bytes() == case.selected.content
    assert resolve(source["request_ref"], "artifact") is False
    assert tools.retained_molecular_reference_access(case.context, source["request_ref"], "artifact") is False
    body_args = dict(source_ref=source["id"], representation="original", offset=0, limit=8192)
    with tools.current_invocation(case.context, read_received=case.workflow.services.read_received_molecular_input,
            tool_name="source.read", arguments=body_args, operation_key="metadata-body-policy-probe"):
        assert tools._check_molecular_source_bytes("source.read", body_args) is None
    assert len(case.calls) == len(case.actor.contexts) == 1
    assert {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in
        ("runtime_episodes", "runtime_actions", "runtime_model_calls", "runtime_observations", "tool_operations")} == {
        "runtime_episodes": 1, "runtime_actions": 1, "runtime_model_calls": 1,
        "runtime_observations": 1, "tool_operations": 1}
    assert store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
    assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0
    action_row = json.loads(store.db.execute("SELECT action FROM runtime_actions").fetchone()[0])
    assert action_row == dict(kind="tool", tool=case.operation, arguments=case.arguments)
    monkeypatch.setattr(PublicClients, "_http", _forbidden)
    monkeypatch.setattr(rcsb, "publish_rcsb_request", _forbidden)
    monkeypatch.setattr(rcsb, "rcsb_entry_result", _forbidden)
    monkeypatch.setattr(rcsb, "rcsb_file_result", _forbidden)
    monkeypatch.setattr(Store, "get_artifact", _forbidden)
    before = _receipt_rows(store)
    with tools.current_invocation(case.context, read_received=case.workflow.services.read_received_molecular_input,
            tool_name=case.operation, arguments=case.arguments, operation_key=case.operation_key):
        cached = tools.execute(case.operation, case.arguments, scope=plain(case.context.scope),
            operation_key=case.operation_key)
    assert cached == case.outcome and _receipt_rows(store) == before


@pytest.mark.parametrize("ordinary_rcsb", ["entry", "file"], indirect=True)
def test_unreceived_rcsb_context_denies_native_file_and_source_body_before_bytes(ordinary_rcsb, tmp_path, monkeypatch):
    case = ordinary_rcsb
    other, root, context = _ordinary_rcsb_owner(case.store, case.tools, tmp_path / "other-run", case.scope,
        run_id="rcsb-unreceived-engineering", provider=ScriptedProvider([]))
    before_known = set(other.receipts.known(context.episode_id))
    assert {case.source["id"], case.source["artifact_ref"]}.isdisjoint(before_known)
    monkeypatch.setattr(Store, "get_artifact", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.molecular_sequence_input_bindings.retained_native_file", _forbidden)
    resolve = other.resolver(plain(context.scope), context=context)
    for reference, namespace in ((case.source["id"], "source"), (case.source["artifact_ref"], "artifact")):
        assert case.tools.retained_molecular_reference_access(context, reference, namespace) is False
        assert resolve(reference, namespace) is False
        received, path = other.services.read_received_molecular_input(context, reference, namespace, file_format="text")
        assert received["failure"] is not None and received["input"] is None and path is None
    body_args = dict(source_ref=case.source["id"], representation="original", offset=0, limit=8192)
    # A metadata access probe through the actual registry, not an invented
    # RuntimeAction completion or a model/scientific observation.
    with case.tools.current_invocation(context, read_received=other.services.read_received_molecular_input,
            tool_name="source.read", arguments=body_args, operation_key="unreceived-rcsb-body-read"):
        denied = case.tools.execute("source.read", body_args, scope=plain(context.scope),
            operation_key="unreceived-rcsb-body-read")
    assert denied["status"] == "invalid" and denied["record_refs"] == [] and denied["result"] is None
    assert denied["feedback"]["code"] == "rcsb_source_primary_body_not_received"
    assert set(other.receipts.known(context.episode_id)) == before_known
    assert case.store.db.execute("SELECT count(*) FROM runtime_actions WHERE episode_id=?", (context.episode_id,)).fetchone()[0] == 0
    assert case.store.db.execute("SELECT count(*) FROM runtime_model_calls WHERE episode_id=?", (context.episode_id,)).fetchone()[0] == 0
    assert len(case.calls) == 1


@pytest.mark.parametrize("kind", ["entry", "file"])
def test_ordinary_rcsb_no_response_has_finite_receipt_private_diagnostic_and_exact_cache(tmp_path, monkeypatch, kind):
    calls = []
    selected = _snapshot(kind)
    def no_response(client, service, url, params, media_type, **kwargs):
        assert service == rcsb.SERVICE and url == selected.url and params == {}
        assert kwargs == dict(max_bytes=8192, timeout_seconds=3, follow_redirects=False)
        calls.append(url)
        raise AcquisitionError("provider_connection_failed", phase="http_request",
            diagnostic={"qualification": "engineered failure without any response"})
    monkeypatch.setattr(PublicClients, "_http", no_response)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
        workflow, root, context = _ordinary_rcsb_owner(store, tools, tmp_path / "run", scope,
            run_id="rcsb-no-response-engineering", provider=ScriptedProvider([]))
        baseline = set(workflow.receipts.known(context.episode_id))
        source_rows_before = [row["id"] for row in store.list("source")]
        operation, arguments, key = "public.rcsb." + kind, _arguments(kind), "rcsb-selected-no-response"
        monkeypatch.setattr(tools, "_source", _forbidden)
        with tools.current_invocation(context, read_received=workflow.services.read_received_molecular_input,
                tool_name=operation, arguments=arguments, operation_key=key):
            outcome = tools.execute(operation, arguments, scope=plain(context.scope), operation_key=key)
        assert outcome["status"] == "failed" and outcome["record_refs"] == []
        assert rcsb.validate_rcsb_receipt(outcome["result"]) == rcsb.failed_rcsb_receipt("data_acquisition_failed")
        assert [row["id"] for row in store.list("source")] == source_rows_before
        diagnostic = outcome["feedback"]["diagnostic_ref"]
        assert type(diagnostic) is str and diagnostic.startswith("artifact_")
        assert outcome["feedback"]["code"] == "provider_connection_failed"
        assert calls == [selected.url] and set(workflow.receipts.known(context.episode_id)) == baseline
        assert tools.retained_molecular_reference_access(context, diagnostic, "artifact") is False
        assert workflow.resolver(plain(context.scope), context=context)(diagnostic, "artifact") is False
        monkeypatch.setattr(PublicClients, "_http", _forbidden)
        monkeypatch.setattr(Store, "get_artifact", _forbidden)
        monkeypatch.setattr(rcsb, "publish_rcsb_request", _forbidden)
        before = _receipt_rows(store)
        with tools.current_invocation(context, read_received=workflow.services.read_received_molecular_input,
                tool_name=operation, arguments=arguments, operation_key=key):
            cached = tools.execute(operation, arguments, scope=plain(context.scope), operation_key=key)
        assert cached == outcome and _receipt_rows(store) == before
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_model_calls").fetchone()[0] == 0
