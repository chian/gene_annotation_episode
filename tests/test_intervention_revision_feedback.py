"""A stale assessment can be corrected using only an already received head."""
import asyncio
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_intervention_storage import LiteratureInterventionRepository
from gene_annotation_episode.state import Store
from test_literature_intervention_storage import intervention_fixture
from test_literature_rate_episode_integration import service_binding


@pytest.mark.parametrize("latest_received", [False, True])
def test_revision_feedback_preserves_history_and_only_names_received_latest_sheet(tmp_path, latest_received):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="ATGGCT", molecule="dna")
        context, arguments = intervention_fixture(store)
        repository = LiteratureInterventionRepository(store, context.run_id)
        first = repository.populate(context, arguments, "original")["result"]["sheet_ref"]
        context = replace(context, received_record_refs=[*context.received_record_refs, first])
        revised = deepcopy(arguments)
        revised["experiment_assessment"].update(revises_sheet_ref=first,
            revision_reason="Clarify the synthetic experimental limitation.",
            conclusion="This is the revised synthetic conclusion.")
        second = repository.populate(context, revised, "revision")["result"]["sheet_ref"]
        saved = {ref: repository.read(ref) for ref in (first, second)}
        if latest_received:
            context = replace(context, received_record_refs=[*context.received_record_refs, second])
        services, _ = service_binding(store, context)
        binding = LiteratureEpisodes(services, rate_population=True, a106_intervention=True)
        services.workflow.episode_bindings = EpisodeBindingRegistry((binding,))
        failed = asyncio.run(binding.execute(context, "literature.intervention_grading.populate",
            revised, "stale-revision"))
        assert failed["status"] == "invalid" and failed["result"] is None
        assert failed["record_refs"] == failed["changed_record_refs"] == []
        assert failed["feedback"]["code"] == "intervention_latest_revision_required"
        detail = failed["feedback"].get("detail", {})
        assert {ref: repository.read(ref) for ref in (first, second)} == saved
        assert repository.current_assessments()[0]["sheet_ref"] == second
        if not latest_received:
            assert detail == {}
            assert "detail" not in failed["feedback"]
            return
        assert detail == {"experiment_ref": arguments["experiment_ref"],
            "assessment_key": arguments["experiment_assessment"]["assessment_key"],
            "requested_predecessor": first, "latest_sheet_ref": second}
        corrected = deepcopy(revised)
        corrected["experiment_assessment"].update(revises_sheet_ref=detail["latest_sheet_ref"],
            revision_reason="Carry forward the latest synthetic conclusion.")
        accepted = asyncio.run(binding.execute(context, "literature.intervention_grading.populate",
            corrected, "corrected-revision"))
        assert accepted["status"] == "completed"
        latest, = repository.current_assessments()
        assert latest["sheet_ref"] == accepted["result"]["sheet_ref"]
        assert latest["revises_sheet_ref"] == second
        assert {ref: repository.read(ref) for ref in (first, second)} == saved
