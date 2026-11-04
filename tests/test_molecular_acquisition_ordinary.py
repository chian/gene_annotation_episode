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
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import identity
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
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


def test_live_ordinary_entrez_getter_receipt_before_observation(tmp_path, monkeypatch):
    _run_live_ordinary_getter(tmp_path, monkeypatch, "ncbi_entrez")


def test_live_ordinary_geo_getter_receipt_before_observation(tmp_path, monkeypatch):
    _run_live_ordinary_getter(tmp_path, monkeypatch, "geo")


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


def test_live_geo_matrix_directory_inventory(tmp_path):
    """One selected official inventory GET; no matrix transfer or episode work."""
    if os.environ.get('HMMER_NATIVE_ORACLE_GEO_MATRIX_INVENTORY') != '1':
        pytest.skip('requires explicit GEO Matrix directory inventory selection')
    study, maximum = 'GSE1001', 65536
    bucket = 'GSE' + study[3:][:-3] + 'nnn'
    directory = geo_tools.ROOT + bucket + '/' + study + '/matrix/'
    assert directory == 'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE1nnn/GSE1001/matrix/'
    client = PublicClients(ncbi_email=None)
    prefix = tmp_path / 'GEO_MATRIX_INVENTORY_PREFIX.json'
    proof = dict(version='geo_matrix_directory_inventory_v1', study=study, directory_url=directory,
        request=dict(service='geo', url=directory, params={}, media_type='text/html', max_bytes=maximum,
            timeout_seconds=client.timeout, follow_redirects=False), http_invocations=0,
        passed=False, inventory_verified=False, selected_file=None,
        qualification='Official directory metadata only; no file download, Source publication, Workflow or analysis')
    _live_write(prefix, proof, exclusive=True)
    try:
        failure = None
        try:
            proof['http_invocations'] += 1
            _live_write(prefix, proof)
            snapshot = client._http('geo', directory, {}, 'text/html', max_bytes=maximum,
                timeout_seconds=client.timeout, follow_redirects=False)
        except AcquisitionError as error:
            failure, snapshot = error, error.snapshot
            proof['acquisition_failure'] = dict(code=error.code, phase=error.phase,
                diagnostic=deepcopy(error.diagnostic))
        if isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes:
            _live_capture(snapshot, tmp_path, proof, prefix)
        if failure is not None:
            raise failure
        assert isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes
        transport = snapshot.transport
        assert snapshot.service == 'geo' and snapshot.url == directory and snapshot.request == {}
        assert type(transport) is dict and transport['status'] == 200
        assert transport.get('effective_url', directory) == directory
        assert transport['request']['method'] == 'GET' and transport['request']['url'] == directory
        assert [value for name, value in transport['request']['headers'].items()
            if name.lower() == 'accept'] == ['text/html']
        assert transport['request_policy'] == dict(timeout_seconds=client.timeout, automatic_redirects=False)
        assert transport['response_byte_limit'] == maximum and transport['body_complete'] is True
        assert transport.get('body_capture_failure') is None and transport.get('body_capture_error') is None
        assert transport['retained_body_bytes'] == transport['observed_body_bytes'] == len(snapshot.content) <= maximum
        declared = transport.get('declared_body_bytes')
        assert declared is None or declared == len(snapshot.content)
        pairs = transport['header_items']
        assert any(name.lower() == 'content-type' and value.split(';', 1)[0].strip().lower() == 'text/html'
            for name, value in pairs)
        assert not any(name.lower() == 'content-range' or name.lower() == 'content-encoding'
            and value.strip().lower() != 'identity' for name, value in pairs)
        advertisement = _geo_matrix_advertisements(snapshot.content, directory=directory, study=study)
        proof['advertisement'] = advertisement
        proof['directory_identity_observed'] = bool(advertisement['matrix_files']) or any(
            urlsplit(directory).path.rstrip('/') in heading['text'] for heading in advertisement['headings'])
        _live_write(prefix, proof)
        assert proof['directory_identity_observed'], 'HTTP 200 HTML does not identify the selected directory'
        assert proof['http_invocations'] == 1
        proof.update(inventory_verified=True, passed=True)
    except BaseException as error:
        proof['test_failure'] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        _live_write(prefix, proof)


def test_retained_native_getter_integrity_without_acquisition(tmp_path, monkeypatch):
    """Apply current pure gates to actual 403 captures, without replay/publication."""
    if os.environ.get('HMMER_NATIVE_ORACLE_RETAINED_GETTER_INTEGRITY') != '1':
        pytest.skip('requires explicit retained 403 getter integrity verification')
    for owner, name in ((PublicClients, '_http'), (Store, '__init__'),
            (ToolRegistry, 'execute'), (ToolRegistry, 'execute_async'), (ToolRegistry, '_source'),
            (Workflow, 'build'), (geo_tools, 'request_geo'), (geo_tools, 'publish_geo_request'),
            (entrez_host, 'request_ncbi_entrez'), (entrez_host, 'publish_ncbi_entrez_request')):
        monkeypatch.setattr(owner, name, _forbidden)
    for name in ('urllib.request.urlopen', 'urllib.request.build_opener',
            'socket.create_connection', 'subprocess.Popen',
            'gene_annotation_episode.native_lifecycle.prepare_job'):
        monkeypatch.setattr(name, _forbidden)

    original = Path('/home/chia/repos/gene_annotation_episode/runs/check403_ordinary_molecular_data_getters_live/tmp')
    cases = (
        dict(service='ncbi_entrez', directory='test_live_ordinary_entrez_gett0',
            proof_sha256='699de611e1c7564609584c06c8f45ab835ab6113054af015120d22d4d647c97c',
            proof_size=29505, body_sha256='e833e37c993c1d6400120a2711e869c7d359f852bd9f64365788afc224ff86eb',
            body_size=285, arguments=deepcopy(ENTREZ_ARGUMENTS),
            source_ref='source_59e757611cd6f73685000eed', retrieved_at='2026-10-31T18:55:58.874465+00:00'),
        dict(service='geo', directory='test_live_ordinary_geo_getter_0',
            proof_sha256='40d812a7a999f7beb3450f5177e4c28923a3ed68453281d5e9c3f24daae45b65',
            proof_size=23281, body_sha256='fccd0054c5d34b5982d9874e0e196af889e0b7cfcadfb693a166662d488a83fe',
            body_size=9409370, arguments=deepcopy(LIVE_GEO_ARGUMENTS),
            source_ref='source_8b95795582e399dcb1700a95', retrieved_at='2026-10-31T18:56:09.665889+00:00'),
    )
    prefix = tmp_path / 'RETAINED_GETTER_INTEGRITY.json'
    audit = dict(version='retained_ordinary_getter_integrity_v1', passed=False, cases=[],
        qualification='Current local validators on exact retained native captures; no new acquisition, '
            'Source, receipt, Store, episode or analysis. Search relevance and unobserved aliases remain unavailable.')
    protected = {}
    _live_write(prefix, audit, exclusive=True)
    try:
        for case in cases:
            directory = original / case['directory']
            proof_path, body_path = directory / LIVE_PREFIX_NAME, directory / 'original-http-body.bin'
            proof_pin, body_pin = _live_pin(proof_path), _live_pin(body_path)
            assert (proof_pin['sha256'], proof_pin['size_bytes']) == (case['proof_sha256'], case['proof_size'])
            assert (body_pin['sha256'], body_pin['size_bytes']) == (case['body_sha256'], case['body_size'])
            proof = json.loads(proof_path.read_bytes())
            before = deepcopy(proof)
            assert proof['version'] == LIVE_PREFIX_VERSION and proof['service'] == case['service']
            assert all(proof[key] is True for key in ('passed', 'action_boundary_verified', 'same_key_replay_verified'))
            arguments = deepcopy(case['arguments'])
            tool = 'public.ncbi.' + ('entrez' if case['service'] == 'ncbi_entrez' else 'geo')
            assert proof['arguments'] == arguments and proof['tool'] == tool
            assert proof['selection'] == dict(kind='tool', tool=tool, arguments=arguments)
            capture, source, control = proof['http_capture'], proof['source'], proof['source_control']
            assert capture['body_file'] == body_pin
            assert capture['service'] == case['service'] and capture['retrieved_at'] == case['retrieved_at']
            assert source['id'] == case['source_ref'] and source['provider'] == tool
            assert source['origin'] == 'external' and source['record_type'] == 'source'
            assert source['retrieved_at'] == capture['retrieved_at'] and source['uri'] == capture['url']
            assert source['artifact_ref'] == 'artifact_' + body_pin['sha256']
            assert proof['outcome']['result'] == dict(acquired=True, source_ref=source['id'],
                data_ref=source['artifact_ref'], failure_code=None)
            operation, = proof['tool_operations']
            action, = proof['journal']['runtime_actions']
            assert json.loads(operation['arguments']) == arguments
            assert json.loads(action['action']) == proof['selection']
            assert json.loads(operation['result'])['result'] == json.loads(action['result'])['result'] == proof['outcome']['result']
            assert control['transport'] == capture['transport']
            for expected in (proof_pin, body_pin, *proof['store_files'].values()):
                pin = _live_pin(expected['path'])
                assert pin == expected
                protected[pin['path']] = dict(**pin, mode=Path(pin['path']).stat().st_mode)
            assert _live_pin(proof['retained_data_file']['path']) == proof['retained_data_file']
            assert proof['retained_data_file']['sha256'] == body_pin['sha256']
            control_path = directory / 'store/artifacts' / source['request_ref'][9:11] / source['request_ref'][9:]
            assert json.loads(control_path.read_bytes()) == control
            raw = body_path.read_bytes()
            assert len(raw) == case['body_size'] and hashlib.sha256(raw).hexdigest() == case['body_sha256']
            spec = (entrez.entrez_request_spec(arguments) if case['service'] == 'ncbi_entrez'
                else geo_tools.geo_request_spec(arguments))
            address = spec['url'] + ('?' + urlencode(spec['params']) if spec['params'] else '')
            assert proof['selected_wire_url'] == address and capture['url'] == spec['url']
            assert capture['request'] == spec['params'] and capture['media_type'] == spec['media_type']
            assert proof['http_calls'] == [dict(started=True, service=case['service'], url=spec['url'],
                params=spec['params'], media_type=spec['media_type'], keywords=dict(
                    max_bytes=arguments['max_bytes'], timeout_seconds=90, follow_redirects=False))]
            transport = capture['transport']
            assert transport['status'] == 200 and transport['body_complete'] is True
            assert transport['effective_url'] == address and transport['request']['method'] == 'GET'
            assert transport['request']['url'] == address
            assert transport['request_policy'] == dict(timeout_seconds=90, automatic_redirects=False)
            assert transport['response_byte_limit'] == arguments['max_bytes']
            assert transport['retained_body_bytes'] == transport['observed_body_bytes'] == len(raw)
            snapshot = SourceSnapshot(service=capture['service'], url=capture['url'],
                request=deepcopy(capture['request']), retrieved_at=capture['retrieved_at'],
                content=raw, media_type=capture['media_type'], transport=deepcopy(transport))
            row = dict(service=case['service'], original_proof=proof_pin, original_body=body_pin,
                source_ref=source['id'], data_ref=source['artifact_ref'], native_request=deepcopy(snapshot.request),
                url=snapshot.url, retrieved_at=snapshot.retrieved_at, transport=deepcopy(snapshot.transport))
            audit['cases'].append(row)
            if case['service'] == 'geo':
                # 403 intercepted _http before request_geo wrapped the selection.
                # Use its exact retained final request, changing no capture field.
                assert control['request'] == dict(version=geo_tools.REQUEST_VERSION,
                    arguments=arguments, native_request=capture['request'])
                selected = replace(snapshot, request=deepcopy(control['request']))
                row['association_failure'] = geo_tools._association_failure(selected, arguments, timeout=90)
                # Streams all members to EOF, including CRC/trailer and GSE header;
                # max_bytes remains the original transfer limit, not a decoded cap.
                row['transfer_content_failure'] = geo_tools._transfer_failure(selected, arguments)
                assert row['association_failure'] is row['transfer_content_failure'] is None
                row['verified_scope'] = 'Retained family SOFT gzip integrity and selected native Series GSE1000 identity'
            else:
                selected = entrez_host._selected_snapshot(snapshot, arguments, spec)
                value = entrez.entrez_result(selected, arguments=arguments,
                    source_ref=source['id'], artifact_ref=source['artifact_ref'])
                row['retrieval_failure'] = entrez_host._retrieval_failure(value, selected)
                row['selected_identity_state'] = entrez.entrez_selected_identity_state(value)
                assert row['retrieval_failure'] is None and row['selected_identity_state'] == 'unavailable'
                assert value['population']['matching_count_native'] == '13'
                assert [item['identifier'] for item in value['records']] == ['200001000', '562']
                assert value['response']['body_complete'] is True and value['response']['retained_bytes'] == 285
                row['verified_scope'] = 'Retained native GDS ESearch request, representation and complete capture; query semantics unavailable'
                row['population'] = deepcopy(value['population'])
            assert selected.request == control['request']
            assert selected.service == snapshot.service and selected.url == snapshot.url
            assert selected.content is raw and selected.retrieved_at == snapshot.retrieved_at
            assert selected.media_type == snapshot.media_type and selected.transport == snapshot.transport
            assert snapshot.request == capture['request'] and proof == before
            row['selected_request'] = deepcopy(selected.request)
            _live_write(prefix, audit)
        audit['passed'] = True
    except BaseException as error:
        audit['test_failure'] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        audit['protected_before'] = protected
        audit['protected_after'] = {path: dict(**_live_pin(path), mode=Path(path).stat().st_mode)
            for path in protected}
        audit['original_bytes_modes_unchanged'] = audit['protected_after'] == protected
        audit['passed'] = audit['passed'] and audit['original_bytes_modes_unchanged']
        _live_write(prefix, audit)
        assert audit['original_bytes_modes_unchanged']
