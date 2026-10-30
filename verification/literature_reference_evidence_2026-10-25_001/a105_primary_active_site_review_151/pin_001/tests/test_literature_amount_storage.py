"""Synthetic selected amount persistence and exact saved-subset return tests."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_amount_inputs import validate_amount_extraction, validate_amount_selection
from gene_annotation_episode.literature_amount_storage import LiteratureAmountRepository, amount_cells_schema
from gene_annotation_episode.state import Store
from test_literature_amount_inputs import fixture, SOURCE, TEXT


def setup(path, *, text=TEXT, arguments=None):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    artifact = store.artifact(text, "text/plain")
    source = store.put("source", {"provider": "synthetic_amount_fixture", "accession": None, "uri": None,
        "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="caller")["id"]
    args = deepcopy(arguments) if arguments is not None else fixture()[0]
    def replace_source(value):
        if isinstance(value, dict):
            return {key: replace_source(child) for key, child in value.items()}
        if isinstance(value, list):
            return [replace_source(child) for child in value]
        return source if value == SOURCE else value
    args = replace_source(args)
    context = BindingContext("amount-run", "amount-child", "literature", (("literature", "case"),),
        store.validate_scope(), {"version": "literature_assignment_v1", "question_context_refs": [],
            "source_refs": [source]}, {}, [source])
    return store, context, args


def test_selected_saved_amounts_have_closed_semantic_projection_and_only_requested_numbers(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureAmountRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        assert outcome["status"] == "completed"
        ref = outcome["result"]["sheet_ref"]
        saved = repo.read(ref)
        validate_amount_extraction(saved["extraction"])
        validate_amount_selection(args, saved["extraction"])
        projected = repo.project_cells([ref], permitted_record_refs=outcome["record_refs"],
            components=["amount_ratio", "conditional_mass_denominator_factor"])
        validate_schema(projected, amount_cells_schema())
        form = obj({"amounts": amount_cells_schema()})
        validate_form({"amounts": projected}, form,
            lambda reference, namespace: store.reference_subset([reference], plain(context.scope)))
        assert [row["value"] for row in projected] == [5 / 7, 1.4]
        assert projected[0]["comparison_kind"] == "stock_target_mass_estimate_over_total_mass_estimate"
        assert projected[0]["numerator"]["amount_role"] == "target_mass_estimate"
        assert projected[0]["denominator"]["amount_role"] == "total_protein_mass_estimate"
        assert projected[0]["numerator"]["subject_ref"] is None
        assert "value" not in projected[0]["numerator"]
        assert len(projected[0]["input_measurement_refs"]) == 2
        assert projected[0]["variance_status"] == "unknown"
        assert all(row["mass_factor_applied_to_rate"] is False for row in projected)
        assert len(saved["sheet"]["cells"]) == 12
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()


@pytest.mark.parametrize("mutation", [
    lambda x: x.update(value=100), lambda x: x.update(unit="uM"),
    lambda x: x.update(unavailable_reason="amount_basis_unknown"),
    lambda x: x["numerator"].update(amount_role="nominal_molecule_amount"),
    lambda x: x["denominator"].update(qualification="unknown"),
    lambda x: x["numerator"].update(measurement_ref=None),
])
def test_typed_subset_rejects_changed_value_or_scientific_meaning(tmp_path, mutation):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureAmountRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        refs = outcome["record_refs"]
        rows = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=refs, components=["amount_ratio"])
        mutation(rows[0])
        with pytest.raises(ContractError, match="differs_from_saved_cells"):
            repo.validate_returned_values(rows, permitted_record_refs=refs)
    finally:
        store.close()


def test_saved_only_reconstruction_replay_and_exact_received_subset(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path)
    repo = LiteratureAmountRepository(store, context.run_id)
    outcome = repo.populate(context, args, "selected")
    ref = outcome["result"]["sheet_ref"]
    rows = repo.project_cells([ref], permitted_record_refs=outcome["record_refs"], components=["amount_ratio"])
    parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "parent"),), assignment={})
    repo.receive_cells(parent, rows, "delivery")
    repo.receive_cells(parent, rows, "delivery")
    source_artifact = store.get(args["source_ref"])["artifact_ref"]
    store.close()
    def forbidden(*args, **kwargs):
        raise AssertionError("saved replay must not parse source or recalculate cells")
    monkeypatch.setattr("gene_annotation_episode.literature_amount_storage.read_amount_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_amount_storage.populate_amount_components", forbidden)
    with Store(tmp_path) as reopened:
        original_get = reopened.get_artifact
        def guarded(reference):
            assert reference != source_artifact, "scientific source bytes must not be reopened"
            return original_get(reference)
        monkeypatch.setattr(reopened, "get_artifact", guarded)
        repo = LiteratureAmountRepository(reopened, context.run_id)
        assert repo.read(ref)["sheet"]["cells"]["amount_ratio"]["value"] == 5 / 7
        assert repo.populate(context, args, "selected") == outcome
        assert repo.received_cells(parent) == rows
        assert len(repo.received_cells(parent)) == 1
        with pytest.raises(ContractError, match="not_received"):
            repo.populate(replace(context, received_record_refs=[]), args, "selected")
        changed = deepcopy(args)
        changed["pair_relationship"] = {"value": "unknown", "witnesses": []}
        with pytest.raises(ContractError, match="operation_key_reused"):
            repo.populate(context, changed, "selected")


def test_missing_receipt_and_assigned_source_ancestry_are_not_global_access(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureAmountRepository(store, context.run_id)
        with pytest.raises(ContractError, match="not_received"):
            repo.populate(replace(context, received_record_refs=[]), args, "selected")
        unrelated_artifact = store.artifact("Other paper", "text/plain")
        other = store.put("source", {"provider": "synthetic_other", "accession": None, "uri": None,
            "artifact_ref": unrelated_artifact, "text_ref": unrelated_artifact, "request_ref": None,
            "version": None, "retrieved_at": None}, origin="caller")["id"]
        page = replace(context, role="literature_page", path=(("literature_page", "page"),), assignment={"source_ref": other})
        with pytest.raises(ContractError, match="outside_assigned_source"):
            repo.populate(page, args, "outside")
        assert store.db.execute("SELECT count(*) FROM literature_amount_operations").fetchone()[0] == 0
    finally:
        store.close()


def test_copied_provider_label_cannot_manufacture_a_selected_amount_sheet(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureAmountRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        row = store.get(outcome["result"]["sheet_ref"])
        request = json.loads(store.get_artifact(row["request_ref"]))
        request["operation_key"] = "never-selected"
        fields = {field: row[field] for field in ("provider", "accession", "uri", "artifact_ref", "text_ref", "version", "retrieved_at", "parent_source_refs")}
        fields["request_ref"] = store.artifact(canonical(request), "application/json")
        fake = store.put("source", fields, origin="tool", scope=plain(context.scope))
        with pytest.raises(ContractError, match="not_selected_output"):
            repo.read(fake["id"])
    finally:
        store.close()


@pytest.mark.parametrize("field,value", [("value", 20), ("measurement_key", "wrong"), ("owner_key", "wrong")])
def test_saved_extraction_checks_source_token_scientific_owner_and_derived_associations(tmp_path, field, value):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureAmountRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        extraction = repo.read(outcome["result"]["sheet_ref"])["extraction"]
        extraction["quantities"]["numerator"][field] = value
        with pytest.raises(ValueError, match="amount_saved_quantity_mismatch"):
            validate_amount_extraction(extraction)
    finally:
        store.close()
