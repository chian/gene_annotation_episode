"""Supplied prior evidence for FBA; synthetic bytes, no native solve or custody.

Fixtures reuse the explicit TEST-normalized677 numerical problem. New prior
records exercise byte/address admission only, not real provider provenance.
"""
from copy import deepcopy
import builtins
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.flux_balance_readers import parse_fba_capture
from gene_annotation_episode.flux_balance_sheet import populate_flux_balance_sheet
from gene_annotation_episode.flux_balance_calculations import calculate_flux_balance_sheet
from test_flux_balance_core_679 import parameters
from test_flux_balance_readers_680 import captures, encode, file
from test_flux_balance_evidence_parsing_689 import (
    change, edit_role, select, synthetic_bundle, update_manifest,
)


def prior(raw=b'{"lim/its":{"~bounds":[-10,8]}}', format_name="synthetic_prior_json"):
    return {"file": file(raw, format_name), "bytes": raw}


def with_prior(captures, *, kind="bound", raw=None, pointer=None):
    extra = prior() if raw is None else prior(raw)
    payloads, expected = synthetic_bundle(captures, constraints=[change("IN", -10, 8)])
    def assign(job):
        if kind in {"receipt", "both"}:
            job["model_input"]["acquisition_receipt_file"] = deepcopy(extra["file"])
        if kind in {"bound", "both"}:
            for side, offset in (("lower", 0), ("upper", 1)):
                job["constraints"][0][side]["source"] = {
                    "file": deepcopy(extra["file"]),
                    "pointer": f"/lim~1its/~0bounds/{offset}" if pointer is None else pointer,
                }
    select(payloads, expected, assign)
    return payloads, expected, extra


def assert_independent_work(result):
    assert len(result["models"]["effective"]["reactions"]) == 3
    assert len(result["problems"]["effective"]["variables"]) == 7
    assert len(result["native_solution"]["native"]["variable_values"]) == 7
    assert [r["flux"]["value"] for r in result["native"]["flux_rows"]] == [7, 6, 6]


@pytest.mark.parametrize("kind", ["receipt", "bound", "both"])
def test_selected_prior_receipt_and_repeated_bound_uses_preserve_original_bytes(captures, kind):
    payloads, expected, extra = with_prior(captures, kind=kind)
    before = deepcopy((payloads, expected, extra))
    result = parse_fba_capture(payloads, expected=expected, prior_sources=[extra])
    assert result["original_request_file"] == payloads["selected_request"]["file"]
    assert result["native"]["request_realization"] == "exact"
    assert result["native"]["constraint_changes"][0]["application"] == "applied"
    assert result["retained_files"].count(extra["file"]) == 1
    assert len(result["retained_files"]) == 9
    assert digest(json.loads(payloads["selected_request"]["bytes"])["requested_job"]) == expected["requested_job_sha256"]
    assert (payloads, expected, extra) == before
    assert_independent_work(result)


def test_selected_order_defines_retained_prior_order_not_payload_order(captures):
    payloads, expected, bound_source = with_prior(captures)
    receipt = prior(b"whole receipt bytes", "synthetic_receipt")
    select(payloads, expected, lambda job: job["model_input"].update(acquisition_receipt_file=receipt["file"]))
    result = parse_fba_capture(payloads, expected=expected, prior_sources=[bound_source, receipt])
    assert result["retained_files"][-2:] == [receipt["file"], bound_source["file"]]
    assert result["native"]["request_realization"] == "exact"


def test_whole_non_json_source_is_valid_without_guessed_subvalue_addresses(captures):
    payloads, expected, extra = with_prior(captures, raw=b"\xff\x00binary evidence", pointer="")
    result = parse_fba_capture(payloads, expected=expected, prior_sources=[extra])
    assert result["native"]["request_realization"] == "exact"
    assert extra["file"] in result["retained_files"]
    select(payloads, expected, lambda job: job["constraints"][0]["lower"]["source"].update(pointer="/field"))
    result = parse_fba_capture(payloads, expected=expected, prior_sources=[extra])
    assert result["original_request_file"] is None
    assert any(r["code"] == "schema_invalid" and "/constraints/0/lower/source" in (r["field"] or "") for r in result["issues"])
    assert_independent_work(result)


@pytest.mark.parametrize("raw,pointer", [
    (b'{"bound":-10}', "/absent"),
    (b'{"bound":-10}', "/bound~2"),
    (b'{"bound":-10,"bound":8}', "/bound"),
    (b'{"bound":1e999}', "/bound"),
    (b'{"bound":NaN}', "/bound"),
    (b'{"bound":', "/bound"),
    (b"<bound>-10</bound>", "/bound"),
    (b"[-10,8]", "/01"),
])
def test_prior_subvalue_requires_actual_finite_unambiguous_json(captures, raw, pointer):
    payloads, expected, extra = with_prior(captures, raw=raw, pointer=pointer)
    result = parse_fba_capture(payloads, expected=expected, prior_sources=[extra])
    assert result["original_request_file"] is None
    assert result["native"]["request_realization"] == "unknown"
    assert extra["file"] in result["retained_files"]  # Verified bytes, unavailable interpretation.
    assert any(r["code"] == "schema_invalid" for r in result["issues"])
    assert_independent_work(result)


@pytest.mark.parametrize("mutation", ["hash", "length", "format", "not_bytes", "extra_key", "missing_file"])
def test_bad_supplied_prior_does_not_replace_or_discard_native_data(captures, mutation):
    payloads, expected, extra = with_prior(captures)
    supplied = deepcopy(extra)
    if mutation == "hash": supplied["bytes"] = b"x" * len(supplied["bytes"])
    elif mutation == "length": supplied["bytes"] += b" "
    elif mutation == "format": supplied["file"]["format"] = "other_format"
    elif mutation == "not_bytes": supplied["bytes"] = supplied["bytes"].decode()
    elif mutation == "extra_key": supplied["trust"] = True
    else: del supplied["file"]
    result = parse_fba_capture(payloads, expected=expected, prior_sources=[supplied])
    assert result["original_request_file"] is None
    assert extra["file"] not in result["retained_files"]
    assert any(r["code"] == "artifact_missing" for r in result["issues"])
    assert any((r["field"] or "").startswith("/prior_sources/0") for r in result["issues"])
    assert_independent_work(result)


@pytest.mark.parametrize("container", [{}, True, "path/to/source", [None]])
def test_invalid_extra_container_is_a_located_failure_with_partial_work(captures, container):
    payloads, expected, extra = with_prior(captures)
    result = parse_fba_capture(payloads, expected=expected, prior_sources=container)
    assert result["original_request_file"] is None
    assert any(r["code"] == "schema_invalid" and (r["field"] or "").startswith("/prior_sources") for r in result["issues"])
    assert_independent_work(result)


@pytest.mark.parametrize("second", ["identical", "conflicting"])
def test_duplicate_external_identity_is_not_resolved_by_silently_choosing_a_row(captures, second):
    payloads, expected, extra = with_prior(captures)
    other = deepcopy(extra)
    if second == "conflicting":
        other["file"]["sha256"] = "e" * 64
    result = parse_fba_capture(payloads, expected=expected, prior_sources=[extra, other])
    assert extra["file"] not in result["retained_files"]
    assert result["original_request_file"] is None
    assert any((r["field"] or "").startswith("/prior_sources/1") for r in result["issues"])
    assert_independent_work(result)


def test_missing_source_has_specific_issue_and_preserves_original_unbound_request(captures):
    payloads, expected, extra = with_prior(captures)
    before = deepcopy(payloads)
    result = parse_fba_capture(payloads, expected=expected)
    assert result["original_request_file"] is None
    assert result["native"]["request_realization"] == "unknown"
    assert {"artifact_missing", "artifact_identity_conflict"} <= {r["code"] for r in result["issues"]}
    assert payloads == before
    assert_independent_work(result)


@pytest.mark.parametrize("defect", ["attempt", "digest", "version"])
def test_unassociated_original_selection_cannot_admit_extra_files(captures, defect):
    payloads, expected, extra = with_prior(captures)
    if defect == "attempt": expected["attempt_id"] = "different_attempt"
    elif defect == "digest": expected["requested_job_sha256"] = "f" * 64
    else:
        edit_role(payloads, expected, "selected_request", lambda raw: raw.update(version="wrong"))
    result = parse_fba_capture(payloads, expected=expected, prior_sources=[extra])
    assert result["original_request_file"] is None
    assert extra["file"] not in result["retained_files"]
    assert_independent_work(result)


def test_prior_file_is_not_a_new_producer_role(captures):
    payloads, expected, extra = with_prior(captures)
    select(payloads, expected, lambda job: job["constraints"][0]["lower"].update(
        source={"role": extra["file"]["artifact_ref"], "pointer": "/lim~1its/~0bounds/0"}))
    result = parse_fba_capture(payloads, expected=expected, prior_sources=[extra])
    assert result["original_request_file"] is None
    assert any(r["code"] == "artifact_missing" and (r["field"] or "").endswith("/role") for r in result["issues"])
    assert_independent_work(result)


def test_arbitrary_file_shaped_evidence_and_environment_do_not_select_extra_bytes(captures):
    payloads, expected = synthetic_bundle(captures)
    extra = prior()
    edit_role(payloads, expected, "effective_model", lambda model: model["effective"].update(
        native_capture_evidence={"file": extra["file"]}))
    result = parse_fba_capture(payloads, expected=expected, prior_sources=[extra])
    assert extra["file"] not in result["retained_files"]
    assert any(r["code"] == "artifact_identity_conflict" and r["field"] == "/prior_sources/0/file" for r in result["issues"])
    assert_independent_work(result)


def test_conflicting_extra_does_not_replace_an_independently_verified_native_role(captures):
    payloads, expected = synthetic_bundle(captures)
    original = deepcopy(payloads["original_model"]["file"])
    extra = prior(b"different bytes", "synthetic_receipt")
    extra["file"]["artifact_ref"] = original["artifact_ref"]
    select(payloads, expected, lambda job: job["model_input"].update(acquisition_receipt_file=extra["file"]))
    result = parse_fba_capture(payloads, expected=expected, prior_sources=[extra])
    assert original in result["retained_files"] and extra["file"] not in result["retained_files"]
    assert result["original_request_file"] is None
    assert_independent_work(result)


@pytest.mark.parametrize("selection", ["matches", "conflicts", "null", "missing_original"])
def test_model_artifact_reference_has_its_actual_original_model_association(captures, selection):
    payloads, expected = synthetic_bundle(captures)
    original = payloads["original_model"]["file"]
    value = None if selection == "null" else "other_model_artifact" if selection == "conflicts" else original["artifact_ref"]
    select(payloads, expected, lambda job: job["model_input"].update(artifact_ref=value))
    if selection == "missing_original":
        payloads["original_model"] = {"file": None, "bytes": None, "state": "absent"}
        update_manifest(payloads, expected)
    result = parse_fba_capture(payloads, expected=expected)
    assert (result["original_request_file"] is not None) is (selection in {"matches", "null"})
    if selection == "conflicts": assert any(r["code"] == "model_identity_conflict" for r in result["issues"])
    assert_independent_work(result)


def test_supported_omitted_argument_keeps_previous_parser_digest(captures):
    path = Path(__file__).parents[1] / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check152a_parsing689/source_snapshot/gene_annotation_episode/flux_balance_readers.py"
    spec = importlib.util.spec_from_file_location("gene_annotation_episode._prior_sources_692_baseline", path)
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    payloads, expected = synthetic_bundle(captures, constraints=[change("IN", -10, 8)])
    old = baseline.parse_fba_capture(payloads, expected=expected)
    for supplied in (None, []):
        current = parse_fba_capture(payloads, expected=expected, prior_sources=supplied)
        assert current == old and digest(current) == digest(old)


def test_prior_bytes_populate_same_sheet_and_saved_calculator_without_external_work(captures):
    payloads, expected, extra = with_prior(captures, kind="both")
    before = deepcopy((payloads, expected, extra))
    def forbidden(*args, **kwargs):
        raise AssertionError("Prior-byte parser/calculator attempted external work")
    from unittest.mock import patch
    from contextlib import ExitStack
    with ExitStack() as stack:
        for owner, name in ((builtins, "open"), (io, "open"), (os, "open"), (Path, "open"),
                            (socket, "socket"), (socket, "create_connection"),
                            (subprocess, "Popen"), (subprocess, "run"), (builtins, "__import__")):
            stack.enter_context(patch.object(owner, name, forbidden))
        parsed = parse_fba_capture(payloads, expected=expected, prior_sources=[extra])
        sheet = populate_flux_balance_sheet(bundle=parsed)
        saved = json.loads(encode(sheet))
        calculated = calculate_flux_balance_sheet(saved, parameters=parameters(saved))
    assert (payloads, expected, extra) == before
    assert saved == sheet
    assert calculated["objective"]["native_basis_calculated"]["value"] == -4.25
    assert calculated["objective"]["full_calculated"]["value"] == -2.75
    assert calculated["active_count"] == 3
    if os.environ.get("HMMER529_ATTEMPT"):
        Path(os.environ["HMMER529_ATTEMPT"], "fba692_saved_example.json").write_text(json.dumps({
            "fixture_identity": "Synthetic prior bytes and TEST-normalized677 scientific records; no native solve or host authority",
            "selected_request": json.loads(payloads["selected_request"]["bytes"]),
            "sheet": sheet, "calculations": calculated,
        }, indent=2, allow_nan=False) + "\n")
