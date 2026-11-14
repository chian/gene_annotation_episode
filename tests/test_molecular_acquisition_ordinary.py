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
from html.parser import HTMLParser
import hashlib
import io
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace
import urllib.error
from urllib.parse import unquote, urlencode, urljoin, urlsplit

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import identity
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry
from gene_annotation_episode import geo_tools
from gene_annotation_episode import ncbi_entrez_acquisition as entrez
from gene_annotation_episode import ncbi_entrez_tools as entrez_host


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


LIVE_PREFIX_VERSION = "ordinary_molecular_getter_live_proof_v1"
LIVE_PREFIX_NAME = "ORDINARY_ACQUISITION_PREFIX.json"
LIVE_GEO_ARGUMENTS = dict(study="GSE1000", data_type="family_soft", max_bytes=1024**3)


def _live_pin(path):
    """Pin opaque bytes without decoding scientific data or loading another copy."""
    path = Path(path).resolve(strict=True)
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024**2), b""):
            digest.update(block)
            size += len(block)
    return dict(path=str(path), sha256=digest.hexdigest(), size_bytes=size)


def _live_write(path, proof, *, exclusive=False):
    with Path(path).open("x" if exclusive else "w") as handle:
        handle.write(json.dumps(proof, indent=2, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _live_gate(service):
    gate = "HMMER_NATIVE_ORACLE_ORDINARY_" + ("ENTREZ" if service == "ncbi_entrez" else "GEO") + "_LIVE"
    attempt = os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ACQUISITION_ATTEMPT", "")
    bounded_attempt = os.environ.get("HMMER529_ATTEMPT", "")
    if os.environ.get(gate) != "1" or not attempt or not bounded_attempt:
        pytest.skip("requires explicit single-service ordinary live getter and named bounded attempt")
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", attempt), "use a unique explicit acquisition attempt ID"
    return attempt, bounded_attempt


def _live_capture(snapshot, root, proof, prefix):
    """Save the actual returned/error capture before its ordinary publication."""
    body_path = root / "original-http-body.bin"
    with body_path.open("xb") as handle:
        handle.write(snapshot.content)
        handle.flush()
        os.fsync(handle.fileno())
    proof["http_capture"] = dict(service=snapshot.service, url=snapshot.url,
        request=deepcopy(snapshot.request), retrieved_at=snapshot.retrieved_at,
        media_type=snapshot.media_type, transport=deepcopy(snapshot.transport),
        body_file=_live_pin(body_path))
    _live_write(prefix, proof)


def _live_audit(store, workflow, caller, proof):
    """Keep actual action-boundary evidence, including incomplete failure paths."""
    tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    names = ("runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls",
        "runtime_forms", "runtime_report_attempts", "runtime_record_receipts", "runtime_receipt_inheritance")
    proof["journal"] = {name: [dict(row) for row in store.db.execute(
        "SELECT * FROM " + name + " WHERE run_id=? ORDER BY rowid", (workflow.run_id,))]
        for name in names if name in tables}
    proof["tool_operations"] = [dict(row) for row in store.db.execute("SELECT * FROM tool_operations ORDER BY rowid")]
    proof["outcome"] = deepcopy(caller.source.last_outcome)
    proof["known_after"] = sorted(workflow.receipts.known(caller.source.episode_id))
    proof["sources"] = [dict(id=row["id"], record=json.loads(row["data"])) for row in store.db.execute(
        "SELECT id,data FROM records WHERE record_type='source' ORDER BY id")]
    proof["artifact_metadata"] = [dict(row) for row in store.db.execute("SELECT * FROM artifacts ORDER BY id")]
    proof["scientific_record_counts"] = {name: store.count(name) for name in ("observation", "annotation")}


def _verify_live_action(store, tools, workflow, caller, arguments, selection, key, proof, monkeypatch):
    """Verify receipt, native byte custody and replay; never interpret the body."""
    outcome, = [json.loads(row["result"]) for row in proof["journal"]["runtime_actions"]]
    receipt = outcome["result"]
    assert set(receipt) == {"acquired", "source_ref", "data_ref", "failure_code"}
    assert receipt["acquired"] is True and receipt["failure_code"] is None, receipt
    assert outcome["status"] == "completed"
    source = store.get(receipt["source_ref"])
    assert source["record_type"] == "source" and source["origin"] == "external"
    assert source["provider"] == selection["tool"] and source["version"] is None
    capture = proof["http_capture"]
    pin = capture["body_file"]
    assert 0 < pin["size_bytes"] <= arguments["max_bytes"]
    assert receipt["data_ref"] == source["artifact_ref"] == "artifact_" + pin["sha256"]
    artifact = store.get(receipt["data_ref"])
    assert artifact["record_type"] == "artifact" and artifact["sha256"] == pin["sha256"]
    assert artifact["size"] == pin["size_bytes"]
    retained = _live_pin(store.path / "artifacts" / artifact["sha256"][:2] / artifact["sha256"])
    assert {name: retained[name] for name in ("sha256", "size_bytes")} == {name: pin[name] for name in ("sha256", "size_bytes")}
    control = json.loads(store.get_artifact(source["request_ref"]))
    assert canonical(control["transport"]) == canonical(capture["transport"])
    transport = control["transport"]
    assert transport["request"]["method"] == "GET" and transport["request"]["url"] == proof["selected_wire_url"]
    assert transport["request_policy"] == dict(timeout_seconds=tools.clients.timeout, automatic_redirects=False)
    assert 200 <= transport["status"] < 300 and transport["body_complete"] is True
    assert transport["response_byte_limit"] == arguments["max_bytes"]
    assert transport["observed_body_bytes"] == transport["retained_body_bytes"] == pin["size_bytes"]
    if proof["service"] == "ncbi_entrez":
        assert control["request"] == arguments
    else:
        assert control["request"] == dict(version=geo_tools.REQUEST_VERSION, arguments=arguments, native_request={})
    assert outcome["record_refs"] == [source["id"], artifact["id"]]
    known = set(workflow.receipts.known(caller.source.episode_id))
    assert known - set(proof["known_before"]) == {source["id"], artifact["id"]}
    assert source["request_ref"] not in known and set(source.get("auxiliary_artifact_refs", [])).isdisjoint(known)
    action, = proof["journal"]["runtime_actions"]
    assert json.loads(action["action"]) == selection
    assert action["episode_id"] == caller.source.episode_id and action["decision_index"] == 0
    operation, = proof["tool_operations"]
    assert operation["operation_key"] == key and operation["name"] == selection["tool"]
    assert operation["arguments"] == canonical(arguments) and operation["scope"] == canonical(proof["scope"])
    assert operation["id"] == identity("operation", dict(key=key, name=selection["tool"], arguments=arguments))
    saved = json.loads(operation["result"])
    assert saved == {name: value for name, value in outcome.items() if name != "pending_work_after_action"}
    episode, = proof["journal"]["runtime_episodes"]
    assert episode["state"] == "active" and episode["completion"] is episode["archive"] is None
    for name in ("runtime_observations", "runtime_model_calls", "runtime_forms", "runtime_report_attempts"):
        assert proof["journal"][name] == []
    assert proof["scientific_record_counts"] == dict(observation=0, annotation=0)
    assert len(proof["http_calls"]) == 1 and proof["http_calls"][0]["started"] is True
    before = _snapshot(store)
    with monkeypatch.context() as replay:
        replay.setattr(PublicClients, "_http", _forbidden)
        asyncio.run(caller.source.execute(selection, 0))
        cached = asyncio.run(workflow.execute(caller.source, selection["tool"], arguments,
            decision_index=0, operation_key=key))
    assert cached == saved and caller.source.last_outcome == outcome and _snapshot(store) == before
    assert not (Path(proof["workflow_directory"]) / "api-service-execution").exists()
    assert caller.request.report_contract is None and workflow.episode_bindings.roles == ()
    proof.update(source=source, source_control=control, retained_data_file=retained,
        same_key_replay_verified=True, action_boundary_verified=True)


def _run_live_ordinary_getter(tmp_path, monkeypatch, service):
    attempt, bounded_attempt = _live_gate(service)
    arguments = deepcopy(ENTREZ_ARGUMENTS if service == "ncbi_entrez" else LIVE_GEO_ARGUMENTS)
    tool = "public.ncbi.entrez" if service == "ncbi_entrez" else "public.ncbi.geo"
    spec = entrez.entrez_request_spec(arguments) if service == "ncbi_entrez" else geo_tools.geo_request_spec(arguments)
    address = spec["url"] + ("?" + urlencode(spec["params"]) if spec["params"] else "")
    prefix, store_directory = tmp_path / LIVE_PREFIX_NAME, tmp_path / "store"
    run_id = "ordinary-live-" + service + "-" + attempt
    proof = dict(version=LIVE_PREFIX_VERSION, attempt=attempt, bounded_attempt=bounded_attempt,
        service=service, tool=tool, arguments=arguments, selected_wire_url=address,
        run_id=run_id, store_directory=str(store_directory), workflow_directory=str(tmp_path / "run"),
        qualification="Actual ordinary action boundary before controller observation; no whole-episode completion or analysis",
        http_calls=[], passed=False, action_boundary_verified=False, same_key_replay_verified=False)
    _live_write(prefix, proof, exclusive=True)
    actual_http = PublicClients._http
    def http(current, service, url, params, media_type, **kwargs):
        assert proof["http_calls"] == [], "one selected actual HTTP request; no retry, fallback or page traversal"
        proof["http_calls"].append(dict(started=True, service=service, url=url,
            params=deepcopy(params), media_type=media_type, keywords=deepcopy(kwargs)))
        _live_write(prefix, proof)
        try:
            snapshot = actual_http(current, service, url, params, media_type, **kwargs)
        except AcquisitionError as error:
            proof["http_calls"][0]["failure"] = dict(code=error.code, phase=error.phase)
            if error.snapshot is not None:
                _live_capture(error.snapshot, tmp_path, proof, prefix)
            _live_write(prefix, proof)
            raise
        except BaseException as error:
            proof["http_calls"][0]["failure"] = dict(exception_type=type(error).__name__, message=str(error))
            _live_write(prefix, proof)
            raise
        _live_capture(snapshot, tmp_path, proof, prefix)
        return snapshot
    try:
        with Store(store_directory) as store:
            subject, = store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]
            scope = store.validate_scope(dict(subject_refs=[subject]))
            tools = ToolRegistry(store, clients=PublicClients(ncbi_email=None))
            workflow = Workflow(store, tools, NoModel(), tmp_path / "run", run_id,
                _forbidden, _neutral_bookkeeping, episode_binding_factories=(), root_role="improvement",
                episode_record_receipts=True, initial_known_record_refs=[])
            caller = workflow.build("improvement", "existing-caller", "Retrieve the selected data for future analysis", scope)
            selection = dict(kind="tool", tool=tool, arguments=arguments)
            key = f"{run_id}:{caller.source.episode_id}:0"
            proof.update(episode_id=caller.source.episode_id, operation_key=key, selection=selection,
                scope=scope, tool_info=deepcopy(tools.catalog(scope)[tool]),
                known_before=sorted(workflow.receipts.known(caller.source.episode_id)))
            _live_write(prefix, proof)
            try:
                with monkeypatch.context() as live:
                    live.setattr(PublicClients, "_http", http)
                    live.setattr("urllib.request.urlopen", _forbidden)
                    live.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)
                    live.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
                    asyncio.run(caller.source.execute(selection, 0))
            finally:
                _live_audit(store, workflow, caller, proof)
                _live_write(prefix, proof)
            _verify_live_action(store, tools, workflow, caller, arguments, selection, key, proof, monkeypatch)
            proof["passed"] = True
    except BaseException as error:
        proof["test_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        database = store_directory / "state.sqlite3"
        if database.is_file():
            proof["database_file"] = _live_pin(database)
            proof["store_files"] = {str(path.relative_to(store_directory)): _live_pin(path)
                for path in sorted(store_directory.rglob("*")) if path.is_file()}
        _live_write(prefix, proof)






class _GeoDirectoryLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.headings, self.heading = [], [], None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'a':
            line, column = self.getpos()
            self.links.append(dict(ordinal_0based=len(self.links),
                hrefs=[value for name, value in attrs if name.lower() == 'href'],
                line_1based=line, column_0based=column, raw_start_tag=self.get_starttag_text()))
        elif tag.lower() in {'title', 'h1'}:
            self.heading = dict(tag=tag.lower(), text='')
            self.headings.append(self.heading)

    def handle_endtag(self, tag):
        if self.heading is not None and tag.lower() == self.heading['tag']:
            self.heading = None

    def handle_data(self, data):
        if self.heading is not None:
            self.heading['text'] += data


def _geo_matrix_advertisements(raw, *, directory, study):
    """Read every anchor occurrence; select no file and follow no link."""
    parser = _GeoDirectoryLinks()
    parser.feed(raw.decode('utf-8'))
    parser.close()
    parent = urlsplit(directory)
    links, matrix_files = [], []
    for original in parser.links:
        row = {**original, 'resolved_url': None, 'file_name': None, 'eligible_matrix_file': False}
        if len(row['hrefs']) == 1 and type(row['hrefs'][0]) is str:
            try:
                address = urljoin(directory, row['hrefs'][0])
                row['resolved_url'] = address
                selected = urlsplit(address)
                if (selected.scheme == parent.scheme and selected.netloc == parent.netloc
                        and selected.path.startswith(parent.path) and not selected.query and not selected.fragment):
                    name = unquote(selected.path[len(parent.path):], errors='strict')
                    if name and '/' not in name and '\\' not in name:
                        row['file_name'] = name
                        # Grammar check only; this does not select or request a file.
                        arguments = dict(study=study, data_type='series_matrix', file_name=name, max_bytes=1)
                        expected = geo_tools.geo_request_spec(arguments)['url']
                        row['eligible_matrix_file'] = address == expected
                        if row['eligible_matrix_file']:
                            matrix_files.append(dict(ordinal_0based=row['ordinal_0based'],
                                href=row['hrefs'][0], url=address, file_name=name))
            except ValueError:
                row['eligible_matrix_file'] = False
        links.append(row)
    return dict(headings=parser.headings, links=links, matrix_files=matrix_files)




