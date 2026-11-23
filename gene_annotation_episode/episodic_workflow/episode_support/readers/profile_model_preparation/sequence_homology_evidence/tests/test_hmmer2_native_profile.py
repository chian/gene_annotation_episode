"""Authentic distributed HMMER2 files and a separately selected H3 profile run.

The original 585 acquisition failure is preserved: its verifier incorrectly
expected exact binary probability identity. No test here downloads or calibrates
anything. A genuine native profile case requires its own explicit gate.
"""
from copy import deepcopy
import asyncio
import hashlib
import json
import os
from pathlib import Path
import socket

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.sequence_homology_evidence.hmmer_preparation_result_views import _hmmer2_evd_quantity
from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.sequence_homology_evidence.tests.test_hmmer2_upstream_fixtures import compare_native_pair


FIXTURES = Path(__file__).parent / "fixtures/hmmer2"
PINS = {
    "fn3-bin": ("d1d230743ecb250fbc75fa5d719d8217a17fc9b3b13b770fb8bbbe1130317add", 16930, "hmmer_binary"),
    "fn3-bin-swap": ("93e30121fe04413b503cccce3463535b202b9886cb8c08567df7f766e26f4f23", 16930, "hmmer_binary"),
    "rrm.hmm": ("053383f3c8aa4cea15ab546d4f529b99826d2de37b73f472b192ccceeb78985b", 29502, "hmmer2_ascii"),
}


def native_fixture(name):
    raw = (FIXTURES / name).read_bytes()
    sha256, size, format = PINS[name]
    assert hashlib.sha256(raw).hexdigest() == sha256 and len(raw) == size
    return raw, format


def database_rows(store):
    tables = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted([tuple(row) for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')], key=repr)
        for name in tables}


def test_actual_distributed_native_binary_conflict_and_saved_evd_view_without_network_or_calculation(tmp_path, monkeypatch):
    receipt_raw = (FIXTURES / "SOURCE_RECEIPT.json").read_bytes()
    assert hashlib.sha256(receipt_raw).hexdigest() == "264591dac5fb2ec67f54d30c1457e5716772df1d4ad5f88eaff5c7459eab6b57"
    receipt = json.loads(receipt_raw)
    assert len(receipt["wire_calls"]) == 3
    records, retained_pins = {}, {}
    for name in PINS:
        raw, format = native_fixture(name)
        entry = next(row for row in receipt["assets"] if row["filename"] == name)
        transport = entry["snapshot"]["transport"]
        assert entry["sha256"] == PINS[name][0] and entry["size_bytes"] == PINS[name][1]
        assert transport["status"] == 200 and transport["body_complete"] is True
        assert transport["observed_body_bytes"] == transport["retained_body_bytes"] == len(raw)
        occurrence = {"occurrence_id": "upstream/" + name, "direction": "input", "role": "models", "ordinal": 0,
            "artifact_ref": str((FIXTURES / name).resolve()), "sha256": PINS[name][0],
            "size_bytes": len(raw), "completeness": "complete"}
        extraction = extract_hmmer_models(raw, occurrence=occurrence, format=format)
        assert extraction["population"] == {"decoded_count": 1, "complete": True, "state": "decoded"}
        assert extraction["issues"] == [] and extraction["records"][0]["terminated"] is True
        records[name] = extraction["records"][0]
        retained_pins[name] = {"sha256": PINS[name][0], "size_bytes": len(raw)}
    conflicts = compare_native_pair(records["fn3-bin"], records["fn3-bin-swap"])
    assert {records[name]["representation"]["byte_order"] for name in ("fn3-bin", "fn3-bin-swap")} == {"little", "big"}
    rrm = records["rrm.hmm"]
    assert rrm["engine_text"] == "[2.2g]" and rrm["length"] == 77 and rrm["sequence_count"] == 90
    assert rrm["representation"]["legacy"]["evd"][0]["tokens"] == ["-44.976292", "0.254831"]
    saved = deepcopy(records)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved EVD inspection attempted input bytes, parsing, math or network")
    with monkeypatch.context() as guard:
        guard.setattr("builtins.open", forbidden)
        guard.setattr("gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.hmmer_model_data.extract_hmmer_models", forbidden)
        guard.setattr("gene_annotation_episode.episodic_workflow.episode_support.calculations.profile_model_preparation.sequence_homology_evidence.hmmer_model_calculations.calculate_hmmer_model_components", forbidden)
        guard.setattr("socket.socket", forbidden)
        values = [_hmmer2_evd_quantity(rrm, path) for path in ("calibration.EVD.mu", "calibration.EVD.lambda")]
        absent = [_hmmer2_evd_quantity(records[name], "calibration.EVD.mu") for name in ("fn3-bin", "fn3-bin-swap")]
    assert records == saved
    assert [(row["value"], row["state"], row["unit"]) for row in values] == [
        (-44.976292, "present", "bit"), (0.254831, "present", "inverse_bit")]
    assert [(row["value"], row["state"]) for row in absent] == [(None, "missing")] * 2
    for name in PINS:
        native_fixture(name)
    (tmp_path / "HMMER2_RETAINED_NATIVE_VERIFICATION.json").write_text(json.dumps({
        "version": "hmmer2_retained_native_fixture_verification", "fixture_pins": retained_pins,
        "binary_native_field_conflicts": conflicts, "remaining_native_fields_equal": True,
        "native_EVD_saved_values": values, "native_EVD_original_tokens": ["-44.976292", "0.254831"],
        "new_HTTP_requests": 0, "HMMER_execution_or_recalibration": False,
        "Store_custody_or_typed_Workflow_verified": False,
        "original_585_capture_failure_preserved": receipt["original_capture_proof"],
    }, indent=2, allow_nan=False) + "\n")


