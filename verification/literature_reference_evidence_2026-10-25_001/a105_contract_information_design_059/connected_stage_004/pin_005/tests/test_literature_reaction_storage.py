"""Synthetic source/selection/replay checks; no papers or model calls."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.domain import ContractError, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_reaction_storage import (
    BINDINGS, COMPONENTS, PROVIDER, LiteratureReactionRepository,
    reaction_cells_schema, reaction_population_schema,
)
from gene_annotation_episode.state import Store


def source(store, text, *, parents=(), alias=False):
    artifact = store.artifact(text)
    return store.put("source", {"provider": "synthetic_reaction_fixture", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact if alias else None,
        "request_ref": None, "version": None, "retrieved_at": None,
        "parent_source_refs": list(parents)}, origin="caller")


def dataset(*, summary=False, budget=True):
    ratio = {"mode": "source_summary" if summary else "independent_units",
        "ratio_kind": "product_pair", "unit": "mol_per_mol", "origin": "synthetic",
        "observations": [] if summary else [{"measurement_key": "prep1", "value": .7},
            {"measurement_key": "prep2", "value": .9}],
        "mean": 1 if summary else None, "sample_sd": None, "independent_n": None,
        "claim": 1, "alternatives": [] if summary else [{"key": "half", "prediction": .5}]}
    return {"version": "a110_source_reaction_measurements_v1", "ratio": ratio,
        "budget": {"basis": "usable_batch", "unit": "umol", "origin": "synthetic",
            "resources_complete": True, "resources": [
                {"resource_key": "resource1", "value": 12, "lower": 12, "upper": 12, "coefficient": 1},
                {"resource_key": "resource2", "value": 6, "lower": 6, "upper": 6, "coefficient": 1}],
            "demand": 10} if budget else None}


def fixture(path, *, page=False, summary=False, data=True):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    provenance = source(store, "Synthetic retained source provenance.")
    root = source(store, "Synthetic reaction experiment.", parents=[provenance["id"]])
    data_row = source(store, json.dumps(dataset(summary=summary, budget=not summary)), parents=[root["id"]])
    text = "Molecule|Construct|Experiment|Product numerator|Product denominator|Endpoint|Condition|Resource context"
    literal = source(store, text, parents=[root["id"]], alias=True)
    interpretation = source(store, "Synthetic physical meaning of the numerical panel.", parents=[root["id"]])
    literals, offset = {}, 0
    for field, quote in zip((literal for literal, _ in BINDINGS.values()), text.split("|")):
        literals[field] = {"source_ref": literal["id"], "representation": "original",
            "start": offset, "end": offset + len(quote), "quote": quote}
        offset += len(quote) + 1
    quote = store.get_artifact(interpretation["artifact_ref"]).decode()
    args = {"source_ref": root["id"], "data_source_ref": data_row["id"] if data else None,
        "source_kind": "synthetic_fixture", "literals": literals,
        "interpretation_witnesses": [{"source_ref": interpretation["id"], "representation": "original",
            "start": 0, "end": len(quote), "quote": quote}]}
    received = [root["id"], literal["id"], interpretation["id"]]
    if data:
        received.append(data_row["id"])
    context = BindingContext("synthetic-reaction-run", "reaction-child", "literature",
        (("literature", "fixture"),), store.validate_scope(),
        {"page": {"source_ref": root["id"]}} if page else {}, {}, tuple(received))
    records = {"root": root, "data": data_row, "literal": literal,
        "interpretation": interpretation, "provenance": provenance}
    return store, context, args, records


def test_selected_reader_calculator_and_closed_scientific_return(tmp_path):
    store, context, args, records = fixture(tmp_path, page=True)
    with store:
        repo = LiteratureReactionRepository(store, context.run_id)
        validate_schema(args, reaction_population_schema())
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        saved = repo.read(ref)
        assert store.get(ref)["provider"] == PROVIDER
        assert saved["version"] == "literature_reaction_record_v2"
        assert set(saved["direct_input_source_refs"]) == set(context.received_record_refs)
        assert records["provenance"]["id"] in saved["input_source_refs"]
        assert records["provenance"]["id"] not in saved["direct_input_source_refs"]
        assert saved["sheet"]["inputs"] == saved["extraction"]["calculation_inputs"]
        assert saved["sheet"]["cells"]["reaction_comparison"]["value"] == pytest.approx(1 / 3)
        assert saved["sheet"]["cells"]["resource_capacity"]["value"] == 6
        assert saved["sheet"]["cells"]["resource_comparison"]["value"] == pytest.approx(.2)
        rows = repo.project_cells([ref, ref], permitted_record_refs=outcome["record_refs"],
            components=("reaction_comparison", "resource_comparison"))
        assert [row["component"] for row in rows] == ["reaction_comparison", "resource_comparison"]
        for row in rows:
            assert row["ratio_kind"] == "product_pair" and row["ratio_mode"] == "independent_units"
            assert row["ratio_unit"] == "mol_per_mol" and row["claim_prediction"] == 1
            assert row["alternative_predictions"] == [.5]
            assert row["budget_basis"] == "usable_batch" and row["budget_unit"] == "umol"
            assert row["resources_complete"] is True and row["demand"] == 10
            assert row["bound_kind"] == "logical_model_domain_not_confidence_interval"
            assert row["measurement_corrections"] == "not_applied"
            assert row["target_correspondence"] == "not_evaluated"
            assert row["ratio_origin"] == row["budget_origin"] == "synthetic"
            assert row["independent_n"] == 2
            assert row["reported_sample_sd"] is None
            assert row["derived_sample_sd"] == pytest.approx(.02 ** .5)
            assert row["ratio_uncertainty"] == "descriptive_sample_sd"
            assert row["uncertainty_interpretation"] == "descriptive_not_confidence_interval"
            assert "formula" not in row and "inputs" not in row and "witness" not in row
        assert set(outcome["changed_record_refs"]) == {ref, *saved["experimental_bindings"].values()}
        for field, (literal, _) in BINDINGS.items():
            binding = store.get(saved["experimental_bindings"][field])
            selected = saved["extraction"]["literals"][literal]
            assert binding.get("label", binding.get("name")) == selected["value"]
            assert binding["anchor"]["artifact_ref"] == selected["witness"]["artifact_ref"]
            assert binding["anchor"]["quote"] == selected["value"]
        validate_closed_schema(obj({"cells": reaction_cells_schema()}))
        validate_schema(rows, reaction_cells_schema())
        assert not store.list("observation") and not store.list("assessment")


@pytest.mark.parametrize("data", [True, False])
def test_missing_replication_or_dataset_stays_unknown(tmp_path, data):
    store, context, args, _ = fixture(tmp_path, summary=True, data=data)
    with store:
        repo = LiteratureReactionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "summary")
        cells = outcome["result"]["cells"]
        assert cells["ratio_mean"]["value"] == (1 if data else None)
        assert cells["claim_nominal_squared_error"]["value"] == (0 if data else None)
        assert cells["claim_mean_squared_error"]["value"] is None
        assert cells["reaction_comparison"]["value"] is None
        assert cells["resource_capacity"]["value"] is None
        rows = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        assert all(row["budget_basis"] is None and row["demand"] is None for row in rows)
        assert all(row["independent_n"] is None and row["reported_sample_sd"] is None
            and row["derived_sample_sd"] is None and row["ratio_uncertainty"] == "unreported"
            and row["budget_origin"] is None for row in rows)
        if not data:
            assert all(row["ratio_mode"] is None for row in rows)


@pytest.mark.parametrize("n", [None, 3])
def test_reported_sd_and_exact_or_missing_n_cross_boundary_as_saved(tmp_path, n):
    store, context, args, records = fixture(tmp_path, summary=True)
    with store:
        data = dataset(summary=True, budget=True)
        data["ratio"].update(sample_sd=.2, independent_n=n, origin="reported")
        data["budget"]["origin"] = "graph_derived"
        row = source(store, json.dumps(data), parents=[records["root"]["id"]])
        args["data_source_ref"] = row["id"]
        context = replace(context, received_record_refs=(*context.received_record_refs, row["id"]))
        repo = LiteratureReactionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "summary_sd")
        saved = repo.read(outcome["result"]["sheet_ref"])
        rows = repo.project_cells([outcome["result"]["sheet_ref"]],
            permitted_record_refs=outcome["record_refs"], components=("claim_mean_squared_error",))
        for value in [outcome["result"], *rows]:
            assert value["independent_n"] == saved["sheet"]["ratio_details"]["independent_n"] == n
            assert value["reported_sample_sd"] == .2
            assert value["derived_sample_sd"] is None
            assert value["ratio_uncertainty"] == "reported_sample_sd"
            assert value["uncertainty_interpretation"] == "descriptive_not_confidence_interval"
            assert value["ratio_origin"] == "reported" and value["budget_origin"] == "graph_derived"
        assert rows[0]["value"] == (pytest.approx(2 * .2 ** 2 / 3) if n == 3 else None)


@pytest.mark.parametrize("part", ["root", "data", "literal", "interpretation"])
def test_each_direct_source_requires_receipt_initial_and_replay(tmp_path, part):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteratureReactionRepository(store, context.run_id)
        repo.populate(context, args, "selected")
        denied = replace(context, received_record_refs=tuple(ref for ref in context.received_record_refs
            if ref != records[part]["id"]))
        before = store.list("source")
        for key in ("new", "selected"):
            with pytest.raises(ContractError, match="not_received"):
                repo.populate(denied, args, key)
        assert store.list("source") == before
        assert store.db.execute("select count(*) from literature_reaction_operations").fetchone()[0] == 1


@pytest.mark.parametrize("part", ["root", "data", "literal", "interpretation", "provenance"])
def test_scope_covers_direct_inputs_and_provenance(tmp_path, monkeypatch, part):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteratureReactionRepository(store, context.run_id)
        repo.populate(context, args, "selected")
        subset = store.reference_subset
        monkeypatch.setattr(store, "reference_subset", lambda refs, scope:
            [] if records[part]["id"] in refs else subset(refs, scope))
        for key in ("new", "selected"):
            with pytest.raises(ContractError, match="outside_scope"):
                repo.populate(context, args, key)


def test_transitive_provenance_is_retained_and_scoped_on_replay(tmp_path, monkeypatch):
    store, context, args, records = fixture(tmp_path)
    with store:
        intermediate = source(store, "Synthetic intermediate provenance.", parents=[records["root"]["id"]])
        data = source(store, json.dumps(dataset()), parents=[intermediate["id"]])
        args["data_source_ref"] = data["id"]
        # Neither the intermediate nor its ancestor provenance needs a receipt
        # for byte reading: both are provenance-only records.
        context = replace(context, received_record_refs=(*context.received_record_refs, data["id"]))
        repo = LiteratureReactionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert intermediate["id"] in saved["input_source_refs"]
        assert records["provenance"]["id"] in saved["input_source_refs"]
        assert intermediate["id"] not in saved["direct_input_source_refs"]
        subset = store.reference_subset
        monkeypatch.setattr(store, "reference_subset", lambda refs, scope:
            [] if intermediate["id"] in refs else subset(refs, scope))
        for key in ("new", "selected"):
            with pytest.raises(ContractError, match="outside_scope"):
                repo.populate(context, args, key)


@pytest.mark.parametrize("part", ["root", "data", "literal", "interpretation"])
def test_each_direct_input_requires_assigned_page_lineage(tmp_path, part):
    store, context, args, records = fixture(tmp_path, page=True)
    with store:
        row = source(store, store.get_artifact(records[part]["artifact_ref"]))
        if part == "literal":
            for witness in args["literals"].values():
                witness["source_ref"] = row["id"]
        elif part == "interpretation":
            args["interpretation_witnesses"][0]["source_ref"] = row["id"]
        else:
            args["source_ref" if part == "root" else "data_source_ref"] = row["id"]
        context = replace(context, received_record_refs=(*context.received_record_refs, row["id"]))
        with pytest.raises(ContractError, match="outside_assigned_source"):
            LiteratureReactionRepository(store, context.run_id).populate(context, args, "bad")


def test_saved_only_reopen_disables_reader_calculator_and_original_bytes(tmp_path, monkeypatch):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteratureReactionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        saved = repo.read(ref)
        rows = repo.project_cells([ref], permitted_record_refs=outcome["record_refs"])
        forbidden_artifacts = {record["artifact_ref"] for record in records.values()}
    def forbidden(*_args, **_kwargs):
        raise AssertionError("saved replay attempted scientific source work")
    monkeypatch.setattr("gene_annotation_episode.literature_reaction_storage.read_reaction_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_reaction_storage.populate_reaction_constraints", forbidden)
    with Store(tmp_path) as reopened:
        repo = LiteratureReactionRepository(reopened, context.run_id)
        read = reopened.get_artifact
        def saved_only(ref):
            assert ref not in forbidden_artifacts
            return read(ref)
        monkeypatch.setattr(reopened, "get_artifact", saved_only)
        reopened.db.execute("pragma query_only=ON")
        # Import canonically stored args to test ordering independent of input dict insertion.
        reordered = json.loads(json.dumps(args, sort_keys=True))
        assert repo.populate(context, reordered, "selected") == outcome
        assert repo.read(ref) == saved
        assert repo.project_cells([ref], permitted_record_refs=outcome["record_refs"]) == rows


def test_publication_rolls_back_bindings_and_operation(tmp_path, monkeypatch):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureReactionRepository(store, context.run_id)
        kinds = ("source", "reference", "term", "context")
        before = [store.list(kind) for kind in kinds]
        put = store.put
        def fail(kind, record, **kwargs):
            if kind == "source" and record["provider"] == PROVIDER:
                raise RuntimeError("synthetic publication interruption")
            return put(kind, record, **kwargs)
        monkeypatch.setattr(store, "put", fail)
        with pytest.raises(RuntimeError, match="publication interruption"):
            repo.populate(context, args, "atomic")
        assert [store.list(kind) for kind in kinds] == before
        assert store.db.execute("select count(*) from literature_reaction_operations").fetchone()[0] == 0
        monkeypatch.setattr(store, "put", put)
        assert repo.populate(context, args, "atomic")["status"] == "completed"


def test_invalid_dataset_cannot_publish_any_bindings(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        invalid = dataset()
        invalid["ratio"]["observations"].append(deepcopy(invalid["ratio"]["observations"][0]))
        row = source(store, json.dumps(invalid), parents=[records["root"]["id"]])
        args["data_source_ref"] = row["id"]
        context = replace(context, received_record_refs=(*context.received_record_refs, row["id"]))
        repo = LiteratureReactionRepository(store, context.run_id)
        kinds = ("source", "reference", "term", "context")
        before = [store.list(kind) for kind in kinds]
        with pytest.raises(ValueError):
            repo.populate(context, args, "invalid")
        assert [store.list(kind) for kind in kinds] == before


def test_selected_authority_run_and_immutable_operation_identity(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureReactionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        actual = store.get(ref)
        record = {key: value for key, value in actual.items() if key not in ("id", "record_type", "origin")}
        caller_copy = store.put("source", record, origin="caller")
        with pytest.raises(ContractError, match="sheet_required"):
            repo.read(caller_copy["id"])
        record["retrieved_at"] = "2026-01-01T00:00:00Z"
        tool_copy = store.put("source", record, origin="tool")
        with pytest.raises(ContractError, match="not_selected_output"):
            repo.read(tool_copy["id"])
        with pytest.raises(ContractError, match="sheet_run_mismatch"):
            LiteratureReactionRepository(store, "different-run").read(ref)
        with pytest.raises(ContractError, match="reused_for_different_work"):
            repo.populate(context, {**args, "source_kind": "retained_extraction"}, "selected")
        with pytest.raises(ContractError, match="run_mismatch"):
            repo.populate(replace(context, run_id="different-run"), args, "new")
        with pytest.raises(ContractError, match="operation_key_required"):
            repo.populate(context, args, "")
        second = repo.populate(context, args, "second")
        assert second["changed_record_refs"] == [second["result"]["sheet_ref"]]
        outcome["result"]["cells"]["ratio_mean"]["value"] = 999
        assert repo.populate(context, args, "selected")["result"]["cells"]["ratio_mean"]["value"] == pytest.approx(.8)


@pytest.mark.parametrize("field,value", [
    ("value", .2), ("formula_code", "reaction_ratio_mean_v1"),
    ("assayed_subject_ref", None), ("data_source_ref", None),
    ("operand_source_kind", "primary_source"), ("ratio_mode", "source_summary"),
    ("ratio_kind", "signal_ratio"), ("ratio_unit", "signal_per_signal"),
    ("claim_prediction", 2), ("alternative_predictions", [.25]),
    ("budget_basis", "supplied_reagent_batch"), ("budget_unit", "uM"),
    ("resources_complete", False), ("demand", 20), ("conditional_on", []),
    ("independent_n", 3), ("reported_sample_sd", .2), ("derived_sample_sd", .3),
    ("ratio_uncertainty", "unreported"), ("ratio_origin", "reported"),
    ("budget_origin", "graph_derived"),
])
def test_forged_numeric_or_meaning_fields_rejected(tmp_path, field, value):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureReactionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = repo.project_cells([outcome["result"]["sheet_ref"]],
            permitted_record_refs=outcome["record_refs"], components=("reaction_comparison",))
        rows[0][field] = value
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_returned_values(rows, permitted_record_refs=outcome["record_refs"])


def test_exact_admitted_subset_idempotent_and_forwarded_without_private_cells(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureReactionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        rows = repo.project_cells([ref], permitted_record_refs=outcome["record_refs"], components=("ratio_mean",))
        parent = replace(context, episode_id="parent", received_record_refs=tuple(outcome["record_refs"]))
        repo.receive_cells(parent, rows, "delivery")
        repo.receive_cells(parent, rows, "delivery")
        assert repo.received_cells(parent) == rows and len(COMPONENTS) == 15
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_cells(rows, sheet_refs=[ref], permitted_record_refs=outcome["record_refs"])
        with pytest.raises(ContractError, match="duplicate_literature"):
            repo.validate_returned_values(rows * 2, permitted_record_refs=outcome["record_refs"])
        with pytest.raises(ContractError, match="delivery_identity_conflict"):
            repo.receive_cells(parent, [], "delivery")
        with pytest.raises(ContractError, match="not_received"):
            repo.project_cells([ref], permitted_record_refs=())
        for components in (("unknown",), ({},), (COMPONENTS[0], COMPONENTS[0])):
            with pytest.raises(ContractError, match="component_selection_invalid"):
                repo.project_cells([ref], permitted_record_refs=outcome["record_refs"], components=components)
        assert not store.list("observation") and not store.list("assessment")


def test_closed_schema_rejects_free_text_and_nonfinite_fields(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureReactionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        for field, value in (("formula_code", "my formula"), ("unavailable_reason", "arbitrary prose"),
                ("conditional_on", ["arbitrary assumption"]), ("value", float("nan")),
                ("claim_prediction", float("inf")), ("ratio_mode", "invented mode"),
                ("independent_n", True), ("reported_sample_sd", -1),
                ("derived_sample_sd", float("nan")), ("ratio_origin", "derived"),
                ("uncertainty_interpretation", "95% confidence interval"),
                ("resources_complete", "probably"), ("formula", "raw formula")):
            changed = deepcopy(rows)
            changed[0][field] = value
            with pytest.raises(ContractError, match="representation_error"):
                repo.validate_returned_values(changed, permitted_record_refs=outcome["record_refs"])
        changed_args = deepcopy(args)
        changed_args["numerical_operands"] = {"value": .7}
        with pytest.raises(ContractError, match="representation_error"):
            repo.populate(context, changed_args, "invalid_arguments")


def test_missing_literal_bindings_and_exact_span_identity(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        args["literals"]["resource_context"] = None
        args["literals"]["construct"] = deepcopy(args["literals"]["molecule"])
        repo = LiteratureReactionRepository(store, context.run_id)
        first = repo.populate(context, args, "first")
        saved = repo.read(first["result"]["sheet_ref"])
        assert saved["experimental_bindings"]["resource_context_ref"] is None
        assert saved["experimental_bindings"]["construct_ref"] != saved["experimental_bindings"]["assayed_subject_ref"]
        row = source(store, "Molecule|Molecule", parents=[records["root"]["id"]])
        context = replace(context, received_record_refs=(*context.received_record_refs, row["id"]))
        args["literals"]["molecule"].update(source_ref=row["id"], start=0, end=8)
        second = repo.populate(context, args, "second")
        args["literals"]["molecule"].update(start=9, end=17)
        third = repo.populate(context, args, "third")
        assert repo.read(second["result"]["sheet_ref"])["experimental_bindings"]["assayed_subject_ref"] != repo.read(third["result"]["sheet_ref"])["experimental_bindings"]["assayed_subject_ref"]
