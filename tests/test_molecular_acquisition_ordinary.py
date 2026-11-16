"""Ordinary getter action-boundary controls, before controller observation.

One existing episode selects one data getter.  No episode loop, completion,
model, child, report or analysis is run.  Only urllib's response is controlled;
the real bounded HTTP capture, ToolRegistry, RuntimeAction and receipts execute.
The fixture's required neutral credit callable is bookkeeping, not a measured
gain or a claimed controller observation.  Separately gated live selectors below
use one original HTTP call and preserve its evidence before later assertions.
"""

import asyncio
from copy import deepcopy
from dataclasses import replace
from email.message import Message
import hashlib
import io
import json
from types import SimpleNamespace
import urllib.error
from urllib.parse import urlencode

import pytest

from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import identity
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry
from gene_annotation_episode import geo_tools
from gene_annotation_episode import ncbi_entrez_acquisition as entrez


CAP = 8 * 1024**2
ENTREZ_ARGUMENTS = dict(operation="search", database="gds", term="GSE1000[ACCN]",
    retstart=0, retmax=2, native_format="json", max_bytes=CAP)
GEO_ARGUMENTS = dict(study="GSE1", data_type="family_soft", max_bytes=CAP)
ENTREZ_DATA = b'{"esearchresult":{"count":"27","retstart":"0","retmax":"2","idlist":["42","42"]}}'
# An engineering gzip file, delivered literally.  This test never decompresses
# it or interprets its metadata/table content.
GEO_DATA = bytes.fromhex(
    "1f8b08000000000002ff8b0b760df2740d56b055700f7635e4520c4e2dca4c2d8e2fc92cc949050aba"
    "e6a567e6a502c5f2d2158a12cb15d2327352b900bc22255634000000")
FAILURE_DATA = b"controlled upstream unavailable\n"


def _forbidden(*args, **kwargs):
    raise AssertionError("ordinary getter control entered a model, controller or scientific operation")


def _neutral_bookkeeping(*args, **kwargs):
    return 0


class NoModel:
    complete = staticmethod(_forbidden)
    release = staticmethod(_forbidden)


class Response(io.BytesIO):
    def __init__(self, data, address, headers):
        super().__init__(data)
        self.status, self.address, self.headers = 200, address, headers

    def geturl(self):
        return self.address


def _http_control(monkeypatch, service, arguments, *, successful):
    spec = entrez.entrez_request_spec(arguments) if service == "ncbi_entrez" else geo_tools.geo_request_spec(arguments)
    address = spec["url"] + ("?" + urlencode(spec["params"]) if spec["params"] else "")
    data = (ENTREZ_DATA if service == "ncbi_entrez" else GEO_DATA) if successful else FAILURE_DATA
    headers = Message()
    headers["Content-Type"] = spec["media_type"] if successful else "text/plain"
    headers["Content-Length"] = str(len(data))
    calls = []
    def open_response(request, timeout):
        assert calls == [], "a second HTTP request, page or retry was not selected"
        assert request.full_url == address and request.get_method() == "GET"
        assert request.get_header("Accept") == spec["media_type"]
        calls.append(dict(url=request.full_url, method=request.get_method(), timeout=timeout))
        if not successful:
            raise urllib.error.HTTPError(address, 503, "controlled upstream unavailable", headers, io.BytesIO(data))
        return Response(data, address, headers)
    monkeypatch.setattr("urllib.request.build_opener", lambda *handlers: SimpleNamespace(open=open_response))
    monkeypatch.setattr("urllib.request.urlopen", _forbidden)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)
    monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
    return dict(calls=calls, data=data, address=address)


def _snapshot(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted((tuple((type(value).__name__, value) for value in row)
        for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr) for name in names}


@pytest.mark.parametrize("service,successful", [
    pytest.param("ncbi_entrez", True, id="ncbi_entrez_data_acquired"),
    pytest.param("ncbi_entrez", False, id="ncbi_entrez_captured_http_failure"),
    pytest.param("geo", True, id="geo_data_acquired"),
    pytest.param("geo", False, id="geo_captured_http_failure"),
])
def test_same_existing_episode_receives_only_ordinary_getter_receipt_before_observation(
        tmp_path, monkeypatch, service, successful):
    arguments = deepcopy(ENTREZ_ARGUMENTS if service == "ncbi_entrez" else GEO_ARGUMENTS)
    tool = "public.ncbi.entrez" if service == "ncbi_entrez" else "public.ncbi.geo"
    wire = _http_control(monkeypatch, service, arguments, successful=successful)
    with Store(tmp_path / "store") as store:
        subject, = store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]
        scope = store.validate_scope(dict(subject_refs=[subject]))
        tools = ToolRegistry(store, clients=PublicClients(ncbi_email=None))
        workflow = Workflow(store, tools, NoModel(), tmp_path / "run",
            "ordinary-getter-" + service + ("-success" if successful else "-captured-failure"),
            _forbidden, _neutral_bookkeeping, episode_binding_factories=(), root_role="improvement",
            episode_record_receipts=True, initial_known_record_refs=[])
        caller = workflow.build("improvement", "existing-caller", "Retrieve the selected data for future analysis", scope)
        assert caller.request.report_contract is None and workflow.episode_bindings.roles == ()
        entry = next(row for row in workflow.catalog(scope, source=caller.source) if row["name"] == tool)
        assert entry["input_schema"] == tools.catalog(scope)[tool]["input_schema"]
        known_before = set(workflow.receipts.known(caller.source.episode_id))
        records_before = {row[0] for row in store.db.execute("SELECT id FROM records")}
        selection = dict(kind="tool", tool=tool, arguments=arguments)
        key = f"{workflow.run_id}:{caller.source.episode_id}:0"
        asyncio.run(caller.source.execute(selection, 0))
        outcome = deepcopy(caller.source.last_outcome)
        receipt = outcome["result"]
        assert set(receipt) == {"acquired", "source_ref", "data_ref", "failure_code"}
        assert type(receipt["acquired"]) is bool and receipt["acquired"] is successful
        source = store.get(receipt["source_ref"])
        assert source["record_type"] == "source" and source["origin"] == "external" and source["provider"] == tool
        assert source["artifact_ref"] == "artifact_" + hashlib.sha256(wire["data"]).hexdigest()
        assert store.get_artifact(source["artifact_ref"]) == wire["data"]
        control = json.loads(store.get_artifact(source["request_ref"]))
        assert control["transport"]["request"]["method"] == "GET"
        assert control["transport"]["request"]["url"] == wire["address"]
        assert control["transport"]["status"] == (200 if successful else 503)
        if service == "ncbi_entrez":
            assert control["request"] == arguments
        else:
            assert control["request"] == dict(version=geo_tools.REQUEST_VERSION, arguments=arguments, native_request={})
        if successful:
            assert receipt["data_ref"] == source["artifact_ref"] and receipt["failure_code"] is None
            assert outcome["record_refs"] == [source["id"], receipt["data_ref"]]
        else:
            assert receipt["data_ref"] is None
            assert receipt["failure_code"] == ("ncbi_entrez_http_not_success" if service == "ncbi_entrez" else "geo_http_not_successful")
            assert outcome["record_refs"] == [source["id"]]
        known_after = set(workflow.receipts.known(caller.source.episode_id))
        assert known_after - known_before == set(outcome["record_refs"])
        assert source["request_ref"] not in known_after
        assert set(source.get("auxiliary_artifact_refs", [])).isdisjoint(known_after)
        assert (source["artifact_ref"] in known_after) is successful
        new_records = [store.get(row[0]) for row in store.db.execute("SELECT id FROM records") if row[0] not in records_before]
        assert new_records == [source]
        assert store.count("observation") == store.count("annotation") == 0
        action = workflow.journal.row("runtime_actions", caller.source.episode_id, 0)
        assert json.loads(action["action"]) == selection
        assert json.loads(action["result"])["result"] == receipt
        operation, = list(store.db.execute("SELECT * FROM tool_operations"))
        assert operation["operation_key"] == key and operation["name"] == tool
        assert operation["arguments"] == canonical(arguments) and operation["scope"] == canonical(scope)
        assert operation["id"] == identity("operation", dict(key=key, name=tool, arguments=arguments))
        saved = json.loads(operation["result"])
        assert saved == {name: value for name, value in outcome.items() if name != "pending_work_after_action"}
        episode, = list(store.db.execute("SELECT * FROM runtime_episodes"))
        assert episode["episode_id"] == caller.source.episode_id and episode["state"] == "active"
        assert episode["completion"] is episode["archive"] is None
        for table in ("runtime_observations", "runtime_model_calls", "runtime_forms", "runtime_report_attempts"):
            assert store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 1
        assert len(wire["calls"]) == 1
        before = _snapshot(store)
        with monkeypatch.context() as replay:
            replay.setattr(PublicClients, "_http", _forbidden)
            asyncio.run(caller.source.execute(selection, 0))
            cached = asyncio.run(workflow.execute(caller.source, tool, arguments, decision_index=0, operation_key=key))
        assert cached == saved and caller.source.last_outcome == outcome
        assert _snapshot(store) == before and len(wire["calls"]) == 1
        assert not (tmp_path / "run/api-service-execution").exists()
        # Standard action bookkeeping returned.  No controller consumed an
        # observation and no episode completion, report or analysis is claimed.
        assert plain(caller.request.as_record())["report_contract"] is None


