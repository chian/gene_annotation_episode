"""Preparation custody, real bounded grading, typed projection and offline replay.

Four original252 captures are reused unchanged. Additional tiny native jobs use
the actual251 reservation/driver and existing native_lifecycle under local_jobs.
Malformed cases are explicitly synthetic mutations, never native measurements.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.library import native_infernal_preparation_acquisition as acquisition
from gene_annotation_episode.episodic_workflow.root.library import native_infernal_preparation_result_publication as publication
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_infernal_contracts import native_infernal_digest as digest
from gene_annotation_episode.episodic_workflow.root.library.native_infernal_preparation_contracts import requested_job_from_infernal_preparation
from gene_annotation_episode.episodic_workflow.root.library.native_infernal_preparation_local import prepare_local_infernal_preparation
from gene_annotation_episode.episodic_workflow.root.a101.practical_execution_state import _immutable
from gene_annotation_episode.state import Store

from test_native_infernal_preparation_result_worker import ROOT, forbidden, selector


POLICY = LocalJobPolicy(5 * 1024 ** 3, 4 * 1024 ** 3)
COMPILED_INDEX = json.loads((ROOT / "gene_annotation_episode/episodic_workflow/root/a107/tests/fixtures/infernal_preparation/compiled/NATIVE_COMPILED_INDEX_001.json").read_bytes())


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
