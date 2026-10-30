from copy import deepcopy
import json
import pytest

from test_native_rna_structure_acquisition import F
from gene_annotation_episode.native_rna_structure_result_publication import (validate_prepared_rna_grading,
    validate_rna_structure_publication_inputs, publish_selected_rna_structure_rows, prepare_rna_structure_grading)
from gene_annotation_episode.native_rna_structure_acquisition import capture_local_rna_structure_bundle
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.practical_execution_records import assess_validations
from gene_annotation_episode.rna_structure_result_views import FAMILY_SOURCES
from gene_annotation_episode.state import Store


def test_actual_bounded_worker_full_retained_schema_and_numeric_metric_order(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        capture = capture_local_rna_structure_bundle(store, target=f.target, directory=tmp_path / "capture")
        selected = F.selector("stem", ["stack_count", "stem_length_pairs"])
        prepared = prepare_rna_structure_grading(store, bundle=f.bundle, capture=capture,
            directory=tmp_path / "grading", policy=LocalJobPolicy(**F.POLICY), selector=selected)
        checked = validate_prepared_rna_grading(store, prepared, bundle=f.bundle, capture=capture, selector=selected)
        assert [cell["name"] for cell in checked["document"]["rows"][0]["cells"]] == ["stack_count", "stem_length_pairs"]
        assert [cell["value"] for cell in checked["document"]["rows"][0]["cells"]] == [2, 3]
        assert len(checked["components"]["pairs"]) == 3
        receipt = json.loads(store.get_artifact(prepared["worker_receipt_artifact_ref"]))
        assert receipt["returncode"] == 0 and receipt["metadata"]["verified_cgroup"]["memory_max"] == 21474836480
        F.retain("actual_grading_worker", prepared=prepared, worker_receipt=receipt, **checked)


def test_worker_model_conflict_retains_independent_supplied_topology(tmp_path):
    with Store(tmp_path / "store") as store:
        request = F.CORE.feature_input(energy_mode="viennarna_evaluate")
        f = F.Fixture(store, tmp_path / "fixture", request=request)
        for name in ("native-result.json", "model.json"):
            value = json.loads((f.attempt / name).read_bytes())
            model = value["model"] if name == "native-result.json" else value
            model["selected"]["temperature_c"] = model["effective_settings"]["temperature_c"] = 25.0
            raw = F.encoded(value)
            (f.attempt / name).write_bytes(raw)
            row = next(item for item in f.bundle["files"] if item["relative_path"] == name)
            row.update(sha256=F.sha(raw), size_bytes=len(raw))
        (f.attempt / "bundle.json").write_bytes(F.encoded(f.bundle))
        capture = capture_local_rna_structure_bundle(store, target=f.target, directory=tmp_path / "capture")
        selected = F.selector(metrics=["pair_count", "evaluated_energy_kcal_mol"])
        prepared = prepare_rna_structure_grading(store, bundle=f.bundle, capture=capture,
            directory=tmp_path / "grading", policy=LocalJobPolicy(**F.POLICY), selector=selected)
        checked = validate_prepared_rna_grading(store, prepared, bundle=f.bundle, capture=capture, selector=selected)
        cells = checked["document"]["rows"][0]["cells"]
        assert cells[0]["value"] == 3 and cells[1]["state"] == "incompatible"
        assert cells[1]["reason"] == "rna_native_result_incompatible"
        assert checked["sheet"]["status"] == "partial"


@pytest.mark.parametrize("prediction", [False, True])
def test_actual_adapter_retains_full_components_and_requested_numerical_rows(tmp_path, prediction):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture", prediction=prediction)
        child = f.child()
        body = f.execute(child)
        assert body["native_success"] and body["capture_complete"] and body["delivery_complete"]
        row = body["rows"][0]
        numbers = {value["name"]: value for value in row["measurements"]}
        assert numbers["pair_count"]["value"] == 3
        assert numbers["paired_fraction"]["value"] == 2 / 3
        assert (numbers["paired_fraction"]["numerator"], numbers["paired_fraction"]["denominator"]) == (6, 9)
        assert numbers["long_stem_fraction"]["value"] == numbers["accepted_pair_fraction"]["value"] == 1.0
        full = json.loads(store.get_artifact(body["prepared"]["components_artifact_ref"]))
        assert len(full["pairs"]) == 3 and len(full["stems"]) == 1 and len(full["regions"]) == 2
        assert len(full["summary"]) > len(numbers)
        assert f.results.completion(child)["operation_key"] == body["operation_key"]
        assert len(f.targets.observations) == 1
        F.retain("prediction_delivery" if prediction else "features_delivery", bundle=f.bundle, receipt=body,
            sheet=json.loads(store.get_artifact(body["prepared"]["sheet_artifact_ref"])), components=full)


def test_native_failure_preserves_supplied_topology_and_qualified_delivery(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture", failure=True)
        child = f.child(selection=F.selector(metrics=["pair_count", "paired_fraction", "evaluated_energy_kcal_mol"]),
            sources=[FAMILY_SOURCES["summary"], FAMILY_SOURCES["failure"]])
        body = f.execute(child)
        assert not body["native_success"] and body["capture_complete"] and body["delivery_complete"]
        assert body["rows"][0]["measurements"][0]["value"] == 3
        missing = body["rows"][0]["unavailable"][0]
        assert (missing["name"], missing["state"], missing["reason"], missing["unit"]) == (
            "evaluated_energy_kcal_mol", "failed", "rna_native_dependency_missing", "kcal/mol")
        assert f.results.facts(child)["execution_result_origin"] is None
        F.retain("native_failure_valid_topology", receipt=body)


def test_missing_present_native_file_preserves_capture_failure_and_partial_topology(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        (f.attempt / "native-result.json").unlink()
        child = f.child()
        body = f.execute(child)
        assert body["native_success"] and not body["capture_complete"] and not body["delivery_complete"]
        assert body["rows"][0]["measurements"][0]["value"] == 3
        assert [value["code"] for value in body["failures"]][:2] == ["rna_capture_unavailable", "rna_native_result_missing"]
        assert body["failures"][0]["field"] == "/files/1"


@pytest.mark.parametrize("kind", ["bound", "wrong_bytes", "unreceived", "dna", "reverse"])
def test_subject_binding_checks_actual_order_molecule_receipts_and_orientation(tmp_path, kind):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture", molecule="dna" if kind == "dna" else "rna")
        subject = f.scope["subject_refs"][0]
        artifact = store.get(subject)["sequence_ref"]
        request = deepcopy(f.request)
        request["subject_binding"] = {"subject_ref": subject, "sequence_artifact_ref": artifact, "start": 0, "end": 9,
            "strand": "-" if kind == "reverse" else "+"}
        if kind == "reverse":
            request["sequence"] = "GGGUUUCCC"
        if kind == "wrong_bytes":
            request["subject_binding"]["sequence_artifact_ref"] = store.artifact(b"GGGUUUCCC")
            f.receipts.receive(f.root.episode_id, [request["subject_binding"]["sequence_artifact_ref"]], kind="initial")
        if kind == "unreceived":
            f.store.db.execute("DELETE FROM runtime_record_receipts WHERE record_ref=?", (artifact,))
        child = f.child()
        if kind in {"bound", "reverse"}:
            assert validate_rna_structure_publication_inputs(store, child, original_input=request, capture={}) == request["subject_binding"]
        else:
            with pytest.raises(ValueError, match="rna_subject_binding_conflict"):
                validate_rna_structure_publication_inputs(store, child, original_input=request, capture={})


def test_changed_saved_component_bytes_and_duplicate_publication_rows_rejected(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        child = f.child()
        body = f.execute(child)
        changed = deepcopy(body)
        changed["rows"].append(deepcopy(changed["rows"][0]))
        with pytest.raises(ValueError):
            f.results._validate_body(changed, child.scope)
        meta = store.get(body["prepared"]["components_artifact_ref"])
        (store.path / "artifacts" / meta["sha256"][:2] / meta["sha256"]).write_bytes(b"{}\n")
        with pytest.raises(ValueError):
            f.results.facts(child)


def test_wrong_original_handoff_is_rejected_by_publisher_itself(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        child = f.child()
        body = f.execute(child)
        receipt = deepcopy(f.practical_receipt)
        receipt["operation_key"] = f"{f.run_id}:{f.producer.episode_id}:2"
        native = receipt["outcome"]["facts"]["requested_job"]
        native["execution_id"] = native["handoff"]["execution_id"] = str(f.root_path / "different-attempt/native.json")
        receipt["validations"] = assess_validations(f.assignment, receipt["outcome"], receipt["context_after"],
            checked_at=receipt["finished_at"], tool_name=receipt["tool_name"])
        f.journal.save("runtime_actions", {"episode_id": f.producer.episode_id, "decision_index": 2,
            "action": F.canonical({"kind": "tool", "tool": receipt["tool_name"], "arguments": {}}), "result": None, "credit": None})
        other = PracticalReceiptInformation(store, f.run_id).publish(f.producer, receipt)
        f.receipts.receive(f.root.episode_id, [other], kind="initial")
        f.handoff = other
        wrong_child = f.child(index=1)
        with pytest.raises(ValueError, match="rna_original_attempt_mismatch"):
            publish_selected_rna_structure_rows(store, wrong_child, source_ref=body["source_ref"], bundle=f.bundle,
                capture=body["capture"], prepared=body["prepared"], selector=F.selector())


def test_malformed_worker_success_retains_capture_with_specific_failure(tmp_path, monkeypatch):
    from gene_annotation_episode import native_rna_structure_result_publication as publication
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        original_runner = publication.run_local_job
        def malicious_projection(*args, **kwargs):
            result = original_runner(*args, **kwargs)
            path = kwargs["cwd"] / "selected-rows.json"
            document = json.loads(path.read_bytes())
            document["rows"][0]["cells"][0]["value"] = 999
            path.write_bytes(F.encoded(document))
            return result
        monkeypatch.setattr(publication, "run_local_job", malicious_projection)
        child = f.child(sources=[FAMILY_SOURCES["summary"], FAMILY_SOURCES["failure"]])
        body = f.execute(child)
        assert body["native_success"] and body["capture_complete"] and not body["delivery_complete"]
        assert body["source_ref"] is not None and body["rows"] == [] and body["prepared"] is None
        assert body["failures"][-1]["code"] == "rna_invalid_component_schema"
        f.returned(f.root, child)


def test_publication_binding_conflict_keeps_valid_numerical_rows(tmp_path):
    def request(f):
        artifact = f.store.artifact(b"GGGUUUCCC")
        f.receipts.receive(f.root.episode_id, [artifact], kind="initial")
        return F.CORE.feature_input(subject_binding={"subject_ref": f.scope["subject_refs"][0],
            "sequence_artifact_ref": artifact, "start": 0, "end": 9, "strand": "+"})
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture", request=request)
        child = f.child()
        body = f.execute(child)
        row = body["rows"][0]
        assert row["status"] == "partial" and row["subject_ref"] is None
        assert row["measurements"][0]["value"] == 3
        assert "rna_subject_binding_conflict" in row["qualification_codes"]
        assert body["delivery_complete"]


def test_feature_segments_reverse_complement_and_selected_interval_use_actual_mapping(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        feature = store.put("feature", {"subject_ref": f.scope["subject_refs"][0], "kind": "ncRNA",
            "segments": [{"start": 0, "end": 2}, {"start": 3, "end": 5}, {"start": 7, "end": 9}],
            "strand": "-", "context_refs": []}, origin="tool", scope=f.scope)["id"]
        artifact = store.artifact(b"GGUUCC")
        f.receipts.receive(f.root.episode_id, [feature, artifact], kind="initial")
        request = F.CORE.feature_input("(..)", "GUUC", subject_binding={"subject_ref": feature,
            "sequence_artifact_ref": artifact, "start": 1, "end": 5, "strand": "+"})
        child = f.child()
        assert validate_rna_structure_publication_inputs(store, child, original_input=request, capture={}) == request["subject_binding"]
        request["subject_binding"]["strand"] = "-"
        with pytest.raises(ValueError, match="rna_subject_binding_conflict"):
            validate_rna_structure_publication_inputs(store, child, original_input=request, capture={})
