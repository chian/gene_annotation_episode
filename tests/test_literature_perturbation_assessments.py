"""One experiment survives corrected assessments and selected parent delivery."""
import asyncio
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.literature_perturbation_assessments import EXPERIMENT_TYPES
from gene_annotation_episode.literature_perturbation_storage import LiteraturePerturbationRepository, perturbation_cells_schema
from gene_annotation_episode.literature_perturbation_summary_storage import perturbation_summary_cells_schema
from test_literature_perturbation_integration import setup_case, binding_for
from test_literature_perturbation_summary_integration import fixture as summary_fixture


def identify(store, context, args, name="experiment-one"):
    record = store.put("reference", {"reference_type": "assay", "source_ref": args["source_ref"],
        "accession": name, "label": name, "sequence_ref": None, "molecule": None,
        "length": None, "term_refs": [], "context_refs": []}, origin="caller")
    args = deepcopy(args)
    args["experiment_assessment"] = {"experiment_ref": record["id"],
        "experiment_type": "intervention_response", "assessment_key": "intervention-contribution",
        "scientific_question": "Does the intervention alter the measured outcome?",
        "conclusion": "The endpoint changes under the selected intervention.",
        "limitations": ["Joint uncertainty of the source index remains unreported."],
        "revises_sheet_ref": None, "revision_reason": None}
    context = replace(context, received_record_refs=(*context.received_record_refs, record["id"]))
    return context, args


@pytest.mark.parametrize("summary", [False, True])
def test_multiple_experiments_revisions_parent_numbers_and_saved_reconstruction(tmp_path, monkeypatch, summary):
    store, context, args = (summary_fixture if summary else setup_case)(tmp_path)
    try:
        binding = binding_for(store, context)
        repo = LiteraturePerturbationRepository(store, context.run_id)
        context, args = identify(store, context, args)
        original = asyncio.run(binding.execute(context, "literature.perturbation.populate", args, "original"))
        assert original["status"] == "completed", original
        first = original["result"]["sheet_ref"]
        context = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *original["record_refs"]))))
        revision = deepcopy(args)
        revision["experiment_assessment"].update(revises_sheet_ref=first,
            revision_reason="Restrict the conclusion to the experimentally measured endpoint.",
            conclusion="The measured endpoint changes; a direct catalytic function is not established.")
        revised = asyncio.run(binding.execute(context, "literature.perturbation.populate", revision, "revision"))
        assert revised["status"] == "completed", revised
        second = revised["result"]["sheet_ref"]
        assert first != second
        assert original["result"]["cells"] == revised["result"]["cells"]
        context = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *revised["record_refs"]))))
        other_context, other_args = identify(store, context, args, "experiment-two")
        other = repo.populate(other_context, other_args, "second-experiment")
        heads = repo.current_assessments()
        assert len(heads) == 2
        assert {row["sheet_ref"] for row in heads} == {second, other["result"]["sheet_ref"]}
        assert len({row["experiment_ref"] for row in heads}) == 2
        assert [row["sheet_ref"] for row in repo.assessment_history(second)] == [first, second]

        schema = obj({"measurements": (perturbation_summary_cells_schema if summary else perturbation_cells_schema)()})
        facts = binding.facts(context, {"committed_record_refs": [second]})
        form = form_with_facts({}, schema, facts)
        binding.validate_report(context, form, schema)
        rows = form["measurements"]
        assert rows and any(row["value"] is not None for row in rows)
        assert all(row["experiment_ref"] == args["experiment_assessment"]["experiment_ref"] for row in rows)
        parent = replace(context, episode_id="parent", role="annotation", assignment={}, path=(("annotation", "root"),))
        binding.received_form_references(parent, form, schema, "assessment-delivery")
        projection = repo.summary_projection() if summary else repo
        assert projection.received_cells(parent) == rows

        saved = [repo.read(ref) for ref in (first, second, other["result"]["sheet_ref"])]
        allowed = {store.get(ref)[key] for ref in (first, second, other["result"]["sheet_ref"])
                   for key in ("artifact_ref", "request_ref")}
        get_artifact = store.get_artifact
        def saved_only(ref):
            assert ref in allowed, "source data must not be reread"
            return get_artifact(ref)
        def forbidden(*args, **kwargs):
            raise AssertionError("saved reconstruction must not recalculate")
        monkeypatch.setattr(store, "get_artifact", saved_only)
        monkeypatch.setattr("gene_annotation_episode.literature_perturbation_storage.read_perturbation_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_perturbation_storage.populate_source_restoration", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_perturbation_storage.populate_source_summary_restoration", forbidden)
        store.db.execute("pragma query_only=ON")
        before = store.db.total_changes
        assert repo.current_assessments() == heads
        assert len(repo.assessment_history(second)) == 2
        assert repo.populate(context, revision, "revision") == revised
        assert projection.received_cells(parent) == rows
        assert [repo.read(ref) for ref in (first, second, other["result"]["sheet_ref"])] == saved
        assert store.db.total_changes == before
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()


def test_duplicate_representation_and_stale_revision_cannot_create_another_experiment(tmp_path):
    store, context, args = setup_case(tmp_path)
    try:
        context, args = identify(store, context, args)
        repo = LiteraturePerturbationRepository(store, context.run_id)
        first = repo.populate(context, args, "one")
        context = replace(context, received_record_refs=(*context.received_record_refs, *first["record_refs"]))
        with pytest.raises(ContractError, match="revision_required"):
            repo.populate(context, args, "duplicate-report")
        revision = deepcopy(args)
        revision["experiment_assessment"].update(revises_sheet_ref=first["result"]["sheet_ref"], revision_reason="Correction")
        repo.populate(context, revision, "two")
        with pytest.raises(ContractError, match="revision_required"):
            repo.populate(context, revision, "stale-correction")
        assert len(repo.current_assessments()) == 1
        assert store.db.execute("SELECT count(*) FROM literature_perturbation_operations").fetchone()[0] == 2
    finally:
        store.close()


def test_cannot_revise_another_experiment_or_use_unreceived_identity(tmp_path):
    store, context, args = setup_case(tmp_path)
    try:
        received, args = identify(store, context, args)
        repo = LiteraturePerturbationRepository(store, context.run_id)
        with pytest.raises(ContractError, match="experiment_not_received"):
            repo.populate(context, args, "unreceived")
        first = repo.populate(received, args, "one")
        received = replace(received, received_record_refs=(*received.received_record_refs, *first["record_refs"]))
        other, other_args = identify(store, received, args, "another-experiment")
        other_args["experiment_assessment"].update(revises_sheet_ref=first["result"]["sheet_ref"], revision_reason="Wrong experiment")
        with pytest.raises(ContractError, match="predecessor_mismatch"):
            repo.populate(other, other_args, "wrong")
        assert len(repo.current_assessments()) == 1
    finally:
        store.close()


def test_reusable_type_includes_intervention_designs_and_separate_scientific_considerations():
    template = EXPERIMENT_TYPES["intervention_response"]
    assert {"native_deletion_restoration", "selective_perturbation_restoration", "variant_replacement", "cas_free_reconstitution"} <= set(template["designs"])
    assert len(template["considerations"]) == 7
