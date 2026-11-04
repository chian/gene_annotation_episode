"""Opt-in capture of one HPA response before any HPA binding is implemented.

The captured file is an HTTP entity witness, not a published Source, a verified
gene record, an expression matrix or evidence of a working production binding.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import urllib.request

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients


GATE = "HMMER_NATIVE_ORACLE_HPA_GENE_CAPTURE_JSON"
GENE_ID = "ENSG00000141510"
URL = "https://www.proteinatlas.org/" + GENE_ID + ".json"
MAX_BYTES = 8388608
TIMEOUT_SECONDS = 30


def _checkpoint(path, proof):
    temporary = path.with_suffix(".pending.json")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(proof, stream, ensure_ascii=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _retain_snapshot(snapshot, directory, proof):
    """Retain bytes before interpreting transport metadata or native JSON."""
    raw = snapshot.content
    path = directory / "native-response.bin"
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    digest = hashlib.sha256(raw).hexdigest()
    proof["retained_file_pin"] = dict(path=str(path.resolve()),
        sha256=digest, size_bytes=len(raw))
    proof["snapshot"] = dict(service=snapshot.service, url=snapshot.url,
        request=deepcopy(snapshot.request), retrieved_at=snapshot.retrieved_at,
        media_type=snapshot.media_type, transport=deepcopy(snapshot.transport))
    proof["phase"] = "native_bytes_retained_before_inspection"


def _inspect_json(raw):
    """Expose structure without replacing raw bytes or choosing a native row.

    Objects retain every ordered member, including duplicate names. Numbers
    retain their original JSON tokens. This is inspection encoding only.
    """
    result = dict(state="not_parsed", encoding="ordered_members_and_number_lexemes_v1",
        root_kind=None, root_container_length=None, value=None, error=None)
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        result.update(state="invalid_utf8", error=dict(
            exception_type=type(error).__name__, message=str(error)))
        return result

    def number(token):
        return dict(kind="number", lexeme=token)

    def members(pairs):
        return dict(kind="object", members=[dict(name=name, value=value)
            for name, value in pairs])

    def nonfinite(token):
        raise ValueError("nonstandard_JSON_number:" + token)

    try:
        value = json.loads(text, object_pairs_hook=members,
            parse_int=number, parse_float=number, parse_constant=nonfinite)
    except (ValueError, RecursionError) as error:
        result.update(state="invalid_json", error=dict(
            exception_type=type(error).__name__, message=str(error)))
        return result
    if type(value) is dict:
        kind = value["kind"]
        length = len(value["members"]) if kind == "object" else None
    elif type(value) is list:
        kind, length = "array", len(value)
    else:
        kind = {str: "string", bool: "boolean", type(None): "null"}[type(value)]
        length = None
    result.update(state="parsed", root_kind=kind,
        root_container_length=length, value=value)
    return result


def _response_failures(snapshot):
    """HTTP/request qualification only; no native HPA item acceptance."""
    if snapshot is None:
        return ["no_response_snapshot"]
    transport = snapshot.transport
    request, policy = transport.get("request"), transport.get("request_policy")
    failures = []
    if (snapshot.service != "hpa" or snapshot.url != URL or snapshot.request != {}
            or type(request) is not dict or request.get("method") != "GET"
            or request.get("url") != URL or transport.get("effective_url") != URL):
        failures.append("selected_request_conflict")
    if policy != dict(timeout_seconds=TIMEOUT_SECONDS, automatic_redirects=False):
        failures.append("selected_transport_policy_conflict")
    if type(transport.get("status")) is not int or transport["status"] != 200:
        failures.append("http_200_not_observed")
    if transport.get("body_complete") is not True:
        failures.append("response_incomplete")
    count = len(snapshot.content)
    for key, expected in (("retained_body_bytes", count), ("observed_body_bytes", count),
            ("response_byte_limit", MAX_BYTES)):
        if type(transport.get(key)) is not int or transport[key] != expected:
            failures.append("response_count_conflict:" + key)
    declared = transport.get("declared_body_bytes")
    if declared is not None and (type(declared) is not int or declared != count):
        failures.append("declared_response_count_conflict")
    if count > MAX_BYTES:
        failures.append("selected_response_byte_limit_exceeded")
    if transport.get("body_capture_failure") is not None:
        failures.append("response_capture_failure")
    return failures


def test_opt_in_single_hpa_gene_json_native_shape_capture(tmp_path, monkeypatch):
    selected = os.environ.get(GATE)
    if selected is None:
        pytest.skip("requires explicit opt-in for one selected HPA GET")
    gate = json.loads(selected)
    assert type(gate) is dict and set(gate) == {
        "enabled", "gene_id", "max_bytes", "timeout_seconds", "follow_redirects"}
    assert gate["enabled"] is True and gate["gene_id"] == GENE_ID
    assert type(gate["max_bytes"]) is int and gate["max_bytes"] == MAX_BYTES
    assert type(gate["timeout_seconds"]) is int and gate["timeout_seconds"] == TIMEOUT_SECONDS
    assert gate["follow_redirects"] is False
    output = tmp_path / "HPA_NATIVE_CAPTURE.json"
    proof = dict(version="hpa_native_shape_capture_observation_v1", phase="prepared",
        invocation_check_passed=False, complete_http_200_selected_response=False,
        native_gene_identity_verified=False, expression_matrix_verified=False,
        production_binding_verified=False, Source_or_Artifact_published=False,
        selected=dict(method="GET", url=URL, gene_id=GENE_ID, params={},
            processing_media_type="application/json", max_bytes=MAX_BYTES,
            timeout_seconds=TIMEOUT_SECONDS, follow_redirects=False),
        wire_calls=[], failure=None, snapshot=None,
        retained_file_pin=None, json_inspection=None, response_qualification_failures=[])
    _checkpoint(output, proof)
    original_builder = urllib.request.build_opener

    def observed_builder(*handlers):
        opener = original_builder(*handlers)
        original_open = opener.open

        def open_once(request, *args, **kwargs):
            if proof["wire_calls"]:
                raise AssertionError("HPA native capture attempted another request")
            proof["wire_calls"].append(dict(method=request.get_method(),
                url=request.full_url, headers=list(request.header_items()),
                body_supplied=request.data is not None, timeout=kwargs.get("timeout")))
            proof["phase"] = "original_get_dispatch_observed"
            _checkpoint(output, proof)
            assert request.get_method() == "GET" and request.full_url == URL
            assert request.data is None and not args and kwargs == {"timeout": TIMEOUT_SECONDS}
            return original_open(request, **kwargs)

        opener.open = open_once
        return opener

    def forbid_urlopen(*args, **kwargs):
        raise AssertionError("HPA native capture requires its no-redirect opener")

    monkeypatch.setattr(urllib.request, "build_opener", observed_builder)
    monkeypatch.setattr(urllib.request, "urlopen", forbid_urlopen)
    snapshot = None
    try:
        client = PublicClients(ncbi_email=None, timeout=TIMEOUT_SECONDS)
        try:
            snapshot = client._http("hpa", URL, {}, "application/json",
                max_bytes=MAX_BYTES, timeout_seconds=TIMEOUT_SECONDS,
                follow_redirects=False)
        except AcquisitionError as error:
            snapshot = error.snapshot
            proof["failure"] = dict(exception_type=type(error).__name__, code=error.code,
                phase=error.phase, retry_after=error.retry_after,
                diagnostic=deepcopy(error.diagnostic), operational=deepcopy(error.operational))
        except Exception as error:
            proof["failure"] = dict(exception_type=type(error).__name__,
                code="unexpected_client_exception", message=str(error))
        if snapshot is not None:
            _retain_snapshot(snapshot, tmp_path, proof)
        else:
            proof["phase"] = "original_get_without_response_snapshot"
        # Preserve any actual response/failure before qualification or parsing.
        _checkpoint(output, proof)
        if snapshot is not None:
            proof["json_inspection"] = _inspect_json(snapshot.content)
            proof["phase"] = "native_shape_inspected_without_item_acceptance"
            _checkpoint(output, proof)
        failures = _response_failures(snapshot)
        proof["response_qualification_failures"] = failures
        proof["complete_http_200_selected_response"] = not failures
        proof["invocation_check_passed"] = len(proof["wire_calls"]) == 1 and not failures
        proof["phase"] = "capture_qualified" if not failures else "capture_failure_preserved"
        _checkpoint(output, proof)
        assert len(proof["wire_calls"]) == 1
        assert not failures, "selected HPA capture did not obtain a complete HTTP200 response; original attempt retained"
    finally:
        _checkpoint(output, proof)
