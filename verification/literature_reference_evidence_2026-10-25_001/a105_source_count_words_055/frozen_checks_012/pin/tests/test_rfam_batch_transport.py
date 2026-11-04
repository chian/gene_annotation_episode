"""Real loopback HTTP framing; no synthetic fixture is claimed as Rfam output."""
import base64
from contextlib import contextmanager
from email.message import Message
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import threading

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.rfam_batch_transport import RfamBatchHTTP


JOB = "infernal_cmscan-loopback-001"


@contextmanager
def loopback(mode="normal", *, timeout=2):
    requests = []
    release = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_POST(self):
            self.do_GET()

        def do_GET(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            requests.append({"method": self.command, "path": self.path,
                             "headers": list(self.headers.raw_items()), "body": body})
            if mode == "no_response":
                self.close_connection = True
                return
            status = {"redirect": 307, "error": 503}.get(mode, 200)
            self.send_response(status)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("X-Duplicate", "one")
            self.send_header("X-Duplicate", "two")
            if mode == "redirect":
                self.send_header("Location", "https://batch.rfam.org/result/other")
            if mode == "error":
                self.send_header("Retry-After", "7")
            if mode in {"chunked", "chunked_partial"}:
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                self.wfile.write(b"3\r\nabc\r\n" + (b"0\r\n\r\n" if mode == "chunked" else b""))
            else:
                self.send_header("Content-Length", "7" if mode in {"partial", "timeout"} else "3")
                self.end_headers()
                self.wfile.write(b"a\x00b")
            self.wfile.flush()
            if mode == "timeout":
                release.wait(3)
            self.close_connection = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
    thread.start()
    client = RfamBatchHTTP(timeout_seconds=timeout)
    # Only the network endpoint is replaced in this controlled test. The
    # selected production URL/headers are independently checked on the wire.
    client._connection = lambda: http.client.HTTPConnection(*server.server_address, timeout=timeout)
    try:
        yield client, requests
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join()


def assert_capture(snapshot, request):
    capture = snapshot.transport["request"]
    assert capture["method"] == request["method"]
    assert capture["header_items"] == request["headers"]
    assert base64.b64decode(capture["body_base64"]) == request["body"]
    assert capture["body_sha256"] == hashlib.sha256(request["body"]).hexdigest()
    assert capture["body_bytes"] == len(request["body"])
    assert snapshot.transport["http_request_count"] == 1
    assert snapshot.transport["automatic_redirects"] is False
    assert snapshot.transport["automatic_retries"] is False
    assert snapshot.transport["duration_meaning"] == "http_request_turnaround"
    assert snapshot.transport["elapsed_seconds"] >= 0
    assert snapshot.transport["acquisition_started_at"] <= snapshot.retrieved_at


def test_exact_single_sequence_multipart_and_duplicate_response_headers():
    with loopback() as (client, requests):
        snapshot = client.submit("ACgtUN")
    assert len(requests) == 1
    request = requests[0]
    assert_capture(snapshot, request)
    assert request["path"] == "/submit-job"
    assert request["method"] == "POST"
    headers = dict(request["headers"])
    boundary = headers["Content-Type"].split("boundary=", 1)[1]
    expected = (f'--{boundary}\r\nContent-Disposition: form-data; name="sequence_file"; '
                'filename="sequence.seq"\r\nContent-Type: text/plain\r\n\r\n'
                f'ACgtUN\n\r\n--{boundary}--\r\n').encode("ascii")
    assert request["body"] == expected
    assert headers["Accept"] == "application/json"
    assert snapshot.request["sequence_length"] == 6
    assert snapshot.request["sequence_sha256"] == hashlib.sha256(b"ACgtUN").hexdigest()
    assert snapshot.request["file_bytes"] == 7
    assert snapshot.content == b"a\x00b"
    assert snapshot.transport["body_complete"] is True
    assert snapshot.transport["bytes_received"] == 3
    assert snapshot.transport["declared_content_length"] == 3
    assert [(k, v) for k, v in snapshot.transport["header_items"] if k == "X-Duplicate"] == [
        ("X-Duplicate", "one"), ("X-Duplicate", "two")]


def test_submit_file_preserves_exact_multiple_records_and_non_ascii_bytes():
    content = b">same first\r\nACGT\r\n>same second\nACGT\n>binary\n\xff\x00"
    with loopback() as (client, requests):
        snapshot = client.submit_file(content, filename="selected records.fa")
    assert len(requests) == 1
    assert_capture(snapshot, requests[0])
    assert requests[0]["body"].split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n--", 1)[0] == content
    assert snapshot.request["file_sha256"] == hashlib.sha256(content).hexdigest()
    assert snapshot.request["file_bytes"] == len(content)
    assert base64.b64decode(snapshot.request["file_base64"]) == content
    assert "sequence_sha256" not in snapshot.request
    assert snapshot.request["filename"] == "selected records.fa"


@pytest.mark.parametrize("operation,representation,path,accept", [
    ("status", None, "/status/" + JOB, "text/plain"),
    ("result", "json", "/result/" + JOB, "application/json"),
    ("result", "tblout", "/result/" + JOB + "/tblout", "text/plain"),
    ("result", "out", "/result/" + JOB + "/out", "text/plain"),
])
def test_one_original_handle_get(operation, representation, path, accept):
    with loopback() as (client, requests):
        snapshot = (client.status(JOB) if operation == "status" else
                    client.result(JOB, representation=representation))
    assert len(requests) == 1
    assert_capture(snapshot, requests[0])
    assert requests[0]["path"] == path
    assert dict(requests[0]["headers"])["Accept"] == accept
    assert snapshot.url == "https://batch.rfam.org" + path
    assert snapshot.request["job_id"] == JOB
    assert snapshot.request["action"] == ("status" if operation == "status" else "fetch")
    assert snapshot.transport["effective_url"] == snapshot.transport["declared_url"] == snapshot.url


@pytest.mark.parametrize("mode,status,code", [
    ("redirect", 307, "rfam_redirect_not_followed"),
    ("error", 503, "rfam_http_error"),
])
def test_http_failures_are_retained_responses_not_retries(mode, status, code):
    with loopback(mode) as (client, requests):
        snapshot = client.status(JOB)
    assert len(requests) == 1
    assert snapshot.transport["status"] == status
    assert snapshot.transport["failure_code"] == code
    assert snapshot.content == b"a\x00b"
    assert snapshot.transport["body_complete"] is True


@pytest.mark.parametrize("mode", ["partial", "timeout", "chunked_partial"])
def test_received_partial_bytes_survive_eof_or_timeout(mode):
    with loopback(mode, timeout=.1) as (client, requests):
        snapshot = client.result(JOB, representation="json")
    assert len(requests) == 1
    assert snapshot.content == (b"abc" if mode == "chunked_partial" else b"a\x00b")
    assert snapshot.transport["body_complete"] is False
    assert snapshot.transport["body_capture_error"] is not None
    assert snapshot.transport["failure_code"] == "rfam_response_body_incomplete"
    assert snapshot.request["job_id"] == JOB


def test_complete_chunked_body():
    with loopback("chunked") as (client, requests):
        snapshot = client.status(JOB)
    assert len(requests) == 1
    assert snapshot.content == b"abc"
    assert snapshot.transport["body_complete"] is True
    assert snapshot.transport["declared_content_length"] is None


def test_lost_submission_response_is_uncertain_with_original_request():
    with loopback("no_response") as (client, requests):
        with pytest.raises(AcquisitionError) as caught:
            client.submit("ACGT")
    error = caught.value
    assert len(requests) == 1
    assert error.snapshot is None
    assert error.code == "rfam_transport_error"
    assert error.phase == "http_response_headers"
    assert error.submission_outcome == "unknown"
    assert error.diagnostic["request_metadata"]["sequence_sha256"] == hashlib.sha256(b"ACGT").hexdigest()
    assert base64.b64decode(error.diagnostic["request_metadata"]["file_base64"]) == b"ACGT\n"
    assert base64.b64decode(error.diagnostic["request"]["body_base64"]) == requests[0]["body"]


def test_lost_status_response_preserves_original_job_without_submission_claim():
    with loopback("no_response") as (client, requests):
        with pytest.raises(AcquisitionError) as caught:
            client.status(JOB)
    assert len(requests) == 1
    assert caught.value.job_ref == JOB
    assert caught.value.submission_outcome is None
    assert caught.value.diagnostic["request_metadata"]["job_id"] == JOB


def test_connect_failure_before_post_is_not_sent(monkeypatch):
    class Connection:
        def connect(self):
            raise socket.gaierror("synthetic DNS failure")

        def close(self):
            pass

    client = RfamBatchHTTP(timeout_seconds=1)
    monkeypatch.setattr(client, "_connection", Connection)
    with pytest.raises(AcquisitionError) as caught:
        client.submit("ACGT")
    assert caught.value.phase == "connect"
    assert caught.value.submission_outcome == "not_sent"
    assert caught.value.diagnostic["request"]["method"] == "POST"


def test_incomplete_read_exception_preserves_exception_partial(monkeypatch):
    class Response:
        headers = Message()
        headers["Content-Length"] = "7"
        status, reason, chunked = 200, "OK", False
        chunk_left = None

        def read1(self, amount):
            raise http.client.IncompleteRead(b"prefix", 1)

        def close(self):
            pass

    class Connection:
        def connect(self): pass
        def putrequest(self, *args, **kwargs): pass
        def putheader(self, *args): pass
        def endheaders(self, body): pass
        def getresponse(self): return Response()
        def close(self): pass

    client = RfamBatchHTTP(timeout_seconds=1)
    monkeypatch.setattr(client, "_connection", Connection)
    snapshot = client.status(JOB)
    assert snapshot.content == b"prefix"
    assert snapshot.transport["body_complete"] is False
    assert snapshot.transport["body_capture_error"] == "IncompleteRead"


@pytest.mark.parametrize("value", [0, -1, True, None, "2", float("nan"), float("inf")])
def test_invalid_timeout(value):
    with pytest.raises(ValueError, match="rfam_transport_timeout_invalid"):
        RfamBatchHTTP(timeout_seconds=value)


@pytest.mark.parametrize("job", ["", "infernal_cmscan-", "../bad", "infernal_cmscan-a?b", "infernal_cmscan-a#b", "https://elsewhere", None, 1])
def test_invalid_handle_never_connects(job, monkeypatch):
    client = RfamBatchHTTP(timeout_seconds=1)
    monkeypatch.setattr(client, "_connection", lambda: pytest.fail("must not connect"))
    for call in (lambda: client.status(job), lambda: client.result(job, representation="json")):
        with pytest.raises(AcquisitionError, match="rfam_job_identity_invalid"):
            call()


@pytest.mark.parametrize("filename", ["", "a\nb", "a\rb", 'a"b', "a/b", "a\\b", "é.fa"])
def test_invalid_filename_never_connects(filename, monkeypatch):
    client = RfamBatchHTTP(timeout_seconds=1)
    monkeypatch.setattr(client, "_connection", lambda: pytest.fail("must not connect"))
    with pytest.raises(AcquisitionError) as caught:
        client.submit_file(b"ACGT", filename=filename)
    assert caught.value.submission_outcome == "not_sent"


def test_invalid_sequence_or_representation_never_connects(monkeypatch):
    client = RfamBatchHTTP(timeout_seconds=1)
    monkeypatch.setattr(client, "_connection", lambda: pytest.fail("must not connect"))
    for sequence in ("", "ACGé", b"ACGT", None):
        with pytest.raises(AcquisitionError, match="rfam_sequence_invalid"):
            client.submit(sequence)
    with pytest.raises(AcquisitionError, match="rfam_request_invalid"):
        client.result(JOB, representation="../../other")
    with pytest.raises(AcquisitionError, match="rfam_request_invalid"):
        client.submit_file("ACGT", filename="x.fa")


def test_transport_does_not_own_replay_or_choose_extra_operations():
    with loopback() as (client, requests):
        first = client.status(JOB)
        second = client.status(JOB)
    assert len(requests) == 2  # Two explicitly selected calls, one request each.
    assert first.request == second.request
    assert all(row["path"] == "/status/" + JOB for row in requests)
