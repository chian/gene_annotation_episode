"""Ordinary UCSC host publication with engineered, socket-free HTTP captures.

The real PublicClients transport, ToolRegistry dispatch, Source importer,
Store reference validation and operation replay own every positive result.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from email.message import Message
import hashlib
import io
import json
import urllib.error
import urllib.request
from urllib.parse import urlencode

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode import ucsc_acquisition as ucsc
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, canonical, identity
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.ucsc_acquisition import (
    ARGUMENTS_SCHEMA, OPERATIONS, ORIGIN, TOOL, ucsc_request_spec,
    ucsc_sequence_interval, validate_ucsc_result,
)
from test_molecular_provider_acquisition_host import _artifacts, _tables, forbidden
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_runtime import action


HUB = "https://example.org/native/hub.txt?literal=one&other=two"
CASES = [
    {"operation": "ucsc_genomes"},
    {"operation": "genark_genomes", "genome": None, "max_items_output": 2},
    {"operation": "public_hubs"},
    {"operation": "hub_genomes", "hub_url": HUB},
    {"operation": "tracks", "genome": "hg38", "hub_url": None, "track_leaves_only": False},
    {"operation": "chromosomes", "genome": "hg38", "hub_url": None, "track": None},
    {"operation": "schema", "genome": "hg38", "hub_url": None, "track": "genes"},
    {"operation": "track", "genome": "hg38", "hub_url": None, "track": "genes", "chrom": "chr1",
        "start": 10, "end": 20, "max_items_output": 2, "json_output_arrays": False},
    {"operation": "sequence", "genome": "hg38", "hub_url": None, "chrom": "chr1",
        "start": 10, "end": 14, "rev_comp": False},
]


def arguments(selected_operation="ucsc_genomes", **changes):
    selected = next(deepcopy(row) for row in CASES if row["operation"] == selected_operation)
    return {**selected, "max_bytes": 16_384, **changes}


def payload(selected_operation):
    return deepcopy({
        "ucsc_genomes": {"ucscGenomes": {"hg38": {"description": "Engineered assembly", "extra": [None, False, 0]}}},
        "genark_genomes": {"genarkGenomes": {"GCF_000001405.40": {"hubUrl": "GCF/native/hub.txt"}},
            "hubUrlPrefix": "https://example.org/hubs", "itemsReturned": 1, "totalAssemblies": 700_000},
        "public_hubs": {"publicHubs": [{"hubUrl": HUB, "extra": {"native": True}}]},
        "hub_genomes": {"hubUrl": HUB, "genomes": {"nativeAssembly": {"twoBitPath": "https://example.org/native.2bit"}}},
        "tracks": {"hg38": {"container": {"genes": {"type": "genePred", "parent": "container"}}}},
        "chromosomes": {"genome": "hg38", "chromCount": 1, "chromosomes": {"chr1": 1000}},
        "schema": {"genome": "hg38", "track": "genes", "type": "genePred", "itemCount": 100,
            "columnTypes": [{"name": "txStart", "sqlType": "int", "jsonType": "number"}]},
        "track": {"genome": "hg38", "track": "genes", "chrom": "chr1", "start": 10, "end": 20,
            "itemsReturned": 1, "genes": [{"txStart": 5, "txEnd": 22, "strand": "-", "native": [False, None, 0]}]},
        "sequence": {"genome": "hg38", "chrom": "chr1", "start": 10, "end": 14, "dna": "AcgN"},
    }[selected_operation])


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


class _Response(io.BytesIO):
    def __init__(self, body, status, headers, address):
        super().__init__(body)
        self.status, self.headers, self.address = status, headers, address

    def geturl(self):
        return self.address


class _HTTP:
    """Supply actual transport input bytes; no socket or publisher is replaced."""
    def __init__(self):
        self.planned, self.requests = [], []

    def add(self, body, *, status=200, headers=None):
        self.planned.append((body, status, dict(headers or {})))

    def open(self, request, timeout):
        self.requests.append({"url": request.full_url, "method": request.get_method(),
            "headers": dict(request.header_items()), "timeout": timeout})
        assert self.planned, "unexpected additional provider request"
        body, status, selected_headers = self.planned.pop(0)
        if isinstance(body, Exception):
            raise body
        headers = Message()
        for name, value in {"Content-Type": "application/json; charset=utf-8",
                "Content-Length": str(len(body)), **selected_headers}.items():
            headers[name] = value
        if not 200 <= status < 300:
            raise urllib.error.HTTPError(request.full_url, status, "Engineered native status",
                headers, io.BytesIO(body))
        return _Response(body, status, headers, request.full_url)


@pytest.fixture
def http(monkeypatch):
    selected = _HTTP()
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_handlers: selected)
    def unexpected_redirect_transport(*_args, **_kwargs):
        raise AssertionError("automatic redirect-capable transport was selected")
    monkeypatch.setattr(urllib.request, "urlopen", unexpected_redirect_transport)
    return selected


def scope_and_tools(store):
    problem = store.create_problem(raw_sequence="ACGTACGT", molecule="dna")
    return {"subject_refs": problem["subject_refs"]}, ToolRegistry(store, clients=PublicClients(timeout=3))


def run(tools, selected, scope, key):
    return asyncio.run(tools.execute_async(TOOL, selected, scope=scope, operation_key=key))


def source_for(store, outcome):
    sources = [store.get(ref) for ref in outcome["record_refs"] if store.get(ref)["record_type"] == "source"]
    assert len(sources) == 1
    return sources[0]


def references(store, outcome):
    """Inspect real Source-associated publication, without granting its operands."""
    source = source_for(store, outcome)
    return store.query_records("reference", references=[source["id"]])["records"]


def assert_custody(store, outcome, selected, body):
    receipt = ucsc.validate_ucsc_receipt(outcome["result"])
    source = source_for(store, outcome)
    assert source["id"] == receipt["source_ref"] and source["origin"] == "external"
    assert source["provider"] == "ucsc" and source["version"] is None and source["accession"] is None
    assert source["artifact_ref"] == "artifact_" + hashlib.sha256(body).hexdigest()
    assert store.get_artifact(source["artifact_ref"]) == body
    private_ref, = source["auxiliary_artifact_refs"]
    private = ucsc.validate_ucsc_value(json.loads(store.get_artifact(private_ref)))
    native = ucsc.ucsc_result_from_value(private, source_ref=source["id"])
    assert native["raw_artifact_ref"] == source["artifact_ref"] and "source_ref" not in private
    retained = json.loads(store.get_artifact(source["request_ref"]))
    assert retained["request"] == selected == native["requested"]
    spec = ucsc_request_spec(selected)
    expected_url = spec["url"] + ("?" + urlencode(spec["params"]) if spec["params"] else "")
    assert retained["transport"]["request"]["url"] == native["response"]["request_url"] == expected_url
    assert retained["transport"]["request_policy"] == {"timeout_seconds": 3, "automatic_redirects": False}
    assert source["uri"] == expected_url
    assert outcome["record_refs"] == [source["id"], *([source["artifact_ref"]] if receipt["acquired"] else [])]
    assert receipt["data_ref"] == (source["artifact_ref"] if receipt["acquired"] else None)
    assert source["request_ref"] not in outcome["record_refs"]
    assert private_ref not in outcome["record_refs"]
    assert native["population_coverage"] == "selected_response_only"
    return native, source


@pytest.mark.parametrize("selected_operation", OPERATIONS)
def test_all_nine_variants_use_one_real_ordinary_catalog_acquisition_and_source_owner(http, tmp_path, selected_operation):
    selected, body = arguments(selected_operation), encoded(payload(selected_operation))
    before = deepcopy(selected)
    http.add(body)
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        assert tools.catalog(scope)[TOOL]["input_schema"] == ARGUMENTS_SCHEMA
        assert [name for name in tools.catalog(scope) if name.startswith("public.ucsc.")] == [TOOL]
        outcome = run(tools, selected, scope, "ucsc:" + selected_operation)
        assert outcome["status"] == "completed"
        native, _ = assert_custody(store, outcome, selected, body)
        assert native["native_json"] == payload(selected_operation) and native["issues"] == []
        assert len(references(store, outcome)) == (1 if selected_operation == "sequence" else 0)
        assert selected == before and len(http.requests) == 1
        assert http.requests[0]["method"] == "GET" and http.requests[0]["timeout"] == 3
        assert http.planned == []


@pytest.mark.parametrize("failure", [False, True])
def test_client_binds_selected_arguments_and_fixed_processing_media_on_success_and_error(http, failure):
    selected = arguments("sequence")
    body = encoded(payload("sequence")) if not failure else b"<html>complete original denial</html>"
    http.add(body, status=403 if failure else 200, headers={"Content-Type": "text/html"})
    client = PublicClients(timeout=3)
    if failure:
        with pytest.raises(AcquisitionError) as caught:
            client.ucsc_request(arguments=selected)
        retained = caught.value.snapshot
        assert caught.value.code == "provider_http_403" and caught.value.phase == "http_response"
    else:
        retained = client.ucsc_request(arguments=selected)
    assert retained.content == body and retained.media_type == "application/json"
    assert retained.transport["headers"]["content-type"] == "text/html"
    assert retained.request == selected and retained.request is not selected
    selected["start"] = 0
    assert retained.request["start"] == 10 and len(http.requests) == 1


@pytest.mark.parametrize("changes", [{"max_bytes": True}, {"max_bytes": 8 * 1024 * 1024 + 1},
    {"endpoint": "https://example.org/unselected"}, {"operation": "unregistered"}])
def test_invalid_client_selection_never_reaches_transport(http, changes):
    with pytest.raises(ValueError):
        PublicClients(timeout=3).ucsc_request(arguments=arguments(**changes))
    assert http.requests == []


@pytest.mark.parametrize("status", [301, 403, 429, 500])
def test_http_failure_retains_complete_native_body_source_and_exact_retry_header(http, tmp_path, status):
    selected = arguments("track")
    body = encoded({"error": "Original native diagnostic", "statusCode": status,
        "statusMessage": "Engineered status wording", "unknown": {"native": [None, False, 0]}})
    http.add(body, status=status, headers={"Retry-After": "30", "Location": "https://example.org/must-not-follow"})
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        outcome = run(tools, selected, scope, "ucsc-http:" + str(status))
        assert outcome["status"] == "partial" and outcome["feedback"]["category"] == "acquisition"
        native, _ = assert_custody(store, outcome, selected, body)
        assert native["native_response_state"] == "error" and native["representation_state"] == "complete"
        assert native["response"]["http_status"] == status and native["response"]["body_complete"] is True
        assert native["response"]["retry_after"] == "30" and native["native_json"]["error"] == "Original native diagnostic"
        assert references(store, outcome) == [] and len(http.requests) == 1


def test_http_success_native_error_is_failed_without_erasing_its_valid_representation(http, tmp_path):
    selected = arguments("sequence")
    body = encoded({"error": "Native provider denial", "statusCode": 403, "statusMessage": "Forbidden"})
    http.add(body)
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        outcome = run(tools, selected, scope, "ucsc-native-error")
        assert outcome["status"] == "partial" and outcome["feedback"]["category"] == "acquisition"
        native, _ = assert_custody(store, outcome, selected, body)
        assert native["native_response_state"] == "error" and native["representation_state"] == "partial"
        assert native["response"]["http_status"] == 200
        assert {row["code"] for row in native["issues"]} == {"native_error_response", "native_status_conflict"}
        assert references(store, outcome) == []


def test_non_json_http_error_preserves_its_entire_original_source_and_observed_media(http, tmp_path):
    selected, body = arguments(), b"<html>Complete engineered denial: &amp; original bytes.</html>"
    http.add(body, status=403, headers={"Content-Type": "text/html"})
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        outcome = run(tools, selected, scope, "ucsc-html-error")
        assert outcome["status"] == "partial" and outcome["feedback"]["category"] == "acquisition"
        native, _ = assert_custody(store, outcome, selected, body)
        assert native["response"]["http_status"] == 403 and native["response"]["body_complete"] is True
        assert native["response"]["content_type"] == "text/html" and native["response"]["media_type"] == "application/json"
        assert native["parse_state"] == "decode_failed" and native["decode_error"] == "invalid_native_json"
        assert references(store, outcome) == [] and len(http.requests) == 1


@pytest.mark.parametrize("selected_operation,status", [("track", 206), ("genark_genomes", 200)])
def test_native_cap_is_a_successful_selected_response_with_separate_population_qualification(http, tmp_path, selected_operation, status):
    selected = arguments(selected_operation)
    native_payload = {**payload(selected_operation), "maxItemsLimit": True,
        "dataDownloadUrl": "https://example.org/unselected/full-data.gz"}
    body = encoded(native_payload)
    http.add(body, status=status)
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        outcome = run(tools, selected, scope, "ucsc-native-cap:" + selected_operation)
        assert outcome["status"] == "completed"
        native, _ = assert_custody(store, outcome, selected, body)
        assert native["response"]["http_status"] == status and native["response"]["body_complete"] is True
        assert native["native_item_cap"]["state"] == "reached" and native["representation_state"] == "complete"
        assert native["native_json"] == native_payload and len(http.requests) == 1
        if selected_operation == "genark_genomes":
            assert native["native_counts"]["totalAssemblies"]["meaning"] == "genark_registry_assemblies"
            assert native["native_counts"]["totalAssemblies"]["value"] == 700_000


@pytest.mark.parametrize("token", ["1e-9999", "9007199254740993"])
def test_duplicate_members_and_exact_number_tokens_survive_real_host_publication(http, tmp_path, token):
    selected = arguments("track")
    body = (b'{"genome":"hg38","track":"genes","chrom":"chr1","start":10,"end":20,'
        b'"sqlTable":"native_table","sqlTable":"alternate_native_table",'
        b'"itemsReturned":1,"genes":[{"value":0,"value":' + token.encode() + b'}]}')
    http.add(body)
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        outcome = run(tools, selected, scope, "ucsc-document:" + token)
        assert outcome["status"] == "completed"
        native, _ = assert_custody(store, outcome, selected, body)
        assert native["parse_state"] == "json_document" and native["native_json"] is None
        members = native["native_document"]["members"]
        assert [item["value"]["value"] for item in members if item["name"] == "sqlTable"] == [
            "native_table", "alternate_native_table"]
        row = next(item["value"] for item in members if item["name"] == "genes")["items"][0]
        assert [item["value"]["token"] for item in row["members"]] == ["0", token]
        assert native["representation_state"] == "complete" and references(store, outcome) == []


@pytest.mark.parametrize("capture", ["byte_limit", "short_body", "invalid_json", "content_type"])
def test_capture_and_representation_failures_retain_source_before_partial_delivery(http, tmp_path, capture):
    selected, body, headers = arguments("sequence"), encoded(payload("sequence")), {}
    if capture == "byte_limit":
        selected["max_bytes"] = len(body) - 1
    elif capture == "short_body":
        headers["Content-Length"] = str(len(body) + 5)
    elif capture == "invalid_json":
        body = b'{"genome":"hg38",'
    else:
        headers["Content-Type"] = "text/plain"
    http.add(body, headers=headers)
    retained = body[:selected["max_bytes"]]
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        outcome = run(tools, selected, scope, "ucsc-partial:" + capture)
        assert outcome["status"] == ("completed" if capture == "content_type" else "partial")
        assert ucsc.validate_ucsc_receipt(outcome["result"])["acquired"] is (capture == "content_type")
        native, _ = assert_custody(store, outcome, selected, retained)
        assert native["response"]["http_status"] == 200 and references(store, outcome) == []
        if capture in {"byte_limit", "short_body"}:
            assert native["response"]["body_complete"] is False
            assert native["response"]["capture_failure"] is not None
        elif capture == "invalid_json":
            assert native["response"]["body_complete"] is True and native["parse_state"] == "decode_failed"
        else:
            assert native["representation_state"] == "complete" and native["response"]["content_type"] == "text/plain"
        assert len(http.requests) == 1


@pytest.mark.parametrize("damage", ["selected", "selected_boolean", "transport_url", "method", "media_type"])
def test_unassociated_snapshot_keeps_its_original_source_and_never_publishes_dna_reference(http, tmp_path, monkeypatch, damage):
    selected, body = arguments("sequence"), encoded(payload("sequence"))
    http.add(body)
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        original = tools.clients.ucsc_request
        def damaged(*, arguments):
            retained = original(arguments=arguments)
            if damage in {"selected", "selected_boolean"}:
                return replace(retained, request={**retained.request, "start": True if damage == "selected_boolean" else 11})
            if damage == "media_type":
                return replace(retained, media_type="text/plain")
            transport = deepcopy(retained.transport)
            if damage == "method":
                transport["request"]["method"] = "POST"
            else:
                transport["request"]["url"] += "&unselected=1"
            return replace(retained, transport=transport)
        monkeypatch.setattr(tools.clients, "ucsc_request", damaged)
        outcome = run(tools, selected, scope, "ucsc-unassociated:" + damage)
        assert outcome["status"] == "partial" and references(store, outcome) == []
        source = source_for(store, outcome)
        assert store.get_artifact(source["artifact_ref"]) == body
        retained = json.loads(store.get_artifact(source["request_ref"]))
        assert retained["request"]["start"] == (True if damage == "selected_boolean" else 11 if damage == "selected" else 10)
        assert len(http.requests) == 1
        saved = store.db.execute("SELECT result FROM tool_operations WHERE operation_key=?", ("ucsc-unassociated:" + damage,)).fetchone()
        assert json.loads(saved[0]) == outcome


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("document", [False, True])
def test_optional_exact_dna_reference_has_only_its_returned_local_sequence_axis(http, tmp_path, reverse, document):
    selected = arguments("sequence", rev_comp=reverse)
    native_payload = payload("sequence")
    if reverse:
        native_payload.update(revComp=True, dna="NcGt")
    body = encoded(native_payload)
    if document:
        body = body[:-1] + b',"extra":0,"extra":1e-9999}'
    http.add(body)
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        before_targets = deepcopy(store.problem()["subject_refs"])
        outcome = run(tools, selected, scope, "ucsc-dna:" + str(reverse) + ":" + str(document))
        assert outcome["status"] == "completed"
        native, source = assert_custody(store, outcome, selected, body)
        interval = ucsc_sequence_interval(native)
        acquired = references(store, outcome)
        assert len(acquired) == 1
        reference = acquired[0]
        assert reference["source_ref"] == source["id"] and reference["origin"] == "external"
        assert reference["reference_type"] == reference["molecule"] == "dna" and reference["length"] == 4
        assert store.get_artifact(reference["sequence_ref"]) == native_payload["dna"].encode("ascii")
        assert reference["sequence_ref"] not in outcome["record_refs"]
        assert reference["id"] not in outcome["record_refs"]
        assert interval["start"] == 10 and interval["end"] == 14 and interval["rev_comp"] is reverse
        assert store.sequence_mapping(reference["id"])["path"] == [{"subject_ref": reference["id"],
            "start": 0, "end": 4, "unit": "nt", "strand": "+"}]
        assert store.subject_length(reference["id"]) == 4 and store.has_exact_mapping(reference["id"]) is True
        assert store.map_segments(reference["id"], [{"start": 0, "end": 4}]) == []
        assert store.coverage(reference["id"]) == [] and store.roots(reference["id"]) == []
        assert store.problem()["subject_refs"] == before_targets
        assert len(http.requests) == 1


@pytest.mark.parametrize("changes", [{"genome": "mm39"}, {"chrom": "chr2"}, {"start": 11},
    {"end": 15}, {"dna": "ACG"}, {"revComp": True}])
def test_unselected_native_sequence_context_stays_source_only(http, tmp_path, changes):
    selected = arguments("sequence")
    body = encoded({**payload("sequence"), **changes})
    http.add(body)
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        outcome = run(tools, selected, scope, "ucsc-sequence-mismatch:" + next(iter(changes)))
        assert outcome["status"] == "partial" and references(store, outcome) == []
        native, _ = assert_custody(store, outcome, selected, body)
        assert ucsc_sequence_interval(native) is None


def test_async_acquisition_dispatch_and_cached_operation_replay_use_exactly_one_http_capture(http, tmp_path, monkeypatch):
    selected, body = arguments("sequence"), encoded(payload("sequence"))
    http.add(body)
    dispatches, actual_to_thread = [], asyncio.to_thread
    async def dispatched(function, *args, **kwargs):
        dispatches.append((function.__name__, deepcopy(kwargs)))
        return await actual_to_thread(function, *args, **kwargs)
    monkeypatch.setattr(asyncio, "to_thread", dispatched)
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        outcome = run(tools, selected, scope, "ucsc-exact-replay")
        assert outcome["status"] == "completed"
        assert_custody(store, outcome, selected, body)
        assert dispatches == [("ucsc_request", {"arguments": selected})]
        monkeypatch.setattr(ucsc, "publish_ucsc_request", forbidden)
        monkeypatch.setattr(ucsc, "ucsc_value", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        assert run(tools, selected, scope, "ucsc-exact-replay") == outcome
        assert len(dispatches) == len(http.requests) == 1
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1
        assert len(references(store, outcome)) == 1


def test_no_response_connection_failure_uses_existing_diagnostic_and_cached_attempt(http, tmp_path):
    selected = arguments()
    http.add(urllib.error.URLError("Engineered connection failure"))
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        outcome = run(tools, selected, scope, "ucsc-connection-failure")
        assert outcome["status"] == "failed" and outcome["record_refs"] == []
        assert ucsc.validate_ucsc_receipt(outcome["result"]) == ucsc.failed_ucsc_receipt("data_acquisition_failed")
        assert outcome["feedback"]["code"] == "provider_connection_failed"
        diagnostic = json.loads(store.get_artifact(outcome["feedback"]["diagnostic_ref"]))
        assert diagnostic["representation"] == "local_exception"
        assert tools.retained_molecular_reference_access(None, outcome["feedback"]["diagnostic_ref"], "artifact") is False
        assert run(tools, selected, scope, "ucsc-connection-failure") == outcome
        assert len(http.requests) == 1 and store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1


def _current_controller(path, initial):
    return FixtureController(str(path), initial, 3)


def _one_controller(path, initial):
    return FixtureController(str(path), initial, 1)


def _current_credit(*args, **kwargs):
    return 0


def _current_workflow(store, tools, provider, directory, run_id):
    return Workflow(store, tools, provider, directory, run_id, _current_controller, _current_credit,
        project_child_credit=_current_credit, root_role="improvement", episode_record_receipts=True,
        initial_known_record_refs=[])


def _current_session(directory):
    role = dict(model="ucsc-presentation-engineering", reasoning_effort="low")
    return _SessionConnection(dict(connection={"command": ["unselected-model-command"]},
        FAST=role, REASONING=role, routing={}), directory, directory.parent)


class _CurrentProvider(ScriptedProvider):
    """Full actual DecisionSource calls; only the Session presentation port runs."""
    def __init__(self, script, session):
        super().__init__(script)
        self.session, self.dispatches = session, []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        wire, model_instructions = self.session._presentation(episode_id, role, instructions, context)
        self.dispatches.append(dict(episode_id=episode_id, context=deepcopy(context),
            instructions=instructions, schema=deepcopy(output_schema), wire=wire,
            model_instructions=model_instructions))
        return await super().complete(episode_id, role, instructions, context, output_schema)


def _native_publication_observer(tools, monkeypatch):
    """Observe the actual host creator's ID; never replace its result/records."""
    create, published = tools._publish_ucsc_sequence_reference, []
    def observe(result, source):
        reference = create(result, source)
        if reference is not None:
            published.append(reference)
        return reference
    monkeypatch.setattr(tools, "_publish_ucsc_sequence_reference", observe)
    return published


def _assert_private_controls(owner, tools, context, source):
    known = set(owner.receipts.known(context.episode_id))
    private = {source["request_ref"], *source.get("auxiliary_artifact_refs", [])}
    assert private.isdisjoint(known)
    resolve = owner.resolver(plain(context.scope), context=context)
    for reference in private:
        assert resolve(reference, "artifact") is False
        assert tools.retained_molecular_reference_access(context, reference, "artifact") is False


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("document", [False, True])
def test_current_episode_receipt_explicit_reference_admission_lost_reply_receiving_builder_and_closed_replay(
        http, tmp_path, monkeypatch, reverse, document):
    class LostReply(RuntimeError): pass
    selected, response = arguments("sequence", rev_comp=reverse), payload("sequence")
    if reverse: response.update(revComp=True, dna="NcGt")
    body = encoded(response)
    if document: body = body[:-1] + b',"extra":0,"extra":1e-9999}'
    http.add(body)
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        original_targets = deepcopy(store.problem()["subject_refs"])
        published = _native_publication_observer(tools, monkeypatch)
        directory, run_id = tmp_path / "run", "ucsc-current-episode-engineering"
        session = _current_session(tmp_path / "session")
        actor = _CurrentProvider([action(TOOL, selected)], session)
        current = _current_workflow(store, tools, actor, directory, run_id)
        goal = "Evaluate the supplied DNA using the caller-selected UCSC interval as reference evidence, without assigning function."
        root = current.build("improvement", "root", goal, scope)
        baseline = set(current.receipts.known(root.source.episode_id))
        original_execute, lost = ToolRegistry.execute_async, []
        async def lose_reply(registry, name, arguments, **kwargs):
            outcome = await original_execute(registry, name, arguments, **kwargs)
            if name == TOOL and not lost:
                assert outcome["status"] == "completed"
                lost.append(deepcopy(outcome)); raise LostReply()
            return outcome
        with monkeypatch.context() as patch:
            patch.setattr(ToolRegistry, "execute_async", lose_reply)
            with pytest.raises(LostReply): asyncio.run(root.run_async(current.context))
        assert len(http.requests) == len(actor.dispatches) == len(published) == 1
        assert store.db.execute("SELECT result FROM runtime_actions WHERE decision_index=0").fetchone()[0] is None
        result = ucsc.validate_ucsc_receipt(lost[0]["result"])
        native, source = assert_custody(store, lost[0], selected, body)
        reference_id, = published
        reference = store.get(reference_id)
        assert reference["source_ref"] == source["id"] and reference["sequence_ref"] != source["artifact_ref"]
        assert lost[0]["record_refs"] == [source["id"], source["artifact_ref"]]
        assert {reference_id, reference["sequence_ref"]}.isdisjoint(lost[0]["record_refs"])
        holder = {}
        def query_reference(context):
            owner, child = holder["owner"], holder["root"]
            binding = owner.binding_context(child.source)
            assert context["last_local_outcome"]["result"] == result
            assert set(owner.receipts.known(binding.episode_id)) == baseline | set(lost[0]["record_refs"])
            # The publication exists, but actual sequence-input admission must
            # still deny it before the separately selected metadata query.
            with monkeypatch.context() as patch:
                patch.setattr(Store, "get_artifact", forbidden)
                patch.setattr("gene_annotation_episode.molecular_sequence_input_bindings.retained_native_file", forbidden)
                denied = owner.services.read_received_molecular_input(binding, reference_id, "reference", subject_metadata_only=True)
                assert denied["input"] is None and denied["failure"]["code"] == "reference_not_received"
                denied_file, path = owner.services.read_received_molecular_input(binding, reference["sequence_ref"], "artifact", file_format="ascii_sequence")
                assert denied_file["input"] is None and denied_file["failure"]["code"] == "reference_not_received" and path is None
            _assert_private_controls(owner, tools, binding, source)
            return action("state.query", dict(kind="reference", references=[source["id"]], offset=0, limit=5))
        def inspect_explicit_reference(context):
            owner, child = holder["owner"], holder["root"]
            binding = owner.binding_context(child.source)
            rows = context["last_local_outcome"]["result"]["records"]
            assert {row["id"] for row in rows} == {reference_id}
            assert all(row["source_ref"] == source["id"] for row in rows)
            expected = baseline | {source["id"], source["artifact_ref"], reference_id, reference["sequence_ref"]}
            assert set(owner.receipts.known(binding.episode_id)) == expected
            admitted = owner.services.read_received_molecular_input(binding, reference_id, "reference", subject_metadata_only=True)
            assert admitted["failure"] is None and admitted["input"]["witness"]["record"] == reference
            admitted_file, path = owner.services.read_received_molecular_input(binding,
                reference["sequence_ref"], "artifact", file_format="ascii_sequence")
            assert admitted_file["failure"] is None and path.read_bytes() == response["dna"].encode("ascii")
            assert tools._sequence(reference_id) == response["dna"]
            assert store.sequence_mapping(reference_id)["path"] == [dict(subject_ref=reference_id,
                start=0, end=4, unit="nt", strand="+")]
            assert store.coverage(reference_id) == store.roots(reference_id) == []
            _assert_private_controls(owner, tools, binding, source)
            # Explicit ID selection after its real row was received, without
            # choosing a first row or performing sequence analysis.
            return action("state.query", {"refs": [reference_id]})
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(ucsc, "publish_ucsc_request", forbidden)
        monkeypatch.setattr(ucsc, "ucsc_value", forbidden)
        monkeypatch.setattr(tools, "_publish_ucsc_sequence_reference", forbidden)
        receiver = _CurrentProvider([query_reference, inspect_explicit_reference], session)
        recovered = _current_workflow(store, tools, receiver, directory, run_id)
        recovered_root = recovered.build("improvement", "root", goal, scope)
        holder.update(owner=recovered, root=recovered_root)
        record = asyncio.run(recovered_root.run_async(recovered.context))
        final = asyncio.run(recovered_root.build_result(record)).as_record()
        assert len(http.requests) == len(published) == 1
        dispatches = actor.dispatches + receiver.dispatches
        calls = list(store.db.execute("SELECT request,response FROM runtime_model_calls ORDER BY call_index"))
        assert len(dispatches) == len(calls) == 3
        for dispatched, saved in zip(dispatches, calls):
            assert json.loads(saved["request"])["context"] == dispatched["context"]
            assert json.loads(dispatched["wire"]) == dispatched["context"]
            assert dispatched["model_instructions"] == dispatched["instructions"] and saved["response"] is not None
            assert dispatched["context"]["goal"] == root.source.request.goal.as_record()
        assert dispatches[1]["context"]["last_local_outcome"]["result"] == result
        assert dispatches[2]["context"]["last_local_outcome"]["result"]["records"] == [reference]
        assert store.problem()["subject_refs"] == original_targets
        assert native["requested"] == selected and store.get_artifact(source["artifact_ref"]) == body
        counts = {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in (
            "runtime_episodes", "runtime_actions", "runtime_model_calls", "runtime_observations", "tool_operations")}
        assert counts == dict(runtime_episodes=1, runtime_actions=3, runtime_model_calls=3,
            runtime_observations=3, tool_operations=3)
        assert store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0
        before, artifacts, archives = _tables(store), _artifacts(store.path / "artifacts"), _artifacts(directory / "archive")
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
        replay_actor = ScriptedProvider([])
        replay = _current_workflow(store, tools, replay_actor, directory, run_id)
        replay_root = replay.build("improvement", "root", goal, scope)
        replay_record = asyncio.run(replay_root.run_async(replay.context))
        assert asyncio.run(replay_root.build_result(replay_record)).as_record() == final
        assert replay_actor.contexts == [] and _tables(store) == before
        assert _artifacts(store.path / "artifacts") == artifacts and _artifacts(directory / "archive") == archives


def test_current_ucsc_legacy_import_and_cache_keep_rich_dto_and_original_reference_refs(http, tmp_path, monkeypatch):
    selected = arguments("sequence")
    http.add(encoded(payload("sequence")))
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        capture = tools.clients.ucsc_request(arguments=selected)
        key = "engineered-original-ucsc-import"
        token = tools._publications.set([])
        try:
            with store.transaction():
                result, refs = tools._import(TOOL, selected, capture)
                outcome = dict(status="completed", operation_ref=identity("operation", dict(key=key,
                    name=TOOL, arguments=selected)), record_refs=refs, changed_record_refs=refs,
                    result=result, feedback=None)
                tools._save(key, TOOL, selected, scope, outcome)
        finally: tools._publications.reset(token)
        assert validate_ucsc_result(result) == result and result["version"] == "ucsc_acquisition_result_v1"
        source = store.get(result["source_ref"])
        assert not source.get("auxiliary_artifact_refs") and len(refs) == 2
        assert [store.get(ref)["record_type"] for ref in refs] == ["source", "reference"]
        before, files = _tables(store), _artifacts(store.path / "artifacts")
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(ucsc, "ucsc_result", forbidden)
        monkeypatch.setattr(ucsc, "ucsc_value", forbidden)
        monkeypatch.setattr(ucsc, "publish_ucsc_request", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        assert run(tools, selected, scope, key) == outcome
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files


@pytest.mark.parametrize("operation", ["sequence", "track"])
def test_unreceived_current_context_cannot_use_ucsc_source_raw_file_or_private_controls_before_bytes(
        http, tmp_path, monkeypatch, operation):
    selected = arguments(operation)
    http.add(encoded(payload(operation)))
    with Store(tmp_path / "store") as store:
        scope, tools = scope_and_tools(store)
        owner = Workflow(store, tools, ScriptedProvider([action(TOOL, selected)]), tmp_path / "owner",
            "ucsc-owner-engineering", _one_controller, _current_credit, project_child_credit=_current_credit,
            root_role="improvement", episode_record_receipts=True, initial_known_record_refs=[])
        root = owner.build("improvement", "root", "Evaluate supplied DNA using caller-selected UCSC evidence.", scope)
        record = asyncio.run(root.run_async(owner.context)); asyncio.run(root.build_result(record))
        outcome = json.loads(store.db.execute("SELECT result FROM tool_operations").fetchone()[0])
        source = source_for(store, outcome)
        optional = references(store, outcome)
        other = Workflow(store, tools, ScriptedProvider([]), tmp_path / "other", "ucsc-other-engineering",
            _one_controller, _current_credit, project_child_credit=_current_credit, root_role="improvement",
            episode_record_receipts=True, initial_known_record_refs=[])
        receiver = other.build("improvement", "root", "Evaluate the same DNA using only actually received operands.", scope)
        context = other.binding_context(receiver.source)
        before = set(other.receipts.known(context.episode_id))
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        monkeypatch.setattr("gene_annotation_episode.molecular_sequence_input_bindings.retained_native_file", forbidden)
        resolve = other.resolver(plain(context.scope), context=context)
        for reference, namespace in ((source["id"], "source"), (source["artifact_ref"], "artifact"),
                (source["request_ref"], "artifact"), *[(ref, "artifact") for ref in source["auxiliary_artifact_refs"]]):
            assert reference not in before
            assert resolve(reference, namespace) is False
            assert tools.retained_molecular_reference_access(context, reference, namespace) is False
            item, path = other.services.read_received_molecular_input(context, reference, namespace, file_format="text")
            assert item["failure"] is not None and item["input"] is None and path is None
        for reference in optional:
            item = other.services.read_received_molecular_input(context, reference["id"], "reference", subject_metadata_only=True)
            assert item["input"] is None and item["failure"]["code"] == "reference_not_received"
            item, path = other.services.read_received_molecular_input(context,
                reference["sequence_ref"], "artifact", file_format="ascii_sequence")
            assert item["input"] is None and item["failure"]["code"] == "reference_not_received" and path is None
        read_args = dict(source_ref=source["id"], representation="original", offset=0, limit=512)
        with tools.current_invocation(context, read_received=other.services.read_received_molecular_input,
                tool_name="source.read", arguments=read_args, operation_key="ucsc-unreceived-body-probe"):
            with pytest.raises(ContractError, match="ucsc_source_primary_body_not_received"):
                tools._check_molecular_source_bytes("source.read", read_args)
        assert set(other.receipts.known(context.episode_id)) == before
        assert store.db.execute("SELECT count(*) FROM runtime_actions WHERE episode_id=?", (context.episode_id,)).fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_model_calls WHERE episode_id=?", (context.episode_id,)).fetchone()[0] == 0


# Fresh opt-in acquisition uses the current episode. The separately gated
# retained replay below preserves the original scientific-child history.
import os


_UCSC_LIVE_QUESTION = ("What DNA and native genome, chromosome and interval context does UCSC return "
    "for hg38 chrM [0,16) in forward orientation?")
_UCSC_LIVE_ARGUMENTS = {"operation": "sequence", "genome": "hg38", "hub_url": None,
    "chrom": "chrM", "start": 0, "end": 16, "rev_comp": False, "max_bytes": 65_536}
_UCSC_LIVE_RUN = "original-ucsc-selected-interval"
_UCSC_LIVE_FORM = {"type": "object", "properties": {"acquired_record_refs": {
    "type": "array", "items": {"type": "string", "format": "reference"},
    "x-source": "committed_record_refs"}}, "required": ["acquired_record_refs"],
    "additionalProperties": False}


def _ucsc_actual_native_interval(raw, result):
    """Verify exact root native values without picking duplicate members."""
    interval = ucsc_sequence_interval(result)
    assert interval is not None
    pairs = json.loads(raw, object_pairs_hook=lambda rows: rows,
        parse_int=lambda token: ("native_integer", token),
        parse_float=lambda token: ("native_number", token))
    assert type(pairs) is list and all(type(row) is tuple and len(row) == 2 for row in pairs)
    def field(name):
        found = [value for key, value in pairs if key == name]
        assert len(found) == 1, name
        return found[0]
    assert field("genome") == interval["genome"] == "hg38"
    assert field("chrom") == interval["chrom"] == "chrM"
    original_bounds = [field(name) for name in ("start", "end")]
    assert all(type(value) is tuple and value[0] == "native_integer" for value in original_bounds)
    assert [int(value[1]) for value in original_bounds] == [interval["start"], interval["end"]] == [0, 16]
    assert field("dna") == interval["dna"] and interval["length"] == len(interval["dna"]) == 16
    orientation = [value for name, value in pairs if name == "revComp"]
    assert not orientation or len(orientation) == 1 and orientation[0] is False
    assert interval["rev_comp"] is False and interval["hub_url"] is None
    return interval, [value[1] for value in original_bounds]


@pytest.mark.skipif(os.environ.get("HMMER_NATIVE_ORACLE_UCSC_LIVE") != "1"
    or "HMMER529_ATTEMPT" not in os.environ, reason="explicit bounded single original UCSC request only")
def test_opt_in_current_episode_ucsc_interval_receipt_and_explicit_reference_admission(tmp_path, monkeypatch):
    """One actual GET in the current episode; later metadata admission is explicit."""
    from test_molecular_provider_acquisition_live import OriginalLivePrefixObserved, RecordingLiveClients
    client = RecordingLiveClients(tmp_path / "provider-access")
    monkeypatch.setattr(client, "_skill", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    selected = deepcopy(_UCSC_LIVE_ARGUMENTS)
    report = dict(version="ucsc_current_acquisition_live_v1", question=_UCSC_LIVE_QUESTION,
        acquired=False, reference_published=False, reference_admitted=False,
        current_receiving_builder_verified=False, closed_replay_verified=False,
        scope="one current episode, ordinary acquisition and explicit metadata reads; no analysis or child")
    proof = tmp_path / "UCSC_ACQUISITION_CURRENT.json"
    with Store(tmp_path / "store") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="ACGTACGT", molecule="dna")["subject_refs"]}
        tools = ToolRegistry(store, clients=client)
        published = _native_publication_observer(tools, monkeypatch)
        session = _current_session(tmp_path / "session")
        holder = {}
        def select_reference_page(context):
            outcome = context["last_local_outcome"]
            confirmed = ucsc.validate_ucsc_receipt(outcome["result"])
            report.update(acquired=confirmed["acquired"], receipt=confirmed)
            if not confirmed["acquired"]:
                raise OriginalLivePrefixObserved("sole UCSC attempt retained without requested-data confirmation")
            source = store.get(confirmed["source_ref"])
            assert confirmed["data_ref"] == source["artifact_ref"]
            binding = holder["workflow"].binding_context(holder["root"].source)
            assert set(holder["workflow"].receipts.known(binding.episode_id)) == holder["baseline"] | {
                source["id"], source["artifact_ref"]}
            _assert_private_controls(holder["workflow"], tools, binding, source)
            report.update(source=source, reference_published=bool(published))
            # Stop any accidental second acquisition; SQL metadata reads remain.
            monkeypatch.setattr(PublicClients, "_http", forbidden)
            monkeypatch.setattr(ucsc, "publish_ucsc_request", forbidden)
            return action("state.query", dict(kind="reference", references=[source["id"]], offset=0, limit=5))
        def select_received_reference(context):
            rows = context["last_local_outcome"]["result"]["records"]
            assert {row["id"] for row in rows} == set(published)
            if len(published) != 1:
                raise OriginalLivePrefixObserved("raw UCSC data retained; no exact DNA Reference was available")
            reference_id, = published
            reference = store.get(reference_id)
            source = report["source"]
            assert reference["source_ref"] == source["id"]
            binding = holder["workflow"].binding_context(holder["root"].source)
            admitted = holder["workflow"].services.read_received_molecular_input(
                binding, reference_id, "reference", subject_metadata_only=True)
            assert admitted["failure"] is None and admitted["input"]["witness"]["record"] == reference
            admitted_file, path = holder["workflow"].services.read_received_molecular_input(
                binding, reference["sequence_ref"], "artifact", file_format="ascii_sequence")
            assert admitted_file["failure"] is None
            private_ref, = source["auxiliary_artifact_refs"]
            native = ucsc.ucsc_result_from_value(ucsc.validate_ucsc_value(
                json.loads(store.get_artifact(private_ref))), source_ref=source["id"])
            raw = store.get_artifact(source["artifact_ref"])
            interval, tokens = _ucsc_actual_native_interval(raw, native)
            assert path.read_bytes() == interval["dna"].encode("ascii")
            assert tools._sequence(reference_id) == interval["dna"]
            assert reference["length"] == interval["length"] == 16
            assert store.sequence_mapping(reference_id)["path"] == [dict(subject_ref=reference_id,
                start=0, end=16, unit="nt", strand="+")]
            assert store.coverage(reference_id) == store.roots(reference_id) == []
            _assert_private_controls(holder["workflow"], tools, binding, source)
            report.update(reference_admitted=True, reference=reference, actual_interval=interval,
                original_interval_number_tokens=tokens, raw_sha256=hashlib.sha256(raw).hexdigest(),
                raw_size_bytes=len(raw), native_response=native["response"])
            return action("state.query", {"refs": [reference_id]})
        actor = _CurrentProvider([action(TOOL, selected), select_reference_page, select_received_reference], session)
        directory, run_id = tmp_path / "run", "current-ucsc-selected-interval"
        current = _current_workflow(store, tools, actor, directory, run_id)
        root = current.build("improvement", "root", _UCSC_LIVE_QUESTION, scope)
        holder.update(workflow=current, root=root, baseline=set(current.receipts.known(root.source.episode_id)))
        stopped, record = False, None
        try:
            record = asyncio.run(root.run_async(current.context))
        except OriginalLivePrefixObserved:
            stopped = True
        except Exception as error:
            report["failure"] = dict(type=type(error).__name__, message=str(error))
            raise
        finally:
            report.update(fixture_prefix_stop=stopped, client_calls=client.calls,
                counts={name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in (
                    "runtime_episodes", "runtime_actions", "runtime_model_calls", "runtime_observations", "tool_operations")})
            proof.write_text(json.dumps(report, indent=2, allow_nan=False))
        assert len(client.calls) == 1
        assert store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0
        if stopped:
            assert record is None
            pytest.skip("sole acquisition prefix retained; its confirmation/reference limitation is recorded")
        final = asyncio.run(root.build_result(record)).as_record()
        assert report["acquired"] and report["reference_admitted"]
        calls = list(store.db.execute("SELECT request,response FROM runtime_model_calls ORDER BY call_index"))
        assert len(calls) == len(actor.dispatches) == 3
        for saved, dispatched in zip(calls, actor.dispatches):
            assert json.loads(saved["request"])["context"] == dispatched["context"]
            assert json.loads(dispatched["wire"]) == dispatched["context"] and saved["response"] is not None
        report["current_receiving_builder_verified"] = True
        before, artifacts, archives = _tables(store), _artifacts(store.path / "artifacts"), _artifacts(directory / "archive")
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        replay_actor = ScriptedProvider([])
        replay = _current_workflow(store, tools, replay_actor, directory, run_id)
        replay_root = replay.build("improvement", "root", _UCSC_LIVE_QUESTION, scope)
        replay_record = asyncio.run(replay_root.run_async(replay.context))
        assert asyncio.run(replay_root.build_result(replay_record)).as_record() == final
        assert replay_actor.contexts == [] and _tables(store) == before
        assert _artifacts(store.path / "artifacts") == artifacts and _artifacts(directory / "archive") == archives
        report.update(closed_replay_verified=True, final_result=final)
        proof.write_text(json.dumps(report, indent=2, allow_nan=False))



@pytest.mark.skipif(not os.environ.get("HMMER_NATIVE_ORACLE_UCSC_RETAINED"),
    reason="explicit original UCSC case directory and expected SQLite digest required")
def test_retained_live_ucsc_interval_parent_delivery_and_cached_root_replay(tmp_path, monkeypatch):
    """Authenticate one selected original, then replay its owned cached root."""
    from pathlib import Path
    import shutil
    import sqlite3

    from gene_annotation_episode.acquisition import SourceSnapshot
    from gene_annotation_episode.execution_contracts import canonical
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.runtime import Workflow
    from gene_annotation_episode.ucsc_acquisition import ucsc_result
    from test_molecular_provider_acquisition_host import _artifacts, _controller, _tables, forbidden
    from test_molecular_provider_acquisition_live import (
        _counts, _retained_live_artifact, _retained_live_inventory, _retained_live_rows,
    )
    from test_runtime import ScriptedProvider

    original = Path(os.environ["HMMER_NATIVE_ORACLE_UCSC_RETAINED"]).resolve()
    expected_sha = os.environ.get("HMMER_NATIVE_ORACLE_UCSC_RETAINED_DB_SHA256")
    assert type(expected_sha) is str and len(expected_sha) == 64 and set(expected_sha) <= set("0123456789abcdef")
    assert original.is_dir() and not original.is_symlink()
    assert not list(original.rglob("*-wal")) and not list(original.rglob("*-shm"))
    original_files = _retained_live_inventory(original)
    assert original_files["store/state.sqlite3"]["sha256"] == expected_sha
    report = {"question": _UCSC_LIVE_QUESTION, "original_database_sha256": expected_sha,
        "original_data_verified": False, "cached_root_replay_reached": False,
        "new_HTTP_requests": 0, "new_native_jobs": 0, "new_model_calls": 0}
    proof = tmp_path / "UCSC_ACQUISITION_RETAINED.json"
    proof.write_text(json.dumps(report, indent=2, allow_nan=False))
    connection = sqlite3.connect((original / "store/state.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        original_rows = _retained_live_rows(connection)
        live_proof = json.loads((original / "UCSC_ACQUISITION_LIVE.json").read_bytes())
        assert live_proof["question"] == _UCSC_LIVE_QUESTION
        assert live_proof["actual_native_interval_verified"] is live_proof["selected_record_delivery_verified"] is True
        assert live_proof["parent_return_reached"] is True and live_proof["closed_root_replay_reached"] is False
        saved, = list(connection.execute("SELECT * FROM tool_operations"))
        assert saved["name"] == TOOL and saved["arguments"] == canonical(_UCSC_LIVE_ARGUMENTS)
        outcome = json.loads(saved["result"])
        value = validate_ucsc_result(outcome["result"])
        assert outcome["status"] == "completed" and value == live_proof["actual_selected_result"]
        source = json.loads(connection.execute("SELECT data FROM records WHERE id=?", (value["source_ref"],)).fetchone()[0])
        assert source["origin"] == "external" and source["provider"] == "ucsc"
        assert source["accession"] is source["version"] is None
        assert source["artifact_ref"] == value["raw_artifact_ref"]
        raw = _retained_live_artifact(connection, original / "store", source["artifact_ref"])
        provenance = json.loads(_retained_live_artifact(connection, original / "store", source["request_ref"]))
        retained = SourceSnapshot(source["provider"], source["uri"], provenance["request"], source["retrieved_at"],
            raw, value["response"]["media_type"], provenance["transport"])
        assert canonical(ucsc_result(retained, arguments=_UCSC_LIVE_ARGUMENTS,
            source_ref=source["id"], artifact_ref=source["artifact_ref"])) == canonical(value)
        interval, number_tokens = _ucsc_actual_native_interval(raw, value)
        assert interval == live_proof["actual_interval"] and number_tokens == live_proof["original_interval_number_tokens"]
        reference, = [json.loads(connection.execute("SELECT data FROM records WHERE id=?", (ref,)).fetchone()[0])
            for ref in outcome["record_refs"] if ref != source["id"]]
        assert reference == live_proof["dna_reference"] and reference["record_type"] == "reference"
        assert reference["origin"] == "external" and reference["source_ref"] == source["id"]
        assert reference["reference_type"] == reference["molecule"] == "dna" and reference["length"] == 16
        assert _retained_live_artifact(connection, original / "store", reference["sequence_ref"]) == interval["dna"].encode("ascii")
        assert list(connection.execute("SELECT * FROM record_roots WHERE record_ref=?", (reference["id"],))) == []
        assert len(live_proof["client_calls"]) == 1 and live_proof["actual_transport_failures"] == []
        spec = ucsc_request_spec(_UCSC_LIVE_ARGUMENTS)
        assert live_proof["client_calls"][0] == {"service": "ucsc", "url": spec["url"], "params": spec["params"],
            "media_type": "application/json", "max_bytes": _UCSC_LIVE_ARGUMENTS["max_bytes"],
            "timeout_seconds": 30, "follow_redirects": False}
        episodes = list(connection.execute("SELECT * FROM runtime_episodes"))
        assert len(episodes) == 2 and all(row["state"] == "yielded" and row["archive"] is not None
            and json.loads(row["completion"])["actions"] == 1 for row in episodes)
        parent = next(row for row in episodes if len(json.loads(row["path"])) == 1)
        child = next(row for row in episodes if len(json.loads(row["path"])) == 2)
        root_request, child_request = json.loads(parent["request"]), json.loads(child["request"])
        original_call, = connection.execute("SELECT request FROM runtime_model_calls WHERE episode_id=?", (parent["episode_id"],))
        original_context = json.loads(original_call["request"])["context"]
        action_row, = connection.execute("SELECT * FROM runtime_actions WHERE episode_id=?", (child["episode_id"],))
        assert json.loads(action_row["action"]) == {"kind": "tool", "tool": TOOL, "arguments": _UCSC_LIVE_ARGUMENTS}
        actual_outcome = json.loads(action_row["result"])
        assert actual_outcome.pop("pending_work_after_action")["items"] == []
        assert canonical(actual_outcome) == canonical(outcome)
        assert saved["operation_key"] == parent["run_id"] + ":" + child["episode_id"] + ":0"
        assert saved["scope"] == canonical(child_request["message"]["scope"])
        form, = connection.execute("SELECT * FROM runtime_forms")
        attempt, = connection.execute("SELECT * FROM runtime_report_attempts")
        returned = json.loads(form["facts"])["committed_record_refs"]
        assert len(returned) == 2 and set(returned) == set(outcome["record_refs"]) == {source["id"], reference["id"]}
        assert json.loads(form["form"]) == json.loads(attempt["form"]) == live_proof["parent_form"] == {"acquired_record_refs": returned}
        assert form["episode_id"] == attempt["child_episode_id"] == child["episode_id"]
        assert attempt["parent_episode_id"] == parent["episode_id"] and attempt["failure"] is None and attempt["decision_index"] == 0
        for ref in (source["id"], source["artifact_ref"], source["request_ref"], reference["id"], reference["sequence_ref"]):
            receipt, = connection.execute("SELECT * FROM runtime_record_receipts WHERE episode_id=? AND record_ref=?",
                (parent["episode_id"], ref))
            assert receipt["receipt_kind"] == "child_form" and receipt["source_index"] == 0
        assert {name: len(original_rows[name]) for name in live_proof["counts"]} == live_proof["counts"] == {
            "runtime_episodes": 2, "runtime_actions": 2, "runtime_observations": 2, "runtime_model_calls": 2,
            "tool_operations": 1, "runtime_forms": 1, "runtime_report_attempts": 1}
        report.update(original_data_verified=True, actual_interval=interval, source_ref=source["id"],
            dna_reference_ref=reference["id"], original_typed_parent_form=live_proof["parent_form"],
            response=value["response"], actual_original_parent_receipts_verified=True)
        proof.write_text(json.dumps(report, indent=2, allow_nan=False))
    finally:
        connection.close()
        assert _retained_live_inventory(original) == original_files

    owned = tmp_path / "owned-retained-ucsc"
    shutil.copytree(original, owned)
    for path in [owned, *owned.rglob("*")]:
        path.chmod(0o755 if path.is_dir() else 0o644)
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr(PublicClients, "_skill", forbidden)
    monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
    monkeypatch.setattr(ToolRegistry, "_import", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    monkeypatch.setattr("gene_annotation_episode.ucsc_acquisition.ucsc_result", forbidden)
    try:
        with Store(owned / "store") as store:
            assert _tables(store) == original_rows
            before, artifacts = _tables(store), _artifacts(store.path / "artifacts")
            run_files = _retained_live_inventory(owned / "run")
            actor = ScriptedProvider([])
            monkeypatch.setattr(actor, "complete", forbidden)
            tools = ToolRegistry(store)
            descriptors = [child_request["message"]["scientific_process"]["mechanics_binding"], LiteratureEpisodes(None).as_record()]
            workflow = Workflow(store, tools, actor, owned / "run", parent["run_id"], _controller,
                lambda *args, **kwargs: 0, project_child_credit=lambda *args, **kwargs: 0,
                credit_binding=original_context["credit_binding"],
                child_credit_binding=original_context["scientific_child_credit_binding"],
                controller_binding=original_context["controller_binding"],
                episode_binding_descriptors=descriptors, episode_record_receipts=True, initial_known_record_refs=[])
            role, key = json.loads(parent["path"])[0]
            root = workflow.build(role, key, root_request["goal"]["objective"], root_request["message"]["scope"])
            record = asyncio.run(root.run_async(workflow.context))
            assert workflow.archive.store(record).descriptor() == json.loads(parent["archive"])
            final = asyncio.run(root.build_result(record)).as_record()
            assert final == live_proof["final_root_result"] and actor.contexts == []
            assert _counts(store) == live_proof["counts"]
            assert _tables(store) == before and _artifacts(store.path / "artifacts") == artifacts
            assert _retained_live_inventory(owned / "run") == run_files
            report.update(cached_root_replay_reached=True, cached_root_result=final,
                replay_scope="original yielded root reuses its original cached child result; no independent child-loop reconstruction",
                tables_artifacts_and_run_files_unchanged=True)
    except Exception as error:
        report["replay_failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        assert _retained_live_inventory(original) == original_files
        report["original_files_unchanged"] = True
        proof.write_text(json.dumps(report, indent=2, allow_nan=False))
