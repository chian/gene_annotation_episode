"""Finite worker custody/CLI checks, not Store authority or an episode proof.

Saved fixtures are original718 observations; injected failures are labelled
engineering faults. Exactly one new tiny native CLI run is shared by its tests.
"""
import builtins
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import ModuleType

import pytest

from gene_annotation_episode import restriction_mapping_worker as worker


ATTEMPT = Path(os.environ["HMMER529_ATTEMPT"]) if "HMMER529_ATTEMPT" in os.environ else None
pytestmark = pytest.mark.skipif(ATTEMPT is None, reason="requires bounded529")
ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check182_native718/restriction-native718"
PINS = ROOT / "verification/tool_graders_restriction_mapping_2026-10-29_718/NATIVE_FIXTURE_PINS_001.json"
SAVED_CASES = ("ecori_linear_internal", "commercial_linear_internal", "nocut_snai", "engineering_partial_search")


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path.absolute()), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def load_file(value):
    return json.loads(Path(value["path"]).read_bytes())


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")


def supplied_binding(sequence):
    # Engineering operand metadata only; no claim of real Store/source authority.
    return {"version": "restriction_selected_sequence_v1", "namespace": "subject",
        "sequence_ref": "subject_engineering722", "source_ref": "source_engineering722",
        "sequence_version": None, "content_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
        "length_nt": len(sequence), "origin_mapping_ref": None}


@pytest.fixture(scope="module")
def inputs():
    destination = ATTEMPT / "worker722-inputs"
    destination.mkdir(exist_ok=False)
    expected = {Path(p["path"]).name: p for p in json.loads(PINS.read_bytes())}
    result = {}
    for name in SAVED_CASES:
        raw = (ORIGINAL / (name + ".json")).read_bytes()
        original = expected[name + ".json"]
        assert len(raw) == original["size_bytes"] and hashlib.sha256(raw).hexdigest() == original["sha256"]
        native_path = destination / (name + ".native.json")
        native_path.write_bytes(raw)
        native = json.loads(raw)
        catalog_path = destination / (name + ".catalog.json")
        save(catalog_path, native["catalog"])
        result[name] = {"version": "restriction_worker_request_v1", "mode": "saved",
            "native_file": pin(native_path), "catalog_file": pin(catalog_path),
            "selected_sequence": native["request"]["sequence_binding"]}
    save(destination / "REQUESTS.json", result)
    return result


@pytest.fixture(scope="module")
def saved_runs(inputs):
    results = {}
    counters = {"native_import_attempts": 0, "network_attempts": 0, "dispatch_attempts": 0}
    original_import = builtins.__import__
    def imports(name, *args, **kwargs):
        if name == "Bio" or name.startswith("Bio.") or "restriction_mapping_native" in name:
            counters["native_import_attempts"] += 1
            raise AssertionError("saved worker imported native")
        return original_import(name, *args, **kwargs)
    def network(*args, **kwargs):
        counters["network_attempts"] += 1
        raise AssertionError("saved worker attempted network")
    def dispatch(*args, **kwargs):
        counters["dispatch_attempts"] += 1
        raise AssertionError("saved worker attempted dispatch")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(builtins, "__import__", imports)
        patch.setattr(socket.socket, "connect", network)
        patch.setattr(socket, "create_connection", network)
        patch.setattr(subprocess, "run", dispatch)
        patch.setattr(subprocess, "Popen", dispatch)
        for name, request in inputs.items():
            results[name] = worker.run_restriction_worker(request,
                output_directory=ATTEMPT / ("worker722-saved-" + name))
    save(ATTEMPT / "worker722-saved-counters.json", counters)
    return results, counters


@pytest.mark.parametrize("name", SAVED_CASES)
def test_saved_complete_bytes_and_original_result_meanings(name, saved_runs, inputs):
    results, counters = saved_runs
    manifest = results[name]
    assert counters == {"native_import_attempts": 0, "network_attempts": 0, "dispatch_attempts": 0}
    assert manifest["status"] == ("partial" if name.startswith("engineering_") else "complete")
    assert manifest["reader_state"] == "returned" and manifest["failure"] is None
    assert manifest["request_sha256"] == worker.restriction_digest(inputs[name])
    for field in ("native_file", "catalog_file"):
        assert Path(manifest[field]["path"]).read_bytes() == Path(inputs[name][field]["path"]).read_bytes()
    mapping = load_file(manifest["mapping_file"])
    native = load_file(manifest["native_file"])
    assert mapping["native_sha256"] == worker.restriction_digest(native)
    assert mapping["selected_sequence"] == inputs[name]["selected_sequence"]
    if name == "ecori_linear_internal":
        row, = mapping["enzyme_rows"]
        assert row["native_search_positions_1based"] == [6]
        assert (row["positions"][0]["watson_boundary_0based"], row["positions"][0]["crick_boundary_0based"]) == (5, 9)
    elif name == "commercial_linear_internal":
        assert mapping["population"] == {"selected_enzyme_count": 623, "attempted_enzyme_count": 623,
            "returned_enzyme_count": 623, "complete_empty_enzyme_count": 616, "recognition_match_count": 9}
    elif name == "nocut_snai":
        row, = mapping["enzyme_rows"]
        assert row["native_search_positions_1based"] == [5]
        assert row["positions"][0]["watson_boundary_0based"] is None
        assert row["positions"][0]["geometry_state"] == "unknown"
    else:
        assert sorted(r["search_state"] for r in mapping["enzyme_rows"]) == ["failed", "not_started", "returned"]
        assert mapping["population"]["attempted_enzyme_count"] == 2
        assert mapping["population"]["returned_enzyme_count"] == 1
        assert mapping["population"]["recognition_match_count"] is None


@pytest.mark.parametrize("fault", ["missing", "symlink", "directory", "digest", "truncated", "duplicate_key", "nonfinite", "overflow"])
def test_bad_saved_native_never_becomes_a_completed_negative(fault, inputs, tmp_path):
    request = deepcopy(inputs["ecori_linear_internal"])
    path = tmp_path / "native.json"
    if fault == "missing":
        request["native_file"]["path"] = str(path)
    elif fault == "symlink":
        path.symlink_to(request["native_file"]["path"])
        request["native_file"]["path"] = str(path)
    elif fault == "directory":
        path.mkdir()
        request["native_file"]["path"] = str(path)
    else:
        raw = Path(request["native_file"]["path"]).read_bytes()
        raw = {"truncated": b'{"version":', "duplicate_key": b'{"version":1,"version":2}',
            "nonfinite": b'{"value":NaN}', "overflow": b'{"value":1e999}'}.get(fault, raw)
        path.write_bytes(raw)
        request["native_file"] = pin(path)
        if fault == "digest": request["native_file"]["sha256"] = "0" * 64
    result = worker.run_restriction_worker(request, output_directory=tmp_path / "output")
    assert result["status"] == "failed" and result["native_state"] == "unavailable"
    assert result["native_file"] is result["mapping_file"] is None
    assert result["reader_state"] == "not_started"
    assert result["failure"]["code"] == ("saved_native_unavailable" if fault == "missing" else
        "saved_json_invalid" if fault in ("truncated", "duplicate_key", "nonfinite", "overflow") else "saved_file_conflict")


@pytest.mark.parametrize("fault", ["missing", "malformed", "conflicting", "null"])
def test_catalog_problem_preserves_the_completed_native_bytes(fault, inputs, tmp_path):
    request = deepcopy(inputs["ecori_linear_internal"])
    path = tmp_path / "catalog.json"
    if fault == "null": request["catalog_file"] = None
    elif fault == "missing": request["catalog_file"]["path"] = str(path)
    else:
        path.write_bytes(b'{"bad":' if fault == "malformed" else b'{}')
        request["catalog_file"] = pin(path)
    result = worker.run_restriction_worker(request, output_directory=tmp_path / "output")
    assert Path(result["native_file"]["path"]).read_bytes() == Path(request["native_file"]["path"]).read_bytes()
    if fault in ("missing", "malformed"):
        assert result["status"] == "partial" and result["reader_state"] == "not_started"
        assert result["failure"]["code"] == ("saved_catalog_unavailable" if fault == "missing" else "saved_json_invalid")
    else:
        assert result["status"] == ("failed" if fault == "null" else "invalid")
        assert result["reader_state"] == "returned" and result["failure"] is None
        assert load_file(result["mapping_file"])["enzyme_rows"] == []


def test_source_path_replacement_during_capture_is_rejected(inputs, tmp_path, monkeypatch):
    request = deepcopy(inputs["ecori_linear_internal"])
    path = tmp_path / "changing.json"
    raw = Path(request["native_file"]["path"]).read_bytes()
    path.write_bytes(raw)
    request["native_file"] = pin(path)
    original = os.fstat
    observed = [0]
    def replace_after_read(fd):
        info = original(fd)
        if os.readlink(f"/proc/self/fd/{fd}") == str(path):
            observed[0] += 1
            if observed[0] == 2:
                replacement = tmp_path / "replacement.json"
                replacement.write_bytes(raw)
                os.replace(replacement, path)
        return info
    monkeypatch.setattr(worker.os, "fstat", replace_after_read)
    result = worker.run_restriction_worker(request, output_directory=tmp_path / "output")
    assert observed[0] == 2 and result["failure"]["code"] == "saved_file_conflict"
    assert result["native_file"] is None


@pytest.mark.parametrize("fault", ["exception", "invalid_result"])
def test_reader_failure_keeps_native_and_catalog_before_return(fault, inputs, tmp_path, monkeypatch):
    def failed(*args, **kwargs):
        if fault == "exception": raise RuntimeError("labelled722_reader_failure")
        return {"labelled722_invalid_mapping": True}
    monkeypatch.setattr(worker, "read_restriction_mapping", failed)
    result = worker.run_restriction_worker(inputs["ecori_linear_internal"], output_directory=tmp_path / "output")
    assert result["status"] == "partial" and result["reader_state"] == "failed"
    assert result["native_file"] and result["catalog_file"] and result["mapping_file"] is None
    assert result["failure"]["code"] == ("reader_exception" if fault == "exception" else "mapping_record_invalid")
    assert json.loads((tmp_path / "output/manifest.json").read_bytes()) == result


@pytest.mark.parametrize("file", ["catalog.json", "mapping.json", "manifest.json"])
def test_later_output_failure_does_not_remove_prior_complete_files(file, inputs, tmp_path, monkeypatch):
    original = worker._Output.write
    def fail(output, name, raw):
        if name == file: raise OSError("labelled722_output_failure")
        return original(output, name, raw)
    monkeypatch.setattr(worker._Output, "write", fail)
    output = tmp_path / "output"
    if file == "manifest.json":
        with pytest.raises(OSError, match="labelled722_output_failure"):
            worker.run_restriction_worker(inputs["ecori_linear_internal"], output_directory=output)
        assert all((output / name).is_file() for name in ("native.json", "catalog.json", "mapping.json"))
    else:
        result = worker.run_restriction_worker(inputs["ecori_linear_internal"], output_directory=output)
        assert result["status"] == "partial" and result["failure"]["code"] == "output_capture_failed"
        assert result["native_file"] and (output / "native.json").is_file()
        assert result["reader_state"] == ("not_started" if file == "catalog.json" else "returned")
        assert result["mapping_file"] is None


def test_existing_output_directory_is_not_overwritten(inputs, tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    kept = output / "native.json"
    kept.write_text("retained operator bytes")
    with pytest.raises(FileExistsError):
        worker.run_restriction_worker(inputs["ecori_linear_internal"], output_directory=output)
    assert kept.read_text() == "retained operator bytes"


def test_dangling_output_alias_is_not_followed(inputs, tmp_path):
    target = tmp_path / "unselected-target"
    output = tmp_path / "output"
    output.symlink_to(target)
    with pytest.raises(FileExistsError):
        worker.run_restriction_worker(inputs["ecori_linear_internal"], output_directory=output)
    assert output.is_symlink() and not target.exists()


@pytest.mark.parametrize("fault", ["exception", "invalid_record"])
def test_labelled_native_adapter_failure_does_not_invent_native_rows(fault, tmp_path, monkeypatch):
    replacement = ModuleType("gene_annotation_episode.restriction_mapping_native")
    calls = []
    def failed(*args, **kwargs):
        calls.append((args, kwargs))
        if fault == "exception": raise RuntimeError("labelled722_native_adapter_failure")
        return {"labelled722_invalid_native_record": True}
    replacement.run_restriction_mapping = failed
    monkeypatch.setitem(sys.modules, "gene_annotation_episode.restriction_mapping_native", replacement)
    sequence = "AAAAGAATTCTTTT"
    request = {"version": "restriction_worker_request_v1", "mode": "native", "sequence": sequence,
        "selected_sequence": supplied_binding(sequence), "enzyme_selection": {"kind": "explicit", "names": ["EcoRI"]},
        "topology": "linear"}
    result = worker.run_restriction_worker(request, output_directory=tmp_path / "output")
    assert len(calls) == 1 and result["status"] == "failed" and result["native_state"] == "failed"
    assert result["native_file"] is result["catalog_file"] is result["mapping_file"] is None
    assert result["reader_state"] == "not_started"
    assert result["failure"]["code"] == ("native_exception" if fault == "exception" else "native_record_invalid")


def test_request_and_manifest_validation_are_closed_detached_and_io_free(inputs, saved_runs, monkeypatch):
    def denied(*args, **kwargs): raise AssertionError("pure validation read a file")
    request = inputs["ecori_linear_internal"]
    manifest = saved_runs[0]["ecori_linear_internal"]
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", denied)
        checked = worker.validate_restriction_worker_request(request)
        checked["selected_sequence"]["source_ref"] = "changed caller copy"
        assert request["selected_sequence"]["source_ref"] != "changed caller copy"
        assert worker.validate_restriction_worker_manifest(manifest) == manifest
        for field, bad in (("extra", True), ("native_file", {**request["native_file"], "size_bytes": True})):
            wrong = deepcopy(request);wrong[field] = bad
            with pytest.raises(ValueError, match="^request_invalid$"):
                worker.validate_restriction_worker_request(wrong)
        wrong = deepcopy(manifest);wrong["reader_state"] = "not_started"
        with pytest.raises(ValueError, match="^manifest_invalid$"):
            worker.validate_restriction_worker_manifest(wrong)


@pytest.mark.parametrize("raw", [b'{"mode":"saved","mode":"native"}', b'{"mode":NaN}', b'{"mode":'])
def test_invalid_cli_request_returns_constrained_failure_without_outputs(raw, tmp_path, monkeypatch, capsys):
    request = tmp_path / "request.json";request.write_bytes(raw)
    output = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", ["restriction_worker", str(request), str(output)])
    assert worker.main() == 2 and not output.exists()
    assert capsys.readouterr().err == '{"phase":"request","code":"request_invalid"}\n'


@pytest.mark.parametrize("status,code", [("complete", 0), ("partial", 0), ("invalid", 2), ("failed", 3)])
def test_saved_cli_exit_matches_actual_retained_result_status(status, code, inputs, tmp_path, monkeypatch):
    selected = "engineering_partial_search" if status == "partial" else "ecori_linear_internal"
    request = deepcopy(inputs[selected])
    if status == "failed":
        request["catalog_file"] = None
    elif status == "invalid":
        catalog = tmp_path / "conflicting-catalog.json"
        catalog.write_text("{}")
        request["catalog_file"] = pin(catalog)
    path = tmp_path / "request.json";save(path, request)
    output = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", ["restriction_worker", str(path), str(output)])
    assert worker.main() == code
    assert json.loads((output / "manifest.json").read_bytes())["status"] == status


@pytest.fixture(scope="module")
def native_cli_once():
    directory = ATTEMPT / "worker722-native-cli"
    directory.mkdir(exist_ok=False)
    sequence = "AAAAGAATTCTTTT"
    request = {"version": "restriction_worker_request_v1", "mode": "native", "sequence": sequence,
        "selected_sequence": supplied_binding(sequence), "enzyme_selection": {"kind": "explicit", "names": ["EcoRI"]},
        "topology": "linear"}
    request_path = directory / "request.json";save(request_path, request)
    # Bootstrap only observes original calls, then runs the real CLI __main__.
    bootstrap = '''import json, runpy, sys
from Bio.Restriction import Restriction as impl
counts = {"batch_search_calls": 0, "original_finditer_calls": 0}
batch, finditer = impl.RestrictionBatch.search, impl.FormattedSeq.finditer
def searched(self, dna, linear=True):
    counts["batch_search_calls"] += 1
    return batch(self, dna, linear=linear)
def found(self, pattern, size):
    counts["original_finditer_calls"] += 1
    return finditer(self, pattern, size)
impl.RestrictionBatch.search, impl.FormattedSeq.finditer = searched, found
request, output, counter = sys.argv[1:]
sys.argv = ["gene_annotation_episode.restriction_mapping_worker", request, output]
try:
    runpy.run_module("gene_annotation_episode.restriction_mapping_worker", run_name="__main__")
finally:
    with open(counter, "x") as stream:
        json.dump(counts, stream, sort_keys=True)
'''
    (directory / "bootstrap.py").write_text(bootstrap)
    with (directory / "stdout.txt").open("x") as stdout, (directory / "stderr.txt").open("x") as stderr:
        completed = subprocess.run([sys.executable, str(directory / "bootstrap.py"), str(request_path),
            str(directory / "output"), str(directory / "counts.json")], stdout=stdout, stderr=stderr, check=False)
    save(directory / "completion.json", {"returncode": completed.returncode,
        "binding_classification": "engineering_metadata_not_Store_authority", "selected_native_contexts": 1})
    return directory, request


def test_one_actual_native_cli_retains_original_search_before_shared_reading(native_cli_once):
    directory, request = native_cli_once
    assert json.loads((directory / "completion.json").read_bytes())["returncode"] == 0
    assert json.loads((directory / "counts.json").read_bytes()) == {"batch_search_calls": 1, "original_finditer_calls": 1}
    manifest = json.loads((directory / "output/manifest.json").read_bytes())
    assert manifest["status"] == "complete" and manifest["request_sha256"] == worker.restriction_digest(request)
    native, mapping = load_file(manifest["native_file"]), load_file(manifest["mapping_file"])
    assert native["request"]["sequence"] == "AAAAGAATTCTTTT"
    assert native["enzyme_searches"][0]["native_search_positions_1based"] == [6]
    assert mapping["enzyme_rows"][0]["native_search_positions_1based"] == [6]
    assert mapping["enzyme_rows"][0]["recognition_match_count"] == 1
    assert mapping["native_sha256"] == worker.restriction_digest(native)
    for field in ("native_file", "catalog_file", "mapping_file"):
        assert pin(Path(manifest[field]["path"])) == manifest[field]
