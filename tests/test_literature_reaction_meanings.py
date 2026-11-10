"""Constructed A110 semantic custody checks; no primary-paper validation."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3

import pytest

from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.domain import ContractError, obj, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_reaction_meanings import (
    DATA_VERSION, RECORD_VERSION, MODEL_FIELDS, RESOURCE_FIELDS, DEMAND_FIELDS,
)
from gene_annotation_episode.literature_reaction_storage import (
    LiteratureReactionRepository, reaction_cells_schema, reaction_population_schema,
    reaction_semantic_cells_schema,
)
from test_literature_reaction_storage import fixture, source, dataset


def semantic_fixture(path, *, unknown=False, mutate=None):
    store, context, args, records = fixture(path, page=True)
    text = ("Constructed only: Balanced reaction model|Alternative bypass model|Alternative side reaction|"
        "Alternative coupled reaction|A + B yields P|A yields Q|Two-electron transfer|"
        "The balanced model predicts a unit product ratio.|The bypass predicts a half ratio.|"
        "The side reaction predicts a half ratio.|The coupled model predicts a different ratio.|"
        "Glucose resource|NADH resource|glucose|NADH|usable amount|reaction vessel|one-minute assay|"
        "defined in-vitro system|The glucose supply is independently specified.|"
        "The NADH supply is independently specified.|One mole of glucose is required per mole of P.|"
        "One mole of NADH is required per mole of P.|Product formation demand|P formation|"
        "Demand is ten micromoles of P in the same vessel and period. µ")
    meanings = source(store, text, parents=[records["root"]["id"]])
    def witness(quote):
        start = text.encode().index(quote.encode())
        return {"source_ref": meanings["id"], "representation": "original", "start": start,
                "end": start + len(quote.encode()), "quote": quote}
    def entry(fields, values, bases):
        return {**{field: None if unknown else witness(value)
            for field, value in zip(fields, values)}, **dict.fromkeys(bases, "unresolved" if unknown else "conditional_assumption")}
    data = dataset()
    data["version"] = DATA_VERSION
    data["ratio"]["alternatives"] = [{"key": "claim", "prediction": .5},
        {"key": "private-second", "prediction": .5}, {"key": "private-near", "prediction": .9}]
    model_values = [
        ("Balanced reaction model", "A + B yields P", "Two-electron transfer", "The balanced model predicts a unit product ratio."),
        ("Alternative bypass model", "A yields Q", "Two-electron transfer", "The bypass predicts a half ratio."),
        ("Alternative side reaction", "A yields Q", "Two-electron transfer", "The side reaction predicts a half ratio."),
        ("Alternative coupled reaction", "A + B yields P", "Two-electron transfer", "The coupled model predicts a different ratio.")]
    data["meanings"] = {"ratio": {
        "claim": entry(MODEL_FIELDS, model_values[0], ("prediction_basis",)),
        "alternatives": [{"key": row["key"], **entry(MODEL_FIELDS, values, ("prediction_basis",))}
            for row, values in zip(data["ratio"]["alternatives"], model_values[1:])]},
        "budget": {"resources": [], "demand": entry(DEMAND_FIELDS,
            ("Product formation demand", "P formation", "defined in-vitro system", "reaction vessel", "one-minute assay",
             "Demand is ten micromoles of P in the same vessel and period."), ("demand_basis",))}}
    resource_values = [
        ("Glucose resource", "glucose", "usable amount", "defined in-vitro system", "reaction vessel", "one-minute assay",
         "The glucose supply is independently specified.", "One mole of glucose is required per mole of P."),
        ("NADH resource", "NADH", "usable amount", "defined in-vitro system", "reaction vessel", "one-minute assay",
         "The NADH supply is independently specified.", "One mole of NADH is required per mole of P.")]
    data["meanings"]["budget"]["resources"] = [{"resource_key": row["resource_key"],
        **entry(RESOURCE_FIELDS, values, ("supply_basis", "coefficient_basis"))}
        for row, values in zip(data["budget"]["resources"], resource_values)]
    if mutate: mutate(data)
    retained = source(store, json.dumps(data), parents=[records["root"]["id"]])
    args["data_source_ref"] = retained["id"]
    context = replace(context, received_record_refs=(*context.received_record_refs, retained["id"], meanings["id"]))
    return store, context, args, {**records, "retained": retained, "meanings": meanings}, data


def populate(store, context, args):
    repo = LiteratureReactionRepository(store, context.run_id)
    outcome = repo.populate(context, args, "selected")
    view = repo.semantic_projection()
    rows = view.project_cells([outcome["result"]["sheet_ref"]],
        permitted_record_refs=outcome["record_refs"], components=["reaction_comparison", "resource_capacity"])
    return repo, outcome, view, rows


def reopen_read_only(store):
    store.close()
    store.db = sqlite3.connect(f"file:{store.path / 'state.sqlite3'}?mode=ro", uri=True)
    store.db.row_factory = sqlite3.Row
    store.db.create_function("library_scope_record", 2, store._scope_filter_record)
    store.db.execute("PRAGMA query_only=ON")


def test_named_models_equal_predictions_and_claim_key_collision_preserve_actual_roles(tmp_path):
    def reverse(data):
        data["meanings"]["ratio"]["alternatives"].reverse()
        data["meanings"]["budget"]["resources"].reverse()
    store, context, args, records, _ = semantic_fixture(tmp_path, mutate=reverse)
    with store:
        repo, outcome, view, rows = populate(store, context, args)
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert saved["version"] == RECORD_VERSION
        assert rows[0]["value"] == pytest.approx(-3 / 7)
        assert rows[1]["value"] == 6
        models = rows[0]["model_definitions"]
        assert [r["role"] for r in models] == ["claim", "alternative", "alternative", "alternative"]
        assert len({r["model_ref"] for r in models}) == 4
        assert [store.get(r["model_ref"])["label"] for r in models] == ["Balanced reaction model",
            "Alternative bypass model", "Alternative side reaction", "Alternative coupled reaction"]
        assert [r["prediction"] for r in models] == [1, .5, .5, .9]
        assert rows[0]["comparison_member_refs"] == [r["model_ref"] for r in models[1:]]
        resources = rows[0]["resource_definitions"]
        assert [store.get(r["entity_ref"])["label"] for r in resources] == ["glucose", "NADH"]
        assert resources[0]["resource_ref"] != resources[1]["resource_ref"]
        demand = rows[0]["demand_definition"]
        assert all(r["coefficient_demand_ref"] == demand["demand_ref"] for r in resources)
        assert [store.get(r["period_ref"])["name"] for r in resources] == ["one-minute assay"] * 2
        assert [store.get(r["compartment_ref"])["name"] for r in resources] == ["reaction vessel"] * 2
        assert demand["value"] == 10 and demand["unit"] == "umol"
        assert rows[0]["nominal_limiting_resource_refs"] == [resources[1]["resource_ref"]]
        assert records["meanings"]["id"] in saved["direct_input_source_refs"]
        validate_closed_schema(obj({"cells": reaction_semantic_cells_schema()}))
        validate_schema(rows, reaction_semantic_cells_schema())
        with pytest.raises(ContractError): validate_schema(rows, reaction_cells_schema())
        with pytest.raises(ContractError, match="projection_version"):
            repo.project_cells([rows[0]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        with pytest.raises(ContractError, match="projection_version"): repo.validate_empty_return_family(context)
        view.validate_empty_return_family(context)
        assert not store.list("observation") and not store.list("assessment")


def test_unknown_and_partial_meanings_do_not_gate_existing_numbers(tmp_path):
    store, context, args, _, _ = semantic_fixture(tmp_path / "unknown", unknown=True)
    with store:
        _, _, _, rows = populate(store, context, args)
        assert rows[0]["value"] == pytest.approx(-3 / 7) and rows[1]["value"] == 6
        models = rows[0]["model_definitions"]
        assert len({r["model_ref"] for r in models}) == 4
        assert all(not r["definition_reported"] and r["prediction_evidence_ref"] is None for r in models)
        assert all(store.get(r["model_ref"])["anchor"] is None for r in models)
        assert all("private-" not in store.get(r["model_ref"])["label"] for r in models)
    def partial(data):
        data["meanings"]["ratio"]["claim"]["definition"] = None
    store, context, args, _, _ = semantic_fixture(tmp_path / "partial", mutate=partial)
    with store:
        _, _, _, rows = populate(store, context, args)
        claim = rows[0]["model_definitions"][0]
        assert not claim["definition_reported"]
        assert store.get(claim["reaction_ref"])["label"] == "A + B yields P"
        assert rows[0]["value"] == pytest.approx(-3 / 7)


@pytest.mark.parametrize("section", ["alternatives", "resources"])
@pytest.mark.parametrize("defect", ["missing", "extra", "duplicate", "unknown"])
def test_semantics_match_the_actual_operand_roster(tmp_path, section, defect):
    def mutate(data):
        container = data["meanings"]["ratio" if section == "alternatives" else "budget"]
        rows = container[section]; key = "key" if section == "alternatives" else "resource_key"
        if defect == "missing": rows.pop()
        elif defect == "extra": rows.append(deepcopy(rows[0]))
        elif defect == "duplicate": rows[1][key] = rows[0][key]
        else: rows[0][key] = "not-an-operand"
    store, context, args, _, _ = semantic_fixture(tmp_path, mutate=mutate)
    with store:
        with pytest.raises(ExperimentalContractError, match="roster_mismatch"):
            LiteratureReactionRepository(store, context.run_id).populate(context, args, "selected")
        assert not [r for r in store.list("source") if r["provider"] == "literature.experimental.reaction"]


def test_source_authorization_before_bytes_in_new_execution_and_saved_replay(tmp_path, monkeypatch):
    store, context, args, records, _ = semantic_fixture(tmp_path)
    with store:
        repo, _, _, _ = populate(store, context, args)
        denied = replace(context, received_record_refs=tuple(r for r in context.received_record_refs if r != records["meanings"]["id"]))
        get = store.get_artifact
        def forbid_meaning_source(ref):
            assert ref != records["meanings"]["artifact_ref"]
            return get(ref)
        monkeypatch.setattr(store, "get_artifact", forbid_meaning_source)
        for key in ("new", "selected"):
            with pytest.raises(ContractError, match="not_received"): repo.populate(denied, args, key)
        # An actually possessed but unrelated page cannot authorize the witness.
        unrelated = source(store, "Unrelated assigned page.")
        outsider = replace(context, assignment={"page": {"source_ref": unrelated["id"]}})
        with pytest.raises(ContractError, match="outside_assigned_source"): repo.populate(outsider, args, "outside")


def test_semantic_readonly_reconstruction_and_exact_subset_receipt(tmp_path, monkeypatch):
    store, context, args, records, _ = semantic_fixture(tmp_path)
    with store:
        repo, outcome, view, rows = populate(store, context, args)
        receiver = replace(context, episode_id="parent", role="annotation", path=(("annotation", "parent"),), received_record_refs=tuple(outcome["record_refs"]))
        subset = rows[:1]
        view.receive_cells(receiver, subset, "delivery")
        assert view.received_cells(receiver) == subset
        reopen_read_only(store)
        get_artifact = store.get_artifact
        original_artifacts = {store.get(ref)["artifact_ref"] for ref in context.received_record_refs}
        def no_source(ref):
            assert ref not in original_artifacts
            return get_artifact(ref)
        def forbidden(*args, **kwargs): raise AssertionError("saved semantic reconstruction reacquired or mutated")
        monkeypatch.setattr(store, "get_artifact", no_source)
        for name in ("artifact", "put", "transaction", "commit_reasoning"): monkeypatch.setattr(store, name, forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_reaction_storage.read_reaction_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_reaction_storage.populate_reaction_constraints", forbidden)
        restored = LiteratureReactionRepository(store, context.run_id).semantic_projection()
        assert restored.received_cells(receiver) == subset
        assert restored.fact_cells(receiver, [rows[0]["sheet_ref"]], components=["resource_capacity"]) == []
        assert store.db.total_changes == 0


def test_portable_old_v2_outcome_schema_payload_and_projection_exact(tmp_path):
    expected = json.loads((Path(__file__).parent / "fixtures/a110_legacy_v2_125.json").read_text())
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureReactionRepository(store, context.run_id)
        out = repo.populate(context, args, "selected"); ref = out["result"]["sheet_ref"]
        assert out == expected["outcome"]
        assert repo.read(ref) == expected["payload"]
        assert repo.project_cells([ref], permitted_record_refs=out["record_refs"]) == expected["rows"]
        # Preserve exact historical payloads and validate their real arguments
        # and rows under both contracts. Current documentation and general REF
        # metadata need not equal the historical schema's serialized text.
        validate_schema(expected["rows"], expected["cells_schema"])
        validate_schema(expected["rows"], reaction_cells_schema())
        validate_schema(args, expected["population_schema"])
        validate_schema(args, reaction_population_schema())
        with pytest.raises(ContractError): repo.semantic_projection().project_cells([ref], permitted_record_refs=out["record_refs"])
        with pytest.raises(ContractError, match="projection_version"): repo.semantic_projection().validate_empty_return_family(context)


def test_exact_requested_subset_cannot_be_forged_or_expanded_by_later_receiver(tmp_path):
    store, context, args, _, _ = semantic_fixture(tmp_path)
    with store:
        _, outcome, view, rows = populate(store, context, args)
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "parent"),),
            received_record_refs=tuple(outcome["record_refs"]))
        view.receive_cells(parent, rows[:1], "delivery")
        with pytest.raises(ContractError, match="cell_not_received"):
            view.validate_fact_values(parent, rows[1:])
        forged = deepcopy(rows[:1])
        forged[0]["model_definitions"][0]["prediction_basis"] = "source_reported"
        with pytest.raises(ContractError, match="differs_from_saved"):
            view.validate_returned_values(forged, permitted_record_refs=outcome["record_refs"])
        forged = deepcopy(rows[:1])
        forged[0]["model_definitions"][1]["model_ref"] = forged[0]["model_definitions"][2]["model_ref"]
        with pytest.raises(ContractError, match="differs_from_saved"):
            view.validate_returned_values(forged, permitted_record_refs=outcome["record_refs"])
        store.db.execute("UPDATE literature_reaction_semantic_received SET cells=?", (json.dumps(forged),))
        with pytest.raises(ContractError, match="delivery_binding_mismatch"): view.received_cells(parent)


def test_saved_scientific_record_tampering_cannot_relabel_the_same_prediction(tmp_path):
    store, context, args, _, _ = semantic_fixture(tmp_path)
    with store:
        _, outcome, view, rows = populate(store, context, args)
        reference = rows[0]["model_definitions"][1]["model_ref"]
        record = store.get(reference)
        record["label"] = "A fabricated reaction name"
        store.db.execute("UPDATE records SET data=? WHERE id=?", (json.dumps(record), reference))
        with pytest.raises(ContractError, match="semantic_binding_mismatch"):
            view.project_cells([rows[0]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])


@pytest.mark.parametrize("missing", ["ratio", "budget", "alternatives"])
def test_partial_sections_and_absent_alternatives_preserve_native_missingness(tmp_path, missing):
    def mutate(data):
        if missing == "alternatives":
            data["ratio"]["alternatives"] = []
            data["meanings"]["ratio"]["alternatives"] = []
        else:
            data[missing] = None
            data["meanings"][missing] = None
    store, context, args, _, _ = semantic_fixture(tmp_path, mutate=mutate)
    with store:
        _, _, _, rows = populate(store, context, args)
        if missing == "ratio":
            assert rows[0]["value"] is None and rows[0]["model_definitions"] == []
            assert rows[0]["unavailable_reason"] == "ratio_unreported" and rows[1]["value"] == 6
        elif missing == "budget":
            assert rows[1]["value"] is None and rows[1]["resource_definitions"] == []
            assert rows[1]["demand_definition"] is None and rows[0]["value"] == pytest.approx(-3 / 7)
        else:
            assert rows[0]["value"] is None and len(rows[0]["model_definitions"]) == 1
            assert rows[0]["comparison_member_refs"] == []
            assert rows[0]["unavailable_reason"] == "alternatives_unreported"
