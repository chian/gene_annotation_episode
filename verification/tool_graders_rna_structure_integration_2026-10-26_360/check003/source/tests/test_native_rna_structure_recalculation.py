from copy import deepcopy
import builtins
import json
import shutil
import pytest

from test_native_rna_structure_acquisition import F
from gene_annotation_episode.rna_structure_result_views import FAMILY_SOURCES, SAVED_SOURCE
from gene_annotation_episode.state import Store


def original(f, *, descriptor=True):
    child = f.child(sources=[FAMILY_SOURCES["summary"], SAVED_SOURCE] if descriptor else [FAMILY_SOURCES["summary"]])
    body = f.execute(child)
    f.returned(f.root, child)
    return child, body


def forbid(*a, **k):
    raise AssertionError("saved-sheet work attempted original acquisition or native parsing")


def test_saved_recalculation_new_generation_no_original_paths_or_acquisition(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        first, body = original(f)
        selected = f.saved_selector(body)
        child = f.child(selection=selected, index=1)
        before_receipt = F.encoded(body)
        before_sheet = store.get_artifact(body["prepared"]["sheet_artifact_ref"])
        before_observations = list(f.targets.observations)
        shutil.rmtree(f.native_root)
        (f.root_path / "supplied-input.json").unlink()
        monkeypatch.setattr("gene_annotation_episode.native_rna_structure_results.capture_local_rna_structure_bundle", forbid)
        monkeypatch.setattr("gene_annotation_episode.native_rna_structure_local.local_rna_structure_plan", forbid)
        monkeypatch.setattr(f.targets, "observe_target", forbid)
        monkeypatch.setattr("gene_annotation_episode.rna_structure_native.parse_rna_native_record", forbid)
        monkeypatch.setattr("socket.create_connection", forbid)
        fresh = f.execute(child)
        values = {value["name"]: value["value"] for value in fresh["rows"][0]["measurements"]}
        assert values == {"pair_count": 3, "paired_fraction": 2/3, "long_stem_fraction": 0.0, "accepted_pair_fraction": 0.0}
        assert fresh["rows"][0]["calculation_key"] != body["rows"][0]["calculation_key"]
        assert fresh["source_ref"] == body["source_ref"] and fresh["observation"] == body["observation"]
        assert fresh["capture"] == body["capture"] and fresh["delivery_complete"]
        assert fresh["prepared"]["source_grading_artifact_ref"] == body["prepared"]["source_grading_artifact_ref"]
        assert store.get_artifact(body["prepared"]["sheet_artifact_ref"]) == before_sheet
        assert f.results._saved_directory(first.episode_id, body["operation_key"]).joinpath("receipt.json").read_bytes() == before_receipt
        assert f.targets.observations == before_observations
        assert f.results.credit_view(child, {"known_record_refs": [body["source_ref"]], "initial_known_record_refs": [body["source_ref"]]})["new_acquired_record_count"] == 0
        assert f.results.facts(child)["execution_result_origin"] is None
        F.retain("saved_recalculation", original_receipt=body, selector=selected, recalculation_receipt=fresh)


@pytest.mark.parametrize("problem", ["missing", "tampered"])
def test_saved_sheet_loss_reports_specific_failure_without_reacquisition(tmp_path, monkeypatch, problem):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        first, body = original(f)
        selected = f.saved_selector(body)
        child = f.child(selection=selected, sources=[FAMILY_SOURCES["summary"], FAMILY_SOURCES["failure"]], index=1)
        meta = store.get(selected["saved_input"]["sheet_artifact_ref"])
        path = store.path / "artifacts" / meta["sha256"][:2] / meta["sha256"]
        path.unlink() if problem == "missing" else path.write_bytes(b"{}\n")
        monkeypatch.setattr("gene_annotation_episode.native_rna_structure_results.capture_local_rna_structure_bundle", forbid)
        monkeypatch.setattr(f.targets, "observe_target", forbid)
        fresh = f.execute(child)
        assert not fresh["delivery_complete"] and fresh["rows"] == []
        expected = "rna_capture_unavailable" if problem == "missing" else "rna_capture_digest_mismatch"
        assert expected in [row["code"] for row in fresh["failures"]]
        assert fresh["source_ref"] == body["source_ref"]


def test_correct_handles_without_prior_typed_descriptor_are_insufficient(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        first, body = original(f, descriptor=False)
        selected = f.saved_selector(body)
        handles = [selected["saved_input"][key] for key in ("handoff_ref", "source_ref", "bundle_artifact_ref", "sheet_artifact_ref")]
        f.receipts.receive(f.root.episode_id, handles, kind="initial")
        child = f.child(selection=selected, index=1)
        with pytest.raises(ValueError, match="saved_input_not_received"):
            f.returns.resolve_saved_rna_input(child, selected["saved_input"])


def test_later_sibling_descriptor_cannot_cross_earlier_frozen_prefix(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        early = f.child(role="scientific_process", index=0, sources=[SAVED_SOURCE])
        later = f.child(index=1, sources=[SAVED_SOURCE])
        body = f.execute(later)
        f.returned(f.root, later)
        selected = f.saved_selector(body)
        with pytest.raises(ValueError, match="saved_input_not_received"):
            f.returns.resolve_saved_rna_input(early, selected["saved_input"])


def test_saved_status_uses_historical_observation_and_publishes_no_science(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        first, body = original(f)
        child = f.child(selection=f.saved_selector(body), index=1)
        monkeypatch.setattr(f.targets, "observe_target", forbid)
        monkeypatch.setattr("gene_annotation_episode.native_rna_structure_results.capture_local_rna_structure_bundle", forbid)
        status = f.execute(child, name="execution.results.status")
        assert status["observation"] == body["observation"]
        assert status["source_ref"] is None and status["rows"] == status["record_refs"] == []
        assert not status["delivery_complete"]


def test_saved_initial_inputs_support_real_before_save_build_boundary(tmp_path):
    from gene_annotation_episode.native_rna_structure_result_publication import validate_rna_structure_selected_inputs
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        first, body = original(f)
        selected = f.saved_selector(body)
        child = f.child(selection=selected, index=1)
        store.db.execute("DELETE FROM runtime_episodes WHERE run_id=? AND episode_id=?", (f.run_id, child.episode_id))
        refs = validate_rna_structure_selected_inputs(store, child, selected, handoff_ref=f.handoff, returns=f.returns)
        assert refs == [selected["saved_input"][key] for key in ("handoff_ref", "source_ref", "bundle_artifact_ref", "sheet_artifact_ref")]
        assert f.results.retained_reference_access(child, selected["saved_input"]["sheet_artifact_ref"], "artifact") is True


def test_initial_empty_facts_and_form_validate_before_child_is_saved(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        child = f.child()
        store.db.execute("DELETE FROM runtime_episodes WHERE run_id=? AND episode_id=?", (f.run_id, child.episode_id))
        schema = F.plain(child.request)["report_contract"]["measurements"]["schema"]
        facts = f.results.facts(child)
        assert facts[FAMILY_SOURCES["summary"]] == [] and facts["execution_result_refs"] == []
        f.returns.validate_received_report(child, {"value_0": []}, schema)
