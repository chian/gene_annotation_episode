"""Ordinary GEO getter controls with engineered HTTP bytes; no live downloads.

The actual registry publishes and caches one selected retrieval. Metadata-only
receiving contexts exercise existing receipts; they assert no Workflow, child,
model, scientific calculation or original GEO study measurement completion.
"""
from copy import deepcopy
from dataclasses import replace
from email.message import Message
import gzip
import hashlib
import io
import json
from types import SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode import geo_tools as geo
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_geo_acquisition import SOFT


FAMILY = {"study": "GSE1001", "data_type": "family_soft", "max_bytes": 65536}
MATRIX = {"study": "GSE1001", "data_type": "series_matrix", "file_name": "GSE1001-GPL96_series_matrix.txt.gz", "max_bytes": 65536}
SUPPLEMENT = {"study": "GSE1000", "data_type": "supplementary_file", "file_name": "filelist.txt", "max_bytes": 65536}
MATRIX_BYTES = gzip.compress(b'!Series_geo_accession\t"GSE1001"\n!Sample_geo_accession\t"GSM1"\t"GSM2"\n!Sample_platform_id\t"GPL96"\t"GPL96"\n!series_matrix_table_begin\n"ID_REF"\t"GSM1"\t"GSM2"\n"p1"\t0\t\n"p2"\tNA\t1e-9999\n!series_matrix_table_end\n', mtime=0)
RAW = {"family_soft": gzip.compress(SOFT.replace(b'GSE1', b'GSE1001'), mtime=0), "series_matrix": MATRIX_BYTES,
    "supplementary_file": b'file\t0\t\tNA\nopaque\x00\xff\n'}


def forbidden(*args, **kwargs):
    pytest.fail("ordinary data retrieval attempted extra HTTP, interpretation or scientific work")


class Responses(PublicClients):
    """Only the shared HTTP response seam is controlled; no endpoint is called."""
    def __init__(self, *, mode="success", raw=None):
        super().__init__(ncbi_email=None, timeout=3)
        self.mode, self.raw, self.calls, self.snapshots = mode, raw, [], []

    def _http(self, service, url, params, media_type, **options):
        self.calls.append(dict(service=service, url=url, params=deepcopy(params), media_type=media_type, **options))
        if self.mode == "no_response":
            raise AcquisitionError("provider_connection_failed", phase="http_request")
        kind = "family_soft" if "/soft/" in url else "series_matrix" if "/matrix/" in url else "supplementary_file"
        raw = RAW[kind] if self.raw is None else self.raw
        maximum = options["max_bytes"]
        retained = raw[:maximum]
        complete = len(raw) <= maximum and self.mode not in {"incomplete", "capture_error", "unknown_capture"}
        status = 503 if self.mode == "http_error" else 302 if self.mode == "redirect" else 206 if self.mode == "range" else 200
        headers = [["Content-Type", "application/octet-stream"]]
        if self.mode == "html":
            retained = b"<html>provider challenge</html>"; raw = retained
            headers = [["Content-Type", "text/html"]]
        if self.mode == "http_encoding": headers.append(["Content-Encoding", "gzip"])
        if self.mode == "range": headers.append(["Content-Range", "bytes 0-2/100"])
        transport = {"status": status, "representation": "http_response_bytes",
            "headers": {key.lower(): value for key, value in headers}, "header_items": headers,
            "request": {"method": "GET", "url": url, "headers": {"Accept": media_type}},
            "request_policy": {"timeout_seconds": options["timeout_seconds"], "automatic_redirects": options["follow_redirects"]},
            "body_complete": None if self.mode == "unknown_capture" else complete,
            "response_byte_limit": maximum, "retained_body_bytes": len(retained),
            "observed_body_bytes": len(raw) if len(raw) <= maximum else maximum+1,
            "declared_body_bytes": len(raw), "job_details": {"database": {"version": "unrelated-version"}}}
        if not complete: transport["body_capture_failure"] = "provider_response_byte_limit" if len(raw) > maximum else "provider_body_capture_failed"
        if self.mode == "capture_error": transport["body_capture_error"] = "IncompleteRead"
        native_request = deepcopy(params)
        if self.mode == "other_request": native_request = {"acc": "GSE2000"}
        elif self.mode == "other_url": url = "https://example.invalid/not-selected"
        elif self.mode == "other_effective": transport["effective_url"] = "https://example.invalid/not-selected"
        elif self.mode == "other_accept": transport["request"]["headers"]["Accept"] = "text/html"
        elif self.mode == "other_method": transport["request"]["method"] = "POST"
        elif self.mode == "other_redirect_policy": transport["request_policy"]["automatic_redirects"] = True
        elif self.mode == "other_timeout": transport["request_policy"]["timeout_seconds"] = 4
        elif self.mode == "other_limit": transport["response_byte_limit"] += 1
        elif self.mode == "other_size": transport["observed_body_bytes"] += 1
        elif self.mode == "status_bool": transport["status"] = True
        value = SourceSnapshot(service, url, native_request, "2026-10-31T12:00:00+00:00", retained, media_type, transport)
        self.snapshots.append(value)
        if status >= 300 or not complete:
            raise AcquisitionError("provider_http_"+str(status) if status >= 300 else "provider_body_capture_failed",
                snapshot=value, phase="http_response")
        return value


@pytest.fixture
def host(tmp_path):
    with Store(tmp_path / "store") as store:
        target, = store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]
        client = Responses()
        yield SimpleNamespace(store=store, client=client, tools=ToolRegistry(store, clients=client),
            scope={"subject_refs": [target]})


def execute(h, arguments=FAMILY, *, key="geo-get"):
    return h.tools.execute(geo.TOOL, deepcopy(arguments), scope=h.scope, operation_key=key)


def inventory(store):
    tables = {name: sorted((tuple(row) for row in store.db.execute('SELECT * FROM "'+name.replace('"', '""')+'"')), key=repr)
        for name, in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
    files = {str(path.relative_to(store.path)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (store.path / "artifacts").rglob("*") if path.is_file()}
    return tables, files


def assert_custody(h, outcome, arguments, *, acquired):
    value = outcome["result"]
    assert set(value) == {"acquired", "source_ref", "data_ref", "failure_code"}
    assert value["acquired"] is acquired
    source = h.store.get(value["source_ref"])
    original = h.client.snapshots[-1]
    assert source["provider"] == geo.TOOL and source["origin"] == "external" and source["version"] is None
    assert source["uri"] == original.url and source["retrieved_at"] == original.retrieved_at
    assert source["artifact_ref"] == "artifact_"+hashlib.sha256(original.content).hexdigest()
    assert h.store.get_artifact(source["artifact_ref"]) == original.content
    request = {"version": geo.REQUEST_VERSION, "arguments": arguments, "native_request": original.request}
    assert canonical(json.loads(h.store.get_artifact(source["request_ref"]))) == canonical({"request": request, "transport": original.transport})
    assert outcome["record_refs"] == ([source["id"], source["artifact_ref"]] if acquired else [source["id"]])
    assert value["data_ref"] == (source["artifact_ref"] if acquired else None)
    assert (value["failure_code"] is None) is acquired
    return source


def receiver(h, refs):
    run_id = "geo-receipt-control"
    journal, receipts = Journal(h.store, run_id), EpisodeReceipts(h.store, run_id)
    path = (("annotation", "receiver"),)
    episode_id = EpisodeRef(run_id, path).episode_id
    manifest = receipts.bind(episode_id)
    request = {"message": {"scope": h.scope, "episode_assignment": {}, "knowledge_inheritance": manifest}}
    journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path), "request": canonical(request),
        "initial_credit": 0., "state": "active"})
    context = BindingContext(run_id, episode_id, "annotation", path, h.scope, {}, request)
    receipts.receive(episode_id, refs, kind="initial")
    return context, receipts


@pytest.mark.parametrize("arguments", [FAMILY, MATRIX, SUPPLEMENT])
def test_actual_registry_gets_exact_selected_file_and_only_returns_compact_receipt(host, monkeypatch, arguments):
    h = host
    monkeypatch.setattr("gene_annotation_episode.geo_acquisition.parse_geo_soft", forbidden)
    monkeypatch.setattr("gzip.decompress", forbidden)
    chosen = deepcopy(arguments)
    outcome = execute(h, chosen)
    assert outcome["status"] == "completed" and outcome["feedback"] is None, outcome
    source = assert_custody(h, outcome, chosen, acquired=True)
    assert source["accession"] == arguments["study"]
    assert h.client.calls == [{**geo.geo_request_spec(arguments), "timeout_seconds": 3}]
    assert h.store.count("annotation") == h.store.count("observation") == 0
    before = inventory(h.store)
    monkeypatch.setattr(h.client, "_http", forbidden)
    assert execute(h, chosen) == outcome
    assert inventory(h.store) == before
    with pytest.raises(ContractError, match="operation_key_reused"):
        execute(h, {**chosen, "max_bytes": chosen["max_bytes"]-1})
    assert inventory(h.store) == before


@pytest.mark.parametrize("arguments,url", [
    (FAMILY, "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE1nnn/GSE1001/soft/GSE1001_family.soft.gz"),
    (MATRIX, "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE1nnn/GSE1001/matrix/GSE1001-GPL96_series_matrix.txt.gz"),
    (SUPPLEMENT, "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE1nnn/GSE1000/suppl/filelist.txt"),
    ({**FAMILY, "study": "GSE1"}, "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE1/soft/GSE1_family.soft.gz"),
    ({**SUPPLEMENT, "file_name": "literal name+μ?.txt"}, "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE1nnn/GSE1000/suppl/literal%20name%2B%CE%BC%3F.txt"),
])
def test_request_compiles_documented_study_directory_and_literal_single_filename(arguments, url):
    spec = geo.geo_request_spec(arguments)
    assert spec == {"service": "geo", "url": url, "params": {}, "media_type": "application/octet-stream",
        "max_bytes": arguments["max_bytes"], "follow_redirects": False}


@pytest.mark.parametrize("arguments", [
    {**FAMILY, "max_bytes": True}, {**FAMILY, "max_bytes": 1.0}, {**FAMILY, "max_bytes": 0},
    {**FAMILY, "max_bytes": geo.MAX_DOWNLOAD_BYTES+1}, {**FAMILY, "study": "GSE01"},
    {**FAMILY, "study": "GSE1\n"}, {**FAMILY, "study": "GSM1"}, {**FAMILY, "study": "gse1"},
    {**FAMILY, "data_type": "raw"}, {**FAMILY, "data_type": []}, {**FAMILY, "data_type": {}},
    {**FAMILY, "file_name": "unexpected.gz"},
    {**MATRIX, "file_name": "GSE2000_series_matrix.txt.gz"}, {**MATRIX, "file_name": "GSE1001-GPL01_series_matrix.txt.gz"},
    {**SUPPLEMENT, "file_name": "../other"}, {**SUPPLEMENT, "file_name": "a/b"}, {**SUPPLEMENT, "file_name": "a\\b"},
    {**SUPPLEMENT, "file_name": ".."}, {**SUPPLEMENT, "file_name": "x\x00y"}, {**FAMILY, "url": "https://example.invalid/"},
    {"study": "GSE1001", "data_type": "series_matrix", "max_bytes": 1},
])
def test_closed_arguments_reject_wrong_study_type_filename_or_limit_before_http(host, arguments):
    with pytest.raises(ContractError, match="geo_arguments_invalid"):
        geo.validate_geo_arguments(arguments)
    outcome = execute(host, arguments)
    assert outcome["status"] == "invalid" and outcome["record_refs"] == []
    assert set(outcome["result"]) == {"acquired", "source_ref", "data_ref", "failure_code"}
    assert outcome["result"]["acquired"] is False and outcome["result"]["source_ref"] is None
    assert outcome["result"]["data_ref"] is None
    assert host.client.calls == [] and host.client.snapshots == []


@pytest.mark.parametrize("mode,code", [("http_error", "geo_http_not_successful"), ("redirect", "geo_http_not_successful"),
    ("range", "geo_partial_response"), ("incomplete", "geo_capture_incomplete"), ("capture_error", "geo_capture_incomplete"),
    ("unknown_capture", "geo_capture_incomplete"), ("http_encoding", "geo_http_content_encoding_unsupported"),
    ("html", "geo_wrong_file_representation"), ("other_request", "geo_selected_request_mismatch"),
    ("other_url", "geo_selected_request_mismatch"), ("other_effective", "geo_selected_request_mismatch"),
    ("other_accept", "geo_selected_request_mismatch"), ("other_method", "geo_selected_request_mismatch"),
    ("other_redirect_policy", "geo_transfer_policy_mismatch"), ("other_timeout", "geo_transfer_policy_mismatch"),
    ("other_limit", "geo_transfer_policy_mismatch"), ("other_size", "geo_capture_identity_mismatch"),
    ("status_bool", "geo_http_status_unavailable")])
def test_captured_failures_keep_real_source_prefix_but_do_not_deliver_data_file(host, monkeypatch, mode, code):
    h = host; h.client.mode = mode
    outcome = execute(h)
    assert outcome["status"] == "partial", outcome
    source = assert_custody(h, outcome, FAMILY, acquired=False)
    assert outcome["result"]["failure_code"] == code
    assert len(h.client.calls) == 1
    assert source["accession"] == (None if mode.startswith("other_") and mode != "other_size" else FAMILY["study"])
    before = inventory(h.store)
    monkeypatch.setattr(h.client, "_http", forbidden)
    assert execute(h) == outcome and inventory(h.store) == before


def test_raw_byte_limit_retains_observed_prefix_without_a_data_delivery(host):
    arguments = {**FAMILY, "max_bytes": 8}
    outcome = execute(host, arguments)
    assert outcome["status"] == "partial", outcome
    source = assert_custody(host, outcome, arguments, acquired=False)
    assert outcome["result"]["failure_code"] == "geo_capture_incomplete"
    assert host.store.get_artifact(source["artifact_ref"]) == RAW["family_soft"][:8]
    assert host.client.snapshots[0].transport["observed_body_bytes"] == 9


def test_no_response_has_no_fabricated_source_and_same_failed_receipt_is_cached(host, monkeypatch):
    h = host; h.client.mode = "no_response"
    before_sources = h.store.count("source")
    outcome = execute(h)
    assert outcome["status"] == "failed" and outcome["record_refs"] == [], outcome
    assert outcome["result"] == {"acquired": False, "source_ref": None, "data_ref": None,
        "failure_code": "provider_connection_failed"}
    assert h.store.count("source") == before_sources and len(h.client.calls) == 1
    before = inventory(h.store)
    monkeypatch.setattr(h.client, "_http", forbidden)
    assert execute(h) == outcome and inventory(h.store) == before


@pytest.mark.parametrize("raw", [b"", b"<html>literal selected supplemental content</html>", b"\xff\x00raw\n"])
def test_explicit_supplementary_bytes_are_opaque_including_a_real_empty_file(host, raw):
    host.client.raw = raw
    outcome = execute(host, SUPPLEMENT)
    assert outcome["status"] == "completed", outcome
    source = assert_custody(host, outcome, SUPPLEMENT, acquired=True)
    assert host.store.get(source["artifact_ref"])["size"] == len(raw)


def test_invalid_gzip_is_not_delivered_as_selected_native_data(host, monkeypatch):
    host.client.raw = b"\x1f\x8b\x08retained-invalid-gzip-body"
    monkeypatch.setattr("gzip.decompress", forbidden)
    monkeypatch.setattr("gene_annotation_episode.geo_acquisition.parse_geo_soft", forbidden)
    outcome = execute(host, {**FAMILY, "max_bytes": geo.MAX_DOWNLOAD_BYTES})
    assert outcome["status"] == "partial", outcome
    source = assert_custody(host, outcome, {**FAMILY, "max_bytes": geo.MAX_DOWNLOAD_BYTES}, acquired=False)
    assert outcome['result']['failure_code'] == 'geo_gzip_integrity_failed'
    assert host.client.calls[0]["max_bytes"] == 1073741824
    assert host.store.get_artifact(source['artifact_ref']) == host.client.raw


@pytest.mark.parametrize('defect', ['crc', 'truncated', 'trailing', 'later_member'])
def test_complete_http_cannot_hide_corrupt_gzip_after_matching_identity(host, defect):
    raw = gzip.compress(b'^SERIES = GSE1001\n', mtime=0)
    if defect == 'crc':
        raw = raw[:-8] + bytes((raw[-8] ^ 1,)) + raw[-7:]
    elif defect == 'truncated':
        raw = raw[:-3]
    elif defect == 'trailing':
        raw += b'not another gzip member'
    else:
        raw += gzip.compress(b'!Series_title = later member\n', mtime=0)[:-2]
    host.client.raw = raw
    outcome = execute(host)
    assert_custody(host, outcome, FAMILY, acquired=False)
    assert outcome['result']['failure_code'] == 'geo_gzip_integrity_failed'


def test_streaming_integrity_reads_all_members_without_an_unselected_decoded_cap(host, monkeypatch):
    expanded = b'^SERIES = GSE1001\n!Series_title = ' + b'x' * (8 * 1024**2 + 65536) + b'\n'
    host.client.raw = gzip.compress(expanded, mtime=0) + gzip.compress(b'', mtime=0)
    original_read = gzip.GzipFile.read
    reads = []
    def bounded_read(stream, size=-1):
        assert size == 65536
        reads.append(size)
        return original_read(stream, size)
    monkeypatch.setattr(gzip.GzipFile, 'read', bounded_read)
    monkeypatch.setattr(gzip, 'decompress', forbidden)
    monkeypatch.setattr('gene_annotation_episode.geo_acquisition.parse_geo_soft', forbidden)
    outcome = execute(host)
    assert_custody(host, outcome, FAMILY, acquired=True)
    assert len(reads) > 128 and len(host.client.calls) == 1


@pytest.mark.parametrize('data_type,body,code', [
    ('family_soft', b'^SERIES = GSE2000\n', 'geo_selected_study_identity_conflict'),
    ('family_soft', b'<html>native-looking compressed error</html>', 'geo_selected_study_identity_unavailable'),
    ('family_soft', b'^SERIES = GSE1001\n', None),
    ('series_matrix', b'!Series_geo_accession\t"GSE2000"\n', 'geo_selected_study_identity_conflict'),
    ('series_matrix', b'!Series_geo_accession\t"GSE1001"\n', None),
])
def test_series_identity_is_literal_without_requiring_scientific_rows(host, data_type, body, code):
    host.client.raw = gzip.compress(body, mtime=0)
    arguments = FAMILY if data_type == 'family_soft' else MATRIX
    outcome = execute(host, arguments)
    assert_custody(host, outcome, arguments, acquired=code is None)
    assert outcome['result']['failure_code'] == code


@pytest.mark.parametrize('platforms,code', [
    (b'"GPL96"\t"GPL96"', None),
    (b'"GPL97"\t"GPL97"', 'geo_selected_platform_identity_conflict'),
    (b'"GPL97"\t"GPL98"', None),
    (b'"GPL96"\t"GPL97"', None),
    (b'"GPL97"\t""', None),
    (b'', None),
])
def test_platform_conflict_requires_unambiguous_native_sample_platform_metadata(host, platforms, code):
    host.client.raw = gzip.compress(b'!Series_geo_accession\t"GSE1001"\n!Sample_platform_id\t' + platforms + b'\n', mtime=0)
    outcome = execute(host, MATRIX)
    assert_custody(host, outcome, MATRIX, acquired=code is None)
    assert outcome['result']['failure_code'] == code


def test_identity_headers_cross_stream_chunks_and_gzip_members(host):
    prefix = b'!Unselected = ' + b'x' * (65536 - 32) + b'\n^SER'
    host.client.raw = gzip.compress(prefix, mtime=0) + gzip.compress(b'IES = GSE1001\n', mtime=0)
    outcome = execute(host)
    assert_custody(host, outcome, FAMILY, acquired=True)


@pytest.mark.parametrize('platform,code', [
    (b'GPL96', None), (b'GPL97', 'geo_selected_platform_identity_conflict'),
])
def test_matrix_tab_delimited_identity_and_platform_headers_accept_crlf(host, platform, code):
    # Engineered Matrix-format headers; this is not an acquired native matrix fixture.
    host.client.raw = gzip.compress(b'!Series_geo_accession\t"GSE1001"\r\n!Sample_platform_id\t"' +
        platform + b'"\t"' + platform + b'"\r\n', mtime=0)
    outcome = execute(host, MATRIX)
    assert_custody(host, outcome, MATRIX, acquired=code is None)
    assert outcome['result']['failure_code'] == code


@pytest.mark.parametrize('marker,suffix,code', [
    (b'!Series_geo_accession', b'\t"GSE1001"\r\n!Sample_platform_id\t"GPL96"\r\n', None),
    (b'!Sample_platform_id', b'\t"GPL97"\r\n', 'geo_selected_platform_identity_conflict'),
])
def test_matrix_tab_delimiter_crosses_decoded_chunks_and_gzip_members(host, marker, suffix, code):
    leading = b'!Series_geo_accession\t"GSE1001"\r\n' if marker == b'!Sample_platform_id' else b''
    prefix = leading + b'!Unselected\t'
    prefix += b'x' * (65536 - len(prefix) - len(b'\r\n') - len(marker)) + b'\r\n' + marker
    assert len(prefix) == 65536
    host.client.raw = gzip.compress(prefix, mtime=0) + gzip.compress(suffix, mtime=0)
    outcome = execute(host, MATRIX)
    assert_custody(host, outcome, MATRIX, acquired=code is None)
    assert outcome['result']['failure_code'] == code


@pytest.mark.parametrize('arguments,body', [
    (MATRIX, b'!Series_geo_accession = "GSE1001"\n'),
    (FAMILY, b'^SERIES\tGSE1001\n'),
])
def test_selected_representation_does_not_borrow_another_header_delimiter(host, arguments, body):
    host.client.raw = gzip.compress(body, mtime=0)
    outcome = execute(host, arguments)
    assert_custody(host, outcome, arguments, acquired=False)
    assert outcome['result']['failure_code'] == 'geo_selected_study_identity_unavailable'


@pytest.mark.parametrize("success", [False, True])
def test_actual_receipts_deliver_requested_data_file_only_on_success_and_keep_controls_private(host, success):
    if not success: host.client.mode = "http_error"
    outcome = execute(host)
    source = assert_custody(host, outcome, FAMILY, acquired=success)
    context, receipts = receiver(host, outcome["record_refs"])
    assert set(receipts.known(context.episode_id)) == set(outcome["record_refs"])
    assert molecular_reference_restriction(host.store, context, source["artifact_ref"], "artifact") is success
    assert molecular_reference_restriction(host.store, context, source["request_ref"], "artifact") is False
    with pytest.raises(ContractError): artifact_path(host.store, source["request_ref"])


def test_source_only_body_read_adds_no_file_receipt_and_cached_read_rechecks_source_receipt(host, monkeypatch):
    host.client.raw = b"selected study data\t0\tNA\n"
    outcome = execute(host, SUPPLEMENT)
    source = assert_custody(host, outcome, SUPPLEMENT, acquired=True)
    context, receipts = receiver(host, [source["id"]])
    assert set(receipts.known(context.episode_id)) == {source["id"]}
    assert molecular_reference_restriction(host.store, context, source["artifact_ref"], "artifact") is False
    arguments = {"source_ref": source["id"], "representation": "original"}
    with host.tools.current_invocation(context, read_received=None, tool_name="source.read",
            arguments=arguments, operation_key=None):
        read = host.tools.execute("source.read", arguments, scope=host.scope, operation_key="body-read")
    assert read["status"] == "completed" and read["result"]["text"] == host.client.raw.decode("ascii"), read
    assert read["record_refs"] == [] and set(receipts.known(context.episode_id)) == {source["id"]}
    original = host.store.db.execute("SELECT result FROM tool_operations WHERE operation_key='body-read'").fetchone()[0]
    host.store.db.execute("DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=?",
        (context.run_id, context.episode_id))
    monkeypatch.setattr("gene_annotation_episode.materials._verified_artifact_path", forbidden)
    with host.tools.current_invocation(context, read_received=None, tool_name="source.read",
            arguments=arguments, operation_key=None):
        denied = host.tools.execute("source.read", arguments, scope=host.scope, operation_key="body-read")
    assert denied["status"] == "invalid" and denied["feedback"]["code"] == "geo_source_primary_body_not_received"
    assert host.store.db.execute("SELECT result FROM tool_operations WHERE operation_key='body-read'").fetchone()[0] == original


def test_actual_shared_http_keeps_file_gzip_bytes_without_a_second_request(host, monkeypatch):
    raw = RAW["family_soft"]
    headers = Message(); headers["Content-Type"] = "application/gzip"; headers["Content-Length"] = str(len(raw))
    calls = []
    class Response(io.BytesIO):
        status = 200
        def __init__(self): super().__init__(raw); self.headers = headers
        def geturl(self): return calls[0][0].full_url
    class Opener:
        def open(self, request, *, timeout): calls.append((request, timeout)); return Response()
    monkeypatch.setattr("urllib.request.build_opener", lambda *handlers: Opener())
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    client = PublicClients(ncbi_email=None, timeout=3)
    host.tools.clients = client
    outcome = execute(host, FAMILY)
    assert outcome["status"] == "completed" and outcome["feedback"] is None, outcome
    receipt = outcome["result"]
    assert receipt == {"acquired": True, "source_ref": outcome["record_refs"][0],
        "data_ref": "artifact_"+hashlib.sha256(raw).hexdigest(), "failure_code": None}
    assert outcome["record_refs"] == [receipt["source_ref"], receipt["data_ref"]]
    assert len(calls) == 1 and calls[0][1] == 3
    assert calls[0][0].full_url == geo.geo_request_spec(FAMILY)["url"]
    source = host.store.get(receipt["source_ref"])
    assert source["provider"] == geo.TOOL and source["origin"] == "external" and source["version"] is None
    assert source["artifact_ref"] == receipt["data_ref"] and source["uri"] == calls[0][0].full_url
    assert host.store.get_artifact(receipt["data_ref"]) == raw
    control = json.loads(host.store.get_artifact(source["request_ref"]))
    assert control["request"] == {"version": geo.REQUEST_VERSION, "arguments": FAMILY, "native_request": {}}
    transport = control["transport"]
    assert transport["request_policy"] == {"timeout_seconds": 3, "automatic_redirects": False}
    assert transport["request"]["method"] == "GET" and transport["request"]["url"] == source["uri"]
    assert transport["body_complete"] is True and transport["response_byte_limit"] == FAMILY["max_bytes"]
    assert transport["retained_body_bytes"] == transport["observed_body_bytes"] == transport["declared_body_bytes"] == len(raw)
    assert canonical(transport["header_items"]) == canonical(list(headers.items()))


def test_tool_contract_is_detached_and_only_describes_an_ordinary_getter():
    value = geo.geo_tool_contract()
    assert value["name"] == geo.TOOL and "file" in value["description"]
    assert value["input_schema"] == geo.ARGUMENTS_SCHEMA
    value["input_schema"].clear()
    assert geo.geo_tool_contract()["input_schema"] == geo.ARGUMENTS_SCHEMA
    assert not hasattr(geo, "GeoService") and not hasattr(geo, "COLLECT")


def test_live_advertised_geo_supplementary_ordinary_acquisition(tmp_path, monkeypatch):
    """One opt-in transfer; a controlled failed receipt is not acquired data."""
    import asyncio
    import os
    from pathlib import Path

    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.runtime import ActionFailure, Workflow
    from test_molecular_acquisition_ordinary import (
        NoModel, _forbidden, _neutral_bookkeeping, _snapshot,
        _live_audit, _live_capture, _live_pin, _live_write,
    )

    if os.environ.get("HMMER_NATIVE_ORACLE_GEO_SUPPLEMENTARY") != "1":
        pytest.skip("requires explicit one-request GEO supplementary acquisition")
    fixture_path = Path(__file__).parent / "fixtures/geo_acquisition/GSE1000_supplementary_advertisement.json"
    advertisement = json.loads(fixture_path.read_bytes())
    assert advertisement["version"] == "geo_retained_supplementary_advertisement_v1"
    assert advertisement["study"] == advertisement["native_record"]["identifier"] == "GSE1000"
    assert advertisement["source_ref"] == "source_8b95795582e399dcb1700a95"
    assert advertisement["raw_file"] == dict(
        artifact_ref="artifact_fccd0054c5d34b5982d9874e0e196af889e0b7cfcadfb693a166662d488a83fe",
        sha256="fccd0054c5d34b5982d9874e0e196af889e0b7cfcadfb693a166662d488a83fe",
        size_bytes=9409370, format="gzip_family_soft")
    assert advertisement["native_record"]["line_1based"] == 39
    assert advertisement["native_record"]["field"] == "Series_supplementary_file"
    assert advertisement["native_record"]["line_without_terminator"] == (
        "!Series_supplementary_file = ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE1nnn/"
        "GSE1000/suppl/GSE1000_RAW.tar")
    assert advertisement["selected_file"] == dict(data_type="supplementary_file", file_name="GSE1000_RAW.tar")
    arguments = dict(study="GSE1000", data_type="supplementary_file",
        file_name="GSE1000_RAW.tar", max_bytes=268435456)
    spec = geo.geo_request_spec(arguments)
    assert spec == dict(service="geo", url=(
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE1nnn/GSE1000/suppl/GSE1000_RAW.tar"),
        params={}, media_type="application/octet-stream", max_bytes=268435456, follow_redirects=False)
    proof_path, store_directory = tmp_path / "GEO_SUPPLEMENTARY_ACQUISITION_PREFIX.json", tmp_path / "store"
    proof = dict(version="geo_supplementary_live_invocation_v1", tool=geo.TOOL, service="geo",
        arguments=arguments, selected_wire_url=spec["url"],
        bounded_attempt=os.environ.get("HMMER529_ATTEMPT"),
        advertisement=advertisement, advertisement_fixture=_live_pin(fixture_path),
        store_directory=str(store_directory), workflow_directory=str(tmp_path / "run"),
        invocation_check_passed=False, native_data_acquired=None, http_calls=[],
        qualification=("One ordinary selected action before any controller observation. The acquisition "
            "verdict is the existing binding's selected-object/capture verdict, not archive-content, "
            "study-file biological identity, matrix, analysis or whole-episode completion."),
        archive_opened=False, analysis_performed=False, same_key_replay_verified=False)
    _live_write(proof_path, proof, exclusive=True)
    actual_http = PublicClients._http

    def http(client, service, url, params, media_type, **kwargs):
        assert proof["http_calls"] == [], "one selected HTTP invocation; no retry or fallback"
        assert dict(service=service, url=url, params=params, media_type=media_type,
            **kwargs) == {**spec, "timeout_seconds": 90}
        proof["http_calls"].append(dict(started=True, service=service, url=url,
            params=deepcopy(params), media_type=media_type, keywords=deepcopy(kwargs)))
        _live_write(proof_path, proof)
        try:
            capture = actual_http(client, service, url, params, media_type, **kwargs)
        except AcquisitionError as error:
            proof["http_calls"][0]["failure"] = dict(code=error.code, phase=error.phase)
            if isinstance(error.snapshot, SourceSnapshot):
                _live_capture(error.snapshot, tmp_path, proof, proof_path)
            _live_write(proof_path, proof)
            raise
        except BaseException as error:
            proof["http_calls"][0]["failure"] = dict(exception_type=type(error).__name__, message=str(error))
            _live_write(proof_path, proof)
            raise
        _live_capture(capture, tmp_path, proof, proof_path)
        return capture

    try:
        with Store(store_directory) as store:
            subject, = store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]
            scope = store.validate_scope(dict(subject_refs=[subject]))
            tools = ToolRegistry(store, clients=PublicClients(ncbi_email=None, timeout=90))
            workflow = Workflow(store, tools, NoModel(), tmp_path / "run", "geo-supplementary-live",
                _forbidden, _neutral_bookkeeping, episode_binding_factories=(), root_role="improvement",
                episode_record_receipts=True, initial_known_record_refs=[])
            caller = workflow.build("improvement", "existing-caller",
                "Retrieve the caller-selected GEO supplementary file for later analysis", scope)
            selection = dict(kind="tool", tool=geo.TOOL, arguments=arguments)
            key = f"{workflow.run_id}:{caller.source.episode_id}:0"
            known_before = set(workflow.receipts.known(caller.source.episode_id))
            proof.update(run_id=workflow.run_id, episode_id=caller.source.episode_id,
                operation_key=key, selection=selection, scope=scope,
                tool_info=deepcopy(tools.catalog(scope)[geo.TOOL]), known_before=sorted(known_before))
            _live_write(proof_path, proof)
            try:
                with monkeypatch.context() as live:
                    live.setattr(PublicClients, "_http", http)
                    live.setattr("urllib.request.urlopen", _forbidden)
                    live.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)
                    live.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
                    live.setattr("gene_annotation_episode.geo_acquisition.parse_geo_soft", _forbidden)
                    live.setattr("tarfile.open", _forbidden)
                    try:
                        asyncio.run(caller.source.execute(selection, 0))
                    except ActionFailure as error:
                        proof["action_failure"] = deepcopy(error.feedback)
            finally:
                _live_audit(store, workflow, caller, proof)
                _live_write(proof_path, proof)
            assert len(proof["http_calls"]) == 1
            action_row, = proof["journal"]["runtime_actions"]
            outcome = json.loads(action_row["result"])
            assert json.loads(action_row["action"]) == selection and action_row["decision_index"] == 0
            assert caller.source.last_outcome == outcome
            receipt = outcome["result"]
            assert type(receipt) is dict and set(receipt) == {"acquired", "source_ref", "data_ref", "failure_code"}
            assert type(receipt["acquired"]) is bool
            proof["native_data_acquired"] = receipt["acquired"]
            failure_codes = {"geo_selected_request_mismatch", "geo_transport_invalid", "geo_transfer_policy_mismatch",
                "geo_http_status_unavailable", "geo_partial_response", "geo_http_not_successful", "geo_capture_incomplete",
                "geo_capture_identity_mismatch", "geo_http_content_encoding_unsupported", "geo_wrong_file_representation",
                "geo_gzip_integrity_failed", "geo_selected_study_identity_conflict", "geo_selected_study_identity_unavailable",
                "geo_selected_platform_identity_conflict", "geo_snapshot_invalid", "geo_timeout_invalid", "geo_arguments_invalid",
                "provider_connection_failed", "provider_request_timeout", "provider_response_byte_limit",
                "provider_body_capture_failed", "data_acquisition_failed", "data_acquisition_publication_incomplete",
                "invalid_tool_input", "adapter_execution_failed"}
            if receipt["acquired"]:
                assert outcome["status"] == "completed" and receipt["failure_code"] is None
                assert receipt["source_ref"] is not None and receipt["data_ref"] is not None
            else:
                assert outcome["status"] in {"partial", "failed", "unavailable", "invalid"}
                assert receipt["data_ref"] is None and receipt["failure_code"] in failure_codes
            capture = proof.get("http_capture")
            references, source = [], None
            if receipt["source_ref"] is not None:
                assert capture is not None
                source = store.get(receipt["source_ref"])
                pin = capture["body_file"]
                assert source["provider"] == geo.TOOL and source["origin"] == "external" and source["version"] is None
                assert source["uri"] == capture["url"] == spec["url"]
                assert source["artifact_ref"] == "artifact_" + pin["sha256"]
                artifact = store.get(source["artifact_ref"])
                assert artifact["sha256"] == pin["sha256"] and artifact["size"] == pin["size_bytes"] <= arguments["max_bytes"]
                retained = _live_pin(store.path / "artifacts" / artifact["sha256"][:2] / artifact["sha256"])
                assert {k: retained[k] for k in ("sha256", "size_bytes")} == {k: pin[k] for k in ("sha256", "size_bytes")}
                control = json.loads(store.get_artifact(source["request_ref"]))
                assert control["request"] == dict(version=geo.REQUEST_VERSION, arguments=arguments, native_request={})
                assert canonical(control["transport"]) == canonical(capture["transport"])
                transport = control["transport"]
                assert transport["request"]["method"] == "GET" and transport["request"]["url"] == spec["url"]
                assert transport["request_policy"] == dict(timeout_seconds=90, automatic_redirects=False)
                assert transport["response_byte_limit"] == arguments["max_bytes"]
                references = [source["id"]]
                if receipt["acquired"]:
                    assert receipt["data_ref"] == source["artifact_ref"]
                    assert transport["status"] == 200 and transport["body_complete"] is True
                    assert transport["observed_body_bytes"] == transport["retained_body_bytes"] == pin["size_bytes"]
                    references.append(source["artifact_ref"])
                proof.update(source=source, source_control=control, retained_capture_file=retained)
            else:
                assert not receipt["acquired"]
                # A transport failure may have no response. An operational
                # publication failure can instead leave captured bytes without
                # a Source; neither case permits inventing a public reference.
                proof["captured_response_without_published_source"] = capture is not None
            assert outcome["record_refs"] == references
            known = set(workflow.receipts.known(caller.source.episode_id))
            assert known - known_before == set(references)
            context = workflow.binding_context(caller.source)
            resolve = workflow.resolver(plain(context.scope), context=context)
            private = set()
            if source is not None:
                private.update([source["request_ref"], *source.get("auxiliary_artifact_refs", [])])
                assert resolve(source["id"], "source") is True
                assert resolve(source["artifact_ref"], "artifact") is receipt["acquired"]
            diagnostic = (outcome.get("feedback") or {}).get("diagnostic_ref")
            if diagnostic is not None:
                private.add(diagnostic)
            assert private.isdisjoint(known)
            for reference in private:
                assert resolve(reference, "artifact") is False
            episode, = proof["journal"]["runtime_episodes"]
            assert episode["state"] == "active" and episode["completion"] is episode["archive"] is None
            for name in ("runtime_observations", "runtime_model_calls", "runtime_forms", "runtime_report_attempts"):
                assert proof["journal"][name] == []
            assert proof["scientific_record_counts"] == dict(observation=0, annotation=0)
            assert caller.request.report_contract is None and workflow.episode_bindings.roles == ()
            operation_row, = proof["tool_operations"]
            saved = json.loads(operation_row["result"])
            assert operation_row["operation_key"] == key and operation_row["name"] == geo.TOOL
            assert operation_row["arguments"] == canonical(arguments) and operation_row["scope"] == canonical(scope)
            assert saved == {k: v for k, v in outcome.items() if k != "pending_work_after_action"}
            before, files = _snapshot(store), {str(p.relative_to(store.path)): _live_pin(p)
                for p in sorted((store.path / "artifacts").rglob("*")) if p.is_file()}
            with monkeypatch.context() as replay:
                replay.setattr(PublicClients, "_http", _forbidden)
                replay.setattr(Store, "get_artifact", _forbidden)
                cached = asyncio.run(workflow.execute(caller.source, geo.TOOL, arguments,
                    decision_index=0, operation_key=key))
            assert cached == saved and _snapshot(store) == before
            assert {str(p.relative_to(store.path)): _live_pin(p)
                for p in sorted((store.path / "artifacts").rglob("*")) if p.is_file()} == files
            proof.update(invocation_check_passed=True, same_key_replay_verified=True,
                newly_received_record_refs=sorted(known - known_before), private_record_refs=sorted(private))
    except BaseException as error:
        proof["test_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        database = store_directory / "state.sqlite3"
        if database.is_file():
            proof["database_file"] = _live_pin(database)
            proof["store_files"] = {str(p.relative_to(store_directory)): _live_pin(p)
                for p in sorted(store_directory.rglob("*")) if p.is_file()}
        _live_write(proof_path, proof)
