from copy import deepcopy
import importlib.util
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode.native_rna_structure_acquisition import capture_local_rna_structure_bundle, validate_capture
from gene_annotation_episode.state import Store

PACKET = Path(__file__).resolve().parents[1] / "verification/tool_graders_rna_structure_results_2026-10-26_358"
SPEC = importlib.util.spec_from_file_location("rna358_fixture_helpers", PACKET / "fixture_helpers.py")
F = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(F)


def test_full_capture_replays_saved_bytes_without_original_files(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        capture = capture_local_rna_structure_bundle(store, target=f.target, directory=tmp_path / "capture")
        assert capture["bundle_validated"] and capture["capture_complete"]
        assert [row["role"] for row in capture["artifacts"]] == ["input", "native_result", "stdout", "stderr"]
        assert store.get_artifact(capture["artifacts"][1]["artifact_ref"]) == (f.attempt / "native-result.json").read_bytes()
        shutil.rmtree(f.native_root)
        monkeypatch.setattr("gene_annotation_episode.native_rna_structure_local.local_rna_structure_plan",
            lambda *a, **k: pytest.fail("reopened original reservation"))
        assert capture_local_rna_structure_bundle(store, target=f.target, directory=tmp_path / "capture") == capture
        F.retain("complete_capture", bundle=f.bundle, capture=capture)


@pytest.mark.parametrize("problem", ["missing", "changed", "symlink"])
def test_present_file_failures_keep_exact_cause_and_invalid_bytes(tmp_path, problem):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        output = f.attempt / "native-result.json"
        output.unlink()
        if problem == "changed":
            output.write_bytes(b"tampered diagnostic bytes\n")
        if problem == "symlink":
            output.symlink_to(f.root_path / "supplied-input.json")
        capture = capture_local_rna_structure_bundle(store, target=f.target, directory=tmp_path / "capture")
        assert capture["bundle_validated"] and not capture["capture_complete"]
        assert capture["failures"] == [F.issue("rna_capture_digest_mismatch" if problem == "changed" else "rna_capture_unavailable",
            stage="capture", record_key=f.job["record_key"], field="/files/1", artifact_role="native_result")]
        assert bool(capture["invalid_artifacts"]) == (problem == "changed")
        if problem == "changed":
            assert store.get_artifact(capture["invalid_artifacts"][0]["artifact_ref"]) == b"tampered diagnostic bytes\n"
        assert validate_capture(store, capture, bundle=f.bundle) == capture
        F.retain("capture_" + problem, capture=capture, expected_manifest=f.bundle)


def test_honest_native_absence_is_complete_custody(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture", failure=True)
        capture = capture_local_rna_structure_bundle(store, target=f.target, directory=tmp_path / "capture")
        assert capture["capture_complete"] and not capture["failures"]
        assert [row["role"] for row in capture["absent_artifacts"]] == ["model", "effective_parameters"]


@pytest.mark.parametrize("mutation,code", [
    (lambda b: b.update(sealed=False), "rna_unsealed_native_attempt"),
    (lambda b: b["identity"].update(episode_id="sibling"), "rna_original_attempt_mismatch"),
    (lambda b: b["files"][1].update(relative_path="../sibling"), "rna_original_attempt_mismatch"),
    (lambda b: b["files"][1].update(role="stdout"), "rna_original_attempt_mismatch"),
    (lambda b: b.update(record_key="wrong-record"), "rna_original_attempt_mismatch"),
])
def test_untrusted_bundle_returns_only_original_capture_identity(tmp_path, mutation, code):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        wrong = deepcopy(f.bundle)
        mutation(wrong)
        (f.attempt / "bundle.json").write_bytes(F.encoded(wrong))
        capture = capture_local_rna_structure_bundle(store, target=f.target, directory=tmp_path / "capture")
        assert not capture["bundle_validated"] and not capture["capture_complete"]
        assert capture["artifacts"] == capture["invalid_artifacts"] == []
        assert capture["failures"] == [F.issue(code, stage="capture", record_key=f.job["record_key"])]


@pytest.mark.parametrize("raw", [b"{}\n{}\n", b'{"a":1,"a":2}\n', b'{"n":NaN}\n', b"\xef\xbb\xbf{}\n", b"{ }\n"])
def test_noncanonical_manifest_is_retained_but_never_scientific_source(tmp_path, raw):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        (f.attempt / "bundle.json").write_bytes(raw)
        capture = capture_local_rna_structure_bundle(store, target=f.target, directory=tmp_path / "capture")
        assert not capture["bundle_validated"]
        assert store.get_artifact(capture["bundle_artifact_ref"]) == raw


def test_capture_replay_rejects_mutated_retained_bytes_and_target(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        capture = capture_local_rna_structure_bundle(store, target=f.target, directory=tmp_path / "capture")
        changed = deepcopy(f.target)
        changed["origin_episode_id"] = "other"
        with pytest.raises(ValueError):
            capture_local_rna_structure_bundle(store, target=changed, directory=tmp_path / "capture")
        row = capture["artifacts"][0]
        path = store.path / "artifacts" / row["sha256"][:2] / row["sha256"]
        path.write_bytes(b"corruption")
        with pytest.raises(ValueError):
            capture_local_rna_structure_bundle(store, target=f.target, directory=tmp_path / "capture")
