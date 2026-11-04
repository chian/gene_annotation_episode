"""Native HTTP transport against a controlled local server, not live BV-BRC."""
from contextlib import contextmanager
from dataclasses import asdict
from email.message import Message
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
import urllib.error

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.bvbrc_analysis_protocol import prepare_rpc_request
from gene_annotation_episode.bvbrc_analysis_transport import BVBRCAnalysisClient


@contextmanager
def server(body=b'{"result":[[]],"id":"test","version":"1.1"}', *, status=200, headers=None):
    received = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self):
            length = int(self.headers.get('Content-Length', 0))
            received.append({'method': self.command, 'path': self.path,
                'headers': dict(self.headers), 'body': self.rfile.read(length)})
            self.send_response(status)
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            if not any(key.lower() == 'content-length' for key in (headers or {})):
                self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = do_PUT = respond
    host = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=host.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{host.server_port}', received
    finally:
        host.shutdown()
        host.server_close()
        thread.join()


def test_rpc_native_body_identity_and_header_secrets(monkeypatch):
    secret = 'OAuth fixture-only-private-header'
    monkeypatch.setenv('BVBRC_TEST_HEADER', secret)
    request = prepare_rpc_request('Workspace.ls', [{'paths': ['/owner/work/α']}], request_id='test')
    with server(headers={'Content-Type': 'application/json', 'Set-Cookie': 'fixture-private-cookie'}) as (url, calls):
        client = BVBRCAnalysisClient({'Workspace': url + '/rpc'}, authorization_env='BVBRC_TEST_HEADER')
        snapshot = client.rpc(request)
    assert len(calls) == 1 and calls[0]['method'] == 'POST'
    assert calls[0]['headers']['Authorization'] == secret
    assert json.loads(calls[0]['body']) == request
    assert snapshot.request == {'kind': 'rpc', 'rpc': request}
    assert snapshot.transport['request']['body_sha256'] == hashlib.sha256(calls[0]['body']).hexdigest()
    assert snapshot.transport['request']['body_bytes'] == len(calls[0]['body'])
    assert snapshot.transport['body_complete'] is True
    assert snapshot.transport['headers']['set-cookie'] == '<redacted>'
    assert snapshot.transport['duration_measure'] == 'client_http_request_turnaround'
    assert snapshot.transport['http_turnaround_seconds'] >= 0
    fields = asdict(snapshot); fields['content'] = snapshot.content.decode()
    retained = json.dumps(fields)
    assert secret not in retained and 'fixture-private-cookie' not in retained
    assert snapshot.service == 'bvbrc_analysis'


@pytest.mark.parametrize('stream', ['stdout', 'stderr'])
def test_task_log_is_one_full_selected_stream(stream):
    with server(b'line one\nline two\n') as (url, calls):
        snapshot = BVBRCAnalysisClient({'AppService': url + '/services/app_service'}).task_log('task-123', stream)
    assert len(calls) == 1
    assert calls[0]['path'] == '/services/app_service/task_info/task-123/' + stream
    assert 'Range' not in calls[0]['headers']
    assert snapshot.content == b'line one\nline two\n'
    assert snapshot.request == {'kind': 'task_log', 'task_id': 'task-123', 'stream': stream}


@pytest.mark.parametrize('status,body,headers', [
    (200, b'abcdef', {}),
    (206, b'cde', {'Content-Range': 'bytes 2-4/6'}),
])
def test_download_retains_actual_range_or_ignored_range_without_trim(monkeypatch, status, body, headers):
    monkeypatch.setenv('BVBRC_TEST_HEADER', 'fixture-only-secret')
    with server(body, status=status, headers=headers) as (url, calls):
        client = BVBRCAnalysisClient({'Workspace': url + '/workspace'}, authorization_env='BVBRC_TEST_HEADER')
        snapshot = client.download(url + '/download?key=fixture-capability', byte_range=(2, 4))
    assert len(calls) == 1 and calls[0]['headers']['Range'] == 'bytes=2-4'
    assert 'Authorization' not in calls[0]['headers']
    assert snapshot.content == body and snapshot.transport['status'] == status
    assert snapshot.request['requested_byte_range'] == [2, 4]
    assert snapshot.transport['headers'].get('content-range') == headers.get('Content-Range')


def test_upload_is_put_upload_part_and_exact_byte_hashes(monkeypatch):
    monkeypatch.setenv('BVBRC_TEST_HEADER', 'OAuth fixture-only-shock')
    content = b'\x00\xffACGT\n'
    native = b'{"status":200,"data":{"id":"shock-node-1"},"error":null}'
    with server(native) as (url, calls):
        client = BVBRCAnalysisClient({'Workspace': 'https://workspace.fixture/rpc'},
            authorization_env='BVBRC_TEST_HEADER', authorization_origins=[url])
        snapshot = client.upload(url + '/node/shock-node-1', content, filename='séquence.fa')
    call, = calls
    assert call['method'] == 'PUT' and call['path'] == '/node/shock-node-1'
    assert call['headers']['Authorization'] == 'OAuth fixture-only-shock'
    assert b'name="upload"' in call['body'] and 'filename="séquence.fa"'.encode() in call['body']
    boundary = snapshot.request['multipart_boundary'].encode()
    assert call['body'].startswith(b'--' + boundary + b'\r\n')
    assert call['body'].endswith(b'\r\n--' + boundary + b'--\r\n')
    assert content in call['body']
    assert snapshot.request['input_bytes'] == len(content)
    assert snapshot.request['input_sha256'] == hashlib.sha256(content).hexdigest()
    assert snapshot.transport['request']['body_sha256'] == hashlib.sha256(call['body']).hexdigest()
    assert snapshot.transport['request']['body_bytes'] == len(call['body'])
    assert snapshot.content == native


@pytest.mark.parametrize('status', [403, 503, 302])
def test_http_error_retains_body_and_does_not_retry_or_redirect(status):
    native = b'<html>controlled service failure</html>'
    with server(native, status=status, headers={'Location': '/must-not-follow', 'Retry-After': '23'}) as (url, calls):
        client = BVBRCAnalysisClient({'AppService': url + '/rpc'})
        with pytest.raises(AcquisitionError) as raised:
            client.rpc(prepare_rpc_request('AppService.enumerate_apps', [], request_id='test'))
    assert len(calls) == 1
    error = raised.value
    assert error.code == ('bvbrc_redirect_not_followed' if status == 302 else 'bvbrc_http_' + str(status))
    assert error.snapshot.content == native and error.snapshot.transport['status'] == status
    assert error.retry_after == 23 and error.submission_outcome == 'unknown'
    assert error.snapshot.transport['automatic_redirects'] is False


def test_truncated_body_retains_received_bytes():
    with server(b'abc', headers={'Content-Length': '10'}) as (url, calls):
        with pytest.raises(AcquisitionError) as raised:
            BVBRCAnalysisClient({'Workspace': url}).download(url + '/download')
    assert len(calls) == 1
    assert raised.value.code == 'bvbrc_response_body_incomplete'
    assert raised.value.snapshot.content == b'abc'
    assert raised.value.snapshot.transport['body_complete'] is False
    assert raised.value.snapshot.transport['received_body_bytes'] == 3


def test_reader_content_length_mismatch_remains_explicit(monkeypatch):
    class Response:
        status = 200
        headers = Message()
        headers['Content-Length'] = '2'
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def geturl(self): return 'https://workspace.fixture/download'
        def read(self): return b'abc'
    monkeypatch.setattr('urllib.request.OpenerDirector.open', lambda *a, **k: Response())
    with pytest.raises(AcquisitionError) as raised:
        BVBRCAnalysisClient({'Workspace': 'https://workspace.fixture'}).download('https://workspace.fixture/download')
    assert raised.value.snapshot.content == b'abc'
    assert raised.value.snapshot.transport['body_capture_error'] == 'content_length_mismatch'


def test_missing_endpoint_auth_and_unconfigured_auth_origin_send_nothing(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('invalid preparation attempted a request')
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    client = BVBRCAnalysisClient({'Workspace': 'https://workspace.fixture'}, authorization_env='BVBRC_TEST_MISSING')
    monkeypatch.delenv('BVBRC_TEST_MISSING', raising=False)
    with pytest.raises(AcquisitionError, match='endpoint_unconfigured'):
        client.task_log('123', 'stdout')
    with pytest.raises(AcquisitionError, match='authorization_unavailable'):
        client.rpc(prepare_rpc_request('Workspace.ls', [{'paths': ['/u/w']}], request_id='test'))
    monkeypatch.setenv('BVBRC_TEST_MISSING', 'fixture-only-secret')
    with pytest.raises(AcquisitionError, match='authorization_origin_unconfigured') as raised:
        client.upload('https://unconfigured.fixture/node/id', b'AC', filename='x.fa')
    assert raised.value.submission_outcome == 'not_sent'


def test_connection_failure_is_one_attempt_with_unknown_outcome(monkeypatch):
    calls = []
    def unavailable(self, request, *, timeout):
        calls.append(request)
        raise urllib.error.URLError(TimeoutError())
    monkeypatch.setattr('urllib.request.OpenerDirector.open', unavailable)
    with pytest.raises(AcquisitionError) as raised:
        BVBRCAnalysisClient({'Workspace': 'https://workspace.fixture'}).upload(
            'https://workspace.fixture/node/id', b'AC', filename='x.fa')
    assert len(calls) == 1 and raised.value.snapshot is None
    assert raised.value.submission_outcome == 'unknown'


@pytest.mark.parametrize('byte_range', [(-1, 1), (2, 1), (True, 2), [0, 1], (0, False)])
def test_invalid_range_does_not_issue_a_request(byte_range, monkeypatch):
    monkeypatch.setattr('urllib.request.OpenerDirector.open', lambda *a, **k: pytest.fail('unexpected request'))
    with pytest.raises(ValueError, match='range_invalid'):
        BVBRCAnalysisClient({'Workspace': 'https://workspace.fixture'}).download(
            'https://workspace.fixture/download', byte_range=byte_range)
