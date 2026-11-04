"""Experimental partner assessments across retained and native source readers."""
import asyncio
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository, partner_cells_schema
from test_literature_partner_integration import setup_case, binding_for
from test_literature_partner_native_integration import setup_case as native_case
from test_literature_partner_defined_integration import setup_case as defined_case
from test_literature_perturbation_assessments import identify


@pytest.mark.parametrize("case", ["matched", "censored", "primary_crossed", "matched_native", "nadh"])
def test_partner_revision_preserves_one_experiment_source_uncertainty_and_parent_return(tmp_path, monkeypatch, case):
    fixture = defined_case if case == "nadh" else native_case if case == "matched_native" else setup_case
    store, context, args = fixture(tmp_path, case=case)
    try:
        context, args = identify(store, context, args)
        args["experiment_assessment"].update(experiment_type="partner_requirement",
            scientific_question="Which partner contribution is resolved by the measured omission/addback comparison?",
            conclusion="The measured dependence is conditional on the selected nonpartner factors.",
            limitations=["Genomic presence and physiological availability are separate questions."])
        binding = binding_for(store, context)
        repo = LiteraturePartnerRepository(store, context.run_id)
        tool = "literature.partner.source.populate" if "input_mode" in args else "literature.partner.populate"
        first = asyncio.run(binding.execute(context, tool, args, "first"))
        assert first["status"] == "completed", first.get("feedback")
        first_ref = first["result"]["sheet_ref"]
        context = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *first["record_refs"]))))
        revision = deepcopy(args)
        revision["experiment_assessment"].update(revises_sheet_ref=first_ref,
            revision_reason="Make the limitation on physiological necessity explicit.",
            conclusion="This comparison alone does not establish a universal physiological requirement.")
        second = repo.populate(context, revision, "revision")
        second_ref = second["result"]["sheet_ref"]
        context = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *second["record_refs"]))))
        assert first["result"]["cells"] == second["result"]["cells"]
        assert second["result"]["cells"]["reference_rate"]["value"] is not None
        if case in ("censored", "primary_crossed"):
            assert second["result"]["cells"]["partner_loss"]["value"] is None
        assert set(second["changed_record_refs"]) <= set(second["record_refs"])
        with pytest.raises(ContractError, match="revision_required"):
            repo.populate(context, revision, "stale")
        assert len(repo.current_assessments()) == 1
        history = repo.assessment_history(second_ref)
        assert len(history) == 2
        schema = obj({"measurements": partner_cells_schema()})
        form = form_with_facts({}, schema, binding.facts(context, {"committed_record_refs": [second_ref]}))
        binding.validate_report(context, form, schema)
        rows = form["measurements"]
        assert rows and all(r["experiment_ref"] == args["experiment_assessment"]["experiment_ref"] for r in rows)
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "root"),), assignment={})
        binding.received_form_references(parent, form, schema, "delivery")
        saved = repo.read(second_ref)
        allowed = {store.get(ref)[field] for ref in (first_ref, second_ref) for field in ("artifact_ref", "request_ref")}
        read = store.get_artifact
        def saved_only(ref):
            assert ref in allowed
            return read(ref)
        def forbidden(*args, **kwargs):
            raise AssertionError("saved replay cannot invoke source readers or calculators")
        monkeypatch.setattr(store, "get_artifact", saved_only)
        monkeypatch.setattr("gene_annotation_episode.literature_partner_storage.read_partner_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_partner_calculations.populate_partner_components", forbidden)
        store.db.execute("pragma query_only=ON")
        before = store.db.total_changes
        assert repo.assessment_history(second_ref) == history
        assert repo.current_assessments()[0]["sheet_ref"] == second_ref
        assert repo.populate(context, revision, "revision") == second
        assert repo.received_cells(parent) == rows
        assert repo.read(second_ref) == saved
        assert store.db.total_changes == before
    finally:
        store.close()
