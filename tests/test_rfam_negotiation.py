"""Synthetic loopback HTTP fixtures; no Rfam/provider/model requests.

The intentionally small CM-shaped body tests header/identity parsing only. It
is not a runnable covariance model or scientific annotation result.
"""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from urllib.parse import urlsplit

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode.episodic_workflow.root.library.rna_evidence import model_header


MODEL = (b"INFERNAL1/a [synthetic transport fixture]\nNAME tRNA\nACC RF00005\n"
         b"DESC tRNA\nCLEN 71\nALPH RNA\nCM\n//\n")
NEGOTIATION_ERROR = b'{"detail":"Could not satisfy the request Accept header."}'


@contextmanager
def server(*, model=MODEL, model_type="application/x-infernal-cm"):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            calls.append({"method": "GET", "path": self.path,
                          "accept": self.headers.get("Accept")})
            if self.path == "/family/RF00005/cm":
                if self.headers.get("Accept") != "*/*":
                    status, content, mime = 406, NEGOTIATION_ERROR, "application/json"
                else:
                    status, content, mime = 200, model, model_type
            elif self.path == "/family/RF00005?content-type=application%2Fjson":
                status, content, mime = 200, b'{"rfam":{"acc":"RF00005","id":"tRNA"}}', "application/json"
            else:
                status, content, mime = 404, b"unexpected fixture request", "text/plain"
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Vary", "Accept")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", calls
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


def local_client(base):
    client = PublicClients(timeout=5)
    native_http = client._http

    def loopback(service, url, params, media_type, **options):
        # Only the fixed provider paths are routed to this synthetic local
        # server. The real HTTP construction/capture path remains in use.
        assert url.startswith("https://rfam.org/family/")
        return native_http(service, base + urlsplit(url).path, params, media_type, **options)

    client._http = loopback
    return client


def test_native_http_negotiation_retains_error_and_corrected_received_mime():
    with server() as (base, calls):
        with pytest.raises(AcquisitionError) as failure:
            PublicClients(timeout=5)._http("rfam_covariance_model", base + "/family/RF00005/cm",
                                          {}, "text/plain")
        error = failure.value
        assert error.code == "provider_http_406" and error.phase == "http_response"
        assert error.snapshot.content == NEGOTIATION_ERROR
        assert error.snapshot.media_type == "application/json"
        transport = error.snapshot.transport
        assert transport["status"] == 406 and transport["body_complete"] is True
        assert transport["request"]["headers"]["Accept"] == "text/plain"
        assert transport["headers"]["vary"] == "Accept"
        assert len(calls) == 1  # The failure was not retried.

        bundle = local_client(base).rfam_model("RF00005")
        assert bundle.model.content == MODEL and model_header(MODEL)["accession"] == "RF00005"
        assert bundle.model.media_type == "application/x-infernal-cm"
        assert bundle.model.transport["headers"]["content-type"] == bundle.model.media_type
        assert bundle.model.transport["request"]["headers"]["Accept"] == "*/*"
        assert bundle.metadata.media_type == "application/json"
        assert bundle.metadata.transport["request"]["headers"]["Accept"] == "application/json"
        assert [row["accept"] for row in calls] == ["text/plain", "*/*", "application/json"]


