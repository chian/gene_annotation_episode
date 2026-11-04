"""Pure-worker checks using original252 captures, never fabricated native output."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess

import pytest

from gene_annotation_episode import native_infernal_preparation_result_worker as worker
from gene_annotation_episode import native_infernal_preparation_worker as pure
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.state import Store


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "verification/tool_graders_infernal_preparation_capture_2026-10-26_252"
EXAMPLES = json.loads((CAPTURE / "NATIVE_CAPTURE_EXAMPLES_002.json").read_bytes())["examples"]


def forbidden(*args, **kwargs):
    raise AssertionError("native execution, acquisition, parsing or calculation forbidden")


def indexed_bytes(row):
    raw = (ROOT / row["path"]).read_bytes()
    assert len(raw) == row["size_bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
    return raw


def captured_case(store, tmp_path, case="consensus"):
    example = next(row for row in EXAMPLES if row["case"] == case)
    captured = json.loads(indexed_bytes(example["capture_receipt"]))
    original_directory = (ROOT / example["capture_receipt"]["path"]).parent
    directory = tmp_path / "capture"
    shutil.copytree(original_directory, directory)
    original_store = original_directory.parent / "store"
    for reference in {captured["bundle_artifact_ref"], *[r["artifact_ref"] for r in captured["artifacts"] + captured["invalid_artifacts"]]}:
        digest = reference.removeprefix("artifact_")
        raw = (original_store / "artifacts" / digest[:2] / digest).read_bytes()
        assert store.artifact(raw, "application/json" if reference == captured["bundle_artifact_ref"] else "application/octet-stream") == reference
    target = json.loads(indexed_bytes(example["original_target"]))
    plan = json.loads(indexed_bytes(example["original_plan"]))
    bundle = json.loads(store.get_artifact(captured["bundle_artifact_ref"]))
    assert bundle == json.loads(indexed_bytes(example["original_bundle"]))
    return target, plan, bundle, captured, directory


def grading_plan(store, tmp_path, case="consensus"):
    target, original_plan, bundle, capture, capture_directory = captured_case(store, tmp_path, case)
    occurrences, failures = worker.qualified_occurrences(bundle, capture["bundle_artifact_ref"], capture)
    parameters, metadata = worker.effective_parameters(bundle, occurrences)
    directory = tmp_path / "worker"
    directory.mkdir()
    return {"version": worker.PLAN_VERSION, "task": "grade", "directory": str(directory),
        "bundle": bundle, "original_plan": original_plan, "bundle_artifact_ref": capture["bundle_artifact_ref"],
        "capture": capture, "occurrences": occurrences, "effective_parameters": parameters,
        "files": [{"occurrence_ref": r["occurrence_ref"], "path": str(store.path / "artifacts" / r["sha256"][:2] / r["sha256"])}
                  for r in worker.eligible_occurrences(occurrences)],
        "failures": worker.unique_failures([*failures, *metadata])}


def selector(collection="output_records", quantities=("values.residue_count", "values.gc_count"), checks=(), artifacts=(), *, keys=None, offset=0, limit=1):
    return {"version": "native_infernal_preparation_result_selector_v1", "acquisition": "complete_bound_bundle",
        "projection": None if collection is None else {"collection": collection,
            "rows": {"record_keys": list(keys)} if keys else {"offset": offset, "limit": limit},
            "quantities": list(quantities), "checks": list(checks)}, "artifacts": list(artifacts)}


@pytest.mark.parametrize("case", [r["case"] for r in EXAMPLES])
def test_actual252_captures_grade_without_native_or_network(tmp_path, monkeypatch, case):
    with Store(tmp_path / "store") as store:
        plan = grading_plan(store, tmp_path, case)
        monkeypatch.setattr(subprocess, "run", forbidden)
        monkeypatch.setattr(subprocess, "Popen", forbidden)
        monkeypatch.setattr(socket, "socket", forbidden)
        result = worker.run(plan)
        assert result["completed"], result
        assert set(result["outputs"]) == {"grading", "sheet", "calculations"}
        directory = Path(plan["directory"])
        grading = json.loads((directory / "grading.json").read_bytes())
        assert grading["sheet"] == json.loads((directory / "sheet.json").read_bytes())
        assert grading["calculations"] == json.loads((directory / "calculations.json").read_bytes())
        assert grading["operation"] == plan["bundle"]["operation"]
        assert len({r["artifact_ref"] for r in grading["sheet"]["artifacts"]}) == len(grading["sheet"]["artifacts"])
        if case == "consensus":
            key = next(r["record_key"] for r in grading["sheet"]["output_records"] if r["kind"] == "generated_sequence")
            cells = next(r["components"] for r in grading["calculations"]["rows"] if r["record_key"] == key)
            assert cells["residue_count"]["value"] == 12
            assert cells["gc_count"]["value"] == 8
            assert cells["gc_fraction_canonical"]["value"] == 8 / 12
        if case == "merge_scores":
            partitions = [r for r in grading["sheet"]["native_rows"] if r["kind"] == "partition"]
            assert len(partitions) == 8
            assert all(len(r["series"]) == r["values"]["score_count"]["value"] for r in partitions)
            assert sum(len(r["series"]) for r in partitions) > 1000
            assert "partition_requests" not in grading["calculations"]["parameters"]
            assert sum(f["code"].endswith("partition_request_binding_unavailable") for f in result["failures"]) == 2
        if case == "calibration_failure":
            assert any(r["completeness"] == "partial" for r in grading["sheet"]["artifacts"] if r["role"] == "calibrated_models")
            assert any(f["code"].endswith("nonzero_returncode") for f in result["failures"])
        assert store.db.execute("SELECT count(*) FROM records WHERE record_type='observation'").fetchone()[0] == 0


def test_projection_uses_saved_numbers_without_parsers_or_calculators(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        plan = grading_plan(store, tmp_path)
        assert worker.run(plan)["completed"]
        grading = Path(plan["directory"]) / "grading.json"
        raw = grading.read_bytes()
        original = json.loads(raw)
        key = next(r["record_key"] for r in original["sheet"]["output_records"] if r["kind"] == "generated_sequence")
        selected = selector("calculations", quantities=("components.gc_fraction_canonical",), keys=[key],
            artifacts=[{"direction": "output", "role": "stdout", "ordinal": 0}])
        directory = tmp_path / "projection"
        directory.mkdir()
        monkeypatch.setattr(pure, "grade_infernal_preparation", forbidden)
        monkeypatch.setattr(pure, "recalculate_infernal_preparation", forbidden)
        monkeypatch.setattr(subprocess, "run", forbidden)
        monkeypatch.setattr(socket, "socket", forbidden)
        result = worker.run({"version": worker.PLAN_VERSION, "task": "project", "directory": str(directory),
            "grading": {"path": str(grading), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)},
            "operation": plan["bundle"]["operation"], "occurrences": plan["occurrences"],
            "source_ref": "source_original", "selector": selected, "failures": []})
        assert result["completed"], result
        projection = json.loads((directory / "projection.json").read_bytes())
        assert projection["rows"][0]["quantities"] == [{"path": "components.gc_fraction_canonical", "value": 8 / 12,
            "basis": "derived", "unit": "fraction", "state": "present"}]
        assert projection["population"]["source_ref"] == "source_original"
        assert projection["artifacts"][0]["source_ref"] == "source_original"


@pytest.mark.parametrize("fault", ["file_ref", "file_digest", "occurrence", "parameters", "request", "extra_file"])
def test_worker_rejects_custody_substitution(tmp_path, fault):
    with Store(tmp_path / "store") as store:
        plan = grading_plan(store, tmp_path)
        if fault == "file_ref":
            plan["files"][0]["occurrence_ref"] += "wrong"
        elif fault == "file_digest":
            substitute = tmp_path / "wrong"
            substitute.write_bytes(b"not the selected model")
            plan["files"][0]["path"] = str(substitute)
        elif fault == "occurrence":
            plan["occurrences"][0]["completeness"] = "partial"
        elif fault == "parameters":
            plan["effective_parameters"]["fake"] = 1
        elif fault == "request":
            plan["bundle"]["requested_job"]["argv"].append("wrong")
        else:
            plan["files"].append(deepcopy(plan["files"][0]))
        result = worker.run(plan)
        assert result["failures"]
        if fault != "file_digest":
            assert not result["completed"]
        else:
            assert any(f["code"].endswith("worker_retained_bytes_mismatch") for f in result["failures"])
            assert result["completed"]  # Missing input yields explicit unavailable measurements.


def test_worker_plan_and_cli_are_closed(tmp_path):
    with pytest.raises(ValueError, match="result_worker_plan_invalid"):
        worker.run({"task": "grade"})
    with pytest.raises(ValueError, match="exact_result_worker_plan_required"):
        worker.main([])


@pytest.mark.parametrize("failed", [False, True])
def test_worker_replays_success_or_failure_without_regrading(tmp_path, monkeypatch, failed):
    with Store(tmp_path / "store") as store:
        plan = grading_plan(store, tmp_path)
        if failed:
            plan["effective_parameters"]["invalid"] = 1
        original = worker.run(plan)
        assert original["completed"] is not failed
        monkeypatch.setattr(pure, "grade_infernal_preparation", forbidden)
        monkeypatch.setattr(subprocess, "run", forbidden)
        monkeypatch.setattr(socket, "socket", forbidden)
        assert worker.run(plan) == original
        (Path(plan["directory"]) / "worker-result.json").unlink()
        with pytest.raises(ValueError, match="original_work_incomplete"):
            worker.run(plan)


def test_missing_gc_capture_cannot_certify_partition_request(tmp_path):
    # This is a pure metadata-contract fault, not a fabricated native result.
    with Store(tmp_path / "store") as store:
        plan = grading_plan(store, tmp_path, "merge_scores")
        bundle = deepcopy(plan["bundle"])
        bundle["mode"] = "partition_scores"
        bundle["operation"]["mode"] = "partition_scores"
        bundle["operation"]["settings"].update({"--part": 1, "--ptot": 2})
        bundle["requested_job"]["native_infernal_preparation"]["operands"].append({"role": "gc"})
        rows = deepcopy(plan["occurrences"])
        partition = next(r for r in rows if r["role"] == "partition_scores")
        partition.update(direction="output", ordinal=0)
        parameters, failures = worker.effective_parameters(bundle, rows)
        assert "partition_requests" not in parameters
        assert any(r["code"].endswith("partition_request_binding_unavailable") for r in failures)


def test_distinct_missing_native_outputs_keep_original_failure_pointers(tmp_path):
    with Store(tmp_path / "store") as store:
        plan = grading_plan(store, tmp_path)
        bundle, capture = deepcopy(plan["bundle"]), deepcopy(plan["capture"])
        missing = [r for r in bundle["artifacts"] if r["role"] in {"stdout", "stderr"}]
        bundle["artifacts"] = [r for r in bundle["artifacts"] if r not in missing]
        capture["artifacts"] = [r for r in capture["artifacts"] if r["role"] not in {"stdout", "stderr"}]
        bundle["failures"] = [{"stage": "outputs", "code": "native_infernal_preparation_missing_output",
            "role": r["role"], "detail": {"relative_path": r["relative_path"]}} for r in missing]
        _, failures = worker.qualified_occurrences(bundle, plan["bundle_artifact_ref"], capture)
        actual = [r for r in failures if r["code"].endswith("missing_output")]
        assert len(actual) == 2
        assert [r["record_key"] for r in actual] == [plan["bundle_artifact_ref"] + "#/failures/" + str(i) for i in range(2)]


@pytest.mark.parametrize("message,code", [
    ("native_infernal_preparation_worker_authenticated_input_conflict", "native_infernal_preparation_worker_authenticated_input_conflict"),
    ("synthetic diagnostic with native content: >model text", "native_infernal_preparation_result_worker_ValueError"),
])
def test_grading_exception_prose_is_only_a_worker_diagnostic(tmp_path, monkeypatch, capsys, message, code):
    with Store(tmp_path / "store") as store:
        plan = grading_plan(store, tmp_path)
        def fail(**kwargs):
            raise ValueError(message)
        monkeypatch.setattr(pure, "grade_infernal_preparation", fail)
        result = worker.run(plan)
        assert not result["completed"] and result["failures"] == [worker.failure("worker", code)]
        diagnostic = json.loads(capsys.readouterr().err)
        assert diagnostic == {"stage": "worker", "record_key": None, "exception_type": "ValueError", "detail": message}
        monkeypatch.setattr(pure, "grade_infernal_preparation", forbidden)
        assert worker.run(plan) == result
        assert capsys.readouterr().err == ""


def test_reading_exception_prose_keeps_the_exact_occurrence_only_in_diagnostic(tmp_path, monkeypatch, capsys):
    with Store(tmp_path / "store") as store:
        plan = grading_plan(store, tmp_path)
        actual = worker._read_bytes
        unavailable_path = plan["files"][0]["path"]
        def read(descriptor):
            if descriptor["path"] == unavailable_path:
                raise ValueError("synthetic retained file reader diagnostic")
            return actual(descriptor)
        monkeypatch.setattr(worker, "_read_bytes", read)
        result = worker.run(plan)
        assert result["completed"]
        assert worker.failure("reading", "native_infernal_preparation_worker_retained_file_invalid",
            plan["files"][0]["occurrence_ref"]) in result["failures"]
        diagnostic = json.loads(capsys.readouterr().err)
        assert diagnostic["detail"] == "synthetic retained file reader diagnostic"
        assert diagnostic["record_key"] == plan["files"][0]["occurrence_ref"]
