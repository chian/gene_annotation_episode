"""Focused read-only330 counterexamples, using synthetic file emitters only."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from gene_annotation_episode import native_blast_database_result_worker as worker
from tests.test_native_blast_database_convergence_worker import (
    request_from_packet, run_request, reuse_request, load, convergence,
    no_interpretation,
)
from tests.test_native_blast_database_result_worker import request_fixture


@pytest.mark.parametrize("program", ["rpsblast", "rpstblastn", "blastn_vdb", "tblastn_vdb"])
def test_nonpsi_fresh_worker_accepts_declared_bio_closure_without_316_or_bridge(tmp_path, program):
    # Imports above load PSI's SeqIO closure in the parent. The new process must
    # verify its declared actual files without importing either new PSI module.
    request = request_fixture(tmp_path, program)
    files = {r["module"]: r for r in request["implementation"]["files"]}
    assert "Bio.SeqIO" in files
    forbidden = ["gene_annotation_episode.native_blast_database_convergence",
        "gene_annotation_episode.blast_native_iteration_records"]
    assert all(name not in files for name in forbidden)
    path = tmp_path / "fresh-request.json"
    path.write_bytes(worker._json_bytes(request))
    script = '''import importlib.abc, json, sys
forbidden = set(json.loads(sys.argv[2]))
class NoPsi(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in forbidden:
            raise AssertionError("non-PSI import: " + fullname)
sys.meta_path.insert(0, NoPsi())
from gene_annotation_episode.native_blast_database_result_worker import run_native_blast_database_result_worker
assert forbidden.isdisjoint(sys.modules)
manifest = run_native_blast_database_result_worker(sys.argv[1])
assert forbidden.isdisjoint(sys.modules)
print(json.dumps({"status": manifest["status"], "version": manifest["version"], "failures": manifest["failures"]}))
raise SystemExit(manifest["status"] == "failed")
'''
    completed = subprocess.run([sys.executable, "-B", "-c", script, str(path), json.dumps(forbidden)],
        cwd=tmp_path, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), capture_output=True)
    (tmp_path / "fresh-worker.stdout").write_bytes(completed.stdout)
    (tmp_path / "fresh-worker.stderr").write_bytes(completed.stderr)
    assert completed.returncode == 0, completed.stdout.decode() + completed.stderr.decode()
    manifest = load(request, "worker-manifest.json")
    assert manifest["version"] == "native_blast_database_result_worker_manifest_v1"
    assert "native_convergence" not in {r["role"] for r in manifest["artifacts"]}
    assert load(request, "sheets.json")["schema"] == "native_blast_database_sheet_set_v1"


def test_noninvoked_v2_reuse_preserves_absent_extraction_and_candidate_list(tmp_path, monkeypatch):
    request = request_from_packet(tmp_path, query=b">q\nACDEFGHI\n>other\nACDEFGHI\n")
    first = run_request(tmp_path, request)
    assert first["status"] != "failed", load(request, "diagnostics.json")
    saved = load(request, "sheets.json")
    assert saved["native_convergence"]["query_binding"]["status"] == "multiple"
    assert saved["native_convergence"]["extraction"] is None
    new = reuse_request(request, first)
    no_interpretation(monkeypatch)
    second = run_request(tmp_path, new, "reuse.json")
    assert second["status"] != "failed", load(new, "diagnostics.json")
    assert second["version"] == first["version"] == "native_blast_database_result_worker_manifest_v2"
    assert load(new, "sheets.json") == saved
    assert "native_convergence" not in {r["role"] for r in second["artifacts"]}
    assert not (Path(new["output_directory"]) / "native-convergence.json").exists()
    assert convergence(new) == []


def test_missing_query_bytes_keeps_readable_hsps_and_no_false_convergence(tmp_path):
    request = request_from_packet(tmp_path)
    query = next(r for r in request["artifacts"] if r["artifact_key"] == request["bundle"]["input_manifest"][0]["artifact_key"])
    Path(query["path"]).unlink()
    manifest = run_request(tmp_path, request)
    assert manifest["status"] == "partial", load(request, "diagnostics.json")
    binding = load(request, "sheets.json")["native_convergence"]
    assert binding["selected"]["query"]["status"] == "bytes_unavailable"
    assert binding["selected"]["query"]["capture"]["sha256"] == query["sha256"]
    assert binding["selected"]["query"]["supplied_bytes"] is None
    assert binding["invocation"] == "not_invoked"
    assert binding["extraction"] is None and convergence(request) == []
    calculations = load(request, "calculations.json")
    assert len(calculations["native_hsp_components"]) == 2
    assert all(c["value"] == 2 for c in calculations["iteration"]["searches"][0]["counts"].values())
    assert any(r["artifact_key"] == query["artifact_key"] and r["code"] == "native_blast_database_artifact_missing"
        for r in manifest["failures"])


def test_rehashed_native_sibling_still_must_equal_saved_extraction(tmp_path, monkeypatch):
    request = request_from_packet(tmp_path)
    first = run_request(tmp_path, request)
    assert first["status"] != "failed", load(request, "diagnostics.json")
    copied = tmp_path / "altered-generation"
    shutil.copytree(request["output_directory"], copied)
    altered = deepcopy(first)
    path = copied / "native-convergence.json"
    extraction = json.loads(path.read_bytes())
    extraction["status"] = "unavailable"
    raw = worker._json_bytes(extraction)
    path.write_bytes(raw)
    entry = next(r for r in altered["artifacts"] if r["role"] == "native_convergence")
    entry.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    (copied / "worker-manifest.json").write_bytes(worker._json_bytes(altered))
    selected = deepcopy(request)
    selected["output_directory"] = str(copied)
    new = reuse_request(selected, first)
    no_interpretation(monkeypatch)
    failed = run_request(tmp_path, new, "rehashed-reuse.json")
    assert failed["status"] == "failed"
    assert any(r["code"] == "native_blast_database_frozen_artifact_changed"
        and r["pointer"] == "/reuse/native_convergence" for r in failed["failures"])
    assert not (Path(new["output_directory"]) / "sheets.json").exists()
