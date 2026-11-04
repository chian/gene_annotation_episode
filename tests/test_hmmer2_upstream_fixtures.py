"""Opt-in one-time capture of three original HMMER2 distribution assets.

This is selected upstream-file acquisition and parser verification, not a new
HMMER execution, calibration or publication of Store Sources/Artifacts. Every
response or failure is checkpointed before native-format assertions.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import urllib.request

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.hmmer_model_binary2 import MAGIC


GATE = "HMMER_NATIVE_ORACLE_HMMER2_UPSTREAM_JSON"
ASSETS = [
    ("fn3-bin", "https://sources.debian.org/data/main/h/hmmer/2.3.2-5/testsuite/fn3-bin", 16930, "hmmer_binary"),
    ("fn3-bin-swap", "https://sources.debian.org/data/main/h/hmmer/2.3.2-5/testsuite/fn3-bin-swap", 16930, "hmmer_binary"),
    ("rrm.hmm", "https://sources.debian.org/data/main/h/hmmer/2.3.2-5/tutorial/rrm.hmm", 29502, "hmmer2_ascii"),
]
MAX_BYTES = 65536
TIMEOUT = 30


def checkpoint(path, value):
    temporary = path.with_suffix(".pending.json")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True, allow_nan=False)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def semantic_model(record):
    """Copy decoded source fields, excluding physical byte order/unused slots."""
    def distribution(value):
        return None if value is None else {"symbols": value["symbols"],
            "cells": [{"probability": cell["probability"], "state": cell["state"]} for cell in value["cells"]]}
    return {"format_tag": record["format_tag"], "engine_text": record["engine_text"],
        "headers": record["headers"], "alphabet": record["alphabet"], "length": record["length"],
        "sequence_count": record["sequence_count"], "effective_sequence_count": record["effective_sequence_count"],
        "cutoffs": record["cutoffs"], "calibration": record["calibration"],
        "initial": {name: distribution(value) for name, value in record["initial"].items()},
        "positions": [{"position": row["position"], "annotations": row["annotations"],
            **{name: distribution(row[name]) for name in ("match", "insert", "transitions")}}
            for row in record["positions"]],
        "used_native_fields": [{key: field[key] for key in ("field", "value", "state")}
            for field in record["representation"]["native_fields"] if field["state"] != "unused"]}


def compare_native_pair(first, second):
    """Retain the distributed p1 conflict; upstream compared ASCII conversion."""
    left, right = semantic_model(first), semantic_model(second)
    assert {key: value for key, value in left.items() if key != "used_native_fields"} == {
        key: value for key, value in right.items() if key != "used_native_fields"}
    assert len(left["used_native_fields"]) == len(right["used_native_fields"])
    differences = [{"first": a, "second": b} for a, b in zip(
        left["used_native_fields"], right["used_native_fields"]) if a != b]
    assert differences == [{"first": {"field": "NULT.p1", "value": 0.9971505999565125, "state": "present"},
        "second": {"field": "NULT.p1", "value": 0.9971505403518677, "state": "present"}}]
    slots = [next(field for field in record["representation"]["native_fields"] if field["field"] == "NULT.p1")
        for record in (first, second)]
    assert [(field["byte_start"], field["byte_end"], field["raw_hex"]) for field in slots] == [
        (478, 482, "43457f3f"), (478, 482, "3f7f4542")]
    return differences


def test_opt_in_original_hmmer2_upstream_binary_pair_and_native_evd_capture(tmp_path, monkeypatch):
    supplied = os.environ.get(GATE)
    if supplied is None:
        pytest.skip("requires explicit selected acquisition of three upstream HMMER2 assets")
    selected = json.loads(supplied)
    assert selected == {"enabled": True, "urls": [asset[1] for asset in ASSETS],
        "max_bytes": MAX_BYTES, "timeout_seconds": TIMEOUT, "follow_redirects": False}
    proof_path = tmp_path / "HMMER2_UPSTREAM_CAPTURE.json"
    proof = {"version": "hmmer2_upstream_native_fixture_capture_v1", "phase": "prepared",
        "selected": selected, "wire_calls": [], "captures": [], "parser_results": [],
        "native_HMMER_program_executed": False, "calibration_executed": False,
        "Store_Source_or_Artifact_published": False,
        "parser_artifact_ref_meaning": "physical retained capture path; no Store artifact custody claim",
        "source_distribution": "HMMER2.3.2 as retained in Debian hmmer2.3.2-5",
        "upstream_binary_pair_relationship": "testsuite/test1-conversion.pl compares hmmconvert output from both byte-swapped fixtures",
        "success": False}
    checkpoint(proof_path, proof)
    original_builder = urllib.request.build_opener
    def observed_builder(*handlers):
        opener = original_builder(*handlers)
        original_open = opener.open
        def once(request, *args, **kwargs):
            url = request.full_url
            assert url in selected["urls"] and not any(row["url"] == url for row in proof["wire_calls"])
            proof["wire_calls"].append({"url": url, "method": request.get_method(),
                "headers": list(request.header_items()), "body_supplied": request.data is not None,
                "timeout": kwargs.get("timeout")})
            checkpoint(proof_path, proof)
            assert request.get_method() == "GET" and request.data is None and not args
            assert kwargs == {"timeout": TIMEOUT}
            return original_open(request, **kwargs)
        opener.open = once
        return opener
    monkeypatch.setattr(urllib.request, "build_opener", observed_builder)
    def forbidden(*args, **kwargs):
        raise AssertionError("fixture acquisition attempted a redirect-capable opener")
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    client = PublicClients(ncbi_email=None, timeout=TIMEOUT)
    for name, url, expected_size, format in ASSETS:
        entry = {"name": name, "url": url, "expected_distribution_size_bytes": expected_size,
            "declared_format": format, "failure": None, "snapshot": None, "file": None}
        proof["captures"].append(entry)
        checkpoint(proof_path, proof)
        snapshot = None
        try:
            snapshot = client._http("hmmer2_upstream_fixture", url, {}, "application/octet-stream",
                max_bytes=MAX_BYTES, timeout_seconds=TIMEOUT, follow_redirects=False)
        except AcquisitionError as error:
            snapshot = error.snapshot
            entry["failure"] = {"code": error.code, "phase": error.phase,
                "diagnostic": deepcopy(error.diagnostic), "operational": deepcopy(error.operational)}
        except Exception as error:
            entry["failure"] = {"code": "unexpected_client_exception", "exception_type": type(error).__name__, "message": str(error)}
        if snapshot is not None:
            path = tmp_path / name
            with path.open("xb") as stream:
                stream.write(snapshot.content); stream.flush(); os.fsync(stream.fileno())
            entry["file"] = pin(path)
            entry["snapshot"] = {"service": snapshot.service, "url": snapshot.url,
                "request": deepcopy(snapshot.request), "retrieved_at": snapshot.retrieved_at,
                "media_type": snapshot.media_type, "transport": deepcopy(snapshot.transport)}
        proof["phase"] = "actual_response_or_failure_retained"
        checkpoint(proof_path, proof)
    assert len(proof["wire_calls"]) == 3
    for entry in proof["captures"]:
        assert entry["failure"] is None and entry["snapshot"] is not None, "original upstream response/failure retained; no retry"
        snapshot, file = entry["snapshot"], entry["file"]
        transport = snapshot["transport"]
        assert snapshot["url"] == entry["url"] and snapshot["request"] == {}
        assert transport["request"]["method"] == "GET" and transport["request"]["url"] == entry["url"]
        assert transport["effective_url"] == entry["url"] and transport["status"] == 200
        assert transport["body_complete"] is True and transport.get("body_capture_failure") is None
        assert transport["request_policy"] == {"timeout_seconds": TIMEOUT, "automatic_redirects": False}
        assert transport["response_byte_limit"] == MAX_BYTES
        assert transport["observed_body_bytes"] == transport["retained_body_bytes"] == file["size_bytes"] == entry["expected_distribution_size_bytes"]
        assert transport["declared_body_bytes"] in (None, file["size_bytes"])
        raw = Path(file["path"]).read_bytes()
        occurrence = {"occurrence_id": "upstream/" + entry["name"], "direction": "input", "role": "models",
            "ordinal": 0, "artifact_ref": file["path"], "sha256": file["sha256"],
            "size_bytes": file["size_bytes"], "completeness": "complete"}
        extraction = extract_hmmer_models(raw, occurrence=occurrence, format=entry["declared_format"])
        parsed_path = tmp_path / (entry["name"] + ".extraction.json")
        checkpoint(parsed_path, extraction)
        proof["parser_results"].append({"name": entry["name"], "file": pin(parsed_path),
            "population": extraction["population"], "issues": extraction["issues"]})
        checkpoint(proof_path, proof)
        assert len(extraction["records"]) == 1 and extraction["records"][0]["terminated"] is True
    by_name = {entry["name"]: json.loads(Path(entry["file"]["path"]).read_text())
        for entry in proof["parser_results"]}
    first, second = [by_name[name]["records"][0] for name in ("fn3-bin", "fn3-bin-swap")]
    assert {first["representation"]["byte_order"], second["representation"]["byte_order"]} == {"little", "big"}
    differences = compare_native_pair(first, second)
    for entry in proof["captures"][:2]:
        raw = Path(entry["file"]["path"]).read_bytes()
        assert any(int.from_bytes(raw[:4], order) == MAGIC for order in ("little", "big"))
    rrm = by_name["rrm.hmm"]["records"][0]
    pair, = rrm["representation"]["legacy"]["evd"]
    assert pair["tokens"] == ["-44.976292", "0.254831"]
    calibration, = rrm["calibration"]
    assert [(parameter["value"], parameter["unit"]) for parameter in calibration["parameters"]] == [(-44.976292, "bit"), (0.254831, "inverse_bit")]
    proof.update(phase="native_fixture_parser_verified", success=True,
        binary_core_arrays_equal=True, binary_native_fields_equal=False,
        binary_native_field_conflicts=differences, ascii_conversion_equivalence_verified=False,
        native_EVD_tokens_retained=True,
        native_producer_executable_version_verified=False)
    checkpoint(proof_path, proof)
