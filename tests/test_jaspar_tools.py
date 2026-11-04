"""Engineered JASPAR getter controls; no live matrix requests or site scoring.

Publisher-unit cases use the real Source writer in an explicit publication
context, without inventing an action/history. The final ordinary Workflow
cases require the finite shared getter wiring and exercise one existing caller,
not an acquisition-specific child or scientific analysis.
"""
import asyncio
from copy import deepcopy
from email.message import Message
import hashlib
import io
import json
from types import SimpleNamespace
from urllib.parse import urlencode
import urllib.request
from urllib.response import addinfourl

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.communication import validate_closed_schema, validate_form
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode import jaspar_tools as jaspar
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


DISCOVER = {"operation": "discover", "filters": {"name": "ABF1", "tax_id": "4932,9606"},
    "version_mode": "provider_default", "page": 1, "page_size": 10, "max_bytes": 65536}
MATRIX = {"operation": "matrix", "matrix_id": "PB0001.1", "representation": "json", "max_bytes": 65536}
PFM = {**MATRIX, "representation": "pfm"}
# The repeated native row and shared TF label are intentional. Neither is a
# reason to choose a first match, discard a row, or acquire a second response.
PAGE = b'{"count":23,"next":"https://jaspar.elixir.no/api/v1/matrix/?page=2","previous":null,"results":[{"matrix_id":"PB0001.1","name":"ABF1","base_id":"PB0001","version":"1"},{"matrix_id":"MA0265.2","name":"ABF1","base_id":"MA0265","version":"2"},{"matrix_id":"PB0001.1","name":"ABF1","base_id":"PB0001","version":"1"}]}'
MATRIX_BYTES = b'{"matrix_id":"PB0001.1","base_id":"PB0001","version":1,"name":"ABF1","pfm":{"A":[0.000,1e-9999],"C":[2,0],"G":[0,3.50],"T":[4,0]},"species":[{"tax_id":4932,"name":"native label"}]}'
PFM_BYTES = b'>PB0001.1 ABF1\n0.000 1e-9999\n2 0\n0 3.50\n4 0\n'


def forbidden(*args, **kwargs):
    raise AssertionError("getter attempted an unselected request, model, native program or calculation")


class Responses(PublicClients):
    """Only the shared HTTP seam is controlled, with literal transport data."""
    def __init__(self, *, raw=None, mode="success"):
        super().__init__(ncbi_email=None, timeout=3)
        self.raw, self.mode, self.calls, self.snapshots = raw, mode, [], []

    def _http(self, service, url, params, media_type, **options):
        self.calls.append({"service": service, "url": url, "params": deepcopy(params),
            "media_type": media_type, **options})
        if self.mode == "no_response":
            raise AcquisitionError("provider_connection_failed", phase="http_request")
        raw = self.raw
        if raw is None:
            raw = PAGE if url == jaspar.ROOT else PFM_BYTES if params["format"] == "pfm" else MATRIX_BYTES
        cap = options["max_bytes"]
        content, complete = raw[:cap], len(raw) <= cap
        status = {"http_error": 503, "redirect": 302, "range": 206}.get(self.mode, 200)
        address = url + "?" + urlencode(params)
        headers = [["Content-Type", "application/json" if params["format"] == "json" else "text/plain"]]
        if self.mode == "encoding": headers.append(["Content-Encoding", "gzip"])
        if self.mode == "range": headers.append(["Content-Range", "bytes 0-1/100"])
        if self.mode == "html_type": headers = [["Content-Type", "text/html"]]
        transport = {"status": status, "representation": "http_response_bytes", "header_items": headers,
            "headers": {key.lower(): value for key, value in headers},
            "effective_url": address, "request": {"method": "GET", "url": address,
                "headers": {"Accept": options["accept"]}},
            "request_policy": {"timeout_seconds": options["timeout_seconds"], "automatic_redirects": options["follow_redirects"]},
            "response_byte_limit": cap, "body_complete": complete,
            "retained_body_bytes": len(content), "observed_body_bytes": min(len(raw), cap + 1),
            "declared_body_bytes": len(raw)}
        if not complete: transport["body_capture_failure"] = "provider_response_byte_limit"
        if self.mode == "unknown_complete": transport["body_complete"] = None
        if self.mode == "capture_error": transport["body_capture_error"] = "IncompleteRead"
        if self.mode == "wrong_size": transport["observed_body_bytes"] += 1
        if self.mode == "status_bool": transport["status"] = True
        if self.mode == "other_effective": transport["effective_url"] = "https://example.invalid/other"
        if self.mode == "other_accept": transport["request"]["headers"]["Accept"] = "text/html"
        if self.mode == "other_method": transport["request"]["method"] = "POST"
        if self.mode == "other_timeout": transport["request_policy"]["timeout_seconds"] = 4
        if self.mode == "other_redirect_policy": transport["request_policy"]["automatic_redirects"] = True
        if self.mode == "other_limit": transport["response_byte_limit"] += 1
        native = {**params, "name": "not-selected"} if self.mode == "other_request" else deepcopy(params)
        observed_url = address if status != 200 else url
        if self.mode == "other_url": observed_url = "https://example.invalid/other"
        snapshot = SourceSnapshot(service, observed_url, native, "2026-11-01T12:00:00+00:00", content, media_type, transport)
        self.snapshots.append(snapshot)
        if status >= 300 or not complete:
            raise AcquisitionError("provider_http_" + str(status), snapshot=snapshot, phase="http_response")
        return snapshot


@pytest.fixture
def host(tmp_path):
    with Store(tmp_path / "store") as store:
        target, = store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]
        client = Responses()
        yield SimpleNamespace(store=store, client=client, tools=ToolRegistry(store, clients=client),
            scope={"subject_refs": [target]})


def publish(host, arguments, snapshot):
    # An isolated internal-publisher test, not a fabricated successful ToolOp.
    token = host.tools._publications.set([])
    try:
        with host.store.transaction():
            return jaspar.publish_jaspar_request(host.tools, arguments, snapshot)
    finally:
        host.tools._publications.reset(token)


@pytest.mark.parametrize("mode,expected", [("provider_default", None), ("latest", "latest")])
def test_discovery_uses_documented_version_key_without_an_all_value(mode, expected):
    args = {**DISCOVER, "version_mode": mode, "page": 2}
    spec = jaspar.jaspar_request_spec(args)
    assert spec["url"] == "https://jaspar.elixir.no/api/v1/matrix/"
    assert spec["params"] == {**DISCOVER["filters"], "page": 2, "page_size": 10, "format": "json",
        **({"version": "latest"} if expected else {})}
    assert "matrix_versions" not in spec["params"] and "version_mode" not in spec["params"]
    assert spec["follow_redirects"] is False and spec["max_bytes"] == args["max_bytes"]


@pytest.mark.parametrize("matrix_id", ["MA0265.1", "UN0001.2", "PB0001.1", "PH0001.1", "legacy_Alpha-2.03", "X.a~b.0"])
def test_versioned_identifiers_are_opaque_single_components_without_prefix_selection(matrix_id):
    for representation in ("json", "pfm"):
        spec = jaspar.jaspar_request_spec({**MATRIX, "matrix_id": matrix_id, "representation": representation})
        assert spec["url"] == jaspar.ROOT + matrix_id + "/"
        assert spec["params"] == {"format": representation}
        assert spec["accept"] == ("application/json" if representation == "json" else "*/*")


@pytest.mark.parametrize("arguments", [
    {**DISCOVER, "version_mode": "all"}, {key: value for key, value in DISCOVER.items() if key != "page"},
    {**DISCOVER, "page": True}, {**DISCOVER, "page_size": 0}, {**DISCOVER, "page_size": 101},
    {**DISCOVER, "filters": {"release": "2026"}}, {**DISCOVER, "filters": {"name": "bad\nname"}},
    {**DISCOVER, "filters": {"name": "\ud800"}}, {**MATRIX, "max_bytes": True},
    {**MATRIX, "max_bytes": jaspar.MAX_BYTES + 1}, {**MATRIX, "url": "https://example.invalid"},
    *[{**MATRIX, "matrix_id": value} for value in ["MA0265", "../MA0265.1", "x/y.1", "x%2fy.1", "x?y.1", "x.1\n", "é.1"]],
])
def test_invalid_choices_fail_before_any_http(arguments):
    client = SimpleNamespace(timeout=3, _http=forbidden)
    with pytest.raises(ContractError, match="^jaspar_arguments_invalid$"):
        jaspar.request_jaspar(client, arguments)


@pytest.mark.parametrize("timeout", [None, True, 0, float("inf"), 10 ** 1000])
def test_invalid_transport_timeout_is_rejected_before_http(timeout):
    with pytest.raises(ContractError, match="^jaspar_timeout_invalid$"):
        jaspar.request_jaspar(SimpleNamespace(timeout=timeout, _http=forbidden), MATRIX)


@pytest.mark.parametrize("arguments,raw", [(DISCOVER, PAGE), (MATRIX, MATRIX_BYTES), (PFM, PFM_BYTES)])
def test_selected_original_bytes_and_native_associations_are_the_delivered_data(host, arguments, raw):
    snapshot = jaspar.request_jaspar(host.client, arguments)
    receipt, refs = publish(host, arguments, snapshot)
    source = host.store.get(receipt["source_ref"])
    assert receipt == {"acquired": True, "source_ref": source["id"],
        "data_ref": "artifact_" + hashlib.sha256(raw).hexdigest(), "failure_code": None}
    assert refs == [source["id"], source["artifact_ref"]] and source["artifact_ref"] == receipt["data_ref"]
    assert source["provider"] == jaspar.TOOL and source["origin"] == "external" and source["version"] is None
    assert source["accession"] == (arguments["matrix_id"] if arguments["operation"] == "matrix" else None)
    assert source["uri"] == snapshot.transport["request"]["url"]
    assert host.store.get_artifact(receipt["data_ref"]) == raw
    controls = json.loads(host.store.get_artifact(source["request_ref"]))
    assert controls == {"request": snapshot.request, "transport": snapshot.transport}
    assert controls["request"]["native_request"] == jaspar.jaspar_request_spec(arguments)["params"]
    assert len(host.client.calls) == 1 and source["request_ref"] not in refs
    assert host.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
    assert host.store.count("observation") == host.store.count("annotation") == 0


@pytest.mark.parametrize("arguments,raw", [
    (DISCOVER, b'{"count":0,"next":null,"previous":null,"results":[]}'),
    (PFM, b'>PB0001.1 zero\n0 0\n0 0\n0 0\n0 0\n'),
])
def test_valid_empty_page_and_zero_matrix_are_data_without_a_scientific_threshold(host, arguments, raw):
    host.client.raw = raw
    receipt, _ = publish(host, arguments, jaspar.request_jaspar(host.client, arguments))
    assert receipt["acquired"] is True and host.store.get_artifact(receipt["data_ref"]) == raw


@pytest.mark.parametrize("mode,code", [
    ("http_error", "jaspar_http_not_successful"), ("redirect", "jaspar_http_not_successful"),
    ("range", "jaspar_partial_response"), ("unknown_complete", "jaspar_capture_incomplete"),
    ("capture_error", "jaspar_capture_incomplete"), ("wrong_size", "jaspar_capture_identity_mismatch"),
    ("encoding", "jaspar_content_encoding_unsupported"), ("status_bool", "jaspar_http_status_unavailable"),
    ("html_type", "jaspar_native_representation_invalid"),
    ("other_request", "jaspar_selected_request_mismatch"), ("other_url", "jaspar_selected_request_mismatch"),
    ("other_effective", "jaspar_selected_request_mismatch"), ("other_accept", "jaspar_selected_request_mismatch"),
    ("other_method", "jaspar_selected_request_mismatch"), ("other_timeout", "jaspar_transfer_policy_mismatch"),
    ("other_redirect_policy", "jaspar_transfer_policy_mismatch"), ("other_limit", "jaspar_transfer_policy_mismatch"),
])
def test_failed_transfer_or_selection_keeps_actual_source_without_data_delivery(host, mode, code):
    host.client.mode = mode
    snapshot = jaspar.request_jaspar(host.client, MATRIX)
    receipt, refs = publish(host, MATRIX, snapshot)
    source = host.store.get(receipt["source_ref"])
    assert receipt == {"acquired": False, "source_ref": source["id"], "data_ref": None, "failure_code": code}
    assert refs == [source["id"]] and source["accession"] is None
    assert source["uri"] == (snapshot.url if code in {"jaspar_selected_request_mismatch", "jaspar_transfer_policy_mismatch"}
        else snapshot.transport["request"]["url"])
    assert host.store.get_artifact(source["artifact_ref"]) == snapshot.content
    assert len(host.client.calls) == 1


def test_byte_limit_retains_a_real_prefix_and_no_response_creates_no_source(host):
    arguments = {**MATRIX, "max_bytes": 13}
    snapshot = jaspar.request_jaspar(host.client, arguments)
    receipt, refs = publish(host, arguments, snapshot)
    assert snapshot.content == MATRIX_BYTES[:13] and snapshot.transport["observed_body_bytes"] == 14
    assert receipt["acquired"] is False and receipt["failure_code"] == "jaspar_capture_incomplete"
    assert refs == [receipt["source_ref"]]
    before = host.store.count("source")
    with pytest.raises(AcquisitionError, match="^provider_connection_failed$"):
        jaspar.request_jaspar(Responses(mode="no_response"), MATRIX)
    assert host.store.count("source") == before


@pytest.mark.parametrize("arguments,raw,code", [
    (MATRIX, MATRIX_BYTES.replace(b'PB0001.1', b'PB0001.2'), "jaspar_matrix_identity_conflict"),
    (MATRIX, MATRIX_BYTES.replace(b'"base_id":"PB0001"', b'"base_id":"OTHER"'), "jaspar_matrix_identity_conflict"),
    (MATRIX, MATRIX_BYTES.replace(b'"version":1', b'"version":true'), "jaspar_matrix_identity_conflict"),
    (MATRIX, b'{"pfm":{}}', "jaspar_matrix_identity_missing"),
    (MATRIX, MATRIX_BYTES.replace(b'"version":1', b'"version":1,"version":1'), "jaspar_native_representation_invalid"),
    (MATRIX, MATRIX_BYTES.replace(b'1e-9999', b'NaN'), "jaspar_native_representation_invalid"),
    (MATRIX, MATRIX_BYTES.replace(b'3.50', b'true'), "jaspar_native_representation_invalid"),
    (MATRIX, MATRIX_BYTES.replace(b'3.50', b'-3.50'), "jaspar_native_representation_invalid"),
    (MATRIX, MATRIX_BYTES.replace(b'[4,0]', b'[4]'), "jaspar_native_representation_invalid"),
    (PFM, PFM_BYTES.replace(b'PB0001.1', b'PB0001.2'), "jaspar_matrix_identity_conflict"),
    (PFM, PFM_BYTES.replace(b'2 0', b'A [2 0]'), "jaspar_native_representation_invalid"),
    (PFM, PFM_BYTES.replace(b'1e-9999', b'Infinity'), "jaspar_native_representation_invalid"),
    (PFM, PFM_BYTES.rsplit(b'4 0', 1)[0], "jaspar_native_representation_invalid"),
    (DISCOVER, PAGE.replace(b'"count":23', b'"count":true'), "jaspar_discovery_page_invalid"),
    (DISCOVER, b'{"detail":"native error"}', "jaspar_discovery_page_invalid"),
])
def test_wrong_identity_or_representation_is_retained_without_guessing_or_normalizing(host, arguments, raw, code):
    host.client.raw = raw
    receipt, refs = publish(host, arguments, jaspar.request_jaspar(host.client, arguments))
    source = host.store.get(receipt["source_ref"])
    assert receipt["failure_code"] == code and receipt["acquired"] is False and receipt["data_ref"] is None
    assert refs == [source["id"]] and host.store.get_artifact(source["artifact_ref"]) == raw


def test_unexpected_late_confirmation_error_still_retains_its_real_source(host, monkeypatch):
    snapshot = jaspar.request_jaspar(host.client, MATRIX)
    def broken(*args):
        raise RuntimeError("engineered late confirmation error")
    monkeypatch.setattr(jaspar, "_representation_failure", broken)
    published = []
    with pytest.raises(RuntimeError, match="engineered late"):
        # Keep the existing publication owner's transaction, as ToolRegistry's
        # inner partial-failure handler does, rather than roll back this prefix.
        token = host.tools._publications.set(published)
        try:
            jaspar.publish_jaspar_request(host.tools, MATRIX, snapshot)
        finally:
            host.tools._publications.reset(token)
    source, = [host.store.get(reference) for reference in published
        if host.store.get(reference).get("record_type") == "source"
        and host.store.get(reference).get("provider") == jaspar.TOOL]
    assert source["accession"] is None and host.store.get_artifact(source["artifact_ref"]) == MATRIX_BYTES


def test_publisher_rejects_a_source_callback_claiming_another_data_identity(host, monkeypatch):
    original_source = host.tools._source
    def wrong_identity(*args, **kwargs):
        return {**original_source(*args, **kwargs), "artifact_ref": "artifact_" + "f" * 64}
    monkeypatch.setattr(host.tools, "_source", wrong_identity)
    snapshot = jaspar.request_jaspar(host.client, MATRIX)
    with pytest.raises(ContractError, match="^jaspar_capture_identity_mismatch$"):
        publish(host, MATRIX, snapshot)


@pytest.mark.parametrize("changes", [
    {"acquired": 1}, {"source_ref": None}, {"data_ref": None}, {"failure_code": "jaspar_http_not_successful"},
    {"source_ref": "source_bad"}, {"data_ref": "artifact_bad"}, {"extra": 0},
    {"acquired": False, "failure_code": "jaspar_http_not_successful"},
    {"acquired": False, "data_ref": None, "failure_code": None},
    {"acquired": False, "data_ref": None, "failure_code": "uncontrolled prose"},
])
def test_one_receipt_authority_rejects_cross_field_and_reference_shape_conflicts(changes):
    receipt = {"acquired": True, "source_ref": "source_" + "a" * 24,
        "data_ref": "artifact_" + "b" * 64, "failure_code": None, **changes}
    with pytest.raises(ContractError, match="^jaspar_receipt_invalid$"):
        jaspar.validate_jaspar_receipt(receipt)


def test_contract_and_closed_receipt_schema_are_detached_and_have_no_analysis_fact_source():
    contract = jaspar.jaspar_tool_contract()
    assert contract["name"] == jaspar.TOOL and contract["resources"] == "api"
    contract["input_schema"].clear()
    assert jaspar.jaspar_tool_contract()["input_schema"] == jaspar.ARGUMENTS_SCHEMA
    schema = jaspar.jaspar_receipt_schema()
    assert validate_closed_schema(schema) == schema and "x-source" not in json.dumps(schema)
    failure = {"acquired": False, "source_ref": None, "data_ref": None, "failure_code": "provider_connection_failed"}
    assert jaspar.validate_jaspar_receipt(failure) == validate_form(failure, schema, forbidden)


@pytest.mark.parametrize("arguments,raw", [
    (PFM, PFM_BYTES), ({**DISCOVER, "page": 2, "version_mode": "latest"}, PAGE),
])
def test_shared_http_performs_one_bounded_get_and_keeps_native_tokens(host, monkeypatch, arguments, raw):
    calls = []
    spec = jaspar.jaspar_request_spec(arguments)
    headers = Message(); headers["Content-Type"] = spec["media_type"]; headers["Content-Length"] = str(len(raw))
    class Response(io.BytesIO):
        status = 200
        def __init__(self):
            super().__init__(raw); self.headers = headers
        def geturl(self):
            return calls[0][0].full_url
    class Opener:
        def open(self, request, *, timeout):
            calls.append((request, timeout)); return Response()
    monkeypatch.setattr("urllib.request.build_opener", lambda *handlers: Opener())
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    client = PublicClients(ncbi_email=None, timeout=3)
    host.tools.clients = client
    snapshot = jaspar.request_jaspar(client, arguments)
    receipt, refs = publish(host, arguments, snapshot)
    assert len(calls) == 1 and calls[0][1] == 3 and calls[0][0].get_method() == "GET"
    assert calls[0][0].full_url == spec["url"] + "?" + urlencode(spec["params"])
    assert calls[0][0].get_header("Accept") == spec["accept"]
    assert snapshot.url == spec["url"] and snapshot.url != calls[0][0].full_url
    source = host.store.get(receipt["source_ref"])
    assert source["uri"] == calls[0][0].full_url
    assert snapshot.transport["request_policy"] == {"timeout_seconds": 3, "automatic_redirects": False}
    assert snapshot.transport["body_complete"] is True and snapshot.transport["response_byte_limit"] == arguments["max_bytes"]
    assert host.store.get_artifact(receipt["data_ref"]) == raw and refs == [receipt["source_ref"], receipt["data_ref"]]


def test_real_shared_redirect_handler_does_not_follow_the_location(host, monkeypatch):
    calls, raw = [], b"actual engineered redirect response\n"
    headers = Message(); headers["Location"] = "https://example.invalid/unselected"
    headers["Content-Type"] = "text/plain"; headers["Content-Length"] = str(len(raw))
    class SelectedHTTPS(urllib.request.HTTPSHandler):
        def https_open(self, request):
            calls.append(request.full_url)
            response = addinfourl(io.BytesIO(raw), headers, request.full_url, 302)
            response.msg = "Found"
            return response
    build_opener = urllib.request.build_opener
    monkeypatch.setattr("urllib.request.build_opener", lambda *handlers: build_opener(SelectedHTTPS(), *handlers))
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    client = PublicClients(ncbi_email=None, timeout=3)
    host.tools.clients = client
    snapshot = jaspar.request_jaspar(client, MATRIX)
    receipt, refs = publish(host, MATRIX, snapshot)
    assert calls == [jaspar.ROOT + "PB0001.1/?format=json"]
    assert snapshot.transport["status"] == 302 and snapshot.content == raw
    assert snapshot.transport["request_policy"]["automatic_redirects"] is False
    assert receipt["acquired"] is False and receipt["failure_code"] == "jaspar_http_not_successful"
    assert refs == [receipt["source_ref"]]
    assert host.store.get_artifact(host.store.get(receipt["source_ref"])["artifact_ref"]) == raw


@pytest.mark.parametrize("successful", [True, False])
def test_ordinary_registry_receipt_and_current_caller_permissions_without_child_or_analysis(host, tmp_path, monkeypatch, successful):
    # Requires the finite shared ToolRegistry/privacy/receipt wiring. No
    # special acquisition episode, typed fact source or model is introduced.
    if not successful:
        host.client.mode = "http_error"
    class NoModel:
        complete = staticmethod(forbidden)
        release = staticmethod(forbidden)
    def neutral(*args, **kwargs):
        return 0
    workflow = Workflow(host.store, host.tools, NoModel(), tmp_path / "run", "ordinary-jaspar",
        forbidden, neutral, root_role="improvement", episode_binding_factories=(),
        episode_record_receipts=True, initial_known_record_refs=[])
    caller = workflow.build("improvement", "existing-caller", "Retrieve the explicitly selected data for future analysis", host.scope)
    baseline = set(workflow.receipts.known(caller.source.episode_id))
    selection = {"kind": "tool", "tool": jaspar.TOOL, "arguments": deepcopy(MATRIX)}
    asyncio.run(caller.source.execute(selection, 0))
    outcome = deepcopy(caller.source.last_outcome)
    receipt = jaspar.validate_jaspar_receipt(outcome["result"])
    assert receipt["acquired"] is successful and outcome["status"] == ("completed" if successful else "partial")
    source = host.store.get(receipt["source_ref"])
    refs = [source["id"], source["artifact_ref"]] if successful else [source["id"]]
    assert outcome["record_refs"] == refs
    assert set(workflow.receipts.known(caller.source.episode_id)) == baseline | set(refs)
    resolver = workflow.resolver(host.scope, source=caller.source)
    assert resolver(source["id"], "source") is True
    assert resolver(source["artifact_ref"], "artifact") is successful
    assert resolver(source["request_ref"], "artifact") is False
    assert validate_form(receipt, jaspar.jaspar_receipt_schema(), resolver) == receipt
    assert source["version"] is None and caller.request.report_contract is None
    assert host.store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
    assert host.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 1
    for table in ("runtime_model_calls", "runtime_observations", "runtime_forms", "runtime_report_attempts"):
        assert host.store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
    before = {table: [tuple(row) for row in host.store.db.execute("SELECT * FROM " + table)]
        for table in ("records", "artifacts", "tool_operations", "runtime_actions", "runtime_record_receipts")}
    monkeypatch.setattr(host.client, "_http", forbidden)
    asyncio.run(caller.source.execute(selection, 0))
    assert caller.source.last_outcome == outcome and len(host.client.calls) == 1
    assert {table: [tuple(row) for row in host.store.db.execute("SELECT * FROM " + table)] for table in before} == before
    assert not (tmp_path / "run" / "api-service-execution").exists()


# Explicitly gated actual-service acquisition. These appended units are not
# covered by the original engineering snapshot or its execution results.
import os
from pathlib import Path
import re

from gene_annotation_episode.domain import identity
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.materials import artifact_path
from test_molecular_acquisition_ordinary import _live_audit, _live_pin, _live_write, _snapshot


LIVE_JASPAR_ARGUMENTS = (
    {"operation": "discover", "filters": {"name": "ABF1"}, "version_mode": "provider_default",
        "page": 1, "page_size": 10, "max_bytes": 8388608},
    {"operation": "matrix", "matrix_id": "MA0265.1", "representation": "json", "max_bytes": 8388608},
    {"operation": "matrix", "matrix_id": "MA0265.1", "representation": "pfm", "max_bytes": 8388608},
)
LIVE_JASPAR_PROOF = "JASPAR_ACQUISITION_PREFIX.json"


def _jaspar_live_gate(tmp_path):
    attempt = os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ACQUISITION_ATTEMPT", "")
    bounded = os.environ.get("HMMER529_ATTEMPT", "")
    if os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_JASPAR_LIVE") != "1" or not attempt or not bounded:
        pytest.skip("requires explicit live JASPAR getter selection and unique bounded acquisition attempt")
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", attempt), "select a unique explicit attempt ID"
    assert tmp_path.resolve().is_relative_to(Path(bounded).resolve(strict=True))
    return attempt, bounded


def _jaspar_live_capture(snapshot, root, action, proof, prefix):
    """Persist the actual returned/error entity before its Source publisher."""
    assert isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes
    path = root / ("original-http-body-" + str(action["decision_index"]) + ".bin")
    with path.open("xb") as handle:
        handle.write(snapshot.content)
        handle.flush()
        os.fsync(handle.fileno())
    action["http_capture"] = {"service": snapshot.service, "url": snapshot.url,
        "request": deepcopy(snapshot.request), "retrieved_at": snapshot.retrieved_at,
        "media_type": snapshot.media_type, "transport": deepcopy(snapshot.transport), "body_file": _live_pin(path)}
    _live_write(prefix, proof)


def _jaspar_live_verify_action(store, workflow, caller, action):
    """Check literal acquisition/custody, without scoring or transforming data."""
    index, arguments = action["decision_index"], action["arguments"]
    row = workflow.journal.row("runtime_actions", caller.source.episode_id, index)
    assert row is not None and json.loads(row["action"]) == action["selection"] and row["result"] is not None
    outcome = json.loads(row["result"])
    action["runtime_action"], action["outcome"] = dict(row), deepcopy(outcome)
    receipt = jaspar.validate_jaspar_receipt(outcome["result"])
    operation = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (action["operation_key"],)).fetchone()
    assert operation is not None and operation["name"] == jaspar.TOOL
    assert operation["id"] == identity("operation", {"key": action["operation_key"], "name": jaspar.TOOL, "arguments": arguments})
    assert operation["arguments"] == canonical(arguments) and operation["scope"] == canonical(caller.source.scope)
    assert json.loads(operation["result"]) == {key: value for key, value in outcome.items() if key != "pending_work_after_action"}
    action["tool_operation"] = dict(operation)
    resolver = workflow.resolver(caller.source.scope, source=caller.source)
    assert validate_form(receipt, jaspar.jaspar_receipt_schema(), resolver) == receipt
    known = set(workflow.receipts.known(caller.source.episode_id))
    assert known == set(action["known_before"]) | set(outcome["record_refs"])
    action["known_after"] = sorted(known)
    action["acquired"] = receipt["acquired"]
    action["receipt_verified"] = True
    diagnostic = (outcome.get("feedback") or {}).get("diagnostic_ref")
    if diagnostic is not None:
        assert diagnostic not in known and resolver(diagnostic, "artifact") is False
    if receipt["source_ref"] is None:
        assert receipt["acquired"] is False and receipt["data_ref"] is None
        assert outcome["record_refs"] == [] and action["http_capture"] is None
        return
    source = store.get(receipt["source_ref"])
    capture = action["http_capture"]
    assert capture is not None
    raw_pin = capture["body_file"]
    assert 0 <= raw_pin["size_bytes"] <= arguments["max_bytes"]
    assert source["provider"] == jaspar.TOOL and source["origin"] == "external" and source["version"] is None
    assert source["uri"] == action["selected_wire_uri"] == capture["transport"]["request"]["url"]
    assert source["retrieved_at"] == capture["retrieved_at"]
    assert source["accession"] == (arguments["matrix_id"] if receipt["acquired"] and arguments["operation"] == "matrix" else None)
    artifact = store.get(source["artifact_ref"])
    assert artifact["record_type"] == "artifact" and source["artifact_ref"] == "artifact_" + raw_pin["sha256"]
    assert artifact["sha256"] == raw_pin["sha256"] and artifact["size"] == raw_pin["size_bytes"]
    raw = Path(raw_pin["path"]).read_bytes()
    assert store.get_artifact(source["artifact_ref"]) == raw
    controls = json.loads(store.get_artifact(source["request_ref"]))
    assert canonical(controls) == canonical({"request": {"version": jaspar.REQUEST_VERSION,
        "arguments": arguments, "native_request": capture["request"]}, "transport": capture["transport"]})
    assert source["request_ref"] not in known and resolver(source["request_ref"], "artifact") is False
    with pytest.raises(ContractError):
        artifact_path(store, source["request_ref"])
    assert set(source.get("auxiliary_artifact_refs", ())).isdisjoint(known)
    expected = [source["id"], source["artifact_ref"]] if receipt["acquired"] else [source["id"]]
    assert outcome["record_refs"] == expected and resolver(source["id"], "source") is True
    independent_file = source["artifact_ref"] in set(action["known_before"])
    assert resolver(source["artifact_ref"], "artifact") is (receipt["acquired"] or independent_file)
    action["source"], action["source_control"] = source, controls
    action["raw_identity_verified"] = action["private_controls_denied"] = True
    if not receipt["acquired"]:
        assert outcome["status"] == "partial" and receipt["data_ref"] is None
        return
    transport = capture["transport"]
    assert outcome["status"] == "completed" and receipt["data_ref"] == source["artifact_ref"]
    assert transport["status"] == 200 and transport["body_complete"] is True
    assert transport["request_policy"] == {"timeout_seconds": 90, "automatic_redirects": False}
    assert transport["response_byte_limit"] == arguments["max_bytes"]
    assert transport["observed_body_bytes"] == transport["retained_body_bytes"] == len(raw)
    if arguments["operation"] == "discover":
        document = json.loads(raw)
        # Preserve native ordering and repetitions. No row selects either of
        # the independently predeclared exact matrix requests below.
        action["native_page_metadata"] = {"count": document["count"], "next": document["next"],
            "previous": document["previous"], "ordered_matrix_ids": [value["matrix_id"] for value in document["results"]]}
    elif arguments["representation"] == "json":
        document = json.loads(raw)
        assert document["matrix_id"] == arguments["matrix_id"] == "MA0265.1"
        action["native_matrix_identity"] = {key: document.get(key) for key in ("matrix_id", "base_id", "version")}
    else:
        assert raw.decode("utf-8").splitlines()[0][1:].split(None, 1)[0] == arguments["matrix_id"] == "MA0265.1"
        action["native_matrix_identity"] = {"matrix_id": arguments["matrix_id"], "representation": "pfm"}
    action["native_identity_verified"] = True


def test_live_preselected_jaspar_page_and_exact_matrix_files(tmp_path, monkeypatch):
    attempt, bounded = _jaspar_live_gate(tmp_path)
    prefix, store_directory = tmp_path / LIVE_JASPAR_PROOF, tmp_path / "store"
    proof = {"version": "ordinary_jaspar_acquisition_live_proof_v1", "attempt": attempt, "bounded_attempt": bounded,
        "tool": jaspar.TOOL, "run_id": "ordinary-live-jaspar-" + attempt,
        "store_directory": str(store_directory), "workflow_directory": str(tmp_path / "run"),
        "selection_basis": "MA0265.1 was preselected from official JASPAR API documentation before any acquisition",
        "official_matrix_url": "https://jaspar.elixir.no/api/v1/matrix/MA0265.1/",
        "qualification": "Three ordinary acquisitions before controller observation; no all-pages, release, site-scoring or biological analysis claim",
        "actions": [], "passed": False, "all_selected_acquisitions_obtained": False,
        "same_action_replay_no_http_verified": False, "ordinary_episode_boundary_verified": False}
    for index, arguments in enumerate(deepcopy(LIVE_JASPAR_ARGUMENTS)):
        spec = jaspar.jaspar_request_spec(arguments)
        proof["actions"].append({"decision_index": index, "arguments": arguments, "request_spec": spec,
            "selected_wire_uri": spec["url"] + "?" + urlencode(spec["params"]),
            "selection": {"kind": "tool", "tool": jaspar.TOOL, "arguments": arguments},
            "http_calls": [], "http_capture": None, "action_returned": False, "receipt_verified": False,
            "acquired": False, "raw_identity_verified": False, "private_controls_denied": False,
            "native_identity_verified": False})
    _live_write(prefix, proof, exclusive=True)
    original_http, active = PublicClients._http, {"index": None}
    def observed_http(client, service, url, params, media_type, **options):
        index = active["index"]
        assert type(index) is int and 0 <= index < len(proof["actions"])
        action = proof["actions"][index]
        assert action["http_calls"] == [], "no retry, automatic page or follow-up request was selected"
        selected = {"service": service, "url": url, "params": deepcopy(params), "media_type": media_type, **options}
        assert selected == {**action["request_spec"], "timeout_seconds": 90}
        action["http_calls"].append({"started": True, **selected})
        _live_write(prefix, proof)
        try:
            snapshot = original_http(client, service, url, params, media_type, **options)
        except AcquisitionError as error:
            action["http_calls"][0]["failure"] = {"code": error.code, "phase": error.phase}
            if error.snapshot is not None:
                _jaspar_live_capture(error.snapshot, tmp_path, action, proof, prefix)
            _live_write(prefix, proof)
            raise
        except BaseException as error:
            action["http_calls"][0]["failure"] = {"exception_type": type(error).__name__, "message": str(error)}
            _live_write(prefix, proof)
            raise
        _jaspar_live_capture(snapshot, tmp_path, action, proof, prefix)
        return snapshot
    class NoModel:
        complete = staticmethod(forbidden)
        release = staticmethod(forbidden)
    def neutral(*args, **kwargs):
        return 0
    try:
        with Store(store_directory) as store:
            subject, = store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]
            scope = {"subject_refs": [subject]}
            tools = ToolRegistry(store, clients=PublicClients(ncbi_email=None, timeout=90))
            workflow = Workflow(store, tools, NoModel(), tmp_path / "run", proof["run_id"], forbidden, neutral,
                root_role="improvement", episode_binding_factories=(), episode_record_receipts=True, initial_known_record_refs=[])
            caller = workflow.build("improvement", "existing-caller", "Retrieve the explicitly selected data for future analysis", scope)
            proof.update(episode_id=caller.source.episode_id, scope=scope,
                known_before=sorted(workflow.receipts.known(caller.source.episode_id)),
                tool_info=deepcopy(tools.catalog(scope)[jaspar.TOOL]))
            for action in proof["actions"]:
                action["operation_key"] = f"{workflow.run_id}:{caller.source.episode_id}:{action['decision_index']}"
            _live_write(prefix, proof)
            try:
                with monkeypatch.context() as live:
                    live.setattr(PublicClients, "_http", observed_http)
                    live.setattr("urllib.request.urlopen", forbidden)
                    live.setattr("subprocess.Popen", forbidden)
                    live.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
                    live.setattr("gene_annotation_episode.native_lifecycle.resume_start", forbidden)
                    live.setattr(ToolRegistry, "_sequence_worker_async", forbidden)
                    for action in proof["actions"]:
                        active["index"] = action["decision_index"]
                        action["known_before"] = sorted(workflow.receipts.known(caller.source.episode_id))
                        _live_write(prefix, proof)
                        try:
                            asyncio.run(caller.source.execute(action["selection"], action["decision_index"]))
                            action["action_returned"] = True
                            _jaspar_live_verify_action(store, workflow, caller, action)
                        finally:
                            _live_audit(store, workflow, caller, proof)
                            _live_write(prefix, proof)
                    active["index"] = None
                    assert all(len(action["http_calls"]) == 1 for action in proof["actions"])
                    proof["all_selected_acquisitions_obtained"] = all(action["acquired"] for action in proof["actions"])
                    _live_write(prefix, proof)
                    assert proof["all_selected_acquisitions_obtained"], [action["outcome"]["result"] for action in proof["actions"]]
                    before = _snapshot(store)
                    live.setattr(PublicClients, "_http", forbidden)
                    for action in proof["actions"]:
                        asyncio.run(caller.source.execute(action["selection"], action["decision_index"]))
                        assert caller.source.last_outcome == action["outcome"]
                    assert _snapshot(store) == before
                    proof["same_action_replay_no_http_verified"] = True
                    assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
                    assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 3
                    assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 3
                    for table in ("runtime_model_calls", "runtime_observations", "runtime_forms", "runtime_report_attempts"):
                        assert store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
                    assert store.count("observation") == store.count("annotation") == 0
                    episode, = proof["journal"]["runtime_episodes"]
                    assert episode["state"] == "active" and episode["completion"] is episode["archive"] is None
                    assert caller.request.report_contract is None and workflow.episode_bindings.roles == ()
                    assert not (tmp_path / "run" / "api-service-execution").exists()
                    proof["ordinary_episode_boundary_verified"] = True
            finally:
                _live_audit(store, workflow, caller, proof)
                _live_write(prefix, proof)
    except BaseException as error:
        proof["test_failure"] = {"exception_type": type(error).__name__, "message": str(error)}
        raise
    finally:
        bundle = []
        for name in ("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm"):
            path = store_directory / name
            if path.is_file():
                row = _live_pin(path)
                bundle.append({"name": name, "sha256": row["sha256"], "size_bytes": row["size_bytes"]})
        proof["sqlite_files"] = bundle
        proof["sqlite_pins_sha256"] = hashlib.sha256(canonical(bundle).encode("utf-8")).hexdigest()
        proof["store_files"] = {str(path.relative_to(store_directory)): _live_pin(path)
            for path in sorted(store_directory.rglob("*")) if path.is_file()}
        _live_write(prefix, proof)
    proof["passed"] = True
    _live_write(prefix, proof)
