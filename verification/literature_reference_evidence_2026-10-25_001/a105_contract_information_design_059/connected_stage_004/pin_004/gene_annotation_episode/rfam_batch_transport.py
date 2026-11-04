"""One selected HTTP request to the public Rfam batch service.

This module transports supplied bytes. It does not parse scientific output,
resolve sequence subjects, interpret job status, or own continuation. A body
read loop drains one response; it never initiates another HTTP request.
"""
from __future__ import annotations

import base64
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import http.client
import math
import re
import time
from typing import Literal
from urllib.parse import urlsplit
import uuid

from .acquisition import AcquisitionError, SourceSnapshot
from .rfam_discovery import BASE_URL, result_url


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class RfamBatchHTTP:
    """Stateless, fixed-origin transport; each call sends at most one request.

    ``timeout_seconds`` limits a blocking network operation. It is not a remote
    job deadline. There is no connection pool, automatic retry, redirect,
    status interpretation, or saved-job lookup. The caller owns durable replay.
    """

    def __init__(self, *, timeout_seconds: float):
        if (type(timeout_seconds) not in (int, float)
                or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
            raise ValueError("rfam_transport_timeout_invalid")
        self.timeout_seconds = float(timeout_seconds)

    def submit(self, sequence: str) -> SourceSnapshot:
        """Submit the supplied ASCII sequence followed by exactly one newline."""
        if not isinstance(sequence, str) or not sequence:
            raise AcquisitionError("rfam_sequence_invalid", phase="local_preflight",
                                   submission_outcome="not_sent")
        try:
            encoded = sequence.encode("ascii")
        except UnicodeEncodeError as error:
            raise AcquisitionError("rfam_sequence_invalid", phase="local_preflight",
                                   submission_outcome="not_sent") from error
        identity = {"sequence_sha256": _digest(encoded), "sequence_length": len(encoded)}
        try:
            snapshot = self.submit_file(encoded + b"\n", filename="sequence.seq")
        except AcquisitionError as error:
            # An uncertain POST retains the same frozen input even without an
            # HTTP response or known remote handle. This does not permit retry.
            if error.diagnostic is not None:
                error.diagnostic.setdefault("request_metadata", {}).update(identity)
            raise
        return replace(snapshot, request={**snapshot.request, **identity})

    def submit_file(self, content: bytes, *, filename: str) -> SourceSnapshot:
        """Submit one exact file part, without interpreting FASTA or its records."""
        if (not isinstance(content, bytes) or not isinstance(filename, str)
                or not filename or re.fullmatch(r'[\x20-\x7e]+', filename) is None
                or any(character in filename for character in '\\"/')):
            raise AcquisitionError("rfam_request_invalid", phase="local_preflight",
                                   submission_outcome="not_sent")
        boundary = "gene-annotation-" + uuid.uuid4().hex
        if boundary.encode("ascii") in content:
            raise AcquisitionError("rfam_request_invalid", phase="local_preflight",
                                   submission_outcome="not_sent")
        prefix = (f'--{boundary}\r\nContent-Disposition: form-data; name="sequence_file"; '
                  f'filename="{filename}"\r\nContent-Type: text/plain\r\n\r\n').encode("ascii")
        body = prefix + content + f"\r\n--{boundary}--\r\n".encode("ascii")
        metadata = {"action": "submit", "job_id": None, "representation": "json",
                    "multipart_field": "sequence_file", "filename": filename,
                    "file_sha256": _digest(content), "file_bytes": len(content),
                    "file_base64": base64.b64encode(content).decode("ascii")}
        return self._request("POST", BASE_URL + "/submit-job", body=body,
                             accept="application/json", metadata=metadata,
                             content_type="multipart/form-data; boundary=" + boundary)

    def status(self, job_id: str) -> SourceSnapshot:
        self._validate_job(job_id)
        return self._request("GET", BASE_URL + "/status/" + job_id, body=None,
                             accept="text/plain", metadata={"action": "status",
                             "job_id": job_id, "representation": "status"})

    def result(self, job_id: str, *, representation: Literal["json", "tblout", "out"]) -> SourceSnapshot:
        self._validate_job(job_id)
        if representation not in ("json", "tblout", "out"):
            raise AcquisitionError("rfam_request_invalid", phase="local_preflight",
                                   job_ref=job_id)
        address = result_url(job_id) + ("/" + representation if representation != "json" else "")
        return self._request("GET", address, body=None,
                             accept="application/json" if representation == "json" else "text/plain",
                             metadata={"action": "fetch", "job_id": job_id,
                                       "representation": representation})

    @staticmethod
    def _validate_job(job_id: str) -> None:
        try:
            result_url(job_id)
        except ValueError as error:
            raise AcquisitionError("rfam_job_identity_invalid", phase="local_preflight") from error

    def _connection(self):
        # Explicit HTTPConnection request construction below captures every
        # actual header, including headers commonly added by higher-level
        # clients. HTTPSConnection verifies the provider's TLS certificate.
        return http.client.HTTPSConnection("batch.rfam.org", timeout=self.timeout_seconds)

    def _request(self, method, address, *, body, accept, metadata, content_type=None):
        parsed = urlsplit(address)
        if (parsed.scheme != "https" or parsed.netloc != "batch.rfam.org"
                or parsed.query or parsed.fragment):
            raise AcquisitionError("rfam_request_invalid", phase="local_preflight",
                                   submission_outcome="not_sent" if method == "POST" else None)
        header_items = [("Host", "batch.rfam.org"), ("Accept", accept),
                        ("Accept-Encoding", "identity"),
                        ("User-Agent", "gene-annotation-episode/0.2"),
                        ("Connection", "close")]
        if body is not None:
            header_items.extend([("Content-Type", content_type), ("Content-Length", str(len(body)))])
        exact_request = {"method": method, "url": address,
                         "headers": dict(header_items), "header_items": header_items,
                         "body_base64": base64.b64encode(body or b"").decode("ascii"),
                         "body_sha256": _digest(body or b""), "body_bytes": len(body or b"")}
        started_at, started_clock = _now(), time.monotonic()
        connection, response = None, None
        phase = "connect"
        try:
            connection = self._connection()
            connection.connect()
            phase = "http_request"
            connection.putrequest(method, parsed.path, skip_host=True, skip_accept_encoding=True)
            for name, value in header_items:
                connection.putheader(name, value)
            connection.endheaders(body)
            phase = "http_response_headers"
            response = connection.getresponse()
        except (OSError, http.client.HTTPException) as error:
            if connection is not None:
                connection.close()
            diagnostic = {"exception_type": type(error).__name__, "message": str(error),
                          "request": exact_request, "request_metadata": dict(metadata),
                          "acquisition_started_at": started_at, "acquisition_finished_at": _now(),
                          "elapsed_seconds": time.monotonic() - started_clock,
                          "duration_meaning": "http_request_turnaround",
                          "timeout_seconds": self.timeout_seconds, "response_received": False}
            raise AcquisitionError("rfam_transport_error", phase=phase,
                                   submission_outcome=("not_sent" if phase == "connect" else "unknown")
                                       if method == "POST" else None,
                                   job_ref=metadata.get("job_id"), diagnostic=diagnostic) from error

        chunks, capture_error = [], None
        response_headers = list(response.headers.raw_items())
        declared_values = [value for key, value in response_headers if key.lower() == "content-length"]
        declared_length = None
        if declared_values:
            if all(re.fullmatch(r"[0-9]+", value.strip()) for value in declared_values):
                try:
                    lengths = {int(value.strip()) for value in declared_values}
                except ValueError:
                    lengths = set()
                if len(lengths) == 1:
                    declared_length = next(iter(lengths))
                else:
                    capture_error = "ConflictingContentLength"
            else:
                capture_error = "InvalidContentLength"
        try:
            # read1 returns available body bytes before a later timeout, rather
            # than losing a short prefix inside a read-to-length operation.
            while True:
                chunk = response.read1(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        except (OSError, http.client.HTTPException) as error:
            partial = getattr(error, "partial", b"")
            if isinstance(partial, bytes) and partial:
                chunks.append(partial)
            capture_error = type(error).__name__
        finally:
            response.close()
            connection.close()
        content = b"".join(chunks)
        if declared_length is not None and len(content) != declared_length:
            capture_error = capture_error or "ContentLengthMismatch"
        # A successfully drained chunked response has consumed its terminal
        # zero chunk and leaves no current chunk. A bare EOF is incomplete.
        if response.chunked and response.chunk_left is not None:
            capture_error = capture_error or "IncompleteChunkedBody"
        finished_at = _now()
        headers = {key.lower(): value for key, value in response_headers}
        status = response.status
        transport = {"status": status, "reason": response.reason,
                     "representation": "http_response_bytes", "headers": headers,
                     "header_items": response_headers, "request": exact_request,
                     "declared_url": address, "effective_url": address,
                     "acquisition_started_at": started_at, "acquisition_finished_at": finished_at,
                     "elapsed_seconds": time.monotonic() - started_clock,
                     "duration_meaning": "http_request_turnaround",
                     "timeout_seconds": self.timeout_seconds, "body_complete": capture_error is None,
                     "bytes_received": len(content), "declared_content_length": declared_length,
                     "body_capture_error": capture_error, "automatic_redirects": False,
                     "automatic_retries": False, "http_request_count": 1,
                     "redirect_not_followed": 300 <= status < 400,
                     "failure_code": ("rfam_response_body_incomplete" if capture_error else
                                      "rfam_redirect_not_followed" if 300 <= status < 400 else
                                      "rfam_http_error" if status >= 400 else None)}
        return SourceSnapshot("rfam_batch", address, dict(metadata), finished_at, content,
                              headers.get("content-type", "application/octet-stream"), transport)
