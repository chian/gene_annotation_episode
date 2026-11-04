"""Engineering HTTP/control tests and projection-only retained231 checks.

HTTP bodies below are explicitly supplied fixtures, never live predictions.
Lexical worker-request fields are shape controls, not producer/handle custody.
No native handle, Source producer or scientific execution receipt is invented.
The existing231 calculator is never rerun by these tests.
"""
import asyncio
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode import protein_disorder_measurements as core
from gene_annotation_episode import protein_disorder_result_contracts as contracts
from gene_annotation_episode import protein_disorder_tools as adapter
from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.runtime import ActionFailure, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_molecular_provider_acquisition_host import _controller, _credit, _scope
from test_protein_disorder_result_contracts import CASES, SOURCE, prepared, request, selection
from test_runtime import ScriptedProvider


def forbidden(*args, **kwargs):
    raise AssertionError("engineering disorder control attempted network, numerical or native execution")


def worker_request(tmp_path, *, mode="predict"):
    """Explicit shape-only request; no corresponding runtime producer exists."""
    invocation = dict(run_id="engineered-disorder-request", episode_id="episode_" + "a" * 64,
        decision_index=0, request_sha256="b" * 64, scope={"subject_refs": []})
    invocation["operation_key"] = invocation["run_id"] + ":" + invocation["episode_id"] + ":0"
    directory = tmp_path / "cache/molecular-measurements" / digest(invocation["operation_key"]) / "worker"
    directory.mkdir(parents=True)
    if mode == "predict":
        arguments = dict(mode="predict", protein_sequence=" A-c\nD2E", threshold=None, max_bytes=4096,
            selection=selection())
        return adapter._request(arguments, invocation, directory, timeout_seconds=3)
    arguments, sheet, _ = prepared()
    return adapter._request(arguments, invocation, directory, sheet=sheet)


def fixture_http(monkeypatch, *, mode="success"):
    """Replace only HTTP with a complete, labelled engineering response."""
    calls = []
    def http(client, service, url, params, media_type, **kwargs):
        calls.append(dict(service=service, url=url, params=params, media_type=media_type, **kwargs))
        if mode == "no_response":
            raise AcquisitionError("provider_connection_failed", phase="http_request")
        raw = b"\xff\x00" if mode == "invalid_utf8" else b"# engineered fixture\n1 A .7\n2 c .8\n"
        original_size = len(raw)
        if mode == "cap":
            raw = raw[:kwargs["max_bytes"]]
        transport = dict(status=503 if mode == "http_error" else 200,
            headers={"content-type": "text/plain"}, header_items=[("Content-Type", "text/plain")],
            request=dict(method="POST", url=url, headers={"Content-type": kwargs["content_type"]},
                body_base64=base64.b64encode(kwargs["body"]).decode("ascii"),
                body_sha256=hashlib.sha256(kwargs["body"]).hexdigest()),
            request_policy=dict(timeout_seconds=kwargs["timeout_seconds"], automatic_redirects=kwargs["follow_redirects"]),
            body_complete=mode != "cap", retained_body_bytes=len(raw),
            observed_body_bytes=kwargs["max_bytes"] + 1 if mode == "cap" else len(raw),
            declared_body_bytes=original_size, response_byte_limit=kwargs["max_bytes"])
        if mode == "cap":
            transport["body_capture_failure"] = "provider_response_byte_limit"
        snapshot = SourceSnapshot(service, url, {}, "2026-11-02T00:00:00Z", raw, "text/plain", transport)
        if mode in ("http_error", "cap"):
            raise AcquisitionError("provider_http_503" if mode == "http_error" else "provider_response_byte_limit",
                snapshot=snapshot, phase="http_response")
        return snapshot
    monkeypatch.setattr(PublicClients, "_http", http)
    monkeypatch.setattr(PublicClients, "_skill", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    monkeypatch.setattr(core, "build_disorder_sheet", forbidden)
    monkeypatch.setattr(core, "calculate_disorder_components", forbidden)
    return calls


def test_frozen_post_has_exact_original_case_and_form_without_a_default_threshold(tmp_path):
    value = worker_request(tmp_path)
    post = value["post"]
    assert value["input"] == dict(protein_sequence=" A-c\nD2E", threshold=None, input_ref=None, input_mapping=None)
    assert post["form"] == dict(seq="AcDE", iupred2="long", anchor2="no")
    assert bytes.fromhex(post["body_hex"]) == b"seq=AcDE&iupred2=long&anchor2=no"
    assert post["url"] == contracts.ENDPOINT and post["method"] == "POST"
    assert post["follow_redirects"] is False and post["timeout_seconds"] == 3 and post["max_bytes"] == 4096
    assert adapter.validate_disorder_worker_request(value) == value
    assert adapter.protein_disorder_tool_contract()["input_schema"] == contracts.protein_disorder_result_schema("Arguments")


@pytest.mark.parametrize("mutation", ["url", "mode", "form", "body", "size", "timeout", "extra", "directory", "inline_ref"])
def test_worker_request_rejects_selected_input_form_and_path_changes(tmp_path, mutation):
    value = worker_request(tmp_path)
    if mutation == "url": value["post"]["url"] += "/other"
    elif mutation == "mode": value["post"]["form"]["iupred2"] = "short"
    elif mutation == "form": value["post"]["form"]["seq"] = "ACDE"
    elif mutation == "body": value["post"]["body_hex"] += "00"
    elif mutation == "size": value["post"]["body_size_bytes"] += 1
    elif mutation == "timeout": value["post"]["timeout_seconds"] = True
    elif mutation == "extra": value["arguments"]["endpoint"] = contracts.ENDPOINT
    elif mutation == "directory": value["directory"] = "relative/worker"
    else: value["input"]["input_ref"] = SOURCE
    with pytest.raises(ValueError):
        adapter.validate_disorder_worker_request(value)


@pytest.mark.parametrize("mode,native_outcome", [("success", "completed"), ("http_error", "failed"),
    ("cap", "partial"), ("invalid_utf8", "failed"), ("no_response", "failed")])
def test_engineered_http_response_is_literal_sealed_and_never_automatically_resent(tmp_path, monkeypatch, mode, native_outcome):
    value = worker_request(tmp_path)
    if mode == "cap":
        arguments = {**value["arguments"], "max_bytes": 8}
        value = adapter._request(arguments, value["invocation"], value["directory"], timeout_seconds=3)
    calls = fixture_http(monkeypatch, mode=mode)
    result = adapter._perform_post(value)
    directory = Path(value["directory"])
    assert len(calls) == 1 and calls[0]["body"] == bytes.fromhex(value["post"]["body_hex"])
    assert json.loads((directory / "post-started.json").read_bytes()) == dict(invocation=value["invocation"], post=value["post"])
    assert json.loads((directory / "transport-seal.json").read_bytes()) == result
    assert adapter._native_outcome(result) == native_outcome
    if mode == "no_response":
        assert result["snapshot"] is result["response_hex"] is result["response_text"] is None
        assert not (directory / "native-response.bin").exists()
    else:
        raw = (directory / "native-response.bin").read_bytes()
        assert result["response_hex"] == raw.hex()
        assert result["snapshot"]["transport"]["header_items"] == [["Content-Type", "text/plain"]]
        assert result["decode_state"] == ("invalid_utf8" if mode == "invalid_utf8" else "decoded")
    with pytest.raises(ContractError, match="protein_disorder_post_already_attempted"):
        adapter._perform_post(value)
    assert len(calls) == 1


def test_transport_is_durable_before_any_native_output_parser_or_calculator(tmp_path, monkeypatch):
    value = worker_request(tmp_path)
    calls = fixture_http(monkeypatch)
    def stop_before_parsing(*args, **kwargs):
        assert (Path(value["directory"]) / "native-response.bin").is_file()
        assert (Path(value["directory"]) / "transport-seal.json").is_file()
        assert kwargs["native_response"] == "# engineered fixture\n1 A .7\n2 c .8\n"
        assert args == (None,) and kwargs["native_log"] is None
        raise RuntimeError("engineered stop before parsing; no scientific calculation")
    monkeypatch.setattr(core, "build_disorder_sheet", stop_before_parsing)
    result = adapter.run_disorder_tool_request(value)
    assert len(calls) == 1 and result["sheet"] is result["components"] is None
    assert result["calculation"] == dict(state="failed", call_count=0)
    assert result["error"]["message"].startswith("engineered stop before parsing")


@pytest.mark.parametrize("field", ["declared_body_bytes", "response_byte_limit"])
def test_unknown_or_boolean_transfer_counts_never_attest_a_complete_response(tmp_path, monkeypatch, field):
    value = worker_request(tmp_path)
    fixture_http(monkeypatch)
    transport = adapter._perform_post(value)
    transport["snapshot"]["transport"][field] = False
    assert adapter._native_outcome(transport) == "partial"


@pytest.mark.parametrize("field", ["content_type", "observed_body_bytes", "retained_body_bytes", "response_byte_limit"])
def test_observed_request_content_type_and_response_extent_must_match_sealed_controls(tmp_path, monkeypatch, field):
    value = worker_request(tmp_path)
    fixture_http(monkeypatch)
    transport = adapter._perform_post(value)
    if field == "content_type":
        transport["snapshot"]["transport"]["request"]["headers"]["Content-type"] = "application/json"
    else:
        transport["snapshot"]["transport"][field] = False
    with pytest.raises(ContractError):
        adapter._validate_transport(transport, value)


def test_saved_worker_uses_only_the_injected_calculator_port_and_keeps_original_inputs(tmp_path, monkeypatch):
    """Port wiring only: original231 Components are returned without recalculation."""
    value = worker_request(tmp_path, mode="calculate_saved")
    _, sheet, components = prepared()
    calls = []
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr(core, "build_disorder_sheet", forbidden)
    def injected(stored_sheet):
        calls.append(deepcopy(stored_sheet))
        assert stored_sheet == sheet
        return deepcopy(components)
    monkeypatch.setattr(core, "calculate_disorder_components", injected)
    result = adapter.run_disorder_tool_request(value)
    assert calls == [sheet] and result["components"] == components and result["sheet"] == sheet
    assert result["transport"]["state"] == "not_requested" and result["transport"]["post"] is None
    assert result["calculation"] == dict(state="completed", call_count=1)
    assert result["components"]["summary"]["scientific_service_execution_verified"] is False


def test_known_calculator_port_exception_preserves_one_entered_call(tmp_path, monkeypatch):
    value = worker_request(tmp_path, mode="calculate_saved")
    calls = []
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr(core, "build_disorder_sheet", forbidden)
    def injected(sheet):
        calls.append(sheet)
        raise RuntimeError("engineered calculator-port exception, no numerical implementation invoked")
    monkeypatch.setattr(core, "calculate_disorder_components", injected)
    result = adapter.run_disorder_tool_request(value)
    assert len(calls) == 1 and result["components"] is None
    assert result["calculation"] == dict(state="failed", call_count=1)


@pytest.mark.parametrize("mutation", ["call_count_bool", "saved_transport", "request_input", "sheet", "components", "error"])
def test_worker_result_rejects_false_calculation_and_saved_native_claims(tmp_path, monkeypatch, mutation):
    """Literal retained values test shape/joins, never a producing-worker receipt."""
    selected = worker_request(tmp_path, mode="calculate_saved")
    _, sheet, components = prepared()
    value = dict(version=adapter.RESULT_VERSION, request=selected,
        transport=dict(version=adapter.TRANSPORT_VERSION, state="not_requested", post=None, snapshot=None,
            response_hex=None, decode_state="missing", response_text=None, failure=None),
        sheet=sheet, components=components, calculation=dict(state="completed", call_count=1), error=None)
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr(core, "build_disorder_sheet", forbidden)
    monkeypatch.setattr(core, "calculate_disorder_components", forbidden)
    assert adapter.validate_disorder_worker_result(value) == value
    changed = deepcopy(value)
    if mutation == "call_count_bool": changed["calculation"]["call_count"] = True
    elif mutation == "saved_transport": changed["transport"]["state"] = "response_received"
    elif mutation == "request_input": changed["request"]["input"]["protein_sequence"] += "A"
    elif mutation == "sheet": changed["sheet"]["inputs"]["threshold"] = .9
    elif mutation == "components": changed["components"]["summary"]["scientific_service_execution_verified"] = True
    else: changed["error"] = dict(exception_type="engineered", message="not a completed calculator return")
    with pytest.raises(ValueError):
        adapter.validate_disorder_worker_result(changed)


@pytest.mark.parametrize("case", CASES)
def test_projection_only_new_stored_rows_keep_original231_values_without_calculation(monkeypatch, case):
    arguments, sheet, components = prepared(case=case)
    packet = contracts.ordinary_disorder_packet(arguments=arguments, sheet=sheet, components=components)
    public = contracts.project_ordinary_disorder_return(packet, SOURCE)
    publication = dict(public=public, sheet=sheet, components=components, source=dict(id=SOURCE))
    changed = dict(mode="read_stored", result_ref=SOURCE, selection=selection(
        request("residue", ["score_value", "score_token"], row_ordinal=0),
        request("summary", ["descriptive_mean_score", "descriptive_mean_denominator_rows"])))
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr(core, "build_disorder_sheet", forbidden)
    monkeypatch.setattr(core, "calculate_disorder_components", forbidden)
    actual = adapter._read_selected(publication, changed)
    assert actual == contracts.project_ordinary_disorder_return(contracts.ordinary_disorder_packet(
        arguments=changed, sheet=sheet, components=components), SOURCE)
    assert actual["source_ref"] == SOURCE and actual["values"]["context"] == public["values"]["context"]


def test_orphaned_post_marker_cannot_prepare_a_replacement_handle(tmp_path, monkeypatch):
    value = worker_request(tmp_path)
    directory = Path(value["directory"])
    (directory / "post-started.json").write_text(json.dumps(dict(invocation=value["invocation"], post=value["post"])))
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    with Store(tmp_path / "store") as store:
        registry = ToolRegistry(store)
        intent = dict(policy=registry.local_job_policy.to_dict(), request=value)
        with pytest.raises(ContractError, match="protein_disorder_original_worker_handle_missing"):
            adapter._dispatch(registry, intent, directory)


def test_started_post_without_response_seal_stays_unconfirmed_without_any_handle_fabrication(tmp_path, monkeypatch):
    """Engineered marker exercises the gate, not a claim that a POST occurred."""
    value = worker_request(tmp_path)
    directory = Path(value["directory"])
    adapter._immutable(directory / "post-started.json", dict(invocation=value["invocation"], post=value["post"]))
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    with pytest.raises(adapter.MolecularOperationUnpublished, match="protein_disorder_post_outcome_unconfirmed"):
        adapter._post_completion_gate(directory, value)
    assert not (directory / "native-handle.json").exists()


def test_direct_tool_call_without_actual_runtime_invocation_is_denied_before_http(tmp_path, monkeypatch):
    value = worker_request(tmp_path)
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr(core, "calculate_disorder_components", forbidden)
    with Store(tmp_path / "store") as store:
        registry = ToolRegistry(store)
        with pytest.raises(ContractError, match="molecular_tool_current_invocation_required"):
            asyncio.run(adapter.execute_protein_disorder_tool(registry, value["arguments"],
                scope=_scope(store), operation_key="not-an-actual-selected-action", authority=None))


def test_real_current_episode_unknown_saved_source_is_denied_without_private_bytes_or_work(tmp_path, monkeypatch):
    """Actual selected action, with no invented earlier Source or grant."""
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr(core, "build_disorder_sheet", forbidden)
    monkeypatch.setattr(core, "calculate_disorder_components", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    with Store(tmp_path / "store") as store:
        registry = ToolRegistry(store)
        scope = _scope(store)
        assert contracts.TOOL in registry.catalog(scope)
        actor = ScriptedProvider([])
        workflow = Workflow(store, registry, actor, tmp_path / "run", "engineering-disorder-receipt-denial",
            _controller, _credit, project_child_credit=_credit, root_role="improvement", episode_record_receipts=True,
            initial_known_record_refs=[])
        root = workflow.build("improvement", "root", "Inspect only a supplied retained disorder result.", scope)
        before = {source["id"] for source in store.list("source")}
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        with pytest.raises(ActionFailure):
            asyncio.run(root.source.execute(dict(kind="tool", tool=contracts.TOOL,
                arguments=dict(mode="read_stored", result_ref=SOURCE, selection=selection())), 0))
        outcome = json.loads(store.db.execute("SELECT result FROM tool_operations").fetchone()[0])
        assert outcome["status"] == "invalid" and outcome["result"] is None and outcome["record_refs"] == []
        assert {source["id"] for source in store.list("source")} == before
        assert actor.contexts == [] and store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_record_receipts WHERE record_ref=?", (SOURCE,)).fetchone()[0] == 0
