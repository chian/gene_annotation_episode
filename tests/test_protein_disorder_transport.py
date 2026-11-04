"""Opt-in official-site observation before selecting a new predictor request.

This is one source/transport GET, not a disorder prediction or a retry of565.
An unavailable site is retained as failure evidence, never as native scores.
"""
from dataclasses import asdict
import hashlib
from html.parser import HTMLParser
import json
import os
from urllib.parse import urlsplit
import urllib.request

import pytest


GATE = "HMMER_NATIVE_ORACLE_DISORDER_TRANSPORT"
URL = "https://iupred2a.elte.hu/"
LIMIT = 2 * 1024 * 1024
TIMEOUT = 30


class _Forms(HTMLParser):
    """Inventory supplied form declarations; never submit or follow them."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.forms = []
        self.scripts = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self._current = dict(action=attrs.get("action"), method=attrs.get("method"), fields=[])
            self.forms.append(self._current)
        elif tag in {"input", "textarea", "select", "button"} and self._current is not None:
            self._current["fields"].append(dict(tag=tag, name=attrs.get("name"), type=attrs.get("type")))
        elif tag == "script" and "src" in attrs:
            self.scripts.append(attrs["src"])

    def handle_endtag(self, tag):
        if tag == "form":
            self._current = None


def _save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")


def test_current_official_iupred_form_and_transport_contract(tmp_path, monkeypatch):
    if os.environ.get(GATE) != "1":
        pytest.skip("requires explicit selection of one official IUPred website GET")
    assert "HMMER529_ATTEMPT" in os.environ
    from gene_annotation_episode.acquisition import AcquisitionError, PublicClients
    from gene_annotation_episode.protein_disorder_result_contracts import ENDPOINT

    endpoint = urlsplit(ENDPOINT)
    assert URL == endpoint.scheme + "://" + endpoint.netloc + "/"
    proof = dict(version="iupred_official_site_transport_observation_v1", phase="prepared",
        url=URL, method="GET", max_bytes=LIMIT, timeout_seconds=TIMEOUT, automatic_redirects=False,
        predictor_endpoint_from_existing_contract=ENDPOINT, wire_calls=[], snapshot=None, failure=None,
        raw_file=None, forms=None, scripts=None, decode_state="missing", interpretation_failure=None,
        selected_prediction_requests=0, calculator_calls=0, Sources_created=0,
        scientific_service_execution_verified=False, positive_prediction_verified=False)
    output = tmp_path / "IUPRED_OFFICIAL_SITE_TRANSPORT.json"
    _save(output, proof)
    actual_build = urllib.request.build_opener

    def observed_build(*handlers):
        opener = actual_build(*handlers)
        actual_open = opener.open

        def observed_open(request, *args, **kwargs):
            assert not proof["wire_calls"], "the selected official-site GET must not repeat"
            assert request.full_url == URL and request.get_method() == "GET" and request.data is None
            proof["wire_calls"].append(dict(url=request.full_url, method=request.get_method(),
                request_body_present=False, timeout=kwargs.get("timeout")))
            _save(output, proof)
            return actual_open(request, *args, **kwargs)

        opener.open = observed_open
        return opener

    monkeypatch.setattr(urllib.request, "build_opener", observed_build)
    snapshot = None
    try:
        snapshot = PublicClients(ncbi_email=None, timeout=TIMEOUT)._http("iupred2a_official_site", URL,
            {}, "text/html", max_bytes=LIMIT, timeout_seconds=TIMEOUT, follow_redirects=False)
    except Exception as error:
        snapshot = getattr(error, "snapshot", None)
        proof["failure"] = dict(code=error.code if isinstance(error, AcquisitionError) else "request_failed",
            phase=getattr(error, "phase", None), exception_type=type(error).__module__ + "." + type(error).__name__,
            diagnostic=getattr(error, "diagnostic", None), message=str(error))
    if snapshot is not None:
        assert type(snapshot.content) is bytes
        raw = snapshot.content
        native = tmp_path / "official-site-response.bin"
        native.write_bytes(raw)
        proof["raw_file"] = dict(path=str(native), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        proof["snapshot"] = {key: value for key, value in asdict(snapshot).items() if key != "content"}
    # The actual response/failure checkpoint precedes decode, HTML interpretation,
    # identity assertions or any assertion concerning the remote site's form.
    proof["phase"] = "response_or_failure_retained_before_interpretation"
    _save(output, proof)
    try:
        assert len(proof["wire_calls"]) == 1
        assert proof["wire_calls"][0]["timeout"] == TIMEOUT
        if snapshot is None:
            assert proof["failure"] is not None and proof["raw_file"] is None
        else:
            assert snapshot.url == URL and snapshot.request == {} and len(snapshot.content) <= LIMIT
            assert snapshot.transport["response_byte_limit"] == LIMIT
            assert snapshot.transport["retained_body_bytes"] == len(snapshot.content)
            assert snapshot.transport["request_policy"] == dict(timeout_seconds=TIMEOUT, automatic_redirects=False)
            assert snapshot.transport["request"]["method"] == "GET"
            assert snapshot.transport["request"]["url"] == URL
            try:
                text = snapshot.content.decode("utf-8")
            except UnicodeDecodeError:
                proof["decode_state"] = "invalid_utf8"
            else:
                proof["decode_state"] = "decoded_utf8"
                parser = _Forms()
                parser.feed(text)
                parser.close()
                proof["forms"], proof["scripts"] = parser.forms, parser.scripts
        proof["phase"] = "observation_verified_without_prediction"
    except BaseException as error:
        proof["interpretation_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        _save(output, proof)
