"""A requirement finding must identify the selected omission/addback experiment.

These custody cases use original partner population and qualification grading.
They are deterministic integration checks, not autonomous-workflow evidence.
"""
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.a107_qualification import (
    PROVIDER, request, refresh, received_qualifications, _read, _publish,
)
from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.domain import obj, identity
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository, partner_cells_schema
from gene_annotation_episode.tool_grading_artifacts import source_tool_grading_entries
from test_literature_partner_integration import setup_case, binding_for
from test_literature_perturbation_assessments import identify
from test_scientific_hypervolume_runtime import assessment


@pytest.mark.parametrize("experiment_link,alternate_view", [
    ("selected", False), ("selected", True), ("other", False),
    ("none", False), ("unidentified", False),
    ("subject_literal", False), ("partner_literal", False),
])
def test_requirement_preserves_numbers_without_borrowing_another_assay(
        tmp_path, monkeypatch, experiment_link, alternate_view):
    store, context, population = setup_case(tmp_path, case="matched", components=["partner_loss"])
    try:
        if experiment_link == "unidentified":
            population["literals"]["experiment"] = None
            population.pop("experiment_assessment", None)
            selected_experiment = None
        else:
            context, population = identify(store, context, population, "selected-assay")
            population["experiment_assessment"].update(
                experiment_type="partner_requirement", assessment_key="partner-requirement",
                scientific_question="What contribution does this omission/addback experiment establish?")
            selected_experiment = population["experiment_assessment"]["experiment_ref"]
        literal_role = {"subject_literal": "subject", "partner_literal": "partner"}.get(experiment_link)
        if literal_role is not None:
            nominated = population["literals"][literal_role]
            anchor = {key: nominated[key] for key in ("source_ref", "start", "end", "quote")}
            anchor["artifact_ref"] = store.get(nominated["source_ref"])["artifact_ref"]
            selected_experiment = store.put("reference", {"reference_type": "assay",
                "source_ref": anchor["source_ref"], "anchor": anchor,
                "accession": identity("partner_literal", {"field": literal_role, **anchor}),
                "label": anchor["quote"], "sequence_ref": None, "molecule": None,
                "length": None, "term_refs": [], "context_refs": []}, origin="tool")["id"]
            population["experiment_assessment"]["experiment_ref"] = selected_experiment
            context = replace(context, received_record_refs=(*context.received_record_refs, selected_experiment))
        repository = LiteraturePartnerRepository(store, context.run_id)
        with monkeypatch.context() as original:
            if literal_role is not None:
                from gene_annotation_episode import literature_experiment_assessments as assessments
                original.setattr(repository, "_authorize_assessment",
                    lambda ctx, value: assessments.authorize_assessment(repository, ctx, value))
            outcome = repository.populate(context, population, "selected-omission-assay")
        sheet_ref = outcome["result"]["sheet_ref"]
        original_sheet = deepcopy(repository.read(sheet_ref))
        original_cells = repository.project_cells([sheet_ref],
            permitted_record_refs=outcome["record_refs"], components=["partner_loss"])
        subject, partner = (original_cells[0][key] for key in ("subject_ref", "partner_ref"))

        observed_experiment = selected_experiment if experiment_link == "selected" or literal_role else None
        if experiment_link == "other":
            context, other = identify(store, context, population, "other-assay-in-same-paper")
            observed_experiment = other["experiment_assessment"]["experiment_ref"]
            assert observed_experiment != selected_experiment
        source_ref = population["source_ref"]
        source = store.get(source_ref)
        artifact = source.get("text_ref") or source["artifact_ref"]
        content = store.get_artifact(artifact)
        if alternate_view:
            # The explicit assay link survives another representation of its
            # source. Equal text by itself is never used to establish the link.
            source_ref = store.put("source", {"provider": "synthetic_alternate_view",
                "accession": "alternate-paper-view", "uri": None, "artifact_ref": artifact,
                "text_ref": artifact, "request_ref": None, "version": None,
                "retrieved_at": None, "parent_source_refs": [population["source_ref"]]},
                origin="caller")["id"]
        observation = store.put("observation", {"subject_refs": [subject],
            "source_subject_refs": [subject, *([observed_experiment] if observed_experiment else [])],
            "kind": "source_content", "source_ref": source_ref, "measurements": [],
            "dependencies": [], "anchor": {"source_ref": source_ref, "artifact_ref": artifact,
                "start": 0, "end": len(content), "quote": content.decode("utf-8")}}, origin="extracted")
        target = context.scope["subject_refs"][0]
        hypothesis = store.put("hypothesis", {"subject_refs": [target], "predicate": "requires",
            "value": {"type": "reference", "ref": partner}, "context_refs": []}, origin="reasoning")
        proposed = assessment(hypothesis["id"], observation["id"], "incomparable")
        proposed["relation"] = "does_not_discriminate"
        proposed["investigation_finding"] = {
            "source_claim": {"subject_refs": [subject], "predicate": "requires",
                "value": {"type": "reference", "ref": partner}, "context_refs": []},
            "qualification": {"kind": "different_source_subject", "context_refs": [], "assumption_refs": []},
            "status": "retained", "withdrawal_reason": "not_withdrawn",
            "same_source_claim_as_ref": None, "replaces_refs": []}
        source_assessment = store.put("assessment", proposed, origin="reasoning")
        known = {target, *context.received_record_refs}
        known.update(row[0] for row in store.db.execute("SELECT id FROM records"))
        context = replace(context, received_record_refs=tuple(sorted(known)))
        binding = binding_for(store, context)
        schema = obj({"measurements": partner_cells_schema()})
        form = form_with_facts({}, schema, binding.facts(context, {"committed_record_refs": [sheet_ref]}))
        assert form["measurements"] == original_cells
        parent = replace(context, episode_id="qualification-parent", role="annotation",
            path=(("annotation", "root"),), assignment={})
        binding.received_form_references(parent, form, schema, "original-component-delivery")
        context = parent
        arguments = {"target_ref": target, "assessment_ref": source_assessment["id"],
            "component_ref": partner, "sheet_ref": sheet_ref, "components": ["partner_loss"]}
        use_ref = request(store, "partner.requirement_evidence", arguments, context=context, known=known)
        known.add(use_ref)
        context = replace(context, received_record_refs=tuple(sorted(known)))
        generated, needs = refresh(store, context, known)
        assert len(generated) == 1
        qualified = _read(store, generated[0], graded=True)
        result = qualified["result"]
        assert result["partner_components"] == original_cells
        assert repository.read(sheet_ref) == original_sheet
        assert source_tool_grading_entries(store, generated[0])[0]["grading"]["sheet"] == qualified
        assert qualified["controller_credit"] is None
        if experiment_link == "selected":
            assert result["state"] == "source_requirement_retained"
            assert result["experiment_binding"]["linked_experiment_refs"] == [selected_experiment]
            assert not result["missing"] and not needs
        else:
            assert result["state"] == "requirement_experiment_application_unresolved"
            assert result["experiment_binding"]["state"] == "unresolved"
            assert not result["experiment_binding"]["linked_experiment_refs"]
            assert result["missing"] and len(needs) == 1
            if literal_role:
                assert "selected_partner_experiment_identity_is_nonexperiment_literal" in result["missing"]
                assert result["experiment_binding"]["invalid_experiment_refs"] == [selected_experiment]

        # Historical custody remains readable, without implying that the old
        # same-paper check established this particular experiment link.
        legacy = deepcopy(qualified)
        legacy["result"].pop("experiment_binding")
        legacy_ref = _publish(store, PROVIDER, legacy, graded=True)
        historical, = received_qualifications(store, [legacy_ref], context.scope, full=True)
        assert not historical["current"]
        assert historical["qualification_update_reasons"] == ["requirement_experiment_binding_not_recorded"]
        assert historical["result"]["partner_components"] == original_cells
        assert _read(store, legacy_ref, graded=True) == legacy
    finally:
        store.close()
