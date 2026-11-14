"""One caller-selected BV-BRC native HTTP operation, retaining actual bytes.

This is transport, not an episode or a retry/polling workflow. Native response
decoding, task/object possession and scientific grading belong to its callers.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from .acquisition import AcquisitionError, SourceSnapshot


SERVICE = 'bvbrc_analysis'
NAMESPACES = frozenset({'AppService', 'Workspace', 'Minhash'})
_SECRET_HEADERS = frozenset({'authorization', 'proxy-authorization', 'cookie', 'set-cookie'})


def _url(value, *, endpoint=False):
    if not isinstance(value, str) or any(char in value for char in ('\r', '\n', '\x00')):
        raise ValueError('bvbrc_native_url_invalid')
    parts = urllib.parse.urlsplit(value)
    if (parts.scheme not in {'http', 'https'} or not parts.hostname or parts.fragment
            or parts.username is not None or parts.password is not None
            or endpoint and parts.query):
        raise ValueError('bvbrc_native_url_invalid')
    return value


def _headers(value):
    return [[name, '<redacted>' if name.lower() in _SECRET_HEADERS else content]
            for name, content in (value.items() if value is not None else ())]


def _origin(url):
    parts = urllib.parse.urlsplit(_url(url))
    return parts.scheme.lower(), parts.hostname.lower(), parts.port or (443 if parts.scheme == 'https' else 80)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


class BVBRCAnalysisClient:
    """Explicit endpoints and optional caller-owned authorization header."""

    def __init__(self, endpoints, *, timeout=90, authorization_env=None,
                 authorization_origins=()):
        if (not isinstance(endpoints, dict) or not endpoints or set(endpoints) - NAMESPACES
                or any(not isinstance(key, str) for key in endpoints)):
            raise ValueError('bvbrc_native_endpoints_required')
        self.endpoints = {name: _url(value, endpoint=True) for name, value in endpoints.items()}
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('bvbrc_native_timeout_invalid')
        if authorization_env is not None and (not isinstance(authorization_env, str)
                or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', authorization_env) is None):
            raise ValueError('bvbrc_authorization_environment_invalid')
        self.timeout, self.authorization_env = timeout, authorization_env
        if not isinstance(authorization_origins, (tuple, list)):
            raise ValueError('bvbrc_authorization_origins_invalid')
        self.authorization_origins = {_origin(value) for value in self.endpoints.values()}
        for origin in authorization_origins:
            parsed = urllib.parse.urlsplit(_url(origin, endpoint=True))
            if parsed.path not in ('', '/'):
                raise ValueError('bvbrc_authorization_origin_must_not_have_path')
            self.authorization_origins.add(_origin(origin))

    def _endpoint(self, namespace):
        if namespace not in self.endpoints:
            raise AcquisitionError('bvbrc_native_endpoint_unconfigured',
                phase='configuration', submission_outcome='not_sent')
        return self.endpoints[namespace]

    def rpc(self, request):
        from .bvbrc_analysis_protocol import prepare_rpc_request
        if not isinstance(request, dict) or set(request) != {'version', 'method', 'params', 'id'}:
            raise ValueError('bvbrc_prepared_rpc_request_invalid')
        checked = prepare_rpc_request(request['method'], request['params'], request_id=request['id'])
        if checked != request:
            raise ValueError('bvbrc_prepared_rpc_request_conflict')
        namespace = request['method'].split('.', 1)[0]
        address = self._endpoint(namespace)
        body = json.dumps(request, ensure_ascii=False, sort_keys=True,
            separators=(',', ':'), allow_nan=False).encode('utf-8')
        return self._request(address, 'POST', {'kind': 'rpc', 'rpc': deepcopy(request)},
            body=body, content_type='application/json')

    def task_log(self, task_id, stream):
        if (not isinstance(task_id, str) or not task_id or stream not in {'stdout', 'stderr'}
                or any(char in task_id for char in ('\r', '\n', '\x00', '/', '\\'))):
            raise ValueError('bvbrc_task_log_selection_invalid')
        address = self._endpoint('AppService').rstrip('/') + '/task_info/' + (
            urllib.parse.quote(task_id, safe='')) + '/' + stream
        return self._request(address, 'GET', {'kind': 'task_log', 'task_id': task_id,
            'stream': stream})

    def task_info(self, task_id: str, file: str) -> SourceSnapshot:
        """Acquire one explicit native task-info file from the configured service.

        The existing task_log request identity and accepted operands stay intact.
        This operation neither queries task status nor searches for an object.
        """
        if (type(task_id) is not str or re.fullmatch(r'[A-Za-z0-9_-]+', task_id) is None
                or type(file) is not str
                or file not in {'stdout', 'stderr', 'job_result_id', 'job_result_folder'}):
            raise ValueError('bvbrc_task_info_selection_invalid')
        address = self._endpoint('AppService').rstrip('/') + '/task_info/' + (
            urllib.parse.quote(task_id, safe='')) + '/' + file
        return self._request(address, 'GET', {'kind': 'task_info', 'task_id': task_id,
            'file': file})

    def download(self, url, *, byte_range=None):
        address = _url(url)
        headers = {}
        if byte_range is not None:
            if (not isinstance(byte_range, tuple) or len(byte_range) != 2
                    or type(byte_range[0]) is not int or byte_range[0] < 0
                    or byte_range[1] is not None and (type(byte_range[1]) is not int
                        or byte_range[1] < byte_range[0])):
                raise ValueError('bvbrc_download_range_invalid')
            start, end = byte_range
            headers['Range'] = f'bytes={start}-' + ('' if end is None else str(end))
        return self._request(address, 'GET', {'kind': 'download', 'url': address,
            'requested_byte_range': None if byte_range is None else list(byte_range)},
            headers=headers, authorize=False)

    def upload(self, node_url, content, *, filename):
        address = _url(node_url)
        if not isinstance(content, bytes):
            raise ValueError('bvbrc_upload_bytes_required')
        if (not isinstance(filename, str) or not filename
                or any(char in filename for char in ('\r', '\n', '\x00', '"', '/', '\\'))):
            raise ValueError('bvbrc_upload_filename_invalid')
        input_hash = hashlib.sha256(content).hexdigest()
        boundary = 'gene-annotation-' + hashlib.sha256(
            filename.encode('utf-8') + b'\x00' + bytes.fromhex(input_hash)).hexdigest()
        if boundary.encode('ascii') in content:
            raise ValueError('bvbrc_multipart_boundary_conflict')
        prefix = (f'--{boundary}\r\nContent-Disposition: form-data; name="upload"; '
            f'filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode('utf-8')
        suffix = f'\r\n--{boundary}--\r\n'.encode('ascii')
        # Send the three existing byte segments without duplicating a large
        # supplied artifact into one additional multipart byte string.
        segments = (prefix, content, suffix)
        body_hash = hashlib.sha256()
        for segment in segments:
            body_hash.update(segment)
        return self._request(address, 'PUT', {'kind': 'upload', 'node_url': address,
            'filename': filename, 'input_bytes': len(content), 'input_sha256': input_hash,
            'multipart_field': 'upload', 'multipart_boundary': boundary}, body=iter(segments),
            body_length=sum(map(len, segments)), body_sha256=body_hash.hexdigest(),
            content_type='multipart/form-data; boundary=' + boundary)

    def _request(self, address, method, operands, *, headers=None, body=None,
                 content_type=None, body_length=None, body_sha256=None, authorize=True):
        outgoing = {'User-Agent': 'gene-annotation-episode/0.2', 'Accept': '*/*', **(headers or {})}
        if content_type is not None:
            outgoing['Content-Type'] = content_type
        if body is not None:
            if isinstance(body, bytes):
                body_length, body_sha256 = len(body), hashlib.sha256(body).hexdigest()
            outgoing['Content-Length'] = str(body_length)
        if authorize and self.authorization_env is not None:
            if _origin(address) not in self.authorization_origins:
                raise AcquisitionError('bvbrc_authorization_origin_unconfigured',
                    phase='configuration', submission_outcome='not_sent')
            authorization = os.environ.get(self.authorization_env)
            if not authorization or any(char in authorization for char in ('\r', '\n', '\x00')):
                raise AcquisitionError('bvbrc_authorization_unavailable',
                    phase='configuration', submission_outcome='not_sent')
            outgoing['Authorization'] = authorization
        native = urllib.request.Request(address, data=body, method=method, headers=outgoing)
        recorded = {'method': method, 'url': address, 'headers': _headers(native.headers),
            'body_bytes': body_length, 'body_sha256': body_sha256}
        opener = urllib.request.build_opener(_NoRedirect())
        started = time.perf_counter()

        def capture(response, status, *, http_error=False):
            items = _headers(response.headers)
            observed_headers = {key.lower(): value for key, value in items}
            transport = {'status': status, 'headers': observed_headers, 'header_items': items,
                'effective_url': response.geturl(), 'request': recorded,
                'automatic_redirects': False, 'representation': 'http_response_bytes',
                'body_complete': True, 'http_error_response': http_error}
            failure = None
            try:
                content = response.read()
            except Exception as error:
                content = getattr(error, 'partial', b'')
                if not isinstance(content, bytes):
                    content = b''
                transport.update(body_complete=False, body_capture_error=type(error).__name__)
                failure = error
            if not isinstance(content, bytes):
                transport.update(body_complete=False, body_capture_error='non_bytes_response')
                content, failure = b'', ValueError('non_bytes_response')
            length = observed_headers.get('content-length')
            if (transport['body_complete'] and length is not None and length.isdecimal()
                    and not observed_headers.get('transfer-encoding') and len(content) != int(length)):
                transport.update(body_complete=False, body_capture_error='content_length_mismatch')
                failure = ValueError('content_length_mismatch')
            transport.update(received_body_bytes=len(content),
                http_turnaround_seconds=time.perf_counter() - started,
                duration_measure='client_http_request_turnaround')
            snapshot = SourceSnapshot(SERVICE, address, deepcopy(operands),
                datetime.now(timezone.utc).isoformat(), content,
                observed_headers.get('content-type', 'application/octet-stream'), transport)
            if failure is not None:
                raise AcquisitionError('bvbrc_response_body_incomplete', snapshot=snapshot,
                    phase='http_response', submission_outcome='unknown') from failure
            return snapshot

        try:
            with opener.open(native, timeout=self.timeout) as response:
                return capture(response, response.status)
        except urllib.error.HTTPError as error:
            try:
                snapshot = capture(error, error.code, http_error=True)
            finally:
                error.close()
            retry = snapshot.transport['headers'].get('retry-after')
            raise AcquisitionError('bvbrc_redirect_not_followed' if 300 <= error.code < 400
                else 'bvbrc_http_' + str(error.code), snapshot=snapshot, phase='http_response',
                submission_outcome='unknown',
                retry_after=float(retry) if retry and retry.isdecimal() else None) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            # Absence of a response does not establish whether a remote
            # create/upload/submission executed. The owner chooses recovery.
            raise AcquisitionError('bvbrc_native_transport_failed', phase='http_request',
                submission_outcome='unknown', diagnostic={
                    'exception_type': type(error).__name__}) from error


__all__ = ['BVBRCAnalysisClient', 'SERVICE']
