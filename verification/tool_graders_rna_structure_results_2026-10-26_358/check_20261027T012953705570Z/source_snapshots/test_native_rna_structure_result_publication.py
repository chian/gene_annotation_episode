from copy import deepcopy
import json
import pytest

from test_native_rna_structure_acquisition import F
from gene_annotation_episode.native_rna_structure_result_publication import (validate_prepared_rna_grading,
    validate_rna_structure_publication_inputs, publish_selected_rna_structure_rows)
from gene_annotation_episode.rna_structure_result_views import FAMILY_SOURCES
from gene_annotation_episode.state import Store


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
        f = F.Fixture(store, tmp_path / "fixture")
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
        if kind == "dna":
            other = store.create_problem(raw_sequence="GGGAAACCC", molecule="dna")["subject_refs"][0]
            request["subject_binding"]["subject_ref"] = other
            f.receipts.receive(f.root.episode_id, [other], kind="initial")
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
