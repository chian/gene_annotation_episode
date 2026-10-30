"""A108 revisions keep physical context evidence and parent numerical results."""
import asyncio
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.literature_context_storage import (
    LiteratureContextRepository, context_cells_schema, context_semantic_cells_schema,
)
from test_literature_context_integration import setup_case, binding_for
from test_literature_context_native_observations import native_fixture
from test_literature_perturbation_assessments import identify


@pytest.mark.parametrize("case", ["paired", "marginal", "primary", "native"])
def test_context_assessments_preserve_combination_partial_results_and_revision_history(tmp_path, monkeypatch, case):
    if case == "native":
        store, context, args, _, _ = native_fixture(tmp_path)
        context = replace(context, assignment={"version": "literature_assignment_v1",
            "question_context_refs": [], "source_refs": list(context.received_record_refs),
            "requested_context_components": ["selected_point", "sampling_lower"]})
    else:
        store, context, args = setup_case(tmp_path, case=case)
    try:
        context, args = identify(store, context, args)
        args["experiment_assessment"].update(experiment_type="requirement_compatibility",
            scientific_question="What does the observed biological context establish about compatibility?",
            conclusion="Compatibility is conditional on the supported requirements and sampling frame.",
            limitations=["Unexamined biological states remain unresolved."])
        binding = binding_for(store, context)
        repo = LiteratureContextRepository(store, context.run_id)
        original = asyncio.run(binding.execute(context, "literature.context.populate", args, "first"))
        assert original["status"] == "completed", original
        first = original["result"]["sheet_ref"]
        context = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *original["record_refs"]))))
        revision = deepcopy(args)
        revision["experiment_assessment"].update(revises_sheet_ref=first,
            revision_reason="Clarify the native versus measured context scope.",
            limitations=["The observations do not establish unmeasured habitat coverage."])
        revised = repo.populate(context, revision, "revision")
        second = revised["result"]["sheet_ref"]
        context = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *revised["record_refs"]))))
        assert original["result"]["cells"] == revised["result"]["cells"]
        cells = revised["result"]["cells"]
        if case == "primary":
            assert [cells[n]["value"] for n in ("selected_lower", "selected_upper", "selected_point")] == [0, 1, None]
        elif case == "marginal":
            assert [cells[n]["value"] for n in ("coverage_lower", "coverage_upper")] == pytest.approx([.5, .8])
        else:
            assert cells["selected_point"]["value"] == .5
        with pytest.raises(ContractError, match="revision_required"):
            repo.populate(context, args, "duplicate-report")
        with pytest.raises(ContractError, match="revision_required"):
            repo.populate(context, revision, "stale-revision")
        assert len(repo.current_assessments()) == 1
        history = repo.assessment_history(second)
        assert [r["sheet_ref"] for r in history] == [first, second]

        schema = obj({"measurements": (context_semantic_cells_schema if case == "native" else context_cells_schema)()})
        form = form_with_facts({}, schema, binding.facts(context, {"committed_record_refs": [second]}))
        binding.validate_report(context, form, schema)
        rows = form["measurements"]
        assert rows and all(r["experiment_ref"] == args["experiment_assessment"]["experiment_ref"] for r in rows)
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "root"),), assignment={})
        binding.received_form_references(parent, form, schema, "parent-delivery")
        view = repo.semantic_projection() if case == "native" else repo
        assert view.received_cells(parent) == rows
        saved = repo.read(second)
        if case == "native":
            assert saved["native_observations"][0]["reported_sd"] == .2
            assert saved["native_observations"][1]["reported_sem"] == .1
        allowed = {store.get(ref)[field] for ref in (first, second) for field in ("artifact_ref", "request_ref")}
        read = store.get_artifact
        def saved_only(ref):
            assert ref in allowed, "original scientific sources must not be read"
            return read(ref)
        def forbidden(*args, **kwargs):
            raise AssertionError("saved reconstruction must not recalculate")
        monkeypatch.setattr(store, "get_artifact", saved_only)
        monkeypatch.setattr("gene_annotation_episode.literature_context_storage.read_context_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_context_storage.populate_context_compatibility", forbidden)
        store.db.execute("pragma query_only=ON")
        before = store.db.total_changes
        assert repo.assessment_history(second) == history
        assert repo.current_assessments()[0]["sheet_ref"] == second
        assert repo.populate(context, revision, "revision") == revised
        assert view.received_cells(parent) == rows
        assert repo.read(second) == saved
        assert store.db.total_changes == before
    finally:
        store.close()
