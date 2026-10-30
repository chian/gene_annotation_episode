"""Actual bounded numerical/publication workers over retained native bytes.

The relocated original execution envelope is a labeled synthetic fixture;
capture, file retention, subprocess grading and projection are real operations.
These checks do not claim episode commissioning or controller integration.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode import native_hmmer_preparation_acquisition as acquisition
from gene_annotation_episode import native_hmmer_preparation_result_publication as publication
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.state import Store
from test_native_hmmer_preparation_result_worker import CASES, capture_native


POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def prepare(store, tmp_path, monkeypatch, program="hmmemit", mode="consensus_simple"):
    root, _, bundle, target, capture = capture_native(store, tmp_path, monkeypatch, program, mode)
    shutil.rmtree(root.parent)
    monkeypatch.setattr(acquisition, "local_hmmer_preparation_plan", lambda *a: pytest.fail("reopened native reservation"))
    prepared = publication.prepare_native_hmmer_preparation_grading(store,
        target=target, capture=capture, capture_directory=tmp_path / "capture",
        directory=tmp_path / "grading", policy=POLICY)
    assert prepared["graded"], prepared
    source = acquisition.publish_original_source(store, bundle=bundle, capture=capture, prepared=prepared)
    return bundle, target, capture, prepared, source


def selector(*, artifacts=(), quantities=(), rows=None):
    return {"version": "native_hmmer_preparation_result_selector_v1",
        "acquisition": "complete_bound_bundle", "artifacts": list(artifacts),
        "projection": {"collection": "calculations", "rows": rows or {"offset": 0, "limit": 1},
            "quantities": list(quantities), "checks": []} if quantities else None}


@pytest.mark.parametrize("program,mode", CASES)
def test_all26_modes_retain_grade_and_publish_only_requested_artifact(tmp_path, monkeypatch, program, mode):
    with Store(tmp_path / "store") as store:
        bundle, target, capture, prepared, source = prepare(store, tmp_path, monkeypatch, program, mode)
        selected = next((r for r in bundle["artifacts"] if r["role"] not in {"stdout", "stderr"}), bundle["artifacts"][0])
        choice = selector(artifacts=[{"direction": "output", "role": selected["role"], "ordinal": 0}])
        full_get = store.get_artifact
        numerical = {prepared[k] for k in ("grading_artifact_ref", "sheet_artifact_ref", "calculations_artifact_ref")}
        def no_full_sheet(reference):
            assert reference not in numerical, "host hydrated full numerical data"
            return full_get(reference)
        monkeypatch.setattr(store, "get_artifact", no_full_sheet)
        result = publication.publish_selected_preparation_result(store, source_ref=source,
            prepared=prepared, selector=choice, directory=tmp_path / "projection", policy=POLICY)
        assert result["rows"] == [] and result["population"]["total_records"] == 0
        assert len(result["artifacts"]) == 1
        artifact = result["artifacts"][0]
        assert artifact["sha256"] == selected["sha256"] and artifact["size_bytes"] == selected["size_bytes"]
        assert result["record_refs"] == [source, artifact["artifact_ref"]]
        assert not numerical.intersection(result["record_refs"])
        monkeypatch.setattr(publication, "run_local_job", lambda *a, **kw: pytest.fail("replay started worker"))
        assert publication.prepare_native_hmmer_preparation_grading(store, target=target, capture=capture,
            capture_directory=tmp_path / "capture", directory=tmp_path / "grading", policy=POLICY) == prepared
        assert publication.validate_publication(store, result, source_ref=source, prepared=prepared,
            selector=choice, directory=tmp_path / "projection", policy=POLICY) == result


@pytest.mark.parametrize("program,mode,path,expected", [
    ("hmmemit", "consensus_simple", "length", 12),
    ("makehmmerdb", "build", "components.source_symbol_total", 28),
    ("makehmmerdb", "build", "components.actual_database_bytes", 314),
])
def test_requested_native_numerical_value_crosses_saved_publication(tmp_path, monkeypatch, program, mode, path, expected):
    with Store(tmp_path / "store") as store:
        _, _, _, prepared, source = prepare(store, tmp_path, monkeypatch, program, mode)
        choice = selector(quantities=[path])
        result = publication.publish_selected_preparation_result(store, source_ref=source,
            prepared=prepared, selector=choice, directory=tmp_path / "projection", policy=POLICY)
        assert len(result["rows"]) == 1
        assert result["rows"][0]["quantities"][0]["value"] == expected
        assert result["rows"][0]["quantities"][0]["state"] == "present"
        # The selected scalar carries only the original files needed to
        # substantiate it, even though no file was explicitly requested.
        expected_roles = {("output", "generated_sequences")} if program == "hmmemit" else (
            {("input", "sequences")} if path.endswith("source_symbol_total")
            else {("output", "fm_database")})
        assert {(r["direction"], r["role"]) for r in result["artifacts"]} == expected_roles
        assert result["population"]["requested_artifact_count"] == 0
        assert result["population"]["returned_artifact_count"] == len(expected_roles)
        assert len(result["rows"][0]["quantities"]) == 1


def test_projection_rejects_changed_selection_and_prepared_identity(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        bundle, _, _, prepared, source = prepare(store, tmp_path, monkeypatch)
        choice = selector(quantities=["length"])
        result = publication.publish_selected_preparation_result(store, source_ref=source,
            prepared=prepared, selector=choice, directory=tmp_path / "projection", policy=POLICY)
        changed = deepcopy(choice)
        changed["projection"]["rows"]["offset"] = 1
        with pytest.raises(ValueError, match="identity_conflict"):
            publication.validate_publication(store, result, source_ref=source, prepared=prepared,
                selector=changed, directory=tmp_path / "projection", policy=POLICY)
        changed = deepcopy(prepared)
        changed["occurrences"][0]["ordinal"] = 9
        with pytest.raises(ValueError, match="identity_conflict"):
            publication.validate_prepared_grading(store, changed, bundle=bundle)


def test_preparation_requires_existing_capture_and_does_not_acquire(tmp_path, monkeypatch):
    monkeypatch.setattr(publication, "capture_local_bundle", lambda *a, **kw: pytest.fail("first capture hidden in grading"))
    with Store(tmp_path / "store") as store:
        prepared = publication.prepare_native_hmmer_preparation_grading(store,
            target={}, capture={}, capture_directory=tmp_path / "capture",
            directory=tmp_path / "grading", policy=POLICY)
        assert not prepared["graded"] and prepared["source_grading_artifact_ref"] is None
        assert prepared["failures"][0]["code"].endswith("completed_capture_required")


def test_captured_artifact_survives_unavailable_grade_worker(tmp_path, monkeypatch):
    """An injected worker-start failure must not hide successfully captured files."""
    with Store(tmp_path / "store") as store:
        root, _, bundle, target, capture = capture_native(store, tmp_path, monkeypatch)
        shutil.rmtree(root.parent)
        original_run = publication.run_local_job

        def unavailable(*args, **kwargs):
            raise OSError("injected numerical worker startup failure")

        monkeypatch.setattr(publication, "run_local_job", unavailable)
        prepared = publication.prepare_native_hmmer_preparation_grading(store,
            target=target, capture=capture, capture_directory=tmp_path / "capture",
            directory=tmp_path / "grading", policy=POLICY)
        assert not prepared["graded"]
        assert all(prepared[k] is None for k in ("grading_artifact_ref", "sheet_artifact_ref", "calculations_artifact_ref"))
        assert prepared["failures"]
        source = acquisition.publish_original_source(store, bundle=bundle, capture=capture, prepared=prepared)
        monkeypatch.setattr(publication, "run_local_job", original_run)
        choice = selector(artifacts=[{"direction": "output", "role": "generated_sequences", "ordinal": 0}])
        result = publication.publish_selected_preparation_result(store, source_ref=source,
            prepared=prepared, selector=choice, directory=tmp_path / "projection", policy=POLICY)
        assert result["rows"] == [] and len(result["artifacts"]) == 1
        assert result["artifacts"][0]["role"] == "generated_sequences"
        assert result["failures"] == prepared["failures"]
        with pytest.raises(ValueError, match="saved_numerical_grading_unavailable"):
            publication.publish_selected_preparation_result(store, source_ref=source,
                prepared=prepared, selector=selector(quantities=["length"]),
                directory=tmp_path / "numeric-projection", policy=POLICY)
        monkeypatch.setattr(publication, "run_local_job", lambda *a, **kw: pytest.fail("replay restarted worker"))
        assert publication.validate_publication(store, result, source_ref=source, prepared=prepared,
            selector=choice, directory=tmp_path / "projection", policy=POLICY) == result
        with pytest.raises(ValueError, match="saved_numerical_grading_unavailable"):
            publication.publish_selected_preparation_result(store, source_ref=source,
                prepared=prepared, selector=selector(quantities=["length"]),
                directory=tmp_path / "numeric-projection", policy=POLICY)


def test_original_saved_alimask_publication_keeps_absent_context_and_frozen_numbers(tmp_path, monkeypatch):
    """Reuse the actual 277 closed publication; never rerun its native job/grade."""
    import hashlib
    from gene_annotation_episode import native_hmmer_preparation_result_worker as worker
    from gene_annotation_episode import hmmer_alignment_preparation_calculations as calculations
    root = Path(__file__).resolve().parents[1]
    original = root / "verification/tool_graders_hmmer_preparation_workflow_2026-10-26_277/check009/temporary/test_all_native_modes_through_3"
    prepared_path, = original.rglob("prepared.json")
    projection_path, = original.rglob("native-hmmer-preparation-projection/publication.json")
    prepared_bytes, projection_bytes = prepared_path.read_bytes(), projection_path.read_bytes()
    assert hashlib.sha256(prepared_bytes).hexdigest() == "85824c53c759e26aacebed9d8ad295578f3fbf3b9b208ee985d633678441652c"
    assert hashlib.sha256(projection_bytes).hexdigest() == "43ce501621049bc2c2c3b838fb958fab91a0b1acaa835eb6ff53d9d9714d94b0"
    shutil.copytree(original / "state", tmp_path / "state")
    # Verification snapshots are immutable. Store needs a writable copied DB
    # for its normal WAL initialization; keep the historical source untouched.
    for copied in [tmp_path / "state", *(tmp_path / "state").rglob("*")]:
        copied.chmod(0o755 if copied.is_dir() else 0o644)
    shutil.copytree(projection_path.parent, tmp_path / "projection/native-hmmer-preparation-projection")
    prepared = json.loads(prepared_bytes)
    selected = json.loads(projection_bytes)
    intent = json.loads((projection_path.parent / "intent.json").read_bytes())
    def forbidden(*args, **kwargs):
        raise AssertionError("old publication replay performed native work, acquisition or numerical grading")
    for module, name in ((publication, "run_local_job"), (publication, "capture_local_bundle"),
                         (worker, "_grade"), (calculations, "reconstruct_alimask_model_map")):
        monkeypatch.setattr(module, name, forbidden)
    with Store(tmp_path / "state") as store:
        stable = publication._stable(store, prepared)
        assert stable["effective_metadata"] == {}
        frozen = store.get_artifact(prepared["grading_artifact_ref"])
        assert json.loads(frozen)["metadata"] == {}
        bundle = json.loads(store.get_artifact(prepared["bundle_artifact_ref"]))
        assert publication.validate_prepared_grading(store, prepared, bundle=bundle) == prepared
        assert publication.validate_publication(store, selected, source_ref=intent["source_ref"],
            prepared=prepared, selector=intent["selector"], directory=tmp_path / "projection", policy=POLICY) == selected
        assert store.get_artifact(prepared["grading_artifact_ref"]) == frozen
        assert publication._stable(store, prepared)["effective_metadata"] == {}
        assert [q["value"] for q in selected["rows"][0]["quantities"]] == [3, 14, 12, 1, 1, None]
    assert prepared_path.read_bytes() == prepared_bytes and projection_path.read_bytes() == projection_bytes


def test_new_alimask_context_is_bound_in_publication_and_checked_on_replay(tmp_path, monkeypatch):
    from gene_annotation_episode import native_hmmer_preparation_result_worker as worker
    with Store(tmp_path / "store") as store:
        bundle, _, _, prepared, source = prepare(store, tmp_path, monkeypatch, "alimask", "alignment_to_model")
        stable = publication._stable(store, prepared)
        context = stable["effective_metadata"]["map_reconstruction_context"]
        alignment = next(r for r in prepared["occurrences"] if (r["direction"], r["role"], r["ordinal"]) == ("input", "alignment", 0))
        assert context["source_occurrence_id"] == alignment["occurrence_id"]
        assert context["source_sha256"] == alignment["sha256"]
        assert context["producer"]["executable_sha256"] == bundle["software"]["actual_sha256"]
        assert context["effective_pb_config"]["seed"] == 42
        grading = json.loads(store.get_artifact(prepared["grading_artifact_ref"]))
        assert grading["metadata"]["map_reconstruction_context"] == context
        assert grading["sheet"]["input_records"][0]["map_reconstruction_context"] == context
        choice = selector(quantities=["components.mapped_model_position_count"])
        result = publication.publish_selected_preparation_result(store, source_ref=source,
            prepared=prepared, selector=choice, directory=tmp_path / "projection", policy=POLICY)
        frozen = store.get_artifact(prepared["grading_artifact_ref"])
        monkeypatch.setattr(publication, "run_local_job", lambda *a, **kw: pytest.fail("replay started worker"))
        monkeypatch.setattr(worker, "_grade", lambda *a, **kw: pytest.fail("replay recomputed grade"))
        assert publication.validate_publication(store, result, source_ref=source, prepared=prepared,
            selector=choice, directory=tmp_path / "projection", policy=POLICY) == result
        altered = deepcopy(stable)
        altered["effective_metadata"]["map_reconstruction_context"]["source_sha256"] = "0" * 64
        changed = deepcopy(prepared)
        changed["source_grading_artifact_ref"] = publication.retain_tool_grading(store,
            provider="episode.execution_result", native_artifact_ref=prepared["bundle_artifact_ref"], grading=altered)
        with pytest.raises(ValueError, match="prepared_grading_custody_conflict"):
            publication.validate_prepared_grading(store, changed, bundle=bundle)
        assert store.get_artifact(prepared["grading_artifact_ref"]) == frozen
