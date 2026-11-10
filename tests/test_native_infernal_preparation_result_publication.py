"""Preparation custody, real bounded grading, typed projection and offline replay.

Four original252 captures are reused unchanged. Additional tiny native jobs use
the actual251 reservation/driver and existing native_lifecycle under local_jobs.
Malformed cases are explicitly synthetic mutations, never native measurements.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import shutil
import socket
import subprocess
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_infernal_preparation_acquisition as acquisition
from gene_annotation_episode import native_infernal_preparation_result_publication as publication
from gene_annotation_episode import native_infernal_preparation_worker as pure
from gene_annotation_episode import infernal_preparation_result_views as views
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_infernal_contracts import native_infernal_digest as digest
from gene_annotation_episode.native_infernal_preparation_contracts import requested_job_from_infernal_preparation
from gene_annotation_episode.native_infernal_preparation_local import prepare_local_infernal_preparation
from gene_annotation_episode.practical_execution_state import _immutable
from gene_annotation_episode.state import Store

from test_native_infernal_preparation_result_worker import (
    ROOT, EXAMPLES, captured_case, forbidden, selector,
)


POLICY = LocalJobPolicy(20 * 1024 ** 3, 4 * 1024 ** 3)
COMPILED_INDEX = json.loads((ROOT / "verification/tool_graders_infernal_preparation_2026-10-26_247/NATIVE_COMPILED_INDEX_001.json").read_bytes())


def grade(store, tmp_path, case="consensus"):
    target, plan, bundle, capture, capture_directory = captured_case(store, tmp_path, case)
    prepared = publication.prepare_native_infernal_preparation_grading(store, target=target,
        capture=capture, capture_directory=capture_directory, directory=tmp_path / "grading", policy=POLICY)
    return target, plan, bundle, capture, capture_directory, prepared


def source(store, bundle, capture, prepared):
    return acquisition.publish_original_source(store, bundle=bundle, capture=capture, prepared=prepared)


def selected(store, tmp_path, bundle, capture, prepared, selection=None):
    ref = source(store, bundle, capture, prepared)
    result = publication.publish_selected_preparation_result(store, source_ref=ref, prepared=prepared,
        selector=selection or selector(), directory=tmp_path / "selection", policy=POLICY)
    return ref, result


def full(store, prepared):
    return json.loads(store.get_artifact(prepared["grading_artifact_ref"]))


def native_case(tmp_path, program, mode, *, change=None):
    indexed = next(r for r in COMPILED_INDEX["cases"] if (r["program"], r["mode"]) == (program, mode))
    raw = (ROOT / indexed["request_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == indexed["request_sha256"]
    job = json.loads(raw)
    if change:
        change(job)
    request = requested_job_from_infernal_preparation(job)
    assignment = {"workspace": str(tmp_path), "resource_kind": "local", "resource_id": "local",
                  "requested_job": request}
    state = SimpleNamespace(assignment=assignment, run_id="publication254", episode_id="selected-local-child")
    operation = "actual-" + program + "-" + mode
    root = tmp_path / ".episode-operations" / digest({"run": state.run_id, "episode": state.episode_id}) / digest(operation)
    root.mkdir(parents=True)
    handle = prepare_local_infernal_preparation(state, operation, root=root, policy=POLICY)
    native_lifecycle.start_prepared(handle)
    actual = native_lifecycle.wait_job(handle)
    _immutable(tmp_path / "native-receipt.json", {"returncode": actual.returncode, "metadata": actual.metadata})
    plan = json.loads((root / "infernal-preparation-plan.json").read_bytes())
    bundle = json.loads((Path(plan["attempt_directory"]) / "bundle.json").read_bytes())
    target = {"version": "execution_target_v1", "handle": "source_original_handoff254", "run_id": state.run_id,
        "origin_episode_id": state.episode_id, "resource_kind": "local", "resource_id": "local",
        "execution_id": str(handle.path), "request_sha256": digest(request), "assignment": assignment, "scope": {}}
    _immutable(tmp_path / "execution-target.json", target)
    return target, plan, bundle


def capture_and_grade(store, tmp_path, target):
    capture_directory = tmp_path / "capture"
    capture = acquisition.capture_local_bundle(store, target=target, directory=capture_directory)
    assert capture["bundle_validated"], capture
    prepared = publication.prepare_native_infernal_preparation_grading(store, target=target, capture=capture,
        capture_directory=capture_directory, directory=tmp_path / "grading", policy=POLICY)
    return capture, prepared


@pytest.mark.parametrize("case", [r["case"] for r in EXAMPLES])
def test_original252_capture_retains_full_numbers_and_receipt(tmp_path, case):
    with Store(tmp_path / "store") as store:
        target, plan, bundle, capture, directory, prepared = grade(store, tmp_path, case)
        assert prepared["graded"], prepared
        result = full(store, prepared)
        assert json.loads(store.get_artifact(prepared["sheet_artifact_ref"])) == result["sheet"]
        assert json.loads(store.get_artifact(prepared["calculations_artifact_ref"])) == result["calculations"]
        assert publication.validate_prepared_grading(store, prepared, bundle=bundle) == prepared
        assert len(prepared["occurrences"]) == len(capture["artifacts"])
        receipt_path = tmp_path / "grading/native-infernal-preparation-grading/grading-receipt.json"
        receipt = json.loads(receipt_path.read_bytes())
        worker_receipt = json.loads(store.get_artifact(receipt["worker_receipt_artifact_ref"]))
        assert worker_receipt["metadata"]["policy"] == POLICY.to_dict()
        assert worker_receipt["metadata"]["verified_cgroup"]["memory_max"] == 20 * 1024**3
        assert 'runtime_max' not in worker_receipt["metadata"]["verified_cgroup"]
        assert store.db.execute("SELECT count(*) FROM records WHERE record_type='observation'").fetchone()[0] == 0
        if case == "consensus":
            refs = [r for r in prepared["occurrences"] if r["role"] in {"stdout", "stderr"}]
            assert refs[0]["artifact_ref"] == refs[1]["artifact_ref"]
            assert refs[0]["occurrence_ref"] != refs[1]["occurrence_ref"]
            key = next(r["record_key"] for r in result["sheet"]["output_records"] if r["kind"] == "generated_sequence")
            cells = next(r["components"] for r in result["calculations"]["rows"] if r["record_key"] == key)
            assert [cells[k]["value"] for k in ("residue_count", "gc_count", "gc_denominator")] == [12, 8, 12]
        if case == "calibration_failure":
            assert prepared["failures"] and prepared["graded"]
            assert result["sheet"]["output_records"]  # Retained partial copied model, not invented success.
        if case == "calibrate":
            row = next(r for r in result["sheet"]["native_rows"] if r["kind"] == "calibration"
                and r["identity"] == {"algorithm": "cm_local_cyk", "name": "fixture246", "source": "model_header"})
            assert row["values"]["lambda"]["value"] == 0.44855
            assert row["values"]["random_hit_count"]["value"] == 4409
            cells = next(r["components"] for r in result["calculations"]["rows"] if r["record_key"] == row["record_key"])
            assert cells["actual_calibration_nt"]["value"] == 10000
            expected = -2.53576 + math.log(0.1) / 0.44855
            assert cells["mu_extrap_calculated"]["value"] == pytest.approx(expected)
            assert cells["mu_extrap_residual"]["value"] == pytest.approx(expected - (-7.66916))


@pytest.mark.parametrize("program,mode", [("cmbuild", "build"), ("cmconvert", "ascii"),
    ("cmfetch", "single_key"), ("cmpress", "press"), ("cmstat", "scores_at_evalue")])
def test_actual_native_preparation_numerical_examples(tmp_path, program, mode):
    target, plan, bundle = native_case(tmp_path, program, mode)
    with Store(tmp_path / "store") as store:
        capture, prepared = capture_and_grade(store, tmp_path, target)
        assert prepared["graded"], prepared
        grading = full(store, prepared)
        if program == "cmbuild":
            row = next(r for r in grading["sheet"]["native_rows"] if r["kind"] == "build")
            assert [row["values"][k]["value"] for k in ("nseq", "alignment_length", "base_pairs")] == [3, 12, 4]
            calc = next(r for r in grading["calculations"]["rows"] if r["record_key"] == row["record_key"])
            assert calc["components"]["paired_consensus_fraction"]["value"] == 8 / 12
        elif program == "cmpress":
            bindings = grading["calculations"]["parameters"]["artifact_bindings"]
            assert len(bindings) == 4
            assert all(b["source_artifact_ref"].endswith("#/inputs/0") and b["regular_file"] for b in bindings)
            checks = grading["calculations"]["rows"][0]["checks"]
            assert next(c["outcome"] for c in checks if c["check"] == "quartet_binding") == "pass"
            assert [c["outcome"] for c in checks if c["check"] == "source_binding"] == ["pass"] * 4
            choice = selector("calculations", quantities=("components.output_artifact_count",), checks=("source_binding", "quartet_binding"),
                artifacts=[{"direction": "output", "role": role, "ordinal": 0} for role in ("i1m", "i1i", "i1f", "i1p")])
            ref, projected = selected(store, tmp_path, bundle, capture, prepared, choice)
            assert len(projected["artifacts"]) == 4
            assert sum(c["name"] == "source_binding" for c in projected["rows"][0]["checks"]) == 4
        elif program == "cmfetch":
            request = next(r for r in prepared["occurrences"] if r["role"] == "request")
            assert store.get_artifact(request["artifact_ref"]) == canonical(bundle["requested_job"]).encode()
            keys = [r for r in grading["sheet"]["native_rows"] if r["kind"] == "key_request"]
            assert keys and keys[0]["locator"]["artifact_ref"] == capture["bundle_artifact_ref"] + "#/requested_job"
            assert keys[0]["requested_key"] == bundle["requested_job"]["native_infernal_preparation"]["key"]
        elif program == "cmconvert":
            assert grading["calculations"]["rows"][0]["components"]["input_model_count"]["value"] == 1
            assert grading["calculations"]["rows"][0]["components"]["output_model_count"]["value"] == 1
        else:
            native = next(r for r in grading["sheet"]["native_rows"] if r["identity"]["algorithm"] == "cm_local_inside")
            cells = next(r["components"] for r in grading["calculations"]["rows"] if r["record_key"] == native["record_key"])
            assert native["values"]["threshold_bits"]["value"] == 45.32
            assert cells["effective_random_hit_count"]["value"] == 3812000
            assert cells["score_at_evalue"]["value"] == pytest.approx(45.3239102053337)
            assert abs(cells["native_conversion_residual"]["value"]) < cells["native_rounding_half_width"]["value"] == .005
        _immutable(tmp_path / "populated-example.json", {"prepared": prepared, "grading": grading})
        assert store.db.execute("SELECT count(*) FROM records WHERE record_type='observation'").fetchone()[0] == 0


def test_native_fetch_missing_key_with_zero_exit(tmp_path):
    target, plan, bundle = native_case(tmp_path, "cmfetch", "key_file")
    assert bundle["returncode"] == 0
    with Store(tmp_path / "store") as store:
        capture, prepared = capture_and_grade(store, tmp_path, target)
        assert prepared["graded"]
        grading = full(store, prepared)
        aggregate = grading["calculations"]["rows"][0]
        assert aggregate["components"]["requested_key_count"]["value"] == 2
        assert aggregate["components"]["missing_key_count"]["value"] == 1
        assert aggregate["components"]["satisfied_key_count"]["value"] == 1
        choice = selector("calculations", quantities=("components.requested_key_count", "components.missing_key_count"), checks=("requested_keys_satisfied",))
        ref, result = selected(store, tmp_path, bundle, capture, prepared, choice)
        assert result["rows"][0]["checks"] == [{"name": "requested_keys_satisfied", "outcome": "fail", "occurrences": []}]
        assert result["rows"][0]["artifact_ref"] is None
        _immutable(tmp_path / "populated-example.json", {"prepared": prepared, "grading": grading, "projection": result})


def test_original_and_effective_binding_parameters_stay_distinct(tmp_path):
    forged = {"artifact_ref": "self-reported", "regular_file": True, "actual_attempt_id": "not-the-producer"}
    target, plan, bundle = native_case(tmp_path, "cmpress", "press",
        change=lambda job: job.update(grading_parameters={"artifact_bindings": [forged]}))
    with Store(tmp_path / "store") as store:
        capture, prepared = capture_and_grade(store, tmp_path, target)
        assert prepared["graded"]
        assert any(f["code"].endswith("supplied_artifact_bindings_conflict") for f in prepared["failures"])
        stable = json.loads(store.get_artifact(prepared["source_grading_artifact_ref"]))["grading"]
        assert stable["original_parameters"] == {"artifact_bindings": [forged]}
        assert len(stable["effective_parameters"]["artifact_bindings"]) == 4
        assert forged not in stable["effective_parameters"]["artifact_bindings"]


@pytest.mark.parametrize("fault", ["changed_input", "missing_output"])
def test_synthetic_native_custody_faults_keep_actual_survivors(tmp_path, fault):
    target, plan, bundle = native_case(tmp_path, "cmemit", "consensus")
    attempt = Path(plan["attempt_directory"])
    if fault == "changed_input":
        row = bundle["inputs"][0]
        changed = (attempt / row["relative_path"]).read_bytes() + b"\nsynthetic native input mutation\n"
        (attempt / row["relative_path"]).write_bytes(changed)
        row.update(final_sha256=hashlib.sha256(changed).hexdigest(), final_size_bytes=len(changed))
        bundle["failures"].append({"stage": "execution", "code": "native_infernal_preparation_immutable_input_changed",
            "role": "models", "detail": {"ordinal": 0}})
    else:
        row = next(r for r in bundle["artifacts"] if r["role"] == "generated_sequences")
        (attempt / row["relative_path"]).unlink()
        bundle["artifacts"].remove(row)
        bundle["failures"].append({"stage": "outputs", "code": "native_infernal_preparation_missing_output",
            "role": row["role"], "detail": {"relative_path": row["relative_path"]}})
    (attempt / "bundle.json").write_text(canonical(bundle) + "\n")
    with Store(tmp_path / "store") as store:
        capture, prepared = capture_and_grade(store, tmp_path, target)
        assert prepared["graded"], prepared
        grading = full(store, prepared)
        if fault == "changed_input":
            original = next(r for r in prepared["occurrences"] if r["direction"] == "input")
            assert original["completeness"] == "partial"
            assert all(r["role"] != "models" for r in grading["sheet"]["artifacts"])
            assert any(f["code"].endswith("input_not_original_selected_bytes") for f in prepared["failures"])
        else:
            assert any(f["code"] == "preparation_generated_output_missing" for f in prepared["failures"])
            choice = selector(None, artifacts=[{"direction": "output", "role": "generated_sequences", "ordinal": 0},
                {"direction": "input", "role": "models", "ordinal": 0}])
            ref, result = selected(store, tmp_path, bundle, capture, prepared, choice)
            assert result["population"]["missing_artifacts"] == choice["artifacts"][:1]
            assert len(result["artifacts"]) == 1


def test_exact_projection_and_stable_source_independent_of_selection(tmp_path):
    with Store(tmp_path / "store") as store:
        _, _, bundle, capture, _, prepared = grade(store, tmp_path)
        ref = source(store, bundle, capture, prepared)
        key = next(r["record_key"] for r in full(store, prepared)["sheet"]["output_records"] if r["kind"] == "generated_sequence")
        first = selector("calculations", quantities=("components.gc_count",), keys=[key], artifacts=[
            {"direction": "output", "role": "stdout", "ordinal": 0}, {"direction": "output", "role": "stderr", "ordinal": 0}])
        second = selector("output_records", quantities=("values.residue_count",))
        a = publication.publish_selected_preparation_result(store, source_ref=ref, prepared=prepared,
            selector=first, directory=tmp_path / "a", policy=POLICY)
        b = publication.publish_selected_preparation_result(store, source_ref=ref, prepared=prepared,
            selector=second, directory=tmp_path / "b", policy=POLICY)
        assert a["rows"][0]["quantities"][0]["value"] == 8 and b["rows"][0]["quantities"][0]["value"] == 12
        assert a["projection_artifact_ref"] != b["projection_artifact_ref"]
        assert len(a["artifacts"]) == 2 and a["artifacts"][0]["artifact_ref"] == a["artifacts"][1]["artifact_ref"]
        assert a["population"]["source_ref"] == b["population"]["source_ref"] == ref
        assert a["record_refs"][0] == b["record_refs"][0] == ref
        assert len(a["record_refs"]) == len(set(a["record_refs"]))
        assert all(r["source_ref"] == ref for r in a["artifacts"])
        assert source(store, bundle, capture, prepared) == ref
        assert store.db.execute("SELECT count(*) FROM records WHERE record_type!='source'").fetchone()[0] == 0
        with pytest.raises(ValueError, match="directory_identity_conflict"):
            publication.publish_selected_preparation_result(store, source_ref=ref, prepared=prepared,
                selector=second, directory=tmp_path / "a", policy=POLICY)


def test_grade_and_publication_replay_with_originals_and_all_work_forbidden(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        target, plan, bundle, capture, capture_directory, prepared = grade(store, tmp_path)
        choice = selector()
        ref, result = selected(store, tmp_path, bundle, capture, prepared, choice)
        large = {prepared[k] for k in ("grading_artifact_ref", "sheet_artifact_ref", "calculations_artifact_ref")}
        actual_get = store.get_artifact
        def small_only(reference):
            assert reference not in large, "Host must not hydrate full sheets"
            return actual_get(reference)
        monkeypatch.setattr(store, "get_artifact", small_only)
        monkeypatch.setattr(publication, "run_local_job", forbidden)
        monkeypatch.setattr(pure, "grade_infernal_preparation", forbidden)
        monkeypatch.setattr(pure, "recalculate_infernal_preparation", forbidden)
        monkeypatch.setattr(views, "project_preparation_result", forbidden)
        monkeypatch.setattr(acquisition, "local_infernal_preparation_plan", forbidden)
        monkeypatch.setattr(acquisition, "_capture_file", forbidden)
        monkeypatch.setattr(subprocess, "run", forbidden)
        monkeypatch.setattr(subprocess, "Popen", forbidden)
        monkeypatch.setattr(socket, "socket", forbidden)
        actual_open = Path.open
        def retained_only(path, *args, **kwargs):
            if path.is_relative_to(Path(plan["attempt_directory"]).parent):
                forbidden()
            return actual_open(path, *args, **kwargs)
        monkeypatch.setattr(Path, "open", retained_only)
        assert publication.prepare_native_infernal_preparation_grading(store, target=target, capture=capture,
            capture_directory=capture_directory, directory=tmp_path / "grading", policy=POLICY) == prepared
        assert publication.validate_publication(store, result, source_ref=ref, prepared=prepared,
            selector=choice, directory=tmp_path / "selection", policy=POLICY) == result
        assert publication.validate_prepared_grading(store, prepared, bundle=bundle) == prepared


@pytest.mark.parametrize("fault", ["source", "prepared_ref", "occurrence", "sheet_bytes", "projection_bytes", "publication"])
def test_source_byte_and_return_mismatches_reject(tmp_path, monkeypatch, fault):
    with Store(tmp_path / "store") as store:
        _, _, bundle, capture, _, prepared = grade(store, tmp_path)
        choice = selector()
        ref, result = selected(store, tmp_path, bundle, capture, prepared, choice)
        if fault == "source":
            ref = acquisition.publish_original_source(store, bundle=bundle, capture=capture)
        elif fault == "prepared_ref":
            prepared["sheet_artifact_ref"] = prepared["calculations_artifact_ref"]
        elif fault == "occurrence":
            prepared["occurrences"][0]["artifact_ref"] = prepared["occurrences"][-1]["artifact_ref"]
        elif fault in {"sheet_bytes", "projection_bytes"}:
            reference = prepared["sheet_artifact_ref"] if fault == "sheet_bytes" else result["projection_artifact_ref"]
            digest_ = reference.removeprefix("artifact_")
            (store.path / "artifacts" / digest_[:2] / digest_).write_bytes(b"{}")
        else:
            result["rows"][0]["quantities"][0]["value"] = 999
        monkeypatch.setattr(publication, "run_local_job", forbidden)
        with pytest.raises(ValueError):
            publication.validate_publication(store, result, source_ref=ref, prepared=prepared,
                selector=choice, directory=tmp_path / "selection", policy=POLICY)


@pytest.mark.parametrize("fault", ["projection_ref", "completed", "failures"])
def test_saved_success_receipt_cannot_remove_projection_evidence(tmp_path, monkeypatch, fault):
    with Store(tmp_path / "store") as store:
        _, _, bundle, capture, _, prepared = grade(store, tmp_path)
        choice = selector()
        ref, result = selected(store, tmp_path, bundle, capture, prepared, choice)
        directory = tmp_path / "selection/native-infernal-preparation-projection"
        receipt = json.loads((directory / "projection-receipt.json").read_bytes())
        if fault == "projection_ref":
            result["projection_artifact_ref"] = None
        elif fault == "completed":
            receipt["completed"] = False
        else:
            result["failures"] = [{"stage": "metadata", "code": "synthetic_forged_failure", "record_key": None}]
        # This deliberately mutates both small local receipts. Rehashing an
        # assertion cannot replace the required retained projection artifact.
        receipt["publication_sha256"] = digest(result)
        (directory / "publication.json").write_text(canonical(result) + "\n")
        (directory / "projection-receipt.json").write_text(canonical(receipt) + "\n")
        monkeypatch.setattr(publication, "run_local_job", forbidden)
        with pytest.raises(ValueError, match="publication_receipt"):
            publication.validate_publication(store, result, source_ref=ref, prepared=prepared,
                selector=choice, directory=tmp_path / "selection", policy=POLICY)


def test_missing_capture_is_structured_prerequisite_and_never_acquires(tmp_path, monkeypatch):
    monkeypatch.setattr(publication, "capture_local_bundle", forbidden)
    monkeypatch.setattr(publication, "run_local_job", forbidden)
    with Store(tmp_path / "store") as store:
        result = publication.prepare_native_infernal_preparation_grading(store, target={}, capture={},
            capture_directory=tmp_path / "missing", directory=tmp_path / "grading", policy=POLICY)
        assert not result["graded"] and result["bundle_artifact_ref"] is None
        assert result["failures"] == [{"stage": "prerequisite", "code": "native_infernal_preparation_completed_capture_required", "record_key": None}]
        assert publication.prepare_native_infernal_preparation_grading(store, target={}, capture={},
            capture_directory=tmp_path / "missing", directory=tmp_path / "grading", policy=POLICY) == result


def test_worker_failure_and_unsealed_intent_never_silently_retry(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        target, plan, bundle, capture, capture_directory = captured_case(store, tmp_path)
        def fails(*args, **kwargs):
            raise OSError("synthetic unavailable worker")
        monkeypatch.setattr(publication, "run_local_job", fails)
        prepared = publication.prepare_native_infernal_preparation_grading(store, target=target, capture=capture,
            capture_directory=capture_directory, directory=tmp_path / "grading", policy=POLICY)
        assert not prepared["graded"] and prepared["grading_artifact_ref"] is None
        monkeypatch.setattr(publication, "run_local_job", forbidden)
        assert publication.prepare_native_infernal_preparation_grading(store, target=target, capture=capture,
            capture_directory=capture_directory, directory=tmp_path / "grading", policy=POLICY) == prepared
        (tmp_path / "grading/native-infernal-preparation-grading/prepared.json").unlink()
        with pytest.raises(ValueError, match="original_work_incomplete"):
            publication.prepare_native_infernal_preparation_grading(store, target=target, capture=capture,
                capture_directory=capture_directory, directory=tmp_path / "grading", policy=POLICY)


@pytest.mark.parametrize("error_type", [ValueError, AcquisitionError])
def test_worker_launch_exception_prose_is_retained_outside_typed_failures(tmp_path, monkeypatch, error_type):
    with Store(tmp_path / "store") as store:
        target, _, _, capture, capture_directory = captured_case(store, tmp_path)
        def fail(*args, **kwargs):
            raise error_type("synthetic worker launch detail with a file path /tmp/example")
        monkeypatch.setattr(publication, "run_local_job", fail)
        prepared = publication.prepare_native_infernal_preparation_grading(store, target=target, capture=capture,
            capture_directory=capture_directory, directory=tmp_path / "grading", policy=POLICY)
        assert not prepared["graded"]
        assert prepared["failures"][0] == {"stage": "worker", "code": "native_infernal_preparation_result_worker_failed", "record_key": None}
        receipt = json.loads((tmp_path / "grading/native-infernal-preparation-grading/grading-receipt.json").read_bytes())
        diagnostic = json.loads(store.get_artifact(receipt["worker_receipt_artifact_ref"]))
        assert diagnostic["detail"] == "synthetic worker launch detail with a file path /tmp/example"
        assert "synthetic" not in canonical(prepared["failures"])
        monkeypatch.setattr(publication, "run_local_job", forbidden)
        assert publication.prepare_native_infernal_preparation_grading(store, target=target, capture=capture,
            capture_directory=capture_directory, directory=tmp_path / "grading", policy=POLICY) == prepared


def test_worker_output_exception_preserves_other_numerical_artifacts_and_diagnostic(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        actual = publication._capture_file
        def capture_output(store, directory, name, *args):
            if name == "grading.json":
                raise ValueError("synthetic full grading retention diagnostic")
            return actual(store, directory, name, *args)
        monkeypatch.setattr(publication, "_capture_file", capture_output)
        _, _, bundle, _, _, prepared = grade(store, tmp_path)
        assert not prepared["graded"] and prepared["grading_artifact_ref"] is None
        assert prepared["sheet_artifact_ref"] is not None and prepared["calculations_artifact_ref"] is not None
        assert any(r["code"] == "native_infernal_preparation_result_worker_output_invalid" for r in prepared["failures"])
        receipt = json.loads((tmp_path / "grading/native-infernal-preparation-grading/grading-receipt.json").read_bytes())
        diagnostic = json.loads(store.get_artifact(receipt["worker_receipt_artifact_ref"]))
        assert diagnostic["output_errors"] == [{"role": "grading", "exception_type": "ValueError",
            "detail": "synthetic full grading retention diagnostic"}]
        assert "synthetic" not in canonical(prepared["failures"])
        assert publication.validate_prepared_grading(store, prepared, bundle=bundle) == prepared


def test_projection_worker_failure_is_durable_without_invented_population(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        _, _, bundle, capture, _, prepared = grade(store, tmp_path)
        ref = source(store, bundle, capture, prepared)
        def fails(*args, **kwargs):
            raise OSError("synthetic projection worker failure")
        monkeypatch.setattr(publication, "run_local_job", fails)
        args = {"source_ref": ref, "prepared": prepared, "selector": selector(),
                "directory": tmp_path / "selection", "policy": POLICY}
        with pytest.raises(ValueError, match="projection_worker_failed"):
            publication.publish_selected_preparation_result(store, **args)
        directory = tmp_path / "selection/native-infernal-preparation-projection"
        saved = json.loads((directory / "projection-failure.json").read_bytes())
        assert saved["projection_artifact_ref"] is None and saved["failures"]
        assert not (directory / "publication.json").exists()
        monkeypatch.setattr(publication, "run_local_job", forbidden)
        with pytest.raises(ValueError, match="projection_worker_failed"):
            publication.publish_selected_preparation_result(store, **args)


def test_failed_grading_can_return_captured_artifacts_in_bounded_projection(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        target, _, bundle, capture, capture_directory = captured_case(store, tmp_path)
        actual = publication.run_local_job
        def fails(*args, **kwargs):
            raise OSError("synthetic grading worker failure")
        monkeypatch.setattr(publication, "run_local_job", fails)
        prepared = publication.prepare_native_infernal_preparation_grading(store, target=target, capture=capture,
            capture_directory=capture_directory, directory=tmp_path / "grading", policy=POLICY)
        assert not prepared["graded"]
        monkeypatch.setattr(publication, "run_local_job", actual)
        choice = selector(None, artifacts=[{"direction": "output", "role": "generated_sequences", "ordinal": 0}])
        ref, result = selected(store, tmp_path, bundle, capture, prepared, choice)
        assert result["projection_artifact_ref"] is not None and len(result["artifacts"]) == 1
        assert result["population"]["collection"] is None and result["rows"] == []
        assert result["failures"] == prepared["failures"]
        numerical = {"source_ref": ref, "prepared": prepared, "selector": selector(),
            "directory": tmp_path / "unavailable-numbers", "policy": POLICY}
        with pytest.raises(ValueError, match="saved_numerical_grading_unavailable"):
            publication.publish_selected_preparation_result(store, **numerical)
        monkeypatch.setattr(publication, "run_local_job", forbidden)
        with pytest.raises(ValueError, match="saved_numerical_grading_unavailable"):
            publication.publish_selected_preparation_result(store, **numerical)


def test_exact_missing_keys_and_stable_grading_across_directories(tmp_path):
    with Store(tmp_path / "store") as store:
        target, _, bundle, capture, capture_directory, prepared = grade(store, tmp_path)
        another = publication.prepare_native_infernal_preparation_grading(store, target=target, capture=capture,
            capture_directory=capture_directory, directory=tmp_path / "another-grading", policy=POLICY)
        assert another == prepared  # Worker timing/placement cannot change source identity.
        grading = full(store, prepared)
        key = next(r["record_key"] for r in grading["sheet"]["output_records"] if r["kind"] == "generated_sequence")
        choice = selector("calculations", quantities=("components.gc_count",), keys=["missing-native-record", key])
        ref, result = selected(store, tmp_path, bundle, capture, prepared, choice)
        assert [r["record_key"] for r in result["rows"]] == [key]
        assert result["population"]["missing_record_keys"] == ["missing-native-record"]
        assert result["population"]["total_records"] == 2 and result["population"]["omitted_records"] == 1


def test_saved_calibration_sheet_recalculates_without_parser_native_or_network(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        _, _, _, _, _, prepared = grade(store, tmp_path, "calibrate")
        grading = full(store, prepared)
        from gene_annotation_episode import infernal_preparation_statistics as parsers
        from gene_annotation_episode import infernal_preparation_models as models
        monkeypatch.setattr(parsers, "populate_infernal_statistics_sheet", forbidden)
        monkeypatch.setattr(models, "extract_infernal_models", forbidden)
        monkeypatch.setattr(subprocess, "run", forbidden)
        monkeypatch.setattr(socket, "socket", forbidden)
        assert pure.recalculate_infernal_preparation(grading["sheet"], parameters=grading["calculations"]["parameters"]) == grading["calculations"]


def test_supplied_capture_and_request_substitution_reject(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        target, _, _, capture, capture_directory = captured_case(store, tmp_path)
        changed = deepcopy(capture)
        changed["artifacts"][0]["artifact_ref"] = changed["artifacts"][-1]["artifact_ref"]
        monkeypatch.setattr(publication, "run_local_job", forbidden)
        with pytest.raises(ValueError, match="supplied_capture_conflict"):
            publication.prepare_native_infernal_preparation_grading(store, target=target, capture=changed,
                capture_directory=capture_directory, directory=tmp_path / "bad-capture", policy=POLICY)
        target["assignment"]["requested_job"]["argv"].append("forged")
        with pytest.raises(ValueError):
            publication.prepare_native_infernal_preparation_grading(store, target=target, capture=capture,
                capture_directory=capture_directory, directory=tmp_path / "bad-target", policy=POLICY)


def test_supplied_previous_ssi_stays_unverified_without_producer_request(tmp_path):
    indexed = next(r for r in COMPILED_INDEX["cases"] if (r["program"], r["mode"]) == ("cmfetch", "single_key"))
    chosen = json.loads((ROOT / indexed["request_path"]).read_bytes())
    _, index_plan, index_bundle = native_case(tmp_path / "index", "cmfetch", "index",
        change=lambda job: job.update(operands=deepcopy(chosen["operands"])))
    copy = next(r for r in index_bundle["working_copies"] if r["operand_role"] == "models")
    model_path = Path(index_plan["attempt_directory"]) / copy["relative_path"]
    ssi_path = Path(str(model_path) + ".ssi")
    def supplied_index(job):
        job["operands"][0]["path"] = str(model_path)
        raw = ssi_path.read_bytes()
        job["operands"].append({"role": "ssi", "ordinal": 0, "path": str(ssi_path), "format": "infernal_ssi",
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw), "artifact_ref": None})
    target, plan, bundle = native_case(tmp_path / "fetch", "cmfetch", "single_key", change=supplied_index)
    with Store(tmp_path / "store") as store:
        capture, prepared = capture_and_grade(store, tmp_path, target)
        assert prepared["graded"]
        ssi = next(r for r in prepared["occurrences"] if r["role"] == "ssi")
        assert any(f["code"].endswith("artifact_binding_unavailable") and f["record_key"] == ssi["occurrence_ref"] for f in prepared["failures"])
        grading = full(store, prepared)
        assert "artifact_bindings" not in grading["calculations"]["parameters"]
        checks = [c for r in grading["calculations"]["rows"] for c in r["checks"] if c["check"] == "source_binding"]
        assert checks and all(c["outcome"] == "unknown" for c in checks)
