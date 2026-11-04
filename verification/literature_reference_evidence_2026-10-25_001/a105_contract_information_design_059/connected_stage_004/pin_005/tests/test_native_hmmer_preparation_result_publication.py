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
