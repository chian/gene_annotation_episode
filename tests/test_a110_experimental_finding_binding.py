"""Experimental components retain their particular source-finding identity."""
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode import a110_experimental_qualification as experimental
from gene_annotation_episode.a110_qualification import received
from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.domain import obj, identity
from gene_annotation_episode.literature_reaction_storage import LiteratureReactionRepository, reaction_cells_schema
from gene_annotation_episode.tool_grading_artifacts import source_tool_grading_entries
from test_literature_reaction_integration import setup_case, binding_for
from test_literature_perturbation_assessments import identify
from test_scientific_hypervolume_runtime import assessment


@pytest.mark.parametrize("experiment_link,alternate_view", [
    ("selected", False), ("selected", True), ("other", False),
    ("none", False), ("unidentified", False), ("no_finding", False),
    ("literal_subject", False), ("literal_subject_no_finding", False),
])
def test_experimental_finding_uses_the_selected_assay_without_changing_its_measurements(
        tmp_path, monkeypatch, experiment_link, alternate_view):
    store, context, population = setup_case(tmp_path)
    try:
        context = replace(context, assignment={**context.assignment,
            "requested_reaction_components": ["ratio_mean"]})
        selected_experiment = None
        literal_subject = experiment_link.startswith("literal_subject")
        no_finding = experiment_link in {"no_finding", "literal_subject_no_finding"}
        if experiment_link == "unidentified":
            population["literals"]["experiment"] = None
            population.pop("experiment_assessment", None)
        else:
            context, population = identify(store, context, population, "selected-reaction-assay")
            population["experiment_assessment"].update(
                experiment_type="reaction_prediction", assessment_key="selected-reaction-ratio")
            selected_experiment = population["experiment_assessment"]["experiment_ref"]
        if literal_subject:
            nominated = population["literals"]["molecule"]
            anchor = {key: nominated[key] for key in ("source_ref", "start", "end", "quote")}
            anchor["artifact_ref"] = store.get(nominated["source_ref"])["artifact_ref"]
            selected_experiment = store.put("reference", {"reference_type": "assay",
                "source_ref": anchor["source_ref"], "anchor": anchor,
                "accession": identity("reaction_literal", {"field": "molecule", **anchor}),
                "label": anchor["quote"], "sequence_ref": None, "molecule": None,
                "length": None, "term_refs": [], "context_refs": []}, origin="tool")["id"]
            population["experiment_assessment"]["experiment_ref"] = selected_experiment
            context = replace(context, received_record_refs=(*context.received_record_refs, selected_experiment))
        repository = LiteratureReactionRepository(store, context.run_id)
        with monkeypatch.context() as original:
            if literal_subject:
                from gene_annotation_episode import literature_experiment_assessments as assessments
                original.setattr(repository, "_authorize_assessment",
                    lambda ctx, value: assessments.authorize_assessment(repository, ctx, value))
            outcome = repository.populate(context, population, "original-ratio-measurement")
        sheet_ref = outcome["result"]["sheet_ref"]
        original_sheet = deepcopy(repository.read(sheet_ref))
        original_cells = repository.project_cells([sheet_ref],
            permitted_record_refs=outcome["record_refs"], components=["ratio_mean"])
        subject = original_cells[0]["assayed_subject_ref"]
        target = context.scope["subject_refs"][0]
        reaction = store.put("term", {"namespace": "synthetic_reaction", "accession": "reaction-one",
            "label": "synthetic reaction", "term_type": "reaction", "source_ref": population["source_ref"],
            "anchor": None}, origin="caller")["id"]
        assessment_ref = None
        if not no_finding:
            observed_experiment = selected_experiment if experiment_link == "selected" or literal_subject else None
            if experiment_link == "other":
                context, other = identify(store, context, population, "different-reaction-assay")
                observed_experiment = other["experiment_assessment"]["experiment_ref"]
                assert observed_experiment != selected_experiment
            source_ref = population["source_ref"]
            source = store.get(source_ref)
            artifact = source.get("text_ref") or source["artifact_ref"]
            content = store.get_artifact(artifact)
            if alternate_view:
                source_ref = store.put("source", {"provider": "synthetic_alternate_view",
                    "accession": "alternate-reaction-paper", "uri": None,
                    "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
                    "version": None, "retrieved_at": None,
                    "parent_source_refs": [population["source_ref"]]}, origin="caller")["id"]
            observation = store.put("observation", {"subject_refs": [subject],
                "source_subject_refs": [subject, *([observed_experiment] if observed_experiment else [])],
                "source_ref": source_ref, "kind": "source_content", "measurements": [],
                "dependencies": [], "anchor": {"source_ref": source_ref, "artifact_ref": artifact,
                    "start": 0, "end": len(content), "quote": content.decode("utf-8")}}, origin="extracted")
            hypothesis = store.put("hypothesis", {"subject_refs": [target], "predicate": "catalyzes",
                "value": {"type": "reference", "ref": reaction}, "context_refs": []}, origin="reasoning")
            proposed = assessment(hypothesis["id"], observation["id"], "incomparable")
            proposed["relation"] = "does_not_discriminate"
            proposed["investigation_finding"] = {
                "source_claim": {"subject_refs": [subject], "predicate": "catalyzes",
                    "value": {"type": "reference", "ref": reaction}, "context_refs": []},
                "qualification": {"kind": "different_source_subject", "context_refs": [], "assumption_refs": []},
                "status": "retained", "withdrawal_reason": "not_withdrawn",
                "same_source_claim_as_ref": None, "replaces_refs": []}
            assessment_ref = store.put("assessment", proposed, origin="reasoning")["id"]
        known = {target, *context.received_record_refs}
        known.update(row[0] for row in store.db.execute("SELECT id FROM records"))
        context = replace(context, received_record_refs=tuple(sorted(known)))
        binding = binding_for(store, context)
        schema = obj({"measurements": reaction_cells_schema()})
        form = form_with_facts({}, schema, binding.facts(context, {"committed_record_refs": [sheet_ref]}))
        assert form["measurements"] == original_cells
        parent = replace(context, episode_id="qualification-parent", role="annotation",
            path=(("annotation", "root"),), assignment={})
        binding.received_form_references(parent, form, schema, "original-component-delivery")
        context = parent
        arguments = {"target_ref": target, "sheet_ref": sheet_ref, "components": ["ratio_mean"],
            "reaction_ref": reaction, "assessment_ref": assessment_ref, "actual_ref": subject,
            "target_subject_ref": None, "source_alignment_ref": None, "alignment_ref": None, "positions": None}
        use_ref = experimental.request(store, arguments, context=context, known=known)
        known.add(use_ref)
        context = replace(context, received_record_refs=tuple(sorted(known)))
        generated, _needs = experimental.refresh(store, context, known)
        qualified, = [experimental.read(store, ref, qualified=True) for ref in generated]
        result = qualified["result"]
        assert result["selected_components"] == original_cells
        assert repository.read(sheet_ref) == original_sheet
        assert source_tool_grading_entries(store, generated[0])[0]["grading"]["sheet"] == qualified
        assert qualified["scientific_credit"] is None
        if literal_subject:
            assert "selected_experiment_identity_is_subject_or_construct_literal" in result["missing"]
        if no_finding:
            assert result["experiment_binding"] is None
            assert result["source_function_finding"] is None
        elif experiment_link == "selected":
            assert result["experiment_binding"]["state"] == "matched"
            assert result["experiment_binding"]["linked_experiment_refs"] == [selected_experiment]
            assert not any("experiment_link_unestablished" in item for item in result["missing"])
        else:
            assert result["experiment_binding"]["state"] == "unresolved"
            assert not result["experiment_binding"]["linked_experiment_refs"]
            assert any("experiment" in item for item in result["missing"])
            if literal_subject:
                assert result["experiment_binding"]["invalid_experiment_refs"] == [selected_experiment]
        legacy = deepcopy(qualified)
        legacy["result"].pop("experiment_binding")
        legacy_ref = experimental.publish(store, experimental.PROVIDER, legacy)
        historical, = received(store, [legacy_ref], context.scope)
        assert historical["current"] is no_finding
        assert historical["result"]["selected_components"] == original_cells
        assert experimental.read(store, legacy_ref, qualified=True) == legacy
    finally:
        store.close()
