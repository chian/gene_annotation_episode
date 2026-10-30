"""Synthetic selected kinetic model storage and exact admitted subsets."""
from copy import deepcopy
from dataclasses import replace
import json
import math

import pytest

from gene_annotation_episode.communication import validate_form, plain
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository
from gene_annotation_episode.literature_kinetic_model_storage import (
    LiteratureKineticModelRepository, COMPONENTS, kinetic_model_cells_schema,
)
from gene_annotation_episode.state import Store
from test_literature_kinetic_model_inputs import setup_model


def populate(store, context, native_args, model_args):
    native = LiteratureKineticRepository(store, context.run_id).populate(context, native_args, "native")
    owner = replace(context, received_record_refs=(*context.received_record_refs, *native["record_refs"]))
    args = {**model_args, "source_ref": native["result"]["sheet_ref"]}
    repo = LiteratureKineticModelRepository(store, context.run_id)
    outcome = repo.populate(owner, args, "model")
    owner = replace(owner, received_record_refs=(*owner.received_record_refs, *outcome["record_refs"]))
    return repo, owner, args, outcome, native


@pytest.mark.parametrize("status", ["known", "estimated", "unknown", "absent"])
def test_actual_existing_numeric_cells_preserve_known_estimated_and_missing_meanings(tmp_path, status):
    store, context, native_args, model_args, _, _ = setup_model(tmp_path, status="known" if status == "absent" else status)
    with store:
        if status == "absent":
            model_args.update(model_source_ref=None, model_witnesses=[])
        repo, owner, args, outcome, native = populate(store, context, native_args, model_args)
        rows = repo.fact_cells(owner, [outcome["result"]["sheet_ref"]], components=COMPONENTS)
        validate_form({"numbers": rows}, obj({"numbers": kinetic_model_cells_schema()}), lambda *_: True)
        assert [r["component"] for r in rows] == list(COMPONENTS)
        assert all(r["numerator"]["parameter_kind"] == "Km" and r["numerator"]["canonical_unit"] == "uM" for r in rows)
        assert all(r["contrast_meaning"] == "numerator_parameter_exceeds_denominator" for r in rows)
        if status in ("known", "estimated"):
            assert rows[0]["value"] == pytest.approx(.11)
            assert rows[1]["value"] == pytest.approx(math.sqrt(.11))
            if status == "known":
                assert rows[2]["value"] == pytest.approx(2.1838773359918244)
                assert rows[3]["value"] == pytest.approx(.7975846370428177)
            else:
                assert rows[2]["unavailable_reason"] == "known_log_covariance_required"
                assert rows[3]["value"] is None
        else:
            assert all(r["value"] is None for r in rows)
            assert rows[0]["unavailable_reason"] == ("kinetic_log_model_unreported" if status == "absent" else "covariance_status_unknown")
        assert repo.populate(owner, args, "model") == outcome
        native_saved = LiteratureKineticRepository(store, context.run_id).read(native["result"]["sheet_ref"])
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert saved["calculation"]["inputs"] == native_saved["extraction"]["calculation_inputs"]
        assert {k: saved["calculation"]["cells"][k] for k in native["result"]["cells"]} == native["result"]["cells"]
        assert native_saved["calculation"]["model"] is None
        assert not store.list("assessment") and not store.list("observation")


@pytest.mark.parametrize("n,reason", [("<20", "censored_measurement"), ("about 20", "approximate_parameter_model_unsupported")])
def test_censoring_and_approximation_are_not_silently_made_exact(tmp_path, n, reason):
    store, context, native_args, model_args, _, _ = setup_model(tmp_path, n=n)
    with store:
        repo, owner, _, outcome, _ = populate(store, context, native_args, model_args)
        rows = repo.fact_cells(owner, [outcome["result"]["sheet_ref"]], components=COMPONENTS)
        assert rows[2]["value"] is None and rows[2]["unavailable_reason"] == reason
        if n.startswith("about"):
            assert rows[0]["value"] == pytest.approx(.11) and rows[0]["approximate"]


def test_shared_physical_estimate_remains_conflicting_not_independent(tmp_path):
    def change(a):
        a["denominator"]["measurement_identity"] = deepcopy(a["numerator"]["measurement_identity"])
    store, context, native_args, model_args, _, _ = setup_model(tmp_path, change=change)
    with store:
        repo, owner, _, outcome, _ = populate(store, context, native_args, model_args)
        rows = repo.fact_cells(owner, [outcome["result"]["sheet_ref"]], components=COMPONENTS)
        assert all(r["value"] is None and r["unavailable_reason"] == "conflicting_source_observation" for r in rows)
        assert rows[0]["numerator"]["physical_observation_ref"] == rows[0]["denominator"]["physical_observation_ref"]


@pytest.mark.parametrize("missing", ["sheet", "model", "witness"])
def test_global_source_ids_do_not_grant_receipt(tmp_path, missing):
    store, context, native_args, model_args, _, _ = setup_model(tmp_path)
    with store:
        native = LiteratureKineticRepository(store, context.run_id).populate(context, native_args, "native")
        args = {**model_args, "source_ref": native["result"]["sheet_ref"]}
        received = (*context.received_record_refs, *native["record_refs"])
        reference = args["source_ref"] if missing == "sheet" else args["model_source_ref"] if missing == "model" else args["model_witnesses"][0]["source_ref"]
        owner = replace(context, received_record_refs=tuple(r for r in received if r != reference))
        with pytest.raises(ContractError, match="source_not_received"):
            LiteratureKineticModelRepository(store, context.run_id).populate(owner, args, "model")


def test_provider_label_is_not_a_committed_native_operation(tmp_path):
    store, context, native_args, model_args, _, _ = setup_model(tmp_path)
    with store:
        native = LiteratureKineticRepository(store, context.run_id).populate(context, native_args, "native")
        row = store.get(native["result"]["sheet_ref"])
        record = {k:v for k,v in row.items() if k not in ("id", "record_type", "origin")}
        record["retrieved_at"] = "forged"
        forged = store.put("source", record, origin="tool", scope=plain(context.scope))["id"]
        owner = replace(context, received_record_refs=(*context.received_record_refs, forged))
        with pytest.raises(ContractError):
            LiteratureKineticModelRepository(store, context.run_id).populate(owner, {**model_args,"source_ref":forged}, "model")


def test_exact_subset_forwarding_and_query_only_saved_reconstruction(tmp_path, monkeypatch):
    path = tmp_path / "state"
    store, context, native_args, model_args, _, _ = setup_model(path)
    repo, owner, args, outcome, _ = populate(store, context, native_args, model_args)
    reference = outcome["result"]["sheet_ref"]
    rows = repo.fact_cells(owner, [reference], components=COMPONENTS)
    parent = replace(owner, episode_id="parent")
    assert repo.fact_cells(parent, [reference], components=COMPONENTS) == []
    subset = [rows[3]]
    repo.receive_cells(parent, subset, "trusted-admission")
    assert repo.fact_cells(parent, [reference], components=COMPONENTS) == subset
    with pytest.raises(ContractError, match="cell_not_received"):
        repo.validate_fact_values(parent, rows)
    invalid = deepcopy(subset); invalid[0]["value"] = .99
    with pytest.raises(ContractError, match="differs_from_saved"):
        repo.receive_cells(parent, invalid, "forged-admission")
    before = list(store.db.iterdump())
    raw_artifacts = {store.get(ref)["artifact_ref"] for ref in context.received_record_refs}
    store.close()
    def forbidden(*_a, **_k):
        raise AssertionError("Saved reconstruction may not read or calculate science")
    for module, name in [("literature_kinetic_model_storage", "read_kinetic_model"),
            ("literature_kinetic_model_storage", "populate_kinetic_contrast"),
            ("literature_kinetic_storage", "read_kinetic_inputs"), ("literature_kinetic_storage", "populate_kinetic_contrast")]:
        monkeypatch.setattr("gene_annotation_episode." + module + "." + name, forbidden)
    with Store(path) as reopened:
        get = reopened.get_artifact
        def saved_only(ref):
            assert ref not in raw_artifacts
            return get(ref)
        monkeypatch.setattr(reopened, "get_artifact", saved_only)
        reopened.db.execute("PRAGMA query_only=ON")
        restored = LiteratureKineticModelRepository(reopened, context.run_id)
        assert restored.populate(owner, args, "model") == outcome
        assert restored.fact_cells(parent, [reference], components=COMPONENTS) == subset
        assert restored.received_cells(parent) == subset
        assert list(reopened.db.iterdump()) == before


def test_own_outcome_contains_only_requested_model_numbers(tmp_path):
    store, context, native_args, model_args, _, _ = setup_model(tmp_path)
    with store:
        context = replace(context, assignment={**context.assignment, "requested_kinetic_model_components":["source_signed_index"]})
        _, _, _, outcome, _ = populate(store, context, native_args, model_args)
        assert set(outcome["result"]["cells"]) == {"source_signed_index"}
        assert [r["component"] for r in outcome["result"]["rows"]] == ["source_signed_index"]
        serialized = canonical(outcome["result"])
        assert '"covariance"' not in serialized and '"magnitude":null' in serialized


def test_provenance_ancestor_does_not_manufacture_source_receipt(tmp_path):
    store, context, native_args, model_args, _, _ = setup_model(tmp_path)
    with store:
        ancestor = store.put("source", {"provider":"synthetic_provenance_only", "accession":None,"uri":None,
            "artifact_ref":store.artifact("provenance only", "text/plain"),"text_ref":None,"request_ref":None,
            "version":None,"retrieved_at":None},origin="caller")["id"]
        original = store.get(model_args["model_source_ref"])
        value = {k:v for k,v in original.items() if k not in ("id","record_type","origin")}
        value["parent_source_refs"] = [*value["parent_source_refs"],ancestor]
        model_ref = store.put("source",value,origin="caller")["id"]
        model_args["model_source_ref"] = model_ref
        context = replace(context,received_record_refs=(*context.received_record_refs,model_ref))
        repo, _, _, outcome, _ = populate(store,context,native_args,model_args)
        assert ancestor in repo.read(outcome["result"]["sheet_ref"])["input_source_refs"]
        assert ancestor not in context.received_record_refs and ancestor not in outcome["record_refs"]


@pytest.mark.parametrize("target", ["payload", "request", "outcome"])
def test_modified_saved_model_never_becomes_original_numeric_fact(tmp_path,target):
    from gene_annotation_episode.materials import artifact_path
    store, context, native_args, model_args, _, _ = setup_model(tmp_path)
    with store:
        repo, _, _, outcome, _ = populate(store,context,native_args,model_args)
        sheet = store.get(outcome["result"]["sheet_ref"])
        if target in ("payload","request"):
            ref = sheet["artifact_ref" if target == "payload" else "request_ref"]
            raw = store.get_artifact(ref)
            physical = artifact_path(store,ref)
            physical.write_bytes(raw.replace(b'"known"',b'"estimated"',1))
            if physical.read_bytes() == raw:
                physical.write_bytes(raw + b' ')
        else:
            forged = deepcopy(outcome)
            forged["result"]["cells"]["source_signed_index"]["value"] = True
            store.db.execute("UPDATE literature_kinetic_model_operations SET outcome=?",(canonical(forged),))
        with pytest.raises(ContractError):
            repo.read(sheet["id"])
