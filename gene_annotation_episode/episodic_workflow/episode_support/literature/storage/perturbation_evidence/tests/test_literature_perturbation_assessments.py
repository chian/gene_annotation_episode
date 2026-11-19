"""One experiment survives corrected assessments and selected parent delivery, through the real runner."""
import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.perturbation_evidence.literature_perturbation_assessments import EXPERIMENT_TYPES
from .library_world import run_scenarios, world  # noqa: F401 - ``world`` is the fixture


@pytest.mark.parametrize('summary', [False, True])
def test_multiple_experiments_revisions_parent_numbers_and_saved_reconstruction(world, summary):
    outcome, = run_scenarios(world, 'experiments', ('multiple_experiments', {'summary': summary}))
    assert outcome['sheets'] == 3 and outcome['received_rows'] > 0


def test_duplicate_representation_and_stale_revision_cannot_create_another_experiment(world):
    outcome, = run_scenarios(world, 'duplicates', ('duplicate_and_stale_revision', {}))
    assert outcome == {'current': 1}


def test_cannot_revise_another_experiment_or_use_unreceived_identity(world):
    outcome, = run_scenarios(world, 'revisions', ('revise_other_experiment', {}))
    assert outcome == {'current': 1}


def test_reusable_type_includes_intervention_designs_and_separate_scientific_considerations():
    template = EXPERIMENT_TYPES["intervention_response"]
    assert {"native_deletion_restoration", "selective_perturbation_restoration", "variant_replacement", "cas_free_reconstitution"} <= set(template["designs"])
    assert len(template["considerations"]) == 7
