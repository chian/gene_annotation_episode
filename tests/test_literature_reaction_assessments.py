"""A110 ratios/resources retain their numerical meanings across revisions."""
import asyncio
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.literature_reaction_storage import LiteratureReactionRepository, reaction_cells_schema, reaction_semantic_cells_schema
from test_literature_reaction_integration import setup_case, binding_for
from test_literature_reaction_native_integration_129 import setup_case as native_case
from test_literature_perturbation_assessments import identify


@pytest.mark.parametrize("case", ["reaction", "resource", "incomplete", "primary", "native"])
def test_reaction_assessment_revision_keeps_numbers_and_exact_saved_parent_results(tmp_path, monkeypatch, case):
    store, context, args = native_case(tmp_path) if case == "native" else setup_case(
        tmp_path, primary=case == "primary", incomplete=case == "incomplete")
    try:
        context, args = identify(store, context, args)
        args["experiment_assessment"].update(
            experiment_type="resource_requirement" if case in ("resource", "incomplete") else "reaction_prediction",
            scientific_question="What does the measured chemistry establish about this reaction or resource constraint?",
            conclusion="The reported quantities constrain the declared chemical model.",
            limitations=["Measured ratios do not establish unmeasured pathway flux."])
        binding = binding_for(store, context)
        repo = LiteratureReactionRepository(store, context.run_id)
        first = asyncio.run(binding.execute(context, "literature.reaction.populate", args, "first"))
        assert first["status"] == "completed", first.get("feedback")
        first_ref = first["result"]["sheet_ref"]
        context = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *first["record_refs"]))))
        revision = deepcopy(args)
        revision["experiment_assessment"].update(revises_sheet_ref=first_ref,
            revision_reason="Clarify interpretation of the experimental scope.",
            limitations=["No intracellular sufficiency or atom-source correction is inferred from a nominal match."])
        second = repo.populate(context, revision, "revision")
        second_ref = second["result"]["sheet_ref"]
        context = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *second["record_refs"]))))
        assert first["result"]["cells"] == second["result"]["cells"]
        cells = second["result"]["cells"]
        if case == "primary":
            assert cells["ratio_mean"]["value"] == 1
            assert cells["reaction_comparison"]["value"] is None
        elif case != "native":
            assert cells["reaction_comparison"]["value"] == pytest.approx(1/3)
            assert cells["resource_coverage_upper"]["value"] == pytest.approx(.6)
            assert cells["resource_coverage"]["value"] == (None if case == "incomplete" else .6)
        with pytest.raises(ContractError, match="revision_required"):
            repo.populate(context, args, "duplicate")
        with pytest.raises(ContractError, match="revision_required"):
            repo.populate(context, revision, "stale")
        assert len(repo.current_assessments()) == 1
        history = repo.assessment_history(second_ref)
        assert len(history) == 2
        schema = obj({"measurements": (reaction_semantic_cells_schema if case == "native" else reaction_cells_schema)()})
        form = form_with_facts({}, schema, binding.facts(context, {"committed_record_refs": [second_ref]}))
        binding.validate_report(context, form, schema)
        rows = form["measurements"]
        assert rows and all(r["experiment_ref"] == args["experiment_assessment"]["experiment_ref"] for r in rows)
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "root"),), assignment={})
        binding.received_form_references(parent, form, schema, "parent-delivery")
        view = repo.semantic_projection() if case == "native" else repo
        assert view.received_cells(parent) == rows
        allowed = {store.get(ref)[field] for ref in (first_ref, second_ref) for field in ("artifact_ref", "request_ref")}
        read = store.get_artifact
        def saved_only(ref):
            assert ref in allowed
            return read(ref)
        def forbidden(*args, **kwargs):
            raise AssertionError("replay cannot re-extract or recalculate")
        monkeypatch.setattr(store, "get_artifact", saved_only)
        monkeypatch.setattr("gene_annotation_episode.literature_reaction_storage.read_reaction_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_reaction_storage.populate_reaction_constraints", forbidden)
        store.db.execute("pragma query_only=ON")
        before = store.db.total_changes
        assert repo.assessment_history(second_ref) == history
        assert repo.current_assessments()[0]["sheet_ref"] == second_ref
        assert repo.populate(context, revision, "revision") == second
        assert view.received_cells(parent) == rows
        assert store.db.total_changes == before
    finally:
        store.close()
