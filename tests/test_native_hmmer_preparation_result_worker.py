"""Bounded retained-native grading; synthetic custody is labeled explicitly."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode import native_hmmer_preparation_acquisition as acquisition
from gene_annotation_episode import native_hmmer_preparation_result_worker as worker
from gene_annotation_episode.native_hmmer_preparation_contracts import PROGRAM_MODES
from gene_annotation_episode.state import Store
from test_native_hmmer_preparation_acquisition import (
    ROOT, RETAINED, read_native, synthetic_custody,
)


CASES = [(p, m) for p, modes in PROGRAM_MODES.items() for m in modes]
CURRENT_SIM = ROOT / "verification/tool_graders_hmmer_preparation_capture_2026-10-26_270/check005/temporary"


def current_sim_plan(mode):
    for path in CURRENT_SIM.glob("test_actual_all_selected_modes*/plan.json"):
        if path.parent.is_symlink():
            continue
        plan, bundle = read_native(path)
        if bundle["mode"] == mode:
            return path
    raise AssertionError("current actual simulation evidence missing")


def capture_native(store, tmp_path, monkeypatch, program="hmmemit", mode="consensus_simple", retained_plan=None):
    if program == "hmmsim" and retained_plan is None:
        retained_plan = current_sim_plan(mode)
    # The original numerical bytes are native; only relocated custody paths and
    # execution owner are synthetic. No HMMER execution occurs in these tests.
    with monkeypatch.context() as scoped:
        root, original_plan, bundle, target = synthetic_custody(
            tmp_path, scoped, program, mode, retained_plan=retained_plan)
        capture = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
    return root, original_plan, bundle, target, capture


def worker_plan(store, tmp_path, original_plan, bundle, capture):
    occurrences, failures = worker.qualified_occurrences(bundle, capture["bundle_artifact_ref"], capture)
    metadata, problems = worker.effective_metadata(bundle, occurrences)
    directory = tmp_path / "numerical-worker"
    directory.mkdir()
    files = []
    for row in worker.eligible_occurrences(occurrences):
        path = store.path / "artifacts" / row["sha256"][:2] / row["sha256"]
        files.append({"occurrence_id": row["occurrence_id"], "path": str(path)})
    return {"version": worker.PLAN_VERSION, "task": "grade", "directory": str(directory),
        "bundle": bundle, "original_plan": original_plan, "bundle_artifact_ref": capture["bundle_artifact_ref"],
        "capture": capture, "occurrences": occurrences, "effective_metadata": metadata,
        "files": files, "failures": worker.unique_failures([*failures, *problems])}


def saved_grading(plan):
    return json.loads((Path(plan["directory"]) / "grading.json").read_bytes())


@pytest.mark.parametrize("program,mode", CASES)
def test_all26_retained_native_modes_reach_numerical_artifacts(tmp_path, monkeypatch, program, mode):
    with Store(tmp_path / "store") as store:
        root, original, bundle, _, capture = capture_native(store, tmp_path, monkeypatch, program, mode)
        plan = worker_plan(store, tmp_path, original, bundle, capture)
        shutil.rmtree(root.parent)
        result = worker.run(plan)
        assert result["completed"], result
        assert set(result["outputs"]) == set(worker.NUMERICAL_FILES)
        grading = saved_grading(plan)
        assert grading["operation"] == bundle["operation"]
        assert grading["requested_parameters"] == bundle["requested_job"]["native_hmmer_preparation"]["grading_parameters"]
        assert grading["formats"] == {r["occurrence_id"]: r["format"] for r in worker.eligible_occurrences(plan["occurrences"])}
        assert grading["sheet"] and grading["calculations"]
        monkeypatch.setattr(worker, "_grade", lambda *a: pytest.fail("replay recalculated"))
        assert worker.run(plan) == result


def test_binary_aliases_keep_distinct_occurrences_and_single_model_population(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        _, original, bundle, _, capture = capture_native(store, tmp_path, monkeypatch, "hmmconvert", "binary")
        plan = worker_plan(store, tmp_path, original, bundle, capture)
        selected = [r for r in plan["occurrences"] if r["role"] in {"stdout", "converted_models"}]
        assert len(selected) == 2
        assert selected[0]["artifact_ref"] == selected[1]["artifact_ref"]
        assert selected[0]["occurrence_id"] != selected[1]["occurrence_id"]
        assert worker.run(plan)["completed"]
        grading = saved_grading(plan)
        extracts = grading["sheet"]["model_extractions"]
        assert [e["occurrence"]["role"] for e in extracts] == ["models", "converted_models"]
        assert extracts[-1]["population"] == {"decoded_count": 1, "complete": True, "state": "decoded"}
        assert len(extracts[-1]["records"]) == 1


def test_partial_native_conversion_keeps_valid_first_model_and_failure(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        _, original, bundle, _, capture = capture_native(store, tmp_path, monkeypatch,
            retained_plan=RETAINED / "test_actual_conversion_failure0/plan.json")
        plan = worker_plan(store, tmp_path, original, bundle, capture)
        result = worker.run(plan)
        assert result["completed"] and bundle["returncode"] == 1
        assert any(r["code"].endswith("native_execution_unsuccessful") for r in result["failures"])
        grading = saved_grading(plan)
        assert len(grading["sheet"]["output_records"]) == 1
        assert grading["sheet"]["issues"] or grading["calculations"]["issues"]


@pytest.mark.parametrize("program,mode,roles", [
    ("hmmfetch", "index", {"ssi"}),
    ("hmmpress", "index", {"binary_models", "ssi_index", "msv_profiles", "remaining_profiles"}),
])
def test_current_index_binding_names_exact_source_copy_and_attempt(tmp_path, monkeypatch, program, mode, roles):
    with Store(tmp_path / "store") as store:
        _, original, bundle, _, capture = capture_native(store, tmp_path, monkeypatch, program, mode)
        plan = worker_plan(store, tmp_path, original, bundle, capture)
        occurrences = {r["occurrence_id"]: r for r in plan["occurrences"]}
        bindings = plan["effective_metadata"]["artifact_bindings"]
        assert {occurrences[r["artifact_occurrence_id"]]["role"] for r in bindings} == roles
        for binding in bindings:
            assert occurrences[binding["source_occurrence_id"]]["role"] == "models"
            assert binding["producer_attempt_id"] == bundle["identity"]["attempt_id"]
            assert binding["source_sha256"] == occurrences[binding["source_occurrence_id"]]["sha256"]
        assert worker.run(plan)["completed"]


def test_fm_build_uses_original_recorded_abi_and_source_relationships(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        _, original, bundle, _, capture = capture_native(store, tmp_path, monkeypatch, "makehmmerdb", "build")
        plan = worker_plan(store, tmp_path, original, bundle, capture)
        metadata = plan["effective_metadata"]
        assert metadata["producer_contract"]["byte_order"] == bundle["native_abi"]["byte_order"]
        assert metadata["source_binding"]["producer_attempt_id"] == bundle["identity"]["attempt_id"]
        assert worker.run(plan)["completed"]
        row = next(r for r in saved_grading(plan)["calculations"]["rows"] if r["kind"] == "database_summary")
        assert row["components"]["source_symbol_total"]["value"] == 28
        assert row["components"]["actual_database_bytes"]["value"] == 314


@pytest.mark.parametrize("fault", ["files_reordered", "metadata", "occurrences", "bundle"])
def test_changed_authenticated_worker_inputs_produce_specific_failure(tmp_path, monkeypatch, fault):
    with Store(tmp_path / "store") as store:
        _, original, bundle, _, capture = capture_native(store, tmp_path, monkeypatch)
        plan = worker_plan(store, tmp_path, original, bundle, capture)
        if fault == "files_reordered":
            plan["files"].reverse()
        elif fault == "metadata":
            plan["effective_metadata"] = {"made_up": 1}
        elif fault == "occurrences":
            plan["occurrences"][0]["ordinal"] = 9
        else:
            plan["bundle"]["operation"]["mode"] = "sample_core_unaligned"
        result = worker.run(plan)
        assert not result["completed"] and result["failures"] and not result["outputs"]


def test_missing_retained_model_preserves_generated_output_measurements(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        _, original, bundle, _, capture = capture_native(store, tmp_path, monkeypatch)
        plan = worker_plan(store, tmp_path, original, bundle, capture)
        source = next(r for r in plan["occurrences"] if r["direction"] == "input" and r["role"] == "models")
        entry = next(r for r in plan["files"] if r["occurrence_id"] == source["occurrence_id"])
        Path(entry["path"]).unlink()
        result = worker.run(plan)
        assert result["completed"], result
        assert any(r["stage"] == "reading" and r["record_key"] == source["occurrence_id"] for r in result["failures"])
        grading = saved_grading(plan)
        assert source["occurrence_id"] not in grading["formats"]
        assert len(grading["sheet"]["output_records"]) == 1


def test_saved_worker_identity_and_numerical_bytes_are_checked(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        _, original, bundle, _, capture = capture_native(store, tmp_path, monkeypatch)
        plan = worker_plan(store, tmp_path, original, bundle, capture)
        assert worker.run(plan)["completed"]
        changed = deepcopy(plan)
        changed["effective_metadata"] = {"invented": True}
        with pytest.raises(ValueError, match="identity_conflict"):
            worker.run(changed)
        (Path(plan["directory"]) / "sheet.json").write_text("{}")
        with pytest.raises(ValueError, match="retained_bytes_mismatch"):
            worker.run(plan)


def test_effective_alimask_context_is_optional_only_for_saved_legacy_validation(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        _, _, bundle, _, capture = capture_native(store, tmp_path, monkeypatch, "alimask", "alignment_to_model")
        occurrences, _ = worker.qualified_occurrences(bundle, capture["bundle_artifact_ref"], capture)
        current, failures = worker.effective_metadata(bundle, occurrences, include_map_context=True)
        old, old_failures = worker.effective_metadata(bundle, occurrences, include_map_context=False)
        assert not failures and not old_failures and old == {}
        source = next(r for r in occurrences if (r["direction"], r["role"], r["ordinal"]) == ("input", "alignment", 0))
        context = current["map_reconstruction_context"]
        assert context["source_occurrence_id"] == source["occurrence_id"]
        assert context["source_sha256"] == source["sha256"]
        missing = [r for r in occurrences if r is not source]
        assert worker.effective_metadata(bundle, missing)[0] == {}
        partial = deepcopy(occurrences)
        next(r for r in partial if r["occurrence_id"] == source["occurrence_id"])["completeness"] = "partial"
        assert worker.effective_metadata(bundle, partial)[0] == {}
        unavailable = deepcopy(bundle)
        unavailable["software"]["actual_sha256"] = None
        unknown = worker.effective_metadata(unavailable, occurrences)[0]["map_reconstruction_context"]
        assert unknown["producer"]["executable_sha256"] is None
        assert unknown["binding"] == "unavailable" and unknown["profile"] is unknown["effective_pb_config"] is None
