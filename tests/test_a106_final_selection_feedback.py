"""A mistaken source selection identifies the received field needing repair."""
import asyncio
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.literature_a106_subscore_storage import LiteratureA106SubscoreRepository
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_intervention_storage import LiteratureInterventionRepository
from gene_annotation_episode.state import Store
from test_literature_a106_subscore import prepared
from test_literature_rate_episode_integration import service_binding


@pytest.mark.parametrize("source_received", [False, True])
def test_final_selection_feedback_identifies_received_source_without_publishing_a_score(tmp_path, source_received):
    with Store(tmp_path) as store:
        context, assessment, correct, _ = prepared(store)
        wrong_ref = assessment["source_ref"]
        if not source_received:
            context = replace(context, received_record_refs=[ref for ref in context.received_record_refs
                if ref != wrong_ref])
        services, _ = service_binding(store, context)
        binding = LiteratureEpisodes(services, rate_population=True, a106_intervention=True)
        services.workflow.episode_bindings = EpisodeBindingRegistry((binding,))
        proposed = deepcopy(correct)
        proposed["experiments"][0]["sheet_ref"] = wrong_ref
        sources_before = store.list("source")
        failed = asyncio.run(binding.execute(context, "literature.a106.finalize", proposed, "wrong-source"))
        assert failed["status"] == "invalid" and failed["result"] is None
        assert failed["record_refs"] == failed["changed_record_refs"] == []
        assert store.list("source") == sources_before
        feedback = failed["feedback"]
        if not source_received:
            assert feedback["code"] == "assay_grading_record_not_received"
            assert "detail" not in feedback
            return
        assert feedback["code"] == "assay_grading_sheet_required"
        detail = feedback["detail"]
        assert detail["field"] == "experiments.0.sheet_ref"
        assert detail["sheet_ref"] == wrong_ref
        assert detail["experiment_ref"] == assessment["experiment_ref"]
        assert detail["actual_provider"] == store.get(wrong_ref)["provider"]
        assert detail["expected_provider"] == LiteratureInterventionRepository.provider
        assert "literature.intervention_grading.populate" in detail["requirement"]
        accepted = asyncio.run(binding.execute(context, "literature.a106.finalize", correct, "correct-source"))
        assert accepted["status"] == "completed"
        cell = accepted["result"]["cells"][0]
        assert cell["value"] == pytest.approx(7.5)
        assert cell["experiments"][0]["sheet_ref"] == correct["experiments"][0]["sheet_ref"]


@pytest.mark.parametrize("latest_received", [False, True])
def test_stale_assessment_feedback_identifies_only_the_received_matching_head(tmp_path, latest_received):
    with Store(tmp_path) as store:
        context, assessment, args, _ = prepared(store)
        native = LiteratureInterventionRepository(store, context.run_id)
        finals = LiteratureA106SubscoreRepository(store, context.run_id)
        first_final = finals.populate(context, args, "first-final")["result"]["sheet_ref"]
        context = replace(context, received_record_refs=[*context.received_record_refs, first_final])
        old_ref = args["experiments"][0]["sheet_ref"]
        revision = deepcopy(assessment)
        revision["experiment_assessment"].update(revises_sheet_ref=old_ref, revision_reason="Correct attribution")
        revision["interpretations"]["attribution_supported"] = dict(status="unknown", support_refs=[])
        latest = native.populate(context, revision, "revised-assessment")["result"]["sheet_ref"]
        # Another current assessment of the same experiment is not this revision's head.
        different = deepcopy(assessment)
        different["experiment_assessment"]["assessment_key"] += "_another_question"
        other = native.populate(context, different, "other-assessment")["result"]["sheet_ref"]
        context = replace(context, received_record_refs=[*context.received_record_refs, other,
            *([latest] if latest_received else [])])
        services, _ = service_binding(store, context)
        binding = LiteratureEpisodes(services, rate_population=True, a106_intervention=True)
        services.workflow.episode_bindings = EpisodeBindingRegistry((binding,))
        args.update(revises_subscore_ref=first_final, revision_reason="Select the corrected assessment")
        before = store.list("source")
        failed = asyncio.run(binding.execute(context, "literature.a106.finalize", args, "stale-assessment"))
        assert failed["status"] == "invalid" and failed["result"] is None
        assert failed["record_refs"] == failed["changed_record_refs"] == []
        assert store.list("source") == before
        assert failed["feedback"]["code"] == "a106_current_assessment_required"
        stale = failed["feedback"]["detail"]["stale_assessments"]
        assert len(stale) == 1
        assert stale[0]["field"] == "experiments.0.sheet_ref"
        assert stale[0]["sheet_ref"] == old_ref
        assert stale[0]["assessment_key"] == assessment["experiment_assessment"]["assessment_key"]
        if latest_received:
            assert stale[0]["latest_sheet_ref"] == latest
        else:
            assert "latest_sheet_ref" not in stale[0]
            assert latest not in str(failed["feedback"])
        assert other not in str(failed["feedback"])
        # Correcting the explicit selection uses the revised science, without rewriting history.
        context = replace(context, received_record_refs=list(dict.fromkeys([*context.received_record_refs, latest])))
        args["experiments"][0]["sheet_ref"] = latest
        accepted = asyncio.run(binding.execute(context, "literature.a106.finalize", args, "current-assessment"))
        assert accepted["status"] == "completed"
        assert accepted["result"]["cells"][0]["value"] is None
        assert finals.read(first_final)["sheet"]["cells"]["experimental_subscore"]["value"] == pytest.approx(7.5)


@pytest.mark.parametrize("latest_received", [False, True])
def test_stale_final_feedback_withholds_unreceived_current_reference(tmp_path, latest_received):
    with Store(tmp_path) as store:
        context, _, args, _ = prepared(store)
        repo = LiteratureA106SubscoreRepository(store, context.run_id)
        first = repo.populate(context, args, "first-final")["result"]["sheet_ref"]
        context = replace(context, received_record_refs=[*context.received_record_refs, first])
        args.update(revises_subscore_ref=first, revision_reason="Correct the conclusion",
            conclusion="Corrected conclusion for the same synthetic comparison.")
        latest = repo.populate(context, args, "revised-final")["result"]["sheet_ref"]
        if latest_received:
            context = replace(context, received_record_refs=[*context.received_record_refs, latest])
        services, _ = service_binding(store, context)
        binding = LiteratureEpisodes(services, rate_population=True, a106_intervention=True)
        services.workflow.episode_bindings = EpisodeBindingRegistry((binding,))
        before = store.list("source")
        failed = asyncio.run(binding.execute(context, "literature.a106.finalize", args, "stale-final"))
        assert failed["status"] == "invalid" and failed["result"] is None
        assert failed["record_refs"] == failed["changed_record_refs"] == []
        assert store.list("source") == before
        assert failed["feedback"]["code"] == "a106_latest_subscore_revision_required"
        detail = failed["feedback"]["detail"]
        assert detail["field"] == "revises_subscore_ref" and detail["requested_predecessor"] == first
        if latest_received:
            assert detail["latest_subscore_refs"] == [latest]
        else:
            assert "latest_subscore_refs" not in detail
            assert latest not in str(failed["feedback"])
        context = replace(context, received_record_refs=list(dict.fromkeys([*context.received_record_refs, latest])))
        args["revises_subscore_ref"] = latest
        accepted = asyncio.run(binding.execute(context, "literature.a106.finalize", args, "current-final"))
        assert accepted["status"] == "completed"
        assert accepted["result"]["cells"][0]["revises_subscore_ref"] == latest
        assert repo.read(latest)["selection"]["revises_subscore_ref"] == first
