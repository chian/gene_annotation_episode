"""Structural interpretation revisions preserve native model and quality limits."""
import asyncio
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.literature_structure_storage import LiteratureStructureRepository, structure_cells_schema
from test_literature_structure_integration import setup_case
from test_literature_perturbation_integration import binding_for
from test_literature_perturbation_assessments import identify


@pytest.mark.parametrize("validation", [False, True])
def test_structural_reassessment_keeps_one_dataset_and_native_saved_only_results(tmp_path, monkeypatch, validation):
    store, context, args = setup_case(tmp_path, validation=validation)
    try:
        context, args = identify(store, context, args, "4HF1-experimental-dataset")
        args["experiment_assessment"].update(experiment_type="structural_feature_geometry",
            scientific_question="Which selected model features support the proposed contacts?",
            conclusion="Geometry is conditional on the selected model and assignments.",
            limitations=["Coordinate uncertainty and population occupancy remain unreported."])
        binding = binding_for(store, context)
        repo = LiteratureStructureRepository(store, context.run_id)
        first = asyncio.run(binding.execute(context, "literature.structure.populate", args, "first"))
        assert first["status"] == "completed", first.get("feedback")
        first_ref = first["result"]["sheet_ref"]
        context = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *first["record_refs"]))))
        revised_args = deepcopy(args)
        # Same physical dataset and exact source values; a changed proposed
        # predicate is a revised interpretation, not another experiment.
        for member in revised_args["geometry_panel"]:
            member["positive_max_A"] = 3.6
        revised_args["experiment_assessment"].update(revises_sheet_ref=first_ref,
            revision_reason="Evaluate sensitivity to the proposed distance predicate.")
        second = repo.populate(context, revised_args, "revision")
        second_ref = second["result"]["sheet_ref"]
        assert first["result"]["cells"]["geometry_support_fraction"]["value"] == .75
        assert second["result"]["cells"]["geometry_support_fraction"]["value"] == 1
        assert second["result"]["cells"]["local_fit_index"]["value"] == (pytest.approx(.815409) if validation else None)
        assert len(repo.current_assessments()) == 1
        history = repo.assessment_history(second_ref)
        assert len(history) == 2
        context = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *second["record_refs"]))))
        with pytest.raises(ContractError, match="revision_required"):
            repo.populate(context, revised_args, "duplicate")
        schema = obj({"measurements": structure_cells_schema()})
        form = form_with_facts({}, schema, binding.facts(context, {"committed_record_refs": [second_ref]}))
        binding.validate_report(context, form, schema)
        rows = form["measurements"]
        assert rows and all(r["experiment_ref"] == args["experiment_assessment"]["experiment_ref"] for r in rows)
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "root"),), assignment={})
        binding.received_form_references(parent, form, schema, "delivery")
        saved = repo.read(second_ref)
        assert saved["extraction"]["native_local"] == repo.read(first_ref)["extraction"]["native_local"]
        allowed = {store.get(ref)[field] for ref in (first_ref, second_ref) for field in ("artifact_ref", "request_ref")}
        read = store.get_artifact
        def saved_only(ref):
            assert ref in allowed
            return read(ref)
        def forbidden(*args, **kwargs):
            raise AssertionError("no original-coordinate read or recalculation during reconstruction")
        monkeypatch.setattr(store, "get_artifact", saved_only)
        monkeypatch.setattr("gene_annotation_episode.literature_structure_storage.read_structure_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_structure_storage.populate_source_geometry", forbidden)
        store.db.execute("pragma query_only=ON")
        before = store.db.total_changes
        assert repo.assessment_history(second_ref) == history
        assert repo.current_assessments()[0]["sheet_ref"] == second_ref
        assert repo.populate(context, revised_args, "revision") == second
        assert repo.received_cells(parent) == rows
        assert repo.read(second_ref) == saved
        assert store.db.total_changes == before
    finally:
        store.close()
