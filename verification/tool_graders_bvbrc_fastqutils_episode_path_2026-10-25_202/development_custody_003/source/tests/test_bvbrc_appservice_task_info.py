from email.message import Message
from http.client import IncompleteRead
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
from threading import Thread
import urllib.error

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.bvbrc_analysis_transport import BVBRCAnalysisClient


ENDPOINT = "https://controlled.invalid/services/app_service"


class Response:
    status = 200

    def __init__(self, url, content=b"native\x00\xff\n", *, headers=None, error=None):
        self.url, self.content, self.error = url, content, error
        self.headers = Message()
        for key, value in (headers or {"Content-Type": "application/octet-stream"}).items():
            self.headers[key] = value

    def geturl(self):
        return self.url

    def read(self):
        if self.error is not None:
            raise self.error
        return self.content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def install(monkeypatch, responder):
    calls = []

    class Opener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            return responder(request)

    monkeypatch.setattr("urllib.request.build_opener", lambda *handlers: Opener())
    return calls


@pytest.mark.parametrize("file", ["stdout", "stderr", "job_result_id", "job_result_folder"])
def test_task_info_is_one_exact_configured_endpoint_get(monkeypatch, file):
    calls = install(monkeypatch, lambda req: Response(req.full_url))
    monkeypatch.setenv("BVBRC_TEST_ONLY_AUTH", "OAuth controlled-token")
    client = BVBRCAnalysisClient({"AppService": ENDPOINT}, timeout=17,
                                 authorization_env="BVBRC_TEST_ONLY_AUTH")
    snapshot = client.task_info("task_12-3", file)
    assert len(calls) == 1
    request, timeout = calls[0]
    assert timeout == 17
    assert request.get_method() == "GET"
    assert request.full_url == ENDPOINT + "/task_info/task_12-3/" + file
    assert request.data is None
    assert request.headers["Authorization"] == "OAuth controlled-token"
    assert snapshot.request == {"kind": "task_info", "task_id": "task_12-3", "file": file}
    assert snapshot.content == b"native\x00\xff\n"
    assert snapshot.transport["body_complete"] is True
    assert snapshot.transport["automatic_redirects"] is False
    assert ["Authorization", "<redacted>"] in snapshot.transport["request"]["headers"]


def test_old_task_log_request_identity_and_operands_are_unchanged(monkeypatch):
    calls = install(monkeypatch, lambda req: Response(req.full_url))
    client = BVBRCAnalysisClient({"AppService": ENDPOINT})
    snapshot = client.task_log("legacy task", "stdout")
    assert snapshot.request == {"kind": "task_log", "task_id": "legacy task", "stream": "stdout"}
    assert calls[0][0].full_url.endswith("/task_info/legacy%20task/stdout")
    with pytest.raises(ValueError, match="bvbrc_task_log_selection_invalid"):
        client.task_log("12", "job_result_id")
    assert len(calls) == 1


@pytest.mark.parametrize("task_id,file", [("12", "other"), ("../12", "stdout"), ("12/x", "stdout"),
    ("x\n", "stdout"), ("", "stdout"), (True, "stdout"), ("12", []), ("..", "stdout"), ("a b", "stdout")])
def test_invalid_new_operands_make_no_call(monkeypatch, task_id, file):
    calls = install(monkeypatch, lambda req: pytest.fail("unexpected request"))
    client = BVBRCAnalysisClient({"AppService": ENDPOINT})
    with pytest.raises(ValueError, match="bvbrc_task_info_selection_invalid"):
        client.task_info(task_id, file)
    assert calls == []


def test_missing_configuration_or_authentication_does_not_issue(monkeypatch):
    calls = install(monkeypatch, lambda req: pytest.fail("unexpected request"))
    with pytest.raises(AcquisitionError, match="endpoint_unconfigured"):
        BVBRCAnalysisClient({"Workspace": "https://controlled.invalid/workspace"}).task_info("12", "stdout")
    monkeypatch.delenv("BVBRC_TEST_ABSENT_AUTH", raising=False)
    with pytest.raises(AcquisitionError, match="authorization_unavailable"):
        BVBRCAnalysisClient({"AppService": ENDPOINT}, authorization_env="BVBRC_TEST_ABSENT_AUTH").task_info("12", "stdout")
    assert calls == []


def test_partial_and_error_replies_retain_exact_bytes_without_retry(monkeypatch):
    calls = install(monkeypatch, lambda req: Response(req.full_url, error=IncompleteRead(b"prefix\xff", 9)))
    client = BVBRCAnalysisClient({"AppService": ENDPOINT})
    with pytest.raises(AcquisitionError) as captured:
        client.task_info("12", "stderr")
    assert captured.value.snapshot.content == b"prefix\xff"
    assert captured.value.snapshot.transport["body_complete"] is False
    assert len(calls) == 1

    def error(req):
        raise urllib.error.HTTPError(req.full_url, 404, "missing selected file", Message(), io.BytesIO(b"missing\x00body"))

    calls = install(monkeypatch, error)
    with pytest.raises(AcquisitionError) as captured:
        client.task_info("12", "job_result_id")
    assert captured.value.snapshot.content == b"missing\x00body"
    assert captured.value.snapshot.transport["status"] == 404
    assert len(calls) == 1


def test_new_task_info_uses_real_http_framing_against_controlled_local_endpoint():
    calls = []
    content = b"11111111-2222-3333-4444-555555555555\n"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            calls.append({"path": self.path, "range": self.headers.get("Range")})
            self.send_response(200)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
    thread.start()
    try:
        endpoint = f"http://127.0.0.1:{server.server_port}/exact-service"
        snapshot = BVBRCAnalysisClient({"AppService": endpoint}).task_info("123", "job_result_id")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    assert calls == [{"path": "/exact-service/task_info/123/job_result_id", "range": None}]
    assert snapshot.content == content
    assert snapshot.transport["received_body_bytes"] == len(content)
    assert snapshot.transport["body_complete"] is True
