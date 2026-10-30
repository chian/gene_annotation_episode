"""Selected source custody, exact requested subsets and source-free replay."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.domain import ContractError, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_active_site_storage import LiteratureActiveSiteRepository, active_site_cells_schema
from gene_annotation_episode.state import Store
from test_literature_active_site_inputs import fixture, SOURCE, TEXT


def setup(path, *, text=TEXT, arguments=None):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    artifact = store.artifact(text, "text/plain")
    source = store.put("source", {"provider": "active_site_test_input", "accession": None, "uri": None,
        "artifact_ref": artifact, "text_ref": artifact, "request_ref": None, "version": None, "retrieved_at": None}, origin="caller")["id"]
    args = deepcopy(arguments) if arguments else fixture(text)[0]
    def replace_source(value):
        if isinstance(value, dict):
            return {key: replace_source(child) for key, child in value.items()}
        if isinstance(value, list):
            return [replace_source(child) for child in value]
        return source if value == SOURCE else value
    args = replace_source(args)
    context = BindingContext("active-run", "active-child", "literature", (("literature", "case"),),
        store.validate_scope(), {"version": "literature_assignment_v1", "question_context_refs": [], "source_refs": [source]}, {}, [source])
    return store, context, args


def test_saved_sheet_exact_semantics_subset_and_closed_form(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureActiveSiteRepository(store, context.run_id)
        assert not repo._installed(repo.operations_table)
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        rows = repo.project_cells([ref], permitted_record_refs=outcome["record_refs"], components=["sites_per_total_monomer"])
        validate_schema(rows, active_site_cells_schema())
        validate_form({"times": rows}, obj({"times": active_site_cells_schema()}),
            lambda reference, namespace: store.reference_subset([reference], plain(context.scope)))
        assert rows[0]["value"] == .6
        assert all(operand["reading"] is None for operand in rows[0]["operands"])
        assert rows[0]["intended_change"]["witness"]["quote"] == "construct tagged"
        assert rows[0]["other_changes"][0]["witness"]["quote"] == "Purification also changed"
        altered = deepcopy(rows)
        altered[0]["interpretations"]["amount_linkage"]["value"] = "different"
        with pytest.raises(ContractError, match="differs_from_saved_cells"):
            repo.validate_returned_values(altered, permitted_record_refs=outcome["record_refs"])
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()


def test_reopen_and_replay_use_saved_operands_without_scientific_source_io(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path)
    repo = LiteratureActiveSiteRepository(store, context.run_id)
    outcome = repo.populate(context, args, "selected")
    ref = outcome["result"]["sheet_ref"]
    rows = repo.project_cells([ref], permitted_record_refs=outcome["record_refs"], components=["sites_per_total_monomer"])
    parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "parent"),), assignment={},
        received_record_refs=(ref,))
    repo.receive_cells(parent, rows, "manual_trusted_admission")
    original_artifact = store.get(args["source_ref"])["artifact_ref"]
    store.close()
    def forbidden(*args, **kwargs):
        raise AssertionError("saved replay cannot reread or reinterpret scientific source")
    monkeypatch.setattr("gene_annotation_episode.literature_active_site_storage.read_active_site_inputs", forbidden)
    with Store(tmp_path) as reopened:
        original_get = reopened.get_artifact
        def guarded(reference):
            assert reference != original_artifact
            return original_get(reference)
        monkeypatch.setattr(reopened, "get_artifact", guarded)
        reopened.db.execute("PRAGMA query_only=ON")
        repo = LiteratureActiveSiteRepository(reopened, context.run_id)
        assert repo.populate(context, args, "selected") == outcome
        assert repo.read(ref)["sheet"]["cells"]["sites_per_total_monomer"]["value"] == .6
        assert repo.received_cells(parent) == rows
        assert repo.fact_cells(parent, [ref], components=list(repo.components)) == rows
        bad = deepcopy(rows); bad[0]["reported_domain"]["lower_inclusive"] = False
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_fact_values(parent, bad)
        with pytest.raises(ContractError, match="not_received"):
            repo.populate(replace(context, received_record_refs=()), args, "selected")
        changed = deepcopy(args); changed["interpretations"]["amount_linkage"] = {"value": "unknown", "witnesses": []}
        with pytest.raises(ContractError, match="operation_key_reused"):
            repo.populate(context, changed, "selected")


def test_source_scope_and_unselected_copies_cannot_acquire_sheet_ownership(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureActiveSiteRepository(store, context.run_id)
        with pytest.raises(ContractError, match="not_received"):
            repo.populate(replace(context, received_record_refs=()), args, "none")
        assert not repo._installed(repo.operations_table)
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        other = replace(context, episode_id="unrelated", received_record_refs=(ref,))
        assert repo.fact_cells(other, [ref], components=list(repo.components)) == []
        with pytest.raises(ContractError, match="cell_not_received"):
            repo.validate_fact_values(other, outcome["result"]["cells"])
    finally:
        store.close()
